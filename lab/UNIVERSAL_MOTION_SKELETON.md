# UNIVERSAL MOTION SKELETON — 14 layers × 3 formats

The canonical skeleton for ANY video motion control (UGC gesture, walk, fight, dance, anime,
superhuman), with the **format map woven in**: every control lives in the format that owns it
(`FORMAT_CONTROL_MAP.md`). Three skeletons, one score:

```
YAML (director authors intent)  +  JSON (machine canonical truth)  +  XML (ordered script & triggers)
        — merged by the compiler into one resolved canonical JSON; XML references JSON by sha256 —
```

Sources: MX §3.1 (the 14-layer stack) + MX Appendix A.1–A.16 (field dictionary) + MX canonical schema
top-level keys + CPCS §19.4 (typed control contracts) + RDC §6/§12 (formats, precedence, evidence).
Coverage audit at the bottom proves nothing in the papers is dropped.

## Layer × format assignment (the woven map)

| # | Layer | YAML (intent) | JSON (precision) | XML (order/triggers) |
|---|---|---|---|---|
| 1 | Intent | ✅ owner | — | ✅ ordered script prose |
| 2 | Action graph | ✅ action atoms (labels/phases) | ✅ resolved graph + frames | ✅ beat order + event marks |
| 3 | Phase | ✅ phase labels/policy | ✅ phase curves, local offsets | — |
| 4 | Root & balance | — | ✅ owner | — |
| 5 | Joint kinematics | — | ✅ owner | — |
| 6 | Contact & interaction | ✅ safety/contact policy | ✅ exact events + tolerances | ✅ impact trigger marks |
| 7 | Dynamics | ✅ physics_mode intent | ✅ owner (numbers) | — |
| 8 | Laban/BESS | ✅ words + phrasing | ✅ float vectors | — |
| 9 | Face & affect | ✅ affect arcs (VAD knots) | ✅ AU spline curves | ✅ AU/gaze/blink/breath TRIGGERS |
| 10 | Mannerism | ✅ owner (profile) | — | — |
| 11 | Secondary motion | ✅ art direction | ✅ solver params + cache refs | — |
| 12 | Stylization/VFX | ✅ style transform + invariants | ✅ resolved transform values | ✅ vfx: event triggers |
| 13 | Presentation | ✅ high-level camera/edit intent | ✅ camera 6DoF + lens + retime map | ✅ cam:/audio:/edit event triggers |
| 14 | Verification | ✅ acceptance thresholds | ✅ owner (metrics, reports) | — |
| — | SPINE (identity/time/coords/authority/rights) | ✅ declares | ✅ resolves | ✅ envelope + hash refs |

---

## SKELETON 1 — YAML (the director's authoring document)

Human-authored creative intent: inheritance, words, arcs, policies, thresholds. No dense numbers.

