"""NB-1 — Narrative beat + causal spine projection (deterministic).

Converts the user's ordinary-language action sequence into a
provenance-preserving NarrativeBeatGraph and binds existing SI-1
interaction units, recruited knowledge, placement, and TD-1 scheduling
to those narrative beats.

Frozen rules:
- USER-EXPRESSED narrative beats are distinct from CPCS-DERIVED
  supporting/consequence beats; every beat records its origin.
- D4: narrative beats are NOT canonical controls; no prose-to-control
  coercion; display names are diagnostic labels only (identity is
  structured: predicate + actor + object + source span + intent hash).
- Clause order establishes USER_SEQUENCE (temporal precedence), never
  causation. STATE_TRANSITION edges come only from the declared
  consequence vocabulary. No invented causal claims.
- Units bind to at most one beat, by structured overlap
  (failure families from the action vocabulary vs unit lineage);
  UNRESOLVED_BINDING is a valid recorded outcome.
- Unresolved fields stay unresolved; nothing is guessed.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

NB1_GRAPH_SCHEMA = "cpcs.narrative_beat_graph/0.1"
NB1_BEAT_SCHEMA = "cpcs.narrative_beat/0.1"

BEAT_ORIGINS = frozenset({
    "USER_EXPLICIT", "USER_IMPLIED_SEQUENCE", "DERIVED_PREREQUISITE",
    "SUPPORTING_TRANSITION",
})
EDGE_KINDS = frozenset({
    "EXPLICIT_BEFORE", "EXPLICIT_AFTER", "USER_SEQUENCE",
    "CAUSAL_REQUIRED", "PREREQUISITE_OF", "STATE_TRANSITION",
    "OVERLAP_ALLOWED", "SUPPORTING_TRANSITION",
})
BINDING_KINDS = frozenset({
    "DIRECT_BINDING", "SUPPORTING_BINDING", "UNRESOLVED_BINDING",
})

# Conservative narrative-action vocabulary. Each entry maps a surface
# verb phrase to a predicate identity, interaction class, associated
# failure families, and DECLARED consequence beats (state transitions
# only — never causal claims about the physical world).
NARRATIVE_ACTIONS: dict[str, dict[str, Any]] = {
    "pick up": {"predicate_id": "PICK_UP", "interaction_class":
                "hand_object", "failure_families": ["FF-CONTACT",
                                                    "FF-IDENTITY"],
                "consequences": []},
    "picks up": {"predicate_id": "PICK_UP", "interaction_class":
                 "hand_object", "failure_families": ["FF-CONTACT",
                                                     "FF-IDENTITY"],
                 "consequences": []},
    "take a drink": {"predicate_id": "DRINK", "interaction_class":
                     "human_object_contact", "failure_families":
                     ["FF-CONTACT", "FF-DEFORMATION"], "consequences": []},
    "takes a drink": {"predicate_id": "DRINK", "interaction_class":
                      "human_object_contact", "failure_families":
                      ["FF-CONTACT", "FF-DEFORMATION"], "consequences": []},
    "drink": {"predicate_id": "DRINK", "interaction_class":
              "human_object_contact", "failure_families":
              ["FF-CONTACT", "FF-DEFORMATION"], "consequences": []},
    "sip": {"predicate_id": "DRINK", "interaction_class":
            "human_object_contact", "failure_families":
            ["FF-CONTACT", "FF-DEFORMATION"], "consequences": []},
    "talk": {"predicate_id": "APPRAISAL_DIALOGUE", "interaction_class":
             "performance_dialogue", "failure_families":
             ["FF-CONTINUITY", "FF-TIMING"], "consequences": []},
    "talks": {"predicate_id": "APPRAISAL_DIALOGUE", "interaction_class":
              "performance_dialogue", "failure_families":
              ["FF-CONTINUITY", "FF-TIMING"], "consequences": []},
    "talking": {"predicate_id": "APPRAISAL_DIALOGUE", "interaction_class":
                "performance_dialogue", "failure_families":
                ["FF-CONTINUITY", "FF-TIMING"], "consequences": []},
    "show": {"predicate_id": "PRODUCT_REVEAL", "interaction_class":
             "product_camera", "failure_families":
             ["FF-IDENTITY", "FF-VISIBILITY", "FF-CAMERA"],
             "consequences": []},
    "shows": {"predicate_id": "PRODUCT_REVEAL", "interaction_class":
              "product_camera", "failure_families":
              ["FF-IDENTITY", "FF-VISIBILITY", "FF-CAMERA"],
              "consequences": []},
    "showing": {"predicate_id": "PRODUCT_REVEAL", "interaction_class":
                "product_camera", "failure_families":
                ["FF-IDENTITY", "FF-VISIBILITY", "FF-CAMERA"],
                "consequences": []},
    "catch": {"predicate_id": "CATCH", "interaction_class": "combat_contact",
              "failure_families": ["FF-CONTACT", "FF-SUPPORT"],
              "consequences": []},
    "catches": {"predicate_id": "CATCH", "interaction_class":
                "combat_contact", "failure_families":
                ["FF-CONTACT", "FF-SUPPORT"], "consequences": []},
    "swing": {"predicate_id": "SWING", "interaction_class":
              "combat_projection", "failure_families":
              ["FF-ROTATION", "FF-SUPPORT"], "consequences": []},
    "swings": {"predicate_id": "SWING", "interaction_class":
               "combat_projection", "failure_families":
               ["FF-ROTATION", "FF-SUPPORT"], "consequences": []},
    "release": {"predicate_id": "RELEASE", "interaction_class":
                "contact_release", "failure_families":
                ["FF-CONTACT", "FF-CAUSALITY"],
                "consequences": ["IMPACT"]},
    "releases": {"predicate_id": "RELEASE", "interaction_class":
                 "contact_release", "failure_families":
                 ["FF-CONTACT", "FF-CAUSALITY"],
                 "consequences": ["IMPACT"]},
    "throw": {"predicate_id": "THROW", "interaction_class":
              "combat_projection", "failure_families":
              ["FF-ROTATION", "FF-CAUSALITY"],
              "consequences": ["FLIGHT", "IMPACT"]},
    "throws": {"predicate_id": "THROW", "interaction_class":
               "combat_projection", "failure_families":
               ["FF-ROTATION", "FF-CAUSALITY"],
               "consequences": ["FLIGHT", "IMPACT"]},
    "fall": {"predicate_id": "FALL", "interaction_class":
             "object_motion", "failure_families":
             ["FF-PHYSICS", "FF-CAUSALITY"], "consequences": ["IMPACT"]},
    "falls": {"predicate_id": "FALL", "interaction_class": "object_motion",
              "failure_families": ["FF-PHYSICS", "FF-CAUSALITY"],
              "consequences": ["IMPACT"]},
    "land": {"predicate_id": "LAND", "interaction_class": "environment_contact",
             "failure_families": ["FF-SUPPORT", "FF-PHYSICS"],
             "consequences": ["SETTLE"]},
    "lands": {"predicate_id": "LAND", "interaction_class":
              "environment_contact", "failure_families":
              ["FF-SUPPORT", "FF-PHYSICS"], "consequences": ["SETTLE"]},
    "recover": {"predicate_id": "RECOVERY", "interaction_class":
                "support_reacquisition", "failure_families":
                ["FF-SUPPORT", "FF-PHYSICS"], "consequences": []},
    "recovers": {"predicate_id": "RECOVERY", "interaction_class":
                 "support_reacquisition", "failure_families":
                 ["FF-SUPPORT", "FF-PHYSICS"], "consequences": []},
    "press": {"predicate_id": "PRESSURE", "interaction_class":
              "combat_follow_up", "failure_families":
              ["FF-CAUSALITY", "FF-CONTACT"], "consequences": []},
    "pressures": {"predicate_id": "PRESSURE", "interaction_class":
                  "combat_follow_up", "failure_families":
                  ["FF-CAUSALITY", "FF-CONTACT"], "consequences": []},
    "unbox": {"predicate_id": "UNBOX", "interaction_class":
              "hand_object", "failure_families":
              ["FF-CONTACT", "FF-IDENTITY"], "consequences": []},
    "unboxes": {"predicate_id": "UNBOX", "interaction_class": "hand_object",
                "failure_families": ["FF-CONTACT", "FF-IDENTITY"],
                "consequences": []},
    "slice": {"predicate_id": "SLICE", "interaction_class":
              "tool_object_contact", "failure_families":
              ["FF-CONTACT", "FF-DEFORMATION"], "consequences": []},
    "slices": {"predicate_id": "SLICE", "interaction_class":
               "tool_object_contact", "failure_families":
               ["FF-CONTACT", "FF-DEFORMATION"], "consequences": []},
    "assemble": {"predicate_id": "ASSEMBLE", "interaction_class":
                 "hand_object", "failure_families":
                 ["FF-CONTACT", "FF-STATE"], "consequences": []},
    "assembles": {"predicate_id": "ASSEMBLE", "interaction_class":
                  "hand_object", "failure_families":
                  ["FF-CONTACT", "FF-STATE"], "consequences": []},
    "apply": {"predicate_id": "APPLY", "interaction_class":
              "human_object_contact", "failure_families":
              ["FF-CONTACT", "FF-DEFORMATION"], "consequences": []},
    "applies": {"predicate_id": "APPLY", "interaction_class":
                "human_object_contact", "failure_families":
                ["FF-CONTACT", "FF-DEFORMATION"], "consequences": []},
    "open": {"predicate_id": "OPEN", "interaction_class":
             "articulated_object", "failure_families":
             ["FF-STATE", "FF-CONTACT"], "consequences": []},
    "opens": {"predicate_id": "OPEN", "interaction_class":
              "articulated_object", "failure_families":
              ["FF-STATE", "FF-CONTACT"], "consequences": []},
    "exchange": {"predicate_id": "DIALOGUE_EXCHANGE", "interaction_class":
                 "performance_dialogue", "failure_families":
                 ["FF-TIMING", "FF-CONTINUITY"], "consequences": []},
    "exchanges": {"predicate_id": "DIALOGUE_EXCHANGE", "interaction_class":
                  "performance_dialogue", "failure_families":
                  ["FF-TIMING", "FF-CONTINUITY"], "consequences": []},
    "respond": {"predicate_id": "APPRAISAL_RESPONSE", "interaction_class":
                "performance_dialogue", "failure_families":
                ["FF-TIMING", "FF-CONTINUITY"], "consequences": []},
    "responds": {"predicate_id": "APPRAISAL_RESPONSE", "interaction_class":
                 "performance_dialogue", "failure_families":
                 ["FF-TIMING", "FF-CONTINUITY"], "consequences": []},
}

ACTOR_TOKENS = ("woman", "man", "creator", "fighter", "actor", "actress",
                "performer", "chef", "person", "hands", "hand", "she", "he",
                "her", "his")
OBJECT_TOKENS = ("water bottle", "bottle", "serum", "watch", "tomato",
                 "letter", "keyboard", "dropper", "glass", "box", "camera",
                 "phone", "opponent", "leg", "knife", "product")

_CLAUSE_RE = re.compile(r",\s*|\.\s*|;\s*|\s+and\s+|\s+then\s+", re.IGNORECASE)


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _find_all_actions(clause: str) -> list[tuple[str, dict[str, Any]]]:
    """All non-overlapping action matches in clause order (a clause may
    contain multiple user actions, e.g. 'pressures him while he tries to
    recover')."""
    low = " " + clause.lower() + " "
    matches: list[tuple[int, str, dict[str, Any]]] = []
    for phrase, spec in sorted(NARRATIVE_ACTIONS.items(),
                               key=lambda kv: -len(kv[0])):
        for match in re.finditer(rf"\b{re.escape(phrase)}\b", low):
            if phrase in ("show", "shows", "showing") and re.search(
                    rf"\b{re.escape(phrase)}\s+off\b", low):
                continue
            matches.append((match.start(), phrase, spec))
    matches.sort(key=lambda m: m[0])
    chosen: list[tuple[str, dict[str, Any]]] = []
    covered_until = -1
    for start, phrase, spec in matches:
        if start < covered_until:
            continue
        chosen.append((phrase, spec))
        covered_until = start + len(phrase)
    if not chosen:
        for pattern, phrase in (
            (re.compile(r"\bpicks?\s+\w+\s+up\b"), "pick up"),
            (re.compile(r"\bpicked\s+\w+\s+up\b"), "pick up"),
        ):
            match = pattern.search(low)
            if match:
                return [(phrase, NARRATIVE_ACTIONS["pick up"])]
    return chosen


def _find_action(clause: str) -> tuple[str, dict[str, Any], int] | None:
    found = _find_all_actions(clause)
    return (found[0][0], found[0][1], 0) if found else None


def _extract_actor(clause: str) -> str | None:
    low = clause.lower()
    for token in sorted(ACTOR_TOKENS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(token)}\b", low):
            return token
    return None


def _extract_object(clause: str) -> str | None:
    low = clause.lower()
    for token in sorted(OBJECT_TOKENS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(token)}\b", low):
            return token
    return None


@dataclass
class NarrativeBeat:
    beat_id: str
    origin: str
    display_name: str
    predicate_id: str
    source_span: str
    actor_ids: list[str]
    object_ids: list[str]
    intended_outcome: list[str]
    explicit_order_index: int
    interaction_class: str | None
    state_change_candidate: list[str]
    failure_families: list[str]
    bound_si1_unit_ids: list[str]
    binding_kind: str
    unresolved_fields: list[str]
    lineage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": NB1_BEAT_SCHEMA,
            "beat_id": self.beat_id,
            "origin": self.origin,
            "display_name": self.display_name,
            "predicate_id": self.predicate_id,
            "source_span": self.source_span,
            "actor_ids": self.actor_ids,
            "object_ids": self.object_ids,
            "intended_outcome": self.intended_outcome,
            "explicit_order_index": self.explicit_order_index,
            "interaction_class": self.interaction_class,
            "state_change_candidate": self.state_change_candidate,
            "failure_families": self.failure_families,
            "bound_si1_unit_ids": self.bound_si1_unit_ids,
            "binding_kind": self.binding_kind,
            "unresolved_fields": self.unresolved_fields,
            "lineage": self.lineage,
        }


