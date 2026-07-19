# CPCS-MX Implementation Roadmap

## Phase 0 — contracts and test data

Deliver:

- canonical JSON Schema;
- authoring YAML Schema;
- observation/RAG schemas;
- stable joint-set convention;
- time and coordinate contracts;
- example scores and expected validation results.

Exit checks:

- all examples parse and validate;
- cross-reference and ID checks pass;
- canonicalization produces stable hashes.

## Phase 1 — deterministic authoring resolver

Implement:

- safe YAML parsing;
- profile URI resolution;
- deterministic typed merge;
- unit normalization;
- lock and authority handling;
- import hashing;
- unresolved ambiguity report;
- canonical candidate output.

Exit checks:

- repeated builds are byte-stable after canonical JSON serialization;
- conflicts are reported rather than silently overwritten;
- path traversal and unsafe YAML tags are rejected.

## Phase 2 — rig and motion interchange

Implement:

- BVH parser/import manifest;
- FBX evaluation through a pinned SDK or DCC environment;
- joint semantic map;
- coordinate conversion;
- dense track assets;
- global-pose equivalence tests;
- retarget residual reports.

Exit checks:

- known clips round-trip within declared tolerances;
- Euler order and basis tests catch deliberate misconfiguration;
- contact frames remain aligned after resampling.

## Phase 3 — event, contact, and IK compiler

Implement:

- action/event graph scheduler;
- global/local phase representation;
- contact and support solver;
- full-body IK tasks;
- joint-limit profiles;
- root-policy selection;
- infeasibility reports.

Exit checks:

- locked foot and hand constraints pass in synthetic tests;
- minimal conflicting constraint sets are reported;
- no silent anatomical or rig-safe limit violation.

## Phase 4 — performance layers

Implement:

- Laban descriptor intervals and proxy profiles;
- FACS-like AU tracks;
- gaze and head coordination;
- breath phrase generator;
- mannerism/profile composition;
- microvariation with deterministic seeds.

Exit checks:

- action content remains constant across performance ablations;
- profile changes are measurable and reversible;
- proxy fields retain calibration/version metadata.

## Phase 5 — style and superhuman transforms

Implement typed transforms for:

- phase-specific timing;
- arcs and silhouette;
- virtual gravity/impulse/damping;
- deformation and smear geometry;
- holds, impact frames, VFX, and camera emphasis;
- invariant enforcement.

Exit checks:

- natural-to-anime transformation preserves action order and contacts;
- rig-safe limits remain intact when stylized reach increases;
- virtual physics and presentation changes are separately inspectable.

## Phase 6 — target adapters

Prioritize:

1. DCC/engine rig export;
2. pose-control video generation;
3. text-to-motion sparse joint control;
4. image/video generation with masks and trajectories;
5. compositor and edit package.

Every adapter returns:

- native fields;
- approximated fields;
- postprocessed fields;
- unsupported fields;
- target package hashes;
- verification plan.

## Phase 7 — closed-loop verification

Implement:

- output pose/face/camera extraction;
- event alignment;
- trajectory and contact metrics;
- foot-slip and joint-limit checks;
- Laban/performance proxy evaluation;
- human review interface;
- localized control revision.

Exit checks:

- known injected errors are detected;
- thresholds are immutable per experiment run;
- unobservable fields are marked inconclusive.

## Phase 8 — research evaluation

Run the ablation suite described in the paper across:

- natural locomotion;
- realistic UGC;
- staged two-character action;
- anime/superhuman motion.

Publish accepted and failed candidates, metric definitions, source scopes, and statistical analysis.
