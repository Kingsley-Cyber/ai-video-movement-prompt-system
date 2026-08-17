# SI-1.1 — Manipulator / Actor Resource Constraint Closure Report

Stage result: **ACCEPTED** — the measured generation failure is
closed at the planning layer, hermetically verified.

## The measured failure (before)

The UGC water-bottle render spontaneously opened the bottle closure with
no physically accounted manipulation. The planning package never
reasoned over: persistent limb occupancy (one hand holding the phone),
interaction preconditions (drinkable/open state), object closure
mechanism, or required manipulation roles.

## What shipped

- `cpcs_actor_resources.py` — `ResourceConstraintPacket`:
  - per-actor manipulator resources (left_hand / right_hand, declared
    bilateral anatomy), states AVAILABLE/OCCUPIED/GRASPING/SUPPORTING/
    CONTACTING/TRANSITIONING
  - capture-device occupancy: `performer_operated_phone` /
    "filmed it on her phone" seeds ONE hand OCCUPIED (which-hand marked
    UNRESOLVED, never guessed); occupancy persists until an explicit
    release
  - declared per-predicate resource requirements (GRASP /
    STABILIZING_MANIPULATOR / SUPPORT / CONTACT / COUNTERFORCE);
    bimanual requirements for OPEN/ASSEMBLE/UNBOX/SLICE
  - precondition dispositions: SATISFIED_ALREADY /
    SUPPORTED_ONE_HAND_REALIZATION / REQUIRES_RESOURCE_REASSIGNMENT /
    REQUIRES_SUPPORT_SURFACE / REQUIRES_ADDITIONAL_BEAT / UNRESOLVED
  - explicit RESOURCE_CONFLICT records (never silently satisfied)
  - grip persistence + release semantics (RELEASE/THROW free the hand)
  - no-beats + no-capture-device -> NO human resource graph (drone)
- NB-1 refinement (same session, needed by SI-1.1): deterministic
  pronoun resolution ("it" -> last named object; DRINK/APPLY act on the
  held container; "shows it to the camera" binds the bottle, not the
  camera); single-declared-actor pronoun resolution.
- Wiring: `actor_resource_constraints` sidecar in the guided package.

## Acceptance (SI11_RESOURCE_DIAGNOSTICS_v0.1.json)

| Case | Phone hold | Preconditions | Conflicts |
|---|---|---|---|
| UGC water bottle | persistent, one hand | DRINK = UNRESOLVED (closure unspecified) | **0** |
| Cooking (slice + grab plate) | — | — | 1 (third-object conflict, as designed) |
| Bimanual assembly | — | — | 0 |
| Fight grip chain (catch→swing→release) | — | — | 0 (grip persists, then releases) |
| Drone | — | — | 0 (no human resource graph) |

Failure-prevention checks for the exact failure case:
- phone hand stays OCCUPIED across all beats: TRUE
- bottle grip never lands on the phone hand: TRUE
- DRINK precondition disposition: UNRESOLVED (closure mechanism
  unspecified; no twist/pop/straw/unscrew invented)
- resource conflicts: 0 (grip chain is physically accounted)

## Gap taxonomy

- MANIPULATOR_RESOURCE_GAP / RESOURCE_CONFLICT: emitted per conflict
  record (cooking third-object case).
- AFFORDANCE_GAP: closure mechanism unknown -> UNRESOLVED, never
  manufactured.

## Frozen boundaries

KA-2.3/KA-2.4/SI-1 policies untouched; retrieval/Control A/provider
untouched; no new research; D4 preserved (no prose-inferred anatomy;
declared vocabulary only).
