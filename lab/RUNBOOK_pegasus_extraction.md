# RUNBOOK — Pegasus extraction (semantic lane)

**Trigger phrases:** "pegasus extraction", "run pegasus on this clip", "extract this video with
pegasus / twelve labs". When the user says any of these, follow this runbook.

**What Pegasus is in this system (paper §30.10):** the **semantic lane** of the two-lane
architecture — it proposes *what happens, roughly when, and why* (shots, beats, action phrases,
movement quality, UGC/marketing functions). It is **not a measurement instrument**: ~1 fps effective
sampling, no sub-frame timing, no exact kinematics, no depth. Exact motion comes from the
measurement lane (`scripts/extract_pose_tier2.py`, Tier 3). The two lanes merge in the VOG
(`RUNBOOK_reference_to_kinematic_truth.md` Step 4).

**Rights gate:** authorized media only. Never identify private persons (use `actor_A`, `actor_B`).
Flag `distinctive_choreography` when the clip is a recognizable routine — structure may be studied,
signatures get re-performed/varied, identity always swapped.

---

## Step 0 — Prereqs

- Twelve Labs account + `TWELVE_LABS_API_KEY`; an index with a **Pegasus** video-understanding model
  enabled (package templates pin `pegasus1.5` — **re-check the current model name/API version at run
  time and log what you actually used**; provider contracts drift).
- Alternative with zero API setup: the Twelve Labs Playground UI — paste the same prompts; you lose
  scripted repeatability, so save the raw response text manually.

## Step 1 — Prepare the media

1. Run main-runbook Step 1 (`extract_video_manifest.py`) so there is a `source_manifest.json` with
   SHA-256 + timebase — extraction claims must be keyed to a registered source.
