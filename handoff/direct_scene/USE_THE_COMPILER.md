# Use the compiler to write a video prompt

Read this when someone asks for a video prompt. Root `AGENTS.md` wins on conflict.

**Do not compose the prompt from `lab/blocks.yaml` or by hand.** The LLM (you) makes the creative
decisions; Python validates them and builds the prompt. A prompt written outside this flow has no
validated motion plan, no closed movement selections and no score.

## Setup, once per session

```bash
git pull
python3 -m pip install -r requirements.lock    # first time only; Python 3.9 or newer
echo '{}' | ./bin/cpcs doctor --role operator  # the top-level "status" must be "success"
```

If the packages are already installed or there is no network, skip `git pull` and the install.
Start a new session after every `git pull`; a session opened before an update may be refused.

Doctor's inner `result.status` may say `NOT_READY` (frozen runtime, architecture freeze, retrieval
contract): those belong to the older guided path and do not block directing.

Windows: run inside WSL. The authority lock uses `fcntl`, which native Windows Python lacks;
`.gitattributes` keeps `bin/` scripts on LF line endings so they run under WSL.

## The flow: one brief, one card, one run

Python runs the eight passes, the ledger and every check for you. You make the creative decisions
once, in one file, in the fixed reasoning order. Do not hand-write proposals or helper scripts.

1. Put the user's idea, verbatim, in `work/<name>/ask.txt` (`work/` is ignored by Git) and read
   the brief for every pass at once. It includes the menus, research and the motion-plan rules, so
   you do not need to read the source code:

   ```bash
   python3 -m lab.application.direct_runner brief --ask-file work/<name>/ask.txt
   ```

2. Copy `handoff/direct_scene/reference/example_card.yaml` (complete and valid; a test runs it) to
   `work/<name>/card.yaml`, keep its shape and replace the content. Put the same ask text in its
   `ask` field.
3. Check the motion plan against the card's own scene (no session needed):

   ```bash
   python3 -m lab.application.direct_runner check --card work/<name>/card.yaml
   ```

   Small commands to edit or assemble the card are fine; do not write programs that author choices.
4. Run it:

   ```bash
   python3 -m lab.application.direct_runner run --card work/<name>/card.yaml
   ```

   It submits every pass through the public operations, builds the prompt in the director layout
   and prints it with a report (session, score, characters, calls, seconds) saved under
   `work/direct_runs/<session>/`. If a check fails it stops and names the card field (for example
   `kinematic_contact_unbound at staging.kinematics`). Fix that field and run again: accepted,
   unchanged passes are reused and any change writes its own revision records. When you change
   something that later passes depend on and leave those passes as they were, the run stops and
   lists them; re-read them in the card, then run again with `--confirm <passes>` (or `all`).

The owner's target is a usable prompt within 4 minutes of receiving the request (LLM time
included). `receipt.json` in the run folder times brief to finished prompt; the run report shows
`end_to_end_since_brief_s`, attempts, calls, missing reasons and characters.

## Scene card

```yaml
ask: "<the user's idea, verbatim>"
model: seedance-2.0
scene_action:                     # who and what, in order, with cause and result
  scene:    {scene_1: {duration_s: 15, location: ..., time_of_day: ..., fixtures: [...]}}
  entities: {ren: {kind: actor, name: Ren, description: ..., start_position: ...}}
  beats:    {beat_1: {order: 1, label: ..., min_s: 1.5, duration_s: 2.0, summary: ...}}   # min_s <= duration_s; lengths add up
  actions:  {act_1: {order: 1, beat: beat_1, actor: ren, target: oni, verb: ..., body_part: ...}}
  interactions: {int_1: {beat: beat_1, action: act_1, kind: contact, contact_surface: ..., reaction: ..., settle: ...}}
performance:                      # per action that needs it; closed fields take a menu term
  act_1: {body: ..., effort_weight: strong, effort_time: sudden, effort_space: direct,
          effort_flow: bound, shape: advancing, connectivity: upper-lower, face: ...}
staging: {blocking: ..., screen_direction: ..., action_axis: ..., hand_uses: ..., kinematic_plan: {...}}
camera:                           # per shot, all twelve fields
  shot_1: {order: 1, beat: beat_1, end_beat: beat_2, shows_initiation: true, framing: ..., angle: ...,
           position: ..., movement: ..., movement_quality: ..., relation: ..., lens: ..., focus: ...,
           composition: ..., time: ..., blur: ..., connection: ...}
light_color: {lighting: ..., color: ..., palette: ..., exposure: ...}
style: {visual_style: ..., motion_style: ..., capture_texture: ..., style_weights: ..., vfx: ...}
audio: {sound: ..., dialogue: ..., music: ...}
synthesis: {end_state: ...}
uses:                             # required for scene-wide passes: the accepted choices each relied on
  staging: [entities.ren, entities.oni, interactions.int_1]
  light_color: [shots.shot_1]
  style: [light_color]            # a pass id cites all of that pass's accepted choices
  audio: [actions.act_1, interactions.int_1]
  synthesis: [audio, shots.shot_1]
why:                              # reasons, keyed by the pass that makes the choice
  "actions.act_1": "why this action"                           # scene items: the card's own key (scene.scene_1, actions.act_1)
  "performance.act_1": "why this movement"                     # later passes: <pass>.<id>, <pass>.<sublayer> or <pass>
  camera: "why this coverage"
# optional
cite: {"actions.act_1": [c_phase_landmarks]}                   # research from the brief
relative: {"actions.act_3": {baseline: {item: act_1, quality: speed}, change: {direction: more, step: much}}}
ask_spans: {"entities.ren": ["Ren is sixteen"]}                # exact phrases of the ask this choice states
skip: {performance: {face: "the faces stay hidden"}}           # reasons for optional slots you leave out
```

