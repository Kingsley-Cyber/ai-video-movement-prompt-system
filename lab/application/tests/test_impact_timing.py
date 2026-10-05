"""A hit's effect cannot come before the hit (plan slice 1, reaction timing; owner approved 2026-10-05).

The motion plan has a clock: a body that takes an impact must already have been touched by a plan contact.
An anticipatory move is the body's own (push_off), not an impact, so it is not caught by this check.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.application import direct_runner as dr
from lab.application.tests.test_direct_runner import jail_card
from lab.second_brain.tests.test_directing_session import fixture_root


def impact_findings(card):
    return [p for p in dr.check_card(card) if p.startswith("kinematic_impact_before_contact")]


class ImpactTimingTests(unittest.TestCase):
    def test_the_example_plan_is_clean(self):
        self.assertEqual(dr.check_card(jail_card()), [])

    def test_a_reaction_before_the_shove_lands_is_refused(self):
        card = jail_card()
        card["staging"]["kinematic_plan"]["force_events"][0]["t"] = 3.5    # Dex is hit half a second before the palms arrive
        self.assertEqual(impact_findings(card), [
            "kinematic_impact_before_contact: Dex takes an impact at 3.5 s, but no plan contact acts on Dex until 4.0 s; "
            "a hit's effect cannot come before the hit. Move the impact to its contact, or make an early move the "
            "body's own (push_off)."])

    def test_an_impact_on_a_body_no_contact_ever_touches_is_refused(self):
        card = jail_card()
        card["staging"]["kinematic_plan"]["contacts"] = []
        self.assertEqual(len(impact_findings(card)), 2)
        self.assertIn("no plan contact acts on Dex at all", impact_findings(card)[0])

    def test_an_impact_at_or_after_the_first_contact_passes(self):
        card = jail_card()
        card["staging"]["kinematic_plan"]["force_events"][0]["t"] = 4.05
        self.assertEqual(impact_findings(card), [])

    def test_staging_refuses_it_where_the_card_is_run(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        card = jail_card()
        card["staging"]["kinematic_plan"]["force_events"][0]["t"] = 3.5
        with self.assertRaisesRegex(dr.RunFailed, r"kinematic_impact_before_contact at staging\.kinematics: Dex takes an impact at 3\.5 s"):
            dr.Runner(root=fixture_root(Path(temporary.name))).run(card)


if __name__ == "__main__":
    unittest.main()
