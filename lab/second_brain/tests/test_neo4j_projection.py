from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lab.second_brain.src.neo4j_projection import (
    Neo4jBackend,
    Neo4jSettings,
    build_projection_plan,
    configured_backend,
    graph_logical_digest,
    reasoning_parity,
    sync_projection,
    watch_projection,
)
from lab.second_brain.src.query import default_request
from lab.second_brain.src.validate import REPO_ROOT
from lab.second_brain.tests.helpers import concept, make_root, write_rows


def _weights(root: Path) -> None:
    path = root / "lab" / "second_brain" / "derived" / "weights.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "algorithm_version": "reflection-v1.3",
                "derivation_policy": "controlled-render-evidence-v3",
                "policy_hash": "sha256:" + "a" * 64,
                "edges": [],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )


def _fixture_root(base: Path) -> Path:
    root = make_root(
        base,
        [concept("c_projection_alpha", "projection alpha")],
    )
    _weights(root)
    return root


class ProjectionPlanTests(unittest.TestCase):
    def test_plan_is_deterministic_located_and_authority_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _fixture_root(Path(directory))
            before = {
                str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file() and "work" not in path.parts
            }
            first = build_projection_plan(root)
            second = build_projection_plan(root)
            after = {
                str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file() and "work" not in path.parts
            }
            self.assertEqual(first, second)
            self.assertEqual(before, after)
            self.assertEqual(first["nodes"][0]["source_file"], "lab/concepts.jsonl")
            self.assertEqual(first["nodes"][0]["source_locator"], "jsonl:1")
            self.assertRegex(first["nodes"][0]["record_hash"], r"^sha256:[0-9a-f]{64}$")

    def test_networkx_is_the_default_and_unknown_backend_fails_closed(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(configured_backend().name, "networkx")
        with patch.dict(os.environ, {"CPCS_GRAPH_BACKEND": "arbitrary"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "unknown CPCS_GRAPH_BACKEND"):
                configured_backend()


@unittest.skipUnless(
    os.environ.get("CPCS_NEO4J_INTEGRATION") == "1",
    "set CPCS_NEO4J_INTEGRATION=1 for the real local Neo4j canary",
)
class Neo4jIntegrationTests(unittest.TestCase):
    @classmethod
    def _clean_namespace(cls, settings: Neo4jSettings) -> None:
        from neo4j import GraphDatabase

        with GraphDatabase.driver(
            settings.uri,
            auth=(settings.user, settings.password),
        ) as driver:
            with driver.session(database=settings.database) as session:
                session.run(
                    "CYPHER 5 MATCH ()-[r:CPCS_REL {namespace: $namespace}]->() DELETE r",
                    namespace=settings.namespace,
                ).consume()
                session.run(
                    "CYPHER 5 MATCH (n:CPCSNode {namespace: $namespace}) DELETE n",
                    namespace=settings.namespace,
                ).consume()
                session.run(
                    "CYPHER 5 MATCH (m:CPCSProjectionMeta {namespace: $namespace}) DELETE m",
                    namespace=settings.namespace,
                ).consume()

    def test_real_sync_incremental_retire_restore_rebuild_hot_load_and_reasoning_parity(self) -> None:
        settings = Neo4jSettings.from_environment()
        self.addCleanup(self._clean_namespace, settings)
        self._clean_namespace(settings)
        with tempfile.TemporaryDirectory() as directory:
            root = _fixture_root(Path(directory))
            first_plan = build_projection_plan(root)
            first = sync_projection(
                expected_snapshot_hash=first_plan["authority_snapshot_hash"],
                root=root,
            )
            replay = sync_projection(
                expected_snapshot_hash=first_plan["authority_snapshot_hash"],
                root=root,
            )
            self.assertEqual(first, replay)
            backend = Neo4jBackend(settings)
            first_graph = backend.load_graph(root, validity_mode="current", as_of=None)
            self.assertIn("c_projection_alpha", first_graph)

            write_rows(
                root / "lab" / "concepts.jsonl",
                [
                    concept("c_projection_alpha", "projection alpha"),
                    concept("c_projection_beta", "projection beta"),
                ],
            )
            write_rows(
                root / "lab" / "second_brain" / "curated" / "edges.jsonl",
                [
                    {
                        "id": "edge_999999",
                        "u": "c_projection_alpha",
                        "v": "c_projection_beta",
                        "type": "refines",
                        "context": "all",
                        "authored_by": "projection_test",
                        "note": None,
                        "sources": [],
                    }
                ],
            )
            second_plan = build_projection_plan(root)
            watch = watch_projection(
                interval_seconds=0.25,
                debounce_seconds=0.0,
                root=root,
                once=True,
            )
            self.assertEqual(watch["sync_count"], 1)
            second = sync_projection(
                expected_snapshot_hash=second_plan["authority_snapshot_hash"],
                root=root,
            )
            self.assertEqual(second["changes"]["created_nodes"], 1)
            self.assertEqual(second["changes"]["created_edges"], 1)
            hot_graph = backend.load_graph(root, validity_mode="current", as_of=None)
            self.assertIn("c_projection_beta", hot_graph)
            self.assertEqual(hot_graph.number_of_edges(), 1)

            write_rows(
                root / "lab" / "concepts.jsonl",
                [concept("c_projection_alpha", "projection alpha")],
            )
            write_rows(root / "lab" / "second_brain" / "curated" / "edges.jsonl", [])
            third_plan = build_projection_plan(root)
            third = sync_projection(
                expected_snapshot_hash=third_plan["authority_snapshot_hash"],
                root=root,
            )
            self.assertEqual(third["changes"]["retired_nodes"], 1)
            self.assertEqual(third["changes"]["retired_edges"], 1)

            write_rows(
                root / "lab" / "concepts.jsonl",
                [
                    concept("c_projection_alpha", "projection alpha"),
                    concept("c_projection_beta", "projection beta"),
                ],
            )
            write_rows(
                root / "lab" / "second_brain" / "curated" / "edges.jsonl",
                [
                    {
                        "id": "edge_999999",
                        "u": "c_projection_alpha",
                        "v": "c_projection_beta",
                        "type": "refines",
                        "context": "all",
                        "authored_by": "projection_test",
                        "note": None,
                        "sources": [],
                    }
                ],
            )
            self.assertEqual(build_projection_plan(root), second_plan)
            restored = sync_projection(
                expected_snapshot_hash=second_plan["authority_snapshot_hash"],
                root=root,
            )
            self.assertEqual(restored["changes"]["restored_nodes"], 1)
            self.assertEqual(restored["changes"]["restored_edges"], 1)

            self._clean_namespace(settings)
            rebuilt = sync_projection(
                expected_snapshot_hash=second_plan["authority_snapshot_hash"],
                root=root,
            )
            self.assertEqual(rebuilt["logical_digest"], second_plan["logical_digest"])
            rebuilt_graph = backend.load_graph(root, validity_mode="current", as_of=None)
            self.assertEqual(graph_logical_digest(rebuilt_graph), second_plan["logical_digest"])

        repository_plan = build_projection_plan(REPO_ROOT)
        sync_projection(
            expected_snapshot_hash=repository_plan["authority_snapshot_hash"],
            root=REPO_ROOT,
        )
        parity = reasoning_parity(
            [
                default_request("Laban effort decimal spatial movement"),
                default_request("restrained fear escalating into urgent movement"),
                default_request("cinematic UGC product recommendation"),
            ],
            REPO_ROOT,
        )
        self.assertEqual(parity["status"], "passed")
        self.assertEqual(parity["case_count"], 3)


if __name__ == "__main__":
    unittest.main()
