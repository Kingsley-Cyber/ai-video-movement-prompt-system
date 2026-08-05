from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from lab.compiler.build import write_build_directory
from lab.compiler.provenance import sha256_bytes
from lab.compiler.tests.test_build import build_for, ready_score
from lab.second_brain.src import record
from lab.second_brain.src.record import (
    _append_verified_run,
    append_run,
    capture_human_testimonial,
    inspect_human_testimonial,
    prepare_experiment_flight,
    review_human_testimonial,
    seal_flight,
    testimonial_normalization_response_hash,
)
from lab.second_brain.src.validate import (
    REPO_ROOT,
    ValidationFailure,
    canonical_json_bytes,
    read_jsonl,
    sha256_value,
    validate_immutable,
)
from lab.second_brain.tests.helpers import (
    concept,
    controlled_lineage,
    finalize_evidence_run,
    make_root,
)

HASH = "sha256:" + "0" * 64


class RecordTests(unittest.TestCase):
    def test_exact_testimonial_capture_review_and_correction_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory))
            render_dir = root / "work" / "render" / "jobs" / ("render_job_" + "0" * 24)
            artifact_dir = render_dir / "artifacts"
            artifact_dir.mkdir(parents=True)
            artifact_bytes = b"fixture-video-bytes"
            artifact_path = artifact_dir / "artifact_000.mp4"
            artifact_path.write_bytes(artifact_bytes)
            render_result = {
                "schema": "cpcs.render_result/1.0",
                "job_id": "render_job_" + "0" * 24,
                "build_id": "build_" + "1" * 32,
                "build_hash": "sha256:" + "2" * 64,
                "provider": "fixture",
                "model": "fixture-1",
                "operation_id": "fixture-operation",
                "status": "succeeded",
                "artifacts": [
                    {
                        "artifact_id": "artifact_000",
                        "relative_path": "artifacts/artifact_000.mp4",
                        "source_uri": None,
                        "mime_type": "video/mp4",
                        "size_bytes": len(artifact_bytes),
                        "sha256": sha256_bytes(artifact_bytes),
                    }
                ],
                "expected_media": {
                    "duration_seconds": 10,
                    "aspect_ratio": "16:9",
                    "resolution": "1280x720",
                    "sample_count": 1,
                },
                "provider_response_hash": "sha256:" + "3" * 64,
                "completed_at": "2027-01-15T08:00:00Z",
            }
            result_path = render_dir / "render_result.json"
            result_path.write_bytes(canonical_json_bytes(render_result))
            speaker = {
                "speaker_id": "director_fixture",
                "role": "owner",
                "rights_basis": "owner_authored",
            }
            capture = {
                "schema": "cpcs.human_testimonial_capture/1.0",
                "render_result": str(result_path),
                "artifact_id": "artifact_000",
                "speaker": speaker,
                "language": "en-US",
                "raw_statement": "The motion reads clearly, but the final beat feels rushed.",
                "captured_at": "2027-01-15T08:05:00Z",
                "supersedes": [],
            }
            first = capture_human_testimonial(capture, root)
            self.assertEqual(capture_human_testimonial(capture, root), first)
            quote = "final beat feels rushed"
            start = capture["raw_statement"].index(quote)

            def normalization(origin: str = "human_authored") -> dict:
                value = {
                    "normalizer": {
                        "origin": origin,
                        "agent": None,
                        "model": None,
                        "prompt_hash": None,
                        "response_hash": None,
                    },
                    "normalized_verdict": "mixed",
                    "summary": "Motion is readable while the ending timing needs repair.",
                    "confidence": 0.9,
                    "dimension_findings": [
                        {
                            "dimension": "timing",
                            "verdict": "fail",
                            "observation": "The ending is rushed.",
                            "confidence": 0.95,
                            "evidence_spans": [
                                {
                                    "start": start,
                                    "end": start + len(quote),
                                    "quote": quote,
                                    "quote_hash": sha256_bytes(quote.encode("utf-8")),
                                }
                            ],
                        }
                    ],
                    "strengths": [],
                    "failures": [],
                    "attribution_candidates": [
                        {
                            "target_type": "canonical_control",
                            "target_ref": "timing.final_beat_duration",
                            "hypothesis": "The final beat duration may be too short.",
                            "confidence": 0.55,
                            "evidence_spans": [
                                {
                                    "start": start,
                                    "end": start + len(quote),
                                    "quote": quote,
                                    "quote_hash": sha256_bytes(quote.encode("utf-8")),
                                }
                            ],
                            "causal_status": "unverified_candidate",
                        }
                    ],
                    "limitations": ["One reviewer and one render."],
                }
                if origin == "llm_proposal":
                    value["normalizer"].update(
                        {
                            "agent": "fixture-normalizer",
                            "model": "fixture-1",
                            "prompt_hash": "sha256:" + "4" * 64,
                            "response_hash": "sha256:" + "0" * 64,
                        }
                    )
                    value["normalizer"]["response_hash"] = (
                        testimonial_normalization_response_hash(value)
                    )
                return value

            review_request = {
                "schema": "cpcs.testimonial_review_request/1.0",
                "testimonial_id": first["id"],
                "normalization": normalization(),
                "reviewed_by": "director_fixture",
                "reviewed_at": "2027-01-15T08:06:00Z",
                "supersedes_reviews": [],
            }
            first_review = review_human_testimonial(review_request, root)
            self.assertEqual(
                review_human_testimonial(review_request, root), first_review
            )
            invalid_span = copy.deepcopy(review_request)
            invalid_span["reviewed_at"] = "2027-01-15T08:07:00Z"
            invalid_span["supersedes_reviews"] = [first_review["id"]]
            invalid_span["normalization"]["dimension_findings"][0][
                "evidence_spans"
            ][0]["quote"] = "not the source quote"
            with self.assertRaisesRegex(ValidationFailure, "does not match"):
                review_human_testimonial(invalid_span, root)

            correction = copy.deepcopy(capture)
            correction["raw_statement"] = (
                "Correction: the motion reads clearly, and the final beat feels rushed."
            )
            correction["captured_at"] = "2027-01-15T08:08:00Z"
            correction["supersedes"] = [first["id"]]
            corrected = capture_human_testimonial(correction, root)
            corrected_quote = "final beat feels rushed"
            corrected_start = correction["raw_statement"].index(corrected_quote)
            corrected_normalization = normalization("llm_proposal")
            for row in (
                corrected_normalization["dimension_findings"]
                + corrected_normalization["attribution_candidates"]
            ):
                row["evidence_spans"][0] = {
                    "start": corrected_start,
                    "end": corrected_start + len(corrected_quote),
                    "quote": corrected_quote,
                    "quote_hash": sha256_bytes(corrected_quote.encode("utf-8")),
                }
            corrected_normalization["normalizer"]["response_hash"] = (
                testimonial_normalization_response_hash(corrected_normalization)
            )
            corrected_review = review_human_testimonial(
                {
                    "schema": "cpcs.testimonial_review_request/1.0",
                    "testimonial_id": corrected["id"],
                    "normalization": corrected_normalization,
                    "reviewed_by": "director_fixture",
                    "reviewed_at": "2027-01-15T08:09:00Z",
                    "supersedes_reviews": [first_review["id"]],
                },
                root,
            )
            inspection = inspect_human_testimonial(first["id"], root)
            self.assertEqual(len(inspection["testimonials"]), 2)
            self.assertEqual(len(inspection["reviews"]), 2)
            self.assertEqual(inspection["current_testimonial_ids"], [corrected["id"]])
            self.assertEqual(
                inspection["current_review_ids"], [corrected_review["id"]]
            )
            self.assertEqual(validate_immutable(root)["human_testimonial"], 2)

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
