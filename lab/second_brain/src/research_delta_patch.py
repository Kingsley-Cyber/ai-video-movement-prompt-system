"""Approval-bound execution of one Research Delta patch in an isolated Git worktree."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

from .research_delta import _read_plan, _target_spec
from .validate import (
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    canonical_json_bytes,
    sha256_value,
    validate_instance,
)


PATCH_POLICY = "cpcs-research-delta-patch/1.0"
EXECUTION_ID_PATTERN = re.compile(r"research_patch_[0-9a-f]{24}")
SAFE_PATH_PATTERN = re.compile(r"[A-Za-z0-9_./-]+")
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
COMMAND_TIMEOUT_SECONDS = 900


def _bytes_hash(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _file_hash(path: Path) -> str:
    return _bytes_hash(path.read_bytes())


def _restricted_environment(worktree: Path) -> dict[str, str]:
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
        "PYTHONPATH": str(worktree),
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }
    if os.environ.get("TMPDIR"):
        environment["TMPDIR"] = os.environ["TMPDIR"]
    return environment


def _run(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int = COMMAND_TIMEOUT_SECONDS,
    check: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=_restricted_environment(cwd),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValidationFailure(f"cannot execute fixed patch command {argv!r}: {error}") from error
    if check and completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ValidationFailure(
            f"fixed patch command failed ({completed.returncode}): {argv!r}: {detail}"
        )
    return completed


def _git(root: Path, arguments: list[str], *, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return _run(
        ["git", "-c", "core.hooksPath=/dev/null", *arguments],
        cwd=root,
        timeout=60,
        check=check,
    )


def _repository_state(root: Path) -> tuple[str, list[str]]:
    top = _git(root, ["rev-parse", "--show-toplevel"]).stdout.decode().strip()
    if Path(top).resolve() != root.resolve():
        raise ValidationFailure("patch execution root is not the Git top-level checkout")
    revision = _git(root, ["rev-parse", "HEAD"]).stdout.decode().strip()
    if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValidationFailure("patch execution baseline revision is invalid")
    rows = _git(root, ["status", "--short", "--untracked-files=all"]).stdout.decode().splitlines()
    dirty = sorted({row[3:] for row in rows if len(row) > 3})
    return revision, dirty


def _patch_root(root: Path, *, create: bool) -> Path:
    repository = root.resolve()
    current = repository
    for part in ("work", "application", "research_delta_patches"):
        current = current / part
        if current.is_symlink():
            raise ValidationFailure(f"research patch path cannot be a symlink: {current}")
        if create:
            current.mkdir(mode=0o700, exist_ok=True)
            os.chmod(current, 0o700)
    if not current.is_dir():
        raise ValidationFailure("research patch operational root does not exist")
    resolved = current.resolve()
    if repository not in resolved.parents:
        raise ValidationFailure("research patch operational root escaped the repository")
    return resolved


def _execution_directory(execution_id: str, root: Path, *, create: bool) -> Path:
    if EXECUTION_ID_PATTERN.fullmatch(execution_id) is None:
        raise ValidationFailure("research patch execution ID is invalid")
    base = _patch_root(root, create=create)
    directory = base / execution_id
    if directory.is_symlink():
        raise ValidationFailure("research patch execution directory cannot be a symlink")
    if create:
        directory.mkdir(mode=0o700, exist_ok=True)
        os.chmod(directory, 0o700)
    if not directory.is_dir() or base not in directory.resolve().parents:
        raise ValidationFailure("research patch execution directory escaped its operational root")
    return directory


def _artifact_path(directory: Path, name: str) -> Path:
    if name not in {
        "request.json", "patch.diff", "state.json", "receipt.json", "cleanup.json"
    }:
        raise ValidationFailure("research patch artifact name is not allowed")
    path = directory / name
    if path.is_symlink():
        raise ValidationFailure(f"research patch artifact cannot be a symlink: {name}")
    return path


def _write_new_bytes(path: Path, payload: bytes) -> None:
    if len(payload) > MAX_ARTIFACT_BYTES:
        raise ValidationFailure("research patch artifact exceeds the operational size limit")
    if path.exists():
        if path.is_symlink() or path.read_bytes() != payload:
            raise ValidationFailure("research patch artifact identity collision")
        return
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)


def _write_new_json(path: Path, value: dict[str, Any]) -> None:
    _write_new_bytes(path, canonical_json_bytes(value))


def _replace_json(path: Path, value: dict[str, Any]) -> None:
    payload = canonical_json_bytes(value)
    if len(payload) > MAX_ARTIFACT_BYTES:
        raise ValidationFailure("research patch state exceeds the operational size limit")
    if path.is_symlink():
        raise ValidationFailure("research patch state cannot be a symlink")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


def _read_json(path: Path, schema_name: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValidationFailure(f"missing or unsafe research patch artifact: {path.name}")
    if path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValidationFailure("research patch artifact exceeds the operational size limit")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationFailure(f"cannot read research patch artifact {path.name}: {error}") from error
    if not isinstance(value, dict):
        raise ValidationFailure(f"research patch artifact {path.name} must be an object")
    validate_instance(schema_name, value, path.parents[4])
    return value


def _hashed_state(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result.pop("state_hash", None)
    result["state_hash"] = sha256_value(result)
    return result


def _validate_state(value: dict[str, Any], root: Path) -> None:
    validate_instance("research_delta_patch_state", value, root)
    unsigned = copy.deepcopy(value)
    claimed = unsigned.pop("state_hash")
    if sha256_value(unsigned) != claimed:
        raise ValidationFailure("research patch state hash does not match its content")
    if value["next_command_index"] != len(value["command_results"]):
        raise ValidationFailure("research patch state command cursor is inconsistent")
    if value["next_command_index"] > value["total_commands"]:
        raise ValidationFailure("research patch state command cursor exceeds the command list")
    if value["phase"] == "passed" and value["next_command_index"] != value["total_commands"]:
        raise ValidationFailure("passed research patch state has incomplete commands")
    if value["phase"] == "failed":
        if not value["command_results"] or value["command_results"][-1]["exit_code"] == 0:
            raise ValidationFailure("failed research patch state lacks a failed command")


def _validate_hashed_record(value: dict[str, Any], hash_field: str, schema_name: str, root: Path) -> None:
    validate_instance(schema_name, value, root)
    unsigned = copy.deepcopy(value)
    claimed = unsigned.pop(hash_field)
    if sha256_value(unsigned) != claimed:
        raise ValidationFailure(f"research patch {hash_field} does not match its content")


def _safe_patch_path(value: str) -> str:
    if (
        SAFE_PATH_PATTERN.fullmatch(value) is None
        or value.startswith("/")
        or "\\" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or value.startswith(".git/")
        or value == ".git"
    ):
        raise ValidationFailure(f"unsafe unified-diff path: {value!r}")
    return value


def _parse_patch(patch_text: str) -> list[str]:
    if not patch_text.endswith("\n"):
        raise ValidationFailure("unified diff must end with a newline")
    if "GIT binary patch" in patch_text or "Binary files " in patch_text:
        raise ValidationFailure("binary patches are not allowed")
    paths: list[str] = []
    current: str | None = None
    old_seen = False
    new_seen = False
    in_hunk = False
    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split(" ")
            if len(parts) != 4 or not parts[2].startswith("a/") or not parts[3].startswith("b/"):
                raise ValidationFailure("unified diff header is malformed")
            old = _safe_patch_path(parts[2][2:])
            new = _safe_patch_path(parts[3][2:])
            if old != new:
                raise ValidationFailure("renames and copies are not allowed")
            if current is not None and not (old_seen and new_seen):
                raise ValidationFailure("unified diff is missing exact file markers")
            if new in paths:
                raise ValidationFailure("unified diff contains a duplicate path")
            paths.append(new)
            current = new
            old_seen = False
            new_seen = False
            in_hunk = False
            continue
        if current is None:
            if line.strip():
                raise ValidationFailure("unified diff contains content before its first header")
            continue
        if line.startswith(("rename from ", "rename to ", "copy from ", "copy to ", "deleted file mode ")):
            raise ValidationFailure("renames, copies, and deletions are not allowed")
        if line.startswith("new file mode ") and line != "new file mode 100644" and line != "new file mode 100755":
            raise ValidationFailure("new files must use mode 100644 or 100755")
        if line.startswith(("old mode ", "new mode ")) and not line.endswith(("100644", "100755")):
            raise ValidationFailure("only regular executable-bit mode changes are allowed")
        if line.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk and line.startswith("--- "):
            marker = line[4:].split("\t", 1)[0]
            if marker not in {f"a/{current}", "/dev/null"}:
                raise ValidationFailure("unified diff old-file marker does not match its header")
            old_seen = True
            continue
        if not in_hunk and line.startswith("+++ "):
            marker = line[4:].split("\t", 1)[0]
            if marker != f"b/{current}":
                raise ValidationFailure("file deletions and mismatched new-file markers are not allowed")
            new_seen = True
            continue
    if not paths or current is None or not (old_seen and new_seen):
        raise ValidationFailure("unified diff has no complete text-file change")
    return sorted(paths)


def _path_allowed(path: str, allowed_paths: list[str]) -> bool:
    return any(path.startswith(value) if value.endswith("/") else path == value for value in allowed_paths)


def _proposal_for(plan: dict[str, Any], proposal_id: str) -> dict[str, Any]:
    matches = [
        row for row in plan["implementation_proposals"] if row["proposal_id"] == proposal_id
    ]
    if len(matches) != 1:
        raise ValidationFailure("research patch references an unknown implementation proposal")
    proposal = matches[0]
    spec = _target_spec(proposal["target"], "claim")
    expected_tests = sorted(set(spec["tests"]) | {"python3 lab/scripts/validate_repo.py"})
    if (
        proposal["current_owner"] != spec["owner"]
        or proposal["allowed_paths"] != sorted(spec["allowed_paths"])
        or proposal["affected_contracts"] != sorted(spec["contracts"])
        or proposal["required_tests"] != expected_tests
    ):
        raise ValidationFailure("research patch proposal no longer matches the fixed owner registry")
    return proposal


def _verify_baseline(plan: dict[str, Any], root: Path) -> str:
    baseline = plan["baseline"]
    revision = baseline["repository_revision"]
    if not isinstance(revision, str):
        raise ValidationFailure("research patch requires a Git-backed Research Delta baseline")
    if baseline["dirty_paths"]:
        raise ValidationFailure("research patch refuses a Research Delta plan created from a dirty checkout")
    current_revision, dirty = _repository_state(root)
    if current_revision != revision:
        raise ValidationFailure("research patch baseline revision no longer matches the checkout")
    if dirty:
        raise ValidationFailure("research patch execution requires a clean live checkout")
    for snapshot in baseline["contract_snapshots"]:
        path = root / snapshot["path"]
        exists = path.is_file() and not path.is_symlink()
        actual = _file_hash(path) if exists else None
        if exists != snapshot["exists"] or actual != snapshot["content_hash"]:
            raise ValidationFailure(
                f"research patch affected contract drifted: {snapshot['path']}"
            )
    return revision


def _commands_for(proposal: dict[str, Any]) -> list[list[str]]:
    commands = [shlex.split(value) for value in proposal["required_tests"]]
    if any(not command for command in commands):
        raise ValidationFailure("research patch fixed command registry contains an empty command")
    return commands


def prepare_research_delta_patch(
    request: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Capture and validate patch bytes without executing code."""
    validate_instance("research_delta_patch_request", request, root)
    patch_bytes = request["patch_text"].encode("utf-8")
    if _bytes_hash(patch_bytes) != request["patch_sha256"]:
        raise ValidationFailure("research patch SHA-256 does not match the exact patch bytes")
    plan = _read_plan(request["delta_id"], root)
    proposal = _proposal_for(plan, request["implementation_proposal_id"])
    revision = _verify_baseline(plan, root)
    paths = _parse_patch(request["patch_text"])
    forbidden = [path for path in paths if not _path_allowed(path, proposal["allowed_paths"])]
    if forbidden:
        raise ValidationFailure(
            "research patch targets paths outside the approved proposal: " + ", ".join(forbidden)
        )
    request_hash = sha256_value(request)
    identity = {
        "policy": PATCH_POLICY,
        "request_hash": request_hash,
        "plan_hash": plan["plan_hash"],
        "proposal_id": proposal["proposal_id"],
        "baseline_revision": revision,
        "patch_sha256": request["patch_sha256"],
    }
    execution_id = "research_patch_" + sha256_value(identity)[7:31]
    directory = _execution_directory(execution_id, root, create=True)
    assert_write_target("research_delta_patch", directory / "request.json", root)
    commands = _commands_for(proposal)
    state = _hashed_state(
        {
            "schema": "cpcs.research_delta_patch_state/1.0",
            "execution_id": execution_id,
            "request_hash": request_hash,
            "plan_hash": plan["plan_hash"],
            "proposal_id": proposal["proposal_id"],
            "baseline_revision": revision,
            "patch_sha256": request["patch_sha256"],
            "patch_paths": paths,
            "phase": "prepared",
            "next_command_index": 0,
            "total_commands": len(commands),
            "command_results": [],
        }
    )
    validate_instance("research_delta_patch_state", state, root)
    _write_new_json(_artifact_path(directory, "request.json"), request)
    _write_new_bytes(_artifact_path(directory, "patch.diff"), patch_bytes)
    state_path = _artifact_path(directory, "state.json")
    if state_path.exists():
        existing = _read_json(state_path, "research_delta_patch_state")
        _validate_state(existing, root)
        if existing["execution_id"] != execution_id or existing["request_hash"] != request_hash:
            raise ValidationFailure("research patch state identity collision")
    else:
        _write_new_json(state_path, state)
    return {
        "schema": "cpcs.research_delta_patch_preparation/1.0",
        "execution_id": execution_id,
        "delta_id": request["delta_id"],
        "proposal_id": proposal["proposal_id"],
        "request_hash": request_hash,
        "plan_hash": plan["plan_hash"],
        "baseline_revision": revision,
        "patch_sha256": request["patch_sha256"],
        "patch_paths": paths,
        "commands": commands,
        "status": "prepared",
        "authority": "operational_bytes_only_requires_separate_execution_authorization",
    }


