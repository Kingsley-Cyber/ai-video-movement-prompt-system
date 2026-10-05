# CPCS application facade

This is the stable client boundary over the existing CPCS runtime. One service owns
operation names, validation, permissions, and response envelopes. CLI, MCP, HTTP, guided, and
advanced clients only translate transport input into that service.

Graph operators use `cpcs.graph.projection.plan`, `.status`, `.sync`, and `.parity`. Planning reads
Git only. Synchronization requires exact request-bound authorization and reads credentials only from
the process environment. Parity compares complete bounded `cpcs.reason` results while Python retains
selection, relevance, conflict, prerequisite, and gap policy. Arbitrary Cypher is not exposed.

## Agent bootstrap

An agent can ask the shared service how to operate this repository for one task:

```bash
./bin/cpcs agent.brief <<'JSON'
{
  "task": "Analyze an authorized video with Pegasus, keep the API key safe, and return natural-language, YAML, JSON, and XML summaries",
  "role": "operator"
}
JSON
```

`cpcs.agent.brief/1.0` returns a plain-language brief and a typed machine plan. It selects the
smallest relevant owner-file set, verifies every recommended operation against the live catalog,
marks unavailable roles and exact-authorization stops, and binds the result to hashes of the routed
repository files. The agent method uses tool discovery, task-conditioned routing, bounded evidence,
typed plan-act-observe-verify steps, epistemic separation, and replay checks. It does not grant a
role or write authority.

For TwelveLabs work, the brief names `TWELVE_LABS_API_KEY` but never reads its value. Credentials
must enter the provider process through the environment, preferably from an OS keychain or secret
manager. They do not belong in prompts, MCP or CLI arguments, job files, logs, telemetry, tests, or
commits. The same output explains how natural language, canonical JSON, YAML, and XML divide work:
JSON owns semantics; the other formats are labelled, loss-accounted projections.

## Local command

```bash
./bin/cpcs status
./bin/cpcs intent.normalize <<'JSON'
{"text":"Create a restrained scene where she realizes he is lying"}
JSON
./bin/cpcs intent.context <<'JSON'
{"text":"Show how this device works in a clear educational video","token_budget":12000}
JSON
./bin/cpcs strategy.compile <<'JSON'
{"text":"Create a restrained scene where she realizes he is lying","minimum_status":"partial"}
JSON
```

Every call returns `cpcs.application_response/1.0` under application policy 1.27. Inputs are the operation's `arguments` object;
use `./bin/cpcs --list` to inspect the chat-safe catalog.

## Evaluator stability

Before calibration or held-out evidence can support release qualification, an operator runs
`cpcs.qualification.stability.evaluate` with two versioned evaluator identities, source-bound human
calibration scores, the exact candidate-optimization manifest, and held-out cases excluded from
that optimization set. The deterministic release owner reports evaluator error, drift, change-score
disagreement, sign disagreement, and recursive optimization collapse. It stores canonical request
and report bytes under ignored mode-`0600` work state and replays them exactly through
`cpcs.qualification.stability.inspect`.

A local pass is not release authority. The report is eligible only from a clean source revision,
and separately trusted external calibration and held-out attestations must bind the report, its
canonical request, and every gate-relevant suite, evaluator, case, human-review, evaluator-output,
and optimization artifact hash. Omission of any declared byte fails closed. The same 64-item
external-evidence limit bounds the complete closure before evaluation or qualification.

Add `--telemetry work/telemetry/application.jsonl` to CLI, MCP, or HTTP processes for content-free
operation timing. Authorized calls retain their authorization ID without retaining prompts or
evidence. Release policy caps context requests at 50,000 tokens, external evidence at 64 items,
HTTP bodies at 4 MiB, one provider build at 32 generated seconds, one analysis request at 600
seconds, one provider batch at 16 items, and one render timeout at 7,200 seconds.

## Local user and project context

