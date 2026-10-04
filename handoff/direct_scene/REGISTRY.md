# The registry of fixed sets

Owner's rule (2026-10-03): **fixed sets are constraints, not free text.** Where a concept is a
closed system, the LLM selects a listed code. It does not write its own vocabulary.

This file is a specification and a standing report. It admits nothing. The owner's draft
registry is in `reference/owner_registry_draft.txt`; Codex's inventories are in its vocabulary
report outside this repository. Admission goes through the existing governed intake and the
owner's review.
`PLAN.md` governs admission and scope. Candidate records and schema-accepted tokens do not alone
establish curated membership, operational admission or tested model behavior.

## Principles

1. **Boundary preservation.** Each closed system describes a different thing and keeps its own
   vocabulary. FACS is visible facial action, not emotion. Laban is movement quality. Camera is
   viewpoint. There is no shared numeric scale across systems.
2. **Versioned authority.** Where an external standard fixes the values (a FACS edition, Laban
   convention), the set names that standard and version and is stored by group, never as one
   flat list.
3. **Selection only.** A slot bound to a set accepts only a listed code. When nothing fits, the
   result is a recorded registry gap for the owner. It is never a custom value.
4. **Kept as they are:** the relative sets (step, direction) and the evidence set (source
   status) already enforced in `directing_session_contract.schema.json`.

## Entry format

Six fields, as the owner wrote them:

| Field | Meaning |
|---|---|
| `code` | stable identifier, grouped (`effort.weight.strong`) |
| `term` | the name in its own system |
| `visible_wording` | what a prompt prints: something a viewer could see |
| `pairs_and_conflicts` | what it excludes, what it combines with, what it hides or needs |
| `model_support` | per model and route, filled **only** from render records; `untested` until then |
| `evidence_status` | admitted source/outcome standing; confidence and source class remain distinct |

Every direction in `visible_wording` states its frame: body, world or camera.

## Where it lives

In the owners this repository already has: the ontology registry
(`lab/second_brain/curated/ontology_registry.json`), coverage manifests, concept cards and source
units, with derived local indexes. Not a new dictionary and not a file under `handoff/`. A pass
slot in `lab/second_brain/directing_passes.yaml` names the set it draws from.

## Standing

"Enforced" = checked by code at HEAD `3c7b0d9`. "Owner draft" = in the pasted registry draft.
"Codex" = in Codex's vocabulary report. Nothing has render evidence.

| Group | Set | Values | Standing |
|---|---|---|---|
| Laban Effort | factors | weight strong/light · time sudden/sustained · space direct/indirect · flow bound/free | Owner draft and Codex agree. Four free-text slots exist |
| | basic actions | punch, slash, dab, flick, press, wring, glide, float | Both list eight; recipes disagree (flag 1) |
| Laban Shape | qualities | spreading/enclosing · rising/sinking · advancing/retreating | Candidate facet; flag 3 concerns the reference frame |
| | modes | shape flow, directional, carving; spoke-like and arc-like are Directional subtypes | Preserve the hierarchy; definitions require source closure |
| | phrasing emphasis | beginning, middle, end | Owner draft only |
| Laban Space | level, reach | low/mid/high · near/mid/far | Both; unverified enumeration |
| | planes, kinesphere | — | Open (flag 6) |
| Bartenieff | connectivity | breath, core-distal, head-tail, upper-lower, body-half, cross-lateral | Both; owner draft says "needs confirmation". One free-text slot exists |
| FACS | action units, by group | upper face, lower face, descriptors, head, eye, visibility; entry-specific modifiers/intensity/timing | Recovered candidates: upper face 9 for the declared facet, lower face 15 partial. Not an admitted complete FACS registry; editions remain distinct |
| Camera | scale | ECU, CU, MCU, MS, MWS, WS, EWS | Owner draft (7); Codex had 3 |
| | angle, vertical | eye level, low, high, overhead, worm's-eye | Owner draft |
| | angle, roll | dutch | Owner draft |
| | angle, horizontal | front-facing, profile | Codex only; missing from the owner draft |
| | movement | static, pan, tilt, push in, pull out, track, crane, orbit, whip pan | Owner draft (flag 4) |
| | support, implied feel | — | Rig/support and motion texture are different facets; define both rather than force one combined list |
| | height | relative to a declared subject/body/world anchor | Contextual parameter, not a missing universal enum |
| | lens, focus | wide/normal/telephoto, zoom · subject/deep/shallow/rack | Codex only |
| | reframing | — | Missing |
| | shot role | setup, insert, over the shoulder… | Proposed project vocabulary; no definitions |
| Contact | state | confirmed, near, occluded, shown by cut, none | Owner draft (flag 5) |
| | prop transitions | prior state, cause, result, new piece names | Proposed; no definitions |
| Action | phases | preparation, execution, contact or apex, follow-through, recovery | A profile default in the repository; not enforced on decisions |
| Mechanics | support, cause, material response, recovery | scene-specific relationships and source-backed mechanisms | No complete physics list or gravity default is required |
| Relative | step, direction | slightly/more/much · more/less | **Enforced. Kept.** |
| Evidence | source status | user explicit, sourced research, creative application, inference, model tested | Keep the schema contract; proposal admission rejects model_tested. A render claim needs separate evidence |

## Flags on the owner's draft

Resolve each flag affecting the facet being admitted; an unrelated flag does not block another
source-complete facet. Do not promote entries without their required review.

1. **Basic action recipes add a Flow pole** (punch written as "sudden, direct, strong, bound").
   The usual definition of the eight actions uses weight, time and space only, and Codex's report
   says flow is not fixed by the action. The draft itself says the recipes need checking.
2. **"Pittak ↔ Rembel"** as an intensity scale. This term could not be placed. Unverified.
3. **"Advancing: reaching toward the viewer/front."** Shape is relative to the body, not the
   camera. State the frame.
4. **The movement list mixes categories.** Handheld is a support; zoom is a lens change. Each
   belongs in its own set, or a zoom gets written as camera travel.
5. **Contact states differ from the research package in this repository**, which has
   confirmed, near, occluded, editorial impact, unknown. The draft has "shown by cut" and "none".
   "None" and "unknown" are different claims; presentation and evidence state are different axes.
6. **Space planes** are named differently across sources. Do not fix them yet.
7. **"Map emotion to FACS AUs"** in the draft's compile notes contradicts its own first
   principle. A face decision is a visible action chosen for a beat, not an emotion lookup.
8. **"Physics: missing → default to gravity"** in the same notes is a silent default. A missing
   set is a gap to report, not a value to assume.

## Admission order (proposed)

1. Effort factors (complete; sourced in the research package already in this repository).
2. Shape qualities.
3. Contact state, after flag 5.
4. FACS upper face (the facet Codex already recovered).
5. Bartenieff connectivity, after its source is confirmed.
6. Camera project vocabulary: scale, vertical/horizontal angle, roll, movement, rig/support,
   texture, lens and focus, with definitions and compatible component parameters after flag 4.
7. Space level and reach.
8. Required project-defined reframing/shot-role/prop-operation facets and contextual mechanics/
   height parameters; do not invent a closed physics or global height taxonomy.

Each step: register the source, extract candidates, review, promote (owner), then bind the slot.
This list is a preparation proposal. PLAN.md selects the source-complete facet needed by the
current acceptance case; neither this ordering nor admission of every group is a global prerequisite.
