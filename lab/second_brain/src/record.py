"""Append-only APIs for sealed flights, runs, and evidence observations."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .authority import authority_reader, authority_writer
from lab.compiler.build import load_validated_build_directory
from lab.compiler.provenance import sha256_bytes
from lab.runtime.contracts import validate_runtime_instance
from lab.verification.verify import validate_verification_instance

from .measurement import validate_measurement_batch

from .validate import (
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    canonical_json_bytes,
    content_hash,
    read_jsonl,
    sha256_value,
    validate_instance,
)

KIND_TO_FILE = {
    "run": "runs.jsonl",
    "pegasus_observation": "pegasus_observations.jsonl",
    "measurement_observation": "measurement_observations.jsonl",
}
LEGACY_EVIDENCE_POLICY = "cpcs-controlled-evidence/1.0"
EVIDENCE_POLICY = "cpcs-controlled-evidence/1.1"


def _text_hash(value: str) -> str:
    """Hash the exact UTF-8 bytes of human-authored text."""
    return sha256_bytes(value.encode("utf-8"))


def _parse_timestamp(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationFailure(f"{label} must be an RFC 3339 date-time") from exc
    if parsed.tzinfo is None:
        raise ValidationFailure(f"{label} must include a timezone")
    return parsed


def _append_content_record(
    *,
    path: Path,
    schema_name: str,
    value: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    """Append one content-identified hash-chain row, or return an exact replay."""
    assert_write_target("record", path, root)
    rows = read_jsonl(path)
    existing = next((row for row in rows if row["id"] == value["id"]), None)
    if existing is not None:
        comparable = {
            key: item
            for key, item in existing.items()
            if key not in {"prior_record_hash", "record_hash"}
        }
        if comparable == value:
            return existing
        raise ValidationFailure(f"immutable record ID collision: {value['id']}")
    stored = copy.deepcopy(value)
    stored["prior_record_hash"] = rows[-1]["record_hash"] if rows else None
    stored["record_hash"] = content_hash(stored)
    validate_instance(schema_name, stored, root)
    with path.open("ab") as handle:
        handle.write(canonical_json_bytes(stored))
        handle.flush()
        os.fsync(handle.fileno())
    return stored


def _exact_existing_content_record(
    rows: list[dict[str, Any]], value: dict[str, Any]
) -> dict[str, Any] | None:
    existing = next((row for row in rows if row["id"] == value["id"]), None)
    if existing is None:
        return None
    comparable = {
        key: item
        for key, item in existing.items()
        if key not in {"prior_record_hash", "record_hash"}
    }
    if comparable != value:
        raise ValidationFailure(f"immutable record ID collision: {value['id']}")
    return existing


def _validated_render_artifact(
    render_result_path: Path,
    artifact_id: str,
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve one artifact and verify its recorded bytes before evidence capture."""
    render_result, render_bytes = _load_json_object(
        render_result_path, "render result"
    )
    validate_runtime_instance("render_result", render_result, root)
    artifacts = [
        row for row in render_result["artifacts"] if row["artifact_id"] == artifact_id
    ]
    if len(artifacts) != 1:
        raise ValidationFailure(
            "render result does not contain the selected artifact exactly once"
        )
    artifact = artifacts[0]
    result_root = render_result_path.expanduser().resolve().parent
    candidate = result_root / artifact["relative_path"]
    if candidate.is_symlink():
        raise ValidationFailure("render artifact cannot be a symlink")
    resolved = candidate.resolve()
    if result_root not in resolved.parents or not resolved.is_file():
        raise ValidationFailure("render artifact path is unsafe or missing")
    artifact_bytes = resolved.read_bytes()
    if (
        len(artifact_bytes) != artifact["size_bytes"]
        or sha256_bytes(artifact_bytes) != artifact["sha256"]
    ):
        raise ValidationFailure("render artifact bytes do not match the render result")
    lineage = {
        "render_job_id": render_result["job_id"],
        "render_result_hash": sha256_bytes(render_bytes),
        "build_id": render_result["build_id"],
        "build_hash": render_result["build_hash"],
        "provider": render_result["provider"],
        "model": render_result["model"],
        "artifact_id": artifact_id,
        "artifact_sha256": artifact["sha256"],
        "artifact_size_bytes": artifact["size_bytes"],
    }
    return render_result, lineage


def _chain_heads(
    rows: list[dict[str, Any]], supersedes_field: str
) -> list[dict[str, Any]]:
    superseded = {
        record_id
        for row in rows
        for record_id in row.get(supersedes_field, [])
    }
    return [row for row in rows if row["id"] not in superseded]


