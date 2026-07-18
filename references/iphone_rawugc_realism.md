# Field-tested preset: raw iPhone UGC (what's working)

This file captures the settings that have produced genuinely-real-looking UGC in practice — refined
from real render feedback, not theory. When someone wants "looks like a real phone video, not AI,"
start here. Two failure modes recur; each has a fix.

## Failure mode 1 — "too movie-like / cinematic"
The model's default prior is cinematic (shallow depth of field, graded color, gimbal-smooth, golden
light). You must actively fight it. Cure = the **anti-cinematic block**:
- say it plainly: "ordinary real phone video, NOT cinematic, not a commercial, no film look, no color grade";
- **flat overhead / available indoor light**, not golden-hour window light;
- **deep focus, NO bokeh / no background blur** (phone selfies keep everything in focus);
- ordinary, slightly cluttered room (bathroom/bedroom) — not a styled set;
- **loosen the performance** (see below) — over-direction reads as a paid actor hitting marks.

## Failure mode 2 — "AI skin" (waxy, plastic, too smooth)
This is the #1 tell. Note the trap: telling the model "smooth skin" makes it *worse* (plastic). Real
skin is not smooth. Cure = **name the microtexture positively AND forbid the AI look**:

Positive (what real skin has) — for a no-makeup ~30-yr-old morning face:
`fine visible pores on cheeks and nose, subtly uneven skin tone, faint fine lines, slight under-eye
puffiness and a soft pillow crease, light oil sheen only in the T-zone, faint natural redness by the
nose.`

Negative (forbid the tell):
`smooth_ai_skin, waxy_skin, poreless, airbrushed, uniform_skin_tone, plastic_skin, beauty_smoothing.`

Framing line that works: *"looks like an unfiltered real iPhone photo of real skin — the OPPOSITE of
smooth AI skin."*

> **Image-to-video rule:** skin texture is set by the **reference still**, not the video prompt. If
> the still is waxy, the video animates waxy no matter what. Put the microtexture recipe in the
> **still** first.

## The iPhone-12 look (a strong, specific realism lever)
Naming a real device gives the model a concrete target. iPhone 12 signature:

**Video:** `1080p; 30fps (NOT 24 — 24 reads as film, 30 reads as real phone video); smart_hdr flat
tone with lifted shadows; cool/neutral white balance; Apple temporal noise-reduction (slight shadow
smear); light over-sharpening halos; faint H.265 artifacts; built-in digital stabilization (smooth
but floaty, micro-jitter — not a gimbal); autofocus & exposure "breathe" and re-adjust; mild
rolling-shutter on quick motion; front camera ~23mm f/2.2, held a bit too close and slightly below
eye level → mild wide-angle distortion; deep focus, no bokeh.`

**Still (image):** same signature minus the motion-only fields (drop fps, stabilization, rolling
shutter, AF/AE breathing).

The single biggest cadence tell is **30fps, not 24.**

## Natural facial motion (avoid the frozen/stiff face)
A still-but-talking face reads as AI. Add a `face_motion` layer: *constantly, subtly alive — natural
eye movement and small darts, gentle blinks, tiny brow flickers, soft cheek and lip micro-shifts,
natural talking mouth shapes, small head bobs synced to speech; relaxed, low-key, never stiff or
frozen.* Forbid `frozen_stiff_face`.

## Loosened performance (for raw UGC, not polished ads)
Dial the direction *down*: casual "telling-a-friend" energy, low-key, **not performing**; a small
shrug; one quick glance off to the side (loses her train of thought) then back; a small "um" or
restart. Drop the choreographed FACS/Laban "beats" — real talking isn't choreographed. (The full
FACS/Laban scoring in `facs_laban_reference.md` is for *polished* performance; raw UGC wants less.)

## Format note (learned the hard way) + preferred UGC formats
The **format doesn't drive realism — the content does.** XML/YAML/JSON are organizational scaffolding;
the model reads the descriptive text. Use a compact structure if it helps you, but keep it inside the
model's input limit (many boxes cap ~2000 chars) and don't let markup tokens dilute the description.

**That said — the formats that have worked best in practice for UGC (King's validated house style),
each kept < 2000 chars so they carry every realism lever in one paste:**
- **YAML-in-XML** — XML envelope (header/routing) + a YAML `<control>` block in CDATA.
  Asset: `../assets/clip.iphone12_rawugc.hybrid.xml`.
- **YAML + JSON** — one dual-parse doc: readable YAML with an embedded `json:` value that is valid
  JSON (JSON ⊂ YAML). Asset: `../assets/clip.iphone12_rawugc.yaml_json.txt`.

**Default to one of these two for UGC clip packages in future sessions.** Why they help (beyond taste):
they force the description into named, checkable fields (`skin_have` / `skin_avoid` / `face` / `device`)
so nothing gets dropped, they stay dual-parseable for tooling, and they fit the ~2000-char input cap.
The realism still comes from the field *content* (iPhone-12 look, real-skin microtexture, natural
face motion, anti-cinematic) — the format just makes sure all of it survives into the paste.

## Ready-to-use assets
- `../assets/clip.iphone12_rawugc.hybrid.xml` — the compact YAML-in-XML clip package that's been
  landing well (4s, iPhone-12, natural face motion, real morning skin), < 2000 chars.
- `../assets/reference_still.iphone12_morning.txt` — the matching reference-still prompt (real
  morning skin, anti-AI-texture), < 2000 chars. Generate this first for image-to-video.

Keep the still and the clip describing the **same** iPhone-12 + skin signature so the look doesn't
drift on the first frame.
