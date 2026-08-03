"""Pure TwelveLabs v1.3 transport for assets, stores, search, Jockey, and embeddings."""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse

API_VERSION = "v1.3"
SDK_VERSION = "1.3.1"
JOCKEY_MODEL = "jockey"
MARENGO_MODEL = "marengo3.0"
API_KEY_ENV = "TWELVE_LABS_API_KEY"
STORE_ID_ENV = "TWELVE_LABS_KNOWLEDGE_STORE_ID"

READ_REQUEST_OPTIONS = {"timeout_in_seconds": 60, "max_retries": 2}
CREATE_REQUEST_OPTIONS = {"timeout_in_seconds": 120, "max_retries": 0}


class TwelveLabsProviderError(RuntimeError):
    """Raised when the TwelveLabs boundary is unavailable or returns an unsafe state."""


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def to_plain(value: Any) -> Any:
    """Convert SDK response models into deterministic JSON-compatible values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_plain(item) for item in value]
    if hasattr(value, "model_dump"):
        return to_plain(
            value.model_dump(mode="json", by_alias=True, exclude_none=False)
        )
    if hasattr(value, "dict"):
        return to_plain(value.dict(by_alias=True, exclude_none=False))
    if hasattr(value, "__dict__"):
        return {
            key: to_plain(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    raise TwelveLabsProviderError(
        f"cannot serialize TwelveLabs response type {type(value).__name__}"
    )


def _installed_sdk_version() -> str | None:
    if importlib.util.find_spec("twelvelabs") is None:
        return None
    try:
        return importlib.metadata.version("twelvelabs")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def doctor(
    env: Mapping[str, str] | None = None,
    *,
    sdk_version: str | None = None,
) -> dict[str, Any]:
    """Report integration readiness without returning credential values."""
    source = os.environ if env is None else env
    installed = _installed_sdk_version() if sdk_version is None else sdk_version
    api_key_configured = bool(source.get(API_KEY_ENV))
    store_configured = bool(source.get(STORE_ID_ENV))
    return {
        "provider": "twelvelabs",
        "api_version": API_VERSION,
        "sdk_required": SDK_VERSION,
        "sdk_installed": installed,
        "sdk_compatible": installed == SDK_VERSION,
        "api_key_configured": api_key_configured,
        "knowledge_store_configured": store_configured,
        "ready_for_store_operations": installed == SDK_VERSION
        and api_key_configured,
        "ready_for_analysis": installed == SDK_VERSION
        and api_key_configured
        and store_configured,
    }


def build_client(
    api_key: str | None = None,
    env: Mapping[str, str] | None = None,
) -> Any:
    """Create a pinned SDK client, loading the dependency only when needed."""
    source = os.environ if env is None else env
    secret = api_key or source.get(API_KEY_ENV)
    if not secret:
        raise TwelveLabsProviderError(f"{API_KEY_ENV} is not configured")
    installed = _installed_sdk_version()
    if installed is None:
        raise TwelveLabsProviderError(
            "TwelveLabs SDK is not installed; install lab/second_brain/requirements.txt"
        )
    if installed != SDK_VERSION:
        raise TwelveLabsProviderError(
            f"TwelveLabs SDK {installed} is installed; this adapter requires {SDK_VERSION}"
        )
    from twelvelabs import TwelveLabs

    return TwelveLabs(api_key=secret)


def wait_until_ready(
    fetch: Callable[[], Any],
    *,
    resource_name: str,
    timeout_s: float,
    poll_interval_s: float,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> Any:
    """Poll one already-created resource with an explicit deadline."""
    if timeout_s <= 0 or poll_interval_s < 0:
        raise ValueError("timeout_s must be positive and poll_interval_s non-negative")
    deadline = monotonic() + timeout_s
    while True:
        resource = fetch()
        status = _field(resource, "status")
        if status == "ready":
            return resource
        if status == "failed":
            resource_id = _field(resource, "id", "unknown")
            raise TwelveLabsProviderError(
                f"{resource_name} failed: id={resource_id}"
            )
        remaining = deadline - monotonic()
        if remaining <= 0:
            resource_id = _field(resource, "id", "unknown")
            raise TwelveLabsProviderError(
                f"{resource_name} timed out after {timeout_s:g}s: "
                f"id={resource_id} status={status or 'unknown'}"
            )
        sleep(min(poll_interval_s, remaining))


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
    kwargs: dict[str, Any] = {
        "name": name,
        "request_options": CREATE_REQUEST_OPTIONS,
    }
    if description is not None:
        kwargs["description"] = description
    if metadata is not None:
        kwargs["metadata"] = metadata
    store = active.knowledge_stores.create(**kwargs)
    if not _field(store, "id"):
        raise TwelveLabsProviderError("knowledge store creation returned no ID")
    return to_plain(store)


def upload_asset(
    *,
    media_type: str,
    url: str | None = None,
    file_path: Path | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Create one asset. The returned ID is the retry/resume boundary."""
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
            method="url",
            url=url,
            request_options=CREATE_REQUEST_OPTIONS,
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
    if not _field(asset, "id"):
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
        lambda: active.assets.retrieve(
            asset_id, request_options=READ_REQUEST_OPTIONS
        ),
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
    if not _field(item, "id"):
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
            knowledge_store_id,
            item_id,
            request_options=READ_REQUEST_OPTIONS,
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
    """Upload and index one item with bounded polling and reusable IDs."""
    if media_type == "audio":
        raise ValueError("Jockey knowledge stores accept video or image assets")
    active = client or build_client()
    created_asset = upload_asset(
        media_type=media_type,
        url=url,
        file_path=file_path,
        client=active,
    )
    ready_asset = wait_for_asset(
        created_asset["id"],
        client=active,
        timeout_s=asset_timeout_s,
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
            knowledge_store_id,
            item_id,
            request_options=READ_REQUEST_OPTIONS,
        )
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
    """Read every search page while preserving the original query contract."""
    if not query_text.strip():
        raise ValueError("query_text must be non-empty")
    if not 1 <= page_size <= 50:
        raise ValueError("page_size must be between 1 and 50")
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
        page_hits = _field(response, "data", [])
        hits.extend(to_plain(page_hits))
        next_token = _field(response, "next_page_token")
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
    """Run one synchronous Jockey response with a strict JSON Schema."""
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


