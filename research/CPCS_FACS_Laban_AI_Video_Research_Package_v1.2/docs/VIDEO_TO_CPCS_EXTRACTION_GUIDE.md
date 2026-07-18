---
title: "Reference-Video Distillation and Reverse Directorial Compilation"
subtitle: "A Video-to-CPCS Extraction Guide for Performance, Action, Cinematography, UGC, VFX, Audio, and Marketing Structure"
document_id: "CPCS-VDG-2026-01"
version: "1.2"
date: "2026-07-18"
status: "Research synthesis and operational design"
rag_ready: true
preferred_chunking: "heading-aware, 500-800 words, preserve tables and code"
---

# Reference-Video Distillation and Reverse Directorial Compilation

## Abstract

A known video can be used as more than a visual reference. It can be treated as an observable execution trace of decisions about performance, blocking, action, timing, camera, editing, sound, visual effects, and audience communication. The challenge is not merely to summarize what appears on screen. It is to recover a reusable, identity-independent and implementation-aware control score that can be translated into the Cinematic Performance Control Score (CPCS) and then recompiled for a different cast, location, product, visual style, duration, or video-generation backend.

This guide defines **Reference-Video Distillation (RVD)** and **Reverse Directorial Compilation (RDC)**. RVD decomposes a source video into synchronized evidence streams. RDC interprets those streams as a hierarchy of shots, beats, performance controls, action and contact events, camera and editorial decisions, audio cues, visual-effects events, and marketing functions. The output is not assumed to be ground truth. Every extracted statement is typed as **measured**, **detected**, **inferred**, **interpreted**, or **authored**, and is accompanied by temporal extent, provenance, confidence, uncertainty, and contradiction records.

The central systems claim is that multimodal large models and conventional computer vision should not be treated as substitutes. Multimodal models such as Gemini and Twelve Labs Pegasus are useful for semantic hypotheses, narrative structure, shot purpose, action naming, social context, and schema-constrained descriptions. Frame-accurate extractors are required for presentation timestamps, shot boundaries, facial Action Unit estimates, gaze, body keypoints, optical flow, camera motion, speech alignment, contact candidates, and physical timing. A fusion layer resolves these observations into a canonical JSON intermediate representation. The resolved score can compile into text prompts, pose or depth control media, first/last frames, camera paths, mask tracks, audio timing, OpenTimelineIO editorial data, VFX events, evaluation constraints, and RAG records.

Two detailed workflows are developed. The first converts a fight scene into an action graph containing approach, step-in, pivot, attack, defense, near-contact or contact, recoil, fall, recovery, reaction, camera concealment, edit timing, and audiovisual impact. The second converts user-generated-content advertising into a communication graph containing hook, lens address, speech cadence, caption timing, demonstration, proof, product visibility, objection handling, brand reveal, and call to action. Both workflows emphasize that the portable “core” is a set of relationships and timing constraints, not an unauthorized replica of a performer’s identity, voice, exact likeness, or copyrighted audiovisual expression.

---

## 1. Research Question

The operational question is:

> Given a known video, how can a system recover the smallest sufficient set of time-indexed controls that explains its performance, action, cinematography, editing, sound, VFX, and persuasive structure well enough to direct a materially new AI-generated video?

This is an inverse problem. Normal CPCS compilation maps intention to an executed shot:

```text
screenplay / director note
        ↓
CPCS score
        ↓
model-specific controls
        ↓
video
```

Reverse Directorial Compilation estimates the latent score from the rendered result:

```text
reference video
        ↓
measurements + detections + semantic hypotheses
        ↓
resolved video-observation graph
        ↓
identity-independent CPCS score
        ↓
new production constraints
```

The inverse is underdetermined. A visible dolly-in might have been created by physical camera movement, a digital crop, a zoom lens, a stabilized handheld shot, or a generated camera transform. A recoil might result from staged contact, near-contact plus acting, an edit, sound design, camera shake, or a combination. A facial expression does not establish a private mental state. Therefore, a responsible reverse compiler reports possible explanations and confidence rather than claiming access to the original filmmakers’ intentions.

## 2. What “Extracting the Core” Means

The **core** is not a complete copy of the source. It is a compact, retargetable explanation of how the source works.

A useful core has seven properties:

1. **Temporal:** it describes changes, not only static labels.
2. **Relational:** it preserves actor-to-actor, actor-to-object, actor-to-camera, and sound-to-picture relationships.
3. **Identity-independent:** it can be retargeted to another performer or character.
4. **Coordinate-normalized:** it is not trapped in the source image resolution or one body size.
5. **Causally ordered:** it preserves anticipation, initiation, contact, reaction, follow-through, and recovery.
6. **Presentation-aware:** it separates what happened in the staged world from how the camera and edit made it visible.
7. **Evidence-aware:** it distinguishes observation from interpretation.

A practical extraction target is the following hierarchy:

| Level | Portable information | Examples |
|---|---|---|
| Production | global format and communication goal | 9:16 UGC ad; 16:9 action sequence; intended platform; duration |
| Sequence | dramatic and persuasive arc | hook → problem → proof → CTA; threat → exchange → reversal → aftermath |
| Scene | setting, participants, continuity state | kitchen demonstration; two fighters in corridor |
| Shot | camera and edit unit | close-up, 1.8 s, handheld, cut on head turn |
| Beat | meaningful state change | recognition, feint, product reveal, impact, decision to run |
| Action event | executable physical unit | step-in, pivot, reach, strike-like motion, dodge, recoil, fall, recovery |
| Performance track | face, gaze, affect, posture, Laban quality | AU04 onset; gaze to lens; bound Flow; sudden Time |
| Physical track | pose, root, phase, contact, momentum | left-foot plant; pelvis rotation; hand-target minimum distance |
| Presentation track | lens, camera, framing, speed, VFX | low angle; push-in; 60% time warp; dust burst; smear frame |
| Audio track | speech, breath, music, impact, silence | 165 words/min; pause before claim; transient at contact |
| Marketing track | attention and conversion hypothesis | product visible by 1.2 s; proof before brand; CTA hold |

The output should preserve enough information to reconstruct the intended relationships while permitting the new production to change appearance, cast, location, dialogue, product, genre, or style.

## 3. Evidence Classes: Do Not Flatten Everything Into “The Model Said”

Every observation in the extraction corpus should carry one of the following classes.

