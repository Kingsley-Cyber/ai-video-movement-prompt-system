# CPCS Universal Video Intent System

> **AI agents:** this repo is AI-managed. Read **[`AGENTS.md`](AGENTS.md)** first — it routes every
> task to its home and carries the editing laws (anti-bloat, validation gate, commit conventions).

For the implemented runtime, second-brain internals, dependency map, current gaps, and remediation
order, read **[`ARCHITECTURE.md`](ARCHITECTURE.md)**.

> **CPCS is a universal AI video-intent generator and creative-direction compiler that turns a
> user's goal into an evidence-informed, provider-ready video production plan.**

The user describes the video in ordinary language. CPCS is intended to infer the domain, retrieve
relevant directing knowledge, resolve constraints, build one provider-neutral production score,
project that score into the selected model's controls, and verify the render. FACS, Laban, graph
traversal, research retrieval, and provider adapters are internal mechanisms rather than required
user vocabulary.

```text
user goal + user/project context + domain profiles + evidence + provider capabilities
→ normalized intent
→ source-grounded context and selected reasoning policy
→ compiled directing strategy
→ canonical video score
→ provider request and prompt package
→ render verification and learning
```

## One kernel, many video domains

CPCS uses one canonical language for intent, subjects, identity, environment, action, performance,
timing, camera, editing, audio, continuity, constraints, provider controls, and verification. Domain
profiles configure that language; they do not create separate schemas or prompt systems.

The Git-backed second brain can project its validated reasoning graph into an isolated local Neo4j
read model. NetworkX remains the default and parity oracle. The projection is incremental,
idempotent, rebuildable from Git, and reachable only through bounded CPCS operations. It is not a
second knowledge authority.

| Experience | Profile emphasis |
|---|---|
| UGC and product demonstrations | trust, claims, product interaction, phone realism, communication beats |
| Cinematic and dialogue scenes | objective, subtext, gaze, suppression, blocking, motivated camera |
| Action, dance, and anime | causality, motion phases, contacts, screen direction, timing, readability |
| Music, education, social, and custom projects | domain-specific defaults, constraints, workflows, and verification metrics |

Profiles can blend through typed precedence:

```text
universal defaults
→ domain profiles
→ user defaults
→ project profile
→ scene overrides
→ shot overrides
→ event locks
```

Conflicts remain explicit. For example, a phone-realism profile cannot silently combine deep focus
with a cinematic profile's shallow depth of field. The dominant intent resolves the conflict, or the
system asks the user which result matters more.

Automatic routing is the default:

```text
"Talking to the phone about a product"
→ UGC + product demonstration + phone realism

"Quiet realization during dialogue"
→ cinematic dialogue + restrained performance + psychological subtext

"Two rivals exchange attacks in a hand-drawn style"
→ screen action + multi-actor geography + anime stylization
```

The interface shows the detected mode so the user can accept or change it.

## Intended user output

A completed compilation produces one traceable build rather than an attractive paragraph with no
control structure:

```text
build/
├── canonical_score.json
├── provider_request.json
├── prompt.txt
├── reference_still_prompt.txt
├── capability_report.json
├── loss_report.json
├── verification_plan.json
└── build_manifest.json
```

Guided users describe a video, upload references, choose duration and platform, review the detected
intent, and render. Advanced users edit the same score's beats, performance, motion, camera, timing,
contacts, profile blend, provider realization, and verification thresholds.

## Current implementation state

