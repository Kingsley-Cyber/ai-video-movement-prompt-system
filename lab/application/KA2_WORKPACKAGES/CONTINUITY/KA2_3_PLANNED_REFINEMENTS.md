# KA-2.3 PLANNED REFINEMENTS — Source-Corpus Alignment Addition

STATUS: **PLANNED / HYPOTHESES ONLY — nothing here is implemented.**
This file is the frozen design record for the next work stage. Do not treat
any claim below as a finding; treat it as an audit expectation to be
verified against the frozen corpus metadata.

Execution order is LOCKED (see §6). No implementation of these refinements
before the policy-neutral merge instrumentation and the committed
PRE-POLICY real-runtime 11-workflow sweep.

---

## 1. Source-corpus knowledge space (audit expectations, NOT recruitment outputs)

The owner recovered 27 completed research-document summaries. They indicate
CPCS's knowledge space is substantially broader than movement. These are
AUDIT EXPECTATIONS: the actual frozen records' structured metadata must
justify discoverability. Do not create new research categories from this
summary alone.

### 1. UNIVERSAL
world/state continuity · causality · identity · temporal organization ·
attention/readability · verification · provider/compiler realization

### 2. MOTION
biomechanics · support/balance · contact · force/momentum · phase grammar ·
Laban · Bartenieff · motion continuity

### 3. PERFORMANCE
FACS · affect/display distinction · gaze · aliveness · motor initiation ·
emphasis · asymmetry · dialogue embodiment · performance register

### 4. INTERACTION
hands · grip · contact persistence · ownership · bimanual interaction ·
articulated/deformable object state · causal action transition

### 5. WORLD/MATERIAL
environment state · collision · drag/friction · water · material
deformation · surface response

### 6. CAPTURE
device/optics · handheld behavior · AF/AE/WB · sensor behavior · light ·
texture/surface realism

### 7. CINEMATOGRAPHY
screen direction · camera motivation · target visibility · attention ·
composition · edit motivation · volumetric continuity

### 8. FORMAT/COMPILER
canonical authority · carrier selection · ControlScope · ControlLifetime ·
capability ladder · compilation loss · semantic equivalence

### Cross-cutting participation requirement

A source/expertise family must NOT be permanently assigned to one video
type. The same hand-contact knowledge may apply to fight, UGC product demo,
cooking, articulated-object manipulation. The same FACS/performance
knowledge may apply to UGC, dialogue, acting, testimonial, narrative
performance. Workflow tags must remain MANY-TO-MANY activation hints.

---

## 2. Five-view knowledge model

Fits the existing architecture without a new subsystem:

- WORKFLOW — "What type(s) of production problem am I solving?"
  (existing L1 tags)
- EXPERTISE — "What specialist knowledge might help?" (existing L2 tags)
- MECHANISM — "What process/state-changing mechanism is actually
  occurring?" (derived; see §2C)
- FAILURE — "What known failure families are consequential?" (a VIEW over
  existing failure_family_ids; see §2B)
- APPLICATION — "Where, when and how does the resulting knowledge apply?"
  (existing KA-2.2 placement/scope decisions)

All views stay many-to-many.

### 2B. FAILURE view — NOT a new tag authority

FAILURE remains a recruitment/diagnostic view over the existing
`failure_family_ids` and related frozen structured signals. Existing
failure IDs remain authoritative. Do not create a second independently
assigned failure taxonomy.

### 2C. MECHANISM view — provenance discipline

Mechanism tags may derive from `mechanism_tokens` and other structured
evidence, but `canonical_concept_ids` are NOT automatically mechanism IDs
(a canonical concept can be broader than a mechanism). Every derived
mechanism tag must record:
- origin field (exactly which structured field justified it)
- source record IDs
- derivation rule
- lineage

Do not flatten concept == mechanism.

---

## 3. Event-aware PASS 1 (highest immediate value, highest misuse risk)

Current whole-request bag-of-signals recognizes "UGC skincare video" but
misses internal semantic structure. Target example:

pick up → acquisition/ownership · turn bottle toward camera →
orientation/product identity/visibility · unscrew → articulated state
transition/bimanual manipulation · draw serum → liquid/object state ·
dispense → material transfer · apply to cheek → contact/surface
interaction · notice texture → sensory appraisal · react → living
performance/FACS/gaze · speak → dialogue embodiment · final reveal →
product identity/camera readability.

Proto-events also give the placement layer natural atomic boundaries: one
improvement strengthens BOTH PASS 1 awareness and atomic placement.

### 3A. NOT a raw keyword router

DO NOT implement `"unscrews" -> ARTICULATED_OBJECT` or
`"smiles" -> FACS`. Instead deterministically derive a structured
proto-event / state-change representation where possible:

```
text span
  ↓
actor / predicate / patient
  ↓
state-change candidate (before-state → after-state)
  ↓
interaction class (hand_object, object_object, actor_environment, …)
  ↓
contact/ownership implications
  ↓
visible consequence
  ↓
candidate mechanism/expertise signals (corpus-supported metadata)
```

Phrase/token matches are evidence for event DETECTION only; they may not
become canonical expertise truth by themselves.

---

## 4. Universal-consideration verdicts

ALWAYS_CONSIDER is meaningful only if something eventually says "I
considered this and determined whether it matters here." For each
universal consideration, produce:

