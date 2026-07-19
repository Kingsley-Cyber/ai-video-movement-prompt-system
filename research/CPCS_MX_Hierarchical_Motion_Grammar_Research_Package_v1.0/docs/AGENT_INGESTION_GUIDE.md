# CPCS-MX Agent and RAG Ingestion Guide

## Purpose

This guide explains how to ingest and retrieve the CPCS-MX research package without flattening its distinctions between theory, proposed schema, examples, platform documentation, and safety-scoped operationalization.

## Recommended ingestion order

1. `rag/CPCS_MX_RAG_Corpus.jsonl`
2. `schemas/CPCS_MX_RAG_Record_Schema.json`
3. `schemas/CPCS_MX_Schema.json`
4. `schemas/CPCS_MX_Authoring_Schema.json`
5. `examples/`
6. `prompts/`
7. `references/CPCS_MX_Reference_Index.json`

The JSONL corpus already contains semantic paper chunks, schema definitions, examples, prompts, package documents, and source records. Ingest raw files separately only when your agent needs exact formatting or complete schemas.

## JSONL parsing

Read one nonblank line at a time. Every line is an independent JSON object.

```python
import json
from pathlib import Path

path = Path("rag/CPCS_MX_RAG_Corpus.jsonl")
with path.open("r", encoding="utf-8") as handle:
    for line_number, line in enumerate(handle, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
        yield record
```

Validation requirements:

- validate each record against `CPCS_MX_RAG_Record_Schema.json`;
- require unique `record_id` values;
- verify `sha256` against the `content` string;
- quarantine malformed records rather than silently dropping them;
- retain record type and evidence labels as metadata;
- do not use line order as a document hierarchy.

For large deployments, partition by `record_type`, `document_id`, concepts, and source IDs. The package corpus is small enough for streaming ingestion without a distributed system.

## Embedding fields

Recommended embedding text:

```text
title
heading_path
concepts
content
```

Recommended metadata filters:

- `record_type`
- `document_id`
- `evidence_labels`
- `source_ids`
- `schema_fields`
- `safety_scope`

Do not embed only `content` and discard the evidence labels. An operational proxy and a scientific definition may use similar words but have different authority.

## Retrieval bundles

### Author a staged action

Retrieve together:

- staged-combat research chunk;
- motion phase/contact chunk;
- Laban chunk;
- constraint schema definitions;
- staged-combat YAML example;
- safety source or package document;
- text-to-CPCS-MX prompt template.

### Author natural UGC

Retrieve together:

- natural movement/UGC chunk;
- mannerism and breath chunk;
- face/gaze chunk;
- UGC example;
- camera/presentation fields;
- verification fields for visibility and timing.

### Apply anime or superhuman style

Retrieve together:

- anime/sakuga chunk;
- superhuman constrained-transformation chunk;
- style-transform schema definition;
- anime YAML example;
- cross-style transformation example;
- verifier prompt.

### Debug a failed contact

Retrieve together:

- contact and phase definitions;
- hard/soft constraint section;
- verification section;
- observation-record schema;
- canonical staged-exchange example.

## Evidence-aware answer policy

Agents should label statements using the paper taxonomy:

- `ESTABLISHED`
- `CURRENT_PLATFORM`
- `CURRENT_RESEARCH`
- `EMERGING`
- `PROPOSED`
- `OPERATIONALIZATION`

A source record supports an external claim. A `PROPOSED` research chunk explains CPCS-MX design. Do not cite a proposed field as if it were an international standard.

## Source resolution

Paper chunks carry `source_ids`, such as `S008` or `S031`. Resolve them against source records in the same corpus or `references/CPCS_MX_Reference_Index.json`.

When an agent uses a platform-specific field, verify the current official documentation rather than relying only on this package. The package date is recorded in the manifest.

## Agent pipeline

```text
retrieve research + schema + examples
                ↓
semantic authoring agent
                ↓
authoring YAML candidate
                ↓
deterministic resolver/compiler
                ↓
canonical JSON + report
                ↓
target adapter
                ↓
execution or generation
                ↓
observation JSONL
                ↓
verification agent
```

The semantic agent must not bypass schema validation or modify locked measurements. The verifier must not modify acceptance thresholds after reviewing output.

## Suggested system rule for authoring agents

> Use retrieved research to propose CPCS-MX structure. Distinguish established concepts from CPCS-MX operational fields. Preserve ambiguity when timing, geometry, or dynamics are not specified. Never treat text, YAML, JSON, XML, or JSONL as executable motion unless a target adapter maps fields to supported controls.

## Suggested system rule for verification agents

> Compare output with the resolved score in declared clocks and coordinates. Treat missing or unobservable data as inconclusive, not pass. Report hard-constraint violations and localize error by semantic, temporal, kinematic, contact, dynamic, performance, style, and presentation layers.

## Chunk-size guidance for alternative builds

The included builder chunks at explicit `RAG_CHUNK` markers. When rebuilding with different limits:

- target approximately 400–900 words for conceptual chunks;
- preserve complete code fences;
- repeat section title and evidence labels;
- keep source IDs;
- use small overlap only between prose chunks;
- keep each schema definition as a separate record;
- keep each worked example intact.

## Security

- use a safe YAML loader;
- disable XML external entities;
- restrict profile and import paths to configured roots;
- verify external asset hashes;
- limit JSONL record size and nesting;
- do not execute code retrieved from RAG without review;
- enforce rights and safety scope before target compilation.