2. **Clip to just the passage you care about.** Shorter interval → denser useful description.
3. **Fast motion (fights, dance, quick gestures): upload a slowed proxy at 0.25×–0.5×.** Record the
   factor. Every timestamp Pegasus returns must be **multiplied back by the factor** before it
   enters any record (a 0.25× proxy's "t=4.0s" is source t=1.0s).

## Step 2 — Pick the pass (don't run everything at once)

| Goal | Use | Asset |
|---|---|---|
| Shots, beats, action phrases, structured segmentation | **API request config** (model, temp 0.2, `time_based_metadata`, segment defs incl. `causal_phases`) | `research/.../prompts/PEGASUS_VIDEO_TO_CPCS_SEGMENTS.json` |
| Broader menu incl. UGC/marketing functions, VFX events, ambiguities (≤10 defs per request) | **Segment-definition template** | `research/.../prompts/twelvelabs_pegasus_segment_definitions.json` |
| Hand/body movement detail for **recreation** | **Movement-analyst free-form prompt** (below) | inline |
| Equivalent passes on Gemini instead of Pegasus | bounded per-domain passes | `research/.../prompts/GEMINI_VIDEO_TO_CPCS_PROMPT.md` |

### The movement-analyst prompt (recreation-oriented, session-proven)

```
You are a movement-evidence analyst. Analyze ONLY this authorized clip and produce a time-indexed
description of actor_A's HAND/ARM gestures and FULL-BODY movement, detailed enough to recreate the
motion in a video generator. Do not identify the person. Output valid JSON only.
Rules: every event has start_s and end_s; separate observed evidence from interpretation; use
"unknown" when unsupported; never invent 3D coordinates, joint angles, force, or sub-frame timing;
note occlusion/blur/cuts/slow-motion/camera-motion as confounds; set high_fps_review=true for motion
too fast to read at 1fps.
For each segment return: id, start_s, end_s, body_phase, hand{which,shape,path,amplitude,speed},
body{posture,weight_shift,torso,head,shoulders,locomotion}, action_atom, laban{weight,time,space,
flow,shape}, contact, sync, evidence_class, confidence, recreation_note (one instruction to
reproduce the exact movement). Then append: global_movement_quality, tempo_rhythm, confounds[],
high_fps_segments[], rights_sensitive (["distinctive_choreography"] if a recognizable routine, else
["none"]).
```

## Step 3 — Run and pin provenance

Whether API or Playground, **log all of**: model name, API version, run date, the prompt/definitions
digest (sha256 of the exact text sent), and the **raw response saved verbatim** to
`work/ref_NNN/pegasus_raw_<pass>.json` (+ its sha256). The package rule: templates are not clients;
provenance is what makes an extraction citable later. Parse `result.data` as JSON; retain
`finish_reason` and errors.

## Step 4 — Convert times, normalize to observation records

Write `work/ref_NNN/observations/pegasus_<pass>.jsonl` — one record per segment, conforming to
`CPCS_Video_Observation_Record_Schema.json` (strict: `additionalProperties: false`; no extra keys).

Mapping rules:

| Record field | Value |
|---|---|
| `record_id` | `pegasus.<pass>.<segment_id>` |
| `source_id` | the manifest's `source.id` |
| `time_range` | start/end **after** slow-factor conversion |
| `clock` | `source_seconds` |
| `layer` | shots→`shot` · beats→`beat` · action phrases/movement→`action` · marketing→`marketing` · vfx→`vfx` · ambiguities→`quality` |
| `evidence_class` | observable descriptions → `inferred` (model-proposed from pixels); functions, Laban, subtext, marketing hypotheses → `interpreted`. **Never** `measured`/`detected` for a semantic model. |
| `confidence` | the model's segment confidence (0–1) |
| `extractor` | `{name: "twelvelabs_pegasus", version: "<model you ran>", api_version: "...", verified_on: "<date>"}` |
| `evidence` | `[{asset: "source" or "analysis_proxy", locator: "t=<start>-<end>s"}]` |
| `quality_flags` | add `slowed_proxy_0.25x` when used; carry `high_fps_review` segments as `needs_measurement_confirmation` |

Worked example (a session-real segment, normalized):

```json
{"record_id": "pegasus.movement.seg_02", "source_id": "source",
 "time_range": {"start_s": 7.0, "end_s": 14.0}, "clock": "source_seconds", "layer": "action",
 "claim": {"type": "movement_segment",
   "value": {"action_atom": "reach", "hand": {"which": "right", "shape": "holding_object",
     "path": "reaches for shelf, grasps pink can, lifts to chest height"},
     "laban": {"weight": "light", "time": "sudden", "space": "direct", "flow": "bound"},
     "recreation_note": "Reach forward to shelf, grasp cylindrical object, lift to chest level."},
   "vocabulary": "lab.pegasus_movement/1.0"},
 "evidence_class": "inferred", "confidence": 0.95,
 "extractor": {"name": "twelvelabs_pegasus", "version": "pegasus1.5"},
 "evidence": [{"asset": "source", "locator": "t=7.000-14.000s"}]}
```

## Step 5 — Hand off

- **To measurement:** every `high_fps_review` segment goes to the pose lane
  (`scripts/extract_pose_tier2.py`) for confirmation — semantic timing loses to measured timing on
  conflict, but the semantic label still names the beat. Contradictions are **retained** in the VOG,
  never averaged.
- **To the VOG:** main-runbook Step 4 (`merge_video_observations.py` + validate).
- **To generation:** for a quick prose recreation, compile each segment's `recreation_note` +
  `laban` into movement-only image-to-video prompts (the session-proven walk→grab→hold pattern);
  for exact choreography, continue to Tier 3 + reverse-compile (main runbook Steps 5–7).

## Known limits (say them, don't discover them)

1 fps semantics → duplicate-looking segments over long windows (dedupe before normalizing) ·
`body_phase` often defaults to "travel" even for stationary holds (correct against pose/locomotion
evidence) · no force/contact certainty (use `contact_status`-style language, never claim impact from
semantics alone) · marketing "why it sells" claims are hypotheses, not outcomes.
