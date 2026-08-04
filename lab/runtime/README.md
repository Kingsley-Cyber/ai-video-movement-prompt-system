# CPCS render runtime

This runtime turns a validated provider build into a recoverable provider operation. The durable
repository stops at the build package; operational state belongs to the ignored job journal.

The initial, live-unqualified adapter targets Google Vertex AI Veo 3.1 through its REST
`predictLongRunning` and `fetchPredictOperation` endpoints. Application Default Credentials are
loaded lazily through `google-auth`; access tokens never enter the build, render job, journal, or
captured request. The prepared request preserves the compiler-owned content, while provider
responses are redacted before capture. The adapter does not author or rewrite direction.

The strongest guarantee is **no automatic duplicate submission**. If an operation receipt was
captured before a process died, resume recovers it and continues polling. If the provider may have
accepted a request but no receipt reached disk, the job stops at `submission_unknown`; an operator
must locate the provider operation and use `reconcile`. No local-only design can truthfully provide
exactly-once external side effects when the provider exposes neither an idempotency key nor a lookup
by client request ID.

Outputs under `work/render_jobs/<job-id>/` include the prepared request, submission receipt, numbered
poll responses, completed response, downloaded MP4 files, and `render_result.json`. These are
hash-bound runtime evidence, not curated knowledge or immutable experiment records.

The journal records schema version 1 in both `PRAGMA user_version` and `schema_migrations`. Use
`python3 -m lab.release.backup` before `python3 -m lab.release.migrations migrate`; opening a newer
unsupported journal fails closed.
