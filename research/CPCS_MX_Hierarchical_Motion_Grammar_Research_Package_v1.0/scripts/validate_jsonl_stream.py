#!/usr/bin/env python3
"""Stream, validate, and optionally quarantine JSONL records.

Supports plain UTF-8 JSONL and gzip-compressed JSONL. Records are validated one
line at a time to avoid loading the entire corpus into memory.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import IO, Any

from jsonschema import Draft202012Validator


def open_text(path: Path) -> IO[str]:
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("r", encoding="utf-8", newline="")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--id-field", default="record_id")
    parser.add_argument("--hash-field", default="sha256")
    parser.add_argument("--hash-content-field", default="content")
    parser.add_argument("--max-line-bytes", type=int, default=8 * 1024 * 1024)
    parser.add_argument("--quarantine", type=Path, help="Write malformed/invalid records with diagnostic metadata")
    parser.add_argument("--duplicates", choices=["error", "warn", "allow-identical"], default="error")
    args = parser.parse_args()

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    seen: dict[str, str] = {}
    counts = Counter()
    quarantine = args.quarantine.open("w", encoding="utf-8") if args.quarantine else None

    def reject(line_no: int, raw: str, reason: str) -> None:
        counts["rejected"] += 1
        if quarantine:
            quarantine.write(json.dumps({"line_number": line_no, "reason": reason, "raw": raw.rstrip("\n")}, ensure_ascii=False) + "\n")
        else:
            print(f"{args.input}:{line_no}: {reason}", file=sys.stderr)

    try:
        with open_text(args.input) as handle:
            for line_no, line in enumerate(handle, start=1):
                counts["lines"] += 1
                if not line.strip():
                    counts["blank"] += 1
                    continue
                if len(line.encode("utf-8")) > args.max_line_bytes:
                    reject(line_no, line, f"line exceeds {args.max_line_bytes} bytes")
                    continue
                try:
                    record: Any = json.loads(line)
                except json.JSONDecodeError as exc:
                    reject(line_no, line, f"JSON parse error: {exc}")
                    continue
                if not isinstance(record, dict):
                    reject(line_no, line, "record must be a JSON object")
                    continue
                errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
                if errors:
                    reason = "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:10])
                    reject(line_no, line, f"schema validation: {reason}")
                    continue
                rid = record.get(args.id_field)
                canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                if rid is not None and str(rid) in seen:
                    counts["duplicates"] += 1
                    identical = seen[str(rid)] == digest
                    if args.duplicates == "error" or (args.duplicates == "allow-identical" and not identical):
                        reject(line_no, line, f"duplicate {args.id_field}={rid}; identical={identical}")
                        continue
                    if args.duplicates == "warn":
                        print(f"warning: duplicate {args.id_field}={rid}; identical={identical}", file=sys.stderr)
                elif rid is not None:
                    seen[str(rid)] = digest

                if args.hash_field in record and args.hash_content_field in record:
                    expected = record[args.hash_field]
                    actual = hashlib.sha256(str(record[args.hash_content_field]).encode("utf-8")).hexdigest()
                    if expected != actual:
                        reject(line_no, line, f"content hash mismatch: expected {expected}, got {actual}")
                        continue
                counts["accepted"] += 1
    finally:
        if quarantine:
            quarantine.close()

    result = {
        "input": str(args.input),
        "schema": str(args.schema),
        "counts": dict(counts),
        "unique_ids": len(seen),
        "valid": counts["rejected"] == 0,
    }
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
