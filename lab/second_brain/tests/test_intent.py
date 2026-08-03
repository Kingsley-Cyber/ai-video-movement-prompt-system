from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

from lab.second_brain.src.intent import (
    build_intent_context,
    canonical_intent_bytes,
    load_profile_policy,
    normalize_intent,
)
from lab.second_brain.src.query import QUERY_POLICY
from lab.second_brain.src.validate import REPO_ROOT, validate_instance


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
            key
            for child in value.values()
            for key in nested_keys(child)
        }
    if isinstance(value, list):
        return {key for child in value for key in nested_keys(child)}
    return set()


class IntentRouterTests(unittest.TestCase):
    def assert_profiles(
        self,
        text: str,
        primary: str,
        secondary: set[str],
    ) -> dict[str, Any]:
        first = normalize_intent(text)
        replay = normalize_intent(text)
        validate_instance("normalized_intent", first)
        self.assertEqual(first["profiles"]["primary"], primary)
        self.assertTrue(secondary <= set(first["profiles"]["secondary"]))
        self.assertEqual(canonical_intent_bytes(first), canonical_intent_bytes(replay))
        return first

    def test_ugc_product_recommendation_canary(self) -> None:
        result = self.assert_profiles(
            "Make a casual phone video recommending this skincare product",
            "ugc",
            {"product_demonstration"},
        )
        self.assertEqual(result["intent"]["task"], "product_recommendation")
        self.assertIn("product_reference", result["requirements"]["missing_inputs"])

    def test_restrained_dialogue_canary(self) -> None:
        result = self.assert_profiles(
            "Create a restrained scene where she realizes he is lying",
            "dialogue_performance",
            {"cinematic_restraint"},
        )
        self.assertEqual(result["intent"]["task"], "dialogue_scene")
        self.assertIn("restrained", result["requirements"]["soft_preferences"])

    def test_shonen_action_canary(self) -> None:
        result = self.assert_profiles(
            "Create an original shonen counterattack with readable screen direction",
            "action",
            {"anime_stylization", "multi_actor"},
        )
        self.assertEqual(result["intent"]["task"], "stylized_action_sequence")
        self.assertIn(
            "readable_screen_direction",
            result["requirements"]["soft_preferences"],
        )

    def test_educational_product_canary(self) -> None:
        result = self.assert_profiles(
            "Show how this device works in a clear educational video",
            "product_demonstration",
            {"educational"},
        )
        self.assertEqual(result["intent"]["audience_effect"], "comprehension")

    def test_cinematic_ugc_blend_exposes_conflict_decision(self) -> None:
        result = self.assert_profiles(
            "Cinematic UGC product recommendation",
            "ugc",
            {"product_demonstration", "cinematic_restraint"},
        )
        self.assertEqual(
            result["conflicts"],
            [
                {
                    "id": "conflict_ugc_cinematic_realism",
                    "profiles": ["ugc", "cinematic_restraint"],
                    "field": "capture.realism_vs_cinematic_lensing",
                    "options": [
                        "phone_realism_dominates",
                        "cinematic_lensing_dominates",
                    ],
                    "disposition": "requires_user_choice",
                    "selected": None,
                    "reason": "UGC capture cues and cinematic lensing can imply incompatible realism priorities.",
                }
            ],
        )
        self.assertIn(
            "profile_conflict",
            {row["code"] for row in result["uncertainties"]},
        )

    def test_ambiguity_and_explicit_override_are_visible(self) -> None:
        ambiguous = normalize_intent("Make a video")
        self.assertEqual(ambiguous["profiles"]["primary"], "general_video")
        self.assertEqual(ambiguous["profiles"]["confidence"], 0.0)
        self.assertIn(
            "domain_ambiguous",
            {row["code"] for row in ambiguous["uncertainties"]},
        )
        overridden = normalize_intent(
            "Make a video",
            profile_overrides=["educational", "ugc"],
            user_constraints=[
                "must:Keep every label legible",
                "lock:Device orientation",
            ],
        )
        self.assertEqual(overridden["profiles"]["primary"], "educational")
        self.assertEqual(overridden["profiles"]["secondary"][0], "ugc")
        self.assertEqual(overridden["profiles"]["selection_source"], "user_override")
        self.assertEqual(
            overridden["requirements"]["hard_constraints"],
            ["Keep every label legible"],
        )
        self.assertEqual(
            overridden["requirements"]["continuity_locks"],
            ["Device orientation"],
        )
        with self.assertRaisesRegex(ValueError, "unknown profile override"):
            normalize_intent("Make a video", profile_overrides=["veo_mode"])

    def test_router_is_provider_neutral_and_policy_only_configures_one_kernel(self) -> None:
        policy = load_profile_policy()
        result = normalize_intent(
            "Create an original shonen counterattack with readable screen direction"
        )
        self.assertEqual(policy["configuration_kind"], "intent_routing_only")
        self.assertEqual(policy["kernel_contract"], "cpcs.video_kernel/1.0")
        self.assertTrue(
            {
                "controls",
                "directing_knowledge",
                "mapping",
                "model",
                "prompt",
                "provider",
                "provider_request",
                "score",
            }.isdisjoint(
                nested_keys(result)
            )
        )

    def test_generated_query_flows_through_safe_context_without_authority_writes(self) -> None:
        before = authority_snapshot(REPO_ROOT)
        routed = build_intent_context(
            "Create a restrained scene where she realizes he is lying",
            token_budget=12_000,
        )
        replay = build_intent_context(
            "Create a restrained scene where she realizes he is lying",
            token_budget=12_000,
        )
        after = authority_snapshot(REPO_ROOT)
        normalized = routed["normalized_intent"]
        bundle = routed["context_bundle"]
        self.assertEqual(
            bundle["request"]["query"],
            normalized["routing"]["knowledge_query"],
        )
        self.assertRegex(bundle["request"]["intent"], r"^normalized-intent:[0-9a-f]{16}$")
        self.assertEqual(bundle["policy_versions"]["query"], QUERY_POLICY["version"])
        self.assertFalse(bundle["request"]["include_external_evidence"])
        self.assertEqual(before, after)
        self.assertEqual(routed, replay)

    def test_cli_returns_the_normalized_contract_without_mutation(self) -> None:
        before = authority_snapshot(REPO_ROOT)
        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "lab.second_brain.src.intent",
                "normalize",
                "Show how this device works in a clear educational video",
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(process.stdout)
        after = authority_snapshot(REPO_ROOT)
        validate_instance("normalized_intent", result)
        self.assertEqual(result["schema"], "cpcs.normalized_intent/1.0")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
