"""Deterministic knowledge-validity filtering and supersession lineage."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable


TEMPORAL_POLICY = {
    "version": "cpcs-temporal/1.0",
    "current_semantics": "open_ended_active_head",
    "historical_interval": "valid_from_inclusive_valid_until_exclusive",
}
VALIDITY_MODES = frozenset({"current", "historical", "all_versions"})
IMPLICIT_VALIDITY = {
    "valid_from": None,
    "valid_until": None,
    "status": "active",
    "supersedes": [],
    "superseded_by": [],
}


def parse_timestamp(value: str) -> datetime:
    """Parse an offset-aware ISO 8601 timestamp."""
    if not isinstance(value, str) or not value:
        raise ValueError("temporal timestamp must be a non-empty string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid temporal timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"temporal timestamp must include an offset: {value}")
    return parsed


def validity_of(record: dict[str, Any]) -> dict[str, Any]:
    """Return an owned copy of explicit or timeless active validity."""
    value = record.get("validity")
    if value is None:
        return {**IMPLICIT_VALIDITY}
    return {
        "valid_from": value.get("valid_from"),
        "valid_until": value.get("valid_until"),
        "status": value.get("status"),
        "supersedes": sorted(value.get("supersedes", [])),
        "superseded_by": sorted(value.get("superseded_by", [])),
    }


def validate_temporal_request(validity_mode: str, as_of: str | None) -> None:
    if validity_mode not in VALIDITY_MODES:
        raise ValueError(f"unknown validity_mode: {validity_mode}")
    if validity_mode == "historical" and as_of is None:
        raise ValueError("historical validity_mode requires as_of")
    if validity_mode != "historical" and as_of is not None:
        raise ValueError("as_of is accepted only with historical validity_mode")
    if as_of is not None:
        parse_timestamp(as_of)


def is_visible(
    record: dict[str, Any],
    validity_mode: str = "current",
    as_of: str | None = None,
) -> bool:
    validate_temporal_request(validity_mode, as_of)
    if validity_mode == "all_versions":
        return True
    validity = validity_of(record)
    if validity_mode == "current":
        return (
            validity["status"] == "active"
            and validity["valid_until"] is None
            and not validity["superseded_by"]
        )
    instant = parse_timestamp(as_of or "")
    starts = validity["valid_from"]
    ends = validity["valid_until"]
    return (
        (starts is None or parse_timestamp(starts) <= instant)
        and (ends is None or instant < parse_timestamp(ends))
    )


def visible_records(
    records: Iterable[dict[str, Any]],
    validity_mode: str = "current",
    as_of: str | None = None,
) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if is_visible(record, validity_mode, as_of)
    ]


def validate_temporal_collections(
    collections: dict[str, list[dict[str, Any]]],
) -> dict[str, int]:
    """Validate reciprocal, same-store, acyclic replacement chains."""
    located: dict[str, tuple[str, dict[str, Any]]] = {}
    explicit = 0
    for store, records in collections.items():
        for record in records:
            record_id = record["id"]
            if record_id in located:
                raise ValueError(f"temporal ID repeats across stores: {record_id}")
            located[record_id] = (store, record)
            if "validity" not in record:
                continue
            explicit += 1
            validity = validity_of(record)
            starts = validity["valid_from"]
            ends = validity["valid_until"]
            if starts is not None:
                parse_timestamp(starts)
            if ends is not None:
                parse_timestamp(ends)
            if starts is not None and ends is not None:
                if parse_timestamp(ends) <= parse_timestamp(starts):
                    raise ValueError(f"{record_id}: valid_until must be after valid_from")
            if validity["status"] == "active" and (
                ends is not None or validity["superseded_by"]
            ):
                raise ValueError(f"{record_id}: active record cannot be closed or superseded")
            if validity["status"] == "superseded" and (
                ends is None or len(validity["superseded_by"]) != 1
            ):
                raise ValueError(f"{record_id}: superseded record needs one successor and valid_until")
            if validity["status"] == "deprecated" and ends is None:
                raise ValueError(f"{record_id}: deprecated record needs valid_until")
            if set(validity["supersedes"]) & set(validity["superseded_by"]):
                raise ValueError(f"{record_id}: replacement directions overlap")

    for record_id, (store, record) in located.items():
        validity = validity_of(record)
        for predecessor_id in validity["supersedes"]:
            target = located.get(predecessor_id)
            if target is None or target[0] != store:
                raise ValueError(f"{record_id}: supersedes missing same-store record {predecessor_id}")
            predecessor = validity_of(target[1])
            if record_id not in predecessor["superseded_by"]:
                raise ValueError(f"{record_id}: non-reciprocal predecessor {predecessor_id}")
            if (
                predecessor["valid_until"] is not None
                and validity["valid_from"] is not None
                and predecessor["valid_until"] != validity["valid_from"]
            ):
                raise ValueError(
                    f"{record_id}: valid_from must equal {predecessor_id} valid_until"
                )
        for successor_id in validity["superseded_by"]:
            target = located.get(successor_id)
            if target is None or target[0] != store:
                raise ValueError(f"{record_id}: successor missing same-store record {successor_id}")
            if record_id not in validity_of(target[1])["supersedes"]:
                raise ValueError(f"{record_id}: non-reciprocal successor {successor_id}")

    state: dict[str, str] = {}

    def visit(record_id: str, stack: list[str]) -> None:
        if state.get(record_id) == "done":
            return
        if state.get(record_id) == "visiting":
            start = stack.index(record_id)
            raise ValueError("supersession cycle: " + " -> ".join(stack[start:] + [record_id]))
        state[record_id] = "visiting"
        stack.append(record_id)
        for successor in validity_of(located[record_id][1])["superseded_by"]:
            visit(successor, stack)
        stack.pop()
        state[record_id] = "done"

    for record_id in sorted(located):
        visit(record_id, [])
    return {"records": len(located), "explicit_validity": explicit}


def replacement_trace(
    record_id: str,
    records: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    by_id = {record["id"]: record for record in records}
    if record_id not in by_id:
        raise ValueError(f"replacement trace record is missing: {record_id}")

    def walk(start: str, direction: str) -> list[str]:
        visited: set[str] = set()
        frontier = list(validity_of(by_id[start])[direction])
        result: list[str] = []
        while frontier:
            current = frontier.pop(0)
            if current in visited or current not in by_id:
                continue
            visited.add(current)
            result.append(current)
            frontier.extend(validity_of(by_id[current])[direction])
            frontier = sorted(set(frontier) - visited)
        return result

    predecessors = walk(record_id, "supersedes")
    successors = walk(record_id, "superseded_by")
    current_candidates = [
        item
        for item in [record_id, *successors]
        if is_visible(by_id[item], "current", None)
    ]
    return {
        "selected_id": record_id,
        "selected_validity": validity_of(by_id[record_id]),
        "predecessors": predecessors,
        "successors": successors,
        "current_head": current_candidates[-1] if current_candidates else None,
        "policy_version": TEMPORAL_POLICY["version"],
    }
