from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from lab.compiler.merge import apply_merge
from lab.compiler.score import (
    REPO_ROOT,
    canonical_score_bytes,
    make_score_request,
    resolve_score,
    validate_compiler_instance,
    validate_configuration,
)
from lab.second_brain.src.intent import build_intent_context


def asset(asset_id: str, role: str) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "role": role,
        "content_hash": "sha256:" + "a" * 64,
        "rights_basis": "owner_authorized_test_fixture",
    }


def authority_snapshot(root: Path) -> dict[str, bytes]:
    paths = [root / "lab/concepts.jsonl"]
    second_brain = root / "lab/second_brain"
    for tier in ("curated", "immutable", "derived", "staging"):
        tier_path = second_brain / tier
        if tier_path.exists():
            paths.extend(path for path in tier_path.rglob("*") if path.is_file())
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(paths)
    }


def nested_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key for child in value.values() for key in nested_keys(child)
        }
    if isinstance(value, list):
        return {key for child in value for key in nested_keys(child)}
    return set()


def resolve_text(
    text: str,
    *,
    assets: list[dict[str, str]] | None = None,
    profile_selection: list[str] | None = None,
    overlays: list[dict[str, Any]] | None = None,
    conflict_resolutions: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    routed = build_intent_context(text, token_budget=12_000)
    request = make_score_request(
        routed,
        profile_selection=profile_selection,
        assets=assets or [],
        overlays=overlays or [],
        conflict_resolutions=conflict_resolutions,
    )
    return request, resolve_score(request)


class MergeOperatorTests(unittest.TestCase):
    def test_all_declared_operators_have_deterministic_behavior(self) -> None:
        self.assertEqual(apply_merge("replace", 1, 2).value, 2)
        self.assertEqual(
            apply_merge("merge_object", {"a": 1}, {"b": 2}).value,
            {"a": 1, "b": 2},
        )
        self.assertEqual(
            apply_merge(
                "merge_by_id",
                [{"id": "a", "value": 1}],
                [{"id": "a", "value": 2}, {"id": "b", "value": 3}],
            ).value,
            [{"id": "a", "value": 2}, {"id": "b", "value": 3}],
        )
        self.assertEqual(apply_merge("append_ordered", [1], [2]).value, [1, 2])
        self.assertEqual(apply_merge("union_set", [2, 1], [2, 3]).value, [1, 2, 3])
        self.assertEqual(apply_merge("union_set", None, [2, 1, 2]).value, [1, 2])
        self.assertEqual(
            apply_merge("merge_by_id", None, [{"id": "b"}, {"id": "a"}]).value,
            [{"id": "a"}, {"id": "b"}],
        )
        self.assertEqual(apply_merge("intersect_set", [2, 1], [2, 3]).value, [2])
        self.assertEqual(apply_merge("minimum", 4, 2).value, 2)
        self.assertEqual(apply_merge("maximum", False, True).value, True)
        self.assertEqual(
            apply_merge(
                "compose_temporal_tracks",
                [{"id": "late", "start_s": 1.0}],
                [{"id": "early", "start_s": 0.0}],
            ).value,
            [
                {"id": "early", "start_s": 0.0},
                {"id": "late", "start_s": 1.0},
            ],
        )
        conflict = apply_merge("reject_on_conflict", "deep", "shallow")
        self.assertTrue(conflict.conflict)
        self.assertIsNone(conflict.value)


class UniversalScoreTests(unittest.TestCase):
    def test_configuration_is_closed_and_schema_valid(self) -> None:
        report = validate_configuration()
        self.assertEqual(report["schemas"], 4)
        self.assertEqual(report["universal_profiles"], 1)
        self.assertEqual(report["domain_profiles"], 8)
        self.assertEqual(report["component_profiles"], 8)
        self.assertEqual(report["control_translations"], 3)
        self.assertGreater(report["field_policies"], 45)

    def test_pure_ugc_product_score_has_phone_realism_without_cinematic_lensing(self) -> None:
        _, score = resolve_text(
            "Make a casual phone video recommending this skincare product",
            assets=[asset("asset_product", "product_reference")],
        )
        validate_compiler_instance("universal_score", score)
        self.assertEqual(score["score_status"], "ready")
        self.assertEqual(score["camera"]["depth_of_field"], "deep_focus")
        self.assertEqual(score["style"]["realism"], "phone_realism")
        self.assertTrue(score["marketing"]["product_visibility"])
        self.assertNotIn("shallow_focus", json.dumps(score))

    def test_cinematic_ugc_requires_two_explicit_realism_decisions(self) -> None:
        request, unresolved = resolve_text(
            "Cinematic UGC product recommendation",
            assets=[asset("asset_product", "product_reference")],
        )
        self.assertEqual(unresolved["score_status"], "needs_input")
        self.assertNotIn("depth_of_field", unresolved["camera"])
        self.assertNotIn("realism", unresolved["style"])
        self.assertEqual(
            {row["conflict_id"] for row in unresolved["profile_resolution"]["conflicts"]},
            {
                "conflict_ugc_cinematic_lensing",
                "conflict_ugc_cinematic_realism",
            },
        )
        request["conflict_resolutions"] = {
            "conflict_ugc_cinematic_lensing": "deep_focus",
            "conflict_ugc_cinematic_realism": "phone_realism",
        }
        resolved = resolve_score(request)
        self.assertEqual(resolved["score_status"], "ready")
        self.assertEqual(resolved["camera"]["depth_of_field"], "deep_focus")
        self.assertEqual(resolved["style"]["realism"], "phone_realism")

    def test_restrained_dialogue_has_subtext_and_no_marketing_controls(self) -> None:
        _, score = resolve_text(
            "Create a restrained scene where she realizes he is lying",
            assets=[asset("asset_characters", "character_references")],
        )
        self.assertEqual(score["score_status"], "ready")
        self.assertEqual(score["performance"]["subtext_strategy"], "context_driven")
        self.assertEqual(score["performance"]["gaze_strategy"], "motivated_by_relationship")
        self.assertEqual(score["camera"]["motivation"], "performance_driven")
        self.assertEqual(score["marketing"], {})

    def test_anime_action_preserves_choreography_independently_of_style(self) -> None:
        _, score = resolve_text(
            "Create an original shonen counterattack with readable screen direction",
            assets=[asset("asset_actors", "actor_references")],
        )
        self.assertEqual(score["score_status"], "ready")
        self.assertTrue(score["motion"]["choreography_preservation"])
        self.assertEqual(score["style"]["presentation"], "anime")
        self.assertEqual(score["style"]["transform"]["target"], "anime_sakuga_action")
        self.assertIn("action_order", score["style"]["protected_invariants"])
        self.assertNotIn("effects", score)

    def test_profile_input_order_cannot_change_score_bytes(self) -> None:
        routed = build_intent_context(
            "Create an original shonen counterattack with readable screen direction",
            token_budget=12_000,
        )
        labels = [
            routed["normalized_intent"]["profiles"]["primary"],
            *routed["normalized_intent"]["profiles"]["secondary"],
        ]
        first = resolve_score(
            make_score_request(
                routed,
                profile_selection=labels,
                assets=[asset("asset_actors", "actor_references")],
            )
        )
        second = resolve_score(
            make_score_request(
                routed,
                profile_selection=list(reversed(labels)),
                assets=[asset("asset_actors", "actor_references")],
            )
        )
        self.assertEqual(canonical_score_bytes(first), canonical_score_bytes(second))

    def test_every_control_has_field_provenance_and_output_is_provider_neutral(self) -> None:
        _, score = resolve_text(
            "Show how this device works in a clear educational video",
            assets=[asset("asset_device", "product_reference")],
        )
        fields = score["provenance"]["fields"]
        for control in score["provider_neutral_controls"]:
            self.assertIn(control["path"], fields)
            self.assertEqual(control["value"], fields[control["path"]]["value"])
            self.assertTrue(fields[control["path"]]["candidates"])
        self.assertTrue(
            {"prompt", "provider", "provider_request"}.isdisjoint(nested_keys(score))
        )
        self.assertEqual(score["provider_realization"]["status"], "unassigned")

    def test_event_lock_survives_later_user_correction(self) -> None:
        overlays = [
            {
                "overlay_id": "overlay_event_lock",
                "scope": "event_lock",
                "priority": 0,
                "values": {"camera": {"screen_direction_locked": True}},
                "locks": ["camera.screen_direction_locked"],
            },
            {
                "overlay_id": "overlay_user_correction",
                "scope": "explicit_user_correction",
                "priority": 0,
                "values": {"camera": {"screen_direction_locked": False}},
                "locks": [],
            },
        ]
        _, score = resolve_text(
            "Make a casual phone video recommending this skincare product",
            assets=[asset("asset_product", "product_reference")],
            overlays=overlays,
        )
        self.assertEqual(score["score_status"], "needs_input")
        self.assertTrue(score["camera"]["screen_direction_locked"])
        self.assertIn("camera.screen_direction_locked", score["constraints"]["locked_paths"])
        self.assertIn("hard_lock_conflict", {row["code"] for row in score["unresolved"]})

    def test_public_cli_replays_without_authority_mutation(self) -> None:
        before = authority_snapshot(REPO_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            intent_process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lab.second_brain.src.intent",
                    "context",
                    "Show how this device works in a clear educational video",
                    "--token-budget",
                    "12000",
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            intent_path = Path(directory) / "intent_context.json"
            intent_path.write_text(intent_process.stdout, encoding="utf-8")
            assets_path = Path(directory) / "assets.json"
            assets_path.write_text(
                json.dumps([asset("asset_device", "product_reference")]),
                encoding="utf-8",
            )
            command = [
                sys.executable,
                "-m",
                "lab.compiler.score",
                "resolve-context",
                str(intent_path),
                "--assets",
                str(assets_path),
            ]
            first = subprocess.run(
                command,
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            second = subprocess.run(
                command,
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
        after = authority_snapshot(REPO_ROOT)
        self.assertEqual(first.stdout, second.stdout)
        validate_compiler_instance("universal_score", json.loads(first.stdout))
        self.assertEqual(before, after)

    def test_context_and_profile_mismatches_are_rejected(self) -> None:
        routed = build_intent_context(
            "Show how this device works in a clear educational video",
            token_budget=12_000,
        )
        request = make_score_request(
            routed,
            assets=[asset("asset_device", "product_reference")],
        )
        bad_context = copy.deepcopy(request)
        bad_context["context_bundle"]["request"]["query"] = "different query"
        with self.assertRaisesRegex(ValueError, "query does not match"):
            resolve_score(bad_context)
        bad_profiles = copy.deepcopy(request)
        bad_profiles["profile_selection"] = ["ugc"]
        with self.assertRaisesRegex(ValueError, "exactly"):
            resolve_score(bad_profiles)


if __name__ == "__main__":
    unittest.main()
