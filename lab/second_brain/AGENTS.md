# Second-brain operating contract

Read `../../AGENTS.md`, `../AGENTS.md`, and `../registry.yaml` first. Those files win on conflict.
This subsystem extends the existing lab control plane. `../concepts.jsonl` remains the sole curated
concept-node authority, and `../../research/` remains frozen.

## Five-W charter

### WHO

The system has five actors with separate authority:

1. The repository owner has final authority over promoted concepts, authored relationships,
   ontology decisions, and experimental verdicts.
2. An authoring or curation agent may create proposals and promote validated proposals. It preserves
   durable IDs, source references, and Git history.
3. The source extractor safely inventories authorized local folders or accepts typed Polymath
   passages, hashes source bytes before parsing, creates stable locators and bounded evidence
   packets, and emits versioned candidate bundles under ignored `work/`. External RAG adapters,
   including Polymath MCP, retrieve passages, metadata, locators, and candidate relationships.
   The Polymath MCP adapter discovers its live tool contract, uses environment-only bearer
   credentials, permits only the two read search tools, and returns a bounded typed evidence packet.
   Adapters submit versioned batches and cannot write proposals directly.
   An MCP-connected external LLM is the semantic extraction worker. It reads only bounded packets
   through the research-session operations and submits schema-constrained packet results. Contract
   `cpcs.semantic_extraction_response/1.1` requires candidates or an evidence-linked
   `no_candidate` reason that accounts for every packet passage. Historical `1.0` captures remain
   readable but are not writable. The session owner captures the exact response bytes and hash; it
   does not treat a fresh model call as deterministic or authoritative.
   The source-unit registry admits only completed, validated source bundles. It stores exact local
   source identity, locator, rights basis, passage hash, and either passage bytes or byte offsets
   into hash-bound preserved files. Promotion must resolve every typed evidence tuple to exactly one
   registered unit. Unresolved local, web, or Polymath references remain explicitly quarantined.
   The Polymath inventory adapter may update the corpus manifest. The distiller records the
   retrieval and extractor contract, computes deterministic fingerprints, deduplication decisions,
   hop alignment, and refactor actions, then stages admissible proposals. Retrieval, embeddings,
   and external IDs do not establish durable repository identity.
4. The TwelveLabs transport package separates assets, Pegasus Analyze, Pegasus Segment, Pegasus
   Batch, knowledge-store Search, Jockey Responses, and Marengo embeddings without repository
   authority. The governed cascade verifies exact local bytes and media time, constrains every
   provider pass to one authorized source or explicit store-item selection, preserves semantic and
   local-measurement lanes in a Video Observation Graph, reverse-compiles only through the
   universal score kernel, then normally records one semantic observation. The explicit
   `operational_only` cascade mode returns the validated VOG and work artifacts without calling the
   recorder or distiller; only the application-owned paired comparison workflow may select that
   mode. Its normal evidence class is
   `interpreted` or `inferred`, never unearned measurement. Knowledge proposals still pass the
   shared deterministic distiller. Every public surface execution writes a content-bound completion
   receipt under ignored work state. Exact retries replay only after the job, result, request,
   response, and normalized hashes validate. Incomplete attempts are quarantined and cannot
   resubmit automatically. Atomic extraction begins with a content-addressed plan whose fixed
   fast, standard, or research mode declares every Analyze and Segment profile, full authorized
   interval coverage, provider-call count, and bounded concurrency before execution. Generated-render score compliance uses a separate closed
   response schema and may target only compiler-declared semantic metric and canonical-path pairs.
5. Intent router, reasoning-policy selector and executors, compiler, render verifier, recorder,
   reflector, and query engine are separate roles. The router
   classifies a user request and selects configured profile labels without inventing directing
   knowledge or provider output. The reasoning-policy selector chooses a curated, status-gated
   policy over the retrieved context. Its bounded Python executor emits an ephemeral operational
   trace and provider-neutral directing strategy without inventing concepts, exposing private
   chain-of-thought, or changing authority. The compiler resolves
   curated knowledge, the recorder admits hash-bound verified-render evidence, exact raw human
   testimonials, reviewed source-span normalizations, and append-only corrections, then appends
   immutable history; the reflector writes provider-scoped derived output,
   the verifier creates temporary compliance and bounded-repair diagnostics, and the query engine
   creates temporary reasoning results. Temporal policy filters every curated
   store consistently, while the index builder creates rebuildable retrieval views only.
