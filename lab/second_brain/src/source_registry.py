"""Immutable local source units, source closure, and exact source-answer fallback."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
from pathlib import Path
from typing import Any, Iterable

import yaml

from .authority import authority_reader, authority_writer
from .source_extract import DEFAULT_CONFIGURATION, validate_source_bundle
from .validate import (
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    canonical_json_bytes,
    content_hash,
    read_jsonl,
    sha256_value,
    validate_instance,
    write_jsonl,
)

SOURCE_UNIT_SCHEMA = "cpcs.source_unit/1.0"
SOURCE_CLOSURE_POLICY = "cpcs-source-closure/1.0"
REGISTRY_RELATIVE_PATH = Path("lab/second_brain/immutable/source_units.jsonl")
SOURCE_POINTER = "second_brain_source_units"
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "that", "the", "this",
    "to", "what", "when", "where", "which", "with",
}
SYMBOLIC_SOURCES = {
    "CPCS": Path(
        "research/CPCS_FACS_Laban_AI_Video_Research_Package_v1.2/paper/"
        "CPCS_FACS_Laban_AI_Video_Directorial_Control_Research_Paper.md"
    ),
    "MX": Path(
        "research/CPCS_MX_Hierarchical_Motion_Grammar_Research_Package_v1.0/"
        "paper/CPCS_MX_Hierarchical_Motion_Grammar_Research_Paper.md"
    ),
    "RDC": Path(
        "research/Pegasus_Atomic_Video_Deconstruction_and_Modular_AI_Recreation_v1.0.md"
    ),
}


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 1 and token not in STOP_WORDS
    }


def _registry_path(root: Path) -> Path:
    return root / REGISTRY_RELATIVE_PATH


def source_registry_required(root: Path = REPO_ROOT) -> bool:
    """Return whether this repository declares source units as a live authority."""
    path = root / "lab" / "registry.yaml"
    if not path.exists():
        return False
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return False
    scripts = value.get("scripts", {}) if isinstance(value, dict) else {}
    return isinstance(scripts, dict) and SOURCE_POINTER in scripts


def _validate_storage(unit: dict[str, Any], root: Path) -> bytes:
    storage = unit["storage"]
    if storage["kind"] == "embedded_passage":
        raw = storage["passage"].encode("utf-8")
    else:
        relative = Path(storage["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValidationFailure(
                f"source unit {unit['id']} has unsafe local path {relative}"
            )
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise ValidationFailure(
                f"source unit {unit['id']} local source is unavailable: {relative}"
            )
        source = path.read_bytes()
        if _sha256_bytes(source) != storage["source_file_sha256"]:
            raise ValidationFailure(
                f"source unit {unit['id']} local source hash changed"
            )
        start = storage["byte_start"]
        end = storage["byte_end"]
        if start >= end or end > len(source):
            raise ValidationFailure(
                f"source unit {unit['id']} has invalid local byte offsets"
            )
        raw = source[start:end]
    if _sha256_bytes(raw) != unit["content_sha256"]:
        raise ValidationFailure(
            f"source unit {unit['id']} passage hash does not match preserved bytes"
        )
    return raw


def load_source_units(root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    """Load and verify the complete append-only source-unit chain."""
    path = _registry_path(root)
    if not path.exists():
        return []
    rows = read_jsonl(path)
    prior: str | None = None
    seen_ids: set[str] = set()
    seen_addresses: set[tuple[str, str, str]] = set()
    for row in rows:
        validate_instance("source_unit", row, root)
        if row["id"] in seen_ids:
            raise ValidationFailure(f"duplicate source unit ID {row['id']}")
        address = (row["source_ref"], row["locator"], row["content_sha256"])
        if address in seen_addresses:
            raise ValidationFailure(
                f"duplicate source unit address {row['source_ref']}#{row['locator']}"
            )
        if row["prior_record_hash"] != prior:
            raise ValidationFailure(
                f"source unit {row['id']} has invalid prior_record_hash"
            )
        if row["record_hash"] != content_hash(row):
            raise ValidationFailure(
                f"source unit {row['id']} has invalid record_hash"
            )
        _validate_storage(row, root)
        seen_ids.add(row["id"])
        seen_addresses.add(address)
        prior = row["record_hash"]
    return rows


def _new_unit(
    *,
    source_id: str,
    source_ref: str,
    locator: str,
    source_byte_hash: str,
    content_sha256: str,
    rights_basis: str,
    media_type: str,
    storage: dict[str, Any],
    aliases: Iterable[str],
) -> dict[str, Any]:
    identity = {
        "source_id": source_id,
        "source_ref": source_ref,
        "locator": locator,
        "content_sha256": content_sha256,
    }
    return {
        "schema": SOURCE_UNIT_SCHEMA,
        "id": "source_unit_" + hashlib.sha256(
            canonical_json_bytes(identity)
        ).hexdigest()[:24],
        "source_id": source_id,
        "source_ref": source_ref,
        "locator": locator,
        "source_byte_hash": source_byte_hash,
        "content_sha256": content_sha256,
        "rights_basis": rights_basis,
        "media_type": media_type,
        "evidence_class": "authored",
        "storage": storage,
        "aliases": sorted(set(aliases)),
        "prior_record_hash": None,
        "record_hash": "sha256:" + "0" * 64,
    }


def _append_units(
    candidates: Iterable[dict[str, Any]], root: Path
) -> dict[str, Any]:
    path = _registry_path(root)
    existing = load_source_units(root)
    merged_candidates: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        prior_candidate = merged_candidates.get(candidate["id"])
        if prior_candidate is None:
            merged_candidates[candidate["id"]] = candidate
            continue
        comparable_fields = set(candidate) - {
            "aliases", "prior_record_hash", "record_hash"
        }
        if any(
            candidate[key] != prior_candidate[key]
            for key in comparable_fields
        ):
            raise ValidationFailure(
                f"source-unit identity collision for {candidate['id']}"
            )
        prior_candidate["aliases"] = sorted(
            set(prior_candidate["aliases"]) | set(candidate["aliases"])
        )
    by_id = {row["id"]: row for row in existing}
    by_address = {
        (row["source_ref"], row["locator"], row["content_sha256"]): row
        for row in existing
    }
    additions = []
    for candidate in sorted(merged_candidates.values(), key=lambda row: row["id"]):
        address = (
            candidate["source_ref"],
            candidate["locator"],
            candidate["content_sha256"],
        )
        prior = by_id.get(candidate["id"]) or by_address.get(address)
        if prior is not None:
            comparable = {
                key: value
                for key, value in prior.items()
                if key not in {"prior_record_hash", "record_hash"}
            }
            proposed = {
                key: value
                for key, value in candidate.items()
                if key not in {"prior_record_hash", "record_hash"}
            }
            if comparable != proposed:
                raise ValidationFailure(
                    f"source-unit collision for {candidate['id']}"
                )
            continue
        additions.append(candidate)
        by_id[candidate["id"]] = candidate
        by_address[address] = candidate
    prior_hash = existing[-1]["record_hash"] if existing else None
    sealed = list(existing)
    for candidate in additions:
        row = dict(candidate)
        row["prior_record_hash"] = prior_hash
        row["record_hash"] = content_hash(row)
        validate_instance("source_unit", row, root)
        _validate_storage(row, root)
        sealed.append(row)
        prior_hash = row["record_hash"]
    if additions:
        assert_write_target("source_registry", path, root)
        write_jsonl(path, sealed)
    return {
        "schema": "cpcs.source_unit_admission/1.0",
        "admitted_ids": [row["id"] for row in additions],
        "existing_ids": sorted(
            set(merged_candidates)
            - set(row["id"] for row in additions)
        ),
        "registry_hash": sha256_value(sealed),
        "source_unit_count": len(sealed),
        "authority_effect": "immutable_append_only",
    }


@authority_writer("source_unit_admission")
def admit_source_bundle(
    bundle: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Persist every verified bundle chunk so external retrieval is no longer required."""
    validate_source_bundle(bundle, root)
    ledger = {row["source_id"]: row for row in bundle["source_ledger"]}
    candidates = []
    for chunk in bundle["chunks"]:
        source = ledger[chunk["source_id"]]
        candidates.append(
            _new_unit(
                source_id=chunk["source_id"],
                source_ref=chunk["source_ref"],
                locator=chunk["locator"],
                source_byte_hash=source["byte_hash"],
                content_sha256=chunk["content_sha256"],
                rights_basis=source["rights_basis"],
                media_type=source["media_type"],
                storage={"kind": "embedded_passage", "passage": chunk["text"]},
                aliases=(
                    chunk["source_ref"],
                    f"{chunk['source_ref']}#{chunk['locator']}",
                ),
            )
        )
    return _append_units(candidates, root)


