"""CPCS-owned, rebuildable Neo4j projection and NetworkX parity boundary."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import signal
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import networkx as nx

from .authority import authority_reader, authority_writer
from .graph import build_live_graph
from .temporal import is_visible_bitemporal, validate_bitemporal_request
from .validate import (
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    canonical_json_bytes,
    read_jsonl,
    sha256_value,
    validate_curated,
    validate_immutable,
    validate_instance,
)


PROJECTION_POLICY = "cpcs-neo4j-projection/1.0"
BACKEND_POLICY = "cpcs-graph-backend/1.0"
PLAN_SCHEMA = "cpcs.graph_projection_plan/1.0"
CHECKPOINT_SCHEMA = "cpcs.graph_projection_checkpoint/1.0"
CHECKPOINT_RELATIVE_PATH = Path("work/neo4j")
DEFAULT_NAMESPACE = "cpcs"
FORBIDDEN_NAMESPACES = frozenset({"polymath", "polymath_mcp"})
GRAPH_BACKENDS = frozenset({"networkx", "neo4j", "neo4j_shadow"})
FALLBACK_POLICIES = frozenset({"fail_closed", "networkx"})
BATCH_SIZE = 500


class ProjectionUnavailable(RuntimeError):
    """Raised when the configured projection cannot be reached safely."""


class ProjectionParityFailure(RuntimeError):
    """Raised when the Neo4j projection differs from the NetworkX reference."""


@dataclass(frozen=True)
class Neo4jSettings:
    uri: str
    user: str
    password: str
    database: str
    namespace: str
    ownership: str

    @classmethod
    def from_environment(cls) -> "Neo4jSettings":
        values = {
            "uri": os.environ.get("CPCS_NEO4J_URI", ""),
            "user": os.environ.get("CPCS_NEO4J_USER", ""),
            "password": os.environ.get("CPCS_NEO4J_PASSWORD", ""),
            "database": os.environ.get("CPCS_NEO4J_DATABASE", "neo4j"),
            "namespace": os.environ.get("CPCS_NEO4J_NAMESPACE", DEFAULT_NAMESPACE),
            "ownership": os.environ.get("CPCS_NEO4J_OWNERSHIP", ""),
        }
        missing = [key for key in ("uri", "user", "password", "ownership") if not values[key]]
        if missing:
            raise ProjectionUnavailable(
                "Neo4j projection is not configured; missing environment values: "
                + ", ".join("CPCS_NEO4J_" + key.upper() for key in missing)
            )
        if values["ownership"] != "cpcs_owned":
            raise ProjectionUnavailable(
                "CPCS_NEO4J_OWNERSHIP must equal cpcs_owned; shared or Polymath-owned graphs are rejected"
            )
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", values["namespace"]):
            raise ProjectionUnavailable("CPCS_NEO4J_NAMESPACE is invalid")
        if values["namespace"] in FORBIDDEN_NAMESPACES:
            raise ProjectionUnavailable("Polymath namespaces are outside CPCS authority")
        if not re.fullmatch(r"[A-Za-z0-9._-]+", values["database"]):
            raise ProjectionUnavailable("CPCS_NEO4J_DATABASE is invalid")
        if not values["uri"].startswith(("bolt://", "neo4j://", "neo4j+s://", "neo4j+ssc://")):
            raise ProjectionUnavailable("CPCS_NEO4J_URI must use a Neo4j Bolt URI")
        return cls(**values)

    def public(self) -> dict[str, Any]:
        return {
            "configured": True,
            "database": self.database,
            "namespace": self.namespace,
            "ownership": self.ownership,
            "credentials_in_environment": True,
        }


def projection_configuration_status() -> dict[str, Any]:
    required = (
        "CPCS_NEO4J_URI",
        "CPCS_NEO4J_USER",
        "CPCS_NEO4J_PASSWORD",
        "CPCS_NEO4J_OWNERSHIP",
    )
    return {
        "configured": all(bool(os.environ.get(name)) for name in required),
        "required_environment_present": {name: bool(os.environ.get(name)) for name in required},
        "database": os.environ.get("CPCS_NEO4J_DATABASE", "neo4j"),
        "namespace": os.environ.get("CPCS_NEO4J_NAMESPACE", DEFAULT_NAMESPACE),
        "backend": os.environ.get("CPCS_GRAPH_BACKEND", "networkx"),
        "fallback_policy": os.environ.get("CPCS_GRAPH_FALLBACK", "fail_closed"),
        "secret_values_exposed": False,
    }


def _driver(settings: Neo4jSettings) -> Any:
    try:
        from neo4j import GraphDatabase
    except ImportError as error:
        raise ProjectionUnavailable(
            "the pinned neo4j Python driver is not installed"
        ) from error
    return GraphDatabase.driver(
        settings.uri,
        auth=(settings.user, settings.password),
        connection_timeout=10.0,
        max_connection_pool_size=8,
        notifications_min_severity="OFF",
    )


def _json(value: Any) -> str:
    return canonical_json_bytes(value).decode("utf-8").rstrip("\n")


def _jsonl_index(
    root: Path,
    relative: str,
    schema_version: str,
) -> dict[str, dict[str, Any]]:
    path = root / relative
    result: dict[str, dict[str, Any]] = {}
    for line_number, record in enumerate(read_jsonl(path), 1):
        result[record["id"]] = {
            "record": record,
            "record_hash": sha256_value(record),
            "schema_version": schema_version,
            "source_file": relative,
            "source_locator": f"jsonl:{line_number}",
        }
    return result


def _authority_index(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    nodes: dict[str, dict[str, Any]] = {}
    nodes.update(_jsonl_index(root, "lab/concepts.jsonl", "cpcs.concept/1.0"))
    nodes.update(
        _jsonl_index(
            root,
            "lab/second_brain/curated/reasoning_policies.jsonl",
            "cpcs.reasoning_policy/1.0",
        )
    )
    bridge_path = root / "lab/second_brain/curated/video_concept_bridges.jsonl"
    if bridge_path.exists():
        nodes.update(
            _jsonl_index(
                root,
                "lab/second_brain/curated/video_concept_bridges.jsonl",
                "cpcs.video_concept_bridge/1.0",
            )
        )
    edges = _jsonl_index(
        root,
        "lab/second_brain/curated/edges.jsonl",
        "cpcs.edge/1.0",
    )
    store_schemas = {
        "flights": "cpcs.flight/1.0",
        "runs": "cpcs.run/1.0",
        "pegasus_observations": "cpcs.pegasus_observation/1.0",
        "measurement_observations": "cpcs.measurement_observation/1.0",
    }
    for store, schema_version in store_schemas.items():
        nodes.update(
            _jsonl_index(
                root,
                f"lab/second_brain/immutable/{store}.jsonl",
                schema_version,
            )
        )
    weights_path = root / "lab" / "second_brain" / "derived" / "weights.json"
    weights = json.loads(weights_path.read_text(encoding="utf-8"))
    for index, edge in enumerate(weights.get("edges", [])):
        edges[edge["id"]] = {
            "record": edge,
            "record_hash": sha256_value(edge),
            "schema_version": "cpcs.learned_weight/1.0",
            "source_file": "lab/second_brain/derived/weights.json",
            "source_locator": f"/edges/{index}",
        }
    return nodes, edges


def _synthetic_edge_source(
    edge_id: str,
    nodes: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    record_id = None
    if edge_id.startswith("flight:"):
        parts = edge_id.split(":", 2)
        record_id = parts[1] if len(parts) == 3 else None
    elif edge_id.startswith("run_flight:"):
        parts = edge_id.split(":", 2)
        record_id = parts[1] if len(parts) == 3 else None
    elif edge_id.startswith("evidence:"):
        parts = edge_id.split(":", 2)
        record_id = parts[1] if len(parts) == 3 else None
    elif edge_id.startswith("policy_concept:"):
        parts = edge_id.split(":", 2)
        record_id = parts[1] if len(parts) == 3 else None
    elif edge_id.startswith("video_bridge:"):
        parts = edge_id.split(":", 2)
        record_id = parts[1] if len(parts) == 3 else None
    return nodes.get(record_id) if record_id else None


def graph_logical_rows(graph: nx.MultiDiGraph) -> dict[str, list[dict[str, Any]]]:
    nodes = [
        {"id": str(node_id), "payload": copy.deepcopy(data)}
        for node_id, data in sorted(graph.nodes(data=True), key=lambda row: str(row[0]))
        if data.get("tier") != "temporary"
    ]
    edges = [
        {
            "id": str(key),
            "u": str(u),
            "v": str(v),
            "payload": copy.deepcopy(data),
        }
        for u, v, key, data in sorted(
            graph.edges(keys=True, data=True),
            key=lambda row: (str(row[0]), str(row[1]), str(row[2])),
        )
        if data.get("tier") != "temporary"
    ]
    return {"nodes": nodes, "edges": edges}


def graph_logical_digest(graph: nx.MultiDiGraph) -> str:
    return sha256_value(graph_logical_rows(graph))


@authority_reader("neo4j_projection_plan")
def build_projection_plan(root: Path = REPO_ROOT) -> dict[str, Any]:
    """Build one deterministic all-version projection from validated Git authority."""
    validate_curated(root)
    validate_immutable(root)
    graph = build_live_graph(
        root,
        include_derived=True,
        validity_mode="all_versions",
        as_of=None,
    )
    node_sources, edge_sources = _authority_index(root)
    projected_nodes: list[dict[str, Any]] = []
    for node_id, data in sorted(graph.nodes(data=True), key=lambda row: str(row[0])):
        source = node_sources.get(str(node_id))
        if source is None:
            raise ValidationFailure(f"projection node lacks repository authority locator: {node_id}")
        payload = copy.deepcopy(data)
        row = {
            "id": str(node_id),
            "record_hash": source["record_hash"],
            "projection_hash": sha256_value({"id": str(node_id), "payload": payload}),
            "node_type": str(data.get("node_type", "unknown")),
            "tier": str(data["tier"]),
            "schema_version": source["schema_version"],
            "source_file": source["source_file"],
            "source_locator": source["source_locator"],
            "payload_json": _json(payload),
        }
        projected_nodes.append(row)
    node_ids = {row["id"] for row in projected_nodes}
    projected_edges: list[dict[str, Any]] = []
    for u, v, key, data in sorted(
        graph.edges(keys=True, data=True),
        key=lambda row: (str(row[0]), str(row[1]), str(row[2])),
    ):
        edge_id = str(key)
        source = edge_sources.get(edge_id) or _synthetic_edge_source(edge_id, node_sources)
        if source is None:
            raise ValidationFailure(f"projection edge lacks repository authority locator: {edge_id}")
        if str(u) not in node_ids or str(v) not in node_ids:
            raise ValidationFailure(f"projection edge has missing endpoint: {edge_id}")
        payload = copy.deepcopy(data)
        row = {
            "id": edge_id,
            "u": str(u),
            "v": str(v),
            "record_hash": source["record_hash"],
            "projection_hash": sha256_value(
                {"id": edge_id, "u": str(u), "v": str(v), "payload": payload}
            ),
            "edge_type": str(data.get("edge_type", "unknown")),
            "tier": str(data["tier"]),
            "schema_version": source["schema_version"],
            "source_file": source["source_file"],
            "source_locator": source["source_locator"],
            "payload_json": _json(payload),
        }
        projected_edges.append(row)
    logical_digest = graph_logical_digest(graph)
    identity = {
        "policy_version": PROJECTION_POLICY,
        "logical_digest": logical_digest,
        "nodes": projected_nodes,
        "edges": projected_edges,
    }
    snapshot_hash = sha256_value(identity)
    value = {
        "schema": PLAN_SCHEMA,
        "policy_version": PROJECTION_POLICY,
        "authority_snapshot_hash": snapshot_hash,
        "generation": "generation_" + snapshot_hash.removeprefix("sha256:")[:24],
        "logical_digest": logical_digest,
        "nodes": projected_nodes,
        "edges": projected_edges,
    }
    validate_instance("graph_projection_plan", value, root)
    return value


def projection_plan_summary(root: Path = REPO_ROOT) -> dict[str, Any]:
    plan = build_projection_plan(root)
    return {
        "schema": "cpcs.graph_projection_plan_summary/1.0",
        "policy_version": plan["policy_version"],
        "authority_snapshot_hash": plan["authority_snapshot_hash"],
        "generation": plan["generation"],
        "logical_digest": plan["logical_digest"],
        "node_count": len(plan["nodes"]),
        "edge_count": len(plan["edges"]),
        "authority_effect": "none",
    }


def _chunks(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    return [rows[index : index + BATCH_SIZE] for index in range(0, len(rows), BATCH_SIZE)]


def _read_database_rows(transaction: Any, namespace: str, *, active_only: bool) -> dict[str, list[dict[str, Any]]]:
    active = " WHERE n.active = true" if active_only else ""
    nodes = [
        dict(record)
        for record in transaction.run(
            "CYPHER 5 MATCH (n:CPCSNode {namespace: $namespace})"
            + active
            + " RETURN n.id AS id, n.record_hash AS record_hash, n.projection_hash AS projection_hash, n.active AS active ORDER BY id",
            namespace=namespace,
        )
    ]
    rel_active = " AND r.active = true" if active_only else ""
    edges = [
        dict(record)
        for record in transaction.run(
            "CYPHER 5 MATCH (u:CPCSNode)-[r:CPCS_REL {namespace: $namespace}]->(v:CPCSNode) "
            "WHERE u.namespace = $namespace AND v.namespace = $namespace"
            + rel_active
            + " RETURN r.id AS id, u.id AS u, v.id AS v, r.record_hash AS record_hash, r.projection_hash AS projection_hash, r.active AS active ORDER BY id, u, v",
            namespace=namespace,
        )
    ]
    return {"nodes": nodes, "edges": edges}


def _read_graph_transaction(transaction: Any, namespace: str) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph(
        name="CPCS Neo4j projected reasoning graph",
        persistence="neo4j_projection",
        projection_policy=PROJECTION_POLICY,
    )
    for record in transaction.run(
        "CYPHER 5 MATCH (n:CPCSNode {namespace: $namespace, active: true}) "
        "RETURN n.id AS id, n.payload_json AS payload_json ORDER BY id",
        namespace=namespace,
    ):
        graph.add_node(record["id"], **json.loads(record["payload_json"]))
    for record in transaction.run(
        "CYPHER 5 MATCH (u:CPCSNode)-[r:CPCS_REL {namespace: $namespace, active: true}]->(v:CPCSNode) "
        "WHERE u.namespace = $namespace AND v.namespace = $namespace AND u.active = true AND v.active = true "
        "RETURN r.id AS id, u.id AS u, v.id AS v, r.payload_json AS payload_json ORDER BY u, v, id",
        namespace=namespace,
    ):
        graph.add_edge(
            record["u"],
            record["v"],
            key=record["id"],
            **json.loads(record["payload_json"]),
        )
    return graph


def _meta(transaction: Any, namespace: str) -> dict[str, Any] | None:
    record = transaction.run(
        "CYPHER 5 MATCH (m:CPCSProjectionMeta {namespace: $namespace}) "
        "RETURN m.policy_version AS policy_version, m.authority_snapshot_hash AS authority_snapshot_hash, "
        "m.generation AS generation, m.logical_digest AS logical_digest, m.node_count AS node_count, m.edge_count AS edge_count",
        namespace=namespace,
    ).single()
    return dict(record) if record is not None else None


def _classify_changes(
    existing: dict[str, list[dict[str, Any]]],
    plan: dict[str, Any],
) -> dict[str, int]:
    result: dict[str, int] = {}
    for kind in ("nodes", "edges"):
        current = {row["id"]: row for row in existing[kind]}
        desired = {row["id"]: row for row in plan[kind]}
        created = updated = restored = 0
        for row_id, row in desired.items():
            prior = current.get(row_id)
            if prior is None:
                created += 1
            elif not prior["active"]:
                restored += 1
            elif prior["projection_hash"] != row["projection_hash"]:
                updated += 1
            if kind == "edges" and prior is not None and (
                prior["u"] != row["u"] or prior["v"] != row["v"]
            ):
                raise ValidationFailure(
                    f"durable edge endpoints changed without a new ID: {row_id}"
                )
        retired = sum(
            1 for row_id, row in current.items() if row["active"] and row_id not in desired
        )
        singular = "node" if kind == "nodes" else "edge"
        result[f"created_{kind}"] = created
        result[f"updated_{kind}"] = updated
        result[f"restored_{kind}"] = restored
        result[f"retired_{kind}"] = retired
    return result


def _verify_active_projection(
    transaction: Any,
    namespace: str,
    plan: dict[str, Any],
) -> None:
    rows = _read_database_rows(transaction, namespace, active_only=True)
    expected_nodes = sorted([
        {
            "id": row["id"],
            "record_hash": row["record_hash"],
            "projection_hash": row["projection_hash"],
        }
        for row in plan["nodes"]
    ], key=lambda row: row["id"])
    actual_nodes = [
        {key: row[key] for key in ("id", "record_hash", "projection_hash")}
        for row in rows["nodes"]
    ]
    expected_edges = sorted([
        {
            "id": row["id"],
            "u": row["u"],
            "v": row["v"],
            "record_hash": row["record_hash"],
            "projection_hash": row["projection_hash"],
        }
        for row in plan["edges"]
    ], key=lambda row: (row["id"], row["u"], row["v"]))
    actual_edges = [
        {key: row[key] for key in ("id", "u", "v", "record_hash", "projection_hash")}
        for row in rows["edges"]
    ]
    if actual_nodes != expected_nodes or actual_edges != expected_edges:
        raise ProjectionParityFailure("Neo4j active IDs, hashes, or endpoints differ from the projection plan")
    graph = _read_graph_transaction(transaction, namespace)
    if graph_logical_digest(graph) != plan["logical_digest"]:
        raise ProjectionParityFailure("Neo4j logical graph digest differs from NetworkX")


def _sync_transaction(
    transaction: Any,
    settings: Neo4jSettings,
    plan: dict[str, Any],
) -> tuple[dict[str, int], bool]:
    namespace = settings.namespace
    prior_meta = _meta(transaction, namespace)
    if prior_meta and (
        prior_meta.get("policy_version") == PROJECTION_POLICY
        and prior_meta.get("authority_snapshot_hash") == plan["authority_snapshot_hash"]
        and prior_meta.get("logical_digest") == plan["logical_digest"]
    ):
        _verify_active_projection(transaction, namespace, plan)
        return _classify_changes(_read_database_rows(transaction, namespace, active_only=False), plan), True

    existing = _read_database_rows(transaction, namespace, active_only=False)
    changes = _classify_changes(existing, plan)
    transaction.run(
        "CYPHER 5 MATCH ()-[r:CPCS_REL {namespace: $namespace}]->() WHERE r.active = true "
        "SET r.active = false, r.retired_generation = $generation",
        namespace=namespace,
        generation=plan["generation"],
    ).consume()
    for rows in _chunks(plan["nodes"]):
        transaction.run(
            "CYPHER 5 UNWIND $rows AS row "
            "MERGE (n:CPCSNode {namespace: $namespace, id: row.id}) "
            "SET n.record_hash = row.record_hash, n.projection_hash = row.projection_hash, "
            "n.node_type = row.node_type, n.tier = row.tier, n.schema_version = row.schema_version, "
            "n.source_file = row.source_file, n.source_locator = row.source_locator, "
            "n.payload_json = row.payload_json, n.generation = $generation, n.active = true "
            "REMOVE n.retired_generation",
            namespace=namespace,
            generation=plan["generation"],
            rows=rows,
        ).consume()
    transaction.run(
        "CYPHER 5 MATCH (n:CPCSNode {namespace: $namespace}) "
        "WHERE n.active = true AND n.generation <> $generation "
        "SET n.active = false, n.retired_generation = $generation",
        namespace=namespace,
        generation=plan["generation"],
    ).consume()
    for rows in _chunks(plan["edges"]):
        transaction.run(
            "CYPHER 5 UNWIND $rows AS row "
            "MATCH (u:CPCSNode {namespace: $namespace, id: row.u}) "
            "MATCH (v:CPCSNode {namespace: $namespace, id: row.v}) "
            "MERGE (u)-[r:CPCS_REL {namespace: $namespace, id: row.id}]->(v) "
            "SET r.record_hash = row.record_hash, r.projection_hash = row.projection_hash, "
            "r.edge_type = row.edge_type, r.tier = row.tier, r.schema_version = row.schema_version, "
            "r.source_file = row.source_file, r.source_locator = row.source_locator, "
            "r.payload_json = row.payload_json, r.generation = $generation, r.active = true "
            "REMOVE r.retired_generation",
            namespace=namespace,
            generation=plan["generation"],
            rows=rows,
        ).consume()
    _verify_active_projection(transaction, namespace, plan)
    transaction.run(
        "CYPHER 5 MERGE (m:CPCSProjectionMeta {namespace: $namespace}) "
        "SET m.policy_version = $policy_version, m.authority_snapshot_hash = $authority_snapshot_hash, "
        "m.generation = $generation, m.logical_digest = $logical_digest, "
        "m.node_count = $node_count, m.edge_count = $edge_count",
        namespace=namespace,
        policy_version=PROJECTION_POLICY,
        authority_snapshot_hash=plan["authority_snapshot_hash"],
        generation=plan["generation"],
        logical_digest=plan["logical_digest"],
        node_count=len(plan["nodes"]),
        edge_count=len(plan["edges"]),
    ).consume()
    return changes, False


def _checkpoint_path(root: Path, namespace: str) -> Path:
    return root / CHECKPOINT_RELATIVE_PATH / namespace / "checkpoint.json"


def _read_checkpoint(root: Path, namespace: str) -> dict[str, Any] | None:
    path = _checkpoint_path(root, namespace)
    if not path.exists():
        return None
    if path.is_symlink():
        raise ValidationFailure("Neo4j checkpoint cannot be a symlink")
    value = json.loads(path.read_text(encoding="utf-8"))
    validate_instance("graph_projection_checkpoint", value, root)
    clean = {key: item for key, item in value.items() if key != "checkpoint_hash"}
    if value["checkpoint_hash"] != sha256_value(clean):
        raise ValidationFailure("Neo4j checkpoint hash is invalid")
    return value


def _write_checkpoint(value: dict[str, Any], root: Path) -> None:
    path = _checkpoint_path(root, value["namespace"])
    assert_write_target("neo4j_projection", path, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise ValidationFailure("Neo4j checkpoint path cannot contain a symlink")
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(canonical_json_bytes(value))
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.chmod(path, 0o600)


@authority_writer("neo4j_projection_sync")
def sync_projection(
    *,
    expected_snapshot_hash: str,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Synchronize one exact validated authority snapshot into the CPCS namespace."""
    settings = Neo4jSettings.from_environment()
    plan = build_projection_plan(root)
    if plan["authority_snapshot_hash"] != expected_snapshot_hash:
        raise ValidationFailure(
            "projection plan changed; inspect the new snapshot hash before authorizing sync"
        )
    checkpoint = _read_checkpoint(root, settings.namespace)
    with _driver(settings) as driver:
        driver.verify_connectivity()
        with driver.session(database=settings.database) as session:
            session.run(
                "CYPHER 5 CREATE CONSTRAINT cpcs_projection_node_identity IF NOT EXISTS "
                "FOR (n:CPCSNode) REQUIRE (n.namespace, n.id) IS UNIQUE"
            ).consume()
            session.run(
                "CYPHER 5 CREATE CONSTRAINT cpcs_projection_meta_identity IF NOT EXISTS "
                "FOR (m:CPCSProjectionMeta) REQUIRE m.namespace IS UNIQUE"
            ).consume()
            changes, replay = session.execute_write(
                _sync_transaction,
                settings,
                plan,
            )
    if (
        replay
        and checkpoint is not None
        and checkpoint["namespace"] == settings.namespace
        and checkpoint["database"] == settings.database
        and checkpoint["authority_snapshot_hash"] == plan["authority_snapshot_hash"]
    ):
        return checkpoint
    value = {
        "schema": CHECKPOINT_SCHEMA,
        "policy_version": PROJECTION_POLICY,
        "namespace": settings.namespace,
        "database": settings.database,
        "authority_snapshot_hash": plan["authority_snapshot_hash"],
        "generation": plan["generation"],
        "logical_digest": plan["logical_digest"],
        "node_count": len(plan["nodes"]),
        "edge_count": len(plan["edges"]),
        "changes": changes,
    }
    value["checkpoint_hash"] = sha256_value(value)
    validate_instance("graph_projection_checkpoint", value, root)
    _write_checkpoint(value, root)
    return value


