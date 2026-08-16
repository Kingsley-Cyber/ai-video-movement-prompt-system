# KA-1 CURRENT STATE

Last updated: 2026-08-15 (context handoff session)

Repository: /Users/king/cpcs-reasoning-ab
Branch: experiment/cpcs-reasoning-layer
HEAD: 29b0320

Previous qualified CPCS release lineage: ae19498 -> 83fe496 -> 1926874 -> 29b0320

## A. CPCS BEFORE KA-1

The following architecture is already release-qualified (CPCS_V1_RELEASE_QUALIFIED,
CPCS_BOOTSTRAP_READY). Do NOT rebuild any of it:

- CPCS v1 guided product (PC-1): guided/FAST/AUTO completion, session/revision
  with immutable history and targeted invalidation, authority order, blocking
  fail-closed. Release-qualified.
- BOOT-1: idempotent `cpcs.bootstrap` + doctor; runtime resolved from argument >
  local config > env; secret-free 0600 config.
- DR-1 deliberation: observations, KnowledgeActivationPacket, 16 hypothesis
  types with competition, query steering, bounded prerequisite/cascade
  reasoning, ReasoningClosurePacket. Qualified.
- TC-1/TC-2 typed knowledge mapping: 19-family path registry
  (`lab/compiler/cpcs_typed.py`), 12 structured constructors, deterministic
  control-type admission, residual semantic closure (executable coverage 1.0,
  HARD 1.0). Qualified.
- EC-1 execution contracts / EC-2 provider projection / CP-1 capability
  resolution / VG-0 execution gate: frozen in the external frozen runtime.
- Retrieval (lanes, hard gate, requirement-local ranking, coverage merge) is
  FROZEN and closed.
- D4 is frozen: no flat-text evidence admission; evidence by ID only.
- Control A (existing compiler/reasoning defaults) is frozen;
  CURRENT_BASELINE remains the default.
- CanonicalScore is the semantic authority (score_id integrity enforced by the
  compiler; post-resolution mutation is forbidden).
- MCP transport exists (`bin/cpcs-mcp`, 33+ tools, auto-exposed via service
  `_register`).
- Provider generation is optional / NOT CONFIGURED and is not part of KA-1.

Relevant flow (with the KA-1 boundary marked):

```
User Intent
    ->
Guided/DR-1
    ->
Knowledge Activation
    ->
Hypotheses
    ->
Query Steering
    ->
Retrieval Evidence
    ->
[KA-1 MISSING/NEW BOUNDARY: Knowledge Application Bridge]
    ->
TreatmentAdapter / Typed Mapping
    ->
CanonicalScore
    ->
Prompt/package projections
```

## B. WHY KA-1 EXISTS

The corpus already contains rich research on: motion, contact, support,
continuous combat state, hand/object manipulation, state transitions,
biomechanics, world interaction, living-performance realism, capture realism,
UGC-relevant realism. The problem is NOT lack of research. The problem is
research APPLICATION: retrieval returns evidence and DR-1 reasons about what
to investigate, but there is no first-class object binding

```
PRINCIPLE -> MECHANISM -> FAILURE RISK -> INTENT APPLICATION -> REPRESENTATION DECISION
```

before deterministic typed mapping. Rich knowledge therefore collapses into
generic controls.

