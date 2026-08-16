# NEXT SESSION PROMPT (paste verbatim into a new agent)

---

You are starting the KA-2 Corpus-Aware Recruitment stage on top of a completed,
accepted CPCS reasoning layer. Do not redesign the system. Do not assume any
of the work below has been implemented — nothing in this file is implemented
yet; it is a plan + continuity handoff.

## 0. Verified current state (trust the repo over this summary — re-verify)

- Repo: /Users/king/cpcs-reasoning-ab
- Branch: experiment/cpcs-reasoning-layer
- HEAD: 4fa4a54 (verify with `git rev-parse HEAD` and `git status`; worktree
  was clean at handoff)
- Lineage: 29b0320 -> d0aa233 (pre-KA repair fix) -> 699179b (KA-1 planning
  docs) -> 8cb33fb (KA-1 release) -> 4fa4a54 (FIX-ARM-B arm score identity)
- Frozen runtime: /Users/king/Downloads/Additional/Runtime
  (env CPCS_FROZEN_RUNTIME_PATH; IMMUTABLE; 1,775 atomic records)
- KA-1 is COMPLETE and ACCEPTED (CPCS_KA1_ACCEPTANCE_v0.1.json = PASS,
  10/10 computed gates). Do NOT reopen KA-1, retrieval, Control A, D4, or
  the provider boundary.

## 1. What already exists (KA-1, all accepted — build ON it)

- lab/application/cpcs_knowledge_application.py — PrinciplePack,
  RepresentationDecision (CONTROL | VERIFICATION | PLANNING |
  NON_EXECUTABLE | COMPOSITE), KnowledgeApplicationSet, build_principle_packs,
  decide_representation, apply_knowledge. Deterministic, prose-free, D4-clean.
- TreatmentAdapter.translate(packet, *, snapshot=None, activation=None) —
  opt-in bridge pass; PLANNING -> planning_guidance, NON_EXECUTABLE ->
  reasoning_material (Translation sidecar fields; never enter the resolved
  score).
- FrozenRuntimeBackend projects universal_type + epistemic_state from loaded
  records (KA-1 WP-5; load-bearing for decision discrimination).
- Real evidence items carry (from frozen cpcs_production.build_packet):
  atomic_record_id, canonical_concept_ids, trigger_ids, objective_ids,
  failure_family_ids, control_ids, supported_requirement_ids, universal_type.
  THIS is the constellation vocabulary — no new research needed.
- DR-1 closure packet (lab/application/cpcs_deliberation.py close()) already
  has EMPTY fields designed for the feedback loop:
  closure["planning_guidance"] = [] and
  closure["non_executable_knowledge_used"] = [...]. The hook exists, unfed.
- Requirement snapshot: 77 requirements (40 mandatory) with dimensions,
  objectives, failures; FAKE_SNAPSHOT hermetic fixture; FakeBackend with
  combat/ecommerce/cooking fixtures.
- Tests: unittest only (`python3 -m unittest ... -q`). Hermetic = env var
  UNSET. Real-runtime tests are env-gated skipUnless and slow (~1-2 min per
  deliberation).

## 2. Why KA-2 exists (the target)

Current honest rating: ~3.5/10 toward "true corpus-aware reasoning" — CPCS
discovering an entire constellation of relevant expertise around the user's
intent and selectively recruiting the right knowledge into reasoning.

What exists: a deterministic per-record disposition router (all 100 retrieved
records get CONTROL/VERIFICATION/PLANNING/NON_EXECUTABLE/COMPOSITE landing
spots). That is breadth-SURFACING, not recruitment.

What is missing (the 5 gaps to close):
1. NO constellation discovery — one flat pack per record; nothing groups
   "support + contact topology + phase model + recovery" into one expertise
   region. Competition groups only fire on identical requirement sets.
2. NO selective recruitment — every retrieved record becomes an applied pack.
   No intent-conditioned gate; selection is delegated upstream to frozen
   retrieval. The fixture decision-mix differences are retrieval artifacts,
   NOT proof of intent conditioning.
3. ONE-WAY bridge — planning_guidance (45 items real-runtime) and
   reasoning_material (35) are dead-ends: counted in the finish package,
   consumed by nothing. DR-1 runs before the bridge; nothing feeds back.
4. Representation breadth is movement-shaped — WP-6 structured interaction is
   the richest landing spot; non-movement expertise lands shallowly.
5. NO evaluation of "was the right knowledge recruited" — only decision-mix
   counts. A 9-rating requires a sealed, held-out recruitment evaluation.

## 3. Frozen boundaries (release blockers if violated)

- Retrieval, ranking, hard gate: FROZEN (top-100 of 1,775 window). The
  recruiter selects WITHIN the window; breadth beyond it is REPORTED as a
  typed coverage gap, never silently widened.
- Control A: lab/compiler/build.py + score.py semantics, CURRENT_BASELINE
  default. Resolved scores are NEVER mutated post-resolution (score_id
  integrity; _validate_score_identity enforces at compile).
- D4: no flat-text evidence admission; evidence by ID only; no prose mining.
- Authority order: USER_EXPLICIT > USER_CORRECTION > CPCS_HARD_REQUIREMENT >
  CPCS_SAFE_INFERENCE > CPCS_GROUNDED_RECOMMENDATION >
  EXISTING_BASELINE_DEFAULT > LEAVE_UNSPECIFIED.
- MCP transport: additive `_register` in service.py only.
- TC-1/TC-2 distinctions and the NEVER_CONTROL_UNIVERSAL_TYPES policy
  (non-executable universal types can never yield CONTROL).
