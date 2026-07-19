# CPCS-MX Agent Workflow Recipes

## Purpose

This document gives retrieval and compilation recipes for agents using the CPCS-MX corpus. It is operational guidance, not a substitute for the canonical schema or the cited external research.

## Shared agent topology

Use three logically separate roles:

```text
semantic authoring agent
        ↓ proposed authoring YAML
resolver/compiler
        ↓ validated canonical JSON + capability report
verification agent
        ↓ evidence JSONL + compliance report
```

The authoring agent proposes. The compiler resolves and validates. The verifier measures. Do not let one model silently perform all three roles while hiding assumptions.

## Recipe 1 — Natural human movement

### Retrieval bundle

Retrieve records matching:

```text
concepts: locomotion, biomechanics, root motion, contacts,
          breath, mannerism, natural movement
record_type: research_chunk, schema_definition, worked_example
```

Include:

- root-motion and locomotion section;
- kinematics/kinetics section;
- phase/contact section;
- mannerism section;
- natural movement/UGC section;
- `natural_walk.yaml`;
- constraint and verification definitions.

### Authoring requirements

Specify:

- objective and environmental context;
- root trajectory and speed range;
- support-foot schedule or phase targets;
- gait asymmetry only when motivated;
- gaze destination and head lead/lag;
- breath phrase;
- one or two stable mannerisms;
- hard foot-slip and collision limits;
- soft smoothness and natural-variation targets.

### Compilation warning

Do not generate “human imperfection” by adding independent random noise to every joint. Use correlated, low-amplitude variation constrained by support, gaze, task, and character profile.

## Recipe 2 — Realistic UGC recreation with a different performer

### Retrieval bundle

```text
concepts: high-fidelity UGC, mannerism, gaze, breath,
          camera-relative performance, source transfer
```

Add the realistic UGC example, capture profile, camera profile, face/gaze definitions, and evidence taxonomy.

### Decomposition

Separate the reference into:

1. message and persuasive beat;
2. speaking and pause timing;
3. lens-address intervals;
4. root and upper-body movement;
5. hand gesture onset, apex, and recovery;
6. product or prop interaction;
7. blink, gaze break, head nod, and breath;
8. camera movement and framing;
9. editing and caption timing;
10. identity-, wardrobe-, setting-, voice-, and brand-specific fields.

### Transfer policy

```yaml
retain:
  - beat_order
  - gesture_function
  - major_timing
  - gaze_to_lens_duty_cycle
  - camera_grammar
parameterize:
  - gesture_amplitude
  - speaking_rate
  - pause_duration
  - handheld_motion_scale
replace:
  - identity
  - voice
  - wardrobe
  - setting
  - product_or_brand_when_required
```

### Verification

Re-extract and compare beat order, lens-address timing, gesture apex, product visibility, shot duration, and camera motion. “Looks authentic” is not a sufficient standalone metric.

## Recipe 3 — Professionally staged screen action

### Retrieval bundle

Retrieve the staged-combat, contact, phase, biomechanics, camera, and safety chunks plus:

```text
examples/staged_combat_exchange.yaml
profiles/movement/staged_action_base_v2.yaml
profiles/screen_action/staged_near_contact_v2.yaml
profiles/camera/impact_readability_v1.yaml
```

### Causal score

Represent:

```text
preparation
→ support change
→ initiation
→ proximal-to-distal propagation
→ staged near-contact or declared virtual contact
→ audiovisual impact accent
→ reaction delay
→ recoil
→ balance recovery
→ reset
```

Store actor trajectories, support states, target volumes, minimum distance, occlusion, camera-side cheating, sound timing, VFX timing, and recovery independently.

### Safety rule

Default to `staged_near_contact` for screen recreation. Do not convert visual impact cues into instructions for causing injury. A camera cut, flash, sound, recoil, or shake can create impact readability without physical collision.

## Recipe 4 — Anime or sakuga transformation

### Retrieval bundle

Retrieve:

- anime/sakuga research chunk;
- superhuman transformation chunk;
- secondary-motion chunk;
- style-transform schema definition;
- anime-superhuman example;
- cross-style transform example;
- verifier prompt.

### Protected invariants

Declare what must survive stylization:

```text
action identity
causal order
support logic
critical contacts or near-contacts
target readability
screen direction
character identity continuity
recovery destination
```

### Transformable domains

Apply separate functions to:

- phase duration;
- root arc and hang time;
- limb reach through rig, mesh, or perspective domains;
- smear geometry;
- held key poses;
- impact-frame exposure or color;
- camera displacement and shake;
- debris, speed lines, trails, and secondary motion;
- facial effort and breath accents.

Do not use one `style_intensity` value as the entire algorithm. It may select or blend a profile, but the resolved score should contain typed transforms.