| Class | Definition | Examples |
|---|---|---|
| `measured` | Derived from media timing or numeric signal with a reproducible operation | PTS, duration, frame size, audio peak, optical-flow magnitude |
| `detected` | Output of a trained detector or classifier | shot boundary, face box, AU intensity estimate, body keypoint |
| `inferred` | Computed from multiple measurements under assumptions | camera pan, likely foot contact, near-contact, local phase |
| `interpreted` | Semantic or directorial reading that is not uniquely observable | intimidation, concealed fear, reaction shot purpose, hook function |
| `authored` | A deliberate production decision added during retargeting | replace product; make motion heavier; move reveal 0.3 s earlier |

A canonical observation should include:

```json
{
  "observation_id": "OBS-ACTION-0042",
  "path": "/shots/SHOT_003/action_events/EVT_07/type",
  "value": "step_in",
  "evidence_class": "inferred",
  "time_range": {"start_s": 4.233, "end_s": 4.617},
  "source_frame_range": {"start": 127, "end": 138},
  "extractor": {
    "name": "action-fusion",
    "version": "0.3.0",
    "inputs": ["pose_track_A", "root_track_A", "optical_flow_03"]
  },
  "confidence": 0.81,
  "uncertainty": {
    "start_s_sd": 0.033,
    "end_s_sd": 0.050
  },
  "alternatives": [
    {"value": "weight_shift_forward", "confidence": 0.31}
  ],
  "review_status": "unreviewed"
}
```

This design prevents a language model’s plausible description from silently overriding a frame-level measurement. It also lets RAG retrieve only human-reviewed observations, only high-confidence kinematics, or all competing interpretations.

## 4. Why One-Pass Multimodal Summarization Is Insufficient

Multimodal models can describe video, identify timestamps, and return structured output. Gemini’s official video-understanding documentation states that models can describe, segment, extract information, answer questions, and refer to timestamps. It also states that visual descriptions are sampled at one frame per second by default and warns that fast action and quick cuts may lose detail; the File API stores video at one FPS and adds timestamps every second [S67]. Vertex AI exposes an optional video FPS field with a default of 1.0 and a documented range above zero through 24 FPS, which makes higher-rate clipped analysis possible when supported by the selected endpoint and model [S69].

One FPS is useful for:

- scene and topic recognition;
- rough shot purpose;
- UGC structure;
- dialogue summary;
- product and location identification;
- broad camera scale;
- long-duration narrative beats.

One FPS is generally inadequate for:

- a four-frame eye tightening;
- exact onset and apex of an Action Unit;
- foot contact within a gait cycle;
- a 120–250 ms impact event;
- a whip pan or flash frame;
- cut-on-action timing;
- distinguishing near-contact from actual contact;
- a smear frame or one-frame VFX accent.

Twelve Labs Pegasus 1.5 supports general video analysis and structured, timestamped video segmentation. Its segmentation interface allows custom segment definitions and typed metadata fields [S71, S72]. This is valuable for discovering editorial narratives, action classes, speaker changes, camera-angle categories, brand appearances, and user-defined event types. It still should not be treated as a substitute for per-frame kinematics or an authoritative FACS coder.

The correct architecture is therefore **multi-pass and multi-resolution**.

## 5. Temporal Pyramid

A video-to-CPCS system should analyze the same source at several temporal scales.

| Pass | Typical sampling or unit | Main purpose |
|---|---:|---|
| Asset pass | container/stream level | codecs, timebase, duration, rotation, frame rate, audio layout |
| Sequence pass | 0.2–1 FPS or full long-context video | story, topic, persuasive arc, scene structure |
| Shot pass | every frame or shot detector | cuts, dissolves, fades, shot duration, transition type |
| Beat pass | 2–8 FPS plus audio | meaningful state changes, dialogue turns, reveals, reactions |
| Performance pass | 24–60 FPS | face, gaze, pose, gesture, gait, camera motion |
| Impact/micro pass | source FPS, optical flow, optional slow proxy | contact, fast action, microexpression, smear, flash, transient |
| Audio pass | 16–48 kHz | words, pauses, breaths, impacts, music beats, silence |

No single sampling rate should be inherited as the truth for every layer. The temporal resolution should be stored per observation.

## 6. End-to-End Architecture

```text
1. Rights and source registration
2. Media normalization and forensic manifest
3. Shot and transition detection
4. Long-context semantic analysis
5. Per-shot multimodal analysis
6. Frame-level face, gaze, pose, tracking, flow, and camera extraction
7. Audio transcription, diarization, rhythm, and event extraction
8. Action/contact/phase inference
9. Laban, affect, directorial, VFX, and marketing interpretation
10. Confidence and provenance fusion
11. Identity-independent normalization
12. Canonical Video Observation Graph
13. Reverse compilation into CPCS
14. Target-model compilation
15. Generated-video re-extraction and compliance scoring
```

Each stage should emit machine-readable records rather than hidden state. A failed stage should not erase the outputs of successful stages.

## 7. Stage 0 — Rights, Consent, and Source Registration

Before analysis, register:

- source URI or local asset identifier;
- cryptographic hash;
- rights basis and permitted use;
- whether identities, voices, logos, copyrighted characters, or private persons appear;
- whether the source can be used only for internal analysis, for retrieval, for training, or for generation;
- retention and deletion policy;
- territorial or campaign restrictions;
- whether human review is required before export.

The extraction target should normally be **abstract grammar**, not unauthorized cloning. “A 0.4-second anticipation followed by a direct step-in and camera-side dodge” is more portable than “recreate this actor exactly.” A UGC ad can preserve its hook density, speaking cadence, product visibility schedule, and proof structure while replacing identity, voice, wording, environment, and branding.

## 8. Stage 1 — Media Normalization and Forensic Manifest

Use `ffprobe` before any model call. FFprobe can report streams, format, frames, packets, chapters, and multiple machine-readable output formats, including JSON and XML [S75]. The manifest establishes the timebase that every later observation references.

Recommended command:

```bash
ffprobe -v error \
  -show_format \
  -show_streams \
  -show_chapters \
  -count_frames \
  -of json \
  reference.mp4 > source_probe.json
```

For frame timestamps:

```bash
ffprobe -v error \
  -select_streams v:0 \
  -show_frames \
  -show_entries frame=best_effort_timestamp_time,pkt_duration_time,key_frame,pict_type \
  -of json \
  reference.mp4 > frame_timestamps.json
```

Create analysis proxies without replacing the original:

```bash
# Constant-frame-rate analysis proxy
ffmpeg -i reference.mp4 \
  -vf "fps=24,scale='min(1280,iw)':-2" \
  -an -c:v libx264 -crf 18 -preset medium \
  analysis_24fps.mp4

# Mono speech-analysis stem
ffmpeg -i reference.mp4 \
  -vn -ac 1 -ar 16000 -c:a pcm_s16le \
  audio_16k_mono.wav

# Low-rate semantic frames
ffmpeg -i reference.mp4 \
  -vf "fps=1,scale=960:-2" \
  semantic_frames/frame_%06d.jpg
```

**Verification checkpoint:** the manifest must report a positive duration; a video stream must exist; extracted proxy duration must remain within a declared tolerance; and the source hash must match every downstream record.

## 9. Stage 2 — Shot, Transition, Scene, and Beat Segmentation

### 9.1 Shot boundaries

Cuts and transitions define the basic editorial units. A first detector can use histogram or content difference. PySceneDetect documents content-based, adaptive, and threshold-based detectors; adaptive detection is designed to reduce false positives during fast camera movement, while threshold detection is useful for fades [S76]. TransNet V2 is a learned shot-transition detector that addresses hard cuts and gradual transitions [S84].

Do not choose one detector blindly. Create boundary proposals from multiple methods, then fuse them:

```text
candidate cut =
  detector agreement
  + high frame difference
  + audio discontinuity
  + abrupt camera-model failure
  + multimodal semantic boundary
```

Store the boundary interval rather than only one frame when a dissolve or motion blur makes the exact cut ambiguous.

Managed video-labeling services can provide additional shot, object, text, speech, and explicit-content annotations, but their results should enter the same evidence graph as detector outputs rather than bypassing local validation. Google Cloud Video Intelligence is one example of an API organized around time-segmented video annotations [S77].

### 9.2 Scenes

A scene is a storytelling unit, not merely a continuous shot. MovieScenes frames scene segmentation as a multimodal and hierarchical problem over clips, segments, and the larger movie [S86]. MovieNet demonstrates the value of aligned character, scene-boundary, action, place, description, and cinematic-style annotations for movie understanding [S85].

Scene grouping should consider:

- location and time continuity;
- cast continuity;
- dialogue topic;
- music cue;
- color and lighting continuity;
- establishing-shot/reverse-shot relationships;
- narrative objective.

### 9.3 Beats

A beat is a state change that matters to the action, performance, or audience. Beat boundaries often occur inside a shot. Candidate signals include:

- gaze acquisition or break;
- speech turn or pause;
- object reveal;
- affect change;
- body initiation;
- contact or near-contact;
- camera move onset;
- sound transient;
- caption change;
- marketing-function transition.

Multimodal models are particularly useful for proposing beat names and purposes. The compiler should then snap broad model timestamps to measured events where possible.

## 10. Stage 3 — Multimodal Semantic Analysis

### 10.1 Gemini

Gemini can process uploaded video or public YouTube URLs, answer questions about timecoded content, and produce structured output [S67, S68]. Use it for a hierarchy of increasingly narrow questions rather than one request for “everything.”

Recommended pass sequence:

1. **Sequence map:** scenes, characters, objectives, persuasive or dramatic arc.
2. **Shot map:** shot purpose, scale, angle, movement, transition, visible action.
3. **Beat map:** state changes and causal ordering within each shot.
4. **Domain pass:** face/performance, action, camera/edit, audio, VFX, marketing.
5. **Contradiction pass:** ask the model to identify ambiguous or unsupported claims.

For rapid action, create short clips and, where appropriate, slowed analysis proxies. Do not alter the source timebase in the canonical record; store the proxy-to-source transform.

Gemini structured outputs improve parseability, but official guidance still requires application-level value validation and notes that only a subset of JSON Schema is supported [S68]. A syntactically valid object can still contain a semantically wrong timestamp or action label.

### 10.2 Twelve Labs Pegasus

Pegasus 1.5 supports general analysis, video clipping, multimodal prompts with reference images, and structured video segmentation [S71]. The segmentation interface permits up to ten segment definitions per request, up to twenty typed fields per definition, and timestamped JSON results [S72]. This makes it suitable for parallel semantic channels such as:

- editorial shots;
- action beats;
- speaker or dialogue turns;
- camera and framing categories;
- product or logo appearances;
- UGC marketing functions;
- VFX events;
- emotional-display changes.

Use specific definitions and finite enums. A field named `camera_angle` with an enum such as `eye_level`, `high`, `low`, `overhead`, and `uncertain` is more auditable than a free-form paragraph. Separate requests are preferable when a definition becomes overloaded.

Provider capability profiles must be date-stamped and pinned to an API or model version. Twelve Labs release notes show that analysis modes, timestamp formats, upload behavior, response limits, and endpoint contracts can change over time; a production extractor should therefore store the documentation date and adapter version with every observation batch [S74].

### 10.3 Twelve Labs Marengo and Gemini Embeddings

Marengo 3.0 is an embedding/search model rather than a per-frame metrology system. Its documented capabilities include multimodal processing, motion search, and improved understanding of cinematography terms such as zoom, pan, and tracking shot [S73]. Use it to retrieve comparable moments and cluster a library by motion or cinematic grammar.

Gemini Embedding 2 maps video and other modalities into a shared embedding space. Official limits state that video embeddings process at most 32 frames, with one-FPS sampling for clips up to 32 seconds and uniform 32-frame sampling for longer clips; audio inside video files is not processed [S70]. It is useful for retrieval and similarity, not for precise action timing.

## 11. Stage 4 — Actor, Face, Gaze, and Performance Extraction

### 11.1 Persistent actor tracks

Every detected person needs a persistent track ID. The system should preserve uncertainty through occlusion, shot changes, masks, and re-entry. Actor tracking is not the same as identity recognition. A privacy-preserving workflow can use ephemeral track IDs without resolving real-world identity.

Track records should contain:

- bounding box or mask;
- visibility and occlusion;
- face visibility;
- body keypoint confidence;
- identity-link confidence across cuts;
- speaking probability;
- interaction partners.

### 11.2 FACS and face-related tracks

OpenFace provides facial landmarks, head pose, a subset of Action Unit presence/intensity estimates, and gaze. Its documentation notes that dynamic video models can perform person-specific calibration and that multi-person AU extraction is less reliable because re-identification and person-specific calibration are limited [S78].

