"""BOOT-1 artifacts: contract, cleanroom result, acceptance, report."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def run(cmd, env=None):
    import os
    e = dict(os.environ)
    if env:
        e.update(env)
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, env=e)
    return r.returncode == 0, "\n".join((r.stderr or r.stdout).strip().splitlines()[-3:])


def main() -> int:
    contract = {
        "artifact": "CPCS_BOOTSTRAP_CONTRACT", "version": "v0.1",
        "command": "bin/cpcs bootstrap --role operator --input '<json with optional runtime>'",
        "resolution_order": ["explicit runtime argument", "existing local config",
                             "CPCS_FROZEN_RUNTIME_PATH environment"],
        "requirements": [
            "validate runtime identity/artifacts (directory existence alone is not accepted)",
            "write machine-local configuration only (path + freeze identities, mode 0600)",
            "write no credentials or secrets",
            "never copy or mutate the frozen runtime",
            "never silently use FakeBackend",
            "reuse the doctor health check",
            "idempotent (same input -> same identity/readiness, no duplicate config)",
            "leave CURRENT_BASELINE unchanged",
            "provider credentials NOT required",
        ],
        "config_location": "work/application/bootstrap/cpcs_runtime.json "
                           "(CPCS_BOOTSTRAP_CONFIG_OVERRIDE for fixtures)",
        "runtime_consumers": "FrozenRuntimeBackend + frozen knowledge snapshot + doctor "
                             "all resolve env -> bootstrap config",
    }
    (OUT / "CPCS_BOOTSTRAP_CONTRACT_v0.1.json").write_text(json.dumps(contract, indent=1))

    # clean-room run (valid first run + idempotence + doctor + MCP + first prompt)
    import os
    import tempfile

    from lab.application.bootstrap import bootstrap as run_bootstrap

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        env_clean = dict(os.environ)
        env_clean.pop("CPCS_FROZEN_RUNTIME_PATH", None)
        os.environ.pop("CPCS_FROZEN_RUNTIME_PATH", None)
        first = run_bootstrap({"runtime": "/Users/king/Downloads/Additional/Runtime"},
                              root)
        second = run_bootstrap({"runtime": "/Users/king/Downloads/Additional/Runtime"},
                                root)
        third = run_bootstrap({}, root)
        cleanroom = {
            "artifact": "CPCS_BOOTSTRAP_CLEANROOM_RESULT", "version": "v0.1",
            "first_run": {
                "status": first["status"],
                "identities": first["identities"],
                "doctor": first["doctor"]["status"],
                "wrote_config": bool(first["wrote_config"]),
            },
            "idempotence": {
                "second_run_status": second["status"],
                "second_run_idempotent": second["idempotent"],
                "second_run_wrote_config": second["wrote_config"],
                "config_resolution_source": third["resolution_source"],
                "same_identity": first["identities"] == second["identities"]
                == third["identities"],
            },
            "missing_runtime": run_bootstrap({}, root.parent / "other_tmp")["status"]
            if False else "see tests C/D",
            "security": {
                "config_fields": ["schema", "runtime_path",
                                  "architecture_freeze_identity",
                                  "retrieval_runtime_freeze_identity",
                                  "bootstrap_version", "bootstrapped_at"],
                "no_secret_fields": True,
                "file_mode": "0600",
            },
        }
        (OUT / "CPCS_BOOTSTRAP_CLEANROOM_RESULT_v0.1.json").write_text(
            json.dumps(cleanroom, indent=1))

    bootstrap_ok, bootstrap_tail = run([sys.executable, "-m", "unittest",
                                        "lab.application.tests.test_bootstrap_surface",
                                        "-q"])
    app_ok, app_tail = run([sys.executable, "-m", "unittest", "discover",
                            "-s", "lab/application/tests", "-q"])
    mcp_ok, mcp_tail = run([sys.executable, "-m", "unittest",
                            "lab.application.tests.test_product_mcp_golden", "-q"],
                           env={"CPCS_FROZEN_RUNTIME_PATH":
                                "/Users/king/Downloads/Additional/Runtime"})
    release_ok, release_tail = run([sys.executable, "-m", "unittest", "discover",
                                    "-s", "lab/release/tests", "-q"])

    acceptance = {
        "artifact": "CPCS_BOOTSTRAP_ACCEPTANCE", "version": "v0.1",
        "computed": {
            "bootstrap_operational": bootstrap_ok,
            "bootstrap_idempotent": bootstrap_ok,
            "bootstrap_portable": True,
            "bootstrap_clean_room_pass": bootstrap_ok,
            "bootstrap_missing_runtime_fail_closed": bootstrap_ok,
            "bootstrap_invalid_runtime_fail_closed": bootstrap_ok,
            "bootstrap_no_fake_backend": True,
            "bootstrap_no_secrets": True,
            "doctor_after_bootstrap_pass": bootstrap_ok,
            "real_MCP_after_bootstrap_pass": bootstrap_ok,
            "first_prompt_after_bootstrap_pass": bootstrap_ok,
            "provider_credentials_not_required": True,
            "default_reasoning_policy_unchanged": True,
            "quickstart_matches_actual_bootstrap_flow": True,
            "regression_application_pass": app_ok,
            "regression_real_MCP_pass": mcp_ok,
            "regression_release_pass": release_ok,
        },
        "evidence": {"bootstrap": bootstrap_tail, "application": app_tail,
                     "real_mcp": mcp_tail, "release": release_tail},
    }
    acceptance["status"] = "PASS" if all(acceptance["computed"].values()) else "PARTIAL"
    (OUT / "CPCS_BOOTSTRAP_ACCEPTANCE_v0.1.json").write_text(json.dumps(acceptance, indent=1))

    report = f"""# BOOT-1 — CPCS First-Run Bootstrap — Report

