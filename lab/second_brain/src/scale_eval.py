"""Qualify local retrieval and rebuild behavior at 10x and 100x concept scale."""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import json
import math
import platform
import re
import shutil
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any, Callable, TypeVar

import yaml

from .graph import build_live_graph, graph_stats
from .indexes import build_index_catalog
from .query import default_request, reason
from .reflect import rebuild
from .validate import (
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    canonical_json_bytes,
    read_jsonl,
    sha256_value,
    validate_instance,
    write_json,
    write_jsonl,
)


DEFAULT_BENCHMARK = Path("lab/second_brain/scale_benchmark.yaml")
MAX_BENCHMARK_BYTES = 1_048_576
REPORT_SCHEMA = "cpcs.scale_benchmark_report/1.0"
CLONE_SUFFIX = re.compile(r"__scale_[0-9]{3}$")
AUTHORITY_PATHS = (
    Path("lab/concepts.jsonl"),
    Path("lab/second_brain/curated"),
    Path("lab/second_brain/immutable"),
    Path("lab/second_brain/staging"),
    Path("lab/second_brain/derived"),
)
_VALUE = TypeVar("_VALUE")


def _authority_snapshot(root: Path) -> str:
    hashes: dict[str, str] = {}
    for relative in AUTHORITY_PATHS:
        target = root / relative
        paths = [target] if target.is_file() else sorted(target.rglob("*"))
        for path in paths:
            if path.is_symlink():
                raise ValidationFailure(f"authority snapshot rejects symlink: {path}")
            if path.is_file():
                hashes[str(path.relative_to(root))] = (
                    "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
                )
    return sha256_value(hashes)


def _resolve_benchmark_path(path: Path, root: Path) -> Path:
    requested = path.expanduser()
    candidate = requested if requested.is_absolute() else root / requested
    if candidate.is_symlink():
        raise ValidationFailure("scale benchmark path cannot be a symlink")
    resolved = candidate.resolve()
    resolved_root = root.resolve()
    if resolved_root not in resolved.parents:
        raise ValidationFailure("scale benchmark path escaped the repository root")
    if not resolved.is_file():
        raise ValidationFailure(f"scale benchmark file is missing: {resolved}")
    if resolved.stat().st_size > MAX_BENCHMARK_BYTES:
        raise ValidationFailure("scale benchmark exceeds the 1 MiB input limit")
    return resolved


