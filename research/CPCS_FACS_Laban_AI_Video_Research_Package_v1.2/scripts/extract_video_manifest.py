#!/usr/bin/env python3
"""Create deterministic local preprocessing assets for video-to-CPCS extraction.

The script intentionally performs no cloud/model calls. It uses ffprobe/FFmpeg
for media forensics, hashing, proxy generation, semantic-frame extraction, and
content-difference shot-boundary proposals. All timestamps remain in the source
clock and all outputs include source hashes for provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import mimetypes
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

VERSION = "1.0.0"


class ExtractionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(cmd: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr or ""
        raise ExtractionError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{stderr[-4000:]}"
        )
    return proc


def require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise ExtractionError(f"Required executable not found on PATH: {name}")
    return path


def parse_fraction(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        try:
            return float(value)
        except ValueError:
            return None


def positive_float(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) and f > 0 else None


def ffprobe_json(ffprobe: str, input_path: Path, *, count_frames: bool = True) -> dict[str, Any]:
    cmd = [
        ffprobe,
        "-v", "error",
        "-show_format",
        "-show_streams",
        "-show_chapters",
        "-show_program_version",
        "-show_library_versions",
    ]
    if count_frames:
        cmd.append("-count_frames")
    cmd.extend(["-of", "json", str(input_path)])
    return json.loads(run(cmd).stdout)


def summarize_probe(probe: dict[str, Any]) -> dict[str, Any]:
    streams = probe.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not video:
        raise ExtractionError("ffprobe found no video stream")

    fmt = probe.get("format", {})
    duration = positive_float(fmt.get("duration")) or positive_float(video.get("duration"))
    if not duration:
        raise ExtractionError("Could not determine a positive source duration")

    avg_fps = parse_fraction(video.get("avg_frame_rate"))
    real_fps = parse_fraction(video.get("r_frame_rate"))
    time_base = video.get("time_base") or "1/1000"
    try:
        tb = Fraction(time_base)
        tb_obj = {"numerator": tb.numerator, "denominator": tb.denominator}
    except (ValueError, ZeroDivisionError):
        tb_obj = {"numerator": 1, "denominator": 1000}

    frame_count = video.get("nb_read_frames") or video.get("nb_frames")
    try:
        frame_count_i = int(frame_count) if frame_count not in (None, "N/A") else None
    except (TypeError, ValueError):
        frame_count_i = None

    variable = None
    if avg_fps and real_fps:
        variable = abs(avg_fps - real_fps) > max(0.01, avg_fps * 0.002)

    return {
        "duration_s": duration,
        "width": int(video.get("width") or 0) or None,
        "height": int(video.get("height") or 0) or None,
        "codec": video.get("codec_name"),
        "pixel_format": video.get("pix_fmt"),
        "nominal_fps": avg_fps or real_fps,
        "real_fps": real_fps,
        "variable_frame_rate_candidate": variable,
        "frame_count": frame_count_i,
        "timebase": tb_obj,
        "start_time_s": float(video.get("start_time") or fmt.get("start_time") or 0.0),
        "rotation": (video.get("tags") or {}).get("rotate"),
        "has_audio": audio is not None,
        "audio": None if audio is None else {
            "codec": audio.get("codec_name"),
            "sample_rate": int(audio.get("sample_rate") or 0) or None,
            "channels": audio.get("channels"),
            "channel_layout": audio.get("channel_layout"),
        },
        "container": fmt.get("format_name"),
        "format_long_name": fmt.get("format_long_name"),
    }


def probe_duration(ffprobe: str, path: Path) -> float:
    out = run([
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ]).stdout.strip()
    duration = positive_float(out)
    if not duration:
        raise ExtractionError(f"Could not determine duration for generated asset: {path}")
    return duration


def create_proxy(ffmpeg: str, source: Path, output: Path, fps: float, max_width: int) -> None:
    vf = f"fps={fps:g},scale='min({max_width},iw)':-2:flags=lanczos"
    base = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-map", "0:v:0", "-vf", vf, "-an"]
    # Prefer H.264 for broad compatibility, fall back to MPEG-4 if unavailable.
    first = base + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium", str(output)]
    proc = subprocess.run(first, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode == 0:
        return
    second = base + ["-c:v", "mpeg4", "-q:v", "2", str(output)]
    run(second)


def extract_audio(ffmpeg: str, source: Path, output: Path) -> None:
    run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
        "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(output)
    ])


def extract_semantic_frames(ffmpeg: str, source: Path, output_dir: Path, fps: float, width: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    vf = f"fps={fps:g},scale='min({width},iw)':-2:flags=lanczos"
    run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
        "-map", "0:v:0", "-vf", vf, "-q:v", "2", str(output_dir / "frame_%06d.jpg")
    ])


def detect_scene_candidates(ffmpeg: str, source: Path, threshold: float) -> list[dict[str, Any]]:
    # metadata=print emits a frame header followed by lavfi.scene_score.
    expr = f"select='gt(scene,{threshold:g})',metadata=print"
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "info", "-i", str(source), "-map", "0:v:0", "-vf", expr, "-an", "-f", "null", "-"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise ExtractionError(f"Scene-candidate extraction failed:\n{(proc.stderr or '')[-4000:]}")

    candidates: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    header_re = re.compile(r"frame:\s*(\d+).*pts_time:([0-9.+-]+)")
    score_re = re.compile(r"lavfi\.scene_score=([0-9.eE+-]+)")
    for line in (proc.stderr or "").splitlines():
        hm = header_re.search(line)
        if hm:
            current = {"analysis_frame": int(hm.group(1)), "time_s": float(hm.group(2)), "score": None}
            continue
        sm = score_re.search(line)
        if sm and current is not None:
            current["score"] = float(sm.group(1))
            current["candidate_id"] = f"cut.{len(candidates)+1:06d}"
            candidates.append(current)
            current = None
    return candidates


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path, help="Source video")
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--source-id", default=None)
    ap.add_argument("--analysis-fps", type=float, default=24.0)
    ap.add_argument("--semantic-fps", type=float, default=1.0)
    ap.add_argument("--scene-threshold", type=float, default=0.35)
    ap.add_argument("--max-width", type=int, default=1280)
    ap.add_argument("--semantic-width", type=int, default=960)
    ap.add_argument("--duration-tolerance-s", type=float, default=0.10)
    ap.add_argument("--skip-proxies", action="store_true")
    ap.add_argument("--skip-scene-candidates", action="store_true")
    args = ap.parse_args()

    try:
        source = args.input.expanduser().resolve(strict=True)
        if not source.is_file():
            raise ExtractionError(f"Input is not a regular file: {source}")
        if args.analysis_fps <= 0 or args.semantic_fps <= 0:
            raise ExtractionError("FPS values must be positive")
        if not 0 < args.scene_threshold < 1:
            raise ExtractionError("Scene threshold must be between 0 and 1")

        ffprobe = require_binary("ffprobe")
        ffmpeg = require_binary("ffmpeg")
        out = args.output_dir.expanduser().resolve()
        out.mkdir(parents=True, exist_ok=True)

        source_hash = sha256_file(source)
        source_id = args.source_id or f"asset.{source_hash[:16]}"
        probe = ffprobe_json(ffprobe, source)
        summary = summarize_probe(probe)
        probe_path = out / "source_probe.json"
        write_json(probe_path, probe)

        assets: list[dict[str, Any]] = [{
            "id": "source",
            "role": "reference_source",
            "path": str(source),
            "sha256": source_hash,
            "bytes": source.stat().st_size,
        }, {
            "id": "source_probe",
            "role": "media_probe",
            "path": str(probe_path),
            "sha256": sha256_file(probe_path),
            "bytes": probe_path.stat().st_size,
        }]

        verification: dict[str, Any] = {
            "source_duration_positive": summary["duration_s"] > 0,
            "video_stream_present": True,
            "proxy_duration_error_s": None,
            "duration_tolerance_s": args.duration_tolerance_s,
        }

        if not args.skip_proxies:
            proxy = out / "analysis_proxy.mp4"
            create_proxy(ffmpeg, source, proxy, args.analysis_fps, args.max_width)
            proxy_duration = probe_duration(ffprobe, proxy)
            duration_error = abs(proxy_duration - summary["duration_s"])
            verification["proxy_duration_error_s"] = duration_error
            if duration_error > args.duration_tolerance_s:
                raise ExtractionError(
                    f"Proxy duration drift {duration_error:.6f}s exceeds tolerance {args.duration_tolerance_s:.6f}s"
                )
            assets.append({
                "id": "analysis_proxy",
                "role": "constant_frame_rate_analysis_proxy",
                "path": str(proxy),
                "sha256": sha256_file(proxy),
                "bytes": proxy.stat().st_size,
                "duration_s": proxy_duration,
                "fps": args.analysis_fps,
                "source_time_mapping": {"source_start_s": 0.0, "proxy_start_s": 0.0, "time_scale": 1.0},
            })

            frames_dir = out / "semantic_frames"
            extract_semantic_frames(ffmpeg, source, frames_dir, args.semantic_fps, args.semantic_width)
            frame_files = sorted(frames_dir.glob("frame_*.jpg"))
            assets.append({
                "id": "semantic_frames",
                "role": "low_rate_semantic_frames",
                "path": str(frames_dir),
                "file_count": len(frame_files),
                "fps": args.semantic_fps,
            })

            if summary["has_audio"]:
                audio = out / "audio_16k_mono.wav"
                extract_audio(ffmpeg, source, audio)
                assets.append({
                    "id": "audio_16k_mono",
                    "role": "speech_and_audio_analysis_stem",
                    "path": str(audio),
                    "sha256": sha256_file(audio),
                    "bytes": audio.stat().st_size,
                    "sample_rate": 16000,
                    "channels": 1,
                })

        candidates: list[dict[str, Any]] = []
        if not args.skip_scene_candidates:
            candidates = detect_scene_candidates(ffmpeg, source, args.scene_threshold)
        candidates_path = out / "shot_candidates.json"
        write_json(candidates_path, {
            "schema": "cpcs-shot-candidates/1.0",
            "source_id": source_id,
            "source_sha256": source_hash,
            "method": "ffmpeg_scene_score",
            "threshold": args.scene_threshold,
            "candidates": candidates,
        })
        assets.append({
            "id": "shot_candidates",
            "role": "content_difference_boundary_proposals",
            "path": str(candidates_path),
            "sha256": sha256_file(candidates_path),
            "bytes": candidates_path.stat().st_size,
            "candidate_count": len(candidates),
        })

        mime = mimetypes.guess_type(source.name)[0] or "video/unknown"
        manifest = {
            "schema": "cpcs-video-source-manifest/1.0",
            "extractor": {"name": "extract_video_manifest.py", "version": VERSION},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": {
                "id": source_id,
                "display_name": source.name,
                "uri": source.as_uri(),
                "sha256": source_hash,
                "bytes": source.stat().st_size,
                "media_type": mime if mime.startswith("video/") else "video/unknown",
                **summary,
            },
            "clock": {
                "canonical": "source_pts",
                "timebase": summary["timebase"],
                "pts_origin_s": summary["start_time_s"],
            },
            "analysis_settings": {
                "analysis_fps": args.analysis_fps,
                "semantic_fps": args.semantic_fps,
                "scene_threshold": args.scene_threshold,
                "max_width": args.max_width,
                "semantic_width": args.semantic_width,
            },
            "assets": assets,
            "verification": verification,
        }
        manifest_path = out / "source_manifest.json"
        write_json(manifest_path, manifest)
        print(json.dumps({
            "status": "ok",
            "manifest": str(manifest_path),
            "source_id": source_id,
            "duration_s": summary["duration_s"],
            "shot_candidate_count": len(candidates),
            "assets": [a["id"] for a in assets],
        }, indent=2))
        return 0
    except (ExtractionError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
