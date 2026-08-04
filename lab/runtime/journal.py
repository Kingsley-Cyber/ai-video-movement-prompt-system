"""SQLite single-writer journal with leases and hash-chained events."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from lab.compiler.provenance import canonical_json_bytes

TERMINAL_STATES = frozenset(
    {"succeeded", "failed", "cancelled", "cancel_unsupported", "timed_out"}
)
SECRET_KEY = re.compile(
    r"(?:authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|password|"
    r"credential|client[_-]?secret|cookie)",
    re.IGNORECASE,
)
SECRET_TEXT = re.compile(r"(?:bearer\s+[A-Za-z0-9._~+/-]+|access_token=)", re.I)
JOURNAL_SCHEMA_VERSION = 1
JOURNAL_SCHEMA_NAME = "baseline_render_journal"
JOURNAL_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    job_json TEXT NOT NULL,
    job_hash TEXT NOT NULL,
    state TEXT NOT NULL,
    adapter TEXT NOT NULL,
    operation_json TEXT,
    completion_json TEXT,
    result_json TEXT,
    last_error_json TEXT,
    poll_count INTEGER NOT NULL DEFAULT 0,
    retry_count INTEGER NOT NULL DEFAULT 0,
    deadline_at REAL NOT NULL,
    lease_owner TEXT,
    lease_expires_at REAL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(job_id),
    event_type TEXT NOT NULL,
    state TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    prior_event_hash TEXT,
    event_hash TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS events_job_seq ON events(job_id, seq);
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL
);
"""
JOURNAL_SCHEMA_CHECKSUM = "sha256:" + hashlib.sha256(
    JOURNAL_SCHEMA_DDL.encode("utf-8")
).hexdigest()


