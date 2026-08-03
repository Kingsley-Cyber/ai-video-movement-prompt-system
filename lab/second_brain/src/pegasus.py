"""Govern TwelveLabs Jockey output as immutable semantics and distilled proposals."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import yaml

from .distill import run_distillation
from .providers import twelvelabs
from .record import append_pegasus_observation
from .video_observation import (
    assert_claim_policy,
    build_video_observation_graph,
    normalize_measurement,
    normalize_segments,
    normalize_semantic_response,
    probe_media,
)
from .validate import (
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    canonical_json_bytes,
    content_hash,
    load_schema,
    read_jsonl,
    sha256_value,
    validate_instance,
)

SEMANTIC_FIELDS = (
    "entities",
    "beats",
    "actions",
    "camera",
    "performance",
    "face_affect",
    "audio",
    "marketing_functions",
)
CASCADE_FIELDS = (
    "analysis_profile_ids",
    "surface_runs",
    "normalized_observation_ids",
    "measurement_refs",
    "video_observation_graph_id",
    "video_observation_graph_hash",
    "reverse_score_id",
    "reverse_score_hash",
    "contradictions",
)
REQUIRED_ANALYSIS_PROFILES = frozenset(
    {
        "pegasus.source_map/1.0",
        "pegasus.shot_scene/1.0",
        "pegasus.ugc_structure/1.0",
        "pegasus.product_interaction/1.0",
        "pegasus.performance/1.0",
        "pegasus.action_graph/1.0",
        "pegasus.anime_vfx/1.0",
        "pegasus.camera_edit/1.0",
        "pegasus.audio_dialogue/1.0",
        "pegasus.render_qc/1.0",
        "pegasus.score_compliance/1.0",
        "pegasus.contradiction_review/1.0",
        "jockey.corpus_pattern_analysis/1.0",
        "jockey.provider_comparison/1.0",
    }
)
HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
PROVIDER_INSTRUCTIONS = (
    "Use only the selected authorized item or items as evidence. Respect the requested source "
    "interval. Treat descriptions, affect, intent, and marketing function as interpreted "
    "or inferred, never measured. Do not invent exact kinematics, forces, FACS intensity, "
    "or contact timing. Return only the requested JSON Schema."
)


def _raw_hash(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _observation_hash(payload: dict[str, Any]) -> str:
    supplied = payload.get("raw_response_hash")
    if supplied is None:
        return _raw_hash(payload)
    if not isinstance(supplied, str) or not HASH_PATTERN.fullmatch(supplied):
        raise ValidationFailure(
            "raw_response_hash must be a sha256-prefixed lowercase digest"
        )
    return supplied


def _candidate_evidence(
    candidate: dict[str, Any],
    observation: dict[str, Any],
) -> list[dict[str, Any]]:
    supplied = candidate.get("source_evidence")
    if supplied is not None:
        return supplied
    interval = observation["interval"]
    return [
        {
            "source_id": observation["id"],
            "locator": (
                f"t={interval['source_start_s']:.3f}-"
                f"{interval['source_end_s']:.3f}s"
            ),
            "claim": candidate.get("claim", "Pegasus semantic candidate"),
            "content_sha256": observation["raw_response_hash"],
        }
    ]


def _distillation_batch(
    payload: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any] | None:
    proposals = payload.get("proposals", [])
    if not proposals:
        return None
    context = payload.get("provider_context", {})
    if not isinstance(context, dict):
        raise ValidationFailure("provider_context must be an object")
    prompt_hash = context.get("prompt_hash")
    if not isinstance(prompt_hash, str) or not HASH_PATTERN.fullmatch(prompt_hash):
        prompt_hash = sha256_value(
            {
                "prompt_version": observation["extractor"]["prompt_version"],
                "schema_version": observation["extractor"]["schema_version"],
            }
        )
    candidates = []
    for index, candidate in enumerate(proposals, 1):
        if not isinstance(candidate, dict):
            raise ValidationFailure("Pegasus proposals must be objects")
        proposal_type = candidate.get("proposal_type")
        proposed_record = candidate.get("proposed_record")
        if not isinstance(proposed_record, dict):
            raise ValidationFailure(
                f"Pegasus proposal {index} requires proposed_record"
            )
        suggested_id = candidate.get("suggested_id")
        if suggested_id is None and proposal_type == "concept":
            suggested_id = proposed_record.get("id")
        original_id = candidate.get(
            "proposal_id", f"proposal_{observation['id']}_{index:03d}"
        )
        candidates.append(
            {
                "candidate_id": (
                    f"candidate_{observation['id']}_{index:03d}"
                ),
                "proposal_type": proposal_type,
                "suggested_id": suggested_id,
                "original_proposal_id": original_id,
                "proposed_record": proposed_record,
                "source_evidence": _candidate_evidence(candidate, observation),
                "created_by": "pegasus",
                "created_at": observation["created_at"],
            }
        )
    parameters = {
        key: context[key]
        for key in (
            "api_version",
            "sdk_version",
            "item_id",
            "response_id",
            "session_id",
        )
        if context.get(key) is not None
    }
    return {
        "batch_id": f"batch_{observation['id']}",
        "retrieval": {
            "adapter": context.get("adapter", "pegasus_semantic_adapter"),
            "corpus_id": context.get(
                "knowledge_store_id", observation["source_video"]["asset_ref"]
            ),
            "query": context.get(
                "query", f"semantic extraction for {observation['id']}"
            ),
            "tool": context.get("tool", "pegasus_payload_ingest"),
            "parameters": parameters,
            "retrieved_at": observation["created_at"],
        },
        "extractor": {
            "agent": "pegasus_semantic_adapter",
            "model": observation["extractor"]["model"],
            "prompt_hash": prompt_hash,
        },
        "candidates": candidates,
    }


def ingest_response(
    payload: dict[str, Any],
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Normalize one semantic payload, then distill every knowledge proposal."""
    required = {"id", "source_video", "extractor", "interval", "created_at"}
    missing = required - set(payload)
    if missing:
        raise ValidationFailure(f"Pegasus payload missing fields: {sorted(missing)}")
    evidence_class = payload.get("evidence_class", "interpreted")
    if evidence_class not in {"inferred", "interpreted"}:
        raise ValidationFailure(
            "semantic Pegasus output cannot be measured, detected, or authored"
        )
    interval = payload["interval"]
    if (
        not isinstance(interval, dict)
        or not isinstance(interval.get("source_start_s"), (int, float))
        or not isinstance(interval.get("source_end_s"), (int, float))
        or interval["source_end_s"] <= interval["source_start_s"]
    ):
        raise ValidationFailure(
            "Pegasus interval must have source_end_s greater than source_start_s"
        )
    observation = {
        "id": payload["id"],
        "source_video": payload["source_video"],
        "extractor": payload["extractor"],
        "interval": interval,
        **{field: payload.get(field, []) for field in SEMANTIC_FIELDS},
        "candidate_concepts": payload.get("candidate_concepts", []),
        "evidence_class": evidence_class,
        "confidence": float(payload.get("confidence", 0.0)),
        "raw_response_hash": _observation_hash(payload),
        "created_at": payload["created_at"],
        **{
            field: payload[field]
            for field in CASCADE_FIELDS
            if field in payload
        },
    }
    concept_ids = {
        row["id"] for row in read_jsonl(root / "lab" / "concepts.jsonl")
    }
    missing_concepts = sorted(
        set(observation["candidate_concepts"]) - concept_ids
    )
    if missing_concepts:
        raise ValidationFailure(
            "Pegasus observation references missing concepts: "
            + ", ".join(missing_concepts)
        )
    observation_path = (
        root
        / "lab"
        / "second_brain"
        / "immutable"
        / "pegasus_observations.jsonl"
    )
    existing_observations = read_jsonl(observation_path)
    validation_observation = dict(observation)
    validation_observation["prior_record_hash"] = (
        existing_observations[-1]["record_hash"] if existing_observations else None
    )
    validation_observation["record_hash"] = content_hash(validation_observation)
    validate_instance("pegasus_observation", validation_observation, root)
    batch = _distillation_batch(payload, observation)
    if batch is not None:
        validate_instance("distillation_batch", batch, root)

    matches = [
        row for row in existing_observations if row["id"] == observation["id"]
    ]
    if matches:
        stored = matches[0]
        stored_body = {
            key: value
            for key, value in stored.items()
            if key not in {"prior_record_hash", "record_hash"}
        }
        if canonical_json_bytes(stored_body) != canonical_json_bytes(observation):
            raise ValidationFailure(
                f"Pegasus observation ID collision: {observation['id']}"
            )
    else:
        stored = append_pegasus_observation(observation, root)

    distillation = run_distillation(batch, root) if batch is not None else None
    proposal_ids = set(distillation["proposal_ids"]) if distillation else set()
    proposals = [
        row
        for row in read_jsonl(
            root / "lab" / "second_brain" / "staging" / "proposals.jsonl"
        )
        if row["proposal_id"] in proposal_ids
    ]
    return {
        "observation": stored,
        "distillation_run": distillation,
        "proposals": proposals,
    }


