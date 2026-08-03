# RUNBOOK: authorized TwelveLabs video-analysis cascade

**Trigger phrases:** "Pegasus extraction", "run Pegasus on this clip", "TwelveLabs integration",
or "analyze this authorized video".

This workflow maps one exact source, segments it, performs targeted deep analysis, fuses optional
local measurements, builds a Video Observation Graph (VOG), reverse-compiles observations through
the universal score kernel, and only then appends one immutable semantic record. Pegasus semantics
remain `inferred` or `interpreted`; exact joints, force, masks, contact timing, depth, and FACS
intensity belong to a separate local-measurement lane.

## 1. Install and inspect readiness

```bash
python3 -m venv work/.venv-second-brain
source work/.venv-second-brain/bin/activate
python3 -m pip install -r lab/second_brain/requirements.txt
export TWELVE_LABS_API_KEY="<secret>"
python3 -m lab.second_brain.src.pegasus doctor
python3 -m lab.second_brain.src.pegasus profiles
```

The adapter pins TwelveLabs API v1.3 and SDK 1.3.1. `doctor` reports only configuration booleans and
versions. Analyze, Segment, Batch, knowledge-store Search, Jockey Responses, and Marengo embeddings
have separate job schemas and transports; none can write repository authority directly.

## 2. Register the exact authorized source

Hash the local bytes first:

```bash
shasum -a 256 "/absolute/path/to/authorized-video.mp4"
```

Create `work/twelvelabs/asset-job.json`:

```json
{
  "schema": "cpcs.twelvelabs_asset_job/1.0",
  "job_id": "tl_asset_product_reveal_001",
  "media_type": "video",
  "source": {
    "file_path": "/absolute/path/to/authorized-video.mp4",
    "sha256": "replace_with_64_lowercase_hex_characters"
  },
  "knowledge_store_id": null,
  "rights_scope": "original",
  "created_at": "2026-08-03T00:00:00Z"
}
```

```bash
python3 -m lab.second_brain.src.pegasus run-job \
  work/twelvelabs/asset-job.json
```

The runner verifies local bytes, uploads once, waits with a deadline, and saves the exact request,
raw SDK response, and normalized registration under ignored `work/twelvelabs/<job_id>/`. Set
`knowledge_store_id` only when this same asset also needs Search or Jockey. Store membership is not
required for isolated Pegasus Analyze or Segment.

## 3. Define the bounded cascade

Run `ffprobe` before choosing the interval. TwelveLabs timestamps are absolute source timestamps;
the adapter independently runs `ffprobe` and rejects authorization outside the local file.

```bash
ffprobe -v error -show_entries format=start_time,duration \
  -of default=noprint_wrappers=1 "/absolute/path/to/authorized-video.mp4"
```

Create `work/twelvelabs/cascade.json`, replacing `asset_ref` with the returned asset ID:

```json
{
  "schema": "cpcs.video_analysis_cascade/1.0",
  "cascade_id": "tl_cascade_product_reveal_001",
  "source": {
    "source_id": "source_product_reveal_001",
    "asset_ref": "asset_replace_me",
    "asset_job_id": "tl_asset_product_reveal_001",
    "local_path": "/absolute/path/to/authorized-video.mp4",
    "sha256": "replace_with_the_same_source_hash",
    "rights_scope": "original"
  },
  "authorized_interval": {"start_s": 0.0, "end_s": 12.0},
  "source_map_profile": "pegasus.source_map/1.0",
  "segment_profile": "pegasus.product_interaction/1.0",
  "deep_analysis_profiles": [
    "pegasus.ugc_structure/1.0",
    "pegasus.performance/1.0",
    "pegasus.camera_edit/1.0"
  ],
  "candidate_concepts": [],
  "measurement_observation_ids": [],
  "created_at": "2026-08-03T00:00:00Z"
}
```

Use only profile IDs returned by the `profiles` command. The source-map pass uses exact-video
Analyze only when the authorized interval covers the complete probed source; otherwise it uses a
clipped Analyze request. Segment returns typed intervals; the current cost-bounded cascade selects
the first deterministic interval for each deep profile, and every deep pass remains inside
that authorization. Provider clips must be at least four seconds.

## 4. Build intent context and reverse-compile

```bash
python3 -m lab.second_brain.src.intent context \
  "Show how this product is used in a clear recommendation video" \
  > work/twelvelabs/intent-context.json
```

Create `work/twelvelabs/score-assets.json` with the asset roles reported as missing by the normalized
intent. Example:

```json
[
  {
    "asset_id": "asset_product_reference",
    "role": "product_reference",
    "content_hash": "sha256:replace_with_64_lowercase_hex_characters",
    "rights_basis": "owner_authorized"
  }
]
```

```bash
python3 -m lab.second_brain.src.pegasus cascade \
  work/twelvelabs/cascade.json \
  --intent-context work/twelvelabs/intent-context.json \
  --score-assets work/twelvelabs/score-assets.json
```

The fixed cascade is:

```text
local hash + ffprobe
→ broad Analyze source map
→ targeted Segment
→ clipped deep Analyze passes
→ local-measurement normalization
→ contradiction-preserving VOG fusion
→ VOG-to-universal-score overlay
→ immutable Pegasus append
```

Every request and raw response is saved and hashed. Local schemas validate all semantic timestamps,
evidence classes, provenance, source hashes, and rights scopes. Measurement and semantic confidence
are never averaged. Conflicts stay in the VOG for review. The universal score remains
provider-neutral and is resolved by `lab/compiler/score.py`, not by the media-analysis adapter.

## 5. Choose the correct surface

| Need | Contract and surface |
|---|---|
| One exact video or one authorized clip | `twelvelabs_analyze_job.schema.json` → Pegasus Analyze |
| Repeated occurrences or temporal categories | `twelvelabs_segment_job.schema.json` → Pegasus Segment |
| Same analysis across many assets | `twelvelabs_batch_job.schema.json` → Pegasus Batch |
| Literal matching clips in named store items | `twelvelabs_search_job.schema.json` → knowledge-store Search |
| Corpus patterns or cross-video entity tracking | `twelvelabs_jockey_job.schema.json` → Jockey Responses |
| Custom similarity or multimodal embeddings | `twelvelabs_marengo_job.schema.json` → Marengo 3.0 |
| Pose, optical flow, masks, contact, or exact geometry | local measurement tools, never Pegasus semantics |

Run any single provider job with:

```bash
python3 -m lab.second_brain.src.pegasus run-job work/twelvelabs/<job>.json
```

Search is filtered to the job's explicit `authorized_item_ids` before the request. Jockey is limited
to explicit item selections. Batch refuses partial success. Raw Analyze artifacts can be
renormalized with `renormalize_analyze_artifacts()` without another provider call.

## Failure and replay rules

- Provider request snapshots are written before external execution.
- Failed, truncated, malformed, unsafe, out-of-bounds, mixed-source, or partial responses never
  append immutable evidence.
- Work artifacts may remain for diagnosis; they are ignored and carry no repository authority.
- Replaying identical jobs and raw responses produces the same VOG, score ID, and immutable record.
- A changed artifact under the same job ID is a collision and is refused.
- A successful fake-client canary proves the local contract, not a production TwelveLabs result.

A live production claim requires SDK 1.3.1, a configured API key, authorized media, completed
provider responses, archived work artifacts, and a green final repository gate.
