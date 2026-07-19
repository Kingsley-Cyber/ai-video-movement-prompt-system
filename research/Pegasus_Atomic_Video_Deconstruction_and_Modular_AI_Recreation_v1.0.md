---
title: "Pegasus-Centered Atomic Video Deconstruction and Modular AI Recreation"
subtitle: "A Standalone Workflow for High-Fidelity UGC Transfer, Fight-Scene Reconstruction, CPCS Compilation, and Evidence-Preserving Data Exchange"
document_id: "CPCS-PEGASUS-RDC-2026-01"
version: "1.0"
date: "2026-07-18"
status: "Research synthesis and implementation blueprint"
rag_ready: true
preferred_chunking: "heading-aware; 450-850 words; preserve tables, schemas, and code blocks"
primary_system: "Twelve Labs Pegasus 1.5"
related_framework: "Cinematic Performance Control Score (CPCS)"
license_note: "Use only with source material for which analysis and transformation are authorized."
---

# Pegasus-Centered Atomic Video Deconstruction and Modular AI Recreation

## Abstract

A reference video can be treated as a rendered trace of many hidden production decisions: script intent, acting, facial expression, body mechanics, choreography, camera placement, editing, sound design, visual effects, and persuasive structure. Recreating that video with different characters requires more than a detailed caption. It requires **atomic deconstruction**: separating the source into synchronized, evidence-backed modules that can be transferred, replaced, retimed, recombined, and compiled for a new text-to-video, image-to-video, pose-conditioned, or video-to-video generation workflow.

This document defines a Pegasus-centered reverse-engineering architecture for that task. Twelve Labs Pegasus 1.5 serves as the **semantic video analyst and reverse-director**. It identifies scenes, passages, visible actions, narrative functions, camera grammar, dialogue function, UGC persuasion structure, performance interpretation, anime effects, and timestamped segment hypotheses. Pegasus is not treated as a frame-accurate motion-capture engine. High-fidelity reconstruction therefore combines Pegasus with a parallel measurement lane containing source timestamps, shot boundaries, actor masks, pose tracks, optical flow, facial tracking, audio events, camera-motion estimates, and manually reviewed contact frames.

The outputs are fused into an evidence-preserving Video Observation Graph and compiled into the Cinematic Performance Control Score (CPCS). Four structured representations have distinct responsibilities. **JSONL** stores atomic observations, provenance, model outputs, corrections, and validation events. **JSON** stores the canonical resolved score. **YAML** provides human-readable direction, inheritance, replacement policies, and overrides. **XML** provides a strongly delimited semantic envelope for directing an LLM compiler. Dense pose, masks, depth, camera, and flow signals remain in media or numerical assets rather than being forced into prose.

Two complete operating profiles are developed. The first transfers a realistic user-generated-content video to a new performer, product, voice, setting, and brand while preserving pace, gaze behavior, hook timing, demonstration order, product visibility, caption rhythm, proof sequence, and camera authenticity. The second reconstructs a stylized fight scene while preserving action causality, body-part timing, screen-space trajectories, contact or near-contact timing, reaction latency, camera concealment, editorial impact, facial performance, Laban movement quality, and anime VFX timing. The document concludes with schemas, prompts, code patterns, acceptance tests, and a closed-loop generation-and-re-extraction protocol.

---

## Executive Summary

The central claim is:

> **Pegasus should recover what the video means, how it is organized, and why each passage functions; specialized extractors should measure exactly where and when visible changes occur.**

A robust system has two synchronized lanes:

| Lane | Main question | Typical outputs |
|---|---|---|
| Pegasus semantic lane | What is happening, what function does it serve, and how is it presented? | scenes, beats, action labels, hook/proof/CTA functions, camera interpretation, directorial purpose, performance hypotheses, VFX descriptions |
| Measurement lane | What visibly changed, where, and at what source time? | presentation timestamps, masks, pose, landmarks, optical flow, contact distances, shot cuts, audio transients, camera transforms |

These lanes are fused only after preserving provenance and uncertainty. A Pegasus statement such as “the creator reveals the product after establishing the problem” is useful semantic evidence. It does not automatically establish the exact reveal frame. A pose tracker can locate the product or hand at a specific frame, but it cannot reliably explain the persuasive purpose of that reveal. The fusion layer needs both.

The highest-fidelity recreation workflow is:

```text
authorized source video
        ↓
media manifest and source clock
        ↓
Pegasus multi-pass semantic extraction
        +
frame-level measurement extraction
        ↓
JSONL observation stream
        ↓
confidence, contradiction, and human-review fusion
        ↓
canonical CPCS JSON score
        ↓
YAML transfer policy and director overrides
        +
XML semantic compiler envelope
        ↓
model adapter
        ↓
text prompt + keyframes + pose/mask/depth/camera/audio controls
        ↓
generated video
        ↓
re-extraction and compliance comparison
```

The formats are not interchangeable:

| Representation | Role |
|---|---|
| JSONL | append-only evidence, per-frame and per-event records, audit trail |
| JSON | canonical resolved intermediate representation |
| YAML | human authoring, style inheritance, substitutions, thresholds, locks |
| XML | semantic hierarchy, role separation, ordered directorial instructions |
| Media/arrays | dense pose, masks, depth, flow, camera, audio, control video |
| Text | semantic fallback for controls unsupported by the target model |

No structured format becomes executable merely because an AI model can tokenize it. Execution occurs only when an adapter maps fields into controls supported by the target system.

---

## 1. Scope and Research Question

This document addresses the following problem:

> Given an authorized reference video, how can Pegasus and supporting tools recover a modular, identity-independent control representation that is precise enough to direct a new AI-generated video with different characters, products, settings, dialogue, or visual style?

The goal is not limited to summarization. It includes:

- high-fidelity UGC recreation with a replacement performer;
- product and brand substitution;
- transfer of creator cadence, gaze pattern, handheld authenticity, demonstration rhythm, and conversion structure;
- reconstruction of fight choreography, including anticipation, attack, defense, near-contact, recoil, fall, and recovery;
- transfer of facial Action Unit timing and affect trajectories;
- transfer of Laban movement qualities;
- separation of actor motion from camera motion;
- preservation of shot and edit grammar;
- recreation of anime-specific timing devices such as holds, smear drawings, impact frames, flashes, speed lines, and time dilation;
- compilation into text-to-video, image-to-video, pose-conditioned, rig-assisted, or video-to-video workflows;
- deterministic validation through re-extraction.

The method does not claim that a single rendered video uniquely reveals the original physical performance or filmmakers’ intentions. Reverse reconstruction is underdetermined. The system records alternatives where evidence is ambiguous.

---

## 2. Definitions

### 2.1 Atomic deconstruction

**Atomic deconstruction** is the decomposition of a video into the smallest units that remain useful for transfer and validation. An atom is not necessarily one frame. It may be:

- one shot transition;
- one action onset;
- one gaze shift;
- one syllable-aligned mouth event;
- one product reveal;
- one foot plant;
- one contact candidate;
- one camera shake impulse;
- one impact flash;
- one call-to-action hold.

Each atom must have a source time, type, subject, value, evidence class, confidence, and provenance.

### 2.2 Modular recreation

**Modular recreation** rebuilds a source by retaining some modules, parameterizing others, replacing others, and excluding prohibited or irrelevant components.

```text
retain:       timing, causal order, camera grammar, motion quality
parameterize: intensity, duration, framing, reaction delay, VFX density
replace:      identity, voice, dialogue, product, brand, wardrobe, setting
exclude:      private data, unlicensed marks, unsafe stunt detail, artifacts
```

### 2.3 Reverse directorial compilation

**Reverse Directorial Compilation (RDC)** infers a structured directorial score from the finished video. Normal compilation goes from intention to video. RDC goes from video to estimated intention, control tracks, and presentation strategy.

### 2.4 High fidelity

High fidelity must be defined by layer. A generation can be semantically faithful but kinematically inaccurate.

| Fidelity type | Question |
|---|---|
| Narrative | Does the same sequence of functions occur? |
| Temporal | Do beats start and end at the intended times? |
| Kinematic | Do bodies and objects follow corresponding trajectories? |
| Performative | Do face, gaze, posture, affect, and movement quality match? |
| Cinematic | Do framing, camera, cuts, and reveals correspond? |
| Audiovisual | Do speech, pauses, impacts, music, and effects align? |
| Marketing | Are hook, proof, product, and CTA relationships preserved? |
| Stylistic | Is the intended new style coherent without retaining protected surface details? |

---

## 3. What Pegasus Contributes

Twelve Labs describes Pegasus as its generative video-to-text model. Pegasus 1.5 supports general prompt-based analysis and time-based video segmentation. Current official documentation states that it analyzes visual content, sound, spoken words, on-screen text, and relationships among modalities. Pegasus 1.5 accepts an asset, URL, or base64 video input without requiring pre-indexing; supports video clipping; supports structured prompts with reference images; and can return structured JSON responses or custom timestamped segments. [TL-01][TL-02]

### 3.1 Appropriate Pegasus responsibilities

Pegasus is well suited to:

- identify scenes and editorial passages;
- name visible actions and interactions;
- identify dialogue and on-screen text function;
- recognize product use, demonstrations, objections, proof, and CTA passages;
- identify broad shot scale, camera angle, and apparent movement;
- explain why a reaction shot or cutaway matters;
- identify character objectives and plausible subtext;
- distinguish setup, escalation, reversal, payoff, and resolution;
- identify anime effects and their perceived role;
- produce timestamped segment proposals;
- return machine-readable fields constrained by JSON Schema;
- compare a video against a reference image supplied in a structured prompt;
- analyze selected clips rather than always processing an entire source;
- analyze many assets through batch requests where appropriate.

### 3.2 Inappropriate Pegasus responsibilities

Pegasus should not be treated as authoritative for:

