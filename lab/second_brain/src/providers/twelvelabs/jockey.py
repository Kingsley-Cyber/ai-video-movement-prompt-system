"""Corpus-level Jockey Responses transport."""

from __future__ import annotations

from typing import Any, Sequence

from .common import CREATE_REQUEST_OPTIONS, build_client


def create_jockey_response(
    knowledge_store_id: str,
    prompt: str,
    *,
    output_schema: dict[str, Any],
    schema_name: str,
    instructions: str | None = None,
    selections: Sequence[dict[str, str]] | None = None,
    session_id: str | None = None,
    include_intermediate_outputs: bool = False,
    client: Any | None = None,
) -> Any:
    if not prompt.strip():
        raise ValueError("prompt must be non-empty")
    if len(prompt) > 10_000:
        raise ValueError("prompt exceeds the 10,000-character Responses limit")
    if instructions is not None and len(instructions) > 2_000:
        raise ValueError("instructions exceed the 2,000-character limit")
    active = client or build_client()
    kwargs: dict[str, Any] = {
        "knowledge_store_id": knowledge_store_id,
        "input": [{"type": "message", "role": "user", "content": prompt}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": output_schema,
                "strict": True,
            }
        },
        "request_options": CREATE_REQUEST_OPTIONS,
    }
    if instructions is not None:
        kwargs["instructions"] = instructions
    if selections is not None:
        kwargs["selections"] = list(selections)
    if session_id is not None:
        kwargs["session_id"] = session_id
    if include_intermediate_outputs:
        kwargs["include"] = ["intermediate_outputs"]
    return active.responses.create(**kwargs)
