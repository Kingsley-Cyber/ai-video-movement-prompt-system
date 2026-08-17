"""One versioned application service for every CPCS client surface."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator

from lab.compiler.build import (
    compile_build,
    load_validated_build_directory,
    make_build_request,
    write_build_directory,
)
from lab.compiler.provenance import sha256_bytes
from lab.compiler.score import make_score_request, resolve_score
from lab.second_brain.src.authority import authority_reader
from lab.second_brain.src.context import build_context_bundle
from lab.second_brain.src.enrich import enrich_context_bundle
from lab.second_brain.src.curate import (
    prepare_distillation_review,
    promote_distillation_bundle,
)
from lab.second_brain.src.distill import run_distillation, status as distillation_status
from lab.second_brain.src.intent import build_intent_context, normalize_intent
from lab.second_brain.src.placement import (
    inspect_graph_growth_plan,
    plan_graph_growth,
)
from lab.second_brain.src.measurement import (
    execute_pose_measurement_job,
    make_pose_measurement_job,
)
from lab.second_brain.src.query import default_request, reason, search_knowledge_objects
from lab.second_brain.src.reasoning_policy import compile_directing_strategy
from lab.second_brain.src.providers.polymath import (
    configuration_status as polymath_configuration_status,
    retrieve as retrieve_polymath,
)
from lab.second_brain.src.record import (
    append_experiment_receipt,
    append_measurement_batch,
    capture_human_testimonial,
    inspect_human_testimonial,
    prepare_experiment_flight,
    review_human_testimonial,
    seal_flight,
)
from lab.second_brain.src.research_session import (
    completed_bundle_for_source_units,
    distill_session,
    inspect_coverage as inspect_research_coverage,
    inspect_source as inspect_research_source,
    list_packets as list_research_packets,
    list_proposals as list_research_proposals,
    prepare_promotion as prepare_research_promotion,
    read_packet as read_research_packet,
    register_source as register_research_source,
    session_status as research_session_status,
    submit_extraction as submit_research_extraction,
    validate_proposals as validate_research_proposals,
)
from lab.second_brain.src.research_delta import (
    inspect_research_delta,
    prepare_research_delta,
)
from lab.second_brain.src.research_delta_patch import (
    discard_research_delta_patch,
    execute_research_delta_patch,
    inspect_research_delta_patch,
    prepare_research_delta_patch,
)
from lab.second_brain.src.reflect import rebuild
from lab.second_brain.src.maintenance import (
    advance_maintenance,
    build_brain_health_report,
    maintenance_status,
    prepare_maintenance,
)
from lab.second_brain.src.neo4j_projection import (
    projection_configuration_status,
    projection_plan_summary,
    projection_status,
    reasoning_parity,
    sync_projection,
)
from lab.second_brain.src.source_extract import (
    extract_folder,
    extract_retrieved_passages,
)
from lab.second_brain.src.source_registry import (
    admit_source_bundle,
    build_source_closure_report,
    resolve_sources,
)
from lab.second_brain.src.terminology import (
    inspect_terminology_proposal,
    propose_terminology_resolution,
    resolve_terminology,
)
from lab.second_brain.src.validate import (
    REPO_ROOT,
    canonical_json_bytes,
    load_schema,
    read_jsonl,
    sha256_value,
)
from lab.second_brain.src.video_observation import normalize_measurement
from lab.second_brain.src.video_reasoning import (
    build_knowledge_comparison_lens,
    discover_video_research_gaps,
    promote_reviewed_video_bridge,
)
from lab.release.contracts import load_release_policy, load_release_schema
from lab.release.stability import evaluate_stability, inspect_stability
from lab.runtime.journal import JobJournal, redact
from lab.runtime.runner import RenderRunner, make_render_job
from lab.second_brain.src.pegasus import (
    execute_surface_job,
    make_atomic_analysis_plan,
    run_analysis_cascade,
)
from lab.verification.verify import (
    build_verification_evidence_bundle,
    compare_reference_candidate,
    compare_reference_round_trip,
    make_verification_analysis_job,
    make_verification_asset_job,
    reference_candidate_comparison_request_schema,
    verify_render,
    write_time_normalized_contact_sheet,
)

from .contracts import load_application_schema, validate_application_instance
from .context_store import ContextProfileStore
from .agent_brief import build_agent_brief
from .accepted_experiment import accept_experiment
from .render_evidence_workflow import RenderEvidenceWorkflow
from .video_comparison_workflow import VideoComparisonWorkflow
from .reasoning_treatment import (
    handler_reasoning_experiment_inspect,
    handler_reasoning_experimental_plan,
    handler_reasoning_experiment_prepare,
    handler_repair_gap_prepare,
    handler_repair_inspect,
    handler_repair_plan,
)
from .cpcs_deliberation import (
    handler_deliberate_inspect,
    handler_deliberate_plan,
    handler_hypotheses_inspect,
    handler_ideate,
    handler_query_plan_inspect,
    handler_reasoning_closure_inspect,
)
from .bootstrap import bootstrap as _bootstrap_run
from .cpcs_guided_handlers import (
    handler_doctor,
    handler_guided_answer,
    handler_guided_finish,
    handler_guided_inspect,
    handler_guided_project,
    handler_guided_revise,
    handler_guided_start,
    handler_knowledge_apply_inspect,
    handler_session_history,
    handler_session_inspect,
)

APPLICATION_POLICY = "cpcs-application/1.27"
AUTHORIZATION_POLICY = "cpcs-local-authority/1.1"
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
    authorization_required: bool = False
    mcp_exposed: bool = True


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


@authority_reader("application_status_snapshot")
def _status(_: dict[str, Any], root: Path) -> dict[str, Any]:
    sb = root / "lab" / "second_brain"
    coverage = json.loads((sb / "derived" / "coverage.json").read_text(encoding="utf-8"))
    source_closure = build_source_closure_report(root)
    return {
        "schema": "cpcs.status/1.0",
        "service_version": APPLICATION_POLICY,
        "release_authority": "local_working_not_production_qualified",
        "stores": {
            "concepts": len(read_jsonl(root / "lab" / "concepts.jsonl")),
            "curated_edges": len(read_jsonl(sb / "curated" / "edges.jsonl")),
            "reasoning_policies": len(
                read_jsonl(sb / "curated" / "reasoning_policies.jsonl")
            ),
            "immutable_runs": len(read_jsonl(sb / "immutable" / "runs.jsonl")),
            "immutable_source_units": source_closure["counts"]["source_units"],
            "learned_edges": coverage["learned_edges"],
        },
        "distillation": distillation_status(root),
        "source_closure": source_closure["counts"],
        "integrations": {
            "polymath_mcp": polymath_configuration_status(),
            "neo4j_projection": projection_configuration_status(),
        },
        "operations": {
            "available": [row["name"] for row in list_operations("chat")],
            "restricted_count": len(OPERATIONS) - len(list_operations("chat")),
        },
        "authority_boundary": {
            "chat": "read_plus_idempotent_operational_build_and_context_expiry",
            "operator": "staging_derived_and_operational",
            "curator": "explicit_request_bound_authorization_required",
            "external_side_effects": "explicit_request_bound_authorization_required",
            "security_limit": "process_role_is_a_local_policy_gate_not_authenticated_identity",
        },
    }


def _agent_brief(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    value = build_agent_brief(
        arguments,
        operation_catalog=list_operations("curator"),
        application_policy=APPLICATION_POLICY,
        root=root,
    )
    validate_application_instance("agent_brief", value, root)
    return value


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
        terminology_proposal_ids=arguments.get("terminology_proposal_ids", []),
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
        valid_at=arguments.get("valid_at"),
        known_at=arguments.get("known_at"),
        validity_mode=arguments.get("validity_mode", "current"),
        retrieval_frame=arguments.get("retrieval_frame"),
        terminology_proposal_ids=arguments.get("terminology_proposal_ids", []),
        root=root,
    )


def _polymath_retrieve(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return retrieve_polymath(
        arguments["query"],
        corpus_ids=arguments.get("corpus_ids", []),
        rights_basis=arguments["rights_basis"],
        tool=arguments.get("tool", "polymath_search"),
        retrieval_tier=arguments.get("retrieval_tier", "qdrant_mongo"),
        top_k=arguments.get("top_k", 8),
        rerank_enabled=arguments.get("rerank_enabled", True),
        search_mode=arguments.get("search_mode", "local"),
        root=root,
    )


def _context_enrich(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return enrich_context_bundle(
        arguments["query"],
        token_budget=arguments.get("token_budget", 12_000),
        rights_basis=arguments["rights_basis"],
        provider=arguments.get("provider"),
        model=arguments.get("model"),
        minimum_status=arguments.get("minimum_status", "ingested"),
        domain=arguments.get("domain"),
        target_format=arguments.get("target_format", "hybrid"),
        required_layers=arguments.get("required_layers", []),
        excluded_layers=arguments.get("excluded_layers", []),
        intent=arguments.get("intent"),
        as_of=arguments.get("as_of"),
        valid_at=arguments.get("valid_at"),
        known_at=arguments.get("known_at"),
        validity_mode=arguments.get("validity_mode", "current"),
        retrieval_frame=arguments.get("retrieval_frame"),
        terminology_proposal_ids=arguments.get("terminology_proposal_ids", []),
        corpus_ids=arguments.get("corpus_ids", []),
        tool=arguments.get("tool", "polymath_search"),
        retrieval_tier=arguments.get("retrieval_tier", "qdrant_mongo"),
        top_k=arguments.get("top_k", 8),
        rerank_enabled=arguments.get("rerank_enabled", True),
        search_mode=arguments.get("search_mode", "local"),
        root=root,
    )


def _context_store(root: Path) -> ContextProfileStore:
    return ContextProfileStore(root)


def _context_profile_put(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return _context_store(root).put(**copy.deepcopy(arguments))


def _context_profile_get(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return _context_store(root).get(arguments["context_id"], as_of=arguments["as_of"])


def _context_profile_list(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return _context_store(root).list(as_of=arguments["as_of"])


def _context_profile_delete(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return _context_store(root).delete(arguments["context_id"])


def _resolved_context_overlays(
    arguments: dict[str, Any], root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    context_ids = arguments.get("context_profile_ids", [])
    if not context_ids:
        if "context_as_of" in arguments or "context_project_id" in arguments:
            raise ValueError(
                "context_as_of and context_project_id require context_profile_ids"
            )
        return [], []
    if "context_as_of" not in arguments:
        raise ValueError("context_profile_ids require context_as_of")
    store = _context_store(root)
    profiles = [
        store.get(context_id, as_of=arguments["context_as_of"])
        for context_id in context_ids
    ]
    if len(context_ids) != len(set(context_ids)):
        raise ValueError("context_profile_ids must be unique")
    project_id = arguments.get("context_project_id")
    for profile in profiles:
        if (
            profile["context_kind"] == "project_profile"
            and profile["project_id"] != project_id
        ):
            raise ValueError(
                f"context profile {profile['context_id']} belongs to another project"
            )
    overlays = [copy.deepcopy(profile["overlay"]) for profile in profiles]
    trace = [
        {
            "context_id": profile["context_id"],
            "revision": profile["revision"],
            "profile_hash": profile["profile_hash"],
            "context_kind": profile["context_kind"],
            "project_id": profile["project_id"],
        }
        for profile in profiles
    ]
    return overlays, trace


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
            valid_at=arguments.get("valid_at"),
            known_at=arguments.get("known_at"),
            validity_mode=arguments.get("validity_mode", "current"),
            retrieval_frame=arguments.get("retrieval_frame"),
            terminology_proposal_ids=arguments.get("terminology_proposal_ids", []),
        )
    return reason(request, root)


def _terminology_resolve(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return resolve_terminology(
        arguments["text"], arguments.get("domain"), root
    )


def _terminology_propose(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return propose_terminology_resolution(
        copy.deepcopy(arguments["resolution"]),
        arguments["match_id"],
        arguments["selected_sense_id"],
        copy.deepcopy(arguments["source_evidence"]),
        copy.deepcopy(arguments["agent"]),
        arguments["rationale"],
        root,
    )


def _terminology_inspect(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return inspect_terminology_proposal(arguments["proposal_id"], root)


def _graph_projection_plan(_: dict[str, Any], root: Path) -> dict[str, Any]:
    return projection_plan_summary(root)


def _graph_projection_status(_: dict[str, Any], root: Path) -> dict[str, Any]:
    return projection_status(root)


def _graph_projection_sync(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return sync_projection(
        expected_snapshot_hash=arguments["expected_snapshot_hash"],
        root=root,
    )


def _graph_projection_parity(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return reasoning_parity(arguments["requests"], root)


def _brain_health(_: dict[str, Any], root: Path) -> dict[str, Any]:
    return build_brain_health_report(root)


def _maintenance_prepare(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return prepare_maintenance(
        arguments["targets"],
        synchronize_neo4j=arguments.get("synchronize_neo4j", False),
        root=root,
    )


def _maintenance_status(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return maintenance_status(arguments["maintenance_id"], root)


def _maintenance_advance(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return advance_maintenance(
        arguments["maintenance_id"],
        expected_snapshot_hash=arguments.get("expected_snapshot_hash"),
        root=root,
    )


def _video_research_gaps(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return discover_video_research_gaps(
        copy.deepcopy(arguments["vog"]),
        query=arguments.get("query"),
        domain=arguments.get("domain"),
        root=root,
    )


def _video_bridge_promote(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return promote_reviewed_video_bridge(
        copy.deepcopy(arguments["vog"]),
        observation_id=arguments["observation_id"],
        concept_id=arguments["concept_id"],
        relation=arguments["relation"],
        review=copy.deepcopy(arguments["review"]),
        root=root,
    )


def _video_comparison_lens(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return build_knowledge_comparison_lens(
        copy.deepcopy(arguments["reference_vog"]),
        copy.deepcopy(arguments["candidate_vog"]),
        query=arguments["query"],
        domain=arguments.get("domain"),
        root=root,
    )


def _knowledge_search(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return search_knowledge_objects(
        arguments.get("query", ""),
        object_types=arguments.get("object_types"),
        object_ids=arguments.get("object_ids"),
        source_refs=arguments.get("source_refs"),
        evidence_classes=arguments.get("evidence_classes"),
        concept_ids=arguments.get("concept_ids"),
        maximum_results=arguments.get("maximum_results", 20),
        maximum_hops=arguments.get("maximum_hops", 5),
        validity_mode=arguments.get("validity_mode", "current"),
        as_of=arguments.get("as_of"),
        root=root,
    )


def _strategy_compile(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    sources = {key for key in ("intent_context", "text") if key in arguments}
    if len(sources) != 1:
        raise ValueError("strategy compile requires exactly one of intent_context or text")
    if "intent_context" in arguments:
        allowed = {"intent_context", "reasoning_policy_id", "knowledge_lens"}
        if set(arguments) - allowed:
            raise ValueError(
                "a complete intent_context cannot be mixed with text facade options"
            )
        intent_context = copy.deepcopy(arguments["intent_context"])
    else:
        lens_request = arguments.get("knowledge_lens", {}).get(
            "context_bundle", {}
        ).get("request", {})
        intent_context = build_intent_context(
            arguments["text"],
            token_budget=arguments.get(
                "token_budget", lens_request.get("token_budget", 12_000)
            ),
            user_constraints=arguments.get("user_constraints", []),
            profile_overrides=arguments.get("profile_overrides", []),
            minimum_status=arguments.get(
                "minimum_status", lens_request.get("minimum_status", "partial")
            ),
            target_format=arguments.get(
                "target_format", lens_request.get("target_format", "hybrid")
            ),
            knowledge_lens=arguments.get("knowledge_lens"),
            root=root,
        )
    return compile_directing_strategy(
        intent_context,
        requested_policy_id=arguments.get("reasoning_policy_id"),
        knowledge_lens=arguments.get("knowledge_lens"),
        root=root,
    )


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
        context_profile_trace: list[dict[str, Any]] = []
    else:
        intent_context = copy.deepcopy(arguments.get("intent_context"))
        if intent_context is None:
            lens_request = arguments.get("knowledge_lens", {}).get(
                "context_bundle", {}
            ).get("request", {})
            intent_context = build_intent_context(
                arguments["text"],
                token_budget=arguments.get(
                    "token_budget", lens_request.get("token_budget", 12_000)
                ),
                user_constraints=arguments.get("user_constraints", []),
                profile_overrides=arguments.get("profile_overrides", []),
                minimum_status=arguments.get(
                    "minimum_status", lens_request.get("minimum_status", "ingested")
                ),
                target_format=arguments.get(
                    "target_format", lens_request.get("target_format", "hybrid")
                ),
                knowledge_lens=arguments.get("knowledge_lens"),
                root=root,
            )
        persisted_overlays, context_profile_trace = _resolved_context_overlays(
            arguments, root
        )
        score_request = make_score_request(
            intent_context,
            profile_selection=arguments.get("profile_selection"),
            overlays=[*persisted_overlays, *arguments.get("overlays", [])],
            conflict_resolutions=arguments.get("conflict_resolutions", {}),
            assets=arguments.get("assets", []),
            requested_policy_id=arguments.get("reasoning_policy_id"),
            knowledge_lens=arguments.get("knowledge_lens"),
            root=root,
        )
    score = resolve_score(score_request, root)
    return {
        **intent_context,
        "context_profiles": context_profile_trace,
        "score": score,
    }


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


def _application_work_root(root: Path) -> Path:
    path = (root / "work" / "application").resolve()
    work = (root / "work").resolve()
    if work not in path.parents:
        raise ValueError("application work root escaped work/")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _build_path(build_id: str, root: Path) -> Path:
    if not re.fullmatch(r"build_[0-9a-f]{32}", build_id):
        raise ValueError("build_id is invalid")
    base = _application_work_root(root) / "builds"
    path = (base / build_id).resolve()
    if base.resolve() not in path.parents:
        raise ValueError("build path escaped application work root")
    return path


def _materialize_artifacts(
    artifacts: dict[str, bytes], root: Path
) -> dict[str, Any]:
    manifest = json.loads(artifacts["build_manifest.json"])
    output = _build_path(manifest["build_id"], root)
    if output.exists():
        existing = load_validated_build_directory(output, root)
        if existing["manifest"]["build_hash"] != manifest["build_hash"]:
            raise ValueError("materialized build ID collides with different bytes")
        return {
            "schema": "cpcs.materialized_build/1.0",
            "build_id": manifest["build_id"],
            "build_hash": manifest["build_hash"],
            "output_dir": str(output),
            "disposition": "already_present",
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{manifest['build_id']}.", dir=output.parent)
    )
    try:
        write_build_directory(artifacts, temporary)
        try:
            os.replace(temporary, output)
        except OSError:
            if not output.exists():
                raise
            existing = load_validated_build_directory(output, root)
            if existing["manifest"]["build_hash"] != manifest["build_hash"]:
                raise ValueError("concurrent build materialization differs")
        loaded = load_validated_build_directory(output, root)
        if loaded["manifest"]["build_hash"] != manifest["build_hash"]:
            raise ValueError("materialized build failed identity verification")
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return {
        "schema": "cpcs.materialized_build/1.0",
        "build_id": manifest["build_id"],
        "build_hash": manifest["build_hash"],
        "output_dir": str(output),
        "disposition": "created",
    }


def _build_materialize(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return _materialize_artifacts(
        compile_build(copy.deepcopy(arguments["request"]), root), root
    )


def _production_prepare(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    score_arguments = {
        key: copy.deepcopy(arguments[key])
        for key in (
            "text",
            "user_constraints",
            "profile_overrides",
            "token_budget",
            "minimum_status",
            "target_format",
            "profile_selection",
            "overlays",
            "conflict_resolutions",
            "assets",
            "context_profile_ids",
            "context_as_of",
            "reasoning_policy_id",
            "knowledge_lens",
        )
        if key in arguments
    }
    production_project_values = {
        key: arguments[key]
        for key in ("platform", "aspect_ratio", "duration_seconds")
        if key in arguments
    }
    if production_project_values:
        score_arguments.setdefault("overlays", []).append(
            {
                "overlay_id": "overlay_production_settings",
                "scope": "explicit_user_correction",
                "priority": 0,
                "values": {"project": production_project_values},
                "locks": [],
                "source_refs": ["application://production.prepare/settings"],
            }
        )
    if score_arguments.get("context_profile_ids"):
        score_arguments["context_project_id"] = arguments["project_id"]
    score_result = _score_build(score_arguments, root)
    directing_strategy = copy.deepcopy(
        score_result["score"]["directing_strategy_trace"]
    )
    project_settings = score_result["score"]["project"]
    build_request = make_build_request(
        score_result["score"],
        project_id=arguments["project_id"],
        creative_mode=arguments.get("creative_mode", "exact"),
        aspect_ratio=project_settings.get("aspect_ratio", "16:9"),
        duration_seconds=project_settings.get("duration_seconds", 8),
        resolution=arguments.get("resolution", "720p"),
        sample_count=arguments.get("sample_count", 1),
        seed=arguments.get("seed", 7),
        storage_uri=arguments.get("storage_uri"),
        asset_bindings=copy.deepcopy(arguments.get("asset_bindings", [])),
    )
    build = _materialize_artifacts(compile_build(build_request, root), root)
    return {
        "schema": "cpcs.production_preparation/1.0",
        **score_result,
        "directing_strategy": directing_strategy,
        "build_request": build_request,
        "build": build,
    }


def _analyze_run(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    job = copy.deepcopy(arguments["job"])
    job_id = job.get("job_id")
    if not isinstance(job_id, str) or not re.fullmatch(
        r"(?:tl|jockey|marengo)_[A-Za-z0-9._-]+", job_id
    ):
        raise ValueError("analysis job has no safe job_id")
    output = _application_work_root(root) / "analysis" / job_id
    return execute_surface_job(job, root, output_root=output)


def _analyze_atomic_prepare(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return make_atomic_analysis_plan(copy.deepcopy(arguments), root)


def _analyze_cascade(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    cascade = copy.deepcopy(arguments["cascade"])
    cascade_id = cascade.get("cascade_id")
    if not isinstance(cascade_id, str) or not re.fullmatch(
        r"tl_cascade_[A-Za-z0-9._-]+", cascade_id
    ):
        raise ValueError("analysis cascade has no safe cascade_id")
    output = _application_work_root(root) / "cascades" / cascade_id
    return run_analysis_cascade(
        cascade,
        root,
        authority_mode=arguments.get("authority_mode", "record_immutable"),
        output_root=output,
        intent_context=copy.deepcopy(arguments.get("intent_context")),
        score_assets=copy.deepcopy(arguments.get("score_assets", [])),
        conflict_resolutions=copy.deepcopy(arguments.get("conflict_resolutions")),
    )


def _render_runner(root: Path) -> RenderRunner:
    work = _application_work_root(root) / "render"
    journal = JobJournal(work / "jobs.sqlite3")
    return RenderRunner(journal, root=root, work_root=work / "jobs")


def _render_create(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    build_dir = _build_path(arguments["build_id"], root)
    job = make_render_job(
        build_dir,
        idempotency_key=arguments["idempotency_key"],
        timeout_seconds=arguments.get("timeout_seconds", 3600),
        poll_interval_seconds=arguments.get("poll_interval_seconds", 10),
        max_safe_retries=arguments.get("max_safe_retries", 2),
        lease_seconds=arguments.get("lease_seconds", 60),
        root=root,
    )
    return redact(_render_runner(root).register(job))


def _render_run(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    runner = _render_runner(root)
    runner.run(arguments["job_id"])
    runner.journal.verify(arguments["job_id"])
    return redact(runner.journal.get(arguments["job_id"]))


def _render_show(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    runner = _render_runner(root)
    runner.journal.verify(arguments["job_id"])
    return redact(runner.journal.get(arguments["job_id"]))


def _render_events(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    runner = _render_runner(root)
    runner.journal.verify(arguments["job_id"])
    return {
        "schema": "cpcs.render_events/1.0",
        "job_id": arguments["job_id"],
        "events": redact(runner.journal.events(arguments["job_id"])),
    }


def _render_cancel(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return redact(_render_runner(root).cancel(arguments["job_id"]))


def _render_reconcile(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return redact(
        _render_runner(root).reconcile(
            arguments["job_id"], copy.deepcopy(arguments["operation"])
        )
    )


def _workflow_child_executor(
    operation: str, arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    """Execute one workflow-derived child through its registered owning handler."""
    spec = OPERATIONS.get(operation)
    if spec is None or operation.startswith("cpcs.workflow."):
        raise ValueError(f"workflow child operation is not registered: {operation}")
    errors = sorted(
        Draft202012Validator(spec.input_schema).iter_errors(arguments),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        detail = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValueError(f"invalid workflow child arguments for {operation}: {detail}")
    _enforce_release_limits(operation, arguments, root)
    return spec.handler(copy.deepcopy(arguments), root)


def _render_evidence_workflow(root: Path) -> RenderEvidenceWorkflow:
    return RenderEvidenceWorkflow(
        executor=lambda operation, arguments: _workflow_child_executor(
            operation, arguments, root
        ),
        build_path=lambda build_id: _build_path(build_id, root),
        root=root,
        work_root=_application_work_root(root) / "render_evidence_workflows",
    )


def _workflow_render_prepare(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return _render_evidence_workflow(root).prepare(copy.deepcopy(arguments["request"]))


def _workflow_render_status(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return _render_evidence_workflow(root).status(arguments["workflow_id"])


def _workflow_render_advance(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return _render_evidence_workflow(root).advance(
        arguments["workflow_id"], arguments["expected_step_hash"]
    )


def _workflow_render_review(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return _render_evidence_workflow(root).supply_review(
        arguments["workflow_id"],
        arguments["expected_state_hash"],
        copy.deepcopy(arguments["review"]),
    )


def _workflow_render_cancel(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return _render_evidence_workflow(root).cancel(
        arguments["workflow_id"], arguments["expected_state_hash"]
    )


def _video_comparison_workflow(root: Path) -> VideoComparisonWorkflow:
    return VideoComparisonWorkflow(
        executor=lambda operation, arguments: _workflow_child_executor(
            operation, arguments, root
        ),
        root=root,
        work_root=_application_work_root(root) / "video_comparisons",
    )


def _video_compare_prepare(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return _video_comparison_workflow(root).prepare(
        copy.deepcopy(arguments["request"])
    )


def _video_compare_status(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return _video_comparison_workflow(root).status(arguments["workflow_id"])


def _video_compare_advance(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return _video_comparison_workflow(root).advance(
        arguments["workflow_id"], arguments["expected_step_hash"]
    )


def _video_compare_inspect(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return _video_comparison_workflow(root).inspect(arguments["workflow_id"])


def _video_compare_cancel(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return _video_comparison_workflow(root).cancel(
        arguments["workflow_id"], arguments["expected_state_hash"]
    )


def _write_operational_json(path: Path, value: dict[str, Any]) -> None:
    data = canonical_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or path.read_bytes() != data:
            raise ValueError(f"operational artifact collision: {path.name}")
        return
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _verify_run(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    build_dir = _build_path(arguments["build_id"], root)
    job_id = arguments["job_id"]
    if not re.fullmatch(r"render_job_[0-9a-f]{24}", job_id):
        raise ValueError("render job ID is invalid")
    result_path = _application_work_root(root) / "render" / "jobs" / job_id / "render_result.json"
    evidence_bundle = copy.deepcopy(arguments.get("evidence_bundle"))
    if evidence_bundle is None:
        evidence_bundle = build_verification_evidence_bundle(
            build_dir,
            result_path,
            arguments["artifact_id"],
            copy.deepcopy(arguments["observations"]),
            human_reviews=copy.deepcopy(arguments.get("human_reviews", [])),
            root=root,
        )
    report = verify_render(
        build_dir,
        result_path,
        arguments["artifact_id"],
        evidence_bundle,
        root=root,
    )
    output = _application_work_root(root) / "verifications" / f"{report['report_id']}.json"
    _write_operational_json(output, report)
    return {
        "schema": "cpcs.verification_result/1.0",
        "evidence_bundle": evidence_bundle,
        "report": report,
        "output": str(output),
    }


def _verify_reference_round_trip(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    job_id = arguments["job_id"]
    result_path = (
        _application_work_root(root)
        / "render"
        / "jobs"
        / job_id
        / "render_result.json"
    )
    report = compare_reference_round_trip(
        _build_path(arguments["build_id"], root),
        result_path,
        arguments["artifact_id"],
        copy.deepcopy(arguments["reference_batch"]),
        copy.deepcopy(arguments["generated_batch"]),
        actor_mapping=copy.deepcopy(arguments["actor_mapping"]),
        joints=copy.deepcopy(arguments["joints"]),
        thresholds=copy.deepcopy(arguments["thresholds"]),
        phase_samples=arguments.get("phase_samples", 21),
        root=root,
    )
    output = (
        _application_work_root(root)
        / "verifications"
        / "reference-round-trip"
        / f"{report['report_id']}.json"
    )
    _write_operational_json(output, report)
    return {
        "schema": "cpcs.reference_round_trip_result/1.0",
        "report": report,
        "output": str(output),
    }


def _verify_reference_compare(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    report = compare_reference_candidate(copy.deepcopy(arguments), root=root)
    directory = (
        _application_work_root(root)
        / "verifications"
        / "reference-candidate"
        / report["report_id"]
    )
    output = directory / "report.json"
    _write_operational_json(output, report)
    visual = None
    if arguments["settings"]["visual_sample_count"]:
        visual = write_time_normalized_contact_sheet(
            arguments,
            report,
            directory / "left-right-time-normalized.jpg",
            root=root,
        )
    return {
        "schema": "cpcs.reference_candidate_comparison_result/1.0",
        "report": report,
        "output": str(output),
        "visual": visual,
    }


def _verify_analysis_prepare(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    build_dir = _build_path(arguments["build_id"], root)
    job_id = arguments["job_id"]
    result_path = _application_work_root(root) / "render" / "jobs" / job_id / "render_result.json"
    return {
        "schema": "cpcs.verification_analysis_preparation/1.0",
        "job": make_verification_analysis_job(
            build_dir,
            result_path,
            arguments["artifact_id"],
            provider_asset_ref=arguments["provider_asset_ref"],
            rights_scope=arguments["rights_scope"],
            root=root,
        ),
    }


def _verify_asset_prepare(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    build_dir = _build_path(arguments["build_id"], root)
    job_id = arguments["job_id"]
    result_path = _application_work_root(root) / "render" / "jobs" / job_id / "render_result.json"
    return {
        "schema": "cpcs.verification_asset_preparation/1.0",
        "job": make_verification_asset_job(
            build_dir,
            result_path,
            arguments["artifact_id"],
            rights_scope=arguments["rights_scope"],
            root=root,
        ),
    }


def _measure_pose_prepare(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return make_pose_measurement_job(
        source_id=arguments["source_id"],
        asset_ref=arguments["asset_ref"],
        local_path=Path(arguments["local_path"]),
        rights_scope=arguments["rights_scope"],
        authorized_interval=copy.deepcopy(arguments["authorized_interval"]),
        model_path=Path(arguments["model_path"]),
        model_version=arguments["model_version"],
        created_at=arguments["created_at"],
        num_poses=arguments.get("num_poses", 2),
        stride=arguments.get("stride", 1),
        keyframe_interval_s=arguments.get("keyframe_interval_s", 0.5),
        min_visibility=arguments.get("min_visibility", 0.5),
        min_detection_confidence=arguments.get("min_detection_confidence", 0.5),
        root=root,
    )


def _measure_pose_run(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    job = copy.deepcopy(arguments["job"])
    job_id = job.get("job_id")
    if not isinstance(job_id, str) or not re.fullmatch(r"pose_job_[0-9a-f]{24}", job_id):
        raise ValueError("pose measurement job has no safe job_id")
    output = _application_work_root(root) / "measurements" / job_id
    return execute_pose_measurement_job(job, root, output_root=output)


def _measure_normalize(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    requested = arguments["measurement_observation_ids"]
    if len(requested) != len(set(requested)):
        raise ValueError("measurement observation IDs must be unique")
    rows = {
        row["id"]: row
        for row in read_jsonl(
            root / "lab" / "second_brain" / "immutable" / "measurement_observations.jsonl"
        )
    }
    missing = sorted(set(requested) - set(rows))
    if missing:
        raise ValueError("unknown measurement observation IDs: " + ", ".join(missing))
    source = copy.deepcopy(arguments["source"])
    interval = copy.deepcopy(arguments["authorized_interval"])
    observations = [
        normalize_measurement(
            rows[measurement_id],
            source=source,
            authorized_interval=interval,
            root=root,
        )
        for measurement_id in requested
    ]
    return {
        "schema": "cpcs.normalized_measurements/1.0",
        "source": source,
        "authorized_interval": interval,
        "observations": observations,
    }


def _record_measurement(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return append_measurement_batch(copy.deepcopy(arguments["batch"]), root)


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
    return prepare_distillation_review(arguments["run_id"], root)


def _research_source_register(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return register_research_source(copy.deepcopy(arguments), root)


def _research_source_inspect(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return inspect_research_source(arguments["session_id"], root)


def _research_source_units_admit(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    bundle = completed_bundle_for_source_units(arguments["session_id"], root)
    admission = admit_source_bundle(bundle, root)
    outputs = rebuild(root)
    return {
        "schema": "cpcs.research_source_unit_admission/1.0",
        "session_id": arguments["session_id"],
        "bundle_id": bundle["bundle_id"],
        "bundle_hash": bundle["bundle_hash"],
        "admission": admission,
        "source_closure": build_source_closure_report(root),
        "derived_outputs": outputs,
    }


def _source_status(_: dict[str, Any], root: Path) -> dict[str, Any]:
    return build_source_closure_report(root)


def _source_resolve(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return resolve_sources(
        concept_ids=arguments.get("concept_ids", []),
        source_unit_ids=arguments.get("source_unit_ids", []),
        query=arguments.get("query", ""),
        root=root,
    )


def _research_packet_list(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return list_research_packets(arguments["session_id"], root)


def _research_packet_read(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return read_research_packet(
        arguments["session_id"], arguments["packet_id"], root
    )


def _research_extraction_submit(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return submit_research_extraction(
        arguments["session_id"],
        copy.deepcopy(arguments["packet_result"]),
        arguments["submitted_at"],
        root,
    )


def _research_extraction_status(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return research_session_status(arguments["session_id"], root)


def _research_coverage_inspect(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return inspect_research_coverage(arguments["session_id"], root)


def _research_proposals_list(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return list_research_proposals(arguments["session_id"], root)


def _research_proposals_validate(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return validate_research_proposals(arguments["session_id"], root)


def _research_distillation_run(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return distill_session(arguments["session_id"], root)


def _research_placement_plan(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return plan_graph_growth(
        arguments["run_id"],
        copy.deepcopy(arguments["durable_ids"]),
        root,
        terminology_proposal_ids=copy.deepcopy(
            arguments.get("terminology_proposal_ids", {})
        ),
    )


def _research_placement_inspect(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return inspect_graph_growth_plan(arguments["plan_id"], root)


def _research_promotion_prepare(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return prepare_research_promotion(arguments["session_id"], root)


def _research_delta_prepare(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return prepare_research_delta(arguments["request"], root)


def _research_delta_inspect(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return inspect_research_delta(arguments["delta_id"], root)


def _research_delta_patch_prepare(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return prepare_research_delta_patch(arguments["request"], root)


def _research_delta_patch_execute(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return execute_research_delta_patch(arguments["execution_id"], root)


def _research_delta_patch_inspect(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return inspect_research_delta_patch(arguments["execution_id"], root)


def _research_delta_patch_discard(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return discard_research_delta_patch(arguments["execution_id"], root)


def _curate_promote(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    result = promote_distillation_bundle(
        arguments["run_id"],
        copy.deepcopy(arguments["durable_ids"]),
        arguments["promoted_by"],
        copy.deepcopy(arguments["review"]),
        root,
    )
    if result.get("growth_plan") is not None:
        result["derived_rebuild"] = {
            "requested_indexes": result["growth_plan"]["affected_derived_indexes"],
            "outputs": rebuild(root),
            "implementation": "canonical_full_rebuild_for_declared_invalidation_scope",
        }
    return result


def _record_render(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return append_experiment_receipt(copy.deepcopy(arguments["receipt"]), root)


def _record_testimonial_capture(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return capture_human_testimonial(copy.deepcopy(arguments["request"]), root)


def _record_testimonial_review(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return review_human_testimonial(copy.deepcopy(arguments["request"]), root)


def _testimonial_inspect(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return inspect_human_testimonial(arguments["testimonial_id"], root)


def _experiment_prepare(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return prepare_experiment_flight(
        flight_id=arguments["flight_id"],
        arm_builds=[
            {
                "id": arm["id"],
                "build_dir": str(_build_path(arm["build_id"], root)),
                "tested_delta": copy.deepcopy(arm.get("tested_delta")),
            }
            for arm in arguments["arms"]
        ],
        classification=arguments["classification"],
        metric_ids=copy.deepcopy(arguments["metric_ids"]),
        outcome_concept_ids=copy.deepcopy(arguments["outcome_concept_ids"]),
        provider=arguments["provider"],
        model_version=arguments["model_version"],
        sealed_at=arguments["sealed_at"],
        root=root,
    )


def _experiment_seal(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return seal_flight(copy.deepcopy(arguments["flight_draft"]), root)


def _experiment_accept(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return accept_experiment(copy.deepcopy(arguments["request"]), root)


def _reflect_rebuild(_: dict[str, Any], root: Path) -> dict[str, Any]:
    return {"schema": "cpcs.reflection_rebuild/1.0", "outputs": rebuild(root)}


def _qualification_stability_evaluate(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return evaluate_stability(copy.deepcopy(arguments["request"]), root)


def _qualification_stability_inspect(
    arguments: dict[str, Any], root: Path
) -> dict[str, Any]:
    return inspect_stability(arguments["report_id"], root)


COMMON_INTENT_PROPERTIES = {
    "text": STRING,
    "user_constraints": STRING_LIST,
    "profile_overrides": STRING_LIST,
}
CONTEXT_PROPERTIES = {
    "token_budget": {"type": "integer", "minimum": 1},
    "minimum_status": {"enum": ["ingested", "partial", "proven"]},
    "target_format": {"enum": ["prose", "natural_language", "yaml", "json", "xml", "hybrid"]},
}
BITEMPORAL_INPUT_PROPERTIES = {
    "as_of": {"type": ["string", "null"]},
    "valid_at": {"type": ["string", "null"]},
    "known_at": {"type": ["string", "null"]},
    "validity_mode": {"enum": ["current", "historical", "all_versions"]},
    "retrieval_frame": {"type": ["object", "null"]},
}
POLYMATH_RETRIEVAL_PROPERTIES = {
    "corpus_ids": {
        "type": "array",
        "maxItems": 8,
        "uniqueItems": True,
        "items": STRING,
    },
    "tool": {
        "enum": ["polymath_search", "polymath_cross_corpus_search"]
    },
    "retrieval_tier": {
        "enum": ["qdrant_only", "qdrant_mongo", "qdrant_mongo_graph"]
    },
    "top_k": {"type": "integer", "minimum": 1, "maximum": 12},
    "rerank_enabled": {"type": "boolean"},
    "search_mode": {"enum": ["local", "global", "auto"]},
}
TERMINOLOGY_PROPOSAL_IDS = {
    "type": "array",
    "uniqueItems": True,
    "items": {
        "type": "string",
        "pattern": "^termprop_[0-9a-f]{24}$",
    },
}
CONTEXT_PROFILE_ID = {
    "type": "string",
    "pattern": "^context_[A-Za-z0-9._-]{3,80}$",
}
CONTEXT_PROFILE_IDS = {
    "type": "array",
    "uniqueItems": True,
    "items": CONTEXT_PROFILE_ID,
}
CONTEXT_AS_OF = {
    "type": "string",
    "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$",
}
PROJECT_ID = {
    "type": "string",
    "pattern": "^[a-z][a-z0-9-]{4,28}[a-z0-9]$",
}


OPERATIONS: dict[str, OperationSpec] = {}


def _register(
    name: str,
    description: str,
    role: str,
    mutation_scope: str | None,
    input_schema: dict[str, Any],
    handler: Handler,
    *,
    authorization_required: bool = False,
    mcp_exposed: bool = True,
) -> None:
    OPERATIONS[name] = OperationSpec(
        name,
        description,
        role,
        mutation_scope,
        input_schema,
        handler,
        authorization_required=authorization_required,
        mcp_exposed=mcp_exposed,
    )


_register("cpcs.status", "Read CPCS runtime and authority status.", "chat", None, _object_schema(), _status)
_register(
    "cpcs.agent.brief",
    "Build a task-scoped, secret-safe operating brief with typed routes, tools, authority stops, and output-format rules.",
    "chat",
    None,
    _object_schema(
        required=("task",),
        properties={
            "task": {"type": "string", "minLength": 1, "maxLength": 8000},
            "role": {"enum": ["chat", "operator", "curator"]},
        },
    ),
    _agent_brief,
)
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
        properties={
            **COMMON_INTENT_PROPERTIES,
            **CONTEXT_PROPERTIES,
            "terminology_proposal_ids": TERMINOLOGY_PROPOSAL_IDS,
        },
    ),
    _intent_context,
)
_register(
    "cpcs.context.enrich",
    "Build local context and retrieve bounded Polymath evidence only for its declared gap.",
    "operator",
    "operational_external",
    _object_schema(
        required=("query", "rights_basis"),
        properties={
            "query": STRING,
            "rights_basis": STRING,
            **CONTEXT_PROPERTIES,
            "provider": {"type": ["string", "null"]},
            "model": {"type": ["string", "null"]},
            "domain": {"type": ["string", "null"]},
            "required_layers": STRING_LIST,
            "excluded_layers": STRING_LIST,
            "intent": {"type": ["string", "null"]},
            **BITEMPORAL_INPUT_PROPERTIES,
            "terminology_proposal_ids": TERMINOLOGY_PROPOSAL_IDS,
            **POLYMATH_RETRIEVAL_PROPERTIES,
        },
    ),
    _context_enrich,
    authorization_required=True,
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
            **BITEMPORAL_INPUT_PROPERTIES,
            "terminology_proposal_ids": TERMINOLOGY_PROPOSAL_IDS,
        },
    ),
    _context_get,
)
_source_resolution_schema = _object_schema(
    properties={
        "concept_ids": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": STRING,
        },
        "source_unit_ids": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {
                "type": "string",
                "pattern": "^source_unit_[0-9a-f]{24}$",
            },
        },
        "query": {"type": "string"},
    },
)
_source_resolution_schema["anyOf"] = [
    {"required": ["concept_ids"]},
    {"required": ["source_unit_ids"]},
]
_register(
    "cpcs.source.status",
    "Inspect deterministic concept source closure and every quarantined reference.",
    "chat",
    None,
    _object_schema(),
    _source_status,
)
_register(
    "cpcs.source.resolve",
    "Dereference curated concepts or exact source-unit IDs into bounded hash-verified local passages.",
    "chat",
    None,
    _source_resolution_schema,
    _source_resolve,
)
_register(
    "cpcs.terminology.resolve",
    "Normalize registered identifiers and detect homonyms before graph traversal; unresolved senses return a bounded agent task.",
    "chat",
    None,
    _object_schema(
        required=("text",),
        properties={
            "text": STRING,
            "domain": {"type": ["string", "null"]},
        },
    ),
    _terminology_resolve,
)
_register(
    "cpcs.terminology.propose",
    "Stage one source-backed agent sense selection for the exact current query without changing canonical authority.",
    "operator",
    "staging",
    _object_schema(
        required=(
            "resolution",
            "match_id",
            "selected_sense_id",
            "source_evidence",
            "agent",
            "rationale",
        ),
        properties={
            "resolution": load_schema("terminology_resolution"),
            "match_id": {"type": "string", "pattern": "^termmatch_[0-9a-f]{24}$"},
            "selected_sense_id": STRING,
            "source_evidence": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {
                    "type": "object",
                    "required": ["source_unit_id", "content_sha256"],
                    "properties": {
                        "source_unit_id": {
                            "type": "string",
                            "pattern": "^source_unit_[0-9a-f]{24}$",
                        },
                        "content_sha256": {
                            "type": "string",
                            "pattern": "^sha256:[0-9a-f]{64}$",
                        },
                    },
                    "additionalProperties": False,
                },
            },
            "agent": {
                "type": "object",
                "required": ["client", "model", "prompt_sha256"],
                "properties": {
                    "client": STRING,
                    "model": STRING,
                    "prompt_sha256": {
                        "type": "string",
                        "pattern": "^sha256:[0-9a-f]{64}$",
                    },
                },
                "additionalProperties": False,
            },
            "rationale": STRING,
        },
    ),
    _terminology_propose,
)
_register(
    "cpcs.terminology.inspect",
    "Inspect one staged terminology proposal and recompute its registry, source, and closed-sense checks.",
    "operator",
    None,
    _object_schema(
        required=("proposal_id",),
        properties={
            "proposal_id": {
                "type": "string",
                "pattern": "^termprop_[0-9a-f]{24}$",
            }
        },
    ),
    _terminology_inspect,
)
_register(
    "cpcs.polymath.retrieve",
    "Retrieve one bounded untrusted Polymath evidence packet for context or distillation.",
    "operator",
    "operational_external",
    _object_schema(
        required=("query", "rights_basis"),
        properties={
            "query": STRING,
            "rights_basis": STRING,
            **POLYMATH_RETRIEVAL_PROPERTIES,
        },
    ),
    _polymath_retrieve,
    authorization_required=True,
)
_register(
    "cpcs.context.profile.put",
    "Create or revise one local typed user or project context profile.",
    "operator",
    "operational",
    _object_schema(
        required=(
            "context_id",
            "context_kind",
            "project_id",
            "priority",
            "values",
            "locks",
            "valid_from",
            "valid_until",
        ),
        properties={
            "context_id": CONTEXT_PROFILE_ID,
            "context_kind": {"enum": ["user_defaults", "project_profile"]},
            "project_id": {"oneOf": [{"type": "null"}, PROJECT_ID]},
            "priority": {"type": "integer", "minimum": 0},
            "values": {"type": "object", "minProperties": 1},
            "locks": STRING_LIST,
            "valid_from": CONTEXT_AS_OF,
            "valid_until": CONTEXT_AS_OF,
        },
    ),
    _context_profile_put,
)
_register(
    "cpcs.context.profile.get",
    "Read one active local context profile and prune expired profile versions.",
    "operator",
    "operational",
    _object_schema(
        required=("context_id", "as_of"),
        properties={"context_id": CONTEXT_PROFILE_ID, "as_of": CONTEXT_AS_OF},
    ),
    _context_profile_get,
)
_register(
    "cpcs.context.profile.list",
    "List active local context profiles and prune expired profile versions.",
    "operator",
    "operational",
    _object_schema(required=("as_of",), properties={"as_of": CONTEXT_AS_OF}),
    _context_profile_list,
)
_register(
    "cpcs.context.profile.delete",
    "Delete every local revision of one context profile.",
    "operator",
    "operational",
    _object_schema(
        required=("context_id",), properties={"context_id": CONTEXT_PROFILE_ID}
    ),
    _context_profile_delete,
    authorization_required=True,
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
            "target_format": {"enum": ["prose", "natural_language", "yaml", "json", "xml", "hybrid"]},
            "provider": {"type": ["string", "null"]},
            "model_version": {"type": ["string", "null"]},
            "maximum_depth": {"type": "integer", "minimum": 0},
            "minimum_status": {"enum": ["ingested", "partial", "proven"]},
            "include_unproven": {"type": "boolean"},
            "required_layers": STRING_LIST,
            "excluded_layers": STRING_LIST,
            "deterministic_seed": {"type": "integer"},
            **BITEMPORAL_INPUT_PROPERTIES,
            "terminology_proposal_ids": {
                "type": "array",
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "pattern": "^termprop_[0-9a-f]{24}$",
                },
            },
        },
    ),
    _reason,
)
_register(
    "cpcs.graph.projection.plan",
    "Build the deterministic CPCS-owned Neo4j projection plan without contacting Neo4j or changing authority.",
    "operator",
    None,
    _object_schema(),
    _graph_projection_plan,
)
_register(
    "cpcs.graph.projection.status",
    "Inspect the active CPCS Neo4j generation, checkpoint, counts, and logical digest without exposing Cypher or credentials.",
    "operator",
    None,
    _object_schema(),
    _graph_projection_status,
)
_register(
    "cpcs.graph.projection.sync",
    "Synchronize one exact authorized Git snapshot into the isolated CPCS Neo4j namespace with idempotent create, update, retire, and restore behavior.",
    "operator",
    "operational_external",
    _object_schema(
        required=("expected_snapshot_hash",),
        properties={
            "expected_snapshot_hash": {
                "type": "string",
                "pattern": "^sha256:[0-9a-f]{64}$",
            }
        },
    ),
    _graph_projection_sync,
    authorization_required=True,
)
_register(
    "cpcs.graph.projection.parity",
    "Compare bounded cpcs.reason results from Neo4j against the NetworkX reference, including paths, sources, evidence, rejections, alternatives, and gaps.",
    "operator",
    None,
    _object_schema(
        required=("requests",),
        properties={
            "requests": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": load_schema("reasoning_query"),
            }
        },
    ),
    _graph_projection_parity,
)
_maintenance_targets_schema = {
    "type": "array",
    "minItems": 1,
    "uniqueItems": True,
    "items": {
        "enum": [
            "weights", "insights", "coverage", "source_closure", "indexes",
            "domain_coverage", "core_memory", "outcome_memory", "brain_health",
        ]
    },
}
_maintenance_id_schema = {
    "type": "string",
    "pattern": "^maintenance_[0-9a-f]{24}$",
}
_register(
    "cpcs.brain.health",
    "Build one revision-bound report for schema, source closure, domain coverage, graph reachability, and projection readiness.",
    "operator",
    None,
    _object_schema(),
    _brain_health,
)
_register(
    "cpcs.maintenance.prepare",
    "Seal one resumable selective-derived maintenance plan and its exact optional Neo4j snapshot.",
    "operator",
    "operational",
    _object_schema(
        required=("targets",),
        properties={
            "targets": _maintenance_targets_schema,
            "synchronize_neo4j": {"type": "boolean"},
        },
    ),
    _maintenance_prepare,
)
_register(
    "cpcs.maintenance.status",
    "Read and hash-verify one resumable maintenance state.",
    "operator",
    None,
    _object_schema(
        required=("maintenance_id",),
        properties={"maintenance_id": _maintenance_id_schema},
    ),
    _maintenance_status,
)
_register(
    "cpcs.maintenance.advance",
    "Advance exactly one maintenance transition; Neo4j submission requires explicit authorization and the prepared snapshot hash.",
    "operator",
    "operational_external",
    _object_schema(
        required=("maintenance_id",),
        properties={
            "maintenance_id": _maintenance_id_schema,
            "expected_snapshot_hash": {
                "type": ["string", "null"],
                "pattern": "^sha256:[0-9a-f]{64}$",
            },
        },
    ),
    _maintenance_advance,
    authorization_required=True,
)
_register(
    "cpcs.video.research_gaps",
    "Use Pegasus VOG evidence and the governed knowledge graph to expose unbridged observations, contradictions, and research gaps.",
    "operator",
    None,
    _object_schema(
        required=("vog",),
        properties={
            "vog": {"type": "object"},
            "query": {"type": ["string", "null"]},
            "domain": {"type": ["string", "null"]},
        },
    ),
    _video_research_gaps,
)
_register(
    "cpcs.video.bridge.promote",
    "Promote one explicitly approved, hash-bound VOG observation-to-concept bridge without merging video and concept graphs.",
    "curator",
    "curated",
    _object_schema(
        required=("vog", "observation_id", "concept_id", "relation", "review"),
        properties={
            "vog": {"type": "object"},
            "observation_id": {"type": "string", "pattern": "^vog_obs_[A-Za-z0-9._-]+$"},
            "concept_id": {"type": "string", "pattern": "^c_[A-Za-z0-9._-]+$"},
            "relation": {"enum": ["USES_CONCEPT", "SUPPORTS_CONCEPT", "CONTRADICTS_CONCEPT", "REVEALS_KNOWLEDGE_GAP"]},
            "review": {
                "type": "object",
                "required": ["status", "reviewer_id", "reviewed_at", "remarks"],
                "properties": {
                    "status": {"const": "approved"},
                    "reviewer_id": STRING,
                    "reviewed_at": STRING,
                    "remarks": STRING,
                },
                "additionalProperties": False,
            },
        },
    ),
    _video_bridge_promote,
    authorization_required=True,
)
_register(
    "cpcs.video.comparison.lens",
    "Build a knowledge-conditioned lens before paired VOG comparison, preserving each graph identity and reviewed bridge coverage.",
    "operator",
    None,
    _object_schema(
        required=("reference_vog", "candidate_vog", "query"),
        properties={
            "reference_vog": {"type": "object"},
            "candidate_vog": {"type": "object"},
            "query": STRING,
            "domain": {"type": ["string", "null"]},
        },
    ),
    _video_comparison_lens,
)
_register(
    "cpcs.knowledge.search",
    "Search first-class research objects and traverse explicit relevance-gated links.",
    "chat",
    None,
    _object_schema(
        properties={
            "query": {"type": "string"},
            "object_types": {
                "type": "array",
                "uniqueItems": True,
                "items": {"enum": ["claim", "equation", "method", "mechanism"]},
            },
            "object_ids": STRING_LIST,
            "source_refs": STRING_LIST,
            "evidence_classes": {
                "type": "array",
                "uniqueItems": True,
                "items": {
                    "enum": [
                        "measured", "detected", "inferred", "interpreted",
                        "authored", "simulated", "derived",
                    ]
                },
            },
            "concept_ids": STRING_LIST,
            "maximum_results": {"type": "integer", "minimum": 1, "maximum": 100},
            "maximum_hops": {"type": "integer", "minimum": 0, "maximum": 8},
            "as_of": {"type": ["string", "null"]},
            "validity_mode": {"enum": ["current", "historical", "all_versions"]},
        },
    ),
    _knowledge_search,
)
_register(
    "cpcs.strategy.compile",
    "Select one governed reasoning policy and compile retrieved knowledge into a provider-neutral directing strategy.",
    "chat",
    None,
    _object_schema(
        properties={
            **COMMON_INTENT_PROPERTIES,
            **CONTEXT_PROPERTIES,
            "intent_context": {"type": "object"},
            "knowledge_lens": {"type": "object"},
            "reasoning_policy_id": {
                "type": "string",
                "pattern": "^rp_[A-Za-z0-9._-]+$",
            },
        },
    ),
    _strategy_compile,
)
_register(
    "cpcs.score.build",
    "Resolve guided or advanced input through one canonical score kernel.",
    "chat",
    "operational",
    _object_schema(
        properties={
            **COMMON_INTENT_PROPERTIES,
            **CONTEXT_PROPERTIES,
            "intent_context": {"type": "object"},
            "score_request": {"type": "object"},
            "knowledge_lens": {"type": "object"},
            "profile_selection": STRING_LIST,
            "overlays": {"type": "array", "items": {"type": "object"}},
            "conflict_resolutions": {"type": "object"},
            "assets": {"type": "array", "items": {"type": "object"}},
            "context_profile_ids": CONTEXT_PROFILE_IDS,
            "context_as_of": CONTEXT_AS_OF,
            "reasoning_policy_id": {
                "type": "string",
                "pattern": "^rp_[A-Za-z0-9._-]+$",
            },
            "context_project_id": {"oneOf": [{"type": "null"}, PROJECT_ID]},
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
    "cpcs.build.materialize",
    "Compile and atomically materialize one provider build under ignored operational state.",
    "operator",
    "operational",
    _object_schema(required=("request",), properties={"request": {"type": "object"}}),
    _build_materialize,
)
_register(
    "cpcs.production.prepare",
    "Resolve ordinary language through intent, context, governed reasoning policy, canonical score, and a materialized provider build.",
    "chat",
    "operational",
    _object_schema(
        required=("text", "project_id"),
        properties={
            **COMMON_INTENT_PROPERTIES,
            **CONTEXT_PROPERTIES,
            "project_id": PROJECT_ID,
            "profile_selection": STRING_LIST,
            "overlays": {"type": "array", "items": {"type": "object"}},
            "conflict_resolutions": {"type": "object"},
            "assets": {"type": "array", "items": {"type": "object"}},
            "reasoning_policy_id": {
                "type": "string",
                "pattern": "^rp_[A-Za-z0-9._-]+$",
            },
            "knowledge_lens": {"type": "object"},
            "creative_mode": {
                "enum": [
                    "exact",
                    "interpretive",
                    "exploratory",
                    "transfer",
                    "diagnostic",
                    "research_gap",
                ]
            },
            "platform": STRING,
            "aspect_ratio": {"enum": ["16:9", "9:16"]},
            "duration_seconds": {"enum": [4, 6, 8]},
            "resolution": {"enum": ["720p", "1080p"]},
            "sample_count": {"type": "integer", "minimum": 1, "maximum": 4},
            "seed": {"type": "integer", "minimum": 0, "maximum": 4294967295},
            "storage_uri": {"type": ["string", "null"]},
            "asset_bindings": {"type": "array", "items": {"type": "object"}},
            "context_profile_ids": CONTEXT_PROFILE_IDS,
            "context_as_of": CONTEXT_AS_OF,
        },
    ),
    _production_prepare,
)
_register(
    "cpcs.analyze.atomic.prepare",
    "Build a fixed-mode, content-addressed atomic video-analysis plan without calling a provider or mutating authority.",
    "operator",
    None,
    {
        key: copy.deepcopy(value)
        for key, value in load_schema("atomic_video_analysis_request").items()
        if key not in {"$schema", "$id"}
    },
    _analyze_atomic_prepare,
)
_register(
    "cpcs.analyze.run",
    "Execute one versioned TwelveLabs surface job and retain request, raw response, and normalized artifacts.",
    "operator",
    "operational_external",
    _object_schema(required=("job",), properties={"job": {"type": "object"}}),
    _analyze_run,
    authorization_required=True,
)
_register(
    "cpcs.analyze.cascade",
    "Run the source-bounded semantic and immutable-measurement cascade through VOG fusion and optional reverse scoring.",
    "curator",
    "operational_external_immutable",
    _object_schema(
        required=("cascade",),
        properties={
            "cascade": {"type": "object"},
            "authority_mode": {
                "enum": ["record_immutable", "operational_only"]
            },
            "intent_context": {"type": ["object", "null"]},
            "score_assets": {"type": "array", "items": {"type": "object"}},
            "conflict_resolutions": {"type": ["object", "null"]},
        },
    ),
    _analyze_cascade,
    authorization_required=True,
)
_register(
    "cpcs.render.create",
    "Register one idempotent render job for a materialized application build.",
    "operator",
    "operational",
    _object_schema(
        required=("build_id", "idempotency_key"),
        properties={
            "build_id": {
                "type": "string",
                "pattern": "^build_[0-9a-f]{32}$",
            },
            "idempotency_key": {"type": "string", "minLength": 1, "maxLength": 256},
            "timeout_seconds": {"type": "number", "exclusiveMinimum": 0},
            "poll_interval_seconds": {"type": "number", "minimum": 0},
            "max_safe_retries": {"type": "integer", "minimum": 0, "maximum": 8},
            "lease_seconds": {"type": "number", "exclusiveMinimum": 0},
        },
    ),
    _render_create,
)
for _name, _description, _handler, _authorization, _scope in (
    (
        "cpcs.render.run",
        "Submit or resume one journaled render job through its registered provider adapter.",
        _render_run,
        True,
        "operational_external",
    ),
    (
        "cpcs.render.show",
        "Read and verify one render-job snapshot.",
        _render_show,
        False,
        None,
    ),
    (
        "cpcs.render.events",
        "Read the verified hash-chained event history for one render job.",
        _render_events,
        False,
        None,
    ),
    (
        "cpcs.render.cancel",
        "Request bounded cancellation for one journaled render job.",
        _render_cancel,
        True,
        "operational_external",
    ),
):
    _register(
        _name,
        _description,
        "operator",
        _scope,
        _object_schema(
            required=("job_id",),
            properties={
                "job_id": {
                    "type": "string",
                    "pattern": "^render_job_[0-9a-f]{24}$",
                }
            },
        ),
        _handler,
        authorization_required=_authorization,
    )
_register(
    "cpcs.render.reconcile",
    "Attach a reviewed provider operation receipt to a quarantined render submission.",
    "operator",
    "operational",
    _object_schema(
        required=("job_id", "operation"),
        properties={
            "job_id": {
                "type": "string",
                "pattern": "^render_job_[0-9a-f]{24}$",
            },
            "operation": {"type": "object"},
        },
    ),
    _render_reconcile,
    authorization_required=True,
)
_workflow_id_schema = {
    "type": "string",
    "pattern": "^workflow_[0-9a-f]{24}$",
}
_hash_schema = {
    "type": "string",
    "pattern": "^sha256:[0-9a-f]{64}$",
}
_register(
    "cpcs.workflow.render.prepare",
    "Create one content-bound workflow for a sealed experiment arm without provider contact or authority mutation.",
    "operator",
    "operational",
    _object_schema(
        required=("request",),
        properties={
            "request": load_application_schema("render_evidence_workflow_request")
        },
    ),
    _workflow_render_prepare,
)
_register(
    "cpcs.workflow.render.status",
    "Verify and read one hash-chained render-evidence workflow without exposing prompts, filesystem paths, or raw review text.",
    "operator",
    None,
    _object_schema(
        required=("workflow_id",),
        properties={"workflow_id": _workflow_id_schema},
    ),
    _workflow_render_status,
)
_register(
    "cpcs.workflow.render.advance",
    "Execute one workflow-derived registered handler under authorization bound to the exact persisted step hash.",
    "curator",
    "operational_external_immutable",
    _object_schema(
        required=("workflow_id", "expected_step_hash"),
        properties={
            "workflow_id": _workflow_id_schema,
            "expected_step_hash": _hash_schema,
        },
    ),
    _workflow_render_advance,
    authorization_required=True,
)
_register(
    "cpcs.workflow.render.review",
    "Supply one exact human review to a verified workflow and stage the existing authorized testimonial operations.",
    "curator",
    "operational",
    _object_schema(
        required=("workflow_id", "expected_state_hash", "review"),
        properties={
            "workflow_id": _workflow_id_schema,
            "expected_state_hash": _hash_schema,
            "review": load_application_schema("render_evidence_workflow_review"),
        },
    ),
    _workflow_render_review,
    authorization_required=True,
)
_register(
    "cpcs.workflow.render.cancel",
    "Stop one workflow locally and invoke the existing render cancellation disposition when a provider job exists.",
    "operator",
    "operational_external",
    _object_schema(
        required=("workflow_id", "expected_state_hash"),
        properties={
            "workflow_id": _workflow_id_schema,
            "expected_state_hash": _hash_schema,
        },
    ),
    _workflow_render_cancel,
    authorization_required=True,
)
_video_comparison_workflow_id_schema = {
    "type": "string",
    "pattern": "^video_compare_[0-9a-f]{24}$",
}
_register(
    "cpcs.video.compare.prepare",
    "Create one content-bound paired Pegasus comparison plan without provider contact or knowledge-authority mutation.",
    "operator",
    "operational",
    _object_schema(
        required=("request",),
        properties={
            "request": load_application_schema("video_comparison_workflow_request")
        },
    ),
    _video_compare_prepare,
)
_register(
    "cpcs.video.compare.status",
    "Verify and read one paired comparison journal with fixed provider-call counts and separate VOG identities.",
    "operator",
    None,
    _object_schema(
        required=("workflow_id",),
        properties={"workflow_id": _video_comparison_workflow_id_schema},
    ),
    _video_compare_status,
)
_register(
    "cpcs.video.compare.advance",
    "Execute exactly one fixed paired-analysis, local-measurement, or comparison step under authorization bound to its persisted step hash.",
    "curator",
    "operational_external",
    _object_schema(
        required=("workflow_id", "expected_step_hash"),
        properties={
            "workflow_id": _video_comparison_workflow_id_schema,
            "expected_step_hash": _hash_schema,
        },
    ),
    _video_compare_advance,
    authorization_required=True,
)
_register(
    "cpcs.video.compare.inspect",
    "Inspect the completed operational comparison report and its exact paired VOG lineage.",
    "operator",
    None,
    _object_schema(
        required=("workflow_id",),
        properties={"workflow_id": _video_comparison_workflow_id_schema},
    ),
    _video_compare_inspect,
)
_register(
    "cpcs.video.compare.cancel",
    "Cancel one exact comparison between synchronous child steps without deleting receipts or analysis artifacts.",
    "operator",
    "operational",
    _object_schema(
        required=("workflow_id", "expected_state_hash"),
        properties={
            "workflow_id": _video_comparison_workflow_id_schema,
            "expected_state_hash": _hash_schema,
        },
    ),
    _video_compare_cancel,
    authorization_required=True,
)
_register(
    "cpcs.verify.asset.prepare",
    "Create one hash-bound TwelveLabs upload job for a retrieved render artifact.",
    "operator",
    None,
    _object_schema(
        required=("build_id", "job_id", "artifact_id", "rights_scope"),
        properties={
            "build_id": {
                "type": "string",
                "pattern": "^build_[0-9a-f]{32}$",
            },
            "job_id": {
                "type": "string",
                "pattern": "^render_job_[0-9a-f]{24}$",
            },
            "artifact_id": {"type": "string", "pattern": "^artifact_[A-Za-z0-9._-]+$"},
            "rights_scope": {"enum": ["authorized", "original", "licensed"]},
        },
    ),
    _verify_asset_prepare,
)
_register(
    "cpcs.verify.analysis.prepare",
    "Create one score-bound Pegasus analysis job for a rendered artifact already registered with TwelveLabs.",
    "operator",
    None,
    _object_schema(
        required=("build_id", "job_id", "artifact_id", "provider_asset_ref", "rights_scope"),
        properties={
            "build_id": {
                "type": "string",
                "pattern": "^build_[0-9a-f]{32}$",
            },
            "job_id": {
                "type": "string",
                "pattern": "^render_job_[0-9a-f]{24}$",
            },
            "artifact_id": {"type": "string", "pattern": "^artifact_[A-Za-z0-9._-]+$"},
            "provider_asset_ref": STRING,
            "rights_scope": {"enum": ["authorized", "original", "licensed"]},
        },
    ),
    _verify_analysis_prepare,
)
_verify_run_schema = _object_schema(
    required=("build_id", "job_id", "artifact_id"),
    properties={
        "build_id": {
            "type": "string",
            "pattern": "^build_[0-9a-f]{32}$",
        },
        "job_id": {
            "type": "string",
            "pattern": "^render_job_[0-9a-f]{24}$",
        },
        "artifact_id": {"type": "string", "pattern": "^artifact_[A-Za-z0-9._-]+$"},
        "evidence_bundle": {"type": "object"},
        "observations": {"type": "array", "items": {"type": "object"}},
        "human_reviews": {"type": "array", "items": {"type": "object"}},
    },
)
_verify_run_schema["oneOf"] = [
    {
        "required": ["evidence_bundle"],
        "not": {"anyOf": [{"required": ["observations"]}, {"required": ["human_reviews"]}]},
    },
    {"required": ["observations"], "not": {"required": ["evidence_bundle"]}},
]
_register(
    "cpcs.verify.run",
    "Build evidence from normalized observations when needed, verify one render, and persist its hash-bound compliance report.",
    "operator",
    "operational",
    _verify_run_schema,
    _verify_run,
)
_round_trip_threshold_schema = _object_schema(
    required=(
        "minimum_trajectory_cosine_similarity",
        "maximum_translation_aligned_rmse",
        "maximum_duration_error_ratio",
        "maximum_path_length_ratio_error",
    ),
    properties={
        "minimum_trajectory_cosine_similarity": {
            "type": "number",
            "minimum": -1,
            "maximum": 1,
        },
        "maximum_translation_aligned_rmse": {"type": "number", "minimum": 0},
        "maximum_duration_error_ratio": {"type": "number", "minimum": 0},
        "maximum_path_length_ratio_error": {"type": "number", "minimum": 0},
    },
)
_register(
    "cpcs.verify.reference.roundtrip",
    "Compare exact source and generated pose batches against one hash-bound rendered artifact without claiming motion ground truth.",
    "operator",
    "operational",
    _object_schema(
        required=(
            "build_id",
            "job_id",
            "artifact_id",
            "reference_batch",
            "generated_batch",
            "actor_mapping",
            "joints",
            "thresholds",
        ),
        properties={
            "build_id": {
                "type": "string",
                "pattern": "^build_[0-9a-f]{32}$",
            },
            "job_id": {
                "type": "string",
                "pattern": "^render_job_[0-9a-f]{24}$",
            },
            "artifact_id": {"type": "string", "pattern": "^artifact_[0-9]{3}$"},
            "reference_batch": {"type": "object"},
            "generated_batch": {"type": "object"},
            "actor_mapping": {
                "type": "object",
                "minProperties": 1,
                "propertyNames": {"pattern": "^actor_[A-Z]+$"},
                "additionalProperties": {
                    "type": "string",
                    "pattern": "^actor_[A-Z]+$",
                },
            },
            "joints": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": STRING,
            },
            "thresholds": _round_trip_threshold_schema,
            "phase_samples": {"type": "integer", "minimum": 3, "maximum": 1001},
        },
    ),
    _verify_reference_round_trip,
)
_register(
    "cpcs.verify.reference.compare",
    "Compare two exact authorized local videos across cut timing, speech pace, detected 2D motion, and declared review lanes; persist an operational report and optional time-normalized contact sheet.",
    "operator",
    "operational",
    reference_candidate_comparison_request_schema(),
    _verify_reference_compare,
)
_measurement_interval_schema = _object_schema(
    required=("start_s", "end_s"),
    properties={
        "start_s": {"type": "number", "minimum": 0},
        "end_s": {"type": "number", "exclusiveMinimum": 0},
    },
)
_register(
    "cpcs.measure.pose.prepare",
    "Bind an authorized local video interval and pose model to one deterministic extraction job.",
    "operator",
    None,
    _object_schema(
        required=(
            "source_id",
            "asset_ref",
            "local_path",
            "rights_scope",
            "authorized_interval",
            "model_path",
            "model_version",
            "created_at",
        ),
        properties={
            "source_id": STRING,
            "asset_ref": STRING,
            "local_path": STRING,
            "rights_scope": {"enum": ["authorized", "original", "licensed"]},
            "authorized_interval": _measurement_interval_schema,
            "model_path": STRING,
            "model_version": STRING,
            "created_at": {"type": "string", "format": "date-time"},
            "num_poses": {"type": "integer", "minimum": 1, "maximum": 8},
            "stride": {"type": "integer", "minimum": 1, "maximum": 120},
            "keyframe_interval_s": {"type": "number", "exclusiveMinimum": 0},
            "min_visibility": {"type": "number", "minimum": 0, "maximum": 1},
            "min_detection_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
    ),
    _measure_pose_prepare,
)
_register(
    "cpcs.measure.pose.run",
    "Execute one hash-bound local pose job into an operational measurement candidate batch.",
    "operator",
    "operational",
    _object_schema(required=("job",), properties={"job": {"type": "object"}}),
    _measure_pose_run,
)
_register(
    "cpcs.measure.normalize",
    "Normalize explicitly selected immutable measurements for Video Observation Graph fusion.",
    "operator",
    None,
    _object_schema(
        required=("source", "authorized_interval", "measurement_observation_ids"),
        properties={
            "source": _object_schema(
                required=("source_id", "asset_ref", "sha256"),
                properties={
                    "source_id": STRING,
                    "asset_ref": STRING,
                    "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                },
            ),
            "authorized_interval": _measurement_interval_schema,
            "measurement_observation_ids": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {"type": "string", "pattern": "^measurement_obs_"},
            },
        },
    ),
    _measure_normalize,
)
RESEARCH_SESSION_ID = {
    "type": "string",
    "pattern": "^research_session_[0-9a-f]{24}$",
}
RESEARCH_PACKET_ID = {
    "type": "string",
    "pattern": "^packet_[0-9a-f]{24}$",
}
RESEARCH_EXTRACTOR = _object_schema(
    required=("agent", "model", "prompt_hash"),
    properties={
        "agent": STRING,
        "model": STRING,
        "prompt_hash": {
            "type": "string",
            "pattern": "^sha256:[0-9a-f]{64}$",
        },
    },
)
_semantic_extraction_response_schema = load_schema("semantic_extraction_response")
_research_packet_result_schema = copy.deepcopy(
    _semantic_extraction_response_schema["$defs"]["packetResult"]
)
_research_packet_result_defs = {
    key: copy.deepcopy(_semantic_extraction_response_schema["$defs"][key])
    for key in ("candidate", "evidenceRef", "noCandidate")
}
_research_configuration_override_schema = copy.deepcopy(
    load_schema("source_extraction_bundle")["$defs"]["configuration"]
)
_research_configuration_override_schema.pop("required", None)
_research_configuration_schema = {
    "oneOf": [
        {"type": "null"},
        _research_configuration_override_schema,
    ]
}
_retrieved_passages_schema = copy.deepcopy(load_schema("retrieved_passages"))
_retrieved_passages_schema.pop("$schema", None)
_retrieved_passages_schema.pop("$id", None)
_research_register_schema = _object_schema(
    required=("source_kind", "extractor", "registered_at"),
    properties={
        "source_kind": {"enum": ["authorized_folder", "polymath_passages"]},
        "folder": STRING,
        "research_goal": STRING,
        "rights_basis": STRING,
        "retrieved_passages": _retrieved_passages_schema,
        "extractor": RESEARCH_EXTRACTOR,
        "registered_at": {"type": "string", "format": "date-time"},
        "configuration": _research_configuration_schema,
    },
)
_research_register_schema["oneOf"] = [
    {
        "properties": {"source_kind": {"const": "authorized_folder"}},
        "required": ["folder", "research_goal", "rights_basis"],
        "not": {"required": ["retrieved_passages"]},
    },
    {
        "properties": {"source_kind": {"const": "polymath_passages"}},
        "required": ["retrieved_passages"],
        "not": {
            "anyOf": [
                {"required": ["folder"]},
                {"required": ["research_goal"]},
                {"required": ["rights_basis"]},
            ]
        },
    },
]
_research_session_schema = _object_schema(
    required=("session_id",), properties={"session_id": RESEARCH_SESSION_ID}
)
_research_delta_request_schema = copy.deepcopy(load_schema("research_delta_request"))
_research_delta_request_schema.pop("$schema", None)
_research_delta_request_schema.pop("$id", None)
_research_delta_request_defs = _research_delta_request_schema.pop("$defs")
_research_delta_prepare_schema = _object_schema(
    required=("request",),
    properties={"request": _research_delta_request_schema},
)
_research_delta_prepare_schema["$defs"] = _research_delta_request_defs
_research_delta_id = {
    "type": "string",
    "pattern": "^research_delta_[0-9a-f]{24}$",
}
_research_delta_patch_request_schema = copy.deepcopy(
    load_schema("research_delta_patch_request")
)
_research_delta_patch_request_schema.pop("$schema", None)
_research_delta_patch_request_schema.pop("$id", None)
_research_delta_patch_prepare_schema = _object_schema(
    required=("request",),
    properties={"request": _research_delta_patch_request_schema},
)
_research_delta_patch_execution_id = {
    "type": "string",
    "pattern": "^research_patch_[0-9a-f]{24}$",
}
_register(
    "cpcs.research.source.register",
    "Register exact authorized source evidence and open a resumable external-LLM extraction session.",
    "operator",
    "operational",
    _research_register_schema,
    _research_source_register,
)
_register(
    "cpcs.research.source.inspect",
    "Inspect registered source orientation, ledger, hashes, and trust boundary.",
    "operator",
    None,
    _research_session_schema,
    _research_source_inspect,
)
_register(
    "cpcs.research.source.units.admit",
    "Append every hash-verified completed-session passage to the immutable local source-unit registry and rebuild source closure.",
    "curator",
    "immutable_and_derived",
    _research_session_schema,
    _research_source_units_admit,
    authorization_required=True,
)
_register(
    "cpcs.research.packet.list",
    "List bounded semantic packets and their captured-response status.",
    "operator",
    None,
    _research_session_schema,
    _research_packet_list,
)
_register(
    "cpcs.research.packet.read",
    "Read one exact source-located packet for an MCP-connected semantic worker.",
    "operator",
    None,
    _object_schema(
        required=("session_id", "packet_id"),
        properties={
            "session_id": RESEARCH_SESSION_ID,
            "packet_id": RESEARCH_PACKET_ID,
        },
    ),
    _research_packet_read,
)
_research_extraction_submit_schema = _object_schema(
    required=("session_id", "packet_result", "submitted_at"),
    properties={
        "session_id": RESEARCH_SESSION_ID,
        "packet_result": _research_packet_result_schema,
        "submitted_at": {"type": "string", "format": "date-time"},
    },
)
_research_extraction_submit_schema["$defs"] = _research_packet_result_defs
_register(
    "cpcs.research.extraction.submit",
    "Capture one source-closed candidate result or explicit evidence-linked no-candidate disposition, then assemble proposals only when all packets arrive.",
    "operator",
    "operational",
    _research_extraction_submit_schema,
    _research_extraction_submit,
)
_register(
    "cpcs.research.extraction.status",
    "Read packet progress, captured hashes, and the current authority boundary.",
    "operator",
    None,
    _research_session_schema,
    _research_extraction_status,
)
_register(
    "cpcs.research.coverage.inspect",
    "Inspect section dispositions, omissions, placement gaps, and disagreements.",
    "operator",
    None,
    _research_session_schema,
    _research_coverage_inspect,
)
_register(
    "cpcs.research.proposals.list",
    "List source-bound untrusted extraction proposals without staging them.",
    "operator",
    None,
    _research_session_schema,
    _research_proposals_list,
)
_register(
    "cpcs.research.proposals.validate",
    "Run deterministic schema, identity, and evidence checks without authority mutation.",
    "operator",
    None,
    _research_session_schema,
    _research_proposals_validate,
)
_register(
    "cpcs.research.distillation.run",
    "Run the shared deterministic distiller for one completed session and write staging only.",
    "operator",
    "staging",
    _research_session_schema,
    _research_distillation_run,
)
_register(
    "cpcs.research.placement.plan",
    "Resolve one staged run into replay-stable identity, ontology, graph, control, metric, source, index, and projection decisions without curated mutation.",
    "operator",
    "staging",
    _object_schema(
        required=("run_id", "durable_ids"),
        properties={
            "run_id": {
                "type": "string",
                "pattern": "^distill_[0-9a-f]{24}$",
            },
            "durable_ids": {
                "type": "object",
                "propertyNames": {
                    "pattern": "^proposal_[A-Za-z0-9._-]+$"
                },
                "additionalProperties": STRING,
            },
            "terminology_proposal_ids": {
                "type": "object",
                "propertyNames": {
                    "pattern": "^proposal_[A-Za-z0-9._-]+$"
                },
                "additionalProperties": TERMINOLOGY_PROPOSAL_IDS,
            },
        },
    ),
    _research_placement_plan,
)
_register(
    "cpcs.research.placement.inspect",
    "Rehash and inspect one staged ontology placement and graph-growth plan against current registries and authority.",
    "operator",
    None,
    _object_schema(
        required=("plan_id",),
        properties={
            "plan_id": {
                "type": "string",
                "pattern": "^growth_[0-9a-f]{24}$",
            }
        },
    ),
    _research_placement_inspect,
)
_register(
    "cpcs.research.promotion.prepare",
    "Read staged proposals and explicit review requirements before separate curator promotion.",
    "operator",
    None,
    _research_session_schema,
    _research_promotion_prepare,
)
_register(
    "cpcs.research.delta.prepare",
    "Resolve completed source-bound claim proposals into a deterministic existing-owner impact plan without changing code or authority.",
    "operator",
    "operational",
    _research_delta_prepare_schema,
    _research_delta_prepare,
)
_register(
    "cpcs.research.delta.inspect",
    "Read and rehash one content-addressed research implementation proposal.",
    "operator",
    None,
    _object_schema(
        required=("delta_id",),
        properties={"delta_id": _research_delta_id},
    ),
    _research_delta_inspect,
)
_register(
    "cpcs.research.delta.patch.prepare",
    "Capture an approved-proposal unified diff, verify its exact hash and closed path scope, and prepare a content-addressed execution without running code.",
    "operator",
    "operational",
    _research_delta_patch_prepare_schema,
    _research_delta_patch_prepare,
)
_register(
    "cpcs.research.delta.patch.execute",
    "Apply one request-bound patch in a detached isolated worktree and run only fixed owner and repository gates without merge, push, or promotion.",
    "curator",
    "operational",
    _object_schema(
        required=("execution_id",),
        properties={"execution_id": _research_delta_patch_execution_id},
    ),
    _research_delta_patch_execute,
)
_register(
    "cpcs.research.delta.patch.inspect",
    "Rehash the captured patch, replay state, gate receipt, logs, and optional cleanup record.",
    "operator",
    None,
    _object_schema(
        required=("execution_id",),
        properties={"execution_id": _research_delta_patch_execution_id},
    ),
    _research_delta_patch_inspect,
)
_register(
    "cpcs.research.delta.patch.discard",
    "Remove only the exact isolated patch worktree while preserving its request, logs, state, and receipt.",
    "curator",
    "operational",
    _object_schema(
        required=("execution_id",),
        properties={"execution_id": _research_delta_patch_execution_id},
    ),
    _research_delta_patch_discard,
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
    mcp_exposed=False,
)
_register(
    "cpcs.distill.run",
    "Run deterministic admission and append staging decisions only.",
    "operator",
    "staging",
    _object_schema(required=("batch",), properties={"batch": {"type": "object"}}),
    _distill_run,
    mcp_exposed=False,
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
_experiment_delta_schema = _object_schema(
    required=("concept_id", "control_id", "value"),
    properties={
        "concept_id": {"type": "string", "pattern": "^c_"},
        "control_id": {
            "type": "string",
            "pattern": "^control_[0-9a-f]{16}$",
        },
        "value": {},
    },
)
_register(
    "cpcs.experiment.prepare",
    "Prepare a validated experiment draft from exact materialized build identities and one declared design.",
    "operator",
    None,
    _object_schema(
        required=(
            "flight_id",
            "arms",
            "classification",
            "metric_ids",
            "outcome_concept_ids",
            "provider",
            "model_version",
            "sealed_at",
        ),
        properties={
            "flight_id": {
                "type": "string",
                "pattern": "^flight_[A-Za-z0-9._-]+$",
            },
            "arms": {
                "type": "array",
                "minItems": 1,
                "items": _object_schema(
                    required=("id", "build_id", "tested_delta"),
                    properties={
                        "id": STRING,
                        "build_id": {
                            "type": "string",
                            "pattern": "^build_[0-9a-f]{32}$",
                        },
                        "tested_delta": {
                            "oneOf": [
                                {"type": "null"},
                                _experiment_delta_schema,
                            ]
                        },
                    },
                ),
            },
            "classification": {
                "enum": ["isolated_comparison", "bundled_observation"]
            },
            "metric_ids": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": STRING,
            },
            "outcome_concept_ids": {
                "type": "array",
                "uniqueItems": True,
                "items": {"type": "string", "pattern": "^c_"},
            },
            "provider": STRING,
            "model_version": STRING,
            "sealed_at": {"type": "string", "format": "date-time"},
        },
    ),
    _experiment_prepare,
)
_register(
    "cpcs.experiment.seal",
    "Seal one prepared experiment draft into append-only immutable authority.",
    "curator",
    "immutable",
    _object_schema(
        required=("flight_draft",),
        properties={"flight_draft": {"type": "object"}},
    ),
    _experiment_seal,
)
_register(
    "cpcs.experiment.accept",
    "Accept one complete isolated experiment, admit every reviewed arm, invoke existing reflection, stage typed findings, and record an exact replay receipt.",
    "curator",
    "immutable",
    _object_schema(
        required=("request",),
        properties={"request": load_schema("accepted_experiment_request")},
    ),
    _experiment_accept,
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
    "cpcs.record.testimonial.capture",
    "Capture an exact human statement against hash-verified render bytes.",
    "curator",
    "immutable",
    _object_schema(
        required=("request",),
        properties={"request": load_schema("human_testimonial_capture")},
    ),
    _record_testimonial_capture,
)
_register(
    "cpcs.record.testimonial.review",
    "Append one source-spanned normalization of a current human testimonial.",
    "curator",
    "immutable",
    _object_schema(
        required=("request",),
        properties={"request": load_schema("testimonial_review_request")},
    ),
    _record_testimonial_review,
)
_register(
    "cpcs.testimonial.inspect",
    "Inspect exact testimonial and reviewed-normalization correction lineage.",
    "operator",
    None,
    _object_schema(
        required=("testimonial_id",),
        properties={
            "testimonial_id": {
                "type": "string",
                "pattern": "^testimonial_[0-9a-f]{24}$",
            }
        },
    ),
    _testimonial_inspect,
)
_register(
    "cpcs.record.measurement",
    "Append one reviewed pose measurement batch to immutable evidence.",
    "curator",
    "immutable",
    _object_schema(required=("batch",), properties={"batch": {"type": "object"}}),
    _record_measurement,
)
_register(
    "cpcs.reflect.rebuild",
    "Rebuild disposable learned state from curated and immutable stores.",
    "operator",
    "derived",
    _object_schema(),
    _reflect_rebuild,
)
_register(
    "cpcs.qualification.stability.evaluate",
    "Evaluate calibration drift and held-out recursive optimization collapse without qualifying or promoting anything.",
    "operator",
    "operational",
    _object_schema(
        required=("request",),
        properties={"request": load_release_schema("evaluator_stability_request")},
    ),
    _qualification_stability_evaluate,
)
_register(
    "cpcs.qualification.stability.inspect",
    "Inspect one exact-replay evaluator stability report and its qualification readiness.",
    "operator",
    None,
    _object_schema(
        required=("report_id",),
        properties={
            "report_id": {
                "type": "string",
                "pattern": "^stability_[0-9a-f]{24}$",
            }
        },
    ),
    _qualification_stability_inspect,
)


_register(
    "cpcs.reasoning.experimental.plan",
    "Run the experimental CPCS reasoning layer over one normalized intent and produce a traceable CPCSReasoningTreatmentPacket with repo-native overlay translation (no provider contact, no score mutation).",
    "chat",
    None,
    _object_schema(
        required=("intent_text",),
        properties={
            "intent_text": {"type": "string", "minLength": 1, "maxLength": 8000},
        },
    ),
    handler_reasoning_experimental_plan,
)
_register(
    "cpcs.reasoning.experiment.prepare",
    "Prepare a reasoning_layer_ab experiment plan: arm A CURRENT_BASELINE vs arm B CPCS_REASONING_V1 through the SAME compiler and evaluation path, with one isolated upstream treatment factor.",
    "operator",
    None,
    _object_schema(
        required=("flight_id", "intent_text"),
        properties={
            "flight_id": {"type": "string", "pattern": "^flight_[A-Za-z0-9._-]+$"},
            "intent_text": {"type": "string", "minLength": 1, "maxLength": 8000},
            "provider": STRING,
            "model_version": STRING,
            "duration_seconds": {"type": "integer", "minimum": 1},
            "aspect_ratio": STRING,
            "resolution": STRING,
            "seed": {"type": "integer", "minimum": 0},
            "generation_count": {"type": "integer", "minimum": 1},
            "project_id": STRING,
        },
    ),
    handler_reasoning_experiment_prepare,
)
_register(
    "cpcs.reasoning.experiment.inspect",
    "Inspect one reasoning_layer_ab experiment plan without provider contact.",
    "chat",
    None,
    _object_schema(
        required=("flight_id", "intent_text"),
        properties={
            "flight_id": {"type": "string", "pattern": "^flight_[A-Za-z0-9._-]+$"},
            "intent_text": {"type": "string", "minLength": 1, "maxLength": 8000},
            "provider": STRING,
            "model_version": STRING,
        },
    ),
    handler_reasoning_experiment_inspect,
)
_register(
    "cpcs.repair.gap.prepare",
    "Build a DiscrepancyPacket from ExpectedStateContract, observation evidence, and an optional user complaint, with epistemic classes kept separate.",
    "chat",
    None,
    _object_schema(
        required=("expected_states",),
        properties={
            "expected_states": {"type": "array", "minItems": 1},
            "observations": {"type": "array"},
            "user_complaint": {"type": "string", "maxLength": 4000},
            "source": {"type": "object"},
        },
    ),
    handler_repair_gap_prepare,
)
_register(
    "cpcs.repair.plan",
    "Run REPAIR_GAP reasoning over one DiscrepancyPacket, produce a traceable RepairControlPlan, and apply it through the existing score compiler as revised generation_v2.",
    "operator",
    None,
    _object_schema(
        required=("intent_text", "discrepancy_packet"),
        properties={
            "intent_text": {"type": "string", "minLength": 1, "maxLength": 8000},
            "discrepancy_packet": {"type": "object"},
            "project_id": STRING,
        },
    ),
    handler_repair_plan,
)
_register(
    "cpcs.repair.inspect",
    "Inspect one repair plan and its revised build request without provider contact.",
    "chat",
    None,
    _object_schema(
        required=("intent_text", "discrepancy_packet"),
        properties={
            "intent_text": {"type": "string", "minLength": 1, "maxLength": 8000},
            "discrepancy_packet": {"type": "object"},
            "project_id": STRING,
        },
    ),
    handler_repair_inspect,
)

_register(
    "cpcs.deliberate.plan",
    "Run knowledge-grounded deliberation over one request: observations, knowledge activation, hypotheses, hypothesis-driven query steering, evidence updates, and bounded reasoning closure (read-only).",
    "chat",
    None,
    _object_schema(
        required=("intent_text",),
        properties={
            "intent_text": {"type": "string", "minLength": 1, "maxLength": 8000},
            "llm_proposals": {"type": "array"},
        },
    ),
    handler_deliberate_plan,
)
_register(
    "cpcs.deliberate.inspect",
    "Inspect one deliberation result (hypotheses, queries, closure) without provider contact.",
    "chat",
    None,
    _object_schema(
        required=("intent_text",),
        properties={
            "intent_text": {"type": "string", "minLength": 1, "maxLength": 8000},
            "llm_proposals": {"type": "array"},
        },
    ),
    handler_deliberate_inspect,
)
_register(
    "cpcs.ideate",
    "Explore grounded creative interpretations in IDEATION mode; candidates remain hypotheses, never mandatory requirements (read-only).",
    "chat",
    None,
    _object_schema(
        required=("intent_text",),
        properties={
            "intent_text": {"type": "string", "minLength": 1, "maxLength": 8000},
        },
    ),
    handler_ideate,
)
_register(
    "cpcs.hypotheses.inspect",
    "Inspect the hypothesis set of one deliberation.",
    "chat",
    None,
    _object_schema(
        required=("intent_text",),
        properties={
            "intent_text": {"type": "string", "minLength": 1, "maxLength": 8000},
            "llm_proposals": {"type": "array"},
        },
    ),
    handler_hypotheses_inspect,
)
_register(
    "cpcs.query.plan.inspect",
    "Inspect the hypothesis-driven query steering plan of one deliberation.",
    "chat",
    None,
    _object_schema(
        required=("intent_text",),
        properties={
            "intent_text": {"type": "string", "minLength": 1, "maxLength": 8000},
            "llm_proposals": {"type": "array"},
        },
    ),
    handler_query_plan_inspect,
)
_register(
    "cpcs.reasoning.closure.inspect",
    "Inspect the bounded reasoning closure packet of one deliberation.",
    "chat",
    None,
    _object_schema(
        required=("intent_text",),
        properties={
            "intent_text": {"type": "string", "minLength": 1, "maxLength": 8000},
            "llm_proposals": {"type": "array"},
        },
    ),
    handler_reasoning_closure_inspect,
)

_register(
    "cpcs.guided.start",
    "Start a guided prompting session: run CPCS deliberation, produce the compressed user-facing projection, and select GUIDED/FAST/AUTO interaction mode (read-only; session state kept per process).",
    "chat",
    None,
    _object_schema(
        required=("intent_text",),
        properties={
            "intent_text": {"type": "string", "minLength": 1, "maxLength": 8000},
            "mode": {"enum": ["GUIDED", "FAST", "AUTO"]},
            "duration_seconds": {"type": "number", "minimum": 0.5},
        },
    ),
    handler_guided_start,
)
_register(
    "cpcs.guided.project",
    "Reproject the current guided session revision into the compressed user-facing projection.",
    "chat",
    None,
    _object_schema(
        required=("session_id",),
        properties={"session_id": {"type": "string", "minLength": 1}},
    ),
    handler_guided_project,
)
_register(
    "cpcs.guided.answer",
    "Record a user answer to a guided choice, with source attribution and FAST-transition detection.",
    "chat",
    None,
    _object_schema(
        required=("session_id", "answer_text"),
        properties={
            "session_id": {"type": "string", "minLength": 1},
            "answer_text": {"type": "string", "minLength": 1, "maxLength": 4000},
            "choice_id": {"type": "string"},
            "question_id": {"type": "string"},
        },
    ),
    handler_guided_answer,
)
_register(
    "cpcs.guided.finish",
    "Finish without clarification: apply safe inference and permitted defaults, respect all HARD semantics, and emit the final prompt package through the existing compiler path.",
    "chat",
    None,
    _object_schema(
        required=("session_id",),
        properties={"session_id": {"type": "string", "minLength": 1}},
    ),
    handler_guided_finish,
)
_register(
    "cpcs.guided.revise",
    "Apply a user correction as a new immutable revision with targeted invalidation of affected reasoning only.",
    "chat",
    None,
    _object_schema(
        required=("session_id", "correction"),
        properties={
            "session_id": {"type": "string", "minLength": 1},
            "correction": {"type": "string", "minLength": 1, "maxLength": 4000},
        },
    ),
    handler_guided_revise,
)
_register(
    "cpcs.guided.inspect",
    "Inspect the guided session: projection, hidden reasoning summary, decisions, and diagnostics.",
    "chat",
    None,
    _object_schema(
        required=("session_id",),
        properties={"session_id": {"type": "string", "minLength": 1}},
    ),
    handler_guided_inspect,
)
_register(
    "cpcs.session.inspect",
    "Inspect one guided session state.",
    "chat",
    None,
    _object_schema(
        required=("session_id",),
        properties={"session_id": {"type": "string", "minLength": 1}},
    ),
    handler_session_inspect,
)
_register(
    "cpcs.session.history",
    "Read the immutable revision history of one guided session.",
    "chat",
    None,
    _object_schema(
        required=("session_id",),
        properties={"session_id": {"type": "string", "minLength": 1}},
    ),
    handler_session_history,
)
_register(
    "cpcs.doctor",
    "Run the guided-prompting health check; provider generation is optional and does not gate readiness.",
    "chat",
    None,
    _object_schema(),
    handler_doctor,
)
_register(
    "cpcs.knowledge.apply.inspect",
    "Inspect the KA-1 knowledge application bridge result for one intent: principle packs, representation decisions, set hash, and lineage, without provider contact (read-only; fails closed without the frozen runtime).",
    "chat",
    None,
    _object_schema(
        required=("intent_text",),
        properties={
            "intent_text": {"type": "string", "minLength": 1, "maxLength": 8000},
        },
    ),
    handler_knowledge_apply_inspect,
)

def _bootstrap(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return _bootstrap_run(arguments, root)


_register(
    "cpcs.bootstrap",
    "Idempotent first-run setup: locate and validate the external frozen CPCS runtime, write machine-local configuration only (no secrets), and run the health check. Provider credentials are not required.",
    "operator",
    None,
    _object_schema(
        properties={
            "runtime": {"type": "string", "minLength": 1, "maxLength": 2000},
        },
    ),
    _bootstrap,
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
            "authorization_required": spec.authorization_required
            or spec.required_role == "curator",
            "input_schema": copy.deepcopy(spec.input_schema),
            "mcp_exposed": spec.mcp_exposed,
        }
        for spec in sorted(OPERATIONS.values(), key=lambda item: item.name)
        if ROLE_LEVEL[role] >= ROLE_LEVEL[spec.required_role]
    ]


def authorization_request_hash(operation: str, arguments: dict[str, Any]) -> str:
    return sha256_value(
        {"schema": REQUEST_SCHEMA, "operation": operation, "arguments": arguments}
    )


def _enforce_release_limits(
    operation: str, arguments: dict[str, Any], root: Path
) -> None:
    policy, _ = load_release_policy(root)
    limits = policy["limits"]
    token_budget = arguments.get("token_budget")
    if token_budget is not None and token_budget > limits["context_token_budget"]:
        raise ValueError(
            f"token_budget exceeds release limit {limits['context_token_budget']}"
        )
    evidence = arguments.get("external_evidence")
    if isinstance(evidence, list) and len(evidence) > limits["external_evidence_items"]:
        raise ValueError(
            "external_evidence exceeds release item limit "
            f"{limits['external_evidence_items']}"
        )
    if operation in {"cpcs.build.compile", "cpcs.build.materialize"} and isinstance(
        arguments.get("request"), dict
    ):
        settings = arguments["request"].get("settings", {})
        samples = settings.get("sample_count")
        duration = settings.get("duration_seconds")
        if isinstance(samples, int) and isinstance(duration, int):
            if samples * duration > limits["generation_seconds_per_request"]:
                raise ValueError("provider build exceeds generation-seconds release limit")
    if operation == "cpcs.production.prepare":
        samples = arguments.get("sample_count", 1)
        duration = arguments.get("duration_seconds", 8)
        if samples * duration > limits["generation_seconds_per_request"]:
            raise ValueError("production preparation exceeds generation-seconds release limit")
    if operation == "cpcs.render.create":
        timeout = arguments.get("timeout_seconds", 3600)
        if timeout > limits["render_timeout_seconds"]:
            raise ValueError("render timeout exceeds release limit")
    if operation in {"cpcs.analyze.run", "cpcs.analyze.cascade"}:
        job = arguments.get("job", arguments.get("cascade", {}))
        if not isinstance(job, dict):
            return
        items = job.get("items", [])
        if isinstance(items, list) and len(items) > limits["provider_batch_items"]:
            raise ValueError("analysis batch exceeds release item limit")
        intervals = [job.get("interval", job.get("authorized_interval"))]
        if isinstance(items, list):
            intervals.extend(
                item.get("interval") for item in items if isinstance(item, dict)
            )
        total = 0.0
        for interval in intervals:
            if not isinstance(interval, dict):
                continue
            start = interval.get("source_start_s", interval.get("start_s"))
            end = interval.get("source_end_s", interval.get("end_s"))
            if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                total += max(0.0, float(end) - float(start))
        if total > limits["analysis_seconds_per_request"]:
            raise ValueError("analysis duration exceeds release limit")
    if operation == "cpcs.measure.pose.run" and isinstance(arguments.get("job"), dict):
        interval = arguments["job"].get("authorized_interval", {})
        start = interval.get("start_s")
        end = interval.get("end_s")
        if (
            isinstance(start, (int, float))
            and isinstance(end, (int, float))
            and end - start > limits["analysis_seconds_per_request"]
        ):
            raise ValueError("measurement duration exceeds release limit")


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
    authorization_required: bool,
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
            "authorization_required": authorization_required,
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
    telemetry: Any | None = None,
) -> dict[str, Any]:
    """Validate, authorize, and execute one application request."""
    if role not in ROLE_LEVEL:
        raise ValueError(f"unknown client role: {role}")
    started = time.perf_counter()
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
    authorization_required = bool(
        spec and (spec.authorization_required or spec.required_role == "curator")
    )
    authorization_id = (
        request.get("authorization", {}).get("authorization_id")
        if isinstance(request, dict)
        and isinstance(request.get("authorization"), dict)
        else None
    )
    try:
        validate_application_instance("application_request", request, root)
        if spec is None:
            raise LookupError(f"unknown CPCS operation: {operation}")
        if ROLE_LEVEL[role] < ROLE_LEVEL[spec.required_role]:
            raise PermissionError(
                f"{operation} requires the {spec.required_role} role; granted role is {role}"
            )
        if not authorization_required and request.get("authorization") is not None:
            raise ValueError(
                "explicit authorization is accepted only for controlled side effects"
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
        _enforce_release_limits(operation, request["arguments"], root)
        if authorization_required:
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
        response = _response(
            request_id=request_id,
            operation=operation,
            status="success",
            required_role=required_role,
            granted_role=role,
            mutation_scope=mutation_scope,
            authorization_required=authorization_required,
            result=result,
            error=None,
            root=root,
        )
        if telemetry is not None:
            telemetry.record(
                trace_id=response["request_id"],
                operation=response["operation"],
                status=response["status"],
                role=role,
                mutation_scope=mutation_scope,
                duration_ms=(time.perf_counter() - started) * 1000,
                authorization_id=authorization_id,
            )
        return response
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
    response = _response(
        request_id=request_id,
        operation=operation,
        status="error",
        required_role=required_role,
        granted_role=role,
        mutation_scope=mutation_scope,
        authorization_required=authorization_required,
        result=None,
        error={"code": code, "message": message},
        root=root,
    )
    if telemetry is not None:
        telemetry.record(
            trace_id=response["request_id"],
            operation=response["operation"],
            status=response["status"],
            role=role,
            mutation_scope=mutation_scope,
            duration_ms=(time.perf_counter() - started) * 1000,
            authorization_id=authorization_id,
        )
    return response
