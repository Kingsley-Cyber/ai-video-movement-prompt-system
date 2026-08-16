"""KA-2.2 — knowledge placement + atomic decomposition (hermetic)."""
from __future__ import annotations

import unittest

from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
from lab.application.cpcs_knowledge_application import apply_knowledge
from lab.application.cpcs_knowledge_constellation import assemble_constellation
from lab.application.cpcs_knowledge_placement import (
    LIFETIME_VOCABULARY,
    PLACEMENT_ROLES,
    SCOPE_VOCABULARY,
    assemble_directing_modules,
    build_placement,
    decompose_atomic_units,
)
from lab.application.cpcs_knowledge_recruitment import recruit_for_intent
from lab.application.reasoning_treatment import FakeBackend, TreatmentAdapter
from lab.compiler.profiles import REPO_ROOT


def _pipeline(intent_text, **backend_kwargs):
    backend = FakeBackend(**backend_kwargs)
    engine = DeliberationEngine(FAKE_SNAPSHOT, backend)
    activation, packet = engine.activate(
        intent_text, {"intent": {"primary_domain": "action"}}, observations=[])
    translation = TreatmentAdapter(REPO_ROOT).translate(
        packet, snapshot=FAKE_SNAPSHOT, activation=activation)
    app_set = translation.application_set
    applications = app_set.get("applications", []) if isinstance(
        app_set, dict) else getattr(app_set, "applications", [])
    evidence_by_id = {ev["atomic_record_id"]: ev
                      for ev in packet.get("retrieved_evidence", []) or []
                      if ev.get("atomic_record_id")}
    constellation = assemble_constellation(
        app_set, activation, evidence_by_id=evidence_by_id)
    pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in applications}
    recruitment = recruit_for_intent(
        constellation, activation, pack_lookup=pack_lookup)
    units = decompose_atomic_units(translation.structured_objects)
    placement = build_placement(recruitment, constellation, units,
                                pack_lookup=pack_lookup)
    modules = assemble_directing_modules(placement, units, recruitment,
                                         pack_lookup=pack_lookup,
                                         constellation=constellation)
    return activation, app_set, applications, constellation, recruitment, units, placement, modules


FIGHT = ("A fighter catches an opponent's leg, swings him in a wide arc, "
         "releases him onto the water, then immediately pressures him while "
         "he tries to recover.")
HIP_TOSS = "A fighter performs a hip toss."
SERUM = (
    "A woman records a casual handheld creator video trying a premium facial "
    "serum. She picks the bottle up from the bathroom counter, turns it so "
    "the label is visible, unscrews the dropper, dispenses two drops on the "
    "back of her other hand, rubs the serum between her fingers, applies it "
    "to her cheek, notices the texture, reacts positively, talks naturally "
    "to the viewer, then brings the bottle near the phone camera for the "
    "final product shot."
)


class Ka2Placement(unittest.TestCase):

    def test_fight_interaction_decomposes_into_phase_units(self):
        *_, units, _, _ = _pipeline(HIP_TOSS)
        phase_units = [u for u in units if u.unit_kind == "INTERACTION_PHASE"]
        self.assertTrue(phase_units, "no interaction phase units")
        actions = {u.unit_id.split(":phase_")[1].split(":", 1)[1]
                   for u in phase_units}
        self.assertIn("projection", actions)
        self.assertTrue(all(u.scope == "PHASE" for u in phase_units))
        # phase ordering preserved
        ids = [u.unit_id for u in phase_units]
        self.assertEqual(ids, sorted(ids))
        self.assertTrue(any(u.ordered_after for u in phase_units))

    def test_placement_binds_interaction_knowledge_locally(self):
        *_, placement, _ = _pipeline(HIP_TOSS)
        scoped = [p for p in placement
                  if p.target_scope in ("INTERACTION", "PHASE")]
        self.assertTrue(scoped, "no interaction-scoped placement")
        for p in scoped:
            self.assertTrue(p.target_unit_ids,
                            "scoped placement without unit binding")
            self.assertIn(p.placement_role, PLACEMENT_ROLES)
            self.assertIn(p.lifetime, LIFETIME_VOCABULARY)
        roles = {p.placement_role for p in placement}
        self.assertTrue({"INTERACTION_MECHANICS", "RECOVERY",
                         "GLOBAL_INVARIANT"} & roles, f"roles: {roles}")
        recovery = [p for p in placement if p.placement_role == "RECOVERY"]
        if recovery:
            self.assertEqual(recovery[0].lifetime, "RECOVERY_UNTIL_COMPLETE")

    def test_emission_policies_never_all_global_emit(self):
        *_, placement, modules = _pipeline(HIP_TOSS)
        policies = {p.emission_policy for p in placement}
        self.assertIn("EMIT_SCOPED_MODULE", policies)
        counts = modules["counts"]
        self.assertLess(counts["global_emit_count"],
                        len(placement), "everything went global (bloat risk)")

    def test_archive_regions_are_reasoning_only(self):
        *_, placement, _ = _pipeline(HIP_TOSS)
        for p in placement:
            if p.disposition == "ARCHIVE":
                self.assertEqual(p.emission_policy, "NO_EMIT_REASONING_ONLY")
                self.assertEqual(p.target_unit_ids, [])

    def test_serum_pipeline_runs_with_corpus_slice(self):
        result = _pipeline(SERUM, corpus_slice=True)
        _, _, applications, constellation, recruitment, _, placement, modules = result
        self.assertTrue(applications,
                        "corpus slice must exercise the pipeline")
        self.assertTrue(constellation.regions)
        self.assertEqual(len(recruitment["dispositions"]),
                         len(constellation.regions))
        self.assertEqual(len(placement), len(constellation.regions))
        self.assertIn("atomic_unit_count", modules["counts"])

    def test_product_only_pipeline_facs_not_required_to_emit(self):
        *_, placement, modules = _pipeline(
            "Macro product-only serum bottle rotating slowly on a pedestal. "
            "No person is visible.", corpus_slice=True)
        for p in placement:
            if p.disposition == "RECRUIT":
                self.assertNotIn("FACS", p.region_id)
        self.assertIsInstance(modules["counts"]["reasoning_only_count"], int)

    def test_no_prose_in_placement_outputs(self):
        import json
        *_, placement, modules = _pipeline(HIP_TOSS)
        blob = json.dumps([p.to_dict() for p in placement]) \
            + json.dumps(modules)
        for forbidden in ("remember realistic physics",
                          "make facial expressions realistic",
                          "handle product naturally"):
            self.assertNotIn(forbidden, blob)

    def test_determinism_placement_hashes_stable(self):
        *_, placement_a, _ = _pipeline(HIP_TOSS)
        *_, placement_b, _ = _pipeline(HIP_TOSS)
        self.assertEqual([p.to_dict() for p in placement_a],
                         [p.to_dict() for p in placement_b])

    def test_scope_and_lifetime_vocabularies_are_explicit(self):
        self.assertTrue(SCOPE_VOCABULARY)
        self.assertIn("CONTACT_INTERVAL", LIFETIME_VOCABULARY)
        self.assertIn("RECOVERY_UNTIL_COMPLETE", LIFETIME_VOCABULARY)


if __name__ == "__main__":
    unittest.main()
