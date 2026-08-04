# CPCS second brain

This directory is the repository-level reasoning control plane for CPCS. It does not replace
Polymath, duplicate `lab/concepts.jsonl`, or change the frozen research packages.

Install its declared runtime dependencies with
`python3 -m pip install -r lab/second_brain/requirements.txt`.

## Storage ownership

| Tier | Authority | Mutation rule |
|---|---|---|
| Curated | concepts, authored edges, rules, intents, mappings | reviewed Git changes |
| Immutable | sealed flights, runs, extraction and measurement observations | append-only API |
| Derived | learned edges, insights, coverage, indexes | delete and rebuild |
| Staging | retrieval decisions, proposals, rejections, corpus inventory | resumable and non-authoritative |

`src/authority.py` wraps every versioned-tier writer in one repository-wide, nonblocking POSIX
`flock` and wraps supported multi-file reads in shared mode. Staging admission, reviewed curation,
immutable recording, migrations, reflection, and the cross-tier Pegasus handoff therefore cannot
run concurrently in separate processes. Query, context, reasoning compilation, graph, index,
status, reflection materialization, and source-coverage reads can coexist across processes but
cannot observe a supported writer's partial transaction. Nested shared reads reuse the outer claim;
an exclusive owner may invoke a nested read, but a shared owner cannot upgrade to a writer. A
competing process receives a diagnostic `AuthorityBusy` before it reads or mutates authority. The
lock file lives under ignored `work/locks/`, is mode `0600`, and is never a knowledge record. The
operating system releases ownership after normal exit or process death; stale metadata never grants
or denies access. Do not delete the lock path while CPCS is active. This is a single-host POSIX
boundary, not a distributed lock or a transaction spanning separate API calls.

`src/curation_journal.py` gives single and bundled promotion plus admitted curated migrations one
crash-recoverable file transaction. Before any curated target changes, it writes a schema-valid
manifest plus exact before/after blobs, hashes and sizes under ignored
`work/curation_transactions/`, fsyncs them, and atomically activates the journal. Target files are
replaced atomically. A durable commit marker requires every after hash; otherwise the next curation
restores every before image before it reads authority. Fully prepared, committed, recovered, and
pre-activation-abandoned operations leave diagnostic receipts. Unknown target bytes, modified
journal content, path escape, symlink, hard link, or an unsafe receipt fails closed. Use
`python3 -m lab.second_brain.src.curate recover` for an explicit recovery pass.

`src/graph.py` builds a NetworkX `MultiDiGraph` in memory from those stores.
`src/query.py` performs deterministic, explainable traversal. `src/compile.py` maps selected
concepts to controls and runs named rule evaluators. `src/record.py` appends hash-chained evidence.
`src/reflect.py` rebuilds learned output from immutable history. `src/context.py` packages gated
query results and typed external passages into read-only, trust-labelled context bundles.
`src/intent.py` normalizes ordinary language, selects router-only profile labels, reports blend
conflicts, and passes its knowledge query to that broker.
`src/providers/polymath.py` performs bounded authenticated MCP discovery and read-only search, then
returns source-located, content-hashed passages in both extraction and context-evidence forms.
`src/source_extract.py` safely parses authorized local research or typed retrieved passages into
content-addressed chunks, bounded semantic packets, coverage findings, and governed candidate
bundles under ignored `work/`.
`src/temporal.py` owns knowledge-validity filtering and reciprocal supersession lineage.
`src/indexes.py` builds the deterministic retrieval catalog consumed by reflection and query
diagnostics; it is derived state, never a second knowledge authority.
`src/retrieval_eval.py` runs the committed expected/forbidden concept cases in
`retrieval_benchmark.yaml` twice through the real reasoning or intent-context path under one shared
authority snapshot. It emits `cpcs.retrieval_benchmark_report/1.0`, fails on missing or forbidden
concepts, profile drift, replay drift, or authority mutation, and may write reports only under
ignored `work/`.
`src/scale_eval.py` materializes ignored 10x and 100x uniquely-IDed fixtures, builds the production
graph and retrieval catalog, replays four research queries twice, and rebuilds derived state twice.
Its `cpcs.scale_benchmark_report/1.0` records local single-worker latency, Python allocation peaks,
deterministic hashes, correctness, and authority immutability. Exact semantic clones are removed
before frontier ranking so duplicate language cannot consume distinct-concept traversal capacity.

## Lifecycle

