# WP-9 — Acceptance, regression, commit, push

Depends on: ALL previous WPs.

## Scope

- `lab/application/ka1_acceptance.py`: compute (never hardcode)
  `CPCS_KA1_ACCEPTANCE_v0.1.json` with gates:
  - bridge_operational (all WPs' tests pass)
  - representation_decisions_correct (CONTROL/VERIFICATION/PLANNING/
    NON_EXECUTABLE/COMPOSITE only; non-executable never CONTROL)
  - hip_toss_state_transition_required (action-labels-only fails)
  - cross_domain_fixtures_pass (3/3)
  - D4_preserved
  - control_a_unchanged (full app + compiler + second-brain suites)
  - mcp_doctor_integrated
  - real_runtime_smoke_pass (env-gated, recorded)
  - all_pre_ka_suites_pass
  - all_artifacts_valid (JSON parse + schema validation)
- Write `KA1_KNOWLEDGE_APPLICATION_REPORT.md` (per-fixture decision mixes,
  before/after comparison: generic throw vs structured interaction, remaining
  gaps, readiness: `CPCS_KNOWLEDGE_APPLICATION_READY | NOT_READY`).

## Release steps (only when all gates pass)

1. `git diff --check` clean; secret scan; portability scan (env-only runtime).
2. One commit on `experiment/cpcs-reasoning-layer`:
   `feat(cpcs): add knowledge application bridge`
3. `git push origin experiment/cpcs-reasoning-layer` (no merge, no PR, no
   promotion).

## Forbidden

- No frozen-runtime / Control-A / MCP transport / D4 changes.
- No unproven test waivers.

## Done when

Acceptance = PASS, report written, commit pushed, worktree clean.