Motivating water-duel defect (real, from the user's generation runs):
- combat generation improved after retries; typed contacts, trajectories,
  Laban, support constraints appeared;
- but world response / recovery / consequence reasoning remained weak;
- the hip-toss beat once made BOTH actors somersault (mirrored rotation) —
  a support_contact_sequence + rotation-axis representation failure;
- global physics prose was insufficient (a longer global essay made the
  second pass WORSE because it never became beat-scoped structured knowledge);
- the research already contained the relevant causal concepts (contact state
  transitions, phase model, support states).

Broader requirement: KA-1 MUST be corpus/domain-general. It must support the
same mechanism for combat, UGC/ecommerce, object manipulation, cooking,
living-performance realism, product identity, hand/object handling,
material/surface response, capture realism. KA-1 is NOT a combat subsystem.

## C. KA-1 ARCHITECTURAL DECISION

Accepted design:

```
DR-1 -> Knowledge Application Bridge -> TreatmentAdapter / Typed Mapping -> CanonicalScore
```

New module: `lab/application/cpcs_knowledge_application.py`

Core objects:

- **PrinciplePack**: {principle, mechanism, failure_risk, evidence_ids,
  intent_application, source_records, pack_id, pack_hash, lineage}. Binds one
  research principle to its mechanism, predicted failure, and evidence as ONE
  reasoning unit. Evidence referenced by ID only (D4).
- **RepresentationDecision**: {decision, rationale, authority, target_family,
  forbidden_coercions, verification_counterpart, decision_hash}. The most
  important missing piece: knowledge does not always become a control.
  Decision enum: CONTROL | VERIFICATION | PLANNING | NON_EXECUTABLE | COMPOSITE.
- **KnowledgeApplicationSet**: ordered (PrinciplePack + RepresentationDecision)
  pairs with competition groups, unknowns, lineage, set_hash. Bridge output,
  typed-mapping input.

Responsibility split (do not collapse):

- Retrieval: "What evidence exists?"
- DR-1: "What should CPCS reason about and what knowledge is still needed?"
- KA-1: "How does retrieved knowledge apply to THIS creative intent?"
- Typed Mapping: "What canonical representation should the resolved
  application become?"
- Presentation/compiler: "How is the canonical meaning projected downstream?"

## D. FROZEN BOUNDARIES

- retrieval/ranking/gating frozen runtime
- Control A (build.py / score.py semantics; CURRENT_BASELINE default)
- D4 (no flat-text evidence coercion)
- authority order:
  USER_EXPLICIT > USER_CORRECTION > CPCS_HARD_REQUIREMENT >
  CPCS_SAFE_INFERENCE > CPCS_GROUNDED_RECOMMENDATION >
  EXISTING_BASELINE_DEFAULT > LEAVE_UNSPECIFIED
- post-resolution score immutability (score_id integrity)
- MCP transport contract
- provider boundary (carriers are not canonical controls)
- TC-1/TC-2 distinctions:
  contact persistence != contact identity
  force != effort != momentum
  temporal != causal
  expected != observed
  verification != generation control
  provider carrier != canonical control
  confidence != scene state

## E. KA-1 WORK PACKAGE MAP

WP-1..WP-9 are specified in:

- `lab/application/KA1_WORKPACKAGES/00_MASTER_BRIEF.md` (authority)
- `lab/application/KA1_WORKPACKAGES/DEPENDENCIES.md` (wave map + file ownership)

Summary (see those files for full specs):
WP-1 schemas/contracts · WP-2 principle engine · WP-3 representation engine ·
WP-4 application set · WP-5 adapter integration · WP-6 structured interaction
payload · WP-7 cross-domain fixtures + real-runtime smoke · WP-8 MCP inspect +
doctor line · WP-9 acceptance/commit.

## F. ACTUAL IMPLEMENTATION STATUS

WP-1 — NOT_STARTED
WP-2 — NOT_STARTED
WP-3 — NOT_STARTED
WP-4 — NOT_STARTED
WP-5 — NOT_STARTED
WP-6 — NOT_STARTED
WP-7 — NOT_STARTED
WP-8 — NOT_STARTED
WP-9 — NOT_STARTED

The KA1_WORKPACKAGES markdown files are PLANS. No KA-1 production code, schemas,
or tests exist yet. `lab/application/cpcs_knowledge_application.py` does NOT
exist.

Related but NOT KA-1 (pre-KA work, uncommitted):
- `lab/application/reasoning_treatment.py` has an uncommitted fix to
  `handler_repair_plan` (stops post-resolution score mutation; moves
  verification_obligations/typed_controls/structured_objects alongside the
  revised build request). This belongs to the RC-1 repair path, not KA-1.
  It was the fix for the water-duel repair demo.
- `lab/application/CPCS_V1_ARCHITECTURE_BRIEFING.md` (untracked): the
  architecture briefing that motivated KA-1.

## G. CURRENT ARCHITECTURAL QUESTIONS / RISKS

1. Uncommitted repair-handler fix (see F): should be committed before or with
   KA-1 work — decide at first commit.
2. WP-6 requires source-native values only (enums); if the frozen corpus does
   not carry a needed enum, the field stays None — do NOT invent values.
3. Real-runtime smoke tests are slow (~1-2 min per deliberation); keep them
   env-gated with skipUnless.
4. `CPCS_BOOTSTRAP_CONFIG_OVERRIDE` env knob exists for config isolation in
   tests (documented in bootstrap contract).

## H. EXACT NEXT SAFE ACTION

KA-1 implementation has not begun. Start WP-1 and WP-6 in parallel according to
the work-package dependency map (Wave 1). Before writing code, commit or
explicitly preserve the uncommitted `reasoning_treatment.py` repair fix.
