from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.record import (
    append_measurement_observation,
    _append_verified_run,
    seal_flight,
)
from lab.second_brain.src.reflect import _promotion_edges, rebuild
from lab.second_brain.src.validate import sha256_value
from lab.second_brain.tests.helpers import (
    concept,
    controlled_lineage,
    finalize_evidence_run,
    make_root,
)

HASH = "sha256:" + "1" * 64


class ReflectTests(unittest.TestCase):
    def test_repeated_isolated_flights_keep_distinct_causal_traces(self) -> None:
        def evidence_run(
            flight_id: str, tag: str, value: int, verdict: str
        ) -> dict:
            lineage = controlled_lineage(tag)
            return {
                "id": f"r_{tag}",
                "flight_id": flight_id,
                "flight_hash": "sha256:" + hashlib.sha256(flight_id.encode()).hexdigest(),
                "intent_id": None,
                "intent_class": "fixture",
                "paradigm": "hybrid",
                "concept_ids": ["c_delta", "c_shared"],
                "concept_content_hashes": {"c_delta": HASH, "c_shared": HASH},
                "provider": "fixture",
                "model_version": "fixture-1",
                "seed": 7,
                "compiler_version": "compiler-1",
                "controls": {
                    "control_0000000000000001": value,
                    "control_0000000000000002": 2,
                },
                "tested_delta": {
                    "concept_id": "c_delta",
                    "control_id": "control_0000000000000001",
                    "value": value,
                },
                "verdict": verdict,
                "evidence_design": {
                    "classification": "isolated_comparison",
                    "causal_eligibility": "candidate",
                    "outcome_concept_ids": ["c_shared"],
                    "policy_version": "cpcs-controlled-evidence/1.0",
                },
                "evidence_lineage": lineage,
                "human_review": {
                    "review_id": f"review_{tag}",
                    "review_hash": HASH,
                    "verdict": verdict,
                },
            }

        edges = _promotion_edges(
            [
                evidence_run("flight_one", "one_a", 1, "keep"),
                evidence_run("flight_one", "one_b", 0, "reject"),
                evidence_run("flight_two", "two_a", 1, "keep"),
                evidence_run("flight_two", "two_b", 0, "reject"),
            ]
        )
        self.assertEqual(len(edges), 2)
        self.assertEqual(len({edge["id"] for edge in edges}), 2)
        self.assertEqual(
            {edge["isolated_comparison"]["flight_id"] for edge in edges},
            {"flight_one", "flight_two"},
        )

    def test_isolated_comparison_and_rebuild_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            delta = concept("c_delta", "delta")
            shared = concept("c_shared", "shared")
            root = make_root(Path(directory), [delta, shared])
            flight = seal_flight(
                {
                    "id": "flight_ab",
                    "intent_id": None,
                    "intent_class": "product_reveal",
                    "arms": [
                        {
                            "id": "a",
                            "paradigm": "hybrid",
                            "tested_delta": {
                                "concept_id": "c_delta",
                                "control_id": "control_0000000000000001",
                                "value": 1,
                            },
                        },
                        {
                            "id": "b",
                            "paradigm": "hybrid",
                            "tested_delta": {
                                "concept_id": "c_delta",
                                "control_id": "control_0000000000000001",
                                "value": 0,
                            },
                        },
                    ],
                    "design": {
                        "classification": "isolated_comparison",
                        "causal_claim_policy": "isolated_only",
                        "metric_ids": ["score"],
                        "outcome_concept_ids": ["c_shared"],
                    },
                    "concept_ids": ["c_delta", "c_shared"],
                    "provider": "fixture",
                    "model_version": "fixture-1",
                    "seed": 7,
                    "compiler_settings": {"version": "compiler-1"},
                    "sealed_at": "2026-07-30T00:00:00Z",
                    "legacy": None,
                },
                root,
            )
            base = {
                "flight_id": flight["id"],
                "flight_hash": flight["flight_hash"],
                "intent_id": None,
                "intent_class": "product_reveal",
                "paradigm": "hybrid",
                "concept_content_hashes": {
                    "c_delta": sha256_value(delta),
                    "c_shared": sha256_value(shared),
                },
                "provider": "fixture",
                "model_version": "fixture-1",
                "seed": 7,
                "compiled_prompt_hash": HASH,
                "compiler_version": "compiler-1",
                "repository_commit": "fixture",
                "output_artifact_hash": HASH,
                "metrics": {"score": 5},
                "recorded_at": "2026-07-30T00:00:01Z",
                "legacy": None,
            }
            lineage_a = controlled_lineage("reflect-a")
            run_a = _append_verified_run(
                finalize_evidence_run({
                    **base,
                    "arm": "a",
                    "concept_ids": ["c_delta", "c_shared"],
                    "output_artifact_hash": lineage_a["artifact_sha256"],
                    "controls": {
                        "control_0000000000000001": 1,
                        "control_0000000000000002": 2,
                    },
                    "tested_delta": {
                        "concept_id": "c_delta",
                        "control_id": "control_0000000000000001",
                        "value": 1,
                    },
                    "verdict": "keep",
                    "evidence_design": {
                        "classification": "isolated_comparison",
                        "causal_eligibility": "candidate",
                        "outcome_concept_ids": ["c_shared"],
                        "policy_version": "cpcs-controlled-evidence/1.0",
                    },
                    "evidence_lineage": lineage_a,
                    "human_review": {
                        "review_id": "review_reflect_a",
                        "reviewer_id": "reviewer_fixture",
                        "verdict": "keep",
                        "rationale": "Arm A passed the isolated fixture.",
                        "reviewed_at": "2026-07-30T00:00:01Z",
                    },
                }),
                root,
            )
            lineage_b = controlled_lineage("reflect-b")
            run_b = _append_verified_run(
                finalize_evidence_run({
                    **base,
                    "arm": "b",
                    "concept_ids": ["c_delta", "c_shared"],
                    "output_artifact_hash": lineage_b["artifact_sha256"],
                    "controls": {
                        "control_0000000000000001": 0,
                        "control_0000000000000002": 2,
                    },
                    "tested_delta": {
                        "concept_id": "c_delta",
                        "control_id": "control_0000000000000001",
                        "value": 0,
                    },
                    "verdict": "reject",
                    "evidence_design": {
                        "classification": "isolated_comparison",
                        "causal_eligibility": "candidate",
                        "outcome_concept_ids": ["c_shared"],
                        "policy_version": "cpcs-controlled-evidence/1.0",
                    },
                    "evidence_lineage": lineage_b,
                    "human_review": {
                        "review_id": "review_reflect_b",
                        "reviewer_id": "reviewer_fixture",
                        "verdict": "reject",
                        "rationale": "Arm B failed the isolated fixture.",
                        "reviewed_at": "2026-07-30T00:00:01Z",
                    },
                }),
                root,
            )
            append_measurement_observation(
                {
                    "id": "measurement_obs_ab",
                    "source_asset_ref": "fixture://measurement",
                    "source_sha256": "a" * 64,
                    "tool": "fixture_pose",
                    "model_version": "fixture-1",
                    "interval": {"start_s": 0.0, "end_s": 1.0},
                    "claim": {"path_curvature": 0.5},
                    "concept_ids": ["c_shared"],
                    "candidate_concepts": [],
                    "evidence_class": "measured",
                    "confidence": 1.0,
                    "created_at": "2026-07-30T00:00:02Z",
                },
                root,
            )
            first = rebuild(root)
            stale = root / "lab/second_brain/derived/stale.json"
            stale.write_text("{}")
            second = rebuild(root)
            self.assertEqual(first, second)
            self.assertFalse(stale.exists())
            weights = __import__("json").loads(
                (root / "lab/second_brain/derived/weights.json").read_text()
            )
            promotes = [edge for edge in weights["edges"] if edge["type"] == "promotes"]
            self.assertEqual(len(promotes), 1)
            self.assertEqual(
                promotes[0]["evidence"], sorted([run_a["id"], run_b["id"]])
            )
            self.assertEqual(promotes[0]["model_version"], "fixture-1")
            self.assertEqual(
                promotes[0]["evidence_scope"], "causal_isolated_comparison"
            )
            self.assertEqual(
                promotes[0]["isolated_comparison"]["winner"]["artifact_sha256"],
                lineage_a["artifact_sha256"],
            )
            associations = [
                edge
                for edge in weights["edges"]
                if edge["type"] == "associated_with_success"
            ]
            self.assertEqual(len(associations), 1)
            index = __import__("json").loads(
                (
                    root
                    / "lab/second_brain/derived/indexes/concept_to_evidence.json"
                ).read_text()
            )
            self.assertIn(
                "measurement_obs_ab",
                index["concept_to_evidence"]["c_shared"],
            )

    def test_bundled_observation_is_traceable_but_never_causal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            alpha = concept("c_alpha", "alpha")
            beta = concept("c_beta", "beta")
            root = make_root(Path(directory), [alpha, beta])
            flight = seal_flight(
                {
                    "id": "flight_bundled",
                    "intent_id": None,
                    "intent_class": "fixture",
                    "arms": [
                        {
                            "id": "bundle",
                            "paradigm": "hybrid",
                            "tested_delta": None,
                        }
                    ],
                    "design": {
                        "classification": "bundled_observation",
                        "causal_claim_policy": "isolated_only",
                        "metric_ids": ["score"],
                        "outcome_concept_ids": [],
                    },
                    "concept_ids": ["c_alpha", "c_beta"],
                    "provider": "fixture",
                    "model_version": "fixture-1",
                    "seed": 7,
                    "compiler_settings": {"version": "compiler-1"},
                    "sealed_at": "2026-07-30T00:00:00Z",
                    "legacy": None,
                },
                root,
            )
            lineage = controlled_lineage("bundled")
            run = _append_verified_run(
                finalize_evidence_run(
                    {
                        "flight_id": flight["id"],
                        "flight_hash": flight["flight_hash"],
                        "intent_id": None,
                        "intent_class": "fixture",
                        "arm": "bundle",
                        "paradigm": "hybrid",
                        "concept_ids": ["c_alpha", "c_beta"],
                        "concept_content_hashes": {
                            "c_alpha": sha256_value(alpha),
                            "c_beta": sha256_value(beta),
                        },
                        "provider": "fixture",
                        "model_version": "fixture-1",
                        "seed": 7,
                        "compiled_prompt_hash": HASH,
                        "compiler_version": "compiler-1",
                        "repository_commit": "fixture",
                        "output_artifact_hash": lineage["artifact_sha256"],
                        "metrics": {"score": 5},
                        "controls": {"control_0000000000000001": True},
                        "tested_delta": None,
                        "verdict": "keep",
                        "evidence_design": {
                            "classification": "bundled_observation",
                            "causal_eligibility": "ineligible_bundled",
                            "outcome_concept_ids": [],
                            "policy_version": "cpcs-controlled-evidence/1.0",
                        },
                        "evidence_lineage": lineage,
                        "human_review": {
                            "review_id": "review_bundled",
                            "reviewer_id": "reviewer_fixture",
                            "verdict": "keep",
                            "rationale": "Bundled fixture observation.",
                            "reviewed_at": "2026-07-30T00:00:01Z",
                        },
                        "recorded_at": "2026-07-30T00:00:01Z",
                        "legacy": None,
                    }
                ),
                root,
            )
            rebuild(root)
            weights = __import__("json").loads(
                (root / "lab/second_brain/derived/weights.json").read_text()
            )
            self.assertFalse(any(edge["type"] == "promotes" for edge in weights["edges"]))
            association = next(
                edge
                for edge in weights["edges"]
                if edge["type"] == "associated_with_success"
            )
            self.assertEqual(association["evidence"], [run["id"]])
            self.assertEqual(association["evidence_scope"], "noncausal_association")
            self.assertEqual(association["weight"], 0.25)
            catalog = __import__("json").loads(
                (
                    root / "lab/second_brain/derived/indexes/catalog.json"
                ).read_text()
            )
            calibration = catalog["provider_performance"]["fixture::fixture-1"]
            self.assertEqual(calibration["calibration_status"], "noncausal_only")
            self.assertEqual(calibration["bundled_run_ids"], [run["id"]])


if __name__ == "__main__":
    unittest.main()