- exact per-frame joint coordinates;
- precise foot-contact frames;
- millisecond-accurate impact timing without verification;
- dense optical flow;
- actual 3D force or torque;
- hidden movement behind cuts or occlusions;
- guaranteed FACS intensity values;
- definitive mental-state inference;
- proof that apparent contact physically occurred;
- exact lens calibration or camera pose from a stylized source;
- exact reproduction of an edited anime drawing as physical motion.

### 3.3 Current operational constraints

As documented in July 2026:

- synchronous general analysis is intended for videos under one hour;
- asynchronous analysis supports videos up to two hours and is required for video segmentation;
- Pegasus 1.5 structured responses use JSON Schema and should be validated client-side;
- the schema takes precedence over a conflicting prompt;
- clipping uses absolute times based on the video’s internal metadata and requires a minimum four-second analysis window;
- Pegasus 1.5 has a 261,120-token combined context window and supports a maximum response length of 98,304 tokens;
- batch analysis requires Pegasus 1.5 and supports general analysis or time-based metadata per batch, but not mixed modes in the same batch;
- current paid segmentation cost is affected by both billable video duration and number of segment definitions. [TL-03][TL-04][TL-05][TL-06]

These values are operational facts, not permanent characteristics. A production implementation should check the current Twelve Labs release notes and API reference before deployment.

---

## 4. Why Pegasus Must Be Paired With a Measurement Lane

A language-generating video model compresses a large audiovisual signal into a semantic response. That compression is useful but lossy. Exact recreation requires access to information the semantic response normally omits.

### 4.1 Example: UGC product reveal

Pegasus may correctly output:

```text
The creator introduces the product immediately after describing the problem,
then demonstrates it while maintaining direct eye contact with the camera.
```

A recreation system still needs to know:

- exact frame where product visibility exceeds a threshold;
- product screen area over time;
- creator’s hand trajectory;
- gaze-away and gaze-return frames;
- dialogue pause before reveal;
- camera shake and autofocus behavior;
- caption change frame;
- cut or continuity edit at the reveal.

### 4.2 Example: anime strike

Pegasus may correctly output:

```text
The protagonist steps inside the opponent’s guard and lands a decisive
counterstrike, emphasized by a low-angle push-in, impact flash, and recoil.
```

A recreation system still needs:

- support-foot plant;
- pelvis and shoulder phase relationship;
- fist path;
- target location;
- minimum screen-space distance;
- whether contact is shown or hidden;
- exact impact frame;
- defender reaction delay;
- number of held, duplicated, or smeared frames;
- camera transform versus background pan;
- audio transient offset;
- shake decay curve.

### 4.3 Evidence classes

Every extraction record should be typed:

| Class | Meaning | Example |
|---|---|---|
| `measured` | reproducible numerical operation | source PTS, audio peak, pixel displacement |
| `detected` | trained detector output | face box, pose joint, shot boundary |
| `inferred` | conclusion from multiple observations | likely foot plant, staged near-contact |
| `interpreted` | semantic/directorial reading | concealed anxiety, proof beat, reaction purpose |
| `authored` | deliberate recreation decision | replace character, shorten pause, lock contact frame |

Pegasus outputs generally enter as `interpreted` or `inferred`, not `measured`.

---

## 5. Atomic Video Ontology

A reference video should be decomposed through a hierarchy rather than one flat caption.

| Level | Definition | UGC example | Fight example |
|---|---|---|---|
| Asset | complete media object | 23-second vertical ad | 14-second anime clip |
| Sequence | major communicative or dramatic unit | problem-to-solution arc | approach-to-reversal exchange |
| Scene | continuity of place/time/action | bathroom demonstration | rooftop confrontation |
| Shot | uninterrupted presentation unit | handheld medium close-up | low-angle tracking shot |
| Beat | meaningful state change | product first appears | defender commits to dodge |
| Action | executable physical or communicative unit | point, unbox, apply, show result | step-in, pivot, strike, recoil |
| Motion primitive | smaller body component | wrist rotate, gaze return | foot plant, hip turn, elbow extension |
| Micro-event | brief accent | blink, breath, caption pop | impact flash, smear, one-frame hold |
| Frame/sample | source-time observation | product bbox | wrist coordinate, audio sample |

### 5.1 Cross-cutting layers

Every temporal unit can carry several layers:

```text
narrative
marketing
speech and audio
face and gaze
body and Laban
physical action and contact
camera and composition
editing and timing
VFX and anime grammar
identity and asset references
uncertainty and provenance
```

This structure prevents a single phrase such as “aggressive product reveal” from silently mixing acting, camera, editing, color, sound, and marketing intent.

---

## 6. Data Architecture: YAML, JSON, XML, and JSONL

### 6.1 JSONL: atomic evidence stream

JSONL stores one independent record per line. It is appropriate for:

- one Pegasus segment;
- one frame-level pose observation;
- one gaze event;
- one camera transform;
- one human correction;
- one conflict;
- one validation result.

Example:

```json
{"record_id":"pegasus.ugc.proof.0003","source_id":"ugc_001","time_range":{"start_s":7.20,"end_s":10.80},"layer":"marketing","claim":{"type":"proof_passage","value":"side_by_side_result"},"evidence_class":"interpreted","confidence":0.84,"extractor":{"name":"pegasus","version":"1.5","pass":"ugc_structure"}}
```

### 6.2 JSON: canonical resolved score

JSON stores the fully resolved hierarchy after fusion and review. It is the source of truth for compilation because it supports deterministic parsing, arrays for ordered events, JSON Schema validation, and stable references.

### 6.3 YAML: human authoring and transfer policy

YAML stores:

- style profiles;
- defaults and inheritance;
- cast, product, brand, and setting replacement;
- intensity and timing parameters;
- locks and overrides;
- model-adapter configuration;
- acceptance thresholds.

### 6.4 XML: semantic compiler envelope

XML stores ordered, strongly delimited directorial instructions and references to canonical assets. Namespaces can separate CPCS, performance, camera, VFX, marketing, and model-adapter vocabularies.

### 6.5 Dense control assets

Do not serialize all numerical motion into text formats. Store:

- pose control as video, arrays, BVH, FBX, or glTF animation;
- masks as image sequences or encoded video;
- depth and normals as image sequences;
- optical flow as arrays or flow files;
- camera paths as matrices or structured arrays;
- audio alignment as sample/time records.

### 6.6 Recommended flow

```text
Pegasus JSON responses
+ detector JSONL
+ human corrections JSONL
        ↓
fusion and precedence
        ↓
canonical CPCS JSON
        +
YAML transfer policy
        +
XML semantic envelope
        ↓
resolved execution package
```

---

## 7. Source Registration and Temporal Grounding

Before calling Pegasus, register the source and construct a reliable clock.

### 7.1 Required manifest fields

```json
{
  "source_id": "ugc_001",
  "sha256": "...",
  "rights_basis": "licensed_reference",
  "container": "mp4",
  "duration_s": 23.416,
  "video_stream": {
    "time_base": "1/90000",
    "nominal_fps": 29.97,
    "width": 1080,
    "height": 1920,
    "rotation_deg": 0
  },
  "audio_stream": {
    "sample_rate": 48000,
    "channels": 2
  },
  "source_start_time_s": 0.0
}
```

Twelve Labs explicitly notes that clipping times use the video’s internal metadata and that some sources do not begin at zero. Its API reference recommends using `ffprobe` to obtain `start_time` and `duration`. [TL-04]

### 7.2 Verification commands

```bash
ffprobe -v error \
  -show_format -show_streams \
  -of json source.mp4 > source_manifest.raw.json
```

```bash
ffprobe -v error \
  -select_streams v:0 \
  -show_frames \
  -show_entries frame=best_effort_timestamp_time,pkt_duration_time,key_frame,pict_type \
  -of json source.mp4 > frame_timestamps.json
```

### 7.3 Verification checkpoint

Before further processing, verify:

- decoded duration agrees with container duration within an explicit tolerance;
- frame timestamps are monotonic;
- variable-frame-rate status is known;
- orientation metadata has been normalized for analysis;
- source hash is frozen;
- all later records reference the same `source_id` and clock.

---

## 8. Pegasus Multi-Pass Analysis Strategy

A single giant prompt is less reliable than several narrowly aligned passes. Twelve Labs recommends keeping related fields together, splitting complex tasks, using focused schemas, and checking `finish_reason` for truncation. [TL-03]

### 8.1 Pass 0: source map

Purpose:

- identify broad sequence structure;
- list recurring people, products, locations, props, and text;
- detect candidate difficult passages;
- provide stable entity labels.

Output:

```json
{
  "video_summary": "...",
  "entities": [
    {"entity_id":"person_a","type":"person","description":"..."},
    {"entity_id":"product_a","type":"product","description":"..."}
  ],
  "candidate_passages": [
    {"type":"product_reveal","start_s":3.2,"end_s":5.4},
    {"type":"fast_action","start_s":11.8,"end_s":14.9}
  ]
}
```

### 8.2 Pass 1: scenes and shots

Use time-based metadata for broad scene segmentation. Extract:

- setting;
- visible entities;
- visual composition;
- action summary;
- speech presence;
- apparent camera angle;
- transition relationship.

Pegasus segment boundaries are semantic proposals. Snap them to measured cuts or source frames during fusion.

### 8.3 Pass 2: narrative and persuasive beats

For UGC, request:

```text
hook
problem
agitation
product introduction
demonstration
proof
objection handling
benefit restatement
brand reveal
CTA
```

For dramatic action, request:

```text
threat
approach
feint
commitment
attack
defense
counterattack
reversal
impact
aftermath
```

### 8.4 Pass 3: camera and editing

Request separate fields for:

- shot scale;
- angle;
- composition;
- apparent camera motion;
- subject motion relative to frame;
- cut function;
- reveal function;
- continuity and screen direction;
- confidence and alternatives.

Do not request a single field named `camera_style`; it is too broad.

