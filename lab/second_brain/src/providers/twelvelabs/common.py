"""Shared, authority-free TwelveLabs v1.3 transport primitives."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import time
from datetime import date, datetime
from typing import Any, Callable, Mapping

API_VERSION = "v1.3"
SDK_VERSION = "1.3.1"
PEGASUS_MODEL = "pegasus1.5"
JOCKEY_MODEL = "jockey"
MARENGO_MODEL = "marengo3.0"
API_KEY_ENV = "TWELVE_LABS_API_KEY"
STORE_ID_ENV = "TWELVE_LABS_KNOWLEDGE_STORE_ID"

READ_REQUEST_OPTIONS = {"timeout_in_seconds": 60, "max_retries": 2}
CREATE_REQUEST_OPTIONS = {"timeout_in_seconds": 120, "max_retries": 0}


class TwelveLabsProviderError(RuntimeError):
    """Raised when the provider boundary is unavailable or unsafe."""


def field(value: Any, name: str, default: Any = None) -> Any:
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
        return to_plain(value.model_dump(mode="json", by_alias=True, exclude_none=False))
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


def installed_sdk_version() -> str | None:
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
    """Report readiness without returning credential values."""
    source = os.environ if env is None else env
    installed = installed_sdk_version() if sdk_version is None else sdk_version
    api_key_configured = bool(source.get(API_KEY_ENV))
    store_configured = bool(source.get(STORE_ID_ENV))
    sdk_compatible = installed == SDK_VERSION
    return {
        "provider": "twelvelabs",
        "api_version": API_VERSION,
        "sdk_required": SDK_VERSION,
        "sdk_installed": installed,
        "sdk_compatible": sdk_compatible,
        "api_key_configured": api_key_configured,
        "knowledge_store_configured": store_configured,
        "ready_for_asset_operations": sdk_compatible and api_key_configured,
        "ready_for_pegasus_analysis": sdk_compatible and api_key_configured,
        "ready_for_store_operations": sdk_compatible and api_key_configured,
        "ready_for_jockey": sdk_compatible and api_key_configured and store_configured,
        "ready_for_analysis": sdk_compatible and api_key_configured and store_configured,
    }


def build_client(
    api_key: str | None = None,
    env: Mapping[str, str] | None = None,
) -> Any:
    source = os.environ if env is None else env
    secret = api_key or source.get(API_KEY_ENV)
    if not secret:
        raise TwelveLabsProviderError(f"{API_KEY_ENV} is not configured")
    installed = installed_sdk_version()
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
    ready_statuses: frozenset[str] = frozenset({"ready"}),
    failed_statuses: frozenset[str] = frozenset({"failed"}),
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> Any:
    """Poll one already-created resource with an explicit deadline."""
    if timeout_s <= 0 or poll_interval_s < 0:
        raise ValueError("timeout_s must be positive and poll_interval_s non-negative")
    deadline = monotonic() + timeout_s
    while True:
        resource = fetch()
        status = field(resource, "status")
        if status in ready_statuses:
            return resource
        if status in failed_statuses:
            resource_id = field(resource, "id", field(resource, "task_id", "unknown"))
            raise TwelveLabsProviderError(
                f"{resource_name} failed: id={resource_id} status={status}"
            )
        remaining = deadline - monotonic()
        if remaining <= 0:
            resource_id = field(resource, "id", field(resource, "task_id", "unknown"))
            raise TwelveLabsProviderError(
                f"{resource_name} timed out after {timeout_s:g}s: "
                f"id={resource_id} status={status or 'unknown'}"
            )
        sleep(min(poll_interval_s, remaining))
