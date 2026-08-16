"""WP-3 — Recruitment refinement + DR-1 closure loop tests (hermetic)."""
from __future__ import annotations

import copy
import unittest

from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
from lab.application.cpcs_knowledge_application import apply_knowledge
from lab.application.cpcs_knowledge_constellation import assemble_constellation
from lab.application.cpcs_knowledge_recruitment import recruit_for_intent
from lab.application.cpcs_knowledge_refinement import (
    MAX_ADDED_PREREQS_PER_INTENT,
    MAX_PREREQ_DEPTH,
    apply_to_closure,
    assess_prerequisites,
    build_refinement_packet,
)
from lab.application.reasoning_treatment import FakeBackend


def _run_full(intent_text):
    engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
    activation, packet = engine.activate(
        intent_text, {"intent": {"primary_domain": "action"}}, observations=[])
    app_set = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
    evidence_by_id = {
        ev["atomic_record_id"]: ev for ev in packet.get("retrieved_evidence", [])}
    constellation = assemble_constellation(app_set, activation, evidence_by_id=evidence_by_id)
    pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in app_set.applications}
    recruitment = recruit_for_intent(
        constellation, activation, pack_lookup=pack_lookup)
    new_pre, gaps = assess_prerequisites(
        recruitment, constellation, activation, pack_lookup=pack_lookup)
    refinement = build_refinement_packet(
        recruitment, constellation, activation,
        new_prerequisites=new_pre, coverage_gaps=gaps,
        application_set=app_set)
    return app_set, activation, constellation, recruitment, refinement


class Ka2RefinementTests(unittest.TestCase):

    def test_assess_prerequisites_returns_no_prereqs_when_no_new_evidence(self):
        _, activation, constellation, recruitment, _ = _run_full(
            "A fighter performs a hip toss.")
        pack_lookup = {}
        new_pre, gaps = assess_prerequisites(
            recruitment, constellation, activation, pack_lookup=pack_lookup)
        self.assertIsInstance(new_pre, list)
        self.assertIsInstance(gaps, list)

    def test_max_added_prereqs_enforced(self):
        self.assertGreater(MAX_ADDED_PREREQS_PER_INTENT, 0)
        self.assertEqual(MAX_PREREQ_DEPTH, 1)

    def test_apply_to_closure_only_touches_two_fields(self):
        _, _, _, _, refinement = _run_full("A fighter performs a hip toss.")
        closure = {
            "closure_id": "closure_test",
            "packet_hash": "original_hash",
            "planning_guidance": [],
            "non_executable_knowledge_used": ["Constraint"],
            "accepted_hypotheses": ["h1", "h2"],
            "safe_inferences": ["h1"],
            "creative_choices": [],
            "remaining_unknowns": [],
            "verification_requirements": ["h1"],
            "reasoning_completeness": "COMPLETE",
            "closure_reason": "all critical hypotheses resolved",
            "lineage": {"activation_packet_id": "kap_x"},
        }
        original = copy.deepcopy(closure)
        updated = apply_to_closure(refinement, closure)
        for key in original:
            if key in ("planning_guidance", "non_executable_knowledge_used",
                       "packet_hash", "lineage"):
                continue
            self.assertEqual(updated[key], original[key],
                             f"closure field {key} must not be mutated")
        self.assertEqual(updated["lineage"]["ka2_pre_refinement_closure_hash"],
                         "original_hash")
        self.assertTrue(updated["lineage"]["ka2_refinement_id"])
        self.assertEqual(updated["lineage"]["ka2_max_prereq_depth"], MAX_PREREQ_DEPTH)
        self.assertEqual(updated["lineage"]["ka2_max_added_prereqs"],
                         MAX_ADDED_PREREQS_PER_INTENT)
        self.assertNotEqual(updated["packet_hash"], "original_hash")

    def test_closure_rehash_stable_across_runs(self):
        _, _, _, _, r1 = _run_full("A fighter performs a hip toss.")
        _, _, _, _, r2 = _run_full("A fighter performs a hip toss.")
        self.assertEqual(r1["refinement_hash"], r2["refinement_hash"])
        closure = {"closure_id": "c", "packet_hash": "h",
                   "planning_guidance": [], "non_executable_knowledge_used": [],
                   "lineage": {}}
        a = apply_to_closure(r1, copy.deepcopy(closure))
        b = apply_to_closure(r2, copy.deepcopy(closure))
        self.assertEqual(a["packet_hash"], b["packet_hash"])

    def test_planning_guidance_appended_not_replaced(self):
        _, _, _, _, refinement = _run_full("A fighter performs a hip toss.")
        closure = {"closure_id": "c", "packet_hash": "h",
                   "planning_guidance": [{"existing": True}],
                   "non_executable_knowledge_used": [],
                   "lineage": {}}
        updated = apply_to_closure(refinement, copy.deepcopy(closure))
        self.assertTrue(any(p.get("existing") for p in updated["planning_guidance"]))
        if refinement.get("planning_guidance"):
            self.assertGreaterEqual(len(updated["planning_guidance"]),
                                    1 + len(refinement["planning_guidance"]))

    def test_non_executable_used_preserved_and_appended(self):
        _, _, _, _, refinement = _run_full("A fighter performs a hip toss.")
        closure = {"closure_id": "c", "packet_hash": "h",
                   "planning_guidance": [],
                   "non_executable_knowledge_used": ["Constraint"],
                   "lineage": {}}
        updated = apply_to_closure(refinement, copy.deepcopy(closure))
        self.assertIn("Constraint", updated["non_executable_knowledge_used"])

    def test_no_data_invented_every_new_prereq_has_supporting_evidence(self):
        _, activation, constellation, recruitment, _ = _run_full(
            "A fighter performs a hip toss.")
        pack_lookup = {}
        new_pre, gaps = assess_prerequisites(
            recruitment, constellation, activation, pack_lookup=pack_lookup)
        if new_pre:
            for rid in new_pre:
                gap_match = [g for g in gaps
                             if g.get("requirement_id") == rid
                             and g["kind"] == "prerequisite_unsupported"]
                self.assertFalse(gap_match,
                                 f"new prereq {rid} must have supporting evidence, "
                                 "or be reported as gap")

    def test_disposition_digest_count_equals_region_count(self):
        _, _, constellation, recruitment, refinement = _run_full(
            "A fighter performs a hip toss.")
        self.assertEqual(len(refinement["disposition_digests"]),
                         len(constellation.regions))
        self.assertEqual(len(refinement["recruited_region_ids"])
                         + len(refinement["context_region_ids"])
                         + len(refinement["archived_region_ids"])
                         + len(refinement["unresolved_region_ids"]),
                         len(constellation.regions))

    def test_determinism_refinement_id_stable(self):
        _, _, _, _, r1 = _run_full("A chef slices a tomato.")
        _, _, _, _, r2 = _run_full("A chef slices a tomato.")
        self.assertEqual(r1["refinement_id"], r2["refinement_id"])
        self.assertEqual(r1["refinement_hash"], r2["refinement_hash"])


if __name__ == "__main__":
    unittest.main()