def _write_once_json(path: Path, value: Any, root: Path) -> Path:
    assert_write_target("twelvelabs", path, root)
    body = canonical_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != body:
            raise ValidationFailure(f"TwelveLabs artifact collision: {path}")
        return path
    try:
        with path.open("xb") as handle:
            handle.write(body)
    except FileExistsError:
        if path.read_bytes() != body:
            raise ValidationFailure(f"TwelveLabs artifact collision: {path}")
    return path


def load_analysis_profiles(root: Path = REPO_ROOT) -> dict[str, dict[str, Any]]:
    """Load the closed analysis-profile catalog and enforce surface ownership."""
    path = root / "lab" / "second_brain" / "analysis_profiles.yaml"
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValidationFailure(f"cannot load analysis profiles: {error}") from error
    validate_instance("twelvelabs_analysis_profiles", value, root)
    rows = value["profiles"]
    profile_ids = [row["profile_id"] for row in rows]
    if len(profile_ids) != len(set(profile_ids)):
        raise ValidationFailure("analysis profile IDs must be unique")
    if set(profile_ids) != REQUIRED_ANALYSIS_PROFILES:
        raise ValidationFailure(
            "analysis profiles must match the closed Slice 9 catalog; "
            f"missing={sorted(REQUIRED_ANALYSIS_PROFILES - set(profile_ids))} "
            f"extra={sorted(set(profile_ids) - REQUIRED_ANALYSIS_PROFILES)}"
        )
    for row in rows:
        prefix = row["profile_id"].split(".", 1)[0]
        if prefix == "jockey" and row["surface"] != "jockey":
            raise ValidationFailure(f"{row['profile_id']} must use the Jockey surface")
        if prefix == "pegasus" and row["surface"] == "jockey":
            raise ValidationFailure(f"{row['profile_id']} cannot use the Jockey surface")
        if row["surface"] == "segment" and not row["segment_definitions"]:
            raise ValidationFailure(f"{row['profile_id']} requires segment definitions")
        if row["surface"] != "segment" and row["segment_definitions"]:
            raise ValidationFailure(
                f"{row['profile_id']} cannot declare segment definitions"
            )
    return {row["profile_id"]: row for row in rows}


def _profile_for(
    profile_id: str,
    surface: str,
    root: Path,
) -> dict[str, Any]:
    profile = load_analysis_profiles(root).get(profile_id)
    if profile is None:
        raise ValidationFailure(f"unknown analysis profile: {profile_id}")
    if profile["surface"] != surface:
        raise ValidationFailure(
            f"{profile_id} belongs to {profile['surface']}, not {surface}"
        )
    return profile


def _active_client(
    client: Any | None,
    env: Mapping[str, str] | None,
) -> Any:
    return client or twelvelabs.build_client(env=env)


def _artifact_root(
    job_id: str,
    root: Path,
    output_root: Path | None,
) -> Path:
    return output_root or root / "work" / "twelvelabs" / job_id


def _write_surface_artifacts(
    *,
    artifacts: Path,
    request: dict[str, Any],
    response: dict[str, Any],
    normalized: Any,
    root: Path,
) -> dict[str, Any]:
    request_path = _write_once_json(artifacts / "request.json", request, root)
    response_path = _write_once_json(artifacts / "response.sdk.json", response, root)
    normalized_path = _write_once_json(
        artifacts / "normalized.json", normalized, root
    )
    return {
        "request": str(request_path),
        "response": str(response_path),
        "normalized": str(normalized_path),
    }