def _testimonial_component(
    testimonial_id: str, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_id = {row["id"]: row for row in rows}
    if testimonial_id not in by_id:
        raise ValidationFailure(f"unknown human testimonial: {testimonial_id}")
    related = {testimonial_id}
    changed = True
    while changed:
        changed = False
        for row in rows:
            links = set(row.get("supersedes", []))
            if row["id"] in related or links & related:
                additions = {row["id"], *links}
                if not additions <= related:
                    related.update(additions)
                    changed = True
    return [row for row in rows if row["id"] in related]


def _validate_testimonial_stores(
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base = root / "lab" / "second_brain" / "immutable"
    testimonials = read_jsonl(base / "testimonials.jsonl")
    reviews = read_jsonl(base / "testimonial_reviews.jsonl")
    for schema_name, rows, path in (
        ("human_testimonial", testimonials, base / "testimonials.jsonl"),
        ("testimonial_review", reviews, base / "testimonial_reviews.jsonl"),
    ):
        prior = None
        seen: set[str] = set()
        for row in rows:
            validate_instance(schema_name, row, root)
            if row["id"] in seen:
                raise ValidationFailure(f"{path}: duplicate immutable ID {row['id']}")
            seen.add(row["id"])
            if row["prior_record_hash"] != prior or row["record_hash"] != content_hash(row):
                raise ValidationFailure(f"{path}: invalid hash chain at {row['id']}")
            prior = row["record_hash"]
    testimonial_ids = {row["id"] for row in testimonials}
    missing = sorted(
        row["testimonial_id"]
        for row in reviews
        if row["testimonial_id"] not in testimonial_ids
    )
    if missing:
        raise ValidationFailure(
            "testimonial reviews reference missing testimonials: " + ", ".join(missing)
        )
    return testimonials, reviews


@authority_writer("immutable")
def capture_human_testimonial(
    request: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Capture an exact human statement against verified render bytes."""
    validate_instance("human_testimonial_capture", request, root)
    _render, artifact = _validated_render_artifact(
        Path(request["render_result"]), request["artifact_id"], root
    )
    path = root / "lab" / "second_brain" / "immutable" / "testimonials.jsonl"
    rows = read_jsonl(path)
    supersedes = copy.deepcopy(request["supersedes"])
    value = {
        "schema": "cpcs.human_testimonial/1.0",
        "artifact": artifact,
        "speaker": copy.deepcopy(request["speaker"]),
        "language": request["language"],
        "raw_statement": request["raw_statement"],
        "raw_statement_hash": _text_hash(request["raw_statement"]),
        "captured_at": request["captured_at"],
        "supersedes": supersedes,
    }
    value["id"] = "testimonial_" + sha256_value(value).removeprefix("sha256:")[:24]
    existing = _exact_existing_content_record(rows, value)
    if existing is not None:
        return existing
    if supersedes:
        predecessor = next(
            (row for row in rows if row["id"] == supersedes[0]), None
        )
        if predecessor is None:
            raise ValidationFailure(
                f"testimonial supersedes unknown record: {supersedes[0]}"
            )
        if any(supersedes[0] in row.get("supersedes", []) for row in rows):
            raise ValidationFailure("testimonial correction must supersede a current head")
        if (
            predecessor["artifact"] != artifact
            or predecessor["speaker"] != request["speaker"]
        ):
            raise ValidationFailure(
                "testimonial correction must retain its exact artifact and speaker"
            )
        if _parse_timestamp(request["captured_at"], "captured_at") <= _parse_timestamp(
            predecessor["captured_at"], "predecessor captured_at"
        ):
            raise ValidationFailure("testimonial correction must be captured later")
    return _append_content_record(
        path=path,
        schema_name="human_testimonial",
        value=value,
        root=root,
    )


def _validate_review_spans(
    normalization: dict[str, Any], statement: str
) -> None:
    metric_findings = normalization.get("metric_findings", [])
    findings = [
        *normalization["dimension_findings"],
        *metric_findings,
        *normalization["strengths"],
        *normalization["failures"],
        *normalization["attribution_candidates"],
    ]
    dimensions = [row["dimension"] for row in normalization["dimension_findings"]]
    if len(dimensions) != len(set(dimensions)):
        raise ValidationFailure("testimonial dimension findings must be unique")
    metric_ids = [row["metric_id"] for row in metric_findings]
    if len(metric_ids) != len(set(metric_ids)):
        raise ValidationFailure("testimonial metric findings must be unique")
    for finding in metric_findings:
        targets = [
            (row["target_type"], row["target_ref"])
            for row in finding["authored_targets"]
        ]
        if len(targets) != len(set(targets)):
            raise ValidationFailure(
                "testimonial metric authored targets must be unique"
            )
    for finding in findings:
        for span in finding["evidence_spans"]:
            if span["start"] >= span["end"] or span["end"] > len(statement):
                raise ValidationFailure("testimonial evidence span is outside the raw statement")
            quote = statement[span["start"] : span["end"]]
            if quote != span["quote"] or _text_hash(quote) != span["quote_hash"]:
                raise ValidationFailure(
                    "testimonial evidence span does not match the exact raw statement"
                )


def testimonial_normalization_response_hash(
    normalization: dict[str, Any]
) -> str:
    """Return the deterministic content hash expected for an LLM proposal."""
    value = copy.deepcopy(normalization)
    value["normalizer"].pop("response_hash", None)
    return sha256_value(value)


@authority_writer("immutable")
def review_human_testimonial(
    request: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Review one current testimonial and append a source-grounded normalization."""
    validate_instance("testimonial_review_request", request, root)
    testimonials, reviews = _validate_testimonial_stores(root)
    testimonial = next(
        (row for row in testimonials if row["id"] == request["testimonial_id"]),
        None,
    )
    if testimonial is None:
        raise ValidationFailure(f"unknown human testimonial: {request['testimonial_id']}")
    if any(
        testimonial["id"] in row.get("supersedes", []) for row in testimonials
    ):
        raise ValidationFailure("only a current testimonial may receive a new review")
    normalization = copy.deepcopy(request["normalization"])
    normalizer = normalization["normalizer"]
    if normalizer["origin"] == "llm_proposal":
        expected_response_hash = testimonial_normalization_response_hash(normalization)
        if normalizer["response_hash"] != expected_response_hash:
            raise ValidationFailure(
                "LLM testimonial response_hash does not match the structured proposal"
            )
    _validate_review_spans(normalization, testimonial["raw_statement"])
    if _parse_timestamp(request["reviewed_at"], "reviewed_at") < _parse_timestamp(
        testimonial["captured_at"], "testimonial captured_at"
    ):
        raise ValidationFailure("testimonial review cannot predate its raw statement")

    artifact = {
        key: testimonial["artifact"][key]
        for key in ("render_job_id", "build_id", "artifact_id", "artifact_sha256")
    }
    value = {
        "schema": "cpcs.testimonial_review/1.0",
        "testimonial_id": testimonial["id"],
        "testimonial_record_hash": testimonial["record_hash"],
        "raw_statement_hash": testimonial["raw_statement_hash"],
        "artifact": artifact,
        "normalization": normalization,
        "reviewed_by": request["reviewed_by"],
        "reviewed_at": request["reviewed_at"],
        "supersedes_reviews": copy.deepcopy(request["supersedes_reviews"]),
    }
    value["id"] = (
        "testimonial_review_" + sha256_value(value).removeprefix("sha256:")[:24]
    )
    existing = _exact_existing_content_record(reviews, value)
    if existing is not None:
        return existing

    component = _testimonial_component(testimonial["id"], testimonials)
    component_ids = {row["id"] for row in component}
    component_reviews = [
        row for row in reviews if row["testimonial_id"] in component_ids
    ]
    heads = _chain_heads(component_reviews, "supersedes_reviews")
    requested_predecessors = request["supersedes_reviews"]
    if component_reviews:
        if len(heads) != 1 or requested_predecessors != [heads[0]["id"]]:
            raise ValidationFailure(
                "testimonial review must supersede the one current review head"
            )
        if _parse_timestamp(request["reviewed_at"], "reviewed_at") <= _parse_timestamp(
            heads[0]["reviewed_at"], "predecessor reviewed_at"
        ):
            raise ValidationFailure("testimonial review correction must be later")
    elif requested_predecessors:
        raise ValidationFailure("first testimonial review cannot supersede another review")

    return _append_content_record(
        path=root
        / "lab"
        / "second_brain"
        / "immutable"
        / "testimonial_reviews.jsonl",
        schema_name="testimonial_review",
        value=value,
        root=root,
    )


@authority_reader("testimonial_inspection")
def inspect_human_testimonial(
    testimonial_id: str, root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Return one correction component and its current immutable heads."""
    testimonials, reviews = _validate_testimonial_stores(root)
    component = _testimonial_component(testimonial_id, testimonials)
    component_ids = {row["id"] for row in component}
    component_reviews = [
        row for row in reviews if row["testimonial_id"] in component_ids
    ]
    return {
        "schema": "cpcs.testimonial_inspection/1.0",
        "requested_testimonial_id": testimonial_id,
        "testimonials": sorted(
            component, key=lambda row: (row["captured_at"], row["id"])
        ),
        "reviews": sorted(
            component_reviews, key=lambda row: (row["reviewed_at"], row["id"])
        ),
        "current_testimonial_ids": sorted(
            row["id"] for row in _chain_heads(component, "supersedes")
        ),
        "current_review_ids": sorted(
            row["id"]
            for row in _chain_heads(component_reviews, "supersedes_reviews")
        ),
    }


def _resolve_testimonial_lineage(
    *,
    review_id: str,
    artifact: dict[str, Any],
    build_id: str,
    render_job_id: str,
    human_review: dict[str, Any],
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    testimonials, reviews = _validate_testimonial_stores(root)
    review = next((row for row in reviews if row["id"] == review_id), None)
    if review is None:
        raise ValidationFailure(f"unknown testimonial review: {review_id}")
    testimonial = next(
        (row for row in testimonials if row["id"] == review["testimonial_id"]),
        None,
    )
    if testimonial is None:
        raise ValidationFailure("testimonial review lost its raw statement")
    component = _testimonial_component(testimonial["id"], testimonials)
    component_ids = {row["id"] for row in component}
    component_reviews = [
        row for row in reviews if row["testimonial_id"] in component_ids
    ]
    if testimonial["id"] not in {
        row["id"] for row in _chain_heads(component, "supersedes")
    }:
        raise ValidationFailure("experiment receipt requires the current raw testimonial")
    if review_id not in {
        row["id"] for row in _chain_heads(component_reviews, "supersedes_reviews")
    }:
        raise ValidationFailure("experiment receipt requires the current testimonial review")
    review_artifact = review["artifact"]
    if (
        review_artifact["artifact_id"] != artifact["artifact_id"]
        or review_artifact["artifact_sha256"] != artifact["sha256"]
        or review_artifact["build_id"] != build_id
        or review_artifact["render_job_id"] != render_job_id
        or review["normalization"]["normalized_verdict"] != human_review["verdict"]
        or review["reviewed_by"] != human_review["reviewer_id"]
        or review["reviewed_at"] != human_review["reviewed_at"]
    ):
        raise ValidationFailure(
            "testimonial review does not match the selected artifact and human verdict"
        )
    lineage = {
        "testimonial_id": testimonial["id"],
        "testimonial_record_hash": testimonial["record_hash"],
        "raw_statement_hash": testimonial["raw_statement_hash"],
        "testimonial_review_id": review["id"],
        "testimonial_review_record_hash": review["record_hash"],
        "artifact_id": artifact["artifact_id"],
        "artifact_sha256": artifact["sha256"],
        "normalized_verdict": review["normalization"]["normalized_verdict"],
    }
    return lineage, review


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_flight_design(flight: dict[str, Any]) -> None:
    arms = flight.get("arms", [])
    arm_ids = [arm.get("id") for arm in arms]
    if len(arm_ids) != len(set(arm_ids)):
        raise ValidationFailure("flight arm IDs must be unique")
    if flight.get("legacy") is not None:
        return
    design = flight.get("design")
    if not isinstance(design, dict):
        raise ValidationFailure("nonlegacy flight requires an experiment design")
    outcomes = set(design.get("outcome_concept_ids", []))
    if not outcomes <= set(flight.get("concept_ids", [])):
        raise ValidationFailure(
            "experiment outcome concepts must be sealed in the flight"
        )
    classification = design.get("classification")
    deltas = [arm.get("tested_delta") for arm in arms]
    if classification == "isolated_comparison":
        if len(arms) < 2 or any(not isinstance(delta, dict) for delta in deltas):
            raise ValidationFailure(
                "isolated comparison requires at least two arms with tested_delta"
            )
        concepts = {delta["concept_id"] for delta in deltas}
        controls = {delta["control_id"] for delta in deltas}
        values = {
            json.dumps(delta["value"], sort_keys=True, separators=(",", ":"))
            for delta in deltas
        }
        if len(concepts) != 1 or len(controls) != 1 or len(values) < 2:
            raise ValidationFailure(
                "isolated comparison arms must vary one shared concept/control across distinct values"
            )
        if not concepts <= set(flight.get("concept_ids", [])):
            raise ValidationFailure(
                "isolated comparison delta concept must be sealed in the flight"
            )
        if not outcomes or outcomes & concepts:
            raise ValidationFailure(
                "isolated comparison requires non-delta outcome concepts"
            )
    elif classification == "bundled_observation":
        if any(delta is not None for delta in deltas):
            raise ValidationFailure(
                "bundled observation arms cannot declare an isolated tested_delta"
            )
    else:
        raise ValidationFailure(f"unknown experiment classification: {classification}")


def _review_hash(review: dict[str, Any]) -> str:
    return sha256_value(
        {key: value for key, value in review.items() if key != "review_hash"}
    )


def _same_json_value(left: Any, right: Any) -> bool:
    return canonical_json_bytes(left) == canonical_json_bytes(right)


def _derive_metric_evidence(
    *,
    metrics: dict[str, Any],
    flight: dict[str, Any],
    score: dict[str, Any],
    verification_requirements: list[dict[str, Any]],
    compliance: dict[str, Any],
    testimonial_review: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Bind every sealed scalar metric to authored and observed evidence."""
    design_metric_ids = set(flight["design"]["metric_ids"])
    if set(metrics) != design_metric_ids:
        missing = sorted(design_metric_ids - set(metrics))
        extra = sorted(set(metrics) - design_metric_ids)
        details = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if extra:
            details.append("extra=" + ",".join(extra))
        raise ValidationFailure(
            "experiment metrics must exactly match the sealed design: "
            + "; ".join(details)
        )
    for metric_id, value in metrics.items():
        if isinstance(value, (dict, list)):
            raise ValidationFailure(
                f"experiment metric must be a scalar: {metric_id}"
            )

    requirements = {row["metric_id"]: row for row in verification_requirements}
    if len(requirements) != len(verification_requirements):
        raise ValidationFailure("verification metric requirements must be unique")
    checks = {row["metric_id"]: row for row in compliance["control_checks"]}
    if len(checks) != len(compliance["control_checks"]):
        raise ValidationFailure("compliance metric checks must be unique")
    traces = {row["assertion_id"]: row for row in compliance["evidence_trace"]}
    if len(traces) != len(compliance["evidence_trace"]):
        raise ValidationFailure("compliance evidence assertions must be unique")

    normalization = (
        testimonial_review["normalization"] if testimonial_review is not None else {}
    )
    findings_list = normalization.get("metric_findings", [])
    findings = {row["metric_id"]: row for row in findings_list}
    if len(findings) != len(findings_list):
        raise ValidationFailure("testimonial metric findings must be unique")
    extra_findings = sorted(set(findings) - design_metric_ids)
    if extra_findings:
        raise ValidationFailure(
            "testimonial review contains metrics outside the sealed design: "
            + ", ".join(extra_findings)
        )

    controls = {
        row["control_id"]: row for row in score["provider_neutral_controls"]
    }
    concept_hashes = flight["concept_content_hashes"]
    rows: list[dict[str, Any]] = []
    for metric_id in sorted(design_metric_ids):
        value = copy.deepcopy(metrics[metric_id])
        check = checks.get(metric_id)
        finding = findings.get(metric_id)
        if check is not None and finding is not None:
            raise ValidationFailure(
                f"metric has competing compliance and testimonial owners: {metric_id}"
            )

        authored: list[dict[str, Any]] = []
        observed: list[dict[str, Any]] = []
        status: str
        if check is not None:
            if check["status"] not in {"pass", "fail"}:
                raise ValidationFailure(
                    f"compliance metric is not observable enough to record: {metric_id}"
                )
            if not _same_json_value(value, check["status"]):
                raise ValidationFailure(
                    f"compliance-owned metric value must equal its deterministic status: {metric_id}"
                )
            requirement = requirements.get(metric_id)
            if requirement is None:
                raise ValidationFailure(
                    f"compliance metric lost its authored verification requirement: {metric_id}"
                )
            source_owner = requirement.get("source_profile") or requirement.get(
                "source_translation"
            )
            authored.append(
                {
                    "source_type": "verification_requirement",
                    "source_ref": f"{source_owner}#{metric_id}",
                    "source_hash": sha256_value(requirement),
                }
            )
            assertion_ids: set[str] = set()
            for target in check["targets"]:
                for control in target["expected_controls"]:
                    control_id = control["control_id"]
                    score_control = controls.get(control_id)
                    if score_control is None or any(
                        score_control.get(key) != control.get(key)
                        for key in ("control_id", "path", "value")
                    ):
                        raise ValidationFailure(
                            f"compliance metric references an unknown canonical control: {metric_id}"
                        )
                    authored.append(
                        {
                            "source_type": "canonical_control",
                            "source_ref": control_id,
                            "source_hash": sha256_value(score_control),
                        }
                    )
                assertion_ids.update(target["evidence_refs"])
            if not assertion_ids:
                raise ValidationFailure(
                    f"compliance metric has no admissible observed evidence: {metric_id}"
                )
            for assertion_id in sorted(assertion_ids):
                trace = traces.get(assertion_id)
                if trace is None or trace["verdict"] not in {"pass", "fail"}:
                    raise ValidationFailure(
                        f"compliance metric lost a valid evidence assertion: {metric_id}"
                    )
                observed.append(
                    {
                        "source_type": "verification_assertion",
                        "source_ref": assertion_id,
                        "source_hash": trace["source_hash"],
                        "evidence_hash": sha256_value(trace),
                        "lane": trace["lane"],
                        "evidence_class": trace["evidence_class"],
                        "verdict": trace["verdict"],
                        "confidence": trace["confidence"],
                    }
                )
            status = check["status"]
        elif finding is not None:
            if testimonial_review is None:
                raise ValidationFailure(
                    f"testimonial metric lost its reviewed source: {metric_id}"
                )
            if finding["verdict"] == "unobservable":
                raise ValidationFailure(
                    f"testimonial metric is unobservable and cannot be recorded: {metric_id}"
                )
            if not _same_json_value(value, finding["value"]):
                raise ValidationFailure(
                    f"testimonial metric value differs from its exact finding: {metric_id}"
                )
            for target in finding["authored_targets"]:
                target_type = target["target_type"]
                target_ref = target["target_ref"]
                if target_type == "concept":
                    target_hash = concept_hashes.get(target_ref)
                    source_type = "concept"
                else:
                    control = controls.get(target_ref)
                    target_hash = sha256_value(control) if control is not None else None
                    source_type = "canonical_control"
                if target_hash is None:
                    raise ValidationFailure(
                        f"testimonial metric target is not sealed in this run: {metric_id}:{target_ref}"
                    )
                authored.append(
                    {
                        "source_type": source_type,
                        "source_ref": target_ref,
                        "source_hash": target_hash,
                    }
                )
            normalizer_origin = normalization["normalizer"]["origin"]
            observed.append(
                {
                    "source_type": "testimonial_metric_finding",
                    "source_ref": testimonial_review["id"] + "#metric:" + metric_id,
                    "source_hash": testimonial_review["record_hash"],
                    "evidence_hash": sha256_value(finding),
                    "lane": "human_review",
                    "evidence_class": (
                        "authored"
                        if normalizer_origin == "human_authored"
                        else "interpreted"
                    ),
                    "verdict": finding["verdict"],
                    "confidence": finding["confidence"],
                }
            )
            status = finding["verdict"]
        else:
            raise ValidationFailure(
                f"experiment metric has no deterministic evidence owner: {metric_id}"
            )

        authored = sorted(
            {
                (row["source_type"], row["source_ref"]): row for row in authored
            }.values(),
            key=lambda row: (row["source_type"], row["source_ref"]),
        )
        rows.append(
            {
                "metric_id": metric_id,
                "value": value,
                "status": status,
                "authored_evidence": authored,
                "observed_evidence": sorted(
                    observed, key=lambda row: (row["source_type"], row["source_ref"])
                ),
            }
        )
    return rows


def _validate_nonlegacy_run(
    run: dict[str, Any], flight: dict[str, Any], arm: dict[str, Any]
) -> None:
    if run.get("legacy") is not None:
        return
    design = flight.get("design") or {}
    classification = design.get("classification")
    expected_eligibility = (
        "candidate"
        if classification == "isolated_comparison"
        else "ineligible_bundled"
    )
    evidence_design = run.get("evidence_design") or {}
    policy_version = evidence_design.get("policy_version")
    if policy_version not in {LEGACY_EVIDENCE_POLICY, EVIDENCE_POLICY}:
        raise ValidationFailure("run uses an unsupported controlled-evidence policy")
    if evidence_design != {
        "classification": classification,
        "causal_eligibility": expected_eligibility,
        "outcome_concept_ids": sorted(design.get("outcome_concept_ids", [])),
        "policy_version": policy_version,
    }:
        raise ValidationFailure("run evidence design does not match its sealed flight")
    if run.get("tested_delta") != arm.get("tested_delta"):
        raise ValidationFailure("run tested_delta does not match its sealed arm")
    delta = run.get("tested_delta")
    controls = run.get("controls")
    if classification == "isolated_comparison":
        if (
            not isinstance(delta, dict)
            or not isinstance(controls, dict)
            or delta.get("control_id") not in controls
            or controls[delta["control_id"]] != delta.get("value")
        ):
            raise ValidationFailure(
                "isolated run controls do not contain the declared tested value"
            )
    elif delta is not None:
        raise ValidationFailure("bundled run cannot claim an isolated tested_delta")
    lineage = run.get("evidence_lineage") or {}
    if run.get("output_artifact_hash") != lineage.get("artifact_sha256"):
        raise ValidationFailure("run artifact hash differs from evidence lineage")
    review = run.get("human_review") or {}
    if review.get("review_hash") != _review_hash(review):
        raise ValidationFailure("run human review hash is invalid")
    if run.get("verdict") != review.get("verdict"):
        raise ValidationFailure("run verdict differs from its human review")
    fingerprint_payload = {
        "flight_hash": run["flight_hash"],
        "arm": run["arm"],
        "lineage": lineage,
        "controls": run["controls"],
        "tested_delta": run["tested_delta"],
        "metrics": run["metrics"],
        "human_review": review,
    }
    metric_evidence = run.get("metric_evidence")
    if policy_version == EVIDENCE_POLICY:
        if not isinstance(metric_evidence, list):
            raise ValidationFailure("controlled-evidence 1.1 run requires metric evidence")
        metric_ids = [row.get("metric_id") for row in metric_evidence]
        if len(metric_ids) != len(set(metric_ids)) or set(metric_ids) != set(
            run["metrics"]
        ):
            raise ValidationFailure(
                "run metric evidence must map every metric exactly once"
            )
        for row in metric_evidence:
            if not _same_json_value(row.get("value"), run["metrics"][row["metric_id"]]):
                raise ValidationFailure(
                    f"run metric evidence value mismatch: {row['metric_id']}"
                )
            for key in ("authored_evidence", "observed_evidence"):
                sources = row.get(key)
                if not isinstance(sources, list) or not sources:
                    raise ValidationFailure(
                        f"run metric evidence has no {key}: {row['metric_id']}"
                    )
                identities = [
                    (source.get("source_type"), source.get("source_ref"))
                    for source in sources
                ]
                if len(identities) != len(set(identities)):
                    raise ValidationFailure(
                        f"run metric evidence repeats {key}: {row['metric_id']}"
                    )
        fingerprint_payload["metric_evidence"] = metric_evidence
    elif metric_evidence is not None:
        raise ValidationFailure(
            "controlled-evidence 1.0 run cannot claim 1.1 metric evidence"
        )
    testimonial_lineage = run.get("testimonial_lineage")
    if testimonial_lineage is not None:
        if (
            review.get("testimonial_review_id")
            != testimonial_lineage.get("testimonial_review_id")
            or lineage.get("artifact_id") != testimonial_lineage.get("artifact_id")
            or lineage.get("artifact_sha256")
            != testimonial_lineage.get("artifact_sha256")
            or review.get("verdict")
            != testimonial_lineage.get("normalized_verdict")
        ):
            raise ValidationFailure("run testimonial lineage is internally inconsistent")
        fingerprint_payload["testimonial_lineage"] = testimonial_lineage
    expected_fingerprint = sha256_value(fingerprint_payload)
    if (
        run.get("evidence_fingerprint") != expected_fingerprint
        or run.get("id")
        != "r_exp_" + expected_fingerprint.removeprefix("sha256:")[:20]
    ):
        raise ValidationFailure("run evidence fingerprint or content-derived ID is invalid")


@authority_writer("immutable")
def seal_flight(draft: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    """Seal and append a flight. Draft editing happens outside the immutable store."""
    path = root / "lab" / "second_brain" / "immutable" / "flights.jsonl"
    assert_write_target("record", path, root)
    rows = read_jsonl(path)
    flight = dict(draft)
    flight["status"] = "sealed"
    flight.setdefault("sealed_at", _utc_now())
    concepts = {
        row["id"]: row for row in read_jsonl(root / "lab" / "concepts.jsonl")
    }
    concept_ids = flight.get("concept_ids", [])
    missing = sorted(set(concept_ids) - set(concepts))
    if missing:
        raise ValidationFailure(
            "flight references missing concepts: " + ", ".join(missing)
        )
    flight["concept_content_hashes"] = {
        concept_id: sha256_value(concepts[concept_id])
        for concept_id in concept_ids
    }
    if flight.get("legacy") is None:
        compiler_version = flight.get("compiler_settings", {}).get("version")
        if (
            flight.get("seed") is None
            or not compiler_version
            or "legacy-unrecorded"
            in {
                flight.get("provider"),
                flight.get("model_version"),
                compiler_version,
            }
        ):
            raise ValidationFailure(
                "nonlegacy flight must seal a seed and exact provider, model, and compiler versions"
            )
        flight["design"] = copy.deepcopy(flight["design"])
        flight["design"]["metric_ids"] = sorted(
            set(flight["design"]["metric_ids"])
        )
        flight["design"]["outcome_concept_ids"] = sorted(
            set(flight["design"]["outcome_concept_ids"])
        )
    _validate_flight_design(flight)
    flight["flight_hash"] = content_hash(flight, ("flight_hash",))
    validate_instance("flight", flight, root)
    existing = next((row for row in rows if row["id"] == flight["id"]), None)
    if existing is not None:
        if existing == flight:
            return existing
        raise ValidationFailure(f"immutable flight ID collision: {flight['id']}")
    with path.open("ab") as handle:
        handle.write(canonical_json_bytes(flight))
    return flight


def prepare_experiment_flight(
    *,
    flight_id: str,
    arm_builds: list[dict[str, Any]],
    classification: str,
    metric_ids: list[str],
    outcome_concept_ids: list[str],
    provider: str,
    model_version: str,
    sealed_at: str,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Build a validated flight draft from exact materialized build directories."""
    if not arm_builds:
        raise ValidationFailure("experiment preparation requires at least one arm")
    if any(
        not isinstance(arm, dict)
        or not isinstance(arm.get("id"), str)
        or not arm["id"]
        or not isinstance(arm.get("build_dir"), (str, Path))
        for arm in arm_builds
    ):
        raise ValidationFailure("experiment arms require an ID and build directory")
    arm_ids = [arm["id"] for arm in arm_builds]
    if len(arm_ids) != len(set(arm_ids)):
        raise ValidationFailure("experiment arm IDs must be unique")
    arm_builds = sorted(copy.deepcopy(arm_builds), key=lambda arm: arm["id"])
    loaded = []
    for arm in arm_builds:
        build = load_validated_build_directory(Path(arm["build_dir"]), root)
        loaded.append((arm, build))
    first_manifest = loaded[0][1]["manifest"]
    shared_manifest_fields = (
        "concept_ids",
        "concept_hashes",
        "compiler_version",
        "seed",
    )
    for _arm, build in loaded[1:]:
        for field in shared_manifest_fields:
            if build["manifest"][field] != first_manifest[field]:
                raise ValidationFailure(
                    f"experiment arm builds disagree on sealed {field}"
                )
    domains = {
        build["score"]["normalized_intent"]["intent"]["primary_domain"]
        for _arm, build in loaded
    }
    if len(domains) != 1:
        raise ValidationFailure("experiment arm builds disagree on primary intent domain")
    control_maps = [
        {
            row["control_id"]: row["value"]
            for row in build["score"]["provider_neutral_controls"]
        }
        for _arm, build in loaded
    ]
    if any(set(controls) != set(control_maps[0]) for controls in control_maps[1:]):
        raise ValidationFailure("experiment arm builds expose different control identities")
    differing_controls = sorted(
        control_id
        for control_id in control_maps[0]
        if len(
            {
                json.dumps(
                    controls[control_id],
                    sort_keys=True,
                    separators=(",", ":"),
                )
                for controls in control_maps
            }
        )
        > 1
    )
    arms = []
    if classification == "isolated_comparison":
        if len(loaded) < 2 or len(differing_controls) != 1:
            raise ValidationFailure(
                "isolated experiment builds must differ on exactly one canonical control"
            )
        differing_control = differing_controls[0]
        delta_concepts = set()
        for (arm, _build), controls in zip(loaded, control_maps):
            delta = copy.deepcopy(arm.get("tested_delta"))
            if (
                not isinstance(delta, dict)
                or delta.get("control_id") != differing_control
                or delta.get("value") != controls[differing_control]
            ):
                raise ValidationFailure(
                    "isolated experiment arm delta does not match its build control"
                )
            delta_concepts.add(delta.get("concept_id"))
            arms.append(
                {
                    "id": arm["id"],
                    "paradigm": "universal_score",
                    "tested_delta": delta,
                }
            )
        if len(delta_concepts) != 1 or not delta_concepts <= set(
            first_manifest["concept_ids"]
        ):
            raise ValidationFailure(
                "isolated experiment delta must name one sealed concept"
            )
    elif classification == "bundled_observation":
        if any(arm.get("tested_delta") is not None for arm, _build in loaded):
            raise ValidationFailure("bundled experiment arms cannot declare tested deltas")
        arms = [
            {"id": arm["id"], "paradigm": "universal_score", "tested_delta": None}
            for arm, _build in loaded
        ]
    else:
        raise ValidationFailure(f"unsupported experiment classification: {classification}")
    draft = {
        "id": flight_id,
        "intent_id": None,
        "intent_class": next(iter(domains)),
        "arms": arms,
        "design": {
            "classification": classification,
            "causal_claim_policy": "isolated_only",
            "metric_ids": sorted(set(metric_ids)),
            "outcome_concept_ids": sorted(set(outcome_concept_ids)),
        },
        "concept_ids": copy.deepcopy(first_manifest["concept_ids"]),
        "provider": provider,
        "model_version": model_version,
        "seed": first_manifest["seed"],
        "compiler_settings": {"version": first_manifest["compiler_version"]},
        "sealed_at": sealed_at,
        "legacy": None,
    }
    preview = copy.deepcopy(draft)
    concepts = {
        row["id"]: row for row in read_jsonl(root / "lab" / "concepts.jsonl")
    }
    missing_concepts = sorted(set(preview["concept_ids"]) - set(concepts))
    if missing_concepts:
        raise ValidationFailure(
            "experiment builds reference missing concepts: "
            + ", ".join(missing_concepts)
        )
    current_hashes = {
        concept_id: sha256_value(concepts[concept_id])
        for concept_id in preview["concept_ids"]
    }
    if current_hashes != first_manifest["concept_hashes"]:
        raise ValidationFailure(
            "experiment build concept snapshot differs from current curated authority"
        )
    preview["status"] = "sealed"
    preview["concept_content_hashes"] = current_hashes
    preview["flight_hash"] = content_hash(preview, ("flight_hash",))
    _validate_flight_design(preview)
    validate_instance("flight", preview, root)
    result = {
        "schema": "cpcs.experiment_flight_preparation/1.0",
        "flight_draft": draft,
        "builds": [
            {
                "arm_id": arm["id"],
                "build_id": build["manifest"]["build_id"],
                "build_hash": build["manifest"]["build_hash"],
                "score_id": build["score"]["score_id"],
                "score_hash": build["manifest"]["score_hash"],
            }
            for arm, build in loaded
        ],
        "differing_control_ids": differing_controls,
    }
    validate_instance("experiment_flight_preparation", result, root)
    return result


@authority_writer("immutable")
def append_record(kind: str, record: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    """Append one hash-chained record. Replacement and deletion are intentionally absent."""
    if kind not in KIND_TO_FILE:
        raise ValidationFailure(f"unsupported immutable record kind: {kind}")
    path = root / "lab" / "second_brain" / "immutable" / KIND_TO_FILE[kind]
    assert_write_target("record", path, root)
    rows = read_jsonl(path)
    if any(row["id"] == record.get("id") for row in rows):
        raise ValidationFailure(f"immutable record ID already exists: {record.get('id')}")
    value = dict(record)
    value["prior_record_hash"] = rows[-1]["record_hash"] if rows else None
    if kind == "run":
        value.setdefault("recorded_at", _utc_now())
    else:
        value.setdefault("created_at", _utc_now())
    value["record_hash"] = content_hash(value)
    validate_instance(kind, value, root)
    with path.open("ab") as handle:
        handle.write(canonical_json_bytes(value))
    return value


def _append_run(
    record: dict[str, Any],
    root: Path,
    *,
    allow_verified_nonlegacy: bool,
) -> dict[str, Any]:
    if record.get("legacy") is None and not allow_verified_nonlegacy:
        raise ValidationFailure(
            "nonlegacy runs must enter through append_experiment_run with exact evidence"
        )
    flights = {row["id"]: row for row in read_jsonl(root / "lab" / "second_brain" / "immutable" / "flights.jsonl")}
    flight = flights.get(record.get("flight_id"))
    if not flight:
        raise ValidationFailure(f"run references unsealed flight: {record.get('flight_id')}")
    if record.get("flight_hash") != flight["flight_hash"]:
        raise ValidationFailure("run flight_hash does not match sealed flight")
    locked = {
        "intent_id": flight["intent_id"],
        "intent_class": flight["intent_class"],
        "concept_ids": flight["concept_ids"],
        "concept_content_hashes": flight["concept_content_hashes"],
        "provider": flight["provider"],
        "model_version": flight["model_version"],
        "seed": flight["seed"],
    }
    mismatches = [
        key for key, expected in locked.items() if record.get(key) != expected
    ]
    compiler_version = flight["compiler_settings"].get("version")
    if compiler_version is not None and record.get("compiler_version") != compiler_version:
        mismatches.append("compiler_version")
    arms = {arm["id"]: arm for arm in flight["arms"]}
    arm = arms.get(record.get("arm"))
    if arm is None:
        mismatches.append("arm")
    elif record.get("paradigm") != arm["paradigm"]:
        mismatches.append("paradigm")
    if mismatches:
        raise ValidationFailure(
            "run differs from sealed flight fields: "
            + ", ".join(sorted(set(mismatches)))
        )
    if record.get("legacy") is None and (
        record.get("seed") is None
        or record.get("output_artifact_hash") is None
        or "legacy-unrecorded"
        in {
            record.get("provider"),
            record.get("model_version"),
            record.get("compiler_version"),
        }
    ):
        raise ValidationFailure(
            "nonlegacy run must record seed, output hash, and exact versions"
        )
    if arm is not None:
        _validate_nonlegacy_run(record, flight, arm)
    return append_record("run", record, root)


@authority_writer("immutable")
def append_run(record: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    """Append a legacy migration run; controlled evidence uses append_experiment_run."""
    return _append_run(record, root, allow_verified_nonlegacy=False)


def _append_verified_run(
    record: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Internal sink reached only after exact experiment evidence validation."""
    return _append_run(record, root, allow_verified_nonlegacy=True)


def _load_json_object(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    expanded = path.expanduser()
    if expanded.is_symlink():
        raise ValidationFailure(f"{label} cannot be a symlink: {expanded}")
    resolved = expanded.resolve()
    if not resolved.is_file():
        raise ValidationFailure(f"{label} is unsafe or missing: {resolved}")
    raw = resolved.read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationFailure(f"{label} is not valid JSON: {resolved}") from exc
    if not isinstance(value, dict):
        raise ValidationFailure(f"{label} must contain one JSON object")
    return value, raw


def _prepare_experiment_run(
    *,
    flight_id: str,
    arm_id: str,
    build_dir: Path,
    render_result_path: Path,
    compliance_report_path: Path,
    artifact_id: str,
    metrics: dict[str, Any],
    human_review: dict[str, Any],
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Resolve and validate one experiment run without mutating authority."""
    flights = {
        row["id"]: row
        for row in read_jsonl(
            root / "lab" / "second_brain" / "immutable" / "flights.jsonl"
        )
    }
    flight = flights.get(flight_id)
    if flight is None or flight.get("legacy") is not None:
        raise ValidationFailure(f"experiment evidence requires a nonlegacy flight: {flight_id}")
    arms = {arm["id"]: arm for arm in flight["arms"]}
    arm = arms.get(arm_id)
    if arm is None:
        raise ValidationFailure(f"experiment evidence references unknown arm: {arm_id}")
    build = load_validated_build_directory(build_dir, root)
    manifest = build["manifest"]
    score = build["score"]
    render_result, render_bytes = _load_json_object(
        render_result_path, "render result"
    )
    compliance, compliance_bytes = _load_json_object(
        compliance_report_path, "compliance report"
    )
    validate_runtime_instance("render_result", render_result, root)
    validate_verification_instance("compliance_report", compliance, root)
    if compliance_bytes != canonical_json_bytes(compliance):
        raise ValidationFailure("compliance report must use canonical JSON bytes")
    compliance_core = {
        key: value for key, value in compliance.items() if key != "report_id"
    }
    expected_report_id = "compliance_" + hashlib.sha256(
        canonical_json_bytes(compliance_core)
    ).hexdigest()[:32]
    if compliance["report_id"] != expected_report_id:
        raise ValidationFailure("compliance report content identity is invalid")
    if (
        render_result["build_id"] != manifest["build_id"]
        or render_result["build_hash"] != manifest["build_hash"]
        or compliance["build_id"] != manifest["build_id"]
        or compliance["build_hash"] != manifest["build_hash"]
        or compliance["score_id"] != score["score_id"]
        or compliance["job_id"] != render_result["job_id"]
    ):
        raise ValidationFailure("build, render result, and compliance identities disagree")
    build_manifest_hash = sha256_bytes(build["artifact_bytes"]["build_manifest.json"])
    render_hash = sha256_bytes(render_bytes)
    if (
        compliance["input_hashes"]["build_manifest"] != build_manifest_hash
        or compliance["input_hashes"]["render_result"] != render_hash
    ):
        raise ValidationFailure("compliance report input hashes do not match supplied evidence")
    artifacts = [
        row for row in render_result["artifacts"] if row["artifact_id"] == artifact_id
    ]
    if len(artifacts) != 1:
        raise ValidationFailure("render result does not contain the selected artifact exactly once")
    artifact = artifacts[0]
    result_root = render_result_path.expanduser().resolve().parent
    artifact_candidate = result_root / artifact["relative_path"]
    if artifact_candidate.is_symlink():
        raise ValidationFailure("render artifact cannot be a symlink")
    artifact_path = artifact_candidate.resolve()
    if result_root not in artifact_path.parents or not artifact_path.is_file():
        raise ValidationFailure("render artifact path is unsafe or missing")
    artifact_bytes = artifact_path.read_bytes()
    if (
        len(artifact_bytes) != artifact["size_bytes"]
        or sha256_bytes(artifact_bytes) != artifact["sha256"]
        or compliance["artifact"]["artifact_id"] != artifact_id
        or compliance["artifact"]["sha256"] != artifact["sha256"]
        or compliance["input_hashes"]["artifact"] != artifact["sha256"]
    ):
        raise ValidationFailure("artifact bytes, render result, and compliance report disagree")
    if (
        manifest["concept_ids"] != flight["concept_ids"]
        or manifest["concept_hashes"] != flight["concept_content_hashes"]
        or manifest["seed"] != flight["seed"]
        or manifest["compiler_version"] != flight["compiler_settings"].get("version")
        or render_result["provider"] != flight["provider"]
        or render_result["model"] != flight["model_version"]
    ):
        raise ValidationFailure("validated build/render evidence differs from sealed flight")
    required_review_fields = {
        "review_id",
        "reviewer_id",
        "verdict",
        "rationale",
        "reviewed_at",
    }
    allowed_review_fields = required_review_fields | {"testimonial_review_id"}
    if not required_review_fields <= set(human_review) or not set(
        human_review
    ) <= allowed_review_fields:
        raise ValidationFailure(
            "human review requires the base fields and only permits testimonial_review_id as an extension"
        )
    normalized_review = {
        key: copy.deepcopy(human_review.get(key))
        for key in sorted(human_review)
    }
    if any(value is None for value in normalized_review.values()):
        raise ValidationFailure("human review is missing a required field")
    normalized_review["review_hash"] = _review_hash(normalized_review)
    controls = {
        row["control_id"]: copy.deepcopy(row["value"])
        for row in score["provider_neutral_controls"]
    }
    delta = copy.deepcopy(arm.get("tested_delta"))
    if delta is not None and (
        delta["control_id"] not in controls
        or controls[delta["control_id"]] != delta["value"]
    ):
        raise ValidationFailure("build score does not realize its sealed arm delta")
    lineage = {
        "build_id": manifest["build_id"],
        "build_hash": manifest["build_hash"],
        "score_id": score["score_id"],
        "score_hash": manifest["score_hash"],
        "request_hash": score["provenance"]["request_hash"],
        "intent_hash": score["provenance"]["intent_hash"],
        "context_hash": score["provenance"]["context_hash"],
        "profile_hashes": copy.deepcopy(manifest["profile_hashes"]),
        "block_hashes": copy.deepcopy(manifest["block_hashes"]),
        "asset_hashes": {
            row["asset_id"]: row["content_hash"] for row in score["assets"]
        },
        "render_job_id": render_result["job_id"],
        "render_result_hash": render_hash,
        "artifact_id": artifact_id,
        "artifact_sha256": artifact["sha256"],
        "provider_response_hash": render_result["provider_response_hash"],
        "compliance_report_id": compliance["report_id"],
        "compliance_report_hash": sha256_bytes(compliance_bytes),
        "compliance_status": compliance["overall_status"],
        "verification_evidence_hash": compliance["input_hashes"]["evidence_bundle"],
    }
    testimonial_lineage = None
    testimonial_review = None
    testimonial_review_id = normalized_review.get("testimonial_review_id")
    if testimonial_review_id is not None:
        testimonial_lineage, testimonial_review = _resolve_testimonial_lineage(
            review_id=testimonial_review_id,
            artifact=artifact,
            build_id=manifest["build_id"],
            render_job_id=render_result["job_id"],
            human_review=normalized_review,
            root=root,
        )
    metric_evidence = _derive_metric_evidence(
        metrics=metrics,
        flight=flight,
        score=score,
        verification_requirements=build["verification_plan"]["requirements"],
        compliance=compliance,
        testimonial_review=testimonial_review,
    )
    evidence_design = {
        "classification": flight["design"]["classification"],
        "causal_eligibility": (
            "candidate"
            if flight["design"]["classification"] == "isolated_comparison"
            else "ineligible_bundled"
        ),
        "outcome_concept_ids": copy.deepcopy(
            flight["design"]["outcome_concept_ids"]
        ),
        "policy_version": EVIDENCE_POLICY,
    }
    fingerprint_payload = {
        "flight_hash": flight["flight_hash"],
        "arm": arm_id,
        "lineage": lineage,
        "controls": controls,
        "tested_delta": delta,
        "metrics": metrics,
        "metric_evidence": metric_evidence,
        "human_review": normalized_review,
    }
    if testimonial_lineage is not None:
        fingerprint_payload["testimonial_lineage"] = testimonial_lineage
    fingerprint = sha256_value(fingerprint_payload)
    run_id = "r_exp_" + fingerprint.removeprefix("sha256:")[:20]
    existing = next(
        (
            row
            for row in read_jsonl(
                root / "lab" / "second_brain" / "immutable" / "runs.jsonl"
            )
            if row["id"] == run_id
        ),
        None,
    )
    if existing is not None:
        if existing.get("evidence_fingerprint") != fingerprint:
            raise ValidationFailure(f"immutable run ID collision: {run_id}")
        return existing
    run = {
        "id": run_id,
        "flight_id": flight["id"],
        "flight_hash": flight["flight_hash"],
        "intent_id": flight["intent_id"],
        "intent_class": flight["intent_class"],
        "arm": arm_id,
        "paradigm": arm["paradigm"],
        "concept_ids": copy.deepcopy(flight["concept_ids"]),
        "concept_content_hashes": copy.deepcopy(flight["concept_content_hashes"]),
        "provider": render_result["provider"],
        "model_version": render_result["model"],
        "seed": manifest["seed"],
        "compiled_prompt_hash": manifest["artifact_hashes"]["prompt.txt"],
        "compiler_version": manifest["compiler_version"],
        "repository_commit": manifest["repository_commit"],
        "output_artifact_hash": artifact["sha256"],
        "metrics": copy.deepcopy(metrics),
        "metric_evidence": metric_evidence,
        "controls": controls,
        "tested_delta": delta,
        "verdict": normalized_review["verdict"],
        "evidence_fingerprint": fingerprint,
        "evidence_design": evidence_design,
        "evidence_lineage": lineage,
        "human_review": normalized_review,
        "recorded_at": normalized_review["reviewed_at"],
        "legacy": None,
    }
    if testimonial_lineage is not None:
        run["testimonial_lineage"] = testimonial_lineage
    return run


@authority_writer("immutable")
def append_prepared_experiment_run(
    run: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Append one internally prepared run, or return its exact immutable replay."""
    if run.get("legacy") is not None:
        raise ValidationFailure("prepared experiment run cannot be legacy evidence")
    flights = {
        row["id"]: row
        for row in read_jsonl(
            root / "lab" / "second_brain" / "immutable" / "flights.jsonl"
        )
    }
    flight = flights.get(run.get("flight_id"))
    if flight is None or flight.get("flight_hash") != run.get("flight_hash"):
        raise ValidationFailure("prepared experiment run lost its sealed flight")
    arm = next(
        (row for row in flight["arms"] if row["id"] == run.get("arm")), None
    )
    if arm is None:
        raise ValidationFailure("prepared experiment run lost its sealed arm")
    _validate_nonlegacy_run(run, flight, arm)
    existing = next(
        (
            row
            for row in read_jsonl(
                root / "lab" / "second_brain" / "immutable" / "runs.jsonl"
            )
            if row["id"] == run["id"]
        ),
        None,
    )
    if existing is not None:
        comparable = {
            key: value
            for key, value in existing.items()
            if key not in {"prior_record_hash", "record_hash"}
        }
        requested = {
            key: value
            for key, value in run.items()
            if key not in {"prior_record_hash", "record_hash"}
        }
        if comparable != requested:
            raise ValidationFailure(f"immutable run ID collision: {run['id']}")
        return existing
    return _append_verified_run(copy.deepcopy(run), root)


@authority_reader("experiment_receipt_preflight")
def prepare_experiment_receipt(
    receipt: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Preflight exact receipt bytes and return the run that admission would append."""
    validate_instance("experiment_receipt", receipt, root)
    return _prepare_experiment_run(
        flight_id=receipt["flight_id"],
        arm_id=receipt["arm_id"],
        build_dir=Path(receipt["build_dir"]),
        render_result_path=Path(receipt["render_result"]),
        compliance_report_path=Path(receipt["compliance_report"]),
        artifact_id=receipt["artifact_id"],
        metrics=receipt["metrics"],
        human_review=receipt["human_review"],
        root=root,
    )


@authority_writer("immutable")
def append_experiment_run(
    *,
    flight_id: str,
    arm_id: str,
    build_dir: Path,
    render_result_path: Path,
    compliance_report_path: Path,
    artifact_id: str,
    metrics: dict[str, Any],
    human_review: dict[str, Any],
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Bind one verified render into an idempotent, immutable experiment run."""
    prepared = _prepare_experiment_run(
        flight_id=flight_id,
        arm_id=arm_id,
        build_dir=build_dir,
        render_result_path=render_result_path,
        compliance_report_path=compliance_report_path,
        artifact_id=artifact_id,
        metrics=metrics,
        human_review=human_review,
        root=root,
    )
    return append_prepared_experiment_run(prepared, root)


def append_experiment_receipt(
    receipt: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Validate the public receipt before resolving its evidence paths."""
    validate_instance("experiment_receipt", receipt, root)
    return append_experiment_run(
        flight_id=receipt["flight_id"],
        arm_id=receipt["arm_id"],
        build_dir=Path(receipt["build_dir"]),
        render_result_path=Path(receipt["render_result"]),
        compliance_report_path=Path(receipt["compliance_report"]),
        artifact_id=receipt["artifact_id"],
        metrics=receipt["metrics"],
        human_review=receipt["human_review"],
        root=root,
    )


@authority_writer("immutable")
def append_improvement_orchestration(
    value: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Append one completed accepted-experiment orchestration or replay it exactly."""
    path = (
        root
        / "lab"
        / "second_brain"
        / "immutable"
        / "improvement_orchestrations.jsonl"
    )
    rows = read_jsonl(path)
    existing_flight = next(
        (
            row
            for row in rows
            if row["flight"]["flight_id"] == value.get("flight", {}).get("flight_id")
        ),
        None,
    )
    if existing_flight is not None and existing_flight["id"] != value.get("id"):
        raise ValidationFailure("experiment flight already has an accepted orchestration")
    return _append_content_record(
        path=path,
        schema_name="improvement_orchestration",
        value=copy.deepcopy(value),
        root=root,
    )


def append_pegasus_observation(record: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    if record.get("evidence_class") not in {"inferred", "interpreted"}:
        raise ValidationFailure("Pegasus semantic evidence must be inferred or interpreted")
    return append_record("pegasus_observation", record, root)


def append_measurement_observation(record: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    return append_record("measurement_observation", record, root)


@authority_writer("immutable")
def append_measurement_batch(
    batch: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Atomically append a validated extraction batch or replay it idempotently."""
    validate_measurement_batch(batch, root)
    path = root / "lab" / "second_brain" / "immutable" / KIND_TO_FILE["measurement_observation"]
    assert_write_target("record", path, root)
    drafts = copy.deepcopy(batch["observations"])
    draft_ids = [row["id"] for row in drafts]
    if len(draft_ids) != len(set(draft_ids)):
        raise ValidationFailure("measurement batch observation IDs must be unique")
    concepts = {
        row["id"] for row in read_jsonl(root / "lab" / "concepts.jsonl")
    }
    missing = sorted(
        {
            concept_id
            for row in drafts
            for concept_id in row.get("concept_ids", [])
            if concept_id not in concepts
        }
    )
    if missing:
        raise ValidationFailure(
            "measurement batch references missing curated concepts: " + ", ".join(missing)
        )
    rows = read_jsonl(path)
    existing = {row["id"]: row for row in rows}
    prior_hash = rows[-1]["record_hash"] if rows else None
    resolved: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    for draft in drafts:
        previous = existing.get(draft["id"])
        if previous is not None:
            comparable = {
                key: value
                for key, value in previous.items()
                if key not in {"prior_record_hash", "record_hash"}
            }
            comparable.pop("measurement_batch_id", None)
            if comparable != draft or previous.get("measurement_batch_id") != batch["batch_id"]:
                raise ValidationFailure(
                    f"immutable measurement ID collision: {draft['id']}"
                )
            resolved.append(previous)
            continue
        value = dict(draft)
        value["measurement_batch_id"] = batch["batch_id"]
        value["prior_record_hash"] = prior_hash
        value["record_hash"] = content_hash(value)
        validate_instance("measurement_observation", value, root)
        prior_hash = value["record_hash"]
        pending.append(value)
        resolved.append(value)
    if pending:
        payload = b"".join(canonical_json_bytes(value) for value in pending)
        with path.open("ab") as handle:
            handle.write(payload)
            handle.flush()
    return {
        "schema": "cpcs.measurement_recording/1.0",
        "batch_id": batch["batch_id"],
        "disposition": "appended" if pending else "already_present",
        "appended_count": len(pending),
        "records": resolved,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("seal-flight", "run", "pegasus", "measurement"):
        item = sub.add_parser(command)
        item.add_argument("record", type=Path, help="JSON object file")
    experiment = sub.add_parser("experiment")
    experiment.add_argument(
        "receipt",
        type=Path,
        help="JSON receipt naming flight, arm, build, render, compliance, metrics, and review",
    )
    experiment.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="repository root (defaults to the active CPCS repository)",
    )
    args = parser.parse_args(argv)
    source = args.receipt if args.command == "experiment" else args.record
    value = json.loads(source.read_text())
    if args.command == "seal-flight":
        result = seal_flight(value)
    elif args.command == "run":
        result = append_run(value)
    elif args.command == "pegasus":
        result = append_pegasus_observation(value)
    elif args.command == "experiment":
        result = append_experiment_receipt(value, args.root.expanduser().resolve())
    else:
        result = append_measurement_observation(value)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
