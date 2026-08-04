from __future__ import annotations

import copy
import json
import shutil
import stat
import tempfile
import unittest
from pathlib import Path

from lab.application.mcp import handle_message
from lab.second_brain.src.validate import REPO_ROOT
from lab.second_brain.tests.helpers import concept, make_root


def _fixture_root(base: Path) -> Path:
    root = make_root(
        base,
        [concept("c_laban_effort", "Laban effort", "Laban Effort")],
    )
    shutil.copytree(
        REPO_ROOT / "lab" / "application" / "schemas",
        root / "lab" / "application" / "schemas",
    )
    shutil.copytree(REPO_ROOT / "lab" / "release", root / "lab" / "release")
    return root


def _curated_snapshot(root: Path) -> dict[str, bytes]:
    paths = [root / "lab" / "concepts.jsonl"]
    paths.extend(
        path
        for path in (root / "lab" / "second_brain" / "curated").rglob("*")
        if path.is_file()
    )
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(paths)}


def _call(root: Path, operation: str, arguments: dict) -> dict:
    response = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": operation, "arguments": copy.deepcopy(arguments)},
        },
        role="operator",
        root=root,
    )
    assert response is not None
    return response["result"]["structuredContent"]


def _registration(source: Path) -> dict:
    return {
        "source_kind": "authorized_folder",
        "folder": str(source),
        "research_goal": "decimal spatial movement for controlled Laban direction",
        "rights_basis": "owner_authorized_test_fixture",
        "registered_at": "2026-08-04T12:00:00Z",
        "extractor": {
            "agent": "fake-mcp-semantic-worker",
            "model": "fake-structured-extractor-1",
            "prompt_hash": "sha256:" + "b" * 64,
        },
    }


def _claim_result(packet: dict, suffix: str = "main") -> dict:
    passage = packet["passages"][0]
    return {
        "packet_id": packet["packet_id"],
        "candidates": [
            {
                "candidate_key": f"decimal_spatial_claim_{suffix}",
                "proposal_type": "claim",
                "suggested_id": f"claim_decimal_spatial_precision_{suffix}",
                "proposed_record": {
                    "concept_ids": ["c_laban_effort"],
                    "statement": (
                        "Decimal spatial waypoints can preserve small directed movement changes."
                    ),
                    "claim_kind": "operational",
                    "method_ids": [],
                    "supports_claim_ids": [],
                    "contradicts_claim_ids": [],
                    "epistemic_class": "interpreted",
                    "evidence_status": "unverified",
                    "confidence": 0.62,
                    "confidence_basis": "One source-located research passage.",
                    "limitations": [
                        "Provider response and causal benefit remain unqualified."
                    ],
                    "status": "ingested",
                    "sources": [
                        {
                            "ref": "placeholder://adapter-owned",
                            "locator": "placeholder",
                            "content_sha256": "sha256:" + "0" * 64,
                        }
                    ],
                },
                "evidence_refs": [
                    {
                        "chunk_id": passage["chunk_id"],
                        "claim": (
                            "The passage proposes decimal waypoints for preserving small movement changes."
                        ),
                    }
                ],
            }
        ],
    }


