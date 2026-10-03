from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from lab.application.service import REQUEST_SCHEMA, invoke, list_operations
from lab.second_brain.tests.test_directing_session import fixture, fixture_root


class DirectingSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = fixture_root(Path(self.temporary.name))
        self.data = fixture()

    def call(self, operation: str, arguments: dict, role: str = "operator") -> dict:
        return invoke(
            {"schema": REQUEST_SCHEMA, "operation": "cpcs." + operation, "arguments": arguments},
            role=role, root=self.root,
        )

    def result(self, operation: str, arguments: dict) -> dict:
        response = self.call(operation, arguments)
        self.assertEqual(response["status"], "success", response.get("error"))
        return response["result"]

    def direct(self) -> tuple[str, dict]:
        started = self.result("direct.start", {"text": self.data["ask"]})
        sid = started["session_id"]
        packet = self.result("direct.packet.read", {"session_id": sid, "pass_id": "scene_action"})
        submitted = self.result("direct.proposal.submit", {
            "session_id": sid, "pass_id": "scene_action", "packet_hash": packet["packet_hash"],
            "proposal": copy.deepcopy(self.data["proposal"]),
        })
        self.assertEqual(submitted["disposition"], "accepted")
        return sid, self.result("direct.finish", {"session_id": sid})

    def test_public_path_directs_the_jail_fight(self) -> None:
        authority = self.root / "lab/second_brain"
        paths = [self.root / "lab/concepts.jsonl"]
        for tier in ("curated", "immutable", "derived", "staging"):
            paths.extend(p for p in (authority / tier).rglob("*") if p.is_file())
        before = {p: p.read_bytes() for p in paths}
        sid, finish = self.direct()
        score = finish["score"]
        for key in ("entities", "beats", "actions", "interactions"):
            self.assertEqual(len(score[key]), self.data["expected"][key])
        self.assertEqual(score["scenes"][0]["duration_s"], 15)
        self.assertIn("scenes", score["constraints"]["locked_paths"])
        self.assertEqual(score["score_status"], "ready")
        self.assertTrue(finish["scene_completeness"]["directed"])
        self.assertEqual(finish["provider_fit"]["status"], "unsupported")
        self.assertIsNone(finish["build"])
        self.assertIn("directing-ledger://", json.dumps(score["provenance"]))
        state = self.result("direct.state.read", {"session_id": sid})
        self.assertEqual(state["scene"]["actions"], score["actions"])
        self.assertEqual(before, {p: p.read_bytes() for p in paths})

    def test_finish_twice_gives_the_same_score_id(self) -> None:
        sid, first = self.direct()
        second = self.result("direct.finish", {"session_id": sid})
        self.assertEqual(first, second)

    def test_plain_score_build_is_unchanged(self) -> None:
        before = self.result("score.build", {"text": self.data["ask"]})
        self.direct()
        after = self.result("score.build", {"text": self.data["ask"]})
        self.assertEqual(before, after)
        self.assertEqual(after["score"]["entities"], [])
        self.assertEqual(after["score"]["actions"], [])

    def test_rejection_is_a_success_response_with_typed_reasons(self) -> None:
        sid = self.result("direct.start", {"text": self.data["ask"]})["session_id"]
        packet = self.result("direct.packet.read", {"session_id": sid, "pass_id": "scene_action"})
        proposal = copy.deepcopy(self.data["proposal"])
        proposal["decisions"][9]["values"]["actor"] = "unknown"
        result = self.result("direct.proposal.submit", {
            "session_id": sid, "pass_id": "scene_action", "packet_hash": packet["packet_hash"],
            "proposal": proposal,
        })
        self.assertEqual(result["disposition"], "rejected")
        self.assertIn("unknown_reference", [r["code"] for r in result["rejections"]])
        self.assertEqual(self.result("direct.state.read", {"session_id": sid})["decisions"], [])

    def test_chat_role_is_denied(self) -> None:
        response = self.call("direct.start", {"text": self.data["ask"]}, role="chat")
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error"]["code"], "permission_denied")

    def test_direct_operations_are_operator_only_and_not_chat_exposed(self) -> None:
        names = {"cpcs.direct." + n for n in (
            "start", "packet.read", "proposal.submit", "state.read", "finish"
        )}
        operators = {row["name"]: row for row in list_operations("operator")}
        self.assertTrue(names <= set(operators))
        self.assertFalse(names.intersection(row["name"] for row in list_operations("chat")))
        self.assertTrue(all(operators[n]["required_role"] == "operator" for n in names))
