"""KA-2.2 — Knowledge placement: atomic decomposition + scope/lifetime.

Consumes KA-2 recruitment + the repo-native structured objects (interaction
payloads, events, temporal/causal relations) and answers:

    "Where exactly should this recruited knowledge influence the video?"

Distinct decisions, never collapsed:
  PASS 1: "What expertise could matter?"
  PASS 2: "What expertise actually matters?"
  DECOMPOSITION: "What concrete portions of the video does it apply to?"
  PLACEMENT: "Where should the resulting knowledge live?"
  SERIALIZATION: "How should the generation-facing model receive it?"

Reuses existing structured semantics: atomic units derive ONLY from typed
structured objects (interaction phases, events, causal edges) — never from
prose reconstruction (D4). Registry scope vocabulary (entity/shot/scene/
beat/phase/interval/global) is the scope anchor.

Nothing here emits prompt text; it produces structured placement decisions
and module groupings the presentation layer may serialize.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

PLACEMENT_SCHEMA = "cpcs.knowledge_placement/0.1"
UNIT_SCHEMA = "cpcs.atomic_unit/0.1"

SCOPE_VOCABULARY = frozenset({
    "GLOBAL", "SCENE", "SHOT", "BEAT", "INTERACTION", "PHASE", "ACTOR",
    "OBJECT", "ENVIRONMENT", "CAMERA_EVENT", "RECOVERY",
})
LIFETIME_VOCABULARY = frozenset({
    "PERSISTENT", "SCENE_LOCAL", "SHOT_LOCAL", "BEAT_LOCAL",
    "UNTIL_STATE_TRANSITION", "CONTACT_INTERVAL", "PHASE_LOCAL",
    "EVENT_ONCE", "RECOVERY_UNTIL_COMPLETE",
})
PLACEMENT_ROLES = frozenset({
    "REASONING_ONLY", "PLANNING", "GLOBAL_INVARIANT", "BEAT_DIRECTION",
    "INTERACTION_MECHANICS", "PERFORMANCE_DIRECTION", "OBJECT_STATE",
    "ENVIRONMENT_RESPONSE", "CAMERA_DIRECTION", "RECOVERY",
    "VERIFICATION", "NEGATIVE_CONSTRAINT",
})
EMISSION_POLICIES = frozenset({
    "NO_EMIT_REASONING_ONLY", "NO_EMIT_VERIFICATION_ONLY", "EMIT_GLOBAL",
    "EMIT_SCOPED_MODULE", "EMIT_STRUCTURED_CARRIER_ONLY",
    "EMIT_PROVIDER_IF_SUPPORTED",
})

# principle-family / failure-family -> scope + role + lifetime (deterministic)
FAMILY_PLACEMENT = {
    "support_contact_chain": ("INTERACTION", "INTERACTION_MECHANICS",
                              "CONTACT_INTERVAL"),
    "support_state_chain": ("INTERACTION", "INTERACTION_MECHANICS",
                            "PHASE_LOCAL"),
    "rotation_axis_discipline": ("INTERACTION", "INTERACTION_MECHANICS",
                                 "PHASE_LOCAL"),
    "identity_continuity": ("GLOBAL", "GLOBAL_INVARIANT", "PERSISTENT"),
    "visibility_continuity": ("GLOBAL", "GLOBAL_INVARIANT", "PERSISTENT"),
    "deformation_control": ("INTERACTION", "ENVIRONMENT_RESPONSE",
                            "EVENT_ONCE"),
    "safety_constraint": ("INTERACTION", "NEGATIVE_CONSTRAINT",
                          "CONTACT_INTERVAL"),
    "protected_invariant": ("GLOBAL", "GLOBAL_INVARIANT", "PERSISTENT"),
    "mechanism_binding": ("INTERACTION", "INTERACTION_MECHANICS",
                          "UNTIL_STATE_TRANSITION"),
    "grounded_principle": ("GLOBAL", "PLANNING", "SCENE_LOCAL"),
    "failure_prevention": ("GLOBAL", "VERIFICATION", "SCENE_LOCAL"),
    "evidence_binding": ("GLOBAL", "REASONING_ONLY", "SCENE_LOCAL"),
}

# expertise doc families that bind to performance moments
PERFORMANCE_DOC_IDS = frozenset({
    "02_facs_laban_bartenieff_gap_closure_completed",
    "cpcs_facs_laban_ai_video_directorial_control_research_paper",
    "behavior_layer",
    "cpcs_reference_living_performance_realism",
    "cpcs_reference_natural_dialogue_mode",
})
ENVIRONMENT_DOC_IDS = frozenset({
    "03_mx_hierarchical_motion_grammar_gap_closure_research",
    "granular_motion_control_for_ai_video_generation",
})


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass
class AtomicUnit:
    unit_id: str
    unit_kind: str
    scope: str
    interaction_id: str | None
    actor_refs: list[str]
    object_refs: list[str]
    state_transitions: dict[str, Any]
    ordered_after: list[str]
    lineage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": UNIT_SCHEMA,
            "unit_id": self.unit_id,
            "unit_kind": self.unit_kind,
            "scope": self.scope,
            "interaction_id": self.interaction_id,
            "actor_refs": self.actor_refs,
            "object_refs": self.object_refs,
            "state_transitions": self.state_transitions,
            "ordered_after": self.ordered_after,
            "lineage": self.lineage,
        }


def decompose_atomic_units(structured_objects: list[dict[str, Any]]
                           ) -> list[AtomicUnit]:
    """Adaptive decomposition from typed structured objects ONLY.

    Each interaction phase becomes one INTERACTION_PHASE unit; each event
    becomes one EVENT unit; the global unit always exists. Causal edges
    order units (cause before effect). Nothing is reconstructed from prose.
    """
    units: list[AtomicUnit] = []
    ordered_after: list[tuple[str, str]] = []
    interactions = [o for o in structured_objects
                    if o.get("target") == "interactions[]"]
    events = [o for o in structured_objects if o.get("target") == "beats[]"]
    for obj in interactions:
        value = obj.get("value") or {}
        interaction_id = value.get("interaction_id")
        roles = value.get("roles") or {}
        actor_refs = sorted({v for k, v in roles.items()
                             if k in ("attacker", "defender", "initiative")
                             and isinstance(v, str)})
        phases = value.get("phases") or []
        previous: str | None = None
        for index, phase in enumerate(phases):
            state_transitions = {k: phase.get(k) for k in
                                 ("support_shift", "com_displacement",
                                  "grip_persists", "support_lost")
                                 if phase.get(k) is not None}
            unit_id = f"{interaction_id}:phase_{index}:{phase.get('action')}"
            units.append(AtomicUnit(
                unit_id=unit_id,
                unit_kind="INTERACTION_PHASE",
                scope="PHASE",
                interaction_id=interaction_id,
                actor_refs=actor_refs,
                object_refs=[],
                state_transitions=state_transitions,
                ordered_after=[previous] if previous else [],
                lineage={"source": "structured_interaction_phases"},
            ))
            if previous:
                ordered_after.append((previous, unit_id))
            previous = unit_id
    for obj in events:
        value = obj.get("value") or {}
        unit_id = value.get("event_id") or ("event_" + _sha(json.dumps(
            value, sort_keys=True, default=str))[:16])
        units.append(AtomicUnit(
            unit_id=unit_id,
            unit_kind="EVENT",
            scope="BEAT",
            interaction_id=None,
            actor_refs=[],
            object_refs=[],
            state_transitions={},
            ordered_after=[],
            lineage={"source": "structured_event"},
        ))
    for rel in structured_objects:
        if rel.get("target") not in (
                "continuity.cpcs_causal_edges[]",
                "continuity.cpcs_temporal_relations[]"):
            continue
        value = rel.get("value") or {}
        cause = value.get("cause") or value.get("before")
        effect = value.get("effect") or value.get("after")
        if cause and effect:
            ordered_after.append((cause, effect))
    # second pass: attach causal ordering for unit ids that match
    for before, after in ordered_after:
        for unit in units:
            if unit.unit_id == after and before not in unit.ordered_after:
                unit.ordered_after.append(before)
    units.sort(key=lambda u: u.unit_id)
    return units


@dataclass
class KnowledgePlacementDecision:
    region_id: str
    target_scope: str
    target_unit_ids: list[str]
    lifetime: str
    placement_role: str
    emission_policy: str
    reason_codes: list[str]
    disposition: str
    decision_hash: str = ""
    lineage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PLACEMENT_SCHEMA,
            "region_id": self.region_id,
            "target_scope": self.target_scope,
            "target_unit_ids": self.target_unit_ids,
            "lifetime": self.lifetime,
            "placement_role": self.placement_role,
            "emission_policy": self.emission_policy,
            "reason_codes": self.reason_codes,
            "disposition": self.disposition,
            "decision_hash": self.decision_hash,
            "lineage": self.lineage,
        }


def _unit_scope_for_family(family: str) -> tuple[str, str, str]:
    return FAMILY_PLACEMENT.get(family, ("GLOBAL", "REASONING_ONLY",
                                         "SCENE_LOCAL"))


def build_placement(
    recruitment: dict[str, Any],
    constellation: Any,
    units: list[AtomicUnit],
    *,
    pack_lookup: dict[str, dict[str, Any]] | None = None,
) -> list[KnowledgePlacementDecision]:
    """Bind each recruited/context region to scope + lifetime + emission.

    Only RECRUIT and CONTEXT regions receive scoped bindings; ARCHIVE and
    UNRESOLVED regions stay reasoning-only. Deterministic.
    """
    pack_lookup = pack_lookup or {}
    regions = list(getattr(constellation, "regions", []) or [])
    region_by_id: dict[str, dict[str, Any]] = {}
    for r in regions:
        d = r if isinstance(r, dict) and "region_id" in r else \
            (r.to_dict() if hasattr(r, "to_dict") else r)
        region_by_id[d["region_id"]] = d
    disposition_by_id = {d["region_id"]: d for d in
                         recruitment.get("dispositions", []) or []}
    unit_by_id = {u.unit_id: u for u in units}
    decisions: list[KnowledgePlacementDecision] = []
    for region_id in sorted(region_by_id):
        region = region_by_id[region_id]
        disp = disposition_by_id.get(region_id, {})
        disposition = disp.get("disposition", "ARCHIVE")
        families = region.get("principle_families", []) or []
        docs = set(region.get("corpus_doc_ids", []) or [])
        interaction_units = [u for u in units
                             if u.unit_kind == "INTERACTION_PHASE"]
        target_scope, role, lifetime = (
            "GLOBAL", "REASONING_ONLY", "SCENE_LOCAL")
        reasons: list[str] = []
        if disposition != "RECRUIT":
            # CONTEXT/ARCHIVE/UNRESOLVED knowledge influences reasoning
            # without becoming emitted text.
            reasons.append(f"disposition_{disposition.lower()}_reasoning_only")
            emission = "NO_EMIT_REASONING_ONLY"
        else:
            chosen_family = None
            for family in families:
                if family in FAMILY_PLACEMENT:
                    chosen_family = family
                    break
            bound_failures = set(
                (disp or {}).get("bound_failure_family_ids", []) or [])
            if docs & PERFORMANCE_DOC_IDS and not any(
                    families and f in ("identity_continuity",
                                       "visibility_continuity",
                                       "protected_invariant")
                    for f in families):
                # Consequence-resolved role: performance doc regions bound
                # to camera/capture failures are capture-realism regions
                # (e.g., a drone shot), not human-performance direction.
                if bound_failures & {"FF-PERFORMANCE", "FF-TIMING"}:
                    target_scope, role, lifetime = (
                        "BEAT", "PERFORMANCE_DIRECTION", "BEAT_LOCAL")
                    reasons.append("performance_doc_bound")
                elif bound_failures & {"FF-CAMERA", "FF-CAPTURE"}:
                    target_scope, role, lifetime = (
                        "SHOT", "CAMERA_DIRECTION", "SHOT_LOCAL")
                    reasons.append("capture_doc_bound")
                else:
                    target_scope, role, lifetime = (
                        "BEAT", "PERFORMANCE_DIRECTION", "BEAT_LOCAL")
                    reasons.append("performance_doc_bound")
            elif docs & ENVIRONMENT_DOC_IDS and interaction_units:
                target_scope, role, lifetime = (
                    "INTERACTION", "ENVIRONMENT_RESPONSE", "EVENT_ONCE")
                reasons.append("environment_doc_bound")
            elif chosen_family:
                target_scope, role, lifetime = _unit_scope_for_family(
                    chosen_family)
                reasons.append(f"family_{chosen_family}")
            else:
                reasons.append("global_default")
        target_units: list[str] = []
        if target_scope in ("INTERACTION", "PHASE", "BEAT") \
                and interaction_units:
            target_units = [u.unit_id for u in interaction_units]
        if role == "RECOVERY" or any(
                u.state_transitions for u in interaction_units
                if u.state_transitions.get("support_lost") is True):
            recovery_units = [u.unit_id for u in interaction_units
                              if u.state_transitions.get("support_lost") is True]
            if recovery_units and role != "GLOBAL_INVARIANT":
                target_units = recovery_units
                role, lifetime = "RECOVERY", "RECOVERY_UNTIL_COMPLETE"
                reasons.append("recovery_bound")
        emission = "EMIT_SCOPED_MODULE" if target_units else \
            ("EMIT_GLOBAL" if role == "GLOBAL_INVARIANT"
             else "NO_EMIT_REASONING_ONLY")
        decision = KnowledgePlacementDecision(
            region_id=region_id,
            target_scope=target_scope,
            target_unit_ids=target_units,
            lifetime=lifetime,
            placement_role=role,
            emission_policy=emission,
            reason_codes=sorted(set(reasons)),
            disposition=disposition,
            lineage={
                "constellation_id": getattr(constellation, "constellation_id",
                                            "unknown"),
                "region_hash": region.get("region_hash", "unknown"),
            },
        )
        decision.decision_hash = _sha(
            {k: v for k, v in decision.to_dict().items()
             if k != "decision_hash"})
        decisions.append(decision)
    return decisions


def assemble_directing_modules(
    placement: list[KnowledgePlacementDecision],
    units: list[AtomicUnit],
    refinement: dict[str, Any],
    *,
    pack_lookup: dict[str, dict[str, Any]] | None = None,
    constellation: Any = None,
) -> dict[str, Any]:
    """Group placement decisions into global vs scoped module structure.

    Output is structured IDs + bindings only (no prose). This is the
    presentation input; it does NOT serialize carrier text."""
    global_entries: list[dict[str, Any]] = []
    scoped_entries: list[dict[str, Any]] = []
    reasoning_only: list[str] = []
    verification_only: list[str] = []
    for decision in placement:
        if decision.emission_policy == "NO_EMIT_VERIFICATION_ONLY":
            verification_only.append(decision.region_id)
            continue
        if decision.emission_policy == "NO_EMIT_REASONING_ONLY":
            reasoning_only.append(decision.region_id)
            continue
        entry = {
            "region_id": decision.region_id,
            "placement_role": decision.placement_role,
            "lifetime": decision.lifetime,
            "target_unit_ids": decision.target_unit_ids,
            "disposition": decision.disposition,
            "decision_hash": decision.decision_hash,
        }
        if decision.target_scope == "GLOBAL":
            global_entries.append(entry)
        else:
            scoped_entries.append(entry)
    return {
        "schema": "cpcs.directing_modules/0.1",
        "global_requirements": sorted(
            global_entries, key=lambda e: e["region_id"]),
        "beat_modules": sorted(
            scoped_entries, key=lambda e: (e["target_unit_ids"], e["region_id"])),
        "reasoning_only_region_ids": sorted(reasoning_only),
        "verification_only_region_ids": sorted(verification_only),
        "counts": {
            "global_emit_count": len(global_entries),
            "scoped_emit_count": len(scoped_entries),
            "reasoning_only_count": len(reasoning_only),
            "verification_only_count": len(verification_only),
            "atomic_unit_count": len(units),
        },
    }
