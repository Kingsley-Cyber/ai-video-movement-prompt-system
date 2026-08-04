"""Local HTTP adapter over the CPCS application service."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from lab.second_brain.src.validate import REPO_ROOT

from .service import REQUEST_SCHEMA, invoke
from .telemetry import TelemetrySink

MAX_REQUEST_BYTES = 4 * 1024 * 1024


def make_handler(
    role: str = "chat",
    root: Path = REPO_ROOT,
    telemetry: TelemetrySink | None = None,
) -> type[BaseHTTPRequestHandler]:
    class CPCSHandler(BaseHTTPRequestHandler):
        server_version = "CPCS/1.0"

        def _write(self, status: int, value: dict[str, Any]) -> None:
            body = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/v1/status":
                self._write(404, {"error": "not_found"})
                return
            response = invoke(
                {"schema": REQUEST_SCHEMA, "operation": "cpcs.status", "arguments": {}},
                role=role,
                root=root,
                telemetry=telemetry,
            )
            self._write(200, response)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/invoke":
                self._write(404, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_REQUEST_BYTES:
                    raise ValueError("request body length is invalid")
                request = json.loads(self.rfile.read(length))
                if not isinstance(request, dict):
                    raise ValueError("request body must be an object")
                response = invoke(
                    request, role=role, root=root, telemetry=telemetry
                )
            except (ValueError, json.JSONDecodeError) as exc:
                self._write(400, {"error": "invalid_json", "message": str(exc)})
                return
            status = 200 if response["status"] == "success" else (
                403 if response["error"]["code"] == "permission_denied" else 400
            )
            self._write(status, response)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return CPCSHandler


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--role", choices=("chat", "operator", "curator"), default="chat")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--telemetry", type=Path)
    args = parser.parse_args(argv)
    if args.role != "chat" and args.host not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("operator and curator HTTP roles are limited to loopback in this local facade")
    root = args.root.resolve()
    telemetry = TelemetrySink(args.telemetry, root=root) if args.telemetry else None
    server = ThreadingHTTPServer(
        (args.host, args.port), make_handler(args.role, root, telemetry)
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
