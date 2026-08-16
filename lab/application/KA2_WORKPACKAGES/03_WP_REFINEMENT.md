# WP-3 — RecruitmentRefinementPacket + DR-1 closure loop (additive)

## Goal

Aggregate per-region recruitment dispositions into a single
`RecruitmentRefinementPacket`, perform bounded prerequisite emergence, surface
coverage gaps, and additively feed `planning_guidance` and
`non_executable_knowledge_used` into the DR-1 closure packet without
mutating any other computed value.

## Prerequisite emergence (bounded)

KA-2 may add a structured `prerequisite_requirement` (typed ID) if a
recruited region's packs collectively reference a requirement ID that
appears in `activation.activated_reasoning_dimensions` or
`activation.candidate_failure_families` BUT is not in the original
`activation.candidate_requirements`. Bounded by:

- `MAX_PREREQ_DEPTH = 2` (one wave of prerequisite emergence from the
  current recruitment; a recruited region may emit prerequisites, but
  prerequisites do not recursively recruit further regions).
- `MAX_ADDED_PREREQS_PER_INTENT = 8`.
- Deterministic ordering: by (region_id, requirement_id).

A prerequisite is only emitted if at least one recruited region's
`pack.lineage.requirement_ids` or evidence `failure_family_ids` actually
contain the new requirement ID. **No silent invention.** If a needed
prerequisite is not supported by the current window, it is recorded as a
`COVERAGE_GAP` (rule 6 of WP-2) instead.

## Closure hook fill (ADDITIVE ONLY)

The DR-1 `close()` function emits a closure packet with two currently-empty
fields:

- `closure["planning_guidance"] = []`
- `closure["non_executable_knowledge_used"] = [...]`

After KA-2's `recruit_for_intent` runs, we additively populate:

- `closure["planning_guidance"] += [{"guidance_id", "region_id", "pack_ids",
  "evidence_ids", "authority", "bound_signals", "lineage"}]` for every
  region with `RECRUIT` or `CONTEXT` and any pack with
  `decision.decision == "PLANNING"`.
- `closure["non_executable_knowledge_used"] += sorted({"region_id:pack_id"
  for region in RECRUIT where any pack has decision NON_EXECUTABLE})`.

The existing `non_executable_knowledge_used` value (a list of
universal_type strings) is **preserved exactly**; KA-2 appends
additional structured entries. No existing computed field is replaced.

## Objects

```python
@dataclass
class RecruitmentRefinementPacket:
    refinement_id: str
    refinement_hash: str
    constellation_hash: str
    activation_packet_id: str
    treatment_packet_hash: str
    recruited_region_ids: list[str]
    context_region_ids: list[str]
    archived_region_ids: list[str]
    unresolved_region_ids: list[str]
    coverage_gaps: list[dict[str, Any]]
    new_prerequisite_requirements: list[str]
    planning_guidance: list[dict[str, Any]]
    non_executable_knowledge_used: list[str]
    disposition_digests: list[dict[str, Any]]
    lineage: dict[str, Any]
```

## Functions

- `assess_prerequisites(dispositions, constellation, activation) ->
  tuple[list[str], list[CoverageGapRecord]]` — bounded; returns added
  prerequisites + gaps.
- `build_refinement_packet(dispositions, constellation, activation,
  prerequisites, gaps) -> RecruitmentRefinementPacket` — pure; deterministic.
- `apply_to_closure(refinement, closure) -> closure` — additive only;
  returns the mutated closure (caller is responsible for re-hashing
  closure.packet_hash ONLY over the closure dict including the new
  entries, with the original field values preserved).

## Closure re-hash policy

The closure's existing `packet_hash` was computed over the
pre-refinement closure body. After KA-2 fills the two fields, the closure
must be re-hashed so downstream consumers see a consistent hash. To
preserve audit, the **original hash is recorded on
`closure["lineage"]["ka2_pre_refinement_closure_hash"]`** before the
additive fill, and `closure["lineage"]["ka2_refinement_id"]` carries the
new refinement id. The new `packet_hash` is recomputed over the
post-fill closure body.

## Tests (test_ka2_refinement.py)

- `assess_prerequisites` returns no prereqs when no recruited region's
  evidence references a new requirement.
- `assess_prerequisites` returns ≤ MAX_ADDED_PREREQS_PER_INTENT prereqs.
- `assess_prerequisites` records a COVERAGE_GAP when an unmet need has
  no supporting evidence.
- `apply_to_closure` mutates only `planning_guidance` and
  `non_executable_knowledge_used`; all other closure fields identical
  by value.
- The pre-refinement closure hash is recorded in lineage.
- The post-refinement closure hash is stable across re-runs of the same
  refinement.
- No data is invented: every new prereq ID is present in at least one
  recruited region's evidence or pack lineage.
- The refinement packet's `disposition_digests` is one entry per
  region; the union of `recruited_region_ids`, `context_region_ids`,
  `archived_region_ids`, `unresolved_region_ids` equals the total
  region count.

## Out of scope

- Stage 4 additive cpcs_typed registry constructors (demand-gated; not
  implemented unless recruited regions prove they need them).
- Score mutation (forbidden).
- New MCP operations (KA-2 is consumed by `_finish`; no new transport).
