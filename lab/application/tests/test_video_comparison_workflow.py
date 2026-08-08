from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lab.application import service
from lab.application.mcp import handle_message
from lab.application.service import REQUEST_SCHEMA, authorization_request_hash, invoke
from lab.application.tests.test_universal_acceptance import _fixture_root
from lab.application.video_comparison_workflow import (
    VideoComparisonWorkflow,
    VideoComparisonWorkflowCrash,
)
from lab.compiler.provenance import canonical_json_bytes, sha256_value


def _request(operation: str, arguments: dict) -> dict:
    return {
        "schema": REQUEST_SCHEMA,
        "operation": operation,
        "arguments": arguments,
    }


def _authorize(operation: str, arguments: dict) -> dict:
    request = _request(operation, arguments)
    request["authorization"] = {
        "schema": "cpcs.explicit_authorization/1.0",
        "authorization_id": "auth_video_comparison_workflow",
        "authorized_by": "owner-test",
        "operation": operation,
        "request_hash": authorization_request_hash(operation, arguments),
        "reason": "Advance this exact inspected comparison step.",
    }
    return request


def _authority_snapshot(root: Path) -> dict[str, bytes]:
    paths = [root / "lab" / "concepts.jsonl"]
    second_brain = root / "lab" / "second_brain"
    for tier in ("curated", "immutable", "derived", "staging"):
        paths.extend(
            path for path in (second_brain / tier).rglob("*") if path.is_file()
        )
    return {
        str(path.relative_to(root)): path.read_bytes() for path in sorted(paths)
    }


def _workflow_request(root: Path, *, suffix: str = "a") -> dict:
    reference = root / "work" / f"reference-{suffix}.mp4"
    candidate = root / "work" / f"candidate-{suffix}.mp4"
    reference.parent.mkdir(parents=True, exist_ok=True)
    reference.write_bytes(f"reference-{suffix}".encode())
    candidate.write_bytes(f"candidate-{suffix}".encode())

    def side(name: str, path: Path) -> dict:
        return {
            "source": {
                "source_id": f"source_{name}_{suffix}",
                "asset_ref": f"asset_{name}_{suffix}",
                "asset_job_id": f"tl_asset_{name}_{suffix}",
                "local_path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "rights_scope": "original",
            },
            "authorized_interval": {"start_s": 0.0, "end_s": 8.0},
            "asr": None,
        }

    return {
        "schema": "cpcs.video_comparison_workflow_request/1.0",
        "mode": "pegasus_direct",
        "reference": side("reference", reference),
        "candidate": side("candidate", candidate),
        "analysis": {
            "mode": "fast",
            "domain_lenses": [],
            "candidate_concepts": [],
            "max_parallel_jobs": 1,
            "maximum_provider_calls": 6,
            "created_at": "2027-01-15T08:00:00Z",
        },
        "local_measurement": None,
        "comparison_settings": {
            "scene_threshold": 0.25,
            "normalized_cut_tolerance": 0.05,
            "minimum_speech_pace_ratio": 0.95,
            "minimum_pose_speed_ratio": 0.95,
            "minimum_pause_s": 0.25,
            "max_pose_gap_s": 1.0,
            "max_pose_step": 0.75,
            "pose_actor_mapping": {"actor_A": "actor_A"},
            "joints": ["left_wrist", "right_wrist"],
            "visual_sample_count": 0,
        },
        "assessments": [],
    }


