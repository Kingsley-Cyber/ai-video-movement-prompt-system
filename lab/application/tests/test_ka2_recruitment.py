"""WP-2 — Recruitment gate tests (hermetic)."""
from __future__ import annotations

import unittest

from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
from lab.application.cpcs_knowledge_application import apply_knowledge
from lab.application.cpcs_knowledge_constellation import assemble_constellation
from lab.application.cpcs_knowledge_recruitment import (
    DISPOSITIONS,
    match_intent_signals,
    recruit_for_intent,
)
from lab.application.reasoning_treatment import FakeBackend, build_treatment_packet


def _set_and_constellation(intent_text, activation_overrides=None):
    engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
    activation, packet = engine.activate(
        intent_text, {"intent": {"primary_domain": "action"}}, observations=[])
    if activation_overrides:
        activation.update(activation_overrides)
    app_set = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
    evidence_by_id = {
        ev["atomic_record_id"]: ev for ev in packet.get("retrieved_evidence", [])}
    constellation = assemble_constellation(app_set, activation, evidence_by_id=evidence_by_id)
    return app_set, activation, constellation, evidence_by_id


class Ka2RecruitmentTests(unittest.TestCase):

    def test_dispostion_set_includes_all_four_values(self):
        self.assertEqual(
            DISPOSITIONS, frozenset({"RECRUIT", "CONTEXT", "ARCHIVE", "UNRESOLVED"}))

    def test_hip_toss_recruits_contact_and_support_regions(self):
        app_set, activation, constellation, _ = _set_and_constellation(
            "A fighter performs a hip toss.")
        pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in app_set.applications}
        result = recruit_for_intent(constellation, activation, pack_lookup=pack_lookup)
        dispositions = result["dispositions"]
        self.assertGreater(len(dispositions), 0)
        self.assertGreater(
            sum(1 for d in dispositions if d["disposition"] == "RECRUIT"), 0)
        for d in dispositions:
            self.assertIn(d["disposition"], DISPOSITIONS)
            self.assertTrue(d["disposition_hash"])
            self.assertTrue(d["reason_codes"])

    def test_match_intent_signals_returns_bound_sets(self):
        region = {"region_id": "r1", "requirement_ids": ["REQ-CONTACT-1"],
                  "failure_family_ids": ["FF-CONTACT"], "objective_ids": [],
                  "trigger_ids": []}
        activation = {"candidate_requirements": ["REQ-CONTACT-1"],
                      "candidate_failure_families": ["FF-CONTACT"],
                      "candidate_objectives": [],
                      "activated_concepts": [],
                      "activated_triggers": [],
                      "activated_reasoning_dimensions": [],
                      "activated_reasoning_affordances": []}
        sig = match_intent_signals(region, activation)
        self.assertEqual(sig["bound_requirement_ids"], ["REQ-CONTACT-1"])
        self.assertEqual(sig["bound_failure_family_ids"], ["FF-CONTACT"])

    def test_archive_when_no_signal_and_evidence_present(self):
        app_set, activation, constellation, _ = _set_and_constellation(
            "A fighter performs a hip toss.")
        pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in app_set.applications}
        constrained_activation = {
            "packet_id": activation.get("packet_id"),
            "candidate_requirements": [],
            "candidate_failure_families": [],
            "candidate_objectives": [],
            "activated_concepts": [],
            "activated_triggers": [],
            "activated_reasoning_dimensions": [],
            "activated_reasoning_affordances": [],
        }
        result = recruit_for_intent(
            constellation, constrained_activation, pack_lookup=pack_lookup)
        dispositions = result["dispositions"]
        regions_with_evidence = [d for d in dispositions if d["evidence_ids"]]
        self.assertGreater(len(regions_with_evidence), 0)
        for d in regions_with_evidence:
            self.assertEqual(d["disposition"], "ARCHIVE")
            self.assertIn("peripheral_to_intent", d["reason_codes"])

    def test_coverage_gap_emitted_for_uncovered_mandatory(self):
        app_set, activation, constellation, _ = _set_and_constellation(
            "A fighter performs a hip toss.")
        pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in app_set.applications}
        forced_activation = dict(activation)
        forced_activation["candidate_requirements"] = sorted(
            set(activation.get("candidate_requirements", [])) | {"REQ-UNCOVERED-XYZ"})
        result = recruit_for_intent(
            constellation, forced_activation, pack_lookup=pack_lookup)
        gap_kinds = {g["kind"] for g in result["coverage_gaps"]}
        self.assertIn("mandatory_requirement_uncovered", gap_kinds)
        gap_reqs = {g.get("requirement_id") for g in result["coverage_gaps"]
                    if g["kind"] == "mandatory_requirement_uncovered"}
        self.assertIn("REQ-UNCOVERED-XYZ", gap_reqs)

    def test_determinism_two_runs_identical_recruitment_hash(self):
        app_set, activation, constellation, _ = _set_and_constellation(
            "A fighter performs a hip toss.")
        pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in app_set.applications}
        a = recruit_for_intent(constellation, activation, pack_lookup=pack_lookup)
        b = recruit_for_intent(constellation, activation, pack_lookup=pack_lookup)
        self.assertEqual(a["recruitment_hash"], b["recruitment_hash"])
        self.assertEqual(a, b)

    def test_no_silent_drops_every_region_has_disposition(self):
        app_set, activation, constellation, _ = _set_and_constellation(
            "A fighter performs a hip toss.")
        pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in app_set.applications}
        result = recruit_for_intent(constellation, activation, pack_lookup=pack_lookup)
        region_ids = {r["region_id"] for r in constellation.regions}
        disp_ids = {d["region_id"] for d in result["dispositions"]}
        self.assertEqual(region_ids, disp_ids)

    def test_unresolved_for_empty_region(self):
        empty_constellation = type("C", (), {})()
        empty_constellation.regions = [{
            "region_id": "r_empty", "pack_ids": [], "evidence_ids": [],
            "canonical_concept_ids": [], "trigger_ids": [],
            "objective_ids": [], "failure_family_ids": [],
            "requirement_ids": [], "principle_families": [],
            "representation_mix": {}}]
        empty_constellation.region_dependency_edges = []
        empty_constellation.constellation_id = "c_empty"
        empty_constellation.constellation_hash = "h"
        result = recruit_for_intent(empty_constellation, {"packet_id": "kap_empty"})
        self.assertEqual(result["dispositions"][0]["disposition"], "UNRESOLVED")

    def test_dependency_consequence_can_promote_to_recruit(self):
        packet = build_treatment_packet(
            treatment_id="t", source_intent_hash="dep",
            query_mode="INITIAL_GENERATION",
            activated_requirements=["REQ-CONTACT-1", "REQ-SUP-1"],
            mandatory_requirements=["REQ-CONTACT-1", "REQ-SUP-1"],
            conditional_requirements=[],
            required_pathways={"REQ-CONTACT-1": "covered", "REQ-SUP-1": "covered"},
            objectives_at_risk=["OBJ-CONTACT", "OBJ-PHYSICAL-PLAUSIBILITY"],
            predicted_failure_families=["FF-CONTACT", "FF-PHYSICS"],
            retrieved_evidence=[
                {"atomic_record_id": "ev_a",
                 "supported_requirement_ids": ["REQ-CONTACT-1"],
                 "failure_family_ids": ["FF-CONTACT"],
                 "objective_ids": ["OBJ-CONTACT"],
                 "universal_type": "Constraint",
                 "trigger_ids": [],
                 "canonical_concept_ids": []},
                {"atomic_record_id": "ev_b",
                 "supported_requirement_ids": ["REQ-SUP-1"],
                 "failure_family_ids": ["FF-PHYSICS"],
                 "objective_ids": ["OBJ-PHYSICAL-PLAUSIBILITY"],
                 "universal_type": "Concept",
                 "trigger_ids": [],
                 "canonical_concept_ids": []},
            ],
            proposed_obligations=[],
            proposed_controls=[{
                "control_id": "ctl_a", "control_type": ["CT-CONTACT-CONTRACT"],
                "target": "scene", "scope": "scene", "hardness": "HARD",
                "source": "EVIDENCE_DERIVED",
                "source_requirement_ids": ["REQ-CONTACT-1", "REQ-SUP-1"],
                "supporting_evidence_ids": ["ev_a", "ev_b"],
                "protected_objectives": ["OBJ-CONTACT", "OBJ-PHYSICAL-PLAUSIBILITY"],
                "prevented_failure_families": ["FF-CONTACT", "FF-PHYSICS"],
                "control_semantics": {"statement": "contact+support",
                                      "universal_type": "Constraint"},
                "action": "add",
            }],
            verification_obligations=[], unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="x",
            retrieval_runtime_freeze_identity="y",
        )
        activation = {
            "packet_id": "kap_dep",
            "candidate_requirements": ["REQ-CONTACT-1"],
            "candidate_failure_families": ["FF-CONTACT"],
            "candidate_objectives": ["OBJ-CONTACT"],
            "activated_concepts": [],
            "activated_triggers": [],
            "activated_reasoning_dimensions": [],
            "activated_reasoning_affordances": ["EVIDENCE_INTERPRETATION"],
        }
        app_set = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
        constellation = assemble_constellation(app_set, activation)
        pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in app_set.applications}
        result = recruit_for_intent(
            constellation, activation, pack_lookup=pack_lookup)
        recruited = [d for d in result["dispositions"] if d["disposition"] == "RECRUIT"]
        self.assertGreaterEqual(len(recruited), 1)


if __name__ == "__main__":
    unittest.main()