def _line_offsets(raw: bytes) -> list[tuple[int, int, str]]:
    rows = []
    offset = 0
    for line in raw.splitlines(keepends=True):
        text = line.decode("utf-8")
        rows.append((offset, offset + len(line), text.rstrip("\r\n")))
        offset += len(line)
    if raw and not rows:
        rows.append((0, len(raw), raw.decode("utf-8")))
    return rows


def _markdown_headings(raw: bytes) -> list[dict[str, Any]]:
    headings = []
    for start, end, line in _line_offsets(raw):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            title = re.sub(r"\s+#+$", "", match.group(2)).strip()
            headings.append(
                {
                    "level": len(match.group(1)),
                    "title": title,
                    "start": start,
                    "line_end": end,
                }
            )
    for index, heading in enumerate(headings):
        heading["end"] = next(
            (
                row["start"]
                for row in headings[index + 1 :]
                if row["level"] <= heading["level"]
            ),
            len(raw),
        )
    return headings


def _section_numbers(value: str) -> list[str]:
    values = []
    for raw in re.findall(
        r"§\s*([0-9]+(?:\.[0-9]+)*(?:-[0-9]+(?:\.[0-9]+)*)?)",
        value,
    ):
        if "-" not in raw:
            values.append(raw)
            continue
        left, right = raw.split("-", 1)
        left_parts = left.split(".")
        right_parts = right.split(".")
        if (
            len(left_parts) == len(right_parts)
            and left_parts[:-1] == right_parts[:-1]
            and left_parts[-1].isdigit()
            and right_parts[-1].isdigit()
        ):
            values.extend(
                ".".join([*left_parts[:-1], str(index)])
                for index in range(int(left_parts[-1]), int(right_parts[-1]) + 1)
            )
        else:
            values.extend((left, right))
    return list(dict.fromkeys(values))


