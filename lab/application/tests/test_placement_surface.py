from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from lab.application.service import REQUEST_SCHEMA, invoke, list_operations
from lab.second_brain.src.distill import run_distillation
from lab.second_brain.src.validate import REPO_ROOT
from lab.second_brain.tests.test_placement import (
    _assignments,
    _batch,
    _root,
)


def _request(operation: str, arguments: dict) -> dict:
    return {
        "schema": REQUEST_SCHEMA,
        "operation": operation,
        "arguments": arguments,
    }


class OntologyPlacementSurfaceTests(unittest.TestCase):
    def test_operator_can_plan_inspect_and_discover_the_closed_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _root(Path(temporary))
            shutil.copytree(
                REPO_ROOT / "lab" / "application" / "schemas",
                root / "lab" / "application" / "schemas",
            )
            shutil.copytree(
                REPO_ROOT / "lab" / "release",
                root / "lab" / "release",
            )
            run = run_distillation(_batch(), root)
            planned = invoke(
                _request(
                    "cpcs.research.placement.plan",
                    {"run_id": run["id"], "durable_ids": _assignments(run)},
                ),
                role="operator",
                root=root,
            )
            self.assertEqual(planned["status"], "success", planned)
            inspected = invoke(
                _request(
                    "cpcs.research.placement.inspect",
                    {"plan_id": planned["result"]["id"]},
                ),
                role="operator",
                root=root,
            )
            self.assertEqual(inspected["status"], "success", inspected)
            self.assertTrue(inspected["result"]["current"])
            operator = {row["name"] for row in list_operations("operator")}
            chat = {row["name"] for row in list_operations("chat")}
            self.assertIn("cpcs.research.placement.plan", operator)
            self.assertIn("cpcs.research.placement.inspect", operator)
            self.assertNotIn("cpcs.research.placement.plan", chat)
            brief = invoke(
                _request(
                    "cpcs.agent.brief",
                    {
                        "task": "Place distilled research into the ontology and graph growth plan",
                        "role": "operator",
                    },
                ),
                root=root,
            )
            self.assertEqual(brief["status"], "success", brief)
            operations = {
                operation
                for phase in brief["result"]["execution_plan"]
                for operation in phase["operations"]
            }
            self.assertIn("cpcs.research.placement.plan", operations)


if __name__ == "__main__":
    unittest.main()
