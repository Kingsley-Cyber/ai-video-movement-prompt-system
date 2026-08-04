from __future__ import annotations

import http.cookiejar
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from lab.application.service import REQUEST_SCHEMA, authorization_request_hash, invoke
from lab.application.ui import (
    COOKIE_NAME,
    SESSION_IDLE_SECONDS,
    WORKSPACE_RETENTION_SECONDS,
    LocalUISession,
    SessionAssetStore,
    make_ui_handler,
)
from lab.runtime.journal import JobJournal
from lab.runtime.runner import RenderRunner
from lab.runtime.tests.test_runner import FakeAdapter
from lab.second_brain.src.validate import REPO_ROOT


class MarkupInventory(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.labels: set[str] = set()
        self.controls: set[str] = set()
        self.landmarks: set[str] = set()
        self.inline_scripts = 0
        self.inline_styles = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        identifier = values.get("id")
        if identifier:
            self.ids.add(identifier)
        if tag == "label" and values.get("for"):
            self.labels.add(str(values["for"]))
        if tag in {"input", "select", "textarea"} and identifier:
            self.controls.add(identifier)
        if tag in {"header", "nav", "main", "footer"}:
            self.landmarks.add(tag)
        if tag == "script" and "src" not in values:
            self.inline_scripts += 1
        if "style" in values:
            self.inline_styles += 1


def application_request(operation: str, arguments: dict) -> dict:
    return {
        "schema": REQUEST_SCHEMA,
        "operation": operation,
        "arguments": arguments,
    }


class UIServer:
    def __init__(self, base: Path, *, role: str = "operator", invoke_fn=invoke) -> None:
        self.session = LocalUISession(
            role=role,
            user="ui-test-user",
            bootstrap_token="bootstrap-test-token",
            session_token="session-test-token",
            csrf_token="csrf-test-token",
        )
        self.assets = SessionAssetStore(base)
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            make_ui_handler(
                role=role,
                session=self.session,
                asset_store=self.assets,
                root=base,
                invoke_fn=invoke_fn,
            ),
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies)
        )

    def bootstrap(self) -> None:
        with self.opener.open(
            f"{self.origin}/?bootstrap=bootstrap-test-token", timeout=10
        ) as response:
            self.assert_status(response.status, 200)

    @staticmethod
    def assert_status(actual: int, expected: int) -> None:
        if actual != expected:
            raise AssertionError(f"expected HTTP {expected}, got {actual}")

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict]:
        request = urllib.request.Request(
            self.origin + path,
            data=body,
            headers=headers or {},
            method=method,
        )
        try:
            with self.opener.open(request, timeout=10) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def post_invoke(self, envelope: dict, *, csrf: bool = True) -> tuple[int, dict]:
        headers = {"Content-Type": "application/json", "Origin": self.origin}
        if csrf:
            headers["X-CPCS-CSRF"] = "csrf-test-token"
        return self.request(
            "/v1/ui/invoke",
            method="POST",
            body=json.dumps(envelope).encode("utf-8"),
            headers=headers,
        )

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.assets.close()