def _heading_span(
    raw: bytes, *, section_number: str | None = None, slug: str | None = None,
    title_contains: str | None = None,
) -> tuple[int, int, str] | None:
    for heading in _markdown_headings(raw):
        title = heading["title"]
        if section_number is not None and not re.match(
            rf"^{re.escape(section_number)}(?:\s|$|[.:])", title
        ):
            continue
        normalized_slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        if slug is not None:
            requested_slug = slug.lower().strip("-")
            if not (
                normalized_slug == requested_slug
                or normalized_slug.startswith(requested_slug + "-")
            ):
                continue
        if title_contains is not None and title_contains.casefold() not in title.casefold():
            continue
        return heading["start"], heading["end"], title
    return None


def _fragment_span(raw: bytes, fragment: str) -> tuple[int, int, str] | None:
    heading = _heading_span(raw, slug=fragment)
    if heading is not None:
        return heading
    tag = fragment.replace("-", "_")
    open_match = re.search(rf"(?m)^\s*<{re.escape(tag)}(?:\s|>)", raw.decode("utf-8"))
    if open_match:
        close_match = re.search(
            rf"</{re.escape(tag)}>\s*", raw.decode("utf-8")[open_match.start() :]
        )
        if close_match:
            prefix = raw.decode("utf-8")[: open_match.start()].encode("utf-8")
            start = len(prefix)
            body = raw.decode("utf-8")[open_match.start() : open_match.start() + close_match.end()]
            return start, start + len(body.encode("utf-8")), fragment
    lines = _line_offsets(raw)
    for index, (start, _, line) in enumerate(lines):
        match = re.match(rf"^(\s*)-\s+id:\s*{re.escape(fragment)}\s*$", line)
        if not match:
            continue
        indent = len(match.group(1))
        end = len(raw)
        for next_start, _, next_line in lines[index + 1 :]:
            next_match = re.match(r"^(\s*)-\s+id:\s*", next_line)
            if next_match and len(next_match.group(1)) == indent:
                end = next_start
                break
        return start, end, fragment
    text = raw.decode("utf-8")
    literal = text.find(fragment)
    if literal >= 0:
        start = len(text[:literal].encode("utf-8"))
        line_end = text.find("\n", literal)
        if line_end < 0:
            line_end = len(text)
        end = len(text[:line_end].encode("utf-8"))
        return start, end, fragment
    return None


