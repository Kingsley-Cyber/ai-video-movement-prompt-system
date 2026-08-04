from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.enrich import enrich_context_bundle
from lab.second_brain.src.validate import canonical_json_bytes, validate_instance
from lab.second_brain.tests.helpers import concept, make_root


def authority_snapshot(root: Path) -> dict[str, bytes]:
    paths = [root / "lab/concepts.jsonl"]
    second_brain = root / "lab/second_brain"
    for tier in ("curated", "immutable", "derived", "staging"):
        tier_path = second_brain / tier
        if tier_path.exists():
            paths.extend(path for path in tier_path.rglob("*") if path.is_file())
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(paths)
    }


def retrieval_package(
    query: str,
    *,
    top_k: int = 4,
    passage: str = "Decimal spatial coordinates can identify a bounded movement target.",
) -> dict:
    content_hash = "sha256:" + hashlib.sha256(passage.encode("utf-8")).hexdigest()
    evidence = {
        "origin": "polymath_mcp",
        "source_id": "source-001",
        "locator": "chapter_2.section_4",
        "content_hash": content_hash,
        "passage": passage,
        "retrieval_query": query,
        "retrieved_at": "2026-08-04T00:00:00Z",
        "score": 0.91,
        "metadata": {
            "title": "Fixture research",
            "corpus_id": "corpus-001",
            "doc_id": "doc-001",
            "chunk_id": "chunk-001",
            "parent_id": None,
            "rank": 1,
            "retrieval_tool": "polymath_search",
        },
        "trust_class": "untrusted_external_evidence",
    }
    return {
        "schema": "cpcs.polymath_retrieval/1.0",
        "adapter_policy": "cpcs-polymath-mcp/1.0",
        "protocol": {
            "endpoint_hash": "sha256:" + "a" * 64,
            "protocol_version": "2026-07-28",
            "server_name": "fixture-polymath",
            "server_version": "1.0",
            "tool": "polymath_search",
            "tool_count": 2,
        },
        "retrieved_passages": {
            "schema": "cpcs.retrieved_passages/1.0",
            "retrieval": {
                "adapter": "polymath_mcp",
                "corpus_id": "corpus-001",
                "query": query,
                "tool": "polymath_search",
                "parameters": {"top_k": top_k},
                "retrieved_at": "2026-08-04T00:00:00Z",
            },
            "rights_basis": "owner_authorized_research",
            "passages": [
                {
                    "source_id": "source-001",
                    "title": "Fixture research",
                    "locator": "chapter_2.section_4",
                    "content_hash": content_hash,
                    "text": passage,
                }
            ],
        },
        "context_evidence": [evidence],
        "diagnostics": {
            "requested_count": top_k,
            "upstream_count": 1,
            "returned_count": 1,
            "truncated_count": 0,
            "duplicate_count": 0,
            "response_bytes": max(1, len(passage.encode("utf-8"))),
            "requested_corpus_ids": ["corpus-001"],
            "returned_corpus_ids": ["corpus-001"],
            "effective_tier": "qdrant_mongo",
            "downgrade_reason": None,
        },
    }


