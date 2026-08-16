"""WP-5 — TreatmentAdapter bridge integration (hermetic)."""
from __future__ import annotations

import re
import unittest

from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
from lab.application.reasoning_treatment import (
    FakeBackend,
    TreatmentAdapter,
    build_treatment_packet,
)
from lab.compiler.profiles import REPO_ROOT

_METRIC_RE = re.compile(r"^metric_[A-Za-z0-9._-]+$")


def _translate(intent_text):
    engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
    activation, packet = engine.activate(
        intent_text, {"intent": {"primary_domain": "action"}}, observations=[])
    translation = TreatmentAdapter(REPO_ROOT).translate(
        packet, snapshot=FAKE_SNAPSHOT, activation=activation)
    return translation, packet, activation


def _translate_packet(packet, activation):
    return TreatmentAdapter(REPO_ROOT).translate(
        packet, snapshot=FAKE_SNAPSHOT, activation=activation)


class Ka1Adapter(unittest.TestCase):

    def test_control_decision_reaches_structured_objects_with_lineage(self):
        translation, _, _ = _translate("A person unboxes a luxury watch.")
        self.assertTrue(translation.structured_objects)
        found = False
        for obj in translation.structured_objects:
            if obj.get("target") in ("continuity.cpcs_invariants[]",):
                lineage = obj["value"].get("lineage", {})
                self.assertTrue(lineage.get("requirement_ids"))
                self.assertTrue(lineage.get("evidence_ids"))
                found = True
        self.assertTrue(found, "no CONTROL-routed structured object")

    def test_verification_decision_creates_schema_valid_entry(self):
        packet = build_treatment_packet(
            treatment_id="treatment_verify", source_intent_hash="verify",
            query_mode="INITIAL_GENERATION",
            activated_requirements=["REQ-CONTACT-1"],
            mandatory_requirements=["REQ-CONTACT-1"],
            conditional_requirements=[],
            required_pathways={"REQ-CONTACT-1": "covered"},
            objectives_at_risk=[],
            predicted_failure_families=[],
            retrieved_evidence=[
                {"atomic_record_id": "ev_metric_001",
                 "supported_requirement_ids": ["REQ-CONTACT-1"],
                 "failure_family_ids": [], "objective_ids": [],
                 "universal_type": "Metric", "epistemic_status": "known"},
            ],
            proposed_obligations=[], proposed_controls=[],
            verification_obligations=[
                {"obligation_id": "verify_metric_1",
                 "requirement_id": "REQ-CONTACT-1",
                 "method": "measured check", "observability": "measured",
                 "target_paths": [], "failure_family_ids": [],
                 "criticality": "important"},
            ],
            unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="x", retrieval_runtime_freeze_identity="y",
        )
        activation = {"packet_id": "kap_verify", "activated_domains": [],
                      "activated_triggers": [], "candidate_objectives": []}
        translation = _translate_packet(packet, activation)
        self.assertTrue(translation.verification_requirements)
        entry = translation.verification_requirements[-1]
        self.assertRegex(entry["metric_id"], _METRIC_RE)
        self.assertIsInstance(entry["target_paths"], list)
        self.assertTrue(entry["method"])
        self.assertIn(entry["observability"],
                      ("direct", "semantic", "measured", "human_review"))
        self.assertTrue(entry["source_profile"])

    def test_planning_and_non_executable_never_enter_controls(self):
        translation, _, _ = _translate("A fighter performs a hip toss.")
        guided_ids = {g["pack_id"] for g in translation.planning_guidance}
        material_ids = {m["pack_id"] for m in translation.reasoning_material}
        self.assertTrue(material_ids, "mechanism pack should be non-executable")
        routed_ids = guided_ids | material_ids
        for obj in translation.structured_objects:
            self.assertNotIn(obj["value"].get("lineage", {}).get("source_control_id"),
                             routed_ids)
        for overlay in translation.overlays:
            self.assertNotIn(overlay.get("overlay_id"), routed_ids)
        for control in translation.provider_neutral_controls:
            self.assertNotIn(control.get("control_id"), routed_ids)
        for requirement in translation.verification_requirements:
            self.assertNotIn(requirement.get("metric_id"), routed_ids)

    def test_application_set_attached(self):
        translation, packet, _ = _translate("A chef slices a tomato.")
        self.assertIsNotNone(translation.application_set)
        self.assertEqual(translation.application_set["schema"],
                         "cpcs.knowledge_application_set/0.1")
        self.assertTrue(translation.application_set["set_hash"])

    def test_d4_no_evidence_prose_in_translation_outputs(self):
        hostile = ("this unique hostile prose must never appear in any "
                   "translation output field")
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
                {"atomic_record_id": "ev_hostile",
                 "supported_requirement_ids": ["REQ-CONTACT-1"],
                 "failure_family_ids": ["FF-CONTACT"], "objective_ids": [],
                 "universal_type": "FailureMode", "epistemic_status": "known",
                 "risk_tokens": ["mirrored_rotation"],
                 "description": hostile},
            ],
            proposed_obligations=[], proposed_controls=[],
            verification_obligations=[],
            unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="x", retrieval_runtime_freeze_identity="y",
        )
        activation = {"packet_id": "kap_hostile", "activated_domains": [],
                      "activated_triggers": [], "candidate_objectives": []}
        translation = _translate_packet(packet, activation)
        import json
        outputs = (
            translation.overlays, translation.structured_objects,
            translation.verification_requirements,
            translation.provider_neutral_controls,
            translation.planning_guidance, translation.reasoning_material,
            translation.warnings, translation.unsupported_mappings,
        )
        for output in outputs:
            self.assertNotIn("unique hostile prose", json.dumps(output))

    def test_existing_call_shape_unchanged_without_bridge(self):
        engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
        _, packet = engine.activate(
            "A fighter performs a hip toss.",
            {"intent": {"primary_domain": "action"}}, observations=[])
        translation = TreatmentAdapter(REPO_ROOT).translate(packet)
        self.assertIsNone(translation.application_set)
        self.assertEqual(translation.planning_guidance, [])
        self.assertEqual(translation.reasoning_material, [])


if __name__ == "__main__":
    unittest.main()
