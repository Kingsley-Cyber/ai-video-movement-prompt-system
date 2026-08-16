"""KA-2.3 step 1 — policy-neutral constellation merge instrumentation.

These tests verify that the instrumentation EXPLAINS every region merge
without changing merge policy, region identity, or any downstream hash.
"""
from __future__ import annotations

import hashlib
import json
import unittest

from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
from lab.application.cpcs_knowledge_application import apply_knowledge
from lab.application.cpcs_knowledge_constellation import (
    MERGE_POLICY_SNAPSHOT,
    STRONG_FACET_KEYS,
    WEAK_FACET_KEYS,
    assemble_constellation,
)
from lab.application.reasoning_treatment import FakeBackend


def _sha(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _constellation(intent_text, **backend_kwargs):
    backend = FakeBackend(**backend_kwargs)
    engine = DeliberationEngine(FAKE_SNAPSHOT, backend)
    activation, packet = engine.activate(
        intent_text, {"intent": {"primary_domain": "action"}}, observations=[])
    app_set = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
    evidence_by_id = {ev["atomic_record_id"]: ev
                      for ev in packet.get("retrieved_evidence", []) or []
                      if ev.get("atomic_record_id")}
    return assemble_constellation(app_set, activation,
                                  evidence_by_id=evidence_by_id)


class Ka2Instrumentation(unittest.TestCase):

    def test_every_region_records_seed_identity(self):
        const = _constellation("A fighter performs a hip toss.")
        self.assertTrue(const.regions)
        for region in const.regions:
            diag = region.get("diagnostics", {})
            seed = diag.get("seed", {})
            self.assertIn("principle_family", seed)
            self.assertIn("corpus_doc_ids", seed)
            self.assertIsInstance(diag.get("orphan"), bool)
            self.assertIsInstance(
                diag.get("strength_breakdown", {}).get("cross_seed_merges"),
                int)

    def test_cross_seed_merge_evidence_is_typed(self):
        const = _constellation("A fighter performs a hip toss.")
        seen = False
        for region in const.regions:
            for entry in region["diagnostics"].get("merge_evidence", []):
                seen = True
                self.assertEqual(entry["role"], "cross_seed_merge")
                self.assertIn("concept_jaccard", entry)
                self.assertIn("shared_failures", entry)
                self.assertIn("shared_concepts", entry)
                self.assertGreaterEqual(entry["concept_jaccard"], 0.5)
                self.assertGreaterEqual(len(entry["shared_concepts"]), 2)
                self.assertTrue(entry["shared_failures"])
        if not seen:
            self.skipTest("fixture produced no cross-seed merges")

    def test_strong_weak_facet_classification_recorded(self):
        const = _constellation("A fighter performs a hip toss.")
        policy = const.lineage["merge_policy_snapshot"]
        self.assertEqual(policy["strong_facet_keys"], list(STRONG_FACET_KEYS))
        self.assertEqual(policy["weak_facet_keys"], list(WEAK_FACET_KEYS))
        self.assertEqual(policy["policy"], "ka2.3-document-seeded-separation")
        for region in const.regions:
            self.assertEqual(
                region["diagnostics"]["merge_policy"]["policy"],
                "ka2.3-document-seeded-separation")

    def test_bridges_are_typed_strong_or_weak(self):
        const = _constellation(
            "A woman records a casual phone video trying a facial serum.",
            corpus_slice=True)
        bridges = const.diagnostics.get("bridges", [])
        self.assertTrue(bridges, "no inter-region bridges recorded")
        for bridge in bridges:
            self.assertIn(bridge["strength"], ("strong", "weak"))
            self.assertIn("kind", bridge)
            self.assertIn("from", bridge)
            self.assertIn("to", bridge)
        kinds = {b["kind"] for b in bridges}
        self.assertIn("shared_document", kinds | set())
        # weak bridge kinds must exist somewhere for corpus-slice evidence
        weak_kinds = {b["kind"] for b in bridges
                      if b["strength"] == "weak"}
        self.assertTrue(weak_kinds, "no weak inter-region bridges")

    def test_merge_policy_snapshot_present(self):
        const = _constellation("A fighter performs a hip toss.")
        self.assertEqual(const.lineage["merge_policy_snapshot"],
                         dict(MERGE_POLICY_SNAPSHOT))
        self.assertEqual(const.diagnostics["merge_policy_snapshot"],
                         dict(MERGE_POLICY_SNAPSHOT))
        for region in const.regions:
            self.assertEqual(region["diagnostics"]["merge_policy"],
                             dict(MERGE_POLICY_SNAPSHOT))

    def test_constellation_hash_excludes_instrumentation(self):
        # Policy-neutrality: the hash covers the same semantic core as
        # before instrumentation (regions minus diagnostics, edges minus
        # the additive strength key).
        const = _constellation("A fighter performs a hip toss.")
        hash_regions = [{k: v for k, v in r.items() if k != "diagnostics"}
                        for r in const.regions]
        hash_edges = [{"from": e["from"], "to": e["to"], "kind": e["kind"]}
                      for e in const.region_dependency_edges]
        body = {
            "regions": hash_regions,
            "edges": sorted(hash_edges,
                            key=lambda e: (e["from"], e["to"], e["kind"])),
            "activation_packet_id": const.lineage["activation_packet_id"],
        }
        self.assertEqual(const.constellation_hash, _sha(body))

    def test_orphan_regions_flagged(self):
        backend = FakeBackend()
        engine = DeliberationEngine(FAKE_SNAPSHOT, backend)
        activation, packet = engine.activate(
            "A fighter performs a hip toss.",
            {"intent": {"primary_domain": "action"}}, observations=[])
        app_set = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
        # evidence-less packs become orphans; verify the flag records it
        const = assemble_constellation(app_set, activation, evidence_by_id={})
        orphans = [r for r in const.regions
                   if r["region_id"] == "region_orphan"]
        if orphans:
            self.assertTrue(orphans[0]["diagnostics"]["orphan"])
        non_orphans = [r for r in const.regions
                       if r["region_id"] != "region_orphan"]
        for region in non_orphans:
            self.assertFalse(region["diagnostics"]["orphan"])

    def test_determinism_diagnostics_stable(self):
        a = _constellation("A fighter performs a hip toss.")
        b = _constellation("A fighter performs a hip toss.")
        self.assertEqual(a.to_dict(), b.to_dict())

    def test_diagnostics_never_affect_region_identity(self):
        const = _constellation("A fighter performs a hip toss.")
        for region in const.regions:
            hash_body = {
                "region_id": region["region_id"],
                "pack_ids": region["pack_ids"],
                "evidence_ids": region["evidence_ids"],
                "facets": {
                    "principle_families": region["principle_families"],
                    "trigger_ids": region["trigger_ids"],
                    "objective_ids": region["objective_ids"],
                    "requirement_ids": region["requirement_ids"],
                    "failure_family_ids": region["failure_family_ids"],
                    "canonical_concept_ids": region["canonical_concept_ids"],
                    "corpus_doc_ids": region["corpus_doc_ids"],
                },
                "decisions": sorted(region["representation_mix"]),
            }
            self.assertEqual(region["region_hash"], _sha(hash_body),
                             "diagnostics leaked into region_hash")

    def test_weak_only_overlap_bridges_never_merges(self):
        # KA-2.3 v3: two packs from DIFFERENT documents sharing ONLY weak
        # facets (triggers/objectives) stay in separate regions and are
        # connected by a weak bridge edge, never merged.
        from lab.application.reasoning_treatment import build_treatment_packet

        packet = build_treatment_packet(
            treatment_id="t_weak", source_intent_hash="weak",
            query_mode="INITIAL_GENERATION",
            activated_requirements=["REQ-X"],
            mandatory_requirements=["REQ-X"],
            conditional_requirements=[],
            required_pathways={"REQ-X": "covered"},
            objectives_at_risk=["OBJ-SHARED"],
            predicted_failure_families=[],
            retrieved_evidence=[
                {"atomic_record_id": "ev_a",
                 "supported_requirement_ids": ["REQ-A"],
                 "failure_family_ids": [],
                 "objective_ids": ["OBJ-SHARED"],
                 "trigger_ids": ["TRIG-SHARED"],
                 "document_id": "doc_a",
                 "universal_type": "Concept",
                 "epistemic_status": "known"},
                {"atomic_record_id": "ev_b",
                 "supported_requirement_ids": ["REQ-B"],
                 "failure_family_ids": [],
                 "objective_ids": ["OBJ-SHARED"],
                 "trigger_ids": ["TRIG-SHARED"],
                 "document_id": "doc_b",
                 "universal_type": "Mechanism",
                 "epistemic_status": "known"},
            ],
            proposed_obligations=[], proposed_controls=[],
            verification_obligations=[], unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="x",
            retrieval_runtime_freeze_identity="y",
        )
        from lab.application.cpcs_knowledge_application import apply_knowledge
        from lab.application.cpcs_deliberation import FAKE_SNAPSHOT

        app_set = apply_knowledge(
            packet, FAKE_SNAPSHOT,
            {"packet_id": "kap_weak", "activated_domains": [],
             "activated_triggers": [], "candidate_objectives": []})
        const = assemble_constellation(
            app_set, {"packet_id": "kap_weak", "packet_hash": "w"},
            evidence_by_id={ev["atomic_record_id"]: ev
                            for ev in packet["retrieved_evidence"]})
        self.assertEqual(len(const.regions), 2,
                         "weak-only cross-document overlap must not merge")
        bridges = const.diagnostics.get("bridges", [])
        self.assertTrue(bridges, "weak overlap must produce a bridge edge")
        self.assertTrue(all(b["strength"] == "weak" for b in bridges))
        weak_kinds = {b["kind"] for b in bridges}
        self.assertTrue({"shared_document", "shared_objective",
                         "shared_trigger"} & weak_kinds)

    def test_requirement_overlap_never_merges(self):
        # v3: shared requirements are bridge evidence (semantic
        # relatedness), never expertise identity. Two packs sharing ONLY a
        # requirement (different docs, no concepts, no failures) must stay
        # separate regions connected by a shared_requirement bridge.
        from lab.application.reasoning_treatment import build_treatment_packet

        packet = build_treatment_packet(
            treatment_id="t_req", source_intent_hash="req",
            query_mode="INITIAL_GENERATION",
            activated_requirements=["REQ-SHARED"],
            mandatory_requirements=["REQ-SHARED"],
            conditional_requirements=[],
            required_pathways={"REQ-SHARED": "covered"},
            objectives_at_risk=[],
            predicted_failure_families=[],
            retrieved_evidence=[
                {"atomic_record_id": "ev_a",
                 "supported_requirement_ids": ["REQ-SHARED"],
                 "failure_family_ids": [],
                 "objective_ids": [],
                 "trigger_ids": [],
                 "document_id": "doc_a",
                 "universal_type": "Concept",
                 "epistemic_status": "known"},
                {"atomic_record_id": "ev_b",
                 "supported_requirement_ids": ["REQ-SHARED"],
                 "failure_family_ids": [],
                 "objective_ids": [],
                 "trigger_ids": [],
                 "document_id": "doc_b",
                 "universal_type": "Mechanism",
                 "epistemic_status": "known"},
            ],
            proposed_obligations=[], proposed_controls=[],
            verification_obligations=[], unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="x",
            retrieval_runtime_freeze_identity="y",
        )
        from lab.application.cpcs_knowledge_application import apply_knowledge
        from lab.application.cpcs_deliberation import FAKE_SNAPSHOT

        app_set = apply_knowledge(
            packet, FAKE_SNAPSHOT,
            {"packet_id": "kap_req", "activated_domains": [],
             "activated_triggers": [], "candidate_objectives": []})
        const = assemble_constellation(
            app_set, {"packet_id": "kap_req", "packet_hash": "r"},
            evidence_by_id={ev["atomic_record_id"]: ev
                            for ev in packet["retrieved_evidence"]})
        self.assertEqual(len(const.regions), 2,
                         "requirement-only overlap must not merge regions")
        kinds = {b["kind"] for b in const.region_dependency_edges}
        self.assertIn("shared_requirement", kinds)

    def test_merge_policy_snapshot_records_separation_policy(self):
        const = _constellation("A fighter performs a hip toss.")
        policy = const.lineage["merge_policy_snapshot"]
        self.assertEqual(policy["policy"], "ka2.3-document-seeded-separation")
        self.assertTrue(policy["doc_identity_is_seed_not_authority"])
        self.assertTrue(policy["cross_seed_merge"][
            "requirement_overlap_never_merges"])
        self.assertIn("prior_policies", policy)
        self.assertEqual(len(policy["prior_policies"]), 2)


if __name__ == "__main__":
    unittest.main()
