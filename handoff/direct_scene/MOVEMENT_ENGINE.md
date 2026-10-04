# Movement engine: design, repository mapping and implementation plan

Version 0.7 (2026-10-03). v0.7 adds Part J: the system view of closed loops, layers, the control
atom shared by authoring, compiler and calculation, scoring and transfer, the experiment
scheduler, durations, and the architecture questions to settle before building. v0.6 added Part I, causal chains as a universal projection of
consequential changes (owner request; first render evidence pending). Version 0.5: Codex reconciled v0.4 with owner intent and actual runtime contracts:
experimental isolation differs from creative variation; requested carriers remain independent;
closed-set dependencies are local to the selected facet. v0.4 adds the
no-regression rule, shot-scale priority and the two variant axes (Part H). v0.1 was reviewed
adversarially; its 26 findings and their resolutions are in Part F. v0.3 added spacing per phase, continuous advantage, render-time failure checks and
Bartenieff initiation chains (owner research pasted 2026-10-03), and maps every part onto objects
that exist in this repository at HEAD `2641552`, including Codex's prop and hand ledger in
progress.

**Status.** Proposed engine specification, except the explicitly identified prop/hand subset.
"Enforced", codes and tables below describe proposed behavior unless marked "as built".
This document authorises no implementation, render, provider call or
promotion. `PLAN.md` owns the build order; Part D below is the proposed breakdown of that order for
this engine. A threshold needs an explicit owner choice, authoritative policy or measured
derivation before use. Calling it authored does not supply that authority. Source definitions,
project choices and tested model response are separate. Names that appear
in owner research but not in this repository (`PlanSegment`, `world.slots`, "layer 12",
`motion.spacing_expand`, `experiment.render_review`, `DirectorProblem`, `ReasoningRoute`,
`DecisionProjection`) are mapped in Part B; none is introduced as a new object.

---

## Part A: design

### A1. What it is

The LLM chooses who the characters are as movers (**signature**), what they can do (**arsenal** of
technique records), and the fight (**actions on one timeline**, grouped into beats and shots).
Python runs a deterministic replay of declared scene state that checks each action's
needs at the moment it starts, resolves contact outcomes, applies effects, derives advantage, and
returns typed rejections with repairs. It also reports movement variety. The LLM decides and
Python checks; the video model receives only the accepted result, in the carrier requested.

Target guarantee: an accepted plan is consistent with its records and admitted rules; the same
accepted inputs, source/rule versions and build settings produce the same state and output bytes.
Not guaranteed: physical realism beyond those rules, taste, or what a model renders.

### A2. Signature (per character)

| Field | Content | Set |
|---|---|---|
| `effort_baseline` | one pole per factor (weight, time, space, flow) | Laban Effort factors |
| `effort_range` | allowed poles beyond the baseline, each with a condition (`evading`, `casting`, `enraged`, `exhausted`, `wounded`, `power_active`) | Effort factors, project condition set |
| `kinetic_signature` | habitual initiation chains (see A6) | Bartenieff connectivity, chain kinds |
| `shape_habit` | habitual shape qualities | Laban Shape qualities |
| `space_habit` | habitual levels and reach | Laban Space level, reach |
| `mass_class` | `light`, `medium`, `heavy`, relative within the scene | project set |
| `turn_rate` | an authored relative description; any numerical bound requires explicit authority | project parameter |

Proposed check: an action's effort sits inside the baseline, or inside `effort_range` with its condition
true (`EFFORT_OUT_OF_RANGE`); turns respect `turn_rate` (`FACING_CONFLICT`). The signature is the
anchor for relative movement wording. Actor-baseline anchors need an admitted extension: the
current magnitude relation requires an earlier event, not a character baseline.

### A3. Technique records and family templates

Include only the records used by the accepted scene. When arsenal validation is enabled, an action may use only a technique in its
actor's arsenal (`NOT_IN_ARSENAL`). Adding one is an arsenal revision with a reason.

```
technique_id        KF_sweep_low
family              strike | kick | grapple | throw | lock | cast | deflect | parry | block_absorb |
                    footwork | evade | fall | get_up | hold_pose | prop_action | everyday | reaction
effort              {weight, time, space, flow}   registry codes; describes the stroke phase
shape               [registry codes]
space               {level, reach}
path                forward | back | lateral | vertical | circular | arc
phases              [{phase, length_s, spacing}] in order; phase from
                    preparation | initiation | stroke | follow_through | recuperation | hold
initiation_chain    {kind, root, path}             see A6
needs               list of need items              see A5
effects             {on_any, on_landed, on_blocked, on_parried, on_evaded, on_partial}
                    each a list of change items     see A5
contact             {part, target_part, contact_state}
counters            {beats: [...], loses_to: [...]}
chains_into         [technique ids]; chain_cut: fraction of recuperation after which a chained technique may start
stroke_counter      true if it may land inside an opponent's stroke
render_risk         low | medium | high | speculative
physics_exceptions  names allowed by the profile
source_status       one of the five evidence values (proposal admission rejects model_tested)
```

Python evaluates versioned, reviewed family templates; it does not invent their rules. A
template is scoped to its source or explicit project convention, not universal biomechanics.
The table is a candidate example, including grounded kicks and resource-limited magic, not
a rule for every kick, throw or spell. Each admitted family has mandatory needs and effects; a
record that omits or contradicts them is rejected `RECORD_UNDERSPECIFIED`.

| Family | Mandatory needs | Mandatory effects |
|---|---|---|
| `kick` | a named standing leg in support; `grounded` unless a profile exception; range `leg` or declared reach | support moves to the standing leg during the stroke |
| `strike` | range within reach; striking hand not holding unless the strike uses that prop | — |
| `throw`, `lock` | a hold on the target established by a prior `grapple` | target support changes; release clears the hold |
| `fall` | a cause (blow, sweep, lost support) | support `back`, `hip` or `hands`; may set `knocked_down` |
| `get_up` | `knocked_down`, or support `back` or `hip` | support returns to the feet |
| `cast` | the power resource `ready` | resource `spent` or `cooldown`; residue if declared |
| `hold_pose` | — | occupies time; minimum length per profile |

### A4. One timeline

Beats and shots are labels over one timeline in seconds. Seconds are canonical; frames are only a
derived view when the selected capability declares a frame rate. Frame rate is never inferred.

```
action   {id, beat, actor, technique, start_s, phases[], needs[], changes[]/effects, outcome?}
beat     {id, order, length_s, tactic, reason}       start and end derived from order and length
shot     {id, beat, end_beat, cut_at_s, elided_s, visible[], camera codes}
```

- Needs are checked at each action's `start_s` against the state as of that instant.
- Effects fire at the end of the stroke (contact) or the end of recuperation (non-contact).
- Same-instant dependent effects require an explicit causal order; independent effects may be
  applied together. Conflicting writes are unresolved. Actor/action IDs may sort output, but
  must not decide who wins a contact or whether a need holds.
- Holds are timed phases and count toward the clip.
- Overlap between two characters' phases is explicit through `start_s`, never assumed.
- Time skipped at a cut (`elided_s`) advances only explicitly declared off-screen events. A cut
  cannot invent state changes. Off-screen effects are
  shown or referenced in the first shot after the cut (`OFFSCREEN_UNREFERENCED`).

### A5. Need and change items

Codex's ledger defines prop needs and changes. The engine proposes additional item kinds;
their admission must preserve the current shapes. Initial `prop_state` and each new piece
require complete state; an existing prop change patches the supplied fields.

| Kind | Need item | Change item |
|---|---|---|
| prop (as built) | `{object, state?, location?, held_by?, hands?}` | `{object, state?, location?, held_by?, hands?, pieces?}`; at least one changed field |
| free hands (as built) | `{hands: [left, right]}` without an object, referring to the action actor | — |
| support | `{support: {actor, parts, surface}}` | same shape |
| airborne | `{airborne: {actor, state}}` | `{airborne: {actor, state, cause}}` |
| range | `{range: {a, b, bands}}` | `{range: {a, b, band}}` |
| facing | `{facing: {actor, referent, values}}` | `{facing: {actor, referent, value}}` |
| stage side | `{stage_side: {actor, side}}` | same |
| hold on a person | `{hold: {actor, target, part}}` | `{hold: {...}}` or `{release: {...}}` |
| power | `{power: {actor, resource, state}}` | same |
| damage | `{damage: {actor, not: [...]}}` | `{damage: {actor, add: value}}` |
| condition | `{condition: {actor, name}}` | `{condition: {actor, name, on}}` |

