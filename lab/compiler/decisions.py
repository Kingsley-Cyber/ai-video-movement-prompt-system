"""Validate authored scene decisions and project them into existing score overlays."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from lab.second_brain.src.validate import REPO_ROOT, sha256_value

from .build import load_capability
from .score import validate_overlay

SCENE_PATHS = ("scenes", "entities", "beats", "actions", "interactions")
IDENTITY_KEYS = {"id", "entity_id", "scene_id", "shot_id", "beat_id", "action_id", "interaction_id"}
LEDGER_KEYS = {
    "decision_id", "pass_id", "layer", "sublayer", "inputs", "relative_anchor",
    "justification", "source_status", "evidence_uses", "lock", "sequence", "revision_of",
}


def scene_from_decisions(decisions: list[dict[str, Any]]) -> dict[str, list]:
    """A scene-content view; acceptance and provenance stay in the decision ledger."""
    groups: dict[str, dict[str, dict]] = {path: {} for path in SCENE_PATHS}
    for decision in decisions:
        target = decision["target"]
        if target["path"] not in groups:
            continue
        item = groups[target["path"]].setdefault(target["item_id"], {"id": target["item_id"]})
        item.update(copy.deepcopy(decision["values"]))
        anchor = decision.get("relative_anchor")
        if anchor is not None:
            item["relative"] = {
                "anchor": anchor["baseline"]["item"],
                "quality": anchor["baseline"]["quality"],
                **anchor["change"],
            }
    return {
        path: sorted(items.values(), key=lambda item: (item.get("order", 0), item["id"]))
        for path, items in groups.items()
    }


def overlays_from_decisions(
    decisions: list[dict[str, Any]], session_id: str, ledger_hash: str
) -> list[dict[str, Any]]:
    scene = scene_from_decisions(decisions)
    suffix = sha256_value({"session_id": session_id, "ledger_hash": ledger_hash})[7:19]
    sources = sorted({
        "directing-session://" + session_id, "directing-ledger://" + ledger_hash,
        *(use["id"] for d in decisions for use in d["evidence_uses"] if use["kind"] == "concept"),
    })
    overlays = []
    if scene["scenes"]:
        overlays.append({
            "overlay_id": "overlay_direct_user_" + suffix,
            "scope": "explicit_user_correction", "priority": 0,
            "values": {"scenes": scene["scenes"]},
            "locks": ["scenes"] if any(
                d["lock"] and d["target"]["path"] == "scenes" for d in decisions
            ) else [],
            "source_refs": sources,
        })
    content = {path: items for path, items in scene.items() if path != "scenes" and items}
    if content:
        overlays.append({
            "overlay_id": "overlay_direct_scene_" + suffix,
            "scope": "scene_override", "priority": 0,
            "values": content, "locks": [], "source_refs": sources,
        })
    return overlays


def scene_completeness(scene: dict[str, list]) -> dict[str, Any]:
    missing = [path for path in ("scenes", "entities", "beats", "actions") if not scene[path]]
    return {
        "directed": not missing,
        "counts": {path: len(scene[path]) for path in SCENE_PATHS},
        "missing": missing,
    }


def provider_fit(scene: dict[str, list], root: Path = REPO_ROOT) -> dict[str, Any]:
    capability, _ = load_capability(root)
    duration = scene["scenes"][0].get("duration_s") if scene["scenes"] else None
    supported = capability["durations_seconds"]
    status = "unspecified" if duration is None else "supported" if duration in supported else "unsupported"
    options = []
    if status == "unsupported":
        options = [
            f"Split into clips of at most {max(supported)} seconds.",
            "Select a provider whose reviewed capability supports the requested duration.",
            "Ask the owner to shorten the scene.",
        ]
    return {
        "capability_id": capability["capability_id"],
        "requested_duration_s": duration, "supported_durations_s": supported,
        "status": status, "options": options,
    }


def validate_decisions(
    decisions: list[dict[str, Any]],
    pass_spec: dict[str, Any],
    packet: dict[str, Any],
    *,
    root: Path = REPO_ROOT,
) -> list[dict[str, Any]]:
    """Return all semantic rejections without changing the proposal or accepted state."""
    errors: list[dict[str, Any]] = []

    def reject(code: str, index: int | None, path: str, message: str) -> None:
        errors.append({"code": code, "decision_index": index, "path": path, "message": message})

    slots = {s["sublayer_id"]: s["target_path"] for s in pass_spec["sublayers"]}
    assigned: dict[tuple[str, str], set[str]] = {}
    for index, decision in enumerate(decisions):
        target, values = decision["target"], decision["values"]
        path = target["path"]
        if slots.get(decision["sublayer"]) != path or path not in SCENE_PATHS:
            reject("path_not_allowed", index, path, "The target must match this pass's sublayer.")
        if IDENTITY_KEYS.intersection(values):
            reject("identity_key_not_allowed", index, path, "Identity belongs only in target.item_id; references use actor, target, beat and action.")
        if LEDGER_KEYS.intersection(values) or "relative" in values:
            reject("scene_values_not_allowed", index, path, "Decision bookkeeping and relative anchors belong in their declared ledger fields.")
        key = (path, target["item_id"])
        seen = assigned.setdefault(key, set())
        overlap = seen.intersection(values)
        if overlap:
            reject("duplicate_value_key", index, path, "Decisions targeting one item must have disjoint values: " + ", ".join(sorted(overlap)))
        seen.update(values)
        if "order" in values and (type(values["order"]) is not int or values["order"] < 1):
            reject("invalid_scene_value", index, path, "An explicit order must be a positive integer.")
        for field in ("min_s", "duration_s"):
            if field in values and (
                type(values[field]) not in (int, float) or values[field] <= 0
            ):
                reject("invalid_scene_value", index, path, field + " must be positive seconds.")
    if errors:
        return errors

    scene = scene_from_decisions(decisions)
    entities = {item["id"] for item in scene["entities"]}
    beats = {item["id"]: item for item in scene["beats"]}
    actions = {item["id"]: item for item in scene["actions"]}
    all_items = {
        item["id"]: item for items in scene.values() for item in items
    }
    beat_orders = [item.get("order") for item in scene["beats"]]
    if beat_orders != list(range(1, len(beat_orders) + 1)):
        reject("beats_not_contiguous", None, "beats", "Beat order must be 1..n without gaps or repeats.")
    requested = packet["constraints"]["requested_duration_s"]
    duration = scene["scenes"][0].get("duration_s") if scene["scenes"] else None
    if requested is not None and duration != requested:
        reject("duration_mismatch", None, "scenes", "Keep the requested duration; provider fit cannot silently shorten it.")
    minimums = [beat.get("min_s") for beat in scene["beats"]]
    if any(type(value) not in (int, float) or value <= 0 for value in minimums):
        reject("invalid_scene_value", None, "beats", "Each beat needs positive min_s.")
    elif duration is not None and sum(minimums) > duration:
        reject("beats_exceed_duration", None, "beats", "The minimum readable beat times exceed the scene's duration.")

    def beat_order(item: dict | None) -> int | None:
        if item is None:
            return None
        if item["id"] in beats:
            return item.get("order")
        return beats.get(item.get("beat"), {}).get("order")

    for index, decision in enumerate(decisions):
        target = decision["target"]
        item = all_items[target["item_id"]]
        for field, collection in (
            ("actor", entities), ("target", entities), ("beat", beats), ("action", actions),
        ):
            if field in decision["values"] and (
                not isinstance(item[field], str) or item[field] not in collection
            ):
                reject("unknown_reference", index, target["path"] + "." + field, "Reference must name an accepted scene item of the declared kind.")
        cause_id = decision["values"].get("caused_by")
        if cause_id is not None:
            cause = actions.get(cause_id) if isinstance(cause_id, str) else None
            own_action = actions.get(item.get("action")) if target["path"] == "interactions" else item
            own_order = own_action.get("order") if own_action else None
            if cause is None or type(own_order) is not int or type(cause.get("order")) is not int or cause["order"] >= own_order:
                reject("effect_before_cause", index, target["path"] + ".caused_by", "A cause must name an action ordered before the effect.")
        anchor = decision["relative_anchor"]
        if anchor is not None:
            baseline = all_items.get(anchor["baseline"]["item"])
            baseline_order, current_order = beat_order(baseline), beat_order(item)
            if baseline_order is None or current_order is None or baseline_order >= current_order:
                reject("anchor_not_earlier", index, target["path"] + ".relative", "The baseline must exist on an earlier beat.")
    try:
        for overlay in overlays_from_decisions(decisions, "directing_session_" + "0" * 24, sha256_value(decisions)):
            validate_overlay(overlay, root)
    except ValueError as exc:
        reject("overlay_invalid", None, "overlays", str(exc))
    return errors
