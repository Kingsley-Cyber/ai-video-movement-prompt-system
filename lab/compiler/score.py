"""Resolve normalized CPCS intent and context into one universal canonical score."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from lab.second_brain.src.validate import validate_instance as validate_second_brain

from . import COMPILER_KERNEL_VERSION
from .constraints import LockRegistry
from .merge import MERGE_POLICY_VERSION, apply_merge
from .profiles import (
    KERNEL_PROFILE_ID,
    REPO_ROOT,
    ProfileCatalog,
    adapt_component_profile,
    flatten_defaults,
    load_profile_catalog,
    select_domain_profiles,
)
from .provenance import (
    canonical_json_bytes,
    field_candidate,
    field_provenance,
    sha256_value,
)
from .translations import (
    TRANSLATION_POLICY_VERSION,
    load_translation_catalog,
    translate_context_mappings,
)

SCORE_REQUEST_SCHEMA = "cpcs.score_request/1.0"
UNIVERSAL_SCORE_SCHEMA = "cpcs.universal_score/1.0"
OVERLAY_SCOPE_ORDER = {
    "user_defaults": 300,
    "project_profile": 400,
    "scene_override": 500,
    "shot_override": 600,
    "event_lock": 700,
    "explicit_user_correction": 800,
}
SCORE_SECTIONS = {
    "project": {},
    "entities": [],
    "scenes": [],
    "shots": [],
    "beats": [],
    "actions": [],
    "performance": {},
    "motion": {},
    "interactions": [],
    "camera": {},
    "editing": {},
    "audio": {},
    "marketing": {},
    "style": {},
    "continuity": {},
}


def _schema_path(name: str, root: Path) -> Path:
    return root / "lab/compiler/schemas" / {
        "control_translation": "control_translation.schema.json",
        "profile": "profile.schema.json",
        "score_request": "score_request.schema.json",
        "universal_score": "universal_score.schema.json",
    }[name]


def _load_schema(name: str, root: Path) -> dict[str, Any]:
    return json.loads(_schema_path(name, root).read_text(encoding="utf-8"))


def validate_compiler_instance(
    name: str, value: Any, root: Path = REPO_ROOT
) -> None:
    validator = Draft202012Validator(_load_schema(name, root))
    errors = sorted(
        validator.iter_errors(value), key=lambda error: list(error.absolute_path)
    )
    if errors:
        detail = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValueError(f"{name}: {detail}")


def validate_configuration(root: Path = REPO_ROOT) -> dict[str, int]:
    for name in ("control_translation", "profile", "score_request", "universal_score"):
        Draft202012Validator.check_schema(_load_schema(name, root))
    catalog = load_profile_catalog(root)
    translations = load_translation_catalog(root, catalog.field_policies)
    return {
        "schemas": 4,
        "universal_profiles": 1,
        "domain_profiles": len(catalog.domains),
        "component_profiles": len(catalog.components),
        "field_policies": len(catalog.field_policies),
        "control_translations": len(translations.records_by_mapping),
    }


def _intent_reference(intent: dict[str, Any]) -> str:
    digest = hashlib.sha256(canonical_json_bytes(intent)).hexdigest()[:16]
    return f"normalized-intent:{digest}"


def _selected_labels(intent: dict[str, Any]) -> list[str]:
    return [intent["profiles"]["primary"], *intent["profiles"]["secondary"]]


def make_score_request(
    intent_context: dict[str, Any],
    *,
    profile_selection: Iterable[str] | None = None,
    overlays: Iterable[dict[str, Any]] = (),
    conflict_resolutions: dict[str, Any] | None = None,
    assets: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Build the versioned request envelope for the public score resolver."""
    if not isinstance(intent_context, dict):
        raise ValueError("intent_context must be an object")
    intent = intent_context.get("normalized_intent")
    context = intent_context.get("context_bundle")
    if not isinstance(intent, dict) or not isinstance(context, dict):
        raise ValueError("intent_context must contain normalized_intent and context_bundle")
    selection = list(profile_selection) if profile_selection is not None else _selected_labels(intent)
    request = {
        "schema": SCORE_REQUEST_SCHEMA,
        "normalized_intent": copy.deepcopy(intent),
        "context_bundle": copy.deepcopy(context),
        "profile_selection": selection,
        "overlays": list(copy.deepcopy(list(overlays))),
        "conflict_resolutions": copy.deepcopy(conflict_resolutions or {}),
        "assets": list(copy.deepcopy(list(assets))),
    }
    validate_compiler_instance("score_request", request)
    return request


