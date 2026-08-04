"""Deterministic local security and release-policy checks."""

from __future__ import annotations

import argparse
import configparser
import json
import re
from pathlib import Path
from typing import Any

from lab.application.http import MAX_REQUEST_BYTES
from lab.second_brain.src.validate import REPO_ROOT

from .contracts import load_release_policy

FORBIDDEN_SOURCE_PATTERNS = {
    "dynamic_eval": re.compile(r"\beval\s*\("),
    "dynamic_exec": re.compile(r"\bexec\s*\("),
    "pickle_load": re.compile(r"\bpickle\.loads?\s*\("),
    "shell_true": re.compile(r"\bshell\s*=\s*True\b"),
    "os_system": re.compile(r"\bos\.system\s*\("),
    "unsafe_yaml": re.compile(r"\byaml\.load\s*\("),
    "stdlib_xml_parser": re.compile(r"\bxml\.etree\b"),
}


def _locked_versions(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line or any(token in line for token in ("@", ">", "<", "~=")):
            raise ValueError(f"dependency lock is not exact: {line}")
        name, version = line.split("==", 1)
        normalized = name.strip().lower().replace("_", "-")
        if normalized in rows:
            raise ValueError(f"duplicate locked dependency: {normalized}")
        if not version.strip():
            raise ValueError(f"dependency lock has no version: {normalized}")
        rows[normalized] = version.strip()
    return rows


def _declared_runtime_dependencies(root: Path) -> dict[str, str]:
    parser = configparser.ConfigParser()
    parser.read(root / "setup.cfg")
    raw = parser["options"]["install_requires"]
    rows = {}
    for line in raw.splitlines():
        value = line.strip()
        if not value:
            continue
        name, version = value.split("==", 1)
        rows[name.lower().replace("_", "-")] = version
    return rows


def _declared_extra_dependencies(root: Path, extra: str) -> dict[str, str]:
    parser = configparser.ConfigParser()
    parser.read(root / "setup.cfg")
    raw = parser["options.extras_require"][extra]
    rows = {}
    for line in raw.splitlines():
        value = line.strip()
        if not value:
            continue
        name, version = value.split("==", 1)
        rows[name.lower().replace("_", "-")] = version
    return rows


def _source_findings(root: Path) -> list[dict[str, Any]]:
    findings = []
    scopes = (
        root / "lab" / "application",
        root / "lab" / "compiler",
        root / "lab" / "runtime",
        root / "lab" / "second_brain" / "src",
        root / "lab" / "verification",
        root / "lab" / "release",
        root / "lab" / "scripts",
    )
    for scope in scopes:
        for path in sorted(scope.rglob("*.py")):
            if "tests" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for rule, pattern in FORBIDDEN_SOURCE_PATTERNS.items():
                for match in pattern.finditer(text):
                    findings.append(
                        {
                            "rule": rule,
                            "path": str(path.relative_to(root)),
                            "line": text.count("\n", 0, match.start()) + 1,
                        }
                    )
    return findings


def scan(root: Path = REPO_ROOT) -> dict[str, Any]:
    root = root.resolve()
    policy, policy_hash = load_release_policy(root)
    core_lock = _locked_versions(root / "requirements.lock")
    provider_lock = _locked_versions(root / "requirements-providers.lock")
    measurement_lock = _locked_versions(root / "requirements-measurement.lock")
    declared = _declared_runtime_dependencies(root)
    declared_measurement = _declared_extra_dependencies(root, "measurement")
    lock_mismatches = {
        name: {"declared": version, "locked": core_lock.get(name)}
        for name, version in declared.items()
        if core_lock.get(name) != version
    }
    findings = _source_findings(root)
    authority_roots = [
        root / "lab" / "concepts.jsonl",
        root / "lab" / "second_brain" / "curated",
        root / "lab" / "second_brain" / "immutable",
        root / "lab" / "second_brain" / "staging",
    ]
    symlinks = [
        str(path.relative_to(root))
        for authority in authority_roots
        for path in ([authority] if authority.is_file() else authority.rglob("*"))
        if path.is_symlink()
    ]
    rights_files = (
        root / "lab" / "compiler" / "schemas" / "score_request.schema.json",
        root / "lab" / "second_brain" / "schemas" / "retrieved_passages.schema.json",
        root / "lab" / "second_brain" / "src" / "source_extract.py",
    )
    missing_rights_contracts = [
        str(path.relative_to(root))
        for path in rights_files
        if "rights_basis" not in path.read_text(encoding="utf-8")
    ]
    failures = []
    if findings:
        failures.append("forbidden_source_patterns")
    if lock_mismatches:
        failures.append("runtime_lock_mismatch")
    if symlinks:
        failures.append("authority_symlinks")
    if missing_rights_contracts:
        failures.append("rights_contract_missing")
    if MAX_REQUEST_BYTES != policy["limits"]["http_request_bytes"]:
        failures.append("http_limit_policy_drift")
    if set(provider_lock) != {"google-auth", "twelvelabs"}:
        failures.append("provider_lock_scope_drift")
    if measurement_lock != declared_measurement:
        failures.append("measurement_lock_scope_drift")
    return {
        "schema": "cpcs.security_report/1.0",
        "policy_hash": policy_hash,
        "status": "passed" if not failures else "failed",
        "failures": failures,
        "source_findings": findings,
        "lock_mismatches": lock_mismatches,
        "authority_symlinks": symlinks,
        "missing_rights_contracts": missing_rights_contracts,
        "core_locked_dependencies": len(core_lock),
        "provider_locked_dependencies": len(provider_lock),
        "measurement_locked_dependencies": len(measurement_lock),
        "privacy": {
            "persistent_user_context": policy["privacy"]["persistent_user_context"],
            "raw_prompt_telemetry": policy["privacy"]["raw_prompt_telemetry"],
        },
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    result = scan()
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
