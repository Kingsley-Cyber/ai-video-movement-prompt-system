from __future__ import annotations

import copy
import unittest
from unittest import mock

from lab.application.mcp import _tool_rows
from lab.application.service import (
    REQUEST_SCHEMA,
    authorization_request_hash,
    invoke,
    list_operations,
)


def request_for(arguments: dict) -> dict:
    return {
        "schema": REQUEST_SCHEMA,
        "operation": "cpcs.polymath.retrieve",
        "arguments": copy.deepcopy(arguments),
    }


def authorization_for(arguments: dict) -> dict:
    return {
        "schema": "cpcs.explicit_authorization/1.0",
        "authorization_id": "auth_polymath_test",
        "authorized_by": "owner-test",
        "operation": "cpcs.polymath.retrieve",
        "request_hash": authorization_request_hash(
            "cpcs.polymath.retrieve", arguments
        ),
        "reason": "test exact external retrieval authorization",
    }


class PolymathApplicationSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.arguments = {
            "query": "decimal spatial movement",
            "rights_basis": "owner_authorized_research",
            "corpus_ids": ["corpus-001"],
            "tool": "polymath_search",
            "retrieval_tier": "qdrant_mongo",
            "top_k": 4,
            "rerank_enabled": True,
            "search_mode": "local",
        }

    def test_external_retrieval_is_operator_only_and_exact_authorized(self) -> None:
        chat = {row["name"] for row in list_operations("chat")}
        operator = {row["name"]: row for row in list_operations("operator")}
        self.assertNotIn("cpcs.polymath.retrieve", chat)
        self.assertIn("cpcs.polymath.retrieve", operator)
        contract = operator["cpcs.polymath.retrieve"]
        self.assertEqual(contract["mutation_scope"], "operational_external")
        self.assertTrue(contract["authorization_required"])

        missing = invoke(request_for(self.arguments), role="operator")
        self.assertEqual(missing["error"]["code"], "permission_denied")

        changed = request_for(self.arguments)
        changed["authorization"] = authorization_for(self.arguments)
        changed["arguments"]["query"] = "changed after authorization"
        mismatched = invoke(changed, role="operator")
        self.assertEqual(mismatched["error"]["code"], "permission_denied")

        status = invoke(
            {"schema": REQUEST_SCHEMA, "operation": "cpcs.status", "arguments": {}}
        )
        polymath = status["result"]["integrations"]["polymath_mcp"]
        self.assertFalse(polymath["network_contacted"])
        self.assertNotIn("token", polymath)

    def test_authorized_retrieval_forwards_one_bounded_typed_request(self) -> None:
        expected = {
            "schema": "cpcs.polymath_retrieval/1.0",
            "retrieved_passages": {"schema": "cpcs.retrieved_passages/1.0"},
        }
        request = request_for(self.arguments)
        request["authorization"] = authorization_for(self.arguments)
        with mock.patch(
            "lab.application.service.retrieve_polymath", return_value=expected
        ) as retrieve:
            response = invoke(request, role="operator")
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["result"], expected)
        retrieve.assert_called_once()
        call = retrieve.call_args
        self.assertEqual(call.args, (self.arguments["query"],))
        self.assertEqual(call.kwargs["corpus_ids"], ["corpus-001"])
        self.assertEqual(call.kwargs["rights_basis"], "owner_authorized_research")
        self.assertEqual(call.kwargs["top_k"], 4)

    def test_mcp_marks_polymath_as_open_world_and_not_read_only(self) -> None:
        operator = {row["name"]: row for row in _tool_rows("operator")}
        tool = operator["cpcs.polymath.retrieve"]
        self.assertTrue(tool["annotations"]["openWorldHint"])
        self.assertFalse(tool["annotations"]["readOnlyHint"])
        self.assertIn("_cpcs_authorization", tool["inputSchema"]["properties"])


if __name__ == "__main__":
    unittest.main()
