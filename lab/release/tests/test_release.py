from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from lab.application.service import REQUEST_SCHEMA, invoke
from lab.application.telemetry import TelemetrySink, summarize
from lab.release.backup import create_backup, restore_backup, verify_backup
from lab.release.contracts import load_release_policy, validate_release_configuration
from lab.release.evidence import (
    secret_environment_name,
    sign_external_evidence,
    verify_external_evidence,
)
from lab.release.migrations import inspect_journal, migrate_journal
from lab.release.qualification import assess, main as qualification_main
from lab.release.security import scan
from lab.runtime.journal import JobJournal, JournalError
from lab.second_brain.src.source_extract import extract_folder
from lab.second_brain.src.validate import REPO_ROOT, ValidationFailure, canonical_json_bytes


class ReleaseHardeningTests(unittest.TestCase):
    def test_release_policy_locks_security_and_quota_gate(self) -> None:
        configuration = validate_release_configuration()
        self.assertEqual(configuration["schemas"], 4)
        self.assertEqual(configuration["release_class"], "local_single_worker")
        self.assertEqual(configuration["authority_locking"], "posix_flock")
        self.assertEqual(configuration["curation_recovery"], "write_ahead_rollback")
        report = scan()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["authority_locking"], "posix_flock")
        self.assertEqual(report["curation_recovery"], "write_ahead_rollback")
        self.assertEqual(report["curation_journal"]["active"], [])
        self.assertEqual(report["source_findings"], [])
        pending = copy.deepcopy(report["curation_journal"])
        pending["active"] = ["curation_tx_" + "a" * 24]
        with mock.patch(
            "lab.release.security.curation_journal_status",
            return_value=pending,
        ):
            rejected = scan()
        self.assertEqual(rejected["status"], "failed")
        self.assertIn("curation_recovery_pending", rejected["failures"])
        denied = invoke(
            {
                "schema": REQUEST_SCHEMA,
                "operation": "cpcs.context.get",
                "arguments": {"query": "movement", "token_budget": 50_001},
            }
        )
        self.assertEqual(denied["error"]["code"], "invalid_request")
        self.assertIn("release limit", denied["error"]["message"])

    def test_content_free_telemetry_is_private_and_traceable(self) -> None:
        work = REPO_ROOT / "work"
        work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as temporary:
            path = Path(temporary) / "telemetry.jsonl"
            sink = TelemetrySink(
                path,
                clock=lambda: "2026-08-03T00:00:00Z",
            )
            secret_text = "private unreleased product codename"
            response = invoke(
                {
                    "schema": REQUEST_SCHEMA,
                    "operation": "cpcs.intent.normalize",
                    "arguments": {"text": secret_text},
                },
                telemetry=sink,
            )
            self.assertEqual(response["status"], "success")
            serialized = path.read_text(encoding="utf-8")
            self.assertNotIn(secret_text, serialized)
            event = json.loads(serialized)
            self.assertEqual(event["trace_id"], response["request_id"])
            self.assertEqual(event["operation"], "cpcs.intent.normalize")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(summarize(path)["events"], 1)

    def test_online_backup_restore_tamper_and_overwrite_denial(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            journal_path = base / "live" / "render_jobs.sqlite3"
            journal = JobJournal(journal_path, time_fn=lambda: 100.0)
            journal.register(
                {
                    "job_id": "job_backup",
                    "idempotency_key": "idem_backup",
                    "adapter": "fixture/1.0",
                    "policy": {"timeout_seconds": 60},
                }
            )
            journal.verify("job_backup")
            backup_path = base / "backup"
            manifest = create_backup(
                backup_path,
                created_at="2026-08-03T00:00:00Z",
                journal_path=journal_path,
            )
            self.assertEqual(verify_backup(backup_path), manifest)
            restore_path = base / "restore"
            restored = restore_backup(backup_path, restore_path)
            self.assertTrue(restored["derived_rebuild_required"])
            restored_journal = JobJournal(restore_path / "work/render_jobs.sqlite3")
            restored_journal.verify("job_backup")
            self.assertEqual(
                (restore_path / "lab/concepts.jsonl").read_bytes(),
                (REPO_ROOT / "lab/concepts.jsonl").read_bytes(),
            )
            with self.assertRaises(FileExistsError):
                restore_backup(backup_path, restore_path)
            victim = next(
                row for row in manifest["files"] if row["kind"] == "prompt_lab"
            )
            path = backup_path.joinpath(*Path(victim["path"]).parts)
            path.write_bytes(path.read_bytes() + b"tamper")
            with self.assertRaisesRegex(ValueError, "hash or size"):
                verify_backup(backup_path)

    def test_existing_journal_requires_verified_backup_before_forward_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            journal_path = base / "legacy.sqlite3"
            with sqlite3.connect(journal_path) as connection:
                connection.execute("CREATE TABLE legacy_marker (id INTEGER PRIMARY KEY)")
                connection.execute("PRAGMA user_version=0")
            self.assertTrue(inspect_journal(journal_path)["migration_required"])
            with self.assertRaisesRegex(JournalError, "backed up"):
                migrate_journal(journal_path)
            backup_path = base / "backup"
            create_backup(
                backup_path,
                created_at="2026-08-03T00:00:00Z",
                journal_path=journal_path,
            )
            result = migrate_journal(journal_path, backup=backup_path)
            self.assertEqual(result["after"]["current_version"], 1)
            self.assertFalse(result["downgrade_supported"])
            self.assertEqual(len(result["after"]["migrations"]), 1)

    def test_qualification_is_categorical_and_external_evidence_is_revision_bound(self) -> None:
        report = assess()
        self.assertEqual(report["overall_status"], "not_qualified")
        gates = {row["gate"]: row for row in report["gates"]}
        self.assertEqual(gates["recoverability"]["status"], "passed")
        self.assertEqual(gates["schema"]["status"], "passed")
        self.assertEqual(gates["security"]["status"], "passed")
        self.assertEqual(gates["provider"]["status"], "blocked_external")
        self.assertEqual(gates["graph_write_promotion"]["status"], "blocked_external")
        core = {key: value for key, value in report.items() if key != "report_hash"}
        expected = "sha256:" + hashlib.sha256(canonical_json_bytes(core)).hexdigest()
        self.assertEqual(report["report_hash"], expected)
        wrong_revision = sign_external_evidence({
            "schema": "cpcs.external_qualification_evidence/2.0",
            "source_revision": "0" * 40,
            "evaluator_id": "owner_test",
            "gates": {
                "closed_world_annotation": {
                    "status": "failed",
                    "evaluated_at": "2026-08-03T00:00:00Z",
                    "artifacts": [
                        {
                            "path": "missing.json",
                            "sha256": "sha256:" + "0" * 64,
                            "size_bytes": 1,
                        }
                    ],
                    "metrics": {"items_annotated": 0},
                    "summary": "Wrong-revision fixture.",
                }
            },
        }, "x" * 32)
        with self.assertRaisesRegex(ValueError, "another revision"):
            assess(external_evidence=wrong_revision)

    def test_external_gate_evidence_requires_trust_mac_and_exact_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            artifact = base / "closed-world.json"
            artifact.write_bytes(b'{"annotated":24,"total":24}\n')
            artifact_bytes = artifact.read_bytes()
            secret = "owner-release-qualification-key-0001"
            core = {
                "schema": "cpcs.external_qualification_evidence/2.0",
                "source_revision": subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=REPO_ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip(),
                "evaluator_id": "owner_test",
                "gates": {
                    "closed_world_annotation": {
                        "status": "passed",
                        "evaluated_at": "2026-08-03T00:00:00Z",
                        "artifacts": [
                            {
                                "path": artifact.name,
                                "sha256": "sha256:"
                                + hashlib.sha256(artifact.read_bytes()).hexdigest(),
                                "size_bytes": artifact.stat().st_size,
                            }
                        ],
                        "metrics": {
                            "items_total": 24,
                            "items_annotated": 24,
                            "coverage": 1.0,
                        },
                        "summary": "All closed-world fixture items were annotated.",
                    }
                },
            }
            evidence = sign_external_evidence(core, secret)
            policy = copy.deepcopy(load_release_policy()[0])
            policy["qualification_trust"]["trusted_evaluators"] = {
                "owner_test": {
                    "secret_sha256": "sha256:"
                    + hashlib.sha256(secret.encode("utf-8")).hexdigest(),
                    "allowed_gates": ["closed_world_annotation"],
                }
            }
            verification_root = base / "verification-root"
            schema_directory = verification_root / "lab/release/schemas"
            schema_directory.mkdir(parents=True)
            shutil.copyfile(
                REPO_ROOT
                / "lab/release/schemas/external_qualification_evidence.schema.json",
                schema_directory / "external_qualification_evidence.schema.json",
            )
            (verification_root / "lab/release/policy.yaml").write_text(
                yaml.safe_dump(policy, sort_keys=False), encoding="utf-8"
            )
            environment = {secret_environment_name("owner_test"): secret}
            verified = verify_external_evidence(
                evidence,
                base,
                environment=environment,
                root=verification_root,
            )
            self.assertEqual(verified["artifact_count"], 1)
            self.assertEqual(verified["total_bytes"], artifact.stat().st_size)
            self.assertNotIn(secret, json.dumps(verified))

            wrong_key = {secret_environment_name("owner_test"): "z" * 32}
            with self.assertRaisesRegex(ValueError, "does not match policy"):
                verify_external_evidence(
                    evidence, base, environment=wrong_key, root=verification_root
                )

            forged = copy.deepcopy(evidence)
            forged["gates"]["closed_world_annotation"]["status"] = "failed"
            with self.assertRaisesRegex(ValueError, "attestation is invalid"):
                verify_external_evidence(
                    forged, base, environment=environment, root=verification_root
                )

            out_of_scope_core = copy.deepcopy(core)
            out_of_scope_core["gates"]["calibration"] = copy.deepcopy(
                out_of_scope_core["gates"]["closed_world_annotation"]
            )
            out_of_scope = sign_external_evidence(out_of_scope_core, secret)
            with self.assertRaisesRegex(ValueError, "not trusted for gates"):
                verify_external_evidence(
                    out_of_scope,
                    base,
                    environment=environment,
                    root=verification_root,
                )

            artifact.write_bytes(artifact.read_bytes() + b"tamper")
            with self.assertRaisesRegex(ValueError, "size differs"):
                verify_external_evidence(
                    evidence,
                    base,
                    environment=environment,
                    root=verification_root,
                )
            artifact.write_bytes(b"X" + artifact_bytes[1:])
            with self.assertRaisesRegex(ValueError, "hash differs"):
                verify_external_evidence(
                    evidence,
                    base,
                    environment=environment,
                    root=verification_root,
                )
            artifact.write_bytes(artifact_bytes)

            traversal_core = copy.deepcopy(core)
            traversal_core["gates"]["closed_world_annotation"]["artifacts"][0][
                "path"
            ] = "../outside.json"
            traversal = sign_external_evidence(traversal_core, secret)
            with self.assertRaisesRegex(ValueError, "safe relative path"):
                verify_external_evidence(
                    traversal,
                    base,
                    environment=environment,
                    root=verification_root,
                )

            linked = base / "linked.json"
            linked.symlink_to(artifact.name)
            symlink_core = copy.deepcopy(core)
            symlink_core["gates"]["closed_world_annotation"]["artifacts"][0][
                "path"
            ] = linked.name
            symlink_evidence = sign_external_evidence(symlink_core, secret)
            with self.assertRaisesRegex(ValueError, "symlink"):
                verify_external_evidence(
                    symlink_evidence,
                    base,
                    environment=environment,
                    root=verification_root,
                )

            evidence_path = base / "evidence.json"
            evidence_path.write_bytes(canonical_json_bytes(evidence))
            evidence_link = base / "evidence-link.json"
            evidence_link.symlink_to(evidence_path.name)
            with self.assertRaisesRegex(ValueError, "manifest.*symlink"):
                qualification_main(["--external-evidence", str(evidence_link)])
            oversized_manifest = base / "oversized-evidence.json"
            oversized_manifest.write_bytes(
                b" "
                * (policy["limits"]["qualification_manifest_bytes"] + 1)
            )
            with self.assertRaisesRegex(ValueError, "manifest exceeds"):
                qualification_main(
                    ["--external-evidence", str(oversized_manifest)]
                )
            with self.assertRaisesRegex(ValueError, "not trusted by policy"):
                assess(
                    external_evidence=evidence,
                    external_evidence_path=evidence_path,
                )
            with mock.patch(
                "lab.release.qualification.verify_external_evidence",
                return_value=verified,
            ) as verifier:
                wired_report = assess(
                    external_evidence=evidence,
                    external_evidence_path=evidence_path,
                )
            wired_gates = {row["gate"]: row for row in wired_report["gates"]}
            self.assertEqual(
                wired_gates["closed_world_annotation"]["status"], "passed"
            )
            self.assertIn(
                verified["attestation_hash"],
                wired_gates["closed_world_annotation"]["evidence"],
            )
            verifier.assert_called_once()

    def test_parser_fuzz_corpus_fails_closed_without_authority_mutation(self) -> None:
        authority = {
            str(path.relative_to(REPO_ROOT)): path.read_bytes()
            for tier in ("curated", "immutable", "staging")
            for path in sorted((REPO_ROOT / "lab/second_brain" / tier).rglob("*"))
            if path.is_file()
        }
        cases = []
        for index in range(8):
            cases.append(
                (
                    f"unsafe_{index}.yaml",
                    f"value: !!python/object/apply:os.system ['echo fuzz-{index}']",
                    None,
                )
            )
            cases.append(
                (
                    f"entity_{index}.xml",
                    f'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///tmp/fuzz-{index}">]><x>&e;</x>',
                    None,
                )
            )
            nested = "[" * (index + 6) + "0" + "]" * (index + 6)
            cases.append((f"deep_{index}.json", nested, {"max_tree_depth": 4}))
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for name, content, configuration in cases:
                folder = base / name.replace(".", "_")
                folder.mkdir()
                (folder / name).write_text(content, encoding="utf-8")
                with self.assertRaises(ValidationFailure):
                    extract_folder(
                        folder,
                        research_goal="fuzz parser safety",
                        rights_basis="owner_authorized_test_fixture",
                        configuration=configuration,
                    )
        after = {
            str(path.relative_to(REPO_ROOT)): path.read_bytes()
            for tier in ("curated", "immutable", "staging")
            for path in sorted((REPO_ROOT / "lab/second_brain" / tier).rglob("*"))
            if path.is_file()
        }
        self.assertEqual(authority, after)


if __name__ == "__main__":
    unittest.main()
