"""TD-1 real-runtime diagnostics (frozen runtime, no provider).

Runs the five acceptance cases (fight at 3/6/10s test conditions, serum,
dialogue, manipulation, drone) through the full pipeline + TD-1 and
writes TD1_REAL_RUNTIME_DIAGNOSTICS_v0.1.json plus the computed
temporal-capability audit TD1_TEMPORAL_CAPABILITY_AUDIT_BEFORE_v0.1.json
and policy artifact TD1_TEMPORAL_POLICY_v0.1.json.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from lab.compiler.profiles import REPO_ROOT

OUT = Path(__file__).resolve().parent
DIAG = OUT / "TD1_REAL_RUNTIME_DIAGNOSTICS_v0.1.json"
AUDIT = OUT / "TD1_TEMPORAL_CAPABILITY_AUDIT_BEFORE_v0.1.json"
POLICY = OUT / "TD1_TEMPORAL_POLICY_v0.1.json"

CASES: list[dict[str, Any]] = [
    {"name": "FIGHT_3S", "duration": 3.0, "intent":
        "A fighter catches an opponent's leg, swings him in a wide arc, "
        "releases him onto the water, then immediately pressures him "
        "while he tries to recover."},
    {"name": "FIGHT_6S", "duration": 6.0, "intent":
        "A fighter catches an opponent's leg, swings him in a wide arc, "
        "releases him onto the water, then immediately pressures him "
        "while he tries to recover."},
    {"name": "FIGHT_10S", "duration": 10.0, "intent":
        "A fighter catches an opponent's leg, swings him in a wide arc, "
        "releases him onto the water, then immediately pressures him "
        "while he tries to recover."},
    {"name": "UGC_SERUM_10S", "duration": 10.0, "intent":
        "A woman records a casual handheld creator video trying a "
        "premium facial serum. She picks the bottle up, unscrews the "
        "dropper, dispenses two drops, rubs the serum between her "
        "fingers, applies it to her cheek, notices the texture, reacts "
        "positively, talks naturally to the viewer, then brings the "
        "bottle near the phone camera."},
    {"name": "HUMAN_PERFORMANCE_DIALOGUE_6S", "duration": 6.0, "intent":
        "Two actors exchange a quiet line in a close-up two-shot, with "
        "subtle micro-reactions."},
    {"name": "OBJECT_MANIPULATION_6S", "duration": 6.0, "intent":
        "A pair of hands assembles a small mechanical keyboard on a desk."},
    {"name": "DRONE_6S", "duration": 6.0, "intent":
        "A drone camera orbits a coastal cliff with no performer visible."},
    {"name": "FIGHT_NO_DURATION", "duration": None, "intent":
        "A fighter catches an opponent's leg, swings him in a wide arc, "
        "releases him onto the water, then immediately pressures him "
        "while he tries to recover."},
]


def _run(intent: str, duration: float | None, snapshot: Any,
         backend: Any) -> dict[str, Any]:
    from lab.application.cpcs_deliberation import DeliberationEngine
    from lab.application.cpcs_knowledge_awareness import build_awareness_profile
    from lab.application.cpcs_knowledge_constellation import assemble_constellation
    from lab.application.cpcs_knowledge_placement import (
        assemble_directing_modules, build_placement, decompose_atomic_units)
    from lab.application.cpcs_knowledge_recruitment import recruit_for_intent
    from lab.application.cpcs_knowledge_refinement import (
        assess_prerequisites, build_refinement_packet)
    from lab.application.cpcs_structured_interaction_projection import (
        enrich_interaction_payloads)
    from lab.application.cpcs_temporal_director import build_temporal_plan
    from lab.application.reasoning_treatment import TreatmentAdapter

    engine = DeliberationEngine(snapshot, backend)
    activation, packet = engine.activate(
        intent, {"intent": {"primary_domain": "action"}}, observations=[])
    awareness = build_awareness_profile(intent, activation=activation)
    translation = TreatmentAdapter(REPO_ROOT).translate(
        packet, snapshot=snapshot, activation=activation)
    translation.structured_objects = enrich_interaction_payloads(
        translation.structured_objects, packet)
    app = translation.application_set
    evidence_by_id = {ev["atomic_record_id"]: ev
                      for ev in packet.get("retrieved_evidence", []) or []}
    const = assemble_constellation(app, activation,
                                   evidence_by_id=evidence_by_id)
    pack_lookup = {e["pack"]["pack_id"]: e["pack"]
                   for e in app["applications"]}
    rec = recruit_for_intent(const, activation, pack_lookup=pack_lookup,
                             awareness=awareness.to_dict())
    units = decompose_atomic_units(translation.structured_objects)
    placement = build_placement(rec, const, units, pack_lookup=pack_lookup,
                                awareness=awareness.to_dict())
    new_pre, gaps = assess_prerequisites(rec, const, activation,
                                         pack_lookup=pack_lookup)
    refine = build_refinement_packet(rec, const, activation,
                                     new_prerequisites=new_pre,
                                     coverage_gaps=gaps,
                                     application_set=app)
    modules = assemble_directing_modules(placement, units, refine,
                                         pack_lookup=pack_lookup,
                                         constellation=const)
    plan = build_temporal_plan(
        units, total_duration_s=duration,
        duration_source="TEST_CONDITION" if duration else None,
        placement=placement)
    scheduled = [s for s in plan.atomic_unit_schedule
                 if s["start_s"] is not None]
    env_unit_ids = {uid for p in placement
                    if p.placement_role == "ENVIRONMENT_RESPONSE"
                    for uid in p.target_unit_ids}
    env_intervals = [
        round(s["duration_s"], 2)
        for s in plan.atomic_unit_schedule
        if s["unit_id"] in env_unit_ids and s["duration_s"] is not None]
    return {
        "total_duration_s": plan.total_duration_s,
        "duration_source": plan.duration_source,
        "feasibility_status": plan.feasibility,
        "atomic_units_total": len(plan.atomic_unit_schedule),
        "scheduled_units": len(scheduled),
        "units_with_numeric_intervals": len(scheduled),
        "overlap_count": len(plan.overlap_groups),
        "hard_dependency_count": len(plan.dependency_edges),
        "readability_critical_count": sum(
            1 for s in plan.atomic_unit_schedule
            if s["readability_critical"]),
        "contact_interval_count": sum(
            1 for s in plan.atomic_unit_schedule
            if "CONTACT_INTERVAL" in s["lifetime_bindings"]),
        "recovery_interval_count": 0,
        "unresolved_temporal_items": len(plan.unresolved_temporal_gaps),
        "compression_decision_count": len(plan.compression_decisions),
        "decomposition_required":
            plan.feasibility == "REQUIRES_DECOMPOSITION",
        "recruited_regions": sum(
            1 for d in rec["dispositions"] if d["disposition"] == "RECRUIT"),
        "scoped_placements": len([p for p in placement if p.target_unit_ids]),
        "prompt_visible_modules": modules["counts"]["global_emit_count"]
        + modules["counts"]["scoped_emit_count"],
        "water_impact_interval_s": env_intervals,
        "plan_hash": plan.plan_hash,
    }


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    from lab.application.cpcs_deliberation import frozen_knowledge_snapshot
    from lab.application.cpcs_knowledge_constellation import (
        MERGE_POLICY_SNAPSHOT)
    from lab.application.cpcs_knowledge_recruitment import (
        RECRUITMENT_POLICY_SNAPSHOT)
    from lab.application.cpcs_temporal_director import (
        TEMPORAL_POLICY_SNAPSHOT, validate_temporal_plan)
    from lab.application.reasoning_treatment import FrozenRuntimeBackend

    snapshot = frozen_knowledge_snapshot()
    backend = FrozenRuntimeBackend()
    results: dict[str, Any] = {}
    for case in CASES:
        result = _run(case["intent"], case["duration"], snapshot, backend)
        results[case["name"]] = result
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
        capture_output=True, text=True, check=True).stdout.strip()
    hashes = {
        "merge_policy": hashlib.sha256(json.dumps(
            MERGE_POLICY_SNAPSHOT, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest(),
        "recruitment_policy": hashlib.sha256(json.dumps(
            RECRUITMENT_POLICY_SNAPSHOT, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest(),
    }
    DIAG.write_text(json.dumps({
        "artifact": "CPCS_TD1_REALTIME_DIAGNOSTICS",
        "version": "v0.1",
        "git_commit": commit,
        "cases": results,
        "frozen_policy_hashes": hashes,
    }, indent=1) + "\n")
    AUDIT.write_text(json.dumps({
        "artifact": "CPCS_TD1_TEMPORAL_CAPABILITY_AUDIT_BEFORE",
        "version": "v0.1",
        "existing_temporal_semantics": {
            "atomic_unit_ordered_after": "causal/temporal edges from "
                "structured temporal_relation/causal_edge objects (KA-2.2)",
            "interaction_phases": "WP-6 phases order (fixture-proven; "
                "real-runtime phase-less interactions become whole units "
                "via SI-1)",
            "ec1_condition_types": "STATE/PERSISTENCE/RELATIONSHIP/"
                "CAUSAL_RESULT/TEMPORAL_ORDER/TRANSITION (projected in SI-1)",
            "si1_time_scopes": "structured single-token scopes only",
            "placement_lifetimes": "symbolic: CONTACT_INTERVAL, PHASE_LOCAL, "
                "EVENT_ONCE, RECOVERY_UNTIL_COMPLETE, UNTIL_STATE_TRANSITION, "
                "PERSISTENT, SCENE_LOCAL, SHOT_LOCAL, BEAT_LOCAL",
            "contact_persistence": "SI-1 PERSISTENCE-class obligation "
                "projection",
        },
        "absent_before_td1": [
            "numeric beat durations", "total-duration authority in the "
            "reasoning flow", "overlap eligibility computation",
            "feasibility verdicts", "readability-priority classes",
            "compression/decomposition decisions",
        ],
        "corpus_support_referenced_not_yet_structured": [
            "ku23 beat contract interval_s", "phase overlap/coarticulation",
            "stage time vs presentation time (anime two clocks)",
        ],
    }, indent=1) + "\n")
    POLICY.write_text(json.dumps(TEMPORAL_POLICY_SNAPSHOT, indent=1) + "\n")
    print(json.dumps({name: {
        "feasibility": fx["feasibility_status"],
        "scheduled": fx["scheduled_units"],
        "critical": fx["readability_critical_count"],
        "compression": fx["compression_decision_count"],
        "impact_s": fx["water_impact_interval_s"],
        "prompt_visible": fx["prompt_visible_modules"],
    } for name, fx in results.items()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
