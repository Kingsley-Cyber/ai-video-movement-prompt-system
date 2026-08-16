# KA-1 Dependency + Parallelization Map

```
WP-1 schemas ──────────────┐
                            ├─> WP-2 principle engine ─┐
WP-6 structured interaction ┘                          ├─> WP-4 application set ─┐
                           WP-3 representation engine ─┘                         ├─> WP-5 adapter ─┐
                                                                                 │                 ├─> WP-7 fixtures ─┐
                                                                                 └─> WP-8 mcp/doctor ─┘                 ├─> WP-9 accept/commit
```

## Parallel waves

- **Wave 1 (parallel, no interdeps):** WP-1, WP-6
- **Wave 2 (parallel):** WP-2, WP-3
- **Wave 3:** WP-4
- **Wave 4 (parallel):** WP-5, WP-8
- **Wave 5:** WP-7
- **Wave 6:** WP-9 (single owner, release discipline)

## File ownership (one owner per file — no two WPs write the same file)

- `lab/application/cpcs_knowledge_application.py` — WP-2, WP-3, WP-4 (one
  module, three sequential owners: agree by following the dataclass/function
  names in the briefs; merge conflicts avoided by wave ordering)
- `lab/compiler/cpcs_typed.py` — WP-6 ONLY
- `lab/application/reasoning_treatment.py` — WP-5 ONLY
- `lab/application/service.py`, `cpcs_guided_handlers.py` — WP-8 ONLY
- tests: `test_ka1_*.py` per WP as named in each brief
- `lab/application/KA1_WORKPACKAGES/` — read-only for all WPs except WP-9
  (acceptance/report) and the master brief

## Cross-WP integration checks (run between waves)

- After Wave 4: `python3 -m unittest lab.application.tests.test_ka1_adapter
  lab.application.tests.test_ka1_mcp -q`
- Before Wave 6: full pre-KA regression list from 00_MASTER_BRIEF.md §5 plus
  all `test_ka1_*`.

## Definitions shared across WPs

- Hermetic = FakeBackend + FAKE_SNAPSHOT, no env, no network, deterministic.
- Real-runtime = `CPCS_FROZEN_RUNTIME_PATH` set; tests skipUnless it exists.
- "Passes" = unittest exit 0 with zero failures (skips allowed only for
  env-gated real-runtime tests).