An extraction pipeline should therefore:

1. crop and stabilize each face track;
2. estimate landmarks, head pose, gaze, and AUs per frame;
3. preserve detector confidence and face size;
4. reject or down-weight severe profile, blur, occlusion, and tiny faces;
5. calibrate a neutral baseline per performer and shot family;
6. smooth only after preserving onset and apex events;
7. convert raw estimates into temporal AU events with onset, apex, offset, amplitude, and asymmetry;
8. retain raw and processed tracks separately.

Do not infer emotion directly from an AU combination. CPCS should store observed facial activity and a separate interpreted affect track.

### 11.3 Gaze and attention

Head pose is not gaze. Eye direction, head orientation, and likely target should be separate. VideoAttentionTarget formalizes dynamic gaze-target inference and explicitly includes out-of-frame targets [S91]. For cinematic analysis, likely targets include:

- camera lens;
- another actor’s face;
- a product or prop;
- an off-screen threat;
- captions or monitor content;
- an undefined scan region.

A UGC video’s lens-address schedule is a major directorial and marketing control. A fight scene’s gaze may anticipate an attack, confirm target acquisition, or conceal intent.

### 11.4 Affect

Estimate experienced affect only as a production interpretation. Visible display can be summarized as a VAD/VAC trajectory conditioned on face, voice, posture, and context, but it remains uncertain. Keep separate fields for:

- `displayed_affect_estimate`;
- `narrative_affect_interpretation`;
- `confidence`;
- `cultural_and_context_notes`.

## 12. Stage 5 — Body Pose, 3D Reconstruction, and Camera Disentanglement

### 12.1 Whole-body pose

AlphaPose provides whole-body multi-person pose estimation and tracking, including body, face, hands, and feet [S79]. 2D keypoints are useful for screen-space choreography, silhouette, gesture, and contact candidates. They do not uniquely determine depth or world-space motion.

For each joint, store:

```json
{
  "t": 3.2667,
  "joint": "right_wrist",
  "xy_norm": [0.714, 0.432],
  "confidence": 0.94,
  "occluded": false,
  "source": "alphapose@version"
}
```

### 12.2 Monocular 3D human reconstruction

4DHumans reconstructs and tracks people in 3D from in-the-wild video and maintains identities through occlusion using 3D tracking [S80]. Such models can create retargetable skeletal or mesh tracks, but monocular scale, depth, camera motion, floor contact, and interaction geometry remain ambiguous.

### 12.3 Joint human-camera-scene reconstruction

SynCHMR addresses the problem that camera reconstruction and human reconstruction are often solved in incompatible frames. It combines human-aware metric SLAM and scene-aware human reconstruction to recover cameras, humans, and scene structure in a common world frame [S81]. This class of method is valuable because apparent screen movement is a mixture of:

Multiview first-/third-person resources such as Ego-Exo4D are valuable for developing and evaluating cross-view activity understanding, camera/body disentanglement, and skilled-action analysis. They do not remove the need to label which conclusions came from a single monocular production source and which were learned or validated from additional views [S90].


a. performer movement;

b. camera translation and rotation;

c. focal-length or crop change;

d. moving background or parallax;

e. stabilization and rolling-shutter artifacts.

### 12.4 Optical flow and background motion

RAFT estimates dense optical flow through recurrent all-pairs field transforms [S82]. Flow can support:

- motion saliency;
- camera-motion estimation from background pixels;
- action onset detection;
- speed-ramp analysis;
- VFX trail and smear detection;
- motion-blur assessment.

Flow alone does not identify cause. Mask performers and moving objects before fitting a global background transform. Compare homography, affine, and 3D camera explanations. Report model residuals.

### 12.5 Structure from motion

COLMAP is a general-purpose Structure-from-Motion and Multi-View Stereo pipeline that recovers camera poses and sparse or dense scene structure from overlapping images [S83]. It is most useful when the shot contains sufficient static texture, parallax, and non-destructive cuts. It may fail on heavy motion blur, shallow depth of field, large dynamic regions, stylized footage, or short shots.

## 13. Coordinate and Time Normalization

### 13.1 Time

Preserve original presentation timestamps. For a constant-rate derivative:

\[
t_f = \frac{f}{r}
\]

where \(f\) is the analysis-frame index and \(r\) is the proxy frame rate. Store a transform back to source PTS. For retargeting, normalize event time within a beat:

\[
\tau = \frac{t - t_{beat,start}}{t_{beat,end}-t_{beat,start}} \in [0,1]
\]

This permits the same action structure to be retimed from 1.2 seconds to 0.9 seconds while preserving relative order.

### 13.2 Space

Screen coordinates should be normalized by frame dimensions. Body coordinates should also be expressed relative to a root and body scale:

\[
\hat{p}_{j,t} = \frac{p_{j,t} - p_{root,t}}{h_t}
\]

where \(h_t\) is estimated body height or another stable scale. Interaction distances can be normalized by mean shoulder width or character height.

### 13.3 Camera-relative and world-relative representations

Store both when available:

- screen-space trajectory for what the audience sees;
- actor-relative camera pose for framing grammar;
- world-space performer trajectory for blocking and physics;
- uncertainty if world reconstruction is unavailable.

A director often cares that “the fist crosses the right third of frame and nearly reaches the opponent’s jaw at 62% of the beat,” even when absolute world coordinates cannot be recovered.

## 14. Stage 6 — Action Atoms, Motion Phases, Contacts, and Combat

### 14.1 Action segmentation

ASFormer addresses frame-level action segmentation over long activity sequences [S87]. ActionFormer localizes temporal action intervals and their categories [S88]. These models motivate a separation between:

- dense frame labels;
- event boundaries;
- action identity;
- action phase;
- participant and target roles.

The CPCS extraction taxonomy should remain production-oriented. For a fight or stunt sequence, useful atoms include:

```text
approach
retreat
step_in
plant
pivot
load
feint
strike_like_motion
reach
grab
redirect
block_like_defense
dodge
duck
parry_like_contact
near_contact
contact
recoil
stagger
fall
roll
rise
recover_guard
hold
```

These labels describe visual choreography; they are not instructions for causing real-world injury.

### 14.2 Phases

Every nontrivial action should have phases:

```text
preparation → initiation → acceleration → apex/contact → follow-through → recovery
```

The phase boundaries can be estimated from joint velocity, acceleration, support changes, target distance, and semantic hypotheses. Store local phases for feet, pelvis, torso, hand, head, and reaction partner when they are not synchronized.

