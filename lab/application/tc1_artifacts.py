"""TC-1 artifact materializer: source manifest, coverage ledger, registry YAML,
registry schema, mapping receipts, ablation, acceptance."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import yaml  # type: ignore

from lab.compiler import cpcs_typed
from lab.compiler.profiles import REPO_ROOT

FROZEN_OUTPUT = Path("/Users/king/Downloads/Additional/Output")
FROZEN_RUNTIME = Path("/Users/king/Downloads/Additional/Runtime")
OUT = Path(__file__).resolve().parent

SOURCE_ROLES = {
    "CPCS_SEMANTIC_ARCHITECTURE_DISCOVERY_v0.1.1.json": "semantic_architecture",
    "CPCS_CANONICAL_VOCABULARY_v0.1.json": "canonical_vocabulary",
    "CPCS_RELATIONSHIP_VOCABULARY_v0.2.json": "relationship_vocabulary",
    "CPCS_REASONING_TRIGGER_MODEL_v0.1.json": "reasoning_trigger_model",
    "CPCS_REASONING_REQUIREMENT_MODEL_v0.1.json": "reasoning_requirement_model",
    "CPCS_REASONING_ACTIVATION_RULES_v0.1.json": "activation_rules",
    "CPCS_OBJECTIVE_RISK_MODEL_v0.1.json": "objective_risk_model",
    "CPCS_FAILURE_PREDICTION_MODEL_v0.1.json": "failure_prediction_model",
    "CPCS_CONTROL_VOCABULARY_v0.1.json": "control_vocabulary",
    "CPCS_TRIGGER_VOCABULARY_v0.1.json": "trigger_vocabulary",
    "CPCS_OBJECTIVE_VOCABULARY_v0.1.json": "objective_vocabulary",
    "CPCS_FAILURE_VOCABULARY_v0.1.json": "failure_vocabulary",
    "CPCS_ATOMIC_SEMANTIC_LINKAGE_v0.1.jsonl": "atomic_semantic_linkage",
    "CPCS_REQUIREMENT_EVIDENCE_MAP_v0.1.json": "requirement_evidence_map",
    "CPCS_PRODUCTION_RETRIEVAL_CONTRACT_v0.1.json": "production_retrieval_contract",
    "CPCS_RETRIEVAL_EVIDENCE_PACKET_SCHEMA_v0.1.json": "evidence_packet_schema",
    "CPCS_SCENE_INTENT_SCHEMA_v0.1.json": "scene_intent_schema",
    "CPCS_WORLD_MODEL_SCHEMA_v0.1.json": "world_model_schema",
    "CPCS_SCENE_PLAN_SCHEMA_v0.1.json": "scene_plan_schema",
    "CPCS_EXECUTION_OBLIGATION_SCHEMA_v0.1.json": "execution_obligation_schema",
    "CPCS_DIRECTOR_CONTROL_IR_SCHEMA_v0.1.json": "director_control_ir_schema",
    "CPCS_CANONICAL_SCORE_SCHEMA_v0.1.json": "canonical_score_schema",
    "CPCS_EXPECTED_STATE_CONTRACT_SCHEMA_v0.1.json": "expected_state_contract_schema",
    "CPCS_CONTROL_COMPILATION_RECEIPT_SCHEMA_v0.1.json": "control_compilation_receipt_schema",
    "CPCS_EXECUTION_FIXTURES_v0.1.json": "ec1_fixtures",
    "CPCS_PROVIDER_PROFILE_SCHEMA_v0.1.json": "provider_boundary_reference",
    "CPCS_PROVIDER_CARRIER_REGISTRY_v0.1.json": "provider_boundary_reference",
    "ARCHITECTURE_FREEZE_MANIFEST_v0.2.json": "architecture_freeze",
    "RUNTIME_RETRIEVAL_FREEZE_MANIFEST_v0.1.json": "runtime_freeze",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# disposition tables (deterministic, frozen in this module)
# --------------------------------------------------------------------------
DIMENSION_DISPOSITIONS = {
    "DIM-IDENTITY": ["REPRESENTED: entities[] entity_state + continuity.cpcs_invariants[]"],
    "DIM-STATE": ["REPRESENTED: entities[] entity_state",
                  "REPRESENTED: beats[] cpcs.event"],
    "DIM-GEOMETRY": ["REPRESENTED: entities[] entity_state"],
    "DIM-CONTACT": ["REPRESENTED: interactions[]"],
    "DIM-PERSISTENCE": ["REPRESENTED: continuity.cpcs_invariants[]"],
    "DIM-VISIBILITY": ["REPRESENTED: entities[] visibility/occlusion",
                       "REPRESENTED: camera.cpcs_subject_visibility[]"],
    "DIM-ORIENTATION": ["REPRESENTED: entities[] orientation"],
    "DIM-TRAJECTORY": ["REPRESENTED: beats[] cpcs.event"],
    "DIM-TIMING": ["REPRESENTED: continuity.cpcs_temporal_relations[]"],
    "DIM-CAUSALITY": ["REPRESENTED: continuity.cpcs_causal_edges[]"],
    "DIM-OWNERSHIP": ["REPRESENTED: entities[] possession/ownership"],
    "DIM-FORCE": ["REPRESENTED: interactions[] contact consequences"],
    "DIM-SUPPORT": ["REPRESENTED: entities[] support/balance"],
    "DIM-TRANSITION": ["REPRESENTED: beats[] cpcs.event"],
    "DIM-UNCERTAINTY": ["METADATA_ONLY: epistemic metadata"],
    "DIM-MEASUREMENT": ["VERIFICATION_ONLY: verification_requirements[]"],
    "DIM-EPISTEMICS": ["METADATA_ONLY: epistemic metadata"],
    "DIM-COORDINATION": ["REPRESENTED: interactions[] coordination"],
    "DIM-CONTINUITY": ["REPRESENTED: continuity.cpcs_invariants[]"],
    "DIM-CAMERA": ["REPRESENTED: camera.cpcs_subject_visibility[]",
                   "REPRESENTED: continuity.cpcs_invariants[] camera-axis"],
    "DIM-VERIFICATION": ["VERIFICATION_ONLY: verification_requirements[]"],
}

CONDITION_TYPE_DISPOSITIONS = {
    "STATE": "REPRESENTED: entities[] entity_state",
    "RELATIONSHIP": "REPRESENTED: interactions[]",
    "EVENT": "REPRESENTED: beats[] cpcs.event",
    "TRANSITION": "REPRESENTED: beats[] cpcs.event (state transition)",
    "PERSISTENCE": "REPRESENTED: continuity.cpcs_invariants[]",
    "NON_OCCURRENCE": "REPRESENTED: continuity.cpcs_constraints[]",
    "TEMPORAL_ORDER": "REPRESENTED: continuity.cpcs_temporal_relations[]",
    "CAUSAL_RESULT": "REPRESENTED: continuity.cpcs_causal_edges[]",
}

OBLIGATION_KIND_DISPOSITIONS = {
    "STATE": "REPRESENTED: entities[] entity_state",
    "EVENT": "REPRESENTED: beats[] cpcs.event",
    "CONTROL": "REPRESENTED: registry-typed control",
    "CONSTRAINT": "REPRESENTED: continuity.cpcs_constraints[]",
    "VERIFICATION": "VERIFICATION_ONLY: verification_requirements[]",
    "EXPECTED_OUTCOME": "EXPECTED_STATE_ONLY: expected-state contract",
}


def main() -> int:
    # 1. source manifest
    manifest = {
        "artifact": "CPCS_TYPED_EXPANSION_SOURCE_MANIFEST", "version": "v0.1",
        "sources": [],
    }
    for filename, role in sorted(SOURCE_ROLES.items()):
        path = (FROZEN_OUTPUT / filename) if (FROZEN_OUTPUT / filename).is_file() \
            else (FROZEN_RUNTIME / filename)
        if not path.is_file():
            print("MISSING source:", filename)
            continue
        manifest["sources"].append({
            "artifact_path": str(path), "filename": filename,
            "artifact_version": filename.split("_v")[-1].replace(".json", "")
            if "_v" in filename else "n/a",
            "artifact_hash": sha256_file(path), "semantic_role": role,
        })
    (OUT / "CPCS_TYPED_EXPANSION_SOURCE_MANIFEST_v0.1.json").write_text(
        json.dumps(manifest, indent=1))

    # 2. coverage ledger
    ledger = {
        "artifact": "CPCS_TYPED_KNOWLEDGE_COVERAGE_LEDGER", "version": "v0.1",
        "dimensions": DIMENSION_DISPOSITIONS,
        "condition_types": CONDITION_TYPE_DISPOSITIONS,
        "obligation_kinds": OBLIGATION_KIND_DISPOSITIONS,
        "control_types": {},
        "registry": {
            path_id: {"semantic_family": e["semantic_family"],
                      "semantic_kind": e["semantic_kind"],
                      "canonical_target": e["canonical_target"],
                      "provider_neutral": e["provider_neutral"]}
            for path_id, e in cpcs_typed.REGISTRY.items()},
    }
    for ct in sorted({ct for entry in cpcs_typed.REGISTRY.values()
                      for ct in entry["source_control_types"]}):
        path_id = cpcs_typed.CONTROL_TYPE_TO_PATH.get(ct)
        ledger["control_types"][ct] = (
            f"REPRESENTED: {cpcs_typed.REGISTRY[path_id]['canonical_target']}"
            if path_id and path_id in cpcs_typed.REGISTRY
            else "UNRESOLVED_WITH_REASON: no deterministic typed mapping")
    (OUT / "CPCS_TYPED_KNOWLEDGE_COVERAGE_LEDGER_v0.1.json").write_text(
        json.dumps(ledger, indent=1))

    # 3. registry yaml + json schema
    registry_yaml = {
        "artifact": "CPCS_REASONING_PATH_REGISTRY", "version": "v0.1",
        "registry_version": cpcs_typed.REGISTRY_VERSION,
        "rule": "bridge between CPCS semantics and repo-native canonical representation; "
                "provider_neutral; D4 enforced (no flat-text admission)",
        "entries": cpcs_typed.REGISTRY,
    }
    (OUT / "cpcs_reasoning_path_registry.yaml").write_text(
        yaml.safe_dump(registry_yaml, sort_keys=False))
    (OUT / "CPCS_REASONING_PATH_REGISTRY_v0.1.json").write_text(
        json.dumps(registry_yaml, indent=1))
    registry_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "cpcs.reasoning_path_registry/1.0",
        "type": "object",
        "required": ["artifact", "version", "registry_version", "entries"],
        "properties": {
            "artifact": {"const": "CPCS_REASONING_PATH_REGISTRY"},
            "version": {"const": "v0.1"},
            "registry_version": {"type": "string"},
            "rule": {"type": "string"},
            "entries": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "required": ["path_id", "semantic_family", "semantic_kind",
                                 "canonical_target", "value_schema", "scope_types",
                                 "target_types", "merge_operator",
                                 "source_control_types", "source_requirement_classes",
                                 "source_concept_ids", "allowed_evidence_classes",
                                 "forbidden_coercions", "verification_counterpart",
                                 "provider_neutral", "provenance_requirements"],
                    "properties": {
                        "provider_neutral": {"const": True},
                        "semantic_kind": {"enum": [
                            "STATE", "CONTROL", "RELATION", "EVENT", "TEMPORAL",
                            "CAUSAL", "INVARIANT", "CONSTRAINT", "VERIFICATION"]},
                    },
                    "additionalProperties": False,
                },
            },
        },
        "additionalProperties": False,
    }
    (OUT / "cpcs_reasoning_path_registry.schema.json").write_text(
        json.dumps(registry_schema, indent=1))
    print("manifest sources:", len(manifest["sources"]))
    print("ledger dimensions:", len(DIMENSION_DISPOSITIONS),
          "condition types:", len(CONDITION_TYPE_DISPOSITIONS),
          "obligation kinds:", len(OBLIGATION_KIND_DISPOSITIONS),
          "control types:", len(ledger["control_types"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
