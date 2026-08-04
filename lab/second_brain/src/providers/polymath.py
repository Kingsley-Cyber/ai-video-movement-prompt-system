"""Bounded authenticated Polymath MCP retrieval into CPCS evidence contracts."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from ..validate import REPO_ROOT, canonical_json_bytes, validate_instance

ADAPTER_POLICY = "cpcs-polymath-mcp/1.0"
MODERN_PROTOCOL = "2026-07-28"
LEGACY_PROTOCOL = "2025-11-25"
DEFAULT_ENDPOINT = "http://127.0.0.1:8765/mcp"
TOKEN_ENVIRONMENTS = ("POLYMATH_MCP_TOKEN", "MCP_API_KEY")
SEARCH_TOOLS = ("polymath_search", "polymath_cross_corpus_search")
RETRIEVAL_TIERS = ("qdrant_only", "qdrant_mongo", "qdrant_mongo_graph")
SEARCH_MODES = ("local", "global", "auto")
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_QUERY_BYTES = 4096
MAX_RIGHTS_BASIS_BYTES = 1024
MAX_PASSAGES = 12
MAX_PASSAGE_BYTES = 1024 * 1024
MAX_TOTAL_PASSAGE_BYTES = 4 * 1024 * 1024
MAX_TOOL_COUNT = 256
DEFAULT_TIMEOUT_SECONDS = 45
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_HEADER_NAME = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_BASE64_SENTINEL = re.compile(r"^=\?base64\?.*\?=$", re.DOTALL)


class PolymathMCPError(RuntimeError):
    """A bounded, credential-safe Polymath transport or contract error."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int | None = None,
        rpc_code: int | None = None,
        supported_versions: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.rpc_code = rpc_code
        self.supported_versions = supported_versions or []


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Any,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler()).open


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _endpoint_hash(endpoint: str) -> str:
    return _sha256_bytes(endpoint.encode("utf-8"))


def _validated_endpoint(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PolymathMCPError("endpoint_invalid", "Polymath MCP endpoint is missing")
    parsed = urllib.parse.urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise PolymathMCPError(
            "endpoint_invalid", "Polymath MCP endpoint must be an HTTP(S) URL"
        )
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise PolymathMCPError(
            "endpoint_invalid",
            "Polymath MCP endpoint cannot contain credentials, query, or fragment",
        )
    try:
        parsed.port
    except ValueError as exc:
        raise PolymathMCPError(
            "endpoint_invalid", "Polymath MCP endpoint port is invalid"
        ) from exc
    if parsed.scheme == "http" and parsed.hostname.lower() not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise PolymathMCPError(
            "endpoint_insecure",
            "Plain HTTP is allowed only for an exact loopback Polymath endpoint",
        )
    path = parsed.path.rstrip("/") or "/mcp"
    if not path.endswith("/mcp") and path != "/mcp":
        raise PolymathMCPError(
            "endpoint_invalid", "Polymath MCP endpoint path must end in /mcp"
        )
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, path, "", "")
    )


def _configuration(
    environ: Mapping[str, str] = os.environ,
) -> tuple[str, str | None, str | None]:
    endpoint = _validated_endpoint(
        environ.get("POLYMATH_MCP_URL", DEFAULT_ENDPOINT)
    )
    for name in TOKEN_ENVIRONMENTS:
        token = environ.get(name)
        if isinstance(token, str) and token.strip():
            return endpoint, token.strip(), name
    return endpoint, None, None


def _resolved_configuration(
    *,
    endpoint: str | None = None,
    token: str | None = None,
    environ: Mapping[str, str] = os.environ,
) -> tuple[str, str | None, str | None]:
    """Resolve explicit overrides without consulting an unrelated invalid env value."""
    resolved_endpoint = _validated_endpoint(
        endpoint if endpoint is not None else environ.get("POLYMATH_MCP_URL", DEFAULT_ENDPOINT)
    )
    if token is not None:
        stripped = token.strip() if isinstance(token, str) else ""
        return resolved_endpoint, stripped or None, "injected" if stripped else None
    for name in TOKEN_ENVIRONMENTS:
        candidate = environ.get(name)
        if isinstance(candidate, str) and candidate.strip():
            return resolved_endpoint, candidate.strip(), name
    return resolved_endpoint, None, None


