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

from .authority import authority_reader, authority_writer
from .indexes import build_index_catalog
from .validate import (
    REPO_ROOT,
    assert_write_target,
    read_jsonl,
    sha256_value,
    validate_instance,
    write_json,
    write_jsonl,
)

ALGORITHM_VERSION = "reflection-v1.3"
DERIVATION_POLICY = "controlled-render-evidence-v3"


def _outcome(run: dict[str, Any]) -> str:
    lineage = run.get("evidence_lineage")
    if run.get("legacy") is None and isinstance(lineage, dict):
        compliance = lineage.get("compliance_status")
        if compliance == "inconclusive":
            return "confounded"
        if compliance == "fail":
            return "failure"
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


def _run_evidence_trace(run: dict[str, Any]) -> dict[str, Any]:
    lineage = run.get("evidence_lineage") or {}
    review = run.get("human_review") or {}
    return {
        "run_id": run["id"],
        "build_id": lineage.get("build_id"),
        "build_hash": lineage.get("build_hash"),
        "artifact_sha256": lineage.get("artifact_sha256"),
        "compliance_report_id": lineage.get("compliance_report_id"),
        "compliance_report_hash": lineage.get("compliance_report_hash"),
        "compliance_status": lineage.get("compliance_status"),
        "human_review_id": review.get("review_id"),
        "human_review_hash": review.get("review_hash"),
        "human_verdict": review.get("verdict", run.get("verdict")),
    }


def _edge_id(parts: tuple[str, ...]) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:20]
    return f"learned_{digest}"


