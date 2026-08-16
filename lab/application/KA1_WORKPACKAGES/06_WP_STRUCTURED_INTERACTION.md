# WP-6 — Structured interaction payload (hip toss canonical object)

Depends on: nothing (parallel with WP-1..4). Owns `lab/compiler/cpcs_typed.py`
additions.

## Scope

Extend the registry's interaction constructor payload ADDITIVELY (new keys
only; existing keys unchanged):

```
interaction value adds:
  roles: {attacker, defender, initiative}
  state_before: {attacker_support, defender_support, grip, balance}
  phases: [entry, off_balance, load_bearing, projection] each with
          {action, support_shift, com_displacement, grip_persists, support_lost}
  projection: {rotation_axis: single_axis|..., rotating_actor: attacker_only|
               defender_only, force_vector: {direction, magnitude}}
  state_after: {defender: {momentum, orientation, balance},
                attacker: {balance}}
  recovery: {allowed: [...], forbidden: [...]}
  world_response: {water|surface: {deformation, drag}}
```

- All values come from source-native enums (`SOURCE_VALUE_ENUMS` pattern) or
  None; nothing reconstructed from prose (D4).
- New schema file `lab/application/CPCS_STRUCTURED_INTERACTION_SCHEMA_v0.1.json`
  describing these fields (all optional; required: roles + phases when the
  interaction is executed).
- New registry entries if needed for world_response (reuse `cpcs.event.action`
  or add `cpcs.world.response` ONLY if justified; prefer existing families).

## Acceptance tests (`test_ka1_structured_interaction.py`)

The frozen evaluation fixture:

- input: `"A fighter performs a hip toss."`
- assert the canonical output (translation structured objects) contains:
  contact interval, support state, causal phases, actor roles, force transfer,
  precondition/postcondition, recovery.
- **fail if output contains only action labels without state transitions** —
  implement exactly this assertion (action-label-only output => test failure).
- assert `rotating_actor == defender_only` and `forbidden` includes
  mirrored_rotation for the throw interaction built from combat fixture
  evidence.
- TC-2 distinctions re-run must stay green.

## Forbidden

- No changes to existing registry entry semantics; no new graph subsystem.
- No removal of the current `state_transition` enum behavior.

## Done when

`test_ka1_structured_interaction.py` passes and TC-2 tests stay green.
