"""SI-1.1 — Manipulator / Actor Resource Constraint Closure.

Makes SI/NB planning conscious of finite actor manipulation resources
(hands), persistent occupancy, interaction preconditions, object
affordance/state, and required manipulation roles.

Root measured failure this closes: a UGC creator holds the phone with
one hand and the bottle with the other; during the drinking sequence
the bottle closure opened with no physically accounted manipulation —
the plan never reasoned about limb occupancy or closure state.

Frozen rules:
- Persistent occupancy: an occupied hand stays occupied until an
  explicit state transition releases/reassigns it.
- Never invent missing hands, releases, supports, or object mechanisms.
  Unknown closure mechanisms stay UNRESOLVED (never 'twist', 'flip',
  'pop', 'straw').
- Precondition dispositions are explicit: SATISFIED_ALREADY,
  SUPPORTED_ONE_HAND_REALIZATION, REQUIRES_RESOURCE_REASSIGNMENT,
  REQUIRES_SUPPORT_SURFACE, REQUIRES_ADDITIONAL_BEAT, UNRESOLVED.
- Resource conflicts produce explicit conflict records.
- No generic keyword routing; no prose-inferred anatomy.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

RESOURCE_SCHEMA = "cpcs.actor_resource_packet/0.1"

RESOURCE_STATES = frozenset({
    "AVAILABLE", "OCCUPIED", "GRASPING", "SUPPORTING", "CONTACTING",
    "TRANSITIONING",
})

PRECONDITION_DISPOSITIONS = frozenset({
    "SATISFIED_ALREADY", "SUPPORTED_ONE_HAND_REALIZATION",
    "REQUIRES_RESOURCE_REASSIGNMENT", "REQUIRES_SUPPORT_SURFACE",
    "REQUIRES_ADDITIONAL_BEAT", "UNRESOLVED",
})

# NB-1 predicate -> required manipulator roles (declared vocabulary;
# bimanual-ness comes from the mechanism, never guessed from prose)
BEAT_RESOURCE_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "PICK_UP": {"manipulators": 1, "roles": ["GRASP"],
                "object_state_effect": None},
    "DRINK": {"manipulators": 1, "roles": ["GRASP"],
              "preconditions": ["object_drinkable_state"],
              "object_state_effect": None},
    "OPEN": {"manipulators": None, "roles": ["GRASP", "COUNTERFORCE"],
             "preconditions": ["object_closure_mechanism_known"],
             "object_state_effect": "closure_open"},
    "APPRAISAL_DIALOGUE": {"manipulators": 0, "roles": []},
    "PRODUCT_REVEAL": {"manipulators": 1, "roles": ["GRASP"]},
    "APPLY": {"manipulators": 1, "roles": ["GRASP", "CONTACT"]},
    "ASSEMBLE": {"manipulators": 2, "roles": ["GRASP", "STABILIZING_MANIPULATOR"]},
    "SLICE": {"manipulators": 2,
              "roles": ["GRASP", "STABILIZING_MANIPULATOR"]},
    "UNBOX": {"manipulators": 2, "roles": ["GRASP", "STABILIZING_MANIPULATOR"],
              "preconditions": ["object_closure_mechanism_known"]},
    "CATCH": {"manipulators": 1, "roles": ["GRASP", "CONTACT"]},
    "SWING": {"manipulators": 1, "roles": ["GRASP"],
              "grip_persistence": "required_through_beat"},
    "RELEASE": {"manipulators": 1, "roles": ["CONTACT"],
                "object_state_effect": "grip_released"},
    "THROW": {"manipulators": 1, "roles": ["GRASP"],
              "object_state_effect": "grip_released"},
    "FALL": {"manipulators": 0, "roles": []},
    "LAND": {"manipulators": 0, "roles": ["SUPPORT"]},
    "RECOVERY": {"manipulators": 0, "roles": ["SUPPORT"]},
    "PRESSURE": {"manipulators": 0, "roles": ["CONTACT"]},
    "DIALOGUE_EXCHANGE": {"manipulators": 0, "roles": []},
    "APPRAISAL_RESPONSE": {"manipulators": 0, "roles": []},
}

# capture-device occupancy: which signal holds the phone hand
PHONE_HOLD_SIGNALS = (
    r"\bperformer_operated_phone\b",
    r"\bfilmed (?:it )?on (?:her |his )?phone\b",
    r"\bhandheld\b",
    r"\bphone camera\b",
    r"\brecords? (?:it )?(?:with|on) (?:her |his )?phone\b",
)


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass
class ActorResource:
    actor_id: str
    resource_id: str
    state: str
    assigned_role: str | None
    assigned_object: str | None
    since_beat: str | None
    lineage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "resource_id": self.resource_id,
            "state": self.state,
            "assigned_role": self.assigned_role,
            "assigned_object": self.assigned_object,
            "since_beat": self.since_beat,
            "lineage": self.lineage,
        }


@dataclass
class ResourceConstraintPacket:
    packet_id: str
    packet_hash: str
    actor_resources: list[dict[str, Any]]
    occupancy_ledger: list[dict[str, Any]]
    preconditions: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    lineage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": RESOURCE_SCHEMA,
            "packet_id": self.packet_id,
            "packet_hash": self.packet_hash,
            "actor_resources": self.actor_resources,
            "occupancy_ledger": self.occupancy_ledger,
            "preconditions": self.preconditions,
            "conflicts": self.conflicts,
            "lineage": self.lineage,
        }


def _has_phone_hold(intent_text: str) -> bool:
    return any(re.search(p, intent_text, re.IGNORECASE)
               for p in PHONE_HOLD_SIGNALS)


def build_resource_constraints(
    intent_text: str,
    beat_graph: Any,
    *,
    actor_ids: list[str] | None = None,
    object_tokens: list[str] | None = None,
) -> ResourceConstraintPacket:
    """Deterministic SI-1.1 resource closure over the NB-1 beat graph."""
    beats = list(getattr(beat_graph, "beats", []) or [])
    beats = sorted(beats, key=lambda b: (b.get("explicit_order_index", 0),
                                         b.get("beat_id", "")))
    # actor ids: from beats' actor fields; a capture device without any
    # declared actor is an unresolved performer (honest, not invented);
    # no beats + no capture device -> NO human resource graph at all.
    if not actor_ids:
        actor_ids = sorted({a for b in beats
                            for a in (b.get("actor_ids") or [])})
        if not actor_ids and _has_phone_hold(intent_text):
            actor_ids = ["unresolved_performer"]
    if not actor_ids:
        body_empty = {
            "resources": [], "ledger": [], "preconditions": [],
            "conflicts": [],
        }
        packet_hash = _sha(body_empty)
        return ResourceConstraintPacket(
            packet_id="res_" + packet_hash[:16],
            packet_hash=packet_hash,
            actor_resources=[],
            occupancy_ledger=[],
            preconditions=[],
            conflicts=[],
            lineage={"beat_count": len(beats), "phone_hold": False,
                     "actor_ids": [], "note": "no human resource graph "
                     "created (no declared actors, no capture device)"})
    # deterministic actor resolution: a beat's actor token resolves to a
    # declared actor id when it is a substring of the id ("she" in
    # "creator"? no) — instead, when exactly ONE actor is declared, all
    # beats with a matching pronoun token belong to that actor.
    single_actor = actor_ids[0] if len(actor_ids) == 1 else None
    pronoun_actor = None
    if single_actor and re.search(r"\b(she|he|her|his|the woman|the man|"
                                  r"the fighter|the chef|the person|"
                                  r"creator)\b", intent_text,
                                  re.IGNORECASE):
        pronoun_actor = single_actor
    resources: dict[str, ActorResource] = {}
    for actor in actor_ids:
        for hand in ("left_hand", "right_hand"):
            key = f"{actor}.{hand}"
            resources[key] = ActorResource(
                actor_id=actor, resource_id=hand, state="AVAILABLE",
                assigned_role=None, assigned_object=None, since_beat=None,
                lineage={"anatomy": "declared_bilateral_upper_limb"})
    occupancy_ledger: list[dict[str, Any]] = []
    preconditions: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    held: dict[str, str] = {}  # object -> resource key (persistent grip)

    # seed capture occupancy: the phone occupies exactly ONE hand; the
    # WHICH hand remains unresolved (never guessed)
    phone_hand: str | None = None
    if _has_phone_hold(intent_text):
        actor = actor_ids[0]
        phone_hand = f"{actor}.{resources[f'{actor}.left_hand'].resource_id}"
        resources[f"{actor}.left_hand"].state = "OCCUPIED"
        resources[f"{actor}.left_hand"].assigned_role = "phone_hold"
        resources[f"{actor}.left_hand"].assigned_object = "phone"
        resources[f"{actor}.left_hand"].since_beat = None
        occupancy_ledger.append({
            "resource": f"{actor}.left_hand",
            "role": "phone_hold", "object": "phone",
            "note": ("one hand persistently holds the capture device; "
                     "hand side declared-convention, which-hand UNRESOLVED"),
            "release_beat": None,
        })

    for beat in beats:
        display = beat.get("display_name") or beat.get("predicate_id", "")
        beat_id = beat.get("beat_id", "")
        spec = BEAT_RESOURCE_REQUIREMENTS.get(display) or {
            "manipulators": 0, "roles": []}
        object_id = (beat.get("object_ids") or [None])[0]
        beat_actor_ids = beat.get("actor_ids") or []
        if beat_actor_ids and beat_actor_ids[0] in (
                "she", "he", "her", "his", "woman", "man", "person",
                "performer", "actor", "actress", "fighter", "chef",
                "hands", "hand"):
            actor = pronoun_actor or beat_actor_ids[0]
        else:
            actor = (beat_actor_ids[0] if beat_actor_ids
                     else (pronoun_actor or actor_ids[0]))
        # precondition resolution
        for precondition in spec.get("preconditions", []) or []:
            if precondition == "object_drinkable_state":
                disposition = "UNRESOLVED"
                reason = ("closure mechanism unspecified; opening animation "
                          "must never be invented")
            elif precondition == "object_closure_mechanism_known":
                disposition = "UNRESOLVED"
                reason = "no structured closure evidence in the runtime"
            else:
                disposition = "UNRESOLVED"
                reason = "precondition source unknown"
            preconditions.append({
                "beat_id": beat_id,
                "display": display,
                "precondition": precondition,
                "object_id": object_id,
                "disposition": disposition,
                "reason": reason,
            })
        # release semantics first: RELEASE/THROW free the held grip
        # (the action IS the release; no new acquisition). When the
        # clause names no object, the actor's current held object is
        # released.
        if display in ("RELEASE", "THROW"):
            release_target = object_id
            if release_target not in held:
                candidates = [obj for obj, key in held.items()
                              if resources[key].actor_id == actor]
                release_target = candidates[0] if candidates else None
            if release_target in held:
                holder = held[release_target]
                resources[holder].state = "AVAILABLE"
                resources[holder].assigned_object = None
                resources[holder].assigned_role = None
                occupancy_ledger.append({
                    "resource": holder, "role": None,
                    "object": release_target,
                    "beat_id": beat_id, "release_beat": beat_id,
                    "note": "grip released at beat"})
                del held[release_target]
                continue
        # resource acquisition for this beat
        needed = spec.get("manipulators") or 0
        if needed == 0:
            continue
        free = [key for key, r in resources.items()
                if r.actor_id == actor and r.state == "AVAILABLE"]
        if object_id and object_id in held:
            # grip persists: reuse the holding hand
            holder = held[object_id]
            if needed <= 1:
                resources[holder].state = "GRASPING"
                resources[holder].assigned_object = object_id
                resources[holder].since_beat = beat_id
                occupancy_ledger.append({
                    "resource": holder, "role": "GRASP", "object": object_id,
                    "beat_id": beat_id, "release_beat": None,
                    "note": "persistent grip carries into this beat"})
                continue
        if needed > len(free):
            occupied = [k for k, r in resources.items()
                        if r.actor_id == actor and r.state != "AVAILABLE"]
            conflicts.append({
                "conflict_id": "conf_" + _sha(beat_id + str(needed))[:16],
                "beat_id": beat_id, "display": display,
                "required_manipulators": needed,
                "available_manipulators": len(free),
                "occupied_resources": occupied,
                "kind": "RESOURCE_CONFLICT",
                "resolution_options": ["REQUIRES_RESOURCE_REASSIGNMENT",
                                       "REQUIRES_SUPPORT_SURFACE",
                                       "REQUIRES_ADDITIONAL_BEAT"],
            })
            continue
        # acquire greedily (deterministic resource order)
        acquired = free[:needed]
        for key in acquired:
            resources[key].state = "GRASPING"
            resources[key].assigned_role = "GRASP"
            resources[key].assigned_object = object_id
            resources[key].since_beat = beat_id
            occupancy_ledger.append({
                "resource": key, "role": "GRASP", "object": object_id,
                "beat_id": beat_id, "release_beat": None,
                "note": "acquired at beat"})
        if object_id:
            held[object_id] = acquired[0]
    body = {
        "resources": [r.to_dict() for r in
                      sorted(resources.values(),
                             key=lambda r: (r.actor_id, r.resource_id))],
        "ledger": occupancy_ledger,
        "preconditions": preconditions,
        "conflicts": conflicts,
    }
    packet_hash = _sha(body)
    return ResourceConstraintPacket(
        packet_id="res_" + packet_hash[:16],
        packet_hash=packet_hash,
        actor_resources=body["resources"],
        occupancy_ledger=body["ledger"],
        preconditions=body["preconditions"],
        conflicts=body["conflicts"],
        lineage={
            "beat_count": len(beats),
            "phone_hold": _has_phone_hold(intent_text),
            "actor_ids": actor_ids,
        },
    )
