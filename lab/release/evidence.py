"""Sign and verify revision-bound external qualification evidence bundles."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from lab.second_brain.src.validate import REPO_ROOT, canonical_json_bytes, sha256_value

from .contracts import load_release_policy, validate_release_instance

SECRET_ENV_PREFIX = "CPCS_QUALIFICATION_KEY_"


def secret_environment_name(evaluator_id: str) -> str:
    return SECRET_ENV_PREFIX + evaluator_id.upper()


def _signing_core(evidence: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in evidence.items() if key != "attestation"}


def _secret_bytes(secret: str | bytes) -> bytes:
    value = secret.encode("utf-8") if isinstance(secret, str) else secret
    if not isinstance(value, bytes) or len(value) < 32:
        raise ValueError("qualification attestation secret must be at least 32 bytes")
    return value


def _secret_hash(secret: bytes) -> str:
    return "sha256:" + hashlib.sha256(secret).hexdigest()


def sign_external_evidence(
    core: dict[str, Any], secret: str | bytes, root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Return one schema-valid HMAC-attested evidence record."""
    if "attestation" in core:
        raise ValueError("unsigned qualification evidence cannot contain attestation")
    key = _secret_bytes(secret)
    mac = hmac.new(key, canonical_json_bytes(core), hashlib.sha256).hexdigest()
    record = {
        **core,
        "attestation": {"algorithm": "hmac-sha256", "mac": mac},
    }
    validate_release_instance("external_qualification_evidence", record, root)
    return record


def _safe_artifact_path(bundle_root: Path, relative_path: str) -> Path:
    if "\\" in relative_path:
        raise ValueError("qualification artifact paths must use POSIX separators")
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError("qualification artifact path is not a safe relative path")
    base = bundle_root.expanduser()
    if base.is_symlink() or not base.resolve().is_dir():
        raise ValueError("qualification evidence root is missing or is a symlink")
    base = base.resolve()
    candidate = base.joinpath(*relative.parts)
    resolved = candidate.resolve()
    if base not in resolved.parents:
        raise ValueError("qualification artifact escapes the evidence root")
    cursor = candidate
    while cursor != base:
        if cursor.is_symlink():
            raise ValueError("qualification artifact path cannot contain a symlink")
        cursor = cursor.parent
    if not candidate.is_file():
        raise ValueError(f"qualification artifact is missing: {relative_path}")
    return candidate


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _trusted_secret(
    evaluator_id: str,
    policy: dict[str, Any],
    environment: Mapping[str, str],
) -> bytes:
    trusted = policy["qualification_trust"]["trusted_evaluators"]
    registered = trusted.get(evaluator_id)
    if registered is None:
        raise ValueError("qualification evidence evaluator is not trusted by policy")
    env_name = secret_environment_name(evaluator_id)
    supplied = environment.get(env_name)
    if supplied is None:
        raise ValueError(f"qualification attestation key is unavailable: {env_name}")
    secret = _secret_bytes(supplied)
    if not hmac.compare_digest(_secret_hash(secret), registered["secret_sha256"]):
        raise ValueError("qualification attestation key does not match policy")
    return secret


