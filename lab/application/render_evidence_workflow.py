"""Journal one sealed experiment arm from render submission to immutable evidence."""

from __future__ import annotations

import copy
import fcntl
import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from lab.compiler.build import load_validated_build_directory
from lab.compiler.provenance import sha256_value
from lab.runtime.journal import redact
from lab.second_brain.src.validate import (
    REPO_ROOT,
    ValidationFailure,
    canonical_json_bytes,
    read_jsonl,
)

from .contracts import validate_application_instance


WORKFLOW_POLICY = "cpcs-render-evidence-workflow/1.0"
WORKFLOW_SCHEMA = "cpcs.render_evidence_workflow_state/1.0"
STEP_RESULT_SCHEMA = "cpcs.render_evidence_workflow_step_result/1.0"
WORKFLOW_ID = re.compile(r"^workflow_[0-9a-f]{24}$")
STEP_OPERATIONS = {
    "cpcs.render.create",
    "cpcs.render.run",
    "cpcs.render.show",
    "cpcs.render.cancel",
    "cpcs.verify.asset.prepare",
    "cpcs.verify.analysis.prepare",
    "cpcs.analyze.run",
    "cpcs.measure.pose.prepare",
    "cpcs.measure.pose.run",
    "cpcs.record.measurement",
    "cpcs.measure.normalize",
    "cpcs.verify.run",
    "cpcs.record.testimonial.capture",
    "cpcs.record.testimonial.review",
    "cpcs.record.render",
}

Executor = Callable[[str, dict[str, Any]], dict[str, Any]]
CrashHook = Callable[[str, dict[str, Any]], None]


class WorkflowCrash(RuntimeError):
    """Test hook equivalent of process death after a durable child receipt."""


def _state_hash(state: dict[str, Any]) -> str:
    return sha256_value({key: value for key, value in state.items() if key != "state_hash"})


def _event_hash(event: dict[str, Any]) -> str:
    return sha256_value({key: value for key, value in event.items() if key != "event_hash"})


def _step(
    *,
    index: int,
    kind: str,
    operation: str,
    arguments: dict[str, Any],
    request_hash: str,
) -> dict[str, Any]:
    if operation not in STEP_OPERATIONS:
        raise ValidationFailure(f"workflow operation is not allowed: {operation}")
    arguments_hash = sha256_value(arguments)
    step_hash = sha256_value(
        {
            "policy": WORKFLOW_POLICY,
            "request_hash": request_hash,
            "index": index,
            "kind": kind,
            "operation": operation,
            "arguments_hash": arguments_hash,
        }
    )
    return {
        "index": index,
        "kind": kind,
        "operation": operation,
        "arguments": copy.deepcopy(arguments),
        "arguments_hash": arguments_hash,
        "step_hash": step_hash,
    }


