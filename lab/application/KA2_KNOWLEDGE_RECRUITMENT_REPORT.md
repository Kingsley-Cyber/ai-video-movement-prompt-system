# KA-2 — Intent-Conditioned Knowledge Constellation Recruitment Report

KA-2 WP-1..WP-5 implementation, dev acceptance (PASS), and precommitted
holdout one-shot (PASS on integrity, recorded honestly on score).

## What ships

| File | Purpose |
|------|---------|
| `lab/application/cpcs_knowledge_constellation.py` | `ExpertiseRegion` + `KnowledgeConstellation`; `assemble_constellation(application_set, activation, evidence_by_id)` groups KA-1 packs by structured overlap of corpus vocabulary (canonical_concept_ids, trigger_ids, objective_ids, failure_family_ids, requirement_ids, principle_family). No prose similarity, D4-clean. |
| `lab/application/cpcs_knowledge_recruitment.py` | `RecruitmentDisposition` ∈ {RECRUIT, CONTEXT, ARCHIVE, UNRESOLVED}; `recruit_for_intent(constellation, activation, pack_lookup)` runs the deterministic rule cascade (mandatory_requirement_bound → predicted_failure_bound → objective_at_risk_bound → trigger_entailment_bound → prerequisite_consequence → mandatory_requirement_uncovered COVERAGE_GAP → reasoning_dimension_unsupported COVERAGE_GAP). |
| `lab/application/cpcs_knowledge_refinement.py` | `RecruitmentRefinementPacket` with bounded prerequisite emergence (MAX_PREREQ_DEPTH=1, MAX_ADDED_PREREQS_PER_INTENT=8); `apply_to_closure(refinement, closure)` additively fills the two existing empty closure fields, records pre-refinement closure hash in lineage, recomputes `packet_hash` over the post-fill body. NO other closure field is mutated. |
| `lab/application/cpcs_guided_handlers.py` | `_deliberate` invokes KA-2 after KA-1 produces `application_set`; `_finish` carries `recruitment_refinement` in the final prompt package (additive field). |
| `lab/application/reasoning_treatment.py` | `FrozenRuntimeBackend.plan` projects `canonical_concept_ids` from the frozen runtime record (additive; same WP-5 pattern as universal_type/epistemic_state). 7 new hermetic FAKE_FIXTURES for the DEV set. |
| `lab/application/ka2_acceptance.py` | 13 computed gates. `--reveal-holdout` runs the one-shot holdout scorer. |
| `lab/application/CPCS_KA2_ACCEPTANCE_v0.1.json` | Computed PASS (13/13 dev gates). |

## KA-2 acceptance status

```
status: PASS (13/13 dev gates — development-set regression only)
qualification_status: DEV_ONLY_PASS_INDEPENDENT_QUALIFICATION_PENDING
holdout commitment verified, holdout verdict: NOT_EVALUABLE (see below)
```

## Holdout status (precommitted, NOT sealed)

The user explicitly acknowledged that the implementation agent and
the run-time agent share the same session, so the holdout is labeled
`precommitted`, not `sealed`. The SHA-256 commitment was computed
before implementation started (commit `5e7aeb5`) and verified at
one-shot run time. The answer key file was NOT read during
implementation.

### One-shot result (no tuning)

```
commitment_verified: true
aggregate_precision: 0.0   (original recorded value)
aggregate_recall: 0.0      (original recorded value)
```

### Corrected verdict (record correction, not a re-score)

The original 0.0 numbers label a harness failure as a total
measurement failure. Five of six intents fell through FakeBackend to
the `trivial` fixture — the recruitment pipeline was never exercised
on them. The honest verdict for this holdout is **NOT_EVALUABLE**
(harness covered 1/6 intents, evaluable 1/6). The one evaluable
intent produced a real finding: the keyword-fallback region lacked
the retrieval-side predicted-failure metadata (FF-IDENTITY /
FF-DEFORMATION), so the recruitment gate could not fire. Recruitment
correctness depends on retrieval-provided structured
failure-family/concept metadata.

The original values are preserved in
`KA2_EVAL_HOLDOUT_RESULT_v0.1.json`; the correction is recorded in
its `record_correction` block. Overall qualification status in
`CPCS_KA2_ACCEPTANCE_v0.1.json` is
`DEV_ONLY_PASS_INDEPENDENT_QUALIFICATION_PENDING`.

### Path to the next independent evaluation (non-contaminated)

This holdout set is burned: it must never be re-scored, re-run with
new fixtures, or used to guide fixture or policy design.

1. Fix hermetic harness coverage independent of these six intents —
   e.g., a deterministic FakeBackend fallback that serves structured
   evidence from a principled slice of real frozen-corpus records,
   so unseen intents can exercise the pipeline without hand-authored
   fixtures.
2. Author a NEW intent set whose expectations are written by a
   process separate from the implementation session (user-authored or
   a separate agent session).
3. Seal it (fresh SHA-256 commitment), implement nothing against it,
   and score it exactly once after policy lock.

## Frozen boundaries (preserved)

- Frozen CPCS runtime: unchanged. Only the FrozenRuntimeBackend.plan
  evidence projection gained one additive field (`canonical_concept_ids`).
- Control A (`lab/compiler/build.py`, `lab/compiler/score.py`): unchanged.
- D4: no flat-text evidence admission.
- Score immutability: post-resolution scores are not mutated.
- MCP transport: no new ops; `recruitment_refinement` rides in the
  existing finish package.
- TC-1/TC-2 distinctions: unchanged.
- Authority order: unchanged.
- KA-1 accepted semantics: untouched. The KA-2 layer is a downstream
  consumer of `KnowledgeApplicationSet`.
- DR-1 existing computed values: `accepted_hypotheses`,
  `safe_inferences`, `creative_choices`, `verification_requirements`,
  `completeness`, `stopping_reason` are preserved exactly. Only
  `planning_guidance` and `non_executable_knowledge_used` are
  additively filled.

## What did NOT ship

- **Stage 4 (representation expansion).** No new `cpcs_typed`
  registry constructors. No recruited region in DEV or holdout
  proves a need. The WP-4 demand gate was not triggered.
- **Real-runtime smoke against the frozen runtime.** The acceptance
  ran with `FakeBackend`. The real-runtime path runs the
  same code (`assemble_constellation`, `recruit_for_intent`,
  `assess_prerequisites`, `build_refinement_packet`,
  `apply_to_closure`) and the FrozenRuntimeBackend projection now
  carries the required structured fields. A real-runtime smoke
  is the next natural step for whoever picks this up next; it
  was not gated into this commit because it requires the
  `CPCS_FROZEN_RUNTIME_PATH` env var and the user's prior runs
  showed real-runtime is 1–2 min per deliberation.

## Rating

The handoff's "3.5/10 honest rating" was the starting point.
The DEV set now passes all 10 intents with positive emergence.
The holdout one-shot verdict is **NOT_EVALUABLE** (harness uncovered
5/6 intents); no recruitment-quality claim can be made from it.

The rating that can be **earned** by architecture alone is now
"structured regions + dispositions + closure loop additive +
D4 preserved + determinism + bounded prerequisite emergence". The
rating that needs an independent evaluation with harness coverage
and corpus-backed evidence is **not** earned here. The handoff was
explicit: "The rating must be earned by the holdout evaluation."
Qualification status: `DEV_ONLY_PASS_INDEPENDENT_QUALIFICATION_PENDING`.