### 14.3 Contact and near-contact

In staged action, apparent impact may be produced without physical contact. Represent:

- `physical_contact_confirmed` only when evidence supports it;
- `near_contact` when minimum distance is small but nonzero;
- `occluded_contact` when the camera hides the decisive geometry;
- `editorial_impact` when cut, sound, shake, or VFX supplies the event;
- `unknown` when depth ambiguity prevents a conclusion.

A candidate hand-target distance is:

\[
d_{ij}(t)=\|p_i(t)-p_j(t)\|
\]

but monocular depth uncertainty must be included. Contact confidence should combine geometric distance, relative velocity, occlusion, sound transient, partner reaction, and frame visibility.

### 14.4 Causal action graph

```json
{
  "event_id": "EVT_12",
  "type": "strike_like_motion",
  "actor": "ACTOR_A",
  "target": "ACTOR_B:head_region",
  "start_s": 5.167,
  "apex_s": 5.433,
  "end_s": 5.800,
  "phases": [
    {"name": "load", "start_s": 5.167, "end_s": 5.267},
    {"name": "accelerate", "start_s": 5.267, "end_s": 5.433},
    {"name": "follow_through", "start_s": 5.433, "end_s": 5.617},
    {"name": "recovery", "start_s": 5.617, "end_s": 5.800}
  ],
  "contact": {
    "classification": "occluded_near_contact",
    "time_s": 5.433,
    "confidence": 0.67
  },
  "causes": ["EVT_10:step_in", "EVT_11:pelvis_pivot"],
  "effects": ["EVT_13:reaction_recoil", "EDIT_07:cut", "AUDIO_19:impact_transient"]
}
```

The causal graph is more transferable than raw pixels because it preserves the order and coupling of actions.

## 15. Stage 7 — Deriving Laban Movement Qualities

Laban Effort is not directly observable as one number, and computational proxies are not definitions. The reverse compiler should produce a **candidate Laban reading** with evidence.

### 15.1 Weight

Possible proxies:

- acceleration and deceleration magnitude;
- vertical center-of-mass displacement;
- contact loading duration;
- visible follow-through;
- muscle-tension appearance where available;
- sound and camera emphasis, stored separately from body mechanics.

A strong-Weight interpretation should not be inferred solely from loud audio.

### 15.2 Time

Possible proxies:

- time from preparation to apex;
- acceleration concentration;
- abruptness of direction change;
- duration of holds and releases;
- action-onset uncertainty.

Sudden Time is a qualitative intention and may coexist with smooth trajectories.

### 15.3 Space

A directness ratio can support a candidate reading:

\[
D = \frac{\|p(t_1)-p(t_0)\|}{\sum_t \|p(t+\Delta t)-p(t)\|}
\]

Values closer to one indicate a straighter path, but direct Space also concerns attention and spatial intent, not only geometry.

### 15.4 Flow

Possible proxies:

- jerk and its distribution;
- residual motion after the action goal;
- frequency of controlled holds;
- reversibility and stopping behavior;
- joint coupling and release.

Bound Flow should not be reduced to “low speed.”

### 15.5 Shape and Body organization

Estimate spreading/enclosing, rising/sinking, advancing/retreating, and body-part initiation from normalized skeletal geometry. Store the measured geometry and the interpreted Laban label separately.

## 16. Stage 8 — Camera, Lens, Framing, and Editorial Grammar

### 16.1 Shot scale and framing

Measure subject occupancy and headroom rather than relying only on labels. Store:

- person-box height as fraction of frame;
- face size;
- headroom and lead room;
- center-of-interest;
- number of visible bodies;
- occlusion and silhouette separation;
- approximate shot-scale label with confidence.

### 16.2 Angle

Camera height and pitch relative to the performer determine high, low, eye-level, overhead, or ground-level readings. When 3D recovery is unavailable, label the visual impression and mark the geometric basis as uncertain.

### 16.3 Camera movement

Classify:

- static/locked;
- handheld perturbation;
- pan/tilt/roll;
- dolly/truck/pedestal;
- orbit;
- push-in/pull-out;
- zoom or crop;
- rack focus;
- whip pan;
- stabilization correction.

Separate designed base path from high-frequency shake. A useful model is:

\[
C(t) = C_{base}(t) \oplus C_{operator}(t) \oplus C_{post}(t)
\]

where the components represent intended path, operator-like perturbation, and postproduction stabilization or crop.

### 16.4 Editing

OpenTimelineIO is an interchange format and API for editorial cut information, including clips, timing, tracks, transitions, markers, and metadata while referencing media externally [S92]. Exporting shot and beat boundaries to OTIO allows the extracted structure to enter a conventional editing pipeline.

Extract:

- cut type and time;
- shot duration;
- J/L cut or audio overlap;
- reaction cut;
- cut on action;
- match on movement;
- insert or product cutaway;
- speed ramp;
- freeze or impact frame;
- montage density;
- continuity of screen direction and eyeline.

A cut is not merely a boundary; it can be a control event whose timing is coupled to gaze, action apex, line delivery, sound, or marketing reveal.

## 17. Stage 9 — Audio, Dialogue, Rhythm, and Impact

Whisper is a general-purpose speech-recognition model supporting multilingual transcription, translation, and language identification [S89]. Use an ASR system to generate word- or segment-timed transcripts, but verify brand names, names, numbers, and rapid speech manually.

Extract:

- speaker turns and overlap;
- word timing and words per minute;
- pauses, fillers, and breath points;
- sentence stress and pitch-energy envelope;
- music tempo and beat grid;
- silence intervals;
- impact transients;
- whooshes, risers, and stingers;
- room tone and ambience;
- audio lead/lag relative to cuts.

For action, estimate whether the perceived force comes from body mechanics, sound, camera, edit, VFX, or all of them. For UGC, speech rhythm, pause placement, caption changes, and lens address often define the pace more strongly than body locomotion.

## 18. Stage 10 — VFX and Stylization Extraction

VFX/anime events should be represented as timed presentation layers, not confused with physical motion.

Examples:

| Event | Evidence | CPCS target |
|---|---|---|
| speed lines | directional high-frequency graphics around movement | VFX line field, direction, start/end, mask |
| energy trail | persistent luminous path following limb/prop | tracked emitter, trail lifetime, width, color family |
| dust burst | localized particle event at footfall or impact | contact-linked particle emitter |
| camera shake | global image transform after impact | post camera impulse track |
| smear frame | one/few highly distorted frames | editorial/VFX frame event |
| impact flash | luminance or color pulse at apex | compositing event linked to contact |
| freeze/hold | repeated or time-warped frame | time-remap event |
| speed ramp | local source-to-output time mapping | retime curve |

