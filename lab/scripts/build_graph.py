#!/usr/bin/env python3
"""Derive lab/graph.json from the structured sources of truth. NEVER hand-edit graph.json.

Sources: concepts.jsonl (cards/layer/source), second-brain authored edges, rules, intents, mappings,
claims, equations, methods, mechanisms,
immutable evidence, learned weights, blocks.yaml, and registry.yaml (patterns, variants, legacy
runs, experiments, runbooks). Deterministic output makes freshness checkable by exact rebuild.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

REPO_IMPORT_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_IMPORT_ROOT))

from lab.second_brain.src.temporal import is_visible

# research-package aliases: how card `source` strings refer to each package in research/.
# ON INGEST of a new package: add its alias here (sync_repo enforces coverage).
PAPER_ALIASES = {
    "CPCS_FACS_Laban_AI_Video_Research_Package_v1.2": ["CPCS §", "CPCS_FACS_Laban"],
    "Pegasus_Atomic_Video_Deconstruction_and_Modular_AI_Recreation_v1.0.md": ["RDC §", "Pegasus_Atomic"],
    "CPCS_MX_Hierarchical_Motion_Grammar_Research_Package_v1.0": ["MX §", "MX Appendix", "CPCS_MX_"],
}


def find_root() -> Path:
    for cand in [Path.cwd(), *Path.cwd().parents]:
        if (cand / "lab" / "registry.yaml").exists():
            return cand
    sys.exit("error: run from inside the repo")


def build(root: Path) -> dict:
    import yaml
    lab = root / "lab"
    second_brain = lab / "second_brain"
    nodes: dict[str, dict] = {}
    edges: set[tuple[str, str, str]] = set()
    tiered_edges: list[dict] = []

    def node(nid: str, ntype: str, **attrs):
        if nid not in nodes:
            nodes[nid] = {"id": nid, "type": ntype, **attrs}
        else:
            nodes[nid].update(attrs)
        return nid

    # paper nodes from research/ dir (so ADD/REMOVE of a package changes the graph)
    research = root / "research"
    for entry in sorted(p.name for p in research.iterdir()) if research.exists() else []:
        node(f"paper:{entry}", "paper")

    def paper_edges(src_id: str, sources: list[str]):
        for s in sources:
            for pkg, aliases in PAPER_ALIASES.items():
                if any(a in s for a in aliases) or pkg in s:
                    if f"paper:{pkg}" in nodes:
                        edges.add((src_id, f"paper:{pkg}", "sourced_from"))

    # concept cards
    for line in (lab / "concepts.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        c = json.loads(line)
        node(c["id"], "concept", kind=c["kind"], layer=c["layer"], status=c["status"], name=c["name"])
        node(f"layer:{c['layer']}", "layer")
        edges.add((c["id"], f"layer:{c['layer']}", "in_layer"))
        for ev in c.get("evidence", []):
            edges.add((c["id"], f"ev:{ev}", "evidenced_by"))
            node(f"ev:{ev}", "evidence")
        paper_edges(c["id"], c.get("source", []))

    # second-brain curated records
    edge_path = second_brain / "curated" / "edges.jsonl"
    if edge_path.exists():
        for line in edge_path.read_text().splitlines():
            if not line.strip():
                continue
            edge = json.loads(line)
            if not is_visible(edge):
                continue
            tiered_edges.append({
                "id": edge["id"], "s": edge["u"], "t": edge["v"], "type": edge["type"],
                "tier": "curated", "rebuildable": False, "context": edge["context"],
            })
    for store, ntype in (("intents", "intent"), ("rules", "rule"), ("mappings", "mapping")):
        path = second_brain / "curated" / f"{store}.jsonl"
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            node(record["id"], ntype, tier="curated")
            if store == "intents":
                node(f"intent_class:{record['intent_class']}", "intent_class")
                tiered_edges.append({
                    "s": record["id"], "t": f"intent_class:{record['intent_class']}",
                    "type": "normalizes", "tier": "curated", "rebuildable": False,
                })
            elif store == "rules":
                concept_id = record.get("trigger", {}).get("concept_id")
                if concept_id in nodes:
                    tiered_edges.append({
                        "s": concept_id, "t": record["id"], "type": "governed_by",
                        "tier": "curated", "rebuildable": False,
                    })
            else:
                concept_id = record["concept_id"]
                control_id = f"control:{record['target_id']}"
                node(control_id, "control", encoding=record["encoding"])
                tiered_edges.extend([
                    {
                        "s": concept_id, "t": record["id"], "type": "has_mapping",
                        "tier": "curated", "rebuildable": False,
                    },
                    {
                        "s": record["id"], "t": control_id, "type": "maps_to",
                        "tier": "curated", "rebuildable": False,
                    },
                ])
    for store, ntype in (
        ("claims", "claim"),
        ("equations", "equation"),
        ("methods", "method"),
        ("mechanisms", "mechanism"),
    ):
        path = second_brain / "curated" / f"{store}.jsonl"
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if not is_visible(record):
                continue
            node(record["id"], ntype, tier="curated")
            for concept_id in record["concept_ids"]:
                if concept_id in nodes:
                    tiered_edges.append({
                        "s": concept_id,
                        "t": record["id"],
                        "type": f"has_{ntype}",
                        "tier": "curated",
                        "rebuildable": False,
                    })
            reference_fields = {
                "claim": (
                    ("method_ids", "uses_method"),
                    ("supports_claim_ids", "supports_claim"),
                    ("contradicts_claim_ids", "contradicts_claim"),
                ),
                "equation": (
                    ("method_ids", "used_by_method"),
                    ("mechanism_ids", "quantifies_mechanism"),
                ),
                "method": (
                    ("equation_ids", "uses_equation"),
                    ("mechanism_ids", "applies_mechanism"),
                ),
                "mechanism": (
                    ("claim_ids", "supported_by_claim"),
                    ("method_ids", "implemented_by_method"),
                    ("equation_ids", "quantified_by_equation"),
                ),
            }[ntype]
            for field, edge_type in reference_fields:
                for target_id in record.get(field, []):
                    tiered_edges.append({
                        "s": record["id"],
                        "t": target_id,
                        "type": edge_type,
                        "tier": "curated",
                        "rebuildable": False,
                    })
            control_ids = []
            if ntype == "equation":
                control_ids.extend(
                    row["control_id"]
                    for row in record.get("operational_mappings", [])
                )
            if ntype == "mechanism":
                control_ids.extend(record.get("controls", []))
            for control_id in sorted(set(control_ids)):
                control_node = f"control:{control_id}"
                node(control_node, "control")
                tiered_edges.append({
                    "s": record["id"],
                    "t": control_node,
                    "type": "maps_to_control",
                    "tier": "curated",
                    "rebuildable": False,
                })

    # blocks
    blocks = yaml.safe_load((lab / "blocks.yaml").read_text()) or {}
    for b in blocks.get("blocks", []):
        node(b["id"], "block", layer=b.get("layer", ""), status=b.get("status", ""))
        for cf in b.get("conflicts_with", []) or []:
            edges.add((b["id"], cf, "conflicts"))
        for ev in b.get("evidence", []) or []:
            node(f"ev:{ev}", "evidence")
            edges.add((b["id"], f"ev:{ev}", "evidenced_by"))

    # registry: patterns, variants, experiments, runbooks
    reg = yaml.safe_load((lab / "registry.yaml").read_text()) or {}
    for p in reg.get("patterns", []):
        node(p["id"], "pattern", confidence=p.get("confidence", ""))
        for ev in p.get("evidence", []) or []:
            node(f"ev:{ev}", "evidence")
            edges.add((p["id"], f"ev:{ev}", "evidenced_by"))
    for v in reg.get("variants", []):
        node(v["id"], "variant", format=v.get("format", ""))
    for e in reg.get("experiments", []):
        node(e["id"], "experiment", status=e.get("status", ""))
        if e.get("promotes"):
            tgt = next((p["id"] for p in reg.get("patterns", []) if p["id"].startswith(e["promotes"])), e["promotes"])
            edges.add((e["id"], tgt, "promotes"))
    for name, rel in (reg.get("runbooks") or {}).items():
        node(f"runbook:{name}", "runbook", path=rel)
    # runs
    for row in csv.DictReader((lab / "runs" / "results.csv").open()):
        node(f"run:{row['run_id']}", "run", verdict=row.get("verdict", ""))
        edges.add((f"run:{row['run_id']}", row["variant_id"], "ran_variant"))

    # immutable second-brain evidence and sealed flights
    immutable = second_brain / "immutable"
    flights_path = immutable / "flights.jsonl"
    if flights_path.exists():
        for line in flights_path.read_text().splitlines():
            if not line.strip():
                continue
            flight = json.loads(line)
            node(flight["id"], "flight", tier="immutable", append_only=True)
    for store in ("runs", "pegasus_observations", "measurement_observations"):
        path = immutable / f"{store}.jsonl"
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            evidence_id = f"run:{record['id']}" if store == "runs" else record["id"]
            node(evidence_id, "run" if store == "runs" else "observation",
                 tier="immutable", append_only=True, evidence_store=store)
            if store == "runs" and record.get("capture_kind") != "manual_render":
                tiered_edges.append({
                    "s": evidence_id, "t": record["flight_id"], "type": "part_of_flight",
                    "tier": "immutable", "append_only": True,
                })
            concept_ids = list(record.get("concept_ids", [])) + list(record.get("candidate_concepts", []))
            for concept_id in sorted(set(concept_ids)):
                if concept_id in nodes:
                    tiered_edges.append({
                        "s": concept_id, "t": evidence_id, "type": "evidenced_by",
                        "tier": "immutable", "append_only": True,
                    })

    # disposable learned relationships
    weights_path = second_brain / "derived" / "weights.json"
    if weights_path.exists():
        for edge in json.loads(weights_path.read_text()).get("edges", []):
            if edge["u"] in nodes and edge["v"] in nodes:
                tiered_edges.append({
                    "id": edge["id"], "s": edge["u"], "t": edge["v"], "type": edge["type"],
                    "tier": "derived", "rebuildable": True, "weight": edge["weight"],
                    "evidence": edge["evidence"], "model_version": edge["model_version"],
                    "context": edge["context"],
                })

    # resolve evidence ids to their real nodes when present (r### -> run:r###, p### -> pattern)
    resolved_edges = set()
    all_ids = set(nodes)
    for s, t, ty in edges:
        if t.startswith("ev:"):
            raw = t[3:]
            real = None
            if f"run:{raw}" in all_ids:
                real = f"run:{raw}"
            else:
                real = next((i for i in all_ids if i.startswith(raw) and nodes[i]["type"] in ("pattern", "experiment", "variant")), None)
            if real:
                resolved_edges.add((s, real, ty))
                continue
        resolved_edges.add((s, t, ty))
    # drop unresolved ev: placeholder nodes that no longer have edges
    used = {s for s, _, _ in resolved_edges} | {t for _, t, _ in resolved_edges}
    nodes = {k: v for k, v in nodes.items() if not (k.startswith("ev:") and k not in used)}

    output_edges = [
        {"s": s, "t": t, "type": ty}
        for s, t, ty in resolved_edges
        if s in nodes and t in nodes
    ]
    output_edges.extend(
        edge for edge in tiered_edges if edge["s"] in nodes and edge["t"] in nodes
    )
    return {
        "note": "DERIVED FILE — regenerate with lab/scripts/build_graph.py; never hand-edit",
        "nodes": sorted(nodes.values(), key=lambda n: n["id"]),
        "edges": sorted(
            output_edges,
            key=lambda e: (e["s"], e["t"], e["type"], e.get("id", ""), e.get("tier", "")),
        ),
    }


def main() -> None:
    root = find_root()
    g = build(root)
    out = root / "lab" / "graph.json"
    out.write_text(json.dumps(g, indent=1, sort_keys=True) + "\n")
    print(f"graph.json: {len(g['nodes'])} nodes, {len(g['edges'])} edges")


if __name__ == "__main__":
    main()
