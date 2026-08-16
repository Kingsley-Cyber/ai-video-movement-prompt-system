"""KA-2 WP-3 — RecruitmentRefinementPacket + DR-1 closure loop (additive).

Bounded prerequisite emergence from a recruitment set, plus a
deterministic `RecruitmentRefinementPacket` that additively fills the
DR-1 closure's two existing fields:
  - closure["planning_guidance"]
  - closure["non_executable_knowledge_used"]

Existing closure computed values are NEVER replaced. The pre-refinement
closure hash is recorded on `closure["lineage"]["ka2_pre_refinement_closure_hash"]`
before the additive fill, and the closure's `packet_hash` is recomputed
over the post-fill body.

FROZEN:
- No silent invention: new prerequisite IDs must appear in at least one
  recruited region's evidence or pack lineage.
- Bounded: MAX_PREREQ_DEPTH=1 (one wave from recruitment), MAX_ADDED=8.
- No frozen retrieval widening; missing expertise → COVERAGE_GAP.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

MAX_PREREQ_DEPTH = 1
MAX_ADDED_PREREQS_PER_INTENT = 8

REFINEMENT_SCHEMA = "cpcs.recruitment_refinement_packet/0.1"
COVERAGE_GAP_SCHEMA = "cpcs.coverage_gap/0.1"

# Gap taxonomy: WHERE knowledge was lost, not just that it was lost.
GAP_CLASSES = [
    "CORPUS_ABSENCE",
    "RETRIEVAL_COVERAGE_GAP",
    "METADATA_COVERAGE_GAP",
    "AWARENESS_FAILURE",
    "CONSTELLATION_FAILURE",
    "RECRUITMENT_FAILURE",
    "REFINEMENT_FAILURE",
    "REPRESENTATION_GAP",
    "SERIALIZATION_GAP",
    "VERIFICATION_GAP",
]

GAP_KIND_TO_CLASS = {
    "mandatory_requirement_uncovered": "RETRIEVAL_COVERAGE_GAP",
    "predicted_failure_uncovered": "RETRIEVAL_COVERAGE_GAP",
    "reasoning_dimension_unsupported": "CORPUS_ABSENCE",
    "prerequisite_unsupported": "RETRIEVAL_COVERAGE_GAP",
    "no_evidence_under_frozen_window": "RETRIEVAL_COVERAGE_GAP",
}


def _classify_gap(gap: dict[str, Any]) -> dict[str, Any]:
    out = dict(gap)
    if "gap_class" not in out:
        out["gap_class"] = GAP_KIND_TO_CLASS.get(
            out.get("kind", ""), "RECRUITMENT_FAILURE")
    return out


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _sorted(values: Any) -> list[str]:
    if not values:
        return []
    return sorted(set(str(v) for v in values if v))


def _pack_lookup(application_set: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for entry in (getattr(application_set, "applications", []) or []):
        if isinstance(entry, dict) and "pack" in entry:
            pack = entry["pack"]
        else:
            pack = entry
        pid = (pack or {}).get("pack_id")
        if pid:
            out[pid] = pack
    return out


def _recruited_region_lookup(recruitment: dict[str, Any]
                             ) -> dict[str, dict[str, Any]]:
    return {d["region_id"]: d for d in recruitment.get("dispositions", [])
            if d.get("disposition") == "RECRUIT"}


def assess_prerequisites(
    recruitment: dict[str, Any],
    constellation: Any,
    activation: dict[str, Any],
    *,
    pack_lookup: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Bounded prerequisite emergence + coverage gap aggregation.

    Returns (new_prerequisite_requirement_ids, coverage_gaps).

    A prerequisite is added only if a recruited region's packs reference
    a requirement ID that the activation did not already include as
    `candidate_requirements`. Bounded by MAX_ADDED_PREREQS_PER_INTENT.
    """
    pack_lookup = pack_lookup or {}
    regions = list(getattr(constellation, "regions", []) or [])
    if regions and isinstance(regions[0], dict) and "region_id" in regions[0]:
        region_dicts = regions
    else:
        region_dicts = [r.to_dict() if hasattr(r, "to_dict") else r for r in regions]
    recruited = _recruited_region_lookup(recruitment)
    existing_reqs = set(activation.get("candidate_requirements", []) or [])
    candidates: dict[str, set[str]] = {}
    supporting_evidence: dict[str, set[str]] = {}
    for region in region_dicts:
        if region["region_id"] not in recruited:
            continue
        for pid in region.get("pack_ids", []) or []:
            pack = pack_lookup.get(pid) or {}
            lineage = pack.get("lineage", {}) or {}
            for rid in (lineage.get("requirement_ids", []) or []):
                if rid in existing_reqs:
                    continue
                candidates.setdefault(rid, set()).add(region["region_id"])
                supporting_evidence.setdefault(rid, set()).update(
                    pack.get("evidence_ids", []) or [])
        for eid in region.get("evidence_ids", []) or []:
            for fam in (region.get("failure_family_ids", []) or []):
                if fam in existing_reqs:
                    continue
                candidates.setdefault(fam, set()).add(region["region_id"])
                supporting_evidence.setdefault(fam, set()).add(eid)

    ordered = sorted(candidates.items(), key=lambda kv: (kv[0], sorted(kv[1])))
    new_reqs: list[str] = []
    for rid, supporting_regions in ordered:
        if len(new_reqs) >= MAX_ADDED_PREREQS_PER_INTENT:
            break
        if not supporting_evidence.get(rid):
            continue
        new_reqs.append(rid)

    coverage_gaps: list[dict[str, Any]] = []
    for gap in recruitment.get("coverage_gaps", []) or []:
        coverage_gaps.append(_classify_gap(gap))
    for rid in new_reqs:
        if not supporting_evidence.get(rid):
            coverage_gaps.append({
                "coverage_gap_id": "gap_prereq_" + _sha(rid)[:16],
                "kind": "prerequisite_unsupported",
                "requirement_id": rid,
                "evidence_ids": [],
                "reason": "needed prerequisite has no supporting evidence in the retrieved window",
            })

    return new_reqs, coverage_gaps


