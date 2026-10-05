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
| 5. Build | `direct.finish` | `{"session_id": "...", "build_settings": {"project_id": "cpcs-local-export", "duration_seconds": 15, "prompt_format": "prose"}}` |

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
  the plan's duration must equal the scene's. Findings come back as `kinematic_<code>`: teleports,
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

## Known limits of the prose output (2026-10-04)

- It is long: every accepted field prints, in alphabetical order inside each item, and the full
  ask prints as `User intent`. A seven-shot scene came to about 25,000 characters.
- Beats print their label only. Seconds per beat are recorded in `capability_report.json`
  (`timing_projection`) but are not printed for Seedance prose.
- `prompt_layout: "labelled_skeleton_v1"` works only for scenes whose beats carry bound roles; a
  new scene is refused with `BOUND_REFERENCE`.
- Cutaways to other places have no field of their own; describe them in the scene and shots.

Tell the user these limits when you hand over a compiled prompt. If they ask for a shorter
labelled version, write it from the accepted decisions and say plainly that the compiler did not
emit that text.

## Boundaries

No render, provider or paid calls: the compiler only writes prompt text. `work/` is local scratch
and is ignored by Git. Do not commit or push unless the owner asks; then follow root `AGENTS.md`.
