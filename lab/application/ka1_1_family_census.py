"""KA-1.1 principle-family census (computed from the frozen corpus).

--before: distribution of universal types currently mapping to
          evidence_binding, with doc/epistemic/facet coverage.
--after:  same census under the refined role-based mapping.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent
BEFORE = OUT / "KA1_1_PRINCIPLE_FAMILY_CENSUS_BEFORE_v0.1.json"
AFTER = OUT / "KA1_1_PRINCIPLE_FAMILY_CENSUS_AFTER_v0.1.json"
RUNTIME_OUTPUT = Path(
    "/Users/king/Downloads/Additional/Output/CPCS_ATOMIC_RETRIEVAL_RECORDS_v0.2.jsonl")


def load_records():
    return [json.loads(line) for line in RUNTIME_OUTPUT.open()]


def family_of(record: dict, use_refined: bool) -> str:
    ut = record.get("universal_type") or "Unknown"
    if use_refined:
        sys.path.insert(0, str(OUT.parents[1]))
        from lab.application.cpcs_knowledge_application import _principle_family
        return _principle_family(record)
    if ut == "FailureMode":
        return "failure_prevention_or_mapped"
    if ut in ("Constraint", "NegativeConstraint", "Invariant", "Rule",
              "Requirement"):
        return "protected_invariant"
    if ut in ("Mechanism", "Procedure", "Process", "ProcessStep", "Workflow"):
        return "mechanism_binding"
    if ut == "Principle":
        return "grounded_principle"
    return "evidence_binding"


def compute(records, use_refined: bool) -> dict:
    rows = []
    families: Counter = Counter()
    for r in records:
        ut = r.get("universal_type") or "Unknown"
        family = family_of(r, use_refined)
        families[family] += 1
        sl = r.get("semantic_linkage") or {}
        rows.append({
            "universal_type": ut,
            "family": family,
            "document_id": r.get("document_id"),
            "epistemic_state": r.get("epistemic_state"),
            "concept_count": len((sl.get("canonical_concept_ids") or {}).keys()),
            "mechanism_token_count": len((sl.get("control_ids") or {}).keys()),
            "failure_family_count": len((sl.get("failure_family_ids") or {}).keys()),
            "trigger_count": len((sl.get("trigger_ids") or {}).keys()),
            "objective_count": len((sl.get("objective_ids") or {}).keys()),
        })
    per_ut: dict[str, dict] = {}
    for ut in sorted({row["universal_type"] for row in rows}):
        ut_rows = [row for row in rows if row["universal_type"] == ut]
        per_ut[ut] = {
            "count": len(ut_rows),
            "families": dict(Counter(r["family"] for r in ut_rows)),
            "documents": len({r["document_id"] for r in ut_rows}),
            "epistemic_states": dict(Counter(r["epistemic_state"]
                                            for r in ut_rows)),
            "concept_coverage": sum(1 for r in ut_rows if r["concept_count"]),
            "mechanism_token_coverage": sum(1 for r in ut_rows
                                            if r["mechanism_token_count"]),
            "failure_family_coverage": sum(1 for r in ut_rows
                                           if r["failure_family_count"]),
            "requirement_coverage": sum(1 for r in ut_rows
                                        if r["trigger_count"]
                                        or r["objective_count"]),
        }
    largest = families.most_common(1)[0] if families else ("none", 0)
    return {
        "total_records": len(rows),
        "family_distribution": dict(families.most_common()),
        "largest_family": largest[0],
        "largest_family_count": largest[1],
        "largest_family_share": round(largest[1] / max(len(rows), 1), 4),
        "per_universal_type": per_ut,
    }


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--before"
    use_refined = mode == "--after"
    records = load_records()
    result = compute(records, use_refined)
    target = AFTER if use_refined else BEFORE
    target.write_text(json.dumps(result, indent=1) + "\n")
    print(f"{mode}: families={len(result['family_distribution'])} "
          f"largest={result['largest_family']} "
          f"({result['largest_family_share']:.0%}) "
          f"-> {target.name}")
    print(json.dumps(result["family_distribution"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
