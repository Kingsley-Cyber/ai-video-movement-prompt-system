#!/usr/bin/env python3
"""Validate the CPCS-MX research package and optionally write manifests."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

SOURCE_RE = re.compile(r"\[(S\d{3})\]")
RAG_MARKER_RE = re.compile(r'<!--\s*RAG_CHUNK\s+id="([^"]+)"')
TOC_LINK_RE = re.compile(r"\]\(#([^)]+)\)")
EXPLICIT_ANCHOR_RE = re.compile(r'<a\s+id="([^"]+)"\s*></a>')


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse error in {path}: {exc}") from exc


def validate_json(instance: Any, schema: dict[str, Any], label: str) -> list[str]:
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    return [f"{label} {list(e.path)}: {e.message}" for e in errors]


def relative_files(package: Path) -> list[Path]:
    return sorted(p for p in package.rglob("*") if p.is_file() and p.name not in {"SHA256SUMS.txt"})


def check_required_files(package: Path) -> list[str]:
    required = [
        "README.md",
        "NOTICE.md",
        "CHANGELOG.md",
        "CITATION.cff",
        "paper/CPCS_MX_Hierarchical_Motion_Grammar_Research_Paper.md",
        "rag/CPCS_MX_RAG_Corpus.jsonl",
        "schemas/CPCS_MX_Schema.json",
        "schemas/CPCS_MX_Authoring_Schema.json",
        "schemas/CPCS_MX_Observation_Record_Schema.json",
        "schemas/CPCS_MX_RAG_Record_Schema.json",
        "scripts/build_cpcs_mx_rag.py",
        "scripts/compile_authoring_yaml.py",
        "scripts/merge_cpcs_mx_observations.py",
        "scripts/validate_jsonl_stream.py",
        "scripts/validate_cpcs_mx_package.py",
        "examples/canonical_cpcs_mx_score.json",
        "examples/natural_walk.yaml",
        "examples/realistic_ugc_gesture.yaml",
        "examples/staged_combat_exchange.yaml",
        "examples/anime_superhuman_action.yaml",
        "prompts/TEXT_TO_CPCS_MX_AGENT_PROMPT.md",
        "prompts/CPCS_MX_VERIFIER_AGENT_PROMPT.md",
        "references/CPCS_MX_Reference_Index.json",
        "references/CPCS_MX_Source_Annotations.jsonl",
        "docs/AGENT_INGESTION_GUIDE.md",
        "docs/AGENT_WORKFLOW_RECIPES.md",
    ]
    return [f"missing required file: {rel}" for rel in required if not (package / rel).is_file()]


def check_markdown(paper: Path, source_ids: set[str]) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    text = paper.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        errors.append("paper front matter missing or unclosed")
    else:
        end = text.find("\n---\n", 4)
        try:
            meta = yaml.safe_load(text[4:end])
            if not isinstance(meta, dict):
                errors.append("paper front matter is not a mapping")
        except yaml.YAMLError as exc:
            errors.append(f"paper front matter parse error: {exc}")
    fence_lines = [line for line in text.splitlines() if line.lstrip().startswith("```")]
    if len(fence_lines) % 2:
        errors.append(f"unbalanced Markdown fences: {len(fence_lines)} fence lines")
    markers = RAG_MARKER_RE.findall(text)
    dup_markers = [m for m, c in Counter(markers).items() if c > 1]
    if dup_markers:
        errors.append(f"duplicate RAG markers: {dup_markers}")
    anchors = set(EXPLICIT_ANCHOR_RE.findall(text))
    toc_links = set(TOC_LINK_RE.findall(text[: text.find("<!-- RAG_CHUNK") if "<!-- RAG_CHUNK" in text else len(text)]))
    missing_anchors = sorted(toc_links - anchors)
    if missing_anchors:
        errors.append(f"TOC links without explicit anchors: {missing_anchors}")
    citations = set(SOURCE_RE.findall(text))
    missing_sources = sorted(citations - source_ids)
    if missing_sources:
        errors.append(f"paper citations not in source index: {missing_sources}")
    stats = {
        "line_count": len(text.splitlines()),
        "word_count": len(text.split()),
        "rag_marker_count": len(markers),
        "citation_source_count": len(citations),
        "toc_link_count": len(toc_links),
        "explicit_anchor_count": len(anchors),
    }
    return errors, stats


def check_references(package: Path) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    json_path = package / "references/CPCS_MX_Reference_Index.json"
    refs = load_json(json_path)
    if not isinstance(refs, list):
        return ["reference index JSON is not a list"], []
    ids = [r.get("id") for r in refs if isinstance(r, dict)]
    if len(ids) != len(set(ids)):
        errors.append("duplicate source IDs in reference index")
    expected = [f"S{i:03d}" for i in range(1, len(ids) + 1)]
    if ids != expected:
        errors.append("source IDs are not contiguous and ordered from S001")
    for idx, ref in enumerate(refs, start=1):
        if not isinstance(ref, dict):
            errors.append(f"reference {idx} is not an object")
            continue
        for field in ("id", "title", "authors", "year", "type", "tier", "status", "url"):
            if field not in ref or ref[field] in (None, ""):
                errors.append(f"reference {ref.get('id', idx)} missing {field}")
        url = str(ref.get("url", ""))
        if not url.startswith(("https://", "http://")):
            errors.append(f"reference {ref.get('id', idx)} has non-web URL: {url}")
    csv_path = package / "references/CPCS_MX_Reference_Index.csv"
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if len(rows) != len(refs):
            errors.append(f"reference CSV count {len(rows)} != JSON count {len(refs)}")
        elif [r.get("id") for r in rows] != ids:
            errors.append("reference CSV IDs differ from JSON IDs")

    annotations_path = package / "references/CPCS_MX_Source_Annotations.jsonl"
    if annotations_path.exists():
        annotation_ids: list[str] = []
        for line_no, line in enumerate(annotations_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{annotations_path.relative_to(package)}:{line_no}: {exc}")
                continue
            if not isinstance(item, dict):
                errors.append(f"{annotations_path.relative_to(package)}:{line_no}: record is not an object")
                continue
            source_id = item.get("source_id")
            annotation_ids.append(source_id)
            if source_id not in ids:
                errors.append(f"source annotation {source_id} is absent from reference index")
        if annotation_ids != ids:
            errors.append("source annotation IDs differ from ordered reference index IDs")
    return errors, refs


def check_data_files(package: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    stats = Counter()
    canonical_schema = load_json(package / "schemas/CPCS_MX_Schema.json")
    authoring_schema = load_json(package / "schemas/CPCS_MX_Authoring_Schema.json")
    observation_schema = load_json(package / "schemas/CPCS_MX_Observation_Record_Schema.json")
    rag_schema = load_json(package / "schemas/CPCS_MX_RAG_Record_Schema.json")

    for path in sorted(package.rglob("*.json")):
        try:
            obj = load_json(path)
            stats["json_files"] += 1
        except ValueError as exc:
            errors.append(str(exc))
            continue
        rel = path.relative_to(package).as_posix()
        if rel == "examples/canonical_cpcs_mx_score.json" or rel.startswith("examples/compiled/") and rel.endswith(".compiled.json"):
            errors.extend(validate_json(obj, canonical_schema, rel))
        if rel.startswith("schemas/"):
            try:
                Draft202012Validator.check_schema(obj)
            except Exception as exc:  # jsonschema raises several schema exceptions
                errors.append(f"invalid JSON Schema {rel}: {exc}")

    yaml_paths = sorted(list(package.rglob("*.yaml")) + list(package.rglob("*.yml")) + list(package.rglob("*.cff")))
    for path in yaml_paths:
        try:
            obj = yaml.safe_load(path.read_text(encoding="utf-8"))
            stats["yaml_files"] += 1
        except yaml.YAMLError as exc:
            errors.append(f"YAML parse error in {path.relative_to(package)}: {exc}")
            continue
        rel = path.relative_to(package).as_posix()
        if rel.startswith("examples/") and isinstance(obj, dict) and "cpcs_mx" in obj:
            errors.extend(validate_json(obj, authoring_schema, rel))

    for path in sorted(package.rglob("*.xml")):
        try:
            ET.parse(path)
            stats["xml_files"] += 1
        except ET.ParseError as exc:
            errors.append(f"XML parse error in {path.relative_to(package)}: {exc}")

    for path in sorted(package.rglob("*.py")):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            stats["python_files"] += 1
        except SyntaxError as exc:
            errors.append(f"Python compile error in {path.relative_to(package)}:{exc.lineno}: {exc.msg}")

    # Observation JSONL.
    for path in sorted((package / "examples/observations").glob("*.jsonl")):
        ids: set[str] = set()
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path.relative_to(package)}:{line_no}: {exc}")
                continue
            stats["observation_records"] += 1
            errors.extend(validate_json(obj, observation_schema, f"{path.relative_to(package)}:{line_no}"))
            rid = obj.get("record_id")
            if rid in ids:
                errors.append(f"duplicate observation record ID {rid} in {path.relative_to(package)}")
            ids.add(rid)

    # RAG JSONL.
    rag_path = package / "rag/CPCS_MX_RAG_Corpus.jsonl"
    rag_ids: set[str] = set()
    rag_counts = Counter()
    if rag_path.exists():
        for line_no, line in enumerate(rag_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{rag_path.relative_to(package)}:{line_no}: {exc}")
                continue
            stats["rag_records"] += 1
            rag_counts[obj.get("record_type", "missing")] += 1
            errors.extend(validate_json(obj, rag_schema, f"{rag_path.relative_to(package)}:{line_no}"))
            rid = obj.get("record_id")
            if rid in rag_ids:
                errors.append(f"duplicate RAG record ID {rid}")
            rag_ids.add(rid)
            content = obj.get("content", "")
            if hashlib.sha256(content.encode("utf-8")).hexdigest() != obj.get("sha256"):
                errors.append(f"RAG content hash mismatch for {rid}")
    stats["rag_counts_by_type"] = dict(sorted(rag_counts.items()))

    # Validate cross-style transform against its schema definition.
    transform_path = package / "examples/cross_style_transform.json"
    if transform_path.exists():
        transform = load_json(transform_path)
        transform_schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", **canonical_schema["$defs"]["styleTransform"]}
        transform_schema["$defs"] = canonical_schema["$defs"]
        errors.extend(validate_json(transform, transform_schema, "examples/cross_style_transform.json"))

    # External asset hashes in canonical example.
    score_path = package / "examples/canonical_cpcs_mx_score.json"
    if score_path.exists():
        score = load_json(score_path)
        for asset in score.get("assets", []):
            uri = asset.get("uri")
            expected = asset.get("sha256")
            if not uri or not expected or expected == "REPLACE_WITH_ACTUAL_HASH":
                continue
            asset_path = (score_path.parent / uri).resolve()
            if not asset_path.exists():
                errors.append(f"canonical example asset missing: {uri}")
            elif sha256_file(asset_path) != expected:
                errors.append(f"canonical example asset hash mismatch: {uri}")

    return errors, dict(stats)


def write_checksums(package: Path) -> int:
    files = [p for p in relative_files(package) if p.relative_to(package).as_posix() not in {"manifests/CPCS_MX_Package_Manifest.json"}]
    lines = [f"{sha256_file(path)}  {path.relative_to(package).as_posix()}" for path in files]
    (package / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--write-checksums", action="store_true")
    args = parser.parse_args()
    package = args.package.resolve()

    errors = check_required_files(package)
    ref_errors, refs = check_references(package)
    errors.extend(ref_errors)
    source_ids = {r["id"] for r in refs if isinstance(r, dict) and "id" in r}
    paper_errors, paper_stats = check_markdown(package / "paper/CPCS_MX_Hierarchical_Motion_Grammar_Research_Paper.md", source_ids)
    errors.extend(paper_errors)
    data_errors, data_stats = check_data_files(package)
    errors.extend(data_errors)

    file_count = len(relative_files(package))
    report = {
        "package": package.name,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "valid": not errors,
        "error_count": len(errors),
        "errors": errors,
        "statistics": {
            "file_count_excluding_checksums": file_count,
            "source_count": len(refs),
            "paper": paper_stats,
            "data": data_stats,
        },
    }

    if args.write_manifest:
        manifest_path = package / "manifests/CPCS_MX_Package_Manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.write_checksums:
        report["statistics"]["checksum_entry_count"] = write_checksums(package)
        if args.write_manifest:
            (package / "manifests/CPCS_MX_Package_Manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
