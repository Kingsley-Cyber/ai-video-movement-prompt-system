"""Compile reasoned concepts through curated mappings and named rule evaluators."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .query import (
    ALLOWED_ADMISSION_REASONS,
    QUERY_POLICY,
    default_request,
    reason,
)
from .rules import (
    controls_for_selection,
    evaluate_rules,
    mappings_for_selection,
)
from .validate import REPO_ROOT, read_jsonl


def compile_result(
    reasoning: dict[str, Any],
    target_format: str | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    sb = root / "lab" / "second_brain"
    selected_rows = reasoning["selected_concepts"]
    unsafe_rows = [
        item
        for item in selected_rows
        if item.get("admission_reason") not in ALLOWED_ADMISSION_REASONS
        or item.get("policy_version") != QUERY_POLICY["version"]
    ]
    if (
        reasoning.get("policy_version") != QUERY_POLICY["version"]
        or unsafe_rows
    ):
        raise ValueError(
            "compiler requires a relevance-gated reasoning result from "
            f"{QUERY_POLICY['version']}"
        )
    selected = {item["id"] for item in selected_rows}
    rejected = {
        item["id"] for item in reasoning.get("rejected_concepts", [])
    }
    recovered = sorted(selected & rejected)
    if recovered:
        raise ValueError(
            "compiler cannot recover rejected concepts: "
            + ", ".join(recovered)
        )
    mappings = mappings_for_selection(
        read_jsonl(sb / "curated" / "mappings.jsonl"),
        selected,
        reasoning["query"].get("provider"),
        reasoning["query"].get("model_version"),
    )
    controls = controls_for_selection(
        mappings,
        selected,
        reasoning["query"].get("provider"),
        reasoning["query"].get("model_version"),
    )
    rules = read_jsonl(sb / "curated" / "rules.jsonl")
    rule_results = evaluate_rules(rules, selected, controls)
    package = {
        "goal": reasoning["query"]["goal"],
        "selected_concepts": reasoning["selected_concepts"],
        "mappings": sorted(mappings, key=lambda item: item["id"]),
        "controls": sorted(controls),
        "rule_results": rule_results,
        "explanation": {
            "path_taken": reasoning["path_taken"],
            "edge_types_used": reasoning["edge_types_used"],
            "alternative_valid_paths": reasoning["alternative_valid_paths"],
            "rejected_concepts": reasoning["rejected_concepts"],
            "conflicts": reasoning["conflicts_encountered"],
            "evidence_ids": reasoning["evidence_ids"],
            "sources": reasoning["source_references"],
            "knowledge_gap": reasoning["knowledge_gap"],
        },
    }
    format_name = target_format or reasoning["query"]["target_format"]
    if format_name == "hybrid":
        format_name = "json"
    environment = Environment(
        loader=FileSystemLoader(str(sb / "templates")),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )
    rendered = environment.get_template(f"{format_name}.j2").render(package=package)
    return {"target_format": format_name, "package": package, "rendered": rendered}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("goal")
    parser.add_argument("--target-format", choices=("prose", "yaml", "json", "xml", "hybrid"), default="hybrid")
    parser.add_argument("--domain")
    parser.add_argument("--provider")
    parser.add_argument("--model-version")
    parser.add_argument("--maximum-depth", type=int, default=5)
    parser.add_argument(
        "--minimum-status",
        choices=("ingested", "partial", "proven"),
        default="partial",
    )
    parser.add_argument("--include-unproven", action="store_true")
    parser.add_argument("--required-layer", action="append", default=[])
    parser.add_argument("--excluded-layer", action="append", default=[])
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    request = default_request(
        args.goal,
        target_format=args.target_format,
        domain=args.domain,
        provider=args.provider,
        model_version=args.model_version,
        maximum_depth=args.maximum_depth,
        minimum_status=args.minimum_status,
        include_unproven=args.include_unproven,
        required_layers=args.required_layer,
        excluded_layers=args.excluded_layer,
        deterministic_seed=args.seed,
    )
    print(compile_result(reason(request), args.target_format)["rendered"])


if __name__ == "__main__":
    main()
