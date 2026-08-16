# WP-7 — Cross-domain fixtures + real-runtime smoke

Depends on: WP-2..6.

## Scope

- `lab/application/ka1_fixtures.py`: three fixture specs with expected
  canonical-output contracts:

  1. COMBAT: "A fighter performs a hip toss."
     Expect: support chain, rotation roles, projection phase, recovery.
  2. ECOMMERCE: "A person unboxes a luxury watch."
     Expect: object identity, hand-object interaction, material visibility,
     camera realism.
  3. COOKING: "A chef slices a tomato."
     Expect: knife-object interaction, cutting motion, food deformation,
     hand safety.

- Each fixture runs through FakeBackend (hermetic, always) AND through the
  real frozen runtime (env-gated, skipUnless like
  `test_product_mcp_golden.py`).
- Output artifact: `lab/application/CPCS_KNOWLEDGE_APPLICATION_FIXTURES_v0.1.json`
  with per-fixture: principle pack count, decision mix, structured object
  counts, planning/reasoning-material counts, set_hash.

## Acceptance tests (`test_ka1_fixtures.py`)

- all three fixtures produce >=1 PrinciplePack and >=1 decision each
- decision mixes differ across domains (proves intent-conditioning, not a
  fixed template)
- each fixture's expected canonical output contract (above) is met
- real-runtime smoke (env-gated): bridge runs end-to-end via
  FrozenRuntimeBackend; determinism across two runs.

## Forbidden

- No new retrieval/compiler paths; consume existing treatment packets.

## Done when

`test_ka1_fixtures.py` passes (hermetic always; real-runtime when env set).
