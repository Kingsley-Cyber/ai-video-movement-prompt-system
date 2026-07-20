#!/usr/bin/env python3
"""Traverse lab/graph.json for creative composition and compilation paths.

    python3 lab/scripts/graph.py stats
    python3 lab/scripts/graph.py neighbors c_kinematic_truth -d 2
    python3 lab/scripts/graph.py path c_tempo_curve paper:CPCS_MX_Hierarchical_Motion_Grammar_Research_Package_v1.0
    python3 lab/scripts/graph.py clusters
    python3 lab/scripts/graph.py walk c_kinematic_truth --steps 6 --seed 7   # deterministic creative walk

Graph is DERIVED (build_graph.py). If stale, sync_repo.py fails the gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path


def load():
    for cand in [Path.cwd(), *Path.cwd().parents]:
        p = cand / "lab" / "graph.json"
        if p.exists():
            g = json.loads(p.read_text())
            adj = defaultdict(list)
            for e in g["edges"]:
                adj[e["s"]].append((e["t"], e["type"]))
                adj[e["t"]].append((e["s"], e["type"]))  # undirected traversal
            return {n["id"]: n for n in g["nodes"]}, adj
    sys.exit("error: lab/graph.json not found — run build_graph.py")


def fmt(nodes, nid):
    n = nodes.get(nid, {})
    extra = n.get("name") or n.get("path") or ""
    return f"{nid} [{n.get('type','?')}]" + (f" — {extra}" if extra else "")


def cmd_stats(nodes, adj, _a):
    from collections import Counter
    print(f"{len(nodes)} nodes")
    for t, c in Counter(n["type"] for n in nodes.values()).most_common():
        print(f"  {t}: {c}")
    print(f"{sum(len(v) for v in adj.values())//2} edges")
    deg = sorted(nodes, key=lambda n: -len(adj[n]))[:5]
    print("hubs:", ", ".join(f"{d}({len(adj[d])})" for d in deg))


def cmd_neighbors(nodes, adj, a):
    if a.node not in nodes:
        sys.exit(f"unknown node {a.node}")
    seen, frontier = {a.node}, [a.node]
    for depth in range(1, a.d + 1):
        nxt = []
        print(f"— depth {depth} —")
        for f in frontier:
            for t, ty in sorted(adj[f]):
                if t not in seen:
                    seen.add(t)
                    nxt.append(t)
                    print(f"  {fmt(nodes, t)}  (via {ty} from {f})")
        frontier = nxt


def cmd_path(nodes, adj, a):
    if a.src not in nodes or a.dst not in nodes:
        sys.exit("unknown endpoint")
    prev = {a.src: None}
    q = deque([a.src])
    while q:
        cur = q.popleft()
        if cur == a.dst:
            break
        for t, ty in adj[cur]:
            if t not in prev:
                prev[t] = (cur, ty)
                q.append(t)
    if a.dst not in prev:
        print("no path")
        return
    path, cur = [], a.dst
    while cur is not None:
        entry = prev[cur]
        path.append((cur, entry[1] if entry else None))
        cur = entry[0] if entry else None
    for nid, ty in reversed(path):
        arrow = f"  --{ty}-->  " if ty else ""
        print(f"{arrow}{fmt(nodes, nid)}")


def cmd_clusters(nodes, adj, _a):
    # connected components over pairs edges among concepts = the "cuisines"
    concept = {n for n, d in nodes.items() if d["type"] == "concept"}
    seen, comps = set(), []
    for start in sorted(concept):
        if start in seen:
            continue
        comp, q = [], deque([start])
        seen.add(start)
        while q:
            cur = q.popleft()
            comp.append(cur)
            for t, ty in adj[cur]:
                if ty == "pairs" and t in concept and t not in seen:
                    seen.add(t)
                    q.append(t)
        comps.append(comp)
    for comp in sorted(comps, key=len, reverse=True)[:8]:
        layers = defaultdict(int)
        for c in comp:
            layers[nodes[c].get("layer", "?")] += 1
        top = ",".join(k for k, _ in sorted(layers.items(), key=lambda x: -x[1])[:3])
        print(f"[{len(comp):3d}] cuisine({top}): {', '.join(comp[:6])}{' …' if len(comp) > 6 else ''}")


def cmd_walk(nodes, adj, a):
    """Deterministic 'creative' walk: seeded PRNG over pairs/in_layer edges — inspiration, reproducible."""
    import random
    rng = random.Random(a.seed)
    cur, trail = a.start, [a.start]
    for _ in range(a.steps):
        opts = [(t, ty) for t, ty in adj[cur] if ty in ("pairs", "in_layer", "sourced_from") and t not in trail]
        if not opts:
            break
        cur = opts[rng.randrange(len(opts))][0]
        trail.append(cur)
    print("creative trail:")
    for nid in trail:
        print(f"  {fmt(nodes, nid)}")
    concepts = [n for n in trail if nodes[n]["type"] == "concept"]
    if len(concepts) > 1:
        print(f"recipe seed: combine {', '.join(concepts)}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stats")
    n = sub.add_parser("neighbors"); n.add_argument("node"); n.add_argument("-d", type=int, default=1)
    pa = sub.add_parser("path"); pa.add_argument("src"); pa.add_argument("dst")
    sub.add_parser("clusters")
    w = sub.add_parser("walk"); w.add_argument("start"); w.add_argument("--steps", type=int, default=6); w.add_argument("--seed", type=int, default=7)
    a = p.parse_args()
    nodes, adj = load()
    {"stats": cmd_stats, "neighbors": cmd_neighbors, "path": cmd_path,
     "clusters": cmd_clusters, "walk": cmd_walk}[a.cmd](nodes, adj, a)


if __name__ == "__main__":
    main()
