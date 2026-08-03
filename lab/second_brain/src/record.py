"""Append-only APIs for sealed flights, runs, and evidence observations."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .validate import (
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    canonical_json_bytes,
    content_hash,
    read_jsonl,
    sha256_value,
    validate_instance,
)

KIND_TO_FILE = {
    "run": "runs.jsonl",
    "pegasus_observation": "pegasus_observations.jsonl",
    "measurement_observation": "measurement_observations.jsonl",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def seal_flight(draft: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    """Seal and append a flight. Draft editing happens outside the immutable store."""
    path = root / "lab" / "second_brain" / "immutable" / "flights.jsonl"
    assert_write_target("record", path, root)
    rows = read_jsonl(path)
    if any(row["id"] == draft.get("id") for row in rows):
        raise ValidationFailure(f"immutable flight ID already exists: {draft.get('id')}")
    flight = dict(draft)
    flight["status"] = "sealed"
    flight.setdefault("sealed_at", _utc_now())
    concepts = {
        row["id"]: row for row in read_jsonl(root / "lab" / "concepts.jsonl")
    }
    concept_ids = flight.get("concept_ids", [])
    missing = sorted(set(concept_ids) - set(concepts))
    if missing:
        raise ValidationFailure(
            "flight references missing concepts: " + ", ".join(missing)
        )
    flight["concept_content_hashes"] = {
        concept_id: sha256_value(concepts[concept_id])
        for concept_id in concept_ids
    }
    if flight.get("legacy") is None:
        compiler_version = flight.get("compiler_settings", {}).get("version")
        if (
            flight.get("seed") is None
            or not compiler_version
            or "legacy-unrecorded"
            in {
                flight.get("provider"),
                flight.get("model_version"),
                compiler_version,
            }
        ):
            raise ValidationFailure(
                "nonlegacy flight must seal a seed and exact provider, model, and compiler versions"
            )
    flight["flight_hash"] = content_hash(flight, ("flight_hash",))
    validate_instance("flight", flight, root)
    with path.open("ab") as handle:
        handle.write(canonical_json_bytes(flight))
    return flight


def append_record(kind: str, record: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    """Append one hash-chained record. Replacement and deletion are intentionally absent."""
    if kind not in KIND_TO_FILE:
        raise ValidationFailure(f"unsupported immutable record kind: {kind}")
    path = root / "lab" / "second_brain" / "immutable" / KIND_TO_FILE[kind]
    assert_write_target("record", path, root)
    rows = read_jsonl(path)
    if any(row["id"] == record.get("id") for row in rows):
        raise ValidationFailure(f"immutable record ID already exists: {record.get('id')}")
    value = dict(record)
    value["prior_record_hash"] = rows[-1]["record_hash"] if rows else None
    if kind == "run":
        value.setdefault("recorded_at", _utc_now())
    else:
        value.setdefault("created_at", _utc_now())
    value["record_hash"] = content_hash(value)
    validate_instance(kind, value, root)
    with path.open("ab") as handle:
        handle.write(canonical_json_bytes(value))
    return value


def append_run(record: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    flights = {row["id"]: row for row in read_jsonl(root / "lab" / "second_brain" / "immutable" / "flights.jsonl")}
    flight = flights.get(record.get("flight_id"))
    if not flight:
        raise ValidationFailure(f"run references unsealed flight: {record.get('flight_id')}")
    if record.get("flight_hash") != flight["flight_hash"]:
        raise ValidationFailure("run flight_hash does not match sealed flight")
    locked = {
        "intent_id": flight["intent_id"],
        "intent_class": flight["intent_class"],
        "concept_ids": flight["concept_ids"],
        "concept_content_hashes": flight["concept_content_hashes"],
        "provider": flight["provider"],
        "model_version": flight["model_version"],
        "seed": flight["seed"],
    }
    mismatches = [
        key for key, expected in locked.items() if record.get(key) != expected
    ]
    compiler_version = flight["compiler_settings"].get("version")
    if compiler_version is not None and record.get("compiler_version") != compiler_version:
        mismatches.append("compiler_version")
    arms = {arm["id"]: arm for arm in flight["arms"]}
    arm = arms.get(record.get("arm"))
    if arm is None:
        mismatches.append("arm")
    elif record.get("paradigm") != arm["paradigm"]:
        mismatches.append("paradigm")
    if mismatches:
        raise ValidationFailure(
            "run differs from sealed flight fields: "
            + ", ".join(sorted(set(mismatches)))
        )
    if record.get("legacy") is None and (
        record.get("seed") is None
        or record.get("output_artifact_hash") is None
        or "legacy-unrecorded"
        in {
            record.get("provider"),
            record.get("model_version"),
            record.get("compiler_version"),
        }
    ):
        raise ValidationFailure(
            "nonlegacy run must record seed, output hash, and exact versions"
        )
    return append_record("run", record, root)


def append_pegasus_observation(record: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    if record.get("evidence_class") not in {"inferred", "interpreted"}:
        raise ValidationFailure("Pegasus semantic evidence must be inferred or interpreted")
    return append_record("pegasus_observation", record, root)


def append_measurement_observation(record: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    return append_record("measurement_observation", record, root)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("seal-flight", "run", "pegasus", "measurement"):
        item = sub.add_parser(command)
        item.add_argument("record", type=Path, help="JSON object file")
    args = parser.parse_args(argv)
    value = json.loads(args.record.read_text())
    if args.command == "seal-flight":
        result = seal_flight(value)
    elif args.command == "run":
        result = append_run(value)
    elif args.command == "pegasus":
        result = append_pegasus_observation(value)
    else:
        result = append_measurement_observation(value)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
