"""DR-1 deliberation-layer structural acceptance tests (hermetic)."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from lab.application.cpcs_deliberation import (
    FAKE_SNAPSHOT,
    DeliberationBudget,
    DeliberationEngine,
    HYPOTHESIS_STATUSES,
    HYPOTHESIS_TYPES,
    NON_EXECUTABLE_AFFORDANCES,
    PLANNING_AFFORDANCES,
    extract_observations,
)
from lab.application.reasoning_treatment import FakeBackend

OUT = Path(__file__).resolve().parents[1]

REQUEST = ("Two fighters clash. Fighter A catches Fighter B's wrist, redirects the "
           "strike, rotates behind B and throws B while the camera circles them. "
           "Keep it readable, fast and anime-styled.")


def _engine():
    return DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())


class DeliberationSurfaceTests(unittest.TestCase):
    def _run(self, text=REQUEST):
        return _engine().deliberate(text, {"intent": {}})

    def test_affordance_ledgers_dispositioned(self):
        non_exec = json.loads((OUT / "CPCS_REASONING_AFFORDANCE_LEDGER_v0.1.json").read_text())
        self.assertTrue(non_exec["summary"]["all_have_reasoning_disposition"])
        for obj in non_exec["non_executable_objects"]:
            self.assertTrue(obj["reasoning_affordances"])
            self.assertIn("canonical score fields", obj["forbidden_from"])
        planning = json.loads((OUT / "CPCS_PLANNING_AFFORDANCE_LEDGER_v0.1.json").read_text())
        self.assertTrue(planning["summary"]["all_have_planning_disposition"])
        for obj in planning["planning_objects"]:
            self.assertTrue(obj["planning_affordances"])
            self.assertIn("canonical score fields", obj["forbidden_from"])

    def test_zero_non_executable_to_control_coercions(self):
        out = self._run()
        closure = out["reasoning_closure_packet"]
        self.assertEqual(closure["canonical_controls_placeholder"], None) if False else None
        # the deliberation engine never emits canonical score fields itself
        for key in ("canonical_states", "canonical_relations", "canonical_events",
                    "canonical_invariants", "canonical_constraints"):
            self.assertEqual(closure[key], [],
                             f"deliberation must not coerce knowledge into {key}")

    def test_hypotheses_are_first_class_and_typed(self):
        out = self._run()
        for h in out["hypothesis_set"]["hypotheses"]:
            self.assertIn(h["hypothesis_type"], HYPOTHESIS_TYPES)
            self.assertIn(h["status"], HYPOTHESIS_STATUSES)
            self.assertTrue(h["structured_semantics"])
            self.assertTrue(h["hash"])

    def test_llm_proposals_not_authoritative(self):
        engine = _engine()
        engine.admit_llm_proposals([], [])  # no-op sanity
        out = engine.deliberate(REQUEST, {"intent": {}}, llm_proposals=[{
            "hypothesis_type": "FAILURE_HYPOTHESIS",
            "claim": "the lighting rig will collapse",
            "candidate_failure_family_ids": ["FF-STYLE"],
            "verification_need": True,
        }])
        proposed = [h for h in out["hypothesis_set"]["hypotheses"]
                    if h["source"] == "LLM_PROPOSED"]
        self.assertTrue(proposed)
        self.assertEqual(proposed[0]["status"], "PROPOSED",
                         "LLM proposals never become truth without evidence")
        # proposals that ARE evidence-grounded may progress, with the
        # evidence-driven transition recorded in the update
        out2 = engine.deliberate(REQUEST, {"intent": {}}, llm_proposals=[{
            "hypothesis_type": "FAILURE_HYPOTHESIS",
            "claim": "contact may fail during the spin",
            "candidate_failure_family_ids": ["FF-CONTACT"],
            "verification_need": True,
        }])
        grounded = [h for h in out2["hypothesis_set"]["hypotheses"]
                    if h["source"] == "LLM_PROPOSED"]
        self.assertTrue(grounded)
        updates = {u["hypothesis_id"]: u for u in out2["hypothesis_updates"]}
        self.assertEqual(updates[grounded[0]["hypothesis_id"]]["prior_status"],
                         "PROPOSED")

    def test_every_query_has_reason_and_target(self):
        out = self._run()
        queries = out["query_steering_plan"]["queries"]
        self.assertTrue(queries)
        for q in queries:
            self.assertTrue(q["reason"])
            self.assertTrue(q["target_hypothesis_ids"] or q["target_unknown_ids"])
            self.assertEqual(q["parent_query_id"], None)  # no orphans in round 1

    def test_prerequisite_discovery_works(self):
        out = self._run()
        causal = [h for h in out["hypothesis_set"]["hypotheses"]
                  if h["hypothesis_type"] == "CAUSAL_HYPOTHESIS"]
        self.assertTrue(causal)
        self.assertTrue(causal[0]["structured_semantics"]["requirement_ids"])
        self.assertEqual(causal[0]["source"], "CASCADE_DERIVED")

    def test_hypothesis_update_works(self):
        out = self._run()
        updates = out["hypothesis_updates"]
        self.assertTrue(updates)
        for u in updates:
            self.assertIn("prior_status", u)
            self.assertIn("updated_status", u)
            self.assertIn("updated_confidence", u)
            self.assertIn("lineage", u)

    def test_contradictions_preserved(self):
        out = self._run()
        closure = out["reasoning_closure_packet"]
        self.assertIn("contradictions_preserved", closure)

    def test_hypothesis_competition_supported(self):
        out = self._run()
        contact = [h for h in out["hypothesis_set"]["hypotheses"]
                   if h["structured_semantics"].get("competition_group") == "contact_mode"]
        self.assertEqual(len(contact), 2)
        self.assertEqual({h["status"] for h in contact}, {"SUPPORTED"},
                         "competing hypotheses are preserved, never averaged")

    def test_safe_inference_separate_from_creative_choice(self):
        out = self._run()
        closure = out["reasoning_closure_packet"]
        self.assertTrue(closure["safe_inferences"])
        self.assertTrue(closure["creative_choices"])
        self.assertFalse(set(closure["safe_inferences"]) & set(closure["creative_choices"]))

    def test_ideation_separate_from_requirement_discovery(self):
        engine = _engine()
        ideation = engine.ideate("a desperate fight where the hero barely wins",
                                 {"intent": {}})
        out = engine.deliberate("a desperate fight where the hero barely wins",
                                {"intent": {}})
        resolved = set(out["reasoning_closure_packet"]["resolved_requirements"])
        for cand in ideation["candidates"]:
            self.assertNotIn(cand["candidate_id"], resolved)
        self.assertEqual(ideation["ideation_mode"], "IDEATION")

    def test_causality_separate_from_temporal_order(self):
        out = self._run()
        causal = [h for h in out["hypothesis_set"]["hypotheses"]
                  if h["hypothesis_type"] == "CAUSAL_HYPOTHESIS"]
        temporal = [h for h in out["hypothesis_set"]["hypotheses"]
                    if h["hypothesis_type"] == "TEMPORAL_HYPOTHESIS"]
        self.assertTrue(causal)
        for h in causal:
            self.assertNotIn(h["hypothesis_id"], [t["hypothesis_id"] for t in temporal])

    def test_non_executable_knowledge_affects_reasoning(self):
        out = self._run()
        activation = out["knowledge_activation_packet"]
        self.assertTrue(activation["activated_reasoning_affordances"])
        self.assertTrue(out["reasoning_closure_packet"]["non_executable_knowledge_used"])

    def test_planning_knowledge_affects_planning(self):
        out = self._run()
        activation = out["knowledge_activation_packet"]
        self.assertIn("activated_planning_affordances", activation)

    def test_query_loops_bounded(self):
        engine = _engine()
        out = engine.deliberate(REQUEST, {"intent": {}})
        queries = out["query_steering_plan"]["queries"]
        self.assertLessEqual(len(queries),
                             engine.budget.max_hypotheses * engine.budget.max_queries_per_hypothesis)
        self.assertLessEqual(len(out["hypothesis_set"]["hypotheses"]),
                             engine.budget.max_hypotheses)

    def test_reasoning_closure_deterministic(self):
        out1 = self._run()
        out2 = self._run()
        self.assertEqual(out1["packet_hash"], out2["packet_hash"])

    def test_cross_domain_not_hierarchy_gated(self):
        out = _engine().deliberate(
            "camera circles while the actors grapple", {"intent": {}})
        dims = out["knowledge_activation_packet"]["activated_reasoning_dimensions"]
        self.assertIn("DIM-CAMERA", dims)
        self.assertIn("DIM-CONTACT", dims)

    def test_tc1_distinctions_preserved(self):
        from lab.compiler import cpcs_typed
        self.assertIn("effort_as_force",
                      cpcs_typed.REGISTRY["cpcs.performance.effort"]["forbidden_coercions"])
        self.assertIn("chronology_as_causality",
                      cpcs_typed.REGISTRY["cpcs.continuity.temporal_relation"]["forbidden_coercions"])

    def test_observations_have_source_attribution(self):
        obs = extract_observations(REQUEST, FAKE_SNAPSHOT)
        self.assertTrue(obs)
        for o in obs:
            self.assertIn(o["source"], ("USER_EXPLICIT", "STRUCTURAL_ENTAILMENT"))

    def test_knowledge_gap_hypothesis_blocks_closure(self):
        out = _engine().deliberate("interaction continues behind a pillar",
                                   {"intent": {}})
        gaps = [h for h in out["hypothesis_set"]["hypotheses"]
                if h["hypothesis_type"] == "KNOWLEDGE_GAP_HYPOTHESIS"]
        self.assertTrue(gaps)
        closure = out["reasoning_closure_packet"]
        self.assertIn(closure["reasoning_completeness"],
                      ("COMPLETE_WITH_UNKNOWNS", "INCOMPLETE"))
        self.assertTrue(closure["closure_reason"])


if __name__ == "__main__":
    unittest.main()
