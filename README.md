# AI Video Movement Prompt System (CPCS)

A modular, **movement-theory-based prompt system** for generating realistic UGC / talking-head video
with AI video models (Veo 3 / 3.1, Sora 2, Kling, Runway) and image models (e.g. Nano Banana Pro).

It packages research on **how human performance and motion can be captured and modularized into a
prompt** — using **FACS** (Facial Action Coding System) for the face and **Laban Movement Analysis**
for movement quality — into a reusable, structured "control score" that compiles down to a
ready-to-paste prompt. This repo is also a drop-in **Claude Code / Agent skill** (`SKILL.md`).

## The core idea

Realistic AI video comes from **directing a performance, not writing a vibe.** A vague prompt gives
the model nothing to render, so it defaults to a glassy, evenly-lit, robotically-still avatar — the
"AI tell." Instead you specify the performance in time (face + movement + body + camera), then
**compile it into the plain-language prompt the model actually reads.**

```
CPCS score (FACS + Laban + body + camera)  ──compiles──▶  prose prompt  ──▶  video model
```

The structured layers are scaffolding that force specificity; the model consumes the compiled prose.

## What's inside

| Path | What it is |
|---|---|
| `SKILL.md` | The method + workflow (install as a skill, or read as the guide) |
| `references/facs_laban_reference.md` | FACS action-unit catalog, Laban efforts/shape, plain-language translations |
| `references/method_details.md` | Realism lock list, reference-still pattern, captions/assembly, verification, per-model notes, reverse (video→prompt) extraction |
| `references/iphone_rawugc_realism.md` | **Field-tested preset** — the raw iPhone-UGC look, anti-AI-skin recipe, preferred formats |
| `assets/clip.iphone12_rawugc.hybrid.xml` | Compact YAML-in-XML clip package (< 2000 chars) |
| `assets/clip.iphone12_rawugc.yaml_json.txt` | YAML + embedded-JSON dual-parse clip package (< 2000 chars) |
| `assets/reference_still.iphone12_morning.txt` | Reference-still prompt (image-to-video identity + skin anchor) |
| `assets/clip_control_package.template.yaml` | Blank fully-scored control template |
| `assets/minified_control_package.example.json` | Minified JSON control example |

## Key findings (learned from real renders)

- **Anti-AI skin (the #1 tell):** never ask for "smooth" skin — that *causes* the waxy plastic look.
  Instead name real microtexture (fine pores, uneven tone, fine lines, under-eye puffiness, T-zone
  sheen) **and** forbid `smooth_ai_skin / waxy / poreless / airbrushed`. For image-to-video, skin is
  locked by the **reference still**, not the video prompt.
- **iPhone-realism levers:** `30fps` (not cinematic 24), Smart-HDR flat tone, cool white balance,
  deep focus / no bokeh, floaty built-in stabilization.
- **Natural facial motion:** add a `face_motion` layer (eye darts, blinks, brow flickers, talking
  mouth shapes) so the face is never stiff/frozen.
- **Loosen the performance for raw UGC:** casual, low-key, a small "um," a glance away — over-direction
  reads as an actor hitting marks.
- **Format doesn't drive realism — content does.** XML/YAML/JSON are organizational scaffolding; the
  model reads the descriptive text. The compact **YAML-in-XML** and **YAML+JSON** packages are useful
  because they carry every realism lever in one paste under the ~2000-char input cap.

## Using it as a skill

Point Claude Code (or a compatible agent) at this folder as a skill, or open the packaged `.skill`
and install it. It triggers on requests like "make my product video look real," "write me a UGC ad
prompt," or "why does my AI creator look fake." Then it walks the workflow above.

## Use it from another agent

`AGENT_PROMPT.md` has a ready-to-paste kickoff prompt for a Codex-style / coding agent. It clones this
repo, internalizes the method, and works at full depth — the iPhone-12 raw-UGC realism, the
anti-AI-skin recipe, and the compact YAML-in-XML / YAML+JSON output under 2000 characters. Hand it
your product and it produces the reference still + clips.

## Prompt Lab (A/B testing + pattern curation)

`lab/` is a tracking system for A/B testing prompt variations and curating the patterns that drive
good output. Every variant, render result, and finding is a structured, machine-readable record, so
an AI agent loads one file (`lab/registry.yaml`) and **recommends prompt combinations** for a goal.

- **`lab/registry.yaml`** — levers vocabulary + variants + patterns + experiments (the source of truth)
- **`lab/AGENTS.md`** — how an agent recommends a combination and logs results
- **`lab/variants/`** — tracked prompt bodies · **`lab/runs/results.csv`** — scored results ledger ·
  **`lab/experiments/`** — A/B tests · **`lab/schema/`** — record shapes

Ask an agent: *"using lab/, recommend a combination for max realism, iPhone look, 4s talking-head."*
See `lab/README.md`.

## Research

The `research/` folder contains the underlying research package — the CPCS directorial-control paper,
the FACS/Laban framework, schemas, a RAG corpus, reference indexes, and the reverse (video → CPCS)
extraction pipeline. Start with
`research/CPCS_FACS_Laban_AI_Video_Research_Package_v1.2/paper/` and that package's own `README.md`.
The skill in this repo is the practical, generation-side distillation of that research.

## Ethics & rights

Preserve *structure* (timing, movement quality, camera grammar), not identity or unverifiable hype.
Keep product/proof claims truthful and substantiated. When recreating a reference video, swap identity,
voice, logos, and any distinctive/recognizable choreography — extract movement quality and timing, not
a clone.

## License

[MIT](LICENSE) — free to use, modify, and distribute. Open-source research release.
