# Second-brain schema contract

All persistent records are UTF-8 JSON Lines except the normalized derived JSON objects. JSON
serialization uses sorted keys, compact separators, Unicode preservation, and a final newline.
Record hashes exclude only the `record_hash` field and include `prior_record_hash`.

## Curated records

- Concepts remain in `lab/concepts.jsonl` and validate against `schemas/concept.schema.json`.
- Authored concept relationships live only in `curated/edges.jsonl`.
- Authored edge types are closed and versioned: `is_a`, `part_of`, `refines`, `requires`,
  `applies_to`, `produces`, `alternative_to`, `pairs_with`, `conflicts_with`, `valid_for`, and
  `invalid_for`. Derived association types cannot enter this ledger.
- Rules name tested Python evaluators. JSON is data, not an executable language.
- Intents normalize recurring goals while preserving canonical free-form language.
- Mappings connect a concept to a provider-independent CPCS control or representation.

Concept `layer` is a free string. `nl_triggers`, encoding metadata, parameters, and provenance can be
added without migrating older cards.

## Immutable records

`flights.jsonl` contains sealed designs and the content hash of every selected concept card.
A changed design gets a new flight ID. Runs must match the flight's intent, arm, paradigm, concepts,
provider, model, seed, and compiler version exactly. `runs.jsonl`,
`pegasus_observations.jsonl`, and `measurement_observations.jsonl` are append-only hash chains.
Legacy imports preserve unknown values as `null` or explicit `legacy-unrecorded` labels.

Pegasus observations contain one top-level evidence class, and every semantic item carries its own
evidence class. Semantic ingestion accepts only `inferred` and `interpreted`. Measurement observations
accept all five evidence classes but require a named tool.

## Derived records

`weights.json` contains learned edges. Every edge has evidence IDs, model version, context,
`n_obs`, and a derivation policy. A `promotes` edge additionally names its isolated comparison.
Derived files contain no build timestamp, so unchanged inputs and policy produce the same bytes.

## Distillation and proposal records

RAG retrieval enters through `distillation_batch.schema.json`. The batch identifies the adapter,
corpus, query, retrieval parameters, extractor, model, prompt hash, source locators, and passage
hashes. `distill.py` writes `staging/distillation_runs.jsonl`. Each run pins the input, policy, and
curated-snapshot hashes, then records every deduplication, hop-alignment, dependency, and refactor
decision. A concept decision may also contain a `connectivity` proof. The proof lists the
same-batch structural edges on the shortest path to curated knowledge, operational edges, mappings,
and explicit missing requirements. An unconnected concept receives
`reject_unconnected_concept`; dependent same-batch records receive `reject_invalid_reference`.

Polymath, Pegasus, and registered generic RAG proposals enter through the same distillation batch
contract with `created_by` set to `polymath_mcp`, `pegasus`, or `rag_pipeline`. Direct external
staging is rejected before a proposal is written. Each staged proposal carries a source locator,
claim, source identity, candidate record, deterministic duplicate candidates, and a status.
Promotion requires explicit positive checks for source and locator resolution, deduplication,
usefulness, relationships, and numeric precision. It writes a new curated record through
`curate.py`; the curator, not an external source, assigns durable IDs. Bundle promotion requires
an exact assignment for every staged proposal in one distillation run.

`twelvelabs_analysis_job.schema.json` binds one authorized source hash to a ready knowledge-store
item, interval, prompt, and existing candidate concepts. Jockey receives
`twelvelabs_semantic_response.schema.json` as its structured-output contract. The same schema is
validated locally before immutable ingestion.

## Query result contract

The query request validates against `reasoning_query.schema.json`. The returned explanation is a
runtime object rather than a persisted record. Each path row includes `direction`, `transition`,
`family`, and `policy_version`. `knowledge_gap.status` is `none`, `partial`, or `missing`;
`should_retrieve` is true for partial or missing coverage and `suggested_query` contains the
uncovered terms. Compiled output preserves the path, edge types, alternative valid paths, rejected
concepts, conflicts, evidence, source references, and knowledge-gap decision.

`context_bundle.schema.json` validates the read-only client package. The bundle preserves the gated
concepts, typed paths, active provider/model mappings, deduplicated source and evidence references,
external passages, conflicts, rejections, and knowledge gap. It labels repository authority,
immutable evidence, rebuildable derived signals, and untrusted external evidence separately.
`budget_report.used_tokens` estimates the complete canonical bundle, including its envelope and
omission report, with UTF-8 byte length divided by four and rounded up.

`normalized_intent.schema.json` validates the provider-neutral user-intent boundary. It contains
request text and overrides, normalized intent fields, selected routing profiles, explicit
requirements, the safe knowledge query, required and excluded layers, conflict dispositions,
uncertainties, and policy versions. It is a returned runtime object, not a curated intent record;
`intent.schema.json` continues to own recurring goals promoted into `curated/intents.jsonl`.

## Schema routing

| Store | Schema |
|---|---|
| `lab/concepts.jsonl` | `concept.schema.json` |
| `curated/edges.jsonl` | `edge.schema.json` |
| `curated/rules.jsonl` | `rule.schema.json` |
| `curated/intents.jsonl` | `intent.schema.json` |
| `curated/mappings.jsonl` | `mapping.schema.json` |
| `staging/proposals.jsonl` | `proposal.schema.json` |
| distillation input objects | `distillation_batch.schema.json` |
| `staging/distillation_runs.jsonl` | `distillation_run.schema.json` |
| `immutable/flights.jsonl` | `flight.schema.json` |
| `immutable/runs.jsonl` | `run.schema.json` |
| `immutable/pegasus_observations.jsonl` | `pegasus_observation.schema.json` |
| `immutable/measurement_observations.jsonl` | `measurement_observation.schema.json` |
| learned edges inside `derived/weights.json` | `learned_weight.schema.json` |
| query request objects | `reasoning_query.schema.json` |
| read-only client context objects | `context_bundle.schema.json` |
| provider-neutral normalized intent objects | `normalized_intent.schema.json` |
| TwelveLabs extraction job objects | `twelvelabs_analysis_job.schema.json` |
| Jockey structured response objects | `twelvelabs_semantic_response.schema.json` |
