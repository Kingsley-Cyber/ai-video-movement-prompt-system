from __future__ import annotations

import hashlib
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from lab.second_brain.src.providers.polymath import (
    LEGACY_PROTOCOL,
    MODERN_PROTOCOL,
    MAX_RESPONSE_BYTES,
    PolymathMCPError,
    StreamableHTTPClient,
    _schema_header_bindings,
    _validated_endpoint,
    configuration_status,
    doctor,
    retrieve,
)
from lab.second_brain.src.source_extract import extract_retrieved_passages
from lab.second_brain.src.validate import REPO_ROOT, validate_instance


def authority_snapshot(root: Path = REPO_ROOT) -> dict[str, bytes]:
    paths = [root / "lab" / "concepts.jsonl"]
    second_brain = root / "lab" / "second_brain"
    for tier in ("curated", "immutable", "derived", "staging"):
        paths.extend(path for path in (second_brain / tier).rglob("*") if path.is_file())
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(paths)
    }


def search_result(*, duplicate: bool = False) -> dict:
    chunks = [
        {
            "corpus_id": "corpus-001",
            "doc_id": "doc-001",
            "chunk_id": "chunk-001",
            "parent_id": "parent-001",
            "filename": "Laban Direction Notes",
            "text": "Decimal spatial waypoints can preserve small directed changes.",
            "score": 0.91,
        },
        {
            "corpus_id": "corpus-001",
            "doc_id": "doc-002",
            "chunk_id": "chunk-004",
            "parent_id": None,
            "title": "Contained Motion",
            "text": "Bound Flow supports contained movement direction when used as an explicit staging choice.",
            "score": 0.83,
        },
    ]
    if duplicate:
        chunks.append(dict(chunks[0]))
    return {
        "chunks": chunks,
        "corpus_ids": ["corpus-001"],
        "requested_tier": "qdrant_mongo",
        "effective_tier": "qdrant_mongo",
        "downgrade_reason": None,
    }


