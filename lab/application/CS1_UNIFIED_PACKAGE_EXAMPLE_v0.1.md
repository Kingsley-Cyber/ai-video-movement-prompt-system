# CPCS UNIFIED DIRECTING PACKAGE — Worked Example (water-bottle UGC, 15s)

Rendered through the v0.1 unified envelope. Kinematic tier intentionally
ABSENT (the frozen runtime supplies no numeric tracks), so every beat is
`authority: proposed` — honest absence, never a guess.

## sync

```yaml
sync:
  schema: cpcs.directing_package/1.0
  clock: { frame_rate: 24, duration_s: 15, frame_count: 360 }
  authority: JSON owns numbers · YAML owns semantics · XML owns order
  bindings:
    yaml: <sha256 of section 1/3>
    json: <sha256 of section 2/3>
    xml:  <sha256 of section 3/3>
  rule: edit any section and the hashes desync — re-resolve before generation
  lineage: { build_id: <cpcs build>, score_id: <cpcs score>, commit: <git> }
```

## 1/3 · YAML — semantics

```yaml
scene:
  content_type: ugc
  style: phone_realism
  duration_s: 15
  delivery: casual_friend_recommendation

actors:
  - actor_id: creator
    look: woman, casual clothing, natural skin
    identity_note: real creator, not an ad actor
  - actor_id: bottle
    kind: object
    look: used water bottle, worn label, personal
    identity_note: product identity persists the whole clip

capture:
  device: performer_operated_phone
  stabilization: moderate
  imperfections: [minor_focus_breathing, small_framing_correction, natural_timing_variation]

protected_invariants:
  - bottle.identity_persists
  - hand_object_contact_never_floats
  - creator.identity_persists

beats:
  - { id: PICK_UP, order: 1, actor: creator, object: bottle,
      action: "picks the bottle up from beside her",
      knowledge: [hand_object_contact, grip_establishment, product_identity],
      origin: USER_EXPLICIT }
  - { id: DRINK, order: 2, actor: creator, object: bottle,
      action: "takes a casual drink",
      knowledge: [grip_persistence, bottle_orientation, liquid_movement, natural_body_response],
      origin: USER_EXPLICIT }
  - { id: APPRAISAL_DIALOGUE, order: 3, actor: creator,
      action: "talks to the camera about why she likes it",
      knowledge: [living_performance, facial_response, gaze_to_camera, dialogue_timing],
      origin: USER_EXPLICIT }
  - { id: PRODUCT_REVEAL, order: 4, actor: creator, object: bottle,
      action: "brings the bottle close, label visible, brief hold",
      knowledge: [product_identity, label_visibility, camera_readability],
      origin: USER_EXPLICIT }

acceptance:
  - bottle never floats; grip never teleports
  - every beat reads on screen; reveal dwells long enough to read the label
  - performance feels unscripted, not ad-like

negative_space:
  - glossy_ad_polish
  - bilateral_perfect_symmetry
  - frozen_face
  - grip_teleport
```

## 2/3 · JSON — canonical truth (numbers only; tracks ABSENT → proposed)

```json
{
  "timebase": { "frame_rate": 24, "duration_s": 15, "frame_count": 360 },
  "controls": {
    "camera.capture_device": "performer_operated_phone",
    "camera.stabilization": 0.45,
    "camera.self_framing_corrections": true,
    "continuity.identity_policy": "preserve_declared_entities",
    "performance.delivery": "casual_friend_recommendation",
    "project.content_type": "ugc",
    "style.realism": "phone_realism",
    "style.capture_imperfections": {"bounded": true,
      "allowed": ["minor_focus_breathing", "small_framing_correction", "natural_timing_variation"]}
  },
  "surface": { "type": "indoor_counter", "reaction": "none_required" },
  "hard_constraints": [
    { "id": "identity_lock", "expression": "bottle.identity_score >= 0.95", "mode": "hard" },
    { "id": "grip_grounding", "expression": "grip_teleport_frames == 0", "mode": "hard" },
    { "id": "no_floating", "expression": "unsupported_flight_frames == 0", "mode": "hard" }
  ],
  "authority": {
    "PICK_UP": "proposed",
    "DRINK": "proposed",
    "APPRAISAL_DIALOGUE": "proposed",
    "PRODUCT_REVEAL": "proposed"
  },
  "kinematic_tier": "absent",
  "verification": [
    { "metric_id": "metric_identity", "target_paths": ["continuity.identity_policy"], "observability": "semantic" },
    { "metric_id": "metric_contact_readability", "target_paths": ["interactions"], "observability": "measured" }
  ],
  "provenance": {
    "note": "no numeric tracks exist in the frozen runtime; every beat stays proposed. CS-1 must serialize structure + timing, never invented motion."
  }
}
```

## 3/3 · XML — order + triggers

```xml
<package>
  <truth href="canonical.json"/>
  <phases>
    <phase id="ACTION_BEATS" authority="proposed">
      <beat ref="PICK_UP" seq="1"/>
      <beat ref="DRINK" seq="2"/>
      <beat ref="APPRAISAL_DIALOGUE" seq="3"/>
      <beat ref="PRODUCT_REVEAL" seq="4"/>
    </phase>
  </phases>
  <camera>
    <track motivation="creator_operated">
      <move trigger="PICK_UP" kind="framing_correction"/>
      <move trigger="PRODUCT_REVEAL" kind="hold_for_readability"/>
    </track>
  </camera>
  <fx>
    <event at="none" kind="none" note="no vfx — capture realism scene"/>
  </fx>
</package>
```

## Why this is multi-character-ready

The same envelope renders the two-fighter anime duel by adding fighters to
`actors`, keying every beat by `fighter_a`/`fighter_b`, and (when a
motion-truth source exists) filling the kinematic tier with root/joint
tracks + timed contacts + camera yaw/pitch — at which point beats flip
from `proposed` to `solved`. One package shape, any cast size.
