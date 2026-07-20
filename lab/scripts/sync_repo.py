#!/usr/bin/env python3
"""CONTROL PLANE: deterministic E2E sync across the repo's coupled artifacts.

The repo grows and shrinks TOGETHER. This script enforces the sync contract (root AGENTS.md):
when a research package is added or removed, the graph, concept cards, CONCEPT_INDEX, and agent
directions must move with it — drift fails the gate.

    python3 lab/scripts/sync_repo.py           # check (gate mode; exit != 0 on drift)
    python3 lab/scripts/sync_repo.py --fix     # regenerate derived artifacts (graph), then re-check;
                                               # content edits it cannot make are printed as REQUIRED ACTIONS

Checks:
  S1 graph freshness      graph.json == exact rebuild from sources (derived-view law)
  S2 research coverage    every research/ package: alias registered (build_graph.PAPER_ALIASES),
                          >=1 concept card sources it, CONCEPT_INDEX mentions it — catches ADDS
  S3 no dangling refs     no card/alias/index entry points at a research package that is gone — catches REMOVALS
  S4 routing sync         lab/AGENTS.md trigger table <-> RUNBOOK_*.md files, both directions
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_graph  # noqa: E402  (shared root-finder + PAPER_ALIASES + build)

ACTIONS: list[str] = []
FAILS: list[str] = []


def fail(msg: str, action: str | None = None):
    FAILS.append(msg)
    print(f"  FAIL  {msg}")
    if action:
        ACTIONS.append(action)


def ok(msg: str):
    print(f"  ok    {msg}")


def main() -> None:
    fix = "--fix" in sys.argv
    root = build_graph.find_root()
    lab = root / "lab"

    # S1 — graph freshness (derived-view law)
    print("[S1] graph freshness")
    rebuilt = json.dumps(build_graph.build(root), indent=1, sort_keys=True) + "\n"
    gpath = lab / "graph.json"
    current = gpath.read_text() if gpath.exists() else ""
    if current != rebuilt:
        if fix:
            gpath.write_text(rebuilt)
            ok("graph.json regenerated (--fix)")
        else:
            fail("graph.json is stale or missing vs its sources",
                 "run: python3 lab/scripts/sync_repo.py --fix  (regenerates graph.json)")
    else:
        ok("graph.json matches exact rebuild")

    # S2/S3 — research packages <-> aliases <-> cards <-> CONCEPT_INDEX
    print("[S2] research coverage (adds)")
    research = root / "research"
    packages = sorted(p.name for p in research.iterdir()) if research.exists() else []
    cards_text = (lab / "concepts.jsonl").read_text()
    index_text = (lab / "CONCEPT_INDEX.md").read_text()
    for pkg in packages:
        aliases = build_graph.PAPER_ALIASES.get(pkg)
        if not aliases:
            fail(f"research/{pkg}: no alias registered",
                 f"INGEST INCOMPLETE for {pkg}: add alias to build_graph.PAPER_ALIASES, add concept "
                 f"cards (>=3 nl_triggers) sourcing it, add a CONCEPT_INDEX part, rebuild graph")
            continue
        if not any(a in cards_text for a in aliases + [pkg]):
            fail(f"research/{pkg}: zero concept cards source it",
                 f"add cards for {pkg} (growth protocol: retrievable + placed + adjustable)")
        else:
            ok(f"{pkg}: cards present")
        stem = pkg.split("_Research_Package")[0].split(".md")[0]
        if stem[:28] not in index_text and pkg not in index_text:
            fail(f"research/{pkg}: not mentioned in CONCEPT_INDEX.md",
                 f"add a CONCEPT_INDEX part/row for {pkg}")

    print("[S3] dangling refs (removals)")
    dangling = [pkg for pkg in build_graph.PAPER_ALIASES if pkg not in packages]
    for pkg in dangling:
        fail(f"alias registered for research/{pkg} but the package is GONE",
             f"REMOVAL INCOMPLETE for {pkg}: delete its alias from build_graph.PAPER_ALIASES, "
             f"retire/retag its concept cards, remove its CONCEPT_INDEX part, rebuild graph")
    if not dangling:
        ok("no aliases point at removed packages")

    # S4 — routing table <-> runbooks on disk
    print("[S4] routing sync")
    agents = (lab / "AGENTS.md").read_text()
    routed = set(re.findall(r"`(RUNBOOK_[A-Za-z0-9_]+\.md)`", agents))
    on_disk = {p.name for p in lab.glob("RUNBOOK_*.md")}
    for missing in sorted(routed - on_disk):
        fail(f"AGENTS.md routes to {missing} which does not exist", f"restore {missing} or remove its routing row")
    for orphan in sorted(on_disk - routed):
        fail(f"{orphan} exists but has no routing row in lab/AGENTS.md", f"add a trigger row for {orphan}")
    if routed == on_disk:
        ok(f"{len(on_disk)} runbooks all routed, no orphans")

    print()
    if FAILS:
        print(f"SYNC RED: {len(FAILS)} drift issue(s).")
        if ACTIONS:
            print("REQUIRED ACTIONS (deterministic, in order):")
            for i, a in enumerate(dict.fromkeys(ACTIONS), 1):
                print(f"  {i}. {a}")
        sys.exit(1)
    print("SYNC GREEN: repo artifacts are in sync (graph, research, cards, index, routing).")


if __name__ == "__main__":
    main()
