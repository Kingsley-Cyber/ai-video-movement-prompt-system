from __future__ import annotations

import copy
import json
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
from lab.second_brain.tests.test_twelvelabs import FakeClient


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


def _semantic_extraction_response(prepared: dict) -> dict:
    packet = prepared["semantic_packets"][0]
    chunk = next(
        row
        for row in packet["passages"]
        if "decimal waypoint samples" in row["text"].lower()
    )
    evidence = lambda claim: [{"chunk_id": chunk["chunk_id"], "claim": claim}]
    return {
        "schema": "cpcs.semantic_extraction_response/1.0",
        "extractor": {
            "agent": "layer-o-semantic-worker",
            "model": "fixture-structured-extractor-1",
            "prompt_hash": "sha256:" + "b" * 64,
        },
        "packet_results": [
            {
                "packet_id": packet["packet_id"],
                "candidates": [
                    {
                        "candidate_key": "decimal_curvature_concept",
                        "proposal_type": "concept",
                        "suggested_id": "c_decimal_curvature_sampling",
                        "proposed_record": {
                            "kind": "technique",
                            "name": "Decimal curvature measurement sampling",
                            "what": "Preserve decimal waypoint samples when calculating per-hand average path curvature so small directional changes remain replayable.",
                            "use_when": "a per-hand Laban curvature measurement must retain small directional changes",
                            "nl_triggers": [
                                "decimal hand path curvature",
                                "decimal curvature samples",
                                "replayable per-hand curvature",
                            ],
                            "status": "ingested",
                            "evidence": [],
                            "source": ["file:curvature.md"],
                            "layer": "Laban Shape",
                        },
                        "evidence_refs": evidence(
                            "The passage defines decimal sampling for replayable per-hand curvature measurement."
                        ),
                    },
                    {
                        "candidate_key": "decimal_curvature_edge",
                        "proposal_type": "edge",
                        "suggested_id": None,
                        "proposed_record": {
                            "u": "c_decimal_curvature_sampling",
                            "v": "c_laban_shape_directional_curvature",
                            "type": "refines",
                            "context": "Laban curvature measurement sampling",
                            "authored_by": "local_source_proposal",
                            "note": "The sampling rule specializes the existing per-hand curvature measurement contract.",
                            "sources": [
                                {
                                    "ref": "file:curvature.md",
                                    "locator": chunk["locator"],
                                }
                            ],
                        },
                        "evidence_refs": evidence(
                            "The passage specializes the curvature measurement contract."
                        ),
                    },
                    {
                        "candidate_key": "decimal_curvature_mapping",
                        "proposal_type": "mapping",
                        "suggested_id": None,
                        "proposed_record": {
                            "concept_id": "c_decimal_curvature_sampling",
                            "target_type": "measurement_control",
                            "target_id": "motion.laban_shape_directional_curvature",
                            "encoding": "json",
                            "mapping": {
                                "sampling_precision": "preserve_source_decimals"
                            },
                            "loss": "low",
                            "provider": None,
                            "model_version": None,
                            "sources": ["file:curvature.md"],
                        },
                        "evidence_refs": evidence(
                            "The passage supports a decimal-preserving measurement-control mapping."
                        ),
                    },
                ],
            }
        ],
    }


def _promotion_review() -> dict:
    return {
        "source_verified": True,
        "source_locator_resolved": True,
        "duplicate_checked": True,
        "operationally_useful": True,
        "relationships_validated": True,
        "numeric_precision_supported": True,
        "reviewed_at": "2027-01-15T06:30:00Z",
        "notes": "Layer O fixture review against the exact authorized source locator.",
    }


def _pegasus_compliance_response(job: dict) -> dict:
    return {
        "finish_reason": "stop",
        "data": json.dumps(
            {
                "assessments": [
                    {
                        "metric_id": row["metric_id"],
                        "target_path": row["target_path"],
                        "verdict": "pass",
                        "observed": "AU06 and AU12 visibly co-activate in the generated performance.",
                        "start_s": 0.0,
                        "end_s": 4.0,
                        "confidence": 0.88,
                        "deviation": None,
                        "limitations": [
                            "Visible facial actions do not prove an internal emotional state."
                        ],
                    }
                    for row in job["verification_requirements"]
                ]
            },
            sort_keys=True,
        ),
    }


