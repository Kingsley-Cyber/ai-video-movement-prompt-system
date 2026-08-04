# Codebase Intent Gap Analysis

> Historical Slice 11 audit retained for decision lineage. The current completion matrix,
> implementation state, and post-Slice-17 gaps are owned by `../../ARCHITECTURE.md`.

**Verdict:** BLOCKED
**Core distillation verdict:** PASS
**Traversal-gate verdict:** PASS
**Repository:** `/Users/king/Documents/New project`
**Plan:** `/Users/king/.codex/attachments/0aed1997-d7e3-4c81-aa23-f34890b9a0e3/pasted-text-1.txt`, SHA-256 `419ef089a00a2f2b4e664edb916ea6158f408046e0b6a4f2243069b43ab3f43c`
**Revision:** Slice 11 local implementation on `codex/render-verification-slice-11`, based on integrated Slice 10
**Audited at:** `2026-08-03`

The local research-to-traversal lifecycle is implemented. It accepts Polymath, Pegasus, and generic
RAG batches; rejects direct external staging; distills connected proposal sets; promotes a reviewed
run with rollback on member failure; traverses the new typed edge; and compiles the new mapping.
The full mission remains blocked by external acceptance evidence: two Polymath records expose zero
chunks, and this environment has no TwelveLabs API key or authorized production provider asset.
The complete provider-neutral fake-client cascade is working; it is not a substitute for live
provider qualification. A journaled render runner now reaches the generation-provider boundary
without authority writes, but its Veo transport is also awaiting live credentials and an authorized
build. A separate verifier now produces deterministic, source-traceable compliance and bounded
repair diagnostics without recording them as evidence or changing authority.

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

`lab/runtime/` now revalidates the compiler's exact eight-file build, binds one idempotency key in a
single-writer SQLite journal, leases one worker, captures the prepared request and operation receipt,
polls only the matching operation, retrieves content-hashed artifacts, and emits
`cpcs.render_result/1.0`. A receipt-first crash resumes without another submit. A potentially
accepted submission with no receipt becomes `submission_unknown` and can only continue after an
operator reconciles a provider operation. OAuth tokens are transport-only and are absent from the
journal and captured artifacts.

`lab/verification/` now checks the exact build, runtime result, MP4 bytes, local media metadata,
embedded normalized observations, human reviews, and content-derived assertions. It preserves
semantic and measurement disagreements, marks absent lanes unobservable, deterministically
computes product-visibility duty cycle, and can only reassert an existing canonical control at the
failed artifact interval. Compliance reports remain ignored diagnostics until a later experiment
recorder admits them.

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

