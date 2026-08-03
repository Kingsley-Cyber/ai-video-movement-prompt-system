"""Runtime schema loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from lab.compiler.profiles import REPO_ROOT

SCHEMAS = {
    "render_job": "render_job.schema.json",
    "render_result": "render_result.schema.json",
}


def load_runtime_schema(name: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    if name not in SCHEMAS:
        raise ValueError(f"unknown runtime schema: {name}")
    return json.loads(
        (root / "lab/runtime/schemas" / SCHEMAS[name]).read_text(encoding="utf-8")
    )


def validate_runtime_instance(
    name: str, value: Any, root: Path = REPO_ROOT
) -> None:
    validator = Draft202012Validator(load_runtime_schema(name, root))
    errors = sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValueError(f"{SCHEMAS[name]}: {detail}")


def validate_runtime_configuration(root: Path = REPO_ROOT) -> dict[str, Any]:
    for name in SCHEMAS:
        Draft202012Validator.check_schema(load_runtime_schema(name, root))
    return {"schemas": len(SCHEMAS), "adapters": ["google_vertex_ai.veo/1.0"]}
