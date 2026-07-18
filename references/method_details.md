# Method Details

Supporting detail for the CPCS UGC workflow. Read the section you need.

## Table of contents
1. The "looks real" lock list (full)
2. Reference still for image-to-video (Nano Banana Pro pattern)
3. Multi-clip assembly + captions
4. Verification checklist
5. Reverse path: recreate movement from a reference video (Pegasus)
6. Per-model notes (Veo / Sora / Kling / Runway)

---

## 1. The "looks real" lock list (full)

These separate "AI ad" from "real creator." Every clip's `compiled_prompt` should carry them.

**Capture grammar (phone, not cinema)**
- Handheld selfie at arm's length; continuous micro-sway; one small re-centering reframe per clip.
- Front-phone look: ~24 mm-equivalent wide lens, mild barrel distortion, slight rolling-shutter on
  fast motion.
- Autofocus *hunts once then snaps* to the face; exposure lifts/dims as the subject moves toward the
  window — "present but bounded," never studio-stable.
- Available light only: a window key on one side, soft shadow on the other.

**Performance**
- Gaze-to-lens 0.6–0.8 (brief natural glances away and back, not a locked stare).
- Micro-expressions sequenced (see `facs_laban_reference.md`); genuine smiles use the cheeks (AU6+12).
- Natural blink rate; one real breath before a line; one micro-disfluency ("okay so—") in exactly one
  clip, not all.
- Laban baseline light/direct with a sudden accent on the emphasis word.

**Skin & audio (the biggest tells)**
- Visible pores, faint shine, flyaways, uneven tone. Explicitly forbid: beauty-smoothing, airbrush,
  plastic skin, glam lighting, robotic stillness.
- Close phone-mic sound with room tone; slight breath/proximity; not noise-gated or studio-clean.

**Speech / pacing**
- ~165–190 wpm conversational; a ~0.28 s pause immediately before the proof line (the single most
  persuasive micro-beat).

## 2. Reference still for image-to-video (Nano Banana Pro pattern)

For image-to-video, generate one still that IS the **opening frame** of the clip, then reuse the same
person across all clips (feed the still back in: "same person, same room, same wardrobe, now holding
…") so identity doesn't drift.

Principles:
- The still should be the **start of the action**, not the end — image-to-video animates *out* of it.
  For a hook, brows just raised, mouth just parting to speak. Not a finished smile.
- **Hands out of frame** so gestures can enter naturally without a pop.
- Set **9:16** to match the video (mismatched aspect causes first-frame crop artifacts).
- Frame it as "a single frame grabbed from a real phone video" to push candid/imperfect.
- Generate 2–3 and pick the one with the most natural eyes and skin.

Prompt skeleton:
```
A candid vertical 9:16 selfie photo that looks like a single frame grabbed from a real phone video —
NOT a professional portrait. [Creator appearance]. In [setting], soft natural window light from the
left, blurred [background]. Front-facing phone camera: wide ~24mm look, mild barrel distortion,
shallow phone-style depth. She looks into the lens, [start-of-action micro-expression]. Photoreal and
imperfect: visible pores, faint T-zone sheen, stray baby hairs, no beauty-smoothing, no airbrushing,
no glam lighting. Natural muted phone-camera color. Hands and product out of frame. No text, no
watermark, no logo.
```

## 3. Multi-clip assembly + captions

- Cut order follows the communication graph; hard **jump cuts**, no dissolves (a real reference has
  ~5 cuts + a few b-roll inserts).
- B-roll: generate 1–3 extra 2 s product-only clips (on a surface, in sunlight, cap twist) and cut
  them over the demonstration.
- Let **room tone bridge** the cuts so it sounds like one session.
- **Captions are added in the editor, not burned in by the model:** ~1.15 cards/s, ~4 words/card,
  highlighted word on the spoken stress, all inside the vertical safe area (clear of top ~12% / bottom
  ~18%). Plain platform-style captions read as more authentic than designed ones.

## 4. Verification checklist

Run on the assembled cut (this is the round-trip check the method is built around):
- [ ] Hook resolves by ~1.35 s (±0.25 s)
- [ ] Product first visible ≤ 3.0 s
- [ ] Product on screen ≥ 35% of runtime
- [ ] Proof beat precedes the CTA
- [ ] CTA / final ask held ≥ 2.5 s
- [ ] Gaze-to-lens looks like 0.6–0.8, not a robotic stare
- [ ] Visible natural body motion (breath + weight shift + at least one head move or hand beat)
- [ ] Skin shows pores/shine, no plastic smoothing
- [ ] Captions inside safe area, ~4 words/card, on-stress emphasis
- [ ] Every claim is truthful and substantiated

## 5. Reverse path: recreate movement from a reference video (Pegasus)

When the user wants to reproduce the hand/body movement from an existing (authorized) TikTok/reference
clip, run a video-understanding model (e.g. Twelve Labs Pegasus, Gemini) to emit a time-indexed
movement description, then compile the `recreation_note` + `laban` fields back into a generation prompt.

**Caveat that decides whether the output is usable:** these models sample ~1 frame/sec by default and
miss fast hand motion. So **clip to just the movement** and upload a **slowed proxy (0.25×–0.5×)**,
then convert times back (×0.25 → multiply reported seconds by 0.25). Never treat the response as
sub-frame truth; flag fast segments for frame-level review.

Extraction prompt (paste into the video model):
```
You are a movement-evidence analyst. Analyze ONLY this authorized clip and produce a time-indexed
description of actor_A's HAND/ARM gestures and FULL-BODY movement, detailed enough to recreate the
motion in a video generator. Do not identify the person. Output valid JSON only.
Rules: every event has start_s and end_s; separate observed evidence from interpretation; use
"unknown" when unsupported; never invent 3D coordinates, joint angles, force, or sub-frame timing;
note occlusion/blur/cuts/slow-motion/camera-motion as confounds; set high_fps_review=true for motion
too fast to read at 1fps.
For each segment return: id, start_s, end_s, body_phase, hand{which,shape,path,amplitude,speed},
body{posture,weight_shift,torso,head,shoulders,locomotion}, action_atom, laban{weight,time,space,
flow,shape}, contact, sync, evidence_class, confidence, recreation_note (one instruction to reproduce
the exact movement). Then append: global_movement_quality, tempo_rhythm, confounds[],
high_fps_segments[], rights_sensitive (["distinctive_choreography"] if a recognizable routine, else
["none"]).
```
Then map each `recreation_note` + `laban` into a movement-only image-to-video prompt (the reference
still carries appearance). If `rights_sensitive` flags distinctive choreography, re-perform/vary it —
extract quality and timing, don't clone.

## 6. Per-model notes

- **Veo 3 / 3.1:** ~8 s single continuous shot; **native synchronized dialogue + SFX** — put the
  spoken line in quotes in the prompt and add `(no subtitles)`. Strong photoreal humans; best default
  for talking-head UGC. Use image-to-video ("ingredients"/reference image) for identity consistency.
- **Sora 2:** strong physical realism + audio; good for demo/b-roll and cameo-style creator shots.
- **Kling 2.x:** excellent motion + image-to-video; add audio/dialogue separately in post.
- **Runway Gen-4:** great for controlled/stylized b-roll and image-to-video; dialogue added in post.

Clip length caps mean a 15 s ad is always assembled from multiple generations — design beat-per-clip.
