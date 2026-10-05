"""Coordinate-logic validation for authored kinematic plans (owner request 2026-10-04)."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from lab.application.service import REQUEST_SCHEMA, invoke
from lab.compiler.kinematics import POLICY, describe_plan, validate_plan
from lab.second_brain.tests.test_directing_session import fixture_root

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def plan(name):
    return json.loads((FIXTURES / name).read_text())


def codes(report):
    return sorted({f["code"] for f in report["findings"]})


class KinematicValidatorTests(unittest.TestCase):
    def test_water_duel_v2_fails_for_the_reasons_that_broke_the_render(self):
        report = validate_plan(plan("water_duel_v2_plan.json"))
        self.assertEqual(report["status"], "fail")
        self.assertEqual(codes(report), ["CAMERA_YAW_ONLY", "CONSTRAINT_CONTRADICTION", "DENSITY", "FRAME_UNDECLARED",
                                         "REACH", "RELEASE", "SPEED_JUMP", "SUPPORT_UNDECLARED", "SWING_EXTENT", "TELEPORT"])
        teleport = next(f for f in report["findings"] if f["code"] == "TELEPORT")
        self.assertEqual((teleport["t"], teleport["subject"]), (3.2, "fighter_a"))
        self.assertIn("1.82 m", teleport["message"])

    def test_water_duel_v3_passes_and_reports_the_policy(self):
        report = validate_plan(plan("water_duel_v3_plan.json"))
        self.assertEqual((report["status"], report["findings"]), ("pass", []))
        self.assertEqual(report["policy"], POLICY["version"])

    def test_skid_hips_above_standing_are_caught(self):
        value = plan("water_duel_v3_plan.json")
        for p in value["tracks"]["fighter_a.hips"]:
            if 3.4 <= p["t"] <= 4.0:
                p["y"] = 1.25  # above the 0.95 m standing hips while skidding on both feet
        self.assertIn("SUPPORT_HEIGHT", codes(validate_plan(value)))

    def test_flight_needs_takeoff_and_landing_events(self):
        value = plan("water_duel_v3_plan.json")
        value["force_events"] = [e for e in value["force_events"] if not (e["kind"] == "landing" and e["actor"] == "fighter_a")]
        self.assertIn("FLIGHT_BOUNDS", codes(validate_plan(value)))

    def test_support_and_contact_tokens_come_from_the_approved_lists(self):
        value = plan("water_duel_v3_plan.json")
        value["support"]["fighter_b"][0]["support"] = "both_feet+hovering"
        value["contacts"][0]["mode"] = "soft"
        value["force_events"][0]["kind"] = "teleport"
        self.assertTrue({"SUPPORT_UNKNOWN", "CONTACT_MODE_UNKNOWN", "FORCE_EVENT_UNKNOWN"} <= set(codes(validate_plan(value))))

    def test_release_off_the_tangent_is_caught(self):
        value = plan("water_duel_v3_plan.json")
        track = value["tracks"]["fighter_a.hips"]
        after = next(p for p in track if p["t"] > 3.2)
        release = next(p for p in track if p["t"] == 3.2)
        after["x"], after["z"] = release["x"], release["z"] + 0.8   # leaves at a right angle to the swing
        self.assertIn("RELEASE", codes(validate_plan(value)))

    def test_camera_aim_and_policy_overrides(self):
        value = plan("water_duel_v3_plan.json")
        value["camera"][2]["look_at"] = [9.0, 1.0, -9.0]
        self.assertIn("CAMERA_AIM", codes(validate_plan(value)))
        value = plan("water_duel_v3_plan.json")
        value["policy_overrides"] = {"max_moves_per_second": 1.0}
        self.assertIn("DENSITY", codes(validate_plan(value)))

    def test_backflip_cannot_land_facing_the_target(self):
        # A no-look backflip keeps its heading, so "lands facing Brawler" contradicts the plan.
        value = plan("water_duel_v3_plan.json")
        value["relations"].append({"actor": "fighter_a", "from_s": 5.4, "to_s": 5.6, "toward": "fighter_b"})
        finding = next(f for f in validate_plan(value)["findings"] if f["code"] == "FACING_RELATION")
        self.assertEqual((finding["t"], finding["subject"]), (5.4, "fighter_a"))

    def test_fast_turns_need_a_declared_spin(self):
        value = plan("water_duel_v3_plan.json")
        value["facing"]["fighter_a"].insert(9, {"t": 5.5, "yaw_deg": 270})   # a half turn in 0.1 s, not marked as a spin
        self.assertIn("TURN_RATE", codes(validate_plan(value)))

    def test_landings_declare_their_parts_and_land_low_and_soft(self):
        value = plan("water_duel_v3_plan.json")
        landing = next(e for e in value["force_events"] if e["kind"] == "landing" and e["actor"] == "fighter_a")
        landing.pop("parts")
        self.assertIn("LANDING_PART_UNDECLARED", codes(validate_plan(value)))
        landing["parts"] = ["back"]
        self.assertIn("LANDING_SUPPORT_MISMATCH", codes(validate_plan(value)))
        value = plan("water_duel_v3_plan.json")
        for p in value["tracks"]["fighter_a.hips"]:
            if p["t"] == 5.4:
                p["y"] = 1.3                      # still in the air when the landing is declared
        self.assertIn("LANDING_HEIGHT", codes(validate_plan(value)))
        value = plan("water_duel_v3_plan.json")
        for p in value["tracks"]["fighter_a.hips"]:
            if p["t"] == 5.25:
                p["y"] = 2.4                      # drops 1.65 m in 0.15 s into the landing
        self.assertIn("LANDING_SPEED", codes(validate_plan(value)))

    def test_plan_reads_as_words_without_coordinates(self):
        sentences = describe_plan(plan("water_duel_v3_plan.json"), {"fighter_a": "Prodigy", "fighter_b": "Brawler"})
        text = " ".join(sentences)
        self.assertTrue(sentences[0].startswith("Prodigy:"))
        for phrase in ("held by Brawler", "touches down on both feet at 3.4 s", "skidding, left hand trailing",
                       "keeps the back to Brawler 4.6–5.4 s", "travels backward 4.75–5.35 s",
                       "lands on both feet at 5.4 s", "faces Brawler 6–8 s", "Brawler: 0–5.6 s on both feet, holding still"):
            self.assertIn(phrase, text)
        for coordinate in ("4.71", "1.2,", "x=", "y=", "z="):
            self.assertNotIn(coordinate, text)
        self.assertEqual(describe_plan(plan("water_duel_v3_plan.json"), {"fighter_a": "Prodigy", "fighter_b": "Brawler"}), sentences)

    def test_validation_is_deterministic_and_never_edits_the_plan(self):
        value = plan("water_duel_v2_plan.json")
        before = copy.deepcopy(value)
        self.assertEqual(validate_plan(value), validate_plan(value))
        self.assertEqual(value, before)


class KinematicOperationTests(unittest.TestCase):
    def test_public_operation_returns_the_same_schema_valid_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture_root(Path(temp))
            for name in ("water_duel_v2_plan.json", "water_duel_v3_plan.json"):
                response = invoke(dict(schema=REQUEST_SCHEMA, operation="cpcs.kinematics.validate",
                                       arguments={"plan": plan(name)}), role="chat", root=root)
                self.assertEqual(response["status"], "success", response.get("error"))
                self.assertEqual(response["result"], validate_plan(plan(name)))
            bad = invoke(dict(schema=REQUEST_SCHEMA, operation="cpcs.kinematics.validate",
                              arguments={"plan": {"schema": "cpcs.kinematic_plan/1.0"}}), role="chat", root=root)
            self.assertEqual(bad["status"], "error")


class AuditCanaryTests(unittest.TestCase):
    """Codex audit 2026-10-04 (REQ-AUD-02/03/04): plans that skip checks must not pass silently."""

    def validate(self, value):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture_root(Path(temp))
            response = invoke(dict(schema=REQUEST_SCHEMA, operation="cpcs.kinematics.validate",
                                   arguments={"plan": value}), role="chat", root=root)
        self.assertEqual(response["status"], "success", response.get("error"))
        return response["result"]

    def jail(self):
        return plan("jail_fight_plan.json")

    def test_the_unchanged_fixture_still_passes(self):
        self.assertEqual(self.validate(self.jail())["status"], "pass")

    def test_a_declared_body_without_its_track_is_a_finding(self):
        value = self.jail()
        del value["tracks"]["rome.hips"]
        value["contacts"], value["camera"], value["relations"] = [], [], []
        report = self.validate(value)
        self.assertEqual((report["status"], codes(report)), ("fail", ["TRACK_MISSING"]))

    def test_opening_point_only_tracks_do_not_cover_the_clip(self):
        value = self.jail()
        for name in value["tracks"]:
            value["tracks"][name] = value["tracks"][name][:1]
        value["contacts"], value["camera"], value["relations"] = [], [], []
        report = self.validate(value)
        self.assertEqual(codes(report), ["TRACK_COVERAGE"])
        self.assertEqual(sorted(f["subject"] for f in report["findings"]), ["dex", "rome"])

    def test_contacts_must_name_real_tracks_that_cover_them(self):
        value = self.jail()
        value["contacts"][0].update(by_track="rome.missing_part", on_track="dex.missing_part")
        self.assertEqual(codes(self.validate(value)), ["CONTACT_TRACK_UNKNOWN"])
        value = self.jail()
        value["tracks"]["rome.right_hand"] = [{"t": 0, "x": -1.8, "y": 1.2, "z": 0}, {"t": 2, "x": -1.0, "y": 1.2, "z": 0}]
        value["contacts"][0]["by_track"] = "rome.right_hand"
        self.assertEqual(codes(self.validate(value)), ["CONTACT_TRACK_COVERAGE"])
        value = self.jail()
        del value["contacts"][0]["max_distance_m"]
        self.assertEqual(codes(self.validate(value)), ["CONTACT_LIMIT_UNDECLARED"])

    def test_degenerate_or_unknown_references_are_typed_findings_not_crashes(self):
        value = self.jail()
        value["camera"][0]["look_at"] = list(value["camera"][0]["pos"])
        self.assertEqual(codes(self.validate(value)), ["CAMERA_AXIS_DEGENERATE"])
        value = self.jail()
        value["camera"][0]["must_see"] = ["rome", "ghost"]
        value["relations"].append({"actor": "rome", "from_s": 0, "to_s": 3, "toward": "ghost"})
        value["swings"] = [{"held_track": "dex.hips", "pivot_track": "ghost.hips", "from_s": 1, "to_s": 2, "turn_deg": 90}]
        self.assertEqual(codes(self.validate(value)), ["CAMERA_SUBJECT_UNKNOWN", "RELATION_SUBJECT_UNKNOWN", "SWING_TRACK_UNKNOWN"])

    def test_a_body_present_for_part_of_the_clip_says_so(self):
        value = self.jail()
        value["tracks"]["dex.hips"] = [p for p in value["tracks"]["dex.hips"] if p["t"] <= 9.5]
        value["support"]["dex"] = [{"from_s": 0, "to_s": 9.5, "support": "both_feet+step"}]
        value["camera"][-1]["must_see"] = ["rome"]
        self.assertEqual(codes(self.validate(value)), ["SUPPORT_GAP", "TRACK_COVERAGE"])
        value["bodies"]["dex"]["present_s"] = [0, 9.5]
        self.assertEqual(self.validate(value)["status"], "pass")
        value["bodies"]["dex"]["present_s"] = [9.5, 2]
        self.assertIn("PRESENCE_INVALID", codes(self.validate(value)))


if __name__ == "__main__":
    unittest.main()