def configuration_status(
    environ: Mapping[str, str] = os.environ,
) -> dict[str, Any]:
    """Return non-secret configuration truth without making a network request."""
    try:
        endpoint, token, source = _configuration(environ)
        return {
            "schema": "cpcs.polymath_configuration/1.0",
            "adapter_policy": ADAPTER_POLICY,
            "status": "configured_unprobed" if token else "credential_required",
            "endpoint_hash": _endpoint_hash(endpoint),
            "endpoint_transport": urllib.parse.urlsplit(endpoint).scheme,
            "credential_configured": bool(token),
            "credential_source": source,
            "network_contacted": False,
        }
    except PolymathMCPError as exc:
        return {
            "schema": "cpcs.polymath_configuration/1.0",
            "adapter_policy": ADAPTER_POLICY,
            "status": exc.code,
            "endpoint_hash": None,
            "endpoint_transport": None,
            "credential_configured": False,
            "credential_source": None,
            "network_contacted": False,
        }


def _parse_rpc_payload(raw: bytes, content_type: str) -> list[dict[str, Any]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PolymathMCPError(
            "response_encoding_invalid", "Polymath MCP response is not UTF-8"
        ) from exc
    values: list[Any] = []
    try:
        if "text/event-stream" in content_type:
            data_lines: list[str] = []
            for line in text.splitlines():
                if not line:
                    if data_lines:
                        values.append(json.loads("\n".join(data_lines)))
                        data_lines = []
                    continue
                if line.startswith(":"):
                    continue
                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip(" "))
            if data_lines:
                values.append(json.loads("\n".join(data_lines)))
        elif raw:
            values.append(json.loads(text))
    except json.JSONDecodeError as exc:
        raise PolymathMCPError(
            "response_json_invalid", "Polymath MCP response is not valid JSON"
        ) from exc
    if len(values) > 256:
        raise PolymathMCPError(
            "response_message_limit", "Polymath MCP response contains too many messages"
        )
    if not all(isinstance(value, dict) for value in values):
        raise PolymathMCPError(
            "response_shape_invalid", "Polymath MCP response must contain JSON objects"
        )
    return values


def _safe_rpc_error(
    status: int,
    raw: bytes,
    content_type: str,
) -> PolymathMCPError:
    rpc_code: int | None = None
    message = "Polymath MCP request failed"
    supported: list[str] = []
    try:
        values = _parse_rpc_payload(raw, content_type)
        error = values[-1].get("error") if values else None
        if isinstance(error, dict):
            if isinstance(error.get("code"), int):
                rpc_code = error["code"]
            if isinstance(error.get("message"), str) and error["message"].strip():
                message = error["message"].strip()[:300]
            data = error.get("data")
            if isinstance(data, dict):
                candidate = data.get("supported") or data.get("supportedVersions")
                if isinstance(candidate, list):
                    supported = [
                        item for item in candidate if isinstance(item, str)
                    ][:16]
    except (PolymathMCPError, json.JSONDecodeError):
        pass
    if status == 401:
        return PolymathMCPError(
            "credential_rejected",
            "Polymath MCP rejected the configured bearer credential",
            http_status=status,
            rpc_code=rpc_code,
        )
    if status == 403:
        return PolymathMCPError(
            "access_denied",
            "Polymath MCP denied this authenticated request",
            http_status=status,
            rpc_code=rpc_code,
        )
    return PolymathMCPError(
        "mcp_http_error",
        f"Polymath MCP HTTP {status}: {message}",
        http_status=status,
        rpc_code=rpc_code,
        supported_versions=supported,
    )


def _header_value(value: str) -> str:
    plain = (
        value
        and value == value.strip()
        and all(character == "\t" or 0x20 <= ord(character) <= 0x7E for character in value)
        and not _BASE64_SENTINEL.fullmatch(value)
    )
    if plain:
        return value
    encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
    return f"=?base64?{encoded}?="


