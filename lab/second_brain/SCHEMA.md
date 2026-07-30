# Second-brain record contracts

This file defines the semantic contract. JSON Schemas under `schemas/` enforce proposal and Pegasus
ingest at bootstrap; the implementation agent must add machine schemas for the remaining records
before enabling their writers.

## Common rules

- UTF-8 JSONL: one complete JSON object per line.
- IDs are durable literals. Existing concept `c_*` IDs are never renamed or recomputed.
- Timestamps are RFC 3339 with an explicit offset or `Z`.
- Hashes use `sha256:<lowercase-hex>`.
- Canonical hashing serializes JSON with sorted keys and no insignificant whitespace.
- Source evidence stores identifiers and locations, not unbounded copyrighted passages.
- Unknown values are `null`; do not invent defaults.
- Immutable records may be appended only. Corrections append superseding records; they do not edit history.

## Curated concept

The current `lab/concepts.jsonl` fields remain valid. New fields are additive during migration.

```json
{
  "id": "c_chiaroscuro",
  "kind": "technique",
  "name": "Chiaroscuro lighting",
  "what": "High key-to-fill contrast that sculpts form through deep shadow.",
  "use_when": "dramatic reveal or facial shape emphasis",
  "nl_triggers": ["dramatic side light", "deep shadow", "rembrandt key"],
  "pairs_with": ["c_silhouette_readability"],
  "conflicts": ["c_flat_morning_diffusion"],
  "status": "partial",
  "evidence": [],
  "source": ["rag://cinematography/alton#p88"],
  "layer": "lighting",
  "encodable_as": ["prose", "numeric"],
  "params": {
    "key_to_fill_ratio": {"type": "range", "min": 2.0, "max": 16.0, "unit": "ratio"}
  },
  "curation": {
    "origin": "polymath_proposal",
    "proposal_id": "proposal_000123",
    "promoted_by": "Kingsley-Cyber",
    "promoted_at": "2026-07-29T23:00:00-06:00"
  }
}
```

`layer` is a free string. New layers do not require migrations.

## Authored edge

Authored edges live separately from learned edges and are human-diffable.

```json
{
  "id": "edge_000117",
  "u": "c_chiaroscuro",
  "v": "c_flat_morning_diffusion",
  "type": "conflicts_with",
  "context": "raw_morning_ugc",
  "note": "Strong sculpted contrast conflicts with the flat ambient-light target.",
  "authored_by": "rag_proposal_promoted",
  "source_evidence": [{"source_id": "rag://cinematography/alton", "locator": "p.88"}],
  "created_at": "2026-07-29T23:00:00-06:00"
}
```

Allowed bootstrap types:

```text
pairs_with
conflicts_with
requires
refines
part_of
alternative_to
maps_to
encodes_as
valid_for
invalid_for
sourced_from
```

## Proposal

Polymath, Pegasus, and reflection may propose records. They may not promote them.

```json
{
  "proposal_id": "proposal_000123",
  "proposal_type": "concept",
  "status": "pending",
  "proposed_record": {},
  "source_evidence": [
    {
      "source_id": "rag://cinematography/alton",
      "locator": "p.88",
      "claim": "High contrast sculpts facial form.",
      "content_sha256": "sha256:..."
    }
  ],
  "dedup_candidates": [{"id": "c_existing", "score": 0.83}],
  "created_by": "polymath_mcp",
  "created_at": "2026-07-29T23:00:00-06:00"
}
```

## Intent

```json
{
  "id": "intent_0007",
  "canonical": "Three-second product reveal with dreamy morning lighting for vertical social video.",
  "motion_class": "reveal",
  "duration_s": 3.0,
  "aspect": "9:16",
  "surface": "reels",
  "requirements": ["product_visible", "reveal_readable"],
  "embedding_ref": "qdrant:intents:0007",
  "created_at": "2026-07-29T23:00:00-06:00"
}
```

