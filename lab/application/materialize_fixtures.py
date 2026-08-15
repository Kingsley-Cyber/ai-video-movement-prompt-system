"""Deterministic no-provider A/B + repair fixture materialization (hermetic).

Produces CPCS_REASONING_AB_FIXTURES_v0.1.json and
CPCS_REPAIR_GAP_FIXTURES_v0.1.json using FakeBackend and the real
existing compiler (make_score_request/resolve_score/make_build_request).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lab.application import reasoning_treatment as rt
from lab.application.reasoning_treatment import (
    DiscrepancyBuilder,
    FakeBackend,
    RepairPlanner,
    TreatmentAdapter,
    handler_reasoning_experiment_prepare,
    handler_repair_gap_prepare,
    handler_repair_plan,
)
from lab.compiler.profiles import REPO_ROOT

AB_FIXTURES = {
    "simple_single_actor_motion": "A runner sprints across a field, decelerates, and stops.",
    "multi_actor_persistent_contact": ("She grabs his wrist while he is holding a glass, "
                                       "pulls him around, the glass spills, and the camera "
                                       "circles them."),
    "object_possession_transfer": "He passes the box to her; she takes it with both hands.",
    "occlusion_continuity": ("A hand disappears behind a pillar mid-grab and re-emerges "
                             "holding the object."),
    "camera_moving_during_interaction": ("Two people argue while the camera orbits them "
                                         "and one gestures sharply."),
    "style_performance": "Render the same action in anime sakuga style with exaggerated anticipation.",
    "material_consequence": ("A glass of water tips over on a wooden table; the water "
                             "spreads and the wood darkens."),
    "multi_shot_editing": ("A three-shot sequence: close-up of hands, wide establishing, "
                           "then a match cut to the same pose in a different room."),
    "trivial": "A plain wide shot of an empty room for two seconds.",
}

REPAIR_CASES = {
    "repair_contact_early_release": {
        "expected_states": [{
            "requirement_id": "REQ-CONTACT-PERSIST", "expected_value": "held",
            "expected_condition": "contact persists through the full pivot",
            "time_scope": "pivot interval", "objectives": ["OBJ-CONTACT-CONTINUITY"],
            "failure_family_if_violated": ["FF-CONTACT"], "criticality": "critical"}],
        "observations": [{"requirement_id": "REQ-CONTACT-PERSIST",
                          "observation_id": "obs_rel_1", "observed_value": "released"}],
        "user_complaint": "the hand let go halfway through the turn",
    },
    "repair_possession_hand_swap": {
        "expected_states": [{
            "requirement_id": "REQ-OWNERSHIP", "expected_value": "same_hand",
            "expected_condition": "the box stays with the same owner",
            "time_scope": "transfer", "objectives": ["OBJ-OWNERSHIP-CONTINUITY"],
            "failure_family_if_violated": ["FF-IDENTITY"], "criticality": "critical"}],
        "observations": [{"requirement_id": "REQ-OWNERSHIP",
                          "observation_id": "obs_swap_1", "observed_value": "swapped"}],
        "user_complaint": "the box jumped between her hands",
    },
    "repair_orientation_occlusion": {
        "expected_states": [{
            "requirement_id": "REQ-ORIENT", "expected_value": "left",
            "expected_condition": "orientation persists through occlusion",
            "time_scope": "occlusion interval", "objectives": ["OBJ-IDENTITY-CONTINUITY"],
            "failure_family_if_violated": ["FF-CONTINUITY"], "criticality": "critical"}],
        "observations": [{"requirement_id": "REQ-ORIENT",
                          "observation_id": "obs_side_1", "observed_value": "flipped"}],
        "user_complaint": None,
    },
}


def main() -> int:
    out_dir = Path(__file__).resolve().parent
    fake = FakeBackend()

    ab_fixtures = {}
    for name, text in AB_FIXTURES.items():
        with mock.patch.object(rt, "FrozenRuntimeBackend",
                               type("F", (rt.FrozenRuntimeBackend,), {
                                   "plan": lambda self, t, i, query_mode="INITIAL_GENERATION",
                                   discrepancy=None: fake.plan(t, i, query_mode=query_mode,
                                                               discrepancy=discrepancy)})):
            plan = handler_reasoning_experiment_prepare(
                {"flight_id": f"flight_ab_{name}", "intent_text": text,
                 "project_id": "cpcs-ab-project"}, REPO_ROOT)
        ab_fixtures[name] = {
            "experiment_id": plan["experiment_id"],
            "experiment_kind": plan["experiment_kind"],
            "shared_input_hash": plan["shared_input_hash"],
            "arm_a": {k: v for k, v in plan["arm_a"].items() if k != "build_request"},
            "arm_b": {k: v for k, v in plan["arm_b"].items() if k != "build_request"},
            "delta": {
                "overlay_ids_b": plan["arm_b"]["overlay_ids"],
                "unsupported_mappings_b": len(plan["arm_b"]["unsupported_mappings"]),
            },
            "confounder_check": plan["confounder_check"],
            "shared_downstream_compiler": plan["shared_downstream_compiler"],
            "shared_evaluation_path": plan["shared_evaluation_path"],
            "differences_before_treatment": plan["differences_before_treatment"],
        }

    repair_fixtures = {}
    for name, case in REPAIR_CASES.items():
        discrepancy = DiscrepancyBuilder().build(
            case["expected_states"], case["observations"],
            user_complaint=case["user_complaint"])
        intent = {"intent": {"primary_domain": "action"}}
        plan = RepairPlanner().plan(discrepancy, fake,
                                    "She grabs his wrist and turns.", intent)
        repair_fixtures[name] = {
            "discrepancy_packet": discrepancy,
            "repair_control_plan": plan,
            "lineage": plan["lineage"],
        }

    (out_dir / "CPCS_REASONING_AB_FIXTURES_v0.1.json").write_text(
        json.dumps({"artifact": "CPCS_REASONING_AB_FIXTURES", "version": "v0.1",
                    "fixtures": ab_fixtures}, indent=1))
    (out_dir / "CPCS_REPAIR_GAP_FIXTURES_v0.1.json").write_text(
        json.dumps({"artifact": "CPCS_REPAIR_GAP_FIXTURES", "version": "v0.1",
                    "fixtures": repair_fixtures}, indent=1))
    print("ab fixtures:", ", ".join(f"{k}:{v['arm_b']['reasoning_policy']}"
                                    for k, v in ab_fixtures.items()))
    print("repair fixtures:", ", ".join(repair_fixtures))
    print("written to", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
