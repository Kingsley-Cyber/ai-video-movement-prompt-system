# Timing and kinematics: tracked carriers and validated coordinates

**Standing:** design for two owner requests (2026-10-04), written by Claude. The owner approved the
frame convention and the three closed lists below and authorized T1 and T2 on 2026-10-04 (standing
decisions SD-15 to SD-17). Implementation status lives in `ARCHITECTURE.md` (REQ-077), not here.
1. Timing is a carrier choice, but it must be tracked so scenes can be calibrated.
2. Coordinates helped when paired with the prompt; their logic must be validated so failures like
   the water-duel landing can't ship.

**Evidence:** the water-duel prompt v2 (`/Applications/CPCS_AB_coordinates/A_absolute_coordinates.md`)
was checked by a 100-line script. It found eight classes of coordinate defects that explain the bad
fall. The repaired v3 (`E_v3_validated_kinematics.md`) passes the same checks. The scripts and both
reports are in `/Applications/CPCS_AB_coordinates/scratchpad/`.

---

## Part T: timing as a tracked carrier choice

**Principle:**
- The clock is canonical data.
- How a prompt prints it is a carrier choice.
- What a model actually did with it is evidence.

Keep the three separate and record all three, so beat lengths can be calibrated per model.

| Layer | Holds | Owner | Status |
|---|---|---|---|
| T1 Canonical clock | beat `duration_s`, plus derived `start_s` and `end_s` when every beat has a length and the lengths sum to the scene duration; `min_s` stays a floor | compiler (`decisions.py`, score) | **authorized** (PLAN Slice C), next slice |
| T2 Timing form per build | which form the carrier printed (`timestamps`, `lengths`, `shot_numbers`, `none`), per beat, plus the model and carrier; recorded in the build audit and loss report as `carrier_choice` with `provider_adherence_claim: false` | compiler (`build.py`, `skeleton.py` already records it for the skeleton) | **authorized**; extends the existing record to every carrier |
| T3 Observed timing per render | event times seen in the render ("kick lands at 4.1 s", "skid stops at 4.6 s"), from your scorecard or later from motion-energy spikes; unobserved stays unknown | recorder (`record.py`) and verifier | needs a scorecard field; no provider call |
| T4 Adherence estimate | per (model × carrier × timing form × beat role): observed ÷ planned length, onset error, drift across the clip | derived tier (`reflect.py`, indexes) | **parked** until scored renders exist |
| T5 Calibrated compile | optional compensation, e.g. "on Seedance mini, impact beats render 1.3× long; author 0.77×", applied only after owner review | compiler | **parked**; needs T4 evidence and your approval |

**Data shape for T3 (one row per observed event):**
`{render_id, event_ref: "c04.touchdown_skid", planned_s: 3.4, observed_s: 3.7 | null, source: owner|verifier, note}`

**What it unlocks:**
- "Seedance mini stretches impacts" becomes a measured number per beat role, not a feeling.
- Beat lengths are then tuned from evidence, and a fast-fight tempo can compensate for a model that
  slows hits down.

---

## Part K: kinematic layer (coordinates the LLM writes, Python checks)

**Principle:**
- The LLM authors coordinates creatively in a working scratchpad.
- Python validates their logic.
- An LLM critic judges what Python can't: does this landing look right?
- Natural language carries the meaning; the numbers support it.

The coordinates are never trusted because they look precise. The v2 water duel looked precise and
was physically impossible in eight ways.

### K1. Authoring contract (what the LLM writes in the scratchpad)

