from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.validate import ValidationFailure, sha256_value
from lab.second_brain.src.video_observation import (
    build_video_observation_graph,
    normalize_semantic_response,
    validate_video_observation_graph,
)
from lab.second_brain.tests.helpers import make_root
from lab.second_brain.tests.test_twelvelabs import semantic_payload


class VideoObservationTests(unittest.TestCase):
    def test_normalization_enforces_interval_and_sensitive_inference_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory))
            source = {
                "source_id": "source_fixture",
                "asset_ref": "asset_fixture",
                "sha256": "a" * 64,
                "rights_scope": "original",
            }
            observations = normalize_semantic_response(
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
            self.assertEqual(observations[0]["evidence_class"], "interpreted")
            unsafe = semantic_payload()
            unsafe["entities"][0]["description"] = "A medical diagnosis is visible."
            with self.assertRaises(ValidationFailure):
                normalize_semantic_response(
                    unsafe,
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

    def test_fusion_preserves_contradictions_and_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory))
            source = {
                "source_id": "source_fixture",
                "asset_ref": "asset_fixture",
                "sha256": "a" * 64,
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
            measurement = copy.deepcopy(semantic[0])
            measurement["observation_id"] = "vog_obs_measurement_fixture"
            measurement["layer"] = "measurement"
            measurement["claim"]["label"] = "not_product"
            measurement["evidence_class"] = "detected"
            measurement["provenance"] = {
                "surface": "local_measurement",
                "model": "fixture-detector",
                "model_version": "1.0",
                "profile_id": "local.fixture-detector",
                "request_hash": "sha256:" + "d" * 64,
                "raw_response_hash": "sha256:" + "e" * 64,
            }
            surface_run = {
                "surface": "pegasus_analyze",
                "job_id": "tl_analyze_fixture",
                "request_hash": "sha256:" + "b" * 64,
                "raw_response_hash": "sha256:" + "c" * 64,
            }
            kwargs = {
                "source": source,
                "authorized_interval": {"start_s": 0.0, "end_s": 4.0},
                "media_metadata": {
                    "duration_s": 4.0,
                    "start_time_s": 0.0,
                    "width": 1920,
                    "height": 1080,
                    "frame_rate": 24.0,
                    "probe_hash": sha256_value({"fixture": True}),
                },
                "semantic_observations": semantic,
                "measurement_observations": [measurement],
                "surface_runs": [surface_run],
                "root": root,
            }
            first = build_video_observation_graph(**kwargs)
            second = build_video_observation_graph(**kwargs)
            self.assertEqual(
                json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True)
            )
            self.assertEqual(first["fusion_report"]["contradictions"], 1)
            self.assertFalse(first["fusion_report"]["confidence_averaging"])

            detached = copy.deepcopy(first)
            observation_node = next(
                node for node in detached["nodes"] if node["node_type"] == "observation"
            )
            observation_node["data"]["provenance"]["request_hash"] = (
                "sha256:" + "f" * 64
            )
            core = {
                key: value
                for key, value in detached.items()
                if key not in {"graph_id", "graph_hash"}
            }
            detached["graph_hash"] = sha256_value(core)
            detached["graph_id"] = (
                "vog_" + detached["graph_hash"][len("sha256:") :][:32]
            )
            with self.assertRaisesRegex(ValidationFailure, "detached"):
                validate_video_observation_graph(detached, root)


if __name__ == "__main__":
    unittest.main()
