"""Project a Video Observation Graph into a standard score overlay and score."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from lab.second_brain.src.validate import REPO_ROOT
from lab.second_brain.src.video_observation import validate_video_observation_graph

from .score import make_score_request, resolve_score


def _stable_id(prefix: str, value: str) -> str:
    return prefix + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _observation_rows(vog: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        node["data"]
        for node in vog["nodes"]
        if node["node_type"] in {"observation", "segment"}
    ]
    return sorted(
        rows,
        key=lambda row: (
            row["interval"]["start_s"],
            row["interval"]["end_s"],
            row["observation_id"],
        ),
    )


def overlay_from_vog(vog: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    """Return only fields owned by the canonical score's declared merge table."""
    validate_video_observation_graph(vog, root)
    rows = _observation_rows(vog)
    entities: dict[str, dict[str, Any]] = {}
    beats: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    shots: list[dict[str, Any]] = []
    marketing: list[str] = []
    camera_scales: list[str] = []
    camera_movements: list[str] = []
    performance_labels: list[str] = []
    for row in rows:
        claim = row["claim"]
        label = str(claim.get("label", claim.get("definition_id", "observed")))
        interval = row["interval"]
        source_ref = f"{vog['graph_id']}#{row['observation_id']}"
        if row["layer"] == "entity":
            entity_id = _stable_id("entity_observed_", label.lower())
            entities[entity_id] = {
                "id": entity_id,
                "name": label,
                "observation_ref": source_ref,
                "evidence_class": row["evidence_class"],
                "confidence": row["confidence"],
            }
        elif row["layer"] == "beat":
            beats.append(
                {
                    "id": _stable_id("beat_observed_", row["observation_id"]),
                    "label": label,
                    "start_s": interval["start_s"],
                    "end_s": interval["end_s"],
                    "observation_ref": source_ref,
                    "evidence_class": row["evidence_class"],
                    "confidence": row["confidence"],
                }
            )
        elif row["layer"] == "action":
            actions.append(
                {
                    "id": _stable_id("action_observed_", row["observation_id"]),
                    "verb": label,
                    "start_s": interval["start_s"],
                    "end_s": interval["end_s"],
                    "observation_ref": source_ref,
                    "evidence_class": row["evidence_class"],
                    "confidence": row["confidence"],
                }
            )
        elif row["layer"] == "segment":
            shots.append(
                {
                    "id": _stable_id("shot_observed_", row["observation_id"]),
                    "start_s": interval["start_s"],
                    "end_s": interval["end_s"],
                    "metadata": claim,
                    "observation_ref": source_ref,
                    "evidence_class": row["evidence_class"],
                    "confidence": row["confidence"],
                }
            )
            if claim.get("shot_scale"):
                camera_scales.append(str(claim["shot_scale"]))
            if claim.get("camera_movement"):
                camera_movements.append(str(claim["camera_movement"]))
        elif row["layer"] == "camera":
            if claim.get("shot_scale"):
                camera_scales.append(str(claim["shot_scale"]))
            if claim.get("movement"):
                camera_movements.append(str(claim["movement"]))
        elif row["layer"] == "performance":
            performance_labels.append(label)
        elif row["layer"] == "marketing":
            marketing.append(label)

    values: dict[str, Any] = {}
    if entities:
        values["entities"] = [entities[key] for key in sorted(entities)]
    if shots:
        values["shots"] = shots
    if beats:
        values["beats"] = beats
    if actions:
        values["actions"] = actions
    if camera_scales:
        values["camera.shot_scale"] = camera_scales[0]
    if camera_movements:
        values["camera.movement"] = camera_movements[0]
    if performance_labels:
        values["performance.delivery"] = performance_labels[0]
    if marketing:
        values["marketing.structure"] = list(dict.fromkeys(marketing))
    if not values:
        raise ValueError("VOG contains no observations projectable to the canonical score")
    return {
        "overlay_id": "overlay_vog_" + vog["graph_hash"][len("sha256:") :][:20],
        "scope": "project_profile",
        "priority": 0,
        "values": values,
        "locks": [],
    }


def resolve_vog_score(
    intent_context: dict[str, Any],
    vog: dict[str, Any],
    *,
    assets: Iterable[dict[str, Any]] = (),
    conflict_resolutions: dict[str, Any] | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Resolve a VOG through the existing canonical score kernel."""
    overlay = overlay_from_vog(vog, root)
    request = make_score_request(
        intent_context,
        overlays=[overlay],
        assets=list(assets),
        conflict_resolutions=conflict_resolutions or {},
    )
    return resolve_score(request, root)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intent_context", type=Path)
    parser.add_argument("vog", type=Path)
    parser.add_argument("--assets", type=Path)
    args = parser.parse_args(argv)
    intent_context = json.loads(args.intent_context.read_text())
    vog = json.loads(args.vog.read_text())
    assets = json.loads(args.assets.read_text()) if args.assets else []
    print(
        json.dumps(
            resolve_vog_score(intent_context, vog, assets=assets),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
