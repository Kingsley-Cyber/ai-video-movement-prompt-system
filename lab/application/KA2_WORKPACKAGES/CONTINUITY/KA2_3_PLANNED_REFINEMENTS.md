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

---

## 9. EXECUTION LOG — policy v3 + semantic quality audit (this session)

- v3 SHIPPED: document-seeded separation
  (seeds = principle_family x corpus_doc_ids; same-family near-duplicate
  docset collapse at Jaccard >= 0.5 + shared failures; cross-seed merge
  requires shared failures + concept Jaccard >= 0.5 + >= 2 shared
  concepts; requirement overlap NEVER merges — bridge only). Weak-only
  overlap and requirement-only overlap stay separate regions (tested).
- SEMANTIC QUALITY AUDIT (real frozen runtime, KA2_3_REGION_QUALITY_
  AUDIT_v0.1.json, content-hashed): FIGHT 8 regions (90/2/2/2/1/1/1/1),
  UGC_SERUM 9 (83/4/3/2/2/2/2/1/1), DRONE 9 (90/3/1x7). Bridges 28-36.
- AUDIT VERDICT: FREEZE NOT REACHED. Owner quality criteria:
  1) coherence: FAIL for the dominant 83-90-pack region (18-19 docs, all
     families, all failure families, empty mechanism tokens);
  2) distinct expertise incorrectly merged: YES — the dominant compound;
  3) same-mechanism fragmentation: minor/none observed;
  4) bridges preserve relationships: partial (kinds are structural only);
  5) recruitment selective: NO — all regions RECRUIT (0 CONTEXT/ARCHIVE);
  6) placement precise: partial — small regions place correctly
     (UGC FF-PERFORMANCE singleton -> PERFORMANCE_DIRECTION;
     protected_invariant -> GLOBAL_INVARIANT; mechanism_binding ->
     INTERACTION_MECHANICS), the compound stays REASONING_ONLY.
- ROOT CAUSE (evidenced): ~80% of real-corpus packs carry KA-1
  principle_family `evidence_binding` (Concept/Schema/Definition/Claim/
  Finding/... all map to one catch-all in build_principle_packs), so
  family x document seeding cannot separate the dominant record class
  and docset-collapse chains it into one compound. The merge policy is
  no longer the binding constraint; the KA-1 family VOCABULARY for
  non-executable classes is.
- OWNER_DECISION_REQUIRED (next step): refine KA-1 `_principle_family`
  for non-executable universal types into corpus-grounded families
  (e.g., conceptual_foundation, schema_guidance, evidence_interpretation,
  recommendation_guidance, ...) WITHOUT changing executable-class
  mappings — then re-run the audit. This touches KA-1 vocabulary (not
  its architecture); the owner's explicit approval gates it.
- Freeze remains NOT reached; holdout process not started.

---

## 10. EXECUTION LOG — KA-1.1 principle vocabulary resolution (approved stage)

- KA-1.1 DONE (this session): role-based family vocabulary derived from
  the frozen TC-2 disposition ledger. Census: evidence_binding 68% ->
  0; 15 families; largest conceptual_foundation 37%. Rule/Requirement
  join protected_invariant. `Evidence` handled by family-level
  supplement (ledger untouched). Artifacts: KA1_1_PRINCIPLE_FAMILY_
  CENSUS_BEFORE/AFTER_v0.1.json, KA1_1_PRINCIPLE_FAMILY_POLICY_v0.1.json,
  KA1_1_PRINCIPLE_VOCABULARY_REPORT.md.
- POST-KA1.1 audit (same KA-2.3 policy): dominant compound persists
  (FIGHT 86 / UGC 78 / DRONE 87 packs). Critical acceptance FAILS.
- DECISIVE pure-seed diagnostic (probe only, thresholds restored):
  74 regions, largest 5 — the seed structure is healthy; the compound
  is manufactured by the v3 cross-seed merge criteria chaining on the
  dense query-wide linkage (few package-level concepts, near-universal
  shared failures across the window).
