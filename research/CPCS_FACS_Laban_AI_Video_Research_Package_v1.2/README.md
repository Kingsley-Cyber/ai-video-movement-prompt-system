# CPCS FACS–Laban AI Video Research Package

**Version:** 1.2  
**Document:** *Cinematic Performance Control for AI Video Generation*  
**Framework:** Cinematic Performance Control Score (CPCS)  
**Reference records:** 90  
**RAG records:** 178  
**Literature and provider-documentation cutoff:** 2026-07-18

This package consolidates the CPCS research paper, its RAG corpus, reference indexes, schemas, compiler-oriented examples, and a new **video-to-CPCS reverse-analysis layer**. The reverse layer converts an authorized reference video into an evidence-preserving description of performance, action, camera, editing, sound, VFX, and marketing structure.

The package does not assume that a multimodal model is a frame-accurate measurement instrument. Its central workflow is:

```text
reference video
  → source-clock manifest and analysis derivatives
  → semantic hypotheses + measured computer-vision/audio tracks
  → Video Observation Graph (VOG)
  → reviewed, identity-independent CPCS projection
  → target-model control package
  → generated video
  → re-extraction and compliance comparison
```

## What the reverse compiler extracts

| Source-video layer | Extraction method | CPCS translation |
|---|---|---|
| Narrative, scene, and beat purpose | multimodal semantic passes over the full video and shot clips | objectives, tactics, subtext, action beats, communication functions |
| Face and gaze | tracked face crops, landmarks, head pose, gaze, AU candidates | time-indexed FACS events, gaze targets, blink and head tracks |
| Body and movement quality | 2D/3D pose, root motion, optical flow, contact inference, Laban interpretation | action atoms, phases, trajectories, contacts, Effort/Shape/Space controls |
| Fight or stunt construction | actor tracks, support changes, target distance, near-contact, reaction and impact evidence | causal action graph: approach → setup → strike-like action → defense → recoil → fall/recovery |
| Camera and edit | shot detection, background motion, subject scale, vanishing-point and track analysis | shot scale, angle, camera path, cut/reaction/slow-motion/impact-frame events |
| Audio and pace | transcript, word timing, pauses, breath, transient and beat analysis | dialogue cadence, silence, impact, music, caption, and edit-synchronization tracks |
| VFX/anime presentation | residual motion, overlays, particles, flashes, shake and smear detection | speed lines, trails, dust, shake, flash, time-warp, smear, compositor events |
| UGC and marketing structure | lens-address, hook/proof/objection/CTA segmentation, product and caption visibility | persuasive beat graph, visibility constraints, variant plan, evaluation metrics |

The semantic lane answers *what a passage appears to mean*. The measurement lane answers *what changed, where, and when*. The canonical graph keeps both, including disagreement, so the generation compiler can use strong evidence without presenting interpretation as fact.

## Core research scope

The main paper integrates:

- FACS Action Units and temporal facial events;
- valence–arousal–dominance/control trajectories;
- Laban Body, Effort, Shape, and Space;
- full-body actions, locomotion, local phase, contact, balance, and dynamics;
- fight/stunt action coding and causal choreography graphs;
- camera, lens, framing, editorial, audio, VFX/anime, and marketing controls;
- YAML, JSON, XML, and JSONL authoring/compilation roles;
- typed style inheritance and scope precedence;
- model-capability negotiation and controlled degradation;
- reference-video distillation and reverse directorial compilation;
- RAG, provenance, contradiction handling, and round-trip verification.

## New in version 1.2

Version 1.2 adds Section 30 and Appendix H to the paper, plus a standalone implementation guide and executable artifacts for reference-video analysis. Important concepts include:

- a temporal pyramid rather than one universal sampling rate;
- `measured`, `detected`, `inferred`, `interpreted`, and `authored` evidence classes;
- separation of actor motion from camera motion;
- frame/timebase normalization using source presentation timestamps;
- semantic passes for Gemini and Twelve Labs Pegasus;
- retrieval/clustering roles for Marengo or other multimodal embeddings;
- FACS, gaze, pose, optical flow, 3D reconstruction, action phase, contact, Laban, camera/edit, audio, VFX, UGC, and marketing extraction;
- fight-scene and creator/UGC worked examples;
- a canonical Video Observation Graph with confidence, provenance, and contradictions;
- reverse compilation into CPCS and target-specific generation controls;
- closed-loop re-extraction of generated results.

## Directory map

```text
CPCS_FACS_Laban_AI_Video_Research_Package_v1.2/
├── README.md
├── requirements.txt
├── SHA256SUMS.txt
├── paper/
├── docs/
├── rag/
├── schemas/
├── scripts/
├── prompts/
├── configs/
├── examples/
├── references/
├── manifests/
└── tests/
```

See `docs/PACKAGE_STRUCTURE.md` for the complete artifact inventory.

## Recommended reading order