The local single-user release can retain typed score overlays without adding preferences to the
research second brain. Profiles live in a mode-`0600` SQLite database under ignored
`work/application/contexts/` state. Each revision carries a content hash, prior-revision hash,
bounded validity interval, and canonical-score source reference. Values must target declared score
fields; provider requests, prompts, media bytes, credentials, and arbitrary metadata are rejected.

```bash
cpcs context.profile.put --role operator --input work/context-profile.json
cpcs context.profile.get --role operator --input work/context-profile-get.json
cpcs context.profile.list --role operator --input work/context-profile-list.json
```

`score.build` and `production.prepare` accept `context_profile_ids` plus an exact `context_as_of`.
Project profiles are accepted only when their stored project ID matches the requested production
project. Inline scene, shot, event-lock, and explicit-correction overlays retain their declared
precedence. Every access prunes expired revisions under the 30-day local retention policy. Deleting
all revisions uses `context.profile.delete` and requires authorization bound to that exact ID.

This is an operating-system-account boundary with filesystem permissions, not encrypted or
authenticated multi-user storage.

## Guided production path

`production.prepare` owns the ordinary-language path through intent, context, governed reasoning
policy, provider-neutral directing strategy, canonical score, provider build, and atomic
materialization under ignored `work/application/` state:

```bash
cpcs production.prepare --input work/production-request.json
cpcs render.create --role operator --input work/render-create.json
cpcs render.run --role operator --input work/render-run.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Approve this exact provider submission"
cpcs render.show --role operator --input work/render-show.json
cpcs verify.asset.prepare --role operator --input work/verification-asset.json
cpcs analyze.run --role operator --input work/verification-upload.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Upload this exact rendered artifact for verification"
cpcs verify.analysis.prepare --role operator --input work/verification-analysis.json
cpcs analyze.run --role operator --input work/verification-analyze.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Analyze this exact artifact against its score criteria"
cpcs verify.run --role operator --input work/verification-request.json
```

`verify.asset.prepare` validates the render bytes and creates the exact TwelveLabs upload job.
After upload, `verify.analysis.prepare` creates a Pegasus job closed to the build's semantic metric
and target pairs. `verify.run` converts its normalized observations into the evidence bundle without
caller-authored mapping. `analyze.run` accepts one of the seven existing TwelveLabs surface-job
contracts. Its first successful call writes a content-bound completion receipt over the job,
normalization identity, returned result, request, response, and normalized artifacts. An exact retry
validates and returns those saved bytes without creating a provider client. Changed content,
artifact tampering, or an incomplete prior attempt fails before provider contact. Provider analysis,
render submission, cancellation, and manual submission reconciliation require exact request-bound
authorization. Preparation, job registration, status, event inspection, and verification do not
contact a provider.

`analyze.atomic.prepare` is the no-spend planning boundary for full video deconstruction. It binds
an existing exact-byte asset registration to fixed `fast`, `standard`, or `research` coverage,
optional `ugc`, `product`, `anime_vfx`, or `render_qc` lenses, a complete authorized interval, and
an explicit one-to-three-worker limit. The response reports the exact profile list and provider-call
count and returns the existing cascade contract. The planner writes no authority and calls no
provider. Authorized `analyze.cascade` execution reuses per-profile completion receipts, so an exact
replay cannot silently issue the same provider calls again.

For paired reference/candidate work, `cpcs.video.compare.prepare` builds both atomic plans before
provider contact and rejects a pair whose combined call count exceeds the request's fixed maximum.
`advance` runs one operational-only cascade, local measurement, or verifier step at a time and
saves its child receipt before changing state. The two VOGs remain separate, and the completed
report is operational evidence rather than an immutable observation or research proposal.

```bash
cpcs video.compare.prepare --role operator --input work/video-comparison/prepare.json
cpcs video.compare.status --role operator --input work/video-comparison/status.json
cpcs video.compare.advance --role curator --input work/video-comparison/advance.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Advance this exact paired comparison step"
cpcs video.compare.inspect --role operator --input work/video-comparison/inspect.json
```

