from __future__ import annotations

import copy
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

from lab.compiler.profiles import load_profile_catalog
from lab.compiler.score import REPO_ROOT, make_score_request, resolve_score
from lab.compiler.translations import (
    TRANSLATION_POLICY_VERSION,
    load_translation_catalog,
    translate_context_mappings,
)
from lab.second_brain.src.intent import build_intent_context

from lab.compiler.tests.test_score import asset, authority_snapshot


def resolve_text(
    text: str,
    *,
    assets: list[dict[str, str]] | None = None,
    overlays: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    routed = build_intent_context(text, token_budget=12_000)
    request = make_score_request(
        routed,
        assets=assets or [],
        overlays=overlays or [],
    )
    return request, resolve_score(request)


class ControlTranslationTests(unittest.TestCase):
    def test_translation_to_undeclared_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            compiler = root / "lab/compiler"
            curated = root / "lab/second_brain/curated"
            (compiler / "schemas").mkdir(parents=True)
            curated.mkdir(parents=True)
            shutil.copy2(
                REPO_ROOT / "lab/compiler/schemas/control_translation.schema.json",
                compiler / "schemas/control_translation.schema.json",
            )
            shutil.copy2(
                REPO_ROOT / "lab/second_brain/curated/mappings.jsonl",
                curated / "mappings.jsonl",
            )
            registry = yaml.safe_load(
                (REPO_ROOT / "lab/compiler/control_translations.yaml").read_text(
                    encoding="utf-8"
                )
            )
            registry["translations"][0]["operations"][0]["target_path"] = (
                "parallel_ontology.facs"
            )
            (compiler / "control_translations.yaml").write_text(
                yaml.safe_dump(registry, sort_keys=False), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "undeclared canonical field"):
                load_translation_catalog(
                    root, load_profile_catalog().field_policies
                )

    def test_facs_mapping_changes_score_with_complete_trace(self) -> None:
        _, score = resolve_text(
            "Create a restrained dialogue closeup with a genuine Duchenne smile and FACS.",
            assets=[asset("asset_characters", "character_references")],
        )
        self.assertEqual(score["performance"]["facs_action_units"], ["AU06", "AU12"])
        research = score["research_translation"]
        self.assertEqual(research["policy_version"], TRANSLATION_POLICY_VERSION)
        applied = {
            row["mapping_id"]: row for row in research["applied"]
        }
        self.assertIn("mapping_000001", applied)
        translation = applied["mapping_000001"]
        self.assertEqual(translation["concept_id"], "c_duchenne")
        self.assertEqual(
            translation["operations"][0]["path"],
            "performance.facs_action_units",
        )
        lineage = score["provenance"]["fields"]["performance.facs_action_units"]
        self.assertIn("mapping_000001", lineage["source_refs"])
        self.assertIn("c_duchenne", lineage["source_refs"])
        self.assertIn(
            "metric_translation_duchenne_au_coactivation",
            {row["metric_id"] for row in score["verification_requirements"]},
        )

    def test_laban_mapping_preserves_measurement_contract(self) -> None:
        _, score = resolve_text(
            "Create a Laban directional curvature movement study per hand.",
            assets=[
                asset("asset_audience", "audience_effect"),
                asset("asset_domain", "video_domain"),
            ],
        )
        self.assertEqual(
            score["motion"]["laban_shape_directional_curvature"],
            {
                "projection_plane": "largest_displacement_2d",
                "scope": "per_hand",
                "signal": "average_path_curvature",
            },
        )
        applied = score["research_translation"]["applied"]
        laban = next(row for row in applied if row["mapping_id"] == "mapping_000006")
        self.assertEqual(laban["loss"]["translation"], "none")
        self.assertIn("2D", laban["limitations"][0])
        metric = next(
            row
            for row in score["verification_requirements"]
            if row["metric_id"] == "metric_translation_laban_hand_path_curvature"
        )
        self.assertEqual(metric["observability"], "measured")
        self.assertEqual(
            metric["source_translation"],
            "translation_laban_directional_curvature_1_0",
        )

    def test_action_translation_is_profile_gated_and_reports_untranslated_mappings(self) -> None:
        request, score = resolve_text(
            "Create a dramatic action scene with motivated camera movement."
        )
        self.assertEqual(score["camera"]["motivation"], "dramatic_action_response")
        self.assertEqual(
            score["camera"]["dramatic_motivation_fields"],
            ["camera_response", "continuity_reason", "dramatic_action"],
        )
        dispositions = score["research_translation"]["dispositions"]
        by_mapping = {row["mapping_id"]: row for row in dispositions}
        self.assertEqual(by_mapping["mapping_000015"]["status"], "applied")
        self.assertEqual(by_mapping["mapping_000002"]["status"], "no_translation")
        self.assertIn(
            "untranslated_research_mapping",
            {row["code"] for row in score["warnings"]},
        )

        catalog = load_translation_catalog(
            field_policies=load_profile_catalog().field_policies
        )
        context = request["context_bundle"]
        direct = translate_context_mappings(
            context["mappings"],
            selected_concept_ids={row["id"] for row in context["selected_concepts"]},
            selected_labels={"general_video"},
            required_layers=set(),
            catalog=catalog,
        )
        direct_by_mapping = {row["mapping_id"]: row for row in direct.dispositions}
        self.assertEqual(
            direct_by_mapping["mapping_000015"]["status"],
            "precondition_failed",
        )

    def test_user_overlay_has_precedence_over_research_translation(self) -> None:
        _, score = resolve_text(
            "Create a dramatic action scene with motivated camera movement.",
            overlays=[
                {
                    "overlay_id": "overlay_camera_choice",
                    "scope": "explicit_user_correction",
                    "priority": 0,
                    "values": {"camera": {"motivation": "character_subjectivity"}},
                    "locks": [],
                }
            ],
        )
        self.assertEqual(score["camera"]["motivation"], "character_subjectivity")
        lineage = score["provenance"]["fields"]["camera.motivation"]
        self.assertEqual(lineage["winner"], "overlay_camera_choice")
        self.assertEqual(
            [row["scope"] for row in lineage["candidates"]][-2:],
            ["research_translation", "explicit_user_correction"],
        )

    def test_mapping_tamper_is_rejected_and_replay_does_not_mutate_authority(self) -> None:
        before = authority_snapshot(REPO_ROOT)
        routed = build_intent_context(
            "Create a Laban directional curvature movement study per hand.",
            token_budget=12_000,
        )
        request = make_score_request(
            routed,
            assets=[
                asset("asset_audience", "audience_effect"),
                asset("asset_domain", "video_domain"),
            ],
        )
        first = resolve_score(request)
        second = resolve_score(copy.deepcopy(request))
        self.assertEqual(first, second)
        after = authority_snapshot(REPO_ROOT)
        self.assertEqual(before, after)

        tampered = copy.deepcopy(request)
        mapping = next(
            row
            for row in tampered["context_bundle"]["mappings"]
            if row["id"] == "mapping_000006"
        )
        mapping["mapping"]["signal"] = "invented_signal"
        with self.assertRaisesRegex(ValueError, "differs from curated authority"):
            resolve_score(tampered)


if __name__ == "__main__":
    unittest.main()
