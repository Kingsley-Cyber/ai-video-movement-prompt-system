"""WP-4 — KnowledgeApplicationSet assembly (hermetic)."""
from __future__ import annotations

import unittest

from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
from lab.application.cpcs_knowledge_application import (
    apply_knowledge,
    build_principle_packs,
    decide_representation,
)
from lab.application.reasoning_treatment import FakeBackend, build_treatment_packet


def _set_for(intent_text):
    engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
    activation, packet = engine.activate(
        intent_text, {"intent": {"primary_domain": "action"}}, observations=[])
    return apply_knowledge(packet, FAKE_SNAPSHOT, activation)


def _competition_packet():
    return build_treatment_packet(
        treatment_id="treatment_competition", source_intent_hash="comp",
        query_mode="INITIAL_GENERATION",
        activated_requirements=["REQ-CONTACT-1"],
        mandatory_requirements=["REQ-CONTACT-1"],
        conditional_requirements=[],
        required_pathways={"REQ-CONTACT-1": "covered"},
        objectives_at_risk=[],
        predicted_failure_families=["FF-CONTACT"],
        retrieved_evidence=[
            {"atomic_record_id": "ev_mech_a",
             "supported_requirement_ids": ["REQ-CONTACT-1"],
             "failure_family_ids": [], "objective_ids": [],
             "universal_type": "Mechanism", "epistemic_status": "known",
             "mechanism_tokens": ["approach_a"]},
            {"atomic_record_id": "ev_mech_b",
             "supported_requirement_ids": ["REQ-CONTACT-1"],
             "failure_family_ids": [], "objective_ids": [],
             "universal_type": "Mechanism", "epistemic_status": "known",
             "mechanism_tokens": ["approach_b"]},
        ],
        proposed_obligations=[], proposed_controls=[],
        verification_obligations=[], unknowns=[],
        uncovered_mandatory_requirements=[],
        architecture_freeze_identity="x", retrieval_runtime_freeze_identity="y",
    )


