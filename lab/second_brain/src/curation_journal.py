"""Crash-recoverable write-ahead transactions for curated authority files."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .authority import authority_writer
from .validate import (
    REPO_ROOT,
    assert_write_target,
    canonical_json_bytes,
    validate_curated,
    validate_instance,
)

JOURNAL_SCHEMA = "cpcs.curated_transaction/1.0"
JOURNAL_RELATIVE_PATH = Path("work/curation_transactions")
MAX_MANIFEST_BYTES = 1_048_576
MAX_TRANSACTION_BYTES = 268_435_456
MAX_TARGETS = 5
MAX_PREPARING = 64
_TRANSACTION_ID = re.compile(r"curation_tx_[0-9a-f]{24}")
_ALLOWED_TARGETS = frozenset(
    {
        "lab/concepts.jsonl",
        "lab/second_brain/curated/edges.jsonl",
        "lab/second_brain/curated/rules.jsonl",
        "lab/second_brain/curated/intents.jsonl",
        "lab/second_brain/curated/mappings.jsonl",
    }
)


class CurationJournalError(RuntimeError):
    """Raised when a curated transaction cannot be trusted or recovered."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _safe_directory(path: Path, root: Path, *, mode: int = 0o700) -> Path:
    if path.is_symlink():
        raise CurationJournalError(f"curation journal directory cannot be a symlink: {path}")
    path.mkdir(exist_ok=True)
    os.chmod(path, mode)
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise CurationJournalError("curation journal directory escaped the repository root")
    return resolved


def _journal_directories(root: Path) -> dict[str, Path]:
    resolved_root = root.expanduser().resolve()
    work = _safe_directory(resolved_root / "work", resolved_root)
    journal = _safe_directory(work / JOURNAL_RELATIVE_PATH.name, resolved_root)
    active = _safe_directory(journal / "active", resolved_root)
    preparing = _safe_directory(journal / "preparing", resolved_root)
    receipts = _safe_directory(journal / "receipts", resolved_root)
    committed = _safe_directory(receipts / "committed", resolved_root)
    recovered = _safe_directory(receipts / "recovered_rollback", resolved_root)
    abandoned = _safe_directory(receipts / "abandoned_preparation", resolved_root)
    return {
        "root": journal,
        "active": active,
        "preparing": preparing,
        "committed": committed,
        "recovered_rollback": recovered,
        "abandoned_preparation": abandoned,
    }


def _write_new_file(path: Path, payload: bytes, mode: int) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, mode)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)


def _replace_file(path: Path, payload: bytes, mode: int, temporary: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise CurationJournalError(f"curated transaction target is missing or unsafe: {path}")
    if temporary.exists() or temporary.is_symlink():
        raise CurationJournalError(f"curated transaction temporary path already exists: {temporary}")
    _write_new_file(temporary, payload, mode)
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def _identity_core(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": manifest["schema"],
        "nonce": manifest["nonce"],
        "operation": manifest["operation"],
        "operation_id": manifest["operation_id"],
        "created_at": manifest["created_at"],
        "targets": manifest["targets"],
    }


def _validate_identity(manifest: dict[str, Any], directory: Path, root: Path) -> None:
    validate_instance("curated_transaction", manifest, root)
    digest = hashlib.sha256(canonical_json_bytes(_identity_core(manifest))).hexdigest()
    if manifest["transaction_id"] != "curation_tx_" + digest[:24]:
        raise CurationJournalError("curated transaction ID is not content-bound")
    if manifest["transaction_hash"] != "sha256:" + digest:
        raise CurationJournalError("curated transaction hash is invalid")
    if directory.name != manifest["transaction_id"]:
        raise CurationJournalError("curated transaction directory identity differs")
    paths = [row["path"] for row in manifest["targets"]]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise CurationJournalError("curated transaction targets must be sorted and unique")
    if not set(paths) <= _ALLOWED_TARGETS:
        raise CurationJournalError("curated transaction contains an unauthorized target")
    total = sum(
        row[side]["size_bytes"]
        for row in manifest["targets"]
        for side in ("before", "after")
    )
    if total > MAX_TRANSACTION_BYTES:
        raise CurationJournalError("curated transaction exceeds the recovery byte limit")
    for index, row in enumerate(manifest["targets"]):
        for side in ("before", "after"):
            expected_blob = f"{side}/{index:03d}.bin"
            if row[side]["blob"] != expected_blob:
                raise CurationJournalError("curated transaction blob placement is invalid")


def _safe_blob(directory: Path, value: str) -> Path:
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or len(relative.parts) != 2
        or relative.parts[0] not in {"before", "after"}
    ):
        raise CurationJournalError(f"unsafe curated transaction blob path: {value}")
    path = directory.joinpath(*relative.parts)
    if path.is_symlink() or not path.is_file() or directory not in path.resolve().parents:
        raise CurationJournalError(f"curated transaction blob is missing or unsafe: {value}")
    return path