1. `source_extract.py` inventories and safely parses local sources, or validates retrieved
   passages, then emits a replay-stable source bundle containing `distillation_batch/1.0`.
2. `ingest.py` inventories sources and accepts versioned RAG candidate batches through
   `python3 -m lab.second_brain.src.ingest batch <batch.json>`.
3. `distill.py` fingerprints candidates, finds duplicates, proves connected placement, records
   refactor actions, and stages only admissible proposal bundles.
4. `curate.py` validates and promotes accepted proposals into their curated owner.
5. `compile.py` resolves mappings and rules for a reasoned concept selection.
6. `record.py` seals isolated or bundled flight designs and admits exact verified-render evidence
   into content-derived, append-only runs.
7. `reflect.py` rebuilds disposable provider-scoped associations, causal isolated-comparison
   effects, calibration indexes, and query ranking signals.
8. `query.py` overlays the tiers without persisting its temporary query node.
9. `context.py` expands selected sources and mappings, deduplicates typed external evidence, and
   packs the complete bundle under a deterministic token estimate without writing any tier.
10. `intent.py` classifies the request through `profiles/intent_routing.yaml` and calls `context.py`
   without producing provider prompts, canonical scores, or knowledge writes.
11. `retrieval_eval.py` qualifies priority-domain selection and profile routing without changing a
    knowledge tier. Change benchmark labels only when an owner-reviewed intent or knowledge change
    makes the prior expectation obsolete; never weaken labels to accept a retrieval regression.

## Controlled render-evidence contract

A nonlegacy flight declares `isolated_comparison` or `bundled_observation` before its first run. An
isolated flight has at least two arms whose `tested_delta` varies one shared curated concept and one
canonical control across distinct values. It also predeclares the non-delta outcome concepts that a
successful comparison may affect; other selected concepts remain context rather than accidental
causal targets. A bundled flight has no tested delta and can never produce a causal learned edge.

After rendering and verification, record one receipt through:

```bash
python3 -m lab.second_brain.src.record experiment work/experiment-receipt.json
```

The receipt names the sealed flight and arm, build directory, runtime result, selected artifact,
compliance report, experiment metrics, and an explicit human review. The recorder revalidates exact
build, result, artifact, and report bytes; binds intent, context, profiles, concepts, blocks, assets,
provider, model, seed, score, request, verification, and review hashes; derives the run ID from that
evidence; and appends once. An exact retry returns the existing row. Changed evidence is rejected.
The generic `record run` subcommand accepts legacy migration rows only and cannot bypass this path
for a new run.

Reflection may derive a causal `promotes` edge only when two runs from the isolated flight have
opposing usable outcomes, the same provider, model, seed, compiler, intent, context, profiles,
concepts, blocks, assets, and controls except the declared delta. Its trace includes both control
values and both build, artifact, compliance, and human-review identities. Other run associations
remain explicitly noncausal and lower weight. Query ranking filters learned signals by provider and
model, and no learned output can modify curated knowledge or override a hard rule.

## Source extraction contract

Create a reviewable bundle from an authorized folder or a typed Polymath-passage envelope:

```bash
python3 -m lab.second_brain.src.source_extract folder <authorized-folder> \
  --research-goal "Laban spatial movement controls" \
  --rights-basis owner_authorized_research \
  --output work/source-bundle.json
python3 -m lab.second_brain.src.source_extract passages work/retrieved-passages.json \
  --output work/source-bundle.json
```

Markdown, text, JSON, JSONL, YAML, and XML parsers create source-owned locators and hashes. YAML
custom tags and aliases, XML declarations and entities, symlinks, path escapes, invalid UTF-8, and
configured size, depth, node, chunk, and packet-limit violations are rejected. Whole large files
never enter semantic extraction: the bundle exposes bounded packets, and an optional typed semantic
response may cite only packet chunk IDs. Structural proposals remain candidates, never truth; new
concepts without a typed path and operational mapping are expected to fail the existing placement
gate until semantic extraction supplies that evidence.

## Intent routing contract

Normalize a request or run the complete read-only request-to-context path with:

```bash
python3 -m lab.second_brain.src.intent normalize \
  "Cinematic UGC product recommendation"
python3 -m lab.second_brain.src.intent context \
  "Show how this device works in a clear educational video"
```

