# CPCS v1 — Architectural Briefing for the Next Expansion

Audience: an external reasoning model / engineer continuing CPCS development.
Branch: `experiment/cpcs-reasoning-layer` (commits `ae19498` → `83fe496` →
`1926874` → `29b0320`). Qualification: CPCS_V1_RELEASE_QUALIFIED +
CPCS_BOOTSTRAP_READY. This document is analysis only — no code was changed to
produce it.

---

## A. CURRENT ARCHITECTURE MAP

| Stage | Purpose | Input | Output | Modules | Status | Extension points |
|---|---|---|---|---|---|---|
| Guided Prompting | session + mode selection (GUIDED/FAST/AUTO), compressed user projection, authority-ordered completion | intent text | GuidedProjectionPacket, CompletionDecisions, final prompt package | `lab/application/cpcs_guided.py`, `cpcs_guided_handlers.py` | EXPERIMENTAL (behind `cpcs.guided.*`) | presentation compression groups; per-beat modular blocks (GAP — see §F) |
| Deliberation (DR-1) | observations, knowledge activation, hypotheses, competition, prerequisites, bounded closure | request + KnowledgeSnapshot | DeliberationPacket (observations, activation, hypothesis set, query plan, updates, closure) | `lab/application/cpcs_deliberation.py` | EXPERIMENTAL | hypothesis types; cascade edges; WORLD_INTERACTION_REASONING hooks (recommended) |
| Knowledge Activation | domain/dimension/affordance activation from retrieved evidence | deliberation packet | KnowledgeActivationPacket | `cpcs_deliberation.py` | EXPERIMENTAL | affordance ledgers (`CPCS_REASONING_AFFORDANCE_LEDGER`, `CPCS_PLANNING_AFFORDANCE_LEDGER`) |
| Hypothesis Generation | requirement/failure/causal/competition/gap hypotheses with structured semantics | activation + snapshot | HypothesisSet | `cpcs_deliberation.py` | EXPERIMENTAL | 16 types frozen; new types additive |
| Query Steering | hypothesis-driven query plan (reason + target + priority, budgeted) | hypotheses | QuerySteeringPlan | `cpcs_deliberation.py` | EXPERIMENTAL | query representations; stop conditions |
| Retrieval | multi-query lanes + hard gate + requirement-local ranking + coverage merge | request | RetrievalEvidencePacket | frozen runtime (`CPCS_FROZEN_RUNTIME_PATH`) via `reasoning_treatment.FrozenRuntimeBackend` | **FROZEN** | none — do not retune |
| Typed Knowledge Mapping (TC-1/TC-2) | deterministic control-type → registry path → structured constructor; D4 (no flat-text admission) | treatment packet | overlays + structured objects (entity_state, interaction, event, temporal, causal, invariant, constraint) | `lab/compiler/cpcs_typed.py`, `reasoning_treatment.TreatmentAdapter` | EXPERIMENTAL | registry entries (19), constructors (12), value sub-schemas (source-native enums) |
| Canonical Controls | typed overlays + structured objects enter the repo score | treatment translation | universal score (canonical authority) | `lab/compiler/score.py` (`make_score_request`/`resolve_score`) | **FROZEN (Control A)** | none |
| Execution Contract (EC-1) | obligations, DirectorControlIR, CanonicalScore, ExpectedStateContract with receipts | retrieval packet | execution packet | frozen runtime `ec1_compiler.py` | **FROZEN** | none |
| Provider Projection (EC-2) | canonical → provider carriers with capability receipts, no semantic redefinition | canonical score | ProviderControlPlan, ProviderGenerationRequest | frozen runtime `ec2_compiler.py` (repo integration has `ProviderProjector` usage) | **FROZEN** | none |
| Capability Resolution (CP-1) | versioned, evidence-backed capability snapshots; UNKNOWN stays explicit | provider request | resolution receipts + fit + readiness | frozen runtime `cp1_resolver.py` | **FROZEN** | capability evidence store only |
| Generation Execution (VG-0/1) | transport executor, pre-flight + dry-run + live gate, immutable receipts | ProviderGenerationRequest | GenerationReceipt, VideoArtifact | frozen runtime `vg0_executor.py` | **FROZEN**; live gate closed (no provider credentials — optional) | none |
| Prompt Compilation | canonical score → provider-neutral carriers (prompt.txt + canonical JSON + verification plan) | build request | `compile_build` artifacts | `lab/compiler/build.py` (`_prompt_and_dispositions`, `_control_line`) | **FROZEN (Control A)** | serialization of beats/actions/interactions (GAP — §F) |
| MCP | stdio JSON-RPC facade over the application service | MCP messages | tool responses | `lab/application/mcp.py`, `service.py` OPERATIONS | **FROZEN** | additive `_register` only |
| Bootstrap | idempotent first-run runtime config + doctor reuse | runtime arg/env/config | machine-local config (0600, no secrets) | `lab/application/bootstrap.py` | EXPERIMENTAL | none |