def _validate_input_contracts(request: dict[str, Any], root: Path) -> None:
    validate_compiler_instance("score_request", request, root)
    intent = request["normalized_intent"]
    context = request["context_bundle"]
    validate_second_brain("normalized_intent", intent, root)
    validate_second_brain("context_bundle", context, root)
    if set(request["profile_selection"]) != set(_selected_labels(intent)):
        raise ValueError(
            "profile_selection must contain exactly the normalized intent profile set"
        )
    if context["request"]["query"] != intent["routing"]["knowledge_query"]:
        raise ValueError("context bundle query does not match normalized intent routing")
    if context["request"]["intent"] != _intent_reference(intent):
        raise ValueError("context bundle intent reference does not match normalized intent")
    if context["request"]["domain"] != intent["intent"]["primary_domain"]:
        raise ValueError("context bundle domain does not match normalized intent")
    if context["request"]["provider"] is not None or context["request"]["model"] is not None:
        raise ValueError("universal score resolution requires provider-neutral context")
    if context["policy_versions"]["query"] != "cpcs-query/1.2":
        raise ValueError("universal score requires the gated cpcs-query/1.2 path")
    overlay_ids = [row["overlay_id"] for row in request["overlays"]]
    if len(overlay_ids) != len(set(overlay_ids)):
        raise ValueError("overlay_id values must be unique")
    asset_ids = [row["asset_id"] for row in request["assets"]]
    if len(asset_ids) != len(set(asset_ids)):
        raise ValueError("asset_id values must be unique")


def _normalized_request_hash_input(request: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(request)
    normalized["profile_selection"] = sorted(normalized["profile_selection"])
    normalized["overlays"] = sorted(
        normalized["overlays"],
        key=lambda row: (
            OVERLAY_SCOPE_ORDER[row["scope"]],
            row["priority"],
            row["overlay_id"],
        ),
    )
    normalized["assets"] = sorted(
        normalized["assets"], key=lambda row: row["asset_id"]
    )
    return normalized


def _set_path(target: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    if len(parts) == 1:
        target[parts[0]] = copy.deepcopy(value)
        return
    node = target[parts[0]]
    if not isinstance(node, dict):
        raise ValueError(f"canonical section {parts[0]} cannot contain nested field {path}")
    for part in parts[1:-1]:
        child = node.setdefault(part, {})
        if not isinstance(child, dict):
            raise ValueError(f"canonical path collides with non-object value: {path}")
        node = child
    node[parts[-1]] = copy.deepcopy(value)


def _control_id(path: str) -> str:
    return "control_" + hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]


def _generated_conflict_id(path: str) -> str:
    return "conflict_field_" + hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]


def _canonical_equal(left: Any, right: Any) -> bool:
    return canonical_json_bytes(left) == canonical_json_bytes(right)


