"""Deterministic contract for turning retrieved research candidates into staging decisions."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .authority import authority_reader, authority_writer
import networkx as nx

from .graph import OPERATIONAL_EDGE_TYPES, STRUCTURAL_EDGE_TYPES
from .ingest import stage_proposal
from .rules import referenced_concept_ids
from .validate import (
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    canonical_json_bytes,
    normalize_concept_identity,
    read_jsonl,
    sha256_value,
    validate_instance,
    validate_staging,
)

POLICY = {
    "version": "cpcs-distill/1.4",
    "concept_exact_threshold": 0.92,
    "concept_review_threshold": 0.55,
    "knowledge_object_review_threshold": 0.72,
    "hop_anchor_threshold": 0.18,
    "maximum_hop_anchors": 5,
    "maximum_anchor_neighbors": 12,
    "new_concept_requires_structural_anchor": True,
    "new_concept_requires_operational_bridge": True,
    "symmetric_edge_types": [
        "alternative_to",
        "conflicts_with",
        "pairs_with",
    ],
}
POLICY_HASH = sha256_value(POLICY)
SOURCE_BOUND_OBJECT_TYPES = frozenset({"claim", "equation", "method", "mechanism"})
KNOWLEDGE_OBJECT_TYPES = frozenset(
    {*SOURCE_BOUND_OBJECT_TYPES, "reasoning_policy"}
)

STAGE_DISPOSITIONS = {
    "stage_new",
    "stage_relationship",
    "stage_mapping",
    "stage_rule",
    "stage_intent",
    "stage_claim",
    "stage_equation",
    "stage_method",
    "stage_mechanism",
    "stage_reasoning_policy",
}

CURATED_PATHS = {
    "concept": Path("lab/concepts.jsonl"),
    "edge": Path("lab/second_brain/curated/edges.jsonl"),
    "intent": Path("lab/second_brain/curated/intents.jsonl"),
    "mapping": Path("lab/second_brain/curated/mappings.jsonl"),
    "rule": Path("lab/second_brain/curated/rules.jsonl"),
    "claim": Path("lab/second_brain/curated/claims.jsonl"),
    "equation": Path("lab/second_brain/curated/equations.jsonl"),
    "method": Path("lab/second_brain/curated/methods.jsonl"),
    "mechanism": Path("lab/second_brain/curated/mechanisms.jsonl"),
    "reasoning_policy": Path(
        "lab/second_brain/curated/reasoning_policies.jsonl"
    ),
}
PROVISIONAL_IDS = {
    "edge": "edge_000000",
    "intent": "intent_candidate",
    "mapping": "mapping_candidate",
    "rule": "rule_candidate",
    "claim": "claim_candidate",
    "equation": "equation_candidate",
    "method": "method_candidate",
    "mechanism": "mechanism_candidate",
}


def _validate_candidate_record(candidate: dict[str, Any], root: Path) -> None:
    proposal_type = candidate["proposal_type"]
    if proposal_type == "concept":
        provisional_id = candidate.get("suggested_id")
        if not provisional_id:
            raise ValidationFailure(
                f"concept candidate {candidate['candidate_id']} requires suggested_id"
            )
    elif proposal_type in KNOWLEDGE_OBJECT_TYPES:
        provisional_id = candidate.get("suggested_id")
        if not provisional_id:
            raise ValidationFailure(
                f"{proposal_type} candidate {candidate['candidate_id']} requires suggested_id"
            )
    else:
        provisional_id = PROVISIONAL_IDS[proposal_type]
    record = {**candidate["proposed_record"], "id": provisional_id}
    validate_instance(proposal_type, record, root)
    if proposal_type in SOURCE_BOUND_OBJECT_TYPES:
        record_sources = sorted(
            (row["ref"], row["locator"], row["content_sha256"])
            for row in record["sources"]
        )
        evidence_sources = sorted(
            (row["source_id"], row["locator"], row["content_sha256"])
            for row in candidate["source_evidence"]
        )
        if record_sources != evidence_sources:
            raise ValidationFailure(
                f"{proposal_type} sources must exactly match source evidence locators and hashes"
            )
    if proposal_type == "reasoning_policy":
        evidence_sources = {row["source_id"] for row in candidate["source_evidence"]}
        if not evidence_sources <= set(record["source_refs"]):
            raise ValidationFailure(
                "reasoning_policy source_refs must include every source evidence ID"
            )


def _normalized_text(value: str) -> str:
    return " ".join(value.lower().split())


def _normalized_value(value: Any) -> Any:
    if isinstance(value, str):
        return _normalized_text(value)
    if isinstance(value, list):
        return [_normalized_value(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _normalized_value(item)
            for key, item in sorted(value.items())
            if key not in {"id", "provenance"}
        }
    return value


def _record_essence(record: dict[str, Any]) -> dict[str, Any]:
    return _normalized_value(record)


def _fingerprint(record: dict[str, Any]) -> str:
    return sha256_value(_record_essence(record))


def _tokens(value: Any) -> set[str]:
    if isinstance(value, dict):
        text = " ".join(str(item) for item in value.values())
    elif isinstance(value, list):
        text = " ".join(str(item) for item in value)
    else:
        text = str(value)
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 1
    }


def _concept_tokens(record: dict[str, Any]) -> set[str]:
    return _tokens(
        {
            key: record.get(key, "")
            for key in ("name", "what", "use_when", "nl_triggers", "layer")
        }
    )


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    if not union:
        return 0.0
    return round(len(left & right) / len(union), 6)


def _concept_similarity(
    candidate: dict[str, Any],
    existing: dict[str, Any],
) -> float:
    candidate_name = normalize_concept_identity(str(candidate.get("name", "")))
    existing_name = normalize_concept_identity(str(existing.get("name", "")))
    candidate_aliases = {
        normalize_concept_identity(str(value))
        for value in [candidate.get("name", ""), *candidate.get("nl_triggers", [])]
        if normalize_concept_identity(str(value))
    }
    existing_aliases = {
        normalize_concept_identity(str(value))
        for value in [existing.get("name", ""), *existing.get("nl_triggers", [])]
        if normalize_concept_identity(str(value))
    }
    if candidate_aliases & existing_aliases:
        return 1.0
    name_score = 1.0 if candidate_name and candidate_name == existing_name else _jaccard(
        _tokens(candidate_name),
        _tokens(existing_name),
    )
    body_score = _jaccard(_concept_tokens(candidate), _concept_tokens(existing))
    return round(max(name_score, body_score), 6)


def _knowledge_object_tokens(proposal_type: str, record: dict[str, Any]) -> set[str]:
    fields = {
        "claim": ("statement", "claim_kind"),
        "equation": ("name", "expression", "solved_quantity", "terms"),
        "method": ("name", "purpose", "steps", "outputs"),
        "mechanism": (
            "name",
            "purpose",
            "causal_hypothesis",
            "causal_chain",
            "controls",
        ),
        "reasoning_policy": (
            "display_name",
            "task_classes",
            "executor",
            "execution_strategy",
            "routing_signals",
            "requires",
            "produces",
            "limitations",
        ),
    }[proposal_type]
    return _tokens({key: record.get(key, "") for key in fields})


def _knowledge_object_similarity(
    proposal_type: str,
    candidate: dict[str, Any],
    existing: dict[str, Any],
) -> float:
    if proposal_type == "equation":
        candidate_expression = re.sub(r"\s+", "", candidate.get("expression", ""))
        existing_expression = re.sub(r"\s+", "", existing.get("expression", ""))
        if candidate_expression and candidate_expression == existing_expression:
            return 1.0
    return _jaccard(
        _knowledge_object_tokens(proposal_type, candidate),
        _knowledge_object_tokens(proposal_type, existing),
    )


def _object_references(proposal_type: str, record: dict[str, Any]) -> set[str]:
    references: set[str] = set(record.get("concept_ids", []))
    fields = {
        "claim": ("method_ids", "supports_claim_ids", "contradicts_claim_ids"),
        "equation": ("method_ids", "mechanism_ids"),
        "method": ("equation_ids", "mechanism_ids"),
        "mechanism": ("claim_ids", "method_ids", "equation_ids"),
    }.get(proposal_type, ())
    for field in fields:
        references.update(record.get(field, []))
    if proposal_type == "equation":
        references.update(
            row["method_id"]
            for row in record.get("operational_mappings", [])
            if row.get("method_id")
        )
    references.discard(record.get("id"))
    return references


def _normalize_batch(batch: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(batch))
    normalized["candidates"] = sorted(
        normalized["candidates"],
        key=lambda item: item["candidate_id"],
    )
    for candidate in normalized["candidates"]:
        candidate["source_evidence"] = sorted(
            candidate["source_evidence"],
            key=lambda item: (
                item["source_id"],
                item["locator"],
                item["claim"],
                item.get("content_sha256") or "",
            ),
        )
    return normalized


def _validate_normalized_batch(
    normalized: dict[str, Any], root: Path
) -> None:
    validate_instance("distillation_batch", normalized, root)
    for candidate in normalized["candidates"]:
        _validate_candidate_record(candidate, root)
    candidate_ids = [item["candidate_id"] for item in normalized["candidates"]]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValidationFailure("distillation candidate IDs must be unique")
    suggested_ids = [
        item["suggested_id"]
        for item in normalized["candidates"]
        if item.get("suggested_id")
    ]
    if len(suggested_ids) != len(set(suggested_ids)):
        raise ValidationFailure("suggested durable IDs must be unique within a batch")


def validate_distillation_batch(
    batch: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Validate one candidate batch without staging or authority mutation."""
    normalized = _normalize_batch(batch)
    _validate_normalized_batch(normalized, root)
    result = {
        "schema": "cpcs.distillation_batch_validation/1.0",
        "valid": True,
        "batch_id": normalized["batch_id"],
        "batch_hash": sha256_value(normalized),
        "candidate_count": len(normalized["candidates"]),
        "proposal_types": sorted(
            {row["proposal_type"] for row in normalized["candidates"]}
        ),
        "source_evidence_count": sum(
            len(row["source_evidence"]) for row in normalized["candidates"]
        ),
        "policy_version": POLICY["version"],
        "policy_hash": POLICY_HASH,
        "authority_effect": "none",
    }
    validate_instance("distillation_batch_validation", result, root)
    return result


