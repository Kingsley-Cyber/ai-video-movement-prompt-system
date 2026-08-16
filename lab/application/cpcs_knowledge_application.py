"""KA-1 — Knowledge Application Bridge.

Sits between DR-1 deliberation and typed mapping:

    DR-1 -> Knowledge Application Bridge -> TreatmentAdapter/Typed Mapping ->
    CanonicalScore

Answers "how does retrieved knowledge apply to THIS creative intent?" — not
"what evidence exists" (retrieval) and not "what conclusions follow" (DR-1).

Deterministic binding rules (frozen here, per WP-2/WP-3/WP-4):

- Principle templates are keyed by evidence universal_type + failure families
  + objectives. NO prose mining: template text is constant per family and
  interpolates only structured IDs/tokens.
- Mechanism binding: Mechanism/Procedure/Process records (and any record
  carrying structured mechanism_tokens) whose supported_requirement_ids
  overlap the pack's requirement set.
- Risk binding: FailureMode/NegativeConstraint records overlapping the same
  requirements; risk tokens are structured fixture fields; contradiction
  records preserved via lineage.
- evidence_ids + source_records: IDs only (D4). No flat-text admission.
- intent_application: structured tags from the activation packet (domains,
  triggers, objectives) — never free text.
- Representation decisions follow the frozen priority rules in
  decide_representation; every NON_EXECUTABLE universal type in the TC-2
  ledger can never yield CONTROL.
- A resolved canonical score is never mutated post-resolution.

Pure functions of their inputs; deterministic ordering by
(principle_family, requirement_ids, pack_id).
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
from lab.application.tc2_classify import (
    EXECUTABLE_BY_UT,
    NON_EXECUTABLE_BY_UT,
)
from lab.compiler import cpcs_typed

PACK_SCHEMA = "cpcs.principle_pack/0.1"
DECISION_SCHEMA = "cpcs.representation_decision/0.1"

# principle family keyed by failure family (combat/contact chain first)
PRINCIPLE_FAMILY_BY_FAILURE = {
    "FF-CONTACT": "support_contact_chain",
    "FF-SUPPORT": "support_state_chain",
    "FF-ROTATION": "rotation_axis_discipline",
    "FF-IDENTITY": "identity_continuity",
    "FF-VISIBILITY": "visibility_continuity",
    "FF-DEFORMATION": "deformation_control",
    "FF-SAFETY": "safety_constraint",
}

PRINCIPLE_TEMPLATES = {
    "support_contact_chain": (
        "a believable contact is a force-transfer chain across a contact "
        "interval; state transitions must be represented"),
    "support_state_chain": (
        "support changes are a subset of contact topology; each phase records "
        "its support state"),
    "rotation_axis_discipline": (
        "projection rotation keeps one rotation axis and one rotating actor"),
    "identity_continuity": (
        "objects keep identity through manipulation; defining features stay "
        "visible"),
    "visibility_continuity": (
        "visibility changes are not existence changes; visibility states stay "
        "explicit"),
    "deformation_control": (
        "material interaction needs a causal deformation response object"),
    "safety_constraint": (
        "safety constraints protect hands and surfaces during execution"),
    "protected_invariant": (
        "a protected invariant constrains execution and is never a decorative "
        "preference"),
    "mechanism_binding": (
        "a bound mechanism explains how the requirement is satisfied"),
    "grounded_principle": "a source principle constrains the representation",
    "evidence_binding": "evidence binds to the activated requirements",
    "failure_prevention": (
        "predicted failure families must be prevented by explicit "
        "representation"),
    # KA-1.1 role-based families (reasoning role, never semantic subject)
    "conceptual_foundation": (
        "a source concept defines the vocabulary for this reasoning problem"),
    "evidence_interpretation": (
        "interpreted evidence informs expectations and never becomes a "
        "control"),
    "provenance_metadata": "provenance metadata anchors evidence lineage",
    "research_governance": (
        "research governance frames what is known versus what is open"),
    "verification_guidance": (
        "verification guidance defines how an expectation is checked"),
    "provider_guidance": (
        "provider realization guidance is capability-scoped"),
    "expected_state_guidance": (
        "expected-state guidance describes outcomes to verify"),
    "recommendation_guidance": (
        "a grounded recommendation suggests a directing choice"),
    "example_guidance": "a worked example transfers by analogy",
    "decision_guidance": "a decision rule resolves directing conflicts",
    "specification_guidance": "a specification constrains representation",
    "planning_guidance": "planning guidance orders the reasoning work",
}

HARD_UNIVERSAL_TYPES = frozenset(
    {"Constraint", "NegativeConstraint", "Invariant", "FailureMode"}
)
MECHANISM_UNIVERSAL_TYPES = frozenset(
    {"Mechanism", "Procedure", "Process", "ProcessStep", "Workflow"}
)

# TC-2 ledger dispositions that can never become generation controls.
NEVER_CONTROL_UNIVERSAL_TYPES = frozenset({
    ut for ut, disposition in dict(NON_EXECUTABLE_BY_UT, **EXECUTABLE_BY_UT).items()
    if disposition not in ("cpcs.continuity.invariant", "cpcs.constraint.negative")
})

DECISIONS_ALLOWED = frozenset(
    {"CONTROL", "VERIFICATION", "PLANNING", "NON_EXECUTABLE", "COMPOSITE"}
)

DECISION_AUTHORITY = {
    "CONTROL": "CPCS_SAFE_INFERENCE",
    "VERIFICATION": "CPCS_SAFE_INFERENCE",
    "PLANNING": "CPCS_GROUNDED_RECOMMENDATION",
    "NON_EXECUTABLE": "LEAVE_UNSPECIFIED",
    "COMPOSITE": "CPCS_HARD_REQUIREMENT",
}


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _overlap(a: list[str], b: list[str]) -> bool:
    return bool(set(a) & set(b))


# ---------------------------------------------------------------------------
# KA-1.1 principle-family vocabulary resolution (role-based, frozen-corpus
# grounded). principle_family = REASONING ROLE, never the semantic subject.
# The mapping derives from the repo's own frozen TC-2 disposition ledger —
# no prose classification, no new ontology, no LLM.
# ---------------------------------------------------------------------------
_DISPOSITION_FAMILY = {
    "NON_EXECUTABLE_KNOWLEDGE": "conceptual_foundation",
    "EPISTEMIC_METADATA": "evidence_interpretation",
    "PROVENANCE_ONLY": "provenance_metadata",
    "RESEARCH_GOVERNANCE": "research_governance",
    "VERIFICATION_ONLY": "verification_guidance",
    "PROVIDER_ONLY": "provider_guidance",
    "EXPECTED_STATE_ONLY": "expected_state_guidance",
}
# PLANNING_ONLY splits by reasoning role (from the frozen ledger's member
# universal types; Mechanism/Procedure/Process/ProcessStep/Workflow keep the
# existing mechanism_binding family).
PLANNING_ROLE_FAMILY = {
    "Recommendation": "recommendation_guidance",
    "Technique": "recommendation_guidance",
    "Heuristic": "recommendation_guidance",
    "Example": "example_guidance",
    "WorkedExample": "example_guidance",
    "DecisionRule": "decision_guidance",
    "ConditionalRule": "decision_guidance",
    "Default": "decision_guidance",
    "DesignDecision": "decision_guidance",
    "Policy": "decision_guidance",
    "Doctrine": "decision_guidance",
    "Corollary": "decision_guidance",
    "Specification": "specification_guidance",
    "Contract": "specification_guidance",
    "ControlVariable": "specification_guidance",
}
# Corpus universal types absent from the frozen TC-2 ledger. Family-level
# supplement ONLY: the TC-2 ledger itself is untouched.
_LOCAL_DISPOSITION_SUPPLEMENT = {
    "Evidence": "evidence_interpretation",
}

PRINCIPLE_FAMILY_VOCABULARY = frozenset({
    "failure_prevention", "protected_invariant", "mechanism_binding",
    "grounded_principle", "conceptual_foundation", "evidence_interpretation",
    "provenance_metadata", "research_governance", "verification_guidance",
    "provider_guidance", "expected_state_guidance",
    "recommendation_guidance", "example_guidance", "decision_guidance",
    "specification_guidance", "planning_guidance",
})


def _principle_family(record: dict[str, Any]) -> str:
    ut = record.get("universal_type")
    if ut == "FailureMode":
        for ff in sorted(record.get("failure_family_ids", []) or []):
            if ff in PRINCIPLE_FAMILY_BY_FAILURE:
                return PRINCIPLE_FAMILY_BY_FAILURE[ff]
        return "failure_prevention"
    if ut in HARD_UNIVERSAL_TYPES - {"FailureMode"}:
        return "protected_invariant"
    if ut in MECHANISM_UNIVERSAL_TYPES:
        return "mechanism_binding"
    if ut == "Principle":
        return "grounded_principle"
    # KA-1.1: non-executable classes resolve to their frozen TC-2 reasoning
    # role instead of one undifferentiated evidence_binding catch-all.
    disposition = NON_EXECUTABLE_BY_UT.get(ut) or EXECUTABLE_BY_UT.get(ut)
    if ut in _LOCAL_DISPOSITION_SUPPLEMENT:
        return _LOCAL_DISPOSITION_SUPPLEMENT[ut]
    if disposition in ("cpcs.continuity.invariant", "cpcs.constraint.negative"):
        # executable classes whose TC-2 target is a registry family
        # (Rule / Requirement and friends) join the protected-invariant
        # reasoning role instead of the non-executable catch-all.
        return "protected_invariant"
    if disposition in _DISPOSITION_FAMILY:
        return _DISPOSITION_FAMILY[disposition]
    if disposition == "PLANNING_ONLY":
        if ut in PLANNING_ROLE_FAMILY:
            return PLANNING_ROLE_FAMILY[ut]
        return "planning_guidance"
    return "evidence_binding"


@dataclass
class PrinciplePack:
    """One principle bound to its mechanism, predicted failure, and evidence."""

    pack_id: str
    pack_hash: str
    principle_family: str
    principle: str
    mechanism: str
    failure_risk: dict[str, Any]
    evidence_ids: list[str]
    source_records: list[dict[str, Any]]
    intent_application: dict[str, Any]
    lineage: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PACK_SCHEMA,
            "pack_id": self.pack_id,
            "pack_hash": self.pack_hash,
            "principle_family": self.principle_family,
            "principle": self.principle,
            "mechanism": self.mechanism,
            "failure_risk": self.failure_risk,
            "evidence_ids": self.evidence_ids,
            "source_records": self.source_records,
            "intent_application": self.intent_application,
            "lineage": self.lineage,
        }


def build_principle_packs(
    treatment_packet: dict[str, Any],
    snapshot: Any,
    activation: dict[str, Any],
) -> list[PrinciplePack]:
    """WP-2: deterministic principle + mechanism + risk binding.

    Pure function of (treatment_packet, snapshot, activation). Snapshot is
    accepted for call-shape symmetry but is not mutated or needed by the
    current deterministic rules."""
    del snapshot  # reserved for future requirement-led binding; not needed yet
    evidence = treatment_packet.get("retrieved_evidence", []) or []
    obligations = treatment_packet.get("verification_obligations", []) or []
    controls = treatment_packet.get("proposed_controls", []) or []
    domains = sorted(set(activation.get("activated_domains", []) or []))
    triggers = sorted(set(activation.get("activated_triggers", []) or []))
    objectives = sorted(set(activation.get("candidate_objectives", []) or []))
    packs: list[PrinciplePack] = []
    for record in evidence:
        arid = record.get("atomic_record_id")
        if not arid:
            continue
        req_ids = sorted(set(record.get("supported_requirement_ids", []) or []))
        family = _principle_family(record)
        mechanism_records = [
            r for r in evidence
            if r.get("atomic_record_id")
            and (r.get("universal_type") in MECHANISM_UNIVERSAL_TYPES
                 or r.get("mechanism_tokens"))
            and _overlap(r.get("supported_requirement_ids", []) or [], req_ids)
        ]
        risk_records = [
            r for r in evidence
            if r.get("atomic_record_id")
            and r.get("universal_type") in ("FailureMode", "NegativeConstraint")
            and _overlap(r.get("supported_requirement_ids", []) or [], req_ids)
        ]
        risk_tokens = sorted({
            token for r in risk_records for token in (r.get("risk_tokens") or [])
        })
        if (record.get("universal_type") in MECHANISM_UNIVERSAL_TYPES
                or record.get("mechanism_tokens")):
            mechanism_tokens = sorted(record.get("mechanism_tokens") or [])
        else:
            mechanism_tokens = sorted({
                token
                for r in mechanism_records
                for token in (r.get("mechanism_tokens") or [])
            })
        source_ids = sorted({arid} | {r["atomic_record_id"] for r in mechanism_records})
        evidence_ids = sorted(
            {arid} | {r["atomic_record_id"] for r in mechanism_records}
            | {r["atomic_record_id"] for r in risk_records}
        )
        failure_family_ids = sorted({
            ff
            for rid in evidence_ids
            for ff in (next((e.get("failure_family_ids", []) or []
                             for e in evidence if e.get("atomic_record_id") == rid),
                            []) or [])
        })
        source_records = [
            {
                "atomic_record_id": r["atomic_record_id"],
                "universal_type": r["universal_type"],
                "epistemic_status": r.get("epistemic_status") or "unknown",
            }
            for r in sorted(evidence, key=lambda x: x.get("atomic_record_id", ""))
            if r.get("atomic_record_id") in source_ids
            and r.get("universal_type")
        ]
        contradiction_ids = sorted({
            cid
            for r in evidence
            if r.get("atomic_record_id") in evidence_ids
            for cid in (r.get("contradiction_ids", []) or [])
        })
        control_types: list[str] = []
        for c in controls:
            if _overlap(c.get("source_requirement_ids", []) or [], req_ids):
                for ct in (c.get("control_type", []) or []):
                    if ct not in control_types:
                        control_types.append(ct)
        obligation_ids = sorted({
            v.get("obligation_id")
            for v in obligations
            if (v.get("requirement_id") in set(req_ids) or not req_ids)
            and v.get("obligation_id")
        })
        lineage = {
            "requirement_ids": req_ids,
            "treatment_packet_hash": treatment_packet.get("packet_hash", "unknown"),
            "activation_packet_id": activation.get("packet_id", "unknown"),
            "control_types": control_types,
            "verification_obligation_ids": obligation_ids,
            "contradiction_ids": contradiction_ids,
        }
        mechanism = ("mechanism: " + ", ".join(mechanism_tokens)
                     if mechanism_tokens else "mechanism: none")
        risk_statement = ("risk: " + ", ".join(risk_tokens or failure_family_ids)
                          if (risk_tokens or failure_family_ids) else "risk: none")
        pack_id = "pack_" + _sha("|".join([family] + req_ids + evidence_ids))[:20]
        pack = PrinciplePack(
            pack_id=pack_id,
            pack_hash="",
            principle_family=family,
            principle=PRINCIPLE_TEMPLATES[family],
            mechanism=mechanism,
            failure_risk={
                "failure_family_ids": failure_family_ids,
                "risk_tokens": risk_tokens,
                "risk_statement": risk_statement,
            },
            evidence_ids=evidence_ids,
            source_records=source_records,
            intent_application={
                "domain_tags": domains,
                "creative_goal_tags": triggers,
                "trigger_ids": triggers,
                "objective_ids": objectives,
            },
            lineage=lineage,
        )
        pack.pack_hash = _sha(pack.to_dict())
        packs.append(pack)
    packs.sort(key=lambda p: (p.principle_family, tuple(p.lineage["requirement_ids"]),
                              p.pack_id))
    return packs


@dataclass
class RepresentationDecision:
    """How one PrinciplePack applies to this creative intent."""

    knowledge_id: str
    decision: str
    rationale: str
    authority: str
    target_family: str | None
    forbidden_coercions: list[str]
    verification_counterpart: str | None
    decision_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": DECISION_SCHEMA,
            "knowledge_id": self.knowledge_id,
            "decision": self.decision,
            "rationale": self.rationale,
            "authority": self.authority,
            "target_family": self.target_family,
            "forbidden_coercions": self.forbidden_coercions,
            "verification_counterpart": self.verification_counterpart,
            "decision_hash": self.decision_hash,
        }


def _registry_target(pack: PrinciplePack) -> tuple[str | None, dict[str, Any] | None]:
    control_types = pack.lineage.get("control_types", []) or []
    probe = {"control_id": pack.pack_id, "control_type": control_types}
    path_id, entry = cpcs_typed.map_control(probe)
    if path_id:
        return path_id, entry
    return None, None


def _affordances_for(universal_types: set[str]) -> set[str]:
    affordances: set[str] = set()
    for ut in universal_types:
        affordances |= set(NON_EXECUTABLE_AFFORDANCES.get(ut, []))
        affordances |= set(PLANNING_AFFORDANCES.get(ut, []))
    return affordances


_PLANNING_ROUTE_AFFORDANCES = frozenset(
    {"QUERY_STEERING", "HYPOTHESIS_GENERATION", "CONCEPT_RECOGNITION"}
)


def decide_representation(
    pack: PrinciplePack,
    activation: dict[str, Any],
    snapshot: Any,
    registry: dict[str, Any] | None = None,
) -> RepresentationDecision:
    """WP-3: frozen priority decision rules (rule1..rule4)."""
    del activation, snapshot, registry  # registry re-resolved via cpcs_typed
    universal_types = {r["universal_type"] for r in pack.source_records}
    has_hard = bool(universal_types & HARD_UNIVERSAL_TYPES)
    path_id, entry = _registry_target(pack)
    obligation_ids = pack.lineage.get("verification_obligation_ids", []) or []
    has_verification = bool(obligation_ids)
    if has_hard:
        if has_verification and path_id:
            decision = "COMPOSITE"
            rationale = ("rule1: HARD evidence plus verification obligations "
                         "with a registry generation representation")
        else:
            decision = "CONTROL"
            rationale = "rule1: HARD evidence requires generation control"
        authority = "CPCS_HARD_REQUIREMENT"
        target_family = path_id
        forbidden = list(entry["forbidden_coercions"]) if entry else []
        counterpart = entry["verification_counterpart"] if entry else None
    elif has_verification and not path_id:
        decision = "VERIFICATION"
        rationale = ("rule2: verification obligations exist and no registry "
                     "generation representation is available")
        authority = "CPCS_SAFE_INFERENCE"
        target_family = None
        forbidden = []
        counterpart = None
    elif universal_types and universal_types <= NEVER_CONTROL_UNIVERSAL_TYPES:
        affordances = _affordances_for(universal_types)
        if affordances & _PLANNING_ROUTE_AFFORDANCES:
            decision = "PLANNING"
            rationale = ("rule3: non-executable evidence carries reasoning "
                         "affordances usable as planning guidance")
        else:
            decision = "NON_EXECUTABLE"
            rationale = ("rule3: non-executable evidence has no control or "
                         "planning route")
        authority = DECISION_AUTHORITY[decision]
        target_family = None
        forbidden = []
        counterpart = None
    else:
        decision = "CONTROL"
        rationale = "rule4: evidence binds to a registry generation target"
        authority = "CPCS_SAFE_INFERENCE"
        target_family = path_id
        forbidden = list(entry["forbidden_coercions"]) if entry else []
        counterpart = entry["verification_counterpart"] if entry else None
    out = RepresentationDecision(
        knowledge_id=pack.pack_id,
        decision=decision,
        rationale=rationale,
        authority=authority,
        target_family=target_family,
        forbidden_coercions=forbidden,
        verification_counterpart=counterpart,
        decision_hash="",
    )
    out.decision_hash = _sha(out.to_dict())
    return out


# ---------------------------------------------------------------------------
# WP-4 — KnowledgeApplicationSet assembly
# ---------------------------------------------------------------------------
SET_SCHEMA = "cpcs.knowledge_application_set/0.1"

AUTHORITY_RANK = {
    "LEAVE_UNSPECIFIED": 1,
    "EXISTING_BASELINE_DEFAULT": 2,
    "CPCS_GROUNDED_RECOMMENDATION": 3,
    "CPCS_SAFE_INFERENCE": 4,
    "CPCS_HARD_REQUIREMENT": 5,
    "USER_CORRECTION": 6,
    "USER_EXPLICIT": 7,
}


@dataclass
class KnowledgeApplicationSet:
    """Ordered (PrinciplePack + RepresentationDecision) applications."""

    set_id: str
    set_hash: str
    applications: list[dict[str, Any]]
    unknowns: list[dict[str, Any]]
    lineage: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SET_SCHEMA,
            "set_id": self.set_id,
            "set_hash": self.set_hash,
            "applications": self.applications,
            "unknowns": self.unknowns,
            "lineage": self.lineage,
        }


def apply_knowledge(
    treatment_packet: dict[str, Any],
    snapshot: Any,
    activation: dict[str, Any],
) -> KnowledgeApplicationSet:
    """WP-4: packs -> decisions -> ordered, competition-preserving set."""
    packs = build_principle_packs(treatment_packet, snapshot, activation)
    decisions = [decide_representation(p, activation, snapshot) for p in packs]
    applications: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    for pack, decision in zip(packs, decisions):
        if decision.decision == "CONTROL" and decision.target_family is None:
            unknowns.append({
                "pack_id": pack.pack_id,
                "reason": ("no decision rule match: CONTROL without a registry "
                           "generation target (fail closed)"),
                "evidence_ids": pack.evidence_ids,
            })
            continue
        applications.append({"pack": pack, "decision": decision})
    competition_groups: dict[frozenset, str] = {}
    by_requirements: dict[frozenset, list[dict[str, Any]]] = {}
    for entry in applications:
        key = frozenset(entry["pack"].lineage["requirement_ids"])
        by_requirements.setdefault(key, []).append(entry)
    for key, members in by_requirements.items():
        if len(members) < 2:
            continue
        distinct = {(m["decision"].decision, m["pack"].mechanism) for m in members}
        if len(distinct) > 1:
            competition_groups[key] = "comp_" + _sha("|".join(sorted(key)))[:16]
    ordering: list[tuple[int, int, int, str]] = []
    for entry in applications:
        pack: PrinciplePack = entry["pack"]
        decision = entry["decision"]
        has_hard = bool({r["universal_type"] for r in pack.source_records}
                        & HARD_UNIVERSAL_TYPES)
        ordering.append((
            -AUTHORITY_RANK[decision.authority],
            -int(has_hard),
            -len(pack.lineage["requirement_ids"]),
            pack.pack_id,
        ))
    ordered = sorted(zip(applications, ordering), key=lambda pair: pair[1])
    applications = [
        {
            "pack": entry["pack"].to_dict(),
            "decision": entry["decision"].to_dict(),
            "competition_group": competition_groups.get(
                frozenset(entry["pack"].lineage["requirement_ids"])),
        }
        for entry, _ in ordered
    ]
    lineage = {
        "treatment_packet_hash": treatment_packet.get("packet_hash", "unknown"),
        "activation_packet_id": activation.get("packet_id", "unknown"),
        "affordance_ledger_coverage": {
            "non_executable_affordances": len(NON_EXECUTABLE_AFFORDANCES),
            "planning_affordances": len(PLANNING_AFFORDANCES),
        },
    }
    set_id = "kas_" + _sha(
        lineage["treatment_packet_hash"] + lineage["activation_packet_id"])[:16]
    body = {
        "applications": applications,
        "unknowns": unknowns,
        "lineage": lineage,
    }
    set_hash = _sha(body)
    return KnowledgeApplicationSet(
        set_id=set_id,
        set_hash=set_hash,
        applications=applications,
        unknowns=unknowns,
        lineage=lineage,
    )
