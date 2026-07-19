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

## Lab-original findings NOT in the paper (novel contributions)

- **Anti-AI-skin rule** — never "smooth"; name microtexture + forbid list (p001, high confidence).
- **Device-signature realism** — "iPhone 12" as a named capture profile (Smart-HDR, cool WB, NR smear).
- **30fps-vs-24 cadence tell** for phone-real vs filmic (p002, pending isolation).
- **<2000-char compact combined formats** as a practical Mode-A packaging discipline.

These are candidates to fold back into the research corpus as new evidence cards.