6. The Research Delta Compiler consumes completed, source-bound claim proposals. It deterministically
   classifies only closed implementation targets, resolves their existing owners, snapshots affected
   contracts, names fixed regression commands, and writes a content-addressed proposal under ignored
   `work/`. It cannot change code, assign a durable ID, write staging or curated data, merge, push,
   or promote. Its separate patch runner captures only a strict proposal-scoped unified diff, then
   requires exact curator authorization before applying it to the sealed Git revision in a detached
   worktree. The runner executes only fixed owner tests and the repository gate, hash-checks logs and
   recovery state, and emits an operational receipt. Inspection and explicit cleanup preserve the
   receipt while keeping the live checkout and every authority tier unchanged.

Never collapse these actors into one unrestricted language-model process.

### WHAT

The control plane has three tiers:

- `curated/` contains Git-versioned authored edges, deterministic rules, normalized intents,
  concept-to-control mappings, first-class claims, equations, methods, creative mechanisms,
  reasoning policies, and
  source references. Every research object names the curated concepts that place it in retrieval
  and may link to other typed research objects only through schema-declared fields.
- `immutable/` contains append-only source units, sealed flights, append-only runs, Pegasus
  observations, measurement observations, exact human testimonials, and reviewed testimonial
  normalizations.
- `derived/` contains reproducible learned weights, insights, coverage, indexes, source closure,
  domain coverage, concise core memory, outcome memory, and the revision-bound brain-health report.

Curated data defines what CPCS recognizes. Immutable data records what occurred. Derived data is
disposable inference. The live reasoning graph overlays all three in memory and is never serialized
back into an authored store.

Keep three graphs distinct:

1. The research knowledge graph contains reusable concepts, typed research objects, mappings,
   policy grounding, provenance, and evidence links. NetworkX is the reference implementation and
   Neo4j is its optional rebuildable projection.
2. The reasoning execution graph is one ephemeral request trace produced by a selected policy. It
   is not written into curated knowledge or Neo4j.
3. The Video Observation Graph describes one asset or comparison. It may cite reusable concepts,
   but it is not the research graph and cannot establish research truth.

`src/video_reasoning.py` is the only bridge owner between the third graph and the first. It may
produce a read-only research-gap report or comparison lens from an exact VOG. A durable bridge is
non-traversable and enters `curated/video_concept_bridges.jsonl` only after exact human review;
Pegasus interpretation alone cannot create it.

A comparison lens may condition a later provider-neutral directing strategy only when its complete
context and current authority snapshot revalidate byte-for-byte. The strategy may admit curated
mappings from that frozen context; it cannot treat an unreviewed VOG observation as graph truth.

## First-class maintenance and anti-decay

The terminology-enabled ontology registry is implemented in `curated/ontology_registry.json` under
the closed `cpcs.ontology_registry/1.2` schema. Curated validation now rejects unregistered concept
kinds and layers, unregistered mapping target families and control namespaces, duplicate normalized
concept names, duplicate normalized semantic fingerprints, undeclared alias collisions, and authored
edges that violate their registered family, directionality, endpoint-kind pair, or cross-layer-root
pair. Every runtime edge type has one registry contract. Existing generic `pairs_with` records remain
valid for migration. New research `pairs_with` proposals are rejected before staging. An interpreted
Pegasus observation proposal may remain staging-only for typed reclassification, but curated
promotion rejects it while its compatibility report is false. Edge types without
an evidenced endpoint inventory remain review-required rather than learning compatibility from graph
connectivity. The distiller also rejects an incoming exact normalized name or alias collision before
staging.
`src/terminology.py` now normalizes registered identifier forms, resolves uniquely supported context,
and pauses `cpcs.reason` when a homonym remains unresolved. `AU1`, `AU01`, and `au-1` resolve to the
same `AU1` domain identifier while explicitly reporting that the complete FACS inventory is not yet
registered. The initial `action unit` and `follow through` sense sets are closed registry entries.

