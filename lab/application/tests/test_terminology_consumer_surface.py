from __future__ import annotations

import unittest

from lab.application.service import REQUEST_SCHEMA, invoke, list_operations


class TerminologyConsumerSurfaceTests(unittest.TestCase):
    def test_intent_and_context_mcp_contracts_accept_resolution_handoff(self) -> None:
        catalog = {row["name"]: row for row in list_operations("chat")}
        for operation in ("cpcs.intent.context", "cpcs.context.get"):
            proposal_schema = catalog[operation]["input_schema"]["properties"][
                "terminology_proposal_ids"
            ]
            self.assertTrue(proposal_schema["uniqueItems"])
            self.assertEqual(
                proposal_schema["items"]["pattern"],
                "^termprop_[0-9a-f]{24}$",
            )

        unresolved = invoke(
            {
                "schema": REQUEST_SCHEMA,
                "operation": "cpcs.intent.context",
                "arguments": {"text": "Make a video with follow through"},
            }
        )
        self.assertEqual(unresolved["status"], "success", unresolved)
        self.assertEqual(
            unresolved["result"]["context_bundle"]["terminology"]["state"],
            "agent_resolution_required",
        )


if __name__ == "__main__":
    unittest.main()
