"""Coordinate-logic validation for authored kinematic plans (owner request 2026-10-04)."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from lab.application.service import REQUEST_SCHEMA, invoke
from lab.compiler.kinematics import POLICY, validate_plan
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


if __name__ == "__main__":
    unittest.main()
