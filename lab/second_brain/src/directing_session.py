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
from .context import build_context_bundle
from .source_registry import resolve_sources
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
        if not set(row["reads"]) <= set(ids[:ids.index(row["pass_id"])]):
            raise ValidationFailure("directing reads must name earlier registered passes")
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
    expected = registry["passes"] if session.get("options", {}).get("mode") == "complete" else registry["passes"][:1]
    if [row["pass_id"] for row in session["passes"]] != [row["pass_id"] for row in expected]:
        raise ValidationFailure("directing session pass plan does not match registry")
    captured = []
    last_capture = {}
    for row in session.get("captures", session["passes"]):
        if "captures" in session:
            proposal = _read_object(directory / "proposals" / (row["proposal_hash"][7:] + ".json"), "directing proposal")
            validate_contract("proposal", proposal, root)
            if proposal["pass_id"] != row["pass_id"] or sha256_value(proposal) != row["proposal_hash"]:
                raise ValidationFailure("directing proposal capture does not match")
            existing = {d["decision_id"]: d for d in captured}
            for d in proposal["decisions"]:
                if d["decision_id"] in existing:
                    if {k: v for k, v in existing[d["decision_id"]].items() if k not in ("pass_id", "sequence")} != d:
                        raise ValidationFailure("captured decision id changed without a revision")
                else:
                    captured.extend(_accepted_decisions({**proposal, "decisions": [d]}, len(captured)))
            last_capture[row["pass_id"]] = row["proposal_hash"]
            continue
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
    if "captures" in session:
        for row in session["passes"]:
            if row["proposal_hash"] != last_capture.get(row["pass_id"]) or (row["status"] == "accepted" and row["pass_id"] not in last_capture):
                raise ValidationFailure("directing pass state does not match captured proposals")
    return directory, session, context


def active_decisions(session: dict) -> list[dict]:
    """Project the immutable ledger's latest choice per decision, omitting stale passes."""
    superseded = {d["revision_of"] for d in session["decisions"] if d["revision_of"]}
    accepted = {p["pass_id"] for p in session["passes"] if p["status"] == "accepted"}
    return [copy.deepcopy(d) for d in session["decisions"]
            if d["decision_id"] not in superseded and d["pass_id"] in accepted]


NEED_SUBLAYERS = {"performance": "body", "camera": "framing"}


def action_needs(decisions: list[dict], not_applicable: dict[str, list[dict]] | None = None) -> list[dict]:
    """Opt-in action-scoped needs derived only from accepted authored actions.

    Each action needs a camera span covering its beat; an action whose actor is not a declared
    object also needs its body pathway. A body need resolves through a performance body choice
    targeted at the action that cites the action's current decision, so revising the action
    reopens it. A targeted not_applicable with a reason, from the pass's own proposal, also
    resolves a need. Nothing here adds needs that the accepted scene did not author.
    """
    state: dict[str, dict[str, dict]] = {}
    owners: dict[tuple[str, str], list[str]] = {}
    for d in decisions:
        target = d["target"]
        state.setdefault(target["path"], {}).setdefault(target["item_id"], {}).update(d["values"])
        if d["layer"] == "scene_action":
            owners.setdefault((target["path"], target["item_id"]), []).append(d["decision_id"])
    entities, beats = state.get("entities", {}), state.get("beats", {})
    beat_order = {item_id: item.get("order") for item_id, item in beats.items()}
    spans = []
    for shot in state.get("shots", {}).values():
        start, end = beat_order.get(shot.get("beat")), beat_order.get(shot.get("end_beat", shot.get("beat")))
        if isinstance(start, int) and isinstance(end, int):
            spans.append((start, end))
    skipped = {(n["sublayer_id"], n["target"]["item_id"]) for rows in (not_applicable or {}).values()
               for n in rows if "target" in n}
    actions = sorted(state.get("actions", {}).items(), key=lambda pair: (pair[1].get("order", 0), pair[0]))
    needs = []
    for pass_id, sublayer in NEED_SUBLAYERS.items():
        for action_id, action in actions:
            depends_on = sorted(owners.get(("actions", action_id), []))
            if pass_id == "performance":
                actor = entities.get(action.get("actor"))
                if actor is None or actor.get("kind") == "object":
                    continue
                resolved = any(
                    d["layer"] == "performance" and d["sublayer"] == "body"
                    and d["target"] == {"path": "actions", "item_id": action_id}
                    and set(d["inputs"]) & set(depends_on)
                    for d in decisions
                )
            else:
                order = beat_order.get(action.get("beat"))
                resolved = isinstance(order, int) and any(start <= order <= end for start, end in spans)
            status = "resolved" if resolved else "not_applicable" if (sublayer, action_id) in skipped else "open"
            needs.append({
                "need_id": f"need_{'body' if pass_id == 'performance' else 'camera'}_{action_id}",
                "pass_id": pass_id, "sublayer_id": sublayer,
                "target": {"path": "actions", "item_id": action_id},
                "depends_on": depends_on, "status": status,
            })
    return needs


