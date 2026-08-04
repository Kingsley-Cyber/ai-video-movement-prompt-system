"""Content-hashed authority and online SQLite backup/restore."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from lab.second_brain.src.authority import authority_writer
from lab.second_brain.src.validate import REPO_ROOT, canonical_json_bytes

from .contracts import (
    load_release_policy,
    validate_release_instance,
)

MANIFEST_NAME = "backup_manifest.json"


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _revision(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    revision = completed.stdout.strip()
    if len(revision) != 40:
        raise ValueError("source revision is not a full commit SHA")
    return revision


def _state_sources(root: Path) -> list[tuple[Path, str]]:
    explicit = (
        (root / "lab" / "concepts.jsonl", "authority"),
        (root / "lab" / "blocks.yaml", "prompt_lab"),
        (root / "lab" / "registry.yaml", "prompt_lab"),
        (root / "lab" / "runs" / "results.csv", "prompt_lab"),
    )
    rows = list(explicit)
    sb = root / "lab" / "second_brain"
    for tier, kind in (
        ("curated", "authority"),
        ("immutable", "authority"),
        ("staging", "staging"),
    ):
        rows.extend(
            (path, kind)
            for path in sorted((sb / tier).rglob("*"))
            if path.is_file()
        )
    missing = [str(path.relative_to(root)) for path, _ in rows if not path.is_file()]
    if missing:
        raise ValueError("backup source is missing: " + ", ".join(missing))
    symlinks = [str(path.relative_to(root)) for path, _ in rows if path.is_symlink()]
    if symlinks:
        raise ValueError("backup source cannot be a symlink: " + ", ".join(symlinks))
    deduped = {path.resolve(): (path, kind) for path, kind in rows}
    return sorted(deduped.values(), key=lambda row: str(row[0].relative_to(root)))


def _copy_state(
    root: Path, target: Path, sources: Iterable[tuple[Path, str]]
) -> list[dict[str, Any]]:
    rows = []
    for source, kind in sources:
        relative = source.relative_to(root)
        destination = target / "state" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        rows.append(
            {
                "path": (PurePosixPath("state") / PurePosixPath(relative.as_posix())).as_posix(),
                "kind": kind,
                "sha256": _sha256(destination),
                "size_bytes": destination.stat().st_size,
            }
        )
    return rows


def _backup_journal(source: Path, destination: Path) -> dict[str, Any]:
    expanded = source.expanduser()
    if expanded.is_symlink() or not expanded.resolve().is_file():
        raise ValueError("render journal is missing or is a symlink")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_uri = f"file:{expanded.resolve()}?mode=ro"
    with sqlite3.connect(source_uri, uri=True) as source_db, sqlite3.connect(
        destination
    ) as target_db:
        source_db.backup(target_db)
        integrity = target_db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError(f"render journal backup failed integrity check: {integrity}")
    return {
        "path": "operational/render_jobs.sqlite3",
        "kind": "render_journal",
        "sha256": _sha256(destination),
        "size_bytes": destination.stat().st_size,
    }


@authority_writer("backup_snapshot")
def create_backup(
    target: Path,
    *,
    created_at: str,
    journal_path: Path | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Create one non-overwriting backup and return its validated manifest."""
    root = root.resolve()
    destination = target.expanduser()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"backup target already exists: {destination}")
    destination = destination.resolve()
    if destination in {root, Path.home().resolve(), Path("/")}:
        raise ValueError("backup target is too broad")
    destination.mkdir(parents=True)
    policy, policy_hash = load_release_policy(root)
    files = _copy_state(root, destination, _state_sources(root))
    if journal_path is not None:
        files.append(
            _backup_journal(
                journal_path,
                destination / "operational" / "render_jobs.sqlite3",
            )
        )
    files.sort(key=lambda row: row["path"])
    core = {
        "schema": "cpcs.backup_manifest/1.0",
        "created_at": created_at,
        "source_revision": _revision(root),
        "policy_hash": policy_hash,
        "files": files,
        "derived_rebuild_required": policy["backup"]["derived_state"] == "rebuild",
    }
    digest = hashlib.sha256(canonical_json_bytes(core)).hexdigest()
    manifest = {
        **core,
        "backup_id": "backup_" + digest[:24],
        "manifest_hash": "sha256:" + digest,
    }
    validate_release_instance("backup_manifest", manifest, root)
    (destination / MANIFEST_NAME).write_bytes(canonical_json_bytes(manifest))
    verify_backup(destination, root=root)
    return manifest


def _safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.parts[0] not in {
        "state",
        "operational",
    }:
        raise ValueError(f"unsafe backup path: {value}")
    return path


def verify_backup(backup: Path, *, root: Path = REPO_ROOT) -> dict[str, Any]:
    directory = backup.expanduser().resolve()
    manifest_path = directory / MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("backup manifest is missing or is a symlink")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_release_instance("backup_manifest", manifest, root)
    core = {
        key: value
        for key, value in manifest.items()
        if key not in {"backup_id", "manifest_hash"}
    }
    digest = hashlib.sha256(canonical_json_bytes(core)).hexdigest()
    if (
        manifest["backup_id"] != "backup_" + digest[:24]
        or manifest["manifest_hash"] != "sha256:" + digest
    ):
        raise ValueError("backup manifest content identity is invalid")
    seen: set[str] = set()
    for row in manifest["files"]:
        relative = _safe_relative(row["path"])
        if row["path"] in seen:
            raise ValueError(f"duplicate backup path: {row['path']}")
        seen.add(row["path"])
        path = directory.joinpath(*relative.parts)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"backup file is missing or unsafe: {row['path']}")
        if path.stat().st_size != row["size_bytes"] or _sha256(path) != row["sha256"]:
            raise ValueError(f"backup file hash or size differs: {row['path']}")
        if row["kind"] == "render_journal":
            with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
                if integrity != "ok":
                    raise ValueError(f"backup journal integrity failed: {integrity}")
    return manifest


def restore_backup(
    backup: Path, destination: Path, *, root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Restore into one new directory; overwriting any existing target is forbidden."""
    manifest = verify_backup(backup, root=root)
    target = destination.expanduser()
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"restore destination already exists: {target}")
    target = target.resolve()
    if target in {root.resolve(), Path.home().resolve(), Path("/")}:
        raise ValueError("restore destination is too broad")
    target.mkdir(parents=True)
    source_root = backup.expanduser().resolve()
    restored = []
    for row in manifest["files"]:
        relative = _safe_relative(row["path"])
        source = source_root.joinpath(*relative.parts)
        if relative.parts[0] == "state":
            output = target.joinpath(*relative.parts[1:])
        else:
            output = target / "work" / "render_jobs.sqlite3"
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, output)
        if _sha256(output) != row["sha256"]:
            raise ValueError(f"restored file hash differs: {row['path']}")
        restored.append(str(output.relative_to(target)))
    return {
        "schema": "cpcs.restore_result/1.0",
        "backup_id": manifest["backup_id"],
        "destination": str(target),
        "restored": sorted(restored),
        "derived_rebuild_required": manifest["derived_rebuild_required"],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("target", type=Path)
    create.add_argument("--created-at", required=True)
    create.add_argument("--journal", type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("backup", type=Path)
    restore = sub.add_parser("restore")
    restore.add_argument("backup", type=Path)
    restore.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    if args.command == "create":
        result = create_backup(
            args.target, created_at=args.created_at, journal_path=args.journal
        )
    elif args.command == "verify":
        result = verify_backup(args.backup)
    else:
        result = restore_backup(args.backup, args.destination)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
