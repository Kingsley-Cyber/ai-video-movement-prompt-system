#!/usr/bin/env python3
"""Validate a CPCS Video Observation Graph structurally and semantically."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "1.0.0"


def add_issue(issues: list[dict[str, Any]], code: str, message: str, path: str, severity: str = "error") -> None:
    issues.append({"code": code, "message": message, "path": path, "severity": severity})


def validate_schema(graph: dict[str, Any], schema_path: Path, record_schema_path: Path | None = None) -> list[dict[str, Any]]:
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("jsonschema is required: pip install jsonschema") from exc
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    resolver_base = schema_path.resolve().as_uri()
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema, registry=None) if False else validator_cls(schema)
    # Referenced sibling schema is resolved by a local registry/store.
    record_path = record_schema_path or (schema_path.parent / "CPCS_Video_Observation_Record_Schema.json")
    if record_path.exists():
        record_schema = json.loads(record_path.read_text(encoding="utf-8"))
        try:
            from referencing import Registry, Resource
            registry = Registry().with_resource(record_schema["$id"], Resource.from_contents(record_schema))
            registry = registry.with_resource(record_path.resolve().as_uri(), Resource.from_contents(record_schema))
            validator = validator_cls(schema, registry=registry)
        except Exception:
            try:
                resolver = jsonschema.RefResolver(base_uri=resolver_base, referrer=schema, store={
                    record_schema.get("$id", ""): record_schema,
                    record_path.name: record_schema,
                    record_path.resolve().as_uri(): record_schema,
                })
                validator = validator_cls(schema, resolver=resolver)
            except Exception:
                validator = validator_cls(schema)
    errors = []
    for err in sorted(validator.iter_errors(graph), key=lambda e: list(e.absolute_path)):
        path = "/" + "/".join(str(p) for p in err.absolute_path)
        errors.append({"code": "SCHEMA", "message": err.message, "path": path or "/", "severity": "error"})
    return errors


def semantic_checks(graph: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    duration = graph.get("source", {}).get("duration_s")
    if not isinstance(duration, (int, float)) or duration <= 0:
        add_issue(issues, "INVALID_DURATION", "Source duration must be positive", "/source/duration_s")
        duration = 0.0

    observation_ids: set[str] = set()
    for i, obs in enumerate(graph.get("observations", [])):
        path = f"/observations/{i}"
        rid = obs.get("record_id")
        if rid in observation_ids:
            add_issue(issues, "DUPLICATE_OBSERVATION_ID", f"Duplicate observation ID {rid}", path + "/record_id")
        elif isinstance(rid, str):
            observation_ids.add(rid)
        tr = obs.get("time_range", {})
        start, end = tr.get("start_s"), tr.get("end_s")
        if isinstance(start, (int, float)) and isinstance(end, (int, float)):
            if end < start:
                add_issue(issues, "REVERSED_TIME_RANGE", "end_s precedes start_s", path + "/time_range")
            if start < -1e-9 or end > duration + 1e-6:
                add_issue(issues, "TIME_OUT_OF_RANGE", f"Observation lies outside source duration {duration}", path + "/time_range")
        if obs.get("source_id") != graph.get("source", {}).get("id"):
            add_issue(issues, "SOURCE_ID_MISMATCH", "Observation source_id differs from graph source.id", path + "/source_id")

    segment_ids: set[str] = set()
    for group in ("shots", "scenes", "beats"):
        previous_start = -1.0
        for i, seg in enumerate(graph.get("segments", {}).get(group, [])):
            path = f"/segments/{group}/{i}"
            sid = seg.get("id")
            if sid in segment_ids:
                add_issue(issues, "DUPLICATE_SEGMENT_ID", f"Duplicate segment ID {sid}", path + "/id")
            elif isinstance(sid, str):
                segment_ids.add(sid)
            start, end = seg.get("start_s"), seg.get("end_s")
            if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                if end <= start:
                    add_issue(issues, "INVALID_SEGMENT_RANGE", "Segment end_s must exceed start_s", path)
                if start < -1e-9 or end > duration + 1e-6:
                    add_issue(issues, "SEGMENT_OUT_OF_RANGE", f"Segment lies outside source duration {duration}", path)
                if start < previous_start:
                    add_issue(issues, "UNSORTED_SEGMENTS", "Segments are not sorted by start_s", path, "warning")
                previous_start = start

    entity_ids: set[str] = set()
    for group in ("actors", "objects", "locations"):
        for i, ent in enumerate(graph.get("entities", {}).get(group, [])):
            eid = ent.get("id")
            path = f"/entities/{group}/{i}/id"
            if eid in entity_ids:
                add_issue(issues, "DUPLICATE_ENTITY_ID", f"Duplicate entity ID {eid}", path)
            elif isinstance(eid, str):
                entity_ids.add(eid)

    resolved_ids: set[str] = set()
    for i, claim in enumerate(graph.get("resolved_claims", [])):
        path = f"/resolved_claims/{i}"
        cid = claim.get("id")
        if cid in resolved_ids:
            add_issue(issues, "DUPLICATE_RESOLVED_ID", f"Duplicate resolved claim ID {cid}", path + "/id")
        elif isinstance(cid, str):
            resolved_ids.add(cid)
        for ref in claim.get("observation_refs", []):
            if ref not in observation_ids:
                add_issue(issues, "UNRESOLVED_OBSERVATION_REF", f"Unknown observation reference {ref}", path + "/observation_refs")
        for ref in claim.get("entity_refs", []):
            if ref not in entity_ids:
                add_issue(issues, "UNRESOLVED_ENTITY_REF", f"Unknown entity reference {ref}", path + "/entity_refs")

    for i, contradiction in enumerate(graph.get("contradictions", [])):
        for ref in contradiction.get("observation_refs", []):
            if ref not in observation_ids and not str(ref).startswith("incoming:"):
                add_issue(issues, "UNRESOLVED_CONTRADICTION_REF", f"Unknown observation reference {ref}", f"/contradictions/{i}/observation_refs", "warning")

    # Interpretive claims must not masquerade as measurements.
    interpretive_layers = {"affect", "laban", "marketing"}
    for i, obs in enumerate(graph.get("observations", [])):
        if obs.get("layer") in interpretive_layers and obs.get("evidence_class") == "measured":
            add_issue(
                issues,
                "INTERPRETIVE_LAYER_MARKED_MEASURED",
                f"Layer {obs.get('layer')} should normally be inferred/interpreted or explicitly operationalized",
                f"/observations/{i}/evidence_class",
                "warning",
            )
    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("graph", type=Path)
    ap.add_argument("--schema", type=Path, required=True)
    ap.add_argument("--record-schema", type=Path, default=None, help="Optional local observation-record schema used to resolve the graph schema's external $ref")
    ap.add_argument("--write-updated", type=Path, default=None, help="Write graph with validation result populated")
    ap.add_argument("--warnings-as-errors", action="store_true")
    args = ap.parse_args()
    try:
        graph_path = args.graph.expanduser().resolve(strict=True)
        schema_path = args.schema.expanduser().resolve(strict=True)
        record_schema_path = args.record_schema.expanduser().resolve(strict=True) if args.record_schema else None
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        issues = validate_schema(graph, schema_path, record_schema_path)
        issues.extend(semantic_checks(graph))
        error_count = sum(1 for i in issues if i.get("severity") == "error")
        warning_count = sum(1 for i in issues if i.get("severity") == "warning")
        schema_valid = not any(i.get("code") == "SCHEMA" for i in issues)
        semantic_valid = not any(i.get("severity") == "error" and i.get("code") != "SCHEMA" for i in issues)
        result = {
            "schema_valid": schema_valid,
            "semantic_valid": semantic_valid,
            "issues": issues,
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "validator_version": VERSION,
        }
        if args.write_updated:
            graph["validation"] = result
            args.write_updated.parent.mkdir(parents=True, exist_ok=True)
            args.write_updated.write_text(json.dumps(graph, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        status_ok = error_count == 0 and (not args.warnings_as_errors or warning_count == 0)
        print(json.dumps({
            "status": "valid" if status_ok else "invalid",
            "graph": str(graph_path),
            "schema_valid": schema_valid,
            "semantic_valid": semantic_valid,
            "errors": error_count,
            "warnings": warning_count,
            "issues": issues,
        }, indent=2))
        return 0 if status_ok else 1
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