`src/providers/twelvelabs/` pins SDK 1.3.1 and separates assets, Pegasus Analyze, Segment, Batch,
knowledge-store Search, Jockey Responses, and Marengo embeddings from repository writes.
`src/pegasus.py` validates seven distinct job contracts plus the source-bounded cascade. It verifies
local bytes and `ffprobe` timing, saves exact requests before provider execution, validates raw and
normalized artifacts, fuses semantic and local-measurement lanes into a contradiction-preserving
VOG, reverse-compiles only through `lab/compiler/score.py`, and appends one immutable semantic row
after the full cascade succeeds. Every Pegasus knowledge proposal still enters `src/distill.py`;
direct staging fails validation and promotion.

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
| REQ-008A | Honest media-observation boundary | typed semantic and measurement rows, source-bounded VOG, preserved contradictions, immutable record, and idempotent handoff | entrypoint: `src/video_observation.py`, `src/pegasus.py`, and `lab/compiler/reverse.py`; wiring: source hash and interval validation to normalized observations to VOG to canonical score to final append; outcome: fake-client source produces deterministic VOG and score IDs, retains semantic/measurement conflicts, and appends exactly once; verification:PASS cascade, observation, reverse, and legacy-ingest tests | WORKING | semantics cannot masquerade as measurements or bypass the universal kernel | REQ-002 and REQ-007B | keep provider transports and measurement confidence separate | `python3 -m unittest lab.second_brain.tests.test_video_observation lab.second_brain.tests.test_pegasus_cascade lab.compiler.tests.test_reverse` |
| REQ-008B | TwelveLabs v1.3 surface integration | pinned, distinct contracts for assets, Analyze, Segment, Batch, Search, Jockey, and Marengo | entrypoint: `src/providers/twelvelabs/`; wiring: SDK 1.3.1 transports to seven strict job schemas and a closed 14-profile catalog; outcome: exact and clipped Analyze isolation, Segment envelopes, all-or-nothing Batch, item-filtered Search, selected-item Jockey, embeddings, saved request/raw artifacts, and local renormalization; verification:PASS fake-client surface tests | WORKING | callers cannot confuse search, corpus reasoning, segmentation, or direct analysis | REQ-008A | reverify pinned contracts on SDK upgrades | `python3 -m unittest lab.second_brain.tests.test_twelvelabs` |
| REQ-008C | Production Pegasus qualification | installed SDK, configured API key, authorized asset, completed Analyze and Segment responses, VOG, reverse score, and immutable production row | adapter doctor reports the SDK and API key absent in this environment; no authorized production asset was supplied; production ledgers remain empty | BLOCKED | provider compatibility and real output quality remain unproven | API key and authorized video | execute the bounded runbook and archive ignored request/raw evidence | `python3 -m lab.second_brain.src.pegasus cascade work/twelvelabs/cascade.json --intent-context work/twelvelabs/intent-context.json --score-assets work/twelvelabs/score-assets.json` |
| REQ-009 | Repository graph and gates | second-brain data in graph and main gate | entrypoint: `build_graph.py` and `validate_repo.py`; wiring: all tiers, routing, distillation, traversal, provider contracts, VOG, reverse compiler, 59 second-brain tests, and 28 compiler tests; outcome: 337-node, 653-edge repository graph; verification:PASS zero-warning gate | WORKING | new files remain governed | REQ-001 through REQ-008B | preserve tier markers and tests | `python3 lab/scripts/validate_repo.py` |
| REQ-010 | Journaled generation execution | one secret-free, idempotent, resumable job validates a build, submits once, polls, retrieves, normalizes, hashes, and records operational lineage without writing authority | entrypoint: `python3 -m lab.runtime.runner`; wiring: build integrity to SQLite lease and event chain to shared adapter lifecycle to `cpcs.render_result/1.0`; outcome: kill after receipt capture resumes with one submission, an active second writer is denied and an expired lease is recoverable, ambiguous submission never retries and can be reconciled, safe operations retry, deadlines and cancellation dispositions persist, artifacts are hashed, and credentials do not persist; verification:PASS eight runtime tests, but no live Veo operation exists | PARTIAL | the local execution boundary is recoverable, while live compatibility and remote cancellation remain unproven | REQ-009 and one authorized provider build | run one approved live Veo operation; retain `submission_unknown` because the provider exposes no documented idempotency key | `python3 -m unittest discover -s lab/runtime/tests -p "test_*.py"` |
| REQ-011 | Render compliance and bounded repair | one provider-neutral report binds the build, render, artifact, required evidence lanes, failed controls, conflicts, locations, deviations, and smallest safe repair | entrypoint: `python3 -m lab.verification.verify verify`; wiring: exact media probe and source-hashed assertions to required-lane adjudication to closed product-visibility and per-hand 2D-curvature comparators to existing-control-only repair; outcome: semantic-measurement conflicts remain unresolved, missing lanes stay unobservable, paired wrist tracks produce source-cited curvature, and a seeded measured failure produces one interval action while every unrelated control is preserved; verification:PASS eight replay, read-only, curvature, failure, conflict, lane, tamper, and bypass canaries | WORKING | render diagnostics no longer require unstructured agent judgment or invented repair values | REQ-010 and typed semantic or measurement evidence | add a comparator only with an explicit measurable input contract; record the report through a separate experiment boundary | `python3 -m unittest discover -s lab/verification/tests -p "test_*.py"` |

## Directory Contract