def _load_execution(execution_id: str, root: Path) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    directory = _execution_directory(execution_id, root, create=False)
    request = _read_json(_artifact_path(directory, "request.json"), "research_delta_patch_request")
    if _bytes_hash(request["patch_text"].encode("utf-8")) != request["patch_sha256"]:
        raise ValidationFailure("stored research patch bytes no longer match their SHA-256")
    patch_path = _artifact_path(directory, "patch.diff")
    if patch_path.is_symlink() or _file_hash(patch_path) != request["patch_sha256"]:
        raise ValidationFailure("stored research patch file no longer matches its SHA-256")
    plan = _read_plan(request["delta_id"], root)
    proposal = _proposal_for(plan, request["implementation_proposal_id"])
    state = _read_json(_artifact_path(directory, "state.json"), "research_delta_patch_state")
    _validate_state(state, root)
    if (
        state["execution_id"] != execution_id
        or state["request_hash"] != sha256_value(request)
        or state["plan_hash"] != plan["plan_hash"]
        or state["proposal_id"] != proposal["proposal_id"]
        or state["patch_sha256"] != request["patch_sha256"]
        or state["patch_paths"] != _parse_patch(request["patch_text"])
    ):
        raise ValidationFailure("research patch execution artifacts do not share one identity")
    commands = _commands_for(proposal)
    for expected_index, result in enumerate(state["command_results"]):
        if result["index"] != expected_index or result["argv"] != commands[expected_index]:
            raise ValidationFailure("research patch command history does not match the fixed registry")
        for stream in ("stdout", "stderr"):
            log = directory / "logs" / f"command-{expected_index:02d}.{stream}"
            if log.is_symlink() or not log.is_file():
                raise ValidationFailure("research patch command history is missing a captured log")
            if _file_hash(log) != result[f"{stream}_hash"]:
                raise ValidationFailure("research patch command log hash does not match its content")
    return directory, request, plan, proposal, state


