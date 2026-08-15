# CPCS Reasoning-Layer Integration — Final Report (RL-1 → AB-2)

## Environment

- base commit: `ae19498` (Bind knowledge lenses to directing strategy)
- branch: `experiment/cpcs-reasoning-layer` (tracks origin/main)
- worktree: `/Users/king/cpcs-reasoning-ab`
- main checkout: untouched (only the untracked seed file it already contained)
- CPCS frozen runtime: `CPCS_FROZEN_RUNTIME_PATH=/Users/king/Downloads/Additional/Runtime` (external, portable, fail-closed)

## Files

Added:
- `lab/application/reasoning_treatment.py` — CPCSReasoningTreatmentPacket builder, TreatmentAdapter (D4-enforced), FrozenRuntimeBackend, FakeBackend, DiscrepancyBuilder, RepairPlanner, six operation handlers
- `lab/application/tests/test_reasoning_treatment_surface.py` — 20 structural acceptance tests
- `lab/application/real_runtime_integration.py` — real frozen-runtime integration runner
- `lab/application/materialize_fixtures.py` — hermetic A/B + repair fixture materializer
- `lab/application/compute_acceptance.py` — computed acceptance
- `lab/application/CPCS_REASONING_AB_FIXTURES_v0.1.json`
- `lab/application/CPCS_REPAIR_GAP_FIXTURES_v0.1.json`
- `lab/application/CPCS_REASONING_AB_REPORT_v0.1.json`
- `lab/application/CPCS_REASONING_TREATMENT_ACCEPTANCE_v0.1.json`

Modified:
- `lab/application/service.py` — additive only: one import block + six `_register(...)` calls (roles: plan/inspect = chat, prepare = operator; mutation_scope None; no curated authority)

## Control-A regression

- Targeted suites (facade, reasoning-policy, runtime, video-comparison, render-evidence, score, build, translations, runner, query, reasoning-policy, video-reasoning): **85/85 OK**
- Full `unittest` discovery (application 88, compiler 28, runtime 8, second_brain 147 (1 skipped), verification 13, repo_control 3, release 12): **299 tests OK**
- Baseline score resolution byte-deterministic before/after integration (asserted in test 1).

## New treatment tests

20/20 OK — baseline unchanged, determinism, same pretreatment input, isolated reasoning_policy factor, downstream controls may differ, D4 flat-text rejection, unsupported-mapping lineage (requirement + evidence + reason + `effect_on_score=none`), mandatory fail-closed, selectivity (trivial → zero overlays/controls/verification inflation), frozen-runtime-missing fail-closed (typed error; Control-A ops unaffected), FakeBackend hermeticity, MCP visibility by role (chat sees 4 read-only ops; operator/curator see all 6; no low-level retrieval ops exposed), discrepancy epistemology (complaint ≠ measured truth; corroboration supported), REPAIR_GAP query mode, repair traceability, repair through existing compiler (`cpcs.build_request/1.0`), retry-vs-repair identity, full fake A/B/repair loop deterministic.

## Real frozen-runtime integration (4 fixtures)

multi_actor_contact / possession_transfer / camera_occlusion / trivial — each: packet deterministic (hash-stable across two plans), freeze identities recorded (architecture + retrieval runtime sha256), evidence IDs structured (not flattened), overlays validated against the real field catalog, provider-neutral score + build request compiled via the existing compiler, 0 overlays / 68–73 unsupported mappings (D4: prose-only controls surfaced, never admitted as text) / +32 verification obligations per fixture.

Honest finding: the frozen runtime activates 32 mandatory requirements even for the trivial fixture — activation breadth is an inherited property of the frozen runtime (documented in its RO-3 report). The hermetic selectivity test proves the adapter adds nothing when no obligation exists; the real runtime's activation breadth is a remaining upstream property, not introduced by this integration.

## A/B fixtures (hermetic, deterministic)

9 fixtures (8 specified + trivial). Arm A = CURRENT_BASELINE, arm B = CPCS_REASONING_V1; identical normalized-intent hash, provider parameters, and downstream compiler/evaluation path; `differences_before_treatment = []`; arm B carries treatment packet id/hash, overlay ids, unsupported mappings.

## Repair-gap fixtures (3)

repair_contact_early_release, repair_possession_hand_swap, repair_orientation_occlusion — each produces a DiscrepancyPacket (expected/observed/user-report epistemically separated, CORROBORATED/CONTRADICTED computed), a RepairControlPlan (add/strengthen + invariants + verification changes + lineage generation_v1→repair_v1→v2), and a revised build request through the existing compiler.

## Acceptance

`CPCS_REASONING_TREATMENT_ACCEPTANCE_v0.1.json`: **PASS** — all 18 computed checks true. Treatment B remains EXPERIMENTAL; `reasoning_policy = CURRENT_BASELINE` stays the default; no production defaults, release qualification, curated knowledge, or MCP defaults changed.

## Remaining implementation gaps

1. Real-runtime activation breadth (trivial intents still activate many mandatory requirements) — inherited frozen-runtime property.
2. D4 admission policy yields zero score overlays on real-runtime controls: all prose-bearing controls land in `unsupported_mappings`; treatment B's repo-native effect today = typed verification obligations + structured evidence lineage. Expanding the typed path catalog would widen admissible overlays without violating D4.
3. REPAIR_GAP retrieval uses a discrepancy-driven query against the frozen production stack (the reserved REPAIR_GAP query family is approximated; full REPAIR_GAP retrieval remains unimplemented upstream).
4. FakeBackend exists for structural tests only; production never falls back to it.

## Ready for live A/B video generation?

**No.** The reasoning layer itself is integrated and validated; live generation remains blocked upstream by the VG-1 credential gate (no provider credentials; fail-closed) and by policy (no paid generation without authorization).

## Recommended next operation

1. Supply provider credentials and rerun VG-1 live to produce the first traceable artifact.
2. Then run a live A/B flight (`cpcs.reasoning.experiment.prepare` arms through the existing render/evaluation pipeline) — same intent, same provider/seed, A vs B.
3. Optionally widen the typed path catalog for admissible overlays (respecting D4).

Not done: merge, push, promotion to default, paid provider generation.
