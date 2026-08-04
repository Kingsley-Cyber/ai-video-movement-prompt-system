"""Build deterministic, read-only, token-budgeted CPCS context bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

from .authority import authority_reader
from .graph import AUTHORED_EDGE_POLICY
from .query import GAP_POLICY, QUERY_POLICY, default_request, reason
from .rules import mappings_for_selection
from .temporal import TEMPORAL_POLICY, visible_records
from .validate import (
    REPO_ROOT,
    canonical_json_bytes,
    read_jsonl,
    validate_instance,
)

ContextBundle = dict[str, Any]

CONTEXT_POLICY = {
    "version": "cpcs-context/1.0",
    "token_estimator": "canonical-json-utf8-bytes-ceil-div-4",
}
TRUST_BOUNDARY = {
    "curated": "repository_authority",
    "immutable": "append_only_evidence",
    "derived": "rebuildable_ranking_signal",
    "external": "untrusted_external_evidence",
}
EXTERNAL_REQUIRED_FIELDS = frozenset(
    {
        "origin",
        "source_id",
        "locator",
        "content_hash",
        "passage",
        "retrieval_query",
    }
)
EXTERNAL_OPTIONAL_FIELDS = frozenset(
    {"retrieved_at", "score", "metadata"}
)
CONTENT_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
ADMISSION_PRIORITY = {
    "direct_match": 0,
    "required_prerequisite": 1,
    "operational_bridge": 2,
    "structural_term_support": 3,
}


def canonical_bundle_bytes(bundle: ContextBundle) -> bytes:
    """Return the byte-stable representation used by replay canaries."""
    return canonical_json_bytes(bundle)


def _estimated_tokens(value: Any) -> int:
    return max(1, math.ceil(len(canonical_json_bytes(value)) / 4))


def _sync_used_tokens(bundle: ContextBundle) -> int:
    report = bundle["budget_report"]
    for _ in range(8):
        estimate = _estimated_tokens(bundle)
        if report["used_tokens"] == estimate:
            return estimate
        report["used_tokens"] = estimate
    raise RuntimeError("context token accounting did not converge")


def _require_external_string(
    item: dict[str, Any], key: str, index: int
) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"external_evidence[{index}].{key} must be a non-empty string"
        )
    return value


def _normalize_external_evidence(
    rows: Iterable[dict[str, Any]] | None,
    retrieval_query: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(rows or []):
        if not isinstance(raw, dict):
            raise ValueError(f"external_evidence[{index}] must be an object")
        fields = set(raw)
        missing = EXTERNAL_REQUIRED_FIELDS - fields
        extra = fields - EXTERNAL_REQUIRED_FIELDS - EXTERNAL_OPTIONAL_FIELDS
        if missing:
            raise ValueError(
                f"external_evidence[{index}] missing fields: "
                + ", ".join(sorted(missing))
            )
        if extra:
            raise ValueError(
                f"external_evidence[{index}] has unexpected fields: "
                + ", ".join(sorted(extra))
            )
        passage = _require_external_string(raw, "passage", index)
        content_hash = _require_external_string(raw, "content_hash", index)
        if not CONTENT_HASH.fullmatch(content_hash):
            raise ValueError(
                f"external_evidence[{index}].content_hash must be sha256:<64 lowercase hex>"
            )
        expected_hash = "sha256:" + hashlib.sha256(
            passage.encode("utf-8")
        ).hexdigest()
        if content_hash != expected_hash:
            raise ValueError(
                f"external_evidence[{index}].content_hash does not match passage bytes"
            )
        row_query = _require_external_string(raw, "retrieval_query", index)
        if row_query != retrieval_query:
            raise ValueError(
                f"external_evidence[{index}].retrieval_query must match declared gap query {retrieval_query!r}"
            )
        row: dict[str, Any] = {
            "origin": _require_external_string(raw, "origin", index),
            "source_id": _require_external_string(raw, "source_id", index),
            "locator": _require_external_string(raw, "locator", index),
            "content_hash": content_hash,
            "passage": passage,
            "retrieval_query": row_query,
            "retrieved_at": raw.get("retrieved_at"),
            "score": raw.get("score"),
            "metadata": raw.get("metadata", {}),
            "trust_class": "untrusted_external_evidence",
        }
        if row["retrieved_at"] is not None and not isinstance(
            row["retrieved_at"], str
        ):
            raise ValueError(
                f"external_evidence[{index}].retrieved_at must be a string or null"
            )
        if row["score"] is not None and (
            isinstance(row["score"], bool)
            or not isinstance(row["score"], (int, float))
        ):
            raise ValueError(
                f"external_evidence[{index}].score must be a number or null"
            )
        if not isinstance(row["metadata"], dict):
            raise ValueError(
                f"external_evidence[{index}].metadata must be an object"
            )
        normalized.append(row)

    normalized.sort(
        key=lambda item: (
            item["content_hash"],
            item["source_id"],
            item["locator"],
        )
    )
    unique: list[dict[str, Any]] = []
    duplicate_omissions: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for row in normalized:
        item_id = f"{row['source_id']}#{row['locator']}"
        if row["content_hash"] in seen_hashes:
            duplicate_omissions.append(
                {
                    "section": "external_evidence",
                    "item_id": item_id,
                    "estimated_tokens": _estimated_tokens(row),
                    "reason": "duplicate_content_hash",
                }
            )
            continue
        seen_hashes.add(row["content_hash"])
        unique.append(row)
    return unique, duplicate_omissions


def _path_trust(tier: str | None) -> str:
    return {
        "temporary": "ephemeral_query_decision",
        "curated": "curated_repository_authority",
        "immutable": "immutable_evidence",
        "derived": "derived_non_authoritative",
    }.get(tier, "ephemeral_query_decision")


def _curated_evidence(
    reasoning: dict[str, Any], root: Path
) -> list[dict[str, Any]]:
    selected_ids = {
        item["id"] for item in reasoning["selected_concepts"]
    }
    concept_rows = {
        row["id"]: row
        for row in read_jsonl(root / "lab/concepts.jsonl")
        if row["id"] in selected_ids
    }
    aggregated: dict[tuple[str, str, str], set[str]] = {}
    for concept_id in sorted(selected_ids):
        for reference in reasoning["source_references"].get(concept_id, []):
            aggregated.setdefault(
                (
                    "source_reference",
                    reference,
                    "curated_lineage_reference",
                ),
                set(),
            ).add(concept_id)
        for evidence_id in concept_rows.get(concept_id, {}).get(
            "evidence", []
        ):
            aggregated.setdefault(
                (
                    "repository_evidence_id",
                    evidence_id,
                    "curated_lineage_reference",
                ),
                set(),
            ).add(concept_id)
    derived_evidence = {
        evidence_id
        for weight in reasoning.get("learned_weights", [])
        for evidence_id in weight.get("evidence", [])
    }
    represented = {key[1] for key in aggregated}
    for evidence_id in reasoning.get("evidence_ids", []):
        trust = (
            "derived_lineage_reference"
            if evidence_id in derived_evidence
            else "curated_lineage_reference"
        )
        if evidence_id not in represented:
            aggregated.setdefault(
                ("repository_evidence_id", evidence_id, trust),
                set(),
            )
    rows = []
    for (kind, reference, trust), concept_ids in sorted(
        aggregated.items()
    ):
        digest = hashlib.sha256(
            f"{kind}\0{reference}\0{trust}".encode("utf-8")
        ).hexdigest()[:16]
        rows.append(
            {
                "id": f"evidence:{digest}",
                "evidence_kind": kind,
                "reference": reference,
                "concept_ids": sorted(concept_ids),
                "trust_class": trust,
            }
        )
    return rows


def _candidate(
    section: str,
    item_id: str,
    value: dict[str, Any],
    concept_dependencies: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "section": section,
        "item_id": item_id,
        "value": value,
        "concept_dependencies": sorted(set(concept_dependencies)),
        "estimated_tokens": _estimated_tokens(value),
    }


def _omission(candidate: dict[str, Any], reason_code: str) -> dict[str, Any]:
    return {
        "section": candidate["section"],
        "item_id": candidate["item_id"],
        "estimated_tokens": candidate["estimated_tokens"],
        "reason": reason_code,
    }


def _replace_omission(
    bundle: ContextBundle,
    candidate: dict[str, Any],
    reason_code: str,
) -> None:
    omissions = bundle["budget_report"]["omitted_items"]
    for index, row in enumerate(omissions):
        if (
            row["section"] == candidate["section"]
            and row["item_id"] == candidate["item_id"]
        ):
            omissions[index] = _omission(candidate, reason_code)
            return
    raise RuntimeError("candidate omission reservation is missing")


def _pack(
    bundle: ContextBundle,
    candidates: list[dict[str, Any]],
    fixed_omissions: list[dict[str, Any]],
) -> None:
    report = bundle["budget_report"]
    report["omitted_items"] = fixed_omissions + [
        _omission(candidate, "token_budget_exceeded")
        for candidate in candidates
    ]
    report["omitted_items"].sort(
        key=lambda row: (row["section"], row["item_id"], row["reason"])
    )
    minimum = _sync_used_tokens(bundle)
    if minimum > report["available_tokens"]:
        raise ValueError(
            "token_budget is too small for the context envelope and omission report; "
            f"minimum is {minimum}"
        )

    admitted_concepts: set[str] = set()
    for candidate in candidates:
        dependencies = set(candidate["concept_dependencies"])
        if not dependencies <= admitted_concepts:
            _replace_omission(bundle, candidate, "dependency_omitted")
            _sync_used_tokens(bundle)
            continue
        omissions = report["omitted_items"]
        reservation = next(
            row
            for row in omissions
            if row["section"] == candidate["section"]
            and row["item_id"] == candidate["item_id"]
        )
        omissions.remove(reservation)
        bundle[candidate["section"]].append(candidate["value"])
        used = _sync_used_tokens(bundle)
        if used > report["available_tokens"]:
            bundle[candidate["section"]].pop()
            omissions.append(reservation)
            omissions.sort(
                key=lambda row: (
                    row["section"],
                    row["item_id"],
                    row["reason"],
                )
            )
            _sync_used_tokens(bundle)
            continue
        if candidate["section"] == "selected_concepts":
            admitted_concepts.add(candidate["item_id"])


@authority_reader("context_snapshot")
def build_context_bundle(
    query: str,
    *,
    token_budget: int,
    provider: str | None = None,
    model: str | None = None,
    minimum_status: str = "ingested",
    include_external_evidence: bool = True,
    external_evidence: Iterable[dict[str, Any]] | None = None,
    domain: str | None = None,
    target_format: str = "hybrid",
    required_layers: Iterable[str] = (),
    excluded_layers: Iterable[str] = (),
    intent: str | None = None,
    as_of: str | None = None,
    validity_mode: str = "current",
    root: Path = REPO_ROOT,
) -> ContextBundle:
    """Build a schema-valid bundle without mutating any repository tier."""
    if isinstance(token_budget, bool) or not isinstance(token_budget, int):
        raise ValueError("token_budget must be an integer")
    if token_budget <= 0:
        raise ValueError("token_budget must be greater than zero")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if intent is not None and (not isinstance(intent, str) or not intent.strip()):
        raise ValueError("intent must be a non-empty string or null")
    if isinstance(required_layers, (str, bytes)) or isinstance(
        excluded_layers, (str, bytes)
    ):
        raise ValueError("required_layers and excluded_layers must be iterables of strings")
    raw_required = list(required_layers)
    raw_excluded = list(excluded_layers)
    for label, layers in (
        ("required_layers", raw_required),
        ("excluded_layers", raw_excluded),
    ):
        if any(not isinstance(layer, str) or not layer.strip() for layer in layers):
            raise ValueError(f"{label} must contain non-empty strings")
    normalized_required = sorted(set(raw_required))
    normalized_excluded = sorted(set(raw_excluded))

    request = default_request(
        query,
        domain=domain,
        target_format=target_format,
        provider=provider,
        model_version=model,
        minimum_status=minimum_status,
        include_unproven=False,
        required_layers=normalized_required,
        excluded_layers=normalized_excluded,
        as_of=as_of,
        validity_mode=validity_mode,
    )
    reasoning = reason(request, root)
    selected_rows = [
        {**row, "trust_class": "curated_repository_authority"}
        for row in sorted(
            reasoning["selected_concepts"],
            key=lambda row: (
                ADMISSION_PRIORITY[row["admission_reason"]],
                row["depth"],
                row["id"],
            ),
        )
    ]
    selected_ids = {row["id"] for row in selected_rows}
    mappings = [
        {**row, "trust_class": "curated_repository_authority"}
        for row in mappings_for_selection(
            visible_records(
                read_jsonl(root / "lab/second_brain/curated/mappings.jsonl"),
                validity_mode,
                as_of,
            ),
            selected_ids,
            provider,
            model,
        )
    ]
    typed_paths = [
        {
            **row,
            "path_kind": "selected",
            "trust_class": _path_trust(row.get("tier")),
        }
        for row in reasoning["path_taken"]
        if row["to"] in selected_ids
    ]
    typed_paths.sort(
        key=lambda row: (
            row["depth"],
            row["to"],
            row["from"],
            row["edge_id"],
        )
    )
    conflicts = []
    for kind, rows in (
        ("authored_conflict", reasoning["conflicts_encountered"]),
        ("domain_rejection", reasoning["domain_rejections"]),
        ("rule_violation", reasoning["rule_violations"]),
    ):
        conflicts.extend(
            {"kind": kind, "details": row}
            for row in rows
        )
    conflicts.sort(
        key=lambda row: (row["kind"], json.dumps(row["details"], sort_keys=True))
    )
    rejections = []
    for row in reasoning["rejected_concepts"]:
        core_keys = {
            "id",
            "name",
            "reason_code",
            "reasons",
            "via_edge",
            "policy_version",
        }
        rejections.append(
            {
                "id": row["id"],
                "name": row.get("name"),
                "reason_code": row["reason_code"],
                "reasons": row["reasons"],
                "via_edge": row["via_edge"],
                "policy_version": row["policy_version"],
                "details": {
                    key: value
                    for key, value in row.items()
                    if key not in core_keys
                },
            }
        )
    rejections.sort(key=lambda row: row["id"])

    gap = reasoning["knowledge_gap"]
    normalized_external, fixed_omissions = _normalize_external_evidence(
        external_evidence,
        gap["suggested_query"],
    )
    external_reason: str | None = None
    if not include_external_evidence:
        external_reason = "external_evidence_disabled"
    elif not gap["should_retrieve"]:
        external_reason = "no_declared_knowledge_gap"

    bundle: ContextBundle = {
        "schema": "cpcs.context_bundle/1.0",
        "request": {
            "query": query,
            "intent": intent,
            "token_budget": token_budget,
            "provider": provider,
            "model": model,
            "domain": domain,
            "target_format": target_format,
            "minimum_status": minimum_status,
            "include_external_evidence": include_external_evidence,
            "as_of": as_of,
            "validity_mode": validity_mode,
        },
        "selected_concepts": [],
        "typed_paths": [],
        "mappings": [],
        "curated_evidence": [],
        "external_evidence": [],
        "conflicts": [],
        "rejections": [],
        "knowledge_gap": gap,
        "temporal": {
            "policy_version": reasoning["temporal_query"]["policy_version"],
            "validity_mode": reasoning["temporal_query"]["validity_mode"],
            "as_of": reasoning["temporal_query"]["as_of"],
            "replacement_traces": reasoning["temporal_query"]["replacement_traces"],
        },
        "budget_report": {
            "available_tokens": token_budget,
            "used_tokens": 0,
            "estimator": CONTEXT_POLICY["token_estimator"],
            "scope": "complete_context_bundle",
            "omitted_items": [],
        },
        "trust_boundary": dict(TRUST_BOUNDARY),
        "policy_versions": {
            "context": CONTEXT_POLICY["version"],
            "query": QUERY_POLICY["version"],
            "gap": GAP_POLICY["version"],
            "edge": AUTHORED_EDGE_POLICY["version"],
            "temporal": TEMPORAL_POLICY["version"],
        },
    }

    candidates: list[dict[str, Any]] = []
    candidates.extend(
        _candidate("selected_concepts", row["id"], row)
        for row in selected_rows
    )
    candidates.extend(
        _candidate(
            "conflicts",
            f"{row['kind']}:{index}",
            row,
        )
        for index, row in enumerate(conflicts)
    )
    candidates.extend(
        _candidate("rejections", row["id"], row)
        for row in rejections
    )
    for row in typed_paths:
        dependencies = [row["to"]]
        if row["from"] in selected_ids:
            dependencies.append(row["from"])
        candidates.append(
            _candidate(
                "typed_paths",
                row["edge_id"] + ":" + row["to"],
                row,
                dependencies,
            )
        )
    candidates.extend(
        _candidate(
            "mappings",
            row["id"],
            row,
            [row["concept_id"]],
        )
        for row in mappings
    )
    candidates.extend(
        _candidate(
            "curated_evidence",
            row["id"],
            row,
            row["concept_ids"],
        )
        for row in _curated_evidence(reasoning, root)
    )
    for row in normalized_external:
        item_id = f"{row['source_id']}#{row['locator']}"
        candidate = _candidate("external_evidence", item_id, row)
        if external_reason:
            fixed_omissions.append(_omission(candidate, external_reason))
        else:
            candidates.append(candidate)

    _pack(bundle, candidates, fixed_omissions)
    validate_instance("context_bundle", bundle, root)
    return bundle


def _read_external_file(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read external evidence JSON: {exc}") from exc
    if isinstance(value, dict) and "external_evidence" in value:
        value = value["external_evidence"]
    if not isinstance(value, list):
        raise ValueError("external evidence JSON must be a list")
    return value


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("build")
    command.add_argument("query")
    command.add_argument("--token-budget", type=int, required=True)
    command.add_argument("--provider")
    command.add_argument("--model")
    command.add_argument("--domain")
    command.add_argument(
        "--target-format",
        choices=("prose", "yaml", "json", "xml", "hybrid"),
        default="hybrid",
    )
    command.add_argument(
        "--minimum-status",
        choices=("ingested", "partial", "proven"),
        default="ingested",
    )
    command.add_argument("--external-evidence", type=Path)
    command.add_argument("--as-of")
    command.add_argument(
        "--validity-mode",
        choices=("current", "historical", "all_versions"),
        default="current",
    )
    command.add_argument(
        "--no-external-evidence",
        action="store_true",
    )
    args = parser.parse_args(argv)
    rows = (
        _read_external_file(args.external_evidence)
        if args.external_evidence
        else None
    )
    bundle = build_context_bundle(
        args.query,
        token_budget=args.token_budget,
        provider=args.provider,
        model=args.model,
        domain=args.domain,
        target_format=args.target_format,
        minimum_status=args.minimum_status,
        include_external_evidence=not args.no_external_evidence,
        external_evidence=rows,
        as_of=args.as_of,
        validity_mode=args.validity_mode,
    )
    print(json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
