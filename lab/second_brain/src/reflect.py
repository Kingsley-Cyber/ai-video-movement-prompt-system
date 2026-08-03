"""Deterministically rebuild learned weights, insights, coverage, and indexes."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .validate import (
    REPO_ROOT,
    assert_write_target,
    read_jsonl,
    sha256_value,
    validate_instance,
    write_json,
    write_jsonl,
)

ALGORITHM_VERSION = "reflection-v1.1"
DERIVATION_POLICY = "immutable-evidence-and-isolated-delta-v2"


def _outcome(run: dict[str, Any]) -> str:
    verdict = run.get("verdict", "").lower()
    if verdict in {"keep", "accept", "pass", "success"}:
        return "success"
    if verdict in {"reject", "fail", "failure"}:
        return "failure"
    numeric = [float(value) for value in run.get("metrics", {}).values() if isinstance(value, (int, float))]
    if numeric and sum(numeric) / len(numeric) >= 4:
        return "success"
    if numeric and sum(numeric) / len(numeric) < 3:
        return "failure"
    return "confounded"


def _edge_id(parts: tuple[str, ...]) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:20]
    return f"learned_{digest}"


def _association_edges(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str, str], set[str]] = defaultdict(set)
    for run in runs:
        concepts = sorted(set(run.get("concept_ids", [])))
        outcome = _outcome(run)
        edge_type = {
            "success": "associated_with_success",
            "failure": "associated_with_failure",
            "confounded": "confounded_with",
        }[outcome]
        for u, v in itertools.combinations(concepts, 2):
            key = (u, v, edge_type, run["model_version"], run["intent_class"])
            groups[key].add(run["id"])
    edges = []
    for (u, v, edge_type, model_version, context), evidence in sorted(groups.items()):
        weight = {
            "associated_with_success": 1.0,
            "associated_with_failure": -1.0,
            "confounded_with": 0.0,
        }[edge_type]
        edge = {
            "id": _edge_id((u, v, edge_type, model_version, context)),
            "u": u,
            "v": v,
            "type": edge_type,
            "weight": weight,
            "evidence": sorted(evidence),
            "model_version": model_version,
            "context": context,
            "n_obs": len(evidence),
            "derivation_policy": DERIVATION_POLICY,
        }
        edges.append(edge)
    return edges


def _controls_without_delta(run: dict[str, Any]) -> dict[str, Any] | None:
    controls = run.get("controls")
    delta = run.get("tested_delta")
    if not isinstance(controls, dict) or not isinstance(delta, dict):
        return None
    control_id = delta.get("control_id")
    if (
        not isinstance(control_id, str)
        or "value" not in delta
        or control_id not in controls
        or controls[control_id] != delta["value"]
    ):
        return None
    return {key: value for key, value in controls.items() if key != delta["control_id"]}


def _promotion_edges(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        base = _controls_without_delta(run)
        if base is None or run.get("seed") is None:
            continue
        key = (
            run["flight_id"],
            run["intent_id"],
            run["provider"],
            run["model_version"],
            run["seed"],
            run["compiler_version"],
            run["paradigm"],
            json.dumps(base, sort_keys=True, separators=(",", ":")),
        )
        groups[key].append(run)
    edges = []
    for key, group in sorted(groups.items(), key=lambda item: repr(item[0])):
        for left, right in itertools.combinations(sorted(group, key=lambda item: item["id"]), 2):
            if {_outcome(left), _outcome(right)} != {"success", "failure"}:
                continue
            if left["tested_delta"]["control_id"] != right["tested_delta"]["control_id"]:
                continue
            if left["tested_delta"]["concept_id"] != right["tested_delta"]["concept_id"]:
                continue
            winner = left if _outcome(left) == "success" else right
            loser = right if winner is left else left
            if winner["tested_delta"].get("value") == loser["tested_delta"].get("value"):
                continue
            delta_concept = winner["tested_delta"]["concept_id"]
            shared = sorted((set(winner.get("concept_ids", [])) & set(loser.get("concept_ids", []))) - {delta_concept})
            for target in shared:
                evidence = sorted([winner["id"], loser["id"]])
                context = winner["intent_class"]
                edge = {
                    "id": _edge_id((delta_concept, target, "promotes", winner["model_version"], context)),
                    "u": delta_concept,
                    "v": target,
                    "type": "promotes",
                    "weight": 1.0,
                    "evidence": evidence,
                    "model_version": winner["model_version"],
                    "context": context,
                    "n_obs": 2,
                    "derivation_policy": DERIVATION_POLICY,
                    "isolated_comparison": {
                        "winner": winner["id"],
                        "loser": loser["id"],
                        "control_id": winner["tested_delta"]["control_id"],
                        "same_seed": True,
                        "same_compiler_version": True,
                        "same_controls_except_delta": True,
                    },
                }
                edges.append(edge)
    return edges


def _observation_edges(
    observations: list[dict[str, Any]],
    *,
    context: str,
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for observation in observations:
        concepts = sorted(
            set(observation.get("concept_ids", []))
            | set(observation.get("candidate_concepts", []))
        )
        model = (
            observation["extractor"]["model_version"]
            if "extractor" in observation
            else observation["model_version"]
        )
        for u, v in itertools.combinations(concepts, 2):
            groups[(u, v, model)].add(observation["id"])
    return [
        {
            "id": _edge_id((u, v, "confounded_with", model, context)),
            "u": u,
            "v": v,
            "type": "confounded_with",
            "weight": 0.0,
            "evidence": sorted(evidence),
            "model_version": model,
            "context": context,
            "n_obs": len(evidence),
            "derivation_policy": DERIVATION_POLICY,
        }
        for (u, v, model), evidence in sorted(groups.items())
    ]


def materialize(root: Path = REPO_ROOT) -> dict[str, Any]:
    sb = root / "lab" / "second_brain"
    runs = read_jsonl(sb / "immutable" / "runs.jsonl")
    observations = read_jsonl(sb / "immutable" / "pegasus_observations.jsonl")
    measurements = read_jsonl(
        sb / "immutable" / "measurement_observations.jsonl"
    )
    edges = (
        _association_edges(runs)
        + _promotion_edges(runs)
        + _observation_edges(observations, context="pegasus_observation")
        + _observation_edges(
            measurements,
            context="measurement_observation",
        )
    )
    deduped = {edge["id"]: edge for edge in edges}
    learned = sorted(deduped.values(), key=lambda item: item["id"])
    for edge in learned:
        validate_instance("learned_weight", edge, root)
    concepts = read_jsonl(root / "lab" / "concepts.jsonl")
    intents = read_jsonl(sb / "curated" / "intents.jsonl")
    mappings = read_jsonl(sb / "curated" / "mappings.jsonl")
    rules = read_jsonl(sb / "curated" / "rules.jsonl")
    authored_edges = read_jsonl(sb / "curated" / "edges.jsonl")
    concept_to_evidence: dict[str, set[str]] = defaultdict(set)
    for run in runs:
        for concept_id in run.get("concept_ids", []):
            concept_to_evidence[concept_id].add(run["id"])
    for observation in observations + measurements:
        for concept_id in (
            set(observation.get("concept_ids", []))
            | set(observation.get("candidate_concepts", []))
        ):
            concept_to_evidence[concept_id].add(observation["id"])
    for edge in learned:
        concept_to_evidence[edge["u"]].update(edge["evidence"])
        concept_to_evidence[edge["v"]].update(edge["evidence"])
    uncovered = sorted(
        row["id"] for row in concepts if not concept_to_evidence.get(row["id"])
    )
    uncovered_by_layer = Counter(
        row["layer"] for row in concepts if row["id"] in set(uncovered)
    )
    coverage = {
        "algorithm_version": ALGORITHM_VERSION,
        "concepts_total": len(concepts),
        "concepts_by_layer": dict(sorted(Counter(row["layer"] for row in concepts).items())),
        "concepts_by_status": dict(sorted(Counter(row["status"] for row in concepts).items())),
        "authored_edges": len(authored_edges),
        "curated_intents": len(intents),
        "curated_mappings": len(mappings),
        "curated_rules": len(rules),
        "immutable_runs": len(runs),
        "pegasus_observations": len(observations),
        "measurement_observations": len(measurements),
        "concepts_with_immutable_evidence": len(concept_to_evidence),
        "concepts_without_immutable_evidence": uncovered,
        "likely_gaps_by_layer": dict(sorted(uncovered_by_layer.items())),
        "learned_edges": len(learned),
    }
    indexes = {
        "algorithm_version": ALGORITHM_VERSION,
        "concept_to_evidence": {
            key: sorted(value) for key, value in sorted(concept_to_evidence.items())
        },
    }
    insights = [
        {
            "id": f"insight_{edge['id'][8:]}",
            "edge_id": edge["id"],
            "statement": f"{edge['u']} {edge['type']} {edge['v']}",
            "evidence": edge["evidence"],
            "model_version": edge["model_version"],
            "context": edge["context"],
        }
        for edge in learned
    ]
    weights = {
        "algorithm_version": ALGORITHM_VERSION,
        "derivation_policy": DERIVATION_POLICY,
        "policy_hash": sha256_value(
            {"algorithm_version": ALGORITHM_VERSION, "derivation_policy": DERIVATION_POLICY}
        ),
        "edges": learned,
    }
    return {"weights": weights, "insights": insights, "coverage": coverage, "indexes": indexes}


def rebuild(root: Path = REPO_ROOT) -> dict[str, str]:
    sb = root / "lab" / "second_brain"
    derived = sb / "derived"
    values = materialize(root)
    assert_write_target("reflect", derived, root)
    if derived.exists():
        shutil.rmtree(derived)
    derived.mkdir(parents=True)
    outputs = {
        derived / "weights.json": ("json", values["weights"]),
        derived / "insights.jsonl": ("jsonl", values["insights"]),
        derived / "coverage.json": ("json", values["coverage"]),
        derived / "indexes" / "concept_to_evidence.json": ("json", values["indexes"]),
    }
    for path, (kind, value) in outputs.items():
        assert_write_target("reflect", path, root)
        (write_jsonl if kind == "jsonl" else write_json)(path, value)
    return {
        str(path.relative_to(derived)): "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(derived.rglob("*"))
        if path.is_file()
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("rebuild",))
    args = parser.parse_args(argv)
    if args.command == "rebuild":
        print(json.dumps(rebuild(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
