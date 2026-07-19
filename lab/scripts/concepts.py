#!/usr/bin/env python3
"""Concept kitchen: semantic retrieval over lab/concepts.jsonl (pure stdlib, no embeddings needed).

Maps a natural-language ask to ranked concept cards — the "ingredients" — each with what it does,
status/evidence, what it pairs with, and where it lives. Follows the RDC paper's retrieval rule
(§34.3): return the BUNDLE (concept + pairings + pointers), never just the closest single match.

Usage (from repo root):
    python3 lab/scripts/concepts.py query "the skin looks plastic and fake"
    python3 lab/scripts/concepts.py query "recreate this anime fight exactly" -k 8 --json
    python3 lab/scripts/concepts.py card c_transfer_policy
    python3 lab/scripts/concepts.py stats
    python3 lab/scripts/concepts.py validate     # gate for concept updates (also run by validate_repo)

Updating concepts: append one JSON line to lab/concepts.jsonl per new concept (id c_*, >=3
nl_triggers, evidence ids resolvable when present), then run `validate`. See lab/AGENTS.md
"Concept kitchen".
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

STOP = {"the", "a", "an", "it", "is", "and", "or", "to", "of", "in", "on", "for", "with", "my",
        "i", "im", "want", "make", "like", "this", "that", "how", "do", "can", "me", "be", "so"}
REQUIRED = {"id", "kind", "name", "what", "use_when", "nl_triggers", "pairs_with", "conflicts",
            "status", "evidence", "source", "layer"}
STATUS_BOOST = {"proven": 0.6, "partial": 0.3, "unexplored": 0.0}


def find_root() -> Path:
    for cand in [Path.cwd(), *Path.cwd().parents]:
        if (cand / "lab" / "concepts.jsonl").exists():
            return cand
    sys.exit("error: run from inside the repo (lab/concepts.jsonl not found)")


def load_cards(root: Path) -> list[dict]:
    cards = []
    for n, line in enumerate((root / "lab" / "concepts.jsonl").read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            cards.append(json.loads(line))
        except json.JSONDecodeError as e:
            sys.exit(f"concepts.jsonl:{n}: invalid JSON — {e.msg}")
    return cards


def toks(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP and len(t) > 1}


def score(card: dict, q: set[str]) -> tuple[float, list[str]]:
    """Weighted overlap: trigger phrases speak the user's language, so they weigh most."""
    hits: list[str] = []
    s = 0.0
    for trig in card["nl_triggers"]:
        tt = toks(trig)
        if not tt:
            continue
        ov = len(tt & q) / len(tt)
        if ov >= 0.5:
            s += 3.0 * ov
            hits.append(trig)
    name_ov = len(toks(card["name"]) & q)
    s += 2.0 * name_ov
    s += 1.0 * len(toks(card["what"] + " " + card["use_when"] + " " + card["layer"]) & q) * 0.25
    if s > 0:
        s += STATUS_BOOST.get(card["status"], 0.0)  # prefer proven when relevance ties
    return s, hits


def fmt_card(c: dict, hits: list[str] | None = None, brief: bool = False) -> str:
    lines = [f"{c['id']}  [{c['kind']}/{c['status']}]  {c['name']}"]
    lines.append(f"    what: {c['what']}")
    if not brief:
        lines.append(f"    use_when: {c['use_when']}")
        if hits:
            lines.append(f"    matched: {', '.join(hits[:3])}")
        if c.get("evidence"):
            lines.append(f"    evidence: {', '.join(c['evidence'])}")
        if c.get("pairs_with"):
            lines.append(f"    pairs_with: {', '.join(c['pairs_with'])}")
        if c.get("conflicts"):
            lines.append(f"    conflicts: {', '.join(c['conflicts'])}")
        lines.append(f"    source: {' | '.join(c['source'])}")
    return "\n".join(lines)