Referents for range and facing are a named character, the camera, or a prop, so a solo UGC clip
works. Laban reach describes body extension; pairwise range describes separation. There is no
automatic near/mid/far-to-clinch/arm/leg mapping. Reachability needs an explicit scene relation
or a source-backed mechanism, including the held prop's reach when relevant.

### A6. Spacing and initiation chains (new in v0.3)

**Spacing.** The following project menu is a candidate, not an admitted universal inventory.
An opted-in phase can select a code only after this facet's definitions and membership are admitted:

| Code | Meaning |
|---|---|
| `even` | constant speed |
| `ease_in` | slow start, fast arrival (breakdown late) |
| `ease_out` | fast start, slow arrival (breakdown early) |
| `ease_in_out` | slow, fast, slow |

Optional per phase: `favor` (`start` or `end`, a soft ease toward that key) and `hang` (true at an
apex). Curve exponents and in-between counts are frame-level detail; they belong to a later solver
or a numeric carrier, not to the directing session, and are not required here.

Proposed diagnostic: a stroke whose phases are all `even` is reported `SPACING_UNIFORM` unless the record states
a reason (a mechanical or deliberately robotic move). A clip whose strokes are all `even` fails the
diversity floor when one is set.

**Initiation chains.** Proposed `initiation_chain = {kind, root, path, pattern}`. The meanings of
chain kinds, connectivity codes and any anatomical adjacency relation need source/version
closure before enforcement. A described pathway may remain authored scene content without
claiming one of these unadmitted codes.

| Field | Values |
|---|---|
| `kind` | `simultaneous` (parts together), `successive` (adjacent parts in turn), `sequential` (non-adjacent parts in turn) |
| `root` | body part where the action starts |
| `path` | ordered body parts; adjacency is checked for `successive` |
| `pattern` | Bartenieff connectivity code the chain expresses |

Checks: the chain's `pattern` is in the actor's `kinetic_signature`, or the record states a reason
(`INITIATION_CHAIN_MISMATCH`). A `successive` path whose neighbours are not adjacent is
`CHAIN_NOT_ADJACENT`. Phases follow the phrase order preparation, initiation, stroke,
follow-through, recuperation; a phase out of order is `PHASE_ORDER`. This proposed phrasing
vocabulary must be reconciled with the repository's preparation/execution/contact-or-apex/
follow-through/recovery vocabulary by explicit definitions, not silent aliases.

### A7. Contact resolution

Every contact action resolves to one outcome: `landed`, `blocked`, `parried`, `evaded`, `partial`.

Resolve the authored outcome against declared contacts, timing and admitted counter rules.
Overlap alone does not establish a successful counter. Competing counters need explicit
accepted resolution; unresolved or missing outcomes produce `INDETERMINATE`, never an assumed
hit. An inconsistent declared outcome produces `OUTCOME_CONFLICT`.

Effects apply only for the resolved outcome. A miss never wounds.

### A8. Derived state

Python derives snapshots from authored initial facts and accepted changes. The snapshot is
computed, not independently authored. The current ledger derives only beat-boundary prop/hand
snapshots. The following wider slots and action-start snapshots remain proposals.

| Slot | Values |
|---|---|
| support | parts (`left_foot`, `right_foot`, `both_feet`, `one_hand`, `hands`, `knee`, `hip`, `back`, `none`) and surface (`floor`, `wall`, `furniture`, `opponent_body`, `water`, `air`, `power`, `wire`) |
| airborne | per character and per prop: `grounded`, `jumping`, `falling`, `flying`, `hanging`, `thrown`; cause; seconds |
| stage_side | per character: `left` or `right` of the action axis |
| facing, range | pairwise against a named referent |
| hands | per hand: `free`, `guard`, `holding:<prop>`, `holding:<character>:<part>`, `casting` |
| props | as built by Codex: state, location, held_by, hands; broken props retire into named pieces |
| power | per resource: `ready`, `charging`, `spent`, `cooldown`; residue |
| damage | visible only: `none`, `scuffed`, `bleeding_minor`, `torn_clothing`, `winded`, `stunned`, `knocked_down` |
| fatigue | `fresh`, `breathing_hard`, `spent`; narrows the effort range |
| advantage | proposed character-relative narrative states, derived only if a reviewed rule defines them |

**Advantage (new in v0.3).** It changes only on a resolved outcome, never by label. Each outcome
moves the narrative state only under an admitted rule. No numeric score, bands or steps are
required by this slice. A reversal (one character moving from `defending` to `pressing`) must be traceable to an
outcome; an authored `advantage` value on an item is rejected `ADVANTAGE_UNCAUSED`. Advantage feeds
the tempo report and may inform cut lengths in the camera pass. It never overrides authored timing.

### A9. Rules and rejection codes

Rejections retain the existing closed shape `{code, decision_index, path, message}`. A concise
repair suggestion may be included in `message`; an added `repairs` field would require an
admitted public-contract change. Do not invent a separate pass-retry quota. Repository
implementation repair follows the existing three-attempt fuse; model proposal policy is distinct.

| Rule | Code |
|---|---|
| prop state, hands, pieces and order (as built) | `PROP_STATE_INVALID`, `PROP_STATE_CONFLICT`, `HAND_OCCUPIED`, `PIECE_IDENTITY`, `PROP_VANISHED`, `PROP_SEQUENCE_UNRESOLVED`; undeclared entities use existing `unknown_reference` |
| record meets its family template | `RECORD_UNDERSPECIFIED` |
| every need holds at the action's start | `PRECONDITION_VIOLATION` |
| required affordance still exists | `AFFORDANCE_REMOVED` |
| contact or landing names a support | `NO_SUPPORT` |
| airborne has a cause and lands within the profile's limit | `UNCAUSED_FLIGHT`, `AIRBORNE_TOO_LONG` |
| range and side change only through effects | `RANGE_JUMP`, `SIDE_JUMP` |
| start after own recuperation, or inside a chain cut | `RECOVERY_SKIPPED` |
| counters land in open windows; declared outcomes agree | `WINDOW_CLOSED`, `OUTCOME_CONFLICT` |
| mass rule, with named exceptions (`leverage_throw`, `power_force`, `anime_impact`) | `MASS_CONFLICT` |
| turns within `turn_rate` | `FACING_CONFLICT` |
| effort inside baseline or conditioned range | `EFFORT_OUT_OF_RANGE` |
| effort time quality agrees with an admitted application rule, if any; it is not duration alone | `EFFORT_TIMING_MISMATCH` |
| spacing, chain, phase order | `SPACING_UNIFORM` (report), `INITIATION_CHAIN_MISMATCH`, `CHAIN_NOT_ADJACENT`, `PHASE_ORDER` |
| advantage only from outcomes | `ADVANTAGE_UNCAUSED` |
| power used only when ready | `POWER_NOT_READY` |
| residue and visible damage persist unless removed by an effect (`gag_reset` under `cartoon`) | `RESIDUE_LOST`, `DAMAGE_RESET` |
| actions and holds fit the clip | `OVERLOADED` (options: cut, split, lengthen; never squeeze) |
| concurrent strokes and visible moments within the model's limits | `UNREADABLE_DENSITY` |
| off-screen effects referenced after a cut | `OFFSCREEN_UNREFERENCED` |
| technique in the actor's arsenal | `NOT_IN_ARSENAL` |
| closed codes belong to their admitted source/version/facet; unresolved required code selection blocks acceptance | `CODE_NOT_IN_SET`, `SET_NOT_ADMITTED` |
| exceptions allowed by the profile | `UNDECLARED_EXCEPTION` |
| a needed field is missing or unresolvable | `INDETERMINATE` (never a permissive default) |

### A10. Physics profiles

