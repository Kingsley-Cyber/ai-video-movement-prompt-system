"""Process-safe read and write transactions for second-brain authority."""

from __future__ import annotations

import functools
import inspect
import json
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Literal, TypeVar, cast

from .validate import REPO_ROOT

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised only on non-POSIX hosts
    fcntl = None  # type: ignore[assignment]

LOCK_SCHEMA = "cpcs.authority_lock/1.1"
LOCK_RELATIVE_PATH = Path("work/locks/second_brain_authority.lock")
LockMode = Literal["shared", "exclusive"]
_FUNCTION = TypeVar("_FUNCTION", bound=Callable[..., Any])
_LOCAL_LOCKS: dict[Path, threading.RLock] = {}
_LOCAL_LOCKS_GUARD = threading.Lock()
_THREAD_STATE = threading.local()


class AuthorityBusy(RuntimeError):
    """Raised before a transaction reads authority when an incompatible owner exists."""

    def __init__(
        self,
        actor: str,
        holder: dict[str, Any] | None,
        *,
        mode: LockMode = "exclusive",
    ) -> None:
        self.actor = actor
        self.holder = holder
        self.mode = mode
        detail = "unknown holder"
        if holder is not None:
            detail = (
                f"actor={holder.get('actor', 'unknown')} "
                f"pid={holder.get('pid', 'unknown')} "
                f"mode={holder.get('mode', 'unknown')}"
            )
        super().__init__(f"second-brain authority {mode} transaction is busy ({detail})")


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
    return (
        value
        if (
            isinstance(value, dict)
            and value.get("schema") == LOCK_SCHEMA
            and "released_at" not in value
        )
        else None
    )


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
    mode: LockMode = "exclusive",
) -> Iterator[dict[str, Any]]:
    """Acquire one nonblocking repository-wide shared or exclusive transaction.

    The operating system releases ``flock`` ownership if the process dies. Metadata is diagnostic
    only and is never used to break or steal a lock.
    """
    if not isinstance(actor, str) or not actor or len(actor) > 64:
        raise ValueError("authority transaction actor must be a short non-empty string")
    if mode not in {"shared", "exclusive"}:
        raise ValueError("authority transaction mode must be shared or exclusive")
    if fcntl is None:
        raise RuntimeError(
            "second-brain authority transactions require the declared posix_flock runtime"
        )
    resolved_root = Path(root).expanduser().resolve()
    claims = _thread_claims()
    existing = claims.get(resolved_root)
    if existing is not None:
        if existing["mode"] == "shared" and mode == "exclusive":
            raise RuntimeError(
                "cannot upgrade a shared authority transaction to exclusive"
            )
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
        raise AuthorityBusy(
            actor,
            {
                "actor": "same_process_other_thread",
                "pid": os.getpid(),
                "mode": "unknown",
            },
            mode=mode,
        )
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
            operation = fcntl.LOCK_SH if mode == "shared" else fcntl.LOCK_EX
            fcntl.flock(handle.fileno(), operation | fcntl.LOCK_NB)
        except BlockingIOError as error:
            holder = _read_holder(handle)
            if holder is None:
                holder = {
                    "actor": (
                        "shared_readers" if mode == "exclusive" else "exclusive_writer"
                    ),
                    "pid": "unknown",
                    "mode": "shared" if mode == "exclusive" else "exclusive",
                }
            raise AuthorityBusy(actor, holder, mode=mode) from error
        receipt = {
            "schema": LOCK_SCHEMA,
            "actor": actor,
            "mode": mode,
            "pid": os.getpid(),
            "thread_id": threading.get_ident(),
            "acquired_at": _utc_now(),
        }
        if mode == "exclusive":
            _write_holder(handle, receipt)
        claims[resolved_root] = {
            "actor": actor,
            "mode": mode,
            "depth": 1,
            "nested_actors": [],
            "receipt": receipt,
        }
        try:
            yield receipt
        finally:
            claims.pop(resolved_root, None)
            if mode == "exclusive":
                try:
                    _write_holder(handle, {**receipt, "released_at": _utc_now()})
                except OSError:
                    pass
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        if handle is not None:
            handle.close()
        local.release()


def _authority_operation(
    actor: str,
    mode: LockMode,
) -> Callable[[_FUNCTION], _FUNCTION]:
    """Wrap a complete rooted function in one authority transaction."""

    def decorate(function: _FUNCTION) -> _FUNCTION:
        signature = inspect.signature(function)

        @functools.wraps(function)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            bound = signature.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            root = Path(bound.arguments.get("root", REPO_ROOT))
            with authority_transaction(root, actor=actor, mode=mode):
                return function(*args, **kwargs)

        return cast(_FUNCTION, wrapped)

    return decorate


def authority_writer(actor: str) -> Callable[[_FUNCTION], _FUNCTION]:
    """Wrap a complete writer in an exclusive authority transaction."""
    return _authority_operation(actor, "exclusive")


def authority_reader(actor: str) -> Callable[[_FUNCTION], _FUNCTION]:
    """Wrap a complete multi-file read in a shared authority transaction."""
    return _authority_operation(actor, "shared")
