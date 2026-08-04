"""Build deterministic, inspectable retrieval and lineage indexes from governed stores."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .authority import authority_reader
from .graph import AUTHORED_EDGE_POLICY, validate_edge_distribution
from .temporal import TEMPORAL_POLICY, is_visible, validate_temporal_request, validity_of
from .validate import REPO_ROOT, read_jsonl, sha256_value


INDEX_POLICY = {
    "version": "cpcs-derived-indexes/1.1",
    "dense_algorithm": "signed-hashed-tfidf/1.0",
    "dense_dimensions": 96,
    "maximum_diagnostic_candidates": 12,
}
STOP = {
    "a", "an", "and", "for", "in", "is", "it", "of", "on", "or", "the", "to", "with",
}


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 1 and token not in STOP
    }


def _concept_text(record: dict[str, Any]) -> str:
    return " ".join(
        [
            str(record.get("name", "")),
            str(record.get("what", "")),
            str(record.get("use_when", "")),
            str(record.get("layer", "")),
            *[str(value) for value in record.get("nl_triggers", [])],
        ]
    )


def _feature(token: str, dimensions: int) -> tuple[int, float]:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % dimensions, 1.0 if digest[4] & 1 else -1.0


def _dense_vector(
    tokens: Iterable[str],
    idf: dict[str, float],
    dimensions: int,
) -> list[float]:
    vector = [0.0] * dimensions
    for token in sorted(set(tokens)):
        index, sign = _feature(token, dimensions)
        vector[index] += sign * idf.get(token, 1.0)
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return [round(value, 8) for value in vector]


def _dense_index(concepts: list[dict[str, Any]]) -> dict[str, Any]:
    token_sets = {record["id"]: _tokens(_concept_text(record)) for record in concepts}
    document_frequency = Counter(
        token for tokens in token_sets.values() for token in tokens
    )
    count = len(concepts)
    idf = {
        token: round(1.0 + math.log((1 + count) / (1 + frequency)), 8)
        for token, frequency in sorted(document_frequency.items())
    }
    dimensions = INDEX_POLICY["dense_dimensions"]
    return {
        "algorithm": INDEX_POLICY["dense_algorithm"],
        "dimensions": dimensions,
        "corpus_size": count,
        "token_idf": idf,
        "vectors": {
            concept_id: _dense_vector(tokens, idf, dimensions)
            for concept_id, tokens in sorted(token_sets.items())
        },
    }


def _prerequisite_closure(
    concept_ids: set[str],
    edges: list[dict[str, Any]],
) -> tuple[dict[str, list[str]], list[list[str]]]:
    direct: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if edge["type"] == "requires":
            direct[edge["u"]].add(edge["v"])
    closures: dict[str, list[str]] = {}
    cycles: set[tuple[str, ...]] = set()
    for start in sorted(concept_ids):
        found: set[str] = set()
        stack: list[tuple[str, tuple[str, ...]]] = [(start, (start,))]
        while stack:
            current, path = stack.pop()
            for required in sorted(direct.get(current, set()), reverse=True):
                if required in path:
                    cycle = path[path.index(required) :] + (required,)
                    body = cycle[:-1]
                    pivot = min(range(len(body)), key=lambda index: body[index])
                    ordered = body[pivot:] + body[:pivot]
                    cycles.add(ordered + (ordered[0],))
                    continue
                found.add(required)
                stack.append((required, path + (required,)))
        closures[start] = sorted(found)
    return closures, [list(cycle) for cycle in sorted(cycles)]


def _concept_to_evidence(
    runs: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    measurements: list[dict[str, Any]],
    learned_edges: list[dict[str, Any]],
) -> dict[str, list[str]]:
    values: dict[str, set[str]] = defaultdict(set)
    for record in runs + observations + measurements:
        for concept_id in set(record.get("concept_ids", [])) | set(
            record.get("candidate_concepts", [])
        ):
            values[concept_id].add(record["id"])
    for edge in learned_edges:
        values[edge["u"]].update(edge["evidence"])
        values[edge["v"]].update(edge["evidence"])
    return {key: sorted(value) for key, value in sorted(values.items())}


@authority_reader("index_snapshot")
def build_index_catalog(
    root: Path = REPO_ROOT,
    *,
    learned_edges: list[dict[str, Any]] | None = None,
    validity_mode: str = "current",
    as_of: str | None = None,
) -> dict[str, Any]:
    validate_temporal_request(validity_mode, as_of)
    sb = root / "lab" / "second_brain"
    concepts = sorted(read_jsonl(root / "lab" / "concepts.jsonl"), key=lambda row: row["id"])
    edges = sorted(read_jsonl(sb / "curated" / "edges.jsonl"), key=lambda row: row["id"])
    mappings = sorted(read_jsonl(sb / "curated" / "mappings.jsonl"), key=lambda row: row["id"])
    intents = sorted(read_jsonl(sb / "curated" / "intents.jsonl"), key=lambda row: row["id"])
    rules = sorted(read_jsonl(sb / "curated" / "rules.jsonl"), key=lambda row: row["id"])
    flights = sorted(read_jsonl(sb / "immutable" / "flights.jsonl"), key=lambda row: row["id"])
    runs = sorted(read_jsonl(sb / "immutable" / "runs.jsonl"), key=lambda row: row["id"])
    observations = sorted(
        read_jsonl(sb / "immutable" / "pegasus_observations.jsonl"),
        key=lambda row: row["id"],
    )
    measurements = sorted(
        read_jsonl(sb / "immutable" / "measurement_observations.jsonl"),
        key=lambda row: row["id"],
    )
    learned = sorted(learned_edges or [], key=lambda row: row["id"])
    view_concepts = [record for record in concepts if is_visible(record, validity_mode, as_of)]
    view_concept_ids = {row["id"] for row in view_concepts}
    current_concept_ids = {
        record["id"] for record in concepts if is_visible(record, "current", None)
    }
    current_edges = [
        record
        for record in edges
        if is_visible(record, "current", None)
        and record["u"] in current_concept_ids
        and record["v"] in current_concept_ids
    ]
    view_edges = [
        record
        for record in edges
        if is_visible(record, validity_mode, as_of)
        and record["u"] in view_concept_ids
        and record["v"] in view_concept_ids
    ]
    view_mappings = [
        record
        for record in mappings
        if is_visible(record, validity_mode, as_of)
        and record["concept_id"] in view_concept_ids
    ]
    view_intents = [
        record for record in intents if is_visible(record, validity_mode, as_of)
    ]

    lexical: dict[str, set[str]] = defaultdict(set)
    aliases: dict[str, set[str]] = defaultdict(set)
    concept_tokens: dict[str, set[str]] = {}
    for concept in view_concepts:
        tokens = _tokens(_concept_text(concept))
        concept_tokens[concept["id"]] = tokens
        for token in tokens:
            lexical[token].add(concept["id"])
        for phrase in [concept["name"], *concept.get("nl_triggers", [])]:
            aliases[phrase.strip().lower()].add(concept["id"])

    adjacency: dict[str, list[dict[str, Any]]] = defaultdict(list)
    conflicts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in view_edges:
        policy = AUTHORED_EDGE_POLICY["types"][edge["type"]]
        for node_id, neighbor, direction in (
            (edge["u"], edge["v"], "forward"),
            (edge["v"], edge["u"], "reverse"),
        ):
            item = {
                "edge_id": edge["id"],
                "neighbor": neighbor,
                "type": edge["type"],
                "family": policy["family"],
                "direction": direction,
                "context": edge["context"],
            }
            adjacency[node_id].append(item)
            if edge["type"] in {"conflicts_with", "invalid_for"}:
                conflicts[node_id].append(item)
    adjacency_value = {
        key: sorted(value, key=lambda row: (row["type"], row["neighbor"], row["edge_id"]))
        for key, value in sorted(adjacency.items())
    }
    conflict_value = {
        key: sorted(value, key=lambda row: (row["type"], row["neighbor"], row["edge_id"]))
        for key, value in sorted(conflicts.items())
    }
    closures, dependency_cycles = _prerequisite_closure(view_concept_ids, view_edges)

    all_curated = {
        "concept": concepts,
        "edge": edges,
        "mapping": mappings,
        "intent": intents,
        "rule": rules,
    }
    temporal_records = {
        record["id"]: {"store": store, **validity_of(record)}
        for store, records in all_curated.items()
        for record in records
    }
    supersession = {
        record_id: {
            "supersedes": value["supersedes"],
            "superseded_by": value["superseded_by"],
        }
        for record_id, value in sorted(temporal_records.items())
        if value["supersedes"] or value["superseded_by"]
    }

    intent_to_concept: dict[str, list[dict[str, Any]]] = {}
    for intent in view_intents:
        terms = _tokens(intent["canonical"] + " " + " ".join(intent["requirements"]))
        matches = [
            {
                "concept_id": concept_id,
                "matched_terms": sorted(terms & tokens),
            }
            for concept_id, tokens in sorted(concept_tokens.items())
            if terms & tokens
        ]
        intent_to_concept[intent["id"]] = matches

    control_to_provider: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for mapping in view_mappings:
        control_to_provider[mapping["target_id"]].append(
            {
                "mapping_id": mapping["id"],
                "concept_id": mapping["concept_id"],
                "provider": mapping.get("provider") or "all",
                "model_version": mapping.get("model_version") or "all",
                "encoding": mapping["encoding"],
                "loss": mapping["loss"],
            }
        )

    provider_performance: dict[str, dict[str, Any]] = {}
    provider_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        provider_groups[f"{run['provider']}::{run['model_version']}"].append(run)
    for key, records in sorted(provider_groups.items()):
        run_ids = {record["id"] for record in records}
        causal_edges = [
            edge
            for edge in learned
            if edge.get("evidence_scope") == "causal_isolated_comparison"
            and set(edge["evidence"]) <= run_ids
        ]
        causal_run_ids = sorted(
            {run_id for edge in causal_edges for run_id in edge["evidence"]}
        )
        controlled = [record for record in records if record.get("legacy") is None]
        bundled = [
            record
            for record in controlled
            if record.get("evidence_design", {}).get("classification")
            == "bundled_observation"
        ]
        provider_performance[key] = {
            "policy_version": "cpcs-provider-calibration/1.0",
            "run_ids": sorted(run_ids),
            "verdict_counts": dict(sorted(Counter(record.get("verdict", "") for record in records).items())),
            "compliance_status_counts": dict(
                sorted(
                    Counter(
                        record.get("evidence_lineage", {}).get(
                            "compliance_status", "legacy_unrecorded"
                        )
                        for record in records
                    ).items()
                )
            ),
            "design_counts": dict(
                sorted(
                    Counter(
                        record.get("evidence_design", {}).get(
                            "classification", "legacy_unrecorded"
                        )
                        for record in records
                    ).items()
                )
            ),
            "controlled_run_ids": sorted(record["id"] for record in controlled),
            "bundled_run_ids": sorted(record["id"] for record in bundled),
            "causal_run_ids": causal_run_ids,
            "causal_edge_ids": sorted(edge["id"] for edge in causal_edges),
            "artifact_hashes": sorted(
                {
                    record["output_artifact_hash"]
                    for record in controlled
                    if record.get("output_artifact_hash")
                }
            ),
            "causal_effects": [
                edge["isolated_comparison"]
                for edge in sorted(causal_edges, key=lambda item: item["id"])
            ],
            "calibration_status": (
                "causal_signal_available"
                if causal_edges
                else "noncausal_only"
                if controlled
                else "legacy_only"
            ),
            "evidence_class": (
                "controlled_render_evidence"
                if controlled
                else "immutable_run_history"
            ),
        }

    experiments = {
        flight["id"]: {
            "flight_hash": flight["flight_hash"],
            "design_classification": flight.get("design", {}).get(
                "classification", "legacy_unrecorded"
            ),
            "concept_ids": sorted(flight.get("concept_ids", [])),
            "arms": sorted(arm["id"] for arm in flight.get("arms", [])),
            "run_ids": sorted(run["id"] for run in runs if run["flight_id"] == flight["id"]),
            "compliance_report_ids": sorted(
                {
                    run.get("evidence_lineage", {}).get("compliance_report_id")
                    for run in runs
                    if run["flight_id"] == flight["id"]
                    and run.get("evidence_lineage", {}).get("compliance_report_id")
                }
            ),
            "causal_edge_ids": sorted(
                edge["id"]
                for edge in learned
                if edge.get("isolated_comparison", {}).get("flight_id")
                == flight["id"]
            ),
        }
        for flight in flights
    }
    video_observations: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {"pegasus": [], "measurement": []}
    )
    for record in observations:
        source = str(record.get("source_asset_ref") or record.get("source_item_id") or record.get("source_sha256"))
        video_observations[source]["pegasus"].append(record["id"])
    for record in measurements:
        source = str(record.get("source_asset_ref") or record.get("source_sha256"))
        video_observations[source]["measurement"].append(record["id"])
    video_observation_value = {
        key: {kind: sorted(ids) for kind, ids in sorted(value.items())}
        for key, value in sorted(video_observations.items())
    }

    input_payload = {
        "concepts": concepts,
        "edges": edges,
        "mappings": mappings,
        "intents": intents,
        "rules": rules,
        "flights": flights,
        "runs": runs,
        "observations": observations,
        "measurements": measurements,
        "learned": learned,
        "policy": INDEX_POLICY,
        "validity_mode": validity_mode,
        "as_of": as_of,
    }
    return {
        "schema": "cpcs.derived_indexes/1.0",
        "algorithm_version": INDEX_POLICY["version"],
        "input_hash": sha256_value(input_payload),
        "lexical_concepts": {
            key: sorted(value) for key, value in sorted(lexical.items())
        },
        "aliases": {key: sorted(value) for key, value in sorted(aliases.items())},
        "dense_semantic_concepts": _dense_index(view_concepts),
        "typed_adjacency": adjacency_value,
        "prerequisite_closure": closures,
        "dependency_cycles": dependency_cycles,
        "conflicts": conflict_value,
        "temporal_validity": {
            "policy_version": TEMPORAL_POLICY["version"],
            "view_mode": validity_mode,
            "as_of": as_of,
            "visible_records": sorted(
                record["id"]
                for records in all_curated.values()
                for record in records
                if is_visible(record, validity_mode, as_of)
            ),
            "records": dict(sorted(temporal_records.items())),
            "current_heads": sorted(
                record_id
                for record_id, (_, record) in {
                    item["id"]: (store, item)
                    for store, records in all_curated.items()
                    for item in records
                }.items()
                if is_visible(record, "current", None)
            ),
        },
        "supersession": supersession,
        "concept_to_source": {
            record["id"]: sorted(record.get("source", []))
            for record in view_concepts
        },
        "concept_to_evidence": {
            concept_id: evidence_ids
            for concept_id, evidence_ids in _concept_to_evidence(
                runs, observations, measurements, learned
            ).items()
            if concept_id in view_concept_ids
        },
        "intent_to_concept": intent_to_concept,
        "control_to_provider": {
            key: sorted(value, key=lambda row: (row["provider"], row["model_version"], row["mapping_id"]))
            for key, value in sorted(control_to_provider.items())
        },
        "provider_performance": provider_performance,
        "experiments": experiments,
        "video_observations": video_observation_value,
        "edge_distribution": validate_edge_distribution(current_edges),
    }


def retrieval_diagnostics(goal: str, catalog: dict[str, Any]) -> dict[str, Any]:
    query_tokens = _tokens(goal)
    lexical_scores: dict[str, set[str]] = defaultdict(set)
    for token in query_tokens:
        for concept_id in catalog["lexical_concepts"].get(token, []):
            lexical_scores[concept_id].add(token)
    lexical = [
        {
            "concept_id": concept_id,
            "score": round(len(matched) / max(1, len(query_tokens)), 8),
            "matched_terms": sorted(matched),
        }
        for concept_id, matched in lexical_scores.items()
    ]
    lexical.sort(key=lambda row: (-row["score"], row["concept_id"]))

    alias = []
    normalized_goal = " ".join(sorted(query_tokens))
    for phrase, concept_ids in catalog["aliases"].items():
        phrase_tokens = _tokens(phrase)
        overlap = phrase_tokens & query_tokens
        if not overlap:
            continue
        exact = phrase.strip() == goal.strip().lower() or " ".join(sorted(phrase_tokens)) == normalized_goal
        score = 1.0 if exact else len(overlap) / max(1, len(phrase_tokens | query_tokens))
        for concept_id in concept_ids:
            alias.append(
                {
                    "concept_id": concept_id,
                    "alias": phrase,
                    "score": round(score, 8),
                    "exact": exact,
                }
            )
    alias.sort(key=lambda row: (-row["score"], row["concept_id"], row["alias"]))

    dense = catalog["dense_semantic_concepts"]
    query_vector = _dense_vector(query_tokens, dense["token_idf"], dense["dimensions"])
    vector = []
    for concept_id, concept_vector in dense["vectors"].items():
        score = sum(left * right for left, right in zip(query_vector, concept_vector))
        if score > 0:
            vector.append({"concept_id": concept_id, "score": round(score, 8)})
    vector.sort(key=lambda row: (-row["score"], row["concept_id"]))
    lexical_by_id = {row["concept_id"]: row["score"] for row in lexical}
    alias_by_id: dict[str, float] = {}
    for row in alias:
        alias_by_id[row["concept_id"]] = max(
            alias_by_id.get(row["concept_id"], 0.0), row["score"]
        )
    vector_by_id = {row["concept_id"]: row["score"] for row in vector}
    fused = [
        {
            "concept_id": concept_id,
            "score": round(
                0.5 * lexical_by_id.get(concept_id, 0.0)
                + 0.3 * alias_by_id.get(concept_id, 0.0)
                + 0.2 * max(0.0, vector_by_id.get(concept_id, 0.0)),
                8,
            ),
            "components": {
                "lexical": lexical_by_id.get(concept_id, 0.0),
                "alias": alias_by_id.get(concept_id, 0.0),
                "vector": vector_by_id.get(concept_id, 0.0),
            },
        }
        for concept_id in sorted(set(lexical_by_id) | set(alias_by_id) | set(vector_by_id))
    ]
    fused.sort(key=lambda row: (-row["score"], row["concept_id"]))
    maximum = INDEX_POLICY["maximum_diagnostic_candidates"]
    return {
        "policy_version": INDEX_POLICY["version"],
        "lexical": lexical[:maximum],
        "aliases": alias[:maximum],
        "vector": vector[:maximum],
        "fused": fused[:maximum],
        "fusion_weights": {"lexical": 0.5, "alias": 0.3, "vector": 0.2},
        "hard_constraints_override_ranking": True,
    }