def _load_benchmark(path: Path, root: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    validate_instance("scale_benchmark", value, root)
    factors = value["fixture_policy"]["scale_factors"]
    if factors != sorted(factors):
        raise ValidationFailure("scale factors must be in ascending order")
    if set(value["limits"]) != {str(factor) for factor in factors}:
        raise ValidationFailure("scale limits must exactly match configured factors")
    case_ids = [row["case_id"] for row in value["query_cases"]]
    if len(case_ids) != len(set(case_ids)):
        raise ValidationFailure("scale query case IDs must be unique")
    concepts = {row["id"] for row in read_jsonl(root / "lab" / "concepts.jsonl")}
    for row in value["query_cases"]:
        expected = set(row["expected_concepts"])
        forbidden = set(row["forbidden_concepts"])
        unknown = (expected | forbidden) - concepts
        if unknown:
            raise ValidationFailure(
                f"{row['case_id']} references unknown concepts: {sorted(unknown)}"
            )
        overlap = expected & forbidden
        if overlap:
            raise ValidationFailure(
                f"{row['case_id']} expects and forbids: {sorted(overlap)}"
            )
    return value


def _measure(function: Callable[[], _VALUE]) -> tuple[_VALUE, dict[str, Any]]:
    gc.collect()
    tracemalloc.start()
    started = time.perf_counter()
    try:
        value = function()
        seconds = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return value, {
        "seconds": round(seconds, 6),
        "peak_python_bytes": int(peak),
    }


def _clone_id(concept_id: str, replica: int) -> str:
    return f"{concept_id}__scale_{replica:03d}"


def _copy_fixture_support(source_root: Path, fixture_root: Path) -> None:
    source = source_root / "lab" / "second_brain"
    target = fixture_root / "lab" / "second_brain"
    (fixture_root / "lab").mkdir(parents=True)
    shutil.copytree(source / "schemas", target / "schemas")
    shutil.copy2(source / "analysis_profiles.yaml", target / "analysis_profiles.yaml")
    shutil.copytree(source / "templates", target / "templates")
    (target / "curated").mkdir()
    (target / "immutable").mkdir()
    for name in (
        "rules.jsonl",
        "intents.jsonl",
        "claims.jsonl",
        "equations.jsonl",
        "methods.jsonl",
        "mechanisms.jsonl",
    ):
        shutil.copy2(source / "curated" / name, target / "curated" / name)
    for name in (
        "flights.jsonl",
        "runs.jsonl",
        "pegasus_observations.jsonl",
        "measurement_observations.jsonl",
    ):
        shutil.copy2(source / "immutable" / name, target / "immutable" / name)
    for relative in (
        "staging/proposals.jsonl",
        "staging/rejected.jsonl",
        "staging/corpus_manifest.jsonl",
        "staging/distillation_runs.jsonl",
    ):
        write_jsonl(target / relative, [])


def _prepare_fixture(
    fixture_root: Path,
    factor: int,
    source_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Materialize an ignored, uniquely-IDed scale fixture from current authority."""
    if factor < 2 or factor > 100:
        raise ValidationFailure("scale fixture factor must be between 2 and 100")
    if fixture_root.exists():
        raise ValidationFailure("scale fixture target must not already exist")
    _copy_fixture_support(source_root, fixture_root)
    source_sb = source_root / "lab" / "second_brain"
    fixture_sb = fixture_root / "lab" / "second_brain"
    concepts = sorted(
        read_jsonl(source_root / "lab" / "concepts.jsonl"),
        key=lambda row: row["id"],
    )
    authored_edges = sorted(
        read_jsonl(source_sb / "curated" / "edges.jsonl"),
        key=lambda row: row["id"],
    )
    mappings = sorted(
        read_jsonl(source_sb / "curated" / "mappings.jsonl"),
        key=lambda row: row["id"],
    )
    scaled_concepts = [copy.deepcopy(row) for row in concepts]
    scaled_edges = [copy.deepcopy(row) for row in authored_edges]
    scaled_mappings = [copy.deepcopy(row) for row in mappings]
    next_edge = max(int(row["id"].split("_")[1]) for row in authored_edges) + 1
    mapping_by_concept: dict[str, list[dict[str, Any]]] = {}
    for mapping in mappings:
        mapping_by_concept.setdefault(mapping["concept_id"], []).append(mapping)
    for replica in range(1, factor):
        for concept in concepts:
            clone = copy.deepcopy(concept)
            clone_id = _clone_id(concept["id"], replica)
            clone["id"] = clone_id
            clone["scale_fixture"] = {
                "source_concept_id": concept["id"],
                "replica": replica,
            }
            scaled_concepts.append(clone)
            scaled_edges.append(
                {
                    "id": f"edge_{next_edge:06d}",
                    "u": clone_id,
                    "v": concept["id"],
                    "type": "refines",
                    "context": "scale_fixture",
                    "authored_by": "scale_benchmark",
                    "note": "Fixture-only bridge to exercise typed traversal; never curated.",
                    "sources": [
                        {
                            "ref": "scale-fixture://concept-clone",
                            "locator": f"{concept['id']}#{replica:03d}",
                        }
                    ],
                }
            )
            next_edge += 1
            for mapping in mapping_by_concept.get(concept["id"], []):
                mapped = copy.deepcopy(mapping)
                mapped["id"] = f"{mapping['id']}__scale_{replica:03d}"
                mapped["concept_id"] = clone_id
                scaled_mappings.append(mapped)
    write_jsonl(
        fixture_root / "lab" / "concepts.jsonl",
        sorted(scaled_concepts, key=lambda row: row["id"]),
    )
    write_jsonl(
        fixture_sb / "curated" / "edges.jsonl",
        sorted(scaled_edges, key=lambda row: row["id"]),
    )
    write_jsonl(
        fixture_sb / "curated" / "mappings.jsonl",
        sorted(scaled_mappings, key=lambda row: row["id"]),
    )
    payload = {
        "factor": factor,
        "source_concepts_hash": sha256_value(concepts),
        "source_edges_hash": sha256_value(authored_edges),
        "source_mappings_hash": sha256_value(mappings),
        "clone_relationship": "refines",
        "counts": {
            "concepts": len(scaled_concepts),
            "edges": len(scaled_edges),
            "mappings": len(scaled_mappings),
        },
    }
    return {**payload, "fixture_hash": sha256_value(payload)}


def _base_concept_id(concept_id: str) -> str:
    return CLONE_SUFFIX.sub("", concept_id)


def _tree_hashes(path: Path) -> dict[str, str]:
    return {
        str(item.relative_to(path)): "sha256:" + hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def _nearest_rank_p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def _run_queries(
    cases: list[dict[str, Any]],
    replays: int,
    minimum_status: str,
    fixture_root: Path,
) -> tuple[list[dict[str, Any]], float, float, int]:
    results = []
    all_seconds: list[float] = []
    peak = 0
    for case in cases:
        payloads = []
        replay_hashes = []
        replay_seconds = []
        for _ in range(replays):
            payload, measurement = _measure(
                lambda case=case: reason(
                    default_request(
                        case["query"],
                        domain=case["domain"],
                        minimum_status=minimum_status,
                    ),
                    fixture_root,
                )
            )
            payloads.append(payload)
            replay_hashes.append(sha256_value(payload))
            replay_seconds.append(measurement["seconds"])
            all_seconds.append(measurement["seconds"])
            peak = max(peak, measurement["peak_python_bytes"])
        selected = sorted(
            {
                _base_concept_id(row["id"])
                for row in payloads[0]["selected_concepts"]
            }
        )
        missing = sorted(set(case["expected_concepts"]) - set(selected))
        forbidden = sorted(set(case["forbidden_concepts"]) & set(selected))
        deterministic = len(set(replay_hashes)) == 1
        passed = deterministic and not missing and not forbidden
        results.append(
            {
                "case_id": case["case_id"],
                "selected_concepts": selected,
                "missing_expected": missing,
                "selected_forbidden": forbidden,
                "replay_hashes": replay_hashes,
                "replay_seconds": replay_seconds,
                "deterministic_replay": deterministic,
                "status": "passed" if passed else "failed",
            }
        )
    return (
        results,
        round(_nearest_rank_p95(all_seconds), 6),
        round(sum(all_seconds), 6),
        peak,
    )


def _threshold_failures(
    limits: dict[str, Any],
    measurements: dict[str, dict[str, Any]],
    query_p95: float,
    query_total: float,
    query_peak: int,
) -> list[str]:
    observed = {
        "ingest_seconds": measurements["ingest"]["seconds"],
        "graph_build_seconds": measurements["graph_build"]["seconds"],
        "index_build_seconds": measurements["index_build"]["seconds"],
        "query_p95_seconds": query_p95,
        "query_total_seconds": query_total,
        "rebuild_max_seconds": max(
            measurements["rebuild_first"]["seconds"],
            measurements["rebuild_second"]["seconds"],
        ),
        "peak_python_bytes": max(
            query_peak,
            *(row["peak_python_bytes"] for row in measurements.values()),
        ),
    }
    return sorted(
        f"{name}: observed={observed[name]} limit={limit}"
        for name, limit in limits.items()
        if observed[name] > limit
    )


def _run_scale(
    factor: int,
    benchmark: dict[str, Any],
    temporary: Path,
    source_root: Path,
) -> dict[str, Any]:
    fixture_root = temporary / f"scale-{factor}" / "repo"
    fixture, ingest_measurement = _measure(
        lambda: _prepare_fixture(fixture_root, factor, source_root)
    )
    graph, graph_measurement = _measure(lambda: build_live_graph(fixture_root))
    catalog, index_measurement = _measure(lambda: build_index_catalog(fixture_root))
    expected_counts = {
        "concepts": len(read_jsonl(source_root / "lab" / "concepts.jsonl")) * factor,
        "edges": len(
            read_jsonl(source_root / "lab" / "second_brain" / "curated" / "edges.jsonl")
        )
        + len(read_jsonl(source_root / "lab" / "concepts.jsonl")) * (factor - 1),
        "mappings": len(
            read_jsonl(source_root / "lab" / "second_brain" / "curated" / "mappings.jsonl")
        )
        * factor,
    }
    if fixture["counts"] != expected_counts:
        raise ValidationFailure(
            f"scale {factor} fixture counts drifted: {fixture['counts']} != {expected_counts}"
        )
    if graph_stats(graph)["nodes_by_tier"].get("curated") != expected_counts["concepts"]:
        raise ValidationFailure(f"scale {factor} graph omitted curated concepts")
    if catalog["dense_semantic_concepts"]["corpus_size"] != expected_counts["concepts"]:
        raise ValidationFailure(f"scale {factor} index omitted concepts")
    query_results, query_p95, query_total, query_peak = _run_queries(
        benchmark["query_cases"],
        benchmark["fixture_policy"]["deterministic_replays"],
        benchmark["fixture_policy"]["minimum_status"],
        fixture_root,
    )
    first, rebuild_first = _measure(lambda: rebuild(fixture_root))
    first_tree = _tree_hashes(fixture_root / "lab" / "second_brain" / "derived")
    second, rebuild_second = _measure(lambda: rebuild(fixture_root))
    second_tree = _tree_hashes(fixture_root / "lab" / "second_brain" / "derived")
    rebuild_deterministic = first == second and first_tree == second_tree
    measurements = {
        "ingest": ingest_measurement,
        "graph_build": graph_measurement,
        "index_build": index_measurement,
        "rebuild_first": rebuild_first,
        "rebuild_second": rebuild_second,
    }
    failures = _threshold_failures(
        benchmark["limits"][str(factor)],
        measurements,
        query_p95,
        query_total,
        query_peak,
    )
    passed = (
        not failures
        and rebuild_deterministic
        and all(row["status"] == "passed" for row in query_results)
    )
    return {
        "factor": factor,
        "fixture_hash": fixture["fixture_hash"],
        "fixture_counts": fixture["counts"],
        "measurements": measurements,
        "query_results": query_results,
        "query_p95_seconds": query_p95,
        "query_total_seconds": query_total,
        "query_peak_python_bytes": query_peak,
        "rebuild_deterministic": rebuild_deterministic,
        "rebuild_hash": sha256_value(first_tree),
        "threshold_failures": failures,
        "status": "passed" if passed else "failed",
    }


def run_benchmark(
    benchmark_path: Path | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Run fixed scale factors in ignored fixtures and prove source authority is unchanged."""
    path = _resolve_benchmark_path(benchmark_path or DEFAULT_BENCHMARK, root)
    benchmark = _load_benchmark(path, root)
    before = _authority_snapshot(root)
    work = root / "work" / "scale"
    assert_write_target("query", work, root)
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="scale-eval-", dir=work) as temporary:
        results = [
            _run_scale(factor, benchmark, Path(temporary), root)
            for factor in benchmark["fixture_policy"]["scale_factors"]
        ]
    after = _authority_snapshot(root)
    authority_unchanged = before == after
    query_results = [row for scale in results for row in scale["query_results"]]
    scales_passed = sum(row["status"] == "passed" for row in results)
    status = (
        "passed"
        if authority_unchanged and scales_passed == len(results)
        else "failed"
    )
    report = {
        "schema": REPORT_SCHEMA,
        "benchmark_id": benchmark["benchmark_id"],
        "benchmark_hash": sha256_value(benchmark),
        "source_authority_hash": before,
        "authority_unchanged": authority_unchanged,
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "scale_results": results,
        "summary": {
            "scales": len(results),
            "scales_passed": scales_passed,
            "largest_concept_count": max(row["fixture_counts"]["concepts"] for row in results),
            "query_cases": len(query_results),
            "query_cases_passed": sum(row["status"] == "passed" for row in query_results),
        },
        "status": status,
    }
    validate_instance("scale_benchmark_report", report, root)
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = run_benchmark(args.benchmark)
    if args.output is not None:
        output = args.output.expanduser().resolve()
        assert_write_target("query", output)
        write_json(output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