```
consideration: causal_coherence
verdict: CONSEQUENTIAL | NOT_CONSEQUENTIAL | UNRESOLVED
reason_codes: [...]
evidence_ids: [...]
```

with explicit COVERAGE_GAP preserved separately where applicable. NEVER
interpret lack of evidence as irrelevance (UNRESOLVED, not
NOT_CONSEQUENTIAL).

---

## 5. Source provenance at constellation level

ExpertiseRegion diagnostics must retain document/source-package provenance
alongside atomic evidence IDs, so the sweep and any later holdout can
answer:

- which research packages contributed?
- which canonical concepts?
- which mechanisms?
- which failures/objectives/requirements?
- which workflow/application scopes?

Source names are DIAGNOSTIC LINEAGE, not generation-facing prompt content.
Do not surface source-document names to the generation model unless needed.

---

## 6. LOCKED execution order

1. Policy-neutral merge instrumentation (record per-region merge facets,
   member counts, facet unions; per-edge kind — strong vs bridge).
2. Commit the PRE-POLICY real-runtime 11-workflow sweep
   (WORKFLOW_RECRUITMENT_MATRIX_REAL_v0.1.json).
3. Inspect what actually happens (region counts/sizes, merge causes,
   bridge density, dispositions, prereqs, gaps, placement counts;
   determine whether the mega-region is universal or workflow-specific).
4. Implement, ONLY where evidence supports need:
   - KA-2.3 weighted expertise-region separation (strong facet merge vs
     weak bridge edge; INTRA-REGION relation vs INTER-REGION bridge)
   - event-aware PASS 1 (proto-event derivation)
   - five-view tag refinement
   - universal-consideration verdicts
5. Run the POST-POLICY sweep; compare against the pre-policy baseline.
6. Freeze policy (stop dev tuning before any holdout authoring).
7. Regression + DEV evaluation.
8. Independent holdout creation by a SEPARATE process/session (never the
   implementation session), sealed commitment, one-shot real-runtime
   scoring, with metrics at least: unstated-expertise emergence,
   selectivity, region quality, prerequisite recall, placement accuracy,
   prompt economy, coverage-gap honesty.

Carrier serialization remains DEFERRED (OWNER_DECISION_REQUIRED). No new
research. No retrieval changes. No Control A changes. No holdout reuse.

---

## 7. Prior-session context (verified state at handoff)

- HEAD at handoff: 87e9e64 (feat(cpcs): add corpus-aware closure and
  placement (KA-2.1/KA-2.2)); clean worktree.
- KA-2.1/KA-2.2 shipped: cpcs_knowledge_awareness.py,
  cpcs_knowledge_placement.py, gap taxonomy, KA2_CORPUS_SLICE_v0.1.json
  harness, WORKFLOW_RECRUITMENT_MATRIX.json (hermetic), GAP_CLOSURE_REPORT.md.
- Known P0/P1 fixes landed: production constellation empty-dict fix,
  evidence-metadata survival fix, same-source vacuity fixes, merge
  threshold >= 2.
- Known remaining (documented): real-corpus mega-region chaining,
  affordance-CONTEXT flood (P2), real-runtime objective_ids projection (P2).
- Qualification status: DEV_ONLY_PASS_INDEPENDENT_QUALIFICATION_PENDING.

---

## 8. EXECUTION LOG (updated after steps 1-4 partial)

- STEP 1 DONE (870aae7): policy-neutral merge instrumentation —
  per-region merge evidence (strong/weak facet breakdowns), typed
  inter-region bridges with strength, merge-policy snapshot, orphan
  flags. Hash-neutral (constellation_hash/region_hash unchanged).
  8 instrumentation tests.
- STEP 2 DONE (ffa733a): PRE-POLICY real-runtime 11-workflow sweep —
  immutable baseline WORKFLOW_RECRUITMENT_MATRIX_REAL_v0.1.json
  (content-hashed, refuse-to-overwrite).
- STEP 3 DONE: inspection finding — every workflow collapsed to ONE
  mega-region (~100 packs, 0 bridges). Weak facets drove the chain:
  trigger_ids in 99/99 joins, objective_ids 99/99.
- STEP 4 PARTIAL (198dfc3): policy v2 shipped — merge requires strong
  facet overlap >= 2; weak facets become bridges only. POST-POLICY
  sweep: 1 mega-region -> 2-4 regions per workflow (improvement, not
  the target constellation).
- DECISIVE FINDING for the next step: the frozen semantic linkage
  attributes concepts/failures/requirements densely ACROSS the
  retrieved window (query-relevant by construction):
  - requirement overlap per join: 60-69/99 (query attribution)
  - 1,354/1,485 cross-(family x doc) group pairs share >= 2 concepts
  - the healthy shape comes ONLY from (principle_family x document)
    grouping: 48-58 regions with sizes 3-6 (measured for FIGHT/UGC/
    DRONE)
  Therefore no facet-overlap threshold over the linkage fields can
  reach the target separation. Policy v3 (next session, NOT yet
  implemented): document-seeded clustering (principle_family x
  document seeds), requirement overlap demoted to bridge-only
  (query-attributed by construction), cross-seed merge ONLY on
  discriminative concept evidence (concept co-occurrence that is
  specific to the shared document pair — computable from the two
  committed sweep artifacts).
- STEPS 5-8 remain: post-v3 sweep, freeze, regression/DEV, independent
  holdout.
