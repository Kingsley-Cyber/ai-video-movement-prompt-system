# Plan

Status lives in `ARCHITECTURE.md` (`REQ-077`), not here.

**The order of code work is Codex's master plan, slices A–E.** It is kept outside this repository
(`compiler-steering-implementation-plan.md` in the owner's Codex outputs folder) together with a
vocabulary report. This file maps the owner's requirements onto those slices. It defines no other
order. Roles set by the owner on 2026-10-03: **Codex builds; Claude writes specifications into
this folder and reviews.**

## State at HEAD `3c7b0d9`

Built (commits `a775f35`, `3c7b0d9`): the five `cpcs.direct.*` operations; eight passes (scene
and action, performance, staging, camera with twelve sublayers, light and colour, style, audio,
synthesis); a sealed decision ledger with inputs, relative anchor, justification and source
status; revisions that mark dependents; per-pass research packets; a Seedance capability file;
prose, canonical and JSON prompt formats. `WORK_ORDER_01_scene_action.md` is complete and kept
for the record.

Not built: any registry of fixed sets; questions to the user; start and end times on beats; the
labelled skeleton; the compact form; XML and YAML outputs; scenario rules; intake of the owner's
later research; taste and variants; multi-clip scenes.

## The loop (as built)

```
cpcs.direct.start             ask → session, intent context, pass plan
cpcs.direct.packet.read       one pass → question, sublayer slots, research, earlier decisions, locks
        (the LLM writes a proposal)
cpcs.direct.proposal.submit   Python validates → accepted into the ledger, or rejected with reasons
cpcs.direct.state.read        the shared scene state
cpcs.direct.finish            accepted decisions → overlays → existing score → existing build
```

## The owner's requirements, mapped onto the slices

Field-level detail for every row is in `INTEGRATION.md`; the sets are in `REGISTRY.md`.

| Requirement | Uses what exists | Adds | Slice |
|---|---|---|---|
| Registry and selection | ontology registry, coverage manifests, concept cards, pass slots | slots name a set; packets carry the menu; submit refuses a code outside the set; nothing-fits becomes a registry gap | B |
| Fixed order of reasoning | pass `reads`, sublayer stacks | loop order inside performance; physics and contact before body, body before camera | A |
| Scenario rules | concept cards with `use_when`, profiles, routing by the live decision | "for scenario X prefer Y" with its source; a departure needs a recorded reason | B |
| Questions for incomplete asks | the guided path's clarification candidates and answer capture | decision needs per pass; blocking first, then creative forks from the sets; answers become locked user-explicit decisions | A |
| Clock and carriers | scene duration, beat lengths, JSON output | start and end per beat derived by Python; XML for ordered timing; YAML for intent; natural language last, timing per model | C, D |
| Two lengths | prose carrier, capability budget, loss records | the labelled skeleton; the compact form by a fixed drop order with a never-dropped set | D |
| Model check per set | capability files, loss records | `model_support` per entry from renders; unsupported sets print visible wording or report a loss | D |
| Compounding | governed intake, packets that pick up new cards, outcome memory | a return must change a layer, a set or a rule; a "research next" list; renders update evidence | B, E |
| One channel at a time | `lab/experiments/`, seeds, revision records | the closed-loop camera tests as experiment definitions with a score gate | E |
| Pattern cards | profiles | a scenario's stack of pre-selected entries | A |
| Short planner | the eight passes | seven stages as an optional session mode | A |

## Decision record (as built)

```
decision_id, pass_id, layer, sublayer, target {path, item_id}, values, inputs,
relative_anchor null | {baseline {item, quality}, change {direction, step}},
justification, source_status, evidence_uses, lock, sequence, revision_of
```

## Evidence so far

The owner rendered a corridor fight through three champion versions on one model, one seed each
(files on his machine under `/Applications/CPCS_corridor_prompts/`, with
`/Applications/CPCS_CODEX_HANDOFF.md`). What those renders support, and what they do not, is
summarised in `PROMPT_SKELETON.md`. The compact form has never been rendered. No second seed.

## Open for the owner

- The eight flags in `REGISTRY.md`; one support set for the camera; height, reframing and physics
  sets.
- The eight proposed conflict resolutions in the Codex handoff.
- A second seed of the champion; a render of the compact form.
