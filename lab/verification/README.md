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
