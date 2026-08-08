from __future__ import annotations

import copy
import json
import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from lab.application.mcp import handle_message
from lab.second_brain.src import research_delta_patch as patch_runtime
from lab.application.service import (
    REQUEST_SCHEMA,
    authorization_request_hash,
    invoke,
    list_operations,
)
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


def _authority_snapshot(root: Path) -> dict[str, bytes]:
    paths = [root / "lab" / "concepts.jsonl"]
    second_brain = root / "lab" / "second_brain"
    for tier in ("curated", "immutable", "staging", "derived"):
        directory = second_brain / tier
        if directory.exists():
            paths.extend(path for path in directory.rglob("*") if path.is_file())
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(paths)
    }


def _call(
    root: Path,
    operation: str,
    arguments: dict,
    *,
    role: str = "operator",
    authorize: bool = False,
) -> dict:
    tool_arguments = copy.deepcopy(arguments)
    if authorize:
        tool_arguments["_cpcs_authorization"] = {
            "schema": "cpcs.explicit_authorization/1.0",
            "authorization_id": "auth_research_delta_patch_fixture",
            "authorized_by": "fixture-owner",
            "operation": operation,
            "request_hash": authorization_request_hash(operation, arguments),
            "reason": "Qualify this exact isolated fixture patch.",
        }
    response = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {"name": operation, "arguments": tool_arguments},
        },
        role=role,
        root=root,
    )
    assert response is not None
    return response["result"]["structuredContent"]


def _run_git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_fixture_root(base: Path) -> Path:
    root = _fixture_root(base)
    verification = root / "lab" / "verification"
    (verification / "tests").mkdir(parents=True, exist_ok=True)
    (verification / "verify.py").write_text(
        '"""Fixture verifier."""\n', encoding="utf-8"
    )
    (verification / "tests" / "test_verify.py").write_text(
        "import unittest\n\n"
        "class VerificationFixtureTests(unittest.TestCase):\n"
        "    def test_fixture(self):\n"
        "        self.assertTrue(True)\n",
        encoding="utf-8",
    )
    scripts = root / "lab" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "validate_repo.py").write_text(
        'print("FIXTURE GATE GREEN")\n', encoding="utf-8"
    )
    (root / ".gitignore").write_text(
        "work/\n__pycache__/\n*.pyc\n", encoding="utf-8"
    )
    _run_git(root, "init", "-q")
    _run_git(root, "config", "user.name", "CPCS Fixture")
    _run_git(root, "config", "user.email", "fixture@example.invalid")
    _run_git(root, "add", ".")
    _run_git(root, "commit", "-q", "-m", "fixture baseline")
    return root


def _patch_request(delta: dict, patch_text: str) -> dict:
    proposal = delta["implementation_proposals"][0]
    return {
        "schema": "cpcs.research_delta_patch_request/1.0",
        "delta_id": delta["delta_id"],
        "implementation_proposal_id": proposal["proposal_id"],
        "patch_format": "unified_diff",
        "patch_text": patch_text,
        "patch_sha256": "sha256:"
        + hashlib.sha256(patch_text.encode("utf-8")).hexdigest(),
        "prepared_by": "fixture-owner",
        "prepared_at": "2026-08-05T12:03:00Z",
        "rationale": "Exercise the approved verification owner with a harmless source-bound marker.",
    }


def _registration(source: Path) -> dict:
    return {
        "source_kind": "authorized_folder",
        "folder": str(source),
        "research_goal": "decimal spatial movement for controlled Laban direction",
        "rights_basis": "owner_authorized_test_fixture",
        "registered_at": "2026-08-05T12:00:00Z",
        "extractor": {
            "agent": "fake-mcp-semantic-worker",
            "model": "fake-structured-extractor-1",
            "prompt_hash": "sha256:" + "b" * 64,
        },
    }