`lab/concepts.jsonl` owns curated concepts. `curated/` owns authored edges, rules, intents, and
mappings. `immutable/` owns sealed flights and hash-chained evidence. `derived/` is the reflector's
disposable target. `staging/proposals.jsonl` owns uncertain candidates,
`staging/distillation_runs.jsonl` owns deterministic decision lineage, and
`staging/corpus_manifest.jsonl` owns retrieval progress. `src/distill.py` owns the deterministic
knowledge-growth policy. `src/ingest.py` owns batch admission and effective staging status.
`src/curate.py` alone owns staging-to-curated writes. `src/providers/twelvelabs/` owns network
transport only. `work/twelvelabs/` owns ignored request and response artifacts. `tests/` owns
behavioral verifiers. `lab/runtime/` owns provider execution code; its SQLite journal and render
artifacts live only under ignored `work/render_jobs/`. `lab/verification/` owns read-only compliance
and bounded repair; its reports stay under ignored `work/`. External retrieval, generation, and
verification adapters may not write curated, immutable, derived, or staging stores directly.

## Remediation Order

1. Define the immutable experiment record that binds one compliance report to the build, score,
   provider, seed, tested delta, artifact, metrics, and human verdict without granting the verifier
   record authority.
2. Qualify the render runner against one authorized Veo build and Application Default Credentials.
   Exit when one operation submits, polls, retrieves, hashes, and validates without secret capture;
   rollback is deletion of ignored runtime artifacts, not remote provider cancellation.
3. Reingest the two zero-chunk Polymath sources when upstream chunks become available. Exit when
   both manifest rows are `complete`; rollback is not applicable because the manifest is
   resumable staging.
4. Configure a TwelveLabs API key and authorized video; configure a dedicated knowledge store only
   for Search or Jockey. Exit when `pegasus doctor` reports analysis ready; rollback is deletion of ignored provider
   artifacts only.
5. Run the production extraction, rebuild reflection, and rerun the repository gate. Exit when a
   typed immutable observation and its distillation lineage validate; immutable records have no
   delete rollback.

## Verification Record

- Contracts: 33 Draft 2020-12 schemas validate stores, actor paths, proposal lineage, seven provider jobs, the profile catalog, Pegasus and source-cited Jockey responses, normalized observations, the VOG, and cascade,
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
- Provider: fake clients verify upload, exact/clipped Analyze, Segment, all-or-nothing Batch,
  item-filtered Search, selected-item Jockey, Marengo, VOG fusion, reverse compilation, exact artifact
  hashes, immutable idempotency, raw-response renormalization, and no-write failure.
- Render runtime: eight canaries verify single-writer idempotency, active-lease exclusion and
  expired-lease recovery, receipt-first kill and resume, ambiguity quarantine and reconciliation,
  safe retry, deadline, cancellation dispositions, fail-closed status handling, complete build and
  event validation, artifact hashing, and token non-persistence.
- Render verification: eight canaries verify artifact metadata, source and assertion hashes,
  deterministic product-visibility and per-hand 2D-curvature comparison, evidence-lane conflicts and gaps, bounded repair,
  unrelated-control preservation, replay, tamper rejection, and no authority mutation.
- Validation: 69 second-brain tests, 28 compiler tests, eight runtime tests, eight verification tests, 14 application tests, seven release tests, and the full repository gate pass with zero warnings.

## Residual Unknowns

- Two Polymath source records contain zero chunks and cannot be distilled until upstream reingest.
- No TwelveLabs API key or authorized production provider video is present; live Analyze and Segment
  response compatibility remains unqualified.
- `google-auth` and ADC are absent, and no live Veo submit, poll, retrieval, or remote cancellation
  has been demonstrated. The documented API provides no request idempotency key or Veo cancel method.
- Product visibility is the only closed deterministic score metric. Other metric methods still need
  typed comparators or source-cited semantic or human assertions and remain unobservable otherwise.
- Bundle promotion restores files after an exception in one process. Crash recovery across process
  termination is not claimed and would require a curated write journal.
- Legacy runs did not record seeds, compiler versions, output hashes, intent IDs, or concept
  snapshots. Their immutable copies preserve those fields as explicit unknowns.
