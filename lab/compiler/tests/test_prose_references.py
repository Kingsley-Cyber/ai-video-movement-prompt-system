"""Every scene reference printed in the default prose carrier resolves to a printed declaration."""
from __future__ import annotations

import copy
import json
import re
import unittest

from lab.compiler.build import compile_build, make_build_request
from lab.compiler.decisions import scene_from_decisions
from lab.compiler.tests.test_build import ready_score
from lab.second_brain.tests.test_directing_session import fixture

REFERENCE_FIELDS = ("caused by", "beat", "end beat", "action")
RAW_ID = re.compile(r"\b(?:act|beat|int|shot)_\d+\b")


def jail_score(mutate=None):
    decisions = copy.deepcopy(fixture()["proposal"]["decisions"])
    if mutate:
        mutate(decisions)
    scene = scene_from_decisions(decisions)
    overlay = dict(overlay_id="overlay_jail_references", scope="scene_override", priority=0,
                   values=scene, locks=[], source_refs=["authored://jail-reference-test"])
    return ready_score("A fight in a county jail", overlays=[overlay])


def build(score, prompt_format):
    # The jail scene is 15 seconds, a duration only the Seedance manual route accepts.
    request = make_build_request(score, project_id="prose-references", model="seedance-2.0",
                                 prompt_format=prompt_format, duration_seconds=15)
    return compile_build(request)["prompt.txt"].decode("utf-8")


def prose(score):
    return build(score, "prose")


def declared_labels(text):
    return {line.split(":", 1)[0] for line in text.splitlines()
            if re.match(r"^(Scene|Character|Beat|Action|Contact|Shot) [^:]+:", line)}


def printed_references(text):
    found = []
    for line in text.splitlines():
        for field in REFERENCE_FIELDS:
            for match in re.finditer(r"(?:^|[:;] )" + field + r": ([^;.]+?)(?=[;.]|$)", line):
                found.append((field, match.group(1).strip()))
    return found


class ProseReferenceTests(unittest.TestCase):
    def assert_resolved(self, text):
        labels = declared_labels(text)
        references = printed_references(text)
        self.assertTrue(references, "the fixture must print cause, beat and action references")
        for field, value in references:
            self.assertIn(value, labels, f"{field} reference {value!r} has no printed declaration")
        self.assertEqual(RAW_ID.findall(text), [], "raw scene IDs must not reach the prose carrier")

    def test_jail_references_resolve_to_printed_declarations(self):
        text = prose(jail_score())
        self.assert_resolved(text)
        self.assertIn("caused by: Action 2", text)
        self.assertIn("action: Action 2", text)
        self.assertIn("beat: Beat 1", text)
        self.assertIn("Contact 1:", text)

    def test_json_carrier_keeps_canonical_ids(self):
        value = json.loads(build(jail_score(), "json"))
        self.assertIn("act_2", json.dumps(value))
        self.assertIn("int_1", json.dumps(value))

    def test_colliding_order_labels_stay_unique_and_resolvable(self):
        def collide(decisions):
            for decision in decisions:
                if decision["target"]["item_id"] == "act_5":
                    decision["values"]["order"] = 6
        text = prose(jail_score(collide))
        self.assertIn("Action 6 (act_5):", text)
        self.assertIn("Action 6 (act_6):", text)
        self.assertIn("action: Action 6 (act_5)", text)
        labels = declared_labels(text)
        for field, value in printed_references(text):
            self.assertIn(value, labels)


if __name__ == "__main__":
    unittest.main()
