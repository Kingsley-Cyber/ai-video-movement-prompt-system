# AGENTS.md — repo governance and routing (read me first)

This repo is **AI-managed under human direction** (owner: Kingsley-Cyber). Agents build, extend, and
maintain it; the owner supplies goals and render verdicts. This file is the single entry point: it
routes every task to its home and states the laws that keep an AI-maintained repo from rotting into
bloat. **If you are an agent working here, load this file first, then only what your task routes to.**

## What this repo is

A research-grounded, evidence-tracked prompt system for AI video generation (CPCS: FACS + Laban
directorial control). Two halves: a **skill** (generation-side authoring method) and a **lab**
(A/B-tested variants, patterns, and modular blocks with confidence + evidence). The `research/`
folder is the frozen upstream paper/package the system is built on.

## Routing — task → entry point

| Task | Go to |
|---|---|
| Compose a generation prompt for a goal | `lab/AGENTS.md` ("To COMPOSE") + `lab/blocks.yaml` |
| Log a render result / verdict | `lab/runs/results.csv` (+ update `best` in `lab/registry.yaml`) |
| Run or design an A/B experiment | `lab/AGENTS.md` + `lab/experiments/` |
| "Pegasus extraction" | `lab/RUNBOOK_pegasus_extraction.md` |
| Recreate motion from a reference video | `lab/RUNBOOK_reference_to_kinematic_truth.md` |
| Full UGC authoring workflow (talking-head ads) | `SKILL.md` + `references/` + `assets/` |
| Theory / "does the paper cover X?" | `lab/CONCEPT_INDEX.md` → `research/.../paper/` |
| Kickoff prompts for external agents | `AGENT_PROMPT.md` |
| Repo state index (levers, variants, patterns, pointers) | `lab/registry.yaml` |

Sub-scopes keep their own operating docs: `lab/AGENTS.md` (lab procedures) and `lab/README.md`
(human orientation). This root file governs the whole repo and wins on conflict.

## Directory contract

```
/            governance only (this file, README, LICENSE, CHANGELOG, AGENT_PROMPT, SKILL.md)
assets/      paste-ready prompt templates (each < 2000 chars when claimed)
references/  skill reference docs (FACS/Laban vocab, method details, realism presets)
lab/         the experiment system — registry.yaml is its single index
  variants/  runs/  experiments/  schema/  scripts/
research/    FROZEN upstream package (SHA256SUMS-protected). NEVER edit in place.
             New findings go to lab/ (CONCEPT_INDEX marks them as candidates to upstream).
work/        (gitignored) extraction workspaces, proxies, model files — never committed
```

## Editing laws (anti-bloat)

1. **One concern, one file.** Extend the owning file; never fork (`*_v2`, `*_final`, `*_new` are
   forbidden). If content moves, delete the old location in the same commit — no dual copies.
2. **Route before you write.** A new file is legal only if a routing row (here) or a registry
   pointer (`lab/registry.yaml`) is added in the same commit. Unrouted files are orphans.
3. **Registry-first for the lab.** Every lab artifact (variant, runbook, script, doc) gets its
   pointer in `registry.yaml`. IDs are immutable once referenced (`v###`, `r###`, `p###`, `e###`,
   `blk_*`).
4. **Evidence discipline.** Any claim of what works carries `confidence` + `evidence` ids, and
   confidence never exceeds evidence: bundled observation = low; near-isolated flip = medium/high;
   isolated seed-controlled A/B = highest. Negative results are first-class records.
5. **Runbooks are executable, not essays.** Commands verified against real files; honest-limits
   section required. Theory belongs in `CONCEPT_INDEX.md` (which cites the paper) — don't restate it.
6. **Naming:** `RUNBOOK_*.md` procedures · `UPPERCASE.md` reference docs · lowercase data files
   (`registry.yaml`, `blocks.yaml`, `results.csv`) · `v###_slug` variants (id encodes the delta).
7. **Prompts the model reads stay under their stated char budget** — verify with `wc -c`, never
   eyeball.
8. **No session-only knowledge.** Anything load-bearing must live in-repo; assume the next agent has
   zero conversation history.

## Validation gate — run before every commit

```bash
python3 lab/scripts/validate_repo.py
```

It must pass (exit 0): YAML parses (registry/blocks/experiments), results.csv rows resolve to
variants, pattern evidence ids resolve, variant files exist on disk both directions, lab scripts
compile, runbook example records validate against the package schema, char-budget assets are under
budget. Fix failures before pushing — never commit a red gate.

## Commit and log conventions

- Imperative subject; body says what and why; end with the agent's `Co-Authored-By` line.
- Commit as the owner's no-reply identity
  (`git -c user.name="Kingsley-Cyber" -c user.email="Kingsley-Cyber@users.noreply.github.com"`).
- **Same commit** appends one line to `CHANGELOG.md`: `- YYYY-MM-DD [scope] summary` (scopes:
  `lab`, `skill`, `research`, `governance`). Git history is the detailed log; CHANGELOG is the
  scannable one-line-per-change ledger.

## Priorities when directives conflict

Owner's explicit instruction → this file → `lab/AGENTS.md` → local file conventions. When an owner
instruction changes a law here, update this file in the same commit so the law and the practice
never diverge.
