"""Thin guided and advanced clients over the same score operation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from lab.second_brain.src.validate import REPO_ROOT

from .service import REQUEST_SCHEMA, invoke


def guided_score(
    text: str,
    *,
    user_constraints: Iterable[str] = (),
    token_budget: int = 12_000,
    overlays: Iterable[dict[str, Any]] = (),
    conflict_resolutions: dict[str, Any] | None = None,
    assets: Iterable[dict[str, Any]] = (),
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    return invoke(
        {
            "schema": REQUEST_SCHEMA,
            "operation": "cpcs.score.build",
            "arguments": {
                "text": text,
                "user_constraints": list(user_constraints),
                "token_budget": token_budget,
                "overlays": list(overlays),
                "conflict_resolutions": conflict_resolutions or {},
                "assets": list(assets),
            },
        },
        role="chat",
        root=root,
    )


def advanced_score(
    intent_context: dict[str, Any],
    *,
    overlays: Iterable[dict[str, Any]] = (),
    conflict_resolutions: dict[str, Any] | None = None,
    assets: Iterable[dict[str, Any]] = (),
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    return invoke(
        {
            "schema": REQUEST_SCHEMA,
            "operation": "cpcs.score.build",
            "arguments": {
                "intent_context": intent_context,
                "overlays": list(overlays),
                "conflict_resolutions": conflict_resolutions or {},
                "assets": list(assets),
            },
        },
        role="chat",
        root=root,
    )
