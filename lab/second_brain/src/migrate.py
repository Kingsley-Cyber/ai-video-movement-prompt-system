"""One-time, cross-tier migration for legacy authored relationships and render rows."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from .validate import (
    REPO_ROOT,
    ValidationFailure,
    content_hash,
    read_jsonl,
    sha256_value,
    validate_curated,
    validate_immutable,
    validate_instance,
    write_json,
    write_jsonl,
)


def _file_sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _relationship_sources(card: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"ref": source, "locator": None} for source in card.get("source", [])]


def _migrate_relationships(root: Path) -> dict[str, Any]:
    concept_path = root / "lab" / "concepts.jsonl"
    edge_path = root / "lab" / "second_brain" / "curated" / "edges.jsonl"
    cards = read_jsonl(concept_path)
    existing_edges = read_jsonl(edge_path)
    if existing_edges or not any("pairs_with" in card or "conflicts" in card for card in cards):
        raise ValidationFailure("relationship migration already applied or target is not empty")
    before_ids = [card["id"] for card in cards]
    before_sources = {card["id"]: card.get("source", []) for card in cards}
    raw: list[tuple[str, str, str, list[dict[str, Any]]]] = []
    for card in cards:
        for target in card.get("pairs_with", []):
            raw.append((card["id"], target, "pairs_with", _relationship_sources(card)))
        for target in card.get("conflicts", []):
            raw.append((card["id"], target, "conflicts_with", _relationship_sources(card)))
    unique = sorted(
        {
            (u, v, edge_type, json.dumps(sources, sort_keys=True))
            for u, v, edge_type, sources in raw
        }
    )
    edges = [
        {
            "id": f"edge_{index:06d}",
            "u": u,
            "v": v,
            "type": edge_type,
            "context": "all",
            "authored_by": "legacy_migration",
            "note": "Migrated without semantic change from the concept card relationship field.",
            "sources": json.loads(sources),
        }
        for index, (u, v, edge_type, sources) in enumerate(unique, 1)
    ]
    migrated_cards = [
        {
            key: value
            for key, value in card.items()
            if key not in {"pairs_with", "conflicts"}
        }
        for card in cards
    ]
    write_jsonl(concept_path, migrated_cards)
    write_jsonl(edge_path, edges)
    after_cards = read_jsonl(concept_path)
    if [card["id"] for card in after_cards] != before_ids:
        raise ValidationFailure("concept IDs changed during relationship migration")
    if {card["id"]: card.get("source", []) for card in after_cards} != before_sources:
        raise ValidationFailure("concept source references changed during relationship migration")
    return {
        "concepts_before": len(cards),
        "concepts_after": len(after_cards),
        "relationship_refs_before": len(raw),
        "authored_edges_after": len(edges),
        "duplicate_relationship_refs_collapsed": len(raw) - len(edges),
        "concept_ids_preserved": True,
        "source_references_preserved": True,
        "concepts_before_sha256": sha256_value(cards),
        "concepts_after_sha256": sha256_value(after_cards),
    }


def _migrate_runs(root: Path) -> dict[str, Any]:
    immutable = root / "lab" / "second_brain" / "immutable"
    flights_path = immutable / "flights.jsonl"
    runs_path = immutable / "runs.jsonl"
    if read_jsonl(flights_path) or read_jsonl(runs_path):
        raise ValidationFailure("legacy run migration target is not empty")
    registry = yaml.safe_load((root / "lab" / "registry.yaml").read_text())
    variants = {item["id"]: item for item in registry.get("variants", [])}
    legacy_rows = list(csv.DictReader((root / "lab" / "runs" / "results.csv").open()))
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    flights: list[dict[str, Any]] = []
    runs: list[dict[str, Any]] = []
    prior: str | None = None
    for row in legacy_rows:
        variant = variants[row["variant_id"]]
        model_version = row["model"] or "legacy-unrecorded"
        paradigm = (
            variant.get("control_paradigm")
            or variant.get("lever_tags", {}).get("control_paradigm")
            or "descriptive_prose"
        )
        intent_class = (
            variant.get("domain")
            or variant.get("lever_tags", {}).get("domain")
            or "legacy-unrecorded"
        )
        prompt_hash = _file_sha(root / "lab" / variant["prompt_file"])
        recorded_at = f"{row['date']}T00:00:00Z"
        flight = {
            "id": f"flight_legacy_{row['run_id']}",
            "status": "sealed",
            "intent_id": None,
            "intent_class": intent_class,
            "arms": [
                {
                    "id": row["variant_id"],
                    "variant_id": row["variant_id"],
                    "paradigm": paradigm,
                }
            ],
            "concept_ids": [],
            "concept_content_hashes": {},
            "provider": "legacy-unrecorded",
            "model_version": model_version,
            "seed": int(row["seed"]) if row["seed"] else None,
            "compiler_settings": {"version": "legacy-unrecorded"},
            "sealed_at": recorded_at,
            "legacy": {"source": "lab/runs/results.csv", "date_precision": "day"},
        }
        flight["flight_hash"] = content_hash(flight, ("flight_hash",))
        validate_instance("flight", flight, root)
        flights.append(flight)
        metrics = {
            key: int(row[key])
            for key in ("realism", "skin", "motion", "adherence")
            if row.get(key)
        }
        run = {
            "id": row["run_id"],
            "flight_id": flight["id"],
            "flight_hash": flight["flight_hash"],
            "intent_id": None,
            "intent_class": intent_class,
            "arm": row["variant_id"],
            "paradigm": paradigm,
            "concept_ids": [],
            "concept_content_hashes": {},
            "provider": "legacy-unrecorded",
            "model_version": model_version,
            "seed": int(row["seed"]) if row["seed"] else None,
            "compiled_prompt_hash": prompt_hash,
            "compiler_version": "legacy-unrecorded",
            "repository_commit": revision,
            "output_artifact_hash": None,
            "metrics": metrics,
            "verdict": row["verdict"],
            "recorded_at": recorded_at,
            "prior_record_hash": prior,
            "legacy": {"source_row": row},
        }
        run["record_hash"] = content_hash(run)
        validate_instance("run", run, root)
        prior = run["record_hash"]
        runs.append(run)
    write_jsonl(flights_path, flights)
    write_jsonl(runs_path, runs)
    return {
        "legacy_rows_before": len(legacy_rows),
        "sealed_flights_after": len(flights),
        "immutable_runs_after": len(runs),
        "run_ids_preserved": [row["run_id"] for row in legacy_rows]
        == [run["id"] for run in runs],
        "legacy_rows_sha256": sha256_value(legacy_rows),
        "immutable_runs_sha256": sha256_value(runs),
        "unknown_fields_preserved_as_unknown": [
            "provider",
            "seed",
            "compiler_version",
            "output_artifact_hash",
            "intent_id",
            "concept_ids",
        ],
    }


def upgrade_flight_hash_contract(root: Path = REPO_ROOT) -> dict[str, Any]:
    """Add sealed concept hashes and rechain legacy runs without changing meaning."""
    immutable = root / "lab" / "second_brain" / "immutable"
    flights_path = immutable / "flights.jsonl"
    runs_path = immutable / "runs.jsonl"
    flights_before = read_jsonl(flights_path)
    runs_before = read_jsonl(runs_path)
    concepts = {
        row["id"]: row for row in read_jsonl(root / "lab" / "concepts.jsonl")
    }
    flights_after: list[dict[str, Any]] = []
    for original in flights_before:
        flight = dict(original)
        flight["concept_content_hashes"] = {
            concept_id: sha256_value(concepts[concept_id])
            for concept_id in flight.get("concept_ids", [])
        }
        flight["flight_hash"] = content_hash(flight, ("flight_hash",))
        validate_instance("flight", flight, root)
        flights_after.append(flight)
    flight_by_id = {row["id"]: row for row in flights_after}
    runs_after: list[dict[str, Any]] = []
    prior: str | None = None
    for original in runs_before:
        run = dict(original)
        flight = flight_by_id[run["flight_id"]]
        run["flight_hash"] = flight["flight_hash"]
        run["concept_ids"] = flight["concept_ids"]
        run["concept_content_hashes"] = flight["concept_content_hashes"]
        run["prior_record_hash"] = prior
        run["record_hash"] = content_hash(run)
        validate_instance("run", run, root)
        prior = run["record_hash"]
        runs_after.append(run)
    if [row["id"] for row in flights_before] != [
        row["id"] for row in flights_after
    ]:
        raise ValidationFailure("flight IDs changed during hash-contract upgrade")
    if [row["id"] for row in runs_before] != [row["id"] for row in runs_after]:
        raise ValidationFailure("run IDs changed during hash-contract upgrade")
    write_jsonl(flights_path, flights_after)
    write_jsonl(runs_path, runs_after)
    validation = validate_immutable(root)
    report_path = root / "lab" / "second_brain" / "MIGRATION_REPORT.json"
    report = json.loads(report_path.read_text())
    contract_report = {
        "flight_count_before": len(flights_before),
        "flight_count_after": len(flights_after),
        "run_count_before": len(runs_before),
        "run_count_after": len(runs_after),
        "flight_ids_preserved": True,
        "run_ids_preserved": True,
        "meaning_fields_changed": False,
        "flights_before_sha256": sha256_value(flights_before),
        "flights_after_sha256": sha256_value(flights_after),
        "runs_before_sha256": sha256_value(runs_before),
        "runs_after_sha256": sha256_value(runs_after),
        "immutable_validation": validation,
    }
    report["flight_hash_contract_upgrade"] = contract_report
    write_json(report_path, report)
    return contract_report


def migrate_existing(root: Path = REPO_ROOT) -> dict[str, Any]:
    report = {
        "migration": "second_brain_v1",
        "source_revision": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "relationships": _migrate_relationships(root),
        "legacy_runs": _migrate_runs(root),
    }
    report["curated_validation"] = validate_curated(root)
    report["immutable_validation"] = validate_immutable(root)
    write_json(root / "lab" / "second_brain" / "MIGRATION_REPORT.json", report)
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("migrate-existing", "upgrade-flight-hash-contract"),
    )
    args = parser.parse_args(argv)
    if args.command == "migrate-existing":
        print(json.dumps(migrate_existing(), indent=2, sort_keys=True))
    else:
        print(
            json.dumps(
                upgrade_flight_hash_contract(),
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
