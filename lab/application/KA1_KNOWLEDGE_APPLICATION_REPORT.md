# KA-1 Knowledge Application Bridge — Implementation Report

Readiness: `CPCS_KNOWLEDGE_APPLICATION_READY`

Acceptance: `CPCS_KA1_ACCEPTANCE_v0.1.json` = PASS (computed, all 10 gates green).

## 1. What was built

The missing block between DR-1 deliberation and typed mapping now exists:

```
DR-1 -> Knowledge Application Bridge (cpcs_knowledge_application.py)
     -> TreatmentAdapter / Typed Mapping -> CanonicalScore
```

- `PrinciplePack` — one research principle bound to its mechanism, predicted
  failure, and evidence (IDs only, D4).
- `RepresentationDecision` — CONTROL | VERIFICATION | PLANNING |
  NON_EXECUTABLE | COMPOSITE, with authority, target family, forbidden
  coercions, and verification counterpart.
- `KnowledgeApplicationSet` — authority-ordered applications with preserved
  competition groups, fail-closed unknowns, and content-derived set hash.
- Adapter pass — VERIFICATION decisions route to verification requirements;
  PLANNING to `planning_guidance`; NON_EXECUTABLE to `reasoning_material`;
  none of it enters the resolved canonical score (score_id integrity).
- Structured interaction payload — beat-scoped `roles / state_before /
  contact_interval / phases / projection / state_after / recovery /
  world_response` with source-native enum vocabularies, plus a state-transition
  gate (`validate_structured_interaction`) that rejects action-label-only
  output.
- `cpcs.knowledge.apply.inspect` MCP op (chat, read-only, fail-closed without
  the frozen runtime) + `knowledge_application` doctor line.

## 2. Cross-domain fixtures (hermetic, computed)

| Fixture | Packs | Decision mix | Risk tokens | Mechanism tokens |
|---|---|---|---|---|
| COMBAT "A fighter performs a hip toss." | 3 | COMPOSITE 1, CONTROL 1, NON_EXECUTABLE 1 | mirrored_rotation | force_transfer_chain, phase_model |
| ECOMMERCE "A person unboxes a luxury watch." | 3 | COMPOSITE 1, CONTROL 2 | logo_visibility_loss | identity_visibility |
| COOKING "A chef slices a tomato." | 3 | COMPOSITE 2, NON_EXECUTABLE 1 | hand_safety | cut_deformation |

Decision mixes differ across domains — the bridge is intent-conditioned, not
one fixed interaction template with different nouns.

## 3. Cross-domain fixtures (real frozen runtime, computed)

100 retrieved evidence records per intent (retrieval budget), 0 unknowns:

| Fixture | COMPOSITE | CONTROL | PLANNING | NON_EXECUTABLE | VERIFICATION |
|---|---|---|---|---|---|
| COMBAT | 4 | 15 | 45 | 35 | 1 |
| ECOMMERCE | 3 | 14 | 49 | 33 | 1 |
| COOKING | 6 | 17 | 43 | 31 | 3 |

Determinism: two full real-runtime bridge runs per fixture produce identical
set hashes.

## 4. Before / after: generic throw vs structured interaction

Before (Control A, flat control lines only):

```
[control_…] motion.choreography_preservation = true
[control_…] style.protected_invariants = [..., "support_contact_sequence", ...]
```

After (structured interaction object, canonical and beat-scoped):

```json
{
  "roles": {"attacker": "fighter_a", "defender": "fighter_b",
            "initiative": "fighter_a"},
  "state_before": {"attacker_support": "stable", "defender_support": "stable",
                   "grip": "hip_grip", "balance": "stable"},
  "contact": {"contact_interval": {"interval_s": [1.5, 2.5],
              "mode_sequence": ["impact", "pivot", "support"]}},
  "phases": [
    {"action": "underhook_hip_placement", "support_shift": "lateral", "..."},
    {"action": "forward_pull", "com_displacement": "displaced", "..."},
    {"action": "load_bearing", "support_lost": true, "..."},
    {"action": "projection", "support_lost": true, "..."}
  ],
  "projection": {"rotation_axis": "single_axis",
                 "rotating_actor": "defender_only",
                 "force_vector": {"direction": "forward_down",
                                  "magnitude": "body_weight"}},
  "state_after": {"defender": {"balance": "unstable"},
                  "attacker": {"balance": "stable"}},
  "recovery": {"allowed": ["plant_hand", "spin_out"],
               "forbidden": ["mirrored_rotation"]},
  "world_response": {"water": {"deformation": "splash",
                               "drag": "velocity_reduction"}}
}
```

The mirrored-rotation defect (both actors somersaulting) is now explicitly
forbidden at the projection phase and recoverable at the gate level: an
action-label-only output fails `validate_structured_interaction`.

## 5. Frozen boundaries preserved

- Retrieval, ranking, and gating: untouched (frozen runtime read-only).
- Control A (`build.py` / `score.py`, CURRENT_BASELINE): unchanged; full
  application, compiler, and second-brain suites green.
- D4: evidence by ID everywhere; hostile-prose probes rejected; no record
  prose appears in any pack or translation output.
- Authority order: decision authorities are a strict subset of the frozen
  seven-tier order; ordering is authority-consistent.
- Score immutability: planning guidance and reasoning material travel
  alongside the score; the resolved score is never mutated post-resolution.
- MCP transport: one additive `_register` op only.
- TC-1/TC-2 distinctions: all residual-closure and typed-coverage suites
  remain green; non-executable universal types can never yield CONTROL.

## 6. Remaining gaps (explicit, not hidden)

- Provider serialization of structured interactions is NOT part of KA-1; the
  canonical objects live in the guided package alongside the score. Emitting
  them into carriers remains a separate, separately-approved compiler change
  (Control A is frozen).
- The state-transition gate is asserted in tests and exposed as
  `validate_structured_interaction`; wiring it as a hard block inside the
  adapter would change existing translation semantics and was deliberately
  not done.
- Real-runtime enum grounding: structured interaction payloads populate only
  from source-native enums; when the frozen corpus carries no value for a
  field, the field stays None rather than inventing prose.
- The A/B experiment prepare handler (`handler_reasoning_experiment_prepare`)
  mutated its resolved arm-B score before compiling (pre-existing, outside
  KA-1 scope). FIXED in the follow-up commit "fix(cpcs): preserve experiment
  arm score identity": treatment data now travels as arm-sidecar fields and
  both arms compile with valid score identity (regression-covered).

## 7. Acceptance evidence

- `CPCS_KA1_ACCEPTANCE_v0.1.json` — PASS, computed by
  `python3 -m lab.application.ka1_acceptance`:
  bridge_operational, representation_decisions_correct,
  hip_toss_state_transition_required, cross_domain_fixtures_pass,
  D4_preserved, control_a_unchanged, mcp_doctor_integrated,
  real_runtime_smoke_pass, all_pre_ka_suites_pass, all_artifacts_valid.
- `CPCS_KNOWLEDGE_APPLICATION_FIXTURES_v0.1.json` — computed hermetic fixture
  artifact.
- KA-1 tests: `test_ka1_schemas` (10), `test_ka1_structured_interaction` (5),
  `test_ka1_principle` (8), `test_ka1_representation` (8),
  `test_ka1_application_set` (8), `test_ka1_adapter` (6), `test_ka1_mcp` (4),
  `test_ka1_fixtures` (7) — 56 tests, plus the pre-KA regression group and the
  full application/compiler/second-brain suites.
