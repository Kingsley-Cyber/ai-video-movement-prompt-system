# CONCEPT INDEX — every modular video-control concept in the research, mapped to lab status

The complete catalog of modular concepts from the research paper
(`research/.../paper/CPCS_FACS_Laban_AI_Video_Directorial_Control_Research_Paper.md`), each mapped to
its paper section, what it controls, and its **lab status**. This is the master inventory the lab
tests against: `CONTROL_SURFACE.md` is the working view of active channels; this file is the full
research-grounded space. When composing (AGENTS.md) needs a capability with no tested block, find the
concept here first — compose from the paper's definition, flag unproven, propose the A/B.

Status: **proven** (validated run) · **partial** (used/bundled, not isolated) · **unexplored** ·
**far-frontier** (needs tooling/training access, not promptable today).

## 1. The layered stack (§3)

| Concept | § | Controls | Status | Lab hook |
|---|---|---|---|---|
| Layer A narrative intent | 3.1 | objective, subtext, beat purpose | partial | communication graph (hook→proof→CTA) |
| Layer B dimensional affect (VAD trajectory) | 3.2, 5 | valence/arousal/dominance over time | partial | `affect_vad` field (v001/v003) |
| Layer C visible performance description | 3.3 | what the audience literally sees | proven | the prose paradigm itself |
| Layer D motion realization | 3.4, 9 | trajectories, phases, contacts, dynamics | proven (kinematics) | v005, `blk_kinematic_skeleton` |
| Layer E cinematic presentation | 3.5 | camera, edit, framing | partial | camera keyframes (v005); prose camera (v001) |
| Layer F generative conditioning | 3.6, 14 | what the target model actually accepts | partial | Mode A prompt-only; Tier 2+ unexplored |

## 2. Facial control (§4)

