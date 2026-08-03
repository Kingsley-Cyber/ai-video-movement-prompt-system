# CPCS Universal Video Intent System

> **AI agents:** this repo is AI-managed. Read **[`AGENTS.md`](AGENTS.md)** first — it routes every
> task to its home and carries the editing laws (anti-bloat, validation gate, commit conventions).

For the implemented runtime, second-brain internals, dependency map, current gaps, and remediation
order, read **[`ARCHITECTURE.md`](ARCHITECTURE.md)**.

> **CPCS is a universal AI video-intent generator and creative-direction compiler that turns a
> user's goal into an evidence-informed, provider-ready video production plan.**

The user describes the video in ordinary language. CPCS is intended to infer the domain, retrieve
relevant directing knowledge, resolve constraints, build one provider-neutral production score,
project that score into the selected model's controls, and verify the render. FACS, Laban, graph
traversal, research retrieval, and provider adapters are internal mechanisms rather than required
user vocabulary.

```text
user goal + user/project context + domain profiles + evidence + provider capabilities
→ normalized intent
→ canonical video score
→ provider request and prompt package
→ render verification and learning
```

## One kernel, many video domains

CPCS uses one canonical language for intent, subjects, identity, environment, action, performance,
timing, camera, editing, audio, continuity, constraints, provider controls, and verification. Domain
profiles configure that language; they do not create separate schemas or prompt systems.

| Experience | Profile emphasis |
|---|---|
| UGC and product demonstrations | trust, claims, product interaction, phone realism, communication beats |
| Cinematic and dialogue scenes | objective, subtext, gaze, suppression, blocking, motivated camera |
| Action, dance, and anime | causality, motion phases, contacts, screen direction, timing, readability |
| Music, education, social, and custom projects | domain-specific defaults, constraints, workflows, and verification metrics |

Profiles can blend through typed precedence:

```text
universal defaults
→ domain profiles
→ user defaults
→ project profile
→ scene overrides
→ shot overrides
→ event locks
```

Conflicts remain explicit. For example, a phone-realism profile cannot silently combine deep focus
with a cinematic profile's shallow depth of field. The dominant intent resolves the conflict, or the
system asks the user which result matters more.

Automatic routing is the default:

```text
"Talking to the phone about a product"
→ UGC + product demonstration + phone realism

"Quiet realization during dialogue"
→ cinematic dialogue + restrained performance + psychological subtext

"Two rivals exchange attacks in a hand-drawn style"
→ screen action + multi-actor geography + anime stylization
```

The interface shows the detected mode so the user can accept or change it.

## Intended user output

A completed compilation produces one traceable build rather than an attractive paragraph with no
control structure:

```text
build/
├── canonical_score.json
├── provider_request.json
├── prompt.txt
├── reference_still_prompt.txt
├── capability_report.json
├── loss_report.json
├── verification_plan.json
└── build_manifest.json
```

Guided users describe a video, upload references, choose duration and platform, review the detected
intent, and render. Advanced users edit the same score's beats, performance, motion, camera, timing,
contacts, profile blend, provider realization, and verification thresholds.

## Current implementation state

The universal product contract is the target, not a claim that the full application already runs.
The repository currently implements the governed knowledge foundation: curated concepts, typed
reasoning, deterministic distillation, query safety, a read-only context bundle, experimental
evidence, media-analysis adapters, component profiles, deterministic intent normalization and
profile routing, one provider-neutral canonical score, typed domain-profile resolution,
hash-bound research-to-control translation, deterministic Veo 3.1 build compilation with explicit
capability and loss accounting, and a local journaled execution boundary that captures, resumes,
and content-hashes provider work without writing knowledge authority. A provider-neutral verifier
then probes rendered media, adjudicates source-cited semantic, measured, and human-review evidence,
preserves disagreements, and proposes only bounded reassertions of existing canonical controls.
Authorized Markdown, text, JSON, JSONL,
YAML, XML, and typed Polymath passages can now enter a safe, content-addressed extraction bridge
that emits bounded, reviewable candidate bundles without promoting repository knowledge. Curated
records now support deterministic current and historical validity, reciprocal replacement lineage,
and a rebuildable lexical, alias, vector, graph, source, evidence, provider, experiment, and video
index catalog.