def _latest_not_applicable(session: dict, directory: Path, root: Path) -> dict[str, list[dict]]:
    latest = {}
    for row in session.get("captures", []):
        latest[row["pass_id"]] = row["proposal_hash"]
    rows = {}
    for pass_id, digest in latest.items():
        if pass_id in NEED_SUBLAYERS:
            proposal = _read_object(directory / "proposals" / (digest[7:] + ".json"), "directing proposal")
            rows[pass_id] = [n for n in proposal["not_applicable"] if "target" in n]
    return rows


def _coverage_enabled(session: dict) -> bool:
    return session.get("options", {}).get("preferences", {}).get("action_coverage") is True


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
    profile_overrides: list[str] | None = None, mode: str = "scene_action",
    model: str = "veo-3.1-generate-001", variant: str = "",
    preferences: dict | None = None, root: Path = REPO_ROOT,
) -> dict:
    if mode not in ("scene_action", "complete"):
        raise ValidationFailure("unknown directing mode")
    registry = load_pass_registry(root)
    registry_hash = sha256_value(registry)
    identity = {
        "schema": SESSION_SCHEMA, "text": text,
        "user_constraints": user_constraints or [],
        "profile_overrides": profile_overrides or [],
        "pass_registry_hash": registry_hash,
    }
    options = {"mode": mode, "model": model, "variant": variant, "preferences": preferences or {}}
    if mode == "complete":
        identity["options"] = options
    elif model != "veo-3.1-generate-001":
        identity["target_model"] = model
    session_id = "directing_session_" + sha256_value(identity)[7:31]
    directory = _directory(session_id, root, create=True)
    if (directory / "session.json").exists():
        _, session, _ = _load(session_id, root)
        return _summary(session, "already_present")
    context = build_intent_context(
        text, user_constraints=user_constraints, profile_overrides=profile_overrides, root=root
    )
    _write_new(directory / "intent_context.json", context)
    session = {
        "schema": SESSION_SCHEMA, "session_id": session_id,
        "ask": {"text": text, "text_hash": sha256_value(text)},
        "intent_context_hash": sha256_value(context), "pass_registry_hash": registry_hash,
        "passes": [{"pass_id": row["pass_id"], "status": "pending", "proposal_hash": None} for row in (registry["passes"] if mode == "complete" else registry["passes"][:1])],
        "decisions": [],
    }
    if mode == "complete":
        session.update(options=options, captures=[])
    elif "target_model" in identity:
        session["target_model"] = model
    session = _seal(session, root)
    _write_new(directory / "session.json", session)
    return _summary(session, "created")