| Concept | § | Controls | Status | Lab hook |
|---|---|---|---|---|
| FACS AUs as control vocabulary | 4.1 | which muscles move | partial | prose FACS in v001/v003; `facs_laban_reference.md` |
| Temporal AU events (onset→apex→offset) | 4.2 | expression *shape in time*, no snap-on | partial | timed `facs_events` (v003) |
| Intensity calibration (A–E) | 4.3 | trace→max; C-peak realism discipline | partial | intensity fields in scored variants |
| Coarticulation, dependencies, incompatibilities | 4.4 | plausible AU combos (AU6+12 Duchenne etc.) | partial | genuine-vs-fake table in skill refs |
| Gaze, head pose, blinks, breathing | 4.5 | the non-AU face channels | partial | gaze_track/blink_track/breath_track (v001·yaml) |
| FACS as numeric AU track (canonical truth) | 4.2+19 | face analog of joint keyframes | **unexplored — TOP experiment** | `blk_facs_au_track` (E-queue #2) |

## 3. Affect (§5)

| Concept | § | Controls | Status |
|---|---|---|---|
| Affect as trajectory, not shot tag | 5.2 | emotional arc across the clip | partial (interval VAD in v001) |
| Affect ≠ FACS (don't collapse) | 5.3, 8 | inner state vs facial surface | adopted as doctrine |
| Character state vs performed display | 5.5 | concealment, social smiles, acting layers | unexplored (rich for drama) |

## 4. Body, movement quality (§6–7)

| Concept | § | Controls | Status | Lab hook |
|---|---|---|---|---|
| Motion atoms (reach, strike_like, duck, pivot…) | 6.3 | discrete action vocabulary | proven | Pegasus extraction + v005 beats |
| BAP/BACS posture coding | 6.1–6.2 | posture/action categories | unexplored (research vocab) | |
| Laban Effort (weight/time/space/flow) — words | 7.3 | movement quality, descriptive | partial | v001/v003 prose |
| Laban Effort — numeric vectors [-1,1] | 7.7 | movement quality, canonical | proven (combat) | `blk_effort_vectors` (v005); UGC untested |
| Laban Shape (rising/advancing/enclosing…) | 7.4 | body sculpting space | partial | shape events in v00x yaml |
| Laban Space / Labanotation symbolic planning | 7.5–7.6 | spatial intent, kinesphere | unexplored | |
| Laban as style-preserving modifier | 7.8 | same action, different quality (style transfer) | unexplored — high value | |

## 5. Motion realization stack (§9)

| Concept | § | Controls | Status | Lab hook |
|---|---|---|---|---|
| Root motion + joint kinematics | 9.1 | exact trajectories | **proven** | v005 |
| Pose ≠ movement (transitions carry meaning) | 9.2 | doctrine | adopted | |
| Global motion phase | 9.3 | prepare→execute→recover macro-rhythm | partial (combat beats) | |
| Local per-limb phase | 9.4 | limb-level timing offsets | unexplored | paper §29.4 calls it an editable interface |
| Contact & support (feet, hands, objects) | 9.5 | grounding, no floating/phasing | proven (combat contacts) | `blk_contact_solver`; product-handling untested |
| Center of mass, balance, support geometry | 9.6 | weight believability | unexplored (numeric CoM track) | |
| Dynamics: weight, momentum, impact | 9.7 | force reads | partial (implied by contacts) | |
| Smoothness/jerk, intentional sharpness | 9.8 | motion texture | partial (`transition_smoothness` in v005 yaml) | |
| Microvariation / biological plausibility | 9.9 | anti-robotic noise | partial (`microvariation: 0.05`) — never isolated | |

## 6. Locomotion (§10)

| Concept | § | Status |
|---|---|---|
| Locomotion as multi-layer score; gait events/phase | 10.1–10.2 | unexplored (walk appeared only in reverse extraction) |
| Stylistic walking via Laban; running | 10.3–10.4 | unexplored |
| Locomotion verification (foot-skate etc.) | 10.5 | unexplored — pairs with §26.7 |

## 7. Multi-actor combat (§11)

| Concept | § | Controls | Status |
|---|---|---|---|
| Choreography as coupled system | 11.1 | attacker/defender dependency | proven (v005 5-exchange) |
| Kinetic chains | 11.2 | force path through body | unexplored |
| Contact vs staged contact | 11.3 | real hit vs sold hit | partial (impact vs near_miss types in v005) |
| Reaction timing | 11.4 | defender response windows | proven-ish (contact windows) |
| Momentum transfer & follow-through | 11.5 | physical continuity of exchanges | partial |
| Weapons and props | 11.6 | held-object choreography | unexplored |
| Camera & editing in action | 11.7 | readability of fast action | partial (static-ish cam in v005) |

## 8. The CPCS score mechanics (§12)

| Concept | § | Controls | Status |
|---|---|---|---|
| Canonical timebase | 12.2 | one clock, all tracks | proven (v005 timebase) |
| Hard / soft constraints / preferences | 12.3 | enforcement tiers | proven (authored) — enforcement untested |
| Constraint graph | 12.4 | cross-constraint dependencies | unexplored |
| Elastic vs fixed timing | 12.5 | which beats may stretch | unexplored |
| Score granularity | 12.6 | how deep to specify | implicitly explored (prose vs numeric = the two paradigms) |
| Uncertainty & alternatives in the score | 12.7 | authored variation | unexplored |

## 9. Structured languages & compilation (§19 — the format chapter)

| Concept | § | Status | Lab hook |
|---|---|---|---|
| **Serialization ≠ control** | 19.1 | **validated** | = our p006 ("format ≠ realism for look") |
| Mode A: structured text pasted into prompt field | 19.2.1 | **proven — our whole method** | all variants |
| Mode B: LLM-mediated interpretation | 19.2.2 | partial (agent compose mode is Mode B) | AGENT_PROMPT.md |
| Mode C: deterministic compiler/workflow engine | 19.2.3 | unexplored | |
| Mode D: native structured conditioning | 19.2.4 | far-frontier (needs API control channels) | |
| **Three-representation architecture (YAML author / JSON canonical / XML envelope)** | 19.3 | **validated empirically** | King's YAML-in-XML, YAML+JSON, tri-format = §19.14/19.15/19.16 working |
| Typed control contracts: FACS/Laban/Combat/Director/VFX/Marketing | 19.4 | partial | our blocks are informal versions |
| YAML authoring shape; direct YAML prompting | 19.5 | proven | v001 lineage |
| JSON canonical + schema validation; pointer/patch; hashing | 19.6 | proven (v005) / patch-workflow unexplored | |
| XML director envelope; XML+JSON embedding | 19.7, 19.15 | proven (hybrid clip package) | `blk`-hybrid assets |
| JSONL for retrieval/eval streams | 19.8 | unexplored (results.csv plays this role) | |
| Style = typed domains, not one adjective | 19.9 | adopted | style_overrides in v005 yaml |
| Scope cascade, merge precedence, lock/final semantics | 19.10 | unexplored | |
| Typed merge algebra; timeline splice/blend | 19.11 | unexplored | |
| Conflict reports & provenance | 19.12 | partial (lab provenance fields) | |
| Capability negotiation + loss budget | 19.19 | unexplored — becomes relevant per-model | |
| Backend adapters (Sora/Veo/Runway param split) | 19.20 | partial (per-model notes in skill) | |
| Compilation tiers: 1 prompt-only / 2 multimodal / 3 render-assisted | 19.21 | Tier 1 proven; Tier 2 (ref stills = entry); Tier 3 far-frontier | |
| Marketing controls as testable requirements | 19.23 | proven-ish | UGC verification targets |
| VFX/anime as separate causal layer | 19.24 | unexplored | anime-medium experiment queued |
| Security / robust parsing | 19.25 | adopted in repo hygiene | |
| 8 deterministic verification checkpoints | 19.26 | unexplored as pipeline | E-queue #1 is checkpoint 7-ish |

## 10. Generative conditioning classes (§14) — mostly Tier-2+ frontier

| Concept | § | Status |
|---|---|---|
| Symbolic/text conditioning | 14.1.1 | proven (it's all we use) |
| Continuous sequence conditioning (motion tracks as model input) | 14.1.2 | far-frontier |
| Spatial control maps / rig-geometry conditioning | 14.1.3–4 | far-frontier |
| Sampling-time guidance; post-generation editing | 14.1.5–6 | unexplored |
| Spatiotemporal tokens; hierarchical conditioning | 14.2–14.3 | far-frontier |
| Decoupling motion from appearance | 14.4 | **partially validated** — our still-anchor (appearance) + prompt (motion) split |
| Camera conditioning; actor-relative camera grammar | 14.5–14.6 | partial (v005 keyframes) |
| Per-frame text vs structured events | 14.7 | unexplored |
| Audio/performance synchronization | 14.8 | partial (say-lines with native Veo audio) |

## 11. RAG & knowledge objects (§17)

| Concept | § | Lab analog |
|---|---|---|
| Concept / evidence / performance-template / shot-template / calibration-profile / **failure card** | 17.2 | blocks = performance templates; v004 = a failure card; calibration profiles unbuilt |
| Hybrid retrieval, query decomposition, provenance separation | 17.5–17.7 | registry.yaml is the miniature |

## 12. Storyboard→direction tooling (§20)

Beat sheet (20.2) ≈ our communication graph — partial. Director/actor/choreographer/cinematographer
views (20.3), directorial override (20.4), variant generation (20.5) ≈ our variants — partial.

## 13. Evaluation & compliance (§24) — the measurement frontier

| Concept | § | Status |
|---|---|---|
| Compliance measured separately from visual quality | 24.1 | adopted (rating dims) |
| Facial / affect / Laban / kinematic / phase / contact / camera / identity compliance metrics | 24.2–24.10 | unexplored as automation — E-queue #1 (round-trip re-extraction) is the entry |
| Multi-objective scorecard | 24.13 | results.csv is the manual version |

## 14. Experimental program (§25)

Factorial ablation (25.2), task suite (25.3), baselines (25.4), reproducibility (25.5) — the lab
implements the lightweight version: one-lever A/Bs = single-factor ablation; `evals`-style task suite
unbuilt.

## 15. Failure-mode library (§26) — diagnostic vocabulary

15 named failures. Observed so far: **v003** ≈ semantic overcommitment / over-direction; **v004** =
plastic-skin (a LAB-ORIGINAL failure the paper does not name). Watchlist for future runs: foot skating
(26.7), floating/penetration (26.8), premature reaction (26.9), camera–actor entanglement (26.10),
identity drift under extreme motion (26.11), over/underconstraint (26.12–13), metric gaming (26.15).

## 16. Reverse distillation (§30) — the extraction side

| Concept | § | Status |
|---|---|---|
| Evidence classes (measured/detected/inferred/interpreted/authored) | 30.3 | adopted in extraction prompts |
| Temporal pyramid (not one sampling rate) | 30.5 | adopted (slowed-proxy caveat) |
| Stages 0–11 extraction pipeline | 30.7–30.19 | partial — Pegasus movement extraction session = stages 3/6-ish |
| Video Observation Graph (VOG) | 30.21 | unexplored locally |
| Reverse compilation into CPCS | 30.22 | proven manually (TikTok walk→grab→hold recreation) |
| Fight & UGC detailed workflows | 30.23–30.24 | partial |
| **Round-trip verification (re-extract the generated video, diff vs authored truth)** | 30.26 | **unexplored — E-queue #1, highest-leverage** |

## 17. Research agenda (§29) — far-frontier parking lot

Shared open score standard · learned direction→score compiler · joint face–body–voice · per-limb
phase as editable UI · differentiable cinematography · physics-aware diffusion · retrieval of
performance-not-stereotype · causal evaluation · director-in-the-loop learning · cross-shot
continuity · distillation benchmarks.

---

## Session discoveries ↔ paper crosswalk

| Lab finding | Paper concept it validates |
|---|---|
| JSON canon truth alone drove the fight scene (r005) | Mode A with canonical JSON (§19.6); numeric Layer D sufficiency |
| YAML-in-XML / YAML+JSON house formats | §19.14–19.16 combined-format architecture |
| "Format ≠ realism for look" (p006) | §19.1 Serialization Is Not Control |
| Still-anchor locks identity/skin, prompt drives motion | §14.4 motion–appearance decoupling |
| One-lever A/Bs in the lab | §25.2 factorial ablation (lightweight) |
| v004 failure record | §17.2.6 failure card |

## Part 2 — RDC paper (Pegasus Atomic Video Deconstruction, CPCS-PEGASUS-RDC-2026-01)

Source: `research/Pegasus_Atomic_Video_Deconstruction_and_Modular_AI_Recreation_v1.0.md` — the
operational companion (deconstruction→recreation engine). Every concept below has a retrievable card
in `concepts.jsonl`; this table is the paper-section map.

| Concept | RDC § | Status | Card |
|---|---|---|---|
| Atomic deconstruction (transfer-useful atoms w/ provenance) | 2.1 | partial | c_atomic_deconstruction |
| 4-verb transfer policy + locks w/ tolerances | 2.2, 18, 27 | unexplored | c_transfer_policy |
| Reverse Directorial Compilation (underdetermined; keep alternatives) | 2.3 | partial | c_rdc |
| 8-layer fidelity (narrative→stylistic) | 2.4 | unexplored | c_fidelity_layers |
| Pegasus role contract + operational constraints (4s min clip, schema>prompt, single-mode batches, 261k/98k tokens) | 3 | partial | c_clipped_analysis, c_schema_over_prompt |
| Evidence classes (5) | 4.3 | proven (adopted) | c_evidence_classes |
| 9-level atomic ontology + 11 cross-cutting layers | 5 | partial | c_atomic_ontology |
| Four-format doctrine + dense-signals-stay-media | 6 | proven/partial | c_house_formats, c_dense_assets_media |
| 8-pass strategy (Pass 0 source map … Pass 7 contradiction QC) | 8 | partial | c_multipass_strategy, c_source_map_pass, c_contradiction_pass |
| Analysis modes: structured JSON, segment defs, clipped, reference-image, batch | 9 | partial | c_reference_image_prompting |
| Measurement stack: SAM 2 / OpenPose-class / RAFT / EMOCA | 11 | partial | c_measurement_stack |
| Camera/object motion separation (MotionCtrl precedent) | 11.6, 24.4 | unexplored | c_camera_object_separation |
| Fusion precedence hierarchy (typed, not absolute) | 12.1 | unexplored | c_precedence_hierarchy |
| Temporal snapping (raw + resolved times) | 12.3 | unexplored | c_temporal_snapping |
| UGC layers: authenticity cues, marketing variables (duty cycle, time-to-first-X) | 15–16 | proven/partial | c_authenticity_cues, c_marketing_variables |
| Fight layers incl. phase landmarks; screen-space truth for anime | 22, 24.5 | partial/unexplored | c_phase_landmarks, c_screen_space_truth |
| Optional physics refinement (DeepMimic) | 24.6 | unexplored | c_physics_refinement |
| 5 compilation tiers (adds rigged intermediate + v2v neutral control render) | 19, 28 | partial | c_compilation_tiers, c_neutral_control_render |
| Adapter capability contract + unsupported-controls report | 30.4, 33 | unexplored | c_adapter_contract |
| Compiler resolution order + typed merge (LLMs must not improvise merges) | 32 | unexplored | c_resolution_order |
| Validation metrics + acceptance profiles (DTW, spectrum similarity) | 20, 29 | unexplored | c_validation_metrics |
| Information-preservation accounting per hop | 30 | partial | c_info_preservation |
| Failure-mode → deterministic-response table (12 rows) | 38 | partial | c_failure_modes |
| SDK patterns (sync structured + async segment defs) | 36–37 | partial | — (code in paper) |

**Cross-validation:** RDC independently confirms the lab's two-lane runbooks, evidence classes, house
formats, p006 ("tokenizable ≠ executable"), and p007 (its own failure mode "UGC becomes too polished").

## Part 3 — MX paper (CPCS-MX Hierarchical Motion Grammar v1.0)

Source: `research/CPCS_MX_Hierarchical_Motion_Grammar_Research_Package_v1.0/` — the *motion-grammar
engine*: a compiler (`scripts/compile_authoring_yaml.py`), reusable `profile://` ingredients (adopted
into `lab/profiles/`), and cross-style transforms. Where CPCS defined the control language and RDC the
deconstruction machine, MX defines **exact, expressive, stylized, and superhuman motion + modular
style switching.** Cards in `concepts.jsonl`; workflow in `RUNBOOK_cross_style_switching.md`.

| Concept | MX § | Status | Card |
|---|---|---|---|
| Layered motion architecture (time/root/joints/dynamics/Laban/FACS/signatures/secondary) | 3 | partial | (spans many cards) |
| Time/clocks/units/coordinate systems | 4 | proven (adopted) | — (in runbooks) |
| Skeleton topology, DoF, joint limits | 5 | unexplored | c_ik_retargeting |
| Root motion + locomotion score | 6 | unexplored | c_locomotion_score |
| Joint tracks, rotation reps (rot6d), interpolation | 7 | unexplored | c_rotation_representation |
| Kinematics/kinetics/momentum/inverse dynamics | 8 | unexplored | c_dynamics_kinetics |
| IK, retargeting, morphology | 9 | unexplored | c_ik_retargeting |
| Motion phases, contacts, action graphs | 10 | proven | c_action_atoms, c_phase_landmarks, c_contact_solver |
| Hard / soft / **perceptual** constraints (silhouette readability) | 11 | unexplored | c_perceptual_constraints |
| Laban as control layer + computational proxies | 12–13 | partial | c_laban_efforts, c_effort_proxies |
| FACS/gaze/breath/upper-body sync | 14 | partial | c_facs_events, c_face_motion_alive |
| Mannerisms, postural tone, movement signatures | 15 | unexplored | c_mannerisms_signatures |
| Natural movement + correlated (not white-noise) variation | 16 | proven/partial | c_correlated_variation, c_authenticity_cues |
| Staged combat, multi-actor coding | 17 | proven | c_kinematic_truth, c_contact_solver |
| Anime/sakuga/limited animation/cartoon physics | 18 | partial | c_style_transform_vector, c_screen_space_truth |
| Superhuman as constrained transformation | 19 | partial | c_superhuman_transform |
| Secondary/overlapping motion (cloth/hair/follow-through) | 20 | unexplored | c_secondary_motion |
| BVH/FBX/dense arrays/canonical interchange | 21 | partial | c_dense_assets_media |
| Procedural animation, motion matching, engine execution | 22 | unexplored | c_motion_matching |
| AI motion synthesis + controllable video gen | 23 | partial | c_execution_carrier |
| Text-to-CPCS-MX compilation | 24 | partial | c_execution_carrier, c_three_agent_topology |
| Canonical schema design | 25 | proven (adopted) | — |
| Constraint resolution & compilation (typed merge, profile://) | 26 | partial | c_profile_system, c_resolution_order |
| Verification & perceptual evaluation | 27 | unexplored | c_validation_metrics |
| **Cross-style modular switching** (content/perf/style/presentation; typed transform; ablation) | 28 | partial | c_content_perf_style_presentation, c_style_transform_vector, c_protected_invariants, c_style_ablation |
| Agent architecture (authoring/compiler/verifier) | 29 | partial | c_three_agent_topology |

**Adopted assets:** 8 `profile://` profiles → `lab/profiles/` (see its README). Frozen originals +
the reference compiler live under `research/`.

**Cross-validation:** MX §28.9 **style ablation** = the lab's one-lever A/B applied to style; MX §16
correlated-variation confirms and sharpens the lab's anti-robotic finding; MX's profile inheritance =
the compiler-backed form of `blocks.yaml`.

## Lab-original findings NOT in the paper (novel contributions)

- **Anti-AI-skin rule** — never "smooth"; name microtexture + forbid list (p001, high confidence).
- **Device-signature realism** — "iPhone 12" as a named capture profile (Smart-HDR, cool WB, NR smear).
- **30fps-vs-24 cadence tell** for phone-real vs filmic (p002, pending isolation).
- **<2000-char compact combined formats** as a practical Mode-A packaging discipline.
- **Format-as-diversity-lever** (p009): same prompt across NL/YAML/XML/JSON/combos renders *different*
  outputs — used deliberately for variance/options, not quality. Nuances p006; not stated as a *liked
  lever* in any paper.
- **Owner kinematic detail layers** (v005 lineage): frame-budget math, character body profiles,
  spatial geometry, tempo/power curves, per-beat body mechanics, quantified audio — the two-document
  (authoring + kinematic canonical) architecture pushed to production depth. Cards: c_frame_budget,
  c_character_profile, c_spatial_geometry, c_tempo_curve, c_body_mechanics, c_audio_spec,
  c_two_document_architecture.

These are candidates to fold back into the research corpus as new evidence cards.
