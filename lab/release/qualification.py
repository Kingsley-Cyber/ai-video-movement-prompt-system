"""Generate a categorical local-release qualification report."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from lab.application.contracts import validate_application_configuration
from lab.compiler.build import validate_build_configuration
from lab.compiler.score import validate_configuration as validate_compiler_configuration
from lab.runtime.contracts import validate_runtime_configuration
from lab.runtime.journal import JobJournal
from lab.second_brain.src.validate import REPO_ROOT, canonical_json_bytes
from lab.verification.verify import validate_verification_configuration

from .backup import create_backup, restore_backup, verify_backup
from .contracts import (
    load_release_policy,
    validate_release_configuration,
    validate_release_instance,
)
from .security import scan

EXTERNAL_GATES = (
    "closed_world_annotation",
    "calibration",
    "held_out",
    "provider",
    "graph_write_promotion",
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _gate(
    gate: str,
    status: str,
    evidence: list[str],
    blocker: str | None = None,
) -> dict[str, Any]:
    return {
        "gate": gate,
        "status": status,
        "evidence": evidence,
        "blocker": blocker,
    }


def _recoverability(root: Path) -> list[str]:
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        journal_path = base / "source" / "render_jobs.sqlite3"
        journal = JobJournal(journal_path)
        if journal.schema_status()["current_version"] != 1:
            raise ValueError("render journal migration did not reach version 1")
        backup_path = base / "backup"
        manifest = create_backup(
            backup_path,
            created_at="2000-01-01T00:00:00Z",
            journal_path=journal_path,
            root=root,
        )
        verified = verify_backup(backup_path, root=root)
        restored = restore_backup(backup_path, base / "restored", root=root)
        if manifest != verified or not restored["derived_rebuild_required"]:
            raise ValueError("backup verification or restore disposition differs")
        return [
            manifest["backup_id"],
            manifest["manifest_hash"],
            f"restored_files:{len(restored['restored'])}",
        ]


def _remote_matches(root: Path, revision: str) -> tuple[bool, str]:
    branch = _git(root, "branch", "--show-current")
    if not branch:
        return False, "detached HEAD has no remote branch evidence"
    output = _git(root, "ls-remote", "--heads", "origin", branch)
    remote = output.split()[0] if output else ""
    return remote == revision, f"origin/{branch}:{remote or 'missing'}"


def _external_rows(
    evidence: dict[str, Any] | None,
    revision: str,
    prior_gates: list[dict[str, Any]],
    root: Path,
) -> list[dict[str, Any]]:
    if evidence is not None:
        validate_release_instance("external_qualification_evidence", evidence, root)
        if evidence["source_revision"] != revision:
            raise ValueError("external qualification evidence targets another revision")
    supplied = (evidence or {}).get("gates", {})
    rows = []
    for name in EXTERNAL_GATES[:-1]:
        item = supplied.get(name)
        if item is None:
            rows.append(
                _gate(
                    name,
                    "blocked_external",
                    [],
                    "signed evaluation evidence was not supplied",
                )
            )
        else:
            rows.append(
                _gate(
                    name,
                    "passed" if item["status"] == "passed" else "failed",
                    [item["evaluator"], *item["artifact_hashes"], item["summary"]],
                    None if item["status"] == "passed" else item["summary"],
                )
            )
    promotion = supplied.get("graph_write_promotion")
    dependencies = [*prior_gates, *rows]
    if any(row["status"] != "passed" for row in dependencies):
        rows.append(
            _gate(
                "graph_write_promotion",
                "blocked_external",
                [],
                "all local, annotation, calibration, held-out, and provider gates must pass first",
            )
        )
    elif promotion is None:
        rows.append(
            _gate(
                "graph_write_promotion",
                "blocked_external",
                [],
                "explicit graph-write promotion evidence was not supplied",
            )
        )
    else:
        rows.append(
            _gate(
                "graph_write_promotion",
                "passed" if promotion["status"] == "passed" else "failed",
                [
                    promotion["evaluator"],
                    *promotion["artifact_hashes"],
                    promotion["summary"],
                ],
                None if promotion["status"] == "passed" else promotion["summary"],
            )
        )
    return rows


def assess(
    *,
    root: Path = REPO_ROOT,
    external_evidence: dict[str, Any] | None = None,
    check_remote: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    policy, policy_hash = load_release_policy(root)
    revision = _git(root, "rev-parse", "HEAD")
    dirty = bool(_git(root, "status", "--porcelain"))
    setup = (root / "setup.cfg").read_text(encoding="utf-8")
    local_gates = [
        _gate(
            "engineering_freeze",
            "passed"
            if not dirty and f"version = {policy['release_version']}" in setup
            else "failed",
            [revision, f"release_version:{policy['release_version']}"],
            None if not dirty else "working tree is not clean",
        )
    ]
    try:
        recovery_evidence = _recoverability(root)
        local_gates.append(_gate("recoverability", "passed", recovery_evidence))
    except Exception as exc:
        local_gates.append(_gate("recoverability", "failed", [], str(exc)))
    remote_evidence = "remote check not requested"
    remote_ok = False
    if check_remote:
        try:
            remote_ok, remote_evidence = _remote_matches(root, revision)
        except Exception as exc:
            remote_evidence = str(exc)
    reproducible = not dirty and remote_ok
    local_gates.append(
        _gate(
            "git_reproducibility",
            "passed" if reproducible else "pending",
            [revision, remote_evidence, _hash(root / "requirements.lock")],
            None if reproducible else "clean local and matching remote heads are required",
        )
    )
    try:
        configuration = {
            "application": validate_application_configuration(root),
            "compiler": validate_compiler_configuration(root),
            "build": validate_build_configuration(root),
            "runtime": validate_runtime_configuration(root),
            "verification": validate_verification_configuration(root),
            "release": validate_release_configuration(root),
        }
        local_gates.append(
            _gate(
                "schema",
                "passed",
                [json.dumps(configuration, sort_keys=True, separators=(",", ":"))],
            )
        )
    except Exception as exc:
        local_gates.append(_gate("schema", "failed", [], str(exc)))
    security = scan(root)
    local_gates.append(
        _gate(
            "security",
            "passed" if security["status"] == "passed" else "failed",
            [json.dumps(security, sort_keys=True, separators=(",", ":"))],
            None if security["status"] == "passed" else ", ".join(security["failures"]),
        )
    )
    gates = [
        *local_gates,
        *_external_rows(external_evidence, revision, local_gates, root),
    ]
    artifacts = {
        path.name: _hash(path)
        for path in (
            root / "pyproject.toml",
            root / "setup.cfg",
            root / "requirements.lock",
            root / "requirements-providers.lock",
            root / "lab" / "release" / "policy.yaml",
        )
    }
    core = {
        "schema": "cpcs.qualification_report/1.0",
        "release_version": policy["release_version"],
        "release_class": policy["release_class"],
        "source_revision": revision,
        "dirty": dirty,
        "policy_hash": policy_hash,
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "sqlite": sqlite3.sqlite_version,
        },
        "artifacts": artifacts,
        "gates": gates,
        "overall_status": (
            "qualified"
            if all(row["status"] == "passed" for row in gates)
            else "not_qualified"
        ),
    }
    report = {
        **core,
        "report_hash": "sha256:"
        + hashlib.sha256(canonical_json_bytes(core)).hexdigest(),
    }
    validate_release_instance("qualification_report", report, root)
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-evidence", type=Path)
    parser.add_argument("--check-remote", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    external = (
        json.loads(args.external_evidence.read_text(encoding="utf-8"))
        if args.external_evidence
        else None
    )
    report = assess(external_evidence=external, check_remote=args.check_remote)
    if args.output:
        output = args.output.expanduser().resolve()
        work = (REPO_ROOT / "work").resolve()
        if output == work or work not in output.parents or output.exists():
            raise ValueError("qualification output must be a new file under work/")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical_json_bytes(report))
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["overall_status"] != "qualified":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
