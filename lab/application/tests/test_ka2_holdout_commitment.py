"""WP-4 — Holdout commitment integrity (does NOT read the answer key)."""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMITMENT_PATH = ROOT / "KA2_EVAL_HOLDOUT_COMMITMENT_v0.1.json"
INTENTS_PATH = ROOT / "KA2_EVAL_HOLDOUT_INTENTS_v0.1.json"
KEY_PATH = ROOT / "KA2_EVAL_HOLDOUT_ANSWER_KEY_v0.1.json"


class Ka2HoldoutCommitmentTests(unittest.TestCase):

    def test_commitment_file_exists(self):
        self.assertTrue(COMMITMENT_PATH.is_file())

    def test_commitment_schema_and_algorithm(self):
        c = json.loads(COMMITMENT_PATH.read_text())
        self.assertEqual(c["schema"], "cpcs.ka2.eval_holdout_commitment/0.1")
        self.assertEqual(c["commitment_algorithm"], "sha256")
        self.assertEqual(len(c["commitment"]), 64)

    def test_intents_file_exists_with_no_answer_labels(self):
        self.assertTrue(INTENTS_PATH.is_file())
        intents = json.loads(INTENTS_PATH.read_text())
        self.assertEqual(intents["schema"], "cpcs.ka2.eval_holdout_intents/0.1")
        for intent in intents["intents"]:
            for forbidden in ("expected_recruited_regions",
                              "expected_archived_regions",
                              "expected_coverage_gaps",
                              "expected_new_prerequisites"):
                self.assertNotIn(forbidden, intent,
                                 f"intent {intent.get('intent_id')} must not "
                                 f"expose {forbidden}")

    def test_answer_key_file_exists(self):
        self.assertTrue(KEY_PATH.is_file())

    def test_commitment_hash_matches_answer_key(self):
        c = json.loads(COMMITMENT_PATH.read_text())
        key = json.loads(KEY_PATH.read_text())
        canonical = json.dumps(key, sort_keys=True, separators=(",", ":")).encode()
        h = hashlib.sha256(canonical).hexdigest()
        self.assertEqual(c["commitment"], h,
                         "holdout commitment must match canonical JSON of answer key")

    def test_commitment_references_correct_key_file(self):
        c = json.loads(COMMITMENT_PATH.read_text())
        self.assertEqual(c["answer_key_file"],
                         "lab/application/KA2_EVAL_HOLDOUT_ANSWER_KEY_v0.1.json")

    def test_label_marks_precommitted(self):
        c = json.loads(COMMITMENT_PATH.read_text())
        self.assertIn("precommitted", c.get("label", ""))


if __name__ == "__main__":
    unittest.main()