### 8.5 Pass 4: performance

Request:

- visible gaze target;
- head and torso orientation;
- posture changes;
- visible facial changes;
- inferred displayed affect;
- possible concealed versus displayed affect;
- Laban-style interpretation;
- uncertainty caused by occlusion, stylization, or blur.

### 8.6 Pass 5: physical action

Request ordered visible action units without claiming hidden biomechanics:

```text
step
plant
pivot
reach
guard
strike-like extension
dodge
duck
block-like action
recoil
fall
landing
recovery
```

Pegasus labels are then aligned to pose and flow measurements.

### 8.7 Pass 6: VFX and audio

Request:

- visible effect type;
- apparent start and end;
- relationship to action;
- sound effect or music accent;
- whether the effect hides physical contact;
- whether time appears slowed, held, repeated, or accelerated.

### 8.8 Pass 7: contradiction and uncertainty

Give Pegasus a structured summary from earlier passes and ask it to identify:

- inconsistent entity assignments;
- overlapping action descriptions;
- uncertain contact claims;
- camera-versus-object-motion ambiguity;
- missing passages;
- interpretations unsupported by visible evidence.

This is a quality-control pass, not a replacement for programmatic validation.

---

## 9. Pegasus Analysis Modes

### 9.1 General analysis with structured JSON

Use this mode when the unit is known and the desired output is a nested analysis. Examples:

- deep analysis of one six-second exchange;
- UGC persuasive structure for an entire 20-second clip;
- shot-purpose explanation;
- ordered beat analysis;
- comparison with a reference product image.

The prompt specifies the analysis task. The JSON Schema specifies the output shape. Twelve Labs states that the schema takes precedence if the two conflict. [TL-03]

### 9.2 Time-based metadata with segment definitions

Use this mode when Pegasus should discover multiple timestamped passages of a defined type. Examples:

- all product demonstrations;
- all direct-to-camera claims;
- all combat exchanges;
- all reaction shots;
- all visible anime impact effects;
- all brand appearances.

Each segment definition contains:

- a unique ID;
- a natural-language description of the segment type;
- optional typed fields;
- optional time constraints.

### 9.3 Clipped analysis

Use `start_time` and `end_time` to analyze a difficult passage independently. Current Pegasus 1.5 clipping requires a minimum four-second window. Padding should therefore be added around very short events, and the final event times should be resolved against the source clock. [TL-04]

### 9.4 Reference-image prompting

Pegasus 1.5 structured prompts can include reference images. This is useful for:

- identifying a specific product in a UGC video;
- maintaining stable entity references across clips;
- checking whether a replacement product occupies the same visual role;
- identifying a specific costume, object, or visual motif.

Reference images support semantic recognition. They do not provide frame-accurate tracking by themselves.

### 9.5 Batch analysis

Batch analysis is useful for:

- running the same schema over many UGC references;
- building a corpus of hooks, proof patterns, and CTA structures;
- analyzing multiple fight clips using a shared action schema;
- evaluation of generated variants.

The current API requires one analysis mode per batch. General analysis and time-based metadata should be placed in separate batches. [TL-06]

---

## 10. Structured Pegasus Output Design

### 10.1 Design principles

A Pegasus schema should follow six rules:

1. **One analytical purpose per schema.** Do not combine unrelated requests for marketing, combat, legal review, and color grading.
2. **Observable language first.** Ask for what is visibly or audibly present before asking for interpretation.
3. **Explicit uncertainty.** Every interpretation should permit uncertainty or alternative explanations.
4. **Stable entity IDs.** Use identifiers such as `creator_a`, `fighter_a`, and `product_a` rather than repeatedly describing appearance.
5. **Ordered arrays for time.** Do not rely on JSON object-key order.
6. **Client-side validation.** Parse the returned JSON string, validate it, and quarantine truncated or invalid responses.

### 10.2 Generic atomic-beat schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "analysis_scope": {"type": "string"},
    "participants": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "entity_id": {"type": "string"},
          "role": {"type": "string"}
        },
        "required": ["entity_id", "role"]
      }
    },
    "ordered_beats": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "beat_id": {"type": "string"},
          "approximate_start_s": {"type": "number"},
          "approximate_end_s": {"type": "number"},
          "observable_event": {"type": "string"},
          "semantic_function": {"type": "string"},
          "initiator": {"type": ["string", "null"]},
          "target": {"type": ["string", "null"]},
          "camera_function": {"type": "string"},
          "audio_function": {"type": "string"},
          "uncertainty": {"type": "string"},
          "confidence": {"type": "number", "minimum": 0, "maximum": 1}
        },
        "required": [
          "beat_id",
          "approximate_start_s",
          "approximate_end_s",
          "observable_event",
          "semantic_function",
          "uncertainty",
          "confidence"
        ]
      }
    }
  },
  "required": ["analysis_scope", "participants", "ordered_beats"]
}
```

Twelve Labs supports JSON Schema Draft 2020-12 with documented constraints and recommends starting with focused schemas. Unsupported schema keywords should be removed if the API rejects them. [TL-03]

### 10.3 Evidence-normalization wrapper

The raw Pegasus output should be wrapped before insertion into the observation stream:

```json
{
  "record_id": "pegasus.fight.beat.0007",
  "source_id": "fight_001",
  "source_time": {
    "start_s": 4.100,
    "end_s": 4.780,
    "clock": "source_pts"
  },
  "layer": "action_semantics",
  "claim": {
    "type": "counterattack",
    "initiator": "fighter_a",
    "target": "fighter_b"
  },
  "evidence_class": "interpreted",
  "confidence": 0.82,
  "extractor": {
    "provider": "twelvelabs",
    "model": "pegasus1.5",
    "analysis_mode": "general",
    "pass_id": "fight_atomic_beats_v3",
    "task_id": "REDACTED_OR_INTERNAL"
  },
  "raw_response_ref": "pegasus/pass_04_fight_atomic.json",
  "review_status": "unreviewed"
}
```

---

## 11. Parallel Measurement Lane

Pegasus is only one contributor. The measurement lane should contain independently reproducible signals.

### 11.1 Shot and transition detection

Extract hard cuts, fades, dissolves, and brief flash transitions. Use source frames rather than a resampled proxy where possible. Store both detector result and human correction.

### 11.2 Entity segmentation and tracking

Promptable video segmentation systems such as SAM 2 can propagate actor and object masks over time. SAM 2 uses streaming memory for video processing and is designed for interactive promptable segmentation. [CV-01]

Required outputs:

```text
actor masks
product masks
weapon or prop masks
energy-effect masks
foreground occluder masks
background confidence masks
```

### 11.3 Human pose and body landmarks

OpenPose established a bottom-up multi-person approach using Part Affinity Fields and supports body, foot, hand, and facial keypoints. [CV-02] Modern implementations may be substituted, but the output should retain:

- detector name and version;
- joint convention;
- coordinate system;
- confidence per joint;
- identity-association confidence;
- raw and corrected tracks.

For anime, automatic pose estimates often fail on exaggerated foreshortening, stylized proportions, occlusion, duplicate speed silhouettes, and smear drawings. Critical frames require manual review.

### 11.4 Optical flow

RAFT estimates dense correspondence between frame pairs using all-pairs correlation and recurrent updates. [CV-03] Flow helps measure:

- fast limb direction;
- smear direction;
- hair and cloth movement;
- background pan;
- shake impulse;
- energy trail direction;
- motion not captured by joints.

### 11.5 Face, gaze, and expression

For real UGC, face analysis can estimate:

- landmarks;
- head pose;
- gaze direction;
- blink timing;
- mouth aperture;
- candidate facial Action Units;
- visibility and occlusion.

EMOCA demonstrates monocular 3D face reconstruction designed to preserve emotional expression and directly estimates valence and arousal from reconstructed facial parameters. [CV-04] It is evidence that face geometry and affect can be linked, not a guarantee that one model will recover ground-truth FACS values from every UGC source.

For anime, use a character-specific functional mapping rather than assuming a photorealistic AU detector transfers unchanged.

### 11.6 Camera estimation

Separate:

- global image transform;
- background transform;
- actor-relative motion;
- focal change;
- crop or digital push;
- shake;
- parallax.

The interpretation `dolly_in` should remain distinct from a measured scale and translation curve. MotionCtrl’s explicit separation of camera motion and object motion reinforces this architectural distinction for controllable video generation. [VG-01]

### 11.7 Audio and speech

Extract:

- transcript with word times;
- speaker turns;
- breaths and mouth noises;
- pauses;
- speaking rate;
- pitch and intensity contours;
- music beats;
- impact transients;
- silence boundaries;
- caption timing and on-screen text.

The source clock must align audio samples to video frames.

---

## 12. Observation Fusion and Precedence

### 12.1 Precedence hierarchy

A recommended default is:

```text
human-reviewed lock
    >
verified source measurement
    >
high-confidence detector observation
    >
fused inference from multiple detectors
    >
Pegasus semantic interpretation
    >