def _schema_header_bindings(
    schema: dict[str, Any], arguments: dict[str, Any]
) -> dict[str, str]:
    bindings: dict[str, str] = {}
    seen: set[str] = set()

    def walk(node: Any, value: Any, path_is_properties: bool = True) -> None:
        if not isinstance(node, dict):
            return
        if "x-mcp-header" in node:
            name = node["x-mcp-header"]
            value_type = node.get("type")
            if (
                not path_is_properties
                or not isinstance(name, str)
                or not name
                or not _HEADER_NAME.fullmatch(name)
                or name.lower() in seen
                or value_type not in {"string", "integer", "boolean"}
            ):
                raise PolymathMCPError(
                    "tool_schema_invalid",
                    "Polymath tool has an invalid x-mcp-header annotation",
                )
            seen.add(name.lower())
            if value is None:
                return
            if value_type == "string" and not isinstance(value, str):
                raise PolymathMCPError(
                    "tool_argument_invalid", "Header-bound tool argument must be a string"
                )
            if value_type == "integer" and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or abs(value) > 9_007_199_254_740_991
            ):
                raise PolymathMCPError(
                    "tool_argument_invalid", "Header-bound tool integer is outside the safe range"
                )
            if value_type == "boolean" and not isinstance(value, bool):
                raise PolymathMCPError(
                    "tool_argument_invalid", "Header-bound tool argument must be boolean"
                )
            rendered = (
                str(value).lower() if isinstance(value, bool) else str(value)
            )
            bindings[f"Mcp-Param-{name}"] = _header_value(rendered)
        for key, child in node.items():
            if key == "properties" and isinstance(child, dict):
                current = value if isinstance(value, dict) else {}
                for property_name, property_schema in child.items():
                    walk(
                        property_schema,
                        current.get(property_name),
                        path_is_properties=path_is_properties,
                    )
            elif key not in {"properties", "x-mcp-header"} and isinstance(
                child, (dict, list)
            ):
                if isinstance(child, list):
                    for item in child:
                        walk(item, None, path_is_properties=False)
                else:
                    walk(child, None, path_is_properties=False)

    walk(schema, arguments)
    return bindings


