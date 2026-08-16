"""WP-3 — RepresentationDecision engine (hermetic)."""
from __future__ import annotations

import unittest

from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
from lab.application.cpcs_knowledge_application import (
    NEVER_CONTROL_UNIVERSAL_TYPES,
    PrinciplePack,
    build_principle_packs,
    decide_representation,
)
from lab.application.reasoning_treatment import FakeBackend
from lab.compiler import cpcs_typed

DECISIONS = {"CONTROL", "VERIFICATION", "PLANNING", "NON_EXECUTABLE", "COMPOSITE"}


def _packs(intent_text):
    engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
    activation, packet = engine.activate(
        intent_text, {"intent": {"primary_domain": "action"}}, observations=[])
    return build_principle_packs(packet, FAKE_SNAPSHOT, activation), activation


def _decisions(intent_text):
    packs, activation = _packs(intent_text)
    return [decide_representation(p, activation, FAKE_SNAPSHOT) for p in packs]


def _theory_pack() -> PrinciplePack:
    return PrinciplePack(
        pack_id="pack_" + "0" * 20,
        pack_hash="0" * 64,
        principle_family="conceptual_foundation",
        principle="template",
        mechanism="mechanism: none",
        failure_risk={"failure_family_ids": [], "risk_tokens": [],
                      "risk_statement": "risk: none"},
        evidence_ids=["ev_theory_001"],
        source_records=[{"atomic_record_id": "ev_theory_001",
                         "universal_type": "Concept",
                         "epistemic_status": "known"}],
        intent_application={"domain_tags": ["combat"],
                            "creative_goal_tags": [],
                            "trigger_ids": [],
                            "objective_ids": []},
        lineage={"requirement_ids": ["REQ-CONTACT-1"],
                 "treatment_packet_hash": "x",
                 "activation_packet_id": "y",
                 "control_types": [],
                 "verification_obligation_ids": [],
                 "contradiction_ids": []},
    )


class Ka1RepresentationEngine(unittest.TestCase):

    def test_combat_pack_is_composite(self):
        for decision in _decisions("A fighter performs a hip toss."):
            if decision.decision != "COMPOSITE":
                continue
            self.assertEqual(decision.target_family, "cpcs.interaction.contact")
            self.assertEqual(decision.authority, "CPCS_HARD_REQUIREMENT")
            break
        else:
            self.fail("no COMPOSITE decision for the combat fixture")

    def test_ecommerce_identity_pack_is_control(self):
        packs, activation = _packs("A person unboxes a luxury watch.")
        identity_packs = [p for p in packs
                          if p.principle_family == "grounded_principle"]
        self.assertTrue(identity_packs)
        decisions = [decide_representation(p, activation, FAKE_SNAPSHOT)
                     for p in identity_packs]
        for decision in decisions:
            self.assertEqual(decision.decision, "CONTROL")
            self.assertIn(decision.target_family,
                          ("cpcs.entity_state.identity",
                           "cpcs.continuity.invariant"))

    def test_pure_theory_pack_never_control(self):
        decision = decide_representation(_theory_pack(), {"packet_id": "kap"},
                                         FAKE_SNAPSHOT)
        self.assertIn(decision.decision, ("PLANNING", "NON_EXECUTABLE"))
        self.assertNotEqual(decision.decision, "CONTROL")

    def test_never_control_policy_covers_tc2_ledger(self):
        for universal_type in sorted(NEVER_CONTROL_UNIVERSAL_TYPES):
            pack = _theory_pack()
            pack.source_records[0]["universal_type"] = universal_type
            decision = decide_representation(pack, {"packet_id": "kap"},
                                             FAKE_SNAPSHOT)
            self.assertNotEqual(
                decision.decision, "CONTROL",
                f"{universal_type} coerced into CONTROL")
            self.assertIn(decision.decision, DECISIONS)

    def test_verification_decision_creates_no_generation_target(self):
        pack = _theory_pack()
        pack.source_records[0]["universal_type"] = "Metric"
        pack.lineage["control_types"] = []
        pack.lineage["verification_obligation_ids"] = ["verify_001"]
        decision = decide_representation(pack, {"packet_id": "kap"}, FAKE_SNAPSHOT)
        self.assertEqual(decision.decision, "VERIFICATION")
        self.assertIsNone(decision.target_family)
        self.assertIsNone(decision.verification_counterpart)

    def test_forbidden_coercions_copied_from_registry(self):
        for decision in _decisions("A fighter performs a hip toss."):
            if decision.target_family == "cpcs.interaction.contact":
                self.assertIn("flat_text", decision.forbidden_coercions)
                self.assertEqual(decision.verification_counterpart,
                                 "cpcs.expected_state.contact")
                break
        else:
            self.fail("no decision targeting the contact family")

    def test_decision_hash_deterministic_and_stable(self):
        packs, activation = _packs("A fighter performs a hip toss.")
        for pack in packs:
            first = decide_representation(pack, activation, FAKE_SNAPSHOT)
            second = decide_representation(pack, activation, FAKE_SNAPSHOT)
            self.assertEqual(first.decision_hash, second.decision_hash)
            self.assertEqual(len(first.decision_hash), 64)

    def test_decisions_use_frozen_decision_vocabulary(self):
        for decision in _decisions("A chef slices a tomato."):
            self.assertIn(decision.decision, DECISIONS)
            self.assertIn(decision.authority, (
                "USER_EXPLICIT", "USER_CORRECTION", "CPCS_HARD_REQUIREMENT",
                "CPCS_SAFE_INFERENCE", "CPCS_GROUNDED_RECOMMENDATION",
                "EXISTING_BASELINE_DEFAULT", "LEAVE_UNSPECIFIED"))


if __name__ == "__main__":
    unittest.main()