@dataclass
class NarrativeBeatGraph:
    graph_id: str
    graph_hash: str
    beats: list[dict[str, Any]]
    edges: list[dict[str, str]]
    unresolved_items: list[dict[str, Any]]
    lineage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": NB1_GRAPH_SCHEMA,
            "graph_id": self.graph_id,
            "graph_hash": self.graph_hash,
            "beats": self.beats,
            "edges": self.edges,
            "unresolved_items": self.unresolved_items,
            "lineage": self.lineage,
        }


def build_narrative_beat_graph(
    intent_text: str,
    *,
    units: list[Any] | None = None,
) -> NarrativeBeatGraph:
    """Deterministic NB-1: user clause beats + declared consequences +
    SI-1 unit binding (structured overlap only)."""
    units = list(units or [])
    clauses = [c.strip() for c in _CLAUSE_RE.split(intent_text) if c.strip()]
    beats: list[NarrativeBeat] = []
    order_index = 0
    # SI-1.1: seed the pronoun referent from the FIRST object named
    # anywhere in the request (e.g., "water bottle" in the intro clause,
    # which may itself produce no beat).
    last_object: str | None = _extract_object(intent_text)
    for clause in clauses:
        matches = _find_all_actions(clause)
        for position, (phrase, spec) in enumerate(matches):
            predicate = spec["predicate_id"]
            actor = _extract_actor(clause)
            obj = _extract_object(clause)
            # SI-1.1 pronoun resolution: "it" refers to the last named
            # object (e.g., "picks it up" -> bottle). Deterministic;
            # never guessed beyond the clause sequence.
            if obj is None and re.search(r"\bit\b", clause.lower()):
                obj = last_object
            elif obj is not None and re.search(r"\bit\b", clause.lower()) \
                    and last_object is not None:
                obj = last_object
            elif obj is None and predicate in ("DRINK", "APPLY") \
                    and last_object is not None:
                # vocabulary-grounded: DRINK/APPLY act on the held
                # container ("takes a drink" -> the bottle)
                obj = last_object
            unresolved: list[str] = []
            if actor is None:
                unresolved.append("actor")
            if obj is None:
                unresolved.append("object")
            beat_id = "beat_" + _sha(
                predicate + str(actor) + str(obj) + clause + str(position))[:16]
            beats.append(NarrativeBeat(
                beat_id=beat_id,
                origin="USER_EXPLICIT",
                display_name=predicate,
                predicate_id=predicate,
                source_span=clause,
                actor_ids=[actor] if actor else [],
                object_ids=[obj] if obj else [],
                intended_outcome=[],
                explicit_order_index=order_index,
                interaction_class=spec.get("interaction_class"),
                state_change_candidate=[],
                failure_families=list(spec.get("failure_families", [])),
                bound_si1_unit_ids=[],
                binding_kind="UNRESOLVED_BINDING",
                unresolved_fields=unresolved,
                lineage={"source_clause": clause, "vocab_entry": phrase},
            ))
            order_index += 1
            if obj is not None:
                last_object = obj
    # declared consequence beats (DERIVED, state-transition only)
    edges: list[dict[str, str]] = []
    user_beats = list(beats)
    for index, beat in enumerate(user_beats):
        parent_clause = beat.lineage["source_clause"]
        _, spec, _ = _find_action(parent_clause) or (None, {}, 0)
        for consequence in spec.get("consequences", []):
            consequence_id = consequence
            if consequence == "IMPACT" and "water" in parent_clause.lower():
                consequence_id = "WATER_IMPACT"
            consequence_beat_id = "beat_" + _sha(
                consequence_id + parent_clause + "derived")[:16]
            beats.append(NarrativeBeat(
                beat_id=consequence_beat_id,
                origin="DERIVED_PREREQUISITE",
                display_name=consequence_id,
                predicate_id=consequence_id,
                source_span=parent_clause,
                actor_ids=[],
                object_ids=[],
                intended_outcome=[],
                explicit_order_index=beat.explicit_order_index + 1,
                interaction_class="environment_contact",
                state_change_candidate=["state_transition"],
                failure_families=["FF-DEFORMATION", "FF-PHYSICS"],
                bound_si1_unit_ids=[],
                binding_kind="UNRESOLVED_BINDING",
                unresolved_fields=["actor", "object"],
                lineage={"derived_from_beat": beat.beat_id,
                         "vocab_consequence": consequence_id},
            ))
            edges.append({"from": beat.beat_id, "to": consequence_beat_id,
                          "kind": "STATE_TRANSITION"})
        if index > 0:
            edges.append({"from": user_beats[index - 1].beat_id,
                          "to": beat.beat_id, "kind": "USER_SEQUENCE"})
    # bind SI-1 units: best structured overlap, one beat per unit
    unit_failures = {
        u.unit_id: set((u.lineage or {}).get("si1_failure_family_ids", [])
                       or []) for u in units
    }
    beat_failures = {b.beat_id: set(b.failure_families) for b in beats}
    unbound_units: list[dict[str, Any]] = []
    for unit in units:
        uid = unit.unit_id
        best_beat = None
        best_overlap = -1
        for beat in beats:
            overlap = len(unit_failures.get(uid, set())
                          & beat_failures.get(beat.beat_id, set()))
            if overlap > best_overlap:
                best_overlap = overlap
                best_beat = beat
        if best_beat is None:
            unbound_units.append({"unit_id": uid,
                                  "kind": "SI1_UNIT_UNBOUND",
                                  "reason": "no narrative beats extracted"})
            continue
        if best_overlap > 0:
            best_beat.bound_si1_unit_ids = sorted(
                set(best_beat.bound_si1_unit_ids) | {uid})
            best_beat.binding_kind = "DIRECT_BINDING"
        else:
            unbound_units.append({
                "unit_id": uid,
                "kind": "SI1_UNIT_UNBOUND",
                "reason": "no failure-family overlap with any beat",
            })
    body = {
        "beats": [b.to_dict() for b in beats],
        "edges": sorted({(e["from"], e["to"], e["kind"]): e
                         for e in edges}.values(),
                        key=lambda e: (e["from"], e["to"], e["kind"])),
        "unresolved": [
            {"clause": c, "kind": "NO_ACTION_VOCABULARY"}
            for c in clauses if not _find_action(c)
        ] + unbound_units,
    }
    graph_hash = _sha(body)
    return NarrativeBeatGraph(
        graph_id="nbg_" + graph_hash[:16],
        graph_hash=graph_hash,
        beats=body["beats"],
        edges=body["edges"],
        unresolved_items=body["unresolved"],
        lineage={
            "intent_hash": _sha(intent_text),
            "clause_count": len(clauses),
            "action_vocabulary_size": len(NARRATIVE_ACTIONS),
        },
    )


def annotate_temporal_plan(plan: Any, graph: NarrativeBeatGraph
                           ) -> dict[str, Any]:
    """Additive NB-1 annotation: TD-1 schedule entries gain narrative
    beat references. TD-1 policy math and hashes are untouched."""
    annotated = plan.to_dict()
    beat_by_unit: dict[str, dict[str, str]] = {}
    for beat in graph.beats:
        for uid in beat["bound_si1_unit_ids"]:
            beat_by_unit[uid] = {
                "narrative_beat_id": beat["beat_id"],
                "narrative_beat_display": beat["display_name"],
                "narrative_beat_origin": beat["origin"],
            }
    for entry in annotated["atomic_unit_schedule"]:
        ref = beat_by_unit.get(entry["unit_id"])
        entry["narrative_beat_id"] = ref["narrative_beat_id"] if ref else None
        entry["narrative_beat_display"] = (ref["narrative_beat_display"]
                                           if ref else None)
    return annotated