class VideoComparisonWorkflowTests(unittest.TestCase):
    @staticmethod
    def _fake_plan(arguments: dict, _root: Path) -> dict:
        source = arguments["source"]
        suffix = hashlib.sha256(source["sha256"].encode()).hexdigest()[:24]
        cascade = {
            "schema": "cpcs.video_analysis_cascade/1.0",
            "cascade_id": "tl_cascade_atomic_" + suffix,
            "source": copy.deepcopy(source),
            "authorized_interval": copy.deepcopy(arguments["authorized_interval"]),
            "source_map_profile": "pegasus.source_map/1.0",
            "segment_profile": "pegasus.action_graph/1.0",
            "supplemental_segment_profiles": [],
            "deep_analysis_profiles": ["pegasus.camera_edit/1.0"],
            "analysis_window_policy": "authorized_interval",
            "max_parallel_jobs": 1,
            "candidate_concepts": [],
            "measurement_observation_ids": [],
            "created_at": arguments["created_at"],
        }
        return {
            "schema": "cpcs.atomic_video_analysis_plan/1.0",
            "plan_id": "atomic_plan_" + suffix,
            "mode": "fast",
            "domain_lenses": [],
            "provider_call_count": 3,
            "coverage": {
                "semantic_profiles": [
                    "pegasus.source_map/1.0",
                    "pegasus.camera_edit/1.0",
                ],
                "segment_profiles": ["pegasus.action_graph/1.0"],
                "analysis_window_policy": "authorized_interval",
                "local_measurement_policy": "none",
                "limitations": ["fixture plan"],
            },
            "cascade": cascade,
            "authority_effect": "plan_only_no_authority_mutation",
            "policy_version": "cpcs-atomic-video-analysis/1.0",
        }

    @staticmethod
    def _fake_cascade(
        cascade: dict, root: Path, *, authority_mode: str, output_root: Path, **_: object
    ) -> dict:
        if authority_mode != "operational_only":
            raise AssertionError("comparison must request operational-only cascade mode")
        source = cascade["source"]
        graph_suffix = hashlib.sha256(source["sha256"].encode()).hexdigest()[:32]
        graph = {
            "schema": "cpcs.video_observation_graph/1.0",
            "graph_id": "vog_" + graph_suffix,
            "source": {
                "source_id": source["source_id"],
                "asset_ref": source["asset_ref"],
                "sha256": source["sha256"],
                "rights_scope": source["rights_scope"],
            },
            "authorized_interval": copy.deepcopy(cascade["authorized_interval"]),
            "media_metadata": {
                "duration_s": 8.0,
                "start_time_s": 0.0,
                "width": 1080,
                "height": 1920,
                "frame_rate": 30.0,
                "probe_hash": "sha256:" + "1" * 64,
            },
            "nodes": [
                {
                    "id": "vog_node_source_" + graph_suffix[:16],
                    "node_type": "source",
                    "data": {
                        "source_id": source["source_id"],
                        "asset_ref": source["asset_ref"],
                        "sha256": source["sha256"],
                        "rights_scope": source["rights_scope"],
                    },
                }
            ],
            "edges": [],
            "contradictions": [],
            "fusion_report": {
                "semantic_observations": 0,
                "measurement_observations": 0,
                "support_links": 0,
                "contradictions": 0,
                "confidence_averaging": False,
            },
            "surface_runs": [
                {
                    "surface": "assets" if index == 0 else "pegasus_analyze",
                    "job_id": f"job_{graph_suffix}_{index}",
                    "request_hash": "sha256:" + str(index + 1) * 64,
                    "raw_response_hash": "sha256:" + str(index + 2) * 64,
                }
                for index in range(4)
            ],
            "graph_hash": "sha256:" + graph_suffix + graph_suffix,
        }
        path = output_root / "04_vog.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json_bytes(graph))
        return {
            "video_observation_graph": graph,
            "reverse_score": None,
            "observation": None,
            "distillation_run": None,
            "authority_effect": "operational_only_no_authority_mutation",
            "artifacts": {
                "vog": str(path),
                "reverse_score": None,
                "immutable_payload": None,
                "run": None,
            },
        }

    @staticmethod
    def _fake_comparison(_arguments: dict, *, root: Path) -> dict:
        return {
            "schema": "cpcs.reference_candidate_comparison_report/1.0",
            "report_id": "reference_candidate_" + "a" * 24,
            "overall_status": "fail",
            "root_hash": sha256_value(str(root)),
        }

    @staticmethod
    def _fake_pose_job(**arguments: object) -> dict:
        source_id = str(arguments["source_id"])
        suffix = hashlib.sha256(source_id.encode()).hexdigest()[:24]
        return {
            "schema": "cpcs.pose_measurement_job/1.0",
            "job_id": "pose_job_" + suffix,
            "source": {
                "source_id": source_id,
                "asset_ref": str(arguments["asset_ref"]),
                "local_path": str(arguments["local_path"]),
                "sha256": hashlib.sha256(
                    Path(str(arguments["local_path"])).read_bytes()
                ).hexdigest(),
                "rights_scope": str(arguments["rights_scope"]),
            },
            "authorized_interval": copy.deepcopy(arguments["authorized_interval"]),
            "detector": {
                "model_version": str(arguments["model_version"]),
            },
        }

    @staticmethod
    def _fake_pose_run(
        job: dict, _root: Path, *, output_root: Path, **_: object
    ) -> dict:
        source = job["source"]
        batch = {
            "schema": "cpcs.measurement_batch/1.0",
            "batch_id": "measurement_batch_" + job["job_id"].removeprefix("pose_job_"),
            "job_id": job["job_id"],
            "source": {
                "source_id": source["source_id"],
                "asset_ref": source["asset_ref"],
                "sha256": source["sha256"],
            },
            "authorized_interval": copy.deepcopy(job["authorized_interval"]),
            "tool": "mediapipe_pose",
            "model_version": job["detector"]["model_version"],
        }
        path = output_root / "measurement_batch.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json_bytes(batch))
        return {
            "schema": "cpcs.pose_measurement_result/1.0",
            "job_id": job["job_id"],
            "batch": batch,
            "artifacts": {"measurement_batch": str(path)},
        }

    def test_public_workflow_recovers_replays_and_exposes_all_mcp_operations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _fixture_root(Path(directory))
            request = _workflow_request(root)
            model_path = root / "work" / "pose-landmarker.task"
            model_path.write_bytes(b"paired-pose-model")
            request["local_measurement"] = {
                "model_path": str(model_path),
                "model_version": "pose-fixture-1",
                "created_at": "2027-01-15T08:00:00Z",
                "keyframe_interval_s": 0.5,
            }
            before = _authority_snapshot(root)
            calls = {"cascade": 0, "compare": 0}

            def cascade(*args, **kwargs):
                calls["cascade"] += 1
                return self._fake_cascade(*args, **kwargs)

            def comparison(*args, **kwargs):
                calls["compare"] += 1
                return self._fake_comparison(*args, **kwargs)

            with mock.patch(
                "lab.application.service.make_atomic_analysis_plan",
                side_effect=self._fake_plan,
            ), mock.patch(
                "lab.application.service.run_analysis_cascade", side_effect=cascade
            ), mock.patch(
                "lab.application.service.compare_reference_candidate",
                side_effect=comparison,
            ), mock.patch(
                "lab.application.service.make_pose_measurement_job",
                side_effect=self._fake_pose_job,
            ), mock.patch(
                "lab.application.service.execute_pose_measurement_job",
                side_effect=self._fake_pose_run,
            ):
                prepare_arguments = {"request": request}
                prepared = invoke(
                    _request("cpcs.video.compare.prepare", prepare_arguments),
                    role="operator",
                    root=root,
                )
                self.assertEqual(prepared["status"], "success", prepared)
                self.assertEqual(
                    invoke(
                        _request("cpcs.video.compare.prepare", prepare_arguments),
                        role="operator",
                        root=root,
                    ),
                    prepared,
                )
                status = prepared["result"]
                self.assertEqual(status["provider_calls"]["planned"], 6)
                self.assertEqual(status["provider_calls"]["completed"], 0)
                workflow_id = status["workflow_id"]
                denied = invoke(
                    _request(
                        "cpcs.video.compare.advance",
                        {
                            "workflow_id": workflow_id,
                            "expected_step_hash": status["next_step"]["step_hash"],
                        },
                    ),
                    role="curator",
                    root=root,
                )
                self.assertEqual(denied["error"]["code"], "permission_denied")

                crash_once = {"enabled": True}

                def crash_hook(_event: str, _artifact: dict) -> None:
                    if crash_once["enabled"]:
                        crash_once["enabled"] = False
                        raise VideoComparisonWorkflowCrash(
                            "simulated process death after paired child receipt"
                        )

                crashing = VideoComparisonWorkflow(
                    executor=lambda operation, arguments: service._workflow_child_executor(
                        operation, arguments, root
                    ),
                    root=root,
                    work_root=root / "work" / "application" / "video_comparisons",
                    crash_hook=crash_hook,
                )
                first_step = {
                    "workflow_id": workflow_id,
                    "expected_step_hash": status["next_step"]["step_hash"],
                }
                with mock.patch(
                    "lab.application.service._video_comparison_workflow",
                    return_value=crashing,
                ):
                    interrupted = invoke(
                        _authorize("cpcs.video.compare.advance", first_step),
                        role="curator",
                        root=root,
                    )
                    self.assertEqual(interrupted["status"], "error")
                    self.assertIn(
                        "simulated process death", interrupted["error"]["message"]
                    )
                    crashing.crash_hook = None
                    resumed = invoke(
                        _authorize("cpcs.video.compare.advance", first_step),
                        role="curator",
                        root=root,
                    )
                self.assertEqual(resumed["status"], "success", resumed)
                self.assertEqual(calls["cascade"], 1)
                status = resumed["result"]
                while status["state"] != "completed":
                    arguments = {
                        "workflow_id": workflow_id,
                        "expected_step_hash": status["next_step"]["step_hash"],
                    }
                    advanced = invoke(
                        _authorize("cpcs.video.compare.advance", arguments),
                        role="curator",
                        root=root,
                    )
                    self.assertEqual(advanced["status"], "success", advanced)
                    status = advanced["result"]

                self.assertEqual(calls, {"cascade": 2, "compare": 1})
                self.assertEqual(status["provider_calls"]["completed"], 6)
                self.assertNotEqual(
                    status["reference"]["video_observation_graph_id"],
                    status["candidate"]["video_observation_graph_id"],
                )
                self.assertTrue(status["local_measurement"]["enabled"])
                self.assertIsNotNone(
                    status["local_measurement"]["reference_batch_id"]
                )
                self.assertIsNotNone(
                    status["local_measurement"]["candidate_batch_id"]
                )
                replay_arguments = {
                    "workflow_id": workflow_id,
                    "expected_step_hash": status["last_completed_step_hash"],
                }
                replay = invoke(
                    _authorize("cpcs.video.compare.advance", replay_arguments),
                    role="curator",
                    root=root,
                )
                self.assertEqual(replay["result"], status)
                self.assertEqual(calls, {"cascade": 2, "compare": 1})
                inspection = invoke(
                    _request(
                        "cpcs.video.compare.inspect", {"workflow_id": workflow_id}
                    ),
                    role="operator",
                    root=root,
                )
                self.assertEqual(inspection["status"], "success", inspection)
                report = inspection["result"]["report"]
                self.assertEqual(
                    report["authority_status"], "operational_evidence_only"
                )
                self.assertEqual(report["provider_calls"], {"planned": 6, "completed": 6})

            operator_tools = {
                row["name"]
                for row in handle_message(
                    {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                    role="operator",
                )["result"]["tools"]
            }
            curator_tools = {
                row["name"]
                for row in handle_message(
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                    role="curator",
                )["result"]["tools"]
            }
            self.assertEqual(
                {
                    "cpcs.video.compare.prepare",
                    "cpcs.video.compare.status",
                    "cpcs.video.compare.inspect",
                    "cpcs.video.compare.cancel",
                }
                <= operator_tools,
                True,
            )
            self.assertIn("cpcs.video.compare.advance", curator_tools)
            self.assertNotIn("cpcs.video.compare.advance", operator_tools)
            self.assertEqual(before, _authority_snapshot(root))

    def test_cancel_is_exact_and_state_tampering_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _fixture_root(Path(directory))
            request = _workflow_request(root, suffix="cancel")
            with mock.patch(
                "lab.application.service.make_atomic_analysis_plan",
                side_effect=self._fake_plan,
            ):
                prepared = invoke(
                    _request(
                        "cpcs.video.compare.prepare", {"request": request}
                    ),
                    role="operator",
                    root=root,
                )
            self.assertEqual(prepared["status"], "success", prepared)
            status = prepared["result"]
            stale_arguments = {
                "workflow_id": status["workflow_id"],
                "expected_state_hash": "sha256:" + "0" * 64,
            }
            stale = invoke(
                _authorize("cpcs.video.compare.cancel", stale_arguments),
                role="operator",
                root=root,
            )
            self.assertEqual(stale["error"]["code"], "invalid_request")
            cancel_arguments = {
                "workflow_id": status["workflow_id"],
                "expected_state_hash": status["state_hash"],
            }
            cancelled = invoke(
                _authorize("cpcs.video.compare.cancel", cancel_arguments),
                role="operator",
                root=root,
            )
            self.assertEqual(cancelled["status"], "success", cancelled)
            self.assertEqual(cancelled["result"]["state"], "cancelled")
            self.assertEqual(
                invoke(
                    _authorize("cpcs.video.compare.cancel", cancel_arguments),
                    role="operator",
                    root=root,
                )["result"],
                cancelled["result"],
            )
            state_path = (
                root
                / "work"
                / "application"
                / "video_comparisons"
                / status["workflow_id"]
                / "state.json"
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["step_index"] += 1
            state_path.write_bytes(canonical_json_bytes(state))
            tampered = invoke(
                _request(
                    "cpcs.video.compare.status",
                    {"workflow_id": status["workflow_id"]},
                ),
                role="operator",
                root=root,
            )
            self.assertEqual(tampered["status"], "error")
            self.assertIn("state hash", tampered["error"]["message"])

    def test_prepare_rejects_profile_drift_and_fixed_budget_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _fixture_root(Path(directory))
            before = _authority_snapshot(root)

            drift_request = _workflow_request(root, suffix="profile-drift")
            plan_calls = {"count": 0}

            def drifting_plan(arguments: dict, plan_root: Path) -> dict:
                plan_calls["count"] += 1
                plan = self._fake_plan(arguments, plan_root)
                if plan_calls["count"] == 2:
                    plan["coverage"]["semantic_profiles"] = [
                        "pegasus.source_map/1.0",
                        "pegasus.performance/1.0",
                    ]
                return plan

            with mock.patch(
                "lab.application.service.make_atomic_analysis_plan",
                side_effect=drifting_plan,
            ):
                drift = invoke(
                    _request(
                        "cpcs.video.compare.prepare", {"request": drift_request}
                    ),
                    role="operator",
                    root=root,
                )
            self.assertEqual(drift["status"], "error")
            self.assertIn("identical profiles", drift["error"]["message"])

            budget_request = _workflow_request(root, suffix="budget")

            def expensive_plan(arguments: dict, plan_root: Path) -> dict:
                plan = self._fake_plan(arguments, plan_root)
                plan["provider_call_count"] = 4
                return plan

            with mock.patch(
                "lab.application.service.make_atomic_analysis_plan",
                side_effect=expensive_plan,
            ):
                overflow = invoke(
                    _request(
                        "cpcs.video.compare.prepare", {"request": budget_request}
                    ),
                    role="operator",
                    root=root,
                )
            self.assertEqual(overflow["status"], "error")
            self.assertIn("above the fixed maximum", overflow["error"]["message"])
            self.assertEqual(before, _authority_snapshot(root))


if __name__ == "__main__":
    unittest.main()