- KA-1 semantics: do not change existing decision rules' outputs for existing
  fixtures unless the sealed evaluation explicitly demands it and the change
  is recorded.

## 4. The 5-stage plan to reach ~9/10 (design summary; detail below)

- Stage 0: SEALED held-out evaluation set, authored FIRST, hashed, committed
  in its own commit BEFORE any implementation code. ~10 intents across
  domains; each with expected expertise regions and expected exclusions.
- Stage 1: Constellation assembly — group packs into ExpertiseRegions by
  structured overlap (failure_family_ids, canonical_concept_ids, trigger_ids,
  objective_ids, supported_requirement_ids). Additive `regions` layer on the
  KnowledgeApplicationSet. Deterministic.
- Stage 2: Recruitment gate — deterministic, prose-free, intent-conditioned
  dispositions RECRUIT / CONTEXT / ARCHIVE against activation signals
  (mandatory requirements, predicted failure families, objectives_at_risk,
  activated triggers/domains). Nothing silently dropped: every pack keeps an
  explicit disposition + reason. Ordering becomes recruitment rank within
  authority tiers.
- Stage 3: Close the loop — feed the application set into the existing empty
  closure fields (closure["planning_guidance"],
  closure["non_executable_knowledge_used"]) additively; guided finish package
  gains a recruited-region summary. DR-1 computed values unchanged.
- Stage 4 (small, optional): additive cpcs_typed registry constructors for
  corpus-carried non-movement families the sealed set demands (material
  response, stick/slip contact modes, visibility persistence). Additive keys
  only (WP-6 precedent). Control A untouched.
- Stage 5: one-shot acceptance — run sealed eval once after policy locks;
  compute gates (constellation coverage, recruitment precision vs sealed
  expectations, exclusion honesty, loop evidence, frozen regressions,
  determinism). Failures recorded honestly; do NOT tune policy to the eval
  (benchmark integrity).

## 5. EXACT NEXT ACTIONS (do these in order)

1. `cd /Users/king/cpcs-reasoning-ab && git rev-parse HEAD && git status`
   Re-verify state. Trust the repo over this file.
2. Read: lab/application/cpcs_knowledge_application.py,
   lab/application/reasoning_treatment.py (translate + FrozenRuntimeBackend),
   lab/application/cpcs_deliberation.py (close + activation),
   lab/application/KA1_WORKPACKAGES/CONTINUITY/IMPLEMENTATION_LEDGER.md,
   lab/application/KA1_KNOWLEDGE_APPLICATION_REPORT.md.
3. ASK THE USER the four open decisions (were left unanswered at handoff):
   a. Scope: all stages, or stop after Stage 3?
   b. Sealed eval authorship: you author the expected-region set (sealed
      commit before implementation), or the user drafts/reviews expectations?
   c. Naming: new KA-2 stage with its own WPs/artifacts, or extend KA-1?
   d. Confirm DR-1 additive-touch rule: fill existing empty closure fields
      only; no changes to existing computed values.
4. Implement Stage 0 FIRST regardless of other answers: write the sealed
   evaluation fixture (intents + expected regions + expected exclusions +
   per-intent hash), commit it alone with a clear "SEALED EVALUATION —
   DO NOT EDIT WITHOUT RE-SEALING" note. Record its content hash in the
   acceptance artifacts.
5. Then Stage 1 -> Stage 2 -> Stage 3 per scope decision, each with
   deterministic unit tests (test_ka2_*.py) and the pre-KA + KA-1 regression
   group re-run after every change:
   python3 -m unittest lab.application.tests.test_reasoning_treatment_surface
   lab.application.tests.test_cpcs_typed_knowledge_coverage
   lab.application.tests.test_tc2_residual_closure
   lab.application.tests.test_deliberation_surface
   lab.application.tests.test_guided_product_surface
   lab.application.tests.test_ka1_* -q
6. Real-runtime smoke env-gated only:
   CPCS_FROZEN_RUNTIME_PATH=/Users/king/Downloads/Additional/Runtime \
   python3 -m unittest lab.application.tests.test_ka2_* -q
7. Before every commit: python3 lab/scripts/validate_repo.py must be GREEN
   (run python3 lab/scripts/sync_repo.py --fix for stale derived maps), then
   `git diff --check`. Commit imperatively with the
   Kingsley-Cyber Co-Authored-By line; append one CHANGELOG.md line
   ([lab] scope). Do not merge; do not push to main; push only
   origin/experiment/cpcs-reasoning-layer.

## 6. Environment notes

- Run from repo root; python3 -m unittest (NOT pytest).
- Hermetic tests: CPCS_FROZEN_RUNTIME_PATH UNSET (FakeBackend + FAKE_SNAPSHOT).
- Real-runtime: export CPCS_FROZEN_RUNTIME_PATH=/Users/king/Downloads/Additional/Runtime
- Real-runtime decision mix reference (KA-1, hip toss, 100 records):
  4 COMPOSITE / 15 CONTROL / 45 PLANNING / 35 NON_EXECUTABLE / 1 VERIFICATION.
- Determinism is non-negotiable: stable hashes, sorted collections, no set
  iteration order dependence.

## 7. DO NOT

- Do not reopen KA-1 acceptance, frozen retrieval, Control A, D4, authority
  order, score immutability, MCP transport, or the provider boundary.
- Do not add new research merely because a mapping is missing.
- Do not let the recruitment gate silently drop knowledge — explicit
  disposition or fail closed, always.
- Do not tune stage policies against the sealed evaluation set (benchmark
  integrity). A second sealed set is required for tuning iterations.
- Do not wire the bridge into DR-1's computed values — additive fields only.

---

END OF PROMPT
