from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lab.application.service import (
    REQUEST_SCHEMA,
    authorization_request_hash,
    invoke,
    list_operations,
)
from lab.application.telemetry import TelemetrySink
from lab.compiler.provenance import sha256_value
from lab.runtime.journal import JobJournal
from lab.runtime.runner import RenderRunner
from lab.runtime.tests.test_runner import FakeAdapter
from lab.second_brain.src.intent import build_intent_context
from lab.second_brain.src.validate import REPO_ROOT
from lab.second_brain.tests.test_twelvelabs import FakeClient, analysis_job
from lab.verification.verify import make_assertion, make_evidence_source

from lab.application.tests.test_facade import authority_snapshot


def request(operation: str, arguments: dict) -> dict:
    return {
        "schema": REQUEST_SCHEMA,
        "operation": operation,
        "arguments": arguments,
    }


def authorize(operation: str, arguments: dict) -> dict:
    value = request(operation, arguments)
    value["authorization"] = {
        "schema": "cpcs.explicit_authorization/1.0",
        "authorization_id": "auth_runtime_surface_test",
        "authorized_by": "owner-test",
        "operation": operation,
        "request_hash": authorization_request_hash(operation, arguments),
        "reason": "exercise the exact bounded external operation",
    }
    return value


class ApplicationRuntimeSurfaceTests(unittest.TestCase):
    def _assets(self, text: str) -> list[dict]:
        routed = build_intent_context(text)
        return [
            {
                "asset_id": f"asset_required_{index}",
                "role": role,
                "content_hash": "sha256:" + "a" * 64,
                "rights_basis": "owner_authorized_test_fixture",
            }
            for index, role in enumerate(
                routed["normalized_intent"]["requirements"]["missing_inputs"]
            )
        ]

    @staticmethod
    def _evidence(
        score: dict,
        render_snapshot: dict,
    ) -> dict:
        result = render_snapshot["result"]
        artifact = result["artifacts"][0]
        controls = {
            row["path"]: row for row in score["provider_neutral_controls"]
        }
        sources = []
        assertions = []
        for index, requirement in enumerate(score["verification_requirements"]):
            for target_index, target_path in enumerate(requirement["target_paths"]):
                measurement = requirement["observability"] == "measured"
                source_id = f"vog_obs_app_{index}_{target_index}"
                claim = (
                    {
                        "metric_id": requirement["metric_id"],
                        "method": requirement["method"],
                        "target_path": target_path,
                        "visible_seconds": 4.0,
                        "total_seconds": 8.0,
                        "duty_cycle": 0.5,
                    }
                    if measurement
                    else {
                        "metric_id": requirement["metric_id"],
                        "target_path": target_path,
                        "method": requirement["method"],
                        "verdict": "pass",
                        "observed": controls[target_path]["value"],
                        "deviation": None,
                        "limitations": ["Fixture semantic assessment."],
                    }
                )
                record = {
                    "schema": "cpcs.normalized_video_observation/1.0",
                    "observation_id": source_id,
                    "source_id": artifact["artifact_id"],
                    "source_sha256": artifact["sha256"].removeprefix("sha256:"),
                    "interval": {"start_s": 0.0, "end_s": 8.0},
                    "subject_refs": [],
                    "layer": "measurement" if measurement else "marketing",
                    "claim": claim,
                    "evidence_class": "detected" if measurement else "interpreted",
                    "confidence": 0.9,
                    "alternatives": [],
                    "provenance": {
                        "surface": "local_measurement" if measurement else "pegasus_analyze",
                        "model": "fixture-measurement" if measurement else "pegasus1.5",
                        "model_version": "1.0",
                        "profile_id": (
                            "local.fixture-measurement"
                            if measurement
                            else "pegasus.score_compliance/1.0"
                        ),
                        "request_hash": "sha256:" + "3" * 64,
                        "raw_response_hash": "sha256:" + "4" * 64,
                    },
                }
                sources.append(
                    make_evidence_source(
                        record, source_type="normalized_video_observation"
                    )
                )
                if not measurement:
                    assertions.append(
                        make_assertion(
                            metric_id=requirement["metric_id"],
                            target_path=target_path,
                            source_ref=source_id,
                            verdict="pass",
                            observed=controls[target_path]["value"],
                            interval={"start_s": 0.0, "end_s": 8.0},
                        )
                    )
        return {
            "schema": "cpcs.verification_evidence_bundle/1.0",
            "job_id": result["job_id"],
            "build_id": result["build_id"],
            "artifact_id": artifact["artifact_id"],
            "artifact_sha256": artifact["sha256"],
            "sources": sources,
            "assertions": assertions,
        }

    def test_guided_preparation_render_and_verification_share_one_public_service(self) -> None:
        text = "Show how this device works in a clear educational video"
        before = authority_snapshot()
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "work") as temporary:
            operational = Path(temporary)
            adapter = FakeAdapter()

            def runner(root: Path) -> RenderRunner:
                return RenderRunner(
                    JobJournal(operational / "render" / "jobs.sqlite3"),
                    root=root,
                    work_root=operational / "render" / "jobs",
                    adapters={adapter.adapter_id: adapter},
                    sleep_fn=lambda _: None,
                )

            with mock.patch(
                "lab.application.service._application_work_root",
                return_value=operational,
            ), mock.patch("lab.application.service._render_runner", side_effect=runner):
                prepared = invoke(
                    request(
                        "cpcs.production.prepare",
                        {
                            "text": text,
                            "project_id": "cpcs-test-project",
                            "assets": self._assets(text),
                            "creative_mode": "diagnostic",
                        },
                    )
                )
                self.assertEqual(prepared["status"], "success")
                self.assertEqual(prepared["result"]["score"]["score_status"], "ready")
                build = prepared["result"]["build"]
                self.assertTrue(Path(build["output_dir"]).is_dir())

                create_arguments = {
                    "build_id": build["build_id"],
                    "idempotency_key": "application-runtime-surface",
                    "poll_interval_seconds": 0,
                }
                created = invoke(
                    request("cpcs.render.create", create_arguments), role="operator"
                )
                self.assertEqual(created["status"], "success")
                job_id = created["result"]["job"]["job_id"]
                run_arguments = {"job_id": job_id}
                denied = invoke(
                    request("cpcs.render.run", run_arguments), role="operator"
                )
                self.assertEqual(denied["error"]["code"], "permission_denied")
                rendered = invoke(
                    authorize("cpcs.render.run", run_arguments), role="operator"
                )
                self.assertEqual(rendered["status"], "success")
                self.assertEqual(rendered["result"]["state"], "succeeded")
                self.assertEqual(adapter.submit_count, 1)

                score = prepared["result"]["score"]
                evidence = self._evidence(score, rendered["result"])
                artifact = rendered["result"]["result"]["artifacts"][0]
                reference_source = operational / "reference-source.mp4"
                reference_source.write_bytes(b"authorized-reference-source")
                pose_model = operational / "pose-model.task"
                pose_model.write_bytes(b"exact-pose-model")
                artifact_path = (
                    operational
                    / "render"
                    / "jobs"
                    / job_id
                    / artifact["relative_path"]
                )

                def frames(_path: Path, _interval: dict, _stride: int):
                    return [(0, 0.0, 0), (1, 2.0, 1), (2, 4.0, 2), (3, 6.0, 3)]

                path = [(0.2, 0.5), (0.3, 0.4), (0.45, 0.4), (0.55, 0.5)]

                def detector(frame: int, _timestamp_ms: int):
                    return [
                        {
                            "left_hip": (0.45, 0.7, 0.98),
                            "right_hip": (0.55, 0.7, 0.98),
                            "left_wrist": (*path[frame], 0.95),
                        }
                    ]

                batches = []
                for source_id, local_path, created_at in (
                    ("source_reference_fixture", reference_source, "2027-01-15T07:59:00Z"),
                    (artifact["artifact_id"], artifact_path, "2027-01-15T08:00:00Z"),
                ):
                    prepared_pose = invoke(
                        request(
                            "cpcs.measure.pose.prepare",
                            {
                                "source_id": source_id,
                                "asset_ref": source_id,
                                "local_path": str(local_path),
                                "rights_scope": "original",
                                "authorized_interval": {"start_s": 0.0, "end_s": 8.0},
                                "model_path": str(pose_model),
                                "model_version": "pose-fixture-1",
                                "created_at": created_at,
                                "keyframe_interval_s": 0.5,
                            },
                        ),
                        role="operator",
                    )
                    self.assertEqual(prepared_pose["status"], "success")
                    with mock.patch(
                        "lab.second_brain.src.measurement._opencv_frames",
                        side_effect=frames,
                    ), mock.patch(
                        "lab.second_brain.src.measurement._mediapipe_detector",
                        return_value=(detector, lambda: None),
                    ):
                        measured_pose = invoke(
                            request(
                                "cpcs.measure.pose.run",
                                {"job": prepared_pose["result"]},
                            ),
                            role="operator",
                        )
                    self.assertEqual(measured_pose["status"], "success")
                    batches.append(measured_pose["result"]["batch"])

                round_trip_arguments = {
                    "build_id": build["build_id"],
                    "job_id": job_id,
                    "artifact_id": artifact["artifact_id"],
                    "reference_batch": batches[0],
                    "generated_batch": batches[1],
                    "actor_mapping": {"actor_A": "actor_A"},
                    "joints": ["left_wrist"],
                    "thresholds": {
                        "minimum_trajectory_cosine_similarity": 0.98,
                        "maximum_translation_aligned_rmse": 0.01,
                        "maximum_duration_error_ratio": 0.05,
                        "maximum_path_length_ratio_error": 0.05,
                    },
                }
                compared = invoke(
                    request("cpcs.verify.reference.roundtrip", round_trip_arguments),
                    role="operator",
                )
                replayed_comparison = invoke(
                    request("cpcs.verify.reference.roundtrip", round_trip_arguments),
                    role="operator",
                )
                self.assertEqual(compared["status"], "success")
                self.assertEqual(compared, replayed_comparison)
                self.assertEqual(
                    compared["result"]["report"]["summary"]["overall_status"],
                    "pass",
                )
                self.assertTrue(Path(compared["result"]["output"]).is_file())
                asset_preparation = invoke(
                    request(
                        "cpcs.verify.asset.prepare",
                        {
                            "build_id": build["build_id"],
                            "job_id": job_id,
                            "artifact_id": artifact["artifact_id"],
                            "rights_scope": "original",
                        },
                    ),
                    role="operator",
                )
                self.assertEqual(asset_preparation["status"], "success")
                self.assertEqual(
                    asset_preparation["result"]["job"]["source"]["sha256"],
                    artifact["sha256"].removeprefix("sha256:"),
                )
                analysis_preparation = invoke(
                    request(
                        "cpcs.verify.analysis.prepare",
                        {
                            "build_id": build["build_id"],
                            "job_id": job_id,
                            "artifact_id": artifact["artifact_id"],
                            "provider_asset_ref": "asset_render_fixture",
                            "rights_scope": "original",
                        },
                    ),
                    role="operator",
                )
                self.assertEqual(analysis_preparation["status"], "success")
                self.assertEqual(
                    analysis_preparation["result"]["job"]["profile_id"],
                    "pegasus.score_compliance/1.0",
                )

                def probe(path: Path, *, expected_sha256: str) -> dict:
                    self.assertEqual(
                        expected_sha256, artifact["sha256"].removeprefix("sha256:")
                    )
                    return {
                        "duration_s": 8.0,
                        "start_time_s": 0.0,
                        "width": 1280,
                        "height": 720,
                        "frame_rate": 24.0,
                        "probe_hash": sha256_value({"fixture": str(path.name)}),
                    }

                with mock.patch("lab.verification.verify.probe_media", side_effect=probe):
                    verified = invoke(
                        request(
                            "cpcs.verify.run",
                            {
                                "build_id": build["build_id"],
                                "job_id": job_id,
                                "artifact_id": artifact["artifact_id"],
                                "observations": [
                                    row["record"] for row in evidence["sources"]
                                ],
                            },
                        ),
                        role="operator",
                    )
                self.assertEqual(verified["status"], "success")
                self.assertEqual(
                    verified["result"]["report"]["overall_status"], "pass"
                )
                self.assertEqual(
                    len(verified["result"]["evidence_bundle"]["assertions"]), 2
                )
                self.assertTrue(Path(verified["result"]["output"]).is_file())
                shown = invoke(
                    request("cpcs.render.show", {"job_id": job_id}), role="operator"
                )
                self.assertEqual(shown["result"]["state"], "succeeded")
                replay = invoke(
                    authorize("cpcs.render.run", run_arguments), role="operator"
                )
                self.assertEqual(replay["result"], rendered["result"])
                self.assertEqual(adapter.submit_count, 1)
        self.assertEqual(before, authority_snapshot())

    def test_twelvelabs_surface_requires_exact_authorization_and_retains_artifacts(self) -> None:
        before = authority_snapshot()
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "work") as temporary:
            operational = Path(temporary)
            job = analysis_job()
            job["job_id"] = "tl_analyze_application_surface_001"
            arguments = {"job": job}
            denied = invoke(request("cpcs.analyze.run", arguments), role="operator")
            self.assertEqual(denied["error"]["code"], "permission_denied")
            with mock.patch(
                "lab.application.service._application_work_root",
                return_value=operational,
            ), mock.patch(
                "lab.second_brain.src.pegasus._active_client",
                return_value=FakeClient(),
            ):
                analyzed = invoke(
                    authorize("cpcs.analyze.run", arguments), role="operator"
                )
            self.assertEqual(analyzed["status"], "success")
            self.assertEqual(len(analyzed["result"]["observations"]), 1)
            for path in analyzed["result"]["artifacts"].values():
                self.assertTrue(Path(path).is_file())
        self.assertEqual(before, authority_snapshot())

    def test_pose_measurement_surface_stages_candidates_without_authority_mutation(self) -> None:
        before = authority_snapshot()
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "work") as temporary:
            operational = Path(temporary)
            source = operational / "source.mp4"
            model = operational / "pose.task"
            source.write_bytes(b"application-pose-source")
            model.write_bytes(b"application-pose-model")
            prepare_arguments = {
                "source_id": "source_application_pose",
                "asset_ref": "asset_application_pose",
                "local_path": str(source),
                "rights_scope": "original",
                "authorized_interval": {"start_s": 0.0, "end_s": 1.5},
                "model_path": str(model),
                "model_version": "pose-landmarker-full-fixture",
                "created_at": "2026-08-03T00:00:00Z",
            }
            prepared = invoke(
                request("cpcs.measure.pose.prepare", prepare_arguments), role="operator"
            )
            self.assertEqual(prepared["status"], "success")
            job = prepared["result"]

            def frames(_path: Path, _interval: dict, _stride: int):
                return [(0, 0.0, "f0"), (1, 0.5, "f1"), (2, 1.0, "f2")]

            def detector(_frame: str, _timestamp_ms: int):
                return [
                    {
                        "left_hip": (0.38, 0.6, 0.95),
                        "right_hip": (0.42, 0.6, 0.96),
                        "left_wrist": (0.32, 0.4, 0.9),
                    }
                ]

            with mock.patch(
                "lab.application.service._application_work_root",
                return_value=operational,
            ), mock.patch(
                "lab.second_brain.src.measurement._opencv_frames",
                side_effect=frames,
            ), mock.patch(
                "lab.second_brain.src.measurement._mediapipe_detector",
                return_value=(detector, lambda: None),
            ):
                measured = invoke(
                    request("cpcs.measure.pose.run", {"job": job}), role="operator"
                )
            self.assertEqual(measured["status"], "success")
            self.assertGreater(
                measured["result"]["batch"]["summary"]["observation_count"], 0
            )
            batch = measured["result"]["batch"]
            immutable_record = copy.deepcopy(batch["observations"][0])
            immutable_record["measurement_batch_id"] = batch["batch_id"]
            immutable_record["prior_record_hash"] = None
            immutable_record["record_hash"] = sha256_value(immutable_record)
            normalize_arguments = {
                "source": {
                    "source_id": batch["source"]["source_id"],
                    "asset_ref": batch["source"]["asset_ref"],
                    "sha256": batch["source"]["sha256"],
                },
                "authorized_interval": batch["authorized_interval"],
                "measurement_observation_ids": [immutable_record["id"]],
            }
            with mock.patch(
                "lab.application.service.read_jsonl",
                return_value=[immutable_record],
            ):
                normalized = invoke(
                    request("cpcs.measure.normalize", normalize_arguments),
                    role="operator",
                )
            self.assertEqual(normalized["status"], "success")
            self.assertEqual(
                normalized["result"]["observations"][0]["subject_refs"],
                ["actor_A"],
            )
            denied = invoke(
                request(
                    "cpcs.record.measurement",
                    {"batch": batch},
                ),
                role="curator",
            )
            self.assertEqual(denied["error"]["code"], "permission_denied")
            cascade_arguments = {
                "cascade": {
                    "cascade_id": "tl_cascade_application_pose",
                    "authorized_interval": {"start_s": 0.0, "end_s": 8.0},
                },
                "intent_context": {"schema": "fixture"},
                "score_assets": [],
            }
            cascade_denied = invoke(
                request("cpcs.analyze.cascade", cascade_arguments), role="curator"
            )
            self.assertEqual(cascade_denied["error"]["code"], "permission_denied")
            with mock.patch(
                "lab.application.service._application_work_root",
                return_value=operational,
            ), mock.patch(
                "lab.application.service.run_analysis_cascade",
                return_value={
                    "video_observation_graph": {"graph_id": "vog_fixture"},
                    "reverse_score": {"score_id": "score_fixture"},
                    "observation": {"id": "pegasus_obs_fixture"},
                    "distillation_run": None,
                    "artifacts": {},
                },
            ) as cascade_owner:
                cascaded = invoke(
                    authorize("cpcs.analyze.cascade", cascade_arguments),
                    role="curator",
                )
            self.assertEqual(cascaded["status"], "success")
            self.assertEqual(
                cascaded["result"]["reverse_score"]["score_id"], "score_fixture"
            )
            self.assertEqual(cascade_owner.call_count, 1)
        self.assertEqual(before, authority_snapshot())

    def test_catalog_marks_external_operations_and_enforces_release_limits(self) -> None:
        operator = {row["name"]: row for row in list_operations("operator")}
        self.assertTrue(operator["cpcs.analyze.run"]["authorization_required"])
        self.assertTrue(operator["cpcs.render.run"]["authorization_required"])
        self.assertFalse(operator["cpcs.render.create"]["authorization_required"])
        self.assertFalse(operator["cpcs.measure.pose.run"]["authorization_required"])
        self.assertFalse(
            operator["cpcs.verify.reference.roundtrip"]["authorization_required"]
        )
        self.assertNotIn("cpcs.record.measurement", operator)
        self.assertNotIn("cpcs.analyze.cascade", operator)
        self.assertNotIn(
            "cpcs.render.run", {row["name"] for row in list_operations("chat")}
        )
        oversized = analysis_job()
        oversized["interval"] = {
            "source_start_s": 0.0,
            "source_end_s": 601.0,
        }
        oversized["media_bounds"] = {
            "source_start_s": 0.0,
            "source_end_s": 601.0,
        }
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "work") as temporary:
            telemetry_path = Path(temporary) / "telemetry.jsonl"
            response = invoke(
                authorize("cpcs.analyze.run", {"job": oversized}),
                role="operator",
                telemetry=TelemetrySink(telemetry_path),
            )
            event = json.loads(telemetry_path.read_text(encoding="utf-8"))
        self.assertEqual(response["error"]["code"], "invalid_request")
        self.assertIn("release limit", response["error"]["message"])
        self.assertEqual(event["authorization_id"], "auth_runtime_surface_test")


if __name__ == "__main__":
    unittest.main()