def _worktree_path(directory: Path) -> Path:
    path = directory / "worktree"
    if path.is_symlink():
        raise ValidationFailure("research patch worktree cannot be a symlink")
    if directory.resolve() not in path.parent.resolve().parents and path.parent.resolve() != directory.resolve():
        raise ValidationFailure("research patch worktree escaped its execution directory")
    return path


def _ensure_worktree(root: Path, directory: Path, revision: str) -> Path:
    worktree = _worktree_path(directory)
    if not worktree.exists():
        _git(root, ["worktree", "add", "--detach", str(worktree), revision])
    if not worktree.is_dir():
        raise ValidationFailure("research patch worktree is not a directory")
    actual = _git(worktree, ["rev-parse", "HEAD"]).stdout.decode().strip()
    if actual != revision:
        raise ValidationFailure("research patch worktree revision does not match its baseline")
    return worktree


def _staged_paths(worktree: Path) -> list[str]:
    payload = _git(worktree, ["diff", "--cached", "--name-only", "-z"]).stdout
    return sorted(value.decode("utf-8") for value in payload.split(b"\0") if value)


def _ensure_patch_applied(worktree: Path, patch_path: Path, expected_paths: list[str]) -> str:
    staged = _staged_paths(worktree)
    if staged:
        if staged != expected_paths:
            raise ValidationFailure("research patch worktree contains unexpected staged paths")
    else:
        _git(worktree, ["apply", "--check", "--whitespace=error-all", str(patch_path)])
        _git(worktree, ["apply", "--index", "--whitespace=error-all", str(patch_path)])
        if _staged_paths(worktree) != expected_paths:
            raise ValidationFailure("applied research patch paths differ from the approved patch")
    diff = _git(worktree, ["diff", "--cached", "--binary", "--full-index"]).stdout
    return _bytes_hash(diff)