```yaml
cpcs_mx:                                        # authoring root (MX authoring schema)
  document_id: <id>
  extends: ["profile://movement/<p>", "style://<genre>/<p>@<ver>"]   # style inheritance — YAML superpower
  imports: {canonical_score: {type: json, path: ../canonical/score.json, sha256: <hash>}}

  # SPINE — declared here, resolved in JSON
  rights_scope: licensed_reference | original          # A.1
  safety_scope: fictional_virtual_motion_only          # A.1 — required for action
  control_profile: {tier: strong|lite|mini, density: sparse|keyed|dense,
                    inference_allowed: [inbetweens, micro_sway]}     # weak-model knob
  authority_order: [locked_events, locked_contacts, locked_root, key_joints,
                    style_fields, generated_inbetweens, secondary_sim]   # MX §3.3

  # L1 INTENT (owner)
  intent: {objective: <goal>, tactic: <how>, obstacle: <resists>, subtext: <hidden>}

  # L2 ACTION GRAPH — action atoms, CPCS §19.4.3 shape
  actions:
    - id: <a1>
      verb: punch_like_strike | step_in | reach | dodge | fall | recover | <any>
      actor: <actor>
      target: <entity.region>
      safety_mode: staged_near_contact                 # default for screen action
      phases: {preparation: [t0,t1], execution: [t1,t2], near_contact: [t2,t3],
               follow_through: [t3,t4], recovery: [t4,t5]}
      support: {planted_effectors: [left_foot]}
      local_phase_order: [rear_foot_pivot, pelvis_rotation, torso_rotation,
                          shoulder, elbow, fist]       # proximal→distal — the power read
      minimum_separation_m: 0.025
      preconditions: [<state>]
      postconditions: [<state>]
      temporal_relations: ["a1 before a2"]

  # L3 PHASE policy (curves live in JSON)
  phase_policy: {wrap: reset, zero_anchor: a1.onset, authority: authored}

  # L6 contact POLICY (exact events live in JSON)
  contact_policy: {default_mode: staged_near_contact, no_penetration: hard,
                   camera_cheat_allowed: true}          # A.8

  # L7 dynamics INTENT
  physics_mode: none | kinematic | hybrid | dynamic     # A.9

  # L8 LABAN (words + phrasing — floats live in JSON)
  laban:
    - {actor: <a>, interval_s: [0,1.5], body: <initiation>,
       effort: {weight: strong, time: sudden, space: direct, flow: bound},
       shape: advancing, space: <kinesphere/pathway>, phrasing: impulsive_accent}  # A.10

  # L9 AFFECT arcs (AU curves live in JSON; triggers in XML)
  affect:
    - {actor: <a>, interval_s: [0,3], experienced: {v: 0.2, a: 0.5, c: 0.6},
       displayed: {v: 0.6, a: 0.8, c: 0.8}}            # A.11 — keep the two separate

  # L10 MANNERISM (owner)
  mannerism:
    <actor>: {profile_id: <reusable>, preferred_stance: orthodox, guard_profile: high_left,
              asymmetry: 0.15, gaze_pattern: <habit>, gesture_inventory: [<modules>],
              microvariation: {amplitude: 0.05, seed: 7},   # correlated, seeded — never white noise
              postural_tone: upright_open, breath_signature: <rhythm>}   # A.12

  # L11 SECONDARY art direction (solver params in JSON)
  secondary_art_direction: [{element: cloak, holds: [], pins: [], face_clearance: true,
                             continuity_policy: across_cuts}]            # A.13

  # L12 STYLE TRANSFORM + invariants (owner; resolved values in JSON)
  style_transform:
    source_profile: natural_human
    target_profile: anime_sakuga_action | feature | ugc | superhuman
    timing_transform: {execution_scale: 0.6, apex_hold: 1.25}
    spatial_transform: {arc_exaggeration: 1.18, silhouette_separation: 1.25, reach_extension: 1.15}
    dynamic_transform: {gravity_scale_by_phase: {aerial: 0.5}, impulse_scale: 2.2}
    deformation_transform: {smear: 0.8, rig_limit_override: false}
    graphic_transform: {key_pose_hold_frames: 2, impact_frame: 1}
    presentation_transform: {camera_emphasis: 1.25, shake_scale: 1.3}
    invariants: [action_order, support_contact_sequence, target_identity,
                 screen_direction, recovery_completion]                   # A.14

  # L13 presentation INTENT (exact paths in JSON; triggers in XML)
  presentation_intent: {framing: wide_two_shot, screen_direction_lock: a_left_b_right,
                        no_slow_mo: true, continuous: true}

  # DOMAIN OVERLAY — marketing (UGC ads; CPCS §19.4.6)
  marketing:
    hook: {deadline_s: 1.0, requirement: <recognizable>}
    product: {asset_id: <p>, minimum_visible_area_ratio: 0.08, hero_interval_s: [3.8,5.1]}
    claim: {text: <approved>, evidence_asset_id: <ref>}
    call_to_action: {minimum_hold_s: 1.2}
    variants: [{id: vertical_9x16, safe_zone: <profile>}]
    measurement: {experiment_id: <e>, primary_metric: <m>}   # hypothesis, never a guarantee

  # TRANSFER POLICY (recreation from reference; RDC §18)
  transfer_policy:
    retain: [beat_order, timing, camera_grammar, laban_quality]
    parameterize: {speaking_rate_scale: 0.95, gesture_amplitude_scale: 0.85}
    replace: [identity, voice, wardrobe, setting, product, brand]
    exclude: [private_data, unlicensed_marks]
    locks: [{path: <json.path>, value: <v>, tolerance: <t>}]

  # L14 acceptance THRESHOLDS (metrics computed in JSON)
  acceptance: {contact_time_error_ms: 50, contact_distance_m: 0.05, identity_score: 0.95,
               foot_slip_m: 0.02, action_order_exact: true, screen_direction_exact: true}

  # high-level HARD CONSTRAINTS (director-reviewable)
  constraints:
    - {id: no_slow_mo, expression: "camera.slow_motion == false", mode: hard}
    - {id: continuous, expression: "cuts == 0", mode: hard}
    - {id: identity_lock, expression: "identity_score >= 0.95", mode: hard}
```

