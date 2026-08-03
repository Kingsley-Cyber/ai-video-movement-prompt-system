"""Literal, paginated knowledge-store search transport."""

from __future__ import annotations

from typing import Any, Sequence

from .common import (
    READ_REQUEST_OPTIONS,
    TwelveLabsProviderError,
    build_client,
    field,
    to_plain,
)


def search_all(
    knowledge_store_id: str,
    query_text: str,
    *,
    modalities: Sequence[str] = ("visual", "audio"),
    filter_: dict[str, Any] | None = None,
    group_by: str = "item",
    page_size: int = 50,
    include_metadata: bool = True,
    client: Any | None = None,
) -> dict[str, Any]:
    if not query_text.strip():
        raise ValueError("query_text must be non-empty")
    if not 1 <= page_size <= 50:
        raise ValueError("page_size must be between 1 and 50")
    if not set(modalities) <= {"visual", "audio"} or not modalities:
        raise ValueError("modalities must contain visual, audio, or both")
    active = client or build_client()
    base: dict[str, Any] = {
        "query": {"text": query_text},
        "search_options": {"video": {"modalities": list(modalities)}},
        "group_by": group_by,
        "page_size": page_size,
        "include_metadata": include_metadata,
        "request_options": READ_REQUEST_OPTIONS,
    }
    if filter_ is not None:
        base["filter"] = filter_
    page_token: str | None = None
    hits: list[Any] = []
    pages = 0
    seen_tokens: set[str] = set()
    while True:
        kwargs = dict(base)
        if page_token is not None:
            kwargs["page_token"] = page_token
        response = active.knowledge_stores.search(knowledge_store_id, **kwargs)
        pages += 1
        hits.extend(to_plain(field(response, "data", [])))
        next_token = field(response, "next_page_token")
        if not next_token:
            break
        if next_token in seen_tokens:
            raise TwelveLabsProviderError("search returned a repeated page token")
        seen_tokens.add(next_token)
        page_token = next_token
    return {
        "knowledge_store_id": knowledge_store_id,
        "query": query_text,
        "pages": pages,
        "data": hits,
        "next_page_token": None,
    }
