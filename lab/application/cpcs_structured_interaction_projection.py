"""SI-1 — Real-runtime structured interaction projection (deterministic).

Closes the gap between real-runtime recruited knowledge and KA-2.2
atomic/scoped placement. The frozen runtime emits controls and
verification obligations with structured semantics (condition types,
target paths, failure families, evidence IDs); the hermetic WP-6
interaction payload proves phase-level placement when controls carry
structured payloads. This module projects the REAL structured semantics
into the EXISTING interaction contract — deterministically, without
prose classification, without an LLM, never manufacturing absent fields.

Rules (frozen here):
- contact.persistence <- PERSISTENCE-class verification obligations
  bound to the control's requirements (same-named frozen semantics).
- verification_refs <- bound obligation IDs (structured targets only).
- continuity_requirements <- PERSISTENCE-class obligations.
- state transitions, phases, roles, actors, state_before/state_after,
  projection, recovery, world_response stay None when the runtime
  provides no structured value (explicit unknown).
- D4: obligation condition text never enters the payload.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

CONTACT_TARGET_PATHS = frozenset({
    "contact", "coordination", "interactions", "entities", "support",
    "continuity",
})
PERSISTENCE_CONDITION_TYPES = frozenset({"PERSISTENCE"})
# D4: only structured single-token scopes may enter the payload; any
# time_scope that looks like prose is excluded from lineage entirely.
_STRUCTURED_SCOPE_RE = __import__("re").compile(r"^[a-z0-9_-]+$")


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _bound_obligations(control: dict[str, Any],
                       obligations: list[dict[str, Any]]
                       ) -> list[dict[str, Any]]:
    """Obligations that bind this control: family target path AND
    (requirement overlap OR failure-family mediation) — structured only."""
    reqs = set(control.get("source_requirement_ids", []) or [])
    ctrl_failures = set(control.get("prevented_failure_families", []) or [])
    bound = []
    for o in obligations:
        o_req = o.get("requirement_id")
        targets = set(o.get("target_paths", []) or [])
        o_failures = set(o.get("failure_family_ids", []) or [])
        if not (targets & CONTACT_TARGET_PATHS):
            continue
        if o_req in reqs or (o_failures & ctrl_failures):
            bound.append(o)
    return bound


def enrich_interaction_payloads(
    structured_objects: list[dict[str, Any]],
    packet: dict[str, Any],
) -> list[dict[str, Any]]:
    """Deterministic SI-1 enrichment of interaction structured objects.

    Returns a NEW list of structured objects (inputs untouched)."""
    controls = {c.get("control_id"): c
                for c in packet.get("proposed_controls", []) or []
                if c.get("control_id")}
    obligations = list(packet.get("verification_obligations", []) or [])
    out: list[dict[str, Any]] = []
    for obj in structured_objects:
        if obj.get("target") != "interactions[]":
            out.append(obj)
            continue
        value = dict(obj.get("value") or {})
        lineage = dict(value.get("lineage") or {})
        control_id = lineage.get("source_control_id")
        control = controls.get(control_id) or {}
        bound = _bound_obligations(control, obligations)
        persistence_ids: list[str] = []
        verification_refs: list[str] = []
        condition_types: list[str] = []
        time_scopes: list[str] = []
        bound_failures: set[str] = set()
        for o in sorted(bound, key=lambda x: x.get("obligation_id", "")):
            oid = o.get("obligation_id")
            if not oid:
                continue
            verification_refs.append(oid)
            if o.get("condition_type") in PERSISTENCE_CONDITION_TYPES:
                persistence_ids.append(oid)
                condition_types.append(o["condition_type"])
                scope = o.get("time_scope")
                if isinstance(scope, str) and _STRUCTURED_SCOPE_RE.match(scope):
                    time_scopes.append(scope)
            bound_failures |= set(o.get("failure_family_ids", []) or [])
        contact = dict(value.get("contact") or {})
        contact["persistence"] = True if persistence_ids else None
        value["contact"] = contact
        value["verification_refs"] = sorted(set(
            (value.get("verification_refs") or []) + verification_refs))
        value["continuity_requirements"] = sorted(set(
            (value.get("continuity_requirements") or []) + persistence_ids))
        lineage["si1_condition_types"] = sorted(set(condition_types))
        lineage["si1_time_scopes"] = sorted(set(time_scopes))
        lineage["si1_bound_obligation_ids"] = sorted(set(verification_refs))
        lineage["si1_failure_family_ids"] = sorted(bound_failures)
        lineage["si1_projection"] = "deterministic-structured"
        value["lineage"] = lineage
        out.append({"target": obj["target"], "schema": obj["schema"],
                    "value": value})
    return out
