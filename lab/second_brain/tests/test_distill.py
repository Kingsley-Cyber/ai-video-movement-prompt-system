from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.curate import promote_proposal
from lab.second_brain.src.distill import run_distillation, status
from lab.second_brain.src.query import default_request, reason
from lab.second_brain.src.validate import read_jsonl, validate_staging
from lab.second_brain.tests.helpers import concept, make_root, write_rows


class DistillationTests(unittest.TestCase):
    def test_batch_is_deduplicated_hop_aligned_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [
                    concept("c_alpha", "motivated camera", layer="camera"),
                    concept("c_beta", "soft key light", layer="lighting"),
                ],
            )
            write_rows(
                root / "lab/second_brain/curated/edges.jsonl",
                [
                    {
                        "id": "edge_000001",
                        "u": "c_alpha",
                        "v": "c_beta",
                        "type": "pairs_with",
                        "context": "all",
                        "authored_by": "test",
                        "note": None,
                        "sources": [],
                    }
                ],
            )
            duplicate = concept(
                "ignored",
                "motivated camera",
                layer="camera",
            )
            duplicate.pop("id")
            new_concept = {
                "kind": "technique",
                "name": "Reveal camera",
                "what": "Tie the reveal beat to a motivated camera response.",
                "use_when": "a reveal needs camera emphasis",
                "nl_triggers": [
                    "camera follows the reveal",
                    "motivate the reveal move",
                    "emphasize the reveal beat",
                ],
                "status": "ingested",
                "evidence": [],
                "source": ["polymath://fixture#chunk-2"],
                "layer": "camera",
                "encodable_as": ["json"],
            }

            def candidate(
                candidate_id: str,
                proposal_type: str,
                proposed_record: dict,
                suggested_id: str | None = None,
            ) -> dict:
                return {
                    "candidate_id": candidate_id,
                    "proposal_type": proposal_type,
                    "suggested_id": suggested_id,
                    "proposed_record": proposed_record,
                    "source_evidence": [
                        {
                            "source_id": "polymath://fixture",
                            "locator": "chunk:fixture_0002",
                            "claim": "The passage supports the candidate.",
                            "content_sha256": "sha256:" + "a" * 64,
                        }
                    ],
                    "created_by": "polymath_mcp",
                    "created_at": "2026-07-30T00:00:00Z",
                }

            batch = {
                "batch_id": "batch_fixture_001",
                "retrieval": {
                    "adapter": "polymath_mcp",
                    "corpus_id": "fixture-corpus",
                    "query": "camera reveal techniques",
                    "tool": "search",
                    "parameters": {"top_k": 5},
                    "retrieved_at": "2026-07-30T00:00:00Z",
                },
                "extractor": {
                    "agent": "fixture-agent",
                    "model": "fixture-model",
                    "prompt_hash": "sha256:" + "b" * 64,
                },
                "candidates": [
                    candidate(
                        "candidate_new_edge",
                        "edge",
                        {
                            "u": "c_reveal_camera",
                            "v": "c_alpha",
                            "type": "refines",
                            "context": "reveal",
                            "authored_by": "polymath_proposal",
                            "note": "The candidate specializes motivated camera use.",
                            "sources": [
                                {
                                    "ref": "polymath://fixture",
                                    "locator": "chunk:fixture_0002",
                                }
                            ],
                        },
                    ),
                    candidate(
                        "candidate_duplicate",
                        "concept",
                        duplicate,
                        "c_duplicate_camera",
                    ),
                    candidate(
                        "candidate_new_concept",
                        "concept",
                        new_concept,
                        "c_reveal_camera",
                    ),
                    candidate(
                        "candidate_new_mapping",
                        "mapping",
                        {
                            "concept_id": "c_reveal_camera",
                            "target_type": "control",
                            "target_id": "camera.reveal.response",
                            "encoding": "json",
                            "mapping": {"field": "reveal_camera"},
                            "loss": "low",
                            "provider": None,
                            "model_version": None,
                            "sources": ["polymath://fixture#chunk-2"],
                        },
                    ),
                    candidate(
                        "candidate_invalid_mapping",
                        "mapping",
                        {
                            "concept_id": "c_missing",
                            "target_type": "control",
                            "target_id": "camera.missing",
                            "encoding": "json",
                            "mapping": {"field": "missing"},
                            "loss": "low",
                            "provider": None,
                            "model_version": None,
                            "sources": ["polymath://fixture#chunk-2"],
                        },
                    ),
                ],
            }
            first = run_distillation(batch, root)
            reordered = copy.deepcopy(batch)
            reordered["candidates"].reverse()
            second = run_distillation(reordered, root)
            self.assertEqual(first, second)
            self.assertEqual(first["summary"]["staged"], 3)
            self.assertEqual(first["summary"]["exact_duplicates"], 1)
            self.assertEqual(first["summary"]["invalid"], 1)
            decisions = {
                row["candidate_id"]: row for row in first["candidate_decisions"]
            }
            self.assertEqual(
                decisions["candidate_duplicate"]["disposition"],
                "reject_exact_duplicate",
            )
            self.assertEqual(
                decisions["candidate_invalid_mapping"]["disposition"],
                "reject_invalid_reference",
            )
            self.assertEqual(
                decisions["candidate_new_edge"]["dependencies"],
                ["candidate_new_concept"],
            )
            anchors = decisions["candidate_new_concept"]["hop_alignment"]["anchors"]
            self.assertTrue(any(row["concept_id"] == "c_alpha" for row in anchors))
            connectivity = decisions["candidate_new_concept"]["connectivity"]
            self.assertTrue(connectivity["connected"])
            self.assertEqual(
                connectivity["anchor_path"],
                ["c_reveal_camera", "c_alpha"],
            )
            self.assertEqual(
                connectivity["mapping_candidate_ids"],
                ["candidate_new_mapping"],
            )
            self.assertEqual(
                len(
                    read_jsonl(
                        root
                        / "lab/second_brain/staging/distillation_runs.jsonl"
                    )
                ),
                1,
            )
            self.assertEqual(
                len(
                    read_jsonl(
                        root / "lab/second_brain/staging/proposals.jsonl"
                    )
                ),
                3,
            )
            self.assertEqual(status(root)["runs"], 1)
            validate_staging(root)
            review = {
                "source_verified": True,
                "source_locator_resolved": True,
                "duplicate_checked": True,
                "operationally_useful": True,
                "relationships_validated": True,
                "numeric_precision_supported": True,
                "reviewed_at": "2026-07-30T00:01:00Z",
                "notes": "fixture review",
            }
            promoted_concept = promote_proposal(
                decisions["candidate_new_concept"]["proposal_id"],
                "c_reveal_camera",
                "test_curator",
                review,
                root,
            )
            self.assertEqual(
                promoted_concept["provenance"]["distillation_run_ids"],
                [first["id"]],
            )
            promote_proposal(
                decisions["candidate_new_edge"]["proposal_id"],
                "edge_000002",
                "test_curator",
                review,
                root,
            )
            promote_proposal(
                decisions["candidate_new_mapping"]["proposal_id"],
                "mapping_000001",
                "test_curator",
                review,
                root,
            )
            after_promotion = run_distillation(batch, root)
            self.assertNotEqual(after_promotion["id"], first["id"])
            self.assertEqual(after_promotion["summary"]["staged"], 0)
            self.assertEqual(after_promotion["summary"]["exact_duplicates"], 4)
            self.assertEqual(after_promotion["summary"]["invalid"], 1)
            self.assertEqual(
                len(
                    read_jsonl(
                        root / "lab/second_brain/staging/proposals.jsonl"
                    )
                ),
                3,
            )
            self.assertEqual(status(root)["runs"], 2)
            query_result = reason(
                default_request(
                    "reveal camera",
                    minimum_status="ingested",
                    target_format="json",
                ),
                root,
            )
            self.assertIn(
                "c_reveal_camera",
                {item["id"] for item in query_result["selected_concepts"]},
            )
            traversed = {
                item["edge_id"] for item in query_result["path_taken"]
            } | {
                item["edge_id"]
                for item in query_result["alternative_valid_paths"]
            }
            self.assertIn("edge_000002", traversed)

    def test_decimal_laban_candidate_requires_nesting_and_an_operational_bridge(self) -> None:
        def candidate(
            candidate_id: str,
            proposal_type: str,
            proposed_record: dict,
            suggested_id: str | None = None,
        ) -> dict:
            return {
                "candidate_id": candidate_id,
                "proposal_type": proposal_type,
                "suggested_id": suggested_id,
                "proposed_record": proposed_record,
                "source_evidence": [
                    {
                        "source_id": "research://laban-decimal-fixture",
                        "locator": "claim:1",
                        "claim": (
                            "Decimal spatial values are proposed as a prompt "
                            "technique; output improvement remains unproven."
                        ),
                        "content_sha256": "sha256:" + "d" * 64,
                    }
                ],
                "created_by": "manual",
                "created_at": "2026-07-30T00:00:00Z",
            }

        decimal_concept = {
            "kind": "hypothesis",
            "name": "Decimal Laban spatial control",
            "what": (
                "Represent spatial movement with decimal values while keeping "
                "any output-quality claim provider-specific and unproven."
            ),
            "use_when": "testing numeric spatial prompting",
            "nl_triggers": [
                "decimal laban movement",
                "numeric spatial prompting",
                "spatial values with decimals",
            ],
            "status": "ingested",
            "evidence": [],
            "source": ["research://laban-decimal-fixture#claim-1"],
            "layer": "quality",
            "encodable_as": ["json", "numeric"],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [concept("c_laban_effort", "Laban effort", layer="quality")],
            )
            unconnected_batch = {
                "batch_id": "batch_decimal_unconnected",
                "retrieval": {
                    "adapter": "manual",
                    "corpus_id": "fixture",
                    "query": "decimal Laban spatial control",
                    "tool": "manual_note",
                    "parameters": {},
                    "retrieved_at": "2026-07-30T00:00:00Z",
                },
                "extractor": {
                    "agent": "fixture-agent",
                    "model": "fixture-model",
                    "prompt_hash": "sha256:" + "e" * 64,
                },
                "candidates": [
                    candidate(
                        "candidate_decimal_concept",
                        "concept",
                        decimal_concept,
                        "c_decimal_laban_spatial",
                    ),
                    candidate(
                        "candidate_decimal_pair",
                        "edge",
                        {
                            "u": "c_decimal_laban_spatial",
                            "v": "c_laban_effort",
                            "type": "pairs_with",
                            "context": "prompt_test",
                            "authored_by": "manual_proposal",
                            "note": "A loose association is not nesting proof.",
                            "sources": [
                                {
                                    "ref": "research://laban-decimal-fixture",
                                    "locator": "claim:1",
                                }
                            ],
                        },
                    ),
                ],
            }
            rejected = run_distillation(unconnected_batch, root)
            rejected_by_id = {
                row["candidate_id"]: row
                for row in rejected["candidate_decisions"]
            }
            self.assertEqual(
                rejected_by_id["candidate_decimal_concept"]["disposition"],
                "reject_unconnected_concept",
            )
            self.assertEqual(rejected["summary"]["staged"], 0)

            connected_batch = copy.deepcopy(unconnected_batch)
            connected_batch["batch_id"] = "batch_decimal_connected"
            connected_batch["candidates"][1]["candidate_id"] = (
                "candidate_decimal_refines"
            )
            connected_batch["candidates"][1]["proposed_record"]["type"] = "refines"
            connected_batch["candidates"].append(
                candidate(
                    "candidate_decimal_mapping",
                    "mapping",
                    {
                        "concept_id": "c_decimal_laban_spatial",
                        "target_type": "control",
                        "target_id": "motion.laban.space_decimal_hypothesis",
                        "encoding": "json",
                        "mapping": {
                            "field": "space",
                            "claim_status": "unproven",
                        },
                        "loss": "low",
                        "provider": None,
                        "model_version": None,
                        "sources": [
                            "research://laban-decimal-fixture#claim-1"
                        ],
                    },
                )
            )
            admitted = run_distillation(connected_batch, root)
            admitted_by_id = {
                row["candidate_id"]: row
                for row in admitted["candidate_decisions"]
            }
            proof = admitted_by_id["candidate_decimal_concept"]["connectivity"]
            self.assertTrue(proof["connected"])
            self.assertEqual(
                proof["anchor_path"],
                ["c_decimal_laban_spatial", "c_laban_effort"],
            )
            self.assertEqual(admitted["summary"]["staged"], 3)


if __name__ == "__main__":
    unittest.main()
