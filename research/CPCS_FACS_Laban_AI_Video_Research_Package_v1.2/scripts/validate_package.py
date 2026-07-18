#!/usr/bin/env python3
"""Validate the CPCS research package without network access.

Checks Markdown structure, citation/reference resolution, RAG JSONL schema
conformance, JSON/YAML/XML syntax, Python syntax, local cross-schema
references, canonical examples, and reference-index consistency.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: python -m pip install -r requirements.txt") from exc

try:
    from jsonschema import Draft202012Validator, validators
    from referencing import Registry, Resource
except ImportError as exc:  # pragma: no cover
    raise SystemExit("jsonschema and referencing are required: python -m pip install -r requirements.txt") from exc

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "CPCS_FACS_Laban_AI_Video_Directorial_Control_Research_Paper.md"
RAG = ROOT / "rag" / "CPCS_RAG_Corpus.jsonl"
RAG_SCHEMA = ROOT / "schemas" / "CPCS_RAG_Record_Schema.json"
OBS_SCHEMA = ROOT / "schemas" / "CPCS_Video_Observation_Record_Schema.json"
GRAPH_SCHEMA = ROOT / "schemas" / "CPCS_Video_Observation_Graph_Schema.json"
EXTRACTION_SCHEMA = ROOT / "schemas" / "CPCS_Video_Extraction_Record_Schema.json"


def add(checks: list[dict[str, Any]], name: str, passed: bool, **details: Any) -> None:
    checks.append({"name": name, "passed": bool(passed), **details})


def validate_instance(instance: Any, schema: dict[str, Any], registry: Registry | None = None) -> list[str]:
    validator_cls = validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema, registry=registry) if registry is not None else validator_cls(schema)
    errors = []
    for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path)):
        path = "/" + "/".join(str(part) for part in error.absolute_path)
        errors.append(f"{path or '/'}: {error.message}")
    return errors


def parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        raise ValueError("Paper has no YAML front matter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("Paper front matter is unterminated")
    data = yaml.safe_load(text[4:end])
    if not isinstance(data, dict):
        raise ValueError("Paper front matter is not a mapping")
    return data


def paper_checks(checks: list[dict[str, Any]]) -> dict[str, Any]:
    text = PAPER.read_text(encoding="utf-8")
    front = parse_frontmatter(text)
    add(checks, "paper_frontmatter", True, version=str(front.get("version")), document_id=front.get("document_id"))

    fence_count = sum(1 for line in text.splitlines() if line.lstrip().startswith("```"))
    add(checks, "paper_code_fences_balanced", fence_count % 2 == 0, fence_count=fence_count)

    explicit_anchors = re.findall(r'<a id="([^"]+)"></a>', text)
    duplicate_anchors = sorted(key for key, count in Counter(explicit_anchors).items() if count > 1)
    add(
        checks,
        "paper_explicit_anchors_unique",
        not duplicate_anchors,
        anchor_count=len(explicit_anchors),
        duplicates=duplicate_anchors,
    )

    internal_targets = re.findall(r"\]\(#([^)]+)\)", text)
    missing_targets = sorted(set(internal_targets) - set(explicit_anchors))
    add(
        checks,
        "paper_internal_anchor_links_resolve",
        not missing_targets,
        link_count=len(internal_targets),
        missing=missing_targets,
    )

    rag_markers = re.findall(r'<!--\s*RAG_CHUNK\s+id="([^"]+)"', text)
    duplicate_markers = sorted(key for key, count in Counter(rag_markers).items() if count > 1)
    add(
        checks,
        "paper_rag_markers_unique",
        not duplicate_markers,
        marker_count=len(rag_markers),
        duplicates=duplicate_markers,
    )

    unfenced_lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            unfenced_lines.append(line)
    unfenced_text = "\n".join(unfenced_lines)
    numbered = []
    for match in re.finditer(r"^#\s+(\d+)\.\s+", unfenced_text, flags=re.MULTILINE):
        numbered.append(int(match.group(1)))
    expected = list(range(1, 32))
    add(checks, "paper_main_section_sequence", numbered == expected, observed=numbered, expected=expected)

    if "# Full Reference List" not in text:
        add(checks, "paper_citations_resolve", False, error="Full Reference List heading missing")
        return {"frontmatter": front, "text": text, "source_ids": []}

    body, bibliography = text.split("# Full Reference List", 1)
    cited = {f"S{token}" for token in re.findall(r"\[S(\d+[A-Z]?)\]", body)}
    source_ids = re.findall(r'<a id="source-(S\d+[A-Z]?)"></a>', bibliography)
    source_set = set(source_ids)
    duplicate_sources = sorted(key for key, count in Counter(source_ids).items() if count > 1)
    add(
        checks,
        "paper_bibliography_source_ids_unique",
        not duplicate_sources,
        source_count=len(source_ids),
        duplicates=duplicate_sources,
    )
    add(
        checks,
        "paper_citations_resolve",
        cited == source_set,
        cited_count=len(cited),
        bibliography_count=len(source_set),
        unresolved_citations=sorted(cited - source_set),
        uncited_sources=sorted(source_set - cited),
    )
    return {"frontmatter": front, "text": text, "source_ids": source_ids}


def syntax_checks(checks: list[dict[str, Any]]) -> None:
    json_errors: list[str] = []
    json_count = 0
    for path in sorted(ROOT.rglob("*.json")):
        # The report may not exist on the first run; when it does, it is ordinary JSON.
        try:
            json.loads(path.read_text(encoding="utf-8"))
            json_count += 1
        except Exception as exc:  # noqa: BLE001
            json_errors.append(f"{path.relative_to(ROOT)}: {exc}")
    add(checks, "json_files_parse", not json_errors, file_count=json_count, errors=json_errors)

    jsonl_errors: list[str] = []
    jsonl_count = 0
    jsonl_record_count = 0
    for path in sorted(ROOT.rglob("*.jsonl")):
        jsonl_count += 1
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                json.loads(line)
                jsonl_record_count += 1
            except Exception as exc:  # noqa: BLE001
                jsonl_errors.append(f"{path.relative_to(ROOT)}:{line_number}: {exc}")
    add(
        checks,
        "jsonl_lines_parse",
        not jsonl_errors,
        file_count=jsonl_count,
        record_count=jsonl_record_count,
        errors=jsonl_errors,
    )

    yaml_errors: list[str] = []
    yaml_count = 0
    for path in sorted(ROOT.rglob("*.yaml")):
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
            yaml_count += 1
        except Exception as exc:  # noqa: BLE001
            yaml_errors.append(f"{path.relative_to(ROOT)}: {exc}")
    add(checks, "yaml_files_parse", not yaml_errors, file_count=yaml_count, errors=yaml_errors)

    import xml.etree.ElementTree as ET

    xml_errors: list[str] = []
    xml_count = 0
    for path in sorted(ROOT.rglob("*.xml")):
        try:
            ET.parse(path)
            xml_count += 1
        except Exception as exc:  # noqa: BLE001
            xml_errors.append(f"{path.relative_to(ROOT)}: {exc}")
    add(checks, "xml_files_parse", not xml_errors, file_count=xml_count, errors=xml_errors)

    py_errors: list[str] = []
    py_count = 0
    for path in sorted((ROOT / "scripts").glob("*.py")):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            py_count += 1
        except Exception as exc:  # noqa: BLE001
            py_errors.append(f"{path.relative_to(ROOT)}: {exc}")
    add(checks, "python_scripts_compile", not py_errors, file_count=py_count, errors=py_errors)


def schema_checks(checks: list[dict[str, Any]]) -> None:
    rag_schema = json.loads(RAG_SCHEMA.read_text(encoding="utf-8"))
    rag_validator = Draft202012Validator(rag_schema)
    rag_errors: list[str] = []
    rag_ids: list[str] = []
    rag_count = 0
    for line_number, line in enumerate(RAG.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        rag_count += 1
        rag_ids.append(str(record.get("record_id")))
        for error in rag_validator.iter_errors(record):
            path = "/" + "/".join(str(part) for part in error.absolute_path)
            rag_errors.append(f"line {line_number} {path}: {error.message}")
    duplicates = sorted(key for key, count in Counter(rag_ids).items() if count > 1)
    add(checks, "rag_json_schema_validation", not rag_errors, record_count=rag_count, errors=rag_errors[:100])
    add(checks, "rag_record_ids_unique", not duplicates, duplicates=duplicates)

    record_schema = json.loads(OBS_SCHEMA.read_text(encoding="utf-8"))
    graph_schema = json.loads(GRAPH_SCHEMA.read_text(encoding="utf-8"))
    registry = Registry().with_resource(record_schema["$id"], Resource.from_contents(record_schema))
    registry = registry.with_resource(OBS_SCHEMA.resolve().as_uri(), Resource.from_contents(record_schema))

    graph_results = []
    for path in [
        ROOT / "examples" / "video_to_cpcs" / "canonical_video_observation_graph.json",
        ROOT / "tests" / "fixtures" / "canonical_graph_validated.json",
    ]:
        instance = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_instance(instance, graph_schema, registry)
        graph_results.append({"file": str(path.relative_to(ROOT)), "errors": errors})
    add(
        checks,
        "canonical_graph_examples_validate",
        all(not item["errors"] for item in graph_results),
        results=graph_results,
    )

    extraction_schema = json.loads(EXTRACTION_SCHEMA.read_text(encoding="utf-8"))
    extraction_instance = json.loads((ROOT / "examples" / "source_video_extraction_example.json").read_text(encoding="utf-8"))
    extraction_errors = validate_instance(extraction_instance, extraction_schema)
    add(
        checks,
        "extended_extraction_fixture_validates",
        not extraction_errors,
        errors=extraction_errors,
    )

    observation_errors: list[str] = []
    observation_count = 0
    observations_path = ROOT / "examples" / "video_to_cpcs" / "provider_fusion_observations.jsonl"
    for line_number, line in enumerate(observations_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        observation_count += 1
        record = json.loads(line)
        for error in Draft202012Validator(record_schema).iter_errors(record):
            path = "/" + "/".join(str(part) for part in error.absolute_path)
            observation_errors.append(f"line {line_number} {path}: {error.message}")
    add(
        checks,
        "provider_fusion_observations_validate",
        not observation_errors,
        record_count=observation_count,
        errors=observation_errors,
    )


def reference_index_checks(checks: list[dict[str, Any]], paper_source_ids: list[str]) -> None:
    index = json.loads((ROOT / "references" / "CPCS_Reference_Index.json").read_text(encoding="utf-8"))
    records = index if isinstance(index, list) else index.get("references", [])
    index_count = len(records)
    ids = [item.get("source_id") for item in records]
    add(
        checks,
        "reference_index_matches_paper",
        ids == paper_source_ids and index_count == len(paper_source_ids),
        index_count=index_count,
        paper_count=len(paper_source_ids),
        missing_from_index=sorted(set(paper_source_ids) - set(ids)),
        extra_in_index=sorted(set(ids) - set(paper_source_ids)),
    )
    malformed_urls = []
    for record in records:
        for url in record.get("urls", []):
            if not re.match(r"^https?://\S+$", url):
                malformed_urls.append({"source_id": record.get("source_id"), "url": url})
    add(checks, "reference_urls_syntactically_valid", not malformed_urls, malformed=malformed_urls)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-report",
        type=Path,
        default=ROOT / "manifests" / "PACKAGE_VALIDATION_REPORT.json",
        help="Path for the JSON validation report",
    )
    args = parser.parse_args()

    checks: list[dict[str, Any]] = []
    try:
        paper = paper_checks(checks)
        syntax_checks(checks)
        schema_checks(checks)
        reference_index_checks(checks, paper["source_ids"])
    except Exception as exc:  # noqa: BLE001
        add(checks, "validator_runtime", False, error=f"{type(exc).__name__}: {exc}")

    failed = [item for item in checks if not item["passed"]]
    report = {
        "schema": "cpcs-package-validation/1.0",
        "package": ROOT.name,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "validator": "scripts/validate_package.py",
        "check_count": len(checks),
        "passed_count": len(checks) - len(failed),
        "failed_count": len(failed),
        "overall_valid": not failed,
        "checks": checks,
        "notes": [
            "This report validates local structure and fixtures; it does not call hosted model APIs.",
            "Provider capabilities must be rechecked against official documentation at execution time.",
            "Checksum and ZIP integrity are verified after this report is generated to avoid checksum cycles.",
        ],
    }
    args.write_report.parent.mkdir(parents=True, exist_ok=True)
    args.write_report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("package", "check_count", "passed_count", "failed_count", "overall_valid")}, indent=2))
    if failed:
        for item in failed:
            print(f"FAILED: {item['name']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
