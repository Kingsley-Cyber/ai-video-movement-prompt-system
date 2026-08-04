"""Deterministic, explainable multi-hop reasoning over the live graph."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import networkx as nx

from .authority import authority_reader
from .graph import AUTHORED_EDGE_POLICY, build_live_graph, traversal_steps
from .indexes import build_index_catalog, retrieval_diagnostics
from .rules import controls_for_selection, evaluate_rules
from .temporal import TEMPORAL_POLICY, replacement_trace, validate_temporal_request, visible_records
from .validate import REPO_ROOT, read_jsonl, sha256_value, validate_instance

STOP = {
    "a", "an", "and", "based", "for", "he", "in", "is", "it", "just", "make",
    "makes", "making", "of", "on", "one", "or", "she", "the", "their", "this",
    "to", "where", "with", "without",
}
STATUS_RANK = {
    "deprecated": -2,
    "unexplored": -1,
    "ingested": 0,
    "partial": 1,
    "proven": 2,
}
MINIMUM_RANK = {"ingested": 0, "partial": 1, "proven": 2}
HARD_EDGE_TYPES = {"conflicts_with", "invalid_for"}
ALLOWED_ADMISSION_REASONS = frozenset(
    {
        "direct_match",
        "structural_term_support",
        "operational_bridge",
        "required_prerequisite",
    }
)
QUERY_POLICY = {
    "version": "cpcs-query/1.6",
    "minimum_root_score": 1.2,
    "maximum_roots": 6,
    "maximum_legacy_hops": 3,
    "root_diversity": "exact-semantic-signature/1.0",
}
GAP_POLICY = {
    "version": "cpcs-gap-policy/1.1",
}


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 1 and token not in STOP
    }


def _semantic_score(node: dict[str, Any], query_tokens: set[str]) -> float:
    score = 0.0
    for trigger in node.get("nl_triggers", []):
        tokens = _tokens(trigger)
        if tokens:
            score += 4.0 * len(tokens & query_tokens) / len(tokens)
    score += 2.0 * len(_tokens(node.get("name", "")) & query_tokens)
    score += 0.4 * len(
        _tokens(" ".join(str(node.get(key, "")) for key in ("what", "use_when", "layer"))) & query_tokens
    )
    return round(score, 6)


def _retrieval_tokens(node: dict[str, Any]) -> set[str]:
    return _tokens(
        " ".join(
            str(node.get(key, ""))
            for key in ("name", "what", "use_when", "nl_triggers", "layer")
        )
    )


def _is_root_match(
    node: dict[str, Any],
    query_tokens: set[str],
    score: float,
) -> bool:
    if score < QUERY_POLICY["minimum_root_score"]:
        return False
    if len(query_tokens) <= 1:
        return True
    if len(query_tokens & _retrieval_tokens(node)) >= 2:
        return True
    name_tokens = _tokens(node.get("name", ""))
    if name_tokens and name_tokens <= query_tokens:
        return True
    return any(
        len(trigger_tokens) == 1 and trigger_tokens <= query_tokens
        for trigger in node.get("nl_triggers", [])
        if (trigger_tokens := _tokens(trigger))
    )


def _knowledge_gap(
    graph: nx.MultiDiGraph,
    query_tokens: set[str],
    roots: list[tuple[float, str]],
    goal: str,
) -> dict[str, Any]:
    covered = set()
    for _, node_id in roots:
        covered.update(query_tokens & _retrieval_tokens(graph.nodes[node_id]))
    uncovered = sorted(query_tokens - covered)
    coverage = round(
        len(covered) / len(query_tokens),
        6,
    ) if query_tokens else 1.0
    if not roots:
        status = "missing"
        should_retrieve = True
        reason = "no_semantic_roots"
    elif uncovered:
        status = "partial"
        should_retrieve = True
        reason = "material_query_terms_uncovered"
    else:
        status = "none"
        should_retrieve = False
        reason = "all_material_query_terms_covered"
    return {
        "status": status,
        "should_retrieve": should_retrieve,
        "coverage": coverage,
        "covered_terms": sorted(covered),
        "uncovered_terms": uncovered,
        "suggested_query": " ".join(uncovered) if uncovered else goal,
        "reason": reason,
        "policy_version": GAP_POLICY["version"],
    }


def _root_eligible(node: dict[str, Any], request: dict[str, Any]) -> bool:
    status = node.get("status", "unexplored")
    if status == "deprecated":
        return False
    if not request["include_unproven"] and STATUS_RANK.get(status, 0) < MINIMUM_RANK[request["minimum_status"]]:
        return False
    if node.get("layer") in set(request["excluded_layers"]):
        return False
    encodings = node.get("encodable_as")
    if encodings and request["target_format"] not in encodings and "hybrid" not in encodings:
        return False
    return True


def _root_signature(node: dict[str, Any]) -> str:
    """Identify exact semantic duplicates without using durable IDs or fixture metadata."""
    payload = {
        "name": node.get("name", ""),
        "what": node.get("what", ""),
        "use_when": node.get("use_when", ""),
        "layer": node.get("layer", ""),
        "nl_triggers": node.get("nl_triggers", []),
        "encodable_as": node.get("encodable_as", []),
        "params": node.get("params", {}),
    }
    return "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _diverse_roots(
    candidates: list[tuple[float, str]],
    graph: nx.MultiDiGraph,
    maximum: int,
) -> tuple[list[tuple[float, str]], list[dict[str, Any]]]:
    selected: list[tuple[float, str]] = []
    representative_by_signature: dict[str, str] = {}
    suppressed: list[dict[str, Any]] = []
    for score, node_id in candidates:
        signature = _root_signature(graph.nodes[node_id])
        representative = representative_by_signature.get(signature)
        if representative is not None:
            suppressed.append(
                {
                    "concept_id": node_id,
                    "representative_id": representative,
                    "semantic_signature": signature,
                }
            )
            continue
        representative_by_signature[signature] = node_id
        if len(selected) < maximum:
            selected.append((score, node_id))
            if len(selected) == maximum:
                break
    return selected, suppressed


def default_request(goal: str, **overrides: Any) -> dict[str, Any]:
    value = {
        "goal": goal,
        "domain": None,
        "target_format": "hybrid",
        "provider": None,
        "model_version": None,
        "required_layers": [],
        "excluded_layers": [],
        "maximum_depth": 5,
        "minimum_status": "partial",
        "include_unproven": False,
        "deterministic_seed": 7,
        "as_of": None,
        "validity_mode": "current",
    }
    value.update(overrides)
    return value


def _incident_edges(graph: nx.MultiDiGraph, node_id: str) -> list[tuple[str, str, str, dict[str, Any]]]:
    edges: list[tuple[str, str, str, dict[str, Any]]] = []
    for u, v, key, data in graph.out_edges(node_id, keys=True, data=True):
        edges.append((u, v, key, data))
    for u, v, key, data in graph.in_edges(node_id, keys=True, data=True):
        edges.append((u, v, key, data))
    return sorted(edges, key=lambda item: (item[3].get("edge_type", ""), item[0], item[1], str(item[2])))


def _other(node_id: str, u: str, v: str) -> str:
    return v if u == node_id else u


def _conflict(
    graph: nx.MultiDiGraph,
    candidate: str,
    selected: set[str],
    domain: str | None,
) -> dict[str, Any] | None:
    for u, v, key, data in _incident_edges(graph, candidate):
        if data.get("edge_type") != "conflicts_with":
            continue
        other = _other(candidate, u, v)
        context = data.get("context", "all")
        if other in selected and (context == "all" or domain is None or context == domain):
            return {"candidate": candidate, "selected": other, "edge_id": str(key), "context": context}
    return None


def _domain_invalidity(
    graph: nx.MultiDiGraph,
    candidate: str,
    domain: str | None,
) -> dict[str, Any] | None:
    if not domain:
        return None
    node = graph.nodes[candidate]
    invalid_values = node.get("invalid_for", [])
    if isinstance(invalid_values, str):
        invalid_values = [invalid_values]
    if domain in invalid_values or "all" in invalid_values:
        return {"candidate": candidate, "domain": domain, "source": "concept"}
    valid_values = node.get("valid_for", [])
    if isinstance(valid_values, str):
        valid_values = [valid_values]
    if valid_values and domain not in valid_values and "all" not in valid_values:
        return {"candidate": candidate, "domain": domain, "source": "concept valid_for"}
    authored_valid_for: list[tuple[str, dict[str, Any]]] = []
    for u, v, key, data in _incident_edges(graph, candidate):
        edge_type = data.get("edge_type")
        context = data.get("context", "all")
        other = _other(candidate, u, v)
        if (
            edge_type == "invalid_for"
            and u == candidate
            and context in {"all", domain}
        ):
            return {
                "candidate": candidate,
                "domain": domain,
                "source": "authored edge",
                "edge_id": str(key),
            }
        if edge_type == "valid_for" and u == candidate:
            authored_valid_for.append(
                (
                    str(key),
                    {
                        "context": context,
                        "other": other,
                    },
                )
            )
    if authored_valid_for and not any(
        data["context"] in {"all", domain} or data["other"] == domain
        for _, data in authored_valid_for
    ):
        return {
            "candidate": candidate,
            "domain": domain,
            "source": "authored valid_for edges",
            "edge_ids": sorted(key for key, _ in authored_valid_for),
        }
    return None


def _requirement_edges(
    graph: nx.MultiDiGraph,
    candidate: str,
) -> list[tuple[str, str, dict[str, Any]]]:
    return sorted(
        (
            v,
            str(key),
            data,
        )
        for _, v, key, data in graph.out_edges(candidate, keys=True, data=True)
        if data.get("edge_type") == "requires"
    )


def _missing_requirements(
    graph: nx.MultiDiGraph,
    candidate: str,
    selected: set[str],
) -> list[str]:
    return sorted(
        required
        for required, _, _ in _requirement_edges(graph, candidate)
        if required not in selected
    )


def _canonical_cycle(cycle: list[str]) -> list[str]:
    body = cycle[:-1]
    start = min(range(len(body)), key=lambda index: body[index])
    ordered = body[start:] + body[:start]
    return ordered + [ordered[0]]


def _dependency_plan(
    graph: nx.MultiDiGraph,
    candidate: str,
) -> dict[str, Any]:
    state: dict[str, str] = {}
    stack: list[str] = []
    order: list[str] = []
    missing: set[str] = set()
    cycles: set[tuple[str, ...]] = set()
    required_by: dict[str, set[str]] = {}
    chain: dict[str, list[str]] = {candidate: []}
    incoming: dict[str, tuple[str, str, dict[str, Any]]] = {}

    def visit(node_id: str) -> None:
        if node_id not in graph or graph.nodes[node_id].get("node_type") != "concept":
            missing.add(node_id)
            return
        if state.get(node_id) == "done":
            return
        if state.get(node_id) == "visiting":
            start = stack.index(node_id)
            cycles.add(tuple(_canonical_cycle(stack[start:] + [node_id])))
            return
        state[node_id] = "visiting"
        stack.append(node_id)
        for required, edge_id, edge_data in _requirement_edges(graph, node_id):
            required_by.setdefault(required, set()).add(node_id)
            proposed_chain = chain[node_id] + [edge_id]
            if required not in chain or proposed_chain < chain[required]:
                chain[required] = proposed_chain
                incoming[required] = (node_id, edge_id, edge_data)
            visit(required)
        stack.pop()
        state[node_id] = "done"
        order.append(node_id)

    visit(candidate)
    return {
        "order": order,
        "missing": sorted(missing),
        "cycles": [list(item) for item in sorted(cycles)],
        "required_by": {
            key: sorted(value) for key, value in sorted(required_by.items())
        },
        "chain": chain,
        "incoming": incoming,
    }


def _admission_reason(
    graph: nx.MultiDiGraph,
    candidate: str,
    query_tokens: set[str],
    edge_data: dict[str, Any],
    mappings: list[dict[str, Any]],
) -> tuple[str | None, list[str]]:
    covered_terms = sorted(
        query_tokens & _retrieval_tokens(graph.nodes[candidate])
    )
    if edge_data.get("tier") == "temporary":
        return "direct_match", covered_terms
    if edge_data.get("traversal_family") == "operational":
        return "operational_bridge", covered_terms
    mapping_terms = set()
    for mapping in mappings:
        if mapping.get("concept_id") != candidate:
            continue
        mapping_terms.update(
            _tokens(
                " ".join(
                    str(mapping.get(key, ""))
                    for key in (
                        "target_id",
                        "target_type",
                        "encoding",
                        "mapping",
                    )
                )
            )
        )
    if query_tokens & mapping_terms:
        return "operational_bridge", covered_terms
    if covered_terms:
        return "structural_term_support", covered_terms
    return None, covered_terms


def _rejection_code(
    conflict: dict[str, Any] | None,
    domain_invalidity: dict[str, Any] | None,
    violations: list[dict[str, Any]],
) -> str:
    if conflict:
        return "conflict"
    if domain_invalidity:
        return "invalid_context"
    if violations:
        return "rule_violation"
    return "invalid_context"


def _learned_summary(
    edge_data: list[dict[str, Any]],
    provider: str | None,
    model_version: str | None,
    domain: str | None,
) -> tuple[float, float, int, list[dict[str, Any]]]:
    negative = 0.0
    positive = 0.0
    evidence_count = 0
    used: list[dict[str, Any]] = []
    for data in edge_data:
        if data.get("tier") != "derived":
            continue
        if provider and data.get("provider", "all") not in {provider, "all"}:
            continue
        if model_version and data.get("model_version") not in {model_version, "all"}:
            continue
        if domain and data.get("context") not in {domain, "all"}:
            continue
        weight = float(data.get("weight", 0.0))
        if weight < 0:
            negative += abs(weight)
        else:
            positive += weight
        evidence = data.get("evidence", [])
        evidence_count += len(evidence)
        used.append(
            {
                "edge_id": data.get("edge_id"),
                "type": data.get("edge_type"),
                "weight": weight,
                "evidence": evidence,
                "provider": data.get("provider", "all"),
                "model_version": data.get("model_version"),
                "evidence_scope": data.get("evidence_scope"),
                "evidence_trace": data.get("evidence_trace", []),
                "isolated_comparison": data.get("isolated_comparison"),
            }
        )
    return negative, positive, evidence_count, sorted(used, key=lambda item: item["edge_id"] or "")


def _admissibility(
    graph: nx.MultiDiGraph,
    candidate: str,
    selected: set[str],
    request: dict[str, Any],
    depth: int,
    rules: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
) -> tuple[
    bool,
    list[str],
    dict[str, Any] | None,
    dict[str, Any] | None,
    list[dict[str, Any]],
]:
    node = graph.nodes[candidate]
    reasons: list[str] = []
    trial = selected | {candidate}
    controls = controls_for_selection(
        mappings,
        trial,
        request.get("provider"),
        request.get("model_version"),
    )
    rule_results = evaluate_rules(rules, trial, controls)
    violations = [
        result
        for result in rule_results
        if not result["passed"] and result["severity"] in {"warning", "error"}
    ]
    for violation in violations:
        reasons.append(
            f"rule {violation['rule_id']} violated: {violation['message']}"
        )
    conflict = _conflict(graph, candidate, selected, request["domain"])
    if conflict:
        reasons.append(f"authored conflict with {conflict['selected']}")
    domain_invalidity = _domain_invalidity(
        graph, candidate, request["domain"]
    )
    if domain_invalidity:
        reasons.append(f"invalid for domain {request['domain']}")
    if node.get("layer") in set(request["excluded_layers"]):
        reasons.append(f"excluded layer {node.get('layer')}")
    encodings = node.get("encodable_as")
    if encodings and request["target_format"] not in encodings and "hybrid" not in encodings:
        reasons.append(f"unsupported encoding {request['target_format']}")
    missing = _missing_requirements(graph, candidate, selected)
    if missing:
        reasons.append("missing requirements: " + ", ".join(missing))
    if depth > request["maximum_depth"]:
        reasons.append("traversal depth exceeded")
    status = node.get("status", "unexplored")
    if status == "deprecated":
        reasons.append("deprecated concept")
    elif not request["include_unproven"] and STATUS_RANK.get(status, 0) < MINIMUM_RANK[request["minimum_status"]]:
        reasons.append(f"status {status} below minimum {request['minimum_status']}")
    return not reasons, reasons, conflict, domain_invalidity, violations


def _candidate_priority(
    graph: nx.MultiDiGraph,
    candidate: str,
    selected: set[str],
    request: dict[str, Any],
    depth: int,
    traversal_rank: int,
    retrieval_score: float,
    rules: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
) -> tuple[Any, ...]:
    node = graph.nodes[candidate]
    trial = selected | {candidate}
    controls = controls_for_selection(
        mappings,
        trial,
        request.get("provider"),
        request.get("model_version"),
    )
    rule_violations = sum(
        1
        for result in evaluate_rules(rules, trial, controls)
        if not result["passed"] and result["severity"] in {"warning", "error"}
    )
    conflict = int(_conflict(graph, candidate, selected, request["domain"]) is not None)
    domain_invalid = int(
        _domain_invalidity(graph, candidate, request["domain"]) is not None
    )
    encodings = node.get("encodable_as")
    unsupported = int(
        bool(encodings)
        and request["target_format"] not in encodings
        and "hybrid" not in encodings
    )
    missing = len(_missing_requirements(graph, candidate, selected))
    edge_items = [data for _, _, _, data in _incident_edges(graph, candidate)]
    negative, positive, evidence_count, _ = _learned_summary(
        edge_items,
        request.get("provider"),
        request["model_version"],
        request["domain"],
    )
    return (
        rule_violations,
        conflict,
        domain_invalid,
        unsupported,
        missing,
        -round(retrieval_score, 6),
        traversal_rank,
        depth,
        negative,
        -positive,
        -evidence_count,
        candidate,
    )


@authority_reader("reason_snapshot")
def reason(request: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    validate_instance("reasoning_query", request, root)
    validate_temporal_request(request["validity_mode"], request["as_of"])
    graph = build_live_graph(
        root,
        validity_mode=request["validity_mode"],
        as_of=request["as_of"],
    )
    sb = root / "lab" / "second_brain"
    rules = visible_records(
        read_jsonl(sb / "curated" / "rules.jsonl"),
        request["validity_mode"],
        request["as_of"],
    )
    mappings = visible_records(
        read_jsonl(sb / "curated" / "mappings.jsonl"),
        request["validity_mode"],
        request["as_of"],
    )
    catalog = build_index_catalog(
        root,
        validity_mode=request["validity_mode"],
        as_of=request["as_of"],
    )
    retrieval = retrieval_diagnostics(request["goal"], catalog)
    goal_digest = hashlib.sha256(
        json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:12]
    query_id = f"query:{request['deterministic_seed']}:{goal_digest}"
    graph.add_node(query_id, node_type="query", tier="temporary", goal=request["goal"])
    query_tokens = _tokens(request["goal"])
    fused_scores = {
        row["concept_id"]: row["score"]
        for row in retrieval["fused"]
    }
    semantic = []
    for node_id, data in graph.nodes(data=True):
        if data.get("node_type") != "concept":
            continue
        base_score = _semantic_score(data, query_tokens)
        semantic.append(
            (
                round(base_score + fused_scores.get(node_id, 0.0), 6),
                base_score,
                node_id,
            )
        )
    root_candidates = [
        (fused_score, node_id)
        for fused_score, base_score, node_id in semantic
        if _is_root_match(graph.nodes[node_id], query_tokens, base_score)
    ]
    root_candidates.sort(key=lambda item: (-item[0], item[1]))
    eligible_candidates = [
        item for item in root_candidates if _root_eligible(graph.nodes[item[1]], request)
    ]
    rejected_candidates = [
        item for item in root_candidates if not _root_eligible(graph.nodes[item[1]], request)
    ]
    eligible_roots, eligible_suppressed = _diverse_roots(
        eligible_candidates,
        graph,
        QUERY_POLICY["maximum_roots"],
    )
    rejected_roots, rejected_suppressed = _diverse_roots(
        rejected_candidates,
        graph,
        QUERY_POLICY["maximum_roots"],
    )
    suppressed_roots = sorted(
        eligible_suppressed + rejected_suppressed,
        key=lambda row: (row["representative_id"], row["concept_id"]),
    )
    roots = sorted(eligible_roots + rejected_roots, key=lambda item: (-item[0], item[1]))
    knowledge_gap = _knowledge_gap(
        graph,
        query_tokens,
        eligible_roots,
        request["goal"],
    )
    for score, node_id in roots:
        graph.add_edge(
            query_id,
            node_id,
            key=f"query_start:{node_id}",
            edge_id=f"query_start:{node_id}",
            edge_type="semantic_start",
            tier="temporary",
            score=score,
            traversal_direction="forward",
            traversal_transition="semantic_match",
            traversal_family="retrieval",
            traversal_rank=0,
        )

    selected: set[str] = set()
    selected_rows: list[dict[str, Any]] = []
    selected_index: dict[str, dict[str, Any]] = {}
    selected_semantic_representatives: dict[str, str] = {}
    suppressed_semantic_duplicates: dict[str, dict[str, Any]] = {}
    expanded: set[str] = set()
    rejected: dict[str, dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    domain_rejections: list[dict[str, Any]] = []
    rule_violations: list[dict[str, Any]] = []
    paths: list[dict[str, Any]] = []
    path_ids: dict[str, list[str]] = {}
    alternatives: list[dict[str, Any]] = []
    learned_used: list[dict[str, Any]] = []
    evidence_ids: set[str] = set()
    sources: dict[str, list[str]] = {}
    frontier: dict[
        tuple[str, int, str, int],
        tuple[str, int, str, str, dict[str, Any], int],
    ] = {}
    queued: set[tuple[str, int, str, int]] = set()
    legacy_hops_enqueued = 0

    rejection_priority = {
        "dependency_cycle": 0,
        "missing_prerequisite": 1,
        "conflict": 2,
        "rule_violation": 3,
        "invalid_context": 4,
        "connectivity_only": 5,
    }

    def enqueue(
        node_id: str,
        depth: int,
        parent: str,
        edge_key: str,
        edge_data: dict[str, Any],
        legacy_count: int,
    ) -> None:
        if graph.nodes[node_id].get("node_type") != "concept":
            return
        semantic_signature = _root_signature(graph.nodes[node_id])
        semantic_representative = selected_semantic_representatives.get(
            semantic_signature
        )
        if semantic_representative is not None and node_id != semantic_representative:
            suppressed_semantic_duplicates.setdefault(
                node_id,
                {
                    "concept_id": node_id,
                    "representative_id": semantic_representative,
                    "semantic_signature": semantic_signature,
                    "via_edge": edge_key,
                },
            )
            return
        signature = (node_id, depth, parent, legacy_count)
        if signature not in queued:
            queued.add(signature)
            frontier[signature] = (
                node_id,
                depth,
                parent,
                edge_key,
                edge_data,
                legacy_count,
            )

    def record_rejection(
        node_id: str,
        reason_code: str,
        reasons: list[str],
        via_edge: str,
        **details: Any,
    ) -> None:
        row = {
            "id": node_id,
            "name": graph.nodes[node_id].get("name") if node_id in graph else None,
            "reason_code": reason_code,
            "reasons": reasons,
            "via_edge": via_edge,
            "policy_version": QUERY_POLICY["version"],
            **details,
        }
        existing = rejected.get(node_id)
        if (
            existing is None
            or rejection_priority[reason_code]
            < rejection_priority.get(existing.get("reason_code"), 99)
        ):
            rejected[node_id] = row

    def make_path_row(
        parent: str,
        node_id: str,
        edge_key: str,
        edge_data: dict[str, Any],
        depth: int,
    ) -> dict[str, Any]:
        return {
            "from": parent,
            "to": node_id,
            "edge_id": edge_key,
            "edge_type": edge_data.get("edge_type"),
            "tier": edge_data.get("tier"),
            "depth": depth,
            "direction": edge_data.get("traversal_direction"),
            "transition": edge_data.get("traversal_transition"),
            "family": edge_data.get("traversal_family"),
            "policy_version": (
                QUERY_POLICY["version"]
                if edge_data.get("tier") == "temporary"
                else AUTHORED_EDGE_POLICY["version"]
            ),
        }

    def commit_selection(
        node_id: str,
        admission_reason: str,
        required_by: list[str],
        covered_terms: list[str],
        parent: str,
        edge_key: str,
        edge_data: dict[str, Any],
        depth: int,
        selected_path: list[str],
    ) -> None:
        rejected.pop(node_id, None)
        selected.add(node_id)
        node = graph.nodes[node_id]
        selected_semantic_representatives.setdefault(
            _root_signature(node),
            node_id,
        )
        row = {
            "id": node_id,
            "name": node.get("name"),
            "layer": node.get("layer"),
            "status": node.get("status"),
            "depth": depth,
            "admission_reason": admission_reason,
            "required_by": sorted(required_by),
            "path": selected_path,
            "covered_terms": covered_terms,
            "policy_version": QUERY_POLICY["version"],
        }
        selected_rows.append(row)
        selected_index[node_id] = row
        path_ids[node_id] = selected_path
        paths.append(
            make_path_row(
                parent,
                node_id,
                edge_key,
                edge_data,
                depth,
            )
        )
        edge_items = [
            data for _, _, _, data in _incident_edges(graph, node_id)
        ]
        _, _, _, learned = _learned_summary(
            edge_items,
            request.get("provider"),
            request["model_version"],
            request["domain"],
        )
        for item in learned:
            learned_used.append(item)
            evidence_ids.update(item["evidence"])
        evidence_ids.update(node.get("evidence", []))
        sources[node_id] = node.get("source", [])

    def expand(
        node_id: str,
        depth: int,
        legacy_count: int,
    ) -> None:
        nonlocal legacy_hops_enqueued
        if node_id in expanded or depth >= request["maximum_depth"]:
            return
        expanded.add(node_id)
        for u, v, key, data in _incident_edges(graph, node_id):
            neighbor = _other(node_id, u, v)
            if graph.nodes[neighbor].get("node_type") != "concept":
                continue
            if data.get("edge_type") not in HARD_EDGE_TYPES:
                continue
            if data.get("edge_type") == "conflicts_with":
                context = data.get("context", "all")
                if (
                    context in {"all", request["domain"]}
                    or request["domain"] is None
                ):
                    conflict_row = {
                        "candidate": neighbor,
                        "selected": node_id,
                        "edge_id": str(key),
                        "context": context,
                    }
                    conflicts.append(conflict_row)
                    record_rejection(
                        neighbor,
                        "conflict",
                        [f"authored conflict with {node_id}"],
                        str(key),
                    )
            elif (
                u == neighbor
                and request["domain"]
                and data.get("context", "all")
                in {"all", request["domain"]}
            ):
                invalidity = {
                    "candidate": neighbor,
                    "domain": request["domain"],
                    "source": "authored edge",
                    "edge_id": str(key),
                }
                domain_rejections.append(invalidity)
                record_rejection(
                    neighbor,
                    "invalid_context",
                    [f"invalid for domain {request['domain']}"],
                    str(key),
                )
        for step in traversal_steps(graph, node_id):
            data = step["edge_data"]
            if data.get("tier") == "derived" and request.get("provider"):
                if data.get("provider", "all") not in {
                    request["provider"],
                    "all",
                }:
                    continue
            if data.get("tier") == "derived" and request["model_version"]:
                if data.get("model_version") not in {
                    request["model_version"],
                    "all",
                }:
                    continue
            if (
                step["family"] == "legacy_association"
                and step["maximum_per_path"] is not None
                and legacy_count >= step["maximum_per_path"]
            ):
                continue
            if (
                step["family"] == "legacy_association"
                and legacy_hops_enqueued
                >= QUERY_POLICY["maximum_legacy_hops"]
            ):
                continue
            next_legacy_count = legacy_count + int(
                step["family"] == "legacy_association"
            )
            decorated = dict(data)
            decorated.update(
                {
                    "traversal_direction": step["direction"],
                    "traversal_transition": step["transition"],
                    "traversal_family": step["family"],
                    "traversal_rank": step["rank"],
                }
            )
            enqueue(
                step["neighbor"],
                depth + 1,
                node_id,
                step["edge_id"],
                decorated,
                next_legacy_count,
            )
            if step["family"] == "legacy_association":
                legacy_hops_enqueued += 1

    for score, node_id in roots:
        edge_key = f"query_start:{node_id}"
        enqueue(
            node_id,
            0,
            query_id,
            edge_key,
            graph.edges[query_id, node_id, edge_key],
            0,
        )

    while frontier and len(selected_rows) < 25:
        signature, item = min(
            frontier.items(),
            key=lambda entry: (
                _candidate_priority(
                    graph,
                    entry[1][0],
                    selected,
                    request,
                    entry[1][1],
                    int(entry[1][4].get("traversal_rank", 0)),
                    float(entry[1][4].get("score", 0.0)),
                    rules,
                    mappings,
                ),
                entry[1][2],
                entry[1][3],
            ),
        )
        node_id, depth, parent, edge_key, edge_data, legacy_count = item
        del frontier[signature]
        admission_reason, covered_terms = _admission_reason(
            graph,
            node_id,
            query_tokens,
            edge_data,
            mappings,
        )
        if node_id in selected:
            alternatives.append(
                {
                    "concept_id": node_id,
                    "from": parent,
                    "edge_id": edge_key,
                    "edge_type": edge_data.get("edge_type"),
                    "direction": edge_data.get("traversal_direction"),
                    "transition": edge_data.get("traversal_transition"),
                    "family": edge_data.get("traversal_family"),
                    "depth": depth,
                }
            )
            if admission_reason and node_id not in expanded:
                if admission_reason == "direct_match":
                    selected_index[node_id]["admission_reason"] = admission_reason
                    selected_index[node_id]["covered_terms"] = covered_terms
                    direct_path = path_ids.get(parent, []) + [edge_key]
                    selected_index[node_id]["path"] = direct_path
                    path_ids[node_id] = direct_path
                expand(node_id, depth, legacy_count)
            continue
        semantic_signature = _root_signature(graph.nodes[node_id])
        semantic_representative = selected_semantic_representatives.get(
            semantic_signature
        )
        if semantic_representative is not None:
            suppressed_semantic_duplicates.setdefault(
                node_id,
                {
                    "concept_id": node_id,
                    "representative_id": semantic_representative,
                    "semantic_signature": semantic_signature,
                    "via_edge": edge_key,
                },
            )
            continue
        if admission_reason is None:
            record_rejection(
                node_id,
                "connectivity_only",
                ["graph reachability without continuing goal relevance"],
                edge_key,
            )
            continue

        plan = _dependency_plan(graph, node_id)
        if plan["cycles"]:
            cycle = plan["cycles"][0]
            for member in sorted(set(cycle[:-1])):
                record_rejection(
                    member,
                    "dependency_cycle",
                    ["dependency cycle: " + " -> ".join(cycle)],
                    edge_key,
                    dependency_cycle=cycle,
                )
            continue
        if plan["missing"]:
            record_rejection(
                node_id,
                "missing_prerequisite",
                [
                    "missing prerequisites: "
                    + ", ".join(plan["missing"])
                ],
                edge_key,
                missing_prerequisites=plan["missing"],
            )
            continue

        trial_selected = set(selected)
        failed_requirement: str | None = None
        for planned in plan["order"]:
            if planned in trial_selected:
                continue
            planned_depth = depth + len(plan["chain"].get(planned, []))
            disposition = _admissibility(
                graph,
                planned,
                trial_selected,
                request,
                planned_depth,
                rules,
                mappings,
            )
            (
                admissible,
                reasons,
                conflict,
                invalidity,
                violations,
            ) = disposition
            if not admissible:
                code = _rejection_code(conflict, invalidity, violations)
                record_rejection(
                    planned,
                    code,
                    reasons,
                    (
                        plan["incoming"].get(planned, (None, edge_key, None))[1]
                    ),
                )
                if conflict:
                    conflicts.append(conflict)
                if invalidity:
                    domain_rejections.append(invalidity)
                rule_violations.extend(
                    {"candidate": planned, **violation}
                    for violation in violations
                )
                failed_requirement = planned
                break
            trial_selected.add(planned)
        if failed_requirement is not None:
            if failed_requirement != node_id:
                record_rejection(
                    node_id,
                    "missing_prerequisite",
                    [
                        "prerequisite was not admissible: "
                        + failed_requirement
                    ],
                    edge_key,
                    missing_prerequisites=[failed_requirement],
                )
            continue

        base_path = path_ids.get(parent, []) + [edge_key]
        for planned in plan["order"]:
            required_by = plan["required_by"].get(planned, [])
            if planned in selected:
                row = selected_index[planned]
                row["required_by"] = sorted(
                    set(row["required_by"]) | set(required_by)
                )
                continue
            if planned == node_id:
                planned_reason = admission_reason
                planned_parent = parent
                planned_edge_key = edge_key
                planned_edge_data = edge_data
                planned_depth = depth
                planned_path = base_path
            else:
                (
                    planned_parent,
                    planned_edge_key,
                    raw_edge_data,
                ) = plan["incoming"][planned]
                planned_edge_data = dict(raw_edge_data)
                planned_edge_data.update(
                    {
                        "traversal_direction": "forward",
                        "traversal_transition": "requires",
                        "traversal_family": "dependency",
                        "traversal_rank": AUTHORED_EDGE_POLICY["types"][
                            "requires"
                        ]["rank"],
                    }
                )
                planned_reason = "required_prerequisite"
                planned_depth = depth + len(plan["chain"][planned])
                planned_path = base_path + plan["chain"][planned]
            planned_covered = sorted(
                query_tokens
                & _retrieval_tokens(graph.nodes[planned])
            )
            commit_selection(
                planned,
                planned_reason,
                required_by,
                planned_covered,
                planned_parent,
                planned_edge_key,
                planned_edge_data,
                planned_depth,
                planned_path,
            )
        expand(node_id, depth, legacy_count)

    selected_layers = {row["layer"] for row in selected_rows}
    missing_layers = sorted(set(request["required_layers"]) - selected_layers)
    ambiguity = []
    if missing_layers:
        ambiguity.append("No admissible selected concept covered required layers: " + ", ".join(missing_layers))
    if not roots:
        ambiguity.append("No semantic starting concept matched the goal.")
    if knowledge_gap["status"] != "none":
        ambiguity.append(
            "Knowledge coverage is "
            + knowledge_gap["status"]
            + "; retrieve: "
            + knowledge_gap["suggested_query"]
        )
    semantic_duplicate_rows = sorted(
        suppressed_semantic_duplicates.values(),
        key=lambda row: (row["representative_id"], row["concept_id"], row["via_edge"]),
    )
    result = {
        "policy_version": QUERY_POLICY["version"],
        "query": request,
        "retrieval_candidates": retrieval,
        "root_selection": {
            "policy_version": QUERY_POLICY["root_diversity"],
            "selected_root_ids": [node_id for _, node_id in eligible_roots],
            "suppressed_exact_duplicates": len(suppressed_roots),
            "suppressed_hash": sha256_value(suppressed_roots),
            "suppressed_preview": suppressed_roots[:20],
        },
        "semantic_deduplication": {
            "policy_version": QUERY_POLICY["root_diversity"],
            "suppressed_exact_duplicates": len(semantic_duplicate_rows),
            "suppressed_hash": sha256_value(semantic_duplicate_rows),
            "suppressed_preview": semantic_duplicate_rows[:20],
        },
        "selected_concepts": selected_rows,
        "rejected_concepts": sorted(rejected.values(), key=lambda item: item["id"]),
        "path_taken": paths,
        "edge_types_used": sorted({row["edge_type"] for row in paths}),
        "conflicts_encountered": sorted(
            {json.dumps(item, sort_keys=True) for item in conflicts}
        ),
        "domain_rejections": sorted(
            {json.dumps(item, sort_keys=True) for item in domain_rejections}
        ),
        "rule_violations": sorted(
            {json.dumps(item, sort_keys=True) for item in rule_violations}
        ),
        "evidence_ids": sorted(evidence_ids),
        "learned_weights": sorted(
            {json.dumps(item, sort_keys=True) for item in learned_used}
        ),
        "source_references": sources,
        "knowledge_gap": knowledge_gap,
        "unresolved_ambiguity": ambiguity,
        "alternative_valid_paths": sorted(
            alternatives, key=lambda item: (item["concept_id"], item["depth"], item["from"])
        )[:20],
    }
    concept_records = read_jsonl(root / "lab" / "concepts.jsonl")
    visible_ids = sorted(
        node_id
        for node_id, data in graph.nodes(data=True)
        if data.get("node_type") == "concept"
    )
    all_concept_ids = sorted(record["id"] for record in concept_records)
    traces = [
        replacement_trace(row["id"], concept_records)
        for row in selected_rows
        if "validity" in next(
            record for record in concept_records if record["id"] == row["id"]
        )
    ]
    result["temporal_query"] = {
        "policy_version": TEMPORAL_POLICY["version"],
        "validity_mode": request["validity_mode"],
        "as_of": request["as_of"],
        "visible_concept_count": len(visible_ids),
        "filtered_concept_ids": sorted(set(all_concept_ids) - set(visible_ids)),
        "replacement_traces": traces,
    }
    result["conflicts_encountered"] = [json.loads(item) for item in result["conflicts_encountered"]]
    result["domain_rejections"] = [json.loads(item) for item in result["domain_rejections"]]
    result["rule_violations"] = [json.loads(item) for item in result["rule_violations"]]
    result["learned_weights"] = [json.loads(item) for item in result["learned_weights"]]
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("reason")
    command.add_argument("goal")
    command.add_argument("--domain")
    command.add_argument("--target-format", choices=("prose", "yaml", "json", "xml", "hybrid"), default="hybrid")
    command.add_argument("--provider")
    command.add_argument("--model-version")
    command.add_argument("--maximum-depth", type=int, default=5)
    command.add_argument("--minimum-status", choices=("ingested", "partial", "proven"), default="partial")
    command.add_argument("--include-unproven", action="store_true")
    command.add_argument("--required-layer", action="append", default=[])
    command.add_argument("--excluded-layer", action="append", default=[])
    command.add_argument("--seed", type=int, default=7)
    command.add_argument("--as-of")
    command.add_argument(
        "--validity-mode",
        choices=("current", "historical", "all_versions"),
        default="current",
    )
    args = parser.parse_args(argv)
    request = default_request(
        args.goal,
        domain=args.domain,
        target_format=args.target_format,
        provider=args.provider,
        model_version=args.model_version,
        required_layers=args.required_layer,
        excluded_layers=args.excluded_layer,
        maximum_depth=args.maximum_depth,
        minimum_status=args.minimum_status,
        include_unproven=args.include_unproven,
        deterministic_seed=args.seed,
        as_of=args.as_of,
        validity_mode=args.validity_mode,
    )
    print(json.dumps(reason(request), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