Source extraction records one recomputable terminology control for every candidate. Distillation
recomputes that control and rejects incompatible edge candidates. Ontology placement recomputes both
controls, accepts only exact current source-backed proposal IDs for unresolved senses, and blocks
promotion when either control remains open. Context bundles carry the compact resolution and proposal
handoff. The directing-strategy and universal-score admission boundaries recompute it and fail closed
when it is stale, tampered, or unresolved.

The maintenance controller uses this framework-neutral state path, which a LangGraph adapter may
execute without becoming a second workflow owner:

```text
detect terminology
-> resolve exact identifier or unique context
-> pause on unresolved homonym
-> dereference exact source units
-> agent selects one returned sense
-> validate source, hashes, registry, and candidate membership
-> stage exact-query proposal
-> inspect currentness
-> pass the proposal through placement or context
-> recompute at strategy and compiler admission
-> reason with the selected sense and reject competing roots
```

The agent may interpret the current query and stage an exact-query sense choice. It may not invent a
new sense, silently change a durable identity, edit the ontology registry, or promote its selection.
Reviewed durable terminology-registry changes, ontology parents, typed control values, and complete
domain inventories remain open.

Concept-to-control mappings may also carry one typed `representation_strategy`. Natural language,
YAML, JSON, and XML entries are projections of the same canonical score meaning. Their structural
roles, losses, and limitations are distinct from claims about provider behavior. A provider-effect
claim remains unverified unless it names its provider, model, task, evidence, and applicable scope;
no format is globally preferred merely because its syntax is convenient for a control family.

Knowledge maintenance is an owned second-brain workflow, not an occasional cleanup task. Before an
agent relies on the brain, and after an authorized knowledge change, it must produce one
revision-bound health result. That result checks authority schemas, provenance closure, temporal
eligibility, terminology collisions, orphaned records, required-domain coverage, retrieval
reachability, derived-index freshness, and NetworkX-to-Neo4j parity when Neo4j is enabled.

Core memory is the concise reviewed layer that an agent can load repeatedly. It contains atomic
concepts, rules, controls, typed relationships, limitations, and source anchors. It does not copy
whole papers, verbose model interpretations, provider responses, or per-asset observations. An
agent drills from core memory to the exact source locator only when the current task needs the
underlying detail.

The maintenance workflow uses typed state transitions and durable checkpoints:

```text
idle
-> inspect
-> classify_decay
-> plan_repair
-> retrieve_source_if_needed
-> validate_proposals
-> await_explicit_review
-> journaled_promotion_if_authorized
-> rebuild_derived_views
-> qualify_retrieval_and_projection
-> closed
```

Every transition records its input hash, policy version, output hash, disposition, and next allowed
states. Failed or interrupted work resumes from the last verified checkpoint. Identical authority,
state, and policy must replay to the same next state. A LangGraph adapter may execute this graph,
but CPCS schemas, guards, journals, and public operations own its meaning. LangGraph-specific nodes
must not contain business rules or become a second authority path.

Decay includes more than old timestamps. The health classifier distinguishes temporal staleness,
superseded knowledge, source or policy version drift, missing provenance, ontology collisions,
orphaned edges, incomplete domain inventories, operational mappings that no longer compile,
retrieval regressions, and stale derived projections. Current retrieval excludes ineligible records
before ranking and reports their exclusion reasons. Historical requests can still retrieve them
through an explicit valid-time and system-known-time view.

Source-unit coverage and domain completeness are separate measures. For each registered vocabulary
or source-declared catalog, a domain coverage manifest must record expected items, extracted items,
staged items, curated items, compiler-mapped items, retrieval-qualified items, and explicit
ambiguous, excluded, or missing dispositions. A source is not semantically complete merely because
every heading and paragraph received a structural disposition.

FACS is the first completeness canary. If an authorized source declares a catalog of Action Units,
the manifest compares its canonical AU identifiers against extraction, curation, mappings, and
retrieval tests. If `AU14` is absent from the graph, CPCS returns a typed `coverage_gap`; it does not
infer that AU14 is invalid or substitute a nearby code. When authorized source evidence contains
the answer, CPCS returns the exact source ID, locator, content hash, answer span, evidence class, and
uncertainty, then may open an unreviewed extraction proposal. The source answer remains external
evidence until the existing distillation and curation gates promote it.

