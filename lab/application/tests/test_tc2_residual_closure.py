"""TC-2 residual-closure tests."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from lab.application.reasoning_treatment import (
    FakeBackend,
    TreatmentAdapter,
    build_treatment_packet,
)
from lab.compiler import cpcs_typed
from lab.compiler.profiles import REPO_ROOT

OUT = Path(__file__).resolve().parents[1]

with open(OUT / "CPCS_RESIDUAL_CLASSIFICATION_v0.1.json") as f:
    CLASSIFICATION = json.load(f)


def _ctl(**kw) -> dict:
    base = {"control_id": "ctl_t", "control_type": [], "target": "scene",
            "scope": "scene", "hardness": "SOFT", "source": "EVIDENCE_DERIVED",
            "source_requirement_ids": [], "supporting_evidence_ids": [],
            "protected_objectives": [], "prevented_failure_families": [],
            "control_semantics": {"statement": "s", "universal_type": "Rule"}}
    base.update(kw)
    return base


class TC2ResidualClosureTests(unittest.TestCase):
    def test_all_residual_mappings_classified(self):
        self.assertEqual(CLASSIFICATION["unresolved"], [])
        for row in CLASSIFICATION["rows"]:
            self.assertIn(row["disposition"], (
                "VERIFICATION_ONLY", "EXPECTED_STATE_ONLY", "EPISTEMIC_METADATA",
                "PROVENANCE_ONLY", "RESEARCH_GOVERNANCE", "PROVIDER_ONLY",
                "PLANNING_ONLY", "NON_EXECUTABLE_KNOWLEDGE",
                "DUPLICATE_SEMANTIC_ALREADY_REPRESENTED",
                "INSUFFICIENT_STRUCTURED_VALUE", "MISSING_EXISTING_REGISTRY_RULE",
                "MISSING_VALUE_SUBSCHEMA", "MISSING_STRUCTURED_CONSTRUCTOR",
                "MISSING_CANONICAL_SEMANTIC_FAMILY", "UPSTREAM_AMBIGUOUS",
                "UNRESOLVED"))

    def test_zero_unexplained_hard_residuals(self):
        for row in CLASSIFICATION["rows"]:
            self.assertNotEqual(row["hardness"], "HARD",
                                f"HARD residual unexplained: {row['control_id']}")

    def test_control_selection_rule_now_mapped(self):
        control = _ctl(control_id="rule1", control_type=["CONTROL_SELECTION_RULE"])
        path_id, entry = cpcs_typed.map_control(control)
        self.assertEqual(path_id, "cpcs.continuity.invariant")
        self.assertEqual(entry["semantic_kind"], "INVARIANT")

    def test_hard_or_soft_control_now_mapped(self):
        control = _ctl(control_id="c1", control_type=["HARD_OR_SOFT_CONTROL"],
                       hardness="HARD")
        path_id, _ = cpcs_typed.map_control(control)
        self.assertEqual(path_id, "cpcs.continuity.invariant")

    def test_duplicate_semantic_suppression(self):
        packet = build_treatment_packet(
            treatment_id="t", source_intent_hash="h", query_mode="INITIAL_GENERATION",
            activated_requirements=[], mandatory_requirements=[],
            conditional_requirements=[], required_pathways={},
            objectives_at_risk=[], predicted_failure_families=[],
            retrieved_evidence=[{"atomic_record_id": "ev1", "provenance": {}}],
            proposed_obligations=[],
            proposed_controls=[
                _ctl(control_id="a", control_type=["CT-CONTACT-CONTRACT"],
                     source_requirement_ids=["REQ-1"], supporting_evidence_ids=["ev1"]),
                _ctl(control_id="b", control_type=["CT-CONTACT-CONTRACT"],
                     source_requirement_ids=["REQ-1"], supporting_evidence_ids=["ev1"]),
            ],
            verification_obligations=[], unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="a", retrieval_runtime_freeze_identity="r")
        translation = TreatmentAdapter(REPO_ROOT).translate(packet)
        self.assertEqual(len(translation.structured_objects), 1)
        self.assertEqual(len(translation.duplicate_semantics), 1)
        self.assertEqual(translation.duplicate_semantics[0]["control_id"], "b")

    def test_value_subschema_enums_schema_valid(self):
        for key, values in cpcs_typed.SOURCE_VALUE_ENUMS.items():
            self.assertIsInstance(values, list)
            self.assertEqual(len(values), len(set(values)))
            self.assertTrue(all(isinstance(v, str) and v for v in values))

    def test_non_executable_residuals_are_vocabulary(self):
        for row in CLASSIFICATION["rows"]:
            if row["disposition"] == "NON_EXECUTABLE_KNOWLEDGE":
                self.assertIn(row["universal_type"],
                              ("Concept", "Schema", "Definition", "Table",
                               "Vocabulary", "Ontology", "Grammar", "JSONSchema"))

    def test_tc1_distinctions_still_hold(self):
        self.assertIn("effort_as_force",
                      cpcs_typed.REGISTRY["cpcs.performance.effort"]["forbidden_coercions"])
        self.assertIn("chronology_as_causality",
                      cpcs_typed.REGISTRY["cpcs.continuity.temporal_relation"]["forbidden_coercions"])
        self.assertIn("identity_as_physics",
                      cpcs_typed.REGISTRY["cpcs.continuity.invariant"]["forbidden_coercions"])


if __name__ == "__main__":
    unittest.main()
