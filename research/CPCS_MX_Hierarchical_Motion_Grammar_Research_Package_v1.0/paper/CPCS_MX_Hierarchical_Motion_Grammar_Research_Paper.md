---
title: "CPCS-MX: A Hierarchical Motion Grammar for Exact, Expressive, and Superhuman Character Performance"
subtitle: "Biomechanics, Laban/FACS integration, action and contact dynamics, retargeting, procedural animation, and agent-readable compilation for AI video generation"
author: "OpenAI research synthesis"
version: "1.0.0"
date: "2026-07-19"
document_id: "cpcs-mx-research-v1"
artifact_type: "standalone research monograph"
language: "en"
ragsafe: true
canonical_citation_style: "stable source identifiers [S001]-[S080]"
status_labels:
  - ESTABLISHED
  - CURRENT_PLATFORM
  - CURRENT_RESEARCH
  - EMERGING
  - PROPOSED
  - OPERATIONALIZATION
scope:
  - human movement representation
  - expressive performance notation
  - stylized and superhuman virtual motion
  - text-to-structured motion compilation
  - AI video and character animation control
  - agent and RAG ingestion
---

# CPCS-MX: A Hierarchical Motion Grammar for Exact, Expressive, and Superhuman Character Performance

## Abstract

This monograph proposes **CPCS-MX**, a standalone extension of the Cinematic Performance Control Score concept for representing, compiling, generating, retargeting, and verifying exact or deliberately stylized character movement. The system combines time-based root motion, skeletal joint tracks, contact and support events, phase signals, kinematic and kinetic estimates, Laban Body–Effort–Shape–Space descriptors, FACS-like facial tracks, gaze, breath, mannerisms, secondary motion, virtual physics, camera presentation, and explicit hard, soft, and perceptual constraints. Its central thesis is that high-fidelity movement cannot be reduced to a text prompt, a pose sequence, a physics simulation, or an expressive label in isolation. It must be represented as a **layered performance program** whose fields have declared semantics, coordinate systems, units, evidence status, merge behavior, and model-specific compilation targets.

The research distinguishes established biomechanics and animation concepts from proposed CPCS-MX engineering conventions. It also distinguishes four meanings of “exact”: exact with respect to source timestamps, exact screen-space trajectories, exact rig-space kinematics, and exact physical dynamics. A monocular video may support the first two while leaving three-dimensional depth, forces, torques, and hidden contacts underdetermined. Consequently, CPCS-MX stores measured, detected, inferred, interpreted, and authored values separately rather than promoting every plausible estimate to ground truth.

For AI video generation, the score is not treated as machine code. JSON is the canonical intermediate representation; YAML is the human authoring and override layer; JSONL is the appendable evidence, event, and evaluation stream; dense motion arrays or control videos carry frame-level geometry; and target adapters compile the resolved score into the controls a model actually supports. The architecture enables naturalistic UGC movement, feature-animation polish, anime or sakuga timing, staged combat, and virtual superhuman motion to share a common causal skeleton while varying performance and stylization through constrained transformation layers.

**Research status.** Biomechanics, inverse kinematics, inverse dynamics, motion phases, retargeting, FACS, Laban-related analysis, and many cited motion-generation methods are established or active research areas. **CPCS-MX is a proposed synthesis and schema**, not an international standard, medical tool, combat-training system, or guarantee of exact compliance by a generative video model.

## How to use this document

The paper is designed for both continuous reading and retrieval-augmented generation. Every major section begins with a stable `RAG_CHUNK` marker. Source claims use stable identifiers such as `[S008]`, resolved in the package reference index. Terms including **hard constraint**, **measured**, **inferred**, **style transform**, and **superhuman** have explicit definitions. Agents should retrieve the relevant conceptual section together with the schema field guide and source records rather than treating isolated numerical examples as universal human constants.

## Table of contents

