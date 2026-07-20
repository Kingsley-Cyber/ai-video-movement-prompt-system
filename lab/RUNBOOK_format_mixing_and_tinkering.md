# RUNBOOK — format mixing (the compiler) & tinkering (the adjustment map)

**Triggers:** "mix yaml and xml", "combine the formats", "which formats for this request", "the
timing feels off", "the punch lands late", "pacing is wrong", "make it hit harder", "tweak it".

Two skills in one: (A) **curate & merge** the right format combination for the user's intent;
(B) **tinker** — when the user is unhappy with math/timing/feel, know exactly which field to turn.

---

## PART A — The mixing compiler

### A.1 Curate by intent (which formats to produce)

Read the request for WHO will edit it and WHICH layers it touches, then pick:

| User intent signal | Package | Why |
|---|---|---|
| "exact choreography / fight / motion" | **JSON only** | pure motion = canonical truth (v005 precedent) |
| "I want to tweak style/feel myself" | **YAML → JSON** | human-editable intent resolving into numbers |
| "beat order, script, SFX/VFX cues matter" | **XML + JSON** | ordered script + triggers, numbers by hash-ref (RDC §31) |
| "style + script, no solver numbers yet" | **YAML + XML** | semantic-first draft; numbers land in JSON later |
| "full production" | **YAML + JSON + XML** | director → solver → envelope (FORMAT_CONTROL_MAP flow) |
| "give me options / A-B it" | **format spread + NL** | same content per format = output variance (p009) |
| any request, always | + **NL as ONE labeled variant** | format discipline law — never NL-only, never NL-silently-dropped |

If the user *names* formats ("YAML and XML"), honor it — assign each control to the format that owns
it (`FORMAT_CONTROL_MAP.md`), never duplicate a control into both.

### A.2 Merge laws (what makes a mixed package a real compile, not a paste-up)

1. **One authority per quantity** (MX §3.3). A number lives in exactly ONE format. XML never
   restates JSON values — it references them: `<cpcs:score href="…json" sha256="…"/>`.
2. **YAML resolves DOWN into JSON.** `extends:`/profiles/overrides are authoring input; the compiler
   materializes them into the canonical JSON. YAML never carries dense arrays.
3. **XML owns order + triggers only.** Beats in sequence, `perf:/vfx:/audio:/cam:` events at times.
   If an XML trigger time conflicts with a JSON contact frame, **JSON wins** (canonical-json
   priority) and the mismatch is REPORTED, not silently averaged (CPCS §19.12 conflict reports).
4. **Resolution order** (CPCS §19.10 / MX §26): profile default < scope (production→shot→beat→event)
   < local override < **human lock**. Locks carry tolerances and survive every merge.
5. **Typed merges only** (CPCS §19.11): scalars replace; timelines merge by stable event ID then
   sort; curves replace/scale/offset/blend ONLY when the operation is explicit. An LLM must not
   improvise merge behavior.
6. **Two-document rule:** semantic intent (YAML/XML) and kinematic truth (JSON) share ONE clock
   (`timebase` + `retime_map`) — check every mixed package for clock agreement before delivering.
7. **Deliverable transparency:** state which formats were produced, which controls live where, and
   which format is authoritative for what.

### A.3 Combo recipes (copy these shapes)

- **YAML+JSON** — YAML head: intent, style `extends:`, laban words, acceptance; JSON body: tracks,
  contacts, camera. Paste order: YAML first (context), JSON second (truth). House compact form:
  `assets/clip.iphone12_rawugc.yaml_json.txt`.
- **XML+JSON** — XML envelope with ordered `<act:beat>` prose + triggers, `<cpcs:score href>` to the
  JSON; JSON unchanged. Use when trigger timing and script order are the user's focus.
- **YAML+XML** — YAML: style/intent/constraints; XML: ordered beats + event marks with *approximate*
  times flagged `authority="proposed"`; promote times to JSON when solved.
- **Tri (YAML+JSON+XML)** — the full production flow; compiler merges to one resolved canonical
  JSON; the three sources stay editable by their owners (director/solver/editor).
- **Quad (+NL)** — everything above + one NL paragraph labeled `variant: natural_language` for the
  A/B spread.