---

## SKELETON 2 — JSON (the machine canonical truth)

Solver-generated / compiler-resolved exact numbers. Top-level keys follow the MX canonical schema.

```jsonc
{
  "schema_id": "cpcs-mx/1.1", "document_id": "<id>",
  "safety_scope": "...", "rights_scope": "...",

  // SPINE resolved
  "timebase": { "canonical": "frames", "fps": 24, "sample_rate_hz": 240,
                "source_clock": "source_pts",
                "retime_map": [ /* τ=w(t): performance-time vs presentation-time (CPCS §19.4.4) —
                                   speed ramps WITHOUT breaking causal order */ ] },
  "coordinate_systems": [ { "id":"world","space":"world","handedness":"right","up_axis":"y",
                            "forward_axis":"z","linear_unit":"m","angular_unit":"rad" },
                          { "id":"screen","space":"normalized_screen" } ],   // anime screen-space truth
  "assets": [ { "id":"<dense>", "uri":"asset://joints.npz", "sha256":"<hash>" } ],  // dense stays media
  "entities": [ { "entity_id":"actor_a", "character_id":"<c>", "performer_id":null, "rig_id":"<r>",
                  "identity": {"reference_image":"<ref>","identity_lock":0.95} } ],  // 3 ids ≠ collapsed
  "characters": [ { "character_id":"<c>", "morphology_profile": {"height_m":1.75,"reach_m":0.72,
                    "mass_kg":68,"dominant_hand":"right","stance":"orthodox"} } ],
  "rigs": [ { "rig_id":"<r>", "joint_set":[ "..." ], "joint_limit_profiles":"anatomical|rig_safe|virtual_stylized",
              "retarget_map":null, "collision_model":"capsules" } ],

  "shots": [ { "shot_id":"s1", "beats":[ {"beat_id":"b1","objective":"<goal>","interval_f":[0,36]} ] } ],

  // L2 resolved action graph
  "events": [ { "action_id":"a1","actor":"actor_a","action_type":"strike_like","target_ref":"actor_b.head",
                "frames":{"onset":12,"contact":24,"end":36}, "temporal_relations":["a1<a2"] } ],

  // L3 phase curves — GLOBAL + LOCAL per bone
  "phases": { "global": {"curve":[[0,0.0],[24,0.5],[36,1.0]], "wrap":"reset", "authority":"authored"},
              "local":  [ {"bone":"pelvis","curve":[...]},
                          {"bone":"r_arm","offset_from":"pelvis","lag_f":2} ] },

  // L4+L5 tracks — one authority per quantity; derivatives DERIVED with declared method
  "tracks": {
    "root": { "coord":"world", "authority":"locked",
              "translation":[{"f":0,"x":-1.2,"y":0,"z":0}], "orientation":[{"f":0,"yaw":90}],
              "velocity":"derived:savgol(w=5)", "support_polygon":[], "center_of_mass":[] },
    "joints": { "<joint>": { "representation":"rot6d|quaternion|keyframes|sampled|external_asset",
                             "interpolation":"cubic|slerp|linear|step|hold",
                             "authority":"locked|guided|preferred|free",
                             "rotation":[...], "position":[...],
                             "angular_velocity":"derived" } }
  },

  // L6 exact contacts
  "contacts": [ { "contact_id":"c1", "contact_type":"support|grasp|touch|staged_near_contact|collision|impact",
                  "site_a":"actor_a.r_fist","site_b":"actor_b.l_forearm","interval_f":[24,26],
                  "distance_curve":[...], "normal":[0,0,1], "min_distance_m":0.02,"tolerance_m":0.05,
                  "impulse":{"value":<v>,"evidence_class":"authored"},   // virtual, labeled
                  "reaction_event_ref":"a2", "camera_cheat_allowed":true, "no_penetration":"hard",
                  "friction_profile":null } ],

  // L7 dynamics numbers (evidence class MANDATORY for force/torque)
  "dynamics": { "mass_profile":{}, "gravity_profile":{"aerial":0.5}, "external_force":[],
                "joint_torque":[], "momentum":[], "energy_budget":null,
                "inverse_dynamics_report":null, "physics_mode":"kinematic" },

  // L8 Laban floats + computational proxies
  "laban_controls": [ { "actor":"actor_a","interval_f":[0,36],
                        "effort":{"weight":0.8,"time":0.9,"space":0.9,"flow":0.2},
                        "shape":"advancing", "proxy_profile":{"time_from":"accel","space_from":"path_directness"} } ],

  // L9 facial AU splines (triggers live in XML)
  "facial_events": [ { "actor":"actor_a","action_unit":"AU04","side":"bilateral",
                       "curve":[[2.50,0.0],[2.74,0.28],[3.05,0.28],[3.52,0.0]],   // onset/apex/offset knots
                       "tolerance":{"intensity_mae":0.08,"apex_time_s":0.06} } ],
  "breath_tracks": [ { "actor":"actor_a","phase":[...],"amplitude":[...] } ],

  // L10 mannerism profile refs (authored in YAML)
  "mannerism_profiles": [ { "profile_id":"<m>", "resolved": true } ],

  // L11 secondary solver params
  "secondary_motion": [ { "system_type":"cloth","drivers":["root","torso"],"solver":"sim|keyframe",
                          "material_parameters":{"mass":..., "damping":..., "stiffness":...},
                          "collision_refs":["capsules"], "cache_asset_ref":"asset://cloth.abc" } ],

  // L12 resolved style transform values
  "style_transforms": [ { "resolved_from":"style://anime/...", "dimensions":{...}, "invariants":[...] } ],

  // L13 camera 6DoF + lens + edit (exact); triggers in XML
  "camera": { "coord":"world", "keys":[{"f":0,"pos":[0,1.5,-3.4],"yaw":0,"pitch":-4,
              "focal_mm":32,"focus_m":3.2,"framing":"wide"}],
              "shake":[{"trigger_f":24,"amp_px":6,"freq_hz":18,"decay_f":8}] },
  "edit_events": [ {"type":"impact_frame","f":24,"presentation_only":true} ],

  // L14 verification (owner)
  "verification_plan": { "metric_definition_ref":"metrics@1.2",
    "metrics": { "contact_time_error_ms":{"target":0,"tol":50}, "contact_distance_m":{"target":0,"tol":0.05},
                 "identity_score":{"target":1.0,"tol":0.05}, "foot_slip_m":{"target":0,"tol":0.02},
                 "silhouette_readable":{"target":true}, "screen_direction_match":{"target":true} },
    "acceptance_gate":{"policy":"all_hard_pass"},
    "candidate_id":null, "comparison_report":null },       // filled per generated candidate
  "capability_report": { "native":[], "approximated":[], "unsupported":[] },  // adapter contract (RDC §33)
  "constraints": [ /* resolved hard/soft/PERCEPTUAL (silhouette, target-visible-at-contact) */ ],
  "provenance": { "operations":[ /* ordered, parameterized, hashed */ ],
                  "per_track_evidence_class": { "/tracks/joints":"detected", "/dynamics":"authored" },
                  "build_manifest":{"tools":{},"models":{},"seeds":{}}, "loss_report":[] },
  "extensions": {}
}
```