`cpcs.source_answer_trace/1.0` is implemented for exact local fallback through the context broker,
with `answered_local`, `not_found`, `ambiguous`, and `not_required` dispositions. The public
`cpcs.brain.health` operation reads the revision-bound health report. `cpcs.maintenance.prepare`,
`.status`, and exactly authorized `.advance` own the resumable inspect, selective-rebuild,
optional validated Neo4j-sync, and qualification path. Promotion-spanning repair, cancellation,
and source-answer-to-domain-repair transitions remain future states and must not be implied by this
closed first workflow.

### Outcome memory and negative knowledge

The runtime preserves exact human statements, quote-spanned normalization,
dimension findings, metric findings, strengths, failures, limitations, experiment verdicts, and
review rationale. Accepted complete isolated experiments produce scoped positive and negative
learned edges, and query ranking consumes their weights. The current derived edge trace retains run,
artifact, compliance, and review identities plus the verdict, but it does not carry the exact
rationale, failed dimensions, remarks, or limitations into traversal. Noncausal failure associations
also downrank candidates without creating a reviewed no-go rule. This is `PARTIAL`, not a complete
outcome-memory system.

`cpcs.outcome_memory/1.0` is a rebuildable view over existing immutable runs,
testimonials, testimonial reviews, verification evidence, and accepted-experiment receipts. It does
not become another evidence store. Each outcome record contains:

1. `outcome_class`: `success`, `failure`, `mixed`, `inconclusive`, or `no_go`.
2. Exact provider, model, task, duration, seed, assets, score, controls, tested delta, and temporal
   scope.
3. Passed, failed, mixed, and unobservable dimensions with metric values and evidence references.
4. Exact human statement references, reviewed summary, rationale, remarks, limitations, and
   attribution status.
5. Positive, negative, neutral, or blocking traversal effect with the evidence threshold that
   permits that effect.

Traversal applies outcome direction conservatively. A scoped success may raise rank but cannot
bypass an authored conflict or missing prerequisite. A failure may lower rank and expose its reason.
Mixed or inconclusive evidence changes neither direction and instead exposes uncertainty or a new
experiment gap. A hard `no_go` may reject a path only after an owner reviews and promotes a scoped
failure card or rule. One render, one LLM remark, one Pegasus interpretation, or one derived
negative edge cannot block a concept globally.

Every reason response must report the outcome evidence it used: admitted positive signals,
downranking negatives, blocking curated no-go rules, ignored out-of-scope evidence, and exact run or
review references. This makes a good hop explain why it was favored and a rejected hop explain the
bad result or constraint that stopped it.

The implemented first maintenance workflow uses one deterministic event pattern. Events are
append-only, hash chained, sequence checked, and folded into current state. Each event binds the
maintenance request, state content, stage input, output payload, policy, and previous event. Its
closed states are:

```text
inspect -> rebuild -> project -> qualify -> complete
```

`failed` is explicit. Retry reads and validates the same expected state and event head; stale or
changed inputs fail. The event ledger records what occurred, while curated knowledge still changes
only through the existing journaled promotion owner. Repair planning, review, promotion,
cancellation, and supersession remain owned target extensions, not hidden transitions.

FACS remains one regression and completeness canary because it provides a concrete identifier
catalog and homonym problem. It is not the parent ontology, the default extraction shape, or a
required control family for unrelated research. Every future domain can register its own vocabulary,
coverage contract, evidence rules, mappings, and held-out queries under the same universal kernel.

### WHEN

External knowledge starts as a source-extraction bundle or retrieval batch. `source_extract.py`
creates proposals, coverage findings, and `distillation_batch/1.0` without staging or promotion.
Its bounded packets expose existing concept anchors and the closed allowed-output vocabulary,
   including reasoning-policy proposals. A new packet cannot use an unexplained empty candidate
   array; it must provide source-closed no-candidate coverage. Source processing identity binds exact source bytes, parser
