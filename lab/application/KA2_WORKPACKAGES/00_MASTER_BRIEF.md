# KA-2 — Intent-Conditioned Knowledge Constellation Recruitment: Master Brief

Read this first. It is the single source of truth for all KA-2 work packages (WP).

KA-1 is **COMPLETE and FROZEN**. Do not reopen KA-1 acceptance. Do not redefine
its decision rules. Build on its substrate (`cpcs_knowledge_application.py`,
`cpcs_deliberation.py`, `reasoning_treatment.py`).

## 1. What we are building

The layer between KA-1's flat per-record application and the resolved reasoning
package:

```
DR-1 (reasoning activation)
        |
        v
KA-1 KNOWLEDGE APPLICATION BRIDGE   (frozen)
        |  flat PrinciplePacks + RepresentationDecisions
        v
KA-2 CONSTELLATION + RECRUITMENT   <-- NEW
        |  ExpertiseRegions + RECRUIT/CONTEXT/ARCHIVE/UNRESOLVED/COVERAGE_GAP
        v
KA-2 REFINEMENT                    <-- NEW
        |  bounded prerequisite emergence + closure hook fill
        v
DR-1 closure (additive) + KA-1 / typed mapping
        |
        v
Canonical Score -> Prompt carriers
```

KA-2 answers: **Which combinations of the applicable knowledge matter for THIS
creative intent, which expertise regions emerge, which are peripheral, and what
prerequisites or reasoning consequences follow?** — not "what is applicable" (KA-1),
not "what is retrieved" (retrieval), not "what hypotheses exist" (DR-1).

## 2. The five gaps (from the handoff)

1. **No constellation discovery.** KA-1 emits one flat pack per record. Nothing
   groups "support + contact topology + phase model + recovery" into one
   expertise region.
2. **No selective recruitment.** Every retrieved record becomes an applied pack.
   Selection is delegated upstream to frozen retrieval.
3. **One-way bridge.** `planning_guidance` (45) and `reasoning_material` (35) are
   dead-ends: counted in the finish package, consumed by nothing. DR-1 runs
   before the bridge; nothing feeds back.
4. **Movement-shaped breadth.** WP-6 structured interaction is the richest
   landing spot; non-movement expertise lands shallowly.
5. **No evaluation.** Only decision-mix counts. Recruitment correctness is not
   measured.

## 3. Core objects (new)

- **ExpertiseRegion** — one constellation of packs that share structured overlap
  (canonical_concept_ids, trigger_ids, objective_ids, failure_family_ids,
  requirement_ids, mechanism relationships). Carries pack_ids, evidence_ids,
  principle_families, representation_mix, intent_signal_coverage, dependencies,
  competition_refs, lineage. Deterministic, ID-only, D4-clean.
- **KnowledgeConstellation** — the full ordered set of regions, plus
  region-to-region dependency edges. Built on top of `KnowledgeApplicationSet`
  additively; does not mutate KA-1 outputs.
- **RecruitmentDisposition** — one of `RECRUIT | CONTEXT | ARCHIVE |
  UNRESOLVED | COVERAGE_GAP`, with deterministic reason codes, intent-signal
  coverage, evidence references, lineage.
- **RecruitmentRefinementPacket** — the per-intent output: recruited regions,
  context regions, archived regions, planning guidance, non-executable
  knowledge used, new prerequisite requirements, coverage gaps, unresolved
  items, lineage, packet_hash. Feeds DR-1 closure additively.
- **CoverageGapRecord** — typed report of an expertise need that the frozen
  retrieval window does not support. Never silently widened.

## 4. Where each piece lives

- `lab/application/cpcs_knowledge_constellation.py` — NEW: `ExpertiseRegion`,
  `KnowledgeConstellation`, `assemble_constellation` (deterministic group-by
  structured overlap).
- `lab/application/cpcs_knowledge_recruitment.py` — NEW: `RecruitmentDisposition`,
  `RecruitmentRefinementPacket`, `recruit_for_intent` (deterministic
  intent-conditioned gate; REPLACES nothing in KA-1).
- `lab/application/cpcs_knowledge_refinement.py` — NEW: bounded prerequisite
  emergence + closure hook fill (additive only).
- `lab/application/reasoning_treatment.py` — MODIFY ONE PASS: add
  `canonical_concept_ids` / `trigger_ids` to the
  `FrozenRuntimeBackend.plan` evidence projection (additive; D4-clean IDs;
  hermetic fixtures get the same fields). NO change to the existing
  `translate` bridge pass; KA-1's outputs are read by KA-2 as a
  downstream consumer.
- `lab/application/cpcs_deliberation.py` — MODIFY ONE PASS: in `close()`,
  invoke the refinement and fill the two empty fields
  `closure["planning_guidance"]` and `closure["non_executable_knowledge_used"]`
  additively. Do NOT replace any existing computed field.
- `lab/application/cpcs_guided_handlers.py` — MODIFY ONE PASS: in `_finish`,
  carry `recruitment_refinement` next to `knowledge_application` in the
  final_prompt_package. No change to canonical score or compiler.
- Schemas/contracts land in `lab/application/` as `CPCS_KA2_*_v0.1.json`.
- Tests land in `lab/application/tests/test_ka2_*.py`.

## 5. Frozen boundaries (DO NOT TOUCH — release blocker if violated)

