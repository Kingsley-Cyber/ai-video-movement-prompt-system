"""WP-8 — cpcs.knowledge.apply.inspect op + doctor line."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from lab.application.cpcs_guided_handlers import (
    cpcs_doctor,
    handler_knowledge_apply_inspect,
)
from lab.compiler.profiles import REPO_ROOT

RUNTIME = os.environ.get("CPCS_FROZEN_RUNTIME_PATH",
                         "/Users/king/Downloads/Additional/Runtime")
HAS_RUNTIME = Path(RUNTIME).is_dir()


class Ka1DoctorAndInspect(unittest.TestCase):

    def test_doctor_includes_knowledge_application_ok(self):
        result = cpcs_doctor(REPO_ROOT, runtime_path=RUNTIME)
        self.assertEqual(result["checks"]["knowledge_application"], "OK")
        self.assertIn("knowledge_application", result["checks"])

    def test_unknown_runtime_returns_typed_error_envelope(self):
        with mock.patch(
            "lab.application.cpcs_guided_handlers.frozen_knowledge_snapshot",
            side_effect=RuntimeError("CPCS_FROZEN_RUNTIME_PATH is not configured"),
        ):
            result = handler_knowledge_apply_inspect(
                {"intent_text": "A fighter performs a hip toss."}, REPO_ROOT)
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["reason"], "frozen_runtime_unavailable")
        self.assertTrue(result["detail"])


@unittest.skipUnless(HAS_RUNTIME, "CPCS_FROZEN_RUNTIME_PATH unavailable")
class RealMcpKa1(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        env = dict(os.environ)
        env["CPCS_FROZEN_RUNTIME_PATH"] = RUNTIME
        env["PYTHONPATH"] = f"{REPO_ROOT}:{env.get('PYTHONPATH', '')}"
        cls.proc = subprocess.Popen(
            [sys.executable, "-m", "lab.application.mcp"],
            cwd=REPO_ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
        cls.next_id = 1

    @classmethod
    def tearDownClass(cls):
        cls.proc.stdin.close()
        cls.proc.wait(timeout=60)

    def call(self, method, params=None):
        message = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        self.next_id += 1
        if params is not None:
            message["params"] = params
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("MCP server exited early: "
                               + self.proc.stderr.read()[:400])
        return json.loads(line)

    def test_tool_visible_in_tools_list(self):
        response = self.call("tools/list", {})
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertIn("cpcs.knowledge.apply.inspect", names)

    def test_inspect_returns_application_summary(self):
        response = self.call("tools/call", {
            "name": "cpcs.knowledge.apply.inspect",
            "arguments": {"intent_text": "A fighter performs a hip toss."},
        })
        content = response["result"]["content"][0]["text"]
        result = json.loads(content)
        self.assertIn("status", result)
        if result["status"] == "OK":
            self.assertTrue(result["set_hash"])
            self.assertIsInstance(result["packs"], list)
            self.assertIsInstance(result["decision_counts"], dict)


if __name__ == "__main__":
    unittest.main()
