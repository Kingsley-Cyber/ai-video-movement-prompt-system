#!/usr/bin/env python3
"""Local, API-neutral preprocessing for the CPCS video reverse compiler.

This utility does not perform semantic video understanding, FACS coding, pose
estimation, optical flow, SLAM, transcription, or action recognition. It
creates a deterministic evidence container for those systems:

* ``probe`` hashes a source and captures ffprobe metadata;
* ``prepare`` creates synchronized frame/audio derivatives and manifests;
* ``init-record`` creates a schema-valid extraction-record scaffold; and
* ``validate`` performs JSON Schema and cross-field integrity checks.

FFmpeg and ffprobe must be available on PATH for ``probe`` and ``prepare``.
The ``validate`` command requires the ``jsonschema`` Python package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Sequence

SCHEMA_VERSION = "cpcs-video-extraction/1.0"
DEFAULT_SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "schemas"
    / "CPCS_Video_Extraction_Record_Schema.json"
)
DEFAULT_CONFIG = (
    Path(__file__).resolve().parents[1]
    / "configs"
    / "video_to_cpcs_pipeline.yaml"
)


class PipelineError(RuntimeError):
    """Raised for deterministic, user-correctable pipeline failures."""


@dataclass(frozen=True)
class CommandResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(block_size), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def directory_manifest(path: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for candidate in sorted(p for p in path.rglob("*") if p.is_file()):
        files.append(
            {
                "path": candidate.relative_to(path).as_posix(),
                "bytes": candidate.stat().st_size,
                "sha256": sha256_file(candidate),
            }
        )
    canonical = "\n".join(f"{f['path']}\t{f['bytes']}\t{f['sha256']}" for f in files)
    return {
        "file_count": len(files),
        "total_bytes": sum(int(f["bytes"]) for f in files),
        "collection_hash": sha256_text(canonical),
        "files": files,
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PipelineError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PipelineError(f"Invalid JSON in {path}: {exc}") from exc


def require_executable(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise PipelineError(f"Required executable is not available on PATH: {name}")
    return path


def run_command(argv: Sequence[str], *, capture_stdout: bool = True) -> CommandResult:
    completed = subprocess.run(
        list(argv),
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture_stdout else subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    result = CommandResult(
        argv=list(argv),
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )
    if result.returncode != 0:
        rendered = " ".join(result.argv)
        raise PipelineError(
            f"Command failed with exit code {result.returncode}: {rendered}\n"
            f"stderr:\n{result.stderr[-4000:]}"
        )
    return result


def parse_rational(value: str | None) -> tuple[int, int] | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        fraction = Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None
    return fraction.numerator, fraction.denominator


def rational_to_float(value: str | None) -> float | None:
    parsed = parse_rational(value)
    if not parsed:
        return None
    numerator, denominator = parsed
    return numerator / denominator


def select_stream(probe: dict[str, Any], codec_type: str) -> dict[str, Any] | None:
    for stream in probe.get("streams", []):
        if stream.get("codec_type") == codec_type:
            return stream
    return None


def media_type_for(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def probe_source(video: Path) -> dict[str, Any]:
    require_executable("ffprobe")
    if not video.is_file():
        raise PipelineError(f"Source video does not exist or is not a file: {video}")

    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-show_chapters",
            "-count_frames",
            "-of",
            "json",
            str(video),
        ]
    )
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise PipelineError(f"ffprobe returned invalid JSON: {exc}") from exc

    video_stream = select_stream(raw, "video")
    audio_stream = select_stream(raw, "audio")
    if video_stream is None:
        raise PipelineError("No video stream was found in the source asset")

    duration_candidates = [
        raw.get("format", {}).get("duration"),
        video_stream.get("duration"),
    ]
    duration_s: float | None = None
    for candidate in duration_candidates:
        try:
            if candidate is not None:
                duration_s = float(candidate)
                break
        except (TypeError, ValueError):
            continue
    if duration_s is None or duration_s <= 0:
        raise PipelineError("Could not determine a positive source duration")

    avg_fps = rational_to_float(video_stream.get("avg_frame_rate"))
    nominal_fps = rational_to_float(video_stream.get("r_frame_rate"))
    rate_mode = "unknown"
    if avg_fps and nominal_fps:
        rate_mode = "constant" if abs(avg_fps - nominal_fps) <= 1e-4 else "variable"

    time_base = parse_rational(video_stream.get("time_base")) or (1, 1_000_000)
    audio_time_base = parse_rational(audio_stream.get("time_base")) if audio_stream else None

    return {
        "schema": "cpcs-source-probe/1.0",
        "created_at": utc_now(),
        "source": {
            "path": str(video.resolve()),
            "uri": video.resolve().as_uri(),
            "display_name": video.name,
            "bytes": video.stat().st_size,
            "content_hash": sha256_file(video),
            "media_type": media_type_for(video),
            "duration_s": duration_s,
        },
        "summary": {
            "video_stream_index": int(video_stream.get("index", 0)),
            "audio_stream_index": int(audio_stream.get("index")) if audio_stream else None,
            "width": int(video_stream.get("width", 0) or 0),
            "height": int(video_stream.get("height", 0) or 0),
            "pixel_format": video_stream.get("pix_fmt"),
            "video_codec": video_stream.get("codec_name"),
            "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
            "nominal_fps": nominal_fps,
            "average_fps": avg_fps,
            "frame_rate_mode": rate_mode,
            "video_time_base": {"numerator": time_base[0], "denominator": time_base[1]},
            "audio_time_base": (
                {"numerator": audio_time_base[0], "denominator": audio_time_base[1]}
                if audio_time_base
                else None
            ),
            "audio_sample_rate_hz": (
                int(audio_stream.get("sample_rate"))
                if audio_stream and audio_stream.get("sample_rate")
                else None
            ),
            "rotation": (video_stream.get("tags") or {}).get("rotate"),
        },
        "ffprobe": raw,
        "command": result.argv,
        "ffprobe_stderr": result.stderr,
    }


def resolve_clip(probe: dict[str, Any], start: float, duration: float | None, maximum: float) -> tuple[float, float]:
    total = float(probe["source"]["duration_s"])
    if start < 0 or start >= total:
        raise PipelineError(f"--start must be in [0, {total}); got {start}")
    available = total - start
    resolved = available if duration is None else duration
    if resolved <= 0:
        raise PipelineError("--duration must be positive")
    resolved = min(resolved, available)
    if resolved > maximum:
        raise PipelineError(
            f"Requested clip duration {resolved:.3f}s exceeds --max-duration {maximum:.3f}s. "
            "Use a shorter interval or explicitly increase --max-duration after rights and cost review."
        )
    return start, resolved


def extract_frame_timestamps(video: Path, start: float, duration: float, output: Path) -> dict[str, Any]:
    interval = f"{start}%+{duration}"
    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-read_intervals",
            interval,
            "-show_frames",
            "-show_entries",
            "frame=best_effort_timestamp_time,pkt_pts_time,pkt_dts_time,pkt_duration_time,key_frame,pict_type,coded_picture_number,display_picture_number",
            "-of",
            "json",
            str(video),
        ]
    )
    raw = json.loads(result.stdout)
    frames = raw.get("frames", [])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for ordinal, frame in enumerate(frames):
            timestamp = frame.get("best_effort_timestamp_time") or frame.get("pkt_pts_time")
            record = {
                "ordinal": ordinal,
                "source_time_s": float(timestamp) if timestamp is not None else None,
                "packet_dts_s": float(frame["pkt_dts_time"]) if frame.get("pkt_dts_time") is not None else None,
                "duration_s": float(frame["pkt_duration_time"]) if frame.get("pkt_duration_time") is not None else None,
                "key_frame": bool(int(frame.get("key_frame", 0))),
                "picture_type": frame.get("pict_type"),
                "coded_picture_number": frame.get("coded_picture_number"),
                "display_picture_number": frame.get("display_picture_number"),
            }
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return {
        "record_count": len(frames),
        "uri": output.resolve().as_uri(),
        "content_hash": sha256_file(output),
        "command": result.argv,
    }


def ffmpeg_extract_frames(
    video: Path,
    output_pattern: Path,
    start: float,
    duration: float,
    fps: float,
    max_width: int,
) -> list[str]:
    output_pattern.parent.mkdir(parents=True, exist_ok=True)
    vf = f"fps={fps:.8g},scale='min({max_width},iw)':-2"
    argv = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{start:.9f}",
        "-t",
        f"{duration:.9f}",
        "-i",
        str(video),
        "-map",
        "0:v:0",
        "-an",
        "-vf",
        vf,
        "-q:v",
        "2",
        "-start_number",
        "0",
        str(output_pattern),
    ]
    run_command(argv, capture_stdout=False)
    return argv


def write_resample_map(output: Path, frame_files: Iterable[Path], start: float, fps: float) -> dict[str, Any]:
    records = []
    for ordinal, frame_path in enumerate(sorted(frame_files)):
        records.append(
            {
                "ordinal": ordinal,
                "derived_time_s": ordinal / fps,
                "source_time_estimate_s": start + ordinal / fps,
                "file": frame_path.name,
                "content_hash": sha256_file(frame_path),
            }
        )
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return {
        "record_count": len(records),
        "sampling_fps": fps,
        "mapping_formula": "source_time_estimate_s = clip_start_s + ordinal / sampling_fps",
        "warning": "This is a resampled derivative map, not an original variable-frame-rate frame identity map.",
        "uri": output.resolve().as_uri(),
        "content_hash": sha256_file(output),
    }


def prepare_derivatives(args: argparse.Namespace) -> dict[str, Any]:
    require_executable("ffmpeg")
    require_executable("ffprobe")
    video = Path(args.video).expanduser().resolve()
    workdir = Path(args.workdir).expanduser().resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    probe_path = workdir / "source_probe.json"
    probe = probe_source(video)
    write_json(probe_path, probe)
    start, duration = resolve_clip(probe, args.start, args.duration, args.max_duration)

    commands: list[list[str]] = []
    derivative_summaries: dict[str, Any] = {}
    timestamps = extract_frame_timestamps(
        video, start, duration, workdir / "source_frame_timestamps.jsonl"
    )

    frame_jobs = [
        ("semantic", float(args.semantic_fps), int(args.semantic_max_width)),
        ("performance", float(args.performance_fps), int(args.performance_max_width)),
        ("face", float(args.face_fps), int(args.face_max_width)),
    ]
    for name, fps, max_width in frame_jobs:
        if fps <= 0:
            raise PipelineError(f"{name} FPS must be positive")
        directory = workdir / "derivatives" / f"{name}_frames"
        pattern = directory / f"{name}_%08d.jpg"
        command = ffmpeg_extract_frames(video, pattern, start, duration, fps, max_width)
        commands.append(command)
        files = sorted(directory.glob("*.jpg"))
        map_path = directory / "resample_map.jsonl"
        map_summary = write_resample_map(map_path, files, start, fps)
        derivative_summaries[name] = {
            "directory": directory.resolve().as_uri(),
            "fps": fps,
            "max_width": max_width,
            "frames": directory_manifest(directory),
            "resample_map": map_summary,
        }

    audio_stream_index = probe["summary"].get("audio_stream_index")
    audio_summary: dict[str, Any]
    if audio_stream_index is None:
        audio_summary = {
            "present": False,
            "warning": "No audio stream was detected; audio derivative was not created.",
        }
    else:
        audio_path = workdir / "derivatives" / "audio_16k_mono.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{start:.9f}",
            "-t",
            f"{duration:.9f}",
            "-i",
            str(video),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(args.audio_sample_rate),
            "-c:a",
            "pcm_s16le",
            str(audio_path),
        ]
        run_command(audio_command, capture_stdout=False)
        commands.append(audio_command)
        audio_summary = {
            "present": True,
            "uri": audio_path.resolve().as_uri(),
            "bytes": audio_path.stat().st_size,
            "content_hash": sha256_file(audio_path),
            "sample_rate_hz": int(args.audio_sample_rate),
            "channels": 1,
        }

    config_hash = sha256_file(DEFAULT_CONFIG) if DEFAULT_CONFIG.exists() else None
    manifest = {
        "schema": "cpcs-video-preparation-manifest/1.0",
        "created_at": utc_now(),
        "source_probe_uri": probe_path.resolve().as_uri(),
        "source_hash": probe["source"]["content_hash"],
        "clip": {
            "start_s": start,
            "duration_s": duration,
            "end_s": start + duration,
            "authority": "source_pts",
            "interval_semantics": "half_open",
        },
        "policy": {
            "maximum_allowed_duration_s": args.max_duration,
            "pipeline_config_uri": DEFAULT_CONFIG.resolve().as_uri() if DEFAULT_CONFIG.exists() else None,
            "pipeline_config_hash": config_hash,
        },
        "source_frame_timestamps": timestamps,
        "derivatives": derivative_summaries,
        "audio": audio_summary,
        "commands": commands,
        "verification": {
            "source_hash_recomputed": sha256_file(video) == probe["source"]["content_hash"],
            "all_requested_frame_sets_nonempty": all(
                summary["frames"]["file_count"] > 1 for summary in derivative_summaries.values()
            ),
            "time_authority": "source_pts",
            "warning": (
                "Semantic, performance, and face images are uniformly resampled derivatives. "
                "Use source_frame_timestamps.jsonl for source-frame timing and specialist tracks."
            ),
        },
    }
    manifest_path = workdir / "preparation_manifest.json"
    write_json(manifest_path, manifest)
    return {"manifest_path": str(manifest_path), "manifest": manifest}


def probe_command(args: argparse.Namespace) -> int:
    video = Path(args.video).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    probe = probe_source(video)
    write_json(output, probe)
    print(json.dumps({"output": str(output), "source": probe["source"], "summary": probe["summary"]}, indent=2))
    return 0


def prepare_command(args: argparse.Namespace) -> int:
    result = prepare_derivatives(args)
    manifest = result["manifest"]
    concise = {
        "manifest_path": result["manifest_path"],
        "clip": manifest["clip"],
        "frame_counts": {
            name: value["frames"]["file_count"] for name, value in manifest["derivatives"].items()
        },
        "audio_present": manifest["audio"]["present"],
        "verification": manifest["verification"],
    }
    print(json.dumps(concise, indent=2))
    return 0


def make_scaffold(video: Path, probe: dict[str, Any], config: Path) -> dict[str, Any]:
    source = probe["source"]
    summary = probe["summary"]
    video_time_base = summary.get("video_time_base") or {"numerator": 1, "denominator": 1_000_000}
    audio_time_base = summary.get("audio_time_base")
    frame_rate_mode = summary.get("frame_rate_mode") or "unknown"
    config_hash = sha256_file(config) if config.exists() else None
    now = utc_now()
    return {
        "$schema": str(DEFAULT_SCHEMA),
        "schema_version": SCHEMA_VERSION,
        "record_id": "EXTRACT-" + source["content_hash"].split(":", 1)[1][:16].upper(),
        "record_type": "video_extraction",
        "title": f"Video extraction: {source.get('display_name', video.name)}",
        "description": "Initialized extraction record. Add specialist tracks, semantic observations, human review, and transfer policy before compilation.",
        "source": {
            "uri": source.get("uri", video.resolve().as_uri()),
            "content_hash": source["content_hash"],
            "duration_s": float(source["duration_s"]),
            "media_type": source.get("media_type", media_type_for(video)),
            "display_name": source.get("display_name", video.name),
            "container": probe.get("ffprobe", {}).get("format", {}).get("format_name"),
            "video_stream_index": int(summary.get("video_stream_index", 0)),
            "audio_stream_index": summary.get("audio_stream_index"),
            "source_type": "local_file",
            "source_is_synthetic_example": False,
        },
        "rights": {
            "basis": "unknown",
            "allowed_uses": ["analysis", "evaluation"],
            "prohibited_transfer": [
                "source_face_embedding",
                "source_voice_embedding",
                "exact_dialogue_text_in_target",
                "logos",
                "copyrighted_music",
                "distinctive_choreography_geometry",
            ],
            "identity_policy": "local_tracking_only",
            "voice_policy": "transcript_only",
            "retention_policy": "Define before external processing or distribution.",
            "consent_status": "unknown",
            "review_notes": "Rights and consent review is blocking before generation-reference use.",
        },
        "timebase": {
            "authority": "source_pts",
            "video_time_base": video_time_base,
            "audio_time_base": audio_time_base,
            "nominal_fps": summary.get("nominal_fps"),
            "average_fps": summary.get("average_fps"),
            "frame_rate_mode": frame_rate_mode,
            "timestamp_map_required": frame_rate_mode != "constant",
            "timestamp_map_uri": None,
            "audio_sample_rate_hz": summary.get("audio_sample_rate_hz"),
            "interval_semantics": "half_open",
        },
        "pipeline": {
            "run_id": "RUN-" + source["content_hash"].split(":", 1)[1][:12].upper(),
            "created_at": now,
            "completed_at": None,
            "status": "initialized",
            "configuration_uri": config.resolve().as_uri() if config.exists() else str(config),
            "configuration_hash": config_hash,
            "tools": [
                {
                    "name": "ffprobe",
                    "version": probe.get("ffprobe", {}).get("program_version", {}).get("version", "external"),
                    "configuration_hash": None,
                    "model_id": None,
                    "prompt_hash": None,
                    "runtime": os.name,
                }
            ],
            "commands_uri": None,
        },
        "segments": [],
        "observations": [],
        "tracks": {},
        "transfer_core": {
            "preserve": [],
            "transform": [],
            "exclude": [
                {
                    "path": "/source/identity",
                    "reason": "Identity transfer is excluded by default.",
                    "source_refs": [],
                    "target_representation": None,
                    "tolerance": 0.0,
                },
                {
                    "path": "/source/voice_identity",
                    "reason": "Voice-identity transfer is excluded by default.",
                    "source_refs": [],
                    "target_representation": None,
                    "tolerance": 0.0,
                },
            ],
            "similarity_budget": {
                "temporal_structure": 0.8,
                "action_causality": 0.8,
                "camera_grammar": 0.6,
                "surface_appearance": 0.15,
                "identity": 0.0,
                "voice_identity": 0.0,
            },
            "target_duration_s": None,
            "normalization_notes": "Define after evidence review.",
        },
        "provenance": {
            "extractors": [
                {
                    "name": "video_to_cpcs_reference_pipeline.py",
                    "version": "1.0.0",
                    "configuration_hash": config_hash,
                    "model_id": None,
                    "prompt_hash": None,
                    "runtime": f"python-{sys.version_info.major}.{sys.version_info.minor}",
                }
            ],
            "source_artifacts": [
                {
                    "artifact_id": "SOURCE-VIDEO",
                    "uri": source.get("uri", video.resolve().as_uri()),
                    "content_hash": source["content_hash"],
                    "role": "source video",
                }
            ],
            "patch_history": [],
        },
        "review": {
            "status": "not_started",
            "required_count": 1,
            "resolved_count": 0,
            "blocking_count": 1,
            "notes": "Rights review is required before compilation.",
        },
        "extensions": {},
    }


def init_record_command(args: argparse.Namespace) -> int:
    video = Path(args.video).expanduser().resolve()
    probe_path = Path(args.probe).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    config = Path(args.config).expanduser().resolve()
    probe = read_json(probe_path)
    if probe.get("source", {}).get("content_hash") != sha256_file(video):
        raise PipelineError("Probe manifest hash does not match the supplied video")
    record = make_scaffold(video, probe, config)
    write_json(output, record)
    print(json.dumps({"output": str(output), "record_id": record["record_id"], "status": record["pipeline"]["status"]}, indent=2))
    return 0


def collect_ids(items: Iterable[dict[str, Any]], field: str) -> list[str]:
    return [str(item[field]) for item in items if field in item]


def semantic_validation(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    duration = float(record.get("source", {}).get("duration_s", 0) or 0)

    collections = [
        ("segments", record.get("segments", []), "segment_id"),
        ("observations", record.get("observations", []), "observation_id"),
    ]
    for label, items, field in collections:
        ids = collect_ids(items, field)
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        if duplicates:
            errors.append(f"Duplicate {field} values in {label}: {duplicates}")

    track_items = list(record.get("tracks", {}).values())
    track_ids = collect_ids(track_items, "track_id")
    duplicates = sorted({value for value in track_ids if track_ids.count(value) > 1})
    if duplicates:
        errors.append(f"Duplicate track_id values: {duplicates}")

    def check_range(label: str, range_value: dict[str, Any]) -> None:
        start = float(range_value.get("start_s", -1))
        end = float(range_value.get("end_s", -1))
        if end < start:
            errors.append(f"{label}: end_s {end} is before start_s {start}")
        if start < 0:
            errors.append(f"{label}: start_s is negative")
        if duration > 0 and end > duration + 1e-6:
            errors.append(f"{label}: end_s {end} exceeds source duration {duration}")

    for segment in record.get("segments", []):
        check_range(f"segment {segment.get('segment_id')}", segment.get("time_range", {}))
    for observation in record.get("observations", []):
        check_range(f"observation {observation.get('observation_id')}", observation.get("time_range", {}))
    for key, track in record.get("tracks", {}).items():
        check_range(f"track {key}", track.get("coverage", {}))

    segment_ids = set(collect_ids(record.get("segments", []), "segment_id"))
    observation_ids = set(collect_ids(record.get("observations", []), "observation_id"))
    track_id_set = set(track_ids)
    known_refs = segment_ids | observation_ids | track_id_set
    for observation in record.get("observations", []):
        for ref in observation.get("segment_refs", []):
            if ref not in segment_ids:
                errors.append(f"observation {observation.get('observation_id')} references unknown segment {ref}")
        for ref in observation.get("evidence_refs", []):
            if ref not in known_refs:
                # External immutable evidence IDs are permitted when namespaced.
                if not ref.startswith(("ASSET-", "FRAME-", "AUDIO-", "SEMANTIC-", "HUMAN-")):
                    errors.append(f"observation {observation.get('observation_id')} references unknown evidence {ref}")

    for list_name in ("preserve", "transform", "exclude"):
        for item in record.get("transfer_core", {}).get(list_name, []):
            for ref in item.get("source_refs", []):
                if ref not in known_refs:
                    errors.append(f"transfer_core.{list_name} references unknown source {ref}")

    if record.get("rights", {}).get("basis") == "unknown":
        # A valid scaffold can be unknown, but compilation must not be claimed.
        status = record.get("pipeline", {}).get("status")
        if status in {"compiled", "resolved"} and "generation_reference" in record.get("rights", {}).get("allowed_uses", []):
            errors.append("Rights basis is unknown but the record is resolved/compiled for generation-reference use")

    return errors


def validate_record(record_path: Path, schema_path: Path) -> dict[str, Any]:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:  # pragma: no cover
        raise PipelineError("jsonschema is required for validation: pip install jsonschema") from exc

    record = read_json(record_path)
    schema = read_json(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    schema_errors = sorted(validator.iter_errors(record), key=lambda e: list(e.absolute_path))
    rendered_schema_errors = [
        f"/{'/'.join(str(x) for x in error.absolute_path)}: {error.message}"
        for error in schema_errors
    ]
    semantic_errors = semantic_validation(record) if isinstance(record, dict) else ["Top-level record is not an object"]
    return {
        "record": str(record_path),
        "schema": str(schema_path),
        "valid": not rendered_schema_errors and not semantic_errors,
        "schema_error_count": len(rendered_schema_errors),
        "semantic_error_count": len(semantic_errors),
        "schema_errors": rendered_schema_errors,
        "semantic_errors": semantic_errors,
        "record_hash": sha256_file(record_path),
        "schema_hash": sha256_file(schema_path),
    }


def validate_command(args: argparse.Namespace) -> int:
    result = validate_record(
        Path(args.record).expanduser().resolve(),
        Path(args.schema).expanduser().resolve(),
    )
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare and validate evidence containers for Video-to-CPCS reverse compilation."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser("probe", help="Hash a source and capture ffprobe metadata")
    probe.add_argument("--video", required=True, help="Path to the authorized source video")
    probe.add_argument("--output", required=True, help="Output JSON probe manifest")
    probe.set_defaults(func=probe_command)

    prepare = subparsers.add_parser(
        "prepare", help="Create synchronized semantic, performance, face, timestamp, and audio derivatives"
    )
    prepare.add_argument("--video", required=True)
    prepare.add_argument("--workdir", required=True)
    prepare.add_argument("--start", type=float, default=0.0)
    prepare.add_argument("--duration", type=float, default=None)
    prepare.add_argument("--max-duration", type=float, default=120.0)
    prepare.add_argument("--semantic-fps", type=float, default=1.0)
    prepare.add_argument("--performance-fps", type=float, default=24.0)
    prepare.add_argument("--face-fps", type=float, default=30.0)
    prepare.add_argument("--semantic-max-width", type=int, default=1280)
    prepare.add_argument("--performance-max-width", type=int, default=1280)
    prepare.add_argument("--face-max-width", type=int, default=1920)
    prepare.add_argument("--audio-sample-rate", type=int, default=16000)
    prepare.set_defaults(func=prepare_command)

    init_record = subparsers.add_parser(
        "init-record", help="Create a schema-valid extraction-record scaffold from a probe manifest"
    )
    init_record.add_argument("--video", required=True)
    init_record.add_argument("--probe", required=True)
    init_record.add_argument("--output", required=True)
    init_record.add_argument("--config", default=str(DEFAULT_CONFIG))
    init_record.set_defaults(func=init_record_command)

    validate = subparsers.add_parser("validate", help="Validate an extraction record")
    validate.add_argument("--record", required=True)
    validate.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    validate.set_defaults(func=validate_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("error: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
