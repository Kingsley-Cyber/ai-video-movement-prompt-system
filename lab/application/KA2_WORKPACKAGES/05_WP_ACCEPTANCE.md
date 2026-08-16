# WP-5 — KA-2 acceptance gates + one-shot holdout scoring

## Goal

Compute (never hand-author) the KA-2 acceptance artifact
`CPCS_KA2_ACCEPTANCE_v0.1.json` plus the holdout result
`KA2_EVAL_HOLDOUT_RESULT_v0.1.json`. Same shape as KA-1 acceptance but
adds KA-2-specific gates.

## Computed gates

1. `ka2_constellation_groups_packs` — for each dev intent, asserts that
   the constellation has ≥1 region with ≥1 pack AND every pack in
   `KnowledgeApplicationSet.applications` appears in exactly one region.
2. `ka2_recruitment_dispositions_complete` — every region has exactly one
   `RecruitmentDisposition`, and the union of dispositions' `region_id`
   sets equals the constellation's region IDs.
3. `ka2_dev_set_positive_emergence` — every dev intent's
   `expected_recruited_regions` are all matched by a recruited region's
   facet signature.
4. `ka2_dev_set_negative_exclusion` — every dev intent's
   `expected_archived_regions` are all matched by an archived region's
   facet signature.
5. `ka2_closure_additive_only` — for each dev intent, the post-refinement
   closure equals the pre-refinement closure except for
   `planning_guidance` and `non_executable_knowledge_used` (additive) and
   the re-computed `packet_hash` plus the two lineage keys.
6. `ka2_coverage_gap_honesty` — every dev intent's
   `expected_coverage_gaps` is present in the refinement's
   `coverage_gaps` list.
7. `ka2_determinism` — running any dev intent twice yields identical
   `constellation_hash`, `refinement_hash`, and per-region
   `region_hash`.
8. `ka2_d4_preserved` — no `prose` strings introduced into any
   recruitment / constellation / refinement field.
9. `ka2_score_immutability` — the resolved score's `score_id` and
   decision fields are unchanged before and after a full finish-package
   run (this is an integration check, not a unit one).
10. `ka2_no_silent_drops` — every `PrinciplePack` in the KA-1 set is
    present in at least one region; every region has a disposition; the
    number of regions == the number of dispositions.
11. `ka2_pre_ka_regression` — `pre_ka_suites` (KA-1's regression list) all
    pass.
12. `ka2_ka1_regression` — every `test_ka1_*` suite passes.
13. `ka2_compiler_unchanged` — Control A compiler test surface remains
    green.
14. `ka2_real_runtime_smoke` — KA-2 dev intent set runs against the
    frozen runtime path with the existing KA-1 real-runtime smoke
    unchanged (env-gated; skip when runtime unavailable).
15. `ka2_holdout_one_shot` — the holdout run executes exactly once,
    verifies commitment hash, scores against the revealed answer key,
    records the result. **No retry.** The acceptance is PASS only if
    every dev gate above is also PASS AND the holdout result is recorded.
    Holdout metric failure does NOT fail the dev-acceptance gate; it is
    reported as a `holdout_recorded` field with the raw score.

## Holdout scoring (separate, post-implementation)

The acceptance script accepts a `--reveal-holdout` flag. When passed:

1. Read the answer key file.
2. Compute its hash; assert it equals the precommitted commitment.
3. Run KA-2 against each holdout intent.
4. For each holdout intent, compute:
   - recruitment precision = matched_expected / recruited_count
   - recruitment recall = matched_expected / expected_count
   - exclusion precision = correctly_archived / archived_count
   - false recruitment rate = non_expected_recruited / recruited_count
5. Write the result to `KA2_EVAL_HOLDOUT_RESULT_v0.1.json`. Do NOT
   modify the acceptance artifact based on holdout failure.

When `--reveal-holdout` is NOT passed, the acceptance script verifies
only the commitment is well-formed and the answer key file exists; it
does NOT read the answer key.

## Out of scope

- Stage 4 (representation expansion) — demand-gated; skipped in v0.1
  unless recruited regions prove they need a new family.
