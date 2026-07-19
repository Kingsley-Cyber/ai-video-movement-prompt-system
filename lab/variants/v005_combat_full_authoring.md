# v005 — FULL AUTHORING ARTIFACT (fight scene, tri-layer style)

This is the complete authored artifact behind `v005_combat_kinematic_json.jsonc`. It uses the paper's
**three-representation architecture** (§19.3): prose brief → YAML authoring source → JSON canonical
truth. **Only the JSON layer was pasted to the model** (`authoring_layers: json_canonical`) and it
alone produced the validated result — "really good choreograph fight scene … good for anime."
(YAML indentation restored here; it was flattened in transport.)

---

## Layer 1 — Prose brief (directorial intent)

**CPCS Combat Test: Fast Hand-to-Hand Kung Fu Exchange**

Goal: Test the model's tracking, fast choreography, and identity preservation with minimal VFX and no
slow-mo. Pure raw movement.

Style: Naruto vs Pain — intense, grounded, back-and-forth hand-to-hand combat. No flashy effects.
Just bodies moving fast.

**The Scene: "Five-Exchange Kung Fu Duel" (8 Seconds)**

- Fighter A (Naruto-style) — Orange accent, aggressive, throws strikes.
- Fighter B (Pain-style) — Dark accent, defensive-counter, redirects.

| Beat | Window | Action |
|---|---|---|
| 1 | 0–1.5s | A throws a right punch. B parries with left forearm. |
| 2 | 1.5–3.0s | B counters with a left palm strike to A's chest. A absorbs and steps back. |
| 3 | 3.0–4.5s | A throws a left hook. B ducks under and pivots. |
| 4 | 4.5–6.0s | A throws a right straight. B redirects with a palm deflection. |
| 5 | 6.0–8.0s | A throws a left hook. B catches A's arm, shoves him back. They reset. |

Constraints: NO SLOW-MO (1.0x). NO VFX (no flashes, sparks, impact frames). HARD: continuous unbroken
sequence; body identity consistent (no morphing); fists reach targets within 0.05 m tolerance.

## Layer 2 — YAML authoring source (creative intent)

```yaml
# kungfu_combat_test.yaml
schema: "cpcs-authoring/1.1"
document_id: "combat.test.fast_exchange"
project: "movement_tracking_test"

imports:
  - id: "stick_rigs"
    uri: "asset://skeletons/combat_sticks.json"
    media_type: "application/cpcs+json"
    sha256: "abc123..."

scope:
  project: "combat_benchmark"
  shot: "fast_exchange_01"

shot:
  duration_s: 8.0
  fps: 24
  aspect_ratio: "16:9"

style_overrides:
  visual:
    medium: "photorealistic"
    contrast: 1.0
    vfx: "none"            # <-- NO VFX. Pure movement.
  motion:
    realism: "biomechanical"
    transition_smoothness: 0.90
    microvariation: 0.05

narrative:
  objective: "Test fast back-and-forth combat tracking."
  audience_takeaway: "This is pure, unbroken hand-to-hand action."

beats:
  - id: "b01.exchange_1"
    start: 0.0
    end: 1.5
    label: "A throws right punch → B parries"
    description: "A steps in, right straight. B parries with left forearm."
  - id: "b02.exchange_2"
    start: 1.5
    end: 3.0
    label: "B counters left palm → A absorbs"
    description: "B strikes chest with left palm. A recoils, steps back."
  - id: "b03.exchange_3"
    start: 3.0
    end: 4.5
    label: "A throws left hook → B ducks"
    description: "A winds up left hook. B ducks under, pivots right."
  - id: "b04.exchange_4"
    start: 4.5
    end: 6.0
    label: "A throws right straight → B deflects"
    description: "A right straight. B redirects with open palm deflection."
  - id: "b05.exchange_5"
    start: 6.0
    end: 8.0
    label: "A left hook → B catches, shoves"
    description: "A left hook. B catches A's arm, pushes A back. Reset."

constraints:
  - id: "continuous_motion"
    expression: "No cuts. No slow-mo. Continuous unbroken 8s sequence."
    mode: "hard"
  - id: "identity_preservation"
    expression: "Fighter A and B must not morph or swap identities."
    mode: "hard"
    minimum_score: 0.95
  - id: "contact_accuracy"
    expression: "Fist-to-target distance < 0.05m at contact times."
    mode: "hard"
    tolerance_m: 0.05
```

## Layer 3 — JSON canonical truth (motion & kinematics)

See `v005_combat_kinematic_json.jsonc` — the layer that was actually pasted, and sufficient alone.

## Style notes (why this artifact matters)

- The tri-layer shape is the paper's §19.3 architecture working in practice: YAML = human authoring,
  JSON = canonical machine truth, prose = intent. §19.22 has the paper's own worked cross-format
  action-trailer version of this same pattern.
- Open question logged as an experiment idea: would pasting YAML+JSON (or all three layers) beat
  JSON-only, or dilute it? (`authoring_layers` lever.)