project default
```

This hierarchy is typed rather than absolute. Pegasus may be more authoritative for narrative function than a pose tracker, while the pose tracker is more authoritative for wrist location.

### 12.2 Conflict example

Pegasus output:

```json
{"claim":"fighter_a punches fighter_b in the face","confidence":0.88}
```

Measurement outputs:

```text
minimum wrist-to-head screen distance: 0.018 frame diagonal
contact region occluded by one-frame flash
no unoccluded intersection visible
reaction begins 1 frame later
```

Resolved record:

```json
{
  "type": "staged_near_contact_or_occluded_contact",
  "display_label": "strike-like action to head target",
  "confidence": 0.79,
  "alternatives": [
    {"value": "physical_contact", "confidence": 0.44},
    {"value": "near_contact_with_editing_cheat", "confidence": 0.63}
  ],
  "lock_for_recreation": "staged_near_contact"
}
```

The recreation can preserve the audience-readable result without asserting an unknowable source fact.

### 12.3 Temporal snapping

Pegasus segment times should be aligned to:

- nearest source frame;
- measured cut;
- detected action onset;
- audio transient;
- human-reviewed event frame.

Store both the raw and resolved times:

```json
{
  "pegasus_start_s": 4.1,
  "resolved_start_frame": 98,
  "resolved_start_s": 4.083,
  "resolution_method": "snap_to_pose_velocity_onset",
  "difference_ms": -17
}
```

---

## 13. CPCS Mapping

The fused observation graph compiles into CPCS layers.

| Extracted evidence | CPCS target |
|---|---|
| facial landmarks and AU candidates | FACS curves |
| inferred affect | experienced/displayed VAD or VAC trajectory |
| pose and movement-quality evidence | Laban Body, Effort, Shape, Space |
| discrete physical actions | combat/action coding graph |
| actor and object trajectories | kinematic and interaction tracks |
| cuts, angles, camera motion | director and editorial controls |
| flash, dust, trails, shake, smear | VFX/anime event tracks |
| hook, proof, CTA, visibility | marketing control graph |
| speech, pause, impact, music | audio and dialogue tracks |

### 13.1 Performance state

```json
{
  "actor_id": "creator_a",
  "time_range": {"start_s": 2.1, "end_s": 4.8},
  "affect": {
    "experienced": {"valence": 0.22, "arousal": 0.48, "control": 0.61},
    "displayed": {"valence": 0.61, "arousal": 0.72, "control": 0.79}
  },
  "face": {
    "au_tracks_ref": "tracks/creator_a_facs.jsonl",
    "gaze_target": "camera_lens"
  },
  "laban": {
    "weight": "light",
    "time": "sudden",
    "space": "direct",
    "flow": "free"
  }
}
```

### 13.2 Action state

```json
{
  "action_id": "ACT_014",
  "actor": "fighter_a",
  "type": "right_strike_like_extension",
  "start_frame": 112,
  "anticipation_apex_frame": 121,
  "target_frame": 148,
  "end_frame": 154,
  "target": "fighter_b.head",
  "support": ["left_foot", "right_foot"],
  "local_phase_refs": {
    "pelvis": "phase/pelvis_ACT_014.json",
    "torso": "phase/torso_ACT_014.json",
    "right_arm": "phase/right_arm_ACT_014.json"
  }
}
```

---

# Part II — High-Fidelity UGC Recreation

## 14. UGC Reconstruction Objective

The UGC goal is not merely to generate “a person talking about a product.” It is to transfer a tested audiovisual communication pattern to a different authorized performer, product, setting, brand, script, and output format.

A UGC source may derive realism from:

- imperfect handheld framing;
- brief autofocus adjustments;
- direct lens address;
- natural eye breaks;
- irregular but intentional speech rhythm;
- hand-to-product coordination;
- jump cuts hidden by gesture continuity;
- product visibility at precise moments;
- caption rhythm;
- room tone and mouth sounds;
- credible pauses and self-corrections;
- demonstration before strong claim;
- reaction after proof;
- restrained brand reveal.

Pegasus can identify the semantic and persuasive structure. Frame-level analysis measures how that structure is executed.

---

## 15. UGC Atomic Deconstruction Layers

### 15.1 Communication graph

```text
hook
→ problem recognition
→ creator credibility cue
→ product introduction
→ demonstration
→ proof
→ benefit interpretation
→ objection handling
→ CTA
```

Not every source uses every node. Pegasus should identify the observed order rather than forcing a generic template.

### 15.2 Speech and language

Extract:

- transcript;
- wording function rather than copyrighted wording alone;
- words per minute;
- clause length;
- pause durations;
- filler-word pattern;
- emphasis words;
- sentence-to-shot alignment;
- claim versus proof order;
- CTA phrasing class.

For recreation, the function can be retained while exact wording is replaced.

### 15.3 Gaze and face

Measure:

- percentage of time looking at lens;
- gaze departures to product, screen, or side;
- blink placement;
- smile onset;
- brow activity around claims;
- mouth behavior during demonstration;
- reaction expression after visible result.

### 15.4 Body and object handling

Measure:

- hand used to hold product;
- grip and orientation;
- product path;
- product-to-camera distance;
- gesture amplitude;
- torso lean;
- head nods;
- point and reveal timing;
- product screen area;
- occlusion by hands.

### 15.5 Camera authenticity

Measure:

- base framing;
- device height and tilt;
- handheld displacement spectrum;
- crop changes;
- autofocus or exposure shifts;
- continuity edits;
- foreground-background stability;
- rolling shutter or motion blur if relevant.

### 15.6 Marketing variables

Measure and interpret:

```text
time to first face
time to first lens address
time to first product appearance
time to first demonstrated result
product visibility duty cycle
caption density
cut count
average shot duration
proof-before-claim relationship
brand reveal time
CTA start and duration
```

These are descriptive variables and testable hypotheses. They do not guarantee conversion.

---

## 16. Pegasus UGC Passes

### 16.1 Pass U1 — persuasive structure

Prompt objective:

> Identify the ordered communication functions in the video. Distinguish visible demonstration, verbal claim, proof, objection handling, brand reveal, and call to action. Do not assume a function that is not supported by visible or audible evidence.

Output fields:

```text
segment_type
start_time
end_time
observable_content
spoken_function
visual_function
product_role
creator_role
audience_assumption
uncertainty
```

### 16.2 Pass U2 — authenticity cues

Ask Pegasus to identify visible and audible cues that make the source feel creator-made rather than studio-made:

- direct lens address;
- casual environment;
- handheld or phone-like framing;
- self-correction;
- incomplete sentence;
- off-axis gaze;
- natural handling noise;
- unpolished transition;
- personal testimony;
- practical demonstration.

The measurement lane quantifies the timing and magnitude of these cues.

### 16.3 Pass U3 — product interaction

Use reference-image prompting when a specific product must be identified. Request:

- appearance intervals;
- handling action;
- orientation;
- demonstration stage;
- visible result;
- relationship between spoken claim and visible proof.

### 16.4 Pass U4 — shot and edit strategy

Request:

- shot scale;
- subject placement;
- cut purpose;
- jump-cut concealment;
- reveal timing;
- use of insert or close-up;
- text overlays;
- pacing shift.

### 16.5 Pass U5 — transfer blueprint

After factual passes, provide their structured outputs to a separate reasoning step and ask for an identity-independent blueprint:

```text
retain timing relationships
replace wording and identity
parameterize energy and pacing
identify elements that require pose or object tracks
identify elements that can compile to text only
```

This is an authored production blueprint, not a new observation of the source.

---

## 17. UGC Canonical Score Example

```json
{
  "schema": "cpcs-ugc-score/1.0",
  "source_id": "ugc_001",
  "duration_s": 18.4,
  "format": {"aspect_ratio": "9:16", "fps": 30},
  "characters": [
    {"actor_id": "creator_a", "role": "creator_presenter"}
  ],
  "products": [
    {"product_id": "product_a", "role": "demonstrated_solution"}
  ],
  "beats": [
    {
      "beat_id": "B01",
      "function": "visual_hook",
      "start_s": 0.0,
      "end_s": 1.1,
      "performance": {
        "gaze_target": "lens",
        "speech_energy": 0.82,
        "displayed_arousal": 0.74
      },
      "camera": {
        "shot_scale": "medium_close_up",
        "handheld_profile_ref": "tracks/camera_handheld.json"
      },
      "marketing": {
        "product_visible": false,
        "problem_cue": true
      }
    },
    {
      "beat_id": "B02",
      "function": "product_reveal",
      "start_s": 1.1,
      "end_s": 2.7,
      "physical_action": {
        "action": "raise_product_to_camera",
        "trajectory_ref": "tracks/product_reveal_path.json"
      },
      "marketing": {
        "first_product_visibility_s": 1.18,
        "target_screen_area_peak": 0.21
      }
    },
    {
      "beat_id": "B03",
      "function": "demonstration_and_proof",
      "start_s": 2.7,
      "end_s": 11.9,
      "product_interactions_ref": "tracks/product_demo.jsonl",
      "caption_track_ref": "tracks/captions.jsonl"
    },
    {
      "beat_id": "B04",
      "function": "cta",
      "start_s": 15.8,
      "end_s": 18.4,
      "performance": {
        "gaze_target": "lens",
        "speech_energy": 0.62,
        "displayed_control": 0.81
      }
    }
  ]
}
```

---

## 18. UGC Transfer Policy in YAML

```yaml
project:
  id: ugc_recreation_001
  objective: recreate communication structure with a new performer and product

imports:
  canonical_score:
    type: json
    path: ../canonical/ugc_score.json
  evidence:
    type: jsonl
    path: ../fusion/ugc_observations.jsonl

transfer_policy:
  retain:
    - beat_order
    - shot_duration_ratios
    - lens_address_schedule
    - product_reveal_timing
    - demonstration_order
    - proof_before_benefit_interpretation
    - caption_change_rhythm
    - handheld_motion_spectrum

  parameterize:
    speaking_rate_scale: 0.95
    gesture_amplitude_scale: 0.85
    handheld_amplitude_scale: 0.70
    hook_duration_scale: 0.90

  replace:
    - performer_identity
    - performer_voice
    - exact_dialogue
    - product_identity
    - brand_identity
    - room_identity
    - wardrobe

new_assets:
  performer: assets/new_creator_reference.png
  product: assets/new_product_reference.png
  room: assets/new_room_reference.png
  voice: assets/authorized_voice_profile.json

locks:
  - path: beats.B02.marketing.first_product_visibility_s
    tolerance_s: 0.10
  - path: beats.B04.function
    value: cta

safety_and_rights:
  source_likeness_transfer: prohibited
  source_voice_transfer: prohibited
  exact_dialogue_transfer: prohibited
