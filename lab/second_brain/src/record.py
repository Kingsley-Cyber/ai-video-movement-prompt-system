"""Append-only APIs for sealed flights, runs, and evidence observations."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
EVIDENCE_POLICY = "cpcs-controlled-evidence/1.0"


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
    if evidence_design != {
        "classification": classification,
        "causal_eligibility": expected_eligibility,
        "outcome_concept_ids": sorted(design.get("outcome_concept_ids", [])),
        "policy_version": EVIDENCE_POLICY,
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
    expected_fingerprint = sha256_value(
        {
            "flight_hash": run["flight_hash"],
            "arm": run["arm"],
            "lineage": lineage,
            "controls": run["controls"],
            "tested_delta": run["tested_delta"],
            "metrics": run["metrics"],
            "human_review": review,
        }
    )
    if (
        run.get("evidence_fingerprint") != expected_fingerprint
        or run.get("id")
        != "r_exp_" + expected_fingerprint.removeprefix("sha256:")[:20]
    ):
        raise ValidationFailure("run evidence fingerprint or content-derived ID is invalid")


def seal_flight(draft: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    """Seal and append a flight. Draft editing happens outside the immutable store."""
    path = root / "lab" / "second_brain" / "immutable" / "flights.jsonl"
    assert_write_target("record", path, root)
    rows = read_jsonl(path)
    if any(row["id"] == draft.get("id") for row in rows):
        raise ValidationFailure(f"immutable flight ID already exists: {draft.get('id')}")
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
    with path.open("ab") as handle:
        handle.write(canonical_json_bytes(flight))
    return flight


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
    review_fields = {
        "review_id",
        "reviewer_id",
        "verdict",
        "rationale",
        "reviewed_at",
    }
    if set(human_review) != review_fields:
        raise ValidationFailure(
            "human review fields must be exactly: " + ", ".join(sorted(review_fields))
        )
    normalized_review = {
        key: copy.deepcopy(human_review.get(key))
        for key in sorted(review_fields)
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
    design_metric_ids = set(flight["design"]["metric_ids"])
    observed_metric_ids = set(metrics) | {
        row["metric_id"] for row in compliance["control_checks"]
    }
    missing_metrics = sorted(design_metric_ids - observed_metric_ids)
    if missing_metrics:
        raise ValidationFailure(
            "experiment evidence omits sealed metrics: " + ", ".join(missing_metrics)
        )
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
    fingerprint = sha256_value(
        {
            "flight_hash": flight["flight_hash"],
            "arm": arm_id,
            "lineage": lineage,
            "controls": controls,
            "tested_delta": delta,
            "metrics": metrics,
            "human_review": normalized_review,
        }
    )
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
    return _append_verified_run(run, root)


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


def append_pegasus_observation(record: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    if record.get("evidence_class") not in {"inferred", "interpreted"}:
        raise ValidationFailure("Pegasus semantic evidence must be inferred or interpreted")
    return append_record("pegasus_observation", record, root)


def append_measurement_observation(record: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    return append_record("measurement_observation", record, root)


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
