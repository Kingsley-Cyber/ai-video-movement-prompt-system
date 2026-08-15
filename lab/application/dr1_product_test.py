"""DR-1 product test: full fight request through the frozen runtime deliberation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lab.application.cpcs_deliberation import (
    DeliberationEngine,
    frozen_knowledge_snapshot,
)
from lab.application.reasoning_treatment import FrozenRuntimeBackend, TreatmentAdapter
from lab.compiler.profiles import REPO_ROOT
from lab.second_brain.src.intent import build_intent_context

REQUEST = ("Two fighters clash. Fighter A catches Fighter B's wrist, redirects the "
           "strike, rotates behind B and throws B while the camera circles them. "
           "Keep it readable, fast and anime-styled.")

OUT = Path(__file__).resolve().parent


def main() -> int:
    snapshot = frozen_knowledge_snapshot()
    backend = FrozenRuntimeBackend()
    ic = build_intent_context(REQUEST, root=REPO_ROOT)
    engine = DeliberationEngine(snapshot, backend)
    out = engine.deliberate(REQUEST, ic["normalized_intent"])
    packet = backend.plan(REQUEST, ic["normalized_intent"])
    translation = TreatmentAdapter(REPO_ROOT).translate(packet)
    closure = out["reasoning_closure_packet"]
    activation = out["knowledge_activation_packet"]

    trace = {
        "artifact": "CPCS_DELIBERATION_PRODUCT_TEST", "version": "v0.1",
        "request": REQUEST,
        "A_explicit_observations": [
            {"id": o["observation_id"], "source": o["source"], "text": o["text"]}
            for o in out["observations"][:24]],
        "B_knowledge_activated": {
            "domains": activation["activated_domains"],
            "dimensions": activation["activated_reasoning_dimensions"],
            "reasoning_affordances": activation["activated_reasoning_affordances"],
            "planning_affordances": activation["activated_planning_affordances"],
            "triggers": activation["activated_triggers"],
            "objectives": activation["candidate_objectives"],
            "failure_families": activation["candidate_failure_families"],
        },
        "C_hypotheses_initial": [
            {"id": h["hypothesis_id"], "type": h["hypothesis_type"],
             "claim": h["claim"], "status": h["status"],
             "semantics": h["structured_semantics"]}
            for h in out["hypothesis_set"]["hypotheses"]],
        "D_why_each_hypothesis_matters": [
            {"id": h["hypothesis_id"], "matters_because": (
                f"requirement coverage ({len(h['candidate_requirement_ids'])} reqs)"
                if h["hypothesis_type"] == "REQUIREMENT_HYPOTHESIS" else
                f"failure risk ({h['candidate_failure_family_ids']})"
                if h["hypothesis_type"] == "FAILURE_HYPOTHESIS" else
                h["hypothesis_type"])}
            for h in out["hypothesis_set"]["hypotheses"]],
        "E_queries_issued": [
            {"id": q["query_id"], "reason": q["reason"],
             "target_hypotheses": q["target_hypothesis_ids"],
             "representations": q["query_representations"], "priority": q["priority"]}
            for q in out["query_steering_plan"]["queries"][:30]],
        "F_evidence_returned": [e["atomic_record_id"] for e in
                                packet["retrieved_evidence"][:40]],
        "G_hypothesis_updates": [
            {"hypothesis_id": u["hypothesis_id"], "prior": u["prior_status"],
             "after": u["updated_status"], "confidence": u["updated_confidence"],
             "supporting": len(u["supporting_evidence_ids"]),
             "contradicting": len(u["contradicting_evidence_ids"])}
            for u in out["hypothesis_updates"]],
        "H_prerequisites_discovered": [
            h["claim"] for h in out["hypothesis_set"]["hypotheses"]
            if h["hypothesis_type"] == "CAUSAL_HYPOTHESIS"],
        "I_rejected_contradicted": {
            "contradicted": closure["contradicted_hypotheses"],
            "rejected": closure["rejected_hypotheses"]},
        "J_safe_inferences": closure["safe_inferences"],
        "K_creative_choices": closure["creative_choices"],
        "L_reasoning_closure": {
            "completeness": closure["reasoning_completeness"],
            "reason": closure["closure_reason"],
            "contradictions_preserved": closure["contradictions_preserved"]},
        "M_executable_requirements": closure["resolved_requirements"],
        "N_typed_canonical_controls": [
            {"object_id": o["value"].get("interaction_id")
             or o["value"].get("invariant_id") or o["value"].get("event_id")
             or o["value"].get("object_id") or o["value"].get("constraint_id")
             or o["value"].get("relation_id"),
             "schema": o["schema"], "target": o["target"],
             "lineage": o["value"]["lineage"]}
            for o in translation.structured_objects[:40]],
        "O_verification_obligations": len(translation.verification_requirements),
        "P_non_executable_knowledge_influencing_reasoning":
            closure["non_executable_knowledge_used"],
        "Q_planning_knowledge_influencing_query_strategy":
            activation["activated_planning_affordances"],
        "packet_hash": out["packet_hash"],
    }
    path = OUT / "CPCS_DELIBERATION_PRODUCT_TEST_v0.1.json"
    path.write_text(json.dumps(trace, indent=1,
                               default=lambda o: o.decode("utf-8", "replace")
                               if isinstance(o, bytes) else str(o)))
    print("observations:", len(trace["A_explicit_observations"]),
          "| hypotheses:", len(trace["C_hypotheses_initial"]),
          "| queries:", len(trace["E_queries_issued"]),
          "| evidence:", len(trace["F_evidence_returned"]),
          "| updates:", len(trace["G_hypothesis_updates"]),
          "| prerequisites:", len(trace["H_prerequisites_discovered"]),
          "| safe:", len(closure["safe_inferences"]),
          "| creative:", len(closure["creative_choices"]),
          "| controls:", len(trace["N_typed_canonical_controls"]),
          "| closure:", closure["reasoning_completeness"])
    print("written:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
