# KA-1 TEST STATE

## Tests run (KA-1 completion session)

All commands from repo root; hermetic tests run with
CPCS_FROZEN_RUNTIME_PATH UNSET.

COMMAND: python3 -m unittest lab.application.tests.test_ka1_schemas -q
RESULT: PASS (10 tests, hermetic)

COMMAND: python3 -m unittest lab.application.tests.test_ka1_structured_interaction -q
RESULT: PASS (5 tests, hermetic)

COMMAND: python3 -m unittest lab.application.tests.test_ka1_principle -q
RESULT: PASS (8 tests, hermetic)

COMMAND: python3 -m unittest lab.application.tests.test_ka1_representation -q
RESULT: PASS (8 tests, hermetic)

COMMAND: python3 -m unittest lab.application.tests.test_ka1_application_set -q
RESULT: PASS (8 tests, hermetic)

COMMAND: python3 -m unittest lab.application.tests.test_ka1_adapter -q
RESULT: PASS (6 tests, hermetic)

COMMAND: python3 -m unittest lab.application.tests.test_ka1_mcp -q
RESULT: PASS (4 tests: 2 hermetic + 2 real-runtime MCP subprocess)

COMMAND: python3 -m unittest lab.application.tests.test_ka1_fixtures -q
RESULT: PASS (7 tests: 6 hermetic + 1 real-runtime smoke, 3 fixtures x 2
deterministic runs, ~72s with CPCS_FROZEN_RUNTIME_PATH set)

COMMAND: python3 -m unittest lab.application.tests.test_reasoning_treatment_surface
         lab.application.tests.test_cpcs_typed_knowledge_coverage
         lab.application.tests.test_tc2_residual_closure
         lab.application.tests.test_deliberation_surface
         lab.application.tests.test_guided_product_surface -q
RESULT: PASS (91 tests) — pre-KA regression group, semantics unchanged

COMMAND: python3 -m lab.application.ka1_acceptance
RESULT: PASS — 10/10 gates, CPCS_KA1_ACCEPTANCE_v0.1.json written. Includes
full application suite (174+ tests), compiler suite, second-brain suite,
artifact validation, decision-policy check, D4 probe, doctor/MCP check, and
env-gated real-runtime smoke (all green).

COMMAND: python3 lab/scripts/validate_repo.py
RESULT: GATE GREEN after sync_repo --fix (derived repository map regenerated
for the new KA-1 files; committed in the release commit).

## Real-runtime state

CPCS_FROZEN_RUNTIME_PATH=/Users/king/Downloads/Additional/Runtime was used
for: real MCP tools/list + cpcs.knowledge.apply.inspect call, real-runtime
bridge smoke (3 fixtures x 2 runs, deterministic set hashes), and the
real-runtime fixture decision mixes recorded in
KA1_KNOWLEDGE_APPLICATION_REPORT.md §3.

Real-runtime decision mixes (100 retrieved records per intent, 0 unknowns):
COMBAT 4 COMPOSITE / 15 CONTROL / 45 PLANNING / 35 NON_EXECUTABLE / 1
VERIFICATION; ECOMMERCE 3/14/49/33/1; COOKING 6/17/43/31/3.
