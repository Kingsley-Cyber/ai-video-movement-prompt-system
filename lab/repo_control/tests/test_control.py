from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from lab.repo_control.src.control import (
    RepoControlError,
    append_event,
    build_repository_map,
    check,
    impact,
    read_events,
    ready_work,
    rebuild,
    split_markdown_table_row,
)


ROOT = Path(__file__).resolve().parents[3]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fixture(base: Path) -> Path:
    root = base / "repo"
    root.mkdir()
    write(
        root / "AGENTS.md",
        """<?xml version="1.0" encoding="UTF-8"?>
<cpcs_repository_agent_contract version="test">
  <directory_contract>
    <directory path="/">root</directory>
    <directory path="lab/">lab</directory>
  </directory_contract>
</cpcs_repository_agent_contract>
""",
    )
    write(root / "lab/registry.yaml", "version: 1\n")
    write(root / "lab/application/AGENTS.md", "# Application owner\n")
    write(root / "lab/application/core.py", "def value():\n    return 3\n")
    write(
        root / "lab/application/service.py",
        "from lab.application.core import value\n",
    )
    write(
        root / "lab/application/tests/test_service.py",
        "from lab.application.service import value\n",
    )
    write(
        root / "ARCHITECTURE.md",
        """# Architecture

| ID | Requirement | Expected evidence | Observed evidence | Status | Impact | Dependency | Smallest remediation | Verifier |
|---|---|---|---|---|---|---|---|---|
| REQ-001 | Core | `lab/application/core.py` works | available | WORKING | base | none | none | `python test.py` |
| REQ-002 | Service | service works | partial | PARTIAL | public | REQ-001 | edit `lab/application/service.py` | `python test.py` |
""",
    )
    for name in ("repository_map", "implementation_event"):
        source = ROOT / f"lab/repo_control/schemas/{name}.schema.json"
        target = root / f"lab/repo_control/schemas/{name}.schema.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git", "-c", "user.name=test", "-c", "user.email=test@example.invalid",
            "commit", "-qm", "fixture",
        ],
        cwd=root,
        check=True,
    )
    return root


class RepoControlTests(unittest.TestCase):
    def test_architecture_row_parser_preserves_pipes_inside_code_spans(self) -> None:
        row = "| REQ-001 | Public path | `one|two|three` | observed | WORKING | impact | none | none | verifier |"
        columns = split_markdown_table_row(row)
        self.assertEqual(len(columns), 9)
        self.assertEqual(columns[2], "`one|two|three`")

    def test_map_replays_and_links_owners_imports_tests_and_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = fixture(Path(directory))
            first = build_repository_map(root)
            self.assertEqual(first, build_repository_map(root))
            edges = {
                (row["source"], row["target"], row["type"])
                for row in first["edges"]
            }
            self.assertIn(
                (
                    "file:lab/application/service.py",
                    "file:lab/application/core.py",
                    "imports",
                ),
                edges,
            )
            self.assertIn(
                (
                    "file:lab/application/tests/test_service.py",
                    "file:lab/application/service.py",
                    "tests",
                ),
                edges,
            )
            self.assertIn(
                (
                    "file:lab/application/core.py",
                    "owner:lab/application/AGENTS.md",
                    "governed_by",
                ),
                edges,
            )
            self.assertIn(
                ("requirement:REQ-002", "requirement:REQ-001", "depends_on"),
                edges,
            )
            self.assertIn(
                (
                    "requirement:REQ-002",
                    "file:lab/application/service.py",
                    "mentions",
                ),
                edges,
            )
            impact_result = impact(root, "lab/application/service.py")
            self.assertEqual(
                impact_result["affected_files"],
                [
                    "lab/application/core.py",
                    "lab/application/service.py",
                    "lab/application/tests/test_service.py",
                ],
            )
            self.assertEqual(
                impact_result["requirements"],
                ["REQ-001 Core", "REQ-002 Service"],
            )
            rebuild(root)
            self.assertEqual(check(root)["status"], "green")
            layer_map = root / "lab/repo_control/derived/REPOSITORY_LAYER_MAP.md"
            layer_text = layer_map.read_text(encoding="utf-8")
            self.assertIn("# CPCS Repository Layer Map", layer_text)
            self.assertIn("`lab/`", layer_text)
            self.assertIn("`lab/application/AGENTS.md`", layer_text)
            self.assertIn("REQ-002", layer_text)
            layer_map.write_text(layer_text + "tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(RepoControlError, "layer map is stale"):
                check(root)
            rebuild(root)
            write(root / "lab/application/core.py", "def value():\n    return 4\n")
            with self.assertRaisesRegex(RepoControlError, "stale"):
                check(root)

    def test_work_log_is_chained_transition_checked_and_drives_ready_view(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = fixture(Path(directory))
            first = append_event(
                root,
                work_id="work_req_002",
                requirement_id="REQ-002",
                event_type="started",
                actor="test-agent",
                summary="Start service slice.",
                files=["lab/application/service.py"],
                occurred_at="2026-08-07T12:00:00Z",
            )
            second = append_event(
                root,
                work_id="work_req_002",
                requirement_id="REQ-002",
                event_type="completed",
                actor="test-agent",
                summary="Service slice verified.",
                files=["lab/application/service.py"],
                verifications=[{
                    "command": "python test.py",
                    "exit_code": 0,
                    "output_sha256": "sha256:" + "1" * 64,
                }],
                occurred_at="2026-08-07T12:01:00Z",
            )
            self.assertEqual(second["parent_event_hash"], first["event_hash"])
            self.assertEqual(len(read_events(root)), 2)
            with self.assertRaisesRegex(RepoControlError, "invalid implementation transition"):
                append_event(
                    root,
                    work_id="work_req_002",
                    requirement_id="REQ-002",
                    event_type="checkpoint",
                    actor="test-agent",
                    summary="Illegal post-completion event.",
                )
            queue = ready_work(root)
            req_two = next(row for row in queue["ready"] if row["id"] == "REQ-002")
            self.assertFalse(req_two["active"])
            path = root / "lab/repo_control/implementation_events.jsonl"
            rows = path.read_text(encoding="utf-8").splitlines()
            tampered = json.loads(rows[0])
            tampered["summary"] = "tampered"
            rows[0] = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RepoControlError, "event hash mismatch"):
                read_events(root)


if __name__ == "__main__":
    unittest.main()
