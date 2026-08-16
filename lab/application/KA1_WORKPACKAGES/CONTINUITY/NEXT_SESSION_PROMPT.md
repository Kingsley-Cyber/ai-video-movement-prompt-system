# NEXT SESSION PROMPT (paste verbatim into a new agent)

---

You are taking over an in-progress CPCS KA-1 implementation. Do not redesign the
system and do not assume the work-package plans have been implemented.

Context: this is a continuation of an AI-managed experiment inside a Git
worktree of the CPCS repo (an experimental reasoning layer stacked on a
release-qualified guided-prompting product). The repo branch is
experiment/cpcs-reasoning-layer. A "frozen CPCS runtime" exists externally at
/Users/king/Downloads/Additional/Runtime (env var CPCS_FROZEN_RUNTIME_PATH) and
is IMMUTABLE. Baseline application behavior ("Control A") is frozen. KA-1 is
the new, not-yet-implemented layer.

EXACT SEQUENCE:

1. cd /Users/king/cpcs-reasoning-ab

2. Read these files IN THIS ORDER:
   - lab/application/KA1_WORKPACKAGES/CONTINUITY/CURRENT_STATE.md
   - lab/application/KA1_WORKPACKAGES/CONTINUITY/IMPLEMENTATION_LEDGER.md
   - lab/application/KA1_WORKPACKAGES/CONTINUITY/GIT_STATE.txt
   - lab/application/KA1_WORKPACKAGES/CONTINUITY/TEST_STATE.md
   - lab/application/KA1_WORKPACKAGES/00_MASTER_BRIEF.md
   - lab/application/KA1_WORKPACKAGES/DEPENDENCIES.md
   Then read only the WP files relevant to the next unfinished dependency
   (from CURRENT_STATE.md section H).

3. Run git status and git rev-parse HEAD yourself. Trust the repository over
   any summary.

4. Inspect the production code before editing it (read the actual files listed
   in the implementation ledger).

5. If plans and code disagree, TRUST ACTUAL CODE + TESTS. Update the
   CONTINUITY files when you diverge from a plan.

6. Preserve the frozen boundaries (CURRENT_STATE.md section D) exactly:
   - Do not modify the frozen CPCS runtime, retrieval contracts, ranking, or
     gating.
   - Do not change Control A (lab/compiler/build.py, lab/compiler/score.py
     semantics; CURRENT_BASELINE default).
   - D4: no flat-text evidence admission; evidence by ID only.
   - Authority order: USER_EXPLICIT > USER_CORRECTION > CPCS_HARD_REQUIREMENT
     > CPCS_SAFE_INFERENCE > CPCS_GROUNDED_RECOMMENDATION >
     EXISTING_BASELINE_DEFAULT > LEAVE_UNSPECIFIED.
   - Never mutate a resolved canonical score post-resolution (score_id
     integrity).
   - Do not change the MCP transport or provider boundary.
   - Preserve TC-1/TC-2 distinctions (contact persistence != contact identity;
     force != effort != momentum; temporal != causal; expected != observed;
     verification != generation control; provider carrier != canonical
     control; confidence != scene state).

7. Continue from the exact WP/status recorded in CURRENT_STATE.md. All KA-1
   WPs are NOT_STARTED; begin Wave 1 (WP-1 + WP-6 in parallel) per
   DEPENDENCIES.md, unless CURRENT_STATE.md says otherwise.

8. Do NOT rerun completed architecture discovery or release qualification.
9. Do NOT add new research merely because an application mapping is missing —
   the corpus research exists; KA-1 is about APPLICATION, not acquisition.
10. Keep KA-1 corpus-aware and cross-domain.

CONCEPTUAL ARCHITECTURE (so you never collapse layers):

- DR-1 (exists): deliberation — "What should CPCS think about and what still
  needs to be known?" Produces hypotheses, query steering, closure.
- KA-1 (NEW): the Knowledge Application Bridge — "How does retrieved knowledge
  apply to THIS creative intent?" Produces PrinciplePack ->
  RepresentationDecision (CONTROL | VERIFICATION | PLANNING | NON_EXECUTABLE |
  COMPOSITE) -> KnowledgeApplicationSet.
- Typed Mapping (exists): "What canonical representation should the resolved
  application become?" (lab/compiler/cpcs_typed.py registry + constructors).
- Presentation/compiler (exists, frozen): projects canonical meaning
  downstream.

DR-1 != KA-1 != Typed Mapping. KA-1 exists to make reasoning corpus-aware at
the application boundary. Knowledge does NOT always become a control; the
RepresentationDecision is the core missing object.

THE THREE CANONICAL FIXTURES (all must be supported by the same mechanism):

COMBAT: "A fighter performs a hip toss."
ECOMMERCE: "A person unboxes a luxury watch."
COOKING: "A chef slices a tomato."

A bridge that simply applies one hardcoded interaction template with different
nouns FAILS. The application must differ because different corpus evidence,
mechanisms, risks, affordances, and representation decisions are relevant.

For the combat fixture specifically: the canonical output must contain contact
interval, support state, causal phases, actor roles, force transfer,
precondition/postcondition, and recovery. An output containing only action
labels without state transitions is INVALID (this is a required test).

EXACT NEXT COMMAND/TASK (current state):

KA-1 implementation has not begun. Start Wave 1: WP-1 (KA-1 schemas/contracts
in lab/application/) and WP-6 (structured interaction payload additions to
lab/compiler/cpcs_typed.py, additive keys only) in parallel, per the WP specs.
Before writing any code, decide how to handle the uncommitted
lab/application/reasoning_treatment.py repair fix (see CURRENT_STATE.md §F/G):
commit it separately or preserve it — do not lose it.

Environment notes: run from the worktree root; tests are unittest
(python3 -m unittest ...); hermetic tests run with CPCS_FROZEN_RUNTIME_PATH
UNSET; real-runtime tests are env-gated (skipUnless) and slow.

DO NOT: merge, push to main, promote KA-1 to default, touch provider
generation, weaken D4, or redo qualified stages.

---

END OF PROMPT
