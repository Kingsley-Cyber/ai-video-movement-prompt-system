# Universal score operating contract

Read `../../AGENTS.md`, `../AGENTS.md`, `../registry.yaml`, and `../profiles/README.md` first. This
directory is the sole owner of the provider-neutral CPCS score and typed profile merge policy.

## Boundary

`score.py` accepts a schema-valid normalized intent, its matching read-only context bundle,
router-profile labels, optional overlays, asset references, and explicit conflict resolutions. It
returns `cpcs.universal_score/1.0`. It performs no retrieval, knowledge promotion, provider prompt
serialization, render submission, or authority-store writes.

Profiles under `lab/profiles/domain/` extend `profile://universal/video/1.0`. Existing component
profiles enter only through the deterministic adapter in `profiles.py`. No profile may add a score
field that lacks a declared merge operator in the universal profile.

## Merge laws

- Merge operators are closed and field-specific. Generic recursive merge is forbidden.
- Profile and overlay input order cannot affect the result.
- Hard locks survive later precedence scopes.
- `reject_on_conflict` removes the disputed value until an explicit resolution selects one option.
- Every resolved field retains its candidates, winning source, operator, reason, and source refs.
- Provider-specific requests and prompts cannot enter the universal score.

## Commands

```bash
python3 -m lab.compiler.score validate
python3 -m lab.compiler.score resolve-context work/intent_context.json --assets work/assets.json
python3 -m lab.compiler.score resolve work/score_request.json
python3 -m unittest discover -s lab/compiler/tests -p "test_*.py"
```

Generated score requests and outputs belong under ignored `work/`. Domain profiles and schemas are
versioned repository configuration and require the root validation gate before commit.
