# Context

Facts below were read from `main` at `29b0320` on 2026-10-03. Line numbers drift: re-check each
one with the repository map or a read before relying on it. A structural outline of any file is
available through the repository-control map (`lab/repo_control/derived/REPOSITORY_LAYER_MAP.md`).

## 1. What the public path does today

Probe: `python3 -m lab.application.cli strategy.compile` and `score.build` with
`{"text": "A jail fight scene, 15 seconds"}`. Saved in `reference/jail_fight_before.json`.

| Result | Value |
|---|---|
| Both operations | `success` |
| `score_status` | `ready` |
| `entities`, `scenes`, `shots`, `beats`, `actions`, `interactions` | all empty |
| Uncovered terms | `15`, `jail`, `screen`, `seconds` |
| Strategy executor | `direct`, operation `select_retrieved_controls`, profile `action` |
| Camera, performance, motion | profile defaults only |

`ready` means "nothing unresolved in the existing resolution contract". It does not mean a scene
was directed.

## 2. Why: the code paths

| Area | Fact | Where |
|---|---|---|
| Strategy | Six deterministic executors (`direct`, `algorithm_of_thoughts`, `atom_of_thoughts`, `chain_of_code`, `tree_of_thoughts`, `graph_of_thoughts`). None accepts an LLM proposal. | `lab/second_brain/src/reasoning_policy.py` about 225–527, `compile_directing_strategy` about 623–709 |
| Strategy → score | A strategy can only admit curated mapping ids; it cannot inject scene content. | `lab/compiler/score.py` about 227–286 |
| Intent | Normalized intent has no duration, subject count or setting. | `lab/second_brain/src/intent.py` about 536–574; uncovered terms from `query.py` about 518–551 |
| Score status | `needs_input` only for lock conflicts, unresolved profile conflicts, missing asset inputs. No scene-completeness check. | `score.py` about 835, 410–414, 650–662, 686–697 |
| **Overlays (the seam)** | `make_score_request(..., overlays=…)`. Overlay: `overlay_id`, `scope` (`user_defaults`, `project_profile`, `scene_override`, `shot_override`, `event_lock`, `explicit_user_correction`), `priority`, `values`, `locks`, optional `source_refs`. Values may set only the 53 declared field paths. | `score.py` about 162–210, 594–615; `lab/compiler/schemas/score_request.schema.json` about 29–58; `lab/profiles/universal/video_v1.yaml` about 16–69 |
| Scene collections | `entities`, `scenes`, `shots`, `beats`, `actions`, `interactions` are whole-array paths merged by item id. Items are untyped objects. | `lab/compiler/merge.py` about 25–67; `universal_score.schema.json` about 66–79 |
| Precedent | An overlay carrying entities, beats, actions and shots already exists for reverse compilation. Guided sessions turn decisions into overlays, in memory only. | `lab/compiler/reverse.py` about 37–126; `lab/application/cpcs_guided.py` about 121–170, `cpcs_guided_handlers.py` about 162, 201 |
| Duration | `project.duration_seconds` is an enum `[4, 6, 8]` in the score schema, the build request schema, the capability schema and `production.prepare`. The build takes duration as its own argument and never reads the score's. | `universal_score.schema.json` about 58; `build.py` about 87, 417–423; `service.py` about 2237 |
| Provider | The build is hard-wired to one provider and one capability file. Prompt budget is a capability fact (`prompt_budget_chars: 12000`). | `lab/compiler/build.py` about 51–57, 99–100, 232–302; `lab/compiler/providers/veo_3_1.yaml` |
| "2,000 characters" | Written as a rule in `lab/AGENTS.md` (about 78, 128, 168), `lab/blocks.yaml` (about 172) and `SKILL.md` (about 125–126). The compiler does not use it. | — |
| LLM proposes, Python validates (existing pattern) | Research extraction: sealed session re-hashed on every load, create-only per-packet captures, atomic replace, storage under `work/application/research_sessions/<id>/`, packets with a response contract, submit re-derives inputs and refuses drift, evidence must come from the packet. | `lab/second_brain/src/research_session.py` about 50–187, 287–441, 576–678 |
| Operations | `OperationSpec` and `_register`; closed argument schemas by default; role gating and exact-request authorization in `invoke`. | `lab/application/service.py` about 185–201, 1590–1610, 3753–3878; example registration about 2884–2906 with handler about 1332–1337 |
| Context per layer | `build_context_bundle` has `required_layers` (flags missing layers) and `excluded_layers` (the only real filter). | `lab/second_brain/src/context.py` about 404; `query.py` about 945, 1728 |
| Layers | 64 flat layers under 23 roots. No sublayers (parent hierarchy is the open part of `REQ-053`). | `lab/second_brain/curated/ontology_registry.json` |
| Knowledge | 132 concept cards, uneven. Nothing for Bartenieff, cause-and-effect reasoning, a shot scale or angle or lens catalog, staging, light and colour, relative anchoring, beat overload. Research objects are a single FACS seed. | `lab/concepts.jsonl`, `lab/second_brain/curated/` |

