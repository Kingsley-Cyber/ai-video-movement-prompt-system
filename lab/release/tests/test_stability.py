from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from lab.application.service import REQUEST_SCHEMA, invoke, list_operations
from lab.release.stability import (
    evaluate_stability,
    evaluator_identity_hash,
    inspect_stability,
    qualification_artifact_hashes,
)
from lab.release.evidence import secret_environment_name, sign_external_evidence
from lab.release.qualification import assess
from lab.second_brain.src.validate import REPO_ROOT, canonical_json_bytes


HASH = "sha256:" + "a" * 64


def _score(value: float, evidence_class: str, tag: str) -> dict:
    return {
        "score": value,
        "evidence_ref": f"fixture://{tag}",
        "evidence_hash": "sha256:" + hashlib.sha256(tag.encode()).hexdigest(),
        "evidence_class": evidence_class,
    }


def _evaluator(evaluator_id: str, version: str) -> dict:
    return {
        "evaluator_id": evaluator_id,
        "model": "fixture-model",
        "version": version,
        "prompt_hash": "sha256:" + ("1" if version == "1" else "2") * 64,
        "response_schema_hash": HASH,
    }


def _hash(tag: str) -> str:
    return "sha256:" + hashlib.sha256(tag.encode()).hexdigest()


def _request() -> dict:
    reference = _evaluator("reference_eval", "1")
    candidate = _evaluator("candidate_eval", "2")
    calibration = []
    for index, human in enumerate((0.6, 0.7, 0.5), 1):
        calibration.append(
            {
                "case_id": f"case_calibration_{index}",
                "artifact_id": f"artifact_calibration_{index}",
                "artifact_hash": _hash(f"artifact-calibration-{index}"),
                "human": _score(human, "human_review", f"human-cal-{index}"),
                "reference_evaluator": _score(human - 0.02, "interpreted", f"ref-cal-{index}"),
                "candidate_evaluator": _score(human - 0.03, "interpreted", f"candidate-cal-{index}"),
            }
        )
    heldout = []
    for index, baseline in enumerate((0.4, 0.5, 0.6), 1):
        heldout.append(
            {
                "case_id": f"case_heldout_{index}",
                "baseline_artifact_id": f"artifact_baseline_{index}",
                "baseline_artifact_hash": _hash(f"artifact-baseline-{index}"),
                "candidate_artifact_id": f"artifact_candidate_{index}",
                "candidate_artifact_hash": _hash(f"artifact-candidate-{index}"),
                "human_baseline": _score(baseline, "human_review", f"human-base-{index}"),
                "human_candidate": _score(baseline + 0.1, "human_review", f"human-candidate-{index}"),
                "evaluator_baseline": _score(baseline + 0.01, "interpreted", f"eval-base-{index}"),
                "evaluator_candidate": _score(baseline + 0.1, "interpreted", f"eval-candidate-{index}"),
            }
        )
    return {
        "schema": "cpcs.evaluator_stability_request/1.0",
        "suite_id": "suite_directing_quality_v1",
        "suite_manifest_hash": HASH,
        "reference_evaluator": reference,
        "candidate_evaluator": candidate,
        "optimization": {
            "candidate_optimized_against_evaluator_hash": evaluator_identity_hash(candidate),
            "manifest_hash": HASH,
            "case_ids": ["case_optimization_1", "case_optimization_2", "case_optimization_3"],
        },
        "thresholds": {
            "max_candidate_mae": 0.1,
            "max_case_drift": 0.1,
            "max_mae_regression": 0.05,
            "max_delta_gap": 0.1,
            "min_evaluator_gain_for_collapse": 0.1,
            "min_human_regression_for_collapse": 0.1,
            "max_sign_disagreements": 0,
        },
        "calibration_cases": calibration,
        "heldout_cases": heldout,
    }


