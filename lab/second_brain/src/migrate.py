"""One-time, cross-tier migration for legacy authored relationships and render rows."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import timezone
from pathlib import Path
from typing import Any

import yaml

from .authority import authority_writer
from .curation_journal import apply_curated_transaction, recover_curated_transactions
from .graph import AUTHORED_EDGE_POLICY, validate_edge_distribution
from .temporal import parse_timestamp, validity_of, visible_records
from .validate import (
    REPO_ROOT,
    ValidationFailure,
    canonical_json_bytes,
    content_hash,
    read_jsonl,
    sha256_value,
    validate_curated,
    validate_immutable,
    validate_instance,
    write_json,
    write_jsonl,
)


RECIPROCAL_EDGE_MIGRATION = "reciprocal_pairs_with_consolidation/1.0"
REVIEWED_EDGE_RECLASSIFICATION = "reviewed_edge_reclassification/1.0"
RECLASSIFICATION_TYPES = frozenset(AUTHORED_EDGE_POLICY["types"]) - {
    "pairs_with"
}
RECLASSIFICATION_PREDECESSOR_TYPES = frozenset(AUTHORED_EDGE_POLICY["types"])


def _file_sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _relationship_sources(card: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"ref": source, "locator": None} for source in card.get("source", [])]


def _canonical_utc(value: str) -> str:
    return (
        parse_timestamp(value)
        .astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _reciprocal_groups(
    edges: list[dict[str, Any]],
) -> list[tuple[tuple[str, str, str], list[dict[str, Any]]]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for edge in visible_records(edges):
        if edge["type"] != "pairs_with":
            continue
        u, v = sorted((edge["u"], edge["v"]))
        grouped.setdefault((u, v, edge["context"]), []).append(edge)
    reciprocal = []
    for key, rows in sorted(grouped.items()):
        if len(rows) == 1:
            continue
        directions = {(row["u"], row["v"]) for row in rows}
        if len(rows) != 2 or len(directions) != 2:
            raise ValidationFailure(
                "pairs_with consolidation requires exactly two inverse records for "
                + "::".join(key)
            )
        if any(
            row.get("authored_by") != "legacy_migration"
            or row.get("context") != "all"
            for row in rows
        ):
            raise ValidationFailure(
                "pairs_with consolidation accepts only reciprocal legacy_migration records: "
                + "::".join(key)
            )
        reciprocal.append((key, sorted(rows, key=lambda row: row["id"])))
    return reciprocal


def _source_union(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_value = {
        json.dumps(source, sort_keys=True, separators=(",", ":")): source
        for row in rows
        for source in row["sources"]
    }
    return [by_value[key] for key in sorted(by_value)]


def _migration_report(root: Path) -> tuple[Path, dict[str, Any]]:
    path = root / "lab" / "second_brain" / "MIGRATION_REPORT.json"
    if not path.exists():
        return path, {"migration": "second_brain_v1"}
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise ValidationFailure("migration report is not valid JSON") from error
    if not isinstance(value, dict):
        raise ValidationFailure("migration report must be an object")
    return path, value


@authority_writer("migration")
def consolidate_reciprocal_edges(
    effective_at: str,
    curated_by: str,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Replace reciprocal legacy associations with lineage-linked symmetric heads."""
    if not isinstance(curated_by, str) or not curated_by or len(curated_by) > 128:
        raise ValidationFailure("curator ID must be a bounded non-empty string")
    effective = _canonical_utc(effective_at)
    recover_curated_transactions(root)
    edge_path = root / "lab" / "second_brain" / "curated" / "edges.jsonl"
    edges_before = read_jsonl(edge_path)
    groups = _reciprocal_groups(edges_before)
    report_path, report = _migration_report(root)
    existing_report = report.get("reciprocal_edge_consolidation")
    if not groups:
        validate_curated(root)
        if isinstance(existing_report, dict):
            if existing_report.get("effective_at") != effective:
                raise ValidationFailure(
                    "reciprocal edge migration already used a different effective timestamp"
                )
            return {"status": "no_change", **existing_report}
        successors = [
            edge
            for edge in edges_before
            if edge.get("provenance", {}).get("migration")
            == RECIPROCAL_EDGE_MIGRATION
        ]
        if successors:
            predecessor_ids = sorted(
                predecessor
                for edge in successors
                for predecessor in validity_of(edge)["supersedes"]
            )
            if any(
                edge.get("provenance", {}).get("effective_at") != effective
                for edge in successors
            ):
                raise ValidationFailure(
                    "reciprocal edge lineage uses a different effective timestamp"
                )
            recovered_report = {
                "migration": RECIPROCAL_EDGE_MIGRATION,
                "effective_at": effective,
                "curated_by": curated_by,
                "reciprocal_groups": len(successors),
                "predecessor_edges_superseded": len(predecessor_ids),
                "successor_edges_created": len(successors),
                "predecessor_ids_preserved": all(
                    any(edge["id"] == predecessor for edge in edges_before)
                    for predecessor in predecessor_ids
                ),
                "semantic_edge_type_changed": False,
                "raw_edges_after": len(edges_before),
                "current_distribution_after": validate_edge_distribution(
                    visible_records(edges_before)
                ),
                "edges_after_sha256": sha256_value(edges_before),
                "transaction": None,
                "report_recovered_from_curated_lineage": True,
            }
            report["reciprocal_edge_consolidation"] = recovered_report
            report["curated_validation"] = validate_curated(root)
            write_json(report_path, report)
            return {"status": "no_change", **recovered_report}
        return {
            "status": "no_change",
            "migration": RECIPROCAL_EDGE_MIGRATION,
            "effective_at": effective,
            "reciprocal_groups": 0,
        }

    maximum_id = max(
        (int(edge["id"].removeprefix("edge_")) for edge in edges_before),
        default=0,
    )
    updates: dict[str, dict[str, Any]] = {}
    successors: list[dict[str, Any]] = []
    for offset, ((u, v, context), predecessors) in enumerate(groups, 1):
        successor_id = f"edge_{maximum_id + offset:06d}"
        predecessor_ids = [row["id"] for row in predecessors]
        for predecessor in predecessors:
            prior_validity = validity_of(predecessor)
            if prior_validity["valid_from"] is not None and (
                parse_timestamp(prior_validity["valid_from"])
                >= parse_timestamp(effective)
            ):
                raise ValidationFailure(
                    f"{predecessor['id']}: migration timestamp must follow valid_from"
                )
            updates[predecessor["id"]] = {
                **predecessor,
                "validity": {
                    **prior_validity,
                    "valid_until": effective,
                    "status": "superseded",
                    "superseded_by": [successor_id],
                },
            }
        successors.append(
            {
                "id": successor_id,
                "u": u,
                "v": v,
                "type": "pairs_with",
                "context": context,
                "authored_by": curated_by,
                "note": (
                    "Consolidated reciprocal legacy records into one symmetric "
                    "association without changing edge meaning."
                ),
                "sources": _source_union(predecessors),
                "provenance": {
                    "migration": RECIPROCAL_EDGE_MIGRATION,
                    "effective_at": effective,
                    "predecessor_ids": predecessor_ids,
                    "semantic_change": False,
                },
                "validity": {
                    "valid_from": effective,
                    "valid_until": None,
                    "status": "active",
                    "supersedes": predecessor_ids,
                    "superseded_by": [],
                },
            }
        )
    edges_after = [updates.get(edge["id"], edge) for edge in edges_before]
    edges_after.extend(successors)
    operation_id = (
        "reciprocal-pairs-with:"
        + sha256_value(
            {
                "migration": RECIPROCAL_EDGE_MIGRATION,
                "effective_at": effective,
                "curated_by": curated_by,
                "predecessor_ids": sorted(updates),
                "edges_before_sha256": sha256_value(edges_before),
            }
        ).removeprefix("sha256:")
    )
    transaction = apply_curated_transaction(
        root,
        operation="consolidate_reciprocal_edges",
        operation_id=operation_id,
        updates={edge_path: b"".join(canonical_json_bytes(row) for row in edges_after)},
    )
    validation = validate_curated(root)
    current_after = visible_records(read_jsonl(edge_path))
    migration_result = {
        "migration": RECIPROCAL_EDGE_MIGRATION,
        "effective_at": effective,
        "curated_by": curated_by,
        "reciprocal_groups": len(groups),
        "predecessor_edges_superseded": len(updates),
        "successor_edges_created": len(successors),
        "predecessor_ids_preserved": True,
        "semantic_edge_type_changed": False,
        "source_references_preserved": all(
            {
                json.dumps(source, sort_keys=True, separators=(",", ":"))
                for predecessor in predecessors
                for source in predecessor["sources"]
            }
            == {
                json.dumps(source, sort_keys=True, separators=(",", ":"))
                for source in successor["sources"]
            }
            for (_, predecessors), successor in zip(groups, successors)
        ),
        "raw_edges_before": len(edges_before),
        "current_edges_before": len(visible_records(edges_before)),
        "raw_edges_after": len(edges_after),
        "current_distribution_after": validate_edge_distribution(current_after),
        "successor_id_range": [successors[0]["id"], successors[-1]["id"]],
        "edges_before_sha256": sha256_value(edges_before),
        "edges_after_sha256": sha256_value(edges_after),
        "transaction": transaction,
        "curated_validation": validation,
    }
    report["reciprocal_edge_consolidation"] = migration_result
    report["curated_validation"] = validation
    write_json(report_path, report)
    return {"status": "applied", **migration_result}


