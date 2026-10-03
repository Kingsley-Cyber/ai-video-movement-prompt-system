# Plan

Approved by the owner on 2026-10-03. Status of each slice is recorded in `ARCHITECTURE.md`
(`REQ-077`), not here.

## Approach

Five operations form a loop the connected agent drives through the existing CLI or MCP:

```
cpcs.direct.start             ask → session, intent context, pass plan
cpcs.direct.packet.read       one pass → its question, sublayer slots, research for its layers,
                               earlier accepted decisions, locks, constraints, response contract
        (the LLM writes a proposal)
cpcs.direct.proposal.submit   Python validates → accepted into the shared state, or rejected with reasons
cpcs.direct.state.read        the shared scene state: decisions by layer and sublayer
cpcs.direct.finish            accepted decisions → overlays → existing score → existing build
```

Accepted decisions enter the score as overlays, the seam the score already has. Origins,
justifications and evidence stay in the session ledger; only scene content goes on score items.

## Where each piece goes

| Piece | Path | Built on |
|---|---|---|
| Session store, packets, capture, evidence rules | new `lab/second_brain/src/directing_session.py` | the helpers and seal pattern of `research_session.py`; `build_intent_context`; `build_context_bundle` |
| Pass registry (passes, sublayer slots, questions, reads, allowed score paths, research layers) | new `lab/second_brain/directing_passes.yaml` | `reference/director_passes_source.yaml`; layer names checked against `curated/ontology_registry.json` |
| Schemas (session, packet, proposal, decision) | new `lab/second_brain/schemas/directing_session.schema.json`, `directing_session_contract.schema.json` | registered in `validate.py` `SCHEMA_FILES` |
| Decisions → overlays; scene validators | new `lab/compiler/decisions.py` | `validate_overlay` (`score.py`), `load_capability` (`build.py`); rules in `reference/validator_rules.md` |
| The five operations | `lab/application/service.py` (thin `_direct_*` handlers, `_register`) | `_score_build`, `OperationSpec` |
| Tests | new `lab/second_brain/tests/test_directing_session.py`, `lab/compiler/tests/test_decisions.py`, `lab/application/tests/test_directing_surface.py` | jail-fight fixture; no existing test is edited |

Sublayers are decision slots bound to score paths inside the pass registry. They are not new
ontology nodes; a true parent hierarchy in the ontology registry is `REQ-053` work under curator
review.

## Decision record

```
decision_id, pass_id, layer, sublayer,
target {path, item_id},
values {scene content only},
inputs [decision ids this decision read],
relative_anchor null | {baseline {item, quality}, change {direction, step}},
justification (brief),
source_status  user_explicit | sourced_research | creative_application | inference | model_tested,
evidence_uses [{kind: ask_span, start, end, text} | {kind: concept, id, content_hash}],
lock, sequence, revision_of
```

## Slices

Each slice ends with: owner tests green, full gate green, `REQ-077` updated, one local commit.