def _write_request_artifact(artifacts: Path, request: dict[str, Any], root: Path) -> Path:
    """Persist the exact provider request before any external side effect."""
    return _write_once_json(artifacts / "request.json", request, root)


def _write_response_artifact(
    artifacts: Path, response: dict[str, Any], root: Path
) -> Path:
    """Persist a returned provider envelope before semantic admission checks."""
    return _write_once_json(artifacts / "response.sdk.json", response, root)


def _source(source_video: dict[str, Any], source_id: str | None = None) -> dict[str, Any]:
    return {
        "source_id": source_id or source_video["asset_ref"],
        "asset_ref": source_video["asset_ref"],
        "sha256": source_video["sha256"],
        "rights_scope": source_video["rights_scope"],
    }


def _authorized_interval(interval: dict[str, Any]) -> dict[str, float]:
    start = float(interval["source_start_s"])
    end = float(interval["source_end_s"])
    if end <= start:
        raise ValidationFailure("source interval must have positive duration")
    return {"start_s": start, "end_s": end}


def _assert_media_bounds(job: dict[str, Any]) -> tuple[dict[str, float], dict[str, float]]:
    media = _authorized_interval(job["media_bounds"])
    interval = _authorized_interval(job["interval"])
    if interval["start_s"] < media["start_s"] or interval["end_s"] > media["end_s"]:
        raise ValidationFailure("provider job interval exceeds declared media bounds")
    return media, interval


