"""TC-1 — CPCS typed knowledge coverage expansion.

Layered on the existing permissive canonical collections (entities,
interactions, beats, continuity, camera, performance, style, editing,
provider_neutral_controls, verification_requirements). No schema
migration: the registry is the authoritative typed contract.

D4 remains enforced: evidence is referenced by ID only; prose is never
admitted as a canonical value; prose-only controls surface under
unsupported_mappings with full lineage.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lab.compiler.profiles import REPO_ROOT

REGISTRY_VERSION = "cpcs-reasoning-path-registry/v0.1"

# Source-native structured value enums (from frozen CPCS artifacts; values are
# canonical, not reconstructed from prose):
#   ug008 contact states: candidate | active | occluded_active | released |
#                         contradicted | unknown
#   02f__continuity_states: visible | partially_visible | occluded | out_of_view
#   continuous_combat con06 ownership: transfer | retain
SOURCE_VALUE_ENUMS = {
    "contact_state_transition": ["candidate", "active", "occluded_active",
                                 "released", "contradicted", "unknown"],
    "visibility_state": ["visible", "partially_visible", "occluded", "out_of_view"],
    "possession_transition": ["transfer", "retain", "unknown"],
}

# ---------------------------------------------------------------------------
# Typed path registry: CPCS semantic family -> repo-native structured target
# ---------------------------------------------------------------------------
# Each entry: path_id, semantic_family, semantic_kind, canonical_target,
# value_schema (structured constructor name), scope_types, target_types,
# merge_operator, source_control_types, source_requirement_classes,
# source_concept_ids, allowed_evidence_classes, forbidden_coercions,
# verification_counterpart, provider_neutral, provenance_requirements.
REGISTRY: dict[str, dict[str, Any]] = {
    # --- entity / world state ---
    "cpcs.entity_state.identity": {
        "path_id": "cpcs.entity_state.identity",
        "semantic_family": "identity_state",
        "semantic_kind": "STATE",
        "canonical_target": "entities[]",
        "value_schema": "cpcs.entity_state/1.0",
        "scope_types": ["entity", "shot", "scene"],
        "target_types": ["actor", "object"],
        "merge_operator": "structured_merge_by_entity_id",
        "source_control_types": ["CT-ROLE-LABELS", "Identity"],
        "source_requirement_classes": ["DIM-IDENTITY"],
        "source_concept_ids": ["identity continuity"],
        "allowed_evidence_classes": ["entity identity evidence"],
        "forbidden_coercions": ["flat_text", "scalar_bool"],
        "verification_counterpart": "cpcs.expected_state.identity",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids", "epistemic_status"],
    },
    "cpcs.entity_state.possession": {
        "path_id": "cpcs.entity_state.possession",
        "semantic_family": "possession",
        "semantic_kind": "STATE",
        "canonical_target": "entities[]",
        "value_schema": "cpcs.entity_state/1.0",
        "scope_types": ["entity", "shot", "scene"],
        "target_types": ["actor", "object"],
        "merge_operator": "structured_merge_by_entity_id",
        "source_control_types": ["CT-ROLE-LABELS", "Possession"],
        "source_requirement_classes": ["DIM-OWNERSHIP"],
        "source_concept_ids": ["possession", "ownership"],
        "allowed_evidence_classes": ["possession evidence"],
        "forbidden_coercions": ["flat_text", "ownership_as_contact"],
        "verification_counterpart": "cpcs.expected_state.possession",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    "cpcs.entity_state.ownership": {
        "path_id": "cpcs.entity_state.ownership",
        "semantic_family": "ownership",
        "semantic_kind": "STATE",
        "canonical_target": "entities[]",
        "value_schema": "cpcs.entity_state/1.0",
        "scope_types": ["entity", "shot", "scene"],
        "target_types": ["actor", "object"],
        "merge_operator": "structured_merge_by_entity_id",
        "source_control_types": ["Ownership"],
        "source_requirement_classes": ["DIM-OWNERSHIP"],
        "source_concept_ids": ["ownership"],
        "allowed_evidence_classes": ["ownership evidence"],
        "forbidden_coercions": ["flat_text", "possession_collapse"],
        "verification_counterpart": "cpcs.expected_state.ownership",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    "cpcs.entity_state.support": {
        "path_id": "cpcs.entity_state.support",
        "semantic_family": "support_state",
        "semantic_kind": "STATE",
        "canonical_target": "entities[]",
        "value_schema": "cpcs.entity_state/1.0",
        "scope_types": ["entity", "shot"],
        "target_types": ["actor"],
        "merge_operator": "structured_merge_by_entity_id",
        "source_control_types": ["CT-POSITIVE-INVARIANTS", "Support"],
        "source_requirement_classes": ["DIM-SUPPORT"],
        "source_concept_ids": ["support"],
        "allowed_evidence_classes": ["support state evidence"],
        "forbidden_coercions": ["flat_text", "support_as_balance"],
        "verification_counterpart": "cpcs.expected_state.support",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    "cpcs.entity_state.balance": {
        "path_id": "cpcs.entity_state.balance",
        "semantic_family": "balance",
        "semantic_kind": "STATE",
        "canonical_target": "entities[]",
        "value_schema": "cpcs.entity_state/1.0",
        "scope_types": ["entity", "shot"],
        "target_types": ["actor"],
        "merge_operator": "structured_merge_by_entity_id",
        "source_control_types": ["Balance"],
        "source_requirement_classes": ["DIM-SUPPORT"],
        "source_concept_ids": ["balance"],
        "allowed_evidence_classes": ["balance evidence"],
        "forbidden_coercions": ["flat_text", "balance_as_support"],
        "verification_counterpart": "cpcs.expected_state.balance",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    "cpcs.entity_state.orientation": {
        "path_id": "cpcs.entity_state.orientation",
        "semantic_family": "orientation",
        "semantic_kind": "STATE",
        "canonical_target": "entities[]",
        "value_schema": "cpcs.entity_state/1.0",
        "scope_types": ["entity", "shot", "scene"],
        "target_types": ["actor", "object"],
        "merge_operator": "structured_merge_by_entity_id",
        "source_control_types": ["Orientation"],
        "source_requirement_classes": ["DIM-ORIENTATION"],
        "source_concept_ids": ["orientation"],
        "allowed_evidence_classes": ["orientation evidence"],
        "forbidden_coercions": ["flat_text"],
        "verification_counterpart": "cpcs.expected_state.orientation",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    "cpcs.entity_state.visibility": {
        "path_id": "cpcs.entity_state.visibility",
        "semantic_family": "visibility",
        "semantic_kind": "STATE",
        "canonical_target": "entities[]",
        "value_schema": "cpcs.entity_state/1.0",
        "scope_types": ["entity", "shot"],
        "target_types": ["actor", "object"],
        "merge_operator": "structured_merge_by_entity_id",
        "source_control_types": ["Visibility"],
        "source_requirement_classes": ["DIM-VISIBILITY"],
        "source_concept_ids": ["visibility"],
        "allowed_evidence_classes": ["visibility evidence"],
        "forbidden_coercions": ["flat_text", "visibility_as_persistence"],
        "verification_counterpart": "cpcs.expected_state.visibility",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    "cpcs.entity_state.occlusion": {
        "path_id": "cpcs.entity_state.occlusion",
        "semantic_family": "occlusion",
        "semantic_kind": "STATE",
        "canonical_target": "entities[]",
        "value_schema": "cpcs.entity_state/1.0",
        "scope_types": ["entity", "shot"],
        "target_types": ["actor", "object"],
        "merge_operator": "structured_merge_by_entity_id",
        "source_control_types": ["OcclusionInterval", "VisibilityConstraint"],
        "source_requirement_classes": ["DIM-VISIBILITY"],
        "source_concept_ids": ["OcclusionInterval"],
        "allowed_evidence_classes": ["occlusion evidence"],
        "forbidden_coercions": ["flat_text", "occlusion_as_absence"],
        "verification_counterpart": "cpcs.expected_state.occlusion",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    # --- interaction / contact ---
    "cpcs.interaction.contact": {
        "path_id": "cpcs.interaction.contact",
        "semantic_family": "contact",
        "semantic_kind": "RELATION",
        "canonical_target": "interactions[]",
        "value_schema": "cpcs.interaction/1.0",
        "scope_types": ["shot", "beat", "phase", "interval"],
        "target_types": ["actor", "object"],
        "merge_operator": "structured_merge_by_interaction_id",
        "source_control_types": ["CT-CONTACT-CONTRACT", "CT-GRIP-TAXONOMY",
                                "Contact", "ContactStateMachine"],
        "source_requirement_classes": ["DIM-CONTACT", "DIM-COORDINATION"],
        "source_concept_ids": ["Contact", "ContactMode", "ContactStateMachine"],
        "allowed_evidence_classes": ["contact evidence"],
        "forbidden_coercions": ["flat_text", "contact_as_global_scalar"],
        "verification_counterpart": "cpcs.expected_state.contact",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    "cpcs.interaction.coordination": {
        "path_id": "cpcs.interaction.coordination",
        "semantic_family": "interaction_coupling",
        "semantic_kind": "RELATION",
        "canonical_target": "interactions[]",
        "value_schema": "cpcs.interaction/1.0",
        "scope_types": ["shot", "beat", "phase"],
        "target_types": ["actor"],
        "merge_operator": "structured_merge_by_interaction_id",
        "source_control_types": ["CoordinationPattern", "InteractionCoupling"],
        "source_requirement_classes": ["DIM-COORDINATION"],
        "source_concept_ids": ["InteractionRoles", "RelativeMotion", "RelativePhase"],
        "allowed_evidence_classes": ["coordination evidence"],
        "forbidden_coercions": ["flat_text"],
        "verification_counterpart": "cpcs.expected_state.coordination",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    # --- events ---
    "cpcs.event.action": {
        "path_id": "cpcs.event.action",
        "semantic_family": "action_event",
        "semantic_kind": "EVENT",
        "canonical_target": "beats[]",
        "value_schema": "cpcs.event/1.0",
        "scope_types": ["beat", "shot"],
        "target_types": ["actor", "object", "camera"],
        "merge_operator": "structured_merge_by_event_id",
        "source_control_types": ["ActionTemplate", "ActionBranch"],
        "source_requirement_classes": ["DIM-STATE", "DIM-TRANSITION"],
        "source_concept_ids": ["Phase", "MotionPhase", "ActionPhase"],
        "allowed_evidence_classes": ["action evidence"],
        "forbidden_coercions": ["flat_text"],
        "verification_counterpart": "cpcs.expected_state.event",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    # --- temporal / causal ---
    "cpcs.continuity.temporal_relation": {
        "path_id": "cpcs.continuity.temporal_relation",
        "semantic_family": "temporal_order",
        "semantic_kind": "TEMPORAL",
        "canonical_target": "continuity.cpcs_temporal_relations[]",
        "value_schema": "cpcs.temporal_relation/1.0",
        "scope_types": ["shot", "phase", "interval"],
        "target_types": ["event"],
        "merge_operator": "append_with_deterministic_id",
        "source_control_types": ["TemporalCoupling", "CT-BEAT-STRUCTURE",
                                "TimeSynchronization", "TimingProfile"],
        "source_requirement_classes": ["DIM-TIMING"],
        "source_concept_ids": ["TimingProfile"],
        "allowed_evidence_classes": ["temporal evidence"],
        "forbidden_coercions": ["flat_text", "chronology_as_causality"],
        "verification_counterpart": "cpcs.expected_state.temporal_order",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    "cpcs.continuity.causal_edge": {
        "path_id": "cpcs.continuity.causal_edge",
        "semantic_family": "causal_dependency",
        "semantic_kind": "CAUSAL",
        "canonical_target": "continuity.cpcs_causal_edges[]",
        "value_schema": "cpcs.causal_edge/1.0",
        "scope_types": ["shot", "phase", "interval"],
        "target_types": ["event", "state"],
        "merge_operator": "append_with_deterministic_id",
        "source_control_types": ["CausalEdge", "Causality"],
        "source_requirement_classes": ["DIM-CAUSALITY"],
        "source_concept_ids": ["causality"],
        "allowed_evidence_classes": ["causal evidence"],
        "forbidden_coercions": ["flat_text", "causality_as_chronology"],
        "verification_counterpart": "cpcs.expected_state.causal_result",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    # --- continuity / invariants ---
    "cpcs.continuity.invariant": {
        "path_id": "cpcs.continuity.invariant",
        "semantic_family": "continuity_invariant",
        "semantic_kind": "INVARIANT",
        "canonical_target": "continuity.cpcs_invariants[]",
        "value_schema": "cpcs.continuity_invariant/1.0",
        "scope_types": ["scene", "shot", "phase", "transition", "interval"],
        "target_types": ["actor", "object", "camera", "relationship"],
        "merge_operator": "append_with_deterministic_id",
        "source_control_types": ["CT-CONTINUITY-LOCKS", "CT-POSITIVE-INVARIANTS",
                                "PersistenceConstraint", "ContinuityState",
                                "Identity", "ContactIdentity", "CameraAxis"],
        "source_requirement_classes": ["DIM-PERSISTENCE", "DIM-CONTINUITY",
                                       "DIM-IDENTITY", "DIM-CAMERA"],
        "source_concept_ids": ["ContinuityState", "PersistenceConstraint",
                               "identity continuity", "physics continuity"],
        "allowed_evidence_classes": ["continuity evidence"],
        "forbidden_coercions": ["flat_text", "identity_as_physics"],
        "verification_counterpart": "cpcs.expected_state.persistence",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    # --- constraints (negative) ---
    "cpcs.constraint.negative": {
        "path_id": "cpcs.constraint.negative",
        "semantic_family": "negative_constraint",
        "semantic_kind": "CONSTRAINT",
        "canonical_target": "continuity.cpcs_constraints[]",
        "value_schema": "cpcs.constraint/1.0",
        "scope_types": ["global", "phase", "event", "transition"],
        "target_types": ["state", "event", "transition"],
        "merge_operator": "append_with_deterministic_id",
        "source_control_types": ["CT-NEGATIVE-CONSTRAINTS",
                                 "CT-PHASE-LOCAL-PROHIBITIONS",
                                 "NegativeConstraint", "forbidden_state",
                                 "ForbiddenGeneration"],
        "source_requirement_classes": ["DIM-STATE", "DIM-VISIBILITY"],
        "source_concept_ids": ["negative constraints"],
        "allowed_evidence_classes": ["negative constraint evidence"],
        "forbidden_coercions": ["flat_text", "generic_negative_prompt"],
        "verification_counterpart": "cpcs.expected_state.non_occurrence",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    # --- camera ---
    "cpcs.camera.subject_visibility": {
        "path_id": "cpcs.camera.subject_visibility",
        "semantic_family": "camera_subject_relation",
        "semantic_kind": "INVARIANT",
        "canonical_target": "camera.cpcs_subject_visibility[]",
        "value_schema": "cpcs.camera_subject_relation/1.0",
        "scope_types": ["shot", "phase"],
        "target_types": ["camera", "actor", "interaction"],
        "merge_operator": "append_with_deterministic_id",
        "source_control_types": ["CT-CAMERA-CONTRACT", "CameraSubjectRelation"],
        "source_requirement_classes": ["DIM-CAMERA", "DIM-VISIBILITY"],
        "source_concept_ids": ["camera"],
        "allowed_evidence_classes": ["camera evidence"],
        "forbidden_coercions": ["flat_text"],
        "verification_counterpart": "cpcs.expected_state.camera_visibility",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    # --- performance ---
    "cpcs.performance.effort": {
        "path_id": "cpcs.performance.effort",
        "semantic_family": "performance_effort",
        "semantic_kind": "STATE",
        "canonical_target": "performance.cpcs_performance_events[]",
        "value_schema": "cpcs.performance_event/1.0",
        "scope_types": ["beat", "shot"],
        "target_types": ["actor"],
        "merge_operator": "append_with_deterministic_id",
        "source_control_types": ["PerformanceExpressionEvent", "Effort"],
        "source_requirement_classes": ["DIM-EPISTEMICS"],
        "source_concept_ids": ["Effort (expressive)"],
        "allowed_evidence_classes": ["performance evidence"],
        "forbidden_coercions": ["flat_text", "effort_as_force"],
        "verification_counterpart": "cpcs.expected_state.performance",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids",
                                    "epistemic_status"],
    },
    # --- style ---
    "cpcs.style.invariant": {
        "path_id": "cpcs.style.invariant",
        "semantic_family": "style_invariant",
        "semantic_kind": "INVARIANT",
        "canonical_target": "style.cpcs_style_invariants[]",
        "value_schema": "cpcs.style_invariant/1.0",
        "scope_types": ["scene", "shot"],
        "target_types": ["style"],
        "merge_operator": "append_with_deterministic_id",
        "source_control_types": ["StyleTransformVector", "StyleInvariant"],
        "source_requirement_classes": ["DIM-STYLE"],
        "source_concept_ids": ["style"],
        "allowed_evidence_classes": ["style evidence"],
        "forbidden_coercions": ["flat_text", "style_overrides_physics"],
        "verification_counterpart": "cpcs.expected_state.style",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
    # --- editing ---
    "cpcs.editing.continuity": {
        "path_id": "cpcs.editing.continuity",
        "semantic_family": "editing_continuity",
        "semantic_kind": "INVARIANT",
        "canonical_target": "editing.cpcs_editing_continuity[]",
        "value_schema": "cpcs.editing_continuity/1.0",
        "scope_types": ["transition"],
        "target_types": ["shot"],
        "merge_operator": "append_with_deterministic_id",
        "source_control_types": ["EditingCut", "CutPreservesState"],
        "source_requirement_classes": ["DIM-CONTINUITY"],
        "source_concept_ids": ["editing"],
        "allowed_evidence_classes": ["editing evidence"],
        "forbidden_coercions": ["flat_text"],
        "verification_counterpart": "cpcs.expected_state.cut_continuity",
        "provider_neutral": True,
        "provenance_requirements": ["requirement_ids", "evidence_ids"],
    },
}

# control_type / rule-name -> registry path_id (deterministic admission gate)
CONTROL_TYPE_TO_PATH: dict[str, str] = {}
for _pid, _entry in REGISTRY.items():
    for _ct in _entry["source_control_types"]:
        CONTROL_TYPE_TO_PATH.setdefault(_ct, _pid)
# Explicit overrides for canonical control types shared across multiple
# families (deterministic precedence: general control semantics win over
# family-specific membership). Recorded in mapping receipts.
CONTROL_TYPE_TO_PATH.update({
    "CT-POSITIVE-INVARIANTS": "cpcs.continuity.invariant",
    "CT-ROLE-LABELS": "cpcs.entity_state.identity",
    "CONTROL_SELECTION_RULE": "cpcs.continuity.invariant",
    "HARD_OR_SOFT_CONTROL": "cpcs.continuity.invariant",
    "PREVENTIVE_CONTROL_AND_VERIFICATION": "cpcs.continuity.invariant",
    "PROTECTION_REQUIREMENT": "cpcs.continuity.invariant",
    "CT-FIRST-FRAME-LOCK": "cpcs.continuity.invariant",
    "CT-END-FRAME-GOAL": "cpcs.event.action",
    "CT-FIRST-LAST-FRAMES": "cpcs.continuity.invariant",
    "CT-MOTION-DELTA": "cpcs.event.action",
    "CT-REFERENCE-STILL": "cpcs.entity_state.identity",
    "CT-CAPTURE-BLOCK": "cpcs.style.invariant",
    "CT-DELIVERY-PLAN": "cpcs.event.action",
    "EXECUTION_SEQUENCE_CANDIDATE": "cpcs.event.action",
    "USER_NEGATIVE": "cpcs.constraint.negative",
    "REPAIR_EVIDENCE": "cpcs.continuity.invariant",
    "INVARIANT": "cpcs.continuity.invariant",
    "NEGATIVE_CONSTRAINT": "cpcs.constraint.negative",
})


def _sid(*parts: str) -> str:
    return "cpcs_" + hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]


# ---------------------------------------------------------------------------
# Structured object constructors (deterministic, idempotent, lineage-bearing)
# ---------------------------------------------------------------------------
@dataclass
class StructuredObject:
    schema: str
    target: str
    value: dict[str, Any]


def _lineage(control: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_ids": sorted(set(control.get("source_requirement_ids", []))),
        "evidence_ids": sorted(set(control.get("supporting_evidence_ids", []))),
        "epistemic_status": control.get("confidence"),
        "source_control_id": control.get("control_id"),
        "hardness": control.get("hardness", "SOFT"),
    }


def build_entity_state(control: dict[str, Any]) -> StructuredObject:
    family = control.get("_family", "identity_state")
    entity_id = control.get("_target_id") or "entity_unspecified"
    return StructuredObject(
        schema="cpcs.entity_state/1.0",
        target="entities[]",
        value={
            "object_id": "cpcs_entity_state_" + _sid(control["control_id"]),
            "entity_ref": entity_id,
            "state_family": family,
            "state": "UNRESOLVED",
            "state_enum": SOURCE_VALUE_ENUMS["visibility_state"]
                if family == "visibility" else None,
            "scope": control.get("scope", "scene"),
            "temporal_scope": control.get("_temporal_scope"),
            "phase_scope": control.get("_phase_scope"),
            "lineage": _lineage(control),
        },
    )


def build_interaction(control: dict[str, Any]) -> StructuredObject:
    return StructuredObject(
        schema="cpcs.interaction/1.0",
        target="interactions[]",
        value={
            "interaction_id": "cpcs_interaction_" + _sid(control["control_id"]),
            "participants": control.get("_participants", []),
            "roles": control.get("_roles", {}),
            "interaction_type": control.get("_family", "contact"),
            "contact": {
                "mode": None, "semantic": None, "geometry": None,
                "identity": None, "persistence": None,
                "state_transition": {
                    "enum": SOURCE_VALUE_ENUMS["contact_state_transition"],
                    "value": None,
                },
            },
            "temporal_scope": control.get("_temporal_scope"),
            "phase_scope": control.get("_phase_scope"),
            "continuity_requirements": [],
            "verification_refs": [],
            "lineage": _lineage(control),
        },
    )


def build_event(control: dict[str, Any]) -> StructuredObject:
    return StructuredObject(
        schema="cpcs.event/1.0",
        target="beats[]",
        value={
            "event_id": "cpcs_event_" + _sid(control["control_id"]),
            "event_type": control.get("_family", "action_event"),
            "target": control.get("target", "scene"),
            "temporal_order": "UNRESOLVED",
            "causal_dependencies": [],
            "lineage": _lineage(control),
        },
    )


def build_temporal_relation(control: dict[str, Any]) -> StructuredObject:
    return StructuredObject(
        schema="cpcs.temporal_relation/1.0",
        target="continuity.cpcs_temporal_relations[]",
        value={
            "relation_id": "cpcs_temporal_" + _sid(control["control_id"]),
            "before": control.get("_before"),
            "after": control.get("_after"),
            "relation_type": control.get("_family", "temporal_order"),
            "lineage": _lineage(control),
        },
    )


def build_causal_edge(control: dict[str, Any]) -> StructuredObject:
    return StructuredObject(
        schema="cpcs.causal_edge/1.0",
        target="continuity.cpcs_causal_edges[]",
        value={
            "edge_id": "cpcs_causal_" + _sid(control["control_id"]),
            "cause": control.get("_cause"),
            "effect": control.get("_effect"),
            "precondition": None,
            "lineage": _lineage(control),
        },
    )


def build_continuity_invariant(control: dict[str, Any]) -> StructuredObject:
    return StructuredObject(
        schema="cpcs.continuity_invariant/1.0",
        target="continuity.cpcs_invariants[]",
        value={
            "invariant_id": "cpcs_invariant_" + _sid(control["control_id"]),
            "invariant_class": control.get("_family", "continuity_invariant"),
            "target": control.get("target", "scene"),
            "scope": control.get("scope", "scene"),
            "temporal_scope": control.get("_temporal_scope"),
            "phase_scope": control.get("_phase_scope"),
            "lineage": _lineage(control),
        },
    )


def build_constraint(control: dict[str, Any]) -> StructuredObject:
    return StructuredObject(
        schema="cpcs.constraint/1.0",
        target="continuity.cpcs_constraints[]",
        value={
            "constraint_id": "cpcs_constraint_" + _sid(control["control_id"]),
            "constraint_class": control.get("_family", "negative_constraint"),
            "forbidden": control.get("_forbidden"),
            "scope": control.get("scope", "scene"),
            "lineage": _lineage(control),
        },
    )


def build_camera_subject_relation(control: dict[str, Any]) -> StructuredObject:
    return StructuredObject(
        schema="cpcs.camera_subject_relation/1.0",
        target="camera.cpcs_subject_visibility[]",
        value={
            "relation_id": "cpcs_camera_" + _sid(control["control_id"]),
            "subject_ref": control.get("_subject_ref"),
            "visibility_requirement": control.get("_family", "camera_subject_relation"),
            "scope": control.get("scope", "shot"),
            "lineage": _lineage(control),
        },
    )


def build_performance_event(control: dict[str, Any]) -> StructuredObject:
    return StructuredObject(
        schema="cpcs.performance_event/1.0",
        target="performance.cpcs_performance_events[]",
        value={
            "event_id": "cpcs_perf_" + _sid(control["control_id"]),
            "effort_quality": control.get("_family", "performance_effort"),
            "epistemic_note": "interpreted performance semantics, not physical force",
            "lineage": _lineage(control),
        },
    )


def build_style_invariant(control: dict[str, Any]) -> StructuredObject:
    return StructuredObject(
        schema="cpcs.style_invariant/1.0",
        target="style.cpcs_style_invariants[]",
        value={
            "invariant_id": "cpcs_style_" + _sid(control["control_id"]),
            "invariant_class": control.get("_family", "style_invariant"),
            "protects": "physical/identity invariants remain protected",
            "lineage": _lineage(control),
        },
    )


def build_editing_continuity(control: dict[str, Any]) -> StructuredObject:
    return StructuredObject(
        schema="cpcs.editing_continuity/1.0",
        target="editing.cpcs_editing_continuity[]",
        value={
            "continuity_id": "cpcs_edit_" + _sid(control["control_id"]),
            "transition_scope": control.get("scope", "transition"),
            "lineage": _lineage(control),
        },
    )


CONSTRUCTORS: dict[str, Any] = {
    "cpcs.entity_state.identity": build_entity_state,
    "cpcs.entity_state.possession": build_entity_state,
    "cpcs.entity_state.ownership": build_entity_state,
    "cpcs.entity_state.support": build_entity_state,
    "cpcs.entity_state.balance": build_entity_state,
    "cpcs.entity_state.orientation": build_entity_state,
    "cpcs.entity_state.visibility": build_entity_state,
    "cpcs.entity_state.occlusion": build_entity_state,
    "cpcs.interaction.contact": build_interaction,
    "cpcs.interaction.coordination": build_interaction,
    "cpcs.event.action": build_event,
    "cpcs.continuity.temporal_relation": build_temporal_relation,
    "cpcs.continuity.causal_edge": build_causal_edge,
    "cpcs.continuity.invariant": build_continuity_invariant,
    "cpcs.constraint.negative": build_constraint,
    "cpcs.camera.subject_visibility": build_camera_subject_relation,
    "cpcs.performance.effort": build_performance_event,
    "cpcs.style.invariant": build_style_invariant,
    "cpcs.editing.continuity": build_editing_continuity,
}


def map_control(control: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    """Deterministic admission: control_type -> registry entry.

    Returns (path_id, entry) or (None, None). No prose routing."""
    for ct in control.get("control_type", []) or []:
        path_id = CONTROL_TYPE_TO_PATH.get(ct)
        if path_id and path_id in REGISTRY:
            return path_id, REGISTRY[path_id]
    # semantic family from deterministic structured identifiers only
    family = control.get("_family")
    if family:
        for path_id, entry in REGISTRY.items():
            if entry["semantic_family"] == family:
                return path_id, entry
    return None, None