def _reviewed_successor(
    predecessor: dict[str, Any],
    decision: dict[str, Any],
    edges_by_id: dict[str, dict[str, Any]],
    review: dict[str, Any],
    review_hash: str,
) -> dict[str, Any] | None:
    validity = validity_of(predecessor)
    if validity["status"] == "active":
        return None
    successors = validity["superseded_by"]
    if validity["status"] != "superseded" or len(successors) != 1:
        raise ValidationFailure(
            f"{predecessor['id']}: reviewed edge predecessor is not active or singly superseded"
        )
    successor = edges_by_id.get(successors[0])
    if successor is None:
        raise ValidationFailure(
            f"{predecessor['id']}: reviewed edge successor is missing"
        )
    provenance = successor.get("provenance", {})
    expected = {
        "migration": REVIEWED_EDGE_RECLASSIFICATION,
        "effective_at": _canonical_utc(review["effective_at"]),
        "review_id": review["review_id"],
        "review_hash": review_hash,
        "reviewed_at": _canonical_utc(review["reviewed_at"]),
        "reviewed_by": review["reviewed_by"],
        "predecessor_id": predecessor["id"],
        "predecessor_hash": decision["predecessor_hash"],
        "semantic_change": True,
        "source_verified": True,
        "relationship_validated": True,
    }
    if any(provenance.get(key) != value for key, value in expected.items()):
        raise ValidationFailure(
            f"{predecessor['id']}: existing successor does not match this exact review"
        )
    if (
        successor["u"] != decision["new_u"]
        or successor["v"] != decision["new_v"]
        or successor["type"] != decision["new_type"]
        or successor["context"] != predecessor["context"]
        or successor["sources"] != decision["evidence"]
        or successor.get("note") != decision["rationale"]
    ):
        raise ValidationFailure(
            f"{predecessor['id']}: existing successor content differs from reviewed decision"
        )
    return successor