## Journaled render-to-evidence workflow

An agent that must carry one sealed experiment arm through generation and evidence admission should
start with `cpcs.agent.brief`, then use the five `cpcs.workflow.render.*` operations. The workflow
binds the sealed flight arm, materialized build, output artifact, provider limits, optional pose
measurement, and required metrics into one content-derived ID. Preparation performs no provider
call and changes no authority store.

```bash
./bin/cpcs agent.brief <<'JSON'
{"task":"Run and resume a journaled end-to-end render-to-evidence workflow","role":"curator"}
JSON
./bin/cpcs workflow.render.prepare --role operator --input work/workflows/prepare.json
./bin/cpcs workflow.render.status --role operator --input work/workflows/status.json
./bin/cpcs workflow.render.advance --role curator --input work/workflows/advance.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Advance this exact persisted workflow step"
```

Every status response identifies one exact `next_step_hash`. The caller authorizes that hash, advances
one step, and inspects status again. A process interruption after a child result is saved reuses that
receipt instead of executing the child again. If provider submission was ambiguous, status exposes
the existing reconciliation action. Verification stops at `awaiting_review`; the agent cannot invent
human feedback. `workflow.render.review` receives the exact statement and source-spanned reviewed
normalization, after which authorized advances record one immutable run. `workflow.render.cancel`
uses the existing runtime cancellation policy and preserves a terminal audit trail.

This workflow does not create another compiler, provider adapter, verifier, evidence authority, or
learning path. `cpcs.experiment.accept` remains the separate all-arm gate for controlled reflection.

## Local graphical client

Launch the installed single-user interface with:

```bash
cpcs-ui
```

The command prints and opens one single-use bootstrap URL. The browser receives an HttpOnly,
SameSite session cookie and a separate CSRF token; POST requests also require an exact loopback
Origin. The interface contains three presentation-only views over the shared service:

- Guided intent review, profile/conflict inspection, local reference staging, canonical score,
  and provider-build preparation.
- Advanced score overlays, conflict resolutions, and provider asset bindings validated by the
  compiler-owned contracts.
- The role-filtered public operation catalog plus journaled render shortcuts. Operations with an
  external or authority side effect require an explicit reason and exact approval; the server
  derives the authorization from the local operating-system account and request hash.

JPEG, PNG, MP4, MOV, and WebM references are signature checked and limited to 32 MiB each. Their
exact bytes live mode `0600` under the ignored UI session workspace and are deleted when the UI
process exits cleanly. Abandoned session workspaces are pruned after the release policy's 30-day retention
boundary when the next UI process starts. A local upload becomes score metadata only. A provider
binding still requires the provider's admitted external URI.

## Controlled experiment path

Verified builds can enter controlled learning without a hidden flight-construction step:

```bash
cpcs experiment.prepare --role operator --input work/experiment-prepare.json
cpcs experiment.seal --role curator --input work/experiment-seal.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Seal this exact build-bound experiment"
cpcs record.testimonial.capture --role curator --input work/testimonial-capture-a.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Capture this exact authorized director statement"
cpcs record.testimonial.review --role curator --input work/testimonial-review-a.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Admit this reviewed source-spanned normalization"
cpcs testimonial.inspect --role operator --input work/testimonial-inspect-a.json
cpcs experiment.accept --role curator --input work/accepted-experiment.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Accept every complete arm and run deterministic reflection"
```

