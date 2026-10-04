"""Build manifests bind the executing compiler checkout, never the caller's data root."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lab.compiler.build import _repository_commit, compile_build, make_build_request
from lab.compiler.profiles import REPO_ROOT
from lab.compiler.tests.test_build import ready_score


def _head(path: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, check=True, capture_output=True, text=True
    ).stdout.strip()


def _data_root(base: Path) -> Path:
    root = base / "data"
    shutil.copytree(REPO_ROOT / "lab", root / "lab", ignore=shutil.ignore_patterns("__pycache__"))
    return root


class BuildCodeRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        score = ready_score("Make a casual phone video recommending this skincare product")
        cls.request = make_build_request(score, project_id="cpcs-test-project")
        cls.code_head = _head(REPO_ROOT)

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)

    def manifest(self, root: Path) -> dict:
        return json.loads(compile_build(self.request, root=root)["build_manifest.json"])

    def test_non_git_data_root_builds_and_binds_the_compiler_checkout(self) -> None:
        root = _data_root(self.base)
        # Stop Git discovery at the temporary base, so an enclosing checkout under TMPDIR cannot answer.
        with mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": str(self.base)}):
            probe = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
            self.assertNotEqual(probe.returncode, 0, "fixture data root must not resolve as a Git checkout")
            manifest = self.manifest(root)
        self.assertEqual(manifest["repository_commit"], self.code_head)

    def test_separate_git_data_root_does_not_replace_the_compiler_revision(self) -> None:
        root = _data_root(self.base)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(
            ["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid",
             "commit", "-qm", "Separate data repository"],
            cwd=root, check=True,
        )
        data_head = _head(root)
        self.assertNotEqual(data_head, self.code_head)
        manifest = self.manifest(root)
        self.assertEqual(manifest["repository_commit"], self.code_head)

    def test_compiler_outside_a_git_checkout_fails_closed(self) -> None:
        outside = self.base / "unpacked_compiler"
        outside.mkdir()
        with mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": str(self.base)}):
            with self.assertRaisesRegex(ValueError, "compiler code revision could not be resolved"):
                _repository_commit(outside)


if __name__ == "__main__":
    unittest.main()
