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

`src/graph.py` builds a NetworkX `MultiDiGraph` in memory from those stores.
`src/query.py` performs deterministic, explainable traversal. `src/compile.py` maps selected
concepts to controls and runs named rule evaluators. `src/record.py` appends hash-chained evidence.
`src/reflect.py` rebuilds learned output from immutable history. `src/context.py` packages gated
query results and typed external passages into read-only, trust-labelled context bundles.
`src/intent.py` normalizes ordinary language, selects router-only profile labels, reports blend
conflicts, and passes its knowledge query to that broker.

## Lifecycle

1. `ingest.py` inventories sources and accepts versioned RAG candidate batches through
   `python3 -m lab.second_brain.src.ingest batch <batch.json>`.
2. `distill.py` fingerprints candidates, finds duplicates, proves connected placement, records
   refactor actions, and stages only admissible proposal bundles.
3. `curate.py` validates and promotes accepted proposals into their curated owner.
4. `compile.py` resolves mappings and rules for a reasoned concept selection.
5. `record.py` seals a flight and appends runs or observations.
6. `reflect.py` rebuilds disposable learned associations.
7. `query.py` overlays the tiers without persisting its temporary query node.
8. `context.py` expands selected sources and mappings, deduplicates typed external evidence, and
   packs the complete bundle under a deterministic token estimate without writing any tier.
9. `intent.py` classifies the request through `profiles/intent_routing.yaml` and calls `context.py`
   without producing provider prompts, canonical scores, or knowledge writes.

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
`curate.py` receives an explicit review. External origins (`polymath_mcp`, `pegasus`, and
`rag_pipeline`) cannot call the direct proposal route.

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

## Polymath status

Runtime discovery on 2026-07-30 verified the local Polymath MCP server at version 1.28.1,
27 callable tools, and 80 documents in the `video_generations_schools` corpus. Wave 0 uses
the returned document IDs, source hashes, titles, and retrieval capabilities. External retrieval
still writes only staging rows and proposals. The corpus pass is terminal with 78 documents
complete and two source records failed because Polymath returned zero chunks. Across 3,192
source-passage fetches, 36 operational concepts, 36 authored relationships, and 36 mappings passed
explicit review and promotion during the corpus pass. A subsequent deterministic distillation run
added the source-backed dual-view VFX color workflow, bringing the totals to 37 concepts, 37
relationships, and 37 mappings. No manifest row remains pending or processing.

## Pegasus status

The provider transport in `src/providers/twelvelabs.py` pins TwelveLabs SDK 1.3.1 and API v1.3. It
supports knowledge-store creation, bounded asset and item polling, fully paginated search, Marengo
3.0 embeddings, and strict Jockey structured output. `src/pegasus.py` is the only repository
ingestion authority: it binds a ready store item to an authorized asset hash, saves request and SDK
response snapshots under ignored `work/`, validates semantic timestamps and evidence classes,
appends the immutable observation, and sends every knowledge proposal through `distill.py`.

Run `python3 -m lab.second_brain.src.pegasus doctor` to check configuration without printing
secrets. A real provider run still requires `TWELVE_LABS_API_KEY`,
`TWELVE_LABS_KNOWLEDGE_STORE_ID`, and an authorized source. Fake-client tests verify the integration
but do not claim a production analysis.

## Validation

Run the commands in `AGENTS.md`. `validate control-plane` validates all stores, checks learned-edge
evidence requirements, and verifies a repeat reflection rebuild produces identical hashes.
