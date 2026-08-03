from __future__ import annotations

import base64
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from typing import Any

from lab.compiler.build import write_build_directory
from lab.compiler.provenance import sha256_bytes
from lab.compiler.tests.test_build import build_for, ready_score
from lab.runtime.adapters.base import AdapterError
from lab.runtime.adapters.veo import VeoVertexAdapter
from lab.runtime.journal import JobJournal, JournalError
from lab.runtime.runner import RenderRunner, RunnerCrash, make_render_job


class FakeAdapter:
    adapter_id = "google_vertex_ai.veo/1.0"
    submission_idempotent = False

    def __init__(
        self,
        *,
        poll_values: list[Any] | None = None,
        submit_error: AdapterError | None = None,
        supports_cancel: bool = True,
    ) -> None:
        self.supports_remote_cancel = supports_cancel
        self.submit_error = submit_error
        self.poll_values = list(
            poll_values
            or [
                {"status": "pending", "operation_id": "operation_fixture", "raw": {"done": False}},
                {
                    "status": "succeeded",
                    "operation_id": "operation_fixture",
                    "raw": {"done": True, "response": {"videos": [{}]}},
                },
            ]
        )
        self.submit_count = 0
        self.poll_count = 0
        self.cancel_count = 0

    def validate(self, build: dict[str, Any], job: dict[str, Any]) -> None:
        if build["manifest"]["build_id"] != job["build_id"]:
            raise AssertionError("fixture build mismatch")

    def prepare(self, build: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
        return {
            "method": "POST",
            "url": build["provider_request"]["url"],
            "body": build["provider_request"]["body"],
            "adapter": self.adapter_id,
            "literal_prompt_text": "Bearer tonic is ordinary creative copy",
        }

    def submit(
        self, prepared: dict[str, Any], *, idempotency_key: str
    ) -> dict[str, Any]:
        self.submit_count += 1
        if self.submit_error is not None:
            raise self.submit_error
        return {
            "operation_id": "operation_fixture",
            "provider": "fake",
            "model": "fixture",
            "submit_response": {"name": "operation_fixture"},
        }

    def poll(self, operation: dict[str, Any]) -> dict[str, Any]:
        self.poll_count += 1
        if not self.poll_values:
            raise AssertionError("fixture exhausted poll values")
        value = self.poll_values.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def retrieve(
        self, completed: dict[str, Any], destination: Path
    ) -> list[dict[str, Any]]:
        destination.mkdir(parents=True, exist_ok=True)
        data = b"\x00\x00\x00\x18ftypmp42fixture"
        path = destination / "artifact_000.mp4"
        path.write_bytes(data)
        return [
            {
                "artifact_id": "artifact_000",
                "relative_path": "artifacts/artifact_000.mp4",
                "source_uri": None,
                "mime_type": "video/mp4",
                "size_bytes": len(data),
                "sha256": sha256_bytes(data),
            }
        ]

    def normalize(
        self,
        *,
        job: dict[str, Any],
        build: dict[str, Any],
        operation: dict[str, Any],
        completed: dict[str, Any],
        artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        parameters = build["provider_request"]["body"]["parameters"]
        return {
            "schema": "cpcs.render_result/1.0",
            "job_id": job["job_id"],
            "build_id": build["manifest"]["build_id"],
            "build_hash": build["manifest"]["build_hash"],
            "provider": "fake",
            "model": "fixture",
            "operation_id": operation["operation_id"],
            "status": "succeeded",
            "artifacts": artifacts,
            "expected_media": {
                "duration_seconds": parameters["durationSeconds"],
                "aspect_ratio": parameters["aspectRatio"],
                "resolution": parameters["resolution"],
                "sample_count": parameters["sampleCount"],
            },
            "provider_response_hash": "sha256:" + "a" * 64,
        }

    def cancel(self, operation: dict[str, Any]) -> dict[str, Any]:
        self.cancel_count += 1
        return {
            "supported": self.supports_remote_cancel,
            "status": "cancelled" if self.supports_remote_cancel else "unsupported",
            "operation_id": operation["operation_id"],
        }


class RuntimeFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name)
        score = ready_score("Show how this device works in a clear educational video")
        _, artifacts = build_for(score)
        self.build_dir = self.workspace / "build"
        write_build_directory(artifacts, self.build_dir)
        self.clock = [1_800_000_000.0]
        self.journal = JobJournal(
            self.workspace / "jobs.sqlite3", time_fn=lambda: self.clock[0]
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def job(self, suffix: str = "fixture", **policy: Any) -> dict[str, Any]:
        values = {
            "timeout_seconds": 100,
            "poll_interval_seconds": 0,
            "max_safe_retries": 2,
            "lease_seconds": 10,
            **policy,
        }
        return make_render_job(
            self.build_dir,
            idempotency_key=f"render-{suffix}-idempotency",
            created_at="2027-01-15T08:00:00Z",
            **values,
        )

    def runner(
        self,
        adapter: Any,
        *,
        crash_hook: Any = None,
        sleep: Any = lambda seconds: None,
        worker_id: str = "worker_fixture",
    ) -> RenderRunner:
        return RenderRunner(
            self.journal,
            work_root=self.workspace / "render_jobs",
            adapters={adapter.adapter_id: adapter},
            worker_id=worker_id,
            crash_hook=crash_hook,
            sleep_fn=sleep,
        )


class RenderRunnerTests(RuntimeFixture):
    def test_successful_job_is_idempotent_hash_bound_and_event_verified(self) -> None:
        adapter = FakeAdapter()
        runner = self.runner(adapter)
        job = self.job()
        first_registration = runner.register(job)
        second_registration = runner.register(json.loads(json.dumps(job)))
        self.assertEqual(first_registration["job_hash"], second_registration["job_hash"])
        result = runner.run(job["job_id"])
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(adapter.submit_count, 1)
        self.assertEqual(runner.run(job["job_id"])["state"], "succeeded")
        self.assertEqual(adapter.submit_count, 1)
        prepared = json.loads(
            (
                self.workspace
                / "render_jobs"
                / job["job_id"]
                / "prepared_request.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            prepared["literal_prompt_text"],
            "Bearer tonic is ordinary creative copy",
        )
        self.journal.verify(job["job_id"])
        artifact = self.workspace / "render_jobs" / job["job_id"] / "artifacts/artifact_000.mp4"
        self.assertEqual(sha256_bytes(artifact.read_bytes()), result["result"]["artifacts"][0]["sha256"])

    def test_kill_after_receipt_capture_resumes_without_second_submission(self) -> None:
        adapter = FakeAdapter(poll_values=[{
            "status": "succeeded",
            "operation_id": "operation_fixture",
            "raw": {"done": True, "response": {"videos": [{}]}},
        }])

        def crash(event: str, snapshot: dict[str, Any]) -> None:
            if event == "after_submit_receipt_capture":
                raise RunnerCrash("simulated process kill")

        runner = self.runner(adapter, crash_hook=crash)
        job = self.job("kill")
        runner.register(job)
        with self.assertRaises(RunnerCrash):
            runner.run(job["job_id"])
        self.assertEqual(self.journal.get(job["job_id"])["state"], "submitting")
        with self.assertRaisesRegex(JournalError, "leased by worker_fixture"):
            self.runner(adapter, worker_id="worker_early").run(job["job_id"])
        self.clock[0] += 11
        resumed = self.runner(adapter, worker_id="worker_resumed").run(job["job_id"])
        self.assertEqual(resumed["state"], "succeeded")
        self.assertEqual(adapter.submit_count, 1)
        events = [row["event_type"] for row in self.journal.events(job["job_id"])]
        self.assertIn("submission_receipt_recovered", events)

    def test_ambiguous_submit_is_never_retried_and_can_be_reconciled(self) -> None:
        adapter = FakeAdapter(
            submit_error=AdapterError(
                "connection lost after dispatch",
                retryable=True,
                submission_uncertain=True,
                code="transport_error",
            ),
            poll_values=[{
                "status": "succeeded",
                "operation_id": "operation_fixture",
                "raw": {"done": True, "response": {"videos": [{}]}},
            }],
        )
        runner = self.runner(adapter)
        job = self.job("ambiguous")
        runner.register(job)
        unknown = runner.run(job["job_id"])
        self.assertEqual(unknown["state"], "submission_unknown")
        self.assertEqual(runner.run(job["job_id"])["state"], "submission_unknown")
        self.assertEqual(adapter.submit_count, 1)
        adapter.submit_error = None
        runner.reconcile(
            job["job_id"],
            {
                "operation_id": "operation_fixture",
                "provider": "fake",
                "model": "fixture",
                "submit_response": {"name": "operation_fixture"},
            },
        )
        self.assertEqual(runner.run(job["job_id"])["state"], "succeeded")
        self.assertEqual(adapter.submit_count, 1)

    def test_poll_retry_timeout_and_remote_cancellation_are_explicit(self) -> None:
        retry = AdapterError("temporary", retryable=True, code="http_503")
        adapter = FakeAdapter(
            poll_values=[
                retry,
                {"status": "pending", "operation_id": "operation_fixture", "raw": {}},
                {
                    "status": "succeeded",
                    "operation_id": "operation_fixture",
                    "raw": {"done": True, "response": {"videos": [{}]}},
                },
            ]
        )
        runner = self.runner(adapter)
        job = self.job("retry")
        runner.register(job)
        completed = runner.run(job["job_id"])
        self.assertEqual(completed["state"], "succeeded")
        self.assertEqual(completed["retry_count"], 1)

        timeout_adapter = FakeAdapter(
            poll_values=[
                {"status": "pending", "operation_id": "operation_fixture", "raw": {}},
                {"status": "pending", "operation_id": "operation_fixture", "raw": {}},
            ]
        )

        def advance(seconds: float) -> None:
            self.clock[0] += 2

        timeout_runner = self.runner(timeout_adapter, sleep=advance, worker_id="worker_timeout")
        timeout_job = self.job("timeout", timeout_seconds=1)
        timeout_runner.register(timeout_job)
        self.assertEqual(timeout_runner.run(timeout_job["job_id"])["state"], "timed_out")

        cancel_adapter = FakeAdapter(poll_values=[RunnerCrash("kill while polling")])
        cancel_runner = self.runner(cancel_adapter, worker_id="worker_cancel")
        cancel_job = self.job("cancel")
        cancel_runner.register(cancel_job)
        with self.assertRaises(RunnerCrash):
            cancel_runner.run(cancel_job["job_id"])
        cancelled = cancel_runner.cancel(cancel_job["job_id"])
        self.assertEqual(cancelled["state"], "cancelled")
        self.assertEqual(cancel_adapter.cancel_count, 1)

        unsupported_adapter = FakeAdapter(
            poll_values=[RunnerCrash("kill while polling")], supports_cancel=False
        )
        unsupported_runner = self.runner(
            unsupported_adapter, worker_id="worker_cancel_unsupported"
        )
        unsupported_job = self.job("cancel-unsupported")
        unsupported_runner.register(unsupported_job)
        with self.assertRaises(RunnerCrash):
            unsupported_runner.run(unsupported_job["job_id"])
        unsupported = unsupported_runner.cancel(unsupported_job["job_id"])
        self.assertEqual(unsupported["state"], "cancel_unsupported")
        self.assertEqual(unsupported_adapter.cancel_count, 1)

    def test_unknown_provider_poll_status_fails_closed(self) -> None:
        adapter = FakeAdapter(
            poll_values=[
                {
                    "status": "mysterious",
                    "operation_id": "operation_fixture",
                    "raw": {},
                }
            ]
        )
        runner = self.runner(adapter)
        job = self.job("invalid-poll")
        runner.register(job)
        result = runner.run(job["job_id"])
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["last_error"]["code"], "invalid_response")

    def test_tampered_build_and_conflicting_idempotency_are_rejected(self) -> None:
        adapter = FakeAdapter()
        runner = self.runner(adapter)
        job = self.job("tamper")
        runner.register(job)
        conflicting = json.loads(json.dumps(job))
        conflicting["policy"]["timeout_seconds"] = 99
        with self.assertRaisesRegex(JournalError, "different input"):
            runner.register(conflicting)
        (self.build_dir / "prompt.txt").write_text("tampered", encoding="utf-8")
        failed = runner.run(job["job_id"])
        self.assertEqual(failed["state"], "failed")
        self.assertEqual(adapter.submit_count, 0)

    def test_journal_detects_event_tampering(self) -> None:
        adapter = FakeAdapter()
        runner = self.runner(adapter)
        job = self.job("journal")
        runner.register(job)
        with sqlite3.connect(self.journal.path) as connection:
            connection.execute(
                "UPDATE events SET payload_json='{}' WHERE job_id=? AND event_type='registered'",
                (job["job_id"],),
            )
        with self.assertRaisesRegex(JournalError, "hash"):
            self.journal.verify(job["job_id"])


class VeoAdapterTests(RuntimeFixture):
    def test_real_adapter_contract_polls_normalizes_and_never_persists_token(self) -> None:
        secret = "super-secret-oauth-token"
        operation = (
            "projects/cpcs-test-project/locations/us-central1/publishers/google/"
            "models/veo-3.1-generate-001/operations/operation-123"
        )
        video = b"\x00\x00\x00\x18ftypmp42provider-fixture"
        calls: list[tuple[str, str | None]] = []

        def opener(request: Any, timeout: float) -> bytes:
            calls.append((request.full_url, request.headers.get("Authorization")))
            if request.full_url.endswith(":predictLongRunning"):
                return json.dumps({"name": operation}).encode()
            return json.dumps(
                {
                    "name": operation,
                    "done": True,
                    "response": {
                        "raiMediaFilteredCount": 0,
                        "videos": [
                            {
                                "bytesBase64Encoded": base64.b64encode(video).decode(),
                                "mimeType": "video/mp4",
                            }
                        ],
                    },
                }
            ).encode()

        adapter = VeoVertexAdapter(
            token_provider=lambda: secret,
            opener=opener,
        )
        runner = self.runner(adapter)
        job = self.job("veo")
        runner.register(job)
        completed = runner.run(job["job_id"])
        self.assertEqual(completed["state"], "succeeded")
        self.assertEqual([value for _, value in calls], [f"Bearer {secret}", f"Bearer {secret}"])
        persisted = self.journal.path.read_bytes() + b"".join(
            path.read_bytes()
            for path in (self.workspace / "render_jobs" / job["job_id"]).rglob("*")
            if path.is_file()
        )
        self.assertNotIn(secret.encode(), persisted)
        self.assertFalse(adapter.cancel({"operation_id": operation})["supported"])


if __name__ == "__main__":
    unittest.main()