def verify_external_evidence(
    evidence: dict[str, Any],
    bundle_root: Path,
    *,
    root: Path = REPO_ROOT,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Verify trust, HMAC, safe file locations, sizes, and hashes."""
    validate_release_instance("external_qualification_evidence", evidence, root)
    active_policy = load_release_policy(root)[0]
    if active_policy["qualification_trust"]["algorithm"] != "hmac-sha256":
        raise ValueError("qualification evidence algorithm is not admitted by policy")
    evaluator_id = evidence["evaluator_id"]
    evaluator_policy = active_policy["qualification_trust"][
        "trusted_evaluators"
    ].get(evaluator_id)
    if evaluator_policy is None:
        raise ValueError("qualification evidence evaluator is not trusted by policy")
    unauthorized_gates = set(evidence["gates"]) - set(
        evaluator_policy["allowed_gates"]
    )
    if unauthorized_gates:
        raise ValueError(
            "qualification evaluator is not trusted for gates: "
            + ", ".join(sorted(unauthorized_gates))
        )
    secret = _trusted_secret(
        evaluator_id, active_policy, environment if environment is not None else os.environ
    )
    expected_mac = hmac.new(
        secret,
        canonical_json_bytes(_signing_core(evidence)),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(evidence["attestation"]["mac"], expected_mac):
        raise ValueError("qualification evidence attestation is invalid")

    limits = active_policy["limits"]
    artifact_limit = limits["external_evidence_items"]
    byte_limit = limits["qualification_evidence_bytes"]
    artifacts_by_gate: dict[str, list[str]] = {}
    unique_artifacts: dict[str, tuple[str, int]] = {}
    total_bytes = 0
    for gate_name in sorted(evidence["gates"]):
        gate_hashes = []
        for artifact in evidence["gates"][gate_name]["artifacts"]:
            relative_path = artifact["path"]
            previous = unique_artifacts.get(relative_path)
            declared_identity = (artifact["sha256"], artifact["size_bytes"])
            if previous is not None:
                if previous != declared_identity:
                    raise ValueError(
                        "qualification artifact path has conflicting identities"
                    )
                gate_hashes.append(previous[0])
                continue
            if len(unique_artifacts) >= artifact_limit:
                raise ValueError(
                    "qualification evidence exceeds the artifact-count limit"
                )
            path = _safe_artifact_path(bundle_root, relative_path)
            actual_size = path.stat().st_size
            if actual_size != artifact["size_bytes"]:
                raise ValueError(
                    f"qualification artifact size differs: {relative_path}"
                )
            if total_bytes + actual_size > byte_limit:
                raise ValueError(
                    "qualification evidence exceeds the total-byte limit"
                )
            actual_hash = _file_hash(path)
            if not hmac.compare_digest(actual_hash, artifact["sha256"]):
                raise ValueError(
                    f"qualification artifact hash differs: {relative_path}"
                )
            identity = (actual_hash, actual_size)
            unique_artifacts[relative_path] = identity
            total_bytes += actual_size
            gate_hashes.append(actual_hash)
        artifacts_by_gate[gate_name] = sorted(set(gate_hashes))

    return {
        "evaluator_id": evaluator_id,
        "attestation_hash": sha256_value(evidence["attestation"]),
        "artifact_hashes_by_gate": artifacts_by_gate,
        "artifact_count": len(unique_artifacts),
        "total_bytes": total_bytes,
    }


def _load_json(path: Path, max_bytes: int) -> dict[str, Any]:
    if path.stat().st_size > max_bytes:
        raise ValueError("qualification evidence manifest exceeds its byte limit")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("qualification evidence must be a JSON object")
    return value


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    sign = subparsers.add_parser("sign")
    sign.add_argument("input", type=Path)
    sign.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("input", type=Path)
    args = parser.parse_args(argv)
    supplied_input = args.input.expanduser()
    if supplied_input.is_symlink() or not supplied_input.resolve().is_file():
        raise ValueError("qualification evidence input is missing or a symlink")
    input_path = supplied_input.resolve()
    policy = load_release_policy()[0]
    manifest_limit = policy["limits"]["qualification_manifest_bytes"]
    if args.command == "sign":
        output = args.output.expanduser().resolve()
        if output.exists() or output.parent != input_path.parent:
            raise ValueError("signed evidence output must be new and beside its input")
        core = _load_json(input_path, manifest_limit)
        evaluator_id = core.get("evaluator_id")
        if not isinstance(evaluator_id, str):
            raise ValueError("unsigned evidence requires evaluator_id")
        secret = _trusted_secret(evaluator_id, policy, os.environ)
        record = sign_external_evidence(core, secret)
        summary = verify_external_evidence(record, input_path.parent)
        output.write_bytes(canonical_json_bytes(record))
        output.chmod(0o600)
    else:
        record = _load_json(input_path, manifest_limit)
        summary = verify_external_evidence(record, input_path.parent)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
