# Render verification operating contract

Read `../../AGENTS.md`, `../AGENTS.md`, `../registry.yaml`, `../compiler/AGENTS.md`,
`../runtime/AGENTS.md`, and `../second_brain/AGENTS.md` first. This directory alone owns
provider-neutral render compliance, diagnosis, and repair planning.

## Boundary

`verify.py` accepts a byte-valid compiler build, a schema-valid runtime result, the exact rendered
artifact, and a self-contained evidence bundle. It locally probes the artifact, evaluates the
compiler's verification plan, preserves semantic, measured, and human-review lanes, and emits
`cpcs.compliance_report/1.0`.

- Artifact identity, duration, aspect ratio, resolution, and frame rate are checked locally.
- Assertions cite embedded source records by content hash. Normalized Pegasus and local-measurement
  records must match the rendered artifact hash.
- Asset preparation revalidates the exact render bytes. Score-compliance analysis jobs contain only
  compiler-declared semantic metric, method, and target-path tuples. Their observations become
  assertions deterministically; unobservable assessments remain source evidence.
- Closed deterministic measurement methods compute their own verdict from the cited record and
  reject caller-supplied verdicts. Product-visibility duty cycle and per-hand average 2D path
  curvature are implemented. Curvature reports image-space measurement completion, not creative
  superiority or three-dimensional body motion.
- The required observability lane decides a metric. Evidence from another lane remains visible but
  cannot substitute for the required lane.
- Opposing semantic and measured verdicts become an unresolved conflict; confidence is never
  averaged and one lane never silently overrides another.
- Missing evidence becomes `unobservable`; missing human review becomes `review_required`.
- Repair actions may only reassert values already present in the canonical score. They cannot
  invent controls, mutate the score, compile a provider prompt, rerender, or write knowledge.
- Reference round-trip comparison accepts two existing `cpcs.measurement_batch/1.0` records, an
  explicit one-to-one actor mapping, caller-declared thresholds, and one exact build/render/artifact
  identity. It requires identical detector settings, binds the generated batch to the retrieved
  artifact bytes, phase-aligns requested tracks, and emits `cpcs.reference_round_trip_report/1.0`.
  The report is 2D detector evidence, not motion-capture truth, camera separation, or a creative
  quality verdict.
- Reference-candidate side-by-side comparison accepts two exact authorized local videos, optional
  hash-bound ASR and pose artifacts, explicit actor mapping and thresholds, and declared semantic,
  local-visual, or human-review assessments. It detects cuts with the declared FFmpeg scene
  threshold, compares duration-normalized edit timing, speech pace and pauses, and selected 2D
  track speeds, then emits an operational report plus an optional time-normalized left/right sheet.
  Reference-derived controls remain unreviewed candidates and cannot qualify a render or write
  knowledge.
- When both sides provide hash-bound VOG artifacts, the same comparison validates each source
  boundary, requires identical analysis profiles, aligns observations by normalized interval,
  profile, and semantic layer, and reports exact matching, diverging, conflicting, or unobservable
  structured claims. It does not treat paraphrases as equal, average confidence, merge the graphs,
  or write either graph into research authority.
- If artifact checks, conflicts, or unobservable requirements remain, repair is blocked rather than
  partially guessed.

Compliance reports belong under ignored `work/`. They are operational diagnostics, not immutable
experiment evidence until `lab.second_brain.src.record experiment` revalidates their content
identity, build/result/artifact hashes, sealed arm, and human review and appends the controlled run.

## Commands

```bash
python3 -m lab.verification.verify validate
python3 -m lab.verification.verify verify work/build work/render_jobs/<job-id>/render_result.json artifact_000 work/evidence.json
cpcs verify.reference.roundtrip --role operator --input work/reference-round-trip.json
cpcs verify.reference.compare --role operator --input work/reference-candidate-comparison.json
python3 -m unittest discover -s lab/verification/tests -p "test_*.py"
```
