"""Content-free local telemetry for application operations."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from lab.release.contracts import validate_release_instance
from lab.second_brain.src.validate import REPO_ROOT, canonical_json_bytes


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class TelemetrySink:
    """Append allowlisted timing events under ignored work/ only."""

    def __init__(
        self,
        path: Path,
        *,
        root: Path = REPO_ROOT,
        clock: Callable[[], str] = _utc_now,
    ) -> None:
        work = (root / "work").resolve()
        candidate = path.expanduser()
        if candidate.is_symlink():
            raise ValueError("telemetry path cannot be a symlink")
        resolved = candidate.resolve()
        if resolved == work or work not in resolved.parents:
            raise ValueError("telemetry must be written under the ignored work directory")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        if resolved.exists() and resolved.is_symlink():
            raise ValueError("telemetry path cannot be a symlink")
        self.path = resolved
        self.root = root
        self.clock = clock

    def record(
        self,
        *,
        trace_id: str,
        operation: str,
        status: str,
        role: str,
        mutation_scope: str | None,
        duration_ms: float,
        authorization_id: str | None = None,
    ) -> dict[str, Any]:
        event = {
            "schema": "cpcs.telemetry_event/1.0",
            "trace_id": trace_id,
            "operation": operation,
            "status": status,
            "role": role,
            "mutation_scope": mutation_scope,
            "authorization_id": authorization_id,
            "duration_ms": round(max(0.0, duration_ms), 3),
            "recorded_at": self.clock(),
        }
        validate_release_instance("telemetry_event", event, self.root)
        descriptor = os.open(
            self.path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o600,
        )
        try:
            os.write(descriptor, canonical_json_bytes(event))
        finally:
            os.close(descriptor)
        return event


def summarize(path: Path) -> dict[str, Any]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    counts: dict[str, int] = {}
    durations: dict[str, list[float]] = {}
    for row in rows:
        key = f"{row['operation']}:{row['status']}"
        counts[key] = counts.get(key, 0) + 1
        durations.setdefault(row["operation"], []).append(row["duration_ms"])
    return {
        "schema": "cpcs.telemetry_summary/1.0",
        "events": len(rows),
        "counts": dict(sorted(counts.items())),
        "maximum_duration_ms": {
            key: max(values) for key, values in sorted(durations.items())
        },
    }
