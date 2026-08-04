"""Application-facade schema loading and validation."""

from __future__ import annotations

import json
import argparse
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from lab.second_brain.src.validate import REPO_ROOT

SCHEMAS = {
    "application_request": "application_request.schema.json",
    "application_response": "application_response.schema.json",
}


def load_application_schema(name: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    if name not in SCHEMAS:
        raise ValueError(f"unknown application schema: {name}")
    return json.loads(
        (root / "lab" / "application" / "schemas" / SCHEMAS[name]).read_text(
            encoding="utf-8"
        )
    )


def validate_application_instance(
    name: str, value: Any, root: Path = REPO_ROOT
) -> None:
    validator = Draft202012Validator(load_application_schema(name, root))
    errors = sorted(
        validator.iter_errors(value), key=lambda item: list(item.absolute_path)
    )
    if errors:
        detail = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValueError(f"{SCHEMAS[name]}: {detail}")


def validate_application_configuration(root: Path = REPO_ROOT) -> dict[str, Any]:
    for name in SCHEMAS:
        Draft202012Validator.check_schema(load_application_schema(name, root))
    return {"schemas": len(SCHEMAS)}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    print(json.dumps(validate_application_configuration(), sort_keys=True))


if __name__ == "__main__":
    main()
