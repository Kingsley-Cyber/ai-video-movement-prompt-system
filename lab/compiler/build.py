"""Compile one canonical CPCS score into a non-submitting provider build directory."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from lab.second_brain.src.query import QUERY_POLICY
from lab.second_brain.src.fixed_sets import is_selection, selected_members
from lab.second_brain.src.validate import sha256_value

from .profiles import REPO_ROOT
from .merge import ID_KEYS
from .provenance import canonical_json_bytes, sha256_bytes
from .score import validate_compiler_instance

BUILD_COMPILER_VERSION = "cpcs-build-compiler/1.0"
BUILD_REQUEST_SCHEMA = "cpcs.build_request/1.0"
ARTIFACT_NAMES = (
    "canonical_score.json",
    "provider_request.json",
    "prompt.txt",
    "reference_still_prompt.txt",
    "capability_report.json",
    "loss_report.json",
    "verification_plan.json",
)


def _load_json_schema(name: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    path = root / "lab/compiler/schemas" / name
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(schema_name: str, value: Any, root: Path = REPO_ROOT) -> None:
    validator = Draft202012Validator(_load_json_schema(schema_name, root))
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.absolute_path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValueError(f"{schema_name}: {detail}")


def load_capability(root: Path = REPO_ROOT, *, model: str = "veo-3.1-generate-001") -> tuple[dict[str, Any], str]:
    profiles = {"veo-3.1-generate-001": "veo_3_1.yaml", "seedance-2.0": "seedance_2_0.yaml"}
    if model not in profiles:
        raise ValueError("unconfigured provider model: " + model)
    path = root / "lab/compiler/providers" / profiles[model]
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("provider capability must be an object")
    _validate("provider_capability.schema.json", value, root)
    return value, sha256_bytes(path.read_bytes())


def validate_build_configuration(root: Path = REPO_ROOT) -> dict[str, Any]:
    schemas = (
        "build_manifest.schema.json",
        "build_request.schema.json",
        "capability_report.schema.json",
        "loss_report.schema.json",
        "provider_capability.schema.json",
        "verification_plan.schema.json",
        "veo_provider_request.schema.json",
    )
    for name in schemas:
        Draft202012Validator.check_schema(_load_json_schema(name, root))
    capability, capability_hash = load_capability(root)
    return {
        "schemas": len(schemas),
        "capability_id": capability["capability_id"],
        "capability_hash": capability_hash,
    }


def make_build_request(
    score: dict[str, Any],
    *,
    project_id: str,
    location: str = "us-central1",
    creative_mode: str = "exact",
    aspect_ratio: str = "16:9",
    duration_seconds: int = 8,
    resolution: str = "720p",
    sample_count: int = 1,
    seed: int = 7,
    storage_uri: str | None = None,
    asset_bindings: list[dict[str, Any]] | None = None,
    model: str = "veo-3.1-generate-001",
    prompt_format: str | None = None,
    prompt_layout: str | None = None,
) -> dict[str, Any]:
    request = {
        "schema": BUILD_REQUEST_SCHEMA,
        "score": copy.deepcopy(score),
        "creative_mode": creative_mode,
        "target": {
            "provider": "byteplus_seedance" if model == "seedance-2.0" else "google_vertex_ai",
            "model": model,
            "project_id": project_id,
            "location": "manual" if model == "seedance-2.0" else location,
        },
        "settings": {
            "aspect_ratio": aspect_ratio,
            "duration_seconds": duration_seconds,
            "resolution": resolution,
            "sample_count": sample_count,
            "seed": seed,
            "storage_uri": storage_uri,
        },
        "asset_bindings": copy.deepcopy(asset_bindings or []),
    }
    if prompt_format is not None:
        request["settings"]["prompt_format"] = prompt_format
    if prompt_layout is not None:
        request["settings"]["prompt_layout"] = prompt_layout
    _validate("build_request.schema.json", request)
    return request


def _repository_commit(root: Path) -> str:
    process = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    )
    value = process.stdout.strip()
    if len(value) != 40:
        raise ValueError("repository commit could not be resolved")
    return value


def _concept_hashes(concept_ids: list[str], root: Path) -> dict[str, str]:
    rows: dict[str, dict[str, Any]] = {}
    path = root / "lab/concepts.jsonl"
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"concept corpus line {line_number} is invalid JSON") from exc
        concept_id = row.get("id") if isinstance(row, dict) else None
        if not isinstance(concept_id, str):
            raise ValueError(f"concept corpus line {line_number} has no valid id")
        if concept_id in rows:
            raise ValueError(f"concept corpus contains duplicate id: {concept_id}")
        rows[concept_id] = row
    missing = sorted(set(concept_ids) - set(rows))
    if missing:
        raise ValueError("canonical score concepts are absent from repository authority: " + ", ".join(missing))
    return {
        concept_id: sha256_bytes(canonical_json_bytes(rows[concept_id]))
        for concept_id in sorted(concept_ids)
    }


def _json_line(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _control_line(control: dict[str, Any]) -> str:
    return f"[{control['control_id']}] {control['path']} = {_json_line(control['value'])}"


def _scene_item_id(item: dict) -> str:
    return str(next(item[k] for k in ID_KEYS if k in item))


def _direction_line(control: dict[str, Any], score: dict, capability: dict, members=None) -> str:
    """Readable carrier made only from the resolved canonical values."""
    path, value = control["path"], control["value"]
    if path not in ("scenes", "entities", "beats", "actions", "interactions", "shots"):
        return _control_line(control)
    actors = {_scene_item_id(e): e.get("name", _scene_item_id(e)) for e in score["entities"]}
    items = {_scene_item_id(i): i for p in ("actions", "beats", "interactions", "shots") for i in score[p]}

    def visible(v: Any) -> str:
        if is_selection(v):
            return (members or {})[sha256_value(v)]["visible_wording"]
        if isinstance(v, str):
            return actors.get(v, v)
        if isinstance(v, list):
            return "; ".join(visible(x) for x in v)
        if isinstance(v, dict):
            if "value" in v and "scale" in v and isinstance(v.get("visible"), str):
                return v["visible"]
            return "; ".join(k.replace("_", " ") + ": " + visible(x) for k, x in sorted(v.items()))
        return str(v).lower() if isinstance(v, bool) else str(v)

    lines = []
    for item in sorted(value, key=lambda i: (i.get("order", 0), _scene_item_id(i))):
        noun = {"scenes": "Scene", "entities": "Character", "beats": "Beat", "actions": "Action", "interactions": "Contact", "shots": "Shot"}[path]
        label = noun + " " + str(item.get("order", _scene_item_id(item)))
        field_order = {"actor": 0, "verb": 1, "initiation": 2, "body_part": 3, "target": 4}
        parts = [k.replace("_", " ") + ": " + visible(v).rstrip(".") for k, v in sorted(item.items(), key=lambda pair: (field_order.get(pair[0], 5), pair[0])) if k not in (*ID_KEYS, "order", "relative")]
        relationships = item.get("relative", [])
        if isinstance(relationships, dict):
            relationships = [relationships]
        for relative in relationships:
            baseline = items[relative["anchor"]]
            anchor = visible(baseline.get("actor", "")) + " " + baseline.get("verb", baseline.get("label", baseline.get("reaction", _scene_item_id(baseline))))
            quality = relative["quality"]
            comparison = ("faster" if relative["direction"] == "more" else "slower") if quality == "speed" else relative["direction"] + " " + ("intense" if quality == "intensity" else quality)
            amount = "" if relative["step"] == "more" else relative["step"] + " "
            parts.append(amount + comparison + " than " + anchor.strip())
        lines.append(label + ": " + "; ".join(parts) + ".")
    return "\n".join(lines)


def _prose_prompt(score: dict, capability: dict, emitted: set[str], members=None) -> str:
    from .decisions import prop_hand_ledger

    lines = ["User intent: " + score["normalized_intent"]["request"]["original_text"]]
    controls = {c["path"]: c for c in score["provider_neutral_controls"] if c["path"] in emitted}
    _, prop_snapshots = prop_hand_ledger(score)
    names = {_scene_item_id(e): e.get("name", _scene_item_id(e)) for e in score["entities"]}
    shot_numbers = capability.get("dialect", {}).get("shot_labels") == "shot_numbers"
    for path in ("scenes", "entities"):
        if path in controls:
            lines.append(_direction_line(controls[path], score, capability, members))
    if "shots" in controls:
        lines.append(_direction_line(controls["shots"], score, capability, members))
    if "beats" in controls:
        for beat in sorted(controls["beats"]["value"], key=lambda b: (b.get("order", 0), _scene_item_id(b))):
            # The timeline owns prose ordering. Summary text stays in the canonical score
            # and JSON carrier; concrete actions and contact responses appear only once.
            header = {k: v for k, v in beat.items() if k != "summary"}
            if "beats" in score["constraints"]["locked_paths"] or "actions" not in controls:
                header = beat
            if shot_numbers:
                temporal = {"start_s", "end_s", "duration_s", "min_s"}
                if "beats" in score["constraints"]["locked_paths"] and temporal.intersection(beat):
                    raise ValueError("Seedance prose cannot preserve a locked timestamp control; select a compatible carrier or model")
                header = {k: v for k, v in header.items() if k not in temporal}
            lines.append(_direction_line({"path": "beats", "value": [header]}, score, capability, members))
            if "actions" in controls:
                for action in sorted((a for a in controls["actions"]["value"] if a.get("beat") == _scene_item_id(beat)), key=lambda a: (a.get("order", 0), _scene_item_id(a))):
                    lines.append(_direction_line({"path": "actions", "value": [action]}, score, capability, members))
                    if "interactions" in controls:
                        contacts = [i for i in controls["interactions"]["value"] if i.get("action") == _scene_item_id(action)]
                        lines.append(_direction_line({"path": "interactions", "value": contacts}, score, capability, members))
            props = prop_snapshots.get(_scene_item_id(beat), {})
            if props and {"entities", "actions"} <= set(controls):
                parts = []
                for obj, state in props.items():
                    held = ""
                    if state["held_by"] is not None:
                        held = "; held by " + names[state["held_by"]] + " in " + "/".join(state["hands"]) + " hand(s)"
                    parts.append(names[obj] + ": " + state["state"] + "; " + state["location"] + held)
                lines.append("PROP: " + ". ".join(parts) + ".")
        if "interactions" in controls:
            unassigned = [i for i in controls["interactions"]["value"] if not i.get("action")]
            lines.append(_direction_line({"path": "interactions", "value": unassigned}, score, capability, members))
    else:
        for path in ("actions", "interactions"):
            if path in controls:
                lines.append(_direction_line(controls[path], score, capability, members))
    for path in sorted(set(controls) - {"scenes", "entities", "shots", "beats", "actions", "interactions"}):
        lines.append(_control_line(controls[path]))
    return "\n".join(line for line in lines if line) + "\n"


def _validate_score_identity(score: dict[str, Any]) -> None:
    score_without_id = {key: value for key, value in score.items() if key != "score_id"}
    expected = "score_" + hashlib.sha256(
        canonical_json_bytes(score_without_id)
    ).hexdigest()[:32]
    if score["score_id"] != expected:
        raise ValueError("canonical score_id does not match score content")


def _binding_map(request: dict[str, Any], score: dict[str, Any]) -> dict[str, dict[str, Any]]:
    score_assets = {row["asset_id"]: row for row in score["assets"]}
    bindings: dict[str, dict[str, Any]] = {}
    used_assets: set[str] = set()
    for row in request["asset_bindings"]:
        role = row["provider_role"]
        if role in bindings:
            raise ValueError(f"provider asset role is duplicated: {role}")
        if row["asset_id"] not in score_assets:
            raise ValueError(f"asset binding is absent from canonical score: {row['asset_id']}")
        if row["asset_id"] in used_assets:
            raise ValueError(f"asset is bound more than once: {row['asset_id']}")
        used_assets.add(row["asset_id"])
        bindings[role] = row
    if "last_frame" in bindings and "first_frame" not in bindings:
        raise ValueError("last_frame requires a first_frame binding")
    return bindings


def _creative_policy(request: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
    mode = request["creative_mode"]
    sample_count = request["settings"]["sample_count"]
    warning_codes = {row["code"] for row in score["warnings"]}
    if mode == "exploratory" and sample_count < 2:
        raise ValueError("exploratory mode requires sample_count between 2 and 4")
    if mode != "exploratory" and sample_count != 1:
        raise ValueError(f"{mode} mode requires sample_count 1")
    if mode == "transfer" and not score["assets"]:
        raise ValueError("transfer mode requires at least one canonical score asset")
    if mode == "diagnostic" and not score["verification_requirements"]:
        raise ValueError("diagnostic mode requires canonical verification requirements")
    if mode == "research_gap" and "knowledge_gap_open" not in warning_codes:
        raise ValueError("research_gap mode requires an open canonical knowledge gap")
    decisions = [
        {
            "decision_id": "creative_mode",
            "outcome": mode,
            "reason": "The caller selected a declared creative policy mode.",
        },
        {
            "decision_id": "sample_count",
            "outcome": sample_count,
            "reason": (
                "Exploratory mode requests bounded provider alternatives."
                if mode == "exploratory"
                else "This mode resolves one provider realization."
            ),
        },
        {
            "decision_id": "seed",
            "outcome": request["settings"]["seed"],
            "reason": "The explicit seed binds replay and provider variation trace.",
        },
    ]
    return {
        "policy_version": "cpcs-creative-policy/1.0",
        "mode": mode,
        "hard_invariants": sorted(score["constraints"]["locked_paths"]),
        "decisions": decisions,
    }


def _prompt_and_dispositions(
    score: dict[str, Any], capability: dict[str, Any], prompt_format: str = "canonical", members=None
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    intent = score["normalized_intent"]["request"]["original_text"]
    fixed = [
        "CPCS CANONICAL VIDEO DIRECTION",
        f"User intent: {intent}",
        "Canonical controls:",
    ]
    budget = capability["policy"]["prompt_budget_chars"]
    evaluation_only = set(capability["control_rules"]["evaluation_only_paths"])
    explicitly_unsupported = set(capability["control_rules"]["unsupported_paths"])
    locked = set(score["constraints"]["locked_paths"])
    prompt_lines: list[str] = []
    dispositions: list[dict[str, Any]] = []
    losses: list[dict[str, Any]] = []
    controls = sorted(
        score["provider_neutral_controls"],
        key=lambda row: (row["path"] not in locked, row["path"], row["control_id"]),
    )
    for control in controls:
        path = control["path"]
        line = _control_line(control) if prompt_format == "canonical" else _direction_line(control, score, capability, members)
        if path in evaluation_only:
            status = "evaluation_only"
            reason = "The provider cannot execute this measurement contract; verification retains it."
        elif path in explicitly_unsupported:
            status = "unsupported"
            reason = "The capability profile marks this canonical path unsupported."
        else:
            candidate = "\n".join([*fixed, *prompt_lines, line]) + "\n"
            if budget is None or len(candidate) <= budget:
                status = "compressed_to_text"
                reason = "The canonical value is projected verbatim into the prompt carrier."
                prompt_lines.append(line)
            elif path in locked:
                raise ValueError(f"prompt budget cannot preserve locked control: {path}")
            else:
                status = "unsupported"
                reason = "The prompt budget cannot carry this control without truncation."
        dispositions.append(
            {
                "control_id": control["control_id"],
                "path": path,
                "status": status,
                "carrier": "prompt.txt" if status == "compressed_to_text" else "verification_plan.json" if status == "evaluation_only" else None,
                "reason": reason,
            }
        )
        if status in {"compressed_to_text", "unsupported", "evaluation_only"}:
            losses.append(
                {
                    "control_id": control["control_id"],
                    "path": path,
                    "loss_type": (
                        "compression" if status == "compressed_to_text" else status
                    ),
                    "severity": (
                        "high"
                        if status == "unsupported"
                        else "low"
                        if status == "compressed_to_text"
                        else "none"
                    ),
                    "reason": reason,
                }
            )
    prompt = "\n".join([*fixed, *prompt_lines]) + "\n"
    if prompt_format == "prose":
        emitted = {row["path"] for row in dispositions if row["status"] == "compressed_to_text"}
        prompt = _prose_prompt(score, capability, emitted, members)
        for loss in losses:
            if loss["path"] == "beats" and "beats" not in locked and "actions" in emitted:
                loss["reason"] = "Prose emits beat labels and timing with each action and contact once. Beat summaries remain in canonical JSON and the JSON carrier."
    if prompt_format == "json":
        # This is a projection of admitted controls, never a competing scene authority.
        emitted = {row["path"] for row in dispositions if row["status"] == "compressed_to_text"}
        prompt = json.dumps({"score_id": score["score_id"], **{c["path"]: c["value"] for c in controls if c["path"] in emitted}}, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if capability.get("dialect", {}).get("shot_labels") == "shot_numbers":
        for loss in losses:
            if loss["path"] == "beats":
                loss["reason"] += " Seedance 2.0 uses shot-number direction, not timestamp conditioning. Timing stays in the canonical score and verification plan; numeric JSON is an untested carrier, not exact timing control."
    if budget is not None and len(prompt) > budget:
        raise ValueError("prompt exceeds the measured capability budget")
    return prompt, dispositions, losses


def _reference_prompt(
    score: dict[str, Any],
    bindings: dict[str, dict[str, Any]],
    capability: dict[str, Any],
    prompt_format: str = "canonical",
    members=None,
) -> tuple[str, list[str], list[dict[str, str]]]:
    lines = ["CPCS REFERENCE STILL PROJECTION", "Canonical reference assets:"]
    by_id = {row["asset_id"]: row for row in score["assets"]}
    bound_ids = {row["asset_id"] for row in bindings.values()}
    if not by_id:
        lines.append("none")
    for asset_id in sorted(by_id):
        asset = by_id[asset_id]
        carrier = next(
            (role for role, row in bindings.items() if row["asset_id"] == asset_id),
            "prompt_reference_only",
        )
        lines.append(
            f"[{asset_id}] role={asset['role']} carrier={carrier} content_hash={asset['content_hash']}"
        )
    if bound_ids - set(by_id):
        raise ValueError("reference prompt contains an unknown bound asset")
    lines.append("Canonical visual controls:")
    prefixes = ("project", "entities", "scenes", "camera", "style", "continuity", "shots") if prompt_format != "canonical" else ("project", "entities", "scenes", "camera", "style", "continuity")
    selected = [
        row
        for row in score["provider_neutral_controls"]
        if row["path"].split(".", 1)[0] in prefixes
        or row["path"] == "marketing.product_visibility"
    ]
    locked = set(score["constraints"]["locked_paths"])
    selected.sort(
        key=lambda row: (row["path"] not in locked, row["path"], row["control_id"])
    )
    budget = capability["policy"]["reference_prompt_budget_chars"]
    projected: list[str] = []
    omissions: list[dict[str, str]] = []
    for control in selected:
        if prompt_format != "canonical" and control["path"] in ("scenes", "shots"):
            static = copy.deepcopy(control)
            removed = []
            temporal = {"duration_s", "sound", "dialogue", "music", "end_state", "hand_uses", "motion_style", "movement", "movement_quality", "relation", "time", "blur", "connection", "beat", "end_beat", "shows_initiation", "occlusion_reason"}
            for item in static["value"]:
                removed.extend(sorted(set(item) & temporal))
                for field in temporal:
                    item.pop(field, None)
            line = _direction_line(static, score, capability, members)
            if removed:
                omissions.append({"control_id": control["control_id"], "path": control["path"], "reason": "Still frame omits temporal fields retained by the primary prompt: " + ", ".join(sorted(set(removed)))})
        else:
            line = _control_line(control) if prompt_format == "canonical" else _direction_line(control, score, capability, members)
        candidate = "\n".join([*lines, line]) + "\n"
        if budget is None or len(candidate) <= budget:
            lines.append(line)
            projected.append(control["control_id"])
        elif control["path"] in locked:
            raise ValueError(
                f"reference prompt budget cannot preserve locked control: {control['path']}"
            )
        else:
            omissions.append(
                {
                    "control_id": control["control_id"],
                    "path": control["path"],
                    "reason": "The reference projection budget is full; the primary prompt still carries this control.",
                }
            )
    if not selected:
        lines.append("none")
    prompt = "\n".join(lines) + "\n"
    if budget is not None and len(prompt) > budget:
        raise ValueError("reference prompt exceeds the measured capability budget")
    return prompt, projected, omissions


def _provider_request(
    request: dict[str, Any], prompt: str, bindings: dict[str, dict[str, Any]], capability: dict[str, Any]
) -> dict[str, Any]:
    target = request["target"]
    settings = request["settings"]
    if capability["api_method"] == "manual_export":
        if bindings or settings["storage_uri"] is not None or settings["sample_count"] != 1:
            raise ValueError("manual Seedance export cannot carry bindings, storage URI or multiple samples")
        return {"method": "MANUAL", "provider": target["provider"], "model": target["model"],
                "prompt": prompt, "settings": {k: settings[k] for k in ("aspect_ratio", "duration_seconds", "resolution")}}
    instance: dict[str, Any] = {"prompt": prompt}
    if "first_frame" in bindings:
        row = bindings["first_frame"]
        instance["image"] = {"gcsUri": row["gcs_uri"], "mimeType": row["mime_type"]}
    if "last_frame" in bindings:
        row = bindings["last_frame"]
        instance["lastFrame"] = {"gcsUri": row["gcs_uri"], "mimeType": row["mime_type"]}
    parameters = {
        "aspectRatio": settings["aspect_ratio"],
        "durationSeconds": settings["duration_seconds"],
        "enhancePrompt": capability["policy"]["enhance_prompt"],
        "personGeneration": capability["policy"]["person_generation"],
        "resolution": settings["resolution"],
        "sampleCount": settings["sample_count"],
        "seed": settings["seed"],
    }
    if settings["storage_uri"] is not None:
        parameters["storageUri"] = settings["storage_uri"]
    provider_request = {
        "method": "POST",
        "url": (
            f"https://{target['location']}-aiplatform.googleapis.com/v1/projects/"
            f"{target['project_id']}/locations/{target['location']}/publishers/google/models/"
            f"{target['model']}:predictLongRunning"
        ),
        "body": {"instances": [instance], "parameters": parameters},
    }
    _validate("veo_provider_request.schema.json", provider_request)
    return provider_request


def compile_build(request: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, bytes]:
    from .decisions import prop_hand_ledger

    _validate("build_request.schema.json", request, root)
    score = request["score"]
    validate_compiler_instance("universal_score", score, root)
    _validate_score_identity(score)
    from .skeleton import validate_scene
    validate_scene(score, root=root)
    members = selected_members(score, root)
    from .decisions import movement_checks
    movement_errors, movement_reports = movement_checks(score, root=root)
    if movement_errors:
        raise ValueError("; ".join(e["code"]+": "+e["message"] for e in movement_errors))
    prop_errors, _ = prop_hand_ledger(score)
    if prop_errors:
        raise ValueError("; ".join(error["code"] + ": " + error["message"] for error in prop_errors))
    if score["score_status"] != "ready" or score["unresolved"]:
        raise ValueError("build compiler requires a ready canonical score")
    capability, capability_hash = load_capability(root, model=request["target"]["model"])
    if request["target"]["provider"] != capability["provider"] or request["target"]["model"] != capability["model"]:
        raise ValueError("build target does not match the selected capability profile")
    if request["target"]["location"] not in capability["locations"]:
        raise ValueError("build location does not match the selected capability profile")
    settings = request["settings"]
    scene_durations = [s.get("duration_s") for s in score["scenes"] if s.get("duration_s") is not None]
    if scene_durations and (len(scene_durations) != 1 or settings["duration_seconds"] != scene_durations[0]):
        raise ValueError("build duration must preserve the canonical scene duration")
    if "duration_seconds" in score["project"] and settings["duration_seconds"] != score["project"]["duration_seconds"]:
        raise ValueError("build duration must preserve the canonical project duration")
    concept_hashes = _concept_hashes(score["provenance"]["concept_ids"], root)
    if members:
        concept_hashes.update({m["concept_id"]: m["selection"]["member_hash"] for m in members.values()})
    for key, allowed in (
        ("aspect_ratio", capability["aspect_ratios"]),
        ("duration_seconds", capability["durations_seconds"]),
        ("resolution", capability["resolutions"]),
    ):
        if settings[key] not in allowed:
            raise ValueError(f"provider capability rejects {key}: {settings[key]}")
    bindings = _binding_map(request, score)
    creative_policy = _creative_policy(request, score)
    prompt, dispositions, losses = _prompt_and_dispositions(score, capability, settings.get("prompt_format", "canonical"), members)
    projection_audit = None
    if settings.get("prompt_layout") == "labelled_skeleton_v1":
        from .skeleton import project
        labelled, projection_audit, omissions = project(score, root=root)
        if settings.get("prompt_format", "canonical") != "json":
            if settings.get("prompt_format") != "prose":
                raise ValueError("labelled_skeleton_v1 requires the prose carrier")
            prompt = labelled
        controls_by_path = {c["path"]: c for c in score["provider_neutral_controls"]}
        for omission in omissions:
            path = omission["ref"].split(".")[0]
            losses.append(dict(control_id=controls_by_path[path]["control_id"], path=omission["ref"], loss_type="omitted_decision", severity="low", reason=omission["decision_id"]+": "+omission["reason"]))
        budget = capability["policy"]["prompt_budget_chars"]
        if budget is not None and len(prompt) > budget:
            raise ValueError("prompt exceeds the measured capability budget")
    reference_prompt, reference_controls, reference_omissions = _reference_prompt(
        score, bindings, capability, settings.get("prompt_format", "canonical"), members
    )
    provider_request = _provider_request(request, prompt, bindings, capability)
    capability_report = {
        "schema": "cpcs.capability_report/1.0",
        "capability_id": capability["capability_id"],
        "provider": capability["provider"],
        "model": capability["model"],
        "prompt_budget_chars": capability["policy"]["prompt_budget_chars"],
        "prompt_chars_used": len(prompt),
        "reference_prompt_budget_chars": capability["policy"]["reference_prompt_budget_chars"],
        "reference_prompt_chars_used": len(reference_prompt),
        "reference_projection_control_ids": reference_controls,
        "reference_projection_omissions": reference_omissions,
        "creative_policy": creative_policy,
        "dispositions": dispositions,
        "limitations": capability["limitations"],
    }
    loss_report = {
        "schema": "cpcs.loss_report/1.0",
        "score_id": score["score_id"],
        "losses": losses,
        "has_unsupported_controls": any(row["loss_type"] == "unsupported" for row in losses),
        "provider_limitations": capability["limitations"],
    }
    verification_plan = {
        "schema": "cpcs.verification_plan/1.0",
        "score_id": score["score_id"],
        "requirements": copy.deepcopy(score["verification_requirements"]),
        "evaluation_only_controls": [row for row in dispositions if row["status"] == "evaluation_only"],
        "provider_artifact_checks": [
            {
                "check_id": "artifact_hash",
                "observed_field": "artifact.sha256",
                "comparator": "sha256_present",
                "expected": True,
                "tolerance": None,
            },
            {
                "check_id": "duration",
                "observed_field": "artifact.duration_seconds",
                "comparator": "equal",
                "expected": settings["duration_seconds"],
                "tolerance": 0,
            },
            {
                "check_id": "aspect_ratio",
                "observed_field": "artifact.aspect_ratio",
                "comparator": "equal",
                "expected": settings["aspect_ratio"],
                "tolerance": None,
            },
            {
                "check_id": "resolution",
                "observed_field": "artifact.resolution",
                "comparator": "equal",
                "expected": settings["resolution"],
                "tolerance": None,
            },
            {
                "check_id": "frame_rate",
                "observed_field": "artifact.frame_rate",
                "comparator": "equal",
                "expected": capability["frame_rate"],
                "tolerance": 0,
            },
        ],
    }
    if members:
        capability_report["movement_reports"] = movement_reports
    if projection_audit is not None:
        capability_report["projection_audit"] = projection_audit
    _validate("capability_report.schema.json", capability_report, root)
    _validate("loss_report.schema.json", loss_report, root)
    _validate("verification_plan.schema.json", verification_plan, root)
    artifacts: dict[str, bytes] = {
        "canonical_score.json": canonical_json_bytes(score),
        "provider_request.json": canonical_json_bytes(provider_request),
        "prompt.txt": prompt.encode("utf-8"),
        "reference_still_prompt.txt": reference_prompt.encode("utf-8"),
        "capability_report.json": canonical_json_bytes(capability_report),
        "loss_report.json": canonical_json_bytes(loss_report),
        "verification_plan.json": canonical_json_bytes(verification_plan),
    }
    artifact_hashes = {name: sha256_bytes(artifacts[name]) for name in ARTIFACT_NAMES}
    manifest_core = {
        "schema": "cpcs.build_manifest/1.0",
        "build_id": "build_" + "0" * 32,
        "compiler_version": BUILD_COMPILER_VERSION,
        "repository_commit": _repository_commit(root),
        "creative_mode": request["creative_mode"],
        "score_id": score["score_id"],
        "score_hash": artifact_hashes["canonical_score.json"],
        "directing_strategy_id": score["directing_strategy_trace"]["strategy_id"],
        "directing_strategy_hash": score["provenance"]["directing_strategy_hash"],
        "intent_schema": score["normalized_intent"]["schema"],
        "query_policy": QUERY_POLICY["version"],
        "profile_hashes": score["provenance"]["profile_hashes"],
        "concept_ids": sorted(concept_hashes) if members else score["provenance"]["concept_ids"],
        "concept_hashes": concept_hashes,
        "block_hashes": {},
        "provider_capability_id": capability["capability_id"],
        "provider_capability_hash": capability_hash,
        "seed": settings["seed"],
        "artifact_hashes": artifact_hashes,
        "build_hash": "sha256:" + "0" * 64,
    }
    hash_input = {key: value for key, value in manifest_core.items() if key not in {"build_id", "build_hash"}}
    digest = hashlib.sha256(canonical_json_bytes(hash_input)).hexdigest()
    manifest_core["build_id"] = "build_" + digest[:32]
    manifest_core["build_hash"] = "sha256:" + digest
    _validate("build_manifest.schema.json", manifest_core, root)
    artifacts["build_manifest.json"] = canonical_json_bytes(manifest_core)
    return artifacts


def write_build_directory(artifacts: dict[str, bytes], output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"build output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in (*ARTIFACT_NAMES, "build_manifest.json"):
        (output_dir / name).write_bytes(artifacts[name])


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def load_validated_build_directory(
    output_dir: Path, root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Load one complete build after rechecking every byte and content identity."""
    directory = output_dir.expanduser().resolve()
    if not directory.is_dir():
        raise ValueError(f"build directory does not exist: {directory}")
    expected_names = {*ARTIFACT_NAMES, "build_manifest.json"}
    actual_names = {path.name for path in directory.iterdir()}
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        unexpected = sorted(actual_names - expected_names)
        raise ValueError(
            f"build directory contract mismatch: missing={missing} unexpected={unexpected}"
        )
    paths = {name: directory / name for name in expected_names}
    unsafe = sorted(
        name for name, path in paths.items() if path.is_symlink() or not path.is_file()
    )
    if unsafe:
        raise ValueError("build directory contains unsafe artifacts: " + ", ".join(unsafe))
    artifact_bytes = {name: path.read_bytes() for name, path in paths.items()}
    manifest = _read_json(paths["build_manifest.json"], "build manifest")
    _validate("build_manifest.schema.json", manifest, root)
    for name, expected_hash in manifest["artifact_hashes"].items():
        actual_hash = sha256_bytes(artifact_bytes[name])
        if actual_hash != expected_hash:
            raise ValueError(f"build artifact hash mismatch: {name}")
    hash_input = {
        key: value
        for key, value in manifest.items()
        if key not in {"build_id", "build_hash"}
    }
    digest = hashlib.sha256(canonical_json_bytes(hash_input)).hexdigest()
    if (
        manifest["build_id"] != "build_" + digest[:32]
        or manifest["build_hash"] != "sha256:" + digest
    ):
        raise ValueError("build manifest content identity does not match")
    score = _read_json(paths["canonical_score.json"], "canonical score")
    validate_compiler_instance("universal_score", score, root)
    _validate_score_identity(score)
    if score["score_id"] != manifest["score_id"]:
        raise ValueError("build score does not match manifest score_id")
    if sha256_bytes(artifact_bytes["canonical_score.json"]) != manifest["score_hash"]:
        raise ValueError("build score hash does not match manifest score_hash")
    provider_request = _read_json(paths["provider_request.json"], "provider request")
    if provider_request.get("method") == "MANUAL":
        if set(provider_request) != {"method", "provider", "model", "prompt", "settings"} or provider_request["provider"] != "byteplus_seedance" or provider_request["model"] != "seedance-2.0":
            raise ValueError("invalid manual provider export")
        if provider_request["prompt"] != artifact_bytes["prompt.txt"].decode("utf-8"):
            raise ValueError("manual provider prompt does not match prompt artifact")
        capability, _ = load_capability(root, model=provider_request["model"])
        for key, allowed in (("aspect_ratio", capability["aspect_ratios"]), ("duration_seconds", capability["durations_seconds"]), ("resolution", capability["resolutions"])):
            if provider_request["settings"].get(key) not in allowed:
                raise ValueError("manual export capability rejects " + key)
    else:
        _validate("veo_provider_request.schema.json", provider_request, root)
    capability_report = _read_json(
        paths["capability_report.json"], "capability report"
    )
    _validate("capability_report.schema.json", capability_report, root)
    loss_report = _read_json(paths["loss_report.json"], "loss report")
    _validate("loss_report.schema.json", loss_report, root)
    verification_plan = _read_json(
        paths["verification_plan.json"], "verification plan"
    )
    _validate("verification_plan.schema.json", verification_plan, root)
    return {
        "directory": directory,
        "manifest": manifest,
        "score": score,
        "provider_request": provider_request,
        "capability_report": capability_report,
        "loss_report": loss_report,
        "verification_plan": verification_plan,
        "artifact_bytes": artifact_bytes,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    compile_command = sub.add_parser("compile")
    compile_command.add_argument("request", type=Path)
    compile_command.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "validate":
        print(json.dumps(validate_build_configuration(), sort_keys=True))
        return
    artifacts = compile_build(_read_json(args.request, "build request"))
    write_build_directory(artifacts, args.output_dir)
    manifest = json.loads(artifacts["build_manifest.json"])
    print(json.dumps({"build_id": manifest["build_id"], "output_dir": str(args.output_dir)}, sort_keys=True))


if __name__ == "__main__":
    main()