class Ka1ApplicationSet(unittest.TestCase):

    def test_determinism_two_runs_identical_set_hash(self):
        first = _set_for("A fighter performs a hip toss.")
        second = _set_for("A fighter performs a hip toss.")
        self.assertEqual(first.set_hash, second.set_hash)
        self.assertEqual(first.applications, second.applications)

    def test_every_application_has_pack_and_decision_pairing(self):
        result = _set_for("A fighter performs a hip toss.")
        self.assertTrue(result.applications)
        for entry in result.applications:
            pack_id = entry["pack"]["pack_id"]
            decision_id = entry["decision"]["knowledge_id"]
            self.assertEqual(pack_id, decision_id)
            self.assertTrue(entry["pack"]["pack_hash"])
            self.assertTrue(entry["decision"]["decision_hash"])

    def test_ordering_stable_and_authority_consistent(self):
        result = _set_for("A fighter performs a hip toss.")
        ranks = [{"CPCS_HARD_REQUIREMENT": 5, "CPCS_SAFE_INFERENCE": 4,
                  "CPCS_GROUNDED_RECOMMENDATION": 3, "LEAVE_UNSPECIFIED": 1,
                  "USER_EXPLICIT": 7, "USER_CORRECTION": 6,
                  "EXISTING_BASELINE_DEFAULT": 2}[e["decision"]["authority"]]
                 for e in result.applications]
        self.assertEqual(ranks, sorted(ranks, reverse=True))

    def test_competition_groups_preserved_not_averaged(self):
        packet = _competition_packet()
        activation = {"packet_id": "kap_comp", "activated_domains": [],
                      "activated_triggers": [], "candidate_objectives": []}
        result = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
        competing = [e for e in result.applications
                     if e["competition_group"] is not None]
        self.assertEqual(len(competing), 2,
                         "two same-requirement mechanisms must compete")
        self.assertEqual(competing[0]["competition_group"],
                         competing[1]["competition_group"])
        mechanisms = {e["pack"]["mechanism"] for e in competing}
        self.assertGreater(len(mechanisms), 1, "alternatives must not be averaged")

    def test_no_competition_when_same_decision_and_mechanism(self):
        packet = build_treatment_packet(
            treatment_id="treatment_dup", source_intent_hash="dup",
            query_mode="INITIAL_GENERATION",
            activated_requirements=["REQ-CONTACT-1"],
            mandatory_requirements=["REQ-CONTACT-1"],
            conditional_requirements=[],
            required_pathways={"REQ-CONTACT-1": "covered"},
            objectives_at_risk=[],
            predicted_failure_families=["FF-CONTACT"],
            retrieved_evidence=[
                {"atomic_record_id": "ev_mech_a",
                 "supported_requirement_ids": ["REQ-CONTACT-1"],
                 "failure_family_ids": [], "objective_ids": [],
                 "universal_type": "Mechanism", "epistemic_status": "known",
                 "mechanism_tokens": ["approach_a"]},
                {"atomic_record_id": "ev_mech_a2",
                 "supported_requirement_ids": ["REQ-CONTACT-1"],
                 "failure_family_ids": [], "objective_ids": [],
                 "universal_type": "Mechanism", "epistemic_status": "known",
                 "mechanism_tokens": ["approach_a"]},
            ],
            proposed_obligations=[], proposed_controls=[],
            verification_obligations=[], unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="x",
            retrieval_runtime_freeze_identity="y",
        )
        activation = {"packet_id": "kap_dup", "activated_domains": [],
                      "activated_triggers": [], "candidate_objectives": []}
        result = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
        self.assertEqual(
            [e["competition_group"] for e in result.applications], [None, None])

    def test_unresolved_control_without_target_fails_closed(self):
        packet = build_treatment_packet(
            treatment_id="treatment_unresolved", source_intent_hash="unres",
            query_mode="INITIAL_GENERATION",
            activated_requirements=["REQ-CONTACT-1"],
            mandatory_requirements=["REQ-CONTACT-1"],
            conditional_requirements=[],
            required_pathways={"REQ-CONTACT-1": "covered"},
            objectives_at_risk=[],
            predicted_failure_families=[],
            retrieved_evidence=[
                {"atomic_record_id": "ev_odd",
                 "supported_requirement_ids": ["REQ-CONTACT-1"],
                 "failure_family_ids": [], "objective_ids": [],
                 "universal_type": "Principle", "epistemic_status": "known",
                 "mechanism_tokens": []},
            ],
            proposed_obligations=[], proposed_controls=[],
            verification_obligations=[], unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="x",
            retrieval_runtime_freeze_identity="y",
        )
        activation = {"packet_id": "kap_unres", "activated_domains": [],
                      "activated_triggers": [], "candidate_objectives": []}
        result = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
        self.assertEqual(len(result.applications), 0)
        self.assertEqual(len(result.unknowns), 1)
        self.assertIn("fail closed", result.unknowns[0]["reason"])

    def test_set_hash_changes_when_pack_changes(self):
        packet = _competition_packet()
        activation = {"packet_id": "kap_comp", "activated_domains": [],
                      "activated_triggers": [], "candidate_objectives": []}
        before = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
        manual = apply_knowledge(
            build_treatment_packet(
                treatment_id="treatment_competition", source_intent_hash="comp",
                query_mode="INITIAL_GENERATION",
                activated_requirements=["REQ-CONTACT-1"],
                mandatory_requirements=["REQ-CONTACT-1"],
                conditional_requirements=[],
                required_pathways={"REQ-CONTACT-1": "covered"},
                objectives_at_risk=[],
                predicted_failure_families=["FF-CONTACT"],
                retrieved_evidence=[
                    {"atomic_record_id": "ev_mech_a",
                     "supported_requirement_ids": ["REQ-CONTACT-1"],
                     "failure_family_ids": [], "objective_ids": [],
                     "universal_type": "Mechanism", "epistemic_status": "known",
                     "mechanism_tokens": ["approach_changed"]},
                    {"atomic_record_id": "ev_mech_b",
                     "supported_requirement_ids": ["REQ-CONTACT-1"],
                     "failure_family_ids": [], "objective_ids": [],
                     "universal_type": "Mechanism", "epistemic_status": "known",
                     "mechanism_tokens": ["approach_b"]},
                ],
                proposed_obligations=[], proposed_controls=[],
                verification_obligations=[], unknowns=[],
                uncovered_mandatory_requirements=[],
                architecture_freeze_identity="x",
                retrieval_runtime_freeze_identity="y",
            ),
            FAKE_SNAPSHOT, activation)
        self.assertNotEqual(before.set_hash, manual.set_hash,
                            "set_hash must change when pack content changes")

    def test_lineage_carries_packet_and_activation_identity(self):
        result = _set_for("A chef slices a tomato.")
        self.assertTrue(result.lineage["treatment_packet_hash"])
        self.assertEqual(result.lineage["activation_packet_id"], "kap_" +
                         result.lineage["activation_packet_id"][4:])
        self.assertIn("affordance_ledger_coverage", result.lineage)


if __name__ == "__main__":
    unittest.main()