def cmd_query(args, cards):
    q = toks(args.text)
    ranked = sorted(((score(c, q), c) for c in cards), key=lambda x: -x[0][0])
    top = [(s, h, c) for (s, h), c in ranked if s > 0][: args.k]
    if not top:
        print("no matches — try different wording, or `stats` to see layers/kinds")
        return
    if args.json:
        print(json.dumps([{"score": round(s, 2), "matched": h, **c} for s, h, c in top], indent=2))
        return
    by_id = {c["id"]: c for c in cards}
    print(f"PANTRY — top {len(top)} ingredient(s) for: {args.text!r}\n")
    for i, (s, h, c) in enumerate(top, 1):
        print(f"{i}. ({s:.1f}) " + fmt_card(c, h))
        print()
    # the bundle rule: expand the top hit's pairings so the answer is a recipe, not one ingredient
    bundle_ids = [p for _, _, c in top[:2] for p in c.get("pairs_with", []) if p in by_id]
    bundle_ids = [b for b in dict.fromkeys(bundle_ids) if b not in {c["id"] for _, _, c in top}]
    if bundle_ids:
        print("BUNDLE — pairs with the top matches (RDC §34.3: retrieve the recipe, not one item):")
        for b in bundle_ids[:5]:
            print("  + " + fmt_card(by_id[b], brief=True).replace("\n", "\n  "))
    flagged = [c["id"] for _, _, c in top if c["status"] == "unexplored"]
    if flagged:
        print(f"\nNOTE: unproven ingredient(s) {', '.join(flagged)} — compose with the flag, propose the A/B (lab/AGENTS.md).")


def cmd_card(args, cards):
    for c in cards:
        if c["id"] == args.id:
            print(fmt_card(c))
            return
    sys.exit(f"no card {args.id!r} — run `stats` or `query`")


def cmd_stats(_args, cards):
    from collections import Counter
    print(f"{len(cards)} concept cards")
    for field in ("status", "kind", "layer"):
        counts = Counter(c[field] for c in cards)
        print(f"  by {field}: " + ", ".join(f"{k}={v}" for k, v in counts.most_common()))


def cmd_validate(_args, cards) -> None:
    ids = [c["id"] for c in cards]
    errs: list[str] = []
    if len(set(ids)) != len(ids):
        dupes = {i for i in ids if ids.count(i) > 1}
        errs.append(f"duplicate ids: {sorted(dupes)}")
    idset = set(ids)
    # evidence ids resolve against the registry when available
    known: set[str] = set()
    reg_path = find_root() / "lab" / "registry.yaml"
    try:
        import yaml
        reg = yaml.safe_load(reg_path.read_text())
        known |= {v["id"] for v in reg.get("variants", [])}
        known |= {p["id"] for p in reg.get("patterns", [])}
        known |= {e["id"] for e in reg.get("experiments", [])}
        import csv
        known |= {r["run_id"] for r in csv.DictReader((find_root() / "lab/runs/results.csv").open())}
    except ImportError:
        print("note: pyyaml missing — skipped evidence resolution", file=sys.stderr)
        known = set()
    for c in cards:
        missing = REQUIRED - c.keys()
        if missing:
            errs.append(f"{c.get('id', '?')}: missing fields {sorted(missing)}")
        if not str(c.get("id", "")).startswith("c_"):
            errs.append(f"{c.get('id', '?')}: id must start with c_")
        if len(c.get("nl_triggers", [])) < 3:
            errs.append(f"{c['id']}: needs >=3 nl_triggers (that's the semantic mapping)")
        for p in list(c.get("pairs_with", [])) + list(c.get("conflicts", [])):
            if p not in idset:
                errs.append(f"{c['id']}: pairs/conflicts ref '{p}' is not a card")
        if known:
            for ev in c.get("evidence", []):
                if ev not in known and not any(k.startswith(ev) for k in known):
                    errs.append(f"{c['id']}: evidence '{ev}' resolves to nothing")
    if errs:
        for e in errs:
            print(f"  FAIL  {e}")
        sys.exit(f"concepts VALIDATE RED: {len(errs)} error(s)")
    print(f"concepts VALIDATE GREEN: {len(cards)} cards OK")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("query", help="rank concepts against a natural-language ask")
    q.add_argument("text")
    q.add_argument("-k", type=int, default=6)
    q.add_argument("--json", action="store_true")
    c = sub.add_parser("card", help="show one card")
    c.add_argument("id")
    sub.add_parser("stats", help="corpus counts")
    sub.add_parser("validate", help="integrity-check the corpus")
    args = p.parse_args()
    cards = load_cards(find_root())
    {"query": cmd_query, "card": cmd_card, "stats": cmd_stats, "validate": cmd_validate}[args.cmd](args, cards)


if __name__ == "__main__":
    main()
