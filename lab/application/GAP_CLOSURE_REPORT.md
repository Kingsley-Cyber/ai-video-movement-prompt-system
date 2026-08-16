# GAP_CLOSURE_REPORT — Corpus-Aware Closure + Recruitment Optimization Sprint

Session target: strengthen corpus-aware reasoning — PASS 1 broad awareness,
PASS 2 focused recruitment, workflow tagging, metadata survival,
cross-domain emergence, evaluation-harness quality, and prompt retention +
placement (KA-2.1 / KA-2.2).

## 1. Gaps discovered

### P0 — correctness / semantic loss (FIXED)

- **P0-1 Production KA-2 wiring built an empty constellation.** The guided
  `_deliberate` pass passed the dict form of `translation.application_set`
  into `assemble_constellation`, whose `getattr(..., "applications")` lookup
  returned `[]` for dicts. Every guided session silently produced zero
  regions / zero recruitment. Fixed: `assemble_constellation` now accepts
  both the dataclass and dict forms.
- **P0-2 Evidence metadata never reached region facets.** `_deliberate`
  built `evidence_by_id` from `knowledge_activation_packet.retrieved_evidence`
  — a field that does not exist on the activation packet. Region facets lost
  every `failure_family_id` / `canonical_concept_id` / evidence `trigger_id`
  / `document_id`, degrading clustering AND recruitment binding. This is the
  same metadata-drop class the KA-2 holdout flagged. Fixed: `_deliberate`
  now builds the lookup from the treatment packet; `region_facets` unions
  evidence-level trigger/objective/doc identity into facets.

### P1 — materially weakens knowledge emergence (FIXED)

- **P1-1 Same-source vacuous trigger binding.** Region trigger facets were
  copied from the activation's own trigger vocabulary, so
  `trigger_entailment_bound` fired for every region (selectivity defect).
  Fixed: trigger binding now intersects evidence trigger vocabulary against
  the snapshot-side activated trigger vocabulary only.
- **P1-2 Same-source vacuous failure/objective binding.** Predicted failure
  families and objectives were derived from the same retrieved evidence as
  the region facets, so every control-capable region "bound" them and
  recruited. Fixed: intent-predicted failures (PASS-1 structured vocab +
  activation candidates) earn RECRUIT
  (`intent_predicted_failure_bound`); retrieval-only failure/objective
  overlap earns CONTEXT (`failure_contextual` / `objective_contextual`).
  Coverage-gap reporting now tracks intent-predicted failures.
- **P1-3 Single-linkage constellation chaining.** One shared vocabulary
  token merged packs into mega-regions (170 hermetic packs → 2 regions).
  Fixed: merge threshold raised to >= 2 shared facets. Hermetic slice now
  yields 36 regions for unseen intents. NOTE: the REAL frozen corpus still
  chains into 1 dense region (recorded below as remaining gap).

### P2 — optimization (partially addressed)

- **P2-1 Affordance-context CONTEXT flood.** `affordance_contextual` still
  marks ~29/36 hermetic regions CONTEXT because activation affordances are
  evidence-derived (same-source). Low harm (CONTEXT is reasoning-only),
  recorded as remaining P2.

## 2. What was built

- **`cpcs_knowledge_awareness.py` (PASS 1)** — `KnowledgeAwarenessProfile`
  with L0 universal considerations (ALWAYS_CONSIDER: evaluate, never force),
  L1 workflow tags (15 classes, deterministic token vocabularies,
  non-exclusive), L2 expertise tags (21 corpus-doc-provenanced families),
  intent signals (interaction / state-change / performance / perception /
  environment vocabularies), predicted failure families, uncertainties,
  content hash. Tags carry provenance (tag / level / source / corpus_doc_ids
  / evidence_tokens / lineage) and never gate retrieval.
- **`cpcs_knowledge_placement.py` (decomposition + placement)** —
  `decompose_atomic_units` derives INTERACTION_PHASE and EVENT units from
  typed structured objects only (D4-clean, adaptive — no prose); phase and
  causal ordering preserved. `build_placement` binds every region to
  scope (GLOBAL/INTERACTION/PHASE/BEAT), lifetime
  (PERSISTENT…RECOVERY_UNTIL_COMPLETE), placement role, and emission policy
  (NO_EMIT_REASONING_ONLY / NO_EMIT_VERIFICATION_ONLY / EMIT_GLOBAL /
  EMIT_SCOPED_MODULE). CONTEXT/ARCHIVE knowledge stays reasoning-only.
  `assemble_directing_modules` produces global vs beat-scoped module
  groupings with emission counts (anti-bloat: recruited ≠ emitted).
- **Recruitment workflow-tag support** — L2 tag → corpus doc IDs → region
  evidence binding; recruits only with the consequential intent signal
  (visible performance for FACS/gaze), else CONTEXT. Tags ADD evidence;
  never the sole reason.
- **Gap taxonomy** — `GAP_CLASSES` (10 classes: CORPUS_ABSENCE …
  VERIFICATION_GAP) attached to every coverage gap as `gap_class`; the
  system can now say WHERE knowledge was lost.
