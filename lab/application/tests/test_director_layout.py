"""The director layout: labelled prose in a director's order that drops no accepted field."""
from __future__ import annotations

import json
import re
import unittest

from lab.application.tests import test_directing_pipeline as pipeline
from lab.second_brain.src.fixed_sets import is_selection, read_catalog
from lab.second_brain.src.validate import REPO_ROOT

STRUCTURAL = {"id", "order", "relative", "kinematic_plan", "kind", "shows_initiation", "prop_state",
              "beat", "end_beat", "action", "actor", "caused_by", "target", "name", "duration_s", "min_s"}
SETTINGS = dict(project_id="cpcs-local-export", duration_seconds=15, prompt_format="prose", prompt_layout="director_v1")


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


class DirectorLayoutTests(unittest.TestCase):
    def client(self, beat_lengths=None):
        client = pipeline.DirectingPipelineTests()
        client.setUp()
        self.addCleanup(client.doCleanups)
        if beat_lengths is not None:
            beats = [d for d in client.data["proposal"]["decisions"] if d["sublayer"] == "beats"]
            for decision, length in zip(beats, beat_lengths):
                decision["values"]["duration_s"] = length
        client.complete()
        return client

    def finish(self, client, **settings):
        return client.result("direct.finish", dict(session_id=client.sid, build_settings={**SETTINGS, **settings}))

    def test_labelled_in_a_directors_order_and_nothing_accepted_is_dropped(self):
        client = self.client()
        result = self.finish(client)
        prompt = result["build"]["artifacts"]["prompt.txt"]["content"]
        text = flat(prompt)
        self.assertNotIn("User intent", prompt)
        self.assertNotIn(client.data["ask"], prompt)                      # the ask is not repeated
        starts = [prompt.index("\n" + label) if not prompt.startswith(label) else 0
                  for label in ("GOAL", "STYLE", "LOOK", "CAST", "WORLD", "STAGING", "MOTION", "BEAT 1", "BEAT 5", "END", "SOUND")]
        self.assertEqual(starts, sorted(starts))
        self.assertIn("GOAL      15s · 5 beats · 1 shot.", prompt)
        self.assertIn("SUMMARY  Rome walks up to Dex and stops chest to chest", prompt)
        self.assertIn("\nBEAT 1 (at least 2s) THE APPROACH\n", prompt)    # the fixture authors minimums only
        self.assertIn("SHOT 1", prompt)
        self.assertIn("Runs through BEAT 5.", text)                       # the shot spans beat_1..beat_5
        self.assertIn("DO 2 Rome shoves.", text)
        self.assertIn("Much faster than DO 1.", text)                     # a relative anchor names its printed label
        self.assertIn("After DO 2.", text)
        self.assertRegex(prompt, r"\n  CONTACT  the middle of Dex's chest\.")
        self.assertRegex(prompt, r"\n  REACT    Dex rocks back one step\. Settles: he plants his rear foot")
        self.assertRegex(prompt, r"\n  NOT      a punch; Dex falling;")
        strong = next(m for m in read_catalog(REPO_ROOT)["laban.effort.weight"]["members"] if m["term"] == "strong")
        self.assertIn(flat(strong["visible_wording"]), text)              # closed codes print their admitted wording
        self.assertNotIn("laban.effort", prompt)
        self.assertIn("MOTION    Rome stays screen-left of Dex throughout.", prompt)
        for coordinate in ('"x"', "look_at", "hip_height", "yaw_deg"):
            self.assertNotIn(coordinate, prompt)
        # Profile defaults the session never accepted are withheld from prose and recorded (REQ-AUD-12).
        self.assertNotRegex(prompt, r"\[control_[0-9a-f]+\]")
        self.assertNotIn("CONTROLS", prompt)
        self.assertNotIn("style.transform", prompt)
        report_dispositions = json.loads(result["build"]["artifacts"]["capability_report.json"]["content"])["dispositions"]
        withheld = sorted(d["path"] for d in report_dispositions if d["status"] == "withheld")
        self.assertIn("project.duration_seconds", withheld)
        self.assertTrue(all("." in path for path in withheld))
        losses = json.loads(result["build"]["artifacts"]["loss_report.json"]["content"])["losses"]
        self.assertEqual(sorted(l["path"] for l in losses if l["loss_type"] == "withheld_default"), withheld)
        self.assertLessEqual(max(len(line) for line in prompt.splitlines() if " = " not in line), 100)
        # Faithful projection: every authored text value of the scene reaches the prompt.
        score = result["score"]
        with_actions = {a["beat"] for a in score["actions"]}
        missing = []
        for path in ("scenes", "entities", "beats", "actions", "interactions", "shots"):
            for item in score[path]:
                for key, value in item.items():
                    if key in STRUCTURAL or is_selection(value):
                        continue
                    for leaf in value if isinstance(value, list) else [value]:
                        if isinstance(leaf, str) and flat(leaf).rstrip(".") not in text and flat(leaf).upper() not in text:
                            missing.append(f"{path}.{item['id']}.{key}")
        self.assertEqual(missing, [])
        report = json.loads(result["build"]["artifacts"]["capability_report.json"]["content"])
        self.assertEqual((report["timing_projection"]["layout"], report["timing_projection"]["printed_form"]), ("director_v1", "minimums"))
        self.assertEqual(report["kinematics"]["prose_projection"], "words")
        default = self.finish(client, prompt_layout="default")["build"]["artifacts"]["prompt.txt"]["content"]
        self.assertNotIn("User intent", default)                          # a directed scene never prints the raw ask
        self.assertNotIn("style.transform", default)
        self.assertTrue(default.startswith("Scene 1: "))
        self.assertEqual(self.finish(client)["build"]["artifacts"]["prompt.txt"]["content"], prompt)   # deterministic

    def test_authored_beat_lengths_print_in_the_beat_heading(self):
        client = self.client(beat_lengths=[3.0, 2.5, 3.0, 3.5, 3.0])
        result = self.finish(client)
        prompt = result["build"]["artifacts"]["prompt.txt"]["content"]
        for heading in ("BEAT 1 (3s) THE APPROACH", "BEAT 2 (2.5s) THE SHOVE", "BEAT 4 (3.5s) THE DRIVE INTO THE BARS"):
            self.assertIn("\n" + heading + "\n", prompt)
        self.assertNotIn("at least", prompt)
        report = json.loads(result["build"]["artifacts"]["capability_report.json"]["content"])
        self.assertEqual(report["timing_projection"]["printed_form"], "lengths")
        self.assertEqual(report["timing_projection"]["schedule_status"], "resolved")

    def test_an_evidence_based_ceiling_refuses_long_prompts_and_names_the_blocks(self):
        client = self.client()
        built = self.finish(client)
        policy = json.loads(built["build"]["artifacts"]["capability_report.json"]["content"])["output_policy"]
        self.assertEqual((policy["limit_chars"], policy["limit_source"]), (14000, "owner_default_2026_10_04"))
        self.assertEqual(policy["chars"], len(built["build"]["artifacts"]["prompt.txt"]["content"]))
        refused = client.call("direct.finish", dict(session_id=client.sid, build_settings={**SETTINGS, "prompt_char_limit": 1500}))
        self.assertEqual(refused["status"], "error")
        message = refused["error"]["message"]
        self.assertRegex(message, r"^PROMPT_OVER_LIMIT: \d+ characters, limit 1500 \(requested\)\. Largest blocks: ")
        self.assertIn("BEAT 1 · SHOT 1", message)             # names the blocks to tighten; nothing is cut
        raised = self.finish(client, prompt_char_limit=20000)
        self.assertEqual(json.loads(raised["build"]["artifacts"]["capability_report.json"]["content"])["output_policy"]["limit_source"], "requested")
        self.assertEqual(raised["build"]["artifacts"]["prompt.txt"]["content"], built["build"]["artifacts"]["prompt.txt"]["content"])

    def test_the_layout_needs_the_prose_carrier(self):
        client = self.client()
        response = client.call("direct.finish", dict(session_id=client.sid, build_settings={**SETTINGS, "prompt_format": "json"}))
        self.assertEqual(response["status"], "error")
        self.assertIn("director_v1 requires the prose carrier", response["error"]["message"])


if __name__ == "__main__":
    unittest.main()
