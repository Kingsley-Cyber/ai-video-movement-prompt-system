"""Validate authored scene decisions and project them into existing score overlays."""

from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any

from lab.second_brain.src.validate import REPO_ROOT, sha256_value

from .build import load_capability
from .merge import ID_KEYS
from .score import validate_overlay

SCENE_PATHS = ("scenes", "entities", "beats", "actions", "interactions", "shots")
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
            relative = {
                "anchor": anchor["baseline"]["item"],
                "quality": anchor["baseline"]["quality"],
                **anchor["change"],
            }
            if "relative" not in item:
                item["relative"] = relative
            elif item["relative"] != relative:
                previous = item["relative"] if isinstance(item["relative"], list) else [item["relative"]]
                if relative not in previous:
                    item["relative"] = [*previous, relative]
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
            "values": content, "locks": sorted({d["target"]["path"] for d in decisions if d["lock"] and d["target"]["path"] in content}), "source_refs": sources,
        })
    return overlays


def scene_completeness(scene: dict[str, list]) -> dict[str, Any]:
    missing = [path for path in ("scenes", "entities", "beats", "actions") if not scene[path]]
    return {
        "directed": not missing,
        "counts": {path: len(scene[path]) for path in SCENE_PATHS if path != "shots"},
        "missing": missing,
    }


def provider_fit(scene: dict[str, list], root: Path = REPO_ROOT, model: str = "veo-3.1-generate-001") -> dict[str, Any]:
    capability, _ = load_capability(root, model=model)
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

    def quantities(value: Any, index: int, path: str) -> None:
        if isinstance(value, dict):
            if "scale" in value and "value" in value:
                scale, amount = value["scale"], value["value"]
                if not isinstance(scale, dict) or any(type(scale.get(k)) not in (int, float) or not math.isfinite(scale[k]) for k in ("min", "max")) or type(amount) not in (int, float) or not math.isfinite(amount) or not scale["min"] <= amount <= scale["max"] or scale["min"] == scale["max"]:
                    reject("quantity_out_of_scale", index, path, "A numeric quality must fit its explicitly declared nonempty scale.")
                if not isinstance(value.get("visible"), str) or not value["visible"].strip():
                    reject("quantity_without_visible_wording", index, path, "Keep numeric truth and supply visible relative wording for prose.")
            for key, child in value.items():
                quantities(child, index, path + "." + key)
        elif isinstance(value, list):
            for child in value:
                quantities(child, index, path)

    slots = {s["sublayer_id"]: s["target_path"] for s in pass_spec["sublayers"]}
    complete = "steering" in packet
    spec_id = pass_spec["pass_id"]
    assigned: dict[tuple[str, str], set[str]] = {}
    for index, decision in enumerate(decisions):
        target, values = decision["target"], decision["values"]
        path = target["path"]
        if complete:
            quantities(values, index, path)
        owned = decision.get("pass_id", decision["layer"]) == spec_id
        if (owned and slots.get(decision["sublayer"]) != path) or path not in SCENE_PATHS:
            reject("path_not_allowed", index, path, "The target must match this pass's sublayer.")
        if owned and complete:
            slot = next((s for s in pass_spec["sublayers"] if s["sublayer_id"] == decision["sublayer"]), {})
            if "fields" in slot and not set(values) <= set(slot["fields"]):
                reject("field_not_allowed", index, path, "Fields must belong to this pass's declared sublayer.")
            if pass_spec["reads"] and not decision["inputs"]:
                reject("missing_upstream_input", index, "inputs", "A creative stack must name the accepted choices it uses.")
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
    if complete:
        total = sum(len(items) for items in scene.values())
        if len(all_items) != total:
            reject("ambiguous_item_id", None, "scene", "Item ids must be unique across scene collections.")
        for path, fields in (("scenes", ("duration_s", "location")), ("entities", ("name", "kind")), ("actions", ("actor", "beat", "verb"))):
            for item in scene[path]:
                if any(not item.get(field) for field in fields):
                    reject("missing_scene_field", None, path, "Scene items need explicit " + ", ".join(fields) + ".")
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
            if complete and baseline is not None:
                quality = anchor["baseline"]["quality"]
                established = {"speed": ("pace", "speed", "effort_time"), "intensity": ("reaction", "effort_weight", "intensity")}
                if not any(key in baseline for key in established.get(quality, (quality,))):
                    reject("anchor_quality_missing", index, target["path"] + ".relative", "The earlier item must establish the compared quality.")
                before, after = baseline.get(quality), item.get(quality)
                if isinstance(before, dict) and isinstance(after, dict) and "scale" in before and "scale" in after:
                    if before["scale"] != after["scale"]:
                        reject("relative_scale_mismatch", index, target["path"], "Compare quantities on the same declared scale.")
                    elif type(before.get("value")) in (int, float) and type(after.get("value")) in (int, float):
                        delta = after["value"] - before["value"]
                        if (anchor["change"]["direction"] == "more" and delta <= 0) or (anchor["change"]["direction"] == "less" and delta >= 0):
                            reject("relative_direction_mismatch", index, target["path"], "The declared relative direction must match the numeric change.")
        if complete and target["path"] == "interactions" and item.get("kind") == "contact":
            if any(not item.get(field) for field in ("action", "contact_surface", "reaction", "settle")):
                reject("contact_missing_response", index, "interactions", "Contact must name its action, surface, reaction and settle.")
        if complete and target["path"] == "shots":
            if item.get("shows_initiation") is False and not item.get("occlusion_reason"):
                reject("camera_hides_initiation", index, "shots", "Hidden initiation needs an explicit creative reason.")
            if "end_beat" in item and (item.get("beat") not in beats or item["end_beat"] not in beats or beats[item["end_beat"]]["order"] < beats[item["beat"]]["order"]):
                reject("invalid_shot_range", index, "shots", "Shot end must name the same or a later beat.")
    prop_errors, _ = prop_hand_ledger(scene)
    errors.extend(prop_errors)
    try:
        for overlay in overlays_from_decisions(decisions, "directing_session_" + "0" * 24, sha256_value(decisions)):
            validate_overlay(overlay, root)
    except ValueError as exc:
        reject("overlay_invalid", None, "overlays", str(exc))
    return errors