The physical event and the effect should be separately addressable. A new generation can retain the action but remove the effect, or retain the effect grammar while changing the action.

## 19. Stage 11 — UGC and Marketing Extraction

Marketing controls describe why a creative is expected to communicate, not a guaranteed sales outcome. The extraction should produce testable hypotheses.

### 19.1 UGC communication graph

Common nodes include:

```text
pattern_interrupt / visual_hook
spoken_hook
problem statement
identity or credibility cue
product reveal
demonstration
mechanism explanation
proof or result
objection handling
offer
call to action
brand or legal hold
```

### 19.2 Measurable UGC tracks

- time to first face;
- time to first spoken proposition;
- time to product visibility;
- product visibility ratio by second;
- gaze-to-lens duty cycle;
- shot-duration distribution;
- camera shake and autofocus behavior;
- speaking rate and pause pattern;
- caption words per card and update frequency;
- b-roll frequency;
- proof-object close-up duration;
- brand visibility and CTA hold;
- first-three-second information density;
- audio/music onset;
- safe-area compliance for captions and platform crops.

### 19.3 Director and marketing separation

A low-angle close-up is a director control. “Establish authority before introducing the product” is a marketing hypothesis. The compiler can connect them, but they should not share one field.

## 20. Confidence Fusion and Contradiction Management

### 20.1 Do not average unlike evidence

A language model’s `0.82` confidence is not calibrated against a pose detector’s keypoint probability. Preserve confidence type and calibration scope.

### 20.2 Evidence bundle

Each resolved field should cite supporting observations:

```json
{
  "resolved_claim_id": "CLAIM-0031",
  "path": "/shots/SHOT_004/camera/move",
  "value": "push_in",
  "status": "accepted",
  "confidence": 0.86,
  "support": ["OBS-FLOW-91", "OBS-SFM-12", "OBS-PEGASUS-44"],
  "contradictions": ["OBS-FOCAL-07"],
  "resolution_rule": "background-parallax evidence outranks semantic label",
  "reviewer": null
}
```

### 20.3 Suggested precedence

For a geometric or temporal fact:

```text
source timestamps
> calibrated geometry/track
> uncalibrated detector
> multimodal semantic inference
> free-form description
```

For a narrative or marketing interpretation:

```text
human-approved interpretation
> multiple independent multimodal analyses
> single semantic analysis
> geometry-only guess
```

### 20.4 Contradiction is a first-class output

Examples:

- semantic model labels a zoom; background parallax supports dolly;
- AU detector reports high AU12 but face is blurred;
- pose indicates possible contact but depth estimate indicates a miss;
- transcript says product name while OCR reads a different brand;
- model labels a cut but transition detector identifies a dissolve.

Do not silently resolve these. Record them for review or downstream sensitivity analysis.

## 21. Canonical Video Observation Graph

The canonical JSON should contain:

```text
source
rights
media_manifest
timebase
scenes
shots
beats
actors
face_tracks
gaze_tracks
pose_tracks
mesh_tracks
action_events
contact_events
camera_tracks
edit_events
audio_tracks
vfx_events
marketing_beats
observations
resolved_claims
normalization
cpcs_projection
validation
```

YAML is appropriate for human-authored extraction plans and overrides. JSON is the canonical resolved interchange. JSONL is appropriate for RAG and observation/event records. XML can wrap the resulting score in a screenplay or director envelope, but should not become the only repository for dense numerical tracks.

## 22. Reverse Compilation Into CPCS

The reverse compiler maps observations into control layers.

| Extracted evidence | CPCS field | Generation target |
|---|---|---|
| AU time series | face Action Unit events | face rig, facial landmarks, expression reference, text fallback |
| gaze/head tracks | attention and head-pose tracks | eye/head controls, actor-facing constraints |
| pose/mesh | skeletal and root tracks | pose video, keypoints, rig animation, motion latent |
| action graph | motion atoms and phases | motion retrieval/generation, choreography graph |
| contact candidates | contact constraints | IK, physics, target trajectories, evaluation |
| Laban reading | movement-quality track | style conditioning, retiming, motion retrieval |
| camera estimate | camera/lens/framing track | 6DoF path, first/last frames, prompt, post crop |
| cut/transition map | editorial track | OTIO/EDL, clip generation schedule |
| VFX events | effect track | masks, particles, compositor, prompt or post |
| audio events | audio synchronization | dialogue, transient, music, captions |
| marketing graph | communication constraints | shot ordering, visibility, CTA and variant plan |

### 22.1 What can be compiled directly

Depending on backend capability:

- text prompt with explicit temporal clauses;
- structured API request;
- reference image or video;
- first and last frames;
- pose, depth, segmentation, edge, and optical-flow videos;
- actor or object masks;
- camera trajectory;
- 3D animation and rendered control passes;
- audio reference or timing plan;
- separate clips per shot plus editorial assembly;
- VFX and caption overlays;
- evaluator constraints.

### 22.2 Controlled degradation

If a model cannot accept an AU curve, the compiler may:

1. bake facial motion into an identity-safe rendered reference;
2. convert it into facial landmarks;
3. compress it into timed language;
4. retain it only as an evaluator;
5. report unsupported control rather than pretending it was enforced.

## 23. Detailed Workflow: Fight or Stunt Scene

### 23.1 Pass A — Editorial anatomy

Extract every shot, transition, speed change, freeze, reaction insert, and impact frame. Create an OTIO timeline. Measure average shot length and the distribution around action apexes.

### 23.2 Pass B — Actor and geography

Track each performer, infer screen direction, estimate world or actor-relative positions, identify obstacles and props, and record visibility. Maintain separate tracks through cuts.

### 23.3 Pass C — Action atomization

For each exchange, label:

```text
setup
approach
weight shift
step-in
plant
pivot/load
attack-like motion
defense/dodge/redirect
near-contact/contact/occluded impact
reaction
follow-through
recovery
new guard or fall
```

### 23.4 Pass D — Kinetic chain

Estimate temporal ordering:

```text
support foot → pelvis → torso → shoulder → elbow → hand/prop
```

