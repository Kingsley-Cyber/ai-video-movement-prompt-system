# CPCS render verification

This subsystem closes the local build-to-render comparison boundary without pretending that one
evidence source is ground truth. It combines exact media metadata with source-cited assertions from
Pegasus semantics, local measurements, or explicit human review.

The output identifies the failed metric, canonical control, artifact interval, observed deviation,
and evidence references. A repair plan can only reassert an existing canonical value at the failed
artifact or interval. Every unrelated control is listed as preserved. Conflicts, missing required
lanes, and failed artifact integrity checks block automatic repair.

The verifier does not invoke a semantic model. It prepares the exact rendered-artifact upload job
and a `pegasus.score_compliance/1.0` job closed to compiler-declared semantic metrics and target
paths. After the application executes those authorized provider jobs, the verifier converts their
normalized observations into source-cited assertions deterministically. Unobservable assessments
remain evidence without becoming pass or fail. Similarity or model confidence alone does not
establish compliance.

For two already downloaded authorized videos, `cpcs.verify.reference.compare` owns the broader
operational side-by-side diagnostic. It hash-checks both media files and optional ASR or pose
artifacts, detects cuts with a declared FFmpeg threshold, compares normalized edit timing, speech
pace, pauses, and selected 2D motion speeds, preserves semantic, local-visual, and human findings,
and can render a reference-left/candidate-right contact sheet. Its derived targets are review
candidates, not canonical score values, curated knowledge, or release qualification.

Reports remain ignored operational artifacts until a schema-valid
`cpcs.experiment_receipt/1.0` passes `python3 -m lab.second_brain.src.record experiment`. That
recorder revalidates the exact build, render result, artifact, report identity, sealed arm, metrics,
and human review before appending immutable evidence.

## Visible initiation order

`python3 -m lab.verification.verify compare-initiation work/initiation-request.json`
compares one declared actor/beat chain against an existing content-valid pose batch. It reads
no video, extracts no pose, and calls no provider. `tests/test_initiation_order.py` contains
synthetic requests and the pinned five-outcome acceptance cases.

The closed `cpcs.initiation_order_request/1.0` input contains `declaration` (actor, beat ID,
interval and initiation chain: kind, root, ordered joint path, pattern), its
`declaration_sha256`, `measurement_batch`, its `measurement_sha256`, and a `camera`
condition (`motion`: fixed, ambiguous or unknown; `basis`: caller_declared). Optional
`calibration` has `onset_tolerance_s` and `visibility_threshold`. Either unset input
produces `uncalibrated`; there are no production values. The existing batch validator
checks detector/source lineage and content identity. Supplied verdicts are rejected.

Onset is the first sampled coordinate change from the beat's initial position. Its window
spans the preceding unchanged sample and the changed sample. Every required joint must
cover the declared beat, remain visible at the explicit threshold and belong to the same
actor. A reversed required pair yields `reversed`; fully separated forward windows yield
`ordered`; overlapping or tolerance-indistinguishable windows yield `indistinguishable`.
Missing tracks/onsets, identity uncertainty or ambiguous camera conditions yield
`unobservable`. The report retains each window, pair result and exact input hashes.

This diagnostic compares the declared path order, including a path declared simultaneous;
it does not certify a movement vocabulary, compliance with simultaneity, force transfer,
Bartenieff coding, or video quality. Fixed camera is caller-declared, not proven by these
tracks. No noise floor is inferred. Real-render use remains unqualified.