`cpcs.normalized_intent/1.0` records the original request, explicit constraints and profile
overrides, domain, task, audience effect, profile blend, missing inputs, knowledge query, required
layers, conflicts, uncertainties, and policy versions. The profile policy is classification
configuration over one declared kernel. It cannot define score controls, provider requests, or
curated knowledge. Prefix a constraint with `must:`, `lock:`, or `input:` to classify it as a hard
constraint, continuity lock, or supplied input.

## Context bundle contract

Build client context with:

```bash
python3 -m lab.second_brain.src.context build \
  "Laban effort decimal spatial movement" \
  --token-budget 12000 --minimum-status ingested --target-format json
```

The broker always calls the relevance-gated query engine. It can accept a JSON list of external
passages through `--external-evidence`, but only when each passage names the query engine's declared
knowledge-gap query and its SHA-256 matches its text. External evidence remains explicitly
untrusted. The broker performs no network retrieval and never writes curated, immutable, derived,
or staging data.

## Distillation contract

A retrieval adapter supplies a batch containing its corpus, query, tool parameters, passage hashes,
extractor identity, prompt hash, and candidate records. The distiller normalizes candidate order,
hashes the batch and curated snapshot, and applies a versioned policy. Each decision records its
source evidence, candidate fingerprint, duplicate matches, one-hop anchors, existing graph path,
same-batch dependencies, connected-placement proof, and proposed refactor action. A new concept
must have a typed structural path to an existing curated concept plus either an operational edge or
an executable mapping. `pairs_with` does not satisfy either requirement. If the concept fails,
same-batch records that depend on it fail with it. Repeating the same batch against the same curated
snapshot returns the same run ID and does not duplicate proposals.

The distiller never promotes knowledge. Exact duplicates are discarded, probable duplicates become
merge reviews, broken references are rejected, and distinct candidates remain pending until
`curate.py` receives an explicit review. External origins (`local_source`, `polymath_mcp`,
`pegasus`, and `rag_pipeline`) cannot call the direct proposal route.

A curator can promote every staged member of one distillation run with:

```bash
python3 -m lab.second_brain.src.curate bundle \
  <distillation-run-id> <proposal-to-durable-id.json> \
  --by <curator-id> --review <review.json>
```

Concepts and intents are written before their dependent edges, mappings, and rules. If any member
fails validation in the promotion process, every touched curated file is restored to its
pre-promotion snapshot.

## Traversal contract

`src/graph.py` owns the versioned authored-edge policy. Structural edges (`is_a`, `part_of`,
`refines`) establish nesting. Operational and dependency edges (`applies_to`, `produces`,
`requires`) connect knowledge to use. `alternative_to` preserves contextual choices.
`conflicts_with`, `valid_for`, and `invalid_for` constrain selection rather than expanding it.
Legacy `pairs_with` edges are low priority and may appear at most once per traversal path, with a
global hop budget.

Every selected hop reports its direction, semantic transition, edge family, tier, and policy
version. Root retrieval requires more than one overlapping term for multi-term goals unless the
concept name or a one-word trigger matches exactly. A query with missing or partial term coverage
returns a `knowledge_gap` object and a deterministic follow-up retrieval query.

## Temporal and index contract

Curated concepts, edges, mappings, rules, and intents may carry a validity interval and reciprocal
replacement links. Records without validity remain timeless active records. Current queries select
only open-ended active heads; historical queries require `--as-of` and use an inclusive start and
exclusive end; `all_versions` is an explicit audit mode. Replacement traces preserve predecessors,
successors, and the current head.

```bash
python3 -m lab.second_brain.src.query reason "restrained movement guidance"
python3 -m lab.second_brain.src.query reason "restrained movement guidance" \
  --validity-mode historical --as-of 2025-06-01T00:00:00Z
python3 -m lab.second_brain.src.migrate consolidate-reciprocal-edges \
  --effective-at 2026-08-04T00:00:00Z --by codex_curator
python3 -m lab.second_brain.src.reflect rebuild
```

Reflection rebuilds one schema-valid catalog containing lexical, alias, deterministic signed
hashed-TFIDF vector, typed adjacency, prerequisite closure, conflict, temporal, supersession,
source, evidence, intent, control/provider, provider-performance, experiment, and video-observation
indexes. Provider-performance rows distinguish legacy, controlled, bundled, and causal evidence and
retain artifact-linked causal effects. Query results expose lexical, alias, vector, and fused candidate scores, but authored
conflicts and invalidity always override ranking. The typed-edge gate rejects repeated current
symmetric relationships and forbids growth beyond 158 current legacy `pairs_with` records or the
admitted production ratio. Historical views retain superseded reciprocal predecessors without
applying the current-distribution ratchet to past adjacency.

