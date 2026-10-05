"""The build's records say what the prompt actually printed (plan slice 5, third timed run).

The director layout's loss record for beats said beat summaries stay only in canonical JSON and the JSON carrier,
while every beat prints a SUMMARY line, so the loss report contradicted the prompt beside it.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lab.application import direct_runner as dr
from lab.application.tests.test_direct_runner import jail_card
from lab.second_brain.tests.test_directing_session import fixture_root


class HonestRecordTests(unittest.TestCase):
    def test_the_beats_loss_record_matches_the_director_prompt(self):
        with tempfile.TemporaryDirectory() as folder:
            result = dr.Runner(root=fixture_root(Path(folder))).run(jail_card())
        self.assertIn("\n  SUMMARY  Rome walks up to Dex and stops chest to chest", result["prompt"])
        losses = json.loads(result["artifacts"]["loss_report.json"]["content"])["losses"]
        beats = next(loss for loss in losses if loss["path"] == "beats")
        self.assertIn("label, length and summary", beats["reason"])
        self.assertNotIn("Beat summaries remain", beats["reason"])


if __name__ == "__main__":
    unittest.main()
