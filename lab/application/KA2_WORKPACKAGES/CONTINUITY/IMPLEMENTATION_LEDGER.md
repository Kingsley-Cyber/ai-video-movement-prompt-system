# KA-2 IMPLEMENTATION LEDGER

| WP | Status | Production files | Test files | Tests run | Result | Commit |
|----|--------|------------------|------------|-----------|--------|--------|
| WP-1 | DONE | cpcs_knowledge_constellation.py (ExpertiseRegion, KnowledgeConstellation, assemble_constellation) | test_ka2_constellation.py | 8 | PASS | ecb89c6 |
| WP-2 | DONE | cpcs_knowledge_recruitment.py (RecruitmentDisposition, recruit_for_intent, dependency_consequence) | test_ka2_recruitment.py | 9 | PASS | ecb89c6 |
| WP-3 | DONE | cpcs_knowledge_refinement.py (assess_prerequisites, build_refinement_packet, apply_to_closure), cpcs_guided_handlers.py _deliberate additive fill, reasoning_treatment.py FrozenRuntimeBackend evidence projection (canonical_concept_ids additive) | test_ka2_refinement.py | 9 | PASS | ecb89c6 |
| WP-4 | DONE | KA2_EVAL_DEV_v0.1.json, KA2_EVAL_HOLDOUT_INTENTS_v0.1.json, KA2_EVAL_HOLDOUT_COMMITMENT_v0.1.json, KA2_EVAL_HOLDOUT_ANSWER_KEY_v0.1.json | test_ka2_dev_evaluation.py (9), test_ka2_holdout_commitment.py (7) | 16 | PASS | 5e7aeb5 (commit) + ecb89c6 (impl) |
| WP-5 | DONE | ka2_acceptance.py, CPCS_KA2_ACCEPTANCE_v0.1.json (13/13 PASS), KA2_EVAL_HOLDOUT_RESULT_v0.1.json (one-shot, P=0.0/R=0.0 honestly recorded), KA2_KNOWLEDGE_RECRUITMENT_REPORT.md | — | full acceptance run | PASS (dev 13/13) + holdout recorded honestly (no tuning) | ecb89c6 (impl) + post-reveal holdout commit |

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

The aggregate precision/recall of 0.0 is recorded honestly: 5 of 6
holdout intents have no FAKE_FIXTURES, so the FakeBackend falls
through to `trivial` (no applications). The 6th
(`holdout_05_product_destroyed`) matched a keyword and produced
1 region but failed the requirement/failure match. No tuning was
attempted; no holdout fixture was authored post-implementation.

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

## Known follow-up items (not blocking KA-2 acceptance)

- Add FAKE_FIXTURES for the 6 holdout intents BEFORE authoring a
  new holdout. This is a hermetic-fixture task, not an
  implementation change. New fixtures must carry structured
  canonical_concept_ids / trigger_ids / failure_family_ids.
- Real-runtime smoke against CPCS_FROZEN_RUNTIME_PATH. The
  FrozenRuntimeBackend now projects the fields KA-2 needs; the
  next natural step is a single end-to-end KA-2 run against
  the corpus.