class ResearchExtractionSurfaceTests(unittest.TestCase):
    def test_fake_mcp_worker_reaches_staging_without_curated_or_graph_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = _fixture_root(base / "fixture")
            source = base / "research"
            source.mkdir()
            (source / "movement.md").write_text(
                "# Decimal spatial movement\n\n"
                "Decimal waypoints such as 0.125 and 0.375 preserve small changes in a "
                "directed hand path for later provider experiments.\n",
                encoding="utf-8",
            )
            curated_before = _curated_snapshot(root)
            registration = _registration(source)

            registered = _call(
                root, "cpcs.research.source.register", registration
            )
            replay = _call(root, "cpcs.research.source.register", registration)
            self.assertEqual(registered, replay)
            self.assertEqual(registered["status"], "success")
            session_id = registered["result"]["session_id"]
            self.assertEqual(registered["result"]["state"], "packets_ready")

            inspected = _call(
                root,
                "cpcs.research.source.inspect",
                {"session_id": session_id},
            )
            self.assertEqual(inspected["status"], "success")
            packets = _call(
                root,
                "cpcs.research.packet.list",
                {"session_id": session_id},
            )
            self.assertEqual(len(packets["result"]["packets"]), 1)
            packet_id = packets["result"]["packets"][0]["packet_id"]
            packet = _call(
                root,
                "cpcs.research.packet.read",
                {"session_id": session_id, "packet_id": packet_id},
            )["result"]["packet"]
            submitted_arguments = {
                "session_id": session_id,
                "packet_result": _claim_result(packet),
                "submitted_at": "2026-08-04T12:01:00Z",
            }
            submitted = _call(
                root, "cpcs.research.extraction.submit", submitted_arguments
            )
            submitted_replay = _call(
                root, "cpcs.research.extraction.submit", submitted_arguments
            )
            self.assertEqual(submitted, submitted_replay)
            self.assertEqual(submitted["result"]["state"], "proposals_ready")

            changed = copy.deepcopy(submitted_arguments)
            changed["packet_result"] = _claim_result(packet, "changed")
            collision = _call(
                root, "cpcs.research.extraction.submit", changed
            )
            self.assertEqual(collision["status"], "error")

            coverage = _call(
                root,
                "cpcs.research.coverage.inspect",
                {"session_id": session_id},
            )
            proposals = _call(
                root,
                "cpcs.research.proposals.list",
                {"session_id": session_id},
            )
            validation = _call(
                root,
                "cpcs.research.proposals.validate",
                {"session_id": session_id},
            )
            self.assertEqual(coverage["status"], "success")
            self.assertEqual(
                proposals["result"]["trust_class"],
                "untrusted_extraction_proposals",
            )
            self.assertTrue(validation["result"]["valid"])
            self.assertEqual(validation["result"]["authority_effect"], "none")
            self.assertEqual(_curated_snapshot(root), curated_before)

            completed_path = (
                root
                / "work"
                / "application"
                / "research_sessions"
                / session_id
                / "completed_bundle.json"
            )
            completed_bytes = completed_path.read_bytes()
            tampered_bundle = json.loads(completed_bytes)
            tampered_bundle["research_goal"] = "tampered after capture"
            completed_path.write_text(json.dumps(tampered_bundle), encoding="utf-8")
            tampered = _call(
                root,
                "cpcs.research.proposals.list",
                {"session_id": session_id},
            )
            self.assertEqual(tampered["status"], "error")
            self.assertIn("does not match content", tampered["error"]["message"])
            completed_path.write_bytes(completed_bytes)

            distilled = _call(
                root,
                "cpcs.research.distillation.run",
                {"session_id": session_id},
            )
            distilled_replay = _call(
                root,
                "cpcs.research.distillation.run",
                {"session_id": session_id},
            )
            self.assertEqual(distilled, distilled_replay)
            self.assertEqual(distilled["result"]["authority_effect"], "staging_only")
            self.assertEqual(_curated_snapshot(root), curated_before)
            registration_replay = _call(
                root, "cpcs.research.source.register", registration
            )
            self.assertEqual(registration_replay["result"]["state"], "distilled")
            self.assertEqual(
                registration_replay["result"]["distillation_run_id"],
                distilled["result"]["run"]["id"],
            )
            prepared = _call(
                root,
                "cpcs.research.promotion.prepare",
                {"session_id": session_id},
            )
            self.assertEqual(prepared["status"], "success")
            self.assertEqual(
                prepared["result"]["next_operation"], "cpcs.curate.promote"
            )

            session_path = (
                root
                / "work"
                / "application"
                / "research_sessions"
                / session_id
                / "session.json"
            )
            self.assertEqual(
                stat.S_IMODE(session_path.stat().st_mode),
                0o600,
            )
            tools = handle_message(
                {"jsonrpc": "2.0", "id": 8, "method": "tools/list"},
                role="operator",
                root=root,
            )
            assert tools is not None
            tool_names = {row["name"] for row in tools["result"]["tools"]}
            self.assertIn("cpcs.research.packet.read", tool_names)
            self.assertIn("cpcs.research.extraction.submit", tool_names)
            self.assertNotIn("cpcs.curate.promote", tool_names)

    def test_source_mutation_after_registration_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = _fixture_root(base / "fixture")
            source = base / "research"
            source.mkdir()
            research_file = source / "movement.md"
            research_file.write_text(
                "# Movement\n\nDecimal spatial changes are source evidence.\n",
                encoding="utf-8",
            )
            registered = _call(
                root,
                "cpcs.research.source.register",
                _registration(source),
            )
            session_id = registered["result"]["session_id"]
            packet_id = _call(
                root,
                "cpcs.research.packet.list",
                {"session_id": session_id},
            )["result"]["packets"][0]["packet_id"]
            packet = _call(
                root,
                "cpcs.research.packet.read",
                {"session_id": session_id, "packet_id": packet_id},
            )["result"]["packet"]
            research_file.write_text(
                "# Movement\n\nThe registered bytes changed after packet creation.\n",
                encoding="utf-8",
            )
            rejected = _call(
                root,
                "cpcs.research.extraction.submit",
                {
                    "session_id": session_id,
                    "packet_result": _claim_result(packet),
                    "submitted_at": "2026-08-04T12:01:00Z",
                },
            )
            self.assertEqual(rejected["status"], "error")
            self.assertIn("changed", rejected["error"]["message"])


if __name__ == "__main__":
    unittest.main()
