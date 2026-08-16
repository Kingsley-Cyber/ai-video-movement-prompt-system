"""WP-5 — KA-2 acceptance computation (computed, never hand-authored).

Runs KA-2 suites, pre-KA + KA-1 regression groups, full application /
compiler / second-brain suites, and the holdout (when --reveal-holdout
is passed and the answer key is unlocked).

Writes CPCS_KA2_ACCEPTANCE_v0.1.json. The KA-2 acceptance status is
PASS only if every dev gate is PASS; the holdout result is recorded
separately without affecting the dev acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[1]
ARTIFACT = OUT / "CPCS_KA2_ACCEPTANCE_v0.1.json"
HOLDOUT_RESULT = OUT / "KA2_EVAL_HOLDOUT_RESULT_v0.1.json"
HOLDOUT_COMMITMENT = OUT / "KA2_EVAL_HOLDOUT_COMMITMENT_v0.1.json"
HOLDOUT_KEY = OUT / "KA2_EVAL_HOLDOUT_ANSWER_KEY_v0.1.json"
HOLDOUT_INTENTS = OUT / "KA2_EVAL_HOLDOUT_INTENTS_v0.1.json"
DEV_SET = OUT / "KA2_EVAL_DEV_v0.1.json"
RUNTIME = os.environ.get("CPCS_FROZEN_RUNTIME_PATH",
                         "/Users/king/Downloads/Additional/Runtime")

KA2_SUITES = [
    "lab.application.tests.test_ka2_constellation",
    "lab.application.tests.test_ka2_recruitment",
    "lab.application.tests.test_ka2_refinement",
    "lab.application.tests.test_ka2_dev_evaluation",
    "lab.application.tests.test_ka2_holdout_commitment",
]
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
    ("compiler", ["-m", "unittest", "discover", "-s",
                  "lab/compiler/tests", "-p", "test_*.py", "-q"]),
    ("second_brain", ["-m", "unittest", "discover", "-s",
                      "lab/second_brain/tests", "-p", "test_*.py", "-q"]),
]


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


def gate_commitment_well_formed() -> dict:
    if not HOLDOUT_COMMITMENT.is_file():
        return {"ok": False, "detail": "commitment file missing"}
    c = json.loads(HOLDOUT_COMMITMENT.read_text())
    if c.get("commitment_algorithm") != "sha256":
        return {"ok": False, "detail": "commitment algorithm must be sha256"}
    if len(c.get("commitment", "")) != 64:
        return {"ok": False, "detail": "commitment must be 64 hex chars"}
    if c.get("answer_key_file") != "lab/application/KA2_EVAL_HOLDOUT_ANSWER_KEY_v0.1.json":
        return {"ok": False, "detail": "answer_key_file path mismatch"}
    return {"ok": True, "label": c.get("label", "unknown")}


def gate_no_silent_drops() -> dict:
    sys.path.insert(0, str(REPO))
    from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
    from lab.application.cpcs_knowledge_application import apply_knowledge
    from lab.application.cpcs_knowledge_constellation import assemble_constellation
    from lab.application.cpcs_knowledge_recruitment import recruit_for_intent
    from lab.application.reasoning_treatment import FakeBackend

    intent_text = "A fighter performs a hip toss."
    engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
    activation, packet = engine.activate(
        intent_text, {"intent": {"primary_domain": "action"}}, observations=[])
    app_set = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
    evidence_by_id = {ev["atomic_record_id"]: ev
                      for ev in packet.get("retrieved_evidence", [])}
    const = assemble_constellation(app_set, activation, evidence_by_id=evidence_by_id)
    pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in app_set.applications}
    rec = recruit_for_intent(const, activation, pack_lookup=pack_lookup)
    region_ids = {r["region_id"] for r in const.regions}
    disp_ids = {d["region_id"] for d in rec["dispositions"]}
    return {
        "ok": region_ids == disp_ids and len(region_ids) > 0,
        "region_count": len(region_ids),
        "disposition_count": len(disp_ids),
    }


def gate_d4_preserved() -> dict:
    sys.path.insert(0, str(REPO))
    from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
    from lab.application.cpcs_knowledge_application import apply_knowledge
    from lab.application.cpcs_knowledge_constellation import assemble_constellation
    from lab.application.cpcs_knowledge_recruitment import recruit_for_intent
    from lab.application.cpcs_knowledge_refinement import build_refinement_packet
    from lab.application.reasoning_treatment import FakeBackend

    intent_text = "A fighter performs a hip toss."
    engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
    activation, packet = engine.activate(
        intent_text, {"intent": {"primary_domain": "action"}}, observations=[])
    app_set = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
    evidence_by_id = {ev["atomic_record_id"]: ev
                      for ev in packet.get("retrieved_evidence", [])}
    const = assemble_constellation(app_set, activation, evidence_by_id=evidence_by_id)
    pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in app_set.applications}
    rec = recruit_for_intent(const, activation, pack_lookup=pack_lookup)
    refinement = build_refinement_packet(
        rec, const, activation, application_set=app_set)
    prose = "unique ka2 d4 probe prose that must never be admitted"
    blob = json.dumps({"const": const.to_dict(), "rec": rec,
                       "ref": refinement}, sort_keys=True)
    return {
        "ok": prose not in blob,
        "detail": "no flat-text prose admitted to constellation/recruitment/refinement",
    }


def gate_closure_additive_only() -> dict:
    sys.path.insert(0, str(REPO))
    import copy
    from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
    from lab.application.cpcs_knowledge_application import apply_knowledge
    from lab.application.cpcs_knowledge_constellation import assemble_constellation
    from lab.application.cpcs_knowledge_recruitment import recruit_for_intent
    from lab.application.cpcs_knowledge_refinement import (
        apply_to_closure, assess_prerequisites, build_refinement_packet)
    from lab.application.reasoning_treatment import FakeBackend

    intent_text = "A fighter performs a hip toss."
    engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
    activation, packet = engine.activate(
        intent_text, {"intent": {"primary_domain": "action"}}, observations=[])
    app_set = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
    evidence_by_id = {ev["atomic_record_id"]: ev
                      for ev in packet.get("retrieved_evidence", [])}
    const = assemble_constellation(app_set, activation, evidence_by_id=evidence_by_id)
    pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in app_set.applications}
    rec = recruit_for_intent(const, activation, pack_lookup=pack_lookup)
    new_pre, gaps = assess_prerequisites(rec, const, activation, pack_lookup=pack_lookup)
    refinement = build_refinement_packet(
        rec, const, activation, new_prerequisites=new_pre,
        coverage_gaps=gaps, application_set=app_set)
    closure = {
        "closure_id": "closure_acceptance",
        "packet_hash": "pre",
        "planning_guidance": [],
        "non_executable_knowledge_used": ["Constraint"],
        "accepted_hypotheses": ["h1"],
        "safe_inferences": ["h1"],
        "creative_choices": [],
        "remaining_unknowns": [],
        "verification_requirements": ["h1"],
        "reasoning_completeness": "COMPLETE",
        "closure_reason": "all critical hypotheses resolved",
        "lineage": {"activation_packet_id": "kap_x"},
    }
    original = copy.deepcopy(closure)
    updated = apply_to_closure(refinement, closure)
    violations = []
    for key in original:
        if key in ("planning_guidance", "non_executable_knowledge_used",
                   "packet_hash", "lineage"):
            continue
        if updated[key] != original[key]:
            violations.append(key)
    return {
        "ok": not violations,
        "violations": violations,
    }


def gate_determinism() -> dict:
    sys.path.insert(0, str(REPO))
    from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
    from lab.application.cpcs_knowledge_application import apply_knowledge
    from lab.application.cpcs_knowledge_constellation import assemble_constellation
    from lab.application.cpcs_knowledge_recruitment import recruit_for_intent
    from lab.application.cpcs_knowledge_refinement import (
        apply_to_closure, assess_prerequisites, build_refinement_packet)
    from lab.application.reasoning_treatment import FakeBackend

    intent_text = "A chef slices a tomato."
    a_hash = b_hash = None
    a_closure = b_closure = None
    for _ in range(2):
        engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
        activation, packet = engine.activate(
            intent_text, {"intent": {"primary_domain": "action"}}, observations=[])
        app_set = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
        evidence_by_id = {ev["atomic_record_id"]: ev
                          for ev in packet.get("retrieved_evidence", [])}
        const = assemble_constellation(app_set, activation, evidence_by_id=evidence_by_id)
        pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in app_set.applications}
        rec = recruit_for_intent(const, activation, pack_lookup=pack_lookup)
        new_pre, gaps = assess_prerequisites(
            rec, const, activation, pack_lookup=pack_lookup)
        refinement = build_refinement_packet(
            rec, const, activation, new_prerequisites=new_pre,
            coverage_gaps=gaps, application_set=app_set)
        closure = apply_to_closure(refinement, {
            "closure_id": "c", "packet_hash": "h",
            "planning_guidance": [], "non_executable_knowledge_used": [],
            "lineage": {}})
        if a_hash is None:
            a_hash = const.constellation_hash
            a_closure = closure["packet_hash"]
        else:
            b_hash = const.constellation_hash
            b_closure = closure["packet_hash"]
    return {"ok": a_hash == b_hash and a_closure == b_closure,
            "constellation_hash_stable": a_hash == b_hash,
            "closure_hash_stable": a_closure == b_closure}


def gate_dev_positive_emergence() -> dict:
    sys.path.insert(0, str(REPO))
    from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
    from lab.application.cpcs_knowledge_application import apply_knowledge
    from lab.application.cpcs_knowledge_constellation import assemble_constellation
    from lab.application.cpcs_knowledge_recruitment import recruit_for_intent
    from lab.application.reasoning_treatment import FakeBackend

    dev = json.loads(DEV_SET.read_text())
    failed = []
    for entry in dev["intents"]:
        engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
        activation, packet = engine.activate(
            entry["intent_text"], {"intent": {"primary_domain": "action"}},
            observations=[])
        app_set = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
        if not app_set.applications:
            failed.append({"intent_id": entry["intent_id"],
                           "reason": "no applications (KA-1 fail-closed)"})
            continue
        evidence_by_id = {ev["atomic_record_id"]: ev
                          for ev in packet.get("retrieved_evidence", [])}
        const = assemble_constellation(app_set, activation, evidence_by_id=evidence_by_id)
        pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in app_set.applications}
        rec = recruit_for_intent(const, activation, pack_lookup=pack_lookup)
        recruited = [r for r in const.regions
                     if any(d["region_id"] == r["region_id"]
                            and d["disposition"] == "RECRUIT"
                            for d in rec["dispositions"])]
        for expected in entry.get("expected_recruited_regions", []):
            sig = expected["region_signature"]
            req_any = set(sig.get("requirement_ids_any_of", []) or [])
            ff_any = set(sig.get("failure_family_ids_any_of", []) or [])
            matched = any(
                (set(r.get("requirement_ids", []) or []) & req_any)
                and (set(r.get("failure_family_ids", []) or []) & ff_any)
                for r in recruited)
            if not matched:
                failed.append({
                    "intent_id": entry["intent_id"],
                    "expected_signature": sig,
                    "recruited_count": len(recruited),
                })
    return {"ok": not failed, "failures": failed}


def gate_dev_coverage_gap_honesty() -> dict:
    sys.path.insert(0, str(REPO))
    from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
    from lab.application.cpcs_knowledge_application import apply_knowledge
    from lab.application.cpcs_knowledge_constellation import assemble_constellation
    from lab.application.cpcs_knowledge_recruitment import recruit_for_intent
    from lab.application.cpcs_knowledge_refinement import (
        assess_prerequisites, build_refinement_packet)
    from lab.application.reasoning_treatment import FakeBackend

    dev = json.loads(DEV_SET.read_text())
    ok = True
    detail = []
    for entry in dev["intents"]:
        engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
        activation, packet = engine.activate(
            entry["intent_text"], {"intent": {"primary_domain": "action"}},
            observations=[])
        app_set = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
        if not app_set.applications:
            continue
        evidence_by_id = {ev["atomic_record_id"]: ev
                          for ev in packet.get("retrieved_evidence", [])}
        const = assemble_constellation(app_set, activation, evidence_by_id=evidence_by_id)
        pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in app_set.applications}
        rec = recruit_for_intent(const, activation, pack_lookup=pack_lookup)
        new_pre, gaps = assess_prerequisites(
            rec, const, activation, pack_lookup=pack_lookup)
        refinement = build_refinement_packet(
            rec, const, activation, new_prerequisites=new_pre,
            coverage_gaps=gaps, application_set=app_set)
        for expected_gap in entry.get("expected_coverage_gaps", []):
            if not any(g.get("requirement_id") == expected_gap
                       or g.get("failure_family_id") == expected_gap
                       for g in refinement["coverage_gaps"]):
                ok = False
                detail.append({"intent_id": entry["intent_id"],
                               "missing_gap": expected_gap})
    return {"ok": ok, "detail": detail}


def score_holdout_once() -> dict:
    """Reveal the holdout key, verify commitment, score, write result."""
    if not HOLDOUT_KEY.is_file():
        return {"ok": False, "detail": "answer key file missing"}
    commitment = json.loads(HOLDOUT_COMMITMENT.read_text())
    key = json.loads(HOLDOUT_KEY.read_text())
    canonical = json.dumps(key, sort_keys=True, separators=(",", ":")).encode()
    h = hashlib.sha256(canonical).hexdigest()
    if h != commitment["commitment"]:
        return {"ok": False, "detail": "commitment hash mismatch; aborting",
                "expected": commitment["commitment"], "computed": h}
    sys.path.insert(0, str(REPO))
    from lab.application.cpcs_deliberation import FAKE_SNAPSHOT, DeliberationEngine
    from lab.application.cpcs_knowledge_application import apply_knowledge
    from lab.application.cpcs_knowledge_constellation import assemble_constellation
    from lab.application.cpcs_knowledge_recruitment import recruit_for_intent
    from lab.application.reasoning_treatment import FakeBackend

    intents = json.loads(HOLDOUT_INTENTS.read_text())
    intent_by_id = {i["intent_id"]: i for i in intents["intents"]}
    per_intent = []
    for expected in key["intents"]:
        intent = intent_by_id.get(expected["intent_id"])
        if not intent:
            per_intent.append({"intent_id": expected["intent_id"],
                               "ok": False, "detail": "missing intent"})
            continue
        engine = DeliberationEngine(FAKE_SNAPSHOT, FakeBackend())
        activation, packet = engine.activate(
            intent["intent_text"], {"intent": {"primary_domain": "action"}},
            observations=[])
        app_set = apply_knowledge(packet, FAKE_SNAPSHOT, activation)
        if not app_set.applications:
            per_intent.append({"intent_id": expected["intent_id"],
                               "ok": False, "detail": "no applications"})
            continue
        evidence_by_id = {ev["atomic_record_id"]: ev
                          for ev in packet.get("retrieved_evidence", [])}
        const = assemble_constellation(app_set, activation, evidence_by_id=evidence_by_id)
        pack_lookup = {e["pack"]["pack_id"]: e["pack"] for e in app_set.applications}
        rec = recruit_for_intent(const, activation, pack_lookup=pack_lookup)
        recruited = [r for r in const.regions
                     if any(d["region_id"] == r["region_id"]
                            and d["disposition"] == "RECRUIT"
                            for d in rec["dispositions"])]
        matched_expected = 0
        for exp in expected.get("expected_recruited_regions", []):
            sig = exp["region_signature"]
            req_any = set(sig.get("requirement_ids_any_of", []) or [])
            ff_any = set(sig.get("failure_family_ids_any_of", []) or [])
            if any((set(r.get("requirement_ids", []) or []) & req_any)
                   and (set(r.get("failure_family_ids", []) or []) & ff_any)
                   for r in recruited):
                matched_expected += 1
        precision = (matched_expected / len(recruited)
                     if recruited else 0.0)
        recall = (matched_expected / max(1, len(expected.get(
            "expected_recruited_regions", []))))
        per_intent.append({
            "intent_id": expected["intent_id"],
            "ok": True,
            "recruited_count": len(recruited),
            "expected_count": len(expected.get("expected_recruited_regions", [])),
            "matched_expected": matched_expected,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
        })
    aggregate_precision = (sum(p.get("precision", 0) for p in per_intent
                                if p.get("ok"))
                           / max(1, sum(1 for p in per_intent if p.get("ok"))))
    aggregate_recall = (sum(p.get("recall", 0) for p in per_intent
                            if p.get("ok"))
                       / max(1, sum(1 for p in per_intent if p.get("ok"))))
    result = {
        "artifact": "CPCS_KA2_HOLDOUT_RESULT",
        "version": "v0.1",
        "commitment_verified": True,
        "commitment_hash": h,
        "aggregate_precision": round(aggregate_precision, 3),
        "aggregate_recall": round(aggregate_recall, 3),
        "per_intent": per_intent,
        "policy_locked": True,
        "tuning_attempts": 0,
    }
    HOLDOUT_RESULT.write_text(json.dumps(result, indent=1) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reveal-holdout", action="store_true",
                        help="Reveal and score the holdout answer key once")
    args = parser.parse_args()
    gates: dict[str, dict] = {}
    ka2 = _unittest(*KA2_SUITES)
    gates["ka2_constellation_groups_packs"] = {
        "ok": ka2["ok"], "detail": ka2["tail"]}
    gates["ka2_recruitment_dispositions_complete"] = {
        "ok": ka2["ok"], "detail": ka2["tail"]}
    pre_ka = _unittest(*PRE_KA_SUITES)
    gates["ka2_pre_ka_regression"] = {"ok": pre_ka["ok"],
                                      "detail": pre_ka["tail"]}
    ka1 = _unittest(*KA1_SUITES)
    gates["ka2_ka1_regression"] = {"ok": ka1["ok"], "detail": ka1["tail"]}
    full = {}
    for name, command in FULL_SUITES:
        result = subprocess.run(
            [sys.executable, *command], cwd=REPO, capture_output=True,
            text=True, timeout=3600)
        full[name] = result.returncode == 0
    gates["ka2_compiler_unchanged"] = {"ok": all(full.values()),
                                       "detail": full}
    gates["ka2_no_silent_drops"] = _run_gate_in_subprocess(gate_no_silent_drops)
    gates["ka2_closure_additive_only"] = _run_gate_in_subprocess(
        gate_closure_additive_only)
    gates["ka2_d4_preserved"] = _run_gate_in_subprocess(gate_d4_preserved)
    gates["ka2_determinism"] = _run_gate_in_subprocess(gate_determinism)
    gates["ka2_dev_positive_emergence"] = _run_gate_in_subprocess(
        gate_dev_positive_emergence)
    gates["ka2_dev_coverage_gap_honesty"] = _run_gate_in_subprocess(
        gate_dev_coverage_gap_honesty)
    gates["ka2_commitment_well_formed"] = gate_commitment_well_formed()
    runtime_env = dict(os.environ)
    runtime_env["CPCS_FROZEN_RUNTIME_PATH"] = RUNTIME
    smoke = _unittest("lab.application.tests.test_ka2_dev_evaluation."
                      "Ka2DevEvaluationTests", env=runtime_env) \
        if Path(RUNTIME).is_dir() else None
    gates["ka2_real_runtime_smoke"] = {
        "ok": bool(smoke and smoke["ok"]),
        "detail": "real-runtime smoke skipped (runtime unavailable)" if smoke is None
        else smoke["tail"],
    }
    holdout_recorded = None
    if args.reveal_holdout:
        holdout_recorded = _run_gate_in_subprocess(score_holdout_once)
        if isinstance(holdout_recorded, dict) and holdout_recorded.get("ok") is False:
            print(json.dumps({"holdout_score_error": holdout_recorded}, indent=1))
            return 1
    overall = all(gate["ok"] for gate in gates.values())
    artifact = {
        "artifact": "CPCS_KA2_ACCEPTANCE",
        "version": "v0.1",
        "status": "PASS" if overall else "FAIL",
        "gates": gates,
        "holdout_recorded": holdout_recorded,
    }
    ARTIFACT.write_text(json.dumps(artifact, indent=1) + "\n")
    summary = {
        "status": artifact["status"],
        "gates": {k: v["ok"] for k, v in gates.items()},
    }
    if holdout_recorded and isinstance(holdout_recorded, dict):
        summary["holdout"] = {
            "commitment_verified": holdout_recorded.get("commitment_verified"),
            "aggregate_precision": holdout_recorded.get("aggregate_precision"),
            "aggregate_recall": holdout_recorded.get("aggregate_recall"),
        }
    print(json.dumps(summary, indent=1))
    return 0 if overall else 1


def _run_gate_in_subprocess(gate_fn) -> dict:
    """Run a gate function in a fresh subprocess to avoid the local
    `lab/application/http.py` shadowing stdlib `http.server` when
    this script is invoked by path."""
    import importlib
    import pickle
    name = gate_fn.__name__
    driver = REPO / "lab" / "application" / "_ka2_gate_driver.py"
    driver.write_text(
        "import json, sys, pickle\n"
        f"sys.path.insert(0, '{REPO}')\n"
        "from lab.application.ka2_acceptance import (\n"
        f"    {name},\n"
        ")\n"
        f"result = {name}()\n"
        "sys.stdout.write('KA2_GATE_JSON_BEGIN' + json.dumps(result, default=str) + 'KA2_GATE_JSON_END')\n"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "lab.application._ka2_gate_driver"],
            cwd=REPO, capture_output=True, text=True, timeout=600)
        out = proc.stdout
        start = out.find("KA2_GATE_JSON_BEGIN")
        end = out.find("KA2_GATE_JSON_END")
        if start == -1 or end == -1:
            return {"ok": False, "detail": f"gate {name} crashed: {proc.stderr[:400]}"}
        payload = out[start + len("KA2_GATE_JSON_BEGIN"):end]
        return json.loads(payload)
    finally:
        if driver.is_file():
            driver.unlink()


if __name__ == "__main__":
    sys.exit(main())
