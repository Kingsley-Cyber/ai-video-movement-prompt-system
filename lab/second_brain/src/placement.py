"""Replay-stable ontology placement and governed research-graph growth planning."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

from .authority import authority_reader, authority_writer
from .distill import (
    CURATED_PATHS,
    STAGE_DISPOSITIONS,
    _curated_snapshot_hash,
    _fingerprint,
    _load_curated,
)
from .graph import (
    OPERATIONAL_EDGE_TYPES,
    STRUCTURAL_EDGE_TYPES,
    edge_compatibility,
)
from .rules import referenced_concept_ids
from .source_registry import (
    load_source_units,
    resolve_typed_source_evidence,
    source_registry_required,
)
from .terminology import candidate_terminology_control
from .validate import (
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    canonical_json_bytes,
    content_hash,
    load_ontology_registry,
    normalize_concept_identity,
    read_jsonl,
    sha256_value,
    validate_instance,
)

POLICY = {
    "version": "cpcs-ontology-placement/1.1",
    "closed_dispositions": [
        "merge", "refine", "extend", "contradict", "supersede", "new",
        "no_candidate", "needs_review",
    ],
    "identity_authority": "explicit_durable_id_assignment",
    "similarity_establishes_identity": False,
    "source_closure_required_when_registered": True,
    "projection_sync_mode": "incremental_content_hash_projection",
}
POLICY_HASH = sha256_value(POLICY)
PLAN_POINTER = "second_brain_graph_growth_plans"
PLAN_PATH = Path("lab/second_brain/staging/graph_growth_plans.jsonl")

AUTHORITY_STORES = {
    proposal_type: str(path)
    for proposal_type, path in CURATED_PATHS.items()
}
DERIVED_INDEXES = {
    "concept": [
        "aliases", "concept_to_source", "dense_semantic_concepts",
        "lexical_concepts", "temporal_validity", "typed_adjacency",
    ],
    "edge": [
        "conflicts", "dependency_cycles", "prerequisite_closure",
        "temporal_validity", "typed_adjacency",
    ],
    "mapping": ["control_to_provider", "temporal_validity"],
    "intent": ["intent_to_concept", "temporal_validity"],
    "rule": ["temporal_validity"],
    "claim": [
        "concept_to_knowledge_object", "knowledge_object_lexical",
        "knowledge_object_links", "temporal_validity",
    ],
    "equation": [
        "concept_to_knowledge_object", "knowledge_object_lexical",
        "knowledge_object_links", "temporal_validity",
    ],
    "method": [
        "concept_to_knowledge_object", "knowledge_object_lexical",
        "knowledge_object_links", "temporal_validity",
    ],
    "mechanism": [
        "concept_to_knowledge_object", "knowledge_object_lexical",
        "knowledge_object_links", "temporal_validity",
    ],
    "reasoning_policy": [
        "reasoning_policy_lexical", "task_class_to_reasoning_policy",
        "temporal_validity",
    ],
}


def placement_required(root: Path = REPO_ROOT) -> bool:
    """Return whether the repository declares growth plans as a live gate."""
    path = root / "lab" / "registry.yaml"
    if not path.exists():
        return False
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return False
    scripts = value.get("scripts", {}) if isinstance(value, dict) else {}
    return isinstance(scripts, dict) and PLAN_POINTER in scripts


def _plan_path(root: Path) -> Path:
    return root / PLAN_PATH


def _load_plans(root: Path) -> list[dict[str, Any]]:
    path = _plan_path(root)
    return read_jsonl(path) if path.exists() else []


def _load_run(run_id: str, root: Path) -> dict[str, Any]:
    runs = read_jsonl(
        root / "lab" / "second_brain" / "staging" / "distillation_runs.jsonl"
    )
    matches = [row for row in runs if row["id"] == run_id]
    if len(matches) != 1:
        raise ValidationFailure(
            f"expected one distillation run {run_id}, found {len(matches)}"
        )
    return matches[0]


def _proposal_index(root: Path) -> dict[str, dict[str, Any]]:
    return {
        row["proposal_id"]: row
        for row in read_jsonl(
            root / "lab" / "second_brain" / "staging" / "proposals.jsonl"
        )
    }


def _registry_hashes(root: Path) -> tuple[dict[str, Any], str, str]:
    registry = load_ontology_registry(root)
    source_units = load_source_units(root) if source_registry_required(root) else []
    return registry, sha256_value(registry), sha256_value(source_units)


def _current_records(
    curated: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    return {
        row["id"]: row
        for rows in curated.values()
        for row in rows
    }


def _concept_references(proposal_type: str, record: dict[str, Any]) -> set[str]:
    if proposal_type == "edge":
        return {record["u"], record["v"]}
    if proposal_type == "mapping":
        return {record["concept_id"]}
    if proposal_type == "rule":
        return referenced_concept_ids(record)
    if proposal_type in {
        "claim", "equation", "method", "mechanism", "reasoning_policy"
    }:
        return set(record.get("concept_ids", []))
    return set()


def _control_targets(
    proposal_type: str, record: dict[str, Any]
) -> tuple[list[str], list[str]]:
    target_types: set[str] = set()
    target_ids: set[str] = set()
    if proposal_type == "mapping":
        target_types.add(record["target_type"])
        target_ids.add(record["target_id"])
    if proposal_type == "equation":
        target_types.update("numeric_control" for _ in record.get("operational_mappings", []))
        target_ids.update(
            row["control_id"] for row in record.get("operational_mappings", [])
        )
    if proposal_type == "mechanism":
        target_types.update("control" for _ in record.get("controls", []))
        target_ids.update(record.get("controls", []))
    return sorted(target_types), sorted(target_ids)


def _metric_ids(value: Any) -> list[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "metric_id" and isinstance(item, str) and item:
                found.add(item)
            else:
                found.update(_metric_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_metric_ids(item))
    return sorted(found)


def _existing_ids(decision: dict[str, Any], records: dict[str, Any]) -> list[str]:
    found = {
        row["id"]
        for row in decision.get("dedup_candidates", [])
        if row["id"] in records
    }
    for reason in decision.get("reasons", []):
        parts = reason.split(":")
        if len(parts) > 1 and parts[1] in records:
            found.add(parts[1])
    suggested = decision.get("suggested_id")
    if suggested in records:
        found.add(suggested)
    return sorted(found)


def _source_units(
    evidence: list[dict[str, Any]], root: Path
) -> tuple[list[str], list[str]]:
    if not source_registry_required(root):
        return [], []
    unit_ids = []
    errors = []
    for row in evidence:
        try:
            unit_ids.append(resolve_typed_source_evidence(row, root)["source_unit_id"])
        except ValidationFailure as exc:
            errors.append(str(exc))
    return sorted(set(unit_ids)), errors


def _classification(
    proposal_type: str,
    record: dict[str, Any],
    registry: dict[str, Any],
    concept_records: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    errors = []
    concept_kind = record.get("kind") if proposal_type == "concept" else None
    layer = record.get("layer") if proposal_type == "concept" else None
    layer_root = registry["layers"].get(layer) if layer is not None else None
    if proposal_type == "concept":
        if concept_kind not in registry["concept_kinds"]:
            errors.append(f"unregistered_concept_kind:{concept_kind}")
        if layer_root is None:
            errors.append(f"unregistered_layer:{layer}")
    related_roots = {
        registry["layers"][concept_records[concept_id]["layer"]]
        for concept_id in _concept_references(proposal_type, record)
        if concept_id in concept_records
        and concept_records[concept_id].get("layer") in registry["layers"]
    }
    if layer_root:
        related_roots.add(layer_root)
    return {
        "concept_kind": concept_kind,
        "layer": layer,
        "layer_root": layer_root,
        "related_layer_roots": sorted(related_roots),
    }, errors


def _graph_fields(
    decision: dict[str, Any],
    decisions: list[dict[str, Any]],
    identity_id: str | None,
) -> dict[str, list[str]]:
    connectivity = decision.get("connectivity", {})
    anchors = {
        row["concept_id"] for row in decision.get("hop_alignment", {}).get("anchors", [])
    }
    anchors.update((connectivity.get("anchor_path") or [])[1:])
    parents: set[str] = set()
    if identity_id:
        for candidate in decisions:
            edge = candidate["proposed_record"]
            if candidate["proposal_type"] != "edge" or edge.get("type") not in STRUCTURAL_EDGE_TYPES:
                continue
            if edge.get("u") == identity_id:
                parents.add(edge["v"])
            elif edge.get("v") == identity_id:
                parents.add(edge["u"])
    return {
        "parent_concept_ids": sorted(parents),
        "anchor_concept_ids": sorted(anchors),
        "structural_edge_candidate_ids": sorted(
            connectivity.get("structural_edge_candidate_ids", [])
        ),
        "operational_edge_candidate_ids": sorted(
            connectivity.get("operational_edge_candidate_ids", [])
        ),
        "mapping_candidate_ids": sorted(connectivity.get("mapping_candidate_ids", [])),
    }


def _disposition(
    decision: dict[str, Any],
    graph: dict[str, list[str]],
    existing_ids: list[str],
) -> str:
    admitted = decision["disposition"] in STAGE_DISPOSITIONS
    if decision["disposition"] in {"already_curated", "already_staged", "reject_exact_duplicate"}:
        return "merge"
    if not admitted:
        return "needs_review"
    record = decision["proposed_record"]
    supersedes = record.get("validity", {}).get("supersedes", [])
    if supersedes:
        return "supersede"
    if decision["proposal_type"] == "claim" and record.get("contradicts_claim_ids"):
        return "contradict"
    if decision["proposal_type"] == "concept":
        refining = any(
            candidate["candidate_id"] in graph["structural_edge_candidate_ids"]
            and candidate["proposed_record"].get("type") == "refines"
            for candidate in decision.get("_all_decisions", [])
        )
        if graph["parent_concept_ids"] and refining:
            return "refine"
        return "new"
    if existing_ids:
        return "needs_review"
    return "extend"


def _placement(
    decision: dict[str, Any],
    decisions: list[dict[str, Any]],
    durable_ids: dict[str, str],
    registry: dict[str, Any],
    curated_records: dict[str, dict[str, Any]],
    concept_records: dict[str, dict[str, Any]],
    terminology_proposal_ids: list[str],
    root: Path,
) -> dict[str, Any]:
    proposal_id = decision.get("proposal_id")
    durable_id = durable_ids.get(proposal_id) if proposal_id else None
    suggested_id = decision.get("suggested_id")
    existing_ids = _existing_ids(decision, curated_records)
    identity_id = durable_id or suggested_id
    graph = _graph_fields(decision, decisions, identity_id)
    classification, errors = _classification(
        decision["proposal_type"], decision["proposed_record"], registry, concept_records
    )
    candidate = {
        "candidate_id": decision["candidate_id"],
        "proposal_type": decision["proposal_type"],
        "proposed_record": decision["proposed_record"],
    }
    terminology_control = candidate_terminology_control(
        candidate,
        terminology_proposal_ids,
        root,
        concept_records=concept_records,
    )
    if terminology_control["unresolved_match_ids"]:
        errors.append(
            "unresolved_terminology:"
            + ",".join(terminology_control["unresolved_match_ids"])
        )
    edge_contract = (
        edge_compatibility(
            decision["proposed_record"],
            concept_records,
            registry,
            candidate=True,
            root=root,
        )
        if decision["proposal_type"] == "edge"
        else None
    )
    if edge_contract is not None and not edge_contract["compatible"]:
        errors.append(
            "edge_compatibility:" + ",".join(edge_contract["reasons"])
        )
    target_types, target_ids = _control_targets(
        decision["proposal_type"], decision["proposed_record"]
    )
    unknown_targets = sorted(set(target_types) - set(registry["mapping_target_types"]))
    namespaces = sorted({re.split(r"[.:]", target_id, maxsplit=1)[0] for target_id in target_ids})
    unknown_namespaces = sorted(set(namespaces) - set(registry["control_namespaces"]))
    if unknown_targets:
        errors.append("unregistered_target_types:" + ",".join(unknown_targets))
    if unknown_namespaces:
        errors.append("unregistered_control_namespaces:" + ",".join(unknown_namespaces))
    if proposal_id and not durable_id:
        errors.append("missing_durable_id_decision")
    if suggested_id and durable_id and suggested_id != durable_id:
        errors.append("durable_id_differs_from_suggested_identity")
    if durable_id in curated_records:
        if _fingerprint(decision["proposed_record"]) != _fingerprint(curated_records[durable_id]):
            errors.append("durable_id_collision_with_different_record")
    if decision["proposal_type"] == "concept":
        incoming_aliases = {
            normalize_concept_identity(value)
            for value in [
                decision["proposed_record"].get("name", ""),
                *decision["proposed_record"].get("nl_triggers", []),
            ]
        }
        for ambiguity in registry["ambiguous_aliases"]:
            if normalize_concept_identity(ambiguity["alias"]) in incoming_aliases and durable_id not in ambiguity["concept_ids"]:
                errors.append(f"declared_ambiguous_alias:{ambiguity['alias']}")
    source_unit_ids, source_errors = _source_units(decision["source_evidence"], root)
    errors.extend(source_errors)
    source_closed = not source_errors and (
        not source_registry_required(root)
        or len(source_unit_ids) == len(decision["source_evidence"])
    )
    disposition = _disposition(
        {**decision, "_all_decisions": decisions}, graph, existing_ids
    )
    admitted = decision["disposition"] in STAGE_DISPOSITIONS
    structurally_connected = (
        decision["proposal_type"] != "concept"
        or bool(graph["structural_edge_candidate_ids"] and graph["anchor_concept_ids"])
    )
    operationally_connected = (
        decision["proposal_type"] != "concept"
        or bool(graph["operational_edge_candidate_ids"] or graph["mapping_candidate_ids"])
    )
    if admitted and decision["proposal_type"] == "concept" and not structurally_connected:
        errors.append("missing_closed_structural_placement")
    if admitted and decision["proposal_type"] == "concept" and not operationally_connected:
        errors.append("missing_closed_operational_bridge")
    if errors and admitted:
        disposition = "needs_review"
    eligible = admitted and not errors and disposition != "needs_review"
    projection_nodes = []
    projection_relationships = []
    if eligible and durable_id:
        if decision["proposal_type"] in {
            "concept", "intent", "claim", "equation", "method", "mechanism", "reasoning_policy"
        }:
            projection_nodes.append(durable_id)
        else:
            projection_relationships.append(durable_id)
    placement = {
        "schema": "cpcs.ontology_placement/1.0",
        "candidate_id": decision["candidate_id"],
        "proposal_id": proposal_id,
        "proposal_type": decision["proposal_type"],
        "disposition": disposition,
        "identity": {
            "suggested_id": suggested_id,
            "durable_id": durable_id,
            "existing_ids": existing_ids,
            "fingerprint": decision["fingerprint"],
            "unchanged_id": bool(suggested_id and suggested_id == durable_id),
        },
        "classification": classification,
        "terminology_control": terminology_control,
        "edge_compatibility": edge_contract,
        "graph": graph,
        "controls": {
            "target_types": target_types,
            "namespaces": namespaces,
            "target_ids": target_ids,
        },
        "metric_ids": _metric_ids(decision["proposed_record"]),
        "source_unit_ids": source_unit_ids,
        "coverage": {
            "source_evidence_count": len(decision["source_evidence"]),
            "source_closed": source_closed,
            "structurally_connected": structurally_connected,
            "operationally_connected": operationally_connected,
        },
        "effects": {
            "authority_stores": [AUTHORITY_STORES[decision["proposal_type"]]] if eligible else [],
            "derived_indexes": DERIVED_INDEXES[decision["proposal_type"]] if eligible else [],
            "projection_nodes": projection_nodes,
            "projection_relationships": projection_relationships,
        },
        "promotion": {
            "eligible": eligible,
            "reasons": (
                ["distillation_admitted", "registry_closed", "source_closed"]
                if eligible else sorted(set(errors or decision["reasons"]))
            ),
            "review_requirements": (
                [
                    "source_verified", "source_locator_resolved", "duplicate_checked",
                    "operationally_useful", "relationships_validated",
                    "numeric_precision_supported",
                ] if eligible else ["resolve_placement_before_promotion"]
            ),
        },
    }
    placement["placement_hash"] = content_hash(placement, ("placement_hash",))
    validate_instance("ontology_placement", placement, root)
    return placement


@authority_writer("ontology_placement")
def plan_graph_growth(
    run_id: str,
    durable_ids: dict[str, str],
    root: Path = REPO_ROOT,
    *,
    terminology_proposal_ids: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Build and append one content-addressed staging-only placement plan."""
    run = _load_run(run_id, root)
    proposal_ids = sorted(run["proposal_ids"])
    terminology_by_proposal = {
        key: sorted(set(value))
        for key, value in (terminology_proposal_ids or {}).items()
    }
    if unexpected := sorted(set(terminology_by_proposal) - set(proposal_ids)):
        raise ValidationFailure(
            "growth-plan terminology assignments reference unknown proposals: "
            + ", ".join(unexpected)
        )
    if any(
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
        for value in (terminology_proposal_ids or {}).values()
    ):
        raise ValidationFailure(
            "growth-plan terminology proposal assignments must be non-empty string arrays"
        )
    if set(durable_ids) != set(proposal_ids):
        missing = sorted(set(proposal_ids) - set(durable_ids))
        extra = sorted(set(durable_ids) - set(proposal_ids))
        raise ValidationFailure(
            f"growth-plan durable ID assignments missing={missing} extra={extra}"
        )
    values = list(durable_ids.values())
    if any(not isinstance(value, str) or not value for value in values):
        raise ValidationFailure("growth-plan durable IDs must be non-empty strings")
    if len(values) != len(set(values)):
        raise ValidationFailure("growth-plan durable IDs must be unique")
    proposals = _proposal_index(root)
    if missing := sorted(set(proposal_ids) - set(proposals)):
        raise ValidationFailure("growth plan references missing proposals: " + ", ".join(missing))
    curated = _load_curated(root)
    current_snapshot = _curated_snapshot_hash(curated)
    if current_snapshot != run["curated_snapshot_hash"]:
        raise ValidationFailure(
            "curated authority changed after distillation; rerun distillation before placement"
        )
    registry, registry_hash, source_registry_hash = _registry_hashes(root)
    current = _current_records(curated)
    concept_records = {row["id"]: row for row in curated["concept"]}
    for decision in run["candidate_decisions"]:
        if decision["proposal_type"] == "concept" and decision.get("suggested_id"):
            concept_records.setdefault(
                decision["suggested_id"],
                {**decision["proposed_record"], "id": decision["suggested_id"]},
            )
    placements = [
        _placement(
            decision, run["candidate_decisions"], durable_ids, registry,
            current, concept_records,
            terminology_by_proposal.get(decision.get("proposal_id"), []),
            root,
        )
        for decision in sorted(run["candidate_decisions"], key=lambda row: row["candidate_id"])
    ]
    eligible = sorted(
        row["proposal_id"] for row in placements
        if row["proposal_id"] and row["promotion"]["eligible"]
    )
    blocked = sorted(set(proposal_ids) - set(eligible))
    input_value = {
        "run_id": run_id,
        "distillation_input_hash": run["input_hash"],
        "distillation_policy_hash": run["policy_hash"],
        "curated_snapshot_hash": current_snapshot,
        "ontology_registry_hash": registry_hash,
        "source_registry_hash": source_registry_hash,
        "durable_ids": dict(sorted(durable_ids.items())),
        "terminology_proposal_ids": terminology_by_proposal,
        "placement_hashes": [row["placement_hash"] for row in placements],
        "policy_hash": POLICY_HASH,
    }
    input_hash = sha256_value(input_value)
    plan = {
        "schema": "cpcs.research_graph_growth_plan/1.0",
        "id": "growth_" + hashlib.sha256(canonical_json_bytes(input_value)).hexdigest()[:24],
        "run_id": run_id,
        "policy_version": POLICY["version"],
        "policy_hash": POLICY_HASH,
        "input_hash": input_hash,
        "curated_snapshot_hash": current_snapshot,
        "ontology_registry_hash": registry_hash,
        "source_registry_hash": source_registry_hash,
        "durable_ids": dict(sorted(durable_ids.items())),
        "terminology_proposal_ids": terminology_by_proposal,
        "placements": placements,
        "promotion_proposal_ids": eligible,
        "blocked_proposal_ids": blocked,
        "affected_authority_stores": sorted({
            value for row in placements for value in row["effects"]["authority_stores"]
        }),
        "affected_derived_indexes": sorted({
            value for row in placements for value in row["effects"]["derived_indexes"]
        }),
        "projection_delta": {
            "node_ids": sorted({
                value for row in placements for value in row["effects"]["projection_nodes"]
            }),
            "relationship_ids": sorted({
                value for row in placements for value in row["effects"]["projection_relationships"]
            }),
            "sync_mode": POLICY["projection_sync_mode"],
        },
        "promotion_ready": not blocked and bool(eligible),
        "authority_effect": "staging_only",
    }
    plan["plan_hash"] = content_hash(plan, ("plan_hash",))
    validate_instance("research_graph_growth_plan", plan, root)
    path = _plan_path(root)
    assert_write_target("placement", path, root)
    rows = _load_plans(root)
    matches = [row for row in rows if row["id"] == plan["id"]]
    if matches:
        if canonical_json_bytes(matches[0]) == canonical_json_bytes(plan):
            return matches[0]
        raise ValidationFailure(f"growth plan ID collision: {plan['id']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(canonical_json_bytes(plan))
    return plan


def _validate_plan_record(plan: dict[str, Any], root: Path) -> None:
    validate_instance("research_graph_growth_plan", plan, root)
    if plan["plan_hash"] != content_hash(plan, ("plan_hash",)):
        raise ValidationFailure(f"growth plan {plan['id']} has invalid plan_hash")
    for placement in plan["placements"]:
        validate_instance("ontology_placement", placement, root)
        if placement["placement_hash"] != content_hash(placement, ("placement_hash",)):
            raise ValidationFailure(
                f"placement {placement['candidate_id']} has invalid placement_hash"
            )


def _plan_terminology_current(
    plan: dict[str, Any],
    run: dict[str, Any],
    curated: dict[str, list[dict[str, Any]]],
    root: Path,
) -> bool:
    decisions = sorted(
        run["candidate_decisions"], key=lambda row: row["candidate_id"]
    )
    placements = sorted(
        plan["placements"], key=lambda row: row["candidate_id"]
    )
    if [row["candidate_id"] for row in decisions] != [
        row["candidate_id"] for row in placements
    ]:
        return False
    concept_records = {row["id"]: row for row in curated["concept"]}
    for decision in decisions:
        if decision["proposal_type"] == "concept" and decision.get("suggested_id"):
            concept_records.setdefault(
                decision["suggested_id"],
                {**decision["proposed_record"], "id": decision["suggested_id"]},
            )
    terminology_by_proposal = plan.get("terminology_proposal_ids", {})
    for decision, placement in zip(decisions, placements):
        recorded = placement.get("terminology_control")
        if recorded is None:
            continue
        current = candidate_terminology_control(
            {
                "candidate_id": decision["candidate_id"],
                "proposal_type": decision["proposal_type"],
                "proposed_record": decision["proposed_record"],
            },
            terminology_by_proposal.get(decision.get("proposal_id"), []),
            root,
            concept_records=concept_records,
        )
        if canonical_json_bytes(current) != canonical_json_bytes(recorded):
            return False
    return True


@authority_reader("ontology_placement_inspect")
def inspect_graph_growth_plan(
    plan_id: str, root: Path = REPO_ROOT
) -> dict[str, Any]:
    matches = [row for row in _load_plans(root) if row["id"] == plan_id]
    if len(matches) != 1:
        raise ValidationFailure(f"expected one growth plan {plan_id}, found {len(matches)}")
    plan = matches[0]
    _validate_plan_record(plan, root)
    run = _load_run(plan["run_id"], root)
    curated = _load_curated(root)
    _, registry_hash, source_registry_hash = _registry_hashes(root)
    current_checks = {
        "distillation_input": plan["run_id"] == run["id"],
        "curated_snapshot": plan["curated_snapshot_hash"] == _curated_snapshot_hash(curated),
        "ontology_registry": plan["ontology_registry_hash"] == registry_hash,
        "source_registry": plan["source_registry_hash"] == source_registry_hash,
        "policy": plan["policy_hash"] == POLICY_HASH,
        "terminology": _plan_terminology_current(
            plan, run, curated, root
        ),
    }
    return {
        "schema": "cpcs.research_graph_growth_plan_inspection/1.0",
        "plan": plan,
        "current_checks": current_checks,
        "current": all(current_checks.values()),
        "authority_effect": "none",
    }


def require_graph_growth_plan(
    run_id: str,
    durable_ids: dict[str, str],
    root: Path = REPO_ROOT,
) -> dict[str, Any] | None:
    """Return the exact current plan or fail before curated mutation."""
    if not placement_required(root):
        return None
    candidates = [
        row for row in _load_plans(root)
        if row["run_id"] == run_id and row["durable_ids"] == dict(sorted(durable_ids.items()))
    ]
    if len(candidates) != 1:
        raise ValidationFailure(
            f"promotion requires one exact ontology placement plan for {run_id}; found {len(candidates)}"
        )
    inspection = inspect_graph_growth_plan(candidates[0]["id"], root)
    plan = inspection["plan"]
    if not inspection["current"]:
        failed = sorted(key for key, value in inspection["current_checks"].items() if not value)
        raise ValidationFailure("growth plan is stale: " + ", ".join(failed))
    if not plan["promotion_ready"] or plan["blocked_proposal_ids"]:
        raise ValidationFailure(
            "growth plan is not promotion ready; blocked=" + ",".join(plan["blocked_proposal_ids"])
        )
    if set(plan["promotion_proposal_ids"]) != set(durable_ids):
        raise ValidationFailure("growth plan promotion set differs from durable ID assignments")
    return plan
