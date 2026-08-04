from __future__ import annotations

import copy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lab.application.service import (
    REQUEST_SCHEMA,
    authorization_request_hash,
    invoke,
)
from lab.compiler.provenance import sha256_value
from lab.runtime.journal import JobJournal
from lab.runtime.runner import RenderRunner
from lab.runtime.tests.test_runner import FakeAdapter
from lab.second_brain.src.intent import build_intent_context
from lab.second_brain.src.validate import (
    REPO_ROOT,
    read_jsonl,
    validate_control_plane,
)
from lab.second_brain.tests.helpers import make_root
from lab.verification.verify import make_assertion, make_evidence_source


def _request(operation: str, arguments: dict) -> dict:
    return {
        "schema": REQUEST_SCHEMA,
        "operation": operation,
        "arguments": arguments,
    }


def _authorize(operation: str, arguments: dict) -> dict:
    value = _request(operation, arguments)
    value["authorization"] = {
        "schema": "cpcs.explicit_authorization/1.0",
        "authorization_id": "auth_universal_acceptance",
        "authorized_by": "owner-test",
        "operation": operation,
        "request_hash": authorization_request_hash(operation, arguments),
        "reason": "Exercise the exact controlled acceptance operation.",
    }
    return value


def _curated_snapshot(root: Path) -> dict[str, bytes]:
    paths = [root / "lab" / "concepts.jsonl"]
    paths.extend(
        path
        for path in (root / "lab" / "second_brain" / "curated").rglob("*")
        if path.is_file()
    )
    return {
        str(path.relative_to(root)): path.read_bytes() for path in sorted(paths)
    }


def _fixture_root(base: Path) -> Path:
    root = make_root(
        base,
        read_jsonl(REPO_ROOT / "lab" / "concepts.jsonl"),
    )
    for source in (REPO_ROOT / "lab" / "second_brain" / "curated").glob(
        "*.jsonl"
    ):
        (root / "lab" / "second_brain" / "curated" / source.name).write_bytes(
            source.read_bytes()
        )
    shutil.copytree(
        REPO_ROOT / "lab" / "application" / "schemas",
        root / "lab" / "application" / "schemas",
    )
    shutil.copytree(REPO_ROOT / "lab" / "release", root / "lab" / "release")
    validate_control_plane(root)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "Create universal acceptance fixture",
        ],
        cwd=root,
        check=True,
    )
    return root


def _assets(text: str, root: Path) -> list[dict]:
    routed = build_intent_context(text, root=root)
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


