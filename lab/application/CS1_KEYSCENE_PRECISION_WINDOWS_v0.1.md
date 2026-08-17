# CS-1 DESIGN — Key-Scene Precision Windows (v0.1)

STATUS: design input for CS-1. Owner-directed refinement of the
kinematic tier after the water-duel v2 render: the catch/swing chain
read well, but the body-water landing was bad.

## The diagnosed failure

Precision asymmetry: the body carried hard kinematic numbers (root
motion, joint tracks, timed contacts) while the environment side was
one prose line. At the landing, a precisely-timed body met an
improvised water surface. The model invented the gap — wrong splash,
wrong deformation, wrong drag — and the scene read as broken exactly at
its most important moment.

Rule derived: **kinematic precision covers contact PAIRS, never actors
alone.** A key scene where a body meets a surface is a two-sided
contract.

## Concept: Kinematic Precision Windows (KPW)

1. **Windows, not full tracks.** Author numeric tracks ONLY for the
   2-3 key scenes that carry the fight (catch → hammer swing → release
   skid). Between windows, authority is explicitly generative
   (style-guided only). Over-constraining the whole clip produces
   stiff, model-fighting output.

2. **Contact-pair contracts.** Every precision contact carries a paired
   ENVIRONMENT RESPONSE with the same tolerance discipline as body
   contact:

   ```json
   {
     "contact": {"id": "c03.release_skid", "start_s": 3.2, "end_s": 4.0,
                 "type": "slide_deceleration", "tolerance_m": 0.08},
     "environment_response": {
       "surface": "water",
       "trigger": "c03.release_skid",          // response is CAUSED, never simultaneous with cause
       "deformation": {"type": "displacement_trough", "depth_scale_bounded": true},
       "spray": {"origin": "contact_site_only", "scale": "bounded", "direction": "along_velocity"},
       "drag": {"curve": "sqrt_deceleration", "residual_motion": "visible_dissipation"},
       "wake": {"type": "skid_line", "persists": "short"}
     },
     "acceptance": [
       "surface deforms only after contact onset",
       "spray originates at the contact site",
       "wake line follows the skid path",
       "body never sinks below tolerance",
       "deceleration matches drag, not a wall"
     ]
   }
   ```

3. **Authority handoffs.** Explicit markers where kinematic authority
   ends and generative authority begins (e.g., after the skid stops,
   recovery is style-guided only). Prevents precision-bleed into
   regions the model renders better free.

4. **Repair loops target the failed pair.** The repair lineage records
   WHICH side failed (body vs environment). v2 repaired body-side
   (joint limits, momentum conservation); the water stayed bad because
   no environment contract existed to repair. v3 repairs the
   environment-response contract, not the body tracks.

## What this changes in the unified package

- The kinematic tier gains `environment_response` contracts paired to
  contacts, with `caused_by` triggers (NB-1 causal discipline: response
  follows cause).
- `acceptance` checks become pair-scoped: each precision window lists
  its own checkable outcomes.
- Windows are listed in `authority` with three states:
  `kinematic` (paired contracts present), `proposed` (no tracks), and
  `generative` (deliberate handoff).

## Layering rules (unchanged frozen doctrine)

- Absent environment contract = honest gap, recorded as
  REPRESENTATION_GAP: ENVIRONMENT_RESPONSE — never backfilled with
  prose guesses.
- Environment response is a state transition caused by the contact
  (never chronology-only) — existing NB-1 STATE_TRANSITION semantics.
- No invented numeric water physics: every bound (depth scale, drag
  curve) is declared bounded-qualitative, not a fake measurement.

## Repo status

- WP-6 world_response schema: EXISTS (water/surface deformation, drag)
- real-runtime environment-response population: GAP (recorded)
- kinematic tier / contact-pair contracts / authority handoffs:
  NOT IMPLEMENTED (CS-1 design inputs)
- acceptance pair-scoping: NOT IMPLEMENTED (CS-1 design input)
