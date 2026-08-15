"""TC-1 typed knowledge coverage tests: dispositions, distinctions, constructors."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest import mock

from lab.application import reasoning_treatment as rt
from lab.application.reasoning_treatment import (
    FakeBackend,
    TreatmentAdapter,
    build_treatment_packet,
)
from lab.compiler import cpcs_typed
from lab.compiler.profiles import REPO_ROOT

OUT = Path(__file__).resolve().parents[1]

with open(OUT / "CPCS_TYPED_KNOWLEDGE_COVERAGE_LEDGER_v0.1.json") as f:
    LEDGER = json.load(f)

EXPECTED_DIMENSIONS = [
    "identity", "state", "geometry", "contact", "persistence", "visibility",
    "orientation", "trajectory", "timing", "causality", "ownership", "force",
    "support", "transition", "uncertainty", "measurement", "epistemics",
    "coordination", "continuity", "camera", "verification",
]
EXPECTED_CONDITION_TYPES = ["STATE", "RELATIONSHIP", "EVENT", "TRANSITION",
                            "PERSISTENCE", "NON_OCCURRENCE", "TEMPORAL_ORDER",
                            "CAUSAL_RESULT"]
EXPECTED_OBLIGATION_KINDS = ["STATE", "EVENT", "CONTROL", "CONSTRAINT",
                             "VERIFICATION", "EXPECTED_OUTCOME"]


def _ctl(**kw) -> dict:
    base = {"control_id": "ctl_test", "control_type": [], "target": "scene",
            "scope": "scene", "hardness": "SOFT", "source": "EVIDENCE_DERIVED",
            "source_requirement_ids": [], "supporting_evidence_ids": [],
            "protected_objectives": [], "prevented_failure_families": [],
            "control_semantics": {"statement": "s", "universal_type": "Rule"}}
    base.update(kw)
    return base


class TypedCoverageTests(unittest.TestCase):
    def test_reasoning_dimension_disposition_coverage(self):
        for name in EXPECTED_DIMENSIONS:
            key = f"DIM-{name.upper()}"
            self.assertIn(key, LEDGER["dimensions"], key)
            self.assertTrue(LEDGER["dimensions"][key], key)
            for disposition in LEDGER["dimensions"][key]:
                self.assertTrue(
                    disposition.startswith(("REPRESENTED", "VERIFICATION_ONLY",
                                            "EXPECTED_STATE_ONLY", "PROVIDER_ONLY",
                                            "METADATA_ONLY", "NOT_SCORE_RELEVANT",
                                            "UNRESOLVED_WITH_REASON")),
                    f"{key}: {disposition}")

    def test_condition_type_disposition_coverage(self):
        for ct in EXPECTED_CONDITION_TYPES:
            self.assertIn(ct, LEDGER["condition_types"], ct)

    def test_obligation_kind_disposition_coverage(self):
        for kind in EXPECTED_OBLIGATION_KINDS:
            self.assertIn(kind, LEDGER["obligation_kinds"], kind)

    def test_control_type_disposition_coverage(self):
        self.assertIn("CT-CONTACT-CONTRACT", LEDGER["control_types"])
        for ct, disposition in LEDGER["control_types"].items():
            self.assertTrue(
                disposition.startswith("REPRESENTED") or
                disposition.startswith("UNRESOLVED_WITH_REASON"), ct)

    # ---- deterministic structured admission -------------------------------
    def test_structured_mapping_deterministic_and_idempotent(self):
        packet = build_treatment_packet(
            treatment_id="t", source_intent_hash="h", query_mode="INITIAL_GENERATION",
            activated_requirements=[], mandatory_requirements=[],
            conditional_requirements=[], required_pathways={},
            objectives_at_risk=[], predicted_failure_families=[],
            retrieved_evidence=[{"atomic_record_id": "ev1", "provenance": {}}],
            proposed_obligations=[],
            proposed_controls=[_ctl(control_id="c1", control_type=["CT-CONTACT-CONTRACT"],
                                    hardness="HARD",
                                    source_requirement_ids=["REQ-1"],
                                    supporting_evidence_ids=["ev1"])],
            verification_obligations=[], unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="a", retrieval_runtime_freeze_identity="r")
        t1 = TreatmentAdapter(REPO_ROOT).translate(packet)
        t2 = TreatmentAdapter(REPO_ROOT).translate(packet)
        self.assertEqual(t1.structured_objects, t2.structured_objects)
        self.assertEqual(len(t1.structured_objects), 1)
        obj = t1.structured_objects[0]
        self.assertEqual(obj["target"], "interactions[]")
        self.assertEqual(obj["schema"], "cpcs.interaction/1.0")
        self.assertEqual(obj["value"]["lineage"]["requirement_ids"], ["REQ-1"])
        self.assertEqual(obj["value"]["lineage"]["evidence_ids"], ["ev1"])
        self.assertEqual(obj["value"]["lineage"]["hardness"], "HARD")

    def test_hard_control_typed_disposition(self):
        control = _ctl(control_id="h1", control_type=["CT-POSITIVE-INVARIANTS"],
                       hardness="HARD")
        path_id, entry = cpcs_typed.map_control(control)
        self.assertEqual(path_id, "cpcs.continuity.invariant")
        self.assertEqual(entry["semantic_kind"], "INVARIANT")

    # ---- the twelve protected distinctions --------------------------------
    def test_distinction_contact_persistence_vs_identity(self):
        self.assertNotEqual(
            cpcs_typed.REGISTRY["cpcs.interaction.contact"]["semantic_family"],
            cpcs_typed.REGISTRY["cpcs.continuity.invariant"]["semantic_family"])
        self.assertIn("contact_as_global_scalar",
                      cpcs_typed.REGISTRY["cpcs.interaction.contact"]["forbidden_coercions"])

    def test_distinction_possession_vs_contact(self):
        p = cpcs_typed.REGISTRY["cpcs.entity_state.possession"]
        c = cpcs_typed.REGISTRY["cpcs.interaction.contact"]
        self.assertNotEqual(p["semantic_family"], c["semantic_family"])

    def test_distinction_ownership_vs_possession(self):
        self.assertIn("possession_collapse",
                      cpcs_typed.REGISTRY["cpcs.entity_state.ownership"]["forbidden_coercions"])

    def test_distinction_effort_vs_force(self):
        e = cpcs_typed.REGISTRY["cpcs.performance.effort"]
        self.assertIn("effort_as_force", e["forbidden_coercions"])
        self.assertNotIn("cpcs.performance.effort", cpcs_typed.CONTROL_TYPE_TO_PATH.get("Force", ""))

    def test_distinction_force_vs_momentum(self):
        self.assertNotIn("momentum",
                         cpcs_typed.REGISTRY["cpcs.interaction.contact"]["semantic_family"])

    def test_distinction_temporal_order_vs_causality(self):
        t = cpcs_typed.REGISTRY["cpcs.continuity.temporal_relation"]
        c = cpcs_typed.REGISTRY["cpcs.continuity.causal_edge"]
        self.assertNotEqual(t["semantic_family"], c["semantic_family"])
        self.assertIn("chronology_as_causality", t["forbidden_coercions"])
        self.assertIn("causality_as_chronology", c["forbidden_coercions"])

    def test_distinction_visibility_vs_state_persistence(self):
        v = cpcs_typed.REGISTRY["cpcs.entity_state.visibility"]
        self.assertIn("visibility_as_persistence", v["forbidden_coercions"])

    def test_distinction_identity_vs_physics_continuity(self):
        self.assertIn("identity_as_physics",
                      cpcs_typed.REGISTRY["cpcs.continuity.invariant"]["forbidden_coercions"])

    def test_distinction_expected_vs_observed(self):
        packet = build_treatment_packet(
            treatment_id="t", source_intent_hash="h", query_mode="INITIAL_GENERATION",
            activated_requirements=[], mandatory_requirements=[],
            conditional_requirements=[], required_pathways={},
            objectives_at_risk=[], predicted_failure_families=[],
            retrieved_evidence=[], proposed_obligations=[],
            proposed_controls=[], verification_obligations=[], unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="a", retrieval_runtime_freeze_identity="r")
        self.assertNotIn("observed", packet)
        self.assertIn("verification_obligations", packet)

    def test_distinction_verification_vs_generation_control(self):
        self.assertEqual(
            cpcs_typed.REGISTRY["cpcs.continuity.invariant"]["semantic_kind"],
            "INVARIANT")
        self.assertNotIn("cpcs.expected_state", cpcs_typed.CONTROL_TYPE_TO_PATH)

    def test_distinction_provider_carrier_vs_canonical_control(self):
        for entry in cpcs_typed.REGISTRY.values():
            self.assertTrue(entry["provider_neutral"])
            self.assertNotIn("provider", entry["canonical_target"].lower())

    def test_distinction_confidence_vs_scene_state(self):
        self.assertNotIn("confidence",
                         cpcs_typed.REGISTRY["cpcs.entity_state.identity"]["value_schema"])

    # ---- D4 + selectivity ------------------------------------------------
    def test_d4_still_rejects_prose_only(self):
        packet = build_treatment_packet(
            treatment_id="t", source_intent_hash="h", query_mode="INITIAL_GENERATION",
            activated_requirements=[], mandatory_requirements=[],
            conditional_requirements=[], required_pathways={},
            objectives_at_risk=[], predicted_failure_families=[],
            retrieved_evidence=[{"atomic_record_id": "evP", "provenance": {}}],
            proposed_obligations=[],
            proposed_controls=[_ctl(control_id="prose1", control_type=["PROSE_ONLY"],
                                    control_semantics={"statement": "wrist contact persists",
                                                       "universal_type": "Rule"})],
            verification_obligations=[], unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="a", retrieval_runtime_freeze_identity="r")
        translation = TreatmentAdapter(REPO_ROOT).translate(packet)
        self.assertEqual(translation.structured_objects, [])
        self.assertTrue(any(m["control_id"] == "prose1"
                            for m in translation.unsupported_mappings))

    def test_trivial_selectivity_preserved(self):
        backend = FakeBackend()
        packet = backend.plan("A plain wide shot of an empty room for two seconds.",
                              {"intent": {}})
        translation = TreatmentAdapter(REPO_ROOT).translate(packet)
        self.assertEqual(translation.structured_objects, [])
        self.assertEqual(translation.overlays, [])


if __name__ == "__main__":
    unittest.main()
