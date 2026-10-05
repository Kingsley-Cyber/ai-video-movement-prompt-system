"""One accepted scene, the requested carriers (plan slice 3).

YAML, XML and JSON carry the same selected payload; a hybrid prints the requested sections in order under one
score, and its structured sections share its prose's selection. A carrier changes representation, never
choreography, and needs no model pass.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from lab.application import direct_runner as dr
from lab.application.tests.test_direct_runner import jail_card
from lab.compiler import carriers
from lab.second_brain.tests.test_directing_session import fixture_root

BASE = dict(project_id="cpcs-local-export", duration_seconds=15)
DIRECTOR = dict(prompt_layout="director_v1")


class RequestedCarrierTests(unittest.TestCase):
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
        finished = self.runner.call("direct.finish", dict(session_id=self.sid, build_settings=dict(BASE, **settings)))
        return finished["build"]["artifacts"]

    def prompt(self, **settings):
        return self.build(**settings)["prompt.txt"]["content"]

    def test_yaml_and_xml_carry_exactly_the_json_payload(self):
        payload = json.loads(self.prompt(prompt_format="json"))
        self.assertEqual(yaml.safe_load(self.prompt(prompt_format="yaml")), payload)
        xml = self.prompt(prompt_format="xml")
        self.assertTrue(xml.startswith(f'<cpcs_prompt carrier="xml" score_id="{payload["score_id"]}">\n'))
        self.assertEqual(carriers.read_xml(xml), payload)
        self.assertIn("kinematic_plan", payload["scenes"][0])       # the plan travels in every structured carrier

    def test_a_hybrid_prints_the_requested_sections_in_order_under_one_score(self):
        artifacts = self.build(prompt_format="hybrid", hybrid_sections=["prose", "yaml", "xml"], **DIRECTOR)
        text = artifacts["prompt.txt"]["content"]
        sections = carriers.read_hybrid(text)
        self.assertEqual(list(sections), ["prose", "yaml", "xml"])
        self.assertEqual(sections["prose"], self.prompt(prompt_format="prose", **DIRECTOR))
        payload = json.loads(self.prompt(prompt_format="json"))
        report = json.loads(artifacts["capability_report.json"]["content"])
        withheld = {d["path"] for d in report["dispositions"] if d["status"] == "withheld"}
        self.assertTrue(withheld)
        shared = {k: v for k, v in payload.items() if k not in withheld}   # the prose section's selection, in every section
        self.assertEqual(yaml.safe_load(sections["yaml"]), shared)
        self.assertEqual(carriers.read_xml(sections["xml"]), shared)
        self.assertIn(f'score_id="{payload["score_id"]}"', text.splitlines()[0])
        self.assertEqual(report["timing_projection"]["carrier"], "hybrid")

    def test_requesting_the_same_carrier_twice_gives_the_same_bytes(self):
        for settings in (dict(prompt_format="yaml"), dict(prompt_format="xml"),
                         dict(prompt_format="hybrid", hybrid_sections=["json", "prose"], **DIRECTOR)):
            self.assertEqual(self.prompt(**settings), self.prompt(**settings))

    def test_an_accepted_change_reaches_every_section(self):
        card = jail_card()
        card["scene_action"]["entities"]["dex"]["description"] = "a lean man in his 20s with a shaved head, in a grey uniform"
        card["prompt_format"], card["hybrid_sections"] = "hybrid", ["prose", "yaml", "json", "xml"]
        prompt = dr.Runner(root=self.root).run(card, confirm={"all"})["prompt"]
        sections = carriers.read_hybrid(prompt)
        self.assertIn("grey uniform", sections["prose"])
        for structured in (yaml.safe_load(sections["yaml"]), json.loads(sections["json"]), carriers.read_xml(sections["xml"])):
            dex = next(e for e in structured["entities"] if e["id"] == "dex")
            self.assertEqual(dex["description"], card["scene_action"]["entities"]["dex"]["description"])

    def test_unsupported_requests_fail_and_never_fall_back_to_prose(self):
        cases = [
            (dict(prompt_format="hybrid"), "a hybrid prompt needs hybrid_sections"),
            (dict(prompt_format="yaml", hybrid_sections=["prose", "yaml"]), "hybrid_sections needs prompt_format hybrid"),
            (dict(prompt_format="hybrid", hybrid_sections=["prose", "prose"]), "invalid_request"),
            (dict(prompt_format="hybrid", hybrid_sections=["prose", "toml"]), "invalid_request"),
            (dict(prompt_format="yaml", **DIRECTOR), "director_v1 requires the prose carrier"),
            (dict(prompt_format="hybrid", hybrid_sections=["yaml", "xml"], **DIRECTOR), "director_v1 requires the prose carrier"),
        ]
        for settings, message in cases:
            with self.subTest(settings=settings), self.assertRaisesRegex(dr.RunFailed, message):
                self.build(**settings)

    def test_the_director_ceiling_measures_the_prose_section_only(self):
        prose = self.prompt(prompt_format="prose", **DIRECTOR)
        hybrid = self.build(prompt_format="hybrid", hybrid_sections=["prose", "json"], **DIRECTOR)
        policy = json.loads(hybrid["capability_report.json"]["content"])["output_policy"]
        self.assertEqual((policy["chars"], policy["limit_chars"], policy["measures"]), (len(prose), 14000, "prose_section"))
        limited = copy.deepcopy(BASE)
        with self.assertRaisesRegex(dr.RunFailed, "PROMPT_OVER_LIMIT"):
            self.runner.call("direct.finish", dict(session_id=self.sid, build_settings=dict(
                limited, prompt_format="hybrid", hybrid_sections=["prose", "json"], prompt_char_limit=len(prose) + 10, **DIRECTOR)))


if __name__ == "__main__":
    unittest.main()
