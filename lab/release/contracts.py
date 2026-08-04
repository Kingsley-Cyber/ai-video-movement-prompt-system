"""Release policy and artifact contract validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from lab.second_brain.src.validate import REPO_ROOT, sha256_value

SCHEMAS = {
    "backup_manifest": "backup_manifest.schema.json",
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
    validator = Draft202012Validator(load_release_schema(name, root))
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
    }
    if set(value) != required or value["schema"] != "cpcs.release_policy/1.0":
        raise ValueError("release policy keys or schema are invalid")
    if value["release_class"] != "local_single_worker":
        raise ValueError("only the bounded local_single_worker release is admitted")
    if value["authority"] != "not_production_qualified":
        raise ValueError("local policy cannot claim production authority")
    if value["runtime"]["worker_limit"] != 1:
        raise ValueError("local release worker_limit must remain one")
    limit_keys = {
        "http_request_bytes",
        "context_token_budget",
        "external_evidence_items",
        "generation_sample_count",
        "generation_duration_seconds",
        "generation_seconds_per_request",
        "analysis_seconds_per_request",
        "provider_batch_items",
        "render_timeout_seconds",
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
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    print(json.dumps(validate_release_configuration(), sort_keys=True))


if __name__ == "__main__":
    main()
