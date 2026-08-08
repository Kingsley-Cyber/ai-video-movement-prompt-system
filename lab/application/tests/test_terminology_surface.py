from __future__ import annotations

import unittest

from lab.application.service import REQUEST_SCHEMA, invoke, list_operations


def _request(operation: str, arguments: dict) -> dict:
    return {
        "schema": REQUEST_SCHEMA,
        "operation": operation,
        "arguments": arguments,
    }


class TerminologySurfaceTests(unittest.TestCase):
    def test_agent_discovers_closed_resolution_workflow(self) -> None:
        result = invoke(
            _request(
                "cpcs.terminology.resolve",
                {"text": "Use action units coding", "domain": None},
            )
        )
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["result"]["state"], "agent_resolution_required")
        self.assertEqual(
            result["result"]["agent_task"]["operation"],
            "cpcs.terminology.propose",
        )

        operator = {row["name"] for row in list_operations("operator")}
        chat = {row["name"] for row in list_operations("chat")}
        self.assertIn("cpcs.terminology.resolve", chat)
        self.assertIn("cpcs.terminology.propose", operator)
        self.assertIn("cpcs.terminology.inspect", operator)
        self.assertNotIn("cpcs.terminology.propose", chat)

        brief = invoke(
            _request(
                "cpcs.agent.brief",
                {
                    "task": "Resolve whether AU01 and action units mean FACS or physical action atoms",
                    "role": "operator",
                },
            )
        )
        self.assertEqual(brief["status"], "success", brief)
        self.assertIn(
            "terminology_resolution",
            brief["result"]["task_routing"]["selected_workflows"],
        )
        operations = {
            operation
            for phase in brief["result"]["execution_plan"]
            for operation in phase["operations"]
        }
        self.assertTrue(
            {
                "cpcs.terminology.resolve",
                "cpcs.source.resolve",
                "cpcs.terminology.propose",
                "cpcs.terminology.inspect",
                "cpcs.reason",
            }.issubset(operations)
        )


if __name__ == "__main__":
    unittest.main()