## Recipe 5 — Virtual-superhuman movement

### Authoring questions

1. Which physical relation is being altered: gravity, strength, speed, impulse, damping, reach, deformation, or time perception?
2. During which phase is it altered?
3. Which invariants remain human-readable?
4. Is the change in staged-world mechanics, rig articulation, mesh deformation, camera presentation, or VFX?
5. What is the recovery logic?

### Example transform

```yaml
style_transform:
  domain: virtual_superhuman
  protected_invariants:
    - action_order
    - takeoff_contact
    - landing_contact
    - target_readability
  phase_transforms:
    launch:
      impulse_scale: 2.2
      duration_scale: 0.72
    flight:
      virtual_gravity_scale: 0.55
      arc_height_scale: 1.6
    impact:
      reaction_impulse_scale: 1.8
      presentation_only_shake_scale: 1.4
    recovery:
      duration_scale: 1.15
      balance_residual_required: true
```

The values are project controls, not biological safety limits.

## Recipe 6 — Diagnose foot skating

### Retrieve

- root motion;
- contacts and support;
- hard constraints;
- IK and retargeting;
- verification metrics;
- canonical track and contact definitions.

### Diagnostic order

1. Confirm source and output clocks.
2. Confirm foot-contact intervals.
3. Convert root and foot tracks into the same coordinate system.
4. Compute horizontal foot displacement during declared support.
5. Check whether root extraction or retarget scaling changed the relationship.
6. Check IK residuals and joint limits.
7. Check terrain or ground-plane mismatch.
8. Correct the earliest causal layer rather than hiding the error with camera motion.

### Output

The verifier should report:

```json
{
  "metric": "support_foot_slip",
  "contact_ref": "contact.left_foot.003",
  "max_displacement_m": 0.074,
  "threshold_m": 0.020,
  "status": "fail",
  "likely_causes": [
    "root_scale_mismatch",
    "retargeted_leg_length_change"
  ]
}
```

## Recipe 7 — Diagnose unnatural “robotic” movement

Do not use smoothness alone. Retrieve and inspect:

- movement phase overlap;
- proximal-to-distal coordination;
- gaze and head lead;
- breath phrase;
- support transitions;
- mannerism profile;
- secondary motion;
- velocity, acceleration, and jerk;
- asymmetry and task-dependent microvariation.

A perfectly smooth pose sequence may still lack weight transfer, anticipation, contact preparation, gaze intention, breath, or recovery.

## Recipe 8 — Text to CPCS-MX

### Step 1: semantic parse

Extract explicit and missing facts:

```text
who
objective
action
start/end or relative order
target
location
style
emotion/display
camera
contacts
hard requirements
unknowns
```

### Step 2: produce authoring YAML

Use profile references for defaults. Keep unsupplied timing or geometry as unresolved, not invented constants.

### Step 3: compile

Run the deterministic resolver. Require:

- schema validation;
- time and unit normalization;
- profile version resolution;
- asset hash verification;
- lock and precedence report;
- unsupported or unresolved field report.

### Step 4: choose execution carrier

| Need | Preferred carrier |
|---|---|
| semantic approximation | text prompt |
| key poses | first/last or sparse reference frames |
| exact screen-space body motion | pose-control video |
| editable contact and balance | rigged animation with IK |
| precise camera | camera trajectory or previsualization render |
| exact masks/occlusion | mask or segmentation video |
| stylized timing and effects | compositor/edit event package |

### Step 5: verify

Re-extract output into observation JSONL and compare against the locked canonical score.

## Recipe 9 — Retrieval query templates

### Concept question

```text
How does CPCS-MX distinguish Laban Effort from mechanics and force?
```

Filter:

```text
record_type in [research_chunk, schema_definition]
concepts contains Laban
```

### Schema question

```text
Which fields encode phase-specific virtual gravity without changing anatomical joint limits?
```

Filter:

```text
record_type = schema_definition
schema_fields or concepts contains styleTransform
```

### Implementation question

```text
How should an agent compile an anime action profile while preserving contact invariants?
```

Retrieve one record from each group:

```text
research_chunk
schema_definition
worked_example
prompt_template
package_document
source
```

### Evidence question

```text
Which parts of the recommendation are established research and which are CPCS-MX proposals?
```

Use `evidence_labels` and resolve all `source_ids` before answering.

## Recipe 10 — Context assembly policy

For each answer or authored score, assemble context in this order:

1. direct research chunk;
2. relevant schema definition;
3. one closest worked example;
4. applicable agent prompt;
5. source records for external claims;
6. safety/rights documentation when identity, combat, or reference transfer is involved.

Avoid retrieving many superficially similar examples without the governing definition. Examples demonstrate syntax; they do not define universal human constants.
