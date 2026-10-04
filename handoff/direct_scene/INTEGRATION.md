# Integration: what the owner's update adds, and where it lands

Owner's target (2026-10-03): **"modular, stackable, but intent and taste driven, and scenario
and situational research backed. If research says anime sakuga uses camera cuts, it adheres."**

This is a specification. The order of code work is Codex's master plan, slices A–E; this file
maps each requirement onto a slice and gives record shapes at field level. Shapes are proposals:
names and admissible scope follow PLAN.md and the owning contract. Nothing here authorises
implementation, renders, provider calls or promotion.

## Dependency-guided reasoning

Use the existing pass dependencies and accepted inputs. The following is a conceptual checklist,
not a universal pass order or graph executor. Face is inside performance, not a separate pass.

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

Optional sourced movement recipe, applied where relevant rather than mandatory slot order:

```
breath and core → Bartenieff connectivity → Effort (weight, time, space, flow) → Shape → Space → integration
```

The current eight passes do not implement this exact warm-up/checklist order. Their `reads` and
explicit revisions supply shared context; required scoped needs and menu membership are proposed
extensions. Accepted scene action must inform consequential performance, staging and camera choices.

This applies to NL descriptions too. The LLM selects the mechanics, intent and camera relationship
and authors visible wording with concise reasons; Python admits those choices. The final prose must
retain the accepted mechanism, not just name its layer. Structured wrappers remain requested options.

## 1. Selection from a set (slice B)

A slot in `directing_passes.yaml` names its set. The packet carries the menu:

```
slot_menu: {slot, set_id, set_version, cardinality: one|some,
            entries: [{code, term, visible_wording, pairs_and_conflicts, model_support, evidence_status}],
            omitted: <count>}          # entries left out for budget stay addressable by lookup
```

A bound slot stores the selected code/version, with its necessary scene parameters and authored
visible application. The example code does not replace the action's pathway or application reason.

Submit refuses: a code not in the set; two codes the entries mark as excluding each other; a code
from another version. When nothing fits, the proposal records a gap instead of a value:

```
registry_gap: {slot, need, nearest_codes: [...], reason}
```

Gaps are listed for the owner and feed the "research next" list (section 7). An allowed open
description can resolve creative content without claiming nonexistent closed membership.

## 2. Scenario rules (slice B)

Research-backed guidance of the form "for scenario X, prefer selections Y".

```
scenario_rule: {rule_id, when: {style | task | scenario facets}, strength: prefer | require,
                selections: [codes] , avoid: [codes],
                source_refs, evidence_status, model_scope}
```

The packet carries applicable rules and sources. A sourced principle and its authored application
retain distinct provenance; following guidance does not automatically make every chosen value
sourced_research. Departing from prefer guidance records an intent/taste reason. A require rule
needs reviewed authority, scope and override policy, consistent with existing locks and governance.
Rules enter governed intake; source text alone cannot silently create a hard constraint.

## 3. Questions for an incomplete ask (slice A)

The guided path already has clarification candidates, an awaiting-user state and answer capture,
in memory. The directing session takes over that policy and persists it.

```
question: {question_id, pass_id, slot, kind: blocking | creative, text,
           options: [{code_or_label, consequence}]}
answer   → a decision with source_status user_explicit, lock only when explicitly protected,
           evidence_uses: [{kind: user_answer, question_id, text}]
```

- **Blocking:** necessary exact inputs only the user can supply, protected identity/contact
  requirements, or a required route selection. Absent artistic detail can be authored; it is not
  automatically a blocking question. Do not invent numeric defaults to avoid a required input.
- **Creative:** a fork with a large consequence (tone, ending, how contact is shown), with
  options drawn from the sets.
- **Modes:** blocking only · up to a stated number · never ask. In "never ask" the LLM chooses
  and labels each choice `creative_application` or `inference`.
- A blocking question left open blocks `finish`. A creative one left open falls to the LLM.

Question/answer bytes and hashes need admission through the current session evidence owner;
user_answer is proposed, not an existing evidence kind. Never-ask cannot invent necessary exact
assets or credentials. Distinguish absent artistic direction from an actual blocking input.

## 4. The clock and the carriers (slices C and D)

Seconds are the canonical clock. Frames are a derived view from a declared rate.

| Carrier | Owns | State at HEAD |
|---|---|---|
| JSON score | accepted numeric timing and canonical meaning | directing supplies duration/minimums; compiler can retain supplied timing fields |
| XML | requested ordered/mixed-content envelope and reference bindings | proposed output contract, not implemented by this document |
| YAML | requested authored intent/inheritance/styles | proposed output contract, not implemented by this document |
| Natural language | accepted visible directing decisions and requested temporal expression | existing prose; new labelled/compact layouts remain proposed |

Fields to add:

```
beat:  {length_s (authored), start_s, end_s (resolved from the admitted schedule)}
event: {onset_s, contact_at_s (within its beat)}
```

The natural-language projection writes time per model: `lengths` ("(2.5s)", as every rendered
champion does), `timecodes` ("0.0–2.5s"), or `none` with a recorded loss. Where a capability
says exact timestamps are not followed, the prompt must not claim them.
Sum lengths for a serial card only; concurrent phases and event/cut boundaries retain their own
relationships. No mandatory traversal through all wrappers. A requested form or hybrid resolves
to one score and receives a supported projection or an explicit unsupported disposition.

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
The never-dropped set is also task-specific: body travel, sound or camera readability can be
essential even when their separate lines occupy a drop tier. Review each selected artifact against
accepted state; final bytes must match its reviewed preview. Budget units come from the request
or capability contract, with measured character/byte accounting rather than a universal limit.

## 6. Model check per set (slice D)

Proposed `model_support` is per model/route/task/version and tested control, with exact outcome
references. Keep definition authority separate. A carrier may print code, visible wording or both;
do not ban codes or infer that unknown/ignored semantic response equals interface incompatibility.
Required meaning survives supported translation or has an explicit loss/unsupported disposition,
consistent with locks. One bundled render does not prove each entry's effect.

## 7. Compounding (slices B and E)

- **Intake rule:** a research return must add or change a layer's guidance, a set entry, or a
  scenario rule. A return that changes none of these is filed as reference only.
- **Eligibility after admission:** a promoted card, entry or rule is available to existing retrieval;
  relevance, scope and budget determine selection. Record omissions; inclusion is not guaranteed.
- **Research next:** knowledge gaps from packets and registry gaps from proposals are collected
  per layer into one list the owner uses to commission research.
- **Renders teach:** recorder operations preserve immutable outcomes; governed experiment/reflection
  produces scoped candidates. Reviewed promotion owns curated support, never a render alone.

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

For each authorized isolated comparison, declare the intervention, protected variables and any
necessary dependent changes. One move, held framing/angle and zero blur are experiment-specific
choices, not universal scene gates. Compound camera components can be valid. Multiple changes
remain bundled observations; unchanged beats are not proof that individual changes were isolated.

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
projection. These are proposed client/session groupings under the existing owners. They do not
replace dependency checks or authorize a parallel workflow. PLAN.md owns their admission; measure
calls/context before claiming speed. Review includes accepted state and all selected final previews.
