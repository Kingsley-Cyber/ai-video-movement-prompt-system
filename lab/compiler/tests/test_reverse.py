from __future__ import annotations

import hashlib
import unittest

from lab.compiler.provenance import canonical_json_bytes, sha256_value
from lab.compiler.reverse import overlay_from_vog, resolve_vog_score
from lab.compiler.score import validate_compiler_instance
from lab.second_brain.src.intent import build_intent_context
from lab.second_brain.src.validate import ValidationFailure


class ReverseCompilerTests(unittest.TestCase):
    def test_vog_projects_through_declared_fields_and_preserves_score_identity(self) -> None:
        observation = {
            "schema": "cpcs.normalized_video_observation/1.0",
            "observation_id": "vog_obs_reverse_fixture",
            "source_id": "source_fixture",
            "source_sha256": "a" * 64,
            "interval": {"start_s": 0.0, "end_s": 4.0},
            "subject_refs": [],
            "layer": "entity",
            "claim": {"label": "device", "description": "A device is visible."},
            "evidence_class": "interpreted",
            "confidence": 0.8,
            "alternatives": [],
            "provenance": {
                "surface": "pegasus_analyze",
                "model": "pegasus1.5",
                "model_version": "api-v1.3-sdk-1.3.1",
                "profile_id": "pegasus.source_map/1.0",
                "request_hash": "sha256:" + "b" * 64,
                "raw_response_hash": "sha256:" + "c" * 64,
            },
        }
        core = {
            "schema": "cpcs.video_observation_graph/1.0",
            "source": {
                "source_id": "source_fixture",
                "asset_ref": "asset_fixture",
                "sha256": "a" * 64,
                "rights_scope": "original",
            },
            "authorized_interval": {"start_s": 0.0, "end_s": 4.0},
            "media_metadata": {
                "duration_s": 4.0,
                "start_time_s": 0.0,
                "width": 1920,
                "height": 1080,
                "frame_rate": 24.0,
                "probe_hash": "sha256:" + "d" * 64,
            },
            "nodes": [
                {
                    "id": "vog_node_reverse_fixture",
                    "node_type": "observation",
                    "data": observation,
                },
                {
                    "id": "vog_node_source_fixture",
                    "node_type": "source",
                    "data": {
                        "source_id": "source_fixture",
                        "asset_ref": "asset_fixture",
                        "sha256": "a" * 64,
                        "rights_scope": "original",
                    },
                },
            ],
            "edges": [
                {
                    "id": "vog_edge_observed_000001",
                    "u": "vog_node_reverse_fixture",
                    "v": "vog_node_source_fixture",
                    "type": "OBSERVED_IN",
                }
            ],
            "contradictions": [],
            "fusion_report": {
                "semantic_observations": 1,
                "measurement_observations": 0,
                "support_links": 0,
                "contradictions": 0,
                "confidence_averaging": False,
            },
            "surface_runs": [
                {
                    "surface": "pegasus_analyze",
                    "job_id": "tl_analyze_reverse_fixture",
                    "request_hash": "sha256:" + "b" * 64,
                    "raw_response_hash": "sha256:" + "c" * 64,
                }
            ],
        }
        graph_hash = sha256_value(core)
        vog = {
            **core,
            "graph_id": "vog_" + graph_hash[len("sha256:") :][:32],
            "graph_hash": graph_hash,
        }
        overlay = overlay_from_vog(vog)
        self.assertEqual(set(overlay["values"]), {"entities"})
        score = resolve_vog_score(
            build_intent_context("Show how this device works in a clear educational video"),
            vog,
            assets=[
                {
                    "asset_id": "asset_device",
                    "role": "product_reference",
                    "content_hash": "sha256:" + "e" * 64,
                    "rights_basis": "owner_authorized_test_fixture",
                }
            ],
        )
        validate_compiler_instance("universal_score", score)
        score_without_id = {
            key: value for key, value in score.items() if key != "score_id"
        }
        expected = "score_" + hashlib.sha256(
            canonical_json_bytes(score_without_id)
        ).hexdigest()[:32]
        self.assertEqual(score["score_id"], expected)
        self.assertEqual(score["provider_realization"]["status"], "unassigned")
        vog["nodes"][0]["data"]["claim"]["label"] = "tampered"
        with self.assertRaisesRegex(ValidationFailure, "content identity"):
            overlay_from_vog(vog)


if __name__ == "__main__":
    unittest.main()
