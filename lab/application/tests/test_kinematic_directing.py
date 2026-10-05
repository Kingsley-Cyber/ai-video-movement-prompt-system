"""Validator-driven repair loop: a kinematic plan joins the staging stack, findings come back as rejections."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from lab.application.service import REQUEST_SCHEMA, invoke
from lab.application.tests.test_directing_pipeline import decision, stacks
from lab.compiler.build import compile_build, make_build_request
from lab.compiler.tests.test_build import ready_score
from lab.second_brain.tests.test_directing_session import fixture, fixture_root


def jail_plan():
    return {
        "schema": "cpcs.kinematic_plan/1.0", "plan_id": "jail_fight_plan", "duration_s": 15,
        "frame": {"units": "m", "up": "y", "surface_y": 0, "screen_right": "+x", "camera": "position_look_at"},
        "bodies": {"rome": {"hip_height_m": 1.0}, "dex": {"hip_height_m": 0.95}},
        "tracks": {
            "rome.hips": [{"t": 0, "x": -2.0, "y": 1.0, "z": 0}, {"t": 3, "x": -0.45, "y": 1.0, "z": 0},
                          {"t": 6, "x": -0.5, "y": 1.0, "z": -0.2}, {"t": 8.5, "x": -0.4, "y": 1.0, "z": 0},
                          {"t": 9.5, "x": 1.15, "y": 1.0, "z": 0}, {"t": 12.5, "x": 1.15, "y": 1.0, "z": 0},
                          {"t": 15, "x": 0.5, "y": 1.0, "z": 0}],
            "dex.hips": [{"t": 0, "x": 0.0, "y": 0.95, "z": 0}, {"t": 4.0, "x": 0.0, "y": 0.95, "z": 0},
                         {"t": 4.4, "x": 0.4, "y": 0.95, "z": 0}, {"t": 6, "x": 0.25, "y": 0.95, "z": 0},
                         {"t": 8.5, "x": 0.25, "y": 0.95, "z": 0}, {"t": 9.5, "x": 1.6, "y": 0.95, "z": 0},
                         {"t": 15, "x": 1.6, "y": 0.95, "z": 0}],
        },
        "support": {"rome": [{"from_s": 0, "to_s": 15, "support": "both_feet+step"}],
                    "dex": [{"from_s": 0, "to_s": 15, "support": "both_feet+step"}]},
        "force_events": [{"t": 4.0, "kind": "impact", "actor": "dex"}, {"t": 8.5, "kind": "impact", "actor": "dex"}],
        "contacts": [{"id": "shove", "mode": "physical_contact", "start_s": 4.0, "end_s": 4.2,
                      "by_track": "rome.hips", "on_track": "dex.hips", "max_distance_m": 0.8}],
        "camera": [{"t": 0, "pos": [0, 1.6, -4], "look_at": [0, 1.0, 0], "must_see": ["rome", "dex"]},
                   {"t": 15, "pos": [0.8, 1.6, -4], "look_at": [1.0, 1.0, 0], "must_see": ["rome", "dex"]}],
    }


def kinematics_decision(plan):
    return decision("stage_kinematics", "staging", "kinematics", "scenes", "scene_1", {"kinematic_plan": plan},
                    ["d_entity_rome", "d_entity_dex", "d_scene_duration"])


class KinematicDirectingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = fixture_root(Path(temp.name))
        self.data = fixture()

    def call(self, op, args):
        return invoke(dict(schema=REQUEST_SCHEMA, operation="cpcs." + op, arguments=args), role="operator", root=self.root)

    def result(self, op, args):
        response = self.call(op, args)
        self.assertEqual(response["status"], "success", response.get("error"))
        return response["result"]

    def start(self, kinematics=True):
        args = dict(text=self.data["ask"], mode="complete", model="seedance-2.0")
        if kinematics:
            args["kinematics"] = True
        self.sid = self.result("direct.start", args)["session_id"]
        self.submit("scene_action", self.data["proposal"]["decisions"])
        self.submit("performance", stacks()["performance"])

    def submit(self, pass_id, ds):
        packet = self.result("direct.packet.read", dict(session_id=self.sid, pass_id=pass_id))
        chosen = {d["sublayer"] for d in ds}
        proposal = dict(schema="cpcs.directing_proposal/1.0", pass_id=pass_id, decisions=copy.deepcopy(ds),
                        not_applicable=[dict(sublayer_id=s["sublayer_id"], reason="Not needed for this scene.")
                                        for s in packet["sublayers"] if not s["required"] and s["sublayer_id"] not in chosen])
        return self.result("direct.proposal.submit", dict(session_id=self.sid, pass_id=pass_id,
                           packet_hash=packet["packet_hash"], proposal=proposal))

    def codes(self, response):
        self.assertEqual(response["disposition"], "rejected", response)
        return sorted({r["code"] for r in response["rejections"]})

    def test_opted_in_staging_requires_a_plan(self):
        self.start()
        packet = self.result("direct.packet.read", dict(session_id=self.sid, pass_id="staging"))
        self.assertIn("cpcs-kinematics/1.0", packet["steering"])
        self.assertEqual(self.codes(self.submit("staging", stacks()["staging"])), ["kinematic_plan_missing"])

    def test_findings_return_as_rejections_and_a_repair_is_accepted(self):
        self.start()
        broken = jail_plan()
        broken["tracks"]["rome.hips"].insert(2, {"t": 3, "x": 1.5, "y": 1.0, "z": 0})   # same time, 1.95 m away
        broken["support"]["dex"][0]["support"] = "both_feet+hovering"
        codes = self.codes(self.submit("staging", stacks()["staging"] + [kinematics_decision(broken)]))
        self.assertIn("kinematic_teleport", codes)
        self.assertIn("kinematic_support_unknown", codes)
        self.assertEqual(self.submit("staging", stacks()["staging"] + [kinematics_decision(jail_plan())])["disposition"], "accepted")

    def test_plan_must_match_the_accepted_scene(self):
        self.start()
        wrong = jail_plan()
        wrong["duration_s"] = 8
        wrong["bodies"]["stranger"] = {"hip_height_m": 1.0}
        self.assertIn("kinematic_scene_mismatch", self.codes(self.submit("staging", stacks()["staging"] + [kinematics_decision(wrong)])))

    def test_accepted_plan_reaches_the_score_json_not_prose_and_builds_refuse_a_failing_plan(self):
        self.start()
        self.assertEqual(self.submit("staging", stacks()["staging"] + [kinematics_decision(jail_plan())])["disposition"], "accepted")
        for pass_id in ("camera", "light_color", "style", "audio", "synthesis"):
            self.assertEqual(self.submit(pass_id, stacks()[pass_id])["disposition"], "accepted")
        finished = self.result("direct.finish", dict(session_id=self.sid))
        score = finished["score"]
        self.assertEqual(score["scenes"][0]["kinematic_plan"]["plan_id"], "jail_fight_plan")
        request = make_build_request(score, project_id="kinematic-test", model="seedance-2.0", duration_seconds=15, prompt_format="prose")
        prose = compile_build(request, root=self.root)
        self.assertNotIn(b"rome.hips", prose["prompt.txt"])
        report = json.loads(prose["capability_report.json"])["kinematics"]
        self.assertEqual((report["plan_id"], report["status"], report["findings"]), ("jail_fight_plan", "pass", 0))
        request["settings"]["prompt_format"] = "json"
        self.assertIn(b"rome.hips", compile_build(request, root=self.root)["prompt.txt"])
        tampered = copy.deepcopy(score)
        tampered["scenes"][0]["kinematic_plan"]["tracks"]["rome.hips"].insert(1, {"t": 0, "x": 3.0, "y": 1.0, "z": 0})
        with self.assertRaisesRegex(ValueError, "score_id"):
            compile_build(dict(request, score=tampered), root=self.root)
        overlays = copy.deepcopy(finished["overlays"])
        for overlay in overlays:
            for scene in overlay["values"].get("scenes", []):
                if "kinematic_plan" in scene:
                    scene["kinematic_plan"]["tracks"]["rome.hips"].insert(1, {"t": 0, "x": 3.0, "y": 1.0, "z": 0})
        failing = ready_score(self.data["ask"], overlays=overlays)   # a resolved score that carries a failing plan
        with self.assertRaisesRegex(ValueError, "KINEMATIC_PLAN_FAILED: .*TELEPORT"):
            compile_build(make_build_request(failing, project_id="kinematic-test", model="seedance-2.0",
                                             duration_seconds=15, prompt_format="json"), root=self.root)

    def test_default_session_keeps_the_slot_optional(self):
        self.start(kinematics=False)
        self.assertEqual(self.submit("staging", stacks()["staging"])["disposition"], "accepted")


if __name__ == "__main__":
    unittest.main()
