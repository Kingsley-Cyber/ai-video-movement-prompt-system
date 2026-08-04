"""Resumable, content-bound research extraction over existing CPCS owners."""

from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .authority import authority_reader, authority_writer
from .curate import prepare_distillation_review
from .distill import (
    POLICY,
    POLICY_HASH,
    run_distillation,
    validate_distillation_batch,
)
from .source_extract import (
    extract_folder,
    extract_retrieved_passages,
    validate_source_bundle,
)
from .validate import (
    REPO_ROOT,
    ValidationFailure,
    canonical_json_bytes,
    sha256_value,
    validate_instance,
)

SESSION_SCHEMA = "cpcs.research_extraction_session/1.0"
SESSION_ID_PATTERN = re.compile(r"research_session_[0-9a-f]{24}")
PACKET_ID_PATTERN = re.compile(r"packet_[0-9a-f]{24}")
MAX_SESSION_FILE_BYTES = 64 * 1024 * 1024


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _ensure_private_dir(path: Path, root: Path) -> Path:
    resolved_root = root.resolve()
    current = resolved_root
    for part in path.resolve().relative_to(resolved_root).parts:
        current = current / part
        if current.is_symlink():
            raise ValidationFailure(
                f"research session directory cannot be a symlink: {current}"
            )
        current.mkdir(mode=0o700, exist_ok=True)
    os.chmod(current, 0o700)
    return path.resolve()


def _sessions_root(root: Path, *, create: bool) -> Path:
    path = root / "work" / "application" / "research_sessions"
    if create:
        return _ensure_private_dir(path, root)
    if path.is_symlink():
        raise ValidationFailure("research session root cannot be a symlink")
    if not path.is_dir():
        raise ValidationFailure("research session root does not exist")
    resolved = path.resolve()
    if root.resolve() not in resolved.parents:
        raise ValidationFailure("research session root escaped the repository")
    return resolved


def _session_dir(session_id: str, root: Path, *, create: bool = False) -> Path:
    if SESSION_ID_PATTERN.fullmatch(session_id) is None:
        raise ValidationFailure("research session ID is invalid")
    base = _sessions_root(root, create=create)
    path = base / session_id
    if path.is_symlink():
        raise ValidationFailure("research session path cannot be a symlink")
    if create:
        path.mkdir(mode=0o700, exist_ok=True)
        os.chmod(path, 0o700)
    if base not in path.resolve().parents:
        raise ValidationFailure("research session path escaped its operational root")
    return path


def _read_object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink():
        raise ValidationFailure(f"{label} cannot be a symlink")
    try:
        if path.stat().st_size > MAX_SESSION_FILE_BYTES:
            raise ValidationFailure(f"{label} exceeds the session file limit")
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationFailure(f"cannot read {label}: {error}") from error
    if not isinstance(value, dict):
        raise ValidationFailure(f"{label} must be a JSON object")
    return value


def _read_bundle(path: Path, label: str, root: Path) -> dict[str, Any]:
    bundle = _read_object(path, label)
    validate_source_bundle(bundle, root)
    return bundle


def _validated_contract(value: dict[str, Any], root: Path) -> dict[str, Any]:
    validate_instance("research_session_contract", value, root)
    return value


def _write_new(path: Path, value: dict[str, Any]) -> None:
    payload = canonical_json_bytes(value)
    if path.exists():
        if path.is_symlink() or path.read_bytes() != payload:
            raise ValidationFailure(f"operational artifact collision: {path.name}")
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
    _fsync_directory(path.parent)


def _replace(path: Path, value: dict[str, Any]) -> None:
    if path.is_symlink():
        raise ValidationFailure(f"operational artifact cannot be a symlink: {path.name}")
    payload = canonical_json_bytes(value)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


