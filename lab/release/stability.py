"""Deterministic evaluator-drift and held-out optimization stability checks."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any

from lab.second_brain.src.validate import REPO_ROOT, canonical_json_bytes, sha256_value

from .contracts import load_release_policy, validate_release_instance


SCHEMA = "cpcs.evaluator_stability_report/1.0"
REQUEST_SCHEMA = "cpcs.evaluator_stability_request/1.0"
EFFECT = "supporting_evidence_only"


def _git_bytes(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True
    ).stdout


def _git_text(root: Path, *args: str) -> str:
    return _git_bytes(root, *args).decode("utf-8").strip()


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def evaluator_identity_hash(identity: dict[str, Any]) -> str:
    """Return the server-owned identity of one versioned evaluator contract."""
    return sha256_value(identity)


def source_state(root: Path = REPO_ROOT) -> dict[str, str]:
    """Bind a report to exact committed and working-tree source bytes."""
    root = root.resolve()
    revision = _git_text(root, "rev-parse", "HEAD")
    status_bytes = _git_bytes(
        root, "status", "--porcelain=v1", "-z", "--untracked-files=all"
    )
    tracked_diff = _git_bytes(root, "diff", "--binary", "HEAD", "--", ".")
    untracked = [
        os.fsdecode(row)
        for row in _git_bytes(
            root, "ls-files", "--others", "--exclude-standard", "-z"
        ).split(b"\0")
        if row
    ]
    untracked_rows: list[dict[str, str]] = []
    for relative in sorted(row for row in untracked if row):
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError("source-state untracked entries must be regular files")
        untracked_rows.append(
            {"path": relative, "sha256": _sha256_bytes(path.read_bytes())}
        )
    fingerprint = sha256_value(
        {
            "revision": revision,
            "status_sha256": _sha256_bytes(status_bytes),
            "tracked_diff_sha256": _sha256_bytes(tracked_diff),
            "untracked": untracked_rows,
        }
    )
    return {
        "revision": revision,
        "state": "clean" if not status_bytes else "dirty",
        "state_hash": fingerprint,
    }


def _work_root(root: Path) -> Path:
    work = root / "work"
    release = work / "release"
    path = release / "evaluator_stability"
    for directory in (work, release, path):
        if directory.is_symlink():
            raise ValueError("evaluator stability work roots cannot be symlinks")
        directory.mkdir(exist_ok=True, mode=0o700)
        if not directory.is_dir():
            raise ValueError("evaluator stability work root is not a directory")
    os.chmod(path, 0o700)
    return path


def _safe_file(path: Path, root: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError("evaluator stability state is missing or unsafe")
    metadata = path.stat()
    if metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise ValueError("evaluator stability state must be mode 0600 with one link")
    limit = load_release_policy(root)[0]["limits"]["qualification_manifest_bytes"]
    if metadata.st_size > limit:
        raise ValueError("evaluator stability state exceeds the qualification manifest limit")


def _write_new(path: Path, value: dict[str, Any]) -> None:
    data = canonical_json_bytes(value)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    os.chmod(path, 0o600)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _rounded(value: float) -> float:
    return round(value, 12)


def _score(item: dict[str, Any]) -> float:
    return float(item["score"])


def _declared_qualification_hashes(
    request: dict[str, Any]
) -> dict[str, set[str]]:
    shared = {request["suite_manifest_hash"]}
    for evaluator in (request["reference_evaluator"], request["candidate_evaluator"]):
        shared.update((evaluator["prompt_hash"], evaluator["response_schema_hash"]))
    calibration = set(shared)
    for case in request["calibration_cases"]:
        calibration.add(case["artifact_hash"])
        calibration.update(
            case[key]["evidence_hash"]
            for key in ("human", "reference_evaluator", "candidate_evaluator")
        )
    held_out = set(shared)
    held_out.add(request["optimization"]["manifest_hash"])
    for case in request["heldout_cases"]:
        held_out.update(
            (case["baseline_artifact_hash"], case["candidate_artifact_hash"])
        )
        held_out.update(
            case[key]["evidence_hash"]
            for key in (
                "human_baseline",
                "human_candidate",
                "evaluator_baseline",
                "evaluator_candidate",
            )
        )
    return {"calibration": calibration, "held_out": held_out}


def _calibration_metrics(request: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings = []
    reference_errors = []
    candidate_errors = []
    drifts = []
    for case in request["calibration_cases"]:
        human = _score(case["human"])
        reference = _score(case["reference_evaluator"])
        candidate = _score(case["candidate_evaluator"])
        reference_error = abs(reference - human)
        candidate_error = abs(candidate - human)
        drift = abs(candidate - reference)
        reference_errors.append(reference_error)
        candidate_errors.append(candidate_error)
        drifts.append(drift)
        findings.append(
            {
                "case_id": case["case_id"],
                "reference_error": _rounded(reference_error),
                "candidate_error": _rounded(candidate_error),
                "evaluator_drift": _rounded(drift),
            }
        )
    reference_mae = _mean(reference_errors)
    candidate_mae = _mean(candidate_errors)
    return (
        {
            "case_count": len(findings),
            "reference_mae": _rounded(reference_mae),
            "candidate_mae": _rounded(candidate_mae),
            "mae_regression": _rounded(candidate_mae - reference_mae),
            "max_case_drift": _rounded(max(drifts)),
        },
        findings,
    )


def _heldout_metrics(request: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    threshold = request["thresholds"]
    findings = []
    delta_gaps = []
    collapse_count = 0
    sign_disagreements = 0
    for case in request["heldout_cases"]:
        human_delta = _score(case["human_candidate"]) - _score(case["human_baseline"])
        evaluator_delta = _score(case["evaluator_candidate"]) - _score(case["evaluator_baseline"])
        delta_gap = abs(evaluator_delta - human_delta)
        collapse = (
            evaluator_delta >= threshold["min_evaluator_gain_for_collapse"]
            and human_delta <= -threshold["min_human_regression_for_collapse"]
        )
        sign_disagreement = (
            (evaluator_delta > 0 and human_delta < 0)
            or (evaluator_delta < 0 and human_delta > 0)
        )
        collapse_count += int(collapse)
        sign_disagreements += int(sign_disagreement)
        delta_gaps.append(delta_gap)
        findings.append(
            {
                "case_id": case["case_id"],
                "human_delta": _rounded(human_delta),
                "evaluator_delta": _rounded(evaluator_delta),
                "delta_gap": _rounded(delta_gap),
                "recursive_optimization_collapse": collapse,
                "sign_disagreement": sign_disagreement,
            }
        )
    return (
        {
            "case_count": len(findings),
            "mean_human_delta": _rounded(
                _mean([row["human_delta"] for row in findings])
            ),
            "mean_evaluator_delta": _rounded(
                _mean([row["evaluator_delta"] for row in findings])
            ),
            "max_delta_gap": _rounded(max(delta_gaps)),
            "recursive_optimization_collapse_count": collapse_count,
            "sign_disagreement_count": sign_disagreements,
        },
        findings,
    )


def _evaluate(request: dict[str, Any], root: Path) -> dict[str, Any]:
    reference_hash = evaluator_identity_hash(request["reference_evaluator"])
    candidate_hash = evaluator_identity_hash(request["candidate_evaluator"])
    if reference_hash == candidate_hash:
        raise ValueError("reference and candidate evaluator identities must differ")
    optimization = request["optimization"]
    if optimization["candidate_optimized_against_evaluator_hash"] != candidate_hash:
        raise ValueError("optimization target does not match the candidate evaluator identity")
    optimization_ids = set(optimization["case_ids"])
    calibration_ids = [row["case_id"] for row in request["calibration_cases"]]
    heldout_ids = [row["case_id"] for row in request["heldout_cases"]]
    if len(calibration_ids) != len(set(calibration_ids)):
        raise ValueError("calibration case IDs must be unique")
    if len(heldout_ids) != len(set(heldout_ids)):
        raise ValueError("held-out case IDs must be unique")
    overlap = (optimization_ids | set(calibration_ids)) & set(heldout_ids)
    if overlap:
        raise ValueError("held-out cases must be disjoint from optimization and calibration cases")
    calibration_artifacts = [row["artifact_id"] for row in request["calibration_cases"]]
    if len(calibration_artifacts) != len(set(calibration_artifacts)):
        raise ValueError("calibration artifact IDs must be unique")
    for case in request["calibration_cases"]:
        if case["human"]["evidence_class"] != "human_review" or any(
            case[key]["evidence_class"] != "interpreted"
            for key in ("reference_evaluator", "candidate_evaluator")
        ):
            raise ValueError("calibration scores use the wrong evidence class")
    for case in request["heldout_cases"]:
        if (
            case["baseline_artifact_id"] == case["candidate_artifact_id"]
            or case["baseline_artifact_hash"] == case["candidate_artifact_hash"]
        ):
            raise ValueError("held-out baseline and candidate artifacts must differ")
        if any(
            case[key]["evidence_class"] != "human_review"
            for key in ("human_baseline", "human_candidate")
        ) or any(
            case[key]["evidence_class"] != "interpreted"
            for key in ("evaluator_baseline", "evaluator_candidate")
        ):
            raise ValueError("held-out scores use the wrong evidence class")
    declared_hashes = _declared_qualification_hashes(request)
    external_limit = load_release_policy(root)[0]["limits"]["external_evidence_items"]
    if len(declared_hashes["calibration"] | declared_hashes["held_out"]) + 2 > external_limit:
        raise ValueError(
            "evaluator stability artifact closure exceeds the release evidence-item limit"
        )

    calibration, calibration_findings = _calibration_metrics(request)
    heldout, heldout_findings = _heldout_metrics(request)
    thresholds = request["thresholds"]
    checks = {
        "candidate_mae": calibration["candidate_mae"] <= thresholds["max_candidate_mae"],
        "case_drift": calibration["max_case_drift"] <= thresholds["max_case_drift"],
        "mae_regression": calibration["mae_regression"] <= thresholds["max_mae_regression"],
        "heldout_delta_gap": heldout["max_delta_gap"] <= thresholds["max_delta_gap"],
        "recursive_optimization_collapse": heldout["recursive_optimization_collapse_count"] == 0,
        "sign_disagreements": heldout["sign_disagreement_count"] <= thresholds["max_sign_disagreements"],
    }
    stability_status = "passed" if all(checks.values()) else "failed"
    source = source_state(root)
    request_hash = sha256_value(request)
    report_id = "stability_" + sha256_value(
        {
            "request_hash": request_hash,
            "source_revision": source["revision"],
            "source_state_hash": source["state_hash"],
        }
    ).removeprefix("sha256:")[:24]
    readiness = (
        "failed_stability"
        if stability_status == "failed"
        else "eligible"
        if source["state"] == "clean"
        else "ineligible_dirty_source"
    )
    core = {
        "schema": SCHEMA,
        "report_id": report_id,
        "request_hash": request_hash,
        "suite_id": request["suite_id"],
        "suite_manifest_hash": request["suite_manifest_hash"],
        "source_revision": source["revision"],
        "source_state": source["state"],
        "source_state_hash": source["state_hash"],
        "evaluator_identities": {
            "reference": reference_hash,
            "candidate": candidate_hash,
        },
        "optimization_manifest_hash": optimization["manifest_hash"],
        "thresholds": copy.deepcopy(thresholds),
        "metrics": {"calibration": calibration, "held_out": heldout},
        "findings": {
            "calibration": calibration_findings,
            "held_out": heldout_findings,
        },
        "checks": checks,
        "stability_status": stability_status,
        "qualification_readiness": readiness,
        "eligible_gates": ["calibration", "held_out"] if readiness == "eligible" else [],
        "qualification_effect": EFFECT,
    }
    return {**core, "report_hash": sha256_value(core)}


def evaluate_stability(
    request: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Validate, evaluate, and persist one content-bound supporting report."""
    root = root.resolve()
    request = copy.deepcopy(request)
    validate_release_instance("evaluator_stability_request", request, root)
    if len(canonical_json_bytes(request)) > load_release_policy(root)[0]["limits"][
        "qualification_manifest_bytes"
    ]:
        raise ValueError("evaluator stability request exceeds the qualification manifest limit")
    report = _evaluate(request, root)
    validate_release_instance("evaluator_stability_report", report, root)
    directory = _work_root(root) / report["report_id"]
    request_path = directory / "request.json"
    report_path = directory / "report.json"
    if directory.exists():
        return inspect_stability(report["report_id"], root)
    directory.mkdir(mode=0o700)
    os.chmod(directory, 0o700)
    try:
        _write_new(request_path, request)
        _write_new(report_path, report)
    except Exception:
        request_path.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)
        directory.rmdir()
        raise
    return report