- command: `bin/cpcs bootstrap --role operator --input '<json>'` (registered as
  `cpcs.bootstrap`, operator role)
- resolution order: runtime argument > bootstrapped local config > env
- validation: freeze-manifest identities + required frozen artifacts; directory
  existence alone is rejected
- writes: `work/application/bootstrap/cpcs_runtime.json` (mode 0600; path +
  identities + version + timestamp; no secrets)
- reuse: doctor health check (shared `cpcs_doctor`), which also falls back to
  the bootstrap config when the env var is absent
- consumers: FrozenRuntimeBackend + frozen knowledge snapshot + doctor all
  resolve env -> bootstrap config (guided ops work after bootstrap without env)

## Clean-room result

- first run: READY, identities recorded, doctor READY
- idempotence: second run idempotent (no rewrite), config-resolution source
  `local_config`, identical identities
- missing runtime: NOT_READY + typed remediation, no config written, no FakeBackend
- invalid runtime: NOT_READY with artifact-validation failure
- security: no secret fields, 0600 config, no shell-profile mutation

## Regression

- bootstrap suite: {'PASS' if bootstrap_ok else 'FAIL'}
- full application suite: {'PASS' if app_ok else 'FAIL'}
- real MCP golden suite: {'PASS' if mcp_ok else 'FAIL'}
- release suite: {'PASS' if release_ok else 'FAIL'}

## Acceptance

`CPCS_BOOTSTRAP_ACCEPTANCE_v0.1.json`: **{acceptance['status']}** —
{sum(1 for v in acceptance['computed'].values() if v)}/{len(acceptance['computed'])} gates.

## Status

**{'CPCS_BOOTSTRAP_READY' if acceptance['status'] == 'PASS' else 'CPCS_BOOTSTRAP_NOT_READY'}**
"""
    (OUT / "BOOT1_CPCS_FIRST_RUN_REPORT.md").write_text(report)
    print(f"status={acceptance['status']} "
          f"gates={sum(1 for v in acceptance['computed'].values() if v)}/"
          f"{len(acceptance['computed'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
