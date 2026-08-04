"""Shared generation-adapter lifecycle contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


class AdapterError(RuntimeError):
    """Typed provider error used by the runner's retry and ambiguity policy."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        submission_uncertain: bool = False,
        code: str = "provider_error",
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.submission_uncertain = submission_uncertain
        self.code = code


@runtime_checkable
class GenerationAdapter(Protocol):
    """Provider-neutral lifecycle. Implementations contain transport only."""

    adapter_id: str
    submission_idempotent: bool
    supports_remote_cancel: bool

    def validate(self, build: dict[str, Any], job: dict[str, Any]) -> None: ...

    def prepare(self, build: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]: ...

    def submit(
        self, prepared: dict[str, Any], *, idempotency_key: str
    ) -> dict[str, Any]: ...

    def poll(self, operation: dict[str, Any]) -> dict[str, Any]: ...

    def retrieve(
        self,
        completed: dict[str, Any],
        destination: Path,
    ) -> list[dict[str, Any]]: ...

    def normalize(
        self,
        *,
        job: dict[str, Any],
        build: dict[str, Any],
        operation: dict[str, Any],
        completed: dict[str, Any],
        artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]: ...

    def cancel(self, operation: dict[str, Any]) -> dict[str, Any]: ...