- Frozen CPCS runtime (retrieval, ranking, gate) — read only via
  `FrozenRuntimeBackend`. KA-2 operates ONLY on the retrieved window.
- Control A: `lab/compiler/build.py`, `lab/compiler/score.py` semantics,
  CURRENT_BASELINE default.
- D4: no flat-text evidence admission; evidence by ID only.
- Canonical score authority: never mutate a resolved score post-resolution.
- MCP transport contract (`lab/application/mcp.py`); add ops only via
  `_register` in `service.py`.
- Authority order: USER_EXPLICIT > USER_CORRECTION > CPCS_HARD_REQUIREMENT >
  CPCS_SAFE_INFERENCE > CPCS_GROUNDED_RECOMMENDATION > EXISTING_BASELINE_DEFAULT
  > LEAVE_UNSPECIFIED.
- TC-1/TC-2 distinctions (contact persistence ≠ contact identity, force ≠
  effort ≠ momentum, etc.).
- KA-1 accepted semantics: do not change existing decision rules' outputs for
  existing fixtures unless the sealed evaluation explicitly demands it and the
  change is recorded.
- DR-1 existing computed values: additive fields only. `accepted_hypotheses`,
  `safe_inferences`, `creative_choices`, `verification_requirements`,
  `completeness`, `stopping_reason` are immutable.

## 6. Evaluation policy (two tiers)

### KA2 DEV SET (visible)
- 8–12 intents across materially different domains.
- Visible labels: expected expertise regions (canonical concept overlap),
  expected supporting regions, expected exclusions, expected prerequisite
  relations, expected representation tendencies.
- May be re-run repeatedly during implementation. Authored FIRST so test
  scaffolding can run before the engine is complete.

### KA2 HOLDOUT SET (precommitted, NOT "sealed" in the strict sense)
- True one-shot acceptance set.
- The implementation agent and the run-time agent share a session, so the
  answer key is technically readable. We treat it as **precommitted** per the
  user's own clarification.
- Procedure:
  1. Author holdout intents + answer key FIRST.
  2. Canonicalize the answer-key representation to JSON.
  3. Compute SHA-256 commitment, write it to
     `lab/application/KA2_EVAL_HOLDOUT_COMMITMENT_v0.1.json`.
  4. Preserve the actual answer key at
     `lab/application/KA2_EVAL_HOLDOUT_ANSWER_KEY_v0.1.json` but do NOT read it
     during implementation.
  5. Commit holdout intent list + commitment + key in their own commit BEFORE
     any implementation code.
  6. During implementation, do not open the answer key file.
  7. After implementation, reveal the answer key, verify its hash matches the
     precommitment, score exactly once, record the result, do NOT tune policy
     against failures.
- The "precommitted" label is honest. We do not claim true blind holdout.

## 7. Determinism

- Same input → same constellation, same recruitment, same refinement.
- Stable hashes, sorted collections, no set iteration order dependence.
- No prose similarity grouping.
- No LLM in the path; intent signals are entirely structured.

## 8. Environment

- Worktree: `/Users/king/cpcs-reasoning-ab` (branch
  `experiment/cpcs-reasoning-layer`, HEAD pre-implementation recorded in
  `CONTINUITY/GIT_STATE.txt`).
- Frozen runtime: `export CPCS_FROZEN_RUNTIME_PATH=/Users/king/Downloads/Additional/Runtime`
  (real-runtime tests; hermetic tests run WITHOUT it and use `FakeBackend`).
- Run tests: `python3 -m unittest lab.application.tests.test_ka2_xxx -q`.
- Run from repo root.
- Existing suites to re-run after any change:
  `python3 -m unittest lab.application.tests.test_reasoning_treatment_surface
  lab.application.tests.test_cpcs_typed_knowledge_coverage
  lab.application.tests.test_tc2_residual_closure
  lab.application.tests.test_deliberation_surface
  lab.application.tests.test_guided_product_surface
  lab.application.tests.test_ka1_* -q`

## 9. Definition of Done (whole KA-2)

1. Constellation assembly groups KA-1 packs into `ExpertiseRegion`s by
   structured overlap; same input → same constellation; no prose similarity.
2. Recruitment gate emits one disposition per region, with explicit reason
   codes, intent-signal coverage, and evidence IDs. Nothing silently dropped.
3. `RecruitmentRefinementPacket` produced, with bounded prerequisite emergence
   (max depth, max added prerequisites) and explicit `COVERAGE_GAP`s where
   expertise is missing inside the frozen window.
4. DR-1 closure's `planning_guidance` and `non_executable_knowledge_used` are
   additively filled. Existing computed values unchanged.
5. DEV set asserts positive emergence AND negative exclusion for every intent.
6. HOLDOUT (precommitted) is run exactly once after policy lock, with
   commitment-hash verification, and the result is recorded honestly.
7. All pre-KA + KA-1 regression suites remain GREEN. Control A unchanged. D4
   preserved. Score immutability preserved.
8. `CPCS_KA2_ACCEPTANCE_v0.1.json` is computed (never hand-authored) and ends
   PASS. The rating in `KA2_KNOWLEDGE_RECRUITMENT_REPORT.md` is earned by the
   holdout metrics, not by architecture.
9. One release commit on `experiment/cpcs-reasoning-layer`; no merge; no push
   to main.
