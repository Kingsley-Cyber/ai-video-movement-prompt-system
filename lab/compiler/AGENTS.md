# Universal score and provider build operating contract

Read `../../AGENTS.md`, `../AGENTS.md`, `../registry.yaml`, and `../profiles/README.md` first. This
directory is the sole owner of the provider-neutral CPCS score, VOG reverse-score projection, typed profile merge policy,
curated-mapping-to-canonical-control translation policy, provider capability profiles, and
non-submitting provider build compilation.

## Boundary

`decisions.py` owns creative-stack proposal checks, accepted-decision projections into existing
overlays, scene completeness and provider-duration fit. It uses `score.py` and `build.py`;
it does not replace them. Rationale and evidence remain in the operational session ledger.
Regression cases live in `tests/test_decisions.py` and `tests/test_directing_build.py` and `tests/test_directing_quantities.py` and `tests/test_dialect_projection.py`.
Prop/hand continuity regressions live in `tests/test_prop_hand_ledger.py`. `decisions.py`
replays entity `prop_state` and action `needs`/`changes`; `build.py` checks the same declared
state before every carrier and prints carried locations in prose. The ledger is derived,
not a second score or authority. It checks declared resources only, not prose or video physics.
The complete directing path supplies per-shot camera stacks and preserves duration in
`project.duration_seconds`. Provider capability selection and canonical/prose/JSON carriers remain
in `build.py`. `providers/seedance_2_0.yaml` admits a manual text export only, sourced to official
BytePlus documentation. It is not a runtime adapter, prompt efficacy evidence, or unlimited-budget
claim; null limits and frame rate remain unknown. Manual exports cannot be submitted by the Veo adapter.

`score.py` accepts a schema-valid normalized intent, its matching read-only context bundle,
router-profile labels, optional overlays, asset references, and explicit conflict resolutions. It
returns `cpcs.universal_score/1.0`. Gated curated mappings enter only through hash-bound records in
`control_translations.yaml`; mappings without an active translation receive an explicit disposition
and cannot change a canonical field. The resolver performs no retrieval, knowledge promotion,
provider prompt serialization, render submission, or authority-store writes.

Before score resolution, the compiler selects or validates one complete
`cpcs.compiled_directing_strategy/1.0` against the exact intent and context. The canonical score
embeds that trace and binds its strategy ID and hash in provenance; the provider build manifest
binds the same pair. This proves which reasoning execution informed an output. Strategy-policy
equivalence or provider effect remains an experimental question and cannot be inferred from a
different strategy ID alone.

When the strategy cites a knowledge comparison lens, the compiler accepts only the lens-bound
context and only mapping IDs admitted by that strategy. A stale or tampered lens fails before score
resolution. The lens remains evidence selection, not canonical meaning or VOG promotion.

Both directing-strategy compilation and universal-score resolution recompute the context bundle's
canonical terminology handoff against the current ontology registry and staged source-backed
proposal IDs. A stale, tampered, or unresolved handoff fails before strategy or score admission.
Compiler code must not guess a homonym, duplicate the terminology registry, or promote a staged
selection.

Profiles under `lab/profiles/domain/` extend `profile://universal/video/1.0`. Existing component
profiles enter only through the deterministic adapter in `profiles.py`. No profile may add a score
field that lacks a declared merge operator in the universal profile.

`skeleton.py` is the build owner's opt-in `labelled_skeleton_v1` prose layout. It reads
canonical field-bound authored clauses and a text-free presentation recipe; it never reads a
prompt source file. Without a recipe it wraps at sentence boundaries. It validates bindings,
beat lengths/ranges and declared prop replay, and audits printed bytes as bound values,
authored clauses or layout. Consumed wrap spaces contribute no content bytes; generated
heading punctuation is layout. Timing is a carrier choice, not provider-adherence evidence.
Source-unspecified camera slots retain their dispositions. The champion oracle is test-only;
the structured fixture and the three `test_*skeleton*` suites prove editable values, exact
bytes, public acceptance, optional withdrawal/loss and unchanged default callers.

## Merge laws