| Block | Content | Why |
|---|---|---|
| Frame | units (m), up axis, water/ground plane, **screen-right axis**, camera convention (position + `look_at`, not bare yaw) | v2 never declared its yaw convention; its camera looked away from the fight |
| Body baseline per character | hip height, stance width, leg length, max run speed, jump height, mass class; Laban baseline → kinematic signature (sudden = high acceleration, sustained = low; bound = short follow-through, free = long); Bartenieff lead (hips move before limbs) | Gives every number a body to be checked against |
| Tracks | hips (root) required; hands and feet optional; keyframes with time | |
| Support intervals | what carries the weight in each interval (`both_feet`, `held_by_<actor>`, `both_hands_plant`, `flight:<reason>`, `both_feet_skid+left_hand_trailing`…) | v2's skid had no declared support, so the model guessed |
| Force events | catch, swing drive, release, touchdown, push-off, landing, impact | Every speed change must cite one |
| Contacts | who, which part, on what, interval, mode (`physical_contact`, `near_miss`, `release`, `staged_near_contact`, `occluded`) | Polymath's diagnosis: contact-mode ambiguity at the release and skid |
| Camera | position, `look_at`, required subjects per keyframe | Aim check |

### K2. Validator (Python, deterministic): proven on the water duel

| Check | Rule | v2 finding |
|---|---|---|
| `TELEPORT` | no two keyframes at the same time in different places | hips jump **1.82 m in zero time** at the release (3.2 s) |
| `SPEED_JUMP` | a speed change over 2.5× needs a declared force event within ±1 frame | eight unexplained jumps, e.g. 1.2 → 5.4 m/s at the release |
| `GRIP_BROKEN` | during a hard grip, holder's hands within reach of the held part (limb length + slack) | hands **1.3–1.9 m** from the held hips for half the swing |
| `SWING_EXTENT` | turn measured from the track must match the words, the hands track and the camera | hips circle **360°, then jump another 178°**; hands and camera describe half a turn |
| `RELEASE` | released body leaves along the swing's tangent at about the swing's speed (0.6–1.4×) | swing slows to 1.2 m/s, skid starts at 5.4 m/s, heading **119° off** the tangent |
| `UNDECLARED_FLIGHT` / `CONSTRAINT_CONTRADICTION` | airborne frames only inside declared flight intervals; constraints can't forbid what the plan requires | plan has a kick and a backflip, yet the hard constraint said **zero flight frames** |
| `SUPPORT_UNDECLARED` | every interval names what carries the weight | skid: hips at water level, no feet/back/side declared |
| `CAMERA_AIM` | required subjects within 30° of the view axis | camera points **90–167° away** from the fighters from 2.4 s on |
| `DENSITY` | planned moves fit the clip at the tempo profile's density | **47 moves** listed for an 8 s clip; only 11 had tracks |

Also checked: speed only decreases during a declared drag interval (skid), and time order.

Built under policy 1.1 (2026-10-04): facing headings with marked spins and turn rate, relations
(toward, away_from, travel forward/backward/sideways), and landings that declare their parts, match
the next support, land low and land at a plausible speed. Kinematics is always on (SD-18).

Planned additional checks:
- landing velocity consistent with gravity (fall height → impact speed);
- hip–shoulder coupling (hips and shoulders turn together);
- joint-range proxies from optional limb tracks;
- reach for every contact.

### K3. LLM critic (semantic): what Python can't judge

**Owner decision 2026-10-04:** no free-form critic. The loop is deterministic: the author LLM
repairs against typed validator rejections in the directing session. Judgments Python can't make
yet become declared fields with new checks (facing, landing part, turn rate) or the owner's render
score, not an LLM opinion. The questions below remain the list of declarations to add.

The critic reads the NL, the numbers and the validator report, then answers fixed questions per
event:
- What touches the surface at this landing?
- Which way is the body facing?
- Does the pose sequence read as one motion?
- Is this anatomically plausible for this character's baseline?
- Does the camera show the must-see moment?

It proposes repairs as edited keyframes or wording. **It cannot override a hard validator finding.**

### K4. Repair loop (the scratchpad)

1. Author in the scratchpad.
2. Run the validator.
3. Run the critic.
4. Repair.
5. Repeat at most 3 rounds (owner rule).
6. Compile.

This is exactly how v3 was made:
- **First pass:** the validator caught my own errors: a 9.4 m/s release whose skid ran into the
  backflip keyframes, and a swing start with no declared force.
