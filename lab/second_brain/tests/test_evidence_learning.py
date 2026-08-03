from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from lab.compiler.build import write_build_directory
from lab.compiler.provenance import canonical_json_bytes, sha256_bytes, sha256_value
from lab.compiler.tests.test_build import build_for, ready_score
from lab.second_brain.src.query import default_request, reason
from lab.second_brain.src.record import (
    append_experiment_receipt,
    append_experiment_run,
    seal_flight,
)
from lab.second_brain.src.reflect import rebuild
from lab.second_brain.src.validate import REPO_ROOT, ValidationFailure, read_jsonl
from lab.second_brain.tests.helpers import make_root
from lab.verification.verify import make_assertion, make_evidence_source, verify_render


def _curated_snapshot(root: Path) -> dict[str, bytes]:
    paths = [root / "lab/concepts.jsonl"]
    paths.extend(
        path
        for path in (root / "lab/second_brain/curated").rglob("*")
        if path.is_file()
    )
    return {
        str(path.relative_to(root)): path.read_bytes() for path in sorted(paths)
    }


class ControlledEvidenceLearningTests(unittest.TestCase):
    def _source(
        self,
        *,
        source_id: str,
        lane: str,
        artifact_id: str,
        artifact_hash: str,
    ) -> dict[str, Any]:
        if lane == "human_review":
            return make_evidence_source(
                {
                    "schema": "cpcs.human_verification_review/1.0",
                    "review_id": source_id,
                    "artifact_id": artifact_id,
                    "reviewer_id": "verification_fixture",
                    "created_at": "2027-01-15T08:00:00Z",
                    "notes": "Bounded fixture review of the generated artifact.",
                },
                source_type="human_review",
            )
        measured = lane == "measurement"
        return make_evidence_source(
            {
                "schema": "cpcs.normalized_video_observation/1.0",
                "observation_id": source_id,
                "source_id": artifact_id,
                "source_sha256": artifact_hash.removeprefix("sha256:"),
                "interval": {"start_s": 0.0, "end_s": 4.0},
                "subject_refs": [],
                "layer": "measurement" if measured else "camera",
                "claim": {"label": "fixture comparison", "description": "bounded"},
                "evidence_class": "detected" if measured else "interpreted",
                "confidence": 0.9,
                "alternatives": [],
                "provenance": {
                    "surface": "local_measurement" if measured else "pegasus_analyze",
                    "model": "fixture-observer",
                    "model_version": "1.0",
                    "profile_id": "local.fixture/1.0",
                    "request_hash": "sha256:" + "3" * 64,
                    "raw_response_hash": "sha256:" + "4" * 64,
                },
            },
            source_type="normalized_video_observation",
        )

    def _evidence_bundle(
        self,
        score: dict[str, Any],
        *,
        job_id: str,
        build_id: str,
        artifact_id: str,
        artifact_hash: str,
    ) -> dict[str, Any]:
        controls = {
            row["path"]: row for row in score["provider_neutral_controls"]
        }
        sources = []
        assertions = []
        for requirement_index, requirement in enumerate(
            score["verification_requirements"]
        ):
            for target_index, target_path in enumerate(requirement["target_paths"]):
                lane = (
                    "measurement"
                    if requirement["observability"] == "measured"
                    else requirement["observability"]
                )
                source_id = (
                    f"human_review_{requirement_index}_{target_index}"
                    if lane == "human_review"
                    else f"vog_obs_learning_{requirement_index}_{target_index}_{lane}"
                )
                sources.append(
                    self._source(
                        source_id=source_id,
                        lane=lane,
                        artifact_id=artifact_id,
                        artifact_hash=artifact_hash,
                    )
                )
                assertions.append(
                    make_assertion(
                        metric_id=requirement["metric_id"],
                        target_path=target_path,
                        source_ref=source_id,
                        verdict="pass",
                        observed=copy.deepcopy(controls[target_path]["value"]),
                        interval={"start_s": 0.0, "end_s": 4.0},
                    )
                )
        return {
            "schema": "cpcs.verification_evidence_bundle/1.0",
            "job_id": job_id,
            "build_id": build_id,
            "artifact_id": artifact_id,
            "artifact_sha256": artifact_hash,
            "sources": sources,
            "assertions": assertions,
        }

    def _render_and_verify(
        self,
        workspace: Path,
        tag: str,
        score: dict[str, Any],
    ) -> tuple[Path, Path, Path, dict[str, Any], dict[str, Any]]:
        _, artifacts = build_for(score)
        build_dir = workspace / tag / "build"
        write_build_directory(artifacts, build_dir)
        manifest = json.loads(artifacts["build_manifest.json"])
        tag_hash = hashlib.sha256(tag.encode()).hexdigest()
        job_id = "render_job_" + tag_hash[:24]
        artifact_id = "artifact_000"
        media = b"\x00\x00\x00\x18ftypmp42controlled-evidence-" + tag.encode()
        media_hash = sha256_bytes(media)
        job_root = workspace / tag / "render"
        artifact_path = job_root / "artifacts" / "artifact_000.mp4"
        artifact_path.parent.mkdir(parents=True)
        artifact_path.write_bytes(media)
        result = {
            "schema": "cpcs.render_result/1.0",
            "job_id": job_id,
            "build_id": manifest["build_id"],
            "build_hash": manifest["build_hash"],
            "provider": "fixture",
            "model": "fixture-1",
            "operation_id": "operation_" + tag,
            "status": "succeeded",
            "artifacts": [
                {
                    "artifact_id": artifact_id,
                    "relative_path": "artifacts/artifact_000.mp4",
                    "source_uri": None,
                    "mime_type": "video/mp4",
                    "size_bytes": len(media),
                    "sha256": media_hash,
                }
            ],
            "expected_media": {
                "duration_seconds": 8,
                "aspect_ratio": "16:9",
                "resolution": "720p",
                "sample_count": 1,
            },
            "provider_response_hash": "sha256:" + tag_hash,
            "completed_at": "2027-01-15T08:00:00Z",
        }
        result_path = job_root / "render_result.json"
        result_path.write_bytes(canonical_json_bytes(result))
        evidence = self._evidence_bundle(
            score,
            job_id=job_id,
            build_id=manifest["build_id"],
            artifact_id=artifact_id,
            artifact_hash=media_hash,
        )

        def probe(path: Path, *, expected_sha256: str) -> dict[str, Any]:
            self.assertEqual(path, artifact_path.resolve())
            self.assertEqual(expected_sha256, media_hash.removeprefix("sha256:"))
            return {
                "duration_s": 8.0,
                "start_time_s": 0.0,
                "width": 1280,
                "height": 720,
                "frame_rate": 24.0,
                "probe_hash": sha256_value({"probe": tag}),
            }

        report = verify_render(
            build_dir,
            result_path,
            artifact_id,
            evidence,
            probe_fn=probe,
        )
        self.assertEqual(report["overall_status"], "pass")
        report_path = job_root / "compliance_report.json"
        report_path.write_bytes(canonical_json_bytes(report))
        return build_dir, result_path, report_path, manifest, report

    def test_verified_isolated_experiment_rebuilds_traceable_provider_calibration(self) -> None:
        text = "Create a multi-actor action scene with readable screen direction"
        score_a = ready_score(text)
        score_b = ready_score(
            text,
            overlays=[
                {
                    "overlay_id": "overlay_isolated_impact_shake",
                    "scope": "explicit_user_correction",
                    "priority": 0,
                    "values": {"camera": {"impact_shake_policy": "none"}},
                    "locks": [],
                }
            ],
        )
        delta_a = next(
            row
            for row in score_a["provider_neutral_controls"]
            if row["path"] == "camera.impact_shake_policy"
        )
        delta_b = next(
            row
            for row in score_b["provider_neutral_controls"]
            if row["path"] == "camera.impact_shake_policy"
        )
        self.assertEqual(delta_a["control_id"], delta_b["control_id"])
        self.assertNotEqual(delta_a["value"], delta_b["value"])
        other_a = {
            row["control_id"]: row["value"]
            for row in score_a["provider_neutral_controls"]
            if row["control_id"] != delta_a["control_id"]
        }
        other_b = {
            row["control_id"]: row["value"]
            for row in score_b["provider_neutral_controls"]
            if row["control_id"] != delta_b["control_id"]
        }
        self.assertEqual(other_a, other_b)

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            build_a, result_a, report_a, manifest_a, report_value_a = (
                self._render_and_verify(workspace, "arm-a", score_a)
            )
            build_b, result_b, report_b, manifest_b, _ = self._render_and_verify(
                workspace, "arm-b", score_b
            )
            concepts = read_jsonl(REPO_ROOT / "lab/concepts.jsonl")
            root = make_root(workspace / "controlled", concepts)
            self.assertEqual(manifest_a["concept_ids"], manifest_b["concept_ids"])
            delta_concept = "c_dramatic_action_motivated_camera"
            self.assertIn(delta_concept, manifest_a["concept_ids"])
            flight = seal_flight(
                {
                    "id": "flight_controlled_render",
                    "intent_id": None,
                    "intent_class": "action",
                    "arms": [
                        {
                            "id": "a",
                            "paradigm": "universal_score",
                            "tested_delta": {
                                "concept_id": delta_concept,
                                "control_id": delta_a["control_id"],
                                "value": delta_a["value"],
                            },
                        },
                        {
                            "id": "b",
                            "paradigm": "universal_score",
                            "tested_delta": {
                                "concept_id": delta_concept,
                                "control_id": delta_b["control_id"],
                                "value": delta_b["value"],
                            },
                        },
                    ],
                    "design": {
                        "classification": "isolated_comparison",
                        "causal_claim_policy": "isolated_only",
                        "metric_ids": ["creative_quality"],
                        "outcome_concept_ids": ["c_camera_keyframes"],
                    },
                    "concept_ids": manifest_a["concept_ids"],
                    "provider": "fixture",
                    "model_version": "fixture-1",
                    "seed": manifest_a["seed"],
                    "compiler_settings": {"version": manifest_a["compiler_version"]},
                    "sealed_at": "2027-01-15T07:00:00Z",
                    "legacy": None,
                },
                root,
            )
            baseline = reason(
                default_request(
                    "dramatic action motivated camera",
                    domain="action",
                    provider="fixture",
                    model_version="fixture-1",
                    minimum_status="ingested",
                ),
                root,
            )
            self.assertEqual(baseline["learned_weights"], [])
            before = _curated_snapshot(root)
            review_a = {
                "review_id": "review_controlled_a",
                "reviewer_id": "director_fixture",
                "verdict": "keep",
                "rationale": "The decaying impact response preserved readable action.",
                "reviewed_at": "2027-01-15T09:00:00Z",
            }
            receipt_a = {
                "schema": "cpcs.experiment_receipt/1.0",
                "flight_id": flight["id"],
                "arm_id": "a",
                "build_dir": str(build_a),
                "render_result": str(result_a),
                "compliance_report": str(report_a),
                "artifact_id": "artifact_000",
                "metrics": {"creative_quality": 5},
                "human_review": review_a,
            }
            receipt_path = workspace / "receipt-a.json"
            receipt_path.write_bytes(canonical_json_bytes(receipt_a))
            command = [
                sys.executable,
                "-m",
                "lab.second_brain.src.record",
                "experiment",
                str(receipt_path),
                "--root",
                str(root),
            ]
            first_process = subprocess.run(
                command,
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            run_a = json.loads(first_process.stdout)
            retry_process = subprocess.run(
                command,
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            retry = json.loads(retry_process.stdout)
            self.assertEqual(run_a, retry)
            self.assertEqual(
                len(read_jsonl(root / "lab/second_brain/immutable/runs.jsonl")), 1
            )
            malformed_receipt = {**receipt_a, "provider_prompt": "forbidden"}
            with self.assertRaisesRegex(ValidationFailure, "experiment_receipt"):
                append_experiment_receipt(malformed_receipt, root)
            tampered_report = copy.deepcopy(report_value_a)
            tampered_report["overall_status"] = "fail"
            tampered_path = workspace / "tampered_report.json"
            tampered_path.write_bytes(canonical_json_bytes(tampered_report))
            with self.assertRaisesRegex(
                ValidationFailure, "compliance report content identity"
            ):
                append_experiment_run(
                    flight_id=flight["id"],
                    arm_id="a",
                    build_dir=build_a,
                    render_result_path=result_a,
                    compliance_report_path=tampered_path,
                    artifact_id="artifact_000",
                    metrics={"creative_quality": 5},
                    human_review=review_a,
                    root=root,
                )
            symlinked_report = workspace / "symlinked-report.json"
            symlinked_report.symlink_to(report_a)
            with self.assertRaisesRegex(ValidationFailure, "cannot be a symlink"):
                append_experiment_run(
                    flight_id=flight["id"],
                    arm_id="a",
                    build_dir=build_a,
                    render_result_path=result_a,
                    compliance_report_path=symlinked_report,
                    artifact_id="artifact_000",
                    metrics={"creative_quality": 5},
                    human_review=review_a,
                    root=root,
                )
            run_b = append_experiment_run(
                flight_id=flight["id"],
                arm_id="b",
                build_dir=build_b,
                render_result_path=result_b,
                compliance_report_path=report_b,
                artifact_id="artifact_000",
                metrics={"creative_quality": 1},
                human_review={
                    "review_id": "review_controlled_b",
                    "reviewer_id": "director_fixture",
                    "verdict": "reject",
                    "rationale": "Removing the impact response weakened action readability.",
                    "reviewed_at": "2027-01-15T09:01:00Z",
                },
                root=root,
            )
            first = rebuild(root)
            second = rebuild(root)
            self.assertEqual(first, second)
            weights = json.loads(
                (root / "lab/second_brain/derived/weights.json").read_text()
            )
            causal = [
                edge
                for edge in weights["edges"]
                if edge["type"] == "promotes" and edge["u"] == delta_concept
            ]
            self.assertEqual(len(causal), 1)
            self.assertEqual(causal[0]["v"], "c_camera_keyframes")
            effect = causal[0]["isolated_comparison"]
            self.assertEqual(effect["winner"]["run_id"], run_a["id"])
            self.assertEqual(effect["loser"]["run_id"], run_b["id"])
            self.assertEqual(
                effect["winner"]["artifact_sha256"], run_a["output_artifact_hash"]
            )
            self.assertEqual(
                effect["loser"]["artifact_sha256"], run_b["output_artifact_hash"]
            )
            catalog = json.loads(
                (
                    root
                    / "lab/second_brain/derived/indexes/catalog.json"
                ).read_text()
            )
            calibration = catalog["provider_performance"]["fixture::fixture-1"]
            self.assertEqual(calibration["calibration_status"], "causal_signal_available")
            self.assertEqual(calibration["causal_run_ids"], sorted([run_a["id"], run_b["id"]]))
            self.assertEqual(
                catalog["experiments"][flight["id"]]["design_classification"],
                "isolated_comparison",
            )
            after = reason(
                default_request(
                    "dramatic action motivated camera",
                    domain="action",
                    provider="fixture",
                    model_version="fixture-1",
                    minimum_status="ingested",
                ),
                root,
            )
            causal_trace = [
                row
                for row in after["learned_weights"]
                if row["evidence_scope"] == "causal_isolated_comparison"
            ]
            self.assertTrue(causal_trace)
            self.assertTrue(
                any(row["isolated_comparison"]["winner"]["artifact_sha256"] == run_a["output_artifact_hash"] for row in causal_trace)
            )
            other_provider = reason(
                default_request(
                    "dramatic action motivated camera",
                    domain="action",
                    provider="other_provider",
                    model_version="fixture-1",
                    minimum_status="ingested",
                ),
                root,
            )
            self.assertFalse(
                any(
                    row.get("evidence_scope") == "causal_isolated_comparison"
                    for row in other_provider["learned_weights"]
                )
            )
            self.assertEqual(before, _curated_snapshot(root))


if __name__ == "__main__":
    unittest.main()
