from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.validate import sha256_value
from lab.second_brain.src.video_observation import (
    build_video_observation_graph,
    normalize_semantic_response,
)
from lab.second_brain.src.video_reasoning import (
    build_knowledge_comparison_lens,
    discover_video_research_gaps,
    promote_reviewed_video_bridge,
)
from lab.second_brain.tests.helpers import concept, make_root, write_rows
from lab.second_brain.tests.test_twelvelabs import semantic_payload


def _vog(root: Path, tag: str) -> dict:
    source = {
        "source_id": f"source_{tag}",
        "asset_ref": f"asset_{tag}",
        "sha256": sha256_value(tag).removeprefix("sha256:"),
        "rights_scope": "original",
    }
    semantic = normalize_semantic_response(
        semantic_payload(),
        source=source,
        authorized_interval={"start_s": 0.0, "end_s": 4.0},
        surface="pegasus_analyze",
        model="pegasus1.5",
        model_version="api-v1.3-sdk-1.3.1",
        profile_id="pegasus.source_map/1.0",
        request_hash="sha256:" + "b" * 64,
        raw_response_hash="sha256:" + "c" * 64,
        root=root,
    )
    return build_video_observation_graph(
        source=source,
        authorized_interval={"start_s": 0.0, "end_s": 4.0},
        media_metadata={
            "duration_s": 4.0,
            "start_time_s": 0.0,
            "width": 1920,
            "height": 1080,
            "frame_rate": 24.0,
            "probe_hash": sha256_value({"tag": tag}),
        },
        semantic_observations=semantic,
        measurement_observations=[],
        surface_runs=[
            {
                "surface": "pegasus_analyze",
                "job_id": f"tl_analyze_{tag}",
                "request_hash": "sha256:" + "b" * 64,
                "raw_response_hash": "sha256:" + "c" * 64,
            }
        ],
        root=root,
    )


class VideoReasoningTests(unittest.TestCase):
    def test_reviewed_bridge_gap_discovery_and_comparison_lens(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [concept("c_product_camera", "product camera framing", "camera")],
            )
            bridge_path = (
                root
                / "lab"
                / "second_brain"
                / "curated"
                / "video_concept_bridges.jsonl"
            )
            write_rows(bridge_path, [])
            reference = _vog(root, "reference")
            candidate = _vog(root, "candidate")
            observation_id = next(
                node["data"]["observation_id"]
                for node in reference["nodes"]
                if node["node_type"] == "observation"
            )
            review = {
                "status": "approved",
                "reviewer_id": "owner_fixture",
                "reviewed_at": "2026-08-07T00:00:00Z",
                "remarks": "The observation explicitly supports the camera concept.",
            }
            first = promote_reviewed_video_bridge(
                reference,
                observation_id=observation_id,
                concept_id="c_product_camera",
                relation="SUPPORTS_CONCEPT",
                review=review,
                root=root,
            )
            second = promote_reviewed_video_bridge(
                reference,
                observation_id=observation_id,
                concept_id="c_product_camera",
                relation="SUPPORTS_CONCEPT",
                review=review,
                root=root,
            )
            self.assertEqual(first, second)
            gaps = discover_video_research_gaps(
                reference,
                query="product camera framing",
                domain="camera",
                root=root,
            )
            self.assertEqual(len(gaps["reviewed_bridges"]), 1)
            lens = build_knowledge_comparison_lens(
                reference,
                candidate,
                query="compare product camera framing",
                domain="camera",
                root=root,
            )
            self.assertIn(first["id"], lens["reference"]["reviewed_bridge_ids"])
            self.assertEqual(lens["candidate"]["reviewed_bridge_ids"], [])


if __name__ == "__main__":
    unittest.main()
