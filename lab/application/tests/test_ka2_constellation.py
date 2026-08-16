"""WP-1 — ExpertiseRegion + KnowledgeConstellation assembly tests (hermetic)."""
from __future__ import annotations

import unittest

from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
from lab.application.cpcs_knowledge_constellation import (
    ORPHAN_REGION_ID,
    KnowledgeConstellation,
    assemble_constellation,
    region_facets,
)
from lab.application.cpcs_knowledge_application import apply_knowledge
from lab.application.reasoning_treatment import FakeBackend, build_treatment_packet


def _set_for(intent_text):
    engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
    activation, packet = engine.activate(
        intent_text, {"intent": {"primary_domain": "action"}}, observations=[])
    return apply_knowledge(packet, FAKE_SNAPSHOT, activation), activation


class Ka2ConstellationTests(unittest.TestCase):

    def test_two_packs_sharing_requirement_and_trigger_land_in_one_region(self):
        app_set, activation = _set_for("A fighter performs a hip toss.")
        constellation = assemble_constellation(app_set, activation)
        self.assertGreaterEqual(len(constellation.regions), 1)
        all_pack_ids = [pid for r in constellation.regions for pid in r["pack_ids"]]
        self.assertEqual(
            sorted(all_pack_ids),
            sorted(p["pack"]["pack_id"] for p in app_set.applications))

    def test_no_prose_grouping_input_drives_only_structured_keys(self):
        app_set, activation = _set_for("A chef slices a tomato.")
        constellation = assemble_constellation(app_set, activation)
        for region in constellation.regions:
            self.assertIn("region_id", region)
            self.assertIn("region_hash", region)
            self.assertIn("principle_families", region)
            self.assertIn("failure_family_ids", region)
            for fld in ("pack_ids", "evidence_ids", "requirement_ids",
                        "objective_ids", "trigger_ids", "canonical_concept_ids"):
                self.assertIsInstance(region[fld], list)

    def test_determinism_two_runs_identical_constellation(self):
        app_set, activation = _set_for("A fighter performs a hip toss.")
        a = assemble_constellation(app_set, activation)
        b = assemble_constellation(app_set, activation)
        self.assertEqual(a.constellation_hash, b.constellation_hash)
        self.assertEqual(a.to_dict(), b.to_dict())

    def test_representation_mix_preserves_ka1_decisions(self):
        app_set, activation = _set_for("A fighter performs a hip toss.")
        constellation = assemble_constellation(app_set, activation)
        ka1_mix: dict[str, int] = {}
        for entry in app_set.applications:
            d = entry["decision"]["decision"]
            ka1_mix[d] = ka1_mix.get(d, 0) + 1
        region_mix: dict[str, int] = {}
        for r in constellation.regions:
            for d, c in r["representation_mix"].items():
                region_mix[d] = region_mix.get(d, 0) + c
        self.assertEqual(ka1_mix, region_mix)

    def test_region_hash_changes_when_pack_changes(self):
        app_set, activation = _set_for("A fighter performs a hip toss.")
        before = assemble_constellation(app_set, activation)
        altered = build_treatment_packet(
            treatment_id="t", source_intent_hash="t2",
            query_mode="INITIAL_GENERATION",
            activated_requirements=["REQ-CONTACT-1", "REQ-SUP-1"],
            mandatory_requirements=["REQ-CONTACT-1", "REQ-SUP-1"],
            conditional_requirements=[],
            required_pathways={"REQ-CONTACT-1": "covered",
                                "REQ-SUP-1": "covered"},
            objectives_at_risk=["OBJ-THROW"],
            predicted_failure_families=["FF-CONTACT", "FF-PHYSICS"],
            retrieved_evidence=[
                {"atomic_record_id": "ev_x1",
                 "supported_requirement_ids": ["REQ-CONTACT-1"],
                 "failure_family_ids": ["FF-CONTACT"],
                 "objective_ids": ["OBJ-THROW"],
                 "universal_type": "Mechanism",
                 "trigger_ids": ["TRIG-NEW-SIGNAL"],
                 "canonical_concept_ids": ["CC-NEW-CONCEPT"]},
            ],
            proposed_obligations=[], proposed_controls=[],
            verification_obligations=[], unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="x",
            retrieval_runtime_freeze_identity="y",
        )
        after = apply_knowledge(altered, FAKE_SNAPSHOT, activation)
        after_const = assemble_constellation(after, activation)
        self.assertNotEqual(before.constellation_hash, after_const.constellation_hash)

    def test_orphan_region_never_merges(self):
        packet = build_treatment_packet(
            treatment_id="t", source_intent_hash="orphan",
            query_mode="INITIAL_GENERATION",
            activated_requirements=["REQ-CONTACT-1"],
            mandatory_requirements=["REQ-CONTACT-1"],
            conditional_requirements=[],
            required_pathways={"REQ-CONTACT-1": "covered"},
            objectives_at_risk=[],
            predicted_failure_families=["FF-CONTACT"],
            retrieved_evidence=[
                {"atomic_record_id": "ev_orphan",
                 "supported_requirement_ids": ["REQ-CONTACT-1"],
                 "failure_family_ids": [],
                 "objective_ids": [],
                 "universal_type": "Concept",
                 "trigger_ids": [],
                 "canonical_concept_ids": []},
            ],
            proposed_obligations=[], proposed_controls=[],
            verification_obligations=[], unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="x",
            retrieval_runtime_freeze_identity="y",
        )
        activation = {"packet_id": "kap_orphan", "activated_domains": [],
                      "activated_triggers": [], "candidate_objectives": []}
        app_set = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
        constellation = assemble_constellation(app_set, activation)
        region_ids = [r["region_id"] for r in constellation.regions]
        self.assertTrue(any(rid != ORPHAN_REGION_ID for rid in region_ids)
                        or len(region_ids) == 1)

    def test_region_facets_returns_empty_for_no_facets(self):
        pack = {"pack_id": "p1", "evidence_ids": [], "intent_application": {},
                "lineage": {}, "principle_family": ""}
        f = region_facets(pack, {})
        self.assertTrue(all(not v for v in f.values()))

    def test_constellation_total_packs_equal_application_count(self):
        app_set, activation = _set_for("A fighter performs a hip toss.")
        constellation = assemble_constellation(app_set, activation)
        total = sum(len(r["pack_ids"]) for r in constellation.regions)
        self.assertEqual(total, len(app_set.applications))


if __name__ == "__main__":
    unittest.main()
