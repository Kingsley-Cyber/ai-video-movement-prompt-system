"""NB-1 real-runtime diagnostics (frozen runtime, no provider).

Five acceptance cases + drone negative: narrative beat extraction,
SI-1 binding, edge kinds, TD-1 attribution. Writes
NB1_REAL_RUNTIME_DIAGNOSTICS_v0.1.json, NB1_INTENT_EVENT_SURVIVAL_
AUDIT_v0.1.json, NB1_NARRATIVE_BEAT_CONTRACT_v0.1.json.
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
DIAG = OUT / "NB1_REAL_RUNTIME_DIAGNOSTICS_v0.1.json"
AUDIT = OUT / "NB1_INTENT_EVENT_SURVIVAL_AUDIT_v0.1.json"
CONTRACT = OUT / "NB1_NARRATIVE_BEAT_CONTRACT_v0.1.json"

CASES: list[dict[str, Any]] = [
    {"name": "UGC_WATER_BOTTLE_15S", "duration": 15.0, "intent":
        "I want a 15-second TikTok-style UGC video of a woman casually "
        "showing off a water bottle she actually uses every day. She "
        "should pick it up, take a drink, talk about why she likes it, "
        "and show it to the camera at the end. I want it to feel natural "
        "and believable like a real creator filmed it on her phone, not "
        "like an ad."},
    {"name": "FIGHT_6S", "duration": 6.0, "intent":
        "A fighter catches an opponent's leg, swings him in a wide arc, "
        "releases him onto the water, then immediately pressures him "
        "while he tries to recover."},
    {"name": "OBJECT_MANIPULATION_6S", "duration": 6.0, "intent":
        "A pair of hands assembles a small mechanical keyboard on a desk."},
    {"name": "HUMAN_PERFORMANCE_DIALOGUE_6S", "duration": 6.0, "intent":
        "Two actors exchange a quiet line in a close-up two-shot, with "
        "subtle micro-reactions."},
    {"name": "DRONE_6S", "duration": 6.0, "intent":
        "A drone camera orbits a coastal cliff with no performer visible."},
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
    from lab.application.cpcs_narrative_beats import (
        annotate_temporal_plan, build_narrative_beat_graph)
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
    graph = build_narrative_beat_graph(intent, units=units)
    annotated = annotate_temporal_plan(plan, graph)
    user_beats = [b for b in graph.beats if b["origin"] == "USER_EXPLICIT"]
    derived_beats = [b for b in graph.beats
                     if b["origin"] == "DERIVED_PREREQUISITE"]
    bound_units = {uid for b in graph.beats for uid in b["bound_si1_unit_ids"]}
    edge_kinds: dict[str, int] = {}
    for e in graph.edges:
        edge_kinds[e["kind"]] = edge_kinds.get(e["kind"], 0) + 1
    return {
        "explicit_user_beat_count": len(user_beats),
        "derived_support_beat_count": len(derived_beats),
        "unresolved_beat_count": len(graph.unresolved_items),
        "user_beat_displays": [b["display_name"] for b in user_beats],
        "derived_beat_displays": [b["display_name"] for b in derived_beats],
        "si1_units_total": len(units),
        "si1_units_bound_to_beats": len(bound_units),
        "unbound_si1_units": len(units) - len(bound_units),
        "narrative_edge_count": len(graph.edges),
        "edge_kinds": edge_kinds,
        "recruited_regions": sum(
            1 for d in rec["dispositions"] if d["disposition"] == "RECRUIT"),
        "scoped_modules": modules["counts"]["scoped_emit_count"],
        "td1_scheduled_units": len(plan.atomic_unit_schedule),
        "td1_units_with_narrative_beat_refs": sum(
            1 for e in annotated["atomic_unit_schedule"]
            if e.get("narrative_beat_id")),
        "duration_budget": duration,
        "feasibility_status": plan.feasibility,
        "beat_placements": [
            {"display": b["display_name"],
             "bound_units": len(b["bound_si1_unit_ids"]),
             "binding_kind": b["binding_kind"]}
            for b in graph.beats
        ],
        "graph_hash": graph.graph_hash,
    }


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    from lab.application.cpcs_deliberation import frozen_knowledge_snapshot
    from lab.application.reasoning_treatment import FrozenRuntimeBackend

    snapshot = frozen_knowledge_snapshot()
    backend = FrozenRuntimeBackend()
    results: dict[str, Any] = {}
    for case in CASES:
        results[case["name"]] = _run(case["intent"], case["duration"],
                                     snapshot, backend)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
        capture_output=True, text=True, check=True).stdout.strip()
    DIAG.write_text(json.dumps({
        "artifact": "CPCS_NB1_REALTIME_DIAGNOSTICS",
        "version": "v0.1",
        "git_commit": commit,
        "cases": results,
    }, indent=1) + "\n")
    AUDIT.write_text(json.dumps({
        "artifact": "CPCS_NB1_INTENT_EVENT_SURVIVAL_AUDIT",
        "version": "v0.1",
        "pre_nb1_survival": {
            "normalized_intent": "coarse only (primary_domain, task, "
                "audience_effect, workflow_hint) — no clause/event "
                "structure survives",
            "dr1_observations": "entity mentions only (fixed token list)",
            "activation_packet": "requirement/trigger/failure signals, "
                "no narrative beats",
            "ec1_controls": "structured controls without narrative "
                "predicates",
            "si1_units": "evidence-bound, semantically anonymous "
                "(hash ids)",
            "td1": "allocates to anonymous units; causal edges = 0 on "
                "real runtime",
        },
        "nb1_adds": {
            "narrative_beat_graph": "user clause beats + declared "
                "consequence beats",
            "beat_origin": "USER_EXPLICIT / DERIVED_PREREQUISITE",
            "edge_kinds": "USER_SEQUENCE (precedence only) + "
                "STATE_TRANSITION (declared consequences); causation "
                "never asserted from order alone",
            "binding": "SI-1 units bind by structured failure-family "
                "overlap; zero overlap = SI1_UNIT_UNBOUND (never "
                "guessed)",
            "td1_annotation": "additive narrative_beat_id per schedule "
                "entry",
        },
    }, indent=1) + "\n")
    CONTRACT.write_text(json.dumps({
        "artifact": "CPCS_NB1_NARRATIVE_BEAT_CONTRACT",
        "version": "v0.1",
        "beat_identity": "structured (predicate + actor + object + "
            "source span + intent hash); display names are diagnostic "
            "labels only",
        "origins": ["USER_EXPLICIT", "DERIVED_PREREQUISITE",
                    "USER_IMPLIED_SEQUENCE", "SUPPORTING_TRANSITION"],
        "edge_kinds": ["USER_SEQUENCE", "STATE_TRANSITION",
                       "EXPLICIT_BEFORE", "EXPLICIT_AFTER",
                       "CAUSAL_REQUIRED", "PREREQUISITE_OF",
                       "OVERLAP_ALLOWED", "SUPPORTING_TRANSITION"],
        "causation_policy": ("clause order establishes temporal "
            "precedence only; CAUSAL_REQUIRED is never derived from "
            "order alone"),
        "binding_kinds": ["DIRECT_BINDING", "SUPPORTING_BINDING",
                          "UNRESOLVED_BINDING"],
        "d4": "narrative beats are planning representations, never "
            "canonical controls; no prose-to-control coercion",
        "vocabulary_policy": "conservative declared action vocabulary; "
            "unmatched clauses recorded as NO_ACTION_VOCABULARY",
    }, indent=1) + "\n")
    print(json.dumps({
        name: {
            "user_beats": fx["user_beat_displays"],
            "derived": fx["derived_beat_displays"],
            "edges": fx["edge_kinds"],
            "units": f"{fx['si1_units_bound_to_beats']}/{fx['si1_units_total']} bound",
            "td1_refs": fx["td1_units_with_narrative_beat_refs"],
            "feasibility": fx["feasibility_status"],
        } for name, fx in results.items()
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
