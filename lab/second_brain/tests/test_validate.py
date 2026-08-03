from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.ingest import upsert_manifest
from lab.second_brain.src.validate import (
    ValidationFailure,
    read_jsonl,
    validate_curated,
    validate_staging,
)
from lab.second_brain.tests.helpers import concept, make_root, write_rows


class ValidationTests(unittest.TestCase):
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
