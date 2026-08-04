"""Versioned local user and project context profiles under ignored work state."""

from __future__ import annotations

import copy
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from lab.compiler.score import validate_overlay
from lab.release.contracts import load_release_policy
from lab.second_brain.src.validate import REPO_ROOT, canonical_json_bytes, sha256_value

from .contracts import validate_application_instance

CONTEXT_PROFILE_SCHEMA = "cpcs.context_profile/1.0"
CONTEXT_STORE_SCHEMA = "cpcs.context_profile_store/1.0"
CONTEXT_ID_PATTERN = re.compile(r"context_[A-Za-z0-9._-]{3,80}")
PROJECT_ID_PATTERN = re.compile(r"[a-z][a-z0-9-]{4,28}[a-z0-9]")
UTC_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def _utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not UTC_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must be an exact UTC second ending in Z")
    parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    if parsed.tzinfo != timezone.utc:
        raise ValueError(f"{field} must be UTC")
    return parsed


def _record_hash(record: dict[str, Any]) -> str:
    value = {
        key: copy.deepcopy(item)
        for key, item in record.items()
        if key != "profile_hash"
    }
    return sha256_value(value)


class ContextProfileStore:
    """SQLite-backed typed overlays for one local operating-system user."""

    def __init__(
        self,
        root: Path = REPO_ROOT,
        *,
        database_path: Path | None = None,
    ) -> None:
        self.root = root.resolve()
        policy, _ = load_release_policy(self.root)
        self.retention_days = policy["privacy"]["context_retention_days"]
        self.max_profiles = policy["limits"]["context_profile_count"]
        self.max_versions = policy["limits"]["context_profile_versions"]
        self.max_profile_bytes = policy["limits"]["context_profile_bytes"]
        default = self.root / "work" / "application" / "contexts" / "profiles.sqlite3"
        self.path = (database_path or default)
        self._prepare_path()
        self._initialize()

    def _prepare_path(self) -> None:
        work = Path(os.path.abspath(self.root / "work"))
        candidate = self.path
        if not candidate.is_absolute():
            candidate = self.root / candidate
        candidate = Path(os.path.abspath(candidate))
        if work not in candidate.parents:
            raise ValueError("context storage must remain under ignored work state")
        cursor = work
        for part in candidate.parent.relative_to(work).parts:
            if cursor.is_symlink():
                raise ValueError("context storage cannot use a symlinked directory")
            cursor.mkdir(mode=0o700, exist_ok=True)
            os.chmod(cursor, 0o700)
            cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("context storage cannot use a symlinked directory")
        cursor.mkdir(mode=0o700, exist_ok=True)
        os.chmod(cursor, 0o700)
        if candidate.is_symlink():
            raise ValueError("context database cannot be a symlink")
        resolved = candidate.resolve()
        if work.resolve() not in resolved.parents:
            raise ValueError("context storage must remain under ignored work state")
        self.path = resolved

    def _connect(self) -> sqlite3.Connection:
        if self.path.is_symlink():
            raise ValueError("context database cannot be a symlink")
        if self.path.exists() and (
            not self.path.is_file() or self.path.stat().st_nlink != 1
        ):
            raise ValueError("context database must be one regular non-linked file")
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        os.chmod(self.path, 0o600)
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in {0, 1}:
                raise ValueError(
                    f"context database schema version {version} is unsupported"
                )
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS context_profiles (
                    context_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    profile_hash TEXT NOT NULL UNIQUE,
                    valid_from TEXT NOT NULL,
                    valid_until TEXT NOT NULL,
                    profile_json BLOB NOT NULL,
                    PRIMARY KEY (context_id, revision)
                );
                CREATE INDEX IF NOT EXISTS context_profiles_validity
                    ON context_profiles (valid_from, valid_until, context_id, revision);
                CREATE TABLE IF NOT EXISTS context_profile_heads (
                    context_id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL,
                    profile_hash TEXT NOT NULL UNIQUE
                );
                """
            )
            if version == 0:
                connection.execute(
                    """
                    INSERT INTO context_profile_heads
                        (context_id, revision, profile_hash)
                    SELECT p.context_id, p.revision, p.profile_hash
                    FROM context_profiles p
                    JOIN (
                        SELECT context_id, MAX(revision) AS revision
                        FROM context_profiles
                        GROUP BY context_id
                    ) latest
                    ON p.context_id=latest.context_id AND p.revision=latest.revision
                    """
                )
                connection.execute("PRAGMA user_version=1")
            expected = {
                "context_profiles": [
                    "context_id",
                    "revision",
                    "profile_hash",
                    "valid_from",
                    "valid_until",
                    "profile_json",
                ],
                "context_profile_heads": [
                    "context_id",
                    "revision",
                    "profile_hash",
                ],
            }
            for table, columns in expected.items():
                actual = [
                    row["name"]
                    for row in connection.execute(f"PRAGMA table_info({table})")
                ]
                if actual != columns:
                    raise ValueError(f"context database table {table} is incompatible")

    def _decode(self, row: sqlite3.Row) -> dict[str, Any]:
        stored = row["profile_json"]
        if not isinstance(stored, (bytes, bytearray, memoryview)):
            raise ValueError("stored context profile is not canonical JSON")
        raw = bytes(stored)
        if len(raw) > self.max_profile_bytes:
            raise ValueError("stored context profile exceeds the release byte limit")
        try:
            record = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("stored context profile is not canonical JSON") from exc
        if raw != canonical_json_bytes(record):
            raise ValueError("stored context profile is not canonical JSON")
        validate_application_instance("context_profile", record, self.root)
        start = _utc(record["valid_from"], "stored valid_from")
        end = _utc(record["valid_until"], "stored valid_until")
        if end <= start or (end - start).total_seconds() > self.retention_days * 86_400:
            raise ValueError("stored context profile has an invalid validity interval")
        if (
            record["context_id"] != row["context_id"]
            or record["revision"] != row["revision"]
            or record["profile_hash"] != row["profile_hash"]
            or record["valid_from"] != row["valid_from"]
            or record["valid_until"] != row["valid_until"]
            or _record_hash(record) != record["profile_hash"]
        ):
            raise ValueError("stored context profile failed identity verification")
        validate_overlay(record["overlay"], self.root)
        return record

    def _rows(
        self,
        connection: sqlite3.Connection,
        context_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if context_id is None:
            rows = connection.execute(
                "SELECT * FROM context_profiles ORDER BY context_id, revision"
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM context_profiles WHERE context_id=? ORDER BY revision",
                (context_id,),
            ).fetchall()
        decoded = [self._decode(row) for row in rows]
        heads = {
            row["context_id"]: row
            for row in connection.execute(
                "SELECT context_id, revision, profile_hash FROM context_profile_heads"
            )
        }
        latest: dict[str, dict[str, Any]] = {}
        for record in decoded:
            latest[record["context_id"]] = record
        for identifier, record in latest.items():
            head = heads.get(identifier)
            if head is None or head["revision"] < record["revision"]:
                raise ValueError("context profile head is missing or stale")
            if (
                head["revision"] == record["revision"]
                and head["profile_hash"] != record["profile_hash"]
            ):
                raise ValueError("context profile head failed identity verification")
        return decoded

    def prune(self, as_of: str) -> dict[str, Any]:
        _utc(as_of, "as_of")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT context_id, revision FROM context_profiles WHERE valid_until <= ?",
                (as_of,),
            ).fetchall()
            connection.execute(
                "DELETE FROM context_profiles WHERE valid_until <= ?",
                (as_of,),
            )
        return {
            "schema": "cpcs.context_profile_prune/1.0",
            "as_of": as_of,
            "deleted_versions": len(rows),
        }

    def put(
        self,
        *,
        context_id: str,
        context_kind: str,
        project_id: str | None,
        priority: int,
        values: dict[str, Any],
        locks: Iterable[str],
        valid_from: str,
        valid_until: str,
    ) -> dict[str, Any]:
        if not isinstance(context_id, str) or not CONTEXT_ID_PATTERN.fullmatch(
            context_id
        ):
            raise ValueError("context_id is invalid")
        if context_kind not in {"user_defaults", "project_profile"}:
            raise ValueError("context_kind is invalid")
        if context_kind == "user_defaults" and project_id is not None:
            raise ValueError("user defaults cannot bind a project_id")
        if context_kind == "project_profile" and (
            not isinstance(project_id, str)
            or not PROJECT_ID_PATTERN.fullmatch(project_id)
        ):
            raise ValueError("project profiles require a valid project_id")
        start = _utc(valid_from, "valid_from")
        end = _utc(valid_until, "valid_until")
        if end <= start:
            raise ValueError("valid_until must be later than valid_from")
        if (end - start).total_seconds() > self.retention_days * 86_400:
            raise ValueError(
                f"context validity exceeds the {self.retention_days}-day retention policy"
            )
        locks_list = sorted(set(locks))
        if not isinstance(priority, int) or isinstance(priority, bool) or priority < 0:
            raise ValueError("priority must be a non-negative integer")
        self.prune(valid_from)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = self._rows(connection, context_id)
            prior = existing[-1] if existing else None
            head = connection.execute(
                "SELECT revision, profile_hash FROM context_profile_heads WHERE context_id=?",
                (context_id,),
            ).fetchone()
            identity = {
                "context_kind": context_kind,
                "project_id": project_id,
                "priority": priority,
                "values": copy.deepcopy(values),
                "locks": locks_list,
                "valid_from": valid_from,
                "valid_until": valid_until,
            }
            if prior is not None:
                prior_identity = {
                    "context_kind": prior["context_kind"],
                    "project_id": prior["project_id"],
                    "priority": prior["overlay"]["priority"],
                    "values": prior["overlay"]["values"],
                    "locks": prior["overlay"]["locks"],
                    "valid_from": prior["valid_from"],
                    "valid_until": prior["valid_until"],
                }
                if canonical_json_bytes(identity) == canonical_json_bytes(prior_identity):
                    return {
                        "schema": CONTEXT_STORE_SCHEMA,
                        "disposition": "already_present",
                        "profile": prior,
                    }
            profile_count = connection.execute(
                "SELECT COUNT(*) FROM context_profile_heads"
            ).fetchone()[0]
            version_count = connection.execute(
                "SELECT COUNT(*) FROM context_profiles"
            ).fetchone()[0]
            if head is None and profile_count >= self.max_profiles:
                raise ValueError("context profile count exceeds the release limit")
            if version_count >= self.max_versions:
                raise ValueError("context profile version count exceeds the release limit")
            revision = 1 if head is None else head["revision"] + 1
            suffix = context_id.removeprefix("context_")
            record = {
                "schema": CONTEXT_PROFILE_SCHEMA,
                "context_id": context_id,
                "context_kind": context_kind,
                "project_id": project_id,
                "revision": revision,
                "valid_from": valid_from,
                "valid_until": valid_until,
                "overlay": {
                    "overlay_id": f"overlay_context_{suffix}_r{revision}",
                    "scope": context_kind,
                    "priority": priority,
                    "values": copy.deepcopy(values),
                    "locks": locks_list,
                    "source_refs": [f"context-profile://{context_id}/{revision}"],
                },
                "previous_profile_hash": head["profile_hash"] if head else None,
                "profile_hash": "",
            }
            record["profile_hash"] = _record_hash(record)
            validate_application_instance("context_profile", record, self.root)
            validate_overlay(record["overlay"], self.root)
            encoded = canonical_json_bytes(record)
            if len(encoded) > self.max_profile_bytes:
                raise ValueError("context profile exceeds the release byte limit")
            connection.execute(
                """
                INSERT INTO context_profiles
                    (context_id, revision, profile_hash, valid_from, valid_until, profile_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    context_id,
                    revision,
                    record["profile_hash"],
                    valid_from,
                    valid_until,
                    encoded,
                ),
            )
            connection.execute(
                """
                INSERT INTO context_profile_heads (context_id, revision, profile_hash)
                VALUES (?, ?, ?)
                ON CONFLICT(context_id) DO UPDATE SET
                    revision=excluded.revision,
                    profile_hash=excluded.profile_hash
                """,
                (context_id, revision, record["profile_hash"]),
            )
        return {
            "schema": CONTEXT_STORE_SCHEMA,
            "disposition": "created" if head is None else "updated",
            "profile": record,
        }

    def get(self, context_id: str, *, as_of: str) -> dict[str, Any]:
        if not isinstance(context_id, str) or not CONTEXT_ID_PATTERN.fullmatch(
            context_id
        ):
            raise ValueError("context_id is invalid")
        _utc(as_of, "as_of")
        self.prune(as_of)
        with self._connect() as connection:
            active = [
                row
                for row in self._rows(connection, context_id)
                if row["valid_from"] <= as_of < row["valid_until"]
            ]
        if not active:
            raise ValueError(f"no active context profile: {context_id}")
        return active[-1]

    def list(self, *, as_of: str) -> dict[str, Any]:
        _utc(as_of, "as_of")
        self.prune(as_of)
        with self._connect() as connection:
            rows = self._rows(connection)
        active: dict[str, dict[str, Any]] = {}
        for row in rows:
            if row["valid_from"] <= as_of < row["valid_until"]:
                active[row["context_id"]] = row
        return {
            "schema": "cpcs.context_profile_list/1.0",
            "as_of": as_of,
            "profiles": [active[key] for key in sorted(active)],
        }

    def delete(self, context_id: str) -> dict[str, Any]:
        if not isinstance(context_id, str) or not CONTEXT_ID_PATTERN.fullmatch(
            context_id
        ):
            raise ValueError("context_id is invalid")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            count = connection.execute(
                "SELECT COUNT(*) FROM context_profiles WHERE context_id=?",
                (context_id,),
            ).fetchone()[0]
            head_exists = connection.execute(
                "SELECT 1 FROM context_profile_heads WHERE context_id=?",
                (context_id,),
            ).fetchone() is not None
            connection.execute(
                "DELETE FROM context_profiles WHERE context_id=?", (context_id,)
            )
            connection.execute(
                "DELETE FROM context_profile_heads WHERE context_id=?", (context_id,)
            )
        return {
            "schema": "cpcs.context_profile_delete/1.0",
            "context_id": context_id,
            "deleted_versions": count,
            "disposition": "deleted" if count or head_exists else "no_change",
        }

    def resolve_overlays(
        self,
        context_ids: Iterable[str],
        *,
        as_of: str,
        project_id: str | None,
    ) -> list[dict[str, Any]]:
        ids = list(context_ids)
        if len(ids) != len(set(ids)):
            raise ValueError("context_profile_ids must be unique")
        profiles = [self.get(context_id, as_of=as_of) for context_id in ids]
        overlays = []
        for profile in profiles:
            if profile["context_kind"] == "project_profile" and profile["project_id"] != project_id:
                raise ValueError(
                    f"context profile {profile['context_id']} belongs to another project"
                )
            overlays.append(copy.deepcopy(profile["overlay"]))
        return overlays