## Polymath status

The adapter performs live MCP discovery instead of storing capability counts in repository code.
On 2026-08-04, an exact-authorized local probe negotiated the legacy `2025-11-25` session protocol
with Polymath 1.29.0, discovered 27 tools including both allowlisted search tools, and returned a
schema-valid two-passage packet. The service returned three upstream chunks for a requested two;
the adapter deterministically retained two and recorded the truncation. Credentials remain in
environment variables and are never included in results. Retrieval itself writes no curated,
immutable, staging, or derived authority.

The earlier corpus inventory contains 80 documents in `video_generations_schools`. The corpus pass
is terminal with 78 documents complete and two source records failed because Polymath returned zero
chunks. Across 3,192
source-passage fetches, 36 operational concepts, 36 authored relationships, and 36 mappings passed
explicit review and promotion during the corpus pass. A subsequent deterministic distillation run
added the source-backed dual-view VFX color workflow, bringing the totals to 37 concepts, 37
relationships, and 37 mappings. No manifest row remains pending or processing.

```bash
python3 -m lab.second_brain.src.providers.polymath doctor
./bin/cpcs polymath.retrieve --role operator \
  --input work/polymath-retrieve.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Retrieve this exact bounded external evidence packet"
```

Set `POLYMATH_MCP_TOKEN` or `MCP_API_KEY` only in the process environment. Plain HTTP is accepted
only for an exact loopback endpoint; remote endpoints require HTTPS.

## Pegasus status

The provider package in `src/providers/twelvelabs/` pins TwelveLabs SDK 1.3.1 and API v1.3. Assets,
Pegasus 1.5 Analyze, Segment, Batch, knowledge-store Search, Jockey Responses, and Marengo 3.0 each
have a separate transport and job schema. The closed 14-profile catalog prevents callers from
smuggling arbitrary analysis behavior across those surfaces.

Generated-render verification uses a dedicated structured Analyze response. The job must carry
the compiler-declared semantic metric, method, and target-path tuples; normalization rejects any
undeclared or duplicate pair. The score-compliance profile is refused by generic Batch and source
cascade paths so it cannot run without that score boundary.

`src/pegasus.py` owns the governed cascade. It verifies exact local source bytes and `ffprobe`
metadata, performs a broad source map, deterministic segmentation and clipped deep passes,
normalizes optional local measurements, preserves disagreements in a source-bounded VOG, and calls
`lab/compiler/reverse.py` through the same universal score resolver. Exact requests, raw responses,
normalized rows, the VOG, reverse score, and run snapshots remain under ignored `work/`. One
hash-chained semantic observation is appended only after every preceding stage validates. Any
knowledge proposals still enter `distill.py` rather than curated authority.

Run `python3 -m lab.second_brain.src.pegasus doctor` to check configuration without printing
secrets. A real provider run still requires `TWELVE_LABS_API_KEY`,
an authorized source, and the store ID only for Search or Jockey. Fake-client tests prove the
complete local cascade and failure atomicity but do not claim a production provider analysis.

## Local measurement status

`src/measurement.py` owns `cpcs.pose_measurement_job/1.0` and
`cpcs.measurement_batch/1.0`. A job binds exact authorized video bytes, interval, PoseLandmarker
model bytes, model version, thresholds, stride, and creation time. Execution calls the detector
once per selected frame, performs deterministic nearest-centroid actor association, retains swap
suspicions, and emits only `detected` 2D image-space tracks with explicit coordinate, camera-motion,
and identity limitations. Raw frames and candidates remain under ignored `work/`.

The application exposes separate preparation, execution, explicit recording, normalization, and
source-cascade operations. Only the exact-authorized curator recording call appends a batch to
`immutable/measurement_observations.jsonl`. Selected immutable IDs normalize through
`normalize_measurement()` and enter the existing VOG and reverse-score path without a manually
rewritten intermediary record. Fake-detector canaries prove replay, one call per frame, actor order,
hash rejection, failure atomicity, idempotent admission, and normalization. No live detector-quality
claim exists until the optional dependencies, exact model, and an approved evaluation clip are
available.

## Validation

Run the commands in `AGENTS.md`. `validate control-plane` validates all stores, checks learned-edge
evidence requirements, and verifies a repeat reflection rebuild produces identical hashes.
