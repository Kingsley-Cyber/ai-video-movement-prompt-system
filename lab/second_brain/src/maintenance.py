"""Deterministic brain-health views and a resumable maintenance state machine."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from collections import Counter, deque
from pathlib import Path
from typing import Any

from .authority import authority_reader, authority_writer
from .graph import build_live_graph
from .neo4j_projection import (
    build_projection_plan,
    graph_logical_digest,
    projection_configuration_status,
    sync_projection,
)
from .source_registry import build_source_closure_report
from .validate import (
    REPO_ROOT,
    ValidationFailure,
    canonical_json_bytes,
    read_jsonl,
    sha256_value,
    validate_curated,
    validate_immutable,
    validate_instance,
    validate_staging,
)


DOMAIN_COVERAGE_POLICY = "cpcs-domain-coverage/1.0"
CORE_MEMORY_POLICY = "cpcs-core-memory/1.0"
OUTCOME_MEMORY_POLICY = "cpcs-outcome-memory/1.0"
BRAIN_HEALTH_POLICY = "cpcs-brain-health/1.0"
MAINTENANCE_POLICY = "cpcs-maintenance/1.0"
MAINTENANCE_TARGETS = frozenset(
    {
        "weights",
        "insights",
        "coverage",
        "source_closure",
        "indexes",
        "domain_coverage",
        "core_memory",
        "outcome_memory",
        "brain_health",
    }
)
STAGE_ORDER = ("inspect", "rebuild", "project", "qualify")


def _work_root(root: Path) -> Path:
    path = (root / "work" / "maintenance").resolve()
    expected = (root / "work").resolve()
    if expected not in path.parents:
        raise ValidationFailure("maintenance state escaped work/")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def _state_path(maintenance_id: str, root: Path) -> Path:
    if not maintenance_id.startswith("maintenance_") or len(maintenance_id) != 36:
        raise ValidationFailure("maintenance ID is invalid")
    path = (_work_root(root) / maintenance_id / "state.json").resolve()
    if _work_root(root) not in path.parents:
        raise ValidationFailure("maintenance state path escaped work/")
    return path


def _event_path(maintenance_id: str, root: Path) -> Path:
    return _state_path(maintenance_id, root).with_name("events.jsonl")


def _state_content_hash(value: dict[str, Any]) -> str:
    return sha256_value(
        {
            key: item
            for key, item in value.items()
            if key not in {"state_hash", "event_count", "event_head"}
        }
    )


def _load_events(maintenance_id: str, root: Path) -> list[dict[str, Any]]:
    path = _event_path(maintenance_id, root)
    if not path.exists():
        return []
    events = read_jsonl(path)
    previous = None
    for sequence, event in enumerate(events, 1):
        validate_instance("knowledge_maintenance_event", event, root)
        if event["sequence"] != sequence or event["previous_event_hash"] != previous:
            raise ValidationFailure("maintenance event chain order is invalid")
        expected = sha256_value(
            {key: item for key, item in event.items() if key != "event_hash"}
        )
        if event["event_hash"] != expected:
            raise ValidationFailure("maintenance event hash is invalid")
        previous = event["event_hash"]
    return events


def _append_event(
    state: dict[str, Any],
    *,
    stage: str,
    input_state_hash: str | None,
    payload: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    events = _load_events(state["maintenance_id"], root)
    core = {
        "schema": "cpcs.knowledge_maintenance_event/1.0",
        "event_id": "maintenance_event_" + "0" * 24,
        "maintenance_id": state["maintenance_id"],
        "sequence": len(events) + 1,
        "stage": stage,
        "input_state_hash": input_state_hash,
        "state_content_hash": _state_content_hash(state),
        "payload_hash": sha256_value(payload),
        "previous_event_hash": events[-1]["event_hash"] if events else None,
    }
    event_id = "maintenance_event_" + sha256_value(core).removeprefix("sha256:")[:24]
    event = {**core, "event_id": event_id}
    event["event_hash"] = sha256_value(event)
    validate_instance("knowledge_maintenance_event", event, root)
    path = _event_path(state["maintenance_id"], root)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("ab") as handle:
        handle.write(canonical_json_bytes(event))
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(path, 0o600)
    state["event_count"] = event["sequence"]
    state["event_head"] = event["event_hash"]
    return state


def _write_state(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    payload = canonical_json_bytes(value)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".state.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_state(maintenance_id: str, root: Path) -> dict[str, Any]:
    path = _state_path(maintenance_id, root)
    if path.is_symlink() or not path.is_file():
        raise ValidationFailure(f"maintenance state is missing: {maintenance_id}")
    value = json.loads(path.read_text(encoding="utf-8"))
    validate_instance("maintenance_state", value, root)
    if value["state_hash"] != sha256_value(
        {key: item for key, item in value.items() if key != "state_hash"}
    ):
        raise ValidationFailure("maintenance state hash is invalid")
    events = _load_events(maintenance_id, root)
    if (
        len(events) != value["event_count"]
        or not events
        or events[-1]["event_hash"] != value["event_head"]
        or events[-1]["state_content_hash"] != _state_content_hash(value)
    ):
        raise ValidationFailure("maintenance state and event head differ")
    return value


def _seal_state(value: dict[str, Any], root: Path) -> dict[str, Any]:
    sealed = copy.deepcopy(value)
    sealed["state_hash"] = sha256_value(
        {key: item for key, item in sealed.items() if key != "state_hash"}
    )
    validate_instance("maintenance_state", sealed, root)
    return sealed


@authority_reader("domain_coverage_snapshot")
def build_domain_coverage_report(root: Path = REPO_ROOT) -> dict[str, Any]:
    concepts = {row["id"]: row for row in read_jsonl(root / "lab" / "concepts.jsonl")}
    mappings = read_jsonl(root / "lab" / "second_brain" / "curated" / "mappings.jsonl")
    mapped = {row["concept_id"] for row in mappings}
    manifest_path = (
        root / "lab" / "second_brain" / "curated" / "domain_coverage_manifests.jsonl"
    )
    manifests = read_jsonl(manifest_path) if manifest_path.exists() else []
    rows = []
    for manifest in sorted(manifests, key=lambda row: row["id"]):
        validate_instance("domain_coverage_manifest", manifest, root)
        expected = set(manifest["expected_ids"])
        curated = expected & set(concepts)
        operational = expected & mapped
        retrieval_qualified = {
            concept_id
            for concept_id in curated
            if concepts[concept_id]["status"] in {"partial", "proven"}
        }
        rows.append(
            {
                "manifest_id": manifest["id"],
                "domain": manifest["domain"],
                "inventory_name": manifest["inventory_name"],
                "inventory_scope": manifest["inventory_scope"],
                "completeness_claim": manifest["completeness_claim"],
                "expected_ids": sorted(expected),
                "curated_ids": sorted(curated),
                "operationally_mapped_ids": sorted(operational),
                "retrieval_qualified_ids": sorted(retrieval_qualified),
                "missing_ids": sorted(expected - curated),
                "source_refs": manifest["source_refs"],
            }
        )
    report = {
        "schema": "cpcs.domain_coverage_report/1.0",
        "policy_version": DOMAIN_COVERAGE_POLICY,
        "manifests": rows,
        "summary": {
            "manifests": len(rows),
            "source_complete_manifests": sum(
                row["completeness_claim"] == "source_complete" for row in rows
            ),
            "expected": sum(len(row["expected_ids"]) for row in rows),
            "curated": sum(len(row["curated_ids"]) for row in rows),
            "operationally_mapped": sum(
                len(row["operationally_mapped_ids"]) for row in rows
            ),
            "retrieval_qualified": sum(
                len(row["retrieval_qualified_ids"]) for row in rows
            ),
            "missing": sum(len(row["missing_ids"]) for row in rows),
        },
    }
    report["report_hash"] = sha256_value(report)
    validate_instance("domain_coverage_report", report, root)
    return report


@authority_reader("core_memory_snapshot")
def build_core_memory_view(root: Path = REPO_ROOT) -> dict[str, Any]:
    sb = root / "lab" / "second_brain"
    concepts = [
        {
            "id": row["id"],
            "name": row["name"],
            "kind": row["kind"],
            "layer": row["layer"],
            "definition": row.get("definition", row.get("what", row["name"])),
            "status": row["status"],
            "source_refs": row.get("source", []),
        }
        for row in read_jsonl(root / "lab" / "concepts.jsonl")
        if row["status"] in {"partial", "proven"}
    ]
    rules = [
        {key: row[key] for key in ("id", "statement", "kind") if key in row}
        for row in read_jsonl(sb / "curated" / "rules.jsonl")
    ]
    mappings = [
        {
            key: row[key]
            for key in ("id", "concept_id", "target_type", "target_id", "encoding")
            if key in row
        }
        for row in read_jsonl(sb / "curated" / "mappings.jsonl")
    ]
    objects = []
    for object_type, filename in (
        ("claim", "claims.jsonl"),
        ("equation", "equations.jsonl"),
        ("method", "methods.jsonl"),
        ("mechanism", "mechanisms.jsonl"),
    ):
        for row in read_jsonl(sb / "curated" / filename):
            objects.append(
                {
                    "object_type": object_type,
                    "id": row["id"],
                    "concept_ids": row["concept_ids"],
                    "source_refs": row.get("source_refs", row.get("sources", [])),
                }
            )
    value = {
        "schema": "cpcs.core_memory_view/1.0",
        "policy_version": CORE_MEMORY_POLICY,
        "concepts": sorted(concepts, key=lambda row: row["id"]),
        "rules": sorted(rules, key=lambda row: row["id"]),
        "mappings": sorted(mappings, key=lambda row: row["id"]),
        "knowledge_objects": sorted(objects, key=lambda row: (row["object_type"], row["id"])),
    }
    value["view_hash"] = sha256_value(value)
    validate_instance("core_memory_view", value, root)
    return value


def _run_outcome(run: dict[str, Any]) -> str:
    compliance = (run.get("evidence_lineage") or {}).get("compliance_status")
    if compliance == "inconclusive":
        return "inconclusive"
    if compliance == "fail" or run.get("verdict", "").lower() in {"reject", "fail", "failure"}:
        return "failure"
    if run.get("verdict", "").lower() in {"keep", "accept", "pass", "success"}:
        return "success"
    return "mixed"


@authority_reader("outcome_memory_snapshot")
def build_outcome_memory(root: Path = REPO_ROOT) -> dict[str, Any]:
    runs = read_jsonl(root / "lab" / "second_brain" / "immutable" / "runs.jsonl")
    outcomes = []
    for run in sorted(runs, key=lambda row: row["id"]):
        if run.get("capture_kind") == "manual_render":
            continue
        review = run.get("human_review") or {}
        outcomes.append(
            {
                "run_id": run["id"],
                "outcome": _run_outcome(run),
                "concept_ids": sorted(run.get("concept_ids", [])),
                "provider": run.get("provider"),
                "model_version": run.get("model_version"),
                "intent_class": run.get("intent_class"),
                "tested_delta": run.get("tested_delta"),
                "remarks": review.get("remarks", run.get("notes", "")),
                "human_verdict": review.get("verdict", run.get("verdict")),
                "evidence_refs": [run["id"]],
            }
        )
    value = {
        "schema": "cpcs.outcome_memory/1.0",
        "policy_version": OUTCOME_MEMORY_POLICY,
        "outcomes": outcomes,
        "summary": dict(sorted(Counter(row["outcome"] for row in outcomes).items())),
    }
    value["view_hash"] = sha256_value(value)
    validate_instance("outcome_memory", value, root)
    return value


def _graph_reachability(graph: Any) -> dict[str, Any]:
    concepts = {
        node_id
        for node_id, data in graph.nodes(data=True)
        if data.get("node_type") == "concept"
    }
    if not concepts:
        return {"concepts": 0, "reachable": 0, "orphan_ids": []}
    start = sorted(concepts)[0]
    seen = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in set(graph.successors(node)) | set(graph.predecessors(node)):
            if neighbor in concepts and neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return {
        "concepts": len(concepts),
        "reachable": len(seen),
        "orphan_ids": sorted(concepts - seen),
    }


@authority_reader("brain_health_snapshot")
def build_brain_health_report(root: Path = REPO_ROOT) -> dict[str, Any]:
    checks = []
    for name, validator in (
        ("curated_schema_and_integrity", validate_curated),
        ("immutable_schema_and_integrity", validate_immutable),
        ("staging_schema_and_integrity", validate_staging),
    ):
        try:
            validator(root)
            checks.append(
                {
                    "check": name,
                    "status": "passed",
                    "detail": {"validated": True},
                }
            )
        except Exception as error:
            checks.append(
                {
                    "check": name,
                    "status": "failed",
                    "detail": {"error_class": error.__class__.__name__, "message": str(error)},
                }
            )
    source_closure = build_source_closure_report(root)
    domain_coverage = build_domain_coverage_report(root)
    graph = build_live_graph(
        root,
        include_derived=True,
        validity_mode="all_versions",
    )
    reachability = _graph_reachability(graph)
    checks.append(
        {
            "check": "typed_graph_reachability",
            "status": "passed" if not reachability["orphan_ids"] else "attention_required",
            "detail": reachability,
        }
    )
    graph_digest = graph_logical_digest(graph)
    projection_status = projection_configuration_status()
    projection = {
        **projection_status,
        "networkx_logical_digest": graph_digest,
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "automatic_sync_requires_exact_authorization": True,
    }
    if projection_status["configured"]:
        plan = build_projection_plan(root)
        projection.update(
            plan_status="validated",
            authority_snapshot_hash=plan["authority_snapshot_hash"],
            generation=plan["generation"],
        )
    else:
        projection["plan_status"] = "not_built_unconfigured"
    checks.append(
        {
            "check": "neo4j_projection_readiness",
            "status": "passed" if projection_status["configured"] else "attention_required",
            "detail": {
                "configured": projection_status["configured"],
                "plan_status": projection["plan_status"],
                "networkx_logical_digest": graph_digest,
            },
        }
    )
    if source_closure["counts"]["partial"] or source_closure["counts"]["quarantined"]:
        checks.append(
            {
                "check": "source_closure",
                "status": "attention_required",
                "detail": source_closure["counts"],
            }
        )
    else:
        checks.append({"check": "source_closure", "status": "passed", "detail": source_closure["counts"]})
    checks.append(
        {
            "check": "domain_semantic_coverage",
            "status": (
                "passed"
                if domain_coverage["summary"]["source_complete_manifests"]
                and not domain_coverage["summary"]["missing"]
                else "attention_required"
            ),
            "detail": domain_coverage["summary"],
        }
    )
    report = {
        "schema": "cpcs.brain_health_report/1.0",
        "policy_version": BRAIN_HEALTH_POLICY,
        "repository_revision": projection.get("authority_snapshot_hash", graph_digest),
        "checks": checks,
        "domain_coverage": domain_coverage,
        "source_closure": source_closure,
        "projection": projection,
        "status": (
            "passed"
            if all(row["status"] == "passed" for row in checks)
            else "attention_required"
        ),
    }
    report["report_hash"] = sha256_value(report)
    validate_instance("brain_health_report", report, root)
    return report


@authority_writer("maintenance_prepare")
def prepare_maintenance(
    targets: list[str],
    *,
    synchronize_neo4j: bool = False,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    selected = sorted(set(targets))
    if not selected or set(selected) - MAINTENANCE_TARGETS:
        raise ValidationFailure("maintenance targets are empty or unknown")
    if synchronize_neo4j:
        plan = build_projection_plan(root)
        revision = plan["authority_snapshot_hash"]
    else:
        revision = graph_logical_digest(
            build_live_graph(
                root,
                include_derived=True,
                validity_mode="all_versions",
            )
        )
    request = {
        "policy_version": MAINTENANCE_POLICY + "/events-1",
        "targets": selected,
        "synchronize_neo4j": synchronize_neo4j,
        "expected_snapshot_hash": revision,
    }
    request_hash = sha256_value(request)
    maintenance_id = "maintenance_" + request_hash.removeprefix("sha256:")[:24]
    path = _state_path(maintenance_id, root)
    if path.exists():
        existing = _read_state(maintenance_id, root)
        if existing["request_hash"] != request_hash:
            raise ValidationFailure("maintenance ID collision")
        return existing
    state = _seal_state(
        {
            "schema": "cpcs.maintenance_state/1.0",
            "maintenance_id": maintenance_id,
            "request_hash": request_hash,
            "revision": revision,
            "targets": selected,
            "neo4j": {
                "requested": synchronize_neo4j,
                "expected_snapshot_hash": (
                    revision if synchronize_neo4j else None
                ),
                "status": "pending" if synchronize_neo4j else "skipped",
            },
            "stage": "inspect",
            "completed_stages": [],
            "receipts": [],
            "event_count": 1,
            "event_head": "sha256:" + "0" * 64,
            "failure": None,
            "state_hash": "sha256:" + "0" * 64,
        },
        root,
    )
    state = _append_event(
        state,
        stage="prepared",
        input_state_hash=None,
        payload=request,
        root=root,
    )
    state = _seal_state(state, root)
    _write_state(path, state)
    return state


@authority_reader("maintenance_status")
def maintenance_status(maintenance_id: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    return _read_state(maintenance_id, root)


@authority_writer("maintenance_advance")
def advance_maintenance(
    maintenance_id: str,
    *,
    expected_snapshot_hash: str | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    state = _read_state(maintenance_id, root)
    if state["stage"] in {"complete", "failed"}:
        return state
    stage = state["stage"]
    input_state_hash = state["state_hash"]
    event_payload: dict[str, Any]
    try:
        if stage == "inspect":
            payload = build_brain_health_report(root)
            next_stage = "rebuild"
        elif stage == "rebuild":
            from .reflect import rebuild

            payload = {"artifact_hashes": rebuild(root, targets=set(state["targets"]))}
            next_stage = "project"
        elif stage == "project":
            if state["neo4j"]["requested"]:
                sealed = state["neo4j"]["expected_snapshot_hash"]
                if expected_snapshot_hash != sealed:
                    raise ValidationFailure(
                        "Neo4j synchronization requires the exact prepared snapshot hash"
                    )
                checkpoint = sync_projection(
                    expected_snapshot_hash=sealed,
                    root=root,
                )
                state["neo4j"]["status"] = "synchronized"
                payload = {"checkpoint": checkpoint}
            else:
                payload = {"status": "skipped", "reason": "not_requested"}
            next_stage = "qualify"
        else:
            payload = build_brain_health_report(root)
            next_stage = "complete"
        receipt = {
            "stage": stage,
            "input_state_hash": state["state_hash"],
            "output_hash": sha256_value(payload),
            "payload": payload,
        }
        state["completed_stages"] = [*state["completed_stages"], stage]
        state["receipts"] = [*state["receipts"], receipt]
        state["stage"] = next_stage
        event_payload = receipt
    except Exception as error:
        if stage == "project" and state["neo4j"]["requested"]:
            state["neo4j"]["status"] = "failed"
        state["stage"] = "failed"
        state["failure"] = {
            "stage": stage,
            "error_class": error.__class__.__name__,
            "message": str(error),
        }
        event_payload = copy.deepcopy(state["failure"])
    state = _append_event(
        state,
        stage=stage if state["stage"] != "failed" else "failed",
        input_state_hash=input_state_hash,
        payload=event_payload,
        root=root,
    )
    state = _seal_state(state, root)
    _write_state(_state_path(maintenance_id, root), state)
    return state