def create_embedding(
    input_type: str,
    *,
    text: str | None = None,
    asset_id: str | None = None,
    image_asset_ids: Sequence[str] | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Create synchronous Marengo 3.0 embeddings for the documented input types."""
    active = client or build_client()
    kwargs: dict[str, Any] = {
        "input_type": input_type,
        "model_name": MARENGO_MODEL,
        "request_options": CREATE_REQUEST_OPTIONS,
    }
    if input_type == "text":
        if not text:
            raise ValueError("text embedding requires text")
        kwargs["text"] = {"input_text": text}
    elif input_type in {"video", "audio", "image"}:
        if not asset_id:
            raise ValueError(f"{input_type} embedding requires asset_id")
        kwargs[input_type] = {"media_source": {"asset_id": asset_id}}
    elif input_type == "multi_input":
        ids = list(image_asset_ids or [])
        if not text or not ids:
            raise ValueError("multi_input embedding requires text and image asset IDs")
        if len(ids) > 10:
            raise ValueError("multi_input supports at most 10 images")
        kwargs["multi_input"] = {
            "input_text": text,
            "media_sources": [
                {"media_type": "image", "asset_id": item} for item in ids
            ],
        }
    else:
        raise ValueError(
            "input_type must be video, audio, text, image, or multi_input"
        )
    return to_plain(active.embed.v_2.create(**kwargs))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    store = sub.add_parser("create-store")
    store.add_argument("name")
    store.add_argument("--description")
    upload = sub.add_parser("upload")
    upload.add_argument("media_type", choices=("video", "image", "audio"))
    upload_source = upload.add_mutually_exclusive_group(required=True)
    upload_source.add_argument("--url")
    upload_source.add_argument("--file", type=Path)
    add = sub.add_parser("add-media")
    add.add_argument("knowledge_store_id")
    add.add_argument("media_type", choices=("video", "image"))
    source = add.add_mutually_exclusive_group(required=True)
    source.add_argument("--url")
    source.add_argument("--file", type=Path)
    search = sub.add_parser("search")
    search.add_argument("knowledge_store_id")
    search.add_argument("query")
    search.add_argument("--page-size", type=int, default=50)
    embed = sub.add_parser("embed")
    embed.add_argument(
        "input_type",
        choices=("video", "audio", "text", "image", "multi_input"),
    )
    embed.add_argument("--text")
    embed.add_argument("--asset-id")
    embed.add_argument("--image-asset-id", action="append", default=[])
    args = parser.parse_args(argv)
    if args.command == "doctor":
        result = doctor()
    elif args.command == "create-store":
        result = create_knowledge_store(args.name, description=args.description)
    elif args.command == "upload":
        created = upload_asset(
            media_type=args.media_type,
            url=args.url,
            file_path=args.file,
        )
        result = wait_for_asset(created["id"])
    elif args.command == "add-media":
        result = add_media(
            args.knowledge_store_id,
            media_type=args.media_type,
            url=args.url,
            file_path=args.file,
        )
    elif args.command == "search":
        result = search_all(
            args.knowledge_store_id,
            args.query,
            page_size=args.page_size,
        )
    else:
        result = create_embedding(
            args.input_type,
            text=args.text,
            asset_id=args.asset_id,
            image_asset_ids=args.image_asset_id,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
