from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.distill import run_distillation
from lab.second_brain.src.graph import edge_compatibility
from lab.second_brain.src.validate import load_ontology_registry, read_jsonl
from lab.second_brain.tests.helpers import concept, make_root


def _technique(concept_id: str, name: str) -> dict:
    row = concept(concept_id, name)
    row["kind"] = "technique"
    return row


def _batch(edge_type: str) -> dict:
    return {
        "batch_id": "batch_edge_compatibility_" + edge_type,
        "retrieval": {
            "adapter": "manual",
            "corpus_id": "edge-contract-fixture",
            "query": "edge compatibility",
            "tool": "manual_note",
            "parameters": {},
            "retrieved_at": "2026-08-08T00:00:00Z",
        },
        "extractor": {
            "agent": "fixture-agent",
            "model": "fixture-model",
            "prompt_hash": "sha256:" + "a" * 64,
        },
        "candidates": [
            {
                "candidate_id": "candidate_edge_compatibility_" + edge_type,
                "proposal_type": "edge",
                "suggested_id": None,
                "proposed_record": {
                    "u": "c_child",
                    "v": "c_parent",
                    "type": edge_type,
                    "context": "fixture",
                    "authored_by": "manual",
                    "note": "Edge-family admission fixture.",
                    "sources": [
                        {"ref": "fixture://edge", "locator": "section:1"}
                    ],
                },
                "source_evidence": [
                    {
                        "source_id": "fixture://edge",
                        "locator": "section:1",
                        "claim": "The source proposes this relationship.",
                        "content_sha256": "sha256:" + "b" * 64,
                    }
                ],
                "created_by": "manual",
                "created_at": "2026-08-08T00:00:00Z",
            }
        ],
    }


class EdgeCompatibilityContractTests(unittest.TestCase):
    def test_closed_pair_passes_and_incompatible_family_fails_before_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_root(
                Path(temporary),
                [
                    _technique("c_child", "Child technique"),
                    _technique("c_parent", "Parent technique"),
                ],
            )
            registry = load_ontology_registry(root)
            concepts = {
                row["id"]: row for row in read_jsonl(root / "lab/concepts.jsonl")
            }
            allowed = edge_compatibility(
                _batch("refines")["candidates"][0]["proposed_record"],
                concepts,
                registry,
                candidate=True,
                root=root,
            )
            self.assertTrue(allowed["compatible"])
            rejected = run_distillation(_batch("applies_to"), root)
            decision = rejected["candidate_decisions"][0]
            self.assertEqual(decision["disposition"], "reject_incompatible_edge")
            self.assertFalse(decision["edge_compatibility"]["compatible"])
            self.assertEqual(rejected["proposal_ids"], [])

    def test_new_legacy_pairs_with_edge_is_not_admitted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_root(
                Path(temporary),
                [
                    _technique("c_child", "Child technique"),
                    _technique("c_parent", "Parent technique"),
                ],
            )
            rejected = run_distillation(_batch("pairs_with"), root)
            report = rejected["candidate_decisions"][0]["edge_compatibility"]
            self.assertEqual(report["admission"], "legacy_existing_only")
            self.assertFalse(report["checks"]["candidate_admitted"])
            self.assertEqual(rejected["summary"]["staged"], 0)


if __name__ == "__main__":
    unittest.main()
