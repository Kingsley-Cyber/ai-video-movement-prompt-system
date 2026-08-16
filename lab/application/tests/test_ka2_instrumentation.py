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
    STRONG_MERGE_THRESHOLD,
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

    def test_every_multi_pack_region_has_merge_evidence(self):
        const = _constellation("A fighter performs a hip toss.")
        multi = [r for r in const.regions if len(r["pack_ids"]) > 1]
        self.assertTrue(multi)
        for region in multi:
            diag = region.get("diagnostics", {})
            evidence = diag.get("merge_evidence", [])
            self.assertEqual(
                len(evidence), len(region["pack_ids"]) - 1,
                f"region {region['region_id']}: merge log incomplete")
            self.assertIsNotNone(diag.get("seed_pack_id"))
            for entry in evidence:
                self.assertIn("overlap_by_facet", entry)
                self.assertIn("strong_overlap", entry)
                self.assertIn("weak_overlap", entry)
                self.assertGreaterEqual(
                    entry["strong_overlap"],
                    STRONG_MERGE_THRESHOLD,
                    "recorded strong overlap below merge threshold")

    def test_strong_weak_facet_classification_recorded(self):
        const = _constellation("A fighter performs a hip toss.")
        for region in const.regions:
            breakdown = region["diagnostics"]["strength_breakdown"]
            self.assertIn("strong_overlap_total", breakdown)
            self.assertIn("weak_overlap_total", breakdown)
            for entry in region["diagnostics"].get("merge_evidence", []):
                strong = sum(entry["overlap_by_facet"][k]
                             for k in STRONG_FACET_KEYS)
                weak = sum(entry["overlap_by_facet"][k] for k in WEAK_FACET_KEYS)
                self.assertEqual(entry["strong_overlap"], strong)
                self.assertEqual(entry["weak_overlap"], weak)

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
        # KA-2.3 separation policy: two packs sharing ONLY weak facets
        # (triggers/objectives/documents) stay in separate regions and are
        # connected by a weak bridge edge, not merged.
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
                 "document_id": "doc_shared",
                 "universal_type": "Concept",
                 "epistemic_status": "known"},
                {"atomic_record_id": "ev_b",
                 "supported_requirement_ids": ["REQ-B"],
                 "failure_family_ids": [],
                 "objective_ids": ["OBJ-SHARED"],
                 "trigger_ids": ["TRIG-SHARED"],
                 "document_id": "doc_shared",
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
                         "weak-only overlap must not merge regions")
        bridges = const.diagnostics.get("bridges", [])
        self.assertTrue(bridges, "weak overlap must produce a bridge edge")
        self.assertTrue(all(b["strength"] == "weak" for b in bridges))
        weak_kinds = {b["kind"] for b in bridges}
        self.assertTrue({"shared_document", "shared_objective",
                         "shared_trigger"} & weak_kinds)

    def test_merge_policy_snapshot_records_separation_policy(self):
        const = _constellation("A fighter performs a hip toss.")
        policy = const.lineage["merge_policy_snapshot"]
        self.assertEqual(policy["policy"], "ka2.3-strong-facet-separation")
        self.assertTrue(policy["weak_facets_bridge_only"])
        self.assertEqual(policy["strong_merge_threshold"],
                         STRONG_MERGE_THRESHOLD)
        self.assertIn("prior_policy", policy)


if __name__ == "__main__":
    unittest.main()