class LocalGraphicalClientTests(unittest.TestCase):
    def test_one_time_bootstrap_session_catalog_and_security_headers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            ui = UIServer(base)
            try:
                status, denied = ui.request("/v1/ui/session")
                self.assertEqual(status, 401)
                self.assertEqual(denied["error"], "session_required")
                ui.bootstrap()
                self.assertTrue(
                    any(cookie.name == COOKIE_NAME for cookie in ui.cookies)
                )
                status, session = ui.request("/v1/ui/session")
                self.assertEqual(status, 200)
                self.assertEqual(session["identity"], "ui-test-user")
                self.assertEqual(session["role"], "operator")
                self.assertEqual(session["csrf_token"], "csrf-test-token")
                self.assertNotIn("session-test-token", json.dumps(session))
                names = {row["name"] for row in session["operations"]}
                self.assertIn("cpcs.production.prepare", names)
                self.assertIn("cpcs.render.run", names)
                second = urllib.request.build_opener()
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    second.open(
                        f"{ui.origin}/?bootstrap=bootstrap-test-token", timeout=10
                    )
                self.assertEqual(caught.exception.code, 401)
                request = urllib.request.Request(ui.origin + "/")
                with ui.opener.open(request, timeout=10) as response:
                    headers = response.headers
                    self.assertEqual(headers["X-Frame-Options"], "DENY")
                    self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
                    self.assertEqual(headers["Cache-Control"], "no-store")
            finally:
                ui.close()

    def test_csrf_origin_role_catalog_and_exact_approval_are_enforced(self) -> None:
        calls: list[dict] = []

        def fake(request: dict, **kwargs: object) -> dict:
            calls.append({"request": request, "kwargs": kwargs})
            return {"status": "success", "result": {"accepted": True}}

        with tempfile.TemporaryDirectory() as temporary:
            ui = UIServer(Path(temporary), invoke_fn=fake)
            try:
                ui.bootstrap()
                envelope = {
                    "request": application_request(
                        "cpcs.intent.normalize", {"text": "casual product video"}
                    )
                }
                status, denied = ui.post_invoke(envelope, csrf=False)
                self.assertEqual(status, 403)
                self.assertEqual(denied["error"], "csrf_denied")
                status, denied = ui.request(
                    "/v1/ui/invoke",
                    method="POST",
                    body=json.dumps(envelope).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Origin": "http://example.invalid",
                        "X-CPCS-CSRF": "csrf-test-token",
                    },
                )
                self.assertEqual(status, 403)
                self.assertEqual(denied["error"], "origin_denied")
                forged = {
                    "request": {
                        **application_request("cpcs.render.run", {"job_id": "render_job_" + "a" * 24}),
                        "authorization": None,
                    }
                }
                status, denied = ui.post_invoke(forged)
                self.assertEqual(status, 400)
                self.assertIn("browser-supplied", denied["message"])
                arguments = {"job_id": "render_job_" + "a" * 24}
                approved = {
                    "request": application_request("cpcs.render.run", arguments),
                    "approval": {
                        "confirmed": True,
                        "reason": "Approve this exact fixture submission",
                    },
                }
                status, result = ui.post_invoke(approved)
                self.assertEqual(status, 200)
                self.assertTrue(result["result"]["accepted"])
                authorization = calls[-1]["request"]["authorization"]
                self.assertEqual(
                    authorization["request_hash"],
                    authorization_request_hash("cpcs.render.run", arguments),
                )
                self.assertEqual(
                    authorization["authorized_by"],
                    "local-os-account:ui-test-user",
                )
                self.assertEqual(calls[-1]["kwargs"]["role"], "operator")
                invisible = {
                    "request": application_request(
                        "cpcs.curate.promote", {"unexpected": True}
                    )
                }
                status, denied = ui.post_invoke(invisible)
                self.assertEqual(status, 400)
                self.assertIn("not available", denied["message"])
            finally:
                ui.close()

    def test_reference_upload_is_exact_byte_typed_and_session_ephemeral(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ui = UIServer(Path(temporary))
            workspace = ui.assets.workspace
            try:
                ui.bootstrap()
                png = b"\x89PNG\r\n\x1a\n" + b"fixture-pixels"
                headers = {
                    "Content-Type": "image/png",
                    "Origin": ui.origin,
                    "X-CPCS-CSRF": "csrf-test-token",
                    "X-CPCS-Asset-Role": "product_reference",
                    "X-CPCS-Rights-Basis": "original",
                }
                status, result = ui.request(
                    "/v1/ui/upload", method="POST", body=png, headers=headers
                )
                self.assertEqual(status, 200)
                self.assertEqual(result["asset"]["role"], "product_reference")
                self.assertEqual(result["upload"]["size_bytes"], len(png))
                path = Path(result["upload"]["local_path"])
                self.assertEqual(path.read_bytes(), png)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                status, replay = ui.request(
                    "/v1/ui/upload", method="POST", body=png, headers=headers
                )
                self.assertEqual(status, 200)
                self.assertEqual(replay["upload"]["disposition"], "already_present")
                bad_headers = {**headers, "Content-Type": "image/jpeg"}
                status, denied = ui.request(
                    "/v1/ui/upload", method="POST", body=png, headers=bad_headers
                )
                self.assertEqual(status, 400)
                self.assertIn("do not match", denied["message"])
            finally:
                ui.close()
            self.assertFalse(workspace.exists())

    def test_abandoned_UI_workspaces_are_pruned_at_the_release_retention_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            sessions = base / "work/application/ui-sessions"
            sessions.mkdir(parents=True)
            abandoned = sessions / "ui_abandoned123"
            abandoned.mkdir()
            (abandoned / "reference.png").write_bytes(b"expired fixture")
            now = 500_000_000.0
            old = now - WORKSPACE_RETENTION_SECONDS - 1
            os.utime(abandoned / "reference.png", (old, old))
            os.utime(abandoned, (old, old))
            unrelated = sessions / "manual_folder"
            unrelated.mkdir()
            os.utime(unrelated, (old, old))
            outside = base / "outside"
            outside.mkdir()
            linked = sessions / "ui_linked123"
            linked.symlink_to(outside, target_is_directory=True)
            store = SessionAssetStore(base, wall_clock=lambda: now)
            try:
                self.assertFalse(abandoned.exists())
                self.assertTrue(unrelated.exists())
                self.assertTrue(linked.is_symlink())
                self.assertTrue(outside.exists())
            finally:
                store.close()

    def test_guided_UI_transport_reaches_real_intent_score_and_build_kernel(self) -> None:
        text = (
            "Create a natural UGC product video. Make it feel like a real friend "
            "recommendation. Show the product clearly. Keep it casual and end with a soft CTA."
        )
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            operational = base / "application"

            def actual(request: dict, **kwargs: object) -> dict:
                with mock.patch(
                    "lab.application.service._application_work_root",
                    return_value=operational,
                ):
                    return invoke(
                        request,
                        role=str(kwargs["role"]),
                        root=REPO_ROOT,
                    )

            ui = UIServer(base, role="chat", invoke_fn=actual)
            try:
                ui.bootstrap()
                envelope = {
                    "request": application_request(
                        "cpcs.production.prepare",
                        {
                            "text": text,
                            "project_id": "local-video-001",
                            "assets": [
                                {
                                    "asset_id": "asset_ui_product_reference",
                                    "role": "product_reference",
                                    "content_hash": "sha256:" + "a" * 64,
                                    "rights_basis": "original",
                                }
                            ],
                        },
                    )
                }
                status, response = ui.post_invoke(envelope)
                self.assertEqual(status, 200, response)
                result = response["result"]
                self.assertEqual(result["normalized_intent"]["profiles"]["primary"], "ugc")
                self.assertEqual(result["score"]["score_status"], "ready")
                self.assertRegex(result["score"]["score_id"], r"^score_[0-9a-f]{32}$")
                self.assertRegex(result["build"]["build_id"], r"^build_[0-9a-f]{32}$")
                self.assertTrue(Path(result["build"]["output_dir"]).is_dir())
            finally:
                ui.close()

    def test_graphical_runtime_path_registers_approves_runs_and_replays_once(self) -> None:
        text = (
            "Create a natural UGC product video. Show the product clearly and end with a soft CTA."
        )
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            operational = base / "application"
            adapter = FakeAdapter()

            def runner(root: Path) -> RenderRunner:
                return RenderRunner(
                    JobJournal(operational / "render" / "jobs.sqlite3"),
                    root=root,
                    work_root=operational / "render" / "jobs",
                    adapters={adapter.adapter_id: adapter},
                    sleep_fn=lambda _: None,
                )

            def actual(request: dict, **kwargs: object) -> dict:
                with mock.patch(
                    "lab.application.service._application_work_root",
                    return_value=operational,
                ), mock.patch(
                    "lab.application.service._render_runner",
                    side_effect=runner,
                ):
                    return invoke(
                        request,
                        role=str(kwargs["role"]),
                        root=REPO_ROOT,
                    )

            ui = UIServer(base, role="operator", invoke_fn=actual)
            try:
                ui.bootstrap()
                prepared_envelope = {
                    "request": application_request(
                        "cpcs.production.prepare",
                        {
                            "text": text,
                            "project_id": "local-video-002",
                            "platform": "youtube_shorts",
                            "assets": [
                                {
                                    "asset_id": "asset_ui_runtime_product",
                                    "role": "product_reference",
                                    "content_hash": "sha256:" + "b" * 64,
                                    "rights_basis": "original",
                                }
                            ],
                        },
                    )
                }
                status, prepared = ui.post_invoke(prepared_envelope)
                self.assertEqual(status, 200, prepared)
                self.assertEqual(
                    prepared["result"]["score"]["project"]["platform"],
                    "youtube_shorts",
                )
                build_id = prepared["result"]["build"]["build_id"]
                create_envelope = {
                    "request": application_request(
                        "cpcs.render.create",
                        {
                            "build_id": build_id,
                            "idempotency_key": "graphical-runtime-fixture",
                            "poll_interval_seconds": 0,
                        },
                    )
                }
                status, created = ui.post_invoke(create_envelope)
                self.assertEqual(status, 200, created)
                job_id = created["result"]["job"]["job_id"]
                run_envelope = {
                    "request": application_request(
                        "cpcs.render.run", {"job_id": job_id}
                    ),
                    "approval": {
                        "confirmed": True,
                        "reason": "Approve the exact graphical runtime fixture",
                    },
                }
                status, rendered = ui.post_invoke(run_envelope)
                self.assertEqual(status, 200, rendered)
                self.assertEqual(rendered["result"]["state"], "succeeded")
                self.assertEqual(adapter.submit_count, 1)
                status, replay = ui.post_invoke(run_envelope)
                self.assertEqual(status, 200, replay)
                self.assertEqual(replay["result"], rendered["result"])
                self.assertEqual(adapter.submit_count, 1)
                status, shown = ui.post_invoke(
                    {
                        "request": application_request(
                            "cpcs.render.show", {"job_id": job_id}
                        )
                    }
                )
                self.assertEqual(status, 200, shown)
                self.assertEqual(shown["result"]["state"], "succeeded")
            finally:
                ui.close()

    def test_session_expires_without_refreshing_on_invalid_credentials(self) -> None:
        now = [10.0]
        session = LocalUISession(
            role="chat",
            user="ui-test-user",
            clock=lambda: now[0],
            bootstrap_token="bootstrap",
            session_token="session",
            csrf_token="csrf",
        )
        self.assertTrue(session.exchange("bootstrap"))
        before = session.last_seen
        now[0] += 5
        self.assertFalse(session.authenticate("wrong"))
        self.assertEqual(session.last_seen, before)
        now[0] = before + SESSION_IDLE_SECONDS + 0.1
        self.assertFalse(session.authenticate("session"))

    def test_packaged_markup_is_semantic_keyboard_visible_and_script_safe(self) -> None:
        web = REPO_ROOT / "lab/application/web"
        html = (web / "index.html").read_text(encoding="utf-8")
        css = (web / "app.css").read_text(encoding="utf-8")
        script = (web / "app.js").read_text(encoding="utf-8")
        parser = MarkupInventory()
        parser.feed(html)
        self.assertEqual(parser.landmarks, {"header", "nav", "main", "footer"})
        self.assertEqual(parser.inline_scripts, 0)
        self.assertEqual(parser.inline_styles, 0)
        self.assertEqual(parser.controls - parser.labels, set())
        self.assertIn('class="skip-link"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn(":focus-visible", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertNotIn("innerHTML", script)
        self.assertNotIn("eval(", script)
        source = (REPO_ROOT / "lab/application/ui.py").read_text(encoding="utf-8")
        for forbidden in (
            "from lab.compiler",
            "from lab.second_brain.src.intent",
            "from lab.second_brain.src.context",
            "from lab.second_brain.src.query",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
