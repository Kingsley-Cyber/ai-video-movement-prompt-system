"""Non-overridable lock handling for canonical score resolution."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any


def _equal(left: Any, right: Any) -> bool:
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(
        right, sort_keys=True, separators=(",", ":")
    )


@dataclass
class LockRegistry:
    values: dict[str, Any] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)

    def lock(self, path: str, value: Any, source: str) -> None:
        if path in self.values and not _equal(self.values[path], value):
            raise ValueError(
                f"lock {path} from {source} conflicts with lock from {self.sources[path]}"
            )
        self.values[path] = copy.deepcopy(value)
        self.sources[path] = source

    def conflict(self, path: str, value: Any, source: str) -> dict[str, Any] | None:
        if path not in self.values or _equal(self.values[path], value):
            return None
        return {
            "code": "hard_lock_conflict",
            "id": f"lock:{path}",
            "path": path,
            "message": (
                f"{source} cannot replace the locked value from {self.sources[path]}."
            ),
            "options": [copy.deepcopy(self.values[path]), copy.deepcopy(value)],
        }

    def paths(self) -> list[str]:
        return sorted(self.values)