version, extraction-policy version, and structural-extractor version so unchanged bytes are
reprocessed when the parsing contract changes. It
preserves explicit Markdown equation blocks as exact, located chunks and gives every parsed source
section a visible disposition. For claim, equation, method, and mechanism candidates, deterministic
adapter code owns the exact source ID, locator, and content hash rather than trusting model-supplied
source fields.
After every packet has a closed disposition, a curator admits the completed bundle through
`cpcs.research.source.units.admit`. This authorization writes only immutable source units and
rebuildable derived views. Distillation may stage proposals before admission, but production
promotion fails closed until every proposal evidence tuple resolves through the registry. Agents
inspect `cpcs.source.status` and use `cpcs.source.resolve` or `cpcs.context.get` to retrieve bounded,
hash-verified passages; they do not flatten lineage into prose-only references.
`distill.py` converts each candidate into a
traceable staging decision under a versioned policy. Promotion requires source verification, schema
validation, duplicate review, operational-usefulness review, relationship validation, and explicit
curation. Before review, `cpcs.research.placement.plan` binds the staged run and exact durable-ID
assignments to one content-addressed `cpcs.research_graph_growth_plan/1.0`. Each proposal receives
one closed `cpcs.ontology_placement/1.0` covering identity, registered classification, parent and
typed bridge edges, controls, metrics, source units, affected derived indexes, and incremental graph
projection. Curation rejects a missing, stale, blocked, or assignment-mismatched plan. Similarity
never establishes durable identity.
A flight is sealed before its first run. Recording follows rendering or extraction. Reflection runs
only after immutable evidence exists and reruns after inputs or policy change. Reflection never
promotes itself.

### WHERE

All new control-plane code and data live under `lab/second_brain/`. Dense assets, downloaded source
bytes, videos, masks, and temporary query output belong under the ignored `work/` directory. The
existing `lab/graph.json` remains the derived repository-wide view.

### WHY

CPCS needs operational reasoning across cinematography, lighting, performance, FACS, Laban,
kinematics, contact, animation, editing, audio, marketing, provider capability, and render evidence.
The repository is the source-closed authority for admitted research: a coding agent can traverse a
concept and dereference its exact local supporting passage without Polymath. Polymath remains an
optional research library for discovering or retrieving evidence not yet admitted locally. Its
results do not become authority until their source units and proposals pass the same gates.

The defining control-plane test is:

```bash
rm -rf lab/second_brain/derived
python3 -m lab.second_brain.src.reflect rebuild
python3 -m lab.second_brain.src.validate control-plane
```

With unchanged inputs and policy, reflection must rebuild byte-identical normalized output.

Credentialed Polymath probes are optional external checks, not part of the offline control-plane
gate:

```bash
python3 -m lab.second_brain.src.providers.polymath doctor
python3 -m lab.second_brain.src.providers.polymath retrieve \
  "Laban effort movement" --rights-basis owner_authorized_research --top-k 4
```

The retrieval qualification test is:

```bash
python3 -m lab.second_brain.src.retrieval_eval \
  --output work/retrieval/qualification.json
```

`retrieval_benchmark.yaml` is a reviewed quality contract. Each case uses the supported reasoning
or intent-context path, names concepts that must be selected and concepts that must never be
selected, and requires exact replay without authority mutation. Do not delete or relabel a failing
case merely to make the gate green; repair the retrieval policy or document and review the changed
product intent first.

The local scale qualification test is:

```bash
python3 -m lab.second_brain.src.scale_eval \
  --output work/scale/qualification.json
```

`scale_benchmark.yaml` clones the current concept corpus to 10x and 100x unique IDs under ignored
`work/`, attaches fixture-only typed `refines` bridges to the real traversal topology, and runs
ingest, graph build, index build, exact query replay, and two reflection rebuilds. It must not edit
authority. Exact semantic duplicates are suppressed before frontier ranking so duplicated source
language cannot consume root or hop budgets. Limits qualify only the declared local single-worker
class; they do not establish hosted, distributed, or arbitrary-corpus performance.

## Write boundaries

`src/directing_session.py` owns the sealed external-LLM creative-decision ledger under ignored
`work/application/directing_sessions/`. It reuses research-session private storage helpers,
reads `directing_passes.yaml` and the two `schemas/directing_session*.schema.json` contracts,
and receives compiler checks through an injected callable. It never imports the compiler,
invents scenes or promotes knowledge. Regression cases live in `tests/test_directing_session.py`.

