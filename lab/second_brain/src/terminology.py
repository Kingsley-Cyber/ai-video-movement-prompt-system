"""Deterministic terminology detection with source-backed agent resolution proposals."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable

from .authority import authority_reader, authority_writer
from .source_registry import load_source_units
from .validate import (
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    canonical_json_bytes,
    content_hash,
    load_ontology_registry,
    normalize_concept_identity,
    read_jsonl,
    sha256_value,
    validate_instance,
)

POLICY = {
    "version": "cpcs-terminology-resolution/1.0",
    "identity_rule": "registry_pattern_and_normalized_integer",
    "context_rule": "unique_lexicographic_domain_then_context_match",
    "ambiguity_rule": "closed_candidates_require_source_backed_agent_proposal",
    "durable_identity_authority": "explicit_human_review",
}
POLICY_HASH = sha256_value(POLICY)
PROPOSAL_PATH = Path("lab/second_brain/staging/terminology_resolutions.jsonl")


def _contains(normalized_text: str, normalized_phrase: str) -> bool:
    return f" {normalized_phrase} " in f" {normalized_text} "


def _sense_row(
    sense: dict[str, Any], normalized_text: str, domain: str | None
) -> dict[str, Any]:
    normalized_domain = normalize_concept_identity(domain or "")
    matched = sorted(
        term
        for term in sense["context_terms"]
        if _contains(normalized_text, normalize_concept_identity(term))
    )
    return {
        "sense_id": sense["sense_id"],
        "label": sense["label"],
        "domain": sense["domain"],
        "concept_ids": sorted(sense["concept_ids"]),
        "context_terms": sorted(sense["context_terms"]),
        "matched_context_terms": matched,
        "domain_match": bool(normalized_domain) and normalized_domain == normalize_concept_identity(sense["domain"]),
    }


def _match_id(identity: dict[str, Any]) -> str:
    return "termmatch_" + hashlib.sha256(canonical_json_bytes(identity)).hexdigest()[:24]


def _identifier_matches(
    text: str, registry: dict[str, Any]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for rule in registry["identifier_rules"]:
        try:
            pattern = re.compile(rule["pattern"])
        except re.error as exc:
            raise ValidationFailure(
                f"ontology identifier rule {rule['id']} has invalid pattern: {exc}"
            ) from exc
        for match in pattern.finditer(text):
            try:
                numeric = str(int(match.group(rule["capture_group"])))
            except (IndexError, ValueError) as exc:
                raise ValidationFailure(
                    f"ontology identifier rule {rule['id']} cannot normalize its capture"
                ) from exc
            canonical = rule["canonical_prefix"] + numeric
            identity = {
                "rule_id": rule["id"],
                "canonical_identifier": canonical,
                "sense_id": rule["sense_id"],
            }
            key = (rule["id"], canonical)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "match_id": _match_id(identity),
                    "match_type": "identifier",
                    "normalized_match": canonical,
                    "canonical_identifier": canonical,
                    "inventory_status": rule["inventory_status"],
                    "disposition": "resolved_exact_identifier",
                    "candidate_senses": [
                        {
                            "sense_id": rule["sense_id"],
                            "label": canonical,
                            "domain": rule["domain"],
                            "concept_ids": sorted(rule["concept_ids"]),
                            "context_terms": [canonical],
                            "matched_context_terms": [canonical],
                            "domain_match": True,
                        }
                    ],
                    "selected_sense_id": rule["sense_id"],
                    "selected_concept_ids": sorted(rule["concept_ids"]),
                }
            )
    return sorted(rows, key=lambda row: (row["normalized_match"], row["match_id"]))


def _term_matches(
    normalized_text: str,
    domain: str | None,
    registry: dict[str, Any],
    identifier_sense_ids: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for term in registry["term_senses"]:
        matched_aliases = sorted(
            {
                normalize_concept_identity(alias)
                for alias in term["aliases"]
                if _contains(normalized_text, normalize_concept_identity(alias))
            }
        )
        if not matched_aliases:
            continue
        senses = sorted(
            (_sense_row(sense, normalized_text, domain) for sense in term["senses"]),
            key=lambda row: row["sense_id"],
        )
        exact_identifier = [
            row for row in senses if row["sense_id"] in identifier_sense_ids
        ]
        ranked = sorted(
            senses,
            key=lambda row: (
                -int(row["domain_match"]),
                -len(row["matched_context_terms"]),
                row["sense_id"],
            ),
        )
        if len(exact_identifier) == 1:
            selected = exact_identifier[0]
        else:
            best = (
                int(ranked[0]["domain_match"]),
                len(ranked[0]["matched_context_terms"]),
            )
            second = (
                int(ranked[1]["domain_match"]),
                len(ranked[1]["matched_context_terms"]),
            )
            selected = ranked[0] if best > second and best != (0, 0) else None
        disposition = "resolved_context" if selected else "agent_resolution_required"
        identity = {
            "term_id": term["id"],
            "normalized_match": term["term"],
            "aliases": matched_aliases,
        }
        rows.append(
            {
                "match_id": _match_id(identity),
                "match_type": "homonym",
                "normalized_match": normalize_concept_identity(term["term"]),
                "disposition": disposition,
                "candidate_senses": senses,
                "selected_sense_id": selected["sense_id"] if selected else None,
                "selected_concept_ids": selected["concept_ids"] if selected else [],
            }
        )
    return sorted(rows, key=lambda row: (row["normalized_match"], row["match_id"]))


@authority_reader("terminology_resolution")
def resolve_terminology(
    text: str,
    domain: str | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Return deterministic identifier/context decisions and bounded agent tasks."""
    if not isinstance(text, str) or not text.strip():
        raise ValidationFailure("terminology text must be a non-empty string")
    registry = load_ontology_registry(root)
    registry_hash = sha256_value(registry)
    normalized_text = normalize_concept_identity(text)
    identifiers = _identifier_matches(text, registry)
    identifier_senses = {
        row["selected_sense_id"] for row in identifiers
    }
    homonyms = _term_matches(
        normalized_text, domain, registry, identifier_senses
    )
    matches = sorted(
        identifiers + homonyms,
        key=lambda row: (row["normalized_match"], row["match_type"], row["match_id"]),
    )
    unresolved = [
        row for row in matches if row["disposition"] == "agent_resolution_required"
    ]
    if unresolved:
        state = "agent_resolution_required"
        agent_task: dict[str, Any] | None = {
            "operation": "cpcs.terminology.propose",
            "match_ids": sorted(row["match_id"] for row in unresolved),
            "allowed_sense_ids": sorted(
                {
                    sense["sense_id"]
                    for row in unresolved
                    for sense in row["candidate_senses"]
                }
            ),
            "requirements": [
                "select_one_allowed_sense",
                "cite_hash_verified_source_units",
                "preserve_uncertainty",
                "do_not_promote",
            ],
        }
    else:
        state = "resolved_deterministically" if matches else "no_registered_term"
        agent_task = None
    identity = {
        "input": {"text": text, "domain": domain},
        "ontology_registry_hash": registry_hash,
        "policy_hash": POLICY_HASH,
    }
    result = {
        "schema": "cpcs.terminology_resolution/1.0",
        "id": "termres_" + hashlib.sha256(canonical_json_bytes(identity)).hexdigest()[:24],
        "policy_version": POLICY["version"],
        "policy_hash": POLICY_HASH,
        "ontology_registry_hash": registry_hash,
        "input": {"text": text, "domain": domain},
        "normalized_text": normalized_text,
        "matches": matches,
        "state": state,
        "candidate_concept_ids": sorted(
            {
                concept_id
                for row in matches
                for sense in row["candidate_senses"]
                for concept_id in sense["concept_ids"]
            }
        ),
        "agent_task": agent_task,
        "authority_effect": "none",
    }
    result["resolution_hash"] = content_hash(result, ("resolution_hash",))
    validate_instance("terminology_resolution", result, root)
    return result


