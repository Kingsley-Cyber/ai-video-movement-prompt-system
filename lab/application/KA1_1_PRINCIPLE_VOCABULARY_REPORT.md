# KA-1.1 — Principle Vocabulary Resolution Report

Stage result: **KA-1.1 scope PASSES; the KA-2.3 critical acceptance test
FAILS, and the remaining collapse is now precisely located in the KA-2.3
merge criteria — not in the principle-family vocabulary.**

## 1. Before-state census (computed)

`KA1_1_PRINCIPLE_FAMILY_CENSUS_BEFORE_v0.1.json`

- 1,775 frozen records; `evidence_binding` held **1,207 records (68%)** —
  42 universal types collapsed into one catch-all family.
- Executable families: protected_invariant 334, grounded_principle 137,
  mechanism_binding 82, failure_prevention 15.

## 2. Refined mapping (role-based, corpus-grounded)

`KA1_1_PRINCIPLE_FAMILY_POLICY_v0.1.json`

principle_family = **reasoning role** (never semantic subject). Derived
from the repo's own frozen TC-2 disposition ledger — no prose
classification, no LLM, no new ontology:

- NON_EXECUTABLE_KNOWLEDGE → `conceptual_foundation`
- EPISTEMIC_METADATA → `evidence_interpretation`
- PROVENANCE_ONLY → `provenance_metadata`
- RESEARCH_GOVERNANCE → `research_governance`
- VERIFICATION_ONLY → `verification_guidance`
- PROVIDER_ONLY → `provider_guidance`
- EXPECTED_STATE_ONLY → `expected_state_guidance`
- PLANNING_ONLY splits: Recommendation/Technique/Heuristic →
  `recommendation_guidance`; Example/WorkedExample → `example_guidance`;
  DecisionRule/ConditionalRule/Default/DesignDecision/Policy/Doctrine/
  Corollary → `decision_guidance`; Specification/Contract/ControlVariable →
  `specification_guidance`; Mechanism/Procedure/Process/ProcessStep/
  Workflow keep `mechanism_binding`.
- Rule/Requirement (TC-2 target cpcs.continuity.invariant) join
  `protected_invariant` instead of the catch-all.
- `Evidence` (6 records, absent from the frozen ledger) → family-level
  supplement `evidence_interpretation`; the TC-2 ledger itself untouched.

## 3. After-state census (computed)

`KA1_1_PRINCIPLE_FAMILY_CENSUS_AFTER_v0.1.json`

- 15 families; `evidence_binding` residual = **0**.
- Largest family: `conceptual_foundation` 656 (37%, down from 68%) — one
  reasoning role (Concept/Schema/Definition/Table/JSONSchema/Ontology/
  Vocabulary/Grammar/SchemaObject), not a catch-all.

## 4. Regressions

KA-1 (8 suites), KA-2/KA-2.1/KA-2.2/KA-2.3 (9 suites), TC-1/TC-2, DR-1,
guided product, reasoning treatment: all green. Full application suite
green. Explicit checks:

- D4 preserved (no prose classification; IDs only).
- non-executable → CONTROL = zero (never-control policy untouched;
  family precision does not alter RepresentationDecision authority).
- Control A unchanged; retrieval unchanged; score immutability preserved.
- KA-2.3 policy snapshot unchanged (no constellation code touched).

## 5. Post-KA1.1 region-quality audit (same KA-2.3 policy)

`KA2_3_REGION_QUALITY_AUDIT_POST_KA11_v0.1.json`

| Workflow | Regions | Dominant region | Before KA-1.1 |
|---|---|---|---|
| FIGHT | 9 | 86 packs | 8 / 90 |
| UGC_SERUM | 13 | 78 packs | 9 / 83 |
| DRONE | 10 | 87 packs | 9 / 90 |

Small regions are coherent and correctly placed (GLOBAL_INVARIANT,
PLANNING, PERFORMANCE_DIRECTION). The dominant compound persists: 18–19
documents, all families, all failure families, empty mechanisms.

## 6. Decisive diagnostic (pure seeds, no policy change)

With the two v3 merge passes disabled in a probe (thresholds raised
diagnostically, then restored):

- **Pure seeds: 74 regions, largest 5 packs.**
- Policy run: 9 regions, largest 86.

Conclusion: **the principle-family vocabulary is no longer the loss
point.** The remaining compound is manufactured by the KA-2.3
cross-seed merge criteria chaining on the dense, query-wide semantic
linkage (window concepts are few and package-level; shared failures are
near-universal across the window). Seed separation alone produces the
target constellation shape.

## 7. Verdict and next step

- KA-1.1: DONE. Vocabulary resolved (68% → 37% largest share, zero
  catch-all, role-based, frozen-ledger-grounded).
- KA-2.3 critical acceptance: **FAILS** — the dominant compound remains,
  and it is NOT semantically coherent. Per the stage rules: STOP. No new
  clustering policy was invented during this stage.
- The semantic dimension still collapsed is now precisely identified: the
  v3 cross-seed merge criteria (`concept_jaccard >= 0.5` + `shared
  failures >= 1`) are not discriminative against the dense frozen
  linkage. The evidenced next step (OWNER_DECISION_REQUIRED, KA-2.3.1):
  replace broad-window concept Jaccard with concept document-frequency
  discriminativeness (concepts specific to the shared document pair), or
  disable cross-seed merge until such evidence exists — seeds alone are
  healthy.