```

---

## 19. UGC Compilation Strategy

### 19.1 Text-only target

Compile only high-level semantics:

- performer and environment;
- beat order;
- dialogue function;
- product reveal;
- camera behavior;
- timing language.

Expected fidelity: broad structure, not exact hand and gaze timing.

### 19.2 Image-to-video target

Provide:

- approved performer reference;
- approved product reference;
- opening composition;
- key product-reveal frame;
- text prompt;
- approximate beat timing.

Expected fidelity: improved identity and composition, moderate motion control.

### 19.3 Pose/object-conditioned target

Provide:

- pose control video;
- product mask and trajectory;
- gaze/head-pose targets;
- camera motion track;
- approved reference images;
- speech or audio timing.

Expected fidelity: high structural and movement correspondence.

### 19.4 Video-to-video target

Create a privacy-safe control render using a neutral rig or silhouette:

```text
new performer rig
+ source-derived motion
+ source-derived camera
+ replacement product proxy
+ no source texture, face, voice, or branding
```

Then apply the desired visual realism and approved identity. This is generally the most direct path to preserving motion and pacing while replacing surface identity.

---

## 20. UGC Validation

Re-extract the generated video and compare:

| Metric | Example check |
|---|---|
| Beat order | exact graph-order match |
| Product reveal | error in seconds or frames |
| Product visibility | screen-area curve similarity |
| Lens address | gaze duty-cycle difference |
| Speech pace | words/minute and pause-distribution error |
| Gesture timing | hand trajectory dynamic-time-warping distance |
| Camera authenticity | transform-spectrum similarity |
| Cut rhythm | shot-duration distribution |
| Caption rhythm | timing and density difference |
| CTA | start, duration, lens address, brand visibility |

A generation should fail validation if the product appears too late, the proof is omitted, the performer never looks at the lens, or the CTA is shortened below the project threshold—even if the video looks attractive.

---

# Part III — Fight and Anime Action Reconstruction

## 21. Fight-Scene Reconstruction Objective

A fight scene is a coupled system of bodies, targets, supports, camera, editing, audio, and stylized exaggeration. The source cannot be represented adequately as a list of poses or a prose sentence such as “they fight intensely.”

The portable core is an **action-causality graph**:

```text
approach
→ preparation
→ foot plant
→ weight shift
→ attack initiation
→ target commitment
→ defense or avoidance
→ near-contact/contact event
→ audiovisual impact
→ recoil
→ displacement or fall
→ recovery
```

Pegasus explains the tactical and cinematic function. The measurement lane reconstructs visible trajectories and timing.

---

## 22. Fight Atomic Deconstruction Layers

### 22.1 Tactical layer

- who initiates;
- intended target;
- attack or defense class;
- range change;
- feint or commitment;
- reversal;
- advantage state.

### 22.2 Body-action layer

- step-in;
- plant;
- pivot;
- pelvis rotation;
- torso rotation;
- guard change;
- extension;
- dodge;
- duck;
- block-like movement;
- recoil;
- fall;
- landing;
- recovery.

### 22.3 Phase layer

Each action has temporal landmarks:

```text
onset
anticipation apex
acceleration onset
maximum extension
minimum target distance
impact accent
follow-through apex
recovery onset
settle
```

Complex actions need local phases for feet, pelvis, torso, arms, head, weapon, and opponent reaction.

### 22.4 Interaction layer

- actor-to-actor distance;
- hand-to-target distance;
- weapon-to-target distance;
- support contacts;
- collision or near-contact status;
- reaction delay;
- momentum direction;
- occlusion and camera cheating.

### 22.5 Laban layer

- Weight: light or strong;
- Time: sustained or sudden;
- Space: indirect or direct;
- Flow: free or bound.

The values describe movement quality, not action identity. The same strike graph can be performed with different Laban qualities.

### 22.6 Face and affect layer

- gaze target;
- blink suppression;
- jaw and brow activity;
- displayed valence, arousal, and control;
- change before and after reversal;
- stylized anime face deformation.

### 22.7 Camera and edit layer

- screen direction;
- shot scale;
- angle;
- push, pan, orbit, crop, shake;
- cut-on-action;
- impact cut;
- reaction cut;
- held frame;
- time warp.

### 22.8 Anime VFX layer

- smear drawing;
- impact flash;
- speed lines;
- motion echo;
- energy trail;
- dust burst;
- debris;
- frame repetition;
- background abstraction;
- color or exposure pulse;
- screen deformation.

---

## 23. Pegasus Fight Passes

### 23.1 Pass F1 — exchange segmentation

Segment the source into tactical passages:

```text
approach
standoff
attack
defense
counterattack
recoil
fall
recovery
reaction
```

Fields:

```text
participants
initiator
target
visible_actions
tactical_function
camera_presentation
vfx_summary
contact_visibility
uncertainty
```

### 23.2 Pass F2 — ordered visible actions

For each passage, request an ordered list of visible physical events. Instruct Pegasus not to invent hidden motion. Require explicit language when cuts, flashes, blur, or occlusion hide the action.

### 23.3 Pass F3 — tactical and emotional interpretation

Request:

- apparent objective;
- commitment versus hesitation;
- dominance change;
- reaction and recovery;
- displayed affect;
- gaze relationship;
- narrative reversal.

### 23.4 Pass F4 — camera and editorial causality

Request:

- what action the camera makes readable;
- what action is hidden;
- whether the edit creates the impact;
- whether background motion implies camera movement;
- whether time is held, repeated, or slowed;
- whether screen direction remains continuous.

### 23.5 Pass F5 — anime effects

Request separate events for:

- effect onset;
- effect type;
- relationship to body movement;
- relationship to sound;
- whether it replaces a physically readable frame;
- whether it should be recreated as generation-time style or post-composite VFX.

---

## 24. Fight Measurement Pipeline

### 24.1 Track all participants

Use stable actor IDs and masks. Preserve identity through occlusion and cuts. A brief duplicate smear silhouette should not automatically create another actor.

### 24.2 Extract reviewed 2D pose

For each critical frame, store:

- root or pelvis;
- shoulders;
- elbows;
- wrists;
- head center and orientation;
- hips;
- knees;
- ankles;
- heel and toe when visible;
- weapon endpoints;
- contour anchors for stylized limbs.

### 24.3 Derive motion primitives

Examples:

```text
left ankle velocity approaches zero while pelvis advances
→ left-foot plant candidate

pelvis rotation precedes shoulder rotation
→ proximal-to-distal strike sequencing

wrist-target distance reaches local minimum
+ impact flash occurs
+ defender recoil follows
→ staged impact event candidate
```

### 24.4 Separate camera and body motion

Estimate background transform after masking actors and effects. Store measured transform independently from cinematic interpretation.

### 24.5 Preserve screen-space truth

For heavily stylized anime, screen-space reconstruction may be more faithful than forced 3D reconstruction. A drawn limb may change length or perspective for one frame. Preserve:

- silhouette;
- image-space joint path;
- target relationship;
- timing;
- perceived force.

A physically plausible rig can then approximate this effect while a compositor restores deliberate stylization.

### 24.6 Optional physics refinement

DeepMimic demonstrates that physics-based controllers can imitate reference motions and recover from perturbations, including martial-arts and acrobatic skills. [AN-01] A physics stage is useful when the new scene requires changed terrain, body proportions, or interaction. It should not erase deliberate anime timing or impossible screen-space exaggeration.

---

## 25. Fight JSONL Evidence Examples

```json
{"record_id":"pose.fighter_a.00148","source_id":"fight_001","frame_index":148,"pts_s":6.172,"layer":"pose","claim":{"coordinate_system":"image_normalized","joints":{"pelvis":{"x":0.421,"y":0.681,"confidence":0.93},"right_wrist":{"x":0.671,"y":0.332,"confidence":0.77}}},"evidence_class":"detected","extractor":{"name":"pose_fusion","version":"1.0"},"review_status":"reviewed"}
```

```json
{"record_id":"flow.right_arm.00147_00148","source_id":"fight_001","frame_range":{"start":147,"end":148},"layer":"optical_flow","claim":{"region":"fighter_a.right_arm","mean_direction_deg":-18.4,"mean_magnitude_px":46.2,"peak_magnitude_px":121.7,"coherence":0.81},"evidence_class":"measured","extractor":{"name":"raft","version":"implementation_pinned"}}
```

```json
{"record_id":"pegasus.action.0009","source_id":"fight_001","time_range":{"start_s":5.9,"end_s":6.6},"layer":"action_semantics","claim":{"type":"counterstrike","initiator":"fighter_a","target":"fighter_b.head","narrative_function":"reversal"},"evidence_class":"interpreted","confidence":0.86,"extractor":{"name":"pegasus","version":"1.5","pass":"fight_actions"}}
```

```json
{"record_id":"fusion.contact.00148","source_id":"fight_001","frame_index":148,"pts_s":6.172,"layer":"interaction","claim":{"type":"staged_near_contact","source":"fighter_a.right_wrist","target":"fighter_b.head","minimum_distance_norm":0.011,"occluded":true,"impact_flash":true},"evidence_class":"inferred","confidence":0.79,"inputs":["pose.fighter_a.00148","pose.fighter_b.00148","flow.right_arm.00147_00148","pegasus.action.0009"],"review_status":"reviewed"}
```

---

## 26. Fight Canonical CPCS Score Example

```json
{
  "schema": "cpcs-fight-score/1.0",
  "source_id": "fight_001",
  "fps": 24,
  "shots": [
    {
      "shot_id": "SHOT_003",
      "start_frame": 96,
      "end_frame": 167,
      "screen_direction": "left_to_right_attack",
      "camera": {
        "shot_scale": "medium_wide",
        "angle": "low",
        "trajectory_ref": "controls/camera_SHOT_003.json"
      },
      "beats": [
        {
          "beat_id": "B_003_02",
          "function": "counterattack_reversal",
          "start_frame": 112,
          "end_frame": 166,
          "actions": [
            {
              "actor": "fighter_a",
              "type": "step_in",
              "start_frame": 112,
              "apex_frame": 121,
              "end_frame": 126
            },
            {
              "actor": "fighter_a",
              "type": "right_strike_like_extension",
              "start_frame": 120,
              "target_frame": 148,
              "end_frame": 154,
              "target": "fighter_b.head",
              "contact_policy": "staged_near_contact"
            },
            {
              "actor": "fighter_b",
              "type": "recoil",
              "start_frame": 149,
              "apex_frame": 158,
              "end_frame": 166
            }
          ],
          "laban": {
            "fighter_a": {
              "weight": 0.88,
              "time": 0.94,
              "space": 0.91,
              "flow": 0.24
            }
          },
          "face": {
            "fighter_a": {
              "gaze_target": "fighter_b.head",
              "displayed_arousal": 0.84,
              "displayed_control": 0.78
            }
          },
          "vfx": [
            {"type":"impact_flash","start_frame":148,"duration_frames":1},
            {"type":"camera_shake","start_frame":148,"end_frame":153,"curve_ref":"controls/shake_148_153.json"}
          ],
          "audio": {
            "impact_frame": 149,
            "impact_offset_from_visual_frames": 1
          }
        }
      ]
    }
  ]
}
```

---

## 27. Fight Transfer YAML

```yaml
project:
  id: fight_recreation_001
  objective: preserve choreography and cinematic readability with replacement characters

