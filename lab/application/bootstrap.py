"""BOOT-1 — first-run bootstrap (idempotent, secret-free, doctor-reusing)."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from lab.compiler.profiles import REPO_ROOT

BOOTSTRAP_VERSION = "cpcs-bootstrap-v1"
CONFIG_REL = Path("work/application/bootstrap/cpcs_runtime.json")

REQUIRED_ARTIFACTS = (
    "ARCHITECTURE_FREEZE_MANIFEST_v0.2.json",
    "RUNTIME_RETRIEVAL_FREEZE_MANIFEST_v0.1.json",
    "CPCS_PRODUCTION_RETRIEVAL_CONTRACT_v0.1.json",
    "CPCS_RETRIEVAL_GOLD_v0.2.json",
)
REQUIRED_MODULES = ("cpcs_loader.py", "cpcs_production.py", "ec1_compiler.py")


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def config_path(root: Path) -> Path:
    override = os.environ.get("CPCS_BOOTSTRAP_CONFIG_OVERRIDE")
    if override:
        return Path(override).expanduser().resolve()
    return root / CONFIG_REL


def load_local_config(root: Path) -> dict[str, Any] | None:
    path = config_path(root)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def write_local_config(root: Path, runtime_path: str, identities: dict[str, str]) -> Path:
    path = config_path(root)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    payload = {
        "schema": "cpcs.bootstrap_config/1.0",
        "runtime_path": str(Path(runtime_path).resolve()),
        "architecture_freeze_identity": identities["architecture_freeze_identity"],
        "retrieval_runtime_freeze_identity": identities["retrieval_runtime_freeze_identity"],
        "bootstrap_version": BOOTSTRAP_VERSION,
        "bootstrapped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    path.write_text(json.dumps(payload, indent=1, sort_keys=True))
    os.chmod(path, 0o600)
    return path


def validate_runtime(runtime_path: str) -> tuple[dict[str, str] | None, str | None]:
    """Identity/artifact validation. Directory existence alone is NOT accepted."""
    rt = Path(runtime_path)
    if not rt.is_dir():
        return None, f"runtime directory does not exist: {rt}"
    output_dir = rt.parent / "Output"
    missing = [name for name in REQUIRED_ARTIFACTS
               if not (output_dir / name).is_file()]
    missing += [name for name in REQUIRED_MODULES if not (rt / name).is_file()]
    if missing:
        return None, "runtime is missing required frozen artifacts: " + ", ".join(missing)
    return {
        "architecture_freeze_identity": _sha_file(
            output_dir / "ARCHITECTURE_FREEZE_MANIFEST_v0.2.json")[:16],
        "retrieval_runtime_freeze_identity": _sha_file(
            output_dir / "RUNTIME_RETRIEVAL_FREEZE_MANIFEST_v0.1.json")[:16],
    }, None


def resolved_runtime_path() -> str | None:
    """Environment first, then bootstrapped local config (app root)."""
    env = os.environ.get("CPCS_FROZEN_RUNTIME_PATH")
    if env:
        return str(Path(env).expanduser().resolve())
    config = load_local_config(REPO_ROOT)
    if config and config.get("runtime_path"):
        return config["runtime_path"]
    return None


def resolve_runtime(arguments: dict[str, Any], root: Path) -> tuple[str, str]:
    """Resolution order: explicit argument > valid local config > env."""
    explicit = arguments.get("runtime")
    if explicit:
        return str(Path(explicit).expanduser().resolve()), "argument"
    config = load_local_config(root)
    if config and config.get("runtime_path"):
        return config["runtime_path"], "local_config"
    env = os.environ.get("CPCS_FROZEN_RUNTIME_PATH")
    if env:
        return str(Path(env).expanduser().resolve()), "environment"
    raise LookupError(
        "no frozen runtime configured: pass --input with {\"runtime\": ...} to "
        "cpcs.bootstrap, or export CPCS_FROZEN_RUNTIME_PATH=/path/to/frozen/Runtime")


def bootstrap(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    existing = load_local_config(root)
    try:
        runtime_path, source = resolve_runtime(arguments, root)
    except LookupError as exc:
        return {
            "status": "NOT_READY",
            "runtime_path": None,
            "reason": str(exc),
            "remediation": (
                "provide the frozen runtime by one of: (1) bin/cpcs bootstrap with "
                "{\"runtime\": \"/path/to/frozen/Runtime\"}, (2) "
                "CPCS_FROZEN_RUNTIME_PATH environment variable, or (3) a prior "
                "bootstrap config under work/application/bootstrap/"),
            "wrote_config": False,
            "fake_backend_used": False,
        }
    identities, error = validate_runtime(runtime_path)
    if error:
        return {
            "status": "NOT_READY",
            "runtime_path": runtime_path,
            "reason": error,
            "remediation": ("point CPCS at a complete frozen runtime containing the "
                            "architecture freeze manifest, retrieval runtime freeze "
                            "manifest, and the production retrieval artifacts"),
            "wrote_config": False,
            "fake_backend_used": False,
        }
    unchanged = bool(existing
                     and existing.get("runtime_path") == str(Path(runtime_path).resolve())
                     and existing.get("architecture_freeze_identity")
                     == identities["architecture_freeze_identity"])
    wrote = None
    if not unchanged:
        wrote = str(write_local_config(root, runtime_path, identities))
    from .cpcs_guided_handlers import cpcs_doctor

    doctor = cpcs_doctor(root, runtime_path=runtime_path)
    ready = doctor["status"] == "READY"
    return {
        "status": "READY" if ready else "NOT_READY",
        "runtime_path": runtime_path,
        "resolution_source": source,
        "identities": identities,
        "wrote_config": wrote,
        "idempotent": unchanged,
        "doctor": doctor,
        "fake_backend_used": False,
        "provider_credentials_required": False,
        "default_reasoning_policy": "CURRENT_BASELINE (unchanged)",
    }
