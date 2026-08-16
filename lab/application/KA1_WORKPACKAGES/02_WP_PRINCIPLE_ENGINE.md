# WP-2 — Principle extraction + mechanism binding engine

Depends on: WP-1 (schemas exist). Parallel with WP-3.

## Scope

Implement in `lab/application/cpcs_knowledge_application.py`:

- `PrinciplePack` dataclass + `build_principle_packs(treatment_packet,
  snapshot, activation) -> list[PrinciplePack]`
- Deterministic binding rules (frozen in the module docstring):
  - Principle templates keyed by evidence universal_type + failure families +
    objectives (NO prose mining): e.g. FailureMode+FF-CONTACT ->
    principle_family "support asymmetry / contact chain"; Constraint ->
    "protected invariant"; Procedure/Workflow -> mechanism source.
  - Mechanism binding: Mechanism/Procedure/Process records whose
    supported_requirement_ids overlap the pack's requirement set.
  - Risk binding: FailureMode/NegativeConstraint records overlapping the same
    requirements; contradiction records preserved.
  - evidence_ids + source_records: IDs only (D4).
  - intent_application: tags from activation (domains, trigger ids, objectives)
    — structured tags, never free text.
- Pure function of inputs; deterministic ordering by (principle_family,
  requirement_ids, pack_id).

## Fixture knowledge needed (hermetic)

Extend `FakeBackend` fixtures (in `reasoning_treatment.py`, ADDITIVE only) with
three cross-domain fixture payloads — evidence records carrying universal
types for: combat (FailureMode, Mechanism, Constraint), ecommerce (Principle,
FailureMode, Definition), cooking (Mechanism, FailureMode, Constraint). Keep
existing fixtures untouched.

## Acceptance tests (`test_ka1_principle.py`)

- combat evidence -> at least one pack whose principle_family is
  support/contact-chain and whose failure_risk includes mirrored-rotation risk
  (mirrored_rotation fixture token).
- ecommerce evidence -> a pack with identity-visibility mechanism + logo-risk.
- cooking evidence -> a pack with cut/deformation mechanism + hand-safety risk.
- determinism: two runs identical hashes.
- D4: every pack's evidence field contains only IDs; assert no record prose
  string appears in any pack.

## Forbidden

- No retrieval changes; consume the treatment packet as given.
- No LLM; no keyword-prose extraction into canonical values.

## Done when

Engine functions exist and `test_ka1_principle.py` passes hermetic.