def _load_curated(root: Path) -> dict[str, list[dict[str, Any]]]:
    return {
        kind: read_jsonl(root / relative)
        for kind, relative in CURATED_PATHS.items()
    }


def _curated_snapshot_hash(
    curated: dict[str, list[dict[str, Any]]],
) -> str:
    return sha256_value(
        {
            kind: sorted(rows, key=lambda item: item["id"])
            for kind, rows in sorted(curated.items())
        }
    )


def _provenance_index(
    curated: dict[str, list[dict[str, Any]]],
) -> dict[str, str]:
    return {
        proposal_id: row["id"]
        for rows in curated.values()
        for row in rows
        if (
            proposal_id := row.get("provenance", {}).get("proposal_id")
        )
    }


def _authored_graph(
    concepts: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(row["id"] for row in concepts)
    graph.add_edges_from((row["u"], row["v"]) for row in edges)
    return graph


def _anchor_rows(
    candidate: dict[str, Any],
    curated: dict[str, list[dict[str, Any]]],
    graph: nx.Graph,
) -> list[dict[str, Any]]:
    concepts = curated["concept"]
    proposal_type = candidate["proposal_type"]
    record = candidate["proposed_record"]
    scored: dict[str, tuple[float, str]] = {}
    if proposal_type == "concept":
        for concept in concepts:
            score = _concept_similarity(record, concept)
            if score >= POLICY["hop_anchor_threshold"]:
                scored[concept["id"]] = (score, "semantic_overlap")
    elif proposal_type == "edge":
        for concept_id in (record.get("u"), record.get("v")):
            if concept_id in graph:
                scored[concept_id] = (1.0, "edge_endpoint")
    elif proposal_type == "mapping":
        concept_id = record.get("concept_id")
        if concept_id in graph:
            scored[concept_id] = (1.0, "mapping_subject")
    elif proposal_type == "rule":
        for concept_id in referenced_concept_ids(record):
            if concept_id in graph:
                scored[concept_id] = (1.0, "rule_reference")
    elif proposal_type in KNOWLEDGE_OBJECT_TYPES:
        for concept_id in record.get("concept_ids", []):
            if concept_id in graph:
                scored[concept_id] = (1.0, f"{proposal_type}_subject")
    anchors = []
    for concept_id, (score, reason) in sorted(
        scored.items(),
        key=lambda item: (-item[1][0], item[0]),
    )[: POLICY["maximum_hop_anchors"]]:
        anchors.append(
            {
                "concept_id": concept_id,
                "score": score,
                "reason": reason,
                "neighbor_ids": sorted(graph.neighbors(concept_id))[
                    : POLICY["maximum_anchor_neighbors"]
                ],
            }
        )
    return anchors


def _existing_path(
    candidate: dict[str, Any],
    graph: nx.Graph,
) -> list[str] | None:
    if candidate["proposal_type"] != "edge":
        return None
    record = candidate["proposed_record"]
    u, v = record.get("u"), record.get("v")
    if u not in graph or v not in graph:
        return None
    try:
        return nx.shortest_path(graph, u, v)
    except nx.NetworkXNoPath:
        return None


def _exact_record_match(
    proposal_type: str,
    record: dict[str, Any],
    curated: dict[str, list[dict[str, Any]]],
) -> str | None:
    essence = _record_essence(record)
    for existing in curated[proposal_type]:
        if _record_essence(existing) == essence:
            return existing["id"]
    if proposal_type != "edge":
        return None
    symmetric = set(POLICY["symmetric_edge_types"])
    if record.get("type") not in symmetric:
        return None
    reverse = dict(record)
    reverse["u"], reverse["v"] = record.get("v"), record.get("u")
    reverse_essence = _record_essence(reverse)
    for existing in curated["edge"]:
        if _record_essence(existing) == reverse_essence:
            return existing["id"]
    return None


def _dedup_rows(
    candidate: dict[str, Any],
    curated: dict[str, list[dict[str, Any]]],
    batch_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    proposal_type = candidate["proposal_type"]
    record = candidate["proposed_record"]
    rows = []
    if proposal_type == "concept":
        comparisons = [
            (existing["id"], existing, "curated concept")
            for existing in curated["concept"]
        ]
        threshold = POLICY["concept_review_threshold"]
        similarity = _concept_similarity
    elif proposal_type in KNOWLEDGE_OBJECT_TYPES:
        comparisons = [
            (existing["id"], existing, f"curated {proposal_type}")
            for existing in curated[proposal_type]
        ]
        comparisons.extend(
            (
                existing["candidate_id"],
                existing["proposed_record"],
                f"same-batch {proposal_type}",
            )
            for existing in batch_candidates
            if existing["proposal_type"] == proposal_type
            and (
                str(existing.get("suggested_id") or ""),
                existing["candidate_id"],
            )
            < (
                str(candidate.get("suggested_id") or ""),
                candidate["candidate_id"],
            )
        )
        threshold = POLICY["knowledge_object_review_threshold"]
        similarity = lambda left, right: _knowledge_object_similarity(  # noqa: E731
            proposal_type, left, right
        )
    else:
        return []
    for existing_id, existing, scope in comparisons:
        score = similarity(record, existing)
        if score >= threshold:
            rows.append(
                {
                    "id": existing_id,
                    "reason": f"deterministic {proposal_type} semantic overlap with {scope}",
                    "score": score,
                }
            )
    return sorted(rows, key=lambda item: (-item["score"], item["id"]))[:5]


def _dependencies_and_missing(
    candidate: dict[str, Any],
    curated_ids: set[str],
    suggested_ids: dict[str, str],
) -> tuple[list[str], list[str]]:
    proposal_type = candidate["proposal_type"]
    record = candidate["proposed_record"]
    references: set[str] = set()
    if proposal_type == "edge":
        references.update(
            value for value in (record.get("u"), record.get("v")) if value
        )
    elif proposal_type == "mapping":
        if record.get("concept_id"):
            references.add(record["concept_id"])
    elif proposal_type == "rule":
        references.update(referenced_concept_ids(record))
    elif proposal_type in KNOWLEDGE_OBJECT_TYPES:
        references.update(_object_references(proposal_type, record))
    dependencies = sorted(
        suggested_ids[item]
        for item in references
        if item in suggested_ids
    )
    missing = sorted(
        item
        for item in references
        if item not in curated_ids and item not in suggested_ids
    )
    return dependencies, missing


def _has_hashed_evidence(candidate: dict[str, Any]) -> bool:
    return all(
        evidence.get("content_sha256") is not None
        for evidence in candidate["source_evidence"]
    )


def _connectivity_proofs(
    candidates: list[dict[str, Any]],
    curated_concept_ids: set[str],
) -> dict[str, dict[str, Any]]:
    suggested_concepts = {
        candidate["suggested_id"]: candidate
        for candidate in candidates
        if candidate["proposal_type"] == "concept"
        and candidate.get("suggested_id")
    }
    valid_concept_ids = curated_concept_ids | set(suggested_concepts)
    structural_graph = nx.Graph()
    structural_graph.add_nodes_from(valid_concept_ids)
    operational_by_concept: dict[str, list[str]] = {
        concept_id: [] for concept_id in suggested_concepts
    }
    mapping_by_concept: dict[str, list[str]] = {
        concept_id: [] for concept_id in suggested_concepts
    }
    for candidate in candidates:
        if not _has_hashed_evidence(candidate):
            continue
        record = candidate["proposed_record"]
        if candidate["proposal_type"] == "edge":
            u, v = record.get("u"), record.get("v")
            if u not in valid_concept_ids or v not in valid_concept_ids:
                continue
            edge_type = record.get("type")
            if edge_type in STRUCTURAL_EDGE_TYPES:
                structural_graph.add_edge(
                    u,
                    v,
                    candidate_id=candidate["candidate_id"],
                )
            if edge_type in OPERATIONAL_EDGE_TYPES:
                for concept_id in (u, v):
                    if concept_id in operational_by_concept:
                        operational_by_concept[concept_id].append(
                            candidate["candidate_id"]
                        )
        elif candidate["proposal_type"] == "mapping":
            concept_id = record.get("concept_id")
            if concept_id in mapping_by_concept:
                mapping_by_concept[concept_id].append(
                    candidate["candidate_id"]
                )

    proofs: dict[str, dict[str, Any]] = {}
    for concept_id, candidate in sorted(suggested_concepts.items()):
        paths = []
        for anchor_id in sorted(curated_concept_ids):
            if not nx.has_path(structural_graph, concept_id, anchor_id):
                continue
            path = nx.shortest_path(structural_graph, concept_id, anchor_id)
            paths.append(path)
        anchor_path = min(paths, key=lambda path: (len(path), path)) if paths else None
        structural_ids = []
        if anchor_path:
            structural_ids = [
                structural_graph.edges[left, right]["candidate_id"]
                for left, right in zip(anchor_path, anchor_path[1:])
            ]
        operational_ids = sorted(set(operational_by_concept[concept_id]))
        mapping_ids = sorted(set(mapping_by_concept[concept_id]))
        reasons = []
        if not anchor_path:
            reasons.append("missing_structural_path_to_curated_concept")
        if not operational_ids and not mapping_ids:
            reasons.append("missing_operational_edge_or_mapping")
        proofs[candidate["candidate_id"]] = {
            "connected": not reasons,
            "structural_edge_candidate_ids": structural_ids,
            "operational_edge_candidate_ids": operational_ids,
            "mapping_candidate_ids": mapping_ids,
            "anchor_path": anchor_path,
            "reasons": reasons,
        }
    return proofs


def _stage_disposition(proposal_type: str) -> str:
    return {
        "concept": "stage_new",
        "edge": "stage_relationship",
        "mapping": "stage_mapping",
        "rule": "stage_rule",
        "intent": "stage_intent",
        "claim": "stage_claim",
        "equation": "stage_equation",
        "method": "stage_method",
        "mechanism": "stage_mechanism",
        "reasoning_policy": "stage_reasoning_policy",
    }[proposal_type]


def _stage_action(proposal_type: str) -> str:
    return {
        "concept": "add_candidate",
        "edge": "add_relationship_candidate",
        "mapping": "add_mapping_candidate",
        "rule": "add_rule_candidate",
        "intent": "add_intent_candidate",
        "claim": "add_claim_candidate",
        "equation": "add_equation_candidate",
        "method": "add_method_candidate",
        "mechanism": "add_mechanism_candidate",
        "reasoning_policy": "add_reasoning_policy_candidate",
    }[proposal_type]


def _decision(
    candidate: dict[str, Any],
    curated: dict[str, list[dict[str, Any]]],
    graph: nx.Graph,
    provenance: dict[str, str],
    staged_ids: set[str],
    suggested_ids: dict[str, str],
    connectivity_proofs: dict[str, dict[str, Any]],
    batch_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    proposal_type = candidate["proposal_type"]
    record = candidate["proposed_record"]
    original_proposal_id = candidate.get("original_proposal_id")
    fingerprint = _fingerprint(record)
    dedup = _dedup_rows(candidate, curated, batch_candidates)
    dependencies, missing = _dependencies_and_missing(
        candidate,
        {row["id"] for rows in curated.values() for row in rows},
        suggested_ids,
    )
    hop_alignment = {
        "anchors": _anchor_rows(candidate, curated, graph),
        "existing_path": _existing_path(candidate, graph),
    }
    connectivity = connectivity_proofs.get(candidate["candidate_id"])
    disposition: str
    reasons: list[str]
    refactors: list[dict[str, Any]]
    proposal_id: str | None = None

    if original_proposal_id and original_proposal_id in provenance:
        target = provenance[original_proposal_id]
        disposition = "already_curated"
        reasons = [f"provenance_match:{target}"]
        refactors = [
            {
                "action": "preserve_durable_id",
                "target_id": target,
                "reason": "The proposal already produced this curated record.",
            }
        ]
        proposal_id = original_proposal_id
    elif original_proposal_id and original_proposal_id in staged_ids:
        disposition = "already_staged"
        reasons = [f"staging_match:{original_proposal_id}"]
        refactors = [
            {
                "action": "preserve_durable_id",
                "target_id": candidate.get("suggested_id"),
                "reason": "The same proposal is already waiting in staging.",
            }
        ]
        proposal_id = original_proposal_id
    elif any(
        evidence.get("content_sha256") is None
        for evidence in candidate["source_evidence"]
    ):
        disposition = "reject_unhashed_evidence"
        reasons = ["source_evidence_missing_content_hash"]
        refactors = [
            {
                "action": "supply_evidence_hash",
                "target_id": None,
                "reason": "Traceable distillation requires a hash for every source passage.",
            }
        ]
    elif (exact_id := _exact_record_match(proposal_type, record, curated)):
        disposition = "reject_exact_duplicate"
        reasons = [f"exact_curated_record:{exact_id}"]
        refactors = [
            {
                "action": "discard_duplicate",
                "target_id": exact_id,
                "reason": "The normalized candidate record already exists.",
            }
        ]
    elif (
        proposal_type == "concept"
        and dedup
        and dedup[0]["score"] >= POLICY["concept_exact_threshold"]
    ):
        target = dedup[0]["id"]
        disposition = "reject_exact_duplicate"
        reasons = [f"concept_similarity_exact:{target}:{dedup[0]['score']:.6f}"]
        refactors = [
            {
                "action": "discard_duplicate",
                "target_id": target,
                "reason": "Concept similarity exceeded the exact-duplicate threshold.",
            }
        ]
    elif proposal_type == "concept" and dedup:
        target = dedup[0]["id"]
        disposition = "review_possible_duplicate"
        reasons = [f"concept_similarity_review:{target}:{dedup[0]['score']:.6f}"]
        refactors = [
            {
                "action": "merge_review",
                "target_id": target,
                "reason": "A curator must choose merge, refine, or separate identity.",
            }
        ]
    elif proposal_type in KNOWLEDGE_OBJECT_TYPES and dedup:
        target = dedup[0]["id"]
        disposition = "review_possible_duplicate"
        reasons = [
            f"{proposal_type}_semantic_review:{target}:{dedup[0]['score']:.6f}"
        ]
        refactors = [
            {
                "action": "merge_review",
                "target_id": target,
                "reason": (
                    "A curator must preserve independent sources and conflicts while "
                    "choosing merge, support, contradiction, or separate identity."
                ),
            }
        ]
    elif missing:
        disposition = "reject_invalid_reference"
        reasons = ["missing_concept_references:" + ",".join(missing)]
        refactors = [
            {
                "action": "repair_reference",
                "target_id": item,
                "reason": "The candidate references no curated or same-batch concept.",
            }
            for item in missing
        ]
    elif (
        proposal_type == "concept"
        and connectivity is not None
        and not connectivity["connected"]
    ):
        disposition = "reject_unconnected_concept"
        reasons = list(connectivity["reasons"])
        refactors = [
            {
                "action": "supply_connectivity",
                "target_id": candidate.get("suggested_id"),
                "reason": (
                    "Add a typed structural path to a curated concept and an "
                    "operational edge or executable mapping."
                ),
            }
        ]
    else:
        disposition = _stage_disposition(proposal_type)
        reasons = ["distinct_candidate_with_resolved_lineage"]
        refactors = [
            {
                "action": _stage_action(proposal_type),
                "target_id": candidate.get("suggested_id"),
                "reason": "The candidate passed deterministic staging policy.",
            }
        ]

    decision = {
        "candidate_id": candidate["candidate_id"],
        "proposal_type": proposal_type,
        "suggested_id": candidate.get("suggested_id"),
        "fingerprint": fingerprint,
        "proposed_record": record,
        "source_evidence": candidate["source_evidence"],
        "disposition": disposition,
        "reasons": reasons,
        "dedup_candidates": dedup,
        "hop_alignment": hop_alignment,
        "dependencies": dependencies,
        "refactor_actions": refactors,
        "proposal_id": proposal_id,
    }
    if connectivity is not None:
        decision["connectivity"] = connectivity
    return decision


def _summary(decisions: list[dict[str, Any]]) -> dict[str, int]:
    dispositions = Counter(item["disposition"] for item in decisions)
    return {
        "candidates": len(decisions),
        "staged": sum(dispositions[item] for item in STAGE_DISPOSITIONS),
        "already_curated": dispositions["already_curated"],
        "already_staged": dispositions["already_staged"],
        "exact_duplicates": dispositions["reject_exact_duplicate"],
        "review_required": dispositions["review_possible_duplicate"],
        "invalid": (
            dispositions["reject_invalid_reference"]
            + dispositions["reject_unconnected_concept"]
            + dispositions["reject_unhashed_evidence"]
        ),
    }


def _reconcile_bundle_dependencies(
    decisions: list[dict[str, Any]],
) -> None:
    by_candidate = {
        decision["candidate_id"]: decision
        for decision in decisions
    }
    concept_by_suggested_id = {
        decision["suggested_id"]: decision
        for decision in decisions
        if decision["proposal_type"] == "concept"
        and decision.get("suggested_id")
    }
    admitted = STAGE_DISPOSITIONS | {"already_curated", "already_staged"}
    changed = True
    while changed:
        changed = False
        for decision in decisions:
            connectivity = decision.get("connectivity")
            if (
                decision["disposition"] == "stage_new"
                and connectivity
            ):
                structural_ids = connectivity[
                    "structural_edge_candidate_ids"
                ]
                bridge_ids = (
                    connectivity["operational_edge_candidate_ids"]
                    + connectivity["mapping_candidate_ids"]
                )
                intermediate_decisions = [
                    concept_by_suggested_id[concept_id]
                    for concept_id in (connectivity["anchor_path"] or [])[1:-1]
                    if concept_id in concept_by_suggested_id
                ]
                missing_members = [
                    candidate_id
                    for candidate_id in structural_ids
                    if by_candidate[candidate_id]["disposition"] not in admitted
                ]
                missing_members.extend(
                    member["candidate_id"]
                    for member in intermediate_decisions
                    if member["disposition"] not in admitted
                )
                bridge_available = any(
                    by_candidate[candidate_id]["disposition"] in admitted
                    for candidate_id in bridge_ids
                )
                if missing_members or not bridge_available:
                    decision["disposition"] = "reject_unconnected_concept"
                    decision["reasons"] = [
                        "connectivity_member_not_admitted:"
                        + ",".join(sorted(set(missing_members)))
                    ] if missing_members else [
                        "operational_bridge_not_admitted"
                    ]
                    decision["refactor_actions"] = [
                        {
                            "action": "supply_connectivity",
                            "target_id": decision.get("suggested_id"),
                            "reason": (
                                "All structural placement members and at least "
                                "one operational bridge must pass admission."
                            ),
                        }
                    ]
                    changed = True
                    continue
            if decision["disposition"] not in STAGE_DISPOSITIONS:
                continue
            rejected_dependencies = [
                dependency_id
                for dependency_id in decision["dependencies"]
                if by_candidate[dependency_id]["disposition"] not in admitted
            ]
            if not rejected_dependencies:
                continue
            decision["disposition"] = "reject_invalid_reference"
            decision["reasons"] = [
                "dependency_not_admitted:" + ",".join(rejected_dependencies)
            ]
            decision["refactor_actions"] = [
                {
                    "action": "repair_reference",
                    "target_id": dependency_id,
                    "reason": (
                        "The relationship cannot stage because its same-batch "
                        "concept failed admission."
                    ),
                }
                for dependency_id in rejected_dependencies
            ]
            changed = True


def _proposal_for_decision(
    decision: dict[str, Any],
    candidate: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    digest = sha256_value(candidate["candidate_id"])[7:19]
    proposal_id = f"proposal_{run_id}_{digest}"
    decision["proposal_id"] = proposal_id
    return {
        "proposal_id": proposal_id,
        "proposal_type": decision["proposal_type"],
        "status": "pending",
        "proposed_record": decision["proposed_record"],
        "source_evidence": decision["source_evidence"],
        "dedup_candidates": decision["dedup_candidates"],
        "created_by": candidate["created_by"],
        "created_at": candidate["created_at"],
        "promotion": None,
        "rejection_reason": None,
    }


@authority_writer("staging")
def run_distillation(
    batch: dict[str, Any],
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    normalized = _normalize_batch(batch)
    _validate_normalized_batch(normalized, root)
    suggested_ids = {
        item["suggested_id"]: item["candidate_id"]
        for item in normalized["candidates"]
        if item.get("suggested_id")
    }

    curated = _load_curated(root)
    snapshot_hash = _curated_snapshot_hash(curated)
    input_hash = sha256_value(normalized)
    run_id = "distill_" + sha256_value(
        {
            "input_hash": input_hash,
            "policy_hash": POLICY_HASH,
            "curated_snapshot_hash": snapshot_hash,
        }
    )[7:31]
    staged = read_jsonl(
        root / "lab" / "second_brain" / "staging" / "proposals.jsonl"
    )
    graph = _authored_graph(curated["concept"], curated["edge"])
    provenance = _provenance_index(curated)
    connectivity_proofs = _connectivity_proofs(
        normalized["candidates"],
        {row["id"] for row in curated["concept"]},
    )
    decisions = [
        _decision(
            candidate,
            curated,
            graph,
            provenance,
            {item["proposal_id"] for item in staged},
            suggested_ids,
            connectivity_proofs,
            normalized["candidates"],
        )
        for candidate in normalized["candidates"]
    ]
    _reconcile_bundle_dependencies(decisions)
    candidates_by_id = {
        item["candidate_id"]: item for item in normalized["candidates"]
    }
    proposals = []
    for decision in decisions:
        if decision["disposition"] in STAGE_DISPOSITIONS:
            proposal = _proposal_for_decision(
                decision,
                candidates_by_id[decision["candidate_id"]],
                run_id,
            )
            validate_instance("proposal", proposal, root)
            proposals.append(proposal)

    record = {
        "id": run_id,
        "batch_id": normalized["batch_id"],
        "input_hash": input_hash,
        "policy_version": POLICY["version"],
        "policy_hash": POLICY_HASH,
        "curated_snapshot_hash": snapshot_hash,
        "retrieval": normalized["retrieval"],
        "extractor": normalized["extractor"],
        "candidate_decisions": decisions,
        "proposal_ids": sorted(
            item["proposal_id"] for item in decisions if item["proposal_id"]
        ),
        "summary": _summary(decisions),
    }
    validate_instance("distillation_run", record, root)
    for proposal in proposals:
        stage_proposal(proposal, root, run_id)

    path = (
        root
        / "lab"
        / "second_brain"
        / "staging"
        / "distillation_runs.jsonl"
    )
    assert_write_target("distill", path, root)
    rows = read_jsonl(path)
    matches = [item for item in rows if item["id"] == run_id]
    if matches:
        if canonical_json_bytes(matches[0]) != canonical_json_bytes(record):
            raise ValidationFailure(f"distillation run ID collision: {run_id}")
        validate_staging(root)
        return matches[0]
    with path.open("ab") as handle:
        handle.write(canonical_json_bytes(record))
    validate_staging(root)
    return record


def audit_staging(root: Path = REPO_ROOT) -> dict[str, Any]:
    proposals = read_jsonl(
        root / "lab" / "second_brain" / "staging" / "proposals.jsonl"
    )
    promoted_proposal_ids = set(_provenance_index(_load_curated(root)))
    proposals = [
        proposal
        for proposal in proposals
        if proposal["proposal_id"] not in promoted_proposal_ids
    ]
    if not proposals:
        raise ValidationFailure("no unpromoted staging proposals exist to audit")
    candidates = [
        {
            "candidate_id": "candidate_" + proposal["proposal_id"][9:],
            "proposal_type": proposal["proposal_type"],
            "suggested_id": (
                proposal["proposed_record"].get("id")
                if proposal["proposal_type"] == "concept"
                else None
            ),
            "original_proposal_id": proposal["proposal_id"],
            "proposed_record": proposal["proposed_record"],
            "source_evidence": proposal["source_evidence"],
            "created_by": proposal["created_by"],
            "created_at": proposal["created_at"],
        }
        for proposal in proposals
    ]
    latest = max(item["created_at"] for item in proposals)
    batch = {
        "batch_id": "batch_staging_" + sha256_value(
            sorted(item["proposal_id"] for item in proposals)
        )[7:23],
        "retrieval": {
            "adapter": "staging_backfill",
            "corpus_id": None,
            "query": "audit existing staging proposals",
            "tool": "existing_staging_store",
            "parameters": {"proposal_count": len(proposals)},
            "retrieved_at": latest,
        },
        "extractor": {
            "agent": "historical_proposal_backfill",
            "model": "recorded-by-original-proposal",
            "prompt_hash": sha256_value(
                {"contract": "historical staging proposal audit"}
            ),
        },
        "candidates": candidates,
    }
    return run_distillation(batch, root)


@authority_reader("distillation_status_snapshot")
def status(root: Path = REPO_ROOT) -> dict[str, Any]:
    runs = read_jsonl(
        root
        / "lab"
        / "second_brain"
        / "staging"
        / "distillation_runs.jsonl"
    )
    dispositions = Counter(
        decision["disposition"]
        for run in runs
        for decision in run["candidate_decisions"]
    )
    return {
        "policy_version": POLICY["version"],
        "policy_hash": POLICY_HASH,
        "runs": len(runs),
        "decisions": sum(dispositions.values()),
        "dispositions": dict(sorted(dispositions.items())),
        "latest_run_id": runs[-1]["id"] if runs else None,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("batch", type=Path)
    sub.add_parser("audit-staging")
    sub.add_parser("status")
    args = parser.parse_args(argv)
    if args.command == "run":
        result = run_distillation(json.loads(args.batch.read_text()))
    elif args.command == "audit-staging":
        result = audit_staging()
    else:
        result = status()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