---

## SKELETON 3 — XML (the ordered script & trigger envelope)

Ordered mixed content + namespaced department triggers. References the JSON by hash — never
duplicates numbers. Canonical-JSON has priority over the language model.

```xml
<cpcs:directorPackage xmlns:cpcs="urn:cpcs:core:1.1" xmlns:act="urn:cpcs:action:1.1"
    xmlns:perf="urn:cpcs:performance:1.1" xmlns:cam="urn:cpcs:camera:1.1"
    xmlns:vfx="urn:cpcs:vfx:1.1" xmlns:audio="urn:cpcs:audio:1.1" xmlns:mkt="urn:cpcs:marketing:1.1">

  <cpcs:score href="asset://canonical/score.json" sha256="<hash>"/>       <!-- single source of numbers -->
  <cpcs:authority><cpcs:canonical-json priority="higher-than-language-model"/>
                  <cpcs:locked-values source="../authoring/locks.yaml"/></cpcs:authority>

  <cpcs:objective>Materially new video preserving authorized timing, action relationships,
    camera grammar, performance dynamics, and communication structure.</cpcs:objective>

  <cpcs:script>                                             <!-- L1/L2: ORDERED narrative — XML superpower -->
    <act:beat id="b01" start="0.0s" end="1.5s">
      <act:description>Fighter A dashes in with a right straight; B parries with the left
        forearm and slides back.</act:description>          <!-- mixed content: prose + tags -->
      <act:event type="impact" time="1.0s" mode="hard">     <!-- L6 trigger mark -->
        <act:participant actor="fighter_a" body_part="right_fist"/>
        <act:participant actor="fighter_b" body_part="left_forearm"/>
      </act:event>
      <perf:facs actor="fighter_a" au="AU4+AU7" intensity="D" time="0.9s"/>   <!-- L9 triggers -->
      <perf:gaze actor="fighter_b" target="fighter_a" time="0.2s"/>
      <perf:blink actor="fighter_b" time="1.2s"/>
      <perf:breath actor="fighter_a" type="exhale_on_strike" time="0.95s"/>
      <perf:vocal_effort actor="fighter_a" type="kiai" time="1.0s"/>          <!-- A.11 -->
      <vfx:impact_flash time="1.0s" duration_frames="1" attach="contact:c1"/> <!-- L12 triggers -->
      <vfx:speed_lines start="0.8s" end="1.0s" attach="actor:fighter_a"/>
      <audio:sfx type="punch_impact" time="1.042s" sync_tolerance_frames="2"
                 freq_hz="60-180" db_boost="6"/>                             <!-- L13 audio -->
      <cam:event type="whip_pan" time="0.9s" deg_per_s="140"/>               <!-- event-driven camera -->
      <cpcs:edit type="impact_frame" time="1.0s" presentation_only="true"/>
    </act:beat>
    <act:beat id="b02" start="1.5s" end="3.0s"> <!-- ... ordered beats continue ... --> </act:beat>
  </cpcs:script>

  <mkt:direction>Preserve hook, proof, product visibility, and CTA relationships.</mkt:direction>
  <cpcs:exclusions><cpcs:item>source performer identity</cpcs:item>
    <cpcs:item>source voice</cpcs:item><cpcs:item>unlicensed logos</cpcs:item></cpcs:exclusions>
</cpcs:directorPackage>
```

