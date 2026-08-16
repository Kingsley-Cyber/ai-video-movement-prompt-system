"""WP-2 — principle extraction + mechanism binding engine (hermetic)."""
from __future__ import annotations

import unittest

from jsonschema import Draft202012Validator

from lab.application.cpcs_deliberation import (
    FAKE_SNAPSHOT,
    DeliberationEngine,
)
from lab.application.cpcs_knowledge_application import (
    PACK_SCHEMA,
    build_principle_packs,
)
from lab.application.reasoning_treatment import (
    FakeBackend,
    build_treatment_packet,
)
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1]


def _packet_and_activation(intent_text):
    normalized_intent = {"intent": {"primary_domain": "action"}}
    engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
    activation, packet = engine.activate(intent_text, normalized_intent,
                                         observations=[])
    return packet, activation


def _packs(intent_text):
    packet, activation = _packet_and_activation(intent_text)
    return build_principle_packs(packet, FAKE_SNAPSHOT, activation)


class Ka1PrincipleEngine(unittest.TestCase):

    def test_combat_pack_has_contact_chain_and_mirrored_rotation_risk(self):
        packs = _packs("A fighter performs a hip toss.")
        contact_packs = [p for p in packs
                         if p.principle_family == "support_contact_chain"]
        self.assertTrue(contact_packs, "no support/contact-chain pack")
        self.assertTrue(any("mirrored_rotation" in p.failure_risk["risk_tokens"]
                            for p in contact_packs),
                        "combat pack missing mirrored-rotation risk token")

    def test_ecommerce_pack_has_identity_visibility_and_logo_risk(self):
        packs = _packs("A person unboxes a luxury watch.")
        self.assertTrue(any("identity_visibility" in p.mechanism for p in packs))
        self.assertTrue(any("logo_visibility_loss" in p.failure_risk["risk_tokens"]
                            for p in packs))
        combined = [p for p in packs
                    if "identity_visibility" in p.mechanism
                    and "logo_visibility_loss" in p.failure_risk["risk_tokens"]]
        self.assertTrue(combined,
                        "no pack binds identity-visibility mechanism + logo risk")

    def test_cooking_pack_has_cut_deformation_and_hand_safety(self):
        packs = _packs("A chef slices a tomato.")
        self.assertTrue(any("cut_deformation" in p.mechanism for p in packs))
        self.assertTrue(any("hand_safety" in p.failure_risk["risk_tokens"]
                            for p in packs))

    def test_determinism_two_runs_identical_hashes(self):
        first = _packs("A fighter performs a hip toss.")
        second = _packs("A fighter performs a hip toss.")
        self.assertEqual([p.pack_hash for p in first],
                         [p.pack_hash for p in second])

    def test_ordering_is_deterministic(self):
        packs = _packs("A fighter performs a hip toss.")
        keys = [(p.principle_family, tuple(p.lineage["requirement_ids"]), p.pack_id)
                for p in packs]
        self.assertEqual(keys, sorted(keys))

    def test_d4_evidence_ids_only_and_no_record_prose(self):
        hostile_prose = ("this is a long mined prose passage that must never "
                         "appear inside any pack")
        packet = build_treatment_packet(
            treatment_id="treatment_hostile", source_intent_hash="hostile",
            query_mode="INITIAL_GENERATION",
            activated_requirements=["REQ-CONTACT-1"],
            mandatory_requirements=["REQ-CONTACT-1"],
            conditional_requirements=[],
            required_pathways={"REQ-CONTACT-1": "covered"},
            objectives_at_risk=[],
            predicted_failure_families=["FF-CONTACT"],
            retrieved_evidence=[
                {"atomic_record_id": "ev_hostile_prose",
                 "supported_requirement_ids": ["REQ-CONTACT-1"],
                 "failure_family_ids": ["FF-CONTACT"],
                 "objective_ids": [],
                 "universal_type": "FailureMode",
                 "epistemic_status": "known",
                 "risk_tokens": ["mirrored_rotation"],
                 "description": hostile_prose},
            ],
            proposed_obligations=[], proposed_controls=[],
            verification_obligations=[], unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="x", retrieval_runtime_freeze_identity="y",
        )
        activation = {"packet_id": "kap_hostile",
                      "activated_domains": ["contact"],
                      "activated_triggers": [], "candidate_objectives": []}
        packs = build_principle_packs(packet, FAKE_SNAPSHOT, activation)
        self.assertTrue(packs)
        for pack in packs:
            self.assertEqual(pack.evidence_ids, ["ev_hostile_prose"])
            blob = json.dumps(pack.to_dict())
            self.assertNotIn("mined prose passage", blob)
            self.assertNotIn(hostile_prose, blob)
            for source in pack.source_records:
                self.assertEqual(source["atomic_record_id"], "ev_hostile_prose")
                self.assertNotIn("description", source)

    def test_packs_validate_against_schema(self):
        schema = json.loads(
            (OUT / "CPCS_PRINCIPLE_PACK_SCHEMA_v0.1.json").read_text())
        validator = Draft202012Validator(schema)
        for intent in ("A fighter performs a hip toss.",
                       "A person unboxes a luxury watch.",
                       "A chef slices a tomato."):
            for pack in _packs(intent):
                problems = list(validator.iter_errors(pack.to_dict()))
                self.assertEqual(problems, [],
                                 f"{intent}: {pack.pack_id}: {problems}")

    def test_intent_application_uses_structured_activation_tags(self):
        packs = _packs("A fighter performs a hip toss.")
        for pack in packs:
            app = pack.intent_application
            self.assertIsInstance(app["domain_tags"], list)
            self.assertIsInstance(app["trigger_ids"], list)
            for tag in app["domain_tags"] + app["trigger_ids"]:
                self.assertFalse(" " in tag, "intent tags must be structured")


if __name__ == "__main__":
    unittest.main()