- **Second pass:** adjusted swing acceleration, drag and relative keyframes; no findings.
- **Camera:** the aim check caught a deliberate tracking shot, so required subjects are now
  declared per keyframe.

### K5. Projection: words lead, numbers support

- The NL section carries the physical reasoning: support, force, direction, deceleration, landing
  pose, initiation order.
- Validated numbers follow as a supporting block.
- If a model ignores numbers, the NL still carries everything, and the numbers still did their
  job: they validated the plan.
- Whether printing numbers helps is a render question (the A/B arms below).

### K6. A/B against reference prompts

**Existing card:** `CPCS_AB_coordinates/TEST_CARD.md`. Arms:
- **A** absolute coordinates;
- **B** none;
- **C** relative words;
- **D** relative numbers;
- **new: E** `E_v3_validated_kinematics.md` (validated coordinates + NL lead, 10,776 characters, inside
  Veo's 12,000).

Rules:
- Same model, route and settings; two seeds each.
- Score blind with the card's 10 checks, plus three for the failure: **release follows the swing**,
  **landing shows what touches the water**, **skid slows steadily**.
- Reference good prompts (champion v3, the flow fight, the original water duel's good render) are
  the quality baseline every arm is judged against.
- The card's warning still holds: confirm which text produced the original good render (the
  7,139-character API prompt or the synchronized document).

---

## How it lands in the repository (existing owners only)

| Piece | Owner | Notes |
|---|---|---|
| Frame, tracks, support, force events, contacts | score scene objects (`actions`, `interactions`, new `tracks` under the existing scene collections) | schema extension with merge policy; one canonical authority |
| Validator | `lab/compiler/decisions.py` (proposal and build checks), the same place as the prop/hand ledger | deterministic; returns typed rejection codes |
| Critic | external LLM through the directing session (a `kinematics` sublayer in performance or staging), with the validator report in the packet | no second workflow |
| Timing record T2 | `build.py` audit and loss report | every carrier |
| Observed timing T3 | `record.py` render records | owner scorecard field |
| Estimates T4–T5 | derived tier | parked |

## Implementation order

| Slice | Content | Authorization |
|---|---|---|
| 1 | T1 canonical clock (derived start/end) + T2 timing form on every carrier | authorized (PLAN Slice C/D) |
| 2 | K1 contract + K2 validator for authored tracks, opt-in, with the water-duel v2 as a failing fixture and v3 as a passing one | your request on 2026-10-04 |
| 3 | K3 critic questions in the directing packet + K4 repair rounds | after 2 |
| 4 | T3 observed timing in render records | needs your scorecard format |
| 5 | T4–T5 adherence and calibration | parked until scored renders |

## Owner-approved conventions (2026-10-04)

These are project conventions, written out exactly from the approved K1 draft. They enter the
registry through the governed admission path when the K slice needs them; until then they bind
authoring and the validator design.

| List | Members |
|---|---|
| Frame | metres; y up; the support surface is y = 0; +x is screen-right for a camera facing +z; cameras are given as position plus `look_at`, never as a bare yaw |
| Support parts (what carries the weight) | `both_feet`, `left_foot`, `right_foot`, `both_hands`, `left_hand`, `right_hand`, `knee`, `seat`, `back`, `side`, `held_by:<entity>`; or `flight:<reason>`, valid only between a declared takeoff and landing. Combinations join with `+` (for example `both_feet+left_hand`) |
| Support manner | `static`, `step`, `skid`, `plant`, `crouch`, `trailing:<part>` |
| Contact modes | `physical_contact`, `near_miss`, `release`, `staged_near_contact`, `occluded` |
| Force events | `catch`, `swing_drive`, `release`, `touchdown`, `push_off`, `landing`, `impact` |

## Remaining owner decisions

1. **Coordinates in printed prompts:** decided per model by the A/B result; until then they print
   for Veo-length routes and stay validation-only for short budgets.
2. **Render E against A and B** (two seeds each) so the fix is proven, not just plausible.
3. **T3 scorecard format:** how observed event times are written down.