def _proposal_path(root: Path) -> Path:
    return root / PROPOSAL_PATH


def _load_proposals(root: Path) -> list[dict[str, Any]]:
    path = _proposal_path(root)
    rows = read_jsonl(path) if path.exists() else []
    for row in rows:
        validate_instance("terminology_resolution_proposal", row, root)
        if row["proposal_hash"] != content_hash(row, ("proposal_hash",)):
            raise ValidationFailure(
                f"terminology proposal {row['id']} has invalid proposal_hash"
            )
    return rows


def _verified_source_evidence(
    evidence: Iterable[dict[str, str]], root: Path
) -> tuple[list[dict[str, str]], str]:
    units = load_source_units(root)
    by_id = {row["id"]: row for row in units}
    verified: list[dict[str, str]] = []
    for item in evidence:
        unit = by_id.get(item.get("source_unit_id", ""))
        if unit is None:
            raise ValidationFailure(
                f"terminology proposal references missing source unit {item.get('source_unit_id')}"
            )
        if item.get("content_sha256") != unit["content_sha256"]:
            raise ValidationFailure(
                f"terminology proposal source hash mismatch for {unit['id']}"
            )
        verified.append(
            {
                "source_unit_id": unit["id"],
                "content_sha256": unit["content_sha256"],
            }
        )
    unique = {
        (row["source_unit_id"], row["content_sha256"]): row for row in verified
    }
    return [unique[key] for key in sorted(unique)], sha256_value(units)


