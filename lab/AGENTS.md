# lab/AGENTS.md — how an AI operates the Prompt Lab

> Repo-wide routing, editing laws, and the pre-commit validation gate live in the **root
> [`AGENTS.md`](../AGENTS.md)** — it wins on conflict. This file is the lab's operating procedure.

This lab tracks A/B tests of prompt variations for AI video generation and curates the patterns that
drive good output. You (an AI agent) use it three ways: **compose a prompt from tested blocks** for a
goal (the primary mode), **recommend a variant**, and **log a result** after a render so the lab learns.

Load `registry.yaml` + `blocks.yaml` first. Only open `variants/`, `runs/results.csv`, or
`experiments/` for detail.

## Named workflows (trigger phrases → runbook)

| When the user says | Follow |
|---|---|
| "pegasus extraction" / "extract this video with pegasus / twelve labs" | `RUNBOOK_pegasus_extraction.md` |
| "recreate the movement/choreography from this clip" | `RUNBOOK_reference_to_kinematic_truth.md` |
| "make it anime/cartoon/feature/superhuman" / "restyle but keep the choreography" | `RUNBOOK_cross_style_switching.md` |

## Concept kitchen — semantic retrieval (do this FIRST for any ask)

The lab's knowledge is a concept-card corpus (`concepts.jsonl`): every technique/doctrine/workflow as
an **ingredient** with `nl_triggers` (how humans phrase it), `what` it does, `status`+`evidence`,
`pairs_with`/`conflicts`, and `source` pointers. Map any natural-language ask to ingredients:

```bash
python3 lab/scripts/concepts.py query "<the user's ask, near-verbatim>"   # ranked pantry + bundle
python3 lab/scripts/concepts.py card <id>                                  # one ingredient in full
```

Cook like a chef, not a lookup table: the pantry tells you *what each ingredient does and what it
pairs with* — compose the recipe (union the top matches' `pairs_with`, respect `conflicts`, prefer
`proven`), then follow each card's `source` pointer for the full text. Retrieval returns the
**bundle**, never one item (RDC §34.3). Unproven ingredients get flagged and composed only with the
flag + a proposed A/B.

**Updating the corpus (how new knowledge enters):** when new research or a validated render finding
adds a concept — append ONE line to `concepts.jsonl`: id `c_*`, ≥3 `nl_triggers` (that's the
semantic mapping; write them as a user would actually phrase the problem), honest `status`
(`unexplored` until evidence), `evidence` ids that resolve, `source` pointing at the paper §/lab
file. Then `python3 lab/scripts/concepts.py validate` must pass. Update an existing card's status
/evidence when a run proves or refutes it — cards are living records, not archives.

**Ingredients vs. prepared bases:** `concepts.jsonl` cards are single ingredients; `lab/profiles/`
holds `profile://` **prepared bases** — versioned bundles of defaults + hard_constraints + metrics you
inherit then override (compiler-backed form of a block; precedence = local override > specific scope >
profile default). For motion/style work, start from a profile, override, and record which overrides
worked. Run the three roles separately — authoring proposes, compiler/resolver validates, verifier
measures (`c_three_agent_topology`); don't collapse them.

## To COMPOSE a prompt for a goal (primary mode)

The user states a goal ("realistic UGC ad for X", "anime fight, two fighters, 8s"). You derive the
best prompt from **tested modular blocks** — not from scratch:

1. Classify the goal → `domain` + `control_paradigm` (look/feel → prose; precise motion → numeric;
   both → hybrid). See `CONTROL_SURFACE.md`.
2. Select every block in `blocks.yaml` matching the domain; prefer higher `confidence`; resolve
   `conflicts_with`.
3. Assemble per `blocks.yaml → composition`: prose blocks weave into one description (+ say-line +
   render negatives, < 2000 chars); numeric blocks assemble the v005-style JSON; hybrid = both.
4. Deliver with a **rationale**: which blocks, each block's confidence and evidence, and any
   `unproven` block flagged as a proposed experiment.
5. If the goal needs a capability no block covers, look it up in `CONCEPT_INDEX.md` first — the full
   research-paper concept catalog with paper § refs — compose from the paper's definition, mark it
   unproven, and propose the isolated A/B that would prove it.

This is the flywheel: every render of a composition gets logged as a run → blocks/patterns gain or
lose confidence → the next composition is better-grounded.

### FORMAT DISCIPLINE — never default to natural language (owner law)

Agents drift to NL-only prompting because it is easy. **NL-only is not a legal default here.** For
any composed deliverable:

1. **Default output = the structured format(s) the control demands** (`FORMAT_CONTROL_MAP.md`,
   `UNIVERSAL_MOTION_SKELETON.md`): pure fight/motion → JSON canonical; intent/style → YAML; ordered
   script/triggers → XML; full production → the combination.
2. **NL is an OPTION, produced transparently** — deliver it as one *labeled variant alongside* the
   structured form(s), never silently *instead of* them. Say which formats you produced and why.
3. **For A/B, multi-format is the elite move** (p009: same content across NL / YAML / XML / JSON /
   combos = output variance = options to select from). When the user wants variations, emit the
   format spread, not one NL paragraph.
4. If you are about to hand the user a single NL paragraph, stop and check: which layer of the
   skeleton does this control, and which format owns that layer? Deliver that format too.

## First: pick the control paradigm

Before choosing levers, pick the paradigm from the goal (see `CONTROL_SURFACE.md`):
- **descriptive_prose** — for look / skin / vibe / performance *feel* (UGC talking-head, product). The
  model reads prose; structured format is packaging.
- **numeric_canonical_truth** — for precise *motion*: choreography, fights, dance, anime. Author
  explicit joint keyframes + timed contacts + Laban effort vectors + camera keyframes (see `v005`).
  The numbers ARE the control; the JSON alone can be sufficient.
- **hybrid** — numeric motion truth + prose for look/skin.

`CONTROL_SURFACE.md` also lists **unexplored channels** (FACS-as-numeric-track, body-control curves,
effort vectors for UGC, verification loop…). When a goal needs one, propose an experiment.

## To RECOMMEND a prompt combination for a goal

1. **Read the goal** and map it to score dimensions (`realism`, `skin`, `motion`, `adherence`).
2. **Select patterns** from `registry.yaml → patterns` where `effect_on` intersects the goal and
   `direction` is positive. Prefer higher `confidence`. Note each pattern's `recommend_when` guard.
3. **Compose the lever set:** union the `set` levers of the chosen patterns; apply every `avoid`.
   Resolve conflicts by confidence, then by `render_style` intent (raw_ugc vs cinematic).
4. **Find the closest existing variant** (`variants[].lever_tags`) with the best `best` score to reuse
   as a base; if none fits, compose a new lever set.
5. **Assemble the prompt** from that lever set using the format templates in `../assets/` (default
   `format: yaml_xml` or `yaml_json`), keeping it **< 2000 chars** (verify with `wc -c`). Translate
   every lever into concrete descriptive prose — the model reads the prose, not the tags.
6. **State the rationale:** list which patterns you applied and their confidence, so the human can
   trust or override. Flag any lever chosen on `low` confidence as "worth A/B testing."

## To LOG a result (so the lab improves)

After a render, append one row to `runs/results.csv`:
`run_id, variant_id, experiment_id, model, seed, date, realism, skin, motion, adherence, verdict, output_link, notes`
- New `run_id` (r003, r004, …). `experiment_id` blank unless part of an A/B. Scores are 1-5.
- If the run beats the variant's current `best`, update that variant's `best` in `registry.yaml`.
- If it's a **new** lever combination, add a variant record (id encodes the delta, e.g.
  `v0NN_<base>_<changed-lever>`), put its prompt body in `variants/`, and set its `lever_tags`.

## To reconstruct motion from a reference video

When the goal is "recreate the movement/choreography of this (authorized) clip," follow
`RUNBOOK_reference_to_kinematic_truth.md` — the two-lane extraction (Pegasus semantics + pose
measurement) → Video Observation Graph → v005-style kinematic JSON → regenerate → round-trip verify.
Identity/wardrobe/setting/distinctive choreography are swap fields, never cloned.

## To run an A/B test

Create `experiments/eNNN_<lever>.yaml`: `hypothesis`, `lever_under_test`, `variant_a`, `variant_b`
(identical except that one lever), the runs, the `result`, and the `promotes` pattern id.
**Change exactly one lever** so the output delta is attributable.

## To PROMOTE / update a pattern

Raise a pattern's `confidence` only when an **isolated** A/B (one lever changed) confirms it — bundled
evidence (a lever that happened to be inside a good champion) stays `low`. Add the experiment id to
`evidence`. Add new patterns when a lever repeatedly moves a dimension. Demote/flip a pattern if
results contradict it. Keep `confidence` honest — it reflects evidence, not how sure the wording sounds.

## Invariants (don't break these)

- One lever per A/B. Keep lever values from the `levers` vocabulary (extend the vocab deliberately).
- The model consumes **prose**; structured formats are packaging. Never claim a format change caused a
  realism change without an isolated test (see `p006`).
- Keep clip packages **< 2000 chars**. Keep product/proof claims truthful.
