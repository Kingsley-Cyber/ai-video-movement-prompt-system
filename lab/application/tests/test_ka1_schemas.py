"""WP-1 — KA-1 schema artifact tests (schemas + contracts, no engine logic)."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from lab.application.ka1_schemas_validate import (
    SAMPLE_PRINCIPLE_PACK,
    SAMPLE_REPRESENTATION_DECISION,
    SCHEMAS,
    validate_samples,
    validate_schemas,
)

OUT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = OUT / "CPCS_KNOWLEDGE_APPLICATION_CONTRACT_v0.1.json"

DECISION_ENUM = ["CONTROL", "VERIFICATION", "PLANNING", "NON_EXECUTABLE", "COMPOSITE"]
AUTHORITY_ORDER = [
    "USER_EXPLICIT", "USER_CORRECTION", "CPCS_HARD_REQUIREMENT",
    "CPCS_SAFE_INFERENCE", "CPCS_GROUNDED_RECOMMENDATION",
    "EXISTING_BASELINE_DEFAULT", "LEAVE_UNSPECIFIED",
]


class Ka1SchemaArtifacts(unittest.TestCase):

    def test_all_three_artifacts_parse(self):
        for path in list(SCHEMAS.values()) + [CONTRACT_PATH]:
            self.assertTrue(path.is_file(), f"missing artifact: {path}")
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertIsInstance(value, dict)

    def test_principle_pack_schema_validates(self):
        self.assertEqual(validate_schemas(), [])

    def test_representation_schema_validates(self):
        self.assertEqual(validate_samples(), [])

    def test_decision_enum_exhaustive(self):
        schema = json.loads(SCHEMAS["representation_decision"].read_text())
        self.assertEqual(
            schema["$defs"]["decisionEnum"]["enum"], DECISION_ENUM)

    def test_authority_subset_of_frozen_order(self):
        schema = json.loads(SCHEMAS["representation_decision"].read_text())
        enum = schema["$defs"]["authorityEnum"]["enum"]
        self.assertEqual(enum, AUTHORITY_ORDER)
        self.assertEqual(len(enum), len(set(enum)))

    def test_contract_authority_matches_frozen_order(self):
        contract = json.loads(CONTRACT_PATH.read_text())
        self.assertEqual(contract["authority_order"], AUTHORITY_ORDER)

    def test_contract_decision_rules_cover_decision_enum(self):
        contract = json.loads(CONTRACT_PATH.read_text())
        rules = " ".join(contract["affordance_mapping_rule"]["decision_rules"].values())
        for decision in DECISION_ENUM:
            self.assertIn(decision, rules.upper())

    def test_samples_validated_by_module(self):
        for name, sample in (
            ("principle_pack", SAMPLE_PRINCIPLE_PACK),
            ("representation_decision", SAMPLE_REPRESENTATION_DECISION),
        ):
            schema = json.loads(SCHEMAS[name].read_text())
            problems = list(Draft202012Validator(schema).iter_errors(sample))
            self.assertEqual(problems, [], f"{name} sample has schema errors")

    def test_invalid_decision_rejected(self):
        schema = json.loads(SCHEMAS["representation_decision"].read_text())
        bad = dict(SAMPLE_REPRESENTATION_DECISION)
        bad["decision"] = "HALLUCINATION"
        problems = list(Draft202012Validator(schema).iter_errors(bad))
        self.assertTrue(problems)

    def test_invalid_authority_rejected(self):
        schema = json.loads(SCHEMAS["representation_decision"].read_text())
        bad = dict(SAMPLE_REPRESENTATION_DECISION)
        bad["authority"] = "LLM_OPINION"
        problems = list(Draft202012Validator(schema).iter_errors(bad))
        self.assertTrue(problems)


if __name__ == "__main__":
    unittest.main()
