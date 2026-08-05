from __future__ import annotations

import copy
import json
import os
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

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
            [str(REPO_ROOT / "bin/cpcs-mcp")],
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
        self.assertEqual(validate_application_configuration()["schemas"], 7)
        request = app_request("cpcs.status")
        before = authority_snapshot()
        first = invoke(copy.deepcopy(request))
        second = invoke(copy.deepcopy(request))
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "success")
        self.assertEqual(first["result"]["release_authority"], "local_working_not_production_qualified")
        self.assertEqual(before, authority_snapshot())

    def test_agent_brief_routes_pegasus_formats_and_secrets_across_transports(self) -> None:
        arguments = {
            "task": (
                "Analyze an authorized video with Pegasus, keep the API key safe, "
                "and return natural-language, YAML, JSON, and XML summaries"
            ),
            "role": "operator",
        }
        request = app_request("cpcs.agent.brief", arguments)
        fake_secret = "tlk_fake_agent_brief_secret_value"
        before = authority_snapshot()
        with mock.patch.dict(os.environ, {"TWELVE_LABS_API_KEY": fake_secret}):
            direct = invoke(copy.deepcopy(request))
            replay = invoke(copy.deepcopy(request))
            cli = self._cli("agent.brief", arguments)
            mcp = self._mcp("cpcs.agent.brief", arguments)
            http = self._http(request)
        self.assertEqual(direct, replay)
        self.assertEqual(direct, cli)
        self.assertEqual(direct, mcp)
        self.assertEqual(direct, http)
        self.assertEqual(direct["status"], "success")
        result = direct["result"]
        self.assertEqual(result["schema"], "cpcs.agent_brief/1.0")
        self.assertIn(
            "twelvelabs_analysis", result["task_routing"]["selected_workflows"]
        )
        self.assertIn(
            "directing_compilation", result["task_routing"]["selected_workflows"]
        )
        route_paths = {row["path"] for row in result["task_routing"]["routes"]}
        self.assertIn("lab/RUNBOOK_pegasus_extraction.md", route_paths)
        operation_rows = {row["name"]: row for row in result["operations"]}
        self.assertIn("cpcs.analyze.atomic.prepare", operation_rows)
        self.assertFalse(
            operation_rows["cpcs.analyze.atomic.prepare"]["authorization_required"]
        )
        self.assertTrue(operation_rows["cpcs.analyze.run"]["authorization_required"])
        self.assertFalse(
            operation_rows["cpcs.analyze.cascade"]["available_to_requested_role"]
        )
        self.assertEqual(
            result["serialization_policy"]["semantic_authority"], "canonical_json"
        )
        serialized = json.dumps(direct, sort_keys=True)
        self.assertNotIn(fake_secret, serialized)
        self.assertIn("TWELVE_LABS_API_KEY", serialized)
        self.assertEqual(before, authority_snapshot())

    def test_atomic_analysis_plan_is_operator_discoverable_and_schema_closed(self) -> None:
        arguments = {
            "schema": "cpcs.atomic_video_analysis_request/1.0",
            "source": {
                "source_id": "source_fixture",
                "asset_ref": "asset_fixture",
                "asset_job_id": "tl_asset_fixture_001",
                "local_path": "/tmp/authorized-fixture.mp4",
                "sha256": "a" * 64,
                "rights_scope": "original",
            },
            "authorized_interval": {"start_s": 0.0, "end_s": 8.0},
            "mode": "research",
            "domain_lenses": ["anime_vfx"],
            "candidate_concepts": [],
            "measurement_observation_ids": [],
            "max_parallel_jobs": 2,
            "created_at": "2026-08-04T00:00:00Z",
        }
        expected = {
            "schema": "cpcs.atomic_video_analysis_plan/1.0",
            "plan_id": "atomic_plan_" + "b" * 24,
            "mode": "research",
        }
        before = authority_snapshot()
        with mock.patch(
            "lab.application.service.make_atomic_analysis_plan",
            return_value=expected,
        ) as planner:
            first = invoke(
                app_request("cpcs.analyze.atomic.prepare", arguments),
                role="operator",
            )
            second = invoke(
                app_request("cpcs.analyze.atomic.prepare", arguments),
                role="operator",
            )
        self.assertEqual(first, second)
        self.assertEqual(first["result"], expected)
        self.assertEqual(planner.call_count, 2)
        self.assertEqual(before, authority_snapshot())

        denied = invoke(app_request("cpcs.analyze.atomic.prepare", arguments))
        self.assertEqual(denied["error"]["code"], "permission_denied")
        malformed = copy.deepcopy(arguments)
        malformed["unknown"] = True
        rejected = invoke(
            app_request("cpcs.analyze.atomic.prepare", malformed), role="operator"
        )
        self.assertEqual(rejected["error"]["code"], "invalid_request")

        chat_tools = handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            role="chat",
        )["result"]["tools"]
        operator_tools = handle_message(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            role="operator",
        )["result"]["tools"]
        self.assertNotIn(
            "cpcs.analyze.atomic.prepare", {row["name"] for row in chat_tools}
        )
        self.assertIn(
            "cpcs.analyze.atomic.prepare", {row["name"] for row in operator_tools}
        )

        brief = invoke(
            app_request(
                "cpcs.agent.brief",
                {"task": "Rerun atomic extraction on this clip", "role": "operator"},
            )
        )["result"]
        phases = {row["phase_id"]: row for row in brief["execution_plan"]}
        self.assertEqual(
            phases["plan_atomic_analysis"]["operations"],
            ["cpcs.analyze.atomic.prepare"],
        )
        self.assertIn("fast is orientation", brief["natural_language_brief"])

    def test_agent_brief_routes_side_by_side_comparison_without_granting_authority(self) -> None:
        arguments = {
            "task": "Run a side-by-side reference fidelity comparison and rebuild the prompt",
            "role": "operator",
        }
        before = authority_snapshot()
        response = invoke(app_request("cpcs.agent.brief", arguments), role="operator")
        self.assertEqual(response["status"], "success")
        result = response["result"]
        self.assertIn(
            "reference_candidate_comparison",
            result["task_routing"]["selected_workflows"],
        )
        operation = next(
            row
            for row in result["operations"]
            if row["name"] == "cpcs.verify.reference.compare"
        )
        self.assertTrue(operation["available_to_requested_role"])
        self.assertFalse(operation["authorization_required"])
        route_paths = {row["path"] for row in result["task_routing"]["routes"]}
        self.assertIn("lab/RUNBOOK_reference_to_kinematic_truth.md", route_paths)
        self.assertEqual(before, authority_snapshot())

    def test_agent_brief_research_route_stops_before_curated_authority(self) -> None:
        result = invoke(
            app_request(
                "cpcs.agent.brief",
                {
                    "task": "Ingest an authorized Markdown research folder into the knowledge base",
                    "role": "operator",
                },
            )
        )["result"]
        self.assertIn(
            "research_distillation", result["task_routing"]["selected_workflows"]
        )
        phases = {row["phase_id"]: row for row in result["execution_plan"]}
        self.assertEqual(phases["stage_research"]["minimum_role"], "operator")
        self.assertEqual(
            phases["plan_research_delta"]["operations"],
            ["cpcs.research.delta.prepare", "cpcs.research.delta.inspect"],
        )
        self.assertEqual(
            phases["qualify_research_delta_patch"]["operations"],
            [
                "cpcs.research.delta.patch.prepare",
                "cpcs.research.delta.patch.execute",
                "cpcs.research.delta.patch.inspect",
                "cpcs.research.delta.patch.discard",
            ],
        )
        self.assertTrue(
            phases["qualify_research_delta_patch"]["authorization_required"]
        )
        self.assertTrue(phases["promote_research"]["optional"])
        self.assertTrue(phases["promote_research"]["authorization_required"])
        operations = {row["name"]: row for row in result["operations"]}
        self.assertFalse(
            operations["cpcs.curate.promote"]["available_to_requested_role"]
        )
        self.assertTrue(
            operations["cpcs.research.delta.prepare"]["available_to_requested_role"]
        )
        rejected = invoke(
            app_request(
                "cpcs.agent.brief",
                {"task": "Inspect this repository", "unknown": "not accepted"},
            )
        )
        self.assertEqual(rejected["error"]["code"], "invalid_request")
        secret = "tlk_fake_secret_that_must_not_be_echoed"
        secret_rejected = invoke(
            app_request(
                "cpcs.agent.brief",
                {"task": f"Analyze this asset with {secret}"},
            )
        )
        self.assertEqual(secret_rejected["error"]["code"], "invalid_request")
        self.assertNotIn(secret, json.dumps(secret_rejected, sort_keys=True))

    def test_agent_brief_routes_exact_human_feedback_before_learning(self) -> None:
        result = invoke(
            app_request(
                "cpcs.agent.brief",
                {
                    "task": "Capture director feedback as a testimonial and learn from the experiment",
                    "role": "curator",
                },
            )
        )["result"]
        phases = {row["phase_id"]: row for row in result["execution_plan"]}
        self.assertEqual(
            phases["capture_human_feedback"]["operations"],
            [
                "cpcs.record.testimonial.capture",
                "cpcs.record.testimonial.review",
                "cpcs.testimonial.inspect",
            ],
        )
        self.assertTrue(phases["capture_human_feedback"]["authorization_required"])
        self.assertEqual(
            phases["record_learning"]["operations"],
            [
                "cpcs.experiment.prepare",
                "cpcs.experiment.seal",
                "cpcs.experiment.accept",
            ],
        )
        operations = {row["name"]: row for row in result["operations"]}
        self.assertTrue(operations["cpcs.experiment.accept"]["authorization_required"])
        self.assertEqual(
            operations["cpcs.experiment.accept"]["required_role"], "curator"
        )
        self.assertIn(
            "Preserve human feedback verbatim", result["natural_language_brief"]
        )

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
        self.assertNotIn("cpcs.testimonial.inspect", chat_names)
        self.assertIn("cpcs.testimonial.inspect", operator_names)
        self.assertNotIn("cpcs.record.testimonial.capture", operator_names)
        self.assertIn("cpcs.record.testimonial.capture", curator_names)
        self.assertIn("cpcs.record.testimonial.review", curator_names)
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
            "cpcs-application/1.24",
        )
        self.assertIn("cpcs.agent.brief", initialized["result"]["instructions"])
        tools = handle_message(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )
        names = {row["name"] for row in tools["result"]["tools"]}
        self.assertIn("cpcs.score.build", names)
        self.assertIn("cpcs.agent.brief", names)
        self.assertIn("cpcs.knowledge.search", names)
        self.assertNotIn("cpcs.curate.promote", names)

    def test_graph_projection_is_bounded_discoverable_and_exactly_authorized(self) -> None:
        before = authority_snapshot()
        plan = invoke(app_request("cpcs.graph.projection.plan"), role="operator")
        self.assertEqual(plan["status"], "success")
        self.assertEqual(plan["result"]["authority_effect"], "none")
        self.assertGreater(plan["result"]["node_count"], 0)
        with mock.patch.dict(os.environ, {}, clear=True):
            status = invoke(
                app_request("cpcs.graph.projection.status"), role="operator"
            )
        self.assertEqual(status["error"]["code"], "operation_failed")
        denied = invoke(
            app_request(
                "cpcs.graph.projection.sync",
                {
                    "expected_snapshot_hash": plan["result"][
                        "authority_snapshot_hash"
                    ]
                },
            ),
            role="operator",
        )
        self.assertEqual(denied["error"]["code"], "permission_denied")
        operator_tools = handle_message(
            {"jsonrpc": "2.0", "id": 8, "method": "tools/list", "params": {}},
            role="operator",
        )
        names = {row["name"] for row in operator_tools["result"]["tools"]}
        self.assertTrue(
            {
                "cpcs.graph.projection.plan",
                "cpcs.graph.projection.status",
                "cpcs.graph.projection.sync",
                "cpcs.graph.projection.parity",
            }
            <= names
        )
        sync_tool = next(
            row
            for row in operator_tools["result"]["tools"]
            if row["name"] == "cpcs.graph.projection.sync"
        )
        self.assertFalse(sync_tool["annotations"]["readOnlyHint"])
        self.assertTrue(sync_tool["annotations"]["idempotentHint"])
        self.assertTrue(sync_tool["annotations"]["openWorldHint"])
        brief = invoke(
            app_request(
                "cpcs.agent.brief",
                {"task": "Rebuild Neo4j and verify graph parity", "role": "operator"},
            ),
            role="operator",
        )
        self.assertEqual(brief["status"], "success")
        self.assertIn(
            "graph_projection",
            brief["result"]["task_routing"]["selected_workflows"],
        )
        self.assertIn(
            "CPCS_NEO4J_PASSWORD",
            brief["result"]["credential_policy"]["environment_variables"],
        )
        self.assertEqual(before, authority_snapshot())

    def test_render_evidence_workflow_is_agent_and_mcp_discoverable(self) -> None:
        before = authority_snapshot()
        brief = invoke(
            app_request(
                "cpcs.agent.brief",
                {
                    "task": "Run and resume a journaled end-to-end render-to-evidence workflow",
                    "role": "curator",
                },
            ),
            role="curator",
        )
        self.assertEqual(brief["status"], "success")
        result = brief["result"]
        self.assertIn(
            "render_evidence_workflow",
            result["task_routing"]["selected_workflows"],
        )
        phases = {row["phase_id"]: row for row in result["execution_plan"]}
        self.assertEqual(
            phases["prepare_render_evidence_workflow"]["operations"],
            ["cpcs.workflow.render.prepare", "cpcs.workflow.render.status"],
        )
        self.assertTrue(
            phases["advance_render_evidence_workflow"]["authorization_required"]
        )
        self.assertTrue(phases["review_render_evidence_workflow"]["optional"])
        self.assertIn("awaiting_review", result["natural_language_brief"])
        curator_tools = handle_message(
            {"jsonrpc": "2.0", "id": 9, "method": "tools/list", "params": {}},
            role="curator",
        )["result"]["tools"]
        tools = {row["name"]: row for row in curator_tools}
        expected = {
            "cpcs.workflow.render.prepare",
            "cpcs.workflow.render.status",
            "cpcs.workflow.render.advance",
            "cpcs.workflow.render.review",
            "cpcs.workflow.render.cancel",
        }
        self.assertTrue(expected <= set(tools))
        for name in expected:
            self.assertTrue(tools[name]["annotations"]["idempotentHint"])
        self.assertTrue(tools["cpcs.workflow.render.status"]["annotations"]["readOnlyHint"])
        self.assertEqual(before, authority_snapshot())

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
