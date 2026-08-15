"""PC-1: real MCP transport smoke + golden product flow (frozen runtime required)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RUNTIME = os.environ.get("CPCS_FROZEN_RUNTIME_PATH",
                         "/Users/king/Downloads/Additional/Runtime")
HAS_RUNTIME = Path(RUNTIME).is_dir()

GOLDEN_REQUEST = ("I want a fast anime fight where Fighter A catches Fighter B's "
                  "punch, redirects the arm, rotates behind B and throws B while "
                  "the camera circles them. Keep it readable and intense.")
TRIVIAL_REQUEST = "Person walks through a quiet hallway. Just make me the prompt."


class McpClient:
    def __init__(self):
        env = dict(os.environ)
        env["CPCS_FROZEN_RUNTIME_PATH"] = RUNTIME
        env["PYTHONPATH"] = f"{REPO}:{env.get('PYTHONPATH', '')}"
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "lab.application.mcp"],
            cwd=REPO, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
        self.next_id = 1
        self.log = []

    def call(self, method: str, params=None) -> dict:
        req_id = self.next_id
        self.next_id += 1
        message = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            message["params"] = params
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            err = self.proc.stderr.read()
            raise RuntimeError(f"MCP server exited early: {err[:600]}")
        response = json.loads(line)
        self.log.append({"request": method, "id": req_id, "response": response})
        return response

    def tool(self, name: str, arguments: dict) -> dict:
        return self.call("tools/call", {"name": name, "arguments": arguments})

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=60)


@unittest.skipUnless(HAS_RUNTIME, "CPCS_FROZEN_RUNTIME_PATH unavailable")
class RealMcpGoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = McpClient()
        cls.client.call("initialize", {"protocolVersion": "2025-03-26",
                                       "capabilities": {},
                                       "clientInfo": {"name": "pc1-test",
                                                      "version": "0"}})
        tools = cls.client.call("tools/list", {})["result"]["tools"]
        cls.tool_names = {t["name"] for t in tools}
        cls.tool_count = len(tools)
        start = cls.client.tool("cpcs.guided.start",
                                {"intent_text": GOLDEN_REQUEST})
        cls.start_content = start["result"]["structuredContent"]["result"]
        cls.session_id = cls.start_content["session_id"]
        cls.initial_projection = cls.start_content["projection"]

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_real_mcp_initialize(self):
        self.assertGreaterEqual(self.tool_count, 20)
        self.assertTrue(self.tool_names)

    def test_real_mcp_tools_list(self):
        for op in ("cpcs.guided.start", "cpcs.guided.project", "cpcs.guided.answer",
                   "cpcs.guided.finish", "cpcs.guided.revise", "cpcs.guided.inspect",
                   "cpcs.session.inspect", "cpcs.session.history", "cpcs.doctor",
                   "cpcs.ideate", "cpcs.deliberate.plan"):
            self.assertIn(op, self.tool_names, f"{op} must be visible through MCP")
        self.assertNotIn("cpcs.retrieval.rrf", self.tool_names)

    def test_real_mcp_guided_start(self):
        content = self.start_content
        self.assertEqual(content["interaction_mode"], "GUIDED")
        projection = content["projection"]
        self.assertTrue(projection["hidden_reasoning_summary"]["hypothesis_count"] > 5)
        # user-facing projection must not dump raw reasoning volume
        self.assertLess(len(projection["important_inferences"]), 8)
        self.assertTrue(projection["clarification_candidates"])

    def test_real_mcp_guided_answer(self):
        r = self.client.tool("cpcs.guided.answer",
                             {"session_id": self.session_id,
                              "answer_text": "Keep the grip through the rotation."})
        self.assertEqual(r["result"]["structuredContent"]["status"], "success")
        result = r["result"]["structuredContent"]["result"]
        self.assertEqual(result["recorded_decision"]["decision_status"], "USER_RESOLVED")
        self.assertEqual(result["recorded_decision"]["authority_source"],
                         "USER_CORRECTION")

    def test_real_mcp_guided_finish(self):
        r = self.client.tool("cpcs.guided.finish", {"session_id": self.session_id})
        content = r["result"]["structuredContent"]["result"]
        self.assertEqual(content["status"], "COMPLETED")
        pkg = content["final_prompt_package"]
        self.assertIsNotNone(pkg)
        self.assertTrue(pkg["prompt"])
        self.assertTrue(pkg["hard_semantics_preserved"])
        self.assertEqual(content["questions_asked"], 0)
        type(self).final_prompt = pkg["prompt"]

    def test_real_mcp_guided_revision(self):
        r = self.client.tool("cpcs.guided.revise",
                             {"session_id": self.session_id,
                              "correction": ("Actually, have A release the wrist "
                                             "just before the throw.")})
        content = r["result"]["structuredContent"]["result"]
        self.assertGreaterEqual(content["revision_id"], 2)
        invalidation = content["targeted_invalidation"]
        self.assertTrue(invalidation["invalidated_ids"])
        self.assertTrue(invalidation["preserved_ids"])
        r2 = self.client.tool("cpcs.guided.finish", {"session_id": self.session_id})
        revised = r2["result"]["structuredContent"]["result"]
        self.assertEqual(revised["status"], "COMPLETED")
        self.assertNotEqual(revised["final_prompt_package"]["prompt"],
                            type(self).final_prompt)

    def test_real_mcp_session_history(self):
        r = self.client.tool("cpcs.session.history", {"session_id": self.session_id})
        content = r["result"]["structuredContent"]["result"]
        self.assertGreaterEqual(content["history_count"], 2)
        hashes = [h.get("state_hash") for h in content["revision_history"]]
        self.assertEqual(len(hashes), len(set(hashes)),
                         "revision history is immutable and distinct")

    def test_real_mcp_trivial_fast_completion(self):
        r = self.client.tool("cpcs.guided.start", {"intent_text": TRIVIAL_REQUEST})
        content = r["result"]["structuredContent"]["result"]
        self.assertEqual(content["interaction_mode"], "FAST")
        self.assertEqual(content["projection"]["clarification_candidates"], [])
        sid = content["session_id"]
        r2 = self.client.tool("cpcs.guided.finish", {"session_id": sid})
        self.assertEqual(r2["result"]["structuredContent"]["result"]["status"],
                         "COMPLETED")

    def test_real_mcp_doctor_ready(self):
        r = self.client.tool("cpcs.doctor", {})
        content = r["result"]["structuredContent"]["result"]
        self.assertEqual(content["status"], "READY")
        self.assertEqual(content["checks"]["provider_generation"].split(" ")[0],
                         "NOT")

    def test_real_mcp_error_paths(self):
        unknown = self.client.tool("cpcs.nonexistent.tool", {})
        self.assertTrue(unknown["error"]["code"] in (-32601, -32602))
        invalid = self.client.tool("cpcs.guided.finish", {"session_id": "missing_session"})
        self.assertTrue(invalid["result"]["isError"])
        missing = self.client.call("tools/call",
                                   {"name": "cpcs.guided.start", "arguments": {}})
        self.assertTrue(missing["result"]["isError"] or "error" in missing)
        bad_method = self.client.call("initialize/nonsense", {})
        self.assertIn("error", bad_method)


if __name__ == "__main__":
    unittest.main()
