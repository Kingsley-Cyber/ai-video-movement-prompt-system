---
name: cpcs-ugc-video-prompts
description: >
  Generate realistic, high-fidelity UGC product-video prompts for AI video models (Veo 3 / 3.1,
  Sora 2, Kling, Runway) using the CPCS method — a directorial "control score" that layers
  time-indexed FACS facial actions, Laban movement quality, and natural micro body-movement over
  each shot, then compiles it to a ready-to-paste prompt. Use this whenever the user wants an
  AI-generated ad, UGC video, talking-head creator video, product demo/unboxing, or "a video that
  looks real / not AI"; wants a Veo or image-to-video prompt for a person performing to camera;
  needs a reference-still prompt (e.g. Nano Banana Pro) to anchor identity for image-to-video; or
  wants to extract and recreate the exact hand/body movement from an existing TikTok or reference
  video. Trigger even if they just say "make my product video look real," "write me a UGC ad
  prompt," or "why does my AI creator look fake" without naming CPCS, FACS, or Laban.
---

# CPCS UGC Video Prompt Compiler

## The core idea (read this first)

Realistic UGC video comes from **directing a performance, not writing a vibe.** A normal prompt
("a woman talks about a serum, realistic") gives the model no performance to render, so it defaults
to a glassy, evenly-lit, robotically-still avatar — the "AI tell."

The fix is a **CPCS control score**: you specify the performance in time — the face as FACS action
units, the movement *quality* as Laban efforts, and a track of natural micro body-movement — then
**compile that into the plain-language prompt the model actually reads.**

```
CPCS score (FACS + Laban + body movement, in YAML)  ──compiles──▶  compiled_prompt (prose)  ──▶  video model
```

**Critical:** video models (Veo, Sora, Kling, Runway) consume **prose**, not YAML or AU codes. So
the structured score is scaffolding that forces specificity; the deliverable the user pastes is the
`compiled_prompt` string. Always translate FACS/Laban into plain language inside `compiled_prompt`
("brow knits with concern," not "AU4:C").

> **Start here for "looks like a real phone video, not AI":** read
> `references/iphone_rawugc_realism.md`. It's the field-tested preset (iPhone-12 look, real skin
> texture, natural facial motion, anti-cinematic levers) refined from real render feedback, with two
> ready assets — a compact clip package and a matching reference still, both < 2000 chars. That
> preset beats the fully-scored approach when the goal is *raw* UGC rather than a polished ad.

## Workflow

1. **Gather inputs:** product (what it is, one benefit, honest proof, CTA), creator/look, ad format
   (talking-head / hands+voiceover / face-hook+b-roll / unboxing), target model. If anything is
   missing, **use sensible defaults and mark `[swap]` slots — don't block the user.** A concrete
   worked example is more useful than a form.
2. **Map to the communication graph** with timings:
   `hook → problem → product_reveal → demonstration → proof → call_to_action`.
   Product should be first visible < 3.0 s; proof must precede CTA; CTA held ≥ 2.5 s.
3. **Split into one clip per beat.** Most models render a single continuous ~8 s shot and cannot
   produce a multi-cut talking-head in one generation — and jump cuts *are* authentic UGC. So each
   beat = its own clip = its own control package. Generate ~8 s, trim to the beat window.
4. **Write a control package per clip** (schema in `assets/clip_control_package.template.yaml`),
   filling the FACS / Laban / body-movement layers well (that is the whole differentiator — see
   below), and end each with a `compiled_prompt`.
5. **For image-to-video,** write one reference-still prompt (identity anchor) and reuse it across all
   clips so the face/room/wardrobe don't drift. See `references/method_details.md`.
6. **Deliver** the compiled prompts + a short verification checklist.

## Fill the performance layers well — this is the differentiator

### FACS (the face, in time)
Don't give one static expression. Give a **sequence** of action-unit events with start/end times,
so the face lives through the line. Typical talking-head hook:
`brow-raise (AU1+2) → concern-knit (AU4) → sharpen (AU4+5+7) on the emphasis word → sincere soften (AU1+12)`.
Full AU catalog, intensities (A–E), and plain-language translations: `references/facs_laban_reference.md`.
A genuine smile **must** include the cheeks (AU6+AU12), not just the mouth — this alone kills a lot of
uncanny-valley.

### Laban (movement quality, in time)
Set a **baseline** effort (e.g. `light / sustained / direct / free` = buoyant and casual) and add a
**sudden accent** exactly on the emphasis word (the "stop scrolling" beat), plus a **Shape** change
(lean in = `advancing`; settle inward on a sincere line = `enclosing`). Efforts + Shape reference:
`references/facs_laban_reference.md`.

