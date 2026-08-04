from __future__ import annotations

import json
import hashlib
import shutil
import copy
from pathlib import Path

from lab.second_brain.src.validate import REPO_ROOT, sha256_value


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


def controlled_lineage(
    tag: str, *, compliance_status: str = "pass"
) -> dict:
    digest = hashlib.sha256(tag.encode()).hexdigest()
    fixed = "sha256:" + "a" * 64
    return {
        "build_id": "build_" + digest[:32],
        "build_hash": "sha256:" + digest,
        "score_id": "score_" + digest[:32],
        "score_hash": "sha256:" + hashlib.sha256((tag + "score").encode()).hexdigest(),
        "request_hash": "sha256:" + hashlib.sha256((tag + "request").encode()).hexdigest(),
        "intent_hash": fixed,
        "context_hash": fixed,
        "profile_hashes": {"profile://universal/video/1.0": fixed},
        "block_hashes": {},
        "asset_hashes": {},
        "render_job_id": "render_job_" + digest[:24],
        "render_result_hash": "sha256:" + hashlib.sha256((tag + "render").encode()).hexdigest(),
        "artifact_id": "artifact_000",
        "artifact_sha256": "sha256:" + hashlib.sha256((tag + "artifact").encode()).hexdigest(),
        "provider_response_hash": "sha256:" + hashlib.sha256((tag + "provider").encode()).hexdigest(),
        "compliance_report_id": "compliance_" + digest[:32],
        "compliance_report_hash": "sha256:" + hashlib.sha256((tag + "compliance").encode()).hexdigest(),
        "compliance_status": compliance_status,
        "verification_evidence_hash": "sha256:" + hashlib.sha256((tag + "verification").encode()).hexdigest(),
    }


def finalize_evidence_run(run: dict) -> dict:
    value = copy.deepcopy(run)
    review = value["human_review"]
    review["review_hash"] = sha256_value(review)
    value["evidence_fingerprint"] = sha256_value(
        {
            "flight_hash": value["flight_hash"],
            "arm": value["arm"],
            "lineage": value["evidence_lineage"],
            "controls": value["controls"],
            "tested_delta": value["tested_delta"],
            "metrics": value["metrics"],
            "human_review": review,
        }
    )
    value["id"] = (
        "r_exp_"
        + value["evidence_fingerprint"].removeprefix("sha256:")[:20]
    )
    return value


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
    shutil.copytree(REPO_ROOT / "lab" / "runtime" / "schemas", root / "lab" / "runtime" / "schemas")
    shutil.copytree(
        REPO_ROOT / "lab" / "verification" / "schemas",
        root / "lab" / "verification" / "schemas",
    )
    write_rows(root / "lab" / "concepts.jsonl", concepts or [])
    for relative in (
        "curated/edges.jsonl",
        "curated/rules.jsonl",
        "curated/intents.jsonl",
        "curated/mappings.jsonl",
        "curated/claims.jsonl",
        "curated/equations.jsonl",
        "curated/methods.jsonl",
        "curated/mechanisms.jsonl",
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
