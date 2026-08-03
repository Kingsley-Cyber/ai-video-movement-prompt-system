"""Schema, tier-boundary, hash-chain, and control-plane validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[3]
SECOND_BRAIN = REPO_ROOT / "lab" / "second_brain"
SCHEMAS = SECOND_BRAIN / "schemas"
CURATED = SECOND_BRAIN / "curated"
IMMUTABLE = SECOND_BRAIN / "immutable"
STAGING = SECOND_BRAIN / "staging"
DERIVED = SECOND_BRAIN / "derived"

SCHEMA_FILES = {
    "concept": "concept.schema.json",
    "edge": "edge.schema.json",
    "rule": "rule.schema.json",
    "intent": "intent.schema.json",
    "mapping": "mapping.schema.json",
    "proposal": "proposal.schema.json",
    "distillation_batch": "distillation_batch.schema.json",
    "distillation_run": "distillation_run.schema.json",
    "flight": "flight.schema.json",
    "run": "run.schema.json",
    "experiment_receipt": "experiment_receipt.schema.json",
    "pegasus_observation": "pegasus_observation.schema.json",
    "measurement_observation": "measurement_observation.schema.json",
    "learned_weight": "learned_weight.schema.json",
    "reasoning_query": "reasoning_query.schema.json",
    "context_bundle": "context_bundle.schema.json",
    "normalized_intent": "normalized_intent.schema.json",
    "twelvelabs_analysis_profiles": "twelvelabs_analysis_profiles.schema.json",
    "twelvelabs_asset_job": "twelvelabs_asset_job.schema.json",
    "twelvelabs_analyze_job": "twelvelabs_analyze_job.schema.json",
    "twelvelabs_segment_job": "twelvelabs_segment_job.schema.json",
    "twelvelabs_batch_job": "twelvelabs_batch_job.schema.json",
    "twelvelabs_search_job": "twelvelabs_search_job.schema.json",
    "twelvelabs_jockey_job": "twelvelabs_jockey_job.schema.json",
    "twelvelabs_marengo_job": "twelvelabs_marengo_job.schema.json",
    "twelvelabs_semantic_response": "twelvelabs_semantic_response.schema.json",
    "twelvelabs_corpus_response": "twelvelabs_corpus_response.schema.json",
    "normalized_video_observation": "normalized_video_observation.schema.json",
    "video_observation_graph": "video_observation_graph.schema.json",
    "video_analysis_cascade": "video_analysis_cascade.schema.json",
    "source_extraction_bundle": "source_extraction_bundle.schema.json",
    "semantic_extraction_response": "semantic_extraction_response.schema.json",
    "retrieved_passages": "retrieved_passages.schema.json",
    "derived_indexes": "derived_indexes.schema.json",
}

STORE_SCHEMAS = {
    REPO_ROOT / "lab" / "concepts.jsonl": "concept",
    CURATED / "edges.jsonl": "edge",
    CURATED / "rules.jsonl": "rule",
    CURATED / "intents.jsonl": "intent",
    CURATED / "mappings.jsonl": "mapping",
    STAGING / "proposals.jsonl": "proposal",
    STAGING / "distillation_runs.jsonl": "distillation_run",
    IMMUTABLE / "flights.jsonl": "flight",
    IMMUTABLE / "runs.jsonl": "run",
    IMMUTABLE / "pegasus_observations.jsonl": "pegasus_observation",
    IMMUTABLE / "measurement_observations.jsonl": "measurement_observation",
}

WRITE_ROOTS = {
    "curate": (REPO_ROOT / "lab" / "concepts.jsonl", CURATED),
    "record": (IMMUTABLE,),
    "reflect": (DERIVED,),
    "manual": (STAGING / "proposals.jsonl",),
    "polymath": (STAGING / "corpus_manifest.jsonl",),
    "distill": (
        STAGING / "proposals.jsonl",
        STAGING / "distillation_runs.jsonl",
    ),
    "pegasus": (IMMUTABLE / "pegasus_observations.jsonl",),
    "query": (REPO_ROOT / "work",),
    "twelvelabs": (REPO_ROOT / "work",),
    "source_extract": (REPO_ROOT / "work",),
}

MANIFEST_STATUSES = {
    "pending",
    "processing",
    "proposed",
    "reviewed",
    "complete",
    "failed",
}
EXTERNAL_PROPOSAL_ORIGINS = frozenset(
    {"local_source", "polymath_mcp", "pegasus", "rag_pipeline"}
)


class ValidationFailure(ValueError):
    """Raised when persistent control-plane data is invalid."""


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def sha256_value(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def content_hash(record: dict[str, Any], excluded: Iterable[str] = ("record_hash",)) -> str:
    clean = {key: value for key, value in record.items() if key not in set(excluded)}
    return sha256_value(clean)


def load_schema(name: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    path = root / "lab" / "second_brain" / "schemas" / SCHEMA_FILES[name]
    return json.loads(path.read_text())


def validate_instance(name: str, value: Any, root: Path = REPO_ROOT) -> None:
    validator = Draft202012Validator(load_schema(name, root), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.absolute_path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}" for error in errors
        )
        raise ValidationFailure(f"{name}: {detail}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValidationFailure(f"missing JSONL store: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValidationFailure(f"{path}:{line_number}: {error.msg}") from error
        if not isinstance(value, dict):
            raise ValidationFailure(f"{path}:{line_number}: record must be an object")
        rows.append(value)
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = b"".join(canonical_json_bytes(row) for row in rows)
    path.write_bytes(body)


def assert_write_target(actor: str, path: Path, root: Path = REPO_ROOT) -> None:
    resolved = path.resolve()
    allowed = []
    for candidate in WRITE_ROOTS[actor]:
        mapped = root / candidate.relative_to(REPO_ROOT) if root != REPO_ROOT else candidate
        allowed.append(mapped.resolve())
    for target in allowed:
        if resolved == target or (not target.suffix and target in resolved.parents):
            return
    raise PermissionError(f"{actor} cannot write {resolved}")


def validate_schemas(root: Path = REPO_ROOT) -> dict[str, int]:
    checked = 0
    for name in sorted(SCHEMA_FILES):
        schema = load_schema(name, root)
        Draft202012Validator.check_schema(schema)
        checked += 1
    return {"schemas": checked}


def validate_manifest_row(row: dict[str, Any]) -> None:
    required = {
        "corpus_item_id",
        "source_ref",
        "title",
        "sha256_or_source_version",
        "domain",
        "status",
        "sections_processed",
        "proposal_ids",
        "promoted_concept_ids",
        "error",
    }
    optional = {"duplicate_of", "retrieval_capabilities"}
    missing = required - set(row)
    extra = set(row) - required - optional
    if missing or extra:
        raise ValidationFailure(
            f"corpus manifest fields missing={sorted(missing)} extra={sorted(extra)}"
        )
    if row["status"] not in MANIFEST_STATUSES:
        raise ValidationFailure(f"invalid corpus manifest status {row['status']}")
    for key in (
        "corpus_item_id",
        "source_ref",
        "title",
        "sha256_or_source_version",
        "domain",
    ):
        if not isinstance(row[key], str) or not row[key]:
            raise ValidationFailure(f"corpus manifest {key} must be a non-empty string")
    for key in ("sections_processed", "proposal_ids", "promoted_concept_ids"):
        if not isinstance(row[key], list) or any(
            not isinstance(item, str) or not item for item in row[key]
        ):
            raise ValidationFailure(f"corpus manifest {key} must be a string array")
    if row["error"] is not None and not isinstance(row["error"], str):
        raise ValidationFailure("corpus manifest error must be null or a string")
    if row.get("duplicate_of") is not None and (
        not isinstance(row["duplicate_of"], str) or not row["duplicate_of"]
    ):
        raise ValidationFailure("corpus manifest duplicate_of must be null or a string")
    capabilities = row.get("retrieval_capabilities")
    if capabilities is not None and not isinstance(capabilities, dict):
        raise ValidationFailure("retrieval_capabilities must be an object")


def validate_curated(root: Path = REPO_ROOT) -> dict[str, int]:
    concept_path = root / "lab" / "concepts.jsonl"
    sb = root / "lab" / "second_brain"
    paths = {
        concept_path: "concept",
        sb / "curated" / "edges.jsonl": "edge",
        sb / "curated" / "rules.jsonl": "rule",
        sb / "curated" / "intents.jsonl": "intent",
        sb / "curated" / "mappings.jsonl": "mapping",
    }
    rows_by_path: dict[Path, list[dict[str, Any]]] = {}
    for path, schema_name in paths.items():
        rows = read_jsonl(path)
        rows_by_path[path] = rows
        for row in rows:
            validate_instance(schema_name, row, root)
    concepts = rows_by_path[concept_path]
    concept_ids = [row["id"] for row in concepts]
    if len(concept_ids) != len(set(concept_ids)):
        raise ValidationFailure("duplicate curated concept ID")
    if any("pairs_with" in row or "conflicts" in row for row in concepts):
        raise ValidationFailure("concept cards still contain duplicate relationship authority")
    edges = rows_by_path[sb / "curated" / "edges.jsonl"]
    valid_ids = set(concept_ids)
    bad_refs = sorted(
        f"{edge['id']}:{endpoint}"
        for edge in edges
        for endpoint in (edge["u"], edge["v"])
        if endpoint not in valid_ids
    )
    if bad_refs:
        raise ValidationFailure(f"authored edge references missing concept: {', '.join(bad_refs)}")
    mappings = rows_by_path[sb / "curated" / "mappings.jsonl"]
    bad_mappings = [row["id"] for row in mappings if row["concept_id"] not in valid_ids]
    if bad_mappings:
        raise ValidationFailure(f"mapping references missing concept: {', '.join(bad_mappings)}")
    all_curated_ids = [
        row["id"]
        for rows in rows_by_path.values()
        for row in rows
    ]
    if len(all_curated_ids) != len(set(all_curated_ids)):
        raise ValidationFailure("durable IDs must be unique across curated stores")
    from .graph import validate_edge_distribution
    from .temporal import validate_temporal_collections

    try:
        validate_temporal_collections(
            {
                schema_name: rows_by_path[path]
                for path, schema_name in paths.items()
            }
        )
        validate_edge_distribution(edges)
    except ValueError as exc:
        raise ValidationFailure(str(exc)) from exc
    from .rules import EVALUATORS, referenced_concept_ids

    rules = rows_by_path[sb / "curated" / "rules.jsonl"]
    unknown_evaluators = sorted(
        row["id"] for row in rules if row["evaluator"] not in EVALUATORS
    )
    if unknown_evaluators:
        raise ValidationFailure(
            "rules use unknown named evaluators: " + ", ".join(unknown_evaluators)
        )
    bad_rule_refs = sorted(
        f"{row['id']}:{concept_id}"
        for row in rules
        for concept_id in referenced_concept_ids(row)
        if concept_id not in valid_ids
    )
    if bad_rule_refs:
        raise ValidationFailure(
            "rules reference missing concepts: " + ", ".join(bad_rule_refs)
        )
    return {
        "concepts": len(concepts),
        "edges": len(edges),
        "rules": len(rows_by_path[sb / "curated" / "rules.jsonl"]),
        "intents": len(rows_by_path[sb / "curated" / "intents.jsonl"]),
        "mappings": len(mappings),
    }


def _validate_hash_chain(rows: list[dict[str, Any]], path: Path) -> None:
    prior: str | None = None
    seen: set[str] = set()
    for row in rows:
        record_id = row["id"]
        if record_id in seen:
            raise ValidationFailure(f"{path}: duplicate immutable ID {record_id}")
        seen.add(record_id)
        if row.get("prior_record_hash") != prior:
            raise ValidationFailure(f"{path}: {record_id} has invalid prior_record_hash")
        expected = content_hash(row)
        if row.get("record_hash") != expected:
            raise ValidationFailure(f"{path}: {record_id} has invalid record_hash")
        prior = row["record_hash"]


def validate_immutable(root: Path = REPO_ROOT) -> dict[str, int]:
    base = root / "lab" / "second_brain" / "immutable"
    specs = {
        base / "flights.jsonl": "flight",
        base / "runs.jsonl": "run",
        base / "pegasus_observations.jsonl": "pegasus_observation",
        base / "measurement_observations.jsonl": "measurement_observation",
    }
    counts: dict[str, int] = {}
    flights: dict[str, dict[str, Any]] = {}
    rows_by_schema: dict[str, list[dict[str, Any]]] = {}
    for path, schema_name in specs.items():
        rows = read_jsonl(path)
        rows_by_schema[schema_name] = rows
        for row in rows:
            validate_instance(schema_name, row, root)
        if schema_name == "flight":
            for row in rows:
                expected = content_hash(row, ("flight_hash",))
                if row["flight_hash"] != expected:
                    raise ValidationFailure(f"{path}: {row['id']} has invalid flight_hash")
                flights[row["id"]] = row
        else:
            _validate_hash_chain(rows, path)
        counts[schema_name] = len(rows)
    all_ids = [
        row["id"]
        for rows in rows_by_schema.values()
        for row in rows
    ]
    if len(all_ids) != len(set(all_ids)):
        raise ValidationFailure("immutable IDs must be unique across stores")
    concepts = {
        row["id"]: row for row in read_jsonl(root / "lab" / "concepts.jsonl")
    }
    intents = {
        row["id"]
        for row in read_jsonl(
            root / "lab" / "second_brain" / "curated" / "intents.jsonl"
        )
    }
    for flight in flights.values():
        if flight["intent_id"] is not None and flight["intent_id"] not in intents:
            raise ValidationFailure(
                f"flight {flight['id']} references missing intent {flight['intent_id']}"
            )
        missing = sorted(set(flight["concept_ids"]) - set(concepts))
        if missing:
            raise ValidationFailure(
                f"flight {flight['id']} references missing concepts: {', '.join(missing)}"
            )
        if set(flight["concept_content_hashes"]) != set(flight["concept_ids"]):
            raise ValidationFailure(
                f"flight {flight['id']} concept_content_hashes do not cover its concept IDs"
            )
        arm_ids = [arm["id"] for arm in flight["arms"]]
        if len(arm_ids) != len(set(arm_ids)):
            raise ValidationFailure(f"flight {flight['id']} has duplicate arm IDs")
        if flight.get("legacy") is None:
            design = flight["design"]
            outcome_concepts = set(design["outcome_concept_ids"])
            if not outcome_concepts <= set(flight["concept_ids"]):
                raise ValidationFailure(
                    f"flight {flight['id']} outcome concepts are not sealed"
                )
            deltas = [arm.get("tested_delta") for arm in flight["arms"]]
            if design["classification"] == "isolated_comparison":
                if len(deltas) < 2 or any(not isinstance(delta, dict) for delta in deltas):
                    raise ValidationFailure(
                        f"flight {flight['id']} isolated design lacks two declared deltas"
                    )
                delta_concepts = {delta["concept_id"] for delta in deltas}
                delta_controls = {delta["control_id"] for delta in deltas}
                delta_values = {
                    json.dumps(delta["value"], sort_keys=True, separators=(",", ":"))
                    for delta in deltas
                }
                if (
                    len(delta_concepts) != 1
                    or len(delta_controls) != 1
                    or len(delta_values) < 2
                    or not delta_concepts <= set(flight["concept_ids"])
                    or not outcome_concepts
                    or bool(outcome_concepts & delta_concepts)
                ):
                    raise ValidationFailure(
                        f"flight {flight['id']} does not isolate one sealed concept/control"
                    )
            elif any(delta is not None for delta in deltas):
                raise ValidationFailure(
                    f"flight {flight['id']} bundled design declares an isolated delta"
                )
    for run in rows_by_schema["run"]:
        flight = flights.get(run["flight_id"])
        if not flight or run["flight_hash"] != flight["flight_hash"]:
            raise ValidationFailure(f"run {run['id']} has missing or mismatched sealed flight")
        locked = {
            "intent_id": flight["intent_id"],
            "intent_class": flight["intent_class"],
            "concept_ids": flight["concept_ids"],
            "concept_content_hashes": flight["concept_content_hashes"],
            "provider": flight["provider"],
            "model_version": flight["model_version"],
            "seed": flight["seed"],
        }
        mismatches = [
            key for key, expected in locked.items() if run.get(key) != expected
        ]
        compiler_version = flight["compiler_settings"].get("version")
        if compiler_version is not None and run["compiler_version"] != compiler_version:
            mismatches.append("compiler_version")
        arms = {arm["id"]: arm for arm in flight["arms"]}
        arm = arms.get(run["arm"])
        if arm is None:
            mismatches.append("arm")
        elif run["paradigm"] != arm["paradigm"]:
            mismatches.append("paradigm")
        if mismatches:
            raise ValidationFailure(
                f"run {run['id']} differs from sealed flight fields: "
                + ", ".join(sorted(set(mismatches)))
            )
        if run.get("legacy") is None and (
            run["seed"] is None
            or run["output_artifact_hash"] is None
            or "legacy-unrecorded"
            in {
                run["provider"],
                run["model_version"],
                run["compiler_version"],
            }
        ):
            raise ValidationFailure(
                f"nonlegacy run {run['id']} must record seed, output hash, and exact versions"
            )
        if run.get("legacy") is None:
            design = flight["design"]
            arm = arms[run["arm"]]
            expected_eligibility = (
                "candidate"
                if design["classification"] == "isolated_comparison"
                else "ineligible_bundled"
            )
            if run["evidence_design"] != {
                "classification": design["classification"],
                "causal_eligibility": expected_eligibility,
                "outcome_concept_ids": sorted(design["outcome_concept_ids"]),
                "policy_version": "cpcs-controlled-evidence/1.0",
            }:
                raise ValidationFailure(
                    f"run {run['id']} evidence design differs from sealed flight"
                )
            if run["tested_delta"] != arm.get("tested_delta"):
                raise ValidationFailure(
                    f"run {run['id']} tested delta differs from sealed arm"
                )
            delta = run["tested_delta"]
            if design["classification"] == "isolated_comparison" and (
                delta["control_id"] not in run["controls"]
                or run["controls"][delta["control_id"]] != delta["value"]
            ):
                raise ValidationFailure(
                    f"run {run['id']} controls do not realize its tested delta"
                )
            lineage = run["evidence_lineage"]
            if run["output_artifact_hash"] != lineage["artifact_sha256"]:
                raise ValidationFailure(
                    f"run {run['id']} artifact hash differs from evidence lineage"
                )
            review = run["human_review"]
            expected_review_hash = sha256_value(
                {key: value for key, value in review.items() if key != "review_hash"}
            )
            if review["review_hash"] != expected_review_hash or run["verdict"] != review["verdict"]:
                raise ValidationFailure(f"run {run['id']} human review lineage is invalid")
            expected_fingerprint = sha256_value(
                {
                    "flight_hash": run["flight_hash"],
                    "arm": run["arm"],
                    "lineage": lineage,
                    "controls": run["controls"],
                    "tested_delta": run["tested_delta"],
                    "metrics": run["metrics"],
                    "human_review": review,
                }
            )
            if (
                run["evidence_fingerprint"] != expected_fingerprint
                or run["id"]
                != "r_exp_" + expected_fingerprint.removeprefix("sha256:")[:20]
            ):
                raise ValidationFailure(f"run {run['id']} evidence fingerprint is invalid")
    for schema_name in (
        "pegasus_observation",
        "measurement_observation",
    ):
        for row in rows_by_schema[schema_name]:
            references = set(row.get("concept_ids", [])) | set(
                row.get("candidate_concepts", [])
            )
            missing = sorted(references - set(concepts))
            if missing:
                raise ValidationFailure(
                    f"{row['id']} references missing concepts: {', '.join(missing)}"
                )
    return counts


def validate_staging(root: Path = REPO_ROOT) -> dict[str, int]:
    staging = root / "lab" / "second_brain" / "staging"
    proposals = read_jsonl(staging / "proposals.jsonl")
    rejected = read_jsonl(staging / "rejected.jsonl")
    distillation_runs = read_jsonl(staging / "distillation_runs.jsonl")
    for row in proposals + rejected:
        validate_instance("proposal", row, root)
    if any(row["status"] != "pending" for row in proposals):
        raise ValidationFailure("staging/proposals.jsonl may contain only pending proposals")
    if any(row["status"] != "rejected" for row in rejected):
        raise ValidationFailure("staging/rejected.jsonl may contain only rejected proposals")
    proposal_ids = [row["proposal_id"] for row in proposals + rejected]
    if len(proposal_ids) != len(set(proposal_ids)):
        raise ValidationFailure("proposal IDs must be unique across staging stores")
    run_ids = [row["id"] for row in distillation_runs]
    if len(run_ids) != len(set(run_ids)):
        raise ValidationFailure("distillation run IDs must be unique")
    known_proposal_ids = set(proposal_ids)
    for run in distillation_runs:
        validate_instance("distillation_run", run, root)
        decision_ids = [
            decision["candidate_id"] for decision in run["candidate_decisions"]
        ]
        if len(decision_ids) != len(set(decision_ids)):
            raise ValidationFailure(
                f"distillation run {run['id']} has duplicate candidate IDs"
            )
        missing_proposals = sorted(set(run["proposal_ids"]) - known_proposal_ids)
        if missing_proposals:
            raise ValidationFailure(
                f"distillation run {run['id']} references missing proposals: "
                + ", ".join(missing_proposals)
            )
        decision_proposals = sorted(
            decision["proposal_id"]
            for decision in run["candidate_decisions"]
            if decision["proposal_id"] is not None
        )
        if decision_proposals != sorted(run["proposal_ids"]):
            raise ValidationFailure(
                f"distillation run {run['id']} proposal index does not match decisions"
            )
    distilled_proposal_ids = {
        proposal_id
        for run in distillation_runs
        for proposal_id in run["proposal_ids"]
    }
    undistilled_external = sorted(
        row["proposal_id"]
        for row in proposals
        if row["created_by"] in EXTERNAL_PROPOSAL_ORIGINS
        and row["proposal_id"] not in distilled_proposal_ids
    )
    if undistilled_external:
        raise ValidationFailure(
            "External proposals lack distillation-run lineage: "
            + ", ".join(undistilled_external)
        )
    manifest = read_jsonl(staging / "corpus_manifest.jsonl")
    for row in manifest:
        validate_manifest_row(row)
    item_ids = [row["corpus_item_id"] for row in manifest]
    if len(item_ids) != len(set(item_ids)):
        raise ValidationFailure("duplicate corpus_item_id in manifest")
    by_id = {row["corpus_item_id"]: row for row in manifest}
    by_version: dict[str, list[str]] = {}
    for row in manifest:
        by_version.setdefault(row["sha256_or_source_version"], []).append(
            row["corpus_item_id"]
        )
        duplicate_of = row.get("duplicate_of")
        if duplicate_of is not None:
            original = by_id.get(duplicate_of)
            if original is None or (
                original["sha256_or_source_version"]
                != row["sha256_or_source_version"]
            ):
                raise ValidationFailure(
                    f"manifest duplicate link is unresolved: {row['corpus_item_id']}"
                )
    for version, ids in by_version.items():
        if len(ids) > 1:
            canonical = min(ids)
            unmarked = sorted(
                item_id
                for item_id in ids
                if item_id != canonical
                and by_id[item_id].get("duplicate_of") != canonical
            )
            if unmarked:
                raise ValidationFailure(
                    f"exact duplicate {version} lacks duplicate_of={canonical}: "
                    + ", ".join(unmarked)
                )
    return {
        "pending_proposals": len(proposals),
        "rejected_proposals": len(rejected),
        "corpus_items": len(manifest),
        "distillation_runs": len(distillation_runs),
    }


def _tree_hashes(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return {
        str(item.relative_to(path)): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def validate_control_plane(root: Path = REPO_ROOT) -> dict[str, Any]:
    schema_counts = validate_schemas(root)
    from .pegasus import load_analysis_profiles

    analysis_profiles = load_analysis_profiles(root)
    curated_counts = validate_curated(root)
    immutable_counts = validate_immutable(root)
    staging_counts = validate_staging(root)
    from . import reflect

    reflect.rebuild(root)
    first = _tree_hashes(root / "lab" / "second_brain" / "derived")
    reflect.rebuild(root)
    second = _tree_hashes(root / "lab" / "second_brain" / "derived")
    if first != second:
        raise ValidationFailure("reflection rebuild is not byte-identical")
    weights_path = root / "lab" / "second_brain" / "derived" / "weights.json"
    weights = json.loads(weights_path.read_text())
    for edge in weights.get("edges", []):
        validate_instance("learned_weight", edge, root)
    catalog_path = root / "lab" / "second_brain" / "derived" / "indexes" / "catalog.json"
    validate_instance("derived_indexes", json.loads(catalog_path.read_text()), root)
    return {
        **schema_counts,
        "analysis_profiles": len(analysis_profiles),
        "curated": curated_counts,
        "immutable": immutable_counts,
        "staging": staging_counts,
        "derived_files": len(first),
        "learned_edges": len(weights.get("edges", [])),
        "rebuild_determinism": "pass",
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scope",
        choices=("schemas", "curated", "immutable", "staging", "control-plane"),
    )
    args = parser.parse_args(argv)
    try:
        if args.scope == "schemas":
            result = validate_schemas()
        elif args.scope == "curated":
            result = validate_curated()
        elif args.scope == "immutable":
            result = validate_immutable()
        elif args.scope == "staging":
            result = validate_staging()
        else:
            result = validate_control_plane()
    except (ValidationFailure, PermissionError) as error:
        print(f"SECOND BRAIN {args.scope.upper()} RED: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(f"SECOND BRAIN {args.scope.upper()} GREEN")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
