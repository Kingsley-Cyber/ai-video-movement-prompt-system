"""Safely convert authorized folders or retrieved passages into reviewable candidate bundles."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Iterable

import yaml
from defusedxml import ElementTree as DefusedElementTree

from .authority import authority_reader
from .ingest import ingest_distillation_batch
from .temporal import is_visible
from .validate import (
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    canonical_json_bytes,
    read_jsonl,
    sha256_value,
    validate_instance,
)

POLICY_VERSION = "cpcs-source-extract/1.2"
PARSER_VERSION = "cpcs-safe-document-parser/1.1"
STRUCTURAL_EXTRACTOR_VERSION = "cpcs-structural-extractor/1.0"
CONTENT_ADDRESSED_TIME = "2000-01-01T00:00:00Z"
ALLOWED_OUTPUTS = [
    "concept",
    "edge",
    "intent",
    "mapping",
    "rule",
    "claim",
    "equation",
    "method",
    "mechanism",
]
SUPPORTED_MEDIA = {
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".xml": "application/xml",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
}
DEFAULT_CONFIGURATION = {
    "policy_version": POLICY_VERSION,
    "max_file_bytes": 10_000_000,
    "max_total_bytes": 100_000_000,
    "max_tree_nodes": 100_000,
    "max_tree_depth": 64,
    "max_chunk_chars": 6_000,
    "max_passages_per_packet": 8,
    "max_packet_chars": 24_000,
    "max_semantic_chunks": 96,
    "max_structural_candidates": 256,
}
LAYER_TERMS = {
    "audio": {"audio", "sound", "dialogue", "music", "voice"},
    "camera": {"camera", "frame", "lens", "shot", "focus", "composition"},
    "editing": {"edit", "cut", "sequence", "montage", "transition"},
    "face": {"face", "facial", "facs", "gaze", "expression"},
    "lighting": {"light", "lighting", "shadow", "exposure", "color"},
    "marketing": {"product", "brand", "claim", "cta", "advertising"},
    "motion": {"motion", "movement", "laban", "gesture", "path", "action"},
    "performance": {"acting", "actor", "performance", "emotion", "subtext"},
    "style": {"style", "anime", "cinematic", "realism", "visual"},
}


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _short_hash(value: Any, length: int = 24) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()[:length]


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 1
    }


def _slug(value: str, maximum: int = 42) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return (slug or "source_concept")[:maximum].rstrip("_")


def _configuration(overrides: dict[str, int] | None = None) -> dict[str, Any]:
    configuration = copy.deepcopy(DEFAULT_CONFIGURATION)
    configuration.update(overrides or {})
    if configuration["max_chunk_chars"] > configuration["max_packet_chars"]:
        raise ValidationFailure("max_chunk_chars cannot exceed max_packet_chars")
    if configuration["max_passages_per_packet"] > 12:
        raise ValidationFailure("semantic packets cannot exceed 12 passages")
    return configuration


def _section(
    source_id: str,
    relative_path: str,
    locator: str,
    heading_path: Iterable[str],
    kind: str,
    text: str,
    line_start: int | None,
    line_end: int | None,
) -> dict[str, Any]:
    normalized = text.strip()
    return {
        "section_id": "section_" + _short_hash(
            {"source_id": source_id, "relative_path": relative_path, "locator": locator}
        ),
        "locator": locator,
        "heading_path": list(heading_path),
        "kind": kind,
        "text": normalized,
        "line_start": line_start,
        "line_end": line_end,
    }


def _decode_text(raw: bytes, relative_path: str) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationFailure(f"{relative_path}: source must be valid UTF-8") from exc


def _markdown_sections(
    raw: bytes,
    source_id: str,
    relative_path: str,
    configuration: dict[str, Any],
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    text = _decode_text(raw, relative_path)
    lines = text.splitlines()
    metadata: dict[str, Any] = {}
    sections: list[dict[str, Any]] = []
    index = 0
    if lines and lines[0].strip() == "---":
        closing = next(
            (position for position in range(1, len(lines)) if lines[position].strip() == "---"),
            None,
        )
        if closing is None:
            raise ValidationFailure(f"{relative_path}: unclosed Markdown front matter")
        body = "\n".join(lines[1:closing])
        try:
            loaded = yaml.safe_load(body) or {}
        except yaml.YAMLError as exc:
            raise ValidationFailure(f"{relative_path}: unsafe or invalid front matter") from exc
        if not isinstance(loaded, dict):
            raise ValidationFailure(f"{relative_path}: front matter must be an object")
        _validate_tree(loaded, relative_path, configuration)
        metadata = loaded
        sections.append(
            _section(
                source_id,
                relative_path,
                f"md:lines-1-{closing + 1}",
                [],
                "front_matter",
                body or "{}",
                1,
                closing + 1,
            )
        )
        index = closing + 1
    headings: list[str] = []
    first_heading: str | None = None

    def classify(line: str) -> str:
        if re.match(r"^\s*(?:[-*+] |\d+[.)] )", line):
            return "list"
        if "|" in line:
            return "table"
        if re.match(r"^\s*(?:>\s|\[[^]]+\]:)", line):
            return "citation"
        return "paragraph"

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            headings = headings[: level - 1]
            while len(headings) < level - 1:
                headings.append("")
            headings.append(title)
            if first_heading is None:
                first_heading = title
            sections.append(
                _section(
                    source_id,
                    relative_path,
                    f"md:line-{index + 1}",
                    headings,
                    "heading",
                    title,
                    index + 1,
                    index + 1,
                )
            )
            index += 1
            continue
        equation_start = (
            line.strip().startswith("$$")
            or line.strip() == r"\["
            or bool(re.match(r"^\s*\\begin\{(?:equation\*?|align\*?|gather\*?)\}", line))
        )
        if equation_start:
            start = index
            stripped = line.strip()
            if stripped.startswith("$$"):
                single_line = len(stripped) > 4 and stripped.endswith("$$")
                terminator = lambda value: value.strip().endswith("$$")
            elif stripped == r"\[":
                single_line = False
                terminator = lambda value: value.strip() == r"\]"
            else:
                environment = re.search(r"\\begin\{([^}]+)\}", line).group(1)
                single_line = False
                terminator = lambda value: bool(
                    re.search(rf"\\end\{{{re.escape(environment)}\}}", value)
                )
            index += 1
            while index < len(lines) and not single_line and not terminator(lines[index]):
                index += 1
            if index < len(lines) and not single_line:
                index += 1
            sections.append(
                _section(
                    source_id,
                    relative_path,
                    f"md:lines-{start + 1}-{index}",
                    headings,
                    "equation",
                    "\n".join(lines[start:index]),
                    start + 1,
                    index,
                )
            )
            continue
        fence = re.match(r"^\s*(```+|~~~+)", line)
        if fence:
            start = index
            marker = fence.group(1)[0]
            index += 1
            while index < len(lines) and not re.match(
                rf"^\s*{re.escape(marker)}{{3,}}", lines[index]
            ):
                index += 1
            if index < len(lines):
                index += 1
            sections.append(
                _section(
                    source_id,
                    relative_path,
                    f"md:lines-{start + 1}-{index}",
                    headings,
                    "code",
                    "\n".join(lines[start:index]),
                    start + 1,
                    index,
                )
            )
            continue
        kind = classify(line)
        start = index
        block = [line]
        index += 1
        while index < len(lines):
            current = lines[index]
            if not current.strip() or re.match(r"^#{1,6}\s+", current) or re.match(
                r"^\s*(```+|~~~+)", current
            ):
                break
            if classify(current) != kind and kind != "paragraph":
                break
            if kind == "paragraph" and classify(current) != "paragraph":
                break
            block.append(current)
            index += 1
        sections.append(
            _section(
                source_id,
                relative_path,
                f"md:lines-{start + 1}-{index}",
                headings,
                kind,
                "\n".join(block),
                start + 1,
                index,
            )
        )
    title = str(metadata.get("title") or first_heading or Path(relative_path).stem)
    return title, metadata, sections


def _text_sections(
    raw: bytes, source_id: str, relative_path: str
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    lines = _decode_text(raw, relative_path).splitlines()
    sections: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        while index < len(lines) and not lines[index].strip():
            index += 1
        if index >= len(lines):
            break
        start = index
        block = []
        while index < len(lines) and lines[index].strip():
            block.append(lines[index])
            index += 1
        sections.append(
            _section(
                source_id,
                relative_path,
                f"text:lines-{start + 1}-{index}",
                [],
                "paragraph",
                "\n".join(block),
                start + 1,
                index,
            )
        )
    return Path(relative_path).stem, {}, sections


def _validate_tree(value: Any, label: str, configuration: dict[str, Any]) -> None:
    stack = [(value, 0)]
    seen: set[int] = set()
    nodes = 0
    while stack:
        node, depth = stack.pop()
        nodes += 1
        if nodes > configuration["max_tree_nodes"]:
            raise ValidationFailure(f"{label}: structured document exceeds node limit")
        if depth > configuration["max_tree_depth"]:
            raise ValidationFailure(f"{label}: structured document exceeds depth limit")
        if isinstance(node, (dict, list)):
            identity = id(node)
            if identity in seen:
                raise ValidationFailure(f"{label}: aliases or cyclic structures are not allowed")
            seen.add(identity)
            children = node.values() if isinstance(node, dict) else node
            for child in children:
                stack.append((child, depth + 1))
        elif not isinstance(node, (str, int, float, bool, type(None))):
            raise ValidationFailure(f"{label}: unsupported structured value {type(node).__name__}")


def _pointer_part(value: Any) -> str:
    return str(value).replace("~", "~0").replace("/", "~1")


def _structured_sections(
    value: Any,
    source_id: str,
    relative_path: str,
    prefix: str,
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    stack: list[tuple[str, list[str], Any]] = [("", [], value)]
    while stack:
        pointer, path, node = stack.pop()
        if isinstance(node, dict) and node:
            for key in sorted(node, key=str, reverse=True):
                part = _pointer_part(key)
                stack.append((f"{pointer}/{part}", [*path, str(key)], node[key]))
            continue
        if isinstance(node, list) and node:
            for index in range(len(node) - 1, -1, -1):
                stack.append((f"{pointer}/{index}", [*path, str(index)], node[index]))
            continue
        text = json.dumps(node, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        locator = f"{prefix}:{pointer or '/'}"
        sections.append(
            _section(
                source_id,
                relative_path,
                locator,
                path,
                "structured_value",
                text,
                None,
                None,
            )
        )
    return sections


def _json_sections(
    raw: bytes,
    source_id: str,
    relative_path: str,
    configuration: dict[str, Any],
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    try:
        value = json.loads(_decode_text(raw, relative_path))
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"{relative_path}: invalid JSON at line {exc.lineno}") from exc
    _validate_tree(value, relative_path, configuration)
    return Path(relative_path).stem, {}, _structured_sections(
        value, source_id, relative_path, "json"
    )


def _jsonl_sections(
    raw: bytes,
    source_id: str,
    relative_path: str,
    configuration: dict[str, Any],
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    lines = _decode_text(raw, relative_path).splitlines()
    sections = []
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        if len(line) > configuration["max_chunk_chars"] * 4:
            raise ValidationFailure(f"{relative_path}:{line_number}: JSONL record exceeds line limit")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationFailure(f"{relative_path}:{line_number}: invalid JSONL record") from exc
        _validate_tree(value, f"{relative_path}:{line_number}", configuration)
        sections.append(
            _section(
                source_id,
                relative_path,
                f"jsonl:/line/{line_number}",
                [str(line_number)],
                "jsonl_record",
                json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
                line_number,
                line_number,
            )
        )
    return Path(relative_path).stem, {}, sections


def _yaml_sections(
    raw: bytes,
    source_id: str,
    relative_path: str,
    configuration: dict[str, Any],
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    try:
        value = yaml.safe_load(_decode_text(raw, relative_path))
    except yaml.YAMLError as exc:
        raise ValidationFailure(f"{relative_path}: unsafe or invalid YAML") from exc
    _validate_tree(value, relative_path, configuration)
    return Path(relative_path).stem, {}, _structured_sections(
        value, source_id, relative_path, "yaml"
    )


def _xml_sections(
    raw: bytes,
    source_id: str,
    relative_path: str,
    configuration: dict[str, Any],
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    if re.search(br"<!\s*(?:DOCTYPE|ENTITY)", raw, flags=re.IGNORECASE):
        raise ValidationFailure(f"{relative_path}: DTD and entity declarations are forbidden")
    try:
        root = DefusedElementTree.fromstring(raw)
    except Exception as exc:
        raise ValidationFailure(f"{relative_path}: unsafe or invalid XML") from exc
    sections: list[dict[str, Any]] = []
    stack: list[tuple[Any, str, list[str], int]] = [(root, f"/{root.tag}[1]", [root.tag], 0)]
    nodes = 0
    while stack:
        element, locator, heading, depth = stack.pop()
        nodes += 1
        if nodes > configuration["max_tree_nodes"]:
            raise ValidationFailure(f"{relative_path}: XML exceeds node limit")
        if depth > configuration["max_tree_depth"]:
            raise ValidationFailure(f"{relative_path}: XML exceeds depth limit")
        direct_text = (element.text or "").strip()
        payload = {
            "tag": element.tag,
            "attributes": {key: element.attrib[key] for key in sorted(element.attrib)},
            "text": direct_text,
        }
        sections.append(
            _section(
                source_id,
                relative_path,
                "xml:" + locator,
                heading,
                "xml_element",
                json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
                None,
                None,
            )
        )
        children = list(element)
        counts: dict[str, int] = {}
        indexed: list[tuple[Any, int]] = []
        for child in children:
            counts[child.tag] = counts.get(child.tag, 0) + 1
            indexed.append((child, counts[child.tag]))
        for child, ordinal in reversed(indexed):
            stack.append(
                (child, f"{locator}/{child.tag}[{ordinal}]", [*heading, child.tag], depth + 1)
            )
    return str(root.tag), {}, sections


def _parse_file(
    raw: bytes,
    extension: str,
    source_id: str,
    relative_path: str,
    configuration: dict[str, Any],
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    if extension == ".md":
        return _markdown_sections(raw, source_id, relative_path, configuration)
    if extension == ".txt":
        return _text_sections(raw, source_id, relative_path)
    if extension == ".json":
        return _json_sections(raw, source_id, relative_path, configuration)
    if extension == ".jsonl":
        return _jsonl_sections(raw, source_id, relative_path, configuration)
    if extension in {".yaml", ".yml"}:
        return _yaml_sections(raw, source_id, relative_path, configuration)
    if extension == ".xml":
        return _xml_sections(raw, source_id, relative_path, configuration)
    raise ValidationFailure(f"unsupported source format: {extension}")


def _folder_sources(
    folder: Path,
    rights_basis: str,
    configuration: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if folder.is_symlink():
        raise ValidationFailure("source folder cannot be a symlink")
    root = folder.resolve()
    if not root.is_dir():
        raise ValidationFailure(f"source folder does not exist: {folder}")
    inventory: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    total_bytes = 0
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        directory_names.sort()
        file_names.sort()
        current_path = Path(current)
        for name in directory_names:
            if (current_path / name).is_symlink():
                raise ValidationFailure(f"symlink directory is forbidden: {(current_path / name).relative_to(root)}")
        for name in file_names:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise ValidationFailure(f"symlink file is forbidden: {relative}")
            if not stat.S_ISREG(path.lstat().st_mode):
                raise ValidationFailure(f"non-regular source is forbidden: {relative}")
            resolved = path.resolve()
            if root != resolved and root not in resolved.parents:
                raise ValidationFailure(f"source path escapes authorized folder: {relative}")
            extension = path.suffix.lower()
            size = path.stat().st_size
            if extension not in SUPPORTED_MEDIA:
                inventory.append(
                    {
                        "relative_path": relative,
                        "extension": extension,
                        "status": "unsupported",
                        "byte_size": size,
                        "byte_hash": None,
                    }
                )
                continue
            if size > configuration["max_file_bytes"]:
                raise ValidationFailure(f"{relative}: source exceeds max_file_bytes")
            raw = path.read_bytes()
            if len(raw) > configuration["max_file_bytes"]:
                raise ValidationFailure(f"{relative}: source exceeds max_file_bytes")
            byte_hash = _sha256_bytes(raw)
            total_bytes += len(raw)
            if total_bytes > configuration["max_total_bytes"]:
                raise ValidationFailure("authorized folder exceeds max_total_bytes")
            source_id = "src_sha256_" + byte_hash[7:]
            title, metadata, sections = _parse_file(
                raw, extension, source_id, relative, configuration
            )
            if not sections:
                raise ValidationFailure(f"{relative}: parsed source contains no addressable sections")
            inventory.append(
                {
                    "relative_path": relative,
                    "extension": extension,
                    "status": "parsed",
                    "byte_size": len(raw),
                    "byte_hash": byte_hash,
                }
            )
            sources.append(
                {
                    "source_id": source_id,
                    "source_ref": "file:" + relative,
                    "relative_path": relative,
                    "media_type": SUPPORTED_MEDIA[extension],
                    "byte_hash": byte_hash,
                    "title": title,
                    "metadata": metadata,
                    "rights_basis": rights_basis,
                    "sections": sections,
                }
            )
    if not sources:
        raise ValidationFailure("authorized folder contains no supported non-empty sources")
    return sorted(inventory, key=lambda row: row["relative_path"]), sorted(
        sources, key=lambda row: row["relative_path"]
    )


def _passage_sources(
    envelope: dict[str, Any], configuration: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    seen_locators: set[tuple[str, str]] = set()
    total_bytes = 0
    for passage in envelope["passages"]:
        passage_bytes = passage["text"].encode("utf-8")
        if len(passage_bytes) > configuration["max_file_bytes"]:
            raise ValidationFailure(
                f"retrieved passage exceeds max_file_bytes: {passage['source_id']}#{passage['locator']}"
            )
        total_bytes += len(passage_bytes)
        if total_bytes > configuration["max_total_bytes"]:
            raise ValidationFailure("retrieved passages exceed max_total_bytes")
        address = (passage["source_id"], passage["locator"])
        if address in seen_locators:
            raise ValidationFailure(
                f"retrieved passage locator repeats: {passage['source_id']}#{passage['locator']}"
            )
        seen_locators.add(address)
        actual = _sha256_bytes(passage_bytes)
        if actual != passage["content_hash"]:
            raise ValidationFailure(
                f"retrieved passage hash mismatch: {passage['source_id']}#{passage['locator']}"
            )
        groups.setdefault(passage["source_id"], []).append(copy.deepcopy(passage))
    inventory = []
    sources = []
    for external_id in sorted(groups):
        rows = sorted(groups[external_id], key=lambda row: (row["locator"], row["content_hash"]))
        aggregate = canonical_json_bytes(rows)
        byte_hash = _sha256_bytes(aggregate)
        source_id = "src_sha256_" + byte_hash[7:]
        relative = f"polymath/{_short_hash(external_id)}.txt"
        sections = [
            _section(
                source_id,
                relative,
                "polymath:" + row["locator"],
                [row["title"]],
                "retrieved_passage",
                row["text"],
                None,
                None,
            )
            for row in rows
        ]
        inventory.append(
            {
                "relative_path": relative,
                "extension": ".txt",
                "status": "parsed",
                "byte_size": sum(len(row["text"].encode("utf-8")) for row in rows),
                "byte_hash": byte_hash,
            }
        )
        sources.append(
            {
                "source_id": source_id,
                "source_ref": external_id,
                "relative_path": relative,
                "media_type": "text/plain",
                "byte_hash": byte_hash,
                "title": rows[0]["title"],
                "metadata": {"retrieval": envelope["retrieval"]},
                "rights_basis": envelope["rights_basis"],
                "sections": sections,
            }
        )
    return inventory, sources


def _split_section(text: str, maximum: int) -> list[tuple[int, int, str]]:
    if not text:
        return []
    parts = []
    start = 0
    while start < len(text):
        end = min(len(text), start + maximum)
        if end < len(text):
            floor = start + maximum // 2
            boundary = max(text.rfind("\n", floor, end), text.rfind(" ", floor, end))
            if boundary > start:
                end = boundary
        segment = text[start:end]
        leading = len(segment) - len(segment.lstrip())
        trailing = len(segment.rstrip())
        actual_start = start + leading
        actual_end = start + trailing
        if actual_end > actual_start:
            parts.append((actual_start, actual_end, text[actual_start:actual_end]))
        start = end if end > start else start + maximum
    return parts


def _build_chunks(
    sources: list[dict[str, Any]], configuration: dict[str, Any]
) -> list[dict[str, Any]]:
    chunks = []
    for source in sources:
        for section in source["sections"]:
            for start, end, text in _split_section(
                section["text"], configuration["max_chunk_chars"]
            ):
                identity = {
                    "source_id": source["source_id"],
                    "relative_path": source["relative_path"],
                    "section_id": section["section_id"],
                    "start": start,
                    "end": end,
                    "text": text,
                }
                chunks.append(
                    {
                        "chunk_id": "chunk_" + _short_hash(identity),
                        "section_id": section["section_id"],
                        "source_id": source["source_id"],
                        "source_ref": source["source_ref"],
                        "relative_path": source["relative_path"],
                        "locator": f"{section['locator']}#chars={start}-{end}",
                        "heading_path": section["heading_path"],
                        "kind": section["kind"],
                        "line_start": section["line_start"],
                        "line_end": section["line_end"],
                        "char_start": start,
                        "char_end": end,
                        "text": text,
                        "content_sha256": _sha256_bytes(text.encode("utf-8")),
                    }
                )
    return sorted(chunks, key=lambda row: (row["relative_path"], row["locator"], row["chunk_id"]))


def _infer_layer(text: str) -> str:
    tokens = _tokens(text)
    scored = [
        (len(tokens & terms), layer)
        for layer, terms in LAYER_TERMS.items()
    ]
    score, layer = max(scored, key=lambda row: (row[0], row[1]))
    return layer if score else "research"


def _candidate_name(section: dict[str, Any], body: str, source_title: str) -> str:
    if section["kind"] == "heading":
        return section["text"][:120]
    if section["heading_path"]:
        return section["heading_path"][-1][:120]
    definition = re.match(
        r"^\s*(?:\*\*)?([A-Z][A-Za-z0-9 /_-]{2,80})(?:\*\*)?\s*[:—-]\s+",
        body,
    )
    if definition:
        return definition.group(1).strip()
    sentence = re.split(r"(?<=[.!?])\s+", body.strip(), maxsplit=1)[0]
    return (sentence[:100].strip(" .:;-") or source_title)[:120]


def _structural_candidates(
    sources: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    created_by: str,
    created_at: str,
    configuration: dict[str, Any],
) -> list[dict[str, Any]]:
    chunks_by_section: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        chunks_by_section.setdefault(chunk["section_id"], []).append(chunk)
    candidates = []
    seen_sections: set[str] = set()
    seen_heading_paths: set[tuple[str, tuple[str, ...]]] = set()
    for source in sources:
        sections = source["sections"]
        for index, section in enumerate(sections):
            if len(candidates) >= configuration["max_structural_candidates"]:
                break
            evidence_section = section
            if section["kind"] == "heading":
                evidence_section = next(
                    (
                        row
                        for row in sections[index + 1 :]
                        if row["kind"] not in {"heading", "front_matter", "code"}
                        and row["heading_path"][: len(section["heading_path"])]
                        == section["heading_path"]
                        and len(row["text"]) >= 40
                    ),
                    section,
                )
            elif section["kind"] in {"front_matter", "code", "table", "equation", "citation"}:
                continue
            if evidence_section["section_id"] in seen_sections:
                continue
            heading_key = (source["relative_path"], tuple(evidence_section["heading_path"]))
            if evidence_section["heading_path"] and heading_key in seen_heading_paths:
                continue
            section_chunks = chunks_by_section.get(evidence_section["section_id"], [])
            if not section_chunks:
                continue
            body = " ".join(chunk["text"] for chunk in section_chunks).strip()
            if len(body) < 40 and section["kind"] != "heading":
                continue
            name = _candidate_name(section, body, source["title"])
            evidence = section_chunks[0]
            suggested_id = (
                f"c_ingest_{_slug(name)}_"
                + _short_hash(
                    {"source_id": source["source_id"], "section": evidence_section["section_id"]},
                    8,
                )
            )
            record = {
                "kind": "research_concept",
                "name": name,
                "what": body[:1_000],
                "use_when": f"When research about {name.lower()} is relevant to video intent or direction.",
                "nl_triggers": [
                    name.lower(),
                    f"how to use {name.lower()}",
                    f"{name.lower()} for video direction",
                ],
                "status": "ingested",
                "evidence": [],
                "source": [f"{source['source_ref']}#{evidence['locator']}"],
                "layer": _infer_layer(name + " " + body),
            }
            candidate_id = "candidate_structural_" + _short_hash(
                {"suggested_id": suggested_id, "record": record, "chunk": evidence["chunk_id"]}
            )
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "proposal_type": "concept",
                    "suggested_id": suggested_id,
                    "proposed_record": record,
                    "source_evidence": [
                        {
                            "source_id": evidence["source_ref"],
                            "locator": evidence["locator"],
                            "claim": f"The source defines or develops {name}.",
                            "content_sha256": evidence["content_sha256"],
                        }
                    ],
                    "created_by": created_by,
                    "created_at": created_at,
                }
            )
            seen_sections.add(evidence_section["section_id"])
            if evidence_section["heading_path"]:
                seen_heading_paths.add(heading_key)
    if not candidates:
        first_source = sources[0]
        first_chunk = chunks[0]
        name = first_source["title"][:120]
        record = {
            "kind": "research_document",
            "name": name,
            "what": first_chunk["text"][:1_000],
            "use_when": f"When research from {name.lower()} is relevant to video direction.",
            "nl_triggers": [name.lower(), f"use {name.lower()}", f"{name.lower()} research"],
            "status": "ingested",
            "evidence": [],
            "source": [f"{first_source['source_ref']}#{first_chunk['locator']}"],
            "layer": _infer_layer(first_chunk["text"]),
        }
        suggested_id = f"c_ingest_{_slug(name)}_{_short_hash(first_chunk['chunk_id'], 8)}"
        candidates.append(
            {
                "candidate_id": "candidate_structural_" + _short_hash(record),
                "proposal_type": "concept",
                "suggested_id": suggested_id,
                "proposed_record": record,
                "source_evidence": [
                    {
                        "source_id": first_chunk["source_ref"],
                        "locator": first_chunk["locator"],
                        "claim": f"The source develops {name}.",
                        "content_sha256": first_chunk["content_sha256"],
                    }
                ],
                "created_by": created_by,
                "created_at": created_at,
            }
        )
    return sorted(candidates, key=lambda row: row["candidate_id"])


def _semantic_packets(
    chunks: list[dict[str, Any]],
    research_goal: str,
    configuration: dict[str, Any],
    root: Path,
) -> tuple[list[dict[str, Any]], set[str]]:
    goal_tokens = _tokens(research_goal)
    ranked = []
    for chunk in chunks:
        overlap = len(goal_tokens & _tokens(" ".join(chunk["heading_path"]) + " " + chunk["text"]))
        bonus = {
            "equation": 3,
            "table": 2,
            "code": 2,
            "heading": 1,
            "paragraph": 1,
            "retrieved_passage": 1,
        }.get(chunk["kind"], 0)
        ranked.append((overlap, bonus, chunk))
    relevant = [row for row in ranked if row[0] > 0]
    if relevant:
        relevant_heading_paths = {
            (row[2]["relative_path"], tuple(row[2]["heading_path"]))
            for row in relevant
            if row[2]["heading_path"]
        }
        relevant = [
            row
            for row in ranked
            if row[0] > 0
            or (
                row[2]["heading_path"]
                and (row[2]["relative_path"], tuple(row[2]["heading_path"]))
                in relevant_heading_paths
            )
        ]
    if not relevant:
        relevant = ranked[: configuration["max_passages_per_packet"]]
    selected = [
        row[2]
        for row in sorted(
            relevant,
            key=lambda row: (-row[0], -row[1], row[2]["relative_path"], row[2]["locator"]),
        )[: configuration["max_semantic_chunks"]]
    ]
    packets = []
    goal_terms = _tokens(research_goal)
    existing_concepts = []
    for concept in read_jsonl(root / "lab" / "concepts.jsonl"):
        if concept["status"] == "deprecated" or not is_visible(concept):
            continue
        searchable = " ".join(
            str(concept.get(key, ""))
            for key in ("name", "what", "use_when", "nl_triggers", "layer")
        )
        overlap = len(goal_terms & _tokens(searchable))
        if overlap:
            existing_concepts.append(
                (
                    overlap,
                    {
                        "id": concept["id"],
                        "name": concept["name"],
                        "layer": concept["layer"],
                        "status": concept["status"],
                    },
                )
            )
    concept_context = [
        row
        for _, row in sorted(
            existing_concepts, key=lambda item: (-item[0], item[1]["id"])
        )[:12]
    ]
    current: list[dict[str, Any]] = []
    current_chars = 0

    def finish() -> None:
        nonlocal current, current_chars
        if not current:
            return
        passages = [
            {
                "chunk_id": row["chunk_id"],
                "source_id": row["source_id"],
                "locator": row["locator"],
                "content_sha256": row["content_sha256"],
                "text": row["text"],
            }
            for row in current
        ]
        core = {
            "research_goal": research_goal,
            "existing_concepts": concept_context,
            "allowed_outputs": ALLOWED_OUTPUTS,
            "passages": passages,
        }
        packets.append(
            {
                "packet_id": "packet_" + _short_hash(core),
                "research_goal": research_goal,
                "existing_concepts": concept_context,
                "allowed_outputs": ALLOWED_OUTPUTS,
                "passage_chars": current_chars,
                "passages": passages,
            }
        )
        current = []
        current_chars = 0

    for chunk in selected:
        size = len(chunk["text"])
        if size > configuration["max_packet_chars"]:
            raise ValidationFailure(f"chunk exceeds semantic packet budget: {chunk['chunk_id']}")
        if current and (
            len(current) >= configuration["max_passages_per_packet"]
            or current_chars + size > configuration["max_packet_chars"]
        ):
            finish()
        current.append(chunk)
        current_chars += size
    finish()
    return packets, {row["chunk_id"] for row in selected}


def _semantic_candidates(
    response: dict[str, Any] | None,
    packets: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    created_by: str,
    created_at: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    structural_extractor = {
        "agent": "cpcs-source-extract",
        "model": "deterministic-structural-rules",
        "prompt_hash": sha256_value(
            {"policy": POLICY_VERSION, "extractor": STRUCTURAL_EXTRACTOR_VERSION}
        ),
    }
    if response is None:
        return [], structural_extractor
    validate_instance("semantic_extraction_response", response)
    packet_index = {row["packet_id"]: row for row in packets}
    chunk_index = {row["chunk_id"]: row for row in chunks}
    seen_results: set[str] = set()
    seen_keys: set[tuple[str, str]] = set()
    candidates = []
    for result in response["packet_results"]:
        packet_id = result["packet_id"]
        if packet_id in seen_results:
            raise ValidationFailure(f"semantic response repeats packet: {packet_id}")
        seen_results.add(packet_id)
        packet = packet_index.get(packet_id)
        if packet is None:
            raise ValidationFailure(f"semantic response references unknown packet: {packet_id}")
        allowed_chunks = {row["chunk_id"] for row in packet["passages"]}
        for proposal in result["candidates"]:
            key = (packet_id, proposal["candidate_key"])
            if key in seen_keys:
                raise ValidationFailure(f"semantic candidate key repeats: {key}")
            seen_keys.add(key)
            evidence = []
            for evidence_ref in proposal["evidence_refs"]:
                chunk_id = evidence_ref["chunk_id"]
                if chunk_id not in allowed_chunks:
                    raise ValidationFailure(
                        f"semantic evidence {chunk_id} is outside packet {packet_id}"
                    )
                chunk = chunk_index[chunk_id]
                evidence.append(
                    {
                        "source_id": chunk["source_ref"],
                        "locator": chunk["locator"],
                        "claim": evidence_ref["claim"],
                        "content_sha256": chunk["content_sha256"],
                    }
                )
            normalized_evidence = sorted(
                evidence,
                key=lambda row: (
                    row["source_id"],
                    row["locator"],
                    row["claim"],
                ),
            )
            proposed_record = copy.deepcopy(proposal["proposed_record"])
            if proposal["proposal_type"] in {
                "claim",
                "equation",
                "method",
                "mechanism",
            }:
                proposed_record["sources"] = [
                    {
                        "ref": row["source_id"],
                        "locator": row["locator"],
                        "content_sha256": row["content_sha256"],
                    }
                    for row in normalized_evidence
                ]
            identity = {
                "packet_id": packet_id,
                "candidate_key": proposal["candidate_key"],
                "proposal_type": proposal["proposal_type"],
                "record": proposed_record,
                "evidence": normalized_evidence,
            }
            candidates.append(
                {
                    "candidate_id": "candidate_semantic_" + _short_hash(identity),
                    "proposal_type": proposal["proposal_type"],
                    "suggested_id": proposal["suggested_id"],
                    "proposed_record": proposed_record,
                    "source_evidence": normalized_evidence,
                    "created_by": created_by,
                    "created_at": created_at,
                }
            )
    extractor = {
        "agent": f"cpcs-source-extract+{response['extractor']['agent']}",
        "model": f"deterministic-structural-rules+{response['extractor']['model']}",
        "prompt_hash": sha256_value(
            {
                "structural": structural_extractor["prompt_hash"],
                "semantic": response["extractor"]["prompt_hash"],
            }
        ),
    }
    return sorted(candidates, key=lambda row: row["candidate_id"]), extractor


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


@authority_reader("source_coverage_snapshot")
def _coverage(
    sources: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    packets: list[dict[str, Any]],
    selected_chunk_ids: set[str],
    candidates: list[dict[str, Any]],
    root: Path,
) -> dict[str, Any]:
    chunk_by_locator = {(row["source_ref"], row["locator"]): row for row in chunks}
    candidate_sections: dict[str, list[str]] = {}
    for candidate in candidates:
        for evidence in candidate["source_evidence"]:
            chunk = chunk_by_locator.get((evidence["source_id"], evidence["locator"]))
            if chunk:
                candidate_sections.setdefault(chunk["section_id"], []).append(candidate["candidate_id"])
    packet_sections: dict[str, list[str]] = {}
    chunk_index = {row["chunk_id"]: row for row in chunks}
    for packet in packets:
        for passage in packet["passages"]:
            chunk = chunk_index[passage["chunk_id"]]
            packet_sections.setdefault(chunk["section_id"], []).append(packet["packet_id"])
    chunks_by_section: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        chunks_by_section.setdefault(chunk["section_id"], []).append(chunk)
    curated_tokens = [
        _tokens(" ".join(str(row.get(key, "")) for key in ("name", "what", "use_when")))
        for row in read_jsonl(root / "lab/concepts.jsonl")
    ]
    dispositions = []
    high_novelty = []
    zero = []
    defined_without_definition = []
    claims_without_concepts = []
    for source in sources:
        for section in source["sections"]:
            section_id = section["section_id"]
            candidate_ids = sorted(set(candidate_sections.get(section_id, [])))
            packet_ids = sorted(set(packet_sections.get(section_id, [])))
            section_chunks = chunks_by_section.get(section_id, [])
            relevant_omitted = any(
                chunk["chunk_id"] not in selected_chunk_ids
                and _tokens(chunk["text"])
                for chunk in section_chunks
            )
            if candidate_ids and packet_ids:
                status = "candidate_and_semantic"
                reasons = ["candidate_extracted", "bounded_semantic_packet"]
            elif candidate_ids:
                status = "candidate_only"
                reasons = ["candidate_extracted"]
            elif packet_ids:
                status = "semantic_only"
                reasons = ["bounded_semantic_packet"]
            elif not section_chunks:
                status = "empty"
                reasons = ["section_has_no_non_whitespace_text"]
            elif relevant_omitted:
                status = "omitted_packet_limit"
                reasons = ["not_selected_for_bounded_semantic_lane"]
            else:
                status = "structural_only"
                reasons = ["parsed_without_candidate"]
            dispositions.append(
                {
                    "section_id": section_id,
                    "status": status,
                    "candidate_ids": candidate_ids,
                    "packet_ids": packet_ids,
                    "reasons": reasons,
                }
            )
            if not candidate_ids:
                zero.append(section_id)
                text = " ".join(row["text"] for row in section_chunks)
                tokens = _tokens(text)
                similarity = max((_jaccard(tokens, row) for row in curated_tokens), default=0.0)
                if tokens and 1.0 - similarity >= 0.8:
                    high_novelty.append(section_id)
                if section["kind"] in {"paragraph", "retrieved_passage", "structured_value"}:
                    claims_without_concepts.append(section_id)
            for line in section["text"].splitlines():
                match = re.match(r"^\s*([A-Z][A-Za-z0-9 /_-]{2,80})\s*[:—-]\s*(.*)$", line)
                if match and len(match.group(2).strip()) < 20:
                    defined_without_definition.append(f"{section_id}:{match.group(1).strip()}")
    concept_ids = {
        row["suggested_id"]
        for row in candidates
        if row["proposal_type"] == "concept" and row.get("suggested_id")
    }
    placed: set[str] = set()
    for candidate in candidates:
        record = candidate["proposed_record"]
        if candidate["proposal_type"] == "edge":
            placed.update(value for value in (record.get("u"), record.get("v")) if value in concept_ids)
        elif candidate["proposal_type"] == "mapping" and record.get("concept_id") in concept_ids:
            placed.add(record["concept_id"])
    semantic_disagreements = []
    structural_by_evidence = {
        (row["source_evidence"][0]["source_id"], row["source_evidence"][0]["locator"]): row
        for row in candidates
        if row["candidate_id"].startswith("candidate_structural_")
    }
    for row in candidates:
        if not row["candidate_id"].startswith("candidate_semantic_") or row["proposal_type"] != "concept":
            continue
        for evidence in row["source_evidence"]:
            structural = structural_by_evidence.get((evidence["source_id"], evidence["locator"]))
            if structural and not (
                _tokens(structural["proposed_record"].get("name", ""))
                & _tokens(row["proposed_record"].get("name", ""))
            ):
                semantic_disagreements.append(row["candidate_id"])
    return {
        "sections_total": len(dispositions),
        "sections_with_disposition": len(dispositions),
        "section_dispositions": sorted(dispositions, key=lambda row: row["section_id"]),
        "high_novelty_without_candidate": sorted(set(high_novelty)),
        "defined_terms_lacking_definitions": sorted(set(defined_without_definition)),
        "claims_lacking_concepts": sorted(set(claims_without_concepts)),
        "concepts_lacking_placement": sorted(concept_ids - placed),
        "semantic_disagreements": sorted(set(semantic_disagreements)),
        "sections_producing_zero_candidates": sorted(set(zero)),
        "unresolved_references": [],
    }


def _validate_bundle_invariants(bundle: dict[str, Any], root: Path) -> None:
    validate_instance("source_extraction_bundle", bundle, root)
    validate_instance("distillation_batch", bundle["distillation_batch"], root)
    chunk_ids = [row["chunk_id"] for row in bundle["chunks"]]
    section_ids = [row["section_id"] for row in bundle["coverage"]["section_dispositions"]]
    candidate_ids = [row["candidate_id"] for row in bundle["distillation_batch"]["candidates"]]
    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValidationFailure("source extraction chunk IDs must be unique")
    if len(section_ids) != len(set(section_ids)):
        raise ValidationFailure("every source section must have exactly one coverage disposition")
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValidationFailure("source extraction candidate IDs must be unique")
    declared_sections = {
        section_id
        for orientation in bundle["orientation"]
        for section_id in orientation["section_ids"]
    }
    if set(section_ids) != declared_sections:
        raise ValidationFailure("coverage dispositions must match the oriented source sections")
    configuration = bundle["configuration"]
    chunk_index = {row["chunk_id"]: row for row in bundle["chunks"]}
    inventory_index = {
        row["relative_path"]: row
        for row in bundle["inventory"]
        if row["status"] == "parsed"
    }
    ledger_index = {
        (row["source_id"], row["relative_path"]): row
        for row in bundle["source_ledger"]
    }
    if len(ledger_index) != len(bundle["source_ledger"]):
        raise ValidationFailure("source ledger identities must be unique")
    for ledger in bundle["source_ledger"]:
        inventory = inventory_index.get(ledger["relative_path"])
        if inventory is None or inventory["byte_hash"] != ledger["byte_hash"]:
            raise ValidationFailure(
                f"source ledger does not match inventory: {ledger['relative_path']}"
            )
        if ledger["source_id"] != "src_sha256_" + ledger["byte_hash"][7:]:
            raise ValidationFailure(
                f"source ledger ID is not content-addressed: {ledger['relative_path']}"
            )
    evidence_index = set()
    for chunk in bundle["chunks"]:
        if _sha256_bytes(chunk["text"].encode("utf-8")) != chunk["content_sha256"]:
            raise ValidationFailure(f"chunk content hash mismatch: {chunk['chunk_id']}")
        if len(chunk["text"]) > configuration["max_chunk_chars"]:
            raise ValidationFailure(f"chunk exceeds configured character budget: {chunk['chunk_id']}")
        ledger = ledger_index.get((chunk["source_id"], chunk["relative_path"]))
        if (
            ledger is None
            or chunk["section_id"] not in declared_sections
            or chunk["relative_path"] != ledger["relative_path"]
            or chunk["source_ref"] != ledger["source_ref"]
        ):
            raise ValidationFailure(f"chunk lineage does not resolve: {chunk['chunk_id']}")
        evidence_index.add(
            (chunk["source_ref"], chunk["locator"], chunk["content_sha256"])
        )
    for packet in bundle["semantic_packets"]:
        if len(packet["passages"]) > configuration["max_passages_per_packet"]:
            raise ValidationFailure(f"packet exceeds passage limit: {packet['packet_id']}")
        actual_chars = sum(len(row["text"]) for row in packet["passages"])
        if actual_chars != packet["passage_chars"] or actual_chars > configuration["max_packet_chars"]:
            raise ValidationFailure(f"packet exceeds or misstates character budget: {packet['packet_id']}")
        for passage in packet["passages"]:
            chunk = chunk_index.get(passage["chunk_id"])
            if chunk is None or passage["content_sha256"] != chunk["content_sha256"]:
                raise ValidationFailure(f"packet passage does not resolve: {passage['chunk_id']}")
    for candidate in bundle["distillation_batch"]["candidates"]:
        for evidence in candidate["source_evidence"]:
            if (
                evidence["source_id"],
                evidence["locator"],
                evidence["content_sha256"],
            ) not in evidence_index:
                raise ValidationFailure(
                    f"candidate evidence does not resolve to an owned chunk: {candidate['candidate_id']}"
                )
    core = {key: value for key, value in bundle.items() if key not in {"bundle_id", "bundle_hash"}}
    expected = hashlib.sha256(canonical_json_bytes(core)).hexdigest()
    if bundle["bundle_id"] != "source_bundle_" + expected[:24]:
        raise ValidationFailure("source extraction bundle_id does not match content")
    if bundle["bundle_hash"] != "sha256:" + expected:
        raise ValidationFailure("source extraction bundle_hash does not match content")


def build_source_bundle(
    *,
    sources: list[dict[str, Any]],
    inventory: list[dict[str, Any]],
    source_kind: str,
    research_goal: str,
    retrieval: dict[str, Any],
    created_by: str,
    created_at: str,
    semantic_response: dict[str, Any] | None = None,
    configuration: dict[str, Any] | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    config = _configuration(configuration)
    chunks = _build_chunks(sources, config)
    if not chunks:
        raise ValidationFailure("source extraction produced no non-empty chunks")
    packets, selected_chunk_ids = _semantic_packets(chunks, research_goal, config, root)
    structural = _structural_candidates(
        sources, chunks, created_by, created_at, config
    )
    semantic, extractor = _semantic_candidates(
        semantic_response, packets, chunks, created_by, created_at
    )
    candidates = sorted([*structural, *semantic], key=lambda row: row["candidate_id"])
    retrieval_record = copy.deepcopy(retrieval)
    retrieval_record["parameters"] = {
        **retrieval_record["parameters"],
        "source_policy": POLICY_VERSION,
        "source_hashes": {
            row["relative_path"]: row["byte_hash"] for row in inventory if row["byte_hash"]
        },
    }
    batch_core = {
        "retrieval": retrieval_record,
        "extractor": extractor,
        "candidates": candidates,
    }
    batch = {
        "batch_id": "batch_" + _short_hash(batch_core),
        **batch_core,
    }
    validate_instance("distillation_batch", batch, root)
    orientation = []
    ledger = []
    chunks_by_section: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        chunks_by_section.setdefault(chunk["section_id"], []).append(chunk)
    for source in sources:
        heading_tree = []
        for section in source["sections"]:
            if section["heading_path"] and section["heading_path"] not in heading_tree:
                heading_tree.append(section["heading_path"])
        source_chunks = [row for row in chunks if row["relative_path"] == source["relative_path"]]
        orientation.append(
            {
                "source_id": source["source_id"],
                "title": source["title"],
                "media_type": source["media_type"],
                "metadata": source["metadata"],
                "heading_tree": heading_tree,
                "section_ids": [row["section_id"] for row in source["sections"]],
                "summary": " ".join(row["text"] for row in source_chunks)[:1_000],
            }
        )
        unresolved = [
            {
                "section_id": section["section_id"],
                "locator": section["locator"],
                "reason": "section_has_no_non_whitespace_text",
            }
            for section in source["sections"]
            if section["section_id"] not in chunks_by_section
        ]
        ledger.append(
            {
                "source_id": source["source_id"],
                "source_ref": source["source_ref"],
                "relative_path": source["relative_path"],
                "media_type": source["media_type"],
                "byte_hash": source["byte_hash"],
                "parser_version": PARSER_VERSION,
                "extractor_versions": [STRUCTURAL_EXTRACTOR_VERSION]
                + ([semantic_response["extractor"]["model"]] if semantic_response else []),
                "rights_basis": source["rights_basis"],
                "sections_total": len(source["sections"]),
                "sections_processed": len(source["sections"]) - len(unresolved),
                "unresolved_sections": unresolved,
                "batch_id": batch["batch_id"],
            }
        )
    coverage = _coverage(
        sources, chunks, packets, selected_chunk_ids, candidates, root
    )
    core = {
        "schema": "cpcs.source_extraction_bundle/1.0",
        "source_kind": source_kind,
        "research_goal": research_goal,
        "configuration": config,
        "inventory": inventory,
        "orientation": sorted(orientation, key=lambda row: (row["source_id"], row["title"])),
        "source_ledger": sorted(ledger, key=lambda row: row["relative_path"]),
        "chunks": chunks,
        "semantic_packets": packets,
        "coverage": coverage,
        "distillation_batch": batch,
    }
    digest = hashlib.sha256(canonical_json_bytes(core)).hexdigest()
    bundle = {
        **core,
        "bundle_id": "source_bundle_" + digest[:24],
        "bundle_hash": "sha256:" + digest,
    }
    _validate_bundle_invariants(bundle, root)
    return bundle


def extract_folder(
    folder: Path,
    *,
    research_goal: str,
    rights_basis: str,
    semantic_response: dict[str, Any] | None = None,
    configuration: dict[str, Any] | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    config = _configuration(configuration)
    inventory, sources = _folder_sources(folder, rights_basis, config)
    retrieval = {
        "adapter": "local_source",
        "corpus_id": "local-folder:" + folder.resolve().name,
        "query": research_goal,
        "tool": "safe_folder_parse",
        "parameters": {"rights_basis": rights_basis},
        "retrieved_at": CONTENT_ADDRESSED_TIME,
    }
    return build_source_bundle(
        sources=sources,
        inventory=inventory,
        source_kind="authorized_folder",
        research_goal=research_goal,
        retrieval=retrieval,
        created_by="local_source",
        created_at=CONTENT_ADDRESSED_TIME,
        semantic_response=semantic_response,
        configuration=config,
        root=root,
    )


def extract_retrieved_passages(
    envelope: dict[str, Any],
    *,
    semantic_response: dict[str, Any] | None = None,
    configuration: dict[str, Any] | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    config = _configuration(configuration)
    validate_instance("retrieved_passages", envelope, root)
    inventory, sources = _passage_sources(envelope, config)
    retrieval = copy.deepcopy(envelope["retrieval"])
    retrieval["parameters"] = {
        **retrieval["parameters"],
        "rights_basis": envelope["rights_basis"],
    }
    return build_source_bundle(
        sources=sources,
        inventory=inventory,
        source_kind="polymath_passages",
        research_goal=envelope["retrieval"]["query"],
        retrieval=retrieval,
        created_by="polymath_mcp",
        created_at=envelope["retrieval"]["retrieved_at"],
        semantic_response=semantic_response,
        configuration=config,
        root=root,
    )


def write_bundle(bundle: dict[str, Any], output: Path, root: Path = REPO_ROOT) -> None:
    assert_write_target("source_extract", output, root)
    if output.exists():
        raise FileExistsError(f"source extraction output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(bundle))


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationFailure(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationFailure(f"{label} must be an object")
    return value


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    folder = sub.add_parser("folder", help="prepare an authorized local folder")
    folder.add_argument("source", type=Path)
    folder.add_argument("--research-goal", required=True)
    folder.add_argument("--rights-basis", required=True)
    folder.add_argument("--semantic-response", type=Path)
    folder.add_argument("--output", type=Path, required=True)
    passages = sub.add_parser("passages", help="prepare typed Polymath passages")
    passages.add_argument("record", type=Path)
    passages.add_argument("--semantic-response", type=Path)
    passages.add_argument("--output", type=Path, required=True)
    distill = sub.add_parser("distill", help="send a prepared bundle to the existing distiller")
    distill.add_argument("bundle", type=Path)
    args = parser.parse_args(argv)
    if args.command == "distill":
        bundle = _read_object(args.bundle, "source extraction bundle")
        _validate_bundle_invariants(bundle, REPO_ROOT)
        result = ingest_distillation_batch(bundle["distillation_batch"])
        print(
            json.dumps(
                {
                    "batch_id": result["batch_id"],
                    "distillation_run_id": result["id"],
                    "proposal_ids": result["proposal_ids"],
                    "summary": result["summary"],
                },
                sort_keys=True,
            )
        )
        return
    semantic = (
        _read_object(args.semantic_response, "semantic extraction response")
        if args.semantic_response
        else None
    )
    if args.command == "folder":
        bundle = extract_folder(
            args.source,
            research_goal=args.research_goal,
            rights_basis=args.rights_basis,
            semantic_response=semantic,
        )
    else:
        bundle = extract_retrieved_passages(
            _read_object(args.record, "retrieved passages"),
            semantic_response=semantic,
        )
    write_bundle(bundle, args.output)
    print(
        json.dumps(
            {
                "batch_id": bundle["distillation_batch"]["batch_id"],
                "bundle_id": bundle["bundle_id"],
                "candidates": len(bundle["distillation_batch"]["candidates"]),
                "chunks": len(bundle["chunks"]),
                "output": str(args.output),
                "semantic_packets": len(bundle["semantic_packets"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
