from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import venv
import zipfile
from pathlib import Path

from lab.second_brain.src.validate import REPO_ROOT


class PackagingTests(unittest.TestCase):
    def test_wheel_contains_runtime_data_and_installs_the_cpcs_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            source.mkdir()
            for name in (
                "pyproject.toml",
                "setup.cfg",
                "MANIFEST.in",
                "README.md",
                "LICENSE",
                "AGENTS.md",
                "ARCHITECTURE.md",
                "CHANGELOG.md",
            ):
                shutil.copyfile(REPO_ROOT / name, source / name)
            shutil.copytree(
                REPO_ROOT / "lab",
                source / "lab",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            wheelhouse = base / "wheelhouse"
            completed = subprocess.run(
                [
                    "python3",
                    "-m",
                    "pip",
                    "wheel",
                    ".",
                    "--no-deps",
                    "--no-build-isolation",
                    "--wheel-dir",
                    str(wheelhouse),
                ],
                cwd=source,
                check=True,
                capture_output=True,
                text=True,
            )
            wheels = list(wheelhouse.glob("*.whl"))
            self.assertEqual(len(wheels), 1, completed.stdout + completed.stderr)
            with zipfile.ZipFile(wheels[0]) as archive:
                names = set(archive.namelist())
            required = {
                "lab/application/schemas/application_request.schema.json",
                "lab/release/policy.yaml",
                "lab/second_brain/curated/edges.jsonl",
                "lab/profiles/intent_routing.yaml",
                "lab/compiler/providers/veo_3_1.yaml",
            }
            self.assertTrue(required <= names, sorted(required - names))
            environment = base / "venv"
            venv.EnvBuilder(with_pip=True, system_site_packages=True).create(environment)
            executable = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            subprocess.run(
                [str(executable), "-m", "pip", "install", "--no-deps", str(wheels[0])],
                cwd=base,
                check=True,
                capture_output=True,
                text=True,
            )
            command = environment / ("Scripts/cpcs.exe" if os.name == "nt" else "bin/cpcs")
            status = subprocess.run(
                [str(command), "status"],
                cwd=base,
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(status.stdout)
            self.assertEqual(payload["status"], "success")
            self.assertEqual(payload["result"]["service_version"], "cpcs-application/1.0")


if __name__ == "__main__":
    unittest.main()