class UniversalAcceptanceTests(unittest.TestCase):
    def test_public_layer_o_research_to_controlled_learning_loop(self) -> None:
        text = (
            "Create a movement study with a Duchenne smile, a precise camera path, "
            "per-hand Laban directional curvature, and decimal hand-path sampling."
        )
        with tempfile.TemporaryDirectory() as directory:
            root = _fixture_root(Path(directory))
            operational = root / "work" / "application"
            research_folder = operational / "research"
            research_folder.mkdir(parents=True)
            (research_folder / "curvature.md").write_text(
                "# Decimal curvature sampling\n\n"
                "Preserve decimal waypoint samples when calculating per-hand average "
                "path curvature so the measurement can be replayed without rounding "
                "away small directional changes. This is a measurement-sampling rule, "
                "not proof that one curvature value is creatively superior.\n",
                encoding="utf-8",
            )
            (research_folder / "contract.json").write_text(
                json.dumps(
                    {
                        "scope": "per_hand",
                        "signal": "average_path_curvature",
                        "precision": "preserve_source_decimals",
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            pose_model = operational / "pose-landmarker.task"
            pose_model.write_bytes(b"layer-o-pose-model-fixture")
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

            curated_before = _curated_snapshot(root)
            with mock.patch(
                "lab.application.service._application_work_root",
                return_value=operational,
            ), mock.patch(
                "lab.application.service._render_runner", side_effect=runner
            ):
                extraction_arguments = {
                    "source_kind": "authorized_folder",
                    "folder": str(research_folder),
                    "research_goal": (
                        "decimal waypoint sampling for per-hand Laban curvature measurement"
                    ),
                    "rights_basis": "owner_authorized_test_fixture",
                }
                oriented = invoke(
                    _request("cpcs.distill.prepare", extraction_arguments),
                    role="operator",
                    root=root,
                )
                oriented_replay = invoke(
                    _request("cpcs.distill.prepare", extraction_arguments),
                    role="operator",
                    root=root,
                )
                self.assertEqual(oriented, oriented_replay)
                self.assertEqual(oriented["status"], "success")
                self.assertEqual(
                    {
                        row["extension"]
                        for row in oriented["result"]["inventory"]
                        if row["status"] == "parsed"
                    },
                    {".json", ".md"},
                )
                self.assertTrue(oriented["result"]["chunks"])
                self.assertTrue(oriented["result"]["semantic_packets"])
                extraction_arguments["semantic_response"] = (
                    _semantic_extraction_response(oriented["result"])
                )
                extracted = invoke(
                    _request("cpcs.distill.prepare", extraction_arguments),
                    role="operator",
                    root=root,
                )
                self.assertEqual(extracted["status"], "success")
                batch = extracted["result"]["distillation_batch"]
                distilled = invoke(
                    _request("cpcs.distill.run", {"batch": batch}),
                    role="operator",
                    root=root,
                )
                distilled_replay = invoke(
                    _request("cpcs.distill.run", {"batch": batch}),
                    role="operator",
                    root=root,
                )
                self.assertEqual(distilled, distilled_replay)
                self.assertEqual(distilled["status"], "success")
                staged = [
                    row
                    for row in distilled["result"]["candidate_decisions"]
                    if row["proposal_id"] is not None
                ]
                self.assertEqual(
                    {row["disposition"] for row in staged},
                    {"stage_new", "stage_relationship", "stage_mapping"},
                )
                review = invoke(
                    _request(
                        "cpcs.curate.review",
                        {"run_id": distilled["result"]["id"]},
                    ),
                    role="operator",
                    root=root,
                )
                self.assertEqual(review["status"], "success")
                durable_by_type = {
                    "concept": "c_decimal_curvature_sampling",
                    "edge": "edge_900001",
                    "mapping": "mapping_900001",
                }
                durable_ids = {
                    proposal["proposal_id"]: durable_by_type[
                        proposal["proposal_type"]
                    ]
                    for proposal in review["result"]["proposals"]
                }
                promotion_arguments = {
                    "run_id": distilled["result"]["id"],
                    "durable_ids": durable_ids,
                    "promoted_by": "owner-test",
                    "review": _promotion_review(),
                }
                denied_promotion = invoke(
                    _request("cpcs.curate.promote", promotion_arguments),
                    role="curator",
                    root=root,
                )
                self.assertEqual(
                    denied_promotion["error"]["code"], "permission_denied"
                )
                promoted = invoke(
                    _authorize("cpcs.curate.promote", promotion_arguments),
                    role="curator",
                    root=root,
                )
                self.assertEqual(promoted["status"], "success", promoted)
                self.assertEqual(
                    set(promoted["result"]["promoted_ids"]),
                    set(durable_by_type.values()),
                )
                indexed = invoke(
                    _request("cpcs.reflect.rebuild", {}),
                    role="operator",
                    root=root,
                )
                indexed_replay = invoke(
                    _request("cpcs.reflect.rebuild", {}),
                    role="operator",
                    root=root,
                )
                self.assertEqual(indexed, indexed_replay)
                self.assertIn(
                    "indexes/catalog.json", indexed["result"]["outputs"]
                )
                curated_after_promotion = _curated_snapshot(root)
                self.assertNotEqual(curated_before, curated_after_promotion)
                new_concept = next(
                    row
                    for row in read_jsonl(root / "lab" / "concepts.jsonl")
                    if row["id"] == "c_decimal_curvature_sampling"
                )
                self.assertEqual(
                    new_concept["provenance"]["origin"], "local_source"
                )
                discovered = invoke(
                    _request(
                        "cpcs.reason",
                        {
                            "goal": "decimal hand path curvature",
                            "minimum_status": "ingested",
                        },
                    ),
                    root=root,
                )
                self.assertIn(
                    "c_decimal_curvature_sampling",
                    {
                        row["id"]
                        for row in discovered["result"]["selected_concepts"]
                    },
                )

                common = {
                    "text": text,
                    "project_id": "cpcs-acceptance-project",
                    "assets": _assets(text, root),
                    "seed": 31,
                }
                arm_a_request = {
                    **common,
                    "overlays": [
                        {
                            "overlay_id": "overlay_acceptance_camera_path",
                            "scope": "explicit_user_correction",
                            "priority": 0,
                            "values": {"camera": {"movement": "slow_lateral_track"}},
                            "locks": [],
                        }
                    ],
                }
                arm_b_request = copy.deepcopy(arm_a_request)
                arm_b_request["overlays"][0]["values"]["camera"]["movement"] = (
                    "locked_off"
                )
                prepared_a = invoke(
                    _request("cpcs.production.prepare", arm_a_request), root=root
                )
                prepared_b = invoke(
                    _request("cpcs.production.prepare", arm_b_request), root=root
                )
                self.assertEqual(prepared_a["status"], "success")
                self.assertEqual(prepared_b["status"], "success")
                score_a = prepared_a["result"]["score"]
                score_b = prepared_b["result"]["score"]
                build_a = prepared_a["result"]["build"]
                build_b = prepared_b["result"]["build"]
                self.assertNotEqual(build_a["build_id"], build_b["build_id"])
                self.assertIn(
                    "c_decimal_curvature_sampling",
                    score_a["provenance"]["concept_ids"],
                )
                self.assertEqual(
                    score_a["profile_resolution"]["kernel_profile"],
                    score_b["profile_resolution"]["kernel_profile"],
                )

                controls_a = {
                    row["path"]: row for row in score_a["provider_neutral_controls"]
                }
                controls_b = {
                    row["path"]: row for row in score_b["provider_neutral_controls"]
                }
                delta_a = controls_a["camera.movement"]
                delta_b = controls_b["camera.movement"]
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
                    artifact_path = (
                        operational
                        / "render"
                        / "jobs"
                        / job_id
                        / artifact["relative_path"]
                    )

                    asset_preparation = invoke(
                        _request(
                            "cpcs.verify.asset.prepare",
                            {
                                "build_id": build["build_id"],
                                "job_id": job_id,
                                "artifact_id": artifact["artifact_id"],
                                "rights_scope": "original",
                            },
                        ),
                        role="operator",
                        root=root,
                    )
                    self.assertEqual(asset_preparation["status"], "success")
                    asset_arguments = {
                        "job": asset_preparation["result"]["job"]
                    }
                    with mock.patch(
                        "lab.second_brain.src.pegasus._active_client",
                        return_value=FakeClient(),
                    ):
                        uploaded = invoke(
                            _authorize("cpcs.analyze.run", asset_arguments),
                            role="operator",
                            root=root,
                        )
                    self.assertEqual(uploaded["status"], "success")
                    provider_asset_ref = uploaded["result"]["asset"]["id"]
                    analysis_preparation = invoke(
                        _request(
                            "cpcs.verify.analysis.prepare",
                            {
                                "build_id": build["build_id"],
                                "job_id": job_id,
                                "artifact_id": artifact["artifact_id"],
                                "provider_asset_ref": provider_asset_ref,
                                "rights_scope": "original",
                            },
                        ),
                        role="operator",
                        root=root,
                    )
                    self.assertEqual(analysis_preparation["status"], "success")
                    analysis_job = analysis_preparation["result"]["job"]
                    self.assertEqual(
                        analysis_job["profile_id"],
                        "pegasus.score_compliance/1.0",
                    )
                    analysis_arguments = {"job": analysis_job}
                    with mock.patch(
                        "lab.second_brain.src.pegasus._active_client",
                        return_value=FakeClient(
                            analyze_response=_pegasus_compliance_response(
                                analysis_job
                            )
                        ),
                    ):
                        analyzed = invoke(
                            _authorize("cpcs.analyze.run", analysis_arguments),
                            role="operator",
                            root=root,
                        )
                    self.assertEqual(analyzed["status"], "success")
                    self.assertTrue(analyzed["result"]["observations"])
                    self.assertEqual(
                        {
                            row["evidence_class"]
                            for row in analyzed["result"]["observations"]
                        },
                        {"interpreted"},
                    )

                    measurement_preparation = invoke(
                        _request(
                            "cpcs.measure.pose.prepare",
                            {
                                "source_id": artifact["artifact_id"],
                                "asset_ref": artifact["artifact_id"],
                                "local_path": str(artifact_path),
                                "rights_scope": "original",
                                "authorized_interval": {
                                    "start_s": 0.0,
                                    "end_s": 8.0,
                                },
                                "model_path": str(pose_model),
                                "model_version": "pose-fixture-1",
                                "created_at": (
                                    "2027-01-15T08:00:00Z"
                                    if arm_id == "a"
                                    else "2027-01-15T08:01:00Z"
                                ),
                                "keyframe_interval_s": 0.5,
                            },
                        ),
                        role="operator",
                        root=root,
                    )
                    self.assertEqual(measurement_preparation["status"], "success")

                    def frames(_path: Path, _interval: dict, _stride: int):
                        return [
                            (0, 0.0, 0),
                            (1, 2.0, 1),
                            (2, 4.0, 2),
                            (3, 6.0, 3),
                        ]

                    left_path = [
                        (0.20, 0.50),
                        (0.30, 0.40),
                        (0.45, 0.40),
                        (0.55, 0.50),
                    ]
                    right_path = [
                        (0.70, 0.50),
                        (0.60, 0.50),
                        (0.50, 0.50),
                        (0.40, 0.50),
                    ]

                    def detector(frame: int, _timestamp_ms: int):
                        return [
                            {
                                "left_hip": (0.45, 0.70, 0.98),
                                "right_hip": (0.55, 0.70, 0.98),
                                "left_wrist": (*left_path[frame], 0.95),
                                "right_wrist": (*right_path[frame], 0.95),
                            }
                        ]

                    with mock.patch(
                        "lab.second_brain.src.measurement._opencv_frames",
                        side_effect=frames,
                    ), mock.patch(
                        "lab.second_brain.src.measurement._mediapipe_detector",
                        return_value=(detector, lambda: None),
                    ):
                        measured = invoke(
                            _request(
                                "cpcs.measure.pose.run",
                                {"job": measurement_preparation["result"]},
                            ),
                            role="operator",
                            root=root,
                        )
                    self.assertEqual(measured["status"], "success")
                    measurement_batch = measured["result"]["batch"]
                    measurement_arguments = {"batch": measurement_batch}
                    recorded_measurements = invoke(
                        _authorize(
                            "cpcs.record.measurement", measurement_arguments
                        ),
                        role="curator",
                        root=root,
                    )
                    self.assertEqual(recorded_measurements["status"], "success")
                    measurement_replay = invoke(
                        _authorize(
                            "cpcs.record.measurement", measurement_arguments
                        ),
                        role="curator",
                        root=root,
                    )
                    self.assertEqual(measurement_replay["status"], "success")
                    self.assertEqual(
                        measurement_replay["result"]["disposition"],
                        "already_present",
                    )
                    self.assertEqual(
                        measurement_replay["result"]["records"],
                        recorded_measurements["result"]["records"],
                    )
                    wrist_ids = sorted(
                        row["id"]
                        for row in recorded_measurements["result"]["records"]
                        if row["claim"]["joint"]
                        in {"left_wrist", "right_wrist"}
                    )
                    self.assertEqual(len(wrist_ids), 2)
                    normalized = invoke(
                        _request(
                            "cpcs.measure.normalize",
                            {
                                "source": measurement_batch["source"],
                                "authorized_interval": measurement_batch[
                                    "authorized_interval"
                                ],
                                "measurement_observation_ids": wrist_ids,
                            },
                        ),
                        role="operator",
                        root=root,
                    )
                    self.assertEqual(normalized["status"], "success")

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
                        "observations": [
                            *analyzed["result"]["observations"],
                            *normalized["result"]["observations"],
                        ],
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
                    trace = verified[arm_id]["result"]["report"]["evidence_trace"]
                    self.assertEqual(
                        {row["lane"] for row in trace},
                        {"measurement", "semantic"},
                    )
                    self.assertEqual(
                        {row["assertion_origin"] for row in trace},
                        {"deterministic_comparator", "supplied"},
                    )
                    replay = invoke(
                        _authorize("cpcs.render.run", run_arguments),
                        role="operator",
                        root=root,
                    )
                    self.assertEqual(replay["result"], rendered[arm_id]["result"])

                self.assertEqual(adapter.submit_count, 2)
                baseline_query = {
                    "goal": "camera path decimal hand path curvature",
                    "provider": "fake",
                    "model_version": "fixture",
                    "minimum_status": "ingested",
                }
                before_learning = invoke(
                    _request("cpcs.reason", baseline_query), root=root
                )
                self.assertEqual(before_learning["result"]["learned_weights"], [])

                delta_concept = "c_camera_keyframes"
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
                    "outcome_concept_ids": ["c_decimal_curvature_sampling"],
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
                        "The slow lateral camera path supported the movement study.",
                    ),
                    (
                        "b",
                        build_b,
                        1,
                        "reject",
                        "The locked camera path reduced the intended spatial reading.",
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

            self.assertEqual(curated_after_promotion, _curated_snapshot(root))
            validation = validate_control_plane(root)
            self.assertEqual(validation["rebuild_determinism"], "pass")
            self.assertGreaterEqual(validation["learned_edges"], 1)
            self.assertEqual(validation["immutable"]["run"], 2)
            self.assertGreaterEqual(
                validation["immutable"]["measurement_observation"], 4
            )


if __name__ == "__main__":
    unittest.main()
