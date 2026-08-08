---
name: cpcs-ugc-video-prompts
description: >
  Generate and evaluate UGC product-video directing packages through the provider-neutral CPCS
  intent, retrieval, strategy, canonical-score, provider-build, verification, and outcome workflow.
  Retrieve FACS, Laban, affect, camera, performance, or other concepts only when the request and
  evidence call for them. Use this whenever the user wants an
  AI-generated ad, UGC video, talking-head creator video, product demo/unboxing, or "a video that
  looks real / not AI"; wants a Veo or image-to-video prompt for a person performing to camera;
  needs a reference-still prompt (e.g. Nano Banana Pro) to anchor identity for image-to-video; or
  wants to extract and recreate the exact hand/body movement from an existing TikTok or reference
  video. Trigger even if they just say "make my product video look real," "write me a UGC ad
  prompt," or "why does my AI creator look fake" without naming CPCS, FACS, or Laban.
---

# CPCS UGC Video Prompt Compiler

## Scope and authority

This is the UGC profile skill, not the CPCS ontology. FACS and Laban are seed research domains and
optional directing mechanisms. They are not mandatory layers, privileged roots, or substitutes for
future research. Use the concepts and controls selected by the current intent, context, evidence,
and provider capability contracts.

The fully resolved canonical JSON score owns meaning. Natural language, YAML, JSON, XML, hybrid
documents, control media, and provider requests are projections. Do not assume that every provider
consumes prose or that one serialization performs best without provider, model, task, duration, and
experiment evidence.

```
ordinary intent -> normalized intent -> retrieved concepts -> directing strategy
-> canonical JSON score -> provider capability negotiation -> provider build
```

Begin with `./bin/cpcs agent.brief` for the exact task and role. Use the returned live operations.
Do not hand-edit curated concepts, mappings, rules, weights, or confidence.

> **Start here for "looks like a real phone video, not AI":** read
> `references/iphone_rawugc_realism.md`. It's the field-tested preset (iPhone-12 look, real skin
> texture, natural facial motion, anti-cinematic levers) refined from real render feedback, with two
> ready assets — a compact clip package and a matching reference still, both < 2000 chars. That
> preset beats the fully-scored approach when the goal is *raw* UGC rather than a polished ad.

## Workflow

1. **Orient and normalize:** request a task brief, inspect status, then normalize the ordinary
   language request through the public CPCS intent and context path.
2. **Gather inputs:** product (what it is, one benefit, honest proof, CTA), creator/look, ad format
   (talking-head / hands+voiceover / face-hook+b-roll / unboxing), target model. If anything is
   missing, **use sensible defaults and mark `[swap]` slots — don't block the user.** A concrete
   worked example is more useful than a form.
3. **Retrieve and map:** use the current reasoner and context bundle. Map the communication graph:
   `hook → problem → product_reveal → demonstration → proof → call_to_action`.
   Product should be first visible < 3.0 s; proof must precede CTA; CTA held ≥ 2.5 s.
4. **Compile:** select only source-traceable mechanisms, resolve conflicts and prerequisites, build
   the canonical score, then let the provider build choose supported projections and report loss.
5. **Verify and record:** bind results to exact artifact bytes. Capture exact human remarks, passed
   and failed dimensions, limitations, and verdicts through the testimonial path. Run accepted
   learning only for a complete reviewed controlled experiment.

## Optional performance mechanisms

Use these only when retrieval and the directing strategy select them. An educational device video,
hands-only demonstration, abstract animation, edit study, or camera experiment may not require FACS
or Laban.

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

## UGC realism profile

Apply only compatible controls selected by the UGC profile and current provider evidence. Details
and rationale: `references/method_details.md`.
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

## Compile provider projections

Translate formal codes into observable directing language when the selected provider lacks a native
control. Preserve the canonical code in score provenance. Respect the provider's measured prompt
budget and capability report; do not use a remembered character limit as a universal rule.

## Output formats

Return the provider build selected by CPCS. The existing assets remain experimental projections for
controlled comparison, not universal defaults:
- **minified JSON** control package (see `assets/minified_control_package.example.json`) for pipelines;
- a **< 2000-char `compiled_prompt` only** for pasting into a model input box;
- a **compact YAML-in-XML hybrid** that stays < 2000 chars and still carries every realism lever —
  see `assets/clip.iphone12_rawugc.hybrid.xml`. XML tags = header/routing; the CDATA YAML = the
  description the model reads.
- a **YAML + JSON combined** doc (readable YAML with an embedded valid-JSON `json:` value; dual-parse,
  < 2000 chars) — see `assets/clip.iphone12_rawugc.yaml_json.txt`.

Always identify the canonical score, provider-consumed fields, unsupported controls, projection
loss, and verification requirements.

## Outcome handling

Preserve success, failure, mixed, inconclusive, and reviewed no-go results. Keep exact user remarks
and reviewed quote spans. A negative outcome must retain the failed dimension, scope, tested delta,
evidence, and limitation so later traversal can explain why it downranked or rejected a path. One
failed render or derived correlation cannot create a global no-go. Hard rejection requires a
reviewed scoped failure card or curated rule.

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
