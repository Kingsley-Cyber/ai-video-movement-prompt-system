#!/usr/bin/env python3
"""Derive lab/graph.json from the structured sources of truth. NEVER hand-edit graph.json.

Sources: concepts.jsonl (cards, pairs/conflicts/layer/source), blocks.yaml, registry.yaml
(patterns/variants/runs/experiments/runbooks). Deterministic output (sorted) so freshness is
checkable by exact rebuild (sync_repo.py). Run: python3 lab/scripts/build_graph.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

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
    nodes: dict[str, dict] = {}
    edges: set[tuple[str, str, str]] = set()

    def node(nid: str, ntype: str, **attrs):
        if nid not in nodes:
            nodes[nid] = {"id": nid, "type": ntype, **attrs}
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
        for p in c.get("pairs_with", []):
            edges.add((c["id"], p, "pairs"))
        for p in c.get("conflicts", []):
            edges.add((c["id"], p, "conflicts"))
        for ev in c.get("evidence", []):
            edges.add((c["id"], f"ev:{ev}", "evidenced_by"))
            node(f"ev:{ev}", "evidence")
        paper_edges(c["id"], c.get("source", []))

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

    return {
        "note": "DERIVED FILE — regenerate with lab/scripts/build_graph.py; never hand-edit",
        "nodes": sorted(nodes.values(), key=lambda n: n["id"]),
        "edges": sorted({"s": s, "t": t, "type": ty} for s, t, ty in resolved_edges
                        if s in nodes and t in nodes) if False else
                 sorted(({"s": s, "t": t, "type": ty} for s, t, ty in resolved_edges
                         if s in nodes and t in nodes), key=lambda e: (e["s"], e["t"], e["type"])),
    }


def main() -> None:
    root = find_root()
    g = build(root)
    out = root / "lab" / "graph.json"
    out.write_text(json.dumps(g, indent=1, sort_keys=True) + "\n")
    print(f"graph.json: {len(g['nodes'])} nodes, {len(g['edges'])} edges")


if __name__ == "__main__":
    main()