- Merge operators are closed and field-specific. Generic recursive merge is forbidden.
- Profile and overlay input order cannot affect the result.
- Hard locks survive later precedence scopes.
- `reject_on_conflict` removes the disputed value until an explicit resolution selects one option.
- Every resolved field retains its candidates, winning source, operator, reason, and source refs.
- Provider-specific requests and prompts cannot enter the universal score.
- `reverse.py` may project typed Video Observation Graph rows only onto fields already declared by
  the universal merge-policy table. It calls the same score resolver, cannot add an ontology or
  provider request, and cannot mutate a resolved score after its content-derived ID is computed.
- A translation must name its source mapping and concept, pin the mapping hash, target a declared
  field and operator, state preconditions, loss, limitations, and verification, and preserve all
  source references in field provenance.

## Commands

```bash
python3 -m lab.compiler.score validate
python3 -m lab.compiler.score resolve-context work/intent_context.json --assets work/assets.json
python3 -m lab.compiler.score resolve work/score_request.json
python3 -m lab.compiler.reverse work/intent_context.json work/vog.json --assets work/assets.json
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

Timing is a carrier choice and is tracked (owner SD-17). `score.derive_timeline` adds a canonical
`timeline` to every score with beats: resolved only when one scene duration exists, beat orders are
1..n and complete beat lengths at or above their `min_s` fill the scene exactly (Decimal sums),
giving per-beat start/end and windows for beat-bound actions, contacts and shots; otherwise it is
unresolved with a reason. Authored beats are unchanged and no frame rate is inferred. The directing
validator rejects complete lengths that miss the scene (`beat_durations_mismatch`) or undercut a
minimum (`beat_duration_below_minimum`). Every scene build records `timing_projection` in the
capability report: carrier, layout, the timing form actually printed (`timestamps`, `lengths`,
`minimums`, `order_only`, `none`; shot-number prose prints `order_only`) and the planned schedule,
as `carrier_choice` with no adherence claim. `tests/test_timeline.py` covers both.

In complete directing, closed movement sets are always on (owner SD-19): `validate_decisions` runs
`movement_checks(require_codes=True)` for every complete-mode packet, so Effort, Shape and
connectivity slots must be admitted selections.

`kinematics.py` validates authored coordinates (owner request 2026-10-04, design in
`handoff/direct_scene/TIMING_AND_KINEMATICS.md`). An LLM writes a `cpcs.kinematic_plan/1.0`:
frame, body baselines (`hip_height_m`), hip and part tracks, support intervals using the SD-16
approved tokens, force events, contacts with approved modes, swings, and camera as position plus
`look_at`. `validate_plan` returns a `cpcs.kinematic_report/1.0` under the versioned
`cpcs-kinematics/1.1` policy; a plan may override named thresholds explicitly. Policy 1.1 adds facing
headings (0 faces +z, 90 faces +x; spins marked), relations (toward, away_from, travel) and landing
parts: `TURN_RATE`, `FACING_RELATION`, `LANDING_PART_UNDECLARED`, `LANDING_SUPPORT_MISMATCH`,
`LANDING_HEIGHT` and `LANDING_SPEED`. Checks: frame,
time order, teleport, unexplained speed change, support coverage, tokens and height, flight
bounds, forbidden-flight contradiction, contact modes and reach, swing extent, tangent release,
camera aim and density. It measures the plan, never a render, and never edits it. `check_plan`
adds input and output schema validation for the public `cpcs.kinematics.validate` operation.
`tests/test_kinematics.py` proves it on the owner's water-duel v2 (converted fixture, must fail)
and an authored v3 (must pass).

Repair loop (owner decision 2026-10-04: a deterministic validator loop, not a free-form LLM
critic). The staging pass has a required `kinematics` slot carrying `kinematic_plan`: kinematics is
always on in complete directing (owner SD-18), so a staging stack without a plan is rejected.
`validate_decisions` schema-checks every submitted plan, returns each finding as
`kinematic_<code>` and rejects `kinematic_scene_mismatch` when the plan's duration or bodies differ
from the accepted scene; the author repairs and resubmits. An accepted plan rides in the scene into
the score. `build._kinematic_status` re-validates it, refuses a failing plan
(`KINEMATIC_PLAN_FAILED`), records its status in the capability report and keeps it out of prose
as numbers; JSON carries it. The default prose carrier prints it as words instead (owner
2026-10-04): `kinematics.describe_plan` turns screen side, support and manner, landings with
parts, facing relations and force events into deterministic sentences named by the scene's cast,
placed as a `Motion plan:` line after the cast. Coordinates never print in prose; the labelled
skeleton is unchanged; the capability report records `prose_projection` (`words`, `structured`
or `none`). Proof:
`lab/application/tests/test_kinematic_directing.py`.

`prompt_layout: director_v1` (owner 2026-10-04, PLAN Slice D) is the labelled natural-language
layout for any accepted scene. `build._director_prompt` prints header blocks once (`GOAL`, `STYLE`,
`LOOK`, `CAST`, `OBJECTS`, `WORLD`, `STAGING`, `MOTION`), then each beat with its length (or its
minimum), its shots and each action's `DO`, `BODY`, `EFFORT`, `SHAPE`, `SPACE`, `FACE`, `CONTACT`,
`REACT` and `NOT` rows, then `END`, `SOUND` and the profile-derived `CONTROLS` verbatim without
their ids. It is made only from accepted canonical fields: the ask is not repeated, references
print as `BEAT n`, `SHOT n` and `DO n`, closed codes print their admitted wording, coordinates never
print, and a field with no place of its own prints beside its owner under its own name, so nothing
accepted is dropped. It requires the prose carrier. The capability report records the layout and
whether lengths or minimums were printed. The default prose carrier and `labelled_skeleton_v1` are
unchanged. Proof: `lab/application/tests/test_director_layout.py`.

The manifest's `repository_commit` is the Git revision of the checkout that holds the executing
compiler code, resolved from `REPO_ROOT`, not from the caller's data root. A fixture or project
data root may be a non-Git copy or a separate repository; its authority inputs are already
hash-bound through the concept, profile and capability hashes. If the compiler code itself is not
in a Git checkout, the build fails closed. `tests/test_build_code_revision.py` covers a non-Git
data root, a separate Git data root, and the fail-closed case.

- Every canonical control receives exactly one capability disposition.
- Prompt lines copy canonical paths and values without adding directing knowledge.
- The default prose carrier prints each beat, action, contact, shot and scene under one label
  (order number, or position when unordered; qualified with the item ID if two items share it),
  and prints every `beat`, `end_beat`, `action` and `caused_by` reference through the same label
  map, so no reference names an undeclared ID. Entities stay referenced by display name. JSON and
  the canonical score keep IDs; `tests/test_prose_references.py` covers resolution and collisions.
- In that timeline, a shot whose `beat` names a declared beat prints directly under that beat, so
  camera direction sits inside its event span; shots without a declared start beat print before
  the timeline as before. The same test file covers the placement.
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
submission, polling, and artifact retrieval belong to the render execution boundary in
`../runtime/AGENTS.md`. Score-linked compliance and repair planning belong to
`../verification/AGENTS.md`; immutable experiment recording remains a separate later boundary.

## Closed movement checks and projection

`decisions.movement_checks` validates selected performance values against the existing
second-brain catalog. Declared body chains use the owner-approved per-side anatomical
adjacency, signature departure reasons and the explicit Round 2 phase crosswalk:
preparation to preparation; initiation and stroke to execution; endstroke to contact-or-apex;
follow-through to follow-through; recuperation to recovery. Initiation precedes stroke
within execution. Uniform spacing is report-only. Effort-action recipes use Weight, Time
and Space, with Flow independent. Legacy authored fields remain unchanged without opt-in
or selected codes. `tests/test_closed_movement.py` covers these checks and retained bytes.
The build resolves selected code hashes, projects visible wording in prose and retains codes
in JSON. Its manifest binds the selected concept hashes. The optional skeleton audit's
`closed_code.bytes` is a subset of typed-bound printed bytes, excluding consumed wrap spaces;
it proves serialization, not provider efficacy. No closed selections means the existing audit
and prompt remain unchanged. Live member promotion is separate governed work.
