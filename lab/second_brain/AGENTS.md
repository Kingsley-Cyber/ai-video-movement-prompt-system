# Second-brain operating contract

Read `../../AGENTS.md`, `../AGENTS.md`, and `../registry.yaml` first. Those files win on conflict.
This subsystem extends the existing lab control plane. `../concepts.jsonl` remains the sole curated
concept-node authority, and `../../research/` remains frozen.

## Five-W charter

### WHO

The system has five actors with separate authority:

1. The repository owner has final authority over promoted concepts, authored relationships,
   ontology decisions, and experimental verdicts.
2. An authoring or curation agent may create proposals and promote validated proposals. It preserves
   durable IDs, source references, and Git history.
3. External RAG adapters, including Polymath MCP, retrieve passages, metadata, locators, and
   candidate relationships. They submit versioned batches and cannot write proposals directly.
   The Polymath inventory adapter may update the corpus manifest. The distiller records the
   retrieval and extractor contract, computes deterministic fingerprints, deduplication decisions,
   hop alignment, and refactor actions, then stages admissible proposals. Retrieval, embeddings,
   and external IDs do not establish durable repository identity.
4. The TwelveLabs transport manages provider assets, stores, search, Jockey responses, and
   embeddings without repository authority. The Pegasus lane alone records semantic observations
   from authorized video. Its normal evidence class is `interpreted` or `inferred`, never unearned
   measurement. Its knowledge proposals must pass the shared deterministic distiller.
5. Intent router, compiler, recorder, reflector, and query engine are separate roles. The router
   classifies a user request and selects configured profile labels without inventing directing
   knowledge or provider output. The compiler resolves
   curated knowledge, the recorder appends immutable history, the reflector writes derived output,
   and the query engine creates temporary reasoning results.

Never collapse these actors into one unrestricted language-model process.

### WHAT

The control plane has three tiers:

- `curated/` contains Git-versioned authored edges, deterministic rules, normalized intents,
  concept-to-control mappings, and source references.
- `immutable/` contains sealed flights, append-only runs, Pegasus observations, and measurement
  observations.
- `derived/` contains reproducible learned weights, insights, coverage, and indexes.

Curated data defines what CPCS recognizes. Immutable data records what occurred. Derived data is
disposable inference. The live reasoning graph overlays all three in memory and is never serialized
back into an authored store.

### WHEN

External knowledge starts as a retrieval batch. `distill.py` converts each candidate into a
traceable staging decision under a versioned policy. Promotion requires source verification, schema
validation, duplicate review, operational-usefulness review, relationship validation, and explicit
curation.
A flight is sealed before its first run. Recording follows rendering or extraction. Reflection runs
only after immutable evidence exists and reruns after inputs or policy change. Reflection never
promotes itself.

### WHERE

All new control-plane code and data live under `lab/second_brain/`. Dense assets, downloaded source
bytes, videos, masks, and temporary query output belong under the ignored `work/` directory. The
existing `lab/graph.json` remains the derived repository-wide view.

### WHY

CPCS needs operational reasoning across cinematography, lighting, performance, FACS, Laban,
kinematics, contact, animation, editing, audio, marketing, provider capability, and render evidence.
Polymath is the research library. This repository stores the smaller vocabulary and relationship
system that CPCS can select, traverse, compile, test, and explain.

The defining control-plane test is:

```bash
rm -rf lab/second_brain/derived
python3 -m lab.second_brain.src.reflect rebuild
python3 -m lab.second_brain.src.validate control-plane
```

With unchanged inputs and policy, reflection must rebuild byte-identical normalized output.

## Write boundaries

| Role | Persistent write scope |
|---|---|
| Curator | `lab/concepts.jsonl` and `curated/` |
| Recorder | append only to `immutable/` |
| Reflector | `derived/` only |
| External RAG adapters | no direct repository writes; submit versioned distillation batches |
| Polymath inventory adapter | `staging/corpus_manifest.jsonl` only |
| Distiller | `staging/distillation_runs.jsonl` and admissible staging proposals |
| TwelveLabs transport | ignored provider artifacts under `work/twelvelabs/` |
| Pegasus adapter | immutable Pegasus observations and distillation batches |
| Query engine | temporary output under `work/` only |
| Context broker | no repository writes; typed bundles are returned to the caller |
| Intent router | no repository writes; normalized intents and context handoffs are returned to the caller |

Project code provides no immutable update or delete operation. A learned edge is invalid without
evidence IDs, model version, context, observation count, and derivation policy. A causal `promotes`
edge also requires an isolated comparison.

## Evidence and identity rules

- Durable concept and intent IDs come only from curated repository files.
- Unknown concept layers are valid free strings.
- Semantic extraction cannot prove exact joints, force, FACS intensity, or contact timing.
- Measurement lanes remain separate and record their tools and evidence classes.
- Existing `c_*`, `v*`, `r*`, `p*`, `e*`, and `blk_*` IDs are never renumbered.
- Learned weights may order admissible choices, but cannot override a hard rule or authored conflict.
- `research/` is read-only upstream evidence.

## Commands

```bash
python3 -m lab.second_brain.src.validate schemas
python3 -m lab.second_brain.src.validate curated
python3 -m lab.second_brain.src.validate immutable
python3 -m lab.second_brain.src.validate control-plane
python3 -m lab.second_brain.src.graph stats
python3 -m lab.second_brain.src.query reason "dramatic natural product reveal"
python3 -m lab.second_brain.src.context build "restrained fear escalating into urgent movement" --token-budget 12000
python3 -m lab.second_brain.src.intent normalize "Cinematic UGC product recommendation"
python3 -m lab.second_brain.src.intent context "Show how this device works in a clear educational video"
python3 -m lab.second_brain.src.ingest batch work/candidate-batch.json
python3 -m lab.second_brain.src.distill status
python3 -m lab.second_brain.src.curate bundle <run-id> work/durable-ids.json --by <curator-id> --review work/review.json
python3 -m lab.second_brain.src.pegasus doctor
python3 -m lab.second_brain.src.providers.twelvelabs --help
python3 -m lab.second_brain.src.reflect rebuild
python3 -m unittest discover -s lab/second_brain/tests -p "test_*.py"
```