`experiment.prepare` resolves application build IDs internally, validates every build byte and
manifest, and proves whether an isolated pair differs on exactly one canonical control. It returns
`cpcs.experiment_flight_preparation/1.0`; it does not write authority. `experiment.seal` is the only
public flight writer and exact retries are idempotent. Changed bytes under the same flight ID are
rejected. `record.testimonial.capture` verifies the selected artifact bytes and stores the exact
UTF-8 statement. `record.testimonial.review` accepts only exact source spans, closes normalizer
fields, and marks attribution as unverified. Corrections supersede append-only records and
`testimonial.inspect` returns both versions plus the current heads. `experiment.accept` receives
all arm receipts together. It rejects partial flights, inconclusive verification, and any arm that
lacks a current reviewed testimonial. It preflights every receipt before immutable admission,
checkpoints an ignored recovery cursor, invokes the existing reflector, records the derived diff
and evidence-cited query traces, and stages typed unreviewed improvement candidates. Exact replay
returns the same immutable orchestration receipt. Curated knowledge is hashed before and after and
must remain unchanged. `record.render` and `reflect.rebuild` remain lower-level compatibility and
diagnostic operations; agents should use the accepted-experiment gate for automatic learning.

## Reference measurement path

The local pose lane uses the same service boundary and never promotes extraction output by itself:

```bash
cpcs measure.pose.prepare --role operator --input work/pose-prepare.json
cpcs measure.pose.run --role operator --input work/pose-run.json
cpcs record.measurement --role curator --input work/measurement-record.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Admit this reviewed exact-byte measurement batch"
cpcs measure.normalize --role operator --input work/measurement-normalize.json
cpcs analyze.cascade --role curator --input work/source-cascade.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Run this exact external cascade and append its semantic evidence"
cpcs verify.reference.compare --role operator --input work/reference-candidate-comparison.json
cpcs verify.reference.roundtrip --role operator --input work/reference-round-trip.json
```

`measure.pose.prepare` hashes the exact video and MediaPipe Tasks model. `measure.pose.run` decodes
only the authorized interval, calls the detector once per selected frame, tracks actors
deterministically, and writes raw frames plus `cpcs.measurement_batch/1.0` under ignored `work/`.
`record.measurement` is the only application operation that admits that reviewed batch into the
append-only measurement store. `measure.normalize` projects selected immutable IDs through the
existing Video Observation Graph observation contract. `analyze.cascade` then fuses those IDs with
source-bounded Pegasus evidence and optionally reverse-resolves one canonical score.

After a generated artifact is re-extracted with the same detector settings,
`verify.reference.roundtrip` binds that generated batch to the exact runtime artifact and compares
explicitly mapped source and generated actors over caller-selected joints. The content-addressed
operational report includes phase-aligned trajectory similarity, translation-aligned RMSE,
path-length ratio, duration error, declared thresholds, and the detector's 2D limitations. It does
not promote either batch, infer actor correspondence, or claim motion-capture truth.

When two authorized local videos exist before a build-bound round trip, use
`verify.reference.compare`. Its strict request binds both media hashes, optional ASR and pose
artifact hashes, explicit actor mapping, thresholds, and separate review lanes. The operation
detects cuts, compares normalized edit timing, speech pace, pauses, and selected image-space motion,
then writes a deterministic report and reference-left/candidate-right contact sheet under ignored
work state. Derived control targets remain unreviewed operational candidates.

The offline Layer O canary in `tests/test_universal_acceptance.py` joins this measurement path with
authorized folder extraction, reviewed promotion, current-index rebuild, ordinary-language score
and build preparation, journaled rendering, Pegasus score compliance, deterministic per-hand 2D
curvature, source-versus-generated pose round-trip comparison, immutable experiment recording, and
evidence-cited later retrieval. It uses fake
provider and detector clients, and it repeats both upload and score-compliance analysis without a
second provider call, so it proves contract and interruption-replay integration rather than live
model quality.

## MCP

Run the newline-delimited JSON-RPC stdio server through the stable checkout launcher:

```bash
./bin/cpcs-mcp --role chat
```

It implements `initialize`, `tools/list`, and `tools/call`. MCP initialization tells an unfamiliar
agent to call `cpcs.agent.brief` first. The default catalog contains the agent
brief, status,
intent, context, reason, score, and non-submitting build tools. Staging, derived, curated, and
immutable operations are absent unless the server process starts with a sufficient role.

