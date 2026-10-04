# Integration: what the owner's update adds, and where it lands

Owner's target (2026-10-03): **"modular, stackable, but intent and taste driven, and scenario
and situational research backed. If research says anime sakuga uses camera cuts, it adheres."**

This is a specification. The order of code work is Codex's master plan, slices A–E; this file
maps each requirement onto a slice and gives record shapes at field level. Shapes are proposals:
names may change to fit the owning schema, meanings may not. Nothing here authorises
implementation, renders, provider calls or promotion.

## The fixed order of reasoning

It is the order of passes and of slots inside a pass. It is not a graph executor.

```
intent, scenario, user answers
  → physics and contact      what touches what, what each thing does when acted on
  → action and body          the movement loop below
  → face
  → camera and framing       must show what the action needs seen
  → look, sound
  → synthesis
relative anchors and evidence status are checked on every decision at every step
```

Movement loop, one stack, filled in this order:

```
breath and core → Bartenieff connectivity → Effort (weight, time, space, flow) → Shape → Space → integration
```

The eight passes at HEAD already run in this order through their `reads`. What changes is inside
a pass: slots are filled in loop order and each bound slot selects from its set.

## 1. Selection from a set (slice B)

A slot in `directing_passes.yaml` names its set. The packet carries the menu:

```
slot_menu: {slot, set_id, set_version, cardinality: one|some,
            entries: [{code, term, visible_wording, pairs_and_conflicts, model_support, evidence_status}],
            omitted: <count>}          # entries left out for budget stay addressable by lookup
```

A decision stores the code, never the wording: `values: {effort_weight: "effort.weight.strong"}`.

Submit refuses: a code not in the set; two codes the entries mark as excluding each other; a code
from another version. When nothing fits, the proposal records a gap instead of a value:

```
registry_gap: {slot, need, nearest_codes: [...], reason}
```

Gaps are listed for the owner and feed the "research next" list (section 7).

## 2. Scenario rules (slice B)

Research-backed guidance of the form "for scenario X, prefer selections Y".

```
scenario_rule: {rule_id, when: {style | task | scenario facets}, strength: prefer | require,
                selections: [codes] , avoid: [codes],
                source_refs, evidence_status, model_scope}
```

The packet carries the rules that apply to the session's scenario, with their sources. Following
a rule is a `sourced_research` decision that cites it. Departing from a `prefer` rule needs a
justification naming intent or taste. Departing from a `require` rule is refused unless the user
said so. Rules enter through the same intake as any research; none is invented by the compiler.

## 3. Questions for an incomplete ask (slice A)

The guided path already has clarification candidates, an awaiting-user state and answer capture,
in memory. The directing session takes over that policy and persists it.

```
question: {question_id, pass_id, slot, kind: blocking | creative, text,
           options: [{code_or_label, consequence}]}
answer   → a decision with source_status user_explicit, lock true,
           evidence_uses: [{kind: user_answer, question_id, text}]
```

- **Blocking:** only what the user alone can know (who or what must appear, what must not change,
  the model and length when absent, limits on contact).
- **Creative:** a fork with a large consequence (tone, ending, how contact is shown), with
  options drawn from the sets.
- **Modes:** blocking only · up to a stated number · never ask. In "never ask" the LLM chooses
  and labels each choice `creative_application` or `inference`.
- A blocking question left open blocks `finish`. A creative one left open falls to the LLM.

## 4. The clock and the carriers (slices C and D)

Seconds are the canonical clock. Frames are a derived view from a declared rate.

| Carrier | Owns | State at HEAD |
|---|---|---|
| JSON score | the clock, numbers, invariants | scene `duration_s`, beat `min_s`; no start or end |
| XML | ordered event timing (onset, apex, offset as timed attributes) | not admitted |
| YAML | authored intent, inheritance, styles | not admitted as an output |
| Natural language | emitted last; loses units | prose lines; no labelled skeleton |

Fields to add:

```
beat:  {length_s (authored), start_s, end_s (derived by Python; lengths sum to the scene)}
event: {onset_s, contact_at_s (within its beat)}
```

The natural-language projection writes time per model: `lengths` ("(2.5s)", as every rendered
champion does), `timecodes` ("0.0–2.5s"), or `none` with a recorded loss. Where a capability
says exact timestamps are not followed, the prompt must not claim them.

## 5. Two lengths from one accepted scene (slice D)

**Full:** the labelled skeleton (`PROMPT_SKELETON.md`; champion v3 is the reference).

**Compact (about 2,000 characters, or the model's own budget):** each beat becomes one
sentence: number and length, framing, range, action, answer, result, prop state. Fields drop in
this order until it fits:

| Order | Dropped |
|---|---|
| first | the motion-priority line; physics detail beyond one sentence; sound detail; look detail |
| second | `WHY` and `TACTIC` lines; camera reasons and start and end frames; per-beat effort, shape and space |
| third | body lines on heavy hits; effort baselines; the struggle chain |
| fourth | camera framing per beat; counts; continuity anchors; what must be visible at key contacts |
| **never** | cast look tokens; the room's two walls and sides; beat order with action and result; the range chain; a changed prop's state; the end frame; the reaction-timing rule; the contact rule |

Rules: required meaning survives when its labelled line disappears; if the never-dropped set
does not fit, report it and print nothing shortened; the compact output is itself reviewed
before it is returned. The order is an untested hypothesis and the compact form has never been
rendered.

## 6. Model check per set (slice D)

`model_support` on an entry is per model and route: `untested`, `followed`, `partly`, `ignored`,
each with the run ids behind it. The prompt prints `visible_wording`, never the code. An
`ignored` entry is dropped with a loss record or moved to a carrier that model follows.

## 7. Compounding (slices B and E)

- **Intake rule:** a research return must add or change a layer's guidance, a set entry, or a
  scenario rule. A return that changes none of these is filed as reference only.
- **Automatic pickup:** a promoted card, entry or rule appears in the next packet whose pass and
  scenario it matches. No code change.
- **Research next:** knowledge gaps from packets and registry gaps from proposals are collected
  per layer into one list the owner uses to commission research.
- **Renders teach:** a recorded render updates `model_support` and the evidence on the entries
  and rules it tested, through the existing recorder. Nothing is promoted automatically.

## 8. One channel at a time (slice E)

The owner's closed-loop camera tests become experiment definitions under `lab/experiments/`:
fixed base prompt and seed, one set value changed per run.

| Loop | Varies | Fixed |
|---|---|---|
| A locked baseline | the action only | locked camera, medium, eye level |
| B pressure | locked → push in → pull back | framing |
| C follow | pan, tilt, tracking | one follow direction per clip |
| D reveal | rack focus, reveal, orbit (last) | — |
| E impact | whip pan, impact, handheld | — |

Score gate per clip: camera moved as named · framing held · angle consistent start to end ·
subject not smeared by the camera · one move only. A failing channel is changed by revising that
one decision; the prompt is not rewritten.

## 9. Pattern cards (slice A)

A scenario's stack of pre-selected entries: pick the motif, then the effort flavour.

```
pattern_card: {card_id, scenario, fixed_selections: {slot: code}, open_slots: [...],
               beat_template: [...], evidence}
```

Stored as a prepared base (profile). The planner's "pick a card" stage selects one or states that
none fits.

## 10. The short planner (slice A)

Seven stages as an optional session mode: intake · pick a card · cast and world · one loop over
the card's beats (selections first, free text second) · state ledger · read-back review ·
projection. Whether it replaces or sits beside the eight-pass mode is Codex's call under the
owner.
