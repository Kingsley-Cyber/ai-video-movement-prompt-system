from __future__ import annotations

import copy
import unittest

from lab.second_brain.src.distill import validate_distillation_batch
from lab.second_brain.src.graph import build_live_graph
from lab.second_brain.src.neo4j_projection import build_projection_plan
from lab.second_brain.src.reasoning_policy import (
    EXECUTOR_REGISTRY,
    compile_from_text,
    load_reasoning_policies,
)
from lab.second_brain.src.validate import REPO_ROOT


class ReasoningPolicyTests(unittest.TestCase):
    def test_policy_store_registry_graph_and_neo4j_projection_are_aligned(self) -> None:
        policies = load_reasoning_policies()
        self.assertEqual(len(policies), 6)
        self.assertEqual(
            {row["executor"] for row in policies}, set(EXECUTOR_REGISTRY)
        )
        graph = build_live_graph()
        for policy in policies:
            self.assertEqual(graph.nodes[policy["id"]]["node_type"], "reasoning_policy")
            for concept_id in policy["concept_ids"]:
                self.assertTrue(graph.has_edge(policy["id"], concept_id))
        plan = build_projection_plan()
        policy_nodes = {
            row["id"] for row in plan["nodes"] if row["node_type"] == "reasoning_policy"
        }
        self.assertEqual(policy_nodes, {row["id"] for row in policies})

    def test_selection_and_execution_replay_without_authority_mutation(self) -> None:
        text = "Create a restrained scene where she realizes he is lying"
        before = {
            path: path.read_bytes()
            for path in [
                REPO_ROOT / "lab" / "concepts.jsonl",
                *sorted((REPO_ROOT / "lab" / "second_brain" / "curated").glob("*.jsonl")),
                *sorted((REPO_ROOT / "lab" / "second_brain" / "immutable").glob("*.jsonl")),
            ]
        }
        first = compile_from_text(text)
        second = compile_from_text(text)
        self.assertEqual(first, second)
        self.assertEqual(first["policy_selection"]["policy_id"], "rp_graph_of_thoughts")
        self.assertEqual(
            first["trust_boundary"]["execution"],
            "ephemeral_deterministic_proposal",
        )
        self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_chain_of_code_performs_only_fixed_safe_calculations(self) -> None:
        value = compile_from_text(
            "Calculate a 5 seconds at 60fps vertical 9:16 video",
            requested_policy_id="rp_chain_of_code",
        )
        calculations = {
            row["operation"]: row for row in value["execution"]["calculations"]
        }
        self.assertEqual(calculations["frame_count"]["result"], 300.0)
        self.assertEqual(calculations["aspect_ratio_decimal"]["result"], 0.5625)
        self.assertFalse(
            value["execution"]["reasoning_trace"][0]["details"].get(
                "arbitrary_code_execution", False
            )
        )

    def test_reasoning_policy_is_a_closed_distillation_output(self) -> None:
        policy = copy.deepcopy(
            next(
                row
                for row in load_reasoning_policies()
                if row["id"] == "rp_algorithm_of_thoughts"
            )
        )
        policy.pop("id")
        policy["policy_id"] = "rp_algorithm_of_thoughts_candidate"
        policy["source_refs"] = ["source://reasoning-paper"]
        batch = {
            "batch_id": "batch_reasoning_policy_fixture",
            "retrieval": {
                "adapter": "fixture",
                "corpus_id": "fixture-corpus",
                "query": "bounded search reasoning",
                "tool": "fixture",
                "parameters": {},
                "retrieved_at": "2000-01-01T00:00:00Z",
            },
            "extractor": {
                "agent": "fixture",
                "model": "fixture",
                "prompt_hash": "sha256:" + "a" * 64,
            },
            "candidates": [
                {
                    "candidate_id": "candidate_reasoning_policy_fixture",
                    "proposal_type": "reasoning_policy",
                    "suggested_id": "rp_algorithm_of_thoughts_candidate",
                    "proposed_record": policy,
                    "source_evidence": [
                        {
                            "source_id": "source://reasoning-paper",
                            "locator": "section-1",
                            "claim": "The source defines a bounded search method.",
                            "content_sha256": "sha256:" + "b" * 64,
                        }
                    ],
                    "created_by": "local_source",
                    "created_at": "2000-01-01T00:00:00Z",
                }
            ],
        }
        report = validate_distillation_batch(batch)
        self.assertEqual(report["proposal_types"], ["reasoning_policy"])
        self.assertEqual(report["authority_effect"], "none")


if __name__ == "__main__":
    unittest.main()
