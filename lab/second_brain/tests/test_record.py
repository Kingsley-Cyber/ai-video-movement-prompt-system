from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src import record
from lab.second_brain.src.record import append_run, seal_flight
from lab.second_brain.src.validate import ValidationFailure, read_jsonl, sha256_value
from lab.second_brain.tests.helpers import concept, make_root

HASH = "sha256:" + "0" * 64


class RecordTests(unittest.TestCase):
    def test_append_only_hash_chain_and_duplicate_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            alpha = concept("c_alpha", "alpha")
            root = make_root(Path(directory), [alpha])
            flight = seal_flight(
                {
                    "id": "flight_test",
                    "intent_id": None,
                    "intent_class": "test",
                    "arms": [{"id": "a", "paradigm": "test"}],
                    "concept_ids": ["c_alpha"],
                    "provider": "fixture",
                    "model_version": "fixture-1",
                    "seed": 7,
                    "compiler_settings": {"version": "test-1"},
                    "sealed_at": "2026-07-30T00:00:00Z",
                    "legacy": None,
                },
                root,
            )
            run = {
                "id": "r_test",
                "flight_id": flight["id"],
                "flight_hash": flight["flight_hash"],
                "intent_id": None,
                "intent_class": "test",
                "arm": "a",
                "paradigm": "test",
                "concept_ids": ["c_alpha"],
                "concept_content_hashes": {"c_alpha": sha256_value(alpha)},
                "provider": "fixture",
                "model_version": "fixture-1",
                "seed": 7,
                "compiled_prompt_hash": HASH,
                "compiler_version": "test-1",
                "repository_commit": "fixture",
                "output_artifact_hash": HASH,
                "metrics": {"score": 5},
                "verdict": "keep",
                "recorded_at": "2026-07-30T00:00:01Z",
                "legacy": None,
            }
            stored = append_run(run, root)
            self.assertTrue(stored["record_hash"].startswith("sha256:"))
            with self.assertRaises(ValidationFailure):
                append_run(run, root)
            mismatch = {**run, "id": "r_mismatch", "provider": "other"}
            with self.assertRaises(ValidationFailure):
                append_run(mismatch, root)
            self.assertEqual(len(read_jsonl(root / "lab/second_brain/immutable/runs.jsonl")), 1)
            self.assertFalse(hasattr(record, "update_record"))
            self.assertFalse(hasattr(record, "delete_record"))


if __name__ == "__main__":
    unittest.main()
