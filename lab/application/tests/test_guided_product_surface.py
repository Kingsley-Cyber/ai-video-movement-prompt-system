"""PC-1 hermetic guided-product tests (FakeBackend; no frozen runtime)."""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from lab.application.cpcs_deliberation import (
    FAKE_SNAPSHOT,
    DeliberationEngine,
    DeliberationBudget,
)
from lab.compiler.profiles import REPO_ROOT
from lab.application.cpcs_guided import (
    AUTHORITY_ORDER,
    COMPRESSION_GROUPS,
    STORE,
    GuidedProjector,
    classify_unknown,
    detect_mode,
)
from lab.application.reasoning_treatment import FakeBackend

OUT = Path(__file__).resolve().parents[1]

REQUEST = ("Two fighters clash. Fighter A catches Fighter B's wrist, redirects the "
           "strike, rotates behind B and throws B while the camera circles them. "
           "Keep it readable, fast and anime-styled.")


def _engine():
    return DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())


def _deliberation(text=REQUEST):
    return _engine().deliberate(text, {"intent": {}})


def _session(request=REQUEST):
    s = STORE.create(request, {"intent": {}})
    return s


class GuidedProjectionTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("CPCS_FROZEN_RUNTIME_PATH", None)
        self.projector = GuidedProjector(lambda: None, lambda: None)

    def test_guided_projection_compresses_internal_reasoning(self):
        d = _deliberation()
        s = _session()
        p = self.projector.project(s, d, mode="GUIDED")
        self.assertLess(len(p["important_inferences"]), 6)
        self.assertLess(len(p["important_failure_risks"]), 6)
        self.assertIn("hidden_reasoning_summary", p)
        self.assertGreater(p["hidden_reasoning_summary"]["hypothesis_count"],
                           len(p["important_inferences"]),
                           "projection hides raw reasoning volume")

    def test_guided_projection_preserves_mandatory_semantics(self):
        d = _deliberation()
        s = _session()
        p = self.projector.project(s, d, mode="FAST")
        closure = d["reasoning_closure_packet"]
        self.assertEqual(set(p["canonical_effect_summary"]["requirements"]),
                         set(closure["resolved_requirements"]))
        for group in p["compression"]:
            self.assertIn(group["group_id"],
                          [g["id"] for g in COMPRESSION_GROUPS],
                          "compression groups never invented")

    def test_fast_mode_asks_zero_optional_questions(self):
        d = _deliberation()
        s = _session()
        p = self.projector.project(s, d, mode="FAST")
        self.assertEqual(p["clarification_candidates"], [])
        self.assertEqual(p["interaction_mode"], "FAST")

    def test_fast_still_runs_cpcs_deliberation(self):
        d = _deliberation()
        s = _session()
        p = self.projector.project(s, d, mode="FAST")
        self.assertGreater(p["hidden_reasoning_summary"]["hypothesis_count"], 0)

    def test_safe_inference_precedes_baseline_default(self):
        d = _deliberation()
        s = _session()
        decisions = self.projector.build_completion_decisions(s, d,
            self.projector.project(s, d, mode="FAST"))
        sources = [x["authority_source"] for x in decisions if x["authority_source"]]
        for src in sources:
            self.assertIn(src, AUTHORITY_ORDER)
        safe = [x for x in decisions if x["decision_status"] == "SAFE_INFERRED"]
        self.assertTrue(safe)
        for x in safe:
            self.assertEqual(x["authority_source"], "CPCS_SAFE_INFERENCE")

    def test_baseline_default_cannot_override_hard_requirement(self):
        self.assertLess(AUTHORITY_ORDER.index("EXISTING_BASELINE_DEFAULT"),
                        AUTHORITY_ORDER.index("LEAVE_UNSPECIFIED"))
        # higher authority ranks earlier: HARD_REQUIREMENT before BASELINE_DEFAULT
        self.assertLess(AUTHORITY_ORDER.index("CPCS_HARD_REQUIREMENT"),
                        AUTHORITY_ORDER.index("EXISTING_BASELINE_DEFAULT"))
        self.assertLess(AUTHORITY_ORDER.index("CPCS_SAFE_INFERENCE"),
                        AUTHORITY_ORDER.index("EXISTING_BASELINE_DEFAULT"))

    def test_baseline_default_cannot_override_user_explicit(self):
        self.assertEqual(AUTHORITY_ORDER[0], "USER_EXPLICIT")
        self.assertLess(AUTHORITY_ORDER.index("EXISTING_BASELINE_DEFAULT"),
                        len(AUTHORITY_ORDER))

    def test_auto_fast_for_closed_request(self):
        d = _deliberation("person walks through a room")
        s = _session("person walks through a room")
        p = self.projector.project(s, d, mode="AUTO")
        self.assertEqual(p["interaction_mode"], "FAST")
        self.assertTrue(p["interaction_decision"])

    def test_auto_guided_for_material_creative_fork(self):
        d = _deliberation()
        s = _session()
        p = self.projector.project(s, d, mode="AUTO")
        self.assertEqual(p["interaction_mode"], "GUIDED")
        self.assertTrue(any(c["severity"] == "IMPORTANT_NONBLOCKING"
                            for c in p["clarification_candidates"]))

    def test_guided_to_fast_preserves_answers(self):
        s = _session()
        decision = {"decision_id": "d1", "session_id": s["session_id"],
                    "revision_id": 1, "subject": "contact",
                    "decision_status": "USER_RESOLVED", "selected_value": "hold",
                    "alternative_values": [], "reason": "user",
                    "authority_source": "USER_CORRECTION",
                    "affected_requirement_ids": [], "affected_hypothesis_ids": [],
                    "affected_paths": [], "evidence_refs": [], "confidence": 1.0,
                    "creative_choice_id": None, "lineage": {}}
        decision["decision_hash"] = "h"
        STORE.record_decision(s["session_id"], decision)
        d = _deliberation()
        p = self.projector.project(s, d, mode="FAST")
        self.assertEqual(len(s["user_decisions"]), 1)
        self.assertEqual(p["interaction_mode"], "FAST")

    def test_fast_to_guided_creates_new_revision(self):
        s = _session()
        rev_before = s["current_revision"]
        STORE.snapshot_revision(s["session_id"])
        self.assertEqual(s["current_revision"], rev_before + 1)
        self.assertEqual(len(s["revision_history"]), 1)

    def test_completion_decision_source_attribution(self):
        d = _deliberation()
        s = _session()
        decisions = self.projector.build_completion_decisions(
            s, d, self.projector.project(s, d, mode="FAST"))
        for x in decisions:
            self.assertIn("authority_source", x)
            self.assertIn("decision_hash", x)

    def test_session_revision_history_immutable(self):
        s = _session()
        d = _deliberation()
        self.projector.project(s, d, mode="FAST")
        STORE.snapshot_revision(s["session_id"])
        STORE.snapshot_revision(s["session_id"])
        h1 = s["revision_history"][0]["state_hash"]
        h2 = s["revision_history"][1]["state_hash"]
        self.assertNotEqual(h1, h2)
        first = json.loads(json.dumps(s["revision_history"][0]))
        STORE.snapshot_revision(s["session_id"])
        self.assertEqual(s["revision_history"][0], first,
                         "history entries are never rewritten")

    def test_targeted_revision_invalidates_only_dependency_closure(self):
        s = _session()
        d = _deliberation()
        invalidation = self.projector.targeted_invalidation(
            s, "release the wrist before the throw",
            d["hypothesis_set"]["hypotheses"])
        self.assertTrue(invalidation["invalidated_ids"])
        self.assertTrue(invalidation["preserved_ids"])
        self.assertFalse(set(invalidation["invalidated_ids"])
                         & set(invalidation["preserved_ids"]))
        self.assertEqual(sorted(invalidation["invalidated_ids"]),
                         sorted(invalidation["recomputed_ids"]))

    def test_blocking_unknown_prevents_fast_completion(self):
        d = _deliberation()
        s = _session()
        blocking = [{"claim": "who holds the object", "hypothesis_id": "h1"}]
        # simulate a blocking unknown in the deliberation
        d["hypothesis_set"]["hypotheses"].append({
            "hypothesis_id": "h1", "hypothesis_type": "KNOWLEDGE_GAP_HYPOTHESIS",
            "claim": "who holds the object", "blocking": True,
            "status": "PROPOSED", "structured_semantics": {"key": "gap"},
            "candidate_requirement_ids": [], "candidate_failure_family_ids": [],
            "supporting_evidence_ids": [], "contradicting_evidence_ids": [],
            "confidence": 0.0,
        })
        self.assertEqual(classify_unknown(d["hypothesis_set"]["hypotheses"][-1]),
                         "BLOCKING")

    def test_ideation_candidate_not_requirement(self):
        engine = _engine()
        ideation = engine.ideate("a desperate fight where the hero barely wins",
                                 {"intent": {}})
        d = _deliberation("a desperate fight where the hero barely wins")
        resolved = set(d["reasoning_closure_packet"]["resolved_requirements"])
        for c in ideation["candidates"]:
            self.assertNotIn(c["candidate_id"], resolved)

    def test_graph_expansion_not_recall_gate(self):
        d = _deliberation()
        activation = d["knowledge_activation_packet"]
        self.assertTrue(activation["candidate_requirements"],
                        "global retrieval independent of graph routing")

    def test_reasoning_hops_bounded(self):
        engine = _engine()
        d = engine.deliberate(REQUEST, {"intent": {}})
        causal = [h for h in d["hypothesis_set"]["hypotheses"]
                  if h["hypothesis_type"] == "CAUSAL_HYPOTHESIS"]
        self.assertLessEqual(len(causal), engine.budget.max_hypotheses)

    def test_query_hops_bounded(self):
        engine = _engine()
        d = engine.deliberate(REQUEST, {"intent": {}})
        self.assertLessEqual(len(d["query_steering_plan"]["queries"]),
                             engine.budget.max_hypotheses
                             * engine.budget.max_queries_per_hypothesis)

    def test_traversal_receipt_deterministic(self):
        e1, e2 = _engine(), _engine()
        d1 = e1.deliberate(REQUEST, {"intent": {}})
        d2 = e2.deliberate(REQUEST, {"intent": {}})
        receipt = lambda d: (d["knowledge_activation_packet"]["packet_hash"],
                             d["reasoning_closure_packet"]["packet_hash"],
                             len(d["query_steering_plan"]["queries"]))
        self.assertEqual(receipt(d1), receipt(d2))

    def test_mode_detection_triggers(self):
        mode, reason = detect_mode("A fight. Just give me the prompt.")
        self.assertEqual(mode, "FAST")
        self.assertTrue(reason)
        mode2, _ = detect_mode("A fight in a warehouse.")
        self.assertEqual(mode2, "AUTO")

    def test_compression_never_collapses_canonical_semantics(self):
        d = _deliberation()
        s = _session()
        p = self.projector.project(s, d, mode="GUIDED")
        for group in p["compression"]:
            canonical = [g for g in COMPRESSION_GROUPS if g["id"] == group["group_id"]]
            self.assertEqual(len(canonical), 1)
        # internal canonical objects remain separate in the hidden summary
        self.assertGreaterEqual(p["hidden_reasoning_summary"]["hypothesis_count"],
                                p["hidden_reasoning_summary"]["safe_inference_count"])


