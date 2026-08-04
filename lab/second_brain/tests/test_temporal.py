from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from lab.second_brain.src import curation_journal
from lab.second_brain.src.compile import compile_result
from lab.second_brain.src.context import build_context_bundle
from lab.second_brain.src.curation_journal import curation_journal_status
from lab.second_brain.src.graph import validate_edge_distribution
from lab.second_brain.src.graph import build_live_graph
from lab.second_brain.src.indexes import build_index_catalog
from lab.second_brain.src.migrate import consolidate_reciprocal_edges
from lab.second_brain.src.query import default_request, reason
from lab.second_brain.src.reflect import rebuild
from lab.second_brain.src.validate import ValidationFailure, validate_curated
from lab.second_brain.src.validate import REPO_ROOT, read_jsonl
from lab.second_brain.tests.helpers import concept, make_root, write_rows


def validity(
    *,
    valid_from: str,
    valid_until: str | None,
    status: str,
    supersedes: list[str],
    superseded_by: list[str],
) -> dict:
    return {
        "valid_from": valid_from,
        "valid_until": valid_until,
        "status": status,
        "supersedes": supersedes,
        "superseded_by": superseded_by,
    }


def temporal_root(base: Path) -> Path:
    old = {
        **concept("c_restraint_old", "restrained motion guidance", "motion"),
        "what": "Earlier restrained motion guidance uses a broad contained movement instruction.",
        "validity": validity(
            valid_from="2025-01-01T00:00:00Z",
            valid_until="2026-01-01T00:00:00Z",
            status="superseded",
            supersedes=[],
            superseded_by=["c_restraint_current"],
        ),
    }
    current = {
        **concept("c_restraint_current", "restrained motion guidance", "motion"),
        "what": "Current restrained motion guidance preserves contained continuation and explicit release limits.",
        "validity": validity(
            valid_from="2026-01-01T00:00:00Z",
            valid_until=None,
            status="active",
            supersedes=["c_restraint_old"],
            superseded_by=[],
        ),
    }
    root = make_root(base, [old, current])
    write_rows(
        root / "lab/second_brain/curated/mappings.jsonl",
        [
            {
                "id": "mapping_restraint_old",
                "concept_id": "c_restraint_old",
                "target_type": "control",
                "target_id": "performance.motion_restraint",
                "encoding": "json",
                "mapping": {"release_limit": "broad"},
                "loss": "low",
                "provider": None,
                "model_version": None,
                "sources": ["fixture://old"],
                "validity": validity(
                    valid_from="2025-01-01T00:00:00Z",
                    valid_until="2026-01-01T00:00:00Z",
                    status="superseded",
                    supersedes=[],
                    superseded_by=["mapping_restraint_current"],
                ),
            },
            {
                "id": "mapping_restraint_current",
                "concept_id": "c_restraint_current",
                "target_type": "control",
                "target_id": "performance.motion_restraint",
                "encoding": "json",
                "mapping": {"release_limit": "explicit"},
                "loss": "low",
                "provider": None,
                "model_version": None,
                "sources": ["fixture://current"],
                "validity": validity(
                    valid_from="2026-01-01T00:00:00Z",
                    valid_until=None,
                    status="active",
                    supersedes=["mapping_restraint_old"],
                    superseded_by=[],
                ),
            },
        ],
    )
    return root


