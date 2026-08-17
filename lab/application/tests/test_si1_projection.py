"""SI-1 — deterministic real-runtime structured interaction projection."""
from __future__ import annotations

import json
import unittest

from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
from lab.application.cpcs_knowledge_placement import decompose_atomic_units
from lab.application.cpcs_structured_interaction_projection import (
    enrich_interaction_payloads,
)
from lab.application.reasoning_treatment import (
    FakeBackend,
    TreatmentAdapter,
    build_treatment_packet,
)
from lab.compiler.profiles import REPO_ROOT


def _packet_with_obligations(condition_type=None, time_scope=None,
                             target_paths=("contact",),
                             failure_families=("FF-CONTACT",)):
    return build_treatment_packet(
        treatment_id="t_si1", source_intent_hash="si1",
        query_mode="INITIAL_GENERATION",
        activated_requirements=["REQ-CONTACT-1"],
        mandatory_requirements=["REQ-CONTACT-1"],
        conditional_requirements=[],
        required_pathways={"REQ-CONTACT-1": "covered"},
        objectives_at_risk=[],
        predicted_failure_families=["FF-CONTACT"],
        retrieved_evidence=[{
            "atomic_record_id": "ev_si1_contact",
            "supported_requirement_ids": ["REQ-CONTACT-1"],
            "failure_family_ids": ["FF-CONTACT"],
            "objective_ids": [],
            "universal_type": "Constraint",
            "epistemic_status": "known",
            "document_id": "doc_contact",
        }],
        proposed_obligations=[],
        proposed_controls=[{
            "control_id": "ctl_si1_contact",
            "control_type": ["CT-CONTACT-CONTRACT"],
            "target": "object", "scope": "scene", "hardness": "SOFT",
            "source": "EVIDENCE_DERIVED",
            "source_requirement_ids": ["REQ-CONTACT-1"],
            "supporting_evidence_ids": ["ev_si1_contact"],
            "protected_objectives": [],
            "prevented_failure_families": ["FF-CONTACT"],
            "control_semantics": {"statement": "contact contract",
                                  "universal_type": "Constraint"},
            "action": "add",
        }],
        verification_obligations=[{
            "obligation_id": "exp_si1_contact",
            "requirement_id": "REQ-CONTACT-1",
            "method": "contact persists through the pivot",
            "observability": "direct",
            "target_paths": list(target_paths),
            "failure_family_ids": list(failure_families),
            "criticality": "critical",
            "condition_type": condition_type,
            "time_scope": time_scope,
        }],
        unknowns=[],
        uncovered_mandatory_requirements=[],
        architecture_freeze_identity="x",
        retrieval_runtime_freeze_identity="y",
    )


class Si1Projection(unittest.TestCase):

    def _interaction(self, packet):
        translation = TreatmentAdapter(REPO_ROOT).translate(
            packet, snapshot=FAKE_SNAPSHOT,
            activation={"packet_id": "kap_si1", "activated_domains": [],
                        "activated_triggers": [], "candidate_objectives": []})
        enriched = enrich_interaction_payloads(
            translation.structured_objects, packet)
        interactions = [o for o in enriched
                        if o.get("target") == "interactions[]"]
        self.assertTrue(interactions)
        return interactions[0]["value"]

    def test_persistence_condition_maps_to_contact_persistence(self):
        value = self._interaction(_packet_with_obligations(
            condition_type="PERSISTENCE", time_scope="throughout the pivot"))
        self.assertTrue(value["contact"]["persistence"])
        self.assertIn("exp_si1_contact", value["verification_refs"])
        self.assertIn("exp_si1_contact", value["continuity_requirements"])
        self.assertIn("PERSISTENCE",
                      value["lineage"]["si1_condition_types"])

    def test_non_persistence_condition_keeps_persistence_none(self):
        value = self._interaction(_packet_with_obligations(
            condition_type="TRANSITION"))
        self.assertIsNone(value["contact"]["persistence"])
        self.assertEqual(value["continuity_requirements"], [])

    def test_absent_fields_stay_none(self):
        value = self._interaction(_packet_with_obligations(
            condition_type="PERSISTENCE"))
        for field in ("state_before", "phases", "projection", "state_after",
                      "recovery", "world_response"):
            self.assertIsNone(value[field], f"{field} must stay None")
        self.assertIsNone(value["contact"]["state_transition"]["value"])

    def test_d4_no_condition_prose_in_payload(self):
        value = self._interaction(_packet_with_obligations(
            condition_type="PERSISTENCE",
            time_scope="the wrist contact must persist for the whole pivot"))
        self.assertNotIn("wrist", json.dumps(value))
        self.assertNotIn("persist for the whole", json.dumps(value))

    def test_phase_less_interaction_produces_interaction_unit(self):
        translation = TreatmentAdapter(REPO_ROOT).translate(
            _packet_with_obligations(condition_type="PERSISTENCE"),
            snapshot=FAKE_SNAPSHOT,
            activation={"packet_id": "k", "activated_domains": [],
                        "activated_triggers": [], "candidate_objectives": []})
        enriched = enrich_interaction_payloads(
            translation.structured_objects,
            _packet_with_obligations(condition_type="PERSISTENCE"))
        units = decompose_atomic_units(enriched)
        interactions = [u for u in units if u.unit_kind == "INTERACTION"]
        self.assertEqual(len(interactions), 1)
        self.assertTrue(interactions[0].state_transitions.get(
            "contact_persistence"))
        self.assertTrue((interactions[0].lineage or {}).get("evidence_ids"))
        events = [u for u in units if u.unit_kind == "EVENT"]
        self.assertFalse(events, "interaction must not collapse to EVENT")

    def test_hip_toss_phase_units_unchanged(self):
        backend = FakeBackend()
        engine = DeliberationEngine(FAKE_SNAPSHOT, backend)
        activation, packet = engine.activate(
            "A fighter performs a hip toss.",
            {"intent": {"primary_domain": "action"}}, observations=[])
        translation = TreatmentAdapter(REPO_ROOT).translate(
            packet, snapshot=FAKE_SNAPSHOT, activation=activation)
        units = decompose_atomic_units(translation.structured_objects)
        phases = [u for u in units if u.unit_kind == "INTERACTION_PHASE"]
        self.assertEqual(len(phases), 4)

    def test_enrichment_is_deterministic(self):
        packet = _packet_with_obligations(condition_type="PERSISTENCE")
        a = enrich_interaction_payloads(
            TreatmentAdapter(REPO_ROOT).translate(
                packet, snapshot=FAKE_SNAPSHOT,
                activation={"packet_id": "k"}).structured_objects, packet)
        b = enrich_interaction_payloads(
            TreatmentAdapter(REPO_ROOT).translate(
                packet, snapshot=FAKE_SNAPSHOT,
                activation={"packet_id": "k"}).structured_objects, packet)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
