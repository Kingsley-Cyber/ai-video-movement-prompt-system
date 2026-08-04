from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from lab.compiler.build import write_build_directory
from lab.compiler.provenance import canonical_json_bytes, sha256_bytes, sha256_value
from lab.compiler.tests.test_build import build_for, ready_score
from lab.compiler.tests.test_score import authority_snapshot
from lab.verification.verify import (
    build_verification_evidence_bundle,
    make_assertion,
    make_evidence_source,
    make_verification_analysis_job,
    make_verification_asset_job,
    validate_verification_configuration,
    verify_render,
)


class VerificationFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name)
        self.score = ready_score(
            "Show how this device works in a clear educational video"
        )
        _, artifacts = build_for(self.score, creative_mode="diagnostic")
        self.build_dir = self.workspace / "build"
        write_build_directory(artifacts, self.build_dir)
        self.manifest = json.loads(artifacts["build_manifest.json"])
        self.job_id = "render_job_" + "1" * 24
        self.artifact_id = "artifact_000"
        self.media = b"\x00\x00\x00\x18ftypmp42verification-fixture"
        self.media_hash = sha256_bytes(self.media)
        self.job_root = self.workspace / "render_job"
        artifact_path = self.job_root / "artifacts/artifact_000.mp4"
        artifact_path.parent.mkdir(parents=True)
        artifact_path.write_bytes(self.media)
        self.result_path = self.job_root / "render_result.json"
        self.render_result = {
            "schema": "cpcs.render_result/1.0",
            "job_id": self.job_id,
            "build_id": self.manifest["build_id"],
            "build_hash": self.manifest["build_hash"],
            "provider": "fixture",
            "model": "fixture",
            "operation_id": "operation_fixture",
            "status": "succeeded",
            "artifacts": [
                {
                    "artifact_id": self.artifact_id,
                    "relative_path": "artifacts/artifact_000.mp4",
                    "source_uri": None,
                    "mime_type": "video/mp4",
                    "size_bytes": len(self.media),
                    "sha256": self.media_hash,
                }
            ],
            "expected_media": {
                "duration_seconds": 8,
                "aspect_ratio": "16:9",
                "resolution": "720p",
                "sample_count": 1,
            },
            "provider_response_hash": "sha256:" + "2" * 64,
            "completed_at": "2027-01-15T08:00:00Z",
        }
        self.result_path.write_bytes(canonical_json_bytes(self.render_result))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def probe(self, path: Path, *, expected_sha256: str) -> dict[str, Any]:
        self.assertEqual(
            path,
            (self.job_root / "artifacts/artifact_000.mp4").resolve(),
        )
        self.assertEqual(expected_sha256, self.media_hash.removeprefix("sha256:"))
        return {
            "duration_s": 8.0,
            "start_time_s": 0.0,
            "width": 1280,
            "height": 720,
            "frame_rate": 24.0,
            "probe_hash": sha256_value({"probe": "fixture-8s-720p-24fps"}),
        }

    def _normalized_source(
        self,
        source_id: str,
        *,
        lane: str,
        interval: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        measurement = lane == "measurement"
        record = {
            "schema": "cpcs.normalized_video_observation/1.0",
            "observation_id": source_id,
            "source_id": self.artifact_id,
            "source_sha256": self.media_hash.removeprefix("sha256:"),
            "interval": interval or {"start_s": 0.0, "end_s": 4.0},
            "subject_refs": [],
            "layer": "measurement" if measurement else "marketing",
            "claim": {"label": "metric comparison", "description": "fixture"},
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
        return make_evidence_source(
            record, source_type="normalized_video_observation"
        )

    def _human_source(self, source_id: str) -> dict[str, Any]:
        return make_evidence_source(
            {
                "schema": "cpcs.human_verification_review/1.0",
                "review_id": source_id,
                "artifact_id": self.artifact_id,
                "reviewer_id": "reviewer_fixture",
                "created_at": "2027-01-15T08:00:00Z",
                "notes": "Fixture review of observable output only.",
            },
            source_type="human_review",
        )

    def evidence(
        self,
        *,
        overrides: dict[tuple[str, str], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        overrides = overrides or {}
        sources: list[dict[str, Any]] = []
        assertions: list[dict[str, Any]] = []
        controls = {
            row["path"]: row for row in self.score["provider_neutral_controls"]
        }
        for requirement_index, requirement in enumerate(
            self.score["verification_requirements"]
        ):
            for target_index, target_path in enumerate(requirement["target_paths"]):
                override = overrides.get((requirement["metric_id"], target_path), {})
                lane = override.get(
                    "lane",
                    "measurement"
                    if requirement["observability"] == "measured"
                    else requirement["observability"],
                )
                source_id = (
                    f"human_review_{requirement_index}_{target_index}"
                    if lane == "human_review"
                    else f"vog_obs_verification_{requirement_index}_{target_index}_{lane}"
                )
                source = (
                    self._human_source(source_id)
                    if lane == "human_review"
                    else self._normalized_source(
                        source_id,
                        lane=lane,
                        interval=override.get("source_interval"),
                    )
                )
                if (
                    lane == "measurement"
                    and requirement["method"] == "product_visibility_duty_cycle"
                ):
                    record = copy.deepcopy(source["record"])
                    record["claim"] = {
                        "metric_id": requirement["metric_id"],
                        "method": requirement["method"],
                        "target_path": target_path,
                        "visible_seconds": 2.0,
                        "total_seconds": 4.0,
                        "duty_cycle": 0.5,
                    }
                    source = make_evidence_source(
                        record, source_type="normalized_video_observation"
                    )
                sources.append(source)
                if (
                    lane == "measurement"
                    and requirement["method"] == "product_visibility_duty_cycle"
                ):
                    continue
                verdict = override.get("verdict", "pass")
                observed = override.get("observed", controls[target_path]["value"])
                assertions.append(
                    make_assertion(
                        metric_id=requirement["metric_id"],
                        target_path=target_path,
                        source_ref=source_id,
                        verdict=verdict,
                        observed=observed,
                        interval=override.get("interval", {"start_s": 0.0, "end_s": 4.0}),
                        deviation=override.get("deviation"),
                        limitations=override.get("limitations", []),
                    )
                )
        return {
            "schema": "cpcs.verification_evidence_bundle/1.0",
            "job_id": self.job_id,
            "build_id": self.manifest["build_id"],
            "artifact_id": self.artifact_id,
            "artifact_sha256": self.media_hash,
            "sources": sources,
            "assertions": assertions,
        }

    def verify(
        self,
        evidence: dict[str, Any],
        *,
        probe: Any = None,
    ) -> dict[str, Any]:
        return verify_render(
            self.build_dir,
            self.result_path,
            self.artifact_id,
            evidence,
            probe_fn=probe or self.probe,
        )


class RenderVerificationTests(VerificationFixture):
    def test_score_bound_analysis_job_and_observations_build_evidence_without_manual_mapping(self) -> None:
        asset_job = make_verification_asset_job(
            self.build_dir,
            self.result_path,
            self.artifact_id,
            rights_scope="original",
        )
        self.assertEqual(asset_job["source"]["sha256"], self.media_hash.removeprefix("sha256:"))
        self.assertEqual(
            Path(asset_job["source"]["file_path"]),
            (self.job_root / "artifacts/artifact_000.mp4").resolve(),
        )
        job = make_verification_analysis_job(
            self.build_dir,
            self.result_path,
            self.artifact_id,
            provider_asset_ref="asset_render_fixture",
            rights_scope="original",
        )
        self.assertEqual(job["profile_id"], "pegasus.score_compliance/1.0")
        self.assertEqual(len(job["verification_requirements"]), 2)
        observations: list[dict[str, Any]] = []
        for index, requirement in enumerate(job["verification_requirements"]):
            record = self._normalized_source(
                f"vog_obs_bridge_semantic_{index}", lane="semantic"
            )["record"]
            record["claim"] = {
                "metric_id": requirement["metric_id"],
                "target_path": requirement["target_path"],
                "method": requirement["method"],
                "verdict": "pass",
                "observed": "visible sequence matches",
                "deviation": None,
                "limitations": ["Semantic comparison does not establish exact kinematics."],
            }
            observations.append(record)
        measurement = next(
            row["record"]
            for row in self.evidence()["sources"]
            if row["record"].get("claim", {}).get("metric_id")
            == "metric_product_visibility"
        )
        observations.append(measurement)
        bundle = build_verification_evidence_bundle(
            self.build_dir,
            self.result_path,
            self.artifact_id,
            observations,
        )
        replay = build_verification_evidence_bundle(
            self.build_dir,
            self.result_path,
            self.artifact_id,
            list(reversed(observations)),
        )
        self.assertEqual(bundle, replay)
        self.assertEqual(len(bundle["assertions"]), 2)
        report = self.verify(bundle)
        self.assertEqual(report["overall_status"], "pass")

    def test_configuration_and_all_pass_report_are_deterministic_and_read_only(self) -> None:
        self.assertEqual(validate_verification_configuration()["schemas"], 2)
        evidence = self.evidence()
        before = authority_snapshot(Path.cwd())
        first = self.verify(evidence)
        reordered = copy.deepcopy(evidence)
        reordered["sources"].reverse()
        reordered["assertions"].reverse()
        second = self.verify(reordered)
        self.assertEqual(first, second)
        self.assertEqual(first["overall_status"], "pass")
        self.assertEqual(first["repair_plan"]["status"], "no_change")
        self.assertTrue(all(row["status"] == "pass" for row in first["artifact_checks"]))
        self.assertTrue(
            {row["assertion_id"] for row in evidence["assertions"]}
            <= {row["assertion_id"] for row in first["evidence_trace"]}
        )
        self.assertIn(
            "deterministic_comparator",
            {row["assertion_origin"] for row in first["evidence_trace"]},
        )
        self.assertEqual(before, authority_snapshot(Path.cwd()))

    def test_measured_failure_produces_one_interval_bounded_existing_control_action(self) -> None:
        evidence = self.evidence()
        source = next(
            row
            for row in evidence["sources"]
            if row["record"].get("claim", {}).get("metric_id")
            == "metric_product_visibility"
        )
        source_index = next(
            index
            for index, row in enumerate(evidence["sources"])
            if row["source_id"] == source["source_id"]
        )
        record = copy.deepcopy(evidence["sources"][source_index]["record"])
        record["interval"] = {"start_s": 1.25, "end_s": 2.75}
        record["claim"] = {
            "metric_id": "metric_product_visibility",
            "method": "product_visibility_duty_cycle",
            "target_path": "marketing.product_visibility",
            "visible_seconds": 0.0,
            "total_seconds": 1.5,
            "duty_cycle": 0.0,
        }
        evidence["sources"][source_index] = make_evidence_source(
            record, source_type="normalized_video_observation"
        )
        report = self.verify(evidence)
        self.assertEqual(report["overall_status"], "fail")
        self.assertEqual(report["repair_plan"]["status"], "proposed")
        self.assertEqual(len(report["repair_plan"]["actions"]), 1)
        action = report["repair_plan"]["actions"][0]
        expected_control = next(
            row
            for row in self.score["provider_neutral_controls"]
            if row["path"] == "marketing.product_visibility"
        )
        self.assertEqual(action["control_id"], expected_control["control_id"])
        self.assertEqual(action["canonical_value"], expected_control["value"])
        self.assertEqual(action["scope"]["kind"], "interval")
        self.assertEqual(
            action["scope"]["interval"], {"start_s": 1.25, "end_s": 2.75}
        )
        self.assertNotIn(
            expected_control["control_id"],
            report["repair_plan"]["preserve_control_ids"],
        )
        self.assertEqual(
            len(report["repair_plan"]["preserve_control_ids"]),
            len(self.score["provider_neutral_controls"]) - 1,
        )
        trace = next(
            row
            for row in report["evidence_trace"]
            if row["source_ref"] == source["source_id"]
        )
        self.assertEqual(trace["assertion_origin"], "deterministic_comparator")

    def test_semantic_measurement_disagreement_is_preserved_and_blocks_repair(self) -> None:
        evidence = self.evidence()
        source = self._normalized_source(
            "vog_obs_semantic_disagreement", lane="semantic"
        )
        evidence["sources"].append(source)
        evidence["assertions"].append(
            make_assertion(
                metric_id="metric_product_visibility",
                target_path="marketing.product_visibility",
                source_ref=source["source_id"],
                verdict="fail",
                observed=False,
                interval={"start_s": 1.0, "end_s": 3.0},
                deviation={
                    "code": "semantic_visibility_disagreement",
                    "expected": True,
                    "observed": False,
                },
            )
        )
        report = self.verify(evidence)
        check = next(
            row
            for row in report["control_checks"]
            if row["metric_id"] == "metric_product_visibility"
        )
        self.assertEqual(check["status"], "conflict")
        self.assertEqual(report["overall_status"], "inconclusive")
        self.assertEqual(report["repair_plan"]["status"], "blocked")
        self.assertEqual(len(report["conflicts"]), 1)
        self.assertEqual(
            report["conflicts"][0]["lanes"], ["measurement", "semantic"]
        )
        self.assertEqual(
            report["conflicts"][0]["resolution"], "preserved_for_review"
        )

    def test_wrong_lane_is_unobservable_and_cannot_silently_substitute(self) -> None:
        evidence = self.evidence(
            overrides={
                ("metric_product_visibility", "marketing.product_visibility"): {
                    "lane": "semantic"
                }
            }
        )
        report = self.verify(evidence)
        check = next(
            row
            for row in report["control_checks"]
            if row["metric_id"] == "metric_product_visibility"
        )
        self.assertEqual(check["status"], "unobservable")
        target = check["targets"][0]
        self.assertEqual(target["required_lane"], "measurement")
        self.assertEqual(target["evidence_refs"], [])
        self.assertEqual(len(target["supplemental_evidence_refs"]), 1)
        self.assertEqual(report["repair_plan"]["status"], "blocked")

    def test_artifact_metadata_failure_blocks_control_repair_and_tampering_is_rejected(self) -> None:
        evidence = self.evidence()

        def wrong_duration(path: Path, *, expected_sha256: str) -> dict[str, Any]:
            value = self.probe(path, expected_sha256=expected_sha256)
            value["duration_s"] = 7.0
            return value

        report = self.verify(evidence, probe=wrong_duration)
        duration = next(
            row for row in report["artifact_checks"] if row["check_id"] == "duration"
        )
        self.assertEqual(duration["status"], "fail")
        self.assertEqual(report["overall_status"], "fail")
        self.assertEqual(report["repair_plan"]["status"], "blocked")
        (self.job_root / "artifacts/artifact_000.mp4").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "artifact bytes"):
            self.verify(evidence)

    def test_detached_source_and_undeclared_assertion_fail_before_evaluation(self) -> None:
        detached = self.evidence()
        detached["sources"][0]["record"]["claim"]["description"] = "changed"
        with self.assertRaisesRegex(ValueError, "source hash mismatch"):
            self.verify(detached)

        undeclared = self.evidence()
        source_id = undeclared["sources"][0]["source_id"]
        undeclared["assertions"].append(
            make_assertion(
                metric_id="metric_not_declared",
                target_path="camera.not_declared",
                source_ref=source_id,
                verdict="pass",
                observed=True,
            )
        )
        with self.assertRaisesRegex(ValueError, "undeclared metric or path"):
            self.verify(undeclared)

        bypass = self.evidence()
        product_source = next(
            row
            for row in bypass["sources"]
            if row["record"].get("claim", {}).get("metric_id")
            == "metric_product_visibility"
        )
        bypass["assertions"].append(
            make_assertion(
                metric_id="metric_product_visibility",
                target_path="marketing.product_visibility",
                source_ref=product_source["source_id"],
                verdict="pass",
                observed={"duty_cycle": 0.0},
            )
        )
        with self.assertRaisesRegex(ValueError, "refuses a supplied verdict"):
            self.verify(bypass)


if __name__ == "__main__":
    unittest.main()