1. `paper/CPCS_FACS_Laban_AI_Video_Directorial_Control_Research_Paper.md`
2. Section 30 of that paper: **Reference-Video Distillation and Reverse Directorial Compilation**
3. `docs/VIDEO_TO_CPCS_EXTRACTION_GUIDE.md`
4. `configs/video_to_cpcs_pipeline.yaml`
5. `schemas/CPCS_Video_Observation_Record_Schema.json`
6. `schemas/CPCS_Video_Observation_Graph_Schema.json`
7. the fight and UGC examples in `examples/video_to_cpcs/`

## Runtime requirements

Python utilities require Python 3.10 or later, PyYAML, and jsonschema. Media preprocessing additionally requires `ffmpeg` and `ffprobe` on `PATH`.

```bash
python -m pip install -r requirements.txt
ffmpeg -version
ffprobe -version
```

Verification checkpoint: both version commands must exit successfully before running the media extractor.

## Rebuild the RAG corpus

Run from the package root:

```bash
python scripts/build_cpcs_rag.py
```

Expected result:

```text
paper_chunks: 87
source_records: 90
total_records: 178
```

The script parses the paper, writes the JSONL and record schema, validates every JSONL line against JSON Schema Draft 2020-12, verifies citation resolution, and updates `manifests/CPCS_RAG_Build_Manifest.json`.

## Rebuild the reference indexes

```bash
python scripts/build_reference_indexes.py
```

Expected result: 90 stable source records and four regenerated files under `references/`.

## Choose an extraction record shape

For a comprehensive project dossier, use the all-in-one command with `probe`, `prepare`, `init-record`, and `validate` subcommands:

```bash
python scripts/video_to_cpcs_reference_pipeline.py --help
```

For distributed evidence fusion and RAG, use the observation-record and Video Observation Graph scripts described below. Both paths preserve source hashes and timing; they serve different storage and workflow needs.

## Normalize a source video for the observation-graph path

Use only media for which the intended analysis and reuse are authorized.

```bash
python scripts/extract_video_manifest.py /path/to/reference.mp4 \
  --output-dir work/reference_001 \
  --analysis-fps 24 \
  --semantic-fps 1 \
  --scene-threshold 0.35
```

Verification checkpoints:

```text
work/reference_001/source_manifest.json
work/reference_001/source_probe.json
work/reference_001/analysis_proxy.mp4
work/reference_001/semantic_frames/
work/reference_001/shot_candidates.json
```

When the source contains audio, the extractor also writes `audio_16k_mono.wav`. The extractor is intentionally local: it does not upload media or invoke a hosted model.

## Merge observation records

Provider outputs and local extractor outputs must first be normalized to `CPCS_Video_Observation_Record_Schema.json`.

```bash
python scripts/merge_video_observations.py \
  --manifest work/reference_001/source_manifest.json \
  --inputs work/reference_001/observations/*.jsonl \
  --output work/reference_001/video_observation_graph.json \
  --conflicts work/reference_001/conflicts.json
```

The merge process rejects source-ID/hash mismatches, preserves provenance, deduplicates exact records, and reports contradictions instead of silently averaging incompatible evidence.

## Validate the canonical graph

```bash
python scripts/validate_video_observation_graph.py \
  work/reference_001/video_observation_graph.json \
  --schema schemas/CPCS_Video_Observation_Graph_Schema.json \
  --record-schema schemas/CPCS_Video_Observation_Record_Schema.json
```

Acceptance requires both `schema_valid: true` and `semantic_valid: true`. Review warnings separately; a schema-valid graph can still contain low-confidence or contested claims.

## Provider prompt assets

The provider files are **templates**, not executable API clients. Provider contracts change, so each run must pin and log the model name, API version, documentation date, request parameters, prompt digest, and raw response digest.

- `prompts/gemini_video_to_cpcs_system.xml`
- `prompts/gemini_video_to_cpcs_request.json`
- `prompts/twelvelabs_pegasus_segment_definitions.json`
- `prompts/video_extraction_plan.yaml`

Semantic models should propose sequence, shot, beat, action, UGC, VFX, and directorial interpretations. Dense timing and movement claims should be checked against source-clock frames, pose/face tracks, optical flow, audio transients, and other measurable evidence.

## Rights and transfer policy

The package supports structural analysis and controlled transformation, not identity cloning or automatic permission. Before reverse compilation, classify fields as:

- **retain:** authorized timing, causal order, movement quality, camera grammar;
- **parameterize:** tolerances, scale, intensity, visibility, pace;
- **replace:** identity, voice, dialogue, logos, wardrobe, setting, product;
- **exclude:** private data, disallowed biometric identifiers, unsafe stunt instruction, and unlicensed assets.

Fight examples are framed as fictional choreography/previsualization. They are not real-world combat instruction. Physical production requires qualified stunt and safety review.

## Integrity

`SHA256SUMS.txt` covers every packaged file except itself. Verify from the package root:

```bash
sha256sum --check SHA256SUMS.txt
```

The package validation report is stored at `manifests/PACKAGE_VALIDATION_REPORT.json`.
