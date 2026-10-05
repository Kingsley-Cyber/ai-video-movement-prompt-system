"""Defects the timed fresh-agent run found on 2026-10-05, each reproduced before its repair (plan slice 5).

- "10-second" in an ask was not read as the requested length, so the user's duration was neither recorded as
  user_explicit nor locked.
- `ask_spans` ignored the `scene.scene_1` spelling that `why` and `cite` accept, so a user span was dropped.
- A choice deleted from the card stayed accepted: alone it was refused with an unexplained
  "pass_already_accepted"; beside another revision of the same pass it kept printing.
"""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from lab.application import direct_runner as dr
from lab.application.tests.test_direct_runner import jail_card
from lab.application.tests.test_director_props import bottle_card
from lab.second_brain.tests.test_directing_session import fixture_root


class TimedRunRepairTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = fixture_root(Path(temporary.name))

    def decision(self, result, decision_id):
        state = dr.Runner(root=self.root).state(result["session_id"])
        return next((d for d in state["decisions"] if d["decision_id"] == decision_id), None)

    def test_a_hyphenated_length_is_the_users_locked_duration(self):
        result = dr.Runner(root=self.root).run(bottle_card())
        duration = self.decision(result, "scene_action.scenes.scene_1.scene.duration")
        self.assertIsNotNone(duration)
        self.assertEqual((duration["source_status"], duration["lock"], duration["evidence_uses"][0]["text"]),
                         ("user_explicit", True, "10-second"))

    def test_ask_spans_accept_the_spelling_why_and_cite_accept(self):
        card = jail_card()
        card["ask_spans"] = {"scene.scene_1": ["A jail fight scene"]}
        scene = self.decision(dr.Runner(root=self.root).run(card), "scene_action.scenes.scene_1.scene")
        self.assertEqual(scene["source_status"], "user_explicit")
        self.assertIn({"kind": "ask_span", "start": 0, "end": 18, "text": "A jail fight scene"}, scene["evidence_uses"])

    def test_a_choice_removed_from_the_card_is_refused_by_name(self):
        first = dr.Runner(root=self.root).run(jail_card())
        removed = jail_card()
        del removed["performance"]["act_2"]["shape"]
        with self.assertRaisesRegex(dr.RunFailed, r"performance: the card no longer has performance\.actions\.act_2\.shape"):
            dr.Runner(root=self.root).run(removed)
        alongside = copy.deepcopy(removed)                       # beside another revision it used to keep printing
        alongside["performance"]["act_2"]["body"] = "The rear foot drives first; the palms arrive last."
        with self.assertRaisesRegex(dr.RunFailed, r"variant"):
            dr.Runner(root=self.root).run(alongside)
        self.assertEqual(dr.Runner(root=self.root).run(jail_card())["prompt"], first["prompt"])


if __name__ == "__main__":
    unittest.main()