Do not infer biomechanical force from image speed alone. Camera movement, shutter, and retiming can change apparent speed.

### 23.5 Pass E — Impact construction

For every impact-like beat, decompose:

```text
body geometry
+ camera framing
+ edit timing
+ sound transient
+ camera impulse
+ VFX accent
+ reaction amplitude
```

This exposes why a beat reads as forceful. The retargeted version can change one component without indiscriminately increasing violence.

### 23.6 Pass F — Safety and abstraction

Export stylized, fictional choreography for previsualization. Do not present it as real-world fighting instruction. Preserve staged near-contact classifications and require stunt-professional review for physical production.

### 23.7 Example fight extraction summary

```yaml
sequence_id: FIGHT_SEQ_01
portable_core:
  dramatic_arc:
    - probe
    - first_commitment
    - reversal
    - controlled_finish
  rhythm:
    exchange_count: 3
    rest_intervals_s: [0.42, 0.71]
  action_events:
    - id: EVT_01
      type: step_in
      actor: A
      phase_range: [0.00, 0.18]
    - id: EVT_02
      type: pivot_load
      actor: A
      phase_range: [0.12, 0.31]
    - id: EVT_03
      type: strike_like_motion
      actor: A
      target: B.head_region
      phase_range: [0.27, 0.56]
    - id: EVT_04
      type: dodge
      actor: B
      phase_range: [0.39, 0.61]
    - id: EVT_05
      type: occluded_near_contact
      phase: 0.55
    - id: EVT_06
      type: reaction_recoil
      actor: B
      phase_range: [0.56, 0.79]
  laban_candidate:
    A: {weight: strong, time: sudden, space: direct, flow: bound_to_free}
    B: {weight: light, time: sudden, space: indirect, flow: free}
  camera:
    shot_scale: medium_wide
    base_move: lateral_track
    impact_impulse: {amplitude: 0.18, duration_s: 0.12}
  edit:
    cut_relative_to_apex_s: 0.04
  audio:
    impact_transient_relative_to_apex_s: 0.00
  exclusions:
    - performer_identity
    - exact wardrobe
    - exact dialogue
    - source_location
```

## 24. Detailed Workflow: UGC Advertisement or Creator Video

### 24.1 Pass A — Communication structure

Ask a multimodal model to identify the proposition and segment the creative into hook, problem, solution, demonstration, proof, objection, offer, and CTA. Use a finite schema and require timestamps.

### 24.2 Pass B — Lens relationship

Measure when the creator looks at the lens, glances at the product, looks at captions, or turns to b-roll. Store gaze-to-lens duty cycle by beat.

### 24.3 Pass C — Speech and caption pace

Transcribe words with timestamps. Estimate:

- words per minute;
- pause duration distribution;
- time to first claim;
- sentence length;
- emphasis points;
- caption update rate;
- alignment between spoken phrase and caption card;
- music-to-speech balance.

### 24.4 Pass D — Visual proof

Track product and proof objects. Measure visibility, size, angle, obstruction, and duration. Distinguish a brand appearance from a persuasive proof event.

### 24.5 Pass E — Camera authenticity grammar

Extract:

- phone-like vertical framing;
- arm-length perspective;
- handheld spectrum;
- autofocus or exposure corrections;
- jump-cut pattern;
- b-roll insert density;
- imperfect but bounded composition.

These features can be intentionally reproduced without duplicating the original person.

### 24.6 Pass F — Variant plan

Compile the extracted core into controlled variants:

```text
same hook timing, new wording
same proof order, different product
same gaze rhythm, different creator
same shot-duration distribution, different location
same CTA hold, different offer
```

### 24.7 Example UGC extraction summary

```yaml
sequence_id: UGC_15S_01
format: {aspect_ratio: "9:16", duration_s: 15.0}
marketing_graph:
  - {id: M1, type: spoken_hook, start_s: 0.00, end_s: 1.35}
  - {id: M2, type: problem, start_s: 1.35, end_s: 3.10}
  - {id: M3, type: product_reveal, start_s: 2.20, end_s: 3.60}
  - {id: M4, type: demonstration, start_s: 3.60, end_s: 8.90}
  - {id: M5, type: proof, start_s: 8.90, end_s: 12.10}
  - {id: M6, type: call_to_action, start_s: 12.10, end_s: 15.00}
performance:
  gaze_to_lens_ratio: 0.72
  speech_rate_wpm: 171
  pause_before_proof_s: 0.28
  laban_candidate:
    weight: light
    time: sudden
    space: direct
    flow: free_with_brief_holds
camera:
  style: handheld_phone
  mean_face_height_fraction: 0.31
  jump_cut_count: 5
captions:
  update_rate_per_s: 1.15
  mean_words_per_card: 4.2
product:
  first_visible_s: 2.24
  total_visibility_ratio: 0.48
  hero_hold_s: 1.10
retargeting_locks:
  - hook_end_s
  - proof_precedes_cta
  - product_first_visible_s_max_3_0
retargeting_variables:
  - creator_identity
  - script_wording
  - product
  - environment
  - color_grade
```

## 25. Provider-Orchestrated Extraction Pattern

A robust system can assign roles as follows:

```text
Gemini / Pegasus
  → semantic hierarchy, custom events, narrative, UGC function,
    broad camera labels, action naming, ambiguity proposals

Marengo / multimodal embeddings
  → retrieval, clustering, similarity search, comparable-shot discovery

FFprobe / FFmpeg
  → authoritative media metadata, PTS, proxies, audio stems, frames

Shot detectors
  → frame-accurate cut and transition proposals

Face / gaze tools
  → landmarks, head pose, AUs, gaze candidates

Pose / mesh / tracking
  → skeleton, root, body parts, identities, normalized motion

Optical flow / SfM / SLAM
  → dense motion, background camera model, camera/actor separation

ASR and audio analysis
  → words, turns, rhythm, pauses, impact and music events

Fusion compiler
  → evidence graph, CPCS projection, capability-aware target package
```

No provider should be the sole source of truth for all layers.

## 26. Round-Trip Verification

The final test is not whether the new video “feels similar” in an unconstrained way. Re-extract the generated result and compare it with the intended CPCS score.

### 26.1 Temporal event error

\[
E_{event}=|t_{generated}-t_{target}|
\]

Use for cuts, gaze changes, product reveal, contact, reaction, and CTA.

### 26.2 Pose or trajectory agreement

Use normalized joint or root trajectories with dynamic time warping when elastic timing is allowed.

