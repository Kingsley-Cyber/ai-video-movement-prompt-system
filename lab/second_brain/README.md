# CPCS curated second brain

This directory is the implementation home for the repo-level reasoning memory. It does not replace
the local Polymath RAG. Polymath stores broad source material; this layer stores the compact,
versioned, operational knowledge that CPCS can reason over, compile, test, and explain.

## Architecture

```text
Polymath MCP / research sources
        │ evidence-linked proposals
        ▼
CURATED — concepts, authored edges, intents, mappings, rules
        │ compilation and experiment design
        ▼
IMMUTABLE — sealed flights, render runs, Pegasus observations
        │ deterministic reflection
        ▼
DERIVED — weights, co-success, failure associations, insights, indexes
        │ overlay at load time
        ▼
NetworkX MultiDiGraph + temporary query graph
```

The truth boundary is the important part:

- Curated knowledge is deliberate and Git-versioned.
- Immutable records state what was run or observed and are never edited or deleted.
- Derived knowledge is inference. It is disposable and must be reproducible.

## Integration with the current repository

The implementation must extend, not fork, these existing systems:

| Existing artifact | Role in the second brain |
|---|---|
| `lab/concepts.jsonl` | Curated seed corpus; preserve every durable `c_*` ID |
| `lab/scripts/concepts.py` | Current semantic retrieval and concept validation |
| `lab/graph.json` | Existing derived repo-knowledge view; never hand-edit |
| `lab/scripts/build_graph.py` | Deterministic graph builder to extend |
| `lab/scripts/graph.py` | Existing CLI to extend with reasoning/query commands |
| `lab/registry.yaml` | Single lab index; owns pointers to this directory |
| `lab/scripts/sync_repo.py` | Drift manager and rebuild contract |
| `lab/RUNBOOK_pegasus_extraction.md` | Semantic video extraction procedure |
| `lab/RUNBOOK_reference_to_kinematic_truth.md` | Pegasus + measurement reconstruction lane |
| `lab/runs/results.csv` | Legacy empirical ledger requiring a non-destructive migration adapter |

Do not create `concepts_v2.jsonl`, `graph_v2.json`, or another competing CLI.

## Intended implementation tree

The implementation agent creates this structure incrementally after schemas and validators exist:

```text
lab/second_brain/
├── AGENTS.md
├── README.md
├── SCHEMA.md
├── TASKS.yaml
├── schemas/
├── prompts/
├── data/
│   ├── curated/
│   │   ├── edges.jsonl
│   │   ├── intents.jsonl
│   │   ├── mappings.jsonl
│   │   └── rules.jsonl
│   ├── immutable/
│   │   ├── flights.jsonl
│   │   ├── runs.jsonl
│   │   └── video_observations.jsonl
│   └── derived/
│       ├── weights.json
│       ├── insights.jsonl
│       └── indexes/
├── src/
└── tests/
```

`lab/concepts.jsonl` remains the canonical concept location until an atomic, validated migration is
implemented. The first loader should treat it as the curated node source and load second-brain
authored edges/mappings around it.

## Reset theorem

The implementation is not trustworthy until this works:

```bash
rm -rf lab/second_brain/data/derived
python3 -m lab.second_brain.src.reflect rebuild
python3 -m lab.second_brain.src.validate control-plane
```

A second rebuild over unchanged inputs must produce the same file hashes.

Empirical provider-effect weights rebuild from immutable render runs. Semantic video indexes and
observation-derived hypotheses rebuild from immutable video observations. Neither may rewrite
curated knowledge.

## Non-goals

- Copying raw books, papers, or RAG chunks into the repository.
- Turning every extracted entity into a durable concept.
- Allowing reflection to promote its own conclusions.
- Treating Pegasus descriptions as measured trajectories.
- Replacing the existing compiler, profiles, lab experiments, or graph with a framework.
- Persisting temporary query nodes or the fully overlaid in-memory graph as authored truth.

Start with [`AGENTS.md`](AGENTS.md), then execute [`TASKS.yaml`](TASKS.yaml).
