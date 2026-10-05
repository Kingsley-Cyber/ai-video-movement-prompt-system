"""A directed scene's model-facing carriers carry only accepted direction (plans slices 3 and 5).

The timed fresh-agent run's YAML printed `camera.impact_shake_policy: decaying_post_event`, a profile default the
session never accepted, beside the accepted locked-off camera. Prose already withheld such defaults (REQ-AUD-12);
JSON, YAML and XML carried them. Every carrier of a directed scene now withholds them, and the canonical score
artifact keeps them with their dispositions and losses.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from lab.application import direct_runner as dr
from lab.application.tests.test_direct_runner import jail_card
from lab.compiler import carriers
from lab.second_brain.tests.test_directing_session import fixture_root


class CarrierDefaultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = fixture_root(Path(cls.temporary.name))
        cls.runner = dr.Runner(root=cls.root)
        cls.sid = cls.runner.run(jail_card())["session_id"]

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def build(self, **settings):
        finished = self.runner.call("direct.finish", dict(session_id=self.sid, build_settings=dict(
            project_id="cpcs-local-export", duration_seconds=15, **settings)))
        return finished["build"]["artifacts"]

    def test_every_carrier_of_a_directed_scene_withholds_unaccepted_defaults(self):
        artifacts = self.build(prompt_format="json")
        report = json.loads(artifacts["capability_report.json"]["content"])
        withheld = {d["path"] for d in report["dispositions"] if d["status"] == "withheld"}
        self.assertIn("camera.impact_shake_policy", withheld)
        payloads = {"json": json.loads(artifacts["prompt.txt"]["content"]),
                    "yaml": yaml.safe_load(self.build(prompt_format="yaml")["prompt.txt"]["content"]),
                    "xml": carriers.read_xml(self.build(prompt_format="xml")["prompt.txt"]["content"])}
        for name, payload in payloads.items():
            self.assertEqual(withheld & set(payload), set(), name)
            self.assertIn("actions", payload, name)
        canonical = json.loads(artifacts["canonical_score.json"]["content"])
        self.assertIn("camera.impact_shake_policy", {c["path"] for c in canonical["provider_neutral_controls"]})
        reasons = {d["reason"] for d in report["dispositions"] if d["status"] == "withheld"}
        self.assertEqual(reasons, {"Profile default not accepted in the directing session; accepted decisions carry the "
                                   "direction in every carrier. Kept in the canonical score."})


if __name__ == "__main__":
    unittest.main()