Inspection notes (verified against the repo):

- `lab/compiler/schemas/universal_score.schema.json` declares `beats`, `actions`,
  `interactions` as `{"type": "array", "items": {"type": "object"}}` — free-form,
  no structured beat/interaction schema (see §C/§F).
- `lab/compiler/build.py::_prompt_and_dispositions` serializes only
  `provider_neutral_controls` as flat lines `[control_id] path = value`; the
  score's `beats`/`actions`/`interactions` are NOT serialized into prompt.txt at
  all. Flat controls survive; structured per-beat structure does not reach the
  carrier.
- The repo's curated second-brain tier is sparse for combat mechanics
  (`curated/mechanisms.jsonl` = 1, `rules.jsonl` = 1, `video_concept_bridges.jsonl`
  = 0). The rich motion/contact/phase knowledge lives in the FROZEN runtime
  corpus (1,775 atomic records, AC-1 semantic linkage, EC-1 control semantics,
  source-native enums such as contact state transitions
  candidate/active/occluded_active/released/contradicted, and the
  `performance.movement_base.phase_model`
  preparation→execution→contact_or_apex→follow_through→recovery).

---

## B. CURRENT CPCS KNOWLEDGE MODEL

Represented:

- **Canonical controls**: 16 CT control types + 19 registry families; typed path
  registry (`cpcs_reasoning_path_registry.yaml` + schema) with semantic kinds
  STATE / RELATION / EVENT / TEMPORAL / CAUSAL / INVARIANT / CONSTRAINT /
  VERIFICATION; deterministic control-type admission (58 rules); D4 forbids
  flat-text admission.
- **Requirements**: 77 reasoning requirements (40 mandatory) with dimensions,
  objectives, failures, depends_on, verification implications; disposition
  coverage 100% (STATE/VERIFICATION/EXPECTED_STATE/GENERATION).
- **Obligations / expected states / verification**: EC-1 execution obligations
  (852 across fixtures), ExpectedStateContract (434) with condition types
  STATE/RELATIONSHIP/EVENT/TRANSITION/PERSISTENCE/NON_OCCURRENCE/TEMPORAL_ORDER/
  CAUSAL_RESULT; verification requirements schema (metric_id, target_paths,
  method, observability, source_profile).
- **Interaction/contact representation**: `cpcs.interaction.contact` structured
  object: participants, roles, interaction_type, contact{mode, semantic,
  geometry, identity, persistence, state_transition(enum)}, temporal_scope,
  phase_scope, continuity_requirements, verification_refs, lineage.
- **Graph traversal**: three bounded forms — (1) graph expansion (retrieval,
  never gates recall), (2) reasoning hops (hypothesis→evidence→prerequisite,
  cascade depth ≤5), (3) query hops (reasoning need→query→evidence, budgeted).
- **MCP ops**: 33+ tools — guided (start/project/answer/finish/revise/inspect),
  session (inspect/history), ideate, deliberate/hypotheses/query/closure inspect,
  doctor, bootstrap, plus the existing baseline surface.

Missing (the representation gap):

- **Beat-scoped causal interaction schema** in the canonical score: no structured
  fields for attacker/defender intent, initiative, center-of-mass relationship,
  support state at beat granularity, load-bearing phase, imbalance (kuzushi)
  phase, rotation/pivot axis, projection path, post-state/recovery. The current
  interaction object carries contact state but not the causal motion graph.
- **Serializer support for beats/actions/interactions**: the compiler emits flat
  control lines; it never renders a per-beat structured block.
- **Curated-tier combat-mechanics content**: the frozen corpus holds the
  knowledge, but the repo-native curated tier (used by Control A) is thin; the
  treatment path (B) reaches the corpus via the frozen runtime, so the knowledge
  exists and is connected for B, not for A.

---

## C. CURRENT VIDEO REASONING CAPABILITY (water-duel evidence)

1. **Character movement** — SOLVED at requirement level: phase_model, joint-limit
   policy, motion phase readability, choreography preservation. FAILING at beat
   level: phase structure is global prose, not per-beat causal segments.
2. **Fighting choreography** — PARTIAL: action-order invariant, combination
   striking, screen direction. FAILING: throw/slam mechanics collapse to generic
   primitives ("throw opponent", "apply force") — the observed double-somersault
   defect (thrower mirrored the rotation) is a support_contact_sequence +
   rotation-axis representation failure, not missing research.
