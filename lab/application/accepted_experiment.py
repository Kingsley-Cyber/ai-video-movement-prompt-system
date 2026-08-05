"""Exact-once outcome orchestration for one accepted, complete experiment."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from lab.second_brain.src.authority import authority_writer
from lab.second_brain.src.query import reason
from lab.second_brain.src.record import (
    append_improvement_orchestration,
    append_prepared_experiment_run,
    prepare_experiment_receipt,
)
from lab.second_brain.src.reflect import (
    ALGORITHM_VERSION,
    DERIVATION_POLICY,
    project_run_edges,
    rebuild,
)
from lab.second_brain.src.validate import (
    REPO_ROOT,
    ValidationFailure,
    canonical_json_bytes,
    read_jsonl,
    sha256_value,
    validate_instance,
)


POLICY_VERSION = "cpcs-improvement-orchestrator/1.0"
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024


def _core_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in run.items()
        if key not in {"prior_record_hash", "record_hash"}
    }


def _curated_hash(root: Path) -> str:
    paths = [root / "lab" / "concepts.jsonl"]
    paths.extend(
        path
        for path in (root / "lab" / "second_brain" / "curated").rglob("*")
        if path.is_file()
    )
    return sha256_value(
        [
            {
                "path": str(path.relative_to(root)),
                "content_hash": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in sorted(paths)
        ]
    )


def _derived_outputs(root: Path) -> dict[str, str]:
    derived = root / "lab" / "second_brain" / "derived"
    return {
        str(path.relative_to(derived)): "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(derived.rglob("*"))
        if path.is_file()
    }


def _timestamp(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValidationFailure(f"{label} must be an RFC 3339 date-time") from error
    if parsed.tzinfo is None:
        raise ValidationFailure(f"{label} must include a timezone")
    return parsed


def _work_directory(orchestration_id: str, root: Path, *, create: bool) -> Path:
    repository = root.resolve()
    current = repository
    for part in ("work", "application", "accepted_experiments", orchestration_id):
        current = current / part
        if current.is_symlink():
            raise ValidationFailure(f"accepted-experiment path cannot be a symlink: {current}")
        if create:
            current.mkdir(mode=0o700, exist_ok=True)
            os.chmod(current, 0o700)
    if not current.is_dir() or repository not in current.resolve().parents:
        raise ValidationFailure("accepted-experiment state escaped the repository")
    return current.resolve()


def _artifact(directory: Path, name: str) -> Path:
    if name not in {"request.json", "state.json"}:
        raise ValidationFailure("accepted-experiment artifact name is invalid")
    path = directory / name
    if path.is_symlink():
        raise ValidationFailure(f"accepted-experiment artifact cannot be a symlink: {name}")
    return path


def _write_new(path: Path, value: dict[str, Any]) -> None:
    payload = canonical_json_bytes(value)
    if len(payload) > MAX_ARTIFACT_BYTES:
        raise ValidationFailure("accepted-experiment artifact exceeds its size limit")
    if path.exists():
        if path.read_bytes() != payload:
            raise ValidationFailure("accepted-experiment artifact identity collision")
        return
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)


def _replace(path: Path, value: dict[str, Any]) -> None:
    payload = canonical_json_bytes(value)
    if len(payload) > MAX_ARTIFACT_BYTES:
        raise ValidationFailure("accepted-experiment state exceeds its size limit")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValidationFailure(f"accepted-experiment artifact is missing or unsafe: {path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationFailure(f"cannot read accepted-experiment artifact: {error}") from error
    if not isinstance(value, dict):
        raise ValidationFailure("accepted-experiment artifact must contain an object")
    return value


def _state(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result.pop("state_hash", None)
    result["state_hash"] = sha256_value(result)
    return result


def _validate_state(value: dict[str, Any], root: Path) -> None:
    validate_instance("accepted_experiment_state", value, root)
    unsigned = copy.deepcopy(value)
    claimed = unsigned.pop("state_hash")
    if sha256_value(unsigned) != claimed:
        raise ValidationFailure("accepted-experiment state hash is invalid")
    if value["next_receipt_index"] != len(value["run_ids"]):
        raise ValidationFailure("accepted-experiment receipt cursor is inconsistent")
    if value["phase"] == "reflected" and not {
        "derived_after_outputs",
        "after_query_traces",
        "candidates",
    } <= set(value):
        raise ValidationFailure("reflected accepted-experiment state is incomplete")


def _existing(orchestration_id: str, flight_id: str, root: Path) -> dict[str, Any] | None:
    rows = read_jsonl(
        root
        / "lab"
        / "second_brain"
        / "immutable"
        / "improvement_orchestrations.jsonl"
    )
    exact = next((row for row in rows if row["id"] == orchestration_id), None)
    other = next(
        (row for row in rows if row["flight"]["flight_id"] == flight_id), None
    )
    if exact is not None:
        validate_instance("improvement_orchestration", exact, root)
        return exact
    if other is not None:
        raise ValidationFailure("experiment flight was already accepted by another request")
    return None


def _evidence_snapshot(
    flight: dict[str, Any], runs: list[dict[str, Any]], projected_edges: list[dict[str, Any]]
) -> dict[str, Any]:
    causal = [
        row
        for row in projected_edges
        if row.get("evidence_scope") == "causal_isolated_comparison"
        and row.get("isolated_comparison", {}).get("flight_id") == flight["id"]
    ]
    if not causal:
        raise ValidationFailure(
            "accepted experiment does not project a causally eligible reflection edge"
        )
    core = {
        "flight_id": flight["id"],
        "flight_hash": flight["flight_hash"],
        "arm_ids": sorted(row["id"] for row in flight["arms"]),
        "prepared_runs": [
            {
                "arm_id": run["arm"],
                "run_id": run["id"],
                "evidence_fingerprint": run["evidence_fingerprint"],
                "run_hash": sha256_value(_core_run(run)),
                "testimonial_review_id": run["testimonial_lineage"][
                    "testimonial_review_id"
                ],
            }
            for run in sorted(runs, key=lambda row: row["arm"])
        ],
        "projected_edges": causal,
    }
    return {**core, "snapshot_hash": sha256_value(core)}


def _trace_summary(
    query: dict[str, Any], result: dict[str, Any], accepted_run_ids: set[str]
) -> dict[str, Any]:
    edges = result.get("learned_weights", [])
    cited = sorted(
        accepted_run_ids
        & {
            evidence_id
            for edge in edges
            for evidence_id in edge.get("evidence", [])
        }
    )
    return {
        "query_hash": sha256_value(query),
        "result_hash": sha256_value(result),
        "learned_edge_ids": sorted(
            edge_id
            for edge in edges
            if isinstance((edge_id := edge.get("edge_id")), str)
        ),
        "cited_run_ids": cited,
        "cites_accepted_evidence": bool(cited),
    }


def _candidate(
    candidate_type: str,
    claim: str,
    edge: dict[str, Any] | None,
    *,
    evidence_ids: list[str],
    domain: str | None,
) -> dict[str, Any]:
    identity = {
        "candidate_type": candidate_type,
        "claim": claim,
        "source_edge_ids": [] if edge is None else [edge["id"]],
        "evidence_ids": sorted(evidence_ids),
        "provider": None if edge is None else edge.get("provider"),
        "model_version": None if edge is None else edge.get("model_version"),
        "domain": domain,
    }
    return {
        "candidate_id": "improvement_candidate_"
        + sha256_value(identity).removeprefix("sha256:")[:24],
        **identity,
        "status": "staged_unreviewed",
        "limitations": [
            "Derived from one accepted experiment and requires explicit review before promotion."
        ],
    }


def _candidates(
    edges: list[dict[str, Any]],
    after_results: list[dict[str, Any]],
    *,
    domain: str,
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {
        "working_patterns": [],
        "failure_cards": [],
        "provider_recommendations": [],
        "compiler_recipes": [],
        "profile_updates": [],
        "research_gaps": [],
    }
    for edge in edges:
        evidence = sorted(edge["evidence"])
        base = f"{edge['u']} {edge['type']} {edge['v']}"
        result["working_patterns"].append(
            _candidate("working_pattern", base, edge, evidence_ids=evidence, domain=domain)
        )
        comparison = edge["isolated_comparison"]
        result["failure_cards"].append(
            _candidate(
                "failure_card",
                f"Control value {comparison['loser']['control_value']!r} underperformed for {edge['v']}",
                edge,
                evidence_ids=evidence,
                domain=domain,
            )
        )
        result["provider_recommendations"].append(
            _candidate(
                "provider_recommendation",
                f"Test the winning {edge['u']} control for {edge['provider']} {edge['model_version']}",
                edge,
                evidence_ids=evidence,
                domain=domain,
            )
        )
        result["compiler_recipes"].append(
            _candidate(
                "compiler_recipe",
                f"Consider the winning {edge['u']} value when compiling for {edge['v']}",
                edge,
                evidence_ids=evidence,
                domain=domain,
            )
        )
        result["profile_updates"].append(
            _candidate(
                "profile_update",
                f"Review whether the {domain} profile should prefer the winning {edge['u']} value",
                edge,
                evidence_ids=evidence,
                domain=domain,
            )
        )
    for query_result in after_results:
        gap = query_result.get("knowledge_gap", {})
        if gap.get("status") not in {None, "none"}:
            result["research_gaps"].append(
                _candidate(
                    "research_gap",
                    gap.get("suggested_query", "Investigate unresolved accepted-experiment coverage"),
                    None,
                    evidence_ids=[],
                    domain=domain,
                )
            )
    return result


@authority_writer("accepted_experiment")
def accept_experiment(
    request: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Accept complete controlled evidence, reflect it, and record one replayable outcome."""
    validate_instance("accepted_experiment_request", request, root)
    for receipt in request["receipts"]:
        validate_instance("experiment_receipt", receipt, root)
    for query in request["trace_queries"]:
        validate_instance("reasoning_query", query, root)
    request_hash = sha256_value(request)
    orchestration_id = (
        "improvement_" + request_hash.removeprefix("sha256:")[:24]
    )
    existing = _existing(orchestration_id, request["flight_id"], root)
    if existing is not None:
        if existing["request_hash"] != request_hash:
            raise ValidationFailure("accepted-experiment request hash collision")
        return existing

    flights = {
        row["id"]: row
        for row in read_jsonl(
            root / "lab" / "second_brain" / "immutable" / "flights.jsonl"
        )
    }
    flight = flights.get(request["flight_id"])
    if flight is None or flight.get("legacy") is not None:
        raise ValidationFailure("accepted experiment requires one sealed nonlegacy flight")
    if (
        flight.get("design", {}).get("classification") != "isolated_comparison"
        or flight.get("design", {}).get("causal_claim_policy") != "isolated_only"
    ):
        raise ValidationFailure("accepted experiment is not an isolated causal candidate")
    arm_ids = sorted(row["id"] for row in flight["arms"])
    receipt_arm_ids = sorted(row["arm_id"] for row in request["receipts"])
    if receipt_arm_ids != arm_ids or len(receipt_arm_ids) != len(set(receipt_arm_ids)):
        raise ValidationFailure("accepted experiment requires exactly one receipt for every arm")
    if any(row["flight_id"] != flight["id"] for row in request["receipts"]):
        raise ValidationFailure("accepted experiment receipts must share the selected flight")

    receipts = sorted(copy.deepcopy(request["receipts"]), key=lambda row: row["arm_id"])
    prepared = [prepare_experiment_receipt(row, root) for row in receipts]
    if any(
        run.get("evidence_design", {}).get("causal_eligibility") != "candidate"
        or run.get("evidence_lineage", {}).get("compliance_status") == "inconclusive"
        or not isinstance(run.get("testimonial_lineage"), dict)
        for run in prepared
    ):
        raise ValidationFailure(
            "accepted experiment requires causally eligible, conclusive, reviewed testimonial evidence for every arm"
        )
    accepted_at = _timestamp(request["accepted_at"], "accepted_at")
    if any(
        accepted_at < _timestamp(run["human_review"]["reviewed_at"], "reviewed_at")
        for run in prepared
    ):
        raise ValidationFailure("experiment acceptance cannot predate an arm review")

    directory = _work_directory(orchestration_id, root, create=True)
    request_path = _artifact(directory, "request.json")
    state_path = _artifact(directory, "state.json")
    _write_new(request_path, request)
    if _read(request_path) != request:
        raise ValidationFailure("accepted-experiment request replay differs from captured bytes")

    if state_path.exists():
        state = _read(state_path)
        _validate_state(state, root)
        if state["request_hash"] != request_hash:
            raise ValidationFailure("accepted-experiment state belongs to another request")
        snapshot = state["evidence_snapshot"]
        expected_runs = {
            row["arm_id"]: row for row in snapshot["prepared_runs"]
        }
        for run in prepared:
            expected = expected_runs.get(run["arm"])
            if expected is None or expected["run_hash"] != sha256_value(_core_run(run)):
                raise ValidationFailure("accepted-experiment evidence changed after preflight")
    else:
        projected = project_run_edges(prepared, root)
        snapshot = _evidence_snapshot(flight, prepared, projected)
        derived_before = _derived_outputs(root)
        before_results = [reason(query, root) for query in request["trace_queries"]]
        state = _state(
            {
                "schema": "cpcs.accepted_experiment_state/1.0",
                "orchestration_id": orchestration_id,
                "policy_version": POLICY_VERSION,
                "request_hash": request_hash,
                "phase": "prepared",
                "evidence_snapshot": snapshot,
                "curated_before_hash": _curated_hash(root),
                "derived_before_outputs": derived_before,
                "before_query_traces": [
                    _trace_summary(query, result, set())
                    for query, result in zip(request["trace_queries"], before_results)
                ],
                "next_receipt_index": 0,
                "run_ids": [],
            }
        )
        _validate_state(state, root)
        _replace(state_path, state)

    for index in range(state["next_receipt_index"], len(prepared)):
        stored_run = append_prepared_experiment_run(_core_run(prepared[index]), root)
        expected = snapshot["prepared_runs"][index]
        if (
            stored_run["id"] != expected["run_id"]
            or stored_run["evidence_fingerprint"] != expected["evidence_fingerprint"]
        ):
            raise ValidationFailure("admitted run differs from accepted evidence snapshot")
        state["phase"] = "admitting"
        state["next_receipt_index"] = index + 1
        state["run_ids"].append(stored_run["id"])
        state = _state(state)
        _validate_state(state, root)
        _replace(state_path, state)

    stored_runs = {
        row["id"]: row
        for row in read_jsonl(
            root / "lab" / "second_brain" / "immutable" / "runs.jsonl"
        )
        if row["id"] in set(state["run_ids"])
    }
    if set(stored_runs) != set(state["run_ids"]):
        raise ValidationFailure("accepted-experiment immutable run set is incomplete")
    projected_edges = snapshot["projected_edges"]
    if state["phase"] == "reflected" and _derived_outputs(root) == state[
        "derived_after_outputs"
    ]:
        derived_after = state["derived_after_outputs"]
        after_traces = state["after_query_traces"]
        candidates = state["candidates"]
    else:
        derived_after = rebuild(root)
        after_results = [reason(query, root) for query in request["trace_queries"]]
        accepted_run_ids = set(state["run_ids"])
        after_traces = [
            _trace_summary(query, result, accepted_run_ids)
            for query, result in zip(request["trace_queries"], after_results)
        ]
        candidates = _candidates(
            projected_edges,
            after_results,
            domain=flight["intent_class"],
        )
        curated_after = _curated_hash(root)
        if curated_after != state["curated_before_hash"]:
            raise ValidationFailure("accepted-experiment orchestration changed curated authority")
        state["phase"] = "reflected"
        state["derived_after_outputs"] = derived_after
        state["after_query_traces"] = after_traces
        state["candidates"] = candidates
        state = _state(state)
        _validate_state(state, root)
        _replace(state_path, state)

    curated_after = _curated_hash(root)
    if curated_after != state["curated_before_hash"]:
        raise ValidationFailure("accepted-experiment orchestration changed curated authority")

    before_traces = state["before_query_traces"]
    value = {
        "schema": "cpcs.improvement_orchestration/1.0",
        "id": orchestration_id,
        "policy_version": POLICY_VERSION,
        "request_hash": request_hash,
        "flight": {
            "flight_id": flight["id"],
            "flight_hash": flight["flight_hash"],
            "classification": "isolated_comparison",
            "causal_eligibility": "eligible",
            "arm_ids": arm_ids,
        },
        "acceptance": {
            "accepted_by": request["accepted_by"],
            "accepted_at": request["accepted_at"],
            "rationale": request["rationale"],
        },
        "evidence_snapshot": {
            "snapshot_hash": snapshot["snapshot_hash"],
            "run_ids": sorted(state["run_ids"]),
            "run_fingerprints": {
                run_id: stored_runs[run_id]["evidence_fingerprint"]
                for run_id in sorted(stored_runs)
            },
            "run_record_hashes": {
                run_id: stored_runs[run_id]["record_hash"]
                for run_id in sorted(stored_runs)
            },
            "testimonial_review_ids": sorted(
                stored_runs[run_id]["testimonial_lineage"]["testimonial_review_id"]
                for run_id in stored_runs
            ),
            "projected_causal_edge_ids": sorted(
                row["id"] for row in projected_edges
            ),
        },
        "reflection": {
            "algorithm_version": ALGORITHM_VERSION,
            "derivation_policy": DERIVATION_POLICY,
            "before_state_hash": sha256_value(state["derived_before_outputs"]),
            "after_state_hash": sha256_value(derived_after),
            "before_outputs": state["derived_before_outputs"],
            "after_outputs": derived_after,
            "changed_files": sorted(
                path
                for path in set(state["derived_before_outputs"]) | set(derived_after)
                if state["derived_before_outputs"].get(path) != derived_after.get(path)
            ),
        },
        "query_traces": [
            {
                "query_hash": after["query_hash"],
                "before_result_hash": before["result_hash"],
                "after_result_hash": after["result_hash"],
                "learned_edge_ids": after["learned_edge_ids"],
                "cited_run_ids": after["cited_run_ids"],
                "cites_accepted_evidence": after["cites_accepted_evidence"],
            }
            for before, after in zip(before_traces, after_traces)
        ],
        "candidates": candidates,
        "authority_effects": {
            "curated_before_hash": state["curated_before_hash"],
            "curated_after_hash": curated_after,
            "curated_unchanged": True,
            "immutable_run_ids": sorted(state["run_ids"]),
            "derived_only": True,
            "promotion_performed": False,
        },
    }
    return append_improvement_orchestration(value, root)
