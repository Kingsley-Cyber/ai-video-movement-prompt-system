# TC-1 — CPCS Typed Knowledge Coverage Expansion — Final Report

## Source artifacts inspected

29 frozen CPCS artifacts (semantic architecture, vocabularies, trigger/requirement/activation/risk/failure models, linkage, evidence map, production retrieval contract, EC-1/EC-2 schemas + fixtures, both freeze manifests) — every path, version, and sha256 recorded in `CPCS_TYPED_EXPANSION_SOURCE_MANIFEST_v0.1.json`.

## Coverage ledger (bottom-up disposition, 100% coverage)

- 21/21 reasoning dimensions disposed (`CPCS_TYPED_KNOWLEDGE_COVERAGE_LEDGER_v0.1.json`)
- 8/8 ExpectedState condition types disposed
- 6/6 execution-obligation kinds disposed
- 43 canonical control types disposed (each `REPRESENTED:<target>` or `UNRESOLVED_WITH_REASON`)
- 77/77 reasoning requirements disposed: STATE 77, VERIFICATION 77, EXPECTED_STATE 77, GENERATION 73 (4 requirements legitimately lack generation representation)
- 53/53 HARD controls from EC-1 fixtures disposed: 32 TYPED_INVARIANT, 5 TYPED_RELATION, 15 TYPED_CONSTRAINT, 1 VERIFICATION_ONLY_WITH_JUSTIFICATION, **0 silently discarded, 0 prose coercions**

## New canonical structures (no schema migration)

The existing permissive collections (entities[], interactions[], beats[], continuity{}, camera{}, performance{}, style{}, editing{}) were already the correct home; the expansion layers a **typed contract** on top:

- `lab/compiler/cpcs_typed.py` — 19-entry path registry + 58-rule deterministic control-type map + 12 structured object constructors (entity state, interaction, event, temporal relation, causal edge, continuity invariant, constraint, camera-subject relation, performance event, style invariant, editing continuity)
- `cpcs_reasoning_path_registry.yaml` + `cpcs_reasoning_path_registry.schema.json` — every entry carries path_id, semantic family/kind, canonical target, value schema, scope/target types, merge operator, source control types, requirement classes, concept ids, allowed evidence classes, forbidden coercions, verification counterpart, provider_neutral=true, provenance requirements
- `CPCS_REASONING_PATH_REGISTRY_v0.1.json`, `CPCS_TYPED_MAPPING_RECEIPTS_v0.1.json`

## Deterministic mapping (D4 intact)

Control admission is by structured identifier only (control_type → registry path → typed constructor). No prose routing; prose-only controls remain `unsupported_mappings` with requirement/evidence lineage and `effect_on_score=none`. Constructors are idempotent, deterministic-ID, lineage-bearing (requirement_ids, evidence_ids, epistemic status, hardness), scope/target preserving.

## Real-runtime replay (before → after)

| fixture | before supported | after supported | before unsupported | after unsupported |
|---|---|---|---|---|
| multi_actor_contact | 0 | 45 structured (7 families) | 70 | 25 |
| possession_transfer | 0 | 43 structured | 68 | 25 |
| camera_occlusion | 0 | 41 structured | 73 | 32 |
| trivial | 0 | 42 structured* | 68 | 26 |

\* The trivial fixture's structured objects faithfully represent the frozen runtime's 32 activated mandatory requirements (upstream activation-breadth property, explicitly out of scope for TC-1). The hermetic selectivity test (FakeBackend trivial → **zero** structured objects/overlays/verification inflation) passes.

Supported rate: 0 → 0.59–0.64; unsupported rate: 1.0 → 0.36–0.46. Verification obligations unchanged (+32/fixture).

## Semantic distinction tests (12/12)

contact persistence ≠ contact identity · possession ≠ contact · ownership ≠ possession · effort ≠ force · force ≠ momentum · temporal order ≠ causality · visibility ≠ state persistence · identity ≠ physics continuity · expected ≠ observed · verification ≠ generation control · provider carrier ≠ canonical control · confidence ≠ scene state — each enforced via registry `forbidden_coercions` and asserted in `test_cpcs_typed_knowledge_coverage.py`.

## Baseline regression

Full application test discovery: **108/108 OK** (88 prior + 20 typed-coverage tests). Compiler/runtime/second_brain/verification/repo_control/release suites previously verified (299 OK); application suites re-verified this run. Control A untouched (no schema changes at all; registry is additive layer).

## Acceptance

`CPCS_TYPED_EXPANSION_ACCEPTANCE_v0.1.json`: **PASS** — all 28 computed gates true (D4 preserved, zero silent HARD drops, zero prose coercions, deterministic + idempotent mapping, temporal scope/requirement/evidence lineage preserved, provider boundary intact, trivial selectivity preserved, old + new tests pass, real-runtime replay pass).

## Remaining legitimate knowledge gaps

1. 25–32 controls per real fixture remain `unsupported_mappings`: they carry semantic meanings that have no typed repo-native family yet (research-governance, provider-projection hints, prose-only recommendations). Every one is surfaced with full lineage — safe, auditable, extensible.
2. Upstream activation breadth (trivial → 32 mandatory) remains untouched per TC-1 scope.
3. Registry families are authoring/planning typed; deeper per-family value sub-schemas (e.g., contact mode/geometry enums) remain a follow-up.

## LIVE A/B VIDEO GENERATION = YES

Structural readiness: yes — Treatment B now maps 59–64% of real-runtime controls into typed canonical structures with full lineage, and the A/B + repair paths compile through the existing compiler. **Live execution remains gated on provider credentials (VG-1) and authorization policy — neither is granted by this operation.**

## Recommended next operation

1. Provider credentials → VG-1 live → first traceable artifact.
2. First live A/B flight (reasoning_layer_ab) through the existing render/evaluation pipeline.
3. Optional: deepen registry value sub-schemas (contact mode/geometry enums, phase enums) to shrink the unsupported set further.

Not done: merge, push, promotion, paid generation, frozen-runtime modification, D4 weakening, provider-specific canonical fields.