One selected profile per scene. The following profiles and exceptions are project candidates.
Combine constraints only when an admitted rule defines their order. Conflicting pack values
require resolution; "strictest" is not defined for arbitrary style or physics choices.

| Profile | Allowed exceptions |
|---|---|
| `realistic` | `leverage_throw` |
| `heightened` | `leverage_throw`, `wire_assist`, `extended_hang` |
| `anime` | heightened set plus `hang_time`, `smear`, `impact_freeze`, `wall_run`, `speed_lines`, `anime_impact`, `power_force` |
| `cartoon` | anime set plus `squash_stretch`, `comic_hold`, `off_model_snap`, `gag_reset` |

Possible measured constraints include airborne duration, turn timing and provider readability.
None has an authorized numeric value here. Laban `sudden` is qualitative, not a duration cutoff;
holds, idle limits and advantage scores are not mandatory universal rules.

### A11. Diversity report

Reported, not enforced, unless the owner sets a floor (a floor is a target and is labelled so).

| Measure | Counted as |
|---|---|
| effort contrast | adjacent strokes differing in resolved weight or time; omitted values are unknown |
| spacing contrast | adjacent strokes with different stroke spacing; all-even strokes reported |
| level changes | Space level changes across strokes |
| path changes | changes of the record's `path` |
| range changes | pairwise band changes |
| tempo curve | declared changes of pace, authored holds and supported advantage reversals; no compulsory hold |
| repeats | repeated techniques in the accepted scene; no invented window size |
| exchange balance | share of beats each character initiates |
| motivation | each counted change links to a tactic from the closed set and a derived state change, otherwise `UNMOTIVATED_CHANGE` |

Creative variants may change multiple free choices while preserving locks, as the existing
packet specifies. An isolated experiment changes one declared lever; its chosen axis may be
camera or timing, so that axis cannot also be frozen. Non-tested factors remain fixed.
See H3 for the current experiment-preparation limitation.

### A12. Genre packs

These packs are proposed, opt-in project conventions, not facts implied by a genre name.
Only relevant accepted rules may enter a scene. Each pack rule is a key and a value. A conflict is two packs giving different values for one key
with no strictness order; it is returned as a question. A pack names a default profile; the scene's
explicit profile overrides it. Prompts describe style traits, never named shows or studios.

| Pack | Default profile | Arsenal seed | Rules (key: value) |
|---|---|---|---|
| `ugc_realism` | realistic | grip, twist, lift, pour, set down | phone occupies a hand only when accepted state says it is held; concurrent actions share no conflicting resources |
| `boxing` | realistic | jab, cross, hook, uppercut, slip, roll, cover, clinch | `weight_transfer_per_punch: required`, `footwork_between_combos: required`, `fatigue: on` |
| `kung_fu` | heightened | palm strike, sweep, kick, staff, lock, throw | `standing_leg_named: required`, `range_change_shown: required` |
| `anime_sakuga` | anime | authored techniques | select key poses, impact accents and spacing from scene intent; no mandatory flash count or spacing default |
| `supernatural` | heightened | authored powers, resources only when declared | charge vulnerability is a creative rule, not an automatic property of magic; declared residue persists |
| `urban_action_comedy_2d` | cartoon | street fighting, exaggerated stunts | `reaction_cut_after_climax: required`, `deadpan_hold_between_bursts: required` |

### A13. Render-time checks

Plan validation does not inspect rendered pixels. These are scored by the owner, or by the existing
authorized analysis/measurement tools, after rendering,
and are tied to the derived state that predicts them.

| Check | Tied to | Severity |
|---|---|---|
| foot float: a foot leaves the floor while support says it bears weight | support | fail |
| penetration: bodies or props pass through each other at a resolved contact | contact outcome | fail |
| contact read: the contact named in `READ` is visible | shot visibility | fail |
| settle: the final phase ends in a stable posture | final recuperation or hold | warning |
| spacing read: strokes do not move at constant speed | spacing | warning |
| prop continuity: a broken prop is never drawn whole | props | fail |

A failure informs a source-linked repair hypothesis through the existing revision path. A frame
failure does not prove which clause caused it; attribution remains scoped to the experiment design.

---

## Part B: where each piece lives in this repository

No new top-level objects, schemas or workflow. All content sits in existing untyped score
collections (`entities`, `actions`, `beats`, `shots`, `scenes`, merged by item id) and existing
owners.

| Engine piece | Repository home | Notes |
|---|---|---|
| signature, arsenal | `entities[]` item fields `movement.signature`, `movement.arsenal[]` | written by the performance pass; arsenal records are data on the entity, not a library file, until promoted |
| technique use on a beat | `actions[]` item fields `technique`, `start_s`, `phases`, `needs`, `changes`, `outcome` | extends Codex's `needs` and `changes`; `start_s` matches the build's existing timing field |
| profile, packs, tactic set choice | `scenes[]` item fields `physics_profile`, `packs` | set at intake from questions or authored |
| beats, shots | existing `beats[]` (`length_s`, `tactic`, `reason`), `shots[]` (`cut_at_s`, `elided_s`, `visible`) | start and end derived |
| derived state, advantage | computed in `lab/compiler/decisions.py`, extending `prop_hand_ledger` into a scene-state replay | never authored; snapshots used by validation and projection |
| rejection codes | `validate_decisions` in `lab/compiler/decisions.py`, injected into `proposal.submit` as `value_check` | same rejection shape as today |
| family templates, profiles, packs, thresholds | one versioned project data file under the compiler owner (`lab/compiler/movement_rules.yaml`), routed in `lab/compiler/AGENTS.md` and `lab/registry.yaml` | closed and versioned; owner changes only |
| closed sets (effort, shape, space, Bartenieff, spacing, chain kind, family, tactic, condition) | existing intake, ontology registry and coverage manifests in `REGISTRY.md`; candidate data stays staged until admitted | do not install a second vocabulary authority in `movement_rules.yaml`; path/body locations remain scene parameters unless a specific facet is admitted |
| pass questions and slots | `lab/second_brain/directing_passes.yaml` (performance: signature, arsenal; scene_action: choreography with technique ids; camera reads must-be-visible moments) | as Codex already does for props |
| render-time checks | `lab/experiments/*.yaml` (lever, variants, runs) and `lab/runs/results.csv`; review through `lab/verification/` | no new step type |

Owner-research names, mapped:

| Research name | Here |
|---|---|
| `PlanSegment`, `phases[]` | `actions[].phases` |
| `world.slots` | derived state snapshots in `decisions.py` |
| "layer 12 of the 16-layer stack" | none; the performance pass and the build projection |
| `motion.spacing_expand` | the projection step in `build.py` that writes spacing as wording or numbers per carrier |
| `experiment.render_review` | `lab/experiments` records and `lab/verification` |
| `SpacingUniformityError`, `AdvantageUncatalyzedError`, `InitiationChainMismatch` | rejection codes `SPACING_UNIFORM`, `ADVANTAGE_UNCAUSED`, `INITIATION_CHAIN_MISMATCH` |
| `frames` per phase | `length_s`; frames only as a derived view from a declared capability frame rate |
| `DirectorProblem`, `ReasoningRoute`, `DecisionProjection` | session, packet and accepted decision records; no new objects |

---

## Part C: final output carriers

One accepted score, several projections. The build's `prompt_format` today accepts `canonical`,
`prose`, `json`. The engine adds `yaml`, `xml` and `hybrid` as values of the same setting, through
the existing build owner, each with dispositions and losses like the others. The hybrid follows
the repository's existing `<cpcs_prompt>` envelope (`lab/variants/v006_measured_ugc_reference_hybrid.xml`):
a YAML projection, an XML schedule, and the canonical JSON, with "canonical_json owns meaning".

The example is one beat of the kitchen fight (beat 3, the kick).

