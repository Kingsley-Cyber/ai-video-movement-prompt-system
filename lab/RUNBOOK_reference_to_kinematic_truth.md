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
  python3 -m pip install mediapipe opencv-python jsonschema   # one-time
  # multi-person model (needed for two-fighter scenes; UGC single-person works without it):
  curl -L -o work/pose_landmarker_full.task \
    https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task

  python3 lab/scripts/extract_pose_tier2.py \
    --manifest work/ref_001/source_manifest.json \
    --model work/pose_landmarker_full.task --num-poses 2 \
    --keyframe-interval 0.5
  ```

  Outputs: `pose_frames_raw.jsonl` (dense per-frame landmarks — Tier-3 feedstock) and
  `observations/pose_tier2.jsonl` — keyframed joint tracks (13 joints + hip-midpoint root per actor)
  that **validate against `CPCS_Video_Observation_Record_Schema.json`** and feed Step 4's merge
  directly. Greedy nearest-centroid actor tracking (actor_A = leftmost first seen) with
  possible-swap frames counted; landmarks below `--min-visibility` dropped. Without `--model` it
  falls back to single-person mode (fine for UGC, wrong for fights).
- **Tier 3 (3D, when depth matters):** add monocular 3D human reconstruction + camera solve to
  separate camera motion from subject motion, derive root motion in meters, contact inference
  (nearest-approach between striking region and target region → contact candidates with distance +
  confidence), and Laban proxies (§30.15: speed/accel → Time, path directness → Space, smoothness →
  Flow, vertical drop/impact → Weight).
- Honest bound: monocular 3D is **estimated, not mocap**. Record units + coordinate system on every
  track; keep evidence class `detected`/`inferred`, never `measured` unless it truly is.

## Step 4 — Merge into the Video Observation Graph

Normalize both lanes' outputs to `CPCS_Video_Observation_Record_Schema.json`, then:

```bash
python scripts/merge_video_observations.py \
  --manifest work/ref_001/source_manifest.json \
  --inputs work/ref_001/observations/*.jsonl \
  --output work/ref_001/video_observation_graph.json \
  --conflicts work/ref_001/conflicts.json

python scripts/validate_video_observation_graph.py \
  work/ref_001/video_observation_graph.json \
  --schema schemas/CPCS_Video_Observation_Graph_Schema.json \
  --record-schema schemas/CPCS_Video_Observation_Record_Schema.json
```

Accept only `schema_valid: true` AND `semantic_valid: true`. Contradictions between lanes are
**retained**, not averaged — semantic said 1.4s, pose says 1.55s → the measured track wins for
timing; the semantic label still names the beat.

## Step 5 — Reverse-compile into v005-style kinematic truth

Map the VOG into the proven shape (`variants/v005_combat_kinematic_json.jsonc` is the template;
blocks: `blk_kinematic_skeleton`, `blk_contact_solver`, `blk_effort_vectors`, `blk_camera_keyframes`,
`blk_hard_constraints_verify`):

- `timebase` from the manifest (fps, duration, frame_count).
- Per actor: `root_motion.positions` + `joint_tracks.<limb>.positions`, **keyframed every ~0.5s**
  from the pose tracks (denser only where the action demands it); annotate intent inline
  (windup/contact/recoil/reset) from the semantic lane's beats.
- `contacts[]` from contact inference: region_a/region_b, start/end from measured nearest-approach,
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

Run Steps 1–3 **on the generated clip**, then diff against the authored score:
- contact times within **50 ms**; contact distance within **0.05 m** (where 3D exists);
- trajectory shape (per-limb path correlation), continuity (no cuts), identity persistence;
- condensed §30.29 gate: every numeric track has units + coordinate system · camera motion separated
  from subject motion where possible · contacts labeled confirmed/near/occluded/unknown · Laban and
  affect fields marked interpretive · contradictions retained · generated result re-extracted and
  compared · rights scope confirmed.

## Step 8 — Log it in the lab

New variant (`v0NN_<source>_reconstruction`, lever_tags incl. `control_paradigm:
numeric_canonical_truth`, `authoring_layers`), a run row in `runs/results.csv` with the round-trip
metrics in notes, and — if the loop confirms or refutes a pattern — update `registry.yaml`.

---

## Tier ladder (stop where the task is satisfied)

| Tier | Adds | Gets you | Cost |
|---|---|---|---|
| 1 | manifest + shots + Pegasus beats | semantic reverse storyboard (what/when-roughly) | minutes |
| 2 | actor tracking + 2D pose + action events | movement shape, gesture paths, exchange timing | + a pose tool |
| 3 | 3D reconstruction + camera solve + contacts + Laban ops | **exact-ish depth/movement/motion** → v005-grade truth | + heavier CV |
| 4 | re-extraction + compliance diff + patch revision | closed loop; auto-scored lab runs | + the verify pass |

Today's lab state: Tier 1 exercised (TikTok session) · Tier 2–3 = the unexercised bridge · Tier 4 =
E-queue #1.
