# Work order 01 — the first pass: `scene_action`

**Repository:** `Kingsley-Cyber/ai-video-movement-prompt-system`, branch `direct-scene`.
**Requirement:** `REQ-077`. **Work id:** `work_req077_scene_action`.

## Goal

An external LLM's scene decisions for one pass reach the existing canonical score through the
public CLI. Ask used throughout: **"A jail fight scene, 15 seconds"**. Today that score is empty.

## Starting state (verify before editing)

- Branch `direct-scene`, clean worktree, `python3 lab/repo_control/src/control.py check` green.
- `python3 -m lab.application.cli --list` shows no `cpcs.direct.*` operation.

## Decisions already made (do not reopen)

1. Scene content enters the score as **overlays**. No change to `resolve_score`, to the score
   schema, to any field policy, or to any existing test.
2. The LLM is the caller. No model client is added. Tests use the fixture
   `handoff/direct_scene/reference/jail_fight_proposal.json`.
3. One pass in this slice: `scene_action`, with five sublayer slots submitted together:
   `scene`, `entities`, `beats`, `actions`, `interactions`.
4. The requested duration is kept as scene content (`scenes[0].duration_s = 15`). The score
   field `project.duration_seconds` and its enum are not touched in this slice. Provider fit is
   reported on the directing path; no build is produced when the duration is unsupported.
5. Origins, justifications, inputs and evidence stay in the session ledger. Score items carry
   scene content only (plus `id`, `order`, `caused_by`, `relative`).
6. `id` is the only identity key on any item. References are named `actor`, `target`, `beat`,
   `action`. Never put `entity_id`, `beat_id`, `action_id`, `scene_id`, `shot_id` or
   `interaction_id` on an item.
7. No seventh reasoning policy, no new application-contract schema, no version bump. New
   operations register at **operator** role and are not chat-exposed.
8. Rejection of a proposal is a **successful** response with `disposition: rejected` and typed
   reasons. Only malformed requests, role failures and a tampered session are errors.
9. No timestamps in session identity or in any hashed payload.

## Files

| Action | Path | Purpose |
|---|---|---|
| create | `lab/second_brain/directing_passes.yaml` | pass registry: one entry, `scene_action` |
| create | `lab/second_brain/schemas/directing_session.schema.json` | sealed session state |
| create | `lab/second_brain/schemas/directing_session_contract.schema.json` | `$defs` for packet, proposal, decision, submit result, state, finish result |
| create | `lab/second_brain/src/directing_session.py` | session store, packet builder, submit, state |
| create | `lab/compiler/decisions.py` | scene validators, `overlays_from_decisions`, `scene_completeness`, `provider_fit` |
| edit | `lab/second_brain/src/validate.py` | add the two schemas to `SCHEMA_FILES` |
| edit | `lab/application/service.py` | five `_direct_*` handlers and their `_register` calls |
| create | `lab/second_brain/tests/test_directing_session.py` | session tests |
| create | `lab/compiler/tests/test_decisions.py` | validator and overlay tests |
| create | `lab/application/tests/test_directing_surface.py` | public-path tests |
| edit | `lab/second_brain/AGENTS.md`, `lab/compiler/AGENTS.md`, `lab/application/AGENTS.md` | route the new files |
| edit | `lab/registry.yaml` | pointers: `directing_passes`, `directing_session_schema` |
| edit | `ARCHITECTURE.md` | `REQ-077` row (to `PARTIAL` with exact evidence) and one row in "Current ownership" |
| edit | `CHANGELOG.md` | one line, scope `lab` |
| rebuild | `lab/repo_control/derived/*` | through `python3 lab/scripts/sync_repo.py --fix` only |

Reuse, do not copy: the private-directory, read, create-only write, atomic replace and seal
helpers in `lab/second_brain/src/research_session.py` (import them; if importing private helpers
is refused by a check, extract nothing and stop to report). `build_intent_context`
(`intent.py`), `validate_overlay` and `make_score_request` (`lab/compiler/score.py`),
`load_capability` (`lab/compiler/build.py`). Import direction: `directing_session.py` must not
import `lab.compiler`; the application handler passes the compiler's check in as a required
callable (`submit_proposal(..., value_check=...)`).

## Pass registry entry

