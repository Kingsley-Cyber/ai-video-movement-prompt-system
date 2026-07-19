#!/usr/bin/env python3
"""Merge validated CPCS-MX observation JSONL streams with explicit precedence.

The merger preserves every input record, applies explicit `supersedes` edges,
identifies unresolved same-slot claims, and writes an active observation stream
plus a conflict report. It does not average incompatible claims.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

EVIDENCE_RANK = {
    "defaulted": 0,
    "interpreted": 1,
    "inferred": 2,
    "detected": 3,
    "derived": 3,
    "measured": 4,
    "authored": 5,
}
REVIEW_RANK = {"unreviewed": 0, "reviewed": 1, "locked": 2, "rejected": -1}


def iter_records(paths: Iterable[Path]) -> Iterable[tuple[Path, int, dict[str, Any]]]:
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError(f"{path}:{line_no}: record must be an object")
                yield path, line_no, record


def temporal_key(record: dict[str, Any]) -> tuple[Any, ...]:
    if "frame_index" in record:
        return ("frame", record["frame_index"])
    if "pts_s" in record:
        return ("pts", round(float(record["pts_s"]), 6))
    tr = record.get("time_range") or {}
    return ("range", round(float(tr.get("start_s", 0)), 6), round(float(tr.get("end_s", 0)), 6))


def claim_slot(record: dict[str, Any]) -> tuple[Any, ...]:
    claim = record.get("claim") or {}
    return (
        record.get("source_id"),
        record.get("layer"),
        record.get("subject_ref"),
        claim.get("type"),
        temporal_key(record),
    )


def authority_key(record: dict[str, Any]) -> tuple[int, int, float, str]:
    return (
        REVIEW_RANK.get(record.get("review_status", "unreviewed"), 0),
        EVIDENCE_RANK.get(record.get("evidence_class", "interpreted"), 0),
        float(record.get("confidence", 0.0)),
        str(record.get("record_id", "")),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--conflicts", type=Path, required=True)
    parser.add_argument("--all-records", type=Path, help="Optional normalized copy of every valid input record")
    args = parser.parse_args()

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    records: dict[str, dict[str, Any]] = {}
    origins: dict[str, dict[str, Any]] = {}

    for path, line_no, record in iter_records(args.inputs):
        errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
        if errors:
            detail = "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:10])
            raise ValueError(f"{path}:{line_no}: schema validation: {detail}")
        rid = str(record["record_id"])
        if rid in records and records[rid] != record:
            raise ValueError(f"conflicting duplicate record_id {rid} at {path}:{line_no}")
        records[rid] = record
        origins[rid] = {"path": str(path), "line_number": line_no}

    superseded_by: dict[str, str] = {}
    for rid, record in records.items():
        for old in record.get("supersedes") or []:
            if old in superseded_by and superseded_by[old] != rid:
                raise ValueError(f"record {old} is superseded by both {superseded_by[old]} and {rid}")
            superseded_by[old] = rid

    active = [r for rid, r in records.items() if rid not in superseded_by and r.get("review_status") != "rejected"]
    slots: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in active:
        slots[claim_slot(record)].append(record)

    selected: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for slot, candidates in slots.items():
        ranked = sorted(candidates, key=authority_key, reverse=True)
        winner = ranked[0]
        selected.append(winner)
        if len(ranked) > 1:
            winner_claim = winner.get("claim")
            incompatible = [r for r in ranked[1:] if r.get("claim") != winner_claim]
            if incompatible:
                conflicts.append({
                    "slot": slot,
                    "selected_record_id": winner["record_id"],
                    "candidate_record_ids": [r["record_id"] for r in ranked],
                    "reason": "same semantic slot contains incompatible claims without explicit supersession",
                    "resolution": "highest declared authority selected for active stream; human review recommended",
                })

    selected.sort(key=lambda r: (temporal_key(r), str(r.get("layer", "")), str(r.get("subject_ref", "")), str(r["record_id"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in selected:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    args.conflicts.write_text(json.dumps({"conflict_count": len(conflicts), "conflicts": conflicts, "superseded_by": superseded_by, "origins": origins}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.all_records:
        with args.all_records.open("w", encoding="utf-8") as handle:
            for rid in sorted(records):
                handle.write(json.dumps(records[rid], ensure_ascii=False, separators=(",", ":")) + "\n")

    print(json.dumps({"input_records": len(records), "active_records": len(selected), "superseded_records": len(superseded_by), "conflicts": len(conflicts), "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