**prose** (the owner's labelled skeleton; `PROMPT_SKELETON.md`):

```
BEAT 3 (2s)
  RANGE    DAI hops half a step back; a full leg-length apart
  DO       DAI throws one straight front kick, much harder than his hand strikes
  BODY     left foot plants, hips drive forward, right leg shoots out fully straight
  EFFORT   DAI at his strongest and most direct so far; the kick starts slow and arrives fast
  CONTACT  only the sole of his boot, onto LIN's crossed forearms
  REACT    her forearms fold into her chest; she slides three steps back until her back hits the fridge door
  PROP     broom still in its wall clip
```

Wording rules: retain accepted mechanics and relevant baselines. Visible wording is the proposed
NL baseline; requested codes, wording or both remain possible. Print essential support, outcome
and prop continuity when declared and relevant, without inventing missing controls.

**yaml** (authored intent; codes allowed):

```yaml
beat_3:
  length_s: 2.0
  range: {DAI-LIN: leg}
  action: {actor: DAI, technique: front_kick, start_s: 4.5}
  effort: {weight: strong, time: sudden, space: direct}   # relative: strongest so far
  phases: [{phase: preparation, length_s: 0.4, spacing: ease_in},
           {phase: stroke, length_s: 0.2, spacing: ease_in},
           {phase: recuperation, length_s: 0.5, spacing: ease_out}]
  initiation_chain: {kind: successive, root: left_foot, path: [left_foot, hips, right_leg], pattern: upper_lower}
  contact: {part: sole, target_part: crossed_forearms, outcome: blocked}
  support: {DAI: left_foot}
```

**xml** (ordered schedule, timed; follows `<xml_schedule>` in v006):

```xml
<beat id="b3" t="4.500-6.500" tactic="finish_it">
  <action actor="DAI" technique="front_kick" t="4.500-5.600" spacing="ease_in"/>
  <contact t="5.100" part="sole" target="LIN.crossed_forearms" outcome="blocked"/>
  <reaction actor="LIN" t="5.100-6.400" result="slides_back_3_steps" stop="fridge_door"/>
  <sfx t="6.400" cue="steel_boom"/>
</beat>
```

**json** (canonical numbers; the score's own values).

**hybrid**:

```xml
<cpcs_prompt version="1.0">
  <authority>canonical_json owns meaning. YAML and XML are projections and add no controls.</authority>
  <yaml_projection><![CDATA[ ...intent, cast signatures, rules... ]]></yaml_projection>
  <xml_schedule> ...one <beat> per beat as above... </xml_schedule>
  <canonical_json><![CDATA[ ...the resolved score... ]]></canonical_json>
</cpcs_prompt>
```

An NL-only request emits NL only; it does not require a structured token block. Deterministic
projection checks use canonical control-to-output trace, capability/loss artifacts and reviewed
final bytes. A requested structured or hybrid carrier can include a shared token block, checked
against the same score. A separate reader's interpretation of prose is advisory, not a second score.

Compact form: the drop order in `INTEGRATION.md` section 5 applies to every carrier; support, prop
state, range and outcomes are in the never-drop set.

---

## Part D: implementation plan

`PLAN.md` alone owns dependency order. Rows below map engine capabilities onto it, not a second
sequential work order or a requirement to make one commit per row. Tests are written first in **new** test files,
no existing test edited, `TMPDIR="$PWD/work" python3 lab/scripts/validate_repo.py` green, work
logged with `lab/repo_control/src/control.py`, `REQ-077` evidence updated, one `CHANGELOG.md` line.

| Step | Slice | Change | Files | New tests |
|---|---|---|---|---|
| 0 | C | prop and hand ledger (Codex; implemented and verified locally, gate green, 16 new tests) | `decisions.py`, `build.py`, `directing_passes.yaml` | `lab/compiler/tests/test_prop_hand_ledger.py` |
| 1 | A | required action/shot coverage, dependencies and clarification; optional declared-state extensions do not need all scientific sets | `directing_session.py`, pass registry and existing contracts | new coverage regressions |
| 2 | B | admit only the source-complete facets used by the selected case; project sets require owner review; scene parameters need no corpus enumeration | existing intake/registry owners | new membership/routing regressions |
| 3 | C | generalise declared state replay and timing, after its input coverage and applicable rules are resolved; explicit simultaneous dependencies | `decisions.py` | `test_scene_state_replay.py` |
| 4 | C | optional technique records and admitted scoped family rules; no compulsory arsenal quota | `decisions.py`, reviewed rule data under the existing owner | `test_technique_records.py` |
| 5 | C | resolved contact outcomes and outcome-keyed effects; no landed fallback | `decisions.py` | `test_contact_outcomes.py` |
| 5a | C | causal chains (Part I): `interactions[].chain` fields, mechanism core set plus profile extensions, trigger and consistency checks reusing the prop ledger and contact outcomes; off unless the scene declares chains | `decisions.py`, reviewed rule data under the existing owner | `test_causal_chains.py` |
| 6 | C | only necessary admitted profiles/packs; conflicts explicit, numeric limits require authority | reviewed rule data, `decisions.py` | `test_movement_profiles.py` |
| 7 | C | spacing, initiation chains and phase order only after relevant facet/adjacency definitions; effort quality kept distinct from seconds | `decisions.py` | `test_spacing_and_chains.py` |
| 8 | C | declared resources/conditions needed by the scene; fatigue/advantage only with admitted rules | `decisions.py` | new resource regressions |
| 9 | D | faithful NL and requested YAML/XML/hybrids, including the chain projection of Part I (I5); authoring inputs and output carriers kept distinct | existing build, loader, application contracts and affected schemas, not enum edits alone | `test_movement_projection.py` |
| 10 | E | diversity report; render scorecard as experiment definitions | `decisions.py`, `lab/experiments/` | `test_diversity_report.py` |

Boundaries for every step:

- Reuse existing owners and authority. Contract/schema changes are admitted only when needed by
  the selected behavior; historical pinned counts do not justify incomplete wiring or bypasses.
- Bookkeeping (justification, evidence) stays in the session ledger; score items carry content only.
- Nothing is promoted to curated knowledge without the owner.

## Part E: acceptance

End to end through the public CLI, for each scene: `cpcs.direct.start` → packets → proposals →
`cpcs.direct.finish` with build settings → the requested carrier.

| Scene | Must show |
|---|---|
| kitchen fight (anime, kung_fu) | broom break carried to the end in every carrier; the kick blocked, not landed; support named on every contact |
| kung fu master vs wizard (heightened, kung_fu + supernatural) | strike inside the charge window wins; cast while spent rejected; staff pieces persist |
| boxing exchange (realistic, boxing) | chained combination with weight transfer; fatigue narrows effort in the last beat |
| UGC bottle opening (realistic, ugc_realism) | when a phone is declared held, two-hand twist rejected until release; tripod capture does not acquire an occupied phone hand |
| 2D action-comedy beat (cartoon, urban_action_comedy_2d) | `gag_reset` accepted only under cartoon; reaction cut after the climax |
| corridor rail break (anime, kung_fu), chain declared | one chain on the break; its result agrees with the prop ledger's pieces; prose, YAML, XML and JSON carry the same chain; compact form keeps the result |
| UGC bottle opening, chain declared | cap seal cracks then lifts; a squash or impact-freeze mechanism is refused under the realistic profile |

Add only tests proving the selected slice and its admitted rules. Existing tests are immutable.
Possible cases include unavailable resources, retired props, effect-before-cause, unresolved
simultaneous effects and inconsistent declared outcomes. Density, all-even spacing, a creative
variant's number of changes, and omitted optional token blocks are not automatic failures.

Then render tests, owner-authorised only: the same fight at low and high diversity, with and without
spacing wording, realistic against anime profile, and prose against hybrid.

## Part H: no regression, shot scale and variant axes (v0.4)

Sources: the repository (`lab/AGENTS.md` one-lever rule; patterns `p006` format is realism-neutral,
`p009` format is a variance lever; `lab/experiments/e003_format_variance.yaml`) and the CPCS
handbook in the owner's cinema corpus (§12 9.2 representation policy; §05 FACS/Laban/Bartenieff
closure: shot-scale control value table, field meanings, open experiments).

### H1. No regression

1. **Off by default.** Legacy scenes without new state declarations or movement options retain
   their existing output. Explicit `prop_state`/`needs`/`changes` opt into the current ledger;
   they need no pack/profile flag. Broader movement behavior remains opt-in.
2. **Champion fixtures.** The owner's rendered prompts (corridor champion v3, the source sequence,
   the format variants v001, v002, v006) are kept as reference fixtures. Any engine change that
   touches projection preserves the rendered source bytes. Hand-authored winners do not yet
   have matching accepted scores; exact re-compilation is not a current software guarantee.
   Register a matching score and reviewed projection before treating it as an output fixture.