How card fields print in the prompt (director layout): each beat prints `SUMMARY` and its shots and
actions; a shot prints `framing` first, then `Angle:`, `Position:`, `Camera:` (movement),
`Camera quality:`, `Relation:`, `Lens:`, `Focus:`, `Composition:`, `Time:`, `Blur:`, `Cut:`
(connection); an action prints `DO n` followed by the actor's name and then `verb` (so write the verb phrase
without the actor: `verb: walks slowly toward Ren`), then `Target:`, `With:` (body_part), `Starts:` (initiation),
`Pace:`, `Result:` (outcome), then `BODY`, `EFFORT`, `SHAPE`, `SPACE`, `FACE`, and its `CONTACT`,
`REACT` and `NOT` rows. Write values that read correctly after their label. Closed movement terms
print the registry's fixed wording (for example `indirect` prints "attention spread across the
room"); check that the wording fits the action before you choose a term. Changing only a `why`, a
citation or `uses` never needs `--confirm`; changing a choice does.

Python fills in decision ids, closed-set hashes, the user-explicit duration and its lock, evidence
spans and not-applicable entries, and wires the references the card names literally (an action's
beat and people, a performance item's action, a shot's beats). It never guesses what a choice
relied on or why: scene-wide passes without `uses` stop the run, and a choice without a `why`
is recorded as "No reason given in the card." and counted in the report. Write each value as a short
visible clause: everything you accept is printed, so the card's length is the prompt's length.

## Length ceiling

Director prompts for Seedance must fit 14,000 characters (owner SD-21; the longest prompt with a good
render was 13,775). Over it the build is refused with the largest blocks named, for example
`PROMPT_OVER_LIMIT: 23311 characters, limit 14000 ... Largest blocks: BEAT 6 · DO 8 1802; ...`.
Tighten those choices' wording in the card and run again. Only if the owner asks for a longer prompt,
set `prompt_char_limit: <n>` at the top of the card; it is recorded as requested.

## Under the hood

The runner calls these operations; use them directly only to debug. Every call is JSON on stdin and
JSON back: `echo '<json>' | ./bin/cpcs <operation> --role operator`.

| Step | Operation | Arguments |
|---|---|---|
| 1. Start | `direct.start` | `{"text": "<the user's idea, verbatim>", "mode": "complete", "model": "seedance-2.0"}` |
| 2. Read a pass | `direct.packet.read` | `{"session_id": "...", "pass_id": "<pass>"}` |
| 3. Submit a pass | `direct.proposal.submit` | `{"session_id": "...", "pass_id": "<pass>", "packet_hash": "<from the packet>", "proposal": {...}}` |
| 4. Check progress | `direct.state.read` | `{"session_id": "..."}` |
| 5. Build | `direct.finish` | `{"session_id": "...", "build_settings": {"project_id": "cpcs-local-export", "duration_seconds": 15, "prompt_format": "prose", "prompt_layout": "director_v1"}}` |

Passes run in this order: `scene_action`, `performance`, `staging`, `camera`, `light_color`,
`style`, `audio`, `synthesis`. Each rejection names its `decision_id`. Never weaken the scene to
get past a check. `--telemetry work/<file>.jsonl` on any `./bin/cpcs` call records its duration.

