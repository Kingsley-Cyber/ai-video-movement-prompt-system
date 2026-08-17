# CPCS UNIFIED DIRECTING PACKAGE — v0.1 (design spec)

STATUS: design input for CS-1 carrier serialization. NOT wired into the
pipeline; Control A and the provider boundary remain frozen. This
unifies the strong concepts from the water-bottle UGC package and the
water-duel-anime synchronized prompt into ONE envelope that supports
multi-character scenes.

## Unified envelope

```
sync:            clock + cross-section hash bindings (desync = re-resolve)
  1/3 YAML       semantics: scene, actor registry, narrative beats,
                 specialists, acceptance, negative_space
  2/3 JSON       canonical truth: numbers, controls, verification,
                 hard constraints, surface, kinematic tier (optional)
  3/3 XML        order + triggers: phases, move sequences, camera track,
                 fx track, pointers into JSON truth
```

- JSON owns every number. YAML owns semantics. XML owns order+triggers.
- Every section carries a content hash in `sync.bindings`; editing any
  section desyncs the package. Rule: re-resolve before generation.
- `sync.clock` (frame_rate / duration_s / frame_count) is shared by all
  three sections — one time authority, no per-format restatement.

## The strong concepts this unifies

| Concept | From | Where it lives in the package |
|---|---|---|
| Sync envelope + hash bindings | water-duel | `sync` |
| Actor/entity identity registry | water-duel | YAML `actors` (id, look, accent, identity_note) — makes every scene multi-character-ready; all beats/tracks keyed by actor id |
| Narrative beats with knowledge bindings | UGC water bottle | YAML `beats` (id, order, action, knowledge, origin USER_EXPLICIT/DERIVED) — NB-1 semantics |
| Proposed vs solved authority | water-duel | JSON `authority` per phase/beat: `solved` ONLY where kinematic tracks exist; otherwise `proposed` — CS-1 must never serialize proposed motion as truth |
| Kinematic motion-truth tier (optional) | water-duel | JSON `tracks` (root_motion, joint_tracks, contacts with tolerances, camera positions/orientations, fx events) — absent tier = honest absence, not a guess |
| Move-level choreography vocabulary | water-duel | XML `phases > moves` (strike.*, slip.*, trap.*, throw.*, catch.*, sweep.*, block.*) — NB-2 taxonomy |
| Acceptance criteria + negative_space | water-duel | YAML `acceptance`, `negative_space` (hard refusals mirrored into NL) |
| Hard-constraint expressions | water-duel | JSON `hard_constraints` (machine-checkable against tracks when present) |
| Surface / world response | water-duel | JSON `surface` (type, support, reaction) — WP-6 world_response semantics |
| Laban authored efforts | water-duel | JSON `tracks.lab_control` — MUST stay epistemically labeled `authored` (TC-2: effort != force) |
| Capture realism + protected invariants | UGC water bottle | YAML `capture`, `protected_invariants` |
| Repair/lineage provenance | both | `sync.lineage` (build_id, score_id, commit, repair lineage) |

## Multi-character rules

1. Every beat, contact, track, and camera event references `actor_id`
   (or `scene`) — never prose names.
2. Two fighters, one presenter, or N performers: the registry is flat;
   specialization lives in beats, not in a new per-character schema.
3. Identity persistence is a protected invariant per actor
   (`actor_id.identity_score >= threshold` where measured).

## Layering rules (frozen boundaries)

- The kinematic tier is OPTIONAL. Its absence means the package is
  temporal/structural only (TD-1 seconds), and all motion is
  PROPOSED. Absence is honest; invention is forbidden.
- Narrative beats are planning representations, never canonical
  controls (D4).
- No provider-specific frame claims unless a dated capability contract
  supports them.

## Repo status of each concept

- sync envelope: NOT IMPLEMENTED (CS-1 design input)
- actor registry: NOT IMPLEMENTED (NB-2 design input)
- beats + knowledge bindings: NB-1 shipped (origin, USER_SEQUENCE/
  STATE_TRANSITION edges)
- proposed/solved authority: NOT IMPLEMENTED (gates CS-1)
- kinematic tracks: NOT IMPLEMENTED (REPRESENTATION_GAP:
  KINEMATIC_TRACKS; TD-1 currently allocates seconds only)
- move vocabulary: PARTIAL (NB-1 has 27 coarse predicates; move-class
  taxonomy is NB-2)
- acceptance/negative_space: NOT IMPLEMENTED (verification requirements
  exist; director-authored acceptance contract does not)
- hard-constraint expressions: PARTIAL (score constraints.hard exists;
  track-checkable expressions need the kinematic tier)
- surface/world_response: SCHEMA EXISTS (WP-6); real-runtime population
  remains a recorded gap
- Laban authored: doctrine exists (performance.effort epistemic note)
- capture realism / protected invariants: shipped (Control A controls)
- lineage: shipped (build/score/repair lineage everywhere)