class TemporalKnowledgeTests(unittest.TestCase):
    @staticmethod
    def _reciprocal_root(base: Path) -> Path:
        root = make_root(
            base,
            [
                concept("c_alpha", "alpha motion"),
                concept("c_beta", "beta motion"),
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
                    "authored_by": "legacy_migration",
                    "note": "first legacy direction",
                    "sources": [
                        {"ref": "fixture://alpha", "locator": "section:a"},
                        {"ref": "fixture://shared", "locator": None},
                    ],
                },
                {
                    "id": "edge_000002",
                    "u": "c_beta",
                    "v": "c_alpha",
                    "type": "pairs_with",
                    "context": "all",
                    "authored_by": "legacy_migration",
                    "note": "second legacy direction",
                    "sources": [
                        {"ref": "fixture://beta", "locator": "section:b"},
                        {"ref": "fixture://shared", "locator": None},
                    ],
                },
            ],
        )
        return root

    def test_reciprocal_migration_preserves_sources_history_and_idempotency(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._reciprocal_root(Path(directory))
            result = consolidate_reciprocal_edges(
                "2026-08-04T00:00:00Z",
                "test_curator",
                root,
            )
            self.assertEqual(result["status"], "applied")
            self.assertEqual(result["reciprocal_groups"], 1)
            self.assertEqual(result["predecessor_edges_superseded"], 2)
            self.assertTrue(result["source_references_preserved"])

            rows = read_jsonl(root / "lab/second_brain/curated/edges.jsonl")
            self.assertEqual([row["id"] for row in rows], [
                "edge_000001",
                "edge_000002",
                "edge_000003",
            ])
            successor = rows[2]
            self.assertEqual(
                successor["validity"]["supersedes"],
                ["edge_000001", "edge_000002"],
            )
            self.assertEqual(
                successor["sources"],
                [
                    {"ref": "fixture://alpha", "locator": "section:a"},
                    {"ref": "fixture://beta", "locator": "section:b"},
                    {"ref": "fixture://shared", "locator": None},
                ],
            )
            self.assertTrue(
                all(
                    row["validity"]["superseded_by"] == ["edge_000003"]
                    for row in rows[:2]
                )
            )

            current_graph = build_live_graph(root, include_derived=False)
            self.assertEqual(list(current_graph.edges(keys=True)), [
                ("c_alpha", "c_beta", "edge_000003")
            ])
            historical_graph = build_live_graph(
                root,
                include_derived=False,
                validity_mode="historical",
                as_of="2026-08-03T23:59:59Z",
            )
            self.assertEqual(
                {key for _, _, key in historical_graph.edges(keys=True)},
                {"edge_000001", "edge_000002"},
            )
            catalog = build_index_catalog(root)
            self.assertEqual(catalog["edge_distribution"]["pairs_with"], 1)
            self.assertEqual(catalog["edge_distribution"]["reciprocal_pairs_with"], 0)
            historical_catalog = build_index_catalog(
                root,
                validity_mode="historical",
                as_of="2026-08-03T23:59:59Z",
            )
            self.assertEqual(
                {
                    item["edge_id"]
                    for items in historical_catalog["typed_adjacency"].values()
                    for item in items
                },
                {"edge_000001", "edge_000002"},
            )
            self.assertEqual(
                historical_catalog["edge_distribution"]["pairs_with"],
                1,
            )
            all_versions_catalog = build_index_catalog(
                root,
                validity_mode="all_versions",
            )
            self.assertEqual(
                {
                    item["edge_id"]
                    for items in all_versions_catalog["typed_adjacency"].values()
                    for item in items
                },
                {"edge_000001", "edge_000002", "edge_000003"},
            )
            self.assertEqual(curation_journal_status(root)["committed_receipts"], 1)

            replay = consolidate_reciprocal_edges(
                "2026-08-04T00:00:00Z",
                "test_curator",
                root,
            )
            self.assertEqual(replay["status"], "no_change")
            self.assertEqual(curation_journal_status(root)["committed_receipts"], 1)

            write_rows(
                root / "lab/second_brain/curated/edges.jsonl",
                rows
                + [
                    {
                        "id": "edge_000004",
                        "u": "c_beta",
                        "v": "c_alpha",
                        "type": "pairs_with",
                        "context": "all",
                        "authored_by": "future_curator",
                        "note": "regression fixture",
                        "sources": [{"ref": "fixture://future", "locator": None}],
                    }
                ],
            )
            with self.assertRaisesRegex(
                ValidationFailure,
                "repeat symmetric relationships",
            ):
                validate_curated(root)

    def test_reciprocal_migration_rolls_back_and_can_retry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._reciprocal_root(Path(directory))
            original = curation_journal._replace_manifest
            failed = False

            def fail_first_commit(*args: object, **kwargs: object) -> dict:
                nonlocal failed
                state = args[2] if len(args) > 2 else kwargs["state"]
                if state == "committed" and not failed:
                    failed = True
                    raise OSError("fixture commit-marker failure")
                return original(*args, **kwargs)

            with mock.patch.object(
                curation_journal,
                "_replace_manifest",
                side_effect=fail_first_commit,
            ), self.assertRaisesRegex(OSError, "commit-marker"):
                consolidate_reciprocal_edges(
                    "2026-08-04T00:00:00Z",
                    "test_curator",
                    root,
                )
            self.assertEqual(
                [row["id"] for row in read_jsonl(
                    root / "lab/second_brain/curated/edges.jsonl"
                )],
                ["edge_000001", "edge_000002"],
            )
            self.assertEqual(curation_journal_status(root)["recovered_receipts"], 1)
            retry = consolidate_reciprocal_edges(
                "2026-08-04T00:00:00Z",
                "test_curator",
                root,
            )
            self.assertEqual(retry["status"], "applied")

    def test_current_historical_and_all_versions_return_replacement_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = temporal_root(Path(directory))
            current = reason(
                default_request("restrained motion guidance", minimum_status="ingested"),
                root,
            )
            self.assertEqual(
                [row["id"] for row in current["selected_concepts"]],
                ["c_restraint_current"],
            )
            current_trace = current["temporal_query"]["replacement_traces"][0]
            self.assertEqual(current_trace["predecessors"], ["c_restraint_old"])
            self.assertEqual(current_trace["current_head"], "c_restraint_current")

            historical = reason(
                default_request(
                    "restrained motion guidance",
                    minimum_status="ingested",
                    validity_mode="historical",
                    as_of="2025-06-01T00:00:00Z",
                ),
                root,
            )
            self.assertEqual(
                [row["id"] for row in historical["selected_concepts"]],
                ["c_restraint_old"],
            )
            historical_trace = historical["temporal_query"]["replacement_traces"][0]
            self.assertEqual(historical_trace["successors"], ["c_restraint_current"])
            self.assertEqual(historical_trace["current_head"], "c_restraint_current")

            all_versions = reason(
                default_request(
                    "restrained motion guidance",
                    minimum_status="ingested",
                    validity_mode="all_versions",
                ),
                root,
            )
            self.assertEqual(
                {row["id"] for row in all_versions["selected_concepts"]},
                {"c_restraint_old", "c_restraint_current"},
            )

    def test_context_and_compiler_use_the_same_temporal_mapping_view(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = temporal_root(Path(directory))
            current = build_context_bundle(
                "restrained motion guidance",
                token_budget=8_000,
                minimum_status="ingested",
                include_external_evidence=False,
                root=root,
            )
            self.assertEqual([row["id"] for row in current["mappings"]], ["mapping_restraint_current"])
            self.assertEqual(current["temporal"]["replacement_traces"][0]["predecessors"], ["c_restraint_old"])

            historical_reasoning = reason(
                default_request(
                    "restrained motion guidance",
                    minimum_status="ingested",
                    validity_mode="historical",
                    as_of="2025-06-01T00:00:00Z",
                ),
                root,
            )
            compiled = compile_result(historical_reasoning, "json", root)
            self.assertEqual(
                [row["id"] for row in compiled["package"]["mappings"]],
                ["mapping_restraint_old"],
            )

    def test_invalid_or_cyclic_supersession_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = temporal_root(Path(directory))
            concepts_path = root / "lab/concepts.jsonl"
            rows = [json.loads(line) for line in concepts_path.read_text().splitlines()]
            rows[1]["validity"]["supersedes"] = []
            write_rows(concepts_path, rows)
            with self.assertRaisesRegex(ValidationFailure, "non-reciprocal"):
                validate_curated(root)

            rows[1]["validity"]["supersedes"] = ["c_restraint_old"]
            rows[0]["validity"] = validity(
                valid_from="2025-01-01T00:00:00Z",
                valid_until="2026-01-01T00:00:00Z",
                status="superseded",
                supersedes=["c_restraint_current"],
                superseded_by=["c_restraint_current"],
            )
            rows[1]["validity"]["supersedes"] = ["c_restraint_old"]
            rows[1]["validity"]["superseded_by"] = ["c_restraint_old"]
            rows[1]["validity"]["status"] = "superseded"
            rows[1]["validity"]["valid_until"] = "2027-01-01T00:00:00Z"
            write_rows(concepts_path, rows)
            with self.assertRaisesRegex(ValidationFailure, "replacement directions overlap|cycle"):
                validate_curated(root)

    def test_index_catalog_rebuilds_and_exposes_every_required_family(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = temporal_root(Path(directory))
            current = build_index_catalog(root)
            historical = build_index_catalog(
                root,
                validity_mode="historical",
                as_of="2025-06-01T00:00:00Z",
            )
            required = {
                "lexical_concepts",
                "aliases",
                "dense_semantic_concepts",
                "typed_adjacency",
                "prerequisite_closure",
                "conflicts",
                "temporal_validity",
                "supersession",
                "concept_to_source",
                "concept_to_evidence",
                "intent_to_concept",
                "control_to_provider",
                "provider_performance",
                "experiments",
                "video_observations",
            }
            self.assertTrue(required <= set(current))
            self.assertEqual(set(current["dense_semantic_concepts"]["vectors"]), {"c_restraint_current"})
            self.assertEqual(set(historical["dense_semantic_concepts"]["vectors"]), {"c_restraint_old"})
            self.assertEqual(set(current["prerequisite_closure"]), {"c_restraint_current"})
            self.assertEqual(set(historical["prerequisite_closure"]), {"c_restraint_old"})
            self.assertEqual(set(current["concept_to_source"]), {"c_restraint_current"})
            self.assertEqual(set(historical["concept_to_source"]), {"c_restraint_old"})
            self.assertEqual(
                set(current["control_to_provider"]),
                {"performance.motion_restraint"},
            )
            first = rebuild(root)
            second = rebuild(root)
            self.assertEqual(first, second)

    def test_vector_ranking_cannot_override_conflict_and_latency_budget(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [
                    concept("c_alpha", "restrained spatial movement", "motion"),
                    concept("c_beta", "restrained spatial motion", "motion"),
                ],
            )
            write_rows(
                root / "lab/second_brain/curated/edges.jsonl",
                [
                    {
                        "id": "edge_000001",
                        "u": "c_alpha",
                        "v": "c_beta",
                        "type": "conflicts_with",
                        "context": "all",
                        "authored_by": "fixture",
                        "note": "Mutually exclusive fixture choices.",
                        "sources": [{"ref": "fixture://conflict", "locator": None}],
                    }
                ],
            )
            started = time.perf_counter()
            result = reason(
                default_request("restrained spatial movement", minimum_status="ingested"),
                root,
            )
            elapsed = time.perf_counter() - started
            self.assertLess(elapsed, 1.0)
            self.assertTrue(result["retrieval_candidates"]["vector"])
            self.assertTrue(result["retrieval_candidates"]["hard_constraints_override_ranking"])
            selected = {row["id"] for row in result["selected_concepts"]}
            rejected = {row["id"] for row in result["rejected_concepts"]}
            self.assertEqual(len(selected), 1)
            self.assertEqual(len(rejected), 1)

            valid = [
                {
                    "id": f"edge_{index:06d}",
                    "type": "pairs_with",
                    "u": f"c_left_{index:06d}",
                    "v": f"c_right_{index:06d}",
                    "context": "all",
                }
                for index in range(1, 159)
            ]
            typed = [
                {"id": f"edge_{index:06d}", "type": "refines"}
                for index in range(159, 196)
            ]
            self.assertEqual(
                validate_edge_distribution(valid + typed)["pairs_with"],
                158,
            )
            with self.assertRaisesRegex(ValueError, "count 159"):
                validate_edge_distribution(
                    valid
                    + [
                        {
                            "id": "edge_000196",
                            "type": "pairs_with",
                            "u": "c_left_extra",
                            "v": "c_right_extra",
                            "context": "all",
                        }
                    ]
                    + typed
                )
            migrated = {
                row["id"]: row
                for row in read_jsonl(
                    REPO_ROOT / "lab/second_brain/curated/edges.jsonl"
                )
                if row["id"] in {
                    "edge_000065",
                    "edge_000086",
                    "edge_000136",
                    "edge_000166",
                }
            }
            self.assertEqual(
                {key: value["type"] for key, value in migrated.items()},
                {
                    "edge_000065": "applies_to",
                    "edge_000086": "produces",
                    "edge_000136": "requires",
                    "edge_000166": "requires",
                },
            )
            self.assertTrue(
                all(row["sources"] and row["authored_by"] == "slice8_typed_migration" for row in migrated.values())
            )


if __name__ == "__main__":
    unittest.main()