def _matches_reviewed_predecessor_hash(
    predecessor: dict[str, Any],
    expected_hash: str,
) -> bool:
    """Match the reviewed active bytes, including after their validity was closed."""
    validity = validity_of(predecessor)
    if validity["status"] == "active":
        return sha256_value(predecessor) == expected_hash
    if validity["status"] != "superseded":
        return False
    restored = {
        **predecessor,
        "validity": {
            **validity,
            "valid_until": None,
            "status": "active",
            "superseded_by": [],
        },
    }
    candidate_hashes = {sha256_value(restored)}
    if validity["valid_from"] is None and not validity["supersedes"]:
        timeless = {key: value for key, value in predecessor.items() if key != "validity"}
        candidate_hashes.add(sha256_value(timeless))
    return expected_hash in candidate_hashes


def _validate_edge_retype_review(
    review: dict[str, Any],
    curated_by: str,
    root: Path,
) -> tuple[str, str]:
    validate_instance("edge_retype_review", review, root)
    if review["reviewed_by"] != curated_by:
        raise ValidationFailure(
            "reviewed edge curator must match the exact reviewed_by identity"
        )
    decisions = review["decisions"]
    predecessor_ids = [row["predecessor_id"] for row in decisions]
    if predecessor_ids != sorted(predecessor_ids):
        raise ValidationFailure(
            "reviewed edge decisions must be sorted by predecessor_id"
        )
    if len(predecessor_ids) != len(set(predecessor_ids)):
        raise ValidationFailure("reviewed edge decisions repeat a predecessor")
    effective = _canonical_utc(review["effective_at"])
    reviewed_at = _canonical_utc(review["reviewed_at"])
    if parse_timestamp(reviewed_at) > parse_timestamp(effective):
        raise ValidationFailure("reviewed_at cannot follow effective_at")
    return effective, sha256_value(review)


