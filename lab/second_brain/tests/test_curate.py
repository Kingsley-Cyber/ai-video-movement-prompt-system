from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.compile import compile_result
from lab.second_brain.src.curate import (
    promote_distillation_bundle,
    promote_proposal,
)
from lab.second_brain.src.distill import run_distillation
from lab.second_brain.src.ingest import (
    ingest_distillation_batch,
    stage_proposal,
    status as ingest_status,
)
from lab.second_brain.src.query import default_request, reason
from lab.second_brain.src.validate import (
    ValidationFailure,
    read_jsonl,
    validate_staging,
)
from lab.second_brain.tests.helpers import concept, make_root


def _review() -> dict:
    return {
        "source_verified": True,
        "source_locator_resolved": True,
        "duplicate_checked": True,
        "operationally_useful": True,
        "relationships_validated": True,
        "numeric_precision_supported": True,
        "reviewed_at": "2026-07-30T00:01:00Z",
        "notes": "fixture review",
    }


def _rag_batch() -> dict:
    evidence = {
        "source_id": "rag://fixture/laban-decimals",
        "locator": "section:spatial-precision",
        "claim": "Decimal positions can express intermediate spatial movement.",
        "content_sha256": "sha256:" + "d" * 64,
    }
    created = {
        "created_by": "rag_pipeline",
        "created_at": "2026-07-30T00:00:00Z",
    }
    return {
        "batch_id": "batch_rag_laban_decimals",
        "retrieval": {
            "adapter": "fixture_rag",
            "corpus_id": "fixture-laban",
            "query": "decimal spatial movement prompting",
            "tool": "retrieve",
            "parameters": {"top_k": 3},
            "retrieved_at": "2026-07-30T00:00:00Z",
        },
        "extractor": {
            "agent": "fixture-distiller",
            "model": "fixture-model",
            "prompt_hash": "sha256:" + "e" * 64,
        },
        "candidates": [
            {
                "candidate_id": "candidate_decimal_concept",
                "proposal_type": "concept",
                "suggested_id": "c_decimal_laban_spatial",
                "proposed_record": {
                    "kind": "prompt_technique",
                    "name": "Decimal spatial sampling",
                    "what": "Decimal values locate intermediate motion coordinates.",
                    "use_when": "A spatial move needs finer trajectory control.",
                    "nl_triggers": [
                        "decimal points for spatial movement",
                        "numeric spatial movement",
                        "fractional trajectory positions",
                    ],
                    "status": "ingested",
                    "evidence": [],
                    "source": ["rag://fixture/laban-decimals#spatial-precision"],
                    "layer": "spatial",
                },
                "source_evidence": [evidence],
                **created,
            },
            {
                "candidate_id": "candidate_decimal_edge",
                "proposal_type": "edge",
                "suggested_id": None,
                "proposed_record": {
                    "u": "c_decimal_laban_spatial",
                    "v": "c_laban_effort",
                    "type": "refines",
                    "context": "movement",
                    "authored_by": "rag_pipeline",
                    "note": "Decimal sampling specializes spatial movement control.",
                    "sources": [
                        {
                            "ref": "rag://fixture/laban-decimals",
                            "locator": "section:spatial-precision",
                        }
                    ],
                },
                "source_evidence": [evidence],
                **created,
            },
            {
                "candidate_id": "candidate_decimal_mapping",
                "proposal_type": "mapping",
                "suggested_id": None,
                "proposed_record": {
                    "concept_id": "c_decimal_laban_spatial",
                    "target_type": "control",
                    "target_id": "motion.laban.space_decimal_hypothesis",
                    "encoding": "numeric",
                    "mapping": {
                        "field": "space_position",
                        "value_type": "decimal",
                    },
                    "loss": "low",
                    "provider": None,
                    "model_version": None,
                    "sources": [
                        "rag://fixture/laban-decimals#spatial-precision"
                    ],
                },
                "source_evidence": [evidence],
                **created,
            },
        ],
    }


def _bundle_assignments(distillation: dict) -> dict[str, str]:
    decisions = {
        decision["candidate_id"]: decision
        for decision in distillation["candidate_decisions"]
    }
    return {
        decisions["candidate_decimal_concept"]["proposal_id"]:
            "c_decimal_laban_spatial",
        decisions["candidate_decimal_edge"]["proposal_id"]:
            "edge_000001",
        decisions["candidate_decimal_mapping"]["proposal_id"]:
            "mapping_000001",
    }


