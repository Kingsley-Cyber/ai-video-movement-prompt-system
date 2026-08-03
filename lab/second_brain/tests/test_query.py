from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.query import default_request, reason
from lab.second_brain.tests.helpers import concept, make_root, write_rows


class QueryTests(unittest.TestCase):
    def test_unknown_goal_emits_a_retrieval_gap_without_unrelated_roots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [concept("c_alpha", "alpha")],
            )
            result = reason(
                default_request(
                    "quasar xylophone orbital tessellation",
                    minimum_status="ingested",
                ),
                root,
            )
            self.assertEqual(result["selected_concepts"], [])
            self.assertEqual(result["knowledge_gap"]["status"], "missing")
            self.assertTrue(result["knowledge_gap"]["should_retrieve"])
            self.assertEqual(
                result["knowledge_gap"]["uncovered_terms"],
                ["orbital", "quasar", "tessellation", "xylophone"],
            )

    def test_ingested_minimum_excludes_unexplored_unless_explicitly_included(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [
                    concept("c_ingested", "gesture", status="ingested"),
                    concept("c_unexplored", "gesture option", status="unexplored"),
                ],
            )
            result = reason(
                default_request("gesture", minimum_status="ingested"),
                root,
            )
            selected = {item["id"] for item in result["selected_concepts"]}
            self.assertIn("c_ingested", selected)
            self.assertNotIn("c_unexplored", selected)
            self.assertTrue(
                any(
                    item["id"] == "c_unexplored"
                    and "below minimum ingested" in item["reasons"][0]
                    for item in result["rejected_concepts"]
                )
            )

            inclusive = reason(
                default_request(
                    "gesture",
                    minimum_status="ingested",
                    include_unproven=True,
                ),
                root,
            )
            self.assertIn(
                "c_unexplored",
                {item["id"] for item in inclusive["selected_concepts"]},
            )

    def test_typed_hops_record_direction_and_stop_legacy_chaining(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [
                    concept("c_alpha", "alpha"),
                    concept("c_beta", "beta"),
                    concept("c_gamma", "gamma"),
                    concept("c_delta", "delta"),
                ],
            )
            write_rows(
                root / "lab/second_brain/curated/edges.jsonl",
                [
                    {
                        "id": "edge_000001",
                        "u": "c_alpha",
                        "v": "c_beta",
                        "type": "refines",
                        "context": "all",
                        "authored_by": "test",
                        "note": None,
                        "sources": [],
                    },
                    {
                        "id": "edge_000002",
                        "u": "c_beta",
                        "v": "c_gamma",
                        "type": "pairs_with",
                        "context": "all",
                        "authored_by": "test",
                        "note": None,
                        "sources": [],
                    },
                    {
                        "id": "edge_000003",
                        "u": "c_gamma",
                        "v": "c_delta",
                        "type": "pairs_with",
                        "context": "all",
                        "authored_by": "test",
                        "note": None,
                        "sources": [],
                    },
                ],
            )
            result = reason(
                default_request("alpha", minimum_status="ingested"),
                root,
            )
            selected = {item["id"] for item in result["selected_concepts"]}
            self.assertEqual(selected, {"c_alpha", "c_beta", "c_gamma"})
            typed_hop = next(
                row
                for row in result["path_taken"]
                if row["edge_id"] == "edge_000001"
            )
            self.assertEqual(typed_hop["direction"], "forward")
            self.assertEqual(typed_hop["transition"], "generalizes_to")
            self.assertEqual(typed_hop["family"], "structural")
            self.assertNotIn("c_delta", selected)

    def test_multi_hop_explanation_and_hard_conflict_override_weight(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [
                    concept("c_alpha", "alpha"),
                    concept("c_beta", "beta"),
                    concept("c_gamma", "gamma"),
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
                    },
                    {
                        "id": "edge_000002",
                        "u": "c_beta",
                        "v": "c_gamma",
                        "type": "conflicts_with",
                        "context": "all",
                        "authored_by": "test",
                        "note": None,
                        "sources": [],
                    },
                ],
            )
            learned = {
                "algorithm_version": "test",
                "derivation_policy": "test",
                "policy_hash": "sha256:" + "0" * 64,
                "edges": [
                    {
                        "id": "learned_positive_gamma",
                        "u": "c_beta",
                        "v": "c_gamma",
                        "type": "co_success",
                        "weight": 1.0,
                        "evidence": ["r_test"],
                        "model_version": "fixture-1",
                        "context": "all",
                        "n_obs": 1,
                        "derivation_policy": "test",
                    }
                ],
            }
            path = root / "lab/second_brain/derived/weights.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(learned))
            result = reason(
                default_request(
                    "alpha",
                    minimum_status="ingested",
                    model_version="fixture-1",
                ),
                root,
            )
            selected = {item["id"] for item in result["selected_concepts"]}
            self.assertIn("c_alpha", selected)
            self.assertIn("c_beta", selected)
            self.assertNotIn("c_gamma", selected)
            self.assertTrue(
                any(item["id"] == "c_gamma" and "authored conflict" in item["reasons"][0]
                    for item in result["rejected_concepts"])
            )
            self.assertTrue(any(path["depth"] >= 1 for path in result["path_taken"]))

    def test_rule_and_domain_invalidity_override_positive_weight(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [
                    concept("c_alpha", "alpha"),
                    concept("c_beta", "beta"),
                    concept("c_gamma", "gamma"),
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
                    },
                    {
                        "id": "edge_000002",
                        "u": "c_gamma",
                        "v": "c_alpha",
                        "type": "invalid_for",
                        "context": "marketing",
                        "authored_by": "test",
                        "note": None,
                        "sources": [],
                    },
                ],
            )
            write_rows(
                root / "lab/second_brain/curated/rules.jsonl",
                [
                    {
                        "id": "rule_no_alpha_beta",
                        "name": "alpha beta exclusion",
                        "trigger": {"concept_id": "c_alpha"},
                        "evaluator": "forbid_combination",
                        "arguments": {"concept_ids": ["c_alpha", "c_beta"]},
                        "severity": "error",
                        "explanation": "The pair is forbidden.",
                        "sources": [],
                    }
                ],
            )
            learned = {
                "algorithm_version": "test",
                "derivation_policy": "test",
                "policy_hash": "sha256:" + "0" * 64,
                "edges": [
                    {
                        "id": "learned_positive_beta",
                        "u": "c_alpha",
                        "v": "c_beta",
                        "type": "associated_with_success",
                        "weight": 1.0,
                        "evidence": ["r_test"],
                        "model_version": "fixture-1",
                        "context": "marketing",
                        "n_obs": 1,
                        "derivation_policy": "test",
                    }
                ],
            }
            path = root / "lab/second_brain/derived/weights.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(learned))
            result = reason(
                default_request(
                    "alpha",
                    domain="marketing",
                    minimum_status="ingested",
                    model_version="fixture-1",
                ),
                root,
            )
            selected = {item["id"] for item in result["selected_concepts"]}
            self.assertIn("c_alpha", selected)
            self.assertNotIn("c_beta", selected)
            self.assertNotIn("c_gamma", selected)
            rejected = {
                item["id"]: item["reasons"] for item in result["rejected_concepts"]
            }
            self.assertTrue(any("rule" in reason for reason in rejected["c_beta"]))
            self.assertTrue(
                any("invalid for domain" in reason for reason in rejected["c_gamma"])
            )

    def test_repository_reasoning_and_retrieval_canaries_follow_typed_paths(self) -> None:
        reasoning = reason(
            default_request(
                "graph operations branching scoring aggregation",
                minimum_status="ingested",
                target_format="json",
            )
        )
        reasoning_ids = {
            item["id"] for item in reasoning["selected_concepts"]
        }
        self.assertIn("c_graph_of_operations_reasoning", reasoning_ids)
        self.assertIn("c_reasoning_strategy_contract", reasoning_ids)
        reasoning_edges = {
            item["edge_id"]: item
            for item in (
                reasoning["path_taken"]
                + reasoning["alternative_valid_paths"]
            )
        }
        self.assertEqual(reasoning_edges["edge_000235"]["family"], "structural")

        retrieval = reason(
            default_request(
                "hybrid global local retrieval supporting path evaluation",
                minimum_status="ingested",
                target_format="json",
            )
        )
        retrieval_ids = {
            item["id"] for item in retrieval["selected_concepts"]
        }
        self.assertTrue(
            {
                "c_hybrid_graph_retrieval",
                "c_global_local_traversal",
                "c_supporting_path_evaluation",
            }
            <= retrieval_ids
        )
        self.assertEqual(retrieval["knowledge_gap"]["status"], "none")


if __name__ == "__main__":
    unittest.main()