3. **Object interaction** — PARTIAL: possession/ownership states exist; grip
   persistence is asserted globally ("grip persists through the lift") but has no
   beat-scoped contact-interval/force-direction structure.
4. **Environment interaction** — WEAK: water surface is prose ("splashes, carries
   skids"); no environment-response object (deformation, drag, splash event tied
   to impact).
5. **Physics reasoning** — PARTIAL: momentum conservation, support, biomechanics
   are global invariants; no force vectors, COM displacement, or load-transfer
   representation per interaction.
6. **Camera reasoning** — SOLVED: dramatic motivation, impact shake, screen
   direction, visibility at contact.
7. **Continuity** — SOLVED: identity policy, action continuity, screen direction.
8. **Recovery after actions** — WEAK: "recovery_completion" is an invariant name;
   there is no post-state / allowed-recovery-action structure.
9. **Cause/effect chains** — PARTIAL: causal edges exist at requirement and
   trigger granularity; they do not extend into beat-level motion causality
   (entry→off-balance→support-loss→projection→landing).

Why failures happen: knowledge survives ingestion (frozen corpus) and typed
mapping (registry) but is dropped at the canonical-score boundary (free-form
beats/interactions) and at the serializer (flat control lines only). The loss is
at the REPRESENTATION + SERIALIZATION layers — exactly the user's diagnosis.

---

## D. FROZEN SYSTEMS (immutable unless explicitly approved)

- CPCS v1 release contracts (all CPCS_* acceptance artifacts, RQ-1 manifest)
- MCP interface (`lab/application/mcp.py`, OPERATIONS transport contract)
- Guided prompting flow semantics (authority order, FAST policy, revision model)
- Retrieval contracts (frozen runtime, production retrieval contract)
- Canonical score authority model (`score_id` integrity, resolve pipeline)
- D4 evidence admission (no flat-text coercion)
- Provider projection boundary (carriers ≠ canonical controls)
- Control A / CURRENT_BASELINE default

---

## E. WORLD_INTERACTION_REASONING — Architecture Recommendation

Options evaluated:

- **Option A (extend knowledge profiles)**: wrong place. Profiles supply
  defaults; the gap is per-interaction causal structure, which profiles cannot
  express without inventing N field-per-move sprawl.
- **Option B (new reasoning layer above execution planning)**: CORRECT. Add a
  deliberation extension that consumes hypotheses/evidence and emits a
  `StructuredInteractionGraph` per beat; the existing typed mapper then
  materializes it into score structures.
- **Option C (new interaction graph subsystem)**: REJECTED. A parallel graph
  breaks the canonical authority model and duplicates the bounded-traversal
  contract already in place.

Recommended: **Option B, thin**. One new reasoning module
(`cpcs_world_interaction.py`) between DR-1 closure and the typed mapper. It does
not create new authorities: it produces the same registry-family objects
(interaction/event/causal/constraint) with richer, beat-scoped payloads.

Knowledge → WorldModel (entity states) → StateTransition (per beat) →
InteractionReasoning (phases/forces/roles) → MovementControls (typed registry
objects) → PromptSerialization (per-beat blocks).

---

## F. Current vs Desired Representation

Current compile of a hip toss:

```
[control_…] motion.choreography_preservation = true
[control_…] style.protected_invariants = [..., "support_contact_sequence", ...]
```

Desired canonical structure (all in the canonical score, then serialized into
every carrier — NL block, JSON, YAML/XML):

```
interaction: hip_toss_phase1
  roles: {attacker: A, defender: B, initiative: attacker}
  state_before: {attacker_support: water_contact, defender_support: water_contact,
                 grip: B_hip_control_on_A, balance: both_stable}
  phases:
    - entry: {action: underhook_hip_placement, support_shift: lateral}
    - off_balance: {kuzushi: forward_pull, defender_com: displaced}
    - load_bearing: {grip_persists: true, attacker_base: widened,
                     defender_support: lost}
    - projection: {axis: single_axis_rotation, actor_rotating: defender_only,
                   force_vector: {direction: forward_down, magnitude: body_weight}}
  world_response: {water: {deformation: splash, drag: velocity_reduction}}
  state_after: {defender: {momentum: reduced, orientation: changed,
                           balance: unstable}, attacker: {balance: stable}}
  recovery: {allowed: [plant_hand, spin_out], forbidden: [mirrored_somersault]}
  verification_refs: [contact_persistence, no_mirrored_rotation]
```

The key rule: **an output that contains only action labels without state
transition is invalid** (this becomes the evaluation fixture below).

---

## G. Research Extraction Review

- Repo-native curated tier: 132 concepts (66 techniques) — mostly control-plane,
  research-method, and format concepts; combat mechanics coverage is thin
  (only `c_contact_solver`, `c_phase_landmarks`, `c_supporting_path_evaluation`
  are motion-adjacent).
