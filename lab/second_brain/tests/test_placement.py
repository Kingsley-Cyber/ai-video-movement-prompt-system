from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.curate import promote_distillation_bundle
from lab.second_brain.src.distill import run_distillation
from lab.second_brain.src.placement import (
    inspect_graph_growth_plan,
    plan_graph_growth,
)
from lab.second_brain.src.source_registry import load_source_units
from lab.second_brain.src.validate import (
    ValidationFailure,
    read_jsonl,
    validate_staging,
)
from lab.second_brain.tests.helpers import (
    concept,
    make_root,
    representation_strategy,
    write_rows,
)
from lab.second_brain.tests.test_source_registry import (
    _complete_no_candidate_session,
)


def _review() -> dict:
    return {
        "source_verified": True,
        "source_locator_resolved": True,
        "duplicate_checked": True,
        "operationally_useful": True,
        "relationships_validated": True,
        "numeric_precision_supported": True,
        "reviewed_at": "2026-08-07T00:00:00Z",
        "notes": "placement canary review",
    }


def _batch() -> dict:
    evidence = {
        "source_id": "file:research/decimal-motion.md",
        "locator": "heading:spatial-precision",
        "claim": "Decimal positions can express intermediate spatial movement.",
        "content_sha256": "sha256:" + "d" * 64,
    }
    common = {
        "created_by": "local_source",
        "created_at": "2026-08-07T00:00:00Z",
    }
    return {
        "batch_id": "batch_placement_canary",
        "retrieval": {
            "adapter": "local_fixture",
            "corpus_id": "placement-canary",
            "query": "decimal spatial movement",
            "tool": "local_extract",
            "parameters": {},
            "retrieved_at": "2026-08-07T00:00:00Z",
        },
        "extractor": {
            "agent": "fixture-agent",
            "model": "fixture-model",
            "prompt_hash": "sha256:" + "e" * 64,
        },
        "candidates": [
            {
                "candidate_id": "candidate_decimal_concept",
                "proposal_type": "concept",
                "suggested_id": "c_decimal_laban_spatial",
                "proposed_record": {
                    "kind": "technique",
                    "name": "Decimal spatial sampling",
                    "what": "Decimal values locate intermediate motion coordinates.",
                    "use_when": "A spatial move needs finer trajectory control.",
                    "nl_triggers": [
                        "decimal spatial movement",
                        "numeric spatial movement",
                        "fractional trajectory positions",
                    ],
                    "status": "ingested",
                    "evidence": [],
                    "source": ["file:research/decimal-motion.md#spatial-precision"],
                    "layer": "motion path authoring",
                },
                "source_evidence": [evidence],
                **common,
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
                    "authored_by": "local_source",
                    "note": "Decimal sampling specializes spatial movement control.",
                    "sources": [
                        {
                            "ref": "file:research/decimal-motion.md",
                            "locator": "heading:spatial-precision",
                        }
                    ],
                },
                "source_evidence": [evidence],
                **common,
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
                    "mapping": {"field": "space_position", "value_type": "decimal"},
                    "representation_strategy": representation_strategy(
                        "motion.laban.space_decimal_hypothesis"
                    ),
                    "loss": "low",
                    "provider": None,
                    "model_version": None,
                    "sources": ["file:research/decimal-motion.md#spatial-precision"],
                },
                "source_evidence": [evidence],
                **common,
            },
        ],
    }


def _root(base: Path) -> Path:
    root = make_root(base, [concept("c_laban_effort", "Laban effort", "whole-body movement")])
    write_rows(
        root / "lab" / "second_brain" / "staging" / "graph_growth_plans.jsonl",
        [],
    )
    (root / "lab" / "registry.yaml").write_text(
        "scripts:\n"
        "  second_brain_graph_growth_plans: "
        "second_brain/staging/graph_growth_plans.jsonl\n",
        encoding="utf-8",
    )
    return root