3. **Promotion by isolated A/B only.** An addition becomes a default for a pack only after a
   scoped isolated comparison meets declared acceptance criteria and receives owner review.
   A fixed seed or a tied score alone does not authorize promotion. Software consistency rules
   can be implemented and tested without claiming rendered efficacy or changing taste defaults.
4. **Prose wording rule.** Prose prints drawable body actions ("the push starts in his back foot").
   Codes and somatic terms may be included when requested or supported by the selected carrier;
   no ban follows from testing the NL baseline. The register comparison in H3 tests their effect.

### H2. Shot scale sets priority, not prohibition

The handbook gives a control-value table by shot scale and marks it "a selection heuristic that
requires provider experiments before being treated as a hard rule". This is proposed priority
guidance, not an automatic visibility filter. Preserve essential controls and user locks.

| Shot scale | Higher priority | Lower priority (first to drop) |
|---|---|---|
| ECU | FACS, gaze, eyelid | full-body connectivity |
| CU | FACS, gaze, head orientation | distal locomotion |
| MCU | face, head, upper-body Effort | foot mechanics |
| Medium | gaze, posture, Effort, Shape | small AU asymmetries |
| Full body | Laban, Bartenieff, support, trajectory | micro-FACS |
| Wide | spacing, trajectory, major Shape, rhythm | facial AU detail |
| Extreme wide | relationships, path, major action | most micro-expression |

Wide framing lowers micro-FACS priority; it does not ban it. Known visibility, narrative need,
budget and selected capability determine any omission. Unknown visibility is not invisible.
Record the actual omission reason, and fail rather than suppress a protected required control.

### H3. Isolated experiment axes and free creative variants

| Axis | Base against sibling |
|---|---|
| format | NL, YAML, XML, JSON, YAML+XML, hybrid (the `e003` plan) |
| layer authority | which layer carries causality for the beat: timing and spacing, kinetic chain, support state, or identity (Effort and Space signature) |
| register | visual direction ("pelvis initiates") against somatic terms ("Bow", sequential connectivity) |
| one Effort factor | same motion, one factor pole changed (Laban minimal pair) |
| one Shape quality | same motion, one shape change (Laban minimal pair) |
| spacing | same motion, one phase's spacing changed |
| timing | same action and FACS combination, different onset or length |
| camera | same action, one camera code changed |
| causal chain | same scene, one chain line present against absent (Part I6) |

For isolated attribution, change one declared factor and freeze non-tested factors. A camera
test does not freeze its camera code; a timing test does not freeze its tested timing. Creative
siblings can change multiple free choices; multi-change outcomes remain bundled evidence.

Current `cpcs.experiment.prepare` accepts isolated arms only when exactly one canonical control
differs. Same-score format/register comparisons change emitted bytes without necessarily changing
a canonical control, so this entrypoint does not yet certify them. An admitted experiment-contract
extension must bind the carrier/settings delta and all fixed meaning before such comparisons can
be prepared as isolated. Do not invent a score change to get past the current check.

### H4. Open questions the handbook names (not to be decided by implementation)

Whether a provider responds better to FACS identifiers or plain descriptions; whether Laban labels
beat kinematic proxies; whether the six Bartenieff patterns improve adherence; temporal adherence
to onset, apex and offset; and whether combined FACS, Laban and connectivity content increases
adherence or only increases prompt complexity. Each is a render experiment under H3.

## Part I: causal chains (v0.6)

Owner request (2026-10-03): treat "A physically causes B; B forces C" as a universal prompting
element across UGC, realism, cinema, animation, anime and supernatural scenes. First evidence: in a
paired render of corridor champion v3 against a challenger that added several physics lines, the
only change attributable to the challenger was a clearer rail break in beat 7, where it had a
chain line. That is one render per prompt, possibly different seeds, and bundled with other
changes. It is a reason to test, not a finding. Status of everything in this part: proposed,
off by default, pending the one-lever test in I6.

### I1. Definition

A chain is one statement, per consequential change, with five slots in a fixed order.

| Slot | Meaning | Type |
|---|---|---|
| `precondition` | the declared world fact that makes the result possible | reference to a scene physics rule or prior state |
| `cause` | who or what acts, with which part | free visible wording; actor and part must match the action |
| `mechanism` | how the material or body responds | closed set (I3) |
| `result` | the state change | change item in the A5 shape; for props, the ledger's change |
| `follow_through` | what the causing body does after | free visible wording, optional |

Corridor beat 7: the rail is held at both ends (precondition) · her forearm comes down on it
(cause) · it bends at the middle (mechanism) · it snaps there into a door half and a stub
(result) · her arm carries on past where the wood was (follow-through).

### I2. Triggers

A chain is warranted when a change persists or matters to what follows.

| Trigger class | Examples |
|---|---|
| object changes state | rail snaps, bottle seal cracks, glass shatters, door bursts open, liquid pours, cloth tears |
| body changes state | knocked down, thrown, stopped by a wall, a strike caught, balance lost, getting up |
| something changes hands | disarm, phone set down, product handed over, rail torn from the wall |
| the environment answers | water splash, dust, curtain swing, wall crack, a crowd parting |
| a power lands | charge, release, impact, persistent residue |
| a cause out of frame | a crash off screen, then a head turns toward it |

Not warranted: an ordinary block or strike that changes nothing, expressive gesture, camera moves,
and changes no later beat or shot uses. The LLM declares chains; Python does not infer them from
prose. A declared state change that a later beat depends on, without a chain, is reported (not
refused) as `CHAIN_SUGGESTED` when chains are enabled for the scene.

### I3. Mechanism set: shared core plus profile extensions

| Set | Members (proposed; owner confirmation pending) | Allowed under |
|---|---|---|
| core | `bends`, `snaps`, `cracks`, `shatters`, `tears`, `compresses`, `folds`, `deflects`, `slides`, `tips`, `pours`, `rebounds`, `stops_on_support`, `turns_with_the_blow`, `gives_way` | every profile |
| heightened | `wire_lifts`, `extended_hang` | heightened, anime, cartoon |
| anime | `impact_freeze`, `launch`, `hang_time`, `smear`, `shockwave` | anime, cartoon |
| cartoon | `squash_stretch`, `snap_back`, `gag_reset`, `comic_hold` | cartoon |
| power | `power_force`, `residue_persists` | packs that declare powers |
| perceptual | `notices`, `turns_toward` (a cause out of frame, no physical mechanism) | every profile |

A mechanism outside the scene profile's sets is refused (`MECHANISM_NOT_ALLOWED`). Members are
project vocabulary under `REGISTRY.md` admission rules; none is promoted without owner review.

### I4. Checks (proposed codes)

| Check | Code |
|---|---|
| the precondition names a declared rule or state that holds when the cause starts | `CHAIN_PRECONDITION_UNMET` |
| the cause's actor and part match the action it is attached to | `CHAIN_CAUSE_MISMATCH` |
| the result agrees with the prop ledger and outcome resolution (pieces, holders, locations) | `CHAIN_RESULT_CONFLICT` |
| the mechanism is allowed by the profile | `MECHANISM_NOT_ALLOWED` |
| nothing earlier uses the result | `effect_before_cause` (existing semantic check; full chain validation remains proposed) |
| at most one chain per contact | `CHAIN_DUPLICATE` |
| chain density | reported only (`CHAIN_DENSITY`); about two to four per 15 s is a starting reference for review, not a limit, until renders support a number |

Rejections use the existing shape and repair loop.

### I5. Authoring and compilation

**Authored** (YAML, on the contact item in the scene and action pass):

```yaml
interactions:
  - id: int_rail_break
    beat: beat_7
    action: act_forearm_chop
    contact: {part: forearm, target: rail}
    chain:
      precondition: {rule: rail_snaps_when_held_both_ends}
      cause: "her forearm comes down on the rail"
      mechanism: bends
      result: {object: rail, state: broken, pieces: [rail_half_door, rail_stub]}
      follow_through: "her arm carries on past where the wood was"
```

