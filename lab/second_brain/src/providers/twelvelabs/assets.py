"""Asset and knowledge-store registration transport."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from .common import (
    CREATE_REQUEST_OPTIONS,
    READ_REQUEST_OPTIONS,
    TwelveLabsProviderError,
    build_client,
    field,
    to_plain,
    wait_until_ready,
)


def create_knowledge_store(
    name: str,
    *,
    description: str | None = None,
    metadata: dict[str, str] | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    if not name.strip():
        raise ValueError("knowledge store name must be non-empty")
    active = client or build_client()
    kwargs: dict[str, Any] = {"name": name, "request_options": CREATE_REQUEST_OPTIONS}
    if description is not None:
        kwargs["description"] = description
    if metadata is not None:
        kwargs["metadata"] = metadata
    store = active.knowledge_stores.create(**kwargs)
    if not field(store, "id"):
        raise TwelveLabsProviderError("knowledge store creation returned no ID")
    return to_plain(store)


def upload_asset(
    *,
    media_type: str,
    url: str | None = None,
    file_path: Path | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    if media_type not in {"video", "image", "audio"}:
        raise ValueError("media_type must be video, image, or audio")
    if (url is None) == (file_path is None):
        raise ValueError("provide exactly one of url or file_path")
    active = client or build_client()
    if url is not None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("url must be a direct HTTP(S) media URL")
        asset = active.assets.create(
            method="url", url=url, request_options=CREATE_REQUEST_OPTIONS
        )
    else:
        assert file_path is not None
        path = file_path.expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        maximum = 32 * 1024 * 1024 if media_type == "image" else 200 * 1024 * 1024
        if path.stat().st_size > maximum:
            raise ValueError(
                f"local {media_type} exceeds the direct-upload limit of "
                f"{maximum // (1024 * 1024)} MB"
            )
        with path.open("rb") as handle:
            asset = active.assets.create(
                method="direct",
                file=handle,
                filename=path.name,
                request_options=CREATE_REQUEST_OPTIONS,
            )
    if not field(asset, "id"):
        raise TwelveLabsProviderError("asset creation returned no ID")
    return to_plain(asset)


def wait_for_asset(
    asset_id: str,
    *,
    client: Any | None = None,
    timeout_s: float = 1800,
    poll_interval_s: float = 5,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    active = client or build_client()
    result = wait_until_ready(
        lambda: active.assets.retrieve(asset_id, request_options=READ_REQUEST_OPTIONS),
        resource_name="asset processing",
        timeout_s=timeout_s,
        poll_interval_s=poll_interval_s,
        sleep=sleep,
        monotonic=monotonic,
    )
    return to_plain(result)


def add_asset_to_store(
    knowledge_store_id: str,
    asset_id: str,
    *,
    asset_type: str = "video",
    metadata: dict[str, str] | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    if asset_type not in {"video", "image"}:
        raise ValueError("knowledge store item type must be video or image")
    active = client or build_client()
    kwargs: dict[str, Any] = {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "request_options": CREATE_REQUEST_OPTIONS,
    }
    if metadata is not None:
        kwargs["metadata"] = metadata
    item = active.knowledge_store_items.create(knowledge_store_id, **kwargs)
    if not field(item, "id"):
        raise TwelveLabsProviderError("knowledge store item creation returned no ID")
    return to_plain(item)


def wait_for_store_item(
    knowledge_store_id: str,
    item_id: str,
    *,
    client: Any | None = None,
    timeout_s: float = 3600,
    poll_interval_s: float = 10,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    active = client or build_client()
    result = wait_until_ready(
        lambda: active.knowledge_store_items.retrieve(
            knowledge_store_id, item_id, request_options=READ_REQUEST_OPTIONS
        ),
        resource_name="knowledge store indexing",
        timeout_s=timeout_s,
        poll_interval_s=poll_interval_s,
        sleep=sleep,
        monotonic=monotonic,
    )
    return to_plain(result)


def add_media(
    knowledge_store_id: str,
    *,
    media_type: str,
    url: str | None = None,
    file_path: Path | None = None,
    client: Any | None = None,
    asset_timeout_s: float = 1800,
    item_timeout_s: float = 3600,
) -> dict[str, Any]:
    if media_type == "audio":
        raise ValueError("Jockey knowledge stores accept video or image assets")
    active = client or build_client()
    created_asset = upload_asset(
        media_type=media_type, url=url, file_path=file_path, client=active
    )
    ready_asset = wait_for_asset(
        created_asset["id"], client=active, timeout_s=asset_timeout_s
    )
    created_item = add_asset_to_store(
        knowledge_store_id,
        ready_asset["id"],
        asset_type=media_type,
        client=active,
    )
    ready_item = wait_for_store_item(
        knowledge_store_id,
        created_item["id"],
        client=active,
        timeout_s=item_timeout_s,
    )
    return {"asset": ready_asset, "item": ready_item}


def retrieve_store_item(
    knowledge_store_id: str,
    item_id: str,
    *,
    client: Any | None = None,
) -> dict[str, Any]:
    active = client or build_client()
    return to_plain(
        active.knowledge_store_items.retrieve(
            knowledge_store_id, item_id, request_options=READ_REQUEST_OPTIONS
        )
    )