- NEXT (OWNER_DECISION_REQUIRED, KA-2.3.1): replace broad-window concept
  Jaccard with concept document-frequency discriminativeness, or disable
  cross-seed merge until such evidence exists. Seeds alone meet the
  target shape. No clustering policy changed during KA-1.1.

---

## 11. EXECUTION LOG — KA-2.3.1 seed-preserving network (approved stage)

- POLICY SHIPPED (this session): cross-seed merge DISABLED BY DEFAULT
  (policy ka2.3.1-seed-preserving-network); docset collapse disabled;
  seeds = (principle_family x corpus_doc_ids) are region identity.
  Bridge kinds renamed per owner vocabulary (shared_concept,
  shared_document_relation). Cross-seed overlap is bridge evidence only:
  requirement/failure/concept/trigger/objective overlap never merges.
- REGION QUALITY AUDIT (real runtime): FIGHT 74 regions / largest 5;
  UGC_SERUM 69 / 5; DRONE 73 / 5. NO MEGA-REGION anywhere.
- 11-WORKFLOW SWEEP: 63-82 regions per workflow, max size 4-7, bridges
  1.9K-3.3K typed edges (shared_failure_family + shared_requirement
  dominant — linkage density now visible as edges, not merges).
  Prompt economy preserved: global_emit 4-11, reasoning_only 55-70.
- ACCEPTANCE: criteria 1,2,3,6,7 PASS. Criterion 4 (selective
  recruitment) FAILS — all regions RECRUIT (0 CONTEXT/ARCHIVE) in every
  workflow. Classified RECRUITMENT_FAILURE with evidenced root cause:
  the snapshot trigger vocabulary IS the corpus trigger vocabulary
  (TRIG-* drawn from the same frozen corpus), so
  trigger_entailment_bound fires on 74/74 regions (same-source
  vacuity at real-runtime scale); mandatory-requirement binding adds
  density (34 candidate requirements, query-attributed).
- FREEZE: NOT REACHED. Region identity is final for now; recruitment
  selectivity is the named next problem. No re-merging.
- NEXT (OWNER_DECISION_REQUIRED, KA-2 PASS-2 refinement): demote
  trigger_entailment_bound to CONTEXT-grade or require consequence
  (intent-predicted failure bound OR control-decision presence), and
  rank/cap RECRUIT so the constellation recruits a SUBSET. Evidence is
  in WORKFLOW_RECRUITMENT_MATRIX_REAL_POST_KA231_v0.1.json and
  KA2_3_REGION_QUALITY_AUDIT_POST_KA231_v0.1.json.

---

## 12. EXECUTION LOG — KA-2.4 consequence-graded recruitment (approved stage)

- RECRUITMENT_FAILURE FIXED (this session): trigger_entailment_bound
  demoted to trigger_contextual; workflow-tag support and prerequisite
  promotion require an executable/verification surface; requirement
  binding requires intent-predicted failure binding or hard-constraint
  family; awareness separates token-derived vs activation-derived
  failures (same-source leak fixed). Latent set|list bug fixed in the
  dependency-consequence path.
- RESULT (real runtime, 11 workflows): RECRUIT 7-19 of 63-82 regions,
  CONTEXT 54-70, no mega-region, prompt economy intact.
- FREEZE REACHED: KA-2.3 region identity (seed-preserving network) and
  KA-2.4 recruitment policy are FROZEN (markers in MERGE_POLICY_SNAPSHOT
  and RECRUITMENT_POLICY_SNAPSHOT).
- DOCUMENTED RESIDUAL: DRONE ~6 camera-failure-bound compound seeds
  labeled PERFORMANCE_DIRECTION (pack-level document mixing; fixed by
  the real-runtime structured-interaction layer, not by more tuning).
- NEXT: see KA2_4_CLOSURE_PATH.md (layer 2 real-runtime structured
  interaction -> owner decision; layer 3 temporal director -> new
  subsystem; layer 4 provider serialization -> deferred). Holdout
  preparation must happen in a SEPARATE session.