class CurateTests(unittest.TestCase):
    def test_polymath_distills_before_explicit_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [concept("c_lighting", "lighting", layer="lighting")],
            )
            proposed = {
                "kind": "technique",
                "name": "motivated light",
                "what": "Light whose visible source explains its direction.",
                "use_when": "natural cinematic staging",
                "nl_triggers": ["motivated light", "natural key", "source driven lighting"],
                "status": "ingested",
                "evidence": [],
                "source": ["polymath://fixture#p1"],
                "layer": "lighting",
            }
            batch = {
                "batch_id": "batch_fixture_curate",
                "retrieval": {
                    "adapter": "polymath_mcp",
                    "corpus_id": "fixture",
                    "query": "motivated lighting",
                    "tool": "search",
                    "parameters": {"top_k": 1},
                    "retrieved_at": "2026-07-30T00:00:00Z",
                },
                "extractor": {
                    "agent": "fixture-agent",
                    "model": "fixture-model",
                    "prompt_hash": "sha256:" + "a" * 64,
                },
                "candidates": [
                    {
                        "candidate_id": "candidate_fixture_001",
                        "proposal_type": "concept",
                        "suggested_id": "c_motivated_light",
                        "proposed_record": proposed,
                        "source_evidence": [
                            {
                                "source_id": "fixture",
                                "locator": "p1",
                                "claim": "The source describes motivated lighting.",
                                "content_sha256": "sha256:" + "b" * 64,
                            }
                        ],
                        "created_by": "polymath_mcp",
                        "created_at": "2026-07-30T00:00:00Z",
                    },
                    {
                        "candidate_id": "candidate_fixture_edge",
                        "proposal_type": "edge",
                        "suggested_id": None,
                        "proposed_record": {
                            "u": "c_motivated_light",
                            "v": "c_lighting",
                            "type": "refines",
                            "context": "lighting",
                            "authored_by": "polymath_proposal",
                            "note": "Motivated light is a lighting specialization.",
                            "sources": [
                                {"ref": "fixture", "locator": "p1"}
                            ],
                        },
                        "source_evidence": [
                            {
                                "source_id": "fixture",
                                "locator": "p1",
                                "claim": "The source places motivated light under lighting.",
                                "content_sha256": "sha256:" + "b" * 64,
                            }
                        ],
                        "created_by": "polymath_mcp",
                        "created_at": "2026-07-30T00:00:00Z",
                    },
                    {
                        "candidate_id": "candidate_fixture_mapping",
                        "proposal_type": "mapping",
                        "suggested_id": None,
                        "proposed_record": {
                            "concept_id": "c_motivated_light",
                            "target_type": "control",
                            "target_id": "lighting.motivated_source",
                            "encoding": "yaml",
                            "mapping": {"field": "motivated_source"},
                            "loss": "low",
                            "provider": None,
                            "model_version": None,
                            "sources": ["fixture#p1"],
                        },
                        "source_evidence": [
                            {
                                "source_id": "fixture",
                                "locator": "p1",
                                "claim": "The source supports a motivated-source control.",
                                "content_sha256": "sha256:" + "b" * 64,
                            }
                        ],
                        "created_by": "polymath_mcp",
                        "created_at": "2026-07-30T00:00:00Z",
                    },
                ],
            }
            distillation = run_distillation(batch, root)
            proposal_id = next(
                row["proposal_id"]
                for row in distillation["candidate_decisions"]
                if row["candidate_id"] == "candidate_fixture_001"
            )
            self.assertEqual(
                [row["id"] for row in read_jsonl(root / "lab/concepts.jsonl")],
                ["c_lighting"],
            )
            review = _review()
            with self.assertRaises(ValidationFailure):
                promote_proposal(
                    proposal_id,
                    "c_motivated_light",
                    "test_curator",
                    {},
                    root,
                )
            promoted = promote_proposal(
                proposal_id,
                "c_motivated_light",
                "test_curator",
                review,
                root,
            )
            self.assertEqual(promoted["id"], "c_motivated_light")
            self.assertEqual(len(read_jsonl(root / "lab/concepts.jsonl")), 2)
            with self.assertRaises(ValidationFailure):
                promote_proposal(
                    proposal_id,
                    "c_motivated_light_duplicate",
                    "test_curator",
                    review,
                    root,
                )

    def test_external_proposal_cannot_bypass_distillation(self) -> None:
        for created_by in ("polymath_mcp", "pegasus", "rag_pipeline"):
            with self.subTest(
                created_by=created_by
            ), tempfile.TemporaryDirectory() as directory:
                root = make_root(Path(directory))
                proposal = {
                    "proposal_id": "proposal_bypass_attempt",
                    "proposal_type": "concept",
                    "status": "pending",
                    "proposed_record": {
                        "kind": "technique",
                        "name": "Bypass attempt",
                        "what": "A valid-shaped record staged outside distillation.",
                        "use_when": "testing the enforcement boundary",
                        "nl_triggers": [
                            "bypass attempt",
                            "undistilled proposal",
                            "direct external staging",
                        ],
                        "status": "ingested",
                        "evidence": [],
                        "source": [f"{created_by}://fixture#bypass"],
                        "layer": "test",
                    },
                    "source_evidence": [
                        {
                            "source_id": f"{created_by}://fixture",
                            "locator": "chunk:bypass",
                            "claim": "The fixture supplies a source-shaped claim.",
                            "content_sha256": "sha256:" + "c" * 64,
                        }
                    ],
                    "created_by": created_by,
                    "created_at": "2026-07-30T00:00:00Z",
                }
                with self.assertRaises(ValidationFailure):
                    stage_proposal(proposal, root)
                validate_staging(root)
                with self.assertRaises(ValidationFailure):
                    promote_proposal(
                        proposal["proposal_id"],
                        "c_bypass_attempt",
                        "test_curator",
                        _review(),
                        root,
                    )

    def test_generic_rag_batch_promotes_bundle_and_compiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [concept(
                    "c_laban_effort",
                    "Laban effort",
                    layer="movement",
                )],
            )
            distillation = ingest_distillation_batch(_rag_batch(), root)
            self.assertEqual(distillation["summary"]["staged"], 3)

            promotion = promote_distillation_bundle(
                distillation["id"],
                _bundle_assignments(distillation),
                "test_curator",
                _review(),
                root,
            )
            self.assertEqual(
                promotion["promoted_ids"],
                [
                    "c_decimal_laban_spatial",
                    "edge_000001",
                    "mapping_000001",
                ],
            )
            self.assertEqual(ingest_status(root)["pending_proposals"], 0)
            self.assertEqual(ingest_status(root)["promoted_proposals"], 3)

            reasoning = reason(
                default_request(
                    "Laban effort",
                    target_format="json",
                    minimum_status="ingested",
                ),
                root,
            )
            selected = {
                item["id"] for item in reasoning["selected_concepts"]
            }
            self.assertIn("c_decimal_laban_spatial", selected)
            self.assertIn(
                "edge_000001",
                {item["edge_id"] for item in reasoning["path_taken"]},
            )
            compiled = compile_result(reasoning, "json", root)
            self.assertIn(
                "motion.laban.space_decimal_hypothesis",
                compiled["package"]["controls"],
            )
            self.assertIn(
                "knowledge_gap",
                compiled["package"]["explanation"],
            )
            self.assertEqual(
                compiled["package"]["explanation"]["sources"][
                    "c_decimal_laban_spatial"
                ],
                ["rag://fixture/laban-decimals#spatial-precision"],
            )

    def test_bundle_promotion_rolls_back_on_member_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [concept(
                    "c_laban_effort",
                    "Laban effort",
                    layer="movement",
                )],
            )
            distillation = ingest_distillation_batch(_rag_batch(), root)
            assignments = _bundle_assignments(distillation)
            edge_proposal_id = next(
                decision["proposal_id"]
                for decision in distillation["candidate_decisions"]
                if decision["candidate_id"] == "candidate_decimal_edge"
            )
            assignments[edge_proposal_id] = "invalid_edge_id"
            with self.assertRaises(ValidationFailure):
                promote_distillation_bundle(
                    distillation["id"],
                    assignments,
                    "test_curator",
                    _review(),
                    root,
                )
            self.assertEqual(
                [row["id"] for row in read_jsonl(root / "lab/concepts.jsonl")],
                ["c_laban_effort"],
            )
            self.assertEqual(
                read_jsonl(
                    root
                    / "lab"
                    / "second_brain"
                    / "curated"
                    / "edges.jsonl"
                ),
                [],
            )
            self.assertEqual(
                read_jsonl(
                    root
                    / "lab"
                    / "second_brain"
                    / "curated"
                    / "mappings.jsonl"
                ),
                [],
            )


if __name__ == "__main__":
    unittest.main()
