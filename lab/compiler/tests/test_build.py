from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from lab.compiler.build import (
    ARTIFACT_NAMES,
    compile_build,
    make_build_request,
    validate_build_configuration,
    write_build_directory,
)
from lab.compiler.profiles import REPO_ROOT
from lab.compiler.provenance import canonical_json_bytes, sha256_bytes
from lab.compiler.score import make_score_request, resolve_score
from lab.compiler.tests.test_score import asset, authority_snapshot
from lab.second_brain.src.intent import build_intent_context


ALL_ARTIFACTS = {*ARTIFACT_NAMES, "build_manifest.json"}
CONFLICT_RESOLUTIONS = {
    "conflict_ugc_cinematic_lensing": "deep_focus",
    "conflict_ugc_cinematic_realism": "phone_realism",
}


def ready_score(
    text: str,
    *,
    extra_assets: list[dict[str, str]] | None = None,
    overlays: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    routed = build_intent_context(text, token_budget=12_000)
    missing = routed["normalized_intent"]["requirements"]["missing_inputs"]
    supplied = [asset(f"asset_required_{index}", role) for index, role in enumerate(missing)]
    request = make_score_request(
        routed,
        assets=[*supplied, *(extra_assets or [])],
        overlays=overlays or [],
        conflict_resolutions=(
            CONFLICT_RESOLUTIONS
            if text == "Cinematic UGC product recommendation"
            else {}
        ),
    )
    score = resolve_score(request)
    if score["score_status"] != "ready":
        raise AssertionError(f"fixture did not resolve: {score['unresolved']}")
    return score


def build_for(
    score: dict[str, Any],
    *,
    creative_mode: str = "exact",
    asset_bindings: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    request = make_build_request(
        score,
        project_id="cpcs-test-project",
        creative_mode=creative_mode,
        sample_count=2 if creative_mode == "exploratory" else 1,
        asset_bindings=asset_bindings,
    )
    return request, compile_build(request)


def decoded(artifacts: dict[str, bytes], name: str) -> dict[str, Any]:
    return json.loads(artifacts[name])


class ProductionBuildCompilerTests(unittest.TestCase):
    def test_configuration_and_all_public_schemas_are_valid(self) -> None:
        report = validate_build_configuration()
        self.assertEqual(report["schemas"], 7)
        self.assertEqual(
            report["capability_id"],
            "provider-capability://google-vertex-ai/veo-3.1-generate-001/1.0",
        )
        score = ready_score(
            "Create a multi-actor action scene with readable screen direction"
        )
        with self.assertRaisesRegex(ValueError, "build_request.schema.json"):
            make_build_request(
                score,
                project_id="cpcs-test-project",
                location="europe-west4",
            )

    def test_golden_domains_compile_to_the_same_eight_artifact_contract(self) -> None:
        reference_asset = asset("asset_motion_reference", "motion_reference")
        image_asset = asset("asset_first_frame", "product_reference")
        cases = (
            ("ugc_product", "Make a casual phone video recommending this skincare product", "exact", None, None),
            ("cinematic_ugc", "Cinematic UGC product recommendation", "interpretive", None, None),
            ("restrained_dialogue", "Create a restrained scene where she realizes he is lying", "exact", None, None),
            ("multi_actor_action", "Create a multi-actor action scene with readable screen direction", "exact", None, None),
            ("anime_action", "Create an original shonen counterattack with readable screen direction", "exploratory", None, None),
            ("education", "Show how this device works in a clear educational video", "diagnostic", None, None),
            ("reference_transfer", "Transfer this reference video's movement into an original scene", "transfer", [reference_asset], None),
            (
                "image_reference",
                "Create an image-led cinematic product reveal",
                "exact",
                [image_asset],
                [{
                    "asset_id": "asset_first_frame",
                    "provider_role": "first_frame",
                    "gcs_uri": "gs://cpcs-test-assets/first-frame.png",
                    "mime_type": "image/png",
                }],
            ),
        )
        semantic_markers = {
            "ugc_product": 'style.realism = "phone_realism"',
            "cinematic_ugc": 'camera.depth_of_field = "deep_focus"',
            "restrained_dialogue": 'performance.subtext_strategy = "context_driven"',
            "multi_actor_action": "continuity.screen_direction_locked = true",
            "anime_action": 'style.presentation = "anime"',
            "education": 'project.communication_goal = "comprehension"',
        }
        for label, text, mode, extra_assets, bindings in cases:
            with self.subTest(label=label):
                score = ready_score(text, extra_assets=extra_assets)
                _, artifacts = build_for(
                    score, creative_mode=mode, asset_bindings=bindings
                )
                self.assertEqual(set(artifacts), ALL_ARTIFACTS)
                manifest = decoded(artifacts, "build_manifest.json")
                self.assertEqual(manifest["creative_mode"], mode)
                self.assertEqual(manifest["score_id"], score["score_id"])
                provider_request = decoded(artifacts, "provider_request.json")
                self.assertEqual(provider_request["method"], "POST")
                self.assertNotIn(
                    "generateAudio", provider_request["body"]["parameters"]
                )
                if label in semantic_markers:
                    self.assertIn(
                        semantic_markers[label], artifacts["prompt.txt"].decode("utf-8")
                    )
                if label == "reference_transfer":
                    self.assertIn(
                        "asset_motion_reference",
                        artifacts["reference_still_prompt.txt"].decode("utf-8"),
                    )
                if label == "image_reference":
                    instance = decoded(artifacts, "provider_request.json")["body"]["instances"][0]
                    self.assertEqual(
                        instance["image"]["gcsUri"],
                        "gs://cpcs-test-assets/first-frame.png",
                    )

    def test_replay_hashes_and_every_manifest_hash_are_deterministic(self) -> None:
        score = ready_score(
            "Show how this device works in a clear educational video"
        )
        request = make_build_request(score, project_id="cpcs-test-project", seed=91)
        first = compile_build(request)
        second = compile_build(copy.deepcopy(request))
        self.assertEqual(first, second)
        manifest = decoded(first, "build_manifest.json")
        self.assertEqual(
            set(manifest["concept_hashes"]), set(manifest["concept_ids"])
        )
        self.assertEqual(manifest["block_hashes"], {})
        for name, digest in manifest["artifact_hashes"].items():
            self.assertEqual(digest, sha256_bytes(first[name]))
        hash_input = {
            key: value
            for key, value in manifest.items()
            if key not in {"build_id", "build_hash"}
        }
        expected = hashlib.sha256(canonical_json_bytes(hash_input)).hexdigest()
        self.assertEqual(manifest["build_id"], "build_" + expected[:32])
        self.assertEqual(manifest["build_hash"], "sha256:" + expected)

    def test_prompt_uses_only_canonical_controls_and_reports_every_one(self) -> None:
        score = ready_score(
            "Create a Laban directional curvature movement study per hand."
        )
        _, artifacts = build_for(score)
        prompt = artifacts["prompt.txt"].decode("utf-8")
        reference_prompt = artifacts["reference_still_prompt.txt"].decode("utf-8")
        report = decoded(artifacts, "capability_report.json")
        losses = decoded(artifacts, "loss_report.json")
        expected = {row["control_id"] for row in score["provider_neutral_controls"]}
        prompt_ids = set(re.findall(r"\[(control_[0-9a-f]{16})\]", prompt))
        reported = [row["control_id"] for row in report["dispositions"]]
        self.assertEqual(set(reported), expected)
        self.assertEqual(len(reported), len(expected))
        self.assertTrue(prompt_ids <= expected)
        self.assertLessEqual(report["prompt_chars_used"], report["prompt_budget_chars"])
        self.assertEqual(report["prompt_chars_used"], len(prompt))
        reference_ids = set(
            re.findall(r"\[(control_[0-9a-f]{16})\]", reference_prompt)
        )
        self.assertTrue(reference_ids <= expected)
        self.assertEqual(
            reference_ids, set(report["reference_projection_control_ids"])
        )
        self.assertLessEqual(
            report["reference_prompt_chars_used"],
            report["reference_prompt_budget_chars"],
        )
        self.assertEqual(report["reference_prompt_chars_used"], len(reference_prompt))
        evaluation = next(
            row
            for row in report["dispositions"]
            if row["path"] == "motion.laban_shape_directional_curvature"
        )
        self.assertEqual(evaluation["status"], "evaluation_only")
        self.assertNotIn(evaluation["control_id"], prompt_ids)
        self.assertIn(
            evaluation["control_id"],
            {row["control_id"] for row in losses["losses"]},
        )
        checks = {
            row["check_id"]: row
            for row in decoded(artifacts, "verification_plan.json")[
                "provider_artifact_checks"
            ]
        }
        self.assertEqual(checks["duration"]["expected"], 8)
        self.assertEqual(checks["duration"]["tolerance"], 0)
        self.assertEqual(checks["frame_rate"]["expected"], 24)

    def test_hard_lock_survives_prompt_projection_and_locked_overflow_fails(self) -> None:
        lock = {
            "overlay_id": "overlay_lock_screen_direction",
            "scope": "event_lock",
            "priority": 0,
            "values": {"camera": {"screen_direction_locked": True}},
            "locks": ["camera.screen_direction_locked"],
        }
        score = ready_score(
            "Create a multi-actor action scene with readable screen direction",
            overlays=[lock],
        )
        _, artifacts = build_for(score)
        control = next(
            row
            for row in score["provider_neutral_controls"]
            if row["path"] == "camera.screen_direction_locked"
        )
        expected_line = (
            f"[{control['control_id']}] camera.screen_direction_locked = true"
        )
        self.assertIn(expected_line, artifacts["prompt.txt"].decode("utf-8"))

        huge_lock = {
            "overlay_id": "overlay_locked_oversize_goal",
            "scope": "event_lock",
            "priority": 0,
            "values": {"project": {"communication_goal": "x" * 12_500}},
            "locks": ["project.communication_goal"],
        }
        oversized = ready_score(
            "Create a multi-actor action scene with readable screen direction",
            overlays=[huge_lock],
        )
        with self.assertRaisesRegex(ValueError, "cannot preserve locked control"):
            build_for(oversized)

    def test_nonlocked_prompt_overflow_is_an_explicit_unsupported_loss(self) -> None:
        overflow = {
            "overlay_id": "overlay_oversize_goal",
            "scope": "shot_override",
            "priority": 0,
            "values": {"project": {"communication_goal": "x" * 12_500}},
            "locks": [],
        }
        score = ready_score(
            "Create a multi-actor action scene with readable screen direction",
            overlays=[overflow],
        )
        _, artifacts = build_for(score)
        report = decoded(artifacts, "capability_report.json")
        losses = decoded(artifacts, "loss_report.json")
        disposition = next(
            row
            for row in report["dispositions"]
            if row["path"] == "project.communication_goal"
        )
        self.assertEqual(disposition["status"], "unsupported")
        self.assertTrue(losses["has_unsupported_controls"])
        self.assertIn(
            disposition["control_id"],
            {row["control_id"] for row in losses["losses"]},
        )
        self.assertNotIn("x" * 100, artifacts["prompt.txt"].decode("utf-8"))

    def test_all_creative_modes_are_manifest_policy_not_score_mutation(self) -> None:
        score = ready_score(
            "Create a multi-actor action scene with readable screen direction",
            extra_assets=[asset("asset_mode_reference", "creative_reference")],
        )
        original = canonical_json_bytes(score)
        modes = (
            "exact",
            "interpretive",
            "exploratory",
            "transfer",
            "diagnostic",
            "research_gap",
        )
        hashes = set()
        for mode in modes:
            _, artifacts = build_for(score, creative_mode=mode)
            manifest = decoded(artifacts, "build_manifest.json")
            report = decoded(artifacts, "capability_report.json")
            self.assertEqual(manifest["creative_mode"], mode)
            self.assertEqual(report["creative_policy"]["mode"], mode)
            decisions = {
                row["decision_id"]: row["outcome"]
                for row in report["creative_policy"]["decisions"]
            }
            self.assertEqual(decisions["seed"], manifest["seed"])
            self.assertEqual(
                decisions["sample_count"], 2 if mode == "exploratory" else 1
            )
            hashes.add(manifest["build_hash"])
        self.assertEqual(len(hashes), len(modes))
        self.assertEqual(canonical_json_bytes(score), original)

    def test_asset_bindings_are_score_bound_and_first_last_frame_is_explicit(self) -> None:
        first = asset("asset_first", "first_frame_reference")
        last = asset("asset_last", "last_frame_reference")
        score = ready_score(
            "Create a restrained scene where she realizes he is lying",
            extra_assets=[first, last],
        )
        bindings = [
            {
                "asset_id": "asset_first",
                "provider_role": "first_frame",
                "gcs_uri": "gs://cpcs-test-assets/first.jpg",
                "mime_type": "image/jpeg",
            },
            {
                "asset_id": "asset_last",
                "provider_role": "last_frame",
                "gcs_uri": "gs://cpcs-test-assets/last.jpg",
                "mime_type": "image/jpeg",
            },
        ]
        _, artifacts = build_for(score, asset_bindings=bindings)
        instance = decoded(artifacts, "provider_request.json")["body"]["instances"][0]
        self.assertEqual(instance["image"]["gcsUri"], bindings[0]["gcs_uri"])
        self.assertEqual(instance["lastFrame"]["gcsUri"], bindings[1]["gcs_uri"])
        with self.assertRaisesRegex(ValueError, "requires a first_frame"):
            build_for(score, asset_bindings=[bindings[1]])
        bad = copy.deepcopy(bindings[0])
        bad["asset_id"] = "asset_not_in_score"
        with self.assertRaisesRegex(ValueError, "absent from canonical score"):
            build_for(score, asset_bindings=[bad])

    def test_tampered_score_identity_and_nonempty_output_are_rejected(self) -> None:
        score = ready_score(
            "Show how this device works in a clear educational video"
        )
        tampered = copy.deepcopy(score)
        tampered["project"]["communication_goal"] = "silent mutation"
        request = make_build_request(tampered, project_id="cpcs-test-project")
        with self.assertRaisesRegex(ValueError, "score_id does not match"):
            compile_build(request)
        _, artifacts = build_for(score)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "existing.txt").write_text("occupied", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not empty"):
                write_build_directory(artifacts, output)

    def test_public_cli_writes_exact_package_without_authority_mutation(self) -> None:
        score = ready_score(
            "Make a casual phone video recommending this skincare product"
        )
        request = make_build_request(score, project_id="cpcs-test-project")
        before = authority_snapshot(REPO_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path = root / "build_request.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            output = root / "build"
            process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lab.compiler.build",
                    "compile",
                    str(request_path),
                    "--output-dir",
                    str(output),
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(process.stdout)
            self.assertEqual(result["output_dir"], str(output))
            self.assertEqual({path.name for path in output.iterdir()}, ALL_ARTIFACTS)
        self.assertEqual(before, authority_snapshot(REPO_ROOT))


if __name__ == "__main__":
    unittest.main()