| # | Slice | What it must prove |
|---|---|---|
| 0 | **Clean start** (done when this folder was committed). Branch `direct-scene` from `main`; stale repository map rebuilt; this handoff routed. | Gate green on the branch |
| 1 | **The smallest real path.** One pass, `scene_action`: scene, characters, beats, actions, interactions and the requested duration, decided together. `start → packet.read → proposal.submit → finish`. See `WORK_ORDER_01_scene_action.md`. | The jail-fight score holds two fighters, five ordered beats, actions, contacts and 15 seconds; bad proposals are refused with typed reasons; the provider's 4/6/8 limit is reported, not applied silently; plain `cpcs.score.build` is unchanged |
| 2 | **Layers and sublayers.** Performance pass (Laban Body, Effort, Shape, Space; Bartenieff; face; affect) and camera pass (framing, angle, position, movement, movement quality, relation to subject, lens) read the accepted action. A pass's sublayers are submitted as one stack. Camera content is stored per shot in `shots[]`. Revisions go through a revision record and mark dependent decisions for re-check. The other passes in `reference/director_passes_source.yaml` are added as registry entries. A pass-loop workflow is added to the agent brief. | A camera stack that hides an action's initiation is refused unless it carries a stated creative reason; a later pass receives earlier decisions; a stale proposal cannot overwrite newer state |
| 3 | **Cause, contact, relative.** Validators at acceptance: one causal event per beat, cause before effect, a contact needs a stated reaction and a settle, hands not double-used, every comparison names an earlier anchor of the same quality. Wording rules are phase-specific, never blanket bans. | The same anchor and change always compile the same; a missing, later or mismatched anchor fails |
| 4 | **Research in every layer.** Packets scope retrieval to the pass's layers; a decision marked `sourced_research` must cite evidence that was in its packet and say how it applies; a layer with no research returns a typed gap. In parallel the owner's later research (hands and contact, cause and effect, camera move catalog, dialogue, capture realism, Laban and Bartenieff) enters through the existing `cpcs.research.*` intake. Rule for intake: a research return must add, change or edit a layer. The owner approves every promotion. | A decision shows the research it used and how; invention is never labelled research |
| 5 | **Model facts.** Duration becomes a real score field that any model length fits and the build reads; a capability file is selected per model; the 15-second model the owner renders on is added, with its dialect levers (for example emphasis marks) tagged by evidence; limits come only from the capability file; the universal "2,000 characters" wording is removed from `lab/AGENTS.md`, `lab/blocks.yaml` and `SKILL.md`. Structured and prose projections both stay available. | One accepted scene builds for two models with the differences listed as losses; a model with no length limit is not trimmed |
| 6 | **Taste and variety.** The loop reads the owner's saved user and project preferences (existing context profiles) and the existing creative modes. A pass can be asked for more than one proposal; variants are labelled by what differs; locked choices never vary. | Same locked content, different free choices |
| 7 | **Renders.** The owner renders the jail fight three ways (compiled, plain ask, a `v005`-style kinematic JSON), then the wording experiments (absolute against relative, wording rungs, emphasis marks per model, front-loading), recorded as `lab/experiments/` files and `lab/runs/results.csv` rows. | Only now may anything be called model-tested |
| 8 | **TwelveLabs, in place.** Apply to the existing provider (`lab/second_brain/src/providers/twelvelabs/`): current SDK range, `pegasus1.5`, `marengo3.5` default with `marengo3.0` selectable, the new embed request body, list and find assets in the library, image and video uploads including large files. Independent of slices 1–7. | Live readiness, list and find succeed; uploads with owner-named files |

Second acceptance scene once slice 2 works: the owner's UNFACED cold open (30 seconds, so it
needs two clips).

## What carries over from the build in the other repository

| The owner's idea | There it was | Here it becomes | Slice |
|---|---|---|---|
| An LLM follows a reasoning control layer, pass by pass | a pass file and a protocol document | the pass registry: all 16 passes and their sublayers as entries | 1–2 |
| Shared scratchpad | a run folder | the sealed directing session and its decision ledger | 1–2 |
| Laban, Bartenieff, FACS, affect, camera sub-layers, camera move catalog | pass sub-modules and a vocabulary file | sublayer slots; catalog and vocabularies enter as research | 2, 4 |
| Relative prompting | anchors and deltas with checks | the same rules at acceptance, stored on scene items, projected per model | 3 |
| Cause and effect | physics events, pathway and hand checks | the same validators in `lab/compiler/decisions.py` | 3 |
| Beats must fit the clip | a fit check with options | checked at submit; reported against the model's real durations | 1, 5 |
| Research becomes knowledge | an ingest document, wording recipes, a gap log | the existing governed intake, same rule | 4 |
| Agnostic core, model dialects | per-model profiles with levers | capability files under `lab/compiler/providers/` | 5 |
| Natural language or structured | prose only | both, through the existing build | 5 |
| Taste and variety | planned, not built | slice 6 | 6 |
| Experiments decide | experiment briefs and arms | `lab/experiments/` records | 7 |
| A model can pick the work up | a queue of work orders | `REQ-077`, the work log, this folder, the agent brief | all |
| TwelveLabs refresh | a new client | fixes to the existing provider | 8 |

## What the jail-fight test showed about the old output

The old path produced a readable fight, but: a result was written before its cause; each contact
was told two or three times; five controls were dropped to fit a character limit that is not
universal; the scene never reached this repository's score. Two findings were rejected as hard
rules: a claimed wording contradiction on one action (the fix is phase-specific wording), and the
idea that structured JSON and relative prompting compete (they do not).
