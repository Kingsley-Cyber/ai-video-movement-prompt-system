# Universal score and provider build operating contract

Read `../../AGENTS.md`, `../AGENTS.md`, `../registry.yaml`, and `../profiles/README.md` first. This
directory is the sole owner of the provider-neutral CPCS score, typed profile merge policy,
curated-mapping-to-canonical-control translation policy, provider capability profiles, and
non-submitting provider build compilation.

## Boundary

`score.py` accepts a schema-valid normalized intent, its matching read-only context bundle,
router-profile labels, optional overlays, asset references, and explicit conflict resolutions. It
returns `cpcs.universal_score/1.0`. Gated curated mappings enter only through hash-bound records in
`control_translations.yaml`; mappings without an active translation receive an explicit disposition
and cannot change a canonical field. The resolver performs no retrieval, knowledge promotion,
provider prompt serialization, render submission, or authority-store writes.

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
- A translation must name its source mapping and concept, pin the mapping hash, target a declared
  field and operator, state preconditions, loss, limitations, and verification, and preserve all
  source references in field provenance.

## Commands

```bash
python3 -m lab.compiler.score validate
python3 -m lab.compiler.score resolve-context work/intent_context.json --assets work/assets.json
python3 -m lab.compiler.score resolve work/score_request.json
python3 -m unittest discover -s lab/compiler/tests -p "test_*.py"
```

Generated score requests and outputs belong under ignored `work/`. Domain profiles and schemas are
versioned repository configuration and require the root validation gate before commit.

## Provider build boundary

`build.py` accepts only a schema-valid, identity-valid, ready canonical score plus explicit build
settings and score-bound asset bindings. It negotiates those controls against the selected profile
under `providers/`, then writes exactly eight artifacts: the canonical score, provider request,
prompt, reference instructions, capability report, loss report, verification plan, and hash-bound
manifest. It never submits a network request, retrieves an artifact, mutates the score, or writes a
knowledge authority store.

- Every canonical control receives exactly one capability disposition.
- Prompt lines copy canonical paths and values without adding directing knowledge.
- Evaluation-only and unsupported controls remain explicit in verification or loss records.
- Prompt overflow cannot drop a hard lock; the build fails instead.
- `enhancePrompt` remains disabled so the provider cannot silently expand the canonical request.
- Capability claims carry official source URLs and change only through reviewed profile updates.
- `block_hashes` stays explicitly empty while controls project directly from the score; legacy prompt
  blocks cannot enter a build without a future governed selector and canonical-control trace.
- The output directory must be empty, and a successful compile writes all eight artifacts.

Build commands:

```bash
python3 -m lab.compiler.build validate
python3 -m lab.compiler.build compile work/build_request.json --output-dir work/build
python3 -m unittest lab.compiler.tests.test_build
```

`provider_request.json` is a transport payload, not authorization to submit it. Provider credentials,
submission, polling, artifact retrieval, and immutable render recording belong to the later render
execution boundary.