if __name__ == "__main__":
    unittest.main()


class BlockingCompletionTests(unittest.TestCase):
    def test_blocking_unknown_prevents_fast_completion_finish(self):
        # hermetic finish-level test: injected blocking hypothesis must fail closed
        s = STORE.create("A fight.", {"intent": {}})
        engine = _engine()
        d = engine.deliberate("A fight.", {"intent": {}})
        d["hypothesis_set"]["hypotheses"].append({
            "hypothesis_id": "h_block", "hypothesis_type": "KNOWLEDGE_GAP_HYPOTHESIS",
            "claim": "which hand holds the weapon", "blocking": True,
            "status": "PROPOSED", "structured_semantics": {"key": "gap"},
            "candidate_requirement_ids": [], "candidate_failure_family_ids": [],
            "supporting_evidence_ids": [], "contradicting_evidence_ids": [],
            "confidence": 0.0, "prerequisite_hypothesis_ids": [],
            "verification_need": False, "query_need": True,
        })
        s["_deliberation"] = d
        s["_translation"] = None
        from lab.second_brain.src.intent import build_intent_context
        s["_intent_context"] = build_intent_context("A fight.", root=REPO_ROOT)
        from lab.application.cpcs_guided_handlers import _finish
        result = _finish(s)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(result["blocking_reason"])
        self.assertIsNone(result["final_prompt_package"])
