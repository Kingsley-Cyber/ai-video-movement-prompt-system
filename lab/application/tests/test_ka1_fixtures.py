"""WP-7 — cross-domain fixtures + real-runtime smoke (env-gated)."""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from lab.application.cpcs_deliberation import FAKE_SNAPSHOT
from lab.application.ka1_fixtures import (
    FIXTURES,
    bridge_result,
    write_fixture_artifact,
)
from lab.application.reasoning_treatment import FakeBackend, FrozenRuntimeBackend

RUNTIME = os.environ.get("CPCS_FROZEN_RUNTIME_PATH",
                         "/Users/king/Downloads/Additional/Runtime")
HAS_RUNTIME = Path(RUNTIME).is_dir()


class Ka1FixturesHermetic(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.results = {
            name: bridge_result(spec["intent"], FakeBackend(), FAKE_SNAPSHOT)
            for name, spec in FIXTURES.items()
        }

    def test_artifact_computed_and_valid(self):
        artifact = write_fixture_artifact()
        self.assertEqual(artifact["artifact"],
                         "CPCS_KNOWLEDGE_APPLICATION_FIXTURES")
        self.assertEqual(sorted(artifact["fixtures"]),
                         ["COMBAT", "COOKING", "ECOMMERCE"])
        path = Path(__file__).resolve().parents[1] / \
            "CPCS_KNOWLEDGE_APPLICATION_FIXTURES_v0.1.json"
        self.assertTrue(path.is_file())
        json.loads(path.read_text())

    def test_every_fixture_produces_packs_and_decisions(self):
        for name, result in self.results.items():
            self.assertGreaterEqual(result["principle_pack_count"], 1,
                                    f"{name}: no principle packs")
            self.assertTrue(result["decision_counts"], f"{name}: no decisions")

    def test_decision_mixes_differ_across_domains(self):
        mixes = [tuple(sorted((k, v) for k, v in result["decision_counts"].items()))
                 for result in self.results.values()]
        self.assertEqual(len(set(mixes)), len(mixes),
                         "decision mixes must be intent-conditioned, "
                         "not one fixed template")

    def _interactions(self, name):
        return [obj for obj in self.results[name]["structured_objects"]
                if obj.get("target") == "interactions[]"]

    def test_combat_contract(self):
        interactions = self._interactions("COMBAT")
        self.assertTrue(interactions)
        value = interactions[0]["value"]
        self.assertTrue(value.get("state_before", {}).get("attacker_support"),
                        "support chain missing")
        self.assertEqual(value["projection"]["rotating_actor"], "defender_only",
                         "rotation roles missing")
        self.assertTrue(any(p.get("action") == "projection"
                            for p in value["phases"]),
                        "projection phase missing")
        self.assertIn("mirrored_rotation", value["recovery"]["forbidden"],
                      "recovery state missing")

    def test_ecommerce_contract(self):
        result = self.results["ECOMMERCE"]
        targets = {obj["target"] for obj in result["structured_objects"]}
        self.assertIn("continuity.cpcs_invariants[]", targets,
                      "object identity invariant missing")
        self.assertIn("interactions[]", targets,
                      "hand-object interaction missing")
        self.assertIn("entities[]", targets, "material visibility missing")
        self.assertIn("camera.cpcs_subject_visibility[]", targets,
                      "camera realism missing")

    def test_cooking_contract(self):
        result = self.results["COOKING"]
        self.assertIn("hand_safety", result["risk_tokens"],
                      "hand safety risk missing from bridge packs")
        self.assertIn("cut_deformation", result["mechanism_tokens"],
                      "cut/deformation mechanism missing from bridge packs")
        interactions = [obj for obj in result["structured_objects"]
                        if obj.get("target") == "interactions[]"]
        self.assertTrue(interactions, "knife-object interaction missing")
        value = interactions[0]["value"]
        self.assertTrue(any(p.get("action") == "cut_through"
                            for p in value["phases"]),
                        "cutting motion missing")
        world = value.get("world_response") or {}
        self.assertEqual(world.get("surface", {}).get("deformation"),
                         "local_displacement",
                        "food deformation response missing")
        self.assertIsNotNone(result["set_hash"])


@unittest.skipUnless(HAS_RUNTIME, "CPCS_FROZEN_RUNTIME_PATH unavailable")
class Ka1FixturesRealRuntime(unittest.TestCase):

    def test_bridge_runs_end_to_end_and_is_deterministic(self):
        from lab.application.cpcs_deliberation import frozen_knowledge_snapshot

        previous = os.environ.get("CPCS_FROZEN_RUNTIME_PATH")
        os.environ["CPCS_FROZEN_RUNTIME_PATH"] = RUNTIME
        try:
            backend = FrozenRuntimeBackend()
            snapshot = frozen_knowledge_snapshot()
            for name, spec in sorted(FIXTURES.items()):
                first = bridge_result(spec["intent"], backend, snapshot)
                second = bridge_result(spec["intent"], backend, snapshot)
                self.assertGreaterEqual(first["principle_pack_count"], 1,
                                        f"{name}: real-runtime bridge empty")
                self.assertEqual(first["set_hash"], second["set_hash"],
                                 f"{name}: real-runtime bridge not deterministic")
        finally:
            if previous is None:
                os.environ.pop("CPCS_FROZEN_RUNTIME_PATH", None)
            else:
                os.environ["CPCS_FROZEN_RUNTIME_PATH"] = previous


if __name__ == "__main__":
    unittest.main()
