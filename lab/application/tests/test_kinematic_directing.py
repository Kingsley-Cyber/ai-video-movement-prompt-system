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
from lab.second_brain.src.validate import REPO_ROOT
from lab.second_brain.tests.test_directing_session import fixture, fixture_root


def jail_plan():
    return json.loads((REPO_ROOT / "lab/compiler/tests/fixtures/jail_fight_plan.json").read_text())


def blocking():
    return [d for d in stacks()["staging"] if d["sublayer"] != "kinematics"]


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

    def start(self):
        self.sid = self.result("direct.start", dict(text=self.data["ask"], mode="complete", model="seedance-2.0"))["session_id"]
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

    def test_staging_always_requires_a_plan_and_there_is_no_switch(self):
        self.start()
        packet = self.result("direct.packet.read", dict(session_id=self.sid, pass_id="staging"))
        self.assertIn("cpcs-kinematics/1.1", packet["steering"])
        self.assertTrue(next(s for s in packet["sublayers"] if s["sublayer_id"] == "kinematics")["required"])
        response = self.submit("staging", blocking())
        self.assertIn("missing_required_sublayer", self.codes(response))
        off = self.call("direct.start", dict(text=self.data["ask"], mode="complete", model="seedance-2.0", kinematics=False))
        self.assertEqual(off["status"], "error")

    def test_findings_return_as_rejections_and_a_repair_is_accepted(self):
        self.start()
        broken = jail_plan()
        broken["tracks"]["rome.hips"].insert(2, {"t": 3, "x": 1.5, "y": 1.0, "z": 0})   # same time, 1.95 m away
        broken["support"]["dex"][0]["support"] = "both_feet+hovering"
        broken["relations"].append({"actor": "dex", "from_s": 4, "to_s": 6, "away_from": "rome"})   # he faces Rome
        codes = self.codes(self.submit("staging", blocking() + [kinematics_decision(broken)]))
        self.assertIn("kinematic_teleport", codes)
        self.assertIn("kinematic_support_unknown", codes)
        self.assertIn("kinematic_facing_relation", codes)
        self.assertEqual(self.submit("staging", blocking() + [kinematics_decision(jail_plan())])["disposition"], "accepted")

    def test_plan_must_match_the_accepted_scene(self):
        self.start()
        wrong = jail_plan()
        wrong["duration_s"] = 8
        wrong["bodies"]["stranger"] = {"hip_height_m": 1.0}
        self.assertIn("kinematic_scene_mismatch", self.codes(self.submit("staging", blocking() + [kinematics_decision(wrong)])))

    def test_accepted_plan_reaches_the_score_json_not_prose_and_builds_refuse_a_failing_plan(self):
        self.start()
        self.assertEqual(self.submit("staging", blocking() + [kinematics_decision(jail_plan())])["disposition"], "accepted")
        for pass_id in ("camera", "light_color", "style", "audio", "synthesis"):
            self.assertEqual(self.submit(pass_id, stacks()[pass_id])["disposition"], "accepted")
        finished = self.result("direct.finish", dict(session_id=self.sid))
        score = finished["score"]
        self.assertEqual(score["scenes"][0]["kinematic_plan"]["plan_id"], "jail_fight_plan")
        request = make_build_request(score, project_id="kinematic-test", model="seedance-2.0", duration_seconds=15, prompt_format="prose")
        prose = compile_build(request, root=self.root)
        self.assertNotIn(b"rome.hips", prose["prompt.txt"])
        self.assertIn(b"Motion plan: Rome stays screen-left of Dex throughout.", prose["prompt.txt"])
        self.assertIn(b"Dex: 0\xe2\x80\x9315 s on both feet, stepping; faces Rome", prose["prompt.txt"])
        report = json.loads(prose["capability_report.json"])["kinematics"]
        self.assertEqual((report["plan_id"], report["status"], report["findings"], report["prose_projection"]),
                         ("jail_fight_plan", "pass", 0, "words"))
        request["settings"]["prompt_format"] = "json"
        structured = compile_build(request, root=self.root)
        self.assertIn(b"rome.hips", structured["prompt.txt"])
        self.assertNotIn(b"Motion plan:", structured["prompt.txt"])
        self.assertEqual(json.loads(structured["capability_report.json"])["kinematics"]["prose_projection"], "structured")
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


if __name__ == "__main__":
    unittest.main()
