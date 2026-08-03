from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src import record
from lab.second_brain.src.record import _append_verified_run, append_run, seal_flight
from lab.second_brain.src.validate import ValidationFailure, read_jsonl, sha256_value
from lab.second_brain.tests.helpers import (
    concept,
    controlled_lineage,
    finalize_evidence_run,
    make_root,
)

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
                    "arms": [
                        {"id": "a", "paradigm": "test", "tested_delta": None}
                    ],
                    "design": {
                        "classification": "bundled_observation",
                        "causal_claim_policy": "isolated_only",
                        "metric_ids": ["score"],
                        "outcome_concept_ids": [],
                    },
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
            lineage = controlled_lineage("record-test")
            run = finalize_evidence_run({
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
                "output_artifact_hash": lineage["artifact_sha256"],
                "metrics": {"score": 5},
                "controls": {"control_0000000000000001": True},
                "tested_delta": None,
                "verdict": "keep",
                "evidence_design": {
                    "classification": "bundled_observation",
                    "causal_eligibility": "ineligible_bundled",
                    "outcome_concept_ids": [],
                    "policy_version": "cpcs-controlled-evidence/1.0",
                },
                "evidence_lineage": lineage,
                "human_review": {
                    "review_id": "review_record_test",
                    "reviewer_id": "reviewer_fixture",
                    "verdict": "keep",
                    "rationale": "Fixture bundled-observation verdict.",
                    "reviewed_at": "2026-07-30T00:00:01Z",
                },
                "recorded_at": "2026-07-30T00:00:01Z",
                "legacy": None,
            })
            with self.assertRaisesRegex(
                ValidationFailure, "must enter through append_experiment_run"
            ):
                append_run(run, root)
            stored = _append_verified_run(run, root)
            self.assertTrue(stored["record_hash"].startswith("sha256:"))
            with self.assertRaises(ValidationFailure):
                _append_verified_run(run, root)
            mismatch = {**run, "provider": "other"}
            with self.assertRaises(ValidationFailure):
                _append_verified_run(mismatch, root)
            self.assertEqual(len(read_jsonl(root / "lab/second_brain/immutable/runs.jsonl")), 1)
            self.assertFalse(hasattr(record, "update_record"))
            self.assertFalse(hasattr(record, "delete_record"))


if __name__ == "__main__":
    unittest.main()
