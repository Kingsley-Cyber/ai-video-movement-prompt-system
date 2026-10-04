"""Promote validated staging proposals into their curated owner."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from .authority import authority_reader, authority_writer
from .curation_journal import (
    apply_curated_transaction,
    recover_curated_transactions,
)
from .rules import EVALUATORS, referenced_concept_ids
from .placement import (
    placement_required,
    require_graph_growth_plan,
)
from .source_registry import (
    resolve_typed_source_evidence,
    source_registry_required,
)
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
    "claim": ("claim", Path("lab/second_brain/curated/claims.jsonl")),
    "equation": ("equation", Path("lab/second_brain/curated/equations.jsonl")),
    "method": ("method", Path("lab/second_brain/curated/methods.jsonl")),
    "mechanism": ("mechanism", Path("lab/second_brain/curated/mechanisms.jsonl")),
    "reasoning_policy": (
        "reasoning_policy",
        Path("lab/second_brain/curated/reasoning_policies.jsonl"),
    ),
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
    "stage_claim",
    "stage_equation",
    "stage_method",
    "stage_mechanism",
    "stage_reasoning_policy",
}
PROMOTION_ORDER = {
    "concept": 0,
    "intent": 1,
    "claim": 1,
    "equation": 1,
    "method": 1,
    "mechanism": 1,
    "reasoning_policy": 1,
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
        *read_jsonl(sb / "curated" / "claims.jsonl"),
        *read_jsonl(sb / "curated" / "equations.jsonl"),
        *read_jsonl(sb / "curated" / "methods.jsonl"),
        *read_jsonl(sb / "curated" / "mechanisms.jsonl"),
        *read_jsonl(sb / "curated" / "reasoning_policies.jsonl"),
    ]


@authority_reader("curation_review_snapshot")
def prepare_distillation_review(
    run_id: str, root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Read one staged run and its proposals without granting promotion authority."""
    sb = root / "lab" / "second_brain"
    matches = [
        row
        for row in read_jsonl(sb / "staging" / "distillation_runs.jsonl")
        if row["id"] == run_id
    ]
    if len(matches) != 1:
        raise ValidationFailure(
            f"expected one distillation run {run_id}, found {len(matches)}"
        )
    run = matches[0]
    proposal_ids = set(run["proposal_ids"])
    proposals = [
        row
        for row in read_jsonl(sb / "staging" / "proposals.jsonl")
        if row["proposal_id"] in proposal_ids
    ]
    return {
        "schema": "cpcs.curation_review/1.0",
        "run": run,
        "proposals": sorted(proposals, key=lambda row: row["proposal_id"]),
        "requirements": {
            "durable_id_for_each_proposal": True,
            "human_review_required": True,
            "explicit_authorization_required_for_promotion": True,
        },
    }


def _distillation_lineage(proposal_id: str, root: Path) -> list[dict[str, Any]]:
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
                approved.append(
                    {
                        "run_id": run["id"],
                        "policy_version": run["policy_version"],
                        "policy_hash": run["policy_hash"],
                        "disposition": decision["disposition"],
                        "fingerprint": decision["fingerprint"],
                        "decision_hash": "sha256:"
                        + hashlib.sha256(canonical_json_bytes(decision)).hexdigest(),
                    }
                )
    return sorted(approved, key=lambda row: row["run_id"])


def _research_object_references(
    schema_name: str,
    record: dict[str, Any],
) -> set[str]:
    fields = {
        "claim": ("method_ids", "supports_claim_ids", "contradicts_claim_ids"),
        "equation": ("method_ids", "mechanism_ids"),
        "method": ("equation_ids", "mechanism_ids"),
        "mechanism": ("claim_ids", "method_ids", "equation_ids"),
    }[schema_name]
    references = {
        item
        for field in fields
        for item in record.get(field, [])
    }
    if schema_name == "equation":
        references.update(
            row["method_id"]
            for row in record.get("operational_mappings", [])
            if row.get("method_id")
        )
    references.discard(record["id"])
    return references


