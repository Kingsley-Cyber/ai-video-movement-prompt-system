# CPCS local release hardening

Slice 14 defines and tests one bounded release class: `local_single_worker`. It is suitable for a
human-operated local workstation after the repository gate passes. It is not an authenticated,
multi-user, unattended, or live-provider-qualified production service.

## Reproducible core install

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --requirement requirements.lock
python -m pip install --no-deps .
cpcs status
```

`requirements.lock` fixes the complete core dependency set. Optional provider versions are isolated
in `requirements-providers.lock`. Local pose dependencies are isolated in
`requirements-measurement.lock` and the `measurement` package extra. Installing either optional
set does not qualify its API or detector quality. CI repeats the core install and the complete
repository gate on Python 3.11.

## Backup and restore

```bash
python3 -m lab.release.backup create work/backups/backup_001 \
  --created-at 2026-08-03T00:00:00Z \
  --journal work/runtime/render_jobs.sqlite3
python3 -m lab.release.backup verify work/backups/backup_001
python3 -m lab.release.backup restore work/backups/backup_001 work/restore_test
```

The backup copies and hashes curated, immutable, staging, prompt-lab, and result-ledger state. A live
SQLite journal uses the SQLite online backup API. Derived state is deliberately omitted and marked
for rebuild. Neither backup creation nor restore overwrites an existing target.

## Journal migration

```bash
python3 -m lab.release.migrations status work/runtime/render_jobs.sqlite3
python3 -m lab.release.migrations migrate work/runtime/render_jobs.sqlite3 \
  --backup work/backups/backup_001
```

The journal carries `PRAGMA user_version`, an immutable migration name, and a migration checksum.
Existing journals require a verified backup before forward migration. Newer unknown versions and
downgrades fail closed.

## Content-free telemetry

```bash
./bin/cpcs status --telemetry work/telemetry/application.jsonl
python3 -m lab.application.http --telemetry work/telemetry/application.jsonl
```

Events contain trace ID, operation, status, role, mutation scope, authorization ID when present,
duration, and time. They never contain prompts, request arguments, paths, evidence, response
content, or errors. Files are created with mode `0600` under ignored `work/` only.

The local release caps each context request, external-evidence packet, provider build, analysis
duration, batch size, and render deadline. `cpcs.production.prepare` and the analysis and render
operations enforce the same `policy.yaml` values before provider work begins.

## Qualification

```bash
python3 -m lab.release.qualification --check-remote \
  --output work/release/qualification.json
```

Exit `0` means every gate passed. Exit `2` means the report is valid but not qualified. The report
always lists these gates separately:

1. engineering freeze;
2. recoverability;
3. Git reproducibility;
4. schema;
5. security;
6. closed-world annotation;
7. calibration;
8. held-out evaluation;
9. live provider;
10. graph-write promotion.

The final five require `cpcs.external_qualification_evidence/1.0` bound to the report's full commit
SHA. Graph-write promotion cannot pass while any earlier gate is not `passed`.

## Honest limits

- Locks use exact versions but do not yet use distribution hashes.
- CI is configured but has not passed until GitHub records a run for the committed revision.
- The installed HTTP service has no TLS or authenticated identity provider and remains loopback-only
  for operator or curator roles.
- The backup canary proves file and journal recovery, not disaster recovery on a second machine.
- Annotation, calibration, held-out, and live-provider evidence is not bundled in this repository.
