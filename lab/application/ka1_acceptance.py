"""WP-9 — KA-1 acceptance computation (computed, never hand-authored).

Runs the KA-1 suites, the pre-KA regression group, the full application /
compiler / second-brain suites, artifact validation, and the decision-policy
checks. Writes CPCS_KA1_ACCEPTANCE_v0.1.json.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[1]
ARTIFACT = OUT / "CPCS_KA1_ACCEPTANCE_v0.1.json"

KA1_SUITES = [
    "lab.application.tests.test_ka1_schemas",
    "lab.application.tests.test_ka1_structured_interaction",
    "lab.application.tests.test_ka1_principle",
    "lab.application.tests.test_ka1_representation",
    "lab.application.tests.test_ka1_application_set",
    "lab.application.tests.test_ka1_adapter",
    "lab.application.tests.test_ka1_mcp",
    "lab.application.tests.test_ka1_fixtures",
]
PRE_KA_SUITES = [
    "lab.application.tests.test_reasoning_treatment_surface",
    "lab.application.tests.test_cpcs_typed_knowledge_coverage",
    "lab.application.tests.test_tc2_residual_closure",
    "lab.application.tests.test_deliberation_surface",
    "lab.application.tests.test_guided_product_surface",
]
FULL_SUITES = [
    ("application", ["-m", "unittest", "discover", "-s",
                     "lab/application/tests", "-q"]),
    ("compiler", ["-m", "unittest", "discover", "-s",
                  "lab/compiler/tests", "-p", "test_*.py", "-q"]),
    ("second_brain", ["-m", "unittest", "discover", "-s",
                      "lab/second_brain/tests", "-p", "test_*.py", "-q"]),
]
SCHEMA_FILES = [
    "CPCS_PRINCIPLE_PACK_SCHEMA_v0.1.json",
    "CPCS_REPRESENTATION_DECISION_SCHEMA_v0.1.json",
    "CPCS_STRUCTURED_INTERACTION_SCHEMA_v0.1.json",
    "CPCS_KNOWLEDGE_APPLICATION_CONTRACT_v0.1.json",
    "CPCS_KNOWLEDGE_APPLICATION_FIXTURES_v0.1.json",
]
RUNTIME = os.environ.get("CPCS_FROZEN_RUNTIME_PATH",
                         "/Users/king/Downloads/Additional/Runtime")


def _unittest(*targets: str, env: dict | None = None) -> dict:
    command = [sys.executable, "-m", "unittest", *targets, "-q"]
    result = subprocess.run(
        command, cwd=REPO, capture_output=True, text=True,
        timeout=3600, env=env or dict(os.environ))
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "tail": result.stdout.strip().splitlines()[-4:]
        + result.stderr.strip().splitlines()[-4:],
    }


def gate_representation_decisions() -> dict:
    sys.path.insert(0, str(REPO))
    from lab.application.cpcs_deliberation import FAKE_SNAPSHOT
    from lab.application.cpcs_knowledge_application import (
        DECISIONS_ALLOWED,
        NEVER_CONTROL_UNIVERSAL_TYPES,
        PrinciplePack,
        decide_representation,
    )

    failures = []
    for ut in sorted(NEVER_CONTROL_UNIVERSAL_TYPES):
        pack = PrinciplePack(
            pack_id="pack_" + "0" * 20, pack_hash="0" * 64,
            principle_family="conceptual_foundation", principle="template",
            mechanism="mechanism: none",
            failure_risk={"failure_family_ids": [], "risk_tokens": [],
                          "risk_statement": "risk: none"},
            evidence_ids=["ev_probe"],
            source_records=[{"atomic_record_id": "ev_probe",
                             "universal_type": ut,
                             "epistemic_status": "known"}],
            intent_application={"domain_tags": [], "creative_goal_tags": [],
                                "trigger_ids": [], "objective_ids": []},
            lineage={"requirement_ids": ["REQ-CONTACT-1"],
                     "treatment_packet_hash": "x",
                     "activation_packet_id": "y",
                     "control_types": [],
                     "verification_obligation_ids": [],
                     "contradiction_ids": []})
        decision = decide_representation(pack, {"packet_id": "probe"},
                                         FAKE_SNAPSHOT)
        if decision.decision == "CONTROL":
            failures.append(ut)
        if decision.decision not in DECISIONS_ALLOWED:
            failures.append(ut)
    return {"ok": not failures, "violations": failures}


def gate_hip_toss_state_transition() -> dict:
    sys.path.insert(0, str(REPO))
    from lab.application.reasoning_treatment import (
        TreatmentAdapter,
        build_treatment_packet,
    )
    from lab.compiler import cpcs_typed
    from lab.compiler.profiles import REPO_ROOT

    packet = build_treatment_packet(
        treatment_id="t", source_intent_hash="t",
        query_mode="INITIAL_GENERATION",
        activated_requirements=["REQ-BEAT-1"],
        mandatory_requirements=["REQ-BEAT-1"],
        conditional_requirements=[],
        required_pathways={"REQ-BEAT-1": "covered"},
        objectives_at_risk=[], predicted_failure_families=[],
        retrieved_evidence=[],
        proposed_obligations=[],
        proposed_controls=[{
            "control_id": "ctl_action_only",
            "control_type": ["CT-CONTACT-CONTRACT"],
            "target": "actor", "scope": "beat", "hardness": "SOFT",
            "source": "EVIDENCE_DERIVED",
            "source_requirement_ids": ["REQ-BEAT-1"],
            "supporting_evidence_ids": [],
            "protected_objectives": [],
            "prevented_failure_families": [],
            "control_semantics": {"statement": "a throw happens",
                                  "universal_type": "Concept"},
            "action": "add",
        }],
        verification_obligations=[], unknowns=[],
        uncovered_mandatory_requirements=[],
        architecture_freeze_identity="x", retrieval_runtime_freeze_identity="y")
    translation = TreatmentAdapter(REPO_ROOT).translate(packet)
    interactions = [o for o in translation.structured_objects
                    if o.get("target") == "interactions[]"]
    if not interactions:
        return {"ok": False, "detail": "no interaction object produced"}
    violations = cpcs_typed.validate_structured_interaction(
        interactions[0]["value"])
    return {"ok": bool(violations),
            "detail": "action-label-only output rejected by the state-"
                      "transition gate" if violations
            else "action-label-only output passed (INVALID)"}


def gate_d4() -> dict:
    sys.path.insert(0, str(REPO))
    from lab.application.cpcs_knowledge_application import build_principle_packs
    from lab.application.reasoning_treatment import build_treatment_packet
    import json as _json

    prose = "unique d4 probe prose that must never be admitted"
    packet = build_treatment_packet(
        treatment_id="t", source_intent_hash="t",
        query_mode="INITIAL_GENERATION",
        activated_requirements=["REQ-CONTACT-1"],
        mandatory_requirements=["REQ-CONTACT-1"],
        conditional_requirements=[],
        required_pathways={"REQ-CONTACT-1": "covered"},
        objectives_at_risk=[], predicted_failure_families=["FF-CONTACT"],
        retrieved_evidence=[{
            "atomic_record_id": "ev_d4_probe",
            "supported_requirement_ids": ["REQ-CONTACT-1"],
            "failure_family_ids": ["FF-CONTACT"], "objective_ids": [],
            "universal_type": "FailureMode", "epistemic_status": "known",
            "risk_tokens": ["probe_risk"], "description": prose,
        }],
        proposed_obligations=[], proposed_controls=[],
        verification_obligations=[], unknowns=[],
        uncovered_mandatory_requirements=[],
        architecture_freeze_identity="x", retrieval_runtime_freeze_identity="y")
    packs = build_principle_packs(packet, None, {"packet_id": "probe",
                                                 "activated_domains": [],
                                                 "activated_triggers": [],
                                                 "candidate_objectives": []})
    for pack in packs:
        blob = _json.dumps(pack.to_dict())
        if "d4 probe prose" in blob:
            return {"ok": False, "detail": "evidence prose leaked into a pack"}
    return {"ok": True, "detail": f"{len(packs)} packs, IDs only"}


def gate_mcp_doctor() -> dict:
    sys.path.insert(0, str(REPO))
    from lab.application.cpcs_guided_handlers import cpcs_doctor
    from lab.compiler.profiles import REPO_ROOT

    result = cpcs_doctor(REPO_ROOT, runtime_path=RUNTIME)
    doctor_ok = result["checks"].get("knowledge_application") == "OK"
    from lab.application import service as service_module
    op_registered = "cpcs.knowledge.apply.inspect" in service_module.OPERATIONS
    return {"ok": doctor_ok and op_registered,
            "doctor": result["checks"].get("knowledge_application"),
            "op_registered": op_registered}


def gate_artifacts() -> dict:
    problems = []
    for name in SCHEMA_FILES:
        path = OUT / name
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{name}: {exc}")
            continue
        if "$schema" in value:
            try:
                Draft202012Validator.check_schema(value)
            except Exception as exc:  # schema errors raise
                problems.append(f"{name}: invalid schema: {exc}")
    return {"ok": not problems, "problems": problems}


def main() -> int:
    gates: dict[str, dict] = {}
    ka1 = _unittest(*KA1_SUITES)
    gates["bridge_operational"] = {"ok": ka1["ok"], "detail": ka1["tail"]}
    pre_ka = _unittest(*PRE_KA_SUITES)
    gates["all_pre_ka_suites_pass"] = {"ok": pre_ka["ok"],
                                       "detail": pre_ka["tail"]}
    full = {}
    for name, command in FULL_SUITES:
        result = subprocess.run(
            [sys.executable, *command], cwd=REPO, capture_output=True,
            text=True, timeout=3600)
        full[name] = result.returncode == 0
    gates["control_a_unchanged"] = {"ok": all(full.values()),
                                    "detail": full}
    gates["representation_decisions_correct"] = gate_representation_decisions()
    gates["hip_toss_state_transition_required"] = (
        gate_hip_toss_state_transition())
    gates["cross_domain_fixtures_pass"] = {
        "ok": ka1["ok"], "detail": "covered by test_ka1_fixtures hermetic"}
    gates["D4_preserved"] = gate_d4()
    gates["mcp_doctor_integrated"] = gate_mcp_doctor()
    gates["all_artifacts_valid"] = gate_artifacts()
    runtime_env = dict(os.environ)
    runtime_env["CPCS_FROZEN_RUNTIME_PATH"] = RUNTIME
    smoke = _unittest("lab.application.tests.test_ka1_fixtures."
                      "Ka1FixturesRealRuntime", env=runtime_env) \
        if Path(RUNTIME).is_dir() else None
    gates["real_runtime_smoke_pass"] = {
        "ok": bool(smoke and smoke["ok"]),
        "detail": "real-runtime smoke skipped (runtime unavailable)" if smoke is None
        else smoke["tail"],
    }
    overall = all(gate["ok"] for gate in gates.values())
    artifact = {
        "artifact": "CPCS_KA1_ACCEPTANCE",
        "version": "v0.1",
        "status": "PASS" if overall else "FAIL",
        "gates": gates,
    }
    ARTIFACT.write_text(json.dumps(artifact, indent=1) + "\n")
    print(json.dumps({"status": artifact["status"],
                      "gates": {k: v["ok"] for k, v in gates.items()}},
                     indent=1))
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
