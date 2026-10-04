"""Opt-in action-scoped coverage: every authored action needs its body pathway and a covering shot."""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from lab.application.service import REQUEST_SCHEMA, invoke
from lab.application.tests.test_directing_pipeline import decision, stacks
from lab.compiler.tests import test_prop_hand_ledger as prop_fixtures
from lab.second_brain.tests.test_directing_session import fixture, fixture_root

JAIL_ACTIONS = ["act_1", "act_2", "act_3", "act_4", "act_5", "act_6"]


def body_for(action_id, inputs, *, revision_of=None, suffix=""):
    values = {"body": f"The planted support foot starts {action_id}; hips and shoulders carry it outward."}
    # The shared camera stack cites p_body, so the act_2 body keeps that decision id.
    name = "p_body" if action_id == "act_2" and not suffix else f"p_body_{action_id}{suffix}"
    made = decision(name, "performance", "body", "actions", action_id, values, inputs)
    made["revision_of"] = revision_of
    return made


def performance(actions=JAIL_ACTIONS, inputs=None):
    others = [d for d in stacks()["performance"] if d["sublayer"] != "body"]
    return [body_for(a, [(inputs or {}).get(a, "d_" + a.replace("act_", "action_"))]) for a in actions] + others


def camera(end_beat):
    ds = copy.deepcopy(stacks()["camera"])
    ds[0]["values"]["end_beat"] = end_beat
    return ds


class ActionCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = fixture_root(Path(self.temp.name))
        self.data = fixture()

    def call(self, op, args):
        return invoke(dict(schema=REQUEST_SCHEMA, operation="cpcs." + op, arguments=args), role="operator", root=self.root)

    def result(self, op, args):
        response = self.call(op, args)
        self.assertEqual(response["status"], "success", response.get("error"))
        return response["result"]

    def start(self, coverage=True, text=None):
        args = dict(text=text or self.data["ask"], mode="complete", model="seedance-2.0")
        if coverage:
            args["action_coverage"] = True
        self.sid = self.result("direct.start", args)["session_id"]

    def packet(self, pass_id):
        return self.result("direct.packet.read", dict(session_id=self.sid, pass_id=pass_id))

    def submit(self, pass_id, ds, targeted=()):
        packet = self.packet(pass_id)
        chosen = {d["sublayer"] for d in ds}
        untargeted = [dict(sublayer_id=s["sublayer_id"], reason="Not needed for this scene.")
                      for s in packet["sublayers"] if not s["required"] and s["sublayer_id"] not in chosen
                      and not any(t["sublayer_id"] == s["sublayer_id"] for t in targeted)]
        proposal = dict(schema="cpcs.directing_proposal/1.0", pass_id=pass_id, decisions=copy.deepcopy(ds),
                        not_applicable=untargeted + list(targeted))
        return self.result("direct.proposal.submit", dict(session_id=self.sid, pass_id=pass_id,
                           packet_hash=packet["packet_hash"], proposal=proposal))

    def accepted(self, response):
        self.assertEqual(response["disposition"], "accepted", response)

    def open_needs(self, response):
        self.assertEqual(response["disposition"], "rejected", response)
        return sorted(r["path"] for r in response["rejections"] if r["code"] == "unresolved_need")

    def scene(self):
        self.accepted(self.submit("scene_action", self.data["proposal"]["decisions"]))

    def through_staging(self):
        self.scene()
        self.accepted(self.submit("performance", performance()))
        self.accepted(self.submit("staging", stacks()["staging"]))

    def test_default_complete_session_keeps_slot_coverage_and_refuses_targeted_not_applicable(self):
        self.start(coverage=False)
        self.scene()
        self.assertNotIn("needs", self.packet("performance"))
        targeted = [dict(sublayer_id="body", reason="Off screen.", target=dict(path="actions", item_id="act_6"))]
        response = self.submit("performance", stacks()["performance"], targeted)
        self.assertIn("unknown_need", [r["code"] for r in response["rejections"]])
        self.accepted(self.submit("performance", stacks()["performance"]))

    def test_authored_actions_create_body_and_camera_needs(self):
        self.start()
        self.scene()
        needs = self.packet("performance")["needs"]
        self.assertEqual([n["need_id"] for n in needs], ["need_body_" + a for a in JAIL_ACTIONS])
        self.assertEqual({n["status"] for n in needs}, {"open"})
        self.assertEqual(needs[1]["depends_on"], ["d_action_2"])
        self.accepted(self.submit("performance", performance()))
        self.accepted(self.submit("staging", stacks()["staging"]))
        camera_needs = self.packet("camera")["needs"]
        self.assertEqual([n["need_id"] for n in camera_needs], ["need_camera_" + a for a in JAIL_ACTIONS])

    def test_unresolved_body_pathway_rejects_the_performance_stack(self):
        self.start()
        self.scene()
        self.assertEqual(self.open_needs(self.submit("performance", stacks()["performance"])),
                         ["need_body_" + a for a in JAIL_ACTIONS if a != "act_2"])

    def test_body_choice_must_cite_the_actions_current_decision(self):
        self.start()
        self.scene()
        wrong = performance(inputs={"act_4": "d_action_3"})
        self.assertEqual(self.open_needs(self.submit("performance", wrong)), ["need_body_act_4"])

    def test_creative_resolution_and_targeted_not_applicable_resolve_needs(self):
        self.start()
        self.scene()
        targeted = [dict(sublayer_id="body", reason="The buzzer beat is a freeze; no new body pathway.",
                         target=dict(path="actions", item_id="act_6"))]
        self.accepted(self.submit("performance", performance(JAIL_ACTIONS[:-1]), targeted))
        statuses = {n["need_id"]: n["status"] for n in self.packet("performance")["needs"]}
        self.assertEqual(statuses["need_body_act_1"], "resolved")
        self.assertEqual(statuses["need_body_act_6"], "not_applicable")

    def test_camera_span_must_cover_every_action_beat_then_finish_builds(self):
        self.start()
        self.through_staging()
        self.assertEqual(self.open_needs(self.submit("camera", camera("beat_2"))),
                         ["need_camera_" + a for a in JAIL_ACTIONS[2:]])
        self.accepted(self.submit("camera", camera("beat_5")))
        for pass_id in ("light_color", "style", "audio", "synthesis"):
            self.accepted(self.submit(pass_id, stacks()[pass_id]))
        finished = self.result("direct.finish", dict(session_id=self.sid))
        self.assertEqual(finished["scene_completeness"]["counts"]["actions"], 6)

    def test_revised_action_reopens_its_body_need(self):
        # d_action_6 has no in-pass dependents, so revising it needs no other scene revision.
        self.start()
        self.scene()
        self.accepted(self.submit("performance", performance()))
        scene = copy.deepcopy(self.data["proposal"]["decisions"])
        index = next(i for i, d in enumerate(scene) if d["decision_id"] == "d_action_6")
        scene[index] = dict(scene[index], decision_id="d_action_6_revised", revision_of="d_action_6",
                            values=dict(scene[index]["values"], verb="lets go and backs away as the buzzer sounds"))
        self.accepted(self.submit("scene_action", scene))
        needs = {n["need_id"]: n for n in self.packet("performance")["needs"]}
        self.assertEqual(needs["need_body_act_6"]["status"], "open")
        self.assertEqual(needs["need_body_act_6"]["depends_on"], ["d_action_6_revised"])
        self.assertEqual(needs["need_body_act_5"]["status"], "resolved")
        error = self.call("direct.finish", dict(session_id=self.sid))
        self.assertEqual(error["status"], "error")
        self.assertIn("need_body_act_6", self.open_needs(self.submit("performance", performance())))
        fixed = performance(inputs={"act_6": "d_action_6_revised"})
        fixed[5] = body_for("act_6", ["d_action_6_revised"], revision_of="p_body_act_6", suffix="_revised")
        self.accepted(self.submit("performance", fixed))
        self.assertEqual({n["status"] for n in self.packet("performance")["needs"]}, {"resolved"})

    def test_non_combat_scene_needs_only_its_authored_people_and_shots(self):
        self.start(text="A casual phone video opening a drink bottle, 15 seconds")
        ds = prop_fixtures.PropHandLedgerTests.bottle(None, True)
        ds.append(prop_fixtures.choice("actions", "cap_rolls", dict(actor="cap", beat="beat_3", order=4,
                                                     verb="rolls across the counter")))
        self.accepted(self.submit("scene_action", ds))
        needs = [n["need_id"] for n in self.packet("performance")["needs"]]
        self.assertEqual(needs, ["need_body_set_phone", "need_body_open", "need_body_drink"])
        self.assertTrue(all(n.startswith("need_body_") for n in needs))


if __name__ == "__main__":
    unittest.main()