@authority_reader("neo4j_projection_status")
def projection_status(root: Path = REPO_ROOT) -> dict[str, Any]:
    settings = Neo4jSettings.from_environment()
    checkpoint = _read_checkpoint(root, settings.namespace)
    with _driver(settings) as driver:
        driver.verify_connectivity()
        with driver.session(database=settings.database) as session:
            meta = session.execute_read(_meta, settings.namespace)
            graph = session.execute_read(_read_graph_transaction, settings.namespace)
    return {
        "schema": "cpcs.graph_projection_status/1.0",
        **settings.public(),
        "policy_version": PROJECTION_POLICY,
        "active_generation": meta,
        "active_logical_digest": graph_logical_digest(graph),
        "active_node_count": graph.number_of_nodes(),
        "active_edge_count": graph.number_of_edges(),
        "checkpoint_present": checkpoint is not None,
        "checkpoint_matches": bool(
            checkpoint
            and meta
            and checkpoint["authority_snapshot_hash"] == meta["authority_snapshot_hash"]
            and checkpoint["logical_digest"] == meta["logical_digest"]
        ),
        "arbitrary_cypher_exposed": False,
    }


class GraphBackend(Protocol):
    name: str

    def load_graph(
        self,
        root: Path,
        *,
        validity_mode: str,
        as_of: str | None,
        valid_at: str | None = None,
        known_at: str | None = None,
    ) -> nx.MultiDiGraph: ...

    def metadata(self) -> dict[str, Any]: ...


