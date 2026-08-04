from __future__ import annotations

import copy
import json
import shutil
import stat
import tempfile
import unittest
from pathlib import Path

from lab.application.mcp import handle_message
from lab.second_brain.src.validate import REPO_ROOT, ValidationFailure, validate_instance
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

            open_configuration = copy.deepcopy(registration)
            open_configuration["configuration"] = {"unknown_limit": 1}
            rejected_configuration = _call(
                root, "cpcs.research.source.register", open_configuration
            )
            self.assertEqual(rejected_configuration["status"], "error")
            self.assertIn(
                "configuration",
                rejected_configuration["error"]["message"],
            )
            self.assertIn(
                "not valid under any of the given schemas",
                rejected_configuration["error"]["message"],
            )

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
            open_packet_result = copy.deepcopy(submitted_arguments)
            open_packet_result["packet_result"]["unexpected"] = True
            rejected_open_result = _call(
                root, "cpcs.research.extraction.submit", open_packet_result
            )
            self.assertEqual(rejected_open_result["status"], "error")
            self.assertIn(
                "Additional properties are not allowed",
                rejected_open_result["error"]["message"],
            )
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

            session_directory = completed_path.parent
            semantic_path = session_directory / "semantic_response.json"
            semantic_bytes = semantic_path.read_bytes()
            tampered_response = json.loads(semantic_bytes)
            tampered_response["packet_results"][0]["candidates"][0][
                "candidate_key"
            ] = "tampered_aggregate_response"
            semantic_path.write_text(json.dumps(tampered_response), encoding="utf-8")
            rejected_response = _call(
                root,
                "cpcs.research.extraction.status",
                {"session_id": session_id},
            )
            self.assertEqual(rejected_response["status"], "error")
            self.assertIn(
                "captured semantic response hash does not match its content",
                rejected_response["error"]["message"],
            )
            semantic_path.write_bytes(semantic_bytes)

            session_path = session_directory / "session.json"
            session_bytes = session_path.read_bytes()
            tampered_session = json.loads(session_bytes)
            tampered_session["research_goal"] = "tampered session state"
            session_path.write_text(json.dumps(tampered_session), encoding="utf-8")
            rejected_session = _call(
                root,
                "cpcs.research.extraction.status",
                {"session_id": session_id},
            )
            self.assertEqual(rejected_session["status"], "error")
            self.assertIn(
                "research session hash does not match its content",
                rejected_session["error"]["message"],
            )
            session_path.write_bytes(session_bytes)

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
            self.assertEqual(_curated_snapshot(root), curated_before)
            with self.assertRaises(ValidationFailure):
                validate_instance(
                    "research_session_contract",
                    {**prepared["result"], "unexpected": True},
                    root,
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
            self.assertNotIn("cpcs.distill.prepare", tool_names)
            self.assertNotIn("cpcs.distill.run", tool_names)

            submit_tool = next(
                row
                for row in tools["result"]["tools"]
                if row["name"] == "cpcs.research.extraction.submit"
            )
            self.assertFalse(
                submit_tool["inputSchema"]["properties"]["packet_result"][
                    "additionalProperties"
                ]
            )

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

    def test_partial_packet_capture_tampering_fails_before_assembly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = _fixture_root(base / "fixture")
            source = base / "research"
            source.mkdir()
            (source / "movement.md").write_text(
                "# First movement\n\nDecimal spatial changes preserve direction.\n\n"
                "# Second movement\n\nBound flow can constrain the next gesture.\n",
                encoding="utf-8",
            )
            registration = _registration(source)
            registration["configuration"] = {"max_passages_per_packet": 1}
            registered = _call(
                root, "cpcs.research.source.register", registration
            )
            session_id = registered["result"]["session_id"]
            packets = _call(
                root,
                "cpcs.research.packet.list",
                {"session_id": session_id},
            )["result"]["packets"]
            self.assertGreaterEqual(len(packets), 2)
            first_packet = _call(
                root,
                "cpcs.research.packet.read",
                {"session_id": session_id, "packet_id": packets[0]["packet_id"]},
            )["result"]["packet"]
            second_packet = _call(
                root,
                "cpcs.research.packet.read",
                {"session_id": session_id, "packet_id": packets[1]["packet_id"]},
            )["result"]["packet"]
            first_submit = _call(
                root,
                "cpcs.research.extraction.submit",
                {
                    "session_id": session_id,
                    "packet_result": _claim_result(first_packet, "first"),
                    "submitted_at": "2026-08-04T12:01:00Z",
                },
            )
            self.assertEqual(first_submit["result"]["state"], "extracting")

            capture_path = (
                root
                / "work"
                / "application"
                / "research_sessions"
                / session_id
                / "packet_results"
                / f"{first_packet['packet_id']}.json"
            )
            capture = json.loads(capture_path.read_text(encoding="utf-8"))
            capture["packet_result"]["candidates"][0]["candidate_key"] = (
                "tampered_partial_capture"
            )
            capture_path.write_text(json.dumps(capture), encoding="utf-8")

            rejected = _call(
                root,
                "cpcs.research.extraction.submit",
                {
                    "session_id": session_id,
                    "packet_result": _claim_result(second_packet, "second"),
                    "submitted_at": "2026-08-04T12:02:00Z",
                },
            )
            self.assertEqual(rejected["status"], "error")
            self.assertIn(
                "response hash does not match its content",
                rejected["error"]["message"],
            )
            self.assertFalse(
                (
                    root
                    / "work"
                    / "application"
                    / "research_sessions"
                    / session_id
                    / "completed_bundle.json"
                ).exists()
            )

    def test_mcp_catalog_and_invocation_apply_the_same_role_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _fixture_root(Path(directory) / "fixture")
            catalogs = {}
            for role in ("chat", "operator", "curator"):
                response = handle_message(
                    {"jsonrpc": "2.0", "id": 8, "method": "tools/list"},
                    role=role,
                    root=root,
                )
                assert response is not None
                catalogs[role] = {
                    row["name"] for row in response["result"]["tools"]
                }

            research_operations = {
                "cpcs.research.source.register",
                "cpcs.research.source.inspect",
                "cpcs.research.packet.list",
                "cpcs.research.packet.read",
                "cpcs.research.extraction.submit",
                "cpcs.research.extraction.status",
                "cpcs.research.coverage.inspect",
                "cpcs.research.proposals.list",
                "cpcs.research.proposals.validate",
                "cpcs.research.distillation.run",
                "cpcs.research.promotion.prepare",
            }
            self.assertTrue(research_operations.isdisjoint(catalogs["chat"]))
            self.assertTrue(research_operations <= catalogs["operator"])
            self.assertNotIn("cpcs.curate.promote", catalogs["operator"])
            self.assertIn("cpcs.curate.promote", catalogs["curator"])
            self.assertNotIn("cpcs.distill.prepare", catalogs["curator"])
            self.assertNotIn("cpcs.distill.run", catalogs["curator"])

            for operation in ("cpcs.distill.prepare", "cpcs.distill.run"):
                rejected = handle_message(
                    {
                        "jsonrpc": "2.0",
                        "id": 9,
                        "method": "tools/call",
                        "params": {"name": operation, "arguments": {}},
                    },
                    role="operator",
                    root=root,
                )
                assert rejected is not None
                self.assertEqual(rejected["error"]["code"], -32601)

            guessed_promotion = handle_message(
                {
                    "jsonrpc": "2.0",
                    "id": 10,
                    "method": "tools/call",
                    "params": {
                        "name": "cpcs.curate.promote",
                        "arguments": {},
                    },
                },
                role="operator",
                root=root,
            )
            assert guessed_promotion is not None
            self.assertEqual(guessed_promotion["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
