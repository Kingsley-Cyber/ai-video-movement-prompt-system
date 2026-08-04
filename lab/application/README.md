# CPCS application facade

This is the stable client boundary over the existing CPCS runtime. One service owns
operation names, validation, permissions, and response envelopes. CLI, MCP, HTTP, guided, and
advanced clients only translate transport input into that service.

## Local command

```bash
./bin/cpcs status
./bin/cpcs intent.normalize <<'JSON'
{"text":"Create a restrained scene where she realizes he is lying"}
JSON
./bin/cpcs intent.context <<'JSON'
{"text":"Show how this device works in a clear educational video","token_budget":12000}
JSON
```

Every call returns `cpcs.application_response/1.0` under application policy 1.6. Inputs are the operation's `arguments` object;
use `./bin/cpcs --list` to inspect the chat-safe catalog.

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

`production.prepare` owns the ordinary-language path through intent, context, canonical score,
provider build, and atomic materialization under ignored `work/application/` state:

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
cpcs record.render --role curator --input work/experiment-receipt-a.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Record this reviewed verified render"
cpcs record.render --role curator --input work/experiment-receipt-b.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Record this reviewed verified render"
cpcs reflect.rebuild --role operator
```

`experiment.prepare` resolves application build IDs internally, validates every build byte and
manifest, and proves whether an isolated pair differs on exactly one canonical control. It returns
`cpcs.experiment_flight_preparation/1.0`; it does not write authority. `experiment.seal` is the only
public flight writer and exact retries are idempotent. Changed bytes under the same flight ID are
rejected. Each `record.render` receipt still binds the build, render artifact, compliance report,
metric, and human review before reflection can influence later queries.

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
```

`measure.pose.prepare` hashes the exact video and MediaPipe Tasks model. `measure.pose.run` decodes
only the authorized interval, calls the detector once per selected frame, tracks actors
deterministically, and writes raw frames plus `cpcs.measurement_batch/1.0` under ignored `work/`.
`record.measurement` is the only application operation that admits that reviewed batch into the
append-only measurement store. `measure.normalize` projects selected immutable IDs through the
existing Video Observation Graph observation contract. `analyze.cascade` then fuses those IDs with
source-bounded Pegasus evidence and optionally reverse-resolves one canonical score.

The offline Layer O canary in `tests/test_universal_acceptance.py` joins this measurement path with
authorized folder extraction, reviewed promotion, current-index rebuild, ordinary-language score
and build preparation, journaled rendering, Pegasus score compliance, deterministic per-hand 2D
curvature, immutable experiment recording, and evidence-cited later retrieval. It uses fake
provider and detector clients, and it repeats both upload and score-compliance analysis without a
second provider call, so it proves contract and interruption-replay integration rather than live
model quality.

## MCP

Run the newline-delimited JSON-RPC stdio server:

```bash
python3 -m lab.application.mcp --role chat
```

It implements `initialize`, `tools/list`, and `tools/call`. The default catalog contains status,
intent, context, reason, score, and non-submitting build tools. Staging, derived, curated, and
immutable operations are absent unless the server process starts with a sufficient role.

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
| `operator` | chat operations plus local context profiles, extraction, local measurement candidates, analysis, materialized builds, render jobs, verification, experiment preparation, distillation, review, reflection | staging, derived, operational, or explicitly authorized external calls |
| `curator` | all operations plus promotion, experiment sealing, measurement admission, source cascade, and render evidence | curated or immutable, only with request-bound authorization |

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
