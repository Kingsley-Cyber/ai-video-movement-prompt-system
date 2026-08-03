from __future__ import annotations

import json
import shutil
from pathlib import Path

from lab.second_brain.src.validate import REPO_ROOT


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    )


def concept(concept_id: str, name: str, layer: str = "test", status: str = "proven") -> dict:
    return {
        "id": concept_id,
        "kind": "concept",
        "name": name,
        "what": f"{name} operational definition",
        "use_when": f"use {name}",
        "nl_triggers": [name, f"{name} control", f"{name} technique"],
        "status": status,
        "evidence": [],
        "source": ["fixture://concepts"],
        "layer": layer,
    }


def make_root(base: Path, concepts: list[dict] | None = None) -> Path:
    root = base / "repo"
    sb = root / "lab" / "second_brain"
    (root / "lab").mkdir(parents=True)
    shutil.copytree(REPO_ROOT / "lab" / "second_brain" / "schemas", sb / "schemas")
    shutil.copy2(
        REPO_ROOT / "lab" / "second_brain" / "analysis_profiles.yaml",
        sb / "analysis_profiles.yaml",
    )
    shutil.copytree(REPO_ROOT / "lab" / "profiles", root / "lab" / "profiles")
    shutil.copytree(REPO_ROOT / "lab" / "compiler", root / "lab" / "compiler")
    write_rows(root / "lab" / "concepts.jsonl", concepts or [])
    for relative in (
        "curated/edges.jsonl",
        "curated/rules.jsonl",
        "curated/intents.jsonl",
        "curated/mappings.jsonl",
        "immutable/flights.jsonl",
        "immutable/runs.jsonl",
        "immutable/pegasus_observations.jsonl",
        "immutable/measurement_observations.jsonl",
        "staging/proposals.jsonl",
        "staging/rejected.jsonl",
        "staging/corpus_manifest.jsonl",
        "staging/distillation_runs.jsonl",
    ):
        write_rows(sb / relative, [])
    shutil.copytree(REPO_ROOT / "lab" / "second_brain" / "templates", sb / "templates")
    return root
