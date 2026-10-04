"""Canonical clock (T1) and the per-build record of how a carrier printed it (T2)."""
from __future__ import annotations

import copy
import json
import unittest

from lab.compiler.build import compile_build, make_build_request
from lab.compiler.decisions import scene_from_decisions, validate_decisions
from lab.compiler.tests.test_build import ready_score
from lab.compiler.tests.test_labelled_skeleton import FIXTURES, build as skeleton_build, champion
from lab.second_brain.src.directing_session import load_pass_registry
from lab.second_brain.src.validate import REPO_ROOT
from lab.second_brain.tests.test_directing_session import fixture

CHAMPION_STARTS = [0, 2.5, 3.5, 5.5, 6.2, 7.7, 10, 11, 11.7, 14]
CHAMPION_ENDS = [2.5, 3.5, 5.5, 6.2, 7.7, 10, 11, 11.7, 14, 15]


def jail_decisions(durations=None, shots=False):
    decisions = copy.deepcopy(fixture()["proposal"]["decisions"])
    for decision in decisions:
        target = decision["target"]
        if target["path"] == "beats" and durations:
            decision["values"]["duration_s"] = durations[target["item_id"]]
    if shots:
        template = next(d for d in decisions if d["target"]["path"] == "beats")
        decisions.append(dict(template, decision_id="d_shot_1", sublayer="shots", inputs=[],
                              target=dict(path="shots", item_id="shot_1"),
                              values=dict(order=1, beat="beat_2", end_beat="beat_4", framing="medium two-shot")))
    return decisions


def jail_score(durations=None, shots=False):
    scene = scene_from_decisions(jail_decisions(durations, shots))
    overlay = dict(overlay_id="overlay_timeline", scope="scene_override", priority=0, values=scene,
                   locks=[], source_refs=["authored://timeline-test"])
    return ready_score("A fight in a county jail", overlays=[overlay])


def report(score, prompt_format):
    request = make_build_request(score, project_id="timeline-test", model="seedance-2.0",
                                 duration_seconds=15, prompt_format=prompt_format)
    return json.loads(compile_build(request)["capability_report.json"])


EVEN = {f"beat_{i}": 3 for i in range(1, 6)}


class CanonicalTimelineTests(unittest.TestCase):
    def test_champion_beat_lengths_resolve_to_an_exact_clock(self):
        artifacts = skeleton_build(champion())
        score = json.loads(artifacts["canonical_score.json"])
        timeline = score["timeline"]
        self.assertEqual(timeline["status"], "resolved")
        self.assertEqual([b["start_s"] for b in timeline["beats"]], CHAMPION_STARTS)
        self.assertEqual([b["end_s"] for b in timeline["beats"]], CHAMPION_ENDS)
        self.assertEqual(timeline["total_s"], 15)
        self.assertEqual(artifacts["prompt.txt"], (FIXTURES / "corridor_champion.txt").read_bytes())

    def test_skeleton_build_records_printed_lengths_beside_the_plan(self):
        record = json.loads(skeleton_build(champion())["capability_report.json"])["timing_projection"]
        self.assertEqual(record["kind"], "carrier_choice")
        self.assertFalse(record["provider_adherence_claim"])
        self.assertEqual((record["carrier"], record["layout"]), ("prose", "labelled_skeleton_v1"))
        self.assertEqual(record["printed_form"], "lengths")
        self.assertEqual(record["schedule_status"], "resolved")
        self.assertEqual([b["start_s"] for b in record["planned"]], CHAMPION_STARTS)

    def test_minimums_only_stay_unresolved_and_carriers_record_their_form(self):
        score = jail_score()
        self.assertEqual(score["timeline"]["status"], "unresolved")
        self.assertEqual(score["timeline"]["reason"], "beat_durations_missing")
        self.assertEqual(score["timeline"]["beats"], [])
        seedance = report(score, "prose")["timing_projection"]
        self.assertEqual(seedance["printed_form"], "order_only")
        self.assertEqual(seedance["schedule_status"], "unresolved")
        self.assertEqual(report(score, "json")["timing_projection"]["printed_form"], "minimums")

    def test_resolved_clock_gives_event_and_shot_windows(self):
        score = jail_score(EVEN, shots=True)
        timeline = score["timeline"]
        self.assertEqual(timeline["status"], "resolved")
        windows = {e["ref"]: e["window_s"] for e in timeline["events"]}
        self.assertEqual(windows["actions.act_3"], [6, 9])
        self.assertEqual(windows["interactions.int_2"], [9, 12])
        self.assertEqual(windows["shots.shot_1"], [3, 12])
        self.assertEqual(report(score, "json")["timing_projection"]["printed_form"], "lengths")
        self.assertEqual(report(score, "prose")["timing_projection"]["printed_form"], "order_only")
        self.assertEqual(jail_score(EVEN, shots=True)["timeline"], timeline)

    def test_directing_rejects_lengths_that_miss_the_scene_or_undercut_a_minimum(self):
        spec = load_pass_registry(REPO_ROOT)["passes"][0]
        packet = {"constraints": {"requested_duration_s": 15}, "steering": "Direct."}
        codes = lambda ds: [e["code"] for e in validate_decisions(ds, spec, packet)]
        self.assertNotIn("beat_durations_mismatch", codes(jail_decisions(EVEN)))
        short = dict(EVEN, beat_5=2)
        self.assertIn("beat_durations_mismatch", codes(jail_decisions(short)))
        tiny = dict(EVEN, beat_1=0.5, beat_2=5.5)
        self.assertIn("beat_duration_below_minimum", codes(jail_decisions(tiny)))

    def test_scores_without_beats_carry_no_timeline_or_timing_record(self):
        score = ready_score("Make a casual phone video recommending this skincare product")
        self.assertNotIn("timeline", score)
        request = make_build_request(score, project_id="timeline-test")
        self.assertNotIn("timing_projection", json.loads(compile_build(request)["capability_report.json"]))


if __name__ == "__main__":
    unittest.main()
