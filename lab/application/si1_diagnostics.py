"""SI-1 real-runtime diagnostics (5 acceptance cases, frozen runtime).

Measures the structured-interaction projection against the real corpus:
unit kind mix, state transitions, bindings, and frozen-policy hashes.
Writes SI1_REALTIME_DIAGNOSTICS_v0.1.json and the computed field-survival
matrix SI1_FIELD_SURVIVAL_MATRIX_v0.1.json.
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
DIAG = OUT / "SI1_REALTIME_DIAGNOSTICS_v0.1.json"
MATRIX = OUT / "SI1_FIELD_SURVIVAL_MATRIX_v0.1.json"

INTENTS: dict[str, str] = {
    "ACTION_FIGHT": ("A fighter catches an opponent's leg, swings him in a "
                     "wide arc, releases him onto the water, then "
                     "immediately pressures him while he tries to recover."),
    "UGC_SERUM": ("A woman records a casual handheld creator video trying a "
                  "premium facial serum. She picks the bottle up, unscrews "
                  "the dropper, dispenses two drops, rubs the serum between "
                  "her fingers, applies it to her cheek, notices the "
                  "texture, reacts positively, talks naturally to the "
                  "viewer, then brings the bottle near the phone camera."),
    "HUMAN_PERFORMANCE_DIALOGUE": ("Two actors exchange a quiet line in a "
                                   "close-up two-shot, with subtle "
                                   "micro-reactions."),
    "OBJECT_MANIPULATION": ("A pair of hands assembles a small mechanical "
                            "keyboard on a desk."),
    "CAMERA_ENVIRONMENT_ONLY": ("A drone camera orbits a coastal cliff with "
                                "no performer visible."),
}

WP6_FIELDS = [
    "roles", "state_before", "contact.persistence",
    "contact.state_transition.value", "contact_interval", "phases",
    "projection", "state_after", "recovery", "world_response",
    "verification_refs", "continuity_requirements",
]


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    from lab.application.cpcs_deliberation import (
        frozen_knowledge_snapshot,
        DeliberationEngine,
    )
    from lab.application.cpcs_knowledge_awareness import build_awareness_profile
    from lab.application.cpcs_knowledge_constellation import (
        MERGE_POLICY_SNAPSHOT,
        assemble_constellation,
    )
    from lab.application.cpcs_knowledge_placement import (
        assemble_directing_modules,
        build_placement,
        decompose_atomic_units,
    )
    from lab.application.cpcs_knowledge_recruitment import (
        RECRUITMENT_POLICY_SNAPSHOT,
        recruit_for_intent,
    )
    from lab.application.reasoning_treatment import (
        FrozenRuntimeBackend,
        TreatmentAdapter,
    )
    from lab.application.cpcs_structured_interaction_projection import (
        enrich_interaction_payloads,
    )

    snapshot = frozen_knowledge_snapshot()
    backend = FrozenRuntimeBackend()
    results: dict[str, Any] = {}
    field_observed: dict[str, int] = {f: 0 for f in WP6_FIELDS}
    for name, intent in INTENTS.items():
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
        placement = build_placement(rec, const, units,
                                    pack_lookup=pack_lookup,
                                    awareness=awareness.to_dict())
        from lab.application.cpcs_knowledge_refinement import (
            assess_prerequisites, build_refinement_packet)
        new_pre, gaps = assess_prerequisites(rec, const, activation,
                                             pack_lookup=pack_lookup)
        refine = build_refinement_packet(rec, const, activation,
                                         new_prerequisites=new_pre,
                                         coverage_gaps=gaps,
                                         application_set=app)
        modules = assemble_directing_modules(
            placement, units, refine, pack_lookup=pack_lookup,
            constellation=const)
        interactions = [o for o in translation.structured_objects
                        if o.get("target") == "interactions[]"]
        for inter in interactions:
            value = inter["value"]
            contact = value.get("contact") or {}
            observed = {
                "roles": bool(value.get("roles")),
                "state_before": value.get("state_before") is not None,
                "contact.persistence": contact.get("persistence") is True,
                "contact.state_transition.value":
                    contact.get("state_transition", {}).get("value")
                    is not None,
                "contact_interval": contact.get("contact_interval") is not None,
                "phases": bool(value.get("phases")),
                "projection": value.get("projection") is not None,
                "state_after": value.get("state_after") is not None,
                "recovery": value.get("recovery") is not None,
                "world_response": value.get("world_response") is not None,
                "verification_refs": bool(value.get("verification_refs")),
                "continuity_requirements":
                    bool(value.get("continuity_requirements")),
            }
            for field, seen in observed.items():
                if seen:
                    field_observed[field] += 1
        scoped = [p for p in placement if p.target_unit_ids]
        results[name] = {
            "intent": intent,
            "generic_event_count": sum(
                1 for u in units if u.unit_kind == "EVENT"),
            "structured_atomic_unit_count": len(units),
            "phase_unit_count": sum(
                1 for u in units if u.unit_kind == "INTERACTION_PHASE"),
            "interaction_count": sum(
                1 for u in units if u.unit_kind == "INTERACTION"),
            "state_transition_count": sum(
                len(u.state_transitions) for u in units),
            "environment_response_count": sum(
                1 for p in scoped
                if p.placement_role == "ENVIRONMENT_RESPONSE"),
            "performance_unit_count": sum(
                1 for p in scoped
                if p.placement_role == "PERFORMANCE_DIRECTION"),
            "recruited_region_count": sum(
                1 for d in rec["dispositions"]
                if d["disposition"] == "RECRUIT"),
            "regions_with_atomic_bindings": len({p.region_id for p in scoped}),
            "scoped_placement_count": len(scoped),
            "reasoning_only_count": modules["counts"][
                "reasoning_only_count"],
            "global_emit_count": modules["counts"]["global_emit_count"],
            "scoped_emit_count": modules["counts"]["scoped_emit_count"],
            "verification_only_count": modules["counts"][
                "verification_only_count"],
        }
    policy_hashes = {
        "merge_policy": hashlib.sha256(json.dumps(
            MERGE_POLICY_SNAPSHOT, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest(),
        "recruitment_policy": hashlib.sha256(json.dumps(
            RECRUITMENT_POLICY_SNAPSHOT, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest(),
    }
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
        capture_output=True, text=True, check=True).stdout.strip()
    diag_artifact = {
        "artifact": "CPCS_SI1_REALTIME_DIAGNOSTICS",
        "version": "v0.1",
        "git_commit": commit,
        "workflows": results,
        "frozen_policy_hashes": policy_hashes,
    }
    DIAG.write_text(json.dumps(diag_artifact, indent=1) + "\n")
    matrix_artifact = {
        "artifact": "CPCS_SI1_FIELD_SURVIVAL_MATRIX",
        "version": "v0.1",
        "wp6_field_non_null_observations": field_observed,
        "projection_rules": {
            "contact.persistence": "PERSISTENCE-class EC-1 obligation bound "
                                    "to the control's requirement ids",
            "verification_refs": "bound obligation ids with structured "
                                 "contact/coordination/interaction target "
                                 "paths",
            "continuity_requirements": "PERSISTENCE-class bound obligations",
            "state_before/state_after/phases/projection/recovery/"
            "world_response": "None unless the runtime supplies a structured "
                              "value (explicit unknown; never manufactured)",
            "roles": "None unless control semantics carry actor/object "
                    "identity (real runtime provides categories only)",
        },
        "never_manufactured": [
            "actor identities", "phase names", "state values",
            "projection values", "recovery actions", "world-response values",
        ],
    }
    MATRIX.write_text(json.dumps(matrix_artifact, indent=1) + "\n")
    print(json.dumps({name: {
        "events": fx["generic_event_count"],
        "units": fx["structured_atomic_unit_count"],
        "interactions": fx["interaction_count"],
        "states": fx["state_transition_count"],
        "env_resp": fx["environment_response_count"],
        "recruited": fx["recruited_region_count"],
        "bound_regions": fx["regions_with_atomic_bindings"],
        "scoped": fx["scoped_placement_count"],
    } for name, fx in results.items()}, indent=1))
    print("policy_hashes:", {k: v[:16] for k, v in policy_hashes.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
