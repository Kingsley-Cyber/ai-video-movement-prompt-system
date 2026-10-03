"""Schema, tier-boundary, hash-chain, and control-plane validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
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
    "directing_session": "directing_session.schema.json",
    "directing_session_contract": "directing_session_contract.schema.json",
    "concept": "concept.schema.json",
    "ontology_registry": "ontology_registry.schema.json",
    "claim": "claim.schema.json",
    "equation": "equation.schema.json",
    "method": "method.schema.json",
    "mechanism": "mechanism.schema.json",
    "reasoning_policy": "reasoning_policy.schema.json",
    "compiled_directing_strategy": "compiled_directing_strategy.schema.json",
    "edge": "edge.schema.json",
    "edge_compatibility": "edge_compatibility.schema.json",
    "edge_retype_review": "edge_retype_review.schema.json",
    "rule": "rule.schema.json",
    "intent": "intent.schema.json",
    "mapping": "mapping.schema.json",
    "curated_transaction": "curated_transaction.schema.json",
    "proposal": "proposal.schema.json",
    "distillation_batch": "distillation_batch.schema.json",
    "distillation_batch_validation": "distillation_batch_validation.schema.json",
    "distillation_run": "distillation_run.schema.json",
    "ontology_placement": "ontology_placement.schema.json",
    "research_graph_growth_plan": "research_graph_growth_plan.schema.json",
    "terminology_resolution": "terminology_resolution.schema.json",
    "terminology_resolution_proposal": "terminology_resolution_proposal.schema.json",
    "flight": "flight.schema.json",
    "experiment_flight_preparation": "experiment_flight_preparation.schema.json",
    "run": "run.schema.json",
    "experiment_receipt": "experiment_receipt.schema.json",
    "accepted_experiment_request": "accepted_experiment_request.schema.json",
    "accepted_experiment_state": "accepted_experiment_state.schema.json",
    "improvement_orchestration": "improvement_orchestration.schema.json",
    "human_testimonial_capture": "human_testimonial_capture.schema.json",
    "human_testimonial": "human_testimonial.schema.json",
    "testimonial_review_request": "testimonial_review_request.schema.json",
    "testimonial_review": "testimonial_review.schema.json",
    "pegasus_observation": "pegasus_observation.schema.json",
    "measurement_observation": "measurement_observation.schema.json",
    "pose_measurement_job": "pose_measurement_job.schema.json",
    "measurement_batch": "measurement_batch.schema.json",
    "learned_weight": "learned_weight.schema.json",
    "reasoning_query": "reasoning_query.schema.json",
    "retrieval_frame": "retrieval_frame.schema.json",
    "domain_coverage_manifest": "domain_coverage_manifest.schema.json",
    "domain_coverage_report": "domain_coverage_report.schema.json",
    "core_memory_view": "core_memory_view.schema.json",
    "outcome_memory": "outcome_memory.schema.json",
    "brain_health_report": "brain_health_report.schema.json",
    "maintenance_state": "maintenance_state.schema.json",
    "knowledge_maintenance_event": "knowledge_maintenance_event.schema.json",
    "video_concept_bridge": "video_concept_bridge.schema.json",
    "video_research_gap_report": "video_research_gap_report.schema.json",
    "knowledge_comparison_lens": "knowledge_comparison_lens.schema.json",
    "retrieval_benchmark": "retrieval_benchmark.schema.json",
    "retrieval_benchmark_report": "retrieval_benchmark_report.schema.json",
    "scale_benchmark": "scale_benchmark.schema.json",
    "scale_benchmark_report": "scale_benchmark_report.schema.json",
    "context_bundle": "context_bundle.schema.json",
    "context_enrichment": "context_enrichment.schema.json",
    "normalized_intent": "normalized_intent.schema.json",
    "twelvelabs_analysis_profiles": "twelvelabs_analysis_profiles.schema.json",
    "twelvelabs_asset_job": "twelvelabs_asset_job.schema.json",
    "twelvelabs_analyze_job": "twelvelabs_analyze_job.schema.json",
    "twelvelabs_segment_job": "twelvelabs_segment_job.schema.json",
    "twelvelabs_batch_job": "twelvelabs_batch_job.schema.json",
    "twelvelabs_search_job": "twelvelabs_search_job.schema.json",
    "twelvelabs_jockey_job": "twelvelabs_jockey_job.schema.json",
    "twelvelabs_marengo_job": "twelvelabs_marengo_job.schema.json",
    "twelvelabs_surface_completion": "twelvelabs_surface_completion.schema.json",
    "twelvelabs_semantic_response": "twelvelabs_semantic_response.schema.json",
    "twelvelabs_verification_response": "twelvelabs_verification_response.schema.json",
    "twelvelabs_corpus_response": "twelvelabs_corpus_response.schema.json",
    "normalized_video_observation": "normalized_video_observation.schema.json",
    "video_observation_graph": "video_observation_graph.schema.json",
    "video_analysis_cascade": "video_analysis_cascade.schema.json",
    "atomic_video_analysis_request": "atomic_video_analysis_request.schema.json",
    "atomic_video_analysis_plan": "atomic_video_analysis_plan.schema.json",
    "source_extraction_bundle": "source_extraction_bundle.schema.json",
    "semantic_extraction_response": "semantic_extraction_response.schema.json",
    "research_extraction_session": "research_extraction_session.schema.json",
    "research_session_contract": "research_session_contract.schema.json",
    "research_delta_request": "research_delta_request.schema.json",
    "research_delta_plan": "research_delta_plan.schema.json",
    "research_delta_patch_request": "research_delta_patch_request.schema.json",
    "research_delta_patch_state": "research_delta_patch_state.schema.json",
    "research_delta_patch_receipt": "research_delta_patch_receipt.schema.json",
    "research_delta_patch_cleanup": "research_delta_patch_cleanup.schema.json",
    "retrieved_passages": "retrieved_passages.schema.json",
    "polymath_retrieval": "polymath_retrieval.schema.json",
    "knowledge_search": "knowledge_search.schema.json",
    "derived_indexes": "derived_indexes.schema.json",
    "graph_projection_plan": "graph_projection_plan.schema.json",
    "graph_projection_checkpoint": "graph_projection_checkpoint.schema.json",
    "source_unit": "source_unit.schema.json",
    "source_closure_report": "source_closure_report.schema.json",
    "source_answer_trace": "source_answer_trace.schema.json",
}

STORE_SCHEMAS = {
    REPO_ROOT / "lab" / "concepts.jsonl": "concept",
    CURATED / "edges.jsonl": "edge",
    CURATED / "rules.jsonl": "rule",
    CURATED / "intents.jsonl": "intent",
    CURATED / "mappings.jsonl": "mapping",
    CURATED / "claims.jsonl": "claim",
    CURATED / "equations.jsonl": "equation",
    CURATED / "methods.jsonl": "method",
    CURATED / "mechanisms.jsonl": "mechanism",
    CURATED / "reasoning_policies.jsonl": "reasoning_policy",
    CURATED / "domain_coverage_manifests.jsonl": "domain_coverage_manifest",
    CURATED / "video_concept_bridges.jsonl": "video_concept_bridge",
    STAGING / "proposals.jsonl": "proposal",
    STAGING / "distillation_runs.jsonl": "distillation_run",
    STAGING / "graph_growth_plans.jsonl": "research_graph_growth_plan",
    STAGING / "terminology_resolutions.jsonl": "terminology_resolution_proposal",
    IMMUTABLE / "flights.jsonl": "flight",
    IMMUTABLE / "runs.jsonl": "run",
    IMMUTABLE / "pegasus_observations.jsonl": "pegasus_observation",
    IMMUTABLE / "measurement_observations.jsonl": "measurement_observation",
    IMMUTABLE / "testimonials.jsonl": "human_testimonial",
    IMMUTABLE / "testimonial_reviews.jsonl": "testimonial_review",
    IMMUTABLE / "improvement_orchestrations.jsonl": "improvement_orchestration",
    IMMUTABLE / "source_units.jsonl": "source_unit",
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
    "placement": (STAGING / "graph_growth_plans.jsonl",),
    "terminology": (STAGING / "terminology_resolutions.jsonl",),
    "pegasus": (IMMUTABLE / "pegasus_observations.jsonl",),
    "query": (REPO_ROOT / "work",),
    "twelvelabs": (REPO_ROOT / "work",),
    "source_extract": (REPO_ROOT / "work",),
    "source_registry": (IMMUTABLE / "source_units.jsonl",),
    "video_bridge": (CURATED / "video_concept_bridges.jsonl",),
    "research_delta": (REPO_ROOT / "work" / "application" / "research_deltas",),
    "research_delta_patch": (
        REPO_ROOT / "work" / "application" / "research_delta_patches",
    ),
    "neo4j_projection": (REPO_ROOT / "work" / "neo4j",),
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


def normalize_concept_identity(value: str) -> str:
    """Return the deterministic identity form used for concept names and aliases."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    characters = "".join(
        character if character.isalnum() else " " for character in normalized
    )
    return " ".join(characters.split())


