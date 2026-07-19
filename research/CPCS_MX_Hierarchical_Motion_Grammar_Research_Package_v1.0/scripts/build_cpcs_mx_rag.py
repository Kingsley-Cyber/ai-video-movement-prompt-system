#!/usr/bin/env python3
"""Build and validate the CPCS-MX RAG JSONL corpus."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator

MARKER_RE = re.compile(
    r'<!--\s*RAG_CHUNK\s+id="(?P<id>[^"]+)"\s+title="(?P<title>[^"]+)"\s+'
    r'concepts="(?P<concepts>[^"]*)"\s+evidence="(?P<evidence>[^"]*)"\s*-->'
)
SOURCE_RE = re.compile(r"\[(S\d{3})\]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
SUBHEADING_SPLIT_RE = re.compile(r"(?=^###\s+)", re.MULTILINE)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return value.strip("_") or "record"


def read_front_matter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("Unclosed Markdown front matter")
    meta = yaml.safe_load(text[4:end]) or {}
    if not isinstance(meta, dict):
        raise ValueError("Front matter must be a mapping")
    return meta, text[end + 5 :]


def make_record(
    *,
    record_id: str,
    record_type: str,
    document_id: str,
    title: str,
    content: str,
    parent_id: str | None = None,
    heading_path: list[str] | None = None,
    concepts: Iterable[str] = (),
    evidence_labels: Iterable[str] = (),
    source_ids: Iterable[str] = (),
    schema_fields: Iterable[str] = (),
    safety_scope: str = "research_and_virtual_animation",
    source_uri: str | None = None,
    metadata: dict[str, Any] | None = None,
    context_before: str = "",
    context_after: str = "",
) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "record_id": record_id,
        "record_type": record_type,
        "document_id": document_id,
        "parent_id": parent_id,
        "title": title,
        "heading_path": heading_path or [],
        "concepts": sorted({x.strip() for x in concepts if x and x.strip()}),
        "evidence_labels": sorted({x.strip() for x in evidence_labels if x and x.strip()}),
        "source_ids": sorted(set(source_ids)),
        "schema_fields": sorted({x.strip() for x in schema_fields if x and x.strip()}),
        "safety_scope": safety_scope,
        "content": content.strip(),
        "context_before": context_before.strip(),
        "context_after": context_after.strip(),
        "metadata": metadata or {},
        "sha256": sha256_text(content.strip()),
    }
    if source_uri is not None:
        rec["source_uri"] = source_uri
    return rec


def split_semantic_section(section: str, max_words: int = 1050) -> list[str]:
    """Split at H3 boundaries, preserving code fences and large examples intact."""
    words = section.split()
    if len(words) <= max_words:
        return [section.strip()]
    parts = [p for p in SUBHEADING_SPLIT_RE.split(section) if p.strip()]
    if len(parts) <= 1:
        return [section.strip()]
    groups: list[str] = []
    current = ""
    for part in parts:
        proposed = (current + "\n" + part).strip() if current else part.strip()
        # Never split within an H3 unit; oversized code examples remain intact.
        if current and len(proposed.split()) > max_words:
            groups.append(current.strip())
            current = part.strip()
        else:
            current = proposed
    if current:
        groups.append(current.strip())
    return groups


def build_paper_records(package: Path) -> list[dict[str, Any]]:
    paper_path = package / "paper" / "CPCS_MX_Hierarchical_Motion_Grammar_Research_Paper.md"
    raw = paper_path.read_text(encoding="utf-8")
    meta, _ = read_front_matter(raw)
    document_id = str(meta.get("document_id", "cpcs-mx-research-v1"))
    records: list[dict[str, Any]] = []
    abstract_match = re.search(r"## Abstract\n(.*?)(?=\n## )", raw, re.S)
    abstract = abstract_match.group(1).strip() if abstract_match else raw[:2500]
    records.append(make_record(
        record_id=f"document.{document_id}",
        record_type="document",
        document_id=document_id,
        title=str(meta.get("title", "CPCS-MX Research Paper")),
        content=abstract,
        concepts=meta.get("scope", []),
        evidence_labels=meta.get("status_labels", []),
        source_uri="paper/CPCS_MX_Hierarchical_Motion_Grammar_Research_Paper.md",
        metadata={"front_matter": meta},
    ))

    matches = list(MARKER_RE.finditer(raw))
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        section = raw[start:end].strip()
        concepts = [x.strip() for x in match.group("concepts").split(",") if x.strip()]
        evidence = [x.strip() for x in match.group("evidence").split(",") if x.strip()]
        subchunks = split_semantic_section(section)
        for subindex, chunk in enumerate(subchunks, start=1):
            headings = [m.group(2).strip() for m in HEADING_RE.finditer(chunk)]
            title = match.group("title")
            if len(subchunks) > 1 and headings:
                title = f"{title} — {headings[-1]}"
            rid = f"chunk.{match.group('id')}" + (f".{subindex:02d}" if len(subchunks) > 1 else "")
            before = subchunks[subindex - 2][-500:] if subindex > 1 else ""
            after = subchunks[subindex][:500] if subindex < len(subchunks) else ""
            records.append(make_record(
                record_id=rid,
                record_type="research_chunk",
                document_id=document_id,
                parent_id=f"document.{document_id}",
                title=title,
                content=chunk,
                heading_path=headings,
                concepts=concepts,
                evidence_labels=evidence,
                source_ids=SOURCE_RE.findall(chunk),
                safety_scope="research_virtual_animation_and_professionally_staged_screen_action",
                source_uri="paper/CPCS_MX_Hierarchical_Motion_Grammar_Research_Paper.md",
                metadata={"rag_marker_id": match.group("id"), "subchunk_index": subindex, "subchunk_count": len(subchunks)},
                context_before=before,
                context_after=after,
            ))
    return records


def build_source_records(package: Path, document_id: str) -> list[dict[str, Any]]:
    source_path = package / "references" / "CPCS_MX_Reference_Index.json"
    rows = json.loads(source_path.read_text(encoding="utf-8"))
    records = []
    for src in rows:
        sid = src["id"]
        content = "\n".join([
            f"Source ID: {sid}",
            f"Title: {src.get('title','')}",
            f"Authors or organization: {src.get('authors','')}",
            f"Year: {src.get('year','')}",
            f"Type: {src.get('type','')}",
            f"Tier: {src.get('tier','')}",
            f"Status: {src.get('status','')}",
            f"DOI: {src.get('doi','')}",
            f"URL: {src.get('url','')}",
            f"Cited in: {', '.join(x.get('chunk_id','') for x in src.get('cited_in', []))}",
        ])
        records.append(make_record(
            record_id=f"source.{sid}",
            record_type="source",
            document_id=document_id,
            parent_id=f"document.{document_id}",
            title=f"{sid}: {src.get('title','')}",
            content=content,
            concepts=list(src.get("concepts") or []) + [src.get("type", "source"), src.get("status", "")],
            evidence_labels=[src.get("status", "")],
            source_ids=[sid],
            source_uri=src.get("url"),
            metadata=src,
        ))
    return records


def build_schema_records(package: Path, document_id: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted((package / "schemas").glob("*.json")):
        obj = json.loads(path.read_text(encoding="utf-8"))
        title = obj.get("title", path.stem)
        top = {k: v for k, v in obj.items() if k != "$defs"}
        records.append(make_record(
            record_id=f"schema.{stable_slug(path.stem)}.root",
            record_type="schema_definition",
            document_id=document_id,
            parent_id=f"document.{document_id}",
            title=f"{title}: root contract",
            content=json.dumps(top, indent=2, ensure_ascii=False),
            concepts=["JSON Schema", path.stem, "validation"],
            evidence_labels=["STANDARD", "PROPOSED"],
            schema_fields=list((obj.get("properties") or {}).keys()),
            source_uri=str(path.relative_to(package)),
            metadata={"schema_id": obj.get("$id"), "draft": obj.get("$schema")},
        ))
        for name, definition in (obj.get("$defs") or {}).items():
            records.append(make_record(
                record_id=f"schema.{stable_slug(path.stem)}.def.{stable_slug(name)}",
                record_type="schema_definition",
                document_id=document_id,
                parent_id=f"schema.{stable_slug(path.stem)}.root",
                title=f"{title}: {name}",
                content=json.dumps(definition, indent=2, ensure_ascii=False),
                concepts=["JSON Schema", path.stem, name],
                evidence_labels=["PROPOSED", "OPERATIONALIZATION"],
                schema_fields=[name],
                source_uri=str(path.relative_to(package)),
                metadata={"json_pointer": f"#/$defs/{name}"},
            ))
    return records


def text_file_record(path: Path, package: Path, document_id: str, record_type: str, concepts: list[str]) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    return make_record(
        record_id=f"{record_type}.{stable_slug(str(path.relative_to(package)))}",
        record_type=record_type,
        document_id=document_id,
        parent_id=f"document.{document_id}",
        title=path.stem.replace("_", " "),
        content=content,
        concepts=concepts,
        evidence_labels=["PROPOSED", "OPERATIONALIZATION"],
        source_ids=SOURCE_RE.findall(content),
        source_uri=str(path.relative_to(package)),
        metadata={"extension": path.suffix.lower()},
    )


def build_package_records(package: Path, document_id: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for name in ("README.md", "NOTICE.md", "CHANGELOG.md"):
        path = package / name
        if path.is_file():
            records.append(text_file_record(path, package, document_id, "package_document", ["package documentation", path.stem]))
    for path in sorted((package / "examples").rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".yaml", ".yml", ".md"}:
            continue
        records.append(text_file_record(path, package, document_id, "worked_example", ["CPCS-MX example", path.stem]))
    for path in sorted((package / "profiles").rglob("*.yaml")):
        records.append(text_file_record(path, package, document_id, "worked_example", ["CPCS-MX profile", path.parent.name, path.stem]))
    for path in sorted((package / "prompts").glob("*")):
        if path.suffix.lower() in {".md", ".xml", ".json", ".yaml"}:
            records.append(text_file_record(path, package, document_id, "prompt_template", ["agent prompt", path.stem]))
    for path in sorted((package / "docs").glob("*.md")):
        rec_type = "field_guide" if "FIELD_GUIDE" in path.name else "package_document"
        records.append(text_file_record(path, package, document_id, rec_type, ["documentation", path.stem]))
    return records


def validate_records(records: list[dict[str, Any]], schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    ids: set[str] = set()
    for index, record in enumerate(records, start=1):
        if record["record_id"] in ids:
            raise ValueError(f"Duplicate record_id: {record['record_id']}")
        ids.add(record["record_id"])
        expected = sha256_text(record["content"])
        if expected != record["sha256"]:
            raise ValueError(f"Hash mismatch for {record['record_id']}")
        errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
        if errors:
            joined = "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:8])
            raise ValueError(f"RAG record {index} {record['record_id']} failed schema: {joined}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    package = args.package.resolve()
    output = args.output or package / "rag" / "CPCS_MX_RAG_Corpus.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)

    paper_records = build_paper_records(package)
    document_id = paper_records[0]["document_id"]
    records = paper_records
    records += build_schema_records(package, document_id)
    records += build_package_records(package, document_id)
    records += build_source_records(package, document_id)
    validate_records(records, package / "schemas" / "CPCS_MX_RAG_Record_Schema.json")

    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

    counts = Counter(record["record_type"] for record in records)
    summary = {
        "output": str(output),
        "record_count": len(records),
        "counts_by_type": dict(sorted(counts.items())),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