class NetworkXBackend:
    name = "networkx"

    def load_graph(
        self,
        root: Path,
        *,
        validity_mode: str,
        as_of: str | None,
        valid_at: str | None = None,
        known_at: str | None = None,
    ) -> nx.MultiDiGraph:
        return build_live_graph(
            root,
            validity_mode=validity_mode,
            as_of=as_of,
            valid_at=valid_at,
            known_at=known_at,
        )

    def metadata(self) -> dict[str, Any]:
        return {"policy_version": BACKEND_POLICY, "selected": self.name, "fallback_used": False}


def _temporal_view(
    graph: nx.MultiDiGraph,
    validity_mode: str,
    as_of: str | None,
    valid_at: str | None = None,
    known_at: str | None = None,
) -> nx.MultiDiGraph:
    validate_bitemporal_request(validity_mode, as_of, valid_at, known_at)
    visible = {
        node_id
        for node_id, data in graph.nodes(data=True)
        if data.get("node_type") != "concept"
        or is_visible_bitemporal(
            data,
            validity_mode,
            as_of=as_of,
            valid_at=valid_at,
            known_at=known_at,
        )
    }
    result = graph.subgraph(visible).copy()
    for u, v, key, data in list(result.edges(keys=True, data=True)):
        if data.get("tier") == "curated" and not is_visible_bitemporal(
            data,
            validity_mode,
            as_of=as_of,
            valid_at=valid_at,
            known_at=known_at,
        ):
            result.remove_edge(u, v, key)
    result.graph.update(
        validity_mode=validity_mode,
        as_of=as_of,
        valid_at=valid_at,
        known_at=known_at,
        projection_policy=PROJECTION_POLICY,
    )
    return result


