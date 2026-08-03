"""Closed typed merge operators for canonical CPCS fields."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any

MERGE_POLICY_VERSION = "cpcs-typed-merge/1.0"
MERGE_OPERATORS = frozenset(
    {
        "replace",
        "merge_object",
        "merge_by_id",
        "append_ordered",
        "union_set",
        "intersect_set",
        "minimum",
        "maximum",
        "compose_temporal_tracks",
        "reject_on_conflict",
    }
)
ID_KEYS = ("id", "entity_id", "scene_id", "shot_id", "beat_id", "action_id", "interaction_id")


@dataclass(frozen=True)
class MergeOutcome:
    value: Any
    conflict: bool = False


def _canonical_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _item_id(value: Any) -> str:
    if isinstance(value, dict):
        for key in ID_KEYS:
            if key in value and isinstance(value[key], (str, int)):
                return f"{key}:{value[key]}"
    raise ValueError("merge_by_id items require one declared identifier field")


def _require_list(value: Any, operator: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{operator} requires list values")
    return value


def _merge_by_id(current: Any, candidate: Any) -> list[Any]:
    existing = _require_list(current, "merge_by_id")
    incoming = _require_list(candidate, "merge_by_id")
    rows = {_item_id(item): copy.deepcopy(item) for item in existing}
    for item in incoming:
        item_key = _item_id(item)
        if item_key in rows:
            if not isinstance(rows[item_key], dict) or not isinstance(item, dict):
                raise ValueError("merge_by_id identified values must be objects")
            rows[item_key] = {
                **copy.deepcopy(rows[item_key]),
                **copy.deepcopy(item),
            }
        else:
            rows[item_key] = copy.deepcopy(item)
    return [rows[key] for key in sorted(rows)]


def _set_values(values: list[Any]) -> dict[str, Any]:
    return {_canonical_key(value): copy.deepcopy(value) for value in values}


def _compose_temporal_tracks(current: Any, candidate: Any) -> list[Any]:
    combined = [
        *copy.deepcopy(_require_list(current, "compose_temporal_tracks")),
        *copy.deepcopy(_require_list(candidate, "compose_temporal_tracks")),
    ]
    for item in combined:
        if not isinstance(item, dict):
            raise ValueError("compose_temporal_tracks items must be objects")
        if "start_s" not in item:
            raise ValueError("compose_temporal_tracks items require start_s")
    return sorted(
        combined,
        key=lambda item: (
            item["start_s"],
            item.get("end_s", item["start_s"]),
            str(item.get("id", item.get("event_id", item.get("track_id", "")))),
            _canonical_key(item),
        ),
    )


def apply_merge(operator: str, current: Any, candidate: Any) -> MergeOutcome:
    """Apply one declared operator without recursive fallback behavior."""
    if operator not in MERGE_OPERATORS:
        raise ValueError(f"unknown merge operator: {operator}")
    if current is None:
        return MergeOutcome(copy.deepcopy(candidate))
    if operator == "replace":
        return MergeOutcome(copy.deepcopy(candidate))
    if operator == "merge_object":
        if not isinstance(current, dict) or not isinstance(candidate, dict):
            raise ValueError("merge_object requires object values")
        return MergeOutcome({**copy.deepcopy(current), **copy.deepcopy(candidate)})
    if operator == "merge_by_id":
        return MergeOutcome(_merge_by_id(current, candidate))
    if operator == "append_ordered":
        return MergeOutcome(
            [
                *copy.deepcopy(_require_list(current, operator)),
                *copy.deepcopy(_require_list(candidate, operator)),
            ]
        )
    if operator == "union_set":
        values = _set_values(
            [
                *_require_list(current, operator),
                *_require_list(candidate, operator),
            ]
        )
        return MergeOutcome([values[key] for key in sorted(values)])
    if operator == "intersect_set":
        left = _set_values(_require_list(current, operator))
        right = _set_values(_require_list(candidate, operator))
        return MergeOutcome([left[key] for key in sorted(set(left) & set(right))])
    if operator in {"minimum", "maximum"}:
        if isinstance(current, bool) and isinstance(candidate, bool):
            value = current and candidate if operator == "minimum" else current or candidate
            return MergeOutcome(value)
        if isinstance(current, bool) or isinstance(candidate, bool):
            raise ValueError(f"{operator} cannot mix booleans and numbers")
        if not isinstance(current, (int, float)) or not isinstance(candidate, (int, float)):
            raise ValueError(f"{operator} requires numeric or boolean values")
        return MergeOutcome(
            min(current, candidate) if operator == "minimum" else max(current, candidate)
        )
    if operator == "compose_temporal_tracks":
        return MergeOutcome(_compose_temporal_tracks(current, candidate))
    if _canonical_key(current) == _canonical_key(candidate):
        return MergeOutcome(copy.deepcopy(current))
    return MergeOutcome(None, conflict=True)