- **Evaluation harness (qualified, not a holdout)** —
  `KA2_CORPUS_SLICE_v0.1.json`: 170 real frozen-corpus records across 28
  documents, intent-independent selection policy (first-4-per-doc + risk
  records), content-hashed, no record prose. `FakeBackend(corpus_slice=True)`
  serves the slice with real structured metadata and corpus-native
  control projection for unseen intents. Default FakeBackend behavior is
  unchanged. The burned holdout is untouched.
- **Guided flow wiring** — awareness profile, evidence-backed constellation,
  tag-aware recruitment, placement, atomic units, and directing modules are
  attached to the deliberation dict and surfaced in the finish package
  (`knowledge_awareness`, `directing_modules`, plus existing
  `recruitment_refinement`).

## 3. PASS-1 / PASS-2 behavior

PASS 1 (breadth): deterministic workflow/expertise tagging over the intent
text + universal considerations + predicted failure families. Serum
diagnostic activates 6 workflow tags and 14 candidate expertise tags
including FACS/gaze/capture-realism/hand-object without any technical term
in the request. Product-only diagnostic activates product/visibility
candidates and excludes FACS/living-performance. "A calm empty frame."
yields an explicit AWARENESS_FAILURE_CANDIDATE uncertainty (honest).

PASS 2 (selectivity): recruitment differentiates intent-predicted signals
(RECRUIT) from same-source retrieval overlap (CONTEXT) and archives
peripheral evidence. Hermetic matrix (WORKFLOW_RECRUITMENT_MATRIX.json):
UGC serum R=10/C=20/A=6 with 8 bounded prerequisites; product-only R=0;
generic video R=0/C=29/A=7 with 13 typed coverage gaps. Emission stays
tight: recruited regions emit scoped modules only when atomic units exist;
CONTEXT/ARCHIVE never emit.

## 4. Prompt retention + placement

- **Pre-fix survival chain:** evidence → packs → regions → dispositions →
  refinement → finish package. Loss points found: P0-1 (empty constellation
  in production) and P0-2 (evidence metadata dropped before facets).
- **Post-fix chain:** evidence → packs (facet-complete) → regions →
  dispositions → refinement → atomic units → scope/lifetime placement →
  emission policy → directing modules → finish package
  (`directing_modules` + `knowledge_awareness`).
- **Decomposition behavior:** interaction phases become units when the
  structured payload carries them (hip-toss fixture: 4 phase units);
  otherwise only event units. Adaptive — no forced universal atomization.
- **Combat diagnostic (hip toss, fixture-backed):** INTERACTION_MECHANICS /
  RECOVERY roles with CONTACT_INTERVAL / RECOVERY_UNTIL_COMPLETE lifetimes;
  at least one EMIT_SCOPED_MODULE. Water-swing diagnostic (no fixture):
  honest zero units, global reasoning-only emission.
- **UGC diagnostic (hermetic slice):** 3 event units, 10 recruited regions
  via tag+performance support, 8 prerequisites discovered; no fabricated
  FACS prompt text.
- **Negative product-only diagnostic:** FACS stays non-recruited and
  reasoning-only.
- **Prompt-bloat measurements:** emitted modules (scoped+global) ≤ recruited
  regions everywhere; matrix records reasoning_only/verification_only/
  emission counts per workflow.

## 5. Metadata survival findings

- `canonical_concept_ids`, evidence `trigger_ids`/`objective_ids`,
  `failure_family_ids`, `document_id`, `universal_type`,
  `epistemic_status` now survive record → evidence → pack → region →
  disposition → placement (region `corpus_doc_ids` facet added for
  tag-to-evidence binding).
- Remaining drop point (recorded): real-runtime evidence still lacks
  `objective_ids` projection in FrozenRuntimeBackend (projection carries
  universal_type / epistemic_state / canonical_concept_ids; objectives are
  derivable from the same record's semantic linkage — add in a follow-up
  if objective binding becomes load-bearing again).

## 6. Harness qualification state

- Hermetic harness: QUALIFIED for pipeline mechanics on unseen intents
  (corpus-slice substrate, intent-independent, hashed).
- Independent evaluation: NOT performed this session. No 9/10 claim. The
  burned KA-2 holdout remains untouched.

## 7. Remaining gaps (deferred)

- **P2-1 affordance CONTEXT flood** (reasoning-only, low harm).
- **P2 real-corpus constellation separation**: the dense frozen corpus still
  chains into one mega-region at threshold >= 2; next step is weighted facet
  matching or seeded clustering (e.g., principle-family seeds + failure
  refinement). DEV-based tuning only.
- **P2 real-runtime objective_ids projection** (see §5).
- **OWNER_DECISION_REQUIRED**: whether atomic-unit/module structure should
  eventually feed a reviewed carrier-serialization change (Control A frozen;
  currently presentation-only, additive to the guided package).

## 8. Tests

New: test_ka2_awareness (12), test_ka2_placement (9), test_ka2_harness (5).
Full application suite: 305 tests OK (was 235). KA-1/KA-2/pre-KA regression
groups green. Real-runtime end-to-end probe: fight intent → awareness tags
(ACTION/FIGHT/ENVIRONMENT) → 100 records → RECRUIT → refinement → 6 atomic
units → placement → modules, with 19 typed coverage gaps
(CORPUS_ABSENCE + RETRIEVAL_COVERAGE_GAP).
