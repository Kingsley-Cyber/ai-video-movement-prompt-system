# WP-4 — KnowledgeApplicationSet assembly

Depends on: WP-2, WP-3.

## Scope

In `lab/application/cpcs_knowledge_application.py`:

- `KnowledgeApplicationSet` dataclass
- `apply_knowledge(treatment_packet, snapshot, activation) ->
  KnowledgeApplicationSet`

Assembly rules:

- run WP-2 packs -> WP-3 decisions; order by authority (hardness, blocking,
  requirement importance) then deterministic id.
- competition: two packs with the same requirement_ids + different
  decisions/mechanisms are kept as alternatives (never averaged); mark
  `competition_group`.
- unknowns: packs with no decision rule match -> UNRESOLVED with reason (fail
  closed; surfaced, not guessed).
- lineage: treatment_packet_hash, activation_packet_id, affordance ledger
  versions; `set_hash` over content.

## Acceptance tests (`test_ka1_application_set.py`)

- determinism (two runs identical set_hash)
- competition preserved
- ordering stable and authority-consistent
- every pack has exactly one decision; every decision references its pack
- set_hash changes when any pack/decision changes (mutation test)

## Forbidden

- No changes to DR-1 or typed mapping; pure assembly.

## Done when

`test_ka1_application_set.py` passes hermetic.