The embedding proposes duplicates; the literal ID establishes identity.

## Mapping

```json
{
  "id": "mapping_000212",
  "concept_id": "c_chiaroscuro",
  "target_type": "control",
  "target_id": "lighting.key_to_fill_ratio",
  "encoding": "numeric",
  "mapping": {"parameter": "key_to_fill_ratio", "unit": "ratio"},
  "loss": "low",
  "source_evidence": [{"source_id": "rag://cinematography/alton", "locator": "p.88"}]
}
```

## Flight

A flight is editable only while `status=draft`. The first associated run seals it.

```json
{
  "id": "flight_0031",
  "status": "sealed",
  "intent_id": "intent_0007",
  "arms": [
    {"arm": "A", "paradigm": "prose", "encoding": "nl", "concept_ids": ["c_chiaroscuro"]},
    {"arm": "B", "paradigm": "numeric", "encoding": "json", "concept_ids": ["c_chiaroscuro"]}
  ],
  "provider": "wan_local",
  "model_version": "wan2.2",
  "seed": 12345,
  "sealed_at": "2026-07-29T23:00:00-06:00",
  "record_hash": "sha256:..."
}
```

## Render run

A run must be self-describing enough to support deterministic reflection without reading mutable
current concept content.

```json
{
  "id": "run_00219",
  "flight_id": "flight_0031",
  "flight_sha256": "sha256:...",
  "intent_id": "intent_0007",
  "motion_class": "reveal",
  "arm": "A",
  "paradigm": "prose",
  "encoding": "nl",
  "concept_refs": [
    {"id": "c_chiaroscuro", "revision": 1, "content_sha256": "sha256:..."}
  ],
  "provider": "wan_local",
  "model_version": "wan2.2",
  "seed": 12345,
  "prompt_sha256": "sha256:...",
  "prompt_path": "outputs/flight_0031_A.txt",
  "compiler_version": "cpcs-compiler/0.1.0",
  "control_plane_commit": "<git-sha>",
  "output_sha256": "sha256:...",
  "output_path": "renders/flight_0031_A.mp4",
  "metrics": {"rating": 4, "completion": null, "saves": null},
  "rendered_at": "2026-07-29T23:00:00-06:00",
  "previous_record_hash": "sha256:...",
  "record_hash": "sha256:..."
}
```

## Pegasus video observation

The machine contract is `schemas/video_observation.schema.json`.

Observations identify the source, extraction configuration, source-clock interval, stable entities,
beats, atomic events, semantic signature, uncertainty, alternatives, and provenance. Semantic fields
are never labeled `measured` unless a named measurement tool produced them in a separate record.

## Learned edge

```json
{
  "u": "c_chiaroscuro",
  "v": "intent_class:reveal",
  "type": "promotes",
  "weight": 0.71,
  "n_obs": 9,
  "evidence": ["run_00219", "run_00231"],
  "context": "product_reveal",
  "provider": "wan_local",
  "model_version": "wan2.2",
  "algorithm_version": "reflect/1.0.0",
  "last_reinforced": "2026-07-29T23:00:00-06:00",
  "decay": 0.98
}
```

A learned edge is invalid without non-empty run evidence, model version, context, and algorithm
version.

Causal `promotes` additionally requires an attributable contrast. Otherwise use:

```text
associated_with_success
co_success
confounded_with
contradicts
```

## Derived insight

```json
{
  "id": "insight_000044",
  "statement": "Chiaroscuro is associated with stronger reveal ratings on wan2.2.",
  "scope": {"context": "product_reveal", "provider": "wan_local", "model_version": "wan2.2"},
  "relationship_type": "associated_with_success",
  "evidence": ["run_00219", "run_00231"],
  "algorithm_version": "reflect/1.0.0",
  "generated_at": "2026-07-29T23:00:00-06:00"
}
```

Insights are disposable. Promotion creates a separate curated proposal and preserves the insight ID as
origin; reflection never writes a curated record directly.
