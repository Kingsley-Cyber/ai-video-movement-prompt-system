from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.curate import promote_distillation_bundle
from lab.second_brain.src.pegasus import ingest_response
from lab.second_brain.src.validate import REPO_ROOT, ValidationFailure
from lab.second_brain.tests.helpers import concept, make_root


class EdgeCompatibilityPromotionTests(unittest.TestCase):
    def test_incompatible_video_edge_can_be_reviewed_but_not_promoted(self) -> None:
        fixture = json.loads(
            (
                REPO_ROOT
                / "lab/second_brain/tests/fixtures/pegasus_response.json"
            ).read_text()
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = make_root(
                Path(temporary),
                [
                    concept("c_communication_graph", "communication graph"),
                    concept("c_camera_keyframes", "camera"),
                ],
            )
            result = ingest_response(fixture, root)
            run = result["distillation_run"]
            self.assertEqual(run["summary"]["staged"], 1)
            proposal_id = run["proposal_ids"][0]
            review = {
                "source_verified": True,
                "source_locator_resolved": True,
                "duplicate_checked": True,
                "operationally_useful": True,
                "relationships_validated": True,
                "numeric_precision_supported": True,
                "reviewed_at": "2026-08-08T00:00:00Z",
                "notes": "The incompatible observation edge must be reclassified.",
            }
            with self.assertRaisesRegex(
                ValidationFailure, "requires reviewed typed reclassification"
            ):
                promote_distillation_bundle(
                    run["id"],
                    {proposal_id: "edge_900001"},
                    "owner-test",
                    review,
                    root,
                )


if __name__ == "__main__":
    unittest.main()
