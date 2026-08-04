from __future__ import annotations

import json
import multiprocessing
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lab.application.service import _status as application_status
from lab.release.backup import create_backup
from lab.second_brain.src import authority as authority_module
from lab.second_brain.src.authority import (
    AuthorityBusy,
    LOCK_RELATIVE_PATH,
    authority_transaction,
)
from lab.second_brain.src.curate import promote_proposal
from lab.second_brain.src.compile import compile_result
from lab.second_brain.src.context import build_context_bundle
from lab.second_brain.src.distill import run_distillation
from lab.second_brain.src.distill import status as distillation_status
from lab.second_brain.src.graph import build_live_graph
from lab.second_brain.src.indexes import build_index_catalog
from lab.second_brain.src.ingest import status as ingest_status
from lab.second_brain.src.ingest import upsert_manifest
from lab.second_brain.src.migrate import migrate_existing
from lab.second_brain.src.pegasus import ingest_response
from lab.second_brain.src.query import default_request, reason
from lab.second_brain.src.record import append_record
from lab.second_brain.src.reflect import materialize, rebuild
from lab.second_brain.src.source_extract import _coverage
from lab.second_brain.tests.helpers import concept, make_root


def _hold_authority(
    root: str,
    ready: object,
    release: object,
    mode: str = "exclusive",
) -> None:
    with authority_transaction(Path(root), actor="test_holder", mode=mode):
        ready.set()
        if not release.wait(15):
            raise RuntimeError("authority lock test timed out waiting for release")