def inspect_stability(
    report_id: str, root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Read one report only after request, result, and source-state replay."""
    root = root.resolve()
    if not report_id.startswith("stability_") or len(report_id) != 34:
        raise ValueError("invalid evaluator stability report ID")
    directory = _work_root(root) / report_id
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("evaluator stability report does not exist")
    if stat.S_IMODE(directory.stat().st_mode) != 0o700:
        raise ValueError("evaluator stability directory must be mode 0700")
    request_path = directory / "request.json"
    report_path = directory / "report.json"
    _safe_file(request_path, root)
    _safe_file(report_path, root)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    stored = json.loads(report_path.read_text(encoding="utf-8"))
    validate_release_instance("evaluator_stability_request", request, root)
    validate_release_instance("evaluator_stability_report", stored, root)
    replay = _evaluate(request, root)
    if replay != stored or replay["report_id"] != report_id:
        raise ValueError("evaluator stability state failed exact replay")
    return stored


def _load_stability_bundle(
    path: Path, root: Path
) -> tuple[dict[str, Any], dict[str, Any], bytes, bytes]:
    """Capture and validate one report and request byte pair exactly once."""
    supplied = path.expanduser()
    if supplied.is_symlink() or not supplied.resolve().is_file():
        raise ValueError("evaluator stability report is missing or a symlink")
    report_path = supplied.resolve()
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    validate_release_instance("evaluator_stability_report", report, root)
    if report_bytes != canonical_json_bytes(report):
        raise ValueError("evaluator stability report must use canonical JSON bytes")
    request_path = report_path.parent / "request.json"
    if request_path.is_symlink() or not request_path.is_file():
        raise ValueError("evaluator stability report requires its canonical sibling request")
    request_bytes = request_path.read_bytes()
    limit = load_release_policy(root)[0]["limits"]["qualification_manifest_bytes"]
    if len(report_bytes) > limit or len(request_bytes) > limit:
        raise ValueError("evaluator stability report or request exceeds the manifest limit")
    request = json.loads(request_bytes)
    validate_release_instance("evaluator_stability_request", request, root)
    if request_bytes != canonical_json_bytes(request):
        raise ValueError("evaluator stability request must use canonical JSON bytes")
    replay = _evaluate(request, root)
    if replay != report:
        raise ValueError("evaluator stability qualification input failed exact replay")
    return report, request, report_bytes, request_bytes


def load_stability_report(path: Path, root: Path = REPO_ROOT) -> dict[str, Any]:
    """Load an exact canonical report file for release qualification."""
    return _load_stability_bundle(path, root.resolve())[0]


def qualification_artifact_hashes(
    report_path: Path, root: Path = REPO_ROOT
) -> tuple[dict[str, Any], dict[str, list[str]]]:
    """Return the complete artifact closure required for trusted gate evidence."""
    report_path = report_path.expanduser().resolve()
    report, request, report_bytes, request_bytes = _load_stability_bundle(
        report_path, root.resolve()
    )
    shared_files = {
        _sha256_bytes(report_bytes),
        _sha256_bytes(request_bytes),
    }
    declared = _declared_qualification_hashes(request)
    calibration = declared["calibration"] | shared_files
    held_out = declared["held_out"] | shared_files
    limit = load_release_policy(root)[0]["limits"]["external_evidence_items"]
    if len(calibration | held_out) > limit:
        raise ValueError(
            "evaluator stability artifact closure exceeds the release evidence-item limit"
        )
    return report, {
        "calibration": sorted(calibration),
        "held_out": sorted(held_out),
    }
