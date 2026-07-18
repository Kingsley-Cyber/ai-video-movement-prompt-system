---
title: "From Action Units to Action Beats"
subtitle: "A Directorial Control, Reference-Video Distillation, and Compilation Framework for AI Video Generation Using FACS, Dimensional Affect, Laban Movement Analysis, Action Coding, Camera, VFX, Marketing, YAML, JSON, and XML"
short_title: "CPCS Research Paper"
document_id: "CPCS-RP-2026-01"
version: "1.2"
date: "2026-07-18"
literature_cutoff: "2026-07-18"
status: "Research synthesis and testable systems proposal"
author: "OpenAI"
language: "en"
citation_style: "author-year with stable source identifiers"
framework_name: "Cinematic Performance Control Score"
framework_acronym: "CPCS"
rag_ready: true
rag_chunking:
  preferred_strategy: "heading-aware semantic chunking"
  target_chunk_tokens: 650
  maximum_chunk_tokens: 950
  overlap_tokens: 100
  preserve_code_blocks: true
  preserve_tables: true
  retain_heading_path: true
  exclude_sections:
    - "Full Reference List"
    - "Document Change Log"
knowledge_domains:
  - facial_action_coding
  - affective_computing
  - laban_movement_analysis
  - character_animation
  - human_motion_generation
  - controllable_video_generation
  - cinematography
  - retrieval_augmented_generation
  - structured_prompt_languages
  - schema_compilation
  - style_inheritance
  - visual_effects_direction
  - marketing_creative_control
  - reference_video_distillation
  - multimodal_video_understanding
  - reverse_directorial_compilation
  - video_observation_graphs
keywords:
  - FACS
  - action units
  - valence arousal dominance
  - VAC
  - VAD
  - Laban Movement Analysis
  - Labanotation
  - motion phase
  - contact constraints
  - physics-based animation
  - text-to-video
  - pose-to-video
  - storyboard control
  - performance direction
  - RAG
  - YAML
  - JSON
  - XML
  - JSON Schema
  - style inheritance
  - typed merge
  - compiler intermediate representation
  - VFX control
  - marketing creative control
  - reference-video distillation
  - reverse directorial compilation
  - video observation graph
  - shot and beat extraction
  - multimodal video analysis
  - round-trip verification
license_note: "This document summarizes published research and proposes a new integration. It does not reproduce proprietary FACS training materials."
---

<!-- RAG_DOC_SUMMARY: This paper proposes the Cinematic Performance Control Score (CPCS), a model-agnostic, time-indexed representation and compiler architecture that translates screenplay intent into affect, FACS, Laban, body action, combat choreography, skeletal, phase, contact, physics, interaction, camera, VFX, audio, and marketing controls. It formalizes YAML authoring, canonical JSON, XML director envelopes, style inheritance, typed merge precedence, model capability negotiation, target-package compilation, and verification for AI video generation. It also defines reference-video distillation: a multi-resolution, evidence-aware process that extracts shots, beats, performance, action, camera, edit, audio, VFX, and marketing grammar into a canonical Video Observation Graph and reverse-compiles it into identity-independent CPCS controls. Established systems, current API examples, and proposed components are explicitly distinguished. -->

<a id="cpcs-abstract"></a>
# From Action Units to Action Beats

## Abstract

Text-to-video systems are increasingly capable of producing visually persuasive shots, yet natural-language prompting remains an imprecise interface for directing human performance. A phrase such as “she walks toward him while hiding her fear” specifies a narrative intention but leaves unresolved the timing, distribution, and coordination of facial activity, gaze, posture, gait, weight transfer, interpersonal distance, camera motion, and physical contact. This paper synthesizes research from facial behavior measurement, affective science, movement analysis, character animation, human-motion generation, and controllable video synthesis to define a more explicit directorial interface.

The paper distinguishes four kinds of representation that are often conflated. The **Facial Action Coding System (FACS)** describes visible facial actions through anatomically grounded Action Units and can be extended into time-varying onset, apex, offset, intensity, and asymmetry curves. **Valence–arousal–dominance**, here also discussed under the user-facing alias **valence–arousal–control (VAC)**, describes the global affective state or trajectory but does not uniquely determine a facial expression or body movement. **Laban Movement Analysis (LMA)** describes the qualitative organization of bodily action—especially Effort, Shape, Body, and Space—but does not by itself specify exact joint trajectories or physical forces. **Kinematic, phase, contact, interaction, and dynamic representations** specify how an intended action is realized over time.

Building on these distinctions, this paper proposes the **Cinematic Performance Control Score (CPCS)**: a hierarchical, time-indexed, machine-readable control specification that translates a screenplay, storyboard, or director’s note into synchronized tracks for narrative beats, dimensional affect, facial Action Units, gaze, Laban qualities, skeletal motion, local motion phase, contacts, dynamics, actor-to-actor relations, camera trajectory, appearance, and sound. CPCS is not presented as an existing scientific standard. It is a systems proposal designed to be falsifiable, implementable, and compatible with diffusion transformers, latent video diffusion, pose-to-video systems, neural character controllers, physics simulators, and render-conditioned pipelines.

The central claim is that directorial control should be treated as a **compilation problem rather than a prompt-writing problem**. Natural language should remain the high-level screenplay and intention layer. A retrieval-augmented compiler should then ground that language in evidence-labeled performance templates, convert it into a structured score, generate or retrieve physically plausible motion, project the motion into control channels, synthesize the shot, and verify the result against the original score. This architecture permits explicit revision: a director can change the apex of a brow action, the force quality of a step, the exact frame of fist contact, or the camera’s six-degree-of-freedom path without rewriting an ambiguous prose prompt.

The expanded framework also distinguishes authoring syntax from model conditioning. YAML is assigned to human-readable project, style, and shot authoring; fully resolved JSON serves as the canonical intermediate representation and API boundary; XML serves as an optional ordered director and screenplay envelope with namespaced FACS, Laban, camera, VFX, and marketing vocabularies; and JSONL carries retrieval, compiler, evaluation, and experiment records. The paper defines a domain-separated style cascade, authority-aware merge precedence from project through frame or event, typed operations for scalars, keyed entities, constraints, and temporal tracks, and explicit combinations such as YAML importing measured JSON tracks or XML referencing a content-addressed canonical JSON score. It further specifies capability negotiation so that each control is reported as native, approximated, baked into a reference, compressed to text, applied in post, retained only for evaluation, or rejected as unsupported.

The framework is extended in the reverse direction through **reference-video distillation and reverse directorial compilation**. Instead of treating a known video as an opaque style reference, the system analyzes it as a layered execution trace. A temporal pyramid combines media forensics, shot and scene detection, multimodal semantic analysis, facial and gaze estimation, pose and 3D reconstruction, optical flow, camera disentanglement, speech and audio analysis, action/contact inference, and editorial interpretation. All claims are stored as measured, detected, inferred, interpreted, or authored evidence with timestamps, confidence, provenance, and contradictions. The resulting Video Observation Graph can be normalized away from performer identity and protected surface details, projected into CPCS, and used to generate new fight choreography, UGC communication structures, or cinematic sequences while preserving only the authorized timing, causal, motion-quality, camera, and marketing grammar.

The paper provides a formal representation, conditioning strategies, a RAG-oriented knowledge architecture, worked examples for dialogue, locomotion, and combat, and an evaluation protocol that separates visual quality from compliance, temporal accuracy, physical plausibility, affective legibility, identity preservation, and cinematic effectiveness. It concludes that FACS, dimensional affect, and Laban should not be collapsed into one universal code. Their value lies in a layered control stack: affect expresses the character’s internal trajectory; FACS and gaze specify facial realization; Laban specifies bodily quality; phase, kinematics, contact, and physics specify executable motion; and camera and editing specify how that performance becomes a shot.

**Keywords:** reference-video distillation; reverse directorial compilation; video observation graph; multimodal video understanding; shot detection; action segmentation; optical flow; FACS; Action Units; valence; arousal; dominance; VAC; Laban Movement Analysis; Labanotation; body action coding; combat choreography; motion phase; contact; physics-based animation; controllable video generation; text-to-video; pose-to-video; cinematic direction; VFX; marketing control; YAML; JSON; XML; JSON Schema; style inheritance; typed merge; compiler intermediate representation; RAG.

---

<!-- RAG_CHUNK id="cpcs.00" title="Evidence and terminology legend" concepts="evidence labels, terminology, VAC, VAD, CPCS" -->
<a id="cpcs-evidence-legend"></a>
## Evidence and Terminology Legend

This document uses five labels to prevent established research from being confused with proposed engineering choices.

| Label | Meaning |
|---|---|
| **[ESTABLISHED]** | A published theory, coding system, representation, or method supported by the cited literature. |
| **[EMERGING]** | A recent research direction, benchmark, preprint, or conference contribution whose generality is not yet settled. |
| **[PROPOSED]** | A component introduced in this paper as part of CPCS. It is not an accepted scientific standard. |
| **[OPERATIONALIZATION]** | A computable proxy proposed for a qualitative construct. It must be empirically calibrated and should not be treated as a definition of that construct. |
| **[CAUTION]** | A limitation, ambiguity, population dependency, or misuse risk. |

The term **VAC** is used in some creative and technical discussions to mean **valence–arousal–control**. Affective-science literature more commonly uses **VAD**—valence, arousal, dominance—or **PAD**—pleasure, arousal, dominance. In this paper, VAC is treated as a user-interface alias for VAD when “control” means the character’s perceived power, agency, or dominance. It is not the same as model controllability, confidence, or guidance strength.

The word **FACS** refers only to the Facial Action Coding System. The acronym **BAP** is ambiguous in the literature: it can refer to the psychological **Body Action and Posture coding system** or to MPEG-4 **Body Animation Parameters**. This paper always writes the full term at first use and avoids treating the two as related standards.

The terms **Authoring Source Layer (ASL)**, **Canonical Intermediate Representation (CIR)**, **Target Execution Package (TEP)**, and **Verification Evidence Record (VER)** are CPCS engineering terms introduced in this paper. YAML, JSON, XML, and JSONL are treated as serializations or envelopes. They become directorial controls only through a documented interpreter, compiler, native model input, or workflow mapping.

---

<!-- RAG_CHUNK id="cpcs.01" title="Executive thesis" concepts="directorial control, prompt compilation, structured score" -->
<a id="cpcs-executive-thesis"></a>
## Executive Thesis

A movie director does not ordinarily direct an actor by naming pixels. The director communicates objectives, relationships, stakes, rhythm, subtext, blocking, and selected physical details. The actor, choreographer, stunt team, cinematographer, editor, and animation department convert those intentions into coordinated behavior. Contemporary text-to-video prompting compresses all of those roles into one underspecified sentence. The resulting model must guess not only what the scene looks like, but also what each character wants, how the emotion changes, which body parts initiate the action, when contacts occur, how momentum propagates, and how the camera observes the event.

The proposed remedy is not merely a longer prompt. It is a hierarchy of representations, each answering a different question:

1. **Narrative and directorial semantics:** What is happening, why is it happening, and what should the audience understand?
2. **Affective state and trajectory:** What is the character experiencing in terms of valence, arousal, and perceived control or dominance?
3. **Visible performance organization:** Which facial actions, gaze behaviors, postures, and movement qualities express the intention?
4. **Motion realization:** What are the trajectories, phases, contacts, dynamics, and interaction constraints that make the behavior executable and human-like?
5. **Cinematic presentation:** Where is the camera, how does it move, what is in focus, and how are shot duration and editing synchronized with performance beats?
6. **Generative realization:** Which control tokens, maps, latent conditions, adapters, simulators, or render passes should drive the video model?
7. **Verification:** Did the generated result follow the score, remain physically plausible, preserve identity, and communicate the intended beat?

FACS, VAD/VAC, Laban, motion phase, and camera pose are therefore not competing solutions. They occupy different levels of a directorial stack. The principal systems contribution of this paper is to define how these levels can be synchronized on one timebase and compiled into conditions that current and future video generators can consume.

---

<!-- RAG_CHUNK id="cpcs.02" title="Contributions" concepts="research synthesis, CPCS, RAG, evaluation" -->
<a id="cpcs-contributions"></a>
## Contributions of This Paper

This paper makes seven contributions.

**First, it establishes a clean conceptual separation between affect, expression, movement quality, motion mechanics, and cinematography.** Valence–arousal does not specify a unique expression; FACS does not encode a complete emotional interpretation; Laban does not directly provide joint rotations; and a skeletal pose sequence does not by itself guarantee weight, contact, or dramatic meaning.

**Second, it proposes the Cinematic Performance Control Score.** CPCS is a synchronized collection of heterogeneous tracks rather than a single flat vector. It is designed to preserve both the director’s high-level language and the low-level measurable constraints needed by a generator.

**Third, it defines a directorial compiler architecture.** The pipeline moves from script and storyboard to retrieval, symbolic planning, motion generation, physical refinement, control-channel rendering, video synthesis, and automated plus human verification.

**Fourth, it defines a RAG-friendly knowledge model.** The model stores concept cards, movement atoms, performance templates, shot templates, calibration profiles, source provenance, and failure cases. Retrieval is constrained by body part, action, affect, Laban qualities, contact structure, camera grammar, duration, evidence level, and licensing.

**Fifth, it proposes an evaluation matrix that separates visual quality from control compliance.** The evaluation includes facial Action Unit tracking, affect-trajectory agreement, Laban-quality agreement, pose error, contact timing, foot skating, collision, center-of-mass support, camera trajectory, temporal compositionality, identity consistency, and director judgments.

**Sixth, it provides concrete worked scores.** These examples show how a line of directorial language can become a synchronized control plan for a dialogue close-up, an emotionally styled walk, and a two-person fight beat.

**Seventh, it defines a reverse compiler from observed video to CPCS.** The proposed reference-video distillation pipeline fuses frame-accurate media and vision measurements with multimodal semantic hypotheses, preserves evidence class and uncertainty, constructs a canonical Video Observation Graph, and converts reusable timing, performance, choreography, cinematography, VFX, audio, and marketing structure into identity-independent controls and round-trip tests.

---

<!-- RAG_EXCLUDE_START -->
<a id="cpcs-toc"></a>
## Table of Contents

- **Foundations:** [1. Research Questions, Scope, and Method](#cpcs-research-questions) · [2. Why Prompt-Only Direction Is Insufficient](#cpcs-prompt-limits) · [3. Layered Representation](#cpcs-layered-principle) · [4. FACS](#cpcs-facs) · [5. Dimensional Affect](#cpcs-affect) · [6. Body Action and Posture Coding](#cpcs-body-coding) · [7. Laban Movement Analysis](#cpcs-laban) · [8. Integration Boundaries](#cpcs-facs-laban-boundary)
- **Motion and formalism:** [9. Motion-Realization Stack](#cpcs-motion-realization) · [10. Walking and Running](#cpcs-locomotion) · [11. Fighting and Interaction](#cpcs-fighting) · [12. CPCS Formalism](#cpcs-formalism)
- **System architecture:** [13. Directorial Compiler](#cpcs-compiler) · [14. Video-Model Conditioning](#cpcs-conditioning) · [15. Training and Inference Objectives](#cpcs-losses) · [16. Data and Calibration](#cpcs-data) · [17. RAG](#cpcs-rag) · [18. Machine-Readable Schema](#cpcs-schema)
- **Structured compilation:** [19. Structured Prompt Languages, Style Inheritance, and Directorial Compilation](#cpcs-structured-prompting)
- **Storyboarding and examples:** [20. Executable Storyboards](#cpcs-storyboard) · [21. Concealed-Fear Dialogue](#cpcs-example-dialogue) · [22. Expressive Walk](#cpcs-example-walk) · [23. Controlled Fight Beat](#cpcs-example-fight)
- **Testing and governance:** [24. Evaluation](#cpcs-evaluation) · [25. Experimental Program](#cpcs-experiments) · [26. Failure Modes](#cpcs-failures) · [27. Ethics and Rights](#cpcs-ethics) · [28. Limitations](#cpcs-limitations) · [29. Research Agenda](#cpcs-future)
- **Reverse compilation:** [30. Reference-Video Distillation and Reverse Directorial Compilation](#cpcs-video-distillation) · [31. Conclusion](#cpcs-conclusion)
- **Appendices:** [A. Glossary](#cpcs-glossary) · [B. Directorial Crosswalk](#cpcs-directorial-crosswalk) · [C. Authoring Template](#cpcs-authoring-template) · [D. Compilation and Verification](#cpcs-compilation-protocol) · [E. RAG Protocol](#cpcs-rag-protocol) · [F. Evidence Map](#cpcs-evidence-map) · [G. Cross-Format Compiler Reference](#cpcs-cross-format-reference) · [H. Video-to-CPCS Operational Reference](#cpcs-video-extraction-reference) · [Full Reference List](#cpcs-references)

<!-- RAG_EXCLUDE_END -->

<!-- RAG_CHUNK id="cpcs.03" title="Research questions and scope" concepts="research questions, scope, methodology" -->
<a id="cpcs-research-questions"></a>
# 1. Research Questions, Scope, and Method

## 1.1 Research Questions

The paper addresses the following questions:

**RQ1.** What aspects of facial and bodily performance can be represented using established descriptive systems such as FACS, dimensional affect, Body Action and Posture coding, and Laban Movement Analysis?

**RQ2.** What additional representations are required to turn those descriptions into smooth, physically plausible, temporally precise movement for walking, running, fighting, dialogue, and interaction?

**RQ3.** How can these heterogeneous representations be synchronized into a control score that behaves more like a director’s, choreographer’s, and cinematographer’s plan than a conventional text prompt?

**RQ4.** How can such a score condition text-to-video, image-to-video, pose-to-video, motion-diffusion, and physics-based systems without assuming one proprietary model architecture?

**RQ5.** How should a retrieval-augmented system store and retrieve movement knowledge while preserving source provenance, uncertainty, performer-specific calibration, and the distinction between scientific evidence and creative convention?

**RQ6.** How can compliance be evaluated independently from photorealism and general video quality?

**RQ7.** How should YAML, JSON, XML, and JSONL be assigned distinct authoring, interchange, canonical, adapter, and retrieval roles, and how should they be combined without creating ambiguous sources of truth?

**RQ8.** How should style inheritance, project-to-frame merge precedence, VFX/anime enhancement, and marketing requirements compile into model inputs and postproduction artifacts while preserving provenance and exposing unsupported controls?

**RQ9.** How can a known reference video be decomposed into a confidence- and provenance-aware observation graph, normalized into identity-independent directorial grammar, reverse-compiled into CPCS, and validated through round-trip re-extraction?

**RQ10.** How can a reverse compiler preserve reusable timing, relational, movement-quality, cinematographic, editorial, auditory, and persuasive structure while explicitly replacing or excluding identity, voice, private data, unlicensed assets, and source-specific surface expression?

## 1.2 Scope

The primary scope is generated video containing one or more human or human-like performers. The proposed framework is applicable to realistic live-action synthesis, stylized animation, digital doubles, avatars, previsualization, virtual production, game cinematics, and embodied agents. It is not restricted to a specific output model, rig, skeleton, body topology, or rendering style.

The paper emphasizes expressive and cinematic control rather than clinical diagnosis. FACS, affect dimensions, gait measures, and body movement descriptors must not be used to infer a person’s private mental state with certainty. A generated performance score specifies an intended portrayal; it does not establish that the same visible behavior has a universal psychological meaning in real people.

The framework also does not claim that every directorial decision should be reduced to numbers. Natural language, reference images, rehearsal video, audio performance, and human judgment remain essential. The purpose of structured controls is to make important decisions inspectable and editable, not to eliminate ambiguity or artistic interpretation.

## 1.3 Method

This is a research synthesis and systems-design paper rather than a report of a completed model-training experiment. It integrates:

- foundational work on FACS and temporal Action Unit events;
- circumplex and VAD/PAD models of affect;
- Body Action and Posture coding and body-action muscle analysis;
- Laban Movement Analysis, Labanotation, and computational Laban models;
- character-animation representations for phase, local phase, motion matching, kinematics, and physics;
- text-to-motion and human-interaction generation;
- controllable human-video and camera-motion generation;
- video and motion evaluation;
- multimodal video understanding, shot and action segmentation, face/gaze/pose extraction, optical flow, 3D human-camera reconstruction, speech analysis, and timeline interchange; and
- retrieval-augmented system design.

Claims are marked according to the evidence legend. The proposed CPCS schema is derived by assigning each established representation a specific role, identifying missing variables required for generation, and defining explicit interfaces between the levels.

---

<!-- RAG_CHUNK id="cpcs.04" title="Why prompt-only control is insufficient" concepts="underspecification, temporal control, text-to-video limitations" -->
<a id="cpcs-prompt-limits"></a>
# 2. Why Prompt-Only Direction Is Insufficient

## 2.1 Natural Language Compresses Too Many Decisions

Consider the note:

> She crosses the room quickly, trying to appear composed, but fear leaks through when she reaches him.

The sentence contains at least five layers of information:

- **plot action:** crossing the room and reaching another person;
- **tempo:** quickly;
- **performed objective:** appear composed;
- **subtext:** fear is being concealed;
- **turning point:** the concealment weakens at arrival.

It does not specify the path, number of steps, gait cycle, foot contacts, head orientation, eye line, breathing, hand behavior, facial Action Units, when fear becomes visible, how strong the leakage is, whether the camera tracks or remains static, or whether the arrival is marked by a cut. A text-to-video model may produce a plausible average interpretation, but the director cannot reliably reproduce, compare, or revise that interpretation.

Adding adjectives often increases semantic density without resolving timing. “Nervous, controlled, subtle, cinematic, realistic” may alter the overall distribution of outputs while leaving the exact event schedule undefined. The problem is not lack of vocabulary alone. It is the absence of a typed temporal representation.

## 2.2 Video Requires State Transitions, Not Static Attribute Lists

Image prompting can often tolerate a bag of attributes because all conditions are evaluated in one frame. Video requires transitions. A character can begin neutral, recognize danger, suppress a reaction, decide to move, accelerate, make contact, recover, and look away. Each event has an onset, duration, apex, and relation to other events.

Benchmarks on temporal compositionality have shown that video generators can struggle when prompts require explicit initial and final states or coordinated changes across time (Feng et al., 2024 [S45]). This weakness is directly relevant to performance direction: “fear leaks through” is a state transition, not a static style tag.

## 2.3 Human Motion Is Constrained by Contact and Momentum

A visually smooth interpolation between poses can still look inhuman. A planted foot may slide. A punch may reach the opponent before the hips rotate. A runner may change direction without a plausible deceleration. An actor may sit without transferring weight to the chair. These failures arise because smoothness is only one property of motion.

Human-like movement also requires:

- support and contact timing;
- coordinated local phases across body parts;
- center-of-mass movement relative to the support region;
- velocity, acceleration, and deceleration profiles;
- momentum propagation and impact response;
- joint limits and body geometry;
- scene and object constraints; and
- controlled variation rather than framewise noise.

Physics-based imitation systems such as DeepMimic demonstrate that motion examples can be combined with dynamic simulation to produce skills that react to perturbations and environmental changes (Peng et al., 2018 [S24]). The implication for video generation is not that every shot must be fully simulated, but that contact and dynamics need explicit representation when they materially affect plausibility.

## 2.4 Cinematic Motion Couples Camera and Performer

The apparent movement in a frame is a combination of performer motion, object motion, scene geometry, and camera motion. A static actor filmed by a fast dolly can exhibit strong optical flow. A running actor held in a stabilized tracking shot can remain nearly fixed in image coordinates. If a model receives only a 2D body trajectory, it may entangle camera and character movement.

Recent controllable-video research increasingly represents camera trajectories and human or object motion separately. TokenMotion encodes camera trajectories and human poses as spatiotemporal tokens, while Free-Form Motion Control uses six-degree-of-freedom pose information to disentangle object and camera movement (Li et al., 2025 [S38]; Shuai et al., 2025 [S40]). These systems support a central premise of CPCS: cinematography is a first-class control track, not an adjective appended to the performance prompt.

## 2.5 Directability Requires Observability and Revision

A control interface is useful when a user can state a desired change and observe whether it occurred. Prompt-only systems provide weak diagnostics: a failed shot may result from text parsing, temporal planning, pose generation, contact errors, identity drift, camera entanglement, or renderer failure, but all failures appear as “the video is wrong.”

A structured score supports local revision:

- move `AU04` onset from frame 38 to frame 46;
- reduce right-side `AU12` intensity by 30 percent;
- change Laban Time from strongly sudden to moderately sustained;
- lock the left foot from frames 20–31;
- shift fist–jaw contact from frame 52 to frame 56;
- lower the camera by 0.25 m while preserving aim;
- increase recovery duration without altering impact time.

This capacity is the operational meaning of directability in the proposed framework.

---

<!-- RAG_CHUNK id="cpcs.05" title="Layered representation principle" concepts="affect, expression, movement quality, kinematics, cinematography" -->
<a id="cpcs-layered-principle"></a>
# 3. The Layered Representation Principle

A core error in many discussions of generative performance is to search for one universal code that can replace all others. No single representation adequately answers all questions. The paper therefore adopts the following principle:

> **A directorial performance should be represented as aligned layers whose meanings are nonredundant but mutually constraining.**

## 3.1 Layer A: Narrative Intent

Narrative intent includes action, objective, obstacle, relationship, subtext, beat changes, and audience information. It is naturally expressed through language and storyboard structure. Examples include:

- “convince him without revealing the lie”;
- “reach the door before the alarm ends”;
- “the strike is a warning, not an attempt to injure”;
- “the audience notices the fear before the other character does.”

These statements guide the selection and timing of lower-level controls but cannot be converted into one fixed pose.

## 3.2 Layer B: Dimensional Affect

Affect provides a continuous trajectory such as valence, arousal, and dominance or control. It answers questions such as whether the character’s experience becomes more positive or negative, activated or calm, empowered or overwhelmed. Affect is useful for interpolation and temporal arcs, but it remains underdetermined: the same high-arousal negative state can be portrayed through fear, anger, pain, or disgust, depending on appraisal, context, and action tendencies.

## 3.3 Layer C: Visible Performance Description

This layer describes observable choices:

- facial Action Units and their temporal curves;
- head orientation, gaze targets, blink timing, and speech articulation;
- body-part actions and postures;
- Laban Effort, Shape, Body, and Space qualities;
- gesture selection and asymmetry.

It converts affect and intention into a performance design, but it still does not fully determine executable motion.

## 3.4 Layer D: Motion Realization

Motion realization specifies:

- root trajectory and orientation;
- joint rotations and positions;
- global and local phase;
- contact states;
- support and balance;
- velocity, acceleration, jerk, momentum, force, and impulse where relevant;
- constraints between performers, props, and scene geometry.

This layer is the bridge from performance description to animation or control signals.

## 3.5 Layer E: Cinematic Presentation

Cinematic presentation includes camera pose, lens, focus, framing, camera–subject relation, shot duration, and edit points. It can amplify, conceal, or reinterpret a performance. A subtle Action Unit may require a close-up; a full-body Laban quality may require a wider frame; an impact may be shaped by camera shake, shutter behavior, sound, and edit timing.

## 3.6 Layer F: Generative Conditioning

The final layer expresses the score in the forms available to a model:

- text or symbolic tokens;
- continuous control embeddings;
- keypoints, skeleton heatmaps, dense pose, depth, normals, segmentation, or optical flow;
- camera extrinsics and intrinsics;
- reference images and identity embeddings;
- audio features;
- adapter features, cross-attention conditions, or adaptive-normalization signals;
- sampling-time energy functions or constraint gradients.

The same CPCS score can be compiled differently for different systems. This separation makes the framework model-agnostic.

## 3.7 Production Control Layers: What Each Layer Controls and What It Cannot Replace

The layered principle becomes operational when each department-like control family is assigned a distinct question, data type, compilation target, and verification method. The following table expands the core performance stack to include choreography, cinematography, stylized effects, and marketing intent. These additions do not make all layers scientifically equivalent. FACS and parts of affective science are observational or measurement traditions; Laban is a movement-analysis tradition; combat, directorial, VFX, and marketing controls are production ontologies proposed for CPCS.

| Control layer | What it controls | Representative examples | What it can compile into | What it cannot establish alone |
|---|---|---|---|---|
| **Narrative and dramaturgy** | Why the action occurs and what the audience should infer. | objective, obstacle, tactic, subtext, revelation, reversal, audience knowledge | beat graph, prompt clauses, event priorities, reveal constraints, continuity state | exact facial activity, joint motion, camera path, or physical feasibility |
| **VAD/VAC affect** | The continuous emotional trajectory and perceived agency or control. | negative-to-positive valence, rising arousal, falling dominance, experienced/displayed divergence | affect curves, style embeddings, retrieval queries, amplitude and timing priors | a unique emotion category, AU combination, gesture, or action |
| **FACS** | Localized visible facial action and its timing. | eyebrow raise, brow lower, cheek lift, lip-corner pull, eye tightening, jaw drop | AU splines, face-rig or blendshape targets, facial landmarks, expression reference frames, face-condition embeddings | private mental state, truthfulness, a complete body performance, or a one-to-one rig mapping |
| **Gaze, head, blink, breath, and speech behavior** | Attention, turn-taking, orientation, regulation, and audiovisual synchronization. | gaze acquisition, glance aversion, head lead, blink at beat boundary, interrupted inhalation | target-constrained gaze tracks, head-pose curves, blink events, phoneme/viseme timing, audio anchors | full affective meaning without narrative context |
| **Body action and posture coding** | Which body part changes and what visible configuration or function it has. | hand rises, torso retreats, shoulders close, weight shifts, arms guard | body-event labels, key poses, joint-region masks, retrieval tags | smooth trajectories, movement quality, contact forces, or balance |
| **Laban Movement Analysis** | The qualitative organization of body movement. | sudden or sustained; heavy or light; direct or indirect; bound or free; spreading, enclosing, rising, sinking | motion-style conditions, retiming priors, trajectory shaping, amplitude and release modifiers, retrieval of compatible motion | a unique skeleton path, exact action identity, contact schedule, or objective force value |
| **Combat and action coding** | The specific causal sequence of physical actions and reactions. | step-in, pivot, punch-like strike, block, dodge, recoil, fall, recovery | action graph, local phases, target trajectories, support constraints, contact/near-contact schedule, physics-controller goals | how the event is framed, how violent it feels cinematically, or whether a live stunt is safe |
| **Kinematics, phase, contact, and dynamics** | How movement is executed in space and time. | root path, joint rotation, foot plant, center-of-mass transfer, impact impulse, recovery | skeletal animation, control maps, simulation targets, collision constraints, motion vectors | story meaning, emotional interpretation, visual style, or market objective |
| **Director and editorial controls** | How the audience sees and temporally receives the performance. | close-up, low angle, dolly-in, reaction cut, slow motion, impact frame, hold, reveal | camera six-degree-of-freedom trajectory, lens/focus values, framing constraints, time-warp curve, edit decision list | the underlying facial or bodily performance unless explicitly coupled to it |
| **VFX and anime controls** | Stylized visual enhancement or deliberate violation of photographic realism. | speed lines, energy trail, dust burst, camera shake, smear frame, impact flash, held drawing, line boil | effect masks, flow fields, compositor graph, post-process keyframes, particle triggers, stylized reference passes | actual body mechanics, real force, or causal contact; effects may exaggerate an event without changing its physical score |
| **Audio and music controls** | Dialogue, breath, footsteps, impacts, ambience, rhythm, and perceptual emphasis. | footfall sync, breath catch, delayed impact sound, music downbeat, room tone | audio-generation prompts, dialogue tracks, foley event list, music cue sheet, audiovisual alignment constraints | visible movement compliance by itself |
| **Marketing controls** | The communicative and commercial hypothesis governing what must be noticed, remembered, compared, or acted upon. | first-second hook, product hero frame, benefit demonstration, proof beat, brand mnemonic, logo hold, call to action, platform-safe composition | shot-priority rules, product visibility constraints, variant matrix, aspect-ratio crops, title/CTA cards, localization package, measurement tags | a guarantee of sales, persuasion, retention, or conversion; those remain empirical outcomes requiring testing |
| **Safety, rights, and policy controls** | Noncreative limits on identities, assets, content, representations, and permitted uses. | consent scope, age restrictions, licensed likeness, prohibited transformation, stunt-reference boundary | validation gates, asset allowlists, rejection or transformation rules, audit records | creative quality or audience response |

**[PROPOSED]** CPCS treats these layers as a typed production graph rather than one long adjective list. A control is useful only when its owner, time range, coordinate system, strength, merge behavior, and target representation are known. For example, `heavy` in Laban describes a perceived movement quality; `high impulse` in a physics layer describes a dynamic quantity; `brutal` in director language may compile partly into reaction amplitude, sound, framing, and VFX. Treating all three words as synonyms would collapse distinct production decisions.

The marketing layer requires particular caution. “Why it sells” is not a directly observable animation property. A marketing score should encode a **testable communication hypothesis**, such as “the product is visually identifiable before the benefit demonstration” or “the call to action remains readable for at least 1.5 seconds in a vertical crop.” It should then attach outcome measures, variants, and experiment identifiers. CPCS must not state that a particular close-up, color, facial expression, or edit pattern will cause a sale without evidence from the relevant campaign and audience.

The VFX layer likewise remains separate from mechanics. A dust burst can make a landing feel heavier, a one-frame smear can make a strike feel faster, and camera shake can amplify impact. None of these changes proves that the character’s center of mass, support foot, joint timing, or contact impulse is plausible. A compliance report should therefore score **physical realization** and **perceptual enhancement** separately.


<!-- RAG_CHUNK id="cpcs.06" title="FACS foundations" concepts="FACS, action units, visible facial movement, descriptive coding" -->
<a id="cpcs-facs"></a>
# 4. Facial Action Coding as a Generative Control Layer

## 4.1 What FACS Represents

**[ESTABLISHED]** The Facial Action Coding System was introduced by Ekman and Friesen as a systematic method for describing visible facial movement and was later revised with Hager (Ekman & Friesen, 1978 [S01]; Ekman, Friesen, & Hager, 2002 [S02]). Its elementary descriptors are **Action Units (AUs)** associated with observable changes produced by individual muscles or coordinated muscle groups. Examples commonly used in computational work include inner-brow raising, brow lowering, cheek raising, lid tightening, lip-corner pulling, and jaw dropping.

FACS is powerful for generative control because it separates a face into localized, combinable actions rather than restricting the model to a small set of categorical emotions. GANimation demonstrated that AU-conditioned generation can continuously vary the magnitude of individual AUs and combine them in one expression (Pumarola et al., 2018 [S09]). ICface and FACEGAN similarly used AU values as interpretable control signals for reenactment and expression transfer (Tripathy, Kannala, & Rahtu, 2020 [S10]; 2021 [S11]). More recent diffusion-based expression-editing work continues to use AU intensity as an explicit and localized condition (Varanka et al., 2024 [S14]; Wei et al., 2025 [S15]).

**[CAUTION]** FACS is primarily descriptive. It codes visible facial actions, not hidden emotion, intention, truthfulness, or diagnosis. A director may choose a set of AUs to portray fear, skepticism, pain, concentration, or deception, but the mapping depends on context, timing, performer morphology, culture, and co-occurring behavior. CPCS therefore stores the narrative and affect layers separately from the AU layer.

## 4.2 From Static AU Values to Temporal AU Events

A single AU intensity vector is not sufficient for performance. Facial actions unfold through time. Research on AU event detection commonly distinguishes phases such as neutral, onset, apex, and offset (Valstar & Pantic, 2006 [S05]; Valstar & Pantic, 2012 [S06]). A directorial interface should therefore represent each AU as a curve rather than a label.

For AU \(i\), CPCS defines the time-varying activation:

\[
F_i(t) = \left(u_i^L(t), u_i^R(t), c_i(t)\right),
\]

where \(u_i^L\) and \(u_i^R\) are calibrated left- and right-side intensities and \(c_i(t)\) is confidence or constraint weight. Bilateral AUs may share one curve when symmetry is intended. Separate curves support unilateral smirks, asymmetric brow movement, and other performance details.

A compact event representation is:

\[
e_i = \{t_{on}, t_{apex\_in}, t_{apex\_out}, t_{off}, b, p, r_{in}, r_{out}\},
\]

where:

- \(t_{on}\): onset start;
- \(t_{apex\_in}\): time at which the apex is reached;
- \(t_{apex\_out}\): time at which release begins;
- \(t_{off}\): offset completion;
- \(b\): baseline activation;
- \(p\): peak activation;
- \(r_{in}\), \(r_{out}\): curve-shape or easing parameters.

A simple smooth interpolation uses the cubic smoothstep function \(h(x)=3x^2-2x^3\):

\[
u_i(t)=
\begin{cases}
b, & t < t_{on},\\
b+(p-b)h\!\left(\frac{t-t_{on}}{t_{apex\_in}-t_{on}}\right), & t_{on}\le t<t_{apex\_in},\\
p, & t_{apex\_in}\le t<t_{apex\_out},\\
p-(p-b)h\!\left(\frac{t-t_{apex\_out}}{t_{off}-t_{apex\_out}}\right), & t_{apex\_out}\le t<t_{off},\\
b, & t\ge t_{off}.
\end{cases}
\]

This curve is not intended as a biological law. It is an editable interpolation primitive. Cubic Hermite splines, monotonic splines, learned motion priors, or performer-specific curves may be substituted.

## 4.3 Intensity Calibration

FACS intensity is often coded ordinally. A generative system usually requires continuous values. A naive mapping from ordinal categories to equally spaced values can be useful for an interface, but it should not be assumed to correspond linearly to muscle activation, displacement, or perceived strength.

**[PROPOSED]** CPCS uses three linked intensity spaces:

1. **Human-readable intensity:** ordinal or verbal, such as trace, slight, marked, severe, maximum.
2. **Canonical normalized intensity:** \([0,1]\), used in templates and model-independent storage.
3. **Performer/rig-specific intensity:** blendshape coefficient, deformation magnitude, latent-control value, or actuator target calibrated for the identity and renderer.

The conversion is stored as a calibration function:

\[
\hat u_{i,r}(t) = g_{i,r,p}\big(u_i(t)\big),
\]

where \(r\) is the rig or model and \(p\) is the performer or identity. The function may be nonlinear because an AU can become perceptually visible at different thresholds across faces and rigs.

## 4.4 Coarticulation, Dependencies, and Incompatibilities

Facial actions are not independent sliders in practice. Speech, breathing, gaze, head movement, and other AUs alter their visible realization. A jaw drop during a vowel should not be generated as if it were an unrelated emotional action. Lip-corner motion can interact with mouth opening, cheek raising, and nasolabial deformation. Eyelid behavior depends on gaze direction and head orientation.

**[PROPOSED]** Each facial event in CPCS may therefore include:

- `source`: emotion, speech, reflex, social signal, physical exertion, or director override;
- `priority`: hard, high, medium, low;
- `dependencies`: other AU, viseme, gaze, or head-pose events;
- `conflicts`: mutually incompatible or visually destructive combinations;
- `blend_mode`: additive, maximum, weighted, suppressive, or learned;
- `region_lock`: upper face, lower face, unilateral side, or full face;
- `identity_calibration_id`;
- `evidence_level` and `source_ids`.

A facial-control solver can resolve competing demands before the video generator is invoked. For example, speech articulation can retain hard lip-closure constraints while an emotional lip-corner action is treated as a soft preference.

## 4.5 Gaze, Head Pose, Blinks, and Breathing

FACS alone is not a complete facial-performance system. Gaze and head orientation strongly affect perceived attention, status, and intention. Blink timing can mark cognitive load, turn-taking, impact, or emotional regulation. Breathing affects the nostrils, mouth, jaw, neck, shoulders, and chest.

CPCS places the following tracks adjacent to the AU tracks:

- head rotation and translation;
- gaze target and binocular convergence;
- eyelid aperture and blink events;
- pupil or iris control where supported;
- viseme/phoneme timing;
- breath phase and respiratory effort;
- tears, perspiration, flushing, or other appearance changes as separate render effects.

This separation avoids forcing all facial meaning into AU codes. It also permits models like ICface, which combine head-pose angles and AU values, to receive the appropriate signals independently (Tripathy et al., 2020 [S10]).

## 4.6 FACS as a Director’s Interface

A director-facing system should not require the user to memorize every AU number. It should support three entry modes:

- **semantic:** “a restrained smile that never reaches the eyes”;
- **reference-based:** analyze a rehearsal or performance clip into candidate AU curves;
- **technical:** edit exact AU curves, asymmetry, and timing.

The system can retrieve candidate mappings from a library, but it must display the result as an editable hypothesis rather than a universal truth. A semantic instruction might compile into a low-intensity, asymmetric lip-corner action while suppressing cheek raising; another director may choose a different realization. The directorial value lies in making the choice explicit and repeatable.

---

<!-- RAG_CHUNK id="cpcs.07" title="Dimensional affect and VAC/VAD" concepts="valence, arousal, dominance, control, affect trajectories" -->
<a id="cpcs-affect"></a>
# 5. Dimensional Affect: Valence, Arousal, and Dominance or Control

## 5.1 Circumplex and VAD Models

**[ESTABLISHED]** Dimensional models represent affect as coordinates rather than discrete labels. Russell’s circumplex model organizes affect primarily around valence and arousal (Russell, 1980 [S07]). Valence represents pleasantness or unpleasantness; arousal represents activation or deactivation. Mehrabian and Russell’s pleasure–arousal–dominance formulation adds a dimension associated with control, power, or dominance (Mehrabian & Russell, 1974 [S08]). The Self-Assessment Manikin operationalizes pleasure/valence, arousal, and dominance through nonverbal rating scales (Bradley & Lang, 1994 [S08A]).

For cinematic control, a continuous affect vector is useful because it can vary smoothly across a shot:

\[
A(t)=[v(t),a(t),d(t)], \qquad v,a,d\in[-1,1].
\]

CPCS permits the alias `control` for \(d\) in user interfaces, provided metadata records that the dimension refers to perceived agency or dominance. A frightened character who remains strategically composed may have negative valence, elevated arousal, and moderate-to-high control. A panicked character may have similar valence and arousal but low control.

## 5.2 Affect Is a Trajectory, Not a Shot-Level Tag

A single affect label for a five-second shot erases the dramatic arc. CPCS represents affect using knots or curves:

```yaml
affect:
  coordinate_system: VAD
  interpolation: cubic_hermite
  knots:
    - {time_s: 0.00, valence: -0.20, arousal: 0.25, dominance: 0.55}
    - {time_s: 1.40, valence: -0.35, arousal: 0.45, dominance: 0.50}
    - {time_s: 2.65, valence: -0.62, arousal: 0.78, dominance: 0.20}
    - {time_s: 4.10, valence: -0.45, arousal: 0.52, dominance: 0.42}
```

This structure supports a beat such as “control collapses at recognition, then partially returns.” The curve can condition motion style, facial planning, voice, breathing, and editing while remaining independent from their exact realization.

## 5.3 Why Affect Does Not Replace FACS

The mapping from affect coordinates to visible behavior is one-to-many. High arousal and negative valence may produce:

- widened eyes and withdrawal;
- narrowed eyes and approach;
- rigid suppression;
- freezing;
- crying;
- laughter under stress;
- culturally or individually specific masking behavior.

Likewise, one AU combination can occur in multiple contexts. Therefore, CPCS uses affect as a latent directorial target and FACS as a visible facial plan. A retrieval module may suggest AU patterns compatible with a target affect, but a performance-planning module must also consider character objective, appraisal, action tendency, social context, speech, and director style.

This separation is supported by systems that explicitly connect affect spaces and facial geometry. EMOCA learns emotion-sensitive 3D face reconstruction and estimates valence and arousal from reconstructed expression parameters (Daněček, Black, & Bolkart, 2022 [S12]). EmoStyle and related work use continuous valence–arousal control for expression editing (Azari & Lim, 2024 [S13]). These methods show that affect coordinates can be computationally useful without implying a deterministic one-to-one map.

## 5.4 Affect as a Cross-Modal Constraint

A director expects the face, body, voice, and camera to tell a coherent story. CPCS treats affect as a cross-modal constraint rather than a direct renderer input only. For a target \(A(t)\), the system can estimate affect from generated modalities:

\[
\hat A_F(t)=E_F(\text{face}),\quad
\hat A_B(t)=E_B(\text{body}),\quad
\hat A_V(t)=E_V(\text{voice}),
\]

and penalize divergence:

\[
\mathcal L_{affect}=
\lambda_F d(\hat A_F,A)+
\lambda_B d(\hat A_B,A)+
\lambda_V d(\hat A_V,A).
\]

The weights depend on the shot. In a close-up, facial evidence may dominate. In a silhouette or long shot, body movement and voice may carry more information.

**[CAUTION]** Affect estimators inherit dataset and cultural biases. They should be used as compliance indicators, not authoritative judges of emotion. Human director ratings remain necessary.

## 5.5 Character State Versus Performed Display

An important dramatic distinction is the difference between **internal state** and **performed display**. A character may feel high arousal but deliberately display low arousal. CPCS therefore supports two affect tracks:

- `experienced_affect`: the intended internal trajectory used by the narrative planner;
- `displayed_affect`: the affective impression the performance should communicate.

Their difference can encode masking, deception, suppression, politeness, or strategic self-presentation:

\[
M(t)=A_{experienced}(t)-A_{displayed}(t).
\]

A high masking magnitude does not directly specify facial action. It tells the performance planner to select controlled leakage, delayed onset, micro-asymmetry, breath changes, or conflicts between modalities. The exact choices remain editable.

---

<!-- RAG_CHUNK id="cpcs.08" title="Body action coding systems" concepts="BAP, BACS, body action, posture coding" -->
<a id="cpcs-body-coding"></a>
# 6. Body Action and Posture Coding: The Closest Observational Analogue to FACS

## 6.1 Body Action and Posture Coding System

**[ESTABLISHED]** The Body Action and Posture coding system developed by Dael, Mortillaro, and Scherer provides a time-aligned microdescription of body movement at multiple levels: anatomical articulation, movement form, and communicative or self-regulatory function (Dael, Mortillaro, & Scherer, 2012 [S16]). It was used to analyze body actions and postures produced by actors portraying emotions (Dael, Mortillaro, & Scherer, 2012 [S17]).

BAP is important for CPCS because it demonstrates that body behavior can be decomposed beyond broad action labels. “Walk” or “fight” is not enough; body-part movement, direction, orientation, posture, and function can be annotated over time.

However, BAP is not a turnkey animation command language. It describes observed movement and posture. It does not necessarily specify joint rotations, ground contacts, center-of-mass dynamics, or actuator torques. CPCS uses BAP-like descriptors in the semantic and observational layer, then compiles them into executable motion representations.

## 6.2 Body Action Coding System and Muscle-Level Ambitions

Research described as a Body Action Coding System has explored the muscle activations underlying emotional body expressions (Huis in ’t Veld, Van Boxtel, & de Gelder, 2014 [S18]). This direction is conceptually closer to the anatomical grounding of FACS, but it should not be mistaken for a complete, universally adopted code for all locomotion, combat, manipulation, dance, and social gesture.

A full-body generative system faces greater complexity than the face:

- the body has many joints and multiple valid kinematic solutions;
- whole-body behavior is strongly constrained by gravity and support;
- movement depends on terrain, props, clothing, footwear, and other actors;
- large actions involve momentum and delayed effects;
- the same endpoint can be reached by different coordination strategies;
- morphology changes feasible trajectories and timing.

Consequently, a “body FACS” alone would still require kinematic, contact, and dynamic layers.

## 6.3 Proposed Motion Atoms

**[PROPOSED]** CPCS defines a model-independent **motion atom** as the smallest practically editable unit of body instruction. It is not claimed as a scientific replacement for BAP or Labanotation.

```yaml
motion_atom:
  id: "atom.right_cross.001"
  actor: "fighter_a"
  body_part: "right_hand"
  primitive: "strike"
  target: "fighter_b.head.left_jaw"
  reference_frame: "fighter_a.pelvis"
  direction: [0.82, 0.05, 0.57]
  amplitude_m: 0.71
  onset_s: 0.58
  apex_or_contact_s: 0.94
  offset_s: 1.32
  phase_role: "distal_effector"
  dependencies:
    - "atom.rear_foot_pivot.001"
    - "atom.pelvis_rotation.001"
    - "atom.torso_rotation.001"
  laban_effort:
    weight: 0.80
    time: 0.92
    space: 0.88
    flow: 0.45
  constraints:
    contact_required: true
    max_penetration_m: 0.01
    preserve_balance: true
```

A motion atom combines the interpretability of a body-part instruction with the timing and dependency information needed by a planner. Complex action is represented as a graph of atoms rather than a flat list.

## 6.4 Functional Meaning and Physical Realization

Body coding systems can annotate functions such as self-touch, adaptors, communicative gestures, or posture changes. In generation, functional meaning is valuable because it helps choose between kinematically possible alternatives. A character “protecting the injured ribs” and a character “folding the arms to signal refusal” may place the forearms in similar regions but require different tension, timing, gaze, and subsequent action.

CPCS preserves function as metadata and treats it as a soft semantic constraint. The final trajectory is produced by a motion planner, retrieval system, or physics controller capable of satisfying the scene and contact constraints.

---

<!-- RAG_CHUNK id="cpcs.09" title="Laban Movement Analysis" concepts="LMA, BESS, Effort, Shape, Body, Space" -->
<a id="cpcs-laban"></a>
# 7. Laban Movement Analysis as the Body-Quality Layer

## 7.1 What Laban Contributes

**[ESTABLISHED]** Laban-based systems describe not only what movement occurs but how it is organized and experienced. Contemporary Laban Movement Analysis is commonly taught through the categories **Body, Effort, Shape, and Space (BESS)**, drawing on Laban’s work and subsequent development by Bartenieff and others (Laban & Lawrence, 1947 [S19]; Bartenieff & Lewis, 1980 [S20]).

For AI performance control, Laban fills a gap between affect and kinematics. It provides vocabulary for movement quality without requiring the director to specify every joint. Two characters can perform the same action—walk forward, raise a hand, sit, punch—with different Effort and Shape qualities.

## 7.2 Body

The **Body** category concerns what parts move, how they are organized, initiation, sequencing, connectivity, and coordination. Computationally useful questions include:

- Which body part initiates?
- Is movement distal or proximal?
- Is the body moving as one unit or through sequential articulation?
- What is the relationship among core, limbs, head, and breath?
- Is the movement symmetrical or cross-lateral?

These questions are directly relevant to human likeness. A punch initiated only by the wrist is different from one sequenced through the foot, pelvis, torso, shoulder, elbow, and fist.

## 7.3 Effort

The four classic Effort factors are commonly represented as polar qualities:

| Factor | Pole 1 | Pole 2 | Directorial interpretation |
|---|---|---|---|
| Weight | light | strong | delicate versus forceful engagement with weight |
| Time | sustained | sudden | lingering versus urgent temporal attitude |
| Space | indirect | direct | flexible attention/path versus focused trajectory |
| Flow | free | bound | released continuity versus controlled restraint |

CPCS stores these as continuous targets in \([-1,1]\), while retaining the verbal pole labels:

\[
L_E(t)=[w(t),\tau(t),s(t),f(t)].
\]

The numbers are interface values, not universal physical units. A director can specify “moderately strong, strongly sudden, direct, and partially bound.” A performer profile or learned style model maps those values into motion.

## 7.4 Shape

Shape describes how the body changes form in relation to itself and the environment. Useful directional tendencies include:

- rising versus sinking;
- spreading versus enclosing;
- advancing versus retreating.

CPCS represents a basic Shape vector:

\[
L_S(t)=[r(t),e(t),a(t)],
\]

where the axes correspond to rise/sink, spread/enclose, and advance/retreat. Additional metadata may represent Shape Flow, Directional movement, or Shaping as appropriate to the production’s Laban practice.

Shape is particularly useful for directing emotional transitions. A character may maintain the same root position while gradually enclosing the torso, narrowing the shoulders, and retreating the head. These changes can communicate withdrawal without an explicit locomotor action.

## 7.5 Space

Space concerns direction, level, pathways, reach, and relation to the kinesphere. A structured system can represent:

- high, middle, and low levels;
- sagittal, vertical, and horizontal tendencies;
- direct destination versus wandering path;
- near, middle, and far reach;
- body-relative versus world-relative direction;
- pathways such as straight, arc, spiral, or irregular.

This information bridges Laban description and geometric control.

## 7.6 Labanotation and Symbolic Motion Planning

Labanotation encodes body part, direction, level, duration, and other movement information through symbols. It offers an important precedent for a symbolic motion language. Recent work has adapted Laban-derived representation for machine generation. One LaMoGen system uses quantified Laban Effort and Shape targets as inference-time guidance for text-to-motion diffusion, seeking to vary expressive quality while preserving action identity (Kim, Kim, & Chun, 2025 [S33]). A separate 2026 LaMoGen work introduces **LabanLite**, which represents atomic body-part actions as discrete Laban symbols paired with textual templates and uses an LLM to compose interpretable motion plans (Jiang et al., 2026 [S34]).

These works support two complementary uses of Laban in CPCS:

1. **quality guidance:** alter how an existing action is performed;
2. **symbolic planning:** decompose language into timed body-part instructions.

They remain emerging research directions rather than a universal production standard.

## 7.7 Computational Operationalizations

**[OPERATIONALIZATION]** To train or verify Laban-conditioned systems, qualitative factors require measurable proxies. The following are candidate features, not definitions:

### Weight proxies

- change in center-of-mass momentum;
- peak acceleration or deceleration;
- estimated impulse at contact;
- movement amplitude and muscular-tension proxies;
- vertical loading and ground-reaction estimates.

### Time proxies

- action duration;
- time to peak speed;
- acceleration concentration;
- ratio of preparation to execution duration;
- onset slope.

### Space proxies

Path directness can be approximated by:

\[
D_{path}=\frac{\|p(t_1)-p(t_0)\|}{\int_{t_0}^{t_1}\|\dot p(t)\|dt},
\]

where values near one indicate a geometrically direct path. This is only one aspect of the Laban Space factor, which also includes attentional orientation and spatial intent.

### Flow proxies

- jerk and higher-order smoothness;
- ability to interrupt or reverse movement;
- stopping distance;
- continuity across joints;
- co-contraction or stiffness estimates in physical models;
- residual movement after the intended endpoint.

### Shape proxies

- torso volume or convex-hull change;
- shoulder and elbow spread;
- vertical center-of-mass and head displacement;
- forward/backward torso displacement;
- distances among selected body landmarks.

**[CAUTION]** Different Laban practitioners may code the same movement differently, and computational proxies can capture only selected aspects of the constructs. Reliability studies and production-specific calibration are necessary (Bernardet et al., 2019 [S21]). CPCS therefore stores both qualitative labels and quantitative features, with provenance.

## 7.8 Laban as a Style-Preserving Modifier

A useful generative principle is to separate **action identity** from **performance quality**. The action “walk to the table” should remain recognizable while its Weight, Time, Space, Flow, and Shape are changed. This can be formulated as constrained style transfer:

\[
\min_{M}\; \mathcal L_{action}(M,M_0)
+\lambda_L \mathcal L_{Laban}(M,L^*)
+\lambda_P \mathcal L_{physical}(M),
\]

where \(M_0\) is a base motion, \(L^*\) is the target Laban profile, and \(M\) is the modified motion. The first term preserves action identity; the second imposes movement quality; the third preserves contacts and physical plausibility.

This formulation mirrors the director’s request: “Keep the blocking and action, but make it heavier, more direct, and more controlled.”

---

<!-- RAG_CHUNK id="cpcs.10" title="Why FACS and Laban must remain distinct" concepts="representation boundaries, integration" -->
<a id="cpcs-facs-laban-boundary"></a>
# 8. Why FACS, Affect, and Laban Should Be Integrated but Not Collapsed

FACS, affect dimensions, and Laban describe different objects:

| Representation | Primary object | Best suited to | Does not uniquely specify |
|---|---|---|---|
| FACS | visible facial actions | localized facial configuration and timing | emotion, intention, body motion, camera |
| VAD/VAC | affective state or impression | continuous emotional trajectory | exact face, gesture, gait, or contact |
| BAP/BACS | observed body action/posture or muscle-oriented body analysis | body-part description and behavior coding | full executable dynamics and cinematic intent |
| Laban | movement organization and quality | expressive style, initiation, shape, spatial attitude | exact joint trajectory or contact solution |
| Skeletal kinematics | pose and trajectory | geometric realization | force, intention, visual appearance |
| Phase and contact | coordination and constraints | locomotion, multi-contact action, timing | narrative meaning or rendering |
| Dynamics | mass, momentum, force, torque | weight, impact, recovery | emotional interpretation |
| Camera score | viewpoint and imaging | framing, reveal, visual rhythm | underlying actor behavior |

The integration is therefore hierarchical:

\[
\text{narrative}\rightarrow
\text{affect}\rightarrow
\text{performance description}\rightarrow
\text{motion realization}\rightarrow
\text{cinematic presentation}\rightarrow
\text{pixels}.
\]

Information also flows backward. A wide shot may make subtle facial actions invisible, causing the compiler to reallocate expression to body, voice, or blocking. A close-up may reduce the need for large gestures. A physically infeasible contact may require the choreography or shot design to change. CPCS is consequently a constraint graph, not a one-way lookup table.


<!-- RAG_CHUNK id="cpcs.11" title="Motion realization stack" concepts="kinematics, skeletal representation, SMPL-X, FLAME, rotations" -->
<a id="cpcs-motion-realization"></a>
# 9. The Motion-Realization Stack

The performance-description layers answer what a movement should communicate. The motion-realization stack answers how the body reaches those results coherently over time.

## 9.1 Root Motion and Skeletal Kinematics

A basic full-body motion sequence contains a root transform and joint rotations:

\[
K(t)=\{T_{root}(t), R_{root}(t), R_1(t),\ldots,R_J(t)\}.
\]

The root usually represents the pelvis or body coordinate frame. Joint rotations are propagated through a kinematic hierarchy to obtain world-space joint positions. Depending on the model, the representation may also include facial, hand, eye, and jaw parameters.

Parametric body models such as SMPL-X provide a shared body, hand, and face parameterization, while FLAME provides a learned head model with identity, pose, and expression parameters (Pavlakos et al., 2019 [S26]; Li et al., 2017 [S25]). AMASS aggregates motion-capture datasets into a common body-model representation, making it useful for motion learning and retrieval (Mahmood et al., 2019 [S27]). These models are implementation options, not requirements of CPCS.

For learning, rotation representations matter. Euler angles introduce discontinuities and axis-order problems; quaternions have sign ambiguity; direct rotation matrices require constraints. The continuous six-dimensional representation proposed by Zhou et al. maps network outputs to valid rotations and is widely useful for motion-learning systems (Zhou et al., 2019 [S28]). CPCS stores a canonical representation identifier and permits conversion at compilation time.

## 9.2 Pose Is Not Movement

A sequence of poses is necessary but not sufficient. Human observers are sensitive to how trajectories are produced. Two sequences can share the same key poses while differing in anticipation, timing, force, continuity, contact, and recovery. This is why a storyboard of static images cannot fully direct animation without timing and transition information.

CPCS distinguishes:

- **key pose:** a strategically important configuration;
- **event:** a semantically meaningful change such as contact, recognition, or release;
- **trajectory constraint:** a path or orientation that must be followed;
- **motion prior:** a learned or retrieved distribution that fills unspecified intervals;
- **physical constraint:** a requirement imposed by support, collision, joint limits, or dynamics.

## 9.3 Global Motion Phase

**[ESTABLISHED]** Phase-conditioned character controllers use a cyclic variable to disambiguate locomotion. Phase-Functioned Neural Networks condition model parameters on locomotion phase, enabling responsive character control across terrain and trajectories (Holden, Komura, & Saito, 2017 [S22]). A normalized phase can be written:

\[
\phi(t)\in[0,1), \qquad \phi(t+T)=\phi(t).
\]

For a walk, phase landmarks may correspond to left initial contact, right toe-off, right initial contact, and left toe-off. The exact event definition depends on the gait convention. The key point is that phase provides a stable coordinate within a repeated movement cycle.

CPCS stores phase together with explicit contact events rather than assuming a fixed percentage for all performers and speeds. Human gait changes with velocity, terrain, footwear, age, style, morphology, and dramatic choice.

## 9.4 Local Motion Phases

A single global phase is inadequate for complex actions. **[ESTABLISHED]** Local Motion Phases assign separate phase variables to different joints or motion components, supporting multi-contact interactions in which body parts follow distinct rhythms (Starke et al., 2020 [S23]). CPCS represents:

\[
\Phi(t)=[\phi_{root}(t),\phi_{left\_foot}(t),\phi_{right\_foot}(t),
\phi_{pelvis}(t),\phi_{torso}(t),\phi_{left\_hand}(t),\ldots].
\]

Local phase is especially useful for:

- a boxer whose rear foot pivots before the fist reaches its target;
- a climber with alternating hand and foot contacts;
- a dancer whose arms sustain while the legs execute sudden steps;
- a person sitting while one hand braces on a chair;
- two actors whose contact events are coupled but whose preparations differ.

A phase track is not necessarily periodic. It may be represented by learned periodic features, normalized progress through an event, or a local oscillator with amplitude, frequency, phase offset, and bias. The representation should be selected according to the action.

## 9.5 Contact and Support

Contact is a first-class event in human motion. CPCS distinguishes:

- **support contact:** foot–ground, hand–rail, body–chair;
- **manipulation contact:** hand–prop, foot–ball;
- **interpersonal contact:** hand–shoulder, fist–jaw, embrace;
- **collision without sustained contact:** impact or deflection;
- **near-contact:** intentional miss, dodge, or threat;
- **attachment:** grip or constrained hold.

A contact event is represented as:

\[
q_k=\{b_a,b_b,t_{start},t_{peak},t_{end},d^*,n^*,\mu,\kappa,w\},
\]

where \(b_a,b_b\) are body or object regions, \(d^*\) is desired separation, \(n^*\) is contact normal if known, \(\mu\) is friction, \(\kappa\) is compliance or softness, and \(w\) is constraint priority.

During a planted-foot interval, the foot’s world-space velocity should be close to zero:

\[
\mathcal L_{plant}=\sum_{t\in Q_{foot}}
\|\dot p_{foot}^{world}(t)\|^2.
\]

Ground penetration can be penalized by signed distance:

\[
\mathcal L_{penetration}=\sum_{j,t}
\max(0,-d_{scene}(p_j(t)))^2.
\]

Contact-aware motion-generation research treats contacts as a bridge between human and object motion and as an explicit control signal for interaction (Diller & Dai, 2024 [S31]; Ma et al., 2024 [S32]). InterControl represents interactions through desired distances between joint pairs and uses inverse-kinematics guidance to align them (Wang et al., 2024 [S30]).

## 9.6 Center of Mass, Balance, and Support Geometry

A body can satisfy joint targets and still appear weightless if the center of mass is inconsistent with support. CPCS optionally estimates the center of mass:

\[
p_{COM}(t)=\frac{\sum_m m_m p_m(t)}{\sum_m m_m},
\]

where \(m_m\) and \(p_m\) are segment masses and centers. In quasi-static motion, the projected center of mass should generally remain within or near the support polygon. Dynamic movement may intentionally move outside it, but then momentum and future contacts must support recovery.

A simple support loss is:

\[
\mathcal L_{support}=d\big(\Pi_{ground}(p_{COM}),\mathcal P_{support}\big)^2,
\]

where the distance is zero inside the support polygon. For running, jumping, falling, or fighting, a capture-point or full dynamic model is more appropriate.

## 9.7 Dynamics: Weight, Momentum, and Impact

A kinematic path determines positions but not the forces that produce them. CPCS includes an optional dynamic state:

\[
Y(t)=\{v(t),a(t),j(t),p_{lin}(t),L_{ang}(t),\tau(t),F(t),I(t)\},
\]

containing velocity, acceleration, jerk, linear momentum, angular momentum, torque, force, and impulse where available.

For impact between actors or objects, impulse provides a useful event-level variable:

\[
J=\int_{t_0}^{t_1}F(t)dt=\Delta p.
\]

A director may not specify Newtons. The interface can use relative descriptors such as glancing, restrained, solid, or explosive, while the physical layer estimates values consistent with mass, speed, and contact duration.

Physics-based imitation methods such as DeepMimic show how motion examples and task objectives can train controllers that preserve stylistic movement while reacting to perturbations (Peng et al., 2018 [S24]). For CPCS, physics can operate at several levels:

- full simulation for stunts, impacts, falls, and object interaction;
- lightweight inverse dynamics for plausibility checks;
- contact-aware kinematic cleanup;
- learned physics priors or differentiable constraints;
- post-generation verification only.

## 9.8 Smoothness, Jerk, and Intentional Sharpness

Jerk is the third derivative of position:

\[
j(t)=\frac{d^3p(t)}{dt^3}.
\]

Minimizing jerk can improve smoothness, but human motion is not uniformly low-jerk. A sudden strike, startled reaction, or hard stop may contain sharp acceleration changes. Therefore, CPCS uses **style-conditioned smoothness**:

\[
\mathcal L_{smooth}=\sum_{b,t}w_b(t)\|j_b(t)\|^2,
\]

where \(w_b(t)\) is reduced near intended impacts or sudden Effort events and increased during sustained, controlled movement. This prevents the common error of smoothing away the dramatic quality that the director requested.

## 9.9 Microvariation and Biological Plausibility

Perfectly periodic motion can look synthetic. Human movement includes variability in timing, amplitude, balance corrections, gaze, breathing, and bilateral symmetry. CPCS supports controlled microvariation with constraints:

\[
M'(t)=M(t)+\epsilon(t),
\]

where \(\epsilon\) is band-limited, correlated across anatomically related joints, and projected back into contact and balance constraints. Random framewise noise is inappropriate because it creates jitter rather than biological variation.

Microvariation should also be identity- and state-dependent. Fatigue, injury, costume, age, skill, and emotional regulation alter movement. These attributes belong in performer and scene profiles rather than being inferred from stereotypes.

---

<!-- RAG_CHUNK id="cpcs.12" title="Walking and running control" concepts="gait, locomotion, phase, stride, contacts, Laban" -->
<a id="cpcs-locomotion"></a>
# 10. Directing Walking and Running

## 10.1 Locomotion as a Multi-Layer Score

A directable walk is not a single animation clip. It is the combination of:

- path and destination;
- speed and acceleration profile;
- stride length and cadence;
- foot contact schedule;
- pelvis, spine, head, and arm coordination;
- gaze and attention;
- Laban Effort and Shape;
- affect trajectory and performance objective;
- terrain, footwear, costume, load, and injury constraints;
- camera relationship.

The root path may be represented as a spline \(P(s)\) with speed \(v(t)\), so that traveled distance is:

\[
s(t)=\int_0^t v(\tau)d\tau, \qquad p_{root}(t)=P(s(t)).
\]

This separates geometric blocking from timing. A director can retain the path while changing urgency, hesitation, or acceleration.

## 10.2 Gait Events and Phase

CPCS represents foot contacts explicitly. A walking template may include heel or initial contact, loading response, mid-stance, terminal stance, toe-off, swing, and the next contact. A production need not use clinical gait terminology internally, but event boundaries should remain observable.

A locomotion solver uses contact events to generate phase and step placement. The planned foot positions must be reachable from the root trajectory and compatible with terrain. A mismatch should trigger one of three outcomes:

1. adjust step length or cadence within tolerance;
2. adjust root timing while preserving the path;
3. return a constraint conflict to the director or planner.

Silent automatic violation—such as foot sliding—is not acceptable in a deterministic workflow.

## 10.3 Stylistic Walking Through Laban

The same route and step schedule can support different qualities:

- **strong, sudden, direct, bound:** purposeful, controlled advance;
- **light, sustained, indirect, free:** drifting or exploratory movement;
- **strong, sustained, direct, bound:** heavy, deliberate procession;
- **light, sudden, indirect, free:** skittish or playful movement.

These descriptions are not emotion labels. Context determines whether a direct, strong walk appears confident, angry, military, exhausted, or protective. The affect and narrative layers resolve the interpretation.

## 10.4 Running

Running introduces shorter support intervals, potential flight phases, greater impact, and stronger coupling between speed and stride parameters. Important controls include:

- acceleration and deceleration distance;
- flight duration;
- foot strike pattern and placement;
- vertical center-of-mass oscillation;
- torso lean;
- arm drive;
- turning radius and bank;
- terrain response;
- fatigue and breathing;
- camera stabilization or shake.

A common video-generation failure is instantaneous speed change. CPCS specifies acceleration envelopes and required stopping distance. A hard stop can be sudden in Laban Time while still respecting the body’s need to lower the center of mass, plant, and dissipate momentum.

## 10.5 Verification for Locomotion

Locomotion verification should report:

- path deviation;
- speed-profile error;
- step-event timing error;
- planted-foot velocity;
- foot penetration and floating;
- stride and cadence statistics;
- phase continuity;
- center-of-mass support or dynamic stability;
- Laban-quality agreement;
- gaze-target adherence;
- camera-relative composition.

A visually attractive video that fails the intended arrival time or slides through contacts is not a successful directed shot.

---

<!-- RAG_CHUNK id="cpcs.13" title="Fighting and multi-actor action" concepts="combat, interaction, contact, reaction, momentum, choreography" -->
<a id="cpcs-fighting"></a>
# 11. Directing Fighting and Multi-Actor Physical Interaction

## 11.1 Choreography Is a Coupled System

A fight cannot be generated reliably as independent animations for two actors. Each action constrains the other actor’s position, timing, attention, and response. CPCS represents a multi-actor scene as a graph:

\[
\mathcal G(t)=(V,E(t)),
\]

where nodes \(V\) are actors, body regions, props, and scene objects; edges \(E(t)\) are contact, target, avoidance, gaze, support, or attachment relations.

A strike event can include:

- attacker and defender;
- initiating body chain;
- target body region;
- intended contact or near-miss;
- impact time and direction;
- safety offset or staged distance;
- defender anticipation and reaction delay;
- impulse class;
- follow-through and recovery;
- camera reveal and edit point;
- sound synchronization.

## 11.2 Kinetic Chains

Human strikes, throws, and evasions are coordinated chains. A right cross may involve:

1. weight shift and rear-foot pressure;
2. rear-foot pivot;
3. pelvis rotation;
4. torso rotation;
5. scapular and shoulder motion;
6. elbow extension;
7. fist orientation;
8. contact or controlled miss;
9. follow-through;
10. recovery to guard.

CPCS encodes dependencies and relative timing rather than requiring every joint to peak simultaneously. Local phase or event-progress variables can express the proximal-to-distal sequence.

## 11.3 Contact Versus Staged Contact

Live-action stunt choreography often creates the visual impression of contact without actual body collision. Generated video should distinguish:

- `physical_contact`: geometry meets and impulse is exchanged;
- `staged_near_contact`: minimum separation is maintained but camera perspective creates apparent contact;
- `occluded_contact`: event occurs behind a body or object;
- `reaction_only`: defender reacts to an implied off-screen or missed action.

This distinction is both cinematic and safety-relevant. A model should not infer real impact when the storyboard calls for a cheated angle.

## 11.4 Reaction Timing

A defender’s reaction should not begin before the perceptual cue unless anticipation is narratively intended. CPCS therefore records:

- cue time;
- perception delay;
- motor response onset;
- contact time;
- reaction apex;
- recovery.

For stylized action, these delays may be compressed or exaggerated. The key is that they are editable. A reaction beginning several frames before contact can be a deliberate stunt convention or an error; the score resolves the ambiguity.

## 11.5 Momentum Transfer and Follow-Through

At impact, the apparent direction and strength of the reaction should be compatible with the strike and body configuration. CPCS can use an interaction constraint:

\[
\mathcal L_{impact}=
\lambda_p\|p_a(t_c)-p_b(t_c)-d^*\|^2
+\lambda_n(1-\hat v_a\cdot n^*)^2
+\lambda_r\|\Delta p_b-J^*\|^2,
\]

where \(t_c\) is contact time, \(d^*\) desired separation, \(n^*\) target direction, and \(J^*\) desired impulse class or vector. The physics need not be exact enough for engineering analysis; it must be coherent enough to support weight and causality.

## 11.6 Weapons and Props

Props introduce rigid-body pose, grip, collision, and continuity constraints. A weapon or tool must not teleport between hands, change scale, or pass through the body. CPCS adds:

- prop identity and geometry reference;
- six-degree-of-freedom trajectory;
- grip contacts and hand-pose constraints;
- attachment intervals;
- collision groups;
- mass and inertia estimates if simulated;
- safety and content-policy metadata;
- continuity across shots.

The framework describes cinematic control; it is not a manual for causing real-world harm. Fight templates should be sourced from licensed choreography or safe performance capture and used with appropriate governance.

## 11.7 Camera and Editing in Action

Action readability depends on camera position, lens, motion, and cutting. A close lens and rapid camera shake can conceal motion errors but reduce spatial comprehension. A wide shot exposes full-body mechanics and contact timing. CPCS can optimize the camera to reveal the intended beat while preserving motion truth.

A fight beat may specify:

- establish the distance before the attack;
- keep both hips visible through preparation;
- allow the striking limb to cross a high-contrast background;
- cut on the defender’s reaction rather than the contact;
- preserve screen direction across the edit;
- synchronize sound transient, camera impulse, and motion apex.

These are semantic cinematic constraints compiled into camera and edit tracks.

---

<!-- RAG_CHUNK id="cpcs.14" title="Cinematic Performance Control Score formalism" concepts="CPCS, formal representation, synchronized tracks" -->
<a id="cpcs-formalism"></a>
# 12. The Cinematic Performance Control Score

## 12.1 Definition

**[PROPOSED]** The Cinematic Performance Control Score is a time-indexed, provenance-aware graph of directorial constraints and preferences. At time \(t\), a shot score is represented as:

\[
\mathcal S(t)=\{
B(t), A(t), F(t), L(t), K(t), \Phi(t), Q(t), Y(t), I(t), G(t), X(t), O(t)
\}.
\]

The components are:

| Symbol | Track | Contents |
|---|---|---|
| \(B(t)\) | beat | narrative action, objective, subtext, event boundaries |
| \(A(t)\) | affect | experienced and displayed VAD/VAC trajectories |
| \(F(t)\) | face | AUs, gaze, head pose, blinks, visemes, breath-linked facial motion |
| \(L(t)\) | Laban | Body, Effort, Shape, and Space descriptors |
| \(K(t)\) | kinematics | root transform, joints, hands, face parameters, key poses |
| \(\Phi(t)\) | phase | global and local phase or event progress |
| \(Q(t)\) | contact | support, object, interpersonal, and near-contact constraints |
| \(Y(t)\) | dynamics | velocity, acceleration, momentum, force, impulse, balance |
| \(I(t)\) | interaction | actor–actor, actor–object, gaze, target, avoidance relations |
| \(G(t)\) | camera | 6-DoF camera, intrinsics, focus, framing, camera events |
| \(X(t)\) | appearance | identity, costume, lighting, environment, render/style constraints |
| \(O(t)\) | audio | dialogue, prosody, breath, Foley, impact, music synchronization |

The score is heterogeneous. A beat is symbolic, an AU is a continuous curve, a contact is an event interval, and a camera pose is a rigid transform. CPCS does not flatten them prematurely. A compiler translates each track into the target model’s conditioning format.

## 12.2 Canonical Timebase

All tracks share a shot clock. The canonical representation uses seconds plus a rational frame rate:

```yaml
timebase:
  start_s: 0.0
  duration_s: 5.0
  frame_rate:
    numerator: 24
    denominator: 1
  frame_count: 120
  drop_frame: false
```

Events store seconds and may cache frame indices. Seconds remain primary because the same score may be rendered at different frame rates. Resampling must preserve event ordering and contact boundaries.

## 12.3 Hard Constraints, Soft Constraints, and Preferences

Every control has a mode:

- **hard:** must be satisfied within tolerance;
- **soft:** optimized with a specified weight;
- **preference:** used for ranking or sampling but may be violated;
- **diagnostic:** measured but not optimized;
- **derived:** computed from other tracks.

Examples:

| Control | Typical mode |
|---|---|
| exact dialogue lip closure | hard or high-weight soft |
| foot planted during stance | hard/high-weight soft |
| fist–target event at frame 56 | hard |
| negative-valence trajectory | soft |
| “slightly indirect” hand path | preference/soft |
| no identity change | high-weight soft or hard threshold |
| cinematic visual quality | ranking objective |

A conflict resolver checks whether hard constraints are jointly feasible. When they are not, the system returns an explicit conflict report rather than silently ignoring one.

## 12.4 Constraint Graph

CPCS represents dependencies through a directed graph. For example:

```text
recognition beat
  ├── raises arousal
  ├── lowers displayed dominance
  ├── triggers gaze shift to doorway
  ├── triggers AU01/AU02 candidate event
  ├── shortens breath cycle
  └── motivates backward weight shift
          ├── changes support polygon
          ├── delays next step
          └── changes camera framing requirement
```

The graph supports propagation. If the recognition time moves by twelve frames, dependent events move according to relative or elastic timing rules.

## 12.5 Elastic and Fixed Timing

Directors often distinguish fixed sync points from flexible intervals. CPCS supports:

- `fixed`: event time cannot move;
- `relative`: event occurs at an offset from another event;
- `elastic`: interval can stretch within bounds;
- `phase_locked`: event remains at a phase landmark;
- `beat_locked`: event follows a music or dialogue beat;
- `contact_locked`: two actor tracks share one event time.

This allows retiming without destroying coordination.

## 12.6 Score Granularity

CPCS can operate at several levels:

1. **sequence:** multiple scenes and continuity constraints;
2. **scene:** actors, setting, relationships, dramatic arc;
3. **shot:** camera, duration, blocking, performance beats;
4. **beat:** action and intention change;
5. **event:** onset, contact, gaze shift, line, cut;
6. **track sample:** continuous values at time \(t\).

RAG retrieval generally occurs at the beat, action-template, or shot-template level. Low-level samples are generated after retrieval and planning.

## 12.7 Uncertainty and Alternatives

Directorial language is frequently ambiguous. CPCS stores alternatives rather than forcing premature certainty:

```yaml
alternatives:
  - id: "fear_leak.eye_widen"
    probability: 0.42
    rationale: "upper-face leakage while mouth remains controlled"
  - id: "fear_leak.breath_swallow"
    probability: 0.36
    rationale: "subtle lower-face and throat performance"
  - id: "fear_leak.gaze_break"
    probability: 0.22
    rationale: "attention failure rather than overt facial expression"
selection_policy: "director_choose_or_generate_variants"
```

Generating controlled variants is more useful than pretending one interpretation is objectively correct.


<!-- RAG_CHUNK id="cpcs.15" title="Directorial compiler architecture" concepts="compiler, screenplay, RAG, motion planning, verification" -->
<a id="cpcs-compiler"></a>
# 13. From Screenplay to Generated Shot: The Directorial Compiler

## 13.1 Overview

**[PROPOSED]** CPCS treats video generation as a compilation pipeline:

```text
screenplay / storyboard / director note / references
                         │
                         ▼
              semantic scene parser
                         │
                         ▼
       retrieval-augmented performance planner
                         │
                         ▼
             CPCS symbolic shot score
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
 facial/affect planner          body/blocking planner
          │                             │
          └──────────────┬──────────────┘
                         ▼
        motion, contact, and camera solver
                         │
                         ▼
        control-channel compiler / renderer
                         │
                         ▼
      video generator or hybrid render pipeline
                         │
                         ▼
       multimodal compliance and quality verifier
                         │
                 revision / resampling
```

Each stage produces inspectable artifacts. This makes failures localizable and supports production workflows in which different specialists approve different layers.

## 13.2 Stage 1: Semantic Scene Parsing

The parser extracts:

- actors and identities;
- actions and objects;
- spatial relations and environment;
- objectives, obstacles, and subtext;
- explicit and implied affect;
- shot duration and temporal markers;
- camera language;
- dialogue, music, and sound cues;
- safety, identity, licensing, and policy constraints.

It should preserve the original text and link every inferred field to a span or source. Unsupported inferences receive lower confidence.

Example:

```yaml
source_text: "Mara crosses quickly, keeping her voice calm. At the final step she sees the blood and freezes."
parsed:
  actor: "Mara"
  actions:
    - {type: locomotion, primitive: walk, manner: quick}
    - {type: speech, manner: calm}
    - {type: perception, object: blood, time_relation: final_step}
    - {type: freeze, trigger: perception}
  performance_conflict:
    experienced_affect: "rising alarm"
    displayed_affect: "calm"
  temporal_anchor: "recognition aligned to final foot contact"
```

## 13.3 Stage 2: Retrieval-Augmented Grounding

The planner retrieves evidence-labeled templates for:

- facial configurations and event shapes;
- affect trajectories;
- Laban profiles and measurable proxies;
- motion atoms and kinetic chains;
- gait, run, sit, reach, fight, and interaction patterns;
- shot grammar and camera trajectories;
- performer or rig calibration;
- known failure modes.

Retrieval should not simply produce prose. It returns structured candidate plans, source provenance, uncertainty, and compatibility constraints. Section 18 defines the RAG architecture in detail.

## 13.4 Stage 3: Symbolic Performance Planning

The planner creates beats and events before generating dense motion. A beat graph for the example above might be:

```text
B01 move-with-control
  onset 0.00 s, offset 2.45 s
  goal: reach partner
  display: calm, purposeful

B02 recognition
  anchor: final left-foot contact, 2.45 s
  gaze shift begins -0.12 s
  arousal rise begins -0.08 s
  body deceleration begins -0.18 s

B03 involuntary freeze
  onset 2.45 s, apex 2.78 s, release 3.60 s
  breath interruption
  upper-body tension increase
  displayed dominance decreases
```

The planner proposes AU, gaze, Laban, motion, and camera tracks consistent with the beats. A director can edit this symbolic plan before costly video synthesis.

## 13.5 Stage 4: Motion and Contact Solving

A motion system may use one or more methods:

- retrieval from motion-capture libraries;
- motion matching;
- text-to-motion diffusion;
- autoregressive motion models;
- symbolic motion generation such as LabanLite planning;
- inverse kinematics;
- learned interaction generation;
- physics-based control;
- keyframe in-betweening.

HumanDreamer demonstrates the value of decoupling text-to-pose from pose-to-video: pose generation operates in a structured space before pixel synthesis (Wang et al., 2025 [S37]). KeyMotion similarly reflects an animation principle in which sparse key motion is generated before in-betweening (Geng et al., 2024 [S36]). CPCS generalizes this into a multi-track planning stage.

## 13.6 Stage 5: Physical Refinement

The generated motion is checked for:

- foot and hand contacts;
- scene penetration;
- joint limits;
- center-of-mass support;
- prop attachment;
- actor–actor intersections;
- momentum and impact coherence;
- phase consistency;
- temporal alignment to dialogue and camera.

Corrections should preserve high-priority directorial constraints. For example, if exact fist-contact time is fixed, the solver may adjust preparation timing and stance rather than moving contact.

## 13.7 Stage 6: Control-Channel Compilation

The same motion score may be converted into multiple conditions:

- 2D keypoint heatmaps;
- skeletal line renderings;
- DensePose or surface-coordinate maps;
- depth maps;
- surface normals;
- semantic segmentation;
- optical flow or point trajectories;
- facial landmarks or AU embeddings;
- camera ray or Plücker-coordinate embeddings;
- contact masks;
- per-frame text/symbol tokens;
- audio features.

The compiler selects only the channels supported by the target generator. It also records transformations so output can be reprojected into the canonical score for verification.

## 13.8 Stage 7: Video Synthesis

The generator may be:

- text-to-video diffusion or diffusion transformer;
- image-to-video model conditioned on a character reference;
- pose-to-video model;
- video-to-video renderer;
- neural avatar renderer;
- 3D engine followed by generative enhancement;
- world model or scene simulator.

CPCS does not require all control to be injected into one model. A hybrid pipeline can render geometry and motion in 3D, generate photorealistic frames, and apply identity or style refinement afterward.

## 13.9 Stage 8: Verification and Revision

The verifier re-extracts:

- AU curves;
- gaze and head pose;
- body pose and motion;
- contacts;
- camera motion;
- identity and appearance;
- affect estimates;
- action and event completion.

It compares them to the score and returns a structured report:

```yaml
verification:
  overall_status: "revise"
  hard_constraints:
    fist_contact_time:
      target_s: 0.940
      observed_s: 0.982
      error_ms: 42
      tolerance_ms: 20
      status: "fail"
    left_foot_plant:
      mean_slip_m_per_s: 0.014
      tolerance_m_per_s: 0.020
      status: "pass"
  soft_constraints:
    laban_directness:
      target: 0.88
      estimate: 0.74
      status: "under_target"
    displayed_arousal:
      ccc: 0.71
      status: "acceptable"
  visual_quality:
    identity_consistency: 0.93
    temporal_artifact_score: 0.18
  recommended_revision:
    - "increase distal hand-path directness"
    - "shift contact condition 1 frame earlier or regenerate frames 21-26"
```

The verifier must distinguish measurement uncertainty from actual failure.

---

<!-- RAG_CHUNK id="cpcs.16" title="Conditioning AI video models" concepts="diffusion, DiT, control tokens, pose maps, adapters, guidance" -->
<a id="cpcs-conditioning"></a>
# 14. Conditioning Text-to-Video and Image-to-Video Models

## 14.1 Model-Agnostic Conditioning Classes

CPCS controls can enter a generator through six broad mechanisms.

### 14.1.1 Symbolic and text conditioning

The score can be serialized into structured tokens and provided to an LLM, motion language model, or video transformer. MotionGPT treats human motion as a language-like token sequence, illustrating how discrete motion vocabularies can connect text and movement (Jiang et al., 2023 [S35]). Symbolic conditioning is interpretable but depends on the model learning a reliable grounding from symbols to motion.

### 14.1.2 Continuous sequence conditioning

AU curves, VAD trajectories, joint positions, camera poses, and local phases can be embedded as time-indexed tokens:

\[
z_k=E_k(c_k(t)),
\]

where each control family has an encoder \(E_k\). Tokens can be fused through cross-attention, temporal attention, or adaptive normalization.

### 14.1.3 Spatial control maps

Pose, depth, segmentation, normals, and trajectories can be rendered into images aligned with each output frame. Convolutional adapters or ControlNet-like branches inject these maps into a diffusion model. This approach is practical because it reuses spatial inductive biases, but 2D maps may lose depth, occlusion, and camera separation unless accompanied by 3D information.

### 14.1.4 Rig or geometry conditioning

A model can receive 3D body parameters, meshes, Gaussian avatars, neural radiance fields, or engine renders. This provides stronger geometric consistency and supports new views but requires reconstruction, rigging, or an identity representation.

### 14.1.5 Sampling-time guidance

A pretrained generator can be guided by differentiable energies:

\[
\epsilon' = \epsilon_\theta(x_t,c)
-\eta\nabla_{x_t}E(x_t;\mathcal S),
\]

where \(E\) measures deviation from CPCS constraints. LaMoGen’s inference-time optimization of text embeddings toward Laban targets is an example of guidance without additional motion data (Kim et al., 2025 [S33]). Sampling-time guidance is flexible but can be computationally expensive and may trade visual quality against constraint compliance.

### 14.1.6 Post-generation editing

A generated video can be edited using facial reenactment, motion transfer, inpainting, retiming, camera stabilization, or localized resynthesis. Post-editing is valuable for surgical revisions but can introduce temporal seams and may not repair underlying physics.

## 14.2 Spatiotemporal Tokens

A modern diffusion transformer can represent each control as tokens with spatial and temporal location. TokenMotion uses spatiotemporal tokens to enable fine-grained camera and human-motion control and a decouple-and-fuse strategy to handle their interaction (Li et al., 2025 [S38]). CPCS extends this idea by assigning tokens to control families:

```text
[BEAT] [AFFECT] [FACE] [BODY_QUALITY] [JOINT] [PHASE]
[CONTACT] [DYNAMICS] [INTERACTION] [CAMERA] [AUDIO]
```

Each token carries:

- time interval or frame index;
- actor and body region;
- value or embedding;
- priority;
- uncertainty;
- source and provenance;
- mask indicating the spatial region it should affect.

The model can use separate encoders and gated fusion to prevent camera control from overwriting human motion or facial control from altering identity.

## 14.3 Hierarchical Conditioning

Fine controls should not enter at every layer with equal strength. A plausible hierarchy is:

- early or global layers: scene, identity, broad action, camera path;
- middle layers: body pose, motion phase, interaction, depth;
- later or local layers: face, hands, contact details, texture;
- temporal modules: beat, event, rhythm, and continuity controls.

This is an engineering hypothesis, not a universal architecture. The appropriate injection points depend on the model.

## 14.4 Decoupling Motion From Appearance

Directorial revision is easier when appearance and motion are disentangled. FACEGAN uses AUs rather than facial landmarks partly to reduce identity leakage from the driver (Tripathy et al., 2021 [S11]). Similar principles apply to the full body: identity, clothing, and body shape should be held stable while motion controls change.

CPCS stores appearance separately from motion and recommends identity-preserving losses or reference conditioning:

\[
\mathcal L_{id}=1-\cos(E_{id}(V_{gen}),E_{id}(R_{actor})).
\]

For stylized characters, the identity encoder must be appropriate to the style; a face-recognition model trained on photographs is not sufficient.

## 14.5 Camera Conditioning

Camera control requires extrinsics and intrinsics:

\[
G(t)=\{R_c(t),p_c(t),f(t),c_x(t),c_y(t),a(t),z_f(t)\},
\]

where \(R_c,p_c\) are orientation and position; \(f\) is focal length; \((c_x,c_y)\) is principal point; \(a\) can represent aperture; and \(z_f\) is focus distance.

CameraCtrl and MotionCtrl investigate explicit camera and motion control in video generation (He et al., 2024 [S39]; Wang et al., 2024 [S41]). Free-Form Motion Control uses six-degree-of-freedom camera and object poses for independent or joint control (Shuai et al., 2025 [S40]). CPCS uses these developments to define camera as a continuous trajectory with event semantics such as reveal, hold, pan, orbit, rack focus, or impact impulse.

## 14.6 Actor-Relative Camera Grammar

Absolute camera coordinates are inconvenient for direction. CPCS supports actor-relative constraints:

```yaml
camera_event:
  type: "dolly_in"
  subject: "Mara.face"
  start_s: 1.80
  end_s: 3.10
  framing_start: "medium_close_up"
  framing_end: "close_up"
  maintain_eye_line: true
  max_subject_screen_drift_px: 12
  motivation: "recognition beat"
```

The camera solver converts this semantic instruction into a 6-DoF path and lens changes, checking collisions and composition.

## 14.7 Per-Frame Text Versus Structured Events

One possible implementation generates a changing text prompt per frame. This is generally inferior to structured events because language embeddings may not interpolate predictably, and separate prompts can cause identity or scene drift. Per-frame text can supplement, but not replace, continuous control tracks.

A better design binds symbolic event tokens to intervals and uses shared identity and scene context across the shot.

## 14.8 Audio and Performance Synchronization

Dialogue and sound provide strong temporal anchors. CPCS represents phoneme or viseme timing, prosody, breath, Foley, and music beats. Facial expression should be composed with speech rather than layered afterward. Full-body actions may also synchronize to audio: a breath before a sprint, a footstep, a weapon swing, or an impact transient.

An audio-conditioned generator can receive separate streams for:

- lexical content;
- phoneme timing;
- pitch, energy, and rhythm;
- emotional prosody;
- nonverbal vocalizations;
- environmental sound and music beats.

The score maintains source separation so changing a Foley impact does not alter the spoken performance unless intentionally coupled.

---

<!-- RAG_CHUNK id="cpcs.17" title="Training objectives" concepts="loss functions, multimodal constraints, optimization" -->
<a id="cpcs-losses"></a>
# 15. Training and Inference Objectives

## 15.1 Composite Objective

A CPCS-conditioned generator can be trained or guided with a composite loss:

\[
\begin{aligned}
\mathcal L ={}&
\lambda_{gen}\mathcal L_{gen}
+\lambda_{text}\mathcal L_{text}
+\lambda_{pose}\mathcal L_{pose}
+\lambda_{face}\mathcal L_{face}
+\lambda_{aff}\mathcal L_{affect}\\
&+\lambda_{lab}\mathcal L_{Laban}
+\lambda_{phase}\mathcal L_{phase}
+\lambda_{contact}\mathcal L_{contact}
+\lambda_{phys}\mathcal L_{physics}\\
&+\lambda_{int}\mathcal L_{interaction}
+\lambda_{cam}\mathcal L_{camera}
+\lambda_{id}\mathcal L_{identity}
+\lambda_{temp}\mathcal L_{temporal}.
\end{aligned}
\]

The terms should not all be active at equal weight. Hard constraints may be enforced by projection or solver stages rather than soft losses. Curriculum training can introduce controls gradually.

## 15.2 Face Compliance Loss

Given target AU curves \(u_i(t)\) and estimates \(\hat u_i(t)\):

\[
\mathcal L_{AU}=\frac{1}{T|\mathcal U|}
\sum_{t,i}w_i(t)|\hat u_i(t)-u_i(t)|.
\]

Temporal event loss compares onset, apex, and offset boundaries. Asymmetry loss is applied only when symmetry or asymmetry is explicitly specified.

## 15.3 Pose and Motion Loss

Position error can use mean per-joint position error after an appropriate alignment:

\[
\mathcal L_{MPJPE}=\frac{1}{TJ}\sum_{t,j}
\|\hat p_{j,t}-p_{j,t}\|_2.
\]

For directorial control, root-aligned MPJPE alone is inadequate because it can ignore blocking. CPCS reports both root-relative and world-space errors, along with orientation and timing.

Velocity and acceleration losses preserve dynamics:

\[
\mathcal L_{vel}=\frac{1}{TJ}\sum_{t,j}
\|\Delta\hat p_{j,t}-\Delta p_{j,t}\|_2,
\]

\[
\mathcal L_{acc}=\frac{1}{TJ}\sum_{t,j}
\|\Delta^2\hat p_{j,t}-\Delta^2p_{j,t}\|_2.
\]

## 15.4 Phase Loss

Circular phase error should account for wraparound:

\[
\mathcal L_{phase}=1-\cos\big(2\pi(\hat\phi-\phi)\big).
\]

For local phases, losses are weighted by relevant body parts and contact states.

## 15.5 Contact and Interaction Loss

Contact loss combines temporal classification and spatial constraints:

\[
\mathcal L_Q=
\lambda_{cls}\operatorname{BCE}(\hat q,q)
+\lambda_{dist}\sum_{t\in Q}\|\hat d(t)-d^*(t)\|^2
+\lambda_{slip}\mathcal L_{plant}.
\]

Interaction loss applies to actor–actor or actor–object joint pairs. It can include minimum-distance, target-direction, and visibility conditions.

## 15.6 Laban Loss

A learned or analytic Laban estimator \(E_L\) produces qualities from motion:

\[
\mathcal L_{Laban}=d(E_L(M),L^*).
\]

Because Laban labels are qualitative and may be coder-dependent, training should use multiple annotators where possible and model label uncertainty. A distributional loss or ordinal regression may be more appropriate than exact scalar regression.

## 15.7 Camera Loss

Camera trajectory error can be measured in translation and geodesic rotation distance:

\[
\mathcal L_{cam}=\lambda_t\|\hat p_c-p_c\|_2^2
+\lambda_r\arccos\left(\frac{\operatorname{tr}(\hat R_cR_c^\top)-1}{2}\right)^2.
\]

Composition losses can track subject screen position, size, headroom, and visibility.

## 15.8 Constraint Scheduling

High guidance at all times can reduce realism or diversity. CPCS permits event-dependent scheduling:

- strengthen contact guidance near impact;
- strengthen identity guidance during occlusion recovery;
- strengthen face guidance in close-up frames;
- reduce jerk penalty during intended sudden actions;
- strengthen camera control during a reveal or match move.

This scheduling follows the score rather than a fixed global weight.


<!-- RAG_CHUNK id="cpcs.18" title="Data and annotation strategy" concepts="datasets, FACS annotation, motion capture, weak supervision, licensing" -->
<a id="cpcs-data"></a>
# 16. Data, Annotation, and Calibration

## 16.1 Why No Single Dataset Is Sufficient

A CPCS-capable system requires variables that are rarely captured together. Facial datasets may contain Action Units but crop out the body. Motion-capture datasets may contain joint trajectories but no face, camera, voice, affect, or cinematic context. Film footage contains rich performance but lacks 3D ground truth, licensed identity controls, and precise contact annotations. Synthetic datasets can provide geometry and camera parameters but may lack realistic behavior.

A practical system therefore combines datasets through a common score and explicit missing-data masks. Training should not fabricate labels for absent modalities.

## 16.2 Desired Synchronized Capture

An ideal research capture would include:

- calibrated multi-view video;
- face and body motion capture;
- hand and eye tracking;
- audio with phoneme and prosody alignment;
- FACS coding with temporal boundaries and intensity;
- VAD ratings from performer, director, and observers;
- Laban coding by trained analysts;
- body action/posture annotation;
- scene geometry and prop pose;
- contact sensors or reliable contact labels;
- force plates or inertial estimates for selected actions;
- camera extrinsics, intrinsics, and lens metadata;
- script, objectives, subtext, and director notes;
- multiple takes under controlled performance variations;
- consent, license, identity, demographic, and usage metadata.

The most valuable experimental design is not merely “many actions.” It contains **controlled contrasts**: the same actor performs the same blocking with different affect, Laban qualities, facial masking, timing, and camera treatment. These contrasts help the model disentangle action identity from expressive style.

## 16.3 Existing Data Sources

Relevant data families include:

- facial AU datasets such as DISFA and other FACS-annotated corpora (Mavadati et al., 2013 [S04]);
- affect datasets such as AffectNet with categorical and dimensional labels (Mollahosseini, Hasani, & Mahoor, 2017 [S03]);
- motion collections normalized through AMASS (Mahmood et al., 2019 [S27]);
- text–motion datasets such as HumanML3D (Guo et al., 2022 [S29]);
- motion-language and action datasets used by diffusion or token models;
- interaction and human–object datasets with contact or scene context;
- pose-to-video and human-video datasets;
- synthetic camera/object datasets such as SynFMC (Shuai et al., 2025 [S40]).

**[CAUTION]** Dataset terms, subject consent, biometric restrictions, model-release terms, and commercial-use rights vary. A RAG or training pipeline must retain dataset-level and item-level license metadata. “Available online” does not imply permission for unrestricted model training or identity synthesis.

## 16.4 Annotation Protocol

CPCS annotation proceeds in passes.

### Pass 1: objective measurements

- timestamps and frame rate;
- camera calibration;
- 2D/3D pose;
- face landmarks and candidate AUs;
- object pose;
- audio alignment;
- estimated contacts.

### Pass 2: trained behavioral coding

- FACS events and intensity;
- BAP-style body actions and postures;
- Laban BESS descriptors;
- gaze and interaction functions.

### Pass 3: directorial and narrative coding

- beat boundaries;
- objectives and obstacles;
- experienced versus displayed affect;
- intended audience information;
- shot function and camera motivation.

### Pass 4: verification

- inter-rater agreement;
- adjudication;
- uncertainty distributions;
- calibration against physical measurements;
- cross-modal consistency checks.

Automated estimators can pre-annotate, but trained human review is required for high-quality reference material.

## 16.5 Annotation Uncertainty

CPCS stores distributions or intervals where labels are uncertain:

```yaml
annotation:
  laban:
    space:
      mean: 0.64
      std: 0.18
      coders: 3
  au04:
    onset_s:
      interval: [1.18, 1.25]
      adjudicated: false
  contact:
    time_s:
      mean: 2.047
      tolerance_s: 0.012
      sensor_supported: true
```

Training can weight examples by confidence. Evaluation should not penalize a model for falling within a credible annotation interval.

## 16.6 Performer and Rig Calibration

The same normalized control can look different on different bodies and rigs. A calibration session should include:

- neutral pose and facial baseline;
- AU range and visibility thresholds;
- head, eye, jaw, hand, and joint ranges;
- gait and run at several speeds;
- representative Laban contrasts;
- reach envelopes;
- balance and contact behavior;
- costume or equipment constraints;
- voice and breathing baselines.

The resulting profile maps canonical CPCS values to performer-specific realization. Calibration is especially important for stylized, nonhuman, disabled, injured, elderly, child, or otherwise non-normative characters. The goal is not to normalize everyone toward one dataset average.

## 16.7 Weak and Synthetic Supervision

Film and web video can provide broad motion and cinematography examples through estimated pose, optical flow, camera motion, and language descriptions. These labels are noisy and should be stored as pseudo-labels with estimator version and confidence.

Synthetic data offers exact camera, depth, segmentation, contact, and object pose. Its limitations include motion style, texture realism, facial subtlety, and simulator bias. Domain randomization and generative appearance transfer can help, but synthetic and real distributions should be evaluated separately.

## 16.8 Counterfactual and Paired Data

CPCS benefits from paired examples differing in one control:

- same motion, different Laban Weight;
- same AU combination, different timing;
- same affect, different masking strategy;
- same choreography, different camera;
- same camera, different actor motion;
- same contact time, different impulse;
- same line reading, different displayed dominance.

Such pairs support causal interpretation of controls and reduce entanglement.

---

<!-- RAG_CHUNK id="cpcs.19" title="RAG architecture" concepts="RAG, knowledge base, hybrid retrieval, provenance, chunking" -->
<a id="cpcs-rag"></a>
# 17. Retrieval-Augmented Performance Direction

## 17.1 Purpose of RAG in CPCS

RAG is not used merely to make prompts longer. It performs four technical functions:

1. retrieve relevant scientific or production knowledge;
2. retrieve executable performance and shot templates;
3. preserve provenance and uncertainty;
4. constrain an LLM planner to representations supported by the production’s models, rigs, and rights.

The retrieval system should distinguish knowledge about human behavior from creative conventions and from project-specific assets.

## 17.2 Knowledge Object Types

CPCS defines six primary object types.

### 17.2.1 Concept card

A self-contained explanation of a construct such as AU onset, Laban Flow, motion phase, support polygon, or camera extrinsics.

### 17.2.2 Evidence card

A claim linked to one or more primary sources, with evidence level, population, method, and limitations.

### 17.2.3 Performance template

A reusable, editable score fragment such as “suppressed startle,” “hesitant approach,” “heavy run stop,” or “restrained right cross.” Templates include tracks and dependencies, not only prose.

### 17.2.4 Shot template

A camera and editing plan associated with a dramatic function, such as reveal, subjective uncertainty, power reversal, or impact readability.

### 17.2.5 Calibration profile

Mappings from canonical values to a specific performer, rig, model, lens package, or control adapter.

### 17.2.6 Failure card

A known failure pattern, detector, likely cause, and repair strategy—for example, foot skating after a camera orbit, AU drift during speech, hand–prop detachment, or reaction preceding contact.

## 17.3 Required Metadata

Each retrieval object should include:

```yaml
id: "perf.hesitant_approach.v2"
type: "performance_template"
title: "Hesitant approach with controlled display"
summary: "Forward locomotion with delayed commitment and intermittent gaze."
canonical_terms:
  - hesitant approach
aliases:
  - reluctant walk forward
  - cautious advance
actors: 1
actions:
  - walk
body_parts:
  - root
  - feet
  - pelvis
  - head
  - eyes
affect_range:
  valence: [-0.7, -0.1]
  arousal: [0.2, 0.7]
  dominance: [-0.4, 0.4]
laban_range:
  weight: [-0.2, 0.5]
  time: [-0.6, 0.3]
  space: [-0.4, 0.5]
  flow: [0.1, 0.8]
contacts:
  - left_foot_ground
  - right_foot_ground
duration_s: [1.5, 8.0]
evidence_level: "mixed_research_and_creative_template"
source_ids:
  - S16
  - S20
  - S22
license:
  template: "project_defined"
  references: "citation_only"
model_compatibility:
  - text_to_motion
  - pose_to_video
  - 3d_rig
version: 2
created_at: "2026-07-18"
```

Metadata enables filtering before semantic ranking.

## 17.4 Chunking Strategy

RAG chunks should be self-contained and scoped to one concept or operation. Recommended properties are:

- 400–900 tokens per conceptual chunk;
- stable chunk identifier;
- heading path;
- concise summary and canonical terms;
- explicit evidence label;
- source identifiers;
- no unresolved pronouns that depend on distant context;
- tables retained with their explanatory text;
- code blocks kept intact;
- equations accompanied by prose definitions.

This paper includes `RAG_CHUNK` comments and a companion JSONL export to support such ingestion.

## 17.5 Hybrid Retrieval

A robust query pipeline combines:

1. **structured filtering:** actor count, action, body part, contact, duration, rig, camera, evidence level;
2. **lexical retrieval:** exact AU, Laban, body-part, or shot terms;
3. **dense retrieval:** semantic similarity to the director’s language;
4. **graph expansion:** dependencies and related concepts;
5. **cross-encoder or LLM reranking:** compatibility with the full scene;
6. **diversity selection:** alternative interpretations rather than near duplicates.

A retrieval score can be written:

\[
R(o|q)=
\alpha R_{lex}
+\beta R_{dense}
+\gamma R_{struct}
+\delta R_{graph}
+\eta R_{provenance}
-\rho R_{conflict}.
\]

The provenance term favors primary, well-matched sources; the conflict term penalizes incompatible contacts, timing, model capabilities, or licenses.

## 17.6 Query Decomposition

The instruction “walks toward him fast but tries not to look frightened” should be decomposed into retrieval subqueries:

- locomotion template: fast walk, approach;
- affect: negative valence, elevated arousal;
- display regulation: experienced/displayed divergence;
- face: subtle leakage alternatives;
- body quality: controlled or bound versus urgent;
- interaction: gaze and interpersonal distance;
- camera: framing that can reveal subtle leakage.

Retrieving one monolithic example risks importing irrelevant details. The planner composes compatible fragments and checks conflicts.

## 17.7 Provenance and Evidence Separation

A knowledge base must not merge the following into one undifferentiated embedding space without metadata:

- peer-reviewed empirical findings;
- coding-manual definitions;
- computational proxy definitions;
- production heuristics;
- director-specific style preferences;
- model-specific prompt tricks;
- generated hypotheses.

Every derived plan should carry a provenance trace:

```yaml
provenance:
  narrative_source: "script.scene_12.line_48"
  affect_inference:
    method: "planner_v3"
    confidence: 0.74
  facial_template:
    object_id: "face.suppressed_startle.v1"
    source_ids: [S01, S05, S09]
  motion_template:
    object_id: "motion.quick_walk_stop.v4"
    source_ids: [S22, S23]
  director_overrides:
    - "remove overt eye widening"
    - "hold gaze on partner until final step"
```

## 17.8 Retrieval Verification Checkpoints

A deterministic workflow should expose checkpoints:

**Checkpoint A: retrieval coverage.** Confirm that every requested action, body part, contact, camera event, and affect transition has at least one candidate object.

**Checkpoint B: source validity.** Confirm that research claims resolve to stored citations and that templates are licensed for the intended use.

**Checkpoint C: compatibility.** Confirm matching skeleton, rig, actor count, duration, environment, and target generator.

**Checkpoint D: conflict report.** List contradictory constraints before generation.

**Checkpoint E: compiled score diff.** Show which retrieved values were accepted, modified, or rejected by the planner.

## 17.9 RAG Security and Contamination Controls

Retrieved documents may contain malformed instructions or untrusted text. The system should treat the knowledge base as data, not authority to modify system behavior. It should also:

- sanitize executable content;
- isolate project-private assets;
- enforce access controls;
- prevent retrieval across incompatible identity-consent scopes;
- retain source hashes and version history;
- support deletion and revocation;
- distinguish generated annotations from human-coded ground truth.

## 17.10 RAG Output Contract

The RAG planner should return structured candidates rather than a final untraceable answer:

```json
{
  "query_id": "shot_12_beat_03",
  "candidates": [
    {
      "object_id": "face.suppressed_startle.v1",
      "score": 0.87,
      "evidence_level": "mixed",
      "source_ids": ["S01", "S05", "S09"],
      "compatible": true,
      "required_adaptations": ["reduce AU intensity for close-up"]
    }
  ],
  "coverage": {
    "face": true,
    "body": true,
    "contacts": true,
    "camera": false
  },
  "unresolved": ["camera plan requires director or shot-template selection"]
}
```

This contract supports testing and prevents the LLM from silently inventing missing control data.

---

<!-- RAG_CHUNK id="cpcs.20" title="CPCS machine-readable schema" concepts="YAML, JSON schema, score format, control tracks" -->
<a id="cpcs-schema"></a>
# 18. Machine-Readable CPCS Schema

## 18.1 Top-Level Structure

The following YAML is an illustrative schema instance. A production implementation should validate it with JSON Schema, Protocol Buffers, Pydantic, or an equivalent typed system.

```yaml
cpcs_version: "1.0"
score_id: "filmA.scene12.shot04"
source:
  script_id: "filmA.scene12"
  storyboard_panel_ids: ["p12-08", "p12-09"]
  director_notes:
    - "Fear becomes visible only at the last step."
    - "Do not lose eye contact before recognition."

status:
  stage: "approved_for_motion_generation"
  evidence_policy: "primary_sources_preferred"

sequence:
  fps: 24
  duration_s: 4.0
  frame_count: 96
  coordinate_system: "right_handed_y_up_meters"

actors:
  - actor_id: "mara"
    identity_ref: "asset.actor.mara.v3"
    body_model: "smplx_2020"
    rig_profile: "rig.mara.v5"
    consent_scope: "project_filmA"
  - actor_id: "jon"
    identity_ref: "asset.actor.jon.v2"
    body_model: "smplx_2020"
    rig_profile: "rig.jon.v4"
    consent_scope: "project_filmA"

scene:
  geometry_ref: "set.lab_corridor.v7"
  gravity_m_s2: [0.0, -9.81, 0.0]
  ground_surface: "floor_main"
  props: []

beats:
  - beat_id: "b01.approach"
    start_s: 0.0
    end_s: 2.45
    action: "mara approaches jon"
    objective: "maintain composure"
    subtext: "rising fear"
  - beat_id: "b02.recognition"
    start_s: 2.45
    end_s: 2.82
    action: "mara sees blood"
    objective: "process without revealing panic"
  - beat_id: "b03.freeze"
    start_s: 2.82
    end_s: 4.0
    action: "mara stops and contains reaction"

tracks:
  affect:
    - actor_id: "mara"
      type: "VAD"
      experienced_knots:
        - [0.00, -0.20, 0.30, 0.55]
        - [2.40, -0.38, 0.54, 0.48]
        - [2.78, -0.78, 0.91, 0.08]
        - [4.00, -0.60, 0.65, 0.30]
      displayed_knots:
        - [0.00, -0.05, 0.18, 0.68]
        - [2.40, -0.10, 0.24, 0.66]
        - [2.78, -0.38, 0.57, 0.30]
        - [4.00, -0.22, 0.40, 0.48]

  face:
    - actor_id: "mara"
      au_events:
        - au: "AU04"
          side: "bilateral"
          onset_s: 2.50
          apex_in_s: 2.74
          apex_out_s: 3.05
          offset_s: 3.52
          peak: 0.28
          mode: "soft"
        - au: "AU05"
          side: "bilateral"
          onset_s: 2.48
          apex_in_s: 2.67
          apex_out_s: 2.78
          offset_s: 3.10
          peak: 0.18
          mode: "soft"
      gaze_events:
        - start_s: 0.0
          end_s: 2.34
          target: "jon.eyes"
        - start_s: 2.34
          end_s: 2.76
          target: "jon.shirt.blood"
        - start_s: 2.76
          end_s: 4.0
          target: "jon.eyes"
      blink_events:
        - {start_s: 3.28, duration_s: 0.14, type: "single"}

  laban:
    - actor_id: "mara"
      interval_s: [0.0, 2.45]
      effort:
        weight: 0.20
        time: 0.68
        space: 0.70
        flow: 0.64
      shape:
        rise_sink: 0.05
        spread_enclose: -0.10
        advance_retreat: 0.72
      body:
        initiation: "pelvis"
        organization: "integrated"
    - actor_id: "mara"
      interval_s: [2.45, 4.0]
      effort:
        weight: 0.46
        time: 0.82
        space: 0.76
        flow: 0.88
      shape:
        rise_sink: -0.18
        spread_enclose: -0.42
        advance_retreat: -0.12
      body:
        initiation: "upper_torso"
        organization: "contained"

  blocking:
    - actor_id: "mara"
      root_path:
        type: "bezier"
        points_m:
          - [-2.4, 0.0, 0.3]
          - [-1.6, 0.0, 0.1]
          - [-0.8, 0.0, 0.0]
          - [-0.55, 0.0, 0.0]
      arrival_s: 2.45
      facing_target: "jon.pelvis"

  phase:
    - actor_id: "mara"
      controller: "locomotion_global_plus_local"
      contact_anchors:
        - {time_s: 0.18, effector: "left_foot", event: "initial_contact"}
        - {time_s: 0.72, effector: "right_foot", event: "initial_contact"}
        - {time_s: 1.28, effector: "left_foot", event: "initial_contact"}
        - {time_s: 1.84, effector: "right_foot", event: "initial_contact"}
        - {time_s: 2.45, effector: "left_foot", event: "final_plant"}

  contacts:
    - contact_id: "mara.left_foot.final_plant"
      actor_a: "mara"
      region_a: "left_foot"
      actor_b: "scene"
      region_b: "floor_main"
      start_s: 2.45
      end_s: 4.0
      type: "support"
      mode: "hard"
      max_slip_m_s: 0.02

  camera:
    coordinate_mode: "world_6dof"
    lens_mm: 50
    trajectory_ref: "camera.shot04.solve.v2"
    semantic_events:
      - type: "tracking_medium"
        interval_s: [0.0, 2.20]
        subject: "mara"
      - type: "dolly_in"
        interval_s: [2.20, 3.20]
        subject: "mara.face"
        framing_end: "close_up"
      - type: "hold"
        interval_s: [3.20, 4.0]
        max_screen_drift_px: 10

  audio:
    dialogue_ref: "audio.scene12.mara.line03.v4"
    breath_events:
      - {time_s: 2.73, type: "inhalation_interrupt", mode: "soft"}

constraints:
  - id: "recognition_on_final_step"
    expression: "beat:b02.start == contact:mara.left_foot.final_plant.start"
    mode: "hard"
    tolerance_s: 0.02
  - id: "no_early_gaze_break"
    expression: "gaze:mara.target == jon.eyes until 2.34"
    mode: "hard"
  - id: "identity_preservation"
    target: "mara"
    mode: "hard_threshold"
    minimum_score: 0.90

provenance:
  planner_model: "performance_planner_v3"
  retrieved_objects:
    - "perf.controlled_approach.v2"
    - "face.suppressed_startle.v1"
    - "shot.recognition_dolly.v3"
  source_ids: ["S01", "S05", "S20", "S22", "S37", "S38"]
```

## 18.2 Schema Design Principles

The schema follows eight principles:

1. **time is explicit;**
2. **actors and body regions are addressable;**
3. **semantic and numeric forms coexist;**
4. **constraints have priority and tolerance;**
5. **provenance is retained;**
6. **uncertainty is representable;**
7. **model-specific values remain in calibration profiles;**
8. **the original directorial language is never discarded.**

## 18.3 Validation

A score validator should test:

- schema types and required fields;
- time ranges and frame counts;
- reference resolution;
- actor and body-part existence;
- monotonic event times;
- contact-pair validity;
- hard-constraint feasibility;
- camera and geometry coordinate consistency;
- source and license completeness;
- model-compatibility requirements.

A valid schema is not necessarily a feasible motion plan. Feasibility requires motion and physical solvers.


<!-- RAG_CHUNK id="cpcs.structured-languages" title="Structured prompt languages and compiler architecture" concepts="YAML, JSON, XML, prompt structure, canonical intermediate representation, compiler, model conditioning" -->
<a id="cpcs-structured-prompting"></a>
# 19. Structured Prompt Languages, Style Inheritance, and Directorial Compilation

## 19.1 The Essential Distinction: Serialization Is Not Control

A structured document can make direction easier to author, validate, retrieve, revise, and translate. It does not automatically make a video generator obey that direction. YAML, JSON, and XML are **data-serialization or markup languages**. They describe how information is written and exchanged. They do not, by themselves, define the cinematic meaning of `AU04`, `bound_flow`, `impact_frame`, or `hero_product_reveal`.

JSON is standardized as a lightweight, text-based, language-independent interchange format with objects, arrays, strings, numbers, booleans, and null. Its objects are unordered collections, while arrays are ordered sequences (Bray, 2017 [S51]). YAML defines mappings, sequences, scalars, tags, anchors, and aliases; its mapping-key order is not part of the application-level representation, and anchors are serialization devices rather than a general inheritance language (YAML Language Development Team, 2021 [S53]). XML defines a textual document syntax built from elements, attributes, character data, and related constructs, while XML namespaces qualify names so that multiple vocabularies can coexist without collisions (Bray et al., 2008 [S54]; Bray et al., 2009 [S55]). These standards define syntax and data models, not a video-directing ontology.

The user-facing statement that “video models are AI and understand machine codes” must therefore be separated into several technically different claims:

1. **Software understands an API protocol.** A service receives bytes over a documented interface, parses fields, checks types, and transfers accepted values to an inference system.
2. **A text encoder tokenizes a prompt.** Characters such as braces, indentation, or XML tags become token IDs. Tokenization does not guarantee that those tokens acquire the intended formal semantics.
3. **A multimodal model consumes tensors.** Text tokens, image latents, audio features, masks, pose maps, or other controls are converted into numerical arrays. These tensors are machine-readable, but they are not CPU “machine code” and are not automatically equivalent to a director’s score.
4. **A model may have learned conventions.** If training data exposed the model to tagged shot descriptions or if an LLM front end was instructed to parse a schema, structured syntax may improve separation and consistency. The result remains probabilistic unless a deterministic parser and adapter enforce the semantics.
5. **A compiler can create actual control.** Software can map a validated field such as `duration_s: 6` to a native duration parameter, map a camera path to a supported trajectory input, render an AU curve into facial landmarks, or reject an unsupported control. This is the strongest meaning of “structured prompting” used in CPCS.

**[PROPOSED]** CPCS defines control as the existence of a documented transformation from a source field to one or more target conditions, plus a verification method. Formally, for a source control field \(x\), target adapter \(A\), and generated artifact \(Y\), directability requires:

\[
A(x) \rightarrow \{z_1, z_2, \ldots, z_k\},
\]

where each \(z_j\) is a supported prompt clause, API parameter, control asset, latent condition, simulation target, compositor operation, or evaluation constraint. The system must also record whether the mapping was exact, approximate, baked into a reference, reduced to prose, or unsupported.

A raw object such as the following may be visually clear to a human yet have no formal effect when pasted into an ordinary prompt box:

```json
{
  "facs": {"AU04": 0.35},
  "laban": {"time": "sudden", "flow": "bound"},
  "camera": {"move": "dolly_in"}
}
```

If the video endpoint accepts only one prompt string, the model may interpret the property names as text, ignore some of them, or generalize from similar examples. The braces are not an executable command. By contrast, a CPCS compiler can transform the same object into a prose shot description, a facial-control pass, a motion-style condition, a camera trajectory, and a compliance test. The difference is not punctuation; it is the presence of a semantic contract and an implementation.

## 19.2 Four Ways Structured Direction Can Reach a Video Generator

Structured direction can be used in four increasingly explicit modes. A production system should state which mode is active because their reliability differs.

### 19.2.1 Mode A: Structured Text Pasted Directly Into a Prompt Field

The simplest mode places YAML, JSON, XML, or a tag-like block inside a natural-language prompt. For example:

```xml
<shot>
  <performance>restrained fear</performance>
  <face>AU04 low; AU05 trace; eye contact maintained</face>
  <body>bound flow; sustained time; direct path</body>
  <camera>slow dolly-in to close-up</camera>
</shot>
```

This can improve human organization and may help a language-conditioned model distinguish subject, action, camera, lighting, and timing. It is still **prompt rhetoric**, not schema enforcement. The model may conflate fields, ignore numeric values, reinterpret tags, or invent unspecified details. This mode is appropriate for rapid exploration and should be labeled `text_interpretation_only` in the compile report.

### 19.2.2 Mode B: LLM-Mediated Interpretation

An LLM reads the structured source, checks or repairs it, and produces a target prompt or set of tool calls. This approach can translate flexible directorial language into stricter fields and can reason about conflicts. Its weaknesses are non-deterministic interpretation, possible field omission, and dependence on the LLM’s context and instructions.

A robust LLM-mediated system should require structured output against a schema, compare the output with the input, and generate an explicit loss report. The LLM is then a planner or semantic translator, not the final authority for units, IDs, merge precedence, or hard constraints.

### 19.2.3 Mode C: Deterministic Compiler and Workflow Engine

A deterministic compiler parses the source, resolves imports and inheritance, validates types and units, produces a canonical intermediate representation, negotiates target capabilities, and emits model-specific inputs. This mode can guarantee that `duration_s` becomes the correct API field, that temporal arrays remain ordered, that a locked identity reference is not silently replaced, and that unsupported AU tracks raise a warning or error.

Determinism here concerns the **translation process**, not necessarily the generated video. A stochastic video model may still produce different pixels or motion across runs. The compiler can nevertheless make the requested conditions, target version, random seed where available, assets, and provenance reproducible.

### 19.2.4 Mode D: Native Structured Conditioning

The strongest model-level control occurs when the target system natively accepts the relevant condition: first and last frames, pose sequences, depth, masks, camera trajectories, keyframes, reference images, audio, motion paths, or learned control tokens. In this case, the compiler maps CPCS fields directly to documented channels rather than compressing them into prose.

Native support is field-specific. A model may natively accept duration and aspect ratio but not Action Unit curves; it may accept first and last frames but not an arbitrary 6-DoF camera path; it may accept a pose video but not a Laban vector. A correct adapter advertises capabilities at the granularity of control fields rather than describing the whole model as simply “controllable.”

## 19.3 The Three-Representation Architecture

**[PROPOSED]** A CPCS production pipeline should separate three representations and one evidence stream:

```text
Authoring Source Layer (ASL)
YAML, XML, screenplay text, storyboard references, measured JSON tracks
                         │
                         ▼
Canonical Intermediate Representation (CIR)
fully resolved, typed, unit-normalized CPCS JSON
                         │
                         ▼
Target Execution Package (TEP)
model request JSON + prompt text + media/control assets + post/VFX/edit plan
                         │
                         ▼
Verification Evidence Records (VER)
JSONL events, extracted tracks, metric results, violations, provenance
```

The **Authoring Source Layer** optimizes for humans and department workflows. It may contain comments, named style profiles, external references, prose notes, and concise defaults. YAML is usually the most readable source for project and shot configuration. XML is useful when ordered narrative, dialogue, annotations, and multiple domain vocabularies must coexist. JSON is suitable for measured or generated tracks and for tools that already emit structured data.

The **Canonical Intermediate Representation** is the single source of truth used by compilers. It contains no unresolved YAML anchors, implicit units, ambiguous aliases, duplicate keys, or inherited values. Every effective value is explicit and has provenance. JSON is a practical canonical format because of its broad tooling and JSON Schema support, but CPCS semantics—not JSON syntax—define the representation. JSON Schema Draft 2020-12 supplies vocabularies for structural validation, reusable definitions, references, and composition (Bhutton et al., 2022 [S52]).

The **Target Execution Package** contains only what a selected backend can consume. A prompt-only backend may receive a prompt string plus duration and aspect ratio. A pose-conditioned backend may receive the prompt plus a frame-indexed pose video. A 3D-to-video pipeline may receive rendered depth, normals, segmentation, optical flow, camera metadata, identity references, and audio. A compositing backend may also receive particles, masks, time-remapping instructions, and title-card assets.

The **Verification Evidence Record** is intentionally append-oriented. JSONL works well here because each event, metric interval, generation candidate, or RAG record can be stored as an independently parsable line. It is not the preferred canonical format for a deeply nested shot because reconstructing hierarchy across lines adds complexity.

The separation yields two important invariants:

- **No backend syntax leaks into the conceptual score unless it is namespaced as an adapter extension.** A director should not have to rewrite FACS, Laban, or beat timing whenever a model changes.
- **No unsupported control disappears silently.** The compiler reports how every control was realized or why it could not be realized.

## 19.4 A Typed Control Ontology for Directing Performance, Action, Presentation, and Marketing

The control-layer table in Section 3.7 answers what each layer controls. A compiler additionally needs field-level contracts. The following is a minimal ontology. Each record has an identifier, scope, time range, value, units or vocabulary, strength, merge policy, provenance, and compilation targets.

```yaml
control:
  id: "shot014.mara.face.au04"
  domain: "performance.face.facs"
  actor_id: "mara"
  interval: {start_s: 2.50, end_s: 3.52}
  value:
    action_unit: "AU04"
    side: "bilateral"
    curve: [[2.50, 0.00], [2.74, 0.28], [3.05, 0.28], [3.52, 0.00]]
  strength: "hard_target_soft_tolerance"
  tolerance: {intensity_mae: 0.08, apex_time_s: 0.06}
  merge: "replace_track"
  provenance:
    authored_by: "performance_director"
    source_note: "fear leaks only after recognition"
  compile_to:
    - "face_rig_curve"
    - "facial_landmark_condition"
    - "prompt_summary"
    - "verification_target"
```

The same shape can represent Laban, action, camera, VFX, or marketing controls while preserving domain-specific value schemas. A combat action record, for example, contains preparation, execution, contact or near-contact, follow-through, and recovery phases. A director-control record contains camera or editorial values. A marketing-control record contains a communication requirement and measurement hypothesis rather than a bodily state.

### 19.4.1 FACS Control Contract

A FACS record should identify the actor, Action Unit, side, calibrated intensity curve, onset/apex/offset or knots, confidence, and intended visibility at the planned shot scale. It can compile to:

- a facial rig curve where a calibrated AU-to-rig map exists;
- blendshape mixtures, with an explicit warning that AUs and blendshapes are not inherently one-to-one;
- facial landmarks, normals, or expression reference images;
- a textual summary for prompt-only models;
- an extraction target used after generation.

The compiler must retain the difference between “AU intended by the director” and “rig parameter used to approximate that AU.”

### 19.4.2 Laban Control Contract

A Laban record contains Body, Effort, Shape, and Space descriptors over an interval. Qualitative poles may be accompanied by calibrated continuous values. It can compile to:

- retrieval constraints for selecting compatible motion clips;
- a learned motion-style embedding;
- trajectory amplitude, acceleration profile, release, directness, and retiming modifiers;
- prompts for motion or video models;
- perceptual evaluation questions.

It should not be compiled directly into an objective force or torque without a calibrated mapping. “Strong Weight” is a perceptual or movement-quality instruction, not a universal Newton value.

### 19.4.3 Combat and Action Control Contract

An action unit in the choreography sense—distinct from a facial Action Unit—can be represented as an **action atom**:

```yaml
action_atom:
  id: "fight01.astra.right_cross"
  verb: "punch_like_strike"
  actor: "astra"
  target: "opponent.head_volume"
  safety_mode: "staged_near_contact"
  phases:
    preparation: [1.10, 1.32]
    execution: [1.32, 1.58]
    near_contact: [1.58, 1.60]
    follow_through: [1.60, 1.78]
    recovery: [1.78, 2.20]
  support:
    planted_effectors: ["left_foot"]
  local_phase_order:
    - "rear_foot_pivot"
    - "pelvis_rotation"
    - "torso_rotation"
    - "right_shoulder"
    - "right_elbow"
    - "right_fist"
  minimum_separation_m: 0.025
```

The atom can compile to a motion-graph query, key poses, body-part phase tracks, target and avoidance constraints, simulation goals, camera readability constraints, and reaction timing. It is a choreography representation, not advice for real-world violence.

### 19.4.4 Director and Editorial Control Contract

Director controls specify how performance becomes audience experience. They include shot size, camera height, angle, lens, focus, movement, screen direction, reveal, cut, duration, speed ramp, slow motion, reaction timing, and impact framing. These controls compile into camera intrinsics/extrinsics, framing objectives, visibility constraints, time mapping, and edit decision lists.

Slow motion requires two time bases:

- **performance or simulation time** \(\tau\), in which the action remains physically coherent;
- **presentation time** \(t\), in which frames are displayed.

A monotonic mapping \(\tau = w(t)\) permits a speed ramp without changing the causal order of foot plant, strike, reaction, and recovery. A one-frame “impact frame” can be represented as a presentation event—frame hold, repeated frame, stylized insertion, or exposure change—without falsely changing the underlying contact duration.

### 19.4.5 VFX and Anime Control Contract

VFX/anime controls specify stylization events such as speed lines, energy trails, dust bursts, camera shake, smear frames, impact flashes, held frames, line boil, or chromatic separation. Each effect record should contain:

- trigger event or time range;
- source actor, body part, or contact;
- spatial attachment mode;
- intensity curve;
- style profile;
- occlusion and compositing order;
- whether it is generated in-model, rendered as a control/reference pass, or added in post;
- a rule preventing it from altering protected identity, product, or safety regions.

Effects can compile to prompt clauses, particle systems, optical-flow-aligned trails, masks, vector fields, compositor nodes, camera impulse curves, or post-process keyframes. They must remain separable from physical metrics so that a dramatic impact flash does not conceal foot sliding or body penetration.

### 19.4.6 Marketing Control Contract

Marketing controls are best represented as requirements and hypotheses rather than style adjectives:

```yaml
marketing:
  objective: "communicate rapid cushioning response"
  audience_segment: "adult recreational runners"
  hook:
    deadline_s: 1.0
    requirement: "recognizable landing impact before first second"
  product:
    asset_id: "shoe.nova.v4"
    minimum_visible_area_ratio: 0.08
    hero_interval_s: [3.8, 5.1]
    logo_occlusion_max: 0.05
  claim:
    text: "Responsive cushioning"
    evidence_asset_id: "claim.approval.2026-14"
  call_to_action:
    text_asset_id: "cta.learn_more.en-US"
    minimum_hold_s: 1.2
  variants:
    - {id: "vertical_9x16", safe_zone: "platform.vertical.v2"}
    - {id: "landscape_16x9", safe_zone: "platform.landscape.v1"}
  measurement:
    experiment_id: "launchA.creative_test.07"
    primary_metric: "qualified_click_through"
```

This layer can compile to visibility and timing constraints, crop-safe layouts, variant jobs, localized text/audio, metadata, and acceptance checks. It cannot compile a guarantee that the creative “will sell.” Sales and attention are outcomes affected by product, audience, placement, price, distribution, competing messages, and many other variables. The score should store the causal claim as a hypothesis to be tested.

## 19.5 YAML as the Human Authoring and Configuration Layer

YAML is appropriate for project configuration, style profiles, shot plans, named references, and department-authored overrides because its indentation and comments can remain readable at substantial depth. The YAML 1.2.2 specification defines mappings, sequences, scalars, tags, anchors, and aliases, but it also states that mapping-key order is not application-level information and that anchor names are discarded when the representation graph is composed (YAML Language Development Team, 2021 [S53]). Three consequences follow for a cinematic score.

First, **time must be represented by ordered sequences or explicit timestamps**, never by the visual order of keys in a mapping. This is safe:

```yaml
beats:
  - {id: "notice", start_s: 0.00, end_s: 0.42}
  - {id: "decide", start_s: 0.42, end_s: 0.88}
  - {id: "move", start_s: 0.88, end_s: 2.40}
```

This is not a portable timeline because the key order is not semantically guaranteed:

```yaml
beats:
  notice: {start_s: 0.00}
  decide: {start_s: 0.42}
  move: {start_s: 0.88}
```

The second form can still work when every record has a timestamp and the compiler sorts it, but the apparent source order must not be the only timing signal.

Second, **YAML anchors and aliases should not be treated as the normative CPCS inheritance system**. They can reduce local repetition:

```yaml
restrained_base: &restrained_base
  performance:
    acting_scale: 0.32
    facial_amplitude: 0.25
    gesture_amplitude: 0.28

shot:
  local_copy: *restrained_base
```

However, an alias reuses a node in the YAML representation; it does not define project/scene/shot precedence, lock semantics, provenance, array-merge policy, or cross-file version resolution. CPCS therefore uses an explicit application-level `extends` and `overrides` contract. A compiler may permit anchors for convenience, but it resolves them before semantic inheritance and records that no anchor identity survives in the canonical score.

Third, YAML loaders vary in scalar resolution and extension behavior. A production profile should require YAML 1.2-compatible parsing, reject duplicate keys, use a safe loader that does not instantiate arbitrary application objects, limit alias expansion, and require explicit strings for values that could be mistaken for dates, booleans, or numbers. Units should be represented in field names or typed objects, not hidden in comments.

### 19.5.1 Recommended YAML Authoring Shape

```yaml
schema: "cpcs-authoring/1.1"
document_id: "campaignA.sequence03.shot014"

imports:
  - id: "production_style"
    uri: "style://campaignA/kinetic-realism@3.2.0"
    sha256: "<content-digest>"
  - id: "measured_body_track"
    uri: "asset://motion/shot014_body.cpcs.json"
    media_type: "application/cpcs+json"
    sha256: "<content-digest>"

extends:
  - "production_style"

scope:
  project: "campaignA"
  sequence: "sequence03"
  scene: "roof_encounter"
  shot: "shot014"

shot:
  duration_s: 6.0
  fps: 24
  narrative:
    objective: "show composure under pressure"
    audience_takeaway: "control is chosen, not effortless"

  style_overrides:
    performance:
      acting_scale: 0.26
    laban:
      flow: {pole: "bound", value: 0.82}
    cinematography:
      camera_mode: "dolly_in"
      lens_mm: 65

  tracks:
    body:
      ref: "measured_body_track#/tracks/body"
    face:
      - id: "mara.au04"
        actor_id: "mara"
        au: "AU04"
        curve: [[2.50, 0.0], [2.74, 0.28], [3.52, 0.0]]

  constraints:
    - id: "no_early_fear_display"
      mode: "hard"
      expression: "face:mara.total_activation < 0.15 until 2.50s"
```

The `$ref`-like fragment after `ref` is a CPCS application convention, not a native YAML reference feature. The compiler resolves the named import, checks the digest and media type, interprets the fragment through the registered resolver, and copies the resolved value into canonical JSON with provenance.

### 19.5.2 Direct YAML Prompting

A user may paste a compact YAML block directly into a text-to-video prompt. This is useful when a model or an upstream LLM has been explicitly instructed to read it. The recommended direct-prompt form is shallow, uses plain terms alongside codes, and does not bury the core action under hundreds of numeric samples:

```yaml
shot: "single continuous medium close-up"
subject: "Mara approaches, recognizes danger, and contains fear"
performance:
  face: "low AU04 brow lowering; trace AU05 eye widening; restrained"
  body: "direct approach; sustained time; bound flow"
camera: "slow dolly-in beginning at recognition"
timing:
  recognition: "2.5 seconds"
  facial_leak: "2.7 seconds"
```

The compiler should mark this as a textual summary. The complete AU spline, contact schedule, and camera path remain in the canonical score because large numeric YAML blocks usually exceed what a prompt-only backend can interpret reliably.

## 19.6 JSON as the Canonical Intermediate Representation and API Boundary

JSON is well suited to a canonical intermediate representation because it is minimal, broadly supported, and compatible with formal validation. RFC 8259 defines JSON objects as unordered and arrays as ordered (Bray, 2017 [S51]). Consequently, CPCS uses objects for named records and arrays for ordered beats, samples, keyframes, patch operations, and priority lists. Duplicate object names are rejected because RFC 8259 notes that receiving software differs when names are not unique.

A fully resolved canonical record should satisfy the following conditions:

- every inherited value is materialized;
- all references are resolved or represented as immutable, content-addressed asset links;
- all times use one declared timebase and explicit units;
- all coordinate systems are declared;
- all array merge decisions have already occurred;
- every effective field has provenance;
- no comments or YAML-only tags remain;
- no adapter-specific field appears outside a registered namespace;
- the record validates against a pinned JSON Schema version.

### 19.6.1 Canonical JSON Example

```json
{
  "$schema": "https://schemas.example.org/cpcs/1.1/cpcs.schema.json",
  "schema_version": "cpcs/1.1",
  "document_id": "campaignA.sequence03.shot014",
  "timebase": {"fps": 24, "duration_s": 6.0, "frame_count": 144},
  "effective_styles": {
    "performance": {"acting_scale": 0.26},
    "laban": {"flow": {"pole": "bound", "value": 0.82}},
    "cinematography": {"camera_mode": "dolly_in", "lens_mm": 65}
  },
  "tracks": {
    "face": [
      {
        "id": "mara.au04",
        "actor_id": "mara",
        "action_unit": "AU04",
        "side": "bilateral",
        "samples": [
          {"time_s": 2.50, "intensity": 0.0},
          {"time_s": 2.74, "intensity": 0.28},
          {"time_s": 3.52, "intensity": 0.0}
        ]
      }
    ]
  },
  "constraints": [
    {
      "id": "no_early_fear_display",
      "mode": "hard",
      "operator": "less_than_until",
      "target": "face:mara.total_activation",
      "value": 0.15,
      "until_s": 2.50
    }
  ],
  "provenance": {
    "resolved_from": [
      {"uri": "style://campaignA/kinetic-realism@3.2.0", "scope": "project"},
      {"uri": "authoring://campaignA.sequence03.shot014.yaml", "scope": "shot"}
    ]
  }
}
```

### 19.6.2 JSON Schema as Structural Validation, Not Cinematic Meaning

JSON Schema Draft 2020-12 can specify required properties, types, ranges, reusable definitions, conditional alternatives, and references (Bhutton et al., 2022 [S52]). It can reject an AU intensity outside `[0,1]`, a missing actor ID, a negative duration, or a camera record with neither a trajectory nor a semantic plan. It cannot determine that an expression is artistically appropriate, that a fight beat reads clearly, or that a product shot will convert. Those are semantic, perceptual, or empirical tests above the structural schema.

A schema fragment can compose domain definitions:

```json
{
  "$defs": {
    "timeSample": {
      "type": "object",
      "required": ["time_s", "value"],
      "properties": {
        "time_s": {"type": "number", "minimum": 0},
        "value": {"type": "number"}
      },
      "additionalProperties": false
    },
    "facsTrack": {
      "type": "object",
      "required": ["id", "actor_id", "action_unit", "samples"],
      "properties": {
        "id": {"type": "string"},
        "actor_id": {"type": "string"},
        "action_unit": {"pattern": "^AU[0-9]{1,2}$"},
        "samples": {
          "type": "array",
          "minItems": 2,
          "items": {"$ref": "#/$defs/timeSample"}
        }
      },
      "additionalProperties": false
    }
  }
}
```

Semantic validation then checks monotonic sample times, actor existence, compatible frame counts, feasible constraints, and cross-track relationships.

### 19.6.3 JSON Pointer, JSON Patch, and Merge Patch

JSON Pointer defines a string syntax for locating a value inside a JSON document (Bryan, Zyp, & Nottingham, 2013 [S58]). JSON Patch defines an ordered sequence of `add`, `remove`, `replace`, `move`, `copy`, and `test` operations (Bryan & Nottingham, 2013 [S59]). These standards are useful for precise shot revisions:

```json
[
  {"op": "test", "path": "/document_id", "value": "campaignA.sequence03.shot014"},
  {"op": "replace", "path": "/effective_styles/cinematography/lens_mm", "value": 85},
  {"op": "replace", "path": "/tracks/face/0/samples/1/intensity", "value": 0.20},
  {"op": "add", "path": "/constraints/-", "value": {
    "id": "hold_closeup_after_apex",
    "mode": "hard",
    "start_s": 2.74,
    "end_s": 3.30
  }}
]
```

The `test` operation makes a patch safer by verifying its expected base. A production patch should also carry base-document and result-document hashes.

JSON Merge Patch provides a simpler object-shaped update in which null removes a member, but it treats arrays as replaceable values rather than providing element-level editing (Hoffman & Snell, 2014 [S60]). It is therefore suitable for shallow configuration changes but insufficient for timeline splicing, keyed track merges, or nuanced null semantics. CPCS uses JSON Patch for auditable canonical revisions and a separate typed merge system for inheritance.

### 19.6.4 Canonicalization and Hashing

Whitespace and object-member order can vary without changing a JSON data model. When CPCS uses a JSON document in a content-addressed manifest, it should canonicalize the document before hashing. The JSON Canonicalization Scheme defines deterministic serialization rules for cryptographic operations (Rundgren, Jordan, & Erdtman, 2020 [S61]). Canonicalization does not replace semantic validation; it lets two systems verify that they hashed the same resolved representation.

## 19.7 XML as a Semantic Director Envelope

XML is most useful when a package contains ordered prose, dialogue, annotations, references, and multiple domain vocabularies. XML namespaces associate element and attribute names with namespace URIs, which avoids collisions between a `face:action`, `lma:effort`, `cam:move`, and `mkt:claim` (Bray et al., 2009 [S55]). XML Schema Definition Language can validate element/attribute structures and datatypes, while XSLT can transform XML documents into other XML, text, or structured outputs (Gao et al., 2012 [S56]; Kay, 2017 [S57]).

A director envelope can preserve literary order and mixed content while referring to canonical JSON for dense controls:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<cpcs:directorPackage
    xmlns:cpcs="urn:cpcs:core:1.1"
    xmlns:face="urn:cpcs:facs:1.1"
    xmlns:lma="urn:cpcs:laban:1.1"
    xmlns:cam="urn:cpcs:camera:1.1"
    xmlns:vfx="urn:cpcs:vfx:1.1"
    xmlns:mkt="urn:cpcs:marketing:1.1"
    id="campaignA.sequence03.shot014">

  <cpcs:brief>
    Mara approaches as though composed. When she recognizes the danger,
    the audience sees a brief failure of control before she recovers.
  </cpcs:brief>

  <cpcs:dialogue actor="mara" audioRef="asset://audio/mara_line_03.wav">
    I said I would come alone.
  </cpcs:dialogue>

  <face:event actor="mara" au="AU04" onset="2.50s" apex="2.74s"
              offset="3.52s" peak="0.28"/>
  <lma:effort actor="mara" interval="0.00s/2.45s"
              weight="light" time="sustained" space="direct" flow="bound"/>
  <cam:move type="dolly-in" interval="2.20s/3.20s" endFraming="close-up"/>

  <cpcs:score
      href="asset://scores/shot014.resolved.cpcs.json"
      mediaType="application/cpcs+json"
      schema="cpcs/1.1"
      sha256="&lt;canonical-json-digest&gt;"/>

  <mkt:requirement id="product_visibility" asset="shoe.nova.v4"
                   interval="3.80s/5.10s" minimumAreaRatio="0.08"/>
</cpcs:directorPackage>
```

The namespace URIs identify vocabularies; they do not need to be network locations. An XML Schema can import separate FACS, Laban, camera, VFX, and marketing modules. An XSLT stylesheet or conventional parser can extract the ordered brief and dialogue, validate the envelope, and generate a CPCS authoring object.

### 19.7.1 Direct XML Prompting

XML-like tags are often useful inside an LLM instruction because they delimit sections. A prompt-only video endpoint, however, receives those tags as text unless its service explicitly parses them. Direct XML prompting should therefore use a concise semantic envelope and avoid pretending that an XSD was enforced when no parser ran.

A direct XML prompt is most defensible when an orchestration LLM is instructed to:

1. parse only the approved elements;
2. reject unknown or duplicated hard controls;
3. return schema-constrained canonical JSON;
4. provide a field-by-field translation report;
5. pass only the compiled prompt and supported assets to the video model.

### 19.7.2 XML With Embedded JSON

Small JSON payloads can be embedded as character data, often in CDATA:

```xml
<cpcs:payload mediaType="application/json" schema="cpcs/1.1"><![CDATA[
{
  "document_id": "campaignA.sequence03.shot014",
  "adapter": "generic.video.prompt-only/1"
}
]]></cpcs:payload>
```

This is technically workable but should not become the default for large motion tracks. Escaping, duplicated schemas, ambiguous ownership, and poor diff readability become problematic. The preferred pattern is an XML envelope with an external, content-addressed JSON score. Inline JSON is appropriate for a small adapter request, manifest, or patch that has exactly one declared authority.

## 19.8 JSONL for Retrieval, Event Streams, and Evaluation

JSON Lines stores one JSON value per line. CPCS uses JSONL for records that are naturally independent or append-only:

- RAG chunks and source records;
- compiler warnings and field mappings;
- generation candidates;
- frame or interval metric observations;
- experiment variants and outcomes;
- audit and provenance events.

A JSONL line can be retrieved or processed without parsing one enormous document:

```json
{"record_type":"compile_mapping","control_id":"shot014.mara.au04","status":"baked_into_reference","artifact":"face_ref_0066.png"}
{"record_type":"metric","candidate_id":"cand_07","metric":"au04_apex_time_error_s","value":0.041,"pass":true}
{"record_type":"marketing_variant","variant_id":"vertical_9x16","hero_visibility":0.091,"cta_hold_s":1.24,"pass":true}
```

JSONL is not the primary score because inheritance, actors, assets, timelines, and constraints form a hierarchy. It is the evidence and retrieval surface around that hierarchy.

<!-- RAG_CHUNK id="cpcs.style-inheritance" title="Style inheritance and typed merge semantics" concepts="style cascade, inheritance, merge precedence, overrides, JSON Patch, conflict resolution, provenance" -->
## 19.9 Style Is a Set of Typed Domains, Not One Global Adjective

“Inherited style” can mean several different things: a production’s visual look, an actor-performance convention, a motion quality, a camera grammar, an editing rhythm, a VFX language, an audio treatment, or a marketing template. Combining all of them under one string such as `style: aggressive cinematic anime` makes precedence impossible to reason about. CPCS therefore separates style into domains with independent schemas and inheritance.

```yaml
style:
  visual:
    medium: "cinematic_photorealism"
    palette: "cool_desaturated"
    contrast: 0.62
    texture: "fine_film_grain"

  performance:
    acting_scale: 0.30
    emotional_externalization: 0.24
    microexpression_bias: 0.78
    gesture_amplitude: 0.34

  affect_display:
    suppression_strength: 0.68
    recovery_speed: 0.55

  motion:
    realism: "biomechanical"
    transition_smoothness: 0.84
    microvariation: 0.16

  laban:
    weight: {pole: "light", value: 0.35}
    time: {pole: "sustained", value: 0.28}
    space: {pole: "direct", value: 0.74}
    flow: {pole: "bound", value: 0.81}

  cinematography:
    camera_style: "controlled_handheld"
    lens_family: "spherical"
    framing_bias: "medium_close_up"
    movement_latency_s: 0.10

  editorial:
    pacing: "deliberate"
    reaction_hold_s: 0.42
    cut_on_action_bias: 0.36

  vfx:
    language: "restrained_graphic_accents"
    shake_scale: 0.20
    smear_frame_policy: "impact_only"

  audio:
    dynamic_range: "wide"
    impact_emphasis: 0.30
    breath_presence: 0.62

  marketing:
    brand_profile: "campaignA.launch_v3"
    product_priority: "high"
    claim_density: "single_claim"
    cta_style: "quiet_confident"
```

A shot may inherit all domains but override only `cinematography.camera_style` and `laban.flow`. The untouched marketing and identity profiles remain stable. This domain separation also prevents a VFX phrase such as `high energy` from accidentally increasing the character’s arousal, shortening the edit, changing color saturation, and enlarging the product in the same uncontrolled step.

## 19.10 Scope Cascade and Merge Precedence

**[PROPOSED]** The ordinary creative cascade proceeds from broad to specific:

```text
studio or system defaults
        ↓
project / production profile
        ↓
sequence profile
        ↓
scene profile
        ↓
shot profile
        ↓
beat override
        ↓
frame, event, or interval override
```

For a field path \(p\), the simplest resolved value is:

\[
V_p^{*} = V_p^{\text{default}}
\oplus V_p^{\text{project}}
\oplus V_p^{\text{sequence}}
\oplus V_p^{\text{scene}}
\oplus V_p^{\text{shot}}
\oplus V_p^{\text{beat}}
\oplus V_p^{\text{event}},
\]

where \(\oplus\) is a field-specific merge operator. “More specific wins” is only the default. A production system also has authority, locks, and constraint classes.

### 19.10.1 Authority Classes

A useful authority order is:

1. **safety, law, rights, and consent** — cannot be weakened by creative overrides;
2. **asset identity and approved claims** — may be locked by production governance;
3. **continuity and technical invariants** — coordinate systems, frame rate, actor IDs, product version;
4. **director-approved hard constraints** — contact frame, reveal order, dialogue sync, hero interval;
5. **department controls** — performance, choreography, camera, VFX, sound, marketing;
6. **adapter defaults and model heuristics** — lowest creative authority.

A conflict between two hard constraints of equal authority is not resolved by “last writer wins.” It is an error requiring revision or an explicit arbitration policy. A safety constraint does not creatively “win” by changing a number; it may reject an asset, remove an operation, or require an approved alternative.

### 19.10.2 Candidate Resolution Tuple

Each candidate value can be represented as:

\[
c = (p, v, a, s, q, \ell, h, o, r),
\]

where:

- \(p\) is the field path;
- \(v\) is the value;
- \(a\) is authority class;
- \(s\) is scope specificity;
- \(q\) is explicit priority within the permitted range;
- \(\ell\) is lock status;
- \(h\) is hard/soft constraint class;
- \(o\) is stable declaration order used only as a final tie-breaker;
- \(r\) is provenance.

A resolver should evaluate candidates in this order:

1. reject any candidate violating non-overridable policy, rights, or schema rules;
2. detect incompatible hard constraints;
3. preserve a valid lock unless the caller has a documented `override_lock` authority;
4. compare authority class;
5. compare scope specificity;
6. compare explicit priority within the same authority and scope;
7. apply the registered type-specific merge operation;
8. use stable declaration order only when the semantics explicitly permit it;
9. emit the winner, all shadowed candidates, and the reason.

This procedure creates explainable inheritance. The compiler can answer, “Why is the lens 85 mm?” with a provenance chain rather than returning only the final number.

### 19.10.3 Lock and Final Semantics

A style profile can lock selected paths:

```yaml
locks:
  - path: "/identity/actors/mara/reference_asset"
    authority: "rights_and_identity"
    reason: "approved likeness asset"
  - path: "/marketing/claim/text"
    authority: "approved_claim"
    reason: "legal-approved wording"
  - path: "/timebase/fps"
    authority: "technical_invariant"
    reason: "delivery specification"
```

A beat override can still modify unlocked facial intensity or camera motion. Attempting to replace the approved claim or actor reference produces an error unless an authorized patch explicitly changes the lock record and records the approval.

## 19.11 Typed Merge Algebra

A generic recursive deep merge is inadequate for cinematic data. Scalars, sets, ordered events, keyed actors, temporal tracks, constraints, and style deltas require different operations. Every schema path that can inherit should declare a merge policy.

| Data kind | Default merge policy | Example | Required behavior |
|---|---|---|---|
| Scalar or enum | `replace` | `lens_mm`, `camera_style`, `flow.pole` | More authoritative/specific value replaces prior value. |
| Numeric style value | `replace`, or explicit `add`/`multiply` | `acting_scale`, `shake_scale` | No implicit arithmetic. Operation must be named and range-checked. |
| Object/map | `deep_merge_typed` | `style.cinematography` | Recurse using the registered policy for each child path. |
| Set-like list | `set_union` or `set_subtract` | tags, allowed assets, retrieval aliases | Deduplicate by canonical identity; order is not semantic. |
| Ordered list | `replace` or `append_ordered` | prompt clauses, edit sequence | Policy must be explicit; preserve declared order. |
| Keyed entity list | `merge_by_id` | actors, beats, constraints, VFX events | Merge records with the same stable ID; reject duplicate IDs without policy. |
| Dense temporal track | `replace_track`, `splice_interval`, or `blend_interval` | AU samples, camera path, root motion | Time-domain operation must define boundaries, interpolation, and overlap behavior. |
| Hard constraints | `conjoin_or_conflict` | “contact at 1.60 s” and “no contact before 1.58 s” | Combine compatible constraints; raise an error for incompatible constraints. |
| Asset reference | `replace_by_digest` | identity image, product model, audio take | Resolve immutable version/digest; do not merge asset bytes. |
| Optional field removal | explicit `$delete` or patch `remove` | remove inherited camera shake | Do not overload null unless the schema defines null as deletion. |

### 19.11.1 Scalar and Delta Operations

A child scope that wants to modify rather than replace a numeric style must state the operation:

```yaml
style_overrides:
  performance:
    acting_scale:
      op: "multiply"
      value: 0.80
  vfx:
    shake_scale:
      op: "add"
      value: -0.10
```

The resolver applies the operation to the inherited value and stores both the base and result. It rejects a delta when no base exists or when the result violates the field range.

### 19.11.2 Keyed-Entity Merge

A shot can modify one beat without replacing the entire beat list:

```yaml
beats:
  merge: "merge_by_id"
  items:
    - id: "impact"
      end_s: 1.68
      director:
        presentation: "single_frame_hold"
```

The compiler finds the inherited `impact` beat, merges the permitted fields, then revalidates timeline ordering and overlaps. An unknown ID can be an error or an insertion depending on an explicit `on_missing` policy.

### 19.11.3 Timeline Splice and Blend

A temporal override must identify the interval and boundary behavior:

```yaml
tracks:
  camera:
    merge: "splice_interval"
    interval_s: [2.20, 3.20]
    boundary: "c1_continuous"
    value:
      type: "dolly_in"
      start_pose_ref: "inherit"
      end_framing: "close_up"
```

`c1_continuous` requires position and first-derivative continuity at splice boundaries. A body or camera solver may insert transition samples. For an AU curve, `blend_interval` might cross-fade intensities over 80 ms. For a hard foot-contact state, blending is usually invalid; the resolver must use contact-aware transition logic.

### 19.11.4 Null, Missing, and Delete Are Different

Three states should remain distinct:

- **missing:** inherit or use a default;
- **null:** explicitly no value, when the schema allows this meaning;
- **delete:** remove an inherited member or event.

JSON Merge Patch uses null as member removal (Hoffman & Snell, 2014 [S60]), which can be convenient but conflicts with domains where null is a legitimate value such as “unknown focus distance.” CPCS therefore uses a typed `$delete` directive in authoring and compiles canonical revisions to JSON Patch `remove` operations.

## 19.12 Conflict Reports and Provenance

Every resolved path should be traceable. A compile report can include:

```json
{
  "path": "/effective_styles/cinematography/lens_mm",
  "resolved_value": 85,
  "resolution": "shot_override_replaced_project_default",
  "winner": {
    "scope": "shot",
    "source": "authoring://shot014.yaml#/shot/style_overrides/cinematography/lens_mm",
    "authority": "director_approved",
    "priority": 50
  },
  "shadowed": [
    {
      "value": 50,
      "scope": "project",
      "source": "style://campaignA/kinetic-realism@3.2.0",
      "reason": "less_specific"
    }
  ]
}
```

For a hard conflict, the report should identify the smallest incompatible set:

```json
{
  "status": "error",
  "code": "HARD_CONSTRAINT_CONFLICT",
  "controls": ["contact_at_1_60", "no_proximity_before_1_75"],
  "explanation": "The required fist-target separation at 1.60 s violates the minimum separation constraint until 1.75 s.",
  "suggested_repairs": [
    "move contact or near-contact to 1.75 s or later",
    "change the first event to staged near-contact",
    "revise the avoidance interval"
  ]
}
```

Provenance is not administrative overhead. It is necessary for continuity, rights management, debugging, RAG grounding, and repeatable experiments.

<!-- RAG_CHUNK id="cpcs.cross-format-compilation" title="Cross-format schema composition and compilation targets" concepts="YAML to JSON, XML with JSON, schema composition, compiler passes, target execution package, control assets" -->
## 19.13 YAML-to-JSON Compilation

YAML-to-JSON compilation is not merely a file-format conversion. A general YAML parser can turn mappings and sequences into native objects, but a CPCS compiler must also resolve semantic constructs. The recommended passes are:

```text
1. Decode and parse YAML with a restricted YAML 1.2 profile.
2. Reject duplicate keys, unsafe tags, excessive alias expansion, and unknown directives.
3. Validate the authoring document against the CPCS authoring schema.
4. Resolve imports by immutable version or digest.
5. Resolve YAML aliases as serialization references.
6. Expand application-level `extends` profiles.
7. Apply typed, scope-aware overrides and locks.
8. Normalize aliases, enumerations, units, timebases, and coordinate systems.
9. Resolve cross-document references and JSON Pointers.
10. Materialize defaults and computed fields.
11. Validate cross-field semantics and constraint feasibility.
12. Emit fully resolved canonical JSON.
13. Canonicalize and hash the JSON.
14. Emit provenance, conflict, and loss reports.
```

A simple serialization conversion might preserve the surface values but miss whether `24` means frames per second, a frame index, a duration, or an AU intensity. Semantic compilation attaches types and units before output.

### 19.13.1 Example: YAML Source and Resolved JSON

Authoring source:

```yaml
schema: "cpcs-authoring/1.1"
extends: ["style://studio/action_base@2"]
shot:
  id: "fight_teaser_07"
  duration_s: 5.0
  overrides:
    laban:
      weight: {pole: "strong", value: 0.74}
      time: {pole: "sudden", value: 0.82}
    vfx:
      speed_lines: {enabled: true, intensity: 0.45}
```

Assume the base profile provides `fps: 24`, `laban.flow: bound/0.70`, `laban.space: direct/0.80`, and a default VFX style. The canonical JSON does not keep `extends`; it contains the effective values and their source map:

```json
{
  "schema_version": "cpcs/1.1",
  "document_id": "fight_teaser_07",
  "timebase": {"fps": 24, "duration_s": 5.0, "frame_count": 120},
  "effective_styles": {
    "laban": {
      "weight": {"pole": "strong", "value": 0.74},
      "time": {"pole": "sudden", "value": 0.82},
      "space": {"pole": "direct", "value": 0.80},
      "flow": {"pole": "bound", "value": 0.70}
    },
    "vfx": {
      "language": "graphic_action_base",
      "speed_lines": {"enabled": true, "intensity": 0.45}
    }
  },
  "provenance": {
    "/effective_styles/laban/space": "style://studio/action_base@2",
    "/effective_styles/laban/weight": "authoring://fight_teaser_07.yaml"
  }
}
```

This resolved object is suitable for validation, hashing, diffing, and target adaptation.

## 19.14 Combining YAML With JSON

YAML and JSON combine most cleanly when each has a defined ownership boundary:

- YAML owns human-authored project, scene, shot, style, and override declarations.
- JSON owns canonical resolved documents, measured tracks, machine-generated plans, schemas, patches, capability profiles, and API payloads.

A YAML shot can reference a JSON motion track:

```yaml
imports:
  - id: "body_capture"
    uri: "asset://motion/shot014.body.cpcs.json"
    media_type: "application/cpcs+json"
    sha256: "<digest>"

shot:
  tracks:
    body:
      ref: "body_capture#/tracks/body"
      adaptation:
        retarget_to: "rig.mara.v5"
        preserve_contacts: true
```

The compiler parses the JSON, validates it against its declared schema, resolves `/tracks/body` using JSON Pointer [S58], retargets it if permitted, and inserts the result into the canonical score. The YAML does not copy thousands of joint samples and the JSON does not need to carry the director’s entire style cascade.

A JSON Patch can revise the compiled score without rewriting YAML:

```yaml
canonical_patches:
  - uri: "patch://reviews/shot014.director-pass-03.json"
    media_type: "application/json-patch+json"
    expected_base_sha256: "<digest-before-patch>"
```

This pattern is appropriate for machine-generated or review-system changes. Human-authored source should remain synchronized by either back-propagating accepted patches or declaring canonical JSON as the review authority for that stage.

### 19.14.1 Avoid Dual Authority

The following is ambiguous:

```yaml
camera:
  lens_mm: 50
  json_payload: '{"camera":{"lens_mm":85}}'
```

Two values claim the same path. A compiler should reject this unless one is explicitly an override with precedence. Combining formats must happen through a semantic merge, not by nesting contradictory text blobs.

## 19.15 Combining XML With JSON

XML and JSON are complementary when XML carries ordered narrative and multiple semantic vocabularies while JSON carries dense, canonical data. Three patterns are supported.

### 19.15.1 External JSON Score Referenced by XML

This is the preferred pattern:

```xml
<cpcs:score href="asset://scores/shot014.resolved.cpcs.json"
            mediaType="application/cpcs+json"
            schema="cpcs/1.1"
            sha256="..."/>
```

The XML envelope can include dialogue, director notes, department approvals, and namespaced annotations. The JSON is the single authority for the resolved score.

### 19.15.2 Inline JSON Payload

Use inline JSON only for small, local data:

```xml
<cpcs:adapterRequest target="prompt-only/1">
  <cpcs:payload mediaType="application/json"><![CDATA[
  {"duration_s": 5, "aspect_ratio": "16:9", "candidate_count": 4}
  ]]></cpcs:payload>
</cpcs:adapterRequest>
```

The XML schema validates that the payload exists and declares a media type; the JSON parser and JSON Schema validate its contents. An XML validator alone cannot validate arbitrary JSON text in CDATA.

### 19.15.3 JSON Embedded as a Tree of XML Elements

A project could map every JSON member to XML elements, but this often produces a second canonical vocabulary and difficult round trips. It is justified only when an XML-native ecosystem requires it and the mapping is generated from one semantic model. Otherwise, reference the JSON directly.

### 19.15.4 XSLT and Cross-Format Transformation

XSLT 3.0 is an XML transformation language and includes facilities that can process JSON-related data models (Kay, 2017 [S57]). An XML director package can therefore be transformed into:

- a textual model prompt;
- canonical JSON or an intermediate XML form later converted to JSON;
- a subtitle or dialogue document;
- an edit-decision or review report;
- HTML documentation for human approval.

A transformation stylesheet is part of the compiler version and must be pinned and tested. A change in XSLT can alter the target prompt even when the XML source is unchanged.

## 19.16 Combining YAML, XML, and JSON in One Production

A complete project can use all three without mixing their responsibilities:

```text
project.yaml
  ├─ declares build profile, imports, styles, model targets, and variant matrix
  ├─ references sequence.xml
  └─ references measured and generated JSON tracks

sequence.xml
  ├─ preserves ordered screenplay, dialogue, director notes, and annotations
  └─ references shot-level canonical JSON scores

shot014.resolved.cpcs.json
  ├─ contains effective controls, tracks, constraints, assets, and provenance
  └─ compiles into backend request JSON and control assets

run.events.jsonl
  └─ records compilation mappings, generations, metrics, and approvals
```

A build manifest binds the package:

```yaml
package:
  id: "campaignA.sequence03.build17"
  sources:
    - {uri: "project.yaml", sha256: "...", role: "project_authoring"}
    - {uri: "sequence.xml", sha256: "...", role: "narrative_envelope"}
    - {uri: "shot014.resolved.cpcs.json", sha256: "...", role: "canonical_score"}
  compiler:
    id: "cpcs-compiler"
    version: "1.1.0"
  target_profiles:
    - "generic.prompt-video/2026-07"
    - "render-control-pipeline/internal-v4"
```

The compiler loads each source through its parser, converts it into a shared abstract syntax and semantic model, resolves authority, and emits one canonical score. It does not concatenate the raw YAML, XML, and JSON and ask the video model to infer which parts matter.

## 19.17 Schema Composition Across Formats

A multi-format system should have **one semantic ontology with several serializations**, not three independently evolving schemas. Each concept has a stable semantic identifier, such as:

```text
cpcs://field/performance/face/facs/action_unit
cpcs://field/movement/laban/effort/flow
cpcs://field/action/phase/near_contact
cpcs://field/camera/trajectory
cpcs://field/vfx/smear_frame
cpcs://field/marketing/product/hero_interval
```

The ontology defines:

- value type and range;
- units and coordinate system;
- required context;
- merge policy;
- constraint semantics;
- allowed scopes;
- compilation targets;
- verification metrics;
- aliases for retrieval and authoring;
- version and deprecation policy.

JSON Schema and XSD are projections of this model. YAML authoring is validated against a JSON-compatible authoring schema after parsing, with additional rules for imports and inheritance. XML namespaces and XSD modules project the same semantic IDs into qualified element names.

### 19.17.1 Schema Modules

A modular schema set might include:

```text
cpcs-core.schema.json
cpcs-narrative.schema.json
cpcs-affect.schema.json
cpcs-facs.schema.json
cpcs-laban.schema.json
cpcs-action.schema.json
cpcs-camera.schema.json
cpcs-vfx.schema.json
cpcs-marketing.schema.json
cpcs-adapter.schema.json

cpcs-core.xsd
cpcs-facs.xsd
cpcs-laban.xsd
cpcs-camera.xsd
cpcs-vfx.xsd
cpcs-marketing.xsd
```

JSON Schema can compose definitions with `$ref`, `$defs`, `allOf`, `anyOf`, and `oneOf` under carefully defined semantics [S52]. XSD can import schemas from different namespaces [S56]. The schemas should be generated or checked against the same field registry to prevent drift.

### 19.17.2 Round-Trip Limits

A lossless round trip is possible only for a shared subset. Differences include:

- XML distinguishes attributes, elements, mixed content, and order in ways that do not map uniquely to JSON objects.
- JSON has a native array and null value; XML represents repetition and absence differently.
- YAML can contain aliases, tags, and presentation comments that are intentionally absent from canonical JSON.
- Numeric precision and lexical forms may differ.

The compiler should therefore promise **semantic equivalence**, not reproduction of whitespace, comments, anchor names, attribute order, or original formatting. Every conversion should emit a loss report when information is omitted.

### 19.17.3 Versioning and Migration

Each document declares a schema version. A migration is an explicit transformation:

```json
{
  "migration_id": "cpcs/1.0-to-1.1",
  "source_schema": "cpcs/1.0",
  "target_schema": "cpcs/1.1",
  "operations": [
    {"op": "rename", "from": "/style/camera", "to": "/style/cinematography"},
    {"op": "split", "from": "/style/action", "to": ["/style/motion", "/style/vfx"]}
  ],
  "requires_review": ["marketing.claim"]
}
```

Automatic migration is permitted only when semantics are preserved. A field split, unit change, or altered merge rule may require human review.

## 19.18 What a CPCS Compiler Can Emit

The canonical score is richer than most current video APIs. The compiler therefore emits a package of complementary artifacts rather than assuming one prompt string can carry everything.

| CPCS source domain | Possible compiled artifact | Typical consumer | Verification evidence |
|---|---|---|---|
| Narrative, objective, subtext | ordered prose prompt blocks; beat labels; semantic tokens | text encoder, planning LLM, shot generator | event-order classifier; human narrative judgment |
| VAD/VAC | affect curve; style embedding; prompt summary; retrieval prior | performance planner, face/body generator | re-estimated affect with confidence and cultural caution |
| FACS | AU curves; rig controls; facial landmarks; expression keyframes; face references | face animator, pose/landmark-conditioned video model | AU extractor, apex-time error, intensity error, identity score |
| Gaze/head/blink/speech | target tracks; head pose; blink events; phoneme/viseme sequence | avatar renderer, talking-head model, pose-conditioned generator | gaze-target error, audiovisual sync, blink timing |
| Laban | motion-style vector; retrieval filter; retiming and trajectory modifiers | motion generator, motion matcher, animation system | expert rating, classifier proxy, action-preservation score |
| Combat/action graph | key poses; motion graph; local phase; target/avoidance constraints | motion diffusion, motion matching, physics controller | event order, near-contact/contact error, support and recovery metrics |
| Kinematics/contact/physics | skeleton stream; joint heatmaps; DensePose; depth; normals; segmentation; optical flow; collision targets | pose-to-video model, renderer, simulator | joint error, foot slip, penetration, CoM support, contact timing |
| Camera/director | 6-DoF trajectory; lens/focus; framing constraints; first/last frames; EDL; time warp | camera-conditioned generator, 3D renderer, editor | camera-pose error, framing, reveal, cut and duration checks |
| VFX/anime | masks; vector fields; particle triggers; shake curve; smear/hold events; compositor graph | VFX generator, renderer, compositor | effect timing, attachment, occlusion, protected-region checks |
| Audio | dialogue, TTS prompt, foley event list, music cue, ambience | audio generator, DAW, video model with audio | sync, loudness, event alignment, intelligibility |
| Marketing | hero-frame constraints; product masks; variant matrix; titles/CTA; crop-safe zones; experiment metadata | creative renderer, editor, localization and ad pipeline | product visibility, text hold, safe-zone, claim/asset validation, experiment outcomes |
| Safety/rights | allowlists; locked assets; prohibited transforms; audit manifest | compiler gate, asset service, policy system | validation pass/fail and approval provenance |

### 19.18.1 Prompt Text

A prompt adapter compresses high-level controls into a readable sequence. It should prioritize subject, action, timing, camera, environment, lighting, style, and critical negatives. It should not serialize every low-level sample into prose.

Example compiled prompt:

```text
Single continuous 6-second shot. Mara approaches Jon along a direct path while
maintaining controlled eye contact. Her movement is sustained and tightly bound,
with restrained gestures. At 2.5 seconds she notices blood on his shirt; her gaze
briefly drops, the final left-foot plant coincides with recognition, and a subtle
brow-lowering and trace eye-widening peak around 2.75 seconds before she regains
control. Begin a slow 65 mm dolly-in at recognition and settle into a close-up.
No early fear display, no extra steps after the final plant, no cut before recovery.
```

The prompt is a lossy projection. The target package should retain the score and loss report.

### 19.18.2 API Parameters

Some controls belong in API fields rather than prose: model identifier, duration, size or aspect ratio, result count, seed where supported, safety settings, and media references. Official OpenAI prompting documentation for Sora 2 explicitly separated attributes governed by API parameters from prompt content; `model`, `size`, and `seconds` had to be supplied in the request rather than requested in prose (OpenAI, 2026 [S63]). This is a concrete example of why a compiler must distinguish semantic prompting from endpoint configuration.

### 19.18.3 Media and Control Passes

When the target accepts images or video, CPCS can render or synthesize:

- first and last frames;
- expression reference frames at AU apexes;
- pose or skeleton sequences;
- DensePose or segmentation video;
- depth and normal passes;
- optical flow and motion-vector fields;
- object and actor masks;
- camera preview or animatic;
- reference performance clips;
- audio guide tracks.

A control pass may encode more timing and geometry than prose. It should be generated from the same canonical timebase and carry frame IDs so that no drift occurs.

### 19.18.4 3D, Simulation, and Postproduction Assets

A hybrid pipeline can compile to BVH/FBX/glTF animation, parametric-body coefficients, camera scene files, physics-controller goals, collision geometry, render passes, and an edit/compositor graph. These artifacts can drive a conventional renderer before the output is passed to an image-to-video or video-to-video model for photorealistic or stylized synthesis.

This route is often preferable for exact walking, running, fighting, and multi-actor contact because it externalizes geometry and timing rather than requiring a pixel model to infer them from text.

<!-- RAG_CHUNK id="cpcs.model-adapters" title="Model capability negotiation and video backend adapters" concepts="text-to-video API, image-to-video, capability profile, degradation policy, OpenAI Sora, Google Veo, Runway API" -->
## 19.19 Capability Negotiation and Controlled Degradation

A canonical CPCS score should not be flattened before the compiler knows the target’s capabilities. Each model or workflow has a versioned capability profile:

```yaml
adapter_profile:
  id: "vendor.model.version"
  verified_on: "2026-07-18"
  accepts:
    text_prompt: {support: "native", maximum_length: 4000}
    duration: {support: "native", values_s: [4, 6, 8]}
    aspect_ratio: {support: "native", values: ["16:9", "9:16"]}
    first_frame: {support: "native"}
    last_frame: {support: "native"}
    reference_images: {support: "model_specific"}
    pose_sequence: {support: "none"}
    facial_au_track: {support: "none"}
    camera_6dof: {support: "none"}
    audio_prompt: {support: "native_or_model_specific"}
    edit_input_video: {support: "model_specific"}
  policies:
    unsupported_hard_control: "error"
    unsupported_soft_control: "approximate_then_warn"
```

For each source control, the compiler chooses one status:

| Status | Meaning |
|---|---|
| `native_exact` | Mapped to a documented target field or condition with matching semantics. |
| `native_approximate` | Mapped to a supported field whose semantics are close but not identical. |
| `baked_into_reference` | Rendered or edited into an image, video, pose, depth, or audio reference. |
| `compressed_to_text` | Summarized in natural language because no stronger channel exists. |
| `postprocess_only` | Applied after generation in edit, VFX, audio, or compositing. |
| `evaluation_only` | Cannot drive the model but remains an acceptance criterion. |
| `dropped_with_warning` | Omitted under an explicitly permitted soft-control policy. |
| `unsupported_error` | Cannot be realized and is too important to drop. Generation does not start. |

This classification prevents false precision. A prompt-only adapter cannot claim that an exact AU spline or contact trajectory was natively conditioned merely because the prose contains numbers.

### 19.19.1 Loss Budget

A production can define a loss budget:

```yaml
loss_policy:
  hard_domains:
    - "identity"
    - "rights"
    - "contact_timing"
    - "marketing.approved_claim"
  maximum_text_compression:
    facs_tracks: 2
    action_events: 6
  permitted_approximations:
    laban: true
    camera_semantics: true
    micro_vfx: true
  forbidden_drops:
    - "dialogue"
    - "product_visibility"
    - "final_frame"
```

When a target cannot meet the budget, the compiler can select a different model, split the shot, render more reference passes, or fail before spending generation resources.

## 19.20 Current Backend Examples as of July 18, 2026

The following examples illustrate adapter design, not permanent product recommendations. Video APIs change quickly, so every adapter must pin a model ID, API version, verification date, and official documentation source.

### 19.20.1 OpenAI Sora 2 Videos API: Prompt and Parameter Separation

OpenAI’s official Video generation guide states that a render job combines a prompt with parameters and that prompt text defines creative content while fields such as size and seconds control resolution and length (OpenAI, 2026 [S62]). The Sora 2 prompting guide further states that some attributes are governed only by API parameters and cannot be requested in prose (OpenAI, 2026 [S63]). This is a useful architectural example even though the same official guide states that Sora 2 and the Videos API are deprecated and scheduled to shut down on **September 24, 2026** [S62].

An illustrative adapter could emit:

```json
{
  "model": "sora-2",
  "prompt": "<compiled cinematic prompt>",
  "size": "1280x720",
  "seconds": "8"
}
```

CPCS fields such as exact AU curves, skeletal pose sequences, and camera 6-DoF trajectories are not represented by this minimal request. The adapter would need to compress them into prompt text, bake them into an input image or video where supported, preserve them as evaluation constraints, or report them unsupported. The deprecation date means this adapter should be treated as historical or transitional, not a durable production dependency.

### 19.20.2 Google Veo on Vertex AI: First/Last Frames and Explicit Parameters

Google Cloud’s Veo documentation provides an example in which a prompt, first image, optional last frame, aspect ratio, duration, result count, negative prompt, resolution, and seed-related configuration are supplied through API fields for supported model variants (Google Cloud, 2026 [S64]). A CPCS adapter can therefore realize selected director controls through:

- prompt text for subject, action, camera semantics, lighting, and style;
- first and last frames for composition and endpoint state;
- explicit duration and aspect ratio;
- negative prompt for prohibited visual outcomes where supported;
- result count for candidate generation;
- seed as a reproducibility aid under the service’s documented behavior.

The adapter must still report that a first/last-frame interface does not equal arbitrary intermediate pose, AU, contact, or camera-path control. It can render an animatic or key endpoint frames from CPCS, but compliance between endpoints remains a model outcome.

Illustrative target package:

```json
{
  "instances": [
    {
      "prompt": "<compiled prompt>",
      "image": {"gcsUri": "gs://project/shot014_first.png", "mimeType": "image/png"},
      "lastFrame": {"gcsUri": "gs://project/shot014_last.png", "mimeType": "image/png"}
    }
  ],
  "parameters": {
    "aspectRatio": "16:9",
    "sampleCount": 4,
    "durationSeconds": 6,
    "resolution": "1080p",
    "negativePrompt": "extra limbs, early reaction, product occlusion"
  }
}
```

Exact field names must be generated from the pinned current API schema rather than copied from a generic profile.

### 19.20.3 Runway API: JSON Requests and Model-Specific Capabilities

Runway’s official getting-started guide shows JSON or SDK requests with fields such as `model`, `promptImage`, `promptText`, `ratio`, and `duration`; text-to-video mode can be selected by omitting the image for a model that supports it (Runway, 2026 [S65]). Its API changelog documents rapidly changing model-specific capabilities, including variants with keyframe, image, video, reference, editing, audio, and resolution options (Runway, 2026 [S66]).

A Runway adapter should not assume that every model behind the same service accepts the same controls. It should generate a profile per model and endpoint. A minimal request might be:

```json
{
  "model": "gen4.5",
  "promptText": "<compiled prompt>",
  "promptImage": "<first-frame-or-data-URI>",
  "ratio": "1280:720",
  "duration": 5
}
```

A different current model may accept keyframes, reference images, a reference video, or audio. The compiler should map CPCS assets only after validating that the selected model and endpoint support them.

### 19.20.4 Why Adapter Documentation Must Be Versioned

The same semantic control can move between channels as APIs evolve. A camera endpoint once expressed only through text may later accept a trajectory. A model may add or remove keyframes, change duration limits, or deprecate an identifier. The adapter record should therefore include:

```yaml
adapter_provenance:
  vendor: "example_vendor"
  model_id: "example_video_v3"
  api_version: "2026-06-15"
  docs_verified_on: "2026-07-18"
  compiler_adapter_version: "1.4.2"
  capability_test_suite: "adapter-tests/example_video_v3@7"
```

A build should fail or require review when the verified capability profile is stale beyond the project’s policy window.

## 19.21 Prompt-Only, Multimodal, and Render-Assisted Compilation Tiers

CPCS defines three deployment tiers.

### Tier 1: Prompt-Only

Outputs:

- one structured prose prompt;
- endpoint parameters;
- negative prompt where available;
- evaluation targets.

This tier is inexpensive and flexible but offers the weakest timing and geometry control. FACS, Laban, combat, and camera tracks are summarized in language.

### Tier 2: Multimodal Control

Outputs may include:

- first, last, and intermediate keyframes;
- pose, landmark, depth, mask, or reference video;
- audio guide;
- prompt and endpoint parameters.

This tier preserves more of the score. The compiler chooses keyframes at narrative and motion events: recognition, AU apex, contact, reaction, recovery, product hero frame, and CTA transition.

### Tier 3: Render- or Simulation-Assisted

Outputs may include:

- full skeletal and facial animation;
- camera and lens tracks;
- physical simulation or contact-aware motion;
- rendered control passes and animatic;
- VFX event passes;
- audio and edit timeline;
- a video-to-video or render-to-video request.

This tier most closely approximates conventional production. The generative model supplies appearance, detail, stylization, or photorealistic transformation while the motion and camera are externally specified.

## 19.22 Worked Cross-Format Example: A Stylized Action Trailer Beat

The following fictional shot integrates performance, action, direction, VFX, and marketing without collapsing them.

### 19.22.1 Directorial Intent

A game protagonist enters frame, reads an incoming threat, steps in, pivots, performs a staged punch-like strike that stops just short of an opponent, and recovers into a controlled stance. The audience should perceive speed and mastery rather than uncontrolled rage. The trailer must reveal the protagonist’s signature gauntlet clearly and end on a brand-safe hero frame.

### 19.22.2 YAML Authoring Source

```yaml
schema: "cpcs-authoring/1.1"
document_id: "gameLaunch.teaser.shot07"
extends:
  - "style://gameLaunch/graphic_action@4"
  - "performance://controlled_mastery@2"

shot:
  duration_s: 5.0
  fps: 24

  narrative:
    objective: "demonstrate controlled mastery"
    audience_takeaway: "the protagonist chooses precision over force"

  performance:
    affect:
      experienced:
        knots: [[0.0, -0.15, 0.55, 0.70], [1.4, -0.35, 0.85, 0.82], [5.0, 0.10, 0.38, 0.90]]
      displayed:
        knots: [[0.0, 0.00, 0.30, 0.78], [1.4, -0.10, 0.48, 0.88], [5.0, 0.08, 0.28, 0.92]]
    face:
      - {id: "astra.au04", au: "AU04", peak: 0.22, apex_s: 1.36}
      - {id: "astra.au07", au: "AU07", peak: 0.30, apex_s: 1.52}
    laban:
      preparation: {weight: "light", time: "sustained", space: "direct", flow: "bound"}
      execution: {weight: "strong", time: "sudden", space: "direct", flow: "bound"}
      recovery: {weight: "light", time: "sustained", space: "direct", flow: "free_to_bound"}

  action:
    atoms:
      - {id: "step_in", type: "step_in", interval_s: [0.80, 1.20]}
      - {id: "pivot", type: "rear_foot_pivot", interval_s: [1.15, 1.42]}
      - id: "right_cross"
        type: "punch_like_strike"
        interval_s: [1.28, 1.82]
        safety_mode: "staged_near_contact"
        target: "opponent.head_volume"
        minimum_separation_m: 0.03
      - {id: "opponent_recoil", type: "anticipatory_reaction", interval_s: [1.58, 2.05]}
      - {id: "recovery", type: "return_to_guard", interval_s: [1.82, 2.55]}

  director:
    camera:
      shot_size: "medium_wide"
      angle: "low"
      move: "dolly_in"
      interval_s: [0.00, 1.56]
    editorial:
      impact_frame: {time_s: 1.58, mode: "one_frame_hold"}
      slow_motion: {source_interval_s: [1.42, 1.76], display_scale: 1.8}
      reaction_cut: {time_s: 2.06, optional: true}

  vfx:
    speed_lines: {interval_s: [1.34, 1.62], intensity: 0.55, attach_to: "right_fist"}
    energy_trail: {interval_s: [1.38, 1.74], intensity: 0.42, attach_to: "gauntlet"}
    dust_burst: {time_s: 1.20, source: "rear_foot_pivot", intensity: 0.36}
    camera_shake: {time_s: 1.58, amplitude: 0.18, decay_s: 0.16}
    smear_frame: {time_s: 1.54, body_part: "right_arm", count: 1}

  marketing:
    product_asset: "gauntlet.astra.signature.v6"
    hook_deadline_s: 1.0
    product_hero_interval_s: [2.60, 4.25]
    minimum_product_area_ratio: 0.07
    logo_occlusion_max: 0.03
    end_card: {asset: "gameLaunch.logo_cta.en-US", start_s: 4.25, minimum_hold_s: 0.75}

  constraints:
    - {id: "no_actual_contact", mode: "hard", expression: "fist_target_distance_m >= 0.03"}
    - {id: "gauntlet_visible_at_apex", mode: "hard", expression: "gauntlet_visibility >= 0.75 at 1.58s"}
    - {id: "recovery_before_hero", mode: "hard", expression: "action:recovery.end <= 2.60s"}
```

### 19.22.3 Canonical JSON Responsibilities

The compiler expands the style profiles, converts qualitative intervals into calibrated records, resolves actor and product assets, creates ordered beat/action arrays, maps all times to 120 frames, and stores the slow-motion mapping separately from simulation time. It also derives:

- `step_in` final foot plant at frame 29;
- pivot, pelvis, torso, shoulder, elbow, and fist local-phase order;
- a near-contact event at simulation frame 38;
- the display-time expansion around that event;
- camera pose targets and screen-space gauntlet visibility;
- VFX triggers attached to motion and contact events;
- the hero interval and end-card safe zone.

### 19.22.4 XML Director Envelope

```xml
<cpcs:directorPackage xmlns:cpcs="urn:cpcs:core:1.1"
                      xmlns:act="urn:cpcs:action:1.1"
                      xmlns:vfx="urn:cpcs:vfx:1.1"
                      xmlns:mkt="urn:cpcs:marketing:1.1"
                      id="gameLaunch.teaser.shot07">
  <cpcs:brief>
    Precision, not rage. The strike stops short; the visual language supplies
    the impact while the choreography remains controlled.
  </cpcs:brief>
  <act:event ref="right_cross" audienceMeaning="mastery"/>
  <vfx:event ref="smear_frame" subordinateTo="no_actual_contact"/>
  <mkt:hero asset="gauntlet.astra.signature.v6" interval="2.60s/4.25s"/>
  <cpcs:score href="asset://scores/gameLaunch.teaser.shot07.cpcs.json"
              mediaType="application/cpcs+json" sha256="..."/>
</cpcs:directorPackage>
```

The XML expresses the director’s interpretive priority and references the numerical authority. It does not duplicate every sample.

### 19.22.5 Prompt-Only Compilation

```text
Five-second stylized action-trailer shot, medium-wide from a low angle. Astra
reads an incoming threat with restrained focus, steps in, pivots from the rear
foot, and delivers one precise right-hand strike that visibly stops just short
of the opponent. The motion is direct, tightly bound, strong and sudden only
through the execution, then light and controlled in recovery. Dolly in through
the action. At the near-impact moment, use one restrained smear frame, a brief
fist-attached energy trail, speed lines, a small dust burst at the pivot, and a
short camera impulse; do not show actual contact. Recover by 2.6 seconds and hold
a clean hero view of the signature gauntlet before the end card. No flurry, no
extra strike, no product occlusion, no uncontrolled anger.
```

The compile report marks exact near-contact distance, AU curves, local phases, and product-area thresholds as `evaluation_only` or `compressed_to_text` unless the backend has stronger inputs.

### 19.22.6 Render-Assisted Compilation

A higher-control target package contains:

```text
request.json
prompt.txt
manifest.json
assets/
  astra_identity.png
  gauntlet_signature_v6.glb
  opponent_reference.png
control/
  pose_000000.png ... pose_000119.png
  depth_000000.exr ... depth_000119.exr
  segmentation_000000.png ... segmentation_000119.png
  face_landmarks_000000.jsonl
  camera_6dof.csv
  optical_flow/
  first_frame.png
  last_frame.png
edit/
  timewarp.json
  edit_decision_list.json
vfx/
  gauntlet_trail_mask/
  speed_line_vector_field/
  dust_trigger.json
  camera_impulse.json
marketing/
  product_visibility_target.json
  safe_zones.json
  end_card.png
verification/
  acceptance_constraints.json
```

The generated shot can then be scored independently for choreography, physical plausibility, visual stylization, and marketing communication.

<!-- RAG_CHUNK id="cpcs.structured-verification" title="Structured compiler verification, security, and limitations" concepts="validation checkpoints, compile report, security, YAML safety, XML security, JSON duplicates, model limitations, RAG" -->
## 19.23 Marketing Controls: From “Why It Sells” to Testable Creative Requirements

A marketing department often speaks in causal shorthand: “open with a hook,” “make the product aspirational,” “show the benefit,” or “end on a strong call to action.” A compiler must turn these statements into observable requirements without claiming that the requirements guarantee commercial success.

**[PROPOSED]** CPCS separates five marketing objects:

1. **communication objective** — what the audience should understand;
2. **creative mechanism** — what the shot is hypothesized to make salient or memorable;
3. **production constraint** — what must be visible, audible, readable, and for how long;
4. **variant plan** — which audience, platform, language, duration, and aspect-ratio versions are required;
5. **measurement plan** — how outcomes will be compared after deployment.

| Marketing concept | Structured control | Compilation | Verification |
|---|---|---|---|
| Hook | `hook.deadline_s`, event type, opening information | opening beat, first-frame composition, early action/audio event | target event visible/audible before deadline |
| Product recognition | asset ID, minimum screen area, angle, occlusion, focus | product mask, hero frame, camera/framing constraints | area ratio, sharpness, occlusion, identity match |
| Benefit demonstration | claim ID, action evidence, before/after or causal beat | storyboard/action sequence, caption, voiceover, comparison layout | required evidence event and approved claim association |
| Brand mnemonic | logo, sonic mark, color/shape asset, recurrence | graphic layer, audio cue, repeated visual event | correct asset, duration, placement, non-distortion |
| Call to action | text/audio asset, start, hold, safe zone, locale | title card, subtitle/voiceover, end frame | legibility, duration, localization, safe-zone compliance |
| Platform variant | ratio, duration, crop, caption, sound-off behavior | variant build matrix and reframed shots | no protected subject/product cropped; required text visible |
| Experiment | variant ID, hypothesis, assignment metadata, metric | manifests and analytics tags | outcome joined to exact creative version and digest |

A marketing compiler can create a variant matrix:

```yaml
variant_matrix:
  dimensions:
    aspect_ratio: ["16:9", "9:16", "1:1"]
    duration_s: [6, 15]
    locale: ["en-US", "es-MX"]
    hook: ["action_first", "product_first"]
  invariants:
    - "approved_claim_text"
    - "product_identity"
    - "minimum_logo_hold"
  outputs:
    naming: "{campaign}.{shot}.{aspect_ratio}.{duration_s}.{locale}.{hook}"
```

The system should not infer that the highest arousal, fastest cut rate, largest face, or strongest camera shake will perform best. Those are testable creative variables. Marketing outcomes should be joined to content hashes so that a result refers to the exact compiled and rendered variant.

## 19.24 VFX and Anime Controls as a Separate Causal Layer

Stylized action frequently uses audiovisual devices that do not correspond directly to physical motion. A smear frame may depict several arm positions in one drawing. Speed lines may be anchored in screen space rather than world space. An impact frame may invert colors or hold a pose. A camera shake may begin just after a near-contact event. CPCS represents these as **presentation effects triggered by performance events**.

```yaml
vfx_event:
  id: "impact.accent.01"
  trigger: "action:right_cross.near_contact"
  temporal_offset_s: 0.00
  effects:
    - {type: "smear_frame", frame_count: 1, source: "right_arm"}
    - {type: "impact_flash", duration_frames: 1, blend_mode: "screen"}
    - {type: "camera_impulse", amplitude: 0.18, decay_s: 0.16}
    - {type: "dust_burst", source: "rear_foot", delay_s: -0.30}
  physical_authority: "none"
  protected_regions:
    - "face"
    - "product.logo"
```

`physical_authority: none` means the effect cannot alter the canonical contact distance, support foot, or body trajectory. If the effect is generated inside a video model and cannot be isolated, the verifier still compares the underlying visible motion to the physical score where possible.

The compiler can choose among three implementations:

- **in-model:** include the effect in prompt text or a style reference;
- **conditioned:** supply masks, flow, vector fields, or keyframes that guide the effect;
- **post:** create a compositor or editor event after the base shot is approved.

Postproduction is usually preferable for one-frame flashes, exact title cards, approved logos, and deterministic CTA timing. In-model generation may be useful for integrated dust, cloth interaction, or painterly motion, but it should not be trusted for exact brand typography or hard frame counts without verification.

## 19.25 Security and Robust Parsing

Structured prompting introduces conventional parser and supply-chain risks in addition to model risks. A production compiler should implement the following controls.

### 19.25.1 YAML

- use a restricted safe loader;
- reject application-specific executable tags from untrusted sources;
- limit alias depth, node count, and expansion;
- reject duplicate keys;
- pin the accepted YAML profile;
- normalize line endings and encoding before hashing;
- treat comments as nonsemantic unless a separate annotation field stores them.

### 19.25.2 JSON

- reject duplicate object names rather than accepting parser-dependent behavior, consistent with RFC 8259 interoperability cautions [S51];
- enforce depth, size, string-length, and numeric limits;
- validate against a pinned schema and vocabulary;
- resolve only approved URI schemes;
- apply JSON Patch only after `test` and base-digest checks;
- canonicalize before content-addressed hashing [S61].

### 19.25.3 XML

- disable external entity resolution and untrusted DTD processing;
- limit document depth, entity expansion, and text size;
- validate namespace URIs and schema versions;
- disallow network schema retrieval during ordinary builds; use pinned local copies;
- sanitize XSLT and extension functions; treat stylesheets as executable build code;
- separate mixed narrative content from control elements.

### 19.25.4 Assets and Imports

- allowlist URI schemes such as `asset://`, `style://`, or approved object storage;
- pin immutable versions and digests;
- verify licenses, consent, and claim approvals before compilation;
- block path traversal and remote redirects;
- record every transitive dependency in the manifest.

### 19.25.5 LLM and RAG Boundaries

Retrieved text, director notes, captions, and external XML content are data, not trusted system instructions. An LLM planner should receive clear delimiters, source provenance, and a schema-constrained output contract. Retrieved content cannot override safety, rights, compiler policy, or locked project values. A RAG record should expose `evidence_level`, `source_ids`, `allowed_uses`, and `compiles_to` metadata so that a phrase retrieved from a stylistic example is not mistaken for an established motion law.

## 19.26 Deterministic Verification Checkpoints

The compiler should stop at observable checkpoints. The following command names are illustrative CPCS interfaces rather than existing standards.

### Checkpoint 1: Parse and Validate Sources

```bash
cpcs validate project.yaml --profile yaml-1.2-restricted
```

Expected observable result:

```text
PASS syntax
PASS duplicate-key check
PASS authoring schema
PASS import digests
0 errors, 0 unresolved references
```

### Checkpoint 2: Resolve Inheritance

```bash
cpcs resolve project.yaml --emit resolved.cpcs.json --emit-report resolve_report.json
```

Expected observable result:

```text
PASS 1,842 effective fields
PASS 37 locks
PASS 0 hard conflicts
WARN 2 soft values shadowed
SHA256 <canonical-score-digest>
```

The report must provide a provenance chain for every inherited or overridden path.

### Checkpoint 3: Validate Semantics and Feasibility

```bash
cpcs check resolved.cpcs.json --semantic --timeline --geometry --constraints
```

Expected observable result:

```text
PASS frame count and timebase
PASS monotonic tracks
PASS actor/asset references
PASS contact and avoidance consistency
PASS camera coordinate system
PASS marketing claim/asset approval
0 hard violations
```

### Checkpoint 4: Negotiate Target Capabilities

```bash
cpcs negotiate resolved.cpcs.json --target vendor.model.version
```

Expected result:

```text
native_exact: 14 controls
native_approximate: 5 controls
baked_into_reference: 9 controls
compressed_to_text: 11 controls
evaluation_only: 7 controls
unsupported_error: 0 controls
```

Generation must not proceed when `unsupported_error` is nonzero.

### Checkpoint 5: Compile the Target Package

```bash
cpcs compile resolved.cpcs.json --target vendor.model.version --out build/shot014
```

Expected files:

```text
request.json
prompt.txt
compile_report.json
manifest.json
control/
verification/acceptance_constraints.json
```

Every file is hashed and the manifest records compiler and adapter versions.

### Checkpoint 6: Dry-Run Temporal Alignment

```bash
cpcs inspect build/shot014 --timeline --frames --assets
```

Expected result:

```text
PASS 144 frames at 24 fps
PASS all control passes share frame IDs 0..143
PASS no audio/control drift
PASS all VFX triggers resolve to events
PASS hero interval and CTA interval fit duration
```

### Checkpoint 7: Score a Candidate

```bash
cpcs score candidate_07.mp4 --against resolved.cpcs.json --out candidate_07.metrics.jsonl
```

The result should report intervals, not only one aggregate score:

```text
PASS identity
PASS AU04 apex timing: error 0.041 s
PASS final foot plant slip: 0.013 m/s
PASS near-contact distance: 0.034 m
WARN camera dolly endpoint framing error: 6.2%
PASS product hero visibility: 9.1%
PASS CTA hold: 1.24 s
```

### Checkpoint 8: Revision as a Patch

```bash
cpcs patch resolved.cpcs.json director_pass_03.json-patch --out resolved.v4.cpcs.json
```

The patch should contain a `test` operation for the base document and produce a new canonical digest. The system can then recompile only affected passes.

## 19.27 What Structured Languages Still Cannot Guarantee

A rigorous structured source improves inspectability and repeatability, but it does not eliminate the central uncertainties of generative video.

- A valid FACS curve does not guarantee that a general video model will render the intended muscle action.
- A Laban vector does not uniquely specify motion and may be interpreted differently across performers, annotators, and model calibrations.
- A contact schedule does not guarantee physically plausible momentum unless the motion or simulation layer enforces it.
- A camera instruction in prompt text does not equal an exact camera trajectory.
- An XML tag does not have higher authority than JSON unless the compiler’s precedence rules say so.
- A seed does not universally imply bitwise-identical video across model versions, hardware, or service updates.
- A marketing score does not guarantee attention, recall, click-through, conversion, or sales.
- A large nested prompt can reduce adherence by overloading a backend even when the syntax is valid.

The correct systems claim is therefore limited but useful:

> **Structured languages make cinematic direction addressable; schemas make it validatable; inheritance makes it reusable; compilers make it translatable; native conditioning makes selected controls stronger; and verification makes compliance measurable. None of these steps turns an unsupported control into a guaranteed model capability.**

## 19.28 RAG Design for Structured Prompt and Compiler Knowledge

RAG records for this chapter should carry fields beyond generic text embeddings:

```json
{
  "concept_id": "cpcs.merge.timeline.splice_interval",
  "representation_types": ["yaml_authoring", "canonical_json"],
  "domains": ["camera", "facs", "body_motion"],
  "scope_levels": ["shot", "beat", "event"],
  "compiles_to": ["camera_track", "au_curve", "control_pass"],
  "merge_policy": "splice_interval",
  "evidence_status": "PROPOSED",
  "source_ids": ["S51", "S52", "S58", "S59"],
  "aliases": ["timeline override", "keyframe splice", "partial track replacement"]
}
```

Retrieval should distinguish at least four query intents:

- **definition:** “What does `merge_by_id` mean?”
- **authoring:** “How do I override one beat in YAML?”
- **compilation:** “What can this camera track become for a first/last-frame model?”
- **diagnosis:** “Why was the AU curve reduced to prose?”

The answer should include the relevant schema path, merge policy, source authority, target capability, and expected compile-report status. This makes the paper usable as both a research document and a compiler knowledge base.

---

<!-- RAG_CHUNK id="cpcs.21" title="Storyboard as executable performance score" concepts="storyboard, animatic, beats, timing, directorial workflow" -->
<a id="cpcs-storyboard"></a>
# 20. From Storyboard Panels to Executable Performance Direction

## 20.1 Static Storyboards and Their Missing Information

A storyboard panel efficiently communicates composition, pose, staging, and sequence, but it usually leaves transition dynamics implicit. A production-ready AI control system should treat each panel as a key state embedded in a timed graph rather than as a complete instruction.

For each panel, CPCS adds:

- entry and exit time;
- narrative beat and objective;
- incoming and outgoing motion;
- key pose tolerance;
- gaze and facial state;
- contacts and support;
- camera pose and lens;
- audio or dialogue anchor;
- transition style;
- uncertainty and acceptable variation.

An **executable storyboard** is therefore closer to an animatic plus motion score.

## 20.2 Beat Sheet

A beat sheet is a human-readable summary of the score:

| Time | Narrative beat | Face and gaze | Body and Laban | Contact/physics | Camera/audio |
|---:|---|---|---|---|---|
| 0.00 | enters with controlled urgency | gaze on partner; low facial activity | quick direct walk; bound flow | alternating foot contacts | medium tracking shot |
| 2.34 | notices blood | gaze drops | deceleration begins | next foot prepares final plant | dolly begins |
| 2.45 | recognition | AU event onset | torso contains; shape encloses | left foot locks | dialogue stops |
| 2.78 | fear leaks through | facial apex; breath interrupt | high tension; near-freeze | COM settles over support | close-up achieved |
| 3.28 | regulation returns | blink and gaze recovery | flow remains bound | no step | camera holds |
| 4.00 | shot end | restrained display | stable posture | planted | cut option |

This table is not the control data itself; it is an editorial view generated from CPCS.

## 20.3 Director, Actor, Choreographer, and Cinematographer Views

One score can expose specialized views:

- **director view:** objectives, beats, affect, performance alternatives, camera and edit;
- **actor view:** intention, subtext, gaze, breath, body initiation, relationship;
- **animator view:** key poses, curves, phases, contacts, constraints;
- **stunt view:** distance, contact type, impulse class, reaction, safety offset;
- **cinematographer view:** lens, camera path, framing, focus, light continuity;
- **ML engineer view:** control channels, model adapters, confidence, loss weights;
- **editor view:** sync points, handles, transition options, continuity.

This role-based projection prevents a technical schema from becoming unusable to creative collaborators.

## 20.4 Directorial Override

Retrieved and generated plans remain subordinate to explicit creative direction. Overrides are stored as first-class records:

```yaml
director_override:
  id: "ovr.shot04.07"
  target: "tracks.face.mara.au05.peak"
  previous_value: 0.31
  new_value: 0.18
  reason: "too overt; audience should read fear from breath and body first"
  author: "director"
  timestamp: "2026-07-18T15:42:00-06:00"
  lock: true
```

Subsequent planners must preserve locked overrides unless a constraint conflict is reported.

## 20.5 Variant Generation

A director may request three controlled variants:

- Variant A: fear leaks through the eyes;
- Variant B: fear leaks through a swallowed breath and jaw tension;
- Variant C: face remains controlled; the body retreats by 4 cm.

All variants share blocking, contact, camera, dialogue, identity, and shot duration. This is a more informative creative experiment than generating three uncontrolled random seeds.

---

<!-- RAG_CHUNK id="cpcs.22" title="Worked example dialogue close-up" concepts="worked example, FACS, affect masking, close-up" -->
<a id="cpcs-example-dialogue"></a>
# 21. Worked Example A: Dialogue Close-Up With Concealed Fear

## 21.1 Directorial Instruction

> During the sentence, she remains socially composed and reassuring. On the final word, she realizes he knows the truth. The audience should see the fear before he does. Do not turn it into a conventional horror reaction.

## 21.2 Narrative Decomposition

- **objective:** reassure and maintain control;
- **obstacle:** recognition that the deception has failed;
- **subtext:** fear rises while display remains regulated;
- **audience asymmetry:** camera reveals a subtle cue unavailable to the other character;
- **turning point:** final word;
- **negative constraint:** no large startle or categorical “scared face.”

## 21.3 Affect Plan

Experienced affect:

- valence moves from mildly negative to strongly negative;
- arousal rises rapidly at the final word;
- dominance/control drops, then partially recovers.

Displayed affect:

- remains near neutral-positive through the sentence;
- arousal increases only moderately;
- dominance remains higher than experienced dominance.

The masking gap peaks shortly after the final word.

## 21.4 Facial Plan

A candidate facial plan might use:

- stable gaze and low AU activity during the reassuring phrase;
- a brief gaze fixation or reduced saccade rate before recognition;
- low-intensity upper-face change with delayed onset;
- restrained lower-face tension coordinated with speech release;
- a breath interruption;
- one recovery blink after the audience has registered the cue.

**[CAUTION]** The exact AU selection is a directorial hypothesis, not a universal signature of concealed fear. The system should generate alternatives and allow the director to inspect the curves.

Example event plan:

```yaml
face_plan:
  final_word_end_s: 2.160
  events:
    - id: "brow_tension"
      au: "AU04"
      onset_s: 2.125
      apex_s: 2.310
      offset_s: 2.760
      peak: 0.22
      side: "bilateral"
    - id: "lid_change"
      au: "AU05"
      onset_s: 2.145
      apex_s: 2.285
      offset_s: 2.480
      peak: 0.14
      side: "bilateral"
    - id: "jaw_control"
      control_type: "jaw_and_lip_tension"
      onset_s: 2.180
      apex_s: 2.420
      offset_s: 2.980
      peak: 0.27
    - id: "recovery_blink"
      control_type: "blink"
      onset_s: 2.820
      duration_s: 0.135
```

## 21.5 Body Plan

Even in a close-up, the neck, shoulders, breath, and torso contribute:

- pre-recognition: sustained, bound, direct presentation;
- recognition: brief increase in bound Flow and strong Weight through isometric containment;
- Shape: slight enclosing without a large retreat;
- head remains oriented to the other actor while eyes carry the first change;
- breath pauses or becomes shallow.

## 21.6 Camera Plan

The audience must perceive a subtle cue. The camera therefore:

- holds a close-up or moves from medium close-up to close-up;
- places the other actor near camera axis so gaze change remains small;
- reaches final framing just before the recognition apex;
- avoids camera shake or a dramatic push that would overstate the beat;
- maintains sufficient depth of field for the eyes and mouth.

## 21.7 Generator Conditions

A pose-to-video or image-to-video model may receive:

- identity reference;
- head-pose and gaze sequence;
- AU embeddings or facial landmarks derived from a rig;
- audio and viseme alignment;
- shoulder/torso pose maps;
- camera trajectory;
- text describing scene and performance objective;
- negative constraints against exaggerated startle.

## 21.8 Verification

Verification checks:

- final-word alignment;
- AU onset, apex, and intensity;
- gaze continuity;
- speech synchronization;
- breath interruption timing if observable;
- identity preservation;
- absence of unintended large head movement;
- director ratings: “audience sees it,” “other character plausibly misses it,” and “not melodramatic.”

---

<!-- RAG_CHUNK id="cpcs.23" title="Worked example expressive walk" concepts="worked example, walk, gait, Laban, affect" -->
<a id="cpcs-example-walk"></a>
# 22. Worked Example B: A Fast Walk That Conceals Panic

## 22.1 Directorial Instruction

> She walks quickly down the corridor toward him. She wants to look in control, but her timing is slightly too urgent. At the last step she sees the injury, freezes, and tries to recover before speaking.

## 22.2 Blocking and Timing

- path length: 2.1 m;
- duration to arrival: 2.45 s;
- five planned contacts;
- final left-foot plant is locked to the recognition beat;
- no additional step during the freeze;
- recovery begins after a 0.45 s containment interval.

## 22.3 Affect and Display

Experienced arousal rises throughout the approach. Displayed arousal remains lower. The discrepancy is expressed through gait timing rather than a large facial expression: cadence is slightly faster than the social context requires, and deceleration begins late.

## 22.4 Laban Profile

Approach:

- Weight: moderate;
- Time: urgent/sudden tendency;
- Space: direct;
- Flow: bound;
- Shape: advancing with controlled torso.

Recognition/freeze:

- Weight: stronger through sudden loading of the final foot;
- Time: sudden stop;
- Space: remains focused;
- Flow: highly bound;
- Shape: slight sink and enclose.

## 22.5 Motion Plan

The root follows a smooth corridor path. Speed rises, holds, then decelerates late:

\[
v(t)=
\begin{cases}
\text{ease-in to }1.15\text{ m/s}, & 0\le t<0.45,\\
1.15\text{ m/s with small variation}, & 0.45\le t<1.95,\\
\text{late deceleration}, & 1.95\le t<2.45,\\
0, & 2.45\le t<2.90.
\end{cases}
\]

The final step absorbs momentum through ankle, knee, hip, and torso rather than freezing all joints on one frame. The head and gaze change slightly before the full-body stop, reflecting visual recognition.

## 22.6 Contact Plan

```yaml
contacts:
  - {time_s: 0.18, foot: left, type: initial_contact}
  - {time_s: 0.72, foot: right, type: initial_contact}
  - {time_s: 1.28, foot: left, type: initial_contact}
  - {time_s: 1.84, foot: right, type: initial_contact}
  - {time_s: 2.45, foot: left, type: final_plant, hold_until_s: 4.0}
```

The exact schedule should be solved against actor morphology and path; it is not a universal gait template.

## 22.7 Camera Plan

A medium tracking shot shows the urgency and full-body timing. The camera begins a restrained push during the final two steps and resolves to a tighter composition after recognition. Camera speed is designed so actor movement remains readable rather than canceled entirely.

## 22.8 Verification

Key metrics include:

- arrival-time error under 20 ms;
- final foot-contact error under one frame;
- planted-foot slip below production threshold;
- no ground penetration or floating;
- late-deceleration profile preserved;
- Laban Time and Flow rated as urgent and controlled;
- facial leakage occurs after gaze recognition, not before;
- camera push does not obscure the stop.

---

<!-- RAG_CHUNK id="cpcs.24" title="Worked example fight beat" concepts="worked example, punch, contact, local phase, camera" -->
<a id="cpcs-example-fight"></a>
# 23. Worked Example C: Controlled Fight Beat

## 23.1 Directorial Instruction

> The first fighter throws a right cross as a warning, not a knockout attempt. The second fighter sees it late, slips most of it, and takes a glancing contact at the left jaw. The strike should feel fast and credible, but both characters remain balanced for the next beat. Keep the geography readable.

## 23.2 Narrative and Safety Interpretation

- intention is intimidation, not maximal harm;
- contact is glancing and limited;
- defender reaction is late but not preemptive;
- both characters must recover to playable positions;
- camera should reveal preparation, path, and reaction;
- the score may use staged near-contact if the production does not require actual geometric collision.

## 23.3 Motion-Atom Graph

```text
rear-foot pressure ──► rear-foot pivot ──► pelvis rotation
                                      └──► torso rotation
pelvis rotation ─────────────────────────► shoulder advance
shoulder advance ──► elbow extension ───► fist trajectory
attacker gaze ───────────────────────────► target stabilization

defender visual cue ─► head slip ─► torso slip ─► left-jaw near/contact
contact event ───────► head reaction ─► torso absorption ─► stance recovery
```

Each edge has an offset range. The fist is not permitted to reach the target before the supporting chain develops.

## 23.4 Laban Profile

Attacker:

- Weight: strong but below maximal;
- Time: sudden;
- Space: highly direct;
- Flow: moderately bound to permit recovery.

Defender:

- Time: sudden after delayed onset;
- Space: direct lateral slip;
- Flow: bound through the contact, then released into recovery;
- Shape: retreat and slight enclose.

## 23.5 Contact and Distance

```yaml
interaction_event:
  id: "right_cross_glance"
  attacker: "fighter_a.right_fist"
  defender: "fighter_b.left_jaw"
  onset_s: 0.58
  contact_s: 0.94
  release_s: 1.02
  type: "glancing_contact"
  desired_separation_m: 0.0
  contact_normal_world: [0.78, 0.10, 0.62]
  impulse_class: "low_to_moderate"
  defender_reaction_delay_s: 0.035
  max_penetration_m: 0.008
  mode: "hard"
```

For staged near-contact, `desired_separation_m` might be 0.02–0.05 m and camera perspective would be constrained to preserve apparent contact.

## 23.6 Local Phase Plan

| Component | Phase onset | Peak/event | Recovery |
|---|---:|---:|---:|
| rear foot | 0.45 s | pivot 0.68 s | 1.18 s |
| pelvis | 0.50 s | rotation peak 0.82 s | 1.26 s |
| torso | 0.55 s | rotation peak 0.88 s | 1.30 s |
| shoulder | 0.60 s | advance peak 0.92 s | 1.34 s |
| fist | 0.62 s | contact 0.94 s | guard 1.42 s |
| defender head | 0.77 s | slip peak 0.96 s | 1.38 s |
| defender torso | 0.80 s | absorption 1.03 s | 1.48 s |

The table is illustrative. A solver adapts it to the actors and exact distance.

## 23.7 Camera Plan

- 35–50 mm equivalent lens to preserve spatial clarity;
- three-quarter angle showing both stances;
- no cut before preparation is readable;
- limited camera impulse at contact, lower amplitude than the body reaction;
- maintain screen direction and both actors’ feet when possible;
- optional cut after recovery to the next beat.

## 23.8 Verification

- contact or near-contact occurs within tolerance;
- no early defender reaction unless marked as anticipation;
- fist path and contact normal match the score;
- rear-foot, pelvis, torso, and arm sequence is ordered correctly;
- both support states remain feasible;
- penetration remains below threshold;
- impulse is compatible with a glancing hit;
- attacker returns to guard;
- camera preserves geography;
- director ratings distinguish “warning” from “knockout attempt.”


<!-- RAG_CHUNK id="cpcs.25" title="Evaluation framework" concepts="evaluation, compliance, video quality, motion quality, human study" -->
<a id="cpcs-evaluation"></a>
# 24. Evaluation: Measuring Directorial Compliance Separately From Visual Quality

## 24.1 The Evaluation Principle

A generated shot can be photorealistic and still fail the direction. It can also follow the motion score while containing visual artifacts. CPCS therefore separates evaluation into six families:

1. **control compliance;**
2. **temporal and causal correctness;**
3. **physical plausibility;**
4. **appearance and identity consistency;**
5. **semantic and cinematic effectiveness;**
6. **general video quality and diversity.**

No single scalar should replace the full report.

## 24.2 Facial Compliance

Recommended facial metrics include:

- per-AU intensity mean absolute error;
- Pearson correlation or concordance correlation over AU curves;
- onset, apex, and offset timing error;
- left/right asymmetry error;
- head-pose error;
- gaze-target accuracy;
- blink-event timing;
- lip-sync or viseme alignment;
- identity similarity and facial-region temporal stability.

Event timing error is:

\[
E_{event}=|\hat t_{event}-t_{event}|.
\]

A shot can have low framewise AU error but poor event timing. Both must be reported.

## 24.3 Affect Compliance

Affect estimators can compare target and observed trajectories using concordance correlation coefficient, dynamic time warping, or curve distance. Separate scores should be computed for experienced-affect proxies and displayed affect only where observable.

Human evaluation should ask:

- What affective trajectory did viewers perceive?
- At what time did the emotional change become noticeable?
- Did the display appear controlled, leaked, exaggerated, or ambiguous?
- Did modalities agree or intentionally conflict?

The study must avoid presenting one annotator’s emotional inference as ground truth.

## 24.4 Laban Compliance

Laban evaluation should combine trained-coder ratings and computational features. Report:

- target-versus-rated Effort factors;
- Shape tendencies;
- body initiation and sequencing;
- confidence and inter-rater agreement;
- action-identity preservation;
- differences across camera views.

A generated motion may satisfy a direct-path metric while still being judged indirect in attentional or expressive terms. Automated proxies must therefore be validated against human coding.

## 24.5 Kinematic Compliance

Measures include:

- world-space and root-relative MPJPE;
- joint rotation error;
- root path and facing error;
- endpoint trajectory error;
- key-pose timing and distance;
- velocity and acceleration error;
- bone-length variance;
- body-shape consistency.

For controlled joints or body parts, report errors separately rather than averaging them with unconstrained joints.

## 24.6 Phase and Rhythm

Report:

- global phase error;
- local phase error by body part;
- contact-to-phase consistency;
- cadence and stride timing;
- temporal ordering of kinetic-chain events;
- music or dialogue beat alignment.

For circular phase, use circular distance. For nonperiodic events, compare normalized progress and event boundaries.

## 24.7 Contact and Physical Plausibility

Recommended measures include:

- contact classification precision and recall;
- contact-time error;
- distance error during intended contact or near-contact;
- planted-foot velocity or skating ratio;
- floating distance;
- ground and body penetration depth;
- hand–prop attachment error;
- collision count and duration;
- center-of-mass support or dynamic-balance measures;
- jerk and acceleration outliers;
- momentum and reaction-direction consistency.

Recent motion benchmarks and toolboxes increasingly report foot skating, floating, penetration, and jerk, reflecting the need for explicit physical metrics (Zhang et al., 2026 [S49]; Liao et al., 2025 [S50]). However, individual metrics can be gamed: a motion can avoid foot sliding by floating above the floor. Metrics must be interpreted jointly.

A simple skating ratio is:

\[
R_{skate}=\frac{\#\{t:q_{foot}(t)=1\land \|\dot p_{foot}^{xy}(t)\|>\epsilon_v\}}{\#\{t:q_{foot}(t)=1\}}.
\]

Thresholds must be normalized for scale, frame rate, and shot type.

## 24.8 Interaction and Causality

For two-person or human–object scenes, evaluate:

- joint-pair distance constraints;
- correct actor and object roles;
- approach, avoidance, or contact direction;
- cue–reaction ordering;
- reaction delay;
- impact and follow-through coherence;
- prop continuity;
- visibility of the intended interaction;
- absence of unintended intersections.

A causality violation occurs when an effect visibly precedes its trigger without a planned anticipation cue.

## 24.9 Camera Compliance

Measures include:

- camera translation and rotation error;
- focal-length and focus error;
- subject screen-position deviation;
- framing-category accuracy;
- occlusion and visibility;
- horizon stability where intended;
- actor/camera motion disentanglement;
- edit-point and reveal timing;
- screen-direction continuity.

The evaluation should be performed in both world coordinates and image space. A small world-space camera error can cause a large compositional error with a long lens.

## 24.10 Identity and Appearance

Report:

- identity embedding consistency;
- body-shape and costume consistency;
- face and hand artifact rates;
- texture flicker;
- background and prop continuity;
- lighting continuity;
- occlusion recovery quality.

Identity measures should be selected with consent and demographic-bias analysis. They should not be the only criterion for a stylized or nonphotorealistic character.

## 24.11 General Video Metrics

Fréchet Video Distance was proposed to compare distributions of real and generated video features and initially showed correlation with human judgments (Unterthiner et al., 2018 [S42]). Fréchet Video Motion Distance focuses more explicitly on motion consistency using keypoint-derived motion features (Liu et al., 2024 [S44]). These metrics are useful for system-level comparison but do not directly prove compliance with a specific score.

Temporal compositionality benchmarks evaluate whether specified state transitions are completed (Feng et al., 2024 [S45]). The WYD benchmark evaluates fine-grained categories of controllable human video generation across actions, interactions, and motion (Bugliarello et al., 2025 [S48]). CPCS can complement such benchmarks by providing exact temporal and control targets.

**[CAUTION]** Distribution metrics can contain content bias and may reward superficial similarity. They should never substitute for task-specific and human evaluation.

## 24.12 Director and Viewer Studies

Two human-study populations are useful.

### Expert/director study

Experts rate:

- compliance with the brief;
- editability and usefulness of the control interface;
- performance specificity;
- action readability;
- physical credibility;
- appropriateness of camera and timing;
- time required to reach an approved take.

### Viewer study

Viewers rate or identify:

- perceived action and affect;
- timing of the dramatic turn;
- causal comprehension;
- character intention;
- realism and artifact severity;
- whether alternative variants communicate the intended distinction.

Blind randomized comparisons are preferable. The study should report effect sizes and inter-rater reliability, not only preference percentages.

## 24.13 Multi-Objective Scorecard

A production scorecard may use thresholds rather than a single weighted average:

```yaml
gates:
  hard_constraint_pass_rate: ">= 0.98"
  identity_score: ">= 0.90"
  contact_timing_error_ms: "<= 25"
  foot_skate_ratio: "<= 0.03"
  penetration_p95_m: "<= 0.012"
  camera_screen_error_px: "<= 12"
rankers:
  director_compliance_rating: "maximize"
  affect_trajectory_ccc: "maximize"
  laban_rating_match: "maximize"
  fvmd: "minimize"
  temporal_artifact_score: "minimize"
```

A video that fails a hard gate is rejected even if its aggregate visual-quality score is high.

---

<!-- RAG_CHUNK id="cpcs.26" title="Experimental research program" concepts="ablation, hypotheses, benchmarks, study design" -->
<a id="cpcs-experiments"></a>
# 25. Experimental Program for Testing CPCS

## 25.1 Core Hypotheses

**H1: Structured temporal controls improve compliance.** A model conditioned on timed CPCS events will achieve lower event-boundary error and higher director ratings than the same model conditioned on prose alone.

**H2: Separating affect from expression improves controllability.** Independent VAD and FACS tracks will produce more reliable masking and leakage effects than one emotion label or one affect vector alone.

**H3: Laban controls improve expressive variation while preserving action identity.** Adding Laban guidance will increase expert-rated movement-quality match without significantly reducing action-recognition accuracy.

**H4: Phase and contact controls improve physical plausibility.** Adding global/local phase and contact constraints will reduce skating, penetration, premature reactions, and interaction-distance error.

**H5: Decoupled camera and performer control improves shot fidelity.** Separate camera and body tracks will reduce camera–motion entanglement and screen-composition error.

**H6: Retrieval with provenance improves planner reliability.** A structured RAG planner will produce fewer unsupported control mappings and higher template compatibility than an unguided LLM planner.

## 25.2 Factorial Ablation

A recommended ablation sequence is:

| Condition | Text | Pose/kinematics | FACS | VAD | Laban | Phase/contact | Camera | RAG |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | ✓ |  |  |  |  |  |  |  |
| B | ✓ | ✓ |  |  |  |  |  |  |
| C | ✓ | ✓ | ✓ |  |  |  |  |  |
| D | ✓ | ✓ | ✓ | ✓ |  |  |  |  |
| E | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |
| F | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |
| G | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| H | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

Additional ablations remove experienced/displayed affect separation, local phase, physical refinement, or provenance filtering.

## 25.3 Task Suite

The task suite should include:

- dialogue close-up with subtle affect transition;
- masked versus overt emotion;
- walk at fixed path with varied Laban qualities;
- walk-to-run and run-to-stop transitions;
- sit, stand, reach, and object handoff;
- two-person embrace, avoidance, and confrontation;
- fight beats with contact and staged near-contact;
- multi-shot continuity with camera changes;
- prop manipulation and occlusion;
- long-duration beat sequence with repeated identity recovery.

Each task should include hard timing anchors and acceptable creative variation.

## 25.4 Baselines

Compare against:

- text-only generation;
- text plus generic pose sequence;
- reference-video driving;
- motion-diffusion plus pose-to-video;
- end-to-end controllable video models;
- 3D animation plus generative rendering;
- human-authored keyframe or motion-capture reference where available.

The goal is not only to outperform one model but to determine which layers contribute under different architectures.

## 25.5 Reproducibility

A reproducible evaluation should release or record:

- exact CPCS scores;
- model and checkpoint identifiers;
- control adapters and compiler versions;
- random seeds;
- sampling parameters;
- calibration profiles;
- source and asset licenses;
- evaluation code and thresholds;
- human-study protocol;
- failed and successful generations.

Reporting only selected showcase videos prevents reliable assessment of directability.

## 25.6 Efficiency Metrics

Production usefulness also depends on cost. Measure:

- number of generations to approval;
- human editing time;
- compute per second of video;
- proportion of revisions achievable without full regeneration;
- cache reuse across variants;
- latency from score edit to preview;
- model calls per accepted shot.

A structured system may add planning overhead but reduce expensive blind resampling.

---

<!-- RAG_CHUNK id="cpcs.27" title="Failure modes" concepts="failure analysis, control conflicts, model limits, diagnostics" -->
<a id="cpcs-failures"></a>
# 26. Failure Modes and Diagnostic Repairs

## 26.1 Semantic Overcommitment

**Failure:** The planner converts an ambiguous emotional note into one stereotyped AU pattern.

**Diagnosis:** Low diversity of retrieved templates; missing character and context constraints.

**Repair:** Return multiple interpretations, expose provenance, and require director selection for low-confidence mappings.

## 26.2 Affect–Display Collapse

**Failure:** Experienced fear and displayed composure are averaged into a generic worried expression.

**Diagnosis:** One affect stream or one global embedding controls all modalities.

**Repair:** Separate experienced and displayed affect; assign leakage to selected modalities and preserve masking elsewhere.

## 26.3 AU Overfitting or Facial Rig Mismatch

**Failure:** Correct AU values create exaggerated or identity-distorting facial deformation.

**Diagnosis:** Canonical-to-rig mapping is uncalibrated.

**Repair:** Apply performer-specific nonlinear calibration; reduce intensity; use perceptual rather than coefficient-only verification.

## 26.4 Speech–Expression Conflict

**Failure:** Emotional mouth controls break phoneme articulation.

**Diagnosis:** AU and viseme tracks are composed additively without priority.

**Repair:** Enforce hard speech contacts, resolve region conflicts, and use learned coarticulation.

## 26.5 Laban Label Without Motion Consequence

**Failure:** The metadata says “strong and sudden,” but the motion remains unchanged.

**Diagnosis:** Laban values are present only in text tokens or injected too weakly.

**Repair:** Connect them to measurable features, use guided sampling or style-conditioned motion generation, and verify with both features and trained coders.

## 26.6 Smooth but Weightless Motion

**Failure:** Trajectories are smooth, but contacts, loading, and momentum are absent.

**Diagnosis:** Optimization emphasizes jerk and pose error only.

**Repair:** add support, contact, center-of-mass, impulse, and recovery constraints; use physics-based refinement where needed.

## 26.7 Foot Skating

**Failure:** A planted foot moves relative to the ground.

**Diagnosis:** root and limb trajectories are generated independently; contact state is missing or lost during video rendering.

**Repair:** lock foot in world space during contact; adjust pelvis/root through inverse kinematics; condition the video model on contact-aware pose or flow; verify after rendering.

## 26.8 Floating and Penetration Tradeoff

**Failure:** Reducing penetration causes the body to float, or reducing sliding increases penetration.

**Diagnosis:** metrics or constraints are optimized independently.

**Repair:** jointly solve floor height, contact state, foot velocity, and root motion; evaluate multiple physical metrics.

## 26.9 Premature Reaction

**Failure:** A defender moves before the strike or a character reacts before seeing the trigger.

**Diagnosis:** action labels are generated globally without cue–response timing.

**Repair:** encode cue time, perception delay, reaction onset, and contact; apply causal-order constraints.

## 26.10 Camera–Actor Entanglement

**Failure:** a camera pan causes the actor to drift, deform, or reverse movement.

**Diagnosis:** the model represents all optical flow as one motion source.

**Repair:** provide separate camera pose and actor motion tokens; use geometry-aware conditioning; verify in world and image coordinates.

## 26.11 Identity Drift Under Extreme Motion

**Failure:** face or body identity changes during occlusion, profile view, or fast action.

**Diagnosis:** weak identity reference, insufficient view coverage, or motion and identity entanglement.

**Repair:** multi-view identity conditioning, 3D/4D avatar representation, identity loss scheduling near occlusions, or local resynthesis.

## 26.12 Overconstraint

**Failure:** the output becomes stiff or visually degraded.

**Diagnosis:** too many controls are marked hard or guidance weights are excessive.

**Repair:** identify minimal sufficient constraints; downgrade style preferences; allow a motion prior to fill unspecified degrees of freedom.

## 26.13 Underconstraint

**Failure:** output varies unpredictably across seeds.

**Diagnosis:** critical timing, contact, camera, or identity variables remain implicit.

**Repair:** convert the relevant director note into explicit events or trajectories; preserve stochasticity elsewhere.

## 26.14 RAG Template Contamination

**Failure:** a retrieved template imports irrelevant gender, age, disability, genre, or cultural assumptions.

**Diagnosis:** dense similarity without metadata filtering or provenance review.

**Repair:** structured filters, bias audits, neutral canonical templates, performer-specific calibration, and director approval.

## 26.15 Metric Gaming

**Failure:** a model improves a metric while looking worse—for example, reducing foot skate by floating.

**Diagnosis:** single-metric optimization.

**Repair:** multi-metric gates, visual inspection, human studies, and adversarial test cases.

---

<!-- RAG_CHUNK id="cpcs.28" title="Ethics and governance" concepts="consent, deepfakes, bias, accessibility, labor, provenance" -->
<a id="cpcs-ethics"></a>
# 27. Ethics, Rights, and Governance

## 27.1 Identity and Performance Rights

A system capable of controlling facial and bodily performance can create persuasive synthetic performances. It should require clear authorization for identifiable people, performers, or proprietary characters. Consent should specify:

- identity use;
- voice and facial use;
- body and motion use;
- training, inference, editing, and distribution rights;
- project and duration scope;
- derivative or transferable rights;
- revocation and retention policy;
- compensation and credit.

A performer’s motion and expressive style can be distinctive even when the face is changed. Governance should not treat motion capture as ownerless technical data.

## 27.2 Deepfake and Deception Risk

Precise AU, gaze, and performance control can be used to fabricate statements or emotional displays. Systems should support:

- consent verification;
- visible or machine-readable provenance;
- content credentials where available;
- audit logs;
- restricted identity models;
- disclosure policies;
- detection and incident response.

Technical provenance does not eliminate social harm, but it improves accountability.

## 27.3 Emotional Inference and Pseudoscience

FACS and VAD should not be used to claim certain knowledge of real people’s internal emotions, honesty, intent, or mental health. CPCS uses these systems to author intended portrayals and measure visible features. It rejects the inference that one facial or body pattern proves a private state.

## 27.4 Cultural and Individual Variation

Gesture, gaze, interpersonal distance, emotional display, and movement quality vary across cultures, communities, contexts, and individuals. A retrieval system trained on narrow film conventions can reproduce stereotypes. Templates should record population and context, and the system should prefer performer-specific direction over demographic assumptions.

## 27.5 Disability and Non-Normative Movement

Metrics such as symmetry, gait regularity, or “physical normality” can penalize authentic disabled movement. CPCS should evaluate against the intended performer profile and action, not a single normative body model. Accessibility requires:

- configurable body topology and assistive devices;
- mobility-aid contacts;
- performer-specific ranges;
- nonpathologizing language;
- evaluation that distinguishes artifact from intentional movement.

## 27.6 Stunt and Violence Governance

Fight generation should be used for fictional choreography, previsualization, safe performance design, and related legitimate applications. Templates should distinguish cinematic illusion from real impact and should not be presented as instructions for harming people. Human stunt professionals remain essential for real production safety.

## 27.7 Labor and Creative Attribution

A directorial model may retrieve or emulate patterns derived from actors, animators, choreographers, and cinematographers. Production systems should retain source and contributor attribution, honor labor agreements, and avoid representing generated performance as a substitute for consented creative work without appropriate terms.

## 27.8 Dataset and RAG Governance

The knowledge store must support:

- provenance and source hashes;
- consent and license scopes;
- access control;
- deletion and revocation;
- versioning and audit trails;
- separation of public research from private production assets;
- bias and coverage reports;
- restrictions on biometric export.

---

<!-- RAG_CHUNK id="cpcs.29" title="Limitations" concepts="limitations, uncertainty, research gaps" -->
<a id="cpcs-limitations"></a>
# 28. Limitations

CPCS is a proposal, not a validated standard. Several limitations remain.

**Representation burden.** Detailed scores can be expensive to author. The framework depends on good defaults, retrieval, reference analysis, and role-specific interfaces so users edit only consequential variables.

**Estimator error.** AU, gaze, pose, camera, contact, and affect estimators are imperfect. Verification must include uncertainty and cannot assume re-extracted controls are ground truth.

**Laban operationalization.** No small set of kinematic metrics fully captures Laban practice. Computational mappings require collaboration with trained movement analysts and validation across styles and bodies.

**Physics–cinema mismatch.** Cinematic motion can intentionally violate strict physics through timing compression, cheats, wire work, or stylization. Physical plausibility should serve the shot, not impose realism where it is not desired.

**Model capacity.** A score can specify controls that a target generator cannot follow. The compiler must know model capabilities and report unsupported features.

**Long-horizon consistency.** Maintaining identity, props, spatial layout, affect, and performance continuity across many shots remains difficult. Sequence-level memory and scene representations are needed.

**Ambiguity.** Directorial language often benefits from interpretive openness. Overformalization can narrow creative discovery. CPCS therefore supports alternatives, preferences, and stochastic realization.

**Evaluation validity.** Automatic metrics may not reflect dramatic effectiveness. Expert and audience studies remain necessary.

---

<!-- RAG_CHUNK id="cpcs.30" title="Future research" concepts="research agenda, multimodal control, world models, standards" -->
<a id="cpcs-future"></a>
# 29. Research Agenda

## 29.1 A Shared Open Performance-Score Standard

A practical next step is an open schema for timed performance controls, analogous to interchange formats in animation and audio. It should support extensible tracks, typed constraints, provenance, and conversion among rigs and models. The CPCS schema is one proposed starting point.

## 29.2 Learned Compiler From Direction to Score

Research should compare:

- direct LLM score generation;
- retrieval-augmented generation;
- symbolic planning with constraint solving;
- multimodal planning from rehearsal video and storyboards;
- interactive planning with director corrections.

The objective is not only score accuracy but reduction in approved-shot iteration cost.

## 29.3 Joint Face–Body–Voice Modeling

Most models specialize in one modality. Future work should learn synchronized face, gaze, breath, voice, and body behavior while retaining independent controls. Masking and leakage provide a demanding test because modalities must intentionally disagree in a coherent way.

## 29.4 Body-Part Local Phase as an Editable Interface

Local phase should be exposed to animators and directors through event language rather than raw oscillators. Research can map instructions such as “hips lead the shoulders by four frames” or “the hand arrives while the torso continues” into phase constraints.

## 29.5 Differentiable Cinematography

Camera solvers could optimize visibility, composition, emotional emphasis, continuity, and motion readability while respecting director constraints. The objective must be interpretable and allow human override.

## 29.6 Physics-Aware Video Diffusion

Future video models may integrate 3D bodies, scene geometry, contacts, and dynamics directly rather than receiving only projected pose maps. Hybrid world models and differentiable simulators could improve impacts, object interaction, cloth, and long-horizon consistency.

## 29.7 Retrieval of Performance, Not Stereotype

RAG research should focus on compositional, context-aware retrieval that can combine neutral action mechanics with project-specific expressive choices. Template diversity and bias evaluation are central.

## 29.8 Causal Evaluation

Benchmarks should test whether controlled changes produce the intended isolated effect. For example, varying only Laban Weight should alter perceived weight without changing action identity or camera. Causal interventions are more informative than broad correlations.

## 29.9 Director-in-the-Loop Learning

Edits made by directors can become preference data, but only with consent and project governance. Models can learn individual directorial grammars while preserving a trace of which controls were changed and why.

## 29.10 Cross-Shot Performance Continuity

A sequence-level score should track unresolved affect, fatigue, injury, prop state, costume, gaze relations, and physical position across cuts. Continuity is not only visual identity; it includes the state of the performance.

## 29.11 Benchmarks for Reference-Video Distillation

Future work should evaluate the inverse pipeline on videos with independently verified shot boundaries, actor tracks, Action Units, 2D/3D pose, contacts, camera motion, dialogue timing, and editorial annotations. Evaluation should distinguish observation accuracy from interpretive agreement and should test whether a reverse-compiled score can regenerate the intended causal and temporal grammar without copying identity or protected surface content. Multiview and ego/exo datasets can support camera/body disentanglement, while production-grade benchmarks must also include fast cuts, VFX, occlusion, UGC framing, and incomplete evidence.

---

<!-- RAG_CHUNK id="cpcs.video.00" title="Reference-video distillation overview" concepts="reference video, inverse direction, Video Observation Graph, reverse compiler" -->
<a id="cpcs-video-distillation"></a>
# 30. Reference-Video Distillation and Reverse Directorial Compilation

This section extends CPCS from **forward compilation**—direction to generated video—into **inverse compilation**—observed video to an editable directorial score. It defines **Reference-Video Distillation (RVD)** as the evidence-preserving decomposition of a known video into semantic, temporal, geometric, performative, cinematic, auditory, VFX, and marketing observations. It defines **Reverse Directorial Compilation (RDC)** as the conversion of those observations into an identity-independent CPCS program suitable for analysis, controlled variation, previsualization, or generation.

The central object is the **Video Observation Graph (VOG)**. A VOG does not store one authoritative model description. It stores source-clock intervals, actor and object tracks, measured trajectories, detector events, semantic hypotheses, interpretive labels, contradictions, confidence, extractor versions, and the exact evidence that supports each resolved claim. A generated result can then be re-extracted into the same graph form and compared with the target score.

<!-- RAG_CHUNK id="cpcs.video.01" title="Reference-video distillation foundations" concepts="reference video, reverse compilation, evidence classes, temporal pyramid, rights" -->
## 30.1 Research Question

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

## 30.2 What “Extracting the Core” Means

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

## 30.3 Evidence Classes: Do Not Flatten Everything Into “The Model Said”

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

## 30.4 Why One-Pass Multimodal Summarization Is Insufficient

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

## 30.5 Temporal Pyramid

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

## 30.6 End-to-End Architecture

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

## 30.7 Stage 0 — Rights, Consent, and Source Registration

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

<!-- RAG_CHUNK id="cpcs.video.02" title="Media normalization and segmentation" concepts="ffprobe, timebase, shot detection, scene segmentation, beat detection" -->
## 30.8 Stage 1 — Media Normalization and Forensic Manifest

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

## 30.9 Stage 2 — Shot, Transition, Scene, and Beat Segmentation

### 30.9.1 Shot boundaries

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

### 30.9.2 Scenes

A scene is a storytelling unit, not merely a continuous shot. MovieScenes frames scene segmentation as a multimodal and hierarchical problem over clips, segments, and the larger movie [S86]. MovieNet demonstrates the value of aligned character, scene-boundary, action, place, description, and cinematic-style annotations for movie understanding [S85].

Scene grouping should consider:

- location and time continuity;
- cast continuity;
- dialogue topic;
- music cue;
- color and lighting continuity;
- establishing-shot/reverse-shot relationships;
- narrative objective.

### 30.9.3 Beats

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

<!-- RAG_CHUNK id="cpcs.video.03" title="Multimodal semantic and performance extraction" concepts="Gemini, Pegasus, Marengo, FACS, gaze, affect, actor tracking" -->
## 30.10 Stage 3 — Multimodal Semantic Analysis

### 30.10.1 Gemini

Gemini can process uploaded video or public YouTube URLs, answer questions about timecoded content, and produce structured output [S67, S68]. Use it for a hierarchy of increasingly narrow questions rather than one request for “everything.”

Recommended pass sequence:

1. **Sequence map:** scenes, characters, objectives, persuasive or dramatic arc.
2. **Shot map:** shot purpose, scale, angle, movement, transition, visible action.
3. **Beat map:** state changes and causal ordering within each shot.
4. **Domain pass:** face/performance, action, camera/edit, audio, VFX, marketing.
5. **Contradiction pass:** ask the model to identify ambiguous or unsupported claims.

For rapid action, create short clips and, where appropriate, slowed analysis proxies. Do not alter the source timebase in the canonical record; store the proxy-to-source transform.

Gemini structured outputs improve parseability, but official guidance still requires application-level value validation and notes that only a subset of JSON Schema is supported [S68]. A syntactically valid object can still contain a semantically wrong timestamp or action label.

### 30.10.2 Twelve Labs Pegasus

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

### 30.10.3 Twelve Labs Marengo and Gemini Embeddings

Marengo 3.0 is an embedding/search model rather than a per-frame metrology system. Its documented capabilities include multimodal processing, motion search, and improved understanding of cinematography terms such as zoom, pan, and tracking shot [S73]. Use it to retrieve comparable moments and cluster a library by motion or cinematic grammar.

Gemini Embedding 2 maps video and other modalities into a shared embedding space. Official limits state that video embeddings process at most 32 frames, with one-FPS sampling for clips up to 32 seconds and uniform 32-frame sampling for longer clips; audio inside video files is not processed [S70]. It is useful for retrieval and similarity, not for precise action timing.

## 30.11 Stage 4 — Actor, Face, Gaze, and Performance Extraction

### 30.11.1 Persistent actor tracks

Every detected person needs a persistent track ID. The system should preserve uncertainty through occlusion, shot changes, masks, and re-entry. Actor tracking is not the same as identity recognition. A privacy-preserving workflow can use ephemeral track IDs without resolving real-world identity.

Track records should contain:

- bounding box or mask;
- visibility and occlusion;
- face visibility;
- body keypoint confidence;
- identity-link confidence across cuts;
- speaking probability;
- interaction partners.

### 30.11.2 FACS and face-related tracks

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

### 30.11.3 Gaze and attention

Head pose is not gaze. Eye direction, head orientation, and likely target should be separate. VideoAttentionTarget formalizes dynamic gaze-target inference and explicitly includes out-of-frame targets [S91]. For cinematic analysis, likely targets include:

- camera lens;
- another actor’s face;
- a product or prop;
- an off-screen threat;
- captions or monitor content;
- an undefined scan region.

A UGC video’s lens-address schedule is a major directorial and marketing control. A fight scene’s gaze may anticipate an attack, confirm target acquisition, or conceal intent.

### 30.11.4 Affect

Estimate experienced affect only as a production interpretation. Visible display can be summarized as a VAD/VAC trajectory conditioned on face, voice, posture, and context, but it remains uncertain. Keep separate fields for:

- `displayed_affect_estimate`;
- `narrative_affect_interpretation`;
- `confidence`;
- `cultural_and_context_notes`.

<!-- RAG_CHUNK id="cpcs.video.04" title="Motion, camera, action, and Laban extraction" concepts="pose, 3D reconstruction, optical flow, camera disentanglement, action phases, contacts, Laban" -->
## 30.12 Stage 5 — Body Pose, 3D Reconstruction, and Camera Disentanglement

### 30.12.1 Whole-body pose

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

### 30.12.2 Monocular 3D human reconstruction

4DHumans reconstructs and tracks people in 3D from in-the-wild video and maintains identities through occlusion using 3D tracking [S80]. Such models can create retargetable skeletal or mesh tracks, but monocular scale, depth, camera motion, floor contact, and interaction geometry remain ambiguous.

### 30.12.3 Joint human-camera-scene reconstruction

SynCHMR addresses the problem that camera reconstruction and human reconstruction are often solved in incompatible frames. It combines human-aware metric SLAM and scene-aware human reconstruction to recover cameras, humans, and scene structure in a common world frame [S81]. This class of method is valuable because apparent screen movement is a mixture of:

Multiview first-/third-person resources such as Ego-Exo4D are valuable for developing and evaluating cross-view activity understanding, camera/body disentanglement, and skilled-action analysis. They do not remove the need to label which conclusions came from a single monocular production source and which were learned or validated from additional views [S90].


a. performer movement;

b. camera translation and rotation;

c. focal-length or crop change;

d. moving background or parallax;

e. stabilization and rolling-shutter artifacts.

### 30.12.4 Optical flow and background motion

RAFT estimates dense optical flow through recurrent all-pairs field transforms [S82]. Flow can support:

- motion saliency;
- camera-motion estimation from background pixels;
- action onset detection;
- speed-ramp analysis;
- VFX trail and smear detection;
- motion-blur assessment.

Flow alone does not identify cause. Mask performers and moving objects before fitting a global background transform. Compare homography, affine, and 3D camera explanations. Report model residuals.

### 30.12.5 Structure from motion

COLMAP is a general-purpose Structure-from-Motion and Multi-View Stereo pipeline that recovers camera poses and sparse or dense scene structure from overlapping images [S83]. It is most useful when the shot contains sufficient static texture, parallax, and non-destructive cuts. It may fail on heavy motion blur, shallow depth of field, large dynamic regions, stylized footage, or short shots.

## 30.13 Coordinate and Time Normalization

### 30.13.1 Time

Preserve original presentation timestamps. For a constant-rate derivative:

\[
t_f = \frac{f}{r}
\]

where \(f\) is the analysis-frame index and \(r\) is the proxy frame rate. Store a transform back to source PTS. For retargeting, normalize event time within a beat:

\[
\tau = \frac{t - t_{beat,start}}{t_{beat,end}-t_{beat,start}} \in [0,1]
\]

This permits the same action structure to be retimed from 1.2 seconds to 0.9 seconds while preserving relative order.

### 30.13.2 Space

Screen coordinates should be normalized by frame dimensions. Body coordinates should also be expressed relative to a root and body scale:

\[
\hat{p}_{j,t} = \frac{p_{j,t} - p_{root,t}}{h_t}
\]

where \(h_t\) is estimated body height or another stable scale. Interaction distances can be normalized by mean shoulder width or character height.

### 30.13.3 Camera-relative and world-relative representations

Store both when available:

- screen-space trajectory for what the audience sees;
- actor-relative camera pose for framing grammar;
- world-space performer trajectory for blocking and physics;
- uncertainty if world reconstruction is unavailable.

A director often cares that “the fist crosses the right third of frame and nearly reaches the opponent’s jaw at 62% of the beat,” even when absolute world coordinates cannot be recovered.

## 30.14 Stage 6 — Action Atoms, Motion Phases, Contacts, and Combat

### 30.14.1 Action segmentation

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

### 30.14.2 Phases

Every nontrivial action should have phases:

```text
preparation → initiation → acceleration → apex/contact → follow-through → recovery
```

The phase boundaries can be estimated from joint velocity, acceleration, support changes, target distance, and semantic hypotheses. Store local phases for feet, pelvis, torso, hand, head, and reaction partner when they are not synchronized.

### 30.14.3 Contact and near-contact

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

### 30.14.4 Causal action graph

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

## 30.15 Stage 7 — Deriving Laban Movement Qualities

Laban Effort is not directly observable as one number, and computational proxies are not definitions. The reverse compiler should produce a **candidate Laban reading** with evidence.

### 30.15.1 Weight

Possible proxies:

- acceleration and deceleration magnitude;
- vertical center-of-mass displacement;
- contact loading duration;
- visible follow-through;
- muscle-tension appearance where available;
- sound and camera emphasis, stored separately from body mechanics.

A strong-Weight interpretation should not be inferred solely from loud audio.

### 30.15.2 Time

Possible proxies:

- time from preparation to apex;
- acceleration concentration;
- abruptness of direction change;
- duration of holds and releases;
- action-onset uncertainty.

Sudden Time is a qualitative intention and may coexist with smooth trajectories.

### 30.15.3 Space

A directness ratio can support a candidate reading:

\[
D = \frac{\|p(t_1)-p(t_0)\|}{\sum_t \|p(t+\Delta t)-p(t)\|}
\]

Values closer to one indicate a straighter path, but direct Space also concerns attention and spatial intent, not only geometry.

### 30.15.4 Flow

Possible proxies:

- jerk and its distribution;
- residual motion after the action goal;
- frequency of controlled holds;
- reversibility and stopping behavior;
- joint coupling and release.

Bound Flow should not be reduced to “low speed.”

### 30.15.5 Shape and Body organization

Estimate spreading/enclosing, rising/sinking, advancing/retreating, and body-part initiation from normalized skeletal geometry. Store the measured geometry and the interpreted Laban label separately.

<!-- RAG_CHUNK id="cpcs.video.05" title="Cinematography, audio, VFX, and marketing extraction" concepts="camera, editing, audio, VFX, UGC, marketing graph" -->
## 30.16 Stage 8 — Camera, Lens, Framing, and Editorial Grammar

### 30.16.1 Shot scale and framing

Measure subject occupancy and headroom rather than relying only on labels. Store:

- person-box height as fraction of frame;
- face size;
- headroom and lead room;
- center-of-interest;
- number of visible bodies;
- occlusion and silhouette separation;
- approximate shot-scale label with confidence.

### 30.16.2 Angle

Camera height and pitch relative to the performer determine high, low, eye-level, overhead, or ground-level readings. When 3D recovery is unavailable, label the visual impression and mark the geometric basis as uncertain.

### 30.16.3 Camera movement

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

### 30.16.4 Editing

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

## 30.17 Stage 9 — Audio, Dialogue, Rhythm, and Impact

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

## 30.18 Stage 10 — VFX and Stylization Extraction

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

## 30.19 Stage 11 — UGC and Marketing Extraction

Marketing controls describe why a creative is expected to communicate, not a guaranteed sales outcome. The extraction should produce testable hypotheses.

### 30.19.1 UGC communication graph

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

### 30.19.2 Measurable UGC tracks

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

### 30.19.3 Director and marketing separation

A low-angle close-up is a director control. “Establish authority before introducing the product” is a marketing hypothesis. The compiler can connect them, but they should not share one field.

<!-- RAG_CHUNK id="cpcs.video.06" title="Evidence fusion and Video Observation Graph" concepts="confidence, contradictions, provenance, canonical graph, CPCS projection" -->
## 30.20 Confidence Fusion and Contradiction Management

### 30.20.1 Do not average unlike evidence

A language model’s `0.82` confidence is not calibrated against a pose detector’s keypoint probability. Preserve confidence type and calibration scope.

### 30.20.2 Evidence bundle

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

### 30.20.3 Suggested precedence

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

### 30.20.4 Contradiction is a first-class output

Examples:

- semantic model labels a zoom; background parallax supports dolly;
- AU detector reports high AU12 but face is blurred;
- pose indicates possible contact but depth estimate indicates a miss;
- transcript says product name while OCR reads a different brand;
- model labels a cut but transition detector identifies a dissolve.

Do not silently resolve these. Record them for review or downstream sensitivity analysis.

## 30.21 Canonical Video Observation Graph

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

## 30.22 Reverse Compilation Into CPCS

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

### 30.22.1 What can be compiled directly

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

### 30.22.2 Controlled degradation

If a model cannot accept an AU curve, the compiler may:

1. bake facial motion into an identity-safe rendered reference;
2. convert it into facial landmarks;
3. compress it into timed language;
4. retain it only as an evaluator;
5. report unsupported control rather than pretending it was enforced.

<!-- RAG_CHUNK id="cpcs.video.07" title="Fight and UGC reverse-compilation workflows" concepts="fight extraction, stunt abstraction, UGC extraction, marketing cadence" -->
## 30.23 Detailed Workflow: Fight or Stunt Scene

### 30.23.1 Pass A — Editorial anatomy

Extract every shot, transition, speed change, freeze, reaction insert, and impact frame. Create an OTIO timeline. Measure average shot length and the distribution around action apexes.

### 30.23.2 Pass B — Actor and geography

Track each performer, infer screen direction, estimate world or actor-relative positions, identify obstacles and props, and record visibility. Maintain separate tracks through cuts.

### 30.23.3 Pass C — Action atomization

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

### 30.23.4 Pass D — Kinetic chain

Estimate temporal ordering:

```text
support foot → pelvis → torso → shoulder → elbow → hand/prop
```

Do not infer biomechanical force from image speed alone. Camera movement, shutter, and retiming can change apparent speed.

### 30.23.5 Pass E — Impact construction

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

### 30.23.6 Pass F — Safety and abstraction

Export stylized, fictional choreography for previsualization. Do not present it as real-world fighting instruction. Preserve staged near-contact classifications and require stunt-professional review for physical production.

### 30.23.7 Example fight extraction summary

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

## 30.24 Detailed Workflow: UGC Advertisement or Creator Video

### 30.24.1 Pass A — Communication structure

Ask a multimodal model to identify the proposition and segment the creative into hook, problem, solution, demonstration, proof, objection, offer, and CTA. Use a finite schema and require timestamps.

### 30.24.2 Pass B — Lens relationship

Measure when the creator looks at the lens, glances at the product, looks at captions, or turns to b-roll. Store gaze-to-lens duty cycle by beat.

### 30.24.3 Pass C — Speech and caption pace

Transcribe words with timestamps. Estimate:

- words per minute;
- pause duration distribution;
- time to first claim;
- sentence length;
- emphasis points;
- caption update rate;
- alignment between spoken phrase and caption card;
- music-to-speech balance.

### 30.24.4 Pass D — Visual proof

Track product and proof objects. Measure visibility, size, angle, obstruction, and duration. Distinguish a brand appearance from a persuasive proof event.

### 30.24.5 Pass E — Camera authenticity grammar

Extract:

- phone-like vertical framing;
- arm-length perspective;
- handheld spectrum;
- autofocus or exposure corrections;
- jump-cut pattern;
- b-roll insert density;
- imperfect but bounded composition.

These features can be intentionally reproduced without duplicating the original person.

### 30.24.6 Pass F — Variant plan

Compile the extracted core into controlled variants:

```text
same hook timing, new wording
same proof order, different product
same gaze rhythm, different creator
same shot-duration distribution, different location
same CTA hold, different offer
```

### 30.24.7 Example UGC extraction summary

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

<!-- RAG_CHUNK id="cpcs.video.08" title="Provider orchestration and round-trip verification" concepts="provider roles, model adapters, round-trip verification, metrics" -->
## 30.25 Provider-Orchestrated Extraction Pattern

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

## 30.26 Round-Trip Verification

The final test is not whether the new video “feels similar” in an unconstrained way. Re-extract the generated result and compare it with the intended CPCS score.

### 30.26.1 Temporal event error

\[
E_{event}=|t_{generated}-t_{target}|
\]

Use for cuts, gaze changes, product reveal, contact, reaction, and CTA.

### 30.26.2 Pose or trajectory agreement

Use normalized joint or root trajectories with dynamic time warping when elastic timing is allowed.

### 30.26.3 Action graph agreement

Compare event types, order, actor roles, targets, and causal edges.

### 30.26.4 Camera agreement

Compare shot scale, framing occupancy, screen direction, base camera move, and impact impulse separately.

### 30.26.5 Marketing agreement

Check constraints such as:

- hook completes by target time;
- product visible within threshold;
- proof precedes CTA;
- caption safe areas preserved;
- CTA hold meets minimum duration.

### 30.26.6 Perceptual review

Human reviewers should separately score:

- action identity;
- performance intent;
- motion naturalness;
- physical readability;
- cinematic clarity;
- originality and non-duplication;
- marketing comprehension;
- rights and policy compliance.

<!-- RAG_CHUNK id="cpcs.video.09" title="Failure modes and implementation tiers" concepts="failure modes, minimum viable implementation, verification checklist" -->
## 30.27 Failure Modes

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

## 30.28 Minimum Viable Implementation

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

## 30.29 Deterministic Verification Checklist

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

---

<!-- RAG_CHUNK id="cpcs.31" title="Conclusion" concepts="conclusion, directorial control, integrated framework" -->
<a id="cpcs-conclusion"></a>
# 31. Conclusion

The search for a single “FACS for the whole body” is understandable but incomplete. Facial Action Units, dimensional affect, body-action coding, Laban movement description, skeletal motion, phase, contact, dynamics, interaction, and camera pose each solve different parts of the directorial problem. Their integration becomes useful only when their boundaries remain explicit.

FACS provides localized, editable facial actions and temporal events. VAD or VAC provides a continuous affective trajectory and a way to distinguish internal state from displayed control. Laban provides an interpretable vocabulary for movement quality, body organization, shape, and spatial attitude. Kinematics, global and local phase, contact, and physics turn those descriptions into executable motion. Camera and audio transform that motion into a cinematic event. RAG grounds directorial language in evidence-labeled templates, project assets, and model capabilities. Verification closes the loop by measuring whether the generated shot followed the plan.

The resulting paradigm is not “prompt engineering” in the narrow sense. It is **performance compilation**. The director supplies story, objective, subtext, reference, and selected constraints. The system compiles those intentions into synchronized tracks, generates a shot, and returns measurable evidence of compliance. Creative ambiguity remains available where the score is soft or stochastic; precision is available where the shot depends on exact timing, contact, expression, or camera movement.

The structured-language layer makes that compilation operational. YAML provides a readable authoring surface for styles and overrides; canonical JSON provides a fully resolved, schema-valid intermediate representation; XML can preserve ordered director, screenplay, dialogue, and namespaced department annotations; and JSONL records retrieval, compilation, metrics, and experiments. Their syntax has no special authority by itself. Authority comes from typed field semantics, explicit scope and merge rules, target capability profiles, and a compiler that maps each control to prompts, parameters, media conditions, simulation or render assets, postproduction events, and acceptance tests. VFX can amplify perception without being mistaken for physics, and marketing requirements can constrain communication without being mistaken for guaranteed commercial causation.

A controllable AI video system should therefore aspire to behave less like a slot machine for attractive clips and more like a responsive production department: able to interpret direction, expose its plan, execute coordinated performance, preserve continuity, and revise a specific beat without losing the rest of the shot.

The reverse compiler completes that loop. It allows a production team to study an authorized reference, extract its causal and temporal grammar, replace identity and surface content, author deliberate variations, and test whether a newly generated sequence preserves the desired performance, choreography, camera, edit, and communication structure. Multimodal models contribute interpretation, but the accountable unit of knowledge is the timecoded evidence graph rather than an unverified paragraph.


---

<!-- RAG_CHUNK id="cpcs.a1" title="Canonical glossary and retrieval aliases" concepts="glossary, ontology, aliases, controlled vocabulary" -->
<a id="cpcs-glossary"></a>
# Appendix A. Canonical Glossary and Retrieval Aliases

This glossary defines the preferred meaning of recurrent terms in CPCS. The **canonical term** should be stored in structured records; the aliases support retrieval from screenplay, animation, acting, movement-analysis, and machine-learning vocabularies. Definitions are operational and do not override the cited source systems.

| Canonical term | Definition in CPCS | Common retrieval aliases | Exclusions and cautions |
|---|---|---|---|
| **Action Unit (AU)** | A FACS descriptor for an observable facial action associated with one or more underlying muscular actions. CPCS stores AU intensity as a temporal curve. | facial unit; muscle action; FACS code; expression component | An AU is not an emotion label and does not prove internal state. |
| **AU event phase** | The temporal organization of a facial action into neutral or baseline, onset, apex or plateau, offset, and return. | onset–apex–offset; expression timing; facial event | Boundaries depend on annotation protocol and frame rate. |
| **AU intensity** | Ordinal or normalized magnitude of an AU at a time point. | activation; strength; magnitude | Cross-person equality cannot be assumed without calibration. |
| **Asymmetry** | A left–right difference in the timing or magnitude of a facial or bodily action. | unilateral; side bias; lopsided | It may be intentional, anatomical, or caused by view and occlusion. |
| **Valence** | Pleasantness–unpleasantness coordinate of intended or perceived affect. | positive–negative affect; hedonic tone | It does not uniquely determine a visible expression. |
| **Arousal** | Activation–deactivation coordinate of intended or perceived affect. | energy; activation; excitation; calmness | Physiological and perceived arousal are not identical. |
| **Dominance / control** | Perceived power, agency, or situational control in a VAD/PAD space. CPCS permits the production alias VAC. | control; agency; power; submission–dominance | Not model guidance strength and not an objective personality score. |
| **Experienced affect** | The state intended for the character within the fiction. | internal emotion; felt state; subtext state | It is a directorial construct for generated performance, not mind reading. |
| **Displayed affect** | The state the character intentionally or involuntarily reveals. | performed emotion; surface affect; mask | May differ from experienced affect, especially in concealment or deception. |
| **Affect leak** | A short divergence in which a suppressed experienced state becomes visible in face, gaze, body, voice, or timing. | crack in composure; micro-leak; reveal | “Microexpression” should be used only when its specific duration and definition are intended. |
| **Body Action and Posture code** | A descriptive label for observable articulation, form, or function in body behavior, derived from BAP-style analysis. | body action code; gesture code; posture code | It is not a universal whole-body analogue of FACS and not MPEG-4 BAP. |
| **Laban Body** | Description of body organization, initiation, connectivity, sequencing, and part relationships. | body connectivity; initiation; kinetic chain | It is qualitative unless explicitly mapped to measurable variables. |
| **Laban Effort** | Qualitative dynamic attitude described through Weight, Time, Space, and Flow factors. | movement quality; dynamics; effort qualities | It is not literal force, duration, Euclidean path, or joint looseness. |
| **Laban Shape** | How the body changes form in relation to self, space, objects, and others. | opening; closing; rising; sinking; advancing; retreating | Shape descriptors require body- and context-sensitive operationalization. |
| **Laban Space** | Spatial intent and organization, including pathways, reach, levels, directions, and kinesphere. | spatial pathway; reach space; directionality | Not equivalent to camera space or image coordinates. |
| **Weight quality** | Laban continuum from light to strong. | delicate–forceful; yielding–powerful | A qualitative impression, not measured Newtons. |
| **Time quality** | Laban continuum from sustained to sudden. | lingering–urgent; gradual–sharp | Not simply clip duration or playback speed. |
| **Space quality** | Laban continuum from indirect to direct. | meandering–focused; flexible–channelled path | Not only path curvature; attention and intention also matter. |
| **Flow quality** | Laban continuum from bound to free. | controlled–released; restrained–continuous | Not merely joint smoothness or range of motion. |
| **Action identity** | The categorical or semantic action that should remain recognizable while style varies. | content; action class; movement verb | Must be evaluated separately from expressive quality. |
| **Movement atom** | A reusable, temporally delimited action component with participants, body parts, constraints, and transition interfaces. | motion primitive; action unit; gesture primitive; clip segment | “Action unit” is avoided for the body when confusion with FACS is possible. |
| **Action beat** | A narratively meaningful interval in which objective, tactic, state, or relationship changes. | performance beat; acting beat; story beat | Beat boundaries need not coincide with cuts or motion-cycle boundaries. |
| **Key pose** | A pose selected because it carries structural, semantic, or contact significance. | keyframe; extreme; storytelling pose | A pose alone does not define transition dynamics. |
| **Root trajectory** | Global translation and orientation of a performer’s reference root, usually pelvis or character frame. | path; locomotion trajectory; actor blocking | Does not determine limb motion or contact by itself. |
| **Global phase** | A normalized variable describing position within a repeated or structured motion cycle. | gait phase; locomotion cycle; phase clock | Complex actions often require multiple local phases. |
| **Local motion phase** | A time-varying phase assigned to a body part, contact channel, or motion component. | part phase; limb phase; multi-contact phase | Need not be periodic; may be represented by learned phase vectors. |
| **Contact state** | Whether a named body region is in contact with the ground, prop, scene, or another performer. | support; touch; plant; grip; impact | Binary contact is often insufficient; location, normal, confidence, and force may be needed. |
| **Contact event** | A transition such as touch-down, grasp, release, impact, or separation. | strike frame; footfall; catch; handoff | An event has temporal tolerance and can be hard or soft. |
| **Support polygon** | Ground-plane region formed by active support contacts, used as a proxy for balance. | base of support | Dynamic movement can be plausible with the projected center of mass temporarily outside it. |
| **Center of mass (CoM)** | Mass-weighted position of the character, estimated from a body model or segment parameters. | balance point; body mass center | Estimation depends on body model and anthropometric assumptions. |
| **Jerk** | Time derivative of acceleration, used as one component of smoothness analysis. | motion roughness; snap-like change | Low jerk alone does not imply human-likeness or dramatic appropriateness. |
| **Momentum propagation** | Ordered transfer of movement through support, pelvis, trunk, and extremities. | kinetic chain; sequential coordination; lead–follow | Exact sequencing is action-, style-, and performer-dependent. |
| **Interaction constraint** | A spatial, temporal, contact, gaze, or causal relation between actors and objects. | relational control; joint pair constraint; blocking relation | Must specify reference frames and tolerances. |
| **Staged contact** | Choreographed near-contact whose camera projection creates the appearance of impact without unsafe physical collision. | camera cheat; pulled punch; cheated hit | Must be explicitly distinguished from true simulated contact. |
| **Camera pose** | Six-degree-of-freedom camera position and orientation at a time point. | extrinsics; camera trajectory; 6DoF camera | Lens and focus are separate controls. |
| **Screen-space trajectory** | Projected path of a person, joint, prop, or feature in the image plane. | 2D path; image trajectory; pixel track | Can be satisfied by different 3D motions and cameras. |
| **Directorial constraint** | A hard or soft condition selected because it affects story meaning, safety, continuity, or shot design. | note; instruction; requirement; lock | It should carry priority, tolerance, and provenance. |
| **Control compiler** | System that translates direction and retrieved knowledge into a validated CPCS score and model-specific conditions. | planner; prompt compiler; shot compiler | It should not silently invent hard facts or unsupported controls. |
| **Control adapter** | Model-specific module that maps a CPCS track to tokens, maps, latents, keyframes, or guidance losses. | conditioner; ControlNet-style adapter; encoder | Adapter support must be declared in a capability profile. |
| **Compliance** | Degree to which generated evidence matches explicit score requirements. | controllability; adherence; instruction following | Separate from image quality, aesthetic appeal, and semantic plausibility. |
| **Capability profile** | Machine-readable declaration of controls a generator accepts, their formats, limits, frame rates, and known failure modes. | model card for control; adapter manifest | It must be versioned because model behavior changes. |
| **Calibration profile** | Performer-, rig-, lens-, or model-specific mapping between normalized controls and observed output. | retargeting profile; neutral baseline; control curve | It must not be generalized beyond its measured scope without validation. |
| **Provenance** | Trace of where a retrieved rule, template, sample, or control value originated. | citation; lineage; source record | Required for evidence review, licensing, and reproducibility. |

## A.1 Preferred Identifier Conventions

CPCS uses stable, typed identifiers so that prose variants do not fragment retrieval:

```text
performer:PERF_A
beat:BEAT_014
track:FACE_AU_04
contact:CONTACT_FIST_TARGET_01
camera:CAM_A
source:S23
concept:laban.effort.weight
movement_atom:locomotion.walk.forward
capability_profile:MODEL_X@2.1
calibration_profile:PERF_A_NEUTRAL@1.0
```

Identifiers should be opaque enough to remain stable when labels change. Human-readable labels belong in separate fields. Version suffixes are required for model, schema, calibration, and template records.

---

<!-- RAG_CHUNK id="cpcs.a2" title="Directorial language crosswalk" concepts="director notes, control mapping, acting language, cinematography language" -->
<a id="cpcs-directorial-crosswalk"></a>
# Appendix B. Directorial Language–to–Control Crosswalk

The following crosswalk is not a dictionary that deterministically converts phrases into movement. It is a retrieval and planning guide. Each phrase proposes candidate control tracks and identifies information that should remain unresolved until the director, choreographer, animator, or compiler selects an interpretation.

## B.1 Face, Gaze, and Affect

| Director’s phrase | Narrative interpretation | Candidate controls | Verification focus |
|---|---|---|---|
| “Hold it together.” | Experienced affect exceeds displayed affect; active suppression. | Separate experienced/displayed VAD; lower AU amplitudes; bound Flow; reduced gesture amplitude; controlled breath; stable gaze with occasional leak. | Difference between latent and displayed tracks; absence of broad expression; presence of selected involuntary cue. |
| “Let the fear leak through for one beat.” | Brief failure of suppression. | Short AU event; gaze break; blink or eyelid change; inhale; shoulder or sternum retreat; affect display pulse aligned to beat. | Event onset, apex, offset, and return; subtlety; no persistent categorical fear face unless requested. |
| “The smile does not reach the eyes.” | Social mouth display with reduced eye-region involvement. | Mouth-related AU combination selected from reference; attenuated or absent eye-region actions; controlled cheek change; held gaze. | Local AU contrast and identity preservation; avoid treating one pattern as a universal deception marker. |
| “Recognize him before you react.” | Perceptual registration precedes overt affect. | Gaze acquisition; pupil/eyelid/head orienting; latency before affect and body response; beat marker for recognition. | Correct ordering and intentional reaction delay. |
| “Think, then answer.” | Cognitive beat visible through timing rather than a stock face. | Speech delay; gaze shift or fixation; micro head movement; breath; low-amplitude facial activity; response onset. | Pause duration, eyeline, and speech synchronization; avoid exaggerated “thinking” iconography. |
| “More dangerous, not angrier.” | Increase dominance/control and threat while limiting high-valence-negative facial display. | VAD dominance increase; lower movement amplitude; direct Space; bound Flow; stable gaze; slow head turn; reduced blinking; selective facial tension. | Threat perception without broad anger stereotype; action identity unchanged. |
| “She is pleased but will not show it.” | Positive experienced valence with neutral or guarded display. | Experienced valence positive; displayed valence near neutral; minute mouth-corner or cheek event; gaze warmth; softened Weight; restrained Flow. | Suppression remains legible only at intended shot scale. |

## B.2 Posture, Gesture, and Movement Quality

| Director’s phrase | Candidate Laban/body interpretation | Mechanical realization | Verification focus |
|---|---|---|---|
| “Make the walk heavier.” | Stronger Weight, possibly more bound Flow and lower Shape. | Longer loading response; greater vertical CoM impulse or visible settling; firmer contacts; adjusted arm swing; preserved speed unless separately changed. | Perceived weight changes while action, path, and duration remain controlled. |
| “Move as if the room is listening.” | Bound Flow; indirect attention with constrained amplitude; shape containment. | Reduced step noise/amplitude; deliberate foot placement; scanning gaze; slower releases; quiet contacts. | Restraint and environmental attention without simply slowing every joint. |
| “Cut through the crowd.” | Direct Space, sudden Time, stronger Weight. | Straighter root path; narrower decision latency; purposeful shoulder orientation; collision-avoidance constraints; decisive acceleration. | Path efficiency, intent, and no body interpenetration. |
| “Float into frame.” | Light Weight, sustained Time, free or softly bound Flow. | Smooth acceleration; low vertical impact; gradual limb follow-through; controlled foot contacts; camera may support illusion. | No literal floating unless intended; contacts remain plausible. |
| “Collapse inward.” | Enclosing Shape, sinking, retreating; decreased dominance. | Spine flexion, shoulder protraction, narrowed base or guarded arms, lowered gaze; controlled balance. | Whole-body shape change, not only head lowering. |
| “Open to him.” | Spreading/opening Shape and relational orientation. | Sternum and pelvis turn; arms release; distance may close; gaze meets partner; affect display can warm. | Orientation and relationship change synchronized to beat. |
| “The hand leads; the body follows.” | Distal initiation and sequential connectivity. | Hand local phase advances forearm, shoulder, torso, and root; reach target constraints. | Lead–lag timing and absence of detached limb motion. |
| “The hips commit before the punch.” | Proximal initiation and kinetic chain. | Foot plant; pelvis phase leads torso, shoulder, elbow, fist; contact event after acceleration chain. | Phase order, target accuracy, support, and recovery. |
| “Stop on the thought.” | Sudden Time at a semantic beat with controlled Flow. | Deceleration planned before beat; contact/support maintained; residual secondary motion may settle. | Stop timing and physical plausibility; avoid instantaneous velocity discontinuity. |
| “Keep the energy moving after the line.” | Continue body and breath phrasing beyond speech endpoint. | Follow-through in gaze, hands, torso, or root; delayed settle; audio and breath tail. | Performance does not freeze when dialogue ends. |

## B.3 Locomotion and Blocking

| Director’s phrase | Score interpretation | Required tracks | Ambiguities to resolve |
|---|---|---|---|
| “Cross quickly.” | Complete a root path under a duration constraint. | Root trajectory; speed profile; gait type; contact schedule; obstacle map. | Run, hurried walk, or stylized glide; start/end velocity; camera-relative or world-relative direction. |
| “Approach but do not invade.” | Reduce interpersonal distance to a social threshold. | Relative distance curve; facing; gaze; endpoint tolerance; collision boundary. | Cultural/contextual distance; partner response. |
| “Circle him while keeping eye contact.” | Coupled orbit and gaze constraint. | Root orbital path; torso/head/gaze orientation; foot contacts; camera geography. | Which actor is reference; orbit direction; whether feet cross. |
| “Back away without looking weak.” | Retreating path with maintained dominance. | Negative root velocity; high dominance; direct Space; stable gaze; controlled base; guard posture. | Speed and reason for retreat; environmental hazards. |
| “She arrives before she is ready.” | Physical endpoint precedes affective preparation. | Root arrival; affect/display lag; breath; gaze avoidance or delayed orientation. | Exact lag and whether the mismatch is comic, anxious, or dramatic. |

## B.4 Fighting, Stunts, and Interaction

| Director’s phrase | Score interpretation | Required controls | Safety/continuity notes |
|---|---|---|---|
| “A fast right cross that nearly misses.” | High-speed strike with near-contact and readable line. | Target joint/volume; local phases; support foot; fist trajectory; minimum distance; follow-through; opponent response; camera projection. | Prefer staged near-contact for live-action references; maintain screen direction. |
| “He absorbs the hit, then decides to fall.” | Impact response followed by intentional delayed surrender of balance. | Contact/near-contact event; impulse proxy; torso recoil; decision beat; support release; fall trajectory. | Separate involuntary recoil from chosen fall; protect head/neck in reference capture. |
| “Make it brutal but not faster.” | Increase perceived force without shortening duration. | Strong Weight; direct Space; larger momentum exchange; reaction amplitude; sound and camera impulse; duration locked. | Do not use actual unsafe force; distinguish audiovisual emphasis from physical contact. |
| “She redirects rather than blocks.” | Change attack trajectory using contact and body positioning. | Hand/forearm contact; vector redirection; root/pelvis turn; attacker balance response; release. | Contact geometry and causal order must be visible. |
| “They fight like they know each other.” | Anticipatory timing and relational familiarity. | Reduced reaction latency; mirrored habits; shared rhythm; feint history; gaze prediction; personalized movement templates. | Avoid generic symmetry; encode character-specific asymmetries. |
| “One clean beat, no flurry.” | Single readable action–reaction unit. | One attack event; one defense/reaction; hold or recovery; camera coverage. | Suppress extra generated strikes and unnecessary limb motion. |

## B.5 Camera and Editing

| Director’s phrase | Camera-score interpretation | Performance coupling | Verification focus |
|---|---|---|---|
| “Stay with her.” | Maintain subject priority through a track, pan, dolly, or reframing. | Camera follows root/face while preserving eyeline and intended scale. | Subject framing, occlusion, and camera lag. |
| “Do not reveal him until she knows.” | Visibility constraint tied to recognition beat. | Occlusion or framing hides second actor until event; gaze/recognition precedes reveal. | No premature body, reflection, or shadow reveal unless intended. |
| “Let the hit land in the wide.” | Contact/readability event occurs while both bodies and geography are visible. | Camera scale and pose locked around contact interval; no cut before reaction information. | Contact projection, silhouettes, and spatial continuity. |
| “Push in when the mask breaks.” | Camera movement keyed to affect leak. | Dolly/zoom begins at facial/display divergence or just before apex. | Temporal offset, lens choice, and absence of accidental perspective change. |
| “The camera hesitates with him.” | Camera motion contains a small delay or aborted move that echoes the character beat. | Camera phase linked but not identical to performer phase. | Intention is legible without unstable or arbitrary shake. |
| “Feel handheld, not chaotic.” | Bounded stochastic camera motion around a designed path. | Noise spectrum and amplitude constrained by lens, operator mass, and shot scale. | Horizon, readability, motion sickness, and repeatability. |

## B.6 Compiler Rule for Ambiguous Direction

A compiler should never convert an ambiguous phrase directly into hard numeric values without an evidence trail. It should produce:

```yaml
director_phrase: "make the walk heavier"
interpretation_candidates:
  - id: candidate_a
    laban:
      weight: +0.55
      flow: -0.20
    mechanics:
      loading_response_scale: 1.20
      vertical_settle_scale: 1.10
      contact_impulse_visual_scale: 1.15
    locked:
      root_path: true
      duration: true
  - id: candidate_b
    laban:
      weight: +0.45
      time: -0.15
    mechanics:
      stride_frequency_scale: 0.94
      stance_ratio_scale: 1.08
    locked:
      endpoint_time: true
selection_status: director_review_required
provenance:
  - template: TEMPLATE_WALK_WEIGHT_03@2.0
  - source_ids: [S19, S20, S21, S33]
```

The director can choose, blend, or reject candidates. Once selected, the numeric values become project-specific instructions, not universal mappings from Laban terminology.

---

<!-- RAG_CHUNK id="cpcs.a3" title="Canonical CPCS authoring template" concepts="CPCS schema, YAML, shot score, machine readable control" -->
<a id="cpcs-authoring-template"></a>
# Appendix C. Canonical CPCS Authoring Template

The following YAML is a comprehensive authoring template. A production may omit unsupported tracks, but it should not silently reinterpret fields. Units, coordinate frames, timebases, confidence, and priorities are explicit. The template is a serialization proposal, not an established standard.

```yaml
cpcs_document:
  schema: "cpcs/1.0"
  document_id: "CPCS_PROJECT_SCENE_SHOT"
  version: "1.0.0"
  created_at: "2026-07-18T00:00:00Z"
  status: "draft|approved|rendered|verified"

  provenance:
    script_id: "SCRIPT_01"
    storyboard_ids: ["BOARD_014A", "BOARD_014B"]
    reference_asset_ids: ["REF_PERFORMANCE_07"]
    source_ids: ["S01", "S02", "S19", "S22"]
    compiler:
      name: "CPCS_COMPILER"
      version: "0.1.0"
    human_approvals:
      director: null
      movement_director: null
      stunt_coordinator: null
      intimacy_coordinator: null
      vfx_supervisor: null

  timebase:
    unit: "seconds"
    start: 0.0
    end: 4.8
    fps: 24
    frame_index_origin: 0
    sample_rate_hz:
      performance: 120
      face: 60
      camera: 60
      audio: 48000
    synchronization:
      master_clock: "picture"
      audio_offset_seconds: 0.0
      mocap_offset_seconds: 0.0

  coordinate_systems:
    world:
      handedness: "right"
      up_axis: "+Y"
      forward_axis: "+Z"
      linear_unit: "meter"
    screen:
      origin: "top_left"
      x_range: [0.0, 1.0]
      y_range: [0.0, 1.0]
    performer_local:
      root_joint: "pelvis"
    camera:
      convention: "world_from_camera"
      rotation_representation: "quaternion_xyzw"

  narrative:
    scene_objective: ""
    shot_purpose: ""
    audience_inference: ""
    dramatic_question: ""
    continuity_state_before: {}
    continuity_state_after: {}
    forbidden_inferences: []

  cast:
    - performer_id: "PERF_A"
      character_id: "CHAR_A"
      identity_asset: "IDENTITY_A@1.0"
      body_model: "SMPL-X-compatible"
      rig_profile: "RIG_A@2.1"
      calibration_profile: "CAL_A@1.4"
      handedness: "right"
      physical_constraints:
        injury_state: null
        range_of_motion_limits: {}
      consent_and_rights:
        identity_use_scope: "project_only"
        reference_capture_scope: "shot_family"

  scene:
    environment_asset: "SET_01@3.0"
    floor_plane:
      point: [0.0, 0.0, 0.0]
      normal: [0.0, 1.0, 0.0]
    collision_geometry: "SET_01_COLLISION@3.0"
    props:
      - prop_id: "PROP_01"
        geometry_asset: "PROP_01@1.0"
        mass_kg: 0.4
        initial_pose: {}
    spatial_zones: []

  directorial_notes:
    - note_id: "NOTE_01"
      text: ""
      author_role: "director"
      applies_to: ["BEAT_01"]
      priority: 0.9
      hardness: "soft"
      ambiguity_policy: "preserve_alternatives"

  beats:
    - beat_id: "BEAT_01"
      label: "recognition"
      start: 0.00
      end: 0.60
      objective: ""
      tactic: ""
      obstacle: ""
      turn: ""
      performer_ids: ["PERF_A"]
      predecessor_ids: []
      successor_ids: ["BEAT_02"]
      editable_handles:
        - "recognition_latency"
        - "gaze_acquisition_time"

    - beat_id: "BEAT_02"
      label: "concealment_break"
      start: 0.60
      end: 1.10
      objective: ""
      performer_ids: ["PERF_A"]
      predecessor_ids: ["BEAT_01"]
      successor_ids: []

  performance_tracks:
    affect:
      - performer_id: "PERF_A"
        representation: "VAD"
        value_range: [-1.0, 1.0]
        experienced:
          interpolation: "cubic_monotone"
          keys:
            - {t: 0.00, valence: -0.25, arousal: 0.35, dominance: 0.10}
            - {t: 1.00, valence: -0.55, arousal: 0.72, dominance: -0.20}
        displayed:
          interpolation: "cubic_monotone"
          keys:
            - {t: 0.00, valence: 0.00, arousal: 0.05, dominance: 0.18}
            - {t: 0.78, valence: -0.08, arousal: 0.18, dominance: 0.10}
            - {t: 1.00, valence: -0.28, arousal: 0.38, dominance: -0.02}
        uncertainty:
          source: "director_authored"
          confidence: 0.80

    face:
      - performer_id: "PERF_A"
        neutral_baseline: "CAL_A_FACE_NEUTRAL@1.4"
        action_units:
          - au: "AU04"
            side: "bilateral"
            scale: "normalized_0_1"
            interpolation: "cubic_monotone"
            keys:
              - {t: 0.00, value: 0.02}
              - {t: 0.72, value: 0.03}
              - {t: 0.90, value: 0.28}
              - {t: 1.15, value: 0.05}
            phase_labels:
              onset: [0.72, 0.86]
              apex: [0.86, 0.98]
              offset: [0.98, 1.15]
            priority: 0.75
            tolerance:
              peak_time_seconds: 0.08
              peak_value: 0.10
          - au: "AU20"
            side: "bilateral"
            scale: "normalized_0_1"
            keys: []
        head_pose:
          representation: "quaternion_xyzw"
          reference_frame: "performer_root"
          keys: []
        gaze:
          mode: "target_plus_offset"
          targets:
            - {t0: 0.00, t1: 0.48, target: "PROP_01"}
            - {t0: 0.48, t1: 1.40, target: "PERF_B.eye_midpoint"}
          saccades: []
          blink_events: []
        jaw_and_speech:
          audio_asset: null
          viseme_track: null
          coarticulation_profile: "LANG_EN_GENERIC@1.0"
        breath:
          events: []

    laban:
      - performer_id: "PERF_A"
        scope: "whole_body"
        interpolation: "piecewise_cubic"
        effort:
          weight:
            convention: {-1.0: "light", 1.0: "strong"}
            keys: []
          time:
            convention: {-1.0: "sustained", 1.0: "sudden"}
            keys: []
          space:
            convention: {-1.0: "indirect", 1.0: "direct"}
            keys: []
          flow:
            convention: {-1.0: "bound", 1.0: "free"}
            keys: []
        shape:
          spreading_enclosing: []
          rising_sinking: []
          advancing_retreating: []
        body:
          initiation: ""
          connectivity: ""
          sequencing: []
        space:
          pathway: ""
          level: "middle"
          kinesphere: "near|mid|far"
        operationalization_profile: "LMA_PROJECT_01@1.0"
        evidence:
          source_ids: ["S19", "S20", "S21"]
          mapping_status: "project_calibrated"

    body_action_codes:
      - performer_id: "PERF_A"
        coding_system: "project_BAP_derived"
        events: []

  motion_tracks:
    root:
      - performer_id: "PERF_A"
        position:
          interpolation: "c2_spline"
          keys: []
        orientation:
          representation: "quaternion_xyzw"
          interpolation: "slerp_squad"
          keys: []
        velocity_limits:
          linear_mps: [0.0, 3.0]
          angular_rps: [0.0, 4.0]

    skeleton:
      - performer_id: "PERF_A"
        topology: "RIG_A@2.1"
        rotation_representation: "continuous_6d"
        source: "generated|retrieved|captured|authored"
        data_asset: null
        key_joint_constraints: []

    phase:
      - performer_id: "PERF_A"
        global:
          representation: "phase_0_1"
          keys: []
        local:
          - channel: "left_foot"
            representation: "phase_vector"
            keys: []
          - channel: "right_foot"
            representation: "phase_vector"
            keys: []
          - channel: "pelvis"
            representation: "phase_vector"
            keys: []
          - channel: "right_hand"
            representation: "phase_vector"
            keys: []

    contacts:
      - contact_id: "CONTACT_01"
        performer_a: "PERF_A"
        body_region_a: "right_hand"
        entity_b: "PROP_01"
        body_or_surface_b: "handle"
        mode: "grasp"
        expected_interval: [1.20, 2.10]
        onset_tolerance_seconds: 0.06
        offset_tolerance_seconds: 0.08
        target_point_world: null
        target_normal_world: null
        maximum_slip_m: 0.015
        maximum_penetration_m: 0.005
        hardness: "hard"
        safety_mode: "simulated"

    dynamics:
      - performer_id: "PERF_A"
        body_mass_kg: null
        center_of_mass_track: null
        angular_momentum_targets: []
        impulse_events: []
        smoothness:
          jerk_weight: 0.15
          spectral_arc_length_weight: 0.05
        physical_mode: "kinematic_with_refinement"

    interaction:
      - interaction_id: "INTERACTION_01"
        participants: ["PERF_A", "PERF_B"]
        constraints:
          - type: "joint_distance"
            a: "PERF_A.right_wrist"
            b: "PERF_B.head"
            interval: [2.00, 2.08]
            target_m: 0.06
            tolerance_m: 0.025
            mode: "staged_near_contact"
          - type: "facing"
            a: "PERF_A.torso_forward"
            b: "PERF_B.root"
            interval: [0.0, 3.0]
            tolerance_degrees: 25

  camera_tracks:
    - camera_id: "CAM_A"
      pose:
        position_keys: []
        orientation_keys: []
        interpolation: "c2_spline_plus_squad"
      lens:
        focal_length_mm: 50
        sensor_width_mm: 36
        aperture_f: 2.8
        focus_distance_m:
          keys: []
      framing_constraints:
        - target: "PERF_A.face"
          interval: [0.0, 1.2]
          screen_box: [0.36, 0.18, 0.68, 0.62]
          hardness: "soft"
      visibility_constraints: []
      handheld_noise:
        enabled: false
        seed: 0
        translational_rms_m: 0.0
        rotational_rms_deg: 0.0
        frequency_band_hz: [0.0, 0.0]
      event_links:
        - event: "BEAT_02.apex"
          camera_action: "push_in"
          offset_seconds: -0.08

  audio_tracks:
    dialogue: []
    breath: []
    footsteps: []
    impacts: []
    foley: []
    score_cues: []

  appearance_constraints:
    identity_lock:
      performer_id: "PERF_A"
      strength: 0.90
    wardrobe_lock: []
    prop_continuity: []
    lighting_continuity: []

  generation_plan:
    target_model_profile: "MODEL_X@2.1"
    seed_policy: "locked_per_candidate"
    candidates: 8
    stages:
      - "score_validation"
      - "motion_generation"
      - "contact_and_physics_refinement"
      - "control_pass_rendering"
      - "video_synthesis"
      - "evidence_extraction"
      - "compliance_scoring"
      - "human_review"
    control_adapters:
      text: true
      reference_image: true
      pose: true
      depth: true
      segmentation: true
      optical_flow: false
      camera_6dof: true
      face_au: false
      audio: true
    fallback_policy:
      unsupported_face_au: "render_3d_face_control_pass"
      unsupported_contact: "generate_motion_upstream"

  verification:
    hard_failures:
      - "missing_required_contact"
      - "unsafe_penetration"
      - "identity_mismatch"
      - "camera_geography_violation"
    metrics:
      au_curve_error: {}
      affect_trajectory_error: {}
      laban_perceptual_score: {}
      joint_position_error: {}
      root_trajectory_error: {}
      contact_timing_error: {}
      foot_sliding: {}
      penetration: {}
      balance: {}
      jerk: {}
      camera_pose_error: {}
      temporal_compositionality: {}
      identity_similarity: {}
    acceptance:
      all_hard_constraints: true
      weighted_compliance_minimum: 0.82
      director_rating_minimum: 4
      director_rating_scale: [1, 5]

  revision_history: []
```

## C.1 Required Versus Optional Fields

A minimally valid score requires:

1. schema and document version;
2. explicit timebase and coordinate conventions;
3. at least one narrative beat;
4. at least one performer or scene subject;
5. a generation target or export profile;
6. provenance for authored and retrieved constraints; and
7. a verification policy.

FACS, Laban, contact, physics, and camera tracks are optional at the schema level because not every shot needs each one. A compiler should warn when a requested directorial effect depends on a missing track. For example, “the punch lands exactly on the cut” requires an interaction/contact event and an edit/camera event; prose alone is insufficient for deterministic verification.

## C.2 Constraint Semantics

Every constraint should expose four properties:

```yaml
constraint:
  target: "PERF_A.right_wrist"
  desired: {position_world: [0.4, 1.5, 2.1]}
  interval: [1.92, 2.00]
  hardness: "hard|soft|preference"
  priority: 0.90
  tolerance: {distance_m: 0.03}
  provenance: {note_id: "NOTE_12", source_ids: ["S30"]}
```

- A **hard** constraint invalidates a candidate outside tolerance.
- A **soft** constraint contributes to the objective but may yield to higher-priority requirements.
- A **preference** ranks otherwise acceptable candidates.
- Priority is meaningful only within a documented arbitration policy.
- Tolerance is mandatory for physical and temporal quantities because neither extraction nor generation is exact.

---

<!-- RAG_CHUNK id="cpcs.a4" title="Compilation and verification protocol" concepts="compiler, pseudocode, validation, deterministic checks, test plan" -->
<a id="cpcs-compilation-protocol"></a>
# Appendix D. Compilation and Verification Protocol

## D.1 End-to-End Compiler Algorithm

The compiler separates semantic planning from model-specific rendering. One possible implementation is:

```text
INPUTS
  screenplay segment
  storyboard panels and shot metadata
  director notes
  performer, set, prop, and camera assets
  model capability profile
  project knowledge base

1. NORMALIZE
  resolve identities, units, coordinate frames, timebase, and shot boundaries
  preserve each original note verbatim with author and timestamp

2. PARSE STORY
  identify action beats, objectives, tactics, obstacles, turns, causal order,
  continuity state, safety constraints, and required audience inferences

3. DETECT CONTROL NEEDS
  determine whether each beat requires affect, FACS, gaze, Laban, exact pose,
  phase, contact, dynamics, interaction, camera, audio, or appearance control

4. RETRIEVE
  issue typed queries for concepts, movement atoms, performance templates,
  calibration records, failure cases, and model-specific adapters
  reject sources that violate project licensing or evidence policy

5. PLAN ALTERNATIVES
  create one or more interpretations for ambiguous director language
  keep qualitative Laban terms and quantitative operationalizations linked
  mark unresolved choices for human selection or controlled sampling

6. COMPOSE SCORE
  place narrative, affect, face, body, motion, interaction, camera, and audio
  tracks on a shared timebase
  add event dependencies and constraint priorities

7. STATIC VALIDATE
  validate schema, units, IDs, time ranges, coordinate conventions,
  constraint conflicts, missing assets, and unsupported model controls

8. REALIZE MOTION
  retrieve, synthesize, or author key motion
  solve local phases, contacts, retargeting, and transitions
  perform physics or contact refinement where required

9. PROJECT CONTROL PASSES
  render skeleton, dense pose, depth, segmentation, normals, optical flow,
  contact masks, face crops or AU-conditioned proxy renders, and camera data

10. SYNTHESIZE VIDEO
  condition target video generator using the strongest supported controls
  lock identity, seed policy, and appearance references

11. EXTRACT EVIDENCE
  estimate face AUs, head pose, gaze, 2D/3D pose, contacts, root and camera
  motion, optical flow, identity, and temporal state transitions

12. SCORE COMPLIANCE
  align estimated evidence to the score
  compute track-specific errors and hard-constraint failures
  report confidence and occlusion for every estimate

13. HUMAN REVIEW
  present synchronized score, generated video, overlays, and violations
  capture director ratings and revision instructions at track level

14. REVISE
  update only affected score segments when possible
  retain prior candidates, seeds, metrics, and provenance

OUTPUTS
  approved CPCS score
  model-specific generation package
  generated video candidates
  evidence package and compliance report
  revision history
```

## D.2 Static Validation Rules

A score should fail before generation when any of the following is true:

- a referenced performer, prop, camera, beat, source, template, or asset ID is undefined;
- a time interval is outside the shot range or has an end before its start;
- coordinates are present without a declared reference frame;
- rotations mix conventions without an explicit conversion;
- hard constraints conflict beyond their tolerances;
- a contact requires geometry that is missing;
- a camera reveal rule conflicts with a required framing rule;
- a model profile lacks an adapter and no fallback is declared;
- a retrieved template has incompatible licensing or missing provenance;
- a safety-critical interaction lacks a simulation, staged-contact, or approved reference protocol.

## D.3 Dynamic Verification Checkpoints

Each pipeline stage should produce observable artifacts rather than an unverifiable “success” status.

| Stage | Required artifact | Pass condition |
|---|---|---|
| Story parse | Beat graph with source spans | Every generated beat links to screenplay or note text. |
| Retrieval | Ranked records with scores and source IDs | Required evidence tier and license filters are satisfied. |
| Score composition | Schema-valid CPCS file | No unresolved hard conflict; all units and frames declared. |
| Motion realization | 3D motion plus contact/phase overlays | Hard keyframes and contact events fall within tolerance. |
| Physics refinement | Simulation or constraint-solver log | No prohibited penetration; stable integration; recovery feasible. |
| Control rendering | Frame-synchronized control passes | Frame count, resolution, camera, and performer IDs match. |
| Video generation | Candidate manifest | Model version, seed, adapters, and input hashes recorded. |
| Evidence extraction | Time-aligned estimates with confidence | Coverage above threshold; occluded intervals flagged. |
| Compliance | Metric report and violation timeline | All hard constraints pass; weighted score exceeds threshold. |
| Human review | Signed review record | Director or delegated reviewer approves specified version. |

## D.4 Suggested Repository Checks

The following commands are examples for a production repository. Paths and validators are project-specific, but the outputs are deterministic and inspectable.

```bash
# 1. Validate syntax and schema.
python -m cpcs.validate scores/shot_014.yaml \
  --schema schemas/cpcs-1.0.json \
  --strict

# Expected: exit code 0 and "0 errors, 0 unresolved hard conflicts".

# 2. Check that all source and asset identifiers resolve.
python -m cpcs.audit_refs scores/shot_014.yaml \
  --source-index knowledge/sources.jsonl \
  --asset-manifest assets/manifest.json

# Expected: no MISSING_ID, LICENSE_BLOCK, or VERSION_AMBIGUITY records.

# 3. Compile to the target model package.
python -m cpcs.compile scores/shot_014.yaml \
  --model-profile models/model_x-2.1.yaml \
  --output builds/shot_014

# Expected: model_inputs/, control_passes/, compile_report.json,
# and a SHA-256 manifest.

# 4. Verify temporal alignment before expensive generation.
python -m cpcs.verify_controls builds/shot_014/control_passes \
  --score scores/shot_014.yaml \
  --max-frame-drift 0

# Expected: all tracks have identical frame IDs and no drift.

# 5. Score a generated candidate.
python -m cpcs.evaluate outputs/shot_014/candidate_003.mp4 \
  --score scores/shot_014.yaml \
  --evidence-cache evidence/shot_014/candidate_003 \
  --report reports/shot_014/candidate_003.json

# Expected: explicit metric values, confidence, and violation intervals.
```

The commands above are an interface specification, not a claim that a public `cpcs` package already exists.

## D.5 Metric Arbitration

A single scalar should not decide whether a shot is correct. CPCS recommends a lexicographic or gated policy:

1. **Safety and rights gates:** prohibited identity use, unsafe reference procedure, or unlicensed assets fail immediately.
2. **Hard continuity and contact gates:** missing actor, wrong prop, impossible geography, or prohibited collision fail.
3. **Control compliance:** facial, motion, event, and camera constraints must meet their specified tolerances.
4. **Physical plausibility:** evaluate support, slip, penetration, timing, and dynamics jointly.
5. **Visual and identity quality:** evaluate artifacts, temporal stability, likeness, and style.
6. **Dramatic effectiveness:** director, editor, movement expert, and audience judgments rank acceptable candidates.

This ordering prevents a photorealistic but incorrectly staged clip from outranking a slightly less polished clip that satisfies the shot’s essential meaning.

## D.6 Ablation Protocol

To determine whether each layer contributes, compare at minimum:

- **T:** text prompt only;
- **T+A:** text plus affect trajectory;
- **T+A+F:** add FACS/gaze;
- **T+A+L:** add Laban without explicit mechanics;
- **T+M:** text plus motion/contact controls;
- **T+A+F+L+M:** integrated performance score;
- **Full CPCS:** integrated performance, camera, audio, RAG, and verification loop.

For each condition, keep the identity references, base prompt, seed set, model version, shot length, and camera plan fixed where the architecture permits. Report both mean performance and candidate variance. The critical hypotheses are not only that Full CPCS improves quality, but that it:

- improves event timing;
- reduces revision locality, meaning a specific note can be changed without damaging unrelated tracks;
- increases agreement between independent directors about whether the instruction was followed;
- preserves action identity while expressive controls vary; and
- reduces the number of generations required to obtain an approved take.

---

<!-- RAG_CHUNK id="cpcs.a5" title="RAG ingestion and retrieval protocol" concepts="RAG, chunking, metadata, hybrid retrieval, source provenance, JSONL" -->
<a id="cpcs-rag-protocol"></a>
# Appendix E. RAG Ingestion and Retrieval Protocol

A RAG system for cinematic performance cannot be treated as a generic collection of paragraphs. It must retrieve **typed evidence and reusable control structures** while preventing descriptive research, production convention, and project-specific calibration from being merged into unsupported rules.

## E.1 Knowledge Record Types

The recommended corpus contains at least eight record types.

### 1. Concept records

Definitions and boundaries for FACS, AU phase, VAD/VAC, Laban factors, phase, contact, physics, camera, and evaluation. They answer “what does this term mean?” and “what does it not mean?”

### 2. Source records

Bibliographic metadata, abstracts or summaries, evidence level, publication status, license or access information, and the claims for which the source is relevant. They answer “what supports this statement?”

### 3. Movement-atom records

Reusable action fragments such as a left-foot plant, gaze acquisition, reach, weight shift, punch load, strike, recoil, recovery, or chair contact. They include entry/exit states, body parts, contacts, phases, and retargeting constraints.

### 4. Performance-template records

Time-aligned compositions for expressive patterns such as concealed fear, reluctant approach, heavy walk, controlled threat, delayed reaction, or shared laughter. They are examples, not universal biological templates.

### 5. Shot-template records

Camera and editing structures linked to performance events: reveal after recognition, push-in on affect leak, wide shot through impact, over-the-shoulder eyeline exchange, or camera hesitation.

### 6. Capability-profile records

Versioned declarations of what a target model can consume: text, image, pose, depth, segmentation, flow, trajectory, camera, audio, face controls, maximum frames, resolution, and known failure modes.

### 7. Calibration records

Mappings for a performer, rig, body model, face estimator, lens, or generator. They store neutral baselines, AU transfer curves, joint limits, scale conversions, and confidence intervals.

### 8. Failure-case records

Known examples of instruction leakage, identity drift, foot skating, contact miss, motion–camera entanglement, expression overshoot, temporal reordering, and metric gaming. They should include diagnosis and verified mitigation, not only a bad clip.

## E.2 Record Schema

A normalized JSONL record can use:

```json
{
  "record_id": "cpcs.07.03",
  "record_type": "paper_chunk",
  "document_id": "CPCS-RP-2026-01",
  "document_version": "1.0",
  "title": "Temporal FACS control",
  "heading_path": [
    "From Action Units to Action Beats",
    "4. Facial Action Coding as a Generative Control Layer",
    "4.3 Temporal FACS control"
  ],
  "text": "...",
  "concepts": ["FACS", "action_unit", "onset", "apex", "offset"],
  "aliases": ["facial timing", "AU curve"],
  "source_ids": ["S05", "S06"],
  "evidence_labels": ["ESTABLISHED", "PROPOSED"],
  "entities": ["AU04", "AU12"],
  "applicability": ["dialogue", "close_up", "image_to_video"],
  "limitations": ["performer_calibration_required"],
  "license_tags": ["research_summary"],
  "anchors": ["cpcs-face-temporal"],
  "language": "en",
  "word_count": 612,
  "content_hash": "sha256:..."
}
```

The `source_ids` field should point to standalone source records, not only a formatted reference list. Every generated answer should be able to return both the paper chunk and the underlying primary sources.

## E.3 Chunking Rules

Chunk boundaries should follow semantic units rather than fixed character counts.

1. Preserve the title and full heading path.
2. Keep equations with the paragraph that defines their variables.
3. Keep a table intact unless it exceeds the model context; when split, repeat column definitions.
4. Keep code blocks intact and tag their language.
5. Start a new chunk when evidence status changes from established to proposed if the distinction could be lost.
6. Do not combine unrelated source domains merely to reach a target size.
7. Carry a short overlap containing definitions and antecedents, not arbitrary trailing text.
8. Store the original unsplit section and offsets so a retrieved chunk can be expanded.
9. Exclude the formatted bibliography from semantic chunks, but ingest each bibliography item as a source record.
10. Hash normalized text so changed chunks can be re-embedded selectively.

A practical target for this paper is approximately 450–750 words per retrieval unit, with a hard maximum determined by the embedding and reranking stack. Token counts should be measured with the actual deployed tokenizer.

## E.4 Hybrid Retrieval

Dense similarity alone may retrieve a conceptually related but operationally incompatible record. CPCS recommends a staged query:

```text
1. Parse intent and entities.
2. Apply hard metadata filters.
3. Run lexical retrieval for exact codes and terms.
4. Run dense retrieval for semantic analogues.
5. Retrieve connected source, template, calibration, and failure records.
6. Rerank for task fit, evidence, temporal structure, and model support.
7. Diversify results across interpretations when direction is ambiguous.
8. Return provenance and unresolved conflicts to the compiler.
```

Hard filters may include:

- performer or rig compatibility;
- body part and action class;
- one-person, multi-person, or human–object interaction;
- contact type;
- shot scale and camera mode;
- duration range and frame rate;
- realistic versus stylized domain;
- evidence label and publication status;
- source date cutoff;
- asset license and consent scope;
- target model capability profile.

Lexical retrieval is necessary for identifiers such as `AU04`, `AU12`, `SMPL-X`, `phase`, `left_foot`, or `6DoF`. Dense retrieval is useful for phrases such as “the mask breaks,” “moves like the floor is fragile,” or “redirect the blow.” A cross-encoder or instruction-aware reranker should assess whether a candidate provides a control structure rather than only thematic similarity.

## E.5 Query Decomposition

Example director request:

> She crosses quickly, maintaining composure, then fear breaks through at the exact moment he steps into the light. The camera pushes in but should not reveal him early.

The RAG planner should decompose it into:

```yaml
queries:
  - type: concept
    terms: [experienced_affect, displayed_affect, affect_leak]
  - type: performance_template
    action: locomotion.walk_or_hurry
    affect: concealed_fear
    beat_relation: arrival_then_leak
  - type: movement_atom
    terms: [root_cross, gait_phase, deceleration, arrival]
  - type: shot_template
    terms: [delayed_reveal, push_in_on_affect_event]
  - type: failure_case
    terms: [premature_reveal, expression_overshoot, foot_skating]
  - type: capability_profile
    model_id: MODEL_X
    required_controls: [pose, camera, visibility, face]
filters:
  duration_seconds: [3.0, 7.0]
  actor_count: 2
  evidence_minimum: emerging_or_established
  project_license: allowed
```

The result set should not directly decide the performance. It supplies candidate interpretations, mechanics, and constraints for the score planner.

## E.6 Retrieval Grounding Policy

A generated score field should carry one of four provenance modes:

- **authored:** explicitly specified by a human;
- **derived:** mechanically computed from authored fields;
- **retrieved:** copied or adapted from a cited template or source;
- **generated:** proposed by the compiler without direct source support.

Generated values are permitted for creative planning, but they must not be presented as empirical laws. Safety-critical, identity-critical, or legally constrained values may require authored or approved provenance.

Example:

```yaml
weight_shift_start:
  value_seconds: 0.42
  provenance_mode: "generated"
  rationale: "supports 0.93 s strike contact while preserving pelvis lead"
  confidence: 0.58
  approval_required: true
```

## E.7 Source-Conflict Handling

When sources disagree or use different definitions, the RAG layer should preserve the conflict:

```json
{
  "conflict_id": "CONFLICT_LABAN_FLOW_PROXY_01",
  "topic": "computational proxy for bound versus free Flow",
  "positions": [
    {
      "source_ids": ["S21"],
      "summary": "LMA reliability and operational definitions require care."
    },
    {
      "template_ids": ["PROJECT_LMA_04"],
      "summary": "Project maps Flow partly to release timing and joint-velocity continuity."
    }
  ],
  "resolution": "retain qualitative label; use project proxy only under named calibration profile"
}
```

The compiler should never average incompatible definitions into a false consensus.

## E.8 Evaluation of the RAG Layer

RAG quality should be evaluated independently from video quality:

- **source precision:** fraction of retrieved records that actually support the requested claim or control;
- **source coverage:** whether required domains are represented;
- **constraint usefulness:** whether a retrieved record produces an executable or reviewable control;
- **provenance completeness:** fraction of score fields with resolvable origins;
- **definition preservation:** whether established, emerging, proposed, and operationalized claims remain distinguishable;
- **version correctness:** whether the compiler used the intended model, schema, template, and calibration versions;
- **license compliance:** whether blocked assets or records were excluded;
- **revision retrieval:** whether a director’s correction retrieves the relevant failure and calibration records on the next iteration;
- **hallucinated-standard rate:** frequency with which project-specific mappings are incorrectly described as scientific standards.

## E.9 Example Retrieval Questions

The corpus should answer questions such as:

```text
What is the difference between valence–arousal and a FACS AU curve?
Which controls make a heavy walk perceptible while preserving path and duration?
How should a right cross be represented as local phases and contact constraints?
What fields are required to synchronize an affect leak with a camera push-in?
Which metrics detect foot skating, contact mistiming, and temporal reordering?
What evidence supports using AUs as controllable expression parameters?
What parts of CPCS are proposed rather than established?
How should a model without native AU control receive a facial performance score?
What calibration is required before comparing AU intensity across performers?
Which source record defines Local Motion Phases?
```

## E.10 RAG Export Included With This Paper

The companion JSONL export generated from this Markdown contains:

- semantic paper chunks with heading paths;
- concepts from each `RAG_CHUNK` marker;
- extracted source IDs and evidence labels;
- stable anchors and content hashes;
- word and character counts;
- source records for every bibliography identifier; and
- document-level metadata.

The export is intended as an ingestion-ready starting point. Embeddings are deliberately not included because they depend on the user’s selected model, tokenizer, vector database, and privacy policy.

---

<!-- RAG_CHUNK id="cpcs.a6" title="Research evidence map" concepts="evidence map, sources, established, emerging, proposed" -->
<a id="cpcs-evidence-map"></a>
# Appendix F. Research Evidence Map

This map clarifies which parts of the framework are grounded in established or emerging literature and which are proposed integrations.

| CPCS component | Primary source IDs | Evidence status | What the sources support | What CPCS adds |
|---|---|---|---|---|
| Observable facial action decomposition | S01, S02 | Established | FACS vocabulary and coding logic for visible facial movement. | Machine-readable temporal tracks linked to generative controls. |
| Temporal facial events | S05, S06 | Established research methods | Onset, apex, offset, and temporal analysis of facial actions. | Directorial curves, event tolerances, and beat synchronization. |
| AU-conditioned face generation | S09–S11, S14, S15 | Established-to-emerging model evidence | AUs can serve as interpretable conditions for face editing or reenactment. | Integration with affect, body, camera, and shot verification. |
| Dimensional affect | S07, S08, S08A | Established | Continuous affect dimensions and measurement interfaces. | Separate experienced/displayed trajectories and VAC production alias. |
| Affect-sensitive face modeling | S03, S12, S13 | Established datasets and emerging generation methods | Valence/arousal labels or controls can be estimated or used in facial synthesis. | Use as high-level intent, not a deterministic AU mapping. |
| Body action/posture description | S16–S18 | Established descriptive research | Time-aligned body behavior and muscle activation studies for emotional body expression. | Typed body-event tracks without claiming a universal body FACS. |
| Laban movement description | S19–S21 | Established movement-analysis tradition with empirical reliability work | Body, Effort, Shape, and Space as movement descriptors. | Project-calibrated numerical proxies and generative adapters. |
| Laban-guided motion generation | S33, S34 | Emerging | Quantified Laban guidance and symbolic Laban-derived motion planning. | Placement inside a full cinematic score and compiler. |
| Kinematic body/face models | S25–S28 | Established computational representations | Shared parametric bodies/faces, mocap normalization, and continuous rotation representations. | Standard interface for score realization and evidence extraction. |
| Phase-based control | S22, S23 | Established character-animation methods | Global and local phase support responsive and multi-contact motion. | Editable beat- and body-part-aligned phase tracks. |
| Physics-based skill realization | S24 | Established research direction | Motion imitation under dynamic simulation and perturbation. | Selective use as a production layer governed by cinematic intent. |
| Text-to-motion language interface | S29, S35, S36 | Established-to-emerging | Text-motion datasets, motion tokens, and keyframe-first generation. | Compilation from screenplay to synchronized multi-track score. |
| Contact and interaction control | S30–S32 | Emerging | Joint-distance control, human–object contacts, and contact-aware motion generation. | Unified actor–actor, actor–object, staged-contact, and camera constraints. |
| Human video control | S37, S38 | Emerging | Decoupled pose/video generation and tokenized camera/human motion control. | Model-agnostic adaptation of full performance scores. |
| Camera/object motion control | S39–S41 | Emerging | Explicit camera trajectories, object trajectories, and independent motion control. | Event-linked camera grammar and reveal/visibility constraints. |
| Video/motion evaluation | S42, S44, S45, S48–S50 | Emerging benchmark ecosystem | Distributional video metrics, motion consistency, temporal transitions, human action coverage, and motion-quality analysis. | Score-specific compliance, hard constraints, and directorial acceptance gates. |
| Structured data and schema languages | S51–S57 | Established standards | JSON, JSON Schema, YAML, XML, namespaces, XSD, and XSLT provide defined data models, validation, qualification, and transformation mechanisms. | Assignment of YAML, JSON, XML, and JSONL to CPCS production roles and one shared semantic ontology. |
| Addressing, revision, and canonical JSON | S58–S61 | Established standards | JSON Pointer, JSON Patch, JSON Merge Patch, and JSON canonicalization support addressing, ordered edits, shallow merge updates, and deterministic serialization for hashing. | Typed cinematic merge algebra, scope cascade, locks, temporal splice/blend rules, and provenance reports. |
| Current video API adapter examples | S62–S66 | Current operational documentation | Official examples of prompt-versus-parameter separation, first/last-frame generation, JSON API requests, and model-specific capability change. | Versioned capability profiles, controlled degradation classes, loss budgets, and model-agnostic target packages. |
| Production control layers | This paper | Proposed | Not an existing unified standard. | Integrated FACS, Laban, combat/action, director, VFX/anime, audio, and marketing contracts with compilation and verification targets. |
| CPCS ontology and schema | This paper | Proposed | Not an existing standard. | Integrated score, compiler, RAG model, schemas, and evaluation plan. |

## F.1 Interpretation Rule

A source appearing in a row does not endorse every CPCS design choice in that row. It supports the narrower claim described under “What the sources support.” CPCS additions remain proposals until implemented and evaluated.

---

<!-- RAG_CHUNK id="cpcs.a7" title="Cross-format CPCS compiler reference" concepts="normative schema, YAML authoring, canonical JSON, XML envelope, merge policies, compile report, pseudocode" -->
<a id="cpcs-cross-format-reference"></a>
# Appendix G. Cross-Format CPCS Compiler Reference

This appendix condenses the structured-language chapter into an implementation-oriented reference. The keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** describe the proposed CPCS contract; they do not claim IETF or W3C standard status for CPCS.

## G.1 Representation Roles

| Representation | Normative CPCS role | May contain unresolved inheritance? | Primary validator | Typical output |
|---|---|---:|---|---|
| YAML | Human authoring, styles, imports, variants, overrides | Yes | restricted YAML parser plus CPCS authoring schema | canonical JSON |
| JSON | Fully resolved canonical score, schemas, patches, requests, reports | No in canonical score | JSON Schema plus semantic validator | target package or evidence |
| XML | Ordered director/narrative envelope and namespaced annotations | Yes, only through explicit CPCS references | XML parser, namespace checks, XSD, semantic validator | authoring AST or canonical JSON |
| JSONL | RAG, compiler events, metrics, experiments, audits | Not applicable per line | line-level JSON Schema and stream rules | searchable evidence stream |
| Binary/media assets | Dense motion, images, video, audio, render passes | No semantic inheritance inside opaque bytes | format-specific validator plus manifest | native model or production input |

## G.2 Required Canonical Fields

A canonical CPCS JSON document SHOULD contain:

```text
schema_version
ontology_version
document_id
document_revision
timebase
coordinate_system
actors
assets
beats
effective_styles
tracks
constraints
adapter_extensions
provenance
rights_and_approvals
content_digest
```

`effective_styles` MUST contain resolved values. Source-level `extends` and `overrides` MUST NOT remain as unresolved instructions in the canonical score. `provenance` MUST retain enough information to reconstruct why each effective field exists.

## G.3 Style Domain Registry

| Domain path | Representative fields | Default merge | Common compilation |
|---|---|---|---|
| `/style/visual` | medium, palette, contrast, texture, era | typed deep merge | prompt, references, color/look pipeline |
| `/style/performance` | acting scale, gesture amplitude, externalization | typed deep merge | performance prompt, motion/face amplitude modifiers |
| `/style/affect_display` | suppression, leakage, recovery | replace per field | experienced/displayed affect relation, AU amplitude priors |
| `/style/motion` | realism, smoothness, microvariation | replace or explicit delta | motion generator settings and evaluation tolerances |
| `/style/laban` | Weight, Time, Space, Flow, Shape | replace per dimension | retrieval, style embedding, retiming/trajectory modifiers |
| `/style/cinematography` | camera grammar, lens family, framing | typed deep merge | camera path, prompt, first/last frames |
| `/style/editorial` | pace, cut bias, holds, time warp | keyed/timeline merge | EDL and presentation-time mapping |
| `/style/vfx` | effect language, shake, trails, smear policy | keyed-event merge | masks, compositor graph, prompt |
| `/style/audio` | dynamics, breath, impacts, ambience | typed deep merge | audio prompt, foley and mix cues |
| `/style/marketing` | product priority, claim density, CTA profile | typed deep merge with locked approvals | variants, hero frames, titles, measurement metadata |

## G.4 Merge-Policy Registry

```json
{
  "merge_policies": {
    "replace": {
      "allowed_types": ["string", "number", "boolean", "null", "object", "array"]
    },
    "deep_merge_typed": {
      "allowed_types": ["object"],
      "child_policy_source": "schema"
    },
    "merge_by_id": {
      "allowed_types": ["array"],
      "identity_field": "id",
      "duplicate_without_policy": "error"
    },
    "append_ordered": {
      "allowed_types": ["array"],
      "ordering": "source_then_override"
    },
    "set_union": {
      "allowed_types": ["array"],
      "identity": "canonical_value"
    },
    "replace_track": {
      "allowed_types": ["array", "object"],
      "requires": ["timebase", "boundary_policy"]
    },
    "splice_interval": {
      "allowed_types": ["array", "object"],
      "requires": ["interval", "boundary_policy", "overlap_policy"]
    },
    "blend_interval": {
      "allowed_types": ["array", "object"],
      "requires": ["interval", "blend_curve"],
      "forbidden_for": ["hard_boolean_contact"]
    },
    "conjoin_or_conflict": {
      "allowed_types": ["array"],
      "on_incompatible_hard_constraints": "error"
    }
  }
}
```

## G.5 Cross-Format Package Example

### G.5.1 `project.yaml`

```yaml
schema: "cpcs-project-authoring/1.1"
project_id: "campaignA"

imports:
  - id: "visual_base"
    uri: "style://campaignA/visual-base@3.0.0"
    sha256: "..."
  - id: "narrative_sequence"
    uri: "file://sequence03.xml"
    media_type: "application/xml"
    sha256: "..."
  - id: "body_track"
    uri: "asset://motion/shot014.body.json"
    media_type: "application/cpcs+json"
    sha256: "..."

extends: ["visual_base"]

targets:
  - id: "review_prompt_model"
    adapter: "generic.prompt-video/1"
  - id: "final_render_assisted"
    adapter: "internal.render-to-video/4"

variants:
  - {id: "landscape", ratio: "16:9", duration_s: 6}
  - {id: "vertical", ratio: "9:16", duration_s: 6}
```

### G.5.2 `sequence03.xml`

```xml
<cpcs:sequence xmlns:cpcs="urn:cpcs:core:1.1"
               xmlns:face="urn:cpcs:facs:1.1"
               xmlns:cam="urn:cpcs:camera:1.1"
               id="campaignA.sequence03">
  <cpcs:scene id="roof_encounter">
    <cpcs:shot id="shot014" scoreRef="asset://scores/shot014.cpcs.json">
      <cpcs:direction>
        The audience sees Mara's fear only after she recognizes the blood.
      </cpcs:direction>
      <face:event actor="mara" au="AU04" apex="2.74s" peak="0.28"/>
      <cam:move type="dolly-in" start="2.20s" end="3.20s"/>
    </cpcs:shot>
  </cpcs:scene>
</cpcs:sequence>
```

### G.5.3 `shot014.body.json`

```json
{
  "$schema": "https://schemas.example.org/cpcs/1.1/body-track.schema.json",
  "track_id": "shot014.body",
  "actor_id": "mara",
  "timebase": {"fps": 24},
  "representation": "joint_rotation_6d",
  "asset_uri": "asset://motion/shot014.body.npz",
  "contact_events": [
    {"id": "left_final_plant", "effector": "left_foot", "frame": 59, "type": "support"}
  ],
  "content_digest": "sha256:..."
}
```

### G.5.4 Resolved `shot014.cpcs.json`

The compiler emits one document in which the XML direction, YAML project profile, and JSON body track have been mapped into the same ontology. The canonical document stores source pointers such as:

```json
{
  "provenance": {
    "/narrative/audience_knowledge": {
      "source": "file://sequence03.xml",
      "locator": "/cpcs:sequence/cpcs:scene/cpcs:shot/cpcs:direction"
    },
    "/tracks/body": {
      "source": "asset://motion/shot014.body.json",
      "locator": "",
      "digest": "sha256:..."
    },
    "/effective_styles/visual": {
      "source": "style://campaignA/visual-base@3.0.0"
    }
  }
}
```

## G.6 Capability Profile Schema Fragment

```json
{
  "$id": "https://schemas.example.org/cpcs/1.1/adapter-profile.schema.json",
  "type": "object",
  "required": ["id", "model_id", "verified_on", "accepts"],
  "properties": {
    "id": {"type": "string"},
    "model_id": {"type": "string"},
    "api_version": {"type": ["string", "null"]},
    "verified_on": {"type": "string", "format": "date"},
    "accepts": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["support"],
        "properties": {
          "support": {
            "enum": ["native", "model_specific", "approximate", "none"]
          },
          "constraints": {"type": "object"}
        }
      }
    }
  }
}
```

## G.7 Compile-Report Schema Fragment

```json
{
  "control_mappings": [
    {
      "control_id": "shot014.mara.au04",
      "source_path": "/tracks/face/0",
      "importance": "hard_target_soft_tolerance",
      "status": "baked_into_reference",
      "outputs": [
        "control/face_landmarks_000060.json",
        "control/expression_apex_000066.png"
      ],
      "losses": [
        "continuous AU curve reduced to landmark sequence and one appearance reference"
      ],
      "verification": [
        "au04_apex_time_error_s",
        "au04_intensity_mae"
      ]
    },
    {
      "control_id": "shot014.marketing.product_hero",
      "source_path": "/marketing/product_hero_interval_s",
      "importance": "hard",
      "status": "native_approximate",
      "outputs": ["control/product_mask/", "prompt.txt"],
      "verification": ["product_visible_area_ratio", "product_occlusion_ratio"]
    }
  ]
}
```

## G.8 Reference Compiler Pseudocode

```python
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class CompileResult:
    canonical_score: dict[str, Any]
    target_package: dict[str, Any]
    resolve_report: dict[str, Any]
    compile_report: dict[str, Any]


def compile_cpcs(source_uri: str, target_profile_uri: str) -> CompileResult:
    source = parse_by_media_type(source_uri, restricted=True)
    validate_authoring_syntax(source)

    graph = build_dependency_graph(source)
    verify_digests_licenses_and_rights(graph)

    ast = normalize_sources_to_semantic_ast(graph)
    resolved, resolve_report = resolve_typed_inheritance(ast)
    reject_hard_conflicts(resolve_report)

    canonical = normalize_units_time_and_coordinates(resolved)
    validate_json_schema(canonical, schema="cpcs/1.1")
    validate_cross_field_semantics(canonical)
    validate_constraint_feasibility(canonical)

    canonical = attach_field_provenance(canonical, resolve_report)
    canonical_digest = canonicalize_and_hash_json(canonical)

    target_profile = load_and_validate_capability_profile(target_profile_uri)
    plan = negotiate_capabilities(canonical, target_profile)
    reject_unsupported_hard_controls(plan)

    package, compile_report = emit_target_package(canonical, plan)
    verify_package_alignment(package, canonical["timebase"])
    attach_manifest(package, canonical_digest, target_profile)

    return CompileResult(canonical, package, resolve_report, compile_report)
```

Every function above has an observable failure mode. No semantic step should be hidden inside a final prompt string.

## G.9 Direct-Prompt Templates by Format

These templates are for prompt-only or LLM-mediated use. They do not replace compilation.

### YAML-oriented prompt

```yaml
shot: "6-second single take"
subject_action: "Mara approaches, notices blood, contains fear"
face: "subtle AU04 and trace AU05 only after 2.5 seconds"
body_quality: "direct path; sustained time; bound flow"
camera: "65 mm slow dolly-in beginning at recognition"
constraints:
  - "no early fear display"
  - "no extra step after final plant"
```

### JSON-oriented prompt

```json
{
  "shot": "6-second single take",
  "subject_action": "Mara approaches, notices blood, contains fear",
  "performance_summary": {
    "face": "subtle brow lower and trace eye widen after recognition",
    "body": "direct, sustained, bound"
  },
  "camera": "65 mm slow dolly-in",
  "must_not": ["early fear display", "extra final step"]
}
```

### XML-oriented prompt

```xml
<shot duration="6s" continuity="single-take">
  <action>Mara approaches, notices blood, and contains fear.</action>
  <performance>
    <face timing="after-2.5s">subtle AU04; trace AU05</face>
    <body>direct path; sustained time; bound flow</body>
  </performance>
  <camera lens="65mm" move="slow-dolly-in" trigger="recognition"/>
  <avoid>early fear display; extra final step</avoid>
</shot>
```

The formats communicate roughly the same semantic summary. Their relative effectiveness depends on the interpreter and target model, not on a universal superiority of braces, indentation, or tags.

## G.10 Acceptance Checklist

A cross-format CPCS implementation is not complete unless all answers below are observable.

- Can the parser identify the schema and reject duplicate or unsafe constructs?
- Can every import be resolved to a pinned version and digest?
- Can the resolver explain every inherited value and lock?
- Does every inheritable path declare a typed merge policy?
- Are ordered events represented by arrays or explicit timestamps?
- Are null, missing, and delete distinguished?
- Can the canonical JSON validate structurally and semantically?
- Can the compiler state exactly what each FACS, Laban, action, director, VFX, and marketing control became?
- Does the target profile identify unsupported controls before generation?
- Are prompt text, API parameters, media controls, postproduction events, and evaluation targets separated?
- Do all control passes share one timebase and frame identity?
- Does every generated variant have a content hash, model/adapter version, and measurement identifier?
- Can a reviewer revise one field through an auditable patch without rewriting the entire shot?

---

<!-- RAG_CHUNK id="cpcs.a8" title="Video-to-CPCS operational reference" concepts="Video Observation Graph, extraction schema, provider prompts, CLI, reverse compiler" -->
<a id="cpcs-video-extraction-reference"></a>
# Appendix H. Video-to-CPCS Operational Reference

## H.1 Package Artifacts

The companion package operationalizes Section 30 with these files:

| Artifact | Role |
|---|---|
| `docs/VIDEO_TO_CPCS_EXTRACTION_GUIDE.md` | Standalone research and implementation guide. |
| `schemas/CPCS_Video_Observation_Graph_Schema.json` | Draft 2020-12 schema for the canonical observation graph. |
| `schemas/CPCS_Video_Observation_Record_Schema.json` | Schema for line-oriented extractor observations and provider hypotheses. |
| `scripts/video_to_cpcs_reference_pipeline.py` | All-in-one local `probe`, `prepare`, `init-record`, and `validate` workflow for a comprehensive extraction-record scaffold. |
| `scripts/extract_video_manifest.py` | Lower-level FFprobe/FFmpeg preprocessing, hashing, proxy creation, semantic-frame extraction, and cut-candidate generation for the observation-graph workflow. |
| `scripts/merge_video_observations.py` | Deterministic fusion of JSON/JSONL records with provenance and conflict reporting. |
| `scripts/validate_video_observation_graph.py` | Schema and semantic validation of clocks, time ranges, identifiers, confidence, references, and resolution claims. |
| `prompts/gemini_video_to_cpcs_system.xml` | Namespaced semantic-analysis instruction envelope. |
| `prompts/gemini_video_to_cpcs_request.json` | Schema-oriented request template for sequence, shot, beat, and contradiction passes. |
| `prompts/twelvelabs_pegasus_segment_definitions.json` | Timestamped segment definitions for editorial, action, UGC, VFX, and marketing channels. |
| `prompts/video_extraction_plan.yaml` | Human-readable orchestration plan and extractor capability profile. |
| `examples/video_to_cpcs/` | Fight, UGC, canonical graph, and evidence-fusion examples. |

## H.2 Evidence Record Contract

Every observation should be independently serializable. The minimum contract is:

```json
{
  "record_id": "obs.pose.actor_a.000042",
  "source_id": "asset.reference.001",
  "time_range": {"start_s": 1.750, "end_s": 1.792},
  "clock": "source_pts",
  "layer": "body_pose",
  "claim": {"type": "right_wrist_position", "value": [0.61, 0.42]},
  "evidence_class": "measured",
  "confidence": 0.91,
  "extractor": {
    "name": "example-pose-extractor",
    "version": "pinned-version",
    "parameters_digest": "sha256:..."
  },
  "evidence": [
    {"asset": "frame://source/42", "locator": "bbox:actor_a"}
  ]
}
```

`evidence_class` is one of `measured`, `detected`, `inferred`, `interpreted`, or `authored`. Confidence values are not assumed to be calibrated across tools. The fusion layer retains tool-specific confidence and may add a separately calibrated `resolved_confidence`.

## H.3 Canonical Graph Contract

The graph separates observations from resolved claims:

```json
{
  "schema": "cpcs-video-observation-graph/1.0",
  "source": {
    "id": "asset.reference.001",
    "sha256": "...",
    "duration_s": 8.0,
    "timebase": {"numerator": 1, "denominator": 24000}
  },
  "segments": {
    "shots": [],
    "scenes": [],
    "beats": []
  },
  "entities": {"actors": [], "objects": []},
  "observations": [],
  "resolved_claims": [],
  "contradictions": [],
  "cpcs_projection": {},
  "validation": {}
}
```

The `cpcs_projection` is a derivative view. The observations and their source locators remain the audit record.

## H.4 Recommended Local Preprocessing

Two compatible local entry points are provided. The comprehensive-record path creates a probe manifest, synchronized semantic/performance/face derivatives, a schema-valid extraction-record scaffold, and a final record validation report:

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

The observation-graph path emits a compact source manifest and cut candidates, after which independent provider and detector records are merged into the canonical VOG:

```bash
python scripts/extract_video_manifest.py reference.mp4 \
  --output-dir work/reference_001 \
  --analysis-fps 24 \
  --semantic-fps 1 \
  --scene-threshold 0.35
```

Expected outputs include `source_probe.json`, `source_manifest.json`, `analysis_proxy.mp4`, `audio_16k_mono.wav` when audio exists, `semantic_frames/`, and `shot_candidates.json`. The script exits nonzero when FFprobe cannot identify a video stream or when a generated proxy falls outside its duration tolerance.

## H.5 Provider Passes

Provider outputs should be saved as evidence records, not copied directly into the resolved graph.

```text
sequence pass
  → narrative, scene, persuasive arc, identities as anonymous track roles

shot pass
  → shot purpose, scale, angle, movement, transition, visible action

beat pass
  → initiation, reveal, contact, reaction, proof, CTA, gaze change

domain pass
  → face, body, action, camera/edit, audio, VFX, marketing

contradiction pass
  → ambiguous timestamps, alternative action labels, unsupported inferences
```

Provider capability profiles must include `provider`, `model`, `api_version`, `verified_on`, input sampling assumptions, schema support, and known limits. A dated profile is part of reproducibility because hosted video-analysis APIs can change [S67, S71, S74].

## H.6 Merge and Validation

```bash
python scripts/merge_video_observations.py \
  --manifest work/reference_001/source_manifest.json \
  --inputs observations/*.json observations/*.jsonl \
  --output work/reference_001/video_observation_graph.json \
  --conflicts work/reference_001/conflicts.json

python scripts/validate_video_observation_graph.py \
  work/reference_001/video_observation_graph.json \
  --schema schemas/CPCS_Video_Observation_Graph_Schema.json
```

A successful merge does not imply that interpretations are correct. It means records are structurally compatible, source hashes agree, time ranges are legal, identifiers resolve, and conflicts have not been silently discarded.

## H.7 Reverse Compilation Outputs

The reverse compiler can emit:

```text
cpcs_resolved.json
prompt.txt
negative_constraints.txt
pose_tracks/
face_tracks/
gaze_tracks/
depth_or_camera/
actor_and_object_masks/
camera_plan.json
edit_plan.otio or edit_plan.json
vfx_events.json
audio_timing.json
marketing_constraints.json
compile_report.json
verification_targets.json
```

The output package must declare which controls are exact, approximate, text-only, baked into references, delegated to postproduction, retained only for evaluation, or unsupported.

## H.8 Non-Copying Normalization

Before using an extracted graph as a generative control source, a policy and creative review should classify fields as:

- **retain:** authorized causal order, duration pattern, motion quality, camera grammar, proof sequence;
- **parameterize:** timing tolerances, shot scale, action intensity, gaze duty cycle, product visibility;
- **replace:** identity, voice, dialogue wording, logos, wardrobe, environment, protected characters;
- **exclude:** private information, disallowed biometric identifiers, unsafe stunt instructions, unlicensed assets.

The intended result is structural translation, not a guarantee of legal non-infringement. Rights review remains project-specific.

## H.9 Round-Trip Acceptance

After generation, run the same extraction stack on the output and compare graphs. At minimum, report:

- shot-boundary and event-time error;
- action-node and causal-edge agreement;
- normalized root/joint trajectory agreement;
- contact/near-contact timing;
- gaze-to-target intervals;
- AU event timing where face quality permits;
- shot scale, screen direction, and camera-motion agreement;
- speech, caption, impact, and music-beat alignment;
- product visibility, proof order, and CTA hold for marketing work;
- unresolved contradictions and reviewer decisions.

No single score should hide failures in a critical layer. Acceptance is a vector of compliance metrics plus human review.

---

<a id="cpcs-references"></a>
# Full Reference List

The stable identifiers below are used throughout the paper. URLs point to primary publisher pages, official proceedings, DOI records, or author-posted preprints. Publication years follow the cited version; online-first and issue years are noted when material.

<a id="source-S01"></a>
**[S01]** Ekman, P., & Friesen, W. V. (1978). *Facial Action Coding System: A Technique for the Measurement of Facial Movement*. Consulting Psychologists Press.

<a id="source-S02"></a>
**[S02]** Ekman, P., Friesen, W. V., & Hager, J. C. (2002). *Facial Action Coding System: The Manual on CD-ROM*. A Human Face.

<a id="source-S03"></a>
**[S03]** Mollahosseini, A., Hasani, B., & Mahoor, M. H. (2017; journal issue 2019). AffectNet: A database for facial expression, valence, and arousal computing in the wild. *IEEE Transactions on Affective Computing, 10*(1), 18–31. https://doi.org/10.1109/TAFFC.2017.2740923 · https://arxiv.org/abs/1708.03985

<a id="source-S04"></a>
**[S04]** Mavadati, S. M., Mahoor, M. H., Bartlett, K., Trinh, P., & Cohn, J. F. (2013). DISFA: A spontaneous facial action intensity database. *IEEE Transactions on Affective Computing, 4*(2), 151–160. https://doi.org/10.1109/T-AFFC.2013.4

<a id="source-S05"></a>
**[S05]** Valstar, M. F., & Pantic, M. (2006). Fully automatic facial action unit detection and temporal analysis. In *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition Workshops*. https://doi.org/10.1109/CVPRW.2006.85

<a id="source-S06"></a>
**[S06]** Valstar, M. F., & Pantic, M. (2012). Fully automatic recognition of the temporal phases of facial actions. *IEEE Transactions on Systems, Man, and Cybernetics, Part B, 42*(1), 28–43. https://doi.org/10.1109/TSMCB.2011.2163710

<a id="source-S07"></a>
**[S07]** Russell, J. A. (1980). A circumplex model of affect. *Journal of Personality and Social Psychology, 39*(6), 1161–1178. https://doi.org/10.1037/h0077714

<a id="source-S08"></a>
**[S08]** Mehrabian, A., & Russell, J. A. (1974). *An Approach to Environmental Psychology*. MIT Press.

<a id="source-S08A"></a>
**[S08A]** Bradley, M. M., & Lang, P. J. (1994). Measuring emotion: The Self-Assessment Manikin and the semantic differential. *Journal of Behavior Therapy and Experimental Psychiatry, 25*(1), 49–59. https://doi.org/10.1016/0005-7916(94)90063-9

<a id="source-S09"></a>
**[S09]** Pumarola, A., Agudo, A., Martinez, A. M., Sanfeliu, A., & Moreno-Noguer, F. (2018). GANimation: Anatomically-aware facial animation from a single image. In *European Conference on Computer Vision (ECCV)*. https://doi.org/10.1007/978-3-030-01249-6_50 · https://arxiv.org/abs/1807.09251

<a id="source-S10"></a>
**[S10]** Tripathy, S., Kannala, J., & Rahtu, E. (2020). ICface: Interpretable and controllable face reenactment using GANs. In *IEEE/CVF Winter Conference on Applications of Computer Vision (WACV)*, 3385–3394. https://openaccess.thecvf.com/content_WACV_2020/html/Tripathy_ICface_Interpretable_and_Controllable_Face_Reenactment_Using_GANs_WACV_2020_paper.html · https://arxiv.org/abs/1904.01909

<a id="source-S11"></a>
**[S11]** Tripathy, S., Kannala, J., & Rahtu, E. (2021). FACEGAN: Facial Attribute Controllable rEenactment GAN. In *IEEE/CVF Winter Conference on Applications of Computer Vision (WACV)*. https://openaccess.thecvf.com/content/WACV2021/html/Tripathy_FACEGAN_Facial_Attribute_Controllable_rEenactment_GAN_WACV_2021_paper.html · https://arxiv.org/abs/2011.04439

<a id="source-S12"></a>
**[S12]** Daněček, R., Black, M. J., & Bolkart, T. (2022). EMOCA: Emotion Driven Monocular Face Capture and Animation. In *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 20311–20322. https://openaccess.thecvf.com/content/CVPR2022/html/Danecek_EMOCA_Emotion_Driven_Monocular_Face_Capture_and_Animation_CVPR_2022_paper.html · https://arxiv.org/abs/2204.11312

<a id="source-S13"></a>
**[S13]** Azari, B., & Lim, A. (2024). EmoStyle: One-Shot Facial Expression Editing Using Continuous Emotion Parameters. In *IEEE/CVF Winter Conference on Applications of Computer Vision (WACV)*, 6385–6394. https://openaccess.thecvf.com/content/WACV2024/html/Azari_EmoStyle_One-Shot_Facial_Expression_Editing_Using_Continuous_Emotion_Parameters_WACV_2024_paper.html

<a id="source-S14"></a>
**[S14]** Varanka, T., Khor, H.-Q., Li, Y., Wei, M., Kung, H., Sebe, N., & Zhao, G. (2024). Towards Localized Fine-Grained Control for Facial Expression Generation. *arXiv preprint arXiv:2407.20175*. https://arxiv.org/abs/2407.20175

<a id="source-S15"></a>
**[S15]** Wei, M., Varanka, T., Jiang, X., Khor, H.-Q., & Zhao, G. (2025). MagicFace: High-Fidelity Facial Expression Editing with Action-Unit Control. *arXiv preprint arXiv:2501.02260*. https://arxiv.org/abs/2501.02260

<a id="source-S16"></a>
**[S16]** Dael, N., Mortillaro, M., & Scherer, K. R. (2012). The Body Action and Posture Coding System (BAP): Development and reliability. *Journal of Nonverbal Behavior, 36*(2), 97–121. https://doi.org/10.1007/s10919-012-0130-0

<a id="source-S17"></a>
**[S17]** Dael, N., Mortillaro, M., & Scherer, K. R. (2012). Emotion expression in body action and posture. *Emotion, 12*(5), 1085–1101. https://doi.org/10.1037/a0025737

<a id="source-S18"></a>
**[S18]** Huis in ’t Veld, E. M. J., van Boxtel, G. J. M., & de Gelder, B. (2014). The Body Action Coding System II: Muscle activations during the perception and expression of emotion. *Frontiers in Behavioral Neuroscience, 8*, 330. https://doi.org/10.3389/fnbeh.2014.00330

<a id="source-S19"></a>
**[S19]** Laban, R., & Lawrence, F. C. (1947). *Effort*. Macdonald & Evans.

<a id="source-S20"></a>
**[S20]** Bartenieff, I., & Lewis, D. (1980). *Body Movement: Coping with the Environment*. Gordon and Breach.

<a id="source-S21"></a>
**[S21]** Bernardet, U., Fdili Alaoui, S., Studd, K., Bradley, K., Pasquier, P., & Schiphorst, T. (2019). Assessing the reliability of the Laban Movement Analysis system. *PLOS ONE, 14*(6), e0218179. https://doi.org/10.1371/journal.pone.0218179

<a id="source-S22"></a>
**[S22]** Holden, D., Komura, T., & Saito, J. (2017). Phase-Functioned Neural Networks for Character Control. *ACM Transactions on Graphics, 36*(4), Article 42. https://doi.org/10.1145/3072959.3073663

<a id="source-S23"></a>
**[S23]** Starke, S., Zhao, Y., Komura, T., & Zaman, K. (2020). Local Motion Phases for Learning Multi-Contact Character Movements. *ACM Transactions on Graphics, 39*(4), Article 54. https://doi.org/10.1145/3386569.3392450

<a id="source-S24"></a>
**[S24]** Peng, X. B., Abbeel, P., Levine, S., & van de Panne, M. (2018). DeepMimic: Example-Guided Deep Reinforcement Learning of Physics-Based Character Skills. *ACM Transactions on Graphics, 37*(4), Article 143. https://doi.org/10.1145/3197517.3201311

<a id="source-S25"></a>
**[S25]** Li, T., Bolkart, T., Black, M. J., Li, H., & Romero, J. (2017). Learning a model of facial shape and expression from 4D scans. *ACM Transactions on Graphics, 36*(6), Article 194. https://doi.org/10.1145/3130800.3130813

<a id="source-S26"></a>
**[S26]** Pavlakos, G., Choutas, V., Ghorbani, N., Bolkart, T., Osman, A. A. A., Tzionas, D., & Black, M. J. (2019). Expressive Body Capture: 3D Hands, Face, and Body from a Single Image. In *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 10975–10985. https://openaccess.thecvf.com/content_CVPR_2019/html/Pavlakos_Expressive_Body_Capture_3D_Hands_Face_and_Body_From_a_Single_CVPR_2019_paper.html

<a id="source-S27"></a>
**[S27]** Mahmood, N., Ghorbani, N., Troje, N. F., Pons-Moll, G., & Black, M. J. (2019). AMASS: Archive of Motion Capture as Surface Shapes. In *IEEE/CVF International Conference on Computer Vision (ICCV)*, 5442–5451. https://arxiv.org/abs/1904.03278

<a id="source-S28"></a>
**[S28]** Zhou, Y., Barnes, C., Lu, J., Yang, J., & Li, H. (2019). On the Continuity of Rotation Representations in Neural Networks. In *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*. https://arxiv.org/abs/1812.07035

<a id="source-S29"></a>
**[S29]** Guo, C., Zou, S., Zuo, X., Wang, S., Ji, W., Li, X., & Cheng, L. (2022). Generating Diverse and Natural 3D Human Motions from Text. In *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 5152–5161. https://openaccess.thecvf.com/content/CVPR2022/html/Guo_Generating_Diverse_and_Natural_3D_Human_Motions_From_Text_CVPR_2022_paper.html

<a id="source-S30"></a>
**[S30]** Wang, Z., Wang, J., Li, Y., Lin, D., & Dai, B. (2024). InterControl: Zero-shot Human Interaction Generation by Controlling Every Joint. In *Advances in Neural Information Processing Systems 37*. https://proceedings.neurips.cc/paper_files/paper/2024/hash/be41269a9fe258f1ecba663b0b402322-Abstract-Conference.html · https://arxiv.org/abs/2311.15864

<a id="source-S31"></a>
**[S31]** Diller, C., & Dai, A. (2024). CG-HOI: Contact-Guided 3D Human-Object Interaction Generation. In *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*. https://openaccess.thecvf.com/content/CVPR2024/html/Diller_CG-HOI_Contact-Guided_3D_Human-Object_Interaction_Generation_CVPR_2024_paper.html · https://arxiv.org/abs/2311.16097

<a id="source-S32"></a>
**[S32]** Ma, S., Cao, Q., Zhang, J., & Tao, D. (2024). Contact-aware Human Motion Generation from Textual Descriptions. *arXiv preprint arXiv:2403.15709*. https://arxiv.org/abs/2403.15709

<a id="source-S33"></a>
**[S33]** Kim, H., Kim, G., & Chun, S. Y. (2025). LaMoGen: Laban Movement-Guided Diffusion for Text-to-Motion Generation. *arXiv preprint arXiv:2509.24469*. https://arxiv.org/abs/2509.24469

<a id="source-S34"></a>
**[S34]** Jiang, J., Au, H. Y., Xiang, J., & Chen, J. (2026). LaMoGen: Language to Motion Generation Through LLM-Guided Symbolic Inference. *arXiv preprint arXiv:2603.11605*. https://arxiv.org/abs/2603.11605

<a id="source-S35"></a>
**[S35]** Jiang, B., Chen, X., Liu, W., Yu, J., Yu, G., & Chen, T. (2023). MotionGPT: Human Motion as a Foreign Language. In *Advances in Neural Information Processing Systems 36*. https://proceedings.neurips.cc/paper_files/paper/2023/hash/3fbf0c1ea0716c03dea93bb6be78dd6f-Abstract-Conference.html · https://arxiv.org/abs/2306.14795

<a id="source-S36"></a>
**[S36]** Geng, Z., Han, C., Hayder, Z., Liu, J., Shah, M., & Mian, A. (2024). Text-guided 3D Human Motion Generation with Keyframe-based Parallel Skip Transformer. *arXiv preprint arXiv:2405.15439*. https://arxiv.org/abs/2405.15439

<a id="source-S37"></a>
**[S37]** Wang, B., Wang, X., Ni, C., Zhao, G., Yang, Z., Zhu, Z., Zhang, M., Zhou, Y., Chen, X., Huang, G., Liu, L., & Wang, X. (2025). HumanDreamer: Generating Controllable Human-Motion Videos via Decoupled Generation. In *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 12391–12401. https://openaccess.thecvf.com/content/CVPR2025/html/Wang_HumanDreamer_Generating_Controllable_Human-Motion_Videos_via_Decoupled_Generation_CVPR_2025_paper.html · https://arxiv.org/abs/2503.24026

<a id="source-S38"></a>
**[S38]** Li, R., Xing, D., Sun, H., Ha, Y., Shen, J., & Ho, C. (2025). TokenMotion: Decoupled Motion Control via Token Disentanglement for Human-centric Video Generation. In *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 1951–1961. https://openaccess.thecvf.com/content/CVPR2025/html/Li_TokenMotion_Decoupled_Motion_Control_via_Token_Disentanglement_for_Human-centric_Video_CVPR_2025_paper.html

<a id="source-S39"></a>
**[S39]** He, H., Xu, Y., Guo, Y., Wetzstein, G., Dai, B., Li, H., & Yang, C. (2024). CameraCtrl: Enabling Camera Control for Text-to-Video Generation. *arXiv preprint arXiv:2404.02101*. https://arxiv.org/abs/2404.02101

<a id="source-S40"></a>
**[S40]** Shuai, X., Ding, H., Qin, Z., Luo, H., Ma, X., & Tao, D. (2025). Free-Form Motion Control: Controlling the 6D Poses of Camera and Objects in Video Generation. In *IEEE/CVF International Conference on Computer Vision (ICCV)*. https://arxiv.org/abs/2501.01425

<a id="source-S41"></a>
**[S41]** Wang, Z., Yuan, Z., Wang, X., Chen, T., Xia, M., Luo, P., & Shan, Y. (2024). MotionCtrl: A Unified and Flexible Motion Controller for Video Generation. In *ACM SIGGRAPH 2024 Conference Papers*. https://arxiv.org/abs/2312.03641

<a id="source-S42"></a>
**[S42]** Unterthiner, T., van Steenkiste, S., Kurach, K., Marinier, R., Michalski, M., & Gelly, S. (2018). Towards Accurate Generative Models of Video: A New Metric & Challenges. *arXiv preprint arXiv:1812.01717*. https://arxiv.org/abs/1812.01717

<a id="source-S44"></a>
**[S44]** Liu, J., Qu, Y., Yan, Q., Zeng, X., Wang, L., & Liao, R. (2024). Fréchet Video Motion Distance: A Metric for Evaluating Motion Consistency in Videos. *arXiv preprint arXiv:2407.16124*. https://arxiv.org/abs/2407.16124

<a id="source-S45"></a>
**[S45]** Feng, W., Li, J., Saxon, M., Fu, T.-J., Chen, W., & Wang, W. Y. (2024). TC-Bench: Benchmarking Temporal Compositionality in Text-to-Video and Image-to-Video Generation. *arXiv preprint arXiv:2406.08656*. https://arxiv.org/abs/2406.08656

<a id="source-S48"></a>
**[S48]** Bugliarello, E., Arnab, A., Paiss, R., Kindermans, P.-J., & Schmid, C. (2025). What Are You Doing? A Closer Look at Controllable Human Video Generation. *arXiv preprint arXiv:2503.04666*. https://arxiv.org/abs/2503.04666

<a id="source-S49"></a>
**[S49]** Zhang, J., Liu, J., Lee, Y.-Y., Moon, S., Zordan, V., Tevet, G., Liu, K., Gould, S., Jacob, O., Jiang, H., Kapadia, M., & Ben-Shabat, Y. (2026). RoMo: A Large-Scale, Richly Organized Dataset and Semantic Taxonomy for Human Motion Generation. In *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*. https://openaccess.thecvf.com/content/CVPR2026/html/Zhang_RoMo_A_Large-Scale_Richly_Organized_Dataset_and_Semantic_Taxonomy_for_CVPR_2026_paper.html · https://arxiv.org/abs/2605.26241

<a id="source-S50"></a>
**[S50]** Liao, T.-H., Zhou, Y., Shen, Y., Huang, C.-H. P., Mitra, S., Huang, J.-B., & Bhattacharya, U. (2025). Shape My Moves: Text-Driven Shape-Aware Synthesis of Human Motions. In *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 1917–1928. https://openaccess.thecvf.com/content/CVPR2025/html/Liao_Shape_My_Moves_Text-Driven_Shape-Aware_Synthesis_of_Human_Motions_CVPR_2025_paper.html · https://arxiv.org/abs/2504.03639


<a id="source-S51"></a>
**[S51]** Bray, T., Ed. (2017). The JavaScript Object Notation (JSON) Data Interchange Format. *RFC 8259; STD 90*. Internet Engineering Task Force. https://www.rfc-editor.org/rfc/rfc8259

<a id="source-S52"></a>
**[S52]** Bhutton, A., Wright, H., Andrews, H., & Hutton, B. (2022). JSON Schema: A Media Type for Describing JSON Documents; JSON Schema Validation: A Vocabulary for Structural Validation of JSON. *Draft 2020-12*. https://json-schema.org/draft/2020-12/json-schema-core · https://json-schema.org/draft/2020-12/json-schema-validation

<a id="source-S53"></a>
**[S53]** YAML Language Development Team. (2021). *YAML Ain’t Markup Language (YAML™), Revision 1.2.2*. https://yaml.org/spec/1.2.2/

<a id="source-S54"></a>
**[S54]** Bray, T., Paoli, J., Sperberg-McQueen, C. M., Maler, E., & Yergeau, F., Eds. (2008). *Extensible Markup Language (XML) 1.0, Fifth Edition*. W3C Recommendation. https://www.w3.org/TR/xml/

<a id="source-S55"></a>
**[S55]** Bray, T., Hollander, D., Layman, A., Tobin, R., & Thompson, H. S., Eds. (2009). *Namespaces in XML 1.0, Third Edition*. W3C Recommendation. https://www.w3.org/TR/xml-names/

<a id="source-S56"></a>
**[S56]** Gao, S., Sperberg-McQueen, C. M., & Thompson, H. S., Eds. (2012). *W3C XML Schema Definition Language (XSD) 1.1 Part 1: Structures*. W3C Recommendation. https://www.w3.org/TR/xmlschema11-1/

<a id="source-S57"></a>
**[S57]** Kay, M., Ed. (2017). *XSL Transformations (XSLT) Version 3.0*. W3C Recommendation. https://www.w3.org/TR/xslt-30/

<a id="source-S58"></a>
**[S58]** Bryan, P., Zyp, K., & Nottingham, M., Eds. (2013). JavaScript Object Notation (JSON) Pointer. *RFC 6901*. Internet Engineering Task Force. https://www.rfc-editor.org/rfc/rfc6901

<a id="source-S59"></a>
**[S59]** Bryan, P., & Nottingham, M., Eds. (2013). JavaScript Object Notation (JSON) Patch. *RFC 6902*. Internet Engineering Task Force. https://www.rfc-editor.org/rfc/rfc6902

<a id="source-S60"></a>
**[S60]** Hoffman, P., & Snell, J. (2014). JSON Merge Patch. *RFC 7396*. Internet Engineering Task Force. https://www.rfc-editor.org/rfc/rfc7396

<a id="source-S61"></a>
**[S61]** Rundgren, A., Jordan, B., & Erdtman, S. (2020). JSON Canonicalization Scheme (JCS). *RFC 8785*. Internet Engineering Task Force. https://www.rfc-editor.org/rfc/rfc8785

<a id="source-S62"></a>
**[S62]** OpenAI. (2026). *Video Generation with Sora*. OpenAI API documentation. Accessed July 18, 2026. The documentation marks Sora 2 and the Videos API as deprecated with shutdown scheduled for September 24, 2026. https://developers.openai.com/api/docs/guides/video-generation

<a id="source-S63"></a>
**[S63]** OpenAI. (2026). *Sora 2 Prompting Guide*. OpenAI Cookbook. Accessed July 18, 2026. https://developers.openai.com/cookbook/examples/sora/sora2_prompting_guide

<a id="source-S64"></a>
**[S64]** Google Cloud. (2026). *Generate Videos with Veo on Vertex AI Using First and Last Video Frames*. Google Cloud documentation, last updated January 2, 2026. https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/generate-videos-from-first-and-last-frames

<a id="source-S65"></a>
**[S65]** Runway. (2026). *API Getting Started Guide*. Runway Developer Documentation. Accessed July 18, 2026. https://docs.dev.runwayml.com/guides/using-the-api/

<a id="source-S66"></a>
**[S66]** Runway. (2026). *API Changelog & Updates*. Runway Developer Documentation. Accessed July 18, 2026. https://docs.dev.runwayml.com/api-details/api_changelog/

<a id="source-S67"></a>
**[S67]** Google AI for Developers. (2026). *Video Understanding: Gemini API*. Last updated July 6, 2026; accessed July 18, 2026. https://ai.google.dev/gemini-api/docs/video-understanding

<a id="source-S68"></a>
**[S68]** Google AI for Developers. (2026). *Structured Outputs: Gemini API*. Last updated July 7, 2026; accessed July 18, 2026. https://ai.google.dev/gemini-api/docs/structured-output

<a id="source-S69"></a>
**[S69]** Google Cloud. (2026). *VideoMetadata: Vertex AI Generative AI RPC Reference*. Accessed July 18, 2026. https://docs.cloud.google.com/vertex-ai/generative-ai/docs/reference/rpc/google.cloud.aiplatform.v1

<a id="source-S70"></a>
**[S70]** Google AI for Developers. (2026). *Embeddings: Multimodal Embeddings with Gemini Embedding 2*. Accessed July 18, 2026. https://ai.google.dev/gemini-api/docs/embeddings

<a id="source-S71"></a>
**[S71]** Twelve Labs. (2026). *Pegasus Model Documentation*. Version 1.3 documentation; accessed July 18, 2026. https://docs.twelvelabs.io/docs/concepts/models/pegasus

<a id="source-S72"></a>
**[S72]** Twelve Labs. (2026). *Segment Videos*. Version 1.3 documentation; accessed July 18, 2026. https://docs.twelvelabs.io/v1.3/docs/guides/segment-videos

<a id="source-S73"></a>
**[S73]** Twelve Labs. (2026). *Marengo Model Documentation*. Version 1.3 documentation; accessed July 18, 2026. https://docs.twelvelabs.io/docs/concepts/models/marengo

<a id="source-S74"></a>
**[S74]** Twelve Labs. (2026). *Release Notes*. Version 1.3 documentation; accessed July 18, 2026. https://docs.twelvelabs.io/docs/get-started/release-notes

<a id="source-S75"></a>
**[S75]** FFmpeg Project. (2026). *ffprobe Documentation*. Accessed July 18, 2026. https://ffmpeg.org/ffprobe.html

<a id="source-S76"></a>
**[S76]** PySceneDetect Contributors. (2026). *PySceneDetect Documentation*. Version 0.7 documentation; accessed July 18, 2026. https://www.scenedetect.com/docs/latest/

<a id="source-S77"></a>
**[S77]** Google Cloud. (2026). *Video Intelligence API Documentation*. Accessed July 18, 2026. https://docs.cloud.google.com/video-intelligence/docs

<a id="source-S78"></a>
**[S78]** Baltrušaitis, T., Zadeh, A., Lim, Y. C., & Morency, L.-P. (2018). OpenFace 2.0: Facial Behavior Analysis Toolkit. In *13th IEEE International Conference on Automatic Face & Gesture Recognition (FG 2018)*, 59–66. https://doi.org/10.1109/FG.2018.00019 · https://github.com/TadasBaltrusaitis/OpenFace

<a id="source-S79"></a>
**[S79]** Fang, H.-S., Li, J., Tang, H., Xu, C., Zhu, H., Xiu, Y., Li, Y.-L., & Lu, C. (2023). AlphaPose: Whole-Body Regional Multi-Person Pose Estimation and Tracking in Real-Time. *IEEE Transactions on Pattern Analysis and Machine Intelligence, 45*(6), 7157–7173. https://doi.org/10.1109/TPAMI.2022.3222784 · https://arxiv.org/abs/2211.03375

<a id="source-S80"></a>
**[S80]** Goel, S., Pavlakos, G., Rajasegaran, J., Kanazawa, A., & Malik, J. (2023). Humans in 4D: Reconstructing and Tracking Humans with Transformers. In *IEEE/CVF International Conference on Computer Vision (ICCV)*. https://arxiv.org/abs/2305.20091

<a id="source-S81"></a>
**[S81]** Zhao, Q., Liu, C., Gong, Z., Weng, J., Li, T., & Tan, P. (2024). Synergistic Global-Space Camera and Human Reconstruction from Videos. In *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*. https://research.adobe.com/publication/synergistic-global-space-camera-and-human-reconstruction-from-videos/

<a id="source-S82"></a>
**[S82]** Teed, Z., & Deng, J. (2020). RAFT: Recurrent All-Pairs Field Transforms for Optical Flow. In *European Conference on Computer Vision (ECCV)*. https://doi.org/10.1007/978-3-030-58536-5_24 · https://www.ecva.net/papers/eccv_2020/papers_ECCV/html/3526_ECCV_2020_paper.php

<a id="source-S83"></a>
**[S83]** Schönberger, J. L., & Frahm, J.-M. (2016). Structure-from-Motion Revisited. In *IEEE Conference on Computer Vision and Pattern Recognition (CVPR)*. COLMAP documentation: https://colmap.github.io/

<a id="source-S84"></a>
**[S84]** Souček, T., & Lokoč, J. (2020). TransNet V2: An Effective Deep Network Architecture for Fast Shot Transition Detection. *arXiv preprint arXiv:2008.04838*. https://arxiv.org/abs/2008.04838

<a id="source-S85"></a>
**[S85]** Huang, Q., Xiong, Y., Rao, A., Wang, J., & Lin, D. (2020). MovieNet: A Holistic Dataset for Movie Understanding. In *European Conference on Computer Vision (ECCV)*. https://doi.org/10.1007/978-3-030-58548-8_41 · https://movienet.github.io/projects/eccv20movienet.html

<a id="source-S86"></a>
**[S86]** Rao, A., Xu, L., Xiong, Y., Xu, G., Huang, Q., Zhou, B., & Lin, D. (2020). A Local-to-Global Approach to Multi-Modal Movie Scene Segmentation. In *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*. https://arxiv.org/abs/2004.02678

<a id="source-S87"></a>
**[S87]** Yi, F., Wen, H., & Jiang, T. (2021). ASFormer: Transformer for Action Segmentation. In *British Machine Vision Conference (BMVC)*. https://doi.org/10.5244/C.35.49 · https://bmva-archive.org.uk/bmvc/2021/conference/papers/paper_0183.html

<a id="source-S88"></a>
**[S88]** Zhang, C.-L., Wu, J., & Li, Y. (2022). ActionFormer: Localizing Moments of Actions with Transformers. In *European Conference on Computer Vision (ECCV)*. https://doi.org/10.1007/978-3-031-19772-7_29 · https://www.ecva.net/papers/eccv_2022/papers_ECCV/html/7278_ECCV_2022_paper.php

<a id="source-S89"></a>
**[S89]** Radford, A., Kim, J. W., Xu, T., Brockman, G., McLeavey, C., & Sutskever, I. (2022). Robust Speech Recognition via Large-Scale Weak Supervision. *arXiv preprint arXiv:2212.04356*. https://arxiv.org/abs/2212.04356 · https://github.com/openai/whisper

<a id="source-S90"></a>
**[S90]** Grauman, K., Westbury, A., Torresani, L., et al. (2024). Ego-Exo4D: Understanding Skilled Human Activity from First- and Third-Person Perspectives. In *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, 19383–19400. https://openaccess.thecvf.com/content/CVPR2024/html/Grauman_Ego-Exo4D_Understanding_Skilled_Human_Activity_from_First-_and_Third-Person_Perspectives_CVPR_2024_paper.html

<a id="source-S91"></a>
**[S91]** Chong, E., Ruiz, N., Wang, Y., Zhang, Y., Rozga, A., & Rehg, J. M. (2020). Detecting Attended Visual Targets in Video. In *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*. https://doi.org/10.1109/CVPR42600.2020.00544

<a id="source-S92"></a>
**[S92]** Academy Software Foundation. (2026). *OpenTimelineIO Documentation*. Accessed July 18, 2026. https://opentimelineio.readthedocs.io/en/latest/

---

<a id="cpcs-change-log"></a>
# Document Change Log

| Version | Date | Changes |
|---|---:|---|
| 1.2 | 2026-07-18 | Added reference-video distillation and reverse directorial compilation; temporal-pyramid analysis; measured/detected/inferred/interpreted/authored evidence classes; Video Observation Graph; Gemini, Pegasus, Marengo, media-forensic, shot, face, gaze, pose, optical-flow, 3D reconstruction, audio, action/contact, camera/edit, VFX, UGC, and marketing extraction roles; fight and UGC reverse-engineering workflows; identity-independent normalization; provider capability pinning; round-trip verification; Appendix H operational reference; schemas, scripts, prompts, fixtures, and reproducible package validation. |
| 1.1 | 2026-07-18 | Added production control taxonomy for FACS, Laban, combat/action, director/editorial, VFX/anime, audio, and marketing layers; complete YAML/JSON/XML/JSONL role theory; authoring-source, canonical-IR, target-package, and evidence architecture; typed style inheritance and merge precedence; cross-format schema composition; capability negotiation; current official adapter examples; security and deterministic verification; Appendix G compiler reference; expanded RAG corpus and bibliography. |
| 1.0 | 2026-07-18 | Initial research synthesis; CPCS formalism; compiler architecture; conditioning strategies; schemas; dialogue, locomotion, and fight examples; evaluation framework; RAG protocol; source-indexed bibliography. |