## 3. Traps already found (read before writing an overlay)

1. **Identity collision.** The merge picks the first of `id, entity_id, scene_id, shot_id,
   beat_id, action_id, interaction_id` present on an item. Two actions that both carry
   `entity_id` collapse into one. Use `id` as the only identity key; name references `actor`,
   `beat`, `target`.
2. **Order is lost.** Merged collections come back sorted by id. Carry an explicit `order`.
3. **No deletion.** Same-id items shallow-merge. A revision must rebuild overlays from the
   current ledger, never patch.
4. **Locks are whole-path.** An overlay lock on `beats` locks the whole array. There are no
   per-item locks.
5. **Everything on an item reaches the prompt.** The build prints each control as one line of
   compact JSON. Origins, justifications and other bookkeeping must stay in the session ledger,
   not on score items.
6. **Nested keys only.** `validate_overlay` indexes overlay values by top-level section. Use
   nested objects (`{"camera": {"shot_scale": …}}`), not dotted keys.
7. **Undeclared paths are rejected.** For example `camera.angle` is not one of the 53 field
   paths. Stay inside declared paths; per-shot camera content goes inside `shots[]` items.
8. **Golden outputs.** The score schema is closed and the score id is a content hash. Adding any
   field or warning to every resolved score would change every id. Six existing tests assert
   `ready` with empty collections. So a scene-completeness signal must live on the directing
   path only.
9. **Pinned counts.** Tests pin: application contract schemas (11), score schemas (4), build
   schemas (7), reasoning policies (6) and the executor registry, and the literal
   `cpcs-application/1.27`. Do not add to those sets or bump that version. Second-brain schemas
   in `validate.py` `SCHEMA_FILES` are not counted. Operations are not counted.
10. **Roles.** Chat-role tool evidence is frozen at 33 tools. Register new operations at operator
    role.
11. **Import direction.** The compiler imports the second brain. A session module in the second
    brain must not import the compiler; inject the compiler's check from the application handler.
12. **Stale sessions.** The compiler recomputes a terminology handoff at score time; a session
    started before a knowledge change can fail at finish. Return a typed `stale_session`.
13. **Tests and `work/`.** Sessions are written under `work/`. Tests must use a temporary root
    or clean up.
14. **The gate was red on `main`** only because the derived repository map was stale. The
    `direct-scene` branch starts with that rebuilt.

## 4. What was built elsewhere, and its status

A "director" was written in another repository by mistake: 16 named passes, a per-clip plan
file, validators, a prose emitter, eight run folders. It directs a scene but keeps it in its own
file, emits prose only, and repeats itself in the prompt (see the jail-fight analysis, summarised
in `PLAN.md`). It must not be installed here as a second compiler.

What is reusable is in `reference/`:

| File | Use |
|---|---|
| `director_passes_source.yaml` | the 16 passes, their questions, what each reads, their sublayers: source for the pass registry |
| `validator_rules.md` | the rules worth porting, with the wording of each failure |
| `jail_fight_proposal.json` | the acceptance fixture for the first pass, already in the decision-record shape |
| `jail_fight_before.json` | the "before" probe |
| `owner_statements.md` | the owner's own words and the contract statements he endorsed |

