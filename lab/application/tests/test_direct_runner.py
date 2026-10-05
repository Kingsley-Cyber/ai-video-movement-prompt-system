"""One scene card runs a whole directing session through the public operations (Codex audit REQ-AUD-11)."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from lab.application import direct_runner as dr
from lab.second_brain.src.validate import REPO_ROOT
from lab.second_brain.tests.test_directing_session import fixture_root


EXAMPLE = REPO_ROOT / "handoff/direct_scene/reference/example_card.yaml"


def jail_card() -> dict:
    """The on-disk example card (the jail fixture); every test here proves it still runs."""
    return yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))


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
        self.assertIn("BEAT 2 (2.5s) THE SHOVE", prompt)
        self.assertIn("project.duration_seconds", result["withheld_defaults"])
        state = dr.Runner(root=self.root).state(result["session_id"])
        duration = next(d for d in state["decisions"] if d["decision_id"] == "scene_action.scenes.scene_1.scene.duration")
        self.assertEqual((duration["source_status"], duration["lock"], duration["evidence_uses"][0]["text"]),
                         ("user_explicit", True, "15 seconds"))
        effort = next(d for d in state["decisions"] if d["decision_id"] == "performance.actions.act_2.effort_weight")
        self.assertEqual(effort["values"]["effort_weight"]["code"], "laban.effort.weight.strong")
        self.assertEqual(effort["inputs"], ["scene_action.actions.act_2.actions"])
        self.assertEqual(effort["justification"], "A shove read from the feet up, so the push has visible weight.")
        light = next(d for d in state["decisions"] if d["pass_id"] == "light_color")
        self.assertEqual(light["justification"], "No reason given in the card.")     # never an invented reason
        self.assertTrue(all(i.startswith("camera.shots.shot_1.") for i in light["inputs"]))
        shot = next(d for d in state["decisions"] if d["decision_id"] == "camera.shots.shot_1.framing")
        self.assertEqual(shot["inputs"], ["scene_action.beats.beat_1.beats", "scene_action.beats.beat_5.beats"])
        self.assertEqual(result["skips_without_reason"], [])
        self.assertIn("light_color.scenes.scene_1.light", result["reasons_missing_for"])
        scene = next(d for d in state["decisions"] if d["decision_id"] == "scene_action.scenes.scene_1.scene")
        self.assertNotEqual(scene["justification"], "No reason given in the card.")      # keyed by the card's own name

    def test_a_rerun_reuses_accepted_work_and_a_change_cascades_by_itself(self):
        card = jail_card()
        first = self.run_card(card)
        again = self.run_card(card)
        self.assertEqual(again["passes"], [f"{p}: unchanged" for p in dr.PASSES])
        self.assertEqual((again["score_id"], again["prompt"]), (first["score_id"], first["prompt"]))
        changed = copy.deepcopy(card)
        changed["scene_action"]["entities"]["dex"]["description"] = "a lean man in his 20s with a shaved head, in a grey uniform"
        changed["light_color"]["lighting"] = "Overhead fluorescents and one red exit sign keep faces readable."
        with self.assertRaisesRegex(dr.RunFailed, "their card sections are unchanged: performance, staging, camera, style, audio, synthesis"):
            self.run_card(changed)              # dependants are not re-stamped until the author confirms them
        revised = dr.Runner(root=self.root).run(changed, confirm={"all"})
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

    def test_reason_only_edits_recheck_by_themselves_and_a_stop_cannot_be_bypassed(self):
        card = jail_card()
        first = self.run_card(card)
        self.assertIn("light_color.scenes.scene_1.light", first["reasons_missing_for"])
        reasons = copy.deepcopy(card)
        reasons["why"]["light_color"] = "Fluorescents keep both faces and the contact readable."
        reasons["why"]["actions.act_1"] = "An unhurried walk sets the speed baseline."
        again = self.run_card(reasons)                                    # no --confirm needed
        self.assertNotIn("light_color.scenes.scene_1.light", again["reasons_missing_for"])
        self.assertLess(again["reasons_missing"], first["reasons_missing"])
        self.assertIn("audio: accepted (0 revised) (rechecked: only reasons changed upstream)", again["passes"])
        meaning = copy.deepcopy(reasons)
        meaning["scene_action"]["entities"]["dex"]["description"] = "a lean man in his 20s in a grey uniform"
        with self.assertRaisesRegex(dr.RunFailed, "card sections are unchanged"):
            self.run_card(meaning)
        with self.assertRaisesRegex(dr.RunFailed, "card sections are unchanged"):
            self.run_card(meaning)                                        # a plain rerun is still stopped
        self.assertIn("grey uniform", dr.Runner(root=self.root).run(meaning, confirm={"all"})["prompt"])

    def test_action_lines_start_with_a_capital(self):
        card = jail_card()
        card["scene_action"]["entities"]["rome"]["name"] = "the big man"
        self.assertIn("DO 1     The big man walks up", self.run_card(card)["prompt"])

    def test_python_never_invents_what_a_scene_wide_choice_relied_on(self):
        card = jail_card()
        del card["uses"]["light_color"]
        with self.assertRaisesRegex(dr.RunFailed, "light_color.light: say which accepted choices this stack relies on"):
            self.run_card(card)
        card = jail_card()
        card["uses"]["audio"] = ["shots.shot_9"]
        with self.assertRaisesRegex(dr.RunFailed, "uses 'shots.shot_9', which is not an accepted choice this pass can read"):
            self.run_card(card)

    def test_the_receipt_times_brief_to_prompt(self):
        runner = dr.Runner(root=self.root)
        runner.brief(jail_card()["ask"])
        result = self.run_card(jail_card())
        self.assertIsNotNone(result["end_to_end_since_brief_s"])
        self.assertEqual(result["run_attempts"], 1)
        receipt = json.loads(runner.receipt_path(result["session_id"]).read_text())
        self.assertEqual([a["outcome"] for a in receipt["attempts"]], ["built"])

    def test_accepted_style_supersedes_the_profile_transform_everywhere(self):
        card = jail_card()
        card["ask"] = "An anime jail fight scene, 15 seconds"
        legacy = dr.Runner(root=self.root).call("score.build", dict(text=card["ask"]))["score"]
        self.assertIn("style.transform", [c["path"] for c in legacy["provider_neutral_controls"]])   # undirected: unchanged
        result = self.run_card(card)
        score = json.loads(result["artifacts"]["canonical_score.json"]["content"])
        self.assertNotIn("style.transform", [c["path"] for c in score["provider_neutral_controls"]])
        lineage = score["provenance"]["fields"]["style.transform"]
        self.assertEqual((lineage["reason"], lineage["winner"]), ("superseded_by_accepted_direction", None))
        self.assertIn("profile://style/anime_sakuga_action_v3", [c["source"] for c in lineage["candidates"]])
        self.assertIn("profile_default_superseded", [w["code"] for w in score["warnings"]])
        structured = dr.Runner(root=self.root).call("direct.finish", dict(session_id=result["session_id"], build_settings=dict(
            project_id="cpcs-local-export", duration_seconds=15, prompt_format="json")))
        self.assertNotIn("style.transform", structured["build"]["artifacts"]["prompt.txt"]["content"])

    def test_check_finds_plan_and_binding_problems_before_a_run(self):
        self.assertEqual(dr.check_card(jail_card(), root=self.root), [])
        card = jail_card()
        card["staging"]["kinematic_plan"]["contacts"] = card["staging"]["kinematic_plan"]["contacts"][:1]
        card["staging"]["kinematic_plan"]["camera"][0]["look_at"] = list(card["staging"]["kinematic_plan"]["camera"][0]["pos"])
        problems = dr.check_card(card, root=self.root)
        self.assertTrue(any(p.startswith("CAMERA_AXIS_DEGENERATE") for p in problems))
        self.assertTrue(any(p.startswith("kinematic_contact_unbound") and "int_2" in p for p in problems))

    def test_brief_gives_every_pass_in_one_page(self):
        brief = dr.Runner(root=self.root).brief(jail_card()["ask"] + "\n")     # trailing whitespace opens the same session
        self.assertIn("MOTION PLAN (kinematic_plan, validated under cpcs-kinematics/1.2", brief)
        self.assertIn("support = parts joined by '+'", brief)
        self.assertIn("handoff/direct_scene/reference/example_card.yaml", brief)
        for pass_id in dr.PASSES:
            self.assertIn(f"\n{pass_id.upper()} (", brief)
        self.assertIn("  laban.effort.weight: light = buoyant touch; strong = the body visibly commits mass", brief)
        self.assertLess(len(brief), 10000)                                      # one compact page (owner's 240 s target)
        self.assertNotIn("A jail fight scene", brief)                           # the ask is not repeated
        self.assertIn("kinematics* (kinematic_plan)", brief)


if __name__ == "__main__":
    unittest.main()