---

## PART B — The tinkering map (symptom → field → format)

When the user says "the math/timing is off," do NOT regenerate blind. Locate the symptom, turn the
one field that owns it, keep everything else fixed (one-lever discipline), re-render.

| User says | Adjust | Where (format) |
|---|---|---|
| "hit lands late/early" | `contacts[].start_f` + the contact-frame joint key; check `retime_map` isn't shifting presentation | JSON |
| "reaction feels slow/fake" | `reaction_delay_f` (2–4f is human; >6f reads sluggish) | JSON |
| "pacing drags" | `timing_transform.execution_scale` ↓ (0.65→0.55), trim `apex_hold`, tempo/BPM curve ↑ | YAML style → JSON |
| "too fast to read" | `key_pose_hold_frames` +1, `anticipation_expansion` ↑, add impact frame | YAML style → JSON/XML |
| "punch feels weak" | anticipation frames ↑ (bigger windup), `impact_hold_frames` ≥1, `reaction_impulse_scale` ↑, camera `shake.amp_px` ↑, audio `db_boost` ↑, Laban `weight` ↑ | JSON + XML triggers |
| "floaty / weightless" | `gravity_scale` → 1.0, `hang_frames` ↓, verify `support` intervals, Laban `weight` ↑, add impulse event | JSON |
| "aerial too short / flat" | `gravity_scale_by_phase.aerial` ↓, `arc_height_scale` ↑, `hang_frames` ↑ | YAML superhuman → JSON |
| "movement is robotic" | correlated `microvariation` (amplitude+seed), local-phase lag (`offset_from: pelvis`), breath track — NEVER white noise | JSON (+YAML mannerism) |
| "feet are sliding" | fix the EARLIEST causal layer: root velocity vs `support` schedule mismatch → root scale, then contact intervals, then IK (MX recipe 6) | JSON |
| "character morphs mid-motion" | `identity_lock` ↑, reference image, densify the failing track (keyed→dense) | JSON spine |
| "camera is confusing / axis flips" | `screen_direction_lock`, separate camera vs object motion, reduce cut count | JSON camera + XML cam: |
| "beats happen in wrong order" | `temporal_relations` in the action graph; XML script order is the ordering authority | XML + JSON events |
| "anime style isn't landing" | **style ablation** — one dimension at a time (smear / holds / arc / silhouette) until the look appears (MX §28.9) | YAML style_transform |
| "impact doesn't POP" | stack the impact recipe: 1-frame hold + flash trigger + shake(amp/freq/decay) + audio transient at contact ±2f | XML triggers + JSON |
| "strike looks flaily not powered" | enforce `local_phase_order` proximal→distal (pelvis→torso→shoulder→elbow→fist) with lag frames | JSON phases |
| "it ignored my numbers" | escalate control density (sparse→keyed→dense) on the ignored track; or escalate execution carrier (text→pose video→rig; RDC tiers) | control_profile |

**Tinkering discipline:** one field per iteration → re-render → log the run (`runs/results.csv`) →
if the fix generalizes, promote it into a card/pattern. Tinkering sessions are experiments.

---

## PART C — Growth protocol (this repo grows with new research)

New research (movie-director concepts, RAG-pipeline output, etc.) enters by the **cannibalize
flow** — same every time:

1. Frozen copy → `research/<package>/` (never edited; own SHA integrity).
2. Adopt reusable assets → `lab/profiles/` or `assets/` (versioned).
3. **Concept cards** → `concepts.jsonl` (≥3 `nl_triggers` phrased how a user talks; honest status).
4. Index → `CONCEPT_INDEX.md` new Part (paper § → status → card).
5. **Controls grow:** if the research adds a new controllable (a director concept like blocking,
   eyeline match, 180-degree rule, shot-reverse-shot rhythm), extend: the SKELETON layer it belongs
   to (usually L13 Presentation), the FORMAT map row, and — critically — a **tinkering-table row**
   (what symptom it fixes, which field, which format).
6. Gate green → commit with CHANGELOG line.

A control isn't "grown" until it is: retrievable (card), placed (skeleton layer + format), and
adjustable (tinkering row). That triple is the definition of done for every future ingest.
