"""KA-2.1/2.2 diagnostics — computed workflow recruitment matrix.

Hermetic mode: FakeBackend(corpus_slice=True) + FAKE_SNAPSHOT writes
WORKFLOW_RECRUITMENT_MATRIX.json.

KA-2.3 PRE-POLICY sweep mode (--real-runtime): one shared
FrozenRuntimeBackend + frozen snapshot across the 11 workflows writes the
IMMUTABLE baseline WORKFLOW_RECRUITMENT_MATRIX_REAL_v0.1.json with
region merge diagnostics (sizes, merge evidence, bridge typology) plus
git commit, merge-policy snapshot, and content hash. The script refuses
to overwrite the baseline artifact once it exists.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
from lab.application.cpcs_knowledge_application import apply_knowledge
from lab.application.cpcs_knowledge_awareness import build_awareness_profile
from lab.application.cpcs_knowledge_constellation import assemble_constellation
from lab.application.cpcs_knowledge_placement import (
    assemble_directing_modules,
    build_placement,
    decompose_atomic_units,
)
from lab.application.cpcs_knowledge_recruitment import recruit_for_intent
from lab.application.reasoning_treatment import FakeBackend, TreatmentAdapter
from lab.compiler.profiles import REPO_ROOT

OUT = Path(__file__).resolve().parent
ARTIFACT = OUT / "WORKFLOW_RECRUITMENT_MATRIX.json"
REAL_ARTIFACT = OUT / "WORKFLOW_RECRUITMENT_MATRIX_REAL_v0.1.json"

WORKFLOW_INTENTS: dict[str, str] = {
    "GENERAL_VIDEO": "A calm wide shot of a quiet street at dusk.",
    "ACTION_FIGHT": ("A fighter catches an opponent's leg, swings him in a "
                     "wide arc, releases him onto the water, then immediately "
                     "pressures him while he tries to recover."),
    "UGC": ("A woman records a casual handheld creator video trying a premium "
            "facial serum. She picks the bottle up from the bathroom counter, "
            "turns it so the label is visible, unscrews the dropper, dispenses "
            "two drops on the back of her other hand, rubs the serum between "
            "her fingers, applies it to her cheek, notices the texture, reacts "
            "positively, talks naturally to the viewer, then brings the bottle "
            "near the phone camera for the final product shot."),
    "ECOMMERCE_PRODUCT_DEMO": ("A luxury watch slowly rotates on a display "
                               "stand while light sweeps across its dial."),
    "UGC_ECOMMERCE": ("A creator handholds the camera while unboxing a "
                      "premium serum bottle for a vlog review."),
    "HUMAN_PERFORMANCE_DIALOGUE": ("Two actors exchange a quiet line in a "
                                   "close-up two-shot, with subtle "
                                   "micro-reactions."),
    "OBJECT_MANIPULATION": ("A pair of hands assembles a small mechanical "
                            "keyboard on a desk."),
    "COOKING_PROCEDURAL": ("A chef slices a tomato on a wooden board."),
    "VEHICLE_ENVIRONMENT": ("A car drives through a puddle on a city street."),
    "CAMERA_ENVIRONMENT_ONLY": ("A drone camera orbits a coastal cliff with "
                                "no performer visible."),
    "NEGATIVE_PRODUCT_ONLY": ("Macro product-only serum bottle rotating "
                              "slowly on a pedestal. No person is visible."),
}


def _run_one(intent_text: str, backend: Any, snapshot: Any) -> dict[str, Any]:
    engine = DeliberationEngine(snapshot, backend)
    activation, packet = engine.activate(
        intent_text, {"intent": {"primary_domain": "action"}}, observations=[])
    awareness = build_awareness_profile(intent_text, activation=activation)
    translation = TreatmentAdapter(REPO_ROOT).translate(
        packet, snapshot=snapshot, activation=activation)
    app_set = translation.application_set or {}
    applications = app_set.get("applications", []) if isinstance(
        app_set, dict) else getattr(app_set, "applications", [])
    evidence_by_id = {ev["atomic_record_id"]: ev
                      for ev in packet.get("retrieved_evidence", []) or []
                      if ev.get("atomic_record_id")}
    constellation = assemble_constellation(
        app_set, activation, evidence_by_id=evidence_by_id)
    pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in applications}
    recruitment = recruit_for_intent(
        constellation, activation, pack_lookup=pack_lookup,
        awareness=awareness.to_dict())
    from lab.application.cpcs_knowledge_refinement import (
        assess_prerequisites,
        build_refinement_packet,
    )
    new_pre, gaps = assess_prerequisites(
        recruitment, constellation, activation, pack_lookup=pack_lookup)
    refinement = build_refinement_packet(
        recruitment, constellation, activation, new_prerequisites=new_pre,
        coverage_gaps=gaps, application_set=app_set)
    units = decompose_atomic_units(translation.structured_objects)
    placement = build_placement(recruitment, constellation, units,
                                pack_lookup=pack_lookup)
    modules = assemble_directing_modules(
        placement, units, refinement, pack_lookup=pack_lookup,
        constellation=constellation)

    counts = {name: 0 for name in
              ("RECRUIT", "CONTEXT", "ARCHIVE", "UNRESOLVED")}
    for d in recruitment["dispositions"]:
        counts[d["disposition"]] = counts.get(d["disposition"], 0) + 1
    scope_distribution: dict[str, int] = {}
    lifetime_distribution: dict[str, int] = {}
    emission_distribution: dict[str, int] = {}
    placement_failures: list[str] = []
    for p in placement:
        scope_distribution[p.target_scope] = \
            scope_distribution.get(p.target_scope, 0) + 1
        lifetime_distribution[p.lifetime] = \
            lifetime_distribution.get(p.lifetime, 0) + 1
        emission_distribution[p.emission_policy] = \
            emission_distribution.get(p.emission_policy, 0) + 1
        if p.target_scope != "GLOBAL" and not p.target_unit_ids:
            placement_failures.append(
                f"{p.region_id}:scoped_without_units")
    gap_classes: dict[str, int] = {}
    for gap in refinement.get("coverage_gaps", []) or []:
        gap_classes[gap.get("gap_class", "RECRUITMENT_FAILURE")] = \
            gap_classes.get(gap.get("gap_class", "RECRUITMENT_FAILURE"), 0) + 1
    return {
        "intent": intent_text,
        "workflow_tags": [t["tag"] for t in awareness.active_workflow_tags],
        "candidate_expertise_tags": [t["tag"]
                                      for t in awareness.candidate_expertise_tags],
        "universal_considerations": len(awareness.universal_considerations),
        "predicted_failure_families": awareness.predicted_failure_families,
        "principle_packs": len(applications),
        "regions": len(constellation.regions),
        "region_diagnostics": _region_diagnostics(constellation),
        "dispositions": counts,
        "coverage_gaps": len(refinement.get("coverage_gaps", []) or []),
        "gap_classes": gap_classes,
        "prerequisites_discovered": len(
            refinement.get("new_prerequisite_requirements", []) or []),
        "atomic_units": [u.to_dict() for u in units],
        "region_to_unit_bindings": [
            {"region_id": p.region_id, "target_scope": p.target_scope,
             "target_unit_ids": p.target_unit_ids, "role": p.placement_role,
             "lifetime": p.lifetime, "emission": p.emission_policy,
             "disposition": p.disposition, "reasons": p.reason_codes}
            for p in placement
        ],
        "scope_distribution": scope_distribution,
        "lifetime_distribution": lifetime_distribution,
        "emission_distribution": emission_distribution,
        "modules": modules["counts"],
        "placement_failures": placement_failures,
        "reasoning_only_regions": modules.get("reasoning_only_region_ids", []),
        "verification_only_regions": modules.get("verification_only_region_ids",
                                                 []),
        "planning_guidance_consumed": len(
            refinement.get("planning_guidance", []) or []),
        "non_executable_consumed": len(
            refinement.get("non_executable_knowledge_used", []) or []),
        "awareness_profile_hash": awareness.profile_hash,
        "recruitment_hash": recruitment.get("recruitment_hash"),
    }


def _region_diagnostics(constellation: Any) -> dict[str, Any]:
    """Per-region merge explanation for the sweep (KA-2.3 instrumentation)."""
    regions_out: list[dict[str, Any]] = []
    for r in constellation.regions:
        diag = r.get("diagnostics", {}) or {}
        regions_out.append({
            "region_id": r["region_id"],
            "pack_count": len(r.get("pack_ids", []) or []),
            "orphan": diag.get("orphan"),
            "seed_pack_id": diag.get("seed_pack_id"),
            "strength_breakdown": diag.get("strength_breakdown"),
            "merge_evidence": diag.get("merge_evidence", []),
            "principle_families": r.get("principle_families", []),
            "facet_counts": {
                "canonical_concept_ids": len(r.get("canonical_concept_ids", []) or []),
                "trigger_ids": len(r.get("trigger_ids", []) or []),
                "objective_ids": len(r.get("objective_ids", []) or []),
                "failure_family_ids": len(r.get("failure_family_ids", []) or []),
                "requirement_ids": len(r.get("requirement_ids", []) or []),
                "corpus_doc_ids": len(r.get("corpus_doc_ids", []) or []),
            },
        })
    sizes = sorted((r["pack_count"] for r in regions_out), reverse=True)
    bridges = (getattr(constellation, "diagnostics", {}) or {}).get(
        "bridges", []) or []
    bridge_kinds: dict[str, int] = {}
    for b in bridges:
        key = f"{b.get('kind')}:{b.get('strength')}"
        bridge_kinds[key] = bridge_kinds.get(key, 0) + 1
    return {
        "region_count": len(regions_out),
        "region_sizes": sizes,
        "max_region_size": sizes[0] if sizes else 0,
        "regions": regions_out,
        "bridge_counts_by_kind": dict(sorted(bridge_kinds.items())),
        "bridge_count": len(bridges),
        "bridge_density": round(
            len(bridges) / max(len(regions_out), 1), 3),
        "merge_policy_snapshot": (getattr(constellation, "diagnostics", {})
                                  or {}).get("merge_policy_snapshot", {}),
    }


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
        capture_output=True, text=True, check=True)
    return result.stdout.strip()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--real-runtime", action="store_true",
                        help="Run the PRE-POLICY sweep against the frozen "
                             "runtime and write the immutable baseline "
                             "WORKFLOW_RECRUITMENT_MATRIX_REAL_v0.1.json")
    parser.add_argument("--artifact-name", default=None,
                        help="Override the real-sweep artifact filename "
                             "(for the POST-POLICY sweep; the pre-policy "
                             "baseline stays immutable)")
    args = parser.parse_args()
    if args.real_runtime:
        return _main_real(args.artifact_name)
    backend = FakeBackend(corpus_slice=True)
    fixtures: dict[str, Any] = {}
    for name, intent in WORKFLOW_INTENTS.items():
        fixtures[name] = _run_one(intent, backend, FAKE_SNAPSHOT)
    artifact = {
        "artifact": "CPCS_WORKFLOW_RECRUITMENT_MATRIX",
        "version": "v0.1",
        "backend": "hermetic_corpus_slice",
        "workflows": fixtures,
    }
    ARTIFACT.write_text(json.dumps(artifact, indent=1) + "\n")
    print(json.dumps({
        name: {
            "tags": fx["workflow_tags"],
            "candidates": len(fx["candidate_expertise_tags"]),
            "dispositions": fx["dispositions"],
            "gaps": fx["coverage_gaps"],
            "prereqs": fx["prerequisites_discovered"],
            "units": len(fx["atomic_units"]),
            "emission": fx["modules"],
        } for name, fx in fixtures.items()
    }, indent=1))
    return 0


def _main_real(artifact_name: str | None = None) -> int:
    """PRE-POLICY baseline sweep: immutable artifact, refuse to overwrite.

    POST-POLICY sweeps use --artifact-name to write a NEW artifact; the
    pre-policy baseline is never rewritten."""
    target = REAL_ARTIFACT if not artifact_name else OUT / artifact_name
    if target.is_file():
        print(f"REFUSED: baseline artifact already exists at {target} "
              "(immutable pre-policy baseline; policy changes require a NEW "
              "post-policy artifact).")
        return 1
    from lab.application.cpcs_deliberation import frozen_knowledge_snapshot
    from lab.application.reasoning_treatment import FrozenRuntimeBackend

    snapshot = frozen_knowledge_snapshot()
    backend = FrozenRuntimeBackend()
    fixtures: dict[str, Any] = {}
    for name, intent in WORKFLOW_INTENTS.items():
        fixtures[name] = _run_one(intent, backend, snapshot)
    body = {
        "workflows": fixtures,
    }
    content_hash = hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    artifact = {
        "artifact": "CPCS_WORKFLOW_RECRUITMENT_MATRIX_REAL",
        "version": "v0.1",
        "backend": "real_frozen_runtime",
        "method": "activate + treatment translate per workflow (no provider)",
        "immutable": True,
        "phase": ("PRE_POLICY_BASELINE" if not artifact_name
                  else "POST_POLICY"),
        "git_commit": _git_commit(),
        "content_hash": content_hash,
        **body,
    }
    target.write_text(json.dumps(artifact, indent=1) + "\n")
    print(json.dumps({
        name: {
            "tags": fx["workflow_tags"],
            "regions": fx["regions"],
            "region_sizes": fx["region_diagnostics"]["region_sizes"][:6],
            "max_region_size": fx["region_diagnostics"]["max_region_size"],
            "bridges": fx["region_diagnostics"]["bridge_counts_by_kind"],
            "dispositions": fx["dispositions"],
            "gaps": fx["coverage_gaps"],
            "units": len(fx["atomic_units"]),
            "emission": fx["modules"],
        } for name, fx in fixtures.items()
    }, indent=1))
    print(f"wrote {target} | commit {artifact['git_commit']} | "
          f"hash {content_hash[:24]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
