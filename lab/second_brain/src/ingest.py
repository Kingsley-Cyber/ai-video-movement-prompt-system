"""Resumable batch-ingestion boundary for external knowledge sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .authority import authority_reader, authority_writer
from .providers.polymath import configuration_status
from .validate import (
    EXTERNAL_PROPOSAL_ORIGINS,
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    canonical_json_bytes,
    read_jsonl,
    validate_manifest_row,
    validate_instance,
    write_jsonl,
)

@authority_writer("staging")
def upsert_manifest(rows: list[dict[str, Any]], root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    path = root / "lab" / "second_brain" / "staging" / "corpus_manifest.jsonl"
    assert_write_target("polymath", path, root)
    existing = {row["corpus_item_id"]: row for row in read_jsonl(path)}
    for row in rows:
        validate_manifest_row(row)
        existing[row["corpus_item_id"]] = row
    ordered = [existing[key] for key in sorted(existing)]
    by_version: dict[str, list[dict[str, Any]]] = {}
    for row in ordered:
        by_version.setdefault(row["sha256_or_source_version"], []).append(row)
    for matches in by_version.values():
        if len(matches) < 2:
            continue
        canonical = min(row["corpus_item_id"] for row in matches)
        for row in matches:
            if row["corpus_item_id"] != canonical:
                row["duplicate_of"] = canonical
            else:
                row.pop("duplicate_of", None)
    write_jsonl(path, ordered)
    return ordered


@authority_writer("staging")
def stage_proposal(
    proposal: dict[str, Any],
    root: Path = REPO_ROOT,
    distillation_run_id: str | None = None,
) -> dict[str, Any]:
    allowed_origins = EXTERNAL_PROPOSAL_ORIGINS | {"manual"}
    if proposal.get("created_by") not in allowed_origins:
        raise ValidationFailure(
            "proposal source must be manual, local_source, polymath_mcp, pegasus, or rag_pipeline"
        )
    if (
        proposal["created_by"] in EXTERNAL_PROPOSAL_ORIGINS
        and distillation_run_id is None
    ):
        raise ValidationFailure(
            "external proposals must enter through a distillation batch"
        )
    if distillation_run_id is not None and not proposal["proposal_id"].startswith(
        f"proposal_{distillation_run_id}_"
    ):
        raise ValidationFailure(
            "proposal ID does not match its distillation run"
        )
    validate_instance("proposal", proposal, root)
    path = root / "lab" / "second_brain" / "staging" / "proposals.jsonl"
    actor = "distill" if distillation_run_id else "manual"
    assert_write_target(actor, path, root)
    rows = read_jsonl(path)
    matches = [row for row in rows if row["proposal_id"] == proposal["proposal_id"]]
    if matches:
        if canonical_json_bytes(matches[0]) == canonical_json_bytes(proposal):
            return matches[0]
        raise ValidationFailure(f"proposal ID collision: {proposal['proposal_id']}")
    with path.open("ab") as handle:
        handle.write(canonical_json_bytes(proposal))
    return proposal


def ingest_distillation_batch(
    batch: dict[str, Any],
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate and distill one batch from a registered RAG adapter."""
    from .distill import run_distillation

    return run_distillation(batch, root)


def _promoted_proposal_ids(root: Path) -> set[str]:
    sb = root / "lab" / "second_brain"
    rows = read_jsonl(root / "lab" / "concepts.jsonl")
    for store in (
        "edges",
        "rules",
        "intents",
        "mappings",
        "claims",
        "equations",
        "methods",
        "mechanisms",
    ):
        rows.extend(read_jsonl(sb / "curated" / f"{store}.jsonl"))
    return {
        proposal_id
        for row in rows
        if (
            proposal_id := row.get("provenance", {}).get("proposal_id")
        )
    }


@authority_reader("ingest_status_snapshot")
def status(root: Path = REPO_ROOT) -> dict[str, Any]:
    manifest = read_jsonl(root / "lab" / "second_brain" / "staging" / "corpus_manifest.jsonl")
    proposals = read_jsonl(root / "lab" / "second_brain" / "staging" / "proposals.jsonl")
    promoted_ids = _promoted_proposal_ids(root)
    promoted = sum(
        proposal["proposal_id"] in promoted_ids
        for proposal in proposals
    )
    polymath = configuration_status()
    return {
        "capabilities": {"polymath_mcp": polymath},
        "corpus_items": len(manifest),
        "proposals": len(proposals),
        "pending_proposals": len(proposals) - promoted,
        "promoted_proposals": promoted,
        "accepted_external_origins": sorted(EXTERNAL_PROPOSAL_ORIGINS),
        "ready_for_external_inventory": polymath["credential_configured"],
        "external_inventory_blocked": not polymath["credential_configured"],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    batch = sub.add_parser(
        "batch",
        help="validate and distill a versioned RAG candidate batch",
    )
    batch.add_argument("record", type=Path)
    inventory = sub.add_parser("inventory")
    inventory.add_argument("rows", type=Path, help="JSON array of verified corpus rows")
    proposal = sub.add_parser(
        "proposal",
        help="stage a manual proposal; external sources must use batch",
    )
    proposal.add_argument("record", type=Path)
    args = parser.parse_args(argv)
    if args.command == "status":
        result = status()
    elif args.command == "batch":
        result = ingest_distillation_batch(
            json.loads(args.record.read_text())
        )
    elif args.command == "inventory":
        result = upsert_manifest(json.loads(args.rows.read_text()))
    else:
        result = stage_proposal(json.loads(args.record.read_text()))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
