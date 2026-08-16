# KA-1 IMPLEMENTATION LEDGER

| WP | Status | Production files | Test files | Tests run | Result | Commit |
|----|--------|------------------|------------|-----------|--------|--------|
| WP-1 | NOT_STARTED | — | — | — | — | — |
| WP-2 | NOT_STARTED | — | — | — | — | — |
| WP-3 | NOT_STARTED | — | — | — | — | — |
| WP-4 | NOT_STARTED | — | — | — | — | — |
| WP-5 | NOT_STARTED | — | — | — | — | — |
| WP-6 | NOT_STARTED | — | — | — | — | — |
| WP-7 | NOT_STARTED | — | — | — | — | — |
| WP-8 | NOT_STARTED | — | — | — | — | — |
| WP-9 | NOT_STARTED | — | — | — | — | — |

## Implemented symbols

None. No KA-1 production symbols exist yet.

Pre-KA symbols that KA-1 builds ON (verified to exist):

- `lab/application/cpcs_deliberation.py` — DeliberationEngine, KnowledgeSnapshot,
  extract_observations, hypothesize, steer, update, close, ideate;
  NON_EXECUTABLE_AFFORDANCES, PLANNING_AFFORDANCES, FAKE_SNAPSHOT,
  frozen_knowledge_snapshot, DeliberationBudget.
- `lab/application/reasoning_treatment.py` — FrozenRuntimeBackend, FakeBackend,
  TreatmentAdapter.translate (overlays + structured_objects +
  verification_requirements + provider_neutral_controls + duplicate_semantics),
  DiscrepancyBuilder, RepairPlanner, handler_repair_gap_prepare,
  handler_repair_plan, apply_structured_objects.
- `lab/compiler/cpcs_typed.py` — REGISTRY (19 entries), CONTROL_TYPE_TO_PATH
  (58 rules), CONSTRUCTORS (12), SOURCE_VALUE_ENUMS (contact_state_transition,
  visibility_state, possession_transition), map_control.
- `lab/application/cpcs_guided.py` — GuidedProjector, GuidedSessionStore (STORE),
  detect_mode, classify_unknown, AUTHORITY_ORDER, COMPRESSION_GROUPS,
  CORRECTION_KEYWORDS.
- `lab/application/bootstrap.py` — bootstrap, resolved_runtime_path,
  validate_runtime, load_local_config, write_local_config, config_path.

## Planned but NOT implemented

Everything in the KA1_WORKPACKAGES WP files. Design documents are NOT code.
Specifically missing:

- `lab/application/cpcs_knowledge_application.py` (entire module)
- PrinciplePack / RepresentationDecision / KnowledgeApplicationSet dataclasses
- build_principle_packs() / decide_representation() / apply_knowledge()
- CPCS_PRINCIPLE_PACK_SCHEMA / CPCS_REPRESENTATION_DECISION_SCHEMA /
  CPCS_KNOWLEDGE_APPLICATION_CONTRACT / CPCS_STRUCTURED_INTERACTION_SCHEMA
- Translation.planning_guidance / Translation.reasoning_material /
  Translation.application_set fields
- extended interaction constructor payload (roles, phases, projection,
  state_after, recovery, world_response)
- cpcs.knowledge.apply.inspect op + doctor knowledge_application line
- any test_ka1_*.py file
- CPCS_KNOWLEDGE_APPLICATION_FIXTURES / CPCS_KA1_ACCEPTANCE artifacts

## File ownership

- Bridge core: `cpcs_knowledge_application.py` (WP-2/3/4, sequential waves)
- Structured semantics: `cpcs_typed.py` + KA-1 schemas (WP-6 owns cpcs_typed.py)
- Integration: `reasoning_treatment.py` (WP-5), `service.py` +
  `cpcs_guided_handlers.py` (WP-8)
- Validation: `ka1_fixtures.py` (WP-7), `ka1_acceptance.py` (WP-9), KA-1
  acceptance/report artifacts (WP-9)
