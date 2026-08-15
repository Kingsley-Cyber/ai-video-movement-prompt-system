# BOOT-1 — CPCS First-Run Bootstrap — Report

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

- bootstrap suite: PASS
- full application suite: PASS
- real MCP golden suite: PASS
- release suite: PASS

## Acceptance

`CPCS_BOOTSTRAP_ACCEPTANCE_v0.1.json`: **PASS** —
17/17 gates.

## Status

**CPCS_BOOTSTRAP_READY**
