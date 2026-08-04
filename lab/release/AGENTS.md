# AGENTS.md — local release and qualification

Root [`AGENTS.md`](../../AGENTS.md) governs the repository. This subsystem hardens and classifies a
bounded `local_single_worker` release. It never converts missing live evidence into a pass.

## Ownership

| Concern | Owner |
|---|---|
| Release class, quotas, privacy, rights, backup, and gate policy | `policy.yaml` |
| Local context storage permissions and privacy findings | `security.py` plus `../application/context_store.py` |
| Exact dependency resolution and installable command | root package manifests and lock files |
| Authority plus online SQLite backup and non-overwriting restore | `backup.py` |
| Forward-only render-journal migrations | `migrations.py` + `lab/runtime/journal.py` |
| Static security, lock, symlink, rights, and policy checks | `security.py` |
| Trusted external-evidence signing, scope, and artifact verification | `evidence.py` |
| Categorical local and external gate report | `qualification.py` |
| Content-free operation events | `lab/application/telemetry.py` |

## Laws

1. The release class remains local and single-worker until authenticated deployment evidence
   supports a new contract.
2. Backup precedes migration. Restore never overwrites a destination. Downgrade is unsupported.
   Backup creation holds the same authority transaction as writers for one consistent snapshot.
3. Derived state is rebuilt, not backed up as authority.
4. Telemetry records only the allowlisted fields in `policy.yaml`; prompts, arguments, assets,
   evidence, errors, and credentials are forbidden.
5. `qualification.py` accepts external gate evidence only for the exact Git revision. Graph-write
   promotion remains blocked until every prior gate passes.
6. Exact version locks do not prove provider compatibility or detector quality. Live providers and
   local measurement models need completed jobs and artifact evidence.
7. A dirty tree or unmatched remote cannot receive reproducibility status `passed`.
8. External gates accept only `cpcs.external_qualification_evidence/2.0` from a policy-registered
   evaluator whose runtime HMAC secret matches the committed fingerprint and whose allowed gate
   scope covers every supplied gate. Every relative artifact path, size, and hash is verified before
   the evaluator's status can enter a report. Secrets never enter evidence, policy, reports, or logs.
9. The local release admits second-brain authority writes only with the policy-declared
   `posix_flock` transaction. It does not claim Windows, network-filesystem, or multi-host writer
   safety, and the lock path must not be deleted while an owning process is active.
10. Curated promotion uses the policy-declared `write_ahead_rollback` boundary. Qualification fails
    while an active or pre-activation transaction needs recovery. A committed transaction is never
    reported as rolled back merely because receipt archival failed.
11. Supported multi-file authority reads use the policy-declared `posix_shared_flock` boundary.
    Shared readers may coexist across processes, writers remain exclusive, and one snapshot never
    extends across separate application calls or unsupported direct file reads.
12. Persistent user and project context is admitted only as compiler-validated typed overlays for
    one local operating-system account. Filesystem permissions, profile, revision, and byte caps,
    explicit validity, expiry pruning, project binding, and exact-authorized deletion are required.
    This boundary is not encrypted, synchronized, authenticated multi-user storage, or authority
    backup data.

## Gate

```bash
python3 -m lab.release.security
python3 -m lab.release.evidence verify work/qualification/evidence.json
python3 -m unittest discover -s lab/release/tests -p 'test_*.py'
python3 lab/scripts/validate_repo.py
```
