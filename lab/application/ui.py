"""Session-bound local graphical client over the CPCS application service."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import pwd
import re
import secrets
import shutil
import stat
import tempfile
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from lab.second_brain.src.validate import REPO_ROOT

from .service import (
    AUTHORIZATION_SCHEMA,
    REQUEST_SCHEMA,
    authorization_request_hash,
    invoke,
    list_operations,
)
from .telemetry import TelemetrySink

UI_POLICY = "cpcs-local-ui/1.0"
COOKIE_NAME = "cpcs_ui_session"
SESSION_IDLE_SECONDS = 30 * 60
WORKSPACE_RETENTION_SECONDS = 30 * 24 * 60 * 60
MAX_REQUEST_BYTES = 4 * 1024 * 1024
MAX_UPLOAD_BYTES = 32 * 1024 * 1024
ALLOWED_UPLOADS = {
    "image/jpeg": ("jpg", lambda value: value.startswith(b"\xff\xd8\xff")),
    "image/png": ("png", lambda value: value.startswith(b"\x89PNG\r\n\x1a\n")),
    "video/mp4": (
        "mp4",
        lambda value: len(value) >= 12 and value[4:8] == b"ftyp",
    ),
    "video/quicktime": (
        "mov",
        lambda value: len(value) >= 12 and value[4:8] == b"ftyp",
    ),
    "video/webm": ("webm", lambda value: value.startswith(b"\x1aE\xdf\xa3")),
}
ROLE_PATTERN = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
RIGHTS_SCOPES = {"authorized", "licensed", "original"}
InvokeFunction = Callable[..., dict[str, Any]]


def _token() -> str:
    return secrets.token_urlsafe(32)


@dataclass
class LocalUISession:
    """One process-local browser session established by a single-use secret."""

    role: str
    user: str
    clock: Callable[[], float] = time.monotonic
    bootstrap_token: str = field(default_factory=_token)
    session_token: str = field(default_factory=_token)
    csrf_token: str = field(default_factory=_token)
    bootstrap_consumed: bool = False
    last_seen: float = field(init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        self.last_seen = self.clock()

    def exchange(self, supplied: str) -> bool:
        with self._lock:
            if self.bootstrap_consumed or not supplied:
                return False
            if not hmac.compare_digest(supplied, self.bootstrap_token):
                return False
            self.bootstrap_consumed = True
            self.bootstrap_token = ""
            self.last_seen = self.clock()
            return True

    def authenticate(self, supplied: str | None, *, refresh: bool = True) -> bool:
        with self._lock:
            now = self.clock()
            if now - self.last_seen > SESSION_IDLE_SECONDS:
                return False
            if not supplied or not hmac.compare_digest(supplied, self.session_token):
                return False
            if refresh:
                self.last_seen = now
            return True

    def refresh(self) -> None:
        with self._lock:
            self.last_seen = self.clock()


def _safe_session_workspace(
    root: Path,
    *,
    wall_clock: Callable[[], float] = time.time,
) -> Path:
    root = root.resolve(strict=True)
    work = root / "work"
    if work.exists() and work.is_symlink():
        raise ValueError("work directory cannot be a symlink")
    work.mkdir(mode=0o700, exist_ok=True)
    base = work / "application" / "ui-sessions"
    for path in (work / "application", base):
        if path.exists() and path.is_symlink():
            raise ValueError("UI workspace ancestor cannot be a symlink")
        path.mkdir(mode=0o700, exist_ok=True)
        os.chmod(path, 0o700)
    now = wall_clock()
    for candidate in base.iterdir():
        if not re.fullmatch(r"ui_[A-Za-z0-9_-]+", candidate.name):
            continue
        if candidate.is_symlink() or not candidate.is_dir():
            continue
        candidate_stat = candidate.stat()
        if now - candidate_stat.st_mtime <= WORKSPACE_RETENTION_SECONDS:
            continue
        resolved_candidate = candidate.resolve(strict=True)
        if base.resolve(strict=True) not in resolved_candidate.parents:
            raise ValueError("stale UI workspace escaped ignored work state")
        shutil.rmtree(resolved_candidate)
    workspace = Path(tempfile.mkdtemp(prefix="ui_", dir=base))
    resolved = workspace.resolve(strict=True)
    if base.resolve(strict=True) not in resolved.parents:
        raise ValueError("UI workspace escaped ignored work state")
    os.chmod(resolved, 0o700)
    return resolved


class SessionAssetStore:
    """Ephemeral exact-byte reference uploads owned by one UI session."""

    def __init__(
        self,
        root: Path = REPO_ROOT,
        *,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        self.workspace = _safe_session_workspace(root, wall_clock=wall_clock)
        self.uploads = self.workspace / "uploads"
        self.uploads.mkdir(mode=0o700)

    def stage(
        self,
        content: bytes,
        *,
        mime_type: str,
        role: str,
        rights_basis: str,
    ) -> dict[str, Any]:
        if not content or len(content) > MAX_UPLOAD_BYTES:
            raise ValueError("reference file size is outside the local UI limit")
        if mime_type not in ALLOWED_UPLOADS:
            raise ValueError("reference media type is not supported")
        extension, matches = ALLOWED_UPLOADS[mime_type]
        if not matches(content):
            raise ValueError("reference bytes do not match the declared media type")
        if not ROLE_PATTERN.fullmatch(role):
            raise ValueError("reference role must be a safe lower-case identifier")
        if rights_basis not in RIGHTS_SCOPES:
            raise ValueError("reference rights basis is not allowed")
        digest = hashlib.sha256(content).hexdigest()
        identity = hashlib.sha256(
            json.dumps(
                {
                    "content_hash": f"sha256:{digest}",
                    "role": role,
                    "rights_basis": rights_basis,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:32]
        asset_id = f"asset_{identity}"
        path = self.uploads / f"{asset_id}.{extension}"
        resolved_parent = path.parent.resolve(strict=True)
        if resolved_parent != self.uploads.resolve(strict=True):
            raise ValueError("reference path escaped the session workspace")
        if path.exists():
            existing_stat = path.stat()
            if (
                path.is_symlink()
                or not stat.S_ISREG(existing_stat.st_mode)
                or existing_stat.st_nlink != 1
                or existing_stat.st_mode & 0o777 != 0o600
            ):
                raise ValueError("existing reference path is unsafe")
            if path.read_bytes() != content:
                raise ValueError("reference identity collides with different bytes")
            disposition = "already_present"
        else:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(path, flags, 0o600)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
            except Exception:
                path.unlink(missing_ok=True)
                raise
            disposition = "created"
        return {
            "schema": "cpcs.local_ui_asset/1.0",
            "asset": {
                "asset_id": asset_id,
                "role": role,
                "content_hash": f"sha256:{digest}",
                "rights_basis": rights_basis,
            },
            "upload": {
                "mime_type": mime_type,
                "size_bytes": len(content),
                "local_path": str(path),
                "disposition": disposition,
                "retention": "deleted_when_the_UI_session_exits",
            },
        }

    def close(self) -> None:
        base = self.workspace.parent.resolve(strict=True)
        resolved = self.workspace.resolve(strict=True)
        if base not in resolved.parents or not self.workspace.name.startswith("ui_"):
            raise ValueError("refusing to remove an unsafe UI workspace")
        shutil.rmtree(resolved)


def _cookie_value(raw: str | None) -> str | None:
    if not raw:
        return None
    cookie = SimpleCookie()
    try:
        cookie.load(raw)
    except Exception:
        return None
    morsel = cookie.get(COOKIE_NAME)
    return morsel.value if morsel else None


def _allowed_origins(port: int) -> set[str]:
    return {
        f"http://127.0.0.1:{port}",
        f"http://localhost:{port}",
        f"http://[::1]:{port}",
    }


def make_ui_handler(
    *,
    role: str,
    session: LocalUISession,
    asset_store: SessionAssetStore,
    root: Path = REPO_ROOT,
    telemetry: TelemetrySink | None = None,
    invoke_fn: InvokeFunction = invoke,
) -> type[BaseHTTPRequestHandler]:
    """Build a local UI handler without moving domain logic into the client."""
    if role not in {"chat", "operator", "curator"}:
        raise ValueError("unknown UI role")
    static_root = Path(__file__).resolve().parent / "web"
    static_files = {
        "/": (static_root / "index.html", "text/html; charset=utf-8"),
        "/assets/app.css": (static_root / "app.css", "text/css; charset=utf-8"),
        "/assets/app.js": (static_root / "app.js", "text/javascript; charset=utf-8"),
    }
    catalog = {row["name"]: row for row in list_operations(role)}

    class CPCSUIHandler(BaseHTTPRequestHandler):
        server_version = "CPCS-Local-UI/1.0"

        def _origins(self) -> set[str]:
            return _allowed_origins(int(self.server.server_address[1]))

        def _host_is_local(self) -> bool:
            host = self.headers.get("Host", "")
            return any(host == origin.removeprefix("http://") for origin in self._origins())

        def _security_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")

        def _write_bytes(
            self,
            status: int,
            body: bytes,
            content_type: str,
            *,
            cookie: str | None = None,
            location: str | None = None,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self._security_headers()
            if cookie is not None:
                self.send_header(
                    "Set-Cookie",
                    f"{COOKIE_NAME}={cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_IDLE_SECONDS}",
                )
            if location is not None:
                self.send_header("Location", location)
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _write_json(self, status: int, value: dict[str, Any]) -> None:
            body = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
            self._write_bytes(status, body, "application/json; charset=utf-8")

        def _error(self, status: int, code: str, message: str) -> None:
            self._write_json(status, {"error": code, "message": message})

        def _authenticated(self) -> bool:
            return self._host_is_local() and session.authenticate(
                _cookie_value(self.headers.get("Cookie"))
            )

        def _post_authorized(self) -> bool:
            if not self._host_is_local() or not session.authenticate(
                _cookie_value(self.headers.get("Cookie")), refresh=False
            ):
                self._error(401, "session_required", "A valid local UI session is required.")
                return False
            origin = self.headers.get("Origin")
            if origin not in self._origins():
                self._error(403, "origin_denied", "The request origin is not the local UI.")
                return False
            supplied = self.headers.get("X-CPCS-CSRF", "")
            if not hmac.compare_digest(supplied, session.csrf_token):
                self._error(403, "csrf_denied", "The session request token is invalid.")
                return False
            session.refresh()
            return True

        def _read_body(self, maximum: int) -> bytes:
            raw_length = self.headers.get("Content-Length", "")
            if not raw_length.isdigit():
                raise ValueError("request body length is missing")
            length = int(raw_length)
            if length <= 0 or length > maximum:
                raise ValueError("request body length is outside the allowed limit")
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError("request body ended before the declared length")
            return body

        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlsplit(self.path)
            if parsed.path == "/healthz":
                self._write_json(200, {"status": "ok", "policy": UI_POLICY})
                return
            if not self._host_is_local():
                self._error(421, "host_denied", "The host is not a local UI origin.")
                return
            bootstrap = urllib.parse.parse_qs(parsed.query).get("bootstrap", [])
            if parsed.path == "/" and len(bootstrap) == 1:
                if session.exchange(bootstrap[0]):
                    self._write_bytes(
                        303,
                        b"",
                        "text/plain; charset=utf-8",
                        cookie=session.session_token,
                        location="/",
                    )
                else:
                    self._error(401, "bootstrap_denied", "The bootstrap link is invalid or already used.")
                return
            if not self._authenticated():
                self._error(401, "session_required", "Open the one-time URL printed by cpcs-ui.")
                return
            if parsed.path == "/v1/ui/session":
                self._write_json(
                    200,
                    {
                        "schema": "cpcs.local_ui_session/1.0",
                        "policy": UI_POLICY,
                        "identity": session.user,
                        "role": role,
                        "csrf_token": session.csrf_token,
                        "session_idle_seconds": SESSION_IDLE_SECONDS,
                        "operations": list(catalog.values()),
                    },
                )
                return
            static = static_files.get(parsed.path)
            if static is None:
                self._error(404, "not_found", "The requested local UI resource does not exist.")
                return
            path, content_type = static
            if not path.is_file() or static_root.resolve() not in path.resolve().parents:
                self._error(500, "asset_missing", "A packaged UI asset is unavailable.")
                return
            self._write_bytes(200, path.read_bytes(), content_type)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlsplit(self.path)
            if not self._post_authorized():
                return
            try:
                if parsed.path == "/v1/ui/invoke":
                    self._invoke_request()
                    return
                if parsed.path == "/v1/ui/upload":
                    self._upload_reference()
                    return
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                self._error(400, "invalid_request", str(exc))
                return
            self._error(404, "not_found", "The requested local UI operation does not exist.")

        def _invoke_request(self) -> None:
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/json":
                raise ValueError("invoke requests require application/json")
            envelope = json.loads(self._read_body(MAX_REQUEST_BYTES).decode("utf-8"))
            if not isinstance(envelope, dict) or not set(envelope) <= {"request", "approval"}:
                raise ValueError("UI invoke envelope contains undeclared fields")
            request = envelope.get("request")
            if not isinstance(request, dict):
                raise ValueError("UI invoke envelope requires one request object")
            if "authorization" in request:
                raise ValueError("browser-supplied authorization is forbidden")
            operation = request.get("operation")
            spec = catalog.get(operation)
            if spec is None:
                raise ValueError("operation is not available to this UI role")
            approval = envelope.get("approval")
            if spec["authorization_required"]:
                if not isinstance(approval, dict) or set(approval) != {"confirmed", "reason"}:
                    raise ValueError("this operation requires an explicit UI approval")
                reason = approval.get("reason")
                if approval.get("confirmed") is not True or not isinstance(reason, str) or not reason.strip():
                    raise ValueError("the exact side effect must be confirmed with a reason")
                if len(reason) > 500:
                    raise ValueError("approval reason exceeds 500 characters")
                arguments = request.get("arguments")
                if not isinstance(arguments, dict):
                    raise ValueError("application request arguments must be an object")
                request_hash = authorization_request_hash(operation, arguments)
                request = dict(request)
                request["authorization"] = {
                    "schema": AUTHORIZATION_SCHEMA,
                    "authorization_id": "auth_ui_" + request_hash.removeprefix("sha256:")[:24],
                    "authorized_by": f"local-os-account:{session.user}",
                    "operation": operation,
                    "request_hash": request_hash,
                    "reason": reason.strip(),
                }
            elif approval is not None:
                raise ValueError("approval is accepted only for a controlled side effect")
            response = invoke_fn(
                request,
                role=role,
                root=root,
                telemetry=telemetry,
            )
            status = 200 if response.get("status") == "success" else (
                403 if response.get("error", {}).get("code") == "permission_denied" else 400
            )
            self._write_json(status, response)

        def _upload_reference(self) -> None:
            mime_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            role_name = self.headers.get("X-CPCS-Asset-Role", "")
            rights_basis = self.headers.get("X-CPCS-Rights-Basis", "")
            result = asset_store.stage(
                self._read_body(MAX_UPLOAD_BYTES),
                mime_type=mime_type,
                role=role_name,
                rights_basis=rights_basis,
            )
            self._write_json(200, result)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return CPCSUIHandler


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--role", choices=("chat", "operator", "curator"), default="operator")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--telemetry", type=Path)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args(argv)
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("cpcs-ui is a local loopback surface only")
    root = args.root.resolve(strict=True)
    telemetry = TelemetrySink(args.telemetry, root=root) if args.telemetry else None
    session = LocalUISession(role=args.role, user=pwd.getpwuid(os.getuid()).pw_name)
    asset_store = SessionAssetStore(root)
    server = ThreadingHTTPServer(
        (args.host, args.port),
        make_ui_handler(
            role=args.role,
            session=session,
            asset_store=asset_store,
            root=root,
            telemetry=telemetry,
        ),
    )
    port = int(server.server_address[1])
    display_host = "[::1]" if args.host == "::1" else args.host
    url = f"http://{display_host}:{port}/?bootstrap={urllib.parse.quote(session.bootstrap_token)}"
    print(
        json.dumps(
            {
                "policy": UI_POLICY,
                "url": url,
                "role": args.role,
                "identity": session.user,
                "security_boundary": "local_loopback_single_os_account",
            },
            sort_keys=True,
        ),
        flush=True,
    )
    if not args.no_open:
        webbrowser.open(url, new=2)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        asset_store.close()


if __name__ == "__main__":
    main()
