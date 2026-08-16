# WP-8 — MCP inspect op + doctor line

Depends on: WP-4 (set exists to inspect).

## Scope

- Register ONE additive op in `lab/application/service.py`:
  - `cpcs.knowledge.apply.inspect` (chat, read-only): given intent_text,
    returns the KnowledgeApplicationSet summary (packs, decisions, set_hash,
    lineage) WITHOUT provider contact. Reuses the bridge + FrozenRuntimeBackend
    (fail closed without runtime — same behavior as other guided ops).
- `cpcs_guided_handlers.cpcs_doctor`: add one check line
  `knowledge_application: OK | MISSING` (import-time check of
  `cpcs_knowledge_application`). Does not gate readiness changes beyond the
  existing contract (it IS required: add to required list).

## Acceptance tests (`test_ka1_mcp.py`)

- tool visible through real MCP `tools/list` (subprocess test, env-gated)
- doctor output includes knowledge_application = OK
- unknown-runtime path: op returns typed error envelope; no crash.

## Forbidden

- No low-level retrieval mechanics exposed; inspect only.

## Done when

`test_ka1_mcp.py` passes (hermetic + env-gated MCP part).