### Local coding harnesses

Claude Code, Codex, Hermes Agent, Cursor, and similar local coding harnesses should keep their own
filesystem, terminal, Git, browser, and editor tools. CPCS MCP adds only the CPCS domain surface:
intent, knowledge, research, compilation, Pegasus, rendering, verification, and evidence. This
prevents a duplicate shell or filesystem authority from appearing inside CPCS.

Point any stdio-capable harness at the absolute path to `bin/cpcs-mcp`. A read-only Hermes entry is:

```yaml
mcp_servers:
  cpcs:
    command: "/absolute/path/to/CPCS/bin/cpcs-mcp"
    args: ["--role", "chat"]
    connect_timeout: 10
    supports_parallel_tool_calls: false
```

Start with `chat`. Use `operator` only for a local coding-agent session that needs staging,
operational builds, research sessions, or provider jobs. External calls still require authorization
bound to the exact operation and arguments. Curator authority stays separate.

Hermes Agent v0.20.0 was qualified locally on 2026-08-04 with the then-current operator catalog.
`hermes mcp test cpcs` connected in 301 ms and discovered 45 MCP-exposed tools. A real Qwen 3.7 Max Hermes turn then
called `mcp__cpcs__cpcs_agent_brief` and returned the exact `cpcs.agent_brief/1.0` schema, brief ID,
and repository-orientation plus TwelveLabs workflow selection. This proves native-agent to MCP to
application-service execution. The current catalog has 81 registered operator operations, of which
79 are MCP exposed, including paired video comparison, atomic analysis planning, Research Delta,
brain maintenance, and video reasoning; those added operations pass the same local MCP
contract tests but have not repeated the external Hermes version canary. This does not qualify other
harness versions or live provider output.

For credentialed provider calls, use a local secret launcher or harness secret provider that loads
`TWELVE_LABS_API_KEY` into the MCP subprocess environment. Never paste the key into a harness YAML
file. `CPCS_PYTHON` can select a local virtual-environment interpreter without changing the launcher.

The operator catalog exposes `cpcs.polymath.retrieve` and `cpcs.context.enrich`. Both are marked
open-world and require authorization bound to the exact arguments. Direct retrieval returns one
typed untrusted packet for context or distillation. Enrichment first runs local context retrieval,
makes no network call when coverage is complete, and otherwise retrieves only the broker's exact
gap query before rebuilding the same token-budgeted context contract. Neither operation promotes
or stages knowledge.

The same operator catalog exposes a resumable research-extraction sequence for an external LLM
connected through MCP:

```text
cpcs.research.source.register
→ cpcs.research.source.inspect
→ cpcs.research.packet.list / cpcs.research.packet.read
→ cpcs.research.extraction.submit
→ cpcs.research.coverage.inspect
→ cpcs.research.proposals.list / cpcs.research.proposals.validate
→ cpcs.research.source.units.admit with exact curator authorization
→ cpcs.research.distillation.run
→ cpcs.research.placement.plan with the exact proposed durable-ID assignments
→ cpcs.research.placement.inspect
→ cpcs.research.delta.prepare / cpcs.research.delta.inspect when implementation impact is in scope
→ cpcs.research.promotion.prepare
```

Registration binds exact source bytes, retrieval metadata, the external agent and model, prompt
hash, schema versions, and distillation policy. Packet results are accepted one at a time. Exact
retries replay; changed output for a captured packet and source mutation after registration fail
closed. The completed LLM response and source bundle remain mode `0600` under ignored
`work/application/research_sessions/`. Source-unit admission accepts only that completed,
hash-verified bundle and appends its exact passages to the immutable local registry. Distillation
writes staging only. Placement then binds each admitted proposal to one exact durable identity,
registered ontology class, typed parent and bridge set, control namespace, metric set, source-unit
set, derived-index invalidation scope, and incremental graph-projection delta. Exact replay returns
the same content-addressed plan. The separate curator-only `cpcs.curate.promote` operation remains
the sole promotion boundary and fails closed unless typed proposal evidence and the current exact
placement plan resolve to their registries.