```yaml
schema: cpcs.directing_passes/1.0
passes:
  - pass_id: scene_action
    question: "Who and what is in the scene, what happens in what order, which actions and contacts occur, what each causes, and does it fit the requested length?"
    reads: []                      # no upstream pass in this slice
    research_layers: [action, whole-body movement, animation timing]   # must exist in curated/ontology_registry.json
    sublayers:
      - {sublayer_id: scene,        target_path: scenes,       required: true,  question: "Where and when; how long (keep the requested duration)."}
      - {sublayer_id: entities,     target_path: entities,     required: true,  question: "Who and what is on screen; what tells them apart."}
      - {sublayer_id: beats,        target_path: beats,        required: true,  question: "Ordered beats; minimum readable seconds each."}
      - {sublayer_id: actions,      target_path: actions,      required: true,  question: "Who does what, with which body part, to whom, on which beat."}
      - {sublayer_id: interactions, target_path: interactions, required: false, question: "Each contact or near miss: surface, reaction, settle, cause."}
```

Validate `research_layers` against the registry's `layers` at load; an unknown layer is an error.

## Session

Storage `work/application/directing_sessions/<session_id>/` (private directory, same modes as
research sessions): `session.json` (sealed, re-hashed on every load), `intent_context.json`
(create-only), `proposals/<pass_id>.json` (create-only).

`session_id = "directing_session_" + first 24 hex of sha256(canonical JSON of
{schema, text, user_constraints, profile_overrides, pass_registry_hash})`.

```
session.json:
{schema: "cpcs.directing_session/1.0", session_id,
 ask: {text, text_hash},
 intent_context_hash, pass_registry_hash,
 passes: [{pass_id, status: pending|accepted, proposal_hash|null}],
 decisions: [ …decision records, in acceptance order… ],
 ledger_hash, session_hash}
```

`ledger_hash` = sha256 of the canonical `decisions` array. `session_hash` seals the whole object.

## Operations

All operator role, `mutation_scope` as the research-session operations use for the same kind of
write (`operational` for start and submit; none for reads), closed argument schemas.

| Operation | Arguments | Returns |
|---|---|---|
| `cpcs.direct.start` | `text` (required), `user_constraints?`, `profile_overrides?` | `{disposition: created\|already_present, session_id, ask, intent_context_hash, pass_plan: [pass_id…], ledger_hash}` |
| `cpcs.direct.packet.read` | `session_id`, `pass_id` | `cpcs.directing_packet/1.0` (below); derived on every call, never stored |
| `cpcs.direct.proposal.submit` | `session_id`, `pass_id`, `packet_hash`, `proposal` | `{disposition: accepted\|rejected\|already_present, proposal_hash, decision_ids, rejections: [{code, decision_index, path, message}], ledger_hash}` |
| `cpcs.direct.state.read` | `session_id` | `{session_id, passes, decisions, scene: {scenes, entities, beats, actions, interactions}, ledger_hash}` |
| `cpcs.direct.finish` | `session_id` | `{session_id, ledger_hash, overlays, score, scene_completeness, provider_fit, build: null}` or `{disposition: stale_session, reason}` |

Packet:

```
{schema: "cpcs.directing_packet/1.0", packet_hash, session_id, pass_id,
 ask: {text},
 question, sublayers: [{sublayer_id, question, target_path, required}],
 upstream: [],                         # accepted decisions this pass reads (empty in this slice)
 locks: [],
 constraints: {requested_duration_s: 15 | null, duration_source: {start, end, text} | null},
 research: {concepts: [{id, name, what, layer, status, content_hash}], knowledge_gaps: [layer…]},
 response_contract: {schema: "cpcs.directing_proposal/1.0", identity_key: "id",
                     reference_keys: ["actor","target","beat","action","caused_by"],
                     source_status: [user_explicit, sourced_research, creative_application, inference]},
 trust_class: "bounded_directing_context"}
```

`requested_duration_s` comes from a deterministic parse of the ask (`<number> seconds|second|s|sec`),
with the matched span. `research.concepts` comes from the session's stored intent context,
filtered to the pass's `research_layers`; layers with no concept are listed in `knowledge_gaps`.
`packet_hash` covers everything in the packet except itself.

Proposal:

```
{schema: "cpcs.directing_proposal/1.0", pass_id,
 decisions: [ {decision_id, layer, sublayer, target: {path, item_id}, values: {…},
               inputs: [decision_id…],
               relative_anchor: null | {baseline: {item, quality}, change: {direction: more|less, step: slightly|more|much}},
               justification, source_status, evidence_uses: [ {kind: "ask_span", start, end, text}
                                                              | {kind: "concept", id, content_hash} ],
               lock: bool, revision_of: null} … ],
 not_applicable: [{sublayer_id, reason}]}
```

