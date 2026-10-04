# The natural-language prompt skeleton (compile target)

The owner supplied this skeleton on 2026-10-03 as the layout the natural-language projection
must produce. His full example, a 15-second kitchen fight, is kept verbatim in
`reference/owner_nl_skeleton_kitchen_fight.txt`. It has not been rendered. Everything it implies
about how a video model reads it is a hypothesis until the owner's renders say otherwise.

**Reference.** The rendered reference is champion v3 of the corridor fight, with the reference
sequence second, both read-only on the owner's machine
(`/Applications/CPCS_corridor_prompts/CHAMPION_corridor_elite_v3.txt`,
`CHAMPION_source_sequence.txt`). Where this file and a champion differ, the champion wins. The
kitchen example in `reference/` is the same skeleton moved to another scene; its later versions
add a props rule (a broken prop's pieces get new names), continuity anchors in the camera line,
and the struggle on a stopped strike. Those additions have not been rendered.

**What the renders support** (one model, one seed each, the owner's judgement): stating the
range on every beat fixed wrong techniques and idle opponents; a side-on camera kept punches
visible; showing the cause inside an insert fixed a prop breaking with nobody in frame. **Still
weak:** a prop knocked out of someone's hands fails; final holds run long; left and right are not
reliably controlled by a sides line. **Not established:** the effect of any single line (they
entered in groups), `TACTIC`, the motion-priority line, cast baselines, a second seed, any other
model, and the compact form.

The skeleton is a **projection layout**, not a second score. Every field below must come from
accepted decisions in the directing session and the canonical score; the build writes them out in
this order for providers that take long natural-language prompts.

## The idea in one line

State what is **absolute** once at the top (who, where, what things are made of, what "normal"
is), then write each beat as **changes against that**, with cause before result and each thing
said once.

## Header blocks (absolute, stated once)

| Block | What it holds | Pass that decides it | Slice |
|---|---|---|---|
| `GOAL` | length, aspect, one line, start state, end state | scene | 1 |
| `MOTION PRIORITY` | which concern wins when two compete, per beat | synthesis | 2 |
| `STYLE` | medium, stylisation devices, and what style may never change (order, who touches what, who is who) | style | 2 |
| `LOOK` | palette anchors in positive words, light source and direction, shadow, bloom | light and colour | 2 |
| `PACE` | global tempo rule, when reactions land, where the one hold is | time | 2 |
| `CAST` | per character: identity, then **baselines**: Effort (four factors as words plus one visible gloss), Body (where movement starts, where weight sits), Shape, Face | entity, performance | 2 |
| `WORLD` | layout by side, prop inventory with counts, screen sides that never flip | world, staging | 2 |
| `PHYSICS` | what each material and prop does when acted on; who is heavier; what reaches further; what needs two hands | physics | 3 |
| `ANCHORS` | the named "normal" for each quality (speed and force, reach) as a thing visible in a named beat | time, physics | 3 |
| `RULES` | contact policy, when reactions land, exact counts, how distance may change, what an insert is | synthesis | 3 |
| `PHRASES` | beats grouped into named phases | time | 2 |
| `END`, `SOUND`, `AVOID` | end state; sounds in order; what must not appear | scene, audio, synthesis | 2 |

## Beat fields (changes against the header)

Beat header: number, seconds, and a named camera setup that can be reused ("A", "A, wider", "B").

| Field | Meaning | Absolute or relative | Pass and sublayer |
|---|---|---|---|
| `TACTIC` | what each character is trying to do in this beat | absolute | intent |
| `RANGE` | the distance between them and how it changes | relative to the last beat; changes only by a shown step, lunge or blow | staging |
| `CAM` | scale, position, angle, movement type and quality, its relation to the subject **with the reason**, start and end framing | setup reused by name; move stated against the subject | camera stack |
| `DO` | the action, with counts | magnitudes against `ANCHORS` | action |
| `ANSWER` | what the other character does in reply | — | action |
| `WHY` | why the action has this quality, tied to the tactic | — | the decision's justification |
| `BODY` | where the action starts and the order it travels (foot, hips, limb) | — | performance: Bartenieff |
| `EFFORT` | Laban Effort for this beat | **relative to the character's own baseline in `CAST`** ("changes here: from light and evasive to strong and direct") | performance: Laban Effort |
| `SHAPE` | the body's form and whether it advances, retreats, rises, sinks, widens, closes | against the `CAST` baseline | performance: Laban Shape |
| `SPACE` | path, level and direction of travel | absolute directions and heights | performance: Laban Space |
| `CONTACT` | exactly which body part meets which surface | absolute | interaction |
| `READ` | what the viewer must be able to see | — | attention, coupled to camera |
| `REACT` | first reaction, what follows, how it stops | timing relative to the hit ("at the same instant") | physics |
| `FACE` | eyes, gaze and one visible change | against the `CAST` baseline | performance: face |
| `PROP` | where every prop is after the beat | absolute state, carried forward | continuity |

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

These follow from the skeleton's own `RULES` and become validators in the slice that gives them
a consumer.

1. Beat seconds sum to the clip length (the example: 10 beats, exactly 15.0 s).
2. Counts in `RULES` equal the counts in the beats' `DO` lines.
3. Every beat has `RANGE`; a change of range names the step, lunge or blow that caused it.
4. `PROP` forms an unbroken chain: each state follows from the previous one and from an action
   in that beat; the prop inventory in `WORLD` is never exceeded.
5. Every `CONTACT` uses only parts allowed by the contact rule.
6. A reaction's cause is in the same or an earlier beat; an insert introduces no new event.
7. Screen sides stated in `WORLD` hold in every `CAM` line that shows both characters.
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

Until then: nothing here is model-tested.
