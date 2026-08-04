"""Process-safe transaction boundary for second-brain authority writers."""

from __future__ import annotations

import functools
import inspect
import json
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, TypeVar, cast

from .validate import REPO_ROOT

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised only on non-POSIX hosts
    fcntl = None  # type: ignore[assignment]

LOCK_SCHEMA = "cpcs.authority_lock/1.0"
LOCK_RELATIVE_PATH = Path("work/locks/second_brain_authority.lock")
_FUNCTION = TypeVar("_FUNCTION", bound=Callable[..., Any])
_LOCAL_LOCKS: dict[Path, threading.RLock] = {}
_LOCAL_LOCKS_GUARD = threading.Lock()
_THREAD_STATE = threading.local()


class AuthorityBusy(RuntimeError):
    """Raised before a writer reads authority when another transaction owns it."""

    def __init__(self, actor: str, holder: dict[str, Any] | None) -> None:
        self.actor = actor
        self.holder = holder
        detail = "unknown holder"
        if holder is not None:
            detail = f"actor={holder.get('actor', 'unknown')} pid={holder.get('pid', 'unknown')}"
        super().__init__(f"second-brain authority is busy ({detail})")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _local_lock(root: Path) -> threading.RLock:
    with _LOCAL_LOCKS_GUARD:
        return _LOCAL_LOCKS.setdefault(root, threading.RLock())


def _thread_claims() -> dict[Path, dict[str, Any]]:
    claims = getattr(_THREAD_STATE, "claims", None)
    if claims is None:
        claims = {}
        _THREAD_STATE.claims = claims
    return cast(dict[Path, dict[str, Any]], claims)


def _lock_path(root: Path) -> Path:
    resolved_root = root.expanduser().resolve()
    work = resolved_root / "work"
    locks = work / "locks"
    for candidate in (work, locks):
        if candidate.is_symlink():
            raise RuntimeError(f"authority lock directory cannot be a symlink: {candidate}")
        candidate.mkdir(exist_ok=True)
        resolved = candidate.resolve()
        if resolved_root not in resolved.parents:
            raise RuntimeError("authority lock directory escaped the repository root")
    return locks / LOCK_RELATIVE_PATH.name


def _read_holder(handle: Any) -> dict[str, Any] | None:
    try:
        handle.seek(0)
        raw = handle.read(4096)
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) and value.get("schema") == LOCK_SCHEMA else None


def _write_holder(handle: Any, value: dict[str, Any]) -> None:
    payload = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    handle.seek(0)
    handle.truncate()
    handle.write(payload)
    handle.flush()
    os.fsync(handle.fileno())


@contextmanager
def authority_transaction(
    root: Path = REPO_ROOT,
    *,
    actor: str,
) -> Iterator[dict[str, Any]]:
    """Acquire one nonblocking repository-wide writer transaction.

    The operating system releases ``flock`` ownership if the process dies. Metadata is diagnostic
    only and is never used to break or steal a lock.
    """
    if not isinstance(actor, str) or not actor or len(actor) > 64:
        raise ValueError("authority transaction actor must be a short non-empty string")
    if fcntl is None:
        raise RuntimeError(
            "second-brain authority writers require the declared posix_flock runtime"
        )
    resolved_root = Path(root).expanduser().resolve()
    claims = _thread_claims()
    existing = claims.get(resolved_root)
    if existing is not None:
        existing["depth"] += 1
        existing["nested_actors"].append(actor)
        try:
            yield cast(dict[str, Any], existing["receipt"])
        finally:
            existing["nested_actors"].pop()
            existing["depth"] -= 1
        return

    local = _local_lock(resolved_root)
    if not local.acquire(blocking=False):
        raise AuthorityBusy(actor, {"actor": "same_process_other_thread", "pid": os.getpid()})
    handle = None
    try:
        path = _lock_path(resolved_root)
        if path.is_symlink():
            raise RuntimeError(f"authority lock file cannot be a symlink: {path}")
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags, 0o600)
        os.fchmod(descriptor, 0o600)
        handle = os.fdopen(descriptor, "r+b", buffering=0)
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise AuthorityBusy(actor, _read_holder(handle)) from error
        receipt = {
            "schema": LOCK_SCHEMA,
            "actor": actor,
            "pid": os.getpid(),
            "thread_id": threading.get_ident(),
            "acquired_at": _utc_now(),
        }
        _write_holder(handle, receipt)
        claims[resolved_root] = {
            "actor": actor,
            "depth": 1,
            "nested_actors": [],
            "receipt": receipt,
        }
        try:
            yield receipt
        finally:
            claims.pop(resolved_root, None)
            try:
                _write_holder(handle, {**receipt, "released_at": _utc_now()})
            except OSError:
                pass
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        if handle is not None:
            handle.close()
        local.release()


def authority_writer(actor: str) -> Callable[[_FUNCTION], _FUNCTION]:
    """Wrap a complete writer function in the rooted authority transaction."""

    def decorate(function: _FUNCTION) -> _FUNCTION:
        signature = inspect.signature(function)

        @functools.wraps(function)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            bound = signature.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            root = Path(bound.arguments.get("root", REPO_ROOT))
            with authority_transaction(root, actor=actor):
                return function(*args, **kwargs)

        return cast(_FUNCTION, wrapped)

    return decorate