class ContextEnrichmentTests(unittest.TestCase):
    def test_no_declared_gap_performs_zero_retrieval_and_preserves_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory), [concept("c_alpha", "alpha")])
            before = authority_snapshot(root)

            def forbidden_retrieval(*args: object, **kwargs: object) -> dict:
                raise AssertionError("retrieval must not run without a declared gap")

            result = enrich_context_bundle(
                "alpha",
                token_budget=6_000,
                rights_basis="owner_authorized_research",
                retrieval_fn=forbidden_retrieval,
                root=root,
            )

            self.assertEqual(result["disposition"], "no_gap")
            self.assertFalse(result["network_contacted"])
            self.assertIsNone(result["retrieval"])
            self.assertEqual(result["context_bundle"]["external_evidence"], [])
            self.assertEqual(result["authority_effect"], "none")
            self.assertEqual(before, authority_snapshot(root))
            validate_instance("context_enrichment", result, root)

    def test_declared_gap_retrieves_exact_suggested_query_and_replays_from_packet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory), [concept("c_alpha", "alpha")])
            calls: list[tuple[tuple, dict]] = []

            def retrieve(query: str, **kwargs: object) -> dict:
                calls.append(((query,), copy.deepcopy(kwargs)))
                return retrieval_package(query, top_k=int(kwargs["top_k"]))

            before = authority_snapshot(root)
            first = enrich_context_bundle(
                "alpha quasar",
                token_budget=6_000,
                rights_basis="owner_authorized_research",
                corpus_ids=["corpus-001"],
                top_k=4,
                retrieval_fn=retrieve,
                root=root,
            )
            second = enrich_context_bundle(
                "alpha quasar",
                token_budget=6_000,
                rights_basis="owner_authorized_research",
                corpus_ids=["corpus-001"],
                top_k=4,
                retrieval_fn=retrieve,
                root=root,
            )

            gap_query = first["initial_knowledge_gap"]["suggested_query"]
            self.assertTrue(first["initial_knowledge_gap"]["should_retrieve"])
            self.assertEqual([call[0][0] for call in calls], [gap_query, gap_query])
            self.assertEqual(calls[0][1]["rights_basis"], "owner_authorized_research")
            self.assertEqual(calls[0][1]["corpus_ids"], ["corpus-001"])
            self.assertEqual(first["disposition"], "enriched")
            self.assertTrue(first["network_contacted"])
            self.assertEqual(first["retrieval"]["query"], gap_query)
            self.assertEqual(first["packing"]["retrieved_passages"], 1)
            self.assertEqual(first["packing"]["packed_passages"], 1)
            evidence = first["context_bundle"]["external_evidence"][0]
            self.assertEqual(evidence["retrieval_query"], gap_query)
            self.assertEqual(evidence["trust_class"], "untrusted_external_evidence")
            self.assertTrue(first["context_bundle"]["knowledge_gap"]["should_retrieve"])
            self.assertEqual(before, authority_snapshot(root))
            self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
            validate_instance("context_enrichment", first, root)

    def test_retrieved_passage_outside_budget_is_reported_without_leaking_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory), [concept("c_alpha", "alpha")])

            def retrieve(query: str, **kwargs: object) -> dict:
                return retrieval_package(
                    query,
                    top_k=int(kwargs["top_k"]),
                    passage="x" * 100_000,
                )

            result = enrich_context_bundle(
                "alpha quasar",
                token_budget=5_000,
                rights_basis="owner_authorized_research",
                top_k=4,
                retrieval_fn=retrieve,
                root=root,
            )

            self.assertEqual(result["disposition"], "retrieved_not_packed")
            self.assertEqual(result["packing"], {
                "retrieved_passages": 1,
                "packed_passages": 0,
                "omitted_passages": 1,
            })
            self.assertEqual(result["context_bundle"]["external_evidence"], [])
            self.assertNotIn("x" * 100, str(result["retrieval"]))
            self.assertTrue(
                any(
                    item["section"] == "external_evidence"
                    and item["reason"] == "token_budget_exceeded"
                    for item in result["context_bundle"]["budget_report"]["omitted_items"]
                )
            )

    def test_inconsistent_retrieval_packet_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory), [concept("c_alpha", "alpha")])

            def retrieve(query: str, **kwargs: object) -> dict:
                package = retrieval_package(query, top_k=int(kwargs["top_k"]))
                package["diagnostics"]["returned_count"] = 2
                return package

            with self.assertRaisesRegex(RuntimeError, "counts are inconsistent"):
                enrich_context_bundle(
                    "alpha quasar",
                    token_budget=6_000,
                    rights_basis="owner_authorized_research",
                    top_k=4,
                    retrieval_fn=retrieve,
                    root=root,
                )


if __name__ == "__main__":
    unittest.main()
