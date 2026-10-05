"""A card may name a scene item by its own spelling wherever it references one (plan slice 5, second timed run).

`why`, `cite` and `ask_spans` accept `scene.scene_1`; `uses` accepted only `scenes.scene_1`, and the second timed
fresh-agent run (2026-10-05) stopped once on `uses: {light_color: [scene.scene_1]}`.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.application import direct_runner as dr
from lab.application.tests.test_direct_runner import jail_card
from lab.second_brain.tests.test_directing_session import fixture_root


class CardSpellingTests(unittest.TestCase):
    def test_uses_accept_the_cards_own_spelling(self):
        with tempfile.TemporaryDirectory() as folder:
            root = fixture_root(Path(folder))
            card = jail_card()
            card["uses"]["light_color"] = ["scene.scene_1", "shot.shot_1"]
            result = dr.Runner(root=root).run(card)
            state = dr.Runner(root=root).state(result["session_id"])
            light = next(d for d in state["decisions"] if d["pass_id"] == "light_color")
            self.assertIn("scene_action.scenes.scene_1.scene", light["inputs"])
            self.assertTrue(any(i.startswith("camera.shots.shot_1.") for i in light["inputs"]))

    def test_an_unknown_reference_is_still_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            card = jail_card()
            card["uses"]["light_color"] = ["scene.scene_9"]
            with self.assertRaisesRegex(dr.RunFailed, r"uses 'scenes?\.scene_9', which is not an accepted choice this pass can read"):
                dr.Runner(root=fixture_root(Path(folder))).run(card)


if __name__ == "__main__":
    unittest.main()