def build_refinement_packet(
    recruitment: dict[str, Any],
    constellation: Any,
    activation: dict[str, Any],
    *,
    new_prerequisites: list[str] | None = None,
    coverage_gaps: list[dict[str, Any]] | None = None,
    application_set: Any | None = None,
) -> dict[str, Any]:
    new_prerequisites = list(new_prerequisites or [])
    coverage_gaps = list(coverage_gaps or [])
    recruited: list[str] = []
    context: list[str] = []
    archived: list[str] = []
    unresolved: list[str] = []
    planning_guidance: list[dict[str, Any]] = []
    non_executable_used: list[str] = []
    pack_lookup = _pack_lookup(application_set) if application_set is not None else {}

    for d in recruitment.get("dispositions", []) or []:
        rid = d["region_id"]
        disp = d["disposition"]
        if disp == "RECRUIT":
            recruited.append(rid)
            for pid in (next((r for r in (getattr(constellation, "regions", []) or [])
                              if r.get("region_id") == rid), {}).get("pack_ids", [])
                        or []):
                pack = pack_lookup.get(pid) or {}
                decision = pack.get("decision", "") or ""
                if decision == "PLANNING":
                    planning_guidance.append({
                        "guidance_id": "guidance_" + _sha(pid)[:16],
                        "region_id": rid,
                        "pack_id": pid,
                        "requirement_ids": (pack.get("lineage") or {}).get(
                            "requirement_ids", []),
                        "evidence_ids": pack.get("evidence_ids", []),
                        "authority": "CPCS_GROUNDED_RECOMMENDATION",
                        "bound_signals": d.get("intent_signals", {}),
                        "lineage": {
                            "refinement_id": None,
                            "activation_packet_id": (
                                activation or {}).get("packet_id", "unknown"),
                        },
                    })
                if decision == "NON_EXECUTABLE":
                    non_executable_used.append(
                        f"{rid}:{pid}:{pack.get('principle_family', 'unknown')}")
        elif disp == "CONTEXT":
            context.append(rid)
        elif disp == "ARCHIVE":
            archived.append(rid)
        elif disp == "UNRESOLVED":
            unresolved.append(rid)

    recruited.sort()
    context.sort()
    archived.sort()
    unresolved.sort()
    non_executable_used = sorted(set(non_executable_used))

    body = {
        "recruited_region_ids": recruited,
        "context_region_ids": context,
        "archived_region_ids": archived,
        "unresolved_region_ids": unresolved,
        "coverage_gaps": sorted(coverage_gaps, key=lambda g: g.get("coverage_gap_id", "")),
        "new_prerequisite_requirements": sorted(new_prerequisites),
        "planning_guidance": sorted(
            planning_guidance, key=lambda g: g["guidance_id"]),
        "non_executable_knowledge_used": non_executable_used,
        "disposition_digests": [
            {
                "region_id": d["region_id"],
                "disposition": d["disposition"],
                "reason_codes": d.get("reason_codes", []),
                "disposition_hash": d.get("disposition_hash", ""),
            }
            for d in sorted(
                recruitment.get("dispositions", []) or [],
                key=lambda x: x["region_id"])
        ],
        "activation_packet_id": (activation or {}).get("packet_id", "unknown"),
        "constellation_id": getattr(constellation, "constellation_id", "unknown"),
    }
    refinement_hash = _sha(body)
    body["lineage"] = {
        "activation_packet_id": body["activation_packet_id"],
        "constellation_id": body["constellation_id"],
        "max_prereq_depth": MAX_PREREQ_DEPTH,
        "max_added_prereqs_per_intent": MAX_ADDED_PREREQS_PER_INTENT,
    }
    return {
        "schema": REFINEMENT_SCHEMA,
        "refinement_id": "refine_" + refinement_hash[:16],
        "refinement_hash": refinement_hash,
        "constellation_hash": getattr(constellation, "constellation_hash", "unknown"),
        "activation_packet_id": body["activation_packet_id"],
        "treatment_packet_hash": (activation or {}).get(
            "activation_lineage", {}).get("treatment_packet_hash", "unknown"),
        "recruited_region_ids": recruited,
        "context_region_ids": context,
        "archived_region_ids": archived,
        "unresolved_region_ids": unresolved,
        "coverage_gaps": body["coverage_gaps"],
        "new_prerequisite_requirements": body["new_prerequisite_requirements"],
        "planning_guidance": body["planning_guidance"],
        "non_executable_knowledge_used": non_executable_used,
        "disposition_digests": body["disposition_digests"],
        "lineage": body["lineage"],
    }


