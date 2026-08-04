"""Hash-bound local pose extraction into reviewable measurement batches."""

from __future__ import annotations

import hashlib
import math
import os
import tempfile
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from .validate import (
    REPO_ROOT,
    ValidationFailure,
    canonical_json_bytes,
    sha256_value,
    validate_instance,
)

MEASUREMENT_POLICY = "cpcs-local-pose/1.0"
MAX_SELECTED_FRAMES = 100_000
JOINTS = {
    "nose": 0,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}

FrameReader = Callable[[Path, dict[str, float], int], Iterable[tuple[int, float, Any]]]
PoseDetector = Callable[[Any, int], list[dict[str, tuple[float, float, float]]]]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _exact_file(path: Path, label: str) -> Path:
    expanded = path.expanduser()
    if expanded.is_symlink():
        raise ValidationFailure(f"{label} cannot be a symlink")
    resolved = expanded.resolve()
    if not resolved.is_file():
        raise ValidationFailure(f"{label} is missing or not a file: {resolved}")
    return resolved


def _content_id(prefix: str, value: dict[str, Any]) -> str:
    return prefix + hashlib.sha256(canonical_json_bytes(value)).hexdigest()[:24]


def make_pose_measurement_job(
    *,
    source_id: str,
    asset_ref: str,
    local_path: Path,
    rights_scope: str,
    authorized_interval: dict[str, float],
    model_path: Path,
    model_version: str,
    created_at: str,
    num_poses: int = 2,
    stride: int = 1,
    keyframe_interval_s: float = 0.5,
    min_visibility: float = 0.5,
    min_detection_confidence: float = 0.5,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Create a content-addressed job bound to exact source and model bytes."""
    source = _exact_file(local_path, "measurement source")
    model = _exact_file(model_path, "pose model")
    core = {
        "schema": "cpcs.pose_measurement_job/1.0",
        "source": {
            "source_id": source_id,
            "asset_ref": asset_ref,
            "local_path": str(source),
            "sha256": _file_sha256(source),
            "rights_scope": rights_scope,
        },
        "authorized_interval": {
            "start_s": float(authorized_interval["start_s"]),
            "end_s": float(authorized_interval["end_s"]),
        },
        "detector": {
            "backend": "mediapipe_tasks_pose",
            "model_path": str(model),
            "model_sha256": _file_sha256(model),
            "model_version": model_version,
            "num_poses": num_poses,
            "stride": stride,
            "keyframe_interval_s": keyframe_interval_s,
            "min_visibility": min_visibility,
            "min_detection_confidence": min_detection_confidence,
        },
        "created_at": created_at,
    }
    value = {**core, "job_id": _content_id("pose_job_", core)}
    validate_instance("pose_measurement_job", value, root)
    if value["authorized_interval"]["end_s"] <= value["authorized_interval"]["start_s"]:
        raise ValidationFailure("authorized measurement interval must have positive duration")
    return value


def _validate_job(job: dict[str, Any], root: Path) -> tuple[Path, Path]:
    validate_instance("pose_measurement_job", job, root)
    core = {key: value for key, value in job.items() if key != "job_id"}
    if job["job_id"] != _content_id("pose_job_", core):
        raise ValidationFailure("pose measurement job content identity is invalid")
    interval = job["authorized_interval"]
    if interval["end_s"] <= interval["start_s"]:
        raise ValidationFailure("authorized measurement interval must have positive duration")
    source = _exact_file(Path(job["source"]["local_path"]), "measurement source")
    model = _exact_file(Path(job["detector"]["model_path"]), "pose model")
    if _file_sha256(source) != job["source"]["sha256"]:
        raise ValidationFailure("measurement source hash does not match exact local bytes")
    if _file_sha256(model) != job["detector"]["model_sha256"]:
        raise ValidationFailure("pose model hash does not match exact local bytes")
    return source, model


def validate_measurement_batch(
    batch: dict[str, Any], root: Path = REPO_ROOT
) -> None:
    validate_instance("measurement_batch", batch, root)
    core = {key: value for key, value in batch.items() if key != "batch_id"}
    if batch["batch_id"] != _content_id("measurement_batch_", core):
        raise ValidationFailure("measurement batch content identity is invalid")


def _opencv_frames(
    path: Path, interval: dict[str, float], stride: int
) -> Iterable[tuple[int, float, Any]]:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "local pose extraction requires the measurement extra: "
            "python -m pip install '.[measurement]'"
        ) from exc
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValidationFailure(f"OpenCV cannot open measurement source: {path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 0:
        capture.release()
        raise ValidationFailure("OpenCV reported a non-positive source frame rate")
    start_frame = max(0, int(interval["start_s"] * fps))
    capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    index = start_frame
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            timestamp = index / fps
            if timestamp >= interval["end_s"]:
                break
            if index % stride == 0:
                yield index, timestamp, frame
            index += 1
    finally:
        capture.release()


def _mediapipe_detector(job: dict[str, Any], model_path: Path) -> tuple[PoseDetector, Callable[[], None]]:
    try:
        import cv2
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
    except ImportError as exc:
        raise RuntimeError(
            "local pose extraction requires the measurement extra: "
            "python -m pip install '.[measurement]'"
        ) from exc
    detector = job["detector"]
    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=detector["num_poses"],
        min_pose_detection_confidence=detector["min_detection_confidence"],
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    def detect(frame: Any, timestamp_ms: int) -> list[dict[str, tuple[float, float, float]]]:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect_for_video(image, timestamp_ms)
        people = []
        for landmarks in result.pose_landmarks or []:
            joints = {}
            for name, index in JOINTS.items():
                landmark = landmarks[index]
                visibility = float(getattr(landmark, "visibility", 1.0) or 0.0)
                joints[name] = (float(landmark.x), float(landmark.y), visibility)
            people.append(joints)
        return people

    return detect, landmarker.close


def _centroid(joints: dict[str, tuple[float, float, float]]) -> tuple[float, float]:
    left = joints.get("left_hip")
    right = joints.get("right_hip")
    if left and right:
        return ((left[0] + right[0]) / 2.0, (left[1] + right[1]) / 2.0)
    if not joints:
        raise ValidationFailure("pose detector returned an empty person")
    return (
        sum(value[0] for value in joints.values()) / len(joints),
        sum(value[1] for value in joints.values()) / len(joints),
    )


class ActorTracker:
    """Deterministic nearest-centroid association with explicit swap suspicion."""

    def __init__(self) -> None:
        self.actors: dict[str, tuple[float, float]] = {}
        self.swap_suspect_frames = 0

    def assign(
        self, detections: list[dict[str, tuple[float, float, float]]]
    ) -> list[tuple[str, dict[str, tuple[float, float, float]]]]:
        if not detections:
            return []
        if not self.actors:
            ordered = sorted(detections, key=lambda value: _centroid(value)[0])
            for index, detection in enumerate(ordered):
                self.actors[f"actor_{chr(ord('A') + index)}"] = _centroid(detection)
            return list(zip(sorted(self.actors), ordered))
        assigned: list[tuple[str, dict[str, tuple[float, float, float]]]] = []
        used: set[int] = set()
        for actor_id, previous in sorted(self.actors.items()):
            choices = []
            for index, detection in enumerate(detections):
                if index in used:
                    continue
                current = _centroid(detection)
                distance = (current[0] - previous[0]) ** 2 + (current[1] - previous[1]) ** 2
                choices.append((distance, index, detection, current))
            if not choices:
                continue
            distance, index, detection, current = min(choices, key=lambda row: (row[0], row[1]))
            used.add(index)
            if distance > 0.09:
                self.swap_suspect_frames += 1
            self.actors[actor_id] = current
            assigned.append((actor_id, detection))
        for index, detection in enumerate(detections):
            if index in used:
                continue
            actor_id = f"actor_{chr(ord('A') + len(self.actors))}"
            self.actors[actor_id] = _centroid(detection)
            assigned.append((actor_id, detection))
        return sorted(assigned, key=lambda row: row[0])


def _keyframes(samples: list[dict[str, float]], interval_s: float) -> list[dict[str, float]]:
    output: list[dict[str, float]] = []
    next_timestamp = samples[0]["t"] if samples else 0.0
    for sample in samples:
        if sample["t"] + 1e-9 >= next_timestamp:
            output.append(sample)
            next_timestamp = sample["t"] + interval_s
    if samples and output[-1]["t"] != samples[-1]["t"]:
        output.append(samples[-1])
    return output


def _batch_parameters(job: dict[str, Any]) -> dict[str, Any]:
    parameters = job["detector"]
    return {
        "policy_version": MEASUREMENT_POLICY,
        "backend": parameters["backend"],
        "model_sha256": parameters["model_sha256"],
        "num_poses": parameters["num_poses"],
        "stride": parameters["stride"],
        "keyframe_interval_s": parameters["keyframe_interval_s"],
        "min_visibility": parameters["min_visibility"],
        "min_detection_confidence": parameters["min_detection_confidence"],
        "max_selected_frames": MAX_SELECTED_FRAMES,
    }


def _validate_detections(
    people: list[dict[str, tuple[float, float, float]]], maximum: int
) -> None:
    if not isinstance(people, list) or len(people) > maximum:
        raise ValidationFailure("pose detector returned an invalid number of people")
    for person in people:
        if not isinstance(person, dict) or not person:
            raise ValidationFailure("pose detector returned an invalid person")
        unknown = sorted(set(person) - set(JOINTS))
        if unknown:
            raise ValidationFailure(
                "pose detector returned unknown joints: " + ", ".join(unknown)
            )
        for joint, coordinates in person.items():
            if not isinstance(coordinates, (tuple, list)) or len(coordinates) != 3:
                raise ValidationFailure(
                    f"pose detector returned invalid coordinates for {joint}"
                )
            if any(
                not isinstance(value, (int, float)) or not math.isfinite(value)
                for value in coordinates
            ):
                raise ValidationFailure(
                    f"pose detector returned non-finite coordinates for {joint}"
                )
            if not 0 <= coordinates[2] <= 1:
                raise ValidationFailure(
                    f"pose detector returned invalid visibility for {joint}"
                )


def _observation(
    job: dict[str, Any], actor: str, joint: str, samples: list[dict[str, float]]
) -> dict[str, Any]:
    claim = {
        "type": "joint_track_2d",
        "actor": actor,
        "joint": joint,
        "positions": samples,
        "units": "normalized_image_xy",
        "coordinate_system": "image_topleft_x_right_y_down",
        "camera_motion_separated": False,
        "quality_flags": ["camera_motion_not_separated"],
        "limitations": [
            "Two-dimensional image-space detection cannot separate camera and subject motion.",
            "Actor identity uses nearest-centroid association and may swap across cuts or occlusion.",
        ],
    }
    identity = {
        "job_id": job["job_id"],
        "actor": actor,
        "joint": joint,
        "claim": claim,
    }
    visibility = [sample["visibility"] for sample in samples]
    return {
        "id": _content_id("measurement_obs_", identity),
        "measurement_job_id": job["job_id"],
        "source_asset_ref": job["source"]["asset_ref"],
        "source_sha256": job["source"]["sha256"],
        "tool": "mediapipe_pose",
        "model_version": job["detector"]["model_version"],
        "model_sha256": job["detector"]["model_sha256"],
        "parameters_hash": sha256_value(_batch_parameters(job)),
        "interval": {"start_s": samples[0]["t"], "end_s": samples[-1]["t"]},
        "claim": claim,
        "concept_ids": [],
        "candidate_concepts": [],
        "evidence_class": "detected",
        "confidence": round(sum(visibility) / len(visibility), 6),
        "created_at": job["created_at"],
    }


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or path.read_bytes() != data:
            raise ValidationFailure(f"measurement artifact collision: {path}")
        return
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
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


def execute_pose_measurement_job(
    job: dict[str, Any],
    root: Path = REPO_ROOT,
    *,
    output_root: Path | None = None,
    frame_reader: FrameReader | None = None,
    detector: PoseDetector | None = None,
) -> dict[str, Any]:
    """Execute locally and persist only operational candidates, never authority."""
    source_path, model_path = _validate_job(job, root)
    if (frame_reader is None) != (detector is None):
        raise ValidationFailure("frame_reader and detector must be injected together")
    closer: Callable[[], None] = lambda: None
    if frame_reader is None:
        frame_reader = _opencv_frames
        detector, closer = _mediapipe_detector(job, model_path)
    assert detector is not None

    tracker = ActorTracker()
    tracks: dict[tuple[str, str], list[dict[str, float]]] = {}
    raw_rows: list[dict[str, Any]] = []
    frames_processed = 0
    frames_with_pose = 0
    previous_frame = -1
    previous_timestamp = -1.0
    parameters = job["detector"]
    try:
        for frame_index, timestamp, frame in frame_reader(
            source_path, job["authorized_interval"], parameters["stride"]
        ):
            if (
                not isinstance(frame_index, int)
                or frame_index <= previous_frame
                or not isinstance(timestamp, (int, float))
                or not math.isfinite(timestamp)
                or timestamp <= previous_timestamp
            ):
                raise ValidationFailure(
                    "frame reader must emit strictly increasing finite frames"
                )
            if not (
                job["authorized_interval"]["start_s"] <= timestamp
                < job["authorized_interval"]["end_s"]
            ):
                raise ValidationFailure("frame reader emitted a frame outside the authorized interval")
            people = detector(frame, round(timestamp * 1000))
            _validate_detections(people, parameters["num_poses"])
            frames_processed += 1
            if frames_processed > MAX_SELECTED_FRAMES:
                raise ValidationFailure(
                    f"pose job exceeds the {MAX_SELECTED_FRAMES} selected-frame safety limit"
                )
            frames_with_pose += int(bool(people))
            previous_frame = frame_index
            previous_timestamp = float(timestamp)
            assigned = tracker.assign(people)
            raw_rows.append(
                {
                    "frame": frame_index,
                    "t": round(timestamp, 6),
                    "actors": {
                        actor: {
                            joint: [round(value, 6) for value in coordinates]
                            for joint, coordinates in sorted(joints.items())
                        }
                        for actor, joints in assigned
                    },
                }
            )
            for actor, joints in assigned:
                for joint, coordinates in sorted(joints.items()):
                    x, y, visibility = coordinates
                    if visibility < parameters["min_visibility"]:
                        continue
                    tracks.setdefault((actor, joint), []).append(
                        {
                            "t": round(timestamp, 6),
                            "x": round(x, 6),
                            "y": round(y, 6),
                            "visibility": round(visibility, 6),
                        }
                    )
    finally:
        closer()

    for actor in sorted(tracker.actors):
        left = {
            sample["t"]: sample
            for sample in tracks.get((actor, "left_hip"), [])
        }
        right = {
            sample["t"]: sample
            for sample in tracks.get((actor, "right_hip"), [])
        }
        midpoints = []
        for timestamp in sorted(set(left) & set(right)):
            midpoints.append(
                {
                    "t": timestamp,
                    "x": round(
                        (left[timestamp]["x"] + right[timestamp]["x"]) / 2,
                        6,
                    ),
                    "y": round(
                        (left[timestamp]["y"] + right[timestamp]["y"]) / 2,
                        6,
                    ),
                    "visibility": round(
                        min(
                            left[timestamp]["visibility"],
                            right[timestamp]["visibility"],
                        ),
                        6,
                    ),
                }
            )
        if midpoints:
            tracks[(actor, "root_hip_mid")] = midpoints

    observations = []
    for (actor, joint), samples in sorted(tracks.items()):
        keyframed = _keyframes(samples, parameters["keyframe_interval_s"])
        if len(keyframed) >= 2 and keyframed[-1]["t"] > keyframed[0]["t"]:
            observations.append(_observation(job, actor, joint, keyframed))
    batch_parameters = _batch_parameters(job)
    core = {
        "schema": "cpcs.measurement_batch/1.0",
        "job_id": job["job_id"],
        "source": {
            "source_id": job["source"]["source_id"],
            "asset_ref": job["source"]["asset_ref"],
            "sha256": job["source"]["sha256"],
        },
        "authorized_interval": job["authorized_interval"],
        "tool": "mediapipe_pose",
        "model_version": parameters["model_version"],
        "parameters": batch_parameters,
        "observations": observations,
        "summary": {
            "frames_processed": frames_processed,
            "frames_with_pose": frames_with_pose,
            "actors": sorted(tracker.actors),
            "possible_swap_frames": tracker.swap_suspect_frames,
            "observation_count": len(observations),
        },
        "created_at": job["created_at"],
    }
    batch = {**core, "batch_id": _content_id("measurement_batch_", core)}
    validate_measurement_batch(batch, root)
    output = output_root or root / "work" / "measurements" / job["job_id"]
    output = output.resolve()
    work = (root / "work").resolve()
    if work not in output.parents:
        raise ValidationFailure("measurement output must stay under work/")
    raw_bytes = b"".join(canonical_json_bytes(row) for row in raw_rows)
    _write_once(output / "request.json", canonical_json_bytes(job))
    _write_once(output / "raw_frames.jsonl", raw_bytes)
    _write_once(output / "measurement_batch.json", canonical_json_bytes(batch))
    return {
        "schema": "cpcs.pose_measurement_result/1.0",
        "job_id": job["job_id"],
        "batch": batch,
        "artifacts": {
            "request": str(output / "request.json"),
            "raw_frames": str(output / "raw_frames.jsonl"),
            "measurement_batch": str(output / "measurement_batch.json"),
        },
    }