def _write_log(directory: Path, index: int, stream: str, payload: bytes) -> str:
    if stream not in {"stdout", "stderr"}:
        raise ValidationFailure("research patch log stream is invalid")
    log_directory = directory / "logs"
    if log_directory.is_symlink():
        raise ValidationFailure("research patch log directory cannot be a symlink")
    log_directory.mkdir(mode=0o700, exist_ok=True)
    os.chmod(log_directory, 0o700)
    path = log_directory / f"command-{index:02d}.{stream}"
    _replace_bytes(path, payload)
    return _bytes_hash(payload)


def _replace_bytes(path: Path, payload: bytes) -> None:
    if len(payload) > MAX_ARTIFACT_BYTES:
        raise ValidationFailure("research patch command output exceeds the operational size limit")
    if path.is_symlink():
        raise ValidationFailure("research patch log cannot be a symlink")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


def _validate_worktree_changes(worktree: Path, expected_paths: list[str]) -> None:
    if _staged_paths(worktree) != expected_paths:
        raise ValidationFailure("research patch staged paths changed during qualification")
    unstaged = _git(worktree, ["diff", "--name-only", "-z"]).stdout
    untracked = _git(worktree, ["ls-files", "--others", "--exclude-standard", "-z"]).stdout
    if unstaged or untracked:
        raise ValidationFailure("research patch tests changed files outside the staged patch")