## Worked examples in this repository

| Need | File |
|---|---|
| A complete `scene_action` proposal | `handoff/direct_scene/reference/jail_fight_proposal.json` |
| Stacks for every later pass | `stacks()` in `lab/application/tests/test_directing_pipeline.py` |
| Kinematic plans that pass | `lab/compiler/tests/fixtures/jail_fight_plan.json`, `water_duel_v3_plan.json` |
| A kinematic plan that fails, with the reasons | `lab/compiler/tests/fixtures/water_duel_v2_plan.json` |

Check a plan before you submit it (read-only, no session needed):

```bash
echo '{"plan": {...}}' | ./bin/cpcs kinematics.validate --role chat
```

## What the compiler enforces

- **Scene and action.** One scene has one duration and one location. Every beat carries
  `duration_s`, and the beat lengths add up to the scene length exactly. Entities are
  `kind: "actor"` or `kind: "object"`. A contact needs a surface, a reaction and a settle.
- **Evidence.** `user_explicit` needs an exact span of the ask (`start`, `end`, `text`).
  `sourced_research` needs a packet concept whose source passages resolved. Anything you invent is
  `creative_application`.
- **Inputs.** A decision may name only decisions listed in that packet's `upstream` or earlier in
  the same proposal.
- **Movement quality.** Effort (weight, time, space, flow), Shape and Bartenieff connectivity are
  chosen from the packet's `fixed_sets`. Copy the member's `selection` object exactly; free wording
  in those slots is rejected. Body, space, face and affect stay free text.
- **Kinematic plan (staging, always required).** Metres, y up, +x screen-right. Give each body's
  standing hip height, hip tracks for the whole scene, support for every moment, facing, relations,
  contacts and camera keyframes (`pos`, `look_at`, `must_see`). Bodies must be declared entities and
  the plan's duration must equal the scene's. Bind it to the scene: every acting person is a plan body or listed in `untracked` with a reason (a hand-only cutaway, an off-screen voice); each body-to-body contact names its scene contact in `interaction`; a camera keyframe may name its `shot`. Findings come back as `kinematic_<code>`: teleports,
  speed jumps without a force event, unsupported bodies, bad landings, a mis-aimed camera. A `skid`
  needs crouched hips; `notes` is a list of strings.
- **Camera.** Every shot needs all twelve sublayers. `framing` also carries `order`, `beat`,
  `end_beat` and either `shows_initiation: true` or an `occlusion_reason`.
- **Revisions.** Revise with a new decision that names `revision_of`, and resubmit that pass's whole
  stack. Later passes are marked for recheck.

## What to hand back

1. The full prompt text.
2. The `session_id`, the score id and every rejection code you repaired.
3. Anything the build reported as unsupported or lost (`loss_report.json`, `provider_fit`).

## The layout to ask for

Always build with `"prompt_layout": "director_v1"`. It prints labelled blocks in a director's
order: `GOAL`, `STYLE`, `LOOK`, `CAST`, `OBJECTS`, `WORLD`, `STAGING`, `MOTION` (the validated plan
as words), then each `BEAT` with its length, its `SHOT` and each action as `DO`, `BODY`, `EFFORT`,
`SHAPE`, `SPACE`, `FACE`, `CONTACT`, `REACT`, `NOT`, then `END`, `SOUND` and the profile `CONTROLS`.
The ask is not repeated, coordinates never print, and no accepted field is dropped.

Without that setting the build uses the older default prose: one alphabetical line per item, the
whole ask printed first, and beats as labels with no seconds. It is kept for compatibility.

## Known limits (2026-10-04)

- The prompt is as long as what you accepted. Twelve camera sublayers per shot and a full movement
  stack per action add up: a seven-shot scene came to about 24,000 characters. Write tight values,
  and give a full movement stack only to the actions that need one.
- The closed movement codes print their admitted wording, which is long. That wording is the
  registry's, not yours to shorten.
- A short form (the planned compact projection) is not built. If the user asks for a shorter
  labelled version, write it from the accepted decisions and say plainly that the compiler did not
  emit that text.
- Cutaways to other places have no field of their own; describe them in the scene and shots.
- `prompt_layout: "labelled_skeleton_v1"` is a different thing: it reproduces owner-authored
  labelled wording and refuses a scene that does not carry it.

## Boundaries

No render, provider or paid calls: the compiler only writes prompt text. `work/` is local scratch
and is ignored by Git. Do not commit or push unless the owner asks; then follow root `AGENTS.md`.
