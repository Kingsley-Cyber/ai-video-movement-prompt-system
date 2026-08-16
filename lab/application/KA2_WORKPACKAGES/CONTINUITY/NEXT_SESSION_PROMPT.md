# NEXT SESSION PROMPT (paste verbatim into a new agent)

---

You are taking over the CPCS corpus-aware reasoning line at the KA-2.3
boundary. KA-1, FIX-ARM-B, KA-2, KA-2.1/KA-2.2 are complete and pushed.
The next stage is REFINEMENT + PROOF, not new machinery.

## 0. Verify current state first (trust the repo over this file)

- Repo: /Users/king/cpcs-reasoning-ab
- Branch: experiment/cpcs-reasoning-layer
- HEAD at last handoff: 87e9e64 (verify with `git rev-parse HEAD` and
  `git status`; worktree was clean)
- Lineage: 4fa4a54 -> 5e7aeb5 (KA-2 eval+WPs) -> ecb89c6 (KA-2 impl) ->
  c5a19a3 (holdout reveal) -> c3c0c8a (record correction) -> 87e9e64
  (KA-2.1/KA-2.2 closure+placement)
- Frozen runtime: /Users/king/Downloads/Additional/Runtime
  (CPCS_FROZEN_RUNTIME_PATH; IMMUTABLE; 1,775 atomic records)
- Qualification status: DEV_ONLY_PASS_INDEPENDENT_QUALIFICATION_PENDING.

## 1. What exists (all shipped and tested)

- KA-1 bridge (packs / representation decisions / application set),
  structured interaction payload, MCP inspect op.
- KA-2 constellation + recruitment + refinement
  (cpcs_knowledge_constellation.py, cpcs_knowledge_recruitment.py,
  cpcs_knowledge_refinement.py).
- KA-2.1 PASS-1 awareness (cpcs_knowledge_awareness.py: L0 universal
  considerations, L1 workflow tags, L2 expertise tags, intent signals).
- KA-2.2 placement (cpcs_knowledge_placement.py: atomic units from typed
  structured objects, scope/lifetime/role/emission decisions, directing
  modules).
- Hermetic harness: KA2_CORPUS_SLICE_v0.1.json (170 real frozen records,
  intent-independent policy, hashed) + FakeBackend(corpus_slice=True).
- Gap taxonomy (GAP_CLASSES) on coverage gaps.
- Diagnostics: ka2_diagnostics.py -> WORKFLOW_RECRUITMENT_MATRIX.json
  (hermetic, 11 workflows).
- Reports: GAP_CLOSURE_REPORT.md; acceptance CPCS_KA2_ACCEPTANCE_v0.1.json
  (13/13 dev gates).

## 2. THE PLAN — read this file FIRST

`KA2_WORKPACKAGES/CONTINUITY/KA2_3_PLANNED_REFINEMENTS.md` is the frozen
design record for this stage. It contains:

- the 27-document knowledge-space audit expectations (8 families),
- the five-view knowledge model (WORKFLOW / EXPERTISE / MECHANISM /
  FAILURE / APPLICATION),
- event-aware PASS-1 proto-event design (NOT a keyword router),
- universal-consideration verdicts (CONSEQUENTIAL /
  NOT_CONSEQUENTIAL / UNRESOLVED + COVERAGE_GAP),
- source-provenance requirements at constellation level,
- the LOCKED execution order (below).

Everything there is PLANNED/HYPOTHESIS — nothing implemented.

## 3. LOCKED execution order (do not reorder)

1. Policy-neutral merge instrumentation in assemble_constellation
   (record per-region merge facets, member counts, facet unions; per-edge
   strong-vs-bridge kind). No policy change.
2. Commit the PRE-POLICY real-runtime 11-workflow sweep
   (extend ka2_diagnostics.py with a FrozenRuntimeBackend mode writing
   WORKFLOW_RECRUITMENT_MATRIX_REAL_v0.1.json; ~20-25 min, env-gated).
3. Inspect the sweep: region counts/sizes, which facets caused merges,
   bridge density, dispositions, prerequisites, gaps, placement counts.
   Determine whether the mega-region is universal or workflow-specific.
4. Implement only what the sweep + DEV set justify:
   KA-2.3 weighted region separation (strong facets merge; weak facets
   bridge as INTRA vs INTER distinction), event-aware PASS 1, five-view
   tag refinement, universal verdicts.
5. POST-POLICY sweep; compare against the pre-policy baseline.
6. Freeze policy (stop dev tuning BEFORE any holdout authoring).
7. Regression + DEV evaluation.
8. Independent holdout: authored by a SEPARATE process/session, sealed
   commitment, one-shot real-runtime scoring; metrics at least:
   unstated-expertise emergence, selectivity, region quality,
   prerequisite recall, placement accuracy, prompt economy,
   coverage-gap honesty.

## 4. Hard constraints (unchanged)

- The KA-2 holdout (intents + answer key) is BURNED: never re-scored,
  never used to guide fixture or policy design.
- No retrieval changes (top-100 contract). No Control A changes.
  No D4 weakening. No resolved-score mutation. No MCP transport change.
  No new research. Carrier serialization stays DEFERRED
  (OWNER_DECISION_REQUIRED).
- Workflow tags are MANY-TO-MANY activation hints, never recall gates,
  never canonical controls.
- MECHANISM tags are derived (origin field + source record IDs +
  derivation rule + lineage); concept != mechanism. FAILURE stays a
  VIEW over failure_family_ids — no second failure taxonomy.

## 5. Environment

- Run from repo root; python3 -m unittest (not pytest).
- Hermetic: CPCS_FROZEN_RUNTIME_PATH UNSET (FakeBackend + FAKE_SNAPSHOT).
- Real-runtime: export CPCS_FROZEN_RUNTIME_PATH=/Users/king/Downloads/Additional/Runtime
  (slow: ~1-2 min per deliberation).
- Before every commit: `python3 lab/scripts/sync_repo.py --fix` then
  `python3 lab/scripts/validate_repo.py` must be GREEN, plus
  `git diff --check`. Commit imperatively with the
  Kingsley-Cyber Co-Authored-By line and a CHANGELOG.md line. Push only
  origin/experiment/cpcs-reasoning-layer. No merge, no promotion.

## 6. Regression group

python3 -m unittest lab.application.tests.test_reasoning_treatment_surface
lab.application.tests.test_cpcs_typed_knowledge_coverage
lab.application.tests.test_tc2_residual_closure
lab.application.tests.test_deliberation_surface
lab.application.tests.test_guided_product_surface
lab.application.tests.test_ka1_schemas lab.application.tests.test_ka1_structured_interaction
lab.application.tests.test_ka1_principle lab.application.tests.test_ka1_representation
lab.application.tests.test_ka1_application_set lab.application.tests.test_ka1_adapter
lab.application.tests.test_ka1_mcp lab.application.tests.test_ka1_fixtures
lab.application.tests.test_ka2_constellation lab.application.tests.test_ka2_recruitment
lab.application.tests.test_ka2_refinement lab.application.tests.test_ka2_dev_evaluation
lab.application.tests.test_ka2_holdout_commitment lab.application.tests.test_ka2_awareness
lab.application.tests.test_ka2_placement lab.application.tests.test_ka2_harness -q

then the full application suite:
python3 -m unittest discover -s lab/application/tests -q

---

END OF PROMPT