def _make_receipt(
    *,
    directory: Path,
    request: dict[str, Any],
    plan: dict[str, Any],
    state: dict[str, Any],
    staged_diff_hash: str | None,
    worktree: Path,
    status: str,
    failure: str | None,
    root: Path,
) -> dict[str, Any]:
    file_hashes = []
    if staged_diff_hash is not None:
        file_hashes = [
            {"path": path, "content_hash": _file_hash(worktree / path)}
            for path in state["patch_paths"]
        ]
    receipt = {
        "schema": "cpcs.research_delta_patch_receipt/1.0",
        "execution_id": state["execution_id"],
        "delta_id": request["delta_id"],
        "proposal_id": state["proposal_id"],
        "request_hash": state["request_hash"],
        "plan_hash": plan["plan_hash"],
        "baseline_revision": state["baseline_revision"],
        "patch_sha256": state["patch_sha256"],
        "patch_paths": state["patch_paths"],
        "staged_diff_hash": staged_diff_hash,
        "file_hashes": file_hashes,
        "status": status,
        "failure": failure,
        "commands": state["command_results"],
        "authority": {
            "worktree": "isolated_detached_operational",
            "live_checkout": "unchanged",
            "curated": "unchanged",
            "immutable": "unchanged",
            "merge": "not_performed",
            "push": "not_performed",
            "promotion": "not_performed",
        },
    }
    receipt["receipt_hash"] = sha256_value(receipt)
    validate_instance("research_delta_patch_receipt", receipt, root)
    _write_new_json(_artifact_path(directory, "receipt.json"), receipt)
    return receipt


