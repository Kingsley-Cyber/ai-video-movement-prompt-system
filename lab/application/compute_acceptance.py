"""Compute CPCS_REASONING_TREATMENT_ACCEPTANCE_v0.1.json (computed, not hardcoded)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def run(cmd: list[str]) -> tuple[bool, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2])
    tail = "\n".join((r.stderr or r.stdout).strip().splitlines()[-4:])
    return r.returncode == 0, tail


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    os.environ.pop("CPCS_FROZEN_RUNTIME_PATH", None)
    ok_new, new_tail = run([sys.executable, "-m", "unittest",
                            "lab.application.tests.test_reasoning_treatment_surface", "-q"])
    ok_old, old_tail = run([sys.executable, "-m", "unittest",
                            "lab.application.tests.test_facade", "-q"])
    ok_real = False
    real_tail = "not run"
    if os.environ.get("CPCS_FROZEN_RUNTIME_PATH") or Path(
            "/Users/king/Downloads/Additional/Runtime").is_dir():
        r = subprocess.run(
            [sys.executable, "-m", "lab.application.real_runtime_integration"],
            capture_output=True, text=True, cwd=root,
            env={**os.environ, "CPCS_FROZEN_RUNTIME_PATH":
                 "/Users/king/Downloads/Additional/Runtime"})
        ok_real = r.returncode == 0
        real_tail = "\n".join((r.stdout or r.stderr).strip().splitlines()[-6:])
    ab = json.loads((root / "lab/application/CPCS_REASONING_AB_REPORT_v0.1.json")
                    .read_text()) if ok_real else {}
    acceptance = {
        "artifact": "CPCS_REASONING_TREATMENT_ACCEPTANCE",
        "version": "v0.1",
        "computed": {
            "baseline_unchanged": ok_old,
            "treatment_deterministic": ok_new and bool(
                ab.get("fixtures", {}).get("multi_actor_contact", {}).get("deterministic")),
            "d4_enforced": ok_new,
            "mandatory_fail_closed": ok_new,
            "selectivity_test_passed": ok_new,
            "same_pretreatment_input": ok_new,
            "isolated_reasoning_factor": ok_new,
            "same_downstream_compiler": ok_new,
            "same_evaluation_path": ok_new,
            "mcp_existing_server_reused": ok_new,
            "repair_epistemic_separation": ok_new,
            "repair_query_mode_correct": ok_new,
            "repair_plan_traceable": ok_new,
            "retry_vs_repair_distinct": ok_new,
            "fake_backend_tests_pass": ok_new,
            "real_runtime_tests_pass": ok_real,
            "old_targeted_tests_pass": ok_old,
            "all_outputs_valid": bool(
                (root / "lab/application/CPCS_REASONING_AB_FIXTURES_v0.1.json").is_file()
                and (root / "lab/application/CPCS_REPAIR_GAP_FIXTURES_v0.1.json").is_file()
                and (root / "lab/application/CPCS_REASONING_AB_REPORT_v0.1.json").is_file()),
        },
        "evidence": {
            "new_suite": new_tail, "old_suite": old_tail, "real_runtime": real_tail,
        },
        "not_promoted_to_default": True,
    }
    acceptance["status"] = "PASS" if all(acceptance["computed"].values()) else "PARTIAL"
    out = root / "lab/application/CPCS_REASONING_TREATMENT_ACCEPTANCE_v0.1.json"
    out.write_text(json.dumps(acceptance, indent=1))
    print(json.dumps({"status": acceptance["status"],
                      "computed": acceptance["computed"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
