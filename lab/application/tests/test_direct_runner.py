"""One scene card runs a whole directing session through the public operations (Codex audit REQ-AUD-11)."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from lab.application import direct_runner as dr
from lab.second_brain.src.validate import REPO_ROOT
from lab.second_brain.tests.test_directing_session import fixture_root


def jail_card() -> dict:
    """The jail fixture and the pipeline test's later stacks, written as one scene card."""
    fixture = json.loads((REPO_ROOT / "handoff/direct_scene/reference/jail_fight_proposal.json").read_text())
    card = {"ask": fixture["ask"], "model": "seedance-2.0", "scene_action": {}, "relative": {}}
    for d in fixture["proposal"]["decisions"]:
        card["scene_action"].setdefault(d["sublayer"], {}).setdefault(d["target"]["item_id"], {}).update(d["values"])
        if d["relative_anchor"]:
            card["relative"][f"{d['target']['path']}.{d['target']['item_id']}"] = d["relative_anchor"]
    card["performance"] = {"act_2": {
        "body": "The planted rear foot starts the shove; the hips and shoulder carry it into the palms.",
        "effort_weight": "strong", "effort_time": "sudden", "effort_space": "direct", "effort_flow": "bound",
        "shape": "advancing", "connectivity": "upper-lower",
        "face": "Rome keeps his eyes on Dex; the jaw tightens at release."}}
    card["staging"] = {"blocking": "Rome stays left, Dex stays right; the bars remain behind Dex.",
                       "kinematic_plan": json.loads((REPO_ROOT / "lab/compiler/tests/fixtures/jail_fight_plan.json").read_text())}
    card["camera"] = {"shot_1": {
        "order": 1, "beat": "beat_1", "end_beat": "beat_5", "shows_initiation": True,
        "framing": "medium-wide, both fighters visible from feet to head", "angle": "eye-level three-quarter view",
        "position": "on the table side of the action axis", "movement": "locked off", "movement_quality": "steady",
        "relation": "observes both fighters", "lens": "wide, separated silhouettes", "focus": "both fighters and the bars",
        "composition": "clear space between palms and chest", "time": "normal playback", "blur": "readable hands",
        "connection": "one continuous shot ending with both fighters apart"}}
    card["light_color"] = {"lighting": "Overhead jail fluorescents keep faces and contact readable."}
    card["style"] = {"visual_style": "Restrained live-action realism."}
    card["audio"] = {"sound": "The bars rattle on impact; the buzzer triggers separation; nobody speaks."}
    card["synthesis"] = {"end_state": "Both fighters upright, apart, looking at each other."}
    return card


class DirectRunnerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = fixture_root(Path(temporary.name))

    def run_card(self, card):
        return dr.Runner(root=self.root).run(card)

    def test_one_card_builds_a_usable_prompt_through_every_pass(self):
        result = self.run_card(jail_card())
        self.assertEqual([p.split(":")[0] for p in result["passes"]], list(dr.PASSES))
        prompt = result["prompt"]
        self.assertTrue(prompt.startswith("GOAL      15s"))                    # director layout, no raw ask
        self.assertNotIn("User intent", prompt)
        self.assertIn("SUMMARY  Rome walks up to Dex", prompt)
        self.assertIn("BEAT 2 (at least 2s) THE SHOVE", prompt)
        self.assertIn("project.duration_seconds", result["withheld_defaults"])
        state = dr.Runner(root=self.root).state(result["session_id"])
        duration = next(d for d in state["decisions"] if d["decision_id"] == "scene_action.scenes.scene_1.scene.duration")
        self.assertEqual((duration["source_status"], duration["lock"], duration["evidence_uses"][0]["text"]),
                         ("user_explicit", True, "15 seconds"))
        effort = next(d for d in state["decisions"] if d["decision_id"] == "performance.actions.act_2.effort_weight")
        self.assertEqual(effort["values"]["effort_weight"]["code"], "laban.effort.weight.strong")
        self.assertIn("scene_action.actions.act_2.actions", effort["inputs"])

    def test_a_rerun_reuses_accepted_work_and_a_change_cascades_by_itself(self):
        card = jail_card()
        first = self.run_card(card)
        again = self.run_card(card)
        self.assertEqual(again["passes"], [f"{p}: unchanged" for p in dr.PASSES])
        self.assertEqual((again["score_id"], again["prompt"]), (first["score_id"], first["prompt"]))
        changed = copy.deepcopy(card)
        changed["scene_action"]["entities"]["dex"]["description"] = "a lean man in his 20s with a shaved head, in a grey uniform"
        changed["light_color"]["lighting"] = "Overhead fluorescents and one red exit sign keep faces readable."
        revised = self.run_card(changed)
        self.assertIn("grey uniform", revised["prompt"])
        self.assertIn("red exit sign", revised["prompt"])
        self.assertNotEqual(revised["score_id"], first["score_id"])
        state = dr.Runner(root=self.root).state(revised["session_id"])
        dex = [d for d in state["decisions"] if d["target"] == {"path": "entities", "item_id": "dex"}]
        self.assertEqual([d["decision_id"] for d in dex], ["scene_action.entities.dex.entities", "scene_action.entities.dex.entities~2"])
        self.assertEqual(dex[1]["revision_of"], dex[0]["decision_id"])

    def test_problems_come_back_against_the_card(self):
        card = jail_card()
        card["performance"]["act_2"]["effort_weight"] = "heavy"
        with self.assertRaisesRegex(dr.RunFailed, "performance.act_2.effort_weight: 'heavy' is not in laban.effort.weight; choose one of: light, strong"):
            self.run_card(card)
        card = jail_card()
        card["staging"]["kinematic_plan"]["contacts"] = card["staging"]["kinematic_plan"]["contacts"][:1]
        with self.assertRaisesRegex(dr.RunFailed, r"kinematic_contact_unbound at staging\.kinematics: scene contact int_2"):
            self.run_card(card)
        card = jail_card()
        card["camera"]["shot_1"]["mood"] = "tense"
        with self.assertRaisesRegex(dr.RunFailed, "camera.shot_1.mood: not a field of this pass"):
            self.run_card(card)

    def test_brief_gives_every_pass_in_one_page(self):
        brief = dr.Runner(root=self.root).brief(jail_card()["ask"])
        for pass_id in dr.PASSES:
            self.assertIn(f"## {pass_id}:", brief)
        self.assertIn("menu laban.effort.weight: light = ", brief)
        self.assertIn("kinematics [required]", brief)


if __name__ == "__main__":
    unittest.main()