def _remove_manifest_temporary(directory: Path) -> None:
    temporary = directory / ".manifest.tmp"
    if not temporary.exists() and not temporary.is_symlink():
        return
    if temporary.is_symlink() or not temporary.is_file():
        raise CurationJournalError("curated transaction manifest temporary is unsafe")
    temporary.unlink()
    _fsync_directory(directory)


def _load_manifest(directory: Path, root: Path) -> dict[str, Any]:
    if directory.is_symlink() or not directory.is_dir() or not _TRANSACTION_ID.fullmatch(directory.name):
        raise CurationJournalError(f"unsafe active curated transaction: {directory}")
    _remove_manifest_temporary(directory)
    manifest_path = directory / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise CurationJournalError("curated transaction manifest is missing or unsafe")
    if manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
        raise CurationJournalError("curated transaction manifest exceeds its byte limit")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CurationJournalError("curated transaction manifest is unreadable") from error
    if not isinstance(manifest, dict):
        raise CurationJournalError("curated transaction manifest must be an object")
    _validate_identity(manifest, directory, root)
    expected_files = {"manifest.json"}
    for row in manifest["targets"]:
        for side in ("before", "after"):
            blob = _safe_blob(directory, row[side]["blob"])
            expected_files.add(row[side]["blob"])
            raw = blob.read_bytes()
            if len(raw) != row[side]["size_bytes"] or _sha256_bytes(raw) != row[side]["sha256"]:
                raise CurationJournalError("curated transaction recovery blob differs from its manifest")
    observed_files = {
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    if observed_files != expected_files:
        raise CurationJournalError("curated transaction contains unexpected recovery files")
    return manifest


def _manifest_payload(manifest: dict[str, Any], state: str) -> bytes:
    value = {**manifest, "state": state}
    return canonical_json_bytes(value)


def _replace_manifest(directory: Path, manifest: dict[str, Any], state: str) -> dict[str, Any]:
    temporary = directory / ".manifest.tmp"
    _write_new_file(temporary, _manifest_payload(manifest, state), 0o600)
    os.replace(temporary, directory / "manifest.json")
    _fsync_directory(directory)
    return {**manifest, "state": state}


def _target_path(root: Path, relative: str) -> Path:
    if relative not in _ALLOWED_TARGETS:
        raise CurationJournalError(f"unauthorized curated transaction target: {relative}")
    target = root.joinpath(*PurePosixPath(relative).parts)
    assert_write_target("curate", target, root)
    if target.is_symlink() or not target.is_file():
        raise CurationJournalError(f"curated transaction target is missing or unsafe: {relative}")
    if target.stat().st_nlink != 1:
        raise CurationJournalError(f"curated transaction target must not be hard-linked: {relative}")
    return target


def _temporary_target(path: Path, transaction_id: str) -> Path:
    return path.parent / f".{path.name}.{transaction_id}.tmp"


def _clear_target_temporary(path: Path, transaction_id: str) -> None:
    temporary = _temporary_target(path, transaction_id)
    if not temporary.exists() and not temporary.is_symlink():
        return
    if temporary.is_symlink() or not temporary.is_file():
        raise CurationJournalError(f"curated transaction temporary is unsafe: {temporary}")
    temporary.unlink()
    _fsync_directory(path.parent)


def _atomic_replace_target(
    path: Path,
    payload: bytes,
    mode: int,
    transaction_id: str,
) -> None:
    temporary = _temporary_target(path, transaction_id)
    _replace_file(path, payload, mode, temporary)


def _archive(directory: Path, manifest: dict[str, Any], directories: dict[str, Path]) -> Path:
    destination = directories[manifest["state"]] / directory.name
    if destination.exists() or destination.is_symlink():
        raise CurationJournalError("curated transaction receipt already exists")
    os.replace(directory, destination)
    try:
        _fsync_directory(directories[manifest["state"]])
        _fsync_directory(directories["active"])
    except OSError:
        # Receipt placement is diagnostic after the authority state is already durable.
        pass
    return destination


def _archive_abandoned_preparations(
    directories: dict[str, Path], root: Path
) -> list[dict[str, Any]]:
    preparing = sorted(directories["preparing"].iterdir(), key=lambda path: path.name)
    if len(preparing) > MAX_PREPARING:
        raise CurationJournalError("too many abandoned curated transaction preparations")
    receipts = []
    for path in preparing:
        if path.is_symlink() or not path.is_dir() or not _TRANSACTION_ID.fullmatch(path.name):
            raise CurationJournalError(f"unsafe curated transaction preparation: {path}")
        destination = directories["abandoned_preparation"] / path.name
        if destination.exists() or destination.is_symlink():
            raise CurationJournalError("abandoned curated transaction receipt already exists")
        os.replace(path, destination)
        receipts.append(
            {
                "transaction_id": path.name,
                "operation": None,
                "operation_id": None,
                "disposition": "abandoned_preparation",
                "receipt": str(destination.relative_to(root)),
            }
        )
    if preparing:
        _fsync_directory(directories["preparing"])
        _fsync_directory(directories["abandoned_preparation"])
    return receipts


def _recover_one(
    directory: Path,
    root: Path,
    directories: dict[str, Path],
) -> dict[str, Any]:
    manifest = _load_manifest(directory, root)
    states: list[str] = []
    for row in manifest["targets"]:
        target = _target_path(root, row["path"])
        _clear_target_temporary(target, manifest["transaction_id"])
        current = _sha256_bytes(target.read_bytes())
        if current == row["before"]["sha256"]:
            states.append("before")
        elif current == row["after"]["sha256"]:
            states.append("after")
        else:
            raise CurationJournalError(
                f"curated target differs from both journal states: {row['path']}"
            )
    state = manifest["state"]
    if state == "prepared":
        for row, current in zip(manifest["targets"], states):
            if current == "before":
                continue
            target = _target_path(root, row["path"])
            payload = _safe_blob(directory, row["before"]["blob"]).read_bytes()
            _atomic_replace_target(
                target,
                payload,
                row["mode"],
                manifest["transaction_id"],
            )
        validate_curated(
            root,
            allow_recoverable_legacy_reciprocals=(
                manifest["operation"] == "consolidate_reciprocal_edges"
            ),
        )
        manifest = _replace_manifest(directory, manifest, "recovered_rollback")
    elif state == "committed":
        if any(current != "after" for current in states):
            raise CurationJournalError("committed curated transaction has incomplete targets")
        validate_curated(root)
    elif state == "recovered_rollback":
        if any(current != "before" for current in states):
            raise CurationJournalError("recovered curated transaction has non-rollback targets")
        validate_curated(
            root,
            allow_recoverable_legacy_reciprocals=(
                manifest["operation"] == "consolidate_reciprocal_edges"
            ),
        )
    else:  # JSON Schema also rejects this; keep the state machine explicit.
        raise CurationJournalError(f"unsupported curated transaction state: {state}")
    receipt = _archive(directory, manifest, directories)
    return {
        "transaction_id": manifest["transaction_id"],
        "operation": manifest["operation"],
        "operation_id": manifest["operation_id"],
        "disposition": manifest["state"],
        "receipt": str(receipt.relative_to(root)),
    }


@authority_writer("curation_recovery")
def recover_curated_transactions(root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    """Recover every fully prepared transaction before curated authority is read."""
    resolved_root = root.expanduser().resolve()
    directories = _journal_directories(resolved_root)
    receipts = _archive_abandoned_preparations(directories, resolved_root)
    active = sorted(directories["active"].iterdir(), key=lambda path: path.name)
    if len(active) > 1:
        raise CurationJournalError("more than one active curated transaction exists")
    receipts.extend(_recover_one(path, resolved_root, directories) for path in active)
    return receipts


def _prepare_transaction(
    root: Path,
    operation: str,
    operation_id: str,
    updates: Mapping[Path, bytes],
) -> tuple[Path, dict[str, Any], dict[str, Path]]:
    if operation not in {
        "promote_proposal",
        "promote_distillation_bundle",
        "consolidate_reciprocal_edges",
    }:
        raise ValueError(f"unsupported curated transaction operation: {operation}")
    if not isinstance(operation_id, str) or not operation_id or len(operation_id) > 256:
        raise ValueError("curated transaction operation ID must be a bounded string")
    if not updates or len(updates) > MAX_TARGETS:
        raise ValueError("curated transaction target count is invalid")
    resolved_root = root.expanduser().resolve()
    directories = _journal_directories(resolved_root)
    if any(directories["active"].iterdir()):
        raise CurationJournalError("active curated transaction must be recovered first")
    targets = []
    raw_targets = []
    for path, after in updates.items():
        relative = path.expanduser().resolve().relative_to(resolved_root).as_posix()
        target = _target_path(resolved_root, relative)
        before = target.read_bytes()
        if not isinstance(after, bytes) or after == before:
            raise ValueError("curated transaction updates must be changed byte strings")
        raw_targets.append((target, before, after, target.stat().st_mode & 0o777))
    raw_targets.sort(key=lambda row: row[0].relative_to(resolved_root).as_posix())
    for index, (target, before, after, mode) in enumerate(raw_targets):
        targets.append(
            {
                "path": target.relative_to(resolved_root).as_posix(),
                "mode": mode,
                "before": {
                    "blob": f"before/{index:03d}.bin",
                    "size_bytes": len(before),
                    "sha256": _sha256_bytes(before),
                },
                "after": {
                    "blob": f"after/{index:03d}.bin",
                    "size_bytes": len(after),
                    "sha256": _sha256_bytes(after),
                },
            }
        )
    if sum(len(before) + len(after) for _, before, after, _ in raw_targets) > MAX_TRANSACTION_BYTES:
        raise ValueError("curated transaction exceeds the recovery byte limit")
    core = {
        "schema": JOURNAL_SCHEMA,
        "nonce": uuid.uuid4().hex,
        "operation": operation,
        "operation_id": operation_id,
        "created_at": _utc_now(),
        "targets": targets,
    }
    digest = hashlib.sha256(canonical_json_bytes(core)).hexdigest()
    manifest = {
        **core,
        "transaction_id": "curation_tx_" + digest[:24],
        "transaction_hash": "sha256:" + digest,
        "state": "prepared",
    }
    validate_instance("curated_transaction", manifest, resolved_root)
    preparing = directories["preparing"] / manifest["transaction_id"]
    active = directories["active"] / manifest["transaction_id"]
    if preparing.exists() or preparing.is_symlink() or active.exists() or active.is_symlink():
        raise CurationJournalError("curated transaction identity already exists")
    preparing.mkdir(mode=0o700)
    (preparing / "before").mkdir(mode=0o700)
    (preparing / "after").mkdir(mode=0o700)
    for index, (_, before, after, _) in enumerate(raw_targets):
        _write_new_file(preparing / "before" / f"{index:03d}.bin", before, 0o600)
        _write_new_file(preparing / "after" / f"{index:03d}.bin", after, 0o600)
    _fsync_directory(preparing / "before")
    _fsync_directory(preparing / "after")
    _write_new_file(preparing / "manifest.json", canonical_json_bytes(manifest), 0o600)
    _fsync_directory(preparing)
    os.replace(preparing, active)
    _fsync_directory(directories["preparing"])
    _fsync_directory(directories["active"])
    return active, manifest, directories


@authority_writer("curation")
def apply_curated_transaction(
    root: Path,
    *,
    operation: str,
    operation_id: str,
    updates: Mapping[Path, bytes],
) -> dict[str, Any]:
    """Apply exact curated file images or roll them all back after any live failure."""
    resolved_root = root.expanduser().resolve()
    recover_curated_transactions(resolved_root)
    active, manifest, directories = _prepare_transaction(
        resolved_root,
        operation,
        operation_id,
        updates,
    )
    try:
        for row in manifest["targets"]:
            target = _target_path(resolved_root, row["path"])
            payload = _safe_blob(active, row["after"]["blob"]).read_bytes()
            _atomic_replace_target(
                target,
                payload,
                row["mode"],
                manifest["transaction_id"],
            )
        validate_curated(resolved_root)
        manifest = _replace_manifest(active, manifest, "committed")
        receipt = _archive(active, manifest, directories)
        return {
            "transaction_id": manifest["transaction_id"],
            "transaction_hash": manifest["transaction_hash"],
            "state": manifest["state"],
            "receipt": str(receipt.relative_to(resolved_root)),
        }
    except BaseException:
        try:
            recovery = _recover_one(active, resolved_root, directories)
        except Exception as recovery_error:
            try:
                durable = _load_manifest(active, resolved_root)
            except Exception:
                durable = None
            if durable is not None and durable["state"] == "committed":
                return {
                    "transaction_id": durable["transaction_id"],
                    "transaction_hash": durable["transaction_hash"],
                    "state": "committed",
                    "receipt": str(active.relative_to(resolved_root)),
                    "completion_recovered": True,
                    "receipt_archive_pending": True,
                }
            raise CurationJournalError(
                "curated transaction failed and automatic rollback could not be proven"
            ) from recovery_error
        if recovery["disposition"] == "committed":
            return {
                "transaction_id": manifest["transaction_id"],
                "transaction_hash": manifest["transaction_hash"],
                "state": "committed",
                "receipt": recovery["receipt"],
                "completion_recovered": True,
            }
        raise


def curation_journal_status(root: Path = REPO_ROOT) -> dict[str, Any]:
    """Return bounded operational state without reading authority or mutating journals."""
    resolved_root = root.expanduser().resolve()
    journal = resolved_root / JOURNAL_RELATIVE_PATH
    if not journal.exists() and not journal.is_symlink():
        return {
            "schema": "cpcs.curation_journal_status/1.0",
            "active": [],
            "preparing": [],
            "committed_receipts": 0,
            "recovered_receipts": 0,
            "abandoned_receipts": 0,
            "max_targets": MAX_TARGETS,
            "max_transaction_bytes": MAX_TRANSACTION_BYTES,
        }
    if journal.is_symlink() or not journal.is_dir() or resolved_root not in journal.resolve().parents:
        raise CurationJournalError("curation journal root is missing or unsafe")

    def entries(relative: str) -> list[str]:
        directory = journal / relative
        if not directory.exists() and not directory.is_symlink():
            return []
        if (
            directory.is_symlink()
            or not directory.is_dir()
            or resolved_root not in directory.resolve().parents
        ):
            raise CurationJournalError(f"curation journal status path is unsafe: {relative}")
        return sorted(path.name for path in directory.iterdir())

    return {
        "schema": "cpcs.curation_journal_status/1.0",
        "active": entries("active"),
        "preparing": entries("preparing"),
        "committed_receipts": len(entries("receipts/committed")),
        "recovered_receipts": len(entries("receipts/recovered_rollback")),
        "abandoned_receipts": len(entries("receipts/abandoned_preparation")),
        "max_targets": MAX_TARGETS,
        "max_transaction_bytes": MAX_TRANSACTION_BYTES,
    }