### Body movement (the biggest realism lever)
Real people are **never robotically still.** Always include a body-movement track:
- continuous subtle **breathing** (never fully still);
- one small **weight shift** onto a hip mid-line;
- **head** micro-moves — an empathetic tilt, a small shake on "no matter what you do";
- a small **lean** toward the lens/window on the emphasis (motivates the exposure lift);
- **one hand beat** entering frame on the peak word, then lowering;
- **shoulder** release on the sincere/closing line.

If you add nothing else beyond the compiled prose, add these — they are what read as "a real person
filmed this."

## The "looks real" lock list (apply to every clip)

Bake these into every `compiled_prompt`. Details and rationale: `references/method_details.md`.
- **Phone capture, not cinema:** handheld arm's-length selfie, ~24 mm wide front-lens with mild
  barrel distortion, gentle micro-sway + one re-centering reframe, autofocus that *hunts then snaps*,
  exposure that drifts toward window light — "imperfect but bounded."
- **Available light only:** a window key on one side, soft shadow on the other. No 3-point lighting.
- **Gaze-to-lens 0.6–0.8**, not a locked stare — brief natural glances away and back.
- **Skin realism (the #1 AI tell) — counter-intuitive:** never ask for "smooth" skin; that produces
  the waxy plastic AI look. Instead **name real microtexture** (fine visible pores, subtly uneven
  tone, faint fine lines, under-eye puffiness, T-zone-only oil sheen) **and forbid the tell**
  (`smooth_ai_skin, waxy, poreless, airbrushed, uniform_skin_tone, plastic_skin`). For image-to-video,
  the texture is locked by the **reference still**, not the video prompt — fix it there first. Full
  recipe: `references/iphone_rawugc_realism.md`.
- **Natural facial motion:** a still-but-talking face reads as AI — add a `face_motion` layer (eye
  darts, blinks, brow flickers, cheek/lip micro-shifts, talking mouth shapes, head bobs synced to
  speech; never `frozen_stiff_face`).
- **Audio:** close phone-mic with room tone and a small breath before the line — not studio-clean.
- **Pace:** ~165–190 wpm conversational; a ~0.28 s pause right before the proof line.

## Compile to the prompt the model reads

Rules for `compiled_prompt`:
- **Translate every AU/Laban term to plain language.** The model can't parse "AU4:C" — write "her
  brow knits with concern."
- Keep the imperfections in the prose (they're the point).
- End with `(no on-screen text, no subtitles)` so captions stay for the edit.
- If the user has a **character limit** (many model input boxes cap at ~2000 chars), the
  `compiled_prompt` **alone** is the deliverable — target < ~1500 chars and drop the YAML.

## Output formats

Default to a **per-clip YAML control package + its `compiled_prompt`.** On request also produce:
- **minified JSON** control package (see `assets/minified_control_package.example.json`) for pipelines;
- a **< 2000-char `compiled_prompt` only** for pasting into a model input box;
- a **compact YAML-in-XML hybrid** that stays < 2000 chars and still carries every realism lever —
  see `assets/clip.iphone12_rawugc.hybrid.xml`. XML tags = header/routing; the CDATA YAML = the
  description the model reads.
- a **YAML + JSON combined** doc (readable YAML with an embedded valid-JSON `json:` value; dual-parse,
  < 2000 chars) — see `assets/clip.iphone12_rawugc.yaml_json.txt`.

**For UGC clip packages, default to one of those two combined formats** (YAML-in-XML or YAML+JSON) —
they're the validated house style: compact enough for the ~2000-char input cap, dual-parseable for
tooling, and structured so no realism lever gets dropped. Full rationale: `references/iphone_rawugc_realism.md`.

Always tell the user which part the model actually consumes (the `compiled_prompt`), so they know
the score is scaffolding.

## Related tasks this skill also covers

- **Reference still for image-to-video** (Nano Banana Pro / any image model): opening-frame = the
  *start* of the action, hands out of frame, 9:16, reused as the identity anchor. Pattern in
  `references/method_details.md`.
- **Recreate movement from an existing video** (reverse path): a Pegasus / video-understanding
  extraction prompt that emits a time-indexed hand+body movement description you compile back into a
  generation prompt. Prompt + the fps/slowed-proxy caveat in `references/method_details.md`.
- **Captions, assembly, verification checklist, per-model notes** (Veo/Sora/Kling/Runway clip length
  and audio): `references/method_details.md`.

## A note on honesty and rights

Preserve *structure* (timing, movement quality, camera grammar), not identity or unverifiable hype.
Keep every product/proof claim truthful and substantiated. When recreating a reference video, swap
identity, voice, logos, and any distinctive/recognizable choreography — extract the movement quality
and timing, not a clone.