class PolymathFixture:
    def __init__(
        self,
        *,
        protocol: str,
        sse: bool = False,
        result: dict | None = None,
        include_cross_search: bool = True,
        legacy_discovery_status: int = 404,
    ) -> None:
        self.protocol = protocol
        self.sse = sse
        self.result = result or search_result()
        self.include_cross_search = include_cross_search
        self.legacy_discovery_status = legacy_discovery_status
        self.token = "fixture-bearer-secret"
        self.session_id = "fixture-session-001"
        self.calls: list[dict] = []
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def _json(self, status: int, value: dict, *, session: bool = False) -> None:
                raw = json.dumps(value, sort_keys=True).encode("utf-8")
                if fixture.sse and status == 200:
                    raw = b"event: message\n" + b"data: " + raw + b"\n\n"
                    content_type = "text/event-stream"
                else:
                    content_type = "application/json"
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(raw)))
                if session:
                    self.send_header("Mcp-Session-Id", fixture.session_id)
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self) -> None:  # noqa: N802
                if self.headers.get("Authorization") != f"Bearer {fixture.token}":
                    self._json(
                        401,
                        {
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {"code": -32001, "message": "auth.unauthorized"},
                        },
                    )
                    return
                length = int(self.headers.get("Content-Length", "0"))
                message = json.loads(self.rfile.read(length))
                fixture.calls.append(
                    {
                        "message": message,
                        "protocol": self.headers.get("MCP-Protocol-Version"),
                        "method_header": self.headers.get("Mcp-Method"),
                        "name_header": self.headers.get("Mcp-Name"),
                        "session": self.headers.get("Mcp-Session-Id"),
                        "custom": self.headers.get("Mcp-Param-Corpus"),
                    }
                )
                method = message.get("method")
                request_id = message.get("id")
                if fixture.protocol == LEGACY_PROTOCOL and method == "server/discover":
                    self._json(
                        fixture.legacy_discovery_status,
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -32601, "message": "Method not found"},
                        },
                    )
                    return
                if fixture.protocol == MODERN_PROTOCOL:
                    self.assert_modern_headers(message)
                    if method == "server/discover":
                        self._json(
                            200,
                            {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "result": {
                                    "resultType": "complete",
                                    "supportedVersions": [MODERN_PROTOCOL],
                                    "capabilities": {"tools": {}},
                                    "_meta": {
                                        "io.modelcontextprotocol/serverInfo": {
                                            "name": "polymath-modern",
                                            "version": "2.0.0",
                                        }
                                    },
                                },
                            },
                        )
                        return
                elif method == "initialize":
                    self._json(
                        200,
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "protocolVersion": LEGACY_PROTOCOL,
                                "capabilities": {"tools": {}},
                                "serverInfo": {
                                    "name": "polymath-legacy",
                                    "version": "1.28.1",
                                },
                            },
                        },
                        session=True,
                    )
                    return
                elif method == "notifications/initialized":
                    if self.headers.get("Mcp-Session-Id") != fixture.session_id:
                        self._json(400, {"error": "session missing"})
                    else:
                        self.send_response(202)
                        self.send_header("Content-Length", "0")
                        self.end_headers()
                    return
                elif self.headers.get("Mcp-Session-Id") != fixture.session_id:
                    self._json(400, {"error": "session missing"})
                    return
                if method == "tools/list":
                    names = ["polymath_search"]
                    if fixture.include_cross_search:
                        names.append("polymath_cross_corpus_search")
                    tools = [
                        {
                            "name": name,
                            "description": "Read-only fixture search",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"},
                                    "corpus_ids": {"type": ["array", "null"]},
                                },
                            },
                        }
                        for name in names
                    ]
                    self._json(
                        200,
                        {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}},
                    )
                    return
                if method == "tools/call":
                    self._json(
                        200,
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": json.dumps(fixture.result, sort_keys=True),
                                    }
                                ]
                            },
                        },
                    )
                    return
                self._json(
                    404,
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": "Method not found"},
                    },
                )

            def assert_modern_headers(self, message: dict) -> None:
                if self.headers.get("MCP-Protocol-Version") != MODERN_PROTOCOL:
                    raise AssertionError("modern protocol header missing")
                if self.headers.get("Mcp-Method") != message.get("method"):
                    raise AssertionError("modern method header mismatch")
                if message.get("method") == "tools/call":
                    if self.headers.get("Mcp-Name") != message["params"]["name"]:
                        raise AssertionError("modern tool name header mismatch")
                meta = message.get("params", {}).get("_meta", {})
                if meta.get("io.modelcontextprotocol/protocolVersion") != MODERN_PROTOCOL:
                    raise AssertionError("modern body protocol metadata missing")

            def log_message(self, format: str, *args: object) -> None:
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_address[1]}/mcp"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class PolymathMCPTests(unittest.TestCase):
    def test_configuration_and_endpoint_policy_are_credential_safe(self) -> None:
        status = configuration_status({})
        self.assertEqual(status["status"], "credential_required")
        self.assertFalse(status["credential_configured"])
        self.assertNotIn("127.0.0.1", json.dumps(status))
        self.assertEqual(
            _validated_endpoint("http://localhost:8765/mcp"),
            "http://localhost:8765/mcp",
        )
        for endpoint in (
            "http://example.com/mcp",
            "ftp://127.0.0.1/mcp",
            "https://user:secret@example.com/mcp",
            "https://example.com/not-mcp",
        ):
            with self.subTest(endpoint=endpoint), self.assertRaises(PolymathMCPError):
                _validated_endpoint(endpoint)

    def test_legacy_session_negotiation_sse_retrieval_and_distiller_handoff(self) -> None:
        fixture = PolymathFixture(protocol=LEGACY_PROTOCOL, sse=True)
        before = authority_snapshot()
        try:
            package = retrieve(
                "decimal spatial movement",
                corpus_ids=["corpus-001"],
                rights_basis="owner_authorized_research",
                endpoint=fixture.endpoint,
                token=fixture.token,
                top_k=2,
                retrieved_at="2026-08-04T00:00:00Z",
            )
            validate_instance("polymath_retrieval", package)
            self.assertEqual(package["protocol"]["protocol_version"], LEGACY_PROTOCOL)
            self.assertEqual(package["diagnostics"]["returned_count"], 2)
            expected = hashlib.sha256(
                package["retrieved_passages"]["passages"][0]["text"].encode("utf-8")
            ).hexdigest()
            self.assertEqual(
                package["retrieved_passages"]["passages"][0]["content_hash"],
                "sha256:" + expected,
            )
            bundle = extract_retrieved_passages(package["retrieved_passages"])
            self.assertEqual(bundle["source_kind"], "polymath_passages")
            self.assertEqual(bundle["distillation_batch"]["retrieval"]["tool"], "polymath_search")
            self.assertNotIn(fixture.token, json.dumps(package))
            self.assertEqual(before, authority_snapshot())
            methods = [call["message"].get("method") for call in fixture.calls]
            self.assertEqual(
                methods[:4],
                ["server/discover", "initialize", "notifications/initialized", "tools/list"],
            )
            self.assertTrue(
                all(
                    call["session"] == fixture.session_id
                    for call in fixture.calls
                    if call["message"].get("method") in {"tools/list", "tools/call"}
                )
            )
        finally:
            fixture.close()

    def test_legacy_fallback_accepts_jsonrpc_method_not_found_over_http_200(self) -> None:
        fixture = PolymathFixture(
            protocol=LEGACY_PROTOCOL,
            legacy_discovery_status=200,
        )
        try:
            result = doctor(endpoint=fixture.endpoint, token=fixture.token)
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["protocol_version"], LEGACY_PROTOCOL)
        finally:
            fixture.close()

    def test_modern_discovery_headers_and_context_evidence(self) -> None:
        fixture = PolymathFixture(protocol=MODERN_PROTOCOL)
        try:
            package = retrieve(
                "restrained bound flow",
                corpus_ids=["corpus-001"],
                rights_basis="owner_authorized_research",
                endpoint=fixture.endpoint,
                token=fixture.token,
                top_k=2,
                retrieved_at="2026-08-04T00:00:00Z",
            )
            self.assertEqual(package["protocol"]["protocol_version"], MODERN_PROTOCOL)
            self.assertEqual(package["protocol"]["server_name"], "polymath-modern")
            self.assertEqual(package["diagnostics"]["upstream_count"], 2)
            self.assertEqual(package["diagnostics"]["truncated_count"], 0)
            evidence = package["context_evidence"][0]
            self.assertEqual(evidence["trust_class"], "untrusted_external_evidence")
            self.assertEqual(evidence["metadata"]["rank"], 1)
            self.assertEqual(evidence["score"], 0.91)
            calls = {
                call["message"].get("method"): call for call in fixture.calls
            }
            self.assertEqual(calls["tools/call"]["method_header"], "tools/call")
            self.assertEqual(calls["tools/call"]["name_header"], "polymath_search")
            self.assertIsNone(calls["tools/call"]["session"])
        finally:
            fixture.close()

    def test_exact_duplicates_are_omitted_but_locator_collisions_fail(self) -> None:
        fixture = PolymathFixture(protocol=LEGACY_PROTOCOL, result=search_result(duplicate=True))
        try:
            package = retrieve(
                "decimal spatial movement",
                corpus_ids=["corpus-001"],
                rights_basis="owner_authorized_research",
                endpoint=fixture.endpoint,
                token=fixture.token,
                top_k=3,
                retrieved_at="2026-08-04T00:00:00Z",
            )
            self.assertEqual(package["diagnostics"]["returned_count"], 2)
            self.assertEqual(package["diagnostics"]["duplicate_count"], 1)
        finally:
            fixture.close()
        collision = search_result()
        collision["chunks"].append(
            {**collision["chunks"][0], "text": "different bytes at the same locator"}
        )
        fixture = PolymathFixture(protocol=LEGACY_PROTOCOL, result=collision)
        try:
            with self.assertRaisesRegex(PolymathMCPError, "different bytes"):
                retrieve(
                    "decimal spatial movement",
                    corpus_ids=["corpus-001"],
                    rights_basis="owner_authorized_research",
                    endpoint=fixture.endpoint,
                    token=fixture.token,
                    top_k=3,
                    retrieved_at="2026-08-04T00:00:00Z",
                )
        finally:
            fixture.close()

    def test_scope_tool_bounds_and_empty_content_fail_closed(self) -> None:
        outside = search_result()
        outside["chunks"][0]["corpus_id"] = "other-corpus"
        for result, expected in (
            (outside, "outside the requested corpus"),
            ({**search_result(), "chunks": []}, "within the adapter passage limit"),
        ):
            fixture = PolymathFixture(protocol=LEGACY_PROTOCOL, result=result)
            try:
                with self.assertRaisesRegex(PolymathMCPError, expected):
                    retrieve(
                        "decimal spatial movement",
                        corpus_ids=["corpus-001"],
                        rights_basis="owner_authorized_research",
                        endpoint=fixture.endpoint,
                        token=fixture.token,
                        top_k=2,
                        retrieved_at="2026-08-04T00:00:00Z",
                    )
            finally:
                fixture.close()
        with self.assertRaises(PolymathMCPError):
            retrieve(
                "q",
                corpus_ids=[],
                rights_basis="authorized",
                tool="polymath_delete_everything",
                token="not-used",
            )
        for kwargs in (
            {"corpus_ids": "not-an-array"},
            {"corpus_ids": [], "rerank_enabled": 1},
            {"corpus_ids": [], "rights_basis": "x" * 1025},
            {"corpus_ids": [], "retrieved_at": "2026-08-04T00:00:00"},
        ):
            arguments = {
                "query": "q",
                "corpus_ids": [],
                "rights_basis": "authorized",
                "token": "not-used",
                **kwargs,
            }
            with self.subTest(kwargs=kwargs), self.assertRaises(PolymathMCPError):
                retrieve(**arguments)

    def test_provider_overreturn_is_deterministically_truncated(self) -> None:
        fixture = PolymathFixture(protocol=LEGACY_PROTOCOL)
        try:
            package = retrieve(
                "decimal spatial movement",
                corpus_ids=["corpus-001"],
                rights_basis="owner_authorized_research",
                endpoint=fixture.endpoint,
                token=fixture.token,
                top_k=1,
                retrieved_at="2026-08-04T00:00:00Z",
            )
            self.assertEqual(package["diagnostics"]["upstream_count"], 2)
            self.assertEqual(package["diagnostics"]["returned_count"], 1)
            self.assertEqual(package["diagnostics"]["truncated_count"], 1)
            self.assertEqual(
                package["retrieved_passages"]["passages"][0]["locator"],
                "chunk=chunk-001",
            )
        finally:
            fixture.close()

    def test_credential_bearing_requests_do_not_follow_redirects(self) -> None:
        calls = []

        class RedirectHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                calls.append(self.path)
                self.send_response(302)
                self.send_header("Location", "/mcp")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = StreamableHTTPClient(
                f"http://127.0.0.1:{server.server_address[1]}/mcp",
                "redirect-secret",
            )
            with self.assertRaises(PolymathMCPError):
                client.connect()
            self.assertEqual(calls, ["/mcp"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_doctor_reports_auth_and_tool_contract_without_secret_content(self) -> None:
        fixture = PolymathFixture(protocol=LEGACY_PROTOCOL, include_cross_search=False)
        try:
            report = doctor(endpoint=fixture.endpoint, token=fixture.token)
            self.assertEqual(report["status"], "tool_contract_incomplete")
            self.assertEqual(report["available_search_tools"], ["polymath_search"])
            self.assertEqual(report["missing_search_tools"], ["polymath_cross_corpus_search"])
            self.assertNotIn(fixture.token, json.dumps(report))
        finally:
            fixture.close()
        missing = doctor(endpoint="http://127.0.0.1:8765/mcp", token=None)
        self.assertEqual(missing["status"], "credential_required")
        self.assertFalse(missing["network_contacted"])

    def test_modern_custom_header_binding_encodes_and_rejects_unsafe_schema(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "corpus": {
                    "type": "string",
                    "x-mcp-header": "Corpus",
                }
            },
        }
        headers = _schema_header_bindings(schema, {"corpus": " cinéma "})
        self.assertTrue(headers["Mcp-Param-Corpus"].startswith("=?base64?"))
        invalid = {
            "type": "object",
            "oneOf": [
                {
                    "properties": {
                        "corpus": {
                            "type": "string",
                            "x-mcp-header": "Corpus",
                        }
                    }
                }
            ],
        }
        with self.assertRaises(PolymathMCPError):
            _schema_header_bindings(invalid, {"corpus": "c1"})

    def test_response_byte_limit_is_enforced_before_json_parsing(self) -> None:
        class OversizedResponse:
            headers = {
                "Content-Length": str(MAX_RESPONSE_BYTES + 1),
                "Content-Type": "application/json",
            }

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, size: int) -> bytes:
                return b""

        client = StreamableHTTPClient(
            "http://127.0.0.1:8765/mcp",
            "secret",
            opener=lambda request, timeout: OversizedResponse(),
        )
        with self.assertRaisesRegex(PolymathMCPError, "byte limit"):
            client.connect()


if __name__ == "__main__":
    unittest.main()
