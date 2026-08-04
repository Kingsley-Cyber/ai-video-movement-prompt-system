from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.intent import build_intent_context
from lab.second_brain.src.pegasus import execute_asset_job, run_analysis_cascade
from lab.second_brain.src.record import append_measurement_observation
from lab.second_brain.src.validate import (
    REPO_ROOT,
    ValidationFailure,
    read_jsonl,
    sha256_value,
)
from lab.second_brain.tests.helpers import concept, make_root
from lab.second_brain.tests.test_twelvelabs import FakeClient


def score_asset() -> dict[str, str]:
    return {
        "asset_id": "asset_device",
        "role": "product_reference",
        "content_hash": "sha256:" + "a" * 64,
        "rights_basis": "owner_authorized_test_fixture",
    }


class PegasusCascadeTests(unittest.TestCase):
    def test_authorized_source_runs_full_cascade_reverse_compile_and_append_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [concept("c_communication_graph", "communication graph")],
            )
            shutil.copy2(
                REPO_ROOT / "lab/second_brain/curated/mappings.jsonl",
                root / "lab/second_brain/curated/mappings.jsonl",
            )
            media = root / "work/source.mp4"
            media.parent.mkdir(parents=True)
            media.write_bytes(b"authorized-video-fixture")
            source_hash = hashlib.sha256(media.read_bytes()).hexdigest()
            uploaded = execute_asset_job(
                {
                    "schema": "cpcs.twelvelabs_asset_job/1.0",
                    "job_id": "tl_asset_fixture_001",
                    "media_type": "video",
                    "source": {"file_path": str(media), "sha256": source_hash},
                    "knowledge_store_id": None,
                    "rights_scope": "original",
                    "created_at": "2026-07-30T00:00:00Z",
                },
                root,
                client=FakeClient(),
            )
            self.assertEqual(uploaded["asset"]["id"], "asset_fixture")
            measurement = append_measurement_observation(
                {
                    "id": "measurement_obs_fixture_001",
                    "measurement_job_id": "pose_job_" + "1" * 24,
                    "measurement_batch_id": "measurement_batch_" + "2" * 24,
                    "source_asset_ref": "asset_fixture",
                    "source_sha256": source_hash,
                    "tool": "fixture-contact-detector",
                    "model_version": "1.0",
                    "model_sha256": "3" * 64,
                    "parameters_hash": "sha256:" + "4" * 64,
                    "interval": {"start_s": 1.0, "end_s": 2.0},
                    "claim": {"label": "not_product", "contact": False},
                    "concept_ids": ["c_communication_graph"],
                    "candidate_concepts": [],
                    "evidence_class": "detected",
                    "confidence": 0.8,
                    "created_at": "2026-07-30T00:00:00Z",
                },
                root,
            )
            cascade = {
                "schema": "cpcs.video_analysis_cascade/1.0",
                "cascade_id": "tl_cascade_fixture_001",
                "source": {
                    "source_id": "source_fixture",
                    "asset_ref": "asset_fixture",
                    "asset_job_id": "tl_asset_fixture_001",
                    "local_path": str(media),
                    "sha256": source_hash,
                    "rights_scope": "original",
                },
                "authorized_interval": {"start_s": 0.0, "end_s": 8.0},
                "source_map_profile": "pegasus.source_map/1.0",
                "segment_profile": "pegasus.shot_scene/1.0",
                "deep_analysis_profiles": [
                    "pegasus.performance/1.0",
                    "pegasus.camera_edit/1.0",
                ],
                "candidate_concepts": ["c_communication_graph"],
                "measurement_observation_ids": [measurement["id"]],
                "created_at": "2026-07-30T00:00:00Z",
            }

            def probe(path: Path, *, expected_sha256: str) -> dict:
                self.assertEqual(path, media)
                self.assertEqual(expected_sha256, source_hash)
                return {
                    "duration_s": 8.0,
                    "start_time_s": 0.0,
                    "width": 1920,
                    "height": 1080,
                    "frame_rate": 24.0,
                    "probe_hash": sha256_value({"fixture": "ffprobe"}),
                }

            intent_context = build_intent_context(
                "Show how this device works in a clear educational video"
            )
            first = run_analysis_cascade(
                cascade,
                root,
                client=FakeClient(),
                probe_fn=probe,
                intent_context=intent_context,
                score_assets=[score_asset()],
            )
            self.assertEqual(
                first["reverse_score"]["schema_version"],
                "cpcs.universal_score/1.0",
            )
            self.assertEqual(
                first["reverse_score"]["provider_realization"]["status"],
                "unassigned",
            )
            self.assertGreaterEqual(
                first["video_observation_graph"]["fusion_report"]["contradictions"],
                1,
            )
            self.assertEqual(
                len(
                    read_jsonl(
                        root / "lab/second_brain/immutable/pegasus_observations.jsonl"
                    )
                ),
                1,
            )
            mismatched = json.loads(json.dumps(cascade))
            mismatched["cascade_id"] = "tl_cascade_fixture_mismatch"
            mismatched["source"]["asset_ref"] = "asset_other"
            with self.assertRaisesRegex(ValidationFailure, "registration identity"):
                run_analysis_cascade(
                    mismatched,
                    root,
                    client=FakeClient(),
                    probe_fn=probe,
                    intent_context=intent_context,
                    score_assets=[score_asset()],
                )
            second = run_analysis_cascade(
                cascade,
                root,
                client=FakeClient(),
                probe_fn=probe,
                intent_context=intent_context,
                score_assets=[score_asset()],
            )
            self.assertEqual(
                second["video_observation_graph"]["graph_hash"],
                first["video_observation_graph"]["graph_hash"],
            )
            self.assertEqual(
                second["reverse_score"]["score_id"], first["reverse_score"]["score_id"]
            )
            self.assertEqual(
                len(
                    read_jsonl(
                        root / "lab/second_brain/immutable/pegasus_observations.jsonl"
                    )
                ),
                1,
            )


if __name__ == "__main__":
    unittest.main()
