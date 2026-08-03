# Codebase Intent Gap Analysis

**Verdict:** BLOCKED
**Core distillation verdict:** PASS
**Traversal-gate verdict:** PASS
**Repository:** `/Users/king/Documents/New project`
**Plan:** `/Users/king/.codex/attachments/0aed1997-d7e3-4c81-aa23-f34890b9a0e3/pasted-text-1.txt`, SHA-256 `419ef089a00a2f2b4e664edb916ea6158f408046e0b6a4f2243069b43ab3f43c`
**Revision:** `3db5dcef5f4902ac7343b79a3d9bdae7dc17fc7e`, implementation present as uncommitted changes
**Audited at:** `2026-07-30T23:35:49-06:00`

The local research-to-traversal lifecycle is implemented. It accepts Polymath, Pegasus, and generic
RAG batches; rejects direct external staging; distills connected proposal sets; promotes a reviewed
run with rollback on member failure; traverses the new typed edge; and compiles the new mapping.
The full mission remains blocked by external acceptance evidence: two Polymath records expose zero
chunks, and this environment has no TwelveLabs API key, configured knowledge store, or authorized
provider asset.

## Intent Contract

The primary runtime is a repeatable research-distillation loop:

1. A retrieval agent finds a graph or coverage gap and retrieves exact source passages.
2. A versioned batch contract pins corpus, query, tool parameters, source hashes, extractor model,
   and prompt hash.
3. A deterministic policy fingerprints candidates, checks exact and probable duplicates, aligns
   them to graph hops, resolves same-batch dependencies, and proposes refactor actions.
4. Admissible records enter staging with complete decision lineage. A separate explicit review
   promotes them into curated authority.
5. Query, compile, and traversal use the expanded graph. Replaying the same evidence against the
   new curated snapshot converts prior additions into deterministic duplicate decisions.

Existing IDs and source references must survive. `lab/concepts.jsonl` remains concept authority,
`research/` stays frozen, immutable records are append-only, and learned data is fully rebuildable.
External retrieval may propose knowledge but cannot establish curated truth. This applies to
Polymath, Pegasus, and registered generic RAG proposals.

## Actual Runtime

`src/distill.py` implements policy `cpcs-distill/1.1`. It hashes the normalized batch, policy, and
curated snapshot to create a durable run ID. Four persistent runs currently hold 225 candidate
decisions. Every decision records source evidence, fingerprint, dedup matches, hop anchors, current
path, dependencies, disposition, and refactor actions. A new concept now also needs a typed
structural path to curated knowledge plus an operational edge or mapping. A failed concept blocks
its same-batch dependents. `src/ingest.py` accepts versioned batches with explicit external origins
and rejects direct external proposal staging before a write. `src/curate.py` orders reviewed bundle
promotion by dependency and restores touched curated files if a member fails during the process.
Effective status is derived from curated provenance: all 111 staged proposal records are promoted,
so intake status reports zero pending even though the historical proposal rows retain their
original `pending` field.

The 90 migrated concept IDs remain intact. Thirty-seven reviewed Polymath concepts bring the
curated total to 127. Five GitHub-backed reasoning and retrieval cards bring the current total to
132. The authored ledger contains 236 edges, one deterministic rule, one intent, and 45 mappings.
Five legacy CSV rows remain unchanged and are mirrored as five sealed flights plus five
hash-chained immutable runs. The live reasoning graph contains 142 nodes and 241 edges. The
repository graph contains 337 nodes and 653 edges.

## Traversal Gate Extension

`src/graph.py` is the edge-policy authority. Structural edges establish nesting; operational and
dependency edges connect a concept to use; contextual edges expose choices; constraint edges never
expand traversal. Legacy `pairs_with` is low priority, is limited to one use per path, and has a
global hop budget.

`src/distill.py` decides admission. Placement is deterministic, but truth claims are not inferred
from placement. The Laban decimal canaries prove the distinction: a concept-only note and a loose
pair are rejected, while `refines -> Laban effort` plus an executable numeric mapping is admitted.
A provider-specific output claim still needs an isolated evaluation.

`src/query.py` decides retrieval and traversal. Multi-term roots need at least two overlapping
terms unless the full concept name or a one-word trigger matches. Every hop reports direction,
transition, family, and policy version. Missing or partial term coverage returns a deterministic
`knowledge_gap` that can drive the next retrieval cycle.

