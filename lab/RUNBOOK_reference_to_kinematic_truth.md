# RUNBOOK — reference video → kinematic truth → regenerate → verify

The full breakdown→reconstruction loop (paper §30): take an authorized reference clip, extract its
motion through the **two lanes** (semantic + measurement), reverse-compile into a v005-style numeric
canonical-truth JSON, regenerate, and round-trip-verify. Follows the paper's §30.28 Minimum Viable
Implementation tiers — each tier is independently useful; stop at the depth the task needs.

```
reference.mp4
  → [1] manifest + proxies (local script)
  → [2] semantic lane: Pegasus/Gemini beats & intent
  → [3] measurement lane: pose tracks (the "exact movement" bridge)
  → [4] merge → Video Observation Graph
  → [5] reverse-compile → v005-style kinematic JSON  (identity/wardrobe/setting SWAPPED)
  → [6] regenerate (paste JSON — authoring_layers: json_canonical_only precedent)
  → [7] round-trip verify (re-extract the generated clip, diff vs the score)
  → [8] log variant + run in the lab
```

**Rights gate (Stage 0, non-negotiable):** analyze only media you're authorized to analyze. The loop
reconstructs *structure* — timing, trajectories, movement quality, camera grammar. Identity, voice,
logos, and any distinctive/recognizable choreography are **swap** fields, never cloned.

---

## Prereqs (one-time)

```bash
cd research/CPCS_FACS_Laban_AI_Video_Research_Package_v1.2
python3 -m pip install -r requirements.txt     # needs Python 3.10+
ffmpeg -version && ffprobe -version            # both must exit 0
cd ../../
python3 -m pip install -r requirements-measurement.lock
```

## Step 1 — Normalize the source (Tier 1; local, no upload)

```bash
python scripts/extract_video_manifest.py /path/to/reference.mp4 \
  --output-dir work/ref_001 \
  --analysis-fps 24 \
  --semantic-fps 1 \
  --scene-threshold 0.35
```

