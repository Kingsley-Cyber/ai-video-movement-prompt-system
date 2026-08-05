"""Release policy and artifact contract validation."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from lab.second_brain.src.validate import REPO_ROOT, sha256_value

SCHEMAS = {
    "backup_manifest": "backup_manifest.schema.json",
    "evaluator_stability_request": "evaluator_stability_request.schema.json",
    "evaluator_stability_report": "evaluator_stability_report.schema.json",
    "external_qualification_evidence": "external_qualification_evidence.schema.json",
    "qualification_report": "qualification_report.schema.json",
    "telemetry_event": "telemetry_event.schema.json",
}


def load_release_schema(name: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    if name not in SCHEMAS:
        raise ValueError(f"unknown release schema: {name}")
    return json.loads(
        (root / "lab" / "release" / "schemas" / SCHEMAS[name]).read_text(
            encoding="utf-8"
        )
    )


def validate_release_instance(
    name: str, value: Any, root: Path = REPO_ROOT
) -> None:
    validator = Draft202012Validator(
        load_release_schema(name, root), format_checker=FormatChecker()
    )
    errors = sorted(
        validator.iter_errors(value), key=lambda item: list(item.absolute_path)
    )
    if errors:
        detail = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValueError(f"{SCHEMAS[name]}: {detail}")


def load_release_policy(root: Path = REPO_ROOT) -> tuple[dict[str, Any], str]:
    path = root / "lab" / "release" / "policy.yaml"
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("release policy must be an object")
    required = {
        "schema",
        "release_version",
        "release_class",
        "authority",
        "runtime",
        "limits",
        "privacy",
        "rights",
        "backup",
        "qualification_gates",
        "qualification_trust",
    }
    if set(value) != required or value["schema"] != "cpcs.release_policy/1.9":
        raise ValueError("release policy keys or schema are invalid")
    if value["release_class"] != "local_single_worker":
        raise ValueError("only the bounded local_single_worker release is admitted")
    if value["authority"] != "not_production_qualified":
        raise ValueError("local policy cannot claim production authority")
    runtime = value["runtime"]
    if not isinstance(runtime, dict) or set(runtime) != {
        "python_min",
        "python_ci",
        "worker_limit",
        "http_bind",
        "installed_command",
        "installed_ui_command",
        "local_ui_session_idle_seconds",
        "authority_locking",
        "authority_read_isolation",
        "curation_recovery",
    }:
        raise ValueError("release runtime policy has an invalid field set")
    if runtime["worker_limit"] != 1:
        raise ValueError("local release worker_limit must remain one")
    if runtime["installed_ui_command"] != "cpcs-ui":
        raise ValueError("local UI command must remain explicit")
    if runtime["local_ui_session_idle_seconds"] != 1800:
        raise ValueError("local UI session idle boundary must remain 1800 seconds")
    if runtime["authority_locking"] != "posix_flock":
        raise ValueError("local release authority locking must remain posix_flock")
    if runtime["authority_read_isolation"] != "posix_shared_flock":
        raise ValueError(
            "local release authority read isolation must remain posix_shared_flock"
        )
    if runtime["curation_recovery"] != "write_ahead_rollback":
        raise ValueError("local release curation recovery must remain write_ahead_rollback")
    limit_keys = {
        "http_request_bytes",
        "local_ui_upload_bytes",
        "context_token_budget",
        "external_evidence_items",
        "qualification_manifest_bytes",
        "qualification_evidence_bytes",
        "generation_sample_count",
        "generation_duration_seconds",
        "generation_seconds_per_request",
        "analysis_seconds_per_request",
        "provider_batch_items",
        "render_timeout_seconds",
        "context_profile_count",
        "context_profile_versions",
        "context_profile_bytes",
        "polymath_response_bytes",
        "polymath_query_bytes",
        "polymath_rights_basis_bytes",
        "polymath_passages",
        "polymath_passage_bytes",
        "polymath_total_passage_bytes",
        "polymath_timeout_seconds",
    }
    limits = value["limits"]
    if not isinstance(limits, dict) or set(limits) != limit_keys:
        raise ValueError("release limits have an invalid field set")
    if any(
        not isinstance(limits[key], int) or isinstance(limits[key], bool) or limits[key] <= 0
        for key in limit_keys
    ):
        raise ValueError("release limits must be positive integers")
    if limits["generation_seconds_per_request"] != (
        limits["generation_sample_count"] * limits["generation_duration_seconds"]
    ):
        raise ValueError("generation-seconds limit must equal samples times duration")
    if limits["context_profile_versions"] < limits["context_profile_count"]:
        raise ValueError("context profile version limit cannot be lower than profile count")
    if limits["context_profile_bytes"] < 1024:
        raise ValueError("context profile byte limit is too small for the public contract")
    privacy = value["privacy"]
    if not isinstance(privacy, dict) or set(privacy) != {
        "persistent_user_context",
        "context_storage",
        "context_access_boundary",
        "context_encryption",
        "context_retention_days",
        "local_ui_session",
        "local_ui_identity",
        "local_ui_reference_storage",
        "local_ui_reference_retention",
        "polymath_credentials",
        "polymath_queries",
        "polymath_enrichment",
        "raw_prompt_telemetry",
        "telemetry_fields",
        "work_retention_days",
    }:
        raise ValueError("release privacy policy has an invalid field set")
    if privacy["persistent_user_context"] != "local_typed_overlays":
        raise ValueError("only local typed context overlays are admitted")
    if privacy["context_storage"] != "ignored_work_sqlite":
        raise ValueError("context profiles must remain in ignored work SQLite state")
    if privacy["context_access_boundary"] != "local_os_account_and_process_role":
        raise ValueError("context access must remain local and process-role bounded")
    if privacy["context_encryption"] != "filesystem_permissions_only":
        raise ValueError("the local context encryption limitation must remain explicit")
    if privacy["raw_prompt_telemetry"] != "forbidden":
        raise ValueError("raw prompt telemetry must remain forbidden")
    if privacy["local_ui_session"] != "one_time_bootstrap_http_only_same_site_cookie_csrf":
        raise ValueError("local UI session policy is invalid")
    if privacy["local_ui_identity"] != "local_os_account_process":
        raise ValueError("local UI identity boundary is invalid")
    if privacy["local_ui_reference_storage"] != "ignored_session_workspace":
        raise ValueError("local UI reference storage boundary is invalid")
    if privacy["local_ui_reference_retention"] != "clean_shutdown_or_work_retention":
        raise ValueError("local UI reference retention boundary is invalid")
    if privacy["polymath_credentials"] != "environment_only_never_persisted":
        raise ValueError("Polymath credentials must remain environment-only")
    if privacy["polymath_queries"] != "exact_authorized_external_read":
        raise ValueError("Polymath queries must remain exact-authorized external reads")
    if privacy["polymath_enrichment"] != "exact_authorized_gap_only_ephemeral":
        raise ValueError("Polymath context enrichment must remain gap-only and ephemeral")
    for key in ("context_retention_days", "work_retention_days"):
        if (
            not isinstance(privacy[key], int)
            or isinstance(privacy[key], bool)
            or privacy[key] <= 0
        ):
            raise ValueError("privacy retention limits must be positive integers")
    if privacy["context_retention_days"] > privacy["work_retention_days"]:
        raise ValueError("context retention cannot exceed general work retention")
    trust = value["qualification_trust"]
    if not isinstance(trust, dict) or set(trust) != {
        "algorithm",
        "trusted_evaluators",
    }:
        raise ValueError("qualification trust policy has an invalid field set")
    if trust["algorithm"] != "hmac-sha256":
        raise ValueError("qualification trust algorithm must be hmac-sha256")
    evaluators = trust["trusted_evaluators"]
    if not isinstance(evaluators, dict) or len(evaluators) > 16:
        raise ValueError("trusted evaluator registry must be a bounded object")
    admitted_gates = {
        "closed_world_annotation",
        "calibration",
        "held_out",
        "provider",
        "graph_write_promotion",
    }
    expected_qualification_gates = {
        "engineering_freeze": "local",
        "recoverability": "local",
        "git_reproducibility": "local_and_remote",
        "schema": "local",
        "security": "local",
        "evaluator_stability_preflight": "local_supporting_evidence",
        "closed_world_annotation": "external_evidence",
        "calibration": "external_evidence_plus_stability_preflight",
        "held_out": "external_evidence_plus_stability_preflight",
        "provider": "external_evidence",
        "graph_write_promotion": "depends_on_all_prior",
    }
    if value["qualification_gates"] != expected_qualification_gates:
        raise ValueError("release qualification gates are invalid")
    for evaluator_id, evaluator in evaluators.items():
        if not isinstance(evaluator_id, str) or not re.fullmatch(
            r"[a-z][a-z0-9_]{2,63}", evaluator_id
        ):
            raise ValueError("trusted evaluator ID is invalid")
        if not isinstance(evaluator, dict) or set(evaluator) != {
            "secret_sha256",
            "allowed_gates",
        }:
            raise ValueError("trusted evaluator policy has an invalid field set")
        if not isinstance(evaluator["secret_sha256"], str) or not re.fullmatch(
            r"sha256:[0-9a-f]{64}", evaluator["secret_sha256"]
        ):
            raise ValueError("trusted evaluator secret hash is invalid")
        allowed = evaluator["allowed_gates"]
        if (
            not isinstance(allowed, list)
            or not allowed
            or len(allowed) != len(set(allowed))
            or not set(allowed) <= admitted_gates
        ):
            raise ValueError("trusted evaluator gate scope is invalid")
    return value, sha256_value(value)


def validate_release_configuration(root: Path = REPO_ROOT) -> dict[str, Any]:
    for name in SCHEMAS:
        Draft202012Validator.check_schema(load_release_schema(name, root))
    policy, policy_hash = load_release_policy(root)
    return {
        "schemas": len(SCHEMAS),
        "policy": policy["schema"],
        "policy_hash": policy_hash,
        "release_class": policy["release_class"],
        "authority_locking": policy["runtime"]["authority_locking"],
        "authority_read_isolation": policy["runtime"]["authority_read_isolation"],
        "curation_recovery": policy["runtime"]["curation_recovery"],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    print(json.dumps(validate_release_configuration(), sort_keys=True))


if __name__ == "__main__":
    main()