imports:
  score:
    type: json
    path: ../canonical/fight_score.json
  observations:
    type: jsonl
    path: ../fusion/fight_observations.jsonl

transfer_policy:
  retain:
    - shot_order
    - screen_direction
    - action_causality
    - support_foot_schedule
    - major_joint_trajectory_shape
    - target_relationships
    - impact_frame
    - reaction_delay
    - laban_quality
    - camera_grammar
    - vfx_timing

  parameterize:
    action_speed_scale: 0.92
    displacement_scale: 1.05
    camera_shake_scale: 0.75
    energy_effect_density: 0.65

  replace:
    - character_identity
    - costume
    - setting
    - exact_energy_design
    - dialogue
    - source_music

characters:
  fighter_a:
    replace_with: protagonist
    rig: assets/protagonist.glb
  fighter_b:
    replace_with: antagonist
    rig: assets/antagonist.glb

locks:
  - path: shots.SHOT_003.beats.B_003_02.actions[1].target_frame
    value: 148
  - path: shots.SHOT_003.screen_direction
    value: left_to_right_attack

safety:
  choreography_type: staged_fictional_action
  require_non_contact_version: true
  require_rig_collision_review: true
```

---

## 28. Fight Compilation Tiers

### Tier 1 — text only

Compile the action graph into precise ordered language. This is useful for ideation but cannot guarantee frame-level recreation.

### Tier 2 — key poses

Provide anticipation, extension, target, recoil, and recovery frames. The model interpolates between them.

### Tier 3 — pose-conditioned video

Render a full pose sequence from reviewed tracks. Provide masks, character references, camera plan, and text.

### Tier 4 — rigged animation intermediate

Retarget to a 3D rig, correct support and balance, animate the camera, and render control passes:

```text
pose
silhouette
mask
depth
normal
optical flow
camera path
```

### Tier 5 — video-to-video appearance transfer

Render a neutral, rights-safe control video with replacement body proportions and no source likeness. Use this as the motion carrier for generative styling.

For exact movement, Tier 3 or higher is normally required. Pegasus provides the semantic score but not the executable frame-by-frame carrier.

---

## 29. Fight Validation

### 29.1 Temporal metrics

```text
shot-boundary error
action-onset error
target-frame error
reaction-delay error
VFX onset error
audio-impact offset error
```

### 29.2 Motion metrics

```text
root trajectory error
joint trajectory error
pose dynamic-time-warping distance
silhouette overlap
foot slip
contact distance
optical-flow direction similarity
```

### 29.3 Performance metrics

```text
gaze target match
FACS onset/apex/offset error
Laban dimension deviation
recoil amplitude
recovery duration
```

### 29.4 Cinematic metrics

```text
screen direction
shot scale
subject placement
camera transform
cut order
impact-frame presence
shake decay
```

Example acceptance profile:

```yaml
acceptance:
  action_order:
    exact_match: true
  screen_direction:
    exact_match: true
  target_frame:
    tolerance_frames: 1
  reaction_delay:
    tolerance_frames: 2
  major_joint_screen_error:
    max_fraction_frame_diagonal: 0.03
  impact_flash:
    required: true
    tolerance_frames: 0
  foot_slip:
    max_normalized_distance_during_contact: 0.008
```

These values are project thresholds, not universal standards.

---

# Part IV — Information Transfer and Compilation

## 30. AI Information and Data Transfer Model

The workflow is an information-preservation system. Each transformation should make explicit what information is retained, compressed, inferred, or discarded.

### 30.1 Source video to Pegasus response

Preserved well:

- semantic relationships;
- broad action;
- speech and text meaning;
- narrative and persuasive structure;
- visible camera and effect descriptions.

Compressed or uncertain:

- frame-level trajectories;
- brief events;
- hidden contact;
- exact physical causes;
- raw audiovisual details.

### 30.2 Source video to detector stream

Preserved well:

- coordinates;
- timing;
- masks;
- motion vectors;
- acoustic events.

Compressed or uncertain:

- intention;
- narrative purpose;
- persuasion function;
- subtext.

### 30.3 Fusion to CPCS

The fusion layer transforms observations into portable control concepts. It should never erase source provenance.

### 30.4 CPCS to model adapter

The adapter performs capability negotiation:

```text
supported natively
→ map to native parameter or control channel

supported through media
→ render pose, mask, depth, keyframe, or control video

supported only semantically
→ compile to prompt text

unsupported
→ postproduction instruction, approximation, warning, or error
```

### 30.5 Generation back to evidence

The generated video is re-extracted using the same schemas. Comparison produces measurable compliance evidence and informs the next generation.

---

## 31. XML Semantic Envelope Example

```xml
<cpcs:recreation-request
    xmlns:cpcs="urn:cpcs:recreation:1"
    xmlns:perf="urn:cpcs:performance:1"
    xmlns:cam="urn:cpcs:camera:1"
    xmlns:vfx="urn:cpcs:vfx:1"
    xmlns:mkt="urn:cpcs:marketing:1">

  <cpcs:source-score
      href="../canonical/resolved_score.json"
      sha256="REPLACE_WITH_VERIFIED_HASH"/>

  <cpcs:objective>
    Produce a materially new video with replacement characters and assets
    while preserving the authorized timing, action relationships, camera
    grammar, performance dynamics, and communication structure.
  </cpcs:objective>

  <cpcs:authority>
    <cpcs:locked-values source="../authoring/locks.yaml"/>
    <cpcs:canonical-json priority="higher-than-language-model"/>
  </cpcs:authority>

  <perf:direction>
    <perf:instruction priority="required">
      Preserve the distinction between experienced affect and displayed affect.
    </perf:instruction>
    <perf:instruction priority="required">
      Preserve Laban timing and flow unless explicitly overridden.
    </perf:instruction>
  </perf:direction>

  <cam:direction>
    Preserve screen direction, shot order, and reveal timing.
  </cam:direction>

  <vfx:direction>
    Preserve event timing while replacing source-specific visual design.
  </vfx:direction>

  <mkt:direction>
    Preserve hook, proof, product visibility, and CTA relationships.
  </mkt:direction>

  <cpcs:exclusions>
    <cpcs:item>source performer identity</cpcs:item>
    <cpcs:item>source voice</cpcs:item>
    <cpcs:item>unlicensed logos</cpcs:item>
    <cpcs:item>exact copyrighted dialogue</cpcs:item>
  </cpcs:exclusions>

</cpcs:recreation-request>
```

The compiler should treat the XML as semantic instruction and the canonical JSON as authoritative numerical data.

---

## 32. Compiler Resolution Order

```text
studio defaults
    ↓
production profile
    ↓
sequence profile
    ↓
scene profile
    ↓
shot profile
    ↓
beat profile
    ↓
event or frame override
    ↓