Read-only clients use `cpcs.source.status` to inspect local closure and `cpcs.source.resolve` to
dereference concept or source-unit IDs into bounded, hash-verified passages. `cpcs.context.get`
automatically includes selected local passages within its existing token budget and returns an exact
local source-answer disposition when the graph reports an unanswered slot. Quarantined Polymath or
web references are not evidence until a completed source bundle is admitted.

Before traversing a domain term, clients may call `cpcs.terminology.resolve`. Exact registered
identifiers and uniquely supported context resolve deterministically. An unresolved homonym returns
a closed agent task and causes `cpcs.reason` to pause rather than guess. An operator agent may inspect
exact source units, call `cpcs.terminology.propose` with one returned sense, then verify it through
`.inspect` and pass the proposal ID to `cpcs.reason`, `cpcs.context.get`, `cpcs.intent.context`, or the
matching proposal ID entry in `cpcs.research.placement.plan`. Extraction and placement expose their recomputed terminology
controls, while directing-strategy and score admission reject unresolved or stale handoffs. The
proposal is staging-only, query-bound, and trust-labelled as interpreted. It cannot edit or promote
the ontology registry.

Research Delta consumes only completed claim candidate IDs. The request supplies closed evidence
and change classes, scope, limitations, and proposed target categories. CPCS resolves the current
owner, affected contracts, fixed tests, allowed patch paths, source hashes, placement, and impact
paths. The resulting `cpcs.research_delta_plan/1.0` is content-addressed under mode-`0600` ignored
`work/application/research_deltas/`. It changes neither code nor any authority tier. Its patch
boundary explicitly requires a separate owner-authorized isolated implementation step.

That implementation step is now public but still non-integrating. Call
`cpcs.research.delta.patch.prepare` with one exact-hash text unified diff. The runtime rejects open
fields, binary patches, renames, deletions, unsafe paths, proposal-scope escapes, dirty or drifted
baselines, and caller-supplied commands. A curator may then authorize `.patch.execute` for the exact
content-derived execution ID. CPCS recreates or resumes a detached worktree, applies the patch with
Git hooks disabled, runs the fixed proposal tests plus `validate_repo.py` in a secret-minimized
environment, and writes hash-checked state, logs, file hashes, and a terminal receipt. Use
`.patch.inspect` to verify it and separately authorize `.patch.discard` to remove only that
worktree. None of these operations merge, push, promote, or edit the live checkout.

The MCP catalog describes closed nested packet-result and extraction-configuration inputs. Runtime
JSON Schemas reject unknown fields and closed-enum violations, validate every research result, and
recompute session, packet-result, captured-response, and completed-bundle hashes before reuse.
Legacy `cpcs.distill.prepare` and `cpcs.distill.run` remain available to local compatibility clients,
but MCP neither discovers nor invokes them. This keeps an MCP semantic worker inside the session
owner even when it guesses an older operation name.

## Local HTTP

```bash
python3 -m lab.application.http --host 127.0.0.1 --port 8765 --role chat
curl http://127.0.0.1:8765/v1/status
curl -X POST http://127.0.0.1:8765/v1/invoke \
  -H 'Content-Type: application/json' \
  -d '{"schema":"cpcs.application_request/1.0","operation":"cpcs.intent.normalize","arguments":{"text":"Casual phone product recommendation"}}'
```

The HTTP adapter has no identity provider. Operator and curator roles are therefore restricted to
loopback and are not production authorization.

## Authority profiles