class JournalError(RuntimeError):
    pass


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if SECRET_KEY.search(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return [redact(item) for item in value]
    if isinstance(value, str) and SECRET_TEXT.search(value):
        return "[REDACTED]"
    return value


def assert_secret_free(value: Any, path: str = "job") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if SECRET_KEY.search(str(key)):
                raise JournalError(f"{path}.{key} is a forbidden secret field")
            assert_secret_free(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            assert_secret_free(item, f"{path}[{index}]")
    elif isinstance(value, str) and SECRET_TEXT.search(value):
        raise JournalError(f"{path} contains credential-like text")


def _json(value: Any) -> str:
    return canonical_json_bytes(redact(value)).decode("utf-8").rstrip("\n")


class JobJournal:
    """Durable job state; SQLite serializes all writers with BEGIN IMMEDIATE."""

    def __init__(
        self,
        path: Path,
        *,
        time_fn: Callable[[], float] = time.time,
    ) -> None:
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.time_fn = time_fn
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version > JOURNAL_SCHEMA_VERSION:
                raise JournalError(
                    f"render journal schema {version} is newer than supported {JOURNAL_SCHEMA_VERSION}"
                )
            connection.executescript(JOURNAL_SCHEMA_DDL)
            row = connection.execute(
                "SELECT name, checksum FROM schema_migrations WHERE version=?",
                (JOURNAL_SCHEMA_VERSION,),
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO schema_migrations VALUES (?, ?, ?)",
                    (
                        JOURNAL_SCHEMA_VERSION,
                        JOURNAL_SCHEMA_NAME,
                        JOURNAL_SCHEMA_CHECKSUM,
                    ),
                )
            elif (
                row["name"] != JOURNAL_SCHEMA_NAME
                or row["checksum"] != JOURNAL_SCHEMA_CHECKSUM
            ):
                raise JournalError("render journal migration checksum is invalid")
            if version < JOURNAL_SCHEMA_VERSION:
                connection.execute(f"PRAGMA user_version={JOURNAL_SCHEMA_VERSION}")

    def schema_status(self) -> dict[str, Any]:
        with self._connect() as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            rows = connection.execute(
                "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
            ).fetchall()
        return {
            "schema": "cpcs.render_journal_schema/1.0",
            "current_version": version,
            "supported_version": JOURNAL_SCHEMA_VERSION,
            "migrations": [dict(row) for row in rows],
        }

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def _append_event(
        self,
        connection: sqlite3.Connection,
        *,
        job_id: str,
        event_type: str,
        state: str,
        payload: Any,
        created_at: float,
    ) -> str:
        prior = connection.execute(
            "SELECT event_hash FROM events WHERE job_id=? ORDER BY seq DESC LIMIT 1",
            (job_id,),
        ).fetchone()
        prior_hash = prior["event_hash"] if prior else None
        row = connection.execute("SELECT COALESCE(MAX(seq), 0) + 1 AS seq FROM events").fetchone()
        seq = int(row["seq"])
        payload_json = _json(payload)
        core = {
            "seq": seq,
            "job_id": job_id,
            "event_type": event_type,
            "state": state,
            "payload": json.loads(payload_json),
            "created_at": created_at,
            "prior_event_hash": prior_hash,
        }
        event_hash = "sha256:" + hashlib.sha256(canonical_json_bytes(core)).hexdigest()
        connection.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                seq,
                job_id,
                event_type,
                state,
                payload_json,
                created_at,
                prior_hash,
                event_hash,
            ),
        )
        return event_hash

    def register(self, job: dict[str, Any]) -> dict[str, Any]:
        assert_secret_free(job)
        now = self.time_fn()
        job_json = _json(job)
        job_hash = "sha256:" + hashlib.sha256(job_json.encode()).hexdigest()
        with self._write() as connection:
            existing = connection.execute(
                "SELECT * FROM jobs WHERE idempotency_key=? OR job_id=?",
                (job["idempotency_key"], job["job_id"]),
            ).fetchone()
            if existing:
                if existing["job_hash"] != job_hash or existing["job_json"] != job_json:
                    raise JournalError("idempotency key or job ID is already bound to different input")
                return self._snapshot_row(existing)
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id, idempotency_key, job_json, job_hash, state, adapter,
                    deadline_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'queued', ?, ?, ?, ?)
                """,
                (
                    job["job_id"],
                    job["idempotency_key"],
                    job_json,
                    job_hash,
                    job["adapter"],
                    now + float(job["policy"]["timeout_seconds"]),
                    now,
                    now,
                ),
            )
            self._append_event(
                connection,
                job_id=job["job_id"],
                event_type="registered",
                state="queued",
                payload={"job_hash": job_hash, "adapter": job["adapter"]},
                created_at=now,
            )
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id=?", (job["job_id"],)
            ).fetchone()
            return self._snapshot_row(row)

    @staticmethod
    def _snapshot_row(row: sqlite3.Row) -> dict[str, Any]:
        def decoded(name: str) -> Any:
            value = row[name]
            return json.loads(value) if value is not None else None

        return {
            "job_id": row["job_id"],
            "idempotency_key": row["idempotency_key"],
            "job": decoded("job_json"),
            "job_hash": row["job_hash"],
            "state": row["state"],
            "adapter": row["adapter"],
            "operation": decoded("operation_json"),
            "completion": decoded("completion_json"),
            "result": decoded("result_json"),
            "last_error": decoded("last_error_json"),
            "poll_count": row["poll_count"],
            "retry_count": row["retry_count"],
            "deadline_at": row["deadline_at"],
            "lease_owner": row["lease_owner"],
            "lease_expires_at": row["lease_expires_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get(self, job_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id=?", (job_id,)
            ).fetchone()
        if row is None:
            raise JournalError(f"unknown render job: {job_id}")
        return self._snapshot_row(row)

    def claim(self, job_id: str, worker_id: str, lease_seconds: float) -> dict[str, Any]:
        now = self.time_fn()
        with self._write() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            if row is None:
                raise JournalError(f"unknown render job: {job_id}")
            if (
                row["lease_owner"] not in {None, worker_id}
                and row["lease_expires_at"] is not None
                and row["lease_expires_at"] > now
            ):
                raise JournalError(f"render job is leased by {row['lease_owner']}")
            connection.execute(
                "UPDATE jobs SET lease_owner=?, lease_expires_at=?, updated_at=? WHERE job_id=?",
                (worker_id, now + lease_seconds, now, job_id),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type="lease_claimed",
                state=row["state"],
                payload={"worker_id": worker_id, "lease_seconds": lease_seconds},
                created_at=now,
            )
        return self.get(job_id)

    def release(self, job_id: str, worker_id: str) -> None:
        now = self.time_fn()
        with self._write() as connection:
            row = connection.execute(
                "SELECT state, lease_owner FROM jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            if row is None:
                raise JournalError(f"unknown render job: {job_id}")
            if row["lease_owner"] != worker_id:
                return
            connection.execute(
                "UPDATE jobs SET lease_owner=NULL, lease_expires_at=NULL, updated_at=? WHERE job_id=?",
                (now, job_id),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type="lease_released",
                state=row["state"],
                payload={"worker_id": worker_id},
                created_at=now,
            )

    def transition(
        self,
        job_id: str,
        worker_id: str,
        *,
        expected: set[str],
        state: str,
        event_type: str,
        payload: Any = None,
        operation: dict[str, Any] | None = None,
        completion: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        poll_increment: int = 0,
        retry_increment: int = 0,
        lease_seconds: float = 60.0,
    ) -> dict[str, Any]:
        now = self.time_fn()
        with self._write() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            if row is None:
                raise JournalError(f"unknown render job: {job_id}")
            if row["lease_owner"] != worker_id:
                raise JournalError("worker does not own the render-job lease")
            if row["state"] not in expected:
                raise JournalError(
                    f"invalid render transition {row['state']} -> {state}; expected {sorted(expected)}"
                )
            updates = {
                "state": state,
                "operation_json": _json(operation) if operation is not None else row["operation_json"],
                "completion_json": _json(completion) if completion is not None else row["completion_json"],
                "result_json": _json(result) if result is not None else row["result_json"],
                "last_error_json": _json(error) if error is not None else row["last_error_json"],
                "poll_count": row["poll_count"] + poll_increment,
                "retry_count": row["retry_count"] + retry_increment,
                "lease_expires_at": now + lease_seconds,
                "updated_at": now,
            }
            connection.execute(
                """
                UPDATE jobs SET state=:state, operation_json=:operation_json,
                completion_json=:completion_json, result_json=:result_json,
                last_error_json=:last_error_json, poll_count=:poll_count,
                retry_count=:retry_count, lease_expires_at=:lease_expires_at,
                updated_at=:updated_at WHERE job_id=:job_id
                """,
                {**updates, "job_id": job_id},
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_type=event_type,
                state=state,
                payload=payload or {},
                created_at=now,
            )
        return self.get(job_id)

    def reconcile_operation(
        self, job_id: str, worker_id: str, operation: dict[str, Any], lease_seconds: float
    ) -> dict[str, Any]:
        return self.transition(
            job_id,
            worker_id,
            expected={"submission_unknown"},
            state="submitted",
            event_type="submission_reconciled",
            payload={"operation_id": operation.get("operation_id")},
            operation=operation,
            lease_seconds=lease_seconds,
        )

    def events(self, job_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE job_id=? ORDER BY seq", (job_id,)
            ).fetchall()
        return [
            {
                "seq": row["seq"],
                "job_id": row["job_id"],
                "event_type": row["event_type"],
                "state": row["state"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
                "prior_event_hash": row["prior_event_hash"],
                "event_hash": row["event_hash"],
            }
            for row in rows
        ]

    def verify(self, job_id: str) -> None:
        prior: str | None = None
        for event in self.events(job_id):
            if event["prior_event_hash"] != prior:
                raise JournalError("render journal event chain is broken")
            core = {key: value for key, value in event.items() if key != "event_hash"}
            expected = "sha256:" + hashlib.sha256(canonical_json_bytes(core)).hexdigest()
            if event["event_hash"] != expected:
                raise JournalError("render journal event hash is invalid")
            prior = event["event_hash"]

    def iso_time(self, timestamp: float | None = None) -> str:
        value = self.time_fn() if timestamp is None else timestamp
        return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")
