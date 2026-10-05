"""A contact's accepted relative prints in director prose, like an action's (plan slice 5, second timed run).

The second timed fresh-agent run (2026-10-05) found the palm strike's accepted "much more intense than the parry"
in the YAML but nowhere in the prose, against the director layout's promise that no accepted field is dropped. The
jail example's drive into the bars carries the same kind of relative against the shove.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.application import direct_runner as dr
from lab.application.tests.test_direct_runner import jail_card
from lab.second_brain.tests.test_directing_session import fixture_root


class ContactRelativeTests(unittest.TestCase):
    def test_a_contact_relative_prints_against_its_anchor(self):
        with tempfile.TemporaryDirectory() as folder:
            prompt = dr.Runner(root=fixture_root(Path(folder))).run(jail_card())["prompt"]
        drive = prompt.split("BEAT 4")[1].split("BEAT 5")[0]
        self.assertIn("  CONTACT  Dex's midsection. After DO 4. Much more intense than the contact of DO 2.\n", drive)
        shove = prompt.split("BEAT 2")[1].split("BEAT 3")[0]
        self.assertIn("\n  CONTACT  the middle of Dex's chest.\n", shove)          # no relative declared, none printed


if __name__ == "__main__":
    unittest.main()
