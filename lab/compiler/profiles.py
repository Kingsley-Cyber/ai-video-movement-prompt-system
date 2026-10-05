"""Load and validate universal, domain, and adapted component profiles."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from .provenance import sha256_bytes

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPILER_ROOT = REPO_ROOT / "lab" / "compiler"
PROFILES_ROOT = REPO_ROOT / "lab" / "profiles"
KERNEL_PROFILE_ID = "profile://universal/video/1.0"

COMPONENT_CAMERA_PATHS = {
    "mode": "camera.capture_device",
    "stabilization": "camera.stabilization",
    "self_framing_corrections": "camera.self_framing_corrections",
    "screen_direction_lock": "camera.screen_direction_locked",
    "target_visibility_at_contact": "camera.target_visibility_at_contact",
    "impact_shake_policy": "camera.impact_shake_policy",
    "shot_scale": "camera.shot_scale",
    "movement": "camera.movement",
    "horizon_policy": "camera.horizon_policy",
}
COMPONENT_METRIC_TARGETS = {
    "face_in_frame_duty_cycle": ["camera.capture_device"],
    "product_visibility_duty_cycle": ["marketing.product_visibility"],
    "gesture_speech_alignment": ["performance.delivery"],
    "contact_readability": ["interactions"],
    "screen_direction_match": ["continuity.screen_direction_locked"],
    "target_visibility_at_contact": ["camera.target_visibility_at_contact"],
    "minimum_contact_distance": ["interactions"],
    "reaction_delay": ["motion.phase_readability"],
}


@dataclass(frozen=True)
class ProfileCatalog:
    kernel: dict[str, Any]
    domains: tuple[dict[str, Any], ...]
    components: dict[str, dict[str, Any]]
    profile_hashes: dict[str, str]
    field_policies: dict[str, str]


# Profiles are re-read on every operation; parse each file version (mtime, size) once per process.
_YAML_CACHE: dict[str, tuple[tuple[int, int], Any]] = {}


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
        version = (stat.st_mtime_ns, stat.st_size)
        cached = _YAML_CACHE.get(str(path))
        if cached is None or cached[0] != version:
            cached = (version, yaml.safe_load(path.read_text(encoding="utf-8")))
            _YAML_CACHE[str(path)] = cached
        value = copy.deepcopy(cached[1])
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot read profile {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"profile must be an object: {path}")
    return value


def _profile_validator(root: Path) -> Draft202012Validator:
    path = root / "lab/compiler/schemas/profile.schema.json"
    schema = __import__("json").loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _schema_errors(
    validator: Draft202012Validator,
    value: dict[str, Any],
    label: str,
) -> None:
    errors = sorted(
        validator.iter_errors(value), key=lambda error: list(error.absolute_path)
    )
    if errors:
        detail = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValueError(f"{label}: {detail}")


def _component_path(profile_id: str, root: Path) -> Path:
    prefix = "profile://"
    if not profile_id.startswith(prefix):
        raise ValueError(f"invalid component profile URI: {profile_id}")
    relative = profile_id[len(prefix) :]
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", relative):
        raise ValueError(f"unsafe component profile URI: {profile_id}")
    profiles_root = (root / "lab/profiles").resolve()
    path = (profiles_root / f"{relative}.yaml").resolve()
    if profiles_root not in path.parents:
        raise ValueError(f"component profile escapes profile root: {profile_id}")
    if not path.is_file():
        raise ValueError(f"component profile does not exist: {profile_id}")
    return path


def flatten_defaults(
    defaults: dict[str, Any], field_policies: dict[str, str]
) -> dict[str, Any]:
    """Flatten only paths admitted by the universal field-policy table."""
    output: dict[str, Any] = {}

    def visit(value: Any, parts: tuple[str, ...]) -> None:
        path = ".".join(parts)
        if path in field_policies:
            output[path] = value
            return
        prefix = path + "." if path else ""
        if not any(candidate.startswith(prefix) for candidate in field_policies):
            raise ValueError(f"profile default targets undeclared canonical field: {path}")
        if not isinstance(value, dict) or not value:
            raise ValueError(f"profile default cannot resolve to a declared field: {path}")
        for key in sorted(value):
            visit(value[key], (*parts, str(key)))

    for key in sorted(defaults):
        visit(defaults[key], (str(key),))
    return output


def _metric_id(name: str, profile_id: str) -> str:
    normalized_profile = re.sub(
        r"[^A-Za-z0-9._-]+", "_", profile_id.removeprefix("profile://")
    ).strip("_")
    normalized_name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return f"metric_component_{normalized_profile}_{normalized_name}"


def adapt_component_profile(
    profile_id: str,
    component: dict[str, Any],
    field_policies: dict[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Map the frozen CPCS-MX component shape into declared canonical fields."""
    allowed_top = {"profile_id", "profile_version", "status", "defaults", "hard_constraints"}
    unexpected = set(component) - allowed_top
    if unexpected:
        raise ValueError(
            f"component profile {profile_id} has unsupported fields: {sorted(unexpected)}"
        )
    defaults = component.get("defaults", {})
    if not isinstance(defaults, dict):
        raise ValueError(f"component profile {profile_id} defaults must be an object")
    values: dict[str, Any] = {}
    known_sections = {
        "capture_style",
        "hard_constraints",
        "imperfections",
        "performance",
        "scope",
        "style_transform",
        "verification",
    }
    unknown_sections = set(defaults) - known_sections
    if unknown_sections:
        raise ValueError(
            f"component profile {profile_id} has unsupported default sections: "
            + ", ".join(sorted(unknown_sections))
        )

    capture = defaults.get("capture_style", {})
    if capture:
        if not isinstance(capture, dict) or "camera" not in capture:
            raise ValueError(f"component profile {profile_id} capture_style is unsupported")
        unknown_capture = set(capture) - {"camera", "imperfections"}
        if unknown_capture:
            raise ValueError(
                f"component profile {profile_id} has unsupported capture fields: "
                f"{sorted(unknown_capture)}"
            )
        camera = capture["camera"]
        if not isinstance(camera, dict):
            raise ValueError(f"component profile {profile_id} camera defaults must be an object")
        unknown = set(camera) - set(COMPONENT_CAMERA_PATHS)
        if unknown:
            raise ValueError(
                f"component profile {profile_id} has unsupported camera fields: {sorted(unknown)}"
            )
        for key, value in camera.items():
            values[COMPONENT_CAMERA_PATHS[key]] = value
        if "imperfections" in capture:
            values["style.capture_imperfections"] = capture["imperfections"]

    if "imperfections" in defaults:
        values["style.capture_imperfections"] = defaults["imperfections"]
    if "style_transform" in defaults:
        values["style.transform"] = defaults["style_transform"]
    if "scope" in defaults:
        scope = defaults["scope"]
        if not isinstance(scope, dict) or set(scope) != {"safety"}:
            raise ValueError(f"component profile {profile_id} scope is unsupported")
        values["project.safety_scope"] = [scope["safety"]]
    if "performance" in defaults:
        performance = defaults["performance"]
        if not isinstance(performance, dict):
            raise ValueError(f"component profile {profile_id} performance must be an object")
        unknown = set(performance) - {"movement_base", "persona_defaults"}
        if unknown:
            raise ValueError(
                f"component profile {profile_id} has unsupported performance fields: {sorted(unknown)}"
            )
        for key, value in performance.items():
            values[f"performance.{key}"] = value

    undeclared = set(values) - set(field_policies)
    if undeclared:
        raise ValueError(
            f"component profile {profile_id} maps to undeclared fields: {sorted(undeclared)}"
        )

    constraints = [
        {
            "constraint_id": f"constraint_component_{index:03d}_"
            + re.sub(r"[^A-Za-z0-9._-]+", "_", profile_id),
            "kind": "safety" if "safety" in str(text).lower() else "invariant",
            "text": str(text),
            "path": None,
            "value": None,
            "source_refs": [profile_id],
        }
        for index, text in enumerate(
            [
                *component.get("hard_constraints", []),
                *defaults.get("hard_constraints", []),
            ],
            1,
        )
    ]
    verification = defaults.get("verification", {})
    if verification and (
        not isinstance(verification, dict)
        or set(verification) != {"recommended_metrics"}
    ):
        raise ValueError(f"component profile {profile_id} verification is unsupported")
    metrics = []
    for metric in verification.get("recommended_metrics", []) if verification else []:
        if metric not in COMPONENT_METRIC_TARGETS:
            raise ValueError(f"component metric has no canonical target: {metric}")
        metrics.append(
            {
                "metric_id": _metric_id(metric, profile_id),
                "target_paths": COMPONENT_METRIC_TARGETS[metric],
                "method": metric,
                "observability": "measured",
            }
        )
    return values, constraints, metrics