| Role | Persistent write scope |
|---|---|
| Curator | `lab/concepts.jsonl` and `curated/` |
| Recorder | append only to `immutable/` |
| Reflector | `derived/` only |
| External RAG adapters | no direct repository writes; submit versioned distillation batches |
| Source extractor | ignored bundles and temporary evidence packets under `work/` only |
| Source-unit registry | append only to `immutable/source_units.jsonl`; unresolved references remain quarantined in the rebuildable source-closure report |
| Research session | ignored source registrations, packet results, captured responses, and replay receipts under `work/application/research_sessions/` only |
| Research Delta Compiler | content-addressed operational impact plans under `work/application/research_deltas/` only |
| Research Delta patch runner | captured patches, detached worktrees, hash-checked state, logs, receipts, and cleanup records under `work/application/research_delta_patches/` only |
| Local measurement adapter | ignored raw frames and candidate batches under `work/` only |
| Polymath inventory adapter | `staging/corpus_manifest.jsonl` only |
| Distiller | `staging/distillation_runs.jsonl` and admissible staging proposals |
| Terminology resolver | read-only deterministic resolutions plus `staging/terminology_resolutions.jsonl` for exact-query, source-backed, non-authoritative agent choices |
| TwelveLabs transport | ignored provider artifacts, attempt markers, and completion receipts under `work/twelvelabs/` or the application analysis work root |
| Pegasus adapter | immutable Pegasus observations and distillation batches |
| Query engine | temporary output under `work/` only |
| Neo4j projection | isolated `CPCSNode`, `CPCS_REL`, and generation metadata plus mode-0600 checkpoints under `work/neo4j/<namespace>/`; never Git authority |
| Context broker | no repository writes; typed bundles are returned to the caller |
| Context enrichment | no repository writes; exact-authorized Polymath reads occur only for the broker's declared gap query |
| Intent router | no repository writes; normalized intents and context handoffs are returned to the caller |
| Maintenance agent | no direct authority writes; health reports, source-answer traces, and repair plans stay derived or under ignored work, while staging, promotion, and rebuild use their existing owners |
| Reasoning-policy selector and executors | no repository writes; selected policy, structured operation trace, and compiled directing strategy are returned to the caller |
| Render verifier | no repository writes; compliance and repair diagnostics stay under ignored `work/` |

Project code provides no immutable update or delete operation. A learned edge is invalid without
evidence IDs, model version, context, observation count, and derivation policy. A causal `promotes`
edge also requires an isolated comparison.

Every staging, curated, immutable, migration, and derived write transaction must enter through
`src/authority.py`. Its one nonblocking POSIX `flock` serializes writer processes across all tiers;
nested writer roles in the owning thread reuse the outer transaction. A competing writer fails
before reading authority and may retry after the owner exits. The OS lock, not the diagnostic JSON,
owns exclusion and is released if the process dies. Never delete or replace
`work/locks/second_brain_authority.lock` while a CPCS process is active. This local boundary does not
claim multi-host or network-filesystem coordination.

Supported multi-file query, context, compile, graph, index, status, reflection, and extraction
coverage reads must use `authority_reader`. Shared readers may coexist across processes; a writer is
exclusive. An exclusive outer transaction may call a reader, but shared-to-exclusive upgrade is
forbidden. The snapshot covers one decorated operation only, not a sequence of independent API
calls or direct file access outside the supported runtime.

Every single-record or bundle promotion and every admitted curated migration must use
`src/curation_journal.py`. The journal is prepared and fsynced before an atomic target replacement.
A missing commit marker means rollback to the exact before hashes; a committed marker requires
every after hash. Recovery rejects target, manifest, blob, path, or symlink tampering and runs before
another curation reads authority. Never bypass the journal with direct append, truncate, or snapshot
restoration. Receipts under ignored `work/` are operational evidence, not curated truth.

## Evidence and identity rules

- Durable concept and intent IDs come only from curated repository files.
- Concept kinds, layers, mapping target families, and control namespaces must resolve through the
  curated ontology registry before promotion.
- Semantic extraction cannot prove exact joints, force, FACS intensity, or contact timing.
- Measurement lanes remain separate and record their tools and evidence classes.
- Existing `c_*`, `v*`, `r*`, `p*`, `e*`, and `blk_*` IDs are never renumbered.
- Supersession creates a new durable ID and reciprocal lineage; it never overwrites or deletes the
  historical record. Current mode selects the open-ended active head. Historical mode requires an
  explicit `as_of` timestamp and uses inclusive-start, exclusive-end validity.
