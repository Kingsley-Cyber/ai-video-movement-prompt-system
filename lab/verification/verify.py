"""Deterministically verify one render against its compiler-owned plan."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, FormatChecker

from lab.compiler.build import load_validated_build_directory
from lab.compiler.profiles import REPO_ROOT
from lab.compiler.provenance import canonical_json_bytes, sha256_bytes, sha256_value
from lab.runtime.contracts import validate_runtime_instance
from lab.second_brain.src.validate import validate_instance
from lab.second_brain.src.video_observation import assert_claim_policy, probe_media

VERIFICATION_POLICY = "cpcs-render-verification/1.0"
REPAIR_POLICY = "cpcs-bounded-repair/1.0"
EVIDENCE_SCHEMA = "cpcs.verification_evidence_bundle/1.0"
REPORT_SCHEMA = "cpcs.compliance_report/1.0"
SCHEMAS = {
    "evidence_bundle": "verification_evidence_bundle.schema.json",
    "compliance_report": "compliance_report.schema.json",
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


def validate_verification_configuration(root: Path = REPO_ROOT) -> dict[str, Any]:
    for name in SCHEMAS:
        Draft202012Validator.check_schema(_schema(name, root))
    return {
        "schemas": len(SCHEMAS),
        "verification_policy": VERIFICATION_POLICY,
        "repair_policy": REPAIR_POLICY,
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
    args = parser.parse_args(argv)
    if args.command == "validate":
        print(json.dumps(validate_verification_configuration(), sort_keys=True))
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