def load_ontology_registry(root: Path = REPO_ROOT) -> dict[str, Any]:
    path = root / "lab" / "second_brain" / "curated" / "ontology_registry.json"
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationFailure(f"cannot read ontology registry: {exc}") from exc
    validate_instance("ontology_registry", registry, root)
    unknown_roots = sorted(
        set(registry["layers"].values()) - set(registry["layer_roots"])
    )
    if unknown_roots:
        raise ValidationFailure(
            "ontology layers reference unknown roots: " + ", ".join(unknown_roots)
        )
    from .graph import AUTHORED_EDGE_POLICY, _edge_directionality

    edge_contracts = registry["edge_type_contracts"]
    runtime_edge_types = AUTHORED_EDGE_POLICY["types"]
    if set(edge_contracts) != set(runtime_edge_types):
        raise ValidationFailure(
            "ontology edge contracts differ from runtime edge policy"
        )
    for edge_type, contract in sorted(edge_contracts.items()):
        runtime = runtime_edge_types[edge_type]
        if contract["family"] != runtime["family"]:
            raise ValidationFailure(
                f"ontology edge contract {edge_type} has the wrong family"
            )
        if contract["directionality"] != _edge_directionality(runtime):
            raise ValidationFailure(
                f"ontology edge contract {edge_type} has the wrong directionality"
            )
        for field, allowed in (
            ("allowed_kind_pairs", set(registry["concept_kinds"])),
            (
                "allowed_cross_layer_root_pairs",
                set(registry["layer_roots"]),
            ),
        ):
            pairs = []
            for pair in contract[field]:
                if not set(pair) <= allowed:
                    raise ValidationFailure(
                        f"ontology edge contract {edge_type} {field} references an unknown value"
                    )
                normalized = (
                    sorted(pair)
                    if contract["directionality"] == "symmetric"
                    else list(pair)
                )
                pairs.append(tuple(normalized))
            if len(pairs) != len(set(pairs)):
                raise ValidationFailure(
                    f"ontology edge contract {edge_type} repeats a normalized {field} pair"
                )
    identifier_ids = [row["id"] for row in registry["identifier_rules"]]
    if len(identifier_ids) != len(set(identifier_ids)):
        raise ValidationFailure("duplicate ontology identifier rule ID")
    term_ids = [row["id"] for row in registry["term_senses"]]
    if len(term_ids) != len(set(term_ids)):
        raise ValidationFailure("duplicate ontology term-sense ID")
    term_aliases: dict[str, str] = {}
    registered_senses: set[str] = set()
    for term in registry["term_senses"]:
        sense_ids = [row["sense_id"] for row in term["senses"]]
        if len(sense_ids) != len(set(sense_ids)):
            raise ValidationFailure(
                f"ontology term {term['id']} repeats a sense ID"
            )
        registered_senses.update(sense_ids)
        for alias in term["aliases"]:
            normalized = normalize_concept_identity(alias)
            owner = term_aliases.setdefault(normalized, term["id"])
            if owner != term["id"]:
                raise ValidationFailure(
                    f"ontology term alias {normalized} belongs to multiple term records"
                )
    for rule in registry["identifier_rules"]:
        try:
            pattern = re.compile(rule["pattern"])
        except re.error as exc:
            raise ValidationFailure(
                f"ontology identifier rule {rule['id']} has invalid pattern: {exc}"
            ) from exc
        if pattern.groups < rule["capture_group"]:
            raise ValidationFailure(
                f"ontology identifier rule {rule['id']} capture_group is missing"
            )
        if rule["sense_id"] not in registered_senses:
            raise ValidationFailure(
                f"ontology identifier rule {rule['id']} references an unknown sense"
            )
    return registry


