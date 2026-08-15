"""Real frozen-runtime integration test + deterministic no-provider A/B report.

Requires CPCS_FROZEN_RUNTIME_PATH to point at the frozen runtime dir.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lab.application.reasoning_treatment import (
    FrozenRuntimeBackend,
    TreatmentAdapter,
)
from lab.compiler.build import make_build_request
from lab.compiler.profiles import REPO_ROOT
from lab.compiler.score import make_score_request, resolve_score
from lab.second_brain.src.intent import build_intent_context

FIXTURES = {
    "multi_actor_contact": (
        "She grabs his wrist while he is holding a glass, pulls him around, "
        "the glass spills, and the camera circles them."),
    "possession_transfer": (
        "He passes the box to her; she takes it with both hands."),
    "camera_occlusion": (
        "A hand disappears behind a pillar mid-grab and re-emerges holding "
        "the object while the camera orbits."),
    "trivial": "A plain wide shot of an empty room for two seconds.",
}


def main() -> int:
    t0 = time.perf_counter()
    backend = FrozenRuntimeBackend()
    adapter = TreatmentAdapter(REPO_ROOT)
    report = {"fixtures": {}, "frozen_runtime_path": backend.runtime_path,
              "duration_s": None}
    for name, text in FIXTURES.items():
        ic = build_intent_context(text, root=REPO_ROOT)
        intent = ic["normalized_intent"]
        p1 = backend.plan(text, intent)
        p2 = backend.plan(text, intent)
        assert p1["packet_hash"] == p2["packet_hash"], "packet non-deterministic"
        translation = adapter.translate(p1)
        score_a = resolve_score(make_score_request(ic, overlays=[]), REPO_ROOT)
        score_b = resolve_score(make_score_request(ic, overlays=translation.overlays),
                                REPO_ROOT)
        score_b["verification_requirements"] = list(
            score_b.get("verification_requirements", [])
        ) + translation.verification_requirements
        score_b["provider_neutral_controls"] = list(
            score_b.get("provider_neutral_controls", [])
        ) + translation.provider_neutral_controls
        score_b["warnings"] = list(score_b.get("warnings", [])) + translation.warnings
        from lab.application.reasoning_treatment import apply_structured_objects
        apply_structured_objects(score_b, translation.structured_objects)
        build_b = make_build_request(score_b, project_id="cpcs-ab-project")
        report["fixtures"][name] = {
            "treatment_packet_id": p1["treatment_id"],
            "treatment_packet_hash": p1["packet_hash"],
            "query_mode": p1["query_mode"],
            "architecture_freeze_identity": p1["architecture_freeze_identity"],
            "retrieval_runtime_freeze_identity": p1["retrieval_runtime_freeze_identity"],
            "requirements": {
                "mandatory": p1["mandatory_requirements"],
                "conditional": p1["conditional_requirements"],
                "required_pathways": p1["required_pathways"],
                "uncovered_mandatory": p1["uncovered_mandatory_requirements"],
                "status": "COMPLETE" if not p1["uncovered_mandatory_requirements"]
                else "INCOMPLETE",
            },
            "evidence": {
                "count": len(p1["retrieved_evidence"]),
                "ids": [e["atomic_record_id"] for e in p1["retrieved_evidence"]][:12],
            },
            "translation": {
                "overlay_ids": [o["overlay_id"] for o in translation.overlays],
                "overlay_count": len(translation.overlays),
                "structured_objects": len(translation.structured_objects),
                "structured_targets": sorted({o["target"] for o in
                                              translation.structured_objects}),
                "unsupported_mappings": len(translation.unsupported_mappings),
                "unsupported_control_ids": [m["control_id"] for m in
                                            translation.unsupported_mappings][:10],
                "verification_added": len(translation.verification_requirements),
                "controls_added": len(translation.provider_neutral_controls),
            },
            "ab_delta": {
                "baseline_verification": len(score_a.get("verification_requirements", [])),
                "treatment_verification": len(score_b.get("verification_requirements", [])),
                "baseline_controls": len(score_a.get("provider_neutral_controls", [])),
                "treatment_controls": len(score_b.get("provider_neutral_controls", [])),
                "overlays_b": [o["overlay_id"] for o in translation.overlays],
                "build_schema": build_b["schema"],
                "provider_neutral": build_b["score"]["score_id"] != "",
            },
            "deterministic": True,
        }
        print(f"[ok] {name}: mandatory={len(p1['mandatory_requirements'])} "
              f"evidence={len(p1['retrieved_evidence'])} "
              f"overlays={len(translation.overlays)} "
              f"unsupported={len(translation.unsupported_mappings)} "
              f"verif +{len(translation.verification_requirements)}")
    report["duration_s"] = round(time.perf_counter() - t0, 1)
    def sanitize(value):
        if isinstance(value, bytes):
            return value.decode("utf-8", "replace")
        if isinstance(value, dict):
            return {k: sanitize(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [sanitize(v) for v in value]
        if isinstance(value, (int, float, str, bool)) or value is None:
            return value
        return str(value)

    out = Path(__file__).resolve().parent / "CPCS_REASONING_AB_REPORT_v0.1.json"
    out.write_text(json.dumps(sanitize(report), indent=1))
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
