"""Capture external directing decisions; Python supplies context and checks, never taste."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any, Callable

import yaml
from jsonschema import Draft202012Validator

from .authority import authority_reader, authority_writer
from .intent import build_intent_context
from .research_session import _ensure_private_dir, _read_object, _replace, _write_new
from .validate import (
    REPO_ROOT, ValidationFailure, load_schema, read_jsonl, sha256_value, validate_instance,
)

SESSION_SCHEMA = "cpcs.directing_session/1.0"
SESSION_PATTERN = re.compile(r"directing_session_[0-9a-f]{24}")


def contract_schema(name: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    schema = load_schema("directing_session_contract", root)
    return {"$ref": "#/$defs/" + name, "$defs": schema["$defs"]}


def validate_contract(name: str, value: Any, root: Path = REPO_ROOT) -> None:
    errors = list(Draft202012Validator(contract_schema(name, root)).iter_errors(value))
    if errors:
        raise ValidationFailure("; ".join(error.message for error in errors))


def load_pass_registry(root: Path = REPO_ROOT) -> dict[str, Any]:
    registry = yaml.safe_load((root / "lab/second_brain/directing_passes.yaml").read_text())
    ontology = _read_object(root / "lab/second_brain/curated/ontology_registry.json", "ontology registry")
    if registry.get("schema") != "cpcs.directing_passes/1.0" or not registry.get("passes"):
        raise ValidationFailure("invalid directing pass registry")
    ids = [row["pass_id"] for row in registry["passes"]]
    if len(ids) != len(set(ids)):
        raise ValidationFailure("directing pass ids must be unique")
    for row in registry["passes"]:
        unknown = set(row["research_layers"]) - set(ontology["layers"])
        if unknown:
            raise ValidationFailure("unknown directing research layers: " + ", ".join(sorted(unknown)))
        if row["reads"]:
            raise ValidationFailure("scene_action has no upstream passes in this slice")
    return registry


def _directory(session_id: str, root: Path, *, create: bool = False) -> Path:
    if SESSION_PATTERN.fullmatch(session_id) is None:
        raise ValidationFailure("invalid directing session id")
    path = root / "work/application/directing_sessions" / session_id
    # Check the lexical components before the reused helper resolves the path.
    current = root.resolve()
    for part in path.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            raise ValidationFailure("directing session directory cannot be a symlink")
    if create:
        return _ensure_private_dir(path, root)
    if not path.is_dir():
        raise ValidationFailure("directing session does not exist")
    return path


def _seal(session: dict, root: Path) -> dict:
    sealed = copy.deepcopy(session)
    sealed.pop("session_hash", None)
    sealed["ledger_hash"] = sha256_value(sealed["decisions"])
    sealed["session_hash"] = sha256_value(sealed)
    validate_instance("directing_session", sealed, root)
    return sealed


def _accepted_decisions(proposal: dict, offset: int) -> list[dict]:
    return [
        {**copy.deepcopy(decision), "pass_id": proposal["pass_id"], "sequence": offset + index}
        for index, decision in enumerate(proposal["decisions"])
    ]


def _load(session_id: str, root: Path) -> tuple[Path, dict, dict]:
    directory = _directory(session_id, root)
    session = _read_object(directory / "session.json", "directing session")
    validate_instance("directing_session", session, root)
    if session["session_id"] != session_id or _seal(session, root) != session:
        raise ValidationFailure("directing session seal does not match its content")
    if session["ask"]["text_hash"] != sha256_value(session["ask"]["text"]):
        raise ValidationFailure("directing ask hash does not match")
    context = _read_object(directory / "intent_context.json", "directing intent context")
    if sha256_value(context) != session["intent_context_hash"]:
        raise ValidationFailure("directing intent context hash does not match")
    registry = load_pass_registry(root)
    if sha256_value(registry) != session["pass_registry_hash"]:
        raise ValidationFailure("directing pass registry changed since start")
    if [row["pass_id"] for row in session["passes"]] != [row["pass_id"] for row in registry["passes"]]:
        raise ValidationFailure("directing session pass plan does not match registry")
    captured = []
    for row in session["passes"]:
        if row["status"] == "accepted":
            proposal = _read_object(directory / "proposals" / (row["pass_id"] + ".json"), "directing proposal")
            validate_contract("proposal", proposal, root)
            if proposal["pass_id"] != row["pass_id"] or sha256_value(proposal) != row["proposal_hash"]:
                raise ValidationFailure("directing proposal capture does not match")
            captured.extend(_accepted_decisions(proposal, len(captured)))
        elif row["proposal_hash"] is not None:
            raise ValidationFailure("pending directing pass cannot have an accepted proposal")
    if captured != session["decisions"]:
        raise ValidationFailure("directing ledger does not match its captures")
    return directory, session, context


def _summary(session: dict, disposition: str) -> dict:
    return {
        "disposition": disposition, "session_id": session["session_id"],
        "ask": {"text": session["ask"]["text"]},
        "intent_context_hash": session["intent_context_hash"],
        "pass_plan": [row["pass_id"] for row in session["passes"]],
        "ledger_hash": session["ledger_hash"],
    }


@authority_writer("directing_session_start")
def start_session(
    text: str, *, user_constraints: list[str] | None = None,
    profile_overrides: list[str] | None = None, root: Path = REPO_ROOT,
) -> dict:
    registry = load_pass_registry(root)
    registry_hash = sha256_value(registry)
    identity = {
        "schema": SESSION_SCHEMA, "text": text,
        "user_constraints": user_constraints or [],
        "profile_overrides": profile_overrides or [],
        "pass_registry_hash": registry_hash,
    }
    session_id = "directing_session_" + sha256_value(identity)[7:31]
    directory = _directory(session_id, root, create=True)
    if (directory / "session.json").exists():
        _, session, _ = _load(session_id, root)
        return _summary(session, "already_present")
    context = build_intent_context(
        text, user_constraints=user_constraints, profile_overrides=profile_overrides, root=root
    )
    _write_new(directory / "intent_context.json", context)
    session = _seal({
        "schema": SESSION_SCHEMA, "session_id": session_id,
        "ask": {"text": text, "text_hash": sha256_value(text)},
        "intent_context_hash": sha256_value(context), "pass_registry_hash": registry_hash,
        "passes": [{"pass_id": row["pass_id"], "status": "pending", "proposal_hash": None} for row in registry["passes"]],
        "decisions": [],
    }, root)
    _write_new(directory / "session.json", session)
    return _summary(session, "created")


def _packet(session: dict, context: dict, pass_id: str, root: Path) -> dict:
    spec = next((row for row in load_pass_registry(root)["passes"] if row["pass_id"] == pass_id), None)
    if spec is None:
        raise ValidationFailure("unknown directing pass")
    text = session["ask"]["text"]
    matched = re.search(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)\b", text, re.I)
    duration = float(matched.group(1)) if matched else None
    # Context contains selected identities and traversal summaries, not definitions.
    # Resolve only those selected ids against the sole concept authority; the packet
    # binds the current complete card hash so a changed definition invalidates submit.
    cards = {row["id"]: row for row in read_jsonl(root / "lab/concepts.jsonl")}
    concepts = []
    for selected in context["context_bundle"]["selected_concepts"]:
        if selected["layer"] not in spec["research_layers"]:
            continue
        card = cards.get(selected["id"])
        if card is None:
            raise ValidationFailure("selected directing concept no longer exists")
        if card["layer"] != selected["layer"] or card["status"] != selected["status"]:
            raise ValidationFailure("selected directing concept classification changed")
        concepts.append({
            **{key: card[key] for key in ("id", "name", "what", "layer", "status")},
            "content_hash": sha256_value(card),
        })
    value = {
        "schema": "cpcs.directing_packet/1.0", "session_id": session["session_id"],
        "pass_id": pass_id, "ask": {"text": text}, "question": spec["question"],
        "sublayers": copy.deepcopy(spec["sublayers"]), "upstream": [], "locks": [],
        "constraints": {
            "requested_duration_s": duration,
            "duration_source": {"start": matched.start(), "end": matched.end(), "text": matched.group(0)} if matched else None,
        },
        "research": {
            "concepts": concepts,
            "knowledge_gaps": [layer for layer in spec["research_layers"] if not any(row["layer"] == layer for row in concepts)],
        },
        "response_contract": {
            "schema": "cpcs.directing_proposal/1.0", "identity_key": "id",
            "reference_keys": ["actor", "target", "beat", "action", "caused_by"],
            "source_status": ["user_explicit", "sourced_research", "creative_application", "inference"],
        },
        "trust_class": "bounded_directing_context",
    }
    value["packet_hash"] = sha256_value(value)
    validate_contract("packet", value, root)
    return value


@authority_reader("directing_packet_read")
def read_packet(session_id: str, pass_id: str, *, root: Path = REPO_ROOT) -> dict:
    _, session, context = _load(session_id, root)
    return _packet(session, context, pass_id, root)


@authority_reader("directing_state_read")
def read_state(session_id: str, *, root: Path = REPO_ROOT) -> dict:
    _, session, _ = _load(session_id, root)
    return {key: copy.deepcopy(session[key]) for key in ("session_id", "passes", "decisions", "ledger_hash")}


@authority_reader("directing_finish_inputs")
def finish_inputs(session_id: str, *, root: Path = REPO_ROOT) -> tuple[dict, dict]:
    _, session, context = _load(session_id, root)
    if any(row["status"] != "accepted" for row in session["passes"]):
        raise ValidationFailure("directing pass must be accepted before finish")
    return session, context


@authority_writer("directing_proposal_submit")
def submit_proposal(
    session_id: str, pass_id: str, packet_hash: str, proposal: dict,
    *, value_check: Callable, root: Path = REPO_ROOT,
) -> dict:
    directory, session, context = _load(session_id, root)
    proposal_hash = sha256_value(proposal)
    errors: list[dict] = []

    def reject(code: str, index: int | None, path: str, message: str) -> None:
        errors.append({"code": code, "decision_index": index, "path": path, "message": message})

    def result(disposition: str, state: dict) -> dict:
        value = {
            "disposition": disposition, "proposal_hash": proposal_hash,
            "decision_ids": [] if errors else [d["decision_id"] for d in proposal["decisions"]],
            "rejections": errors, "ledger_hash": state["ledger_hash"],
        }
        validate_contract("submit_result", value, root)
        return value

    schema_errors = list(Draft202012Validator(contract_schema("proposal", root)).iter_errors(proposal))
    if schema_errors:
        for error in schema_errors:
            reject("schema_invalid", None, "/".join(map(str, error.absolute_path)) or "proposal", error.message)
        return result("rejected", session)
    packet = _packet(session, context, pass_id, root)
    if proposal["pass_id"] != pass_id:
        reject("schema_invalid", None, "pass_id", "Proposal pass must match the requested pass.")
    if packet_hash != packet["packet_hash"]:
        reject("stale_packet", None, "packet_hash", "Packet hash does not match the current pass view.")
    if errors:
        return result("rejected", session)
    pass_state = next(row for row in session["passes"] if row["pass_id"] == pass_id)
    if pass_state["status"] == "accepted":
        if pass_state["proposal_hash"] == proposal_hash:
            return result("already_present", session)
        reject("pass_already_accepted", None, "pass_id", "A different proposal cannot replace this accepted pass.")
        return result("rejected", session)
    spec = next(row for row in load_pass_registry(root)["passes"] if row["pass_id"] == pass_id)
    for slot in spec["sublayers"]:
        if slot["required"] and not any(d["sublayer"] == slot["sublayer_id"] for d in proposal["decisions"]):
            reject("missing_required_sublayer", None, slot["sublayer_id"], "Required sublayers need a decision and cannot be not_applicable.")
    slots = {s["sublayer_id"]: s for s in spec["sublayers"]}
    for absent in proposal["not_applicable"]:
        slot = slots.get(absent["sublayer_id"])
        if slot is None or slot["required"]:
            reject("missing_required_sublayer", None, absent["sublayer_id"], "Only a declared optional sublayer may be not_applicable.")
    earlier = {d["decision_id"] for d in packet["upstream"]}
    concepts = {(row["id"], row["content_hash"]) for row in packet["research"]["concepts"]}
    text = session["ask"]["text"]
    for index, decision in enumerate(proposal["decisions"]):
        if decision["decision_id"] in earlier:
            reject("duplicate_decision_id", index, "decision_id", "Decision ids must be unique.")
        if not set(decision["inputs"]) <= earlier:
            reject("unknown_input", index, "inputs", "Inputs must name earlier decisions or packet upstream.")
        earlier.add(decision["decision_id"])
        spans = [u for u in decision["evidence_uses"] if u["kind"] == "ask_span"]
        valid_spans = [u for u in spans if 0 <= u["start"] < u["end"] <= len(text) and text[u["start"]:u["end"]] == u["text"]]
        cited = [u for u in decision["evidence_uses"] if u["kind"] == "concept"]
        status = decision["source_status"]
        if status == "user_explicit" and not valid_spans:
            reject("user_explicit_without_span", index, "evidence_uses", "User-explicit choices need a verbatim ask span.")
        if len(valid_spans) != len(spans) and status != "user_explicit":
            reject("evidence_outside_packet", index, "evidence_uses", "An ask span must match the exact ask.")
        if any((u["id"], u["content_hash"]) not in concepts for u in cited) or (status == "sourced_research" and not cited):
            reject("evidence_outside_packet", index, "evidence_uses", "Research must cite exact concept ids and hashes in this packet.")
        if status == "model_tested":
            reject("model_tested_not_admissible", index, "source_status", "This slice admits no model-tested claims.")
        if decision["lock"] and status != "user_explicit":
            reject("lock_requires_user_explicit", index, "lock", "Only a user-explicit decision may be locked.")
        if decision["layer"] != pass_id:
            reject("path_not_allowed", index, "layer", "The decision belongs to the requested pass.")
    errors.extend(value_check(session["decisions"] + proposal["decisions"], spec, packet))
    if errors:
        return result("rejected", session)
    captures = _ensure_private_dir(directory / "proposals", root)
    _write_new(captures / (pass_id + ".json"), proposal)
    session["decisions"].extend(_accepted_decisions(proposal, len(session["decisions"])))
    pass_state.update(status="accepted", proposal_hash=proposal_hash)
    session = _seal(session, root)
    _replace(directory / "session.json", session)
    return result("accepted", session)
