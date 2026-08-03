"""Govern TwelveLabs Jockey output as immutable semantics and distilled proposals."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping

from .distill import run_distillation
from .providers import twelvelabs
from .record import append_pegasus_observation
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
HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
PROVIDER_INSTRUCTIONS = (
    "Use only the selected authorized item as evidence. Respect the requested source "
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


def _response_text(response: dict[str, Any]) -> str:
    texts = [
        content["text"]
        for output in response.get("output", [])
        if output.get("type") == "message"
        for content in output.get("content", [])
        if content.get("type") == "output_text"
        and isinstance(content.get("text"), str)
    ]
    if len(texts) != 1:
        raise ValidationFailure(
            f"expected one structured Jockey output text, found {len(texts)}"
        )
    return texts[0]


def _validate_semantic_intervals(
    semantic: dict[str, Any],
    interval: dict[str, float],
) -> None:
    lower = interval["source_start_s"]
    upper = interval["source_end_s"]
    for field in SEMANTIC_FIELDS:
        for index, item in enumerate(semantic[field]):
            start = item["start_s"]
            end = item["end_s"]
            if end <= start:
                raise ValidationFailure(
                    f"{field}/{index}: end_s must be greater than start_s"
                )
            if start < lower or end > upper:
                raise ValidationFailure(
                    f"{field}/{index}: timestamp is outside {lower:g}-{upper:g}s"
                )


def extract_with_twelvelabs(
    job: dict[str, Any],
    root: Path = REPO_ROOT,
    *,
    client: Any | None = None,
    env: Mapping[str, str] | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    """Run Jockey for one authorized item and ingest its structured response."""
    validate_instance("twelvelabs_analysis_job", job, root)
    interval = job["interval"]
    if interval["source_end_s"] <= interval["source_start_s"]:
        raise ValidationFailure(
            "analysis job source_end_s must be greater than source_start_s"
        )
    source = os.environ if env is None else env
    store_id = job.get("knowledge_store_id") or source.get(
        twelvelabs.STORE_ID_ENV
    )
    if not store_id:
        raise ValidationFailure(
            "knowledge_store_id is absent and "
            f"{twelvelabs.STORE_ID_ENV} is not configured"
        )
    active = client or twelvelabs.build_client(env=source)
    item = twelvelabs.retrieve_store_item(
        store_id, job["item_id"], client=active
    )
    if item.get("status") != "ready":
        raise ValidationFailure(
            f"knowledge store item {job['item_id']} is not ready"
        )
    if item.get("asset_id") != job["source_video"]["asset_ref"]:
        raise ValidationFailure(
            "knowledge store item asset_id does not match the authorized source"
        )

    semantic_schema = load_schema("twelvelabs_semantic_response", root)
    prompt = (
        f"Analyze only {{{{sel:0}}}} from source seconds "
        f"{interval['source_start_s']:g} through {interval['source_end_s']:g}. "
        f"{job['prompt']}"
    )
    instructions = PROVIDER_INSTRUCTIONS
    if job.get("instructions"):
        instructions += " Domain guidance: " + job["instructions"]
    prompt_hash = sha256_value(
        {
            "prompt": prompt,
            "instructions": instructions,
            "schema": semantic_schema,
        }
    )
    artifacts = (
        output_root
        if output_root is not None
        else root / "work" / "twelvelabs" / job["job_id"]
    )
    request_snapshot = {
        "provider": "twelvelabs",
        "api_version": twelvelabs.API_VERSION,
        "sdk_version": twelvelabs.SDK_VERSION,
        "model": twelvelabs.JOCKEY_MODEL,
        "knowledge_store_id": store_id,
        "item_id": job["item_id"],
        "input": [
            {"type": "message", "role": "user", "content": prompt}
        ],
        "instructions": instructions,
        "selections": [{"kind": "item", "id": job["item_id"]}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "cpcs_pegasus_semantics",
                "schema": semantic_schema,
                "strict": True,
            }
        },
        "prompt_hash": prompt_hash,
    }
    request_path = _write_once_json(
        artifacts / "request.json", request_snapshot, root
    )
    response_model = twelvelabs.create_jockey_response(
        store_id,
        prompt,
        output_schema=semantic_schema,
        schema_name="cpcs_pegasus_semantics",
        instructions=instructions,
        selections=[{"kind": "item", "id": job["item_id"]}],
        client=active,
    )
    response = twelvelabs.to_plain(response_model)
    response_path = _write_once_json(
        artifacts / "response.sdk.json", response, root
    )
    response_hash = (
        "sha256:" + hashlib.sha256(canonical_json_bytes(response)).hexdigest()
    )
    if response.get("status") != "completed":
        raise ValidationFailure(
            f"Jockey response is {response.get('status', 'unknown')}, not completed"
        )
    if response.get("knowledge_store_id") != store_id:
        raise ValidationFailure(
            "Jockey response knowledge_store_id does not match the analysis job"
        )
    response_id = response.get("id")
    session_id = response.get("session_id")
    if not isinstance(response_id, str) or not response_id:
        raise ValidationFailure("Jockey response returned no response ID")
    if not isinstance(session_id, str) or not session_id:
        raise ValidationFailure("Jockey response returned no session ID")
    try:
        semantic = json.loads(_response_text(response))
    except json.JSONDecodeError as error:
        raise ValidationFailure(
            f"Jockey structured response is not valid JSON: {error.msg}"
        ) from error
    validate_instance("twelvelabs_semantic_response", semantic, root)
    _validate_semantic_intervals(semantic, interval)
    evidence_classes = {
        item["evidence_class"]
        for field in SEMANTIC_FIELDS
        for item in semantic[field]
    }
    evidence_class = (
        "interpreted" if "interpreted" in evidence_classes else "inferred"
    )
    payload = {
        "id": "pegasus_obs_" + job["job_id"][len("tl_job_") :],
        "source_video": job["source_video"],
        "extractor": {
            "provider": "twelvelabs",
            "model": twelvelabs.JOCKEY_MODEL,
            "model_version": (
                f"api-{twelvelabs.API_VERSION}-sdk-{twelvelabs.SDK_VERSION}"
            ),
            "prompt_version": prompt_hash,
            "schema_version": "twelvelabs-semantic-response/1.0",
        },
        "interval": interval,
        **{field: semantic[field] for field in SEMANTIC_FIELDS},
        "candidate_concepts": job["candidate_concepts"],
        "evidence_class": evidence_class,
        "confidence": semantic["confidence"],
        "raw_response_hash": response_hash,
        "created_at": job["created_at"],
        "provider_context": {
            "adapter": "twelvelabs_jockey",
            "knowledge_store_id": store_id,
            "item_id": job["item_id"],
            "response_id": response_id,
            "session_id": session_id,
            "query": job["prompt"],
            "tool": "responses.create",
            "prompt_hash": prompt_hash,
            "api_version": twelvelabs.API_VERSION,
            "sdk_version": twelvelabs.SDK_VERSION,
        },
    }
    payload_path = _write_once_json(
        artifacts / "normalized_payload.json", payload, root
    )
    result = ingest_response(payload, root)
    run_snapshot = {
        "job_id": job["job_id"],
        "observation_id": result["observation"]["id"],
        "observation_record_hash": result["observation"]["record_hash"],
        "distillation_run_id": (
            result["distillation_run"]["id"]
            if result["distillation_run"] is not None
            else None
        ),
        "response_id": response_id,
        "session_id": session_id,
        "raw_response_hash": response_hash,
    }
    run_path = _write_once_json(
        artifacts / "run.json", run_snapshot, root
    )
    result["provider"] = {
        "response_id": response_id,
        "session_id": session_id,
        "knowledge_store_id": store_id,
        "item_id": job["item_id"],
        "raw_response_hash": response_hash,
    }
    result["artifacts"] = {
        "request": str(request_path),
        "response": str(response_path),
        "normalized_payload": str(payload_path),
        "run": str(run_path),
    }
    return result


def main(argv: list[str] | None = None) -> None:
    arguments = list(sys.argv[1:] if argv is None else argv)
    commands = {"doctor", "extract", "ingest"}
    if arguments and arguments[0] not in commands:
        result = ingest_response(json.loads(Path(arguments[0]).read_text()))
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    extract = sub.add_parser("extract")
    extract.add_argument("job", type=Path)
    ingest = sub.add_parser("ingest")
    ingest.add_argument("payload", type=Path)
    args = parser.parse_args(arguments)
    if args.command == "doctor":
        result = twelvelabs.doctor()
    elif args.command == "extract":
        result = extract_with_twelvelabs(json.loads(args.job.read_text()))
    else:
        result = ingest_response(json.loads(args.payload.read_text()))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
