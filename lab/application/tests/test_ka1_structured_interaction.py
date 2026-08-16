"""WP-6 — structured interaction payload (hip toss canonical object).

Frozen evaluation fixture: input "A fighter performs a hip toss." — the
canonical output must contain contact interval, support state, causal phases,
actor roles, force transfer, precondition/postcondition, and recovery. An
output containing only action labels without state transitions is INVALID.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from lab.application.reasoning_treatment import (
    TreatmentAdapter,
    build_treatment_packet,
)
from lab.compiler import cpcs_typed
from lab.compiler.profiles import REPO_ROOT

OUT = Path(__file__).resolve().parents[1]

INTENT = "A fighter performs a hip toss."

# Combat fixture evidence ids (frozen corpus records; IDs only per D4):
#   ku30 force-transfer chain, ku33 contact failure taxonomy, ku23 beat
#   contract, ku29 contact interval, ku35 action phases, 02f support state,
#   03 material response.
EV_KU30 = ("continuous_combat_state_contact_coarticulation_anime_time_volumetric_"
           "cinematography::continuous_combat_state_contact_coarticulation_anime_"
           "time_volumetric_cinematography__ku30")
EV_KU33 = ("continuous_combat_state_contact_coarticulation_anime_time_volumetric_"
           "cinematography::continuous_combat_state_contact_coarticulation_anime_"
           "time_volumetric_cinematography__ku33")
EV_KU23 = ("continuous_combat_state_contact_coarticulation_anime_time_volumetric_"
           "cinematography::continuous_combat_state_contact_coarticulation_anime_"
           "time_volumetric_cinematography__ku23")
EV_KU29 = ("continuous_combat_state_contact_coarticulation_anime_time_volumetric_"
           "cinematography::continuous_combat_state_contact_coarticulation_anime_"
           "time_volumetric_cinematography__ku29")
EV_KU35 = ("continuous_combat_state_contact_coarticulation_anime_time_volumetric_"
           "cinematography::continuous_combat_state_contact_coarticulation_anime_"
           "time_volumetric_cinematography__ku35")
EV_SUPPORT = "02_facs_laban_bartenieff_gap_closure_completed::02f__support_state"
EV_MATERIAL = ("03_mx_hierarchical_motion_grammar_gap_closure_research::"
               "03__material_response")

COMBAT_EVIDENCE = [
    {"atomic_record_id": EV_KU30, "universal_type": "Principle",
     "supported_requirement_ids": ["REQ-CONTACT-1"],
     "failure_family_ids": ["FF-CONTACT"]},
    {"atomic_record_id": EV_KU33, "universal_type": "NegativeConstraint",
     "supported_requirement_ids": ["REQ-CONTACT-1"],
     "failure_family_ids": ["FF-CONTACT"]},
    {"atomic_record_id": EV_KU23, "universal_type": "Specification",
     "supported_requirement_ids": ["REQ-BEAT-1"],
     "failure_family_ids": []},
    {"atomic_record_id": EV_KU29, "universal_type": "Schema",
     "supported_requirement_ids": ["REQ-CONTACT-1"],
     "failure_family_ids": []},
    {"atomic_record_id": EV_KU35, "universal_type": "Schema",
     "supported_requirement_ids": ["REQ-PHASE-1"],
     "failure_family_ids": []},
    {"atomic_record_id": EV_SUPPORT, "universal_type": "Schema",
     "supported_requirement_ids": ["REQ-SUPPORT-1"],
     "failure_family_ids": ["FF-SUPPORT"]},
    {"atomic_record_id": EV_MATERIAL, "universal_type": "Concept",
     "supported_requirement_ids": ["REQ-WORLD-1"],
     "failure_family_ids": []},
]

HIP_TOSS_CONTROL = {
    "control_id": "ctl_hip_toss_001",
    "control_type": ["CT-CONTACT-CONTRACT"],
    "target": "actor", "scope": "beat", "hardness": "HARD",
    "source": "EVIDENCE_DERIVED",
    "source_requirement_ids": ["REQ-CONTACT-1", "REQ-SUPPORT-1", "REQ-BEAT-1"],
    "supporting_evidence_ids": [EV_KU30, EV_KU33, EV_KU23, EV_KU29, EV_KU35,
                                EV_SUPPORT, EV_MATERIAL],
    "protected_objectives": ["OBJ-THROW"],
    "prevented_failure_families": ["FF-CONTACT", "FF-SUPPORT"],
    "control_semantics": {"statement": "hip toss throw contract",
                          "universal_type": "Constraint"},
    "_roles": {"attacker": "fighter_a", "defender": "fighter_b",
               "initiative": "fighter_a"},
    "_state_before": {"attacker_support": "stable", "defender_support": "stable",
                      "grip": "hip_grip", "balance": "stable"},
    "_contact_interval": {"interval_s": [1.5, 2.5],
                          "mode_sequence": ["impact", "pivot", "support"]},
    "_phases": [
        {"action": "underhook_hip_placement", "support_shift": "lateral",
         "com_displacement": "none", "grip_persists": True, "support_lost": False},
        {"action": "forward_pull", "support_shift": "forward",
         "com_displacement": "displaced", "grip_persists": True,
         "support_lost": False},
        {"action": "load_bearing", "support_shift": "none",
         "com_displacement": "lowered", "grip_persists": True, "support_lost": True},
        {"action": "projection", "support_shift": "none",
         "com_displacement": "displaced", "grip_persists": False,
         "support_lost": True},
    ],
    "_projection": {"rotation_axis": "single_axis",
                    "rotating_actor": "defender_only",
                    "force_vector": {"direction": "forward_down",
                                     "magnitude": "body_weight"}},
    "_state_after": {
        "defender": {"momentum": "reduced", "orientation": "changed",
                     "balance": "unstable"},
        "attacker": {"balance": "stable"},
    },
    "_recovery": {"allowed": ["plant_hand", "spin_out"],
                  "forbidden": ["mirrored_rotation"]},
    "_world_response": {"water": {"deformation": "splash",
                                  "drag": "velocity_reduction"}},
    "action": "add",
}

# A control carrying only an action label: no roles/phases/state transitions.
ACTION_LABEL_ONLY_CONTROL = {
    "control_id": "ctl_action_label_only",
    "control_type": ["CT-CONTACT-CONTRACT"],
    "target": "actor", "scope": "beat", "hardness": "SOFT",
    "source": "EVIDENCE_DERIVED",
    "source_requirement_ids": ["REQ-BEAT-1"],
    "supporting_evidence_ids": [],
    "protected_objectives": [],
    "prevented_failure_families": [],
    "control_semantics": {"statement": "a throw happens", "universal_type": "Concept"},
    "action": "add",
}


def make_packet(controls, intent=INTENT):
    return build_treatment_packet(
        treatment_id="treatment_fixture",
        source_intent_hash="fixture",
        query_mode="INITIAL_GENERATION",
        activated_requirements=["REQ-CONTACT-1", "REQ-SUPPORT-1", "REQ-BEAT-1"],
        mandatory_requirements=["REQ-CONTACT-1"],
        conditional_requirements=["REQ-SUPPORT-1", "REQ-BEAT-1"],
        required_pathways={"REQ-CONTACT-1": "covered"},
        objectives_at_risk=["OBJ-THROW"],
        predicted_failure_families=["FF-CONTACT", "FF-SUPPORT"],
        retrieved_evidence=COMBAT_EVIDENCE,
        proposed_obligations=[],
        proposed_controls=controls,
        verification_obligations=[],
        unknowns=[],
        uncovered_mandatory_requirements=[],
        architecture_freeze_identity="fixture",
        retrieval_runtime_freeze_identity="fixture",
    )


def _enum_leaf_allowed(value) -> bool:
    if value is None or isinstance(value, bool) or isinstance(value, (int, float)):
        return True
    if isinstance(value, list):
        return all(_enum_leaf_allowed(item) for item in value)
    if isinstance(value, dict):
        return all(_enum_leaf_allowed(v) for v in value.values())
    return isinstance(value, str)


class Ka1StructuredInteraction(unittest.TestCase):

    def _translated_interaction(self, control):
        packet = make_packet([control])
        translation = TreatmentAdapter(REPO_ROOT).translate(packet)
        interactions = [o for o in translation.structured_objects
                        if o.get("target") == "interactions[]"]
        self.assertTrue(interactions, "no interaction structured object produced")
        return interactions[0]["value"]

    def test_hip_toss_canonical_output_contains_state_transitions(self):
        value = self._translated_interaction(HIP_TOSS_CONTROL)
        self.assertEqual(
            cpcs_typed.validate_structured_interaction(value), [],
            "hip toss payload failed the state-transition gate")
        # contact interval
        interval = value.get("contact", {}).get("contact_interval")
        self.assertIsNotNone(interval)
        self.assertTrue(interval.get("mode_sequence"))
        # support state
        self.assertEqual(value["state_before"]["attacker_support"], "stable")
        self.assertEqual(value["state_before"]["defender_support"], "stable")
        # causal phases with state transitions
        phases = value["phases"]
        self.assertEqual(len(phases), 4)
        for phase in phases:
            self.assertTrue(any(phase.get(key) is not None for key in
                                ("support_shift", "com_displacement",
                                 "grip_persists", "support_lost")),
                            f"phase without state transitions: {phase}")
        # actor roles
        self.assertEqual(value["roles"]["attacker"], "fighter_a")
        self.assertEqual(value["roles"]["defender"], "fighter_b")
        self.assertIn("initiative", value["roles"])
        # force transfer
        force = value["projection"]["force_vector"]
        self.assertEqual(force["direction"], "forward_down")
        self.assertIsNotNone(force["magnitude"])
        # precondition / postcondition
        self.assertTrue(value["state_before"])
        self.assertTrue(value["state_after"])
        self.assertEqual(value["state_after"]["defender"]["balance"], "unstable")
        # recovery with mirrored-rotation forbidden
        self.assertIn("mirrored_rotation", value["recovery"]["forbidden"])
        self.assertEqual(value["projection"]["rotating_actor"], "defender_only")

    def test_action_labels_only_is_invalid(self):
        value = self._translated_interaction(ACTION_LABEL_ONLY_CONTROL)
        violations = cpcs_typed.validate_structured_interaction(value)
        self.assertTrue(violations,
                        "action-label-only output passed the gate (invalid)")
        codes = {v["code"] for v in violations}
        self.assertIn("missing_causal_phases", codes)
        self.assertIn("missing_actor_roles", codes)

    def test_structured_interaction_schema_conditional(self):
        schema = json.loads(
            (OUT / "CPCS_STRUCTURED_INTERACTION_SCHEMA_v0.1.json").read_text())
        validator = Draft202012Validator(schema)
        value = self._translated_interaction(HIP_TOSS_CONTROL)
        executed = {"executed": True, **value}
        self.assertEqual(list(validator.iter_errors(executed)), [])
        action_only = {"executed": True,
                       **self._translated_interaction(ACTION_LABEL_ONLY_CONTROL)}
        problems = list(validator.iter_errors(action_only))
        self.assertTrue(problems)

    def test_no_prose_reconstructed_into_values(self):
        value = self._translated_interaction(HIP_TOSS_CONTROL)
        payload = {key: value[key] for key in
                   ("roles", "state_before", "phases", "projection",
                    "state_after", "recovery", "world_response")}
        self.assertTrue(_enum_leaf_allowed(payload),
                        "payload leaf values must be enums/bools/numbers, "
                        "never reconstructed prose")

    def test_existing_interaction_keys_unchanged(self):
        value = self._translated_interaction(HIP_TOSS_CONTROL)
        for key in ("interaction_id", "participants", "interaction_type",
                    "contact", "temporal_scope", "phase_scope",
                    "continuity_requirements", "verification_refs", "lineage"):
            self.assertIn(key, value)
        self.assertEqual(
            value["contact"]["state_transition"]["enum"],
            cpcs_typed.SOURCE_VALUE_ENUMS["contact_state_transition"])


if __name__ == "__main__":
    unittest.main()
