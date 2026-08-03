from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.pegasus import ingest_response
from lab.second_brain.src.validate import REPO_ROOT, ValidationFailure, read_jsonl
from lab.second_brain.tests.helpers import concept, make_root


class PegasusTests(unittest.TestCase):
    def test_semantic_observation_is_typed_and_proposals_stay_staging(self) -> None:
        fixture = json.loads(
            (REPO_ROOT / "lab/second_brain/tests/fixtures/pegasus_response.json").read_text()
        )
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [concept("c_communication_graph", "communication graph"), concept("c_camera_keyframes", "camera")],
            )
            result = ingest_response(fixture, root)
            self.assertEqual(result["observation"]["evidence_class"], "interpreted")
            self.assertEqual(
                len(read_jsonl(root / "lab/second_brain/immutable/pegasus_observations.jsonl")),
                1,
            )
            self.assertEqual(
                len(read_jsonl(root / "lab/second_brain/staging/proposals.jsonl")),
                1,
            )
            self.assertIsNotNone(result["distillation_run"])
            self.assertEqual(result["distillation_run"]["summary"]["staged"], 1)
            self.assertEqual(
                len(
                    read_jsonl(
                        root
                        / "lab/second_brain/staging/distillation_runs.jsonl"
                    )
                ),
                1,
            )
            retry = ingest_response(fixture, root)
            self.assertEqual(
                retry["observation"]["record_hash"],
                result["observation"]["record_hash"],
            )
            self.assertEqual(
                len(
                    read_jsonl(
                        root
                        / "lab/second_brain/immutable/pegasus_observations.jsonl"
                    )
                ),
                1,
            )
            self.assertEqual(
                retry["distillation_run"]["id"],
                result["distillation_run"]["id"],
            )
            self.assertEqual(
                len(
                    read_jsonl(
                        root
                        / "lab/second_brain/staging/distillation_runs.jsonl"
                    )
                ),
                1,
            )
            collision = json.loads(json.dumps(fixture))
            collision["confidence"] = 0.5
            with self.assertRaises(ValidationFailure):
                ingest_response(collision, root)
            self.assertEqual(len(read_jsonl(root / "lab/second_brain/curated/edges.jsonl")), 0)
            measured = dict(fixture)
            measured["id"] = "pegasus_obs_fixture_measured"
            measured["evidence_class"] = "measured"
            with self.assertRaises(ValidationFailure):
                ingest_response(measured, root)
            untyped = json.loads(json.dumps(fixture))
            untyped["id"] = "pegasus_obs_fixture_untyped"
            untyped["entities"] = [{"id": "untyped"}]
            with self.assertRaises(ValidationFailure):
                ingest_response(untyped, root)
            missing_concept = json.loads(json.dumps(fixture))
            missing_concept["id"] = "pegasus_obs_fixture_missing_concept"
            missing_concept["candidate_concepts"] = ["c_not_curated"]
            with self.assertRaises(ValidationFailure):
                ingest_response(missing_concept, root)


if __name__ == "__main__":
    unittest.main()