class Neo4jBackend:
    name = "neo4j"

    def __init__(self, settings: Neo4jSettings | None = None) -> None:
        self.settings = settings or Neo4jSettings.from_environment()

    def load_graph(
        self,
        root: Path,
        *,
        validity_mode: str,
        as_of: str | None,
        valid_at: str | None = None,
        known_at: str | None = None,
    ) -> nx.MultiDiGraph:
        with _driver(self.settings) as driver:
            driver.verify_connectivity()
            with driver.session(database=self.settings.database) as session:
                meta = session.execute_read(_meta, self.settings.namespace)
                if meta is None or meta.get("policy_version") != PROJECTION_POLICY:
                    raise ProjectionUnavailable("Neo4j has no active CPCS projection generation")
                graph = session.execute_read(_read_graph_transaction, self.settings.namespace)
        if graph_logical_digest(graph) != meta["logical_digest"]:
            raise ProjectionParityFailure("active Neo4j graph differs from its published generation")
        return _temporal_view(
            graph,
            validity_mode,
            as_of,
            valid_at=valid_at,
            known_at=known_at,
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "policy_version": BACKEND_POLICY,
            "selected": self.name,
            "namespace": self.settings.namespace,
            "database": self.settings.database,
            "fallback_used": False,
        }


class ShadowBackend:
    name = "neo4j_shadow"

    def __init__(self) -> None:
        self.reference = NetworkXBackend()
        self.projection = Neo4jBackend()

    def load_graph(
        self,
        root: Path,
        *,
        validity_mode: str,
        as_of: str | None,
        valid_at: str | None = None,
        known_at: str | None = None,
    ) -> nx.MultiDiGraph:
        reference = self.reference.load_graph(
            root,
            validity_mode=validity_mode,
            as_of=as_of,
            valid_at=valid_at,
            known_at=known_at,
        )
        projected = self.projection.load_graph(
            root,
            validity_mode=validity_mode,
            as_of=as_of,
            valid_at=valid_at,
            known_at=known_at,
        )
        if graph_logical_digest(reference) != graph_logical_digest(projected):
            raise ProjectionParityFailure("Neo4j shadow graph differs from NetworkX")
        return reference

    def metadata(self) -> dict[str, Any]:
        return {
            "policy_version": BACKEND_POLICY,
            "selected": self.name,
            "reference": "networkx",
            "projection": "neo4j",
            "fallback_used": False,
        }


