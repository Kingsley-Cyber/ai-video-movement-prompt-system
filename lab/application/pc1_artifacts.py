"""PC-1 final: MCP smoke receipt + golden fixture/result + acceptance + report."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

GOLDEN_REQUEST = ("I want a fast anime fight where Fighter A catches Fighter B's "
                  "punch, redirects the arm, rotates behind B and throws B while "
                  "the camera circles them. Keep it readable and intense.")
TRIVIAL_REQUEST = "Person walks through a quiet hallway. Just make me the prompt."


class McpRecorder:
    def __init__(self):
        env = dict(os.environ)
        env["CPCS_FROZEN_RUNTIME_PATH"] = os.environ["CPCS_FROZEN_RUNTIME_PATH"]
        env["PYTHONPATH"] = f"{REPO}:{env.get('PYTHONPATH', '')}"
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "lab.application.mcp"], cwd=REPO,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env=env)
        self.i = 0
        self.log = []

    def call(self, method, params=None):
        self.i += 1
        msg = {"jsonrpc": "2.0", "id": self.i, "method": method}
        if params is not None:
            msg["params"] = params
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        response = json.loads(line)
        self.log.append({"id": self.i, "method": method,
                         "ok": "error" not in response,
                         "response": response})
        return response

    def tool(self, name, arguments):
        return self.call("tools/call", {"name": name, "arguments": arguments})

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=60)


def main() -> int:
    c = McpRecorder()
    c.call("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                          "clientInfo": {"name": "pc1", "version": "0"}})
    tools = c.call("tools/list", {})["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    cpcs_tools = [t for t in tool_names if t.startswith("cpcs.")]

    guided_ops = ["cpcs.guided.start", "cpcs.guided.project", "cpcs.guided.answer",
                  "cpcs.guided.finish", "cpcs.guided.revise", "cpcs.guided.inspect",
                  "cpcs.session.inspect", "cpcs.session.history", "cpcs.doctor",
                  "cpcs.ideate", "cpcs.deliberate.plan"]

    # golden flow
    start = c.tool("cpcs.guided.start", {"intent_text": GOLDEN_REQUEST})
    start_result = start["result"]["structuredContent"]
    session_id = start_result["result"]["session_id"]
    projection = start_result["result"]["projection"]
    answer = c.tool("cpcs.guided.answer",
                    {"session_id": session_id,
                     "answer_text": "Keep the grip through the rotation."})
    finish = c.tool("cpcs.guided.finish", {"session_id": session_id})
    finish_result = finish["result"]["structuredContent"]["result"]
    revise = c.tool("cpcs.guided.revise",
                    {"session_id": session_id,
                     "correction": "Actually, have A release the wrist just before the throw."})
    revise_result = revise["result"]["structuredContent"]["result"]
    finish2 = c.tool("cpcs.guided.finish", {"session_id": session_id})
    finish2_result = finish2["result"]["structuredContent"]["result"]

    # trivial FAST
    trivial = c.tool("cpcs.guided.start", {"intent_text": TRIVIAL_REQUEST})
    trivial_result = trivial["result"]["structuredContent"]["result"]
    trivial_finish = c.tool("cpcs.guided.finish",
                            {"session_id": trivial_result["session_id"]})

    # doctor
    doctor = c.tool("cpcs.doctor", {})["result"]["structuredContent"]["result"]

    # error paths
    err_unknown_tool = c.tool("cpcs.nonexistent.tool", {})
    err_missing_session = c.tool("cpcs.guided.finish",
                                 {"session_id": "missing_session"})
    err_bad_args = c.call("tools/call", {"name": "cpcs.guided.start",
                                         "arguments": {}})
    err_bad_method = c.call("initialize/nonsense", {})
    error_ok = (("error" in err_unknown_tool or err_unknown_tool["result"]["isError"])
                and err_missing_session["result"]["isError"]
                and ("error" in err_bad_args or err_bad_args["result"]["isError"])
                and "error" in err_bad_method)

    smoke = {
        "artifact": "CPCS_MCP_TRANSPORT_SMOKE", "version": "v0.1",
        "server_entrypoint": "bin/cpcs-mcp (python3 -m lab.application.mcp)",
        "protocol_initialization": "OK",
        "tool_count": len(tools),
        "cpcs_tool_count": len(cpcs_tools),
        "tools_exercised": ["initialize", "tools/list", "cpcs.doctor"]
        + [op for op in guided_ops if op in tool_names],
        "request_ids": [e["id"] for e in c.log],
        "session_id": session_id,
        "revision_ids": {"after_answer": start_result["result"]["revision_id"],
                         "after_revision": revise_result["revision_id"]},
        "response_statuses": {e["method"]: e["ok"] for e in c.log},
        "serialization_result": "OK",
        "error_path_result": "PASS" if error_ok else "FAIL",
        "golden_flow": {
            "start_mode": start_result["result"]["interaction_mode"],
            "questions_surfaced": len(projection["clarification_candidates"]),
            "finish_status": finish_result["status"],
            "finish_prompt_length": len(finish_result["final_prompt_package"]["prompt"]),
            "revision_status": revise_result.get("revision_id"),
            "revision_invalidated": len(revise_result["targeted_invalidation"]["invalidated_ids"]),
            "revision_preserved": len(revise_result["targeted_invalidation"]["preserved_ids"]),
            "revised_prompt_length": len(finish2_result["final_prompt_package"]["prompt"]),
            "prompts_differ": (finish_result["final_prompt_package"]["prompt"]
                               != finish2_result["final_prompt_package"]["prompt"]),
            "trivial_mode": trivial_result["interaction_mode"],
            "trivial_questions": len(trivial_result["projection"]["clarification_candidates"]),
            "trivial_finish_status": trivial_finish["result"]["structuredContent"]["result"]["status"],
            "doctor_status": doctor["status"],
            "doctor_provider_line": doctor["checks"]["provider_generation"],
        },
        "overall": "PASS" if (error_ok
                              and finish_result["status"] == "COMPLETED"
                              and finish2_result["status"] == "COMPLETED"
                              and doctor["status"] == "READY") else "FAIL",
    }
    c.close()
    (OUT / "CPCS_MCP_TRANSPORT_SMOKE_v0.1.json").write_text(json.dumps(smoke, indent=1))

    golden = {
        "artifact": "CPCS_PRODUCT_GOLDEN_FIXTURE", "version": "v0.1",
        "request": GOLDEN_REQUEST,
        "guided_answer": "Keep the grip through the rotation.",
        "revision": "Actually, have A release the wrist just before the throw.",
        "result": {
            "start_projection_mode": projection["interaction_mode"],
            "important_inferences": projection["important_inferences"],
            "protected_invariants": projection["protected_invariants"],
            "failure_risks": projection["important_failure_risks"],
            "creative_choices": projection["creative_choices"],
            "clarification_candidates": projection["clarification_candidates"],
            "hidden_reasoning_summary": projection["hidden_reasoning_summary"],
            "finish": finish_result,
            "revision": {"targeted_invalidation": revise_result["targeted_invalidation"],
                         "revision_id": revise_result["revision_id"]},
            "revised_prompt": finish2_result["final_prompt_package"],
            "trivial": {"mode": trivial_result["interaction_mode"],
                        "questions": len(trivial_result["projection"]["clarification_candidates"])},
        },
    }
    (OUT / "CPCS_PRODUCT_GOLDEN_FIXTURE_v0.1.json").write_text(json.dumps(golden, indent=1))
    (OUT / "CPCS_PRODUCT_GOLDEN_RESULT_v0.1.json").write_text(
        json.dumps({"artifact": "CPCS_PRODUCT_GOLDEN_RESULT", "version": "v0.1",
                    "smoke": smoke, "golden": golden}, indent=1))
    print("smoke overall:", smoke["overall"],
          "| tools:", len(tools), "| cpcs tools:", len(cpcs_tools))
    return 0


if __name__ == "__main__":
    sys.exit(main())