| Role | Operations | Mutation |
|---|---|---|
| `chat` | status, intent, evidence context, reason, score, inline build, guided production preparation | none or ignored operational build and expiring local-context state |
| `operator` | chat operations plus local context profiles, resumable research extraction, Research Delta planning and patch capture or inspection, local measurement candidates, analysis, materialized builds, render jobs, verification, experiment preparation, distillation, review, reflection | staging, derived, operational, or explicitly authorized external calls |
| `curator` | all operations plus isolated Research Delta execution or cleanup, promotion, experiment sealing, measurement admission, source cascade, and render evidence | operational, curated, or immutable controlled effects, only with request-bound authorization |

An explicit authorization contains the operation and
`authorization_request_hash(operation, arguments)`. Changing one argument invalidates it. This is
a deliberate human-approval boundary, not a substitute for authenticated deployment security.

## Honest limits

- The wheel installs `cpcs`; `bin/cpcs` remains the repository checkout shim.
- MCP covers the tools protocol needed by CPCS; it is not yet qualified against multiple MCP hosts.
- HTTP is a loopback adapter with a bounded request body and operation quotas. It has no TLS,
  authenticated identity, sessions, or multi-user rate limiting.
- The graphical client is a bounded local single-account surface. It has no TLS, remote identity
  provider, multi-user sessions, or mobile-native shell.
- Local context profiles are filesystem-permission protected and retention bounded, but not
  encrypted, remotely authenticated, synchronized, or shared across operating-system accounts.
- Live provider qualification remains a separate gap.
- A quarantined TwelveLabs attempt is never resubmitted automatically. Provider-specific remote
  reconciliation remains manual when no durable remote request ID was captured.
- The measurement extra and a PoseLandmarker model must be installed separately. Installation does
  not establish accuracy; a qualified clip and reviewed detector metrics are still required.

## Labelled directing projection

For an accepted field-bound scene, `cpcs.direct.finish` accepts build settings
`prompt_format: prose` and `prompt_layout: labelled_skeleton_v1`. A supported provider fit
materializes through the existing build owner and returns `output_dir`; default callers retain
inline builds. JSON and ordinary prose remain available. The layout never reads an oracle or
an external prompt file. `cpcs.direct.withdraw` takes `session_id`, `decision_id`, `field`
(such as `direction.FACE`) and `reason`; it preserves the capture history and reports the
missing field in the build's loss artifact. Required direction fields cannot be withdrawn.

### Kinematic plan validation

`cpcs.kinematics.validate` takes `plan` (a `cpcs.kinematic_plan/1.0` document an LLM authored in
its scratchpad) and returns a `cpcs.kinematic_report/1.0`: `pass` or `fail` with typed findings
(teleports, unexplained speed changes, support coverage and height, flight bounds, reach, swing
extent, tangent release, camera aim, density and unapproved tokens). It is read-only, deterministic
and never edits the plan; a schema-invalid plan returns an error. It checks the plan's own
coherence, not a render.

A complete directing session started with `kinematics: true` asks for a `kinematic_plan` in the
staging stack. Each validator finding returns as a `kinematic_<code>` rejection to repair; a plan
that misses the scene duration or names undeclared bodies is `kinematic_scene_mismatch`. Builds
refuse a failing plan and keep accepted plans out of prose; JSON carries them.

### Existing manual-render evidence

`cpcs.record.render` also accepts a receipt with `capture_kind: manual_render`,
`media` and `prompt_source` file identities (`path`, `sha256`, `size_bytes`),
and `feedback` rows (`speaker`: owner or Claude; `representation`: verbatim or paraphrase;
`text`, optional `context_paraphrase`). Exact curator authorization remains required.
The existing render-evidence workflow hashes both local files, reads only container facts
with verifier-owned ffprobe, and delegates append/replay to the immutable recorder.
It stores source prompt bytes with an owner-attributed binding. Route, model, seed, settings,
submission time, actual submitted text and requested frame rate remain explicit null unknowns.
Container frame rate is the exact rational reported by ffprobe, not a requested setting.
No render, analysis, sealed flight, numeric score, learning or promotion is inferred.
