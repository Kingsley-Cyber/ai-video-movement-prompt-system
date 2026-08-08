"""Journal one exact reference and candidate through paired operational analysis."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from lab.compiler.provenance import sha256_value
from lab.runtime.journal import redact
from lab.second_brain.src.validate import (
    REPO_ROOT,
    ValidationFailure,
    canonical_json_bytes,
)

from .contracts import validate_application_instance


WORKFLOW_POLICY = "cpcs-video-comparison-workflow/1.0"
WORKFLOW_STATE_SCHEMA = "cpcs.video_comparison_workflow_state/1.0"
STEP_RESULT_SCHEMA = "cpcs.video_comparison_workflow_step_result/1.0"
WORKFLOW_ID = re.compile(r"^video_compare_[0-9a-f]{24}$")
STEP_OPERATIONS = {
    "cpcs.analyze.cascade",
    "cpcs.measure.pose.prepare",
    "cpcs.measure.pose.run",
    "cpcs.verify.reference.compare",
}

Executor = Callable[[str, dict[str, Any]], dict[str, Any]]
CrashHook = Callable[[str, dict[str, Any]], None]


class VideoComparisonWorkflowCrash(RuntimeError):
    """Test hook equivalent of process death after a durable child receipt."""


def _state_hash(state: dict[str, Any]) -> str:
    return sha256_value({key: value for key, value in state.items() if key != "state_hash"})


def _event_hash(event: dict[str, Any]) -> str:
    return sha256_value({key: value for key, value in event.items() if key != "event_hash"})


def _path_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _step(
    *,
    index: int,
    kind: str,
    operation: str,
    arguments: dict[str, Any],
    request_hash: str,
    plan_hash: str,
) -> dict[str, Any]:
    if operation not in STEP_OPERATIONS:
        raise ValidationFailure(f"video comparison operation is not allowed: {operation}")
    arguments_hash = sha256_value(arguments)
    step_hash = sha256_value(
        {
            "policy": WORKFLOW_POLICY,
            "request_hash": request_hash,
            "plan_hash": plan_hash,
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


class VideoComparisonWorkflow:
    """Content-bound file journal over paired registered analysis and verifier handlers."""

    def __init__(
        self,
        *,
        executor: Executor,
        root: Path = REPO_ROOT,
        work_root: Path | None = None,
        crash_hook: CrashHook | None = None,
    ) -> None:
        self.executor = executor
        self.root = root
        self.work_root = (
            work_root or root / "work" / "application" / "video_comparisons"
        ).expanduser().resolve()
        expected_work = (root / "work").resolve()
        if expected_work not in self.work_root.parents:
            raise ValidationFailure("video comparison root escaped work/")
        self.work_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.work_root, 0o700)
        self.crash_hook = crash_hook

    def _directory(self, workflow_id: str, *, create: bool = False) -> Path:
        if not WORKFLOW_ID.fullmatch(workflow_id):
            raise ValidationFailure("video comparison workflow ID is invalid")
        path = (self.work_root / workflow_id).resolve()
        if self.work_root not in path.parents:
            raise ValidationFailure("video comparison directory escaped work root")
        if create:
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(path, 0o700)
        elif not path.is_dir() or path.is_symlink():
            raise ValidationFailure(
                f"video comparison workflow does not exist: {workflow_id}"
            )
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
                    f"video comparison workflow is busy: {workflow_id}"
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
                raise ValidationFailure(f"video comparison artifact collision: {path.name}")
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
            raise ValidationFailure(f"video comparison {label} is missing or unsafe")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationFailure(f"video comparison {label} is invalid JSON") from exc
        if not isinstance(value, dict):
            raise ValidationFailure(f"video comparison {label} must be an object")
        if path.read_bytes() != canonical_json_bytes(value):
            raise ValidationFailure(f"video comparison {label} is not canonical JSON")
        return value

    @staticmethod
    def _atomic_request(
        side: dict[str, Any], analysis: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "schema": "cpcs.atomic_video_analysis_request/1.0",
            "source": copy.deepcopy(side["source"]),
            "authorized_interval": copy.deepcopy(side["authorized_interval"]),
            "mode": analysis["mode"],
            "domain_lenses": sorted(analysis["domain_lenses"]),
            "candidate_concepts": sorted(analysis["candidate_concepts"]),
            "measurement_observation_ids": [],
            "max_parallel_jobs": analysis["max_parallel_jobs"],
            "created_at": analysis["created_at"],
        }

    @staticmethod
    def _atomic_summary(plan: dict[str, Any]) -> dict[str, Any]:
        coverage = plan["coverage"]
        cascade = plan["cascade"]
        return {
            "plan_id": plan["plan_id"],
            "cascade_id": cascade["cascade_id"],
            "provider_call_count": plan["provider_call_count"],
            "semantic_profiles": sorted(coverage["semantic_profiles"]),
            "segment_profiles": sorted(coverage["segment_profiles"]),
            "analysis_window_policy": coverage["analysis_window_policy"],
            "policy_version": plan["policy_version"],
            "cascade_hash": sha256_value(cascade),
        }

    def _build_plan(
        self, request: dict[str, Any], request_hash: str
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        analysis = request["analysis"]
        reference_plan = self.executor(
            "cpcs.analyze.atomic.prepare",
            self._atomic_request(request["reference"], analysis),
        )
        candidate_plan = self.executor(
            "cpcs.analyze.atomic.prepare",
            self._atomic_request(request["candidate"], analysis),
        )
        reference_summary = self._atomic_summary(reference_plan)
        candidate_summary = self._atomic_summary(candidate_plan)
        reference_profiles = {
            "semantic": reference_summary["semantic_profiles"],
            "segment": reference_summary["segment_profiles"],
            "window": reference_summary["analysis_window_policy"],
        }
        candidate_profiles = {
            "semantic": candidate_summary["semantic_profiles"],
            "segment": candidate_summary["segment_profiles"],
            "window": candidate_summary["analysis_window_policy"],
        }
        if reference_profiles != candidate_profiles:
            raise ValidationFailure(
                "reference and candidate analysis plans do not use identical profiles"
            )
        planned_calls = (
            reference_plan["provider_call_count"]
            + candidate_plan["provider_call_count"]
        )
        maximum_calls = analysis["maximum_provider_calls"]
        if planned_calls > maximum_calls:
            raise ValidationFailure(
                f"paired analysis requires {planned_calls} provider calls, above the fixed maximum {maximum_calls}"
            )
        measurement = request["local_measurement"]
        step_kinds = ["reference_analysis", "candidate_analysis"]
        if measurement is not None:
            step_kinds.extend(
                [
                    "reference_measurement_prepare",
                    "reference_measurement_run",
                    "candidate_measurement_prepare",
                    "candidate_measurement_run",
                ]
            )
        step_kinds.append("compare")
        core = {
            "schema": "cpcs.video_comparison_workflow_plan/1.0",
            "request_hash": request_hash,
            "mode": request["mode"],
            "reference_analysis": reference_summary,
            "candidate_analysis": candidate_summary,
            "paired_profile_hash": sha256_value(reference_profiles),
            "provider_calls": {
                "maximum": maximum_calls,
                "planned": planned_calls,
            },
            "local_measurement": {
                "enabled": measurement is not None,
                "configuration_hash": (
                    sha256_value(measurement) if measurement is not None else None
                ),
                "model_version": (
                    measurement["model_version"] if measurement is not None else None
                ),
            },
            "step_kinds": step_kinds,
            "authority_effect": "operational_only_no_authority_mutation",
            "policy_version": WORKFLOW_POLICY,
        }
        plan_hash = sha256_value(core)
        plan = {
            **core,
            "plan_id": "video_compare_plan_"
            + plan_hash.removeprefix("sha256:")[:24],
            "plan_hash": plan_hash,
        }
        validate_application_instance("video_comparison_workflow_plan", plan, self.root)
        return plan, reference_plan, candidate_plan

    def _validate_state(self, state: dict[str, Any], directory: Path) -> None:
        validate_application_instance("video_comparison_workflow_state", state, self.root)
        if state["state_hash"] != _state_hash(state):
            raise ValidationFailure("video comparison state hash is invalid")
        request = self._read_object(directory / "request.json", "request")
        validate_application_instance(
            "video_comparison_workflow_request", request, self.root
        )
        if state["request_hash"] != sha256_value(request):
            raise ValidationFailure("video comparison request hash is invalid")
        plan = self._read_object(directory / "plan.json", "plan")
        validate_application_instance("video_comparison_workflow_plan", plan, self.root)
        if state["plan_hash"] != plan["plan_hash"]:
            raise ValidationFailure("video comparison plan hash is invalid")
        plan_core = {
            key: value
            for key, value in plan.items()
            if key not in {"plan_id", "plan_hash"}
        }
        if plan["plan_hash"] != sha256_value(plan_core):
            raise ValidationFailure("video comparison plan content identity is invalid")
        prior = None
        for sequence, event in enumerate(state["events"], 1):
            if event["sequence"] != sequence or event["previous_hash"] != prior:
                raise ValidationFailure("video comparison event sequence is invalid")
            if event["event_hash"] != _event_hash(event):
                raise ValidationFailure("video comparison event hash is invalid")
            if event["result_path"] is not None:
                candidate = (directory / event["result_path"]).resolve()
                if directory not in candidate.parents:
                    raise ValidationFailure(
                        "video comparison event result escaped its directory"
                    )
                artifact = self._read_object(candidate, "step result")
                if (
                    artifact.get("schema") != STEP_RESULT_SCHEMA
                    or artifact.get("workflow_id") != state["workflow_id"]
                    or artifact.get("result_hash") != event["result_hash"]
                    or sha256_value(artifact.get("result")) != event["result_hash"]
                ):
                    raise ValidationFailure(
                        "video comparison step result hash is invalid"
                    )
            prior = event["event_hash"]
        if state["event_head"] != prior:
            raise ValidationFailure("video comparison event head is invalid")
        next_step = state["next_step"]
        if next_step is not None:
            expected = _step(
                index=next_step["index"],
                kind=next_step["kind"],
                operation=next_step["operation"],
                arguments=next_step["arguments"],
                request_hash=state["request_hash"],
                plan_hash=state["plan_hash"],
            )
            if expected != next_step or next_step["index"] != state["step_index"]:
                raise ValidationFailure("video comparison next step identity is invalid")
        if state["state"] == "completed":
            report = self._read_object(directory / "report.json", "report")
            validate_application_instance(
                "video_comparison_workflow_report", report, self.root
            )
            report_core = {
                key: value
                for key, value in report.items()
                if key not in {"report_id", "report_hash"}
            }
            if report["report_hash"] != sha256_value(report_core):
                raise ValidationFailure("video comparison report hash is invalid")
            if state["result"] != {
                "report_id": report["report_id"],
                "report_hash": report["report_hash"],
                "overall_status": report["comparison"]["overall_status"],
            }:
                raise ValidationFailure("video comparison terminal result is invalid")

    def _load(self, workflow_id: str, directory: Path | None = None) -> dict[str, Any]:
        directory = directory or self._directory(workflow_id)
        state = self._read_object(directory / "state.json", "state")
        if state.get("workflow_id") != workflow_id:
            raise ValidationFailure("video comparison state belongs to another workflow")
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
    ) -> None:
        state["next_step"] = _step(
            index=state["step_index"],
            kind=kind,
            operation=operation,
            arguments=arguments,
            request_hash=state["request_hash"],
            plan_hash=state["plan_hash"],
        )
        state["state"] = "ready"

    def prepare(self, request: dict[str, Any]) -> dict[str, Any]:
        request = copy.deepcopy(request)
        validate_application_instance(
            "video_comparison_workflow_request", request, self.root
        )
        if request["reference"]["source"]["sha256"] == request["candidate"]["source"]["sha256"]:
            raise ValidationFailure(
                "video comparison requires different reference and candidate bytes"
            )
        request_hash = sha256_value(request)
        workflow_id = "video_compare_" + request_hash.removeprefix("sha256:")[:24]
        with self._lock(workflow_id, create=True) as directory:
            request_path = directory / "request.json"
            if request_path.exists():
                existing = self._read_object(request_path, "request")
                if existing != request:
                    raise ValidationFailure(
                        "video comparison workflow ID collides with another request"
                    )
                return self._public(self._load(workflow_id, directory))
            plan, reference_plan, candidate_plan = self._build_plan(
                request, request_hash
            )
            self._write_once(request_path, request)
            self._write_once(directory / "plan.json", plan)
            state = {
                "schema": WORKFLOW_STATE_SCHEMA,
                "workflow_id": workflow_id,
                "request_hash": request_hash,
                "plan_hash": plan["plan_hash"],
                "state": "ready",
                "step_index": 0,
                "next_step": _step(
                    index=0,
                    kind="reference_analysis",
                    operation="cpcs.analyze.cascade",
                    arguments={
                        "cascade": copy.deepcopy(reference_plan["cascade"]),
                        "authority_mode": "operational_only",
                    },
                    request_hash=request_hash,
                    plan_hash=plan["plan_hash"],
                ),
                "last_completed_step_hash": None,
                "context": {
                    "mode": request["mode"],
                    "plan_id": plan["plan_id"],
                    "paired_profile_hash": plan["paired_profile_hash"],
                    "provider_calls": copy.deepcopy(plan["provider_calls"]),
                    "reference": copy.deepcopy(request["reference"]),
                    "candidate": copy.deepcopy(request["candidate"]),
                    "reference_atomic_plan": reference_plan,
                    "candidate_atomic_plan": candidate_plan,
                    "local_measurement": copy.deepcopy(request["local_measurement"]),
                    "comparison_settings": copy.deepcopy(
                        request["comparison_settings"]
                    ),
                    "assessments": copy.deepcopy(request["assessments"]),
                    "reference_analysis": None,
                    "candidate_analysis": None,
                    "reference_measurement": None,
                    "candidate_measurement": None,
                },
                "events": [],
                "event_head": None,
                "result": None,
                "state_hash": "",
            }
            state["state_hash"] = _state_hash(state)
            validate_application_instance(
                "video_comparison_workflow_state", state, self.root
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
                raise ValidationFailure("video comparison step result is invalid")
            return copy.deepcopy(artifact["result"]), path
        result = self.executor(step["operation"], copy.deepcopy(step["arguments"]))
        if not isinstance(result, dict):
            raise ValidationFailure(
                "video comparison child operation returned a non-object"
            )
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

    def _analysis_context(
        self, state: dict[str, Any], side: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        if result.get("authority_effect") != "operational_only_no_authority_mutation":
            raise ValidationFailure(
                "video comparison requires an operational-only analysis cascade"
            )
        if result.get("observation") is not None or result.get("distillation_run") is not None:
            raise ValidationFailure(
                "video comparison analysis attempted to return authority records"
            )
        vog = result.get("video_observation_graph")
        if not isinstance(vog, dict):
            raise ValidationFailure("video comparison analysis returned no VOG")
        source = state["context"][side]["source"]
        if (
            vog.get("source", {}).get("source_id") != source["source_id"]
            or vog.get("source", {}).get("sha256") != source["sha256"]
        ):
            raise ValidationFailure("video comparison VOG crosses its source boundary")
        vog_path = Path(result.get("artifacts", {}).get("vog", "")).expanduser().resolve()
        work = (self.root / "work").resolve()
        if work not in vog_path.parents or not vog_path.is_file() or vog_path.is_symlink():
            raise ValidationFailure("video comparison VOG artifact is missing or unsafe")
        if json.loads(vog_path.read_text(encoding="utf-8")) != vog:
            raise ValidationFailure("video comparison VOG artifact differs from child result")
        atomic_plan = state["context"][f"{side}_atomic_plan"]
        completed_calls = len(vog["surface_runs"]) - 1
        if completed_calls != atomic_plan["provider_call_count"]:
            raise ValidationFailure(
                "video comparison completed provider-call count differs from its fixed plan"
            )
        return {
            "video_observation_graph": copy.deepcopy(vog),
            "vog_artifact": {
                "path": str(vog_path),
                "sha256": _path_sha256(vog_path),
            },
            "completed_provider_calls": completed_calls,
        }

    def _measurement_arguments(
        self, state: dict[str, Any], side: str
    ) -> dict[str, Any]:
        source_side = state["context"][side]
        source = source_side["source"]
        measurement = state["context"]["local_measurement"]
        if measurement is None:
            raise ValidationFailure("video comparison has no local measurement plan")
        return {
            "source_id": source["source_id"],
            "asset_ref": source["asset_ref"],
            "local_path": source["local_path"],
            "rights_scope": source["rights_scope"],
            "authorized_interval": copy.deepcopy(source_side["authorized_interval"]),
            **copy.deepcopy(measurement),
        }

    def _measurement_context(
        self, state: dict[str, Any], side: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        batch = result.get("batch")
        if not isinstance(batch, dict):
            raise ValidationFailure("video comparison measurement returned no batch")
        source = state["context"][side]["source"]
        if (
            batch.get("source", {}).get("source_id") != source["source_id"]
            or batch.get("source", {}).get("sha256") != source["sha256"]
        ):
            raise ValidationFailure(
                "video comparison measurement crosses its source boundary"
            )
        batch_path = Path(
            result.get("artifacts", {}).get("measurement_batch", "")
        ).expanduser().resolve()
        work = (self.root / "work").resolve()
        if work not in batch_path.parents or not batch_path.is_file() or batch_path.is_symlink():
            raise ValidationFailure(
                "video comparison measurement artifact is missing or unsafe"
            )
        if json.loads(batch_path.read_text(encoding="utf-8")) != batch:
            raise ValidationFailure(
                "video comparison measurement artifact differs from child result"
            )
        return {
            "batch_id": batch["batch_id"],
            "tool": batch["tool"],
            "model_version": batch["model_version"],
            "batch_artifact": {
                "path": str(batch_path),
                "sha256": _path_sha256(batch_path),
            },
        }

    def _comparison_arguments(self, state: dict[str, Any]) -> dict[str, Any]:
        context = state["context"]

        def media(side: str) -> dict[str, Any]:
            source_side = context[side]
            source = source_side["source"]
            measurement = context[f"{side}_measurement"]
            analysis = context[f"{side}_analysis"]
            return {
                "source_id": source["source_id"],
                "asset_id": source["asset_ref"],
                "local_path": source["local_path"],
                "sha256": source["sha256"],
                "rights_scope": source["rights_scope"],
                "asr": copy.deepcopy(source_side["asr"]),
                "pose_batch": (
                    None
                    if measurement is None
                    else copy.deepcopy(measurement["batch_artifact"])
                ),
                "video_observation_graph": copy.deepcopy(
                    analysis["vog_artifact"]
                ),
            }

        return {
            "schema": "cpcs.reference_candidate_comparison_request/1.0",
            "reference": media("reference"),
            "candidate": media("candidate"),
            "settings": copy.deepcopy(context["comparison_settings"]),
            "assessments": copy.deepcopy(context["assessments"]),
        }

    def _workflow_report(
        self,
        state: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        comparison = result.get("report")
        if not isinstance(comparison, dict):
            raise ValidationFailure("video comparison verifier returned no report")
        context = state["context"]

        def side(name: str) -> dict[str, Any]:
            source_side = context[name]
            source = source_side["source"]
            atomic = context[f"{name}_atomic_plan"]
            analysis = context[f"{name}_analysis"]
            vog = analysis["video_observation_graph"]
            return {
                "source_id": source["source_id"],
                "source_sha256": source["sha256"],
                "authorized_interval": copy.deepcopy(
                    source_side["authorized_interval"]
                ),
                "atomic_plan_id": atomic["plan_id"],
                "cascade_id": atomic["cascade"]["cascade_id"],
                "video_observation_graph_id": vog["graph_id"],
                "video_observation_graph_hash": vog["graph_hash"],
                "semantic_profiles": sorted(
                    atomic["coverage"]["semantic_profiles"]
                ),
                "segment_profiles": sorted(
                    atomic["coverage"]["segment_profiles"]
                ),
                "surface_run_count": len(vog["surface_runs"]),
            }

        reference_measurement = context["reference_measurement"]
        candidate_measurement = context["candidate_measurement"]
        measurement_enabled = context["local_measurement"] is not None
        completed_calls = (
            context["reference_analysis"]["completed_provider_calls"]
            + context["candidate_analysis"]["completed_provider_calls"]
        )
        visual = result.get("visual")
        public_visual = (
            None
            if visual is None
            else {
                "sha256": visual["sha256"],
                "sample_count": visual["sample_count"],
                "layout": visual["layout"],
            }
        )
        core = {
            "schema": "cpcs.video_comparison_workflow_report/1.0",
            "workflow_id": state["workflow_id"],
            "request_hash": state["request_hash"],
            "plan_id": context["plan_id"],
            "plan_hash": state["plan_hash"],
            "paired_profile_hash": context["paired_profile_hash"],
            "mode": context["mode"],
            "authority_status": "operational_evidence_only",
            "provider_calls": {
                "planned": context["provider_calls"]["planned"],
                "completed": completed_calls,
            },
            "reference": side("reference"),
            "candidate": side("candidate"),
            "local_measurement": {
                "enabled": measurement_enabled,
                "tool": (
                    reference_measurement["tool"] if measurement_enabled else None
                ),
                "model_version": (
                    reference_measurement["model_version"]
                    if measurement_enabled
                    else None
                ),
                "reference_batch_id": (
                    reference_measurement["batch_id"]
                    if measurement_enabled
                    else None
                ),
                "candidate_batch_id": (
                    candidate_measurement["batch_id"]
                    if measurement_enabled
                    else None
                ),
            },
            "comparison": {
                "report_id": comparison["report_id"],
                "report_hash": sha256_value(comparison),
                "overall_status": comparison["overall_status"],
                "report": copy.deepcopy(comparison),
                "visual": public_visual,
            },
            "limitations": sorted(
                {
                    "The report is operational comparison evidence and cannot promote knowledge or qualify a provider.",
                    "Pegasus descriptions remain interpreted or inferred evidence, not exact pose, force, identity, or private mental state.",
                    "Cancellation takes effect between synchronous child steps; an in-flight provider call keeps its own receipt and reconciliation rules.",
                }
            ),
        }
        report_hash = sha256_value(core)
        report = {
            **core,
            "report_id": "video_compare_report_"
            + report_hash.removeprefix("sha256:")[:24],
            "report_hash": report_hash,
        }
        validate_application_instance(
            "video_comparison_workflow_report", report, self.root
        )
        return report

    def _apply(
        self,
        state: dict[str, Any],
        step: dict[str, Any],
        result: dict[str, Any],
        directory: Path,
    ) -> None:
        context = state["context"]
        kind = step["kind"]
        state["step_index"] += 1
        state["next_step"] = None
        state["last_completed_step_hash"] = step["step_hash"]
        if kind == "reference_analysis":
            context["reference_analysis"] = self._analysis_context(
                state, "reference", result
            )
            self._set_next(
                state,
                kind="candidate_analysis",
                operation="cpcs.analyze.cascade",
                arguments={
                    "cascade": copy.deepcopy(
                        context["candidate_atomic_plan"]["cascade"]
                    ),
                    "authority_mode": "operational_only",
                },
            )
            return
        if kind == "candidate_analysis":
            context["candidate_analysis"] = self._analysis_context(
                state, "candidate", result
            )
            if context["local_measurement"] is None:
                self._set_next(
                    state,
                    kind="compare",
                    operation="cpcs.verify.reference.compare",
                    arguments=self._comparison_arguments(state),
                )
            else:
                self._set_next(
                    state,
                    kind="reference_measurement_prepare",
                    operation="cpcs.measure.pose.prepare",
                    arguments=self._measurement_arguments(state, "reference"),
                )
            return
        if kind == "reference_measurement_prepare":
            self._set_next(
                state,
                kind="reference_measurement_run",
                operation="cpcs.measure.pose.run",
                arguments={"job": copy.deepcopy(result)},
            )
            return
        if kind == "reference_measurement_run":
            context["reference_measurement"] = self._measurement_context(
                state, "reference", result
            )
            self._set_next(
                state,
                kind="candidate_measurement_prepare",
                operation="cpcs.measure.pose.prepare",
                arguments=self._measurement_arguments(state, "candidate"),
            )
            return
        if kind == "candidate_measurement_prepare":
            self._set_next(
                state,
                kind="candidate_measurement_run",
                operation="cpcs.measure.pose.run",
                arguments={"job": copy.deepcopy(result)},
            )
            return
        if kind == "candidate_measurement_run":
            context["candidate_measurement"] = self._measurement_context(
                state, "candidate", result
            )
            if (
                context["reference_measurement"]["tool"]
                != context["candidate_measurement"]["tool"]
                or context["reference_measurement"]["model_version"]
                != context["candidate_measurement"]["model_version"]
            ):
                raise ValidationFailure(
                    "video comparison local measurements require the same tool and model"
                )
            self._set_next(
                state,
                kind="compare",
                operation="cpcs.verify.reference.compare",
                arguments=self._comparison_arguments(state),
            )
            return
        if kind == "compare":
            report = self._workflow_report(state, result)
            self._write_once(directory / "report.json", report)
            state["state"] = "completed"
            state["result"] = {
                "report_id": report["report_id"],
                "report_hash": report["report_hash"],
                "overall_status": report["comparison"]["overall_status"],
            }
            return
        raise ValidationFailure(f"video comparison cannot apply step kind: {kind}")

    def advance(self, workflow_id: str, expected_step_hash: str) -> dict[str, Any]:
        with self._lock(workflow_id) as directory:
            state = self._load(workflow_id, directory)
            if expected_step_hash == state["last_completed_step_hash"]:
                return self._public(state)
            step = state["next_step"]
            if step is None:
                raise ValidationFailure(
                    f"video comparison has no executable step while {state['state']}"
                )
            if expected_step_hash != step["step_hash"]:
                raise ValidationFailure(
                    "video comparison advance targets a stale or different step"
                )
            before = state["state"]
            try:
                result, result_path = self._step_result(state, directory, step)
                self._apply(state, step, result, directory)
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
                    "video_comparison_workflow_state", state, self.root
                )
                self._replace(directory / "state.json", state)
                return self._public(state)
            except VideoComparisonWorkflowCrash:
                raise
            except Exception as exc:
                if state["last_completed_step_hash"] != step["step_hash"]:
                    failure = redact(
                        {"type": type(exc).__name__, "message": str(exc)}
                    )
                    failure_path = (
                        directory / "steps" / f"{step['index']:03d}_failure.json"
                    )
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
                    state["result"] = {
                        "failure": failure,
                        "step_hash": step["step_hash"],
                    }
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

    def cancel(self, workflow_id: str, expected_state_hash: str) -> dict[str, Any]:
        with self._lock(workflow_id) as directory:
            state = self._load(workflow_id, directory)
            if state["state"] == "cancelled":
                cancellation = self._read_object(
                    directory / "cancel.json", "cancellation"
                )
                if (
                    cancellation.get("schema") != STEP_RESULT_SCHEMA
                    or cancellation.get("workflow_id") != workflow_id
                    or cancellation.get("step_hash") != expected_state_hash
                    or cancellation.get("operation") is not None
                    or cancellation.get("result_hash")
                    != sha256_value(cancellation.get("result"))
                ):
                    raise ValidationFailure(
                        "video comparison cancellation replay is not exact"
                    )
                return self._public(state)
            if state["state"] == "completed":
                raise ValidationFailure(
                    "completed video comparison cannot be cancelled"
                )
            if expected_state_hash != state["state_hash"]:
                raise ValidationFailure(
                    "video comparison cancellation targets stale state"
                )
            before = state["state"]
            outcome = {
                "disposition": "cancelled_between_steps",
                "completed_steps": state["step_index"],
                "provider_calls_completed": sum(
                    (
                        state["context"].get(f"{side}_analysis") or {}
                    ).get("completed_provider_calls", 0)
                    for side in ("reference", "candidate")
                ),
            }
            cancellation = {
                "schema": STEP_RESULT_SCHEMA,
                "workflow_id": workflow_id,
                "step_index": state["step_index"],
                "step_hash": expected_state_hash,
                "operation": None,
                "arguments_hash": sha256_value(
                    {
                        "workflow_id": workflow_id,
                        "expected_state_hash": expected_state_hash,
                    }
                ),
                "result": outcome,
                "result_hash": sha256_value(outcome),
            }
            self._write_once(directory / "cancel.json", cancellation)
            state["state"] = "cancelled"
            state["next_step"] = None
            state["result"] = copy.deepcopy(outcome)
            self._append_event(
                state,
                event_type="cancelled",
                state_before=before,
                state_after="cancelled",
                step_hash=None,
                operation=None,
                result_hash=sha256_value(outcome),
                result_path="cancel.json",
            )
            state["state_hash"] = _state_hash(state)
            validate_application_instance(
                "video_comparison_workflow_state", state, self.root
            )
            self._replace(directory / "state.json", state)
            return self._public(state)

    def status(self, workflow_id: str) -> dict[str, Any]:
        with self._lock(workflow_id) as directory:
            return self._public(self._load(workflow_id, directory))

    def inspect(self, workflow_id: str) -> dict[str, Any]:
        with self._lock(workflow_id) as directory:
            state = self._load(workflow_id, directory)
            if state["state"] != "completed":
                raise ValidationFailure(
                    "video comparison report is available only after completion"
                )
            report = self._read_object(directory / "report.json", "report")
            return {
                "schema": "cpcs.video_comparison_workflow_inspection/1.0",
                "workflow_id": workflow_id,
                "state_hash": state["state_hash"],
                "report": report,
            }

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

        def analysis_lineage(side: str) -> dict[str, Any]:
            atomic = context[f"{side}_atomic_plan"]
            completed = context.get(f"{side}_analysis")
            vog = (
                None
                if completed is None
                else completed["video_observation_graph"]
            )
            return {
                "source_id": context[side]["source"]["source_id"],
                "source_sha256": context[side]["source"]["sha256"],
                "atomic_plan_id": atomic["plan_id"],
                "cascade_id": atomic["cascade"]["cascade_id"],
                "planned_provider_calls": atomic["provider_call_count"],
                "completed_provider_calls": (
                    0
                    if completed is None
                    else completed["completed_provider_calls"]
                ),
                "video_observation_graph_id": (
                    None if vog is None else vog["graph_id"]
                ),
                "video_observation_graph_hash": (
                    None if vog is None else vog["graph_hash"]
                ),
            }

        return {
            "schema": "cpcs.video_comparison_workflow_status/1.0",
            "policy_version": WORKFLOW_POLICY,
            "workflow_id": state["workflow_id"],
            "request_hash": state["request_hash"],
            "plan_id": context["plan_id"],
            "plan_hash": state["plan_hash"],
            "paired_profile_hash": context["paired_profile_hash"],
            "mode": context["mode"],
            "state": state["state"],
            "state_hash": state["state_hash"],
            "step_index": state["step_index"],
            "next_step": (
                None
                if next_step is None
                else {
                    key: copy.deepcopy(next_step[key])
                    for key in (
                        "index",
                        "kind",
                        "operation",
                        "arguments_hash",
                        "step_hash",
                    )
                }
            ),
            "last_completed_step_hash": state["last_completed_step_hash"],
            "provider_calls": {
                "maximum": context["provider_calls"]["maximum"],
                "planned": context["provider_calls"]["planned"],
                "completed": sum(
                    analysis_lineage(side)["completed_provider_calls"]
                    for side in ("reference", "candidate")
                ),
            },
            "reference": analysis_lineage("reference"),
            "candidate": analysis_lineage("candidate"),
            "local_measurement": {
                "enabled": context["local_measurement"] is not None,
                "reference_batch_id": (
                    context["reference_measurement"]["batch_id"]
                    if context["reference_measurement"] is not None
                    else None
                ),
                "candidate_batch_id": (
                    context["candidate_measurement"]["batch_id"]
                    if context["candidate_measurement"] is not None
                    else None
                ),
            },
            "events": events,
            "result": copy.deepcopy(state["result"]),
            "authority_effect": "operational_only_no_authority_mutation",
        }
