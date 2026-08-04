"""Pegasus 1.5 asynchronous time-based segmentation transport."""

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


def segment_video(
    asset_id: str,
    segment_definitions: Sequence[dict[str, Any]],
    *,
    custom_id: str,
    start_s: float | None = None,
    end_s: float | None = None,
    min_segment_duration: float = 2.0,
    max_segment_duration: float | None = None,
    timeout_s: float = 3600,
    poll_interval_s: float = 5,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    client: Any | None = None,
) -> dict[str, Any]:
    if not segment_definitions:
        raise ValueError("segment_definitions must be non-empty")
    if (start_s is None) != (end_s is None):
        raise ValueError("start_s and end_s must be supplied together")
    if start_s is not None and (start_s < 0 or end_s is None or end_s - start_s < 4):
        raise ValueError("segmentation interval must be at least 4 seconds")
    active = client or build_client()
    kwargs: dict[str, Any] = {
        "video": {"type": "asset_id", "asset_id": asset_id},
        "model_name": PEGASUS_MODEL,
        "custom_id": custom_id,
        "analysis_mode": "time_based_metadata",
        "response_format": {
            "type": "segment_definitions",
            "segment_definitions": list(segment_definitions),
        },
        "min_segment_duration": min_segment_duration,
        "request_options": CREATE_REQUEST_OPTIONS,
    }
    if max_segment_duration is not None:
        if max_segment_duration < min_segment_duration:
            raise ValueError("max_segment_duration must not be below the minimum")
        kwargs["max_segment_duration"] = max_segment_duration
    if start_s is not None:
        kwargs["start_time"] = start_s
        kwargs["end_time"] = end_s
    created = active.analyze_async.tasks.create(**kwargs)
    task_id = field(created, "task_id")
    if not task_id:
        raise ValueError("segmentation task returned no task_id")
    completed = wait_until_ready(
        lambda: active.analyze_async.tasks.retrieve(
            task_id, request_options=READ_REQUEST_OPTIONS
        ),
        resource_name="Pegasus segmentation",
        timeout_s=timeout_s,
        poll_interval_s=poll_interval_s,
        sleep=sleep,
        monotonic=monotonic,
    )
    completed_plain = to_plain(completed)
    result = completed_plain.get("result")
    if not isinstance(result, dict) or result.get("finish_reason") != "stop":
        raise TwelveLabsProviderError(
            "Pegasus segmentation did not finish cleanly: "
            f"{(result or {}).get('finish_reason', 'unknown')}"
        )
    if not isinstance(result.get("data"), (str, dict)):
        raise TwelveLabsProviderError("Pegasus segmentation returned no structured data")
    return {"created": to_plain(created), "completed": completed_plain}
