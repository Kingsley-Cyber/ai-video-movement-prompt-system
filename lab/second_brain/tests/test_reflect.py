from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.record import (
    append_measurement_observation,
    append_run,
    seal_flight,
)
from lab.second_brain.src.reflect import rebuild
from lab.second_brain.src.validate import sha256_value
from lab.second_brain.tests.helpers import concept, make_root

HASH = "sha256:" + "1" * 64


class ReflectTests(unittest.TestCase):
    def test_isolated_comparison_and_rebuild_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            delta = concept("c_delta", "delta")
            shared = concept("c_shared", "shared")
            root = make_root(Path(directory), [delta, shared])
            flight = seal_flight(
                {
                    "id": "flight_ab",
                    "intent_id": None,
                    "intent_class": "product_reveal",
                    "arms": [
                        {"id": "a", "paradigm": "hybrid"},
                        {"id": "b", "paradigm": "hybrid"},
                    ],
                    "concept_ids": ["c_delta", "c_shared"],
                    "provider": "fixture",
                    "model_version": "fixture-1",
                    "seed": 7,
                    "compiler_settings": {"version": "compiler-1"},
                    "sealed_at": "2026-07-30T00:00:00Z",
                    "legacy": None,
                },
                root,
            )
            base = {
                "flight_id": flight["id"],
                "flight_hash": flight["flight_hash"],
                "intent_id": None,
                "intent_class": "product_reveal",
                "paradigm": "hybrid",
                "concept_content_hashes": {
                    "c_delta": sha256_value(delta),
                    "c_shared": sha256_value(shared),
                },
                "provider": "fixture",
                "model_version": "fixture-1",
                "seed": 7,
                "compiled_prompt_hash": HASH,
                "compiler_version": "compiler-1",
                "repository_commit": "fixture",
                "output_artifact_hash": HASH,
                "metrics": {"score": 5},
                "recorded_at": "2026-07-30T00:00:01Z",
                "legacy": None,
            }
            append_run(
                {
                    **base,
                    "id": "r_ab_a",
                    "arm": "a",
                    "concept_ids": ["c_delta", "c_shared"],
                    "controls": {"delta": 1, "base": 2},
                    "tested_delta": {"concept_id": "c_delta", "control_id": "delta", "value": 1},
                    "verdict": "keep",
                },
                root,
            )
            append_run(
                {
                    **base,
                    "id": "r_ab_b",
                    "arm": "b",
                    "concept_ids": ["c_delta", "c_shared"],
                    "controls": {"delta": 0, "base": 2},
                    "tested_delta": {"concept_id": "c_delta", "control_id": "delta", "value": 0},
                    "verdict": "reject",
                },
                root,
            )
            append_measurement_observation(
                {
                    "id": "measurement_obs_ab",
                    "source_asset_ref": "fixture://measurement",
                    "source_sha256": "a" * 64,
                    "tool": "fixture_pose",
                    "model_version": "fixture-1",
                    "interval": {"start_s": 0.0, "end_s": 1.0},
                    "claim": {"path_curvature": 0.5},
                    "concept_ids": ["c_shared"],
                    "candidate_concepts": [],
                    "evidence_class": "measured",
                    "confidence": 1.0,
                    "created_at": "2026-07-30T00:00:02Z",
                },
                root,
            )
            first = rebuild(root)
            stale = root / "lab/second_brain/derived/stale.json"
            stale.write_text("{}")
            second = rebuild(root)
            self.assertEqual(first, second)
            self.assertFalse(stale.exists())
            weights = __import__("json").loads(
                (root / "lab/second_brain/derived/weights.json").read_text()
            )
            promotes = [edge for edge in weights["edges"] if edge["type"] == "promotes"]
            self.assertEqual(len(promotes), 1)
            self.assertEqual(promotes[0]["evidence"], ["r_ab_a", "r_ab_b"])
            self.assertEqual(promotes[0]["model_version"], "fixture-1")
            associations = [
                edge
                for edge in weights["edges"]
                if edge["type"] == "associated_with_success"
            ]
            self.assertEqual(len(associations), 1)
            index = __import__("json").loads(
                (
                    root
                    / "lab/second_brain/derived/indexes/concept_to_evidence.json"
                ).read_text()
            )
            self.assertIn(
                "measurement_obs_ab",
                index["concept_to_evidence"]["c_shared"],
            )


if __name__ == "__main__":
    unittest.main()