- Learned weights may order admissible choices, but cannot override a hard rule or authored conflict.
- A nonlegacy flight declares `isolated_comparison` or `bundled_observation` before recording. Only
  an evidence-complete isolated pair may derive a causal edge; bundled and single-run signals remain
  noncausal. An isolated flight predeclares outcome concept IDs; unrelated context concepts never
  become causal targets merely because they were selected in the same score.
- Public experiment preparation resolves exact materialized build IDs, validates their manifests
  and curated concept snapshot, and proves the isolated control delta before a separately
  authorized seal. Exact flight resealing is idempotent; changed content under one ID is rejected.
- A controlled run binds exact build, score, request, provider, model, profile, concept, block,
  asset, seed, artifact, compliance, metric, human-review, and optional selected testimonial
  lineage. Capture preserves exact UTF-8 wording. Review findings cite verified codepoint spans;
  correction appends one successor without altering either prior record. Attribution remains an
  `unverified_candidate`. Content-derived IDs make exact retries idempotent; changed evidence is
  rejected.
- New controlled-evidence `1.1` runs require one server-derived `metric_evidence` row for every
  sealed metric. A compliance-owned metric uses its exact `pass` or `fail` status and resolves the
  compiler requirement plus canonical controls to hash-bound verification assertions. Any other
  scalar requires one current testimonial `metric_findings` entry with the same value, exact raw
  statement spans, and a concept or canonical control sealed in the run. Extra, missing,
  duplicated, mismatched, unobservable, or ungrounded metrics fail before append. Historical
  `1.0` runs remain readable but cannot claim `1.1` lineage.
- Accepted automatic reflection requires one complete isolated flight whose every arm has
  conclusive verification and a current reviewed testimonial. The application orchestrator may
  preflight and append those exact runs, call this subsystem's existing reflector, and append one
  immutable `improvement_orchestration` receipt. It cannot calculate alternate weights, accept a
  partial flight, treat an LLM diagnosis as evidence, or promote its working-pattern, failure,
  provider, compiler, profile, or research candidates.
- Learned ranking is filtered by provider and model unless a derived signal explicitly uses `all`.
- `research/` is read-only upstream evidence.

## Neo4j projection workflow

Neo4j is an optional persistent read model behind the existing Python-owned reasoning policy.
`src/neo4j_projection.py` builds one all-version plan from validated Git records, retains durable
IDs, record and projection hashes, tiers, repository locators, payloads, and directed parallel edge
IDs, then synchronizes only an environment-selected CPCS namespace. Polymath namespaces are
rejected. No application or MCP operation accepts credentials, Cypher, labels, database names, or
filesystem paths from tool arguments.

The local deployment is pinned in `neo4j.compose.yaml`. Its `/data` and `/logs` mounts use named
volumes, and its ports default to loopback `17474` and `17687`. Load `CPCS_NEO4J_PASSWORD` from
macOS Keychain or another external secret manager before starting it. Also set
`CPCS_NEO4J_URI`, `CPCS_NEO4J_USER`, `CPCS_NEO4J_DATABASE`, `CPCS_NEO4J_NAMESPACE`, and
`CPCS_NEO4J_OWNERSHIP=cpcs_owned` in the application environment.

Use this order:

```bash
./bin/cpcs graph.projection.plan --role operator
./bin/cpcs graph.projection.status --role operator
./bin/cpcs graph.projection.sync --role operator --input work/neo4j/sync.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Synchronize this exact inspected Git snapshot"
./bin/cpcs graph.projection.parity --role operator --input work/neo4j/parity.json
```

`CPCS_GRAPH_BACKEND` accepts `networkx`, `neo4j_shadow`, or `neo4j`. NetworkX remains the default.
`CPCS_GRAPH_FALLBACK` accepts `fail_closed` or `networkx`; the default is `fail_closed` when a
Neo4j mode is selected. The polling watcher calls the same synchronization implementation:

```bash
python3 -m lab.second_brain.src.neo4j_projection watch \
  --interval-seconds 1 --debounce-seconds 1
```

