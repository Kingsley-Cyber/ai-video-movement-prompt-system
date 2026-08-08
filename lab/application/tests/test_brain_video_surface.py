from __future__ import annotations

import unittest

from lab.application.mcp import _tool_rows
from lab.application.service import list_operations


class BrainVideoSurfaceTests(unittest.TestCase):
    def test_mcp_exposes_bounded_maintenance_and_video_reasoning_contracts(self) -> None:
        operator = {row["name"]: row for row in list_operations("operator")}
        curator = {row["name"]: row for row in list_operations("curator")}
        mcp_operator = {row["name"]: row for row in _tool_rows("operator")}
        for name in (
            "cpcs.brain.health",
            "cpcs.maintenance.prepare",
            "cpcs.maintenance.status",
            "cpcs.maintenance.advance",
            "cpcs.video.research_gaps",
            "cpcs.video.comparison.lens",
        ):
            self.assertIn(name, operator)
            self.assertIn(name, mcp_operator)
        self.assertTrue(operator["cpcs.maintenance.advance"]["authorization_required"])
        self.assertEqual(
            operator["cpcs.maintenance.advance"]["mutation_scope"],
            "operational_external",
        )
        bridge = curator["cpcs.video.bridge.promote"]
        self.assertEqual(bridge["required_role"], "curator")
        self.assertTrue(bridge["authorization_required"])
        self.assertEqual(bridge["mutation_scope"], "curated")


if __name__ == "__main__":
    unittest.main()
