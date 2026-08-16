# WP-4 — KA-2 evaluation fixtures (DEV + precommitted HOLDOUT)

## Goal

Two evaluation tiers. The DEV set is the implementation-tunable surface.
The HOLDOUT set is **precommitted**: answer key is hashed before
implementation, not opened during implementation, scored once after
implementation, not used to tune.

## File layout

- `lab/application/KA2_EVAL_DEV_v0.1.json` — visible dev set (8–12 intents,
  expected regions, expected exclusions, prerequisite expectations,
  representation tendencies).
- `lab/application/KA2_EVAL_HOLDOUT_INTENTS_v0.1.json` — holdout intent
  texts + IDs (NO answer labels).
- `lab/application/KA2_EVAL_HOLDOUT_COMMITMENT_v0.1.json` — SHA-256
  commitment to the answer key + schema/version.
- `lab/application/KA2_EVAL_HOLDOUT_ANSWER_KEY_v0.1.json` — holdout answer
  key. **Not opened by the implementation agent.**
- `lab/application/KA2_EVAL_HOLDOUT_RESULT_v0.1.json` — computed one-shot
  result, written only after the answer key is revealed and the
  commitment is verified.

## Dev set intents (initial draft)

1. `a_fighter_performs_a_hip_toss` — combat: support+contact+projection+recovery.
2. `a_fighter_falls_into_water_and_recovers` — environment response +
   recovery.
3. `a_woman_applies_facial_serum_and_likes_it` — UGC: facial behavior +
   hand-object + product identity (emergence: FACS not named in intent).
4. `a_serum_bottle_rotates_on_a_pedestal_no_person` — product macro:
   FACS should be ARCHIVE (exclusion test).
5. `a_person_unboxes_a_luxury_watch` — ecommerce: identity continuity +
   contact + camera readability.
6. `a_creator_records_a_casual_dialogue_clip` — dialogue: timing + gaze +
   camera (no choreography).
7. `a_chef_slices_a_tomato` — cooking: contact + safety + deformation.
8. `a_car_drives_through_a_puddle` — vehicle: environment + material
   response.
9. `a_closeup_face_shows_disappointment` — pure facial performance.
10. `a_drone_camera_orbits_a_cliff_no_performer` — environment/camera only,
    no actor (exclusion test).

## Dev set expectations (per intent)

Each entry includes:

- `intent_id`
- `intent_text`
- `expected_recruited_regions` (list of region facet signatures)
- `expected_archived_regions` (list of facet signatures expected to
  resolve to ARCHIVE)
- `expected_coverage_gaps` (list of typed need-IDs expected to be
  surfaced when evidence is missing)
- `expected_planning_guidance_nonempty` (bool)
- `expected_non_executable_used` (bool)
- `expected_new_prerequisites` (list of requirement IDs the run is
  expected to surface)
- `expected_representation_tendency` (qualitative: e.g.
  `more_controls_than_ka1` or `more_planning`)

The expected signatures are facet-based (e.g.
`{trigger_ids: ["TRIG-FACE"], objective_ids: [], failure_family_ids: []}`)
so the test compares structured keys, not free text. This is the
"deterministic region identity" we use in WP-1.

## Holdout set design (initial draft)

- `holdout_01_dance_choreography` — choreography: timing + body
  mechanics + camera.
- `holdout_02_hands_only_assembly` — product assembly hands-only.
- `holdout_03_two_actor_dialogue_closeup` — dialogue intimacy + gaze +
  micro-reaction.
- `holdout_04_dramatic_rain_landing` — environment response under
  performer action.
- `holdout_05_product_destroyed` — product integrity breach (negative).
- `holdout_06_face_only_with_voiceover` — voiceover over face.

The holdout answer key is a JSON list of objects matching the dev-set
schema. The commitment is `sha256(canonical_json(answer_key))`.

## Test strategy

- `test_ka2_dev_evaluation.py` loads the DEV set, runs KA-2 for each
  intent, asserts:
  - recruited regions match the expected facet signatures,
  - archived regions are present and match,
  - coverage gaps are present and named,
  - planning_guidance and non_executable_knowledge_used are populated
    where expected,
  - new prerequisites are surfaced where expected,
  - per-intent constellation_hash is stable across two runs.
- `test_ka2_holdout_commitment.py` checks that the commitment file
  exists, contains a valid SHA-256, and references the right key file
  path. It does NOT read the answer key.
- The one-shot holdout run is in `ka2_acceptance.py` (WP-5).

## Open: implementation MUST NOT tune against holdout

The holdout runs after WP-5 in `ka2_acceptance.py` only. If the result
fails any gate, the failure is recorded honestly. The user decides
whether to ship, retune with a NEW holdout, or hold.