1. [Research problem and contributions](#1-research-problem-and-contributions)
2. [Evidence and claim taxonomy](#2-evidence-and-claim-taxonomy)
3. [The CPCS-MX layered architecture](#3-the-cpcs-mx-layered-architecture)
4. [Time, clocks, units, and coordinate systems](#4-time-clocks-units-and-coordinate-systems)
5. [Skeleton topology, degrees of freedom, and joint limits](#5-skeleton-topology-degrees-of-freedom-and-joint-limits)
6. [Root motion and locomotor organization](#6-root-motion-and-locomotor-organization)
7. [Joint tracks, rotation representations, and interpolation](#7-joint-tracks-rotation-representations-and-interpolation)
8. [Kinematics, kinetics, momentum, and inverse dynamics](#8-kinematics-kinetics-momentum-and-inverse-dynamics)
9. [Inverse kinematics, retargeting, and morphology](#9-inverse-kinematics-retargeting-and-morphology)
10. [Motion phases, contacts, and action graphs](#10-motion-phases-contacts-and-action-graphs)
11. [Hard, soft, and perceptual constraints](#11-hard-soft-and-perceptual-constraints)
12. [Laban Body–Effort–Shape–Space as a control layer](#12-laban-bodyeffortshapespace-as-a-control-layer)
13. [Effort phrasing, Shape change, and computational proxies](#13-effort-phrasing-shape-change-and-computational-proxies)
14. [FACS, face, gaze, breath, and upper-body synchronization](#14-facs-face-gaze-breath-and-upper-body-synchronization)
15. [Mannerisms, postural tone, and movement signatures](#15-mannerisms-postural-tone-and-movement-signatures)
16. [Natural movement and high-fidelity UGC](#16-natural-movement-and-high-fidelity-ugc)
17. [Staged combat and multi-actor action coding](#17-staged-combat-and-multi-actor-action-coding)
18. [Anime, sakuga, limited animation, and cartoon physics](#18-anime-sakuga-limited-animation-and-cartoon-physics)
19. [Superhuman motion as constrained transformation](#19-superhuman-motion-as-constrained-transformation)
20. [Secondary and overlapping motion](#20-secondary-and-overlapping-motion)
21. [BVH, FBX, dense arrays, and canonical interchange](#21-bvh-fbx-dense-arrays-and-canonical-interchange)
22. [Procedural animation, motion matching, and engine execution](#22-procedural-animation-motion-matching-and-engine-execution)
23. [AI motion synthesis and controllable video generation](#23-ai-motion-synthesis-and-controllable-video-generation)
24. [Text-to-CPCS-MX compilation](#24-text-to-cpcs-mx-compilation)
25. [Canonical schema design](#25-canonical-schema-design)
26. [Constraint resolution and compilation](#26-constraint-resolution-and-compilation)
27. [Verification and perceptual evaluation](#27-verification-and-perceptual-evaluation)
28. [Cross-style modular switching](#28-cross-style-modular-switching)
29. [Agent architecture and RAG ingestion](#29-agent-architecture-and-rag-ingestion)
30. [Experimental program](#30-experimental-program)
31. [Limitations, rights, safety, and ethics](#31-limitations-rights-safety-and-ethics)
32. [Conclusions](#32-conclusions)
33. [Appendix A — CPCS-MX field dictionary](#appendix-a--cpcs-mx-field-dictionary)
34. [Appendix B — canonical JSON example](#appendix-b--canonical-json-example)
35. [Appendix C — YAML authoring example](#appendix-c--yaml-authoring-example)
36. [Appendix D — validation checklist](#appendix-d--validation-checklist)
37. [Appendix E — glossary](#appendix-e--glossary)

<!-- RAG_CHUNK id="cpcs-mx-01" title="Research problem and contributions" concepts="CPCS-MX, exact motion, AI video control, layered performance score" evidence="PROPOSED,ESTABLISHED" -->
<a id="1-research-problem-and-contributions"></a>
## 1. Research problem and contributions

### 1.1 The control gap

A conventional text-to-video prompt can state that a character walks, runs, pivots, strikes, recoils, smiles, or looks frightened. It usually cannot state—at an enforceable level—where the pelvis is at every source time, which foot is supporting the body, when a hand reaches a target, how the torso and shoulder phases overlap, whether the apparent contact is real or staged, how long the recovery lasts, how gaze leads the action, or how an effect frame alters the visual motion without altering the underlying choreography. The prompt is semantic; the desired performance is spatiotemporal and causal.

Traditional animation systems solve parts of this problem with keyframes, curves, inverse kinematics, motion capture, retargeting, motion matching, dynamics, and artist review. Biomechanics provides coordinate systems, joint models, inverse kinematics, inverse dynamics, ground-reaction analysis, and quantitative error measures. Laban-related systems provide language for movement organization and qualitative dynamics. FACS decomposes visible facial movement into Action Units. Contemporary motion-generation research adds text conditioning, diffusion priors, joint-level spatial guidance, contact-guided interaction, event-level alignment, and camera or trajectory controls. These bodies of work are complementary, but their control variables are rarely unified in one agent-readable score. [S001][S002][S008][S009][S031][S051][S054][S058]

CPCS-MX addresses that gap as an intermediate representation. It is intended to sit between three domains:

1. **Human or machine observation:** motion capture, pose estimation, video analysis, animator notation, or director instruction.
2. **Performance authoring:** natural language, YAML profiles, editable curves, event graphs, constraints, and style transformations.
3. **Execution:** a game engine, DCC rig, physics controller, text-to-motion model, pose-conditioned video generator, image-to-video model, or compositor.

### 1.2 What “exact” can mean

The word *exact* is often used without specifying the reference space. CPCS-MX requires the target of exactness to be declared.

- **Clock exactness:** events occur on the intended frame or source presentation timestamp.
- **Screen-space exactness:** visible landmarks, silhouettes, objects, and contacts follow intended image-plane paths.
- **Rig-space exactness:** a defined skeleton follows intended root transforms and joint rotations.
- **world-space exactness:** actors and props follow intended three-dimensional trajectories relative to a scene coordinate frame.
- **dynamic exactness:** masses, forces, torques, impulses, contact responses, and momentum match a defined physical model.
- **perceptual exactness:** the audience reads the intended action, emotion, weight, and causal event even when geometric paths differ.

A single monocular video can strongly constrain clock and screen-space behavior while leaving depth, hidden limbs, forces, and torques ambiguous. Conversely, a motion-capture file may provide rig-space trajectories but omit facial behavior, camera presentation, or the visual exaggerations that make a shot readable. Exactness is therefore a vector of compliance dimensions, not a single score.

### 1.3 Contributions of this monograph

The paper contributes:

- a layered model separating intent, action identity, kinematics, dynamics, expression, mannerism, stylization, and presentation;
- a time-based canonical schema with root, joint, phase, contact, Laban, FACS, gaze, breath, and secondary-motion tracks;
- a formal distinction between hard, soft, perceptual, and stylistic constraints;
- a superhuman transformation model that preserves declared invariants rather than multiplying every physical quantity indiscriminately;
- a modular cross-style system for photoreal human, UGC, feature animation, anime, and virtual superhuman motion;
- a compilation architecture from text and YAML into canonical JSON, dense control media, and target-specific adapters;
- a verification framework that compares generated motion against the same score used to direct it;
- an RAG packaging model for agent retrieval, source provenance, and deterministic validation.

The key design principle is **separation before composition**. A contact event is not a camera shake. A strong Laban Weight quality is not a measured force. A negative affect state is not a guaranteed FACS configuration. A fast screen-space smear is not necessarily a physically fast limb. A superhuman visual deformation is not automatically an expanded human joint limit. Once these distinctions are retained, the layers can be combined deliberately rather than conflated by a large prompt.

<!-- RAG_CHUNK id="cpcs-mx-02" title="Evidence and claim taxonomy" concepts="provenance, measured, detected, inferred, authored, evidence status" evidence="PROPOSED" -->
<a id="2-evidence-and-claim-taxonomy"></a>
## 2. Evidence and claim taxonomy

CPCS-MX is intended for systems in which values may originate from instruments, computer vision, multimodal models, artists, directors, or simulations. Those sources do not have equal epistemic status. A high-confidence language-model description remains an interpretation; a joint coordinate reconstructed from monocular video remains model-dependent; a force vector inferred without measured external loads is not a measured force. OpenSim’s inverse-dynamics workflow, for example, requires kinematics, inertial properties, and external loads to compute net joint forces and moments; missing or inconsistent inputs produce residuals and modeling error. [S002][S005]

### 2.1 Evidence classes

Every CPCS-MX observation or authored value should carry one of the following classes:

| Evidence class | Meaning | Example |
|---|---|---|
| `measured` | Directly computed from a calibrated sensor or source clock under a declared method | force-plate vertical GRF; source PTS; mocap marker position |
| `detected` | Output of a detector operating on observed media | 2D wrist landmark; blink candidate; foreground mask |
| `inferred` | Estimate derived by a model from incomplete evidence | 3D pose from monocular video; probable foot contact; camera translation |
| `interpreted` | Semantic or expressive reading | “bound flow”; “concealed fear”; “reaction beat” |
| `authored` | Deliberate creative value | contact moved to frame 72; gravity scale set to 0.65 |
| `simulated` | Result of a declared virtual model | rigid-body impulse; cloth trajectory; virtual joint torque |
| `derived` | Deterministic calculation from other records | velocity from filtered position; jerk metric; phase estimate |

A record should also store extractor name and version, source asset hash, timestamp or frame range, confidence where meaningful, alternatives, review status, and supersession relationships. Confidence does not replace evidence class. A measured but poorly calibrated sensor can be wrong; an interpreted label can be useful without being ground truth.

### 2.2 Research-status labels

Claims in this paper use a second taxonomy:

- **ESTABLISHED:** supported by mature scientific, technical, or professional practice.
- **CURRENT_PLATFORM:** behavior documented by a current engine or tool and therefore version-dependent.
- **CURRENT_RESEARCH:** recent peer-reviewed work that may not yet be production-standard.
- **EMERGING:** preprint or early research requiring replication or engineering validation.
- **PROPOSED:** a CPCS-MX schema or conceptual contribution.
- **OPERATIONALIZATION:** an engineering mapping from a qualitative concept to data fields or metrics; useful but not identical to the underlying theory.

For example, Laban Effort categories are established movement-analysis concepts. Mapping `direct Space` to a normalized path-curvature threshold is an operationalization. The mapping may be calibrated for a project, but it should not be presented as the universal definition of directness.

### 2.3 Provenance and conflict resolution

Each value can retain a provenance chain:

```text
source video frame
→ pose detector candidate
→ temporal smoother
→ human correction
→ retarget solver
→ generated control video
→ generated-video re-extraction
```

When sources conflict, CPCS-MX does not silently average them. It applies declared authority and locks. A reviewed frame-level contact can supersede a multimodal interpretation. A director can author a different contact frame, but the change should be recorded as a creative override rather than rewriting the source observation. A physically infeasible authored pose can remain in the score as a target, while the compiler emits an infeasibility report and either requests a stylized deformation layer or relaxes a named soft constraint.

### 2.4 Why this matters for agents

An agent retrieving a sentence such as “increase punch force by 1.5×” must know whether the number is a measured sports value, a simulated virtual impulse, a stylization scalar, or an unsafe instruction for a real performer. RAG records therefore include evidence labels, domain tags, and safety scope. Agent prompts should require citations to source identifiers and should prohibit converting virtual parameters into real-world human performance instructions without a separate safety review.

<!-- RAG_CHUNK id="cpcs-mx-03" title="The CPCS-MX layered architecture" concepts="hierarchical motion grammar, layers, intent, action, execution, presentation" evidence="PROPOSED" -->
<a id="3-the-cpcs-mx-layered-architecture"></a>
## 3. The CPCS-MX layered architecture

CPCS-MX models performance as a hierarchy of coupled but independently inspectable layers. The architecture is designed to answer a diagnostic question: when a generated clip fails, was the failure semantic, temporal, kinematic, dynamic, expressive, stylistic, or presentational?

### 3.1 Layer stack

| Layer | Primary question | Representative controls |
|---|---|---|
| Intent | Why is the character moving? | objective, tactic, obstacle, subtext |
| Action graph | What causal actions occur? | step, pivot, reach, dodge, recoil, fall, recover |
| Phase | When is each component active? | preparation, initiation, contact, follow-through, reset |
| Root and balance | Where is the body as a whole? | pelvis trajectory, facing, support polygon, COM proxy |
| Joint kinematics | How do segments articulate? | rotations, positions, velocities, accelerations |
| Contact and interaction | What touches or constrains what? | support, grasp, near-contact, prop contact, impact event |
| Dynamics | What virtual physical explanation is used? | mass, impulse, torque estimate, gravity, damping |
| Laban/BESS | What movement quality and shaping are perceived? | Weight, Time, Space, Flow, Shape change |
| Face and affect | What visible and internal performance cues evolve? | FACS-like AU curves, VAD/VAC, gaze, head, blink |
| Mannerism | What makes the movement character-specific? | guard preference, asymmetry, fidget, habitual timing |
| Secondary motion | What follows the primary skeleton? | hair, cloth, soft tissue, accessories, debris |
| Stylization | How is motion transformed by genre? | holds, smears, exaggeration, time warp, deformation |
| Presentation | How does the audience see it? | camera, lens, framing, edit, slow motion, impact frame |
| Verification | How is compliance tested? | contact error, trajectory error, foot slip, readability |

### 3.2 Modular composition

A movement module is not a finished clip. It is a reusable partial specification with declared inputs, outputs, preconditions, postconditions, and editable parameters. A `step_in` module may require a supporting stance, produce a forward root displacement, change support state, and expose timing parameters. A `strike_like_extension` module may begin after a pelvis or torso initiation, target a screen-space or world-space region, and terminate in staged near-contact. A `recoil` module consumes an impact event and produces root displacement, head delay, upper-body response, and recovery.

Modules are composed through event and constraint edges rather than by concatenating prose. This is analogous to music orchestration: individual lines have their own timing and expression but are synchronized through a score. Local Motion Phases demonstrate why complex movement benefits from multiple phase signals rather than a single global phase; different bones can have asynchronous rhythms and contacts. [S009]

### 3.3 Primary versus derived tracks

CPCS-MX differentiates **authoritative tracks** from **derived tracks**. If root position is authoritative, velocity and acceleration are calculated from it under a specified filter and differentiation method. If velocity is authored as authoritative, the compiler integrates it and then verifies positional constraints. Maintaining two incompatible authoritative versions of the same quantity creates an overconstrained system.

A recommended authority order is:

```text
locked event timing
→ locked contacts and support
→ locked root trajectory
→ locked key joint targets
→ style and expressive fields
→ generated in-betweens
→ secondary simulation
```

This order is configurable. A physics-first workflow may instead lock masses and contacts and allow the root path to emerge. A screen-space anime recreation may lock silhouettes and key drawings while allowing the hidden 3D rig to deviate.

### 3.4 Control versus presentation

CPCS-MX deliberately separates **staged-world motion** from **rendered-image motion**. Camera shake, zoom, motion blur, speed lines, and smear drawings can make an action appear faster or stronger without changing the underlying joint trajectory. Conversely, a physically fast action can be unreadable if the camera crosses the axis or the silhouette collapses. The compiler therefore emits both a performance package and a presentation package, with explicit dependencies between them.

<!-- RAG_CHUNK id="cpcs-mx-04" title="Time, clocks, units, and coordinate systems" concepts="timebase, PTS, frames, coordinate frames, units, synchronization" evidence="ESTABLISHED,PROPOSED" -->
<a id="4-time-clocks-units-and-coordinate-systems"></a>
## 4. Time, clocks, units, and coordinate systems

Precision begins with a clock. Frame numbers alone are insufficient when the source is variable-frame-rate, retimed, or edited from multiple streams. CPCS-MX stores a canonical time in seconds or rational media time, then permits frame indices as views derived from a declared frame rate.

### 4.1 Time representation

A project declares:

```json
{
  "timebase": {
    "canonical": "seconds",
    "fps": {"numerator": 24000, "denominator": 1001},
    "source_clock": "presentation_timestamp",
    "sample_rate_hz": 120,
    "rounding": "nearest_source_frame"
  }
}
```

Events should carry both a time and, when relevant, a source-frame identifier. Time intervals use half-open semantics—`[start, end)`—unless explicitly declared otherwise. Curves state their interpolation method and sampling domain. A one-frame impact drawing at 24 fps is not equivalent to a 41.67 ms continuous event if the target renderer performs motion interpolation; the score must state whether the frame is a held drawing, an exposure, or a sample in a continuous trajectory.

### 4.2 Coordinate frames

At minimum, the score distinguishes:

- **world frame:** scene-level coordinates;
- **character root frame:** orientation and translation of the character controller;
- **pelvis or body frame:** anatomical or rig-centered reference;
- **joint local frame:** child transform relative to parent;
- **camera frame:** coordinates relative to the optical center;
- **screen frame:** normalized image coordinates;
- **object frame:** prop-relative coordinates;
- **contact frame:** local tangent, normal, and binormal at an interaction surface.

Every vector requires a frame. `force: [0, 500, 0]` is meaningless without units, coordinate axes, point of application, and whether it is measured, inferred, or simulated. ISB reporting recommendations emphasize the importance of coordinate system, perspective, normalization, and sign conventions for forces and moments. [S005]

### 4.3 Units and normalization

CPCS-MX uses SI units internally by default: meters, seconds, kilograms, Newtons, Newton-meters, radians, and radians per second. Screen-space coordinates can be normalized to `[0,1]`, but the schema must identify the image dimensions and origin convention. Laban values, affect values, style intensities, and confidence values are dimensionless and require declared ranges.

Normalized values should not erase physical values. A `root_speed_norm: 0.8` can be useful to a learned model, but the canonical record should retain the scale used to compute it. Similarly, a joint’s normalized range should reference a rig-specific minimum and maximum rather than implying universal anatomy.

### 4.4 Synchronization across modalities

Motion, audio, face, camera, and VFX often have different sampling rates. The system retains source clocks and defines synchronization transforms. An impact may have:

- visual near-contact at `t = 2.4167 s`;
- one-frame flash at the same exposure;
- camera shake beginning 8 ms later;
- impact sound onset 20 ms later;
- facial tightening reaching an apex 100 ms later.

These are separate events with causal links, not one overloaded timestamp. The schema permits offsets and uncertainty intervals. When timing is inferred from compressed video, the record should include the temporal resolution and confidence instead of reporting false precision.

<!-- RAG_CHUNK id="cpcs-mx-05" title="Skeleton topology, degrees of freedom, and joint limits" concepts="skeleton, DoF, joint limits, anatomy, stylized deformation" evidence="ESTABLISHED,PROPOSED" -->
<a id="5-skeleton-topology-degrees-of-freedom-and-joint-limits"></a>
## 5. Skeleton topology, degrees of freedom, and joint limits

A skeletal track is meaningful only relative to a declared topology and rest configuration. Two characters can both have a joint called `shoulder_r` while differing in parent hierarchy, local axes, rest orientation, segment length, twist distribution, and degrees of freedom. Motion retargeting research exists precisely because copying rotations between non-identical skeletons produces semantic and geometric failures. [S016][S017][S018]

### 5.1 Skeleton declaration

The schema stores:

- stable joint identifiers and parent relationships;
- rest transforms;
- local coordinate axes;
- rotational and translational degrees of freedom;
- segment lengths and optional mass/inertia estimates;
- skinning or deformation references;
- semantic regions such as hand, forearm, torso, head, and support foot;
- retarget chains and end effectors;
- joint limits and preferred angles;
- virtual or stylized deformation controls that are not skeletal joints.

A compact example:

```json
{
  "joint_id": "elbow_r",
  "parent": "upper_arm_r",
  "dof": ["flexion_extension", "pronation_supination_proxy"],
  "rotation_representation": "quaternion_xyzw",
  "limits": {
    "mode": "rig_specific",
    "flexion_extension_rad": [-0.05, 2.62],
    "soft_margin_rad": 0.12
  },
  "preferred_angle_rad": 0.35
}
```

The numerical range above is illustrative, not a universal clinical range. Human range of motion varies by subject, joint definition, measurement method, activity, and pathology. A production rig may intentionally use different limits.

### 5.2 Anatomical, rig, and virtual limits

CPCS-MX defines three limit domains:

1. **Anatomical limits:** evidence-based ranges for a particular human model or performer.
2. **Rig limits:** what a production skeleton and skinning system can support without unacceptable deformation.
3. **virtual stylization limits:** deliberate nonhuman deformation, often implemented by squash/stretch, lattice deformation, blendshapes, segment scaling, or key-shape interpolation.

This separation corrects a common but unsafe simplification: “increase human joint range by 30% for superhuman motion.” Directly extending an anatomical elbow, knee, or spine limit can produce visually broken or injury-like poses and, if translated into live performance, dangerous guidance. In CPCS-MX, a photoreal human rig keeps anatomical or rig limits. A stylized character may exceed the visible human silhouette through a separate deformation layer while the underlying skeleton remains within declared limits, or may declare itself a nonhuman virtual skeleton with its own limits.

### 5.3 Degrees of freedom and coupled constraints

Not all joints are independent ball joints. OpenSim models can define coordinate couplers, point constraints, and weld constraints, allowing one generalized coordinate to depend on another. [S003] CPCS-MX can represent coupled constraints such as scapular rhythm, patellar motion proxies, twist distribution along a forearm, or a locked prop grip. These constraints should be implemented in the solver or retarget adapter, not merely documented as prose.

### 5.4 Rest pose and topology versioning

A canonical motion file must reference a skeleton version and rest-pose hash. Changing a rest pose can alter every local rotation while leaving the visible pose similar. For agent workflows, skeleton metadata is retrieved with the motion chunk. Dense joint data without topology is treated as incomplete.

<!-- RAG_CHUNK id="cpcs-mx-06" title="Root motion and locomotor organization" concepts="root motion, pelvis trajectory, locomotion, center of mass, trajectory" evidence="ESTABLISHED,PROPOSED" -->
<a id="6-root-motion-and-locomotor-organization"></a>
## 6. Root motion and locomotor organization

Root motion describes the global translation and orientation that moves a character through the scene. It should not be confused with pelvis motion, center-of-mass motion, or a camera-relative image trajectory. Unity and Unreal both distinguish animation-root behavior from local joint animation and provide workflows for extracting or applying root motion. [S012][S014]

### 6.1 Root-track fields

A root track can contain:

```json
{
  "root_track": {
    "frame": "world",
    "position_m": [[0.0,0.0,0.0],[0.02,0.0,0.01]],
    "orientation": {"representation":"quaternion_xyzw","samples":[[0,0,0,1],[0,0.01,0,0.99995]]},
    "linear_velocity_mps": {"derived_from":"position_m"},
    "angular_velocity_radps": {"derived_from":"orientation"},
    "facing_target": "actor_b",
    "trajectory_constraints": ["stay_inside_stage_zone_A"]
  }
}
```

For locomotion, the root track encodes path and heading, while joint tracks encode gait style and contact execution. A character can follow the same root path with different cadence, step width, posture, arm swing, Laban qualities, and mannerisms.

### 6.2 Root motion versus center of mass

The root is a control convention. The center of mass is a mass-weighted physical quantity. They may coincide approximately but should not be assumed identical. A stylized leap can keep a smooth root arc while the character’s changing pose moves the actual center of mass relative to the pelvis. A physically informed workflow can store a COM track derived from segment masses and positions, together with support-polygon and balance margins.

### 6.3 Locomotor phase

Cyclic locomotion benefits from a phase variable. PFNN conditions character control on phase, trajectory, and environmental data to produce responsive locomotion over terrain. [S008] The CPCS-MX root layer therefore allows global phase, but it does not force all action into one cycle. Running, turning, carrying, climbing, or combat footwork may require local phases for feet, pelvis, torso, and hands. [S009]

### 6.4 Root trajectory constraints

Common constraints include:

- start and end transforms;
- target arrival time;
- corridor or navigation region;
- maximum curvature;
- speed and acceleration bounds;
- facing and gaze relationships;
- foot-contact consistency;
- camera framing compatibility;
- collision avoidance;
- scene affordances such as stairs or ledges.

A root path should not be “corrected” independently after joint generation if doing so causes planted feet to slide. Any root edit triggers contact-aware re-solving of the lower body.

### 6.5 Natural imperfection

High-fidelity UGC should not use a perfectly uniform root trajectory unless the performance demands it. Human motion includes small speed fluctuations, corrections, asymmetric step lengths, and postural adjustments. These should be generated as correlated, task-aware variation—not white noise. Random jitter added independently to every frame produces vibration, not naturalism. The score stores a low-frequency variation process, limits, and seed so that the result is reproducible.

<!-- RAG_CHUNK id="cpcs-mx-07" title="Joint tracks, rotation representations, and interpolation" concepts="joint tracks, rotations, quaternions, 6D rotations, interpolation, continuity" evidence="ESTABLISHED,PROPOSED" -->
<a id="7-joint-tracks-rotation-representations-and-interpolation"></a>
## 7. Joint tracks, rotation representations, and interpolation

### 7.1 Representation choices

Euler angles are readable but susceptible to axis-order ambiguity, wrapping, and gimbal singularities. Quaternions are compact and support spherical interpolation, but their double-cover property requires sign consistency. Neural networks trained in ordinary Euclidean output spaces can benefit from continuous 5D or 6D rotation representations, which avoid discontinuities associated with lower-dimensional representations in that setting. [S006] QuaterNet demonstrates a quaternion-based motion model and the value of forward-kinematics losses that penalize positional consequences of rotation errors. [S007]

CPCS-MX therefore permits multiple representations but requires one canonical representation per track and explicit conversion metadata. Recommended choices are:

- quaternions for interchange and rig playback;
- 6D continuous rotations for neural-model interfaces;
- exponential maps or axis-angle for local edits with bounded magnitudes;
- Euler channels only when required by a source format, with axis order and unwrapping declared.

### 7.2 Sparse keys and dense samples

A joint track may be:

- sparse keyframes plus interpolation;
- dense samples at a fixed rate;
- a procedural function;
- a reference to an external binary array;
- a constraint-only track solved at compile time.

Large arrays should not be embedded directly in a human-edited JSON document. The canonical score can reference an `.npz`, Arrow, Parquet, glTF animation, BVH, or FBX asset by URI and hash while retaining semantic events and constraints in JSON.

### 7.3 Continuity classes

Smoothness should be specified according to the task:

- `C0`: positional continuity; no teleportation.
- `C1`: velocity continuity; no instantaneous velocity jump.
- `C2`: acceleration continuity; smoother force implication.
- deliberate discontinuity: impact frame, held drawing, teleport, stylized snap.

A physically plausible joint path often benefits from at least velocity continuity, but animation may intentionally use sharp timing changes. The score therefore marks discontinuities as authored events rather than allowing a smoothing filter to erase them.

### 7.4 Derivatives and filtering

Velocity, acceleration, and jerk amplify noise. The score records:

- filter type and parameters;
- derivative method;
- source sample rate;
- boundary handling;
- whether derivatives are authoritative or derived.

This is essential when comparing outputs. Two systems can report different peak acceleration from the same positional samples because of smoothing and finite-difference choices.

### 7.5 Joint chains and arcs

Human and stylized movement is often judged by end-effector arcs rather than individual joint curves. CPCS-MX can store both local joint tracks and derived world-space paths for hands, feet, head, weapon tips, or gaze targets. A hard screen-space fist arc can coexist with soft elbow and shoulder preferences, allowing IK to find a coherent solution.

<!-- RAG_CHUNK id="cpcs-mx-08" title="Kinematics, kinetics, momentum, and inverse dynamics" concepts="kinematics, kinetics, force, torque, impulse, momentum, inverse dynamics" evidence="ESTABLISHED,PROPOSED" -->
<a id="8-kinematics-kinetics-momentum-and-inverse-dynamics"></a>
## 8. Kinematics, kinetics, momentum, and inverse dynamics

Kinematics describes motion without specifying the forces that cause it. Kinetics concerns forces, torques, impulses, and mass-dependent dynamics. Conflating them causes false precision. A video can show a hand moving rapidly; it does not directly reveal the applied joint torque or impact force without a model and additional measurements.

### 8.1 Kinematic tracks

CPCS-MX can store or derive:

- position and orientation;
- linear and angular velocity;
- linear and angular acceleration;
- jerk;
- path curvature and torsion;
- joint range and excursion;
- intersegmental timing;
- center-of-mass and center-of-pressure proxies.

### 8.2 Kinetic and dynamic fields

Optional fields include:

- segment mass and inertia;
- gravity vector;
- external force and torque with point of application;
- contact impulse and duration;
- joint torque estimates;
- damping, compliance, restitution, and friction;
- virtual actuator strength limits;
- energy and momentum diagnostics.

OpenSim inverse dynamics solves for generalized forces that produce a movement when given kinematics, inertial properties, and external loads. [S002] CPCS-MX records whether a force or torque is measured, simulated, or estimated, and it stores residual diagnostics when a motion and its loads are dynamically inconsistent.

### 8.3 Momentum transfer as an action relation

For a digital fight or superhuman action, `momentum_transfer` is best represented as a relation between actors or objects:

```json
{
  "event_id": "impact_042",
  "type": "simulated_impact",
  "source": "actor_a.hand_r",
  "target": "actor_b.upper_torso",
  "time_s": 2.4167,
  "impulse_world_Ns": [18.0, 4.0, 1.5],
  "reaction_delay_s": 0.0417,
  "transfer_fraction": 0.62,
  "visual_exaggeration": 1.35,
  "evidence_class": "authored",
  "scope": "virtual_only"
}
```

The values are virtual design parameters unless backed by instrumented data. The animation system can use them to drive recoil, debris, sound, camera shake, or a physics controller. A staging adapter may instead compile the same event into a near-contact cue and an independently choreographed reaction, avoiding actual collision.

### 8.4 Proximal-to-distal sequencing is not a universal template

Combat biomechanics often discusses transfer through legs, pelvis, trunk, shoulder, elbow, and hand. Studies of straight punches show that proximal-to-distal maxima can coexist with simultaneous initiation, and sequencing varies with technique and context. [S041] Other studies report different kinetics and kinematics across punch types. [S042] CPCS-MX should therefore encode observed or authored phase relationships rather than hard-coding one universal chain.

### 8.5 Superhuman physics

A virtual character can have nonhuman mass, strength, gravity response, or compliance. The score must still be internally coherent. If gravity is reduced to extend hang time, landing timing, vertical velocity, camera tracking, cloth response, and debris should all use the same virtual world definition unless a deliberate cartoon discontinuity is marked. “Stronger” should not automatically mean every joint moves faster; it may mean a shorter acceleration phase, greater virtual impulse, less recoil, or a larger environmental response.

<!-- RAG_CHUNK id="cpcs-mx-09" title="Inverse kinematics, retargeting, and morphology" concepts="inverse kinematics, retargeting, morphology, end effectors, solver" evidence="ESTABLISHED,PROPOSED" -->
<a id="9-inverse-kinematics-retargeting-and-morphology"></a>
## 9. Inverse kinematics, retargeting, and morphology

Inverse kinematics solves for generalized coordinates that best satisfy positional, orientational, or marker targets. OpenSim formulates IK as a weighted least-squares fit between model and experimental markers or coordinates. [S001] Production rigs use related methods to place hands and feet, align to terrain, preserve contacts, or adapt animation to different proportions. Unreal’s Full-Body IK exposes effectors, preferred angles, stiffness, mass multipliers, stretching, and root behavior, illustrating the practical control variables a CPCS-MX adapter may target. [S013]

### 9.1 IK objective

A simplified objective is:

\[
\min_q
\sum_i w_i \|f_i(q)-x_i^*\|^2
+ \sum_j \lambda_j \|q_j-q_j^{pref}\|^2
+ E_{contact}(q)
+ E_{limit}(q)
+ E_{style}(q)
\]

where `q` are joint coordinates, `f_i(q)` are end-effector positions, `x_i*` are targets, and the remaining terms penalize contact violation, joint-limit violation, and deviation from preferred style. Hard constraints are handled separately or with exact projection where possible.

### 9.2 Retargeting goals

Retargeting must preserve more than joint angles. Depending on the shot, the priorities may be:

- action identity;
- foot and hand contacts;
- root path;
- timing and phase;
- end-effector paths;
- center-of-mass behavior;
- silhouette;
- gaze target;
- Laban quality;
- local mannerism;
- camera-relative composition.

Highly varied morphologies require a morphology-independent representation and IK or learned adaptation. [S016] Skeleton-aware and geometry-aware methods seek to preserve semantics while reducing artifacts such as interpenetration. [S017][S018]

### 9.3 Retarget profile

CPCS-MX stores a `retarget_profile`:

```yaml
retarget_profile:
  source_skeleton: humanml3d_22j_v1
  target_skeleton: hero_longlimb_v4
  retarget_root: pelvis
  chains:
    arm_r:
      source: [shoulder_r, elbow_r, wrist_r]
      target: [clavicle_r, upperarm_r, lowerarm_r, hand_r]
      preserve:
        - wrist_world_path
        - elbow_bend_plane
  scale_policy:
    root_displacement: preserve_normalized_leg_length
    hand_reach: target_proportion
  contacts:
    feet: hard
    hands: event_dependent
  twist_distribution: procedural
```

### 9.4 Stylized morphology

Long limbs, oversized hands, nonhuman torsos, tails, wings, or extra joints require explicit semantic mapping. The system should not pretend that every target is a human skeleton. It can map an action’s functional endpoints—support, reach, gaze, impact—onto a different topology while preserving timing and intent. Cross-morphology work demonstrates that retargeting is a representation and control problem, not a direct channel copy.

### 9.5 Solver verification

After retargeting, calculate contact error, end-effector path error, joint-limit violations, penetration, root deviation, and phase deviation. A visually acceptable result can intentionally deviate from source joint angles while preserving perceptual invariants.

<!-- RAG_CHUNK id="cpcs-mx-10" title="Motion phases, contacts, and action graphs" concepts="phase, local phase, contacts, support, action graph, events" evidence="ESTABLISHED,PROPOSED" -->
<a id="10-motion-phases-contacts-and-action-graphs"></a>
## 10. Motion phases, contacts, and action graphs

### 10.1 Global and local phases

A phase variable maps time to progress through a recurring or bounded movement. PFNN uses phase to coordinate locomotion. [S008] Local Motion Phases extend the idea to asynchronous rhythms across body parts and multi-contact movements. [S009] CPCS-MX uses both:

```json
{
  "phase_tracks": [
    {"id":"gait","domain":"global","periodic":true,"samples":[[0.0,0.0],[0.5,0.52],[1.0,0.0]]},
    {"id":"hand_r_attack","domain":"joint_group","periodic":false,"samples":[[1.2,0.0],[1.45,0.35],[1.62,1.0],[1.88,0.0]]}
  ]
}
```

For nonperiodic actions, the phase can represent preparation, execution, apex/contact, follow-through, and recovery. It is not required to advance linearly.

### 10.2 Contact taxonomy

Contacts include:

- `support`: foot, hand, knee, or body supporting weight;
- `grasp`: hand or appendage constrained to an object;
- `surface_touch`: visible touch without substantial support;
- `staged_near_contact`: intentionally appears to connect from the camera without collision;
- `simulated_impact`: virtual dynamic event;
- `environmental_collision`: body or prop meets scene geometry;
- `attachment`: weapon, wearable, harness, or rig constraint;
- `break_contact`: release or takeoff.

A contact record stores participants, local points, surface normal, start/end, confidence, friction/compliance where simulated, and whether the event is hard or soft.

### 10.3 Contact events as anchors

Contacts are among the strongest anchors for believable motion. Foot skating occurs when a foot expected to be planted moves relative to the ground. Hand-object interaction fails when grasp points drift or penetrate. Contact-guided generation methods explicitly model contact to improve coherent human-object motion. [S056]

In a fight shot, contact timing couples multiple systems:

```text
attacker end-effector path
+ defender target position
+ near-contact or collision decision
+ defender reaction onset
+ sound onset
+ VFX accent
+ camera shake
+ edit point
```

The event graph preserves that causal bundle while allowing each offset to be edited.

### 10.4 Action graph

An action graph represents causal and temporal relationships:

```text
establish_guard
→ shift_weight
→ step_in
→ pelvis_turn
→ torso_turn
→ arm_extension
→ staged_near_contact
→ defender_recoil
→ follow_through
→ return_to_guard
```

Edges can mean `before`, `overlaps`, `causes`, `requires`, `targets`, or `interrupts`. This allows the same movement content to be rephrased. A sudden style compresses preparation and increases acceleration; a sustained style lengthens transitions; a feint interrupts before contact and redirects the action graph.

### 10.5 Multi-actor constraints

InterControl represents human interaction using desired distances between joint pairs and uses IK guidance to align joints. [S055] CPCS-MX generalizes this to distance, orientation, visibility, and event constraints. Two characters can be required to maintain a screen-space gap while their world-space paths differ to achieve a camera cheat.

<!-- RAG_CHUNK id="cpcs-mx-11" title="Hard, soft, and perceptual constraints" concepts="constraints, feasibility, hard constraints, soft constraints, perceptual constraints" evidence="PROPOSED,ESTABLISHED" -->
<a id="11-hard-soft-and-perceptual-constraints"></a>
## 11. Hard, soft, and perceptual constraints

A sophisticated score needs more than desired values. It must state which requirements are inviolable, negotiable, or judged perceptually.

### 11.1 Constraint classes

**Hard constraints** must be satisfied or compilation fails. Examples:

- source foot remains within 2 cm of its planted point during a declared support interval;
- contact event occurs at frame 72;
- no body penetration beyond a declared tolerance;
- character remains inside a stage boundary;
- locked joint does not move;
- action order remains unchanged.

**Soft constraints** contribute weighted penalties:

- prefer elbow bend near a reference;
- preserve root trajectory within 5 cm;
- maintain a Laban directness target;
- minimize deviation from a captured motion;
- reduce jerk outside deliberate accents.

**Perceptual constraints** concern audience reading:

- silhouette remains separable;
- hand remains visible during the key action;
- attack direction is readable;
- product label occupies a minimum screen region;
- antagonist reaction is visible before the cut;
- camera does not obscure the causal contact.

**Style constraints** describe genre conventions but can be relaxed when they conflict with action identity:

- use two-frame anticipation hold;
- allow one smear exposure;
- preserve restrained acting scale;
- reduce microvariation during a heroic pose.

### 11.2 Feasibility and priority

Hard constraints can conflict. A hand cannot simultaneously reach two distant targets at one time. A short-limbed target may not match a long-limbed source wrist path while keeping the root fixed and all joints within limits. The compiler performs a feasibility pass before generation and returns a minimal conflict set when possible.

Recommended priority groups:

```text
P0 safety and rights constraints
P1 timebase, identity replacement, locked contacts
P2 action causality and root feasibility
P3 key joint and gaze targets
P4 expressive and Laban goals
P5 secondary motion and stylistic polish
```

Priorities do not mean lower layers are unimportant; they define what may be relaxed when no exact solution exists.

### 11.3 Constraint schema

```json
{
  "constraint_id": "foot_lock_L_001",
  "type": "position_lock",
  "class": "hard",
  "target": "actor_a.foot_l.contact_patch",
  "frame": "world",
  "interval_s": [0.82, 1.31],
  "position_m": [1.22, 0.0, -0.43],
  "tolerance_m": 0.02,
  "on_violation": "fail_compile",
  "provenance": {"evidence_class":"authored"}
}
```

### 11.4 Perceptual metrics are project-defined

A value such as `silhouette_readability > 0.90` is not a universal scientific standard. It must be tied to a measurement method: segmentation confidence, pose separability, human ratings, or an occlusion metric. CPCS-MX stores the metric definition, evaluator version, threshold, and calibration set.

### 11.5 Constraint-preserving stylization

Stylization operates around invariants. A smear may violate anatomical shape but preserve hand start point, end point, timing, action direction, and silhouette. A low-gravity leap may change the flight arc but preserve takeoff contact, target landing, gaze, and narrative beat duration. This is more controllable than applying one global `style_intensity` scalar.

<!-- RAG_CHUNK id="cpcs-mx-12" title="Laban Body–Effort–Shape–Space as a control layer" concepts="Laban, BESS, Effort, Shape, Space, Body" evidence="ESTABLISHED,OPERATIONALIZATION" -->
<a id="12-laban-bodyeffortshapespace-as-a-control-layer"></a>
## 12. Laban Body–Effort–Shape–Space as a control layer

Laban Movement Analysis is richer than four adjectives. A common organizing frame is Body, Effort, Shape, and Space. Labanotation and Kinetography Laban are formal notation systems for recording movement direction, body involvement, level, timing, and other aspects; Benesh Movement Notation is another established system for documenting and reconstructing movement. [S022][S023][S024] CPCS-MX does not replace these traditions. It borrows concepts for computational performance control and stores links to formal notation when available.

### 12.1 Body

The Body component addresses what moves and how parts are connected or initiated. CPCS-MX represents:

- initiating body part;
- sequencing across segments;
- simultaneous versus successive action;
- connectivity patterns;
- whole-body versus isolated involvement;
- support and weight shift;
- breath support;
- body-part emphasis.

This maps naturally to action graphs, local phases, and joint groups.

### 12.2 Effort

Effort is commonly described through factors with paired qualities:

| Factor | Qualities | Engineering interpretation candidates |
|---|---|---|
| Weight | light / strong | force intention, acceleration profile, muscular engagement, groundedness |
| Time | sustained / sudden | urgency, temporal compression, acceleration onset |
| Space | indirect / direct | path focus, target commitment, curvature, attention allocation |
| Flow | free / bound | controllability, continuation, braking, tension, reversibility |

These are qualitative movement intentions. Strong Weight is not numerically identical to high Newtons; a small gesture can be performed with strong intention. Direct Space is not simply a straight line; it concerns focused attention and spatial approach. Bound Flow is not merely low speed; it concerns control and containment.

### 12.3 Shape

Shape addresses how the body changes form in relation to self and environment. Useful CPCS-MX fields include:

- rising / sinking;
- spreading / enclosing;
- advancing / retreating;
- shape flow, directional shaping, and carving-like three-dimensional adaptation;
- torso expansion and contraction;
- reach volume and kinesphere occupancy;
- relationship to objects, partners, and camera.

### 12.4 Space

Space includes direction, level, pathways, planes, reach space, and spatial intent. CPCS-MX stores world-space and body-relative directions, levels, target points, path families, and camera-relative composition.

### 12.5 Laban as a modulation layer

The EMOTE model showed how Effort and Shape qualities can be applied to base movements while preserving the underlying action. [S028] CPCS-MX adopts this separation:

```text
action content: walk toward door
+ Effort: light, sustained, indirect, bound
+ Shape: enclosing, sinking
+ mannerism: protects throat, avoids eye contact
= a specific performance
```

Recent work such as LaMoGen investigates quantitative Laban guidance for generative motion, but such mappings remain active research and should be marked emerging. [S029]

### 12.6 Interval representation

Laban qualities vary through a phrase. The score uses intervals and transition curves rather than one clip-level label:

```yaml
laban_intervals:
  - interval_s: [0.0, 1.4]
    effort: {weight: light, time: sustained, space: indirect, flow: bound}
    shape: {vertical: sinking, transverse: enclosing}
  - interval_s: [1.4, 1.75]
    transition: sudden_release
    effort: {weight: strong, time: sudden, space: direct, flow: free}
```

The transition itself is part of the acting. A bound-to-free release may communicate loss of restraint even when the action content is unchanged.
<!-- RAG_CHUNK id="cpcs-mx-13" title="Effort phrasing, Shape change, and computational proxies" concepts="effort phrasing, Laban proxies, feature mapping, calibration" evidence="OPERATIONALIZATION,EMERGING" -->
<a id="13-effort-phrasing-shape-change-and-computational-proxies"></a>
## 13. Effort phrasing, Shape change, and computational proxies

### 13.1 From static labels to phrases

Movement quality is temporal. A performer can begin with sustained, bound movement, accumulate tension, release suddenly, and settle into light free flow. A single clip-level tag discards the phrase. CPCS-MX models an Effort phrase as a sequence of intervals plus transitions, emphasis points, and body-part scopes.

```json
{
  "effort_phrase_id": "phrase_07",
  "scope": ["pelvis","spine","arm_r"],
  "intervals": [
    {"time_s":[0.0,0.8],"weight":0.35,"time":0.22,"space":0.78,"flow":0.18},
    {"time_s":[0.8,1.05],"weight":0.88,"time":0.95,"space":0.92,"flow":0.30},
    {"time_s":[1.05,1.7],"weight":0.45,"time":0.40,"space":0.62,"flow":0.75}
  ],
  "anchors": [
    {"event":"contact_12","role":"effort_apex"}
  ]
}
```

The normalized values are engineering controls, not official Laban scores. The project defines which pole corresponds to zero and one, how the values are elicited or annotated, and how they compile.

### 13.2 Candidate computational features

A compiler may use measurable features as proxies:

| Laban-related target | Candidate features | Important caveat |
|---|---|---|
| Strong Weight | acceleration magnitude, deceleration, support loading, torso involvement, virtual impulse | physical magnitude and perceived intention can diverge |
| Sudden Time | short onset, concentrated velocity peak, narrow event interval | a sudden action can still be small and light |
| Direct Space | low path curvature, stable target vector, focused gaze, low lateral search | directness includes attention, not geometry alone |
| Bound Flow | early braking, reduced overshoot, low endpoint variance, muscular/pose containment | bound does not mean rigid or slow |
| Rising Shape | vertical COM/root change, spinal lengthening, lifted sternum/head | apparent rise can be produced by camera |
| Enclosing Shape | reduced reach volume, limb adduction, torso contraction | body morphology affects raw volume |

The mappings should be fitted against expert annotations or project-specific exemplars. A model can learn to predict Laban labels, but the generated score should retain the underlying motion features and annotation provenance.

### 13.3 Phrasing transforms

CPCS-MX defines transforms that operate on a base motion:

- **temporal redistribution:** change the duration of preparation, execution, and recovery while preserving total duration or selected events;
- **amplitude shaping:** increase or decrease selected joint excursions and root displacement;
- **path shaping:** straighten, curve, redirect, or carve end-effector paths;
- **continuity shaping:** change braking, overshoot, and follow-through;
- **body involvement:** recruit or suppress torso, pelvis, head, and counter-movement;
- **support shaping:** shift groundedness and weight transfer;
- **attention shaping:** alter gaze lead and target persistence.

A transform declares invariants. For example, converting a reach from sustained to sudden may preserve target contact time and endpoint while compressing initiation and increasing the peak velocity. Converting from free to bound may preserve the target path but reduce overshoot and shorten follow-through.

### 13.4 Shape and camera

Shape is perceived through both body configuration and framing. A close-up can hide a full-body spreading action; a wide lens can exaggerate advancing; a camera tilt can simulate rising. The score stores body Shape and camera presentation separately, then allows a verification layer to evaluate the composite image.

### 13.5 Combat-specific Effort

A digital combat exchange may use contrasting effort phrases:

```text
fighter A: strong + sudden + direct + bound
fighter B: light + sustained + indirect + free
```

This creates tactical readability: one character commits, the other yields and redirects. The action graph can remain identical while timing, path, support, and follow-through change. For stage or screen violence, these descriptors concern performance and virtual animation; they are not instructions to apply real force to a person.

### 13.6 Superhuman effort paradoxes

Stylized movement can intentionally combine apparently contradictory physical cues, such as strong Weight with a light recovery, or sudden initiation with prolonged hang time. CPCS-MX represents these as separate phase-local controls rather than forcing one label across the clip:

```text
launch: strong / sudden / direct / bound
flight: light / sustained / direct / free
landing: strong / sudden / direct / bound
recovery: light / sustained / indirect / free
```

This phase-specific notation captures the “heavy impact, floating recovery” pattern more accurately than a global strength multiplier.

<!-- RAG_CHUNK id="cpcs-mx-14" title="FACS, face, gaze, breath, and upper-body synchronization" concepts="FACS, action units, gaze, breath, blink, facial timing" evidence="ESTABLISHED,PROPOSED" -->
<a id="14-facs-face-gaze-breath-and-upper-body-synchronization"></a>
## 14. FACS, face, gaze, breath, and upper-body synchronization

### 14.1 FACS is visible movement coding

FACS decomposes observable facial movement into anatomically based Action Units. [S031][S032] It does not, by itself, prove a person’s emotion, intent, truthfulness, or internal state. CPCS-MX stores three separate tracks:

1. **experienced affect:** an authored or inferred internal VAD/VAC trajectory;
2. **display strategy:** conceal, amplify, substitute, neutralize, or leak;
3. **visible facial behavior:** AU-like movement, head pose, gaze, blink, and mouth/jaw action.

This separation allows a character to feel fear while presenting composure.

### 14.2 AU timing

A facial event stores onset, apex, offset, intensity, asymmetry, and confidence. Native FACS intensity uses ordinal A–E levels; a digital rig may use normalized `[0,1]` values. CPCS-MX preserves the original coding system and records the mapping to the target rig.

```json
{
  "event_id": "face_au04_12",
  "actor": "hero",
  "au": "AU04",
  "side": "bilateral",
  "onset_s": 1.82,
  "apex_s": 2.08,
  "offset_s": 2.46,
  "intensity": {"scale":"normalized_rig","value":0.42},
  "source_coding": {"scale":"FACS_A_to_E","value":"B"},
  "sync": {"event":"impact_12","offset_s":0.10}
}
```

A common coding error should be avoided: AU14 is generally the **dimpler**, whereas lip tightening and pressing are associated with other Action Units such as AU23 and AU24. AU45 denotes blink. Agent vocabularies should use a validated AU dictionary rather than relying on approximate internet lists.

### 14.3 Face-body coupling

Facial behavior should not be pasted on top of body motion after the fact. Strain, anticipation, impact, recovery, and attention have body-wide timing. A high-effort action can involve:

- gaze acquiring the target before movement onset;
- head stabilization or counter-rotation;
- blink suppression during critical visual guidance;
- jaw or lip tension during preparation;
- facial apex at or slightly after contact;
- blink, exhale, or release during recovery.

OpenFace can estimate landmarks, head pose, gaze, and a subset of Action Units, but detector outputs depend on visibility and training domain. [S033] Stylized faces require character-specific mappings. Performance-driven facial animation demonstrates the value of transferring captured expression weights to a different target shape while allowing an artist to define target key shapes. [S034]

### 14.4 Gaze as an action track

Natural action often uses proactive gaze: the eyes acquire task-relevant locations before the hand or body completes the action. [S037] CPCS-MX stores gaze target, saccade onset, fixation interval, confidence, and whether eyes, head, and torso participate.

```yaml
gaze_events:
  - target: antagonist_right_hand
    start_s: 0.62
    fixation_s: [0.71, 1.08]
    lead_relative_to_body_action_s: 0.18
    eye_head_coordination: eyes_then_head
```

### 14.5 Breath and effort rhythm

Breath provides phrase structure and visible micro-rhythm. It can drive ribcage expansion, shoulder elevation, abdominal tension, vocalization, and recovery. Human locomotor-respiratory coupling exists, but ratios vary across individuals and tasks; CPCS-MX should not hard-code one universal step-to-breath ratio. [S036]

A breath track contains phase, volume proxy, airway state, and synchronization:

```json
{
  "breath_track": {
    "cycles": [
      {"inhale_s":[0.0,0.9],"hold_s":[0.9,1.05],"exhale_s":[1.05,1.48]}
    ],
    "effort_sync": [{"event":"launch_01","phase":"exhale","offset_s":0.0}],
    "visibility": 0.35,
    "audio": "short_effort_exhale"
  }
}
```

### 14.6 Micro-expression caution

Micro-expression datasets annotate brief facial events with onset, apex, offset, and AU codes. [S035] Their existence does not justify automated deception inference. In CPCS-MX they are useful as timing references for subtle facial movement, not as a lie detector.

<!-- RAG_CHUNK id="cpcs-mx-15" title="Mannerisms, postural tone, and movement signatures" concepts="mannerism, personality, asymmetry, postural sway, movement signature" evidence="ESTABLISHED,PROPOSED" -->
<a id="15-mannerisms-postural-tone-and-movement-signatures"></a>
## 15. Mannerisms, postural tone, and movement signatures

### 15.1 Why perfect generic motion looks synthetic

A motion can satisfy joint trajectories and contacts yet feel anonymous. Human movement includes stable individual tendencies: preferred stance width, arm-swing asymmetry, head carriage, tempo, gesture vocabulary, gaze habits, postural tone, and correction strategies. Research has found relationships between gait features, emotion, and some personality measures, but these relationships are probabilistic and context-dependent, not deterministic personality readers. [S039][S040]

CPCS-MX treats a movement signature as a reusable character profile, not a psychological diagnosis.

### 15.2 Mannerism profile

```yaml
mannerism_profile:
  id: guarded_confident_v2
  baseline_posture:
    chest_openness: 0.62
    chin_elevation: 0.08
    shoulder_asymmetry: {left_higher: 0.03}
  locomotion:
    cadence_bias: 0.04
    stride_asymmetry: 0.025
    arm_swing_right_scale: 0.88
    preferred_turn_side: left
  gaze:
    target_acquisition_lead_s: 0.16
    direct_gaze_duty_cycle: 0.64
  habits:
    - action: jaw_set
      trigger: threat_appraisal
      probability: 0.55
      refractory_s: 3.0
    - action: knuckle_flex
      trigger: waiting
      probability: 0.18
  microvariation:
    seed: 424201
    low_frequency_sway: 0.012
    correction_interval_s: [1.2, 3.8]
```

Probabilities should be used with a deterministic random seed so that generation can be reproduced. A habit has triggers and a refractory period; it is not applied uniformly every few seconds.

### 15.3 Postural tone and sway

Quiet standing is not motionless. Postural sway contains universal and individual components related to balance control. [S038] For animation, a postural-tone model can include low-frequency ankle/hip strategy, respiration-driven torso motion, head stabilization, and visual-attention changes. The amplitudes must scale with shot size: a close-up can reveal small head and shoulder motion that would be irrelevant in a wide shot.

### 15.4 Structured imperfection

Natural imperfection has causes:

- sensorimotor correction after an inaccurate step;
- slight foot repositioning to restore support;
- asymmetric reach due to handedness;
- breath-induced timing variation;
- attention switching;
- fatigue or load;
- environmental uncertainty;
- social self-presentation.

CPCS-MX models these as bounded modules and event responses. Independent frame noise is prohibited by default because it produces jitter and violates smoothness.

### 15.5 Cultural and contextual gestures

Gestures can be culturally, socially, and situationally specific. The framework stores provenance, intended context, and review status. Agents should not infer a culture from a single gesture or generate stereotyped movement profiles. A production can define an approved gesture library with human review.

### 15.6 Character continuity

The same character should retain recognizable timing and posture across generated shots even when the action changes. The character profile therefore compiles into priors for root posture, phase timing, gaze, facial baseline, gesture selection, and recovery. MotionPersona and related research illustrate the growing interest in conditioning locomotion on traits or short exemplars, but such systems remain data- and domain-dependent. [S060]

<!-- RAG_CHUNK id="cpcs-mx-16" title="Natural movement and high-fidelity UGC" concepts="UGC, naturalism, handheld, creator video, imperfections, product visibility" evidence="PROPOSED,ESTABLISHED" -->
<a id="16-natural-movement-and-high-fidelity-ugc"></a>
## 16. Natural movement and high-fidelity UGC

High-fidelity UGC is not merely low production quality. It is a recognizable performance and capture grammar: direct address, imperfect but purposeful timing, handheld or device-like framing, practical lighting, product handling, conversational gestures, eye-line shifts, captions, cuts, and evidence beats. A recreation system should decompose those elements instead of adding random shake and compression artifacts.

### 16.1 UGC performance layers

A creator-style clip can be represented as:

```text
communication objective
→ verbal beat
→ gaze target
→ gesture and product action
→ posture and breath
→ camera/device behavior
→ edit and caption event
→ proof or reaction
```

The movement score records:

- lens-address intervals and gaze duty cycle;
- product pick-up, presentation, use, and set-down contacts;
- hand-to-product visibility;
- speech gesture timing;
- body lean toward or away from the device;
- natural pauses and self-corrections;
- breath and blink behavior;
- framing drift and correction;
- cut and caption timing;
- wardrobe, identity, product, and setting replacement policy.

### 16.2 Controlled naturalism

A UGC style profile might introduce:

- slight root and camera drift with low-frequency correlation;
- one small balance adjustment after a reach;
- gaze alternating between lens, product, and thought-space;
- gesture onset preceding emphasized words;
- brief hesitation before a claim;
- nonuniform but plausible speaking rhythm;
- asymmetric hand use;
- restrained secondary cloth and hair response.

It should not introduce continuous jitter, random blinks, arbitrary pauses, or inconsistent hand-object geometry.

### 16.3 Product and action constraints

If a product is central, CPCS-MX can enforce:

```yaml
perceptual_constraints:
  - id: product_visibility_demo
    metric: visible_area_fraction
    target: product_primary_face
    interval_s: [2.4, 4.8]
    minimum: 0.018
    class: hard
  - id: hand_not_cover_label
    metric: label_occlusion_fraction
    maximum: 0.22
    class: soft
```

These thresholds are project-specific and require a defined detector. The marketing layer may hypothesize that a hook, proof beat, or product hold improves communication, but the system cannot guarantee sales.

### 16.4 Identity replacement with performance retention

For rights-safe modular recreation, retain approved structural features—timing, beat order, gesture function, camera grammar—and replace identity, voice, wardrobe, setting, dialogue, and branded elements as required. Movement signature should be generated for the replacement performer rather than copied as a biometric fingerprint from an unauthorized person.

### 16.5 UGC verification

Measure:

- lens-address timing;
- gesture-to-word offset;
- product contact and visibility;
- hand-object penetration;
- shot duration and cut order;
- camera drift spectrum;
- blink and gaze plausibility;
- speech/body synchronization;
- identity and brand replacement compliance.

The generated video is re-extracted into the same CPCS-MX layers, allowing agentic comparison rather than subjective prompt tweaking alone.

<!-- RAG_CHUNK id="cpcs-mx-17" title="Staged combat and multi-actor action coding" concepts="fight choreography, staged combat, contact, recoil, recovery, multi-actor" evidence="ESTABLISHED,PROPOSED,SAFETY" -->
<a id="17-staged-combat-and-multi-actor-action-coding"></a>
## 17. Staged combat and multi-actor action coding

### 17.1 Scope and safety

This section concerns **virtual character animation and professionally staged screen action**. It does not provide instructions for injuring a person. Professional stage-combat practice prioritizes safety, repeatability, theatrical commitment, and storytelling. [S044] Apparent impacts can be created through distance, angle, timing, reaction, sound, editing, and VFX rather than actual force.

### 17.2 Atomic action vocabulary

A fight scene should be decomposed into functional actions rather than named techniques alone:

- establish stance or guard;
- approach, retreat, circle, close distance;
- shift support;
- step-in or step-out;
- pivot or turn;
- load or anticipate;
- reach or strike-like extension;
- block, parry, evade, duck, redirect;
- staged near-contact or virtual impact;
- recoil, displacement, stumble, fall;
- catch, roll, brace, land;
- recovery, reorientation, return to guard;
- reaction or decision pause.

Named martial-arts labels can be metadata, but the executable score uses root, joint, phase, contact, and target relations.

### 17.3 Coupled actor score

A combat beat is not two independent clips. It is a coupled system:

```json
{
  "beat_id": "exchange_03",
  "participants": ["attacker","defender"],
  "events": [
    {"id":"A_step","actor":"attacker","type":"step_in","start_s":1.20,"end_s":1.48},
    {"id":"A_extend","actor":"attacker","type":"strike_like_extension","start_s":1.36,"apex_s":1.67,"end_s":1.82},
    {"id":"near_contact","type":"staged_near_contact","source":"attacker.hand_r","target":"defender.head_region","time_s":1.67},
    {"id":"B_recoil","actor":"defender","type":"recoil","start_s":1.71,"apex_s":1.88,"end_s":2.20}
  ],
  "relations": [
    {"type":"causes","from":"near_contact","to":"B_recoil"},
    {"type":"targets","from":"A_extend","to":"defender.head_region"}
  ]
}
```

### 17.4 Biomechanical organization

The score may encode support-foot drive, pelvis rotation, torso rotation, shoulder motion, elbow extension, and wrist path. Biomechanics research shows that sequence and contribution differ among punch types and styles, and that lower-body and trunk behavior influence output. [S041][S042][S043] For animation, the useful conclusion is not a universal combat recipe; it is that whole-body coordination and support changes matter for perceived power.

### 17.5 Contact, impulse, and reaction

A contact event can include:

- visual minimum distance;
- collision decision;
- contact normal;
- virtual impulse;
- defender reaction delay;
- local deformation;
- root displacement;
- camera and audio accents;
- recovery duration.

For staged near-contact, the attacker trajectory and defender reaction can be authored independently, with camera placement making the event read as contact. This permits repeatability and avoids requiring a physically accurate collision.

### 17.6 Falls and recovery

Falls need support-state and landing-event notation:

```text
loss of balance
→ base of support failure
→ protective or stylized response
→ first contact
→ load distribution
→ secondary contacts
→ slide or roll
→ settle
→ recovery decision
```

A virtual superhuman fall may include crater effects and reduced injury response, but the action graph still needs clear contact timing and body orientation. Real stunt planning belongs to qualified professionals, not an automated animation schema.

### 17.7 Readability and camera cheats

Fight choreography is designed for an audience. Screen direction, silhouette, target visibility, reaction timing, and cut placement are perceptual constraints. A camera-side cheat can preserve a visible gap while making trajectories overlap in projection. The score stores both world-space and screen-space contact conditions so the technique is explicit.

### 17.8 Fine-tuning loop

For a generated fight:

1. compile pose, root, contact, and camera controls;
2. generate the clip;
3. re-extract actors and pose;
4. measure contact frame, minimum distance, root path, phase, reaction delay, and screen direction;
5. adjust only the failing modules;
6. regenerate the smallest affected interval;
7. verify continuity at splice boundaries.

This modular loop is more deterministic than rewriting an entire paragraph prompt.

<!-- RAG_CHUNK id="cpcs-mx-18" title="Anime, sakuga, limited animation, and cartoon physics" concepts="anime, sakuga, holds, smears, key poses, cartoon physics" evidence="ESTABLISHED,PROPOSED" -->
<a id="18-anime-sakuga-limited-animation-and-cartoon-physics"></a>
## 18. Anime, sakuga, limited animation, and cartoon physics

Anime and other stylized 2D animation often optimize for designed drawings and perceptual motion rather than continuous anatomical reconstruction. The source may contain held cels, exposure changes, extreme key poses, smear drawings, multiplane background movement, perspective deformation, impact flashes, and deliberate temporal discontinuities. Treating every frame as a sample of a smooth 3D human skeleton can destroy the style.

### 18.1 Dual representation

CPCS-MX stores two linked representations:

1. **choreographic skeleton:** action, root, joint, phase, and contact logic;
2. **graphic motion layer:** key drawings, silhouette, deformation, exposure, smear, effects, and camera-plane motion.

Cartoon Capture demonstrated that traditionally animated motion can be tracked and retargeted while preserving expressive non-rigid changes. [S046][S080] Artist-Directed Dynamics combines simulation with keyframing to support exaggeration and abrupt deformations rather than forcing animation to obey a single physical simulation. [S045]

### 18.2 Exposure and held drawings

An animation exposure track states which drawing or pose is displayed and for how long:

```yaml
exposure_track:
  - frames: [0, 2]
    pose_ref: anticipation_key_A
    hold: true
  - frames: [3, 3]
    pose_ref: smear_01
    deformation_mode: graphic
  - frames: [4, 5]
    pose_ref: contact_key_B
    hold: true
```

The underlying skeleton may interpolate continuously for simulation or camera integration, while the render selects held or deformed drawings.

### 18.3 Smear frames

A smear is not simply motion blur. It is an authored shape that connects positions, preserves direction, and improves readability. CPCS-MX represents:

- source and destination silhouette anchors;
- smear duration in exposures;
- body regions affected;
- maximum deformation;
- multiplicity or echo count;
- line-of-action;
- color and effect treatment;
- whether the rig or only the render deforms.

### 18.4 Keyframe economy

A stylized sequence can concentrate information in anticipation, apex, contact, and recoil keys. In-between density becomes a style control. Fewer in-betweens do not imply poor motion if timing, arcs, silhouettes, and action causality are clear. The score stores `key_pose_priority` and `inbetween_policy` rather than demanding constant frame-to-frame change.

### 18.5 Perspective and anatomy

A fist may enlarge toward camera, limbs may stretch, or the torso may twist beyond human anatomy for one drawing. These are graphic deformations. They should compile through camera-relative scaling, blendshapes, cage deformation, or 2D warps, not by silently changing the human joint-limit schema.

### 18.6 Impact grammar

An anime impact may combine:

```text
contact key
+ one-frame monochrome or inverse-color flash
+ background speed-field discontinuity
+ screen shake
+ debris burst
+ held recoil silhouette
+ delayed sound or silence gap
```

Each element has independent timing. The impact can be superhuman in presentation while the choreography retains a staged near-contact.

### 18.7 Style transfer limits

A scalar `style_intensity` can be a user interface control, but the compiler should expand it into multiple parameters: hold density, smear probability, deformation scale, camera amplitude, effect density, time-warp strength, and anatomical deviation. Otherwise one slider can produce incoherent combinations.

<!-- RAG_CHUNK id="cpcs-mx-19" title="Superhuman motion as constrained transformation" concepts="superhuman, physics scale, gravity, impulse, deformation, invariants" evidence="PROPOSED,ESTABLISHED" -->
<a id="19-superhuman-motion-as-constrained-transformation"></a>
## 19. Superhuman motion as constrained transformation

### 19.1 The wrong model: multiply everything

A global “2.5× strength” or “1.5× speed” parameter is too coarse. It can shorten actions until they become unreadable, break contacts, create impossible joint velocities, desynchronize effects, and eliminate character-specific timing. Superhuman motion should be a **phase- and domain-specific transformation** applied to a coherent base action.

### 19.2 Transformation vector

```json
{
  "superhuman_transform": {
    "scope": "virtual_only",
    "temporal": {
      "preparation_scale": 0.82,
      "execution_scale": 0.55,
      "recovery_scale": 1.20,
      "hang_time_scale": 1.65
    },
    "spatial": {
      "root_displacement_scale": 1.80,
      "reach_scale": 1.15,
      "arc_height_scale": 1.45
    },
    "dynamics": {
      "gravity_scale": 0.68,
      "virtual_actuator_scale": 2.4,
      "impact_impulse_scale": 1.9,
      "environment_response_scale": 2.8
    },
    "graphic": {
      "deformation_scale": 1.35,
      "smear_strength": 0.70,
      "effect_density": 0.65
    },
    "invariants": [
      "action_order",
      "takeoff_contact",
      "landing_target",
      "screen_direction",
      "hero_silhouette_at_apex"
    ]
  }
}
```

### 19.3 Gravity and hang time

Reducing gravity changes the entire ballistic arc, not only a single frame. A compiler can solve the required takeoff velocity for a desired apex and landing time under the virtual gravity vector. If an artist wants an impossible pause at the apex, the score marks a `time_suspension` or `graphic_hold` rather than pretending it follows ordinary ballistics.

### 19.4 Momentum-defying pivots

A sudden midair direction change requires one of the following explanations:

- contact with a surface or object;
- propulsion or energy effect;
- aerodynamic or nonhuman capability;
- camera-relative illusion;
- explicit cartoon-physics discontinuity.

The score declares which explanation is intended. This supports consistent secondary motion and environmental response.

### 19.5 Strong impact, light recovery

The user’s proposed “weight 1.4× human with floating recovery” becomes a phrase:

- launch and contact use strong Weight, rapid acceleration, and high virtual environmental response;
- recovery uses reduced gravity, longer damping, freer Flow, and lower visible effort;
- facial and breath tracks can show strain at impact but effortless composure afterward.

This is expressive logic, not a literal human force multiplier.

### 19.6 Virtual capacity profile

A character has a declared capacity profile:

```yaml
virtual_capacity:
  morphology: nonhuman_humanoid
  joint_limit_domain: rig_specific
  max_virtual_torque_scale: 2.4
  gravity_tolerance: 0.6
  impact_resilience: 3.0
  aerial_control: enabled
  injury_model: cinematic_none
```

This profile is separate from a real performer. It prevents an agent from translating virtual parameters into unsafe physical rehearsal.

### 19.7 Preserve readability

Superhuman speed often needs more anticipation, a held key, a camera setup, or time dilation—not less. The execution can be physically fast while the presentation allocates screen time for the audience to understand the event. CPCS-MX permits stage time and presentation time to differ through retiming and editing tracks.

<!-- RAG_CHUNK id="cpcs-mx-20" title="Secondary and overlapping motion" concepts="secondary motion, cloth, hair, soft tissue, accessories, overlap" evidence="ESTABLISHED,PROPOSED" -->
<a id="20-secondary-and-overlapping-motion"></a>
## 20. Secondary and overlapping motion

Secondary motion includes hair, cloth, loose equipment, soft tissue, capes, tails, debris, and environmental response. It contributes weight and continuity but should follow the primary performance rather than obscure it.

### 20.1 Driver graph

```text
root and joint acceleration
→ attachment-point motion
→ secondary solver
→ collision and wind
→ stylization constraints
→ render or control pass
```

Each secondary system declares driver joints, rest state, material parameters, collision proxies, damping, and artistic overrides.

### 20.2 Position-based dynamics

Position-Based Dynamics directly projects positions to satisfy constraints and is widely used because of controllability and robust collision handling. [S047] XPBD extends the approach to improve compliance behavior and provide more physically meaningful constraint control. [S048] These methods are suitable references for cloth, hair, ropes, and accessories, although production systems may use other solvers.

### 20.3 Primary-secondary separation

```json
{
  "secondary_motion": {
    "system_id": "coat_tail",
    "type": "cloth",
    "drivers": ["pelvis","spine_02"],
    "solver": "xpbd",
    "parameters": {
      "mass_kg": 0.42,
      "damping": 0.08,
      "compliance": 0.0004,
      "wind_world_mps": [0.0,0.0,0.0]
    },
    "art_direction": {
      "clear_face": true,
      "delay_scale": 1.2,
      "silhouette_priority": 0.8
    }
  }
}
```

### 20.4 Production overrides

Pixar’s cloth-production reports illustrate that simulation must coexist with director-mandated shapes and difficult character proportions. [S050] A CPCS-MX secondary system can include pinned shapes, collision exemptions, or keyed overrides. The overrides are visible in provenance rather than hidden inside a cache.

### 20.5 Anime secondary motion

Hair or cloth may be held, snapped, or drawn as a designed arc rather than continuously simulated. The secondary layer can therefore use modes:

- `physical_simulation`;
- `neural_simulation`;
- `keyframed_overlap`;
- `graphic_hold_and_snap`;
- `hybrid`.

### 20.6 Verification

Check:

- attachment continuity;
- penetration;
- temporal lag;
- energy decay;
- silhouette interference;
- face and product occlusion;
- continuity across cuts;
- consistency with virtual gravity and wind.

Secondary motion should not be used to hide failures in the primary body track.


<!-- RAG_CHUNK id="cpcs-mx-21" title="BVH, FBX, dense arrays, and canonical interchange" concepts="BVH, FBX, motion interchange, dense arrays, canonical JSON, provenance" evidence="ESTABLISHED,PROPOSED" -->
<a id="21-bvh-fbx-dense-arrays-and-canonical-interchange"></a>
## 21. BVH, FBX, dense arrays, and canonical interchange

CPCS-MX does not replace established animation files. It assigns them a narrower and more precise role. A motion-capture or DCC format carries geometry and animation data; a CPCS-MX score carries the **meaning, authority, constraints, evidence, and compilation policy** surrounding that data. The two should be linked rather than conflated.

### 21.1 BVH as a transparent skeletal-motion interchange

The BioVision Hierarchy format represents a joint hierarchy, static offsets, per-joint channels, a frame count, a frame time, and one row of channel values per frame. [S019] Its strengths are simplicity, portability, and human inspectability. For research agents, the format is also useful because an extractor can deterministically recover:

- hierarchy and parent-child structure;
- channel order;
- root translation;
- Euler rotations;
- sample cadence;
- a dense motion matrix.

Its limitations are equally important:

- the file generally does not declare a universal physical unit;
- coordinate handedness and up-axis are workflow conventions rather than guaranteed semantics;
- Euler channel order varies and must be preserved;
- there is no standard representation of contacts, force, torque, facial AUs, Laban qualities, camera intent, safety scope, or evidence provenance;
- a BVH hierarchy is not a complete character rig and may omit twist joints, fingers, facial joints, deformers, and constraints;
- bone length and joint topology may differ substantially from the target skeleton.

A CPCS-MX importer therefore wraps the raw motion in an explicit manifest:

```json
{
  "asset_id": "motion.bvh.reference_walk.001",
  "uri": "tracks/reference_walk.bvh",
  "media_type": "application/x-bvh",
  "sha256": "…",
  "declared_units": {
    "translation": "centimeter",
    "rotation": "degree"
  },
  "coordinates": {
    "handedness": "right",
    "up_axis": "+Y",
    "forward_axis": "+Z"
  },
  "rotation_channels": "preserve_source_order",
  "source_fps": 60,
  "import_transform": {
    "scale_to_meter": 0.01,
    "basis_change": "bvh_y_up_to_cpcs_y_up"
  }
}
```

The importer must verify the reconstructed global pose at selected frames. A file that parses without errors can still be misinterpreted by an incorrect Euler order, basis transform, or unit assumption.

### 21.2 FBX as a production container

FBX can carry skeletons, meshes, skin weights, animation curves, takes, cameras, lights, constraints, and scene transforms. Autodesk’s SDK exposes animation stacks, layers, curve nodes, and curves; DCC and engine importers add their own settings for units, axes, pre-rotations, root handling, and bake rates. [S020][S021] This makes FBX useful as a production interchange format but also creates hidden degrees of freedom.

A deterministic FBX intake process should record:

1. SDK or importer version;
2. source and target units;
3. axis conversion;
4. transform inheritance mode;
5. pre- and post-rotation handling;
6. animation stack and layer selection;
7. curve interpolation and tangent mode;
8. resampling rate;
9. constraint baking policy;
10. skeleton and mesh bind-pose hashes.

CPCS-MX should never infer that two FBX files are equivalent merely because they contain the same number of frames. Their evaluated global transforms must be compared after the same import policy.

### 21.3 Canonical score versus dense tracks

JSON is suitable for hierarchy, events, constraints, intervals, provenance, and references. It is inefficient for millions of floating-point samples. The recommended architecture is:

```text
canonical CPCS-MX JSON
├── project, characters, rigs, actions, phases, contacts
├── Laban, face, breath, mannerism, style, camera
├── hard/soft/perceptual constraints
├── track manifests and content hashes
└── references to dense assets

external track assets
├── root transforms
├── joint rotations
├── optional joint positions
├── velocities and accelerations
├── pose-confidence arrays
├── contact probabilities
├── dense facial coefficients
└── simulation caches
```

Dense arrays may be stored as NumPy-compatible arrays, HDF5, Arrow/Parquet columns, engine-native animation clips, or video control passes. The score must declare the encoding, shape, dtype, ordering, timebase, coordinate system, and checksum. The format is less important than explicit semantics and reproducibility.

```json
{
  "track_asset": {
    "asset_id": "track.joints.actor_a.take_03",
    "uri": "tracks/actor_a_take_03_rot6d.f32",
    "encoding": "raw_little_endian",
    "dtype": "float32",
    "shape": [721, 68, 6],
    "semantic": "local_joint_rotation_6d",
    "joint_order_ref": "rig.actor_a.joints.v4",
    "sample_rate_hz": 120,
    "interval": {"start_s": 0.0, "end_s": 6.0},
    "sha256": "…"
  }
}
```

Continuous 5D or 6D rotation representations can be preferable inside learned systems because they avoid representational discontinuities that create optimization difficulty; quaternions remain useful for storage and interpolation when sign continuity is enforced. [S006][S007] CPCS-MX permits multiple encodings but requires one declared canonical evaluation path.

### 21.4 Canonicalization pipeline

```text
BVH / FBX / engine clip / mocap stream
                 ↓
parse without semantic loss
                 ↓
normalize units and coordinate basis
                 ↓
map source joints to canonical semantic joints
                 ↓
resample only when necessary
                 ↓
compute global transforms and verification landmarks
                 ↓
externalize dense arrays
                 ↓
write canonical JSON manifest and provenance
```

The original asset remains immutable. Every conversion creates a new asset record linked through `derived_from`. Resampling, smoothing, foot-lock correction, retargeting, and manual edits are separate transformations with parameters and hashes.

### 21.5 Loss accounting

Every exporter should produce a loss report:

```yaml
loss_report:
  source: motion.fbx.take_03
  target: motion.bvh.take_03
  unsupported:
    - facial_blendshapes
    - animation_layers
    - constraints
    - camera
  baked:
    - control_rig_constraints
  resampled:
    from_hz: 120
    to_hz: 60
  maximum_global_joint_error_m: 0.0042
  maximum_root_orientation_error_deg: 0.18
```

The report is critical for agent workflows. Without it, an agent may retrieve a simplified BVH and incorrectly assume that it contains the full source performance.

### 21.6 Interchange verification

At minimum, verify:

- joint-name and parent mapping;
- bind/rest pose;
- root transform and facing;
- scale and limb lengths;
- global transforms at first, middle, last, and contact frames;
- left/right consistency;
- quaternion sign continuity or Euler unwrap;
- sample count and exact time span;
- event alignment after resampling;
- preserved locks and constraints;
- content hashes.

The expected output is not simply “import succeeded.” It is a quantified equivalence statement in a declared space.

<!-- RAG_CHUNK id="cpcs-mx-22" title="Procedural animation, motion matching, and engine execution" concepts="motion matching, root motion, control rig, procedural animation, runtime controller" evidence="ESTABLISHED,CURRENT_PLATFORM,PROPOSED" -->
<a id="22-procedural-animation-motion-matching-and-engine-execution"></a>
## 22. Procedural animation, motion matching, and engine execution

A CPCS-MX score can drive an offline DCC pipeline, but its architecture is also compatible with real-time character controllers. Game engines demonstrate how root motion, state, trajectory prediction, IK, animation databases, and procedural constraints can be composed at runtime. Current engine interfaces are version-dependent; the general control principles are more stable than any specific menu or node. [S011][S012][S013][S014][S015][S073]

### 22.1 Root-motion execution modes

A runtime adapter declares one of four root policies:

| Mode | Root trajectory authority | Typical use |
|---|---|---|
| `clip_driven` | animation clip | authored attacks, cinematic locomotion |
| `controller_driven` | navigation/gameplay controller | responsive gameplay |
| `constraint_driven` | contacts, target and optimization | exact staging or procedural traversal |
| `hybrid_warped` | clip plus trajectory warp | motion matching and target alignment |

In `clip_driven` mode, the root curve is extracted from the source animation and applied to the character or converted to an engine trajectory. In `controller_driven` mode, in-place animation follows a root commanded by the gameplay system. In `hybrid_warped` mode, the clip’s local qualities are retained while displacement, facing, and contact time are adjusted within declared limits.

Root policy must be explicit because it changes the meaning of every contact. A foot planted in the source clip can slide if a controller moves the capsule independently. A root-authoritative cinematic clip can collide with gameplay geometry unless the environment has been staged for it.

### 22.2 Motion matching as retrieval plus adaptation

Motion matching selects a pose or frame from a database by comparing the current state and desired future trajectory to feature vectors. A CPCS-MX adapter can compile fields into query features:

```text
current root velocity
current facing
current joint positions and velocities
support/contact state
desired future trajectory samples
desired facing samples
action tag
style/persona tag
Laban proxy values
```

The matching cost can be conceptualized as:

\[
C_i = w_p E_{pose,i} + w_v E_{velocity,i} + w_t E_{trajectory,i}
+ w_c E_{contact,i} + w_s E_{style,i} + w_a E_{action,i}.
\]

The weights are project parameters, not universal constants. A combat cinematic may prioritize contact and action tags; a background crowd controller may prioritize trajectory and continuity. Unreal’s current Motion Matching documentation illustrates a production implementation based on pose-search databases and query trajectories. [S011]

Motion matching is not deterministic solely because the query is structured. Determinism also depends on database version, feature normalization, tie-breaking, runtime state, and post-selection warping. CPCS-MX stores these in an execution manifest.

### 22.3 Procedural IK and full-body adjustment

IK is used for:

- foot placement on uneven ground;
- hand-to-prop alignment;
- gaze and head aiming;
- seating and bracing;
- target-aware reaches;
- combat staging and near-contact;
- retarget correction;
- camera-relative framing adjustments.

Full-body IK distributes error across a chain rather than moving a single end effector. Current Control Rig and Animation Rigging systems expose solvers, effectors, constraints, pole vectors, and per-bone settings. [S013][S015][S073] CPCS-MX represents the intent independently:

```json
{
  "ik_task": {
    "id": "ik.right_hand.prop_handle",
    "interval": [1.42, 2.87],
    "effector": "right_hand",
    "target": {"entity": "prop_sword", "socket": "grip"},
    "position_weight": 1.0,
    "orientation_weight": 0.85,
    "pole_target": "right_elbow_preferred_plane",
    "joint_limit_profile": "rig.actor_a.anatomical",
    "root_translation_limit_m": 0.06,
    "root_rotation_limit_deg": 4.0,
    "failure_policy": "report_and_hold_last_valid"
  }
}
```

The engine adapter maps this to the available solver. If no solver can satisfy it, the adapter must not silently move the prop or violate a locked contact.

### 22.4 Procedural locomotion and phase-conditioned control

PFNN conditions a locomotion model on a cyclic phase variable and user/environment controls, enabling terrain-adaptive character control. [S008] Local Motion Phases generalize the idea by learning asynchronous phase signals for multiple body parts in multi-contact actions. [S009] These works support a CPCS-MX distinction between:

- global gait phase;
- limb-local phase;
- action-event phase;
- contact state;
- presentation retime.

A procedural locomotion controller can consume desired speed, curvature, terrain samples, gait identity, and style profile. The output is then checked against hard constraints and character-specific preferences.

### 22.5 Physics-based controllers

DeepMimic demonstrates that a physics-based character can imitate reference motion while retaining some capacity to respond to perturbations. [S010] OpenSim Moco provides an optimal-control framework for musculoskeletal and movement problems. [S004] CPCS-MX does not prescribe one solver, but it can compile a score into a trajectory-optimization or reinforcement-learning objective:

\[
J = \sum_t \left(
 w_q E_q(t) + w_{\dot q}E_{\dot q}(t)
 + w_r E_{root}(t) + w_c E_{contact}(t)
 + w_e E_{effort}(t) + w_u\|u(t)\|^2
\right),
\]

subject to dynamics, joint limits, non-penetration, balance, and task constraints. Here, `effort` is an engineering proxy derived from the authored performance score—not an assertion that Laban theory is reducible to one physical cost.

### 22.6 Engine execution package

A runtime compiler may emit:

```text
character rig mapping
animation database or base clip IDs
root policy and trajectory
state-machine/action graph
phase and contact streams
IK tasks and priorities
motion-warp targets
physics profile
facial curves
secondary-motion profile
camera and VFX events
verification probes
```

The package includes a capability report. A target that supports only root trajectory and pose playback cannot claim to execute torque constraints or Laban fields natively; those fields must be approximated through retrieval, curve shaping, or offline generation.

### 22.7 Verification checkpoints

At runtime or in recorded replays, measure:

- root deviation from desired trajectory;
- transition discontinuity;
- contact timing and foot slip;
- IK residual;
- joint-limit violations;
- collision penetration;
- action-state sequence;
- phase continuity;
- frame-time dependence;
- deterministic replay under a fixed seed and database hash.

The engine is an execution target, not the semantic source of truth.

<!-- RAG_CHUNK id="cpcs-mx-23" title="AI motion synthesis and controllable video generation" concepts="text-to-motion, diffusion, joint control, interaction, trajectory guidance, video generation" evidence="CURRENT_RESEARCH,EMERGING,PROPOSED" -->
<a id="23-ai-motion-synthesis-and-controllable-video-generation"></a>
## 23. AI motion synthesis and controllable video generation

AI motion systems occupy different points in the control stack. Some generate 3D skeletal motion from text. Others edit selected joints or time ranges. Others generate interactions or human-object contacts. Video models may consume text, reference images, trajectories, pose sequences, or latent-space controls. CPCS-MX treats these as adapters with declared capability matrices rather than as interchangeable “AI animation” tools.

### 23.1 Text-to-motion priors

Motion Diffusion Model applies diffusion to human motion and supports tasks such as text-conditioned generation and motion completion. [S051] MotionGPT formulates motion as a language-like sequence and unifies multiple motion tasks through a text-motion representation. [S052] MoMask uses masked modeling for generative human motion. [S062] HumanML3D provides a widely used text-motion dataset and representation for this research line. [S065]

These systems are useful for producing a plausible base motion from semantic intent. Their text descriptions generally do not encode every frame-level constraint. A CPCS-MX compiler can therefore use them in a staged process:

```text
textual intent and action graph
→ base motion proposal
→ joint/contact/phase guidance
→ retargeting and IK
→ physics or constraint refinement
→ presentation compilation
```

The generated motion remains a candidate until it passes score-based verification.

### 23.2 Fine-grained spatial and temporal control

FineMoGen targets fine-grained spatiotemporal instruction following. [S053] OmniControl adds control over arbitrary joints at arbitrary times. [S054] StickMotion uses a drawn stick figure as an explicit movement control. [S057] These directions align with CPCS-MX because the score can compile selected fields into sparse or dense control conditions:

- pelvis positions at phase boundaries;
- right-wrist target at a contact time;
- both feet locked during a support interval;
- head orientation toward a gaze target;
- key-pose skeletons at storyboard frames;
- free generation for unspecified joints and intervals.

A crucial design rule is **minimum necessary constraint**. Overconstraining every joint at every frame can force unnatural interpolation and remove the motion prior’s ability to coordinate the body. Underconstraining contact-critical moments produces drift. The compiler should classify constraints as locked, guided, preferred, or free.

### 23.3 Interaction generation

InterControl controls joint relationships for human-human interaction. [S055] CG-HOI uses contact guidance for human-object interaction. [S056] These approaches motivate explicit relation tracks:

```json
{
  "relation": {
    "id": "rel.actor_a_hand.actor_b_guard",
    "interval": [2.06, 2.42],
    "source": "actor_a.right_hand",
    "target": "actor_b.left_forearm",
    "relation_type": "staged_near_contact",
    "distance_curve_m": [[2.06,0.42],[2.31,0.018],[2.42,0.31]],
    "locked_event": {"type":"minimum_distance","time_s":2.31},
    "collision_policy": "no_penetration"
  }
}
```

This is more informative than independent prompts saying “A punches” and “B blocks.” The relation defines causal synchronization and gives a verifier an observable target.

### 23.4 Style, persona, and body-part control

Motion Puzzle supports body-part-aware motion style transfer. [S061] MotionPersona explores characteristic-aware locomotion. [S060] These works reinforce the need to separate:

- action content;
- body-part style;
- character persona;
- morphology;
- global genre transform.

A character may retain a habitual narrow stance and protective shoulder posture while the production switches from photorealistic UGC to feature-animation timing. Style should not erase persona unless an explicit override says so.

### 23.5 Event alignment

AToM focuses on event-level alignment between text and generated motion. [S063] CPCS-MX uses event nodes as an intermediate layer between sentences and frames:

```text
"she hesitates, commits, then catches the falling cup"

hesitation onset
→ gaze shift
→ hand preparation
→ commitment threshold
→ reach acceleration
→ grasp contact
→ object stabilization
→ breath release
```

The event graph provides a retrieval and evaluation unit. It also allows agents to revise one beat without regenerating an entire sequence.

### 23.6 Motion control in video generation

MotionCtrl separates camera and object-motion controls in video generation. [S066] TokenMotion and Wan-Move represent emerging work on disentangled or trajectory-guided motion control for human-centric and general video generation. [S058][S059] Their exact interfaces and production readiness may change, but they illustrate a broader architecture: **text is only one condition among trajectories, camera signals, reference appearance, and temporal control**.

A CPCS-MX video adapter may emit:

- narrative prompt;
- actor and wardrobe reference images;
- per-frame 2D or 3D pose control;
- root or selected-point trajectories;
- masks and identity regions;
- depth or normal passes;
- camera trajectory;
- first/last/key frames;
- optical-flow or motion-field priors;
- effect and edit instructions;
- generation seed and sampler parameters.

The adapter reports which score fields were natively conditioned, approximated in prose, implemented in pre/postproduction, or ignored.

### 23.7 A fidelity ladder

| Tier | Executable carrier | Expected fidelity |
|---|---|---|
| 0 | text only | broad semantics and style |
| 1 | text plus reference images | appearance and broad motion |
| 2 | text plus key poses/frames | stronger composition and pose milestones |
| 3 | dense pose or trajectory control | stronger screen-space choreography |
| 4 | rigged 3D animation plus control renders | editable, repeatable motion and camera |
| 5 | rig/simulation plus constrained video render | highest practical structural fidelity |

No tier guarantees pixel identity. “Exact” is assessed against declared metrics and tolerances.

### 23.8 Model capability negotiation

The compiler interrogates or configures a capability matrix:

```json
{
  "target": "video_adapter.example.v2",
  "supports": {
    "text": true,
    "reference_images": 4,
    "pose_video": true,
    "camera_trajectory": false,
    "point_trajectories": 8,
    "mask_sequence": true,
    "seed": true,
    "duration_s": [2,10]
  },
  "fallbacks": {
    "camera_trajectory": "render_into_control_video",
    "laban": "compile_to_motion_and_text",
    "facs": "compile_to_face_curve_then_reference_video"
  }
}
```

This prevents format theater: the presence of a detailed JSON field does not mean the target model can execute it.

### 23.9 Closed-loop generation

```text
resolved CPCS-MX score
→ target controls
→ candidate generation
→ re-extract pose, contacts, camera, face, timing
→ compare with score
→ localize error
→ modify control or regenerate interval
```

The loop converts generative video from one-pass prompting into measured iteration. The verifier must use the same coordinate and clock conventions as the score.

<!-- RAG_CHUNK id="cpcs-mx-24" title="Text-to-CPCS-MX compilation" concepts="natural language, semantic parsing, ambiguity, compiler, agent workflow" evidence="PROPOSED,OPERATIONALIZATION" -->
<a id="24-text-to-cpcs-mx-compilation"></a>
## 24. Text-to-CPCS-MX compilation

Natural language remains the most accessible directorial interface. The problem is not that prose is useless; it is that prose under-specifies time, geometry, authority, and conflict resolution. A text-to-CPCS-MX compiler should preserve the expressive advantages of language while refusing to fabricate precision that the director did not provide.

### 24.1 Compilation stages

```text
source request
→ discourse and shot segmentation
→ entity and role resolution
→ action/event graph induction
→ temporal relation extraction
→ performance-quality extraction
→ camera/VFX/marketing extraction
→ ambiguity and feasibility analysis
→ schema population
→ constraint synthesis
→ model-specific compilation
```

Each stage emits provenance and confidence. An LLM may propose action labels or timing intervals; a deterministic validator checks schema, units, references, and contradictions.

### 24.2 Separate intent from implementation

Consider:

> She crosses the room as if trying not to wake anyone, hears the latch, freezes, then turns with controlled fear.

A compiler should first recover intent and events:

```yaml
intent:
  objective: cross without detection
  obstacle: uncertain sound behind her
  subtext: fear is actively suppressed

events:
  - quiet_locomotion
  - auditory_trigger
  - freeze
  - gaze_lead
  - controlled_turn
```

Only then should it propose implementation:

```yaml
implementation_candidates:
  quiet_locomotion:
    root_speed_mps: [0.55, 0.75]
    laban:
      weight: light
      time: sustained
      space: direct
      flow: bound
    contacts:
      footfall_impulse_scale: low
  freeze:
    duration_s: null
    status: requires_director_or_style_default
```

The missing freeze duration is not invented as a fact. The compiler can offer candidates based on a style profile, but the selected value is labeled `authored_by_compiler` or `defaulted`.

### 24.3 Lexicon without rigidity

A reusable lexicon maps language to candidate modules:

| Phrase | Candidate action/performance mapping |
|---|---|
| “steps into range” | `step_in` plus target-distance constraint |
| “snaps her head around” | head yaw event, sudden Time, bounded overshoot |
| “floats down” | reduced descent acceleration or presentation retime, light Weight |
| “barely reacts” | reduced reaction amplitude, delayed or suppressed face/body response |
| “lands heavily” | contact event, high virtual impulse cue, strong Weight, secondary settling |
| “nervous energy” | elevated micro-movement rate, gaze shifts, breath variability, bounded fidgets |

The lexicon is probabilistic and context-sensitive. “Heavy” may refer to body mass, perceived Weight, impact sound, animation timing, or emotional tone. The compiler asks which domain is intended when ambiguity affects execution; in batch mode, it preserves alternatives.

### 24.4 Temporal language

Natural-language temporal relations can be compiled into a partial-order graph:

```text
before, after, during, overlaps, starts_with,
ends_with, meets, contains, immediately_after
```

Example:

```json
{
  "temporal_relations": [
    {"a":"gaze_shift","relation":"before","b":"head_turn"},
    {"a":"exhale","relation":"overlaps","b":"effort_peak"},
    {"a":"impact_flash","relation":"starts_with","b":"near_contact"},
    {"a":"recoil","relation":"immediately_after","b":"near_contact",
     "tolerance_s":0.08}
  ]
}
```

A scheduler assigns times subject to duration ranges, locks, and target shot length. If the graph is inconsistent, the compiler returns the minimal conflict set instead of choosing silently.

### 24.5 Numeric grounding

Numbers in prompts require units and scope:

```text
“move two meters”
→ root displacement in declared world coordinates

“turn 90 degrees”
→ root yaw or named joint rotation?

“hold for six frames”
→ six exposures at which frame rate and retime policy?

“30% stronger”
→ which observable: speed, acceleration, reaction, VFX, sound, or simulated impulse?
```

The compiler normalizes quantities to SI internally while retaining the author’s expression. It does not translate “30% stronger” into a real-world torque without an explicit virtual-dynamics model.

### 24.6 Director-facing questions and defaults

For interactive authoring, ambiguity is best resolved through targeted questions. For autonomous batch generation, the compiler uses named defaults:

```yaml
default_resolution:
  profile: cinematic_human_v2
  freeze_duration_s: 0.45
  gaze_lead_s: 0.12
  contact_mode: staged_near_contact
  uncertainty_policy: preserve_alternatives
```

Defaults are versioned and included in the final manifest. An agent can reproduce the score only if it knows the default profile.

### 24.7 Text-to-structure output contract

The LLM should return a candidate document with:

- schema version;
- source text spans supporting each field;
- evidence class;
- confidence;
- unresolved terms;
- alternatives;
- requested external assets;
- safety scope;
- no undeclared fields.

The candidate is validated, normalized, and resolved by deterministic code. This division uses the LLM for semantic interpretation and ordinary software for contract enforcement.

### 24.8 Reverse compilation to text

Many video systems still accept prose. The resolved score can be summarized into a model-specific prompt, but the compiler must distinguish **lossless controls** from **textual fallbacks**. A generated prompt might state:

> Low-angle medium-wide shot. The protagonist plants the left foot, advances 0.8 m, rotates the pelvis before the torso, and extends the right arm toward a staged near-contact at 2.31 s. Movement is strong, sudden, direct, and bound; the opponent’s recoil begins within two frames. Preserve left-to-right screen direction.

The exact curves remain in the pose, trajectory, or rig controls. The prose is a semantic reinforcement, not the sole carrier of timing.

<!-- RAG_CHUNK id="cpcs-mx-25" title="Canonical schema design" concepts="JSON Schema, canonical JSON, track objects, intervals, events, constraints" evidence="STANDARD,PROPOSED" -->
<a id="25-canonical-schema-design"></a>
## 25. Canonical schema design

The canonical representation is JSON validated by JSON Schema Draft 2020-12. JSON provides interoperable objects, arrays, numbers, strings, booleans, and null; JSON Schema provides reusable definitions, conditional validation, references, and machine-readable contracts. [S076][S077] YAML may author the same data model, but canonicalization removes YAML aliases, implicit typing, comments, and formatting choices before hashing. [S079]

### 25.1 Design principles

1. **Every number has a semantic field and declared unit.**
2. **Temporal order is represented by arrays and timestamps, not object-member order.**
3. **Dense arrays are external assets with shapes and hashes.**
4. **Evidence and authoring status are explicit.**
5. **Hard constraints are distinct from preferences.**
6. **Style transformation is distinct from anatomical motion.**
7. **Character, rig, and performer identity are separate entities.**
8. **Coordinate systems are referenced, not assumed.**
9. **Derived values record their derivation method.**
10. **Unsupported target capabilities create reports, not silent omissions.**

### 25.2 Top-level structure

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "schema_id": "urn:cpcs-mx:schema:1.0",
  "document_id": "score.project_001.sequence_004",
  "timebase": {},
  "coordinate_systems": [],
  "assets": [],
  "characters": [],
  "rigs": [],
  "style_profiles": [],
  "shots": [],
  "constraints": [],
  "verification_plan": {},
  "provenance": {},
  "extensions": {}
}
```

### 25.3 Track object

A uniform track contract reduces parser complexity:

```json
{
  "track_id": "track.actor_a.root.position",
  "semantic": "root_translation",
  "subject_ref": "actor_a",
  "coordinate_system_ref": "world_stage",
  "unit": "meter",
  "authority": "locked",
  "representation": {
    "type": "keyframes",
    "interpolation": "cubic_hermite",
    "keys": [
      {"t":0.0,"value":[0.0,0.0,0.0]},
      {"t":1.2,"value":[0.0,0.0,0.8]}
    ]
  },
  "evidence": {
    "class": "authored",
    "source_refs": ["director.note.17"],
    "confidence": 1.0
  }
}
```

Allowed representations can include `constant`, `keyframes`, `sampled_inline`, `external_asset`, `procedural`, and `derived`. Each has different required fields.

### 25.4 Interval object

Intervals use explicit boundaries and optional fades:

```json
{
  "interval_id": "effort.actor_a.attack_phrase",
  "start_s": 1.20,
  "end_s": 2.55,
  "boundary_semantics": "half_open",
  "fade_in_s": 0.12,
  "fade_out_s": 0.18
}
```

An interval does not imply constant values. It can reference curves or subphrases.

### 25.5 Event object

```json
{
  "event_id": "event.near_contact.001",
  "type": "staged_near_contact",
  "time_s": 2.31,
  "participants": [
    {"entity_ref":"actor_a","site":"right_hand"},
    {"entity_ref":"actor_b","site":"head_target_volume"}
  ],
  "tolerance_s": 0.0417,
  "hard": true,
  "payload": {
    "minimum_distance_m": 0.018,
    "no_penetration": true,
    "camera_cheat_allowed": true
  }
}
```

Events may occur at a point or over an interval. A point event can link to audio, facial, VFX, and reaction events through temporal relations.

### 25.6 Laban object

```json
{
  "laban_control": {
    "interval_ref": "interval.attack_phrase",
    "effort": {
      "weight": {"pole":"strong","intensity":0.88},
      "time": {"pole":"sudden","intensity":0.93},
      "space": {"pole":"direct","intensity":0.90},
      "flow": {"pole":"bound","intensity":0.72}
    },
    "shape": {
      "vertical":"rising",
      "sagittal":"advancing",
      "horizontal":"spreading"
    },
    "phrasing": {
      "pattern":"increasing_then_impulsive_then_decreasing",
      "peak_event_ref":"event.near_contact.001"
    },
    "status":"authored_descriptor",
    "computational_proxy_profile":"laban_proxy.production_v3"
  }
}
```

The descriptor and its computational proxy are separate. This avoids claiming that a specific velocity threshold is the universal meaning of `sudden`.

### 25.7 Face, gaze, and breath objects

```json
{
  "facial_event": {
    "event_id":"face.actor_a.strain.001",
    "interval":[2.08,2.44],
    "action_units":[
      {"au":"AU04","side":"bilateral","curve_ref":"curve.au04.001"},
      {"au":"AU07","side":"bilateral","curve_ref":"curve.au07.001"},
      {"au":"AU23","side":"bilateral","curve_ref":"curve.au23.001"}
    ],
    "gaze_target_ref":"actor_b.head",
    "blink_policy":"suppress_during_target_acquisition",
    "evidence_class":"authored"
  },
  "breath_phrase": {
    "interval":[1.50,3.20],
    "phase_events":[
      {"type":"exhale_on_effort","time_s":2.18},
      {"type":"recovery_inhale","time_s":2.74}
    ],
    "thorax_amplitude":0.42,
    "audio_ref":"breath.actor_a.take_02"
  }
}
```

### 25.8 Constraint object

```json
{
  "constraint_id":"constraint.foot_lock.left.001",
  "scope":{"subject_ref":"actor_a","interval":[1.10,1.86]},
  "type":"contact_lock",
  "site":"left_foot",
  "target":{"entity_ref":"stage_floor","region":"support_patch_02"},
  "priority":"hard",
  "tolerances":{
    "horizontal_slip_m":0.015,
    "vertical_error_m":0.008,
    "orientation_error_deg":3.0
  },
  "failure_policy":"reject_candidate"
}
```

Perceptual constraints can use project-defined metrics:

```json
{
  "constraint_id":"constraint.silhouette.contact_pose",
  "type":"perceptual_metric",
  "priority":"soft",
  "metric":"limb_separation_ratio",
  "event_ref":"event.near_contact.001",
  "minimum":0.65,
  "view_ref":"camera.shot_07"
}
```

The metric definition and calibration dataset must be versioned.

### 25.9 Extension namespacing

Projects may add fields under explicit namespaces:

```json
{
  "extensions": {
    "urn:studio.example:anime-effects:1": {
      "smear_shape_library":"smears.v7",
      "impact_palette":"white_red_black"
    }
  }
}
```

Unrecognized extensions are retained but not executed unless the target adapter declares support.

### 25.10 Versioning and migration

Schema versions follow explicit migrations:

```text
1.0 → 1.1
rename `physics_scale` to `virtual_physics_profile`
split scalar `style_intensity` into typed transformation dimensions
preserve old value in migration provenance
```

A migration cannot silently reinterpret a number. It must define how old semantics map to new fields and emit warnings where equivalence is impossible.


<!-- RAG_CHUNK id="cpcs-mx-26" title="Constraint resolution and compilation" concepts="constraint solver, merge precedence, locks, feasibility, target adapters" evidence="ESTABLISHED,PROPOSED,OPERATIONALIZATION" -->
<a id="26-constraint-resolution-and-compilation"></a>
## 26. Constraint resolution and compilation

A score becomes executable only after inheritance, references, conflicts, and target capabilities have been resolved. The compiler is therefore not a serializer. It is a typed constraint-resolution system that produces an execution package and an auditable loss report.

### 26.1 Scope cascade

CPCS-MX permits defaults and overrides at multiple scopes:

```text
studio
→ production
→ sequence
→ scene
→ shot
→ beat
→ action
→ event
→ frame/sample
```

Specificity alone is not sufficient. A lower scope cannot override a locked higher-scope safety or identity rule unless the authority policy explicitly permits it. The effective precedence tuple is:

\[
P = (\text{authority},\; \text{lock},\; \text{specificity},\; \text{revision},\; \text{source order}).
\]

`source order` is a final deterministic tie-breaker, not a substitute for meaningful precedence.

### 26.2 Typed merge behavior

Different values require different merge operations:

| Type | Default operation | Example |
|---|---|---|
| scalar setting | replace | gravity profile |
| object | recursive merge | cinematography profile |
| keyed entity array | merge by stable ID | actions, constraints |
| ordinary ordered array | replace or append by policy | prompt clauses |
| numerical curve | splice/blend/replace interval | AU intensity |
| interval descriptor | interval algebra | Laban phrase |
| hard constraint | union, then feasibility check | foot lock plus hand target |
| asset reference | replace with provenance | character reference |
| lock | monotonic unless authorized unlock | contact frame |

A generic deep-merge library is insufficient. It may append duplicate constraints, merge incompatible coordinate systems, or overwrite one temporal key without recomputing interpolation.

### 26.3 Curve composition

Suppose a production profile supplies a baseline breathing curve, a shot profile raises arousal, and an action event adds an effort exhale. The final curve can be composed as:

\[
b(t)=\operatorname{clamp}\left(b_0(t)+a_{shot}(t)+e_{action}(t),\;b_{min},\;b_{max}\right),
\]

but only if all three tracks declare additive semantics. A root-position curve would not normally be composed this way. Curve fields specify:

- operation: `replace`, `add`, `multiply`, `max`, `min`, `blend`, `warp_time`;
- interval;
- blend envelope;
- unit;
- coordinate frame;
- priority;
- whether the operation is commutative.

### 26.4 Constraint graph

The compiler builds a graph whose nodes are variables, tracks, events, and assets. Edges express:

- equality or inequality;
- temporal relation;
- geometric relation;
- dependency;
- derivation;
- authority;
- mutual exclusion.

Example:

```text
left-foot lock ─────┐
                    ├→ pelvis and leg IK solution
right-hand target ──┤
                    ├→ full-body residual
joint limits ───────┤
root path lock ─────┘
```

If the target is unreachable without moving a locked root or violating joint limits, the compiler reports an infeasible set. It can suggest alternatives—move the target, allow a root adjustment, use stylized deformation, or reduce the lock—but it must not silently choose.

### 26.5 Hard and soft solving

A common formulation is:

\[
\min_x \sum_i w_i E_i(x)
\quad \text{subject to} \quad
h_j(x)=0,\quad g_k(x)\le 0,
\]

where hard contacts, non-penetration, and locked events become constraints, while pose fidelity, smoothness, style, and energy become weighted objectives. OpenSim IK and inverse-dynamics workflows illustrate established optimization and residual concepts in movement analysis, while interactive spacetime constraints and full-body IK illustrate related animation approaches. [S001][S002][S049][S073]

CPCS-MX adds a policy layer around the solver:

```yaml
solve_policy:
  hard_failure: reject
  soft_failure: emit_metric
  max_iterations: 100
  deterministic_seed: 4117
  priority_order:
    - safety_and_nonpenetration
    - locked_contact
    - locked_event_time
    - root_path
    - key_pose
    - joint_style
    - smoothness
    - secondary_motion
```

### 26.6 Anatomical, rig, and virtual constraints

Three joint-limit profiles may coexist:

1. `anatomical_reference`: a documented human range or research model;
2. `rig_safe`: the transform range that preserves the specific character mesh and deformation;
3. `virtual_stylized`: a deliberately nonhuman range permitted in the stylization layer.

The active limit is selected per interval and per layer. The skeleton solver should not exceed `rig_safe` merely because a `virtual_stylized` deformation allows the rendered silhouette to stretch farther. That stretch can be implemented through mesh deformation, camera perspective, smear geometry, or a separate nonhuman rig.

### 26.7 Compilation passes

A recommended compiler executes these passes:

1. Parse YAML/JSON/XML authoring inputs.
2. Resolve includes and stable references.
3. Normalize types, units, clocks, and coordinate systems.
4. Expand profiles and inheritance.
5. Apply authority and lock rules.
6. Build event and constraint graphs.
7. Detect temporal and geometric conflicts.
8. Resolve or report feasibility.
9. Generate or import dense base motion.
10. Apply retargeting and IK.
11. Apply style and superhuman transforms under invariants.
12. Generate face, gaze, breath, and secondary tracks.
13. Compile camera, audio, VFX, and edit events.
14. Negotiate target capabilities.
15. Emit target package, loss report, and verification plan.

Each pass writes an immutable intermediate artifact with a hash when reproducibility is required.

### 26.8 Compilation products

The same resolved score can produce different packages:

```text
DCC package:
FBX/scene + rig curves + contacts + camera + notes

engine package:
animation clips + root trajectory + state/action graph + IK tasks

text-to-motion package:
action prompt + event tokens + sparse joint constraints

video package:
prompt + references + pose/depth/mask controls + camera render

RAG package:
semantic chunks + field docs + examples + source records
```

A target adapter declares a coverage matrix:

```json
{
  "field":"shots[].beats[].laban_control.effort.weight",
  "status":"approximated",
  "method":"motion_retrieval_and_velocity_shaping",
  "loss":"qualitative descriptor not natively supported",
  "verification_metrics":["effort_proxy_weight_v3"]
}
```

### 26.9 Deterministic build identity

A build identity should include:

- canonical score hash;
- dense asset hashes;
- compiler version and commit;
- profile versions;
- model and adapter version;
- solver settings;
- random seeds;
- platform-dependent settings;
- capability report;
- unresolved warnings.

Without this identity, “same prompt” is not a reproducible specification.

<!-- RAG_CHUNK id="cpcs-mx-27" title="Verification and perceptual evaluation" concepts="verification, trajectory error, contact, smoothness, silhouette, human evaluation" evidence="ESTABLISHED,PROPOSED,OPERATIONALIZATION" -->
<a id="27-verification-and-perceptual-evaluation"></a>
## 27. Verification and perceptual evaluation

Verification asks whether an executed clip satisfies the score—not whether it is generically attractive. A candidate can look polished while reversing action order or missing a contact. Another can satisfy joint tracks but appear mechanical because breath, gaze, phase, and weight transfer are wrong. CPCS-MX uses a vector of metrics and never collapses all quality into one unexplained score.

### 27.1 Clock and event metrics

For event \(e\):

\[
E_{time}(e)=|t_e^{out}-t_e^{target}|.
\]

For an interval, compare start, end, duration, and overlap. For event order, compute a partial-order violation count. Report in seconds and source frames.

```json
{
  "metric":"contact_time_error",
  "event_ref":"event.near_contact.001",
  "target_s":2.310,
  "observed_s":2.352,
  "error_s":0.042,
  "error_frames_at_24fps":1.01,
  "pass":false,
  "threshold_s":0.025
}
```

### 27.2 Root and joint errors

For global joint positions:

\[
E_{joint}=\frac{1}{TJ}\sum_{t,j}
\|p^{out}_{t,j}-p^{target}_{t,j}\|_2.
\]

Also report per-joint percentiles and normalize by body height when comparing differently sized characters. Rotation error uses geodesic angular distance rather than component-wise Euler subtraction.

Root metrics include:

- positional trajectory error;
- facing/yaw error;
- speed and acceleration profile error;
- path curvature error;
- phase-boundary displacement;
- screen-space trajectory after camera projection.

For stylized transfer, world-space error may be allowed while screen-space silhouette and event timing remain locked.

### 27.3 Contact and support metrics

During a declared planted contact:

\[
E_{slip}=\sum_{t\in C}
\|\Pi_{ground}(p_t-p_{t-1})\|_2.
\]

Also measure vertical penetration, orientation drift, contact duration, minimum inter-actor distance, and support-polygon relation to a center-of-mass proxy. Foot-skating evaluation is established as an important animation-quality concern, but implementations vary; the metric definition must be packaged with the result. [S069]

### 27.4 Smoothness without over-smoothing

Jerk-based and spectral smoothness measures can identify discontinuity or fragmented motion, but smoothness is task dependent. A strike, stumble, or impact is not supposed to have the same velocity profile as a gentle reach. Reviews of movement smoothness caution that metrics have different assumptions and sensitivities. [S067][S068]

CPCS-MX therefore evaluates smoothness within labeled phases:

```text
preparation: continuity and low unintended jitter
execution: intended acceleration profile
contact: allowed discontinuity or impulse cue
recovery: controlled decay and balance restoration
```

A filter that lowers global jerk by erasing an impact peak is a failure, not an improvement.

### 27.5 Dynamics plausibility

When a virtual dynamics model is present, evaluate:

- residual forces and moments;
- ground-reaction consistency;
- momentum change around contact;
- actuator or torque limits;
- center-of-mass behavior;
- energy injection and dissipation;
- balance recovery.

Inverse-dynamics results are model-dependent and require declared coordinate and reporting conventions. [S002][S005] For monocular reference video, dynamics are usually hypotheses or virtual design parameters, not measurements.

### 27.6 Laban and performance compliance

Laban compliance can be assessed through a mixture of expert annotation, learned classifiers, and project-specific proxies. Possible proxy features include:

- acceleration onset for Time;
- path straightness or target deviation for Space;
- impulse, deceleration, and support loading for Weight;
- movement continuation and restraint for Flow;
- body-volume and directional expansion for Shape.

The report must state `proxy_profile_id`, calibration data, and confidence. It should not say “Laban score 0.87” without explaining what was measured.

### 27.7 Face, gaze, and breath compliance

Measure:

- AU onset, apex, offset, side, and amplitude;
- head-pose curve;
- gaze-target agreement;
- blink timing;
- lip/jaw synchronization where speech is present;
- thorax and shoulder breath proxy;
- breath-audio alignment;
- facial visibility and detector confidence.

FACS describes observable facial actions; emotion interpretation remains separate. [S031][S032][S033]

### 27.8 Perceptual and cinematic metrics

Useful project-defined measures include:

- silhouette separation of key limbs;
- contact readability;
- actor overlap ratio;
- screen-direction continuity;
- target visibility before and at contact;
- face or product visibility duty cycle;
- camera-motion readability;
- impact-frame detectability;
- visual center stability;
- secondary-motion occlusion.

These are operational metrics, not universal artistic laws. They should supplement expert review.

### 27.9 Human evaluation protocol

A controlled study can ask trained and untrained raters separate questions:

1. Is the intended action identifiable?
2. Does the character appear balanced and weighted?
3. Is the movement quality consistent with the descriptor?
4. Is the character’s mannerism consistent across clips?
5. Is the contact or near-contact readable?
6. Does stylization preserve action causality?
7. Does the clip look natural, intentionally stylized, or accidentally broken?

Randomize order, blind system identity, include repeated items for reliability, and report confidence intervals. Do not combine all questions into one preference score unless the research question specifically requires it.

### 27.10 Re-extraction and error localization

The output clip is processed by the same observation stack used for references:

```text
video
→ shot/clock analysis
→ entity tracking
→ pose and face extraction
→ camera-motion estimation
→ contact/event inference
→ score alignment
→ metric vector
```

Error is localized to a layer:

```text
semantic action correct; contact 3 frames late
root path correct; right wrist arc incorrect
body motion correct; camera reverses screen direction
joint motion correct; Laban phrasing too sustained
contact correct; facial strain begins too early
```

This diagnosis determines whether to revise text, a trajectory, an IK constraint, a style transform, or presentation.

<!-- RAG_CHUNK id="cpcs-mx-28" title="Cross-style modular switching" concepts="natural, UGC, feature animation, anime, superhuman, style transform" evidence="ESTABLISHED,PROPOSED" -->
<a id="28-cross-style-modular-switching"></a>
## 28. Cross-style modular switching

A strong motion representation should support style changes without rebuilding the causal action from scratch. CPCS-MX models style as a typed transformation from a neutral or source score to a target score, subject to invariants.

### 28.1 Content, performance, and presentation separation

```text
action content:
walk toward target → stop → turn → reach

performance:
hesitant, direct, bound, protective posture

style transform:
natural UGC / feature animation / anime / superhuman

presentation:
handheld close shot / locked wide / impact montage
```

Mixing these layers in a single `style_intensity` scalar makes controlled transfer impossible. CPCS-MX may expose a convenience scalar, but it expands into named dimensions.

### 28.2 Style transformation vector

```json
{
  "style_transform": {
    "source_profile":"natural_human",
    "target_profile":"anime_sakuga_action",
    "dimensions": {
      "timing_compression":1.35,
      "anticipation_expansion":1.20,
      "key_pose_hold_frames":2,
      "arc_exaggeration":1.18,
      "silhouette_separation":1.25,
      "secondary_overlap":1.15,
      "microvariation":0.45,
      "graphic_smear":0.80,
      "impact_frame":1.0,
      "camera_emphasis":1.25
    },
    "invariants":[
      "action_order",
      "support_contact_sequence",
      "target_identity",
      "screen_direction",
      "recovery_completion"
    ]
  }
}
```

Values are project controls, not standardized perceptual units.

### 28.3 Natural human profile

A natural profile favors:

- physically plausible weight transfer;
- moderate asymmetry;
- low-amplitude postural sway;
- gaze that often leads reaching and navigation;
- respiratory and speech coupling;
- small balance corrections;
- nonuniform but coherent timing;
- realistic joint and rig limits;
- limited camera/VFX compensation.

Natural does not mean smooth everywhere. Human movement includes intermittent corrections, impacts, hesitations, and task-specific variability.

### 28.4 High-fidelity UGC profile

A UGC profile may add:

- direct lens address;
- performer-operated or lightly stabilized camera motion;
- self-framing corrections;
- speech gesture alignment;
- product handling constraints;
- pauses for captions or proof;
- imperfect but intentional transitions;
- continuity of personal mannerisms;
- visibility requirements for face, hands, and product.

The profile should not manufacture “authenticity” as random jitter. It models plausible capture conditions and performer behavior.

### 28.5 Feature-animation profile

Feature animation can emphasize established animation principles such as anticipation, staging, follow-through, overlapping action, arcs, timing, exaggeration, and appeal. [S070][S071] CPCS-MX expresses these as measurable or inspectable transformations:

- anticipation duration and amplitude;
- silhouette target at key poses;
- overshoot and settle curves;
- staggered secondary-motion phases;
- controlled squash/stretch or mesh deformation;
- camera staging and visual hierarchy.

“Appeal” is not reduced to a number; it remains an artistic evaluation supported by clarity metrics.

### 28.6 Anime and limited-animation profile

Anime may intentionally use:

- held drawings;
- low or variable exposure cadence;
- abrupt timing changes;
- extreme perspective;
- smear drawings;
- repeated impact frames;
- background motion replacing body motion;
- visual abstraction and effects;
- off-model deformation at selected frames.

Cartoon capture and artist-directed dynamics show that stylized source motion can be structurally transferred or physically guided while preserving designed qualities. [S045][S046][S080] The executable carrier may be key drawings and exposure timing rather than a continuous anatomically valid trajectory.

### 28.7 Superhuman profile

Superhuman motion changes declared virtual rules:

```yaml
virtual_physics:
  gravity_scale_by_phase:
    launch: 1.0
    aerial_hold: 0.35
    descent: 0.75
  propulsion_impulse_scale: 2.2
  drag_scale: 0.4
  landing_response_scale: 1.5

stylized_deformation:
  reach_extension_scale: 1.15
  perspective_extension_scale: 1.25
  rig_joint_limit_override: false

presentation:
  anticipation_time_scale: 1.25
  execution_time_scale: 0.55
  recovery_time_scale: 1.10
  impact_hold_frames: 1
```

The transform states where energy enters the system and how it is visually communicated. “Momentum-defying pivot” can be authored as a virtual external impulse, a time warp, a camera transformation, or a graphic discontinuity; these have different implications and should not share one field.

### 28.8 Cross-style invariants

Recommended invariants include:

- action identity and order;
- participant and target identity;
- support/contact topology;
- safety classification of staged interactions;
- shot purpose;
- critical gaze or product visibility;
- start/end narrative state;
- locked dialogue and audio events;
- rights and identity replacements.

Style-specific deviations are then explainable. A two-frame anime hold may change continuous timing while preserving the contact event and narrative beat.

### 28.9 Style ablation

To test a style profile, generate the same action with one dimension changed at a time:

```text
base action
+ anticipation only
+ key-pose holds only
+ arc exaggeration only
+ microvariation only
+ VFX only
+ full profile
```

This identifies which controls actually produce the perceived style and which merely add noise.

<!-- RAG_CHUNK id="cpcs-mx-29" title="Agent architecture and RAG ingestion" concepts="RAG, agents, JSONL, retrieval, provenance, tool architecture" evidence="STANDARD,PROPOSED,OPERATIONALIZATION" -->
<a id="29-agent-architecture-and-rag-ingestion"></a>
## 29. Agent architecture and RAG ingestion

The package is intended to support research and production agents without forcing them to ingest one enormous document as an undifferentiated context window. The paper, schema, examples, and sources are separate but cross-linked artifacts.

### 29.1 Agent roles

A multi-agent workflow can assign narrow responsibilities:

| Agent | Responsibility | Prohibited behavior |
|---|---|---|
| Research agent | retrieve theory and source records | invent unsupported standards |
| Director agent | author intent, beats, performance, camera | modify locked measurements silently |
| Motion compiler | map actions to tracks and constraints | infer rights or safety approval |
| Biomechanics reviewer | check kinematic/dynamic feasibility | treat monocular estimates as measured force |
| Laban/performance agent | author qualitative phrasing | redefine Laban concepts through proxies |
| Face agent | construct AU/gaze/breath tracks | infer concealed mental state as fact |
| Style agent | apply typed transforms | violate invariants without report |
| Target adapter | emit model/engine controls | claim unsupported native control |
| Verification agent | re-extract and compare | change acceptance thresholds after seeing results |
| Rights/safety agent | enforce transfer and use policy | provide real-world harmful combat coaching |

### 29.2 RAG record types

The JSONL corpus uses one object per line. JSON Text Sequences standardize a related record-oriented approach; this package uses newline-delimited JSON as a practical convention and validates each line independently. [S078]

Recommended record types:

```text
document
research_chunk
schema_definition
field_guide
worked_example
source
prompt_template
validation_rule
migration_note
```

Each record contains stable identifiers, heading paths, concepts, evidence labels, source links, and a content hash.

```json
{
  "record_id":"chunk.cpcs_mx.17.staged_combat",
  "record_type":"research_chunk",
  "document_id":"cpcs-mx-research-v1",
  "title":"Staged combat and multi-actor action coding",
  "heading_path":["17","Staged combat and multi-actor action coding"],
  "concepts":["staged combat","contact","reaction","action graph"],
  "evidence_labels":["ESTABLISHED","PROPOSED"],
  "source_ids":["S041","S042","S044","S055"],
  "content":"…",
  "sha256":"…"
}
```

### 29.3 Chunking strategy

Chunk boundaries follow semantic sections, not a fixed character count. Long sections are divided at subheadings with a small context header. Each chunk should be independently interpretable but retain:

- document title;
- section number and heading path;
- definition scope;
- evidence labels;
- source IDs;
- neighboring chunk IDs;
- schema fields discussed.

Do not split a JSON or YAML example across records. Code examples should either remain within one chunk or become separate `worked_example` records.

### 29.4 Retrieval strategy

Queries should combine semantic similarity with metadata filters. Example:

```json
{
  "query":"compile a direct bound strike with staged near-contact",
  "filters": {
    "concepts_any":["staged combat","Laban","contact"],
    "evidence_labels_not":["UNVERIFIED"],
    "safety_scope":"virtual_or_staged"
  },
  "include_record_types":[
    "research_chunk","schema_definition","worked_example"
  ]
}
```

The agent should retrieve source records for claims, field definitions for syntax, and examples for composition. Retrieving only the nearest prose chunk can omit required units or safety constraints.

### 29.5 JSONL parser requirements

A production parser should:

1. stream one line at a time;
2. ignore blank lines but not malformed nonblank lines;
3. report filename and line number;
4. validate each object against the record schema;
5. reject duplicate `record_id` values unless byte-identical and explicitly deduplicated;
6. verify hashes when present;
7. quarantine invalid records rather than dropping them silently;
8. support compressed input where scale requires it;
9. checkpoint offsets for resumable ingestion;
10. preserve source order only as metadata, not semantic hierarchy.

For small research packages, a simple `for line in file` parser is sufficient. For very large frame-level observation streams, use partitioning by source, actor, layer, and time range and consider columnar conversion for analytics.

### 29.6 Knowledge graph relationships

Records can expose edges:

```text
section DEFINES field
field COMPILES_TO control
example USES field
metric VERIFIES field
source SUPPORTS claim
style_transform PRESERVES invariant
migration REPLACES field
```

This improves retrieval for questions such as “Which metrics verify a bound-flow staged contact?” or “Which target controls can carry a local wrist trajectory?”

### 29.7 Agent output discipline

An agent generating a score should provide:

- canonical JSON or authoring YAML;
- schema-validation result;
- assumptions and defaults;
- source IDs for research claims;
- unresolved ambiguities;
- capability coverage report;
- verification plan;
- safety and rights scope.

It should not claim deterministic video output merely because the score validates. Schema validity establishes structure, not model compliance.

### 29.8 RAG freshness and source status

Platform documentation and emerging model interfaces can change. Source records include retrieval or publication dates and status labels. Agents should prefer normative standards and peer-reviewed research for stable concepts, and current official documentation for platform-specific behavior. An adapter based on a deprecated API should be treated as historical even if its conceptual discussion remains useful.

<!-- RAG_CHUNK id="cpcs-mx-30" title="Experimental program" concepts="experiments, ablation, benchmarks, natural motion, UGC, combat, anime" evidence="PROPOSED" -->
<a id="30-experimental-program"></a>
## 30. Experimental program

CPCS-MX should be evaluated as a representation and compiler, not only through visually selected demos. A rigorous program separates schema expressiveness, compilation accuracy, model controllability, and perceived motion quality.

### 30.1 Research questions

1. Does explicit phase and contact coding improve temporal compliance over text-only prompting?
2. Do Laban and mannerism layers improve perceived performance specificity without reducing action correctness?
3. Does separating anatomical motion from stylized deformation reduce rig failures in superhuman clips?
4. Do dense pose controls outperform key poses for fight-scene contact timing?
5. Does a canonical score improve transfer of choreography across characters and morphologies?
6. Does re-extraction enable targeted correction with fewer full regenerations?
7. Which fields remain unsupported by current generation adapters?

### 30.2 Test suite

#### Natural locomotion

- walk, stop, turn, reach;
- uneven-ground foot placement;
- speed changes;
- habitual asymmetry;
- gaze and breath coordination.

#### High-fidelity UGC

- direct lens address;
- speech gesture;
- product pickup and demonstration;
- self-framing adjustment;
- natural pause and CTA hold.

#### Staged combat

- step-in and camera-side strike-like action;
- block or dodge;
- staged near-contact;
- recoil and recovery;
- two-character timing and screen direction.

#### Anime/superhuman

- held anticipation key;
- compressed execution;
- smear frame;
- reduced-gravity aerial phase;
- exaggerated but readable landing;
- VFX and camera emphasis.

### 30.3 Ablation conditions

```text
A: text only
B: text + action graph
C: B + phase/contact events
D: C + root and key-joint constraints
E: D + Laban/mannerism/face/breath
F: E + style transform
G: F + full dense control and closed-loop verification
```

Keep model, seed strategy, references, duration, and camera constant where possible. Report failures and discarded samples.

### 30.4 Metrics

Primary metrics:

- action-order accuracy;
- event timing error;
- contact distance and contact-time error;
- root and joint trajectory error;
- foot slip;
- retargeted end-effector error;
- joint-limit and penetration violations;
- camera and screen-direction compliance;
- face/gaze event error;
- perceived movement-quality match;
- persona consistency;
- generation attempts to acceptance.

Secondary metrics:

- prompt/token length;
- compiler runtime;
- adapter coverage;
- human correction time;
- RAG retrieval precision;
- schema-invalid output rate;
- conflict-resolution rate.

### 30.5 Calibration studies

Laban proxy profiles require calibration. Have trained movement analysts label clips, compute candidate features, and evaluate whether the proxy is predictive without collapsing distinct concepts. Mannerism profiles require repeated performances from the same character or performer to distinguish stable traits from one-shot action demands. Perceptual metrics require human ratings and reliability analysis.

### 30.6 Reproducibility package

Each run stores:

```text
input score and hashes
compiler and adapter versions
source and reference assets
model identifier
seed and generation parameters
output videos
re-extracted observations
metric reports
human-rating protocol and anonymized data
failure log
```

A curated demo without failed candidates is not sufficient evidence of control.

### 30.7 Success criteria

The project should define task-specific thresholds before generation. Example engineering gates might require action-order equality, contact within one or two frames, foot slip below a chosen distance, and no hard joint-limit violations. Such thresholds are not universal; they derive from shot purpose, frame rate, scale, and intended style.

<!-- RAG_CHUNK id="cpcs-mx-31" title="Limitations, rights, safety, and ethics" concepts="limitations, rights, identity, staged combat, biometric data, safety" evidence="ESTABLISHED,PROPOSED" -->
<a id="31-limitations-rights-safety-and-ethics"></a>
## 31. Limitations, rights, safety, and ethics

### 31.1 Under-determination

Monocular video cannot uniquely determine hidden depth, joint rotations, contact force, mass, torque, or off-camera motion. Anime and heavily edited action can be intentionally nonphysical. CPCS-MX preserves alternatives and confidence; it does not turn an inference into ground truth through schema formatting.

### 31.2 Model compliance

A validated score does not guarantee that a generative model will follow it. Exact control depends on the executable carrier, target capabilities, training distribution, references, duration, and iterative verification. Text-only generation remains a weak carrier for frame-accurate motion.

### 31.3 Biomechanical scope

Biomechanical fields are suitable for simulation, analysis, and virtual-character control. They are not medical diagnosis or individualized real-world performance instruction. Joint limits vary across people and models. Inverse dynamics depends on model assumptions and input quality. [S002][S003][S005]

### 31.4 Combat scope

Combat examples describe virtual animation or professionally staged screen action. Stage-combat organizations emphasize training, choreography, communication, and safety systems. [S044] The package should not be used to optimize real-world injury, force delivery, or evasion. Contact records default to staged near-contact unless an authorized virtual simulation explicitly requires collision.

### 31.5 Identity and biometric data

Motion, face, gait, voice, and mannerisms can be identifying. A production must establish consent, licensing, data retention, allowed transformations, and replacement policy. Structural choreography transfer should separate:

- reusable action grammar;
- performer-specific biometric signature;
- character identity;
- protected costume or design;
- source-specific cinematography and expressive assets.

An agent must not assume that technical extractability grants legal or ethical permission.

### 31.6 Cultural interpretation

Gestures and postures can be culturally specific. A mannerism library should record context and source scope rather than label behaviors as universal emotional signs. Affect inference from movement or face is probabilistic and context dependent.

### 31.7 FACS and emotion

FACS codes visible facial action, not honesty, diagnosis, or a person’s true internal state. [S031][S032] CPCS-MX separates observed AUs, displayed affect, inferred narrative state, and authored character intention.

### 31.8 Superhuman representation

Virtual gravity, impulse, deformation, and timing transforms should be labeled as fictional. They should not be converted into instructions for human performers. Physically impossible motion can still be internally coherent as screen animation when its graphic rules and causal cues are explicit.

### 31.9 Dataset and model bias

Motion datasets may underrepresent body types, disabilities, cultures, ages, and movement traditions. Retargeting and generation models can normalize motion toward dominant training distributions. Evaluation should include morphology diversity and avoid treating one gait or expressivity profile as the definition of natural movement.

### 31.10 Security and parser safety

Agent-ingested YAML should use safe parsing, disable arbitrary object construction, constrain includes, validate paths, and reject untrusted executable tags. JSONL parsers should limit record size and nesting depth. External assets require checksum and media-type verification. XML envelopes, when used, should disable external entity expansion and unrestricted network resolution.

### 31.11 Transparency

A generated clip or score should retain provenance sufficient to answer:

- which motion was observed, generated, retargeted, or manually authored;
- which performer or dataset contributed;
- what was replaced;
- which controls were approximated;
- which hard constraints failed;
- which safety and rights policies were applied.

<!-- RAG_CHUNK id="cpcs-mx-32" title="Conclusions" concepts="CPCS-MX, hierarchical motion grammar, AI video, exact control" evidence="PROPOSED" -->
<a id="32-conclusions"></a>
## 32. Conclusions

CPCS-MX treats character performance as a layered, time-addressable program rather than an expanded text prompt. Root trajectories and joint tracks describe geometry; contacts and phases describe causal coordination; kinematics and virtual dynamics describe motion behavior; Laban, FACS, gaze, breath, and mannerisms describe performance; style transforms describe how action is re-expressed; camera and VFX describe presentation; and constraints plus verification make the result testable.

The architecture supports a continuum:

```text
observed human performance
→ canonical motion score
→ character-specific retargeting
→ naturalistic or stylized transformation
→ engine, DCC, motion-model, or video-model execution
→ re-extraction and compliance testing
```

Its most important discipline is separation. Anatomical limits are not cartoon deformation. Perceived Weight is not mass. An AU is not an emotion diagnosis. A JSON object is not executable motion. A semantic video model is not a frame-accurate pose tracker. A visually convincing contact is not necessarily physical contact. By keeping these distinctions explicit, a sophisticated score can combine them without losing scientific or production meaning.

The proposed schema is deliberately model-agnostic. Its value depends on adapters, calibration, validation, and agent behavior. The next research step is empirical: implement the compiler, publish representative scores and failure cases, measure which controls survive each target pipeline, and refine the representation based on observable compliance rather than prompt folklore.


<!-- RAG_CHUNK id="cpcs-mx-app-a" title="Appendix A CPCS-MX field dictionary" concepts="field dictionary, schema, units, semantics" evidence="PROPOSED,OPERATIONALIZATION" -->
<a id="appendix-a--cpcs-mx-field-dictionary"></a>
## Appendix A — CPCS-MX field dictionary

This appendix summarizes the canonical field families. The machine-readable schema in the package is authoritative for syntax; this table explains intent and common failure modes.

### A.1 Document and provenance

| Field | Meaning | Required discipline |
|---|---|---|
| `schema_id` | CPCS-MX contract version | exact URI or stable version string |
| `document_id` | stable score identity | globally unique within production |
| `title` | human-readable title | not used as an identifier |
| `created_at` / `modified_at` | timestamps | ISO 8601 |
| `authors` | human or agent contributors | roles and tool versions |
| `derived_from` | source artifact references | immutable lineage |
| `provenance.operations` | transformation history | ordered, parameterized, hashed |
| `rights_scope` | permitted use and transfer | explicit rather than inferred |
| `safety_scope` | virtual/staged/real-world restrictions | required for action content |

### A.2 Time and media

| Field | Meaning | Common failure |
|---|---|---|
| `timebase.canonical` | canonical time domain | mixing seconds and frames |
| `timebase.fps` | presentation or view rate | assuming integer fps |
| `timebase.sample_rate_hz` | dense track sampling | using video fps for all solvers |
| `timebase.source_clock` | PTS, frame, simulation, or authored | losing variable-frame timing |
| `interval.start_s/end_s` | half-open temporal interval | ambiguous inclusive endpoints |
| `event.time_s` | point-event target | omitting tolerance |
| `retime_map` | source-to-presentation mapping | applying slow motion to physics unintentionally |

### A.3 Coordinate systems

| Field | Meaning |
|---|---|
| `coordinate_system_id` | stable basis identifier |
| `space` | world, stage, root, local joint, camera, image, normalized screen |
| `handedness` | left or right |
| `up_axis` / `forward_axis` | basis axes |
| `origin` | declared reference point |
| `linear_unit` | meter internally recommended |
| `angular_unit` | radian internally recommended |
| `transform_to_parent` | explicit basis transform |

Every track that contains geometry references a coordinate system. Screen-space trajectories are not interchangeable with world-space trajectories.

### A.4 Entities, characters, and rigs

| Field | Meaning |
|---|---|
| `entity_id` | actor, prop, environment, camera, effect, or audio entity |
| `character_id` | narrative character identity |
| `performer_id` | source performer or motion identity, if permitted |
| `rig_id` | skeleton and deformation system |
| `morphology_profile` | body proportions and shape metadata |
| `joint_set` | ordered semantic joints |
| `joint_limit_profiles` | anatomical, rig-safe, virtual-stylized |
| `retarget_map` | source-to-target semantic mapping |
| `collision_model` | virtual contact geometry |

Character identity, performer identity, and rig identity must not be collapsed. One character can be portrayed by multiple performers or rigs; one rig can portray multiple characters.

### A.5 Shots, beats, and action graph

| Field | Meaning |
|---|---|
| `shot_id` | continuous presentation unit |
| `beat_id` | dramatic or performance unit |
| `objective` | immediate character goal |
| `tactic` | strategy used to reach the goal |
| `action_id` | reusable or authored physical action |
| `action_type` | step, pivot, reach, fall, recover, etc. |
| `preconditions` | required state before action |
| `postconditions` | expected resulting state |
| `participants` | actors/props and their roles |
| `target_ref` | spatial or semantic target |
| `temporal_relations` | partial-order dependencies |

Actions should be task descriptions, not vague style labels. `aggressive` belongs in performance or intent; `step_in` belongs in action coding.

### A.6 Phase fields

| Field | Meaning |
|---|---|
| `global_phase` | cyclic or normalized action phase |
| `local_phase` | body-part-specific phase |
| `phase_label` | preparation, execution, contact, recovery, reset |
| `phase_curve` | continuous phase value over time |
| `phase_event_refs` | synchronization to events |
| `phase_authority` | observed, authored, generated, or derived |

A phase value without a definition is unusable. The score states whether phase wraps, clamps, or resets and which event anchors zero.

### A.7 Root and joint tracks

| Field | Meaning |
|---|---|
| `root_translation` | global pelvis/root position |
| `root_orientation` | global facing/orientation |
| `joint_rotation` | local joint rotation |
| `joint_position` | local or global joint position |
| `velocity` / `acceleration` | declared derivatives or authored tracks |
| `angular_velocity` / `angular_acceleration` | rotational derivatives |
| `representation` | keyframes, sampled, external asset, procedural |
| `interpolation` | step, linear, cubic, quaternion slerp, etc. |
| `authority` | locked, guided, preferred, free |

Derived derivatives record the smoothing and differentiation method. Raw numerical differentiation can amplify pose-estimation noise.

### A.8 Contacts and relations

| Field | Meaning |
|---|---|
| `contact_id` | stable interaction event/interval |
| `contact_type` | support, grasp, touch, staged near-contact, collision |
| `site_a/site_b` | semantic contact sites |
| `distance_curve` | optional separation over time |
| `normal` | virtual contact normal |
| `friction_profile` | simulation-only friction model |
| `impulse` | virtual or estimated impulse, with evidence status |
| `reaction_event_ref` | synchronized response |
| `camera_cheat_allowed` | visible alignment may differ from world geometry |
| `no_penetration` | hard or soft relation |

Real-world impact force should not be inferred from an animation label. Virtual parameters must be labeled.

### A.9 Kinematics and dynamics

| Field | Meaning |
|---|---|
| `mass_profile` | character/segment virtual masses |
| `gravity_profile` | phase-specific virtual gravity |
| `external_force` | simulation input or measured force |
| `joint_torque` | simulated, estimated, or constrained torque |
| `center_of_mass` | model-derived COM track |
| `momentum` | linear/angular momentum |
| `energy_budget` | virtual work or control cost |
| `inverse_dynamics_report` | residual and model settings |
| `physics_mode` | none, kinematic, hybrid, dynamic |

The evidence class is mandatory for force and torque fields.

### A.10 Laban/BESS

| Field | Meaning |
|---|---|
| `body` | body organization and initiation |
| `effort.weight` | light–strong attitude toward Weight |
| `effort.time` | sustained–sudden attitude toward Time |
| `effort.space` | indirect–direct attitude toward Space |
| `effort.flow` | free–bound attitude toward Flow |
| `shape` | rising/sinking, spreading/enclosing, advancing/retreating |
| `space` | kinesphere, directions, pathways, spatial intent |
| `phrasing` | change pattern across a phrase |
| `proxy_profile` | computational operationalization |

Use Laban descriptors to guide quality, not as substitutes for trajectories and contacts.

### A.11 Face, affect, gaze, and breath

| Field | Meaning |
|---|---|
| `facial_tracks` | AU or rig coefficient curves |
| `action_unit` | FACS AU identifier and side |
| `onset/apex/offset` | temporal landmarks |
| `displayed_affect` | visible affect trajectory |
| `character_state` | authored narrative/internal state |
| `gaze_target` | entity or spatial target |
| `saccade/blink` | eye-event timing |
| `head_pose` | head orientation independent of gaze |
| `breath_track` | respiratory phase and amplitude |
| `vocal_effort_event` | exertion sound and synchronization |

Observed AUs, displayed affect, and narrative intent are separate layers.

### A.12 Mannerisms and persona

| Field | Meaning |
|---|---|
| `mannerism_profile_id` | reusable character movement profile |
| `preferred_stance` | habitual support and alignment |
| `guard_profile` | fictional/staged action posture |
| `asymmetry` | stable left/right preference |
| `gaze_pattern` | target acquisition and aversion habits |
| `gesture_inventory` | recurring gesture modules |
| `microvariation` | bounded timing/amplitude variation |
| `postural_tone` | baseline alignment and movement readiness |
| `breath_signature` | characteristic rhythm/profile |

Mannerisms should be based on authorized character design or consented performance data.

### A.13 Secondary motion

| Field | Meaning |
|---|---|
| `system_type` | cloth, hair, soft tissue, prop, debris |
| `drivers` | primary joints or transforms |
| `solver` | simulation or keyframe method |
| `material_parameters` | mass, damping, compliance, stiffness |
| `collision_refs` | collision proxies |
| `art_direction` | holds, pins, silhouette, face-clearance |
| `cache_asset_ref` | baked result |
| `continuity_policy` | behavior across cuts |

### A.14 Style and superhuman fields

| Field | Meaning |
|---|---|
| `source_profile` / `target_profile` | named style spaces |
| `timing_transform` | phase-specific retime |
| `spatial_transform` | path, reach, arc, silhouette |
| `dynamic_transform` | virtual gravity, impulse, damping |
| `deformation_transform` | mesh or rig stylization |
| `graphic_transform` | holds, smears, impact frames |
| `presentation_transform` | camera/VFX/audio emphasis |
| `invariants` | fields that must remain unchanged |
| `style_intensity` | optional macro control expanded into dimensions |

### A.15 Presentation and marketing fields

| Field | Meaning |
|---|---|
| `camera_track` | pose, lens, framing, focus |
| `edit_events` | cuts, holds, retimes, reaction cuts |
| `vfx_events` | trails, dust, flashes, shake, smears |
| `audio_events` | dialogue, breath, impacts, music accents |
| `attention_target` | intended visual focus |
| `product_visibility` | measurable screen presence |
| `hook/proof/cta` | UGC or marketing beat function |
| `variant_matrix` | experimental creative variations |

Marketing fields describe communication structure and hypotheses; they do not guarantee sales.

### A.16 Verification and build fields

| Field | Meaning |
|---|---|
| `verification_plan` | metrics and extraction methods |
| `acceptance_gate` | threshold and failure policy |
| `metric_definition_ref` | versioned implementation |
| `candidate_id` | generated execution identity |
| `comparison_report` | target/output metric vector |
| `capability_report` | native/approximated/unsupported fields |
| `build_manifest` | hashes, tools, models, seeds |
| `loss_report` | transformations and omissions |

<!-- RAG_CHUNK id="cpcs-mx-app-b" title="Appendix B canonical JSON example" concepts="canonical JSON, example score, action, Laban, constraints" evidence="PROPOSED,OPERATIONALIZATION" -->
<a id="appendix-b--canonical-json-example"></a>
## Appendix B — canonical JSON example

The following compact example describes a fictional, professionally staged near-contact action. It demonstrates structure rather than prescribing real-world combat technique.

```json
{
  "$schema": "../schemas/CPCS_MX_Schema.json",
  "schema_id": "urn:cpcs-mx:schema:1.0",
  "document_id": "score.example.staged_exchange.001",
  "title": "Staged approach, near-contact, recoil, and recovery",
  "safety_scope": "virtual_or_professionally_staged_screen_action",
  "rights_scope": {
    "source_motion": "original_or_licensed",
    "identity_transfer": "replace_source_identity"
  },
  "timebase": {
    "canonical": "seconds",
    "fps": {"numerator": 24, "denominator": 1},
    "sample_rate_hz": 120,
    "interval_semantics": "half_open"
  },
  "coordinate_systems": [
    {
      "coordinate_system_id": "world_stage",
      "space": "world",
      "handedness": "right",
      "up_axis": "+Y",
      "forward_axis": "+Z",
      "linear_unit": "meter",
      "angular_unit": "radian"
    }
  ],
  "characters": [
    {
      "character_id": "actor_a",
      "rig_ref": "rig.humanoid.a",
      "mannerism_profile_ref": "mannerism.centered_controlled"
    },
    {
      "character_id": "actor_b",
      "rig_ref": "rig.humanoid.b",
      "mannerism_profile_ref": "mannerism.reactive_guarded"
    }
  ],
  "rigs": [
    {
      "rig_id": "rig.humanoid.a",
      "joint_set_ref": "jointset.cpcs_humanoid_68",
      "joint_limit_profile_ref": "limits.rig_safe.a"
    },
    {
      "rig_id": "rig.humanoid.b",
      "joint_set_ref": "jointset.cpcs_humanoid_68",
      "joint_limit_profile_ref": "limits.rig_safe.b"
    }
  ],
  "shots": [
    {
      "shot_id": "shot_001",
      "interval": {"start_s": 0.0, "end_s": 4.0},
      "camera": {
        "shot_scale": "medium_wide",
        "angle": "slightly_low",
        "screen_direction": "actor_a_left_to_right",
        "trajectory_track_ref": "track.camera.pose.001"
      },
      "beats": [
        {
          "beat_id": "beat_approach",
          "interval": {"start_s": 0.0, "end_s": 1.20},
          "objective": "actor_a closes distance while retaining control",
          "actions": [
            {
              "action_id": "action.actor_a.step_in",
              "action_type": "step_in",
              "actor_ref": "actor_a",
              "phase_refs": ["phase.actor_a.step_in"]
            }
          ]
        },
        {
          "beat_id": "beat_exchange",
          "interval": {"start_s": 1.20, "end_s": 2.72},
          "objective": "readable staged attack and reaction",
          "actions": [
            {
              "action_id": "action.actor_a.strike_like",
              "action_type": "strike_like_extension",
              "actor_ref": "actor_a",
              "target_ref": "actor_b.head_target_volume",
              "phase_refs": ["phase.actor_a.strike_like"],
              "contact_event_ref": "event.near_contact.001"
            },
            {
              "action_id": "action.actor_b.recoil",
              "action_type": "recoil",
              "actor_ref": "actor_b",
              "trigger_event_ref": "event.near_contact.001",
              "phase_refs": ["phase.actor_b.recoil"]
            }
          ],
          "laban_controls": [
            {
              "subject_ref": "actor_a",
              "interval": {"start_s": 1.20, "end_s": 2.42},
              "effort": {
                "weight": {"pole": "strong", "intensity": 0.86},
                "time": {"pole": "sudden", "intensity": 0.92},
                "space": {"pole": "direct", "intensity": 0.90},
                "flow": {"pole": "bound", "intensity": 0.74}
              },
              "shape": {
                "sagittal": "advancing",
                "horizontal": "spreading"
              },
              "proxy_profile_ref": "laban_proxy.production_v3"
            }
          ]
        },
        {
          "beat_id": "beat_recovery",
          "interval": {"start_s": 2.72, "end_s": 4.0},
          "objective": "both characters restore stable readable states"
        }
      ]
    }
  ],
  "phases": [
    {
      "phase_id": "phase.actor_a.step_in",
      "subject_ref": "actor_a",
      "labels": [
        {"name": "preparation", "interval": [0.00, 0.30]},
        {"name": "execution", "interval": [0.30, 0.92]},
        {"name": "settle", "interval": [0.92, 1.20]}
      ]
    },
    {
      "phase_id": "phase.actor_a.strike_like",
      "subject_ref": "actor_a",
      "labels": [
        {"name": "anticipation", "interval": [1.20, 1.56]},
        {"name": "acceleration", "interval": [1.56, 2.28]},
        {"name": "near_contact", "interval": [2.28, 2.34]},
        {"name": "follow_through", "interval": [2.34, 2.48]},
        {"name": "recovery", "interval": [2.48, 3.20]}
      ]
    },
    {
      "phase_id": "phase.actor_b.recoil",
      "subject_ref": "actor_b",
      "labels": [
        {"name": "reaction_delay", "interval": [2.31, 2.35]},
        {"name": "recoil", "interval": [2.35, 2.78]},
        {"name": "recovery", "interval": [2.78, 3.70]}
      ]
    }
  ],
  "tracks": [
    {
      "track_id": "track.actor_a.root.position",
      "semantic": "root_translation",
      "subject_ref": "actor_a",
      "coordinate_system_ref": "world_stage",
      "unit": "meter",
      "authority": "locked",
      "representation": {
        "type": "keyframes",
        "interpolation": "cubic_hermite",
        "keys": [
          {"t": 0.0, "value": [-0.85, 0.0, 0.0]},
          {"t": 1.2, "value": [-0.18, 0.0, 0.0]},
          {"t": 2.31, "value": [0.08, 0.0, 0.0]},
          {"t": 4.0, "value": [-0.02, 0.0, 0.0]}
        ]
      }
    },
    {
      "track_id": "track.joints.actor_a",
      "semantic": "local_joint_rotation_6d",
      "subject_ref": "actor_a",
      "representation": {
        "type": "external_asset",
        "asset_ref": "asset.track.actor_a.joints"
      }
    }
  ],
  "events": [
    {
      "event_id": "event.near_contact.001",
      "type": "staged_near_contact",
      "time_s": 2.31,
      "tolerance_s": 0.0208,
      "participants": [
        {"entity_ref": "actor_a", "site": "right_hand"},
        {"entity_ref": "actor_b", "site": "head_target_volume"}
      ],
      "payload": {
        "minimum_distance_m": 0.018,
        "no_penetration": true,
        "camera_cheat_allowed": true
      },
      "hard": true
    },
    {
      "event_id": "event.actor_b.reaction_onset",
      "type": "reaction_onset",
      "time_s": 2.35,
      "tolerance_s": 0.0417,
      "linked_to": "event.near_contact.001"
    }
  ],
  "facial_events": [
    {
      "event_id": "face.actor_a.effort",
      "subject_ref": "actor_a",
      "interval": [2.02, 2.50],
      "action_units": [
        {"au": "AU04", "side": "bilateral", "peak": 0.34},
        {"au": "AU07", "side": "bilateral", "peak": 0.42},
        {"au": "AU23", "side": "bilateral", "peak": 0.38}
      ],
      "gaze_target_ref": "actor_b.head_target_volume"
    }
  ],
  "breath_tracks": [
    {
      "track_id": "breath.actor_a.001",
      "subject_ref": "actor_a",
      "events": [
        {"type": "exhale_on_effort", "time_s": 2.12},
        {"type": "recovery_inhale", "time_s": 2.86}
      ]
    }
  ],
  "constraints": [
    {
      "constraint_id": "constraint.actor_a.left_foot_lock",
      "scope": {"subject_ref": "actor_a", "interval": [1.34, 2.34]},
      "type": "contact_lock",
      "site": "left_foot",
      "priority": "hard",
      "tolerances": {
        "horizontal_slip_m": 0.015,
        "vertical_error_m": 0.008
      },
      "failure_policy": "reject_candidate"
    },
    {
      "constraint_id": "constraint.screen_direction",
      "scope": {"shot_ref": "shot_001"},
      "type": "screen_direction",
      "priority": "hard",
      "value": "actor_a_left_to_right",
      "failure_policy": "reject_candidate"
    }
  ],
  "assets": [
    {
      "asset_id": "asset.track.actor_a.joints",
      "uri": "tracks/actor_a_joints_rot6d.f32",
      "encoding": "raw_little_endian",
      "dtype": "float32",
      "shape": [481, 68, 6],
      "sample_rate_hz": 120,
      "sha256": "REPLACE_WITH_ACTUAL_HASH"
    }
  ],
  "verification_plan": {
    "metrics": [
      "action_order_accuracy",
      "contact_time_error",
      "minimum_contact_distance",
      "root_trajectory_error",
      "major_joint_screen_error",
      "foot_slip",
      "joint_limit_violations",
      "screen_direction_match",
      "facial_event_timing"
    ],
    "acceptance_gates": [
      {"metric": "action_order_accuracy", "operator": "==", "value": 1.0},
      {"metric": "contact_time_error_s", "operator": "<=", "value": 0.0417},
      {"metric": "joint_limit_violations", "operator": "==", "value": 0}
    ]
  }
}
```

<!-- RAG_CHUNK id="cpcs-mx-app-c" title="Appendix C YAML authoring example" concepts="YAML, authoring, inheritance, natural UGC, superhuman style" evidence="STANDARD,PROPOSED,OPERATIONALIZATION" -->
<a id="appendix-c--yaml-authoring-example"></a>
## Appendix C — YAML authoring example

YAML is intended for readable authoring, profiles, imports, and overrides. It compiles into canonical JSON; YAML anchors are not relied upon as the formal inheritance system.

```yaml
cpcs_mx:
  schema: "urn:cpcs-mx:schema:1.0"
  document_id: "authoring.ugc_power_demo.001"

  extends:
    - "profile://movement/natural_human_v3"
    - "profile://capture/authentic_ugc_v2"
    - "profile://performance/confident_direct_v1"

  imports:
    base_motion:
      type: json
      path: "../canonical/base_product_demo.json"
    pose_reference:
      type: asset
      path: "../tracks/product_demo_pose.npz"

  scope:
    safety: "ordinary_nonhazardous_product_demonstration"
    rights: "authorized_character_and_product_assets"

  shot:
    id: "shot_ugc_01"
    duration_s: 8.0
    fps: 30
    objective: "Establish immediate credibility, demonstrate the feature, and hold the proof result."

  character:
    id: "creator_a"
    mannerism_profile:
      preferred_stance: "left_hip_loaded"
      gesture_bias: "right_hand_explanatory"
      gaze:
        lens_address_duty_cycle: 0.68
        product_check_before_demo: true
      microvariation:
        timing_sigma_s: 0.035
        amplitude_sigma: 0.04
        deterministic_seed: 817

  action_graph:
    - id: "hook_lens_address"
      interval_s: [0.0, 1.4]
      actions:
        - direct_gaze_to_lens
        - small_forward_lean
        - right_hand_hook_gesture

    - id: "pickup_and_demo"
      interval_s: [1.4, 5.8]
      actions:
        - gaze_to_product
        - reach
        - grasp
        - lift_to_demo_zone
        - demonstrate_feature
        - return_gaze_to_lens
      hard_constraints:
        - "right_hand maintains product grasp from 2.1s to 5.6s"
        - "product logo is camera-visible from 3.4s to 5.2s"

    - id: "proof_hold"
      interval_s: [5.8, 7.2]
      actions:
        - hold_result
        - restrained_smile
        - micro_nod

    - id: "cta"
      interval_s: [7.2, 8.0]
      actions:
        - return_product_to_lower_frame
        - lens_address

  performance:
    laban:
      hook_lens_address:
        weight: {pole: light, intensity: 0.32}
        time: {pole: sudden, intensity: 0.48}
        space: {pole: direct, intensity: 0.84}
        flow: {pole: bound, intensity: 0.44}
      pickup_and_demo:
        weight: {pole: light, intensity: 0.24}
        time: {pole: sustained, intensity: 0.58}
        space: {pole: direct, intensity: 0.78}
        flow: {pole: free, intensity: 0.36}

    face:
      hook:
        - {au: AU01, peak: 0.18, apex_s: 0.32}
        - {au: AU02, peak: 0.14, apex_s: 0.32}
        - {au: AU12, peak: 0.26, apex_s: 0.90}
      proof:
        - {au: AU06, peak: 0.16, apex_s: 6.36}
        - {au: AU12, peak: 0.32, apex_s: 6.36}

    breath:
      - {type: inhale_prepare, time_s: 0.0}
      - {type: speech_exhale_phrase, interval_s: [0.18, 1.28]}
      - {type: recovery_inhale, time_s: 5.72}

  capture_style:
    camera:
      mode: "performer_operated_phone"
      stabilization: 0.42
      self_framing_corrections: true
      hard_constraint: "face and product never simultaneously leave frame"
    imperfections:
      enabled: true
      bounded: true
      no_random_jitter: true
      allowed:
        - minor_focus_breathing
        - small_framing_correction
        - natural_gesture_timing_variation

  style_switch:
    target: "superhuman_comedic_product_demo"
    enabled: false
    dimensions:
      gravity_scale: 0.8
      anticipation_expansion: 1.15
      product_lift_arc_scale: 1.20
      graphic_emphasis: 0.35
    invariants:
      - product_grasp
      - product_logo_visibility
      - spoken_timing
      - lens_address_events

  verification:
    gates:
      - metric: product_visibility_duty_cycle
        operator: ">="
        value: 0.82
      - metric: grasp_contact_error_s
        operator: "<="
        value: 0.067
      - metric: face_in_frame_duty_cycle
        operator: ">="
        value: 0.92
      - metric: hard_constraint_violations
        operator: "=="
        value: 0
```

<!-- RAG_CHUNK id="cpcs-mx-app-d" title="Appendix D validation checklist" concepts="validation, checklist, compiler, motion quality" evidence="PROPOSED,OPERATIONALIZATION" -->
<a id="appendix-d--validation-checklist"></a>
## Appendix D — validation checklist

### D.1 Syntax and schema

- [ ] JSON parses without duplicate keys.
- [ ] YAML is loaded with a safe parser.
- [ ] XML, when present, disables external entities.
- [ ] Canonical JSON validates against the intended schema version.
- [ ] All stable IDs are unique.
- [ ] All references resolve.
- [ ] No undeclared extension namespace is executed.
- [ ] Required evidence classes are present.

### D.2 Time

- [ ] Canonical clock is declared.
- [ ] FPS is rational where necessary.
- [ ] Source PTS is preserved for extracted motion.
- [ ] Interval boundary semantics are declared.
- [ ] Retiming maps source, simulation, and presentation clocks explicitly.
- [ ] Event tolerances are declared.
- [ ] One-frame effects specify exposure semantics.

### D.3 Geometry

- [ ] Units are explicit.
- [ ] Handedness, up-axis, forward-axis, and origin are explicit.
- [ ] Root and joint tracks name their coordinate systems.
- [ ] Rotation encoding and interpolation are explicit.
- [ ] Joint order and rig version are hashed.
- [ ] Retarget mapping and morphology are documented.
- [ ] Global-pose spot checks pass.

### D.4 Action and phases

- [ ] Action identities and participants are stable.
- [ ] Preconditions and postconditions are compatible.
- [ ] Temporal relation graph is acyclic or intentionally cyclic.
- [ ] Preparation, execution, contact, and recovery are represented where relevant.
- [ ] Local phases exist for asynchronous multi-contact actions.
- [ ] Recovery and reset are not omitted.

### D.5 Contacts and dynamics

- [ ] Support contacts are separated from interaction contacts.
- [ ] Staged near-contact is not mislabeled as physical impact.
- [ ] Locked contacts include tolerances.
- [ ] No-penetration and camera-cheat policies are explicit.
- [ ] Force, torque, impulse, mass, and gravity fields state evidence status.
- [ ] Joint-limit profile is anatomical, rig-safe, or virtual-stylized.
- [ ] Virtual dynamics do not become real-performer instructions.

### D.6 Performance

- [ ] Laban descriptors have intervals and subjects.
- [ ] Computational proxies are identified as proxies.
- [ ] Shape change and phrasing are not reduced to one Effort label.
- [ ] FACS AUs use correct identifiers and timing.
- [ ] Observed facial actions are separate from inferred emotion.
- [ ] Gaze, head, blink, and breath are synchronized with action.
- [ ] Mannerism profile is character-specific and authorized.
- [ ] Microvariation is bounded and seeded where reproducibility matters.

### D.7 Style and superhuman transformation

- [ ] Source and target styles are named.
- [ ] Macro intensity expands into typed dimensions.
- [ ] Anatomical motion and mesh deformation are separate.
- [ ] Virtual gravity and impulse are phase-specific where needed.
- [ ] Invariants are listed.
- [ ] Holds, smears, and impact frames specify presentation semantics.
- [ ] Style changes preserve action causality unless an override is documented.

### D.8 Secondary motion

- [ ] Driver joints are declared.
- [ ] Simulation or keyframe method is declared.
- [ ] Collision proxies and art-direction overrides are explicit.
- [ ] Face, hand, and product occlusion constraints are checked.
- [ ] Cache or solver version is recorded.

### D.9 Target compilation

- [ ] Target capability matrix is current.
- [ ] Every important score field is marked native, approximated, postprocessed, or unsupported.
- [ ] Text is not used as the only carrier for locked frame-level motion.
- [ ] Dense controls have correct length, rate, and resolution.
- [ ] Seed, model, adapter, and sampler settings are recorded.
- [ ] Loss report is generated.

### D.10 Verification

- [ ] Acceptance gates were defined before reviewing outputs.
- [ ] Output was re-extracted using compatible clocks and coordinates.
- [ ] Event timing, action order, contacts, root, and joints were measured.
- [ ] Smoothness was evaluated by phase, not globally alone.
- [ ] Joint limits, penetration, and foot slip were checked.
- [ ] Face, gaze, breath, camera, and VFX timing were checked where relevant.
- [ ] Human evaluation separates action, naturalness, style, and preference.
- [ ] Failed candidates and revisions are retained in the experiment log.

### D.11 RAG and agents

- [ ] JSONL parses one independent object per line.
- [ ] Record IDs and hashes are unique and valid.
- [ ] Chunks retain heading paths, evidence labels, and source IDs.
- [ ] Code examples are not split across chunks.
- [ ] Schema, examples, and source records are retrieved with conceptual prose.
- [ ] Platform-specific claims are freshness-checked.
- [ ] Agent output lists assumptions, unresolved ambiguity, capability loss, and verification plan.

<!-- RAG_CHUNK id="cpcs-mx-app-e" title="Appendix E glossary" concepts="glossary, definitions, CPCS-MX terminology" evidence="ESTABLISHED,PROPOSED" -->
<a id="appendix-e--glossary"></a>
## Appendix E — glossary

**Action graph.** A directed structure representing physical actions, participants, preconditions, postconditions, and causal or temporal relations.

**Action Unit (AU).** A FACS label for an observable facial movement component. It is not, by itself, an emotion label. [S031]

**Anatomical limit.** A human-reference joint range from a declared model or source. It is not automatically the safe range for every person or rig.

**Authority.** The degree to which a track or field controls the resolved score: locked, guided, preferred, or free.

**Canonical JSON.** The fully resolved, typed CPCS-MX representation used for validation, hashing, and target compilation.

**Contact.** A support, grasp, touch, near-contact, or collision relation between declared sites over time.

**Control carrier.** The actual input that conveys a requirement to an execution system, such as a trajectory, pose video, rig curve, mask, or prompt.

**CPCS-MX.** The proposed hierarchical motion-grammar extension defined in this monograph.

**Dense track.** A sampled time series stored inline or in an external array asset.

**Displayed affect.** Affect communicated through observable performance; distinct from authored internal character state or inferred real emotion.

**Evidence class.** One of measured, detected, inferred, interpreted, authored, defaulted, or derived.

**Exactness target.** The declared reference space in which fidelity is evaluated: clock, screen, rig, world, dynamics, or perception.

**FACS.** Facial Action Coding System, an anatomically oriented method for coding visible facial actions. [S031][S032]

**Hard constraint.** A requirement whose violation rejects or invalidates a candidate under the declared policy.

**IK.** Inverse kinematics: solving model coordinates to satisfy target marker or end-effector positions, subject to a model and objective. [S001]

**Inverse dynamics.** Estimating generalized forces or moments from motion and external-force data under a specified model. [S002]

**Laban/BESS.** Body, Effort, Shape, and Space concepts used to analyze and articulate movement organization and quality.

**Local phase.** A phase signal associated with a body part or local movement rhythm, useful when different parts are asynchronous. [S009]

**Mannerism profile.** A reusable, character-specific set of habitual postures, timing, asymmetries, gestures, gaze patterns, and microvariation.

**Motion matching.** Retrieval of animation frames or poses from a database based on current pose and desired trajectory/features.

**Perceptual constraint.** A project-defined visual or experiential requirement, such as silhouette readability or target visibility.

**Phase.** A normalized or labeled temporal organization of a cyclic or bounded movement.

**Presentation time.** Time as shown to the audience after editing, holds, slow motion, or time warps.

**Proxy profile.** A versioned computational mapping used to estimate a qualitative descriptor such as Laban Effort. The proxy is not the theory itself.

**Retargeting.** Mapping motion from a source skeleton or morphology to a target while preserving selected semantics and constraints. [S016][S017][S018]

**Rig-safe limit.** The rotation or deformation range that preserves a specific rig’s mesh, controls, and production requirements.

**Root motion.** Global or character-level translation and orientation that moves the body through the environment.

**Secondary motion.** Motion driven by the primary performance, including hair, cloth, accessories, soft tissue, and debris.

**Soft constraint.** A weighted preference whose error is measured and optimized rather than absolutely prohibited.

**Staged near-contact.** A screen-action event designed to read as contact while preserving a small separation or camera-side cheat.

**Style transform.** A typed transformation of timing, space, dynamics, deformation, graphics, or presentation, subject to declared invariants.

**Superhuman motion.** Deliberately fictional movement created through explicit virtual physics, timing, deformation, and presentation transforms—not a recommendation for human performance.

**Virtual-stylized limit.** A declared nonhuman motion or deformation range used only in virtual character execution.

**Verification plan.** The metrics, extractors, thresholds, and failure policies used to compare an execution with the score.

**YAML authoring layer.** A readable source representation for profiles and overrides that compiles into canonical JSON. [S079]

**JSONL evidence stream.** One independent JSON record per line, used for observations, RAG records, metrics, and audit events.
