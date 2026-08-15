"""BOOT-1 bootstrap surface tests (clean-room, idempotence, fail-closed, security)."""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RUNTIME_DEFAULT = "/Users/king/Downloads/Additional/Runtime"
HAS_RUNTIME = Path(RUNTIME_DEFAULT).is_dir()


class BootstrapSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ.pop("CPCS_FROZEN_RUNTIME_PATH", None)

    def tearDown(self):
        self.tmp.cleanup()

    def _bootstrap(self, arguments=None):
        from lab.application.bootstrap import bootstrap
        return bootstrap(arguments or {}, self.root)

    def test_missing_runtime_fail_closed(self):
        result = self._bootstrap()
        self.assertEqual(result["status"], "NOT_READY")
        self.assertTrue(result["remediation"])
        self.assertFalse(result["fake_backend_used"])
        self.assertFalse(result["wrote_config"])
        from lab.application.bootstrap import config_path
        self.assertFalse(config_path(self.root).exists(),
                         "no invalid partial configuration written")

    def test_invalid_runtime_fail_closed(self):
        fake_runtime = self.root / "fake_runtime"
        fake_runtime.mkdir()
        (fake_runtime / "not_a_real_runtime.txt").write_text("nope")
        result = self._bootstrap({"runtime": str(fake_runtime)})
        self.assertEqual(result["status"], "NOT_READY")
        self.assertIn("missing required frozen artifacts", result["reason"])

    def test_security_no_secrets(self):
        result = self._bootstrap({"runtime": "/some/valid/path"})
        # with an invalid path no config is written; test the writer directly
        from lab.application.bootstrap import write_local_config, config_path
        write_local_config(self.root, "/some/valid/path", {
            "architecture_freeze_identity": "arch-1234",
            "retrieval_runtime_freeze_identity": "retr-5678"})
        cfg = config_path(self.root)
        payload = json.loads(cfg.read_text())
        forbidden = ("key", "token", "secret", "password", "credential", "cookie")
        self.assertFalse(any(k in payload for k in forbidden))
        self.assertEqual(set(payload), {
            "schema", "runtime_path", "architecture_freeze_identity",
            "retrieval_runtime_freeze_identity", "bootstrap_version",
            "bootstrapped_at"})
        mode = stat.S_IMODE(cfg.stat().st_mode)
        self.assertEqual(mode, 0o600)

    @unittest.skipUnless(HAS_RUNTIME, "frozen runtime unavailable")
    def test_valid_first_run_and_idempotence(self):
        result = self._bootstrap({"runtime": RUNTIME_DEFAULT})
        self.assertEqual(result["status"], "READY")
        self.assertTrue(result["wrote_config"])
        self.assertEqual(result["doctor"]["status"], "READY")
        self.assertFalse(result["fake_backend_used"])
        self.assertFalse(result["provider_credentials_required"])
        # idempotence
        result2 = self._bootstrap({"runtime": RUNTIME_DEFAULT})
        self.assertEqual(result2["status"], "READY")
        self.assertTrue(result2["idempotent"])
        self.assertIsNone(result2["wrote_config"])
        self.assertEqual(result2["identities"], result["identities"])
        # resolution from local config (no env, no argument)
        result3 = self._bootstrap({})
        self.assertEqual(result3["resolution_source"], "local_config")
        self.assertEqual(result3["identities"], result["identities"])

    @unittest.skipUnless(HAS_RUNTIME, "frozen runtime unavailable")
    def test_cli_bootstrap_doctor_and_mcp_first_prompt(self):
        # A: real CLI first run in the clean room
        env = dict(os.environ)
        env.pop("CPCS_FROZEN_RUNTIME_PATH", None)
        env["PYTHONPATH"] = f"{REPO}:{env.get('PYTHONPATH', '')}"
        input_file = self.root / "bootstrap_input.json"
        input_file.write_text(json.dumps({"runtime": RUNTIME_DEFAULT}))
        env["CPCS_BOOTSTRAP_CONFIG_OVERRIDE"] = str(self.root / "cpcs_runtime.json")
        bootstrap_out = subprocess.run(
            [sys.executable, "-m", "lab.application.cli", "bootstrap",
             "--role", "operator",
             "--input", str(input_file)],
            cwd=REPO, capture_output=True, text=True, env=env)
        self.assertEqual(bootstrap_out.returncode, 0, bootstrap_out.stderr)
        bootstrap_resp = json.loads(bootstrap_out.stdout)
        self.assertEqual(bootstrap_resp["status"], "success")
        self.assertEqual(bootstrap_resp["result"]["status"], "READY")
        # doctor through the same clean room
        doctor_env = {**env}
        doctor_env.pop("CPCS_FROZEN_RUNTIME_PATH", None)
        doctor_input = self.root / "doctor_input.json"
        doctor_input.write_text("{}")
        doctor_out = subprocess.run(
            [sys.executable, "-m", "lab.application.cli", "doctor",
             "--input", str(doctor_input)],
            cwd=REPO, capture_output=True, text=True, env=doctor_env)
        self.assertEqual(doctor_out.returncode, 0, doctor_out.stderr)
        doctor_resp = json.loads(doctor_out.stdout)
        self.assertEqual(doctor_resp["result"]["status"], "READY")
        # real MCP: initialize + tools/list + one-sentence FAST request
        mcp = subprocess.Popen(
            [sys.executable, "-m", "lab.application.mcp"],
            cwd=REPO, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1,
            env=doctor_env)
        def call(msg):
            mcp.stdin.write(json.dumps(msg) + "\n")
            mcp.stdin.flush()
            return json.loads(mcp.stdout.readline())
        init = call({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertIn("result", init)
        tools = call({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertIn("cpcs.guided.start",
                      {t["name"] for t in tools["result"]["tools"]})
        start = call({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                      "params": {"name": "cpcs.guided.start",
                                 "arguments": {"intent_text": (
                                     "Person walks through a quiet hallway. "
                                     "Just make me the prompt.")}}})
        self.assertEqual(start["result"]["structuredContent"]["status"], "success")
        result = start["result"]["structuredContent"]["result"]
        self.assertEqual(result["interaction_mode"], "FAST")
        finish = call({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                       "params": {"name": "cpcs.guided.finish",
                                  "arguments": {"session_id": result["session_id"]}}})
        final = finish["result"]["structuredContent"]["result"]
        self.assertEqual(final["status"], "COMPLETED")
        self.assertTrue(final["final_prompt_package"]["prompt"])
        mcp.stdin.close()
        mcp.wait(timeout=60)


if __name__ == "__main__":
    unittest.main()
