"""Deterministic, explainable multi-hop reasoning over the live graph."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import networkx as nx

from .graph import AUTHORED_EDGE_POLICY, build_live_graph, traversal_steps
from .rules import controls_for_selection, evaluate_rules
from .validate import REPO_ROOT, read_jsonl, validate_instance

STOP = {
    "a", "an", "and", "for", "in", "is", "it", "of", "on", "or", "the", "to", "with",
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
QUERY_POLICY = {
    "version": "cpcs-query/1.1",
    "minimum_root_score": 0.8,
    "complete_token_coverage": 0.6,
    "maximum_roots": 5,
    "maximum_legacy_hops": 3,
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
    elif coverage < QUERY_POLICY["complete_token_coverage"]:
        status = "partial"
    else:
        status = "none"
    return {
        "status": status,
        "should_retrieve": status != "none",
        "coverage": coverage,
        "covered_terms": sorted(covered),
        "uncovered_terms": uncovered,
        "suggested_query": " ".join(uncovered) if uncovered else goal,
        "policy_version": QUERY_POLICY["version"],
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


def _missing_requirements(graph: nx.MultiDiGraph, candidate: str, selected: set[str]) -> list[str]:
    required = [
        v
        for _, v, _, data in graph.out_edges(candidate, keys=True, data=True)
        if data.get("edge_type") == "requires"
    ]
    return sorted(item for item in required if item not in selected)


def _learned_summary(
    edge_data: list[dict[str, Any]],
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
                "model_version": data.get("model_version"),
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
        edge_items, request["model_version"], request["domain"]
    )
    return (
        rule_violations,
        conflict,
        domain_invalid,
        unsupported,
        missing,
        traversal_rank,
        depth,
        negative,
        -positive,
        -evidence_count,
        candidate,
    )


def reason(request: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    validate_instance("reasoning_query", request, root)
    graph = build_live_graph(root)
    sb = root / "lab" / "second_brain"
    rules = read_jsonl(sb / "curated" / "rules.jsonl")
    mappings = read_jsonl(sb / "curated" / "mappings.jsonl")
    goal_digest = hashlib.sha256(request["goal"].encode()).hexdigest()[:12]
    query_id = f"query:{request['deterministic_seed']}:{goal_digest}"
    graph.add_node(query_id, node_type="query", tier="temporary", goal=request["goal"])
    query_tokens = _tokens(request["goal"])
    semantic = [
        (_semantic_score(data, query_tokens), node_id)
        for node_id, data in graph.nodes(data=True)
        if data.get("node_type") == "concept"
    ]
    root_candidates = [
        (score, node_id)
        for score, node_id in semantic
        if _is_root_match(graph.nodes[node_id], query_tokens, score)
    ]
    root_candidates.sort(key=lambda item: (-item[0], item[1]))
    eligible_roots = [
        item for item in root_candidates if _root_eligible(graph.nodes[item[1]], request)
    ][: QUERY_POLICY["maximum_roots"]]
    rejected_roots = [
        item for item in root_candidates if not _root_eligible(graph.nodes[item[1]], request)
    ][: QUERY_POLICY["maximum_roots"]]
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
    rejected: dict[str, dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    domain_rejections: list[dict[str, Any]] = []
    rule_violations: list[dict[str, Any]] = []
    paths: list[dict[str, Any]] = []
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
                    rules,
                    mappings,
                ),
                entry[1][2],
                entry[1][3],
            ),
        )
        node_id, depth, parent, edge_key, edge_data, legacy_count = item
        del frontier[signature]
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
            continue
        admissible, reasons, conflict, invalidity, violations = _admissibility(
            graph,
            node_id,
            selected,
            request,
            depth,
            rules,
            mappings,
        )
        if not admissible:
            rejected.setdefault(
                node_id,
                {
                    "id": node_id,
                    "name": graph.nodes[node_id].get("name"),
                    "reasons": reasons,
                    "via_edge": edge_key,
                },
            )
            if conflict:
                conflicts.append(conflict)
            if invalidity:
                domain_rejections.append(invalidity)
            rule_violations.extend(
                {"candidate": node_id, **violation} for violation in violations
            )
            continue
        selected.add(node_id)
        node = graph.nodes[node_id]
        selected_rows.append(
            {
                "id": node_id,
                "name": node.get("name"),
                "layer": node.get("layer"),
                "status": node.get("status"),
                "depth": depth,
            }
        )
        path_row = {
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
        paths.append(path_row)
        edge_items = [data for _, _, _, data in _incident_edges(graph, node_id)]
        _, _, _, learned = _learned_summary(
            edge_items, request["model_version"], request["domain"]
        )
        for item in learned:
            learned_used.append(item)
            evidence_ids.update(item["evidence"])
        evidence_ids.update(node.get("evidence", []))
        sources[node_id] = node.get("source", [])
        if depth >= request["maximum_depth"]:
            continue
        for u, v, key, data in _incident_edges(graph, node_id):
            neighbor = _other(node_id, u, v)
            if graph.nodes[neighbor].get("node_type") != "concept":
                continue
            if data.get("edge_type") in HARD_EDGE_TYPES:
                if data.get("edge_type") == "conflicts_with":
                    context = data.get("context", "all")
                    if context in {"all", request["domain"]} or request["domain"] is None:
                        conflict_row = {
                            "candidate": neighbor,
                            "selected": node_id,
                            "edge_id": str(key),
                            "context": context,
                        }
                        conflicts.append(conflict_row)
                        rejected.setdefault(
                            neighbor,
                            {
                                "id": neighbor,
                                "name": graph.nodes[neighbor].get("name"),
                                "reasons": [f"authored conflict with {node_id}"],
                                "via_edge": str(key),
                            },
                        )
                elif (
                    u == neighbor
                    and request["domain"]
                    and data.get("context", "all") in {
                    "all",
                    request["domain"],
                    }
                ):
                    invalidity = {
                        "candidate": neighbor,
                        "domain": request["domain"],
                        "source": "authored edge",
                        "edge_id": str(key),
                    }
                    domain_rejections.append(invalidity)
                    rejected.setdefault(
                        neighbor,
                        {
                            "id": neighbor,
                            "name": graph.nodes[neighbor].get("name"),
                            "reasons": [f"invalid for domain {request['domain']}"],
                            "via_edge": str(key),
                        },
                    )
        for step in traversal_steps(graph, node_id):
            data = step["edge_data"]
            if data.get("tier") == "derived" and request["model_version"]:
                if data.get("model_version") not in {request["model_version"], "all"}:
                    continue
            if (
                step["family"] == "legacy_association"
                and step["maximum_per_path"] is not None
                and legacy_count >= step["maximum_per_path"]
            ):
                continue
            if (
                step["family"] == "legacy_association"
                and legacy_hops_enqueued >= QUERY_POLICY["maximum_legacy_hops"]
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
    result = {
        "query": request,
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
    )
    print(json.dumps(reason(request), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
