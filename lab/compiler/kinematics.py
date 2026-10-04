"""Deterministic logic checks for an authored kinematic plan (cpcs.kinematic_plan/1.0).

The external LLM authors coordinates; this module checks that they are physically coherent with
the plan's own declarations. It measures the plan, not a render, and never edits it. Thresholds
come from a named, versioned policy that a plan may override explicitly.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .profiles import REPO_ROOT

POLICY = {
    "version": "cpcs-kinematics/1.0",
    "speed_jump_ratio": 2.5,          # consecutive segment speeds; a larger change needs a force event
    "speed_floor_mps": 0.3,           # ignore ratios between near-still segments
    "force_window_s": 0.11,           # a force event explains a speed change within this distance
    "release_angle_deg": 25.0,        # release direction vs the swing's tangent
    "release_speed_ratio": [0.6, 1.4],
    "swing_extent_tolerance_deg": 45.0,
    "standing_tolerance_m": 0.1,      # hips may sit this much above standing while on the feet
    "crouch_depth_m": 0.15,           # a declared crouch puts the hips at least this far below standing
    "camera_cone_deg": 30.0,
    "max_moves_per_second": 2.0,
}
SUPPORT_PARTS = {"both_feet", "left_foot", "right_foot", "both_hands", "left_hand", "right_hand",
                 "knee", "seat", "back", "side"}
SUPPORT_MANNER = {"static", "step", "skid", "plant", "crouch"}
CONTACT_MODES = {"physical_contact", "near_miss", "release", "staged_near_contact", "occluded"}
FORCE_EVENTS = {"catch", "swing_drive", "release", "touchdown", "push_off", "landing", "impact"}
FRAME_KEYS = ("units", "up", "surface_y", "screen_right", "camera")
FEET = {"both_feet", "left_foot", "right_foot"}


def _point(p: dict) -> tuple[float, float, float]:
    return (p["x"], p["y"], p["z"])


def _at(track: list[dict], t: float) -> tuple[float, float, float] | None:
    for a, b in zip(track, track[1:]):
        if a["t"] <= t <= b["t"] and b["t"] > a["t"]:
            f = (t - a["t"]) / (b["t"] - a["t"])
            return tuple(a[k] + f * (b[k] - a[k]) for k in "xyz")
    if track and track[-1]["t"] == t:
        return _point(track[-1])
    return None


def _support_at(intervals: list[dict], t: float) -> list[dict]:
    return [s for s in intervals if s["from_s"] <= t <= s["to_s"]]


def parse_support(value: str) -> dict[str, Any]:
    """`flight:<reason>`, `held_by:<actor>`, or parts joined by `+` with optional manner words."""
    if value.startswith("flight:"):
        return {"kind": "flight", "reason": value.split(":", 1)[1]}
    if value.startswith("held_by:"):
        return {"kind": "held", "by": value.split(":", 1)[1]}
    parts, manner, unknown = set(), set(), []
    for token in value.split("+"):
        if token in SUPPORT_PARTS:
            parts.add(token)
        elif token in SUPPORT_MANNER or token.startswith("trailing:") and token.split(":", 1)[1] in SUPPORT_PARTS:
            manner.add(token)
        else:
            unknown.append(token)
    return {"kind": "grounded", "parts": parts, "manner": manner, "unknown": unknown}


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    policy = {**POLICY, **plan.get("policy_overrides", {})}
    findings: list[dict[str, Any]] = []

    def find(code: str, message: str, *, t: float | None = None, subject: str | None = None) -> None:
        findings.append({"code": code, "t": t, "subject": subject, "message": message})

    frame = plan.get("frame", {})
    missing = [k for k in FRAME_KEYS if k not in frame]
    if missing:
        find("FRAME_UNDECLARED", "frame lacks " + ", ".join(missing))
    duration = plan["duration_s"]
    bodies = plan["bodies"]
    tracks = plan["tracks"]
    forces = plan.get("force_events", [])
    for event in forces:
        if event["kind"] not in FORCE_EVENTS:
            find("FORCE_EVENT_UNKNOWN", f"force event '{event['kind']}' is not in the approved list", t=event["t"], subject=event.get("actor"))
    support = plan.get("support", {})

    for actor, body in sorted(bodies.items()):
        track = tracks.get(f"{actor}.hips", [])
        standing = body["hip_height_m"]
        for a, b in zip(track, track[1:]):
            if b["t"] < a["t"]:
                find("TIME_ORDER", "keyframes go back in time", t=b["t"], subject=actor)
            elif b["t"] == a["t"] and _point(a) != _point(b):
                find("TELEPORT", f"hips jump {math.dist(_point(a), _point(b)):.2f} m in zero time", t=a["t"], subject=actor)
        segments = [(a["t"], b["t"], math.dist(_point(a), _point(b)) / (b["t"] - a["t"])) for a, b in zip(track, track[1:]) if b["t"] > a["t"]]
        actor_forces = [e["t"] for e in forces if e.get("actor") in (actor, None) or actor in e.get("actors", [])]
        for (t0, t1, v0), (u0, u1, v1) in zip(segments, segments[1:]):
            low, high = min(v0, v1), max(v0, v1)
            if low > policy["speed_floor_mps"] and high / low > policy["speed_jump_ratio"] and not any(abs(t1 - f) <= policy["force_window_s"] for f in actor_forces):
                find("SPEED_JUMP", f"speed {v0:.1f} -> {v1:.1f} m/s with no force event", t=t1, subject=actor)
        intervals = support.get(actor, [])
        if not intervals:
            find("SUPPORT_UNDECLARED", "no support intervals declared", subject=actor)
        else:
            covered = sorted((s["from_s"], s["to_s"]) for s in intervals)
            cursor = 0.0
            for start, end in covered:
                if start > cursor + 1e-9:
                    find("SUPPORT_GAP", f"nothing carries the weight between {cursor} and {start} s", t=cursor, subject=actor)
                cursor = max(cursor, end)
            if cursor < duration - 1e-9:
                find("SUPPORT_GAP", f"nothing carries the weight after {cursor} s", t=cursor, subject=actor)
            for s in intervals:
                parsed = parse_support(s["support"])
                if parsed["kind"] == "grounded" and (parsed["unknown"] or not parsed["parts"]):
                    find("SUPPORT_UNKNOWN", f"'{s['support']}' uses tokens outside the approved support lists", t=s["from_s"], subject=actor)
                if parsed["kind"] == "held" and parsed["by"] not in bodies:
                    find("SUPPORT_UNKNOWN", f"held by undeclared body '{parsed['by']}'", t=s["from_s"], subject=actor)
                if parsed["kind"] == "flight":
                    starts = [e for e in forces if abs(e["t"] - s["from_s"]) <= policy["force_window_s"] and e["kind"] in ("push_off", "release")]
                    ends = [e for e in forces if abs(e["t"] - s["to_s"]) <= policy["force_window_s"] and e["kind"] in ("landing", "touchdown", "catch")]
                    if not starts or not ends:
                        find("FLIGHT_BOUNDS", f"flight '{parsed['reason']}' needs a push_off or release at its start and a landing, touchdown or catch at its end", t=s["from_s"], subject=actor)
        for p in track:
            spans = [parse_support(s["support"]) for s in _support_at(intervals, p["t"])]
            if not spans:
                continue
            grounded = [s for s in spans if s["kind"] == "grounded"]
            if all(s["kind"] == "grounded" for s in spans):
                on_feet = any(s["parts"] & FEET for s in grounded)
                if on_feet and p["y"] > standing + policy["standing_tolerance_m"]:
                    find("SUPPORT_HEIGHT", f"hips at {p['y']:.2f} m are above standing ({standing} m) while on the feet; declare a flight", t=p["t"], subject=actor)
                if any("crouch" in s["manner"] or "skid" in s["manner"] for s in grounded) and p["y"] > standing - policy["crouch_depth_m"]:
                    find("SUPPORT_HEIGHT", f"hips at {p['y']:.2f} m are not crouched below standing ({standing} m)", t=p["t"], subject=actor)
        if plan.get("constraints", {}).get("forbid_flight"):
            airborne = [p["t"] for p in track if p["y"] > standing + policy["standing_tolerance_m"]]
            if any(parse_support(s["support"])["kind"] == "flight" for s in intervals) or airborne:
                find("CONSTRAINT_CONTRADICTION", "constraints forbid flight but the plan flies"
                     + (f" (hips above standing at {airborne} s)" if airborne else ""), subject=actor)

    for contact in plan.get("contacts", []):
        if contact["mode"] not in CONTACT_MODES:
            find("CONTACT_MODE_UNKNOWN", f"contact '{contact['id']}' mode '{contact['mode']}' is not in the approved list", t=contact["start_s"], subject=contact["id"])
        limit = contact.get("max_distance_m")
        by, on = tracks.get(contact.get("by_track", "")), tracks.get(contact.get("on_track", ""))
        if contact["mode"] == "physical_contact" and limit is not None and by and on:
            for p in on:
                if contact["start_s"] <= p["t"] <= contact["end_s"]:
                    q = _at(by, p["t"])
                    if q is not None and math.dist(q, _point(p)) > limit:
                        find("REACH", f"'{contact['id']}' parts are {math.dist(q, _point(p)):.2f} m apart (limit {limit} m)", t=p["t"], subject=contact["id"])

    for swing in plan.get("swings", []):
        held, pivot = tracks[swing["held_track"]], tracks[swing["pivot_track"]]
        pts = [p for p in held if swing["from_s"] <= p["t"] <= swing["to_s"]]
        turn = 0.0
        previous = None
        for p in pts:
            c = _at(pivot, p["t"]) or _point(pivot[-1])
            angle = math.degrees(math.atan2(p["z"] - c[2], p["x"] - c[0]))
            if previous is not None:
                turn += (angle - previous + 180) % 360 - 180
            previous = angle
        if abs(turn - swing["turn_deg"]) > policy["swing_extent_tolerance_deg"]:
            find("SWING_EXTENT", f"held body turns {turn:.0f} deg around the pivot; the plan says {swing['turn_deg']} deg", t=swing["from_s"], subject=swing["held_track"])

    for event in forces:
        if event["kind"] != "release":
            continue
        track = tracks.get(f"{event['actor']}.hips", [])
        earlier = [p for p in track if p["t"] < event["t"]]
        exact = [p for p in track if p["t"] == event["t"]]
        later = [p for p in track if p["t"] > event["t"]]
        if not earlier or not later:
            continue
        arrive = _point(exact[0]) if exact else _at(track, event["t"])
        leave = _point(exact[-1]) if exact else arrive   # a duplicate keyframe at release is the teleport
        a, n = earlier[-1], later[0]
        v_pre = ((arrive[0] - a["x"]) / (event["t"] - a["t"]), (arrive[2] - a["z"]) / (event["t"] - a["t"]))
        v_post = ((n["x"] - leave[0]) / (n["t"] - event["t"]), (n["z"] - leave[2]) / (n["t"] - event["t"]))
        gap = abs((math.degrees(math.atan2(v_post[1], v_post[0]) - math.atan2(v_pre[1], v_pre[0])) + 180) % 360 - 180)
        ratio = math.hypot(*v_post) / max(math.hypot(*v_pre), 1e-9)
        low, high = policy["release_speed_ratio"]
        if gap > policy["release_angle_deg"] or not low <= ratio <= high:
            find("RELEASE", f"leaves {gap:.0f} deg off the swing direction at {ratio:.1f}x its speed", t=event["t"], subject=event["actor"])

    for key in plan.get("camera", []):
        if "look_at" not in key or "pos" not in key:
            find("CAMERA_YAW_ONLY", "camera keyframe lacks position and look_at; aim cannot be checked", t=key["t"])
            continue
        axis = [key["look_at"][i] - key["pos"][i] for i in range(3)]
        for actor in key.get("must_see", []):
            p = _at(tracks.get(f"{actor}.hips", []), key["t"]) or _point(tracks[f"{actor}.hips"][-1])
            to = [p[i] - key["pos"][i] for i in range(3)]
            cos = sum(a * b for a, b in zip(axis, to)) / (math.hypot(*axis) * math.hypot(*to))
            angle = math.degrees(math.acos(max(-1.0, min(1.0, cos))))
            if angle > policy["camera_cone_deg"]:
                find("CAMERA_AIM", f"{actor} is {angle:.0f} deg off the view axis", t=key["t"], subject=actor)

    moves = plan.get("moves", [])
    if moves and len(moves) / duration > policy["max_moves_per_second"]:
        tracked = sum(1 for m in moves if m.get("tracked"))
        find("DENSITY", f"{len(moves)} moves in {duration} s ({tracked} with tracks)")

    findings.sort(key=lambda f: (f["code"], f["t"] if f["t"] is not None else -1, f["subject"] or ""))
    return {"schema": "cpcs.kinematic_report/1.0", "policy": policy["version"],
            "status": "fail" if findings else "pass", "findings": findings}


def check_plan(plan: dict[str, Any], *, root: Path = REPO_ROOT) -> dict[str, Any]:
    """Schema-check a plan, validate its coordinate logic and return a schema-valid report."""
    schemas = root / "lab/compiler/schemas"
    plan_schema = json.loads((schemas / "kinematic_plan.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(plan_schema).iter_errors(plan), key=lambda e: list(e.absolute_path))
    if errors:
        where = "/".join(map(str, errors[0].absolute_path)) or "plan"
        raise ValueError(f"kinematic plan is invalid at {where}: {errors[0].message}")
    report = validate_plan(plan)
    Draft202012Validator(json.loads((schemas / "kinematic_report.schema.json").read_text(encoding="utf-8"))).validate(report)
    return report
