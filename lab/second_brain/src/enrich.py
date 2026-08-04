"""Enrich a safe CPCS context bundle only when its query declares a gap."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Callable, Iterable

from .context import CONTEXT_POLICY, build_context_bundle
from .providers.polymath import ADAPTER_POLICY, retrieve as retrieve_polymath
from .query import GAP_POLICY, QUERY_POLICY
from .validate import REPO_ROOT, ValidationFailure, sha256_value, validate_instance

RetrievalFunction = Callable[..., dict[str, Any]]

ENRICHMENT_POLICY = {
    "version": "cpcs-context-enrichment/1.0",
    "external_retrieval": "gaps_only_exact_authorization",
}


def _build_context(
    query: str,
    *,
    token_budget: int,
    provider: str | None,
    model: str | None,
    minimum_status: str,
    include_external_evidence: bool,
    external_evidence: Iterable[dict[str, Any]] | None,
    domain: str | None,
    target_format: str,
    required_layers: Iterable[str],
    excluded_layers: Iterable[str],
    intent: str | None,
    as_of: str | None,
    validity_mode: str,
    root: Path,
) -> dict[str, Any]:
    return build_context_bundle(
        query,
        token_budget=token_budget,
        provider=provider,
        model=model,
        minimum_status=minimum_status,
        include_external_evidence=include_external_evidence,
        external_evidence=external_evidence,
        domain=domain,
        target_format=target_format,
        required_layers=required_layers,
        excluded_layers=excluded_layers,
        intent=intent,
        as_of=as_of,
        validity_mode=validity_mode,
        root=root,
    )


def _result(
    *,
    disposition: str,
    network_contacted: bool,
    initial_gap: dict[str, Any],
    retrieval: dict[str, Any] | None,
    context_bundle: dict[str, Any],
    retrieved_passages: int,
    root: Path,
) -> dict[str, Any]:
    packed_passages = len(context_bundle["external_evidence"])
    value = {
        "schema": "cpcs.context_enrichment/1.0",
        "disposition": disposition,
        "external_retrieval_policy": ENRICHMENT_POLICY["external_retrieval"],
        "network_contacted": network_contacted,
        "initial_knowledge_gap": copy.deepcopy(initial_gap),
        "retrieval": copy.deepcopy(retrieval),
        "context_bundle": context_bundle,
        "packing": {
            "retrieved_passages": retrieved_passages,
            "packed_passages": packed_passages,
            "omitted_passages": retrieved_passages - packed_passages,
        },
        "authority_effect": "none",
        "policy_versions": {
            "enrichment": ENRICHMENT_POLICY["version"],
            "context": CONTEXT_POLICY["version"],
            "query": QUERY_POLICY["version"],
            "gap": GAP_POLICY["version"],
            "polymath": ADAPTER_POLICY,
        },
    }
    validate_instance("context_enrichment", value, root)
    return value


def enrich_context_bundle(
    query: str,
    *,
    token_budget: int,
    rights_basis: str,
    provider: str | None = None,
    model: str | None = None,
    minimum_status: str = "ingested",
    domain: str | None = None,
    target_format: str = "hybrid",
    required_layers: Iterable[str] = (),
    excluded_layers: Iterable[str] = (),
    intent: str | None = None,
    as_of: str | None = None,
    validity_mode: str = "current",
    corpus_ids: list[str] | None = None,
    tool: str = "polymath_search",
    retrieval_tier: str = "qdrant_mongo",
    top_k: int = 8,
    rerank_enabled: bool = True,
    search_mode: str = "local",
    retrieval_fn: RetrievalFunction | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Return local context or one exact-gap Polymath enrichment without writes."""
    initial = _build_context(
        query,
        token_budget=token_budget,
        provider=provider,
        model=model,
        minimum_status=minimum_status,
        include_external_evidence=False,
        external_evidence=None,
        domain=domain,
        target_format=target_format,
        required_layers=required_layers,
        excluded_layers=excluded_layers,
        intent=intent,
        as_of=as_of,
        validity_mode=validity_mode,
        root=root,
    )
    initial_gap = copy.deepcopy(initial["knowledge_gap"])
    if not initial_gap["should_retrieve"]:
        return _result(
            disposition="no_gap",
            network_contacted=False,
            initial_gap=initial_gap,
            retrieval=None,
            context_bundle=initial,
            retrieved_passages=0,
            root=root,
        )

    gap_query = initial_gap["suggested_query"]
    retrieve = retrieval_fn or retrieve_polymath
    try:
        package = retrieve(
            gap_query,
            corpus_ids=list(corpus_ids or []),
            rights_basis=rights_basis,
            tool=tool,
            retrieval_tier=retrieval_tier,
            top_k=top_k,
            rerank_enabled=rerank_enabled,
            search_mode=search_mode,
            root=root,
        )
        validate_instance("polymath_retrieval", package, root)
    except ValidationFailure as exc:
        raise RuntimeError("Polymath retrieval packet failed validation") from exc
    evidence = package["context_evidence"]
    passages = package["retrieved_passages"]["passages"]
    package_query = package["retrieved_passages"]["retrieval"]["query"]
    returned_count = package["diagnostics"]["returned_count"]
    if package_query != gap_query:
        raise RuntimeError("Polymath retrieval query does not match the declared gap query")
    if len(evidence) != len(passages) or returned_count != len(evidence):
        raise RuntimeError("Polymath retrieval packet passage counts are inconsistent")

    enriched = _build_context(
        query,
        token_budget=token_budget,
        provider=provider,
        model=model,
        minimum_status=minimum_status,
        include_external_evidence=True,
        external_evidence=evidence,
        domain=domain,
        target_format=target_format,
        required_layers=required_layers,
        excluded_layers=excluded_layers,
        intent=intent,
        as_of=as_of,
        validity_mode=validity_mode,
        root=root,
    )
    packed = len(enriched["external_evidence"])
    trace = {
        "packet_hash": sha256_value(package),
        "packet_schema": package["schema"],
        "adapter_policy": package["adapter_policy"],
        "query": gap_query,
        "protocol": copy.deepcopy(package["protocol"]),
        "diagnostics": copy.deepcopy(package["diagnostics"]),
        "retrieved_passages_schema": package["retrieved_passages"]["schema"],
    }
    return _result(
        disposition="enriched" if packed else "retrieved_not_packed",
        network_contacted=True,
        initial_gap=initial_gap,
        retrieval=trace,
        context_bundle=enriched,
        retrieved_passages=len(evidence),
        root=root,
    )
