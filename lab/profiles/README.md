# Profiles — higher-order modular ingredients

Reusable, **versioned, composable** defaults adopted from the CPCS-MX package
(`research/CPCS_MX_Hierarchical_Motion_Grammar_Research_Package_v1.0/profiles/`). Where `concepts.jsonl`
cards are single ingredients, a **profile is a prepared base** — a named bundle of defaults +
`hard_constraints` + recommended verification metrics you inherit and then override.

Most files are current **component profiles** for movement, capture, camera, performance,
screen action, and style. `intent_routing.yaml` is a separate router-only configuration that detects
UGC, product, dialogue, cinematic, action, anime, multi-actor, and educational request labels. Those
labels activate the domain configurations under `domain/`. Every domain configuration extends
`profile://universal/video/1.0`; none defines its own score schema.

## Universal profile contract

Every future domain pack extends one universal video-score schema. It may declare required layers,
defaults, composition rules, conflicts, preferred workflows, serialization preferences, and
verification metrics. It must not create its own canonical schema, concept authority, or compiler.

Domain packs blend existing component axes. For example, a UGC product-demonstration pack can select
`capture/authentic_ugc_v2`, add marketing and product-interaction requirements, and retain the same
camera, performance, constraint, provenance, and verification fields used by a cinematic or action
pack.

## The idea (paper §26, §28)

```
natural-language direction + profile:// references + measured assets
        → authoring YAML  → deterministic resolve/merge/validate → canonical score
```

An authoring doc pulls profiles by axis, then resolves them through this precedence order:

```text
universal defaults
→ user defaults
→ project profile
→ domain profiles
→ scene overrides
→ shot overrides
→ event locks
```

Later scopes override earlier defaults. `hard_constraints` never silently drop. Conflicting values
must resolve through a named dominance rule or become a user decision. This is the compiler-backed
version of the lab's compose mode (`profile://` is the resolvable, inheritable form of a `blk_*`).

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
| routing | `intent_routing` | deterministic classification signals, knowledge layers, missing inputs, and the UGC/cinematic conflict decision |
| universal | `video_v1` | canonical field policies and typed merge operators for one provider-neutral score |
| domain | `ugc`, `product_demo`, `dialogue`, `cinematic_restraint`, `action`, `anime`, `multi_actor`, `educational` | configurable defaults, component-profile composition, conflicts, workflows, and verification metrics |

## How an agent uses them (cross-style "cooking")

The style profile is the key modular switch: it transforms a neutral action into a target
presentation **while preserving invariants** (action order, support/contact sequence, target
identity, recovery). Change one style dimension at a time to learn what actually produces the look
(§28.9 style ablation = the lab's one-lever A/B, applied to style). Full workflow:
`RUNBOOK_cross_style_switching.md`. Concept cards: `c_profile_system`, `c_style_transform_vector`,
`c_protected_invariants`, `c_style_ablation`, `c_superhuman_transform`.

## Status & provenance

The CPCS-MX component profiles are `production_example` / `safety_scoped_example` and are
**structurally sound but not yet lab-render-validated**. `lab/compiler/` now adapts them into the
universal score through declared paths, then merges domain configurations and transient overlays.
Treat numeric dimensions as starting points; log runs and promote through the normal evidence
discipline. The frozen originals, schemas, and reference compiler `compile_authoring_yaml.py` live
under `research/`.
