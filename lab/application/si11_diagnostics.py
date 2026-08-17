"""SI-1.1 acceptance diagnostics — the measured generation failure.

Runs the exact UGC water-bottle scenario plus cooking / manipulation /
fight / drone resource cases. Writes SI11_RESOURCE_DIAGNOSTICS_v0.1.json.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from lab.compiler.profiles import REPO_ROOT

OUT = Path(__file__).resolve().parent
DIAG = OUT / "SI11_RESOURCE_DIAGNOSTICS_v0.1.json"

CASES: list[dict[str, Any]] = [
    {"name": "UGC_WATER_BOTTLE_FAILURE_CASE", "actor_ids": ["creator"],
     "intent": ("A 15-second TikTok-style UGC video of a woman casually "
                "showing off a water bottle she actually uses every day. "
                "She picks it up, takes a drink, talks about why she "
                "likes it, and shows it to the camera at the end. It "
                "should feel natural and believable like a real creator "
                "filmed it on her phone, not like an ad.")},
    {"name": "COOKING_THIRD_OBJECT", "actor_ids": ["chef"],
     "intent": "A chef slices a tomato and picks up a plate."},
    {"name": "OBJECT_MANIPULATION_BIMANUAL", "actor_ids": ["hands"],
     "intent": "A pair of hands assembles a small mechanical keyboard on "
               "a desk."},
    {"name": "FIGHT_GRIP_CHAIN", "actor_ids": ["fighter"],
     "intent": ("A fighter catches an opponent's leg, swings him in a "
                "wide arc, releases him onto the water, then immediately "
                "pressures him while he tries to recover.")},
    {"name": "DRONE_NO_HUMAN_GRAPH", "actor_ids": None,
     "intent": "A drone camera orbits a coastal cliff with no performer "
               "visible."},
]


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    from lab.application.cpcs_actor_resources import build_resource_constraints
    from lab.application.cpcs_narrative_beats import build_narrative_beat_graph

    results: dict[str, Any] = {}
    for case in CASES:
        graph = build_narrative_beat_graph(case["intent"])
        packet = build_resource_constraints(
            case["intent"], graph, actor_ids=case["actor_ids"])
        results[case["name"]] = {
            "intent": case["intent"][:80],
            "beats": [b["display_name"] for b in graph.beats],
            "phone_hold": packet.lineage.get("phone_hold", False),
            "resources": packet.actor_resources,
            "occupancy_ledger": packet.occupancy_ledger,
            "preconditions": packet.preconditions,
            "conflicts": packet.conflicts,
            "packet_hash": packet.packet_hash,
        }
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
        capture_output=True, text=True, check=True).stdout.strip()
    DIAG.write_text(json.dumps({
        "artifact": "CPCS_SI11_RESOURCE_DIAGNOSTICS",
        "version": "v0.1",
        "git_commit": commit,
        "cases": results,
    }, indent=1) + "\n")

    # acceptance summary for the measured failure case
    wb = results["UGC_WATER_BOTTLE_FAILURE_CASE"]
    print("FAILURE-CASE ACCEPTANCE (water bottle):")
    print("  phone hand persistent:",
          any(r["assigned_role"] == "phone_hold"
              and r["state"] == "OCCUPIED" for r in wb["resources"]))
    print("  bottle grip on phone hand:",
          any(e.get("object") == "bottle" and e.get("role") == "GRASP"
              and "phone_hold" == next(
                  (r["assigned_role"] for r in wb["resources"]
                   if r["actor_id"] + "." + r["resource_id"] == e["resource"]),
                  None)
              for e in wb["occupancy_ledger"]))
    print("  DRINK precondition:",
          next((p["disposition"] for p in wb["preconditions"]
                if p["display"] == "DRINK"), "missing"))
    print("  invented closure mechanism present:",
          any(m in json.dumps(wb["preconditions"])
              for m in ("twist", "pop", "flip_open", "straw", "unscrew")))
    print("  resource conflicts:", len(wb["conflicts"]))
    print()
    for name, fx in results.items():
        if name == "UGC_WATER_BOTTLE_FAILURE_CASE":
            continue
        print(f"{name:28} conflicts={len(fx['conflicts'])} "
              f"resources={len(fx['resources'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