class RenderEvidenceWorkflow:
    """Content-bound file journal around existing application operation handlers."""

    def __init__(
        self,
        *,
        executor: Executor,
        build_path: Callable[[str], Path],
        root: Path = REPO_ROOT,
        work_root: Path | None = None,
        crash_hook: CrashHook | None = None,
    ) -> None:
        self.executor = executor
        self.build_path = build_path
        self.root = root
        self.work_root = (
            work_root or root / "work" / "application" / "render_evidence_workflows"
        ).expanduser().resolve()
        expected_work = (root / "work").resolve()
        if expected_work not in self.work_root.parents:
            raise ValidationFailure("workflow root escaped work/")
        self.work_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.work_root, 0o700)
        self.crash_hook = crash_hook

    def _directory(self, workflow_id: str, *, create: bool = False) -> Path:
        if not WORKFLOW_ID.fullmatch(workflow_id):
            raise ValidationFailure("render evidence workflow ID is invalid")
        path = (self.work_root / workflow_id).resolve()
        if self.work_root not in path.parents:
            raise ValidationFailure("workflow directory escaped work root")
        if create:
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(path, 0o700)
        elif not path.is_dir() or path.is_symlink():
            raise ValidationFailure(f"render evidence workflow does not exist: {workflow_id}")
        return path

    @contextmanager
    def _lock(self, workflow_id: str, *, create: bool = False) -> Iterator[Path]:
        directory = self._directory(workflow_id, create=create)
        lock_path = directory / ".lock"
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.chmod(lock_path, 0o600)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValidationFailure(
                    f"render evidence workflow is busy: {workflow_id}"
                ) from exc
            yield directory
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    @staticmethod
    def _write_once(path: Path, value: dict[str, Any]) -> None:
        data = canonical_json_bytes(value)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.exists():
            if path.is_symlink() or path.read_bytes() != data:
                raise ValidationFailure(f"workflow artifact collision: {path.name}")
            return
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            os.chmod(path, 0o600)
        finally:
            if temporary.exists():
                temporary.unlink()

    @staticmethod
    def _replace(path: Path, value: dict[str, Any]) -> None:
        data = canonical_json_bytes(value)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            os.chmod(path, 0o600)
        finally:
            if temporary.exists():
                temporary.unlink()

    @staticmethod
    def _read_object(path: Path, label: str) -> dict[str, Any]:
        if path.is_symlink() or not path.is_file():
            raise ValidationFailure(f"workflow {label} is missing or unsafe")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationFailure(f"workflow {label} is invalid JSON") from exc
        if not isinstance(value, dict):
            raise ValidationFailure(f"workflow {label} must be an object")
        if path.read_bytes() != canonical_json_bytes(value):
            raise ValidationFailure(f"workflow {label} is not canonical JSON")
        return value

    def _verify_flight_and_build(self, request: dict[str, Any]) -> dict[str, Any]:
        flights = {
            row["id"]: row
            for row in read_jsonl(
                self.root
                / "lab"
                / "second_brain"
                / "immutable"
                / "flights.jsonl"
            )
        }
        flight = flights.get(request["flight_id"])
        if flight is None or flight.get("legacy") is not None:
            raise ValidationFailure(
                f"workflow requires a sealed nonlegacy flight: {request['flight_id']}"
            )
        arm = next(
            (row for row in flight["arms"] if row["id"] == request["arm_id"]),
            None,
        )
        if arm is None:
            raise ValidationFailure(
                f"workflow flight has no arm: {request['arm_id']}"
            )
        directory = self.build_path(request["build_id"])
        build = load_validated_build_directory(directory, self.root)
        manifest = build["manifest"]
        if (
            manifest["concept_ids"] != flight["concept_ids"]
            or manifest["concept_hashes"] != flight["concept_content_hashes"]
            or manifest["seed"] != flight["seed"]
            or manifest["compiler_version"] != flight["compiler_settings"]["version"]
        ):
            raise ValidationFailure("workflow build differs from the sealed flight")
        controls = {
            row["control_id"]: row["value"]
            for row in build["score"]["provider_neutral_controls"]
        }
        delta = arm.get("tested_delta")
        if delta is not None and controls.get(delta["control_id"]) != delta["value"]:
            raise ValidationFailure("workflow build does not realize the sealed arm delta")
        sealed_metrics = set(flight["design"]["metric_ids"])
        supplied_metrics = set(request["metrics"])
        missing_metrics = sorted(sealed_metrics - supplied_metrics)
        extra_metrics = sorted(supplied_metrics - sealed_metrics)
        if missing_metrics or extra_metrics:
            details = []
            if missing_metrics:
                details.append("missing=" + ",".join(missing_metrics))
            if extra_metrics:
                details.append("extra=" + ",".join(extra_metrics))
            raise ValidationFailure(
                "workflow metrics must exactly match sealed requirements: "
                + "; ".join(details)
            )
        parameters = build["provider_request"]["body"]["parameters"]
        if parameters["sampleCount"] != 1:
            raise ValidationFailure("render evidence workflow requires one output sample")
        return {
            "build_dir": str(directory),
            "duration_seconds": parameters["durationSeconds"],
        }

    def _validate_state(self, state: dict[str, Any], directory: Path) -> None:
        validate_application_instance("render_evidence_workflow_state", state, self.root)
        if state["state_hash"] != _state_hash(state):
            raise ValidationFailure("workflow state hash is invalid")
        request = self._read_object(directory / "request.json", "request")
        validate_application_instance(
            "render_evidence_workflow_request", request, self.root
        )
        if state["request_hash"] != sha256_value(request):
            raise ValidationFailure("workflow request hash is invalid")
        prior = None
        for sequence, event in enumerate(state["events"], 1):
            if event["sequence"] != sequence or event["previous_hash"] != prior:
                raise ValidationFailure("workflow event sequence is invalid")
            if event["event_hash"] != _event_hash(event):
                raise ValidationFailure("workflow event hash is invalid")
            if event["result_path"] is not None:
                candidate = (directory / event["result_path"]).resolve()
                if directory not in candidate.parents:
                    raise ValidationFailure("workflow event result escaped its directory")
                artifact = self._read_object(candidate, "step result")
                if (
                    artifact.get("schema") != STEP_RESULT_SCHEMA
                    or artifact.get("workflow_id") != state["workflow_id"]
                    or artifact.get("result_hash") != event["result_hash"]
                    or sha256_value(artifact.get("result")) != event["result_hash"]
                ):
                    raise ValidationFailure("workflow step result hash is invalid")
            prior = event["event_hash"]
        if state["event_head"] != prior:
            raise ValidationFailure("workflow event head is invalid")
        next_step = state["next_step"]
        if next_step is not None:
            expected = _step(
                index=next_step["index"],
                kind=next_step["kind"],
                operation=next_step["operation"],
                arguments=next_step["arguments"],
                request_hash=state["request_hash"],
            )
            if expected != next_step or next_step["index"] != state["step_index"]:
                raise ValidationFailure("workflow next step identity is invalid")

    def _load(self, workflow_id: str, directory: Path | None = None) -> dict[str, Any]:
        directory = directory or self._directory(workflow_id)
        state = self._read_object(directory / "state.json", "state")
        if state.get("workflow_id") != workflow_id:
            raise ValidationFailure("workflow state belongs to another workflow")
        self._validate_state(state, directory)
        return state

    @staticmethod
    def _append_event(
        state: dict[str, Any],
        *,
        event_type: str,
        state_before: str,
        state_after: str,
        step_hash: str | None,
        operation: str | None,
        result_hash: str | None,
        result_path: str | None,
    ) -> None:
        event = {
            "sequence": len(state["events"]) + 1,
            "event_type": event_type,
            "state_before": state_before,
            "state_after": state_after,
            "step_hash": step_hash,
            "operation": operation,
            "result_hash": result_hash,
            "result_path": result_path,
            "previous_hash": state["event_head"],
        }
        event["event_hash"] = _event_hash(event)
        state["events"].append(event)
        state["event_head"] = event["event_hash"]

    def _set_next(
        self,
        state: dict[str, Any],
        *,
        kind: str,
        operation: str,
        arguments: dict[str, Any],
        runtime_state: str = "ready",
    ) -> None:
        state["next_step"] = _step(
            index=state["step_index"],
            kind=kind,
            operation=operation,
            arguments=arguments,
            request_hash=state["request_hash"],
        )
        state["state"] = runtime_state

    def _verification_step(self, state: dict[str, Any]) -> None:
        observations = [
            *state["context"].get("semantic_observations", []),
            *state["context"].get("measurement_observations", []),
        ]
        self._set_next(
            state,
            kind="verify_render",
            operation="cpcs.verify.run",
            arguments={
                "build_id": state["context"]["build_id"],
                "job_id": state["context"]["render_job_id"],
                "artifact_id": state["context"]["artifact_id"],
                "observations": observations,
            },
        )

    def prepare(self, request: dict[str, Any]) -> dict[str, Any]:
        request = copy.deepcopy(request)
        validate_application_instance(
            "render_evidence_workflow_request", request, self.root
        )
        request_hash = sha256_value(request)
        workflow_id = "workflow_" + request_hash.removeprefix("sha256:")[:24]
        with self._lock(workflow_id, create=True) as directory:
            request_path = directory / "request.json"
            if request_path.exists():
                existing = self._read_object(request_path, "request")
                if existing != request:
                    raise ValidationFailure("workflow ID collides with another request")
                return self._public(self._load(workflow_id, directory))
            build_context = self._verify_flight_and_build(request)
            self._write_once(request_path, request)
            render_arguments = {
                "build_id": request["build_id"],
                **copy.deepcopy(request["render"]),
            }
            state = {
                "schema": WORKFLOW_SCHEMA,
                "workflow_id": workflow_id,
                "request_hash": request_hash,
                "state": "ready",
                "step_index": 0,
                "next_step": _step(
                    index=0,
                    kind="render_create",
                    operation="cpcs.render.create",
                    arguments=render_arguments,
                    request_hash=request_hash,
                ),
                "last_completed_step_hash": None,
                "context": {
                    "flight_id": request["flight_id"],
                    "arm_id": request["arm_id"],
                    "build_id": request["build_id"],
                    "build_dir": build_context["build_dir"],
                    "artifact_id": request["artifact_id"],
                    "rights_scope": request["rights_scope"],
                    "duration_seconds": build_context["duration_seconds"],
                    "metrics": copy.deepcopy(request["metrics"]),
                    "measurement": copy.deepcopy(request["measurement"]),
                    "semantic_observations": [],
                    "measurement_observations": [],
                },
                "review": None,
                "events": [],
                "event_head": None,
                "result": None,
                "state_hash": "",
            }
            state["state_hash"] = _state_hash(state)
            validate_application_instance(
                "render_evidence_workflow_state", state, self.root
            )
            self._replace(directory / "state.json", state)
            return self._public(state)

    def _result_path(self, directory: Path, step: dict[str, Any]) -> Path:
        return (
            directory
            / "steps"
            / f"{step['index']:03d}_{step['step_hash'].removeprefix('sha256:')[:16]}.json"
        )

    def _step_result(
        self,
        state: dict[str, Any],
        directory: Path,
        step: dict[str, Any],
    ) -> tuple[dict[str, Any], Path]:
        path = self._result_path(directory, step)
        if path.exists():
            artifact = self._read_object(path, "step result")
            if (
                artifact.get("schema") != STEP_RESULT_SCHEMA
                or artifact.get("workflow_id") != state["workflow_id"]
                or artifact.get("step_hash") != step["step_hash"]
                or artifact.get("operation") != step["operation"]
                or artifact.get("arguments_hash") != step["arguments_hash"]
                or artifact.get("result_hash") != sha256_value(artifact.get("result"))
            ):
                raise ValidationFailure("workflow step result is invalid")
            return copy.deepcopy(artifact["result"]), path
        result = self.executor(step["operation"], copy.deepcopy(step["arguments"]))
        if not isinstance(result, dict):
            raise ValidationFailure("workflow child operation returned a non-object")
        artifact = {
            "schema": STEP_RESULT_SCHEMA,
            "workflow_id": state["workflow_id"],
            "step_index": step["index"],
            "step_hash": step["step_hash"],
            "operation": step["operation"],
            "arguments_hash": step["arguments_hash"],
            "result": copy.deepcopy(result),
            "result_hash": sha256_value(result),
        }
        self._write_once(path, artifact)
        if self.crash_hook is not None:
            self.crash_hook("after_step_result", copy.deepcopy(artifact))
        return result, path

    def _apply(self, state: dict[str, Any], step: dict[str, Any], result: dict[str, Any]) -> None:
        context = state["context"]
        kind = step["kind"]
        state["step_index"] += 1
        state["next_step"] = None
        state["last_completed_step_hash"] = step["step_hash"]
        if kind == "render_create":
            context["render_job_id"] = result["job"]["job_id"]
            self._set_next(
                state,
                kind="render_run",
                operation="cpcs.render.run",
                arguments={"job_id": context["render_job_id"]},
            )
            return
        if kind in {"render_run", "render_refresh"}:
            render_state = result["state"]
            if render_state == "succeeded":
                artifacts = [
                    row
                    for row in result["result"]["artifacts"]
                    if row["artifact_id"] == context["artifact_id"]
                ]
                if len(artifacts) != 1:
                    raise ValidationFailure(
                        "workflow render result does not contain its selected artifact"
                    )
                context["artifact"] = copy.deepcopy(artifacts[0])
                render_root = (
                    self.root
                    / "work"
                    / "application"
                    / "render"
                    / "jobs"
                    / context["render_job_id"]
                ).resolve()
                context["render_result"] = str(render_root / "render_result.json")
                context["artifact_path"] = str(
                    (render_root / artifacts[0]["relative_path"]).resolve()
                )
                self._set_next(
                    state,
                    kind="asset_prepare",
                    operation="cpcs.verify.asset.prepare",
                    arguments={
                        "build_id": context["build_id"],
                        "job_id": context["render_job_id"],
                        "artifact_id": context["artifact_id"],
                        "rights_scope": context["rights_scope"],
                    },
                )
                return
            if render_state == "submission_unknown":
                self._set_next(
                    state,
                    kind="render_refresh",
                    operation="cpcs.render.show",
                    arguments={"job_id": context["render_job_id"]},
                    runtime_state="waiting_reconciliation",
                )
                return
            if render_state in {
                "queued", "validated", "prepared", "submitting", "submitted",
                "polling", "retrieving"
            }:
                self._set_next(
                    state,
                    kind="render_run",
                    operation="cpcs.render.run",
                    arguments={"job_id": context["render_job_id"]},
                )
                return
            state["state"] = "failed"
            state["result"] = {
                "failure_stage": "render",
                "render_state": render_state,
                "error": copy.deepcopy(result.get("error")),
            }
            return
        if kind == "asset_prepare":
            self._set_next(
                state,
                kind="asset_upload",
                operation="cpcs.analyze.run",
                arguments={"job": copy.deepcopy(result["job"])},
            )
            return
        if kind == "asset_upload":
            context["provider_asset_ref"] = result["asset"]["id"]
            self._set_next(
                state,
                kind="analysis_prepare",
                operation="cpcs.verify.analysis.prepare",
                arguments={
                    "build_id": context["build_id"],
                    "job_id": context["render_job_id"],
                    "artifact_id": context["artifact_id"],
                    "provider_asset_ref": context["provider_asset_ref"],
                    "rights_scope": context["rights_scope"],
                },
            )
            return
        if kind == "analysis_prepare":
            self._set_next(
                state,
                kind="analysis_run",
                operation="cpcs.analyze.run",
                arguments={"job": copy.deepcopy(result["job"])},
            )
            return
        if kind == "analysis_run":
            context["semantic_observations"] = copy.deepcopy(result["observations"])
            measurement = context["measurement"]
            if measurement is None:
                self._verification_step(state)
                return
            pose_arguments = {
                "source_id": context["artifact_id"],
                "asset_ref": context["artifact_id"],
                "local_path": context["artifact_path"],
                "rights_scope": context["rights_scope"],
                "authorized_interval": {
                    "start_s": 0.0,
                    "end_s": float(context["duration_seconds"]),
                },
                **copy.deepcopy(measurement),
            }
            self._set_next(
                state,
                kind="measurement_prepare",
                operation="cpcs.measure.pose.prepare",
                arguments=pose_arguments,
            )
            return
        if kind == "measurement_prepare":
            self._set_next(
                state,
                kind="measurement_run",
                operation="cpcs.measure.pose.run",
                arguments={"job": copy.deepcopy(result)},
            )
            return
        if kind == "measurement_run":
            context["measurement_batch"] = copy.deepcopy(result["batch"])
            self._set_next(
                state,
                kind="measurement_record",
                operation="cpcs.record.measurement",
                arguments={"batch": copy.deepcopy(result["batch"])},
            )
            return
        if kind == "measurement_record":
            observation_ids = sorted(row["id"] for row in result["records"])
            context["measurement_observation_ids"] = observation_ids
            batch = context["measurement_batch"]
            self._set_next(
                state,
                kind="measurement_normalize",
                operation="cpcs.measure.normalize",
                arguments={
                    "source": copy.deepcopy(batch["source"]),
                    "authorized_interval": copy.deepcopy(batch["authorized_interval"]),
                    "measurement_observation_ids": observation_ids,
                },
            )
            return
        if kind == "measurement_normalize":
            context["measurement_observations"] = copy.deepcopy(result["observations"])
            self._verification_step(state)
            return
        if kind == "verify_render":
            context["compliance_report"] = result["output"]
            context["compliance_report_id"] = result["report"]["report_id"]
            context["compliance_status"] = result["report"]["overall_status"]
            context["compliance_metric_statuses"] = [
                {
                    "metric_id": row["metric_id"],
                    "status": row["status"],
                }
                for row in sorted(
                    result["report"]["control_checks"],
                    key=lambda row: row["metric_id"],
                )
            ]
            state["state"] = "awaiting_review"
            return
        if kind == "testimonial_capture":
            context["testimonial_id"] = result["id"]
            review = state["review"]
            self._set_next(
                state,
                kind="testimonial_review",
                operation="cpcs.record.testimonial.review",
                arguments={
                    "request": {
                        "schema": "cpcs.testimonial_review_request/1.0",
                        "testimonial_id": context["testimonial_id"],
                        "normalization": copy.deepcopy(review["normalization"]),
                        "reviewed_by": review["reviewed_by"],
                        "reviewed_at": review["reviewed_at"],
                        "supersedes_reviews": [],
                    }
                },
            )
            return
        if kind == "testimonial_review":
            context["testimonial_review_id"] = result["id"]
            human_review = copy.deepcopy(state["review"]["human_review"])
            human_review["testimonial_review_id"] = result["id"]
            self._set_next(
                state,
                kind="record_run",
                operation="cpcs.record.render",
                arguments={
                    "receipt": {
                        "schema": "cpcs.experiment_receipt/1.0",
                        "flight_id": context["flight_id"],
                        "arm_id": context["arm_id"],
                        "build_dir": context["build_dir"],
                        "render_result": context["render_result"],
                        "compliance_report": context["compliance_report"],
                        "artifact_id": context["artifact_id"],
                        "metrics": copy.deepcopy(context["metrics"]),
                        "human_review": human_review,
                    }
                },
            )
            return
        if kind == "record_run":
            context["run_id"] = result["id"]
            state["state"] = "completed"
            state["result"] = {
                "run_id": result["id"],
                "run_record_hash": result["record_hash"],
                "flight_id": context["flight_id"],
                "arm_id": context["arm_id"],
                "build_id": context["build_id"],
                "render_job_id": context["render_job_id"],
                "artifact_id": context["artifact_id"],
                "compliance_report_id": context["compliance_report_id"],
                "testimonial_id": context["testimonial_id"],
                "testimonial_review_id": context["testimonial_review_id"],
            }
            return
        raise ValidationFailure(f"workflow cannot apply step kind: {kind}")

    def advance(self, workflow_id: str, expected_step_hash: str) -> dict[str, Any]:
        with self._lock(workflow_id) as directory:
            state = self._load(workflow_id, directory)
            if expected_step_hash == state["last_completed_step_hash"]:
                return self._public(state)
            step = state["next_step"]
            if step is None:
                raise ValidationFailure(
                    f"workflow has no executable step while {state['state']}"
                )
            if expected_step_hash != step["step_hash"]:
                raise ValidationFailure("workflow advance targets a stale or different step")
            before = state["state"]
            try:
                result, result_path = self._step_result(state, directory, step)
                self._apply(state, step, result)
                relative = str(result_path.relative_to(directory))
                self._append_event(
                    state,
                    event_type="step_completed",
                    state_before=before,
                    state_after=state["state"],
                    step_hash=step["step_hash"],
                    operation=step["operation"],
                    result_hash=sha256_value(result),
                    result_path=relative,
                )
                state["state_hash"] = _state_hash(state)
                validate_application_instance(
                    "render_evidence_workflow_state", state, self.root
                )
                self._replace(directory / "state.json", state)
                return self._public(state)
            except WorkflowCrash:
                raise
            except Exception as exc:
                if state["last_completed_step_hash"] != step["step_hash"]:
                    failure = redact(
                        {"type": type(exc).__name__, "message": str(exc)}
                    )
                    failure_path = directory / "steps" / f"{step['index']:03d}_failure.json"
                    failure_artifact = {
                        "schema": STEP_RESULT_SCHEMA,
                        "workflow_id": workflow_id,
                        "step_index": step["index"],
                        "step_hash": step["step_hash"],
                        "operation": step["operation"],
                        "arguments_hash": step["arguments_hash"],
                        "result": failure,
                        "result_hash": sha256_value(failure),
                    }
                    self._write_once(failure_path, failure_artifact)
                    state["state"] = "failed"
                    state["next_step"] = None
                    state["result"] = {"failure": failure, "step_hash": step["step_hash"]}
                    self._append_event(
                        state,
                        event_type="failed",
                        state_before=before,
                        state_after="failed",
                        step_hash=step["step_hash"],
                        operation=step["operation"],
                        result_hash=sha256_value(failure),
                        result_path=str(failure_path.relative_to(directory)),
                    )
                    state["state_hash"] = _state_hash(state)
                    self._replace(directory / "state.json", state)
                raise

    def supply_review(
        self, workflow_id: str, expected_state_hash: str, review: dict[str, Any]
    ) -> dict[str, Any]:
        review = copy.deepcopy(review)
        validate_application_instance(
            "render_evidence_workflow_review", review, self.root
        )
        with self._lock(workflow_id) as directory:
            state = self._load(workflow_id, directory)
            review_hash = sha256_value(review)
            if state["review"] is not None:
                if sha256_value(state["review"]) != review_hash:
                    raise ValidationFailure("workflow review is immutable after supply")
                return self._public(state)
            if expected_state_hash != state["state_hash"]:
                raise ValidationFailure("workflow review targets stale state")
            if state["state"] != "awaiting_review" or state["next_step"] is not None:
                raise ValidationFailure("workflow is not awaiting human review")
            before = state["state"]
            state["review"] = review
            state["step_index"] += 1
            self._set_next(
                state,
                kind="testimonial_capture",
                operation="cpcs.record.testimonial.capture",
                arguments={
                    "request": {
                        "schema": "cpcs.human_testimonial_capture/1.0",
                        "render_result": state["context"]["render_result"],
                        "artifact_id": state["context"]["artifact_id"],
                        "speaker": copy.deepcopy(review["speaker"]),
                        "language": review["language"],
                        "raw_statement": review["raw_statement"],
                        "captured_at": review["captured_at"],
                        "supersedes": [],
                    }
                },
            )
            self._append_event(
                state,
                event_type="review_supplied",
                state_before=before,
                state_after=state["state"],
                step_hash=None,
                operation=None,
                result_hash=review_hash,
                result_path=None,
            )
            state["state_hash"] = _state_hash(state)
            validate_application_instance(
                "render_evidence_workflow_state", state, self.root
            )
            self._replace(directory / "state.json", state)
            return self._public(state)

    def cancel(self, workflow_id: str, expected_state_hash: str) -> dict[str, Any]:
        with self._lock(workflow_id) as directory:
            state = self._load(workflow_id, directory)
            if state["state"] == "cancelled":
                artifact = self._read_object(directory / "cancel.json", "cancellation")
                expected_keys = {
                    "schema", "workflow_id", "step_index", "step_hash", "operation",
                    "arguments_hash", "result", "result_hash",
                }
                if (
                    set(artifact) != expected_keys
                    or artifact["schema"] != STEP_RESULT_SCHEMA
                    or artifact["workflow_id"] != workflow_id
                    or artifact["step_hash"] != expected_state_hash
                    or artifact["operation"] not in {None, "cpcs.render.cancel"}
                    or artifact["result_hash"] != sha256_value(artifact["result"])
                ):
                    raise ValidationFailure("workflow cancellation replay is not exact")
                return self._public(state)
            if state["state"] == "completed":
                raise ValidationFailure("completed workflow cannot be cancelled")
            if expected_state_hash != state["state_hash"]:
                raise ValidationFailure("workflow cancellation targets stale state")
            before = state["state"]
            job_id = state["context"].get("render_job_id")
            if job_id is None:
                outcome = {"disposition": "cancelled_before_render_registration"}
                operation = None
            else:
                outcome = self.executor("cpcs.render.cancel", {"job_id": job_id})
                operation = "cpcs.render.cancel"
            cancel_artifact = {
                "schema": STEP_RESULT_SCHEMA,
                "workflow_id": workflow_id,
                "step_index": state["step_index"],
                "step_hash": state["state_hash"],
                "operation": operation,
                "arguments_hash": sha256_value({"job_id": job_id}),
                "result": copy.deepcopy(outcome),
                "result_hash": sha256_value(outcome),
            }
            cancel_path = directory / "cancel.json"
            self._write_once(cancel_path, cancel_artifact)
            state["state"] = "cancelled"
            state["next_step"] = None
            state["result"] = {"cancellation": copy.deepcopy(outcome)}
            self._append_event(
                state,
                event_type="cancelled",
                state_before=before,
                state_after="cancelled",
                step_hash=None,
                operation=operation,
                result_hash=sha256_value(outcome),
                result_path=str(cancel_path.relative_to(directory)),
            )
            state["state_hash"] = _state_hash(state)
            validate_application_instance(
                "render_evidence_workflow_state", state, self.root
            )
            self._replace(directory / "state.json", state)
            return self._public(state)

    def status(self, workflow_id: str) -> dict[str, Any]:
        with self._lock(workflow_id) as directory:
            return self._public(self._load(workflow_id, directory))

    @staticmethod
    def _public(state: dict[str, Any]) -> dict[str, Any]:
        context = state["context"]
        next_step = state["next_step"]
        events = [
            {
                key: copy.deepcopy(value)
                for key, value in event.items()
                if key != "result_path"
            }
            for event in state["events"]
        ]
        value = {
            "schema": "cpcs.render_evidence_workflow_status/1.0",
            "policy_version": WORKFLOW_POLICY,
            "workflow_id": state["workflow_id"],
            "request_hash": state["request_hash"],
            "state": state["state"],
            "state_hash": state["state_hash"],
            "step_index": state["step_index"],
            "next_step": (
                None
                if next_step is None
                else {
                    key: copy.deepcopy(next_step[key])
                    for key in (
                        "index", "kind", "operation", "arguments_hash", "step_hash"
                    )
                }
            ),
            "last_completed_step_hash": state["last_completed_step_hash"],
            "lineage": {
                "flight_id": context["flight_id"],
                "arm_id": context["arm_id"],
                "build_id": context["build_id"],
                "render_job_id": context.get("render_job_id"),
                "artifact_id": context["artifact_id"],
                "provider_asset_ref": context.get("provider_asset_ref"),
                "compliance_report_id": context.get("compliance_report_id"),
                "testimonial_id": context.get("testimonial_id"),
                "testimonial_review_id": context.get("testimonial_review_id"),
                "run_id": context.get("run_id"),
            },
            "evidence_counts": {
                "semantic": len(context.get("semantic_observations", [])),
                "measurement": len(context.get("measurement_observations", [])),
            },
            "review_supplied": state["review"] is not None,
            "metric_requirements": {
                "sealed_metrics": [
                    {
                        "metric_id": metric_id,
                        "value": copy.deepcopy(context["metrics"][metric_id]),
                    }
                    for metric_id in sorted(context["metrics"])
                ],
                "compliance_checks": copy.deepcopy(
                    context.get("compliance_metric_statuses", [])
                ),
                "testimonial_rule": (
                    "Each sealed metric that is not exactly represented by a pass or fail "
                    "compliance status requires one quote-spanned normalization.metric_findings "
                    "entry with the same scalar value and a sealed concept or canonical-control target."
                ),
            },
            "events": events,
            "result": copy.deepcopy(state["result"]),
            "recovery": None,
        }
        if state["state"] == "waiting_reconciliation":
            value["recovery"] = {
                "operation": "cpcs.render.reconcile",
                "job_id": context.get("render_job_id"),
                "then": "advance the workflow using the newly reported step hash",
            }
        return value
