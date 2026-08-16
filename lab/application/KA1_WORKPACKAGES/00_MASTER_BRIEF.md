# KA-1 — Knowledge Application Bridge: Master Brief

Read this first. It is the single source of truth for all KA-1 work packages (WP).

## 1. What we are building

The missing block between DR-1 deliberation and typed mapping:

```
DR-1 (reason about request + find evidence)
        |
        v
KNOWLEDGE APPLICATION BRIDGE   <-- NEW (cpcs_knowledge_application.py)
        |
        v
Typed Mapping (TreatmentAdapter)
        |
        v
Canonical Score -> Prompt carriers
```

The bridge converts retrieved research into **intent-conditioned reasoning
objects** BEFORE control compilation. It answers: "How does this knowledge
transform the solution?" — not "what documents exist" (retrieval) and not "what
conclusions follow" (reasoning).

## 2. Core objects

- **PrinciplePack**: {principle, mechanism, failure_risk, evidence_ids,
  intent_application, source_records}. Binds one research principle to its
  mechanism, its predicted failure, and its evidence — as ONE reasoning unit.
- **RepresentationDecision**: {knowledge_id, decision: CONTROL | VERIFICATION |
  PLANNING | NON_EXECUTABLE | COMPOSITE, rationale, authority, target_family,
  forbidden_coercions}. The most important missing piece: knowledge does not
  always become a control.
- **KnowledgeApplicationSet**: ordered collection of (PrinciplePack +
  RepresentationDecision) with competition/alternatives, unknowns, lineage, hash.
  Output of the bridge, input to the typed mapper.

Example chain (ecommerce):

```
Principle:   "Objects maintain identity through manipulation."
Mechanism:   "Camera needs uninterrupted visibility of defining features."
Creative implication: "Rotate product while maintaining logo visibility."
Canonical control:    object.identity_visibility = maintained
```

## 3. Where each piece lives

- `lab/application/cpcs_knowledge_application.py` — NEW engine module
  (KnowledgeApplicationEngine, PrinciplePack, RepresentationDecision,
  CreativeApplication). Deterministic; no LLM required; D4 enforced.
- `lab/application/reasoning_treatment.py` — MODIFY ONE PASS ONLY:
  `Treatment Packet -> KnowledgeApplicationSet -> Typed Controls`.
  Existing paths must remain intact (old tests keep passing).
- `lab/compiler/cpcs_typed.py` — ADDITIVELY extend the interaction constructor
  payload (roles, phases, force vector, rotation axis, support states,
  recovery) using source-native enums. No existing entry changes semantics.
- Schemas/contracts land in `lab/application/` as `CPCS_*_v0.1.json`.
- Tests land in `lab/application/tests/test_ka1_*.py`.

## 4. Frozen boundaries (DO NOT TOUCH — release blocker if violated)

- Frozen CPCS runtime (retrieval, ranking, gate) — read only via
  `FrozenRuntimeBackend`.
- Control A: `lab/compiler/build.py`, `lab/compiler/score.py` semantics,
  CURRENT_BASELINE default.
- D4: no flat-text evidence admission; evidence referenced by ID only;
  unsupported prose stays explicitly dispositioned.
- MCP transport contract (`lab/application/mcp.py`); add ops only via
  `_register` in `service.py`.
- Authority order: USER_EXPLICIT > USER_CORRECTION > CPCS_HARD_REQUIREMENT >
  CPCS_SAFE_INFERENCE > CPCS_GROUNDED_RECOMMENDATION > EXISTING_BASELINE_DEFAULT
  > LEAVE_UNSPECIFIED.
- Canonical score authority: never mutate a resolved score post-resolution
  (score_id integrity).
- TC-1/TC-2 distinctions (contact persistence ≠ contact identity, force ≠
  effort ≠ momentum, temporal ≠ causal, expected ≠ observed, verification ≠
  generation control, provider carrier ≠ canonical control, confidence ≠ scene
  state).

## 5. Environment

- Worktree: `/Users/king/cpcs-reasoning-ab` (branch
  `experiment/cpcs-reasoning-layer`, HEAD `29b0320`).
- Frozen runtime: `export CPCS_FROZEN_RUNTIME_PATH=/Users/king/Downloads/Additional/Runtime`
  (real-runtime tests; hermetic tests run WITHOUT it and use `FakeBackend`).
- Run tests: `python3 -m unittest lab.application.tests.test_ka1_xxx -q`
  (repo uses unittest, not pytest).
- Run from repo root. `PYTHONPATH` is handled by running from root.
- Existing suites to re-run after any change:
  `python3 -m unittest lab.application.tests.test_reasoning_treatment_surface
  lab.application.tests.test_cpcs_typed_knowledge_coverage
  lab.application.tests.test_tc2_residual_closure
  lab.application.tests.test_deliberation_surface
  lab.application.tests.test_guided_product_surface -q`

## 6. Conventions

- Deterministic: same inputs -> same outputs (stable hashes, sorted
  collections, no set-iteration order dependence).
- Every object carries `lineage` (requirement_ids, evidence_ids, epistemic
  status) and a content hash.
- No prose synthesis into canonical values: principle/mechanism text uses
  structured templates over structured fields; user-facing phrasing is
  presentation only (compression groups pattern).
- Artifacts are computed, never hand-authored numbers.
- Follow existing repo style (no gratuitous comments, JSON artifacts with
  artifact/version keys).

## 7. Definition of Done (whole KA-1)

1. Bridge operational for 3 cross-domain fixtures: combat hip toss, ecommerce
   watch unbox, cooking tomato slice.
2. Hip-toss canonical output contains: contact interval, support state, causal
   phases, actor roles, force transfer, precondition/postcondition, recovery.
   **Any output with only action labels (no state transitions) FAILS.**
3. All old suites pass; Control A unchanged; D4 preserved.
4. Acceptance `CPCS_KA1_ACCEPTANCE_v0.1.json` = PASS (computed).
5. One release commit on `experiment/cpcs-reasoning-layer`; push; no merge.
