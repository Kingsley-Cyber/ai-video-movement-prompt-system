# RUNBOOK — cross-style switching (cook the same action into any style)

**Trigger phrases:** "make it anime / cartoon / feature-animation / superhuman", "restyle this",
"same fight but stylized", "change the style but keep the choreography".

**The idea (MX §28):** a good motion score lets you change *style* without rebuilding the *action*.
You separate four layers, keep the action fixed, and apply a **typed style transform** with declared
**invariants**. Style is a recipe of named dimensions — not one "make it anime" scalar — so you can
taste each ingredient and know what it does.

Concept cards: `c_content_perf_style_presentation`, `c_style_transform_vector`,
`c_protected_invariants`, `c_style_ablation`, `c_superhuman_transform`, `c_profile_system`.
Profiles: `lab/profiles/style/`, `lab/profiles/movement/`.

---

## Step 1 — Separate the four layers (don't skip this)

```
action content     what physically happens: approach -> plant -> strike -> recoil -> recover
performance        how it's done: hesitant | committed, bound | free, protective posture
style transform    the target look: natural | UGC | feature-animation | anime/sakuga | superhuman
presentation       how it's shot: handheld close | locked wide | impact montage
```
Only **style transform** and **presentation** change in a restyle. Content and performance are held.
If your source is a v005-style kinematic JSON, that IS the action content — leave it intact.

## Step 2 — Declare the invariants (what must survive)

Pick from `c_protected_invariants` — the non-negotiables the transform may not break:
`action_order, support_contact_sequence, participant/target_identity, screen_direction,
safety_class, critical gaze/product visibility, start/end state, recovery_completion`.
These become hard checks in Step 5. Everything not listed is fair game to stylize.

## Step 3 — Pick a style profile as the base

Inherit one `profile://style/*` (e.g. `lab/profiles/style/anime_sakuga_action_v3.yaml`) as the
starting recipe, then override dimensions. A profile is a prepared base, not a straitjacket.

## Step 4 — Author the typed style-transform vector

Named dimensions (each a separate ingredient — MX §28.2). Anime example:

```json
{"style_transform":{
  "source_profile":"natural_human","target_profile":"anime_sakuga_action",
  "dimensions":{"timing_compression":1.35,"anticipation_expansion":1.20,"key_pose_hold_frames":2,
    "arc_exaggeration":1.18,"silhouette_separation":1.25,"secondary_overlap":1.15,
    "microvariation":0.45,"graphic_smear":0.80,"impact_frame":1.0,"camera_emphasis":1.25},
  "invariants":["action_order","support_contact_sequence","target_identity","screen_direction","recovery_completion"]}}
```

**Superhuman** adds phase-typed virtual physics (`c_superhuman_transform`) — state WHERE energy enters
and HOW it's shown as separate fields, never merged:

```yaml
virtual_physics: {gravity_scale_by_phase: {launch: 1.0, aerial_hold: 0.35, descent: 0.75},
                  propulsion_impulse_scale: 2.2, drag_scale: 0.4, landing_response_scale: 1.5}
stylized_deformation: {reach_extension_scale: 1.15, perspective_extension_scale: 1.25, rig_joint_limit_override: false}
presentation: {anticipation_time_scale: 1.25, execution_time_scale: 0.55, recovery_time_scale: 1.10, impact_hold_frames: 1}
```

Then compile the transformed score to the target model via the execution carrier that fits the
fidelity need (`c_execution_carrier`): anime often compiles to **key drawings + exposure timing**, not
a continuous anatomical trajectory (`c_screen_space_truth`).

## Step 5 — Ablate to learn what each ingredient does (this is the "truly understand" part)

Generate the SAME action changing ONE dimension at a time (`c_style_ablation` = the lab's one-lever
A/B applied to style):

```
base action
+ anticipation_expansion only
+ key_pose_hold_frames only
+ arc_exaggeration only
+ silhouette_separation only
+ graphic_smear only
+ full profile
```

Log each as a variant + run in the lab. This tells you which dimensions actually produce the perceived
style and which only add noise — so the profile becomes knowledge, not a magic number. Verify the
Step-2 invariants held on every output (a two-frame anime hold may change timing but must preserve the
contact event and the beat).

## Step 6 — Promote

Dimensions that reliably produce the look on your target model graduate from the profile's example
values to evidence-backed defaults (update the profile + a `p###` pattern). The style profile is a
living recipe refined by ablation, exactly like every other lab ingredient.

---

## Why this beats "make it anime" in the prompt

A single "anime style" instruction is one opaque scalar — you can't tell whether the smear, the holds,
or the arc exaggeration is doing the work, and it silently mangles the choreography. The typed vector +
invariants + ablation give you **separable, checkable, teachable** control: the same reason numeric
kinematic truth (v005) beat prose for motion, applied to style.