def resolve_score(
    request: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Resolve one provider-neutral score without writing repository authority."""
    _validate_input_contracts(request, root)
    catalog = load_profile_catalog(root)
    labels = sorted(set(request["profile_selection"]))
    domain_profiles = select_domain_profiles(labels, catalog)
    selected_profile_ids = {profile["profile_id"] for profile in domain_profiles}

    values: dict[str, Any] = {}
    winners: dict[str, str | None] = {}
    candidates: dict[str, list[dict[str, Any]]] = {}
    reasons: dict[str, str] = {}
    conflicted_paths: dict[str, str] = {}
    locks = LockRegistry()
    unresolved: list[dict[str, Any]] = []
    applied_constraints: list[dict[str, Any]] = []

    active_conflicts: dict[str, dict[str, Any]] = {}
    for profile in domain_profiles:
        for conflict in profile["conflicts"]:
            if set(conflict["profiles"]) <= selected_profile_ids:
                if conflict["field"] in active_conflicts:
                    raise ValueError(
                        f"multiple active profile conflicts own {conflict['field']}"
                    )
                active_conflicts[conflict["field"]] = conflict

    def apply_value(
        path: str,
        value: Any,
        *,
        source: str,
        scope: str,
        priority: int,
        source_refs: list[str],
    ) -> None:
        operator = catalog.field_policies[path]
        candidate = field_candidate(
            source=source,
            scope=scope,
            priority=priority,
            value=value,
            source_refs=source_refs,
        )
        candidates.setdefault(path, []).append(candidate)
        lock_conflict = locks.conflict(path, value, source)
        if lock_conflict:
            unresolved.append(lock_conflict)
            reasons[path] = "hard_lock_retained"
            return
        if path in conflicted_paths:
            return
        outcome = apply_merge(operator, values.get(path), value)
        if outcome.conflict:
            conflict = active_conflicts.get(path)
            conflict_id = (
                conflict["conflict_id"] if conflict else _generated_conflict_id(path)
            )
            conflicted_paths[path] = conflict_id
            values.pop(path, None)
            winners[path] = None
            reasons[path] = "requires_user_choice"
            return
        values[path] = outcome.value
        winners[path] = source
        reasons[path] = (
            "single_candidate" if len(candidates[path]) == 1 else "typed_merge"
        )

    def apply_constraints(
        profile_id: str,
        rows: list[dict[str, Any]],
        *,
        scope: str,
        priority: int,
    ) -> None:
        for row in rows:
            normalized = {
                "constraint_id": row["constraint_id"],
                "kind": row["kind"],
                "text": row["text"],
                "path": row.get("path"),
                "value": copy.deepcopy(row.get("value")),
                "source_refs": sorted(set(row.get("source_refs", [profile_id]))),
            }
            applied_constraints.append(normalized)
            path = normalized["path"]
            if path is None:
                continue
            apply_value(
                path,
                normalized["value"],
                source=row["constraint_id"],
                scope=scope,
                priority=priority,
                source_refs=normalized["source_refs"],
            )
            if row["kind"] in {"hard_lock", "invariant", "safety"}:
                if path not in values:
                    raise ValueError(f"constraint cannot lock unresolved path: {path}")
                locks.lock(path, values[path], row["constraint_id"])

    kernel_defaults = flatten_defaults(
        catalog.kernel["defaults"], catalog.field_policies
    )
    for path, value in sorted(kernel_defaults.items()):
        apply_value(
            path,
            value,
            source=KERNEL_PROFILE_ID,
            scope="universal_defaults",
            priority=0,
            source_refs=[KERNEL_PROFILE_ID],
        )
    apply_constraints(
        KERNEL_PROFILE_ID,
        catalog.kernel["constraints"],
        scope="universal_defaults",
        priority=0,
    )

    component_owners: dict[str, set[str]] = {}
    for profile in domain_profiles:
        for component_id in profile["component_profiles"]:
            component_owners.setdefault(component_id, set()).add(profile["profile_id"])
    component_constraints: dict[str, list[dict[str, Any]]] = {}
    component_metrics: dict[str, list[dict[str, Any]]] = {}
    for index, component_id in enumerate(sorted(component_owners), 1):
        component = catalog.components[component_id]
        adapted, constraints, metrics = adapt_component_profile(
            component_id, component, catalog.field_policies
        )
        component_constraints[component_id] = constraints
        component_metrics[component_id] = metrics
        for path, value in sorted(adapted.items()):
            apply_value(
                path,
                value,
                source=component_id,
                scope="component_profiles",
                priority=10 + index,
                source_refs=[component_id],
            )
        apply_constraints(
            component_id,
            constraints,
            scope="component_profiles",
            priority=10 + index,
        )

    for profile in domain_profiles:
        priority = 100 + profile["priority"]
        defaults = flatten_defaults(profile["defaults"], catalog.field_policies)
        for path, value in sorted(defaults.items()):
            apply_value(
                path,
                value,
                source=profile["profile_id"],
                scope="domain_profiles",
                priority=priority,
                source_refs=[profile["profile_id"]],
            )
        for contribution in sorted(
            profile["control_contributions"], key=lambda row: row["control_id"]
        ):
            apply_value(
                contribution["path"],
                contribution["value"],
                source=contribution["control_id"],
                scope="domain_profiles",
                priority=priority,
                source_refs=contribution["source_refs"],
            )
        apply_constraints(
            profile["profile_id"],
            profile["constraints"],
            scope="domain_profiles",
            priority=priority,
        )

    required_layers = sorted(
        {
            *request["normalized_intent"]["routing"]["required_layers"],
            *(layer for profile in domain_profiles for layer in profile["required_layers"]),
        }
    )
    translation_catalog = load_translation_catalog(root, catalog.field_policies)
    translation_result = translate_context_mappings(
        request["context_bundle"]["mappings"],
        selected_concept_ids={
            row["id"] for row in request["context_bundle"]["selected_concepts"]
        },
        selected_labels=set(labels),
        required_layers=set(required_layers),
        catalog=translation_catalog,
    )
    for contribution in sorted(
        translation_result.contributions,
        key=lambda row: (row["priority"], row["operation_id"]),
    ):
        apply_value(
            contribution["path"],
            contribution["value"],
            source=contribution["operation_id"],
            scope="research_translation",
            priority=200 + contribution["priority"],
            source_refs=contribution["source_refs"],
        )

    overlays = sorted(
        request["overlays"],
        key=lambda row: (
            OVERLAY_SCOPE_ORDER[row["scope"]],
            row["priority"],
            row["overlay_id"],
        ),
    )
    for overlay in overlays:
        priority = OVERLAY_SCOPE_ORDER[overlay["scope"]] + overlay["priority"]
        overlay_values = flatten_defaults(overlay["values"], catalog.field_policies)
        unknown_locks = set(overlay["locks"]) - set(overlay_values)
        if unknown_locks:
            raise ValueError(
                f"{overlay['overlay_id']} locks fields absent from its values: "
                f"{sorted(unknown_locks)}"
            )
        for path, value in sorted(overlay_values.items()):
            apply_value(
                path,
                value,
                source=overlay["overlay_id"],
                scope=overlay["scope"],
                priority=priority,
                source_refs=[overlay["overlay_id"]],
            )
        for path in sorted(overlay["locks"]):
            if path not in values:
                raise ValueError(f"{overlay['overlay_id']} cannot lock unresolved field {path}")
            locks.lock(path, values[path], overlay["overlay_id"])

    conflict_outputs: list[dict[str, Any]] = []
    used_resolutions: set[str] = set()
    for path, conflict_id in sorted(conflicted_paths.items()):
        definition = active_conflicts.get(path)
        options = (
            list(definition["options"])
            if definition
            else [candidate["value"] for candidate in candidates[path]]
        )
        unique_options: list[Any] = []
        for option in options:
            if not any(_canonical_equal(option, existing) for existing in unique_options):
                unique_options.append(option)
        selected = request["conflict_resolutions"].get(conflict_id)
        if conflict_id in request["conflict_resolutions"]:
            if not any(_canonical_equal(selected, option) for option in unique_options):
                raise ValueError(
                    f"conflict resolution {conflict_id} must select one declared option"
                )
            used_resolutions.add(conflict_id)
            values[path] = copy.deepcopy(selected)
            winners[path] = "explicit_conflict_resolution"
            reasons[path] = "explicit_conflict_resolution"
            candidates[path].append(
                field_candidate(
                    source="explicit_conflict_resolution",
                    scope="explicit_user_correction",
                    priority=900,
                    value=selected,
                    source_refs=[conflict_id],
                )
            )
        else:
            unresolved.append(
                {
                    "code": "profile_conflict",
                    "id": conflict_id,
                    "path": path,
                    "message": (
                        definition["reason"]
                        if definition
                        else f"Field {path} has incompatible candidates."
                    ),
                    "options": unique_options,
                }
            )
        if definition:
            conflict_outputs.append(
                {
                    "conflict_id": conflict_id,
                    "profiles": list(definition["profiles"]),
                    "field": path,
                    "options": unique_options,
                    "outcome": (
                        "resolved_by_precedence"
                        if selected is not None
                        else definition["outcome"]
                    ),
                    "selected": copy.deepcopy(selected),
                    "reason": definition["reason"],
                }
            )
    unused_resolutions = set(request["conflict_resolutions"]) - used_resolutions
    if unused_resolutions:
        raise ValueError(
            "conflict_resolutions reference inactive conflicts: "
            + ", ".join(sorted(unused_resolutions))
        )

    supplied_roles = {asset["role"] for asset in request["assets"]}
    for missing in request["normalized_intent"]["requirements"]["missing_inputs"]:
        if missing not in supplied_roles:
            unresolved.append(
                {
                    "code": "missing_input",
                    "id": f"input:{missing}",
                    "path": None,
                    "message": f"Required input is missing: {missing}.",
                    "options": [missing],
                }
            )

    applied_profiles = [
        {
            "profile_id": KERNEL_PROFILE_ID,
            "profile_kind": "universal",
            "priority": 0,
            "content_hash": catalog.profile_hashes[KERNEL_PROFILE_ID],
            "component_of": [],
        }
    ]
    for component_id in sorted(component_owners):
        applied_profiles.append(
            {
                "profile_id": component_id,
                "profile_kind": "component",
                "priority": 10,
                "content_hash": catalog.profile_hashes[component_id],
                "component_of": sorted(component_owners[component_id]),
            }
        )
    for profile in domain_profiles:
        applied_profiles.append(
            {
                "profile_id": profile["profile_id"],
                "profile_kind": "domain",
                "priority": profile["priority"],
                "content_hash": catalog.profile_hashes[profile["profile_id"]],
                "component_of": [],
            }
        )

    field_lineage = {
        path: field_provenance(
            value=copy.deepcopy(values.get(path)),
            winner=winners.get(path),
            candidates=rows,
            operator=catalog.field_policies[path],
            reason=reasons.get(path, "unresolved"),
        )
        for path, rows in sorted(candidates.items())
    }
    resolved_sections = copy.deepcopy(SCORE_SECTIONS)
    for path, value in sorted(values.items()):
        _set_path(resolved_sections, path, value)

    metrics: dict[str, dict[str, Any]] = {}

    def add_metrics(
        rows: Iterable[dict[str, Any]],
        *,
        source_profile: str | None = None,
        source_translation: str | None = None,
    ) -> None:
        if (source_profile is None) == (source_translation is None):
            raise ValueError("verification metric requires exactly one source")
        for row in rows:
            normalized = copy.deepcopy(row)
            if source_profile is not None:
                normalized["source_profile"] = source_profile
            if source_translation is not None:
                normalized["source_translation"] = source_translation
            existing = metrics.get(row["metric_id"])
            if existing and existing != normalized:
                raise ValueError(f"verification metric id collision: {row['metric_id']}")
            metrics[row["metric_id"]] = normalized

    add_metrics(catalog.kernel["verification_metrics"], source_profile=KERNEL_PROFILE_ID)
    for component_id in sorted(component_metrics):
        add_metrics(component_metrics[component_id], source_profile=component_id)
    for profile in domain_profiles:
        add_metrics(profile["verification_metrics"], source_profile=profile["profile_id"])
    for source_metric in translation_result.verification_metrics:
        metric = copy.deepcopy(source_metric)
        source_translation = metric.pop("source_translation")
        add_metrics([metric], source_translation=source_translation)

    controls = [
        {
            "control_id": _control_id(path),
            "path": path,
            "value": copy.deepcopy(value),
            "authority": "canonical_score",
            "provenance_ref": f"provenance.fields.{path}",
        }
        for path, value in sorted(values.items())
    ]
    warnings = []
    context = request["context_bundle"]
    if context["knowledge_gap"]["should_retrieve"]:
        warnings.append(
            {
                "code": "knowledge_gap_open",
                "message": "The context bundle reports material uncovered knowledge terms.",
            }
        )
    untranslated = [
        row
        for row in translation_result.dispositions
        if row["status"] == "no_translation"
    ]
    if untranslated:
        warnings.append(
            {
                "code": "untranslated_research_mapping",
                "message": (
                    f"{len(untranslated)} gated mapping(s) have no active canonical translation."
                ),
            }
        )
    precondition_failures = [
        row
        for row in translation_result.dispositions
        if row["status"] == "precondition_failed"
    ]
    if precondition_failures:
        warnings.append(
            {
                "code": "research_translation_precondition_failed",
                "message": (
                    f"{len(precondition_failures)} canonical translation(s) were not applicable."
                ),
            }
        )
    preferred_workflows = sorted(
        {
            workflow
            for profile in domain_profiles
            for workflow in profile["preferred_workflows"]
        }
    )
    normalized_request = _normalized_request_hash_input(request)
    profile_hashes = {
        row["profile_id"]: row["content_hash"] for row in applied_profiles
    }
    score: dict[str, Any] = {
        "schema_version": UNIVERSAL_SCORE_SCHEMA,
        "score_id": "score_" + "0" * 32,
        "score_status": "needs_input" if unresolved else "ready",
        "normalized_intent": copy.deepcopy(request["normalized_intent"]),
        "profile_resolution": {
            "kernel_profile": KERNEL_PROFILE_ID,
            "requested_labels": labels,
            "applied_profiles": applied_profiles,
            "required_layers": required_layers,
            "preferred_workflows": preferred_workflows,
            "merge_policy": MERGE_POLICY_VERSION,
            "conflicts": conflict_outputs,
        },
        "research_translation": {
            "policy_version": TRANSLATION_POLICY_VERSION,
            "applied": list(translation_result.applied),
            "dispositions": list(translation_result.dispositions),
        },
        **resolved_sections,
        "assets": sorted(
            copy.deepcopy(request["assets"]), key=lambda row: row["asset_id"]
        ),
        "constraints": {
            "hard": request["normalized_intent"]["requirements"]["hard_constraints"],
            "soft": request["normalized_intent"]["requirements"]["soft_preferences"],
            "continuity_locks": request["normalized_intent"]["requirements"]["continuity_locks"],
            "applied": sorted(
                applied_constraints, key=lambda row: row["constraint_id"]
            ),
            "locked_paths": locks.paths(),
        },
        "provider_neutral_controls": controls,
        "provider_realization": {
            "status": "unassigned",
            "capability_dispositions": [],
        },
        "verification_requirements": [metrics[key] for key in sorted(metrics)],
        "provenance": {
            "resolver_version": COMPILER_KERNEL_VERSION,
            "request_hash": sha256_value(normalized_request),
            "intent_hash": sha256_value(request["normalized_intent"]),
            "context_hash": sha256_value(request["context_bundle"]),
            "profile_hashes": profile_hashes,
            "concept_ids": sorted(
                row["id"] for row in context["selected_concepts"]
            ),
            "fields": field_lineage,
        },
        "unresolved": sorted(
            unresolved,
            key=lambda row: (row["code"], row["id"], str(row["path"])),
        ),
        "warnings": sorted(warnings, key=lambda row: row["code"]),
    }
    score_without_id = {key: value for key, value in score.items() if key != "score_id"}
    score["score_id"] = "score_" + hashlib.sha256(
        canonical_json_bytes(score_without_id)
    ).hexdigest()[:32]
    validate_compiler_instance("universal_score", score, root)
    return score


def canonical_score_bytes(score: dict[str, Any]) -> bytes:
    return canonical_json_bytes(score)


def _read_request(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read score request: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("score request must be an object")
    return value


def _read_json_value(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label}: {exc}") from exc


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    resolve = sub.add_parser("resolve")
    resolve.add_argument("request", type=Path)
    resolve_context = sub.add_parser("resolve-context")
    resolve_context.add_argument("intent_context", type=Path)
    resolve_context.add_argument("--assets", type=Path)
    resolve_context.add_argument("--overlays", type=Path)
    resolve_context.add_argument("--conflict-resolutions", type=Path)
    resolve_context.add_argument("--profile-label", action="append")
    args = parser.parse_args(argv)
    if args.command == "validate":
        print(json.dumps(validate_configuration(), sort_keys=True))
        return
    if args.command == "resolve":
        score = resolve_score(_read_request(args.request))
    else:
        intent_context = _read_json_value(args.intent_context, "intent context")
        assets = _read_json_value(args.assets, "assets") if args.assets else []
        overlays = _read_json_value(args.overlays, "overlays") if args.overlays else []
        resolutions = (
            _read_json_value(args.conflict_resolutions, "conflict resolutions")
            if args.conflict_resolutions
            else {}
        )
        if not isinstance(assets, list):
            raise ValueError("assets file must contain a list")
        if not isinstance(overlays, list):
            raise ValueError("overlays file must contain a list")
        if not isinstance(resolutions, dict):
            raise ValueError("conflict resolutions file must contain an object")
        score = resolve_score(
            make_score_request(
                intent_context,
                profile_selection=args.profile_label,
                assets=assets,
                overlays=overlays,
                conflict_resolutions=resolutions,
            )
        )
    print(json.dumps(score, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
