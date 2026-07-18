# Prompt Lab

A tracking system for **A/B testing prompt variations** for AI video generation and **curating the
patterns** that drive good output. Every prompt variant, render result, and finding is a structured,
machine-readable record so an AI agent (or you) can load the state and **recommend combinations**.

## The model

```
levers  →  variants  →  runs (results.csv)  →  experiments (A/B)  →  patterns  →  recommendations
```

- **Levers** (`registry.yaml`) — the controlled vocabulary of knobs (camera.fps, skin.strategy, …).
- **Variants** (`variants/`) — tracked prompt packages, each tagged with its lever values.
- **Runs** (`runs/results.csv`) — one row per generation: variant → model/seed → output link + 1-5
  scores (realism, skin, motion, adherence) + verdict.
- **Experiments** (`experiments/`) — A/B tests that change **one lever** so a result delta is
  attributable.
- **Patterns** (`registry.yaml`) — curated "lever(s) → effect" findings with confidence + evidence.
  This is the recommendation engine.

## Files

| Path | Role |
|---|---|
| `registry.yaml` | **Single source of truth** — levers, variants, patterns, experiments. Load this first. |
| `AGENTS.md` | How an AI agent recommends a combination and logs results. |
| `variants/` | The actual prompt bodies (paste-ready). |
| `runs/results.csv` | Append-only results ledger (open in a spreadsheet, sort by score). |
| `experiments/` | A/B test records. |
| `schema/records.schema.json` | Record shapes for variant / run / experiment / pattern. |

## Quick start

- **Get a recommendation:** point an agent at this folder and ask, e.g. *"recommend a combination for
  max realism, iPhone look, 4s talking-head."* It reads `registry.yaml`, unions the positive patterns,
  and assembles a prompt from the templates. See `AGENTS.md`.
- **Log a render:** add a row to `runs/results.csv`; if it beats the variant's `best`, update
  `registry.yaml`.
- **Test a lever:** copy a variant, change exactly one lever, render both on the same seed, record an
  experiment.

## Honesty rule

`confidence` on a pattern reflects **evidence**, not conviction. A lever bundled inside a good
champion stays `low` confidence until an **isolated** A/B (one lever changed, same seed) confirms it.
Current seed data is from the authoring session (qualitative) — the champion `v001` is real and
user-validated; the single-lever attributions are hypotheses awaiting isolated renders.
