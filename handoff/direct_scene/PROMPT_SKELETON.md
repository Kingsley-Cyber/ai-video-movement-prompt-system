# The natural-language prompt skeleton (compile target)

The owner supplied this skeleton on 2026-10-03 as the layout the natural-language projection
must produce. His full example, a 15-second kitchen fight, is kept verbatim in
`reference/owner_nl_skeleton_kitchen_fight.txt`. It has not been rendered. Everything it implies
about how a video model reads it is a hypothesis until the owner's renders say otherwise.

**Reference.** The rendered reference is champion v3 of the corridor fight, with the reference
sequence second, both read-only on the owner's machine
(`/Applications/CPCS_corridor_prompts/CHAMPION_corridor_elite_v3.txt`,
`CHAMPION_source_sequence.txt`). Champions fix the historical submitted bytes; PLAN.md and explicit
owner intent govern new authoring. An approved resolved treatment is distinct from its evidence. The
kitchen example in `reference/` is the same skeleton moved to another scene; its later versions
add a props rule (a broken prop's pieces get new names), continuity anchors in the camera line,
and the struggle on a stopped strike. Those additions have not been rendered.

**What the renders support** (one model, one seed each, the owner's judgement): stating the
the bundle adding range/positive action wording was reported to improve techniques and activity;
side-on coverage was associated with readable punches; a cause-visible insert accompanied improved
prop causality. These are scoped observations, not isolated clause effects. **Still
weak:** a prop knocked out of someone's hands fails; final holds run long; left and right are not
reliably controlled by a sides line. **Not established:** the effect of any single line (they
entered in groups), `TACTIC`, the motion-priority line, cast baselines, a second seed, any other
model, and the compact form.

The skeleton is a **projection layout**, not a second score. Every field below must come from
accepted decisions in the directing session and the canonical score; the build writes them out in
this order for providers that take long natural-language prompts.
The LLM must reason about the content of these fields as it does structured decisions: why this
action, which support/body pathway, what response and which camera makes it readable. Visible
mechanisms and concise reasons belong to accepted authoring; the emitted NL must preserve those
consequential choices. Printing the labels around generic prose does not satisfy this target.
Requested YAML/XML/JSON and hybrids remain available; this layout is not their replacement.

## The idea in one line

State what is **absolute** once at the top (who, where, what things are made of, what "normal"
is), then write each beat as **changes against that**, with cause before result and each thing
said once.

## Header blocks (absolute, stated once)

| Block | What it holds | Pass that decides it | Slice |
|---|---|---|---|
| `GOAL` | length, aspect, objective, start/end state | scene_action, synthesis | A, C, D |
| `MOTION PRIORITY` | which concern wins when two compete, within locks | synthesis | C, D |
| `STYLE` | medium, devices and protected semantic meaning | style | C, D |
| `LOOK` | palette, lighting and visible treatment | light_color | C, D |
| `PACE` | action timing, reaction relations and selected holds | scene_action, performance, camera.time | C, D |
| `CAST` | identity plus relevant Effort/Body/Shape/Face baselines | scene_action, performance | A, B, C, D |
| `WORLD` | layout, object inventory and scoped spatial relations | scene_action, staging | A, C, D |
| `PHYSICS` | contextual support, causes and material response | scene_action, performance, staging | C, D |
| `ANCHORS` | visible baselines and referenced magnitude relations | performance, staging, camera | C, D |
| `RULES` | admitted scoped contact/count/range/insert policy | relevant decision owners, synthesis | C, D |
| `PHRASES` | authored beat grouping | scene_action | C, D |
| `END`, `SOUND`, `AVOID` | terminal state, audio and scoped exclusions | scene_action, audio, synthesis | C, D |

## Beat fields (changes against the header)

Beat header: number, seconds, and a named camera setup that can be reused ("A", "A, wider", "B").

| Field | Meaning | Absolute or relative | Pass and sublayer |
|---|---|---|---|
| `TACTIC` | what each character is trying to do in this beat | authored intent | scene_action |
| `RANGE` | the distance between them and how it changes | relative to the last beat; changes only by a shown step, lunge or blow | staging |
| `CAM` | scale, position, angle, movement type and quality, its relation to the subject **with the reason**, start and end framing | setup reused by name; move stated against the subject | camera stack |
| `DO` | the action, with counts | magnitudes against `ANCHORS` | scene_action |
| `ANSWER` | what the other character does in reply | response bound to the incoming action | scene_action |
| `WHY` | why the action has this quality, tied to the tactic | — | the decision's justification |
| `BODY` | where the action starts and the order it travels (foot, hips, limb) | — | performance: Bartenieff |
| `EFFORT` | Laban Effort for this beat | **relative to the character's own baseline in `CAST`** ("changes here: from light and evasive to strong and direct") | performance: Laban Effort |
| `SHAPE` | the body's form and whether it advances, retreats, rises, sinks, widens, closes | against the `CAST` baseline | performance: Laban Shape |
| `SPACE` | path, level and direction of travel | absolute directions and heights | performance: Laban Space |
| `CONTACT` | exactly which body part meets which surface | explicit relation | scene_action interactions, staging |
| `READ` | what the viewer must be able to see | shot/event binding | camera, synthesis |
| `REACT` | caused response, continuation and stopping | bind contact reactions to contact; defenses to attacks | scene_action, performance, staging |
| `FACE` | eyes, gaze and one visible change | against the `CAST` baseline | performance: face |
| `PROP` | where relevant props/pieces are after the beat | explicit state, carried forward | scene_action, staging |

## How the skeleton steers absolute and relative

- **Absolute** carries state: materials, layout, sides, identity, baselines, counts, contact parts,
  directions and heights.
- **Relative** carries magnitude and change: "much harder than his hand strikes", "strongest and
  most direct so far", "from light and evasive to strong and direct", "slides back at her speed".
- A relative statement always points at something already made visible: an entry in `ANCHORS`,
  a `CAST` baseline, or an earlier beat.
- Cause and effect are split across fields in a fixed order: `DO` (cause), `CONTACT`,
  `REACT` (result, then how it stops), `PROP` (what stays changed). `PHYSICS` states in advance
  what each object will do, so a reaction in a beat is never the first time the model hears of it.

## What Python can check from this layout

These are scoped recipe/declared-state checks, admitted where they have a consumer under PLAN.md.
They are not universally required fields or evidence of rendered mechanics. The historical champion
does not already satisfy every proposed addition. Preserve its bytes and record approved deviations.

1. Beat seconds sum to the clip length (the example: 10 beats, exactly 15.0 s).
2. Counts in `RULES` equal the counts in the beats' `DO` lines.
3. Every beat has `RANGE`; a change of range names the step, lunge or blow that caused it.
4. `PROP` forms an unbroken chain: each state follows from the previous one and from an action
   in that beat; the prop inventory in `WORLD` is never exceeded.
5. Every `CONTACT` uses only parts allowed by the contact rule.
6. A reaction has its cause binding; an insert references a continuing action/phase and may advance
   it without introducing an unrelated event or counting a repeated view as a new strike.
7. Declared screen/axis locks hold in their scope; do not force one permanent side across all setups.
8. A two-handed prop is not used while a hand is otherwise occupied.
9. Every comparison names an anchor, a baseline or an earlier beat that exists.
10. A `PHYSICS` precondition is met where it is used (the handle is held at both ends in the
    beat where it snaps).

## Time in the skeleton

Beats carry a length in seconds ("(2.5s)") and the lengths sum to the clip. No champion carries
start and end times. The clock itself lives in the score; how time is written in the prompt
(lengths, timecodes, or none) is a per-model choice. See `INTEGRATION.md` section 4.

## Points to settle with the owner (not decided here)

| Point | Detail |
|---|---|
| Two meanings of "anchor" | `ANCHORS` names magnitude baselines; beat headers use "ANCHOR A / B" for reusable camera setups. One of them should be renamed (for example "SETUP A"). |
| A chained comparison | Beat 9: "each strike faster than the last" compares against the previous change, which the owner's own rule ("no chains") excludes. Options: compare each to the anchor, or accept rising sequences as a named pattern. |
| Lens and focus | `CAM` covers nine of the twelve camera sublayers; focal length and focus are absent in the example. |
| Density | 10 beats, 9 cuts, 4 inserts under one second and about 14 strikes in 15 s. Whether a model renders this is unknown. The project's old reading-time conventions would call it overloaded; `PACE` asks for full speed on purpose. Report the density; do not forbid it. |
| Length | About 14,400 characters. Only for models with no short prompt limit. A short form per model is a dialect decision. |

## Tests the owner's renders should decide

Same scene, same model and seeds, one change at a time:

1. Full skeleton against the plain one-line `GOAL`.
2. With and without the `WHY` lines.
3. Labelled fields against the same content as flowing prose.
4. `EFFORT` as Laban words, as the visible gloss only, and both.
5. One 15-second clip against the same beats split into two clips.
6. With and without the `PHYSICS` block.

The champions have owner-reported rendered outcomes. The new clauses, precise individual effects,
compact projection and cross-model transfer remain unqualified. These proposed render comparisons
authorize no provider execution and do not halt dependency-ready software work.