def _packet(session: dict, context: dict, pass_id: str, root: Path) -> dict:
    spec = next((row for row in load_pass_registry(root)["passes"] if row["pass_id"] == pass_id), None)
    if spec is None:
        raise ValidationFailure("unknown directing pass")
    if pass_id not in {p["pass_id"] for p in session["passes"]}:
        raise ValidationFailure("pass is not in this session plan")
    text = session["ask"]["text"]
    reads = set(spec["reads"])
    for row in reversed(load_pass_registry(root)["passes"]):
        if row["pass_id"] in reads:
            reads.update(row["reads"])
    matched = re.search(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)\b", text, re.I)
    duration = float(matched.group(1)) if matched else None
    # Context contains selected identities and traversal summaries, not definitions.
    # Resolve only those selected ids against the sole concept authority; the packet
    # binds the current complete card hash so a changed definition invalidates submit.
    cards = {row["id"]: row for row in read_jsonl(root / "lab/concepts.jsonl")}
    concepts = []
    complete = "options" in session
    selected_context = context["context_bundle"]
    if complete:
        ontology = _read_object(root / "lab/second_brain/curated/ontology_registry.json", "ontology")
        selected_context = build_context_bundle(
            text + " " + spec["question"], token_budget=context["context_bundle"]["request"]["token_budget"],
            required_layers=spec["research_layers"],
            excluded_layers=sorted(set(ontology["layers"]) - set(spec["research_layers"])), root=root,
        )
    for selected in selected_context["selected_concepts"]:
        if selected["layer"] not in spec["research_layers"]:
            continue
        card = cards.get(selected["id"])
        if card is None:
            raise ValidationFailure("selected directing concept no longer exists")
        if card["layer"] != selected["layer"] or card["status"] != selected["status"]:
            raise ValidationFailure("selected directing concept classification changed")
        concept = {
            **{key: card[key] for key in ("id", "name", "what", "layer", "status")},
            "content_hash": sha256_value(card),
        }
        if complete:
            concept["source_refs"] = card.get("source_refs", [])
            concept["source_resolution"] = resolve_sources(concept_ids=[card["id"]], root=root)
        concepts.append(concept)
    value = {
        "schema": "cpcs.directing_packet/1.0", "session_id": session["session_id"],
        "pass_id": pass_id, "ask": {"text": text}, "question": spec["question"],
        "sublayers": copy.deepcopy(spec["sublayers"]),
        "upstream": [d for d in active_decisions(session) if d["pass_id"] in reads],
        "locks": [d["decision_id"] for d in active_decisions(session) if d["lock"] and complete and d["pass_id"] != pass_id],
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
    if complete:
        value["preferences"] = {**session["options"]["preferences"], "variant": session["options"]["variant"]}
        value["provider"] = {"model": session["options"]["model"]}
        value["steering"] = (
            "Direct the scene using this accepted state. Invent coherent techniques when the user leaves them open, "
            "but label inventions creative_application or inference. Select this pass's sublayers together as a stack. "
            "Cite packet research and briefly explain its application; unresolved sources are knowledge gaps. "
            "Use a visible baseline and relative changes rather than absolute magnitudes. "
            "Keep contacts, body travel, phases, cause before effect and recovery explicit. "
            "Respect user locks and taste preferences; variant guidance changes only free choices. "
            "Use inputs to name accepted decisions each choice relies on. Account for every sublayer with a decision "
            "or a justified not_applicable disposition. Revise by naming revision_of; never silently overwrite. "
            "Return structured decisions and concise justifications, not private chain-of-thought."
        )
    if complete and pass_id in ("scene_action", "performance"):  # closed movement sets are always on (owner SD-19)
        from .fixed_sets import slot_menus
        value["fixed_sets"], value["registry_gaps"] = slot_menus(root, actor_only=pass_id=="scene_action")
        value["steering"] += (" Select closed movement slots using exactly fixed_set, version, code and member_hash from these menus. "
                              "Outside-set values are registry gaps, not members. Free action wording remains authored. "
                              "Definitions are research; choosing their application remains a creative decision. "
                              "Body may declare initiation_chain, ordered phases with spacing and an Effort action recipe; "
                              "actor kinetic_signature lists its patterns. Record departures explicitly.")
    if complete and pass_id == "staging":  # kinematics is always on (owner SD-18)
        value["steering"] += (" Include a kinematics decision whose kinematic_plan follows cpcs.kinematic_plan/1.0: frame "
                              "(metres, y up, surface y = 0, +x screen-right, camera by position and look_at), each declared "
                              "body's standing hip height, hip tracks, support intervals for every moment (approved parts and "
                              "manner; flight only between a push_off or release and a landing, touchdown or catch), force "
                              "events with the parts each landing puts down, facing headings (0 faces +z, 90 faces +x; mark "
                              "authored spins), relations (toward, away_from or travel forward/backward/sideways), contact modes "
                              "and camera keyframes. It is validated under cpcs-kinematics/1.1; each "
                              "finding returns as a rejection to repair. Cover the accepted scene duration and declared bodies only.")
    if complete and _coverage_enabled(session) and pass_id in NEED_SUBLAYERS:
        # Status reads every unsuperseded choice, including a pass awaiting recheck, so the packet
        # shows exactly which needs a revision reopened. Submit and finish enforce accepted state.
        directory = _directory(session["session_id"], root)
        superseded = {d["revision_of"] for d in session["decisions"] if d["revision_of"]}
        current = [d for d in session["decisions"] if d["decision_id"] not in superseded]
        value["needs"] = [n for n in action_needs(current, _latest_not_applicable(session, directory, root))
                          if n["pass_id"] == pass_id]
        value["steering"] += (" Resolve every listed need: for a body need, give a body choice targeted at that action "
                              "that cites its current decision in inputs; for a camera need, keep a shot whose beat span "
                              "includes the action's beat. Otherwise give a not_applicable with sublayer_id, the action "
                              "target and a concrete reason. Missing research is not a reason.")
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
    directory, session, context = _load(session_id, root)
    if any(row["status"] != "accepted" for row in session["passes"]):
        raise ValidationFailure("directing pass must be accepted before finish")
    if _coverage_enabled(session):
        open_needs = [n["need_id"] for n in action_needs(active_decisions(session), _latest_not_applicable(session, directory, root))
                      if n["status"] == "open"]
        if open_needs:
            raise ValidationFailure("unresolved directing needs: " + ", ".join(open_needs))
    session = copy.deepcopy(session)
    session["decisions"] = active_decisions(session)
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
    complete = "options" in session
    if pass_state["status"] == "accepted":
        if pass_state["proposal_hash"] == proposal_hash:
            return result("already_present", session)
        if not complete or not any(d["revision_of"] for d in proposal["decisions"]):
            reject("pass_already_accepted", None, "pass_id", "A different proposal needs explicit revision records.")
            return result("rejected", session)
    spec = next(row for row in load_pass_registry(root)["passes"] if row["pass_id"] == pass_id)
    if any(p["status"] != "accepted" for p in session["passes"] if p["pass_id"] in spec["reads"]):
        reject("upstream_not_accepted", None, "inputs", "Accept the prerequisite passes before this stack.")
        return result("rejected", session)
    for slot in spec["sublayers"]:
        if slot["required"] and not any(d["sublayer"] == slot["sublayer_id"] for d in proposal["decisions"]):
            reject("missing_required_sublayer", None, slot["sublayer_id"], "Required sublayers need a decision and cannot be not_applicable.")
    slots = {s["sublayer_id"]: s for s in spec["sublayers"]}
    if complete:
        covered = [d["sublayer"] for d in proposal["decisions"]] + [n["sublayer_id"] for n in proposal["not_applicable"]]
        for slot in slots:
            if slot not in covered:
                reject("missing_sublayer_disposition", None, slot, "Every slot needs a choice or justified not_applicable.")
        if any(n["sublayer_id"] in {d["sublayer"] for d in proposal["decisions"]} for n in proposal["not_applicable"] if "target" not in n):
            reject("contradictory_sublayer_disposition", None, "not_applicable", "A selected slot cannot also be not applicable.")
    for absent in proposal["not_applicable"]:
        if "target" in absent:
            continue  # A targeted entry answers one action need; it is checked against the derived needs below.
        slot = slots.get(absent["sublayer_id"])
        if slot is None or slot["required"]:
            reject("missing_required_sublayer", None, absent["sublayer_id"], "Only a declared optional sublayer may be not_applicable.")
    superseded = {d["revision_of"] for d in session["decisions"] if d["revision_of"]}
    current = {d["decision_id"]: d for d in session["decisions"] if d["decision_id"] not in superseded}
    earlier = {d["decision_id"] for d in packet["upstream"]}
    concepts = {(row["id"], row["content_hash"]) for row in packet["research"]["concepts"]}
    concepts.update((m["concept_id"], m["selection"]["member_hash"])
                    for spec in packet.get("fixed_sets", {}).values() for m in spec["members"])
    text = session["ask"]["text"]
    for index, decision in enumerate(proposal["decisions"]):
        old = current.get(decision["decision_id"])
        if complete and old is not None:
            if {k: v for k, v in old.items() if k not in ("pass_id", "sequence")} != decision:
                reject("duplicate_decision_id", index, "decision_id", "A revised choice needs a new decision id and revision_of.")
        if complete and decision["revision_of"] is not None:
            previous = current.get(decision["revision_of"])
            if previous is None or previous["pass_id"] != pass_id or previous["target"] != decision["target"] or previous["sublayer"] != decision["sublayer"]:
                reject("invalid_revision", index, "revision_of", "Revise a current choice owned by this slot and target.")
            elif previous["lock"]:
                reject("locked_decision", index, "revision_of", "A revision cannot replace a locked user choice.")
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
        if complete and status == "sourced_research":
            available = {c["id"]: c for c in packet["research"]["concepts"]}
            if any(available.get(u["id"], {}).get("source_resolution", {}).get("unresolved") or not available.get(u["id"], {}).get("source_resolution", {}).get("passages") for u in cited):
                reject("source_not_resolved", index, "evidence_uses", "Research claims need hash-verified source passages; unresolved cards support creative inference only.")
        if status == "model_tested":
            reject("model_tested_not_admissible", index, "source_status", "This slice admits no model-tested claims.")
        if decision["lock"] and status != "user_explicit":
            reject("lock_requires_user_explicit", index, "lock", "Only a user-explicit decision may be locked.")
        if decision["layer"] != pass_id:
            reject("path_not_allowed", index, "layer", "The decision belongs to the requested pass.")
    candidate = copy.deepcopy(session)
    if complete:
        fresh = [d for d in proposal["decisions"] if d["decision_id"] not in current]
        candidate["decisions"].extend(_accepted_decisions({**proposal, "decisions": fresh}, len(session["decisions"])))
        next(p for p in candidate["passes"] if p["pass_id"] == pass_id)["status"] = "accepted"
        # Revision leaves history intact, but consumers must explicitly re-check the new input.
        if any(d["revision_of"] for d in fresh):
            affected = {pass_id}
            for row in load_pass_registry(root)["passes"]:
                if set(row["reads"]) & affected:
                    affected.add(row["pass_id"])
                    next(p for p in candidate["passes"] if p["pass_id"] == row["pass_id"])["status"] = "needs_recheck"
        errors.extend(value_check(active_decisions(candidate), spec, packet))
        targeted = [n for n in proposal["not_applicable"] if "target" in n]
        if _coverage_enabled(session) and pass_id in NEED_SUBLAYERS:
            needs = [n for n in action_needs(active_decisions(candidate), {pass_id: targeted}) if n["pass_id"] == pass_id]
            known = {(n["sublayer_id"], n["target"]["item_id"]) for n in needs}
            for entry in targeted:
                if (entry["sublayer_id"], entry["target"]["item_id"]) not in known:
                    reject("unknown_need", None, "not_applicable", "A targeted not_applicable must answer a listed action need.")
            for need in needs:
                if need["status"] == "open":
                    reject("unresolved_need", None, need["need_id"], "Resolve this action need with a targeted choice or a justified targeted not_applicable.")
        elif targeted:
            reject("unknown_need", None, "not_applicable", "This session lists no action needs to answer.")
    else:
        fresh = proposal["decisions"]
        errors.extend(value_check(session["decisions"] + fresh, spec, packet))
        if any("target" in n for n in proposal["not_applicable"]):
            reject("unknown_need", None, "not_applicable", "This session lists no action needs to answer.")
    if errors:
        return result("rejected", session)
    captures = _ensure_private_dir(directory / "proposals", root)
    if complete:
        # Capture only newly authored records, including explicit revisions. Recheck proposals
        # may reuse current decisions; those are not duplicate ledger entries.
        capture = proposal
        capture_hash = sha256_value(capture)
        capture_path = captures / (capture_hash[7:] + ".json")
        if not capture_path.exists():
            _write_new(capture_path, capture)
        candidate["captures"].append({"pass_id": pass_id, "proposal_hash": capture_hash})
        session = candidate
        pass_state = next(p for p in session["passes"] if p["pass_id"] == pass_id)
    else:
        _write_new(captures / (pass_id + ".json"), proposal)
        session["decisions"].extend(_accepted_decisions(proposal, len(session["decisions"])))
    pass_state.update(status="accepted", proposal_hash=proposal_hash)
    session = _seal(session, root)
    _replace(directory / "session.json", session)
    return result("accepted", session)


def withdraw_decision(session_id: str, decision_id: str, field: str, reason: str, *, value_check, root: Path = REPO_ROOT) -> dict:
    """Append a scoped optional-field revision; preserve captures and locks."""
    directory, session, context = _load(session_id, root)
    previous = next((d for d in active_decisions(session) if d['decision_id'] == decision_id), None)
    if previous is None or previous['lock']:
        raise ValidationFailure('PROTECTED_OR_UNKNOWN_DECISION')
    optional={'FACE','WHY','TACTIC','EFFORT','SHAPE','SPACE','BODY','READ'}
    if not field.startswith('direction.') or field.split('.',1)[1] not in optional or not reason.strip():
        raise ValidationFailure('PROTECTED_DIRECTION_FIELD')
    revised={k:copy.deepcopy(v) for k,v in previous.items() if k not in ('sequence','pass_id')}
    label=field.split('.',1)[1]
    if label not in revised['values'].get('direction',{}):raise ValidationFailure('UNKNOWN_DIRECTION_FIELD')
    del revised['values']['direction'][label]
    target=previous['target'];reference=target['path']+'.'+target['item_id']+'.'+field
    revised['values'].setdefault('direction_omissions',[]).append(dict(ref=reference,decision_id=decision_id,reason=reason))
    revised.update(decision_id='withdraw_'+sha256_value([decision_id,field,reason])[7:31],revision_of=decision_id,justification=reason)
    candidate=copy.deepcopy(session);candidate['decisions'].extend(_accepted_decisions(dict(pass_id=previous['pass_id'],decisions=[revised]),len(candidate['decisions'])))
    spec=next(p for p in load_pass_registry(root)['passes'] if p['pass_id']==previous['pass_id'])
    errors=value_check(active_decisions(candidate),spec,_packet(session,context,previous['pass_id'],root))
    if errors:raise ValidationFailure(str(errors))
    captures=_ensure_private_dir(directory/'proposals',root)
    if 'captures' not in candidate:
        candidate['captures']=[]
        for row in candidate['passes']:
            if row['proposal_hash'] is not None:
                old=_read_object(captures/(row['pass_id']+'.json'),'proposal')
                name=captures/(row['proposal_hash'][7:]+'.json')
                if not name.exists():_write_new(name,old)
                candidate['captures'].append(dict(pass_id=row['pass_id'],proposal_hash=row['proposal_hash']))
    proposal=dict(schema='cpcs.directing_proposal/1.0',pass_id=previous['pass_id'],decisions=[revised],not_applicable=[])
    validate_contract('proposal',proposal,root);digest=sha256_value(proposal)
    path=captures/(digest[7:]+'.json')
    if not path.exists():_write_new(path,proposal)
    candidate['captures'].append(dict(pass_id=previous['pass_id'],proposal_hash=digest))
    next(p for p in candidate['passes'] if p['pass_id']==previous['pass_id']).update(status='accepted',proposal_hash=digest)
    affected={previous['pass_id']}
    for row in load_pass_registry(root)['passes']:
        if set(row['reads']) & affected:
            affected.add(row['pass_id'])
            for current in candidate['passes']:
                if current['pass_id']==row['pass_id']:current['status']='needs_recheck'
    candidate=_seal(candidate,root);_replace(directory/'session.json',candidate)
    return dict(disposition='withdrawn',decision_id=revised['decision_id'],ledger_hash=candidate['ledger_hash'])
