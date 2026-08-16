"""KA-2.3 semantic region-quality audit (real frozen runtime).

Runs FIGHT / UGC_SERUM / DRONE through the full pipeline under the v3
document-seeded separation policy and records, per region: member count,
principle families, mechanism tokens, canonical concepts, source
documents, failure families, placement roles, and strongest bridge
relationships. Region count alone is not the target — semantic coherence
is. Writes the audit artifact (content-hashed); --artifact-name selects
the post-KA1.1 variant.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from lab.compiler.profiles import REPO_ROOT

OUT = Path(__file__).resolve().parent
ARTIFACT = OUT / "KA2_3_REGION_QUALITY_AUDIT_v0.1.json"

AUDIT_INTENTS: dict[str, str] = {
    "FIGHT": ("A fighter catches an opponent's leg, swings him in a wide "
              "arc, releases him onto the water, then immediately pressures "
              "him while he tries to recover."),
    "UGC_SERUM": ("A woman records a casual handheld creator video trying a "
                  "premium facial serum. She picks the bottle up from the "
                  "bathroom counter, turns it so the label is visible, "
                  "unscrews the dropper, dispenses two drops on the back of "
                  "her other hand, rubs the serum between her fingers, "
                  "applies it to her cheek, notices the texture, reacts "
                  "positively, talks naturally to the viewer, then brings "
                  "the bottle near the phone camera for the final product "
                  "shot."),
    "DRONE": ("A drone camera orbits a coastal cliff with no performer "
              "visible."),
}


def _mechanism_tokens(pack: dict[str, Any]) -> list[str]:
    mechanism = (pack.get("mechanism") or "").removeprefix("mechanism: ")
    return sorted({t.strip() for t in mechanism.split(",")
                   if t.strip() and t.strip() != "none"})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-name", default=None)
    args = parser.parse_args()
    target = OUT / args.artifact_name if args.artifact_name else ARTIFACT
    sys.path.insert(0, str(REPO_ROOT))
    from lab.application.cpcs_deliberation import (
        frozen_knowledge_snapshot,
        DeliberationEngine,
    )
    from lab.application.cpcs_knowledge_application import apply_knowledge
    from lab.application.cpcs_knowledge_awareness import build_awareness_profile
    from lab.application.cpcs_knowledge_constellation import assemble_constellation
    from lab.application.cpcs_knowledge_placement import (
        build_placement,
        decompose_atomic_units,
    )
    from lab.application.cpcs_knowledge_recruitment import recruit_for_intent
    from lab.application.reasoning_treatment import (
        FrozenRuntimeBackend,
        TreatmentAdapter,
    )

    snapshot = frozen_knowledge_snapshot()
    backend = FrozenRuntimeBackend()
    results: dict[str, Any] = {}
    for name, intent in AUDIT_INTENTS.items():
        engine = DeliberationEngine(snapshot, backend)
        activation, packet = engine.activate(
            intent, {"intent": {"primary_domain": "action"}},
            observations=[])
        awareness = build_awareness_profile(intent, activation=activation)
        translation = TreatmentAdapter(REPO_ROOT).translate(
            packet, snapshot=snapshot, activation=activation)
        app_set = translation.application_set or {}
        applications = app_set.get("applications", []) if isinstance(
            app_set, dict) else getattr(app_set, "applications", [])
        evidence_by_id = {ev["atomic_record_id"]: ev
                          for ev in packet.get("retrieved_evidence", []) or []
                          if ev.get("atomic_record_id")}
        constellation = assemble_constellation(
            app_set, activation, evidence_by_id=evidence_by_id)
        pack_lookup = {e["pack"]["pack_id"]: e["pack"]
                       for e in applications}
        recruitment = recruit_for_intent(
            constellation, activation, pack_lookup=pack_lookup,
            awareness=awareness.to_dict())
        units = decompose_atomic_units(translation.structured_objects)
        placement = build_placement(recruitment, constellation, units,
                                    pack_lookup=pack_lookup)
        role_by_region = {p.region_id: p.placement_role for p in placement}
        disposition_by_region = {p.region_id: p.disposition for p in placement}
        bridges = constellation.diagnostics.get("bridges", []) or []
        bridge_map: dict[str, list[dict[str, Any]]] = {}
        for bridge in bridges:
            bridge_map.setdefault(bridge["from"], []).append(bridge)
            bridge_map.setdefault(bridge["to"], []).append(bridge)
        regions: list[dict[str, Any]] = []
        for region in constellation.regions:
            mechanisms: list[str] = []
            for pid in region.get("pack_ids", []) or []:
                pack = pack_lookup.get(pid) or {}
                mechanisms.extend(_mechanism_tokens(pack))
            related = bridge_map.get(region["region_id"], [])
            strongest = sorted(
                related,
                key=lambda b: (0 if b["strength"] == "strong" else 1,
                               b["kind"]))[:6]
            regions.append({
                "region_id": region["region_id"],
                "member_count": len(region.get("pack_ids", []) or []),
                "principle_families": region.get("principle_families", []),
                "mechanism_tokens": sorted(set(mechanisms)),
                "canonical_concepts": region.get("canonical_concept_ids", []),
                "source_documents": region.get("corpus_doc_ids", []),
                "failure_families": region.get("failure_family_ids", []),
                "placement_role": role_by_region.get(region["region_id"]),
                "disposition": disposition_by_region.get(region["region_id"]),
                "cross_seed_merges": region.get("diagnostics", {}).get(
                    "strength_breakdown", {}).get("cross_seed_merges", 0),
                "strongest_bridges": [
                    {"to": b["to"] if b["from"] == region["region_id"]
                     else b["from"], "kind": b["kind"],
                     "strength": b["strength"]}
                    for b in strongest
                ],
            })
        results[name] = {
            "intent": intent,
            "workflow_tags": [t["tag"] for t in awareness.active_workflow_tags],
            "candidate_expertise_tags": [t["tag"] for t in
                                         awareness.candidate_expertise_tags],
            "principle_packs": len(applications),
            "region_count": len(regions),
            "regions": sorted(regions, key=lambda r: -r["member_count"]),
            "bridge_count": len(bridges),
            "recruitment_counts": {
                d: sum(1 for p in placement if p.disposition == d)
                for d in ("RECRUIT", "CONTEXT", "ARCHIVE", "UNRESOLVED")},
        }
    body = {"workflows": results}
    content_hash = hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
        capture_output=True, text=True, check=True).stdout.strip()
    artifact = {
        "artifact": "CPCS_KA2_3_REGION_QUALITY_AUDIT",
        "version": "v0.1",
        "policy": "ka2.3-document-seeded-separation",
        "ka1_1_family_vocabulary": True,
        "git_commit": commit,
        "content_hash": content_hash,
        **body,
    }
    target.write_text(json.dumps(artifact, indent=1) + "\n")
    print(f"wrote {target}")
    print(json.dumps({
        name: {
            "regions": fx["region_count"],
            "sizes": [r["member_count"] for r in fx["regions"]][:10],
            "recruitment": fx["recruitment_counts"],
        } for name, fx in results.items()
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