def _association_edges(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        concepts = sorted(set(run.get("concept_ids", [])))
        outcome = _outcome(run)
        edge_type = {
            "success": "associated_with_success",
            "failure": "associated_with_failure",
            "confounded": "confounded_with",
        }[outcome]
        for u, v in itertools.combinations(concepts, 2):
            key = (
                u,
                v,
                edge_type,
                run["provider"],
                run["model_version"],
                run["intent_class"],
            )
            groups[key].append(run)
    edges = []
    for (u, v, edge_type, provider, model_version, context), records in sorted(groups.items()):
        evidence = sorted({run["id"] for run in records})
        weight = {
            "associated_with_success": 0.25,
            "associated_with_failure": -0.25,
            "confounded_with": 0.0,
        }[edge_type]
        edge = {
            "id": _edge_id((u, v, edge_type, provider, model_version, context)),
            "u": u,
            "v": v,
            "type": edge_type,
            "weight": weight,
            "evidence": sorted(evidence),
            "provider": provider,
            "model_version": model_version,
            "context": context,
            "n_obs": len(evidence),
            "derivation_policy": DERIVATION_POLICY,
            "evidence_scope": "noncausal_association",
            "evidence_trace": [
                _run_evidence_trace(run)
                for run in sorted(records, key=lambda item: item["id"])
            ],
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
        lineage = run.get("evidence_lineage") or {}
        if (
            base is None
            or run.get("seed") is None
            or run.get("evidence_design", {}).get("classification")
            != "isolated_comparison"
            or run.get("evidence_design", {}).get("causal_eligibility")
            != "candidate"
            or lineage.get("compliance_status") == "inconclusive"
        ):
            continue
        key = (
            run["flight_id"],
            run["intent_id"],
            run["provider"],
            run["model_version"],
            run["seed"],
            run["compiler_version"],
            run["paradigm"],
            json.dumps(
                sorted(run.get("evidence_design", {}).get("outcome_concept_ids", [])),
                separators=(",", ":"),
            ),
            json.dumps(run.get("concept_content_hashes", {}), sort_keys=True, separators=(",", ":")),
            lineage.get("intent_hash"),
            lineage.get("context_hash"),
            json.dumps(lineage.get("profile_hashes", {}), sort_keys=True, separators=(",", ":")),
            json.dumps(lineage.get("block_hashes", {}), sort_keys=True, separators=(",", ":")),
            json.dumps(lineage.get("asset_hashes", {}), sort_keys=True, separators=(",", ":")),
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
            declared_outcomes = set(
                winner["evidence_design"]["outcome_concept_ids"]
            )
            shared = sorted(
                declared_outcomes
                & set(winner.get("concept_ids", []))
                & set(loser.get("concept_ids", []))
                - {delta_concept}
            )
            for target in shared:
                evidence = sorted([winner["id"], loser["id"]])
                context = winner["intent_class"]
                edge = {
                    "id": _edge_id(
                        (
                            delta_concept,
                            target,
                            "promotes",
                            winner["flight_id"],
                            winner["provider"],
                            winner["model_version"],
                            context,
                        )
                    ),
                    "u": delta_concept,
                    "v": target,
                    "type": "promotes",
                    "weight": 1.0,
                    "evidence": evidence,
                    "provider": winner["provider"],
                    "model_version": winner["model_version"],
                    "context": context,
                    "n_obs": 2,
                    "derivation_policy": DERIVATION_POLICY,
                    "evidence_scope": "causal_isolated_comparison",
                    "evidence_trace": [
                        _run_evidence_trace(run) for run in (winner, loser)
                    ],
                    "isolated_comparison": {
                        "flight_id": winner["flight_id"],
                        "flight_hash": winner["flight_hash"],
                        "control_id": winner["tested_delta"]["control_id"],
                        "concept_id": delta_concept,
                        "winner": {
                            **_run_evidence_trace(winner),
                            "control_value": winner["tested_delta"]["value"],
                        },
                        "loser": {
                            **_run_evidence_trace(loser),
                            "control_value": loser["tested_delta"]["value"],
                        },
                        "same_seed": True,
                        "same_compiler_version": True,
                        "same_controls_except_delta": True,
                        "same_intent_context_profiles_blocks_assets": True,
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
            "provider": "all",
            "model_version": model,
            "context": context,
            "n_obs": len(evidence),
            "derivation_policy": DERIVATION_POLICY,
            "evidence_scope": "noncausal_observation",
            "evidence_trace": [],
        }
        for (u, v, model), evidence in sorted(groups.items())
    ]


@authority_reader("reflection_projection")
def project_run_edges(
    candidate_runs: list[dict[str, Any]], root: Path = REPO_ROOT
) -> list[dict[str, Any]]:
    """Project learned edges attributable only to the supplied runs."""
    current = read_jsonl(root / "lab" / "second_brain" / "immutable" / "runs.jsonl")
    by_id = {row["id"]: row for row in current}
    for run in candidate_runs:
        if "record_hash" in run:
            validate_instance("run", run, root)
        candidate = {
            key: value
            for key, value in run.items()
            if key not in {"prior_record_hash", "record_hash"}
        }
        existing = by_id.get(run["id"])
        if existing is not None:
            comparable = {
                key: value
                for key, value in existing.items()
                if key not in {"prior_record_hash", "record_hash"}
            }
            if comparable != candidate:
                raise ValueError(f"candidate run conflicts with immutable run {run['id']}")
            continue
        by_id[run["id"]] = candidate
    after = {
        edge["id"]: edge
        for edge in _association_edges(list(by_id.values()))
        + _promotion_edges(list(by_id.values()))
    }
    candidate_ids = {row["id"] for row in candidate_runs}
    return [
        after[edge_id]
        for edge_id in sorted(after)
        if set(after[edge_id].get("evidence", [])) <= candidate_ids
        and bool(after[edge_id].get("evidence"))
    ]


@authority_reader("reflection_snapshot")
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
        "controlled_runs": sum(run.get("legacy") is None for run in runs),
        "isolated_comparison_runs": sum(
            run.get("evidence_design", {}).get("classification")
            == "isolated_comparison"
            for run in runs
        ),
        "bundled_observation_runs": sum(
            run.get("evidence_design", {}).get("classification")
            == "bundled_observation"
            for run in runs
        ),
        "causal_learned_edges": sum(
            edge.get("evidence_scope") == "causal_isolated_comparison"
            for edge in learned
        ),
        "pegasus_observations": len(observations),
        "measurement_observations": len(measurements),
        "concepts_with_immutable_evidence": len(concept_to_evidence),
        "concepts_without_immutable_evidence": uncovered,
        "likely_gaps_by_layer": dict(sorted(uncovered_by_layer.items())),
        "learned_edges": len(learned),
    }
    indexes = build_index_catalog(root, learned_edges=learned)
    validate_instance("derived_indexes", indexes, root)
    insights = [
        {
            "id": f"insight_{edge['id'][8:]}",
            "edge_id": edge["id"],
            "statement": f"{edge['u']} {edge['type']} {edge['v']}",
            "evidence": edge["evidence"],
            "provider": edge["provider"],
            "model_version": edge["model_version"],
            "context": edge["context"],
            "evidence_scope": edge["evidence_scope"],
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
    from .source_registry import build_source_closure_report

    return {
        "weights": weights,
        "insights": insights,
        "coverage": coverage,
        "indexes": indexes,
        "source_closure": build_source_closure_report(root),
    }


@authority_writer("reflection")
def rebuild(
    root: Path = REPO_ROOT,
    *,
    targets: set[str] | None = None,
) -> dict[str, str]:
    """Rebuild all derived views or an explicit dependency-closed subset."""
    sb = root / "lab" / "second_brain"
    derived = sb / "derived"
    values = materialize(root)
    from .maintenance import (
        build_brain_health_report,
        build_core_memory_view,
        build_domain_coverage_report,
        build_outcome_memory,
    )

    values.update(
        domain_coverage=build_domain_coverage_report(root),
        core_memory=build_core_memory_view(root),
        outcome_memory=build_outcome_memory(root),
    )
    assert_write_target("reflect", derived, root)
    if targets is None and derived.exists():
        shutil.rmtree(derived)
    derived.mkdir(parents=True, exist_ok=True)
    outputs = {
        derived / "weights.json": ("json", values["weights"]),
        derived / "insights.jsonl": ("jsonl", values["insights"]),
        derived / "coverage.json": ("json", values["coverage"]),
        derived / "source_closure.json": ("json", values["source_closure"]),
        derived / "indexes" / "catalog.json": ("json", values["indexes"]),
        derived / "indexes" / "concept_to_evidence.json": (
            "indexes",
            "json",
            {
                "algorithm_version": values["indexes"]["algorithm_version"],
                "concept_to_evidence": values["indexes"]["concept_to_evidence"],
            },
        ),
        derived / "domain_coverage.json": (
            "domain_coverage",
            "json",
            values["domain_coverage"],
        ),
        derived / "core_memory.json": (
            "core_memory",
            "json",
            values["core_memory"],
        ),
        derived / "outcome_memory.json": (
            "outcome_memory",
            "json",
            values["outcome_memory"],
        ),
    }
    normalized_outputs: dict[Path, tuple[str, str, Any]] = {}
    for path, value in outputs.items():
        if len(value) == 2:
            kind, payload = value
            target = {
                "weights.json": "weights",
                "insights.jsonl": "insights",
                "coverage.json": "coverage",
                "source_closure.json": "source_closure",
                "catalog.json": "indexes",
            }[path.name]
            normalized_outputs[path] = (target, kind, payload)
        else:
            normalized_outputs[path] = value
    selected = set(targets) if targets is not None else {
        target for target, _, _ in normalized_outputs.values()
    } | {"brain_health"}
    unknown = selected - {
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
    if unknown:
        raise ValueError("unknown derived rebuild targets: " + ", ".join(sorted(unknown)))
    touched: list[Path] = []
    for path, (target, kind, value) in normalized_outputs.items():
        if target not in selected:
            continue
        assert_write_target("reflect", path, root)
        (write_jsonl if kind == "jsonl" else write_json)(path, value)
        touched.append(path)
    if "brain_health" in selected:
        health_path = derived / "brain_health.json"
        health = build_brain_health_report(root)
        assert_write_target("reflect", health_path, root)
        write_json(health_path, health)
        touched.append(health_path)
    return {
        str(path.relative_to(derived)): "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(touched)
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("rebuild",))
    args = parser.parse_args(argv)
    if args.command == "rebuild":
        print(json.dumps(rebuild(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