**Canonical** (JSON score): the same fields with ids on the `interactions` item; bookkeeping stays
in the session ledger.

**Projections:**

| Carrier | Form |
|---|---|
| prose (labelled skeleton) | `CHAIN    the rail is held at both ends, so it bends at the middle under the forearm and snaps there; her arm follows through past where the wood was` (template: precondition, so mechanism under cause, and result; follow-through) |
| YAML | the authored block |
| XML schedule | `<chain at="8.10" cause="forearm" mechanism="bends" result="snaps" pieces="rail_half_door rail_stub"/>` |
| JSON | the canonical fields |
| compact | folded into the beat sentence ("her forearm snaps the held rail at the middle"); the result is in the never-drop set, mechanism wording is dropped first |
| token block | chain id, mechanism code, result, for deterministic read-back |

The precondition is printed once in the scene's `PHYSICS` block and referred to by the chain; the
chain's result feeds the prop ledger, the camera pass's must-see moments, and later beats.

### I6. Evidence plan

| Test | Genre | Lever |
|---|---|---|
| beat 7 chain line, champion v3 against champion v3 plus that one line, same seed, two seeds | anime action, prop break | chain present against absent |
| UGC bottle opening | UGC realism | the seal-crack chain present against absent |
| glass knocked off a table, witness turns | cinema realism | the shatter chain, and the out-of-frame perceptual chain |
| supernatural strike with residue | supernatural | the residue chain |
| cartoon hit with squash and snap back | cartoon | the squash chain |

Score per render: the result visible and in order; the cause visible before the result; nothing
else worse (identity, text on set, holds, flash). A chain becomes a default for a pack only after
its isolated test meets the acceptance criteria and the owner reviews it (H1 rule 3).

### I7. Open questions for the owner

1. The mechanism members in I3.
2. Whether chains print as their own labelled line or fold into `REACT`.
3. Whether the density reference should become a pack setting once renders give a number.

## Part J: loops, layers and the unified calculation (v0.7, reviewed)

Owner intent (2026-10-03): scoring and tuning should be calculated, not guessed; once a choice is
tuned in one setting it should inform related settings; the system should run largely on its
own; the loops must cover camera, Laban, Bartenieff, face, physics and consequential state;
results must remain attributable to the prompt, event and duration. Authoring, compilation and
calculation must use the same accepted meaning.

**J13 review baseline:** runtime at `2ae2111`, with the v0.7 documentation reviewed against it.
This is a documentation proposal for owner approval, not permission to implement or spend.
`PLAN.md` contains the J11 answers and the sole proposed A–E build sequence. Status below
separates executable mechanisms from qualified evidence. No new ontology root is admitted here.

### J1. Where the evidence stands

The corridor renders are owner-reported external evidence. Their exact submitted bytes, actual
route/version, seed visibility and scores are not registered as qualified runs in this checkout.
Reported physics/chain improvements remain observations pending those receipts, not measured
or isolated effects established by this document.

The repo is not empty of render observations: `lab/second_brain/immutable/runs.jsonl:1` contains
five legacy rows, r001–r005, mirrored in `lab/runs/results.csv:2`. Their seeds and output hashes
are null, and no nonlegacy controlled rows, testimonials, admitted pose observations or Pegasus
observations are present in those immutable stores. They cannot establish the new directing
path's per-control performance. The existing render-to-evidence machinery is executable;
its lack of qualified data does not make the software unbuilt.

Some MX content already reaches the score: `lab/compiler/profiles.py:133` adapts component
profiles, including `lab/profiles/style/anime_sakuga_action_v3.yaml:6`; active FACS, Shape and
camera mappings are in `lab/compiler/control_translations.yaml:4`. A complete technique,
phase, chain or scientific vocabulary is not implied by these examples.

The evidence bottleneck is exact recording and applicable checks for this path. Coherence,
coverage and faithful projection work can proceed after approval without first spending on
renders. Statistical transfer and automatic selection must wait for qualifying evidence.

### J2. One control meaning, distinct definitions and occurrences

Use the existing canonical score and admitted ontology. Do not create a second atom vocabulary.
A closed member has source/version/facet/code identity. Its **occurrence** also needs the scene
item, target, interval and accepted value or relation. The same code used on two shots is not
one decision. Open actions, dialogue, body paths and locations remain authored content, with
provenance; they do not require a fabricated closed code.

Current `provider_neutral_controls` are path-level controls (`lab/compiler/score.py:340,776`).
An entire actions array can be one control. They are not yet phase/shot/atom occurrences.
A scoped occurrence binding is a proposed C/E extension of those controls and existing metric
lineage, not an added top-level score or editable authority. Authoring and projection reference
that meaning; scoring joins observations to it where the evidence permits.

Unexpected measured events and failures are valid source observations. Keep them unmatched or
as research gaps until reviewed; do not discard them because no planned atom predicted them.
Context includes exact route/version, source/rule versions, profile, shot purpose, visibility
and actual duration. The owner's 5/10/15-second examples do not close the duration universe.

### J3. Layers and existing ownership

These are audit groupings, not new registered semantic layers. Camera expands to the twelve
sublayers already in `lab/second_brain/directing_passes.yaml:154`.

| ID | Layer / required coverage | Current standing and owner |
|---|---|---|
| L1 | intent, scene purpose, tactics, beats, end frame | scene/action and synthesis passes; declared sequence/duration checks; target-scoped needs remain A |
| L2 | cast, identity, wardrobe, object identity and locks | score collections/merge laws and session locks; exact visual persistence requires observation |
| L3 | movement: technique, phases, spacing, key pose, prop/hand state | prop/hand replay built in `decisions.py:264`; full technique/phase engine proposed |
| L4 | support, trajectory, material/environment response, airborne and physical conventions | staging/body descriptions and MX constraints exist; generic physical-state replay proposed; compiler owns checks |
| L5 | contact, cause, mechanism, result and recovery | existing semantic contact/causal checks plus declared prop replay; Part I chain vocabulary/projection proposed |
| L6 | Effort factors and basic actions | performance slots exist; complete versioned code facets not admitted |
| L7 | Shape hierarchy and Space | performance slots and active hand-curvature mapping; full inventory not admitted |
| L8 | body connectivity and initiation paths | performance connectivity/body slots exist; closed connectivity/chain kind and adjacency rules not admitted |
| L9 | visible face, FACS, gaze and affect trajectories, kept distinct | optional face/affect slots; AU06/AU12 mapping; AU inventory not registered; no hard shot-scale gate |
| L10a | camera framing | required shot slot; scale menu proposed |
| L10b | camera angle | required slot; roll, horizontal and vertical components need distinct definitions |
| L10c | camera movement | required slot; complete versioned component menus not admitted; archived catalog is not current runtime coverage |
| L10d | camera movement quality, rig/support and feel | required quality slot; stabilization profile field; rig and texture are separate facets |
| L10e | lens/perspective/zoom | required lens slot; numeric/word bridges and closed bands remain scoped proposals |
| L10f | shot connection/edit and impact presentation | required connection slot; MX impact/style profiles reach score; exact cut execution is unqualified |
| L10g | composition and subject hierarchy | required composition slot; no universal closed composition list |
| L10h | camera relation to action: lead/follow/counter/observe | required relation slot; source-bound definitions/application guidance still needed |
| L10i | playback and camera timing | required time slot; canonical scheduling distinct from delivery frame precision |
| L10j | blur/readability | required blur slot; no validated per-model universal blur threshold |
| L10k | position, axis and subject-relative height | required position slot; height/landmarks are parameters, not missing universal codes |
| L10l | focus and its targets | required focus slot; visibility, deep/shallow/rack and target identity must remain distinct |
| L11 | event clock, overlap, duration and density | duration/order/min_s checks built; concurrent phase clock and learned readability/costs proposed |
| L12 | look, light, palette, sound, dialogue and performance synchronization | light/style/audio passes exist; cue/event fidelity and detector coverage are incomplete |
| L14 | context, reference assets and protected communication/claim constraints | existing context store, project fields, assets and binding owners; exact inputs/rights/loss are part of the plan, not a new ontology |
| L13 | authoring form, emitted carrier, compactness and dialect | canonical/prose/JSON built; structured authoring/new carriers/compact fidelity planned in D |