---

## COVERAGE AUDIT — second pass against all three papers

Every concept family checked against the three skeletons. ✔ = carried; location named.

| Concept (paper §) | YAML | JSON | XML |
|---|---|---|---|
| Rights + safety scope (MX A.1) | ✔ scope | ✔ mirrored | ✔ exclusions |
| Provenance ops / build manifest / loss report (A.1, A.16) | — | ✔ provenance | — |
| Timebase + sample_rate + source_clock (A.2) | — | ✔ timebase | — |
| **Two time bases τ=w(t) / retime** (CPCS §19.4.4, A.2) | ✔ no_slow_mo intent | ✔ retime_map | ✔ edit events |
| Coordinate systems incl. screen-space (A.3, RDC §24.5) | — | ✔ coordinate_systems | — |
| Entity ≠ character ≠ performer ≠ rig (A.4) | — | ✔ entities/characters/rigs | ✔ actor refs |
| Morphology / joint limits / retarget / collision (A.4) | — | ✔ rigs | — |
| Identity anchor + lock (RDC §12) | — | ✔ entities.identity | — |
| Shots/beats/objective/tactic (A.5) | ✔ intent | ✔ shots | ✔ ordered script |
| Action atoms + pre/postconditions + local_phase_order + min separation (§19.4.3) | ✔ actions | ✔ events | ✔ event marks |
| Global + local phase, wrap/anchor/authority (A.6) | ✔ policy | ✔ phases | — |
| Root/joints/rotations/interpolation/authority (A.7) | — | ✔ tracks | — |
| Derived derivatives w/ declared method (A.7, §3.3) | — | ✔ "derived:savgol" | — |
| Contacts full (types, distance_curve, normal, friction, impulse, reaction, camera_cheat, no_penetration) (A.8) | ✔ policy | ✔ contacts | ✔ triggers |
| Dynamics (mass/gravity/torque/COM/momentum/energy/physics_mode; evidence mandatory) (A.9) | ✔ physics_mode | ✔ dynamics | — |
| Laban Body/Effort/Shape/Space/phrasing + proxies (A.10) | ✔ words | ✔ floats+proxies | — |
| FACS AU curves + tolerance; displayed vs experienced affect; gaze/saccade/blink/head/breath/vocal effort (A.11) | ✔ affect arcs | ✔ facial_events, breath | ✔ perf: triggers |
| Mannerism full profile (A.12) | ✔ owner | ✔ refs | — |
| Secondary motion full (drivers/solver/material/art_direction/cache/continuity) (A.13) | ✔ art direction | ✔ solver params | — |
| Style transform 6 sub-transforms + invariants + macro expansion (A.14, MX §28) | ✔ owner | ✔ resolved | ✔ vfx triggers |
| Superhuman phase physics (MX §19/§28.7) | ✔ dynamic_transform | ✔ gravity_profile | — |
| Camera track (pose/lens/framing/focus) + edit events (A.15) | ✔ intent | ✔ camera/edit | ✔ cam:/edit triggers |
| VFX events attached to contacts/actors (§19.4.5) | — | — | ✔ vfx: |
| Audio events w/ Hz/dB/sync tolerance (A.15, owner spec) | — | — | ✔ audio: |
| Marketing contract (hook/product/claim/CTA/variants/measurement) (§19.4.6, A.15) | ✔ overlay | — | ✔ mkt: |
| Variant matrix (A.15) | ✔ marketing.variants | — | — |
| Transfer policy 4 verbs + locks w/ tolerance (RDC §18) | ✔ transfer_policy | — | ✔ exclusions |
| Hard/soft/PERCEPTUAL constraints (MX §11) | ✔ constraints | ✔ resolved | — |
| Verification plan/gate/metrics/candidate/comparison (A.16) | ✔ acceptance | ✔ verification_plan | — |
| Capability report / adapter contract (A.16, RDC §33) | — | ✔ capability_report | — |
| Evidence classes per track (RDC §4.3) | — | ✔ provenance | — |
| Authority order + one-authority-per-quantity (MX §3.3) | ✔ authority_order | ✔ per-track authority | ✔ authority element |
| Control-vs-presentation split (MX §3.4) | ✔ (intent vs presentation) | ✔ presentation_only flags | ✔ (triggers ≠ numbers) |
| Control-density tiers for weak models (lab) | ✔ control_profile | ✔ density honored | — |
| Dense assets stay media, hash-referenced (RDC §6.5) | ✔ imports | ✔ assets | ✔ score href |
| Correlated seeded microvariation (MX §16) | ✔ mannerism.microvariation | ✔ seeds in build_manifest | — |

**Audit result: every field family in MX Appendix A.1–A.16, every CPCS §19.4 contract, and every RDC
format/precedence concept has a named home. Nothing overlooked.** Cards: `c_layer_stack`,
`c_format_control_map`, `c_two_document_architecture`.
