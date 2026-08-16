# KA-2 IMPLEMENTATION LEDGER

| WP | Status | Production files | Test files | Tests run | Result | Commit |
|----|--------|------------------|------------|-----------|--------|--------|
| WP-1 | DONE | cpcs_knowledge_constellation.py (ExpertiseRegion, KnowledgeConstellation, assemble_constellation) | test_ka2_constellation.py | 8 | PASS | ecb89c6 |
| WP-2 | DONE | cpcs_knowledge_recruitment.py (RecruitmentDisposition, recruit_for_intent, dependency_consequence) | test_ka2_recruitment.py | 9 | PASS | ecb89c6 |
| WP-3 | DONE | cpcs_knowledge_refinement.py (assess_prerequisites, build_refinement_packet, apply_to_closure), cpcs_guided_handlers.py _deliberate additive fill, reasoning_treatment.py FrozenRuntimeBackend evidence projection (canonical_concept_ids additive) | test_ka2_refinement.py | 9 | PASS | ecb89c6 |
| WP-4 | DONE | KA2_EVAL_DEV_v0.1.json, KA2_EVAL_HOLDOUT_INTENTS_v0.1.json, KA2_EVAL_HOLDOUT_COMMITMENT_v0.1.json, KA2_EVAL_HOLDOUT_ANSWER_KEY_v0.1.json | test_ka2_dev_evaluation.py (9), test_ka2_holdout_commitment.py (7) | 16 | PASS | 5e7aeb5 (commit) + ecb89c6 (impl) |
| WP-5 | DONE | ka2_acceptance.py, CPCS_KA2_ACCEPTANCE_v0.1.json (13/13 dev gates), KA2_EVAL_HOLDOUT_RESULT_v0.1.json (one-shot, verdict NOT_EVALUABLE with record_correction), KA2_KNOWLEDGE_RECRUITMENT_REPORT.md | — | full acceptance run | PASS (dev 13/13) + holdout verdict NOT_EVALUABLE (no tuning) | ecb89c6 (impl) + c5a19a3 (holdout reveal) + record-correction commit |

## Holdout honesty note

The holdout is **precommitted**, not sealed. Per the user's
explicit clarification: "if operationally impossible to hide the
answer key from the implementation session, state explicitly that
the evaluation is 'precommitted' rather than 'sealed' and do not
claim true holdout performance." The answer key file
(`KA2_EVAL_HOLDOUT_ANSWER_KEY_v0.1.json`) exists and is hashed, but
was not opened during implementation. The SHA-256 commitment in
`KA2_EVAL_HOLDOUT_COMMITMENT_v0.1.json` was verified before the
one-shot scoring ran.

Original recorded aggregate precision/recall: 0.0. Record
correction (post-reveal, non-amending commit): the 0.0 values label
a harness failure as a total measurement failure. 5 of 6 holdout
intents fell through FakeBackend to `trivial` (no applications), so
the recruitment pipeline was never exercised on them. The one-shot
verdict is **NOT_EVALUABLE** (harness covered 1/6). The one
evaluable intent (`holdout_05_product_destroyed`) produced a real
finding: the keyword-fallback region lacked the retrieval-side
predicted-failure metadata (FF-IDENTITY / FF-DEFORMATION), so the
recruitment gate could not fire. No tuning was attempted; no
holdout fixture was authored post-implementation.

This holdout set (intents + answer key) is BURNED. It must never be
re-scored, re-run with new fixtures, or used to guide fixture or
policy design. The next independent evaluation requires:
1. Hermetic harness coverage independent of these six intents
   (e.g., a deterministic FakeBackend fallback serving structured
   evidence from a principled slice of real frozen-corpus records).
2. A NEW intent set with expectations authored by a process separate
   from the implementation session.
3. A fresh sealed commitment and a single one-shot reveal.

Overall qualification: DEV_ONLY_PASS_INDEPENDENT_QUALIFICATION_PENDING
(computed in CPCS_KA2_ACCEPTANCE_v0.1.json).

## Implemented symbols

- `lab/application/cpcs_knowledge_constellation.py` — `region_facets`,
  `assemble_constellation`, `ExpertiseRegion`, `KnowledgeConstellation`,
  `REGION_SCHEMA`, `CONSTELLATION_SCHEMA`, `ORPHAN_REGION_ID`.
- `lab/application/cpcs_knowledge_recruitment.py` — `match_intent_signals`,
  `recruit_for_intent`, `RecruitmentDisposition`, `DISPOSITIONS`,
  `STRENGTH`, `DISPOSITION_SCHEMA`, `RECRUITMENT_SCHEMA`.
