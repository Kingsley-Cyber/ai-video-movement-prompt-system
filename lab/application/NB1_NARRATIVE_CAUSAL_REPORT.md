# NB-1 — Narrative Beat + Causal Spine Projection Report

Stage result: **ACCEPTED** (all critical criteria pass; unresolved items
are recorded honestly, never guessed).

## What shipped

- `cpcs_narrative_beats.py` — `NarrativeBeatGraph` / `NarrativeBeat`:
  - Conservative declared action vocabulary (clause-level extraction;
    phrasal verbs like "picks it up"; "showing off" excluded as
    creator framing, not a reveal; multiple actions per clause).
  - Beat identity is structured (predicate + actor + object + source
    span + position hash); display names are diagnostic labels only.
  - Origins: USER_EXPLICIT for user clauses; DERIVED_PREREQUISITE for
    declared consequence beats (release → WATER_IMPACT).
  - Edges: USER_SEQUENCE from clause order (temporal precedence,
    NEVER causation); STATE_TRANSITION from the declared consequence
    vocabulary. CAUSAL_REQUIRED is never derived from order alone.
  - SI-1 unit binding by structured failure-family overlap; one unit →
    one beat; zero-overlap units are reported SI1_UNIT_UNBOUND, never
    guessed. D4: beats are planning representations, never canonical
    controls.
  - `annotate_temporal_plan` adds narrative_beat_id/display per TD-1
    schedule entry (additive; TD-1 policy math and hash untouched).
- Guided flow wiring: `narrative_beat_graph` +
  beat-annotated `temporal_directing_plan` in the deliberation package.

## Real-runtime acceptance (NB1_REAL_RUNTIME_DIAGNOSTICS_v0.1.json)

| Case | User beats | Derived | Edges | Units bound | TD-1 refs |
|---|---|---|---|---|---|
| UGC water bottle 15s | PICK_UP, DRINK, APPRAISAL_DIALOGUE, PRODUCT_REVEAL | — | 3 USER_SEQUENCE | 8/13 | 8 |
| FIGHT 6s | CATCH, SWING, RELEASE, PRESSURE, RECOVERY | WATER_IMPACT | 4 SEQ + 1 STATE_TRANSITION | 11/18 | 11 |
| MANIPULATION 6s | ASSEMBLE | — | — | 10/17 | 10 |
| DIALOGUE 6s | DIALOGUE_EXCHANGE | — | — | 8/16 | 8 |
| DRONE 6s | none (negative passes) | — | — | 0/19 | 0 |

- A/B/C: ordinary language yields provenance-backed beats; water bottle
  and fight distinguish their major action chains.
- D/E: SI-1 units bind to beats; recruited expertise binds through
  those units to the proper narrative beats (beat_placements recorded
  per case).
- F: TD-1 intervals now attributable to narrative beats.
- G: real-runtime ordering/state edges are no longer zero for
  multi-event requests (3-5 edges).
- H: temporal precedence is never promoted to causation
  (CAUSAL_REQUIRED absent; only USER_SEQUENCE + STATE_TRANSITION).
- I: derived mechanics (WATER_IMPACT) remain distinguishable from
  explicit user beats.
- J: drone manufactures no performer/action beats.
- K/L: no prose-to-control coercion; frozen KA/SI/TD policies
  untouched (TD-1 annotation is additive; plan_hash unchanged).

## Honest gaps (recorded)

1. Actor/object extraction is token-vocabulary based; clauses without
   recognized tokens record actor/object as unresolved.
2. Binding granularity inherits the pack-level document-mixing
   residual (some units bind by family overlap rather than exact
   record identity).
3. CAUSAL_REQUIRED edges remain unused: nothing in the frozen runtime
   yet supplies evidence-grade causal relations beyond declared state
   consequences.
4. 5/13 water-bottle units remain unbound (no failure-family overlap
   with any extracted beat) — reported, not guessed.

## Next (per closure path)

CS-1 reviewed directing carrier serialization (owner decision), then
implementation freeze + independent holdout in a separate session.