class StreamableHTTPClient:
    """Small bounded MCP client supporting modern and live legacy Polymath eras."""

    def __init__(
        self,
        endpoint: str,
        token: str,
        *,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        opener: Callable[..., Any] = _NO_REDIRECT_OPENER,
    ) -> None:
        self.endpoint = _validated_endpoint(endpoint)
        if not isinstance(token, str) or not token.strip():
            raise PolymathMCPError(
                "credential_required", "A Polymath MCP bearer credential is required"
            )
        if not 1 <= timeout_seconds <= 120:
            raise PolymathMCPError(
                "timeout_invalid", "Polymath MCP timeout must be between 1 and 120 seconds"
            )
        self._token = token.strip()
        self.timeout_seconds = timeout_seconds
        self._opener = opener
        self._next_id = 1
        self.protocol_version: str | None = None
        self.session_id: str | None = None
        self.server_info: dict[str, Any] = {}
        self.tools: dict[str, dict[str, Any]] = {}

    def _post(
        self,
        message: dict[str, Any],
        *,
        protocol: str,
        expect_response: bool = True,
        tool_name: str | None = None,
        custom_headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        body = canonical_json_bytes(message)
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
            "MCP-Protocol-Version": protocol,
            "User-Agent": "CPCS-Polymath-MCP/1.0",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if protocol == MODERN_PROTOCOL:
            headers["Mcp-Method"] = str(message.get("method") or "")
            if tool_name is not None:
                headers["Mcp-Name"] = _header_value(tool_name)
            headers.update(custom_headers or {})
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                declared = response.headers.get("Content-Length")
                if declared and declared.isdigit() and int(declared) > MAX_RESPONSE_BYTES:
                    raise PolymathMCPError(
                        "response_too_large",
                        "Polymath MCP response exceeds the configured byte limit",
                    )
                session_id = response.headers.get("Mcp-Session-Id")
                if session_id:
                    if not all(0x21 <= ord(character) <= 0x7E for character in session_id):
                        raise PolymathMCPError(
                            "session_invalid", "Polymath MCP returned an invalid session ID"
                        )
                    self.session_id = session_id
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise PolymathMCPError(
                        "response_too_large",
                        "Polymath MCP response exceeds the configured byte limit",
                    )
                if not expect_response:
                    return None
                values = _parse_rpc_payload(
                    raw, response.headers.get("Content-Type", "application/json")
                )
        except urllib.error.HTTPError as exc:
            raw = exc.read(MAX_RESPONSE_BYTES + 1)
            raise _safe_rpc_error(
                exc.code, raw[:MAX_RESPONSE_BYTES], exc.headers.get("Content-Type", "")
            ) from exc
        except urllib.error.URLError as exc:
            raise PolymathMCPError(
                "endpoint_unreachable", "Polymath MCP endpoint is unreachable"
            ) from exc
        request_id = message.get("id")
        matching = [value for value in values if value.get("id") == request_id]
        if len(matching) != 1:
            raise PolymathMCPError(
                "response_id_invalid", "Polymath MCP response did not match the request ID"
            )
        response = matching[0]
        if isinstance(response.get("error"), dict):
            error = response["error"]
            raise PolymathMCPError(
                "mcp_rpc_error",
                str(error.get("message") or "Polymath MCP RPC failed")[:300],
                rpc_code=error.get("code") if isinstance(error.get("code"), int) else None,
            )
        if not isinstance(response.get("result"), dict):
            raise PolymathMCPError(
                "response_shape_invalid", "Polymath MCP result must be an object"
            )
        return response

    def _request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        protocol: str,
        tool_name: str | None = None,
        custom_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            },
            protocol=protocol,
            tool_name=tool_name,
            custom_headers=custom_headers,
        )
        assert response is not None
        return response

    @staticmethod
    def _modern_meta() -> dict[str, Any]:
        return {
            "io.modelcontextprotocol/protocolVersion": MODERN_PROTOCOL,
            "io.modelcontextprotocol/clientInfo": {
                "name": "cpcs-polymath",
                "version": ADAPTER_POLICY,
            },
            "io.modelcontextprotocol/clientCapabilities": {},
        }

    @staticmethod
    def _legacy_fallback_allowed(exc: PolymathMCPError) -> bool:
        if LEGACY_PROTOCOL in exc.supported_versions:
            return True
        return (
            exc.http_status in {400, 404, 405}
            and exc.rpc_code in {None, -32600, -32601, -32602}
        ) or (
            exc.http_status is None
            and exc.rpc_code in {-32600, -32601, -32602}
        )

    def connect(self) -> None:
        try:
            discovery = self._request(
                "server/discover",
                {"_meta": self._modern_meta()},
                protocol=MODERN_PROTOCOL,
            )["result"]
            supported = discovery.get("supportedVersions")
            if not isinstance(supported, list) or MODERN_PROTOCOL not in supported:
                raise PolymathMCPError(
                    "protocol_unsupported",
                    "Polymath MCP discovery did not admit the current protocol",
                    supported_versions=(
                        [item for item in supported if isinstance(item, str)][:16]
                        if isinstance(supported, list)
                        else []
                    ),
                )
            server = discovery.get("_meta", {}).get(
                "io.modelcontextprotocol/serverInfo", {}
            )
            self.server_info = server if isinstance(server, dict) else {}
            self.protocol_version = MODERN_PROTOCOL
            return
        except PolymathMCPError as exc:
            if not self._legacy_fallback_allowed(exc):
                raise
        initialized = self._request(
            "initialize",
            {
                "protocolVersion": LEGACY_PROTOCOL,
                "capabilities": {},
                "clientInfo": {
                    "name": "cpcs-polymath",
                    "version": ADAPTER_POLICY,
                },
            },
            protocol=LEGACY_PROTOCOL,
        )["result"]
        negotiated = initialized.get("protocolVersion")
        if negotiated != LEGACY_PROTOCOL:
            raise PolymathMCPError(
                "protocol_unsupported",
                "Polymath MCP did not negotiate the supported legacy protocol",
            )
        server = initialized.get("serverInfo", {})
        self.server_info = server if isinstance(server, dict) else {}
        self.protocol_version = LEGACY_PROTOCOL
        self._post(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            protocol=LEGACY_PROTOCOL,
            expect_response=False,
        )

    def list_tools(self) -> dict[str, dict[str, Any]]:
        if self.protocol_version is None:
            self.connect()
        protocol = str(self.protocol_version)
        params = {"_meta": self._modern_meta()} if protocol == MODERN_PROTOCOL else {}
        result = self._request("tools/list", params, protocol=protocol)["result"]
        rows = result.get("tools")
        if not isinstance(rows, list) or len(rows) > MAX_TOOL_COUNT:
            raise PolymathMCPError(
                "tool_catalog_invalid", "Polymath MCP tool catalog is invalid or too large"
            )
        tools: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("name"), str):
                raise PolymathMCPError(
                    "tool_catalog_invalid", "Polymath MCP tool entry is invalid"
                )
            name = row["name"]
            if name in tools:
                raise PolymathMCPError(
                    "tool_catalog_invalid", "Polymath MCP tool names must be unique"
                )
            tools[name] = copy.deepcopy(row)
        self.tools = tools
        return copy.deepcopy(tools)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.tools:
            self.list_tools()
        tool = self.tools.get(name)
        if tool is None:
            raise PolymathMCPError(
                "required_tool_missing", f"Polymath MCP does not expose required tool {name}"
            )
        protocol = str(self.protocol_version)
        params: dict[str, Any] = {"name": name, "arguments": copy.deepcopy(arguments)}
        headers: dict[str, str] = {}
        if protocol == MODERN_PROTOCOL:
            params["_meta"] = self._modern_meta()
            schema = tool.get("inputSchema", {})
            if not isinstance(schema, dict):
                raise PolymathMCPError(
                    "tool_schema_invalid", "Polymath MCP tool input schema is invalid"
                )
            headers = _schema_header_bindings(schema, arguments)
        result = self._request(
            "tools/call",
            params,
            protocol=protocol,
            tool_name=name,
            custom_headers=headers,
        )["result"]
        if result.get("isError") is True:
            raise PolymathMCPError(
                "tool_execution_failed", "Polymath MCP search tool reported an error"
            )
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return copy.deepcopy(structured)
        content = result.get("content")
        if not isinstance(content, list) or not content:
            raise PolymathMCPError(
                "tool_result_invalid", "Polymath MCP tool result contains no typed content"
            )
        first = content[0]
        if not isinstance(first, dict) or not isinstance(first.get("text"), str):
            raise PolymathMCPError(
                "tool_result_invalid", "Polymath MCP tool result text is missing"
            )
        try:
            value = json.loads(first["text"])
        except json.JSONDecodeError as exc:
            raise PolymathMCPError(
                "tool_result_invalid", "Polymath MCP tool result text is not JSON"
            ) from exc
        if not isinstance(value, dict):
            raise PolymathMCPError(
                "tool_result_invalid", "Polymath MCP tool result must be an object"
            )
        return value


