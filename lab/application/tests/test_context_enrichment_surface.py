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


OPERATION = "cpcs.context.enrich"


def request_for(arguments: dict) -> dict:
    return {
        "schema": REQUEST_SCHEMA,
        "operation": OPERATION,
        "arguments": copy.deepcopy(arguments),
    }


def authorization_for(arguments: dict) -> dict:
    return {
        "schema": "cpcs.explicit_authorization/1.0",
        "authorization_id": "auth_context_enrichment_test",
        "authorized_by": "owner-test",
        "operation": OPERATION,
        "request_hash": authorization_request_hash(OPERATION, arguments),
        "reason": "test exact gap-only context enrichment authorization",
    }


class ContextEnrichmentApplicationSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.arguments = {
            "query": "Laban effort decimal spatial movement",
            "rights_basis": "owner_authorized_research",
            "token_budget": 12_000,
            "minimum_status": "ingested",
            "target_format": "json",
            "corpus_ids": ["corpus-001"],
            "tool": "polymath_search",
            "retrieval_tier": "qdrant_mongo",
            "top_k": 4,
            "rerank_enabled": True,
            "search_mode": "local",
        }

    def test_operation_is_operator_only_external_and_exact_authorized(self) -> None:
        chat = {row["name"] for row in list_operations("chat")}
        operator = {row["name"]: row for row in list_operations("operator")}
        self.assertNotIn(OPERATION, chat)
        self.assertIn(OPERATION, operator)
        contract = operator[OPERATION]
        self.assertEqual(contract["mutation_scope"], "operational_external")
        self.assertTrue(contract["authorization_required"])

        missing = invoke(request_for(self.arguments), role="operator")
        self.assertEqual(missing["error"]["code"], "permission_denied")

        changed = request_for(self.arguments)
        changed["authorization"] = authorization_for(self.arguments)
        changed["arguments"]["top_k"] = 5
        mismatched = invoke(changed, role="operator")
        self.assertEqual(mismatched["error"]["code"], "permission_denied")

    def test_no_gap_public_operation_contacts_no_external_service(self) -> None:
        arguments = {
            **self.arguments,
            "query": "Laban effort",
        }
        request = request_for(arguments)
        request["authorization"] = authorization_for(arguments)
        with mock.patch(
            "lab.second_brain.src.enrich.retrieve_polymath",
            side_effect=AssertionError("no-gap request must not contact Polymath"),
        ):
            response = invoke(request, role="operator")

        self.assertEqual(response["status"], "success")
        result = response["result"]
        self.assertEqual(result["schema"], "cpcs.context_enrichment/1.0")
        self.assertEqual(result["disposition"], "no_gap")
        self.assertFalse(result["network_contacted"])
        self.assertEqual(result["authority_effect"], "none")

    def test_authorized_gap_request_forwards_context_and_retrieval_options(self) -> None:
        expected = {
            "schema": "cpcs.context_enrichment/1.0",
            "disposition": "enriched",
        }
        request = request_for(self.arguments)
        request["authorization"] = authorization_for(self.arguments)
        with mock.patch(
            "lab.application.service.enrich_context_bundle",
            return_value=expected,
        ) as enrich:
            response = invoke(request, role="operator")

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["result"], expected)
        enrich.assert_called_once()
        call = enrich.call_args
        self.assertEqual(call.args, (self.arguments["query"],))
        self.assertEqual(call.kwargs["rights_basis"], "owner_authorized_research")
        self.assertEqual(call.kwargs["token_budget"], 12_000)
        self.assertEqual(call.kwargs["corpus_ids"], ["corpus-001"])
        self.assertEqual(call.kwargs["top_k"], 4)

    def test_mcp_marks_enrichment_as_open_world_and_not_read_only(self) -> None:
        operator = {row["name"]: row for row in _tool_rows("operator")}
        tool = operator[OPERATION]
        self.assertTrue(tool["annotations"]["openWorldHint"])
        self.assertFalse(tool["annotations"]["readOnlyHint"])
        self.assertIn("_cpcs_authorization", tool["inputSchema"]["properties"])


if __name__ == "__main__":
    unittest.main()
