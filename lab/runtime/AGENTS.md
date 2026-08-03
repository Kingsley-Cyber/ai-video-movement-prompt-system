# Render runtime operating contract

Read `../../AGENTS.md`, `../AGENTS.md`, `../registry.yaml`, and `../compiler/AGENTS.md` first. This
directory is the sole owner of journaled provider submission, polling, retrieval, and normalized
render results. It has no directing, curation, scoring, compilation, or immutable-evidence authority.

## Boundary

`runner.py` accepts only a byte-validated build directory produced by `lab/compiler/build.py`. It
registers one secret-free `cpcs.render_job/1.0` in an ignored SQLite journal, leases it to one writer,
and executes the adapter lifecycle `validate → prepare → submit → poll → retrieve → normalize →
cancel`. Runtime artifacts and journal databases stay under `work/render_jobs/` and are never
repository truth.

- Idempotency keys bind one immutable job input. Reuse with different input fails.
- A provider request is captured before submission; an operation receipt is fsynced before the
  journal advances to `submitted`.
- Resume never repeats a known submission. A crash with no persisted receipt becomes
  `submission_unknown` and requires explicit reconciliation.
- Only safe poll and retrieval operations retry. The Veo endpoint has no documented server-side
  idempotency key, so ambiguous submission errors are never retried automatically.
- The prepared request preserves the compiler-owned content exactly; its closed schema has no
  credential carrier. OAuth credentials are injected only at transport time. Secret-shaped fields
  are refused in job input, and provider responses plus journal events are recursively redacted.
- Result artifacts are content-hashed and checked against the compiled sample count. Recording them
  into the second brain is a later, explicit evidence operation.
- The shared adapter interface cannot alter prompts, controls, scores, provider requests, or
  knowledge. A provider adapter is a transport projection only.

Google documents polling for Veo `predictLongRunning` through `fetchPredictOperation`, but no
Veo-specific remote-cancel method. The adapter therefore reports cancellation as unsupported and
warns that stopping local polling does not prove provider cancellation or prevent charges.

## Commands

```bash
python3 -m lab.runtime.runner validate
python3 -m lab.runtime.runner create work/build --idempotency-key <stable-key>
python3 -m lab.runtime.runner run <render-job-id>
python3 -m lab.runtime.runner resume <render-job-id>
python3 -m lab.runtime.runner reconcile <render-job-id> work/operation.json
python3 -m lab.runtime.runner cancel <render-job-id>
python3 -m lab.runtime.runner show <render-job-id>
python3 -m lab.runtime.runner events <render-job-id>
python3 -m unittest discover -s lab/runtime/tests -p "test_*.py"
```
