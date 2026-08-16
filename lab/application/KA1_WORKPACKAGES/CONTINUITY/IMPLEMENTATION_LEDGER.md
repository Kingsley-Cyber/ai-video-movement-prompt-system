# KA-1 IMPLEMENTATION LEDGER

| WP | Status | Production files | Test files | Tests run | Result | Commit |
|----|--------|------------------|------------|-----------|--------|--------|
| WP-1 | DONE | CPCS_PRINCIPLE_PACK_SCHEMA_v0.1.json, CPCS_REPRESENTATION_DECISION_SCHEMA_v0.1.json, CPCS_KNOWLEDGE_APPLICATION_CONTRACT_v0.1.json, ka1_schemas_validate.py | test_ka1_schemas.py | 10 | PASS | feat(cpcs): add knowledge application bridge |
| WP-2 | DONE | cpcs_knowledge_application.py (PrinciplePack, build_principle_packs), reasoning_treatment.py FAKE_FIXTURES (combat/ecommerce/cooking) | test_ka1_principle.py | 8 | PASS | feat(cpcs): add knowledge application bridge |
| WP-3 | DONE | cpcs_knowledge_application.py (RepresentationDecision, decide_representation, NEVER_CONTROL_UNIVERSAL_TYPES) | test_ka1_representation.py | 8 | PASS | feat(cpcs): add knowledge application bridge |
| WP-4 | DONE | cpcs_knowledge_application.py (KnowledgeApplicationSet, apply_knowledge) | test_ka1_application_set.py | 8 | PASS | feat(cpcs): add knowledge application bridge |
| WP-5 | DONE | reasoning_treatment.py (Translation fields + bridge pass), FrozenRuntimeBackend universal_type/epistemic_state projection, cpcs_guided_handlers.py (_deliberate, _finish, _knowledge_application_summary) | test_ka1_adapter.py | 6 | PASS | feat(cpcs): add knowledge application bridge |
| WP-6 | DONE | cpcs_typed.py (SOURCE_VALUE_ENUMS additions, build_interaction additive payload, validate_structured_interaction), CPCS_STRUCTURED_INTERACTION_SCHEMA_v0.1.json | test_ka1_structured_interaction.py | 5 | PASS | feat(cpcs): add knowledge application bridge |
| WP-7 | DONE | ka1_fixtures.py, CPCS_KNOWLEDGE_APPLICATION_FIXTURES_v0.1.json | test_ka1_fixtures.py | 7 (incl. real-runtime smoke) | PASS | feat(cpcs): add knowledge application bridge |
| WP-8 | DONE | cpcs_guided_handlers.py (handler_knowledge_apply_inspect + doctor line), service.py (_register cpcs.knowledge.apply.inspect) | test_ka1_mcp.py | 4 (incl. real MCP) | PASS | feat(cpcs): add knowledge application bridge |
| WP-9 | DONE | ka1_acceptance.py, CPCS_KA1_ACCEPTANCE_v0.1.json (=PASS, 10/10 gates), KA1_KNOWLEDGE_APPLICATION_REPORT.md | — | full acceptance run | PASS | feat(cpcs): add knowledge application bridge |

## Implemented symbols

- `lab/application/cpcs_knowledge_application.py` — PrinciplePack,
  RepresentationDecision, KnowledgeApplicationSet dataclasses;
  build_principle_packs, decide_representation, apply_knowledge;
  PRINCIPLE_FAMILY_BY_FAILURE, PRINCIPLE_TEMPLATES,
  HARD_UNIVERSAL_TYPES, MECHANISM_UNIVERSAL_TYPES,
  NEVER_CONTROL_UNIVERSAL_TYPES (derived from TC-2 ledger),
  DECISIONS_ALLOWED, DECISION_AUTHORITY, AUTHORITY_RANK.
- `lab/compiler/cpcs_typed.py` — new SOURCE_VALUE_ENUMS (combat_phase,
  rotation_axis, rotating_actor, support_state, com_displacement,
  contact_mode, world_deformation, drag_effect, recovery_action); extended
  build_interaction (roles, state_before, contact.contact_interval, phases,
  projection, state_after, recovery, world_response — additive keys only);
  validate_structured_interaction gate.
- `lab/application/reasoning_treatment.py` — Translation.planning_guidance /
  reasoning_material / application_set; opt-in bridge pass in translate
  (snapshot + activation kwargs); FrozenRuntimeBackend projects
  universal_type + epistemic_state from loaded records; FAKE_FIXTURES gains
  a_fighter_performs_a_hip_toss, a_person_unboxes_a_luxury_watch,
  a_chef_slices_a_tomato.
- `lab/application/cpcs_guided_handlers.py` — _deliberate passes snapshot +
  activation; _finish emits planning_guidance / reasoning_material /
  knowledge_application summary; handler_knowledge_apply_inspect; doctor
  knowledge_application check (required).
- `lab/application/service.py` — registered cpcs.knowledge.apply.inspect.
- `lab/application/ka1_fixtures.py` — FIXTURES, bridge_result,
  write_fixture_artifact.
- `lab/application/ka1_acceptance.py` — computed acceptance gates.
- `lab/application/ka1_schemas_validate.py` — schema + sample validation.

## Key semantics (do not regress)

- Evidence universal types drive decisions; without them (pre-WP-5 real
  runtime) every pack degrades to CONTROL/VVERIFICATION — the
  FrozenRuntimeBackend projection fix is load-bearing.
- control_types in pack lineage preserve PACKET ORDER (registry first-match
  semantics); do not alphabetize.
- The bridge pass in translate() is opt-in (snapshot + activation). Existing
  callers without bridge keep identical behavior.
- validate_structured_interaction is asserted in tests, not wired as a hard
  translation block (would change existing semantics).

## Pre-KA commits

- d0aa233 fix(cpcs): stop post-resolution score mutation in repair planning
- 699179b docs(cpcs): add KA-1 knowledge application bridge work packages

## Known remaining item (not KA-1)

- handler_reasoning_experiment_prepare still mutates its resolved arm-B score
  post-resolution (pre-existing). Compiling arm B will fail score identity
  validation. Separate repair-path-class fix recommended.
