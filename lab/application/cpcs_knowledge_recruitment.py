"""KA-2 WP-2 — Intent-Conditioned Recruitment Gate.

Assigns exactly one `RecruitmentDisposition` to every region in a
`KnowledgeConstellation`, driven by structured intent signals from the
activation packet. Nothing silently dropped. COVERAGE_GAP is reported
as a separate field on the refinement (per constellation), not as a
region disposition.

Dispositions:
  RECRUIT, CONTEXT, ARCHIVE, UNRESOLVED

Coverage gaps:
  COVERAGE_GAP (per intent, not per region)

Pure functions of their inputs. Deterministic ordering by region_id.

FROZEN: do not mutate the constellation; the recruiter is a downstream
consumer of `KnowledgeConstellation` plus activation.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from lab.application.cpcs_deliberation import (
    NON_EXECUTABLE_AFFORDANCES,
    PLANNING_AFFORDANCES,
)

DISPOSITION_SCHEMA = "cpcs.recruitment_disposition/0.1"
RECRUITMENT_SCHEMA = "cpcs.recruitment_set/0.1"

DISPOSITIONS = frozenset({"RECRUIT", "CONTEXT", "ARCHIVE", "UNRESOLVED"})
STRENGTH = {"RECRUIT": 3, "CONTEXT": 2, "ARCHIVE": 1, "UNRESOLVED": 0}

# KA-2.4 recruitment policy: RECRUIT requires a CONSEQUENTIAL reason.
# Reasons carrying real intent-conditioned consequence:
RECRUIT_GRADE_REASONS = frozenset({
    "mandatory_requirement_bound",      # intent requirement + control path
    "intent_predicted_failure_bound",   # intent-predicted failure + control
    "workflow_tag_support",             # corpus doc binding + performance
                                        # signal (consequential conjunction)
    "prerequisite_consequence",         # recruited dependency consequence
})
# Reasons that indicate relatedness but not consequence:
CONTEXT_GRADE_REASONS = frozenset({
    "trigger_contextual",               # snapshot trigger vocab == corpus
                                        # trigger vocab (same-source; demoted
                                        # from trigger_entailment_bound)
    "objective_contextual",
    "failure_contextual",
    "workflow_tag_context",
    "affordance_contextual",
})
RECRUITMENT_POLICY_SNAPSHOT = {
    "policy": "ka2.4-consequence-grade-recruitment",
    "frozen": "2026-08-16",
    "freeze_note": ("frozen after the KA-2.4 audit: consequence-graded "
                    "recruitment produces a subset (R 16-19 of 69-74 "
                    "regions); trigger/tag/dependency promotion require an "
                    "executable or verification surface."),
    "recruit_grade_reasons": sorted(RECRUIT_GRADE_REASONS),
    "context_grade_reasons": sorted(CONTEXT_GRADE_REASONS),
    "note": ("a region recruits only on intent-conditioned consequence; "
             "relatedness alone is CONTEXT; unreferenced evidence is "
             "ARCHIVE; nothing is silently dropped"),
}


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _sorted(values: Any) -> list[str]:
    if not values:
        return []
    return sorted(set(str(v) for v in values if v))


def _affordances_for_region(region: dict[str, Any],
                            pack_lookup: dict[str, dict[str, Any]]
                            ) -> set[str]:
    affs: set[str] = set()
    for pid in region.get("pack_ids", []) or []:
        pack = pack_lookup.get(pid) or {}
        for rec in pack.get("source_records", []) or []:
            ut = rec.get("universal_type")
            if not ut:
                continue
            affs |= set(NON_EXECUTABLE_AFFORDANCES.get(ut, []) or [])
            affs |= set(PLANNING_AFFORDANCES.get(ut, []) or [])
    return affs


@dataclass
class RecruitmentDisposition:
    region_id: str
    disposition: str
    reason_codes: list[str]
    intent_signals: dict[str, list[str]]
    evidence_ids: list[str]
    bound_requirement_ids: list[str]
    bound_failure_family_ids: list[str]
    bound_objective_ids: list[str]
    bound_trigger_ids: list[str]
    contributing_regions: list[str] = field(default_factory=list)
    coverage_gap_emitted: bool = False
    lineage: dict[str, Any] = field(default_factory=dict)
    disposition_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": DISPOSITION_SCHEMA,
            "region_id": self.region_id,
            "disposition": self.disposition,
            "reason_codes": self.reason_codes,
            "intent_signals": self.intent_signals,
            "evidence_ids": self.evidence_ids,
            "bound_requirement_ids": self.bound_requirement_ids,
            "bound_failure_family_ids": self.bound_failure_family_ids,
            "bound_objective_ids": self.bound_objective_ids,
            "bound_trigger_ids": self.bound_trigger_ids,
            "contributing_regions": self.contributing_regions,
            "coverage_gap_emitted": self.coverage_gap_emitted,
            "lineage": self.lineage,
            "disposition_hash": self.disposition_hash,
        }


def match_intent_signals(region: dict[str, Any],
                         activation: dict[str, Any]) -> dict[str, list[str]]:
    candidate_requirements = set(activation.get("candidate_requirements", []) or [])
    candidate_failures = set(activation.get("candidate_failure_families", []) or [])
    candidate_objectives = set(activation.get("candidate_objectives", []) or [])
    activated_triggers = set(activation.get("activated_triggers", []) or [])
    activated_dimensions = set(activation.get("activated_reasoning_dimensions", []) or [])
    activated_affordances = set(activation.get("activated_reasoning_affordances", []) or [])
    uncovered_mandatory = set(activation.get("initial_unknowns", []) or [])  # placeholder

    return {
        "bound_requirement_ids": _sorted(
            set(region.get("requirement_ids", []) or []) & candidate_requirements),
        "bound_failure_family_ids": _sorted(
            set(region.get("failure_family_ids", []) or []) & candidate_failures),
        "bound_objective_ids": _sorted(
            set(region.get("objective_ids", []) or []) & candidate_objectives),
        # Trigger binding is only meaningful against the SNAPSHOT-side
        # activated trigger vocabulary (intent-conditioned). The evidence
        # trigger vocabulary is the same retrieval source as
        # activated_concepts, so intersecting with it is vacuous.
        "bound_trigger_ids": _sorted(
            set(region.get("trigger_ids", []) or []) & activated_triggers),
        "activated_dimensions": _sorted(activated_dimensions),
        "activated_affordances": _sorted(activated_affordances),
        "uncovered_mandatory_ids": _sorted(uncovered_mandatory),
    }


def recruit_for_intent(
    constellation: Any,
    activation: dict[str, Any],
    *,
    pack_lookup: dict[str, dict[str, Any]] | None = None,
    awareness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the recruitment gate. Returns a recruitment set with one
    disposition per region plus a list of typed COVERAGE_GAPs."""
    regions = list(getattr(constellation, "regions", []) or [])
    if regions and isinstance(regions[0], dict) and "region_id" in regions[0]:
        region_dicts = regions
    else:
        region_dicts = [r.to_dict() if hasattr(r, "to_dict") else r for r in regions]
    pack_lookup = pack_lookup or {}
    candidate_requirements = set(activation.get("candidate_requirements", []) or [])
    candidate_failures = set(activation.get("candidate_failure_families", []) or [])
    candidate_objectives = set(activation.get("candidate_objectives", []) or [])
    activated_triggers = set(activation.get("activated_triggers", []) or [])
    activated_affordances = set(activation.get("activated_reasoning_affordances", []) or [])
    activated_dimensions = set(activation.get("activated_reasoning_dimensions", []) or [])

    # PASS-1 workflow-tag support: tags ADD evidence (L2 tag -> corpus doc
    # IDs -> region evidence). A tag recruits only when its corpus docs are
    # present in the region AND the intent carries the consequential signal
    # (e.g., a visible performer for FACS). Tags are never the sole reason.
    awareness = awareness or {}
    candidate_tags: dict[str, dict[str, Any]] = {
        t["tag"]: t for t in awareness.get("candidate_expertise_tags", []) or []}
    performance_signals = (awareness.get("intent_signals", {}) or {}).get(
        "performance", []) or []

    per_region_strength: dict[str, int] = {}
    dispositions: list[RecruitmentDisposition] = []
    region_evidence_coverage: dict[str, set[str]] = {}
    region_id_set: set[str] = set()
    covered_requirements: set[str] = set()
    covered_failures: set[str] = set()

    # Intent-conditioned failure signal (PASS-1 structured vocab). Failure
    # families that appear ONLY in retrieved evidence are same-source with
    # the region facets and can only earn CONTEXT; failures the intent
    # itself predicts earn RECRUIT.
    intent_predicted_failures = set(
        awareness.get("predicted_failure_families", []) or [])

    for region in region_dicts:
        rid = region["region_id"]
        region_id_set.add(rid)
        region_evidence_coverage[rid] = set(region.get("evidence_ids", []) or [])
        signals = match_intent_signals(region, activation)
        affs = _affordances_for_region(region, pack_lookup)
        decision_mix = region.get("representation_mix", {}) or {}
        has_control_or_composite = bool(
            (decision_mix.get("CONTROL", 0) or 0)
            + (decision_mix.get("COMPOSITE", 0) or 0))
        has_verification_decision = bool(decision_mix.get("VERIFICATION", 0))
        reasons: list[str] = []
        strength = 1
        disposition = "ARCHIVE"
        bound_reqs = set(signals["bound_requirement_ids"])
        bound_failures = set(signals["bound_failure_family_ids"])
        bound_objectives = set(signals["bound_objective_ids"])
        bound_triggers = set(signals["bound_trigger_ids"])

        # KA-2.4 consequence grading: a mandatory-requirement binding is
        # consequential when the region ALSO carries an intent-conditioned
        # failure signal or is a hard-constraint family. Requirement-only
        # overlap is query-attribution (same-source) and stays CONTEXT.
        bound_intent_failures = bound_failures & intent_predicted_failures
        hard_family = bool(
            set(region.get("principle_families", []) or [])
            & {"protected_invariant"})
        has_surface = (has_control_or_composite or has_verification_decision)
        if bound_reqs and has_surface:
            covered_requirements |= bound_reqs
            if bound_intent_failures or hard_family:
                reasons.append("mandatory_requirement_bound")
                strength = max(strength, STRENGTH["RECRUIT"])
                disposition = "RECRUIT"
            else:
                reasons.append("requirement_contextual")
                strength = max(strength, STRENGTH["CONTEXT"])
                if STRENGTH[disposition] < STRENGTH["CONTEXT"]:
                    disposition = "CONTEXT"
        if bound_intent_failures and has_surface:
            reasons.append("intent_predicted_failure_bound")
            strength = max(strength, STRENGTH["RECRUIT"])
            disposition = "RECRUIT"
            covered_failures |= bound_intent_failures
        if bound_failures and has_control_or_composite:
            reasons.append("failure_contextual")
            strength = max(strength, STRENGTH["CONTEXT"])
            if STRENGTH[disposition] < STRENGTH["CONTEXT"]:
                disposition = "CONTEXT"
        if bound_objectives:
            reasons.append("objective_contextual")
            strength = max(strength, STRENGTH["CONTEXT"])
            if STRENGTH[disposition] < STRENGTH["CONTEXT"]:
                disposition = "CONTEXT"
        if bound_triggers:
            # KA-2.4: demoted from RECRUIT-grade. The snapshot trigger
            # vocabulary is drawn from the same frozen corpus as the
            # evidence trigger vocabulary, so this binding is same-source
            # at real-runtime scale (trigger_entailment_bound fired on
            # every region and destroyed selectivity).
            reasons.append("trigger_contextual")
            strength = max(strength, STRENGTH["CONTEXT"])
            if STRENGTH[disposition] < STRENGTH["CONTEXT"]:
                disposition = "CONTEXT"
        if not reasons and affs & activated_affordances:
            reasons.append("affordance_contextual")
            strength = max(strength, STRENGTH["CONTEXT"])
            if STRENGTH[disposition] < STRENGTH["CONTEXT"]:
                disposition = "CONTEXT"
        if candidate_tags:
            region_docs = set(region.get("corpus_doc_ids", []) or [])
            supporting_tags = sorted(
                tag for tag, meta in candidate_tags.items()
                if set(meta.get("corpus_doc_ids", []) or []) & region_docs)
            if supporting_tags:
                # KA-2.4 consequence gate: tag support recruits only when
                # the region carries an executable/verifiable surface AND
                # the consequential performance signal is present. Doc-id
                # overlap alone is same-source evidence (whole research
                # packages span many expertise areas).
                has_surface = (has_control_or_composite
                               or has_verification_decision)
                if performance_signals and has_surface:
                    reasons.append("workflow_tag_support")
                    strength = max(strength, STRENGTH["RECRUIT"])
                    if STRENGTH[disposition] < STRENGTH["RECRUIT"]:
                        disposition = "RECRUIT"
                else:
                    reasons.append("workflow_tag_context")
                    strength = max(strength, STRENGTH["CONTEXT"])
                    if STRENGTH[disposition] < STRENGTH["CONTEXT"]:
                        disposition = "CONTEXT"
        if not reasons and region.get("evidence_ids"):
            reasons.append("peripheral_to_intent")
            strength = max(strength, STRENGTH["ARCHIVE"])
            if STRENGTH[disposition] < STRENGTH["ARCHIVE"]:
                disposition = "ARCHIVE"
        if not region.get("evidence_ids") and not region.get("pack_ids"):
            reasons.append("no_evidence_under_frozen_window")
            disposition = "UNRESOLVED"
            strength = STRENGTH["UNRESOLVED"]

        per_region_strength[rid] = strength
        intent_signals_out = {
            "activated_dimensions": signals["activated_dimensions"],
            "activated_affordances": signals["activated_affordances"],
            "bound_requirement_ids": _sorted(bound_reqs),
            "bound_failure_family_ids": _sorted(bound_failures),
            "bound_objective_ids": _sorted(bound_objectives),
            "bound_trigger_ids": _sorted(bound_triggers),
        }
        disp = RecruitmentDisposition(
            region_id=rid,
            disposition=disposition,
            reason_codes=sorted(set(reasons)),
            intent_signals=intent_signals_out,
            evidence_ids=sorted(region.get("evidence_ids", []) or []),
            bound_requirement_ids=sorted(bound_reqs),
            bound_failure_family_ids=sorted(bound_failures),
            bound_objective_ids=sorted(bound_objectives),
            bound_trigger_ids=sorted(bound_triggers),
            contributing_regions=[],
            coverage_gap_emitted=False,
            lineage={
                "activation_packet_id": (activation or {}).get("packet_id", "unknown"),
                "constellation_id": getattr(constellation, "constellation_id", "unknown"),
            },
        )
        body = {k: v for k, v in disp.to_dict().items() if k != "disposition_hash"}
        disp.disposition_hash = _sha(body)
        dispositions.append(disp)

    dependency_consequence = []
    for edge in (getattr(constellation, "region_dependency_edges", []) or []):
        from_rid = edge.get("from")
        to_rid = edge.get("to")
        if not from_rid or not to_rid:
            continue
        from_disp = next((d for d in dispositions if d.region_id == from_rid), None)
        to_disp = next((d for d in dispositions if d.region_id == to_rid), None)
        if not from_disp or not to_disp:
            continue
        if from_disp.disposition == "RECRUIT" and to_disp.disposition != "RECRUIT":
            to_affs = _affordances_for_region(
                next(r for r in region_dicts if r["region_id"] == to_rid),
                pack_lookup,
            )
            # KA-2.4 consequence gate: dependency promotion requires the
            # target to carry an executable/verifiable surface. Affordance
            # overlap alone is same-source (activation affordances derive
            # from the same retrieved evidence) and promoted 46/74 regions.
            to_mix = next(
                (r.get("representation_mix", {}) or {}
                 for r in region_dicts if r["region_id"] == to_rid), {})
            to_has_surface = bool(
                (to_mix.get("CONTROL", 0) or 0)
                + (to_mix.get("COMPOSITE", 0) or 0)
                + (to_mix.get("VERIFICATION", 0) or 0))
            if to_affs & activated_affordances and to_has_surface:
                dependency_consequence.append(to_rid)
                if STRENGTH[to_disp.disposition] < STRENGTH["RECRUIT"]:
                    to_disp.disposition = "RECRUIT"
                    to_disp.reason_codes = sorted(
                        set(to_disp.reason_codes) | {"prerequisite_consequence"})
                to_disp.contributing_regions = sorted(
                    set(to_disp.contributing_regions) | {from_rid})
                body = {k: v for k, v in to_disp.to_dict().items()
                        if k != "disposition_hash"}
                to_disp.disposition_hash = _sha(body)

    coverage_gaps: list[dict[str, Any]] = []
    for req in sorted(candidate_requirements - covered_requirements):
        coverage_gaps.append({
            "coverage_gap_id": "gap_" + _sha(req)[:16],
            "kind": "mandatory_requirement_uncovered",
            "requirement_id": req,
            "evidence_ids": [],
            "reason": "no recruited region binds this mandatory requirement",
        })
    for ff in sorted(intent_predicted_failures - covered_failures):
        coverage_gaps.append({
            "coverage_gap_id": "gap_" + _sha(ff)[:16],
            "kind": "predicted_failure_uncovered",
            "failure_family_id": ff,
            "evidence_ids": [],
            "reason": "no recruited region covers this intent-predicted failure family",
        })
    for dim in sorted(activated_dimensions):
        matched = any(
            (dim.replace("DIM-", "").lower() in (p.get("principle_families") or []))
            or (dim in (r.get("principle_families") or []))
            for r in region_dicts
            for p in [r]
        )
        if not matched:
            coverage_gaps.append({
                "coverage_gap_id": "gap_dim_" + _sha(dim)[:16],
                "kind": "reasoning_dimension_unsupported",
                "dimension_id": dim,
                "evidence_ids": [],
                "reason": "activation invokes a reasoning dimension with no "
                          "corpus-backed region in the retrieved window",
            })

    dispositions.sort(key=lambda d: d.region_id)
    body = {
        "dispositions": [d.to_dict() for d in dispositions],
        "coverage_gaps": coverage_gaps,
        "dependency_consequence": sorted(dependency_consequence),
    }
    recruitment_hash = _sha(body)
    return {
        "schema": RECRUITMENT_SCHEMA,
        "recruitment_id": "recruit_" + _sha(recruitment_hash)[:16],
        "recruitment_hash": recruitment_hash,
        "dispositions": [d.to_dict() for d in dispositions],
        "coverage_gaps": coverage_gaps,
        "dependency_consequence": sorted(dependency_consequence),
        "recruitment_policy": dict(RECRUITMENT_POLICY_SNAPSHOT),
        "lineage": {
            "activation_packet_id": (activation or {}).get("packet_id", "unknown"),
            "constellation_id": getattr(constellation, "constellation_id", "unknown"),
            "region_count": len(dispositions),
            "coverage_gap_count": len(coverage_gaps),
        },
    }