Checkpoints (per package README): `source_manifest.json` (SHA-256 + timebase), `source_probe.json`,
`analysis_proxy.mp4` (constant 24fps — the measurement lane's clock), `semantic_frames/`,
`shot_candidates.json`, and `audio_16k_mono.wav` when audio exists.

## Step 2 — Semantic lane: Pegasus/Gemini (Tier 1–2)

> Full dedicated workflow (passes, provenance, record normalization): `RUNBOOK_pegasus_extraction.md`.

What this lane is FOR: beats, intent, action atoms, exchange structure — **not** exact motion
(~1 fps sampling; never treat it as sub-frame truth).

1. Segmentation pass: use `prompts/twelvelabs_pegasus_segment_definitions.json` (editorial_shots,
   performance_beats, action_events, ugc_marketing_functions, ambiguities) or the Gemini prompt
   (`prompts/GEMINI_VIDEO_TO_CPCS_PROMPT.md`) run as bounded per-domain passes.
2. Movement-detail pass: the hand/body movement-analyst prompt (skill
   `references/method_details.md` §5) → time-indexed segments with `laban`, `action_atom`,
   `recreation_note`, `high_fps_review`.
3. **Fast motion:** clip to just the action and upload a **slowed proxy (0.25×–0.5×)**, then multiply
   reported times back by the slow factor. Anything flagged `high_fps_review` must be confirmed by
   the measurement lane, not trusted from semantics.

## Step 3 — Measurement lane: pose tracks (Tier 2→3; the exactness bridge)

This is what turns "he throws a right punch" into `{"t":1.0,"x":0.2,"y":0.3,"z":0.8}`.

- **Tier 2 (2D, do this first) — helper script provided:**

  ```bash
  # Exact optional runtime versions are declared separately from the core release.
  python3 -m pip install -r requirements-measurement.lock
  # Multi-person MediaPipe Tasks model. Record its release/version with the job.
  curl -L -o work/pose_landmarker_full.task \
    https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task

  python3 lab/scripts/extract_pose_tier2.py \
    --manifest work/ref_001/source_manifest.json \
    --rights-scope authorized \
    --model work/pose_landmarker_full.task \
    --model-version pose-landmarker-full-float16-reviewed \
    --start 0 --end 8 --num-poses 2 --keyframe-interval 0.5
  ```

  Outputs under `work/measurements/<pose_job_id>/`: the exact request, dense
  `raw_frames.jsonl`, and a validated `cpcs.measurement_batch/1.0`. The batch contains keyframed
  joint tracks for every detected actor and is a review candidate, not immutable truth. The
  adapter calls the detector once per selected frame, assigns actor_A to the leftmost first-seen
  person, counts possible swaps, and drops landmarks below the declared visibility threshold. The
  deprecated single-person MediaPipe API is not used; a Tasks model is mandatory.
- **Tier 3 (3D, when depth matters):** add monocular 3D human reconstruction + camera solve to
  separate camera motion from subject motion, derive root motion in meters, contact inference
  (nearest-approach between striking region and target region → contact candidates with distance +
  confidence), and Laban proxies (§30.15: speed/accel → Time, path directness → Space, smoothness →
  Flow, vertical drop/impact → Weight).
- Honest bound: monocular 3D is **estimated, not mocap**. Record units + coordinate system on every
  track; keep evidence class `detected`/`inferred`, never `measured` unless it truly is.

## Step 4 — Review, admit, and merge into the Video Observation Graph

Review the candidate batch, then use the curator operation to append it. Authorization is bound to
the exact batch bytes:

```bash
cpcs record.measurement --role curator --input work/ref_001/measurement-record.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Admit reviewed pose detections for this exact source"

cpcs analyze.cascade --role curator --input work/ref_001/source-cascade.json \
  --authorize-as Kingsley-Cyber \
  --authorization-reason "Run the exact Pegasus and measurement fusion cascade"
```

The cascade names the admitted `measurement_observation_ids`, exact local source path and hash,
TwelveLabs asset registration, authorized interval, semantic profiles, and optional intent context.
It normalizes both lanes, validates a content-addressed VOG, preserves contradictions without
averaging confidence, and optionally returns the reverse-resolved canonical score. A semantic label
may name a beat while the detected pose track supplies its image-space timing; neither silently
overwrites the other.

## Step 5 — Reverse-compile into v005-style kinematic truth

When `intent_context` and required score assets are supplied to `cpcs.analyze.cascade`, the existing
reverse compiler maps the VOG through the universal score resolver. The proven shape remains
`variants/v005_combat_kinematic_json.jsonc`; its relevant blocks are
`blk_kinematic_skeleton`, `blk_contact_solver`, `blk_effort_vectors`,
`blk_camera_keyframes`, and `blk_hard_constraints_verify`:

- `timebase` from the manifest (fps, duration, frame_count).
- Per actor: `root_motion.positions` + `joint_tracks.<limb>.positions`, **keyframed every ~0.5s**
  from the pose tracks (denser only where the action demands it); annotate intent inline
  (windup/contact/recoil/reset) from the semantic lane's beats.
- `contacts[]` from contact inference: region_a/region_b, start/end from detected nearest-approach,
  `type: impact | near_miss | grasp_and_shove`, `tolerance_m: 0.05`.
- `lab_control` effort vectors per interval from the Laban proxies.
- `camera.positions/orientations` from the camera solve (or authored simply if Tier 2).
- `hard_constraints` + `verification` blocks (identity lock, no slow-mo/vfx if that's the intent,
  contact timing tolerance 50ms).
- **Swap layer:** replace identity, wardrobe, setting, and any distinctive choreography signature;
  keep timing, trajectories, quality.

## Step 6 — Regenerate

Paste the JSON alone (`authoring_layers: json_canonical_only` — the v005 precedent), or hybrid it
with a prose look/skin block for stylized/photoreal surfaces. For anime: same truth,
`medium: anime_cel` (queued experiment).

## Step 7 — Round-trip verify (§30.26, Tier 4)

Run Steps 1–3 **on the generated clip** with the same detector model and settings used for the
source. Then call the public comparator with the exact materialized build, runtime job, selected
artifact, both candidate batches, an explicitly reviewed actor mapping, selected joints, and
declared thresholds:

```bash
cpcs verify.reference.roundtrip --role operator \
  --input work/ref_001/reference-round-trip.json
```

The operation verifies the build and runtime result, hashes the retrieved artifact bytes, rejects a
generated batch from different media, rejects detector-setting drift, phase-aligns each requested
track, and writes `cpcs.reference_round_trip_report/1.0` under ignored application work state. It
reports trajectory cosine similarity, absolute and translation-aligned 2D RMSE, duration error,
path-length ratio, missing tracks, and actor-swap suspicion. Thresholds are explicit input because
the current repository has no empirical basis for universal pass limits.

For Tier 2 this closes the automated detected-track source-versus-generated loop. It does not yet
provide these Tier 3 measures:
- contact times within **50 ms** or contact distance within **0.05 m**;
- continuity across cuts, independently verified identity persistence, or camera-separated motion;
- condensed §30.29 gate: every numeric track has units + coordinate system · camera motion separated
  from subject motion where possible · contacts labeled confirmed/near/occluded/unknown · Laban and
  affect fields marked interpretive · contradictions retained · generated result re-extracted and
  compared · rights scope confirmed.

## Step 8 — Log it in the lab

New variant (`v0NN_<source>_reconstruction`, lever_tags incl. `control_paradigm:
numeric_canonical_truth`, `authoring_layers`), a run row in `runs/results.csv` with the round-trip
metrics in notes, and — if the loop confirms or refutes a pattern — update `registry.yaml`.

Also seal the full experiment design through `lab.second_brain.src.record.seal_flight` before the
first render, then record the verified result through `cpcs record.render` with a complete
`cpcs.experiment_receipt/1.0`. The immutable record carries the flight hash, exact prompt
hash, model version, seed, compiler version, repository revision, artifact hash, metrics, prior
record hash, and record hash. A changed arm, concept set, seed, provider, model, or compiler setting
requires a new flight ID.

---

## Tier ladder (stop where the task is satisfied)

| Tier | Adds | Gets you | Cost |
|---|---|---|---|
| 1 | manifest + shots + Pegasus beats | semantic reverse storyboard (what/when-roughly) | minutes |
| 2 | actor tracking + 2D pose + action events | movement shape, gesture paths, exchange timing | + a pose tool |
| 3 | 3D reconstruction + camera solve + contacts + Laban ops | **exact-ish depth/movement/motion** → v005-grade truth | + heavier CV |
| 4 | re-extraction + compliance diff + patch revision | closed loop; auto-scored lab runs | + the verify pass |

Today's lab state: Tier 1 has historical use. Tier 2 now has an offline extraction and automated
source-versus-generated comparison contract with fake-detector public canaries but no approved
real-clip qualification. Tier 3 remains unimplemented. Tier 4 works locally for generated-render
score compliance and Tier 2 reference-motion round-trip diagnostics; provider and detector quality
remain external qualification gaps.
