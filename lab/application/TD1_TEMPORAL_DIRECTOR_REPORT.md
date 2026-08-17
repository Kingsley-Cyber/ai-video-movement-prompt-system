# TD-1 — Temporal Director / Beat Budget Report

Stage result: **ACCEPTED** (all critical criteria pass; recorded gaps are
honest REPRESENTATION_GAPs, not filled with guesses).

## What shipped

- `cpcs_temporal_director.py` — deterministic causal-first scheduler:
  `TemporalDirectingPlan` + `AtomicUnitSchedule` (declared policy
  parameters: allocation quantum 0.05s, compression threshold 0.1s —
  neither is an evidence-backed readability minimum), causal DAG from
  SI-1 unit ordering, overlap eligibility = no-directed-path pairs,
  weight-proportional allocation from structured consequence signals,
  feasibility verdicts, compression decisions, `validate_temporal_plan`.
- Guided flow: optional `duration_seconds` on `cpcs.guided.start`
  (additive); without a duration the plan is TEMPORALLY_UNDERSPECIFIED
  (no fabricated seconds). The plan travels as a sidecar
  (`deliberation["temporal_directing_plan"]`); Control A and the
  provider boundary untouched.
- Placement: consequence-anchored intermediate fallback (evidence
  overlap → shared failure families → all units) for unit binding.
- Artifacts: `TD1_TEMPORAL_CAPABILITY_AUDIT_BEFORE_v0.1.json`,
  `TD1_TEMPORAL_POLICY_v0.1.json`, `TD1_REAL_RUNTIME_DIAGNOSTICS_v0.1.json`.

## Real-runtime results (computed)

| Case | Feasibility | Scheduled | Compression | Env-bound units |
|---|---|---|---|---|
| FIGHT 3s | FEASIBLE_WITH_COMPRESSION | 18 | 6 | 12 (0.22s each) |
| FIGHT 6s | FEASIBLE | 18 | 0 | 12 (0.44s each) |
| FIGHT 10s | FEASIBLE | 18 | 0 | 12 (0.74s each) |
| FIGHT no duration | TEMPORALLY_UNDERSPECIFIED | 0 | 0 | 0 |
| UGC_SERUM 10s | FEASIBLE | 15 | 0 | 10 |
| DIALOGUE 6s | FEASIBLE | 16 | 0 | 8 |
| MANIPULATION 6s | FEASIBLE | 17 | 0 | 10 |
| DRONE 6s | FEASIBLE | 19 | 0 | 14 |

- Different budgets produce materially different allocations and
  verdicts (3s compresses; 6s/10s do not).
- Causal ordering preserved everywhere (verified by
  `validate_temporal_plan` + tests).
- Water-impact units receive real intervals scaling with budget.
- No total duration → no fabricated seconds (H criterion).
- Hardness is never silently compressed away — compression is flagged,
  never silent.

## Honest gaps (recorded, not guessed)

1. REPRESENTATION_GAP: no grounded numeric readability minimums exist
   for any event class → READABILITY_CRITICAL flags + policy parameters
   only; no invented constants.
2. REPRESENTATION_GAP: which specific unit IS "the water impact"
   remains imprecise — env-bound units number 12 because region-level
   evidence unions dilute control-level anchoring (the pack-level
   document-mixing residual). Fixed by record-anchored packs (owner
   decision), not by scheduler tuning.
3. REPRESENTATION_GAP: RECOVERY role / FACS onset-apex-offset /
   stage-vs-presentation time remain unsupported by the frozen
   runtime; TD-1 preserves symbolic lifetimes without numeric
   realization.
4. No provider-specific timing claims; provider realization is
   downstream (carrier serialization deferred).

## Frozen boundaries

KA-2.3 region identity and KA-2.4 recruitment hashes unchanged
(recorded in the diagnostics artifact). SI-1 semantics unchanged.
Control A unchanged. D4 preserved. No retrieval/top-100 changes.
Full regression + repo gate green at commit.