On acceptance each decision gains `pass_id` and `sequence` (its index in the ledger).

## Submit rules

The proposal is atomic: any rejection rejects all of it. Apply in this order; collect every
rejection found by a rule before returning.

| # | Rule | Code |
|---|---|---|
| 1 | proposal matches the closed schema | `schema_invalid` |
| 2 | re-derived `packet_hash` equals the one sent | `stale_packet` |
| 3 | pass is `pending`, or the proposal hash equals the accepted one (then `already_present`) | `pass_already_accepted` |
| 4 | every required sublayer has at least one decision, or is listed in `not_applicable` with a reason (only non-required sublayers may be) | `missing_required_sublayer` |
| 5 | each `target.path` is one of the pass's `target_path`s | `path_not_allowed` |
| 6 | `values` carries none of `id, entity_id, scene_id, shot_id, beat_id, action_id, interaction_id` (the item id is `target.item_id`); two decisions may target the same item only when their `values` keys are disjoint | `identity_key_not_allowed`, `duplicate_value_key` |
| 7 | `inputs` name decisions earlier in this proposal or in the packet's `upstream` | `unknown_input` |
| 8 | references close: `actor` and `target` name an entity item; `beat` names a beat item; an interaction's `action` names an action item | `unknown_reference` |
| 9 | `caused_by` names an action whose `order` is lower than the item's own (an interaction uses the `order` of its `action`) | `effect_before_cause` |
| 10 | beat `order` values are 1..n with no gaps or repeats | `beats_not_contiguous` |
| 11 | sum of beat `min_s` ≤ the scene's `duration_s` | `beats_exceed_duration` |
| 12 | `user_explicit` carries an `ask_span` whose `text` equals `ask.text[start:end]` | `user_explicit_without_span` |
| 13 | `sourced_research` carries at least one `concept` use whose id and `content_hash` are in the packet's `research.concepts` | `evidence_outside_packet` |
| 14 | `model_tested` is not admissible in this slice | `model_tested_not_admissible` |
| 15 | `lock: true` only on a `user_explicit` decision | `lock_requires_user_explicit` |
| 16 | a `relative_anchor.baseline.item` exists and sits on an earlier beat than the decision's item | `anchor_not_earlier` |
| 17 | the overlays built from ledger + proposal pass `validate_overlay` | `overlay_invalid` |

Rules 5–11, 16 and 17 live in `lab/compiler/decisions.py` and reach the session through the
injected `value_check`. Rules 1–4, 7, 12–15 live in `directing_session.py`.

## Decisions → overlays (`lab/compiler/decisions.py`)

`overlays_from_decisions(decisions, session_id, ledger_hash) -> list[overlay]`, always rebuilt
from the whole current ledger, deterministic (sorted keys, items ordered by `order` then `id`).

- Each item = `{"id": target.item_id, **values}`; a `relative_anchor` becomes
  `"relative": {"anchor": baseline.item, "quality": …, "direction": …, "step": …}`.
- `overlay_direct_user_<12 hex>`: scope `explicit_user_correction`; the **whole** `scenes`
  array (every scene decision, so the locked path is written once); `locks: ["scenes"]` when any
  scene decision has `lock: true`.
- `overlay_direct_scene_<12 hex>`: scope `scene_override`; `entities`, `beats`, `actions`,
  `interactions`; no locks.
- `source_refs` on both: `directing-session://<session_id>`, `directing-ledger://<ledger_hash>`,
  plus each cited concept id.
- Check the lock behaviour with a test before relying on it. If the two-overlay split produces a
  lock conflict, keep `scenes` in one overlay only and say so in the report.

`scene_completeness(scene) -> {directed: bool, counts: {…}, missing: [path…]}`: `directed` is true
when scenes, entities, beats and actions are all non-empty.

`provider_fit(scene, root) -> {capability_id, requested_duration_s, supported_durations_s,
status: supported|unsupported|unspecified, options: […]}` using `load_capability`. For the
jail fight: requested 15, supported `[4, 6, 8]`, `unsupported`, options: split into clips of at
most the largest supported duration; select a provider whose capability allows it (a later
slice); the owner shortens the scene.

## Finish