Persistent user/project preferences, live provider qualification, controlled evidence learning,
and the guided or advanced end-user interface remain implementation gaps. Their
dependency order and acceptance canaries live in
[`ARCHITECTURE.md`](ARCHITECTURE.md).

## Repository map

| Path | What it is |
|---|---|
| `ARCHITECTURE.md` | Product contract, actual runtime, gap matrix, ownership, and remediation order |
| `SKILL.md` | Current UGC authoring specialization, not the universal runtime |
| `lab/second_brain/` | Safe research extraction, curated knowledge, typed graph reasoning, evidence, context, and distillation |
| `lab/compiler/` | One universal-score resolver, typed merge policy, research-control translations, provider capabilities, and non-submitting build compiler |
| `lab/runtime/` | Journaled provider execution, recovery, and transport-only generation adapters |
| `lab/verification/` | Local media compliance, evidence-lane conflict handling, and bounded repair planning |
| `lab/profiles/` | Component profiles, router labels, one universal profile, and domain configurations |
| `lab/registry.yaml` | Prompt-lab levers, variants, patterns, experiments, and routed artifacts |
| `references/facs_laban_reference.md` | FACS action-unit catalog, Laban efforts/shape, plain-language translations |
| `references/method_details.md` | Realism lock list, reference-still pattern, captions/assembly, verification, per-model notes, reverse (video→prompt) extraction |
| `references/iphone_rawugc_realism.md` | **Field-tested preset** — the raw iPhone-UGC look, anti-AI-skin recipe, preferred formats |
| `assets/clip.iphone12_rawugc.hybrid.xml` | Compact YAML-in-XML clip package (< 2000 chars) |
| `assets/clip.iphone12_rawugc.yaml_json.txt` | YAML + embedded-JSON dual-parse clip package (< 2000 chars) |
| `assets/reference_still.iphone12_morning.txt` | Reference-still prompt (image-to-video identity + skin anchor) |
| `assets/clip_control_package.template.yaml` | Blank fully-scored control template |
| `assets/minified_control_package.example.json` | Minified JSON control example |

## Current evidence base: UGC and motion

- **Anti-AI skin (the #1 tell):** never ask for "smooth" skin — that *causes* the waxy plastic look.
  Instead name real microtexture (fine pores, uneven tone, fine lines, under-eye puffiness, T-zone
  sheen) **and** forbid `smooth_ai_skin / waxy / poreless / airbrushed`. For image-to-video, skin is
  locked by the **reference still**, not the video prompt.
- **iPhone-realism levers:** `30fps` (not cinematic 24), Smart-HDR flat tone, cool white balance,
  deep focus / no bokeh, floaty built-in stabilization.
- **Natural facial motion:** add a `face_motion` layer (eye darts, blinks, brow flickers, talking
  mouth shapes) so the face is never stiff/frozen.
- **Loosen the performance for raw UGC:** casual, low-key, a small "um," a glance away. Over-direction
  reads as an actor hitting marks.
- **Format does not drive realism for look controls.** XML/YAML/JSON are organizational scaffolding; the
  model reads the descriptive text. The compact **YAML-in-XML** and **YAML+JSON** packages are useful
  because they carry every realism lever in one paste under the ~2000-char input cap.

These observations cover tested portions of the current lab. They are ingredients for relevant
profiles, not universal defaults for every video domain.

## Current agent-operated surfaces

Point Claude Code or a compatible agent at this folder to use today's authoring and repository
operations. `SKILL.md` handles the current UGC specialization. `lab/AGENTS.md` handles composition,
experiments, and render verdicts. `lab/second_brain/AGENTS.md` governs retrieval, distillation,
curation, reasoning, context, and evidence.

## Use it from another agent

`AGENT_PROMPT.md` contains operator prompts for research distillation, concept retrieval, prompt-lab
composition, and the current UGC workflow. These are development and authoring clients of CPCS, not
substitutes for the planned end-user intent application.

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
