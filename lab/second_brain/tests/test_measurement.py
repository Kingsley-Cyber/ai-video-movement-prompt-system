from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lab.second_brain.src.measurement import (
    execute_pose_measurement_job,
    make_pose_measurement_job,
)
from lab.second_brain.src.record import append_measurement_batch
from lab.second_brain.src.validate import ValidationFailure, canonical_json_bytes, read_jsonl
from lab.second_brain.src.video_observation import normalize_measurement
from lab.second_brain.tests.helpers import make_root


def person(x: float) -> dict[str, tuple[float, float, float]]:
    return {
        "left_hip": (x - 0.02, 0.6, 0.95),
        "right_hip": (x + 0.02, 0.6, 0.96),
        "left_wrist": (x - 0.08, 0.4, 0.9),
    }


class MeasurementAdapterTests(unittest.TestCase):
    def _fixture(self, directory: str) -> tuple[Path, Path, Path, dict]:
        root = make_root(Path(directory))
        source = root / "work" / "source.mp4"
        model = root / "work" / "pose.task"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"authorized-pose-source")
        model.write_bytes(b"exact-pose-model")
        job = make_pose_measurement_job(
            source_id="source_pose_fixture",
            asset_ref="asset_pose_fixture",
            local_path=source,
            rights_scope="original",
            authorized_interval={"start_s": 0.0, "end_s": 1.5},
            model_path=model,
            model_version="pose-landmarker-full-fixture",
            created_at="2026-08-03T00:00:00Z",
            num_poses=2,
            keyframe_interval_s=0.5,
            root=root,
        )
        return root, source, model, job

    @staticmethod
    def _frames(path: Path, interval: dict, stride: int):
        del path, interval, stride
        return [(0, 0.0, "f0"), (1, 0.5, "f1"), (2, 1.0, "f2")]

    def test_pose_job_replays_deterministically_and_calls_detector_once_per_frame(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, _source, _model, job = self._fixture(directory)
            calls: list[int] = []

            def detector(frame: str, timestamp_ms: int):
                calls.append(timestamp_ms)
                if frame == "f1":
                    return [person(0.75), person(0.25)]
                return [person(0.25), person(0.75)]

            output = root / "work" / "pose-output"
            first = execute_pose_measurement_job(
                job,
                root,
                output_root=output,
                frame_reader=self._frames,
                detector=detector,
            )
            second = execute_pose_measurement_job(
                job,
                root,
                output_root=output,
                frame_reader=self._frames,
                detector=detector,
            )
            self.assertEqual(first, second)
            self.assertEqual(calls, [0, 500, 1000, 0, 500, 1000])
            batch = first["batch"]
            self.assertEqual(batch["summary"]["frames_processed"], 3)
            self.assertEqual(batch["summary"]["actors"], ["actor_A", "actor_B"])
            self.assertGreater(batch["summary"]["observation_count"], 0)
            self.assertTrue(
                all(row["evidence_class"] == "detected" for row in batch["observations"])
            )
            self.assertTrue(
                any(row["claim"]["joint"] == "root_hip_mid" for row in batch["observations"])
            )
            actor_a = next(
                row
                for row in batch["observations"]
                if row["claim"]["actor"] == "actor_A"
                and row["claim"]["joint"] == "left_hip"
            )
            self.assertLess(actor_a["claim"]["positions"][0]["x"], 0.5)
            self.assertTrue((output / "raw_frames.jsonl").is_file())

    def test_exact_source_and_model_bytes_are_checked_before_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, source, _model, job = self._fixture(directory)
            source.write_bytes(b"changed-source")
            output = root / "work" / "must-not-exist"
            with self.assertRaisesRegex(ValidationFailure, "source hash"):
                execute_pose_measurement_job(
                    job,
                    root,
                    output_root=output,
                    frame_reader=self._frames,
                    detector=lambda _frame, _time: [],
                )
            self.assertFalse(output.exists())

    def test_injected_runtime_must_be_complete_and_stays_failure_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, _source, _model, job = self._fixture(directory)
            output = root / "work" / "must-not-exist"
            with self.assertRaisesRegex(ValidationFailure, "injected together"):
                execute_pose_measurement_job(
                    job,
                    root,
                    output_root=output,
                    frame_reader=self._frames,
                )
            self.assertFalse(output.exists())
            invalid_output = root / "work" / "invalid-detector-output"
            with self.assertRaisesRegex(ValidationFailure, "non-finite"):
                execute_pose_measurement_job(
                    job,
                    root,
                    output_root=invalid_output,
                    frame_reader=self._frames,
                    detector=lambda _frame, _time: [
                        {"left_hip": (float("nan"), 0.5, 0.9)}
                    ],
                )
            self.assertFalse(invalid_output.exists())
            dependency_output = root / "work" / "missing-dependency-output"
            with mock.patch(
                "lab.second_brain.src.measurement._mediapipe_detector",
                side_effect=RuntimeError(
                    "local pose extraction requires the measurement extra"
                ),
            ), self.assertRaisesRegex(RuntimeError, "measurement extra"):
                execute_pose_measurement_job(
                    job,
                    root,
                    output_root=dependency_output,
                )
            self.assertFalse(dependency_output.exists())

    def test_reviewed_batch_appends_once_and_normalizes_for_vog(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, _source, _model, job = self._fixture(directory)
            result = execute_pose_measurement_job(
                job,
                root,
                output_root=root / "work" / "pose-output",
                frame_reader=self._frames,
                detector=lambda _frame, _time: [person(0.4)],
            )
            store = root / "lab" / "second_brain" / "immutable" / "measurement_observations.jsonl"
            self.assertEqual(read_jsonl(store), [])
            first = append_measurement_batch(result["batch"], root)
            second = append_measurement_batch(result["batch"], root)
            self.assertEqual(first["disposition"], "appended")
            self.assertEqual(second["disposition"], "already_present")
            self.assertEqual(len(read_jsonl(store)), len(first["records"]))
            normalized = normalize_measurement(
                first["records"][0],
                source={
                    "source_id": "source_pose_fixture",
                    "asset_ref": "asset_pose_fixture",
                    "sha256": job["source"]["sha256"],
                },
                authorized_interval={"start_s": 0.0, "end_s": 1.5},
                root=root,
            )
            self.assertEqual(normalized["layer"], "measurement")
            self.assertEqual(normalized["evidence_class"], "detected")
            self.assertEqual(normalized["subject_refs"], ["actor_A"])

    def test_batch_identity_and_concept_references_fail_before_append(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, _source, _model, job = self._fixture(directory)
            result = execute_pose_measurement_job(
                job,
                root,
                output_root=root / "work" / "pose-output",
                frame_reader=self._frames,
                detector=lambda _frame, _time: [person(0.4)],
            )
            changed = copy.deepcopy(result["batch"])
            changed["observations"][0]["concept_ids"] = ["c_missing"]
            store = root / "lab" / "second_brain" / "immutable" / "measurement_observations.jsonl"
            with self.assertRaisesRegex(ValidationFailure, "content identity"):
                append_measurement_batch(changed, root)
            self.assertEqual(read_jsonl(store), [])
            core = {key: value for key, value in changed.items() if key != "batch_id"}
            changed["batch_id"] = "measurement_batch_" + hashlib.sha256(
                canonical_json_bytes(core)
            ).hexdigest()[:24]
            with self.assertRaisesRegex(ValidationFailure, "missing curated concepts"):
                append_measurement_batch(changed, root)
            self.assertEqual(read_jsonl(store), [])


if __name__ == "__main__":
    unittest.main()
