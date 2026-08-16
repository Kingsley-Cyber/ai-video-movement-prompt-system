"""KA-2 WP-1 — ExpertiseRegion + KnowledgeConstellation assembly.

Builds deterministic expertise regions on top of a KA-1
`KnowledgeApplicationSet` (read-only consumer). Groups packs by structured
overlap of corpus vocabulary (canonical_concept_ids, trigger_ids,
objective_ids, failure_family_ids, requirement_ids, principle_family).
No prose similarity, no LLM. D4-clean (IDs only).

Pure functions of their inputs. Deterministic ordering by region_id.

FROZEN: do not mutate KA-1 outputs. The constellation reads the
`applications` list as-is; it does not touch the resolved score.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from lab.application.cpcs_deliberation import (
    NON_EXECUTABLE_AFFORDANCES,
    PLANNING_AFFORDANCES,
)

REGION_SCHEMA = "cpcs.expertise_region/0.1"
CONSTELLATION_SCHEMA = "cpcs.knowledge_constellation/0.1"

ORPHAN_REGION_ID = "region_orphan"

# ---------------------------------------------------------------------------
# KA-2.3 merge-policy snapshot (instrumentation; NOT a policy change)
# ---------------------------------------------------------------------------
# Strong facets are intra-region evidence: sharing them means the concepts
# jointly describe one expertise mechanism. Weak facets are inter-region
# bridge evidence: sharing them means the regions interact for this problem.
# The merge threshold and key classes below are the CURRENT policy (>= 2
# shared facets across all keys); instrumentation only RECORDS how the
# policy behaves per merge. Changing these constants is a policy change
# and belongs to KA-2.3 refinement work AFTER the pre-policy sweep.
STRONG_FACET_KEYS = ("canonical_concept_ids", "failure_family_ids",
                     "requirement_ids", "principle_families")
WEAK_FACET_KEYS = ("trigger_ids", "objective_ids", "corpus_doc_ids")
CLUSTER_MERGE_THRESHOLD = 2
MERGE_POLICY_SNAPSHOT = {
    "threshold": CLUSTER_MERGE_THRESHOLD,
    "strong_facet_keys": list(STRONG_FACET_KEYS),
    "weak_facet_keys": list(WEAK_FACET_KEYS),
    "instrumentation_version": "ka2.3-instrumentation-v1",
}


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _sorted(values: Any) -> list[str]:
    if not values:
        return []
    return sorted(set(str(v) for v in values if v))


def region_facets(pack: dict[str, Any], evidence_by_id: dict[str, dict[str, Any]]
                  | None = None) -> dict[str, list[str]]:
    """Return the structured facet set of one PrinciplePack dict.

    The facet set drives region membership. A pack with empty facets
    lands in the orphan region (never merged)."""
    evidence_by_id = evidence_by_id or {}
    evidence_ids = pack.get("evidence_ids", []) or []
    principle_family = pack.get("principle_family", "")
    intent_app = pack.get("intent_application", {}) or {}
    lineage = pack.get("lineage", {}) or {}
    trigger_ids: set[str] = set(intent_app.get("trigger_ids", []) or [])
    objective_ids: set[str] = set(intent_app.get("objective_ids", []) or [])
    requirement_ids: set[str] = set(lineage.get("requirement_ids", []) or [])
    failure_family_ids: set[str] = set()
    canonical_concept_ids: set[str] = set()
    corpus_doc_ids: set[str] = set()
    for eid in evidence_ids:
        ev = evidence_by_id.get(eid) or {}
        for ff in ev.get("failure_family_ids", []) or []:
            failure_family_ids.add(ff)
        for cc in ev.get("canonical_concept_ids", []) or []:
            canonical_concept_ids.add(cc)
        for t in ev.get("trigger_ids", []) or []:
            trigger_ids.add(t)
        for o in ev.get("objective_ids", []) or []:
            objective_ids.add(o)
        doc_id = ev.get("document_id")
        if doc_id:
            corpus_doc_ids.add(doc_id)
    facets = {
        "principle_families": [principle_family] if principle_family else [],
        "trigger_ids": _sorted(trigger_ids),
        "objective_ids": _sorted(objective_ids),
        "requirement_ids": _sorted(requirement_ids),
        "failure_family_ids": _sorted(failure_family_ids),
        "canonical_concept_ids": _sorted(canonical_concept_ids),
        "corpus_doc_ids": _sorted(corpus_doc_ids),
    }
    return facets


def _facet_overlap_count(a: dict[str, list[str]], b: dict[str, list[str]]) -> int:
    count = 0
    for key in ("trigger_ids", "objective_ids", "requirement_ids",
                "failure_family_ids", "canonical_concept_ids"):
        count += len(set(a.get(key, []) or []) & set(b.get(key, []) or []))
    if a.get("principle_families") and b.get("principle_families"):
        count += len(set(a["principle_families"]) & set(b["principle_families"]))
    return count


def _is_empty_facet(facets: dict[str, list[str]]) -> bool:
    return all(not v for v in facets.values())


@dataclass
class ExpertiseRegion:
    region_id: str
    region_hash: str
    pack_ids: list[str]
    evidence_ids: list[str]
    canonical_concept_ids: list[str]
    trigger_ids: list[str]
    objective_ids: list[str]
    failure_family_ids: list[str]
    requirement_ids: list[str]
    principle_families: list[str]
    corpus_doc_ids: list[str] = field(default_factory=list)
    representation_mix: dict[str, int] = field(default_factory=dict)
    intent_signal_coverage: dict[str, list[str]] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    competition_refs: list[str] = field(default_factory=list)
    lineage: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": REGION_SCHEMA,
            "region_id": self.region_id,
            "region_hash": self.region_hash,
            "pack_ids": self.pack_ids,
            "evidence_ids": self.evidence_ids,
            "canonical_concept_ids": self.canonical_concept_ids,
            "trigger_ids": self.trigger_ids,
            "objective_ids": self.objective_ids,
            "failure_family_ids": self.failure_family_ids,
            "requirement_ids": self.requirement_ids,
            "principle_families": self.principle_families,
            "corpus_doc_ids": self.corpus_doc_ids,
            "representation_mix": self.representation_mix,
            "intent_signal_coverage": self.intent_signal_coverage,
            "dependencies": self.dependencies,
            "competition_refs": self.competition_refs,
            "lineage": self.lineage,
            "diagnostics": self.diagnostics,
        }


@dataclass
class KnowledgeConstellation:
    constellation_id: str
    constellation_hash: str
    regions: list[dict[str, Any]]
    region_dependency_edges: list[dict[str, str]]
    lineage: dict[str, Any]
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CONSTELLATION_SCHEMA,
            "constellation_id": self.constellation_id,
            "constellation_hash": self.constellation_hash,
            "regions": self.regions,
            "region_dependency_edges": self.region_dependency_edges,
            "lineage": self.lineage,
            "diagnostics": self.diagnostics,
        }


def _facet_overlap_breakdown(a: dict[str, list[str]],
                             b: dict[str, list[str]]) -> dict[str, Any]:
    overlap: dict[str, int] = {}
    strong = 0
    weak = 0
    for key in STRONG_FACET_KEYS + WEAK_FACET_KEYS:
        count = len(set(a.get(key, []) or []) & set(b.get(key, []) or []))
        overlap[key] = count
        if key in STRONG_FACET_KEYS:
            strong += count
        else:
            weak += count
    return {
        "overlap_by_facet": overlap,
        "strong_overlap": strong,
        "weak_overlap": weak,
    }


def _build_region(
    region_id: str,
    packs: list[dict[str, Any]],
    decisions: list[str],
    facets_union: dict[str, list[str]],
    lineage: dict[str, Any],
    diagnostics: dict[str, Any] | None = None,
) -> ExpertiseRegion:
    body = {
        "region_id": region_id,
        "pack_ids": _sorted([p["pack_id"] for p in packs]),
        "evidence_ids": _sorted({eid for p in packs
                                 for eid in (p.get("evidence_ids") or [])}),
        "facets": facets_union,
        "decisions": sorted(set(decisions)),
    }
    region_hash = _sha(body)
    return ExpertiseRegion(
        region_id=region_id,
        region_hash=region_hash,
        pack_ids=body["pack_ids"],
        evidence_ids=body["evidence_ids"],
        canonical_concept_ids=facets_union.get("canonical_concept_ids", []),
        trigger_ids=facets_union.get("trigger_ids", []),
        objective_ids=facets_union.get("objective_ids", []),
        failure_family_ids=facets_union.get("failure_family_ids", []),
        requirement_ids=facets_union.get("requirement_ids", []),
        principle_families=facets_union.get("principle_families", []),
        corpus_doc_ids=facets_union.get("corpus_doc_ids", []),
        representation_mix={
            d: sum(1 for x in decisions if x == d) for d in sorted(set(decisions))
        },
        intent_signal_coverage={},
        lineage=lineage,
        diagnostics=diagnostics or {},
    )


def _union_facets(parts: list[dict[str, list[str]]]) -> dict[str, list[str]]:
    out: dict[str, set[str]] = {
        "principle_families": set(),
        "trigger_ids": set(),
        "objective_ids": set(),
        "requirement_ids": set(),
        "failure_family_ids": set(),
        "canonical_concept_ids": set(),
        "corpus_doc_ids": set(),
    }
    for p in parts:
        for k in out:
            for v in p.get(k, []) or []:
                out[k].add(v)
    return {k: sorted(v) for k, v in out.items()}


def _competition_refs(packs_with_decisions: list[tuple[dict[str, Any], str]]
                       ) -> list[str]:
    refs: list[str] = []
    for pack, _ in packs_with_decisions:
        group = (pack.get("lineage") or {}).get("competition_group")
        if group and group not in refs:
            refs.append(group)
    return refs


def _affordance_evidence(
    pack: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
) -> set[str]:
    universal_types: set[str] = set()
    for rec in pack.get("source_records", []) or []:
        ut = rec.get("universal_type")
        if ut:
            universal_types.add(ut)
    affs: set[str] = set()
    for ut in universal_types:
        affs |= set(NON_EXECUTABLE_AFFORDANCES.get(ut, []) or [])
        affs |= set(PLANNING_AFFORDANCES.get(ut, []) or [])
    return affs


def assemble_constellation(
    application_set: Any,
    activation: dict[str, Any],
    *,
    evidence_by_id: dict[str, dict[str, Any]] | None = None,
) -> KnowledgeConstellation:
    """Group KA-1 `KnowledgeApplicationSet.applications` packs into regions.

    Reads `application_set.applications` (a list of dicts each with `pack`
    and `decision` keys, plus optional `competition_group`). Pure.
    """
    evidence_by_id = evidence_by_id or {}
    if isinstance(application_set, dict):
        applications = list(application_set.get("applications", []) or [])
    else:
        applications = list(getattr(application_set, "applications", []) or [])
    if applications and isinstance(applications[0], dict) and "pack" in applications[0]:
        packs_decisions = [
            (entry["pack"], entry["decision"]["decision"],
             entry.get("competition_group"))
            for entry in applications
        ]
    else:
        packs_decisions = [
            (entry.get("pack", entry),
             (entry.get("decision") or {}).get("decision", "CONTROL"),
             entry.get("competition_group"))
            for entry in applications
        ]
    facets_per_pack: list[dict[str, list[str]]] = []
    for pack, _decision, _grp in packs_decisions:
        facets_per_pack.append(region_facets(pack, evidence_by_id))

    clusters: list[list[int]] = []
    merge_log: list[tuple[int, int, dict[str, Any]]] = []
    for i, fi in enumerate(facets_per_pack):
        if _is_empty_facet(fi):
            clusters.append([i])
            continue
        placed = False
        for cluster in clusters:
            j = cluster[0]
            if _is_empty_facet(facets_per_pack[j]):
                continue
            # Merge threshold >= 2 prevents single-linkage chaining from
            # collapsing the constellation into mega-regions through one
            # shared vocabulary token.
            if _facet_overlap_count(fi, facets_per_pack[j]) >= 2:
                cluster.append(i)
                placed = True
                merge_log.append(
                    (i, j, _facet_overlap_breakdown(fi, facets_per_pack[j])))
                break
        if not placed:
            clusters.append([i])

    regions: list[ExpertiseRegion] = []
    for cluster in clusters:
        if len(cluster) == 1 and _is_empty_facet(facets_per_pack[cluster[0]]):
            region_id = ORPHAN_REGION_ID
            is_orphan = True
        elif len(cluster) == 1:
            pack = packs_decisions[cluster[0]][0]
            region_id = "region_" + _sha(pack["pack_id"])[:16]
            is_orphan = False
        else:
            region_id = "region_" + _sha(
                "|".join(sorted(packs_decisions[i][0]["pack_id"] for i in cluster))
            )[:16]
            is_orphan = False
        cluster_packs = [packs_decisions[i][0] for i in cluster]
        cluster_decisions = [packs_decisions[i][1] for i in cluster]
        cluster_facets = _union_facets([facets_per_pack[i] for i in cluster])
        comp_refs = _competition_refs(
            list(zip(cluster_packs, cluster_decisions)))
        seed_index = cluster[0]
        seed_pack_id = cluster_packs[0]["pack_id"]
        evidence = []
        for joined, joined_to, breakdown in merge_log:
            if joined_to != seed_index:
                continue
            evidence.append({
                "role": "joined",
                "joined_pack_id": packs_decisions[joined][0]["pack_id"],
                "joined_to_pack_ids": [seed_pack_id],
                **breakdown,
            })
        strong_total = sum(e["strong_overlap"] for e in evidence)
        weak_total = sum(e["weak_overlap"] for e in evidence)
        diagnostics = {
            "merge_policy": dict(MERGE_POLICY_SNAPSHOT),
            "orphan": is_orphan,
            "seed_pack_id": seed_pack_id if len(cluster) > 1 else None,
            "merge_evidence": sorted(
                evidence, key=lambda e: e["joined_pack_id"]),
            "strength_breakdown": {
                "strong_overlap_total": strong_total,
                "weak_overlap_total": weak_total,
                "joins": len(evidence),
            },
        }
        region = _build_region(
            region_id=region_id,
            packs=cluster_packs,
            decisions=cluster_decisions,
            facets_union=cluster_facets,
            lineage={
                "activation_packet_id": (activation or {}).get("packet_id", "unknown"),
                "pack_count": len(cluster),
                "competition_refs": comp_refs,
            },
            diagnostics=diagnostics,
        )
        regions.append(region)

    regions.sort(key=lambda r: r.region_id)

    edges: list[dict[str, str]] = []
    for i, ri in enumerate(regions):
        for j, rj in enumerate(regions):
            if i >= j:
                continue
            if (ri.requirement_ids and rj.requirement_ids
                    and set(ri.requirement_ids) & set(rj.requirement_ids)):
                edges.append({"from": ri.region_id, "to": rj.region_id,
                              "kind": "shared_requirement",
                              "strength": "strong"})
                continue
            if (ri.failure_family_ids and rj.failure_family_ids
                    and set(ri.failure_family_ids) & set(rj.failure_family_ids)):
                edges.append({"from": ri.region_id, "to": rj.region_id,
                              "kind": "shared_failure_family",
                              "strength": "strong"})
                continue
            if (ri.canonical_concept_ids and rj.canonical_concept_ids
                    and set(ri.canonical_concept_ids)
                    & set(rj.canonical_concept_ids)):
                edges.append({"from": ri.region_id, "to": rj.region_id,
                              "kind": "shared_canonical_concept",
                              "strength": "strong"})
                continue
            if (ri.corpus_doc_ids and rj.corpus_doc_ids
                    and set(ri.corpus_doc_ids) & set(rj.corpus_doc_ids)):
                edges.append({"from": ri.region_id, "to": rj.region_id,
                              "kind": "shared_document",
                              "strength": "weak"})
                continue
            if (ri.objective_ids and rj.objective_ids
                    and set(ri.objective_ids) & set(rj.objective_ids)):
                edges.append({"from": ri.region_id, "to": rj.region_id,
                              "kind": "shared_objective",
                              "strength": "weak"})
                continue
            if (ri.trigger_ids and rj.trigger_ids
                    and set(ri.trigger_ids) & set(rj.trigger_ids)):
                edges.append({"from": ri.region_id, "to": rj.region_id,
                              "kind": "shared_trigger",
                              "strength": "weak"})

    constellation_id = "constellation_" + _sha(
        (activation or {}).get("packet_hash", "unknown")
        + "|" + "|".join(r.region_id for r in regions)
    )[:16]
    # Policy-neutrality: constellation_hash covers the same semantic core
    # as before instrumentation (regions minus diagnostics, edges minus
    # the additive strength key), so all downstream hashes stay stable.
    hash_regions = [
        {k: v for k, v in r.to_dict().items() if k != "diagnostics"}
        for r in regions
    ]
    hash_edges = [{"from": e["from"], "to": e["to"], "kind": e["kind"]}
                  for e in edges]
    body = {
        "regions": hash_regions,
        "edges": sorted(hash_edges, key=lambda e: (e["from"], e["to"], e["kind"])),
        "activation_packet_id": (activation or {}).get("packet_id", "unknown"),
    }
    constellation_hash = _sha(body)
    diagnostics = {
        "merge_policy_snapshot": dict(MERGE_POLICY_SNAPSHOT),
        "region_diagnostics": {
            r["region_id"]: r["diagnostics"]
            for r in [x.to_dict() for x in regions]
        },
        "bridges": sorted(edges, key=lambda e: (e["from"], e["to"], e["kind"])),
        "bridge_counts": {
            "strong": sum(1 for e in edges if e.get("strength") == "strong"),
            "weak": sum(1 for e in edges if e.get("strength") == "weak"),
        },
    }
    return KnowledgeConstellation(
        constellation_id=constellation_id,
        constellation_hash=constellation_hash,
        regions=[r.to_dict() for r in regions],
        region_dependency_edges=sorted(
            edges, key=lambda e: (e["from"], e["to"], e["kind"])),
        lineage={
            "activation_packet_id": body["activation_packet_id"],
            "region_count": len(regions),
            "edge_count": len(edges),
            "pack_count": sum(len(r["pack_ids"]) for r in body["regions"]),
            "merge_policy_snapshot": dict(MERGE_POLICY_SNAPSHOT),
        },
        diagnostics=diagnostics,
    )
