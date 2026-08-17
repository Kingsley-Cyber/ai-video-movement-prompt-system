"""TD-1 — Temporal Director / Beat Budget (deterministic, causal-first).

Schedules MEANING, not words. Consumes SI-1 atomic units + causal
dependencies + placement lifetimes + existing temporal semantics and
produces a feasible temporal directing plan.

Frozen rules:
- Causal order is primary: a unit's predecessors always precede it;
  state effects are never scheduled before their cause.
- Overlap is eligibility from the causal DAG (no directed path), never
  arbitrary serialization; deliberate overlap is recorded, not forced.
- Total duration is NEVER invented. Unknown total -> TEMPORALLY_
  UNDERSPECIFIED plan (relative weights + ordering only).
- No universal numeric readability minimum is invented. READABILITY_
  CRITICAL units are flagged and receive allocation priority via
  deterministic weights; feasibility verdicts derive from the
  allocation math against the declared quantization parameter.
- Hard temporal requirements are never silently compressed away.
- No provider-specific timing claims; no prompt strings.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

TD1_PLAN_SCHEMA = "cpcs.temporal_directing_plan/0.1"
TD1_SCHEDULE_SCHEMA = "cpcs.atomic_unit_schedule/0.1"

# Allocation quantization (seconds): allocations below the quantum are
# recorded as compressed; the quantum is a declared POLICY PARAMETER,
# not an evidence-backed readability minimum.
ALLOCATION_QUANTUM_S = 0.05
# Compression threshold: an allocation at or below this declared policy
# threshold is recorded as compressed (absolute pressure signal; NOT a
# readability claim about any specific event class).
COMPRESSION_THRESHOLD_S = 0.1

DURATION_SOURCES = frozenset({
    "USER_EXPLICIT", "EXISTING_SCENE_CONTRACT",
    "EXISTING_PROVIDER_OR_CLIP_CONTRACT", "EXISTING_BASELINE_DEFAULT",
    "TEST_CONDITION",
})

FEASIBILITY_CLASSES = frozenset({
    "FEASIBLE", "FEASIBLE_WITH_COMPRESSION", "REQUIRES_DECOMPOSITION",
    "TEMPORALLY_UNDERSPECIFIED", "INFEASIBLE_WITH_CURRENT_REQUIREMENTS",
})

TEMPORAL_POLICY_SNAPSHOT = {
    "policy": "td1-causal-first-weight-allocation",
    "allocation_quantum_s": ALLOCATION_QUANTUM_S,
    "compression_threshold_s": COMPRESSION_THRESHOLD_S,
    "causal_order_primary": True,
    "overlap_eligibility": "causal_dag_no_directed_path",
    "no_invented_total_duration": True,
    "no_invented_readability_minimums": True,
    "compression_is_absolute_pressure_not_readability_claim": True,
    "readability_critical_signal": [
        "verification_refs non-empty",
        "contact_persistence",
        "placement role ENVIRONMENT_RESPONSE / RECOVERY / OBJECT_STATE",
        "unit carries state transitions",
    ],
    "weight_factors": {
        "base": 1.0,
        "state_transition": 0.5,
        "contact_persistence": 0.5,
        "verification_bound": 0.5,
        "environment_response_role": 0.5,
        "hardness_HARD_lineage": 0.5,
    },
    "hardness_never_compressed_away": True,
}


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass
class AtomicUnitSchedule:
    unit_id: str
    start_s: float | None
    end_s: float | None
    duration_s: float | None
    temporal_role: str
    hardness: str
    predecessor_ids: list[str]
    allowed_overlap_ids: list[str]
    prohibited_overlap_ids: list[str]
    minimum_readability_s: float | None
    priority_class: str
    readability_critical: bool
    lifetime_bindings: list[str]
    evidence_ids: list[str]
    requirement_ids: list[str]
    reason_codes: list[str]
    lineage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TD1_SCHEDULE_SCHEMA,
            "unit_id": self.unit_id,
            "start_s": self.start_s,
            "end_s": self.end_s,
            "duration_s": self.duration_s,
            "temporal_role": self.temporal_role,
            "hardness": self.hardness,
            "predecessor_ids": self.predecessor_ids,
            "allowed_overlap_ids": self.allowed_overlap_ids,
            "prohibited_overlap_ids": self.prohibited_overlap_ids,
            "minimum_readability_s": self.minimum_readability_s,
            "priority_class": self.priority_class,
            "readability_critical": self.readability_critical,
            "lifetime_bindings": self.lifetime_bindings,
            "evidence_ids": self.evidence_ids,
            "requirement_ids": self.requirement_ids,
            "reason_codes": self.reason_codes,
            "lineage": self.lineage,
        }


@dataclass
class TemporalDirectingPlan:
    plan_id: str
    total_duration_s: float | None
    duration_source: str | None
    atomic_unit_schedule: list[dict[str, Any]]
    dependency_edges: list[dict[str, str]]
    overlap_groups: list[list[str]]
    unresolved_temporal_gaps: list[dict[str, Any]]
    feasibility: str
    compression_decisions: list[dict[str, Any]]
    lineage: dict[str, Any]
    plan_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TD1_PLAN_SCHEMA,
            "plan_id": self.plan_id,
            "total_duration_s": self.total_duration_s,
            "duration_source": self.duration_source,
            "atomic_unit_schedule": self.atomic_unit_schedule,
            "dependency_edges": self.dependency_edges,
            "overlap_groups": self.overlap_groups,
            "unresolved_temporal_gaps": self.unresolved_temporal_gaps,
            "feasibility": self.feasibility,
            "compression_decisions": self.compression_decisions,
            "lineage": self.lineage,
            "plan_hash": self.plan_hash,
        }


def _causal_dag(units: list[Any]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    predecessors: dict[str, set[str]] = {}
    successors: dict[str, set[str]] = {}
    for u in units:
        predecessors.setdefault(u.unit_id, set())
        successors.setdefault(u.unit_id, set())
    for u in units:
        for p in u.ordered_after:
            if p in predecessors:
                predecessors[u.unit_id].add(p)
                successors[p].add(u.unit_id)
    return predecessors, successors


def _has_path(successors: dict[str, set[str]], a: str, b: str) -> bool:
    stack = [a]
    seen = set()
    while stack:
        node = stack.pop()
        if node == b:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(successors.get(node, set()))
    return False


def _weight(unit: Any, role_by_unit: dict[str, str]) -> float:
    lineage = unit.lineage or {}
    weight = 1.0
    if unit.state_transitions:
        weight += 0.5
    if unit.state_transitions.get("contact_persistence"):
        weight += 0.5
    if (lineage.get("verification_refs")
            or lineage.get("si1_bound_obligation_ids")):
        weight += 0.5
    if role_by_unit.get(unit.unit_id) in ("ENVIRONMENT_RESPONSE", "RECOVERY",
                                          "OBJECT_STATE"):
        weight += 0.5
    if lineage.get("hardness") == "HARD":
        weight += 0.5
    return weight


def _readability_critical(unit: Any, role_by_unit: dict[str, str]) -> bool:
    lineage = unit.lineage or {}
    return bool(
        lineage.get("verification_refs")
        or lineage.get("si1_bound_obligation_ids")
        or unit.state_transitions.get("contact_persistence")
        or role_by_unit.get(unit.unit_id) in ("ENVIRONMENT_RESPONSE",
                                              "RECOVERY", "OBJECT_STATE")
        or unit.state_transitions)


def build_temporal_plan(
    units: list[Any],
    *,
    total_duration_s: float | None = None,
    duration_source: str | None = None,
    placement: list[Any] | None = None,
) -> TemporalDirectingPlan:
    """Deterministic TD-1: causal-first weight allocation.

    units: SI-1/KA-2.2 AtomicUnit objects (with ordered_after).
    placement: optional KnowledgePlacementDecision list for role weights.
    """
    if duration_source and duration_source not in DURATION_SOURCES:
        raise ValueError(f"unknown duration source: {duration_source}")
    placement = list(placement or [])
    role_by_unit: dict[str, str] = {}
    for p in placement:
        for uid in p.target_unit_ids:
            role_by_unit.setdefault(uid, p.placement_role)
    predecessors, successors = _causal_dag(units)
    unit_by_id = {u.unit_id: u for u in units}
    ordered = sorted(units, key=lambda u: u.unit_id)
    topo: list[str] = []
    remaining = {u.unit_id for u in units}
    while remaining:
        ready = sorted(uid for uid in remaining
                       if not (predecessors[uid] & remaining))
        if not ready:
            # cycle fallback (should not occur with ordered_after chains):
            # deterministic: take the lexicographically first remaining
            ready = [sorted(remaining)[0]]
        for uid in ready:
            topo.append(uid)
            remaining.discard(uid)
    schedules: list[AtomicUnitSchedule] = []
    weights = {uid: _weight(unit_by_id[uid], role_by_unit) for uid in topo}
    total_weight = sum(weights.values()) or 1.0
    unresolved = total_duration_s is None
    start = 0.0
    for uid in topo:
        unit = unit_by_id[uid]
        lineage = unit.lineage or {}
        preds = sorted(predecessors[uid])
        allowed = []
        prohibited = []
        for other in topo:
            if other == uid:
                continue
            if _has_path(successors, uid, other) or _has_path(successors, other, uid):
                prohibited.append(other)
            else:
                allowed.append(other)
        duration = None
        start_s = None
        end_s = None
        if not unresolved:
            duration = round(total_duration_s * weights[uid] / total_weight, 2)
            duration = max(duration, ALLOCATION_QUANTUM_S)
            start_s = round(start, 2)
            end_s = round(start + duration, 2)
            start = end_s
        schedules.append(AtomicUnitSchedule(
            unit_id=uid,
            start_s=start_s,
            end_s=end_s,
            duration_s=duration,
            temporal_role=("INTERACTION" if unit.unit_kind != "EVENT"
                           else "EVENT"),
            hardness=str(lineage.get("hardness") or "SOFT"),
            predecessor_ids=preds,
            allowed_overlap_ids=allowed,
            prohibited_overlap_ids=prohibited,
            minimum_readability_s=None,
            priority_class=("CRITICAL" if _readability_critical(
                unit, role_by_unit) else "STANDARD"),
            readability_critical=_readability_critical(unit, role_by_unit),
            lifetime_bindings=sorted({
                p.lifetime for p in placement
                if uid in p.target_unit_ids}),
            evidence_ids=sorted(set(lineage.get("evidence_ids", []) or [])),
            requirement_ids=sorted(set(lineage.get("requirement_ids", [])
                                      or [])),
            reason_codes=["causal_order_preserved"] if preds else [],
            lineage={"unit_kind": unit.unit_kind,
                     "source": lineage.get("source")},
        ))
    dependency_edges = [
        {"from": p, "to": uid}
        for uid in topo for p in sorted(predecessors[uid])
    ]
    overlap_groups: list[list[str]] = []
    for i, uid in enumerate(topo):
        group = [uid]
        for other in topo[i + 1:]:
            if _has_path(successors, uid, other) or _has_path(successors,
                                                              other, uid):
                continue
            group.append(other)
        if len(group) > 1:
            overlap_groups.append(group)
    compression_decisions: list[dict[str, Any]] = []
    if not unresolved:
        for s in schedules:
            if s.duration_s is not None and s.duration_s <= COMPRESSION_THRESHOLD_S:
                compression_decisions.append({
                    "unit_id": s.unit_id,
                    "action": ("compressed_at_threshold"
                               if s.duration_s > ALLOCATION_QUANTUM_S
                               else "compressed_to_quantum"),
                    "duration_s": s.duration_s,
                    "readability_critical": s.readability_critical,
                })
    gaps: list[dict[str, Any]] = []
    if unresolved:
        gaps.append({
            "gap_id": "gap_total_duration",
            "kind": "TEMPORAL_TOTAL_UNDERSPECIFIED",
            "reason": "no legitimate duration source; relative plan only",
        })
    if unresolved:
        feasibility = "TEMPORALLY_UNDERSPECIFIED"
    else:
        hard_units = [s for s in schedules if s.hardness == "HARD"]
        compressed_hard = [s for s in hard_units if s.duration_s is not None
                           and s.duration_s <= ALLOCATION_QUANTUM_S]
        if (schedules
                and all(s.duration_s is not None
                        and s.duration_s <= COMPRESSION_THRESHOLD_S
                        for s in schedules)):
            feasibility = "REQUIRES_DECOMPOSITION"
        elif hard_units and len(compressed_hard) == len(hard_units):
            feasibility = "REQUIRES_DECOMPOSITION"
        elif compression_decisions:
            feasibility = "FEASIBLE_WITH_COMPRESSION"
        else:
            feasibility = "FEASIBLE"
    body = {
        "schedules": [s.to_dict() for s in schedules],
        "dependencies": sorted(dependency_edges,
                               key=lambda e: (e["from"], e["to"])),
        "overlap_groups": overlap_groups,
        "gaps": gaps,
        "feasibility": feasibility,
        "compression_decisions": compression_decisions,
        "total_duration_s": total_duration_s,
        "duration_source": duration_source,
    }
    plan_hash = _sha(body)
    return TemporalDirectingPlan(
        plan_id="td1_" + plan_hash[:16],
        total_duration_s=total_duration_s,
        duration_source=duration_source,
        atomic_unit_schedule=[s.to_dict() for s in schedules],
        dependency_edges=sorted(dependency_edges,
                                key=lambda e: (e["from"], e["to"])),
        overlap_groups=overlap_groups,
        unresolved_temporal_gaps=gaps,
        feasibility=feasibility,
        compression_decisions=compression_decisions,
        lineage={
            "policy": TEMPORAL_POLICY_SNAPSHOT["policy"],
            "unit_count": len(schedules),
            "policy_hash": _sha(TEMPORAL_POLICY_SNAPSHOT),
        },
        plan_hash=plan_hash,
    )


def validate_temporal_plan(plan: TemporalDirectingPlan) -> list[dict[str, str]]:
    """Deterministic TD-1 verification; empty list = valid."""
    violations: list[dict[str, str]] = []
    sched = {s["unit_id"]: s for s in plan.atomic_unit_schedule}
    total = plan.total_duration_s
    if total is not None:
        for s in plan.atomic_unit_schedule:
            if s["start_s"] is None or s["end_s"] is None:
                violations.append({"code": "unresolved_in_scheduled_plan",
                                   "message": s["unit_id"]})
                continue
            if s["start_s"] < -1e-9 or s["end_s"] < s["start_s"]:
                violations.append({"code": "negative_or_inverted_interval",
                                   "message": s["unit_id"]})
            if s["end_s"] > total + 1e-6:
                violations.append({"code": "outside_total_budget",
                                   "message": s["unit_id"]})
    for s in plan.atomic_unit_schedule:
        for p in s["predecessor_ids"]:
            ps = sched.get(p)
            if ps is None:
                continue
            if (s["start_s"] is not None and ps["end_s"] is not None
                    and s["start_s"] < ps["end_s"] - 1e-9):
                violations.append({"code": "predecessor_order_violated",
                                   "message": f"{p} -> {s['unit_id']}"})
        for p in s["prohibited_overlap_ids"]:
            ps = sched.get(p)
            if ps is None:
                continue
            if (s["start_s"] is not None and ps["end_s"] is not None
                    and not (s["end_s"] <= ps["start_s"]
                             or ps["end_s"] <= s["start_s"])):
                violations.append({"code": "prohibited_overlap",
                                   "message": f"{p} <> {s['unit_id']}"})
    return violations