def _sealed_session(value: dict[str, Any], root: Path) -> dict[str, Any]:
    session = copy.deepcopy(value)
    session.pop("session_hash", None)
    session["session_hash"] = sha256_value(session)
    validate_instance("research_extraction_session", session, root)
    packet_ids = [row["packet_id"] for row in session["packet_states"]]
    if packet_ids != sorted(packet_ids) or len(packet_ids) != len(set(packet_ids)):
        raise ValidationFailure("research session packet states must be unique and sorted")
    return session


def _load_session(session_id: str, root: Path) -> tuple[Path, dict[str, Any]]:
    directory = _session_dir(session_id, root)
    session = _read_object(directory / "session.json", "research session")
    validate_instance("research_extraction_session", session, root)
    expected = _sealed_session(session, root)["session_hash"]
    if session["session_hash"] != expected:
        raise ValidationFailure("research session hash does not match its content")
    _validate_session_captures(directory, session, root)
    return directory, session


def _write_session(directory: Path, session: dict[str, Any], root: Path) -> dict[str, Any]:
    sealed = _sealed_session(session, root)
    _replace(directory / "session.json", sealed)
    return sealed


def _source_bundle(
    registration: dict[str, Any],
    root: Path,
    semantic_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if registration["source_kind"] == "authorized_folder":
        return extract_folder(
            Path(registration["folder"]),
            research_goal=registration["research_goal"],
            rights_basis=registration["rights_basis"],
            semantic_response=semantic_response,
            configuration=registration.get("configuration"),
            root=root,
        )
    return extract_retrieved_passages(
        copy.deepcopy(registration["retrieved_passages"]),
        semantic_response=semantic_response,
        configuration=registration.get("configuration"),
        root=root,
    )


def _research_goal(registration: dict[str, Any]) -> str:
    if registration["source_kind"] == "authorized_folder":
        return registration["research_goal"]
    return registration["retrieved_passages"]["retrieval"]["query"]


def _validate_registration(arguments: dict[str, Any], root: Path) -> None:
    extractor = arguments["extractor"]
    validate_instance(
        "semantic_extraction_response",
        {
            "schema": "cpcs.semantic_extraction_response/1.0",
            "extractor": extractor,
            "packet_results": [],
        },
        root,
    )
    kind = arguments["source_kind"]
    if kind == "authorized_folder":
        required = {"folder", "research_goal", "rights_basis"}
        if not required <= set(arguments) or "retrieved_passages" in arguments:
            raise ValidationFailure(
                "authorized_folder requires folder, research_goal, and rights_basis"
            )
    elif kind == "polymath_passages":
        if "retrieved_passages" not in arguments or any(
            key in arguments for key in ("folder", "research_goal", "rights_basis")
        ):
            raise ValidationFailure(
                "polymath_passages requires retrieved_passages and no folder fields"
            )
    else:
        raise ValidationFailure(f"unsupported source kind: {kind}")


def _session_status_value(
    session: dict[str, Any], root: Path
) -> dict[str, Any]:
    submitted = sum(
        row["status"] == "submitted" for row in session["packet_states"]
    )
    return _validated_contract({
        "schema": "cpcs.research_extraction_status/1.0",
        "session_id": session["session_id"],
        "session_hash": session["session_hash"],
        "state": session["state"],
        "source_bundle_id": session["source_bundle_id"],
        "source_bundle_hash": session["source_bundle_hash"],
        "packets": {
            "total": len(session["packet_states"]),
            "submitted": submitted,
            "pending": len(session["packet_states"]) - submitted,
        },
        "captured_response_hash": session["captured_response_hash"],
        "completed_bundle_id": session["completed_bundle_id"],
        "completed_bundle_hash": session["completed_bundle_hash"],
        "distillation_run_id": session["distillation_run_id"],
        "authority": {
            "source_and_llm_output": "captured_untrusted_evidence",
            "proposals": "untrusted_extraction_proposals",
            "curated": "unchanged_without_explicit_cpcs.curate.promote",
        },
    }, root)


def _validate_timestamp(value: str, label: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValidationFailure(f"{label} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValidationFailure(f"{label} must include a timezone")


@authority_writer("research_session_register")
def register_source(
    arguments: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    registration = copy.deepcopy(arguments)
    _validate_timestamp(registration["registered_at"], "registered_at")
    _validate_registration(registration, root)
    initial = _source_bundle(registration, root)
    contracts = {
        "source_bundle_schema": initial["schema"],
        "semantic_response_schema": "cpcs.semantic_extraction_response/1.0",
        "distillation_batch_schema": "cpcs.distillation_batch/1.0",
        "distillation_policy_version": POLICY["version"],
        "distillation_policy_hash": POLICY_HASH,
    }
    identity = {
        "source_bundle_hash": initial["bundle_hash"],
        "extractor": registration["extractor"],
        "contracts": contracts,
        "registered_at": registration["registered_at"],
    }
    session_id = "research_session_" + sha256_value(identity)[7:31]
    directory = _session_dir(session_id, root, create=True)
    source_request_hash = sha256_value(registration)
    packet_states = [
        {
            "packet_id": row["packet_id"],
            "status": "pending",
            "response_hash": None,
            "submitted_at": None,
        }
        for row in sorted(initial["semantic_packets"], key=lambda row: row["packet_id"])
    ]
    has_packets = bool(packet_states)
    session = _sealed_session(
        {
            "schema": SESSION_SCHEMA,
            "session_id": session_id,
            "state": "packets_ready" if has_packets else "proposals_ready",
            "registered_at": registration["registered_at"],
            "source_kind": registration["source_kind"],
            "research_goal": _research_goal(registration),
            "source_request_hash": source_request_hash,
            "source_bundle_id": initial["bundle_id"],
            "source_bundle_hash": initial["bundle_hash"],
            "extractor": registration["extractor"],
            "contracts": contracts,
            "packet_states": packet_states,
            "captured_response_hash": None,
            "completed_bundle_id": None if has_packets else initial["bundle_id"],
            "completed_bundle_hash": None if has_packets else initial["bundle_hash"],
            "distillation_run_id": None,
        },
        root,
    )
    _write_new(directory / "registration.json", registration)
    _write_new(directory / "initial_bundle.json", initial)
    if not has_packets:
        _write_new(directory / "completed_bundle.json", initial)
    session_path = directory / "session.json"
    if session_path.exists():
        _, existing = _load_session(session_id, root)
        static_fields = (
            "registered_at",
            "source_kind",
            "research_goal",
            "source_request_hash",
            "source_bundle_id",
            "source_bundle_hash",
            "extractor",
            "contracts",
        )
        if any(existing[field] != session[field] for field in static_fields):
            raise ValidationFailure("research session identity collision")
        return _session_status_value(existing, root)
    else:
        _write_new(session_path, session)
    return _session_status_value(session, root)


@authority_reader("research_session_status")
def session_status(session_id: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    _, session = _load_session(session_id, root)
    return _session_status_value(session, root)


@authority_reader("research_source_inspect")
def inspect_source(session_id: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    directory, session = _load_session(session_id, root)
    bundle = _read_bundle(
        directory / "initial_bundle.json", "initial source bundle", root
    )
    return _validated_contract({
        "schema": "cpcs.research_source_inspection/1.0",
        "session_id": session_id,
        "source_kind": session["source_kind"],
        "research_goal": session["research_goal"],
        "bundle_id": bundle["bundle_id"],
        "bundle_hash": bundle["bundle_hash"],
        "inventory": bundle["inventory"],
        "orientation": bundle["orientation"],
        "source_ledger": bundle["source_ledger"],
        "trust_class": "registered_source_evidence_not_curated_truth",
    }, root)


@authority_reader("research_packet_list")
def list_packets(session_id: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    directory, session = _load_session(session_id, root)
    bundle = _read_bundle(
        directory / "initial_bundle.json", "initial source bundle", root
    )
    states = {row["packet_id"]: row for row in session["packet_states"]}
    packets = [
        {
            "packet_id": packet["packet_id"],
            "passage_count": len(packet["passages"]),
            "passage_chars": packet["passage_chars"],
            "source_ids": sorted({row["source_id"] for row in packet["passages"]}),
            "status": states[packet["packet_id"]]["status"],
            "response_hash": states[packet["packet_id"]]["response_hash"],
        }
        for packet in sorted(bundle["semantic_packets"], key=lambda row: row["packet_id"])
    ]
    return _validated_contract({
        "schema": "cpcs.research_packet_list/1.0",
        "session_id": session_id,
        "packets": packets,
    }, root)


@authority_reader("research_packet_read")
def read_packet(
    session_id: str, packet_id: str, root: Path = REPO_ROOT
) -> dict[str, Any]:
    if PACKET_ID_PATTERN.fullmatch(packet_id) is None:
        raise ValidationFailure("semantic packet ID is invalid")
    directory, session = _load_session(session_id, root)
    bundle = _read_bundle(
        directory / "initial_bundle.json", "initial source bundle", root
    )
    matches = [
        row for row in bundle["semantic_packets"] if row["packet_id"] == packet_id
    ]
    if len(matches) != 1:
        raise ValidationFailure(
            f"expected one semantic packet {packet_id}, found {len(matches)}"
        )
    return _validated_contract({
        "schema": "cpcs.research_packet/1.0",
        "session_id": session_id,
        "extractor": session["extractor"],
        "response_contract": session["contracts"]["semantic_response_schema"],
        "packet": matches[0],
        "trust_class": "bounded_source_evidence",
    }, root)


def _packet_result_path(directory: Path, packet_id: str) -> Path:
    if PACKET_ID_PATTERN.fullmatch(packet_id) is None:
        raise ValidationFailure("semantic packet ID is invalid")
    results = directory / "packet_results"
    if results.is_symlink():
        raise ValidationFailure("packet result directory cannot be a symlink")
    results.mkdir(mode=0o700, exist_ok=True)
    os.chmod(results, 0o700)
    return results / f"{packet_id}.json"


def _validate_packet_result_record(
    record: dict[str, Any],
    session: dict[str, Any],
    packet_id: str,
    root: Path,
    *,
    require_state_match: bool,
) -> dict[str, Any]:
    _validated_contract(record, root)
    if record["session_id"] != session["session_id"]:
        raise ValidationFailure("packet result belongs to a different research session")
    if record["packet_id"] != packet_id:
        raise ValidationFailure("packet result filename and packet ID do not match")
    if record["packet_result"]["packet_id"] != packet_id:
        raise ValidationFailure("captured semantic response has a different packet ID")
    _validate_timestamp(record["submitted_at"], "captured submitted_at")
    expected_hash = sha256_value(record["packet_result"])
    if record["response_hash"] != expected_hash:
        raise ValidationFailure("packet result response hash does not match its content")
    validate_instance(
        "semantic_extraction_response",
        {
            "schema": "cpcs.semantic_extraction_response/1.0",
            "extractor": session["extractor"],
            "packet_results": [record["packet_result"]],
        },
        root,
    )
    states = [
        row for row in session["packet_states"] if row["packet_id"] == packet_id
    ]
    if len(states) != 1:
        raise ValidationFailure("packet result has no unique session state")
    state = states[0]
    if require_state_match and (
        state["status"] != "submitted"
        or state["response_hash"] != record["response_hash"]
        or state["submitted_at"] != record["submitted_at"]
    ):
        raise ValidationFailure("packet result does not match its sealed session state")
    return record


def _read_packet_result(
    directory: Path,
    session: dict[str, Any],
    packet_id: str,
    root: Path,
    *,
    require_state_match: bool,
) -> dict[str, Any]:
    record = _read_object(
        _packet_result_path(directory, packet_id), f"packet result {packet_id}"
    )
    return _validate_packet_result_record(
        record,
        session,
        packet_id,
        root,
        require_state_match=require_state_match,
    )


def _submitted_results(
    directory: Path, session: dict[str, Any], root: Path
) -> list[dict[str, Any]]:
    rows = []
    for state in session["packet_states"]:
        packet_id = state["packet_id"]
        path = _packet_result_path(directory, packet_id)
        if path.exists():
            rows.append(
                _read_packet_result(
                    directory,
                    session,
                    packet_id,
                    root,
                    require_state_match=state["status"] == "submitted",
                )
            )
        elif state["status"] == "submitted":
            raise ValidationFailure(f"captured packet result is missing: {packet_id}")
    return rows


def _validate_session_captures(
    directory: Path, session: dict[str, Any], root: Path
) -> None:
    for state in session["packet_states"]:
        if state["status"] == "submitted":
            _read_packet_result(
                directory,
                session,
                state["packet_id"],
                root,
                require_state_match=True,
            )
    captured_hash = session["captured_response_hash"]
    if captured_hash is None:
        return
    semantic_response = _read_object(
        directory / "semantic_response.json", "captured semantic response"
    )
    validate_instance("semantic_extraction_response", semantic_response, root)
    if sha256_value(semantic_response) != captured_hash:
        raise ValidationFailure(
            "captured semantic response hash does not match its content"
        )
    results = _submitted_results(directory, session, root)
    expected = {
        "schema": "cpcs.semantic_extraction_response/1.0",
        "extractor": session["extractor"],
        "packet_results": [row["packet_result"] for row in results],
    }
    if semantic_response != expected:
        raise ValidationFailure(
            "captured semantic response does not match packet-result captures"
        )


@authority_writer("research_extraction_submit")
def submit_extraction(
    session_id: str,
    packet_result: dict[str, Any],
    submitted_at: str,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    _validate_timestamp(submitted_at, "submitted_at")
    directory, session = _load_session(session_id, root)
    registration = _read_object(directory / "registration.json", "source registration")
    initial = _read_bundle(
        directory / "initial_bundle.json", "initial source bundle", root
    )
    current = _source_bundle(registration, root)
    if current["bundle_hash"] != initial["bundle_hash"]:
        raise ValidationFailure(
            "registered source bytes or extraction context changed; register a new session"
        )
    response = {
        "schema": "cpcs.semantic_extraction_response/1.0",
        "extractor": session["extractor"],
        "packet_results": [copy.deepcopy(packet_result)],
    }
    validate_instance("semantic_extraction_response", response, root)
    packet_id = packet_result["packet_id"]
    known = {row["packet_id"] for row in session["packet_states"]}
    if packet_id not in known:
        raise ValidationFailure(f"semantic response references unknown packet: {packet_id}")
    _source_bundle(registration, root, response)
    response_hash = sha256_value(packet_result)
    record = {
        "schema": "cpcs.research_packet_result/1.0",
        "session_id": session_id,
        "packet_id": packet_id,
        "submitted_at": submitted_at,
        "response_hash": response_hash,
        "packet_result": copy.deepcopy(packet_result),
    }
    _validate_packet_result_record(
        record,
        session,
        packet_id,
        root,
        require_state_match=False,
    )
    result_path = _packet_result_path(directory, packet_id)
    if result_path.exists():
        existing = _read_packet_result(
            directory,
            session,
            packet_id,
            root,
            require_state_match=False,
        )
        if existing["response_hash"] != response_hash:
            raise ValidationFailure(
                f"packet {packet_id} already has a different captured response"
            )
        if existing["submitted_at"] != submitted_at:
            raise ValidationFailure(
                f"packet {packet_id} already has a different submission timestamp"
            )
    else:
        _write_new(result_path, record)

    for state in session["packet_states"]:
        if state["packet_id"] == packet_id and state["status"] == "pending":
            state.update(
                {
                    "status": "submitted",
                    "response_hash": response_hash,
                    "submitted_at": submitted_at,
                }
            )
    results = _submitted_results(directory, session, root)
    if len(results) == len(session["packet_states"]):
        semantic_response = {
            "schema": "cpcs.semantic_extraction_response/1.0",
            "extractor": session["extractor"],
            "packet_results": [row["packet_result"] for row in results],
        }
        completed = _source_bundle(registration, root, semantic_response)
        _write_new(directory / "semantic_response.json", semantic_response)
        _write_new(directory / "completed_bundle.json", completed)
        session.update(
            {
                "state": "proposals_ready",
                "captured_response_hash": sha256_value(semantic_response),
                "completed_bundle_id": completed["bundle_id"],
                "completed_bundle_hash": completed["bundle_hash"],
            }
        )
    else:
        session["state"] = "extracting"
    session = _write_session(directory, session, root)
    return _session_status_value(session, root)


def _completed_bundle(
    session_id: str, root: Path
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    directory, session = _load_session(session_id, root)
    if session["state"] not in {"proposals_ready", "distilled"}:
        raise ValidationFailure("research extraction proposals are not ready")
    bundle = _read_bundle(
        directory / "completed_bundle.json", "completed source bundle", root
    )
    if (
        bundle["bundle_id"] != session["completed_bundle_id"]
        or bundle["bundle_hash"] != session["completed_bundle_hash"]
    ):
        raise ValidationFailure("completed source bundle does not match the session")
    return directory, session, bundle


@authority_reader("research_coverage_inspect")
def inspect_coverage(session_id: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    directory, session = _load_session(session_id, root)
    name = (
        "completed_bundle.json"
        if session["completed_bundle_hash"] is not None
        else "initial_bundle.json"
    )
    bundle = _read_bundle(directory / name, "source extraction bundle", root)
    return _validated_contract({
        "schema": "cpcs.research_coverage/1.0",
        "session_id": session_id,
        "state": session["state"],
        "bundle_id": bundle["bundle_id"],
        "bundle_hash": bundle["bundle_hash"],
        "coverage": bundle["coverage"],
    }, root)


@authority_reader("research_proposals_list")
def list_proposals(session_id: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    _, _, bundle = _completed_bundle(session_id, root)
    batch = bundle["distillation_batch"]
    return _validated_contract({
        "schema": "cpcs.research_proposal_list/1.0",
        "session_id": session_id,
        "batch_id": batch["batch_id"],
        "batch_hash": sha256_value(batch),
        "proposals": copy.deepcopy(batch["candidates"]),
        "trust_class": "untrusted_extraction_proposals",
        "authority_effect": "none",
    }, root)


@authority_reader("research_proposals_validate")
def validate_proposals(session_id: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    _, _, bundle = _completed_bundle(session_id, root)
    validation = validate_distillation_batch(bundle["distillation_batch"], root)
    result = {**validation, "session_id": session_id}
    validate_instance("distillation_batch_validation", result, root)
    return result


@authority_writer("research_distillation_run")
def distill_session(session_id: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    directory, session, bundle = _completed_bundle(session_id, root)
    validate_distillation_batch(bundle["distillation_batch"], root)
    run = run_distillation(copy.deepcopy(bundle["distillation_batch"]), root)
    if session["distillation_run_id"] not in {None, run["id"]}:
        raise ValidationFailure("research session resolved to a different distillation run")
    session["state"] = "distilled"
    session["distillation_run_id"] = run["id"]
    _write_new(directory / "distillation_run.json", run)
    _write_session(directory, session, root)
    return _validated_contract({
        "schema": "cpcs.research_distillation/1.0",
        "session_id": session_id,
        "run": run,
        "authority_effect": "staging_only",
    }, root)


@authority_reader("research_promotion_prepare")
def prepare_promotion(session_id: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    _, session = _load_session(session_id, root)
    if session["distillation_run_id"] is None:
        raise ValidationFailure("research session has no staged distillation run")
    review = prepare_distillation_review(session["distillation_run_id"], root)
    return _validated_contract({
        "schema": "cpcs.research_promotion_preparation/1.0",
        "session_id": session_id,
        "review": review,
        "next_operation": "cpcs.curate.promote",
        "authority_effect": "none",
    }, root)
