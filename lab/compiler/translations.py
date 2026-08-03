"""Translate gated curated mappings into declared canonical score fields."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from .profiles import REPO_ROOT
from .provenance import sha256_value

TRANSLATION_POLICY_VERSION = "cpcs-control-translation/1.0"
TRANSLATION_REGISTRY_SCHEMA = "cpcs.control_translation_registry/1.0"


@dataclass(frozen=True)
class TranslationCatalog:
    records_by_mapping: dict[str, dict[str, Any]]
    record_hashes: dict[str, str]
    mapping_hashes: dict[str, str]
    mapping_concepts: dict[str, str]


@dataclass(frozen=True)
class TranslationResult:
    contributions: tuple[dict[str, Any], ...]
    applied: tuple[dict[str, Any], ...]
    dispositions: tuple[dict[str, Any], ...]
    verification_metrics: tuple[dict[str, Any], ...]


def mapping_contract_hash(mapping: dict[str, Any]) -> str:
    """Hash the durable mapping record while ignoring context-only trust labeling."""
    durable = {
        key: copy.deepcopy(value)
        for key, value in mapping.items()
        if key != "trust_class"
    }
    return sha256_value(durable)


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot read control translation registry: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("control translation registry must be an object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"cannot read curated mappings: {exc}") from exc
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid curated mapping on line {line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"curated mapping line {line_number} must be an object")
        rows.append(value)
    return rows


def _schema_validator(root: Path) -> Draft202012Validator:
    path = root / "lab/compiler/schemas/control_translation.schema.json"
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read control translation schema: {exc}") from exc
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _validate_schema(
    validator: Draft202012Validator,
    value: dict[str, Any],
) -> None:
    errors = sorted(
        validator.iter_errors(value), key=lambda error: list(error.absolute_path)
    )
    if errors:
        detail = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValueError(f"control translation registry: {detail}")


def _decode_pointer_part(value: str) -> str:
    return value.replace("~1", "/").replace("~0", "~")


def resolve_mapping_pointer(mapping: dict[str, Any], pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise ValueError(f"mapping pointer must start with '/': {pointer}")
    current: Any = mapping
    for raw_part in pointer[1:].split("/"):
        part = _decode_pointer_part(raw_part)
        if isinstance(current, dict):
            if part not in current:
                raise ValueError(f"mapping pointer does not resolve: {pointer}")
            current = current[part]
        elif isinstance(current, list):
            if not part.isdigit() or int(part) >= len(current):
                raise ValueError(f"mapping pointer does not resolve: {pointer}")
            current = current[int(part)]
        else:
            raise ValueError(f"mapping pointer crosses a scalar value: {pointer}")
    return copy.deepcopy(current)


def load_translation_catalog(
    root: Path = REPO_ROOT,
    field_policies: dict[str, str] | None = None,
) -> TranslationCatalog:
    registry = _read_yaml(root / "lab/compiler/control_translations.yaml")
    _validate_schema(_schema_validator(root), registry)
    if registry["schema"] != TRANSLATION_REGISTRY_SCHEMA:
        raise ValueError("unsupported control translation registry schema")
    if registry["policy_version"] != TRANSLATION_POLICY_VERSION:
        raise ValueError("unsupported control translation policy version")

    curated_rows = _read_jsonl(
        root / "lab/second_brain/curated/mappings.jsonl"
    )
    curated = {row["id"]: row for row in curated_rows}
    if len(curated) != len(curated_rows):
        raise ValueError("curated mapping ids must be unique")
    mapping_hashes = {
        mapping_id: mapping_contract_hash(row)
        for mapping_id, row in curated.items()
    }
    mapping_concepts = {
        mapping_id: row["concept_id"] for mapping_id, row in curated.items()
    }

    records: dict[str, dict[str, Any]] = {}
    record_hashes: dict[str, str] = {}
    translation_ids: set[str] = set()
    for record in registry["translations"]:
        translation_id = record["translation_id"]
        mapping_id = record["mapping_id"]
        if translation_id in translation_ids:
            raise ValueError(f"duplicate translation id: {translation_id}")
        if mapping_id in records:
            raise ValueError(f"multiple active translations for mapping: {mapping_id}")
        translation_ids.add(translation_id)
        mapping = curated.get(mapping_id)
        if mapping is None:
            raise ValueError(f"translation references unknown mapping: {mapping_id}")
        if mapping.get("provider") is not None or mapping.get("model_version") is not None:
            raise ValueError(
                f"provider-specific mapping cannot enter the canonical score: {mapping_id}"
            )
        if record["concept_id"] != mapping["concept_id"]:
            raise ValueError(f"translation concept does not match mapping: {mapping_id}")
        if record["mapping_hash"] != mapping_hashes[mapping_id]:
            raise ValueError(f"translation mapping hash is stale: {mapping_id}")
        if record["loss"]["source_mapping"] != mapping["loss"]:
            raise ValueError(f"translation loss does not match mapping: {mapping_id}")
        required = set(record["preconditions"]["required_profile_labels"])
        excluded = set(record["preconditions"]["excluded_profile_labels"])
        if required & excluded:
            raise ValueError(
                f"translation profile preconditions overlap: {translation_id}"
            )
        operation_ids: set[str] = set()
        for operation in record["operations"]:
            operation_id = operation["operation_id"]
            if operation_id in operation_ids:
                raise ValueError(
                    f"duplicate operation id in {translation_id}: {operation_id}"
                )
            operation_ids.add(operation_id)
            if field_policies is not None:
                operator = field_policies.get(operation["target_path"])
                if operator is None:
                    raise ValueError(
                        f"translation targets undeclared canonical field: "
                        f"{operation['target_path']}"
                    )
                if operator != operation["expected_merge_operator"]:
                    raise ValueError(
                        f"translation operator does not match canonical policy: "
                        f"{operation['target_path']}"
                    )
            source = operation["source"]
            if source["kind"] == "mapping_pointer":
                resolve_mapping_pointer(mapping, source["pointer"])
        records[mapping_id] = copy.deepcopy(record)
        record_hashes[translation_id] = sha256_value(record)

    return TranslationCatalog(
        records_by_mapping=records,
        record_hashes=record_hashes,
        mapping_hashes=mapping_hashes,
        mapping_concepts=mapping_concepts,
    )


def _precondition_failure(
    record: dict[str, Any],
    selected_labels: set[str],
    required_layers: set[str],
) -> str | None:
    preconditions = record["preconditions"]
    missing_labels = sorted(
        set(preconditions["required_profile_labels"]) - selected_labels
    )
    if missing_labels:
        return "missing required profile labels: " + ", ".join(missing_labels)
    excluded = sorted(
        set(preconditions["excluded_profile_labels"]) & selected_labels
    )
    if excluded:
        return "excluded profile labels are active: " + ", ".join(excluded)
    missing_layers = sorted(
        set(preconditions["required_layers"]) - required_layers
    )
    if missing_layers:
        return "missing required knowledge layers: " + ", ".join(missing_layers)
    return None


def translate_context_mappings(
    mappings: list[dict[str, Any]],
    *,
    selected_concept_ids: set[str],
    selected_labels: set[str],
    required_layers: set[str],
    catalog: TranslationCatalog,
) -> TranslationResult:
    """Return deterministic contributions and explicit dispositions for gated mappings."""
    contributions: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []
    dispositions: list[dict[str, Any]] = []
    verification_metrics: list[dict[str, Any]] = []
    seen_mapping_ids: set[str] = set()

    for mapping in sorted(mappings, key=lambda row: row["id"]):
        mapping_id = mapping["id"]
        concept_id = mapping["concept_id"]
        if mapping_id in seen_mapping_ids:
            raise ValueError(f"context mapping ids must be unique: {mapping_id}")
        seen_mapping_ids.add(mapping_id)
        if concept_id not in selected_concept_ids:
            raise ValueError(
                f"context mapping is not owned by a selected concept: {mapping_id}"
            )
        expected_hash = catalog.mapping_hashes.get(mapping_id)
        if expected_hash is None:
            raise ValueError(f"context references unknown curated mapping: {mapping_id}")
        actual_hash = mapping_contract_hash(mapping)
        if actual_hash != expected_hash:
            raise ValueError(f"context mapping differs from curated authority: {mapping_id}")
        if catalog.mapping_concepts[mapping_id] != concept_id:
            raise ValueError(f"context mapping concept mismatch: {mapping_id}")

        record = catalog.records_by_mapping.get(mapping_id)
        if record is None:
            dispositions.append(
                {
                    "mapping_id": mapping_id,
                    "concept_id": concept_id,
                    "status": "no_translation",
                    "translation_id": None,
                    "reason": "No active canonical control translation is registered.",
                    "changed_paths": [],
                }
            )
            continue
        failure = _precondition_failure(
            record, selected_labels, required_layers
        )
        if failure:
            dispositions.append(
                {
                    "mapping_id": mapping_id,
                    "concept_id": concept_id,
                    "status": "precondition_failed",
                    "translation_id": record["translation_id"],
                    "reason": failure,
                    "changed_paths": [],
                }
            )
            continue

        changed_paths: list[str] = []
        operation_outputs: list[dict[str, Any]] = []
        for operation in sorted(
            record["operations"], key=lambda row: row["operation_id"]
        ):
            source = operation["source"]
            value = (
                resolve_mapping_pointer(mapping, source["pointer"])
                if source["kind"] == "mapping_pointer"
                else copy.deepcopy(source["value"])
            )
            refs = sorted(
                {
                    record["translation_id"],
                    mapping_id,
                    concept_id,
                    *mapping["sources"],
                }
            )
            contribution = {
                "operation_id": operation["operation_id"],
                "path": operation["target_path"],
                "value": value,
                "priority": record["priority"],
                "expected_merge_operator": operation["expected_merge_operator"],
                "source_refs": refs,
            }
            contributions.append(contribution)
            operation_outputs.append(copy.deepcopy(contribution))
            changed_paths.append(operation["target_path"])

        metric_ids: list[str] = []
        for metric in record["verification"]:
            normalized = {
                **copy.deepcopy(metric),
                "source_translation": record["translation_id"],
            }
            verification_metrics.append(normalized)
            metric_ids.append(metric["metric_id"])
        applied.append(
            {
                "translation_id": record["translation_id"],
                "translation_hash": catalog.record_hashes[record["translation_id"]],
                "mapping_id": mapping_id,
                "mapping_hash": actual_hash,
                "concept_id": concept_id,
                "operations": operation_outputs,
                "loss": copy.deepcopy(record["loss"]),
                "limitations": list(record["limitations"]),
                "conflict_strategy": record["conflict_strategy"],
                "verification_metric_ids": sorted(metric_ids),
            }
        )
        dispositions.append(
            {
                "mapping_id": mapping_id,
                "concept_id": concept_id,
                "status": "applied",
                "translation_id": record["translation_id"],
                "reason": "The active translation passed its declared preconditions.",
                "changed_paths": sorted(set(changed_paths)),
            }
        )

    return TranslationResult(
        contributions=tuple(contributions),
        applied=tuple(applied),
        dispositions=tuple(dispositions),
        verification_metrics=tuple(verification_metrics),
    )
