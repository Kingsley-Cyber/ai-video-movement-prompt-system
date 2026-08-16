# KA-1 TEST STATE

## Tests run this session

This session was the KA-1 planning/handoff session. NO KA-1 tests exist yet,
so none were run.

Prior-session evidence (for context only — these were run in the RQ-1 / BOOT-1
sessions, NOT this session):

COMMAND: python3 -m unittest lab.application.tests.test_reasoning_treatment_surface
         lab.application.tests.test_cpcs_typed_knowledge_coverage
         lab.application.tests.test_tc2_residual_closure
         lab.application.tests.test_deliberation_surface
         lab.application.tests.test_guided_product_surface -q
RESULT: PASS (hermetic) — recorded in RQ-1 acceptance

COMMAND: python3 -m unittest discover -s lab/application/tests -q
RESULT: PASS — recorded in RQ-1/BOOT-1 acceptance

COMMAND: python3 -m unittest lab.application.tests.test_product_mcp_golden -q
RESULT: PASS (REAL-RUNTIME + MCP SUBPROCESS, env-gated with
        CPCS_FROZEN_RUNTIME_PATH=/Users/king/Downloads/Additional/Runtime)

COMMAND: python3 -m unittest lab.application.tests.test_bootstrap_surface -q
RESULT: PASS (HERMETIC + REAL-RUNTIME + MCP SUBPROCESS, env-gated)

This session (water-duel repair demo, pre-KA):
- DiscrepancyPacket build: PASS (status CONTRADICTED)
- cpcs.repair.plan via real runtime: PASS (RepairControlPlan produced:
  66 strengthen / 34 add, lineage generation_v1->repair_v1->v2, 0 unsupported)
- compile_build of revised build: FAILED first (score_id integrity caught
  post-resolution mutation in handler_repair_plan)
- fix applied to handler_repair_plan; re-run was ABORTED by the user before
  completion. Post-fix verification NOT completed.

## Tests not yet run

- All test_ka1_*.py suites (do not exist yet).
- Regression group from 00_MASTER_BRIEF.md §5 (must be re-run after any KA-1
  change):
  python3 -m unittest lab.application.tests.test_reasoning_treatment_surface
  lab.application.tests.test_cpcs_typed_knowledge_coverage
  lab.application.tests.test_tc2_residual_closure
  lab.application.tests.test_deliberation_surface
  lab.application.tests.test_guided_product_surface -q
- Full application suite:
  python3 -m unittest discover -s lab/application/tests -q
- Real MCP golden (env-gated):
  python3 -m unittest lab.application.tests.test_product_mcp_golden -q
- Bootstrap suite:
  python3 -m unittest lab.application.tests.test_bootstrap_surface -q

## Real-runtime state

CPCS_FROZEN_RUNTIME_PATH=/Users/king/Downloads/Additional/Runtime was used
successfully this session (real-runtime) for the repair demo retrieval/plan.
HERMETIC, REAL-RUNTIME, and MCP SUBPROCESS results are distinguished above
where applicable. KA-1 hermetic tests must run with the env var UNSET.
