"""TC-2 step 1: full residual inventory replay across the 4 real-runtime fixtures.

Produces CPCS_RESIDUAL_MAPPING_LEDGER_v0.1.json with every unsupported
mapping's structured fields (no prose used for classification later).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lab.application.reasoning_treatment import FrozenRuntimeBackend, TreatmentAdapter
from lab.compiler.profiles import REPO_ROOT
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
    backend = FrozenRuntimeBackend()
    adapter = TreatmentAdapter(REPO_ROOT)
    ledger = {"artifact": "CPCS_RESIDUAL_MAPPING_LEDGER", "version": "v0.1",
              "fixtures": {}}
    from lab.application.tc2_classify import EXECUTABLE_BY_UT, NON_EXECUTABLE_BY_UT

    for name, text in FIXTURES.items():
        ic = build_intent_context(text, root=REPO_ROOT)
        packet = backend.plan(text, ic["normalized_intent"])
        translation = adapter.translate(packet)
        rows = []
        executable_total = 0
        hard_total = 0
        hard_represented = 0
        executable_represented = 0
        executable_unsupported = 0
        mapped_ids = {m["control_ids"][0] for m in translation.lineage.values()
                      if isinstance(m, dict) and m.get("control_ids")}
        duplicate_ids = {d["control_id"] for d in translation.duplicate_semantics}
        for m in translation.unsupported_mappings:
            control = next((c for c in packet["proposed_controls"]
                            if c["control_id"] == m["control_id"]), {})
            ut = (control.get("control_semantics") or {}).get("universal_type")
            rows.append({
                "control_id": m["control_id"],
                "control_type": control.get("control_type", []),
                "control_family": control.get("control_family",
                                              control.get("source", "EVIDENCE_DERIVED")),
                "hardness": control.get("hardness", "SOFT"),
                "target": control.get("target", "scene"),
                "scope": control.get("scope", "scene"),
                "universal_type": ut,
                "requirement_ids": m["requirement_ids"],
                "evidence_ids": m["evidence_ids"],
                "rejection_reason": m["reason"],
                "effect_on_score": m["effect_on_score"],
            })
        for c in packet["proposed_controls"]:
            ut = (c.get("control_semantics") or {}).get("universal_type")
            if ut in EXECUTABLE_BY_UT and EXECUTABLE_BY_UT[ut] in (
                    "cpcs.continuity.invariant", "cpcs.constraint.negative"):
                executable_total += 1
                if c["control_id"] in mapped_ids or c["control_id"] in duplicate_ids:
                    executable_represented += 1
                else:
                    executable_unsupported += 1
            if c.get("hardness") == "HARD":
                hard_total += 1
                if c["control_id"] in mapped_ids or c["control_id"] in duplicate_ids:
                    hard_represented += 1
        ledger["fixtures"][name] = {
            "residuals": rows, "count": len(rows),
            "structured_mapped": len(translation.structured_objects),
            "duplicates_suppressed": len(translation.duplicate_semantics),
            "executable_total": executable_total,
            "executable_represented": executable_represented,
            "executable_unsupported": executable_unsupported,
            "hard_total": hard_total,
            "hard_represented": hard_represented,
        }
    out = Path(__file__).resolve().parent / "CPCS_RESIDUAL_MAPPING_LEDGER_v0.1.json"
    out.write_text(json.dumps(ledger, indent=1,
                              default=lambda o: o.decode("utf-8", "replace")
                              if isinstance(o, bytes) else str(o)))
    for name, fx in ledger["fixtures"].items():
        print(name, "residuals:", fx["count"])
    print("written:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
