"""Reviewed VOG bridges, Pegasus research gaps, and comparison lenses."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from .authority import authority_reader, authority_writer
from .query import QUERY_POLICY, default_request, reason
from .validate import (
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    content_hash,
    read_jsonl,
    sha256_value,
    validate_instance,
    write_jsonl,
)
from .video_observation import validate_video_observation_graph


GAP_POLICY = "cpcs-video-research-gap/1.0"
LENS_POLICY = "cpcs-knowledge-comparison-lens/1.0"
LAYER_MAP = {
    "entity": "identity",
    "beat": "narrative",
    "action": "motion",
    "camera": "camera",
    "performance": "performance",
    "face_affect": "affect",
    "audio": "audio",
    "marketing": "marketing",
    "measurement": "measurement",
    "verification": "validation",
    "quality": "quality",
}
WORD = re.compile(r"[a-z0-9]+")


def _observations(vog: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        (
            copy.deepcopy(node["data"])
            for node in vog["nodes"]
            if node["node_type"] in {"observation", "measurement", "segment"}
        ),
        key=lambda row: row["observation_id"],
    )


def _claim_text(observation: dict[str, Any]) -> str:
    return json.dumps(
        observation["claim"],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _frame(vog: dict[str, Any], domain: str | None) -> dict[str, Any]:
    layers = sorted(
        {
            LAYER_MAP[row["layer"]]
            for row in _observations(vog)
            if row["layer"] in LAYER_MAP
        }
    )
    return {
        "schema": "cpcs.retrieval_frame/1.0",
        "domain_masks": [domain] if domain else [],
        "hard_constraints": ["preserve Pegasus evidence class", "preserve contradictions"],
        "required_coverage_slots": layers,
        "excluded_layers": [],
        "requested_outputs": ["concept", "mapping", "claim", "method", "mechanism", "source_passage"],
        "root_budget": QUERY_POLICY["maximum_roots"],
        "hop_budget": 5,
        "prerequisite_budget": 25 - QUERY_POLICY["maximum_roots"],
        "token_budget": 12000,
    }


def _query(vog: dict[str, Any], query: str | None) -> str:
    claims = " ".join(_claim_text(row) for row in _observations(vog))
    value = " ".join(part for part in (query, claims) if part).strip()
    if not value:
        raise ValidationFailure("video reasoning requires a query or observations")
    return value


def _vog_identity(vog: dict[str, Any]) -> dict[str, Any]:
    return {
        "graph_id": vog["graph_id"],
        "graph_hash": vog["graph_hash"],
        "source_id": vog["source"]["source_id"],
        "source_sha256": vog["source"]["sha256"],
    }


def _bridges_for_vog(vog: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    path = root / "lab" / "second_brain" / "curated" / "video_concept_bridges.jsonl"
    return sorted(
        (
            row
            for row in (read_jsonl(path) if path.exists() else [])
            if row["vog"]["graph_id"] == vog["graph_id"]
            and row["vog"]["graph_hash"] == vog["graph_hash"]
        ),
        key=lambda row: row["id"],
    )


@authority_reader("video_research_gap_snapshot")
def discover_video_research_gaps(
    vog: dict[str, Any],
    *,
    query: str | None = None,
    domain: str | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    validate_video_observation_graph(vog, root)
    frame = _frame(vog, domain)
    query_text = _query(vog, query)
    reasoning = reason(
        default_request(
            query_text,
            domain=domain,
            minimum_status="partial",
            maximum_depth=frame["hop_budget"],
            retrieval_frame=frame,
        ),
        root,
    )
    bridges = _bridges_for_vog(vog, root)
    bridged = {row["observation_id"] for row in bridges}
    observations = _observations(vog)
    value = {
        "schema": "cpcs.video_research_gap_report/1.0",
        "policy_version": GAP_POLICY,
        "vog": _vog_identity(vog),
        "query": query_text,
        "retrieval_frame": frame,
        "selected_concepts": copy.deepcopy(reasoning["selected_concepts"]),
        "reviewed_bridges": bridges,
        "unbridged_observations": [
            {
                "observation_id": row["observation_id"],
                "layer": row["layer"],
                "evidence_class": row["evidence_class"],
                "claim_hash": sha256_value(row["claim"]),
                "source_ref": f"{vog['graph_id']}#{row['observation_id']}",
                "disposition": "review_or_research_required",
            }
            for row in observations
            if row["observation_id"] not in bridged
        ],
        "contradictions": copy.deepcopy(vog["contradictions"]),
        "knowledge_gap": copy.deepcopy(reasoning["knowledge_gap"]),
    }
    value["report_hash"] = sha256_value(value)
    validate_instance("video_research_gap_report", value, root)
    return value


@authority_writer("reviewed_video_bridge")
def promote_reviewed_video_bridge(
    vog: dict[str, Any],
    *,
    observation_id: str,
    concept_id: str,
    relation: str,
    review: dict[str, Any],
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    validate_video_observation_graph(vog, root)
    observations = {row["observation_id"]: row for row in _observations(vog)}
    if observation_id not in observations:
        raise ValidationFailure("reviewed bridge observation is absent from the VOG")
    concepts = {row["id"] for row in read_jsonl(root / "lab" / "concepts.jsonl")}
    if concept_id not in concepts:
        raise ValidationFailure("reviewed bridge concept is not curated")
    identity = {
        "vog": _vog_identity(vog),
        "observation_id": observation_id,
        "concept_id": concept_id,
        "relation": relation,
    }
    bridge_id = "vog_bridge_" + sha256_value(identity).removeprefix("sha256:")[:24]
    value = {
        "schema": "cpcs.video_concept_bridge/1.0",
        "id": bridge_id,
        **identity,
        "evidence_class": observations[observation_id]["evidence_class"],
        "source_refs": [f"{vog['graph_id']}#{observation_id}"],
        "review": copy.deepcopy(review),
    }
    value["bridge_hash"] = content_hash(value, ("bridge_hash",))
    validate_instance("video_concept_bridge", value, root)
    path = root / "lab" / "second_brain" / "curated" / "video_concept_bridges.jsonl"
    assert_write_target("video_bridge", path, root)
    existing = read_jsonl(path)
    by_id = {row["id"]: row for row in existing}
    if bridge_id in by_id:
        if by_id[bridge_id] != value:
            raise ValidationFailure("reviewed bridge replay differs from curated authority")
        return by_id[bridge_id]
    write_jsonl(path, sorted([*existing, value], key=lambda row: row["id"]))
    return value


def _side_summary(vog: dict[str, Any], concepts: list[dict[str, Any]], root: Path) -> dict[str, Any]:
    bridges = _bridges_for_vog(vog, root)
    observations = _observations(vog)
    bridge_concepts = {row["concept_id"] for row in bridges}
    selected_ids = {row["id"] for row in concepts}
    return {
        "vog": _vog_identity(vog),
        "observation_count": len(observations),
        "contradiction_count": len(vog["contradictions"]),
        "reviewed_bridge_ids": [row["id"] for row in bridges],
        "covered_concept_ids": sorted(bridge_concepts & selected_ids),
        "unreviewed_observation_ids": sorted(
            {row["observation_id"] for row in observations}
            - {row["observation_id"] for row in bridges}
        ),
    }


@authority_reader("knowledge_comparison_lens_snapshot")
def build_knowledge_comparison_lens(
    reference_vog: dict[str, Any],
    candidate_vog: dict[str, Any],
    *,
    query: str,
    domain: str | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    validate_video_observation_graph(reference_vog, root)
    validate_video_observation_graph(candidate_vog, root)
    combined = copy.deepcopy(reference_vog)
    combined["nodes"] = [*reference_vog["nodes"], *candidate_vog["nodes"]]
    frame = _frame(combined, domain)
    reasoning = reason(
        default_request(
            query,
            domain=domain,
            minimum_status="partial",
            maximum_depth=frame["hop_budget"],
            retrieval_frame=frame,
        ),
        root,
    )
    concepts = copy.deepcopy(reasoning["selected_concepts"])
    dimensions = sorted(
        set(frame["required_coverage_slots"])
        | {row["layer"] for row in concepts}
    )
    value = {
        "schema": "cpcs.knowledge_comparison_lens/1.0",
        "policy_version": LENS_POLICY,
        "query": query,
        "retrieval_frame": frame,
        "concepts": concepts,
        "comparison_dimensions": dimensions,
        "reference": _side_summary(reference_vog, concepts, root),
        "candidate": _side_summary(candidate_vog, concepts, root),
    }
    value["lens_hash"] = sha256_value(value)
    validate_instance("knowledge_comparison_lens", value, root)
    return value
