# WP-3 — RepresentationDecision engine

Depends on: WP-1, WP-2. Parallel with WP-6.

## Scope

In `lab/application/cpcs_knowledge_application.py`:

- `RepresentationDecision` dataclass
- `decide_representation(pack, activation, snapshot, registry) ->
  RepresentationDecision`

Deterministic decision rules (priority order, frozen here):

1. pack has a HARD evidence record (universal_type Constraint/NegativeConstraint/
   Invariant/FailureMode) -> CONTROL (+ VERIFICATION when verification
   obligations exist) => COMPOSITE when both.
2. pack's requirements have verification_implications and NO generation
   representation in the registry => VERIFICATION.
3. pack evidence is only non-executable classes (Concept/Schema/Definition/
   Recommendation/Technique...) => use DR-1 affordance ledgers:
   - affordance includes QUERY_STEERING / HYPOTHESIS_GENERATION / CONCEPT_
     RECOGNITION => PLANNING (planning_guidance only)
   - otherwise => NON_EXECUTABLE
4. anything else => CONTROL with target_family from the registry
   (`cpcs_typed.map_control` on the pack's control types).

Each decision records: rationale (rule id), authority, target_family,
forbidden_coercions (copied from the registry entry), verification_counterpart.

## Acceptance tests (`test_ka1_representation.py`)

- combat pack -> COMPOSITE (CONTROL+VERIFICATION)
- ecommerce identity pack -> CONTROL with target family entity_state or
  continuity invariant
- a pure-theory pack (Concept evidence) -> NON_EXECUTABLE or PLANNING (never
  CONTROL)
- the 97-non-executable policy: for every NON_EXECUTABLE universal type in the
  TC-2 ledger, decide_representation never returns CONTROL.
- distinction tests: verification decision does not create a generation
  control; PLANNING decision cannot enter the canonical score (assert at
  adapter level in WP-5).
- determinism + decision_hash stability.

## Forbidden

- No new registry families here (WP-6 owns additions).
- No prose in selected values.

## Done when

`test_ka1_representation.py` passes hermetic.
