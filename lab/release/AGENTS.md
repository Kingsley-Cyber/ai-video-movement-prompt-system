# AGENTS.md — local release and qualification

Root [`AGENTS.md`](../../AGENTS.md) governs the repository. This subsystem hardens and classifies a
bounded `local_single_worker` release. It never converts missing live evidence into a pass.

## Ownership

| Concern | Owner |
|---|---|
| Release class, quotas, privacy, rights, backup, and gate policy | `policy.yaml` |
| Exact dependency resolution and installable command | root package manifests and lock files |
| Authority plus online SQLite backup and non-overwriting restore | `backup.py` |
| Forward-only render-journal migrations | `migrations.py` + `lab/runtime/journal.py` |
| Static security, lock, symlink, rights, and policy checks | `security.py` |
| Categorical local and external gate report | `qualification.py` |
| Content-free operation events | `lab/application/telemetry.py` |

## Laws

1. The release class remains local and single-worker until authenticated deployment evidence
   supports a new contract.
2. Backup precedes migration. Restore never overwrites a destination. Downgrade is unsupported.
3. Derived state is rebuilt, not backed up as authority.
4. Telemetry records only the allowlisted fields in `policy.yaml`; prompts, arguments, assets,
   evidence, errors, and credentials are forbidden.
5. `qualification.py` accepts external gate evidence only for the exact Git revision. Graph-write
   promotion remains blocked until every prior gate passes.
6. Exact version locks do not prove provider compatibility. Live providers need completed jobs and
   artifact evidence.
7. A dirty tree or unmatched remote cannot receive reproducibility status `passed`.

## Gate

```bash
python3 -m lab.release.security
python3 -m unittest discover -s lab/release/tests -p 'test_*.py'
python3 lab/scripts/validate_repo.py
```
