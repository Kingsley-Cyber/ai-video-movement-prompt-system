from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.maintenance import (
    advance_maintenance,
    build_brain_health_report,
    build_domain_coverage_report,
    maintenance_status,
    prepare_maintenance,
)
from lab.second_brain.src.reflect import rebuild
from lab.second_brain.src.temporal import is_visible_bitemporal
from lab.second_brain.tests.helpers import concept, make_root, write_rows


class MaintenanceRuntimeTests(unittest.TestCase):
    def test_bitemporal_visibility_separates_valid_and_known_time(self) -> None:
        record = {
            "validity": {
                "valid_from": "2025-01-01T00:00:00Z",
                "valid_until": None,
                "status": "active",
                "supersedes": [],
                "superseded_by": [],
            },
            "provenance": {"system_known_from": "2025-02-01T00:00:00Z"},
        }
        self.assertFalse(
            is_visible_bitemporal(
                record,
                "historical",
                valid_at="2025-01-15T00:00:00Z",
                known_at="2025-01-20T00:00:00Z",
            )
        )
        self.assertTrue(
            is_visible_bitemporal(
                record,
                "historical",
                valid_at="2025-01-15T00:00:00Z",
                known_at="2025-02-02T00:00:00Z",
            )
        )

    def test_selective_rebuild_and_resumable_maintenance_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [concept("c_fixture_camera", "camera movement", "camera")],
            )
            write_rows(
                root
                / "lab"
                / "second_brain"
                / "curated"
                / "domain_coverage_manifests.jsonl",
                [
                    {
                        "schema": "cpcs.domain_coverage_manifest/1.0",
                        "id": "domain_inventory_fixture_camera",
                        "domain": "camera",
                        "inventory_name": "Fixture camera inventory",
                        "inventory_scope": "complete_source_inventory",
                        "expected_ids": ["c_fixture_camera"],
                        "source_refs": ["fixture://camera"],
                        "completeness_claim": "source_complete",
                    }
                ],
            )
            selective = rebuild(root, targets={"domain_coverage"})
            self.assertEqual(set(selective), {"domain_coverage.json"})
            self.assertFalse(
                (root / "lab" / "second_brain" / "derived" / "weights.json").exists()
            )
            rebuild(root)
            state = prepare_maintenance(
                ["domain_coverage", "brain_health"], root=root
            )
            for _ in range(4):
                state = advance_maintenance(state["maintenance_id"], root=root)
            self.assertEqual(state["stage"], "complete")
            self.assertEqual(len(state["completed_stages"]), 4)
            self.assertEqual(state["event_count"], 5)
            self.assertEqual(
                maintenance_status(state["maintenance_id"], root)["state_hash"],
                state["state_hash"],
            )
            health = build_brain_health_report(root)
            self.assertEqual(health["domain_coverage"]["summary"]["missing"], 0)


if __name__ == "__main__":
    unittest.main()