def load_profile_catalog(root: Path = REPO_ROOT) -> ProfileCatalog:
    validator = _profile_validator(root)
    profile_paths = [
        *sorted((root / "lab/profiles/universal").glob("*.yaml")),
        *sorted((root / "lab/profiles/domain").glob("*.yaml")),
    ]
    if not profile_paths:
        raise ValueError("no universal or domain profiles found")
    profiles: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for path in profile_paths:
        profile = _read_yaml(path)
        _schema_errors(validator, profile, str(path.relative_to(root)))
        profile_id = profile["profile_id"]
        if profile_id in profiles:
            raise ValueError(f"duplicate profile id: {profile_id}")
        profiles[profile_id] = profile
        hashes[profile_id] = sha256_bytes(path.read_bytes())

    kernels = [row for row in profiles.values() if row["profile_kind"] == "universal"]
    if len(kernels) != 1 or kernels[0]["profile_id"] != KERNEL_PROFILE_ID:
        raise ValueError(f"exactly one universal profile must own {KERNEL_PROFILE_ID}")
    kernel = kernels[0]
    field_policies = dict(kernel["field_policies"])
    domains = tuple(
        sorted(
            (row for row in profiles.values() if row["profile_kind"] == "domain"),
            key=lambda row: (row["priority"], row["profile_id"]),
        )
    )
    for domain in domains:
        if domain["extends"] != [KERNEL_PROFILE_ID]:
            raise ValueError(f"{domain['profile_id']} must extend only {KERNEL_PROFILE_ID}")
        flatten_defaults(domain["defaults"], field_policies)
        for contribution in domain["control_contributions"]:
            if contribution["path"] not in field_policies:
                raise ValueError(
                    f"{domain['profile_id']} control targets undeclared field "
                    f"{contribution['path']}"
                )
        for constraint in domain["constraints"]:
            path = constraint.get("path")
            if path is not None and path not in field_policies:
                raise ValueError(
                    f"{domain['profile_id']} constraint targets undeclared field {path}"
                )
        for metric in domain["verification_metrics"]:
            unknown = set(metric["target_paths"]) - set(field_policies)
            if unknown:
                raise ValueError(
                    f"{domain['profile_id']} metric targets undeclared fields: {sorted(unknown)}"
                )
        for conflict in domain["conflicts"]:
            if conflict["field"] not in field_policies:
                raise ValueError(
                    f"{domain['profile_id']} conflict targets undeclared field {conflict['field']}"
                )
            unknown_profiles = set(conflict["profiles"]) - set(profiles)
            if unknown_profiles:
                raise ValueError(
                    f"{domain['profile_id']} conflict references unknown profiles: "
                    f"{sorted(unknown_profiles)}"
                )

    activation: dict[str, str] = {}
    components: dict[str, dict[str, Any]] = {}
    for domain in domains:
        for label in domain["activation_labels"]:
            if label in activation:
                raise ValueError(
                    f"router label {label} is owned by both {activation[label]} and "
                    f"{domain['profile_id']}"
                )
            activation[label] = domain["profile_id"]
        for component_id in domain["component_profiles"]:
            if component_id in components:
                continue
            path = _component_path(component_id, root)
            component = _read_yaml(path)
            if component.get("profile_id") != component_id:
                raise ValueError(f"component profile id mismatch in {path}")
            adapt_component_profile(component_id, component, field_policies)
            components[component_id] = component
            hashes[component_id] = sha256_bytes(path.read_bytes())

    router = _read_yaml(root / "lab/profiles/intent_routing.yaml")
    router_labels = set(router.get("profiles", {})) - {"general_video"}
    if set(activation) != router_labels:
        raise ValueError(
            "domain profile activation labels must exactly cover router labels; "
            f"missing={sorted(router_labels - set(activation))}, "
            f"extra={sorted(set(activation) - router_labels)}"
        )
    return ProfileCatalog(
        kernel=kernel,
        domains=domains,
        components=components,
        profile_hashes=hashes,
        field_policies=field_policies,
    )


def select_domain_profiles(
    labels: list[str], catalog: ProfileCatalog
) -> list[dict[str, Any]]:
    requested = set(labels) - {"general_video"}
    selected = [
        profile
        for profile in catalog.domains
        if requested & set(profile["activation_labels"])
    ]
    covered = {
        label
        for profile in selected
        for label in profile["activation_labels"]
        if label in requested
    }
    if covered != requested:
        raise ValueError(f"no domain profile for router labels: {sorted(requested - covered)}")
    return selected