class FallbackBackend:
    name = "networkx_fallback"

    def __init__(self, failed_backend: str, error: Exception) -> None:
        self.failed_backend = failed_backend
        self.error = error
        self.reference = NetworkXBackend()

    def load_graph(
        self,
        root: Path,
        *,
        validity_mode: str,
        as_of: str | None,
        valid_at: str | None = None,
        known_at: str | None = None,
    ) -> nx.MultiDiGraph:
        return self.reference.load_graph(
            root,
            validity_mode=validity_mode,
            as_of=as_of,
            valid_at=valid_at,
            known_at=known_at,
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "policy_version": BACKEND_POLICY,
            "selected": self.name,
            "failed_backend": self.failed_backend,
            "failure_class": self.error.__class__.__name__,
            "fallback_used": True,
        }


def configured_backend() -> GraphBackend:
    selected = os.environ.get("CPCS_GRAPH_BACKEND", "networkx")
    fallback = os.environ.get("CPCS_GRAPH_FALLBACK", "fail_closed")
    if selected not in GRAPH_BACKENDS:
        raise ProjectionUnavailable(f"unknown CPCS_GRAPH_BACKEND: {selected}")
    if fallback not in FALLBACK_POLICIES:
        raise ProjectionUnavailable(f"unknown CPCS_GRAPH_FALLBACK: {fallback}")
    if selected == "networkx":
        return NetworkXBackend()
    try:
        return Neo4jBackend() if selected == "neo4j" else ShadowBackend()
    except Exception as error:
        if fallback == "networkx":
            return FallbackBackend(selected, error)
        raise


