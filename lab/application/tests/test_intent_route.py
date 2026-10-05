"""An ask the intent router cannot place in a domain is caught at the brief, not after every pass (plan slice 5 repair).

Timed fresh-agent run, 2026-10-05: an ask about "two fighters" matched no domain profile, so its score needed
video_domain and audience_effect. The runner accepted all eight passes and only then stopped at finish with
"build compiler requires a ready canonical score"; investigating and restarting cost most of a 585-second
request. The brief now prints the route and the fix, a domain profile reaches direct.start through its existing
profile_overrides from both the brief and the card, and check and run refuse an unrouted ask before any
session work.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.application import direct_runner as dr
from lab.application.tests.test_direct_runner import jail_card
from lab.second_brain.tests.test_directing_session import fixture_root

UNROUTED = "Two fighters in a jail dayroom, 15 seconds"


class IntentRouteTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = fixture_root(Path(temporary.name))

    def card(self, profile=None):
        card = jail_card()
        card["ask"] = UNROUTED
        if profile is not None:
            card["profile"] = profile
        return card

    def test_the_brief_shows_the_route(self):
        brief = dr.Runner(root=self.root).brief(jail_card()["ask"])
        self.assertIn("\nINTENT    action profile (task action_sequence; effect readable_excitement).\n", brief)
        self.assertNotIn("NEEDS A DOMAIN", brief)

    def test_an_unrouted_brief_stops_at_once_with_the_fix(self):
        runner = dr.Runner(root=self.root)
        with self.assertRaises(dr.RunFailed) as stopped:
            runner.brief(UNROUTED, research=True)
        message = str(stopped.exception)
        self.assertTrue(message.startswith("NEEDS A DOMAIN: no domain profile matched this ask"))
        self.assertIn("audience_effect, video_domain", message)
        self.assertIn("--profile <name>", message)
        self.assertIn(" action,", message)
        self.assertEqual([c["operation"] for c in runner.calls], ["intent.normalize"])   # no session, no search

    def test_a_profile_routes_the_brief_and_the_card_to_one_session(self):
        brief = dr.Runner(root=self.root).brief(UNROUTED, profiles=["action"])
        self.assertIn("\nINTENT    action profile (task action_sequence; effect readable_excitement).\n", brief)
        session_id = brief.split()[1]
        result = dr.Runner(root=self.root).run(self.card(profile=["action"]))
        self.assertEqual(result["session_id"], session_id)
        self.assertTrue(result["prompt"].startswith("GOAL      15s"))

    def test_run_and_check_refuse_an_unrouted_ask_before_any_session_work(self):
        runner = dr.Runner(root=self.root)
        with self.assertRaisesRegex(dr.RunFailed, "no domain profile matched this ask"):
            runner.run(self.card())
        self.assertEqual([c["operation"] for c in runner.calls], ["intent.normalize"])
        self.assertTrue(any("no domain profile matched this ask" in p for p in dr.check_card(self.card())))
        self.assertFalse(any("domain profile" in p for p in dr.check_card(self.card(profile=["action"]))))

    def test_an_unknown_profile_is_refused_before_any_session_work(self):
        runner = dr.Runner(root=self.root)
        with self.assertRaisesRegex(dr.RunFailed, "intent.normalize"):
            runner.run(self.card(profile=["brawl"]))
        self.assertEqual([c["operation"] for c in runner.calls], ["intent.normalize"])


if __name__ == "__main__":
    unittest.main()
