"""KA-2.1 harness — principled hermetic corpus slice (not a holdout)."""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
from lab.application.cpcs_knowledge_application import apply_knowledge
from lab.application.reasoning_treatment import FakeBackend

OUT = Path(__file__).resolve().parents[1]
SLICE_PATH = OUT / "KA2_CORPUS_SLICE_v0.1.json"

UNSEEN_INTENTS = [
    "A drone flies over a snowy mountain range at dawn.",
    "Two dancers perform a synchronized hip-hop routine on a stage under "
    "colored lights.",
    "A glass of milk falls off the edge of a table.",
]


class Ka2Harness(unittest.TestCase):

    def test_slice_parses_and_carries_real_metadata(self):
        body = json.loads(SLICE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(body["artifact"], "CPCS_KA2_CORPUS_SLICE")
        records = body["records"]
        self.assertGreater(len(records), 100)
        for record in records:
            for field in ("atomic_record_id", "document_id", "universal_type",
                          "epistemic_state", "canonical_concept_ids",
                          "trigger_ids", "objective_ids",
                          "failure_family_ids"):
                self.assertIn(field, record)
            self.assertNotIn("description", record,
                             "no record prose in the harness slice")

    def test_slice_selection_policy_is_intent_independent(self):
        body = json.loads(SLICE_PATH.read_text(encoding="utf-8"))
        self.assertIn("intent-independent", body["selection_policy"])
        # content hash covers records; hash must be stable
        recomputed = hashlib.sha256(json.dumps(
            body["records"], sort_keys=True,
            separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(recomputed, body["content_hash"])

    def test_corpus_slice_fallback_serves_unseen_intents(self):
        backend = FakeBackend(corpus_slice=True)
        for intent in UNSEEN_INTENTS:
            packet = backend.plan(intent, {"intent": {"primary_domain": "action"}})
            evidence = packet.get("retrieved_evidence", [])
            self.assertTrue(evidence, f"no evidence for: {intent[:40]}")
            self.assertGreater(len(evidence), 100)
            self.assertTrue(all(ev.get("universal_type") for ev in evidence),
                            "evidence lacks universal_type")
            self.assertTrue(any(ev.get("canonical_concept_ids")
                                for ev in evidence),
                            "evidence lacks canonical_concept_ids")

    def test_unseen_intent_runs_full_pipeline(self):
        backend = FakeBackend(corpus_slice=True)
        engine = DeliberationEngine(FAKE_SNAPSHOT, backend)
        for intent in UNSEEN_INTENTS:
            activation, packet = engine.activate(
                intent, {"intent": {"primary_domain": "action"}},
                observations=[])
            app_set = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
            self.assertTrue(app_set.applications,
                            f"no applications for: {intent[:40]}")

    def test_default_backend_unchanged_without_slice(self):
        backend = FakeBackend()
        packet = backend.plan(UNSEEN_INTENTS[0],
                              {"intent": {"primary_domain": "action"}})
        self.assertEqual(packet.get("retrieved_evidence", []), [],
                         "default FakeBackend behavior must stay trivial")

    def test_slice_has_no_burned_holdout_dependency(self):
        body = json.loads(SLICE_PATH.read_text(encoding="utf-8"))
        for record in body["records"]:
            for value in record.values():
                if isinstance(value, str):
                    self.assertNotIn("holdout", value.lower())


if __name__ == "__main__":
    unittest.main()
