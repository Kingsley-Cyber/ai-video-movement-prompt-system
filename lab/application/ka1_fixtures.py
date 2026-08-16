"""KA-1 WP-7 — cross-domain fixtures + real-runtime smoke.

Three fixtures share one bridge mechanism; their canonical outputs differ
because different corpus evidence, mechanisms, risks, affordances, and
representation decisions are relevant (intent-conditioned application).

Each fixture runs hermetically through FakeBackend (always) and through the
frozen runtime when CPCS_FROZEN_RUNTIME_PATH is set (env-gated).

Output artifact: CPCS_KNOWLEDGE_APPLICATION_FIXTURES_v0.1.json (computed).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lab.application.cpcs_deliberation import (
    FAKE_SNAPSHOT,
    DeliberationEngine,
)
from lab.application.reasoning_treatment import (
    FakeBackend,
    TreatmentAdapter,
)
from lab.compiler.profiles import REPO_ROOT

OUT = Path(__file__).resolve().parent
ARTIFACT_PATH = OUT / "CPCS_KNOWLEDGE_APPLICATION_FIXTURES_v0.1.json"

FIXTURES: dict[str, dict[str, Any]] = {
    "COMBAT": {
        "intent": "A fighter performs a hip toss.",
        "expected": ["support_chain", "rotation_roles", "projection_phase",
                     "recovery_state"],
    },
    "ECOMMERCE": {
        "intent": "A person unboxes a luxury watch.",
        "expected": ["object_identity", "hand_object_interaction",
                     "material_visibility", "camera_realism"],
    },
    "COOKING": {
        "intent": "A chef slices a tomato.",
        "expected": ["knife_object_interaction", "cutting_motion",
                     "food_deformation", "hand_safety"],
    },
}


def bridge_result(intent_text: str, backend: Any, snapshot: Any) -> dict[str, Any]:
    """Run DR-1 activation + KA-1 bridge + typed translation for one intent."""
    engine = DeliberationEngine(snapshot, backend)
    activation, packet = engine.activate(
        intent_text, {"intent": {"primary_domain": "action"}}, observations=[])
    translation = TreatmentAdapter(REPO_ROOT).translate(
        packet, snapshot=snapshot, activation=activation)
    application_set = translation.application_set or {}
    decision_counts: dict[str, int] = {}
    risk_tokens: set[str] = set()
    mechanism_tokens: set[str] = set()
    for entry in application_set.get("applications", []):
        decision = entry["decision"]["decision"]
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
        risk_tokens |= set(entry["pack"]["failure_risk"].get("risk_tokens", []))
        mechanism_tokens |= {
            token.strip() for token in entry["pack"]["mechanism"]
            .removeprefix("mechanism: ").split(",")
            if token.strip() and token.strip() != "none"
        }
    structured_counts: dict[str, int] = {}
    for obj in translation.structured_objects:
        key = obj.get("schema") or obj.get("target") or "unknown"
        structured_counts[key] = structured_counts.get(key, 0) + 1
    return {
        "principle_pack_count": len(application_set.get("applications", [])),
        "decision_counts": dict(sorted(decision_counts.items())),
        "risk_tokens": sorted(risk_tokens),
        "mechanism_tokens": sorted(mechanism_tokens),
        "structured_object_counts": dict(sorted(structured_counts.items())),
        "planning_guidance_count": len(translation.planning_guidance),
        "reasoning_material_count": len(translation.reasoning_material),
        "unknown_count": len(application_set.get("unknowns", [])),
        "set_hash": application_set.get("set_hash"),
        "structured_objects": [
            {"target": obj.get("target"), "schema": obj.get("schema"),
             "value": obj.get("value")}
            for obj in translation.structured_objects
        ],
    }


def compute_fixture_artifact(snapshot: Any, backend: Any,
                             label: str) -> dict[str, Any]:
    fixtures: dict[str, Any] = {}
    for name, spec in sorted(FIXTURES.items()):
        result = bridge_result(spec["intent"], backend, snapshot)
        result.pop("structured_objects")
        fixtures[name] = {
            "intent": spec["intent"],
            "expected": spec["expected"],
            "backend": label,
            **result,
        }
    return {
        "artifact": "CPCS_KNOWLEDGE_APPLICATION_FIXTURES",
        "version": "v0.1",
        "fixtures": fixtures,
    }


def write_fixture_artifact(snapshot: Any = FAKE_SNAPSHOT,
                           backend: Any | None = None) -> dict[str, Any]:
    backend = backend if backend is not None else FakeBackend()
    label = "hermetic" if isinstance(backend, FakeBackend) else "real_runtime"
    artifact = compute_fixture_artifact(snapshot, backend, label)
    ARTIFACT_PATH.write_text(json.dumps(artifact, indent=1) + "\n")
    return artifact


if __name__ == "__main__":
    print(json.dumps(write_fixture_artifact(), indent=1))
