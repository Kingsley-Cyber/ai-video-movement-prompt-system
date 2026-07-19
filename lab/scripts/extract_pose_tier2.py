#!/usr/bin/env python3
"""Tier-2 measurement lane: 2D whole-body pose tracks from the analysis proxy.

Runbook Step 3 (RUNBOOK_reference_to_kinematic_truth.md). Reads the source manifest written by the
research package's extract_video_manifest.py, runs per-frame 2D pose (MediaPipe), tracks actors
across frames, and emits:

  1. <out>/pose_frames_raw.jsonl        dense per-frame landmarks (Tier-3 feedstock; not schema-bound)
  2. <out>/observations/pose_tier2.jsonl  keyframed joint-track observation records conforming to
     CPCS_Video_Observation_Record_Schema.json, ready for merge_video_observations.py

Backends:
  - MediaPipe Tasks PoseLandmarker (multi-person) when a .task model is supplied via --model:
      curl -L -o pose_landmarker_full.task \
        https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task
  - Legacy mp.solutions.pose fallback (SINGLE person) when no model file is given.

Install: python3 -m pip install mediapipe opencv-python jsonschema

Honest bounds (paper §30.12-30.13): this is 2D image-space measurement — evidence_class "detected",
units normalized to the image, camera motion NOT separated from subject motion. Tier 3 (3D + camera
solve) refines it. Never relabel these records "measured".
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# MediaPipe landmark indices -> the compact joint set the lab keyframes
JOINTS = {
    "nose": 0,
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13, "right_elbow": 14,
    "left_wrist": 15, "right_wrist": 16,
    "left_hip": 23, "right_hip": 24,
    "left_knee": 25, "right_knee": 26,
    "left_ankle": 27, "right_ankle": 28,
}
EXTRACTOR_VERSION = "lab-pose-tier2/1.0"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--manifest", type=Path, help="source_manifest.json from extract_video_manifest.py (preferred)")
    src.add_argument("--video", type=Path, help="direct video path (requires --source-id)")
    p.add_argument("--source-id", help="source id when using --video")
    p.add_argument("--model", type=Path, default=None, help=".task PoseLandmarker model (enables multi-person)")
    p.add_argument("--num-poses", type=int, default=2, help="max people to track (tasks backend only; default 2)")
    p.add_argument("--stride", type=int, default=1, help="process every Nth frame (default 1)")
    p.add_argument("--keyframe-interval", type=float, default=0.5, help="seconds between keyframes in track records")
    p.add_argument("--min-visibility", type=float, default=0.5, help="drop landmarks below this visibility")
    p.add_argument("--min-detection-confidence", type=float, default=0.5)
    p.add_argument("--output-dir", type=Path, default=None, help="default: alongside the manifest")
    return p.parse_args()


def load_source(args) -> tuple[Path, str, str | None, float, Path]:
    """Return (video_path, source_id, source_sha256, fallback_fps, out_dir)."""
    if args.manifest:
        m = json.loads(args.manifest.read_text())
        src = m.get("source", {})
        source_id = src.get("id") or m.get("source_id") or "source"
        source_sha = src.get("sha256") or m.get("source_sha256")
        base = args.manifest.parent
        proxy = next((base / a.get("path", a.get("id", "")) for a in m.get("assets", [])
                      if isinstance(a, dict) and a.get("id") == "analysis_proxy"), None)
        if proxy is None or not Path(proxy).exists():
            cand = base / "analysis_proxy.mp4"
            proxy = cand if cand.exists() else Path(src.get("path", ""))
        if not Path(proxy).exists():
            sys.exit(f"error: could not locate analysis_proxy.mp4 near {args.manifest}")
        fps = float(m.get("analysis_fps", 24.0))
        return Path(proxy), source_id, source_sha, fps, args.output_dir or base
    if not args.source_id:
        sys.exit("error: --video requires --source-id (merge keys records to the manifest's source id)")
    return args.video, args.source_id, None, 24.0, args.output_dir or args.video.parent


def open_backend(args):
    """Return (mode, detect_fn) where detect_fn(bgr_frame, t_ms) -> list[person] of {joint: (x,y,vis)}."""
    try:
        import cv2  # noqa: F401
        import mediapipe as mp
    except ImportError as e:
        sys.exit(f"missing dependency ({e.name}). Install: python3 -m pip install mediapipe opencv-python jsonschema")

    import cv2

    def landmarks_to_joints(landmarks) -> dict:
        out = {}
        for name, idx in JOINTS.items():
            lm = landmarks[idx]
            vis = float(getattr(lm, "visibility", 1.0) or 0.0)
            out[name] = (float(lm.x), float(lm.y), vis)
        return out

    if args.model:
        if not args.model.exists():
            sys.exit(f"model file not found: {args.model} (see --help for the download curl)")
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
        opts = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(args.model)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=args.num_poses,
            min_pose_detection_confidence=args.min_detection_confidence,
        )
        landmarker = vision.PoseLandmarker.create_from_options(opts)

        def detect(frame_bgr, t_ms: int):
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = landmarker.detect_for_video(image, t_ms)
            return [landmarks_to_joints(person) for person in (res.pose_landmarks or [])]

        return f"tasks:{args.model.name} num_poses={args.num_poses}", detect

    # Legacy fallback: single person only
    pose = mp.solutions.pose.Pose(static_image_mode=False, model_complexity=1,
                                  min_detection_confidence=args.min_detection_confidence)

    def detect(frame_bgr, t_ms: int):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        res = pose.process(rgb)
        if not res.pose_landmarks:
            return []
        return [landmarks_to_joints(res.pose_landmarks.landmark)]

    print("warning: no --model given -> legacy single-person backend. Multi-actor scenes need the .task model.",
          file=sys.stderr)
    return "legacy:solutions.pose single-person", detect


def centroid(joints: dict) -> tuple[float, float]:
    lh, rh = joints.get("left_hip"), joints.get("right_hip")
    if lh and rh:
        return ((lh[0] + rh[0]) / 2.0, (lh[1] + rh[1]) / 2.0)
    xs = [v[0] for v in joints.values()]
    ys = [v[1] for v in joints.values()]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


class ActorTracker:
    """Greedy nearest-centroid association. actor_A = leftmost at first sight. Keeps swap uncertainty."""

    def __init__(self):
        self.actors: dict[str, tuple[float, float]] = {}
        self.swap_suspect_frames = 0

    def assign(self, detections: list[dict]) -> list[tuple[str, dict]]:
        if not detections:
            return []
        if not self.actors:
            ordered = sorted(detections, key=lambda d: centroid(d)[0])
            for i, det in enumerate(ordered):
                self.actors[f"actor_{chr(ord('A') + i)}"] = centroid(det)
            return [(aid, det) for aid, det in zip(sorted(self.actors), ordered)]
        assigned, used = [], set()
        for aid, last in sorted(self.actors.items()):
            best, best_d = None, 1e9
            for i, det in enumerate(detections):
                if i in used:
                    continue
                c = centroid(det)
                d = (c[0] - last[0]) ** 2 + (c[1] - last[1]) ** 2
                if d < best_d:
                    best, best_d = i, d
            if best is not None:
                used.add(best)
                if best_d > 0.09:  # jumped >~0.3 of frame width: possible identity swap or cut
                    self.swap_suspect_frames += 1
                self.actors[aid] = centroid(detections[best])
                assigned.append((aid, detections[best]))
        for i, det in enumerate(detections):  # brand-new entrant
            if i not in used:
                aid = f"actor_{chr(ord('A') + len(self.actors))}"
                self.actors[aid] = centroid(det)
                assigned.append((aid, det))
        return assigned


def keyframe(track: list[dict], interval: float) -> list[dict]:
    out, next_t = [], 0.0
    for s in track:
        if s["t"] + 1e-9 >= next_t:
            out.append(s)
            next_t = s["t"] + interval
    if track and (not out or out[-1]["t"] != track[-1]["t"]):
        out.append(track[-1])
    return out


def make_record(seq: int, source_id: str, actor: str, joint: str,
                samples: list[dict], backend: str, clip_len: float, params: dict) -> dict:
    # NOTE: the record schema is additionalProperties:false — the source binding is source_id only
    # (no top-level source_sha256); the manifest carries the hash.
    vis = [s["visibility"] for s in samples]
    return {
        "record_id": f"pose2d.{actor}.{joint}.{seq:04d}",
        "source_id": source_id,
        "time_range": {"start_s": samples[0]["t"], "end_s": samples[-1]["t"]},
        "clock": "source_seconds",
        "layer": "body_pose",
        "claim": {
            "type": "joint_track_2d",
            "value": {"actor": actor, "joint": joint,
                      "positions": [{"t": s["t"], "x": s["x"], "y": s["y"], "visibility": s["visibility"]}
                                    for s in samples]},
            "units": "normalized_image_xy",
            "coordinate_system": "image_topleft_x_right_y_down",
            "vocabulary": "lab.pose_tier2/1.0",
        },
        "evidence_class": "detected",
        "confidence": round(sum(vis) / len(vis), 4),
        "extractor": {"name": "mediapipe_pose", "version": EXTRACTOR_VERSION,
                      "model": backend, "parameters": params},
        "evidence": [{"asset": "analysis_proxy",
                      "locator": f"t={samples[0]['t']:.3f}-{samples[-1]['t']:.3f}s",
                      "description": "2D pose keyframes from the constant-fps analysis proxy"}],
        "quality_flags": (["camera_motion_not_separated"] +
                          (["short_clip"] if clip_len < 2.0 else [])),
        "notes": "Tier-2 2D image-space track; camera and subject motion are entangled (paper 30.12).",
    }


def main() -> None:
    args = parse_args()
    video, source_id, _source_sha, fallback_fps, out_dir = load_source(args)
    backend_name, detect = open_backend(args)

    import cv2
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        sys.exit(f"error: cannot open {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or fallback_fps
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "observations").mkdir(exist_ok=True)
    raw_path = out_dir / "pose_frames_raw.jsonl"
    obs_path = out_dir / "observations" / "pose_tier2.jsonl"

    tracker = ActorTracker()
    tracks: dict[tuple[str, str], list[dict]] = {}
    frames_seen = frames_with_pose = 0

    with raw_path.open("w") as raw:
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % args.stride:
                idx += 1
                continue
            t = idx / fps
            people = detect(frame, int(t * 1000))
            frames_seen += 1
            frames_with_pose += bool(people)
            assigned = tracker.assign(people)
            raw.write(json.dumps({"frame": idx, "t": round(t, 4),
                                  "actors": {aid: {j: [round(v, 4) for v in xyv]
                                                   for j, xyv in joints.items()}
                                             for aid, joints in assigned}}) + "\n")
            for aid, joints in assigned:
                for jname, (x, y, vis) in joints.items():
                    if vis < args.min_visibility:
                        continue
                    tracks.setdefault((aid, jname), []).append(
                        {"t": round(t, 4), "x": round(x, 4), "y": round(y, 4), "visibility": round(vis, 3)})
            idx += 1
    cap.release()
    clip_len = idx / fps if fps else 0.0

    params = {"stride": args.stride, "keyframe_interval_s": args.keyframe_interval,
              "min_visibility": args.min_visibility, "fps": fps}
    records = []
    for seq, ((aid, jname), samples) in enumerate(sorted(tracks.items())):
        kf = keyframe(samples, args.keyframe_interval)
        if len(kf) >= 2:
            records.append(make_record(seq, source_id, aid, jname, kf,
                                       backend_name, clip_len, params))
    # root motion = hip midpoint per actor
    actors = sorted({aid for aid, _ in tracks})
    for seq, aid in enumerate(actors):
        lh, rh = tracks.get((aid, "left_hip"), []), tracks.get((aid, "right_hip"), [])
        by_t = {s["t"]: s for s in lh}
        mids = [{"t": s["t"], "x": round((s["x"] + by_t[s["t"]]["x"]) / 2, 4),
                 "y": round((s["y"] + by_t[s["t"]]["y"]) / 2, 4),
                 "visibility": round(min(s["visibility"], by_t[s["t"]]["visibility"]), 3)}
                for s in rh if s["t"] in by_t]
        kf = keyframe(mids, args.keyframe_interval)
        if len(kf) >= 2:
            records.append(make_record(9000 + seq, source_id, aid, "root_hip_mid", kf,
                                       backend_name, clip_len, params))

    with obs_path.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    # self-validate against the package schema when present
    schema_path = next((p for p in [
        Path("research/CPCS_FACS_Laban_AI_Video_Research_Package_v1.2/schemas/CPCS_Video_Observation_Record_Schema.json"),
        Path(__file__).resolve().parents[2] / "research/CPCS_FACS_Laban_AI_Video_Research_Package_v1.2/schemas/CPCS_Video_Observation_Record_Schema.json",
    ] if p.exists()), None)
    if schema_path:
        try:
            import jsonschema
            schema = json.loads(schema_path.read_text())
            bad = 0
            for r in records:
                try:
                    jsonschema.validate(r, schema)
                except jsonschema.ValidationError as e:
                    bad += 1
                    print(f"schema-invalid {r['record_id']}: {e.message}", file=sys.stderr)
            print(f"schema check: {len(records) - bad}/{len(records)} records valid "
                  f"({schema_path.name})")
        except ImportError:
            print("note: jsonschema not installed; skipped self-validation", file=sys.stderr)
    else:
        print("note: package schema not found; skipped self-validation", file=sys.stderr)

    detect_rate = (frames_with_pose / frames_seen) if frames_seen else 0.0
    print(f"backend: {backend_name}")
    print(f"frames: {frames_seen} processed, pose in {frames_with_pose} ({detect_rate:.0%})")
    print(f"actors: {actors or 'none'} | possible-swap frames: {tracker.swap_suspect_frames}")
    print(f"wrote {raw_path}  (dense raw)")
    print(f"wrote {obs_path}  ({len(records)} track records, keyframe {args.keyframe_interval}s)")
    print("next: merge_video_observations.py --inputs .../observations/*.jsonl  (runbook Step 4)")
    if detect_rate < 0.6:
        print("warning: low detection rate — try a clearer clip, lower stride, or the full/heavy model",
              file=sys.stderr)


if __name__ == "__main__":
    main()
