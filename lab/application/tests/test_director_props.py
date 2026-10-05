"""Tracked props print from the replayed state in director prose (plan slice 1 + 5, the bottle canary).

The director layout printed an action's `needs` and `changes` as a flattened field dump in the DO line
("object: the cap; state: off the bottle; object: the bottle; state: open"), which loses which state
belongs to which object and repeats the PROP row, and printed a starting prop_state as a raw mapping with
"None". The PROP row, derived from the ledger replay, is the one place prop facts print in prose.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from lab.application import direct_runner as dr
from lab.compiler import carriers
from lab.second_brain.src.validate import REPO_ROOT
from lab.second_brain.tests.test_directing_session import fixture_root

BOTTLE = REPO_ROOT / "handoff/direct_scene/reference/bottle_card.yaml"


def bottle_card() -> dict:
    return dr.load_card(BOTTLE.read_text(encoding="utf-8"))


class DirectorPropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = fixture_root(Path(cls.temporary.name))
        cls.result = dr.Runner(root=cls.root).run(bottle_card())
        cls.prompt = cls.result["prompt"]

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_prop_facts_print_once_from_the_replayed_state(self):
        for leaked in ("Changes:", "Needs:", "None", "object:", "held by:"):
            self.assertNotIn(leaked, self.prompt)
        self.assertIn("  DO 2     Maya twists the cap off in two short turns. Target: the cap. With: right hand.", self.prompt)
        self.assertIn("  PROP     the bottle: open; in her left hand; held by Maya in left hand(s). the cap: off the\n"
                      "           bottle; in her right hand; held by Maya in right hand(s).", self.prompt)
        after_cap_down = self.prompt.split("BEAT 3")[1].split("BEAT 4")[0]
        self.assertIn("the cap: off the\n           bottle; on the counter.", after_cap_down)

    def test_objects_start_from_their_declared_state(self):
        self.assertIn("the bottle: a clear glass bottle of sparkling water, label facing the camera. State at\n"
                      "          start: closed; on the counter.", self.prompt)
        self.assertIn("the cap: a green metal screw cap. State at start: screwed on; on the bottle.", self.prompt)

    def test_the_structured_carriers_keep_needs_and_changes(self):
        card = bottle_card()
        card["prompt_format"], card["hybrid_sections"] = "hybrid", ["prose", "yaml"]
        sections = carriers.read_hybrid(dr.Runner(root=self.root).run(card)["prompt"])
        self.assertEqual(sections["prose"], self.prompt)
        twist = next(a for a in yaml.safe_load(sections["yaml"])["actions"] if a["id"] == "act_2")
        self.assertEqual(twist["changes"], card["scene_action"]["actions"]["act_2"]["changes"])
        self.assertEqual(twist["needs"], card["scene_action"]["actions"]["act_2"]["needs"])

    def test_a_changed_prop_state_reaches_prose_and_every_structured_section(self):
        card = bottle_card()
        card["scene_action"]["actions"]["act_3"]["changes"][0]["location"] = "beside the bottle"
        card["synthesis"]["end_state"] = "Maya holds the open bottle at her chin after the sip; the cap lies beside the bottle."
        card["prompt_format"], card["hybrid_sections"] = "hybrid", ["prose", "yaml", "json", "xml"]
        with tempfile.TemporaryDirectory() as folder:     # its own session, so the shared one stays unrevised
            runner = dr.Runner(root=fixture_root(Path(folder)))
            runner.run(bottle_card())
            sections = carriers.read_hybrid(runner.run(card, confirm={"all"})["prompt"])
        self.assertIn("the cap: off the\n           bottle; beside the bottle.", sections["prose"].split("BEAT 3")[1])
        for structured in (yaml.safe_load(sections["yaml"]), json.loads(sections["json"]), carriers.read_xml(sections["xml"])):
            cap_down = next(a for a in structured["actions"] if a["id"] == "act_3")
            self.assertEqual(cap_down["changes"][0]["location"], "beside the bottle")


if __name__ == "__main__":
    unittest.main()
