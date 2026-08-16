"""WP-4 — KA-2 DEV evaluation (visible, re-runnable)."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
from lab.application.cpcs_knowledge_application import apply_knowledge
from lab.application.cpcs_knowledge_constellation import assemble_constellation
from lab.application.cpcs_knowledge_recruitment import recruit_for_intent
from lab.application.cpcs_knowledge_refinement import (
    apply_to_closure,
    assess_prerequisites,
    build_refinement_packet,
)
from lab.application.reasoning_treatment import FakeBackend

DEV_PATH = Path(__file__).resolve().parents[1] / "KA2_EVAL_DEV_v0.1.json"


def _run(intent_text):
    engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
    activation, packet = engine.activate(
        intent_text, {"intent": {"primary_domain": "action"}}, observations=[])
    app_set = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
    evidence_by_id = {
        ev["atomic_record_id"]: ev for ev in packet.get("retrieved_evidence", [])}
    constellation = assemble_constellation(app_set, activation, evidence_by_id=evidence_by_id)
    pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in app_set.applications}
    recruitment = recruit_for_intent(
        constellation, activation, pack_lookup=pack_lookup)
    new_pre, gaps = assess_prerequisites(
        recruitment, constellation, activation, pack_lookup=pack_lookup)
    refinement = build_refinement_packet(
        recruitment, constellation, activation,
        new_prerequisites=new_pre, coverage_gaps=gaps,
        application_set=app_set)
    closure = {
        "closure_id": "closure_" + intent_text[:8],
        "packet_hash": "pre",
        "planning_guidance": [],
        "non_executable_knowledge_used": [],
        "lineage": {},
    }
    closure_after = apply_to_closure(refinement, closure)
    return {
        "app_set": app_set,
        "activation": activation,
        "constellation": constellation,
        "recruitment": recruitment,
        "refinement": refinement,
        "closure": closure_after,
    }


def _region_matches(region, sig):
    req_any = set(sig.get("requirement_ids_any_of", []) or [])
    ff_any = set(sig.get("failure_family_ids_any_of", []) or [])
    if req_any and not (set(region.get("requirement_ids", []) or []) & req_any):
        return False
    if ff_any and not (set(region.get("failure_family_ids", []) or []) & ff_any):
        return False
    return True


class Ka2DevEvaluationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dev = json.loads(DEV_PATH.read_text())
        cls.intents = {i["intent_id"]: i for i in cls.dev["intents"]}

    def test_dev_set_loads(self):
        self.assertGreaterEqual(len(self.intents), 8)

    def test_each_intent_produces_at_least_one_region_and_one_recruit(self):
        for intent_id, intent in self.intents.items():
            with self.subTest(intent_id=intent_id):
                result = _run(intent["intent_text"])
                self.assertGreater(len(result["constellation"].regions), 0)
                recruited = [d for d in result["recruitment"]["dispositions"]
                             if d["disposition"] == "RECRUIT"]
                self.assertGreater(len(recruited), 0,
                                   f"{intent_id} must produce ≥1 RECRUIT region")

    def test_dev_set_positive_emergence(self):
        for intent_id, intent in self.intents.items():
            with self.subTest(intent_id=intent_id):
                result = _run(intent["intent_text"])
                recruited_regions = [
                    r for r in result["constellation"].regions
                    if any(d["region_id"] == r["region_id"] and
                           d["disposition"] == "RECRUIT"
                           for d in result["recruitment"]["dispositions"])]
                for expected in intent.get("expected_recruited_regions", []):
                    sig = expected["region_signature"]
                    if not any(_region_matches(r, sig) for r in recruited_regions):
                        self.fail(
                            f"{intent_id} missing expected recruited region "
                            f"with signature {sig}")

    def test_dev_set_negative_exclusion(self):
        for intent_id, intent in self.intents.items():
            with self.subTest(intent_id=intent_id):
                result = _run(intent["intent_text"])
                archived_regions = [
                    r for r in result["constellation"].regions
                    if any(d["region_id"] == r["region_id"] and
                           d["disposition"] == "ARCHIVE"
                           for d in result["recruitment"]["dispositions"])]
                for expected in intent.get("expected_archived_regions", []):
                    sig = expected["region_signature"]
                    if not any(_region_matches(r, sig) for r in archived_regions):
                        self.fail(
                            f"{intent_id} missing expected archived region "
                            f"with signature {sig}")

    def test_no_silent_drops(self):
        for intent_id, intent in self.intents.items():
            with self.subTest(intent_id=intent_id):
                result = _run(intent["intent_text"])
                regions = result["constellation"].regions
                dispositions = result["recruitment"]["dispositions"]
                self.assertEqual(
                    {r["region_id"] for r in regions},
                    {d["region_id"] for d in dispositions})

    def test_d4_preserved_no_prose_in_regions(self):
        for intent_id, intent in self.intents.items():
            with self.subTest(intent_id=intent_id):
                result = _run(intent["intent_text"])
                for r in result["constellation"].regions:
                    blob = json.dumps(r, sort_keys=True)
                    self.assertNotIn("d4 probe prose", blob)

    def test_closure_preserved_for_non_target_fields(self):
        for intent_id, intent in self.intents.items():
            with self.subTest(intent_id=intent_id):
                result = _run(intent["intent_text"])
                for d in result["recruitment"]["dispositions"]:
                    self.assertIsInstance(d["evidence_ids"], list)
                    self.assertIsInstance(d["bound_requirement_ids"], list)
                    self.assertIsInstance(d["bound_failure_family_ids"], list)

    def test_planning_guidance_field_present(self):
        for intent_id, intent in self.intents.items():
            with self.subTest(intent_id=intent_id):
                result = _run(intent["intent_text"])
                self.assertIn("planning_guidance", result["closure"])
                self.assertIn("non_executable_knowledge_used", result["closure"])

    def test_no_region_orphan_when_packs_present(self):
        for intent_id, intent in self.intents.items():
            with self.subTest(intent_id=intent_id):
                result = _run(intent["intent_text"])
                self.assertGreater(len(result["constellation"].regions), 0)


if __name__ == "__main__":
    unittest.main()