def _required_identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise PolymathMCPError(
            "retrieval_result_invalid", f"Polymath result has an invalid {label}"
        )
    return value


def _chunk_value(chunk: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in chunk and chunk[key] is not None:
            return chunk[key]
    return None


def _retrieval_package(
    *,
    client: StreamableHTTPClient,
    result: dict[str, Any],
    query: str,
    corpus_ids: list[str],
    rights_basis: str,
    tool: str,
    retrieval_tier: str,
    top_k: int,
    rerank_enabled: bool,
    search_mode: str,
    retrieved_at: str,
    root: Path,
) -> dict[str, Any]:
    chunks = result.get("chunks")
    if not isinstance(chunks, list) or not chunks or len(chunks) > MAX_PASSAGES:
        raise PolymathMCPError(
            "retrieval_result_invalid",
            "Polymath search must return within the adapter passage limit",
        )
    upstream_count = len(chunks)
    chunks = chunks[:top_k]
    passages: list[dict[str, Any]] = []
    external: list[dict[str, Any]] = []
    seen: dict[tuple[str, str], str] = {}
    duplicates = 0
    total = 0
    actual_corpora: set[str] = set()
    for rank, chunk in enumerate(chunks, start=1):
        if not isinstance(chunk, dict):
            raise PolymathMCPError(
                "retrieval_result_invalid", "Polymath search chunk must be an object"
            )
        corpus_id = _required_identifier(
            _chunk_value(chunk, "corpus_id"), "corpus_id"
        )
        if corpus_ids and corpus_id not in corpus_ids:
            raise PolymathMCPError(
                "retrieval_scope_violation",
                "Polymath returned a chunk outside the requested corpus scope",
            )
        doc_id = _required_identifier(
            _chunk_value(chunk, "doc_id", "document_id"), "doc_id"
        )
        chunk_id = _required_identifier(
            _chunk_value(chunk, "chunk_id", "id"), "chunk_id"
        )
        text = _chunk_value(chunk, "text", "content", "page_content")
        if not isinstance(text, str) or not text.strip():
            raise PolymathMCPError(
                "retrieval_result_invalid", "Polymath search chunk text is empty"
            )
        raw = text.encode("utf-8")
        if len(raw) > MAX_PASSAGE_BYTES:
            raise PolymathMCPError(
                "passage_too_large", "Polymath passage exceeds the per-passage byte limit"
            )
        total += len(raw)
        if total > MAX_TOTAL_PASSAGE_BYTES:
            raise PolymathMCPError(
                "passages_too_large", "Polymath passages exceed the total byte limit"
            )
        source_id = "polymath://" + urllib.parse.quote(
            corpus_id, safe="-._~:"
        ) + "/document/" + urllib.parse.quote(doc_id, safe="-._~:")
        locator = "chunk=" + urllib.parse.quote(chunk_id, safe="-._~:")
        content_hash = _sha256_bytes(raw)
        address = (source_id, locator)
        if address in seen:
            if seen[address] != content_hash:
                raise PolymathMCPError(
                    "retrieval_locator_collision",
                    "Polymath returned different bytes for one source locator",
                )
            duplicates += 1
            total -= len(raw)
            continue
        seen[address] = content_hash
        title = _chunk_value(
            chunk, "filename", "title", "source_title", "doc_name"
        )
        if not isinstance(title, str) or not title.strip():
            title = doc_id
        title = title.strip()[:500]
        score = _chunk_value(chunk, "score", "similarity_score", "rerank_score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            score = None
        passage = {
            "source_id": source_id,
            "title": title,
            "locator": locator,
            "content_hash": content_hash,
            "text": text,
        }
        passages.append(passage)
        external.append(
            {
                "origin": "polymath_mcp",
                "source_id": source_id,
                "locator": locator,
                "content_hash": content_hash,
                "passage": text,
                "retrieval_query": query,
                "retrieved_at": retrieved_at,
                "score": float(score) if score is not None else None,
                "metadata": {
                    "title": title,
                    "corpus_id": corpus_id,
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    "parent_id": _chunk_value(chunk, "parent_id"),
                    "rank": rank,
                    "retrieval_tool": tool,
                },
                "trust_class": "untrusted_external_evidence",
            }
        )
        actual_corpora.add(corpus_id)
    if not passages:
        raise PolymathMCPError(
            "retrieval_empty", "Polymath search returned no unique non-empty passages"
        )
    returned_corpora = result.get("corpus_ids")
    if not isinstance(returned_corpora, list) or not all(
        isinstance(item, str) for item in returned_corpora
    ):
        returned_corpora = sorted(actual_corpora)
    envelope = {
        "schema": "cpcs.retrieved_passages/1.0",
        "retrieval": {
            "adapter": "polymath_mcp",
            "corpus_id": (
                next(iter(actual_corpora)) if len(actual_corpora) == 1 else None
            ),
            "query": query,
            "tool": tool,
            "parameters": {
                "requested_corpus_ids": corpus_ids,
                "returned_corpus_ids": sorted(set(returned_corpora)),
                "retrieval_tier": retrieval_tier,
                "effective_tier": result.get("effective_tier"),
                "top_k": top_k,
                "rerank_enabled": rerank_enabled,
                "search_mode": search_mode,
                "downgrade_reason": result.get("downgrade_reason"),
            },
            "retrieved_at": retrieved_at,
        },
        "rights_basis": rights_basis,
        "passages": passages,
    }
    validate_instance("retrieved_passages", envelope, root)
    package = {
        "schema": "cpcs.polymath_retrieval/1.0",
        "adapter_policy": ADAPTER_POLICY,
        "protocol": {
            "endpoint_hash": _endpoint_hash(client.endpoint),
            "protocol_version": client.protocol_version,
            "server_name": client.server_info.get("name"),
            "server_version": client.server_info.get("version"),
            "tool": tool,
            "tool_count": len(client.tools),
        },
        "retrieved_passages": envelope,
        "context_evidence": external,
        "diagnostics": {
            "requested_count": top_k,
            "upstream_count": upstream_count,
            "returned_count": len(passages),
            "truncated_count": max(0, upstream_count - top_k),
            "duplicate_count": duplicates,
            "response_bytes": total,
            "requested_corpus_ids": corpus_ids,
            "returned_corpus_ids": sorted(actual_corpora),
            "effective_tier": result.get("effective_tier"),
            "downgrade_reason": result.get("downgrade_reason"),
        },
    }
    validate_instance("polymath_retrieval", package, root)
    return package


def retrieve(
    query: str,
    *,
    corpus_ids: list[str] | None,
    rights_basis: str,
    tool: str = "polymath_search",
    retrieval_tier: str = "qdrant_mongo",
    top_k: int = 8,
    rerank_enabled: bool = True,
    search_mode: str = "local",
    endpoint: str | None = None,
    token: str | None = None,
    retrieved_at: str | None = None,
    client_factory: Callable[..., StreamableHTTPClient] = StreamableHTTPClient,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Retrieve one bounded evidence packet without writing repository authority."""
    if not isinstance(query, str) or not query.strip():
        raise PolymathMCPError("query_invalid", "Polymath retrieval query is missing")
    query = query.strip()
    if len(query.encode("utf-8")) > MAX_QUERY_BYTES:
        raise PolymathMCPError(
            "query_too_large", "Polymath retrieval query exceeds the byte limit"
        )
    if not isinstance(rights_basis, str) or not rights_basis.strip():
        raise PolymathMCPError(
            "rights_basis_required", "Polymath retrieval requires a rights basis"
        )
    if len(rights_basis.strip().encode("utf-8")) > MAX_RIGHTS_BASIS_BYTES:
        raise PolymathMCPError(
            "rights_basis_too_large", "Polymath rights basis exceeds the byte limit"
        )
    if tool not in SEARCH_TOOLS:
        raise PolymathMCPError(
            "tool_not_allowed", "Polymath retrieval tool is outside the read-only allowlist"
        )
    if retrieval_tier not in RETRIEVAL_TIERS or search_mode not in SEARCH_MODES:
        raise PolymathMCPError(
            "retrieval_parameters_invalid", "Polymath retrieval mode or tier is invalid"
        )
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= MAX_PASSAGES:
        raise PolymathMCPError(
            "retrieval_parameters_invalid", "Polymath top_k must be between 1 and 12"
        )
    if corpus_ids is not None and not isinstance(corpus_ids, list):
        raise PolymathMCPError(
            "corpus_scope_invalid", "Polymath corpus scope must be an array"
        )
    if not isinstance(rerank_enabled, bool):
        raise PolymathMCPError(
            "retrieval_parameters_invalid", "Polymath rerank flag must be boolean"
        )
    requested_corpora = list(corpus_ids or [])
    if len(requested_corpora) > 8 or len(requested_corpora) != len(set(requested_corpora)):
        raise PolymathMCPError(
            "corpus_scope_invalid", "Polymath corpus scope is duplicated or too broad"
        )
    for corpus_id in requested_corpora:
        _required_identifier(corpus_id, "requested corpus_id")
    resolved_endpoint, resolved_token, _ = _resolved_configuration(
        endpoint=endpoint,
        token=token,
    )
    if not resolved_token:
        raise PolymathMCPError(
            "credential_required",
            "Set POLYMATH_MCP_TOKEN or MCP_API_KEY before Polymath retrieval",
        )
    timestamp = retrieved_at or _utc_now()
    try:
        parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if parsed_timestamp.tzinfo is None:
            raise ValueError("timezone missing")
    except (AttributeError, ValueError) as exc:
        raise PolymathMCPError(
            "retrieved_at_invalid", "Polymath retrieval time must be ISO 8601"
        ) from exc
    client = client_factory(resolved_endpoint, resolved_token)
    client.connect()
    tools = client.list_tools()
    if tool not in tools:
        raise PolymathMCPError(
            "required_tool_missing", f"Polymath MCP does not expose required tool {tool}"
        )
    result = client.call_tool(
        tool,
        {
            "query": query,
            "corpus_ids": requested_corpora or None,
            "retrieval_tier": retrieval_tier,
            "final_top_k": top_k,
            "rerank_enabled": rerank_enabled,
            "search_mode": search_mode,
        },
    )
    return _retrieval_package(
        client=client,
        result=result,
        query=query,
        corpus_ids=requested_corpora,
        rights_basis=rights_basis.strip(),
        tool=tool,
        retrieval_tier=retrieval_tier,
        top_k=top_k,
        rerank_enabled=rerank_enabled,
        search_mode=search_mode,
        retrieved_at=timestamp,
        root=root,
    )


def doctor(
    *,
    endpoint: str | None = None,
    token: str | None = None,
    client_factory: Callable[..., StreamableHTTPClient] = StreamableHTTPClient,
) -> dict[str, Any]:
    """Probe MCP discovery without exposing credentials or claiming corpus access."""
    resolved_endpoint: str | None = None
    resolved_token: str | None = None
    source: str | None = None
    network_contacted = False
    try:
        resolved_endpoint, resolved_token, source = _resolved_configuration(
            endpoint=endpoint,
            token=token,
        )
        if not resolved_token:
            raise PolymathMCPError(
                "credential_required", "A Polymath MCP bearer credential is required"
            )
        client = client_factory(resolved_endpoint, resolved_token)
        network_contacted = True
        client.connect()
        tools = client.list_tools()
        available = sorted(set(SEARCH_TOOLS) & set(tools))
        missing = sorted(set(SEARCH_TOOLS) - set(tools))
        return {
            "schema": "cpcs.polymath_doctor/1.0",
            "adapter_policy": ADAPTER_POLICY,
            "status": "ready" if available and not missing else "tool_contract_incomplete",
            "endpoint_hash": _endpoint_hash(resolved_endpoint),
            "credential_configured": True,
            "credential_source": source,
            "protocol_version": client.protocol_version,
            "server": copy.deepcopy(client.server_info),
            "tool_count": len(tools),
            "available_search_tools": available,
            "missing_search_tools": missing,
            "network_contacted": True,
        }
    except PolymathMCPError as exc:
        return {
            "schema": "cpcs.polymath_doctor/1.0",
            "adapter_policy": ADAPTER_POLICY,
            "status": exc.code,
            "endpoint_hash": (
                _endpoint_hash(resolved_endpoint)
                if resolved_endpoint is not None
                else None
            ),
            "credential_configured": bool(resolved_token),
            "credential_source": source,
            "protocol_version": None,
            "server": {},
            "tool_count": 0,
            "available_search_tools": [],
            "missing_search_tools": list(SEARCH_TOOLS),
            "network_contacted": network_contacted,
        }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    retrieve_parser = sub.add_parser("retrieve")
    retrieve_parser.add_argument("query")
    retrieve_parser.add_argument("--corpus-id", action="append", default=[])
    retrieve_parser.add_argument("--rights-basis", required=True)
    retrieve_parser.add_argument("--tool", choices=SEARCH_TOOLS, default=SEARCH_TOOLS[0])
    retrieve_parser.add_argument("--retrieval-tier", choices=RETRIEVAL_TIERS, default="qdrant_mongo")
    retrieve_parser.add_argument("--top-k", type=int, default=8)
    retrieve_parser.add_argument("--search-mode", choices=SEARCH_MODES, default="local")
    retrieve_parser.add_argument("--no-rerank", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "doctor":
        result = doctor(endpoint=args.endpoint)
    else:
        result = retrieve(
            args.query,
            corpus_ids=args.corpus_id,
            rights_basis=args.rights_basis,
            tool=args.tool,
            retrieval_tier=args.retrieval_tier,
            top_k=args.top_k,
            rerank_enabled=not args.no_rerank,
            search_mode=args.search_mode,
            endpoint=args.endpoint,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
