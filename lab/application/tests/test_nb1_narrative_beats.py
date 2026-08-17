"""NB-1 — narrative beat + causal spine projection tests (hermetic)."""
from __future__ import annotations

import unittest

from lab.application.cpcs_knowledge_placement import AtomicUnit
from lab.application.cpcs_narrative_beats import (
    build_narrative_beat_graph,
    annotate_temporal_plan,
)
from lab.application.cpcs_temporal_director import build_temporal_plan

WATER_BOTTLE = (
    "A 15-second TikTok-style UGC video of a woman casually showing off a "
    "water bottle she actually uses every day. She picks it up, takes a "
    "drink, talks about why she likes it, and shows it to the camera at "
    "the end. It should feel natural and believable like a real creator "
    "filmed it on her phone, not like an ad."
)
FIGHT = (
    "A fighter catches an opponent's leg, swings him in a wide arc, "
    "releases him onto the water, then immediately pressures him while he "
    "tries to recover."
)


def _unit(uid, failures, evidence=("ev_x",)):
    return AtomicUnit(
        unit_id=uid, unit_kind="INTERACTION", scope="INTERACTION",
        interaction_id="i1", actor_refs=[], object_refs=[],
        state_transitions={},
        ordered_after=[],
        lineage={"si1_failure_family_ids": list(failures),
                 "evidence_ids": list(evidence), "source": "test"})


class Nb1NarrativeBeats(unittest.TestCase):

    def test_water_bottle_user_beats(self):
        graph = build_narrative_beat_graph(WATER_BOTTLE)
        displays = [b["display_name"] for b in graph.beats]
        for expected in ("PICK_UP", "DRINK", "APPRAISAL_DIALOGUE",
                         "PRODUCT_REVEAL"):
            self.assertIn(expected, displays)
        user = [b for b in graph.beats if b["origin"] == "USER_EXPLICIT"]
        self.assertEqual(len(user), 4)

    def test_fight_user_beats_and_derived_impact(self):
        graph = build_narrative_beat_graph(FIGHT)
        displays = {b["display_name"] for b in graph.beats}
        self.assertIn("CATCH", displays)
        self.assertIn("SWING", displays)
        self.assertIn("RELEASE", displays)
        self.assertIn("PRESSURE", displays)
        self.assertIn("RECOVERY", displays)
        self.assertIn("WATER_IMPACT", displays)
        derived = [b for b in graph.beats if b["display_name"] == "WATER_IMPACT"]
        self.assertEqual(len(derived), 1)
        self.assertEqual(derived[0]["origin"], "DERIVED_PREREQUISITE")
        self.assertIn("derived_from_beat", derived[0]["lineage"])

    def test_water_impact_edge_is_state_transition_not_causal(self):
        graph = build_narrative_beat_graph(FIGHT)
        kinds = {e["kind"] for e in graph.edges}
        self.assertIn("STATE_TRANSITION", kinds)
        self.assertIn("USER_SEQUENCE", kinds)
        self.assertNotIn("CAUSAL_REQUIRED", kinds,
                         "clause order must not become causation")

    def test_user_sequence_edges_follow_clause_order(self):
        graph = build_narrative_beat_graph(WATER_BOTTLE)
        user = sorted((b for b in graph.beats
                       if b["origin"] == "USER_EXPLICIT"),
                      key=lambda b: b["explicit_order_index"])
        seq = {e["from"]: e["to"] for e in graph.edges
               if e["kind"] == "USER_SEQUENCE"}
        self.assertEqual(len(seq), len(user) - 1)
        for i in range(len(user) - 1):
            self.assertEqual(seq[user[i]["beat_id"]],
                             user[i + 1]["beat_id"])

    def test_si1_units_bind_by_failure_overlap(self):
        units = [
            _unit("u_contact", ["FF-CONTACT", "FF-IDENTITY"]),
            _unit("u_liquid", ["FF-DEFORMATION", "FF-CONTACT"]),
            _unit("u_camera", ["FF-CAMERA", "FF-VISIBILITY"]),
        ]
        graph = build_narrative_beat_graph(WATER_BOTTLE, units=units)
        bound = {b["display_name"]: b["bound_si1_unit_ids"]
                 for b in graph.beats}
        self.assertIn("u_contact", bound["PICK_UP"])
        self.assertIn("u_liquid", bound["DRINK"])
        self.assertIn("u_camera", bound["PRODUCT_REVEAL"])
        # one unit -> one beat (best overlap)
        all_bound = [uid for b in graph.beats
                     for uid in b["bound_si1_unit_ids"]]
        self.assertEqual(len(all_bound), len(set(all_bound)))

    def test_unresolved_binding_recorded_when_no_overlap(self):
        units = [_unit("u_mystery", ["FF-UNKNOWN-XYZ"])]
        graph = build_narrative_beat_graph(WATER_BOTTLE, units=units)
        self.assertTrue(any(
            u.get("unit_id") == "u_mystery"
            and u.get("kind") == "SI1_UNIT_UNBOUND"
            for u in graph.unresolved_items),
            "zero-overlap units must be reported unbound, never guessed")

    def test_td1_annotation_adds_beat_refs(self):
        units = [
            _unit("u_contact", ["FF-CONTACT", "FF-IDENTITY"]),
            _unit("u_camera", ["FF-CAMERA", "FF-VISIBILITY"]),
        ]
        graph = build_narrative_beat_graph(WATER_BOTTLE, units=units)
        plan = build_temporal_plan(units, total_duration_s=15.0,
                                   duration_source="USER_EXPLICIT")
        annotated = annotate_temporal_plan(plan, graph)
        refs = {e["unit_id"]: e["narrative_beat_display"]
                for e in annotated["atomic_unit_schedule"]}
        self.assertEqual(refs["u_contact"], "PICK_UP")
        self.assertEqual(refs["u_camera"], "PRODUCT_REVEAL")
        # TD-1 core fields unchanged
        self.assertEqual(annotated["plan_hash"], plan.plan_hash)
        self.assertEqual(annotated["feasibility"], plan.feasibility)

    def test_drone_negative_no_performer_beats(self):
        graph = build_narrative_beat_graph(
            "A drone camera orbits a coastal cliff with no performer "
            "visible.")
        self.assertEqual(len(graph.beats), 0)
        self.assertTrue(graph.unresolved_items)

    def test_no_prose_control_coercion(self):
        graph = build_narrative_beat_graph(WATER_BOTTLE)
        import json
        blob = json.dumps(graph.to_dict())
        self.assertNotIn("smile naturally", blob)
        self.assertNotIn("make facial expressions", blob)

    def test_determinism(self):
        a = build_narrative_beat_graph(FIGHT)
        b = build_narrative_beat_graph(FIGHT)
        self.assertEqual(a.graph_hash, b.graph_hash)
        self.assertEqual(a.to_dict(), b.to_dict())

    def test_beat_identity_is_structured(self):
        graph = build_narrative_beat_graph(WATER_BOTTLE)
        drink = next(b for b in graph.beats
                     if b["display_name"] == "DRINK")
        self.assertTrue(drink["beat_id"].startswith("beat_"))
        self.assertTrue(drink["source_span"])
        self.assertIn("object", drink["unresolved_fields"] or [] or
                      [])  # drink clause names no object token -> honest


if __name__ == "__main__":
    unittest.main()
