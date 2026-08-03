# RUNBOOK: TwelveLabs Jockey extraction in the Pegasus semantic lane

**Trigger phrases:** "Pegasus extraction", "run Pegasus on this clip", "TwelveLabs integration",
or "analyze this video with Jockey".

This lane answers what appears to happen, roughly when, and what it may mean. It does not measure
joint angles, force, contact, depth, FACS intensity, or sub-frame timing. Those claims belong in the
measurement lane.

## 1. Install and verify

The repository pins `twelvelabs==1.3.1` because the v1.3 Jockey Responses surface is a research
preview. Jockey is the public agent name accepted by the current Responses API. That endpoint does
not expose an underlying Pegasus model selector, so records must say `model: jockey`, not
`pegasus1.5`.

```bash
python3 -m venv work/.venv-second-brain
source work/.venv-second-brain/bin/activate
python3 -m pip install -r lab/second_brain/requirements.txt
export TWELVE_LABS_API_KEY="<secret>"
python3 -m lab.second_brain.src.pegasus doctor
```

`doctor` reports only booleans and versions. It never prints the key. A ready configuration shows
SDK 1.3.1, an API key, and a knowledge-store ID.

## 2. Create a dedicated store and add media

Use a dedicated one-item store for sensitive extraction. Jockey selections are a strong prompt
preference, not a hard access-control boundary.

```bash
python3 -m lab.second_brain.src.providers.twelvelabs create-store \
  "cpcs-authorized-clip"

export TWELVE_LABS_KNOWLEDGE_STORE_ID="<returned-ks-id>"

python3 -m lab.second_brain.src.providers.twelvelabs add-media \
  "$TWELVE_LABS_KNOWLEDGE_STORE_ID" video \
  --file "/absolute/path/to/authorized-video.mp4"
```

The adapter accepts either `--file` or a direct raw-media `--url`. It creates the asset once, polls
with a deadline, creates the store item once, then polls indexing with a second deadline. Save the
returned `asset.id` and `item.id`; those IDs are the resume boundary after any interruption.

Current direct-upload limits enforced by the adapter are 200 MB for local video and 32 MB for local
images. Public URLs must be direct HTTP or HTTPS media links. Knowledge stores accept video and
image items.

## 3. Define one governed analysis job

Hash the exact authorized source:

```bash
shasum -a 256 "/absolute/path/to/authorized-video.mp4"
```

Create an ignored work file such as `work/twelvelabs/job.json`:

```json
{
  "job_id": "tl_job_product_reveal_001",
  "knowledge_store_id": "ks_replace_me",
  "item_id": "ksi_replace_me",
  "source_video": {
    "asset_ref": "asset_replace_me",
    "sha256": "replace_with_64_lowercase_hex_characters",
    "rights_scope": "original"
  },
  "interval": {
    "source_start_s": 0.0,
    "source_end_s": 12.0
  },
  "prompt": "Identify entities, beats, actions, camera behavior, performance, affect, audio, and marketing functions.",
  "instructions": "Use neutral actor labels and flag ambiguity caused by cuts or occlusion.",
  "candidate_concepts": [],
  "created_at": "2026-07-30T00:00:00Z"
}
```

The `asset_ref` must match the asset attached to `item_id`. The adapter refuses an unready item,
an asset mismatch, an invalid rights scope, or timestamps outside the requested source interval.

## 4. Extract and ingest

```bash
python3 -m lab.second_brain.src.pegasus extract \
  work/twelvelabs/job.json
```

One successful run performs this fixed sequence:

1. Validate the job and bind it to the ready store item.
2. Send the local semantic schema to Jockey as strict structured output.
3. Save canonical request and SDK-response snapshots under `work/twelvelabs/<job_id>/`.
4. Validate every semantic field, evidence class, confidence, and timestamp locally.
5. Append one hash-chained immutable observation and distill every included knowledge proposal.

The immutable hash points to the exact canonical bytes in `response.sdk.json`. The run also records
the API version, SDK version, store ID, item ID, response ID, session ID, and prompt hash. Repeating
the same job and provider response is idempotent. A changed response under the same job ID is a
collision and is refused.

## 5. Search and embeddings

Search reads every result page while preserving the original query, filter, modalities, grouping,
page size, and metadata flags:

```bash
python3 -m lab.second_brain.src.providers.twelvelabs search \
  "$TWELVE_LABS_KNOWLEDGE_STORE_ID" \
  "moments where the product is revealed"
```

Marengo 3.0 embeddings support `video`, `audio`, `image`, `text`, and `multi_input`:

```bash
python3 -m lab.second_brain.src.providers.twelvelabs embed text \
  --text "a direct product reveal with a proof beat"
```

For media embeddings, first run `upload <video|audio|image> --file <path>` and pass the returned
asset ID to `embed <type> --asset-id <id>`. Multi-input embeddings accept one text value and up to
10 repeated `--image-asset-id` values.

The provider module returns search and embedding data but cannot write curated, immutable, or
staging knowledge. Only `pegasus.py` may ingest semantics, and every external proposal must have a
deterministic distillation-run lineage before promotion.

## Failure rule

If credentials, a store, an authorized source, or a completed structured response is unavailable,
stop before appending immutable evidence. Request and provider-response snapshots may remain in
ignored `work/` for diagnosis. Fake-client tests prove the contract only; they are not evidence
that TwelveLabs analyzed a production video.