Source closure, evidence class, revisions, losses and provider capability are cross-cutting
requirements on these groupings. They are not optional decorations or extra prompt paragraphs.

### J4. Loops, owners and boundaries

| Loop | Existing owner and current boundary | Proposed completion |
|---|---|---|
| 1 plan | session proposals/revisions and compiler validation; no autonomous LLM caller | target-scoped gap/clarification loop, accepted repairs, dependent needs reopened |
| 2 fidelity | score/build, manifest hashes, dispositions/loss; semantic completeness partial | verify every consequential accepted occurrence reaches requested artifacts or explicit loss |
| 3 render/observe | runtime journal, application workflow, verifier, analysis/measurement and human review | manual receipt import and layer-specific observable checks; no invented observation |
| 4 experiment/derive | sealed flights, immutable recorder, accepted-experiment orchestrator and reflector | scoped occurrence outcomes; carrier delta extension; estimators only after usable records |
| 5 knowledge/maintenance | intake, source registry, ontology/coverage, maintenance, governed promotion and retrieval | admit relevant complete facets, retain gaps/negative outcomes and freshness; no runtime Polymath dependency |
| 6 taste | context profiles/packet preferences and exact testimonial capture/review | join explicit preferences to comparable decisions without treating adherence as taste |
| 7 provider/dialect | capability selection, build dispositions, adapter and provider-specific derived index | route/version-qualified response evidence; unknown never means supported or forbidden |
| 8 authorization/qualification | application exact-request authorization and release/stability owners | budget/approval-bound scheduler, scorer qualification, drift/held-out checks and explicit stops |

Loop 8 is the missing cross-cutting boundary in the original J4. It reuses existing owners;
no new scheduler may bypass them. Repairs can require dependent changes, not an arbitrary
one-field/one-rerender quota. Each child provider operation requires its existing authorization.

### J5. Verified loop × layer matrix

**B:** a complete bounded software path for the stated concern exists. **P:** an executable
subset or shared substrate exists, but the row's full coverage is incomplete. **S:** proposed
row-specific behavior only. **—:** neither current nor proposed behavior identified.
These are software statuses, not evidence scores. Generic handlers do not prove a complete
scientific inventory, suitable checks or qualified performance for every member.

| Layer | 1 plan | 2 fidelity | 3 render | 4 experiment | 5 knowledge | 6 taste | 7 provider | 8 authority |
|---|---|---|---|---|---|---|---|---|
| L1 intent, beats | P | P | P | P | P | P | P | B |
| L2 identity | P | P | P | P | P | P | P | B |
| L3 movement engine | P | P | P | P | P | P | P | B |
| L4 physics/support/environment | P | P | P | P | P | P | P | B |
| L5 contact/chains | P | P | P | P | P | P | P | B |
| L6 Effort | P | P | S | P | P | P | P | B |
| L7 Shape/Space | P | P | P | P | P | P | P | B |
| L8 connectivity | P | P | S | P | P | P | P | B |
| L9 face/gaze/affect | P | P | P | P | P | P | P | B |
| L10a framing | P | P | P | P | P | P | P | B |
| L10b angle | P | P | S | P | P | P | P | B |
| L10c movement | P | P | P | P | P | P | P | B |
| L10d quality/support/feel | P | P | P | P | P | P | P | B |
| L10e lens | P | P | S | P | P | P | P | B |
| L10f connection/edit/impact | P | P | P | P | P | P | P | B |
| L10g composition | P | P | S | P | P | P | P | B |
| L10h relation to action | P | P | P | P | P | P | P | B |
| L10i playback/timing | P | P | P | P | P | P | P | B |
| L10j blur | P | P | S | P | P | P | P | B |
| L10k position/height | P | P | S | P | P | P | P | B |
| L10l focus | P | P | S | P | P | P | P | B |
| L11 time/density | P | P | P | P | P | P | P | B |
| L12 look/audio/synchronization | P | P | P | P | P | P | P | B |
| L14 context/assets/claims | P | P | P | P | P | P | P | B |
| L13 projection | P | P | P | P | P | P | P | B |

Evidence for the cells, including the limits of shared P coverage:

| Cells | Verified path / limits |
|---|---|
| plan P | `directing_passes.yaml:1,47,125,149,237,259,280,303` → `directing_session.py:305` → `decisions.py:117`; slots/refs/locks/relative values checked, but complete target-scoped needs and closed menus absent |
| fidelity P | `score.py:740` → `build.py:176,212,539`; fields project, props persist and final bytes hash; no complete occurrence-to-clause proof/new requested carriers |
| render P | `application/render_evidence_workflow.py:389,739` → existing runtime/analysis/verification/record handlers; domain/profile metrics and translation metrics → `verify.py:2372`; P denotes these subsets, not full key-pose/physical/camera observability |
| render S | no dedicated component comparator/qualified detector located for these rows; generic semantic or human assertion envelopes are not equivalent to complete per-member checks; proposed checks in J6 |
| experiment P | `record.py:549,933,1222` → `accepted_experiment.py` → `reflect.py:139,329` → `indexes.py:442`; exact canonical deltas and metric lineage, not per-occurrence probability/pooling or a scheduler |
| knowledge P | `ontology_registry.json`, `source_registry.py`, `maintenance.py:192,375`, `query.py:1022`, session packets; generic intake/lookup/coverage exist, relevant complete memberships and application mappings remain incomplete |
| taste P | `context_store.py:48` → packet preferences at `directing_session.py:264`; `record.py:214,315` captures/reviews exact feedback; no automatic preference estimator |
| provider P | `build.py:337,501,539` and provider files classify/project controls; `indexes.py:442` scopes learned signals; not tested native response for every camera/movement code or Artlist mini parity |
| authority B | exact-request guard `application/service.py:3909,3941`, runtime lease/journal contract, `release/stability.py:248`; bounded software guards exist; no human authorization, render budget or live qualification is granted by this B |

Current checked-in evidence: five legacy rows, zero nonlegacy controlled runs. This is not a
numeric readiness score. The original "render loop unbuilt everywhere" reading and approximate
cell-completeness counts are withdrawn. Verify gates for each future selected cell through its
public path; generic coverage cannot silently become fully qualified row coverage.

### J6. Checks and observation limits

A check binds an existing metric/method, expected accepted control occurrence, actual artifact,
interval, visibility, source class, evaluator/version and uncertainty. Missing or ambiguous
observations remain unobservable/conflicting; they are not failures or zeros in an estimator.

| Concern | Existing check or missing check | Owner |
|---|---|---|
| artifact/hash, duration, aspect, resolution, frame rate | current technical checks in `build.py:608`, `verify.py:635`; unknown expected frame rate must not be tested as equality to null | compiler + verifier; manual-route unknown handling is a gap |
| action/order, identity/screen direction, product and camera purpose | registered domain/component/translation metrics; applicable semantic or reviewed lanes only | profiles/translation + verifier |
| visible AU06/AU12 | semantic translation metric exists; no certified full AU detector/intensity scoring | verifier; source-bound FACS admission in second brain |
| Shape hand-path curvature | deterministic average 2D curvature comparator; not full body Shape, support or 3D contact | `verify.py:442,532` |
| product visible | deterministic duty-cycle comparator | `verify.py:334` |
| body pose/support/slip/contact | hash-bound pose tracks exist; joint visibility/swaps/confidence and image-space ambiguity remain; no certified support/contact/force solver | `measurement.py:65,393`, verifier |
| Effort, connectivity, lens, focus, angle, blur and composition | proposed specific observables/rubrics; do not claim automatic scoring because a semantic envelope exists | selected profiles/metrics + verifier; research definitions through intake |
| causal chain/material result and persistent pieces | proposed event/result/visibility checks; current prop ledger validates declarations only | compiler + verifier; Part I is not implemented |
| dialogue, sound cues and lip/body synchronization | authored cues exist; isolated stems/phoneme timing and full synchronization checks are missing | audio/performance pass + verifier |
| assets, exact label/claim, omission and unintended events | source/asset bytes, approved claims and required output/loss must bind; unmatched failures retained | context/score/build + verifier + recorder |
| preference/taste and scorer disagreement | exact testimonial spans and source lanes already exist; compare aesthetics separately from adherence | recorder + stability owner |

