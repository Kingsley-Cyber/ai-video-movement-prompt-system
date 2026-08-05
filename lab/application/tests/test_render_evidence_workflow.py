from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lab.application import service
from lab.application.render_evidence_workflow import (
    RenderEvidenceWorkflow,
    WorkflowCrash,
)
from lab.application.service import REQUEST_SCHEMA, authorization_request_hash, invoke
from lab.application.tests.test_universal_acceptance import (
    _assets,
    _fixture_root,
    _pegasus_compliance_response,
)
from lab.compiler.provenance import sha256_bytes
from lab.runtime.journal import JobJournal
from lab.runtime.runner import RenderRunner
from lab.runtime.tests.test_runner import FakeAdapter
from lab.second_brain.src.validate import read_jsonl
from lab.second_brain.tests.test_twelvelabs import FakeClient


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
        "authorization_id": "auth_render_evidence_workflow",
        "authorized_by": "owner-test",
        "operation": operation,
        "request_hash": authorization_request_hash(operation, arguments),
        "reason": "Advance this exact inspected workflow step.",
    }
    return request


class RenderEvidenceWorkflowTests(unittest.TestCase):
    def _prepared_fixture(self, root: Path, operational: Path) -> tuple[dict, dict]:
        text = "Create a restrained scene where she realizes he is lying"
        production = invoke(
            _request(
                "cpcs.production.prepare",
                {
                    "text": text,
                    "project_id": "render-evidence-workflow",
                    "assets": _assets(text, root),
                    "duration_seconds": 4,
                    "aspect_ratio": "16:9",
                    "resolution": "720p",
                    "seed": 41,
                },
            ),
            role="operator",
            root=root,
        )
        self.assertEqual(production["status"], "success", production)
        build = production["result"]["build"]
        experiment_arguments = {
            "flight_id": "flight_render_evidence_workflow",
            "arms": [
                {"id": "a", "build_id": build["build_id"], "tested_delta": None}
            ],
            "classification": "bundled_observation",
            "metric_ids": ["creative_quality"],
            "outcome_concept_ids": [],
            "provider": "fake",
            "model_version": "fixture",
            "sealed_at": "2027-01-15T07:00:00Z",
        }
        prepared = invoke(
            _request("cpcs.experiment.prepare", experiment_arguments),
            role="operator",
            root=root,
        )
        self.assertEqual(prepared["status"], "success", prepared)
        seal_arguments = {"flight_draft": prepared["result"]["flight_draft"]}
        sealed = invoke(
            _authorize("cpcs.experiment.seal", seal_arguments),
            role="curator",
            root=root,
        )
        self.assertEqual(sealed["status"], "success", sealed)
        model_path = operational / "pose-landmarker.task"
        model_path.write_bytes(b"render-evidence-pose-model")
        workflow_request = {
            "schema": "cpcs.render_evidence_workflow_request/1.0",
            "flight_id": sealed["result"]["id"],
            "arm_id": "a",
            "build_id": build["build_id"],
            "artifact_id": "artifact_000",
            "rights_scope": "original",
            "render": {
                "idempotency_key": "render-evidence-workflow-a",
                "timeout_seconds": 300,
                "poll_interval_seconds": 0,
                "max_safe_retries": 2,
                "lease_seconds": 30,
            },
            "measurement": {
                "model_path": str(model_path),
                "model_version": "pose-fixture-1",
                "created_at": "2027-01-15T08:00:00Z",
                "keyframe_interval_s": 0.5,
            },
            "metrics": {"creative_quality": 5},
        }
        return workflow_request, build

    @staticmethod
    def _review() -> dict:
        statement = "The restrained performance and camera timing preserve the intended realization."
        span = {
            "start": 0,
            "end": len(statement),
            "quote": statement,
            "quote_hash": sha256_bytes(statement.encode("utf-8")),
        }
        return {
            "schema": "cpcs.render_evidence_workflow_review/1.0",
            "speaker": {
                "speaker_id": "director_fixture",
                "role": "owner",
                "rights_basis": "owner_authored",
            },
            "language": "en-US",
            "raw_statement": statement,
            "captured_at": "2027-01-15T08:05:00Z",
            "normalization": {
                "normalizer": {
                    "origin": "human_authored",
                    "agent": None,
                    "model": None,
                    "prompt_hash": None,
                    "response_hash": None,
                },
                "normalized_verdict": "keep",
                "summary": statement,
                "confidence": 1.0,
                "dimension_findings": [
                    {
                        "dimension": "performance",
                        "verdict": "pass",
                        "observation": statement,
                        "confidence": 1.0,
                        "evidence_spans": [span],
                    }
                ],
                "metric_findings": [
                    {
                        "metric_id": "creative_quality",
                        "value": 5,
                        "verdict": "pass",
                        "observation": statement,
                        "confidence": 1.0,
                        "authored_targets": [
                            {
                                "target_type": "concept",
                                "target_ref": "c_scored_performance",
                            }
                        ],
                        "evidence_spans": [span],
                        "limitations": [
                            "One reviewed artifact from one bundled arm."
                        ],
                    }
                ],
                "strengths": [],
                "failures": [],
                "attribution_candidates": [],
                "limitations": ["One reviewed artifact from one bundled arm."],
            },
            "reviewed_by": "director_fixture",
            "reviewed_at": "2027-01-15T08:06:00Z",
            "human_review": {
                "review_id": "review_render_evidence_workflow_a",
                "reviewer_id": "director_fixture",
                "verdict": "keep",
                "rationale": statement,
                "reviewed_at": "2027-01-15T08:06:00Z",
            },
        }

    def test_public_workflow_recovers_and_records_one_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _fixture_root(Path(directory))
            operational = root / "work" / "application"
            workflow_request, _build = self._prepared_fixture(root, operational)
            adapter = FakeAdapter()

            def render_runner(runtime_root: Path) -> RenderRunner:
                return RenderRunner(
                    JobJournal(operational / "render" / "jobs.sqlite3"),
                    root=runtime_root,
                    work_root=operational / "render" / "jobs",
                    adapters={adapter.adapter_id: adapter},
                    sleep_fn=lambda _: None,
                )

            asset_client = FakeClient()
            analysis_client = FakeClient()
            clients = iter((asset_client, analysis_client))

            def active_client(*_args, **_kwargs) -> FakeClient:
                return next(clients)

            def frames(_path: Path, _interval: dict, _stride: int):
                return [(0, 0.0, 0), (1, 1.0, 1), (2, 2.0, 2), (3, 3.0, 3)]

            points = [(0.20, 0.50), (0.30, 0.40), (0.45, 0.40), (0.55, 0.50)]

            def detector(frame: int, _timestamp_ms: int):
                return [
                    {
                        "left_hip": (0.45, 0.70, 0.98),
                        "right_hip": (0.55, 0.70, 0.98),
                        "left_wrist": (*points[frame], 0.95),
                        "right_wrist": (1 - points[frame][0], points[frame][1], 0.95),
                    }
                ]

            def probe(_path: Path, *, expected_sha256: str) -> dict:
                self.assertRegex(expected_sha256, r"^[0-9a-f]{64}$")
                return {
                    "duration_s": 4.0,
                    "start_time_s": 0.0,
                    "width": 1280,
                    "height": 720,
                    "frame_rate": 24.0,
                    "probe_hash": "sha256:" + "9" * 64,
                }

            with mock.patch(
                "lab.application.service._application_work_root",
                return_value=operational,
            ), mock.patch(
                "lab.application.service._render_runner", side_effect=render_runner
            ), mock.patch(
                "lab.second_brain.src.pegasus._active_client",
                side_effect=active_client,
            ), mock.patch(
                "lab.second_brain.src.measurement._opencv_frames",
                side_effect=frames,
            ), mock.patch(
                "lab.second_brain.src.measurement._mediapipe_detector",
                return_value=(detector, lambda: None),
            ), mock.patch(
                "lab.verification.verify.probe_media", side_effect=probe
            ):
                prepare_arguments = {"request": workflow_request}
                prepared = invoke(
                    _request("cpcs.workflow.render.prepare", prepare_arguments),
                    role="operator",
                    root=root,
                )
                self.assertEqual(prepared["status"], "success", prepared)
                self.assertEqual(
                    invoke(
                        _request("cpcs.workflow.render.prepare", prepare_arguments),
                        role="operator",
                        root=root,
                    ),
                    prepared,
                )
                status = prepared["result"]
                workflow_id = status["workflow_id"]
                workflow_directory = (
                    operational / "render_evidence_workflows" / workflow_id
                )
                crash_once = {"enabled": True}

                def crash_hook(_event: str, _artifact: dict) -> None:
                    if crash_once["enabled"]:
                        crash_once["enabled"] = False
                        raise WorkflowCrash("simulated process death after durable child receipt")

                crashing = RenderEvidenceWorkflow(
                    executor=lambda operation, arguments: service._workflow_child_executor(
                        operation, arguments, root
                    ),
                    build_path=lambda build_id: service._build_path(build_id, root),
                    root=root,
                    work_root=operational / "render_evidence_workflows",
                    crash_hook=crash_hook,
                )
                with mock.patch(
                    "lab.application.service._render_evidence_workflow",
                    return_value=crashing,
                ):
                    first_step = {
                        "workflow_id": workflow_id,
                        "expected_step_hash": status["next_step"]["step_hash"],
                    }
                    interrupted = invoke(
                        _authorize("cpcs.workflow.render.advance", first_step),
                        role="curator",
                        root=root,
                    )
                    self.assertEqual(interrupted["status"], "error")
                    self.assertIn("simulated process death", interrupted["error"]["message"])
                    crashing.crash_hook = None
                    resumed = invoke(
                        _authorize("cpcs.workflow.render.advance", first_step),
                        role="curator",
                        root=root,
                    )
                    self.assertEqual(resumed["status"], "success", resumed)
                    status = resumed["result"]

                self.assertEqual(adapter.submit_count, 0)
                while status["state"] not in {"awaiting_review", "completed", "failed"}:
                    next_step = status["next_step"]
                    self.assertIsNotNone(next_step, status)
                    if next_step["kind"] == "analysis_run":
                        internal = json.loads(
                            (workflow_directory / "state.json").read_text(encoding="utf-8")
                        )
                        analysis_client.analyze_response = _pegasus_compliance_response(
                            internal["next_step"]["arguments"]["job"]
                        )
                    advance_arguments = {
                        "workflow_id": workflow_id,
                        "expected_step_hash": next_step["step_hash"],
                    }
                    advanced = invoke(
                        _authorize("cpcs.workflow.render.advance", advance_arguments),
                        role="curator",
                        root=root,
                    )
                    self.assertEqual(advanced["status"], "success", advanced)
                    status = advanced["result"]

                self.assertEqual(status["state"], "awaiting_review", status)
                self.assertEqual(adapter.submit_count, 1)
                self.assertGreater(status["evidence_counts"]["semantic"], 0)
                self.assertGreater(status["evidence_counts"]["measurement"], 0)
                self.assertEqual(
                    status["metric_requirements"]["sealed_metrics"],
                    [{"metric_id": "creative_quality", "value": 5}],
                )
                self.assertIn(
                    "normalization.metric_findings",
                    status["metric_requirements"]["testimonial_rule"],
                )
                self.assertNotIn("raw_statement", json.dumps(status))
                review_arguments = {
                    "workflow_id": workflow_id,
                    "expected_state_hash": status["state_hash"],
                    "review": self._review(),
                }
                reviewed = invoke(
                    _authorize("cpcs.workflow.render.review", review_arguments),
                    role="curator",
                    root=root,
                )
                self.assertEqual(reviewed["status"], "success", reviewed)
                status = reviewed["result"]
                while status["state"] != "completed":
                    next_step = status["next_step"]
                    self.assertIsNotNone(next_step, status)
                    advance_arguments = {
                        "workflow_id": workflow_id,
                        "expected_step_hash": next_step["step_hash"],
                    }
                    advanced = invoke(
                        _authorize("cpcs.workflow.render.advance", advance_arguments),
                        role="curator",
                        root=root,
                    )
                    self.assertEqual(advanced["status"], "success", advanced)
                    status = advanced["result"]

                final_step_hash = status["last_completed_step_hash"]
                replay_arguments = {
                    "workflow_id": workflow_id,
                    "expected_step_hash": final_step_hash,
                }
                replay = invoke(
                    _authorize("cpcs.workflow.render.advance", replay_arguments),
                    role="curator",
                    root=root,
                )
                self.assertEqual(replay["result"], status)
                read_status = invoke(
                    _request(
                        "cpcs.workflow.render.status", {"workflow_id": workflow_id}
                    ),
                    role="operator",
                    root=root,
                )
                self.assertEqual(read_status["result"], status)
                runs = [
                    row
                    for row in read_jsonl(
                        root / "lab" / "second_brain" / "immutable" / "runs.jsonl"
                    )
                    if row.get("flight_id") == workflow_request["flight_id"]
                ]
                self.assertEqual(len(runs), 1)
                self.assertEqual(runs[0]["id"], status["result"]["run_id"])
                self.assertEqual(len(asset_client.assets.create_calls), 1)
                self.assertEqual(len(analysis_client.analyze_calls), 1)
                for path in (
                    workflow_directory / "request.json",
                    workflow_directory / "state.json",
                ):
                    self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_cancel_is_exact_and_state_tampering_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _fixture_root(Path(directory))
            operational = root / "work" / "application"
            workflow_request, _build = self._prepared_fixture(root, operational)
            workflow_request["render"]["idempotency_key"] = "cancel-before-render"
            adapter = FakeAdapter()

            def render_runner(runtime_root: Path) -> RenderRunner:
                return RenderRunner(
                    JobJournal(operational / "render" / "jobs.sqlite3"),
                    root=runtime_root,
                    work_root=operational / "render" / "jobs",
                    adapters={adapter.adapter_id: adapter},
                    sleep_fn=lambda _: None,
                )

            with mock.patch(
                "lab.application.service._application_work_root",
                return_value=operational,
            ), mock.patch(
                "lab.application.service._render_runner", side_effect=render_runner
            ):
                prepared = invoke(
                    _request(
                        "cpcs.workflow.render.prepare", {"request": workflow_request}
                    ),
                    role="operator",
                    root=root,
                )
                self.assertEqual(prepared["status"], "success", prepared)
                status = prepared["result"]
                registered = invoke(
                    _authorize(
                        "cpcs.workflow.render.advance",
                        {
                            "workflow_id": status["workflow_id"],
                            "expected_step_hash": status["next_step"]["step_hash"],
                        },
                    ),
                    role="curator",
                    root=root,
                )
                self.assertEqual(registered["status"], "success", registered)
                status = registered["result"]
                self.assertEqual(status["next_step"]["kind"], "render_run")
                self.assertIsNotNone(status["lineage"]["render_job_id"])
                self.assertEqual(adapter.submit_count, 0)
                stale = invoke(
                    _authorize(
                        "cpcs.workflow.render.cancel",
                        {
                            "workflow_id": status["workflow_id"],
                            "expected_state_hash": "sha256:" + "0" * 64,
                        },
                    ),
                    role="operator",
                    root=root,
                )
                self.assertEqual(stale["error"]["code"], "invalid_request")
                cancel_arguments = {
                    "workflow_id": status["workflow_id"],
                    "expected_state_hash": status["state_hash"],
                }
                cancelled = invoke(
                    _authorize("cpcs.workflow.render.cancel", cancel_arguments),
                    role="operator",
                    root=root,
                )
                self.assertEqual(cancelled["result"]["state"], "cancelled")
                self.assertEqual(
                    cancelled["result"]["result"]["cancellation"]["state"],
                    "cancelled",
                )
                self.assertEqual(
                    invoke(
                        _authorize("cpcs.workflow.render.cancel", cancel_arguments),
                        role="operator",
                        root=root,
                    )["result"],
                    cancelled["result"],
                )
                wrong_replay = invoke(
                    _authorize(
                        "cpcs.workflow.render.cancel",
                        {
                            "workflow_id": status["workflow_id"],
                            "expected_state_hash": "sha256:" + "1" * 64,
                        },
                    ),
                    role="operator",
                    root=root,
                )
                self.assertEqual(wrong_replay["error"]["code"], "invalid_request")
                state_path = (
                    operational
                    / "render_evidence_workflows"
                    / status["workflow_id"]
                    / "state.json"
                )
                state = json.loads(state_path.read_text(encoding="utf-8"))
                state["step_index"] += 1
                state_path.write_text(
                    json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n",
                    encoding="utf-8",
                )
                tampered = invoke(
                    _request(
                        "cpcs.workflow.render.status",
                        {"workflow_id": status["workflow_id"]},
                    ),
                    role="operator",
                    root=root,
                )
                self.assertEqual(tampered["status"], "error")
                self.assertIn("state hash", tampered["error"]["message"])


if __name__ == "__main__":
    unittest.main()
