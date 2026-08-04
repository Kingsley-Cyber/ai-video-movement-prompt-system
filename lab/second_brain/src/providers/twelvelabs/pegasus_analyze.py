"""Pegasus 1.5 synchronous exact-video and clipped-analysis transport."""

from __future__ import annotations

from typing import Any

from .common import (
    CREATE_REQUEST_OPTIONS,
    PEGASUS_MODEL,
    TwelveLabsProviderError,
    build_client,
    to_plain,
)


def analyze_video(
    asset_id: str,
    prompt: str,
    *,
    output_schema: dict[str, Any],
    start_s: float | None = None,
    end_s: float | None = None,
    temperature: float = 0.0,
    max_tokens: int = 8192,
    client: Any | None = None,
) -> dict[str, Any]:
    if not asset_id:
        raise ValueError("asset_id must be non-empty")
    if not prompt.strip():
        raise ValueError("prompt must be non-empty")
    if (start_s is None) != (end_s is None):
        raise ValueError("start_s and end_s must be supplied together")
    if start_s is not None and (start_s < 0 or end_s is None or end_s - start_s < 4):
        raise ValueError("clipped Pegasus analysis requires an interval of at least 4 seconds")
    active = client or build_client()
    kwargs: dict[str, Any] = {
        "model_name": PEGASUS_MODEL,
        "video": {"type": "asset_id", "asset_id": asset_id},
        "prompt": prompt,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_schema", "json_schema": output_schema},
        "request_options": CREATE_REQUEST_OPTIONS,
    }
    if start_s is not None:
        kwargs["start_time"] = start_s
        kwargs["end_time"] = end_s
    response = to_plain(active.analyze(**kwargs))
    if response.get("finish_reason") != "stop":
        raise TwelveLabsProviderError(
            "Pegasus Analyze did not finish cleanly: "
            f"{response.get('finish_reason', 'unknown')}"
        )
    if not isinstance(response.get("data"), (str, dict)):
        raise TwelveLabsProviderError("Pegasus Analyze returned no structured data")
    return response
