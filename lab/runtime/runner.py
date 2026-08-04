"""Crash-recoverable render runner over one journal and adapter lifecycle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from lab.compiler.build import load_validated_build_directory
from lab.compiler.profiles import REPO_ROOT
from lab.compiler.provenance import canonical_json_bytes, sha256_bytes

from .adapters import AdapterError, GenerationAdapter, VeoVertexAdapter
from .contracts import validate_runtime_configuration, validate_runtime_instance
from .journal import JobJournal, JournalError, TERMINAL_STATES, redact

JOB_SCHEMA = "cpcs.render_job/1.0"


class RunnerCrash(RuntimeError):
    """Test hook equivalent of abrupt process death; state is intentionally untouched."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _job_id(idempotency_key: str) -> str:
    return "render_job_" + hashlib.sha256(idempotency_key.encode()).hexdigest()[:24]


def make_render_job(
    build_dir: Path,
    *,
    idempotency_key: str,
    adapter: str = "google_vertex_ai.veo/1.0",
    timeout_seconds: float = 3600,
    poll_interval_seconds: float = 10,
    max_safe_retries: int = 2,
    lease_seconds: float = 60,
    created_at: str | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    build = load_validated_build_directory(build_dir, root)
    job = {
        "schema": JOB_SCHEMA,
        "job_id": _job_id(idempotency_key),
        "idempotency_key": idempotency_key,
        "build_dir": str(build["directory"]),
        "build_id": build["manifest"]["build_id"],
        "build_hash": build["manifest"]["build_hash"],
        "adapter": adapter,
        "policy": {
            "timeout_seconds": timeout_seconds,
            "poll_interval_seconds": poll_interval_seconds,
            "max_safe_retries": max_safe_retries,
            "lease_seconds": lease_seconds,
        },
        "created_at": created_at or _utc_now(),
    }
    validate_runtime_instance("render_job", job, root)
    return job


class RenderRunner:
    def __init__(
        self,
        journal: JobJournal,
        *,
        root: Path = REPO_ROOT,
        work_root: Path | None = None,
        adapters: Mapping[str, GenerationAdapter] | None = None,
        worker_id: str | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        crash_hook: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self.journal = journal
        self.root = root
        self.work_root = (work_root or root / "work/render_jobs").expanduser().resolve()
        self.work_root.mkdir(parents=True, exist_ok=True)
        self.adapters = dict(adapters or {"google_vertex_ai.veo/1.0": VeoVertexAdapter()})
        self.worker_id = worker_id or "worker_" + uuid.uuid4().hex
        self.sleep_fn = sleep_fn
        self.crash_hook = crash_hook

    def register(self, job: dict[str, Any]) -> dict[str, Any]:
        validate_runtime_instance("render_job", job, self.root)
        if job["job_id"] != _job_id(job["idempotency_key"]):
            raise JournalError("render job ID does not match its idempotency key")
        build = load_validated_build_directory(Path(job["build_dir"]), self.root)
        if (
            build["manifest"]["build_id"] != job["build_id"]
            or build["manifest"]["build_hash"] != job["build_hash"]
        ):
            raise JournalError("render job build identity does not match build directory")
        if job["adapter"] not in self.adapters:
            raise JournalError(f"no registered generation adapter: {job['adapter']}")
        return self.journal.register(job)

    def _job_root(self, job_id: str) -> Path:
        if not job_id.startswith("render_job_"):
            raise JournalError("invalid render job ID")
        path = (self.work_root / job_id).resolve()
        if self.work_root not in path.parents:
            raise JournalError("render job path escaped work root")
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _write_json_once(
        path: Path, value: Any, *, redact_secrets: bool = True
    ) -> None:
        safe = redact(value) if redact_secrets else value
        data = canonical_json_bytes(safe)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != data:
                raise JournalError(f"render artifact collision: {path.name}")
            return
        temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise JournalError(f"render artifact must be an object: {path.name}")
        return value

    def _hook(self, event: str, snapshot: dict[str, Any]) -> None:
        if self.crash_hook is not None:
            self.crash_hook(event, snapshot)

    def _error(
        self,
        job_id: str,
        policy: dict[str, Any],
        snapshot: dict[str, Any],
        error: Exception,
        *,
        state: str = "failed",
    ) -> dict[str, Any]:
        payload = {
            "type": type(error).__name__,
            "message": str(error),
            "code": getattr(error, "code", "runtime_error"),
            "retryable": bool(getattr(error, "retryable", False)),
            "submission_uncertain": bool(
                getattr(error, "submission_uncertain", False)
            ),
        }
        return self.journal.transition(
            job_id,
            self.worker_id,
            expected={snapshot["state"]},
            state=state,
            event_type=state,
            payload=payload,
            error=payload,
            lease_seconds=policy["lease_seconds"],
        )

    def run(self, job_id: str) -> dict[str, Any]:
        initial = self.journal.get(job_id)
        if initial["state"] in TERMINAL_STATES or initial["state"] == "submission_unknown":
            return initial
        policy = initial["job"]["policy"]
        snapshot = self.journal.claim(job_id, self.worker_id, policy["lease_seconds"])
        release = True
        try:
            adapter = self.adapters[snapshot["adapter"]]
            job_root = self._job_root(job_id)
            build = load_validated_build_directory(
                Path(snapshot["job"]["build_dir"]), self.root
            )
            if (
                build["manifest"]["build_id"] != snapshot["job"]["build_id"]
                or build["manifest"]["build_hash"] != snapshot["job"]["build_hash"]
            ):
                raise JournalError("build changed after render job registration")
            while True:
                state = snapshot["state"]
                if state in TERMINAL_STATES or state == "submission_unknown":
                    return snapshot
                if self.journal.time_fn() >= snapshot["deadline_at"]:
                    return self._error(
                        job_id,
                        policy,
                        snapshot,
                        TimeoutError("render job exceeded its persisted deadline"),
                        state="timed_out",
                    )
                if state == "queued":
                    adapter.validate(build, snapshot["job"])
                    snapshot = self.journal.transition(
                        job_id,
                        self.worker_id,
                        expected={"queued"},
                        state="validated",
                        event_type="validated",
                        payload={"build_id": build["manifest"]["build_id"]},
                        lease_seconds=policy["lease_seconds"],
                    )
                    continue
                if state == "validated":
                    prepared = adapter.prepare(build, snapshot["job"])
                    self._write_json_once(
                        job_root / "prepared_request.json",
                        prepared,
                        redact_secrets=False,
                    )
                    snapshot = self.journal.transition(
                        job_id,
                        self.worker_id,
                        expected={"validated"},
                        state="prepared",
                        event_type="prepared",
                        payload={"request_hash": sha256_bytes(canonical_json_bytes(prepared))},
                        lease_seconds=policy["lease_seconds"],
                    )
                    continue
                if state == "prepared":
                    snapshot = self.journal.transition(
                        job_id,
                        self.worker_id,
                        expected={"prepared"},
                        state="submitting",
                        event_type="submission_started",
                        lease_seconds=policy["lease_seconds"],
                    )
                    prepared = self._read_json(job_root / "prepared_request.json")
                    assert prepared is not None
                    try:
                        operation = adapter.submit(
                            prepared,
                            idempotency_key=snapshot["idempotency_key"],
                        )
                    except AdapterError as error:
                        target = (
                            "submission_unknown"
                            if error.submission_uncertain or error.retryable
                            else "failed"
                        )
                        return self._error(
                            job_id, policy, snapshot, error, state=target
                        )
                    self._write_json_once(job_root / "submit_response.json", operation)
                    self._hook("after_submit_receipt_capture", snapshot)
                    snapshot = self.journal.transition(
                        job_id,
                        self.worker_id,
                        expected={"submitting"},
                        state="submitted",
                        event_type="submitted",
                        payload={"operation_id": operation.get("operation_id")},
                        operation=operation,
                        lease_seconds=policy["lease_seconds"],
                    )
                    self._hook("after_submission_persisted", snapshot)
                    continue
                if state == "submitting":
                    recovered = self._read_json(job_root / "submit_response.json")
                    if recovered is None:
                        return self._error(
                            job_id,
                            policy,
                            snapshot,
                            RuntimeError(
                                "submission may have reached the provider but no operation receipt exists"
                            ),
                            state="submission_unknown",
                        )
                    snapshot = self.journal.transition(
                        job_id,
                        self.worker_id,
                        expected={"submitting"},
                        state="submitted",
                        event_type="submission_receipt_recovered",
                        payload={"operation_id": recovered.get("operation_id")},
                        operation=recovered,
                        lease_seconds=policy["lease_seconds"],
                    )
                    continue
                if state in {"submitted", "polling"}:
                    try:
                        completed = adapter.poll(snapshot["operation"])
                    except AdapterError as error:
                        if (
                            error.retryable
                            and snapshot["retry_count"] < policy["max_safe_retries"]
                        ):
                            snapshot = self.journal.transition(
                                job_id,
                                self.worker_id,
                                expected={state},
                                state="polling",
                                event_type="poll_retry",
                                payload={"code": error.code, "message": str(error)},
                                retry_increment=1,
                                lease_seconds=policy["lease_seconds"],
                            )
                            self.sleep_fn(policy["poll_interval_seconds"])
                            continue
                        return self._error(job_id, policy, snapshot, error)
                    poll_number = snapshot["poll_count"] + 1
                    self._write_json_once(
                        job_root / "poll" / f"{poll_number:06d}.json", completed
                    )
                    if completed["status"] == "pending":
                        snapshot = self.journal.transition(
                            job_id,
                            self.worker_id,
                            expected={state},
                            state="polling",
                            event_type="polled",
                            payload={"status": "pending", "poll": poll_number},
                            poll_increment=1,
                            lease_seconds=policy["lease_seconds"],
                        )
                        self.sleep_fn(policy["poll_interval_seconds"])
                        continue
                    if completed["status"] == "failed":
                        return self._error(
                            job_id,
                            policy,
                            snapshot,
                            RuntimeError("provider operation completed with an error"),
                        )
                    if completed["status"] != "succeeded":
                        return self._error(
                            job_id,
                            policy,
                            snapshot,
                            AdapterError(
                                "provider returned an unrecognized operation status",
                                code="invalid_response",
                            ),
                        )
                    self._write_json_once(job_root / "completed_response.json", completed)
                    snapshot = self.journal.transition(
                        job_id,
                        self.worker_id,
                        expected={state},
                        state="retrieving",
                        event_type="provider_completed",
                        payload={"poll": poll_number},
                        completion=completed,
                        poll_increment=1,
                        lease_seconds=policy["lease_seconds"],
                    )
                    continue
                if state == "retrieving":
                    try:
                        artifacts = adapter.retrieve(
                            snapshot["completion"], job_root / "artifacts"
                        )
                    except AdapterError as error:
                        if (
                            error.retryable
                            and snapshot["retry_count"] < policy["max_safe_retries"]
                        ):
                            snapshot = self.journal.transition(
                                job_id,
                                self.worker_id,
                                expected={"retrieving"},
                                state="retrieving",
                                event_type="retrieve_retry",
                                payload={"code": error.code, "message": str(error)},
                                retry_increment=1,
                                lease_seconds=policy["lease_seconds"],
                            )
                            self.sleep_fn(policy["poll_interval_seconds"])
                            continue
                        return self._error(job_id, policy, snapshot, error)
                    result = adapter.normalize(
                        job=snapshot["job"],
                        build=build,
                        operation=snapshot["operation"],
                        completed=snapshot["completion"],
                        artifacts=artifacts,
                    )
                    result["completed_at"] = self.journal.iso_time()
                    validate_runtime_instance("render_result", result, self.root)
                    if len(result["artifacts"]) != result["expected_media"]["sample_count"]:
                        raise JournalError(
                            "provider artifact count does not match the compiled sample count"
                        )
                    for artifact in result["artifacts"]:
                        path = job_root / artifact["relative_path"]
                        if (
                            not path.is_file()
                            or path.stat().st_size != artifact["size_bytes"]
                            or sha256_bytes(path.read_bytes()) != artifact["sha256"]
                        ):
                            raise JournalError(
                                f"normalized render artifact is not hash-bound: {path.name}"
                            )
                    self._write_json_once(job_root / "render_result.json", result)
                    return self.journal.transition(
                        job_id,
                        self.worker_id,
                        expected={"retrieving"},
                        state="succeeded",
                        event_type="succeeded",
                        payload={
                            "artifacts": [row["sha256"] for row in result["artifacts"]]
                        },
                        result=result,
                        lease_seconds=policy["lease_seconds"],
                    )
                raise JournalError(f"render runner cannot handle state: {state}")
        except RunnerCrash:
            release = False
            raise
        except Exception as error:
            current = self.journal.get(job_id)
            if current["state"] not in TERMINAL_STATES and current["state"] != "submission_unknown":
                return self._error(job_id, policy, current, error)
            return current
        finally:
            if release:
                self.journal.release(job_id, self.worker_id)

    def reconcile(self, job_id: str, operation: dict[str, Any]) -> dict[str, Any]:
        snapshot = self.journal.get(job_id)
        policy = snapshot["job"]["policy"]
        self.journal.claim(job_id, self.worker_id, policy["lease_seconds"])
        try:
            self._write_json_once(
                self._job_root(job_id) / "submit_response.json", operation
            )
            return self.journal.reconcile_operation(
                job_id, self.worker_id, operation, policy["lease_seconds"]
            )
        finally:
            self.journal.release(job_id, self.worker_id)

    def cancel(self, job_id: str) -> dict[str, Any]:
        snapshot = self.journal.get(job_id)
        if snapshot["state"] in TERMINAL_STATES:
            return snapshot
        if snapshot["state"] == "submission_unknown":
            return snapshot
        policy = snapshot["job"]["policy"]
        snapshot = self.journal.claim(job_id, self.worker_id, policy["lease_seconds"])
        try:
            if snapshot["operation"] is None and snapshot["state"] == "submitting":
                return self.journal.transition(
                    job_id,
                    self.worker_id,
                    expected={"submitting"},
                    state="submission_unknown",
                    event_type="cancel_blocked_by_unknown_submission",
                    payload={
                        "warning": "Cannot prove whether the provider accepted the submission."
                    },
                    lease_seconds=policy["lease_seconds"],
                )
            if snapshot["operation"] is None:
                return self.journal.transition(
                    job_id,
                    self.worker_id,
                    expected={snapshot["state"]},
                    state="cancelled",
                    event_type="cancelled_before_submission",
                    lease_seconds=policy["lease_seconds"],
                )
            outcome = self.adapters[snapshot["adapter"]].cancel(snapshot["operation"])
            state = "cancelled" if outcome.get("supported") else "cancel_unsupported"
            return self.journal.transition(
                job_id,
                self.worker_id,
                expected={snapshot["state"]},
                state=state,
                event_type=state,
                payload=outcome,
                lease_seconds=policy["lease_seconds"],
            )
        finally:
            self.journal.release(job_id, self.worker_id)


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--journal", type=Path, default=REPO_ROOT / "work/render_jobs/jobs.sqlite3"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    create = sub.add_parser("create")
    create.add_argument("build_dir", type=Path)
    create.add_argument("--idempotency-key", required=True)
    for command in ("run", "resume", "cancel", "show", "events"):
        item = sub.add_parser(command)
        item.add_argument("job_id")
    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("job_id")
    reconcile.add_argument("operation", type=Path)
    args = parser.parse_args(argv)
    if args.command == "validate":
        print(json.dumps(validate_runtime_configuration(), sort_keys=True))
        return
    journal = JobJournal(args.journal)
    runner = RenderRunner(journal)
    if args.command == "create":
        result = runner.register(
            make_render_job(args.build_dir, idempotency_key=args.idempotency_key)
        )
    elif args.command in {"run", "resume"}:
        result = runner.run(args.job_id)
    elif args.command == "cancel":
        result = runner.cancel(args.job_id)
    elif args.command == "reconcile":
        result = runner.reconcile(args.job_id, _read_object(args.operation))
    elif args.command == "events":
        result = {"job_id": args.job_id, "events": journal.events(args.job_id)}
    else:
        result = journal.get(args.job_id)
    print(json.dumps(redact(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