def _validate_references(
    schema_name: str,
    record: dict[str, Any],
    concept_ids: set[str],
    valid_curated_ids: set[str],
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
    elif schema_name in {"claim", "equation", "method", "mechanism"}:
        missing = sorted(set(record["concept_ids"]) - concept_ids)
        if missing:
            raise ValidationFailure(
                f"proposed {schema_name} references missing concepts: "
                + ", ".join(missing)
            )
        missing_objects = sorted(
            _research_object_references(schema_name, record) - valid_curated_ids
        )
        if missing_objects:
            raise ValidationFailure(
                f"proposed {schema_name} references missing research objects: "
                + ", ".join(missing_objects)
            )
    elif schema_name == "reasoning_policy":
        missing = sorted(set(record["concept_ids"]) - concept_ids)
        if missing:
            raise ValidationFailure(
                "proposed reasoning_policy references missing concepts: "
                + ", ".join(missing)
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
    future_ids: set[str] | None = None,
) -> tuple[Path, dict[str, Any]]:
    proposal_id = proposal["proposal_id"]
    if proposal["status"] != "pending":
        raise ValidationFailure(f"proposal {proposal_id} is not pending")
    external_source = proposal["created_by"] in EXTERNAL_PROPOSAL_ORIGINS
    distillation = (
        _distillation_lineage(proposal_id, root) if external_source else []
    )
    if external_source and not distillation:
        raise ValidationFailure(
            f"External proposal lacks an admissible distillation decision: {proposal_id}"
        )
    schema_name, relative_path = PROPOSAL_SCHEMA[proposal["proposal_type"]]
    record = dict(proposal["proposed_record"])
    record["id"] = durable_id
    if schema_name == "reasoning_policy":
        record["policy_id"] = durable_id
    source_evidence = []
    for evidence in proposal["source_evidence"]:
        required = ("source_id", "locator", "claim", "content_sha256")
        missing = [
            key
            for key in required
            if not isinstance(evidence.get(key), str) or not evidence[key]
        ]
        if missing:
            raise ValidationFailure(
                "promotion source evidence requires non-empty typed fields: "
                + ", ".join(missing)
            )
        source_evidence.append(
            resolve_typed_source_evidence(evidence, root)
            if source_registry_required(root)
            else dict(evidence)
        )
    record["provenance"] = {
        "origin": proposal["created_by"],
        "proposal_id": proposal_id,
        "promoted_by": promoted_by,
        "promoted_at": promoted_at,
        "source_evidence": source_evidence,
        "review": dict(review),
        "distillation": distillation,
        "distillation_run_ids": [row["run_id"] for row in distillation],
        "validation": {
            "schema": schema_name,
            "status": "passed",
        },
        "deduplication": {
            "candidates": list(proposal.get("dedup_candidates", [])),
            "reviewed": review["duplicate_checked"],
        },
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
    valid_curated_ids = {
        row["id"] for row in all_curated
    } | set(future_ids or ()) | {durable_id}
    _validate_references(
        schema_name,
        record,
        next_concept_ids,
        valid_curated_ids,
    )
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
    if (
        placement_required(root)
        and matches[0]["created_by"] in EXTERNAL_PROPOSAL_ORIGINS
    ):
        raise ValidationFailure(
            "source-derived promotion requires its exact distillation bundle and "
            "ontology placement plan"
        )
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
        {durable_id},
    )
    apply_curated_transaction(
        root,
        operation="promote_proposal",
        operation_id=proposal_id,
        updates={target: target.read_bytes() + canonical_json_bytes(record)},
    )
    return record


def _fixed_set_companion_updates(
    review: dict[str, Any], promoted: list[dict[str, Any]], root: Path
) -> dict[Path, bytes]:
    """Append only complete inventories for the fixed members in this exact bundle."""
    if "fixed_set_manifests" not in review:
        return {}
    manifests = review["fixed_set_manifests"]
    if not isinstance(manifests, list) or not manifests:
        raise ValidationFailure("fixed_set_manifests must be a non-empty list")
    path = root / "lab/second_brain/curated/domain_coverage_manifests.jsonl"
    assert_write_target("curate", path, root)
    existing = read_jsonl(path)
    ids = {m["id"] for m in existing}
    sets = {m["fixed_set"]["set_id"] for m in existing if "fixed_set" in m}
    members = {
        c["id"]: c["params"]["fixed_set_member"]
        for c in promoted if "fixed_set_member" in c.get("params", {})
    }
    declared = set()
    for manifest in manifests:
        validate_instance("domain_coverage_manifest", manifest, root)
        if "fixed_set" not in manifest:
            raise ValidationFailure("bundle companions must declare fixed-set inventories")
        spec = manifest["fixed_set"]
        if manifest["id"] in ids or spec["set_id"] in sets:
            raise ValidationFailure("fixed-set inventory ID or set already declared")
        ids.add(manifest["id"])
        sets.add(spec["set_id"])
        for entry in spec["members"]:
            member = members.get(entry["concept_id"])
            if member is None or entry["concept_id"] in declared:
                raise ValidationFailure("inventory member must be unique in this exact promotion bundle")
            if any(member[k] != spec[k] for k in ("set_id", "version", "authority")) or member["code"] != entry["code"]:
                raise ValidationFailure("inventory identity differs from its promoted member")
            declared.add(entry["concept_id"])
    if declared != set(members):
        raise ValidationFailure("inventory companions must cover every fixed member in the bundle")
    return {path: path.read_bytes() + b"".join(canonical_json_bytes(m) for m in manifests)}


@authority_writer("curation")
def promote_distillation_bundle(
    run_id: str,
    durable_ids: dict[str, str],
    promoted_by: str,
    review: PromotionReview | dict[str, Any],
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Promote proposals and optional review.fixed_set_manifests in one transaction."""
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
    incompatible_staged_edges = sorted(
        decision["candidate_id"]
        for decision in matches[0]["candidate_decisions"]
        if (
            decision["disposition"] in DISTILLATION_STAGE_DISPOSITIONS
            and decision.get("edge_compatibility") is not None
            and not decision["edge_compatibility"]["compatible"]
        )
    )
    if incompatible_staged_edges:
        raise ValidationFailure(
            "promotion requires reviewed typed reclassification for staged video edges: "
            + ", ".join(incompatible_staged_edges)
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

    growth_plan = require_graph_growth_plan(run_id, durable_ids, root)
    placement_by_proposal = {
        row["proposal_id"]: row
        for row in (growth_plan or {}).get("placements", [])
        if row["proposal_id"] is not None
    }

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
            set(assigned_ids),
        )
        if growth_plan is not None:
            placement = placement_by_proposal[proposal_id]
            record["provenance"]["validation"]["ontology_placement"] = {
                "growth_plan_id": growth_plan["id"],
                "growth_plan_hash": growth_plan["plan_hash"],
                "placement_hash": placement["placement_hash"],
                "disposition": placement["disposition"],
                "layer_root": placement["classification"]["layer_root"],
                "related_layer_roots": placement["classification"][
                    "related_layer_roots"
                ],
            }
            validate_instance(
                PROPOSAL_SCHEMA[proposals[proposal_id]["proposal_type"]][0],
                record,
                root,
            )
        promoted.append(record)
        updates[target] = updates.get(target, target.read_bytes()) + canonical_json_bytes(record)
    updates.update(_fixed_set_companion_updates(review, promoted, root))
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
        "growth_plan": (
            {
                "id": growth_plan["id"],
                "plan_hash": growth_plan["plan_hash"],
                "affected_derived_indexes": growth_plan[
                    "affected_derived_indexes"
                ],
                "projection_delta": growth_plan["projection_delta"],
            }
            if growth_plan is not None
            else None
        ),
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