`src/providers/twelvelabs.py` pins SDK 1.3.1 and isolates store creation, asset and item polling,
fully paginated search, Marengo 3.0 embeddings, and strict Jockey responses from repository writes.
`src/pegasus.py` validates one authorized job, checks the ready item-to-asset binding, saves
canonical request and SDK-response artifacts under ignored `work/`, validates the same JSON Schema
sent to Jockey, and appends semantics through the immutable ledger. Every Pegasus knowledge
proposal now enters `src/distill.py`; direct staging fails validation and promotion.

The production proof used a Polymath passage from the VES Handbook about neutralizing VFX plates,
carrying a controlled creative grade, reviewing through a final-look LUT, and checking integration
without the LUT. Run `distill_c4c1e66a2b64427cd27135c2` staged one concept, one authored edge, and
one mapping. Explicit review promoted `c_dual_view_color_integration`, `edge_000226`, and
`mapping_000040`. Query and compile then selected the concept, traversed the edge, and emitted
control `color.vfx.dual_view_integration`. Replay run `distill_55e37a781ca456d0cedec271` rejected
all three candidates as exact duplicates against the updated curated snapshot.

The generic-RAG canary submits a versioned batch for decimal spatial sampling, a `refines` edge to
Laban effort, and control mapping `motion.laban.space_decimal_hypothesis`. Bundle promotion writes
the concept before the edge and mapping. A query rooted at Laban effort then traverses
`edge_000001` in the isolated test repository and the compiler emits the control with path, edge,
source, alternative-path, and knowledge-gap trace fields. A second canary gives the edge an invalid
durable ID after the concept member is attempted and verifies that all curated files return to
their pre-promotion bytes.

## Gap Matrix

