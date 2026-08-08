"""Minimal MCP stdio adapter over the CPCS application service."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from lab.second_brain.src.validate import REPO_ROOT

from .service import APPLICATION_POLICY, REQUEST_SCHEMA, invoke, list_operations
from .telemetry import TelemetrySink

MCP_PROTOCOL_VERSION = "2025-03-26"


def _error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def _tool_rows(role: str) -> list[dict[str, Any]]:
    rows = []
    for operation in list_operations(role):
        if not operation["mcp_exposed"]:
            continue
        input_schema = copy.deepcopy(operation["input_schema"])
        if operation["authorization_required"]:
            input_schema["properties"]["_cpcs_authorization"] = {"type": "object"}
        rows.append(
            {
                "name": operation["name"],
                "title": operation["name"],
                "description": operation["description"],
                "inputSchema": input_schema,
                "annotations": {
                    "readOnlyHint": operation["mutation_scope"] is None,
                    "destructiveHint": operation["mutation_scope"] == "curated",
                    "idempotentHint": operation["name"] in {
                        "cpcs.research.source.register",
                        "cpcs.research.extraction.submit",
                        "cpcs.research.distillation.run",
                        "cpcs.record.render",
                        "cpcs.record.testimonial.capture",
                        "cpcs.record.testimonial.review",
                        "cpcs.reflect.rebuild",
                        "cpcs.production.prepare",
                        "cpcs.build.materialize",
                        "cpcs.render.create",
                        "cpcs.render.run",
                        "cpcs.verify.run",
                        "cpcs.measure.pose.run",
                        "cpcs.record.measurement",
                        "cpcs.analyze.atomic.prepare",
                        "cpcs.analyze.cascade",
                        "cpcs.experiment.prepare",
                        "cpcs.experiment.seal",
                        "cpcs.graph.projection.sync",
                        "cpcs.workflow.render.prepare",
                        "cpcs.workflow.render.status",
                        "cpcs.workflow.render.advance",
                        "cpcs.workflow.render.review",
                        "cpcs.workflow.render.cancel",
                        "cpcs.video.compare.prepare",
                        "cpcs.video.compare.status",
                        "cpcs.video.compare.advance",
                        "cpcs.video.compare.inspect",
                        "cpcs.video.compare.cancel",
                        "cpcs.research.delta.patch.prepare",
                        "cpcs.research.delta.patch.execute",
                        "cpcs.research.delta.patch.discard",
                    },
                    "openWorldHint": "external" in (operation["mutation_scope"] or ""),
                },
            }
        )
    return rows


def handle_message(
    message: dict[str, Any],
    *,
    role: str = "chat",
    root: Path = REPO_ROOT,
    telemetry: TelemetrySink | None = None,
) -> dict[str, Any] | None:
    message_id = message.get("id")
    if message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return _error(message_id, -32600, "invalid JSON-RPC request")
    method = message["method"]
    if method.startswith("notifications/"):
        return None
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "cpcs", "version": APPLICATION_POLICY},
                "instructions": (
                    "Start an unfamiliar repository task with cpcs.agent.brief. "
                    "CPCS tools use repository authority labels and role-gated writes."
                ),
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": message_id, "result": {"tools": _tool_rows(role)}}
    if method != "tools/call":
        return _error(message_id, -32601, f"method not found: {method}")
    params = message.get("params")
    if not isinstance(params, dict) or not isinstance(params.get("name"), str):
        return _error(message_id, -32602, "tools/call requires a tool name")
    available = {row["name"] for row in _tool_rows(role)}
    if params["name"] not in available:
        return _error(message_id, -32601, f"tool not found: {params['name']}")
    arguments = params.get("arguments", {})
    if not isinstance(arguments, dict):
        return _error(message_id, -32602, "tool arguments must be an object")
    arguments = copy.deepcopy(arguments)
    authorization = arguments.pop("_cpcs_authorization", None)
    request = {
        "schema": REQUEST_SCHEMA,
        "operation": params["name"],
        "arguments": arguments,
    }
    if authorization is not None:
        request["authorization"] = authorization
    response = invoke(request, role=role, root=root, telemetry=telemetry)
    text = json.dumps(response, sort_keys=True, ensure_ascii=False)
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "result": {
            "content": [{"type": "text", "text": text}],
            "structuredContent": response,
            "isError": response["status"] == "error",
        },
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("chat", "operator", "curator"), default="chat")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--telemetry", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    telemetry = TelemetrySink(args.telemetry, root=root) if args.telemetry else None
    for line in sys.stdin:
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError("message must be an object")
            response = handle_message(
                message, role=args.role, root=root, telemetry=telemetry
            )
        except (ValueError, json.JSONDecodeError) as exc:
            response = _error(None, -32700, str(exc))
        if response is not None:
            print(json.dumps(response, sort_keys=True, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
