# WP-1 — ExpertiseRegion + KnowledgeConstellation assembly

## Goal

Group the flat `PrinciplePack` list from KA-1's `KnowledgeApplicationSet` into
deterministic `ExpertiseRegion`s by structured overlap of corpus vocabulary.
No prose similarity, no LLM.

## Inputs

- `KnowledgeApplicationSet` (KA-1, frozen):
  - `applications[i].pack`: `PrinciplePack`
    - `pack_id`, `pack_hash`
    - `principle_family`
    - `mechanism`
    - `evidence_ids`
    - `source_records` (each carrying `atomic_record_id`, `universal_type`,
      `epistemic_status`)
    - `intent_application` (domain_tags, creative_goal_tags, trigger_ids,
      objective_ids)
    - `lineage` (requirement_ids, control_types, verification_obligation_ids,
      contradiction_ids, treatment_packet_hash, activation_packet_id)
  - `applications[i].decision`: `RepresentationDecision`
    - `decision` ∈ {CONTROL, VERIFICATION, PLANNING, NON_EXECUTABLE, COMPOSITE}
  - `applications[i].competition_group`
- Activation packet: `activated_domains`, `activated_triggers`,
  `activated_reasoning_dimensions`, `activated_reasoning_affordances`,
  `candidate_objectives`, `candidate_failure_families`,
  `activated_concepts`.
- Evidence records (read-only, via `evidence_by_id` map projected by
  FrozenRuntimeBackend and the FAKE_FIXTURES):
  - `canonical_concept_ids` (NEW in WP-3 projection extension)
  - `trigger_ids`, `objective_ids`, `failure_family_ids`, `control_ids`
  - `universal_type`, `epistemic_status`

## Grouping keys (structured, ID-only, no prose)

For each pack, the region-key facet set is the union (sorted) of:

- `pack.intent_application.trigger_ids`
- `pack.intent_application.objective_ids`
- `pack.lineage.requirement_ids`
- aggregated `failure_family_ids` over `pack.evidence_ids` (from evidence
  records)
- aggregated `canonical_concept_ids` over `pack.evidence_ids`
- `pack.principle_family`

Two packs join the same region iff their facet sets overlap by at least
`MIN_REGION_OVERLAP` ID tokens (default: 1, conservative). Packs that
share no tokens with any other pack get a singleton region. Empty facet
sets land in a single `orphan` region, never merged with others.

Determinism:

- Region ID = `region_` + sha256(sorted pack_ids)[:16].
- Region hash = sha256 of canonical region dict (sorted keys).
- Final constellation order = regions sorted by (region_id,) so output is
  stable.

## Objects

```python
@dataclass
class ExpertiseRegion:
    region_id: str
    region_hash: str
    pack_ids: list[str]
    evidence_ids: list[str]
    canonical_concept_ids: list[str]
    trigger_ids: list[str]
    objective_ids: list[str]
    failure_family_ids: list[str]
    requirement_ids: list[str]
    principle_families: list[str]
    representation_mix: dict[str, int]   # decision -> count
    intent_signal_coverage: dict[str, list[str]]
    dependencies: list[str]              # other region_ids
    competition_refs: list[str]
    lineage: dict[str, Any]
```

```python
@dataclass
class KnowledgeConstellation:
    constellation_id: str
    constellation_hash: str
    regions: list[dict[str, Any]]        # serialized ExpertiseRegion
    region_dependency_edges: list[dict[str, str]]
    lineage: dict[str, Any]
```

## Functions

- `region_facets(pack, evidence_by_id) -> set[str]` — pure
- `assemble_constellation(application_set, activation, *,
  evidence_by_id=None) -> KnowledgeConstellation` — top-level; idempotent
- `region_for_pack(region, pack_id) -> bool` — membership test
- `orphan_region() -> dict` — single-facet region for packs with no overlap

## Tests (test_ka2_constellation.py)

- Two packs sharing a requirement_id and one trigger_id land in one region.
- Two packs sharing no tokens land in two singleton regions.
- Determinism: same input → same constellation_hash twice.
- Region coverage of principle_families is preserved.
- Representation mix preserves KA-1 decisions exactly.
- Region hash changes when one pack's pack_hash changes.
- Orphan region is created for a pack with empty facet set; never merged.

## Out of scope

- Recruitment decisions (WP-2).
- Prerequisite edges (WP-3).
- Closure hook fill (WP-3).
