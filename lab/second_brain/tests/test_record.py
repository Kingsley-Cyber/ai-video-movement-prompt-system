from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from lab.compiler.build import write_build_directory
from lab.compiler.tests.test_build import build_for, ready_score
from lab.second_brain.src import record
from lab.second_brain.src.record import (
    _append_verified_run,
    append_run,
    prepare_experiment_flight,
    seal_flight,
)
from lab.second_brain.src.validate import (
    REPO_ROOT,
    ValidationFailure,
    read_jsonl,
    sha256_value,
)
from lab.second_brain.tests.helpers import (
    concept,
    controlled_lineage,
    finalize_evidence_run,
    make_root,
)

HASH = "sha256:" + "0" * 64


class RecordTests(unittest.TestCase):
    def test_prepare_and_idempotently_seal_exact_build_bound_experiment(self) -> None:
        text = "Create a multi-actor action scene with readable screen direction"
        score_a = ready_score(text)
        score_b = ready_score(
            text,
            overlays=[
                {
                    "overlay_id": "overlay_record_prepare_delta",
                    "scope": "explicit_user_correction",
                    "priority": 0,
                    "values": {"camera": {"impact_shake_policy": "none"}},
                    "locks": [],
                }
            ],
        )
        control_a = next(
            row
            for row in score_a["provider_neutral_controls"]
            if row["path"] == "camera.impact_shake_policy"
        )
        control_b = next(
            row
            for row in score_b["provider_neutral_controls"]
            if row["path"] == "camera.impact_shake_policy"
        )
        self.assertEqual(control_a["control_id"], control_b["control_id"])
        self.assertNotEqual(control_a["value"], control_b["value"])
        _, artifacts_a = build_for(score_a)
        _, artifacts_b = build_for(score_b)

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            root = make_root(
                workspace,
                read_jsonl(REPO_ROOT / "lab" / "concepts.jsonl"),
            )
            build_a = workspace / "build-a"
            build_b = workspace / "build-b"
            write_build_directory(artifacts_a, build_a)
            write_build_directory(artifacts_b, build_b)
            concept_id = "c_dramatic_action_motivated_camera"
            arm_builds = [
                {
                    "id": "a",
                    "build_dir": str(build_a),
                    "tested_delta": {
                        "concept_id": concept_id,
                        "control_id": control_a["control_id"],
                        "value": control_a["value"],
                    },
                },
                {
                    "id": "b",
                    "build_dir": str(build_b),
                    "tested_delta": {
                        "concept_id": concept_id,
                        "control_id": control_b["control_id"],
                        "value": control_b["value"],
                    },
                },
            ]
            kwargs = {
                "flight_id": "flight_prepared_builds",
                "arm_builds": arm_builds,
                "classification": "isolated_comparison",
                "metric_ids": ["creative_quality"],
                "outcome_concept_ids": ["c_camera_keyframes"],
                "provider": "fixture",
                "model_version": "fixture-1",
                "sealed_at": "2027-01-15T07:00:00Z",
                "root": root,
            }
            prepared = prepare_experiment_flight(**kwargs)
            replay = prepare_experiment_flight(**copy.deepcopy(kwargs))
            self.assertEqual(prepared, replay)
            reordered = prepare_experiment_flight(
                **{**kwargs, "arm_builds": list(reversed(arm_builds))}
            )
            self.assertEqual(prepared, reordered)
            self.assertEqual(
                prepared["differing_control_ids"], [control_a["control_id"]]
            )
            self.assertEqual(
                [row["build_id"] for row in prepared["builds"]],
                [
                    json.loads(artifacts_a["build_manifest.json"])["build_id"],
                    json.loads(artifacts_b["build_manifest.json"])["build_id"],
                ],
            )

            sealed = seal_flight(prepared["flight_draft"], root)
            sealed_replay = seal_flight(
                copy.deepcopy(prepared["flight_draft"]), root
            )
            self.assertEqual(sealed, sealed_replay)
            self.assertEqual(
                len(
                    read_jsonl(
                        root / "lab/second_brain/immutable/flights.jsonl"
                    )
                ),
                1,
            )
            collision = copy.deepcopy(prepared["flight_draft"])
            collision["provider"] = "different-provider"
            with self.assertRaisesRegex(
                ValidationFailure, "immutable flight ID collision"
            ):
                seal_flight(collision, root)

    def test_append_only_hash_chain_and_duplicate_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            alpha = concept("c_alpha", "alpha")
            root = make_root(Path(directory), [alpha])
            flight = seal_flight(
                {
                    "id": "flight_test",
                    "intent_id": None,
                    "intent_class": "test",
                    "arms": [
                        {"id": "a", "paradigm": "test", "tested_delta": None}
                    ],
                    "design": {
                        "classification": "bundled_observation",
                        "causal_claim_policy": "isolated_only",
                        "metric_ids": ["score"],
                        "outcome_concept_ids": [],
                    },
                    "concept_ids": ["c_alpha"],
                    "provider": "fixture",
                    "model_version": "fixture-1",
                    "seed": 7,
                    "compiler_settings": {"version": "test-1"},
                    "sealed_at": "2026-07-30T00:00:00Z",
                    "legacy": None,
                },
                root,
            )
            lineage = controlled_lineage("record-test")
            run = finalize_evidence_run({
                "flight_id": flight["id"],
                "flight_hash": flight["flight_hash"],
                "intent_id": None,
                "intent_class": "test",
                "arm": "a",
                "paradigm": "test",
                "concept_ids": ["c_alpha"],
                "concept_content_hashes": {"c_alpha": sha256_value(alpha)},
                "provider": "fixture",
                "model_version": "fixture-1",
                "seed": 7,
                "compiled_prompt_hash": HASH,
                "compiler_version": "test-1",
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
                    "review_id": "review_record_test",
                    "reviewer_id": "reviewer_fixture",
                    "verdict": "keep",
                    "rationale": "Fixture bundled-observation verdict.",
                    "reviewed_at": "2026-07-30T00:00:01Z",
                },
                "recorded_at": "2026-07-30T00:00:01Z",
                "legacy": None,
            })
            with self.assertRaisesRegex(
                ValidationFailure, "must enter through append_experiment_run"
            ):
                append_run(run, root)
            stored = _append_verified_run(run, root)
            self.assertTrue(stored["record_hash"].startswith("sha256:"))
            with self.assertRaises(ValidationFailure):
                _append_verified_run(run, root)
            mismatch = {**run, "provider": "other"}
            with self.assertRaises(ValidationFailure):
                _append_verified_run(mismatch, root)
            self.assertEqual(len(read_jsonl(root / "lab/second_brain/immutable/runs.jsonl")), 1)
            self.assertFalse(hasattr(record, "update_record"))
            self.assertFalse(hasattr(record, "delete_record"))


if __name__ == "__main__":
    unittest.main()
