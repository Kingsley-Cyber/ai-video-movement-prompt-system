from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lab.second_brain.src.graph import build_live_graph, traversal_steps
from lab.second_brain.src.migrate import reclassify_reviewed_edges
from lab.second_brain.src.temporal import replacement_trace, visible_records
from lab.second_brain.src.validate import (
    REPO_ROOT,
    ValidationFailure,
    read_jsonl,
    sha256_value,
    validate_curated,
    validate_instance,
)
from lab.second_brain.tests.helpers import concept, make_root, write_rows


EFFECTIVE_AT = "2026-08-04T12:00:00Z"


def edge(
    edge_id: str,
    u: str,
    v: str,
    source: str,
) -> dict:
    return {
        "id": edge_id,
        "u": u,
        "v": v,
        "type": "pairs_with",
        "context": "all",
        "authored_by": "legacy_migration",
        "note": "legacy association",
        "sources": [{"ref": source, "locator": "section-1"}],
    }


def review_for(edges: list[dict]) -> dict:
    decisions = []
    types = {
        "edge_000001": ("c_alpha", "c_beta", "requires"),
        "edge_000002": ("c_gamma", "c_beta", "applies_to"),
    }
    for row in edges:
        new_u, new_v, new_type = types[row["id"]]
        decisions.append(
            {
                "predecessor_id": row["id"],
                "predecessor_hash": sha256_value(row),
                "new_u": new_u,
                "new_v": new_v,
                "new_type": new_type,
                "rationale": f"Reviewed source supports {new_type} semantics.",
                "evidence": copy.deepcopy(row["sources"]),
                "source_verified": True,
                "relationship_validated": True,
                "approved": True,
            }
        )
    return {
        "schema": "cpcs.edge_retype_review/1.0",
        "review_id": "edge_review_fixture_cluster",
        "scope": "typed_edge_reclassification",
        "reviewed_at": EFFECTIVE_AT,
        "effective_at": EFFECTIVE_AT,
        "reviewed_by": "owner-test",
        "decisions": decisions,
    }