A full copy of that work also sits on the local branch `parked/director-import` on the owner's
machine. It is never merged or pushed. Do not depend on it.

## 5. Laws that bind this work (from the root `AGENTS.md`)

- Extend the owning file or module; no `_v2`, `_final`, `_new`, `_copy` forks.
- A new file is legal only when routing or the registry points to it in the same commit.
- `ARCHITECTURE.md` is the only implementation-status authority; no parallel roadmap or task file.
- `python3 lab/scripts/validate_repo.py` exits zero before every commit.
- Derived maps are rebuilt, never hand-edited (`python3 lab/scripts/sync_repo.py --fix`).
- Curated tier changes need explicit human review. Models propose; they do not promote.
- One `CHANGELOG.md` line per commit; commit subject imperative; agent Co-Authored-By line.
- Work is logged with `python3 lab/repo_control/src/control.py log` (`work_id` must match
  `^work_[a-z0-9][a-z0-9_-]{2,79}$`).

## 6. Update: state after two implementation commits (HEAD `3c7b0d9`, read 2026-10-03)

Sections 1–3 describe `main` before the directing path existed. Since then:

| Area | Now | Where |
|---|---|---|
| Operations | `cpcs.direct.start`, `.packet.read`, `.proposal.submit`, `.state.read`, `.finish`; operator role; `mode` is `scene_action` or `complete`; `model` is `veo-3.1-generate-001` or `seedance-2.0` | `lab/application/service.py` about 606–640, 1691–1744 |
| Passes | eight, in `lab/second_brain/directing_passes.yaml`; the camera pass has twelve required sublayers; performance has body, four effort slots, shape, space, connectivity, face, affect | that file |
| Values | values is a nonempty object with ownership/reference/causal and other checks; closed creative vocabulary membership is missing | `directing_session_contract.schema.json`, `lab/compiler/decisions.py` |
| Research in packets | in `complete` mode a context bundle is rebuilt per pass; selected concepts and source resolution reach the packet; an admitted card becomes eligible subject to relevance, scope and budget | `directing_session.py` about 199–254 |
| Questions to the user | none in the directing path; the older guided path has them in memory | `lab/application/cpcs_guided.py` about 217–240 |
| Time | directing supplies duration/order/minimums rather than a resolved schedule; supplied timing keys can reach the existing compiler | `lab/compiler/decisions.py`, `lab/compiler/build.py` |
| Prompt formats | `canonical`, `prose` (`Label n: key: value;` lines), `json`; no labelled skeleton, no compact form, no XML or YAML | `lab/compiler/build.py` about 212–330 |
| Providers | `veo_3_1.yaml` (4, 6, 8 s; 12,000 characters); `seedance_2_0.yaml` (4–15 s; budget unknown; manual export) | `lab/compiler/providers/` |

**Build provenance boundary.** `test_finish_emits_replayable_seedance_prompt_and_reference_still`
and `test_structured_projection_uses_the_same_score` in
`lab/application/tests/test_directing_pipeline.py` pass only when the gate is run with
`TMPDIR="$PWD/work"`: the fixture copies `lab/` into a temporary folder and `compile_build` runs
`git rev-parse HEAD` there (`lab/compiler/build.py` about 126–133). Without that environment
override they fail. Preserve those tests and diagnose the implementation's distinction
between a data root and authoritative code revision. Do not change `setUp`, fabricate a commit or
rely on an unrelated ancestor Git repository. The documented TMPDIR gate is scoped evidence;
if original tests and provenance requirements conflict, stop and report the exact conflict.

The follow-up inspection at documentation commit `5ca8281` found a clean branch. Historical state
in sections 1–3 is not a current blocker. Preferences and variant already exist at session start
and in packets; extend their use rather than recreating them. PLAN.md now owns the A–E follow-up
order within repository governance. This documentation correction implements no new runtime behavior.
