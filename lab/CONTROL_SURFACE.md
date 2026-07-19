# Control Surface — the full map of what we can control (and what's unexplored)

> This is the *working* view of active channels. The **complete research-grounded inventory** — every
> modular concept in the paper with section refs and lab status — is `CONCEPT_INDEX.md`.

There are **two control paradigms** in this system. Most work so far has explored only the first.
This file catalogs every control *channel*, its paradigm, whether it's been tested, and a test idea —
so the lab can drive experiments against the gaps. Update `status` + `evidence` as runs come in.

## The two paradigms

| Paradigm | What the model consumes | Best for | Proven in |
|---|---|---|---|
| **descriptive_prose** | natural-language description | look, skin, vibe, performance *feel* (UGC) | v001–v004 |
| **numeric_canonical_truth** | explicit numeric tracks (keyframes, timings, vectors) | precise motion, choreography, timing, contact, identity lock | v005 (combat) |

Key finding (p008): for **motion/choreography**, numeric canonical truth carries precision prose
cannot — v005 was driven by JSON *alone* ("really good hand-to-hand… good for anime"). This refines
p006: format is realism-neutral for *look*, but numeric structure is a genuine control channel for
*motion*.

## Channel catalog

Status: `proven` (a good run confirms it) · `partial` (bundled/seen, not isolated) · `unexplored`.

### A. Descriptive-prose channels (look & feel)
| Channel | Controls | Status | Evidence |
|---|---|---|---|
| camera.device / iPhone signature | realism of image | proven | v001 |
| lighting (flat/window/…) | cinematic vs raw | partial | v003 vs v001 |
| skin.strategy (microtexture vs smooth) | the #1 AI tell | **proven** | v001 vs v004 |
| performance.direction (loose vs scored) | ad vs candid | partial | v003 |
| face.motion (descriptive) | stiff vs alive face | partial | v001 |
| render_style (raw vs cinematic) | reads as UGC vs ad | partial | v003 vs v001 |

### B. Numeric-canonical-truth channels (motion & precision)
| Channel | Controls | Status | Evidence / Test idea |
|---|---|---|---|
| body kinematics (`root_motion` + `joint_tracks` position keyframes) | exact limb/body trajectories | **proven** | v005 |
| contact solver (`contacts`: region_a/region_b, timing, tolerance, type impact/near_miss/grasp) | strikes land, timing, no phasing | **proven** | v005 |
| Laban effort as numeric vectors (`lab_control` weight/time/space/flow ∈ [-1,1] over intervals) | movement *quality* per beat | **proven (combat)** | v005 — **unexplored for UGC/face** |
| camera keyframes (position/orientation over time) | shot path, framing over time | proven (combat) | v005 — **unexplored for UGC** |
| hard-constraint + verification blocks (identity_lock, no_slow_mo, contact tolerance, machine-checkable) | enforce & auto-grade the render | partial | v005 authored them; **verification not yet run against an output** |
| microvariation / transition_smoothness / biomechanical realism | naturalness of motion | unexplored | present in YAML, never isolated |

### C. Unexplored control sub-concepts (the frontier you flagged)
These are the biggest opportunities — none tested yet.

1. **FACS as a numeric AU track (facial canonical truth).** We've only used FACS *descriptively*.
   Build a time-indexed AU-intensity track (like `joint_tracks`, but per action unit) as canonical
   truth for a talking-head. *Test:* does an AU curve improve lip-sync + expression precision vs prose
   FACS? Domain: ugc_talkinghead + anime.
2. **Body-control adjustment as tracks.** Center-of-mass / balance curve, weight-shift curve, gaze
   vector over time, breathing amplitude — as numeric channels rather than words. *Test:* gaze-vector
   track vs "gaze-to-lens 0.7" prose — which holds eye contact better?
3. **Effort-vector control for non-combat.** Apply `lab_control` effort ramps to a UGC gesture or a
   dance. *Test:* does a light/sudden effort vector on the hook beat read as more alive than prose?
4. **Contact taxonomy beyond combat.** grasp / press / tap / hold-object contacts for product
   handling. *Test:* does a `contact` on hand↔product fix floaty product holds in UGC?
5. **Style medium channel.** `medium: photorealistic | anime_cel | 2.5d`. v005 was flagged "good for
   anime." *Test:* same kinematic truth, medium=anime_cel vs photorealistic.
6. **Speed / time-warp channel.** Currently forced to 1.0x. *Test:* controlled ramp on the apex frame
   only — does it help or break "no slow-mo" realism?
7. **Identity-lock tokens / reference binding.** v005 asserts `identity_score>=0.95` as a constraint;
   we haven't tested what actually holds identity across fast motion (reference image? seed? token?).
8. **Verification loop (closed feedback).** Actually *run* the `verification.metrics` against a
   generated clip (contact timing, identity drift, cut detection) instead of only authoring them.
   This turns the lab from manual scoring toward auto-scoring.

## How to explore a channel

Pick a row with `status: unexplored`, create a variant that toggles just that channel (hold the rest
constant), render A/B, log runs, and — if it moves a dimension — promote a pattern. Add new lever
values to `registry.yaml → levers` when a channel becomes a recurring knob (e.g.
`facial_control: {values: [prose_facs, au_track]}`).
