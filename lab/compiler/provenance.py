"""Canonical hashing and field-lineage helpers for universal scores."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def field_candidate(
    *,
    source: str,
    scope: str,
    priority: int,
    value: Any,
    source_refs: list[str],
) -> dict[str, Any]:
    return {
        "source": source,
        "scope": scope,
        "priority": priority,
        "value": value,
        "source_refs": sorted(set(source_refs)),
    }


def field_provenance(
    *,
    value: Any,
    winner: str | None,
    candidates: list[dict[str, Any]],
    operator: str,
    reason: str,
) -> dict[str, Any]:
    refs = sorted(
        {
            ref
            for candidate in candidates
            for ref in candidate.get("source_refs", [])
        }
    )
    return {
        "value": value,
        "winner": winner,
        "candidates": candidates,
        "merge_operator": operator,
        "reason": reason,
        "source_refs": refs,
    }