human lock
```

Typed merge rules:

| Value type | Merge rule |
|---|---|
| scalar | more specific scope replaces unless locked |
| object | recursive typed merge |
| ordered timeline | merge by stable event ID, then sort by resolved time |
| curve | replace, scale, offset, or blend only when operation is explicit |
| constraint set | union, then detect contradictions |
| asset reference | replace only if rights and compatibility checks pass |
| lock | immutable to lower-authority stages |

A language model should not improvise merge behavior.

---

## 33. Provider Adapter Contract

Every target-model adapter should declare capabilities:

```json
{
  "adapter_id": "target_video_model_x",
  "supports": {
    "text_prompt": true,
    "reference_images": 4,
    "first_frame": true,
    "last_frame": true,
    "pose_video": false,
    "mask_video": false,
    "camera_trajectory": false,
    "audio_conditioning": false,
    "video_to_video": true
  },
  "limits": {
    "max_duration_s": 10,
    "supported_aspect_ratios": ["9:16", "16:9", "1:1"]
  }
}
```

The compiler then emits:

```text
request JSON
compiled prompt
reference assets
control media
unsupported-control report
postproduction plan
validation profile
```

---

## 34. RAG-Friendly Storage

### 34.1 Record types

A RAG corpus should contain:

```text
document records
methodology chunks
source records
Pegasus prompt records
schema records
observation records
canonical-score fragments
adapter capability records
validation results
failure cases
human corrections
```

### 34.2 Metadata

Recommended metadata:

```json
{
  "record_id": "cpcs.pegasus.ugc.product_reveal",
  "record_type": "method_chunk",
  "document_id": "CPCS-PEGASUS-RDC-2026-01",
  "heading_path": [
    "High-Fidelity UGC Recreation",
    "Pegasus UGC Passes",
    "Product interaction"
  ],
  "concepts": [
    "Pegasus",
    "UGC",
    "product visibility",
    "reference image prompting",
    "modular recreation"
  ],
  "evidence_status": "operational_synthesis",
  "as_of_date": "2026-07-18",
  "source_ids": ["TL-01", "TL-02", "TL-03"]
}
```

### 34.3 Retrieval rules

For a query such as “recreate the motion of an anime counterattack,” retrieve:

1. fight action graph;
2. Pegasus fight pass schema;
3. pose and optical-flow measurement guidance;
4. contact ambiguity policy;
5. fight transfer YAML;
6. adapter tier recommendation;
7. validation thresholds.

Do not retrieve only the text-prompt example.

---

## 35. Implementation Blueprint

### Phase 1 — Minimum viable semantic system

Deliverables:

- source manifest;
- Pegasus source-map pass;
- scenes and beats segmentation;
- camera/edit pass;
- UGC or fight-specific pass;
- JSONL normalization;
- canonical JSON draft;
- human review interface.

Expected result: strong semantic blueprint, moderate timing precision.

### Phase 2 — Frame-level measurement

Add:

- frame timestamps;
- shot detection;
- masks;
- pose;
- optical flow;
- face and gaze;
- audio alignment;
- event snapping.

Expected result: high temporal and screen-space precision.

### Phase 3 — Modular recreation compiler

Add:

- YAML transfer policy;
- XML envelope;
- merge engine;
- target capability registry;
- pose/mask/camera rendering;
- generated-video validation.

Expected result: repeatable generation packages.

### Phase 4 — Corpus and learning loop

Add:

- RAG corpus;
- reusable UGC and fight templates;
- failure-case retrieval;
- benchmark clips;
- acceptance dashboards;
- automatic regeneration decisions.

Expected result: system improves through explicit evidence rather than prompt drift.

---

## 36. Python SDK Pattern for Pegasus General Analysis

The following pattern follows the current Twelve Labs Python SDK concepts. Exact imports and symbols should be checked against the installed SDK version and current official documentation before execution.

```python
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from twelvelabs import TwelveLabs
from twelvelabs.types import (
    AnalyzePromptV2,
    SyncResponseFormat,
    VideoContext_AssetId,
)

API_KEY = os.environ["TWELVELABS_API_KEY"]
ASSET_ID = os.environ["TWELVELABS_ASSET_ID"]

client = TwelveLabs(api_key=API_KEY)

schema: dict[str, Any] = {
    "type": "object",
    "properties": {
        "analysis_scope": {"type": "string"},
        "ordered_beats": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "beat_id": {"type": "string"},
                    "approximate_start_s": {"type": "number"},
                    "approximate_end_s": {"type": "number"},
                    "observable_event": {"type": "string"},
                    "semantic_function": {"type": "string"},
                    "uncertainty": {"type": "string"},
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                },
                "required": [
                    "beat_id",
                    "approximate_start_s",
                    "approximate_end_s",
                    "observable_event",
                    "semantic_function",
                    "uncertainty",
                    "confidence",
                ],
            },
        },
    },
    "required": ["analysis_scope", "ordered_beats"],
}

prompt = """
Analyze the video as a reverse director. Return ordered, observable beats.
Separate visible events from semantic function. Do not invent hidden action.
Use stable entity labels. Report uncertainty when cuts, blur, occlusion, or
stylization prevent a confident interpretation.
""".strip()

response = client.analyze(
    model_name="pegasus1.5",
    video=VideoContext_AssetId(asset_id=ASSET_ID),
    prompt_v_2=AnalyzePromptV2(input_text=prompt),
    response_format=SyncResponseFormat(
        type="json_schema",
        json_schema=schema,
    ),
    temperature=0.1,
    max_tokens=8192,
)

if getattr(response, "finish_reason", None) == "length":
    raise RuntimeError("Pegasus response was truncated; reduce scope or increase output limit.")

payload = json.loads(response.data or "{}")
Draft202012Validator(schema).validate(payload)

Path("pegasus_pass.json").write_text(
    json.dumps(payload, indent=2),
    encoding="utf-8",
)
```

Verification:

```text
response parses as JSON
schema validation passes
finish_reason is not length
all beats have ordered times
all entities use stable IDs
uncertainty is non-empty for ambiguous events
```

---

## 37. Python Pattern for Segment Definitions

```python
from __future__ import annotations

import json
import os
import time

from twelvelabs import TwelveLabs
from twelvelabs.types import AsyncResponseFormat, VideoContext_AssetId

client = TwelveLabs(api_key=os.environ["TWELVELABS_API_KEY"])
asset_id = os.environ["TWELVELABS_ASSET_ID"]

segment_definitions = [
    {
        "id": "ugc_functions",
        "description": (
            "Detect continuous passages that perform a distinct UGC "
            "communication function. Do not force a category when evidence "
            "is insufficient."
        ),
        "fields": [
            {
                "name": "function",
                "type": "string",
                "description": "Primary communication function.",
                "enum": [
                    "hook",
                    "problem",
                    "product_introduction",
                    "demonstration",
                    "proof",
                    "objection_handling",
                    "benefit",
                    "brand_reveal",
                    "cta",
                    "other",
                ],
            },
            {
                "name": "observable_evidence",
                "type": "string",
                "description": "Visible or audible evidence supporting the label.",
            },
            {
                "name": "product_visible",
                "type": "boolean",
                "description": "Whether the relevant product is visibly present.",
            },
            {
                "name": "uncertainty",
                "type": "string",
                "description": "Ambiguity or missing evidence.",
            },
        ],
    }
]

task = client.analyze_async.tasks.create(
    video=VideoContext_AssetId(asset_id=asset_id),
    model_name="pegasus1.5",
    analysis_mode="time_based_metadata",
    response_format=AsyncResponseFormat(
        type="segment_definitions",
        segment_definitions=segment_definitions,
    ),
    temperature=0.1,
    max_tokens=32768,
)

while True:
    task = client.analyze_async.tasks.retrieve(task.task_id)
    if task.status == "ready":
        break
    if task.status == "failed":
        raise RuntimeError("Pegasus segmentation task failed")
    time.sleep(5)

result = json.loads(task.result.data or "[]")
print(json.dumps(result, indent=2))
```

Operational note: current paid segmentation billing considers the number of segment definitions. Prefer several focused runs only when the added information justifies the cost. [TL-05]

---

## 38. Failure Modes and Deterministic Responses

| Failure | Observable symptom | Response |
|---|---|---|
| Prompt-schema mismatch | output follows schema but not prompt | align them; schema has precedence |
| Truncated JSON | `finish_reason` is `length` or parsing fails | reduce clip/task scope or adjust output limit |
| Overloaded schema | missing or generic fields | split into related passes |
| Semantic timestamp drift | segment boundaries miss visible onset | snap to source frames and measured events |
| Actor identity swap | labels change during occlusion | use masks, tracking, and human correction |
| Anime pose failure | impossible joints or lost limbs | manual keyframes and contour anchors |
| Camera/object confusion | actor seems to move with background | separate background transform and actor track |
| False contact claim | model says “hit” but flash hides gap | use ambiguous contact class and reviewed policy |
| UGC becomes too polished | generated motion loses authenticity | enforce camera spectrum, gaze breaks, pauses, and continuity imperfections |
| Exact motion not reproduced | text model invents interpolation | escalate to pose video, rig, or video-to-video control |
| Source identity leaks | replacement resembles source performer | remove source texture/face/voice and use neutral control render |
| Data drift | fields change between passes | pin schema versions and stable IDs |

---

## 39. Verification Checklist

### Source and rights

- [ ] Source hash recorded.
- [ ] Rights and transformation basis documented.
- [ ] Identity, voice, brand, and dialogue replacement policy approved.
- [ ] Source clock and internal start time verified.

### Pegasus

- [ ] Pegasus version recorded.
- [ ] Analysis mode recorded.
- [ ] Prompt and schema aligned.
- [ ] `finish_reason` checked.
- [ ] Raw response preserved.
- [ ] Response parsed and validated client-side.
- [ ] Semantic timestamps retained before snapping.
- [ ] Uncertainty required for ambiguous events.

### Measurement lane

- [ ] Frame timestamps extracted.
- [ ] Shot cuts reviewed.
- [ ] Entity masks reviewed.
- [ ] Pose identity continuity reviewed.
- [ ] Optical flow generated for fast passages.
- [ ] Camera and object motion separated.
- [ ] Audio transients and dialogue aligned.
- [ ] Critical contact and reveal frames manually reviewed.

### Fusion

- [ ] Evidence classes preserved.
- [ ] Conflicting claims retained.
- [ ] Stable entity and event IDs used.
- [ ] Human locks applied to critical events.
- [ ] Canonical JSON passes schema validation.

### Recreation

- [ ] YAML transfer policy resolves without conflict.
- [ ] Unsupported controls reported by adapter.
- [ ] Dense controls rendered where required.
- [ ] Source identity and protected assets excluded.
- [ ] Generation package is reproducible.

### Validation

- [ ] Generated video re-extracted.
- [ ] Temporal, motion, camera, performance, and marketing metrics computed.
- [ ] Acceptance gates evaluated.
- [ ] Failures mapped to specific controls rather than handled by vague prompt expansion.

---

## 40. Conclusions

Pegasus is most powerful in a recreation pipeline when it is used neither as a generic captioner nor as a fictional motion-capture device. Its proper role is a **schema-constrained semantic reverse-director**.

For UGC, Pegasus can recover the communication graph: hook, problem, product introduction, demonstration, proof, benefit, objection handling, brand reveal, and CTA. It can explain how camera, speech, text, product interaction, and creator behavior support those functions. Measurements then recover reveal frames, gaze timing, product trajectories, caption rhythm, pauses, and handheld motion. The new video can preserve the structure while replacing the performer, voice, wording, product, brand, and setting.

For fight and anime action, Pegasus can recover the tactical and cinematic graph: approach, commitment, attack, defense, reversal, impact, recoil, and recovery. It can identify apparent camera purpose, editorial concealment, VFX, and emotional progression. Pose, masks, optical flow, source timing, contact inference, and human review recover the visible motion required for high-fidelity transfer. The new scene can preserve action causality, screen-space timing, Laban quality, FACS and gaze progression, camera grammar, and effect timing while replacing characters and surface design.

The decisive system property is not the presence of YAML, JSON, XML, or JSONL. It is the disciplined transfer of information across representations:

```text
video evidence
→ semantic and measured observations
→ typed uncertainty and provenance
→ canonical CPCS score
→ explicit replacement and retention policy
→ supported generation controls
→ re-extracted compliance evidence
```

High-fidelity recreation becomes practical when every layer has an owner, every event has a clock, every interpretation has provenance, every unsupported control is reported, and every generated result can be measured against the score that directed it.

---

# Appendix A — Recommended Project Structure

```text
pegasus_recreation_project/
├── source/
│   ├── source.mp4
│   ├── source_manifest.json
│   ├── frame_timestamps.json
│   └── audio.wav
├── pegasus/
│   ├── pass_00_source_map.json
│   ├── pass_01_scene_segments.json
│   ├── pass_02_beats.json
│   ├── pass_03_camera_edit.json
│   ├── pass_04_performance.json
│   ├── pass_05_actions.json
│   ├── pass_06_vfx_audio.json
│   ├── pass_07_contradictions.json
│   └── pegasus_observations.jsonl
├── vision/
│   ├── frames/
│   ├── masks/
│   ├── pose.jsonl
│   ├── face_gaze.jsonl
│   ├── optical_flow.jsonl
│   ├── camera_motion.jsonl
│   ├── contacts.jsonl
│   └── audio_events.jsonl
├── fusion/
│   ├── all_observations.jsonl
│   ├── conflicts.jsonl
│   ├── review_queue.jsonl
│   └── resolved_video_observation_graph.json
├── canonical/
│   ├── cpcs_score.json
│   └── cpcs_score.schema.json
├── authoring/
│   ├── transfer_policy.yaml
│   ├── director_overrides.yaml
│   └── semantic_envelope.xml
├── controls/
│   ├── pose_control.mp4
│   ├── mask_control.mp4
│   ├── depth_control.mp4
│   ├── camera_path.json
│   ├── keyframes/
│   └── storyboard/
├── adapters/
│   ├── capability_profile.json
│   ├── compiled_prompt.txt
│   ├── target_request.json
│   └── unsupported_controls.json
└── validation/
    ├── generated_observations.jsonl
    ├── comparison_report.json
    └── overlay_review.mp4
