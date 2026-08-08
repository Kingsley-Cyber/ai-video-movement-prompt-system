"""Deterministically verify one render against its compiler-owned plan."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import statistics
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, FormatChecker

from lab.compiler.build import load_validated_build_directory
from lab.compiler.profiles import REPO_ROOT
from lab.compiler.provenance import canonical_json_bytes, sha256_bytes, sha256_value
from lab.runtime.contracts import validate_runtime_instance
from lab.second_brain.src.measurement import validate_measurement_batch
from lab.second_brain.src.validate import validate_instance
from lab.second_brain.src.video_observation import (
    assert_claim_policy,
    probe_media,
    validate_video_observation_graph,
)

VERIFICATION_POLICY = "cpcs-render-verification/1.0"
REPAIR_POLICY = "cpcs-bounded-repair/1.0"
REFERENCE_ROUND_TRIP_POLICY = "cpcs-reference-round-trip/1.0"
REFERENCE_CANDIDATE_COMPARISON_POLICY = "cpcs-reference-candidate-comparison/1.0"
EVIDENCE_SCHEMA = "cpcs.verification_evidence_bundle/1.0"
REPORT_SCHEMA = "cpcs.compliance_report/1.0"
REFERENCE_ROUND_TRIP_SCHEMA = "cpcs.reference_round_trip_report/1.0"
REFERENCE_CANDIDATE_COMPARISON_REQUEST_SCHEMA = (
    "cpcs.reference_candidate_comparison_request/1.0"
)
REFERENCE_CANDIDATE_COMPARISON_REPORT_SCHEMA = (
    "cpcs.reference_candidate_comparison_report/1.0"
)
SCHEMAS = {
    "evidence_bundle": "verification_evidence_bundle.schema.json",
    "compliance_report": "compliance_report.schema.json",
    "reference_round_trip_report": "reference_round_trip_report.schema.json",
    "reference_candidate_comparison_request": (
        "reference_candidate_comparison_request.schema.json"
    ),
    "reference_candidate_comparison_report": (
        "reference_candidate_comparison_report.schema.json"
    ),
}
STATUS_PRECEDENCE = {
    "pass": 0,
    "unobservable": 1,
    "review_required": 2,
    "fail": 3,
    "conflict": 4,
}
DETERMINISTIC_MEASUREMENT_METHODS = frozenset(
    {
        "measured_average_hand_path_curvature",
        "product_visibility_duty_cycle",
    }
)


def _schema(name: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    if name not in SCHEMAS:
        raise ValueError(f"unknown verification schema: {name}")
    return json.loads(
        (root / "lab/verification/schemas" / SCHEMAS[name]).read_text(
            encoding="utf-8"
        )
    )


def _validate(name: str, value: Any, root: Path = REPO_ROOT) -> None:
    validator = Draft202012Validator(
        _schema(name, root), format_checker=FormatChecker()
    )
    errors = sorted(
        validator.iter_errors(value), key=lambda error: list(error.absolute_path)
    )
    if errors:
        detail = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValueError(f"{SCHEMAS[name]}: {detail}")


def validate_verification_instance(
    name: str, value: Any, root: Path = REPO_ROOT
) -> None:
    """Validate one public verification contract instance."""
    _validate(name, value, root)


def reference_candidate_comparison_request_schema(
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Return the exact public request schema for application adapters."""
    return copy.deepcopy(_schema("reference_candidate_comparison_request", root))


def validate_verification_configuration(root: Path = REPO_ROOT) -> dict[str, Any]:
    for name in SCHEMAS:
        Draft202012Validator.check_schema(_schema(name, root))
    return {
        "schemas": len(SCHEMAS),
        "verification_policy": VERIFICATION_POLICY,
        "repair_policy": REPAIR_POLICY,
        "reference_round_trip_policy": REFERENCE_ROUND_TRIP_POLICY,
        "reference_candidate_comparison_policy": (
            REFERENCE_CANDIDATE_COMPARISON_POLICY
        ),
    }


def make_evidence_source(
    record: dict[str, Any], *, source_type: str
) -> dict[str, Any]:
    if source_type == "normalized_video_observation":
        source_id = record.get("observation_id")
    elif source_type == "human_review":
        source_id = record.get("review_id")
    else:
        raise ValueError(f"unsupported verification source type: {source_type}")
    if not isinstance(source_id, str) or not source_id:
        raise ValueError("verification source has no valid source identity")
    return {
        "source_id": source_id,
        "source_type": source_type,
        "source_hash": sha256_value(record),
        "record": copy.deepcopy(record),
    }