def _surface_run(
    surface: str,
    job_id: str,
    request_hash: str,
    raw_response_hash: str,
) -> dict[str, str]:
    return {
        "surface": surface,
        "job_id": job_id,
        "request_hash": request_hash,
        "raw_response_hash": raw_response_hash,
    }


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def execute_asset_job(
    job: dict[str, Any],
    root: Path = REPO_ROOT,
    *,
    client: Any | None = None,
    env: Mapping[str, str] | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    """Upload one rights-scoped asset and optionally register it in one store."""
    validate_instance("twelvelabs_asset_job", job, root)
    source = job["source"]
    file_path = Path(source["file_path"]) if "file_path" in source else None
    if file_path is not None and _file_hash(file_path.expanduser().resolve()) != source["sha256"]:
        raise ValidationFailure("asset job local file hash does not match source sha256")
    if job["media_type"] == "audio" and job.get("knowledge_store_id") is not None:
        raise ValidationFailure("audio assets cannot be registered in a Jockey store")
    request = {
        "provider": "twelvelabs",
        "api_version": twelvelabs.API_VERSION,
        "sdk_version": twelvelabs.SDK_VERSION,
        "surface": "assets",
        "job": job,
    }
    artifact_root = _artifact_root(job["job_id"], root, output_root)
    _write_request_artifact(artifact_root, request, root)
    active = _active_client(client, env)
    created = twelvelabs.upload_asset(
        media_type=job["media_type"],
        url=source.get("url"),
        file_path=file_path,
        client=active,
    )
    ready = twelvelabs.wait_for_asset(created["id"], client=active)
    item = None
    if job.get("knowledge_store_id") is not None:
        created_item = twelvelabs.add_asset_to_store(
            job["knowledge_store_id"],
            ready["id"],
            asset_type=job["media_type"],
            client=active,
        )
        item = twelvelabs.wait_for_store_item(
            job["knowledge_store_id"], created_item["id"], client=active
        )
    response = {"asset": ready, "knowledge_store_item": item}
    request_hash = sha256_value(request)
    response_hash = sha256_value(response)
    artifacts = _write_surface_artifacts(
        artifacts=artifact_root,
        request=request,
        response=response,
        normalized={
            "asset_id": ready["id"],
            "source_sha256": source["sha256"],
            "rights_scope": job["rights_scope"],
            "knowledge_store_item": item,
        },
        root=root,
    )
    return {
        "asset": ready,
        "knowledge_store_item": item,
        "surface_run": _surface_run(
            "assets", job["job_id"], request_hash, response_hash
        ),
        "artifacts": artifacts,
    }


def _analyze_request(
    job: dict[str, Any],
    profile: dict[str, Any],
    semantic_schema: dict[str, Any],
) -> dict[str, Any]:
    return {
        "provider": "twelvelabs",
        "api_version": twelvelabs.API_VERSION,
        "sdk_version": twelvelabs.SDK_VERSION,
        "surface": "pegasus_analyze",
        "model": twelvelabs.PEGASUS_MODEL,
        "asset_id": job["source_video"]["asset_ref"],
        "analysis_scope": job["analysis_scope"],
        "media_bounds": job["media_bounds"],
        "interval": job["interval"],
        "profile_id": job["profile_id"],
        "prompt": f"{profile['prompt']} Task focus: {job['prompt']}",
        "output_schema": semantic_schema,
        "temperature": 0.0,
    }


def _normalize_analyze_response(
    job: dict[str, Any],
    request: dict[str, Any],
    response: dict[str, Any],
    *,
    source_id: str | None,
    root: Path,
) -> list[dict[str, Any]]:
    return normalize_semantic_response(
        response["data"],
        source=_source(job["source_video"], source_id),
        authorized_interval=_authorized_interval(job["interval"]),
        surface="pegasus_analyze",
        model=twelvelabs.PEGASUS_MODEL,
        model_version=f"api-{twelvelabs.API_VERSION}-sdk-{twelvelabs.SDK_VERSION}",
        profile_id=job["profile_id"],
        request_hash=sha256_value(request),
        raw_response_hash=sha256_value(response),
        root=root,
    )


def execute_analyze_job(
    job: dict[str, Any],
    root: Path = REPO_ROOT,
    *,
    client: Any | None = None,
    env: Mapping[str, str] | None = None,
    output_root: Path | None = None,
    source_id: str | None = None,
) -> dict[str, Any]:
    """Run exact-video or interval-clipped Pegasus Analyze in source isolation."""
    validate_instance("twelvelabs_analyze_job", job, root)
    profile = _profile_for(job["profile_id"], "analyze", root)
    media_bounds, interval = _assert_media_bounds(job)
    if job["analysis_scope"] == "exact_video" and interval != media_bounds:
        raise ValidationFailure("exact-video Analyze must authorize the complete media bounds")
    if job["analysis_scope"] == "clipped_interval" and interval["end_s"] - interval["start_s"] < 4:
        raise ValidationFailure("clipped Analyze intervals must be at least 4 seconds")
    semantic_schema = load_schema("twelvelabs_semantic_response", root)
    request = _analyze_request(job, profile, semantic_schema)
    artifact_root = _artifact_root(job["job_id"], root, output_root)
    _write_request_artifact(artifact_root, request, root)
    active = _active_client(client, env)
    clip = (
        {}
        if job["analysis_scope"] == "exact_video"
        else {"start_s": interval["start_s"], "end_s": interval["end_s"]}
    )
    response = twelvelabs.analyze_video(
        job["source_video"]["asset_ref"],
        request["prompt"],
        output_schema=semantic_schema,
        temperature=0.0,
        client=active,
        **clip,
    )
    _write_response_artifact(artifact_root, response, root)
    observations = _normalize_analyze_response(
        job, request, response, source_id=source_id, root=root
    )
    request_hash = sha256_value(request)
    response_hash = sha256_value(response)
    artifacts = _write_surface_artifacts(
        artifacts=artifact_root,
        request=request,
        response=response,
        normalized={"observations": observations},
        root=root,
    )
    return {
        "observations": observations,
        "surface_run": _surface_run(
            "pegasus_analyze", job["job_id"], request_hash, response_hash
        ),
        "artifacts": artifacts,
    }


def renormalize_analyze_artifacts(
    job: dict[str, Any],
    artifacts: Path,
    root: Path = REPO_ROOT,
    *,
    source_id: str | None = None,
) -> list[dict[str, Any]]:
    """Recreate normalized observations from saved request and raw response only."""
    validate_instance("twelvelabs_analyze_job", job, root)
    request = json.loads((artifacts / "request.json").read_text(encoding="utf-8"))
    response = json.loads(
        (artifacts / "response.sdk.json").read_text(encoding="utf-8")
    )
    expected = _analyze_request(
        job,
        _profile_for(job["profile_id"], "analyze", root),
        load_schema("twelvelabs_semantic_response", root),
    )
    if canonical_json_bytes(request) != canonical_json_bytes(expected):
        raise ValidationFailure("saved Analyze request does not match the supplied job")
    return _normalize_analyze_response(
        job, request, response, source_id=source_id, root=root
    )


def execute_segment_job(
    job: dict[str, Any],
    root: Path = REPO_ROOT,
    *,
    client: Any | None = None,
    env: Mapping[str, str] | None = None,
    output_root: Path | None = None,
    source_id: str | None = None,
) -> dict[str, Any]:
    """Run one timestamp-bounded Pegasus segmentation task."""
    validate_instance("twelvelabs_segment_job", job, root)
    profile = _profile_for(job["profile_id"], "segment", root)
    _, interval = _assert_media_bounds(job)
    if interval["end_s"] - interval["start_s"] < 4:
        raise ValidationFailure("Segment intervals must be at least 4 seconds")
    request = {
        "provider": "twelvelabs",
        "api_version": twelvelabs.API_VERSION,
        "sdk_version": twelvelabs.SDK_VERSION,
        "surface": "pegasus_segment",
        "model": twelvelabs.PEGASUS_MODEL,
        "asset_id": job["source_video"]["asset_ref"],
        "media_bounds": job["media_bounds"],
        "interval": job["interval"],
        "profile_id": job["profile_id"],
        "segment_definitions": profile["segment_definitions"],
        "min_segment_duration": job["min_segment_duration"],
        "max_segment_duration": job.get("max_segment_duration"),
    }
    artifact_root = _artifact_root(job["job_id"], root, output_root)
    _write_request_artifact(artifact_root, request, root)
    response = twelvelabs.segment_video(
        job["source_video"]["asset_ref"],
        profile["segment_definitions"],
        custom_id=re.sub(
            r"[^A-Za-z0-9_-]", "_", job["job_id"][len("tl_segment_") :]
        )[:64],
        start_s=interval["start_s"],
        end_s=interval["end_s"],
        min_segment_duration=job["min_segment_duration"],
        max_segment_duration=job.get("max_segment_duration"),
        client=_active_client(client, env),
    )
    _write_response_artifact(artifact_root, response, root)
    data = response["completed"]["result"]["data"]
    observations = normalize_segments(
        data,
        source=_source(job["source_video"], source_id),
        authorized_interval=interval,
        profile_id=job["profile_id"],
        request_hash=sha256_value(request),
        raw_response_hash=sha256_value(response),
        root=root,
    )
    request_hash = sha256_value(request)
    response_hash = sha256_value(response)
    artifacts = _write_surface_artifacts(
        artifacts=artifact_root,
        request=request,
        response=response,
        normalized={"observations": observations},
        root=root,
    )
    return {
        "observations": observations,
        "surface_run": _surface_run(
            "pegasus_segment", job["job_id"], request_hash, response_hash
        ),
        "artifacts": artifacts,
    }


def execute_batch_job(
    job: dict[str, Any],
    root: Path = REPO_ROOT,
    *,
    client: Any | None = None,
    env: Mapping[str, str] | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    """Run one same-profile Pegasus batch without accepting partial success."""
    validate_instance("twelvelabs_batch_job", job, root)
    expected_surface = "analyze" if job["analysis_mode"] == "general" else "segment"
    profile = _profile_for(job["profile_id"], expected_surface, root)
    semantic_schema = load_schema("twelvelabs_semantic_response", root)
    requests = []
    for item in job["items"]:
        interval = _authorized_interval(item["interval"])
        if interval["end_s"] - interval["start_s"] < 4:
            raise ValidationFailure("batch item intervals must be at least 4 seconds")
        requests.append(
            {
                "custom_id": item["custom_id"],
                "video": {"type": "asset_id", "asset_id": item["asset_ref"]},
                "start_time": interval["start_s"],
                "end_time": interval["end_s"],
            }
        )
    defaults = (
        {
            "prompt": {"input_text": profile["prompt"]},
            "response_format": {"type": "json_schema", "json_schema": semantic_schema},
            "temperature": 0.0,
            "max_tokens": 8192,
        }
        if job["analysis_mode"] == "general"
        else {
            "response_format": {
                "type": "segment_definitions",
                "segment_definitions": profile["segment_definitions"],
            },
            "min_segment_duration": 2.0,
        }
    )
    request = {
        "provider": "twelvelabs",
        "api_version": twelvelabs.API_VERSION,
        "sdk_version": twelvelabs.SDK_VERSION,
        "surface": "pegasus_batch",
        "model": twelvelabs.PEGASUS_MODEL,
        "analysis_mode": job["analysis_mode"],
        "profile_id": job["profile_id"],
        "requests": requests,
        "defaults": defaults,
    }
    artifact_root = _artifact_root(job["job_id"], root, output_root)
    _write_request_artifact(artifact_root, request, root)
    response = twelvelabs.analyze_batch(
        requests,
        analysis_mode=job["analysis_mode"],
        defaults=defaults,
        client=_active_client(client, env),
    )
    _write_response_artifact(artifact_root, response, root)
    by_custom_id = {row["custom_id"]: row for row in response["results"]}
    if len(response["results"]) != len(job["items"]) or set(by_custom_id) != {
        row["custom_id"] for row in job["items"]
    }:
        raise ValidationFailure("batch results do not exactly match submitted custom IDs")
    request_hash = sha256_value(request)
    response_hash = sha256_value(response)
    observations: list[dict[str, Any]] = []
    for item in job["items"]:
        row = by_custom_id[item["custom_id"]]
        result = row.get("data")
        if not isinstance(result, dict) or result.get("finish_reason") != "stop":
            raise ValidationFailure(
                f"batch item {item['custom_id']} did not finish cleanly"
            )
        source = {
            "source_id": item["custom_id"],
            "asset_ref": item["asset_ref"],
            "sha256": item["sha256"],
            "rights_scope": item["rights_scope"],
        }
        interval = _authorized_interval(item["interval"])
        if job["analysis_mode"] == "general":
            observations.extend(
                normalize_semantic_response(
                    result["data"],
                    source=source,
                    authorized_interval=interval,
                    surface="pegasus_batch",
                    model=twelvelabs.PEGASUS_MODEL,
                    model_version=f"api-{twelvelabs.API_VERSION}-sdk-{twelvelabs.SDK_VERSION}",
                    profile_id=job["profile_id"],
                    request_hash=request_hash,
                    raw_response_hash=response_hash,
                    root=root,
                )
            )
        else:
            observations.extend(
                normalize_segments(
                    result["data"],
                    source=source,
                    authorized_interval=interval,
                    profile_id=job["profile_id"],
                    request_hash=request_hash,
                    raw_response_hash=response_hash,
                    surface="pegasus_batch",
                    root=root,
                )
            )
    observations.sort(key=lambda row: row["observation_id"])
    artifacts = _write_surface_artifacts(
        artifacts=artifact_root,
        request=request,
        response=response,
        normalized={"observations": observations},
        root=root,
    )
    return {
        "observations": observations,
        "surface_run": _surface_run(
            "pegasus_batch", job["job_id"], request_hash, response_hash
        ),
        "artifacts": artifacts,
    }


def execute_search_job(
    job: dict[str, Any],
    root: Path = REPO_ROOT,
    *,
    client: Any | None = None,
    env: Mapping[str, str] | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    """Search literal clips only inside the explicit authorized item set."""
    validate_instance("twelvelabs_search_job", job, root)
    filter_ = {"item_id": {"in_": sorted(job["authorized_item_ids"])}}
    request = {
        "provider": "twelvelabs",
        "api_version": twelvelabs.API_VERSION,
        "sdk_version": twelvelabs.SDK_VERSION,
        "surface": "knowledge_store_search",
        "knowledge_store_id": job["knowledge_store_id"],
        "query": job["query"],
        "modalities": job["modalities"],
        "filter": filter_,
    }
    artifact_root = _artifact_root(job["job_id"], root, output_root)
    _write_request_artifact(artifact_root, request, root)
    response = twelvelabs.search_all(
        job["knowledge_store_id"],
        job["query"],
        modalities=job["modalities"],
        filter_=filter_,
        client=_active_client(client, env),
    )
    _write_response_artifact(artifact_root, response, root)
    unauthorized = sorted(
        {
            row.get("item_id")
            for row in response["data"]
            if row.get("item_id") not in set(job["authorized_item_ids"])
        }
    )
    if unauthorized:
        raise ValidationFailure(
            "knowledge-store search returned unauthorized items: "
            + ", ".join(str(item) for item in unauthorized)
        )
    request_hash = sha256_value(request)
    response_hash = sha256_value(response)
    artifacts = _write_surface_artifacts(
        artifacts=artifact_root,
        request=request,
        response=response,
        normalized={"hits": response["data"]},
        root=root,
    )
    return {
        "hits": response["data"],
        "surface_run": _surface_run(
            "knowledge_store_search", job["job_id"], request_hash, response_hash
        ),
        "artifacts": artifacts,
    }


def _response_text(response: dict[str, Any]) -> str:
    texts = [
        content["text"]
        for output in response.get("output", [])
        if output.get("type") == "message"
        for content in output.get("content", [])
        if content.get("type") == "output_text" and isinstance(content.get("text"), str)
    ]
    if len(texts) != 1:
        raise ValidationFailure(
            f"expected one structured Jockey output text, found {len(texts)}"
        )
    return texts[0]


def execute_jockey_job(
    job: dict[str, Any],
    root: Path = REPO_ROOT,
    *,
    client: Any | None = None,
    env: Mapping[str, str] | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    """Run selected-item corpus reasoning without writing repository authority."""
    validate_instance("twelvelabs_jockey_job", job, root)
    profile = _profile_for(job["profile_id"], "jockey", root)
    output_schema = load_schema("twelvelabs_corpus_response", root)
    instructions = PROVIDER_INSTRUCTIONS
    if job.get("instructions"):
        instructions += " Domain guidance: " + job["instructions"]
    prompt = f"{profile['prompt']} Task focus: {job['prompt']}"
    request = {
        "provider": "twelvelabs",
        "api_version": twelvelabs.API_VERSION,
        "sdk_version": twelvelabs.SDK_VERSION,
        "surface": "jockey",
        "model": twelvelabs.JOCKEY_MODEL,
        "knowledge_store_id": job["knowledge_store_id"],
        "selections": job["selections"],
        "profile_id": job["profile_id"],
        "prompt": prompt,
        "instructions": instructions,
        "output_schema": output_schema,
    }
    artifact_root = _artifact_root(job["job_id"], root, output_root)
    _write_request_artifact(artifact_root, request, root)
    response = twelvelabs.to_plain(
        twelvelabs.create_jockey_response(
            job["knowledge_store_id"],
            prompt,
            output_schema=output_schema,
            schema_name="cpcs_jockey_corpus_observations",
            instructions=instructions,
            selections=job["selections"],
            client=_active_client(client, env),
        )
    )
    _write_response_artifact(artifact_root, response, root)
    if response.get("status") != "completed":
        raise ValidationFailure("Jockey response is not completed")
    if response.get("knowledge_store_id") != job["knowledge_store_id"]:
        raise ValidationFailure("Jockey response crossed the requested store boundary")
    try:
        structured = json.loads(_response_text(response))
    except json.JSONDecodeError as error:
        raise ValidationFailure("Jockey output is not valid structured JSON") from error
    validate_instance("twelvelabs_corpus_response", structured, root)
    selected_ids = {row["id"] for row in job["selections"]}
    returned_ids = {row["item_id"] for row in structured["observations"]}
    if not returned_ids <= selected_ids:
        raise ValidationFailure("Jockey response cites an item outside explicit selections")
    for index, observation in enumerate(structured["observations"]):
        assert_claim_policy(observation["claim"], f"observations[{index}].claim")
        interval = observation["interval"]
        if interval is not None and interval["end_s"] <= interval["start_s"]:
            raise ValidationFailure(
                f"Jockey observation {index} has a non-positive interval"
            )
    request_hash = sha256_value(request)
    response_hash = sha256_value(response)
    artifacts = _write_surface_artifacts(
        artifacts=artifact_root,
        request=request,
        response=response,
        normalized={"corpus_observations": structured},
        root=root,
    )
    return {
        "corpus_observations": structured,
        "surface_run": _surface_run(
            "jockey", job["job_id"], request_hash, response_hash
        ),
        "artifacts": artifacts,
    }


def execute_marengo_job(
    job: dict[str, Any],
    root: Path = REPO_ROOT,
    *,
    client: Any | None = None,
    env: Mapping[str, str] | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    """Create an explicit custom-similarity embedding artifact."""
    validate_instance("twelvelabs_marengo_job", job, root)
    request = {
        "provider": "twelvelabs",
        "api_version": twelvelabs.API_VERSION,
        "sdk_version": twelvelabs.SDK_VERSION,
        "surface": "marengo",
        "model": twelvelabs.MARENGO_MODEL,
        "input_type": job["input_type"],
        "text": job.get("text"),
        "asset_id": job.get("asset_id"),
        "image_asset_ids": job.get("image_asset_ids", []),
    }
    artifact_root = _artifact_root(job["job_id"], root, output_root)
    _write_request_artifact(artifact_root, request, root)
    response = twelvelabs.create_embedding(
        job["input_type"],
        text=job.get("text"),
        asset_id=job.get("asset_id"),
        image_asset_ids=job.get("image_asset_ids"),
        client=_active_client(client, env),
    )
    request_hash = sha256_value(request)
    response_hash = sha256_value(response)
    artifacts = _write_surface_artifacts(
        artifacts=artifact_root,
        request=request,
        response=response,
        normalized={"embedding_response": response},
        root=root,
    )
    return {
        "embedding_response": response,
        "surface_run": _surface_run(
            "marengo", job["job_id"], request_hash, response_hash
        ),
        "artifacts": artifacts,
    }


def execute_surface_job(
    job: dict[str, Any],
    root: Path = REPO_ROOT,
    **kwargs: Any,
) -> dict[str, Any]:
    """Dispatch only versioned, unambiguous TwelveLabs surface contracts."""
    schema = job.get("schema")
    dispatch = {
        "cpcs.twelvelabs_asset_job/1.0": execute_asset_job,
        "cpcs.twelvelabs_analyze_job/1.0": execute_analyze_job,
        "cpcs.twelvelabs_segment_job/1.0": execute_segment_job,
        "cpcs.twelvelabs_batch_job/1.0": execute_batch_job,
        "cpcs.twelvelabs_search_job/1.0": execute_search_job,
        "cpcs.twelvelabs_jockey_job/1.0": execute_jockey_job,
        "cpcs.twelvelabs_marengo_job/1.0": execute_marengo_job,
    }
    if schema not in dispatch:
        raise ValidationFailure(f"unknown TwelveLabs surface job schema: {schema}")
    return dispatch[schema](job, root, **kwargs)


def _fit_analysis_window(
    candidate: dict[str, float],
    authorized: dict[str, float],
) -> dict[str, float]:
    start = max(candidate["start_s"], authorized["start_s"])
    end = min(candidate["end_s"], authorized["end_s"])
    if end - start >= 4:
        return {"start_s": start, "end_s": end}
    center = (start + end) / 2
    start = max(authorized["start_s"], center - 2)
    end = min(authorized["end_s"], start + 4)
    start = max(authorized["start_s"], end - 4)
    if end - start < 4:
        raise ValidationFailure("authorized source interval is shorter than 4 seconds")
    return {"start_s": start, "end_s": end}


def _load_measurements(
    ids: Iterable[str],
    *,
    source: dict[str, Any],
    authorized_interval: dict[str, float],
    root: Path,
) -> list[dict[str, Any]]:
    requested = set(ids)
    rows = {
        row["id"]: row
        for row in read_jsonl(
            root / "lab" / "second_brain" / "immutable" / "measurement_observations.jsonl"
        )
        if row["id"] in requested
    }
    missing = sorted(requested - set(rows))
    if missing:
        raise ValidationFailure("cascade measurements do not exist: " + ", ".join(missing))
    return [
        normalize_measurement(
            rows[measurement_id],
            source=source,
            authorized_interval=authorized_interval,
            root=root,
        )
        for measurement_id in sorted(rows)
    ]


def _load_asset_registration(
    source: dict[str, Any], root: Path
) -> dict[str, str]:
    artifacts = root / "work" / "twelvelabs" / source["asset_job_id"]
    try:
        request = json.loads((artifacts / "request.json").read_text(encoding="utf-8"))
        response = json.loads(
            (artifacts / "response.sdk.json").read_text(encoding="utf-8")
        )
        normalized = json.loads(
            (artifacts / "normalized.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationFailure(
            f"cannot load exact asset registration {source['asset_job_id']}: {error}"
        ) from error
    job = request.get("job")
    if (
        request.get("surface") != "assets"
        or not isinstance(job, dict)
        or job.get("job_id") != source["asset_job_id"]
    ):
        raise ValidationFailure("asset registration request does not match the cascade")
    validate_instance("twelvelabs_asset_job", job, root)
    registered_source = job["source"]
    registered_path = registered_source.get("file_path")
    if registered_path is None:
        raise ValidationFailure("analysis cascades require an exact local-file asset registration")
    if Path(registered_path).expanduser().resolve() != Path(source["local_path"]).expanduser().resolve():
        raise ValidationFailure("asset registration local path does not match the cascade")
    if (
        registered_source["sha256"] != source["sha256"]
        or job["rights_scope"] != source["rights_scope"]
        or normalized.get("source_sha256") != source["sha256"]
        or normalized.get("rights_scope") != source["rights_scope"]
        or normalized.get("asset_id") != source["asset_ref"]
        or response.get("asset", {}).get("id") != source["asset_ref"]
    ):
        raise ValidationFailure("asset registration identity does not match the cascade source")
    return _surface_run(
        "assets",
        source["asset_job_id"],
        sha256_value(request),
        sha256_value(response),
    )


def _pegasus_payload(
    cascade: dict[str, Any],
    vog: dict[str, Any],
    semantic: list[dict[str, Any]],
    score: dict[str, Any] | None,
) -> dict[str, Any]:
    output = {field: [] for field in SEMANTIC_FIELDS}
    layer_fields = {
        "entity": "entities",
        "beat": "beats",
        "action": "actions",
        "camera": "camera",
        "performance": "performance",
        "face_affect": "face_affect",
        "audio": "audio",
        "marketing": "marketing_functions",
    }
    for row in semantic:
        field = layer_fields.get(row["layer"])
        if field is None:
            continue
        output[field].append(
            {
                **row["claim"],
                "start_s": row["interval"]["start_s"],
                "end_s": row["interval"]["end_s"],
                "evidence_class": row["evidence_class"],
                "confidence": row["confidence"],
                "vog_observation_id": row["observation_id"],
            }
        )
    classes = {row["evidence_class"] for row in semantic}
    confidence = min((row["confidence"] for row in semantic), default=0.0)
    source = cascade["source"]
    interval = cascade["authorized_interval"]
    profile_ids = [
        cascade["source_map_profile"],
        cascade["segment_profile"],
        *cascade["deep_analysis_profiles"],
    ]
    payload = {
        "id": "pegasus_obs_" + cascade["cascade_id"][len("tl_cascade_") :],
        "source_video": {
            "asset_ref": source["asset_ref"],
            "sha256": source["sha256"],
            "rights_scope": source["rights_scope"],
        },
        "extractor": {
            "provider": "twelvelabs",
            "model": twelvelabs.PEGASUS_MODEL,
            "model_version": f"api-{twelvelabs.API_VERSION}-sdk-{twelvelabs.SDK_VERSION}",
            "prompt_version": sha256_value(sorted(profile_ids)),
            "schema_version": "video-observation-graph/1.0",
        },
        "interval": {
            "source_start_s": interval["start_s"],
            "source_end_s": interval["end_s"],
        },
        **output,
        "candidate_concepts": cascade["candidate_concepts"],
        "evidence_class": "interpreted" if "interpreted" in classes else "inferred",
        "confidence": confidence,
        "raw_response_hash": sha256_value(vog["surface_runs"]),
        "created_at": cascade["created_at"],
        "analysis_profile_ids": sorted(set(profile_ids)),
        "surface_runs": vog["surface_runs"],
        "normalized_observation_ids": sorted(
            row["observation_id"] for row in semantic
        ),
        "measurement_refs": sorted(cascade.get("measurement_observation_ids", [])),
        "video_observation_graph_id": vog["graph_id"],
        "video_observation_graph_hash": vog["graph_hash"],
        "contradictions": vog["contradictions"],
    }
    if score is not None:
        payload["reverse_score_id"] = score["score_id"]
        payload["reverse_score_hash"] = sha256_value(score)
    return payload


def run_analysis_cascade(
    cascade: dict[str, Any],
    root: Path = REPO_ROOT,
    *,
    client: Any | None = None,
    env: Mapping[str, str] | None = None,
    output_root: Path | None = None,
    probe_fn: Callable[..., dict[str, Any]] = probe_media,
    intent_context: dict[str, Any] | None = None,
    score_assets: Iterable[dict[str, Any]] = (),
    conflict_resolutions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute the source-bounded semantic/measurement cascade, then append once."""
    validate_instance("video_analysis_cascade", cascade, root)
    profiles = load_analysis_profiles(root)
    if profiles[cascade["source_map_profile"]]["surface"] != "analyze":
        raise ValidationFailure("source_map_profile must own Analyze")
    if profiles[cascade["segment_profile"]]["surface"] != "segment":
        raise ValidationFailure("segment_profile must own Segment")
    for profile_id in cascade["deep_analysis_profiles"]:
        if profiles[profile_id]["surface"] != "analyze":
            raise ValidationFailure("deep-analysis profiles must own Analyze")
    source = cascade["source"]
    asset_registration = _load_asset_registration(source, root)
    media = probe_fn(Path(source["local_path"]), expected_sha256=source["sha256"])
    authorized = cascade["authorized_interval"]
    media_start = media["start_time_s"]
    media_end = media_start + media["duration_s"]
    if authorized["start_s"] < media_start or authorized["end_s"] > media_end:
        raise ValidationFailure("authorized interval exceeds the exact local source")
    if authorized["end_s"] - authorized["start_s"] < 4:
        raise ValidationFailure("analysis cascade requires at least four authorized seconds")
    artifacts = _artifact_root(cascade["cascade_id"], root, output_root)
    active = _active_client(client, env)
    source_video = {
        "asset_ref": source["asset_ref"],
        "sha256": source["sha256"],
        "rights_scope": source["rights_scope"],
    }
    full_source_authorized = (
        abs(authorized["start_s"] - media_start) < 1e-6
        and abs(authorized["end_s"] - media_end) < 1e-6
    )
    source_map_job = {
        "schema": "cpcs.twelvelabs_analyze_job/1.0",
        "job_id": "tl_analyze_" + cascade["cascade_id"][len("tl_cascade_") :] + "_source_map",
        "source_video": source_video,
        "analysis_scope": "exact_video" if full_source_authorized else "clipped_interval",
        "media_bounds": {
            "source_start_s": media_start,
            "source_end_s": media_end,
        },
        "interval": {
            "source_start_s": authorized["start_s"],
            "source_end_s": authorized["end_s"],
        },
        "profile_id": cascade["source_map_profile"],
        "prompt": "Build a broad source map before targeted analysis.",
        "candidate_concepts": cascade["candidate_concepts"],
        "created_at": cascade["created_at"],
    }
    source_map = execute_analyze_job(
        source_map_job,
        root,
        client=active,
        output_root=artifacts / "01_source_map",
        source_id=source["source_id"],
    )
    segment_job = {
        "schema": "cpcs.twelvelabs_segment_job/1.0",
        "job_id": "tl_segment_" + cascade["cascade_id"][len("tl_cascade_") :],
        "source_video": source_video,
        "media_bounds": {
            "source_start_s": media_start,
            "source_end_s": media_end,
        },
        "interval": {
            "source_start_s": authorized["start_s"],
            "source_end_s": authorized["end_s"],
        },
        "profile_id": cascade["segment_profile"],
        "min_segment_duration": 2.0,
        "max_segment_duration": None,
        "created_at": cascade["created_at"],
    }
    segmentation = execute_segment_job(
        segment_job,
        root,
        client=active,
        output_root=artifacts / "02_segmentation",
        source_id=source["source_id"],
    )
    candidates = segmentation["observations"]
    target = candidates[0]["interval"] if candidates else authorized
    window = _fit_analysis_window(target, authorized)
    deep_results = []
    for index, profile_id in enumerate(cascade["deep_analysis_profiles"], 1):
        deep_job = {
            "schema": "cpcs.twelvelabs_analyze_job/1.0",
            "job_id": (
                "tl_analyze_"
                + cascade["cascade_id"][len("tl_cascade_") :]
                + f"_deep_{index:02d}"
            ),
            "source_video": source_video,
            "analysis_scope": "clipped_interval",
            "media_bounds": {
                "source_start_s": media_start,
                "source_end_s": media_end,
            },
            "interval": {
                "source_start_s": window["start_s"],
                "source_end_s": window["end_s"],
            },
            "profile_id": profile_id,
            "prompt": "Deeply analyze the targeted segment selected by the source map.",
            "candidate_concepts": cascade["candidate_concepts"],
            "created_at": cascade["created_at"],
        }
        deep_results.append(
            execute_analyze_job(
                deep_job,
                root,
                client=active,
                output_root=artifacts / f"03_deep_{index:02d}",
                source_id=source["source_id"],
            )
        )
    semantic = [
        *source_map["observations"],
        *segmentation["observations"],
        *(row for result in deep_results for row in result["observations"]),
    ]
    measurements = _load_measurements(
        cascade.get("measurement_observation_ids", []),
        source=source,
        authorized_interval=authorized,
        root=root,
    )
    surface_runs = [
        asset_registration,
        source_map["surface_run"],
        segmentation["surface_run"],
        *(result["surface_run"] for result in deep_results),
    ]
    vog = build_video_observation_graph(
        source={
            "source_id": source["source_id"],
            "asset_ref": source["asset_ref"],
            "sha256": source["sha256"],
            "rights_scope": source["rights_scope"],
        },
        authorized_interval=authorized,
        media_metadata=media,
        semantic_observations=semantic,
        measurement_observations=measurements,
        surface_runs=surface_runs,
        root=root,
    )
    vog_path = _write_once_json(artifacts / "04_vog.json", vog, root)
    score = None
    score_path = None
    if intent_context is not None:
        from lab.compiler.reverse import resolve_vog_score

        score = resolve_vog_score(
            intent_context,
            vog,
            assets=score_assets,
            conflict_resolutions=conflict_resolutions,
            root=root,
        )
        score_path = _write_once_json(artifacts / "05_reverse_score.json", score, root)
    payload = _pegasus_payload(cascade, vog, semantic, score)
    payload_path = _write_once_json(artifacts / "06_immutable_payload.json", payload, root)
    result = ingest_response(payload, root)
    run = {
        "cascade_id": cascade["cascade_id"],
        "source_sha256": source["sha256"],
        "authorized_interval": authorized,
        "video_observation_graph_id": vog["graph_id"],
        "video_observation_graph_hash": vog["graph_hash"],
        "reverse_score_id": score["score_id"] if score else None,
        "observation_id": result["observation"]["id"],
        "observation_record_hash": result["observation"]["record_hash"],
    }
    run_path = _write_once_json(artifacts / "run.json", run, root)
    return {
        "video_observation_graph": vog,
        "reverse_score": score,
        "observation": result["observation"],
        "distillation_run": result["distillation_run"],
        "artifacts": {
            "vog": str(vog_path),
            "reverse_score": str(score_path) if score_path else None,
            "immutable_payload": str(payload_path),
            "run": str(run_path),
        },
    }


def main(argv: list[str] | None = None) -> None:
    arguments = list(sys.argv[1:] if argv is None else argv)
    commands = {"doctor", "profiles", "run-job", "cascade", "ingest"}
    if arguments and arguments[0] not in commands:
        result = ingest_response(json.loads(Path(arguments[0]).read_text()))
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("profiles")
    run_job = sub.add_parser("run-job")
    run_job.add_argument("job", type=Path)
    cascade = sub.add_parser("cascade")
    cascade.add_argument("job", type=Path)
    cascade.add_argument("--intent-context", type=Path)
    cascade.add_argument("--score-assets", type=Path)
    ingest = sub.add_parser("ingest")
    ingest.add_argument("payload", type=Path)
    args = parser.parse_args(arguments)
    if args.command == "doctor":
        result = twelvelabs.doctor()
    elif args.command == "profiles":
        result = {"profiles": sorted(load_analysis_profiles())}
    elif args.command == "run-job":
        result = execute_surface_job(json.loads(args.job.read_text()))
    elif args.command == "cascade":
        result = run_analysis_cascade(
            json.loads(args.job.read_text()),
            intent_context=(
                json.loads(args.intent_context.read_text())
                if args.intent_context
                else None
            ),
            score_assets=(
                json.loads(args.score_assets.read_text())
                if args.score_assets
                else []
            ),
        )
    else:
        result = ingest_response(json.loads(args.payload.read_text()))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
