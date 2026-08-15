"""TC-2: residual classification, executable-semantic coverage, ablation, acceptance."""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

OUT = Path(__file__).resolve().parent

# deterministic disposition rules (structured identifiers only, no prose)
NON_EXECUTABLE_BY_UT = {
    "Concept": "NON_EXECUTABLE_KNOWLEDGE",
    "Schema": "NON_EXECUTABLE_KNOWLEDGE",
    "Definition": "NON_EXECUTABLE_KNOWLEDGE",
    "Observation": "EPISTEMIC_METADATA",
    "Observations": "EPISTEMIC_METADATA",
    "EvidenceRecord": "PROVENANCE_ONLY",
    "ResearchGap": "RESEARCH_GOVERNANCE",
    "OpenQuestion": "RESEARCH_GOVERNANCE",
    "Measurement": "VERIFICATION_ONLY",
    "Metric": "VERIFICATION_ONLY",
    "ProviderImplication": "PROVIDER_ONLY",
    "Procedure": "PLANNING_ONLY",
    "Workflow": "PLANNING_ONLY",
    "Recommendation": "PLANNING_ONLY",
    "Technique": "PLANNING_ONLY",
    "Heuristic": "PLANNING_ONLY",
}
EXECUTABLE_BY_UT = {
    "Constraint": "cpcs.continuity.invariant",
    "NegativeConstraint": "cpcs.constraint.negative",
    "Invariant": "cpcs.continuity.invariant",
    "Rule": "cpcs.continuity.invariant",
    "FailureMode": "cpcs.continuity.invariant",
    "Principle": "cpcs.continuity.invariant",
    "Requirement": "cpcs.continuity.invariant",
    "DecisionRule": "PLANNING_ONLY",
    "ConditionalRule": "PLANNING_ONLY",
    "Default": "PLANNING_ONLY",
    "DesignDecision": "PLANNING_ONLY",
    "Policy": "PLANNING_ONLY",
    "Doctrine": "PLANNING_ONLY",
    "Claim": "EPISTEMIC_METADATA",
    "Fact": "EPISTEMIC_METADATA",
    "Finding": "EPISTEMIC_METADATA",
    "Experiment": "RESEARCH_GOVERNANCE",
    "WorkedExample": "PLANNING_ONLY",
    "Mapping": "PROVENANCE_ONLY",
    "Relationship": "PROVENANCE_ONLY",
    "Table": "NON_EXECUTABLE_KNOWLEDGE",
    "JSONSchema": "NON_EXECUTABLE_KNOWLEDGE",
    "Ontology": "NON_EXECUTABLE_KNOWLEDGE",
    "Vocabulary": "NON_EXECUTABLE_KNOWLEDGE",
    "Mechanism": "PLANNING_ONLY",
    "Process": "PLANNING_ONLY",
    "ProcessStep": "PLANNING_ONLY",
    "SelfCorrection": "RESEARCH_GOVERNANCE",
    "Corollary": "PLANNING_ONLY",
    "PromptTemplate": "PROVIDER_ONLY",
    "Contract": "PLANNING_ONLY",
    "ArchitectureRule": "RESEARCH_GOVERNANCE",
    "Specification": "PLANNING_ONLY",
    "OutcomeRequirement": "EXPECTED_STATE_ONLY",
    "TestableRule": "VERIFICATION_ONLY",
    "ValidationRule": "VERIFICATION_ONLY",
    "Checklist": "VERIFICATION_ONLY",
    "Protocol": "VERIFICATION_ONLY",
    "Source": "PROVENANCE_ONLY",
    "Grammar": "NON_EXECUTABLE_KNOWLEDGE",
    "Example": "PLANNING_ONLY",
    "SchemaObject": "NON_EXECUTABLE_KNOWLEDGE",
    "ControlVariable": "PLANNING_ONLY",
}


def classify(ledger: dict) -> dict:
    counts = Counter()
    rows = []
    for name, fx in ledger["fixtures"].items():
        for r in fx["residuals"]:
            ut = r["universal_type"] or "Unknown"
            disposition = NON_EXECUTABLE_BY_UT.get(ut) or EXECUTABLE_BY_UT.get(ut)
            if disposition and disposition not in ("PLANNING_ONLY",
                                                   "cpcs.continuity.invariant",
                                                   "cpcs.constraint.negative"):
                pass
            if ut in NON_EXECUTABLE_BY_UT:
                disposition = NON_EXECUTABLE_BY_UT[ut]
            elif ut in EXECUTABLE_BY_UT:
                target = EXECUTABLE_BY_UT[ut]
                if target in ("cpcs.continuity.invariant", "cpcs.constraint.negative"):
                    disposition = "MISSING_EXISTING_REGISTRY_RULE"
                else:
                    disposition = target
            elif r["control_type"] and r["control_type"][0] == "CONTROL_SELECTION_RULE":
                disposition = "MISSING_EXISTING_REGISTRY_RULE"
            else:
                disposition = "UNRESOLVED"
            counts[disposition] += 1
            rows.append({
                "fixture": name, "control_id": r["control_id"],
                "universal_type": ut, "control_type": r["control_type"],
                "hardness": r["hardness"],
                "requirement_ids": r["requirement_ids"],
                "disposition": disposition,
            })
    return {"counts": dict(counts), "rows": rows,
            "total": sum(counts.values()),
            "unresolved": [r for r in rows if r["disposition"] == "UNRESOLVED"]}


def main() -> int:
    ledger = json.loads((OUT / "CPCS_RESIDUAL_MAPPING_LEDGER_v0.1.json").read_text())
    classification = classify(ledger)
    (OUT / "CPCS_RESIDUAL_CLASSIFICATION_v0.1.json").write_text(
        json.dumps(classification, indent=1))
    print("before-closure classification:", classification["counts"])
    print("unresolved:", len(classification["unresolved"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