@authority_writer("migration")
def reclassify_reviewed_edges(
    review: dict[str, Any],
    curated_by: str,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Supersede exact reviewed authored edges with typed successor edges."""
    if not isinstance(curated_by, str) or not curated_by or len(curated_by) > 128:
        raise ValidationFailure("curator ID must be a bounded non-empty string")
    effective, review_hash = _validate_edge_retype_review(
        review, curated_by, root
    )
    recover_curated_transactions(root)
    edge_path = root / "lab" / "second_brain" / "curated" / "edges.jsonl"
    edges_before = read_jsonl(edge_path)
    edges_by_id = {edge["id"]: edge for edge in edges_before}
    if len(edges_by_id) != len(edges_before):
        raise ValidationFailure("authored edge IDs are not unique")
    prior_review_hashes = {
        edge.get("provenance", {}).get("review_hash")
        for edge in edges_before
        if edge.get("provenance", {}).get("migration")
        == REVIEWED_EDGE_RECLASSIFICATION
        and edge.get("provenance", {}).get("review_id") == review["review_id"]
    }
    prior_review_hashes.discard(None)
    if prior_review_hashes and prior_review_hashes != {review_hash}:
        raise ValidationFailure(
            "reviewed edge review_id is already bound to different content"
        )

    pending: list[tuple[dict[str, Any], dict[str, Any]]] = []
    replayed: list[dict[str, Any]] = []
    for decision in review["decisions"]:
        predecessor = edges_by_id.get(decision["predecessor_id"])
        if predecessor is None:
            raise ValidationFailure(
                f"{decision['predecessor_id']}: reviewed predecessor is missing"
            )
        prior_validity = validity_of(predecessor)
        if not _matches_reviewed_predecessor_hash(
            predecessor, decision["predecessor_hash"]
        ):
            raise ValidationFailure(
                f"{predecessor['id']}: reviewed predecessor hash is stale"
            )
        if predecessor["type"] not in RECLASSIFICATION_PREDECESSOR_TYPES:
            raise ValidationFailure(
                f"{predecessor['id']}: predecessor is not an authored edge type"
            )
        if decision["new_type"] not in RECLASSIFICATION_TYPES:
            raise ValidationFailure(
                f"{predecessor['id']}: unsupported reviewed edge type"
            )
        if {decision["new_u"], decision["new_v"]} != {
            predecessor["u"],
            predecessor["v"],
        }:
            raise ValidationFailure(
                f"{predecessor['id']}: reviewed endpoints must preserve the predecessor pair"
            )
        if (
            decision["new_type"] == predecessor["type"]
            and decision["new_u"] == predecessor["u"]
            and decision["new_v"] == predecessor["v"]
        ):
            raise ValidationFailure(
                f"{predecessor['id']}: reviewed decision must change relationship semantics"
            )
        if decision["evidence"] != predecessor["sources"]:
            raise ValidationFailure(
                f"{predecessor['id']}: reviewed evidence must exactly preserve predecessor sources"
            )
        if prior_validity["valid_from"] is not None and (
            parse_timestamp(prior_validity["valid_from"])
            >= parse_timestamp(effective)
        ):
            raise ValidationFailure(
                f"{predecessor['id']}: review effective_at must follow valid_from"
            )
        successor = _reviewed_successor(
            predecessor,
            decision,
            edges_by_id,
            review,
            review_hash,
        )
        if successor is None:
            pending.append((predecessor, decision))
        else:
            replayed.append(successor)

    if pending and replayed:
        raise ValidationFailure(
            "reviewed edge batch is partially applied; recovery or manual audit is required"
        )
    if replayed:
        validation = validate_curated(root)
        replay_result = {
            "status": "no_change",
            "migration": REVIEWED_EDGE_RECLASSIFICATION,
            "review_id": review["review_id"],
            "review_hash": review_hash,
            "effective_at": effective,
            "curated_by": curated_by,
            "predecessor_ids": [row["predecessor_id"] for row in review["decisions"]],
            "successor_ids": [row["id"] for row in replayed],
            "semantic_edge_type_changed": True,
        }
        report_path, report = _migration_report(root)
        history = report.setdefault("reviewed_edge_reclassifications", [])
        if not isinstance(history, list):
            raise ValidationFailure(
                "migration report reviewed_edge_reclassifications must be a list"
            )
        matching = [
            row
            for row in history
            if isinstance(row, dict)
            and row.get("review_id") == review["review_id"]
        ]
        if any(row.get("review_hash") != review_hash for row in matching):
            raise ValidationFailure(
                "migration report review_id is bound to different content"
            )
        if not matching:
            history.append(
                {
                    **{key: value for key, value in replay_result.items() if key != "status"},
                    "source_references_preserved": True,
                    "raw_edges_after": len(edges_before),
                    "current_distribution_after": validate_edge_distribution(
                        visible_records(edges_before)
                    ),
                    "edges_after_sha256": sha256_value(edges_before),
                    "transaction": None,
                    "report_recovered_from_curated_lineage": True,
                }
            )
            report["curated_validation"] = validation
            write_json(report_path, report)
        return replay_result

    maximum_id = max(
        (int(edge["id"].removeprefix("edge_")) for edge in edges_before),
        default=0,
    )
    updates: dict[str, dict[str, Any]] = {}
    successors: list[dict[str, Any]] = []
    for offset, (predecessor, decision) in enumerate(pending, 1):
        successor_id = f"edge_{maximum_id + offset:06d}"
        prior_validity = validity_of(predecessor)
        updates[predecessor["id"]] = {
            **predecessor,
            "validity": {
                **prior_validity,
                "valid_until": effective,
                "status": "superseded",
                "superseded_by": [successor_id],
            },
        }
        successor = {
            "id": successor_id,
            "u": decision["new_u"],
            "v": decision["new_v"],
            "type": decision["new_type"],
            "context": predecessor["context"],
            "authored_by": curated_by,
            "note": decision["rationale"],
            "sources": decision["evidence"],
            "provenance": {
                "migration": REVIEWED_EDGE_RECLASSIFICATION,
                "effective_at": effective,
                "review_id": review["review_id"],
                "review_hash": review_hash,
                "reviewed_at": _canonical_utc(review["reviewed_at"]),
                "reviewed_by": review["reviewed_by"],
                "predecessor_id": predecessor["id"],
                "predecessor_hash": decision["predecessor_hash"],
                "semantic_change": True,
                "source_verified": decision["source_verified"],
                "relationship_validated": decision["relationship_validated"],
            },
            "validity": {
                "valid_from": effective,
                "valid_until": None,
                "status": "active",
                "supersedes": [predecessor["id"]],
                "superseded_by": [],
            },
        }
        validate_instance("edge", successor, root)
        successors.append(successor)

    edges_after = [updates.get(edge["id"], edge) for edge in edges_before]
    edges_after.extend(successors)
    validate_edge_distribution(visible_records(edges_after))
    operation_id = (
        "reviewed-edge-reclassification:"
        + sha256_value(
            {
                "migration": REVIEWED_EDGE_RECLASSIFICATION,
                "review_hash": review_hash,
                "edges_before_sha256": sha256_value(edges_before),
            }
        ).removeprefix("sha256:")
    )
    transaction = apply_curated_transaction(
        root,
        operation="reclassify_reviewed_edges",
        operation_id=operation_id,
        updates={edge_path: b"".join(canonical_json_bytes(row) for row in edges_after)},
    )
    validation = validate_curated(root)
    current_after = visible_records(read_jsonl(edge_path))
    result = {
        "migration": REVIEWED_EDGE_RECLASSIFICATION,
        "review_id": review["review_id"],
        "review_hash": review_hash,
        "effective_at": effective,
        "curated_by": curated_by,
        "predecessor_ids": [row["id"] for row, _ in pending],
        "successor_ids": [row["id"] for row in successors],
        "semantic_edge_type_changed": True,
        "source_references_preserved": all(
            predecessor["sources"] == successor["sources"]
            for (predecessor, _), successor in zip(pending, successors)
        ),
        "raw_edges_before": len(edges_before),
        "raw_edges_after": len(edges_after),
        "current_distribution_after": validate_edge_distribution(current_after),
        "edges_before_sha256": sha256_value(edges_before),
        "edges_after_sha256": sha256_value(edges_after),
        "transaction": transaction,
        "curated_validation": validation,
    }
    report_path, report = _migration_report(root)
    history = report.setdefault("reviewed_edge_reclassifications", [])
    if not isinstance(history, list):
        raise ValidationFailure(
            "migration report reviewed_edge_reclassifications must be a list"
        )
    history.append(result)
    report["curated_validation"] = validation
    write_json(report_path, report)
    return {"status": "applied", **result}


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


@authority_writer("migration")
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


@authority_writer("migration")
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
        choices=(
            "migrate-existing",
            "upgrade-flight-hash-contract",
            "consolidate-reciprocal-edges",
            "reclassify-reviewed-edges",
        ),
    )
    parser.add_argument("--review")
    parser.add_argument("--effective-at")
    parser.add_argument("--by")
    args = parser.parse_args(argv)
    if args.command == "migrate-existing":
        print(json.dumps(migrate_existing(), indent=2, sort_keys=True))
    elif args.command == "upgrade-flight-hash-contract":
        print(
            json.dumps(
                upgrade_flight_hash_contract(),
                indent=2,
                sort_keys=True,
            )
        )
    elif args.command == "consolidate-reciprocal-edges":
        if not args.effective_at or not args.by:
            parser.error(
                "consolidate-reciprocal-edges requires --effective-at and --by"
            )
        print(
            json.dumps(
                consolidate_reciprocal_edges(args.effective_at, args.by),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        if not args.review or not args.by:
            parser.error(
                "reclassify-reviewed-edges requires --review and --by"
            )
        review_path = Path(args.review).expanduser().resolve()
        try:
            review = json.loads(review_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            parser.error(f"review file is unreadable: {exc}")
        print(
            json.dumps(
                reclassify_reviewed_edges(review, args.by),
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
