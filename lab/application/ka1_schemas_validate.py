"""WP-1 validation: sample PrinciplePack/RepresentationDecision instances must
validate against the KA-1 JSON schemas (draft 2020-12 validators embedded in
the schema files)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

OUT = Path(__file__).resolve().parent

SCHEMAS = {
    "principle_pack": OUT / "CPCS_PRINCIPLE_PACK_SCHEMA_v0.1.json",
    "representation_decision": OUT / "CPCS_REPRESENTATION_DECISION_SCHEMA_v0.1.json",
}

SAMPLE_PRINCIPLE_PACK = {
    "schema": "cpcs.principle_pack/0.1",
    "pack_id": "pack_" + "0" * 20,
    "pack_hash": "0" * 64,
    "principle_family": "support_contact_chain",
    "principle": "A believable contact is connected to support through a force-transfer chain.",
    "mechanism": "Body segments visibly organize around the interaction across a contact interval.",
    "failure_risk": {
        "failure_family_ids": ["FF-CONTACT"],
        "risk_statement": "partner moves without a force-transfer chain",
    },
    "evidence_ids": ["continuous_combat_state_contact_coarticulation_anime_time_volumetric_cinematography::continuous_combat_state_contact_coarticulation_anime_time_volumetric_cinematography__ku30"],
    "source_records": [
        {
            "atomic_record_id": "continuous_combat_state_contact_coarticulation_anime_time_volumetric_cinematography::continuous_combat_state_contact_coarticulation_anime_time_volumetric_cinematography__ku30",
            "universal_type": "Principle",
            "epistemic_status": "known",
        }
    ],
    "intent_application": {
        "domain_tags": ["combat"],
        "creative_goal_tags": ["hip_toss"],
    },
    "lineage": {
        "requirement_ids": ["REQ-CONTACT-1"],
        "treatment_packet_hash": "treatment_hash_placeholder",
        "activation_packet_id": "activation_placeholder",
    },
}

SAMPLE_REPRESENTATION_DECISION = {
    "schema": "cpcs.representation_decision/0.1",
    "knowledge_id": "pack_" + "0" * 20,
    "decision": "COMPOSITE",
    "rationale": "rule1: HARD contact evidence plus verification obligations",
    "authority": "CPCS_HARD_REQUIREMENT",
    "target_family": "cpcs.interaction.contact",
    "forbidden_coercions": ["flat_text", "contact_as_global_scalar"],
    "verification_counterpart": "cpcs.expected_state.contact",
    "decision_hash": "0" * 64,
}


def validate_schemas() -> list[str]:
    errors: list[str] = []
    for name, path in SCHEMAS.items():
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{name}: schema file unreadable: {exc}")
            continue
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:  # schema errors surface as exceptions
            errors.append(f"{name}: schema is invalid: {exc}")
    return errors


def validate_samples() -> list[str]:
    errors: list[str] = []
    samples = {
        "principle_pack": SAMPLE_PRINCIPLE_PACK,
        "representation_decision": SAMPLE_REPRESENTATION_DECISION,
    }
    for name, sample in samples.items():
        schema = json.loads(SCHEMAS[name].read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        problems = sorted(validator.iter_errors(sample), key=lambda e: list(e.path))
        if problems:
            for problem in problems:
                errors.append(f"{name}: {list(problem.path)}: {problem.message}")
    return errors


def main() -> int:
    errors = validate_schemas() + validate_samples()
    if errors:
        for error in errors:
            print("KA1 SCHEMA FAIL:", error, file=sys.stderr)
        return 1
    print("KA1 SCHEMAS GREEN:", ", ".join(sorted(SCHEMAS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