def apply_to_closure(refinement: dict[str, Any],
                     closure: dict[str, Any]) -> dict[str, Any]:
    """Add KA-2 entries into the two existing empty closure fields.

    Records the pre-refinement closure hash on
    `closure["lineage"]["ka2_pre_refinement_closure_hash"]`, appends
    refinement entries, recomputes `closure["packet_hash"]` over the
    post-fill body, and returns the closure. ALL other closure fields
    are preserved exactly.
    """
    updated = copy.deepcopy(closure)
    if "lineage" not in updated or not isinstance(updated["lineage"], dict):
        updated["lineage"] = {}
    pre_hash = updated.get("packet_hash", "")
    updated["lineage"]["ka2_pre_refinement_closure_hash"] = pre_hash
    updated["lineage"]["ka2_refinement_id"] = refinement.get("refinement_id", "unknown")
    updated["lineage"]["ka2_refinement_hash"] = refinement.get("refinement_hash", "unknown")
    updated["lineage"]["ka2_constellation_hash"] = refinement.get(
        "constellation_hash", "unknown")
    updated["lineage"]["ka2_max_prereq_depth"] = MAX_PREREQ_DEPTH
    updated["lineage"]["ka2_max_added_prereqs"] = MAX_ADDED_PREREQS_PER_INTENT

    existing_planning = list(updated.get("planning_guidance", []) or [])
    new_planning = list(refinement.get("planning_guidance", []) or [])
    for entry in new_planning:
        entry.setdefault("lineage", {})
        if isinstance(entry.get("lineage"), dict):
            entry["lineage"]["refinement_id"] = refinement.get("refinement_id", "unknown")
        existing_planning.append(entry)
    updated["planning_guidance"] = existing_planning

    existing_ne = list(updated.get("non_executable_knowledge_used", []) or [])
    new_ne = list(refinement.get("non_executable_knowledge_used", []) or [])
    for ne in new_ne:
        if ne not in existing_ne:
            existing_ne.append(ne)
    updated["non_executable_knowledge_used"] = existing_ne

    body = {k: v for k, v in updated.items() if k != "packet_hash"}
    updated["packet_hash"] = _sha(body)
    return updated
