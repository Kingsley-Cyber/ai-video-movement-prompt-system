"""A scene card is structured authoring input: a repeated key or malformed YAML is refused with its line,
never resolved silently (plan slice 3; Codex carrier contract: reject duplicate keys and malformed input).
"""
from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import yaml

from lab.application import direct_runner as dr
from lab.application.tests.test_direct_runner import EXAMPLE


class CardInputTests(unittest.TestCase):
    def test_the_example_card_loads_exactly_as_before(self):
        text = EXAMPLE.read_text(encoding="utf-8")
        self.assertEqual(dr.load_card(text), yaml.safe_load(text))

    def test_a_repeated_key_is_refused_where_it_repeats(self):
        card = "ask: a scene\nscene_action:\n  actions:\n    act_1: {verb: walks}\n    act_1: {verb: runs}\n"
        with self.assertRaisesRegex(dr.RunFailed, r"^card line 5: duplicate key 'act_1' \(first at line 4\)"):
            dr.load_card(card)
        with self.assertRaisesRegex(dr.RunFailed, r"^card line 3: duplicate key 'why'"):
            dr.load_card("ask: a\nwhy: {a: b}\nwhy: {c: d}\n")

    def test_malformed_or_non_mapping_cards_are_refused(self):
        with self.assertRaisesRegex(dr.RunFailed, r"^card is not valid YAML at line 2"):
            dr.load_card("ask: a\n  scene_action: [unclosed\n")
        with self.assertRaisesRegex(dr.RunFailed, r"^card must be a mapping"):
            dr.load_card("- just\n- a list\n")

    def test_the_command_line_stops_on_a_repeated_key(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "card.yaml"
            path.write_text("ask: a scene\nask: another\n", encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as stopped:
                dr.main(["check", "--card", str(path)])
            self.assertEqual(stopped.exception.code, 1)
            self.assertIn("card line 2: duplicate key 'ask'", out.getvalue())


if __name__ == "__main__":
    unittest.main()
