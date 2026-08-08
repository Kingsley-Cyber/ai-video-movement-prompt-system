from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.ingest import upsert_manifest
from lab.second_brain.src.validate import (
    ValidationFailure,
    read_jsonl,
    validate_curated,
    validate_instance,
    validate_staging,
)
from lab.second_brain.tests.helpers import (
    concept,
    make_root,
    representation_strategy,
    write_rows,
)


class ValidationTests(unittest.TestCase):
    def test_concept_registry_rejects_normalized_name_and_alias_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = concept("c_alpha", "Camera Path")
            second = concept("c_beta", "camera-path")
            root = make_root(Path(directory), [first, second])
            with self.assertRaisesRegex(
                ValidationFailure, "duplicate normalized concept names"
            ):
                validate_curated(root)

        with tempfile.TemporaryDirectory() as directory:
            first = concept("c_alpha", "Camera Path")
            second = concept("c_beta", "Lens Motion")
            second["nl_triggers"][0] = "camera path"
            root = make_root(Path(directory), [first, second])
            with self.assertRaisesRegex(
                ValidationFailure, "concept alias registry mismatch"
            ):
                validate_curated(root)

    def test_qualified_format_effect_requires_provider_model_task_and_evidence(self) -> None:
        strategy = representation_strategy("camera.motion.path")
        effect = strategy["projections"][2]["conditioning_effects"][0]
        effect["evidence_status"] = "qualified"
        mapping = {
            "id": "mapping_format_test",
            "concept_id": "c_camera",
            "target_type": "control",
            "target_id": "camera.motion.path",
            "encoding": "json",
            "mapping": {"field": "camera_path"},
            "representation_strategy": strategy,
            "loss": "low",
            "provider": None,
            "model_version": None,
            "sources": ["fixture://format"],
        }
        with self.assertRaisesRegex(ValidationFailure, "mapping"):
            validate_instance("mapping", mapping)
        qualified = copy.deepcopy(mapping)
        qualified_effect = qualified["representation_strategy"]["projections"][2][
            "conditioning_effects"
        ][0]
        qualified_effect["scope"].update(
            {
                "provider": "fixture_provider",
                "model_version": "fixture_model/1",
                "task_class": "camera_motion",
            }
        )
        validate_instance("mapping", qualified)

    def test_derived_edge_type_cannot_enter_curated_store(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [concept("c_alpha", "alpha"), concept("c_beta", "beta")],
            )
            write_rows(
                root / "lab/second_brain/curated/edges.jsonl",
                [
                    {
                        "id": "edge_000001",
                        "u": "c_alpha",
                        "v": "c_beta",
                        "type": "promotes",
                        "context": "all",
                        "authored_by": "test",
                        "note": None,
                        "sources": [],
                    }
                ],
            )
            with self.assertRaises(ValidationFailure):
                validate_curated(root)

    def test_manifest_marks_exact_duplicates_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory))
            base = {
                "source_ref": "polymath://fixture",
                "title": "fixture",
                "sha256_or_source_version": "sha256:" + "a" * 64,
                "domain": "cinematography",
                "status": "pending",
                "sections_processed": [],
                "proposal_ids": [],
                "promoted_concept_ids": [],
                "error": None,
            }
            upsert_manifest(
                [
                    {**base, "corpus_item_id": "cinema_0002"},
                    {**base, "corpus_item_id": "cinema_0001"},
                ],
                root,
            )
            validate_staging(root)
            rows = read_jsonl(
                root / "lab/second_brain/staging/corpus_manifest.jsonl"
            )
            self.assertNotIn("duplicate_of", rows[0])
            self.assertEqual(rows[1]["duplicate_of"], "cinema_0001")


if __name__ == "__main__":
    unittest.main()
