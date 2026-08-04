from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.compile import compile_result
from lab.second_brain.src.query import QUERY_POLICY, default_request, reason
from lab.second_brain.tests.helpers import concept, make_root, write_rows


class QueryTests(unittest.TestCase):
    def test_query_term_gate_blocks_homonyms_but_preserves_explicit_intent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stereo = {
                **concept("c_stereo", "stereo depth interaxial control"),
                "nl_triggers": [
                    "compress stereo depth for intimacy",
                    "open stereo depth",
                    "interaxial control",
                ],
                "what": "Use interaxial separation and focal length for stereo depth.",
                "use_when": "an intimate stereoscopic shot needs depth control",
                "query_term_gate": {
                    "any": ["stereo", "stereoscopic", "interaxial"],
                },
            }
            root = make_root(Path(directory), [stereo])

            shallow = reason(
                default_request(
                    "intimate macro lens with shallow depth of field",
                    minimum_status="ingested",
                ),
                root,
            )
            self.assertEqual(shallow["selected_concepts"], [])
            self.assertEqual(
                shallow["root_selection"]["query_term_gated_roots"],
                1,
            )
            self.assertEqual(
                shallow["root_selection"]["query_term_gated_preview"][0][
                    "concept_id"
                ],
                "c_stereo",
            )

            explicit = reason(
                default_request(
                    "intimate stereoscopic shot with interaxial depth control",
                    minimum_status="ingested",
                ),
                root,
            )
            self.assertEqual(
                [row["id"] for row in explicit["selected_concepts"]],
                ["c_stereo"],
            )

    def test_more_relevant_root_wins_an_authored_conflict_before_id_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            capture = {
                **concept("c_capture", "phone capture"),
                "nl_triggers": ["cinematic polished"],
                "what": "phone capture realism",
                "use_when": "phone footage",
            }
            scored = {
                **concept("c_scored", "scored FACS Laban performance"),
                "nl_triggers": ["scored FACS Laban performance"],
                "what": "choreographed FACS and Laban performance",
                "use_when": "polished cinematic commercial",
            }
            root = make_root(Path(directory), [capture, scored])
            write_rows(
                root / "lab/second_brain/curated/edges.jsonl",
                [
                    {
                        "id": "edge_000001",
                        "u": "c_capture",
                        "v": "c_scored",
                        "type": "conflicts_with",
                        "context": "all",
                        "authored_by": "test",
                        "note": "Fixture choices are mutually exclusive.",
                        "sources": [{"ref": "fixture://conflict", "locator": None}],
                    }
                ],
            )

            result = reason(
                default_request(
                    "polished cinematic commercial with a scored FACS Laban performance",
                    minimum_status="ingested",
                ),
                root,
            )

            self.assertEqual(
                [row["id"] for row in result["selected_concepts"]],
                ["c_scored"],
            )
            capture_rejection = next(
                row for row in result["rejected_concepts"] if row["id"] == "c_capture"
            )
            self.assertEqual(capture_rejection["reason_code"], "conflict")
            self.assertIn("c_scored", capture_rejection["reasons"][0])

    def test_exact_semantic_duplicate_roots_do_not_consume_root_budget(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [
                    concept("c_alpha", "alpha"),
                    concept("c_alpha_clone_1", "alpha"),
                    concept("c_alpha_clone_2", "alpha"),
                ],
            )
            result = reason(
                default_request("alpha", minimum_status="ingested"),
                root,
            )
            self.assertEqual(
                [row["id"] for row in result["selected_concepts"]],
                ["c_alpha"],
            )
            self.assertEqual(
                result["root_selection"]["suppressed_exact_duplicates"],
                2,
            )
            self.assertEqual(
                {
                    row["representative_id"]
                    for row in result["root_selection"]["suppressed_preview"]
                },
                {"c_alpha"},
            )

    def test_exact_semantic_duplicate_hops_do_not_consume_selection_budget(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [
                    concept("c_alpha", "alpha"),
                    {
                        **concept("c_beta", "beta"),
                        "what": "beta supplies alpha structural term support",
                    },
                    {
                        **concept("c_beta_clone", "beta"),
                        "what": "beta supplies alpha structural term support",
                    },
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
                        "u": "c_alpha",
                        "v": "c_beta_clone",
                        "type": "refines",
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
            self.assertEqual(
                {row["id"] for row in result["selected_concepts"]},
                {"c_alpha", "c_beta"},
            )
            self.assertEqual(
                result["semantic_deduplication"]["suppressed_exact_duplicates"],
                1,
            )
            self.assertEqual(
                result["semantic_deduplication"]["suppressed_preview"][0][
                    "representative_id"
                ],
                "c_beta",
            )

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
                    {
                        **concept("c_beta", "beta"),
                        "what": "beta supplies alpha structural term support",
                    },
                    {
                        **concept("c_gamma", "gamma"),
                        "what": "gamma supplies alpha structural term support",
                    },
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
                    {
                        **concept("c_beta", "beta"),
                        "what": "beta supplies alpha structural term support",
                    },
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
                    {
                        **concept("c_beta", "beta"),
                        "what": "beta supplies alpha structural term support",
                    },
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

    def test_laban_canary_blocks_unrelated_color_and_requests_retrieval(self) -> None:
        request = default_request(
            "Laban effort decimal spatial movement",
            minimum_status="ingested",
            include_unproven=True,
            maximum_depth=5,
            target_format="json",
        )
        reasoning = reason(request)
        selected = {
            item["id"] for item in reasoning["selected_concepts"]
        }
        self.assertNotIn("c_dual_view_color_integration", selected)
        self.assertIn("c_laban_efforts", selected)
        self.assertIn("c_laban_shape_directional_curvature", selected)
        self.assertEqual(
            reasoning["knowledge_gap"]["uncovered_terms"],
            ["decimal", "spatial"],
        )
        self.assertEqual(reasoning["knowledge_gap"]["status"], "partial")
        self.assertTrue(reasoning["knowledge_gap"]["should_retrieve"])
        self.assertEqual(
            reasoning["knowledge_gap"]["reason"],
            "material_query_terms_uncovered",
        )
        compiled = compile_result(reasoning, "json")
        self.assertNotIn(
            "color.vfx.dual_view_integration",
            compiled["package"]["controls"],
        )
        unsafe_reasoning = json.loads(json.dumps(reasoning))
        unsafe_reasoning["selected_concepts"].append(
            {
                "id": "c_dual_view_color_integration",
                "name": "Dual-view color integration",
                "layer": "color pipeline",
                "status": "ingested",
                "depth": 2,
                "admission_reason": "connectivity_only",
                "required_by": [],
                "path": ["edge_000226"],
                "covered_terms": [],
                "policy_version": QUERY_POLICY["version"],
            }
        )
        with self.assertRaisesRegex(
            ValueError,
            "relevance-gated reasoning result",
        ):
            compile_result(unsafe_reasoning, "json")

    def test_prerequisites_close_transitively_and_precede_dependents(self) -> None:
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
                        "id": "edge_requires_alpha_beta",
                        "u": "c_alpha",
                        "v": "c_beta",
                        "type": "requires",
                        "context": "all",
                        "authored_by": "test",
                        "note": None,
                        "sources": [],
                    },
                    {
                        "id": "edge_requires_beta_gamma",
                        "u": "c_beta",
                        "v": "c_gamma",
                        "type": "requires",
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
            selected = result["selected_concepts"]
            self.assertEqual(
                [item["id"] for item in selected],
                ["c_gamma", "c_beta", "c_alpha"],
            )
            by_id = {item["id"]: item for item in selected}
            self.assertEqual(
                by_id["c_gamma"]["admission_reason"],
                "required_prerequisite",
            )
            self.assertEqual(by_id["c_gamma"]["required_by"], ["c_beta"])
            self.assertEqual(by_id["c_beta"]["required_by"], ["c_alpha"])
            self.assertEqual(by_id["c_alpha"]["admission_reason"], "direct_match")

    def test_missing_prerequisite_rejects_dependent_with_stable_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [concept("c_alpha", "alpha")],
            )
            write_rows(
                root / "lab/second_brain/curated/edges.jsonl",
                [
                    {
                        "id": "edge_requires_missing",
                        "u": "c_alpha",
                        "v": "c_missing",
                        "type": "requires",
                        "context": "all",
                        "authored_by": "test",
                        "note": None,
                        "sources": [],
                    }
                ],
            )
            result = reason(
                default_request("alpha", minimum_status="ingested"),
                root,
            )
            self.assertEqual(result["selected_concepts"], [])
            rejected = {
                item["id"]: item for item in result["rejected_concepts"]
            }
            self.assertEqual(
                rejected["c_alpha"]["reason_code"],
                "missing_prerequisite",
            )
            self.assertEqual(
                rejected["c_alpha"]["missing_prerequisites"],
                ["c_missing"],
            )

    def test_dependency_cycle_is_rejected_and_terminates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [
                    concept("c_alpha", "alpha"),
                    concept("c_beta", "beta"),
                ],
            )
            write_rows(
                root / "lab/second_brain/curated/edges.jsonl",
                [
                    {
                        "id": "edge_requires_alpha_beta",
                        "u": "c_alpha",
                        "v": "c_beta",
                        "type": "requires",
                        "context": "all",
                        "authored_by": "test",
                        "note": None,
                        "sources": [],
                    },
                    {
                        "id": "edge_requires_beta_alpha",
                        "u": "c_beta",
                        "v": "c_alpha",
                        "type": "requires",
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
            self.assertEqual(result["selected_concepts"], [])
            rejected = {
                item["id"]: item for item in result["rejected_concepts"]
            }
            self.assertEqual(
                rejected["c_alpha"]["reason_code"],
                "dependency_cycle",
            )
            self.assertEqual(
                rejected["c_beta"]["reason_code"],
                "dependency_cycle",
            )
            self.assertEqual(
                rejected["c_alpha"]["dependency_cycle"],
                ["c_alpha", "c_beta", "c_alpha"],
            )

    def test_query_replay_preserves_order_paths_rejections_and_gap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [
                    concept("c_alpha", "alpha"),
                    concept("c_beta", "beta"),
                    concept("c_noise", "noise"),
                ],
            )
            write_rows(
                root / "lab/second_brain/curated/edges.jsonl",
                [
                    {
                        "id": "edge_requires_alpha_beta",
                        "u": "c_alpha",
                        "v": "c_beta",
                        "type": "requires",
                        "context": "all",
                        "authored_by": "test",
                        "note": None,
                        "sources": [],
                    },
                    {
                        "id": "edge_alpha_noise",
                        "u": "c_alpha",
                        "v": "c_noise",
                        "type": "pairs_with",
                        "context": "all",
                        "authored_by": "test",
                        "note": None,
                        "sources": [],
                    },
                ],
            )
            request = default_request(
                "alpha orbital",
                minimum_status="ingested",
            )
            first = reason(request, root)
            second = reason(request, root)
            self.assertEqual(
                first["selected_concepts"],
                second["selected_concepts"],
            )
            self.assertEqual(first["path_taken"], second["path_taken"])
            self.assertEqual(
                first["rejected_concepts"],
                second["rejected_concepts"],
            )
            self.assertEqual(first["knowledge_gap"], second["knowledge_gap"])
            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