def _assignments(run: dict) -> dict[str, str]:
    by_candidate = {
        row["candidate_id"]: row for row in run["candidate_decisions"]
    }
    return {
        by_candidate["candidate_decimal_concept"]["proposal_id"]:
            "c_decimal_laban_spatial",
        by_candidate["candidate_decimal_edge"]["proposal_id"]:
            "edge_900001",
        by_candidate["candidate_decimal_mapping"]["proposal_id"]:
            "mapping_placement_canary",
    }


class OntologyPlacementTests(unittest.TestCase):
    def test_plan_is_replay_stable_and_does_not_mutate_curated_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _root(Path(temporary))
            run = run_distillation(_batch(), root)
            assignments = _assignments(run)
            curated_before = {
                path: path.read_bytes()
                for path in [
                    root / "lab" / "concepts.jsonl",
                    *sorted((root / "lab" / "second_brain" / "curated").glob("*.jsonl")),
                ]
            }
            first = plan_graph_growth(run["id"], assignments, root)
            second = plan_graph_growth(run["id"], assignments, root)
            self.assertEqual(first, second)
            self.assertTrue(first["promotion_ready"])
            self.assertEqual(first["blocked_proposal_ids"], [])
            self.assertEqual(len(read_jsonl(
                root / "lab" / "second_brain" / "staging" / "graph_growth_plans.jsonl"
            )), 1)
            by_type = {row["proposal_type"]: row for row in first["placements"]}
            self.assertEqual(by_type["concept"]["disposition"], "refine")
            self.assertEqual(by_type["edge"]["disposition"], "extend")
            self.assertEqual(by_type["mapping"]["disposition"], "extend")
            self.assertEqual(
                by_type["concept"]["graph"]["parent_concept_ids"],
                ["c_laban_effort"],
            )
            self.assertEqual(
                by_type["mapping"]["controls"]["namespaces"], ["motion"]
            )
            inspection = inspect_graph_growth_plan(first["id"], root)
            self.assertTrue(inspection["current"])
            self.assertEqual(
                curated_before,
                {path: path.read_bytes() for path in curated_before},
            )
            self.assertEqual(validate_staging(root)["graph_growth_plans"], 1)

    def test_promotion_fails_without_plan_and_binds_exact_plan_afterward(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _root(Path(temporary))
            run = run_distillation(_batch(), root)
            assignments = _assignments(run)
            with self.assertRaisesRegex(ValidationFailure, "ontology placement plan"):
                promote_distillation_bundle(
                    run["id"], assignments, "owner-test", _review(), root
                )
            plan = plan_graph_growth(run["id"], assignments, root)
            changed = dict(assignments)
            changed[next(iter(changed))] = "c_wrong_assignment"
            with self.assertRaisesRegex(ValidationFailure, "ontology placement plan"):
                promote_distillation_bundle(
                    run["id"], changed, "owner-test", _review(), root
                )
            promoted = promote_distillation_bundle(
                run["id"], assignments, "owner-test", _review(), root
            )
            self.assertEqual(promoted["growth_plan"]["id"], plan["id"])
            for record in promoted["records"]:
                binding = record["provenance"]["validation"]["ontology_placement"]
                self.assertEqual(binding["growth_plan_id"], plan["id"])
                self.assertIn(
                    binding["disposition"], {"refine", "extend"}
                )

    def test_exact_duplicate_merges_and_declared_alias_ambiguity_needs_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            duplicate_record = dict(_batch()["candidates"][0]["proposed_record"])
            duplicate_record["id"] = "c_decimal_laban_spatial"
            duplicate_root = make_root(base / "duplicate", [duplicate_record])
            write_rows(
                duplicate_root / "lab" / "second_brain" / "staging" / "graph_growth_plans.jsonl",
                [],
            )
            (duplicate_root / "lab" / "registry.yaml").write_text(
                "scripts:\n  second_brain_graph_growth_plans: "
                "second_brain/staging/graph_growth_plans.jsonl\n",
                encoding="utf-8",
            )
            duplicate_batch = _batch()
            duplicate_batch["batch_id"] = "batch_placement_duplicate"
            duplicate_batch["candidates"] = [duplicate_batch["candidates"][0]]
            duplicate_run = run_distillation(duplicate_batch, duplicate_root)
            duplicate_plan = plan_graph_growth(
                duplicate_run["id"], {}, duplicate_root
            )
            self.assertEqual(
                duplicate_plan["placements"][0]["disposition"], "merge"
            )
            self.assertFalse(duplicate_plan["promotion_ready"])

            ambiguous_root = make_root(
                base / "ambiguous",
                [
                    concept("c_phase_landmarks", "Phase landmarks", "animation timing"),
                    concept("c_secondary_motion", "Secondary motion", "whole-body movement"),
                ],
            )
            write_rows(
                ambiguous_root / "lab" / "second_brain" / "staging" / "graph_growth_plans.jsonl",
                [],
            )
            (ambiguous_root / "lab" / "registry.yaml").write_text(
                "scripts:\n  second_brain_graph_growth_plans: "
                "second_brain/staging/graph_growth_plans.jsonl\n",
                encoding="utf-8",
            )
            ambiguous_batch = _batch()
            ambiguous_batch["batch_id"] = "batch_placement_ambiguous"
            candidate = ambiguous_batch["candidates"][0]
            candidate["suggested_id"] = "c_follow_through_new"
            candidate["proposed_record"].update(
                {
                    "name": "Follow through",
                    "nl_triggers": [
                        "follow through",
                        "continuing action",
                        "motion continuation",
                    ],
                }
            )
            ambiguous_batch["candidates"] = [candidate]
            ambiguous_run = run_distillation(ambiguous_batch, ambiguous_root)
            ambiguous_assignments = {
                row["proposal_id"]: "c_follow_through_new"
                for row in ambiguous_run["candidate_decisions"]
                if row["proposal_id"] is not None
            }
            ambiguous_plan = plan_graph_growth(
                ambiguous_run["id"], ambiguous_assignments, ambiguous_root
            )
            placement = ambiguous_plan["placements"][0]
            self.assertEqual(placement["disposition"], "needs_review")
            self.assertIn(
                "declared_ambiguous_alias:follow through",
                placement["promotion"]["reasons"],
            )

    def test_live_source_registry_is_resolved_into_every_placement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = _root(base)
            source = base / "source"
            source.mkdir()
            (source / "movement.md").write_text(
                "# Spatial precision\n\nDecimal positions can express intermediate movement.\n",
                encoding="utf-8",
            )
            _complete_no_candidate_session(root, source)
            unit = load_source_units(root)[0]
            (root / "lab" / "registry.yaml").write_text(
                "scripts:\n"
                "  second_brain_graph_growth_plans: "
                "second_brain/staging/graph_growth_plans.jsonl\n"
                "  second_brain_source_units: "
                "second_brain/immutable/source_units.jsonl\n",
                encoding="utf-8",
            )
            batch = _batch()
            batch["batch_id"] = "batch_placement_source_closed"
            for candidate in batch["candidates"]:
                candidate["source_evidence"] = [
                    {
                        "source_id": unit["source_ref"],
                        "locator": unit["locator"],
                        "claim": "The preserved passage supports the placement canary.",
                        "content_sha256": unit["content_sha256"],
                    }
                ]
            run = run_distillation(batch, root)
            plan = plan_graph_growth(run["id"], _assignments(run), root)
            self.assertTrue(plan["promotion_ready"])
            self.assertTrue(
                all(
                    placement["source_unit_ids"] == [unit["id"]]
                    and placement["coverage"]["source_closed"]
                    for placement in plan["placements"]
                )
            )


if __name__ == "__main__":
    unittest.main()
