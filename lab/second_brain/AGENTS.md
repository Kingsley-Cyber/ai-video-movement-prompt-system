# lab/second_brain/AGENTS.md — curated reasoning control plane

> Load the root [`AGENTS.md`](../../AGENTS.md), then [`lab/AGENTS.md`](../AGENTS.md), then
> [`lab/registry.yaml`](../registry.yaml) before acting. The root laws win on conflict. This file is
> the operating contract for building and maintaining the repo-level curated second brain.

## The five Ws

### WHO

- **Owner / human curator:** approves durable knowledge, resolves ambiguous merges, and may explicitly
  promote a proposal into curated truth.
- **Implementation agent:** builds the storage, validation, graph, query, reflection, and migration
  code. In auto mode it continues through the task graph until a named external blocker or a green
  completion gate.
- **Polymath MCP:** external research memory. It retrieves passages, source metadata, and candidate
  knowledge from domains broader than FACS. It is a proposal source, never a direct writer of truth.
- **Pegasus AI:** semantic video-extraction lane. It produces append-only observations typed as
  `interpreted` or `inferred`; it never claims detector-grade measurement.
- **Compiler / recorder / reflector / verifier:** separate roles. Compiler resolves authored inputs,
  recorder appends what happened, reflector recomputes learned signals, verifier measures outputs.

### WHAT

Build a repo-level operational second brain that powers CPCS reasoning without duplicating the local
RAG corpus. It consists of:

1. **Curated:** durable concepts, authored edges, intents, mappings, and deterministic rules.
2. **Immutable:** sealed flights, generation runs, and Pegasus source-video observations.
3. **Derived:** learned weights, co-success edges, failure associations, reflection insights, and
   query indexes that can be deleted and rebuilt.
4. **Live graph:** a NetworkX `MultiDiGraph` assembled in memory from curated records, then overlaid
   with evidence-backed derived edges and temporary query nodes.
5. **Proposal lanes:** Polymath and Pegasus may create evidence-linked proposals; only promotion
   writes curated records.

The current [`lab/concepts.jsonl`](../concepts.jsonl) is the existing curated seed corpus. Preserve
its durable `c_*` IDs. Do not create a competing concept store or silently renumber existing cards.

### WHERE

- Existing curated seed: `lab/concepts.jsonl`
- Existing authored lab state: `lab/blocks.yaml`, `lab/registry.yaml`, `lab/profiles/`
- Existing derived repo graph: `lab/graph.json`, rebuilt by `lab/scripts/build_graph.py`
- Existing semantic retrieval: `lab/scripts/concepts.py`
- Existing graph traversal: `lab/scripts/graph.py`
- Existing Pegasus procedure: `lab/RUNBOOK_pegasus_extraction.md`
- Existing reference reconstruction: `lab/RUNBOOK_reference_to_kinematic_truth.md`
- New implementation home: `lab/second_brain/`
- Temporary MCP inventories, downloaded evidence, proxies, videos, and dense tracks: `work/second_brain/`
- Future curated/immutable/derived stores: create them under `lab/second_brain/data/` only after their
  schemas, validators, routing, and migration path pass in the same change.

### WHEN

Build in the order declared in `TASKS.yaml`.

- First inventory the repository and the actual Polymath MCP tool/resource surface.
- Then implement record schemas and validation before any bulk distillation.
- Then implement proposal, promotion, append-only recording, graph loading, and deterministic rebuild.
- Only after those gates are green may the agent distill Polymath sources in batches.
- Pegasus observations may be recorded after the immutable observation schema and append-only writer
  are green.
- Reflection runs only after immutable records exist and writes only the derived tier.
- Curated promotion occurs deliberately after deduplication, evidence review, and schema validation.
- Rebuild derived artifacts after any immutable append or reflection-algorithm version change.

### WHY

CPCS needs a compact operational vocabulary that can select, combine, reject, compile, test, and
explain controls across cinematography, lighting, animation, acting, FACS, Laban/BESS, BML, body
mechanics, camera, editing, audio, marketing, provider adaptation, and validation. The local RAG is
the broad library; this repo is the controlled field manual.

The architecture is sound only when deleting derived knowledge loses no truth:

```bash
rm -rf lab/second_brain/data/derived
python3 -m lab.second_brain.src.reflect rebuild
python3 -m lab.second_brain.src.validate control-plane
```

The rebuilt files must be deterministic for the same immutable inputs and algorithm version.

## Non-negotiable write laws

| Actor/process | May read | May write | Forbidden |
|---|---|---|---|
| Polymath MCP distiller | external corpus, curated records | proposal staging only | curated, immutable, derived |
| Pegasus extractor | source video, runbook, schemas | immutable observation append + proposals | curated concepts/edges, learned weights |
| Curator/promoter | proposals, curated records, evidence | curated append/update through validator | immutable mutation, direct derived edits |
| Recorder | sealed flight, exact artifacts | immutable append only | edit/delete prior records |
| Reflector | immutable ledgers, curated IDs | derived only | curated or immutable writes |
| Query/reasoner | curated + immutable + derived | temporary result/proof files in `work/` | persistent mutation during query |

Additional laws:

1. A learned edge without `evidence[]`, `model_version`, `algorithm_version`, and context cannot exist.
2. `promotes` requires an attributable controlled comparison. Bundled wins become
   `associated_with_success` or `confounded_with`, never causal promotion.
3. Pegasus semantics are `interpreted`/`inferred`. Pose, camera, face, or audio measurements must name
   the measuring tool and remain separate records.
4. Once a flight has a run, the flight is sealed. Any design change creates a new flight ID.
5. Exact prompt/request and output hashes are mandatory for immutable render runs.
6. RAG embeddings support retrieval and deduplication; they never define durable identity.
7. `lab/graph.json` remains derived and is never hand-edited.
8. Do not edit `research/`; it is frozen upstream evidence.
9. Never invent MCP tool names. Discover the connected surface first and record it in
   `work/second_brain/mcp_inventory.json`.
10. No bulk promotion. Distill in reviewable batches and preserve source-level provenance.

## Auto-mode execution contract

Do not stop after creating scaffolding. Continue through `TASKS.yaml` in dependency order. At every
phase:

1. Read the owning files instead of assuming their shape.
2. Make the smallest coherent change.
3. Run the phase acceptance command.
4. Record deterministic, observable output.
5. Fix red gates before starting the next phase.
6. Append the required `CHANGELOG.md` line in the same commit.
7. Run the final repository gate after all edits, not before them.

Stop only for a real external blocker such as unavailable MCP authentication, unavailable Pegasus
credentials/input video, a paid operation requiring owner approval, or an unresolved destructive
migration. When blocked, finish every unblocked task and write the exact blocker and continuation
command into `work/second_brain/BLOCKERS.md`.

## Polymath MCP distillation procedure

1. Inspect the runtime's connected MCP tools/resources and save an inventory under `work/second_brain/`.
2. Query broad operational domains, not only FACS: cinematography, lighting, composition, acting,
   gesture, animation principles, BML, Laban/BESS, biomechanics, kinematics, contact, dynamics,
   camera, editing, sound, marketing, motion capture, skeletons, OpenUSD/glTF, provider controls,
   validation, and experimental design.
3. Retrieve evidence bundles with stable source identifiers and locations.
4. Normalize candidate concepts to the existing `c_*` vocabulary; search `lab/concepts.jsonl` before
   proposing a new ID.
5. Write proposal JSONL conforming to `schemas/proposal.schema.json`.
6. Run deduplication and source validation.
7. Promote only through the curated writer; preserve the proposal ID and source claims.
8. After each batch, rebuild/query the live graph and inspect conflicts and orphan nodes.

Use `prompts/POLYMATH_DISTILLATION.md` as the task prompt.

## Pegasus video-distillation procedure

Follow `lab/RUNBOOK_pegasus_extraction.md` for the semantic multi-pass workflow and
`lab/RUNBOOK_reference_to_kinematic_truth.md` when precise motion reconstruction is required.

Pegasus must produce:

- a source manifest with content hash and rights scope;
- stable entity IDs;
- source-clock intervals with raw and resolved times;
- beats, atomic actions, camera/edit/audio/performance observations;
- communication function and semantic signature;
- contradictions, alternatives, uncertainty, and evidence class;
- the Pegasus provider/model/version, prompt hash, schema hash, and pass ID.

Append observations through the immutable recorder using
`schemas/video_observation.schema.json`. Dense videos, masks, pose arrays, optical flow, and proxies
stay under `work/`; committed records contain hashes and references. Candidate reusable concepts,
edges, mappings, or rules are emitted as proposals—not written directly to curated files.

Use `prompts/PEGASUS_VIDEO_DISTILLATION.md` as the extraction contract.

## Required implementation properties

- NetworkX `MultiDiGraph`; typed, directional parallel edges.
- Authored and learned edges carry explicit `edge_origin`.
- Save operations serialize authored records only. Never serialize the overlaid live graph back into
  curated storage.
- Traversal applies an admissibility predicate: conflicts prune, encoding/provider/domain constraints
  filter, and evidence-backed weight orders otherwise admissible hops.
- Deterministic tie-breakers end with stable IDs.
- Canonical JSON serialization is sorted and stable before hashing.
- Append-only writers refuse duplicate IDs and any attempt to replace existing immutable rows.
- Reflection is idempotent: identical inputs and algorithm version produce byte-identical outputs.
- Every answer can emit a proof trace showing selected concepts, paths, conflicts, evidence, and
  derived-edge provenance.

## Definition of done

The implementation is complete only when all of these pass:

```bash
python3 lab/scripts/concepts.py validate
python3 lab/scripts/build_graph.py
python3 lab/scripts/sync_repo.py
python3 lab/scripts/validate_repo.py
python3 -m unittest discover -s lab/second_brain/tests -p "test_*.py"
python3 -m lab.second_brain.src.reflect rebuild
python3 -m lab.second_brain.src.validate control-plane
```

The control-plane validation must report:

```text
CURATED: valid
IMMUTABLE: append-only ledger valid
DERIVED: rebuilt
LEARNED EDGES WITHOUT EVIDENCE: 0
LEARNED EDGES WITHOUT MODEL VERSION: 0
DIRECT DERIVED-TO-CURATED WRITES: 0
REBUILD DETERMINISM: pass
CONTROL PLANE: GREEN
```
