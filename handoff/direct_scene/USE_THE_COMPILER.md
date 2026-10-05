# Use the compiler to write a video prompt

Read this when someone asks for a video prompt. Root `AGENTS.md` wins on conflict.

**Do not compose the prompt from `lab/blocks.yaml` or by hand.** The LLM (you) makes the creative
decisions; Python validates them and builds the prompt. A prompt written outside this flow has no
validated motion plan, no closed movement selections and no score.

## Setup, once per session

```bash
git pull
python3 -m pip install -r requirements.lock    # first time only; Python 3.9 or newer
echo '{}' | ./bin/cpcs doctor --role operator  # must report "status": "success"
```

Start a new session after every `git pull`; a session opened before an update may be refused.

## The flow

Every call is JSON on stdin and JSON back:

```bash
echo '<json>' | ./bin/cpcs <operation> --role operator
```

| Step | Operation | Arguments |
|---|---|---|
| 1. Start | `direct.start` | `{"text": "<the user's idea, verbatim>", "mode": "complete", "model": "seedance-2.0"}` |
| 2. Read a pass | `direct.packet.read` | `{"session_id": "...", "pass_id": "<pass>"}` |
| 3. Submit a pass | `direct.proposal.submit` | `{"session_id": "...", "pass_id": "<pass>", "packet_hash": "<from the packet>", "proposal": {...}}` |
| 4. Check progress | `direct.state.read` | `{"session_id": "..."}` |
| 5. Build | `direct.finish` | `{"session_id": "...", "build_settings": {"project_id": "cpcs-local-export", "duration_seconds": 15, "prompt_format": "prose", "prompt_layout": "director_v1"}}` |

Passes, in this order: `scene_action`, `performance`, `staging`, `camera`, `light_color`, `style`,
`audio`, `synthesis`. Each packet gives the sublayers to fill, the research you may cite, the
fixed-set menus, the earlier decisions you may name as inputs (`upstream`) and the response
contract. The finished prompt is `result.build.artifacts["prompt.txt"].content`.

When a submit returns `"disposition": "rejected"`, read every rejection code, repair exactly those
points and submit again. Never weaken the scene to get past a check.

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
