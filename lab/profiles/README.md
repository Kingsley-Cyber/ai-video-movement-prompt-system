# Profiles — higher-order modular ingredients

Reusable, **versioned, composable** defaults adopted from the CPCS-MX package
(`research/CPCS_MX_Hierarchical_Motion_Grammar_Research_Package_v1.0/profiles/`). Where `concepts.jsonl`
cards are single ingredients, a **profile is a prepared base** — a named bundle of defaults +
`hard_constraints` + recommended verification metrics you inherit and then override.

## The idea (paper §26, §28)

```
natural-language direction + profile:// references + measured assets
        → authoring YAML  → deterministic resolve/merge/validate → canonical score
```

An authoring doc pulls one profile per axis (movement / capture / camera / performance /
screen_action / style), then overrides locally. Precedence: **local override > more-specific scope >
profile default**, and `hard_constraints` never silently drop. This is the compiler-backed version of
the lab's compose mode (`profile://` = the resolvable, inheritable form of a `blk_*`).

## What's here

| Axis | Profile | Gives |
|---|---|---|
| movement | `natural_human_v3` | micro-sway, bounded balance corrections, gaze-leads-navigation, breath coupling, rig-safe limits |
| movement | `staged_action_base_v2` | the 5-phase model (prep → execution → contact/apex → follow-through → recovery), safety-scoped |
| capture | `authentic_ugc_v2` | performer-operated phone, **bounded** imperfections (no random jitter), duty-cycle metrics |
| camera | `impact_readability_v1` | screen-direction lock, target-visible-at-contact, decaying post-impact shake |
| camera | `observational_medium_wide_v1` | neutral observational framing |
| performance | `confident_direct_v1` | postural tone, gaze commitment, gesture directness, clean recovery |
| screen_action | `staged_near_contact_v2` | contact defaults to staged near-contact, no undeclared penetration, safety metrics |
| style | `anime_sakuga_action_v3` | a **style_transform**: typed dimensions (anticipation, silhouette separation, smear, impact frames) + invariants that must survive |

## How an agent uses them (cross-style "cooking")

The style profile is the key modular switch: it transforms a neutral action into a target
presentation **while preserving invariants** (action order, support/contact sequence, target
identity, recovery). Change one style dimension at a time to learn what actually produces the look
(§28.9 style ablation = the lab's one-lever A/B, applied to style). Full workflow:
`RUNBOOK_cross_style_switching.md`. Concept cards: `c_profile_system`, `c_style_transform_vector`,
`c_protected_invariants`, `c_style_ablation`, `c_superhuman_transform`.

## Status & provenance

These are `production_example` / `safety_scoped_example` profiles from CPCS-MX v1.0 — **structurally
sound but not yet lab-render-validated**. Treat their numeric dimensions as starting points; log runs
and promote via the normal evidence discipline. The frozen originals (with the paper, schemas, and the
reference compiler `compile_authoring_yaml.py`) live under `research/`.
