# CPCS local release hardening

Slice 14 defines and tests one bounded release class: `local_single_worker`. It is suitable for a
human-operated local workstation after the repository gate passes. It is not an authenticated,
multi-user, unattended, or live-provider-qualified production service.

The release contract declares `posix_flock` for second-brain authority transactions and
`posix_shared_flock` for supported read isolation. One local writer may own staging, curated,
immutable, migration, or derived mutation at a time. Supported multi-file readers may coexist but
cannot overlap a writer, so a query operation sees either the before or after authority snapshot.
A competing process fails before authority reads, and process death releases the kernel lock.
Windows, network-filesystem, and multi-host coordination are outside this release class.

Curated promotion adds `write_ahead_rollback`: exact before and after images are hash-bound in an
ignored journal before any target changes. A process death before the durable commit marker causes
the next curation to restore all before images; death after the marker preserves the committed after
images. Security qualification rejects an active or incomplete preparation until recovery archives
it. Recovery data is capped at five targets and 256 MiB per transaction.

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
for rebuild. Backup creation owns the global authority transaction for the complete copy, so a
supported writer cannot interleave its snapshot. Neither backup creation nor restore overwrites an
existing target.

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

Polymath credentials remain environment-only. Query-time enrichment is ephemeral, operator-only,
and bound to exact request authorization. It contacts Polymath only after the local context broker
declares a knowledge gap and uses that broker's exact suggested query.

Local user and project profiles are separately capped at 256 IDs, 1,024 retained revisions, and
64 KiB per record. Each record has an explicit validity interval no longer than the 30-day work
retention policy. Context-store access prunes expired revisions. The database and directory use
mode `0600` and `0700`; security qualification rejects a symlink or permission drift at the default
path. Records contain compiler-validated overlays only and are excluded from second-brain authority
backup. Filesystem permissions are the only confidentiality mechanism in this release class.

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

The final five require `cpcs.external_qualification_evidence/2.0` bound to the report's full commit
SHA. Graph-write promotion cannot pass while any earlier gate is not `passed`.

### Trusted external evidence

External status is not self-authenticating. `policy.yaml` contains an initially empty
`qualification_trust.trusted_evaluators` registry. A human owner must register an evaluator ID with
only a SHA-256 fingerprint of a secret and the exact gates that evaluator may approve:

```yaml
qualification_trust:
  algorithm: hmac-sha256
  trusted_evaluators:
    owner_release:
      secret_sha256: sha256:<64 lowercase hex characters>
      allowed_gates: [closed_world_annotation, calibration, held_out, provider]
```

The secret must be at least 32 bytes and must remain outside Git. Supply it only when signing or
verifying:

```bash
export CPCS_QUALIFICATION_KEY_OWNER_RELEASE='<secret held outside the repository>'
python3 -m lab.release.evidence sign work/qualification/evidence-core.json \
  --output work/qualification/evidence.json
python3 -m lab.release.evidence verify work/qualification/evidence.json
python3 -m lab.release.qualification --check-remote \
  --external-evidence work/qualification/evidence.json \
  --output work/release/qualification.json
```

The unsigned core lists gate status, scalar metrics, and one or more artifact records with a path
relative to the evidence file, exact byte size, and SHA-256. Signing refuses an unregistered or
wrong secret. Verification checks evaluator gate scope, HMAC, path containment, symlinks, file
existence, size, hash, artifact count, and total bytes before qualification reads a status. Neither
the secret nor its value is written to evidence or reports. The policy also caps the manifest at
1 MiB, each gate at 64 artifact records, and verified artifact content at 256 MiB per bundle.

HMAC is an integrity and shared-secret trust boundary for the declared local single-worker release;
it is not a public-key signature or third-party nonrepudiation. A hosted multi-party release should
replace this boundary with an identity-provider or KMS-backed signature adapter rather than sharing
the local evaluator secret.

## Honest limits

- Locks use exact versions but do not yet use distribution hashes.
- CI is configured but has not passed until GitHub records a run for the committed revision.
- The installed HTTP service has no TLS or authenticated identity provider and remains loopback-only
  for operator or curator roles.
- The backup canary proves file and journal recovery, not disaster recovery on a second machine.
- Annotation, calibration, held-out, and live-provider evidence is not bundled in this repository.
- The trusted-evaluator registry is empty by default. External gates therefore cannot pass until the
  owner commits an evaluator fingerprint and gate scope for the exact release lineage.
- The authority lock is a single-host POSIX advisory lock. The lock path must not be deleted while a
  process owns it. Shared isolation covers supported decorated operations only, not direct file
  reads, multiple separate API calls, network filesystems, or distributed coordination.
- Curated transaction receipts live under the policy's ignored work state; automatic 30-day receipt
  pruning is not implemented yet.