def _reasoning_projection(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result.pop("graph_backend", None)
    return result


@authority_reader("neo4j_reasoning_parity")
def reasoning_parity(
    requests: list[dict[str, Any]],
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    if not 1 <= len(requests) <= 8:
        raise ValidationFailure("reasoning parity requires 1 through 8 bounded queries")
    from .query import reason

    reference = NetworkXBackend()
    projected = Neo4jBackend()
    cases = []
    for request in requests:
        validate_instance("reasoning_query", request, root)
        expected = _reasoning_projection(reason(request, root, graph_backend=reference))
        actual = _reasoning_projection(reason(request, root, graph_backend=projected))
        expected_hash = sha256_value(expected)
        actual_hash = sha256_value(actual)
        if expected_hash != actual_hash:
            raise ProjectionParityFailure(
                "Neo4j reasoning response differs from NetworkX for " + request["goal"]
            )
        cases.append(
            {
                "request_hash": sha256_value(request),
                "result_hash": expected_hash,
                "selected_concept_ids": [row["id"] for row in expected["selected_concepts"]],
                "path_edge_ids": [row["edge_id"] for row in expected["path_taken"]],
                "source_references_hash": sha256_value(expected["source_references"]),
                "evidence_ids": expected["evidence_ids"],
                "rejected_concepts_hash": sha256_value(expected["rejected_concepts"]),
                "alternatives_hash": sha256_value(expected["alternative_valid_paths"]),
                "knowledge_gap_hash": sha256_value(expected["knowledge_gap"]),
            }
        )
    return {
        "schema": "cpcs.graph_reasoning_parity/1.0",
        "policy_version": BACKEND_POLICY,
        "projection_policy": PROJECTION_POLICY,
        "case_count": len(cases),
        "cases": cases,
        "status": "passed",
    }


def watch_projection(
    *,
    interval_seconds: float,
    debounce_seconds: float,
    root: Path = REPO_ROOT,
    once: bool = False,
) -> dict[str, Any]:
    if not 0.25 <= interval_seconds <= 60.0:
        raise ValueError("interval_seconds must be between 0.25 and 60")
    if not 0.0 <= debounce_seconds <= 30.0:
        raise ValueError("debounce_seconds must be between 0 and 30")
    stop = False

    def request_stop(*_: Any) -> None:
        nonlocal stop
        stop = True

    if not once:
        signal.signal(signal.SIGTERM, request_stop)
        signal.signal(signal.SIGINT, request_stop)
    pending_hash = None
    pending_since = 0.0
    sync_count = 0
    while not stop:
        plan = build_projection_plan(root)
        status = projection_status(root)
        active_hash = (status.get("active_generation") or {}).get("authority_snapshot_hash")
        if active_hash != plan["authority_snapshot_hash"]:
            now = time.monotonic()
            if pending_hash != plan["authority_snapshot_hash"]:
                pending_hash = plan["authority_snapshot_hash"]
                pending_since = now
            if now - pending_since >= debounce_seconds:
                sync_projection(expected_snapshot_hash=pending_hash, root=root)
                sync_count += 1
                pending_hash = None
        else:
            pending_hash = None
        if once:
            break
        time.sleep(interval_seconds)
    return {
        "schema": "cpcs.graph_projection_watch/1.0",
        "policy_version": PROJECTION_POLICY,
        "sync_count": sync_count,
        "stopped": True,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("status")
    sync_parser = subparsers.add_parser("sync")
    sync_parser.add_argument("--expected-snapshot-hash", required=True)
    parity_parser = subparsers.add_parser("parity")
    parity_parser.add_argument("request_file", type=Path)
    watch_parser = subparsers.add_parser("watch")
    watch_parser.add_argument("--interval-seconds", type=float, default=1.0)
    watch_parser.add_argument("--debounce-seconds", type=float, default=1.0)
    watch_parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "plan":
        result = projection_plan_summary()
    elif args.command == "status":
        result = projection_status()
    elif args.command == "sync":
        result = sync_projection(expected_snapshot_hash=args.expected_snapshot_hash)
    elif args.command == "parity":
        value = json.loads(args.request_file.read_text(encoding="utf-8"))
        requests = value if isinstance(value, list) else value["requests"]
        result = reasoning_parity(requests)
    else:
        result = watch_projection(
            interval_seconds=args.interval_seconds,
            debounce_seconds=args.debounce_seconds,
            once=args.once,
        )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