Deleting the CPCS namespace or its local volume never deletes Git authority. Re-run the inspected
sync to reconstruct the same logical digest. Verify exact ownership and a recoverable Git snapshot
before deleting a namespace.

## Commands

```bash
python3 -m lab.second_brain.src.validate schemas
python3 -m lab.second_brain.src.validate curated
python3 -m lab.second_brain.src.validate immutable
python3 -m lab.second_brain.src.validate control-plane
python3 -m lab.second_brain.src.graph stats
python3 -m lab.second_brain.src.neo4j_projection plan
python3 -m lab.second_brain.src.query reason "dramatic natural product reveal"
python3 -m lab.second_brain.src.query knowledge "target constraint residual" --object-type claim --maximum-hops 5
python3 -m lab.second_brain.src.scale_eval --output work/scale/qualification.json
python3 -m lab.second_brain.src.migrate consolidate-reciprocal-edges --effective-at 2026-08-04T00:00:00Z --by codex_curator
python3 -m lab.second_brain.src.migrate reclassify-reviewed-edges --review work/edge-review.json --by <curator-id>
python3 -m lab.second_brain.src.query reason "current guidance" --validity-mode historical --as-of 2026-01-01T00:00:00Z
python3 -m lab.second_brain.src.context build "restrained fear escalating into urgent movement" --token-budget 12000
./bin/cpcs context.enrich --role operator --input work/context-enrichment.json --authorize-as Kingsley-Cyber --authorization-reason "Retrieve evidence for this exact declared context gap"
python3 -m lab.second_brain.src.intent normalize "Cinematic UGC product recommendation"
python3 -m lab.second_brain.src.intent context "Show how this device works in a clear educational video"
python3 -m lab.second_brain.src.source_extract folder <authorized-folder> --research-goal "<gap>" --rights-basis <basis> --output work/source-bundle.json
python3 -m lab.second_brain.src.source_extract passages <retrieved-passages.json> --output work/source-bundle.json
python3 -m lab.second_brain.src.source_extract distill work/source-bundle.json
python3 -m lab.second_brain.src.research_delta prepare work/research-delta-request.json
python3 -m lab.second_brain.src.research_delta inspect <research-delta-id>
python3 -m lab.second_brain.src.ingest batch work/candidate-batch.json
python3 -m lab.second_brain.src.distill status
python3 -m lab.second_brain.src.curate bundle <run-id> work/durable-ids.json --by <curator-id> --review work/review.json
python3 -m lab.second_brain.src.pegasus doctor
python3 -m lab.second_brain.src.pegasus profiles
python3 -m lab.second_brain.src.pegasus run-job work/twelvelabs/job.json
./bin/cpcs analyze.atomic.prepare --role operator --input work/twelvelabs/atomic-request.json
python3 -m lab.second_brain.src.pegasus cascade work/twelvelabs/cascade.json --intent-context work/twelvelabs/intent-context.json --score-assets work/twelvelabs/score-assets.json
python3 lab/scripts/extract_pose_tier2.py --video <authorized-video> --source-id <source-id> --rights-scope authorized --model <pose.task> --model-version <version> --end <seconds>
python3 -m lab.second_brain.src.record experiment work/experiment-receipt.json
./bin/cpcs agent brief --role curator --task "record a reviewed render metric"
python3 -m lab.second_brain.src.providers.twelvelabs --help
python3 -m lab.second_brain.src.reflect rebuild
python3 -m unittest discover -s lab/second_brain/tests -p "test_*.py"
```

`cpcs.direct.withdraw` appends a revision removing an unlocked optional direction field,
retains the original capture, records its omission reason and invalidates dependent passes.
Protected fields and locked decisions reject. Owner-authored wording references bind the
accepted source hash and a resolved field locator; they are not research or model-tested claims.
A legacy scene/action import with bound direction can carry its authored shots; complete
sessions retain camera-pass ownership. An explicit nondefault model is retained in legacy
session identity, without changing original default sessions.

Complete directing sessions derive pass-scoped research through the existing bounded context
builder and exact source resolver. Layer/sub-layer stacks read accepted prerequisite decisions.
Explicit revisions retain old captures and invalidate dependent stacks. New proposal generation
is creative work; replay starts from captured choices. No pass promotes knowledge.