- `lab/application/cpcs_knowledge_refinement.py` —
  `assess_prerequisites`, `build_refinement_packet`, `apply_to_closure`,
  `MAX_PREREQ_DEPTH`, `MAX_ADDED_PREREQS_PER_INTENT`.
- `lab/application/reasoning_treatment.py` — `FrozenRuntimeBackend.plan`
  now projects `canonical_concept_ids` (additive; D4-clean IDs).
  7 new FAKE_FIXTURES: `a_fighter_falls_into_a_river_and_recovers`,
  the three serum/dialogue fixtures, `a_car_drives_through_a_puddle_on_a_city_street.`,
  `a_close-up_of_a_face_shows_disappointment_after_reading_a_letter.`,
  `a_drone_camera_orbits_a_coastal_cliff_with_no_performer_visible.`.
- `lab/application/cpcs_guided_handlers.py` — `_deliberate` invokes
  KA-2 additively when `application_set` is present; `_finish`
  carries `recruitment_refinement` in `final_prompt_package`
  (new optional field).
- `lab/application/ka2_acceptance.py` — 13 gates; `--reveal-holdout`
  runs the one-shot holdout scorer.

## Key semantics (do not regress)

- `apply_to_closure` mutates ONLY `planning_guidance`,
  `non_executable_knowledge_used`, `packet_hash`, and adds four
  `ka2_*` lineage keys. Every other closure field is preserved
  exactly (deep-equal with the pre-refinement closure).
- The pre-refinement `closure["packet_hash"]` is recorded on
  `closure["lineage"]["ka2_pre_refinement_closure_hash"]` BEFORE
  the additive fill, so audit can recover the original hash.
- `RecruitmentDisposition` carries `bound_requirement_ids`,
  `bound_failure_family_ids`, `bound_objective_ids`,
  `bound_trigger_ids` — the structured reasons for its decision.
  No prose is admitted into any recruitment field.
- `COVERAGE_GAP` is a per-intent field on the refinement, not a
  per-region disposition. Per-region dispositions are exactly one
  of {RECRUIT, CONTEXT, ARCHIVE, UNRESOLVED}.
- Stage 4 (representation expansion) was NOT triggered. No new
  `cpcs_typed` constructors; Control A untouched.

## Pre-KA commits

- 4fa4a54 fix(cpcs): preserve experiment arm score identity
- 5e7aeb5 feat(cpcs): add KA-2 evaluation (DEV + precommitted HOLDOUT) and WPs

## KA-2.1 / KA-2.2 closure sprint (supersedes earlier follow-up items)

- P0 fixed: production constellation was empty (dict-form application set
  ignored) and evidence metadata never reached region facets (activation
  packet has no retrieved_evidence). Both fixed + regression-tested.
- P1 fixed: vacuous trigger/objective/failure binding (same-source
  overlap); constellation merge threshold >= 2 facets; intent-predicted
  failure split (RECRUIT) vs retrieval-only overlap (CONTEXT).
- New modules: cpcs_knowledge_awareness.py (PASS 1 profile, L0/L1/L2 tags,
  universal considerations), cpcs_knowledge_placement.py (atomic units,
  scope/lifetime/emission decisions, directing modules).
- Harness: KA2_CORPUS_SLICE_v0.1.json (170 real frozen records, 28 docs,
  intent-independent policy, hashed) + FakeBackend(corpus_slice=True)
  opt-in fallback with corpus-native control projection.
- Gap taxonomy: GAP_CLASSES with gap_class on every coverage gap.
- Diagnostics: ka2_diagnostics.py -> WORKFLOW_RECRUITMENT_MATRIX.json.
- Report: GAP_CLOSURE_REPORT.md.

## Known follow-up items (NOT the burned holdout)

The KA-2 holdout set (intents + answer key) is BURNED: never re-scored,
never used to guide fixture or policy design. Do NOT author fixtures for
those six intents. The principled harness (corpus slice) replaces the
fixture-per-intent approach.

- P2: affordance-context CONTEXT flood (reasoning-only, low harm).
- P2: real-corpus constellation separation (dense frozen corpus chains
  into one mega-region; consider seeded/weighted clustering).
- P2: FrozenRuntimeBackend objective_ids evidence projection.
- OWNER_DECISION_REQUIRED: whether directing modules should ever feed a
  reviewed carrier-serialization change (Control A frozen).