def make_assertion(
    *,
    metric_id: str,
    target_path: str,
    source_ref: str,
    verdict: str,
    observed: Any,
    interval: dict[str, float] | None = None,
    deviation: dict[str, Any] | None = None,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    core = {
        "metric_id": metric_id,
        "target_path": target_path,
        "source_ref": source_ref,
        "verdict": verdict,
        "observed": copy.deepcopy(observed),
        "interval": copy.deepcopy(interval),
        "deviation": copy.deepcopy(deviation),
        "limitations": sorted(set(limitations or [])),
    }
    digest = hashlib.sha256(canonical_json_bytes(core)).hexdigest()[:24]
    return {"assertion_id": "verification_assertion_" + digest, **core}


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {label}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be one JSON object")
    return value


def _human_source_lane(record: dict[str, Any], artifact_id: str) -> str:
    expected = {
        "schema",
        "review_id",
        "artifact_id",
        "reviewer_id",
        "created_at",
        "notes",
    }
    if set(record) != expected:
        raise ValueError("human review record has an invalid field set")
    if record["schema"] != "cpcs.human_verification_review/1.0":
        raise ValueError("human review record has an invalid schema")
    if not isinstance(record["review_id"], str) or not record["review_id"]:
        raise ValueError("human review has no review ID")
    if record["artifact_id"] != artifact_id:
        raise ValueError("human review refers to a different artifact")
    if not isinstance(record["reviewer_id"], str) or not record["reviewer_id"]:
        raise ValueError("human review has no reviewer ID")
    if not isinstance(record["notes"], str):
        raise ValueError("human review notes must be text")
    assert_claim_policy(record["notes"], "human_review.notes")
    try:
        parsed = datetime.fromisoformat(record["created_at"].replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError("human review timestamp is invalid") from error
    if parsed.tzinfo is None:
        raise ValueError("human review timestamp must include an offset")
    return "human_review"


def _source_lane(
    source: dict[str, Any], *, artifact_id: str, artifact_hash: str, root: Path
) -> str:
    record = source["record"]
    if sha256_value(record) != source["source_hash"]:
        raise ValueError(f"verification source hash mismatch: {source['source_id']}")
    if source["source_type"] == "human_review":
        lane = _human_source_lane(record, artifact_id)
        expected_id = record["review_id"]
    else:
        validate_instance("normalized_video_observation", record, root)
        assert_claim_policy(record["claim"], "verification_source.claim")
        expected_id = record["observation_id"]
        if record["source_sha256"] != artifact_hash.removeprefix("sha256:"):
            raise ValueError("normalized observation refers to different media bytes")
        lane = (
            "measurement"
            if record["provenance"]["surface"] == "local_measurement"
            else "semantic"
        )
        if lane == "measurement" and record["evidence_class"] not in {
            "measured",
            "detected",
        }:
            raise ValueError("local measurement source has a non-measurement evidence class")
    if source["source_id"] != expected_id:
        raise ValueError("verification source ID is detached from its record")
    return lane


def _validate_evidence(
    bundle: dict[str, Any],
    *,
    job_id: str,
    build_id: str,
    artifact_id: str,
    artifact_hash: str,
    duration_seconds: float,
    requirements: list[dict[str, Any]],
    root: Path,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    _validate("evidence_bundle", bundle, root)
    expected_identity = (job_id, build_id, artifact_id, artifact_hash)
    actual_identity = (
        bundle["job_id"],
        bundle["build_id"],
        bundle["artifact_id"],
        bundle["artifact_sha256"],
    )
    if actual_identity != expected_identity:
        raise ValueError("verification evidence identity does not match build and render")
    sources: dict[str, dict[str, Any]] = {}
    for source in bundle["sources"]:
        if source["source_id"] in sources:
            raise ValueError(f"duplicate verification source: {source['source_id']}")
        enriched = copy.deepcopy(source)
        enriched["lane"] = _source_lane(
            source,
            artifact_id=artifact_id,
            artifact_hash=artifact_hash,
            root=root,
        )
        if source["source_type"] == "normalized_video_observation":
            interval = source["record"]["interval"]
            if (
                interval["end_s"] <= interval["start_s"]
                or interval["end_s"] > duration_seconds
            ):
                raise ValueError("verification source interval is outside the artifact")
        sources[source["source_id"]] = enriched
    allowed = {
        (requirement["metric_id"], target_path)
        for requirement in requirements
        for target_path in requirement["target_paths"]
    }
    requirements_by_pair = {
        (requirement["metric_id"], target_path): requirement
        for requirement in requirements
        for target_path in requirement["target_paths"]
    }
    assertions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for assertion in bundle["assertions"]:
        if assertion["assertion_id"] in seen:
            raise ValueError(f"duplicate verification assertion: {assertion['assertion_id']}")
        seen.add(assertion["assertion_id"])
        expected = make_assertion(
            metric_id=assertion["metric_id"],
            target_path=assertion["target_path"],
            source_ref=assertion["source_ref"],
            verdict=assertion["verdict"],
            observed=assertion["observed"],
            interval=assertion["interval"],
            deviation=assertion["deviation"],
            limitations=assertion["limitations"],
        )
        if expected["assertion_id"] != assertion["assertion_id"]:
            raise ValueError("verification assertion ID does not match its content")
        if assertion["source_ref"] not in sources:
            raise ValueError("verification assertion source does not exist in its bundle")
        if (assertion["metric_id"], assertion["target_path"]) not in allowed:
            raise ValueError("verification assertion targets an undeclared metric or path")
        requirement = requirements_by_pair[
            (assertion["metric_id"], assertion["target_path"])
        ]
        if (
            sources[assertion["source_ref"]]["lane"] == "measurement"
            and requirement["method"] in DETERMINISTIC_MEASUREMENT_METHODS
        ):
            raise ValueError(
                "deterministic measurement method refuses a supplied verdict"
            )
        interval = assertion["interval"]
        if interval is not None and (
            interval["end_s"] <= interval["start_s"]
            or interval["end_s"] > duration_seconds
        ):
            raise ValueError("verification assertion interval is outside the artifact")
        enriched = copy.deepcopy(assertion)
        enriched["lane"] = sources[assertion["source_ref"]]["lane"]
        enriched["origin"] = "supplied"
        assertions.append(enriched)
    return sources, sorted(assertions, key=lambda row: row["assertion_id"])


def _derive_measurement_assertions(
    *,
    sources: dict[str, dict[str, Any]],
    assertions: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    score: dict[str, Any],
) -> list[dict[str, Any]]:
    """Execute the closed local comparator set without trusting supplied verdicts."""
    requirements_by_metric = {row["metric_id"]: row for row in requirements}
    controls_by_path = {
        row["path"]: row for row in score["provider_neutral_controls"]
    }
    existing = {
        (row["metric_id"], row["target_path"], row["source_ref"])
        for row in assertions
    }
    derived: list[dict[str, Any]] = []
    for source_id, source in sorted(sources.items()):
        if source["lane"] != "measurement":
            continue
        record = source["record"]
        claim = record["claim"]
        metric_id = claim.get("metric_id")
        if not isinstance(metric_id, str) or metric_id not in requirements_by_metric:
            continue
        requirement = requirements_by_metric[metric_id]
        method = claim.get("method")
        if method != requirement["method"]:
            raise ValueError("measurement claim method does not match its verification requirement")
        if method not in DETERMINISTIC_MEASUREMENT_METHODS:
            continue
        target_path = claim.get("target_path")
        if target_path not in requirement["target_paths"]:
            raise ValueError("measurement claim targets the wrong canonical path")
        if (metric_id, target_path, source_id) in existing:
            raise ValueError("deterministic measurement comparator cannot be bypassed by a supplied verdict")
        visible = claim.get("visible_seconds")
        total = claim.get("total_seconds")
        duty_cycle = claim.get("duty_cycle")
        if (
            isinstance(visible, bool)
            or isinstance(total, bool)
            or isinstance(duty_cycle, bool)
            or not isinstance(visible, (int, float))
            or not isinstance(total, (int, float))
            or not isinstance(duty_cycle, (int, float))
            or total <= 0
            or visible < 0
            or visible > total
            or duty_cycle < 0
            or duty_cycle > 1
            or abs(float(duty_cycle) - float(visible) / float(total)) > 1e-9
        ):
            raise ValueError("product visibility measurement is internally inconsistent")
        interval = record["interval"]
        if float(total) > interval["end_s"] - interval["start_s"] + 1e-9:
            raise ValueError("product visibility measurement exceeds its source interval")
        control = controls_by_path.get(target_path)
        if control is None or not isinstance(control["value"], bool):
            raise ValueError("product visibility comparator requires one boolean canonical control")
        expected = control["value"]
        passed = duty_cycle > 0 if expected else duty_cycle == 0
        assertion = make_assertion(
            metric_id=metric_id,
            target_path=target_path,
            source_ref=source_id,
            verdict="pass" if passed else "fail",
            observed={
                "visible_seconds": visible,
                "total_seconds": total,
                "duty_cycle": duty_cycle,
            },
            interval=interval,
            deviation=(
                None
                if passed
                else {
                    "code": "product_not_visible_in_measured_interval",
                    "expected": expected,
                    "observed_duty_cycle": duty_cycle,
                }
            ),
            limitations=[
                "Visibility duration is measured; product identity still depends on the detector input contract."
            ],
        )
        assertion["lane"] = "measurement"
        assertion["origin"] = "deterministic_comparator"
        derived.append(assertion)
    derived.extend(
        _derive_hand_path_curvature_assertions(
            sources=sources,
            assertions=assertions,
            requirements=requirements,
            controls_by_path=controls_by_path,
        )
    )
    return sorted(derived, key=lambda row: row["assertion_id"])


def _finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _average_path_curvature(claim: dict[str, Any]) -> dict[str, Any]:
    """Measure total absolute 2D turning divided by observed path length."""
    expected = {
        "type",
        "actor",
        "joint",
        "positions",
        "units",
        "coordinate_system",
        "camera_motion_separated",
        "quality_flags",
        "limitations",
    }
    if set(claim) != expected:
        raise ValueError("hand-path measurement claim has an invalid field set")
    if claim["type"] != "joint_track_2d" or claim["joint"] not in {
        "left_wrist",
        "right_wrist",
    }:
        raise ValueError("hand-path curvature requires one wrist joint track")
    if not isinstance(claim["actor"], str) or not claim["actor"]:
        raise ValueError("hand-path curvature requires one actor identity")
    if (
        claim["units"] != "normalized_image_xy"
        or claim["coordinate_system"] != "image_topleft_x_right_y_down"
        or claim["camera_motion_separated"] is not False
    ):
        raise ValueError("hand-path curvature requires the declared 2D image-space contract")
    if (
        not isinstance(claim["quality_flags"], list)
        or "camera_motion_not_separated" not in claim["quality_flags"]
        or any(not isinstance(row, str) or not row for row in claim["quality_flags"])
        or not isinstance(claim["limitations"], list)
        or any(not isinstance(row, str) or not row for row in claim["limitations"])
    ):
        raise ValueError("hand-path curvature requires explicit quality and limitation labels")
    positions = claim["positions"]
    if not isinstance(positions, list) or len(positions) < 3:
        raise ValueError("hand-path curvature requires at least three samples")
    points: list[tuple[float, float, float]] = []
    previous_time = -math.inf
    for sample in positions:
        if not isinstance(sample, dict) or set(sample) != {
            "t",
            "x",
            "y",
            "visibility",
        }:
            raise ValueError("hand-path curvature sample has an invalid field set")
        if not all(
            _finite_number(sample[key]) for key in ("t", "x", "y", "visibility")
        ):
            raise ValueError("hand-path curvature sample must contain finite numbers")
        timestamp = float(sample["t"])
        visibility = float(sample["visibility"])
        if timestamp <= previous_time or not 0 <= visibility <= 1:
            raise ValueError(
                "hand-path curvature samples require increasing time and valid visibility"
            )
        points.append((timestamp, float(sample["x"]), float(sample["y"])))
        previous_time = timestamp
    segments: list[tuple[float, float, float]] = []
    for left, right in zip(points, points[1:]):
        dx = right[1] - left[1]
        dy = right[2] - left[2]
        length = math.hypot(dx, dy)
        if length > 1e-12:
            segments.append((dx, dy, length))
    if len(segments) < 2:
        raise ValueError("hand-path curvature requires at least two nonzero segments")
    total_turn = 0.0
    for left, right in zip(segments, segments[1:]):
        cosine = (left[0] * right[0] + left[1] * right[1]) / (
            left[2] * right[2]
        )
        total_turn += abs(math.acos(max(-1.0, min(1.0, cosine))))
    path_length = sum(row[2] for row in segments)
    return {
        "actor": claim["actor"],
        "joint": claim["joint"],
        "average_path_curvature": round(total_turn / path_length, 9),
        "path_length": round(path_length, 9),
        "total_turn_radians": round(total_turn, 9),
        "sample_count": len(points),
        "start_s": points[0][0],
        "end_s": points[-1][0],
        "units": "radians_per_normalized_image_unit",
    }


def _derive_hand_path_curvature_assertions(
    *,
    sources: dict[str, dict[str, Any]],
    assertions: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    controls_by_path: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    matches = [
        row
        for row in requirements
        if row["method"] == "measured_average_hand_path_curvature"
    ]
    if not matches:
        return []
    if len(matches) != 1 or len(matches[0]["target_paths"]) != 1:
        raise ValueError("hand-path curvature comparator requires one declared target")
    requirement = matches[0]
    target_path = requirement["target_paths"][0]
    control = controls_by_path.get(target_path)
    expected_control = {
        "projection_plane": "largest_displacement_2d",
        "scope": "per_hand",
        "signal": "average_path_curvature",
    }
    if control is None or control["value"] != expected_control:
        raise ValueError(
            "hand-path curvature comparator does not support this canonical control"
        )
    tracks: dict[str, dict[str, tuple[str, dict[str, Any], dict[str, Any]]]] = {}
    actors_with_tracks: set[str] = set()
    for source_id, source in sorted(sources.items()):
        if source["lane"] != "measurement":
            continue
        claim = source["record"]["claim"]
        if claim.get("type") != "joint_track_2d":
            continue
        actor = claim.get("actor")
        if isinstance(actor, str) and actor:
            actors_with_tracks.add(actor)
        joint = claim.get("joint")
        if joint not in {"left_wrist", "right_wrist"}:
            continue
        observed = _average_path_curvature(claim)
        interval = source["record"]["interval"]
        if (
            abs(observed["start_s"] - float(interval["start_s"])) > 1e-9
            or abs(observed["end_s"] - float(interval["end_s"])) > 1e-9
        ):
            raise ValueError("hand-path samples do not match their source interval")
        by_joint = tracks.setdefault(actor, {})
        if joint in by_joint:
            raise ValueError(f"duplicate hand-path track for {actor}:{joint}")
        by_joint[joint] = (source_id, source["record"], observed)
    if not tracks:
        return []
    required_joints = {"left_wrist", "right_wrist"}
    if any(
        set(tracks.get(actor, {})) != required_joints
        for actor in actors_with_tracks
    ):
        return []
    existing = {
        (row["metric_id"], row["target_path"], row["source_ref"])
        for row in assertions
    }
    output: list[dict[str, Any]] = []
    for actor in sorted(tracks):
        for joint in sorted(required_joints):
            source_id, record, observed = tracks[actor][joint]
            if (requirement["metric_id"], target_path, source_id) in existing:
                raise ValueError(
                    "deterministic measurement comparator cannot be bypassed by a supplied verdict"
                )
            assertion = make_assertion(
                metric_id=requirement["metric_id"],
                target_path=target_path,
                source_ref=source_id,
                verdict="pass",
                observed=observed,
                interval=record["interval"],
                limitations=[
                    "Curvature is measured in normalized 2D image space; depth-axis motion is unavailable.",
                    "Camera motion is not separated from subject motion.",
                    "Verification covers only actors present in the supplied normalized measurement sources.",
                ],
            )
            assertion["lane"] = "measurement"
            assertion["origin"] = "deterministic_comparator"
            output.append(assertion)
    return sorted(output, key=lambda row: row["assertion_id"])


def _aspect_ratio(width: int, height: int) -> str:
    divisor = math.gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def _resolution(width: int, height: int) -> str:
    return f"{min(width, height)}p"


def _artifact_checks(
    plan: dict[str, Any], artifact: dict[str, Any], metadata: dict[str, Any]
) -> list[dict[str, Any]]:
    observed = {
        "artifact_hash": artifact["sha256"],
        "duration": metadata["duration_s"],
        "aspect_ratio": _aspect_ratio(metadata["width"], metadata["height"]),
        "resolution": _resolution(metadata["width"], metadata["height"]),
        "frame_rate": metadata["frame_rate"],
    }
    values: list[dict[str, Any]] = []
    for check in sorted(plan["provider_artifact_checks"], key=lambda row: row["check_id"]):
        check_id = check["check_id"]
        value = observed[check_id]
        if check["comparator"] == "sha256_present":
            passed = isinstance(value, str) and value == artifact["sha256"]
        elif isinstance(value, (int, float)) and isinstance(
            check["expected"], (int, float)
        ):
            tolerance = float(check["tolerance"] or 0)
            passed = abs(float(value) - float(check["expected"])) <= tolerance
        else:
            passed = value == check["expected"]
        deviation = None
        if not passed:
            deviation = {
                "code": "artifact_metadata_mismatch",
                "expected": check["expected"],
                "observed": value,
            }
        values.append(
            {
                "check_id": check_id,
                "status": "pass" if passed else "fail",
                "expected": check["expected"],
                "observed": value,
                "deviation": deviation,
                "evidence_refs": [metadata["probe_hash"]],
            }
        )
    return values


def _required_lane(observability: str) -> str:
    return "measurement" if observability == "measured" else observability


def _target_result(
    requirement: dict[str, Any],
    target_path: str,
    assertions: list[dict[str, Any]],
    controls_by_path: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    relevant = [
        row
        for row in assertions
        if row["metric_id"] == requirement["metric_id"]
        and row["target_path"] == target_path
    ]
    lane = _required_lane(requirement["observability"])
    admissible = [row for row in relevant if row["lane"] == lane]
    supplemental = [row for row in relevant if row["lane"] != lane]
    controls = [
        {"control_id": row["control_id"], "path": row["path"], "value": row["value"]}
        for row in controls_by_path.get(target_path, [])
    ]
    limitations = sorted(
        {
            limitation
            for row in relevant
            for limitation in row["limitations"]
        }
    )
    verdicts = {row["verdict"] for row in relevant}
    if not controls:
        status = "unobservable"
        limitations.append("target_path_has_no_canonical_control")
    elif verdicts == {"pass", "fail"}:
        status = "conflict"
        limitations.append("evidence_lanes_disagree")
    elif not admissible:
        status = "review_required" if lane == "human_review" else "unobservable"
        limitations.append(f"required_{lane}_evidence_missing")
    elif {row["verdict"] for row in admissible} == {"pass", "fail"}:
        status = "conflict"
        limitations.append("required_lane_evidence_disagrees")
    elif any(row["verdict"] == "fail" for row in admissible):
        status = "fail"
    else:
        status = "pass"
    locations = sorted(
        {
            canonical_json_bytes(row["interval"]).decode("utf-8").strip()
            for row in relevant
            if row["interval"] is not None
        }
    )
    deviations = [
        copy.deepcopy(row["deviation"])
        for row in relevant
        if row["verdict"] == "fail" and row["deviation"] is not None
    ]
    if status == "fail" and not deviations:
        deviations = [
            {
                "code": "canonical_expectation_not_observed",
                "expected": [row["value"] for row in controls],
                "observed": [row["observed"] for row in admissible],
            }
        ]
    return {
        "target_path": target_path,
        "status": status,
        "required_lane": lane,
        "expected_controls": controls,
        "evidence_refs": sorted(row["assertion_id"] for row in admissible),
        "supplemental_evidence_refs": sorted(
            row["assertion_id"] for row in supplemental
        ),
        "locations": [json.loads(row) for row in locations],
        "deviations": deviations,
        "limitations": sorted(set(limitations)),
    }


def _control_checks(
    requirements: list[dict[str, Any]],
    assertions: list[dict[str, Any]],
    score: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    controls_by_path: dict[str, list[dict[str, Any]]] = {}
    for control in score["provider_neutral_controls"]:
        controls_by_path.setdefault(control["path"], []).append(control)
    checks: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for requirement in sorted(requirements, key=lambda row: row["metric_id"]):
        targets = [
            _target_result(requirement, path, assertions, controls_by_path)
            for path in sorted(requirement["target_paths"])
        ]
        status = max(
            (row["status"] for row in targets),
            key=lambda value: STATUS_PRECEDENCE[value],
        )
        source_ref = requirement.get("source_profile") or requirement["source_translation"]
        checks.append(
            {
                "metric_id": requirement["metric_id"],
                "method": requirement["method"],
                "observability": requirement["observability"],
                "status": status,
                "source_ref": source_ref,
                "targets": targets,
            }
        )
        for target in targets:
            if target["status"] != "conflict":
                continue
            refs = sorted(
                [*target["evidence_refs"], *target["supplemental_evidence_refs"]]
            )
            source_assertions = [
                row for row in assertions if row["assertion_id"] in refs
            ]
            core = {
                "metric_id": requirement["metric_id"],
                "target_path": target["target_path"],
                "lanes": sorted({row["lane"] for row in source_assertions}),
                "evidence_refs": refs,
                "resolution": "preserved_for_review",
            }
            digest = hashlib.sha256(canonical_json_bytes(core)).hexdigest()[:24]
            conflicts.append(
                {"conflict_id": "verification_conflict_" + digest, **core}
            )
    return checks, sorted(conflicts, key=lambda row: row["conflict_id"])


def _status_counts(values: list[str]) -> dict[str, int]:
    return {
        key: sum(value == key for value in values)
        for key in ("pass", "fail", "conflict", "unobservable", "review_required")
    }


def _repair_plan(
    *,
    artifact_id: str,
    artifact_checks: list[dict[str, Any]],
    control_checks: list[dict[str, Any]],
    controls: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers = [
        {"code": "artifact_check_failed", "ref": row["check_id"]}
        for row in artifact_checks
        if row["status"] == "fail"
    ]
    failed_targets: list[tuple[str, dict[str, Any]]] = []
    for check in control_checks:
        for target in check["targets"]:
            if target["status"] == "fail":
                if not target["expected_controls"]:
                    blockers.append(
                        {"code": "canonical_control_missing", "ref": target["target_path"]}
                    )
                else:
                    failed_targets.append((check["metric_id"], target))
            elif target["status"] in {"conflict", "unobservable", "review_required"}:
                blockers.append(
                    {"code": target["status"], "ref": f"{check['metric_id']}:{target['target_path']}"}
                )
    all_control_ids = sorted(row["control_id"] for row in controls)
    if blockers:
        return {
            "status": "blocked",
            "actions": [],
            "preserve_control_ids": all_control_ids,
            "blocked_by": sorted(blockers, key=lambda row: (row["code"], row["ref"])),
        }
    grouped: dict[str, dict[str, Any]] = {}
    for metric_id, target in failed_targets:
        for control in target["expected_controls"]:
            row = grouped.setdefault(
                control["control_id"],
                {
                    "metric_ids": set(),
                    "target_path": control["path"],
                    "control_id": control["control_id"],
                    "canonical_value": control["value"],
                    "evidence_refs": set(),
                    "locations": [],
                },
            )
            row["metric_ids"].add(metric_id)
            row["evidence_refs"].update(target["evidence_refs"])
            row["locations"].extend(target["locations"])
    actions: list[dict[str, Any]] = []
    for control_id in sorted(grouped):
        row = grouped[control_id]
        locations = row.pop("locations")
        if locations:
            interval = {
                "start_s": min(item["start_s"] for item in locations),
                "end_s": max(item["end_s"] for item in locations),
            }
            scope = {"kind": "interval", "artifact_id": artifact_id, "interval": interval}
        else:
            scope = {"kind": "artifact", "artifact_id": artifact_id, "interval": None}
        core = {
            "action": "reassert_existing_control",
            "metric_ids": sorted(row["metric_ids"]),
            "target_path": row["target_path"],
            "control_id": control_id,
            "canonical_value": row["canonical_value"],
            "scope": scope,
            "evidence_refs": sorted(row["evidence_refs"]),
            "reason": "Observed failure is bounded to this existing canonical control and scope.",
        }
        digest = hashlib.sha256(canonical_json_bytes(core)).hexdigest()[:24]
        actions.append({"action_id": "repair_action_" + digest, **core})
    changed = {row["control_id"] for row in actions}
    return {
        "status": "proposed" if actions else "no_change",
        "actions": actions,
        "preserve_control_ids": sorted(set(all_control_ids) - changed),
        "blocked_by": [],
    }


def _validated_render_identity(
    build_dir: Path,
    render_result_path: Path,
    artifact_id: str,
    root: Path,
) -> tuple[dict[str, Any], Path, dict[str, Any], dict[str, Any]]:
    build = load_validated_build_directory(build_dir, root)
    result_path = render_result_path.expanduser().resolve()
    render_result = _load_object(result_path, "render result")
    validate_runtime_instance("render_result", render_result, root)
    if (
        render_result["build_id"] != build["manifest"]["build_id"]
        or render_result["build_hash"] != build["manifest"]["build_hash"]
    ):
        raise ValueError("render result does not match the validated build")
    artifacts = [
        row for row in render_result["artifacts"] if row["artifact_id"] == artifact_id
    ]
    if len(artifacts) != 1:
        raise ValueError("render result does not contain exactly one selected artifact")
    return build, result_path, render_result, artifacts[0]


def _validated_artifact_path(
    result_path: Path, artifact: dict[str, Any]
) -> Path:
    job_root = result_path.parent
    media_candidate = job_root / artifact["relative_path"]
    if media_candidate.is_symlink():
        raise ValueError("render artifact path is unsafe or missing")
    media_path = media_candidate.resolve()
    if job_root not in media_path.parents or not media_path.is_file():
        raise ValueError("render artifact path is unsafe or missing")
    media_bytes = media_path.read_bytes()
    if (
        len(media_bytes) != artifact["size_bytes"]
        or sha256_bytes(media_bytes) != artifact["sha256"]
    ):
        raise ValueError("render artifact bytes do not match the runtime result")
    return media_path


def _joint_track_points(claim: dict[str, Any]) -> list[tuple[float, float, float]]:
    expected = {
        "type",
        "actor",
        "joint",
        "positions",
        "units",
        "coordinate_system",
        "camera_motion_separated",
        "quality_flags",
        "limitations",
    }
    if set(claim) != expected or claim["type"] != "joint_track_2d":
        raise ValueError("round-trip comparison requires one closed 2D joint-track claim")
    if not isinstance(claim["actor"], str) or not claim["actor"]:
        raise ValueError("round-trip joint track has no actor identity")
    if not isinstance(claim["joint"], str) or not claim["joint"]:
        raise ValueError("round-trip joint track has no joint identity")
    if (
        claim["units"] != "normalized_image_xy"
        or claim["coordinate_system"] != "image_topleft_x_right_y_down"
        or claim["camera_motion_separated"] is not False
    ):
        raise ValueError("round-trip comparison requires the declared 2D image-space contract")
    if (
        not isinstance(claim["quality_flags"], list)
        or "camera_motion_not_separated" not in claim["quality_flags"]
        or any(not isinstance(row, str) or not row for row in claim["quality_flags"])
        or not isinstance(claim["limitations"], list)
        or any(not isinstance(row, str) or not row for row in claim["limitations"])
    ):
        raise ValueError("round-trip joint track lacks required quality and limitation labels")
    positions = claim["positions"]
    if not isinstance(positions, list) or len(positions) < 2:
        raise ValueError("round-trip joint track requires at least two samples")
    points: list[tuple[float, float, float]] = []
    previous_time = -math.inf
    for sample in positions:
        if not isinstance(sample, dict) or set(sample) != {
            "t",
            "x",
            "y",
            "visibility",
        }:
            raise ValueError("round-trip joint-track sample has an invalid field set")
        if not all(
            _finite_number(sample[key]) for key in ("t", "x", "y", "visibility")
        ):
            raise ValueError("round-trip joint-track sample must contain finite numbers")
        timestamp = float(sample["t"])
        visibility = float(sample["visibility"])
        if timestamp < 0 or timestamp <= previous_time or not 0 <= visibility <= 1:
            raise ValueError(
                "round-trip joint-track samples require increasing nonnegative time and valid visibility"
            )
        points.append((timestamp, float(sample["x"]), float(sample["y"])))
        previous_time = timestamp
    return points


def _measurement_tracks(
    batch: dict[str, Any], root: Path
) -> dict[tuple[str, str], tuple[dict[str, Any], list[tuple[float, float, float]]]]:
    validate_measurement_batch(batch, root)
    if batch["summary"]["observation_count"] != len(batch["observations"]):
        raise ValueError("measurement batch summary does not match its observations")
    parameter_hash = sha256_value(batch["parameters"])
    model_sha256 = batch["parameters"].get("model_sha256")
    if not isinstance(model_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", model_sha256):
        raise ValueError("measurement batch has no exact detector model hash")
    tracks: dict[
        tuple[str, str], tuple[dict[str, Any], list[tuple[float, float, float]]]
    ] = {}
    for observation in batch["observations"]:
        if (
            observation["measurement_job_id"] != batch["job_id"]
            or observation["source_asset_ref"] != batch["source"]["asset_ref"]
            or observation["source_sha256"] != batch["source"]["sha256"]
            or observation["tool"] != batch["tool"]
            or observation["model_version"] != batch["model_version"]
            or observation["model_sha256"] != model_sha256
            or observation["parameters_hash"] != parameter_hash
            or observation["evidence_class"] != "detected"
        ):
            raise ValueError("measurement observation is detached from its batch lineage")
        points = _joint_track_points(observation["claim"])
        interval = observation["interval"]
        if (
            abs(points[0][0] - float(interval["start_s"])) > 1e-9
            or abs(points[-1][0] - float(interval["end_s"])) > 1e-9
            or interval["start_s"] < batch["authorized_interval"]["start_s"]
            or interval["end_s"] > batch["authorized_interval"]["end_s"]
        ):
            raise ValueError("measurement track interval is detached from its samples or batch")
        key = (observation["claim"]["actor"], observation["claim"]["joint"])
        if key in tracks:
            raise ValueError(f"duplicate measurement track: {key[0]}:{key[1]}")
        tracks[key] = (observation, points)
    return tracks


def _measurement_identity(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "batch_id": batch["batch_id"],
        "job_id": batch["job_id"],
        "source_id": batch["source"]["source_id"],
        "asset_ref": batch["source"]["asset_ref"],
        "source_sha256": batch["source"]["sha256"],
        "evidence_class": "detected",
        "tool": batch["tool"],
        "model_version": batch["model_version"],
        "model_sha256": batch["parameters"]["model_sha256"],
    }


def _resample_track(
    points: list[tuple[float, float, float]], phase_samples: int
) -> list[tuple[float, float]]:
    start = points[0][0]
    duration = points[-1][0] - start
    if duration <= 0:
        raise ValueError("round-trip joint track has no positive duration")
    phases = [(row[0] - start) / duration for row in points]
    output: list[tuple[float, float]] = []
    right = 1
    for index in range(phase_samples):
        phase = index / (phase_samples - 1)
        while right < len(phases) - 1 and phases[right] < phase:
            right += 1
        left = right - 1
        span = phases[right] - phases[left]
        weight = 0.0 if span <= 0 else (phase - phases[left]) / span
        x = points[left][1] + (points[right][1] - points[left][1]) * weight
        y = points[left][2] + (points[right][2] - points[left][2]) * weight
        output.append((x, y))
    return output


def _path_length(points: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(right[0] - left[0], right[1] - left[1])
        for left, right in zip(points, points[1:])
    )


def _round_trip_metrics(
    reference: list[tuple[float, float, float]],
    generated: list[tuple[float, float, float]],
    phase_samples: int,
) -> dict[str, Any]:
    source_points = _resample_track(reference, phase_samples)
    generated_points = _resample_track(generated, phase_samples)
    absolute_squared = [
        (right[0] - left[0]) ** 2 + (right[1] - left[1]) ** 2
        for left, right in zip(source_points, generated_points)
    ]
    source_displacements = [
        (point[0] - source_points[0][0], point[1] - source_points[0][1])
        for point in source_points
    ]
    generated_displacements = [
        (point[0] - generated_points[0][0], point[1] - generated_points[0][1])
        for point in generated_points
    ]
    aligned_squared = [
        (right[0] - left[0]) ** 2 + (right[1] - left[1]) ** 2
        for left, right in zip(source_displacements, generated_displacements)
    ]
    dot = sum(
        left[0] * right[0] + left[1] * right[1]
        for left, right in zip(source_displacements, generated_displacements)
    )
    source_norm = math.sqrt(
        sum(point[0] ** 2 + point[1] ** 2 for point in source_displacements)
    )
    generated_norm = math.sqrt(
        sum(point[0] ** 2 + point[1] ** 2 for point in generated_displacements)
    )
    if source_norm <= 1e-12 and generated_norm <= 1e-12:
        similarity = 1.0
    elif source_norm <= 1e-12 or generated_norm <= 1e-12:
        similarity = 0.0
    else:
        similarity = max(-1.0, min(1.0, dot / (source_norm * generated_norm)))
    source_length = _path_length(source_points)
    generated_length = _path_length(generated_points)
    if source_length <= 1e-12 and generated_length <= 1e-12:
        length_ratio: float | None = 1.0
        length_error: float | None = 0.0
    elif source_length <= 1e-12:
        length_ratio = None
        length_error = None
    else:
        length_ratio = generated_length / source_length
        length_error = abs(length_ratio - 1.0)
    source_duration = reference[-1][0] - reference[0][0]
    generated_duration = generated[-1][0] - generated[0][0]
    return {
        "absolute_rmse": round(math.sqrt(sum(absolute_squared) / phase_samples), 9),
        "translation_aligned_rmse": round(
            math.sqrt(sum(aligned_squared) / phase_samples), 9
        ),
        "trajectory_cosine_similarity": round(similarity, 9),
        "reference_path_length": round(source_length, 9),
        "generated_path_length": round(generated_length, 9),
        "path_length_ratio": None if length_ratio is None else round(length_ratio, 9),
        "path_length_ratio_error": (
            None if length_error is None else round(length_error, 9)
        ),
        "duration_error_ratio": round(
            abs(generated_duration / source_duration - 1.0), 9
        ),
        "phase_samples": phase_samples,
    }


def _round_trip_checks(
    metrics: dict[str, Any], thresholds: dict[str, float]
) -> list[dict[str, Any]]:
    definitions = (
        (
            "trajectory_cosine_similarity",
            "minimum_trajectory_cosine_similarity",
            "greater_than_or_equal",
        ),
        (
            "translation_aligned_rmse",
            "maximum_translation_aligned_rmse",
            "less_than_or_equal",
        ),
        (
            "duration_error_ratio",
            "maximum_duration_error_ratio",
            "less_than_or_equal",
        ),
        (
            "path_length_ratio_error",
            "maximum_path_length_ratio_error",
            "less_than_or_equal",
        ),
    )
    output = []
    for metric, threshold, comparator in definitions:
        observed = metrics[metric]
        expected = float(thresholds[threshold])
        passed = observed is not None and (
            float(observed) >= expected
            if comparator == "greater_than_or_equal"
            else float(observed) <= expected
        )
        output.append(
            {
                "check_id": metric,
                "status": "pass" if passed else "fail",
                "comparator": comparator,
                "expected": expected,
                "observed": observed,
            }
        )
    return output


def compare_reference_round_trip(
    build_dir: Path,
    render_result_path: Path,
    artifact_id: str,
    reference_batch: dict[str, Any],
    generated_batch: dict[str, Any],
    *,
    actor_mapping: dict[str, str],
    joints: list[str],
    thresholds: dict[str, float],
    phase_samples: int = 21,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Compare source and generated detected tracks without claiming motion ground truth."""
    build, result_path, render_result, artifact = _validated_render_identity(
        build_dir, render_result_path, artifact_id, root
    )
    _validated_artifact_path(result_path, artifact)
    reference_tracks = _measurement_tracks(reference_batch, root)
    generated_tracks = _measurement_tracks(generated_batch, root)
    if generated_batch["source"]["sha256"] != artifact["sha256"].removeprefix(
        "sha256:"
    ):
        raise ValueError("generated measurement batch refers to different render bytes")
    if (
        reference_batch["tool"] != generated_batch["tool"]
        or reference_batch["model_version"] != generated_batch["model_version"]
        or reference_batch["parameters"] != generated_batch["parameters"]
    ):
        raise ValueError("round-trip batches require identical detector settings")
    if not isinstance(actor_mapping, dict) or not actor_mapping:
        raise ValueError("round-trip comparison requires an explicit actor mapping")
    if any(
        not isinstance(source, str)
        or not re.fullmatch(r"actor_[A-Z]+", source)
        or not isinstance(generated, str)
        or not re.fullmatch(r"actor_[A-Z]+", generated)
        for source, generated in actor_mapping.items()
    ) or len(set(actor_mapping.values())) != len(actor_mapping):
        raise ValueError("round-trip actor mapping must be one-to-one and well formed")
    if not set(actor_mapping) <= set(reference_batch["summary"]["actors"]):
        raise ValueError("round-trip actor mapping names an unknown reference actor")
    if not set(actor_mapping.values()) <= set(generated_batch["summary"]["actors"]):
        raise ValueError("round-trip actor mapping names an unknown generated actor")
    if (
        not isinstance(joints, list)
        or not joints
        or len(joints) != len(set(joints))
        or any(not isinstance(joint, str) or not joint for joint in joints)
    ):
        raise ValueError("round-trip joints must be one nonempty unique list")
    if not isinstance(phase_samples, int) or isinstance(phase_samples, bool) or not 3 <= phase_samples <= 1001:
        raise ValueError("round-trip phase sample count must be between 3 and 1001")
    expected_thresholds = {
        "minimum_trajectory_cosine_similarity",
        "maximum_translation_aligned_rmse",
        "maximum_duration_error_ratio",
        "maximum_path_length_ratio_error",
    }
    if set(thresholds) != expected_thresholds or any(
        not _finite_number(value) for value in thresholds.values()
    ):
        raise ValueError("round-trip thresholds have an invalid field set or value")
    if not -1 <= float(thresholds["minimum_trajectory_cosine_similarity"]) <= 1 or any(
        float(thresholds[key]) < 0
        for key in expected_thresholds
        if key != "minimum_trajectory_cosine_similarity"
    ):
        raise ValueError("round-trip thresholds are outside their supported ranges")

    tracks: list[dict[str, Any]] = []
    for source_actor, generated_actor in sorted(actor_mapping.items()):
        for joint in sorted(joints):
            source = reference_tracks.get((source_actor, joint))
            generated = generated_tracks.get((generated_actor, joint))
            if source is None or generated is None:
                missing = []
                if source is None:
                    missing.append("reference")
                if generated is None:
                    missing.append("generated")
                tracks.append(
                    {
                        "source_actor": source_actor,
                        "generated_actor": generated_actor,
                        "joint": joint,
                        "status": "unobservable",
                        "reason": "missing_" + "_and_".join(missing) + "_track",
                        "source_observation_id": None if source is None else source[0]["id"],
                        "generated_observation_id": (
                            None if generated is None else generated[0]["id"]
                        ),
                        "metrics": None,
                        "checks": [],
                    }
                )
                continue
            metrics = _round_trip_metrics(source[1], generated[1], phase_samples)
            checks = _round_trip_checks(metrics, thresholds)
            tracks.append(
                {
                    "source_actor": source_actor,
                    "generated_actor": generated_actor,
                    "joint": joint,
                    "status": (
                        "pass"
                        if all(row["status"] == "pass" for row in checks)
                        else "fail"
                    ),
                    "reason": None,
                    "source_observation_id": source[0]["id"],
                    "generated_observation_id": generated[0]["id"],
                    "metrics": metrics,
                    "checks": checks,
                }
            )
    passed = sum(row["status"] == "pass" for row in tracks)
    failed = sum(row["status"] == "fail" for row in tracks)
    unobservable = sum(row["status"] == "unobservable" for row in tracks)
    possible_swaps = (
        reference_batch["summary"]["possible_swap_frames"]
        + generated_batch["summary"]["possible_swap_frames"]
    )
    if unobservable or possible_swaps:
        overall_status = "inconclusive"
    elif failed:
        overall_status = "fail"
    else:
        overall_status = "pass"
    limitations = [
        "Both inputs are detector-derived evidence, not motion-capture ground truth.",
        "Comparison is phase-aligned in normalized 2D image space and cannot evaluate depth-axis motion.",
        "Camera motion is not separated from subject motion, so framing changes can affect the diagnostics.",
        "Actor correspondence is explicit caller-reviewed input and is not inferred from appearance.",
        "Thresholds are declared qualification criteria, not learned claims of creative superiority.",
    ]
    if possible_swaps:
        limitations.append(
            "At least one detector batch reports possible actor swaps, so the result is inconclusive."
        )
    core = {
        "schema": REFERENCE_ROUND_TRIP_SCHEMA,
        "policy": REFERENCE_ROUND_TRIP_POLICY,
        "render": {
            "build_id": build["manifest"]["build_id"],
            "build_hash": build["manifest"]["build_hash"],
            "score_id": build["manifest"]["score_id"],
            "render_job_id": render_result["job_id"],
            "artifact_id": artifact_id,
            "artifact_sha256": artifact["sha256"],
        },
        "reference": _measurement_identity(reference_batch),
        "generated": _measurement_identity(generated_batch),
        "comparison": {
            "actor_mapping": dict(sorted(actor_mapping.items())),
            "joints": sorted(joints),
            "phase_samples": phase_samples,
            "thresholds": {
                key: float(thresholds[key]) for key in sorted(thresholds)
            },
            "detector_parameters_hash": sha256_value(reference_batch["parameters"]),
        },
        "summary": {
            "overall_status": overall_status,
            "tracks_requested": len(tracks),
            "tracks_passed": passed,
            "tracks_failed": failed,
            "tracks_unobservable": unobservable,
            "reference_possible_swap_frames": reference_batch["summary"][
                "possible_swap_frames"
            ],
            "generated_possible_swap_frames": generated_batch["summary"][
                "possible_swap_frames"
            ],
        },
        "tracks": tracks,
        "limitations": sorted(limitations),
    }
    report = {
        **core,
        "report_id": "reference_round_trip_"
        + hashlib.sha256(canonical_json_bytes(core)).hexdigest()[:24],
    }
    _validate("reference_round_trip_report", report, root)
    return report


def _path_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_bound_json(artifact: dict[str, Any], label: str) -> dict[str, Any]:
    path = Path(artifact["path"]).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {path}")
    if _path_sha256(path) != artifact["sha256"]:
        raise ValueError(f"{label} hash does not match its declared bytes")
    return _load_object(path, label)


def _detect_scene_cuts(path: Path, threshold: float) -> list[float]:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "info",
            "-i",
            str(path),
            "-vf",
            f"select='gt(scene,{threshold:.9f})',showinfo",
            "-an",
            "-f",
            "null",
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return [
        round(float(value), 9)
        for value in re.findall(r"pts_time:([0-9]+(?:\.[0-9]+)?)", completed.stderr)
    ]


def _asr_metrics(value: dict[str, Any], minimum_pause_s: float) -> dict[str, Any]:
    words = []
    for segment in value.get("segments", []):
        for word in segment.get("words", []):
            if not _finite_number(word.get("start")) or not _finite_number(word.get("end")):
                raise ValueError("ASR word timestamps must be finite numbers")
            start = float(word["start"])
            end = float(word["end"])
            if start < 0 or end < start:
                raise ValueError("ASR word timestamps must be non-negative and ordered")
            words.append((start, end))
    words.sort()
    if not words:
        raise ValueError("ASR artifact contains no word timestamps")
    if any(right[0] < left[0] for left, right in zip(words, words[1:])):
        raise ValueError("ASR word timestamps are not monotonic")
    pauses = [
        max(0.0, right[0] - left[1])
        for left, right in zip(words, words[1:])
        if right[0] - left[1] >= minimum_pause_s
    ]
    span = words[-1][1] - words[0][0]
    if span <= 0:
        raise ValueError("ASR speech span must be positive")
    return {
        "word_count": len(words),
        "speech_span_s": round(span, 9),
        "words_per_minute": round(len(words) * 60.0 / span, 4),
        "pauses_at_or_above_threshold": len(pauses),
        "pause_total_s": round(sum(pauses), 9),
        "longest_pause_s": round(max(pauses, default=0.0), 9),
    }


def _track_speed(
    points: list[tuple[float, float, float]], max_gap_s: float, max_step: float
) -> dict[str, Any]:
    speeds = []
    excluded_gap = 0
    excluded_step = 0
    for left, right in zip(points, points[1:]):
        delta_t = right[0] - left[0]
        distance = math.hypot(right[1] - left[1], right[2] - left[2])
        if delta_t <= 0 or delta_t > max_gap_s:
            excluded_gap += 1
            continue
        if distance > max_step:
            excluded_step += 1
            continue
        speeds.append(distance / delta_t)
    return {
        "median_normalized_speed_per_s": (
            None if not speeds else round(statistics.median(speeds), 6)
        ),
        "included_steps": len(speeds),
        "excluded_gap_steps": excluded_gap,
        "excluded_large_steps": excluded_step,
    }


def _pose_speed_rows(
    reference_batch: dict[str, Any],
    candidate_batch: dict[str, Any],
    *,
    actor_mapping: dict[str, str],
    joints: list[str],
    max_gap_s: float,
    max_step: float,
    minimum_ratio: float,
    root: Path,
) -> dict[str, Any]:
    reference_tracks = _measurement_tracks(reference_batch, root)
    candidate_tracks = _measurement_tracks(candidate_batch, root)
    if (
        reference_batch["tool"] != candidate_batch["tool"]
        or reference_batch["model_version"] != candidate_batch["model_version"]
        or reference_batch["parameters"] != candidate_batch["parameters"]
    ):
        raise ValueError("side-by-side pose batches require identical detector settings")
    if len(set(actor_mapping.values())) != len(actor_mapping):
        raise ValueError("side-by-side actor mapping must be one-to-one")
    if not set(actor_mapping) <= set(reference_batch["summary"]["actors"]):
        raise ValueError("side-by-side mapping names an unknown reference actor")
    if not set(actor_mapping.values()) <= set(candidate_batch["summary"]["actors"]):
        raise ValueError("side-by-side mapping names an unknown candidate actor")
    rows = []
    for reference_actor, candidate_actor in sorted(actor_mapping.items()):
        for joint in sorted(joints):
            reference_track = reference_tracks.get((reference_actor, joint))
            candidate_track = candidate_tracks.get((candidate_actor, joint))
            if reference_track is None or candidate_track is None:
                rows.append(
                    {
                        "reference_actor": reference_actor,
                        "candidate_actor": candidate_actor,
                        "joint": joint,
                        "status": "unobservable",
                        "reference": None,
                        "candidate": None,
                        "candidate_ratio": None,
                    }
                )
                continue
            reference_speed = _track_speed(reference_track[1], max_gap_s, max_step)
            candidate_speed = _track_speed(candidate_track[1], max_gap_s, max_step)
            reference_value = reference_speed["median_normalized_speed_per_s"]
            candidate_value = candidate_speed["median_normalized_speed_per_s"]
            ratio = (
                None
                if reference_value in {None, 0} or candidate_value is None
                else round(candidate_value / reference_value, 6)
            )
            rows.append(
                {
                    "reference_actor": reference_actor,
                    "candidate_actor": candidate_actor,
                    "joint": joint,
                    "status": (
                        "unobservable"
                        if ratio is None
                        else "pass" if ratio >= minimum_ratio else "fail"
                    ),
                    "reference": reference_speed,
                    "candidate": candidate_speed,
                    "candidate_ratio": ratio,
                }
            )
    statuses = [row["status"] for row in rows]
    return {
        "status": (
            "fail"
            if "fail" in statuses
            else "unobservable" if "unobservable" in statuses else "pass"
        ),
        "measurement_class": "detected_2d_image_space",
        "camera_motion_separated": False,
        "tracks": rows,
        "reference_possible_swap_frames": reference_batch["summary"][
            "possible_swap_frames"
        ],
        "candidate_possible_swap_frames": candidate_batch["summary"][
            "possible_swap_frames"
        ],
    }


def _media_identity(
    media: dict[str, Any], probe_fn: Callable[..., dict[str, Any]]
) -> tuple[Path, dict[str, Any]]:
    path = Path(media["local_path"]).expanduser().resolve()
    probe = probe_fn(path, expected_sha256=media["sha256"])
    required = {
        "duration_s",
        "start_time_s",
        "width",
        "height",
        "frame_rate",
        "probe_hash",
    }
    if set(probe) != required:
        raise ValueError("side-by-side media probe returned an invalid field set")
    return path, {
        "source_id": media["source_id"],
        "asset_id": media["asset_id"],
        "sha256": media["sha256"],
        "rights_scope": media["rights_scope"],
        "duration_s": float(probe["duration_s"]),
        "width": int(probe["width"]),
        "height": int(probe["height"]),
        "frame_rate": float(probe["frame_rate"]),
        "probe_hash": probe["probe_hash"],
    }


def _align_normalized_cuts(
    reference_cuts: list[float],
    candidate_cuts: list[float],
    reference_duration: float,
    candidate_duration: float,
    tolerance: float,
) -> dict[str, Any]:
    for label, cuts, duration in (
        ("reference", reference_cuts, reference_duration),
        ("candidate", candidate_cuts, candidate_duration),
    ):
        if (
            any(not _finite_number(value) or not 0 < float(value) < duration for value in cuts)
            or cuts != sorted(set(cuts))
        ):
            raise ValueError(f"{label} cut detector returned invalid boundaries")
    remaining = set(range(len(candidate_cuts)))
    matches = []
    for reference_cut in reference_cuts:
        normalized = reference_cut / reference_duration
        choices = sorted(
            (
                abs(candidate_cuts[index] / candidate_duration - normalized),
                index,
            )
            for index in remaining
        )
        if choices and choices[0][0] <= tolerance:
            error, index = choices[0]
            remaining.remove(index)
            matches.append(
                {
                    "reference_s": reference_cut,
                    "candidate_s": candidate_cuts[index],
                    "reference_projected_candidate_s": round(
                        normalized * candidate_duration, 9
                    ),
                    "normalized_error": round(error, 9),
                    "status": "pass",
                }
            )
        else:
            matches.append(
                {
                    "reference_s": reference_cut,
                    "candidate_s": None,
                    "reference_projected_candidate_s": round(
                        normalized * candidate_duration, 9
                    ),
                    "normalized_error": None,
                    "status": "missing",
                }
            )
    return {
        "status": (
            "pass"
            if len(reference_cuts) == len(candidate_cuts)
            and all(row["status"] == "pass" for row in matches)
            else "fail"
        ),
        "reference_cuts_s": reference_cuts,
        "candidate_cuts_s": candidate_cuts,
        "reference_shot_count": len(reference_cuts) + 1,
        "candidate_shot_count": len(candidate_cuts) + 1,
        "matches": matches,
        "extra_candidate_cuts_s": [candidate_cuts[index] for index in sorted(remaining)],
    }


def _vog_observations(vog: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        (
            copy.deepcopy(node["data"])
            for node in vog["nodes"]
            if node["node_type"] in {"observation", "segment"}
        ),
        key=lambda row: row["observation_id"],
    )


def _normalized_observation_midpoint(
    observation: dict[str, Any], authorized_interval: dict[str, float]
) -> float:
    duration = authorized_interval["end_s"] - authorized_interval["start_s"]
    midpoint = (
        observation["interval"]["start_s"]
        + observation["interval"]["end_s"]
    ) / 2
    return (midpoint - authorized_interval["start_s"]) / duration


def _observation_ref(vog: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    return {
        "observation_id": observation["observation_id"],
        "source_ref": f"{vog['graph_id']}#{observation['observation_id']}",
        "interval": copy.deepcopy(observation["interval"]),
        "subject_refs": copy.deepcopy(observation["subject_refs"]),
        "claim": copy.deepcopy(observation["claim"]),
        "claim_hash": sha256_value(observation["claim"]),
        "provenance": copy.deepcopy(observation["provenance"]),
    }


def _compare_video_observation_graphs(
    request: dict[str, Any],
    reference: dict[str, Any],
    candidate: dict[str, Any],
    *,
    tolerance: float,
    actor_mapping: dict[str, str],
    root: Path,
) -> dict[str, Any]:
    reference_artifact = request["reference"].get("video_observation_graph")
    candidate_artifact = request["candidate"].get("video_observation_graph")
    limitations = [
        "VOG alignment compares normalized time, profile, layer, subjects, and structured claim values; it does not infer paraphrase equivalence.",
        "A diverging interpreted claim identifies a review target, not physical measurement or a quality verdict.",
    ]
    if reference_artifact is None and candidate_artifact is None:
        return {
            "status": "not_supplied",
            "evidence_class": "interpreted",
            "confidence_averaging": False,
            "profile_match": None,
            "subject_mapping": copy.deepcopy(actor_mapping),
            "reference_graph": None,
            "candidate_graph": None,
            "counts": {
                "matching": 0,
                "diverging": 0,
                "conflicting": 0,
                "unobservable": 0,
            },
            "rows": [],
            "limitations": limitations,
        }
    if reference_artifact is None or candidate_artifact is None:
        raise ValueError("side-by-side VOG alignment requires both graph artifacts")
    reference_vog = _load_bound_json(reference_artifact, "reference VOG")
    candidate_vog = _load_bound_json(candidate_artifact, "candidate VOG")
    validate_video_observation_graph(reference_vog, root)
    validate_video_observation_graph(candidate_vog, root)
    for label, vog, media in (
        ("reference", reference_vog, reference),
        ("candidate", candidate_vog, candidate),
    ):
        if (
            vog["source"]["source_id"] != media["source_id"]
            or vog["source"]["sha256"] != media["sha256"]
            or vog["source"]["asset_ref"] != media["asset_id"]
        ):
            raise ValueError(f"{label} VOG refers to different media identity")
    reference_rows = _vog_observations(reference_vog)
    candidate_rows = _vog_observations(candidate_vog)
    reference_profiles = sorted(
        {row["provenance"]["profile_id"] for row in reference_rows}
    )
    candidate_profiles = sorted(
        {row["provenance"]["profile_id"] for row in candidate_rows}
    )
    if reference_profiles != candidate_profiles:
        raise ValueError("side-by-side VOGs require identical analysis profiles")
    reference_conflicts = {
        observation_id
        for row in reference_vog["contradictions"]
        for observation_id in (
            row["left_observation_id"],
            row["right_observation_id"],
        )
    }
    candidate_conflicts = {
        observation_id
        for row in candidate_vog["contradictions"]
        for observation_id in (
            row["left_observation_id"],
            row["right_observation_id"],
        )
    }
    remaining = set(range(len(candidate_rows)))
    rows = []
    for left in reference_rows:
        left_slot = (left["layer"], left["provenance"]["profile_id"])
        left_phase = _normalized_observation_midpoint(
            left, reference_vog["authorized_interval"]
        )
        choices = []
        for index in remaining:
            right = candidate_rows[index]
            right_slot = (right["layer"], right["provenance"]["profile_id"])
            if right_slot != left_slot:
                continue
            right_phase = _normalized_observation_midpoint(
                right, candidate_vog["authorized_interval"]
            )
            choices.append((abs(right_phase - left_phase), index))
        choices.sort()
        if not choices or choices[0][0] > tolerance:
            rows.append(
                {
                    "layer": left_slot[0],
                    "profile_id": left_slot[1],
                    "status": "unobservable",
                    "phase_error": None,
                    "reference": _observation_ref(reference_vog, left),
                    "candidate": None,
                }
            )
            continue
        error, index = choices[0]
        remaining.remove(index)
        right = candidate_rows[index]
        if (
            left["observation_id"] in reference_conflicts
            or right["observation_id"] in candidate_conflicts
        ):
            status = "conflicting"
        elif (
            left["claim"] == right["claim"]
            and sorted(actor_mapping.get(value, value) for value in left["subject_refs"])
            == right["subject_refs"]
        ):
            status = "matching"
        else:
            status = "diverging"
        rows.append(
            {
                "layer": left_slot[0],
                "profile_id": left_slot[1],
                "status": status,
                "phase_error": round(error, 9),
                "reference": _observation_ref(reference_vog, left),
                "candidate": _observation_ref(candidate_vog, right),
            }
        )
    for index in sorted(remaining):
        right = candidate_rows[index]
        rows.append(
            {
                "layer": right["layer"],
                "profile_id": right["provenance"]["profile_id"],
                "status": "unobservable",
                "phase_error": None,
                "reference": None,
                "candidate": _observation_ref(candidate_vog, right),
            }
        )
    rows.sort(
        key=lambda row: (
            row["profile_id"],
            row["layer"],
            "" if row["reference"] is None else row["reference"]["observation_id"],
            "" if row["candidate"] is None else row["candidate"]["observation_id"],
        )
    )
    counts = {
        status: sum(row["status"] == status for row in rows)
        for status in ("matching", "diverging", "conflicting", "unobservable")
    }
    if counts["diverging"]:
        status = "diverging"
    elif counts["conflicting"]:
        status = "conflicting"
    elif counts["unobservable"]:
        status = "unobservable"
    else:
        status = "matching"
    return {
        "status": status,
        "evidence_class": "interpreted",
        "confidence_averaging": False,
        "profile_match": True,
        "subject_mapping": copy.deepcopy(actor_mapping),
        "reference_graph": {
            "graph_id": reference_vog["graph_id"],
            "graph_hash": reference_vog["graph_hash"],
            "artifact_sha256": reference_artifact["sha256"],
        },
        "candidate_graph": {
            "graph_id": candidate_vog["graph_id"],
            "graph_hash": candidate_vog["graph_hash"],
            "artifact_sha256": candidate_artifact["sha256"],
        },
        "counts": counts,
        "rows": rows,
        "limitations": limitations,
    }


def compare_reference_candidate(
    request: dict[str, Any],
    *,
    root: Path = REPO_ROOT,
    probe_fn: Callable[..., dict[str, Any]] | None = None,
    cut_detector: Callable[[Path, float], list[float]] | None = None,
) -> dict[str, Any]:
    """Compare two exact local videos without promoting the result to authority."""
    _validate("reference_candidate_comparison_request", request, root)
    probe_fn = probe_fn or probe_media
    cut_detector = cut_detector or _detect_scene_cuts
    reference_path, reference = _media_identity(request["reference"], probe_fn)
    candidate_path, candidate = _media_identity(request["candidate"], probe_fn)
    settings = copy.deepcopy(request["settings"])
    reference_cuts = cut_detector(reference_path, settings["scene_threshold"])
    candidate_cuts = cut_detector(candidate_path, settings["scene_threshold"])
    timeline = _align_normalized_cuts(
        reference_cuts,
        candidate_cuts,
        reference["duration_s"],
        candidate["duration_s"],
        settings["normalized_cut_tolerance"],
    )

    reference_asr = request["reference"]["asr"]
    candidate_asr = request["candidate"]["asr"]
    if reference_asr is None or candidate_asr is None:
        speech = {
            "status": "unobservable",
            "reason": "both hash-bound ASR artifacts are required",
            "reference": None,
            "candidate": None,
            "candidate_wpm_ratio": None,
        }
    else:
        if reference_asr["model"] != candidate_asr["model"]:
            raise ValueError("side-by-side ASR artifacts require the same model")
        reference_speech = _asr_metrics(
            _load_bound_json(reference_asr, "reference ASR"),
            settings["minimum_pause_s"],
        )
        candidate_speech = _asr_metrics(
            _load_bound_json(candidate_asr, "candidate ASR"),
            settings["minimum_pause_s"],
        )
        ratio = round(
            candidate_speech["words_per_minute"]
            / reference_speech["words_per_minute"],
            6,
        )
        speech = {
            "status": (
                "pass" if ratio >= settings["minimum_speech_pace_ratio"] else "fail"
            ),
            "reason": None,
            "reference": {
                **reference_speech,
                "artifact_sha256": reference_asr["sha256"],
                "model": reference_asr["model"],
            },
            "candidate": {
                **candidate_speech,
                "artifact_sha256": candidate_asr["sha256"],
                "model": candidate_asr["model"],
            },
            "candidate_wpm_ratio": ratio,
        }

    reference_pose = request["reference"]["pose_batch"]
    candidate_pose = request["candidate"]["pose_batch"]
    if reference_pose is None or candidate_pose is None:
        motion = {
            "status": "unobservable",
            "reason": "both hash-bound pose batches are required",
            "measurement_class": "detected_2d_image_space",
            "camera_motion_separated": False,
            "tracks": [],
        }
    else:
        reference_batch = _load_bound_json(reference_pose, "reference pose batch")
        candidate_batch = _load_bound_json(candidate_pose, "candidate pose batch")
        if reference_batch["source"]["sha256"] != reference["sha256"]:
            raise ValueError("reference pose batch refers to different media bytes")
        if candidate_batch["source"]["sha256"] != candidate["sha256"]:
            raise ValueError("candidate pose batch refers to different media bytes")
        motion = _pose_speed_rows(
            reference_batch,
            candidate_batch,
            actor_mapping=settings["pose_actor_mapping"],
            joints=settings["joints"],
            max_gap_s=settings["max_pose_gap_s"],
            max_step=settings["max_pose_step"],
            minimum_ratio=settings["minimum_pose_speed_ratio"],
            root=root,
        )
        motion["reason"] = None
        motion["reference_batch_sha256"] = reference_pose["sha256"]
        motion["candidate_batch_sha256"] = candidate_pose["sha256"]

    vog_alignment = _compare_video_observation_graphs(
        request,
        reference,
        candidate,
        tolerance=settings["normalized_cut_tolerance"],
        actor_mapping=settings["pose_actor_mapping"],
        root=root,
    )

    assessments = sorted(
        copy.deepcopy(request["assessments"]), key=lambda row: row["id"]
    )
    statuses = [timeline["status"], speech["status"], motion["status"]] + [
        row["status"] for row in assessments
    ]
    if vog_alignment["status"] == "diverging":
        statuses.append("fail")
    elif vog_alignment["status"] == "conflicting":
        statuses.append("conflict")
    elif vog_alignment["status"] == "unobservable":
        statuses.append("unobservable")
    if "fail" in statuses:
        overall = "fail"
    elif any(value in {"conflict", "unobservable"} for value in statuses):
        overall = "inconclusive"
    else:
        overall = "pass"
    visual_samples = [
        {
            "index": index + 1,
            "phase": round((index + 0.5) / settings["visual_sample_count"], 9),
            "reference_s": round(
                reference["duration_s"]
                * (index + 0.5)
                / settings["visual_sample_count"],
                9,
            ),
            "candidate_s": round(
                candidate["duration_s"]
                * (index + 0.5)
                / settings["visual_sample_count"],
                9,
            ),
        }
        for index in range(settings["visual_sample_count"])
    ]
    reference_wpm = None if speech["reference"] is None else speech["reference"]["words_per_minute"]
    core = {
        "schema": REFERENCE_CANDIDATE_COMPARISON_REPORT_SCHEMA,
        "policy": REFERENCE_CANDIDATE_COMPARISON_POLICY,
        "authority_status": "operational_evidence_only",
        "overall_status": overall,
        "reference": reference,
        "candidate": candidate,
        "settings": settings,
        "timeline": timeline,
        "speech": speech,
        "motion": motion,
        "vog_alignment": vog_alignment,
        "assessments": assessments,
        "reference_control_candidates": {
            "review_status": "unreviewed_operational_targets",
            "target_duration_s": candidate["duration_s"],
            "target_shot_count": timeline["reference_shot_count"],
            "target_cut_s": [
                row["reference_projected_candidate_s"] for row in timeline["matches"]
            ],
            "target_word_count": (
                None
                if reference_wpm is None
                else round(reference_wpm * candidate["duration_s"] / 60.0)
            ),
            "target_words_per_minute": reference_wpm,
            "maximum_pause_s": (
                None if speech["reference"] is None else speech["reference"]["longest_pause_s"]
            ),
            "minimum_pose_speed_ratio": settings["minimum_pose_speed_ratio"],
        },
        "visual_samples": visual_samples,
        "limitations": sorted(
            [
                "ASR timestamps are detector estimates and do not establish exact spoken wording.",
                "Pose speed is two-dimensional image-space evidence with no camera-motion separation.",
                "Scene-change detection depends on the declared threshold and local FFmpeg implementation.",
                "Identity, product, text, and semantic assessments remain in their declared evidence lanes.",
                "Reference-derived controls are unreviewed operational candidates, not curated knowledge or production qualification.",
            ]
        ),
        "input_hash": sha256_value(request),
    }
    report = {
        **core,
        "report_id": "reference_candidate_"
        + hashlib.sha256(canonical_json_bytes(core)).hexdigest()[:24],
    }
    _validate("reference_candidate_comparison_report", report, root)
    return report


def write_time_normalized_contact_sheet(
    request: dict[str, Any],
    report: dict[str, Any],
    output: Path,
    *,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Render the report's exact phase-aligned left/right frame pairs under work/."""
    path = output.expanduser().resolve()
    work = (root / "work").resolve()
    if work not in path.parents:
        raise ValueError("comparison visual output must stay under ignored work/")
    samples = report["visual_samples"]
    if not samples:
        raise ValueError("comparison request disabled visual samples")
    path.parent.mkdir(parents=True, exist_ok=True)
    for side in ("reference", "candidate"):
        media_path = Path(request[side]["local_path"]).expanduser().resolve()
        if _path_sha256(media_path) != request[side]["sha256"]:
            raise ValueError(f"{side} media changed before visual extraction")
    with tempfile.TemporaryDirectory(dir=path.parent) as temporary:
        temporary_path = Path(temporary)
        frames = []
        for sample in samples:
            for side in ("reference", "candidate"):
                frame = temporary_path / f"{sample['index']:02d}_{side}.png"
                subprocess.run(
                    [
                        "ffmpeg",
                        "-nostdin",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-y",
                        "-ss",
                        str(sample[f"{side}_s"]),
                        "-i",
                        str(Path(request[side]["local_path"]).expanduser().resolve()),
                        "-frames:v",
                        "1",
                        "-vf",
                        "scale=320:568:force_original_aspect_ratio=decrease,pad=320:568:(ow-iw)/2:(oh-ih)/2:black",
                        str(frame),
                    ],
                    check=True,
                    capture_output=True,
                )
                frames.append(frame)
        filter_parts = []
        pair_labels = []
        for index in range(len(samples)):
            pair = f"pair{index}"
            filter_parts.append(f"[{index * 2}:v][{index * 2 + 1}:v]hstack=2[{pair}]")
            pair_labels.append(f"[{pair}]")
        filter_parts.append(
            "".join(pair_labels) + f"vstack={len(samples)}[out]"
        )
        command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
        for frame in frames:
            command.extend(["-i", str(frame)])
        command.extend(
            [
                "-filter_complex",
                ";".join(filter_parts),
                "-map",
                "[out]",
                "-frames:v",
                "1",
                str(path),
            ]
        )
        subprocess.run(command, check=True, capture_output=True)
    return {
        "path": str(path),
        "sha256": "sha256:" + _path_sha256(path),
        "sample_count": len(samples),
        "layout": "reference_left_candidate_right_time_normalized",
    }


def make_verification_asset_job(
    build_dir: Path,
    render_result_path: Path,
    artifact_id: str,
    *,
    rights_scope: str,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Create one hash-bound TwelveLabs upload job for a rendered artifact."""
    _, result_path, render_result, artifact = _validated_render_identity(
        build_dir, render_result_path, artifact_id, root
    )
    media_path = _validated_artifact_path(result_path, artifact)
    identity = {
        "job_id": render_result["job_id"],
        "artifact_id": artifact_id,
        "artifact_sha256": artifact["sha256"],
        "rights_scope": rights_scope,
    }
    digest = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()[:24]
    job = {
        "schema": "cpcs.twelvelabs_asset_job/1.0",
        "job_id": "tl_asset_verify_" + digest,
        "media_type": "video",
        "source": {
            "file_path": str(media_path),
            "sha256": artifact["sha256"].removeprefix("sha256:"),
        },
        "knowledge_store_id": None,
        "rights_scope": rights_scope,
        "created_at": render_result["completed_at"],
    }
    validate_instance("twelvelabs_asset_job", job, root)
    return job


def make_verification_analysis_job(
    build_dir: Path,
    render_result_path: Path,
    artifact_id: str,
    *,
    provider_asset_ref: str,
    rights_scope: str,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Create one score-bound Pegasus job for a rendered provider asset."""
    build, result_path, render_result, artifact = _validated_render_identity(
        build_dir, render_result_path, artifact_id, root
    )
    _validated_artifact_path(result_path, artifact)
    requirements = [
        {
            "metric_id": row["metric_id"],
            "target_path": target_path,
            "method": row["method"],
            "observability": "semantic",
        }
        for row in build["verification_plan"]["requirements"]
        if row["observability"] == "semantic"
        for target_path in row["target_paths"]
    ]
    requirements = sorted(
        requirements, key=lambda row: (row["metric_id"], row["target_path"])
    )
    if not requirements:
        raise ValueError("build has no semantic verification requirements")
    prompt = (
        "Assess every declared metric and target using visible evidence only. "
        "Return pass, fail, or unobservable. Do not add metrics or canonical paths. "
        "Criteria: "
        + canonical_json_bytes(requirements).decode("utf-8").strip()
    )
    if len(prompt) > 8000:
        raise ValueError("semantic verification criteria exceed the provider prompt budget")
    identity = {
        "build_id": render_result["build_id"],
        "job_id": render_result["job_id"],
        "artifact_id": artifact_id,
        "artifact_sha256": artifact["sha256"],
        "provider_asset_ref": provider_asset_ref,
        "requirements": requirements,
    }
    digest = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()[:24]
    duration = float(render_result["expected_media"]["duration_seconds"])
    job = {
        "schema": "cpcs.twelvelabs_analyze_job/1.0",
        "job_id": "tl_analyze_verify_" + digest,
        "source_video": {
            "asset_ref": provider_asset_ref,
            "sha256": artifact["sha256"].removeprefix("sha256:"),
            "rights_scope": rights_scope,
        },
        "analysis_scope": "exact_video",
        "media_bounds": {"source_start_s": 0.0, "source_end_s": duration},
        "interval": {"source_start_s": 0.0, "source_end_s": duration},
        "profile_id": "pegasus.score_compliance/1.0",
        "prompt": prompt,
        "candidate_concepts": [],
        "verification_requirements": requirements,
        "created_at": render_result["completed_at"],
    }
    validate_instance("twelvelabs_analyze_job", job, root)
    return job


def build_verification_evidence_bundle(
    build_dir: Path,
    render_result_path: Path,
    artifact_id: str,
    observations: list[dict[str, Any]],
    *,
    human_reviews: list[dict[str, Any]] | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Bind normalized observations to the exact score targets they were allowed to assess."""
    build, result_path, render_result, artifact = _validated_render_identity(
        build_dir, render_result_path, artifact_id, root
    )
    _validated_artifact_path(result_path, artifact)
    allowed = {
        (row["metric_id"], target_path): row
        for row in build["verification_plan"]["requirements"]
        for target_path in row["target_paths"]
    }
    sources: list[dict[str, Any]] = []
    assertions: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    for record in [*copy.deepcopy(observations), *copy.deepcopy(human_reviews or [])]:
        source_type = (
            "human_review"
            if record.get("schema") == "cpcs.human_verification_review/1.0"
            else "normalized_video_observation"
        )
        if source_type == "normalized_video_observation":
            validate_instance("normalized_video_observation", record, root)
            if record["source_sha256"] != artifact["sha256"].removeprefix("sha256:"):
                raise ValueError("verification observation refers to different media bytes")
        source = make_evidence_source(record, source_type=source_type)
        if source["source_id"] in source_ids:
            raise ValueError("verification inputs contain duplicate source IDs")
        source_ids.add(source["source_id"])
        sources.append(source)
        if (
            source_type != "normalized_video_observation"
            or record["provenance"]["profile_id"]
            != "pegasus.score_compliance/1.0"
        ):
            continue
        claim = record["claim"]
        required_claim = {
            "metric_id",
            "target_path",
            "method",
            "verdict",
            "observed",
            "deviation",
            "limitations",
        }
        if set(claim) != required_claim:
            raise ValueError("score-compliance observation has an invalid claim contract")
        pair = (claim["metric_id"], claim["target_path"])
        requirement = allowed.get(pair)
        if requirement is None or requirement["observability"] != "semantic":
            raise ValueError("score-compliance observation targets an undeclared semantic metric")
        if claim["method"] != requirement["method"]:
            raise ValueError("score-compliance observation uses the wrong metric method")
        if claim["verdict"] == "unobservable":
            continue
        if claim["verdict"] not in {"pass", "fail"}:
            raise ValueError("score-compliance observation has an invalid verdict")
        assertions.append(
            make_assertion(
                metric_id=claim["metric_id"],
                target_path=claim["target_path"],
                source_ref=source["source_id"],
                verdict=claim["verdict"],
                observed=claim["observed"],
                interval=record["interval"],
                deviation=claim["deviation"],
                limitations=claim["limitations"],
            )
        )
    bundle = {
        "schema": EVIDENCE_SCHEMA,
        "job_id": render_result["job_id"],
        "build_id": render_result["build_id"],
        "artifact_id": artifact_id,
        "artifact_sha256": artifact["sha256"],
        "sources": sorted(sources, key=lambda row: row["source_id"]),
        "assertions": sorted(assertions, key=lambda row: row["assertion_id"]),
    }
    _validate("evidence_bundle", bundle, root)
    return bundle


def verify_render(
    build_dir: Path,
    render_result_path: Path,
    artifact_id: str,
    evidence_bundle: dict[str, Any],
    *,
    root: Path = REPO_ROOT,
    probe_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    probe_fn = probe_fn or probe_media
    build, result_path, render_result, artifact = _validated_render_identity(
        build_dir, render_result_path, artifact_id, root
    )
    media_path = _validated_artifact_path(result_path, artifact)
    metadata = probe_fn(
        media_path, expected_sha256=artifact["sha256"].removeprefix("sha256:")
    )
    required_probe = {
        "duration_s",
        "start_time_s",
        "width",
        "height",
        "frame_rate",
        "probe_hash",
    }
    if set(metadata) != required_probe:
        raise ValueError("media probe returned an invalid field set")
    sources, assertions = _validate_evidence(
        evidence_bundle,
        job_id=render_result["job_id"],
        build_id=render_result["build_id"],
        artifact_id=artifact_id,
        artifact_hash=artifact["sha256"],
        duration_seconds=float(metadata["duration_s"]),
        requirements=build["verification_plan"]["requirements"],
        root=root,
    )
    assertions = sorted(
        [
            *assertions,
            *_derive_measurement_assertions(
                sources=sources,
                assertions=assertions,
                requirements=build["verification_plan"]["requirements"],
                score=build["score"],
            ),
        ],
        key=lambda row: row["assertion_id"],
    )
    evidence_trace = []
    for assertion in assertions:
        source = sources[assertion["source_ref"]]
        record = source["record"]
        evidence_trace.append(
            {
                "assertion_id": assertion["assertion_id"],
                "source_ref": source["source_id"],
                "source_hash": source["source_hash"],
                "lane": source["lane"],
                "assertion_origin": assertion["origin"],
                "evidence_class": (
                    record["evidence_class"]
                    if source["source_type"] == "normalized_video_observation"
                    else "authored"
                ),
                "confidence": (
                    record["confidence"]
                    if source["source_type"] == "normalized_video_observation"
                    else 1.0
                ),
                "verdict": assertion["verdict"],
                "observed": copy.deepcopy(assertion["observed"]),
                "interval": copy.deepcopy(assertion["interval"]),
            }
        )
    artifact_checks = _artifact_checks(
        build["verification_plan"], artifact, metadata
    )
    control_checks, conflicts = _control_checks(
        build["verification_plan"]["requirements"], assertions, build["score"]
    )
    artifact_statuses = [row["status"] for row in artifact_checks]
    control_statuses = [row["status"] for row in control_checks]
    if "fail" in artifact_statuses or "fail" in control_statuses:
        overall = "fail"
    elif any(
        value in {"conflict", "unobservable", "review_required"}
        for value in control_statuses
    ):
        overall = "inconclusive"
    else:
        overall = "pass"
    normalized_evidence = {
        **copy.deepcopy(evidence_bundle),
        "sources": sorted(
            copy.deepcopy(evidence_bundle["sources"]), key=lambda row: row["source_id"]
        ),
        "assertions": sorted(
            copy.deepcopy(evidence_bundle["assertions"]),
            key=lambda row: row["assertion_id"],
        ),
    }
    core = {
        "schema": REPORT_SCHEMA,
        "policy_versions": {
            "verification": VERIFICATION_POLICY,
            "repair": REPAIR_POLICY,
        },
        "job_id": render_result["job_id"],
        "build_id": render_result["build_id"],
        "build_hash": render_result["build_hash"],
        "score_id": build["score"]["score_id"],
        "artifact": {
            "artifact_id": artifact_id,
            "sha256": artifact["sha256"],
            "size_bytes": artifact["size_bytes"],
            "mime_type": artifact["mime_type"],
            "duration_seconds": metadata["duration_s"],
            "width": metadata["width"],
            "height": metadata["height"],
            "aspect_ratio": _aspect_ratio(metadata["width"], metadata["height"]),
            "resolution": _resolution(metadata["width"], metadata["height"]),
            "frame_rate": metadata["frame_rate"],
            "probe_hash": metadata["probe_hash"],
        },
        "overall_status": overall,
        "artifact_checks": artifact_checks,
        "control_checks": control_checks,
        "conflicts": conflicts,
        "evidence_trace": sorted(
            evidence_trace, key=lambda row: row["assertion_id"]
        ),
        "summary": {
            "artifact": _status_counts(artifact_statuses),
            "controls": _status_counts(control_statuses),
        },
        "repair_plan": _repair_plan(
            artifact_id=artifact_id,
            artifact_checks=artifact_checks,
            control_checks=control_checks,
            controls=build["score"]["provider_neutral_controls"],
        ),
        "input_hashes": {
            "build_manifest": sha256_bytes(
                build["artifact_bytes"]["build_manifest.json"]
            ),
            "verification_plan": sha256_bytes(
                build["artifact_bytes"]["verification_plan.json"]
            ),
            "render_result": sha256_bytes(result_path.read_bytes()),
            "evidence_bundle": sha256_value(normalized_evidence),
            "artifact": artifact["sha256"],
        },
    }
    digest = hashlib.sha256(canonical_json_bytes(core)).hexdigest()[:32]
    report = {"report_id": "compliance_" + digest, **core}
    _validate("compliance_report", report, root)
    return report


def _write_output(path: Path, value: dict[str, Any], root: Path) -> None:
    output = path.expanduser().resolve()
    work = (root / "work").resolve()
    if output != work and work not in output.parents:
        raise ValueError("verification output must stay under ignored work/")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(value))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    verify = sub.add_parser("verify")
    verify.add_argument("build_dir", type=Path)
    verify.add_argument("render_result", type=Path)
    verify.add_argument("artifact_id")
    verify.add_argument("evidence_bundle", type=Path)
    verify.add_argument("--output", type=Path)
    compare = sub.add_parser("compare-reference")
    compare.add_argument("request", type=Path)
    compare.add_argument("--output", type=Path)
    compare.add_argument("--visual-output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "validate":
        print(json.dumps(validate_verification_configuration(), sort_keys=True))
        return
    if args.command == "compare-reference":
        request = _load_object(args.request, "reference comparison request")
        report = compare_reference_candidate(request)
        if args.output is not None:
            _write_output(args.output, report, REPO_ROOT)
        if args.visual_output is not None:
            visual = write_time_normalized_contact_sheet(
                request, report, args.visual_output
            )
            print(json.dumps({"report": report, "visual": visual}, indent=2, sort_keys=True))
        else:
            print(json.dumps(report, indent=2, sort_keys=True))
        return
    report = verify_render(
        args.build_dir,
        args.render_result,
        args.artifact_id,
        _load_object(args.evidence_bundle, "verification evidence bundle"),
    )
    if args.output is not None:
        _write_output(args.output, report, REPO_ROOT)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
