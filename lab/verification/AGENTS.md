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
- If artifact checks, conflicts, or unobservable requirements remain, repair is blocked rather than
  partially guessed.

Compliance reports belong under ignored `work/`. They are operational diagnostics, not immutable
experiment evidence until `lab.second_brain.src.record experiment` revalidates their content
identity, build/result/artifact hashes, sealed arm, and human review and appends the controlled run.

## Commands

```bash
python3 -m lab.verification.verify validate
python3 -m lab.verification.verify verify work/build work/render_jobs/<job-id>/render_result.json artifact_000 work/evidence.json
python3 -m unittest discover -s lab/verification/tests -p "test_*.py"
```