| ID | Requirement | Expected evidence | Observed evidence | Status | Impact | Dependency | Smallest remediation | Verifier |
|---|---|---|---|---|---|---|---|---|
| REQ-001 | Routed three-tier subsystem | governance routes and registered paths | entrypoint: `lab/second_brain/AGENTS.md`; wiring: root and lab routes plus twelve registered public entrypoints; outcome: one governed owner subtree; verification:pass S5 | WORKING | subsystem stays reachable and owned | none | preserve S5 checks | `python3 lab/scripts/sync_repo.py` |
| REQ-002 | Schemas and actor write boundaries | validators reject cross-tier writes | entrypoint: `src/validate.py`; wiring: 16 schemas, exact actor paths, and cross-store checks; outcome: curated, immutable, derived, staging, and ignored provider-artifact owners remain separate; verification:pass control plane | WORKING | inference remains tier-typed | REQ-001 | add stores only with schema and owner checks | `python3 -m lab.second_brain.src.validate control-plane` |
| REQ-003 | Authored edge authority | no derived relationship authority in curated records | entrypoint: `src/graph.py`; wiring: closed edge enum plus versioned family, direction, rank, and traversal policy; outcome: 236 authored edges; verification:pass schema and direction tests | WORKING | relationships have one authority and explicit hop meaning | REQ-002 | version edge-policy changes | `python3 -m unittest lab.second_brain.tests.test_graph lab.second_brain.tests.test_query lab.second_brain.tests.test_validate` |
| REQ-004 | Sealed flights and append-only runs | hashes, concept snapshots, field matching, and chain validation | entrypoint: `src/record.py`; wiring: seal then append; outcome: five upgraded legacy flights and runs with preserved IDs; verification:pass mismatch and duplicate refusal | WORKING | immutable history can drive reflection | REQ-002 | append evidence only through `record.py` | `python3 -m lab.second_brain.src.validate immutable` |
| REQ-005 | Explainable deterministic query | multi-hop paths with rule and conflict precedence | entrypoint: `src/query.py`; wiring: shared evaluators, typed direction-labelled hops, bounded legacy edges, and explicit knowledge gaps; outcome: selected and rejected concepts, supporting paths, conflicts, evidence, alternatives, and retrieval follow-ups; verification:pass rule, conflict, typed-hop, unknown-query, and repository canaries | WORKING | recommendations and retrieval gaps are reproducible | REQ-003 | version query-policy changes | `python3 -m unittest lab.second_brain.tests.test_query` |
| REQ-006 | Disposable deterministic reflection | derived-only rebuild from curated and immutable inputs | entrypoint: `src/reflect.py`; wiring: complete derived reset and four normalized outputs; outcome: run, Pegasus, measurement, and comparison indexes; verification:pass stale deletion and repeat hashes | WORKING | learned data is safely disposable | REQ-004 | version derivation-policy changes | `python3 -m lab.second_brain.src.validate control-plane` |
| REQ-007A | Generic RAG proposal boundary | versioned batches with adapter identity, source locators, hashes, and explicit origin | entrypoint: `python3 -m lab.second_brain.src.ingest batch <batch.json>`; wiring: `ingest_distillation_batch` calls the shared distiller while direct external `proposal` calls fail before write; outcome: Polymath, Pegasus, and `rag_pipeline` inputs share one lineage contract and status derives 111 promoted versus zero pending proposals; verification:PASS `test_external_proposal_cannot_bypass_distillation` and intake status | WORKING | retrieval cannot establish authority or silently masquerade as manual knowledge | REQ-002 | register any future origin in both schemas and the external-origin policy | `python3 -m unittest lab.second_brain.tests.test_curate` |
| REQ-007B | Deterministic distillation agent | versioned input, stable decisions, dedup, connected placement, dependencies, refactors, and run ledger | entrypoint: `python3 -m lab.second_brain.src.ingest batch <batch.json>`; wiring: normalized batch to policy `cpcs-distill/1.1` to connected-bundle proof to proposal and run ledgers; outcome: unconnected and loose-pair concepts fail, while structurally nested concepts with an operational bridge stage as one dependency-coherent run; verification:PASS distill, Laban decimal, dependency, idempotency, and bypass tests | WORKING | research can grow the graph without orphan concepts or unsupported truth claims | REQ-003 and REQ-007A | version any policy or threshold change | `python3 -m unittest lab.second_brain.tests.test_distill lab.second_brain.tests.test_curate` |
| REQ-007C | Reviewed bundle promotion | exact per-run durable-ID assignments, dependency order, lineage, and rollback on member failure | entrypoint: `python3 -m lab.second_brain.src.curate bundle <run-id> <assignments.json> --by <curator> --review <review.json>`; wiring: concept and intent members precede edges, mappings, and rules through `promote_proposal`; outcome: every touched curated file is restored when a later member fails in process; verification:PASS `test_bundle_promotion_rolls_back_on_member_failure` | WORKING | connected knowledge cannot be left partially curated by a validation failure | REQ-007B | retain the one-process rollback boundary or add a journal before cross-process recovery is claimed | `python3 -m unittest lab.second_brain.tests.test_curate` |
| REQ-007E | Traceable knowledge expansion | reviewed promotion must become queryable, traversable, and compilable | entrypoint: ingest batch to curate bundle to `reason` and `compile_result`; wiring: proposal lineage persists into curated provenance and typed edge policy feeds traversal; outcome: the generic RAG canary traverses `edge_000001`, emits `motion.laban.space_decimal_hypothesis`, and preserves sources plus the knowledge-gap decision in compiled output; verification:PASS `test_generic_rag_batch_promotes_bundle_and_compiles` | WORKING | distillation affects real reasoning output | REQ-007C | keep the public intake-to-compile canary | `python3 -m unittest lab.second_brain.tests.test_curate` |
| REQ-007D | Full corpus review | terminal progress and source-backed proposals for every retrievable row | entrypoint: Polymath corpus pass; wiring: 3,192 passage fetches into 80 manifest rows; outcome: 78 complete and two failed because the upstream records contain zero chunks; verification: PASS for all retrievable rows | BLOCKED | two sources cannot contribute knowledge | upstream Polymath reingest | reingest the two zero-chunk records | `python3 -m lab.second_brain.src.validate staging` |
| REQ-008A | Honest Pegasus semantic boundary | typed fields, immutable record, and idempotent distilled proposal handoff | entrypoint: `src/pegasus.py`; wiring: prevalidation, exact saved-response hash, immutable append, and shared distillation; outcome: fixture creates one interpreted observation, one distillation run, and one proposal; verification:pass untyped, measured, collision, and direct-staging rejection | WORKING | semantics cannot masquerade as measurements or bypass research governance | REQ-002 and REQ-007B | keep provider transports behind this boundary | `python3 -m unittest lab.second_brain.tests.test_pegasus lab.second_brain.tests.test_curate` |
| REQ-008B | TwelveLabs v1.3 integration | pinned client for stores, uploads, search, embeddings, and Jockey structured output | entrypoint: `src/providers/twelvelabs.py`; wiring: SDK 1.3.1 transport to governed `extract_with_twelvelabs`; outcome: bounded polling, pagination preservation, strict schemas, item-to-asset binding, exact artifact hashes, and failure atomicity; verification:pass fake-client contract tests | WORKING | the provider can be configured without changing repository authority | REQ-008A | keep the research-preview version pinned and reverify on upgrade | `python3 -m unittest lab.second_brain.tests.test_twelvelabs` |
| REQ-008C | Production Jockey extraction | configured credentials, authorized asset, completed response, and immutable production row | adapter doctor reports no API key or configured knowledge store in this environment; no authorized provider asset was supplied; production ledgers remain empty | BLOCKED | no production provider observation exists | API key, dedicated store, and authorized video | run the integrated extraction job | `python3 -m lab.second_brain.src.pegasus extract work/twelvelabs/job.json` |
| REQ-009 | Repository graph and gates | second-brain data in graph and main gate | entrypoint: `build_graph.py` and `validate_repo.py`; wiring: all tiers, routing, distillation, traversal, provider contract, and 23 behavioral tests; outcome: 337-node, 653-edge repository graph; verification:PASS zero-warning gate | WORKING | new files remain governed | REQ-001 through REQ-008B | preserve tier markers and tests | `python3 lab/scripts/validate_repo.py` |

