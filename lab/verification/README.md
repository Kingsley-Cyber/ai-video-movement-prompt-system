# CPCS render verification

This subsystem closes the local build-to-render comparison boundary without pretending that one
evidence source is ground truth. It combines exact media metadata with source-cited assertions from
Pegasus semantics, local measurements, or explicit human review.

The output identifies the failed metric, canonical control, artifact interval, observed deviation,
and evidence references. A repair plan can only reassert an existing canonical value at the failed
artifact or interval. Every unrelated control is listed as preserved. Conflicts, missing required
lanes, and failed artifact integrity checks block automatic repair.

The verifier does not invoke a semantic model. `pegasus.score_compliance/1.0` is the governed
semantic analysis profile; its normalized observations must be converted into source-cited metric
assertions before this deterministic boundary evaluates them. Similarity or model confidence alone
does not establish compliance.

Reports remain ignored operational artifacts until a schema-valid
`cpcs.experiment_receipt/1.0` passes `python3 -m lab.second_brain.src.record experiment`. That
recorder revalidates the exact build, render result, artifact, report identity, sealed arm, metrics,
and human review before appending immutable evidence.
