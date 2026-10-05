"""The kinematic plan and the accepted scene describe the same events (Codex audit REQ-AUD-05)."""
from __future__ import annotations

import copy
import unittest

# Import modules, not TestCase classes: a TestCase in this namespace would be discovered and run twice.
from lab.application.tests import test_kinematic_directing as kd
from lab.application.tests.test_directing_pipeline import stacks
from lab.compiler.build import compile_build, make_build_request
from lab.compiler.tests.test_build import ready_score

blocking, jail_plan, kinematics_decision = kd.blocking, kd.jail_plan, kd.kinematics_decision


def codes(result):
    return sorted({r["code"] for r in result["rejections"]})


class PlanBindingTests(unittest.TestCase):
    def setUp(self):
        self.client = kd.KinematicDirectingTests()
        self.client.setUp()
        self.addCleanup(self.client.doCleanups)
        self.data, self.root = self.client.data, self.client.root

    def result(self, op, args):
        return self.client.result(op, args)

    def submit(self, pass_id, ds):
        return self.client.submit(pass_id, ds)

    def start(self):
        self.client.start()

    def staging(self, plan):
        return self.submit("staging", blocking() + [kinematics_decision(plan)])

    def timed_start(self, variant=""):
        """The jail fixture with authored beat lengths, so contact times can be checked against beats."""
        options = dict(text=self.data["ask"], mode="complete", model="seedance-2.0")
        if variant:
            options["variant"] = variant
        self.client.sid = self.result("direct.start", options)["session_id"]
        decisions = copy.deepcopy(self.data["proposal"]["decisions"])
        for d, length in zip([d for d in decisions if d["sublayer"] == "beats"], (3.0, 2.5, 3.0, 3.5, 3.0)):
            d["values"]["duration_s"] = length
        self.assertEqual(self.submit("scene_action", decisions)["disposition"], "accepted")
        self.submit("performance", stacks()["performance"])

    def test_the_consistent_fixture_is_accepted(self):
        self.start()
        self.assertEqual(self.staging(jail_plan())["disposition"], "accepted")

    def test_every_scene_contact_between_tracked_bodies_is_bound(self):
        self.start()
        plan = jail_plan()
        plan["contacts"] = [c for c in plan["contacts"] if c["id"] != "drive"]
        result = self.staging(plan)
        self.assertEqual(codes(result), ["kinematic_contact_unbound"])
        self.assertIn("int_2", next(r for r in result["rejections"] if r["code"] == "kinematic_contact_unbound")["message"])

    def test_a_bound_contact_must_join_the_same_people(self):
        self.start()
        plan = jail_plan()
        plan["bodies"]["guard"] = {"hip_height_m": 1.0}
        plan["tracks"]["guard.hips"] = [{"t": 0, "x": 2.5, "y": 1.0, "z": 0}, {"t": 15, "x": 2.5, "y": 1.0, "z": 0}]
        plan["support"]["guard"] = [{"from_s": 0, "to_s": 15, "support": "both_feet+static"}]
        plan["contacts"][0]["on_track"] = "guard.hips"
        plan["contacts"][0]["max_distance_m"] = 5.0
        self.assertIn("kinematic_scene_mismatch", codes(self.staging(plan)))   # an undeclared body is still refused first
        plan = jail_plan()
        plan["contacts"][0]["interaction"] = "int_9"
        self.assertEqual(codes(self.staging(plan)), ["kinematic_contact_unbound", "kinematic_reference_unknown"])

    def test_a_bound_contact_happens_inside_its_beat(self):
        self.timed_start()
        plan = jail_plan()                                    # beats now run 0-3, 3-5.5, 5.5-8.5, 8.5-12, 12-15
        plan["contacts"][0].update(start_s=3.5, end_s=3.7)    # the shove (int_1) is in beat 2
        self.assertEqual(self.staging(plan)["disposition"], "accepted")
        self.timed_start(variant="late shove")                # a fresh session for the failing case
        later = jail_plan()
        later["contacts"][0].update(start_s=10.0, end_s=10.2)
        result = self.staging(later)
        self.assertEqual(codes(result), ["kinematic_contact_mismatch"])
        self.assertIn("3–5.5 s", result["rejections"][0]["message"])

    def test_people_who_act_are_tracked_or_declared_untracked(self):
        self.start()
        plan = jail_plan()
        for key in ("bodies", "support", "facing"):
            plan[key].pop("dex", None)
        plan["tracks"].pop("dex.hips")
        plan["contacts"], plan["relations"] = [], [r for r in plan["relations"] if r["actor"] != "dex" and r.get("toward") != "dex"]
        for key in plan["camera"]:
            key["must_see"] = ["rome"]
        self.assertEqual(codes(self.staging(plan)), ["kinematic_body_untracked"])
        plan["untracked"] = [{"entity": "dex", "reason": "seen only as a hand in an insert"}]
        self.assertEqual(self.staging(plan)["disposition"], "accepted")

    def test_a_camera_keyframe_naming_a_shot_falls_inside_it_and_builds_refuse_a_broken_binding(self):
        self.start()
        plan = jail_plan()
        plan["camera"][0]["shot"] = "shot_1"
        self.assertEqual(self.staging(plan)["disposition"], "accepted")   # shots do not exist yet at staging
        for pass_id in ("camera", "light_color", "style", "audio", "synthesis"):
            self.assertEqual(self.submit(pass_id, stacks()[pass_id])["disposition"], "accepted")
        finished = self.result("direct.finish", dict(session_id=self.client.sid, build_settings=dict(
            project_id="cpcs-local-export", duration_seconds=15, prompt_format="prose")))
        self.assertIsNotNone(finished["build"])
        overlays = copy.deepcopy(finished["overlays"])
        for overlay in overlays:
            for scene in overlay["values"].get("scenes", []):
                if "kinematic_plan" in scene:
                    scene["kinematic_plan"]["camera"][0]["shot"] = "shot_7"
        broken = ready_score(self.data["ask"], overlays=overlays)   # a resolved score whose plan names a missing shot
        with self.assertRaisesRegex(ValueError, "KINEMATIC_BINDING_FAILED: kinematic_reference_unknown"):
            compile_build(make_build_request(broken, model="seedance-2.0", project_id="cpcs-local-export",
                                             duration_seconds=15, prompt_format="prose"), self.root)


if __name__ == "__main__":
    unittest.main()