class AuthorityTransactionTests(unittest.TestCase):
    def test_shared_readers_coexist_and_reject_a_competing_writer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            context = multiprocessing.get_context("spawn")
            ready = context.Event()
            release = context.Event()
            process = context.Process(
                target=_hold_authority,
                args=(str(root), ready, release, "shared"),
            )
            process.start()
            try:
                self.assertTrue(ready.wait(10), "reader process did not acquire lock")
                with authority_transaction(
                    root,
                    actor="second_reader",
                    mode="shared",
                ) as receipt:
                    self.assertEqual(receipt["mode"], "shared")
                with self.assertRaises(AuthorityBusy) as raised:
                    upsert_manifest([], root)
                self.assertEqual(raised.exception.mode, "exclusive")
                self.assertEqual(raised.exception.holder["actor"], "shared_readers")
                self.assertEqual(raised.exception.holder["mode"], "shared")
                self.assertFalse((root / "lab").exists())
            finally:
                release.set()
                process.join(10)
                if process.is_alive():
                    process.terminate()
                    process.join(5)
            self.assertEqual(process.exitcode, 0)

    def test_exclusive_writer_rejects_supported_reads_before_they_open_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_root(
                Path(temporary),
                [concept("c_movement", "movement")],
            )
            request = default_request("movement", minimum_status="ingested")
            reasoning = reason(request, root)
            context = multiprocessing.get_context("spawn")
            ready = context.Event()
            release = context.Event()
            process = context.Process(
                target=_hold_authority,
                args=(str(root), ready, release),
            )
            process.start()
            try:
                self.assertTrue(ready.wait(10), "writer process did not acquire lock")
                for attempt in (
                    lambda: reason(request, root),
                    lambda: compile_result(reasoning, root=root),
                    lambda: build_context_bundle(
                        "movement",
                        token_budget=1_000,
                        root=root,
                    ),
                    lambda: build_live_graph(root),
                    lambda: build_index_catalog(root),
                    lambda: ingest_status(root),
                    lambda: distillation_status(root),
                    lambda: materialize(root),
                    lambda: application_status({}, root),
                    lambda: _coverage([], [], [], set(), [], root),
                ):
                    with self.assertRaises(AuthorityBusy) as raised:
                        attempt()
                    self.assertEqual(raised.exception.mode, "shared")
                    self.assertEqual(raised.exception.holder["actor"], "test_holder")
                    self.assertEqual(raised.exception.holder["mode"], "exclusive")
                    self.assertEqual(raised.exception.holder["pid"], process.pid)
            finally:
                release.set()
                process.join(10)
                if process.is_alive():
                    process.terminate()
                    process.join(5)
            self.assertEqual(process.exitcode, 0)

    def test_nested_modes_are_explicit_and_shared_to_exclusive_upgrade_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            with authority_transaction(
                root,
                actor="reader",
                mode="shared",
            ) as outer_reader:
                with authority_transaction(
                    root,
                    actor="nested_reader",
                    mode="shared",
                ) as nested_reader:
                    self.assertEqual(nested_reader, outer_reader)
                with self.assertRaisesRegex(RuntimeError, "cannot upgrade"):
                    with authority_transaction(root, actor="writer"):
                        pass
            with authority_transaction(root, actor="writer") as outer_writer:
                with authority_transaction(
                    root,
                    actor="nested_reader",
                    mode="shared",
                ) as nested_reader:
                    self.assertEqual(nested_reader, outer_writer)
            self.assertEqual(outer_reader["mode"], "shared")
            self.assertEqual(outer_writer["mode"], "exclusive")

    def test_competing_process_is_rejected_before_every_authority_tier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            context = multiprocessing.get_context("spawn")
            ready = context.Event()
            release = context.Event()
            process = context.Process(
                target=_hold_authority,
                args=(str(root), ready, release),
            )
            process.start()
            try:
                self.assertTrue(ready.wait(10), "holder process did not acquire lock")
                attempts = (
                    lambda: upsert_manifest([], root),
                    lambda: run_distillation({}, root),
                    lambda: promote_proposal(
                        "proposal_missing", "c_missing", "owner", {}, root
                    ),
                    lambda: append_record("run", {}, root),
                    lambda: ingest_response({}, root),
                    lambda: rebuild(root),
                    lambda: migrate_existing(root),
                    lambda: create_backup(
                        root / "work" / "backup",
                        created_at="2026-08-03T00:00:00Z",
                        root=root,
                    ),
                )
                for attempt in attempts:
                    with self.assertRaises(AuthorityBusy) as raised:
                        attempt()
                    self.assertEqual(raised.exception.holder["actor"], "test_holder")
                    self.assertEqual(raised.exception.holder["pid"], process.pid)
                self.assertFalse((root / "lab").exists())
            finally:
                release.set()
                process.join(10)
                if process.is_alive():
                    process.terminate()
                    process.join(5)
            self.assertEqual(process.exitcode, 0)

    def test_nested_owner_replays_and_process_death_cannot_leave_a_stale_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            context = multiprocessing.get_context("spawn")
            ready = context.Event()
            release = context.Event()
            process = context.Process(
                target=_hold_authority,
                args=(str(root), ready, release),
            )
            process.start()
            try:
                self.assertTrue(ready.wait(10), "holder process did not acquire lock")
            finally:
                if process.is_alive():
                    process.terminate()
                process.join(10)
            self.assertFalse(process.is_alive())
            with authority_transaction(root, actor="staging") as outer:
                with authority_transaction(root, actor="staging") as nested:
                    self.assertEqual(nested, outer)
                with authority_transaction(root, actor="curation") as cross_tier:
                    self.assertEqual(cross_tier, outer)
            with authority_transaction(root, actor="curation") as next_owner:
                self.assertEqual(next_owner["actor"], "curation")
                self.assertEqual(next_owner["pid"], os.getpid())
            lock_path = root / LOCK_RELATIVE_PATH
            self.assertEqual(lock_path.stat().st_mode & 0o777, 0o600)
            metadata = json.loads(lock_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["actor"], "curation")
            self.assertIn("released_at", metadata)
            lock_path.unlink()
            outside = Path(temporary) / "outside.lock"
            outside.write_text("do not touch", encoding="utf-8")
            lock_path.symlink_to(outside)
            with self.assertRaisesRegex(RuntimeError, "lock file cannot be a symlink"):
                with authority_transaction(root, actor="staging"):
                    pass
            self.assertEqual(outside.read_text(encoding="utf-8"), "do not touch")
            with mock.patch("lab.second_brain.src.authority.fcntl", None):
                with self.assertRaisesRegex(RuntimeError, "declared posix_flock"):
                    with authority_transaction(root, actor="staging"):
                        pass
            metadata_root = Path(temporary) / "metadata-failure-repo"
            metadata_root.mkdir()
            original_writer = authority_module._write_holder

            def fail_release_metadata(handle: object, value: dict[str, object]) -> None:
                if "released_at" in value:
                    raise OSError("simulated diagnostic metadata failure")
                original_writer(handle, value)

            with mock.patch.object(
                authority_module,
                "_write_holder",
                side_effect=fail_release_metadata,
            ):
                with authority_transaction(metadata_root, actor="staging"):
                    pass
            with authority_transaction(metadata_root, actor="curation"):
                pass


if __name__ == "__main__":
    unittest.main()
