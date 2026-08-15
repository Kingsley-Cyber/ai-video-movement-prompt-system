"""DR-1 artifact materializer: affordance ledgers, fixtures, A/B results."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lab.application.cpcs_deliberation import (
    DeliberationEngine,
    FAKE_SNAPSHOT,
    NON_EXECUTABLE_AFFORDANCES,
    PLANNING_AFFORDANCES,
)
from lab.application.reasoning_treatment import FakeBackend

OUT = Path(__file__).resolve().parent

FIXTURES = {
    "trivial": "person walks through a room",
    "contact": "A holds B's wrist while circling behind him",
    "contact_transfer": "A catches B's arm, switches grip, then releases",
    "possession": "she carries a glass while turning",
    "transfer": "he takes the object from her",
    "support": "one fighter catches the other before they fall",
    "occlusion": "interaction continues behind a pillar",
    "causal": "impact knocks the table and the glass falls",
    "camera": "camera circles while the actors grapple",
    "anime": "stylized multi-phase combat with impact holds",
    "performance": "she realizes he is lying but tries not to show it",
    "ambiguous": "he defeats him at the end",
    "cross_domain": "contact plus camera plus style plus environment consequence",
    "ideation": "I want a desperate fight where the hero barely wins",
    "failure": "make a complex grapple that doesn't fall apart",
}


def main() -> int:
    # --- affordance ledgers from TC-2 residual ledger (unique objects) ---
    residual = json.loads((OUT / "CPCS_RESIDUAL_MAPPING_LEDGER_v0.1.json").read_text())
    unique: dict[str, dict] = {}
    for fx in residual["fixtures"].values():
        for r in fx["residuals"]:
            unique.setdefault(r["control_id"], r)
    non_exec = []
    planning = []
    for r in unique.values():
        ut = r["universal_type"] or ""
        if ut in NON_EXECUTABLE_AFFORDANCES:
            non_exec.append({
                "object_id": r["control_id"],
                "universal_type": ut,
                "tc2_disposition": "NON_EXECUTABLE_KNOWLEDGE",
                "reasoning_affordances": NON_EXECUTABLE_AFFORDANCES[ut],
                "requirement_ids": r["requirement_ids"],
                "evidence_ids": r["evidence_ids"],
                "forbidden_from": ["canonical score fields", "generation controls",
                                   "provider carriers"],
            })
        elif ut in PLANNING_AFFORDANCES:
            planning.append({
                "object_id": r["control_id"],
                "universal_type": ut,
                "tc2_disposition": "PLANNING_ONLY",
                "planning_affordances": PLANNING_AFFORDANCES[ut],
                "consumed_by": "DeliberationEngine (query steering, stopping, ordering)",
                "forbidden_from": ["canonical score fields", "generation controls"],
            })
    (OUT / "CPCS_REASONING_AFFORDANCE_LEDGER_v0.1.json").write_text(json.dumps({
        "artifact": "CPCS_REASONING_AFFORDANCE_LEDGER", "version": "v0.1",
        "non_executable_objects": non_exec,
        "summary": {"total": len(non_exec),
                    "all_have_reasoning_disposition": bool(non_exec)},
    }, indent=1))
    (OUT / "CPCS_PLANNING_AFFORDANCE_LEDGER_v0.1.json").write_text(json.dumps({
        "artifact": "CPCS_PLANNING_AFFORDANCE_LEDGER", "version": "v0.1",
        "planning_objects": planning,
        "summary": {"total": len(planning),
                    "all_have_planning_disposition": bool(planning)},
    }, indent=1))

    # --- fixtures (hermetic deliberation runs) ---
    engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
    fixtures = {}
    for name, text in FIXTURES.items():
        out = engine.deliberate(text, {"intent": {}})
        closure = out["reasoning_closure_packet"]
        hypotheses = out["hypothesis_set"]["hypotheses"]
        fixtures[name] = {
            "request": text,
            "deliberation_id": out["deliberation_id"],
            "observations": len(out["observations"]),
            "hypotheses": len(hypotheses),
            "queries": len(out["query_steering_plan"]["queries"]),
            "safe_inferences": len(closure["safe_inferences"]),
            "creative_choices": len(closure["creative_choices"]),
            "contradicted": len(closure["contradicted_hypotheses"]),
            "completeness": closure["reasoning_completeness"],
            "closure_reason": closure["closure_reason"],
            "packet_hash": out["packet_hash"],
        }
        if name == "ideation":
            ideation = engine.ideate(text, {"intent": {}})
            fixtures[name]["ideation_candidates"] = len(ideation["candidates"])
    (OUT / "CPCS_DELIBERATION_FIXTURES_v0.1.json").write_text(json.dumps({
        "artifact": "CPCS_DELIBERATION_FIXTURES", "version": "v0.1",
        "fixtures": fixtures,
    }, indent=1))

    # --- A/B: A = baseline (no deliberation) vs B = deliberation ---
    ab = {"artifact": "CPCS_DELIBERATION_AB_RESULTS", "version": "v0.1",
          "arms": {}}
    for name, text in FIXTURES.items():
        out = engine.deliberate(text, {"intent": {}})
        closure = out["reasoning_closure_packet"]
        arm_b = {
            "hypotheses_proposed": len(out["hypothesis_set"]["hypotheses"]),
            "hypotheses_grounded": sum(1 for h in out["hypothesis_set"]["hypotheses"]
                                       if h["status"] in ("SUPPORTED", "WEAKLY_SUPPORTED")),
            "requirements_discovered": len(closure["resolved_requirements"]),
            "failure_risks_discovered": len(closure["predicted_failures"]),
            "prerequisites_discovered": sum(
                1 for h in out["hypothesis_set"]["hypotheses"]
                if h["hypothesis_type"] == "CAUSAL_HYPOTHESIS"),
            "queries_issued": len(out["query_steering_plan"]["queries"]),
            "safe_inferences": len(closure["safe_inferences"]),
            "creative_questions": len(closure["creative_choices"]),
            "unresolved_critical_gaps": closure["reasoning_completeness"] != "COMPLETE",
            "clarification_efficiency": 1.0 if not closure["creative_choices"] else
            1.0 / (1 + len(closure["creative_choices"])),
            "reasoning_completeness": closure["reasoning_completeness"],
        }
        ab["arms"][name] = {
            "A_CURRENT_BASELINE": {
                "hypotheses_proposed": 0, "hypotheses_grounded": 0,
                "requirements_discovered": 0, "failure_risks_discovered": 0,
                "prerequisites_discovered": 0, "queries_issued": 0,
                "safe_inferences": 0, "creative_questions": 0,
                "unresolved_critical_gaps": None,
                "clarification_efficiency": None,
                "reasoning_completeness": "N/A (no deliberation layer)",
            },
            "B_CPCS_DELIBERATION_V1": arm_b,
        }
    (OUT / "CPCS_DELIBERATION_AB_RESULTS_v0.1.json").write_text(
        json.dumps(ab, indent=1))
    print("non-executable objects:", len(non_exec), "| planning objects:", len(planning))
    for name, fx in fixtures.items():
        print(f"  {name:<18} H:{fx['hypotheses']} Q:{fx['queries']} "
              f"safe:{fx['safe_inferences']} creative:{fx['creative_choices']} "
              f"{fx['completeness']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
