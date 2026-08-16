# WP-2 — Intent-Conditioned Recruitment Gate

## Goal

Assign exactly one `RecruitmentDisposition` to every `ExpertiseRegion` based on
structured intent signals from the activation packet. No prose similarity, no
LLM, no silent drops.

## Dispositions

```
RECRUIT      — region materially changes reasoning, planning, canonical
               representation, or verification for this intent.
CONTEXT      — useful supporting knowledge but not central enough to drive
               representation.
ARCHIVE      — retrieved and valid, but peripheral to this creative problem.
UNRESOLVED   — insufficient structured evidence to decide safely.
COVERAGE_GAP — important expertise need identified by reasoning that is
               NOT supported within the frozen retrieved window.
```

Nothing disappears silently. Every region carries:

- `disposition`
- `reason_codes` (list of typed codes)
- `intent_signals` (list of activation packet fields that drove the decision)
- `evidence_ids` (the region's evidence IDs)
- `lineage` (treatment packet hash, activation packet id, constellation hash)

## Decision rules (deterministic, frozen for KA-2 v0.1)

The gate is a function of:

- `region.canonical_concept_ids`
- `region.trigger_ids`
- `region.objective_ids`
- `region.failure_family_ids`
- `region.requirement_ids`
- `region.representation_mix` (counts of KA-1 decisions)
- `activation.activated_concepts` (trigger IDs)
- `activation.candidate_objectives` (objectives at risk)
- `activation.candidate_failure_families` (predicted failure families)
- `activation.activated_reasoning_dimensions` (DIM-…)
- `activation.activated_domains`
- `activation.activated_triggers` (parent trigger source IDs)
- `activation.activated_reasoning_affordances` (DR-1 affordances)
- `activation.candidate_requirements` (mandatory requirement IDs)

Rule order (first match wins, all rules checked but disposition = max
strength):

1. **Hard bind → RECRUIT** if `region.requirement_ids` ∩
   `activation.candidate_requirements` is non-empty AND the region carries at
   least one pack whose decision ∈ {CONTROL, COMPOSITE, VERIFICATION}. Reason
   code: `mandatory_requirement_bound`.
2. **Failure bind → RECRUIT** if `region.failure_family_ids` ∩
   `activation.candidate_failure_families` is non-empty AND
   `region.representation_mix` has CONTROL or COMPOSITE. Reason code:
   `predicted_failure_bound`.
3. **Objective bind → RECRUIT** if `region.objective_ids` ∩
   `activation.candidate_objectives` is non-empty. Reason code:
   `objective_at_risk_bound`.
4. **Trigger / concept bind → RECRUIT** if `region.trigger_ids` ∩
   `activation.activated_concepts` is non-empty. Reason code:
   `trigger_entailment_bound`. **This is the emergence rule** — it allows a
   region whose trigger IDs match an activated concept the user did not
   name in the surface intent.
5. **Reasoning-affordance consequence → RECRUIT** if the region's pack
   universal_types have planning / non-executable affordances that
   intersect `activation.activated_reasoning_affordances` AND another
   already-recruited region depends on this region (via a region
   dependency edge from WP-1). Reason code:
   `prerequisite_consequence`. **This is the dependency-emergence rule**.
6. **Mandatory uncovered → COVERAGE_GAP** if the activation packet has
   `uncovered_mandatory_requirements` non-empty AND the activation's
   `candidate_requirements` references a requirement ID that no region
   covers via any pack. Reason code: `mandatory_requirement_uncovered`.
7. **Reasoning affordance alone → CONTEXT** if the region's
   universal_types have affordances that intersect
   `activation.activated_reasoning_affordances` but the region is not
   directly bound by 1–5. Reason code: `affordance_contextual`.
8. **Evidence present but no signal → ARCHIVE** if the region has ≥1
   evidence ID but no overlap with any intent signal. Reason code:
   `peripheral_to_intent`.
9. **Insufficient evidence → UNRESOLVED** if the region has zero evidence
   IDs and zero pack_ids. Reason code: `no_evidence_under_frozen_window`.

The disposition is the max-strength of all matched rules. Strength order:

```
RECRUIT > CONTEXT > ARCHIVE > UNRESOLVED
COVERAGE_GAP is reported as a separate field on the constellation
(per-region `coverage_gap_emitted: bool`), not as a region disposition.
```

When multiple RECRUIT rules match, the reason_codes union is preserved
(do not lose them). When CONTEXT and RECRUIT both match, RECRUIT wins and
the CONTEXT reason code is preserved as a contributing reason.

## Objects

```python
@dataclass
class RecruitmentDisposition:
    region_id: str
    disposition: str            # RECRUIT | CONTEXT | ARCHIVE | UNRESOLVED
    reason_codes: list[str]
    intent_signals: dict[str, list[str]]
    evidence_ids: list[str]
    bound_requirement_ids: list[str]
    bound_failure_family_ids: list[str]
    bound_objective_ids: list[str]
    bound_trigger_ids: list[str]
    contributing_regions: list[str]
    coverage_gap_emitted: bool
    lineage: dict[str, Any]
```

## Functions

- `match_intent_signals(region, activation) -> dict[str, list[str]]` — pure
- `recruit_for_intent(constellation, activation) -> list[RecruitmentDisposition]`
  — top-level; one disposition per region; deterministic

## Tests (test_ka2_recruitment.py)

- A region bound to a mandatory requirement + a CONTROL decision → RECRUIT
  with code `mandatory_requirement_bound`.
- A region whose `trigger_ids` intersect `activated_concepts` even though the
  user intent did not name them → RECRUIT (emergence).
- A region with a planning/non-executable affordance that depends on a
  recruited region → RECRUIT (dependency consequence).
- A region with zero intent overlap and ≥1 evidence → ARCHIVE
  (`peripheral_to_intent`).
- Empty region (no evidence, no packs) → UNRESOLVED.
- A mandatory requirement with zero regions → COVERAGE_GAP emitted.
- Determinism: same inputs → same dispositions and same per-region hashes.
- Disposition is monotonic: adding a new intent signal that matches an
  archived region can only move it to RECRUIT or CONTEXT, never the reverse.
- No region is silently dropped; every region has a disposition.
- Recruitment does not mutate the constellation; new object.
