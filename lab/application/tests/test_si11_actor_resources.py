"""SI-1.1 — actor resource constraint tests (hermetic)."""
from __future__ import annotations

import unittest

from lab.application.cpcs_actor_resources import build_resource_constraints
from lab.application.cpcs_narrative_beats import build_narrative_beat_graph

WATER_BOTTLE = (
    "A 15-second TikTok-style UGC video of a woman casually showing off "
    "a water bottle she actually uses every day. She picks it up, takes "
    "a drink, talks about why she likes it, and shows it to the camera "
    "at the end. It should feel natural and believable like a real "
    "creator filmed it on her phone, not like an ad."
)
FIGHT = (
    "A fighter catches an opponent's leg, swings him in a wide arc, "
    "releases him onto the water, then immediately pressures him while "
    "he tries to recover."
)


class Si11ActorResources(unittest.TestCase):

    def test_phone_hand_stays_occupied_across_beats(self):
        graph = build_narrative_beat_graph(WATER_BOTTLE)
        packet = build_resource_constraints(
            WATER_BOTTLE, graph, actor_ids=["creator"])
        self.assertTrue(packet.lineage["phone_hold"])
        phone_holds = [r for r in packet.actor_resources
                       if r["assigned_role"] == "phone_hold"]
        self.assertEqual(len(phone_holds), 1)
        self.assertEqual(phone_holds[0]["state"], "OCCUPIED")
        # the bottle grip never lands on the phone hand
        for entry in packet.occupancy_ledger:
            if entry.get("object") == "bottle" and entry.get("role") == "GRASP":
                self.assertNotEqual(entry["resource"],
                                    phone_holds[0]["actor_id"] + "." +
                                    phone_holds[0]["resource_id"])

    def test_drink_precondition_unresolved_no_invented_mechanism(self):
        graph = build_narrative_beat_graph(WATER_BOTTLE)
        packet = build_resource_constraints(
            WATER_BOTTLE, graph, actor_ids=["creator"])
        drink_pre = [p for p in packet.preconditions
                     if p["display"] == "DRINK"]
        self.assertTrue(drink_pre)
        self.assertEqual(drink_pre[0]["disposition"], "UNRESOLVED")
        self.assertIn("never be invented", drink_pre[0]["reason"])
        import json
        blob = json.dumps(packet.to_dict())
        for invented in ("twist", "flip_open", "pop", "straw", "unscrew"):
            self.assertNotIn(invented, blob)

    def test_bimanual_conflict_under_phone_occupancy(self):
        graph = build_narrative_beat_graph(
            "She picks up a box and assembles a keyboard on her desk. "
            "She filmed it on her phone.",
            units=[])
        packet = build_resource_constraints(
            "She picks up a box and assembles a keyboard on her desk. "
            "She filmed it on her phone.",
            graph, actor_ids=["creator"])
        self.assertTrue(packet.conflicts,
                        "bimanual action with one hand holding the phone "
                        "must produce a resource conflict")
        self.assertEqual(packet.conflicts[0]["kind"], "RESOURCE_CONFLICT")

    def test_cooking_third_object_conflict(self):
        graph = build_narrative_beat_graph(
            "A chef slices a tomato and picks up a plate.")
        packet = build_resource_constraints(
            "A chef slices a tomato and picks up a plate.",
            graph, actor_ids=["chef"])
        self.assertTrue(packet.conflicts,
                        "both hands in slice grip, third object must conflict")

    def test_fight_grip_persists_then_releases(self):
        graph = build_narrative_beat_graph(FIGHT)
        packet = build_resource_constraints(
            FIGHT, graph, actor_ids=["fighter"])
        holds = [e for e in packet.occupancy_ledger
                 if e.get("role") == "GRASP"]
        self.assertTrue(holds)
        releases = [e for e in packet.occupancy_ledger
                    if e.get("release_beat")]
        self.assertTrue(releases, "RELEASE must free the grip")
        self.assertFalse(packet.conflicts,
                         "catch->swing->release chain must not conflict")

    def test_drone_no_human_resource_graph(self):
        graph = build_narrative_beat_graph(
            "A drone camera orbits a coastal cliff with no performer "
            "visible.")
        packet = build_resource_constraints(
            "A drone camera orbits a coastal cliff with no performer "
            "visible.", graph)
        self.assertEqual(packet.actor_resources, [])
        self.assertEqual(packet.occupancy_ledger, [])

    def test_determinism(self):
        graph = build_narrative_beat_graph(WATER_BOTTLE)
        a = build_resource_constraints(WATER_BOTTLE, graph,
                                       actor_ids=["creator"])
        b = build_resource_constraints(WATER_BOTTLE, graph,
                                       actor_ids=["creator"])
        self.assertEqual(a.packet_hash, b.packet_hash)
        self.assertEqual(a.to_dict(), b.to_dict())


if __name__ == "__main__":
    unittest.main()
