#!/usr/bin/env python3
"""Thin CLI for the governed local pose-measurement adapter."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lab.second_brain.src.measurement import (
    execute_pose_measurement_job,
    make_pose_measurement_job,
)
from lab.second_brain.src.validate import REPO_ROOT


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--manifest", type=Path, help="source_manifest.json containing an analysis proxy")
    source.add_argument("--video", type=Path, help="exact local video source")
    parser.add_argument("--source-id", help="required with --video")
    parser.add_argument("--asset-ref", help="immutable source asset reference; defaults to source ID")
    parser.add_argument("--rights-scope", required=True, choices=("authorized", "original", "licensed"))
    parser.add_argument("--model", type=Path, required=True, help="MediaPipe Tasks PoseLandmarker .task file")
    parser.add_argument("--model-version", required=True, help="exact model release or content version")
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--end", type=float, required=True)
    parser.add_argument("--num-poses", type=int, default=2)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--keyframe-interval", type=float, default=0.5)
    parser.add_argument("--min-visibility", type=float, default=0.5)
    parser.add_argument("--min-detection-confidence", type=float, default=0.5)
    parser.add_argument("--created-at", default=None, help="RFC 3339 timestamp; defaults to current UTC")
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args(argv)


def _manifest_source(path: Path) -> tuple[Path, str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    source = value.get("source", {})
    source_id = source.get("id") or value.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        raise ValueError("manifest has no source ID")
    base = path.parent
    candidates = [
        base / row.get("path", "")
        for row in value.get("assets", [])
        if isinstance(row, dict) and row.get("id") == "analysis_proxy"
    ]
    candidates.append(base / "analysis_proxy.mp4")
    video = next((candidate for candidate in candidates if candidate.is_file()), None)
    if video is None:
        raise ValueError("manifest has no resolvable analysis proxy")
    asset_ref = source.get("asset_ref") or source_id
    return video, source_id, asset_ref


def main(argv: list[str] | None = None) -> None:
    args = _arguments(argv)
    if args.manifest:
        video, source_id, manifest_asset_ref = _manifest_source(args.manifest)
        asset_ref = args.asset_ref or manifest_asset_ref
    else:
        if not args.source_id:
            raise ValueError("--video requires --source-id")
        video = args.video
        source_id = args.source_id
        asset_ref = args.asset_ref or source_id
    job = make_pose_measurement_job(
        source_id=source_id,
        asset_ref=asset_ref,
        local_path=video,
        rights_scope=args.rights_scope,
        authorized_interval={"start_s": args.start, "end_s": args.end},
        model_path=args.model,
        model_version=args.model_version,
        created_at=args.created_at or _utc_now(),
        num_poses=args.num_poses,
        stride=args.stride,
        keyframe_interval_s=args.keyframe_interval,
        min_visibility=args.min_visibility,
        min_detection_confidence=args.min_detection_confidence,
    )
    output = args.output_dir or REPO_ROOT / "work" / "measurements" / job["job_id"]
    result = execute_pose_measurement_job(job, output_root=output)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
