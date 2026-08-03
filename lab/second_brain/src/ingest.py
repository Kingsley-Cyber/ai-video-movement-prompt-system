"""Resumable batch-ingestion boundary for external knowledge sources."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

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

DISCOVERED_CAPABILITIES = {
    "discovered_on": "2026-07-30",
    "polymath_available": True,
    "mcp_endpoint": "http://127.0.0.1:8765/mcp",
    "server": {"name": "polymath", "version": "1.28.1"},
    "protocol_version": "2025-11-25",
    "tool_count": 27,
    "twelvelabs_adapter_available": True,
    "pegasus_provider_configured": bool(
        os.environ.get("TWELVE_LABS_API_KEY")
        and os.environ.get("TWELVE_LABS_KNOWLEDGE_STORE_ID")
    ),
    "retrieval_tools": [
        "polymath_search",
        "search",
        "fetch",
        "polymath_cross_corpus_search",
        "polymath_list_corpora",
        "polymath_list_documents",
        "polymath_get_chunk_extraction",
    ],
    "target_corpus": {
        "id": "149a2dcb-8c61-404e-8006-1df7e3791b5a",
        "name": "video_generations_schools",
        "verified_document_count": 80,
    },
    "uncertainty": (
        "The TwelveLabs v1.3 adapter is installed in the repository. Provider credentials, "
        "a configured knowledge store, and an authorized source video remain unverified. "
        "Polymath capabilities were verified through the live MCP endpoint."
    ),
}


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
    for store in ("edges", "rules", "intents", "mappings"):
        rows.extend(read_jsonl(sb / "curated" / f"{store}.jsonl"))
    return {
        proposal_id
        for row in rows
        if (
            proposal_id := row.get("provenance", {}).get("proposal_id")
        )
    }


def status(root: Path = REPO_ROOT) -> dict[str, Any]:
    manifest = read_jsonl(root / "lab" / "second_brain" / "staging" / "corpus_manifest.jsonl")
    proposals = read_jsonl(root / "lab" / "second_brain" / "staging" / "proposals.jsonl")
    promoted_ids = _promoted_proposal_ids(root)
    promoted = sum(
        proposal["proposal_id"] in promoted_ids
        for proposal in proposals
    )
    return {
        "capabilities": DISCOVERED_CAPABILITIES,
        "corpus_items": len(manifest),
        "proposals": len(proposals),
        "pending_proposals": len(proposals) - promoted,
        "promoted_proposals": promoted,
        "accepted_external_origins": sorted(EXTERNAL_PROPOSAL_ORIGINS),
        "ready_for_external_inventory": True,
        "external_inventory_blocked": not DISCOVERED_CAPABILITIES["polymath_available"],
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