def _local_unit(
    path: Path,
    start: int,
    end: int,
    locator: str,
    alias: str,
    root: Path,
) -> dict[str, Any]:
    raw = path.read_bytes()
    relative = path.relative_to(root).as_posix()
    byte_hash = _sha256_bytes(raw)
    content = raw[start:end]
    source_id = "src_sha256_" + byte_hash.removeprefix("sha256:")
    media_type = mimetypes.guess_type(path.name)[0] or "text/plain"
    # Keep the exact source-file hash and byte span in the source identity and
    # locator, but embed the selected passage so an installed CPCS package can
    # verify and serve admitted evidence without shipping the complete research
    # corpus. The repository copy can still audit the locator against source.
    storage = {
        "kind": "embedded_passage",
        "passage": content.decode("utf-8"),
    }
    return _new_unit(
        source_id=source_id,
        source_ref="file:" + relative,
        locator=locator,
        source_byte_hash=byte_hash,
        content_sha256=_sha256_bytes(content),
        rights_basis="repository_owned_or_owner_authorized",
        media_type=media_type,
        storage=storage,
        aliases=(alias, f"file:{relative}#{locator}"),
    )


def _units_for_reference(
    reference: str, root: Path
) -> tuple[list[dict[str, Any]], str | None]:
    symbolic = re.match(r"^(CPCS|MX|RDC)\s+(.+)$", reference)
    if symbolic:
        prefix, selector = symbolic.groups()
        relative = SYMBOLIC_SOURCES[prefix]
        path = root / relative
        if not path.is_file():
            return [], "missing_local_source"
        raw = path.read_bytes()
        numbers = _section_numbers(selector)
        spans = []
        if numbers:
            for number in numbers:
                span = _heading_span(raw, section_number=number)
                if span is None:
                    return [], "unresolved_locator"
                spans.append((number, *span))
        elif "Appendix A" in selector:
            span = _heading_span(raw, title_contains="Appendix A")
            if span is None:
                return [], "unresolved_locator"
            spans.append(("Appendix A", *span))
        else:
            return [], "unresolved_locator"
        return [
            _local_unit(
                path,
                start,
                end,
                f"markdown:{prefix}:{number}#bytes={start}-{end}",
                reference,
                root,
            )
            for number, start, end, _ in spans
        ], None
    if reference.startswith(("polymath://", "http://", "https://")):
        return [], "external_passage_not_admitted"
    path_text, separator, fragment = reference.partition("#")
    relative_path = Path(path_text)
    path = root / relative_path
    if relative_path.is_absolute() or ".." in relative_path.parts or not path.is_file():
        return [], "missing_local_source" if "/" in path_text or "." in path_text else "unregistered_reference"
    raw = path.read_bytes()
    if not separator:
        return [
            _local_unit(
                path,
                0,
                len(raw),
                f"bytes:0-{len(raw)}",
                reference,
                root,
            )
        ], None
    try:
        span = _fragment_span(raw, fragment)
    except UnicodeDecodeError:
        span = None
    if span is None:
        return [], "unresolved_locator"
    start, end, label = span
    return [
        _local_unit(
            path,
            start,
            end,
            f"fragment:{label}#bytes={start}-{end}",
            reference,
            root,
        )
    ], None