```

---

# Appendix B — Minimal JSONL Parser and Validator

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def read_jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL at {path}:{line_number}: {exc.msg}"
                ) from exc
            if not isinstance(value, dict):
                raise ValueError(
                    f"Expected object at {path}:{line_number}; got {type(value).__name__}"
                )
            yield line_number, value


def validate_record(record: dict[str, Any], *, path: Path, line: int) -> None:
    required = {
        "record_id",
        "source_id",
        "layer",
        "claim",
        "evidence_class",
        "extractor",
    }
    missing = sorted(required - record.keys())
    if missing:
        raise ValueError(f"Missing {missing} at {path}:{line}")


seen: set[str] = set()
input_path = Path("all_observations.jsonl")

for line_number, record in read_jsonl(input_path):
    validate_record(record, path=input_path, line=line_number)
    record_id = str(record["record_id"])
    if record_id in seen:
        raise ValueError(f"Duplicate record_id {record_id!r} at line {line_number}")
    seen.add(record_id)

print(f"validated_records={len(seen)}")
```

---

# Appendix C — Pegasus Prompt Template for UGC

```text
You are analyzing an authorized reference video for modular recreation with a
new performer, product, wording, setting, and brand.

Your task is semantic extraction, not motion capture.

1. Identify ordered communication functions supported by visible or audible
   evidence: hook, problem, product introduction, demonstration, proof,
   objection handling, benefit, brand reveal, CTA, or other.
2. Use stable entity IDs.
3. Separate observable events from inferred marketing function.
4. Report approximate source times.
5. Identify direct lens address, gaze breaks, product interaction, creator
   credibility cues, captions, cut purposes, and camera authenticity cues.
6. Do not infer conversion success.
7. Do not copy or recommend copying identity, voice, exact dialogue, branding,
   or private information.
8. Report uncertainty where evidence is incomplete.
9. Return only data conforming to the supplied JSON Schema.
```

---

# Appendix D — Pegasus Prompt Template for Fight and Anime Action

```text
Analyze this authorized fictional fight reference as a reverse director.

1. Divide the clip into ordered tactical passages and atomic visible beats.
2. Use stable IDs for each fighter, object, and effect.
3. Describe only visible action. Do not invent movement hidden by cuts,
   occlusion, blur, impact flashes, or stylization.
4. For every beat, identify initiator, target, visible action, tactical
   function, camera function, edit function, VFX, audio accent, and uncertainty.
5. Distinguish apparent contact, occluded contact, and staged near-contact.
6. Identify preparation, step or plant, pivot, extension, dodge or defense,
   impact accent, recoil, fall, and recovery when visible.
7. Interpret movement through Laban Weight, Time, Space, and Flow, but list the
   visible evidence supporting each interpretation.
8. Describe facial and gaze changes without claiming access to private mental
   state.
9. Identify held frames, repeated frames, smear drawings, speed lines, energy
   trails, flashes, dust, debris, shake, and time warps.
10. Return only data conforming to the supplied JSON Schema.
```

---

# Appendix E — Source and Research References

## Twelve Labs official documentation

- **[TL-01] Pegasus model overview.** Twelve Labs. “Pegasus.” Current version and supported analysis modes, video segmentation, multimodal prompting, and direct input methods. https://docs.twelvelabs.io/docs/concepts/models/pegasus
- **[TL-02] Analyze videos guide.** Twelve Labs. Multimodal analysis, assets, sync/async processing, reference-image prompts, response controls, and operational workflow. https://docs.twelvelabs.io/docs/guides/analyze-videos
- **[TL-03] Structured responses.** Twelve Labs. JSON Schema output, prompt-schema precedence, client-side validation, streaming, truncation handling, and schema constraints. https://docs.twelvelabs.io/docs/guides/analyze-videos/structured-responses
- **[TL-04] Sync analysis API reference.** Twelve Labs. Pegasus 1.5 clipping, internal start time, minimum clip duration, output limits, and structured prompts. https://docs.twelvelabs.io/api-reference/analyze-videos/analyze
- **[TL-05] Release notes.** Twelve Labs. Pegasus 1.5 SDK support, context-window changes, response limits, and segmentation billing updates as of May 2026. https://docs.twelvelabs.io/docs/get-started/release-notes
- **[TL-06] Batch analysis API reference.** Twelve Labs. Pegasus 1.5 batch modes and limits. https://docs.twelvelabs.io/api-reference/analyze-videos/batch-analysis/create-batch
- **[TL-07] Segment videos guide.** Twelve Labs. Custom segment definitions, typed fields, time-based metadata, and parsing results. https://docs.twelvelabs.io/v1.3/docs/guides/segment-videos
- **[TL-08] Segment videos quickstart.** Twelve Labs. Python and Node.js workflow for asynchronous segmentation. https://docs.twelvelabs.io/docs/get-started/quickstart/segment-videos

## Primary computer-vision and animation research

- **[CV-01] SAM 2.** Ravi, N. et al. “SAM 2: Segment Anything in Images and Videos.” 2024. https://arxiv.org/abs/2408.00714
- **[CV-02] OpenPose.** Cao, Z. et al. “OpenPose: Realtime Multi-Person 2D Pose Estimation using Part Affinity Fields.” 2018. https://arxiv.org/abs/1812.08008
- **[CV-03] RAFT.** Teed, Z. and Deng, J. “RAFT: Recurrent All-Pairs Field Transforms for Optical Flow.” 2020. https://arxiv.org/abs/2003.12039
- **[CV-04] EMOCA.** Danecek, R., Black, M. J., and Bolkart, T. “EMOCA: Emotion Driven Monocular Face Capture and Animation.” 2022. https://arxiv.org/abs/2204.11312
- **[VG-01] MotionCtrl.** Wang, Z. et al. “MotionCtrl: A Unified and Flexible Motion Controller for Video Generation.” 2023. https://arxiv.org/abs/2312.03641
- **[AN-01] DeepMimic.** Peng, X. B. et al. “DeepMimic: Example-Guided Deep Reinforcement Learning of Physics-Based Character Skills.” 2018. https://arxiv.org/abs/1804.02717

## Standards and tooling

- **FFprobe documentation.** FFmpeg Project. Machine-readable media, stream, packet, and frame inspection. https://ffmpeg.org/ffprobe.html
- **JSON standard.** Bray, T. “The JavaScript Object Notation (JSON) Data Interchange Format.” RFC 8259. https://www.rfc-editor.org/rfc/rfc8259
- **JSON Schema Draft 2020-12.** https://json-schema.org/draft/2020-12
- **YAML 1.2.2 specification.** https://yaml.org/spec/1.2.2/
- **XML 1.0.** World Wide Web Consortium. https://www.w3.org/TR/xml/
- **Namespaces in XML.** World Wide Web Consortium. https://www.w3.org/TR/xml-names/

---

## Document Use Note

This document describes an engineering workflow for authorized analysis and transformation. High-fidelity structural recreation does not require unauthorized copying of a person’s identity, voice, private information, exact copyrighted dialogue, brand assets, or protected character design. The recommended architecture deliberately separates transferable structure from replaceable surface identity.
