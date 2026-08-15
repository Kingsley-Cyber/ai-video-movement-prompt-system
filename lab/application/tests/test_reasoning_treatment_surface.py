"""Structural acceptance tests for the CPCS reasoning-layer treatment.

Hermetic: FakeBackend only. The real FrozenRuntimeBackend is exercised by
the separate integration run (CPCS_FROZEN_RUNTIME_PATH set) and fails
closed here when the env var is absent.
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest import mock

from lab.application import reasoning_treatment as rt
from lab.application.reasoning_treatment import (
    BackendUnavailableError,
    DiscrepancyBuilder,
    FakeBackend,
    FrozenRuntimeBackend,
    RepairPlanner,
    TreatmentAdapter,
    build_treatment_packet,
    handler_reasoning_experiment_prepare,
    handler_reasoning_experimental_plan,
    handler_repair_gap_prepare,
    handler_repair_plan,
)
from lab.compiler.profiles import REPO_ROOT
from lab.compiler.score import make_score_request, resolve_score


class _FakeFrozen(FrozenRuntimeBackend):
    """FrozenRuntimeBackend with the plan() surface delegated to FakeBackend."""

    def __init__(self):
        super().__init__(runtime_path=None)
        self._fake = FakeBackend()

    def plan(self, intent_text, normalized_intent, *, query_mode="INITIAL_GENERATION",
             discrepancy=None):
        return self._fake.plan(intent_text, normalized_intent,
                               query_mode=query_mode, discrepancy=discrepancy)


def _patch_backend(func):
    @mock.patch.object(rt, "FrozenRuntimeBackend", _FakeFrozen)
    def _wrapped(self, *args, **kwargs):
        return func(self, *args, **kwargs)
    return _wrapped


def _intent_context(text: str):
    from lab.second_brain.src.intent import build_intent_context
    return build_intent_context(text, root=REPO_ROOT)


INTENT_CONTACT = (
    "She grabs his wrist while he is holding a glass, pulls him around, "
    "the glass spills, and the camera circles them."
)
INTENT_TRIVIAL = "A plain wide shot of an empty room for two seconds."


class ReasoningTreatmentSurfaceTests(unittest.TestCase):
    def setUp(self):
        # hermetic: never require the external runtime in these tests
        os.environ.pop("CPCS_FROZEN_RUNTIME_PATH", None)

    # 1 ------------------------------------------------------------------
    def test_reasoning_treatment_baseline_unchanged(self):
        ic = _intent_context(INTENT_CONTACT)
        score_a = resolve_score(make_score_request(ic), REPO_ROOT)
        score_b = resolve_score(make_score_request(ic), REPO_ROOT)
        self.assertEqual(score_a, score_b)
        from lab.application import service
        baseline_ops = {o.name for o in service.OPERATIONS.values()}
        for name in ("cpcs.intent.normalize", "cpcs.intent.context",
                     "cpcs.score.build", "cpcs.experiment.prepare",
                     "cpcs.experiment.seal", "cpcs.experiment.accept"):
            self.assertIn(name, baseline_ops)

    # 2 ------------------------------------------------------------------
    def test_reasoning_treatment_deterministic(self):
        intent = {"intent": {"primary_domain": "action"}}
        backend = FakeBackend()
        p1 = backend.plan(INTENT_CONTACT, intent)
        p2 = backend.plan(INTENT_CONTACT, intent)
        self.assertEqual(p1["packet_hash"], p2["packet_hash"])

    # 3/4 ----------------------------------------------------------------
    @_patch_backend
    def test_reasoning_ab_same_pretreatment_input(self):
        plan = handler_reasoning_experiment_prepare(
            {"flight_id": "flight_ab_test", "intent_text": INTENT_CONTACT,
             "project_id": "cpcs-ab-project"}, REPO_ROOT)
        self.assertEqual(plan["arm_a"]["normalized_intent_hash"],
                         plan["arm_b"]["normalized_intent_hash"])
        self.assertEqual(plan["confounder_check"],
                         {"same_intent": True, "same_provider_parameters": True})
        self.assertEqual(plan["differences_before_treatment"], [])
        shared_keys = ("duration_seconds", "aspect_ratio", "seed", "resolution")
        for key in shared_keys:
            self.assertEqual(
                plan["arm_a"]["build_request"]["settings"][key],
                plan["arm_b"]["build_request"]["settings"][key],
            )

    @_patch_backend
    def test_reasoning_ab_isolated_policy_factor(self):
        plan = handler_reasoning_experiment_prepare(
            {"flight_id": "flight_ab_iso", "intent_text": INTENT_CONTACT,
             "project_id": "cpcs-ab-project"}, REPO_ROOT)
        self.assertEqual(plan["experiment_kind"], "reasoning_layer_ab")
        self.assertEqual(plan["arm_a"]["reasoning_policy"], "CURRENT_BASELINE")
        self.assertEqual(plan["arm_b"]["reasoning_policy"], "CPCS_REASONING_V1")
        self.assertIsNone(plan["arm_a"]["treatment_packet_id"])
        self.assertIsNotNone(plan["arm_b"]["treatment_packet_id"])
        self.assertTrue(plan["shared_downstream_compiler"])
        self.assertTrue(plan["shared_evaluation_path"])

    @_patch_backend
    def test_reasoning_ab_downstream_controls_may_differ(self):
        plan = handler_reasoning_experiment_prepare(
            {"flight_id": "flight_ab_ctl", "intent_text": INTENT_CONTACT,
             "project_id": "cpcs-ab-project"}, REPO_ROOT)
        a = plan["arm_a"]["build_request"]["score"]
        b = plan["arm_b"]["build_request"]["score"]
        self.assertGreaterEqual(
            len(b.get("verification_requirements", [])),
            len(a.get("verification_requirements", [])),
        )

    # 6/7 ------------------------------------------------------------------
    def test_d4_flat_text_evidence_rejected(self):
        packet = build_treatment_packet(
            treatment_id="t_d4", source_intent_hash="h", query_mode="INITIAL_GENERATION",
            activated_requirements=[], mandatory_requirements=[],
            conditional_requirements=[], required_pathways={},
            objectives_at_risk=[], predicted_failure_families=[],
            retrieved_evidence=[{"atomic_record_id": "ev_prose_1",
                                 "provenance": {}}],
            proposed_obligations=[],
            proposed_controls=[{
                "control_id": "ctl_prose_1", "control_type": ["PROSE"],
                "target": "scene", "scope": "scene", "hardness": "SOFT",
                "source": "EVIDENCE_DERIVED", "source_requirement_ids": ["REQ-X"],
                "supporting_evidence_ids": ["ev_prose_1"],
                "protected_objectives": [], "prevented_failure_families": [],
                "control_semantics": {
                    "statement": "the wrist contact must persist for the whole pivot",
                    "universal_type": "Rule"},
            }],
            verification_obligations=[], unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="a", retrieval_runtime_freeze_identity="r",
        )
        translation = TreatmentAdapter(REPO_ROOT).translate(packet)
        for overlay in translation.overlays:
            for value in overlay["values"].values():
                self.assertNotIsInstance(value, str,
                                         "flat text must never become an overlay value")
                self.assertNotIn("wrist", json.dumps(value))
        prose_mappings = [m for m in translation.unsupported_mappings
                          if m["control_id"] == "ctl_prose_1"]
        self.assertTrue(prose_mappings)
        self.assertEqual(prose_mappings[0]["effect_on_score"], "none")

    def test_unsupported_mapping_preserves_lineage(self):
        packet = build_treatment_packet(
            treatment_id="t_u", source_intent_hash="h", query_mode="INITIAL_GENERATION",
            activated_requirements=[], mandatory_requirements=[],
            conditional_requirements=[], required_pathways={},
            objectives_at_risk=[], predicted_failure_families=[],
            retrieved_evidence=[{"atomic_record_id": "ev_u_1", "provenance": {}}],
            proposed_obligations=[],
            proposed_controls=[{
                "control_id": "ctl_u_1", "control_type": ["PROSE"],
                "target": "scene", "scope": "scene", "hardness": "SOFT",
                "source": "EVIDENCE_DERIVED", "source_requirement_ids": ["REQ-U"],
                "supporting_evidence_ids": ["ev_u_1"],
                "protected_objectives": [], "prevented_failure_families": [],
                "control_semantics": {"statement": "unmappable prose",
                                      "universal_type": "Rule"},
            }],
            verification_obligations=[], unknowns=[],
            uncovered_mandatory_requirements=[],
            architecture_freeze_identity="a", retrieval_runtime_freeze_identity="r",
        )
        translation = TreatmentAdapter(REPO_ROOT).translate(packet)
        mapping = translation.unsupported_mappings[0]
        self.assertEqual(mapping["requirement_ids"], ["REQ-U"])
        self.assertEqual(mapping["evidence_ids"], ["ev_u_1"])
        self.assertIn("reason", mapping)
        self.assertIn("proposed_semantic_meaning", mapping)
        self.assertEqual(mapping["effect_on_score"], "none")

    # 8 ------------------------------------------------------------------
    def test_uncovered_mandatory_requirement_fails_closed(self):
        backend = FakeBackend()
        intent = {"intent": {"primary_domain": "action"}}
        packet = backend.plan(INTENT_CONTACT, intent)
        packet["uncovered_mandatory_requirements"] = ["REQ-MISSING"]
        adapter = TreatmentAdapter(REPO_ROOT)
        translation = adapter.translate(packet)
        self.assertTrue(any(w["code"] == "treatment_uncovered_mandatory"
                            for w in translation.warnings))

    # 9 ------------------------------------------------------------------
    def test_treatment_b_has_no_effect_when_no_additional_obligation_is_discovered(self):
        backend = FakeBackend()
        intent = {"intent": {"primary_domain": "ugc"}}
        packet = backend.plan(INTENT_TRIVIAL, intent)
        translation = TreatmentAdapter(REPO_ROOT).translate(packet)
        self.assertEqual(translation.overlays, [])
        self.assertEqual(translation.verification_requirements, [])
        self.assertEqual(translation.provider_neutral_controls, [])
        self.assertEqual(translation.unsupported_mappings, [])
        self.assertIsNotNone(packet["packet_hash"])

    # 10 -----------------------------------------------------------------
    def test_frozen_runtime_missing_fails_closed(self):
        os.environ.pop("CPCS_FROZEN_RUNTIME_PATH", None)
        backend = FrozenRuntimeBackend()
        with self.assertRaises(BackendUnavailableError):
            backend.plan(INTENT_CONTACT, {"intent": {}})
        from lab.application import service
        response = service.invoke(
            {"schema": "cpcs.application_request/1.0",
             "operation": "cpcs.reasoning.experimental.plan",
             "arguments": {"intent_text": INTENT_CONTACT}},
            role="chat", root=REPO_ROOT)
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error"]["code"], "operation_failed")
        control_a = service.invoke(
            {"schema": "cpcs.application_request/1.0",
             "operation": "cpcs.status", "arguments": {}}, role="chat",
            root=REPO_ROOT)
        self.assertEqual(control_a["status"], "success")

    # 11 -----------------------------------------------------------------
    def test_fake_backend_is_hermetic(self):
        os.environ.pop("CPCS_FROZEN_RUNTIME_PATH", None)
        backend = FakeBackend()
        intent = {"intent": {"primary_domain": "action"}}
        p1 = backend.plan(INTENT_CONTACT, intent)
        p2 = backend.plan(INTENT_CONTACT, intent)
        self.assertEqual(p1, p2)
        self.assertEqual(p1["query_mode"], "INITIAL_GENERATION")

    # 12 -----------------------------------------------------------------
    def test_mcp_reasoning_tools_visible_by_role(self):
        from lab.application.mcp import handle_message
        roles = ("chat", "operator", "curator")
        for role in roles:
            reply = handle_message(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                role=role, root=REPO_ROOT)
            names = {t["name"] for t in reply["result"]["tools"]}
            for op in ("cpcs.reasoning.experimental.plan",
                       "cpcs.reasoning.experiment.inspect",
                       "cpcs.repair.gap.prepare",
                       "cpcs.repair.inspect"):
                self.assertIn(op, names, f"{op} must be visible to {role}")
            for op in ("cpcs.reasoning.experiment.prepare", "cpcs.repair.plan"):
                if role == "chat":
                    self.assertNotIn(op, names)
                else:
                    self.assertIn(op, names)
            self.assertNotIn("cpcs.research.query", names)

    # 13/14/15 -----------------------------------------------------------
    def test_discrepancy_expected_vs_observed(self):
        builder = DiscrepancyBuilder()
        packet = builder.build(
            expected_states=[{
                "requirement_id": "REQ-C", "expected_value": "held",
                "expected_condition": "contact persists", "time_scope": "pivot",
                "objectives": ["OBJ-CONTACT"], "failure_family_if_violated": ["FF-CONTACT"],
                "criticality": "critical",
            }],
            observations=[{"requirement_id": "REQ-C", "observation_id": "obs1",
                           "observed_value": "released"}],
        )
        d = packet["discrepancies"][0]
        self.assertEqual(d["status"], "CONTRADICTED")
        self.assertEqual(d["affected_requirement_ids"], ["REQ-C"])

    def test_user_complaint_not_video_truth(self):
        builder = DiscrepancyBuilder()
        packet = builder.build(
            expected_states=[{
                "requirement_id": "REQ-C", "expected_value": "held",
                "expected_condition": "contact persists", "time_scope": "pivot",
                "objectives": [], "failure_family_if_violated": [],
                "criticality": "important",
            }],
            observations=[{"requirement_id": "REQ-C", "observation_id": "obs1",
                           "observed_value": "held"}],
            user_complaint="the hand let go",
        )
        d = packet["discrepancies"][0]
        self.assertEqual(d["status"], "CORROBORATED")
        self.assertEqual(d["user_report"], "the hand let go")
        self.assertIn("not measured video truth",
                      d["evidence"]["user_report_epistemic_status"])

    def test_user_complaint_can_be_corroborated(self):
        builder = DiscrepancyBuilder()
        packet = builder.build(
            expected_states=[{
                "requirement_id": "REQ-C", "expected_value": "held",
                "expected_condition": "contact persists", "time_scope": "pivot",
                "objectives": [], "failure_family_if_violated": [],
                "criticality": "important",
            }],
            observations=[], user_complaint="the hand let go",
        )
        self.assertEqual(packet["discrepancies"][0]["status"], "CORROBORATED")

    # 16/17 ----------------------------------------------------------------
    @_patch_backend
    def test_repair_gap_uses_repair_query_mode(self):
        class RecordingBackend(FakeBackend):
            def __init__(self):
                super().__init__()
                self.last_mode = None
            def plan(self, intent_text, normalized_intent, *, query_mode="INITIAL_GENERATION",
                     discrepancy=None):
                self.last_mode = query_mode
                return super().plan(intent_text, normalized_intent,
                                    query_mode=query_mode, discrepancy=discrepancy)
        recorder = RecordingBackend()
        discrepancy = handler_repair_gap_prepare(
            {"expected_states": [{
                "requirement_id": "REQ-C", "expected_value": "held",
                "expected_condition": "contact persists", "time_scope": "pivot",
                "objectives": [], "failure_family_if_violated": ["FF-CONTACT"],
                "criticality": "critical"}],
             "observations": [{"requirement_id": "REQ-C", "observation_id": "obs1",
                               "observed_value": "released"}],
             "user_complaint": "the hand let go"}, REPO_ROOT)
        intent = {"intent": {"primary_domain": "action"}}
        plan = RepairPlanner().plan(discrepancy, recorder, INTENT_CONTACT, intent)
        self.assertEqual(recorder.last_mode, "REPAIR_GAP")

    @_patch_backend
    def test_repair_plan_traceability(self):
        discrepancy = handler_repair_gap_prepare(
            {"expected_states": [{
                "requirement_id": "REQ-C", "expected_value": "held",
                "expected_condition": "contact persists", "time_scope": "pivot",
                "objectives": [], "failure_family_if_violated": ["FF-CONTACT"],
                "criticality": "critical"}],
             "observations": [{"requirement_id": "REQ-C", "observation_id": "obs1",
                               "observed_value": "released"}]}, REPO_ROOT)
        intent = {"intent": {"primary_domain": "action"}}
        plan = RepairPlanner().plan(discrepancy, FakeBackend(), INTENT_CONTACT, intent)
        self.assertTrue(plan["supported_requirement_ids"])
        for key, value in (("generation", "v1"), ("repair", "v1"),
                            ("revised_generation", "v2")):
            self.assertEqual(plan["lineage"][key], value)

    # 18 ------------------------------------------------------------------
    @_patch_backend
    def test_repair_uses_existing_compiler(self):
        discrepancy = handler_repair_gap_prepare(
            {"expected_states": [{
                "requirement_id": "REQ-C", "expected_value": "held",
                "expected_condition": "contact persists", "time_scope": "pivot",
                "objectives": [], "failure_family_if_violated": ["FF-CONTACT"],
                "criticality": "critical"}],
             "observations": [{"requirement_id": "REQ-C", "observation_id": "obs1",
                               "observed_value": "released"}]}, REPO_ROOT)
        result = handler_repair_plan(
            {"intent_text": INTENT_CONTACT, "discrepancy_packet": discrepancy,
             "project_id": "cpcs-repair-project"}, REPO_ROOT)
        build = result["revised_build_request"]
        self.assertEqual(build["schema"], "cpcs.build_request/1.0")
        self.assertIn("score", build)
        self.assertEqual(result["lineage"]["revised_generation"], "v2")

    # 19 ------------------------------------------------------------------
    def test_retry_vs_repair_identity(self):
        retry = "generation_v1_attempt_2"
        repair = "generation_v2_after_repair_v1"
        self.assertNotEqual(retry, repair)
        plan = RepairPlanner().plan(
            {"schema": "cpcs.discrepancy_packet/1.0", "discrepancies": []},
            FakeBackend(), INTENT_CONTACT, {"intent": {}})
        for key, value in (("generation", "v1"), ("repair", "v1"),
                            ("revised_generation", "v2")):
            self.assertEqual(plan["lineage"][key], value)

    # 20 ------------------------------------------------------------------
    @_patch_backend
    def test_full_fake_ab_repair_loop(self):
        plan1 = handler_reasoning_experiment_prepare(
            {"flight_id": "flight_loop", "intent_text": INTENT_CONTACT,
             "project_id": "cpcs-ab-project"}, REPO_ROOT)
        discrepancy = handler_repair_gap_prepare(
            {"expected_states": [{
                "requirement_id": "REQ-C", "expected_value": "held",
                "expected_condition": "contact persists", "time_scope": "pivot",
                "objectives": [], "failure_family_if_violated": ["FF-CONTACT"],
                "criticality": "critical"}],
             "observations": [{"requirement_id": "REQ-C", "observation_id": "obs1",
                               "observed_value": "released"}]}, REPO_ROOT)
        repair1 = handler_repair_plan(
            {"intent_text": INTENT_CONTACT, "discrepancy_packet": discrepancy,
             "project_id": "cpcs-repair-project"}, REPO_ROOT)
        plan2 = handler_reasoning_experiment_prepare(
            {"flight_id": "flight_loop", "intent_text": INTENT_CONTACT,
             "project_id": "cpcs-ab-project"}, REPO_ROOT)
        repair2 = handler_repair_plan(
            {"intent_text": INTENT_CONTACT, "discrepancy_packet": discrepancy,
             "project_id": "cpcs-repair-project"}, REPO_ROOT)
        self.assertEqual(plan1["arm_b"]["treatment_packet_hash"],
                         plan2["arm_b"]["treatment_packet_hash"])
        self.assertEqual(repair1["repair_control_plan"]["repair_plan_id"],
                         repair2["repair_control_plan"]["repair_plan_id"])
        self.assertEqual(plan1["experiment_kind"], "reasoning_layer_ab")


if __name__ == "__main__":
    unittest.main()
