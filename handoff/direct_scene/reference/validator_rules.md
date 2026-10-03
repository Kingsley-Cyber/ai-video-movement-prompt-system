# Validator rules worth porting

Source: the checker written in the other repository (`director/tools/dircheck.py`, 79 passing
tests there). These are rules, not code to copy: that checker reads its own plan format. Port a
rule only in the slice that gives it a consumer, into `lab/compiler/decisions.py`, with a failing
test first. Wording of each failure is given so the meaning is unambiguous; choose codes that fit
this repository.

## Slice 1 (scene and action)

| Rule | Fails when | Original message |
|---|---|---|
| References close | an action names an actor, target or beat that does not exist | "unknown beat", "unknown anchor" |
| Cause before effect | a reaction is ordered before its cause | "cannot precede its cause", "stages out of causal order" |
| Beats fit the clip | the sum of minimum readable seconds exceeds the clip | "OVERLOADED" with options: cut, overlap non-causal beats, split, lengthen. Never squeeze. |
| Fit verdicts | ratio of load to clip length | FITS ≤ 0.85, TIGHT ≤ 1.0, OVERLOADED above (conventions, not measured) |
| Anchor is earlier | a comparison names an anchor on the same or a later beat | "anchor is not earlier" |

## Slice 2 (stacks and coupling)

| Rule | Fails when | Original message |
|---|---|---|
| Camera grammar is mandatory | no camera movement decision, or no framing or optics decision | "explicit camera grammar is mandatory" |
| One camera move per shot | two moves with no beat scope | "one camera move per shot" |
| Known camera move | a move is neither in the catalog nor a custom move with a decision record | "unknown camera move" |
| Optics are not motion | a lens change is worded as the camera body moving | "optics written as camera motion" |
| Camera shows confirmed contact | the camera is told to look away from a contact that must be seen | "camera hides a confirmed contact" |
| Camera does not show hidden contact | a close-up is put on a contact that is meant to be occluded | "camera shows a hidden contact" |
| Order first, texture second | a style or render decision reorders or removes a beat | "order first, texture second" |
| One owner per field | two passes write the same field | "one owner per field" |
| Constant motion | no beat declares how its motion is spaced | warning: "constant motion" |

New in this repository (not in the old checker): a camera stack must keep the initiation of the
action it frames visible, unless the decision carries a stated creative reason; a beat's spacing
and its movement-quality values must not disagree for the same phase of an action.

## Slice 3 (cause, contact, relative)

| Rule | Fails when | Original message |
|---|---|---|
| One causal event per beat | two contact events share a beat | "one causal event per beat" |
| Edge admission | a contact has no surface, no reaction or no settle | "edge admission … no effect without a named cause, contact and settle" |
| Explicit trigger | a contact does not name who and which body part | "explicit: trigger needs actor and part" |
| No magic jump | an object changes state with no prior contact and transfer | "magic jump" |
| Connected state chain | a stage starts in a state the previous stage did not end in | "disconnected state chain" |
| Anticipation exists | an action has no preparation before contact | "no anticipation stage" |
| Aftermath exists | an action ends at contact with nothing after | "no aftermath stage" |
| Hands are not double-used | a hand that holds something else is used for a task | "needs N hand(s), lists M distinct hand(s)", "listed twice", "holds the camera" |
| Beat covers its stages | a beat is shorter than its stages need | "beat does not cover its pathway stages" |
| Same quality | a comparison's quality differs from its anchor's | "quality mismatch" |
| One escalation per quality | two comparisons for one quality on one item | "one escalation per quality" |
| Force needs a baseline | a contact's force is compared with nothing of weight or intensity | "force anchor" |
| Events depend forward | an event depends on a later one | "depends_on … not earlier" |

Wording lint (warnings, never failures): a bare magnitude word with no comparison in the
sentence ("fast", "heavy", "hard", "big"); a vague style word ("cinematic", "epic", "dynamic").
Named techniques are allowed ("slow motion", "wide shot", "hard cut"). Treat these as
phase-specific guidance, not blanket bans.

## Conventions the old checker used (unmeasured)

- Minimum readable seconds: about 0.8 for a reach or a settle, 1.0 for one bounded motion,
  0.2 per stage inside a beat.
- Speech: words ÷ 130 per minute for quiet delivery (research gives 150–190 conversational),
  plus a breath and a turn gap.
- None of these has a render behind it. Label them as conventions wherever they are used.

## What the old output got wrong (do not reproduce)

1. An anchor sentence was emitted before the event on the same beat: a result before its cause.
2. A beat, its anchor, its event and a movement-quality sentence restated one action.
3. A universal 2,000-character budget dropped real content. Limits belong to a provider.
4. Bookkeeping lived beside content. Here it stays in the session ledger.