def validate_concept_registry(
    concepts: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
    root: Path = REPO_ROOT,
) -> dict[str, int]:
    """Validate closed classifications and deterministic concept identity collisions."""
    registry = load_ontology_registry(root)
    concept_ids = {row["id"] for row in concepts}
    unknown_kinds = sorted(
        f"{row['id']}:{row['kind']}"
        for row in concepts
        if row["kind"] not in registry["concept_kinds"]
    )
    if unknown_kinds:
        raise ValidationFailure("unregistered concept kinds: " + ", ".join(unknown_kinds))
    unknown_layers = sorted(
        f"{row['id']}:{row['layer']}"
        for row in concepts
        if row["layer"] not in registry["layers"]
    )
    if unknown_layers:
        raise ValidationFailure("unregistered concept layers: " + ", ".join(unknown_layers))

    by_id = {row["id"]: row for row in concepts}

    def identity_head(record_id: str) -> str:
        """Collapse one already-validated supersession chain to its current identity head."""
        current_id = record_id
        while True:
            successors = by_id[current_id].get("validity", {}).get("superseded_by", [])
            if not successors:
                return current_id
            current_id = successors[0]

    names: dict[str, set[str]] = {}
    aliases: dict[str, set[str]] = {}
    fingerprints: dict[tuple[str, str, str, str], set[str]] = {}
    scale_work_root = (REPO_ROOT / "work" / "scale").resolve()
    fixture_root = root.resolve()
    allow_scale_replicas = scale_work_root in fixture_root.parents
    for row in concepts:
        fixture = row.get("scale_fixture")
        if (
            allow_scale_replicas
            and isinstance(fixture, dict)
            and isinstance(fixture.get("source_concept_id"), str)
            and isinstance(fixture.get("replica"), int)
            and row["id"]
            == f"{fixture['source_concept_id']}__scale_{fixture['replica']:03d}"
        ):
            continue
        identity_id = identity_head(row["id"])
        name = normalize_concept_identity(row["name"])
        names.setdefault(name, set()).add(identity_id)
        fingerprint = (
            name,
            normalize_concept_identity(row["what"]),
            normalize_concept_identity(row["use_when"]),
        )
        fingerprints.setdefault(fingerprint, set()).add(identity_id)
        for phrase in {row["name"], *row.get("nl_triggers", [])}:
            normalized = normalize_concept_identity(phrase)
            if normalized:
                aliases.setdefault(normalized, set()).add(identity_id)

    duplicate_names = {name: ids for name, ids in names.items() if len(ids) > 1}
    if duplicate_names:
        detail = "; ".join(
            f"{name}={','.join(sorted(ids))}"
            for name, ids in sorted(duplicate_names.items())
        )
        raise ValidationFailure("duplicate normalized concept names: " + detail)
    duplicate_fingerprints = [
        sorted(ids) for ids in fingerprints.values() if len(ids) > 1
    ]
    if duplicate_fingerprints:
        raise ValidationFailure(
            "duplicate normalized concept fingerprints: "
            + "; ".join(",".join(ids) for ids in sorted(duplicate_fingerprints))
        )

    declared_ambiguities: dict[str, set[str]] = {}
    for row in registry["ambiguous_aliases"]:
        alias = normalize_concept_identity(row["alias"])
        if alias in declared_ambiguities:
            raise ValidationFailure(f"duplicate ontology ambiguity declaration: {alias}")
        ids = set(row["concept_ids"])
        missing = sorted(ids - concept_ids)
        if missing:
            raise ValidationFailure(
                f"ontology ambiguity {alias} references missing concepts: "
                + ", ".join(missing)
            )
        declared_ambiguities[alias] = ids
    actual_ambiguities = {
        alias: ids for alias, ids in aliases.items() if len(ids) > 1
    }
    if actual_ambiguities != declared_ambiguities:
        unexpected = sorted(set(actual_ambiguities) - set(declared_ambiguities))
        stale = sorted(set(declared_ambiguities) - set(actual_ambiguities))
        mismatched = sorted(
            alias
            for alias in set(actual_ambiguities) & set(declared_ambiguities)
            if actual_ambiguities[alias] != declared_ambiguities[alias]
        )
        raise ValidationFailure(
            "concept alias registry mismatch "
            f"unexpected={unexpected} stale={stale} mismatched={mismatched}"
        )
    registry_pointer = root / "lab" / "registry.yaml"
    terminology_required = (
        registry_pointer.exists()
        and "second_brain_terminology:" in registry_pointer.read_text(encoding="utf-8")
    )
    if terminology_required:
        terminology_refs = {
            concept_id
            for term in registry["term_senses"]
            for sense in term["senses"]
            for concept_id in sense["concept_ids"]
        } | {
            concept_id
            for rule in registry["identifier_rules"]
            for concept_id in rule["concept_ids"]
        }
        missing = sorted(terminology_refs - concept_ids)
        if missing:
            raise ValidationFailure(
                "ontology terminology references missing concepts: "
                + ", ".join(missing)
            )
        term_candidates = {
            normalize_concept_identity(alias): {
                concept_id
                for sense in term["senses"]
                for concept_id in sense["concept_ids"]
            }
            for term in registry["term_senses"]
            for alias in term["aliases"]
        }
        mismatched_terms = sorted(
            alias
            for alias, ids in declared_ambiguities.items()
            if alias in term_candidates and term_candidates[alias] != ids
        )
        if mismatched_terms:
            raise ValidationFailure(
                "ontology term senses disagree with declared ambiguity: "
                + ", ".join(mismatched_terms)
            )

    unknown_target_types = sorted(
        f"{row['id']}:{row['target_type']}"
        for row in mappings
        if row["target_type"] not in registry["mapping_target_types"]
    )
    if unknown_target_types:
        raise ValidationFailure(
            "unregistered mapping target types: " + ", ".join(unknown_target_types)
        )
    unknown_namespaces = sorted(
        f"{row['id']}:{row['target_id'].split('.', 1)[0]}"
        for row in mappings
        if row["target_id"].split(".", 1)[0]
        not in registry["control_namespaces"]
    )
    if unknown_namespaces:
        raise ValidationFailure(
            "unregistered control namespaces: " + ", ".join(unknown_namespaces)
        )
    for mapping in mappings:
        strategy = mapping.get("representation_strategy")
        if not strategy:
            continue
        formats = [row["format"] for row in strategy["projections"]]
        if len(formats) != len(set(formats)):
            raise ValidationFailure(
                f"mapping {mapping['id']} has duplicate representation formats"
            )
        unknown_roles = sorted(
            {
                role
                for projection in strategy["projections"]
                for role in projection["roles"]
            }
            - set(registry["representation_roles"])
        )
        if unknown_roles:
            raise ValidationFailure(
                f"mapping {mapping['id']} has unregistered representation roles: "
                + ", ".join(unknown_roles)
            )
    return {
        "concept_kinds": len(registry["concept_kinds"]),
        "layers": len(registry["layers"]),
        "ambiguous_aliases": len(declared_ambiguities),
        "identifier_rules": len(registry["identifier_rules"]),
        "term_senses": len(registry["term_senses"]),
    }


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


