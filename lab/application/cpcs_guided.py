"""PC-1 — GP-2 guided projection + session/revision + FAST/AUTO completion.

Stacks on DR-1 deliberation. Presentation compression never collapses
canonical semantics. Authority order:
USER_EXPLICIT > USER_CORRECTION > CPCS_HARD_REQUIREMENT >
CPCS_SAFE_INFERENCE > CPCS_GROUNDED_RECOMMENDATION >
EXISTING_BASELINE_DEFAULT > LEAVE_UNSPECIFIED
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lab.compiler.profiles import REPO_ROOT

GUIDED_VERSION = "cpcs-guided-v1"

FAST_TRIGGERS = [
    "just give me the prompt", "just make me the prompt", "just make it", "skip the questions",
    "use your best judgment", "you decide", "finish it",
    "don't ask me anything", "just finish", "that's enough",
    "whatever", "pick the best one", "use the strongest version",
]

AUTHORITY_ORDER = [
    "USER_EXPLICIT", "USER_CORRECTION", "CPCS_HARD_REQUIREMENT",
    "CPCS_SAFE_INFERENCE", "CPCS_GROUNDED_RECOMMENDATION",
    "EXISTING_BASELINE_DEFAULT", "LEAVE_UNSPECIFIED",
]

# deterministic compression groups: internal semantic ids -> user phrase
COMPRESSION_GROUPS = [
    {
        "id": "grip_relationship_coherence",
        "phrase": "Keep the grip and actor relationship coherent throughout the rotation.",
        "members": ["contact persistence", "contact identity", "interaction coupling",
                    "relative orientation", "phase synchronization"],
    },
    {
        "id": "contact_mode",
        "phrase": "Decide how contact behaves through the move (hold or release timing).",
        "members": ["contact persists", "contact transfers"],
    },
    {
        "id": "readable_camera",
        "phrase": "Camera must keep the interaction readable.",
        "members": ["camera visibility", "subject visibility", "interaction visibility"],
    },
    {
        "id": "causal_chain",
        "phrase": "Each beat must be set up by the previous one (causal chain).",
        "members": ["causal dependency", "reaction follows cause"],
    },
]

# correction token -> affected semantic keys (deterministic targeted invalidation)
CORRECTION_KEYWORDS = {
    "release": ["contact persistence", "contact_transfer", "contact_mode"],
    "grip": ["contact persistence", "contact identity", "contact_mode"],
    "hold": ["contact persistence", "contact_mode"],
    "camera": ["readable_camera"],
    "style": ["style"],
    "anime": ["style"],
    "identity": ["contact identity"],
    "fall": ["support"],
    "throw": ["causal_chain"],
}


def _sid(*parts: str) -> str:
    return "gp_" + hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]


def _jsonable(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, (tuple, set, frozenset)):
        return sorted(_jsonable(v) for v in value if not isinstance(v, (bytes,)) and v is not None)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return {k: _jsonable(v) for k, v in vars(value).items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _sha(value: Any) -> str:
    if isinstance(value, bytes):
        return hashlib.sha256(value).hexdigest()
    return hashlib.sha256(
        json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def classify_unknown(hypothesis: dict[str, Any]) -> str:
    """Unknown severity: BLOCKING / IMPORTANT_NONBLOCKING / OPTIONAL."""
    if hypothesis.get("blocking"):
        return "BLOCKING"
    if hypothesis["hypothesis_type"] in ("REQUIREMENT_HYPOTHESIS",
                                         "FAILURE_HYPOTHESIS"):
        return "IMPORTANT_NONBLOCKING"
    return "OPTIONAL"


def detect_mode(request_text: str, *, user_authorizes_best: bool = False) -> tuple[str, str]:
    low = " " + request_text.lower() + " "
    hits = [t for t in FAST_TRIGGERS if t in low]
    if hits:
        return "FAST", f"fast trigger: {hits[0]}"
    return "AUTO", "no explicit mode trigger"


class GuidedSessionStore:
    """In-process durable session registry (immutable revision history)."""

    def __init__(self):
        self.sessions: dict[str, dict[str, Any]] = {}

    def create(self, request: str, normalized_intent: dict[str, Any]) -> dict[str, Any]:
        session_id = "session_" + _sha(request + str(time.time_ns()))[:16]
        session = {
            "session_id": session_id,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "current_revision": 1,
            "interaction_mode": "AUTO",
            "original_request": request,
            "normalized_intent_id": "intent_" + _sha(normalized_intent)[:16],
            "normalized_intent_hash": _sha(normalized_intent),
            "active_closure_id": None,
            "active_projection_id": None,
            "user_decisions": [],
            "completion_decisions": [],
            "accepted_creative_choices": [],
            "rejected_creative_choices": [],
            "active_assumptions": [],
            "blocking_unknowns": [],
            "canonical_score_id": None,
            "prompt_build_id": None,
            "revision_history": [],
            "status": "DELIBERATING",
            "lineage": {"guided_version": GUIDED_VERSION},
        }
        session["state_hash"] = _sha({k: v for k, v in session.items()
                                      if k != "state_hash" and not k.startswith("_")})
        self.sessions[session_id] = session
        return session

    def get(self, session_id: str) -> dict[str, Any]:
        if session_id not in self.sessions:
            raise LookupError(f"unknown guided session: {session_id}")
        return self.sessions[session_id]

    def snapshot_revision(self, session_id: str) -> dict[str, Any]:
        session = self.get(session_id)
        snapshot = {k: json.loads(json.dumps(_jsonable(v)))
                    for k, v in session.items()
                    if k not in ("revision_history",) and not k.startswith("_")}
        session["revision_history"] = session["revision_history"] + [snapshot]
        session["current_revision"] += 1
        session["state_hash"] = _sha({k: v for k, v in session.items()
                                      if k != "state_hash" and not k.startswith("_")})
        return session

    def record_decision(self, session_id: str, decision: dict[str, Any]) -> None:
        session = self.get(session_id)
        session["completion_decisions"] = session["completion_decisions"] + [decision]
        if decision["decision_status"] == "USER_RESOLVED":
            session["user_decisions"] = session["user_decisions"] + [decision]
            if decision.get("creative_choice_id"):
                session["accepted_creative_choices"].append(
                    decision["creative_choice_id"])


STORE = GuidedSessionStore()


class GuidedProjector:
    def __init__(self, engine_builder, translation_builder):
        self.engine_builder = engine_builder
        self.translation_builder = translation_builder

    def project(self, session: dict[str, Any], deliberation: dict[str, Any],
                *, mode: str = "AUTO") -> dict[str, Any]:
        closure = deliberation["reasoning_closure_packet"]
        activation = deliberation["knowledge_activation_packet"]
        hypotheses = deliberation["hypothesis_set"]["hypotheses"]

        creative = [h for h in hypotheses
                    if h["structured_semantics"].get("competition_group")
                    and h["status"] in ("SUPPORTED", "WEAKLY_SUPPORTED")]
        blocking = [h for h in hypotheses if classify_unknown(h) == "BLOCKING"
                    and h["status"] != "SUPPORTED"]
        failures = [h for h in hypotheses if h["hypothesis_type"] == "FAILURE_HYPOTHESIS"
                    and h["status"] == "SUPPORTED"]
        safe = [h for h in hypotheses if h["hypothesis_id"] in closure["safe_inferences"]]

        # mode decision
        if mode == "AUTO":
            if not blocking and not creative:
                mode = "FAST"
                mode_reason = "no blocking unknowns and no material creative fork"
            else:
                mode = "GUIDED"
                mode_reason = ("material creative fork present" if creative
                               else "blocking unknown present")
        else:
            mode_reason = "explicit mode"

        clarification = []
        creative = creative if mode == "GUIDED" else []  # FAST asks zero optional
        for h in creative[:3]:
            clarification.append({
                "question_id": _sid("q", h["hypothesis_id"]),
                "subject": h["structured_semantics"].get("competition_group", "choice"),
                "question": ("Should the contact hold through the whole move, "
                             "or transfer/release partway?")
                if h["structured_semantics"].get("key", "").startswith("contact")
                else f"Decide: {h['claim']}",
                "options": ["hold throughout", "transfer partway", "leave to CPCS"],
                "affected_hypothesis_ids": [h["hypothesis_id"]],
                "severity": "IMPORTANT_NONBLOCKING",
            })
        for h in blocking[:2]:
            clarification.append({
                "question_id": _sid("q", h["hypothesis_id"]),
                "subject": "blocking",
                "question": h["claim"],
                "options": [],
                "affected_hypothesis_ids": [h["hypothesis_id"]],
                "severity": "BLOCKING",
            })

        compression_used = []
        for group in COMPRESSION_GROUPS:
            if any(member in json.dumps([h["claim"] for h in hypotheses]).lower()
                   or any(h["structured_semantics"].get("key") == member
                          for h in hypotheses)
                   for member in group["members"]):
                compression_used.append({"group_id": group["id"],
                                         "phrase": group["phrase"]})

        projection = {
            "projection_id": "projection_" + _sid(session["session_id"],
                                                  str(session["current_revision"]))[:16],
            "session_id": session["session_id"],
            "revision_id": session["current_revision"],
            "source_request_id": session["normalized_intent_id"],
            "source_closure_id": closure["closure_id"],
            "source_closure_hash": closure["packet_hash"],
            "interaction_mode": mode,
            "interaction_decision": mode_reason,
            "understood_intent": session["original_request"],
            "important_inferences": [h["claim"] for h in safe[:5]],
            "protected_invariants": [h["claim"] for h in safe
                                     if h["hypothesis_type"] in
                                     ("REQUIREMENT_HYPOTHESIS",)][:5],
            "important_failure_risks": [h["claim"] for h in failures[:5]],
            "creative_choices": [{"choice_id": h["hypothesis_id"],
                                  "summary": h["claim"]} for h in creative[:3]],
            "clarification_candidates": clarification,
            "safe_inferences_applied": [h["hypothesis_id"] for h in safe],
            "grounded_recommendations": [],
            "baseline_defaults_applied": [],
            "details_left_unspecified": [],
            "blocking_unknowns": [{"hypothesis_id": h["hypothesis_id"],
                                   "claim": h["claim"],
                                   "severity": "BLOCKING"} for h in blocking],
            "canonical_effect_summary": {
                "requirements": activation["candidate_requirements"],
                "failure_families": activation["candidate_failure_families"],
            },
            "verification_summary": {
                "verification_obligations": len(closure["verification_requirements"]),
            },
            "hidden_reasoning_summary": {
                "observation_count": len(deliberation["observations"]),
                "hypothesis_count": len(hypotheses),
                "query_count": len(deliberation["query_steering_plan"]["queries"]),
                "evidence_update_count": len(deliberation["hypothesis_updates"]),
                "prerequisite_count": sum(1 for h in hypotheses
                                          if h["hypothesis_type"] == "CAUSAL_HYPOTHESIS"),
                "safe_inference_count": len(safe),
                "canonical_control_count": len(closure["resolved_requirements"]),
            },
            "compression": compression_used,
            "source_attribution": {
                "authority_order": AUTHORITY_ORDER,
                "closure_hash": closure["packet_hash"],
            },
            "lineage": {
                "deliberation_id": deliberation["deliberation_id"],
                "guided_version": GUIDED_VERSION,
            },
        }
        projection["projection_hash"] = _sha(
            {k: v for k, v in projection.items() if k != "projection_hash"})
        return projection

    # ------------------------------------------------------- completion
    def build_completion_decisions(self, session: dict[str, Any],
                                   deliberation: dict[str, Any],
                                   projection: dict[str, Any]) -> list[dict[str, Any]]:
        closure = deliberation["reasoning_closure_packet"]
        decisions = []
        for h in deliberation["hypothesis_set"]["hypotheses"]:
            if h["status"] == "SUPPORTED" and h["hypothesis_id"] in closure["safe_inferences"]:
                status = "SAFE_INFERRED"
            elif h.get("blocking"):
                status = "BLOCKING"
            elif h["hypothesis_type"] in ("FAILURE_HYPOTHESIS",
                                          "REQUIREMENT_HYPOTHESIS"):
                status = "SAFE_INFERRED"
            else:
                status = "LEFT_UNSPECIFIED"
            decisions.append({
                "decision_id": _sid("dec", h["hypothesis_id"]),
                "session_id": session["session_id"],
                "revision_id": session["current_revision"],
                "subject": h["claim"],
                "decision_status": status,
                "selected_value": h["claim"] if status != "LEFT_UNSPECIFIED" else None,
                "alternative_values": [],
                "reason": f"closure status {h['status']}",
                "authority_source": {"SAFE_INFERRED": "CPCS_SAFE_INFERENCE",
                                     "BLOCKING": None,
                                     "LEFT_UNSPECIFIED": "LEAVE_UNSPECIFIED"}[status],
                "affected_requirement_ids": h["candidate_requirement_ids"],
                "affected_hypothesis_ids": [h["hypothesis_id"]],
                "affected_paths": [],
                "evidence_refs": h["supporting_evidence_ids"],
                "confidence": h["confidence"],
                "lineage": {"hypothesis_id": h["hypothesis_id"]},
            })
            decisions[-1]["decision_hash"] = _sha(
                {k: v for k, v in decisions[-1].items() if k != "decision_hash"})
        return decisions

    # ------------------------------------------------------- targeted revision
    def targeted_invalidation(self, session: dict[str, Any],
                              correction: str,
                              hypotheses: list[dict[str, Any]]) -> dict[str, Any]:
        low = correction.lower()
        affected_keys = set()
        for token, keys in CORRECTION_KEYWORDS.items():
            if token in low:
                affected_keys |= set(keys)
        invalidated = []
        preserved = []
        for h in hypotheses:
            key = h["structured_semantics"].get("key", "")
            claim_low = h["claim"].lower()
            hit = (key in affected_keys or
                   any(k in claim_low for k in affected_keys if len(k) > 4))
            if hit:
                invalidated.append(h["hypothesis_id"])
            else:
                preserved.append(h["hypothesis_id"])
        # dependency closure: causal hypotheses depending on invalidated ids
        for h in hypotheses:
            if h["hypothesis_id"] in preserved and any(
                    dep in invalidated for dep in h.get("prerequisite_hypothesis_ids", [])):
                preserved.remove(h["hypothesis_id"])
                invalidated.append(h["hypothesis_id"])
        return {
            "invalidated_ids": sorted(invalidated),
            "recomputed_ids": sorted(invalidated),
            "preserved_ids": sorted(preserved),
            "correction": correction,
        }
