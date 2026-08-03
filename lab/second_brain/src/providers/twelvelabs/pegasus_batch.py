"""Pegasus 1.5 batch-analysis transport."""

from __future__ import annotations

import time
from typing import Any, Callable, Sequence

from .common import (
    CREATE_REQUEST_OPTIONS,
    PEGASUS_MODEL,
    READ_REQUEST_OPTIONS,
    TwelveLabsProviderError,
    build_client,
    field,
    to_plain,
    wait_until_ready,
)


def analyze_batch(
    requests: Sequence[dict[str, Any]],
    *,
    analysis_mode: str,
    defaults: dict[str, Any] | None = None,
    timeout_s: float = 7200,
    poll_interval_s: float = 10,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    client: Any | None = None,
) -> dict[str, Any]:
    if not 1 <= len(requests) <= 1000:
        raise ValueError("batch requires between 1 and 1000 requests")
    if analysis_mode not in {"general", "time_based_metadata"}:
        raise ValueError("unknown batch analysis_mode")
    custom_ids = [row.get("custom_id") for row in requests]
    if None in custom_ids or len(custom_ids) != len(set(custom_ids)):
        raise ValueError("batch custom_id values must be present and unique")
    active = client or build_client()
    kwargs: dict[str, Any] = {
        "model_name": PEGASUS_MODEL,
        "analysis_mode": analysis_mode,
        "requests": list(requests),
        "request_options": CREATE_REQUEST_OPTIONS,
    }
    if defaults is not None:
        kwargs["defaults"] = defaults
    created = active.analyze_async.batches.create(**kwargs)
    batch_id = field(created, "batch_id")
    if not batch_id:
        raise TwelveLabsProviderError("batch creation returned no batch_id")
    completed = wait_until_ready(
        lambda: active.analyze_async.batches.retrieve(
            batch_id, request_options=READ_REQUEST_OPTIONS
        ),
        resource_name="Pegasus batch",
        timeout_s=timeout_s,
        poll_interval_s=poll_interval_s,
        ready_statuses=frozenset({"completed"}),
        failed_statuses=frozenset({"canceled", "expired"}),
        sleep=sleep,
        monotonic=monotonic,
    )
    results = [
        to_plain(item)
        for item in active.analyze_async.batches.results(
            batch_id, request_options=READ_REQUEST_OPTIONS
        )
    ]
    failed = [
        row
        for row in results
        if row.get("status") != "ready"
        or not isinstance(row.get("data"), dict)
        or row["data"].get("finish_reason") != "stop"
        or not isinstance(row["data"].get("data"), (str, dict))
    ]
    if failed:
        raise TwelveLabsProviderError(
            f"Pegasus batch completed with {len(failed)} non-ready item(s)"
        )
    return {
        "created": to_plain(created),
        "completed": to_plain(completed),
        "results": results,
    }
