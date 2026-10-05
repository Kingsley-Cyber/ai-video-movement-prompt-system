"""Run a whole directing session from one scene card (owner 2026-10-04; Codex audit REQ-AUD-11).

The eight directing passes, their order, the sealed ledger and every check stay exactly as they
are. What moves into Python is the plumbing an agent used to do by hand for each pass: reading
packets, writing decision ids and closed-set hashes, wiring inputs to the current upstream
decisions, filling not-applicable slots, writing revision records when an accepted choice changes,
rechecking downstream passes, and building the prompt.

    python3 -m lab.application.direct_runner brief --ask-file ask.txt [--model seedance-2.0]
    python3 -m lab.application.direct_runner run --card card.yaml

``brief`` opens (or reuses) the session and prints everything the author needs for every pass in
one page. ``run`` submits the card pass by pass through the public operations. A rejection stops
the run and is reported against the card field that caused it; fix the card and run again.
Accepted, unchanged passes are reused, so a rerun only does the work that changed.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from lab.application.service import REQUEST_SCHEMA, invoke
from lab.second_brain.src.validate import REPO_ROOT

PASSES = ("scene_action", "performance", "staging", "camera", "light_color", "style", "audio", "synthesis")
SCENE_SLOTS = {"scene": "scenes", "entities": "entities", "beats": "beats", "actions": "actions", "interactions": "interactions"}
REFERENCE_KEYS = ("actor", "target", "beat", "end_beat", "action", "caused_by")
DEFAULT_LAYOUT = {"prompt_format": "prose", "prompt_layout": "director_v1", "project_id": "cpcs-local-export"}


class RunFailed(Exception):
    pass


class Runner:
    def __init__(self, root: Path = REPO_ROOT, role: str = "operator") -> None:
        self.root, self.role = root, role
        self.calls: list[dict] = []

    # ---- public operations, timed --------------------------------------------------------
    def call(self, operation: str, arguments: dict) -> dict:
        started = time.perf_counter()
        response = invoke(dict(schema=REQUEST_SCHEMA, operation="cpcs." + operation, arguments=arguments),
                          role=self.role, root=self.root)
        self.calls.append({"operation": operation, "seconds": round(time.perf_counter() - started, 3),
                           "status": response["status"]})
        if response["status"] != "success":
            raise RunFailed(f"{operation}: {response['error']['code']}: {response['error']['message']}")
        return response["result"]

    def start(self, ask: str, model: str, variant: str | None) -> dict:
        options = dict(text=ask, mode="complete", model=model)
        if variant:
            options["variant"] = variant
        return self.call("direct.start", options)

    def packet(self, session_id: str, pass_id: str) -> dict:
        return self.call("direct.packet.read", dict(session_id=session_id, pass_id=pass_id))

    def state(self, session_id: str) -> dict:
        return self.call("direct.state.read", dict(session_id=session_id))

    # ---- brief -------------------------------------------------------------------------------
    def brief(self, ask: str, model: str = "seedance-2.0", variant: str | None = None) -> str:
        started = self.start(ask, model, variant)
        sid = started["session_id"]
        lines = [f"SESSION {sid}  model {model}", f"ASK {ask.strip()}", ""]
        for pass_id in PASSES:
            packet = self.packet(sid, pass_id)
            lines.append(f"## {pass_id}: {packet['question']}")
            for slot in packet["sublayers"]:
                fields = ", ".join(slot.get("fields", [])) or "(whole item)"
                lines.append(f"- {slot['sublayer_id']} [{'required' if slot['required'] else 'optional'}] -> {slot['target_path']}: {fields}")
            for set_id, spec in sorted(packet.get("fixed_sets", {}).items()):
                terms = "; ".join(f"{m['term']} = {m['visible_wording'][:70]}" for m in spec["members"])
                lines.append(f"  menu {set_id}: {terms}")
            for concept in packet["research"]["concepts"]:
                resolved = bool(concept.get("source_resolution", {}).get("passages")) and not concept.get("source_resolution", {}).get("unresolved")
                lines.append(f"  research {concept['id']} ({'citable as sourced' if resolved else 'inspiration only'}): {concept['what'][:150]}")
            if packet["research"]["knowledge_gaps"]:
                lines.append("  gaps: " + ", ".join(packet["research"]["knowledge_gaps"]))
            for rule in packet.get("render_rules", []):
                lines.append(f"  render rule {rule['rule_id']} [{rule['level']}]: {rule['statement']} Instead: {rule['instead']}")
            if pass_id == "staging":
                lines.append("  " + packet["steering"].split("Include a kinematics decision", 1)[-1][:900].strip())
            lines.append("")
        lines.append("Write the scene card (handoff/direct_scene/USE_THE_COMPILER.md, 'Scene card'), then run it.")
        return "\n".join(lines)

    # ---- card -> decisions --------------------------------------------------------------------
    def run(self, card: dict, *, build_settings: dict | None = None) -> dict:
        started_at = time.perf_counter()
        ask = card["ask"]
        sid = self.start(ask, card.get("model", "seedance-2.0"), card.get("variant"))["session_id"]
        notes: list[str] = []
        for pass_id in PASSES:
            state = self.state(sid)
            status = next(p["status"] for p in state["passes"] if p["pass_id"] == pass_id)
            current = _current(state, pass_id)
            packet = self.packet(sid, pass_id)
            desired = _desired(card, pass_id, packet, state, sid)
            decisions, changed = _reconcile(desired, current)
            if status == "accepted" and not changed:
                notes.append(f"{pass_id}: unchanged")
                continue
            card_paths = [d.pop("_card") for d in decisions]
            given = {d["sublayer"] for d in decisions}
            skips = card.get("skip", {}).get(pass_id, {})
            not_applicable = [dict(sublayer_id=s["sublayer_id"], reason=skips.get(s["sublayer_id"], "Not needed for this scene."))
                              for s in packet["sublayers"] if not s["required"] and s["sublayer_id"] not in given]
            proposal = dict(schema="cpcs.directing_proposal/1.0", pass_id=pass_id, decisions=decisions, not_applicable=not_applicable)
            result = self.call("direct.proposal.submit", dict(session_id=sid, pass_id=pass_id,
                                                              packet_hash=packet["packet_hash"], proposal=proposal))
            if result["disposition"] == "rejected":
                problems = []
                by_id = {d["decision_id"]: path for d, path in zip(decisions, card_paths)}
                for rejection in result["rejections"]:
                    index = rejection["decision_index"]
                    if rejection.get("decision_id") is not None:
                        where = by_id.get(rejection["decision_id"], "earlier pass decision " + rejection["decision_id"])
                    elif index is None and rejection["path"].startswith("decisions/"):
                        where = card_paths[int(rejection["path"].split("/")[1])]
                    else:
                        where = f"{pass_id}.{rejection['path']}"
                    problems.append(f"{rejection['code']} at {where}: {rejection['message']}")
                raise RunFailed(f"{pass_id} rejected:\n  " + "\n  ".join(problems))
            notes.append(f"{pass_id}: {result['disposition']}" + (f" ({sum(1 for d in decisions if d.get('revision_of'))} revised)" if status != "pending" else ""))
        settings = dict(DEFAULT_LAYOUT, duration_seconds=_duration(card), **(build_settings or {}))
        finished = self.call("direct.finish", dict(session_id=sid, build_settings=settings))
        if finished.get("build") is None:
            raise RunFailed("finish returned no build: " + json.dumps(finished.get("provider_fit")))
        artifacts = finished["build"]["artifacts"]
        prompt = artifacts["prompt.txt"]["content"]
        report = json.loads(artifacts["capability_report.json"]["content"])
        return {
            "session_id": sid, "score_id": finished["score"]["score_id"], "prompt": prompt,
            "prompt_chars": len(prompt), "passes": notes, "calls": len(self.calls),
            "python_seconds": round(sum(c["seconds"] for c in self.calls), 2),
            "elapsed_seconds": round(time.perf_counter() - started_at, 2),
            "withheld_defaults": sorted(d["path"] for d in report["dispositions"] if d["status"] == "withheld"),
            "artifacts": artifacts,
        }


def _duration(card: dict) -> int:
    scenes = card["scene_action"]["scene"]
    value = next(iter(scenes.values()))["duration_s"]
    return int(value)


def _current(state: dict, pass_id: str) -> list[dict]:
    """The latest decision per slot and target for one pass, whatever the pass status."""
    superseded = {d["revision_of"] for d in state["decisions"] if d.get("revision_of")}
    return [d for d in state["decisions"] if d["pass_id"] == pass_id and d["decision_id"] not in superseded]


def _selection(packet: dict, set_id: str, value: Any, where: str) -> Any:
    if not isinstance(value, str):
        return value
    spec = packet.get("fixed_sets", {}).get(set_id)
    if spec is None:
        raise RunFailed(f"{where}: no {set_id} menu in this packet")
    member = next((m for m in spec["members"] if m["term"] == value), None)
    if member is None:
        raise RunFailed(f"{where}: '{value}' is not in {set_id}; choose one of: {', '.join(m['term'] for m in spec['members'])}")
    return copy.deepcopy(member["selection"])


CLOSED_FIELDS = {"effort_weight": "laban.effort.weight", "effort_time": "laban.effort.time", "effort_space": "laban.effort.space",
                 "effort_flow": "laban.effort.flow", "shape": "laban.shape.quality", "connectivity": "bartenieff.connectivity"}


def _desired(card: dict, pass_id: str, packet: dict, state: dict, sid: str) -> list[dict]:
    """The decisions the card asks for in one pass, with ids, inputs, evidence and selections filled in."""
    section = card.get(pass_id) or {}
    # Inputs may name only accepted upstream decisions or earlier decisions in this proposal.
    # Scene items cite the scene_action decision that declared them; later passes cite their own stacks.
    index: dict[tuple[str, str], list[str]] = {}
    for d in packet["upstream"]:
        if d["pass_id"] == "scene_action" or d["target"]["path"] == "scenes":
            index.setdefault((d["target"]["path"], d["target"]["item_id"]), []).append(d["decision_id"])
    why = card.get("why", {})
    cite = card.get("cite", {})
    relative = card.get("relative", {})
    concepts = {c["id"]: c for c in packet["research"]["concepts"]}
    ask = packet["ask"]["text"]
    duration_span = packet["constraints"].get("duration_source")
    slots = {s["sublayer_id"]: s for s in packet["sublayers"]}
    out: list[dict] = []
    proposal_items: dict[tuple[str, str], list[str]] = {}

    def inputs_for(path: str, item: dict | None, item_id: str) -> list[str]:
        refs: list[tuple[str, str]] = []
        if pass_id == "scene_action":
            for key in REFERENCE_KEYS:
                value = (item or {}).get(key)
                if isinstance(value, str):
                    refs.append(("beats" if key in ("beat", "end_beat") else "actions" if key in ("action", "caused_by") else "entities", value))
        elif path == "actions":
            refs.append(("actions", item_id))
        elif path == "shots":
            beat = (item or {}).get("beat")
            refs += [("beats", beat)] + [("actions", a) for a, d in (card["scene_action"].get("actions") or {}).items() if d.get("beat") == beat]
        else:
            # A scene-wide stack cites the nearest accepted pass it reads (the first decision of that stack).
            upstream = {d["pass_id"] for d in packet["upstream"]}
            nearest = next((p for p in reversed(PASSES[:PASSES.index(pass_id)]) if p in upstream), "scene_action")
            return [d["decision_id"] for d in packet["upstream"] if d["pass_id"] == nearest][:1]
        ids: list[str] = []
        for ref in refs:
            ids += index.get(ref, []) or proposal_items.get(ref, [])   # upstream first; within scene_action, earlier items
        return list(dict.fromkeys(ids))

    def add(path: str, item_id: str, sublayer: str, values: dict, item: dict | None, card_path: str, suffix: str = "") -> None:
        key = f"{path}.{item_id}"
        status, uses = "creative_application", []
        if suffix == ".duration":   # the length the ask states is the user's, and locked
            status = "user_explicit"
            uses.append(dict(kind="ask_span", start=duration_span["start"], end=duration_span["end"], text=duration_span["text"]))
        for concept_id in cite.get(key, []) if suffix != ".duration" else []:
            concept = concepts.get(concept_id)
            if concept is None:
                raise RunFailed(f"{card_path}: cites {concept_id}, which this pass's research does not contain")
            uses.append(dict(kind="concept", id=concept_id, content_hash=concept["content_hash"]))
            resolution = concept.get("source_resolution", {})
            if resolution.get("passages") and not resolution.get("unresolved") and status == "creative_application":
                status = "sourced_research"
        for phrase in card.get("ask_spans", {}).get(key, []) if suffix != ".duration" else []:
            start = ask.find(phrase)
            if start < 0:
                raise RunFailed(f"{card_path}: ask span '{phrase}' is not in the ask")
            uses.append(dict(kind="ask_span", start=start, end=start + len(phrase), text=phrase))
            status = "user_explicit"
        decision = dict(
            decision_id=f"{pass_id}.{path}.{item_id}.{sublayer}{suffix}", layer=pass_id, sublayer=sublayer,
            target=dict(path=path, item_id=item_id), values=values, inputs=inputs_for(path, item, item_id),
            relative_anchor=relative.get(key) if pass_id == "scene_action" else None,
            justification=why.get(key, f"Authored in the scene card as part of the {pass_id} stack."),
            source_status=status, evidence_uses=uses, lock=suffix == ".duration",
            revision_of=None, _card=card_path)
        proposal_items.setdefault((path, item_id), []).append(decision["decision_id"])
        out.append(decision)

    if pass_id == "scene_action":
        for sublayer, path in SCENE_SLOTS.items():
            for item_id, item in (section.get(sublayer) or {}).items():
                values = copy.deepcopy(item)
                if (sublayer == "scene" and duration_span and values.get("duration_s") == packet["constraints"]["requested_duration_s"]):
                    timing = {k: values.pop(k) for k in ("order", "duration_s") if k in values}
                    add(path, item_id, sublayer, timing, item, f"scene_action.scene.{item_id}.duration_s", ".duration")
                if values:
                    add(path, item_id, sublayer, values, item, f"scene_action.{sublayer}.{item_id}")
        return out
    by_field = {f: s for s, spec in slots.items() for f in spec.get("fields", [])}
    if pass_id in ("performance", "camera"):
        path = "actions" if pass_id == "performance" else "shots"
        for item_id, item in section.items():
            grouped: dict[str, dict] = {}
            for field, value in item.items():
                if field not in by_field:
                    raise RunFailed(f"{pass_id}.{item_id}.{field}: not a field of this pass; fields: {', '.join(sorted(by_field))}")
                if field in CLOSED_FIELDS:
                    value = _selection(packet, CLOSED_FIELDS[field], value, f"{pass_id}.{item_id}.{field}")
                grouped.setdefault(by_field[field], {})[field] = value
            for sublayer, values in grouped.items():
                add(path, item_id, sublayer, values, item if path == "shots" else None, f"{pass_id}.{item_id}.{sublayer}")
        return out
    scene_id = next(iter(card["scene_action"]["scene"]))
    grouped = {}
    for field, value in section.items():
        if field not in by_field:
            raise RunFailed(f"{pass_id}.{field}: not a field of this pass; fields: {', '.join(sorted(by_field))}")
        grouped.setdefault(by_field[field], {})[field] = value
    for sublayer, values in grouped.items():
        add("scenes", scene_id, sublayer, values, None, f"{pass_id}.{sublayer}")
    return out


def _reconcile(desired: list[dict], current: list[dict]) -> tuple[list[dict], bool]:
    """Reuse unchanged current decisions and write revisions for changed ones, in proposal order.

    Inputs written against base ids are remapped to the ids this proposal ends up using, so a
    decision that depends on a revised one is itself revised with the new input (no stale inputs).
    """
    by_base = {d["decision_id"].partition("~")[0]: d for d in current}
    id_map: dict[str, str] = {}
    out, changed = [], False
    for decision in desired:
        base, card_path = decision["decision_id"], decision.pop("_card")
        decision["inputs"] = [id_map.get(i, i) for i in decision["inputs"]]
        old = by_base.pop(base, None)
        if old is not None:
            comparable = {k: v for k, v in old.items() if k not in ("pass_id", "sequence")}
            if comparable == {**decision, "decision_id": old["decision_id"], "revision_of": old["revision_of"]}:
                id_map[base] = old["decision_id"]
                out.append({**comparable, "_card": card_path})
                continue
            generation = old["decision_id"].partition("~")[2]
            decision["decision_id"] = f"{base}~{int(generation) + 1 if generation.isdigit() else 2}"
            decision["revision_of"] = old["decision_id"]
        id_map[base] = decision["decision_id"]
        changed = True
        out.append({**decision, "_card": card_path})
    if by_base:
        changed = True   # a choice was removed from the card; the remaining stack is resubmitted
    return out, changed


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    brief = sub.add_parser("brief")
    brief.add_argument("--ask-file", type=Path, required=True)
    brief.add_argument("--model", default="seedance-2.0")
    brief.add_argument("--variant")
    run = sub.add_parser("run")
    run.add_argument("--card", type=Path, required=True)
    run.add_argument("--out", type=Path, help="directory under work/ for prompt.txt and reports")
    args = parser.parse_args(argv)
    runner = Runner()
    try:
        if args.command == "brief":
            print(runner.brief(args.ask_file.read_text(encoding="utf-8"), args.model, args.variant))
            return
        card = yaml.safe_load(args.card.read_text(encoding="utf-8"))
        result = runner.run(card)
    except RunFailed as exc:
        print(f"STOPPED after {len(runner.calls)} calls, {sum(c['seconds'] for c in runner.calls):.1f} s in Python\n{exc}")
        sys.exit(1)
    out = args.out or REPO_ROOT / "work" / "direct_runs" / result["session_id"]
    out.mkdir(parents=True, exist_ok=True)
    for name, artifact in result["artifacts"].items():
        (out / name).write_text(artifact["content"], encoding="utf-8")
    summary = {k: v for k, v in result.items() if k not in ("prompt", "artifacts")}
    (out / "run_report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"\nPROMPT ({result['prompt_chars']} characters) -> {out / 'prompt.txt'}\n")
    print(result["prompt"])


if __name__ == "__main__":
    main()
