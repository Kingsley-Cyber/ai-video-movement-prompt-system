"""The runner times the owner's target from the original request, not from the brief (plan slice 0)."""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from lab.application import direct_runner as dr
from lab.application.tests.test_direct_runner import jail_card
from lab.second_brain.tests.test_directing_session import fixture_root


class RequestClockTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = fixture_root(Path(temporary.name))
        self.runner = dr.Runner(root=self.root)

    def receipt(self, session_id):
        return json.loads(self.runner.receipt_path(session_id).read_text())

    def test_a_declared_request_time_starts_the_clock_and_the_intervals_add_up(self):
        requested = time.time() - 30
        self.runner.brief(jail_card()["ask"], requested_at=requested)
        broken = jail_card()
        broken["performance"]["act_2"]["effort_weight"] = "heavy"
        with self.assertRaises(dr.RunFailed):
            dr.Runner(root=self.root).run(broken)
        result = dr.Runner(root=self.root).run(jail_card())
        receipt = self.receipt(result["session_id"])
        self.assertEqual((receipt["requested_at"], receipt["requested_at_source"]), (requested, "operator_flag"))
        self.assertTrue(all("started_at" in a for a in receipt["attempts"]))
        clock = result["clock"]
        self.assertEqual(clock["requested_at_source"], "operator_flag")
        self.assertGreaterEqual(clock["request_to_brief_s"], 29.9)
        self.assertGreater(clock["repair_s"], 0)                     # the stopped attempt came first
        self.assertGreater(clock["brief_python_s"], 0)
        intervals = clock["request_to_brief_s"] + clock["authoring_s"] + clock["repair_s"] + clock["final_run_s"]
        self.assertAlmostEqual(intervals, result["first_prompt_since_request_s"], delta=0.3)
        self.assertGreaterEqual(result["end_to_end_since_request_s"], result["end_to_end_since_brief_s"] + 29.9)

    def test_the_first_usable_prompt_stays_the_target_figure_after_a_rebuild(self):
        self.runner.brief(jail_card()["ask"], requested_at=time.time() - 5)
        first = dr.Runner(root=self.root).run(jail_card())
        card = jail_card()
        card["light_color"]["lighting"] = "Overhead fluorescents and one red exit sign keep faces readable."
        later = dr.Runner(root=self.root).run(card, confirm={"all"})
        self.assertEqual(later["first_prompt_since_request_s"], first["first_prompt_since_request_s"])
        self.assertGreaterEqual(later["end_to_end_since_request_s"], first["end_to_end_since_request_s"])

    def test_without_a_declared_request_time_the_origin_is_unknown_never_guessed(self):
        self.runner.brief(jail_card()["ask"])
        result = dr.Runner(root=self.root).run(jail_card())
        self.assertIsNone(result["end_to_end_since_request_s"])
        self.assertIsNone(result["first_prompt_since_request_s"])
        self.assertEqual((result["clock"]["requested_at_source"], result["clock"]["request_to_brief_s"]), (None, None))
        self.assertIsNotNone(result["clock"]["authoring_s"])
        self.assertNotIn("requested_at", self.receipt(result["session_id"]))

    def test_a_request_time_in_the_future_or_after_the_brief_is_refused(self):
        with self.assertRaisesRegex(dr.RunFailed, "in the future"):
            self.runner.brief(jail_card()["ask"], requested_at=time.time() + 600)
        with self.assertRaisesRegex(dr.RunFailed, "not a time"):
            self.runner.brief(jail_card()["ask"], requested_at=float("nan"))
        self.runner.brief(jail_card()["ask"])
        session_id = self.runner.start(jail_card()["ask"], "seedance-2.0", None)["session_id"]
        brief_at = self.receipt(session_id)["brief_at"]
        with self.assertRaisesRegex(dr.RunFailed, "after this session's brief"):
            self.runner.brief(jail_card()["ask"], requested_at=brief_at + 0.001)
        self.assertNotIn("requested_at", self.receipt(session_id))

    def test_a_second_brief_never_moves_the_origin(self):
        first = time.time() - 60
        self.runner.brief(jail_card()["ask"], requested_at=first)
        self.runner.brief(jail_card()["ask"], requested_at=first - 600)
        session_id = self.runner.start(jail_card()["ask"], "seedance-2.0", None)["session_id"]
        self.assertEqual(self.receipt(session_id)["requested_at"], first)

    def test_the_command_line_takes_the_request_time(self):
        parsed = dr.parser().parse_args(["brief", "--ask-file", "ask.txt", "--requested-at", "1759650000"])
        self.assertEqual(parsed.requested_at, 1759650000.0)


if __name__ == "__main__":
    unittest.main()
