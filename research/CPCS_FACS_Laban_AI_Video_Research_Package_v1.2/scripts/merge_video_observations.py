#!/usr/bin/env python3
"""Merge JSON/JSONL video observations into a canonical CPCS observation graph."""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

VERSION = "1.0.0"


def canonical_digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        records = []
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: JSONL line is not an object")
            records.append(value)
        return records
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, list):
        if not all(isinstance(v, dict) for v in value):
            raise ValueError(f"{path}: array contains non-object values")
        return value
    if isinstance(value, dict) and isinstance(value.get("observations"), list):
        return list(value["observations"])
    if isinstance(value, dict):
        return [value]
    raise ValueError(f"{path}: unsupported JSON top-level value")


def expand_inputs(patterns: Iterable[str]) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        matches = [Path(p) for p in glob.glob(pattern)] or [Path(pattern)]
        for p in matches:
            rp = p.expanduser().resolve(strict=True)
            if rp not in seen:
                seen.add(rp)
                paths.append(rp)
    return paths


def time_start(record: dict[str, Any]) -> float:
    try:
        return float(record.get("time_range", {}).get("start_s", 0.0))
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--conflicts", type=Path, required=True)
    ap.add_argument("--graph-id", default=None)
    ap.add_argument("--fail-on-duplicate-conflict", action="store_true")
    args = ap.parse_args()

    try:
        manifest_path = args.manifest.expanduser().resolve(strict=True)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source = manifest["source"]
        source_id = source["id"]
        source_hash = source["sha256"]
        input_paths = expand_inputs(args.inputs)

        by_id: dict[str, dict[str, Any]] = {}
        duplicate_conflicts: list[dict[str, Any]] = []
        ignored_duplicates: list[dict[str, Any]] = []
        load_issues: list[dict[str, Any]] = []

        for path in input_paths:
            for index, record in enumerate(load_records(path)):
                rid = record.get("record_id")
                if not isinstance(rid, str) or not rid:
                    load_issues.append({"path": str(path), "index": index, "code": "MISSING_RECORD_ID"})
                    continue
                if record.get("source_id") != source_id:
                    load_issues.append({
                        "path": str(path), "record_id": rid, "code": "SOURCE_ID_MISMATCH",
                        "expected": source_id, "actual": record.get("source_id")
                    })
                    continue
                rec_hash = record.get("source_sha256")
                if rec_hash and rec_hash != source_hash:
                    load_issues.append({
                        "path": str(path), "record_id": rid, "code": "SOURCE_HASH_MISMATCH",
                        "expected": source_hash, "actual": rec_hash
                    })
                    continue
                if rid in by_id:
                    old = by_id[rid]
                    if canonical_digest(old) == canonical_digest(record):
                        ignored_duplicates.append({"record_id": rid, "path": str(path), "status": "identical"})
                    else:
                        duplicate_conflicts.append({
                            "id": f"conflict.duplicate.{len(duplicate_conflicts)+1:06d}",
                            "record_id": rid,
                            "type": "duplicate_id",
                            "status": "open",
                            "existing_digest": canonical_digest(old),
                            "incoming_digest": canonical_digest(record),
                            "incoming_path": str(path),
                        })
                    continue
                by_id[rid] = record

        if args.fail_on_duplicate_conflict and duplicate_conflicts:
            raise ValueError(f"Found {len(duplicate_conflicts)} conflicting duplicate record IDs")

        observations = sorted(by_id.values(), key=lambda r: (time_start(r), r.get("layer", ""), r["record_id"]))
        graph_id = args.graph_id or f"vog.{source_hash[:16]}"
        width = source.get("width")
        height = source.get("height")
        graph = {
            "schema": "cpcs-video-observation-graph/1.0",
            "graph_id": graph_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": {
                "id": source_id,
                "uri": source.get("uri"),
                "display_name": source.get("display_name"),
                "sha256": source_hash,
                "duration_s": source["duration_s"],
                "media_type": source.get("media_type", "video/unknown"),
                "width": width,
                "height": height,
                "nominal_fps": source.get("nominal_fps"),
                "variable_frame_rate": source.get("variable_frame_rate_candidate"),
                "has_audio": source.get("has_audio"),
                "probe_asset": next((a.get("path") for a in manifest.get("assets", []) if a.get("id") == "source_probe"), None),
            },
            "clock": {
                "canonical": manifest.get("clock", {}).get("canonical", "source_pts"),
                "timebase": manifest.get("clock", {}).get("timebase", {"numerator": 1, "denominator": 1000}),
                "pts_origin_s": manifest.get("clock", {}).get("pts_origin_s", 0.0),
                "proxy_mappings": [
                    {"proxy_id": a["id"], **a["source_time_mapping"]}
                    for a in manifest.get("assets", []) if a.get("source_time_mapping")
                ],
            },
            "rights": {
                "basis": None,
                "permitted_uses": [],
                "restricted_elements": [],
                "retention_policy": None,
                "human_review_required": True,
            },
            "segments": {"shots": [], "scenes": [], "beats": []},
            "entities": {"actors": [], "objects": [], "locations": []},
            "observations": observations,
            "resolved_claims": [],
            "contradictions": [
                {
                    "id": c["id"],
                    "observation_refs": [c["record_id"], f"incoming:{c['incoming_digest'][:12]}"],
                    "type": "duplicate_id",
                    "status": "open",
                    "resolution": None,
                    "reviewer": None,
                }
                for c in duplicate_conflicts
            ],
            "cpcs_projection": {},
            "provider_profiles": [],
            "assets": [
                {
                    "id": a["id"],
                    "uri": Path(a["path"]).as_uri() if a.get("path") and Path(a["path"]).is_absolute() else str(a.get("path", "")),
                    "role": a.get("role", "unknown"),
                    "sha256": a.get("sha256"),
                    "media_type": None,
                    "source_time_mapping": a.get("source_time_mapping"),
                }
                for a in manifest.get("assets", []) if a.get("path")
            ],
            "validation": {
                "schema_valid": False,
                "semantic_valid": False,
                "issues": load_issues,
                "validated_at": None,
                "validator_version": None,
            },
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.conflicts.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(graph, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        args.conflicts.write_text(json.dumps({
            "schema": "cpcs-video-observation-merge-report/1.0",
            "source_id": source_id,
            "input_files": [str(p) for p in input_paths],
            "record_count": len(observations),
            "ignored_duplicates": ignored_duplicates,
            "duplicate_conflicts": duplicate_conflicts,
            "load_issues": load_issues,
        }, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": "ok",
            "graph": str(args.output),
            "records": len(observations),
            "conflicts": len(duplicate_conflicts),
            "issues": len(load_issues),
        }, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
