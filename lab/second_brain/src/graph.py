"""Assemble the live NetworkX MultiDiGraph without persisting the overlay."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import networkx as nx

from .authority import authority_reader
from .temporal import TEMPORAL_POLICY, is_visible, validate_temporal_request
from .validate import REPO_ROOT, read_jsonl


AUTHORED_EDGE_POLICY = {
    "version": "cpcs-edge-policy/1.0",
    "types": {
        "is_a": {
            "family": "structural",
            "forward": "generalizes_to",
            "reverse": "specializes_to",
            "rank": 10,
        },
        "part_of": {
            "family": "structural",
            "forward": "part_to_whole",
            "reverse": "whole_to_part",
            "rank": 12,
        },
        "refines": {
            "family": "structural",
            "forward": "generalizes_to",
            "reverse": "specializes_to",
            "rank": 10,
        },
        "requires": {
            "family": "dependency",
            "forward": "requires",
            "reverse": "required_by",
            "rank": 25,
        },
        "applies_to": {
            "family": "operational",
            "forward": "applies_to",
            "reverse": "has_applicable_concept",
            "rank": 20,
        },
        "produces": {
            "family": "operational",
            "forward": "produces",
            "reverse": "produced_by",
            "rank": 22,
        },
        "alternative_to": {
            "family": "contextual",
            "forward": "alternative_to",
            "reverse": "alternative_to",
            "rank": 50,
        },
        "pairs_with": {
            "family": "legacy_association",
            "forward": "pairs_with",
            "reverse": "pairs_with",
            "rank": 80,
            "maximum_per_path": 1,
        },
        "conflicts_with": {
            "family": "constraint",
            "traversable": False,
        },
        "valid_for": {
            "family": "constraint",
            "traversable": False,
        },
        "invalid_for": {
            "family": "constraint",
            "traversable": False,
        },
    },
}
STRUCTURAL_EDGE_TYPES = frozenset(
    edge_type
    for edge_type, policy in AUTHORED_EDGE_POLICY["types"].items()
    if policy["family"] == "structural"
)
OPERATIONAL_EDGE_TYPES = frozenset(
    edge_type
    for edge_type, policy in AUTHORED_EDGE_POLICY["types"].items()
    if policy["family"] in {"operational", "dependency"}
)
EDGE_DISTRIBUTION_POLICY = {
    "version": "cpcs-typed-edge-distribution/1.1",
    "maximum_pairs_with": 154,
    "maximum_pairs_with_ratio": 0.79,
    "ratio_minimum_edges": 195,
}


def validate_edge_distribution(
    edges: list[dict[str, Any]],
    *,
    allow_recoverable_legacy_reciprocals: bool = False,
) -> dict[str, Any]:
    policy_edges = list(edges)
    reciprocal: dict[tuple[str, str, str], list[str]] = {}
    edge_by_id = {edge["id"]: edge for edge in edges}
    for edge in edges:
        if edge["type"] != "pairs_with":
            continue
        u, v = sorted((edge["u"], edge["v"]))
        reciprocal.setdefault((u, v, edge["context"]), []).append(edge["id"])
    duplicates = {
        "::".join(key): sorted(edge_ids)
        for key, edge_ids in sorted(reciprocal.items())
        if len(edge_ids) > 1
    }
    if duplicates and allow_recoverable_legacy_reciprocals:
        retained_ids: set[str] = set()
        duplicate_ids = {edge_id for edge_ids in duplicates.values() for edge_id in edge_ids}
        for edge_ids in duplicates.values():
            rows = [edge_by_id[edge_id] for edge_id in edge_ids]
            directions = {(row["u"], row["v"]) for row in rows}
            if (
                len(rows) != 2
                or len(directions) != 2
                or any(
                    row.get("authored_by") != "legacy_migration"
                    or row.get("context") != "all"
                    for row in rows
                )
            ):
                raise ValueError(
                    "recoverable reciprocal allowance accepts only exact inverse "
                    "legacy_migration pairs"
                )
            retained_ids.add(min(edge_ids))
        policy_edges = [
            edge
            for edge in edges
            if edge["id"] not in duplicate_ids or edge["id"] in retained_ids
        ]
    elif duplicates:
        raise ValueError(
            "current pairs_with records repeat symmetric relationships: "
            + json.dumps(duplicates, sort_keys=True, separators=(",", ":"))
        )
    counts = Counter(edge["type"] for edge in policy_edges)
    total = len(policy_edges)
    legacy = counts.get("pairs_with", 0)
    ratio = legacy / total if total else 0.0
    if legacy > EDGE_DISTRIBUTION_POLICY["maximum_pairs_with"]:
        raise ValueError(
            f"pairs_with count {legacy} exceeds typed-edge policy maximum "
            f"{EDGE_DISTRIBUTION_POLICY['maximum_pairs_with']}"
        )
    if (
        total >= EDGE_DISTRIBUTION_POLICY["ratio_minimum_edges"]
        and ratio > EDGE_DISTRIBUTION_POLICY["maximum_pairs_with_ratio"]
    ):
        raise ValueError(
            f"pairs_with ratio {ratio:.6f} exceeds typed-edge policy maximum "
            f"{EDGE_DISTRIBUTION_POLICY['maximum_pairs_with_ratio']:.6f}"
        )
    return {
        "policy_version": EDGE_DISTRIBUTION_POLICY["version"],
        "total": total,
        "by_type": dict(sorted(counts.items())),
        "pairs_with": legacy,
        "pairs_with_ratio": round(ratio, 6),
        "reciprocal_pairs_with": len(duplicates),
    }


def traversal_steps(
    graph: nx.MultiDiGraph,
    node_id: str,
) -> list[dict[str, Any]]:
    """Return policy-labelled concept hops from one node."""
    steps: list[dict[str, Any]] = []
    incident = list(graph.out_edges(node_id, keys=True, data=True))
    incident.extend(graph.in_edges(node_id, keys=True, data=True))
    for u, v, key, data in incident:
        neighbor = v if u == node_id else u
        if graph.nodes[neighbor].get("node_type") != "concept":
            continue
        if data.get("tier") == "derived":
            steps.append(
                {
                    "neighbor": neighbor,
                    "edge_id": str(key),
                    "edge_data": data,
                    "edge_type": data.get("edge_type"),
                    "direction": "forward" if u == node_id else "reverse",
                    "transition": "learned_association",
                    "family": "learned",
                    "rank": 90,
                    "maximum_per_path": None,
                }
            )
            continue
        edge_type = data.get("edge_type")
        policy = AUTHORED_EDGE_POLICY["types"].get(edge_type)
        if not policy or policy.get("traversable", True) is False:
            continue
        direction = "forward" if u == node_id else "reverse"
        steps.append(
            {
                "neighbor": neighbor,
                "edge_id": str(key),
                "edge_data": data,
                "edge_type": edge_type,
                "direction": direction,
                "transition": policy[direction],
                "family": policy["family"],
                "rank": policy["rank"],
                "maximum_per_path": policy.get("maximum_per_path"),
            }
        )
    return sorted(
        steps,
        key=lambda item: (
            item["rank"],
            item["edge_type"] or "",
            item["neighbor"],
            item["edge_id"],
        ),
    )


@authority_reader("graph_snapshot")
def build_live_graph(
    root: Path = REPO_ROOT,
    include_derived: bool = True,
    validity_mode: str = "current",
    as_of: str | None = None,
) -> nx.MultiDiGraph:
    validate_temporal_request(validity_mode, as_of)
    graph = nx.MultiDiGraph(
        name="CPCS second-brain live reasoning graph",
        persistence="in_memory_overlay_only",
        validity_mode=validity_mode,
        as_of=as_of,
        temporal_policy=TEMPORAL_POLICY["version"],
    )
    lab = root / "lab"
    sb = lab / "second_brain"
    concepts = read_jsonl(lab / "concepts.jsonl")
    for concept in sorted(concepts, key=lambda item: item["id"]):
        if not is_visible(concept, validity_mode, as_of):
            continue
        graph.add_node(
            concept["id"],
            node_type="concept",
            tier="curated",
            rebuildable=False,
            **{key: value for key, value in concept.items() if key != "id"},
        )
    for edge in sorted(read_jsonl(sb / "curated" / "edges.jsonl"), key=lambda item: item["id"]):
        if not is_visible(edge, validity_mode, as_of) or edge["u"] not in graph:
            continue
        if edge["v"] not in graph and edge["type"] != "requires":
            continue
        graph.add_edge(
            edge["u"],
            edge["v"],
            key=edge["id"],
            edge_id=edge["id"],
            edge_type=edge["type"],
            tier="curated",
            rebuildable=False,
            context=edge["context"],
            sources=edge["sources"],
            validity=edge.get("validity"),
        )
    for flight in read_jsonl(sb / "immutable" / "flights.jsonl"):
        graph.add_node(
            flight["id"],
            node_type="flight",
            tier="immutable",
            append_only=True,
            flight_hash=flight["flight_hash"],
        )
        for concept_id in flight.get("concept_ids", []):
            if concept_id not in graph:
                continue
            key = f"flight:{flight['id']}:{concept_id}"
            graph.add_edge(
                concept_id,
                flight["id"],
                key=key,
                edge_id=key,
                edge_type="sealed_in_flight",
                tier="immutable",
                append_only=True,
            )
    for store_name in ("runs", "pegasus_observations", "measurement_observations"):
        path = sb / "immutable" / f"{store_name}.jsonl"
        for record in read_jsonl(path):
            evidence_id = record["id"]
            graph.add_node(
                evidence_id,
                node_type="evidence",
                evidence_store=store_name,
                tier="immutable",
                append_only=True,
            )
            if store_name == "runs":
                key = f"run_flight:{evidence_id}:{record['flight_id']}"
                graph.add_edge(
                    evidence_id,
                    record["flight_id"],
                    key=key,
                    edge_id=key,
                    edge_type="part_of_flight",
                    tier="immutable",
                    append_only=True,
                )
            concept_ids = list(record.get("concept_ids", [])) + list(record.get("candidate_concepts", []))
            for concept_id in sorted(set(concept_ids)):
                if concept_id in graph:
                    key = f"evidence:{evidence_id}:{concept_id}"
                    graph.add_edge(
                        concept_id,
                        evidence_id,
                        key=key,
                        edge_id=key,
                        edge_type="evidenced_by",
                        tier="immutable",
                        append_only=True,
                    )
    if include_derived:
        weights_path = sb / "derived" / "weights.json"
        if weights_path.exists():
            weights = json.loads(weights_path.read_text())
            for edge in sorted(weights.get("edges", []), key=lambda item: item["id"]):
                if edge["u"] not in graph or edge["v"] not in graph:
                    continue
                graph.add_edge(
                    edge["u"],
                    edge["v"],
                    key=edge["id"],
                    edge_id=edge["id"],
                    edge_type=edge["type"],
                    tier="derived",
                    rebuildable=True,
                    weight=edge["weight"],
                    evidence=edge["evidence"],
                    provider=edge.get("provider", "all"),
                    model_version=edge["model_version"],
                    context=edge["context"],
                    n_obs=edge["n_obs"],
                    derivation_policy=edge["derivation_policy"],
                    evidence_scope=edge.get("evidence_scope"),
                    evidence_trace=edge.get("evidence_trace", []),
                    isolated_comparison=edge.get("isolated_comparison"),
                )
    return graph


def graph_stats(graph: nx.MultiDiGraph) -> dict[str, Any]:
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "nodes_by_tier": dict(sorted(Counter(data.get("tier", "temporary") for _, data in graph.nodes(data=True)).items())),
        "edges_by_tier": dict(
            sorted(Counter(data.get("tier", "temporary") for _, _, data in graph.edges(data=True)).items())
        ),
        "parallel_edge_pairs": sum(
            1
            for u, v in set(graph.edges())
            if graph.number_of_edges(u, v) > 1
        ),
        "graph_type": type(graph).__name__,
        "validity_mode": graph.graph.get("validity_mode"),
        "as_of": graph.graph.get("as_of"),
        "temporal_policy": graph.graph.get("temporal_policy"),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("stats",))
    args = parser.parse_args(argv)
    if args.command == "stats":
        print(json.dumps(graph_stats(build_live_graph()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
