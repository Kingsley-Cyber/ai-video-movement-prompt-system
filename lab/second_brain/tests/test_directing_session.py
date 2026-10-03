from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from functools import partial
from pathlib import Path

from lab.compiler.decisions import validate_decisions
from lab.second_brain.src import directing_session as direct
from lab.second_brain.src.validate import REPO_ROOT, ValidationFailure


def fixture() -> dict:
    return json.loads(
        (REPO_ROOT / "handoff/direct_scene/reference/jail_fight_proposal.json").read_text()
    )


def fixture_root(base: Path) -> Path:
    root = base / "repo"
    shutil.copytree(
        REPO_ROOT / "lab", root / "lab", ignore=shutil.ignore_patterns("__pycache__")
    )
    return root


class DirectingSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = fixture_root(Path(self.temporary.name))
        self.data = fixture()
        self.started = direct.start_session(self.data["ask"], root=self.root)
        self.session_id = self.started["session_id"]
        self.packet = direct.read_packet(self.session_id, "scene_action", root=self.root)

    def submit(self, proposal: dict | None = None, packet_hash: str | None = None) -> dict:
        return direct.submit_proposal(
            self.session_id, "scene_action",
            packet_hash or self.packet["packet_hash"],
            proposal if proposal is not None else copy.deepcopy(self.data["proposal"]),
            value_check=partial(validate_decisions, root=self.root), root=self.root,
        )

    def refused(self, proposal: dict, code: str) -> None:
        before = direct.read_state(self.session_id, root=self.root)
        result = self.submit(proposal)
        self.assertEqual(result["disposition"], "rejected")
        self.assertIn(code, [r["code"] for r in result["rejections"]])
        self.assertEqual(before, direct.read_state(self.session_id, root=self.root))

    def test_start_creates_sealed_session_and_is_idempotent(self) -> None:
        again = direct.start_session(self.data["ask"], root=self.root)
        self.assertEqual(again["disposition"], "already_present")
        self.assertEqual(again["session_id"], self.session_id)
        path = self.root / "work/application/directing_sessions" / self.session_id
        session = json.loads((path / "session.json").read_text())
        self.assertEqual(session["ledger_hash"], self.started["ledger_hash"])
        self.assertEqual((path / "session.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.stat().st_mode & 0o777, 0o700)
        self.assertEqual(session["decisions"], [])

    def test_packet_is_derived_and_hash_stable(self) -> None:
        self.assertEqual(
            self.packet, direct.read_packet(self.session_id, "scene_action", root=self.root)
        )
        self.assertEqual(self.packet["upstream"], [])
        self.assertEqual(len(self.packet["sublayers"]), 5)
        for row in self.packet["research"]["concepts"]:
            self.assertIn(row["layer"], ["action", "whole-body movement", "animation timing"])
            self.assertTrue(row["content_hash"].startswith("sha256:"))
        path = self.root / "work/application/directing_sessions" / self.session_id
        self.assertFalse((path / "packet.json").exists())

    def test_packet_reports_requested_duration_with_its_span(self) -> None:
        constraints = self.packet["constraints"]
        self.assertEqual(constraints["requested_duration_s"], 15)
        span = constraints["duration_source"]
        self.assertEqual(span["text"], self.data["ask"][span["start"]:span["end"]])
        self.assertEqual(span["text"], "15 seconds")

    def test_submit_accepts_jail_fight_and_appends_ledger(self) -> None:
        result = self.submit()
        self.assertEqual(result["disposition"], "accepted")
        state = direct.read_state(self.session_id, root=self.root)
        self.assertEqual(len(state["decisions"]), len(self.data["proposal"]["decisions"]))
        self.assertEqual(state["passes"][0]["status"], "accepted")
        self.assertEqual(
            [d["sequence"] for d in state["decisions"]], list(range(len(state["decisions"])))
        )
        self.assertTrue(all(d["pass_id"] == "scene_action" for d in state["decisions"]))

    def test_identical_resubmit_is_already_present(self) -> None:
        first = self.submit()
        again = self.submit()
        self.assertEqual(again["disposition"], "already_present")
        self.assertEqual(first["proposal_hash"], again["proposal_hash"])
        self.assertEqual(first["ledger_hash"], again["ledger_hash"])

    def test_different_second_proposal_is_refused(self) -> None:
        self.submit()
        changed = copy.deepcopy(self.data["proposal"])
        changed["decisions"][1]["values"]["time_of_day"] = "morning"
        self.refused(changed, "pass_already_accepted")

    def test_stale_packet_hash_is_refused(self) -> None:
        result = self.submit(packet_hash="sha256:" + "0" * 64)
        self.assertEqual(result["disposition"], "rejected")
        self.assertEqual(result["rejections"][0]["code"], "stale_packet")
        self.assertEqual(direct.read_state(self.session_id, root=self.root)["decisions"], [])

    def test_tampered_session_fails_closed(self) -> None:
        path = self.root / "work/application/directing_sessions" / self.session_id / "session.json"
        session = json.loads(path.read_text())
        session["ask"]["text"] = "Changed ask"
        path.write_text(json.dumps(session))
        with self.assertRaises(ValidationFailure):
            direct.read_state(self.session_id, root=self.root)

    def test_missing_required_sublayer_is_refused(self) -> None:
        proposal = copy.deepcopy(self.data["proposal"])
        proposal["decisions"] = [d for d in proposal["decisions"] if d["sublayer"] != "entities"]
        proposal["not_applicable"] = [{"sublayer_id": "entities", "reason": "No actors"}]
        self.refused(proposal, "missing_required_sublayer")

    def test_user_explicit_requires_verbatim_ask_span(self) -> None:
        proposal = copy.deepcopy(self.data["proposal"])
        proposal["decisions"][0]["evidence_uses"][0]["text"] = "8 seconds"
        self.refused(proposal, "user_explicit_without_span")

    def test_sourced_research_must_cite_packet_evidence(self) -> None:
        proposal = copy.deepcopy(self.data["proposal"])
        proposal["decisions"][2]["source_status"] = "sourced_research"
        proposal["decisions"][2]["evidence_uses"] = [
            {"kind": "concept", "id": "c_absent", "content_hash": "sha256:" + "0" * 64}
        ]
        self.refused(proposal, "evidence_outside_packet")

    def test_model_tested_is_not_admissible_yet(self) -> None:
        proposal = copy.deepcopy(self.data["proposal"])
        proposal["decisions"][2]["source_status"] = "model_tested"
        self.refused(proposal, "model_tested_not_admissible")

    def test_lock_requires_user_explicit(self) -> None:
        proposal = copy.deepcopy(self.data["proposal"])
        proposal["decisions"][2]["lock"] = True
        self.refused(proposal, "lock_requires_user_explicit")

    def test_unknown_input_is_refused(self) -> None:
        proposal = copy.deepcopy(self.data["proposal"])
        proposal["decisions"][2]["inputs"] = ["d_action_6"]
        self.refused(proposal, "unknown_input")

    def test_requested_duration_cannot_be_silently_shortened(self) -> None:
        proposal = copy.deepcopy(self.data["proposal"])
        proposal["decisions"][0]["values"]["duration_s"] = 8
        self.refused(proposal, "duration_mismatch")