The universal product contract is implemented as a working local runtime, but it is not yet an
externally qualified production service. The repository implements
the governed knowledge foundation: curated concepts, typed
reasoning, deterministic distillation, query safety, independent typed research-object search,
a curated six-policy reasoning registry with deterministic Python executors,
a read-only context bundle, experimental
evidence, media-analysis adapters, component profiles, deterministic intent normalization and
profile routing, one provider-neutral canonical score, typed domain-profile resolution,
hash-bound research-to-control translation, deterministic Veo 3.1 build compilation with explicit
capability and loss accounting, and a local journaled execution boundary that captures, resumes,
and content-hashes provider work without writing knowledge authority. A provider-neutral verifier
then prepares hash-bound render-upload and closed score-compliance jobs, converts normalized
observations into source-cited assertions, probes rendered media, and adjudicates semantic, measured, and human-review evidence,
preserves disagreements, and proposes only bounded reassertions of existing canonical controls.
Verified outputs can then enter a sealed isolated or bundled experiment through an idempotent,
hash-bound run contract. Exact human feedback is captured against verified artifact bytes before a
human or LLM proposes quote-spanned normalization; corrections append successors, and attribution
stays unverified until experiment evidence supports it. Deterministic reflection keeps bundled signals noncausal, admits causal
provider/model effects only for one-control comparisons, and exposes their artifact-linked trace to
later ranking without changing curated knowledge. The authorized `cpcs.experiment.accept` gate now
requires every isolated arm, conclusive verification, and a current reviewed testimonial before it
admits runs, invokes the existing reflector, records the derived diff and evidence-cited query
trace, and emits only unreviewed improvement candidates. Partial arms, individual renders, raw
measurements, and LLM diagnoses cannot trigger automatic learning. A shared application facade now exposes status,
intent, context, reasoning, provider-neutral strategy compilation, score, atomic build
materialization, TwelveLabs analysis, journaled
render execution, verification asset and analysis preparation, observation-to-evidence conversion,
and compliance verification through the installed `cpcs` command, MCP stdio,
loopback HTTP, headless clients, and an installed `cpcs-ui` graphical surface. The local UI uses a
single-use bootstrap, HttpOnly session cookie, CSRF and exact-Origin checks, accessible guided and
advanced views, bounded exact-byte reference staging, and the role-filtered public operation
catalog. It calls the same dispatcher and cannot assert its own authorization. Role policy hides operational and authority
tools from chat clients. External provider calls, cancellation, reconciliation, curated writes, and
immutable writes need authorization bound to the exact request.
An operator-only Polymath MCP adapter now performs authenticated live discovery and bounded search
through that same exact-authorization boundary. It emits content-hashed passages labeled as
untrusted external evidence for context or governed distillation and does not mutate authority.
An MCP-connected external LLM can now consume those passages or local research through a resumable
`cpcs.research.*` session. CPCS registers exact source bytes, exposes bounded packets, captures and
hashes one typed response per packet, validates proposals, stages them through the shared distiller,
and prepares human review. Closed runtime schemas reject unknown fields, stored packet and aggregate
responses are rehashed before reuse, and MCP cannot invoke legacy direct-batch distillation. The LLM
proposes meaning; deterministic code owns source closure, identity, placement, and staging, while
only a curator can promote repository truth.
Completed claim proposals can also enter the Research Delta boundary. CPCS binds
their exact sources and extraction hashes, resolves existing repository owners, snapshots affected
contracts, names fixed regression tests, and emits content-addressed impact and patch-boundary plans
under ignored work state. A coding agent may then capture a strict proposal-scoped unified diff.
Only a separately authorized curator call can apply it to a detached worktree and run the fixed
owner tests plus the repository gate. CPCS records hash-checked logs, replay state, a gate receipt,
and explicit cleanup. It never merges, pushes, promotes, assigns durable IDs, changes the live
checkout, or treats a passing patch as repository authority.
The same local application boundary can retain versioned user-default and project-profile overlays
in a permission-restricted SQLite store under ignored `work/` state. Profiles are limited to
declared canonical-score fields, expire within 30 days, remain separate from research authority,
and enter score provenance through revision-specific source references. This is local
operating-system-account storage, not encrypted or authenticated multi-user memory.
The same service now binds exact authorized reference-video and PoseLandmarker bytes, produces
reviewable 2D detected-track batches without authority writes, admits them only through an
explicit curator operation, normalizes selected immutable records into the Video Observation
Graph, and exposes the semantic/measurement cascade through optional reverse scoring.
One offline public-contract canary now executes the complete governed Layer O sequence from an
authorized research folder through reviewed knowledge promotion, intent and build preparation,
fake-provider rendering, fake Pegasus analysis, local pose verification, immutable controlled
evidence, reflection, and evidence-cited later retrieval. It does not substitute for live-provider,
detector-accuracy, calibration, or held-out qualification.
The supported TwelveLabs dispatcher now wraps every Assets, Analyze, Segment, Batch, Search,
Jockey, and Marengo call in a content-bound completion receipt. An exact retry returns the saved
result without provider contact; changed, tampered, concurrent, or incomplete attempts fail closed
instead of risking an automatic second charge.
Atomic video deconstruction now starts with `cpcs.analyze.atomic.prepare`, which validates an exact
registered source and emits a content-addressed `fast`, `standard`, or `research` cascade with
whole-interval coverage, explicit domain lenses, bounded concurrency, and a visible provider-call
count before any external spend. Agents discover the same workflow through `cpcs.agent.brief`.
The repository also packages an installed `cpcs` entry point, locks the core dependency graph,
runs a GitHub validation workflow, versions journal migrations, backs up authority plus live SQLite
state without overwriting, emits content-free local telemetry, and generates categorical release
reports whose external gates cannot pass without revision-bound, policy-trusted HMAC attestation
and exact verification of every supplied evidence artifact. The default evaluator registry is
empty, so a model or agent cannot self-approve production authority.
Evaluator changes now pass through `cpcs.qualification.stability.evaluate` and `.inspect`. The
release owner binds versioned evaluator identities, source-grounded human calibration, the exact
optimization set, disjoint held-out cases, thresholds, Git source state, and canonical replay. It
detects evaluator drift, human-versus-evaluator score disagreement, and the failure mode where an
optimized evaluator score rises while human held-out quality falls. A local pass is supporting
evidence only; dirty source is ineligible, and trusted external calibration and held-out evidence
must bind the exact report, canonical request, and every gate-relevant suite, evaluator, case,
human-review, evaluator-output, and optimization artifact before either release gate can pass.
Agents learn this path
from `cpcs.agent.brief` when a task mentions calibration, held-out evaluation, evaluator drift,
metric gaming, or recursive degradation.
Every versioned second-brain writer also enters one repository-wide POSIX transaction lock, so
competing local processes fail before staging, curation, immutable recording, migration, or derived
rebuild logic reads authority. Curated promotion additionally prepares hash-bound before/after
images and atomically replaces every touched store; a process killed before the commit marker is
rolled back by the next curation operation. Supported multi-file query, context, compiler, status,
reflection, graph, index, and extraction-coverage reads hold a shared POSIX snapshot transaction;
writers require the exclusive mode. Kernel ownership is released on process death. This remains a
single-host boundary and makes no distributed-lock or network-filesystem claim.
The repository gate also runs 13 labeled production-path retrieval cases across UGC, product,
education, dialogue, cinematic restraint, anime action, identity, contact, FACS, Laban, structured
formats, and research reasoning. Every required concept must be found, every named unrelated
concept must remain absent, replay must be exact, and authority bytes must remain unchanged.
Authorized Markdown, text, JSON, JSONL,
YAML, XML, and typed Polymath passages can now enter a safe, content-addressed extraction bridge
that emits bounded, reviewable candidate bundles without promoting repository knowledge. Curated
records now support deterministic current and historical validity, reciprocal replacement lineage,
and a rebuildable lexical, alias, vector, graph, source, evidence, typed research-object,
provider, experiment, and video index catalog.

