from __future__ import annotations

import unittest

from lab.application.service import APPLICATION_POLICY, REQUEST_SCHEMA, invoke, list_operations
from lab.second_brain.src.validate import REPO_ROOT


class ReasoningPolicySurfaceTests(unittest.TestCase):
    def test_public_strategy_operation_is_read_only_and_replay_stable(self) -> None:
        authority_paths = [
            REPO_ROOT / "lab" / "concepts.jsonl",
            *sorted((REPO_ROOT / "lab" / "second_brain" / "curated").glob("*.jsonl")),
            *sorted((REPO_ROOT / "lab" / "second_brain" / "immutable").glob("*.jsonl")),
        ]
        before = {path: path.read_bytes() for path in authority_paths}
        request = {
            "schema": REQUEST_SCHEMA,
            "operation": "cpcs.strategy.compile",
            "arguments": {
                "text": "Create a restrained scene where she realizes he is lying",
                "minimum_status": "partial",
            },
        }
        first = invoke(request)
        second = invoke(request)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "success")
        self.assertEqual(first["policy_versions"]["application"], APPLICATION_POLICY)
        self.assertEqual(
            first["result"]["policy_selection"]["policy_id"],
            "rp_graph_of_thoughts",
        )
        self.assertEqual(before, {path: path.read_bytes() for path in authority_paths})

    def test_operation_is_discoverable_to_chat_without_write_authority(self) -> None:
        row = next(
            operation
            for operation in list_operations("chat")
            if operation["name"] == "cpcs.strategy.compile"
        )
        self.assertIsNone(row["mutation_scope"])
        self.assertFalse(row["authorization_required"])


if __name__ == "__main__":
    unittest.main()