@authority_writer("source_unit_backfill")
def backfill_local_references(root: Path = REPO_ROOT) -> dict[str, Any]:
    """Append exact local spans for every currently resolvable concept reference."""
    candidates = []
    unresolved: dict[str, str] = {}
    references = sorted(
        {
            reference
            for concept in read_jsonl(root / "lab" / "concepts.jsonl")
            for reference in concept.get("source", [])
        }
    )
    for reference in references:
        units, reason = _units_for_reference(reference, root)
        candidates.extend(units)
        if reason is not None:
            unresolved[reference] = reason
    result = _append_units(candidates, root)
    result["references"] = {
        "total": len(references),
        "resolved": len(references) - len(unresolved),
        "unresolved": len(unresolved),
    }
    result["unresolved_references"] = [
        {"reference": reference, "reason": reason}
        for reference, reason in sorted(unresolved.items())
    ]
    return result


def _units_for_alias(
    reference: str, units: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    exact = [row for row in units if reference in row["aliases"]]
    if exact:
        return exact
    if reference.startswith("polymath://") and "#chunk=" in reference:
        source_ref, chunk_id = reference.split("#chunk=", 1)
        return [
            row
            for row in units
            if row["source_ref"] == source_ref and chunk_id in row["locator"]
        ]
    return []


def _unresolved_reason(reference: str) -> str:
    if reference.startswith(("polymath://", "http://", "https://")):
        return "external_passage_not_admitted"
    path_text = reference.partition("#")[0]
    if "/" in path_text or "." in path_text:
        return "missing_local_source"
    if "§" in reference or "Appendix" in reference:
        return "unresolved_locator"
    return "unregistered_reference"


def build_source_closure_report(root: Path = REPO_ROOT) -> dict[str, Any]:
    units = load_source_units(root)
    concepts = read_jsonl(root / "lab" / "concepts.jsonl")
    rows = []
    polymath_dependent = 0
    polymath_quarantined = 0
    for concept in sorted(concepts, key=lambda row: row["id"]):
        resolved_ids: set[str] = set()
        unresolved = []
        has_polymath = any(
            reference.startswith("polymath://")
            for reference in concept.get("source", [])
        )
        unresolved_polymath = False
        for reference in concept.get("source", []):
            matches = _units_for_alias(reference, units)
            if matches:
                resolved_ids.update(row["id"] for row in matches)
            else:
                reason = _unresolved_reason(reference)
                unresolved.append({"reference": reference, "reason": reason})
                unresolved_polymath = unresolved_polymath or reference.startswith(
                    "polymath://"
                )
        status = (
            "source_closed"
            if resolved_ids and not unresolved
            else "partial"
            if resolved_ids
            else "quarantined"
        )
        rows.append(
            {
                "concept_id": concept["id"],
                "status": status,
                "source_unit_ids": sorted(resolved_ids),
                "unresolved_references": sorted(
                    unresolved, key=lambda row: row["reference"]
                ),
            }
        )
        polymath_dependent += int(has_polymath)
        polymath_quarantined += int(has_polymath and unresolved_polymath)
    report = {
        "schema": "cpcs.source_closure_report/1.0",
        "policy_version": SOURCE_CLOSURE_POLICY,
        "registry_hash": sha256_value(units),
        "concepts": rows,
        "counts": {
            "concepts": len(rows),
            "source_closed": sum(row["status"] == "source_closed" for row in rows),
            "partial": sum(row["status"] == "partial" for row in rows),
            "quarantined": sum(row["status"] == "quarantined" for row in rows),
            "source_units": len(units),
            "polymath_dependent_concepts": polymath_dependent,
            "polymath_quarantined_concepts": polymath_quarantined,
        },
    }
    report["report_hash"] = sha256_value(report)
    validate_instance("source_closure_report", report, root)
    return report


def resolve_typed_source_evidence(
    evidence: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Resolve one proposal evidence triple to one immutable local source unit."""
    required = ("source_id", "locator", "claim", "content_sha256")
    missing = [
        key
        for key in required
        if not isinstance(evidence.get(key), str) or not evidence[key]
    ]
    if missing:
        raise ValidationFailure(
            "promotion source evidence requires non-empty typed fields: "
            + ", ".join(missing)
        )
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", evidence["content_sha256"]):
        raise ValidationFailure("promotion source evidence content_sha256 is invalid")
    matches = [
        unit
        for unit in load_source_units(root)
        if unit["source_ref"] == evidence["source_id"]
        and unit["locator"] == evidence["locator"]
        and unit["content_sha256"] == evidence["content_sha256"]
    ]
    if len(matches) != 1:
        raise ValidationFailure(
            "promotion source evidence does not resolve to exactly one immutable "
            f"source unit: {evidence['source_id']}#{evidence['locator']}"
        )
    return {**evidence, "source_unit_id": matches[0]["id"]}


def _unit_bytes(unit: dict[str, Any], root: Path) -> bytes:
    return _validate_storage(unit, root)


def _bounded_passage(
    unit: dict[str, Any], query: str, root: Path
) -> dict[str, Any]:
    raw = _unit_bytes(unit, root)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValidationFailure(
            f"source unit {unit['id']} is not UTF-8 text"
        ) from error
    maximum = DEFAULT_CONFIGURATION["max_chunk_chars"]
    segments = []
    start = 0
    while start < len(text):
        end = min(len(text), start + maximum)
        segment = text[start:end]
        segments.append((len(_tokens(query) & _tokens(segment)), start, end, segment))
        start = end
    score, char_start, char_end, passage = max(
        segments, key=lambda row: (row[0], -row[1])
    )
    byte_start = len(text[:char_start].encode("utf-8"))
    byte_end = len(text[:char_end].encode("utf-8"))
    return {
        "source_unit_id": unit["id"],
        "source_id": unit["source_id"],
        "source_ref": unit["source_ref"],
        "locator": f"{unit['locator']}#unit_bytes={byte_start}-{byte_end}",
        "source_unit_content_hash": unit["content_sha256"],
        "content_hash": _sha256_bytes(passage.encode("utf-8")),
        "passage": passage,
        "rights_basis": unit["rights_basis"],
        "evidence_class": unit["evidence_class"],
        "match_token_count": score,
    }


@authority_reader("source_unit_resolution")
def resolve_sources(
    *,
    concept_ids: Iterable[str] = (),
    source_unit_ids: Iterable[str] = (),
    query: str = "",
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    units = load_source_units(root)
    by_id = {row["id"]: row for row in units}
    requested_units = set(source_unit_ids)
    requested_concepts = set(concept_ids)
    concepts = {
        row["id"]: row
        for row in read_jsonl(root / "lab" / "concepts.jsonl")
        if row["id"] in requested_concepts
    }
    missing_concepts = sorted(requested_concepts - set(concepts))
    missing_units = sorted(requested_units - set(by_id))
    if missing_concepts or missing_units:
        raise ValidationFailure(
            f"source resolution missing concepts={missing_concepts} source_units={missing_units}"
        )
    unresolved = []
    concept_links: dict[str, list[str]] = {}
    for concept_id, concept in sorted(concepts.items()):
        linked = set()
        for reference in concept.get("source", []):
            matches = _units_for_alias(reference, units)
            linked.update(row["id"] for row in matches)
            if not matches:
                unresolved.append(
                    {
                        "concept_id": concept_id,
                        "reference": reference,
                        "reason": _unresolved_reason(reference),
                    }
                )
        concept_links[concept_id] = sorted(linked)
        requested_units.update(linked)
    passages = [
        _bounded_passage(by_id[unit_id], query, root)
        for unit_id in sorted(requested_units)
    ]
    return {
        "schema": "cpcs.source_resolution/1.0",
        "query": query,
        "concept_source_units": concept_links,
        "passages": passages,
        "unresolved": unresolved,
        "registry_hash": sha256_value(units),
    }


def _sentences(text: str) -> list[tuple[int, int, str]]:
    spans = []
    for match in re.finditer(r"\S(?:.*?)(?:[.!?](?=\s|$)|\n+|$)", text, re.DOTALL):
        quote = match.group(0).strip()
        if not quote:
            continue
        leading = len(match.group(0)) - len(match.group(0).lstrip())
        start_char = match.start() + leading
        end_char = start_char + len(quote)
        spans.append((start_char, end_char, quote))
    return spans


def source_answer_trace(
    question: str,
    knowledge_gap: dict[str, Any],
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    slot = {
        "covered_terms": list(knowledge_gap.get("covered_terms", [])),
        "uncovered_terms": list(knowledge_gap.get("uncovered_terms", [])),
        "suggested_query": knowledge_gap.get("suggested_query", ""),
    }
    base = {
        "schema": "cpcs.source_answer_trace/1.0",
        "question": question,
        "unresolved_graph_slot": slot,
        "matches": [],
        "source_unit_id": None,
        "source_id": None,
        "locator": None,
        "content_hash": None,
        "answer_span": None,
        "evidence_class": None,
    }
    if not knowledge_gap.get("should_retrieve", False):
        trace = {
            **base,
            "disposition": "not_required",
            "uncertainty": "The curated graph did not declare an unanswered slot.",
        }
        validate_instance("source_answer_trace", trace, root)
        return trace
    query_tokens = _tokens(knowledge_gap.get("suggested_query", question))
    required_tokens = {
        token
        for term in knowledge_gap.get("uncovered_terms", [])
        for token in _tokens(term)
    } or query_tokens
    ranked = []
    for unit in load_source_units(root):
        raw = _unit_bytes(unit, root)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for start_char, end_char, quote in _sentences(text):
            quote_tokens = _tokens(quote)
            overlap = len(query_tokens & quote_tokens)
            if not required_tokens <= quote_tokens:
                continue
            distance = abs(len(_tokens(quote)) - len(query_tokens))
            start_byte = len(text[:start_char].encode("utf-8"))
            end_byte = len(text[:end_char].encode("utf-8"))
            ranked.append(
                {
                    "score": (overlap, -distance),
                    "unit": unit,
                    "start_byte": start_byte,
                    "end_byte": end_byte,
                    "quote": quote,
                }
            )
    if not ranked:
        trace = {
            **base,
            "disposition": "not_found",
            "uncertainty": "No preserved local source span shared a substantive query term.",
        }
        validate_instance("source_answer_trace", trace, root)
        return trace
    best_score = max(row["score"] for row in ranked)
    best = sorted(
        (row for row in ranked if row["score"] == best_score),
        key=lambda row: (row["unit"]["id"], row["start_byte"]),
    )
    matches = [
        {
            "source_unit_id": row["unit"]["id"],
            "source_id": row["unit"]["source_id"],
            "locator": row["unit"]["locator"],
            "content_hash": row["unit"]["content_sha256"],
        }
        for row in best
    ]
    if len(best) != 1:
        trace = {
            **base,
            "disposition": "ambiguous",
            "matches": matches,
            "uncertainty": "Multiple preserved local spans have the same deterministic match score.",
        }
        validate_instance("source_answer_trace", trace, root)
        return trace
    selected = best[0]
    unit = selected["unit"]
    quote = selected["quote"]
    trace = {
        **base,
        "disposition": "answered_local",
        "matches": matches,
        "source_unit_id": unit["id"],
        "source_id": unit["source_id"],
        "locator": unit["locator"],
        "content_hash": unit["content_sha256"],
        "answer_span": {
            "start_byte": selected["start_byte"],
            "end_byte": selected["end_byte"],
            "quote": quote,
            "quote_hash": _sha256_bytes(quote.encode("utf-8")),
        },
        "evidence_class": unit["evidence_class"],
        "uncertainty": "Exact authored source text is returned; its claim is not promoted by retrieval.",
    }
    validate_instance("source_answer_trace", trace, root)
    return trace


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("backfill", "status"))
    args = parser.parse_args(argv)
    result = (
        backfill_local_references()
        if args.command == "backfill"
        else build_source_closure_report()
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