Authenticated remote deployment, distribution-hash locks,
real-clip measurement qualification, Tier 3 motion solving,
live provider qualification, and provider-specific reconciliation of quarantined remote attempts
remain implementation gaps. Their
dependency order and acceptance canaries live in
[`ARCHITECTURE.md`](ARCHITECTURE.md).

## Repository map

| Path | What it is |
|---|---|
| `ARCHITECTURE.md` | Product contract, actual runtime, gap matrix, ownership, and remediation order |
| `SKILL.md` | Current UGC authoring specialization, not the universal runtime |
| `lab/second_brain/` | Safe research extraction, curated knowledge, typed graph reasoning, evidence, context, and distillation |
| `lab/compiler/` | One universal-score resolver, typed merge policy, research-control translations, provider capabilities, and non-submitting build compiler |
| `lab/runtime/` | Journaled provider execution, recovery, and transport-only generation adapters |
| `lab/verification/` | Local media compliance, evidence-lane conflict handling, and bounded repair planning |
| `lab/application/` | Shared application service plus CLI, MCP, HTTP, and the local guided/advanced graphical client |
| `cpcs-ui` | Installed loopback-only graphical workflow over the same application service |
| `lab/release/` | Local release policy, backup/restore, migrations, security, telemetry, and qualification |
| `bin/cpcs` | Repository-local stable command over the application service |
| `bin/cpcs-mcp` | Checkout-relative stdio launcher for Hermes, Claude Code, Codex, Cursor, and other local MCP harnesses |
| `lab/profiles/` | Component profiles, router labels, one universal profile, and domain configurations |
| `lab/registry.yaml` | Prompt-lab levers, variants, patterns, experiments, and routed artifacts |
| `references/facs_laban_reference.md` | FACS action-unit catalog, Laban efforts/shape, plain-language translations |
| `references/method_details.md` | Realism lock list, reference-still pattern, captions/assembly, verification, per-model notes, reverse (video→prompt) extraction |
| `references/iphone_rawugc_realism.md` | **Field-tested preset** — the raw iPhone-UGC look, anti-AI-skin recipe, preferred formats |
| `assets/clip.iphone12_rawugc.hybrid.xml` | Compact YAML-in-XML clip package (< 2000 chars) |
| `assets/clip.iphone12_rawugc.yaml_json.txt` | YAML + embedded-JSON dual-parse clip package (< 2000 chars) |
| `assets/reference_still.iphone12_morning.txt` | Reference-still prompt (image-to-video identity + skin anchor) |
| `assets/clip_control_package.template.yaml` | Blank fully-scored control template |
| `assets/minified_control_package.example.json` | Minified JSON control example |

