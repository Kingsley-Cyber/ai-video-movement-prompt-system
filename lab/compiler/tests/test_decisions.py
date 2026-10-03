from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from lab.compiler.decisions import (
    overlays_from_decisions, provider_fit, scene_from_decisions, validate_decisions,
)
from lab.compiler.score import make_score_request, resolve_score, validate_overlay
from lab.second_brain.src.directing_session import load_pass_registry, start_session
from lab.second_brain.tests.test_directing_session import fixture, fixture_root


class DecisionCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = fixture_root(Path(self.temporary.name))
        self.data = fixture()
        self.decisions = copy.deepcopy(self.data["proposal"]["decisions"])
        for index, decision in enumerate(self.decisions):
            decision.update(pass_id="scene_action", sequence=index)
        self.spec = load_pass_registry(self.root)["passes"][0]
        self.packet = {"constraints": {"requested_duration_s": 15}}

    def overlays(self) -> list:
        return overlays_from_decisions(self.decisions, "directing_session_" + "a" * 24, "sha256:" + "b" * 64)

    def refused(self, changed: list, code: str) -> None:
        errors = validate_decisions(changed, self.spec, self.packet, root=self.root)
        self.assertIn(code, [r["code"] for r in errors])

    def test_overlays_from_decisions_pass_validate_overlay(self) -> None:
        for overlay in self.overlays():
            validate_overlay(overlay, self.root)
        self.assertEqual(self.overlays()[0]["locks"], ["scenes"])
        self.assertNotIn("scenes", self.overlays()[1]["values"])

    def test_overlays_are_deterministic_for_one_ledger(self) -> None:
        self.assertEqual(self.overlays(), self.overlays())
        original = copy.deepcopy(self.decisions)
        self.overlays()
        self.assertEqual(original, self.decisions)

    def test_identity_key_other_than_id_is_refused(self) -> None:
        changed = copy.deepcopy(self.decisions)
        changed[9]["values"]["entity_id"] = "rome"
        self.refused(changed, "identity_key_not_allowed")

    def test_two_actions_by_one_actor_both_survive_resolution(self) -> None:
        started = start_session(self.data["ask"], root=self.root)
        path = self.root / "work/application/directing_sessions" / started["session_id"]
        context = json.loads((path / "intent_context.json").read_text())
        score = resolve_score(make_score_request(context, overlays=self.overlays(), root=self.root), self.root)
        self.assertEqual(len(score["actions"]), 6)
        self.assertEqual(sum(a["actor"] == "rome" for a in score["actions"]), 5)
        self.assertEqual(score["score_status"], "ready")
        self.assertIn("scenes", score["constraints"]["locked_paths"])

    def test_unknown_actor_reference_is_refused(self) -> None:
        changed = copy.deepcopy(self.decisions)
        changed[9]["values"]["actor"] = "unknown"
        self.refused(changed, "unknown_reference")

    def test_effect_before_cause_is_refused(self) -> None:
        changed = copy.deepcopy(self.decisions)
        changed[10]["values"]["caused_by"] = "act_5"
        self.refused(changed, "effect_before_cause")

    def test_beats_must_be_contiguous(self) -> None:
        changed = copy.deepcopy(self.decisions)
        changed[5]["values"]["order"] = 1
        self.refused(changed, "beats_not_contiguous")

    def test_beats_must_fit_the_requested_duration(self) -> None:
        changed = copy.deepcopy(self.decisions)
        changed[4]["values"]["min_s"] = 20
        self.refused(changed, "beats_exceed_duration")

    def test_anchor_must_sit_on_an_earlier_beat(self) -> None:
        changed = copy.deepcopy(self.decisions)
        changed[11]["relative_anchor"]["baseline"]["item"] = "act_5"
        self.refused(changed, "anchor_not_earlier")

    def test_bookkeeping_never_reaches_score_items(self) -> None:
        scene = scene_from_decisions(self.decisions)
        forbidden = {"decision_id", "inputs", "justification", "source_status", "evidence_uses", "pass_id", "sequence", "revision_of", "lock"}
        for items in scene.values():
            for item in items:
                self.assertFalse(forbidden.intersection(item))
        relative = next(a for a in scene["actions"] if a["id"] == "act_3")["relative"]
        self.assertEqual(relative["anchor"], "act_1")
        self.assertEqual(relative["direction"], "more")

    def test_provider_fit_reports_unsupported_duration(self) -> None:
        result = provider_fit(scene_from_decisions(self.decisions), self.root)
        self.assertEqual(result["requested_duration_s"], 15)
        self.assertEqual(result["supported_durations_s"], [4, 6, 8])
        self.assertEqual(result["status"], "unsupported")
        self.assertTrue(result["options"])

    def test_duplicate_value_key_is_refused(self) -> None:
        changed = copy.deepcopy(self.decisions)
        changed[1]["values"]["duration_s"] = 15
        self.refused(changed, "duplicate_value_key")

    def test_sublayer_must_match_its_target_path(self) -> None:
        changed = copy.deepcopy(self.decisions)
        changed[2]["target"]["path"] = "shots"
        self.refused(changed, "path_not_allowed")
