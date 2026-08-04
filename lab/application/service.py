"""One versioned application service for every CPCS client surface."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator

from lab.compiler.build import compile_build
from lab.compiler.provenance import sha256_bytes
from lab.compiler.score import make_score_request, resolve_score
from lab.second_brain.src.context import build_context_bundle
from lab.second_brain.src.curate import promote_distillation_bundle
from lab.second_brain.src.distill import run_distillation, status as distillation_status
from lab.second_brain.src.intent import build_intent_context, normalize_intent
from lab.second_brain.src.query import default_request, reason
from lab.second_brain.src.record import append_experiment_receipt
from lab.second_brain.src.reflect import rebuild
from lab.second_brain.src.source_extract import (
    extract_folder,
    extract_retrieved_passages,
)
from lab.second_brain.src.validate import (
    REPO_ROOT,
    canonical_json_bytes,
    read_jsonl,
    sha256_value,
)

from .contracts import validate_application_instance

APPLICATION_POLICY = "cpcs-application/1.0"
AUTHORIZATION_POLICY = "cpcs-local-authority/1.0"
REQUEST_SCHEMA = "cpcs.application_request/1.0"
RESPONSE_SCHEMA = "cpcs.application_response/1.0"
AUTHORIZATION_SCHEMA = "cpcs.explicit_authorization/1.0"

ROLE_LEVEL = {"chat": 0, "operator": 1, "curator": 2}
Handler = Callable[[dict[str, Any], Path], dict[str, Any]]


@dataclass(frozen=True)
class OperationSpec:
    name: str
    description: str
    required_role: str
    mutation_scope: str | None
    input_schema: dict[str, Any]
    handler: Handler


def _object_schema(
    *,
    required: tuple[str, ...] = (),
    properties: dict[str, Any] | None = None,
    additional: bool = False,
) -> dict[str, Any]:
    return {
        "type": "object",
        "required": list(required),
        "properties": properties or {},
        "additionalProperties": additional,
    }


STRING = {"type": "string", "minLength": 1}
STRING_LIST = {"type": "array", "items": STRING, "uniqueItems": True}


def _status(_: dict[str, Any], root: Path) -> dict[str, Any]:
    sb = root / "lab" / "second_brain"
    coverage = json.loads((sb / "derived" / "coverage.json").read_text(encoding="utf-8"))
    return {
        "schema": "cpcs.status/1.0",
        "service_version": APPLICATION_POLICY,
        "release_authority": "local_working_not_production_qualified",
        "stores": {
            "concepts": len(read_jsonl(root / "lab" / "concepts.jsonl")),
            "curated_edges": len(read_jsonl(sb / "curated" / "edges.jsonl")),
            "immutable_runs": len(read_jsonl(sb / "immutable" / "runs.jsonl")),
            "learned_edges": coverage["learned_edges"],
        },
        "distillation": distillation_status(root),
        "operations": {
            "available": [row["name"] for row in list_operations("chat")],
            "restricted_count": len(OPERATIONS) - len(list_operations("chat")),
        },
        "authority_boundary": {
            "chat": "read_only",
            "operator": "staging_and_derived_only",
            "curator": "explicit_request_bound_authorization_required",
            "security_limit": "process_role_is_a_local_policy_gate_not_authenticated_identity",
        },
    }


def _intent_normalize(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return normalize_intent(
        arguments["text"],
        user_constraints=arguments.get("user_constraints", []),
        profile_overrides=arguments.get("profile_overrides", []),
        root=root,
    )


def _intent_context(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return build_intent_context(
        arguments["text"],
        token_budget=arguments.get("token_budget", 12_000),
        user_constraints=arguments.get("user_constraints", []),
        profile_overrides=arguments.get("profile_overrides", []),
        minimum_status=arguments.get("minimum_status", "ingested"),
        target_format=arguments.get("target_format", "hybrid"),
        root=root,
    )


def _context_get(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return build_context_bundle(
        arguments["query"],
        token_budget=arguments.get("token_budget", 12_000),
        provider=arguments.get("provider"),
        model=arguments.get("model"),
        minimum_status=arguments.get("minimum_status", "ingested"),
        include_external_evidence=arguments.get("include_external_evidence", True),
        external_evidence=arguments.get("external_evidence"),
        domain=arguments.get("domain"),
        target_format=arguments.get("target_format", "hybrid"),
        required_layers=arguments.get("required_layers", []),
        excluded_layers=arguments.get("excluded_layers", []),
        intent=arguments.get("intent"),
        as_of=arguments.get("as_of"),
        validity_mode=arguments.get("validity_mode", "current"),
        root=root,
    )


def _reason(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    sources = {key for key in ("request", "goal") if key in arguments}
    if len(sources) != 1:
        raise ValueError("reason requires exactly one of request or goal")
    if "request" in arguments:
        if set(arguments) != {"request"}:
            raise ValueError("a complete reasoning request cannot be mixed with goal fields")
        request = copy.deepcopy(arguments["request"])
    else:
        request = default_request(
            arguments["goal"],
            domain=arguments.get("domain"),
            target_format=arguments.get("target_format", "hybrid"),
            provider=arguments.get("provider"),
            model_version=arguments.get("model_version"),
            maximum_depth=arguments.get("maximum_depth", 5),
            minimum_status=arguments.get("minimum_status", "partial"),
            include_unproven=arguments.get("include_unproven", False),
            required_layers=arguments.get("required_layers", []),
            excluded_layers=arguments.get("excluded_layers", []),
            deterministic_seed=arguments.get("deterministic_seed", 7),
            as_of=arguments.get("as_of"),
            validity_mode=arguments.get("validity_mode", "current"),
        )
    return reason(request, root)


def _score_build(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    sources = {
        key for key in ("score_request", "intent_context", "text") if key in arguments
    }
    if len(sources) != 1:
        raise ValueError(
            "score build requires exactly one of score_request, intent_context, or text"
        )
    if "score_request" in arguments:
        if set(arguments) != {"score_request"}:
            raise ValueError("a complete score_request cannot be mixed with facade options")
        score_request = copy.deepcopy(arguments["score_request"])
        intent_context = {
            "normalized_intent": copy.deepcopy(score_request["normalized_intent"]),
            "context_bundle": copy.deepcopy(score_request["context_bundle"]),
        }
    else:
        intent_context = copy.deepcopy(arguments.get("intent_context"))
        if intent_context is None:
            intent_context = build_intent_context(
                arguments["text"],
                token_budget=arguments.get("token_budget", 12_000),
                user_constraints=arguments.get("user_constraints", []),
                profile_overrides=arguments.get("profile_overrides", []),
                minimum_status=arguments.get("minimum_status", "ingested"),
                target_format=arguments.get("target_format", "hybrid"),
                root=root,
            )
        score_request = make_score_request(
            intent_context,
            profile_selection=arguments.get("profile_selection"),
            overlays=arguments.get("overlays", []),
            conflict_resolutions=arguments.get("conflict_resolutions", {}),
            assets=arguments.get("assets", []),
        )
    score = resolve_score(score_request, root)
    return {**intent_context, "score": score}


def _build_compile(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    artifacts = compile_build(copy.deepcopy(arguments["request"]), root)
    encoded = {
        name: {
            "sha256": sha256_bytes(content),
            "media_type": (
                "application/json"
                if name.endswith(".json")
                else "text/plain; charset=utf-8"
            ),
            "content": content.decode("utf-8"),
        }
        for name, content in sorted(artifacts.items())
    }
    manifest = json.loads(artifacts["build_manifest.json"])
    return {
        "schema": "cpcs.inline_build/1.0",
        "build_id": manifest["build_id"],
        "build_hash": manifest["build_hash"],
        "artifacts": encoded,
    }


def _distill_prepare(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    kind = arguments["source_kind"]
    if kind == "authorized_folder":
        required = {"folder", "research_goal", "rights_basis"}
        if not required <= set(arguments) or "retrieved_passages" in arguments:
            raise ValueError(
                "authorized_folder requires folder, research_goal, and rights_basis only"
            )
        return extract_folder(
            Path(arguments["folder"]),
            research_goal=arguments["research_goal"],
            rights_basis=arguments["rights_basis"],
            semantic_response=arguments.get("semantic_response"),
            configuration=arguments.get("configuration"),
            root=root,
        )
    if kind == "polymath_passages":
        if "retrieved_passages" not in arguments or any(
            key in arguments for key in ("folder", "research_goal", "rights_basis")
        ):
            raise ValueError(
                "polymath_passages requires retrieved_passages and no folder fields"
            )
        return extract_retrieved_passages(
            arguments["retrieved_passages"],
            semantic_response=arguments.get("semantic_response"),
            configuration=arguments.get("configuration"),
            root=root,
        )
    raise ValueError(f"unsupported source_kind: {kind}")


def _distill_run(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return run_distillation(copy.deepcopy(arguments["batch"]), root)


def _curate_review(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    run_id = arguments["run_id"]
    sb = root / "lab" / "second_brain"
    matches = [
        row
        for row in read_jsonl(sb / "staging" / "distillation_runs.jsonl")
        if row["id"] == run_id
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one distillation run {run_id}, found {len(matches)}")
    run = matches[0]
    proposal_ids = set(run["proposal_ids"])
    proposals = [
        row
        for row in read_jsonl(sb / "staging" / "proposals.jsonl")
        if row["proposal_id"] in proposal_ids
    ]
    return {
        "schema": "cpcs.curation_review/1.0",
        "run": run,
        "proposals": sorted(proposals, key=lambda row: row["proposal_id"]),
        "requirements": {
            "durable_id_for_each_proposal": True,
            "human_review_required": True,
            "explicit_authorization_required_for_promotion": True,
        },
    }


def _curate_promote(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return promote_distillation_bundle(
        arguments["run_id"],
        copy.deepcopy(arguments["durable_ids"]),
        arguments["promoted_by"],
        copy.deepcopy(arguments["review"]),
        root,
    )


def _record_render(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return append_experiment_receipt(copy.deepcopy(arguments["receipt"]), root)


def _reflect_rebuild(_: dict[str, Any], root: Path) -> dict[str, Any]:
    return {"schema": "cpcs.reflection_rebuild/1.0", "outputs": rebuild(root)}


COMMON_INTENT_PROPERTIES = {
    "text": STRING,
    "user_constraints": STRING_LIST,
    "profile_overrides": STRING_LIST,
}
CONTEXT_PROPERTIES = {
    "token_budget": {"type": "integer", "minimum": 1},
    "minimum_status": {"enum": ["ingested", "partial", "proven"]},
    "target_format": {"enum": ["prose", "yaml", "json", "xml", "hybrid"]},
}


OPERATIONS: dict[str, OperationSpec] = {}


def _register(
    name: str,
    description: str,
    role: str,
    mutation_scope: str | None,
    input_schema: dict[str, Any],
    handler: Handler,
) -> None:
    OPERATIONS[name] = OperationSpec(
        name, description, role, mutation_scope, input_schema, handler
    )


_register("cpcs.status", "Read CPCS runtime and authority status.", "chat", None, _object_schema(), _status)
_register(
    "cpcs.intent.normalize",
    "Normalize ordinary language into the provider-neutral intent contract.",
    "chat",
    None,
    _object_schema(required=("text",), properties=COMMON_INTENT_PROPERTIES),
    _intent_normalize,
)
_register(
    "cpcs.intent.context",
    "Normalize ordinary language and build its safe context bundle.",
    "chat",
    None,
    _object_schema(
        required=("text",),
        properties={**COMMON_INTENT_PROPERTIES, **CONTEXT_PROPERTIES},
    ),
    _intent_context,
)
_register(
    "cpcs.context.get",
    "Build a token-budgeted context bundle from safe retrieval.",
    "chat",
    None,
    _object_schema(
        required=("query",),
        properties={
            "query": STRING,
            **CONTEXT_PROPERTIES,
            "provider": {"type": ["string", "null"]},
            "model": {"type": ["string", "null"]},
            "domain": {"type": ["string", "null"]},
            "include_external_evidence": {"type": "boolean"},
            "external_evidence": {"type": "array", "items": {"type": "object"}},
            "required_layers": STRING_LIST,
            "excluded_layers": STRING_LIST,
            "intent": {"type": ["string", "null"]},
            "as_of": {"type": ["string", "null"]},
            "validity_mode": {"enum": ["current", "historical", "all_versions"]},
        },
    ),
    _context_get,
)
_register(
    "cpcs.reason",
    "Retrieve relevant concepts and typed traversal paths.",
    "chat",
    None,
    _object_schema(
        properties={
            "request": {"type": "object"},
            "goal": STRING,
            "domain": {"type": ["string", "null"]},
            "target_format": {"enum": ["prose", "yaml", "json", "xml", "hybrid"]},
            "provider": {"type": ["string", "null"]},
            "model_version": {"type": ["string", "null"]},
            "maximum_depth": {"type": "integer", "minimum": 0},
            "minimum_status": {"enum": ["ingested", "partial", "proven"]},
            "include_unproven": {"type": "boolean"},
            "required_layers": STRING_LIST,
            "excluded_layers": STRING_LIST,
            "deterministic_seed": {"type": "integer"},
            "as_of": {"type": ["string", "null"]},
            "validity_mode": {"enum": ["current", "historical", "all_versions"]},
        },
    ),
    _reason,
)
_register(
    "cpcs.score.build",
    "Resolve guided or advanced input through one canonical score kernel.",
    "chat",
    None,
    _object_schema(
        properties={
            **COMMON_INTENT_PROPERTIES,
            **CONTEXT_PROPERTIES,
            "intent_context": {"type": "object"},
            "score_request": {"type": "object"},
            "profile_selection": STRING_LIST,
            "overlays": {"type": "array", "items": {"type": "object"}},
            "conflict_resolutions": {"type": "object"},
            "assets": {"type": "array", "items": {"type": "object"}},
        },
    ),
    _score_build,
)
_register(
    "cpcs.build.compile",
    "Compile a ready canonical score into inline provider build artifacts without submission.",
    "chat",
    None,
    _object_schema(required=("request",), properties={"request": {"type": "object"}}),
    _build_compile,
)
_register(
    "cpcs.distill.prepare",
    "Prepare a governed candidate bundle from an authorized folder or Polymath passages.",
    "operator",
    None,
    _object_schema(
        required=("source_kind",),
        properties={
            "source_kind": {"enum": ["authorized_folder", "polymath_passages"]},
            "folder": STRING,
            "research_goal": STRING,
            "rights_basis": STRING,
            "retrieved_passages": {"type": "object"},
            "semantic_response": {"type": ["object", "null"]},
            "configuration": {"type": ["object", "null"]},
        },
    ),
    _distill_prepare,
)
_register(
    "cpcs.distill.run",
    "Run deterministic admission and append staging decisions only.",
    "operator",
    "staging",
    _object_schema(required=("batch",), properties={"batch": {"type": "object"}}),
    _distill_run,
)
_register(
    "cpcs.curate.review",
    "Read one distillation run and its explicit promotion requirements.",
    "operator",
    None,
    _object_schema(required=("run_id",), properties={"run_id": STRING}),
    _curate_review,
)
_register(
    "cpcs.curate.promote",
    "Promote a reviewed distillation bundle into curated authority.",
    "curator",
    "curated",
    _object_schema(
        required=("run_id", "durable_ids", "promoted_by", "review"),
        properties={
            "run_id": STRING,
            "durable_ids": {"type": "object", "additionalProperties": STRING},
            "promoted_by": STRING,
            "review": {"type": "object"},
        },
    ),
    _curate_promote,
)
_register(
    "cpcs.record.render",
    "Append one exact, verified experiment receipt to immutable evidence.",
    "curator",
    "immutable",
    _object_schema(required=("receipt",), properties={"receipt": {"type": "object"}}),
    _record_render,
)
_register(
    "cpcs.reflect.rebuild",
    "Rebuild disposable learned state from curated and immutable stores.",
    "operator",
    "derived",
    _object_schema(),
    _reflect_rebuild,
)


def list_operations(role: str = "chat") -> list[dict[str, Any]]:
    if role not in ROLE_LEVEL:
        raise ValueError(f"unknown client role: {role}")
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "required_role": spec.required_role,
            "mutation_scope": spec.mutation_scope,
            "input_schema": copy.deepcopy(spec.input_schema),
        }
        for spec in sorted(OPERATIONS.values(), key=lambda item: item.name)
        if ROLE_LEVEL[role] >= ROLE_LEVEL[spec.required_role]
    ]


def authorization_request_hash(operation: str, arguments: dict[str, Any]) -> str:
    return sha256_value(
        {"schema": REQUEST_SCHEMA, "operation": operation, "arguments": arguments}
    )


def _request_id(request: Any) -> str:
    if (
        isinstance(request, dict)
        and isinstance(request.get("request_id"), str)
        and re.fullmatch(r"app_[0-9a-f]{24}", request["request_id"])
    ):
        return request["request_id"]
    return "app_" + hashlib.sha256(canonical_json_bytes(request)).hexdigest()[:24]


def _response(
    *,
    request_id: str,
    operation: str,
    status: str,
    required_role: str,
    granted_role: str,
    mutation_scope: str | None,
    result: dict[str, Any] | None,
    error: dict[str, Any] | None,
    root: Path,
) -> dict[str, Any]:
    value = {
        "schema": RESPONSE_SCHEMA,
        "request_id": request_id,
        "operation": operation,
        "status": status,
        "authority": {
            "required_role": required_role,
            "granted_role": granted_role,
            "mutation_scope": mutation_scope,
        },
        "policy_versions": {
            "application": APPLICATION_POLICY,
            "authorization": AUTHORIZATION_POLICY,
        },
        "result": result,
        "error": error,
    }
    validate_application_instance("application_response", value, root)
    return value


def invoke(
    request: dict[str, Any],
    *,
    role: str = "chat",
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate, authorize, and execute one application request."""
    if role not in ROLE_LEVEL:
        raise ValueError(f"unknown client role: {role}")
    request_id = _request_id(request)
    raw_operation = request.get("operation") if isinstance(request, dict) else None
    operation = (
        raw_operation
        if isinstance(raw_operation, str)
        and re.fullmatch(r"cpcs\.[a-z][a-z0-9_.]*", raw_operation)
        else "cpcs.invalid"
    )
    spec = OPERATIONS.get(operation)
    required_role = spec.required_role if spec else "chat"
    mutation_scope = spec.mutation_scope if spec else None
    try:
        validate_application_instance("application_request", request, root)
        if spec is None:
            raise LookupError(f"unknown CPCS operation: {operation}")
        if ROLE_LEVEL[role] < ROLE_LEVEL[spec.required_role]:
            raise PermissionError(
                f"{operation} requires the {spec.required_role} role; granted role is {role}"
            )
        if spec.required_role != "curator" and request.get("authorization") is not None:
            raise ValueError(
                "explicit authorization is accepted only for controlled curator operations"
            )
        errors = sorted(
            Draft202012Validator(spec.input_schema).iter_errors(request["arguments"]),
            key=lambda item: list(item.absolute_path),
        )
        if errors:
            detail = "; ".join(
                f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
                for error in errors
            )
            raise ValueError(f"invalid arguments for {operation}: {detail}")
        if spec.required_role == "curator":
            authorization = request.get("authorization")
            expected_hash = authorization_request_hash(operation, request["arguments"])
            if not isinstance(authorization, dict):
                raise PermissionError(f"{operation} requires explicit authorization")
            if (
                authorization.get("schema") != AUTHORIZATION_SCHEMA
                or authorization.get("operation") != operation
                or authorization.get("request_hash") != expected_hash
            ):
                raise PermissionError(
                    f"{operation} authorization is not bound to this exact request"
                )
        result = spec.handler(copy.deepcopy(request["arguments"]), root)
        return _response(
            request_id=request_id,
            operation=operation,
            status="success",
            required_role=required_role,
            granted_role=role,
            mutation_scope=mutation_scope,
            result=result,
            error=None,
            root=root,
        )
    except PermissionError as exc:
        code = "permission_denied"
        message = str(exc) or exc.__class__.__name__
    except LookupError as exc:
        code = "unknown_operation"
        message = str(exc) or exc.__class__.__name__
    except (TypeError, ValueError, KeyError) as exc:
        code = "invalid_request"
        message = str(exc) or exc.__class__.__name__
    except Exception as exc:  # fail closed at the transport boundary
        code = "operation_failed"
        message = str(exc) or exc.__class__.__name__
    return _response(
        request_id=request_id,
        operation=operation,
        status="error",
        required_role=required_role,
        granted_role=role,
        mutation_scope=mutation_scope,
        result=None,
        error={"code": code, "message": message},
        root=root,
    )