def _verification_evidence(
    score: dict,
    render_snapshot: dict,
    *,
    arm_id: str,
) -> dict:
    result = render_snapshot["result"]
    artifact = result["artifacts"][0]
    controls = {row["path"]: row for row in score["provider_neutral_controls"]}
    sources = []
    assertions = []
    for requirement_index, requirement in enumerate(
        score["verification_requirements"]
    ):
        for target_index, target_path in enumerate(requirement["target_paths"]):
            measured = requirement["observability"] == "measured"
            source_id = (
                f"vog_obs_acceptance_{arm_id}_{requirement_index}_{target_index}"
            )
            claim = (
                {
                    "label": "fixture measurement comparison",
                    "description": requirement["method"],
                }
                if measured
                else {
                    "metric_id": requirement["metric_id"],
                    "target_path": target_path,
                    "method": requirement["method"],
                    "verdict": "pass",
                    "observed": copy.deepcopy(controls[target_path]["value"]),
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
                "layer": "measurement" if measured else "camera",
                "claim": claim,
                "evidence_class": "detected" if measured else "interpreted",
                "confidence": 0.9,
                "alternatives": [],
                "provenance": {
                    "surface": (
                        "local_measurement" if measured else "pegasus_analyze"
                    ),
                    "model": (
                        "fixture-measurement" if measured else "pegasus1.5"
                    ),
                    "model_version": "1.0",
                    "profile_id": (
                        "local.fixture-measurement"
                        if measured
                        else "pegasus.score_compliance/1.0"
                    ),
                    "request_hash": "sha256:" + "3" * 64,
                    "raw_response_hash": "sha256:" + "4" * 64,
                },
            }
            source = make_evidence_source(
                record, source_type="normalized_video_observation"
            )
            sources.append(source)
            assertions.append(
                make_assertion(
                    metric_id=requirement["metric_id"],
                    target_path=target_path,
                    source_ref=source_id,
                    verdict="pass",
                    observed=copy.deepcopy(controls[target_path]["value"]),
                    interval={"start_s": 0.0, "end_s": 8.0},
                    limitations=["Fixture acceptance evidence."],
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


class UniversalAcceptanceTests(unittest.TestCase):
    def test_public_intent_to_controlled_learning_loop(self) -> None:
        text = "Create a multi-actor action scene with readable screen direction"
        with tempfile.TemporaryDirectory() as directory:
            root = _fixture_root(Path(directory))
            operational = root / "work" / "application"
            adapter = FakeAdapter(
                poll_values=[
                    {
                        "status": "pending",
                        "operation_id": "operation_fixture_a",
                        "raw": {"done": False},
                    },
                    {
                        "status": "succeeded",
                        "operation_id": "operation_fixture_a",
                        "raw": {"done": True, "response": {"videos": [{}]}},
                    },
                    {
                        "status": "pending",
                        "operation_id": "operation_fixture_b",
                        "raw": {"done": False},
                    },
                    {
                        "status": "succeeded",
                        "operation_id": "operation_fixture_b",
                        "raw": {"done": True, "response": {"videos": [{}]}},
                    },
                ]
            )

            def runner(runtime_root: Path) -> RenderRunner:
                return RenderRunner(
                    JobJournal(operational / "render" / "jobs.sqlite3"),
                    root=runtime_root,
                    work_root=operational / "render" / "jobs",
                    adapters={adapter.adapter_id: adapter},
                    sleep_fn=lambda _: None,
                )

            common = {
                "text": text,
                "project_id": "cpcs-acceptance-project",
                "assets": _assets(text, root),
                "seed": 31,
            }
            variant = {
                **common,
                "overlays": [
                    {
                        "overlay_id": "overlay_acceptance_impact_shake",
                        "scope": "explicit_user_correction",
                        "priority": 0,
                        "values": {"camera": {"impact_shake_policy": "none"}},
                        "locks": [],
                    }
                ],
            }
            curated_before = _curated_snapshot(root)
            with mock.patch(
                "lab.application.service._application_work_root",
                return_value=operational,
            ), mock.patch(
                "lab.application.service._render_runner", side_effect=runner
            ):
                prepared_a = invoke(
                    _request("cpcs.production.prepare", common), root=root
                )
                prepared_b = invoke(
                    _request("cpcs.production.prepare", variant), root=root
                )
                self.assertEqual(prepared_a["status"], "success")
                self.assertEqual(prepared_b["status"], "success")
                score_a = prepared_a["result"]["score"]
                score_b = prepared_b["result"]["score"]
                build_a = prepared_a["result"]["build"]
                build_b = prepared_b["result"]["build"]
                self.assertNotEqual(build_a["build_id"], build_b["build_id"])

                controls_a = {
                    row["path"]: row for row in score_a["provider_neutral_controls"]
                }
                controls_b = {
                    row["path"]: row for row in score_b["provider_neutral_controls"]
                }
                delta_a = controls_a["camera.impact_shake_policy"]
                delta_b = controls_b["camera.impact_shake_policy"]
                self.assertEqual(delta_a["control_id"], delta_b["control_id"])
                self.assertNotEqual(delta_a["value"], delta_b["value"])
                self.assertEqual(
                    {
                        row["control_id"]: row["value"]
                        for row in score_a["provider_neutral_controls"]
                        if row["control_id"] != delta_a["control_id"]
                    },
                    {
                        row["control_id"]: row["value"]
                        for row in score_b["provider_neutral_controls"]
                        if row["control_id"] != delta_b["control_id"]
                    },
                )

                rendered = {}
                verified = {}
                for arm_id, score, build in (
                    ("a", score_a, build_a),
                    ("b", score_b, build_b),
                ):
                    create_arguments = {
                        "build_id": build["build_id"],
                        "idempotency_key": f"universal-acceptance-{arm_id}",
                        "poll_interval_seconds": 0,
                    }
                    created = invoke(
                        _request("cpcs.render.create", create_arguments),
                        role="operator",
                        root=root,
                    )
                    self.assertEqual(created["status"], "success")
                    job_id = created["result"]["job"]["job_id"]
                    run_arguments = {"job_id": job_id}
                    rendered[arm_id] = invoke(
                        _authorize("cpcs.render.run", run_arguments),
                        role="operator",
                        root=root,
                    )
                    self.assertEqual(rendered[arm_id]["status"], "success")
                    self.assertEqual(rendered[arm_id]["result"]["state"], "succeeded")
                    artifact = rendered[arm_id]["result"]["result"]["artifacts"][0]

                    def probe(path: Path, *, expected_sha256: str) -> dict:
                        self.assertEqual(
                            expected_sha256,
                            artifact["sha256"].removeprefix("sha256:"),
                        )
                        return {
                            "duration_s": 8.0,
                            "start_time_s": 0.0,
                            "width": 1280,
                            "height": 720,
                            "frame_rate": 24.0,
                            "probe_hash": sha256_value(
                                {"fixture": str(path.name), "arm": arm_id}
                            ),
                        }

                    verify_arguments = {
                        "build_id": build["build_id"],
                        "job_id": job_id,
                        "artifact_id": artifact["artifact_id"],
                        "evidence_bundle": _verification_evidence(
                            score,
                            rendered[arm_id]["result"],
                            arm_id=arm_id,
                        ),
                    }
                    with mock.patch(
                        "lab.verification.verify.probe_media", side_effect=probe
                    ):
                        verified[arm_id] = invoke(
                            _request("cpcs.verify.run", verify_arguments),
                            role="operator",
                            root=root,
                        )
                    self.assertEqual(verified[arm_id]["status"], "success")
                    self.assertEqual(
                        verified[arm_id]["result"]["report"]["overall_status"],
                        "pass",
                    )
                    replay = invoke(
                        _authorize("cpcs.render.run", run_arguments),
                        role="operator",
                        root=root,
                    )
                    self.assertEqual(replay["result"], rendered[arm_id]["result"])

                self.assertEqual(adapter.submit_count, 2)
                baseline_query = {
                    "goal": "dramatic action motivated camera",
                    "domain": "action",
                    "provider": "fake",
                    "model_version": "fixture",
                    "minimum_status": "ingested",
                }
                before_learning = invoke(
                    _request("cpcs.reason", baseline_query), root=root
                )
                self.assertEqual(before_learning["result"]["learned_weights"], [])

                delta_concept = "c_dramatic_action_motivated_camera"
                experiment_arguments = {
                    "flight_id": "flight_universal_acceptance",
                    "arms": [
                        {
                            "id": "a",
                            "build_id": build_a["build_id"],
                            "tested_delta": {
                                "concept_id": delta_concept,
                                "control_id": delta_a["control_id"],
                                "value": delta_a["value"],
                            },
                        },
                        {
                            "id": "b",
                            "build_id": build_b["build_id"],
                            "tested_delta": {
                                "concept_id": delta_concept,
                                "control_id": delta_b["control_id"],
                                "value": delta_b["value"],
                            },
                        },
                    ],
                    "classification": "isolated_comparison",
                    "metric_ids": ["creative_quality"],
                    "outcome_concept_ids": ["c_camera_keyframes"],
                    "provider": "fake",
                    "model_version": "fixture",
                    "sealed_at": "2027-01-15T07:00:00Z",
                }
                experiment = invoke(
                    _request("cpcs.experiment.prepare", experiment_arguments),
                    role="operator",
                    root=root,
                )
                experiment_replay = invoke(
                    _request("cpcs.experiment.prepare", experiment_arguments),
                    role="operator",
                    root=root,
                )
                self.assertEqual(experiment, experiment_replay)
                self.assertEqual(experiment["status"], "success")
                self.assertEqual(
                    experiment["result"]["differing_control_ids"],
                    [delta_a["control_id"]],
                )
                seal_arguments = {
                    "flight_draft": experiment["result"]["flight_draft"]
                }
                denied = invoke(
                    _request("cpcs.experiment.seal", seal_arguments),
                    role="curator",
                    root=root,
                )
                self.assertEqual(denied["error"]["code"], "permission_denied")
                sealed = invoke(
                    _authorize("cpcs.experiment.seal", seal_arguments),
                    role="curator",
                    root=root,
                )
                sealed_replay = invoke(
                    _authorize("cpcs.experiment.seal", seal_arguments),
                    role="curator",
                    root=root,
                )
                self.assertEqual(sealed, sealed_replay)
                self.assertEqual(sealed["status"], "success")

                runs = {}
                for arm_id, build, metric, verdict, rationale in (
                    (
                        "a",
                        build_a,
                        5,
                        "keep",
                        "The motivated impact response preserved action readability.",
                    ),
                    (
                        "b",
                        build_b,
                        1,
                        "reject",
                        "Removing the impact response weakened action readability.",
                    ),
                ):
                    job_id = rendered[arm_id]["result"]["job"]["job_id"]
                    artifact = rendered[arm_id]["result"]["result"]["artifacts"][0]
                    receipt_arguments = {
                        "receipt": {
                            "schema": "cpcs.experiment_receipt/1.0",
                            "flight_id": sealed["result"]["id"],
                            "arm_id": arm_id,
                            "build_dir": build["output_dir"],
                            "render_result": str(
                                operational
                                / "render"
                                / "jobs"
                                / job_id
                                / "render_result.json"
                            ),
                            "compliance_report": verified[arm_id]["result"]["output"],
                            "artifact_id": artifact["artifact_id"],
                            "metrics": {"creative_quality": metric},
                            "human_review": {
                                "review_id": f"review_acceptance_{arm_id}",
                                "reviewer_id": "director_fixture",
                                "verdict": verdict,
                                "rationale": rationale,
                                "reviewed_at": (
                                    "2027-01-15T09:00:00Z"
                                    if arm_id == "a"
                                    else "2027-01-15T09:01:00Z"
                                ),
                            },
                        }
                    }
                    runs[arm_id] = invoke(
                        _authorize("cpcs.record.render", receipt_arguments),
                        role="curator",
                        root=root,
                    )
                    self.assertEqual(runs[arm_id]["status"], "success")
                    run_replay = invoke(
                        _authorize("cpcs.record.render", receipt_arguments),
                        role="curator",
                        root=root,
                    )
                    self.assertEqual(run_replay, runs[arm_id])

                reflected = invoke(
                    _request("cpcs.reflect.rebuild", {}),
                    role="operator",
                    root=root,
                )
                reflected_replay = invoke(
                    _request("cpcs.reflect.rebuild", {}),
                    role="operator",
                    root=root,
                )
                self.assertEqual(reflected, reflected_replay)
                after_learning = invoke(
                    _request("cpcs.reason", baseline_query), root=root
                )
                causal = [
                    row
                    for row in after_learning["result"]["learned_weights"]
                    if row["evidence_scope"] == "causal_isolated_comparison"
                ]
                self.assertTrue(causal)
                self.assertEqual(
                    causal[0]["isolated_comparison"]["flight_id"],
                    sealed["result"]["id"],
                )
                self.assertEqual(
                    set(causal[0]["evidence"]),
                    {runs["a"]["result"]["id"], runs["b"]["result"]["id"]},
                )

            self.assertEqual(curated_before, _curated_snapshot(root))
            validation = validate_control_plane(root)
            self.assertEqual(validation["rebuild_determinism"], "pass")
            self.assertGreaterEqual(validation["learned_edges"], 1)


if __name__ == "__main__":
    unittest.main()
