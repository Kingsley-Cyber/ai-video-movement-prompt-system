"""Normalize, fuse, and hash source-bounded Video Observation Graphs."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable

from .validate import (
    REPO_ROOT,
    ValidationFailure,
    canonical_json_bytes,
    sha256_value,
    validate_instance,
)

OBSERVATION_POLICY = "cpcs-video-observation/1.0"
FIELD_LAYER = {
    "entities": "entity",
    "beats": "beat",
    "actions": "action",
    "camera": "camera",
    "performance": "performance",
    "face_affect": "face_affect",
    "audio": "audio",
    "marketing_functions": "marketing",
}
FORBIDDEN_CLAIM_KEYS = frozenset(
    {
        "race",
        "ethnicity",
        "religion",
        "sexual_orientation",
        "medical_condition",
        "diagnosis",
        "political_affiliation",
        "protected_trait",
        "private_state",
    }
)
FORBIDDEN_ASSERTION = re.compile(
    r"\b(?:actually feels|secretly believes|private mental state|medical diagnosis|"
    r"sexual orientation|political affiliation|racial identity)\b",
    re.IGNORECASE,
)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_media(
    path: Path,
    *,
    expected_sha256: str,
) -> dict[str, Any]:
    """Run local ffprobe and bind the result to exact source bytes."""
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    if _file_sha256(resolved) != expected_sha256:
        raise ValidationFailure("local media hash does not match the authorized source")
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=start_time,duration:stream=codec_type,width,height,r_frame_rate",
            "-of",
            "json",
            str(resolved),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    raw = json.loads(completed.stdout)
    video_streams = [
        row for row in raw.get("streams", []) if row.get("codec_type") == "video"
    ]
    if len(video_streams) != 1:
        raise ValidationFailure("ffprobe must report exactly one video stream")
    stream = video_streams[0]
    rate_text = str(stream.get("r_frame_rate", "0/1"))
    numerator, denominator = (float(value) for value in rate_text.split("/", 1))
    if denominator == 0:
        raise ValidationFailure("ffprobe returned an invalid frame rate")
    result = {
        "duration_s": float(raw["format"]["duration"]),
        "start_time_s": float(raw["format"].get("start_time", 0.0)),
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "frame_rate": round(numerator / denominator, 8),
        "probe_hash": sha256_value(raw),
    }
    if result["duration_s"] <= 0 or result["frame_rate"] <= 0:
        raise ValidationFailure("ffprobe returned non-positive media dimensions")
    return result


def assert_claim_policy(value: Any, path: str = "claim") -> None:
    if isinstance(value, dict):
        forbidden = sorted(set(value) & FORBIDDEN_CLAIM_KEYS)
        if forbidden:
            raise ValidationFailure(
                f"{path} contains prohibited inference fields: {', '.join(forbidden)}"
            )
        for key, child in value.items():
            assert_claim_policy(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_claim_policy(child, f"{path}[{index}]")
    elif isinstance(value, str) and FORBIDDEN_ASSERTION.search(value):
        raise ValidationFailure(f"{path} asserts a protected trait or private state")


def _interval(value: dict[str, Any]) -> dict[str, float]:
    start = value.get("start_s", value.get("source_start_s", value.get("start_time")))
    end = value.get("end_s", value.get("source_end_s", value.get("end_time")))
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
        raise ValidationFailure("observation interval requires numeric start and end")
    if start < 0 or end <= start:
        raise ValidationFailure("observation interval must be positive and ordered")
    return {"start_s": float(start), "end_s": float(end)}


def _inside(inner: dict[str, float], outer: dict[str, float]) -> bool:
    return inner["start_s"] >= outer["start_s"] and inner["end_s"] <= outer["end_s"]


def _observation_id(seed: dict[str, Any]) -> str:
    digest = hashlib.sha256(canonical_json_bytes(seed)).hexdigest()[:24]
    return "vog_obs_" + digest


def normalize_semantic_response(
    response: dict[str, Any] | str,
    *,
    source: dict[str, Any],
    authorized_interval: dict[str, float],
    surface: str,
    model: str,
    model_version: str,
    profile_id: str,
    request_hash: str,
    raw_response_hash: str,
    root: Path = REPO_ROOT,
) -> list[dict[str, Any]]:
    semantic = json.loads(response) if isinstance(response, str) else response
    validate_instance("twelvelabs_semantic_response", semantic, root)
    values: list[dict[str, Any]] = []
    for field_name, layer in FIELD_LAYER.items():
        for index, item in enumerate(semantic[field_name]):
            interval = _interval(item)
            if not _inside(interval, authorized_interval):
                raise ValidationFailure(
                    f"{field_name}/{index} lies outside the authorized interval"
                )
            claim = {"label": item["label"], "description": item["description"]}
            assert_claim_policy(claim)
            value = {
                "schema": "cpcs.normalized_video_observation/1.0",
                "observation_id": _observation_id(
                    {
                        "source": source["source_id"],
                        "surface": surface,
                        "profile": profile_id,
                        "field": field_name,
                        "index": index,
                        "interval": interval,
                        "claim": claim,
                        "raw": raw_response_hash,
                    }
                ),
                "source_id": source["source_id"],
                "source_sha256": source["sha256"],
                "interval": interval,
                "subject_refs": [],
                "layer": layer,
                "claim": claim,
                "evidence_class": item["evidence_class"],
                "confidence": item["confidence"],
                "alternatives": [],
                "provenance": {
                    "surface": surface,
                    "model": model,
                    "model_version": model_version,
                    "profile_id": profile_id,
                    "request_hash": request_hash,
                    "raw_response_hash": raw_response_hash,
                },
            }
            validate_instance("normalized_video_observation", value, root)
            values.append(value)
    return sorted(values, key=lambda row: row["observation_id"])


def normalize_verification_response(
    response: dict[str, Any] | str,
    *,
    source: dict[str, Any],
    authorized_interval: dict[str, float],
    requirements: list[dict[str, Any]],
    surface: str,
    model: str,
    model_version: str,
    profile_id: str,
    request_hash: str,
    raw_response_hash: str,
    root: Path = REPO_ROOT,
) -> list[dict[str, Any]]:
    """Normalize score-bound semantic assessments without expanding their target set."""
    semantic = json.loads(response) if isinstance(response, str) else response
    validate_instance("twelvelabs_verification_response", semantic, root)
    allowed = {
        (row["metric_id"], row["target_path"]): row for row in requirements
    }
    if len(allowed) != len(requirements):
        raise ValidationFailure("verification requirements contain duplicate targets")
    values: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, assessment in enumerate(semantic["assessments"]):
        pair = (assessment["metric_id"], assessment["target_path"])
        requirement = allowed.get(pair)
        if requirement is None:
            raise ValidationFailure(
                "verification response targets an undeclared metric or canonical path"
            )
        if pair in seen:
            raise ValidationFailure("verification response repeats one metric target")
        seen.add(pair)
        interval = _interval(assessment)
        if not _inside(interval, authorized_interval):
            raise ValidationFailure(
                f"verification assessment/{index} lies outside the authorized interval"
            )
        limitations = sorted(set(assessment["limitations"]))
        if assessment["verdict"] == "unobservable" and not limitations:
            raise ValidationFailure(
                "an unobservable verification assessment requires a limitation"
            )
        claim = {
            "metric_id": assessment["metric_id"],
            "target_path": assessment["target_path"],
            "method": requirement["method"],
            "verdict": assessment["verdict"],
            "observed": assessment["observed"],
            "deviation": assessment.get("deviation"),
            "limitations": limitations,
        }
        assert_claim_policy(claim)
        value = {
            "schema": "cpcs.normalized_video_observation/1.0",
            "observation_id": _observation_id(
                {
                    "source": source["source_id"],
                    "surface": surface,
                    "profile": profile_id,
                    "assessment": index,
                    "interval": interval,
                    "claim": claim,
                    "raw": raw_response_hash,
                }
            ),
            "source_id": source["source_id"],
            "source_sha256": source["sha256"],
            "interval": interval,
            "subject_refs": [],
            "layer": "verification",
            "claim": claim,
            "evidence_class": "interpreted",
            "confidence": assessment["confidence"],
            "alternatives": [],
            "provenance": {
                "surface": surface,
                "model": model,
                "model_version": model_version,
                "profile_id": profile_id,
                "request_hash": request_hash,
                "raw_response_hash": raw_response_hash,
            },
        }
        validate_instance("normalized_video_observation", value, root)
        values.append(value)
    return sorted(values, key=lambda row: row["observation_id"])


def normalize_segments(
    response: dict[str, Any] | str,
    *,
    source: dict[str, Any],
    authorized_interval: dict[str, float],
    profile_id: str,
    request_hash: str,
    raw_response_hash: str,
    surface: str = "pegasus_segment",
    root: Path = REPO_ROOT,
) -> list[dict[str, Any]]:
    segments = json.loads(response) if isinstance(response, str) else response
    if not isinstance(segments, dict):
        raise ValidationFailure("segment response must be an object")
    values: list[dict[str, Any]] = []
    for definition_id, rows in sorted(segments.items()):
        if not isinstance(rows, list):
            raise ValidationFailure(f"segment definition {definition_id} must be an array")
        for index, row in enumerate(rows):
            interval = _interval(row)
            if not _inside(interval, authorized_interval):
                raise ValidationFailure(
                    f"segment {definition_id}/{index} lies outside the authorized interval"
                )
            metadata = row.get("metadata", {})
            if not isinstance(metadata, dict):
                raise ValidationFailure("segment metadata must be an object")
            claim = {"definition_id": definition_id, **metadata}
            assert_claim_policy(claim)
            value = {
                "schema": "cpcs.normalized_video_observation/1.0",
                "observation_id": _observation_id(
                    {
                        "source": source["source_id"],
                        "profile": profile_id,
                        "definition": definition_id,
                        "index": index,
                        "interval": interval,
                        "claim": claim,
                        "raw": raw_response_hash,
                    }
                ),
                "source_id": source["source_id"],
                "source_sha256": source["sha256"],
                "interval": interval,
                "subject_refs": [],
                "layer": "segment",
                "claim": claim,
                "evidence_class": "interpreted",
                "confidence": float(row.get("confidence", 0.5)),
                "alternatives": [],
                "provenance": {
                    "surface": surface,
                    "model": "pegasus1.5",
                    "model_version": "api-v1.3-sdk-1.3.1",
                    "profile_id": profile_id,
                    "request_hash": request_hash,
                    "raw_response_hash": raw_response_hash,
                },
            }
            validate_instance("normalized_video_observation", value, root)
            values.append(value)
    return sorted(values, key=lambda row: row["observation_id"])


def normalize_measurement(
    record: dict[str, Any],
    *,
    source: dict[str, Any],
    authorized_interval: dict[str, float],
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    if record["source_asset_ref"] != source["asset_ref"]:
        raise ValidationFailure("measurement asset does not match the cascade source")
    if record["source_sha256"] != source["sha256"]:
        raise ValidationFailure("measurement hash does not match the cascade source")
    interval = _interval(record["interval"])
    if not _inside(interval, authorized_interval):
        raise ValidationFailure("measurement lies outside the authorized interval")
    assert_claim_policy(record["claim"])
    value = {
        "schema": "cpcs.normalized_video_observation/1.0",
        "observation_id": _observation_id(
            {"measurement_id": record["id"], "record_hash": record["record_hash"]}
        ),
        "source_id": source["source_id"],
        "source_sha256": source["sha256"],
        "interval": interval,
        "subject_refs": [],
        "layer": "measurement",
        "claim": record["claim"],
        "evidence_class": record["evidence_class"],
        "confidence": record["confidence"],
        "alternatives": [],
        "provenance": {
            "surface": "local_measurement",
            "model": record["tool"],
            "model_version": record["model_version"],
            "profile_id": f"local.{record['tool']}",
            "request_hash": sha256_value(
                {"tool": record["tool"], "model_version": record["model_version"]}
            ),
            "raw_response_hash": record["record_hash"],
        },
    }
    validate_instance("normalized_video_observation", value, root)
    return value


def _overlap(left: dict[str, float], right: dict[str, float]) -> bool:
    return left["start_s"] < right["end_s"] and right["start_s"] < left["end_s"]


def build_video_observation_graph(
    *,
    source: dict[str, Any],
    authorized_interval: dict[str, float],
    media_metadata: dict[str, Any],
    semantic_observations: Iterable[dict[str, Any]],
    measurement_observations: Iterable[dict[str, Any]],
    surface_runs: Iterable[dict[str, Any]],
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    semantic = sorted(semantic_observations, key=lambda row: row["observation_id"])
    measurements = sorted(
        measurement_observations, key=lambda row: row["observation_id"]
    )
    observations = [*semantic, *measurements]
    source_node_id = "vog_node_source_" + hashlib.sha256(
        source["source_id"].encode("utf-8")
    ).hexdigest()[:16]
    nodes = [{"id": source_node_id, "node_type": "source", "data": source}]
    edges: list[dict[str, Any]] = []
    observation_nodes: dict[str, str] = {}
    for observation in observations:
        node_id = "vog_node_" + observation["observation_id"][len("vog_obs_") :]
        observation_nodes[observation["observation_id"]] = node_id
        node_type = (
            "measurement"
            if observation["evidence_class"] in {"measured", "detected"}
            else "segment"
            if observation["layer"] == "segment"
            else "observation"
        )
        nodes.append({"id": node_id, "node_type": node_type, "data": observation})
        edges.append(
            {
                "id": f"vog_edge_observed_{len(edges):06d}",
                "u": node_id,
                "v": source_node_id,
                "type": "SEGMENT_OF" if node_type == "segment" else "OBSERVED_IN",
            }
        )

    contradictions: list[dict[str, Any]] = []
    support_links = 0
    for left in semantic:
        for right in measurements:
            if not _overlap(left["interval"], right["interval"]):
                continue
            common = sorted(set(left["claim"]) & set(right["claim"]))
            if not common:
                continue
            conflicts = [
                key for key in common if left["claim"][key] != right["claim"][key]
            ]
            edge_type = "CONTRADICTS" if conflicts else "SUPPORTS"
            if conflicts:
                contradiction_id = (
                    "vog_contradiction_"
                    + hashlib.sha256(
                        f"{left['observation_id']}:{right['observation_id']}".encode()
                    ).hexdigest()[:20]
                )
                contradictions.append(
                    {
                        "id": contradiction_id,
                        "left_observation_id": left["observation_id"],
                        "right_observation_id": right["observation_id"],
                        "fields": conflicts,
                        "resolution": "preserved_for_review",
                    }
                )
            else:
                support_links += 1
            edges.append(
                {
                    "id": f"vog_edge_fusion_{len(edges):06d}",
                    "u": observation_nodes[left["observation_id"]],
                    "v": observation_nodes[right["observation_id"]],
                    "type": edge_type,
                }
            )

    core = {
        "schema": "cpcs.video_observation_graph/1.0",
        "source": source,
        "authorized_interval": authorized_interval,
        "media_metadata": media_metadata,
        "nodes": sorted(nodes, key=lambda row: row["id"]),
        "edges": sorted(edges, key=lambda row: row["id"]),
        "contradictions": sorted(contradictions, key=lambda row: row["id"]),
        "fusion_report": {
            "semantic_observations": len(semantic),
            "measurement_observations": len(measurements),
            "support_links": support_links,
            "contradictions": len(contradictions),
            "confidence_averaging": False,
        },
        "surface_runs": sorted(
            surface_runs, key=lambda row: (row["surface"], row["job_id"])
        ),
    }
    graph_hash = sha256_value(core)
    value = {
        **core,
        "graph_id": "vog_" + graph_hash[len("sha256:") :][:32],
        "graph_hash": graph_hash,
    }
    validate_video_observation_graph(value, root)
    return value


def validate_video_observation_graph(
    value: dict[str, Any], root: Path = REPO_ROOT
) -> None:
    """Validate schema, content identity, references, source bounds, and counts."""
    validate_instance("video_observation_graph", value, root)
    core = {
        key: item
        for key, item in value.items()
        if key not in {"graph_id", "graph_hash"}
    }
    expected_hash = sha256_value(core)
    expected_id = "vog_" + expected_hash[len("sha256:") :][:32]
    if value["graph_hash"] != expected_hash or value["graph_id"] != expected_id:
        raise ValidationFailure("Video Observation Graph content identity does not match")
    node_ids = [row["id"] for row in value["nodes"]]
    edge_ids = [row["id"] for row in value["edges"]]
    if value["nodes"] != sorted(value["nodes"], key=lambda row: row["id"]):
        raise ValidationFailure("Video Observation Graph nodes are not canonical")
    if value["edges"] != sorted(value["edges"], key=lambda row: row["id"]):
        raise ValidationFailure("Video Observation Graph edges are not canonical")
    if value["contradictions"] != sorted(
        value["contradictions"], key=lambda row: row["id"]
    ):
        raise ValidationFailure("Video Observation Graph contradictions are not canonical")
    if value["surface_runs"] != sorted(
        value["surface_runs"], key=lambda row: (row["surface"], row["job_id"])
    ):
        raise ValidationFailure("Video Observation Graph surface runs are not canonical")
    if len(node_ids) != len(set(node_ids)):
        raise ValidationFailure("Video Observation Graph node IDs must be unique")
    if len(edge_ids) != len(set(edge_ids)):
        raise ValidationFailure("Video Observation Graph edge IDs must be unique")
    known_nodes = set(node_ids)
    for edge in value["edges"]:
        if edge["u"] not in known_nodes or edge["v"] not in known_nodes:
            raise ValidationFailure(f"VOG edge {edge['id']} has a dangling endpoint")
    source_nodes = [row for row in value["nodes"] if row["node_type"] == "source"]
    if len(source_nodes) != 1 or source_nodes[0]["data"] != value["source"]:
        raise ValidationFailure("VOG must contain exactly one matching source node")
    unsupported_node_types = sorted(
        {
            row["node_type"]
            for row in value["nodes"]
            if row["node_type"]
            not in {"source", "observation", "measurement", "segment"}
        }
    )
    if unsupported_node_types:
        raise ValidationFailure(
            "VOG contains node types without a v1.0 semantic validator: "
            + ", ".join(unsupported_node_types)
        )
    run_evidence = {
        (row["surface"], row["request_hash"], row["raw_response_hash"])
        for row in value["surface_runs"]
    }
    observations = [
        row
        for row in value["nodes"]
        if row["node_type"] in {"observation", "measurement", "segment"}
    ]
    observation_ids: set[str] = set()
    for node in observations:
        observation = node["data"]
        validate_instance("normalized_video_observation", observation, root)
        observation_id = observation["observation_id"]
        if observation_id in observation_ids:
            raise ValidationFailure("VOG normalized observation IDs must be unique")
        observation_ids.add(observation_id)
        if (
            observation["source_id"] != value["source"]["source_id"]
            or observation["source_sha256"] != value["source"]["sha256"]
        ):
            raise ValidationFailure(f"{observation_id} crosses the VOG source boundary")
        if not _inside(observation["interval"], value["authorized_interval"]):
            raise ValidationFailure(f"{observation_id} crosses the VOG time boundary")
        expected_node_type = (
            "measurement"
            if observation["evidence_class"] in {"measured", "detected"}
            else "segment"
            if observation["layer"] == "segment"
            else "observation"
        )
        if node["node_type"] != expected_node_type:
            raise ValidationFailure(
                f"{observation_id} evidence class does not match its VOG node type"
            )
        provenance = observation["provenance"]
        evidence_key = (
            provenance["surface"],
            provenance["request_hash"],
            provenance["raw_response_hash"],
        )
        if (
            provenance["surface"] != "local_measurement"
            and evidence_key not in run_evidence
        ):
            raise ValidationFailure(
                f"{observation_id} provenance is detached from declared surface runs"
            )
    semantic_count = sum(
        node["node_type"] in {"observation", "segment"} for node in observations
    )
    measurement_count = sum(
        node["node_type"] == "measurement" for node in observations
    )
    report = value["fusion_report"]
    if report["semantic_observations"] != semantic_count:
        raise ValidationFailure("VOG semantic observation count does not match nodes")
    if report["measurement_observations"] != measurement_count:
        raise ValidationFailure("VOG measurement observation count does not match nodes")
    contradiction_ids = {row["id"] for row in value["contradictions"]}
    if len(contradiction_ids) != len(value["contradictions"]):
        raise ValidationFailure("VOG contradiction IDs must be unique")
    for contradiction in value["contradictions"]:
        if not {
            contradiction["left_observation_id"],
            contradiction["right_observation_id"],
        } <= observation_ids:
            raise ValidationFailure(
                f"VOG contradiction {contradiction['id']} references a missing observation"
            )
    if report["contradictions"] != len(value["contradictions"]):
        raise ValidationFailure("VOG contradiction count does not match records")
    if report["support_links"] != sum(
        edge["type"] == "SUPPORTS" for edge in value["edges"]
    ):
        raise ValidationFailure("VOG support count does not match edges")
    if report["contradictions"] != sum(
        edge["type"] == "CONTRADICTS" for edge in value["edges"]
    ):
        raise ValidationFailure("VOG contradiction count does not match edges")
