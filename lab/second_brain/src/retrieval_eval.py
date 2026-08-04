"""Qualify production retrieval against labeled expected and forbidden concepts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from .authority import authority_reader
from .intent import build_intent_context, load_profile_policy
from .query import QUERY_POLICY, default_request, reason
from .validate import (
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    canonical_json_bytes,
    read_jsonl,
    sha256_value,
    validate_instance,
    write_json,
)

DEFAULT_BENCHMARK = Path("lab/second_brain/retrieval_benchmark.yaml")
MAX_BENCHMARK_BYTES = 1_048_576
REPORT_SCHEMA = "cpcs.retrieval_benchmark_report/1.0"
AUTHORITY_PATHS = (
    Path("lab/concepts.jsonl"),
    Path("lab/second_brain/curated"),
    Path("lab/second_brain/immutable"),
    Path("lab/second_brain/staging"),
    Path("lab/second_brain/derived"),
)


def _authority_snapshot(root: Path) -> str:
    hashes: dict[str, str] = {}
    for relative in AUTHORITY_PATHS:
        target = root / relative
        paths = [target] if target.is_file() else sorted(target.rglob("*"))
        for path in paths:
            if path.is_symlink():
                raise ValidationFailure(f"authority snapshot rejects symlink: {path}")
            if not path.is_file():
                continue
            key = str(path.relative_to(root))
            hashes[key] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    return sha256_value(hashes)


def _resolve_benchmark_path(path: Path, root: Path) -> Path:
    requested = path.expanduser()
    candidate = requested if requested.is_absolute() else root / requested
    if candidate.is_symlink():
        raise ValidationFailure("retrieval benchmark path cannot be a symlink")
    resolved = candidate.resolve()
    resolved_root = root.resolve()
    if resolved_root not in resolved.parents:
        raise ValidationFailure("retrieval benchmark path escaped the repository root")
    if not resolved.is_file():
        raise ValidationFailure(f"retrieval benchmark file is missing: {resolved}")
    if resolved.stat().st_size > MAX_BENCHMARK_BYTES:
        raise ValidationFailure("retrieval benchmark exceeds the 1 MiB input limit")
    return resolved


def _load_benchmark(path: Path, root: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    validate_instance("retrieval_benchmark", value, root)
    case_ids = [row["case_id"] for row in value["cases"]]
    if len(case_ids) != len(set(case_ids)):
        raise ValidationFailure("retrieval benchmark case IDs must be unique")
    known = {
        row["id"] for row in read_jsonl(root / "lab" / "concepts.jsonl")
    }
    intent_policy = load_profile_policy(root)
    known_profiles = set(intent_policy["profiles"])
    known_conflicts = {row["id"] for row in intent_policy["conflicts"]}
    for row in value["cases"]:
        expected = set(row["expected_concepts"])
        forbidden = set(row["forbidden_concepts"])
        unknown = (expected | forbidden) - known
        if unknown:
            raise ValidationFailure(
                f"{row['case_id']} references unknown concepts: {sorted(unknown)}"
            )
        overlap = expected & forbidden
        if overlap:
            raise ValidationFailure(
                f"{row['case_id']} expects and forbids the same concepts: {sorted(overlap)}"
            )
        layer_overlap = set(row["required_layers"]) & set(row["excluded_layers"])
        if layer_overlap:
            raise ValidationFailure(
                f"{row['case_id']} requires and excludes layers: {sorted(layer_overlap)}"
            )
        if row["mode"] == "reason":
            if (
                row["profile_overrides"]
                or row["expected_primary_profile"] is not None
                or row["expected_secondary_profiles"]
                or row["expected_conflicts"]
            ):
                raise ValidationFailure(
                    f"{row['case_id']} reason mode cannot assert intent profiles"
                )
        elif row["domain"] is not None or row["required_layers"] or row["excluded_layers"]:
            raise ValidationFailure(
                f"{row['case_id']} intent_context routing must own domain and layers"
            )
        else:
            profile_refs = set(row["profile_overrides"]) | set(
                row["expected_secondary_profiles"]
            )
            if row["expected_primary_profile"] is not None:
                profile_refs.add(row["expected_primary_profile"])
            unknown_profiles = profile_refs - known_profiles
            if unknown_profiles:
                raise ValidationFailure(
                    f"{row['case_id']} references unknown profiles: {sorted(unknown_profiles)}"
                )
            unknown_conflicts = set(row["expected_conflicts"]) - known_conflicts
            if unknown_conflicts:
                raise ValidationFailure(
                    f"{row['case_id']} references unknown conflicts: {sorted(unknown_conflicts)}"
                )
    return value


def _execute_case(
    row: dict[str, Any],
    policy: dict[str, Any],
    root: Path,
) -> tuple[dict[str, Any], list[str], str | None, list[str], list[str]]:
    if row["mode"] == "reason":
        result = reason(
            default_request(
                row["query"],
                domain=row["domain"],
                required_layers=row["required_layers"],
                excluded_layers=row["excluded_layers"],
                minimum_status=policy["minimum_status"],
            ),
            root,
        )
        return (
            result,
            [item["id"] for item in result["selected_concepts"]],
            None,
            [],
            [],
        )
    result = build_intent_context(
        row["query"],
        token_budget=policy["token_budget"],
        profile_overrides=row["profile_overrides"],
        minimum_status=policy["minimum_status"],
        root=root,
    )
    normalized = result["normalized_intent"]
    return (
        result,
        [item["id"] for item in result["context_bundle"]["selected_concepts"]],
        normalized["profiles"]["primary"],
        list(normalized["profiles"]["secondary"]),
        [item["id"] for item in normalized["conflicts"]],
    )


def _profile_failures(
    row: dict[str, Any],
    primary: str | None,
    secondary: list[str],
    conflicts: list[str],
) -> list[str]:
    failures = []
    if primary != row["expected_primary_profile"]:
        failures.append(
            f"primary_profile expected={row['expected_primary_profile']} actual={primary}"
        )
    if secondary != row["expected_secondary_profiles"]:
        failures.append(
            "secondary_profiles expected="
            f"{row['expected_secondary_profiles']} actual={secondary}"
        )
    if conflicts != row["expected_conflicts"]:
        failures.append(
            f"conflicts expected={row['expected_conflicts']} actual={conflicts}"
        )
    return failures


@authority_reader("retrieval_benchmark_snapshot")
def run_benchmark(
    benchmark_path: Path | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Run every labeled case twice under one read snapshot."""
    path = _resolve_benchmark_path(
        benchmark_path or DEFAULT_BENCHMARK,
        root,
    )
    benchmark = _load_benchmark(path, root)
    before = _authority_snapshot(root)
    case_results = []
    required_total = 0
    required_found = 0
    forbidden_total = 0
    forbidden_selected = 0
    deterministic_cases = 0
    for row in benchmark["cases"]:
        first = _execute_case(row, benchmark["policy"], root)
        second = _execute_case(row, benchmark["policy"], root)
        first_payload, selected, primary, secondary, conflicts = first
        deterministic = canonical_json_bytes(first_payload) == canonical_json_bytes(
            second[0]
        )
        if deterministic:
            deterministic_cases += 1
        selected_set = set(selected)
        missing = sorted(set(row["expected_concepts"]) - selected_set)
        forbidden = sorted(set(row["forbidden_concepts"]) & selected_set)
        profile_failures = _profile_failures(
            row,
            primary,
            secondary,
            conflicts,
        )
        required_total += len(row["expected_concepts"])
        required_found += len(row["expected_concepts"]) - len(missing)
        forbidden_total += len(row["forbidden_concepts"])
        forbidden_selected += len(forbidden)
        passed = not missing and not forbidden and not profile_failures and deterministic
        case_results.append(
            {
                "case_id": row["case_id"],
                "mode": row["mode"],
                "selected_concepts": selected,
                "missing_expected": missing,
                "selected_forbidden": forbidden,
                "primary_profile": primary,
                "secondary_profiles": secondary,
                "conflict_ids": conflicts,
                "profile_failures": profile_failures,
                "replay_hash": sha256_value(first_payload),
                "deterministic_replay": deterministic,
                "status": "passed" if passed else "failed",
            }
        )
    after = _authority_snapshot(root)
    authority_unchanged = before == after
    cases_passed = sum(row["status"] == "passed" for row in case_results)
    status = (
        "passed"
        if authority_unchanged and cases_passed == len(case_results)
        else "failed"
    )
    report = {
        "schema": REPORT_SCHEMA,
        "benchmark_id": benchmark["benchmark_id"],
        "benchmark_hash": sha256_value(benchmark),
        "query_policy": QUERY_POLICY["version"],
        "authority_snapshot_hash": before,
        "authority_unchanged": authority_unchanged,
        "case_results": case_results,
        "summary": {
            "cases": len(case_results),
            "cases_passed": cases_passed,
            "required_concepts": required_total,
            "required_found": required_found,
            "forbidden_concepts": forbidden_total,
            "forbidden_selected": forbidden_selected,
            "required_recall": round(required_found / required_total, 6),
            "forbidden_clean_rate": round(
                1 - forbidden_selected / forbidden_total,
                6,
            ),
            "deterministic_cases": deterministic_cases,
        },
        "status": status,
    }
    validate_instance("retrieval_benchmark_report", report, root)
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