def _claim_result(packet: dict) -> dict:
    passage = packet["passages"][0]
    return {
        "packet_id": packet["packet_id"],
        "candidates": [
            {
                "candidate_key": "decimal_spatial_claim",
                "proposal_type": "claim",
                "suggested_id": "claim_decimal_spatial_precision",
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
        "no_candidate": None,
    }


def _delta_request(session_id: str, candidate_id: str) -> dict:
    return {
        "schema": "cpcs.research_delta_request/1.0",
        "session_id": session_id,
        "objective": "Assess how decimal spatial direction should affect controlled video prompts.",
        "planned_at": "2026-08-05T12:02:00Z",
        "claims": [
            {
                "candidate_id": candidate_id,
                "knowledge_class": "project_specific_synthesis",
                "change_class": "verification_affecting",
                "scope": {
                    "providers": ["twelvelabs"],
                    "models": ["pegasus-1.2"],
                    "domains": ["motion_direction"],
                    "tasks": ["reference_video_analysis"],
                },
                "limitations": [
                    "The claim does not establish measured 3D movement or provider causality."
                ],
                "implementation_targets": ["verification_rule"],
            }
        ],
    }


class ResearchDeltaSurfaceTests(unittest.TestCase):
    def _completed_session(self, root: Path, source: Path) -> tuple[str, str]:
        registered = _call(
            root, "cpcs.research.source.register", _registration(source)
        )
        self.assertEqual(registered["status"], "success")
        session_id = registered["result"]["session_id"]
        packet_list = _call(
            root, "cpcs.research.packet.list", {"session_id": session_id}
        )
        packet_id = packet_list["result"]["packets"][0]["packet_id"]
        packet = _call(
            root,
            "cpcs.research.packet.read",
            {"session_id": session_id, "packet_id": packet_id},
        )["result"]["packet"]
        submitted = _call(
            root,
            "cpcs.research.extraction.submit",
            {
                "session_id": session_id,
                "packet_result": _claim_result(packet),
                "submitted_at": "2026-08-05T12:01:00Z",
            },
        )
        self.assertEqual(submitted["result"]["state"], "proposals_ready")
        proposal_list = _call(
            root, "cpcs.research.proposals.list", {"session_id": session_id}
        )
        candidate_id = proposal_list["result"]["proposals"][0]["candidate_id"]
        return session_id, candidate_id

    def test_public_delta_plan_replays_and_preserves_every_authority_tier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = _fixture_root(base / "fixture")
            source = base / "research"
            source.mkdir()
            (source / "motion.md").write_text(
                "# Decimal movement\n\n"
                "A proposed prompt experiment uses decimal waypoints to represent small "
                "changes in a directed hand path. It remains an interpreted directing claim.\n",
                encoding="utf-8",
            )
            session_id, candidate_id = self._completed_session(root, source)
            authority_before = _authority_snapshot(root)
            request = _delta_request(session_id, candidate_id)

            prepared = _call(
                root, "cpcs.research.delta.prepare", {"request": request}
            )
            replay = _call(
                root, "cpcs.research.delta.prepare", {"request": request}
            )
            self.assertEqual(prepared, replay)
            self.assertEqual(prepared["status"], "success")
            plan = prepared["result"]
            self.assertEqual(plan["authority"]["code"], "unchanged")
            self.assertEqual(plan["authority"]["curated"], "unchanged")
            self.assertEqual(
                plan["operational_claims"][0]["current_owner"],
                "lab/second_brain/curated/claims.jsonl",
            )
            self.assertEqual(
                plan["implementation_proposals"][0]["current_owner"],
                "lab/verification/verify.py",
            )
            self.assertEqual(
                plan["implementation_proposals"][0]["patch_boundary"]["status"],
                "proposal_only_requires_explicit_owner_authorization",
            )
            self.assertTrue(plan["impact_paths"][0]["path_hash"].startswith("sha256:"))
            source_refs = plan["operational_claims"][0]["source_refs"]
            self.assertEqual(len(source_refs), 1)
            self.assertNotEqual(source_refs[0]["content_hash"], "sha256:" + "0" * 64)

            inspected = _call(
                root,
                "cpcs.research.delta.inspect",
                {"delta_id": plan["delta_id"]},
            )
            self.assertEqual(inspected["result"], plan)
            self.assertEqual(_authority_snapshot(root), authority_before)

            plan_path = (
                root
                / "work"
                / "application"
                / "research_deltas"
                / plan["delta_id"]
                / "plan.json"
            )
            self.assertEqual(plan_path.stat().st_mode & 0o777, 0o600)

    def test_delta_contract_rejects_open_fields_unsafe_scope_and_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = _fixture_root(base / "fixture")
            source = base / "research"
            source.mkdir()
            (source / "motion.md").write_text(
                "# Movement\n\nDecimal positions are a prompt hypothesis for testing.\n",
                encoding="utf-8",
            )
            session_id, candidate_id = self._completed_session(root, source)
            request = _delta_request(session_id, candidate_id)

            open_request = copy.deepcopy(request)
            open_request["claims"][0]["unexpected"] = True
            rejected_open = _call(
                root,
                "cpcs.research.delta.prepare",
                {"request": open_request},
            )
            self.assertEqual(rejected_open["status"], "error")
            self.assertIn(
                "Additional properties are not allowed",
                rejected_open["error"]["message"],
            )

            unsafe = copy.deepcopy(request)
            unsafe["claims"][0]["knowledge_class"] = "unverified"
            rejected_unsafe = _call(
                root, "cpcs.research.delta.prepare", {"request": unsafe}
            )
            self.assertEqual(rejected_unsafe["status"], "error")
            self.assertIn(
                "unverified research cannot create an implementation proposal",
                rejected_unsafe["error"]["message"],
            )

            prepared = _call(
                root, "cpcs.research.delta.prepare", {"request": request}
            )["result"]
            plan_path = (
                root
                / "work"
                / "application"
                / "research_deltas"
                / prepared["delta_id"]
                / "plan.json"
            )
            tampered = json.loads(plan_path.read_text(encoding="utf-8"))
            tampered["objective"] = "tampered objective"
            plan_path.write_text(json.dumps(tampered), encoding="utf-8")
            rejected_tamper = _call(
                root,
                "cpcs.research.delta.inspect",
                {"delta_id": prepared["delta_id"]},
            )
            self.assertEqual(rejected_tamper["status"], "error")
            self.assertIn("plan hash", rejected_tamper["error"]["message"])

    def test_delta_tools_are_operator_only_and_agent_visible(self) -> None:
        chat = {row["name"] for row in list_operations("chat")}
        operator = {row["name"]: row for row in list_operations("operator")}
        for name in (
            "cpcs.research.delta.prepare",
            "cpcs.research.delta.inspect",
        ):
            self.assertNotIn(name, chat)
            self.assertIn(name, operator)
            self.assertTrue(operator[name]["mcp_exposed"])
        self.assertEqual(
            operator["cpcs.research.delta.prepare"]["mutation_scope"],
            "operational",
        )

    def test_approved_patch_runs_real_isolated_git_gates_replays_and_discards(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = _git_fixture_root(base / "fixture")
            source = base / "research"
            source.mkdir()
            (source / "motion.md").write_text(
                "# Decimal movement\n\nA Pegasus interpretation proposes decimal movement verification.\n",
                encoding="utf-8",
            )
            session_id, candidate_id = self._completed_session(root, source)
            delta = _call(
                root,
                "cpcs.research.delta.prepare",
                {"request": _delta_request(session_id, candidate_id)},
            )["result"]
            self.assertEqual(delta["baseline"]["dirty_paths"], [])
            patch_text = (
                "diff --git a/lab/verification/verify.py b/lab/verification/verify.py\n"
                "--- a/lab/verification/verify.py\n"
                "+++ b/lab/verification/verify.py\n"
                "@@ -1 +1,2 @@\n"
                " \"\"\"Fixture verifier.\"\"\"\n"
                "+# Research Delta fixture marker; no authority write.\n"
            )
            request = _patch_request(delta, patch_text)
            authority_before = _authority_snapshot(root)
            prepared = _call(
                root,
                "cpcs.research.delta.patch.prepare",
                {"request": request},
            )
            self.assertEqual(prepared["status"], "success")
            execution_id = prepared["result"]["execution_id"]

            denied = invoke(
                {
                    "schema": REQUEST_SCHEMA,
                    "operation": "cpcs.research.delta.patch.execute",
                    "arguments": {"execution_id": execution_id},
                },
                role="operator",
                root=root,
            )
            self.assertEqual(denied["error"]["code"], "permission_denied")

            executed = _call(
                root,
                "cpcs.research.delta.patch.execute",
                {"execution_id": execution_id},
                role="curator",
                authorize=True,
            )
            self.assertEqual(executed["status"], "success")
            receipt = executed["result"]
            self.assertEqual(receipt["status"], "passed")
            self.assertEqual(len(receipt["commands"]), 2)
            self.assertEqual(receipt["authority"]["merge"], "not_performed")
            self.assertEqual(_authority_snapshot(root), authority_before)
            self.assertEqual(_run_git(root, "status", "--short"), "")

            replay = _call(
                root,
                "cpcs.research.delta.patch.execute",
                {"execution_id": execution_id},
                role="curator",
                authorize=True,
            )
            self.assertEqual(replay["result"], receipt)
            inspected = _call(
                root,
                "cpcs.research.delta.patch.inspect",
                {"execution_id": execution_id},
            )
            self.assertEqual(inspected["result"]["receipt"], receipt)

            log_path = (
                root
                / "work"
                / "application"
                / "research_delta_patches"
                / execution_id
                / "logs"
                / "command-00.stdout"
            )
            original_log = log_path.read_bytes()
            log_path.write_bytes(original_log + b"tampered")
            rejected_log = _call(
                root,
                "cpcs.research.delta.patch.inspect",
                {"execution_id": execution_id},
            )
            self.assertEqual(rejected_log["status"], "error")
            self.assertIn("log hash", rejected_log["error"]["message"])
            log_path.write_bytes(original_log)

            discarded = _call(
                root,
                "cpcs.research.delta.patch.discard",
                {"execution_id": execution_id},
                role="curator",
                authorize=True,
            )
            self.assertTrue(discarded["result"]["worktree_removed"])
            worktree = (
                root
                / "work"
                / "application"
                / "research_delta_patches"
                / execution_id
                / "worktree"
            )
            self.assertFalse(worktree.exists())
            self.assertTrue(worktree.with_name("receipt.json").is_file())
            cleanup_replay = _call(
                root,
                "cpcs.research.delta.patch.discard",
                {"execution_id": execution_id},
                role="curator",
                authorize=True,
            )
            self.assertEqual(cleanup_replay["result"], discarded["result"])

    def test_patch_contract_rejects_hash_drift_open_fields_and_out_of_scope_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = _git_fixture_root(base / "fixture")
            source = base / "research"
            source.mkdir()
            (source / "motion.md").write_text(
                "# Movement\n\nA source-located verification hypothesis.\n",
                encoding="utf-8",
            )
            session_id, candidate_id = self._completed_session(root, source)
            delta = _call(
                root,
                "cpcs.research.delta.prepare",
                {"request": _delta_request(session_id, candidate_id)},
            )["result"]
            unsafe_patch = (
                "diff --git a/README.md b/README.md\n"
                "--- a/README.md\n"
                "+++ b/README.md\n"
                "@@ -1 +1,2 @@\n"
                " fixture\n"
                "+unsafe\n"
            )
            request = _patch_request(delta, unsafe_patch)
            rejected = _call(
                root,
                "cpcs.research.delta.patch.prepare",
                {"request": request},
            )
            self.assertEqual(rejected["status"], "error")
            self.assertIn("outside the approved proposal", rejected["error"]["message"])

            open_request = copy.deepcopy(request)
            open_request["unexpected"] = True
            rejected_open = _call(
                root,
                "cpcs.research.delta.patch.prepare",
                {"request": open_request},
            )
            self.assertEqual(rejected_open["status"], "error")
            self.assertIn("Additional properties", rejected_open["error"]["message"])

            drift = copy.deepcopy(request)
            drift["patch_sha256"] = "sha256:" + "0" * 64
            rejected_drift = _call(
                root,
                "cpcs.research.delta.patch.prepare",
                {"request": drift},
            )
            self.assertEqual(rejected_drift["status"], "error")
            self.assertIn("exact patch bytes", rejected_drift["error"]["message"])

    def test_public_execute_recovers_a_hash_complete_interrupted_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = _git_fixture_root(base / "fixture")
            source = base / "research"
            source.mkdir()
            (source / "motion.md").write_text(
                "# Recovery\n\nA source-located Pegasus verification hypothesis.\n",
                encoding="utf-8",
            )
            session_id, candidate_id = self._completed_session(root, source)
            delta = _call(
                root,
                "cpcs.research.delta.prepare",
                {"request": _delta_request(session_id, candidate_id)},
            )["result"]
            patch_text = (
                "diff --git a/lab/verification/verify.py b/lab/verification/verify.py\n"
                "--- a/lab/verification/verify.py\n"
                "+++ b/lab/verification/verify.py\n"
                "@@ -1 +1,2 @@\n"
                " \"\"\"Fixture verifier.\"\"\"\n"
                "+# Recoverable Research Delta marker.\n"
            )
            prepared = _call(
                root,
                "cpcs.research.delta.patch.prepare",
                {"request": _patch_request(delta, patch_text)},
            )["result"]
            execution_id = prepared["execution_id"]
            execution = patch_runtime._load_execution(execution_id, root)
            execution_directory, _request, plan, proposal, state = execution
            worktree = patch_runtime._ensure_worktree(
                root, execution_directory, plan["baseline"]["repository_revision"]
            )
            patch_runtime._ensure_patch_applied(
                worktree,
                execution_directory / "patch.diff",
                state["patch_paths"],
            )
            first_command = patch_runtime._commands_for(proposal)[0]
            completed = patch_runtime._run(first_command, cwd=worktree)
            state["phase"] = "testing"
            state["next_command_index"] = 1
            state["command_results"] = [
                {
                    "index": 0,
                    "argv": first_command,
                    "exit_code": completed.returncode,
                    "stdout_hash": patch_runtime._write_log(
                        execution_directory, 0, "stdout", completed.stdout
                    ),
                    "stderr_hash": patch_runtime._write_log(
                        execution_directory, 0, "stderr", completed.stderr
                    ),
                }
            ]
            state = patch_runtime._hashed_state(state)
            patch_runtime._replace_json(execution_directory / "state.json", state)
            _run_git(root, "worktree", "remove", "--force", str(worktree))
            self.assertFalse(worktree.exists())

            recovered = _call(
                root,
                "cpcs.research.delta.patch.execute",
                {"execution_id": execution_id},
                role="curator",
                authorize=True,
            )
            self.assertEqual(recovered["result"]["status"], "passed")
            self.assertEqual(len(recovered["result"]["commands"]), 2)
            self.assertTrue(worktree.is_dir())

    def test_patch_tools_expose_prepare_and_inspect_but_gate_execute_and_discard(self) -> None:
        operator = {row["name"]: row for row in list_operations("operator")}
        curator = {row["name"]: row for row in list_operations("curator")}
        self.assertIn("cpcs.research.delta.patch.prepare", operator)
        self.assertIn("cpcs.research.delta.patch.inspect", operator)
        self.assertNotIn("cpcs.research.delta.patch.execute", operator)
        self.assertNotIn("cpcs.research.delta.patch.discard", operator)
        for name in (
            "cpcs.research.delta.patch.execute",
            "cpcs.research.delta.patch.discard",
        ):
            self.assertIn(name, curator)
            self.assertTrue(curator[name]["authorization_required"])


if __name__ == "__main__":
    unittest.main()
