"""Deterministic local security and release-policy checks."""

from __future__ import annotations

import argparse
import configparser
import json
import os
import re
from pathlib import Path
from typing import Any

from lab.application.http import MAX_REQUEST_BYTES
from lab.application.ui import (
    MAX_REQUEST_BYTES as UI_MAX_REQUEST_BYTES,
    MAX_UPLOAD_BYTES,
    SESSION_IDLE_SECONDS,
    WORKSPACE_RETENTION_SECONDS,
)
from lab.second_brain.src.curation_journal import (
    CurationJournalError,
    curation_journal_status,
)
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
    context_root = root / "work" / "application" / "contexts"
    context_database = context_root / "profiles.sqlite3"
    context_storage_findings = []
    if context_root.is_symlink():
        context_storage_findings.append("context_directory_symlink")
    elif context_root.exists() and context_root.stat().st_mode & 0o777 != 0o700:
        context_storage_findings.append("context_directory_mode")
    if context_database.is_symlink():
        context_storage_findings.append("context_database_symlink")
    elif context_database.exists():
        context_stat = context_database.stat()
        if not context_database.is_file() or context_stat.st_nlink != 1:
            context_storage_findings.append("context_database_link_or_type")
        if context_stat.st_mode & 0o777 != 0o600:
            context_storage_findings.append("context_database_mode")
    if context_root.exists() and not context_root.is_symlink():
        context_storage_findings.extend(
            "context_child_symlink"
            for path in context_root.iterdir()
            if path.is_symlink()
        )
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
    try:
        curation_status = curation_journal_status(root)
        curation_status_error = None
    except CurationJournalError as error:
        curation_status = None
        curation_status_error = str(error)
    failures = []
    if findings:
        failures.append("forbidden_source_patterns")
    if lock_mismatches:
        failures.append("runtime_lock_mismatch")
    if symlinks:
        failures.append("authority_symlinks")
    if missing_rights_contracts:
        failures.append("rights_contract_missing")
    if context_storage_findings:
        failures.append("context_storage_unsafe")
    if MAX_REQUEST_BYTES != policy["limits"]["http_request_bytes"]:
        failures.append("http_limit_policy_drift")
    if UI_MAX_REQUEST_BYTES != policy["limits"]["http_request_bytes"]:
        failures.append("local_ui_request_limit_policy_drift")
    if MAX_UPLOAD_BYTES != policy["limits"]["local_ui_upload_bytes"]:
        failures.append("local_ui_upload_limit_policy_drift")
    if SESSION_IDLE_SECONDS != policy["runtime"]["local_ui_session_idle_seconds"]:
        failures.append("local_ui_session_limit_policy_drift")
    if WORKSPACE_RETENTION_SECONDS != policy["privacy"]["work_retention_days"] * 86400:
        failures.append("local_ui_retention_policy_drift")
    if set(provider_lock) != {"google-auth", "twelvelabs"}:
        failures.append("provider_lock_scope_drift")
    if measurement_lock != declared_measurement:
        failures.append("measurement_lock_scope_drift")
    if os.name != "posix":
        failures.append("authority_locking_unsupported")
    if curation_status_error is not None:
        failures.append("curation_journal_unsafe")
    elif curation_status is not None and (
        curation_status["active"] or curation_status["preparing"]
    ):
        failures.append("curation_recovery_pending")
    return {
        "schema": "cpcs.security_report/1.0",
        "policy_hash": policy_hash,
        "status": "passed" if not failures else "failed",
        "failures": failures,
        "source_findings": findings,
        "lock_mismatches": lock_mismatches,
        "authority_symlinks": symlinks,
        "missing_rights_contracts": missing_rights_contracts,
        "context_storage_findings": context_storage_findings,
        "core_locked_dependencies": len(core_lock),
        "provider_locked_dependencies": len(provider_lock),
        "measurement_locked_dependencies": len(measurement_lock),
        "authority_locking": policy["runtime"]["authority_locking"],
        "authority_read_isolation": policy["runtime"]["authority_read_isolation"],
        "curation_recovery": policy["runtime"]["curation_recovery"],
        "curation_journal": curation_status,
        "curation_journal_error": curation_status_error,
        "qualification_trusted_evaluators": sorted(
            policy["qualification_trust"]["trusted_evaluators"]
        ),
        "privacy": {
            "persistent_user_context": policy["privacy"]["persistent_user_context"],
            "context_storage": policy["privacy"]["context_storage"],
            "context_access_boundary": policy["privacy"]["context_access_boundary"],
            "context_encryption": policy["privacy"]["context_encryption"],
            "context_retention_days": policy["privacy"]["context_retention_days"],
            "local_ui_session": policy["privacy"]["local_ui_session"],
            "local_ui_identity": policy["privacy"]["local_ui_identity"],
            "local_ui_reference_storage": policy["privacy"]["local_ui_reference_storage"],
            "local_ui_reference_retention": policy["privacy"]["local_ui_reference_retention"],
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
