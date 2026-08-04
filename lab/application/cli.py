"""Stable local `cpcs` command over the shared application service."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from lab.second_brain.src.validate import REPO_ROOT

from .service import REQUEST_SCHEMA, invoke, list_operations
from .telemetry import TelemetrySink


def _read_object(path: Path | None) -> dict[str, Any]:
    if path is None:
        if sys.stdin.isatty():
            return {}
        raw = sys.stdin.read()
        if not raw.strip():
            return {}
    else:
        raw = path.read_text(encoding="utf-8")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("CLI input must be one JSON object")
    return value


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="cpcs", description="CPCS stable application command"
    )
    parser.add_argument("operation", nargs="?", help="operation name, with or without cpcs. prefix")
    parser.add_argument("--input", type=Path, help="JSON arguments file; defaults to stdin or {}")
    parser.add_argument("--authorization", type=Path, help="explicit authorization JSON")
    parser.add_argument("--request-id")
    parser.add_argument("--role", choices=("chat", "operator", "curator"), default="chat")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--telemetry", type=Path, help="append content-free events under work/")
    parser.add_argument("--list", action="store_true", help="list operations available to the role")
    args = parser.parse_args(argv)
    if args.list:
        print(json.dumps({"operations": list_operations(args.role)}, indent=2, sort_keys=True))
        return
    if not args.operation:
        parser.error("operation is required unless --list is used")
    operation = args.operation if args.operation.startswith("cpcs.") else "cpcs." + args.operation
    request: dict[str, Any] = {
        "schema": REQUEST_SCHEMA,
        "operation": operation,
        "arguments": _read_object(args.input),
    }
    if args.request_id:
        request["request_id"] = args.request_id
    if args.authorization:
        request["authorization"] = json.loads(
            args.authorization.read_text(encoding="utf-8")
        )
    root = args.root.resolve()
    telemetry = TelemetrySink(args.telemetry, root=root) if args.telemetry else None
    response = invoke(request, role=args.role, root=root, telemetry=telemetry)
    print(json.dumps(response, indent=2, sort_keys=True, ensure_ascii=False))
    if response["status"] != "success":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