def _validate_receipt_identity(
    receipt: dict[str, Any],
    *,
    request: dict[str, Any],
    plan: dict[str, Any],
    state: dict[str, Any],
) -> None:
    expected_status = (
        "failed"
        if any(result["exit_code"] != 0 for result in state["command_results"])
        else "passed"
    )
    if (
        receipt["execution_id"] != state["execution_id"]
        or receipt["delta_id"] != request["delta_id"]
        or receipt["proposal_id"] != state["proposal_id"]
        or receipt["request_hash"] != state["request_hash"]
        or receipt["plan_hash"] != plan["plan_hash"]
        or receipt["baseline_revision"] != state["baseline_revision"]
        or receipt["patch_sha256"] != state["patch_sha256"]
        or receipt["patch_paths"] != state["patch_paths"]
        or receipt["commands"] != state["command_results"]
        or receipt["status"] != expected_status
    ):
        raise ValidationFailure("research patch receipt does not match its execution state")


def execute_research_delta_patch(
    execution_id: str, root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Apply and qualify one captured patch without integrating it."""
    directory, request, plan, proposal, state = _load_execution(execution_id, root)
    receipt_path = _artifact_path(directory, "receipt.json")
    if receipt_path.exists():
        receipt = _read_json(receipt_path, "research_delta_patch_receipt")
        _validate_hashed_record(receipt, "receipt_hash", "research_delta_patch_receipt", root)
        _validate_receipt_identity(
            receipt, request=request, plan=plan, state=state
        )
        return receipt
    if state["phase"] == "discarded":
        raise ValidationFailure("research patch worktree was discarded before qualification")
    revision = _verify_baseline(plan, root)
    if revision != state["baseline_revision"]:
        raise ValidationFailure("research patch state baseline does not match its plan")
    commands = _commands_for(proposal)
    if len(commands) != state["total_commands"]:
        raise ValidationFailure("research patch fixed command list changed after preparation")
    worktree = _ensure_worktree(root, directory, revision)
    if state["phase"] == "prepared":
        state["phase"] = "worktree_ready"
        state = _hashed_state(state)
        _replace_json(_artifact_path(directory, "state.json"), state)
    staged_diff_hash = _ensure_patch_applied(
        worktree, _artifact_path(directory, "patch.diff"), state["patch_paths"]
    )
    if state["phase"] == "failed":
        return _make_receipt(
            directory=directory,
            request=request,
            plan=plan,
            state=state,
            staged_diff_hash=staged_diff_hash,
            worktree=worktree,
            status="failed",
            failure=(
                "fixed qualification command "
                f"{state['command_results'][-1]['index']} exited "
                f"{state['command_results'][-1]['exit_code']}"
            ),
            root=root,
        )
    if state["phase"] == "passed":
        _validate_worktree_changes(worktree, state["patch_paths"])
        return _make_receipt(
            directory=directory,
            request=request,
            plan=plan,
            state=state,
            staged_diff_hash=staged_diff_hash,
            worktree=worktree,
            status="passed",
            failure=None,
            root=root,
        )
    if state["phase"] in {"worktree_ready", "prepared"}:
        state["phase"] = "patch_applied"
        state = _hashed_state(state)
        _replace_json(_artifact_path(directory, "state.json"), state)
    state["phase"] = "testing"
    state = _hashed_state(state)
    _replace_json(_artifact_path(directory, "state.json"), state)
    for index in range(state["next_command_index"], len(commands)):
        command = commands[index]
        completed = _run(command, cwd=worktree, check=False)
        result = {
            "index": index,
            "argv": command,
            "exit_code": completed.returncode,
            "stdout_hash": _write_log(directory, index, "stdout", completed.stdout),
            "stderr_hash": _write_log(directory, index, "stderr", completed.stderr),
        }
        state["command_results"].append(result)
        state["next_command_index"] = index + 1
        if completed.returncode != 0:
            state["phase"] = "failed"
            state = _hashed_state(state)
            _replace_json(_artifact_path(directory, "state.json"), state)
            return _make_receipt(
                directory=directory,
                request=request,
                plan=plan,
                state=state,
                staged_diff_hash=staged_diff_hash,
                worktree=worktree,
                status="failed",
                failure=f"fixed qualification command {index} exited {completed.returncode}",
                root=root,
            )
        state = _hashed_state(state)
        _replace_json(_artifact_path(directory, "state.json"), state)
    _validate_worktree_changes(worktree, state["patch_paths"])
    state["phase"] = "passed"
    state = _hashed_state(state)
    _replace_json(_artifact_path(directory, "state.json"), state)
    return _make_receipt(
        directory=directory,
        request=request,
        plan=plan,
        state=state,
        staged_diff_hash=staged_diff_hash,
        worktree=worktree,
        status="passed",
        failure=None,
        root=root,
    )


def inspect_research_delta_patch(
    execution_id: str, root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Rehash one patch request, state, optional receipt, and cleanup record."""
    directory, request, plan, proposal, state = _load_execution(execution_id, root)
    result: dict[str, Any] = {
        "schema": "cpcs.research_delta_patch_inspection/1.0",
        "execution_id": execution_id,
        "delta_id": request["delta_id"],
        "proposal_id": proposal["proposal_id"],
        "request_hash": sha256_value(request),
        "plan_hash": plan["plan_hash"],
        "phase": state["phase"],
        "next_command_index": state["next_command_index"],
        "total_commands": state["total_commands"],
        "receipt": None,
        "cleanup": None,
    }
    receipt_path = _artifact_path(directory, "receipt.json")
    if receipt_path.exists():
        receipt = _read_json(receipt_path, "research_delta_patch_receipt")
        _validate_hashed_record(receipt, "receipt_hash", "research_delta_patch_receipt", root)
        _validate_receipt_identity(
            receipt, request=request, plan=plan, state=state
        )
        result["receipt"] = receipt
    cleanup_path = _artifact_path(directory, "cleanup.json")
    if cleanup_path.exists():
        cleanup = _read_json(cleanup_path, "research_delta_patch_cleanup")
        _validate_hashed_record(cleanup, "cleanup_hash", "research_delta_patch_cleanup", root)
        if cleanup["execution_id"] != execution_id or state["phase"] != "discarded":
            raise ValidationFailure("research patch cleanup does not match its execution state")
        result["cleanup"] = cleanup
    return result


def discard_research_delta_patch(
    execution_id: str, root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Remove only the exact isolated worktree and preserve all operational evidence."""
    directory, _request, _plan, _proposal, state = _load_execution(execution_id, root)
    cleanup_path = _artifact_path(directory, "cleanup.json")
    if cleanup_path.exists():
        cleanup = _read_json(cleanup_path, "research_delta_patch_cleanup")
        _validate_hashed_record(cleanup, "cleanup_hash", "research_delta_patch_cleanup", root)
        return cleanup
    worktree = _worktree_path(directory)
    removed = worktree.exists()
    if removed:
        _git(root, ["worktree", "remove", "--force", str(worktree)])
    if worktree.exists():
        raise ValidationFailure("research patch worktree cleanup did not remove the exact target")
    state["phase"] = "discarded"
    state = _hashed_state(state)
    _replace_json(_artifact_path(directory, "state.json"), state)
    cleanup = {
        "schema": "cpcs.research_delta_patch_cleanup/1.0",
        "execution_id": execution_id,
        "worktree_removed": removed,
        "operational_evidence_preserved": True,
    }
    cleanup["cleanup_hash"] = sha256_value(cleanup)
    validate_instance("research_delta_patch_cleanup", cleanup, root)
    _write_new_json(cleanup_path, cleanup)
    return cleanup