- Frozen runtime corpus: rich (1,775 atomic records with contact states,
  phase models, support states, momentum/force distinctions, ug008 contact
  taxonomy, continuous-combat state machine, granular motion manual). This
  knowledge IS extracted and linked (AC-1 semantic linkage), and it flows into
  Treatment B via the frozen retrieval stack.
- Conclusion: **research exists and is connected for B; the repo-native
  Control-A tier is the thin layer.** The gap is not extraction; it is that the
  extracted knowledge has no beat-scoped canonical schema to land in, and the
  serializer cannot emit it.

---

## H. Implementation Plan (no code yet)

### 1. Recommended subsystem design

New module `lab/application/cpcs_world_interaction.py` (EXPERIMENTAL, additive):

- `StructuredInteractionGraph` builder: per activated interaction hypothesis,
  construct beat-scoped structure from evidence (contact state transition enum,
  phase model, support states) using the deterministic registry constructors —
  no prose synthesis; D4 intact (evidence by ID).
- Runs between DR-1 closure and the typed mapper; consumes the existing
  treatment packet + registry; produces registry-family objects with the richer
  payloads of §F.
- The existing typed mapper (`TreatmentAdapter`) gains a pass that routes these
  richer objects into `interactions[]` / `beats[]` entries of the guided package
  (alongside the score, preserving score_id integrity).

### 2. Required schemas

- `CPCS_STRUCTURED_INTERACTION_SCHEMA_v0.1.json`: roles/intent/initiative,
  state_before, phases (entry, off_balance, load_bearing, projection), contact
  interval, force vector, rotation axis, world_response, state_after, recovery
  (allowed/forbidden), verification_refs, lineage. All fields optional except
  roles + phases + state transitions when the interaction is executed.
- `CPCS_STATE_TRANSITION_SCHEMA_v0.1.json`: before/after entity states +
  transition causes (applied force, support change, grip event) — reusable for
  all interactions, not just throws.
- `CPCS_WORLD_RESPONSE_SCHEMA_v0.1.json`: environment/object responses
  (deformation, splash, drag) linked to the interaction that caused them
  (causal edge, never chronology-only).

### 3. Required graph relationships

Reuse existing predicates — no new graph subsystem:
- interaction → causal edge → world_response
- interaction → temporal relation → beats (ordering)
- interaction → continuity invariant (grip persistence, single-axis rotation)
- entity state → state transition → entity state
- verification requirement → interaction (verification_refs)

### 4. Required MCP operations

Additive only:
- `cpcs.world.interaction.inspect` (diagnostic: per-beat structured graph)
- optionally `cpcs.world.interaction.plan` (operator, read-only)

### 5. Test strategy

- **Evaluation fixture (hip toss)**: input "A fighter performs a hip toss."
  Assert the canonical output contains: contact interval, support state, causal
  phases, actor roles, force transfer, precondition/postcondition, recovery
  state. **Fail if only action labels appear without state transitions.**
- Negative distinction tests: force ≠ momentum; support loss ≠ imbalance;
  mirrored rotation forbidden at projection phase; recovery allowed-set
  enforced.
- Serialization test: the same structured interaction renders consistently in
  NL (per-beat block), JSON, and YAML/XML carriers.
- Regression: full existing suites (Control A, D4, TC-1/2, DR-1, PC-1, MCP).

### 6. Backwards compatibility risks

- **Low**: everything lands in optional score-family fields (free-form objects)
  or the guided package alongside the score; no frozen schemas change; no
  compiler changes; no provider-boundary changes.
- **Watch**: serializer additions must NOT enter Control A's `compile_build`
  path (that is frozen). Per-beat block serialization lives in the guided
  prompt package layer only, unless separately approved for the frozen compiler.
- D4: richer payloads must never smuggle prose into canonical values — all new
  fields are typed/enumerated with evidence IDs in lineage.
- Session/revision semantics unchanged; new reasoning objects participate in
  targeted invalidation via their requirement/evidence lineage.

---

## Summary for the implementer

1. The knowledge exists and is connected for Treatment B (frozen corpus +
   registry). Do not add research.
2. The loss points are: (a) free-form `beats/actions/interactions` in the
   canonical score, (b) the flat control-line serializer, (c) no beat-scoped
   causal interaction schema.
3. Fix = one thin experimental reasoning module (Option B) producing richer
   registry-family interaction objects + additive package-level per-beat
   serialization. Schemas, fixture, tests, and MCP inspect op as specified in
   §H.
4. Do not touch: frozen runtime, retrieval, Control A compiler path, MCP
   transport, authority model, D4.