def prop_hand_ledger(scene: dict[str, list]) -> tuple[list[dict], dict[str, dict]]:
    """Replay declared prop state, needs and changes; never infer them from prose.

    Snapshots are disposable views of canonical scene data, not another authority.
    Existing scenes without these declarations retain their original behavior.
    """
    actions = scene["actions"]
    if not any("prop_state" in e for e in scene["entities"]) and not any(
        "needs" in a or "changes" in a for a in actions
    ):
        return [], {}
    errors: list[dict] = []
    states: dict[str, dict] = {}
    retired: set[str] = set()
    snapshots: dict[str, dict] = {}

    def reject(code: str, path: str, message: str) -> None:
        errors.append(dict(code=code, decision_index=None, path=path, message=message))

    normalized: dict[str, list] = {}
    for path in ("entities", "actions", "beats"):
        normalized[path] = []
        for item in scene[path]:
            identity = next((item[k] for k in ID_KEYS if k in item), None)
            if not isinstance(identity, str):
                reject("PROP_STATE_INVALID", path, "Ledger items need an existing canonical identity.")
                return errors, {}
            normalized[path].append({**item, "id": identity})
    entities = {item["id"]: item for item in normalized["entities"]}
    actions = normalized["actions"]

    def hands_valid(value: Any) -> bool:
        return isinstance(value, list) and all(h in ("left", "right") for h in value) and len(set(value)) == len(value)

    def state_valid(value: Any, path: str) -> bool:
        if not isinstance(value, dict) or set(value) != {"state", "location", "held_by", "hands"}:
            reject("PROP_STATE_INVALID", path, "Prop state needs state, location, held_by and hands only.")
            return False
        if not isinstance(value["state"], str) or not value["state"].strip():
            reject("PROP_STATE_INVALID", path, "Name the authored object state.")
        if not isinstance(value["location"], str) or not value["location"].strip():
            reject("PROP_VANISHED", path, "Keep an explicit location, including when off screen.")
        holder = value["held_by"]
        if holder is not None and (not isinstance(holder, str) or holder not in entities):
            reject("unknown_reference", path, "The holder must name a declared entity.")
        if not hands_valid(value["hands"]) or (holder is None) != (value["hands"] == []):
            reject("PROP_STATE_INVALID", path, "A held prop names its left/right hands; an unheld prop has none.")
        return not errors

    def occupancy(values: dict[str, dict], path: str) -> dict[tuple[str, str], str]:
        occupied: dict[tuple[str, str], str] = {}
        for obj, state in sorted(values.items()):
            for hand in state["hands"]:
                key = (state["held_by"], hand)
                if key in occupied:
                    reject("HAND_OCCUPIED", path, f"{key[0]}'s {hand} hand already holds {occupied[key]}.")
                occupied[key] = obj
        return occupied

    for obj, entity in sorted(entities.items()):
        if "prop_state" in entity:
            value = entity["prop_state"]
            if state_valid(value, "entities." + obj + ".prop_state"):
                if value["state"] == "broken":
                    reject("PIECE_IDENTITY", "entities." + obj, "Initialize the named pieces instead of a broken whole.")
                states[obj] = copy.deepcopy(value)
    if errors:
        return errors, {}
    occupancy(states, "entities.prop_state")
    beat_ids = {beat["id"] for beat in normalized["beats"]}
    for action in actions:
        if action.get("beat") not in beat_ids:
            reject("unknown_reference", "actions." + action["id"], "Ledger actions need a declared beat.")
        actor = action.get("actor")
        if not isinstance(actor, str) or actor not in entities:
            reject("unknown_reference", "actions." + action["id"], "Ledger actions need a declared actor.")
    if errors:
        return errors, {}

    for beat in sorted(normalized["beats"], key=lambda b: (b.get("order", 0), b["id"])):
        events = [a for a in actions if a.get("beat") == beat["id"]]
        orders = [a.get("order") for a in events]
        if any(type(n) is not int or n < 1 for n in orders) or len(set(orders)) != len(orders):
            reject("PROP_SEQUENCE_UNRESOLVED", "beats." + beat["id"], "Ledger actions require explicit, distinct orders within their beat.")
            return errors, {}
        for action in sorted(events, key=lambda a: a["order"]):
            path = "actions." + action["id"]
            occupied = occupancy(states, path)
            needs, changes = action.get("needs", []), action.get("changes", [])
            if not isinstance(needs, list) or not isinstance(changes, list):
                reject("PROP_STATE_INVALID", path, "needs and changes must be lists.")
                return errors, {}
            for need in needs:
                if not isinstance(need, dict) or not need or not set(need) <= {"object", "state", "location", "held_by", "hands"}:
                    reject("PROP_STATE_INVALID", path + ".needs", "A need names an object state or free hands.")
                    continue
                if "hands" in need and not hands_valid(need["hands"]):
                    reject("PROP_STATE_INVALID", path + ".needs", "Name distinct left/right hands.")
                    continue
                obj = need.get("object")
                if obj is None:
                    if set(need) != {"hands"} or not need["hands"]:
                        reject("PROP_STATE_INVALID", path + ".needs", "A free-hand need contains only nonempty hands.")
                        continue
                    for hand in need["hands"]:
                        if (action.get("actor"), hand) in occupied:
                            reject("HAND_OCCUPIED", path + ".needs", "Free-hand action requires release of the held object first.")
                    continue
                if not isinstance(obj, str) or obj not in states or obj in retired:
                    reject("PROP_STATE_CONFLICT", path + ".needs", "Use a live prop with established state, or name its piece.")
                    continue
                if any(states[obj].get(k) != v for k, v in need.items() if k not in ("object", "hands")):
                    reject("PROP_STATE_CONFLICT", path + ".needs", "The required state disagrees with the previous action's result.")
                for hand in need.get("hands", []):
                    if occupied.get((action.get("actor"), hand)) != obj:
                        reject("HAND_OCCUPIED", path + ".needs", "The requested hand must already hold this object.")
            if errors:
                return errors, {}
            updated = copy.deepcopy(states)
            changed: set[str] = set()
            for change in changes:
                if not isinstance(change, dict) or not set(change) <= {"object", "state", "location", "held_by", "hands", "pieces"}:
                    reject("PROP_STATE_INVALID", path + ".changes", "A change contains object state fields or a break with pieces.")
                    continue
                obj = change.get("object")
                if not isinstance(obj, str) or obj not in states or obj in retired:
                    reject("PROP_STATE_CONFLICT", path + ".changes", "Change a live initialized prop, not a retired whole.")
                    continue
                if obj in changed or set(change) == {"object"}:
                    reject("PROP_STATE_INVALID", path + ".changes", "Each object has one explicit resulting change per action.")
                    continue
                changed.add(obj)
                value = {**updated[obj], **{k: v for k, v in change.items() if k not in ("object", "pieces")}}
                if change.get("state") == "broken":
                    pieces = change.get("pieces")
                    if not isinstance(pieces, list) or not pieces:
                        reject("PIECE_IDENTITY", path + ".changes", "A break names the new pieces and their complete states.")
                        continue
                    value.update(held_by=None, hands=[])
                    for piece in pieces:
                        piece_id = piece.get("object") if isinstance(piece, dict) else None
                        if not isinstance(piece_id, str) or piece_id not in entities or piece_id in updated or piece_id in retired:
                            reject("PIECE_IDENTITY", path + ".changes.pieces", "Each piece must have a distinct declared entity identity.")
                            continue
                        piece_state = {k: v for k, v in piece.items() if k != "object"}
                        if state_valid(piece_state, path + ".changes.pieces"):
                            updated[piece_id] = copy.deepcopy(piece_state)
                    retired.add(obj)
                elif "pieces" in change:
                    reject("PIECE_IDENTITY", path + ".changes", "Only a declared break creates pieces.")
                if state_valid(value, path + ".changes"):
                    updated[obj] = value
            if errors:
                return errors, {}
            occupancy(updated, path + ".changes")
            if errors:
                return errors, {}
            states = updated
        snapshots[beat["id"]] = {obj: copy.deepcopy(state) for obj, state in sorted(states.items()) if obj not in retired}
    return errors, snapshots
