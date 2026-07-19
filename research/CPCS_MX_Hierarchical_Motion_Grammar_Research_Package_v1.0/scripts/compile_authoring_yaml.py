#!/usr/bin/env python3
"""Resolve CPCS-MX authoring YAML and emit a canonical JSON candidate.

This is a reference compiler for profiles, merge behavior, normalization, and
basic semantic mapping. It intentionally does not synthesize dense skeletal
motion. Unmapped authoring fields are retained in a namespaced extension and
reported instead of being silently discarded.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

APPEND_PATH_SUFFIXES = {
    ("hard_constraints",),
    ("soft_constraints",),
    ("verification", "recommended_metrics"),
}
ID_KEYS = ("id", "action_id", "constraint_id", "event_id", "track_id", "system_id")


def read_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML parse failure in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping at {path}")
    return data


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse failure in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object at {path}")
    return data


def is_append_path(path: tuple[str, ...]) -> bool:
    return any(path[-len(suffix):] == suffix for suffix in APPEND_PATH_SUFFIXES if len(path) >= len(suffix))


def item_id(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    for key in ID_KEYS:
        if key in item and isinstance(item[key], (str, int)):
            return f"{key}:{item[key]}"
    return None


def merge_lists(base: list[Any], override: list[Any], path: tuple[str, ...]) -> list[Any]:
    if is_append_path(path):
        return copy.deepcopy(base) + copy.deepcopy(override)
    base_ids = [item_id(x) for x in base]
    over_ids = [item_id(x) for x in override]
    if base and override and all(base_ids) and all(over_ids):
        result = copy.deepcopy(base)
        index = {item_id(item): i for i, item in enumerate(result)}
        for item in override:
            ident = item_id(item)
            if ident in index:
                result[index[ident]] = deep_merge(result[index[ident]], item, path + (ident or "item",))
            else:
                index[ident] = len(result)
                result.append(copy.deepcopy(item))
        return result
    return copy.deepcopy(override)


def deep_merge(base: Any, override: Any, path: tuple[str, ...] = ()) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        result = copy.deepcopy(base)
        for key, value in override.items():
            if key in result:
                result[key] = deep_merge(result[key], value, path + (str(key),))
            else:
                result[key] = copy.deepcopy(value)
        return result
    if isinstance(base, list) and isinstance(override, list):
        return merge_lists(base, override, path)
    return copy.deepcopy(override)


def profile_uri_to_path(uri: str, profiles_root: Path) -> Path:
    prefix = "profile://"
    if not uri.startswith(prefix):
        raise ValueError(f"Unsupported profile URI: {uri}")
    rel = uri[len(prefix):]
    if not re.fullmatch(r"[A-Za-z0-9_.\-/]+", rel):
        raise ValueError(f"Unsafe profile URI: {uri}")
    candidate = (profiles_root / f"{rel}.yaml").resolve()
    root = profiles_root.resolve()
    if root not in candidate.parents:
        raise ValueError(f"Profile escaped configured root: {uri}")
    return candidate


def verify_sha256(path: Path, expected: str | None) -> str:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected and actual.lower() != expected.lower():
        raise ValueError(f"SHA-256 mismatch for {path}: expected {expected}, got {actual}")
    return actual


def load_imports(authoring: dict[str, Any], source_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    resolved: dict[str, Any] = {}
    provenance: list[dict[str, Any]] = []
    for name, spec in (authoring.get("imports") or {}).items():
        if not isinstance(spec, dict) or "type" not in spec or "path" not in spec:
            raise ValueError(f"Invalid import specification: {name}")
        rel = Path(spec["path"])
        path = (source_path.parent / rel).resolve()
        root = source_path.parent.resolve()
        if root not in path.parents and path != root:
            raise ValueError(f"Import path escapes authoring directory: {spec['path']}")
        if not path.exists():
            provenance.append({"name": name, "path": str(path), "status": "missing"})
            continue
        digest = verify_sha256(path, spec.get("sha256"))
        typ = spec["type"]
        if typ == "json":
            content: Any = read_json(path)
        elif typ == "yaml":
            content = read_yaml(path)
        else:
            content = {"asset_path": str(path), "type": typ, "sha256": digest}
        resolved[name] = content
        provenance.append({"name": name, "path": str(path), "type": typ, "sha256": digest, "status": "resolved"})
    return resolved, provenance


def normalize_actor_list(authoring: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    chars: list[dict[str, Any]] = []
    mannerisms: list[dict[str, Any]] = []
    raw = []
    if isinstance(authoring.get("character"), dict):
        raw.append(authoring["character"])
    if isinstance(authoring.get("characters"), list):
        raw.extend(x for x in authoring["characters"] if isinstance(x, dict))
    if not raw:
        raw = [{"id": "actor_a"}]
    seen: set[str] = set()
    for item in raw:
        cid = str(item.get("id") or item.get("character_id") or f"actor_{len(chars)+1}")
        if cid in seen:
            continue
        seen.add(cid)
        out: dict[str, Any] = {"character_id": cid}
        mannerism = item.get("mannerism_profile")
        if isinstance(mannerism, str):
            out["mannerism_profile_ref"] = mannerism
        elif isinstance(mannerism, dict):
            mid = f"mannerism.{cid}.authoring"
            out["mannerism_profile_ref"] = mid
            mp: dict[str, Any] = {"mannerism_profile_id": mid, "rights_scope": "authoring_document"}
            allowed = {"preferred_stance", "asymmetry", "gesture_inventory", "gaze_pattern", "microvariation", "postural_tone", "breath_signature"}
            for k, v in mannerism.items():
                if k in allowed:
                    mp[k] = v
                elif k == "gaze" and isinstance(v, dict):
                    mp["gaze_pattern"] = v
            mannerisms.append(mp)
        chars.append(out)
    return chars, mannerisms, chars[0]["character_id"]


def make_constraint(text_or_obj: Any, idx: int, priority: str, shot_id: str) -> dict[str, Any]:
    if isinstance(text_or_obj, dict):
        c = copy.deepcopy(text_or_obj)
        c.setdefault("constraint_id", f"constraint.{priority}.{idx:03d}")
        c.setdefault("type", "authoring_constraint")
        c.setdefault("priority", priority)
        c.setdefault("scope", {"shot_ref": shot_id})
        c.setdefault("failure_policy", "reject_candidate" if priority == "hard" else "report")
        return c
    return {
        "constraint_id": f"constraint.{priority}.{idx:03d}",
        "scope": {"shot_ref": shot_id},
        "type": "textual_constraint",
        "value": str(text_or_obj),
        "priority": priority,
        "failure_policy": "reject_candidate" if priority == "hard" else "report",
        "evidence": {"class": "authored", "confidence": 1.0},
    }


def compile_candidate(resolved: dict[str, Any], profile_trace: list[dict[str, Any]], import_trace: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    unresolved: list[str] = []
    shot_src = resolved.get("shot") if isinstance(resolved.get("shot"), dict) else {}
    shot_id = str(shot_src.get("id") or "shot_001")
    duration = float(shot_src.get("duration_s") or 4.0)
    fps_raw = shot_src.get("fps", 24)
    if isinstance(fps_raw, dict):
        fps = {"numerator": int(fps_raw.get("numerator", 24)), "denominator": int(fps_raw.get("denominator", 1))}
    else:
        fps = {"numerator": int(fps_raw), "denominator": 1}

    characters, mannerisms, default_actor = normalize_actor_list(resolved)
    actor_ids = {c["character_id"] for c in characters}

    beat_intervals: dict[str, list[float]] = {}
    beats: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []

    for bidx, beat_src in enumerate(resolved.get("action_graph") or [], start=1):
        if not isinstance(beat_src, dict):
            unresolved.append(f"action_graph[{bidx}] is not an object")
            continue
        bid = str(beat_src.get("id") or f"beat_{bidx:03d}")
        interval = beat_src.get("interval_s") or [0.0, duration]
        if not (isinstance(interval, list) and len(interval) == 2):
            unresolved.append(f"{bid}: invalid interval_s; defaulted to shot interval")
            interval = [0.0, duration]
        interval = [float(interval[0]), float(interval[1])]
        beat_intervals[bid] = interval
        actions: list[dict[str, Any]] = []
        for aidx, raw_action in enumerate(beat_src.get("actions") or [], start=1):
            if isinstance(raw_action, str):
                typ = raw_action
                actor = default_actor
                target = None
                trigger = None
            elif isinstance(raw_action, dict):
                typ = str(raw_action.get("type") or raw_action.get("action") or f"unspecified_{aidx}")
                actor = str(raw_action.get("actor") or raw_action.get("actor_ref") or default_actor)
                target = raw_action.get("target") or raw_action.get("target_ref")
                trigger = raw_action.get("trigger") or raw_action.get("trigger_event_ref")
            else:
                unresolved.append(f"{bid}: action {aidx} has unsupported type")
                continue
            if actor not in actor_ids:
                unresolved.append(f"{bid}: action {typ} references undeclared actor {actor}")
            action = {
                "action_id": f"action.{actor}.{re.sub(r'[^A-Za-z0-9_.-]+','_',typ)}.{aidx:02d}",
                "action_type": typ,
                "actor_ref": actor,
                "interval": interval,
            }
            if target:
                action["target_ref"] = str(target)
            if trigger:
                # A natural-language trigger is preserved as metadata unless it already looks like a stable event ID.
                if str(trigger).startswith("event."):
                    action["trigger_event_ref"] = str(trigger)
                else:
                    action["metadata"] = {"authoring_trigger": str(trigger)}
            actions.append(action)
        beat: dict[str, Any] = {"beat_id": bid, "interval": {"start_s": interval[0], "end_s": interval[1]}, "actions": actions}
        if "objective" in beat_src:
            beat["objective"] = str(beat_src["objective"])
        elif shot_src.get("objective"):
            beat["objective"] = str(shot_src["objective"])
        beats.append(beat)

        markers = beat_src.get("phase_markers")
        if isinstance(markers, dict):
            for name, value in markers.items():
                if isinstance(value, (int, float)):
                    events.append({
                        "event_id": f"event.{bid}.{name}",
                        "type": str(name),
                        "time_s": float(value),
                        "hard": False,
                        "evidence": {"class": "authored", "confidence": 1.0},
                    })
        for c in beat_src.get("hard_constraints") or []:
            constraints.append(make_constraint(c, len(constraints)+1, "hard", shot_id))
        for c in beat_src.get("soft_constraints") or []:
            constraints.append(make_constraint(c, len(constraints)+1, "soft", shot_id))

    # Global constraints.
    for c in resolved.get("hard_constraints") or []:
        constraints.append(make_constraint(c, len(constraints)+1, "hard", shot_id))
    for c in resolved.get("soft_constraints") or []:
        constraints.append(make_constraint(c, len(constraints)+1, "soft", shot_id))

    laban_controls: list[dict[str, Any]] = []
    perf = resolved.get("performance") if isinstance(resolved.get("performance"), dict) else {}
    laban = perf.get("laban") if isinstance(perf.get("laban"), dict) else {}
    for label, spec in laban.items():
        if not isinstance(spec, dict):
            continue
        # Direct Effort map or nested per-beat map.
        if any(k in spec for k in ("weight", "time", "space", "flow")):
            subject = label if label in actor_ids else default_actor
            interval = beat_intervals.get(label, [0.0, duration])
            effort = {k: v for k, v in spec.items() if k in ("weight", "time", "space", "flow") and isinstance(v, dict)}
            if effort:
                laban_controls.append({"subject_ref": subject, "interval": interval, "effort": effort, "status": "authored_descriptor", "evidence": {"class": "authored", "confidence": 1.0}})
        else:
            for sublabel, sub in spec.items():
                if not isinstance(sub, dict) or not any(k in sub for k in ("weight", "time", "space", "flow")):
                    continue
                interval = beat_intervals.get(sublabel, beat_intervals.get(label, [0.0, duration]))
                effort = {k: v for k, v in sub.items() if k in ("weight", "time", "space", "flow") and isinstance(v, dict)}
                laban_controls.append({"subject_ref": label if label in actor_ids else default_actor, "interval": interval, "effort": effort, "status": "authored_descriptor", "evidence": {"class": "authored", "confidence": 1.0}})

    facial_events: list[dict[str, Any]] = []
    face = perf.get("face") if isinstance(perf.get("face"), dict) else {}
    for label, aus in face.items():
        if not isinstance(aus, list):
            continue
        subject = next((aid for aid in actor_ids if label.startswith(aid)), default_actor)
        peaks = [float(x["apex_s"]) for x in aus if isinstance(x, dict) and isinstance(x.get("apex_s"), (int, float))]
        center = sum(peaks)/len(peaks) if peaks else duration/2
        au_out = []
        for au in aus:
            if not isinstance(au, dict) or "au" not in au:
                continue
            item = {"au": str(au["au"]), "side": str(au.get("side", "bilateral"))}
            for k in ("peak", "onset_s", "apex_s", "offset_s"):
                if k in au:
                    item[k] = float(au[k])
            au_out.append(item)
        if au_out:
            facial_events.append({"event_id": f"face.{subject}.{label}", "subject_ref": subject, "interval": [max(0.0, center-0.25), min(duration, center+0.25)], "action_units": au_out, "evidence": {"class": "authored", "confidence": 1.0}})

    breath_tracks: list[dict[str, Any]] = []
    breath = perf.get("breath")
    if isinstance(breath, list):
        grouped: dict[str, list[dict[str, Any]]] = {}
        for event in breath:
            if not isinstance(event, dict) or "type" not in event:
                continue
            subject = str(event.get("subject") or default_actor)
            out = {k: v for k, v in event.items() if k in ("type", "time_s", "interval_s", "audio_ref")}
            if "interval_s" in out:
                out["interval"] = out.pop("interval_s")
            grouped.setdefault(subject, []).append(out)
        for subject, evs in grouped.items():
            breath_tracks.append({"track_id": f"breath.{subject}.authoring", "subject_ref": subject, "interval": [0.0, duration], "events": evs, "evidence": {"class": "authored", "confidence": 1.0}})

    style_transforms: list[dict[str, Any]] = []
    st = resolved.get("style_transform") or resolved.get("style_switch")
    if isinstance(st, dict) and (st.get("target") or st.get("target_profile")):
        style_transforms.append({
            "transform_id": f"transform.{resolved.get('document_id','authoring')}.001",
            "source_profile": str(st.get("source") or st.get("source_profile") or "natural_human"),
            "target_profile": str(st.get("target") or st.get("target_profile")),
            "interval": [0.0, duration],
            "dimensions": copy.deepcopy(st.get("dimensions") or {}),
            "invariants": list(st.get("invariants") or []),
            "evidence": {"class": "authored", "confidence": 1.0},
        })

    verification_src = resolved.get("verification") if isinstance(resolved.get("verification"), dict) else {}
    gates = []
    for gate in verification_src.get("gates") or []:
        if not isinstance(gate, dict) or not all(k in gate for k in ("metric", "operator", "value")):
            unresolved.append("verification gate missing metric/operator/value")
            continue
        gates.append({"metric": str(gate["metric"]), "operator": str(gate["operator"]), "value": gate["value"]})
    metrics = sorted({str(g["metric"]) for g in gates} | {str(x) for x in verification_src.get("recommended_metrics") or []})

    scope = resolved.get("scope") if isinstance(resolved.get("scope"), dict) else {}
    rights = scope.get("rights", "unspecified")
    rights_obj = rights if isinstance(rights, dict) else {"authoring_scope": str(rights)}

    extension_payload = {
        "resolved_authoring": resolved,
        "profile_trace": profile_trace,
        "import_trace": import_trace,
        "unresolved": unresolved,
        "compiler_scope": "reference compiler; no dense motion synthesis",
    }
    candidate: dict[str, Any] = {
        "$schema": "../schemas/CPCS_MX_Schema.json",
        "schema_id": "urn:cpcs-mx:schema:1.0",
        "document_id": str(resolved.get("document_id") or "score.compiled.unnamed"),
        "title": str(shot_src.get("objective") or resolved.get("document_id") or "Compiled CPCS-MX candidate"),
        "safety_scope": str(scope.get("safety") or "unspecified"),
        "rights_scope": rights_obj,
        "timebase": {"canonical": "seconds", "fps": fps, "sample_rate_hz": max(60, fps["numerator"] / fps["denominator"]), "interval_semantics": "half_open"},
        "characters": characters,
        "mannerism_profiles": mannerisms,
        "shots": [{"shot_id": shot_id, "interval": {"start_s": 0.0, "end_s": duration}, "beats": beats}],
        "events": events,
        "laban_controls": laban_controls,
        "facial_events": facial_events,
        "breath_tracks": breath_tracks,
        "style_transforms": style_transforms,
        "secondary_motion": [],
        "constraints": constraints,
        "verification_plan": {"metrics": metrics, "acceptance_gates": gates},
        "capability_report": {"dense_motion_synthesis": "not_implemented", "semantic_mapping": "partial", "unresolved_count": len(unresolved)},
        "provenance": {"compiler": "compile_authoring_yaml.py", "profiles": profile_trace, "imports": import_trace},
        "extensions": {"urn:cpcs-mx:resolved-authoring:1": extension_payload},
    }
    # Pass through secondary systems in a schema-compatible subset.
    for idx, sec in enumerate(resolved.get("secondary_motion") or [], start=1):
        if not isinstance(sec, dict):
            continue
        drivers = sec.get("drivers") or []
        candidate["secondary_motion"].append({
            "system_id": str(sec.get("id") or sec.get("system_id") or f"secondary.{idx:03d}"),
            "type": str(sec.get("type") or "other"),
            "drivers": [str(x) for x in drivers] or [default_actor],
            "solver": str(sec.get("mode") or sec.get("solver") or "authoring_unspecified"),
            "parameters": copy.deepcopy(sec.get("parameters") or {}),
            "art_direction": copy.deepcopy(sec.get("art_direction") or {}),
        })
    return candidate, unresolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Authoring YAML file")
    parser.add_argument("output", type=Path, help="Canonical JSON candidate")
    parser.add_argument("--profiles-root", type=Path, default=Path(__file__).resolve().parents[1] / "profiles")
    parser.add_argument("--authoring-schema", type=Path, default=Path(__file__).resolve().parents[1] / "schemas" / "CPCS_MX_Authoring_Schema.json")
    parser.add_argument("--canonical-schema", type=Path, default=Path(__file__).resolve().parents[1] / "schemas" / "CPCS_MX_Schema.json")
    parser.add_argument("--report", type=Path, help="Optional compilation report JSON")
    parser.add_argument("--allow-unresolved", action="store_true", help="Return success when semantic items remain unresolved")
    args = parser.parse_args()

    source = read_yaml(args.input)
    authoring_schema = read_json(args.authoring_schema)
    authoring_errors = sorted(Draft202012Validator(authoring_schema).iter_errors(source), key=lambda e: list(e.path))
    if authoring_errors:
        for error in authoring_errors:
            print(f"AUTHORING SCHEMA ERROR {list(error.path)}: {error.message}", file=sys.stderr)
        return 2

    body = copy.deepcopy(source["cpcs_mx"])
    profile_trace: list[dict[str, Any]] = []
    merged: dict[str, Any] = {}
    for uri in body.get("extends") or []:
        path = profile_uri_to_path(str(uri), args.profiles_root)
        if not path.exists():
            profile_trace.append({"uri": uri, "status": "missing", "path": str(path)})
            continue
        profile = read_yaml(path)
        defaults = profile.get("defaults") or {}
        merged = deep_merge(merged, defaults)
        profile_trace.append({"uri": uri, "status": "resolved", "path": str(path), "version": profile.get("profile_version"), "sha256": verify_sha256(path, None)})
    merged = deep_merge(merged, body)
    imports, import_trace = load_imports(merged, args.input)
    if imports:
        merged.setdefault("resolved_imports", imports)

    candidate, unresolved = compile_candidate(merged, profile_trace, import_trace)
    canonical_schema = read_json(args.canonical_schema)
    validation_errors = sorted(Draft202012Validator(canonical_schema).iter_errors(candidate), key=lambda e: list(e.path))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = {
        "input": str(args.input),
        "output": str(args.output),
        "profile_trace": profile_trace,
        "import_trace": import_trace,
        "unresolved": unresolved,
        "schema_errors": [{"path": list(e.path), "message": e.message} for e in validation_errors],
        "canonical_valid": not validation_errors,
    }
    report_path = args.report or args.output.with_suffix(".report.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if validation_errors:
        for error in validation_errors:
            print(f"CANONICAL SCHEMA ERROR {list(error.path)}: {error.message}", file=sys.stderr)
        return 3
    if unresolved and not args.allow_unresolved:
        print(f"Compiled valid candidate with {len(unresolved)} unresolved semantic item(s); see {report_path}", file=sys.stderr)
        return 4
    print(f"Wrote {args.output}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
