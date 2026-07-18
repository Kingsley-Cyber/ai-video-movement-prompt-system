# FACS + Laban Reference (for talking-head UGC)

Use this to fill the `facs_events`, `laban`, and `body_movement` layers of a control package, and to
translate them into plain language inside `compiled_prompt`. The model reads the plain language — the
codes are for you.

## Table of contents
1. FACS action units (the ones that matter for UGC)
2. FACS intensity + timing
3. Combinations that read as genuine vs. fake
4. Laban Effort, Shape, Space
5. Plain-language translation cheat sheet
6. Body-movement catalog

---

## 1. FACS action units (the ones that matter for UGC)

| AU | Name | Plain language for the prompt |
|----|------|-------------------------------|
| AU1 | Inner brow raiser | inner brows lift (concern, interest, sincerity onset) |
| AU2 | Outer brow raiser | brows lift (surprise, emphasis, "listen") |
| AU1+2 | Full brow raise | eyebrows lift in a quick "wait—" |
| AU4 | Brow lowerer | brow knits / furrows (concern, focus, doubt) |
| AU5 | Upper-lid raiser | eyes widen, alert |
| AU6 | Cheek raiser | cheeks lift (the "real smile" muscle) |
| AU7 | Lid tightener | eyes narrow slightly with intent |
| AU9 | Nose wrinkler | nose scrunches ("ugh / ick") |
| AU10 | Upper-lip raiser | upper lip lifts (mild distaste / intensity) |
| AU12 | Lip-corner puller | mouth smiles |
| AU14 | Dimpler | one-sided smirk / wry |
| AU15 | Lip-corner depressor | mouth turns down (sad, unimpressed) |
| AU17 | Chin raiser | chin pushes up, lower lip out (doubt, "hmm") |
| AU23/24 | Lip tightener / pressor | presses lips (holding back, resolve) |
| AU25 | Lips part | mouth parts to speak |
| AU26 | Jaw drop | jaw opens (surprise, mid-word) |
| AU45 | Blink | natural blink |

## 2. FACS intensity + timing

- Intensity is **A→E** (A = trace, C = marked/pronounced, E = maximum). For UGC keep most in **B–C**;
  reserve **D** for the single emphasis peak. Anything at E on a face reads as a mug/caricature.
- Give each event a **start_s / end_s**. Expressions have onset → apex → offset; don't snap them on.
- Blinks: roughly every 2–4 s, plus one on a thought-shift. Zero blinking = uncanny.

## 3. Combinations that read as genuine vs. fake

- **Genuine (Duchenne) smile = AU6 + AU12.** Mouth-only (AU12 alone) reads as a polite/social smile
  and, held too long, as creepy. When you want warmth, always add the cheeks.
- **Concerned-but-warm:** brief **AU4 + AU12** together (knit brow, small smile) — fine for a beat,
  not sustained.
- **Sincere close:** **AU1 + AU12** at low intensity — inner brows up, gentle smile ("I really mean
  this").
- **Emphatic peak:** **AU4 + AU5 + AU7** — knit + widen + tighten, the "listen to me" face; pair with
  the Laban sudden accent.
- **Surprise/hook:** **AU1 + AU2 + AU5** (+ AU26 if mouth opens).
- Avoid impossible sustains (e.g., wide AU5 held for 5 s), and avoid a single frozen expression across
  a whole line — sequence at least 2–3 events.

## 4. Laban Effort, Shape, Space

**Effort factors** (pick a value on each axis; a full combo = one of the 8 named Efforts):

| Factor | Values |
|--------|--------|
| Weight | light ↔ strong |
| Time | sustained ↔ sudden |
| Space | direct ↔ indirect |
| Flow | free ↔ bound |

The 8 Efforts (handy shorthand): **Float** (light/sustained/indirect/free), **Punch/Thrust**
(strong/sudden/direct/bound), **Glide** (light/sustained/direct/free), **Slash**
(strong/sudden/indirect/free), **Dab** (light/sudden/direct/bound), **Wring**
(strong/sustained/indirect/bound), **Flick** (light/sudden/indirect/free), **Press**
(strong/sustained/direct/bound).

**Shape** (how the body sculpts space): `rising | sinking | advancing | retreating | spreading |
enclosing`.

**How to use it for UGC:**
- **Baseline** for a casual creator: `light / sustained / direct / free` (buoyant, easy, credible).
- **Accent** on the emphasis word: switch Time to **sudden** (a Dab or Punch) for one beat — this is
  the physical "hit" that makes a line land.
- **Shape**: `advancing` when leaning toward the lens on emphasis; `enclosing` when settling inward on
  a sincere line; `rising` on excitement; `sinking` on a letdown/problem.
- **Product handling** (reach/hold/show): `light / sustained / direct / bound` (Glide→Press) reads as
  careful and deliberate; `enclosing` on the grasp.

## 5. Plain-language translation cheat sheet

| Score | Write in the compiled_prompt |
|-------|------------------------------|
| AU1+2:C | "eyebrows lift in a quick 'wait—'" |
| AU4:C | "her brow knits with concern" |
| AU4+5+7:D | "she sharpens — brow tight, eyes widening with intent" |
| AU6+12:B | "a warm genuine smile, eyes crinkling" |
| AU1+12:B | "inner brows lift into a sincere half-smile" |
| Laban sudden accent | "a quick, punchy beat on the word" |
| Shape advancing | "she leans slightly toward the lens" |
| Shape enclosing | "she settles inward, softer" |
| light/free baseline | "loose, buoyant, unhurried movement" |

## 6. Body-movement catalog

Pull 3–5 of these per clip so the body isn't frozen:
- **breath**: continuous subtle rise/fall; an audible inhale before the first word; a soft settling
  breath before a sincere line.
- **weight_shift**: onto one hip mid-sentence (subtle).
- **head**: empathetic tilt; small shake ("no matter what you do"); a single nod on agreement; settle
  to center on the close.
- **torso**: small lean-in on the peak; ease back to neutral after.
- **shoulders**: a relax/drop as tension releases on the closing line.
- **hands**: one hand rises into frame for an open-palm or point **beat** on the emphasis word, then
  lowers; fingers count "three things"; a light self-touch (hair tuck, touch collarbone) on a candid
  aside.
- **micro-still-avoidance**: even in a "hold," add a slight wrist rotation or a breath — never a
  statue.
