"""Explicit render-journal schema inspection and forward migration."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from lab.runtime.journal import JOURNAL_SCHEMA_VERSION, JobJournal, JournalError

from .backup import verify_backup


def inspect_journal(path: Path) -> dict[str, Any]:
    expanded = path.expanduser()
    if expanded.is_symlink():
        raise JournalError("render journal cannot be a symlink")
    if not expanded.exists():
        return {
            "schema": "cpcs.migration_status/1.0",
            "path": str(expanded),
            "exists": False,
            "current_version": 0,
            "supported_version": JOURNAL_SCHEMA_VERSION,
            "migration_required": False,
        }
    with sqlite3.connect(f"file:{expanded.resolve()}?mode=ro", uri=True) as connection:
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    return {
        "schema": "cpcs.migration_status/1.0",
        "path": str(expanded.resolve()),
        "exists": True,
        "current_version": version,
        "supported_version": JOURNAL_SCHEMA_VERSION,
        "migration_required": version < JOURNAL_SCHEMA_VERSION,
    }


def migrate_journal(path: Path, *, backup: Path | None = None) -> dict[str, Any]:
    before = inspect_journal(path)
    if before["current_version"] > JOURNAL_SCHEMA_VERSION:
        raise JournalError("journal downgrade is forbidden")
    if before["exists"] and before["migration_required"]:
        if backup is None:
            raise JournalError("an existing journal must be backed up before migration")
        manifest = verify_backup(backup)
        if not any(row["kind"] == "render_journal" for row in manifest["files"]):
            raise JournalError("migration backup does not contain the render journal")
    journal = JobJournal(path)
    return {
        "schema": "cpcs.migration_result/1.0",
        "before": before,
        "after": journal.schema_status(),
        "backup_id": (
            verify_backup(backup)["backup_id"] if backup is not None else None
        ),
        "downgrade_supported": False,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("journal", type=Path)
    migrate = sub.add_parser("migrate")
    migrate.add_argument("journal", type=Path)
    migrate.add_argument("--backup", type=Path)
    args = parser.parse_args(argv)
    result = (
        inspect_journal(args.journal)
        if args.command == "status"
        else migrate_journal(args.journal, backup=args.backup)
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