## Current evidence base: UGC and motion

- **Anti-AI skin (the #1 tell):** never ask for "smooth" skin — that *causes* the waxy plastic look.
  Instead name real microtexture (fine pores, uneven tone, fine lines, under-eye puffiness, T-zone
  sheen) **and** forbid `smooth_ai_skin / waxy / poreless / airbrushed`. For image-to-video, skin is
  locked by the **reference still**, not the video prompt.
- **iPhone-realism levers:** `30fps` (not cinematic 24), Smart-HDR flat tone, cool white balance,
  deep focus / no bokeh, floaty built-in stabilization.
- **Natural facial motion:** add a `face_motion` layer (eye darts, blinks, brow flickers, talking
  mouth shapes) so the face is never stiff/frozen.
- **Loosen the performance for raw UGC:** casual, low-key, a small "um," a glance away. Over-direction
  reads as an actor hitting marks.
- **Format does not drive realism for look controls.** XML/YAML/JSON are organizational scaffolding; the
  model reads the descriptive text. The compact **YAML-in-XML** and **YAML+JSON** packages are useful
  because they carry every realism lever in one paste under the ~2000-char input cap.

These observations cover tested portions of the current lab. They are ingredients for relevant
profiles, not universal defaults for every video domain.

## Current agent-operated surfaces

Point Claude Code or a compatible agent at this folder to use today's authoring and repository
operations. `SKILL.md` handles the current UGC specialization. `lab/AGENTS.md` handles composition,
experiments, and render verdicts. `lab/second_brain/AGENTS.md` governs retrieval, distillation,
curation, reasoning, context, and evidence. Start any unfamiliar task with
`./bin/cpcs agent.brief`; the read-only operation returns a source-hashed natural-language brief and
typed plan using the live role-gated CLI and MCP catalog.

## Use it from another agent

`cpcs.agent.brief` is the automatic entry point for another agent. It routes the task, marks API
credential boundaries, selects existing operations, and explains canonical JSON plus natural
language, YAML, and XML projections. `AGENT_PROMPT.md` contains deeper operator prompts for research
distillation, concept retrieval, prompt-lab composition, and the current UGC workflow. Those prompts
remain guidance, not runtime authority.

A local coding harness keeps its existing filesystem, terminal, Git, browser, and IDE controls and
connects `bin/cpcs-mcp` for CPCS-specific tools. Hermes Agent is live-tested on this device through
that boundary; other harnesses use the same MCP contract but remain separately qualified clients.

## Prompt Lab (A/B testing + pattern curation)

`lab/` is a tracking system for A/B testing prompt variations and curating the patterns that drive
good output. Every variant, render result, and finding is a structured, machine-readable record, so
an AI agent loads one file (`lab/registry.yaml`) and **recommends prompt combinations** for a goal.

- **`lab/registry.yaml`** — levers vocabulary + variants + patterns + experiments (the source of truth)
- **`lab/AGENTS.md`** — how an agent recommends a combination and logs results
- **`lab/variants/`** — tracked prompt bodies · **`lab/runs/results.csv`** — scored results ledger ·
  **`lab/experiments/`** — A/B tests · **`lab/schema/`** — record shapes

Ask an agent: *"using lab/, recommend a combination for max realism, iPhone look, 4s talking-head."*
See `lab/README.md`.

## Research

The `research/` folder contains frozen source packages for every admitted domain. FACS/Laban and
hierarchical motion grammar are early packages, not the knowledge boundary. Each later domain can
bring its own concepts, claims, methods, mechanisms, vocabularies, controls, metrics, and evidence
rules through the same governed extraction and curation path. Root `SKILL.md` is the UGC profile
skill; it does not define the universal ontology or the complete second brain.

## Ethics & rights

Preserve *structure* (timing, movement quality, camera grammar), not identity or unverifiable hype.
Keep product/proof claims truthful and substantiated. When recreating a reference video, swap identity,
voice, logos, and any distinctive/recognizable choreography — extract movement quality and timing, not
a clone.

## License

[MIT](LICENSE) — free to use, modify, and distribute. Open-source research release.

## CPCS Guided Prompting v1 (experimental reasoning layer)

CPCS v1 is an experimental knowledge-grounded guided-prompting layer that runs
BEFORE canonical score compilation. It deliberates with the frozen CPCS
reasoning/retrieval system (hypotheses, query steering, prerequisite discovery,
bounded closure), projects a compressed user-facing guided experience, and hands
the resulting typed overlays to the SAME existing compiler path used by the
baseline. The baseline (`reasoning_policy = CURRENT_BASELINE`) remains the
default; `CPCS_REASONING_V1` is opt-in.

### Quickstart (validated flow)

```sh
git clone https://github.com/Kingsley-Cyber/ai-video-movement-prompt-system.git
cd ai-video-movement-prompt-system
bin/cpcs bootstrap --role operator --input <(echo '{"runtime": "/path/to/frozen/Runtime"}')
bin/cpcs doctor
bin/cpcs-mcp
# connect your MCP client and send one sentence, e.g.:
#   "Person walks through a quiet hallway. Just make me the prompt."
```

`bin/cpcs bootstrap` is idempotent: it validates the frozen runtime
identity/artifacts, writes machine-local configuration (path + freeze
identities only, no secrets), and reuses the doctor health check.
Alternatively the runtime can be provided per-process:

```sh
export CPCS_FROZEN_RUNTIME_PATH=/path/to/frozen/Runtime
```

Without a configured runtime, guided CPCS operations fail closed with a
typed backend-unavailable error; baseline operations are unaffected.

### Health check

```sh
bin/cpcs doctor
```

Reports each guided-prompting component. Provider generation is reported as
`NOT CONFIGURED` when credentials are absent; this does NOT gate guided-prompting
readiness.

### MCP

```sh
bin/cpcs-mcp
```

An MCP client discovers the high-level tools through `tools/list`:

- `cpcs.guided.start` / `cpcs.guided.project` / `cpcs.guided.answer`
- `cpcs.guided.finish` (FAST "just give me the prompt" completion — still runs
  full deliberation; zero optional questions; blocking unknowns fail closed)
- `cpcs.guided.revise` (targeted revision with immutable session history)
- `cpcs.guided.inspect`, `cpcs.session.inspect`, `cpcs.session.history`
- `cpcs.ideate` (creative direction candidates; candidates are never
  mandatory requirements)
- `cpcs.deliberate.plan`, `cpcs.hypotheses.inspect`,
  `cpcs.query.plan.inspect`, `cpcs.reasoning.closure.inspect` (diagnostics)

### Modes

- **GUIDED**: full deliberation, compressed projection, only material questions
  (normally 0–3 per turn).
- **FAST**: triggered by phrases like "just give me the prompt"; completes with
  safe inference + baseline defaults without optional questions.
- **AUTO**: chooses FAST when nothing material needs a decision, GUIDED when a
  creative fork or blocking issue exists.

### Revision

A completed prompt can be revised ("Actually, …"). Revisions are immutable
history entries; only the dependency closure of the affected reasoning is
invalidated. Retries are NOT repairs.

### Provider generation

Provider generation is optional and unconfigured in this release. The guided
prompting product is fully usable without provider credentials; the final
prompt package is produced by the existing provider-neutral compiler path.
