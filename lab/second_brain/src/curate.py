"""Promote validated staging proposals into their curated owner."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from .authority import authority_writer
from .curation_journal import (
    apply_curated_transaction,
    recover_curated_transactions,
)
from .rules import EVALUATORS, referenced_concept_ids
from .validate import (
    EXTERNAL_PROPOSAL_ORIGINS,
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    canonical_json_bytes,
    read_jsonl,
    validate_curated,
    validate_instance,
)

PROPOSAL_SCHEMA = {
    "concept": ("concept", Path("lab/concepts.jsonl")),
    "edge": ("edge", Path("lab/second_brain/curated/edges.jsonl")),
    "rule": ("rule", Path("lab/second_brain/curated/rules.jsonl")),
    "intent": ("intent", Path("lab/second_brain/curated/intents.jsonl")),
    "mapping": ("mapping", Path("lab/second_brain/curated/mappings.jsonl")),
}

REQUIRED_REVIEW_FLAGS = (
    "source_verified",
    "source_locator_resolved",
    "duplicate_checked",
    "operationally_useful",
    "relationships_validated",
    "numeric_precision_supported",
)
DISTILLATION_STAGE_DISPOSITIONS = {
    "stage_new",
    "stage_relationship",
    "stage_mapping",
    "stage_rule",
    "stage_intent",
}
PROMOTION_ORDER = {
    "concept": 0,
    "intent": 1,
    "edge": 2,
    "mapping": 3,
    "rule": 4,
}


class PromotionReview(TypedDict):
    source_verified: bool
    source_locator_resolved: bool
    duplicate_checked: bool
    operationally_useful: bool
    relationships_validated: bool
    numeric_precision_supported: bool
    reviewed_at: str
    notes: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _validate_review(review: dict[str, Any]) -> None:
    missing = [flag for flag in REQUIRED_REVIEW_FLAGS if review.get(flag) is not True]
    if missing:
        raise ValidationFailure(
            "promotion review must explicitly pass: " + ", ".join(missing)
        )
    reviewed_at = review.get("reviewed_at")
    if not isinstance(reviewed_at, str):
        raise ValidationFailure("promotion review requires reviewed_at")
    try:
        datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValidationFailure("promotion reviewed_at must be ISO-8601") from error
    if "notes" in review and not isinstance(review["notes"], str):
        raise ValidationFailure("promotion review notes must be a string")


def _all_curated(root: Path) -> list[dict[str, Any]]:
    sb = root / "lab" / "second_brain"
    return [
        *read_jsonl(root / "lab" / "concepts.jsonl"),
        *read_jsonl(sb / "curated" / "edges.jsonl"),
        *read_jsonl(sb / "curated" / "rules.jsonl"),
        *read_jsonl(sb / "curated" / "intents.jsonl"),
        *read_jsonl(sb / "curated" / "mappings.jsonl"),
    ]


def _distillation_lineage(proposal_id: str, root: Path) -> list[str]:
    runs = read_jsonl(
        root
        / "lab"
        / "second_brain"
        / "staging"
        / "distillation_runs.jsonl"
    )
    approved = []
    for run in runs:
        for decision in run["candidate_decisions"]:
            if (
                decision["proposal_id"] == proposal_id
                and decision["disposition"] in DISTILLATION_STAGE_DISPOSITIONS
            ):
                approved.append(run["id"])
    return sorted(set(approved))


def _validate_references(
    schema_name: str,
    record: dict[str, Any],
    concept_ids: set[str],
) -> None:
    if schema_name == "edge":
        missing = sorted({record["u"], record["v"]} - concept_ids)
        if missing:
            raise ValidationFailure(
                "proposed edge references missing concepts: " + ", ".join(missing)
            )
    elif schema_name == "mapping" and record["concept_id"] not in concept_ids:
        raise ValidationFailure(
            f"proposed mapping references missing concept {record['concept_id']}"
        )
    elif schema_name == "rule":
        if record["evaluator"] not in EVALUATORS:
            raise ValidationFailure(
                f"proposed rule uses unknown evaluator {record['evaluator']}"
            )
        missing = sorted(referenced_concept_ids(record) - concept_ids)
        if missing:
            raise ValidationFailure(
                "proposed rule references missing concepts: " + ", ".join(missing)
            )


def _prepare_promotion_record(
    proposal: dict[str, Any],
    durable_id: str,
    promoted_by: str,
    review: PromotionReview | dict[str, Any],
    promoted_at: str,
    all_curated: list[dict[str, Any]],
    concept_ids: set[str],
    root: Path,
) -> tuple[Path, dict[str, Any]]:
    proposal_id = proposal["proposal_id"]
    if proposal["status"] != "pending":
        raise ValidationFailure(f"proposal {proposal_id} is not pending")
    external_source = proposal["created_by"] in EXTERNAL_PROPOSAL_ORIGINS
    distillation_run_ids = (
        _distillation_lineage(proposal_id, root) if external_source else []
    )
    if external_source and not distillation_run_ids:
        raise ValidationFailure(
            f"External proposal lacks an admissible distillation decision: {proposal_id}"
        )
    schema_name, relative_path = PROPOSAL_SCHEMA[proposal["proposal_type"]]
    record = dict(proposal["proposed_record"])
    record["id"] = durable_id
    record["provenance"] = {
        "origin": proposal["created_by"],
        "proposal_id": proposal_id,
        "promoted_by": promoted_by,
        "promoted_at": promoted_at,
        "review": dict(review),
        "distillation_run_ids": distillation_run_ids,
    }
    validate_instance(schema_name, record, root)
    target = root / relative_path
    assert_write_target("curate", target, root)
    if any(row["id"] == durable_id for row in all_curated):
        raise ValidationFailure(f"durable ID already exists: {durable_id}")
    if any(
        row.get("provenance", {}).get("proposal_id") == proposal_id
        for row in all_curated
    ):
        raise ValidationFailure(f"proposal already promoted: {proposal_id}")
    next_concept_ids = set(concept_ids)
    if schema_name == "concept":
        next_concept_ids.add(durable_id)
    _validate_references(schema_name, record, next_concept_ids)
    concept_ids.clear()
    concept_ids.update(next_concept_ids)
    all_curated.append(record)
    return target, record


@authority_writer("curation")
def promote_proposal(
    proposal_id: str,
    durable_id: str,
    promoted_by: str,
    review: PromotionReview | dict[str, Any],
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    _validate_review(review)
    recover_curated_transactions(root)
    validate_curated(root)
    proposals = read_jsonl(root / "lab" / "second_brain" / "staging" / "proposals.jsonl")
    matches = [row for row in proposals if row["proposal_id"] == proposal_id]
    if len(matches) != 1:
        raise ValidationFailure(f"expected one proposal {proposal_id}, found {len(matches)}")
    all_curated = _all_curated(root)
    concept_ids = {
        row["id"] for row in read_jsonl(root / "lab" / "concepts.jsonl")
    }
    target, record = _prepare_promotion_record(
        matches[0],
        durable_id,
        promoted_by,
        review,
        _utc_now(),
        all_curated,
        concept_ids,
        root,
    )
    apply_curated_transaction(
        root,
        operation="promote_proposal",
        operation_id=proposal_id,
        updates={target: target.read_bytes() + canonical_json_bytes(record)},
    )
    return record


@authority_writer("curation")
def promote_distillation_bundle(
    run_id: str,
    durable_ids: dict[str, str],
    promoted_by: str,
    review: PromotionReview | dict[str, Any],
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Promote every staged proposal in one crash-recoverable transaction."""
    _validate_review(review)
    recover_curated_transactions(root)
    validate_curated(root)
    runs = read_jsonl(
        root
        / "lab"
        / "second_brain"
        / "staging"
        / "distillation_runs.jsonl"
    )
    matches = [run for run in runs if run["id"] == run_id]
    if len(matches) != 1:
        raise ValidationFailure(
            f"expected one distillation run {run_id}, found {len(matches)}"
        )
    proposal_ids = sorted(
        decision["proposal_id"]
        for decision in matches[0]["candidate_decisions"]
        if (
            decision["disposition"] in DISTILLATION_STAGE_DISPOSITIONS
            and decision["proposal_id"]
        )
    )
    if not proposal_ids:
        raise ValidationFailure(
            f"distillation run {run_id} has no proposals to promote"
        )
    if set(durable_ids) != set(proposal_ids):
        missing = sorted(set(proposal_ids) - set(durable_ids))
        extra = sorted(set(durable_ids) - set(proposal_ids))
        raise ValidationFailure(
            f"bundle durable ID assignments missing={missing} extra={extra}"
        )
    assigned_ids = list(durable_ids.values())
    if any(
        not isinstance(durable_id, str) or not durable_id
        for durable_id in assigned_ids
    ):
        raise ValidationFailure(
            "bundle durable ID assignments must be non-empty strings"
        )
    if len(assigned_ids) != len(set(assigned_ids)):
        raise ValidationFailure("bundle durable IDs must be unique")

    proposals = {
        proposal["proposal_id"]: proposal
        for proposal in read_jsonl(
            root
            / "lab"
            / "second_brain"
            / "staging"
            / "proposals.jsonl"
        )
        if proposal["proposal_id"] in proposal_ids
    }
    missing_records = sorted(set(proposal_ids) - set(proposals))
    if missing_records:
        raise ValidationFailure(
            "bundle references missing staging proposals: "
            + ", ".join(missing_records)
        )
    ordered = sorted(
        proposal_ids,
        key=lambda proposal_id: (
            PROMOTION_ORDER[proposals[proposal_id]["proposal_type"]],
            proposal_id,
        ),
    )
    all_curated = _all_curated(root)
    concept_ids = {
        row["id"] for row in read_jsonl(root / "lab" / "concepts.jsonl")
    }
    promoted_at = _utc_now()
    promoted = []
    updates: dict[Path, bytes] = {}
    for proposal_id in ordered:
        target, record = _prepare_promotion_record(
            proposals[proposal_id],
            durable_ids[proposal_id],
            promoted_by,
            review,
            promoted_at,
            all_curated,
            concept_ids,
            root,
        )
        promoted.append(record)
        updates[target] = updates.get(target, target.read_bytes()) + canonical_json_bytes(record)
    transaction = apply_curated_transaction(
        root,
        operation="promote_distillation_bundle",
        operation_id=run_id,
        updates=updates,
    )
    return {
        "run_id": run_id,
        "promoted_ids": [record["id"] for record in promoted],
        "records": promoted,
        "transaction": transaction,
    }


def main(argv: list[str] | None = None) -> None:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv and raw_argv[0] not in {
        "promote",
        "bundle",
        "recover",
        "-h",
        "--help",
    }:
        raw_argv.insert(0, "promote")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    promote = sub.add_parser("promote")
    promote.add_argument("proposal_id")
    promote.add_argument("durable_id")
    promote.add_argument("--by", required=True)
    promote.add_argument("--review", type=Path, required=True)
    bundle = sub.add_parser("bundle")
    bundle.add_argument("run_id")
    bundle.add_argument(
        "assignments",
        type=Path,
        help="JSON object mapping every proposal ID to its durable ID",
    )
    bundle.add_argument("--by", required=True)
    bundle.add_argument("--review", type=Path, required=True)
    sub.add_parser("recover")
    args = parser.parse_args(raw_argv)
    if args.command == "promote":
        result = promote_proposal(
            args.proposal_id,
            args.durable_id,
            args.by,
            json.loads(args.review.read_text()),
        )
    elif args.command == "bundle":
        result = promote_distillation_bundle(
            args.run_id,
            json.loads(args.assignments.read_text()),
            args.by,
            json.loads(args.review.read_text()),
        )
    else:
        result = {"recovered": recover_curated_transactions()}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
