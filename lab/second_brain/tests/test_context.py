from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.context import (
    build_context_bundle,
    canonical_bundle_bytes,
)
from lab.second_brain.src.validate import REPO_ROOT, validate_instance
from lab.second_brain.tests.helpers import concept, make_root, write_rows


def passage_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


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


class ContextBrokerTests(unittest.TestCase):
    def test_laban_bundle_is_safe_gap_explicit_schema_valid_and_replay_stable(self) -> None:
        first = build_context_bundle(
            "Laban effort decimal spatial movement",
            token_budget=12_000,
            minimum_status="ingested",
            include_external_evidence=False,
            target_format="json",
        )
        second = build_context_bundle(
            "Laban effort decimal spatial movement",
            token_budget=12_000,
            minimum_status="ingested",
            include_external_evidence=False,
            target_format="json",
        )

        selected = {item["id"] for item in first["selected_concepts"]}
        mapping_targets = {item["target_id"] for item in first["mappings"]}
        self.assertIn("c_laban_efforts", selected)
        self.assertNotIn("c_dual_view_color_integration", selected)
        self.assertNotIn("color.vfx.dual_view_integration", mapping_targets)
        self.assertEqual(
            first["knowledge_gap"]["uncovered_terms"],
            ["decimal", "spatial"],
        )
        self.assertTrue(first["knowledge_gap"]["should_retrieve"])
        self.assertEqual(first["schema"], "cpcs.context_bundle/1.0")
        self.assertLessEqual(
            first["budget_report"]["used_tokens"],
            first["budget_report"]["available_tokens"],
        )
        validate_instance("context_bundle", first)
        self.assertEqual(canonical_bundle_bytes(first), canonical_bundle_bytes(second))

    def test_external_evidence_is_hash_checked_deduplicated_and_untrusted(self) -> None:
        passage = "Decimal spatial coordinates may encode a bounded movement target."
        content_hash = passage_hash(passage)
        common = {
            "origin": "polymath_mcp",
            "locator": "chapter_2.section_4",
            "content_hash": content_hash,
            "passage": passage,
            "retrieval_query": "decimal spatial",
        }
        bundle = build_context_bundle(
            "Laban effort decimal spatial movement",
            token_budget=12_000,
            minimum_status="ingested",
            target_format="json",
            external_evidence=[
                {**common, "source_id": "source_b"},
                {**common, "source_id": "source_a"},
            ],
        )

        self.assertEqual(len(bundle["external_evidence"]), 1)
        self.assertEqual(bundle["external_evidence"][0]["source_id"], "source_a")
        self.assertEqual(
            bundle["external_evidence"][0]["trust_class"],
            "untrusted_external_evidence",
        )
        self.assertEqual(
            bundle["trust_boundary"]["curated"],
            "repository_authority",
        )
        self.assertEqual(
            bundle["trust_boundary"]["external"],
            "untrusted_external_evidence",
        )
        self.assertTrue(
            any(
                item["reason"] == "duplicate_content_hash"
                for item in bundle["budget_report"]["omitted_items"]
            )
        )

        with self.assertRaisesRegex(ValueError, "content_hash"):
            build_context_bundle(
                "Laban effort decimal spatial movement",
                token_budget=12_000,
                minimum_status="ingested",
                external_evidence=[
                    {
                        **common,
                        "source_id": "source_bad_hash",
                        "content_hash": "sha256:" + "0" * 64,
                    }
                ],
            )
        with self.assertRaisesRegex(ValueError, "unexpected fields"):
            build_context_bundle(
                "Laban effort decimal spatial movement",
                token_budget=12_000,
                minimum_status="ingested",
                external_evidence=[
                    {**common, "source_id": "source_extra", "authority": True}
                ],
            )
        with self.assertRaisesRegex(ValueError, "trust_class"):
            build_context_bundle(
                "Laban effort decimal spatial movement",
                token_budget=12_000,
                minimum_status="ingested",
                external_evidence=[
                    {
                        **common,
                        "source_id": "source_false_authority",
                        "trust_class": "repository_authority",
                    }
                ],
            )

    def test_budget_preserves_priority_and_reports_deterministic_omissions(self) -> None:
        full = build_context_bundle(
            "Laban effort decimal spatial movement",
            token_budget=12_000,
            minimum_status="ingested",
            include_external_evidence=False,
            target_format="json",
        )
        constrained_budget = full["budget_report"]["used_tokens"] - 1
        constrained = build_context_bundle(
            "Laban effort decimal spatial movement",
            token_budget=constrained_budget,
            minimum_status="ingested",
            include_external_evidence=False,
            target_format="json",
        )
        replay = build_context_bundle(
            "Laban effort decimal spatial movement",
            token_budget=constrained_budget,
            minimum_status="ingested",
            include_external_evidence=False,
            target_format="json",
        )

        full_direct = [
            item["id"]
            for item in full["selected_concepts"]
            if item["admission_reason"] == "direct_match"
        ]
        constrained_ids = {
            item["id"] for item in constrained["selected_concepts"]
        }
        self.assertTrue(full_direct)
        self.assertIn(full_direct[0], constrained_ids)
        self.assertTrue(constrained["budget_report"]["omitted_items"])
        self.assertTrue(
            any(
                item["reason"] == "token_budget_exceeded"
                for item in constrained["budget_report"]["omitted_items"]
            )
        )
        self.assertLessEqual(
            constrained["budget_report"]["used_tokens"],
            constrained_budget,
        )
        self.assertEqual(
            canonical_bundle_bytes(constrained),
            canonical_bundle_bytes(replay),
        )
        self.assertNotEqual(
            canonical_bundle_bytes(full),
            canonical_bundle_bytes(constrained),
        )

    def test_provider_model_filters_are_shared_and_authority_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory), [concept("c_alpha", "alpha")])
            write_rows(
                root / "lab/second_brain/curated/mappings.jsonl",
                [
                    {
                        "id": "mapping_generic",
                        "concept_id": "c_alpha",
                        "target_type": "control",
                        "target_id": "alpha.generic",
                        "encoding": "hybrid",
                        "mapping": {"value": 1},
                        "loss": "none",
                        "provider": None,
                        "model_version": None,
                        "sources": ["fixture://generic"],
                    },
                    {
                        "id": "mapping_provider",
                        "concept_id": "c_alpha",
                        "target_type": "control",
                        "target_id": "alpha.provider",
                        "encoding": "hybrid",
                        "mapping": {"value": 2},
                        "loss": "none",
                        "provider": "pegasus",
                        "model_version": None,
                        "sources": ["fixture://provider"],
                    },
                    {
                        "id": "mapping_model",
                        "concept_id": "c_alpha",
                        "target_type": "control",
                        "target_id": "alpha.model",
                        "encoding": "hybrid",
                        "mapping": {"value": 3},
                        "loss": "none",
                        "provider": "pegasus",
                        "model_version": "m1",
                        "sources": ["fixture://model"],
                    },
                ],
            )
            before = authority_snapshot(root)
            matched = build_context_bundle(
                "alpha",
                token_budget=6_000,
                provider="pegasus",
                model="m1",
                root=root,
            )
            generic_only = build_context_bundle(
                "alpha",
                token_budget=6_000,
                provider="other",
                model="m2",
                root=root,
            )
            after = authority_snapshot(root)

            self.assertEqual(
                {item["id"] for item in matched["mappings"]},
                {"mapping_generic", "mapping_provider", "mapping_model"},
            )
            self.assertEqual(
                {item["id"] for item in generic_only["mappings"]},
                {"mapping_generic"},
            )
            self.assertEqual(before, after)

    def test_cli_build_is_schema_valid_and_does_not_mutate_repository_tiers(self) -> None:
        before = authority_snapshot(REPO_ROOT)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lab.second_brain.src.context",
                "build",
                "Laban effort decimal spatial movement",
                "--token-budget",
                "12000",
                "--minimum-status",
                "ingested",
                "--target-format",
                "json",
                "--no-external-evidence",
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        bundle = json.loads(result.stdout)
        after = authority_snapshot(REPO_ROOT)

        validate_instance("context_bundle", bundle)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
