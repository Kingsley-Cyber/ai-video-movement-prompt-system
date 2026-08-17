"""TD-1 — temporal director tests (hermetic)."""
from __future__ import annotations

import unittest

from lab.application.cpcs_knowledge_placement import AtomicUnit
from lab.application.cpcs_temporal_director import (
    TEMPORAL_POLICY_SNAPSHOT,
    build_temporal_plan,
    validate_temporal_plan,
)


def _unit(uid, ordered_after=(), kind="INTERACTION",
          state_transitions=None, lineage=None):
    return AtomicUnit(
        unit_id=uid, unit_kind=kind, scope="PHASE", interaction_id="i1",
        actor_refs=[], object_refs=[],
        state_transitions=state_transitions or {},
        ordered_after=list(ordered_after),
        lineage=lineage or {"source": "test"})


CHAIN = [
    _unit("catch"),
    _unit("swing", ["catch"]),
    _unit("release", ["swing"]),
    _unit("flight", ["release"]),
    _unit("water_impact", ["flight"],
          state_transitions={"contact_persistence": True},
          lineage={"verification_refs": ["exp_impact"],
                   "source_control_id": "c_impact"}),
    _unit("water_response", ["water_impact"]),
    _unit("recovery", ["water_response"],
          lineage={"verification_refs": ["exp_recovery"]}),
    _unit("pressure", ["recovery"]),
]


class Td1TemporalDirector(unittest.TestCase):

    def test_causal_chain_ordered_sequentially(self):
        plan = build_temporal_plan(CHAIN, total_duration_s=6.0,
                                   duration_source="TEST_CONDITION")
        schedule = {s["unit_id"]: s for s in plan.atomic_unit_schedule}
        for s in plan.atomic_unit_schedule:
            for p in s["predecessor_ids"]:
                self.assertLessEqual(
                    schedule[p]["end_s"], s["start_s"] + 1e-9,
                    f"{p} must end before {s['unit_id']} starts")
        self.assertEqual(validate_temporal_plan(plan), [])

    def test_water_impact_receives_real_interval(self):
        plan = build_temporal_plan(CHAIN, total_duration_s=6.0,
                                   duration_source="TEST_CONDITION")
        impact = next(s for s in plan.atomic_unit_schedule
                      if s["unit_id"] == "water_impact")
        self.assertIsNotNone(impact["start_s"])
        self.assertIsNotNone(impact["end_s"])
        self.assertGreater(impact["duration_s"], 0)

    def test_environment_response_follows_impact(self):
        plan = build_temporal_plan(CHAIN, total_duration_s=6.0,
                                   duration_source="TEST_CONDITION")
        schedule = {s["unit_id"]: s for s in plan.atomic_unit_schedule}
        self.assertLessEqual(
            schedule["water_impact"]["end_s"],
            schedule["water_response"]["start_s"] + 1e-9)

    def test_no_total_duration_no_fabricated_seconds(self):
        plan = build_temporal_plan(CHAIN)
        self.assertEqual(plan.feasibility, "TEMPORALLY_UNDERSPECIFIED")
        for s in plan.atomic_unit_schedule:
            self.assertIsNone(s["start_s"])
            self.assertIsNone(s["duration_s"])
        self.assertTrue(any(
            g["kind"] == "TEMPORAL_TOTAL_UNDERSPECIFIED"
            for g in plan.unresolved_temporal_gaps))

    def test_different_durations_differ_materially(self):
        p3 = build_temporal_plan(CHAIN, total_duration_s=3.0,
                                 duration_source="TEST_CONDITION")
        p6 = build_temporal_plan(CHAIN, total_duration_s=6.0,
                                 duration_source="TEST_CONDITION")
        p10 = build_temporal_plan(CHAIN, total_duration_s=10.0,
                                  duration_source="TEST_CONDITION")
        def durations(plan):
            return [s["duration_s"] for s in plan.atomic_unit_schedule]
        self.assertNotEqual(durations(p3), durations(p6))
        self.assertNotEqual(durations(p6), durations(p10))
        # a critical unit gets strictly more absolute time at 10s
        def impact(plan):
            return next(s["duration_s"] for s in plan.atomic_unit_schedule
                        if s["unit_id"] == "water_impact")
        self.assertGreater(impact(p10), impact(p3))

    def test_feasibility_variation_3s_vs_10s(self):
        p3 = build_temporal_plan(CHAIN, total_duration_s=3.0,
                                 duration_source="TEST_CONDITION")
        p10 = build_temporal_plan(CHAIN, total_duration_s=10.0,
                                  duration_source="TEST_CONDITION")
        self.assertIn(p3.feasibility, ("FEASIBLE", "FEASIBLE_WITH_COMPRESSION",
                                       "REQUIRES_DECOMPOSITION"))
        self.assertIn(p10.feasibility, ("FEASIBLE", "FEASIBLE_WITH_COMPRESSION"))

    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            build_temporal_plan(CHAIN, total_duration_s=5.0,
                                duration_source="LLM_GUESS")

    def test_overlap_eligibility_never_between_causal_chain(self):
        plan = build_temporal_plan(CHAIN, total_duration_s=6.0,
                                   duration_source="TEST_CONDITION")
        for s in plan.atomic_unit_schedule:
            for p in s["predecessor_ids"]:
                self.assertIn(p, s["prohibited_overlap_ids"],
                              "causal predecessors must be prohibited overlap")

    def test_readability_critical_flags(self):
        plan = build_temporal_plan(CHAIN, total_duration_s=6.0,
                                   duration_source="TEST_CONDITION")
        impact = next(s for s in plan.atomic_unit_schedule
                      if s["unit_id"] == "water_impact")
        self.assertTrue(impact["readability_critical"])
        self.assertEqual(impact["priority_class"], "CRITICAL")
        plain = next(s for s in plan.atomic_unit_schedule
                     if s["unit_id"] == "flight")
        self.assertFalse(plain["readability_critical"])

    def test_determinism_plan_hash_stable(self):
        a = build_temporal_plan(CHAIN, total_duration_s=6.0,
                                duration_source="TEST_CONDITION")
        b = build_temporal_plan(CHAIN, total_duration_s=6.0,
                                duration_source="TEST_CONDITION")
        self.assertEqual(a.plan_hash, b.plan_hash)
        self.assertEqual(a.to_dict(), b.to_dict())

    def test_overlap_groups_exist_for_independent_units(self):
        units = [
            _unit("speech"),
            _unit("hand_manipulation"),
            _unit("gaze", ["speech"]),
        ]
        plan = build_temporal_plan(units, total_duration_s=4.0,
                                   duration_source="TEST_CONDITION")
        # speech and hand_manipulation are causally independent
        self.assertTrue(any("speech" in g and "hand_manipulation" in g
                            for g in plan.overlap_groups))

    def test_policy_snapshot_present(self):
        plan = build_temporal_plan(CHAIN, total_duration_s=6.0,
                                   duration_source="TEST_CONDITION")
        self.assertEqual(plan.lineage["policy"],
                         TEMPORAL_POLICY_SNAPSHOT["policy"])
        self.assertTrue(TEMPORAL_POLICY_SNAPSHOT["no_invented_total_duration"])
        self.assertTrue(TEMPORAL_POLICY_SNAPSHOT[
            "no_invented_readability_minimums"])


if __name__ == "__main__":
    unittest.main()