### 26.3 Action graph agreement

Compare event types, order, actor roles, targets, and causal edges.

### 26.4 Camera agreement

Compare shot scale, framing occupancy, screen direction, base camera move, and impact impulse separately.

### 26.5 Marketing agreement

Check constraints such as:

- hook completes by target time;
- product visible within threshold;
- proof precedes CTA;
- caption safe areas preserved;
- CTA hold meets minimum duration.

### 26.6 Perceptual review

Human reviewers should separately score:

- action identity;
- performance intent;
- motion naturalness;
- physical readability;
- cinematic clarity;
- originality and non-duplication;
- marketing comprehension;
- rights and policy compliance.

## 27. Failure Modes

| Failure | Cause | Mitigation |
|---|---|---|
| missed fast action | low sampling rate | clip and resample; frame-level pose/flow; slow proxy |
| false shot boundary | flash, shake, VFX | multi-detector fusion; transition interval; semantic continuity |
| wrong actor identity | occlusion or cut | track confidence; cross-shot review; no forced identity resolution |
| pose jitter | detector instability | confidence-aware smoothing; 3D prior; preserve raw track |
| foot skating inferred from camera | camera/actor conflation | background motion model; world reconstruction |
| false contact | monocular depth ambiguity | near-contact class; multi-cue fusion; human review |
| Laban overclaim | metric treated as definition | label as candidate interpretation; retain evidence |
| AU overclaim | blur/profile/calibration | face-quality gating; per-person calibration; uncertainty |
| semantic hallucination | one-pass MLLM output | structured schema, evidence timestamps, contradiction pass |
| UGC “style clone” | identity and surface copied | extract timing/communication grammar; replace protected elements |
| video model ignores score | unsupported controls | capability negotiation; control passes; evaluator; report loss |
| RAG retrieves speculation as fact | evidence classes flattened | metadata filters; reviewed status; source and confidence fields |

## 28. Minimum Viable Implementation

A first production implementation can be built in four tiers.

### Tier 1 — Semantic reverse storyboard

- ffprobe manifest;
- shot detection;
- transcript;
- Gemini or Pegasus shot/beat descriptions;
- canonical JSON;
- human review.

### Tier 2 — Performance-aware extraction

Add:

- actor tracking;
- face/head/gaze;
- 2D whole-body pose;
- action events;
- camera and edit tracks;
- UGC/marketing graph.

### Tier 3 — Motion and interaction reconstruction

Add:

- monocular 3D human reconstruction;
- camera/scene reconstruction;
- local phases;
- contact inference;
- Laban operationalization;
- pose/depth/mask control exports.

### Tier 4 — Closed-loop generation

Add:

- target-model adapter;
- clip-level generation;
- editorial assembly;
- re-extraction;
- automatic compliance report;
- patch-based revision.

### 28.1 Two operational CLI paths

The package exposes two compatible representations rather than forcing one file shape onto every production.

The **comprehensive extraction-record path** is useful when one project record should contain source rights, timebase, pipeline tools, tracks, observations, transfer policy, and validation together:

```bash
python scripts/video_to_cpcs_reference_pipeline.py probe \
  --video reference.mp4 \
  --output work/reference_001/probe.json

python scripts/video_to_cpcs_reference_pipeline.py prepare \
  --video reference.mp4 \
  --workdir work/reference_001/derivatives

python scripts/video_to_cpcs_reference_pipeline.py init-record \
  --video reference.mp4 \
  --probe work/reference_001/probe.json \
  --output work/reference_001/extraction_record.json

python scripts/video_to_cpcs_reference_pipeline.py validate \
  --record work/reference_001/extraction_record.json
```

The **observation-graph path** is useful for distributed extraction, provider fusion, and RAG. It creates a media manifest, collects independently serializable observation records, merges them into a VOG, and validates that graph:

```bash
python scripts/extract_video_manifest.py reference.mp4 \
  --output-dir work/reference_001

python scripts/merge_video_observations.py \
  --manifest work/reference_001/source_manifest.json \
  --inputs work/reference_001/observations/*.jsonl \
  --output work/reference_001/video_observation_graph.json \
  --conflicts work/reference_001/conflicts.json

python scripts/validate_video_observation_graph.py \
  work/reference_001/video_observation_graph.json \
  --schema schemas/CPCS_Video_Observation_Graph_Schema.json \
  --record-schema schemas/CPCS_Video_Observation_Record_Schema.json
```

The comprehensive record and the VOG can coexist. The former is convenient as a project dossier; the latter is better for append-only evidence, disagreement, retrieval, and independent reprocessing.

## 29. Deterministic Verification Checklist

Before accepting an extraction:

```text
[ ] source SHA-256 recorded
[ ] source duration and streams validated
[ ] source and proxy timebases mapped
[ ] shot boundaries reviewed or confidence-scored
[ ] every semantic claim has a time range
[ ] every numeric track has units and coordinate system
[ ] actor IDs retain uncertainty through occlusion
[ ] face/AU observations are quality-gated
[ ] camera motion is separated from subject motion where possible
[ ] contact labels distinguish confirmed, near, occluded, and unknown
[ ] Laban and affect fields are explicitly interpretive
[ ] audio transcript and picture share a clock
[ ] marketing claims are hypotheses, not guaranteed outcomes
[ ] every resolved claim cites evidence records
[ ] contradictions are retained
[ ] CPCS projection passes schema validation
[ ] unsupported target controls are reported
[ ] generated result is re-extracted and compared
[ ] rights and consent scope permits the intended use
```

## 30. Conclusion

Reference-video analysis becomes useful for AI video direction when it moves beyond captioning. A source video should be treated as a layered execution trace. Its reusable core consists of synchronized relationships: what changes, when it changes, who causes it, who or what it targets, how the body realizes it, how the camera and edit reveal it, how audio and VFX amplify it, and what the audience is expected to understand.

Multimodal models provide semantic reach; deterministic media tools and computer-vision models provide temporal and geometric evidence; human review supplies accountable interpretation. CPCS provides the integration layer. The resulting Video Observation Graph can be reverse-compiled into an identity-independent performance and production score, then recompiled into prompts, control media, camera and edit plans, VFX events, audio timing, and compliance tests for an AI video generator.

The primary engineering principle is simple: **do not ask one model to “understand the whole video” and accept a paragraph. Build an evidence graph, preserve uncertainty, and compile the video’s structure into editable controls.**