def _fixture_root(base: Path) -> Path:
    root = base / "repo"
    (root / "lab" / "release").mkdir(parents=True)
    (root / "lab" / "application").mkdir(parents=True)
    shutil.copytree(REPO_ROOT / "lab/release/schemas", root / "lab/release/schemas")
    shutil.copytree(REPO_ROOT / "lab/application/schemas", root / "lab/application/schemas")
    shutil.copy2(REPO_ROOT / "lab/release/policy.yaml", root / "lab/release/policy.yaml")
    (root / ".gitignore").write_text("work/\n", encoding="utf-8")
    (root / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
    return root


def _materialize_qualification_artifacts(
    request: dict, bundle: Path
) -> dict[str, dict]:
    artifact_root = bundle / "artifacts"
    artifact_root.mkdir(parents=True)
    by_hash: dict[str, dict] = {}

    def write(tag: str) -> tuple[str, str]:
        path = artifact_root / f"{tag}.json"
        path.write_bytes(canonical_json_bytes({"tag": tag, "fixture": True}))
        digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        by_hash[digest] = {
            "path": path.relative_to(bundle).as_posix(),
            "sha256": digest,
            "size_bytes": path.stat().st_size,
        }
        return digest, by_hash[digest]["path"]

    request["suite_manifest_hash"] = write("suite-manifest")[0]
    response_schema_hash = write("evaluator-response-schema")[0]
    request["reference_evaluator"]["prompt_hash"] = write("reference-prompt")[0]
    request["reference_evaluator"]["response_schema_hash"] = response_schema_hash
    request["candidate_evaluator"]["prompt_hash"] = write("candidate-prompt")[0]
    request["candidate_evaluator"]["response_schema_hash"] = response_schema_hash
    request["optimization"]["manifest_hash"] = write("optimization-manifest")[0]
    request["optimization"][
        "candidate_optimized_against_evaluator_hash"
    ] = evaluator_identity_hash(request["candidate_evaluator"])

    for case in request["calibration_cases"]:
        case["artifact_hash"] = write(case["artifact_id"])[0]
        for key in ("human", "reference_evaluator", "candidate_evaluator"):
            digest, relative = write(f"{case['case_id']}-{key}")
            case[key]["evidence_hash"] = digest
            case[key]["evidence_ref"] = relative
    for case in request["heldout_cases"]:
        case["baseline_artifact_hash"] = write(case["baseline_artifact_id"])[0]
        case["candidate_artifact_hash"] = write(case["candidate_artifact_id"])[0]
        for key in (
            "human_baseline",
            "human_candidate",
            "evaluator_baseline",
            "evaluator_candidate",
        ):
            digest, relative = write(f"{case['case_id']}-{key}")
            case[key]["evidence_hash"] = digest
            case[key]["evidence_ref"] = relative
    return by_hash


class EvaluatorStabilityTests(unittest.TestCase):
    def test_pass_replay_modes_and_public_operator_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _fixture_root(Path(temporary))
            request = _request()
            first = evaluate_stability(copy.deepcopy(request), root)
            second = evaluate_stability(copy.deepcopy(request), root)
            self.assertEqual(first, second)
            self.assertEqual(first["stability_status"], "passed")
            self.assertEqual(first["qualification_readiness"], "eligible")
            self.assertEqual(first["eligible_gates"], ["calibration", "held_out"])
            self.assertEqual(first["qualification_effect"], "supporting_evidence_only")
            directory = root / "work/release/evaluator_stability" / first["report_id"]
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            self.assertEqual((directory / "request.json").stat().st_mode & 0o777, 0o600)
            self.assertEqual((directory / "report.json").stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=root,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout,
                "",
            )

            evaluated = invoke(
                {
                    "schema": REQUEST_SCHEMA,
                    "operation": "cpcs.qualification.stability.evaluate",
                    "arguments": {"request": copy.deepcopy(request)},
                },
                role="operator",
                root=root,
            )
            self.assertEqual(evaluated["status"], "success")
            self.assertEqual(evaluated["result"], first)

            denied = invoke(
                {
                    "schema": REQUEST_SCHEMA,
                    "operation": "cpcs.qualification.stability.inspect",
                    "arguments": {"report_id": first["report_id"]},
                },
                root=root,
            )
            self.assertEqual(denied["error"]["code"], "permission_denied")
            inspected = invoke(
                {
                    "schema": REQUEST_SCHEMA,
                    "operation": "cpcs.qualification.stability.inspect",
                    "arguments": {"report_id": first["report_id"]},
                },
                role="operator",
                root=root,
            )
            self.assertEqual(inspected["status"], "success")
            self.assertEqual(inspected["result"], first)
            brief = invoke(
                {
                    "schema": REQUEST_SCHEMA,
                    "operation": "cpcs.agent.brief",
                    "arguments": {
                        "task": "Detect evaluator drift and recursive optimization failure on held-out cases",
                        "role": "operator",
                    },
                },
                root=root,
            )
            self.assertEqual(brief["status"], "success")
            self.assertIn(
                "evaluator_stability",
                brief["result"]["task_routing"]["selected_workflows"],
            )
            brief_operations = {row["name"] for row in brief["result"]["operations"]}
            self.assertIn("cpcs.qualification.stability.evaluate", brief_operations)
            self.assertIn("cpcs.qualification.stability.inspect", brief_operations)
            names = {row["name"] for row in list_operations("operator")}
            self.assertIn("cpcs.qualification.stability.evaluate", names)
            self.assertIn("cpcs.qualification.stability.inspect", names)

    def test_drift_collapse_dirty_source_and_closed_contracts_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)

            drift_root = _fixture_root(base / "drift")
            drift = _request()
            drift["calibration_cases"][0]["candidate_evaluator"]["score"] = 0.95
            drift_report = evaluate_stability(drift, drift_root)
            self.assertEqual(drift_report["stability_status"], "failed")
            self.assertFalse(drift_report["checks"]["case_drift"])

            collapse_root = _fixture_root(base / "collapse")
            collapse = _request()
            case = collapse["heldout_cases"][0]
            case["human_baseline"]["score"] = 0.7
            case["human_candidate"]["score"] = 0.4
            case["evaluator_baseline"]["score"] = 0.3
            case["evaluator_candidate"]["score"] = 0.8
            collapse_report = evaluate_stability(collapse, collapse_root)
            self.assertEqual(collapse_report["stability_status"], "failed")
            self.assertEqual(
                collapse_report["metrics"]["held_out"]["recursive_optimization_collapse_count"],
                1,
            )
            self.assertFalse(collapse_report["checks"]["recursive_optimization_collapse"])

            dirty_root = _fixture_root(base / "dirty")
            (dirty_root / "tracked.txt").write_text("changed\n", encoding="utf-8")
            dirty_report = evaluate_stability(_request(), dirty_root)
            self.assertEqual(dirty_report["source_state"], "dirty")
            self.assertEqual(dirty_report["qualification_readiness"], "ineligible_dirty_source")

            invalid_root = _fixture_root(base / "invalid")
            unknown = _request()
            unknown["candidate_evaluator"]["unknown"] = True
            with self.assertRaisesRegex(ValueError, "Additional properties"):
                evaluate_stability(unknown, invalid_root)
            mismatch = _request()
            mismatch["optimization"]["candidate_optimized_against_evaluator_hash"] = HASH
            with self.assertRaisesRegex(ValueError, "optimization target"):
                evaluate_stability(mismatch, invalid_root)
            overlap = _request()
            overlap["optimization"]["case_ids"][0] = "case_heldout_1"
            with self.assertRaisesRegex(ValueError, "disjoint"):
                evaluate_stability(overlap, invalid_root)
            wrong_lane = _request()
            wrong_lane["heldout_cases"][0]["human_candidate"]["evidence_class"] = "interpreted"
            with self.assertRaisesRegex(ValueError, "wrong evidence class"):
                evaluate_stability(wrong_lane, invalid_root)
            same_artifact = _request()
            same_artifact["heldout_cases"][0]["candidate_artifact_hash"] = same_artifact[
                "heldout_cases"
            ][0]["baseline_artifact_hash"]
            with self.assertRaisesRegex(ValueError, "artifacts must differ"):
                evaluate_stability(same_artifact, invalid_root)
            oversized = _request()
            template = oversized["heldout_cases"][0]
            oversized["heldout_cases"] = []
            for index in range(10):
                case = copy.deepcopy(template)
                case["case_id"] = f"case_heldout_extra_{index}"
                case["baseline_artifact_id"] = f"artifact_baseline_extra_{index}"
                case["candidate_artifact_id"] = f"artifact_candidate_extra_{index}"
                case["baseline_artifact_hash"] = _hash(f"oversized-base-{index}")
                case["candidate_artifact_hash"] = _hash(f"oversized-candidate-{index}")
                for key in (
                    "human_baseline",
                    "human_candidate",
                    "evaluator_baseline",
                    "evaluator_candidate",
                ):
                    case[key]["evidence_hash"] = _hash(f"oversized-{key}-{index}")
                oversized["heldout_cases"].append(case)
            with self.assertRaisesRegex(ValueError, "evidence-item limit"):
                evaluate_stability(oversized, invalid_root)

    def test_stored_report_tampering_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _fixture_root(Path(temporary))
            report = evaluate_stability(_request(), root)
            path = root / "work/release/evaluator_stability" / report["report_id"] / "report.json"
            tampered = json.loads(path.read_text(encoding="utf-8"))
            tampered["metrics"]["calibration"]["candidate_mae"] = 0.0
            path.write_text(json.dumps(tampered, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            os.chmod(path, 0o600)
            with self.assertRaisesRegex(ValueError, "exact replay|hash is invalid"):
                inspect_stability(report["report_id"], root)

    def test_release_requires_complete_trusted_stability_artifact_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            shutil.copytree(
                REPO_ROOT,
                root,
                ignore=shutil.ignore_patterns(".git", "work", "__pycache__", "*.pyc"),
            )
            secret = "stability-test-owner-key-00000001"
            policy_path = root / "lab/release/policy.yaml"
            policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
            policy["qualification_trust"]["trusted_evaluators"] = {
                "stability_owner": {
                    "secret_sha256": "sha256:"
                    + hashlib.sha256(secret.encode()).hexdigest(),
                    "allowed_gates": ["calibration", "held_out"],
                }
            }
            policy_path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
            revision = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            bundle = root / "work/qualification"
            bundle.mkdir(parents=True)
            request = _request()
            artifacts_by_hash = _materialize_qualification_artifacts(request, bundle)
            stability = evaluate_stability(request, root)
            stability_path = (
                root
                / "work/release/evaluator_stability"
                / stability["report_id"]
                / "report.json"
            )
            copied_report = bundle / "stability.json"
            copied_report.write_bytes(stability_path.read_bytes())
            copied_request = bundle / "request.json"
            copied_request.write_bytes(stability_path.with_name("request.json").read_bytes())
            report_artifact = {
                "path": copied_report.name,
                "sha256": "sha256:"
                + hashlib.sha256(copied_report.read_bytes()).hexdigest(),
                "size_bytes": copied_report.stat().st_size,
            }
            request_artifact = {
                "path": copied_request.name,
                "sha256": "sha256:"
                + hashlib.sha256(copied_request.read_bytes()).hexdigest(),
                "size_bytes": copied_request.stat().st_size,
            }
            artifacts_by_hash[report_artifact["sha256"]] = report_artifact
            artifacts_by_hash[request_artifact["sha256"]] = request_artifact
            loaded, required = qualification_artifact_hashes(copied_report, root)
            self.assertEqual(loaded, stability)
            calibration_gate = {
                "status": "passed",
                "evaluated_at": "2026-08-05T00:00:00Z",
                "artifacts": [artifacts_by_hash[digest] for digest in required["calibration"]],
                "metrics": {"cases": 3},
                "summary": "Trusted evaluator accepted the complete calibration evidence set.",
            }
            heldout_gate = {
                "status": "passed",
                "evaluated_at": "2026-08-05T00:00:00Z",
                "artifacts": [artifacts_by_hash[digest] for digest in required["held_out"]],
                "metrics": {"cases": 3},
                "summary": "Trusted evaluator accepted the complete held-out evidence set.",
            }
            evidence = sign_external_evidence(
                {
                    "schema": "cpcs.external_qualification_evidence/2.0",
                    "source_revision": revision,
                    "evaluator_id": "stability_owner",
                    "gates": {
                        "calibration": copy.deepcopy(calibration_gate),
                        "held_out": copy.deepcopy(heldout_gate),
                    },
                },
                secret,
            )
            evidence_path = bundle / "evidence.json"
            evidence_path.write_bytes(canonical_json_bytes(evidence))
            environment = {secret_environment_name("stability_owner"): secret}
            with mock.patch.dict(os.environ, environment, clear=False):
                report = assess(
                    root=root,
                    external_evidence=evidence,
                    external_evidence_path=evidence_path,
                    stability_report=stability,
                    stability_report_path=copied_report,
                )
            gates = {row["gate"]: row for row in report["gates"]}
            self.assertEqual(gates["evaluator_stability_preflight"]["status"], "passed")
            self.assertEqual(gates["calibration"]["status"], "passed")
            self.assertEqual(gates["held_out"]["status"], "passed")

            unbound_gate = copy.deepcopy(heldout_gate)
            omitted_hash = next(
                digest
                for digest in required["held_out"]
                if digest not in set(required["calibration"])
            )
            unbound_gate["artifacts"] = [
                row for row in unbound_gate["artifacts"] if row["sha256"] != omitted_hash
            ]
            unbound = sign_external_evidence(
                {
                    "schema": "cpcs.external_qualification_evidence/2.0",
                    "source_revision": revision,
                    "evaluator_id": "stability_owner",
                    "gates": {
                        "calibration": copy.deepcopy(calibration_gate),
                        "held_out": unbound_gate,
                    },
                },
                secret,
            )
            unbound_path = bundle / "unbound-evidence.json"
            unbound_path.write_bytes(canonical_json_bytes(unbound))
            with mock.patch.dict(os.environ, environment, clear=False):
                rejected = assess(
                    root=root,
                    external_evidence=unbound,
                    external_evidence_path=unbound_path,
                    stability_report=stability,
                    stability_report_path=copied_report,
                )
            rejected_gates = {row["gate"]: row for row in rejected["gates"]}
            self.assertEqual(rejected_gates["held_out"]["status"], "failed")
            self.assertIn("missing required", rejected_gates["held_out"]["blocker"])
            self.assertIn(omitted_hash, rejected_gates["held_out"]["blocker"])


if __name__ == "__main__":
    unittest.main()