def validate_curated(
    root: Path = REPO_ROOT,
    *,
    allow_recoverable_legacy_reciprocals: bool = False,
) -> dict[str, int]:
    concept_path = root / "lab" / "concepts.jsonl"
    sb = root / "lab" / "second_brain"
    paths = {
        concept_path: "concept",
        sb / "curated" / "edges.jsonl": "edge",
        sb / "curated" / "rules.jsonl": "rule",
        sb / "curated" / "intents.jsonl": "intent",
        sb / "curated" / "mappings.jsonl": "mapping",
        sb / "curated" / "claims.jsonl": "claim",
        sb / "curated" / "equations.jsonl": "equation",
        sb / "curated" / "methods.jsonl": "method",
        sb / "curated" / "mechanisms.jsonl": "mechanism",
        sb / "curated" / "reasoning_policies.jsonl": "reasoning_policy",
    }
    for optional_path, schema_name in (
        (sb / "curated" / "domain_coverage_manifests.jsonl", "domain_coverage_manifest"),
        (sb / "curated" / "video_concept_bridges.jsonl", "video_concept_bridge"),
    ):
        if optional_path.exists():
            paths[optional_path] = schema_name
    rows_by_path: dict[Path, list[dict[str, Any]]] = {}
    for path, schema_name in paths.items():
        rows = read_jsonl(path)
        rows_by_path[path] = rows
        for row in rows:
            validate_instance(schema_name, row, root)
    concepts = rows_by_path[concept_path]
    from .temporal import validate_temporal_collections

    try:
        validate_temporal_collections({"concept": concepts})
    except ValueError as exc:
        raise ValidationFailure(str(exc)) from exc
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
    video_bridges = rows_by_path.get(
        sb / "curated" / "video_concept_bridges.jsonl", []
    )
    bad_video_bridges = sorted(
        row["id"] for row in video_bridges if row["concept_id"] not in valid_ids
    )
    if bad_video_bridges:
        raise ValidationFailure(
            "video bridge references missing concept: "
            + ", ".join(bad_video_bridges)
        )
    for row in video_bridges:
        if row["bridge_hash"] != content_hash(row, ("bridge_hash",)):
            raise ValidationFailure(
                f"video bridge {row['id']} has invalid bridge_hash"
            )
    ontology_counts = validate_concept_registry(concepts, mappings, root)
    reasoning_policies = rows_by_path[
        sb / "curated" / "reasoning_policies.jsonl"
    ]
    mismatched_policy_ids = sorted(
        row["id"] for row in reasoning_policies if row["id"] != row["policy_id"]
    )
    if mismatched_policy_ids:
        raise ValidationFailure(
            "reasoning policy id must equal policy_id: "
            + ", ".join(mismatched_policy_ids)
        )
    bad_policy_refs = sorted(
        f"{row['id']}:{concept_id}"
        for row in reasoning_policies
        for concept_id in row["concept_ids"]
        if concept_id not in valid_ids
    )
    if bad_policy_refs:
        raise ValidationFailure(
            "reasoning policy references missing concept: "
            + ", ".join(bad_policy_refs)
        )
    for store_name, schema_name in (
        ("claims", "claim"),
        ("equations", "equation"),
        ("methods", "method"),
        ("mechanisms", "mechanism"),
    ):
        rows = rows_by_path[sb / "curated" / f"{store_name}.jsonl"]
        bad_refs = sorted(
            f"{row['id']}:{concept_id}"
            for row in rows
            for concept_id in row["concept_ids"]
            if concept_id not in valid_ids
        )
        if bad_refs:
            raise ValidationFailure(
                f"{schema_name} references missing concept: " + ", ".join(bad_refs)
            )
    research_ids = {
        "claim": {
            row["id"]
            for row in rows_by_path[sb / "curated" / "claims.jsonl"]
        },
        "equation": {
            row["id"]
            for row in rows_by_path[sb / "curated" / "equations.jsonl"]
        },
        "method": {
            row["id"]
            for row in rows_by_path[sb / "curated" / "methods.jsonl"]
        },
        "mechanism": {
            row["id"]
            for row in rows_by_path[sb / "curated" / "mechanisms.jsonl"]
        },
    }
    reference_fields = {
        "claim": {
            "method_ids": "method",
            "supports_claim_ids": "claim",
            "contradicts_claim_ids": "claim",
        },
        "equation": {
            "method_ids": "method",
            "mechanism_ids": "mechanism",
        },
        "method": {
            "equation_ids": "equation",
            "mechanism_ids": "mechanism",
        },
        "mechanism": {
            "claim_ids": "claim",
            "method_ids": "method",
            "equation_ids": "equation",
        },
    }
    for schema_name, fields in reference_fields.items():
        rows = rows_by_path[
            sb / "curated" / f"{schema_name}s.jsonl"
        ]
        for row in rows:
            if any(
                row["id"] in row.get(field, [])
                for field in fields
            ):
                raise ValidationFailure(
                    f"{schema_name} {row['id']} cannot reference itself"
                )
            missing_object_refs = sorted(
                f"{field}:{reference}"
                for field, target_type in fields.items()
                for reference in row.get(field, [])
                if reference not in research_ids[target_type]
            )
            if schema_name == "equation":
                missing_object_refs.extend(
                    f"operational_mappings.method_id:{mapping['method_id']}"
                    for mapping in row.get("operational_mappings", [])
                    if mapping.get("method_id")
                    and mapping["method_id"] not in research_ids["method"]
                )
            if missing_object_refs:
                raise ValidationFailure(
                    f"{schema_name} {row['id']} references missing research objects: "
                    + ", ".join(sorted(missing_object_refs))
                )
    all_curated_ids = [
        row["id"]
        for rows in rows_by_path.values()
        for row in rows
    ]
    if len(all_curated_ids) != len(set(all_curated_ids)):
        raise ValidationFailure("durable IDs must be unique across curated stores")
    from .graph import validate_edge_compatibilities, validate_edge_distribution
    from .temporal import validate_temporal_collections, visible_records

    try:
        validate_temporal_collections(
            {
                schema_name: rows_by_path[path]
                for path, schema_name in paths.items()
            }
        )
        validate_edge_distribution(
            visible_records(edges),
            allow_recoverable_legacy_reciprocals=(
                allow_recoverable_legacy_reciprocals
            ),
        )
        registry_pointer = root / "lab" / "registry.yaml"
        edge_contract_enabled = (
            registry_pointer.exists()
            and "second_brain_edge_compatibility_schema:"
            in registry_pointer.read_text(encoding="utf-8")
        )
        if edge_contract_enabled:
            validate_edge_compatibilities(
                edges,
                concepts,
                load_ontology_registry(root),
                root=root,
            )
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
        "claims": len(rows_by_path[sb / "curated" / "claims.jsonl"]),
        "equations": len(rows_by_path[sb / "curated" / "equations.jsonl"]),
        "methods": len(rows_by_path[sb / "curated" / "methods.jsonl"]),
        "mechanisms": len(rows_by_path[sb / "curated" / "mechanisms.jsonl"]),
        "reasoning_policies": len(reasoning_policies),
        "ontology_layers": ontology_counts["layers"],
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
        base / "testimonials.jsonl": "human_testimonial",
        base / "testimonial_reviews.jsonl": "testimonial_review",
        base / "improvement_orchestrations.jsonl": "improvement_orchestration",
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
    from .source_registry import load_source_units

    counts["source_unit"] = len(load_source_units(root))
    concepts = {
        row["id"]: row for row in read_jsonl(root / "lab" / "concepts.jsonl")
    }
    intents = {
        row["id"]
        for row in read_jsonl(
            root / "lab" / "second_brain" / "curated" / "intents.jsonl"
        )
    }
    testimonials = rows_by_schema["human_testimonial"]
    testimonial_by_id = {row["id"]: row for row in testimonials}
    testimonial_children: dict[str, int] = {}
    for row in testimonials:
        exact_hash = "sha256:" + hashlib.sha256(
            row["raw_statement"].encode("utf-8")
        ).hexdigest()
        if row["raw_statement_hash"] != exact_hash:
            raise ValidationFailure(
                f"testimonial {row['id']} raw_statement_hash is invalid"
            )
        for predecessor_id in row["supersedes"]:
            predecessor = testimonial_by_id.get(predecessor_id)
            if predecessor is None:
                raise ValidationFailure(
                    f"testimonial {row['id']} supersedes missing record {predecessor_id}"
                )
            testimonial_children[predecessor_id] = (
                testimonial_children.get(predecessor_id, 0) + 1
            )
            if (
                predecessor["artifact"] != row["artifact"]
                or predecessor["speaker"] != row["speaker"]
            ):
                raise ValidationFailure(
                    f"testimonial {row['id']} changes artifact or speaker across correction"
                )
    branched_testimonials = sorted(
        record_id
        for record_id, count in testimonial_children.items()
        if count > 1
    )
    if branched_testimonials:
        raise ValidationFailure(
            "testimonial correction chains branch at: "
            + ", ".join(branched_testimonials)
        )

    testimonial_reviews = rows_by_schema["testimonial_review"]
    testimonial_review_by_id = {row["id"]: row for row in testimonial_reviews}
    review_children: dict[str, int] = {}
    for row in testimonial_reviews:
        testimonial = testimonial_by_id.get(row["testimonial_id"])
        if testimonial is None:
            raise ValidationFailure(
                f"testimonial review {row['id']} references missing raw statement"
            )
        if (
            row["testimonial_record_hash"] != testimonial["record_hash"]
            or row["raw_statement_hash"] != testimonial["raw_statement_hash"]
            or row["artifact"]
            != {
                key: testimonial["artifact"][key]
                for key in (
                    "render_job_id",
                    "build_id",
                    "artifact_id",
                    "artifact_sha256",
                )
            }
        ):
            raise ValidationFailure(
                f"testimonial review {row['id']} has invalid raw/artifact lineage"
            )
        normalization = row["normalization"]
        dimension_ids = [
            finding["dimension"]
            for finding in normalization["dimension_findings"]
        ]
        if len(dimension_ids) != len(set(dimension_ids)):
            raise ValidationFailure(
                f"testimonial review {row['id']} repeats a dimension finding"
            )
        if normalization["normalizer"]["origin"] == "llm_proposal":
            normalized_response = json.loads(json.dumps(normalization))
            reported_hash = normalized_response["normalizer"].pop(
                "response_hash"
            )
            if reported_hash != sha256_value(normalized_response):
                raise ValidationFailure(
                    f"testimonial review {row['id']} has invalid LLM response_hash"
                )
        for predecessor_id in row["supersedes_reviews"]:
            if predecessor_id not in testimonial_review_by_id:
                raise ValidationFailure(
                    f"testimonial review {row['id']} supersedes missing review {predecessor_id}"
                )
            review_children[predecessor_id] = review_children.get(predecessor_id, 0) + 1
        for finding in (
            row["normalization"]["dimension_findings"]
            + row["normalization"]["strengths"]
            + row["normalization"]["failures"]
            + row["normalization"]["attribution_candidates"]
        ):
            for span in finding["evidence_spans"]:
                if (
                    span["start"] >= span["end"]
                    or span["end"] > len(testimonial["raw_statement"])
                ):
                    raise ValidationFailure(
                        f"testimonial review {row['id']} has an out-of-range evidence span"
                    )
                quote = testimonial["raw_statement"][span["start"] : span["end"]]
                quote_hash = "sha256:" + hashlib.sha256(quote.encode("utf-8")).hexdigest()
                if quote != span["quote"] or quote_hash != span["quote_hash"]:
                    raise ValidationFailure(
                        f"testimonial review {row['id']} has an invalid evidence span"
                    )
    branched_reviews = sorted(
        record_id for record_id, count in review_children.items() if count > 1
    )
    if branched_reviews:
        raise ValidationFailure(
            "testimonial review chains branch at: " + ", ".join(branched_reviews)
        )
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
            policy_version = run["evidence_design"].get("policy_version")
            if policy_version not in {
                "cpcs-controlled-evidence/1.0",
                "cpcs-controlled-evidence/1.1",
            } or run["evidence_design"] != {
                "classification": design["classification"],
                "causal_eligibility": expected_eligibility,
                "outcome_concept_ids": sorted(design["outcome_concept_ids"]),
                "policy_version": policy_version,
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
            fingerprint_payload = {
                "flight_hash": run["flight_hash"],
                "arm": run["arm"],
                "lineage": lineage,
                "controls": run["controls"],
                "tested_delta": run["tested_delta"],
                "metrics": run["metrics"],
                "human_review": review,
            }
            metric_evidence = run.get("metric_evidence")
            if policy_version == "cpcs-controlled-evidence/1.1":
                metric_ids = [row["metric_id"] for row in metric_evidence]
                if len(metric_ids) != len(set(metric_ids)) or set(metric_ids) != set(
                    run["metrics"]
                ):
                    raise ValidationFailure(
                        f"run {run['id']} metric evidence does not cover every metric exactly once"
                    )
                for metric_row in metric_evidence:
                    if canonical_json_bytes(metric_row["value"]) != canonical_json_bytes(
                        run["metrics"][metric_row["metric_id"]]
                    ):
                        raise ValidationFailure(
                            f"run {run['id']} metric evidence value is inconsistent"
                        )
                fingerprint_payload["metric_evidence"] = metric_evidence
            elif metric_evidence is not None:
                raise ValidationFailure(
                    f"run {run['id']} claims metric evidence under policy 1.0"
                )
            testimonial_lineage = run.get("testimonial_lineage")
            if testimonial_lineage is not None:
                testimonial = testimonial_by_id.get(
                    testimonial_lineage["testimonial_id"]
                )
                testimonial_review = testimonial_review_by_id.get(
                    testimonial_lineage["testimonial_review_id"]
                )
                if (
                    testimonial is None
                    or testimonial_review is None
                    or testimonial_review["testimonial_id"] != testimonial["id"]
                    or testimonial["record_hash"]
                    != testimonial_lineage["testimonial_record_hash"]
                    or testimonial["raw_statement_hash"]
                    != testimonial_lineage["raw_statement_hash"]
                    or testimonial_review["record_hash"]
                    != testimonial_lineage["testimonial_review_record_hash"]
                    or review.get("testimonial_review_id")
                    != testimonial_review["id"]
                    or lineage["artifact_id"]
                    != testimonial_lineage["artifact_id"]
                    or lineage["artifact_sha256"]
                    != testimonial_lineage["artifact_sha256"]
                    or review["verdict"]
                    != testimonial_lineage["normalized_verdict"]
                ):
                    raise ValidationFailure(
                        f"run {run['id']} testimonial lineage is invalid"
                    )
                fingerprint_payload["testimonial_lineage"] = testimonial_lineage
            expected_fingerprint = sha256_value(fingerprint_payload)
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
    run_by_id = {row["id"]: row for row in rows_by_schema["run"]}
    accepted_flights: set[str] = set()
    for orchestration in rows_by_schema["improvement_orchestration"]:
        flight_id = orchestration["flight"]["flight_id"]
        flight = flights.get(flight_id)
        if flight is None or orchestration["flight"]["flight_hash"] != flight["flight_hash"]:
            raise ValidationFailure(
                f"improvement orchestration {orchestration['id']} lost its sealed flight"
            )
        if flight_id in accepted_flights:
            raise ValidationFailure(
                f"experiment flight {flight_id} has multiple accepted orchestrations"
            )
        accepted_flights.add(flight_id)
        run_ids = orchestration["evidence_snapshot"]["run_ids"]
        if set(run_ids) != set(orchestration["authority_effects"]["immutable_run_ids"]):
            raise ValidationFailure(
                f"improvement orchestration {orchestration['id']} has inconsistent run sets"
            )
        for run_id in run_ids:
            run = run_by_id.get(run_id)
            if (
                run is None
                or run["flight_id"] != flight_id
                or orchestration["evidence_snapshot"]["run_fingerprints"].get(run_id)
                != run["evidence_fingerprint"]
                or orchestration["evidence_snapshot"]["run_record_hashes"].get(run_id)
                != run["record_hash"]
            ):
                raise ValidationFailure(
                    f"improvement orchestration {orchestration['id']} has invalid run lineage"
                )
    return counts


def validate_staging(root: Path = REPO_ROOT) -> dict[str, int]:
    staging = root / "lab" / "second_brain" / "staging"
    proposals = read_jsonl(staging / "proposals.jsonl")
    rejected = read_jsonl(staging / "rejected.jsonl")
    distillation_runs = read_jsonl(staging / "distillation_runs.jsonl")
    growth_plan_path = staging / "graph_growth_plans.jsonl"
    graph_growth_plans = (
        read_jsonl(growth_plan_path) if growth_plan_path.exists() else []
    )
    terminology_path = staging / "terminology_resolutions.jsonl"
    terminology_resolutions = (
        read_jsonl(terminology_path) if terminology_path.exists() else []
    )
    for row in terminology_resolutions:
        validate_instance("terminology_resolution_proposal", row, root)
        if row["proposal_hash"] != content_hash(row, ("proposal_hash",)):
            raise ValidationFailure(
                f"terminology proposal {row['id']} has invalid proposal_hash"
            )
    terminology_ids = [row["id"] for row in terminology_resolutions]
    if len(terminology_ids) != len(set(terminology_ids)):
        raise ValidationFailure("terminology proposal IDs must be unique")
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
    growth_plan_ids = [row["id"] for row in graph_growth_plans]
    if len(growth_plan_ids) != len(set(growth_plan_ids)):
        raise ValidationFailure("research graph growth plan IDs must be unique")
    known_run_ids = set(run_ids)
    for plan in graph_growth_plans:
        validate_instance("research_graph_growth_plan", plan, root)
        if plan["run_id"] not in known_run_ids:
            raise ValidationFailure(
                f"growth plan {plan['id']} references missing run {plan['run_id']}"
            )
        if plan["plan_hash"] != content_hash(plan, ("plan_hash",)):
            raise ValidationFailure(
                f"growth plan {plan['id']} has invalid plan_hash"
            )
        placement_proposals = []
        for placement in plan["placements"]:
            validate_instance("ontology_placement", placement, root)
            if placement["placement_hash"] != content_hash(
                placement, ("placement_hash",)
            ):
                raise ValidationFailure(
                    f"growth plan {plan['id']} contains an invalid placement hash"
                )
            if placement["proposal_id"] is not None:
                placement_proposals.append(placement["proposal_id"])
        if sorted(placement_proposals) != sorted(
            set(plan["promotion_proposal_ids"]) | set(plan["blocked_proposal_ids"])
        ):
            raise ValidationFailure(
                f"growth plan {plan['id']} proposal partitions do not match placements"
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
        "graph_growth_plans": len(graph_growth_plans),
        "terminology_resolutions": len(terminology_resolutions),
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
    derived_schema_files = {
        "source_closure_report": "source_closure.json",
        "domain_coverage_report": "domain_coverage.json",
        "core_memory_view": "core_memory.json",
        "outcome_memory": "outcome_memory.json",
        "brain_health_report": "brain_health.json",
    }
    for schema_name, relative_path in derived_schema_files.items():
        path = root / "lab" / "second_brain" / "derived" / relative_path
        validate_instance(schema_name, json.loads(path.read_text()), root)
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