`verify.py:63` has only two deterministic measurement-method implementations. Local pose
extraction is detected image-space evidence; it does not certify contact distance, grounded
support, foot slip or FACS by itself. Pegasus remains interpretation. Opposing lane verdicts
stay conflicts (`verify.py:679`); source reliability weights must not average them away.

### J7. Calculation and transfer: proposed, not currently estimated

Current REQ-026 derives scoped association/isolated-effect indexes, not per-atom probabilities
or a hierarchical estimator. Extend the existing reflector/index owner only after qualifying
records exist and the estimation contract is approved. Capture estimator version, training
record identities, check/evaluator versions, exact context, uncertainty and exclusions.
Do not invent priors, similarity weights, confidence cutoffs or probability values.

Fight evidence may suggest a UGC hypothesis; it does not automatically qualify a UGC prior or
production default. Pool only under an explicit tested transfer assumption. Unknown contexts
stay unknown; preserve negative and conflicting evidence. Correlated check sources and repeated
frames are not independent render trials. Add interactions only when the design supports them.

Use `release/stability.py` for calibration/held-out and evaluator drift safeguards. Data from
conflicts, unknown seeds or bundled prompts has its actual eligible use, not isolated authority.
The present software can be exercised with fixtures; fixtures do not train real effectiveness.

### J8. Scheduler: proposed under existing authorization

No autonomous experiment scheduler or best-per-atom production mode exists now. A future
scheduler proposes tests from an evidence coverage view, then uses the existing exact-request
approval, runtime journal, recorder and stability boundaries. It needs an owner-set budget,
permitted routes/operations, declared costs or unknown costs, and stop/recovery rules. None is
set by this document; unknown price cannot be represented as free spending.

Same-score format/register pairs need the H3 experiment-contract extension. Actual UI seeds
may be unknown; such imports are observations rather than seeded isolated proof. Selection
uses coherent candidate stacks and accepted state, not independently highest-scoring atoms
that conflict. Exploration, taste and production efficacy are different objectives. Choice
policy/version and any sampled choices must be captured for replay; root build creative modes
are not this unimplemented scheduler.

### J9. Duration: preserve accepted meaning

The score accepts positive numeric duration (`universal_score.schema.json:58`); the build
accepts positive whole seconds (`build_request.schema.json:24`). Veo's current capability is
4/6/8 seconds, while the manual Seedance profile lists 4–15. The schemas do not share a 4/6/8
restriction. Artlist/mini compatibility is not established by the BytePlus profile.

A 15-second accepted scene cannot silently become 10 or 5 seconds by deleting/merging beats.
Duration adaptation creates a proposed derived treatment/revision with explicit omissions,
new clock/state replay, preserved locks/end conditions and review. Compilation then emits
that accepted variant. Density and time-cost estimates, if learned, remain uncertain guidance
until scoped qualified evidence supports hard limits. Seconds stay canonical; frame rate is
never inferred from a prompt or genre.

### J10. Closed slots, open artistry

A closed-code slot must select an admitted member for its source/version/facet or record a gap.
Scene paths, distances, body landmarks, dialogue, tactic descriptions and artistic actions can
remain open authored/inferred content. They may not impersonate a missing scientific code.
Model response, source-definition closure and project conventions have separate admission and
evidence states. Every observation need not already have a planned atom; keep unexpected events
as observation or research candidates under existing owners.

### J11. Architecture questions and documented answers

All ten questions are answered with file citations in `PLAN.md` under "Part J architecture
answers for owner approval". Proposed extensions are separated from current facts. No answer
admits a vocabulary, approves a statistical method, sets a budget or authorizes implementation.

### J12. Proposed build order mapped to A–E

`PLAN.md` owns this order and the exit criteria. After owner approval:

| Order | Slices / existing owners | Dependency and result |
|---|---|---|
| coverage/identity/observability contract | A + relevant B + C/E interfaces | identify consequential targets, admitted facet/version or open description, occurrence and applicable checks; no full scientific inventory prerequisite |
| exact manual receipt and observation lane | E, runtime/application/verification/record owners | bind actual prompt/media/route/settings and preserve unknowns; choose a camera check supported by the available evidence, not all moves at once |
| champion as accepted treatment and faithful projection | C + D | source-preserved champion, resolved conflicts, accepted scene, clock/state and requested layout; report diff before treating it as a fixture |
| recorded controlled comparisons | E, existing experiment owners | usable sealed arms and applicable checks; same-score carrier contract first where needed; no promotion through bundled observations |
| estimates/coverage and transfer validation | E, reflector/index/stability | qualifying records before fitting; begin within tested scope, transfer separately evaluated; no arbitrary initial probabilities |
| authorized scheduler and evidence-conditioned selection | A/B packet/context + E application/runtime | reviewed estimator, budget and request-bound authority; capture choices, never add a competing executor |
| widen and automate scoring | relevant A–E owners | follow measured evidence gaps; admit each needed facet, qualify detector/rubric and preserve owner review for taste |

The original J12 render-first order omitted current-path representation/observability and manual
import prerequisites. Its pooling/scheduler stages move after usable evidence. This is not a
new list of mandatory engine modules; each admitted slice still obeys MSW and the repository gate.

### J13. Review instructions and approval boundary

The J5 cells, J3/J4 owners and J6 limits above are the current documentation audit. PLAN holds
all J11 answers, unresolved choices and this J12 mapping. Verify them again only if code changes
or new evidence invalidates them. Implementation, new tests, schema changes, scorer code,
providers and promotion wait for owner approval of the proposed slice. None occurs in this review.

## Part F: historical review findings (v0.1)

The following table records earlier proposed resolutions, not implementation proof. Current
scope, dependencies and corrected semantics are governed by Parts A, C, D and H and `PLAN.md`.

| # | Finding | Resolved in |
|---|---|---|
| 1 | the LLM writes the records it is checked against | A3 family templates |
| 2, 13 | needs checked at beat start; no timeline | A4 |
| 3 | airborne could end at clip end | A9, A10 |
| 4 | effects applied on a miss | A7 |
| 5 | signature not enforced | A2, A9 |
| 6 | no screen side | A5, A8 `stage_side` |
| 7 | unreadable overlaps | A9 `UNREADABLE_DENSITY` |
| 8 | mass refused legitimate scenes | A9, A10 exceptions |
| 9 | UGC has no opponent | A5 referents |
| 10 | cartoon resets refused | A9, A10 `gag_reset` |
| 11 | cross-counters refused | A3 `stroke_counter` |
| 12 | thresholds keyed unclearly | A10 |
| 14 | pack stacking undefined | A12 |
| 15 | no chain field | A3 |
| 16 | effort per phase unclear; holds unbudgeted | A3, A4 |
| 17 | two distance vocabularies; unadmitted sets | A5 mapping, A9 `SET_NOT_ADMITTED`, Part B |
| 18 | phone and two-hand ambiguity | A8 |
| 19 | grabs, throws, multiple opponents, thrown props, supports, blocks | A3 families, A5, A8 pairwise slots |
| 20 | no shots or cuts | A4 |
| 21 | no holds; damage states | A3, A8 |
| 22 | diversity gaming | A11, H3 one-lever variants |
| 23, 24 | overclaims | A1, A9 `INDETERMINATE` |
| 25 | prose read-back not deterministic | Part C token block |
| 26 | floors are targets | A11 |

Still open: music-beat alignment; every authored threshold value; the owner's confirmation of the
new closed sets (spacing, chain kind, path, family, tactic, condition).

## Part G: not claimed

The engine checks that a plan is coherent under its own records, the family templates and the
profile. It does not simulate physics numerically, judge taste, or predict a render. Arsenal moves
are creative until a card or a render backs them. Whether spacing wording, initiation chains or
varied effort improve renders is a render test.