class ReviewedEdgeReclassificationTests(unittest.TestCase):
    def make_fixture(self, directory: str) -> tuple[Path, list[dict], dict]:
        root = make_root(
            Path(directory),
            [
                concept("c_alpha", "alpha"),
                concept("c_beta", "beta"),
                concept("c_gamma", "gamma"),
            ],
        )
        edges = [
            edge("edge_000001", "c_alpha", "c_beta", "fixture://alpha-beta"),
            edge("edge_000002", "c_beta", "c_gamma", "fixture://beta-gamma"),
        ]
        write_rows(root / "lab/second_brain/curated/edges.jsonl", edges)
        review = review_for(edges)
        validate_instance("edge_retype_review", review, root)
        return root, edges, review

    def test_reviewed_batch_preserves_lineage_sources_and_typed_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, predecessors, review = self.make_fixture(directory)

            result = reclassify_reviewed_edges(review, "owner-test", root)

            self.assertEqual(result["status"], "applied")
            self.assertEqual(result["predecessor_ids"], ["edge_000001", "edge_000002"])
            self.assertEqual(result["successor_ids"], ["edge_000003", "edge_000004"])
            self.assertTrue(result["semantic_edge_type_changed"])
            self.assertTrue(result["source_references_preserved"])
            rows = read_jsonl(root / "lab/second_brain/curated/edges.jsonl")
            current = visible_records(rows)
            self.assertEqual(
                [(row["id"], row["u"], row["v"], row["type"]) for row in current],
                [
                    ("edge_000003", "c_alpha", "c_beta", "requires"),
                    ("edge_000004", "c_gamma", "c_beta", "applies_to"),
                ],
            )
            by_id = {row["id"]: row for row in rows}
            for predecessor, successor_id in zip(predecessors, result["successor_ids"]):
                self.assertEqual(by_id[successor_id]["sources"], predecessor["sources"])
                self.assertEqual(
                    replacement_trace(predecessor["id"], rows)["current_head"],
                    successor_id,
                )
            historical = visible_records(
                rows,
                validity_mode="historical",
                as_of="2026-08-04T11:59:59Z",
            )
            self.assertEqual([row["id"] for row in historical], ["edge_000001", "edge_000002"])
            graph = build_live_graph(root, include_derived=False)
            steps = traversal_steps(graph, "c_alpha")
            self.assertEqual(
                [(row["edge_type"], row["transition"], row["neighbor"]) for row in steps],
                [("requires", "requires", "c_beta")],
            )
            validate_curated(root)

            correction = {
                "schema": "cpcs.edge_retype_review/1.0",
                "review_id": "edge_review_fixture_correction",
                "scope": "typed_edge_reclassification",
                "reviewed_at": "2026-08-04T12:01:00Z",
                "effective_at": "2026-08-04T12:01:00Z",
                "reviewed_by": "owner-test",
                "decisions": [
                    {
                        "predecessor_id": "edge_000003",
                        "predecessor_hash": sha256_value(by_id["edge_000003"]),
                        "new_u": "c_beta",
                        "new_v": "c_alpha",
                        "new_type": "applies_to",
                        "rationale": "Reviewed correction changes dependency to policy applicability.",
                        "evidence": copy.deepcopy(by_id["edge_000003"]["sources"]),
                        "source_verified": True,
                        "relationship_validated": True,
                        "approved": True,
                    }
                ],
            }
            no_op = copy.deepcopy(correction)
            no_op["review_id"] = "edge_review_fixture_no_op"
            no_op["decisions"][0]["new_u"] = "c_alpha"
            no_op["decisions"][0]["new_v"] = "c_beta"
            no_op["decisions"][0]["new_type"] = "requires"
            with self.assertRaisesRegex(ValidationFailure, "change relationship semantics"):
                reclassify_reviewed_edges(no_op, "owner-test", root)
            corrected = reclassify_reviewed_edges(correction, "owner-test", root)
            self.assertEqual(corrected["status"], "applied")
            self.assertEqual(corrected["successor_ids"], ["edge_000005"])
            corrected_rows = read_jsonl(
                root / "lab/second_brain/curated/edges.jsonl"
            )
            trace = replacement_trace("edge_000001", corrected_rows)
            self.assertEqual(trace["successors"], ["edge_000003", "edge_000005"])
            self.assertEqual(trace["current_head"], "edge_000005")
            current_by_id = {
                row["id"]: row for row in visible_records(corrected_rows)
            }
            self.assertEqual(
                (
                    current_by_id["edge_000005"]["u"],
                    current_by_id["edge_000005"]["v"],
                    current_by_id["edge_000005"]["type"],
                ),
                ("c_beta", "c_alpha", "applies_to"),
            )
            validate_curated(root)

    def test_exact_review_replays_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, _, review = self.make_fixture(directory)
            first = reclassify_reviewed_edges(review, "owner-test", root)
            path = root / "lab/second_brain/curated/edges.jsonl"
            before = path.read_bytes()

            replay = reclassify_reviewed_edges(review, "owner-test", root)

            self.assertEqual(first["successor_ids"], replay["successor_ids"])
            self.assertEqual(replay["status"], "no_change")
            self.assertEqual(before, path.read_bytes())
            changed = copy.deepcopy(review)
            changed["decisions"][0]["rationale"] = "Different reviewed meaning."
            with self.assertRaisesRegex(ValidationFailure, "review_id"):
                reclassify_reviewed_edges(changed, "owner-test", root)

            report_path = root / "lab/second_brain/MIGRATION_REPORT.json"
            report_path.unlink()
            recovered = reclassify_reviewed_edges(review, "owner-test", root)
            self.assertEqual(recovered["status"], "no_change")
            report = json.loads(report_path.read_text())
            self.assertTrue(
                report["reviewed_edge_reclassifications"][0][
                    "report_recovered_from_curated_lineage"
                ]
            )
            tampered_rows = read_jsonl(path)
            tampered_rows[0]["note"] = "tampered predecessor meaning"
            write_rows(path, tampered_rows)
            with self.assertRaisesRegex(ValidationFailure, "predecessor hash is stale"):
                reclassify_reviewed_edges(review, "owner-test", root)

    def test_review_rejects_stale_identity_scope_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, _, review = self.make_fixture(directory)
            cases = []
            stale = copy.deepcopy(review)
            stale["decisions"][0]["predecessor_hash"] = "sha256:" + "0" * 64
            cases.append((stale, "stale"))
            endpoints = copy.deepcopy(review)
            endpoints["decisions"][0]["new_v"] = "c_gamma"
            cases.append((endpoints, "endpoints"))
            evidence = copy.deepcopy(review)
            evidence["decisions"][0]["evidence"][0]["ref"] = "fixture://forged"
            cases.append((evidence, "evidence"))
            unsorted = copy.deepcopy(review)
            unsorted["decisions"].reverse()
            cases.append((unsorted, "sorted"))
            for value, message in cases:
                with self.subTest(message=message):
                    with self.assertRaisesRegex(ValidationFailure, message):
                        reclassify_reviewed_edges(value, "owner-test", root)
            with self.assertRaisesRegex(ValidationFailure, "reviewed_by"):
                reclassify_reviewed_edges(review, "different-curator", root)

    def test_failed_journal_application_leaves_curated_bytes_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, _, review = self.make_fixture(directory)
            path = root / "lab/second_brain/curated/edges.jsonl"
            before = path.read_bytes()
            with mock.patch(
                "lab.second_brain.src.migrate.apply_curated_transaction",
                side_effect=RuntimeError("fixture journal failure"),
            ):
                with self.assertRaisesRegex(RuntimeError, "journal failure"):
                    reclassify_reviewed_edges(review, "owner-test", root)
            self.assertEqual(before, path.read_bytes())

    def test_repository_kinematic_nesting_preserves_lineage_and_typed_traversal(self) -> None:
        rows = read_jsonl(REPO_ROOT / "lab/second_brain/curated/edges.jsonl")
        current = {row["id"]: row for row in visible_records(rows)}
        expected = {
            "edge_000283": ("c_camera_keyframes", "c_kinematic_truth", "part_of"),
            "edge_000284": ("c_contact_solver", "c_kinematic_truth", "part_of"),
            "edge_000285": ("c_effort_vectors", "c_kinematic_truth", "part_of"),
            "edge_000286": ("c_hard_constraints", "c_kinematic_truth", "applies_to"),
        }
        self.assertEqual(
            {
                edge_id: (current[edge_id]["u"], current[edge_id]["v"], current[edge_id]["type"])
                for edge_id in expected
            },
            expected,
        )
        predecessors = {
            "edge_000243": "edge_000283",
            "edge_000249": "edge_000284",
            "edge_000257": "edge_000285",
            "edge_000264": "edge_000286",
        }
        for predecessor, successor in predecessors.items():
            self.assertEqual(replacement_trace(predecessor, rows)["current_head"], successor)

        historical = {
            row["id"]
            for row in visible_records(
                rows,
                validity_mode="historical",
                as_of="2026-08-04T11:20:01Z",
            )
        }
        self.assertTrue(set(predecessors).issubset(historical))
        self.assertTrue(set(predecessors.values()).isdisjoint(historical))

        graph = build_live_graph(REPO_ROOT, include_derived=False)
        steps = {
            row["neighbor"]: (row["edge_type"], row["transition"])
            for row in traversal_steps(graph, "c_kinematic_truth")
        }
        self.assertEqual(steps["c_camera_keyframes"], ("part_of", "whole_to_part"))
        self.assertEqual(steps["c_contact_solver"], ("part_of", "whole_to_part"))
        self.assertEqual(steps["c_effort_vectors"], ("part_of", "whole_to_part"))
        self.assertEqual(
            steps["c_hard_constraints"],
            ("applies_to", "has_applicable_concept"),
        )


if __name__ == "__main__":
    unittest.main()
