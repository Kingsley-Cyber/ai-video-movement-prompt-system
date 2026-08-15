"""DR-1 — CPCS knowledge-grounded deliberation + hypothesis/query-steering layer.

Lives BEFORE execution/control compilation. Consumes the frozen knowledge
and retrieval infrastructure; replaces nothing. Deterministic core; the
optional LLM hypothesis proposer is an ideation source whose output
always enters as source=LLM_PROPOSED / status=PROPOSED and must pass
CPCS grounding before it can affect anything.

D4 remains enforced everywhere: evidence by ID, no flat-text admission.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from lab.compiler.profiles import REPO_ROOT

DELIBERATION_VERSION = "cpcs-deliberation-v1"
_NEGATION_RE = re.compile(r"\b(not|no|without|absent|never|must not|forbidden|avoid)\b")
_TOKEN_RE = re.compile(r"[a-z0-9_]{3,}")


def _sid(*parts: str) -> str:
    return "dr_" + hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]


def _sha(value: Any) -> str:
    if isinstance(value, bytes):
        return hashlib.sha256(value).hexdigest()
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Reasoning affordances for non-executable knowledge (TC-2 dispositions kept;
# this is an ORTHOGONAL second property — DR-1)
# ---------------------------------------------------------------------------
REASONING_AFFORDANCES = [
    "CONCEPT_RECOGNITION", "HYPOTHESIS_GENERATION", "QUERY_STEERING",
    "PREREQUISITE_DISCOVERY", "DISAMBIGUATION", "CAUSAL_REASONING",
    "TEMPORAL_REASONING", "STATE_REASONING", "FAILURE_ANTICIPATION",
    "ANALOGICAL_TRANSFER", "EVIDENCE_INTERPRETATION", "CONTRADICTION_ANALYSIS",
    "VERIFICATION_PLANNING", "RESEARCH_GAP_DISCOVERY",
    "ONTOLOGY_OR_SCHEMA_INTERPRETATION",
]

# universal_type -> reasoning affordances (structured semantics, deterministic)
NON_EXECUTABLE_AFFORDANCES: dict[str, list[str]] = {
    "Concept": ["CONCEPT_RECOGNITION", "HYPOTHESIS_GENERATION", "QUERY_STEERING",
                "DISAMBIGUATION", "STATE_REASONING"],
    "Schema": ["ONTOLOGY_OR_SCHEMA_INTERPRETATION", "CONCEPT_RECOGNITION",
               "QUERY_STEERING", "STATE_REASONING"],
    "Definition": ["CONCEPT_RECOGNITION", "DISAMBIGUATION",
                   "ONTOLOGY_OR_SCHEMA_INTERPRETATION"],
    "Observation": ["EVIDENCE_INTERPRETATION", "CONTRADICTION_ANALYSIS"],
    "Observations": ["EVIDENCE_INTERPRETATION", "CONTRADICTION_ANALYSIS"],
    "EvidenceRecord": ["EVIDENCE_INTERPRETATION", "CONTRADICTION_ANALYSIS",
                       "VERIFICATION_PLANNING"],
    "ResearchGap": ["RESEARCH_GAP_DISCOVERY", "QUERY_STEERING"],
    "OpenQuestion": ["RESEARCH_GAP_DISCOVERY", "QUERY_STEERING"],
    "Measurement": ["VERIFICATION_PLANNING", "EVIDENCE_INTERPRETATION"],
    "Metric": ["VERIFICATION_PLANNING"],
    "ProviderImplication": ["FAILURE_ANTICIPATION"],
    "Table": ["ONTOLOGY_OR_SCHEMA_INTERPRETATION"],
    "JSONSchema": ["ONTOLOGY_OR_SCHEMA_INTERPRETATION"],
    "Ontology": ["ONTOLOGY_OR_SCHEMA_INTERPRETATION", "CONCEPT_RECOGNITION"],
    "Vocabulary": ["CONCEPT_RECOGNITION", "ONTOLOGY_OR_SCHEMA_INTERPRETATION"],
    "Grammar": ["ONTOLOGY_OR_SCHEMA_INTERPRETATION"],
    "Claim": ["EVIDENCE_INTERPRETATION", "CONTRADICTION_ANALYSIS"],
    "Fact": ["EVIDENCE_INTERPRETATION"],
    "Finding": ["EVIDENCE_INTERPRETATION", "HYPOTHESIS_GENERATION"],
    "Experiment": ["RESEARCH_GAP_DISCOVERY", "VERIFICATION_PLANNING"],
    "WorkedExample": ["ANALOGICAL_TRANSFER", "HYPOTHESIS_GENERATION"],
    "Mapping": ["EVIDENCE_INTERPRETATION"],
    "Relationship": ["EVIDENCE_INTERPRETATION", "PREREQUISITE_DISCOVERY"],
    "Mechanism": ["CAUSAL_REASONING", "PREREQUISITE_DISCOVERY"],
    "Process": ["PREREQUISITE_DISCOVERY", "TEMPORAL_REASONING"],
    "ProcessStep": ["PREREQUISITE_DISCOVERY"],
    "SelfCorrection": ["RESEARCH_GAP_DISCOVERY"],
    "Corollary": ["CAUSAL_REASONING", "HYPOTHESIS_GENERATION"],
    "PromptTemplate": ["FAILURE_ANTICIPATION"],
    "Contract": ["PREREQUISITE_DISCOVERY"],
    "ArchitectureRule": ["RESEARCH_GAP_DISCOVERY"],
    "Specification": ["ONTOLOGY_OR_SCHEMA_INTERPRETATION"],
    "OutcomeRequirement": ["VERIFICATION_PLANNING"],
    "TestableRule": ["VERIFICATION_PLANNING"],
    "ValidationRule": ["VERIFICATION_PLANNING"],
    "Checklist": ["VERIFICATION_PLANNING"],
    "Protocol": ["VERIFICATION_PLANNING"],
    "Source": ["EVIDENCE_INTERPRETATION"],
    "SchemaObject": ["ONTOLOGY_OR_SCHEMA_INTERPRETATION"],
    "ControlVariable": ["STATE_REASONING"],
    "Example": ["ANALOGICAL_TRANSFER", "HYPOTHESIS_GENERATION"],
}

# planning affordances for PLANNING_ONLY objects
PLANNING_AFFORDANCES: dict[str, list[str]] = {
    "Recommendation": ["QUERY_DECOMPOSITION", "EVIDENCE_ACQUISITION_STRATEGY",
                       "STOPPING_HEURISTIC"],
    "Technique": ["QUERY_DECOMPOSITION", "EVIDENCE_ACQUISITION_STRATEGY"],
    "Heuristic": ["STOPPING_HEURISTIC", "QUERY_DECOMPOSITION"],
    "Procedure": ["REASONING_ORDER", "PREREQUISITE_ORDERING"],
    "Workflow": ["REASONING_ORDER", "PHASE_DECOMPOSITION"],
    "DecisionRule": ["CONFLICT_RESOLUTION_STRATEGY", "REASONING_ORDER"],
    "ConditionalRule": ["CONFLICT_RESOLUTION_STRATEGY"],
    "Default": ["EVIDENCE_ACQUISITION_STRATEGY"],
    "DesignDecision": ["REASONING_ORDER"],
    "Policy": ["REASONING_ORDER", "CONFLICT_RESOLUTION_STRATEGY"],
    "Doctrine": ["REASONING_ORDER"],
}

HYPOTHESIS_TYPES = [
    "REQUIREMENT_HYPOTHESIS", "FAILURE_HYPOTHESIS", "CAUSAL_HYPOTHESIS",
    "STATE_HYPOTHESIS", "CONTINUITY_HYPOTHESIS", "TEMPORAL_HYPOTHESIS",
    "INTERACTION_HYPOTHESIS", "VISIBILITY_HYPOTHESIS",
    "OWNERSHIP_POSSESSION_HYPOTHESIS", "SUPPORT_BALANCE_HYPOTHESIS",
    "CAMERA_RELATION_HYPOTHESIS", "PERFORMANCE_HYPOTHESIS",
    "STYLE_HYPOTHESIS", "VERIFICATION_HYPOTHESIS",
    "CREATIVE_INTERPRETATION_HYPOTHESIS", "KNOWLEDGE_GAP_HYPOTHESIS",
]
HYPOTHESIS_STATUSES = [
    "PROPOSED", "SUPPORTED", "WEAKLY_SUPPORTED", "CONTRADICTED", "REJECTED",
    "RESOLVED_AS_REQUIREMENT", "RESOLVED_AS_SAFE_INFERENCE",
    "RESOLVED_AS_CREATIVE_CHOICE", "UNRESOLVED",
]
QUERY_INTENTS = [
    "CONCEPT", "RULE", "CONSTRAINT", "FAILURE", "PROCEDURE", "CONTROL",
    "EVIDENCE", "VERIFICATION", "PROVIDER", "EXAMPLE", "EXPERIMENT",
]
OBSERVATION_SOURCES = ["USER_EXPLICIT", "STRUCTURAL_ENTAILMENT"]


@dataclass
class DeliberationBudget:
    max_hypotheses: int = 60
    max_active_hypotheses: int = 60
    max_query_rounds: int = 3
    max_queries_per_hypothesis: int = 4
    max_cascade_depth: int = 5
    max_retrieved_evidence_items: int = 100
    max_contradiction_branches: int = 6
    max_unresolved_creative_choices: int = 5


@dataclass
class KnowledgeSnapshot:
    triggers: dict[str, dict[str, Any]] = field(default_factory=dict)
    requirements: dict[str, dict[str, Any]] = field(default_factory=dict)
    failure_families: dict[str, dict[str, Any]] = field(default_factory=dict)
    objectives: dict[str, dict[str, Any]] = field(default_factory=dict)
    bridges: list[dict[str, str]] = field(default_factory=list)
    cascade_edges: list[tuple[str, str]] = field(default_factory=list)
    architecture_identity: str = "unknown"
    retrieval_identity: str = "unknown"


class Backend(Protocol):
    """Treatment backend used by the deliberation engine (frozen or fake)."""

    def plan(self, intent_text: str, normalized_intent: dict[str, Any], *,
             query_mode: str = "INITIAL_GENERATION",
             discrepancy: dict[str, Any] | None = None) -> dict[str, Any]: ...


# ---------------------------------------------------------------------------
# Observation extraction (deterministic; USER_EXPLICIT vs STRUCTURAL)
# ---------------------------------------------------------------------------
def extract_observations(request: str, snapshot: KnowledgeSnapshot) -> list[dict[str, Any]]:
    observations = []
    low = " " + request.lower() + " "
    # USER_EXPLICIT: entities/actions the user stated (deterministic patterns)
    for ent in ("fighter", "actor", "she", "he", "hand", "glass", "wrist",
                "camera", "table", "box", "pillar", "hero"):
        if re.search(rf"\b{ent}\b", low):
            observations.append({
                "observation_id": _sid("obs", ent),
                "text": f"entity mentioned: {ent}",
                "kind": "entity_mention",
                "source": "USER_EXPLICIT",
                "structured": {"entity_token": ent},
            })
    # STRUCTURAL_ENTAILMENT: activated triggers are structurally entailed
    for trig, tdef in sorted(snapshot.triggers.items()):
        obs = {
            "observation_id": _sid("obs", trig),
            "text": tdef.get("definition", trig),
            "kind": "trigger_entailment",
            "source": "STRUCTURAL_ENTAILMENT",
            "structured": {"trigger_id": trig},
        }
        observations.append(obs)
    return observations[:60]


class DeliberationEngine:
    def __init__(self, snapshot: KnowledgeSnapshot, backend: Backend,
                 budget: DeliberationBudget | None = None,
                 proposal_set_identity: str = "deterministic-v1"):
        self.snapshot = snapshot
        self.backend = backend
        self.budget = budget or DeliberationBudget()
        self.proposal_set_identity = proposal_set_identity

    # ------------------------------------------------------------ activation
    def activate(self, request: str, normalized_intent: dict[str, Any],
                 observations: list[dict[str, Any]]) -> dict[str, Any]:
        packet = self.backend.plan(request, normalized_intent)
        domains = sorted({d.split("-")[1] if d.startswith("DIM-") else d
                          for d in {r for r in packet["required_pathways"]}})
        affordances = set()
        planning = set()
        for e in packet["retrieved_evidence"]:
            ut = (e.get("universal_type") or "").title()
            affordances |= set(NON_EXECUTABLE_AFFORDANCES.get(ut, []))
            planning |= set(PLANNING_AFFORDANCES.get(ut, []))
        activation = {
            "packet_id": "kap_" + _sid(request)[:16],
            "normalized_intent_id": "intent_" + packet["source_intent_hash"][:16],
            "normalized_intent_hash": packet["source_intent_hash"],
            "explicit_observations": [o["observation_id"] for o in observations
                                      if o["source"] == "USER_EXPLICIT"],
            "activated_domains": domains,
            "activated_reasoning_dimensions": sorted({
                r.get("reasoning_dimension")
                for r in self.snapshot.requirements.values()
                if r["requirement_id"] in set(packet["mandatory_requirements"])}),
            "activated_concepts": sorted({c for e in packet["retrieved_evidence"]
                                          for c in e.get("trigger_ids", [])}),
            "activated_reasoning_affordances": sorted(affordances),
            "activated_planning_affordances": sorted(planning),
            "activated_triggers": sorted({r["trigger_source"]
                                          for r in self.snapshot.requirements.values()
                                          if r["requirement_id"] in
                                          set(packet["mandatory_requirements"]
                                              + packet["conditional_requirements"])}),
            "candidate_objectives": sorted(packet.get("objectives_at_risk", [])),
            "candidate_failure_families": sorted(packet.get("predicted_failure_families", [])),
            "candidate_requirements": packet["mandatory_requirements"],
            "initial_unknowns": packet.get("unknowns", []),
            "potential_cross_domain_bridges": self.snapshot.bridges,
            "activation_lineage": {
                "treatment_packet_id": packet["treatment_id"],
                "treatment_packet_hash": packet["packet_hash"],
            },
            "frozen_architecture_identity": packet["architecture_freeze_identity"],
        }
        activation["packet_hash"] = _sha(
            {k: v for k, v in activation.items() if k != "packet_hash"})
        return activation, packet

    # ------------------------------------------------------------ hypotheses
    def hypothesize(self, request: str, packet: dict[str, Any]) -> list[dict[str, Any]]:
        H = []
        budget = self.budget.max_hypotheses
        req_ids = set(packet["mandatory_requirements"])
        cond_ids = set(packet["conditional_requirements"])
        h_requirement, h_failure, h_competition, h_causal, h_visibility, h_gaps = (
            [], [], [], [], [], [])
        # REQUIREMENT_HYPOTHESIS per mandatory requirement
        for rid in sorted(req_ids | cond_ids):
            req = self.snapshot.requirements.get(rid)
            if req is None:
                continue
            h_requirement.append(self._hyp(
                "REQUIREMENT_HYPOTHESIS", rid,
                f"requirement {rid} ({req.get('reasoning_dimension')}) must be satisfied",
                source="KNOWLEDGE_DERIVED",
                requirement_ids=[rid],
                objective_ids=req.get("objectives_protected", []),
                failure_ids=req.get("failures_prevented", []),
                dimensions=[req.get("reasoning_dimension")],
                verification_need=True, query_need=True))
        # FAILURE_HYPOTHESIS per predicted failure family (failure-first)
        for ff in sorted(set(packet.get("predicted_failure_families", []))):
            fam = self.snapshot.failure_families.get(ff, {})
            h_failure.append(self._hyp(
                "FAILURE_HYPOTHESIS", f"fail:{ff}",
                f"{ff} may occur if its requirement is not maintained",
                source="KNOWLEDGE_DERIVED",
                requirement_ids=[r["requirement_id"] for r in
                                 self.snapshot.requirements.values()
                                 if ff in r.get("failures_prevented", [])][:8],
                failure_ids=[ff],
                objective_ids=fam.get("canonical_objectives", []),
                verification_need=True, query_need=True))
        # competition: contact persistence vs contact transfer
        if "FF-CONTACT" in packet.get("predicted_failure_families", []):
            h_competition.append(self._hyp("INTERACTION_HYPOTHESIS", "contact_persist",
                               "contact persists through the interaction",
                               source="KNOWLEDGE_DERIVED",
                               requirement_ids=sorted(req_ids)[:8],
                               failure_ids=["FF-CONTACT"],
                               competition_group="contact_mode",
                               query_need=True))
            h_competition.append(self._hyp("INTERACTION_HYPOTHESIS", "contact_transfer",
                               "contact transfers midway through the interaction",
                               source="KNOWLEDGE_DERIVED",
                               requirement_ids=sorted(req_ids)[:8],
                               failure_ids=["FF-CONTACT"],
                               competition_group="contact_mode",
                               query_need=True))
        # causal hypothesis from requirement depends_on (structured)
        seen = set()
        for rid in sorted(req_ids | cond_ids):
            req = self.snapshot.requirements.get(rid, {})
            for dep in req.get("depends_on", []) or []:
                key = (dep, rid)
                if key in seen:
                    continue
                seen.add(key)
                h_causal.append(self._hyp(
                    "CAUSAL_HYPOTHESIS", f"causal:{dep}->{rid}",
                    f"{rid} depends causally on {dep}",
                    source="CASCADE_DERIVED",
                    requirement_ids=[rid, dep],
                    prerequisite_hypothesis_ids=[_sid("hyp", dep)],
                    query_need=True))
        # cascade-derived prerequisite hypotheses (frozen activation rules)
        activated_triggers = {r.get("trigger_source") for r in
                               self.snapshot.requirements.values()
                               if r["requirement_id"] in (req_ids | cond_ids)}
        for src_t, tgt_t in self.snapshot.cascade_edges:
            if src_t in activated_triggers and tgt_t in activated_triggers:
                key = ("cascade", src_t, tgt_t)
                if key in seen:
                    continue
                seen.add(key)
                h_causal.append(self._hyp(
                    "CAUSAL_HYPOTHESIS", f"cascade:{src_t}->{tgt_t}",
                    f"reasoning for {tgt_t} follows {src_t} activation",
                    source="CASCADE_DERIVED",
                    requirement_ids=[r["requirement_id"] for r in
                                     self.snapshot.requirements.values()
                                     if r.get("trigger_source") == tgt_t][:6],
                    prerequisite_hypothesis_ids=[_sid("hyp", src_t)],
                    query_need=True))
        # visibility hypothesis when a visibility-dimension requirement is active
        if any(self.snapshot.requirements.get(r, {}).get("reasoning_dimension")
               in ("DIM-VISIBILITY", "DIM-CAMERA") for r in req_ids):
            h_visibility.append(self._hyp(
                "VISIBILITY_HYPOTHESIS", "visibility",
                "subject/interaction visibility may be critical",
                source="KNOWLEDGE_DERIVED",
                requirement_ids=[r for r in sorted(req_ids)
                                 if self.snapshot.requirements.get(r, {}).get(
                                     "reasoning_dimension") in
                                 ("DIM-VISIBILITY", "DIM-CAMERA")][:8],
                query_need=True))
        # knowledge-gap hypotheses from requirement missing_information
        for rid in sorted(req_ids):
            req = self.snapshot.requirements.get(rid, {})
            for item in req.get("missing_information", []) or []:
                h_gaps.append(self._hyp(
                    "KNOWLEDGE_GAP_HYPOTHESIS", f"gap:{rid}:{_sha(str(item))[:8]}",
                    f"requirement {rid} has missing information: {item}",
                    source="KNOWLEDGE_DERIVED",
                    requirement_ids=[rid],
                    unknown_ids=[_sid("unk", rid + str(item))],
                    query_need=True, blocking=True))
        # budget-bound merge with priority. Requirement hypotheses are capped at
        # half the budget so failure/competition/causal/visibility reasoning is
        # never starved (deterministic policy, frozen here).
        req_cap = max(1, budget // 2)
        H = h_requirement[:req_cap]
        for category in (h_gaps, h_failure, h_competition, h_causal, h_visibility):
            for h in category:
                if len(H) >= budget:
                    break
                H.append(h)
            if len(H) >= budget:
                break
        # LLM-proposed hypotheses may be injected via admit_llm_proposals()
        return H

    def _hyp(self, htype: str, key: str, claim: str, *, source: str,
             requirement_ids=None, objective_ids=None, failure_ids=None,
             dimensions=None, competition_group=None, verification_need=False,
             query_need=False, prerequisite_hypothesis_ids=None, unknown_ids=None,
             blocking=False) -> dict[str, Any]:
        h = {
            "hypothesis_id": _sid("hyp", htype, key),
            "hypothesis_type": htype,
            "claim": claim,
            "structured_semantics": {
                "type": htype, "key": key,
                "requirement_ids": sorted(set(requirement_ids or [])),
                "objective_ids": sorted(set(objective_ids or [])),
                "failure_family_ids": sorted(set(failure_ids or [])),
                "dimensions": sorted(set(dimensions or [])),
                "competition_group": competition_group,
            },
            "source": source,
            "affected_domains": [],
            "affected_dimensions": sorted(set(dimensions or [])),
            "candidate_requirement_ids": sorted(set(requirement_ids or [])),
            "candidate_objective_ids": sorted(set(objective_ids or [])),
            "candidate_failure_family_ids": sorted(set(failure_ids or [])),
            "supporting_knowledge_ids": [],
            "supporting_evidence_ids": [],
            "contradicting_evidence_ids": [],
            "prerequisite_hypothesis_ids": prerequisite_hypothesis_ids or [],
            "depends_on_unknown_ids": unknown_ids or [],
            "confidence": 0.0,
            "status": "PROPOSED",
            "verification_need": verification_need,
            "query_need": query_need,
            "blocking": blocking,
        }
        h["hash"] = _sha({k: v for k, v in h.items() if k != "hash"})
        return h

    def admit_llm_proposals(self, hypotheses, proposals):
        """LLM proposals enter as PROPOSED; never authoritative."""
        for p in proposals:
            h = self._hyp(p["hypothesis_type"], "llm:" + _sha(p["claim"])[:12],
                          p["claim"], source="LLM_PROPOSED",
                          requirement_ids=p.get("candidate_requirement_ids"),
                          failure_ids=p.get("candidate_failure_family_ids"),
                          verification_need=p.get("verification_need", False),
                          query_need=True)
            h["proposal_set_identity"] = self.proposal_set_identity
            hypotheses.append(h)
        return hypotheses[:self.budget.max_hypotheses]

    # ------------------------------------------------------------ query steering
    def steer(self, hypotheses: list[dict[str, Any]],
              unknowns: list[dict[str, Any]]) -> dict[str, Any]:
        queries = []
        seen = set()
        rounds = 1
        for h in hypotheses:
            if not h["query_need"]:
                continue
            dims = h["affected_dimensions"] or ["DIM-STATE"]
            fams = sorted({d.replace("DIM-", "").lower() for d in dims})
            per_h = 0
            for fam in fams:
                if per_h >= self.budget.max_queries_per_hypothesis:
                    break
                key = (h["hypothesis_id"], fam)
                if key in seen:
                    continue
                seen.add(key)
                queries.append({
                    "query_id": _sid("q", h["hypothesis_id"], fam),
                    "query_mode": "INITIAL_GENERATION",
                    "reason": (f"resolve {h['hypothesis_type']} "
                               f"{h['hypothesis_id']} on dimension {fam}"),
                    "target_hypothesis_ids": [h["hypothesis_id"]],
                    "target_unknown_ids": h.get("depends_on_unknown_ids", []),
                    "target_requirement_ids": h["candidate_requirement_ids"],
                    "target_dimensions": dims,
                    "target_domains": fams,
                    "retrieval_intents": ["CONCEPT", "RULE", "CONSTRAINT",
                                          "FAILURE", "EVIDENCE"],
                    "query_representations": {
                        "semantic_family": fam,
                        "dimension_ids": dims,
                    },
                    "expected_evidence_class": "typed evidence for "
                                               + "/".join(fams),
                    "success_condition": (f"evidence supporting or contradicting "
                                          f"{h['hypothesis_id']}"),
                    "stop_if_satisfied": True,
                    "priority": self._query_priority(h),
                    "parent_query_id": None,
                    "lineage": {"hypothesis_id": h["hypothesis_id"]},
                })
                per_h += 1
        # budget + dedupe
        queries = sorted(queries, key=lambda q: q["priority"])
        plan = {
            "query_steering_plan_id": "qsp_" + _sid(*(q["query_id"] for q in queries))[:16],
            "query_rounds_planned": rounds,
            "queries": queries[: self.budget.max_hypotheses * 4],
            "budget": self.budget.__dict__,
            "steering_rule": ("hypothesis-driven only; every query answers a "
                              "structured reasoning need; no keyword expansion"),
        }
        return plan

    def _query_priority(self, h: dict[str, Any]) -> int:
        if h.get("blocking"):
            return 1
        if h["hypothesis_type"] == "REQUIREMENT_HYPOTHESIS":
            return 2
        if h["hypothesis_type"] == "FAILURE_HYPOTHESIS":
            return 3
        if h.get("competition_group") or h["hypothesis_type"] == "CAUSAL_HYPOTHESIS":
            return 4
        if h["hypothesis_type"] == "KNOWLEDGE_GAP_HYPOTHESIS":
            return 5
        return 9

    # ------------------------------------------------------------ updates
    def update(self, hypotheses: list[dict[str, Any]],
               packet: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        evidence = packet.get("retrieved_evidence", [])
        updates = []
        for h in hypotheses:
            reqs = set(h["candidate_requirement_ids"])
            fails = set(h["candidate_failure_family_ids"])
            supporting = []
            contradicting = []
            for e in evidence:
                hits = set(e.get("supported_requirement_ids", [])) & reqs
                ffhits = set(e.get("failure_family_ids", [])) & fails
                if hits or ffhits:
                    label = str(e.get("provenance", {}).get("heading", "") or "")
                    if _NEGATION_RE.search(label):
                        contradicting.append(e["atomic_record_id"])
                    else:
                        supporting.append(e["atomic_record_id"])
            prior = h["status"]
            h["supporting_evidence_ids"] = sorted(set(supporting))
            h["contradicting_evidence_ids"] = sorted(set(contradicting))
            total = len(h["supporting_evidence_ids"]) + len(h["contradicting_evidence_ids"])
            h["confidence"] = round(len(h["supporting_evidence_ids"]) / total, 3) if total else 0.0
            if h["supporting_evidence_ids"] and not h["contradicting_evidence_ids"]:
                new_status = "SUPPORTED"
            elif h["contradicting_evidence_ids"] and not h["supporting_evidence_ids"]:
                new_status = "CONTRADICTED"
            elif h["supporting_evidence_ids"]:
                new_status = "WEAKLY_SUPPORTED"
            else:
                new_status = "PROPOSED"
            h["status"] = new_status
            updates.append({
                "update_id": _sid("upd", h["hypothesis_id"]),
                "hypothesis_id": h["hypothesis_id"],
                "prior_status": prior,
                "new_evidence_ids": sorted(set(supporting + contradicting)),
                "supporting_evidence_ids": h["supporting_evidence_ids"],
                "contradicting_evidence_ids": h["contradicting_evidence_ids"],
                "evidence_conflicts": bool(contradicting and supporting),
                "updated_confidence": h["confidence"],
                "updated_status": new_status,
                "new_unknowns": [],
                "new_prerequisites": [],
                "new_candidate_hypotheses": [],
                "resolution": None,
                "lineage": {"hypothesis_id": h["hypothesis_id"]},
            })
        return hypotheses, updates

    # ------------------------------------------------------------ closure
    def close(self, request: str, hypotheses: list[dict[str, Any]],
              observations: list[dict[str, Any]], packet: dict[str, Any],
              activation: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
        accepted = [h for h in hypotheses if h["status"] in ("SUPPORTED",)]
        safe_inferences = []
        creative_choices = []
        remaining_unknowns = []
        for h in accepted:
            group = h["structured_semantics"].get("competition_group")
            if h["hypothesis_type"] in ("REQUIREMENT_HYPOTHESIS", "FAILURE_HYPOTHESIS",
                                        "CAUSAL_HYPOTHESIS", "INTERACTION_HYPOTHESIS",
                                        "VISIBILITY_HYPOTHESIS"):
                if group:
                    creative_choices.append(h)
                else:
                    safe_inferences.append(h)
            elif h["hypothesis_type"] == "KNOWLEDGE_GAP_HYPOTHESIS":
                remaining_unknowns.append(h)
        # competition resolution: keep both, never average (surface as creative)
        groups: dict[str, list[dict[str, Any]]] = {}
        for h in hypotheses:
            g = h["structured_semantics"].get("competition_group")
            if g:
                groups.setdefault(g, []).append(h)
        contradicted = [h for h in hypotheses if h["status"] == "CONTRADICTED"]
        rejected = [h for h in hypotheses if h["status"] == "REJECTED"]
        unresolved = [h for h in hypotheses if h["status"] in ("PROPOSED", "WEAKLY_SUPPORTED")]
        blocking = [h for h in unresolved if h.get("blocking")]
        completeness = ("COMPLETE" if not blocking and not remaining_unknowns
                        else "COMPLETE_WITH_UNKNOWNS" if not blocking
                        else "INCOMPLETE")
        stopping = ("all critical hypotheses resolved" if completeness == "COMPLETE"
                    else "blocking knowledge gaps remain" if blocking
                    else "non-blocking unknowns surfaced; budget bounded")
        closure = {
            "closure_id": "closure_" + _sid(request)[:16],
            "normalized_intent_id": activation["normalized_intent_id"],
            "explicit_observations": [o["observation_id"] for o in observations],
            "accepted_hypotheses": [h["hypothesis_id"] for h in accepted],
            "rejected_hypotheses": [h["hypothesis_id"] for h in rejected],
            "contradicted_hypotheses": [h["hypothesis_id"] for h in contradicted],
            "safe_inferences": [h["hypothesis_id"] for h in safe_inferences],
            "creative_choices": [h["hypothesis_id"] for h in creative_choices],
            "remaining_unknowns": [h["depends_on_unknown_ids"] for h in remaining_unknowns],
            "resolved_requirements": activation["candidate_requirements"],
            "predicted_failures": activation["candidate_failure_families"],
            "objectives_at_risk": activation["candidate_objectives"],
            "canonical_states": [],
            "canonical_relations": [],
            "canonical_events": [],
            "canonical_temporal_relations": [],
            "canonical_causal_relations": [],
            "canonical_invariants": [],
            "canonical_constraints": [],
            "verification_requirements": [h["hypothesis_id"] for h in accepted
                                          if h.get("verification_need")],
            "planning_guidance": [],
            "non_executable_knowledge_used": sorted({
                ut for e in packet.get("retrieved_evidence", [])
                for ut in [e.get("universal_type") or ""] if ut.title() in
                NON_EXECUTABLE_AFFORDANCES}),
            "queries_executed": [q["query_id"] for q in plan["queries"]],
            "evidence_used": [e["atomic_record_id"] for e in
                              packet.get("retrieved_evidence", [])],
            "contradictions_preserved": [h["hypothesis_id"] for h in
                                         hypotheses if h["contradicting_evidence_ids"]],
            "reasoning_completeness": completeness,
            "closure_reason": stopping,
            "lineage": {
                "activation_packet_id": activation["packet_id"],
                "treatment_packet_hash": packet["packet_hash"],
                "proposal_set_identity": self.proposal_set_identity,
                "budget": self.budget.__dict__,
            },
        }
        closure["packet_hash"] = _sha({k: v for k, v in closure.items()
                                       if k != "packet_hash"})
        return closure, hypotheses

    # ------------------------------------------------------------ ideation
    IDEATION_TEMPLATES = {
        "fight": [
            ("attritional", "attritional struggle where the hero barely survives"),
            ("reversal", "late reversal after being dominated"),
            ("environment", "environment-assisted win using the surroundings"),
            ("counter", "technical counter sequence"),
            ("defense", "defensive survival into a single opportunity"),
        ],
        "generic": [
            ("faithful", "faithful minimal interpretation of the request"),
            ("expressive", "performance-emphasized interpretation"),
            ("stylized", "stylized exaggeration interpretation"),
        ],
    }

    def ideate(self, request: str, normalized_intent: dict[str, Any]) -> dict[str, Any]:
        packet = self.backend.plan(request, normalized_intent)
        low = request.lower()
        fight_terms = ("fight", "clash", "combat", "strike", "throw")
        template_key = "fight" if any(t in low for t in fight_terms) else "generic"
        candidates = []
        for key, claim in self.IDEATION_TEMPLATES[template_key]:
            h = self._hyp("CREATIVE_INTERPRETATION_HYPOTHESIS", f"ideate:{key}",
                          claim, source="LLM_PROPOSED", query_need=True)
            h["proposal_set_identity"] = self.proposal_set_identity
            fails = set(packet.get("predicted_failure_families", []))
            evidence_overlap = min(20, len(packet["retrieved_evidence"]))
            candidates.append({
                "candidate_id": _sid("cand", key),
                "creative_hypothesis": h["hypothesis_id"],
                "intent_alignment": "candidate" if key != "faithful" else "direct",
                "required_reasoning_dimensions": h["affected_dimensions"],
                "required_domains": [],
                "likely_execution_requirements": [],
                "likely_failure_families": sorted(fails)[:5],
                "knowledge_support": sorted({ut.title() for e in
                                             packet["retrieved_evidence"][:20]
                                             for ut in [e.get("universal_type") or ""]}),
                "evidence_support": evidence_overlap,
                "unknowns": [],
                "tradeoffs": [],
                "control_complexity_estimate": "medium",
                "verification_complexity_estimate": "medium",
                "creative_assumptions": [claim],
                "status": "PROPOSED",
            })
        return {
            "ideation_mode": "IDEATION",
            "request": request,
            "candidates": candidates,
            "rule": ("ideation hypotheses are creative proposals, NOT mandatory "
                     "requirements; CPCS never silently selects the user's story"),
        }

    # ------------------------------------------------------------ full run
    def deliberate(self, request: str, normalized_intent: dict[str, Any],
                   llm_proposals: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        observations = extract_observations(request, self.snapshot)
        activation, packet = self.activate(request, normalized_intent, observations)
        hypotheses = self.hypothesize(request, packet)
        if llm_proposals:
            hypotheses = self.admit_llm_proposals(hypotheses, llm_proposals)
        hypotheses = hypotheses[:self.budget.max_active_hypotheses]
        plan = self.steer(hypotheses, [])
        hypotheses, updates = self.update(hypotheses, packet)
        closure, hypotheses = self.close(request, hypotheses, observations,
                                         packet, activation, plan)
        return {
            "schema": "cpcs.deliberation/1.0",
            "deliberation_id": "deliberation_" + _sid(request)[:16],
            "request": request,
            "observations": observations,
            "knowledge_activation_packet": activation,
            "hypothesis_set": {
                "hypotheses": hypotheses,
                "count": len(hypotheses),
            },
            "query_steering_plan": plan,
            "hypothesis_updates": updates,
            "reasoning_closure_packet": closure,
            "deliberation_version": DELIBERATION_VERSION,
            "proposal_set_identity": self.proposal_set_identity,
            "packet_hash": _sha({"closure": closure["packet_hash"],
                                 "plan": plan["query_steering_plan_id"],
                                 "activation": activation["packet_hash"]}),
        }


# ---------------------------------------------------------------------------
# Knowledge snapshot loaders
# ---------------------------------------------------------------------------
def frozen_knowledge_snapshot() -> KnowledgeSnapshot:
    import os
    import sys

    from .bootstrap import resolved_runtime_path

    runtime = resolved_runtime_path()
    if not runtime:
        raise RuntimeError("CPCS_FROZEN_RUNTIME_PATH is not configured "
                           "(or run bin/cpcs bootstrap)")
    sys.path.insert(0, runtime)
    from cpcs_loader import CPCSLoader

    loader = CPCSLoader(version="v0.2")
    loader.validate()
    return KnowledgeSnapshot(
        triggers={t: loader.trigger_vocab[t] for t in loader.trigger_vocab},
        requirements={r["requirement_id"]: r for r in loader.requirements},
        failure_families=dict(loader.failure_families),
        objectives=dict(loader.objective_vocab),
        cascade_edges=[tuple(e[:2]) for e in loader.cascade_edges],
        bridges=[{"source": "persistent state under occlusion",
                  "target": "contact/possession/identity continuity",
                  "bridge": "OcclusionInterval persistence semantics",
                  "transfer_limitation": "candidate only; needs validation"}],
        architecture_identity="frozen-arch-v2",
        retrieval_identity="frozen-runtime-v1",
    )


def _fake_req(rid, dim, obj, fail, deps=(), missing=()):
    return {"requirement_id": rid, "trigger_source": "TRIG-" + dim.split("-")[-1],
            "reasoning_dimension": dim, "objectives_protected": [obj],
            "failures_prevented": [fail], "depends_on": list(deps),
            "missing_information": list(missing)}


FAKE_SNAPSHOT = KnowledgeSnapshot(
    triggers={
        "TRIG-CONTACT": {"definition": "contact occurs", "activated_dimensions": ["DIM-CONTACT"]},
        "TRIG-MOTION": {"definition": "motion occurs", "activated_dimensions": ["DIM-TRAJECTORY"]},
    },
    requirements={
        "REQ-CONTACT-1": _fake_req("REQ-CONTACT-1", "DIM-CONTACT", "OBJ-CONTACT", "FF-CONTACT"),
        "REQ-CAUSAL-1": _fake_req("REQ-CAUSAL-1", "DIM-CAUSALITY", "OBJ-CAUSALITY",
                                  "FF-CAUSALITY", deps=("REQ-CONTACT-1",)),
        "REQ-VIS-1": _fake_req("REQ-VIS-1", "DIM-VISIBILITY", "OBJ-CONTINUITY",
                               "FF-CONTINUITY", missing=("occlusion persistence",)),
        "REQ-CAM-1": _fake_req("REQ-CAM-1", "DIM-CAMERA", "OBJ-READABILITY",
                               "FF-CAMERA"),
        "REQ-OWN-1": _fake_req("REQ-OWN-1", "DIM-OWNERSHIP", "OBJ-IDENTITY",
                               "FF-IDENTITY"),
        "REQ-SUP-1": _fake_req("REQ-SUP-1", "DIM-SUPPORT", "OBJ-PHYSICAL-PLAUSIBILITY",
                               "FF-PHYSICS"),
    },
    failure_families={
        "FF-CONTACT": {"name": "ContactFailure", "canonical_objectives": ["OBJ-CONTACT"],
                       "activating_conditions": ["contact present"]},
        "FF-CAUSALITY": {"name": "CausalityFailure", "canonical_objectives": ["OBJ-CAUSALITY"]},
        "FF-CONTINUITY": {"name": "ContinuityFailure", "canonical_objectives": ["OBJ-CONTINUITY"]},
        "FF-CAMERA": {"name": "CameraFailure", "canonical_objectives": ["OBJ-READABILITY"]},
        "FF-IDENTITY": {"name": "IdentityFailure", "canonical_objectives": ["OBJ-IDENTITY"]},
        "FF-PHYSICS": {"name": "PhysicsFailure",
                       "canonical_objectives": ["OBJ-PHYSICAL-PLAUSIBILITY"]},
    },
    objectives={"OBJ-CONTACT": {"name": "ContactObjective"},
                "OBJ-CAUSALITY": {"name": "CausalityObjective"},
                "OBJ-CONTINUITY": {"name": "ContinuityObjective"},
                "OBJ-READABILITY": {"name": "ReadabilityObjective"},
                "OBJ-IDENTITY": {"name": "IdentityObjective"},
                "OBJ-PHYSICAL-PLAUSIBILITY": {"name": "PhysicalPlausibilityObjective"}},
    bridges=[],
    architecture_identity="fake-arch-v2",
    retrieval_identity="fake-runtime-v1",
)


# ---------------------------------------------------------------------------
# Application operation handlers (registered additively in service.py)
# ---------------------------------------------------------------------------
def _engine(root):
    from lab.application.reasoning_treatment import FrozenRuntimeBackend
    from lab.second_brain.src.intent import build_intent_context

    snapshot = frozen_knowledge_snapshot()
    backend = FrozenRuntimeBackend()
    return snapshot, backend, build_intent_context


def _run(arguments, root, parts):
    snapshot, backend, build_intent_context = _engine(root)
    ic = build_intent_context(arguments["intent_text"], root=root)
    engine = DeliberationEngine(snapshot, backend)
    out = engine.deliberate(arguments["intent_text"], ic["normalized_intent"],
                            llm_proposals=arguments.get("llm_proposals"))
    return out, parts


def handler_deliberate_plan(arguments, root):
    out, _ = _run(arguments, root, ())
    return {
        "deliberation_id": out["deliberation_id"],
        "knowledge_activation_packet": out["knowledge_activation_packet"],
        "hypothesis_set": out["hypothesis_set"],
        "query_steering_plan": out["query_steering_plan"],
        "hypothesis_updates": out["hypothesis_updates"],
        "reasoning_closure_packet": out["reasoning_closure_packet"],
        "packet_hash": out["packet_hash"],
    }


def handler_deliberate_inspect(arguments, root):
    result = handler_deliberate_plan(arguments, root)
    result.pop("knowledge_activation_packet", None)
    result.pop("hypothesis_updates", None)
    return result


def handler_ideate(arguments, root):
    snapshot, backend, build_intent_context = _engine(root)
    ic = build_intent_context(arguments["intent_text"], root=root)
    engine = DeliberationEngine(snapshot, backend)
    return engine.ideate(arguments["intent_text"], ic["normalized_intent"])


def handler_hypotheses_inspect(arguments, root):
    result = handler_deliberate_plan(arguments, root)
    return {"deliberation_id": result["deliberation_id"],
            "hypothesis_set": result["hypothesis_set"],
            "packet_hash": result["packet_hash"]}


def handler_query_plan_inspect(arguments, root):
    result = handler_deliberate_plan(arguments, root)
    return {"deliberation_id": result["deliberation_id"],
            "query_steering_plan": result["query_steering_plan"],
            "packet_hash": result["packet_hash"]}


def handler_reasoning_closure_inspect(arguments, root):
    result = handler_deliberate_plan(arguments, root)
    return {"deliberation_id": result["deliberation_id"],
            "reasoning_closure_packet": result["reasoning_closure_packet"],
            "packet_hash": result["packet_hash"]}