## Directory Contract

`lab/concepts.jsonl` owns curated concepts. `curated/` owns authored edges, rules, intents, and
mappings. `immutable/` owns sealed flights and hash-chained evidence. `derived/` is the reflector's
disposable target. `staging/proposals.jsonl` owns uncertain candidates,
`staging/distillation_runs.jsonl` owns deterministic decision lineage, and
`staging/corpus_manifest.jsonl` owns retrieval progress. `src/distill.py` owns the deterministic
knowledge-growth policy. `src/ingest.py` owns batch admission and effective staging status.
`src/curate.py` alone owns staging-to-curated writes. `src/providers/twelvelabs.py` owns network
transport only. `work/twelvelabs/` owns ignored request and response artifacts. `tests/` owns
behavioral verifiers. External retrieval adapters may submit batches but may not write curated or
proposal stores directly.

## Remediation Order

1. Reingest the two zero-chunk Polymath sources when upstream chunks become available. Exit when
   both manifest rows are `complete`; rollback is not applicable because the manifest is
   resumable staging.
2. Configure a TwelveLabs API key, dedicated knowledge store, and authorized video. Exit when
   `pegasus doctor` reports configuration ready; rollback is deletion of ignored provider
   artifacts only.
3. Run the production extraction, rebuild reflection, and rerun the repository gate. Exit when a
   typed immutable observation and its distillation lineage validate; immutable records have no
   delete rollback.

## Verification Record

- Contracts: 16 Draft 2020-12 schemas validate stores, actor paths, proposal lineage, provider jobs,
  structured semantic responses, and immutable references.
- Intake and distillation: `python3 -m lab.second_brain.src.ingest status` reports three accepted
  external origins, 111 promoted proposals, and zero effective pending proposals. Four production
  runs record 225 decisions. Idempotency, reordered input, duplicate rejection, broken references,
  connected placement, same-batch dependency failure, snapshot replay, and bypass prevention have
  behavioral tests.
- Expansion: a real Polymath passage produced one concept, relationship, and mapping. The isolated
  generic-RAG canary also proves public batch intake, reviewed bundle promotion, typed traversal,
  compiled control output, trace propagation, and rollback after a later member fails.
- Traversal: typed direction canaries, bounded legacy hops, operation-graph retrieval, hybrid
  global-to-local retrieval, and missing-query retrieval signals pass.
- Graphs: the live graph contains 142 nodes and 241 edges. The repository graph contains 337 nodes
  and 653 edges.
- Provider: fake clients verify setup, bounded polling, failure handling, page-token preservation,
  embeddings, Jockey structure, exact artifact hashes, immutable idempotency, and no-write failure.
- Validation: 23 behavioral tests and the full repository gate pass with zero warnings.

## Residual Unknowns

- Two Polymath source records contain zero chunks and cannot be distilled until upstream reingest.
- No TwelveLabs API key, configured knowledge store, or authorized provider video is present.
- Bundle promotion restores files after an exception in one process. Crash recovery across process
  termination is not claimed and would require a curated write journal.
- Legacy runs did not record seeds, compiler versions, output hashes, intent IDs, or concept
  snapshots. Their immutable copies preserve those fields as explicit unknowns.