1. Load and re-verify the session; require the pass `accepted`.
2. Build overlays from the ledger.
3. Build the score with the session's stored intent context and those overlays through the same
   code path `cpcs.score.build` uses (`make_score_request` then `resolve_score`). If the compiler
   refuses the stored context because knowledge changed, return `disposition: stale_session`
   with the compiler's reason.
4. Return overlays, score, `scene_completeness`, `provider_fit`, `build: null`.

## Tests (write each before its code)

`lab/second_brain/tests/test_directing_session.py`
- `test_start_creates_sealed_session_and_is_idempotent`
- `test_packet_is_derived_and_hash_stable`
- `test_packet_reports_requested_duration_with_its_span`
- `test_submit_accepts_jail_fight_and_appends_ledger`
- `test_identical_resubmit_is_already_present`
- `test_different_second_proposal_is_refused`
- `test_stale_packet_hash_is_refused`
- `test_tampered_session_fails_closed`
- `test_missing_required_sublayer_is_refused`
- `test_user_explicit_requires_verbatim_ask_span`
- `test_sourced_research_must_cite_packet_evidence`
- `test_model_tested_is_not_admissible_yet`
- `test_lock_requires_user_explicit`

`lab/compiler/tests/test_decisions.py`
- `test_overlays_from_decisions_pass_validate_overlay`
- `test_overlays_are_deterministic_for_one_ledger`
- `test_identity_key_other_than_id_is_refused`
- `test_two_actions_by_one_actor_both_survive_resolution`
- `test_unknown_actor_reference_is_refused`
- `test_effect_before_cause_is_refused`
- `test_beats_must_be_contiguous`
- `test_beats_must_fit_the_requested_duration`
- `test_anchor_must_sit_on_an_earlier_beat`
- `test_bookkeeping_never_reaches_score_items`
- `test_provider_fit_reports_unsupported_duration`

`lab/application/tests/test_directing_surface.py`
- `test_public_path_directs_the_jail_fight` (start → packet.read → proposal.submit → finish:
  2 entities, 5 beats, 6 actions, 2 interactions, `scenes[0].duration_s == 15`, `scenes` in
  `constraints.locked_paths`, `directing-ledger://` in the provenance of `beats`,
  `score_status == "ready"`, `scene_completeness.directed is True`,
  `provider_fit.status == "unsupported"`)
- `test_finish_twice_gives_the_same_score_id`
- `test_plain_score_build_is_unchanged` (same text through `cpcs.score.build`: collections empty)
- `test_rejection_is_a_success_response_with_typed_reasons`
- `test_chat_role_is_denied`
- `test_direct_operations_are_operator_only_and_not_chat_exposed`

Follow the fixtures and temporary-root pattern of the existing research-session tests
(`lab/second_brain/tests/helpers.py`, `lab/application/tests/test_research_extraction_surface.py`).
Tests must not leave anything under the real `work/`.

## Commands

```bash
python3 lab/repo_control/src/control.py check
python3 lab/repo_control/src/control.py impact lab/application/service.py
python3 lab/repo_control/src/control.py log --work-id work_req077_scene_action --requirement REQ-077 --event started --actor <agent> --summary "<scope, verifier, rollback boundary>"
python3 -m unittest lab.second_brain.tests.test_directing_session lab.compiler.tests.test_decisions lab.application.tests.test_directing_surface
python3 lab/scripts/sync_repo.py --fix
python3 lab/scripts/validate_repo.py
```

End-to-end by hand (operator role):

```bash
echo '{"text": "A jail fight scene, 15 seconds"}' > /tmp/start.json
python3 -m lab.application.cli direct.start --role operator --input /tmp/start.json
# then packet.read, proposal.submit with the fixture and the returned packet_hash, then finish
```

## Acceptance

- All tests above pass; every pre-existing test passes unmodified; the gate prints `GATE GREEN`.
- Through the CLI the jail-fight score holds the directed scene with 15 seconds kept, and the
  provider-fit line says unsupported with options.
- `cpcs.score.build` for the same text returns what it returned before this slice.
- `REQ-077` reads `PARTIAL` with entrypoint, wiring, outcome and `verification:PASS` evidence,
  and names what is still open (slices 2–8).
- One local commit on `direct-scene`. Nothing pushed.

## Stop if

- A pinned count or version would have to change, or an existing test would have to be edited.
- The score cannot accept the overlays without changing `resolve_score` or a field policy.
- The stored intent context cannot be reused at finish for a reason other than stale knowledge.
- The gate fails for a reason outside this slice's files after one honest attempt to understand it.

Report the exact error and what you tried.