@authority_writer("terminology")
def propose_terminology_resolution(
    resolution: dict[str, Any],
    match_id: str,
    selected_sense_id: str,
    source_evidence: list[dict[str, str]],
    agent: dict[str, str],
    rationale: str,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Stage one source-backed agent choice without changing canonical identity."""
    validate_instance("terminology_resolution", resolution, root)
    current = resolve_terminology(
        resolution["input"]["text"], resolution["input"]["domain"], root
    )
    if canonical_json_bytes(current) != canonical_json_bytes(resolution):
        raise ValidationFailure("terminology resolution is stale or tampered")
    matches = [row for row in current["matches"] if row["match_id"] == match_id]
    if len(matches) != 1:
        raise ValidationFailure(
            f"expected one terminology match {match_id}, found {len(matches)}"
        )
    match = matches[0]
    if match["disposition"] != "agent_resolution_required":
        raise ValidationFailure("agent proposals are accepted only for unresolved ambiguity")
    senses = {row["sense_id"]: row for row in match["candidate_senses"]}
    if selected_sense_id not in senses:
        raise ValidationFailure(
            f"selected sense {selected_sense_id} is outside the closed candidate set"
        )
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValidationFailure("terminology proposal rationale must be non-empty")
    if set(agent) != {"client", "model", "prompt_sha256"}:
        raise ValidationFailure("terminology proposal agent metadata is not closed")
    if not all(isinstance(agent[key], str) and agent[key] for key in ("client", "model")):
        raise ValidationFailure("terminology proposal agent client and model must be non-empty")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", agent["prompt_sha256"]):
        raise ValidationFailure("terminology proposal prompt_sha256 is invalid")
    verified_sources, source_registry_hash = _verified_source_evidence(
        source_evidence, root
    )
    if not verified_sources:
        raise ValidationFailure("terminology proposal requires source evidence")
    selected = senses[selected_sense_id]
    identity = {
        "resolution_hash": current["resolution_hash"],
        "match_id": match_id,
        "selected_sense_id": selected_sense_id,
        "source_evidence": verified_sources,
        "agent": agent,
        "rationale": rationale,
    }
    proposal = {
        "schema": "cpcs.terminology_resolution_proposal/1.0",
        "id": "termprop_" + hashlib.sha256(canonical_json_bytes(identity)).hexdigest()[:24],
        "policy_version": POLICY["version"],
        "resolution_id": current["id"],
        "resolution_hash": current["resolution_hash"],
        "match_id": match_id,
        "input": current["input"],
        "ontology_registry_hash": current["ontology_registry_hash"],
        "source_registry_hash": source_registry_hash,
        "selected_sense_id": selected_sense_id,
        "selected_concept_ids": selected["concept_ids"],
        "rejected_sense_ids": sorted(set(senses) - {selected_sense_id}),
        "source_evidence": verified_sources,
        "agent": agent,
        "rationale": rationale,
        "status": "agent_resolved_ephemeral_awaiting_review",
        "authority_effect": "staging_only",
    }
    proposal["proposal_hash"] = content_hash(proposal, ("proposal_hash",))
    validate_instance("terminology_resolution_proposal", proposal, root)
    path = _proposal_path(root)
    assert_write_target("terminology", path, root)
    rows = _load_proposals(root)
    matches = [row for row in rows if row["id"] == proposal["id"]]
    if matches:
        if canonical_json_bytes(matches[0]) == canonical_json_bytes(proposal):
            return matches[0]
        raise ValidationFailure(f"terminology proposal ID collision: {proposal['id']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(canonical_json_bytes(proposal))
    return proposal


@authority_reader("terminology_resolution_inspect")
def inspect_terminology_proposal(
    proposal_id: str, root: Path = REPO_ROOT
) -> dict[str, Any]:
    matches = [row for row in _load_proposals(root) if row["id"] == proposal_id]
    if len(matches) != 1:
        raise ValidationFailure(
            f"expected one terminology proposal {proposal_id}, found {len(matches)}"
        )
    proposal = matches[0]
    current = resolve_terminology(
        proposal["input"]["text"], proposal["input"]["domain"], root
    )
    _, source_registry_hash = _verified_source_evidence(
        proposal["source_evidence"], root
    )
    match = next(
        (row for row in current["matches"] if row["match_id"] == proposal["match_id"]),
        None,
    )
    allowed = {
        sense["sense_id"]
        for sense in (match or {}).get("candidate_senses", [])
    }
    checks = {
        "resolution": proposal["resolution_hash"] == current["resolution_hash"],
        "ontology_registry": proposal["ontology_registry_hash"] == current["ontology_registry_hash"],
        "source_registry": proposal["source_registry_hash"] == source_registry_hash,
        "closed_sense": proposal["selected_sense_id"] in allowed,
    }
    return {
        "schema": "cpcs.terminology_resolution_proposal_inspection/1.0",
        "proposal": proposal,
        "current_checks": checks,
        "current": all(checks.values()),
        "authority_effect": "none",
    }


def current_query_terminology_control(
    text: str,
    domain: str | None,
    proposal_ids: Iterable[str],
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Resolve current-query roots while keeping staged agent choices non-authoritative."""
    resolution = resolve_terminology(text, domain, root)
    unresolved = {
        row["match_id"]: row
        for row in resolution["matches"]
        if row["disposition"] == "agent_resolution_required"
    }
    proposals: list[dict[str, Any]] = []
    for proposal_id in proposal_ids:
        inspection = inspect_terminology_proposal(proposal_id, root)
        if not inspection["current"]:
            raise ValidationFailure(f"terminology proposal {proposal_id} is stale")
        proposal = inspection["proposal"]
        if proposal["resolution_id"] != resolution["id"]:
            raise ValidationFailure(
                f"terminology proposal {proposal_id} belongs to another query"
            )
        proposals.append(proposal)
    by_match: dict[str, dict[str, Any]] = {}
    for proposal in proposals:
        if proposal["match_id"] in by_match:
            raise ValidationFailure(
                f"multiple terminology proposals select match {proposal['match_id']}"
            )
        by_match[proposal["match_id"]] = proposal
    forced = {
        concept_id
        for row in resolution["matches"]
        if row["disposition"] != "agent_resolution_required"
        for concept_id in row["selected_concept_ids"]
    }
    forced.update(
        concept_id
        for proposal in proposals
        for concept_id in proposal["selected_concept_ids"]
    )
    gated = {
        concept_id
        for row in resolution["matches"]
        if row["match_type"] == "homonym"
        for sense in row["candidate_senses"]
        for concept_id in sense["concept_ids"]
    }
    selected_senses = {
        concept_id
        for row in resolution["matches"]
        if row["disposition"] != "agent_resolution_required"
        for concept_id in row["selected_concept_ids"]
    } | {
        concept_id
        for proposal in proposals
        for concept_id in proposal["selected_concept_ids"]
    }
    gated -= selected_senses
    unresolved_match_ids = sorted(set(unresolved) - set(by_match))
    return {
        "resolution": resolution,
        "proposal_ids": sorted(proposal["id"] for proposal in proposals),
        "proposal_selections": [
            {
                "proposal_id": proposal["id"],
                "proposal_hash": proposal["proposal_hash"],
                "match_id": proposal["match_id"],
                "selected_sense_id": proposal["selected_sense_id"],
                "selected_concept_ids": proposal["selected_concept_ids"],
                "source_evidence": proposal["source_evidence"],
            }
            for proposal in sorted(proposals, key=lambda row: row["id"])
        ],
        "forced_root_ids": sorted(forced),
        "gated_root_ids": sorted(gated),
        "unresolved_match_ids": unresolved_match_ids,
        "trust_class": (
            "interpreted_agent_resolution"
            if proposals
            else "deterministic_registry_resolution"
        ),
        "authority_effect": "none",
    }


def _candidate_semantic_strings(value: Any, *, field: str | None = None) -> list[str]:
    excluded = {
        "authored_by", "created_at", "evidence", "id", "provenance",
        "source", "sources", "validity",
    }
    if field in excluded:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [
            text
            for item in value
            for text in _candidate_semantic_strings(item, field=field)
        ]
    if isinstance(value, dict):
        return [
            text
            for key, item in sorted(value.items())
            for text in _candidate_semantic_strings(item, field=key)
        ]
    return []


def _candidate_domain(
    candidate: dict[str, Any],
    registry: dict[str, Any],
    root: Path,
    concept_records: dict[str, dict[str, Any]] | None,
) -> str | None:
    record = candidate["proposed_record"]
    if candidate["proposal_type"] == "concept":
        return registry["layers"].get(record.get("layer"))
    concept_ids: set[str] = set()
    if candidate["proposal_type"] == "edge":
        concept_ids.update(
            value for value in (record.get("u"), record.get("v")) if value
        )
    elif candidate["proposal_type"] == "mapping":
        if record.get("concept_id"):
            concept_ids.add(record["concept_id"])
    else:
        concept_ids.update(record.get("concept_ids", []))
    concepts = {
        row["id"]: row for row in read_jsonl(root / "lab" / "concepts.jsonl")
    }
    concepts.update(concept_records or {})
    roots = {
        registry["layers"].get(concepts[concept_id].get("layer"))
        for concept_id in concept_ids
        if concept_id in concepts
    }
    roots.discard(None)
    return next(iter(roots)) if len(roots) == 1 else None


def candidate_terminology_control(
    candidate: dict[str, Any],
    proposal_ids: Iterable[str] = (),
    root: Path = REPO_ROOT,
    *,
    concept_records: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Apply the same resolver to one extracted or distilled candidate."""
    registry = load_ontology_registry(root)
    strings = _candidate_semantic_strings(candidate["proposed_record"])
    text = "\n".join(dict.fromkeys(item.strip() for item in strings if item.strip()))
    if not text:
        text = candidate["candidate_id"]
    domain = _candidate_domain(candidate, registry, root, concept_records)
    control = current_query_terminology_control(
        text, domain, proposal_ids, root
    )
    return {
        "candidate_id": candidate["candidate_id"],
        "input_text": text,
        "domain": domain,
        **control,
    }


def terminology_handoff(control: dict[str, Any]) -> dict[str, Any]:
    """Return the compact, recomputable terminology boundary for context clients."""
    resolution = control["resolution"]
    return {
        "resolution_id": resolution["id"],
        "resolution_hash": resolution["resolution_hash"],
        "ontology_registry_hash": resolution["ontology_registry_hash"],
        "state": resolution["state"],
        "proposal_ids": list(control["proposal_ids"]),
        "proposal_selections": list(control["proposal_selections"]),
        "forced_root_ids": list(control["forced_root_ids"]),
        "gated_root_ids": list(control["gated_root_ids"]),
        "unresolved_match_ids": list(control["unresolved_match_ids"]),
        "trust_class": control["trust_class"],
        "authority_effect": "none",
    }


def validate_terminology_handoff(
    text: str,
    domain: str | None,
    handoff: dict[str, Any],
    root: Path = REPO_ROOT,
    *,
    require_resolved: bool,
) -> dict[str, Any]:
    """Recompute a context handoff and optionally stop compiler admission."""
    current = current_query_terminology_control(
        text, domain, handoff.get("proposal_ids", []), root
    )
    expected = terminology_handoff(current)
    if canonical_json_bytes(expected) != canonical_json_bytes(handoff):
        no_term_replay = all(
            value.get("state") == "no_registered_term"
            and not value.get("proposal_ids")
            and not value.get("forced_root_ids")
            and not value.get("gated_root_ids")
            and not value.get("unresolved_match_ids")
            for value in (expected, handoff)
        )
        if not no_term_replay:
            raise ValidationFailure("terminology context handoff is stale or tampered")
    if require_resolved and current["unresolved_match_ids"]:
        raise ValidationFailure(
            "compiler admission requires resolved terminology: "
            + ",".join(current["unresolved_match_ids"])
        )
    return current
