from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from lab.application.clients import advanced_score, guided_score
from lab.application.contracts import validate_application_configuration
from lab.application.http import make_handler
from lab.application.mcp import handle_message
from lab.application.service import (
    REQUEST_SCHEMA,
    authorization_request_hash,
    invoke,
    list_operations,
)
from lab.compiler.build import make_build_request
from lab.compiler.profiles import REPO_ROOT
from lab.second_brain.src.intent import build_intent_context


def authority_snapshot(root: Path = REPO_ROOT) -> dict[str, bytes]:
    paths = [root / "lab" / "concepts.jsonl"]
    sb = root / "lab" / "second_brain"
    for tier in ("curated", "immutable", "derived", "staging"):
        paths.extend(path for path in (sb / tier).rglob("*") if path.is_file())
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(paths)
    }


def app_request(operation: str, arguments: dict | None = None) -> dict:
    return {
        "schema": REQUEST_SCHEMA,
        "operation": operation,
        "arguments": arguments or {},
    }


class FacadeTests(unittest.TestCase):
    def _cli(self, operation: str, arguments: dict) -> dict:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "arguments.json"
            path.write_text(json.dumps(arguments), encoding="utf-8")
            completed = subprocess.run(
                [str(REPO_ROOT / "bin/cpcs"), operation, "--input", str(path)],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            return json.loads(completed.stdout)

    def _mcp(self, operation: str, arguments: dict) -> dict:
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {"name": operation, "arguments": arguments},
            },
        ]
        completed = subprocess.run(
            ["python3", "-m", "lab.application.mcp"],
            cwd=REPO_ROOT,
            input="".join(json.dumps(row) + "\n" for row in messages),
            check=True,
            capture_output=True,
            text=True,
        )
        responses = [json.loads(line) for line in completed.stdout.splitlines()]
        call = next(row for row in responses if row.get("id") == 7)
        return call["result"]["structuredContent"]

    def _http(self, request: dict) -> dict:
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            body = json.dumps(request).encode("utf-8")
            call = urllib.request.Request(
                f"http://127.0.0.1:{server.server_address[1]}/v1/invoke",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(call, timeout=10) as response:
                return json.loads(response.read())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_configuration_status_replay_and_authority_safety(self) -> None:
        self.assertEqual(validate_application_configuration()["schemas"], 3)
        request = app_request("cpcs.status")
        before = authority_snapshot()
        first = invoke(copy.deepcopy(request))
        second = invoke(copy.deepcopy(request))
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "success")
        self.assertEqual(first["result"]["release_authority"], "local_working_not_production_qualified")
        self.assertEqual(before, authority_snapshot())

    def test_typed_knowledge_search_is_public_read_only_and_replay_stable(self) -> None:
        request = app_request(
            "cpcs.knowledge.search",
            {"query": "inverse kinematics target constraints", "maximum_hops": 5},
        )
        before = authority_snapshot()
        first = invoke(copy.deepcopy(request))
        second = invoke(copy.deepcopy(request))
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "success")
        self.assertEqual(first["result"]["schema"], "cpcs.knowledge_search/1.0")
        self.assertEqual(before, authority_snapshot())
        names = {row["name"] for row in list_operations("chat")}
        self.assertIn("cpcs.knowledge.search", names)

    def test_cli_mcp_http_and_in_process_return_the_same_contract(self) -> None:
        arguments = {"text": "Create a restrained scene where she realizes he is lying"}
        request = app_request("cpcs.intent.normalize", arguments)
        before = authority_snapshot()
        direct = invoke(copy.deepcopy(request))
        cli = self._cli("intent.normalize", arguments)
        mcp = self._mcp("cpcs.intent.normalize", arguments)
        http = self._http(request)
        self.assertEqual(direct, cli)
        self.assertEqual(direct, mcp)
        self.assertEqual(direct, http)
        self.assertEqual(before, authority_snapshot())

    def test_guided_and_advanced_clients_share_the_exact_score_kernel(self) -> None:
        text = "Create a restrained scene where she realizes he is lying"
        before = authority_snapshot()
        routed = build_intent_context(text, token_budget=12_000)
        assets = [
            {
                "asset_id": f"asset_required_{index}",
                "role": role,
                "content_hash": "sha256:" + "a" * 64,
                "rights_basis": "owner_authorized_test_fixture",
            }
            for index, role in enumerate(
                routed["normalized_intent"]["requirements"]["missing_inputs"]
            )
        ]
        guided = guided_score(text, assets=assets)
        advanced = advanced_score(routed, assets=assets)
        self.assertEqual(guided["status"], "success")
        self.assertEqual(advanced["status"], "success")
        self.assertEqual(guided["result"], advanced["result"])
        self.assertEqual(guided["result"]["score"]["score_status"], "ready")
        self.assertEqual(before, authority_snapshot())

    def test_build_payload_is_identical_across_all_transports(self) -> None:
        text = "Create a restrained scene where she realizes he is lying"
        routed = build_intent_context(text, token_budget=12_000)
        assets = [
            {
                "asset_id": f"asset_required_{index}",
                "role": role,
                "content_hash": "sha256:" + "a" * 64,
                "rights_basis": "owner_authorized_test_fixture",
            }
            for index, role in enumerate(
                routed["normalized_intent"]["requirements"]["missing_inputs"]
            )
        ]
        score_response = advanced_score(routed, assets=assets)
        score = score_response["result"]["score"]
        build_request = make_build_request(
            score, project_id="cpcs-test-project", seed=31
        )
        arguments = {"request": build_request}
        request = app_request("cpcs.build.compile", arguments)
        before = authority_snapshot()
        direct = invoke(copy.deepcopy(request))
        cli = self._cli("build.compile", arguments)
        mcp = self._mcp("cpcs.build.compile", arguments)
        http = self._http(request)
        self.assertEqual(direct, cli)
        self.assertEqual(direct, mcp)
        self.assertEqual(direct, http)
        self.assertEqual(len(direct["result"]["artifacts"]), 8)
        self.assertEqual(before, authority_snapshot())

    def test_chat_surface_cannot_discover_or_invoke_write_tools(self) -> None:
        chat_names = {row["name"] for row in list_operations("chat")}
        operator_names = {row["name"] for row in list_operations("operator")}
        curator_names = {row["name"] for row in list_operations("curator")}
        self.assertNotIn("cpcs.distill.run", chat_names)
        self.assertNotIn("cpcs.curate.promote", chat_names)
        self.assertIn("cpcs.distill.run", operator_names)
        self.assertNotIn("cpcs.curate.promote", operator_names)
        self.assertIn("cpcs.curate.promote", curator_names)
        status = invoke(app_request("cpcs.status"))
        self.assertNotIn(
            "cpcs.curate.promote", status["result"]["operations"]["available"]
        )
        before = authority_snapshot()
        denied = invoke(
            app_request(
                "cpcs.curate.promote",
                {
                    "run_id": "distill_missing",
                    "durable_ids": {},
                    "promoted_by": "test",
                    "review": {},
                },
            ),
            role="chat",
        )
        self.assertEqual(denied["error"]["code"], "permission_denied")
        self.assertEqual(before, authority_snapshot())

    def test_curator_authorization_is_bound_to_exact_operation_and_arguments(self) -> None:
        arguments = {
            "run_id": "distill_missing",
            "durable_ids": {},
            "promoted_by": "test",
            "review": {},
        }
        request = app_request("cpcs.curate.promote", arguments)
        before = authority_snapshot()
        missing = invoke(copy.deepcopy(request), role="curator")
        self.assertEqual(missing["error"]["code"], "permission_denied")
        request["authorization"] = {
            "schema": "cpcs.explicit_authorization/1.0",
            "authorization_id": "auth_test",
            "authorized_by": "owner-test",
            "operation": "cpcs.curate.promote",
            "request_hash": authorization_request_hash(
                "cpcs.curate.promote", {**arguments, "run_id": "different"}
            ),
            "reason": "test exact request binding",
        }
        mismatched = invoke(request, role="curator")
        self.assertEqual(mismatched["error"]["code"], "permission_denied")
        request["authorization"]["request_hash"] = authorization_request_hash(
            "cpcs.curate.promote", arguments
        )
        authorized = invoke(request, role="curator")
        self.assertEqual(authorized["error"]["code"], "invalid_request")
        self.assertIn("promotion review", authorized["error"]["message"])
        self.assertEqual(before, authority_snapshot())

    def test_ambiguous_facade_inputs_fail_closed(self) -> None:
        score = invoke(
            app_request(
                "cpcs.score.build",
                {"text": "Make a video", "intent_context": {}},
            )
        )
        reasoning = invoke(
            app_request(
                "cpcs.reason",
                {"goal": "Make a video", "request": {}},
            )
        )
        self.assertEqual(score["error"]["code"], "invalid_request")
        self.assertEqual(reasoning["error"]["code"], "invalid_request")
        malformed = invoke(
            {
                "schema": REQUEST_SCHEMA,
                "request_id": "bad",
                "operation": "not-a-cpcs-operation",
                "arguments": {},
            }
        )
        self.assertEqual(malformed["status"], "error")
        self.assertRegex(malformed["request_id"], r"^app_[0-9a-f]{24}$")
        self.assertEqual(malformed["operation"], "cpcs.invalid")

    def test_mcp_handshake_and_tool_catalog_are_protocol_shaped(self) -> None:
        initialized = handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        )
        self.assertEqual(initialized["result"]["serverInfo"]["name"], "cpcs")
        self.assertEqual(
            initialized["result"]["serverInfo"]["version"],
            "cpcs-application/1.13",
        )
        tools = handle_message(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )
        names = {row["name"] for row in tools["result"]["tools"]}
        self.assertIn("cpcs.score.build", names)
        self.assertIn("cpcs.knowledge.search", names)
        self.assertNotIn("cpcs.curate.promote", names)

    def test_transport_modules_contain_no_domain_implementation_imports(self) -> None:
        for relative in (
            "lab/application/cli.py",
            "lab/application/mcp.py",
            "lab/application/http.py",
            "lab/application/clients.py",
        ):
            text = (REPO_ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("from lab.compiler", text, relative)
            self.assertNotIn("from lab.second_brain.src.intent", text, relative)
            self.assertNotIn("from lab.second_brain.src.context", text, relative)
            self.assertNotIn("from lab.second_brain.src.query", text, relative)


if __name__ == "__main__":
    unittest.main()
