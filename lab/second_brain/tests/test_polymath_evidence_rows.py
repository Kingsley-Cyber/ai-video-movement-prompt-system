"""The adapter speaks the connected search contract (one corpus, mode, evidence_rows) beside the legacy one (plan slice 2).

The contract is read from the tool's own input schema, so the legacy fixture server and its tests are unchanged.
"""
from __future__ import annotations

import copy
import hashlib
import unittest

from lab.second_brain.src.providers import polymath

LIVE_SCHEMA = {"type": "object", "required": ["query", "corpus_id"], "properties": {
    "query": {"type": "string"}, "corpus_id": {"type": "string"},
    "mode": {"type": "string", "default": "HYBRID"}, "max_evidence": {"type": "integer", "default": 12}}}
LEGACY_SCHEMA = {"type": "object", "properties": {"query": {"type": "string"}, "corpus_ids": {"type": ["array", "null"]}}}


def row(n: int, text: str | None = None, **extra) -> dict:
    """One evidence row in the shape the connected server returned on 2026-10-05."""
    return {"id": f"chunk_{n:064x}", "kind": "chunk", "doc_id": f"doc_{n:064x}", "corpus_id": "cinema",
            "title": f"Book {n}.md", "source": f"Book {n}.md · Pages {n}",
            "text": text if text is not None else f"Passage {n}. The push lands from the feet up and the body reacts on the hit, never before it.",
            "text_clean": "cleaned", "timecode": None, "heading_path": [f"Book {n}", f"Pages {n}"],
            "char_start": 10 * n, "char_end": 10 * n + 120, "tier": "child", "lanes": ["reranked"],
            "score": 24.0 - n, "document": {"source_name": f"Book {n}.md", "frontmatter": {}}, "utility_role": "DIRECT", **extra}


def live_result(rows: list[dict]) -> dict:
    return {"mode": "HYBRID", "evidence_rows": rows, "evidence_contract": "retrieve-evidence-rows-v1",
            "graph_facts": 0, "latency_ms": 6391.8}


class FakeClient:
    def __init__(self, endpoint: str, token: str, *, schema: dict, result: dict, calls: list) -> None:
        self.endpoint, self.protocol_version = endpoint, polymath.MODERN_PROTOCOL
        self.server_info, self.tools = {"name": "polymath", "version": "test"}, {}
        self.schema, self.result, self.calls = schema, result, calls

    def connect(self) -> None:
        pass

    def list_tools(self) -> dict:
        self.tools = {"polymath_search": {"name": "polymath_search", "inputSchema": self.schema}}
        return copy.deepcopy(self.tools)

    def call_tool(self, name: str, arguments: dict) -> dict:
        self.calls.append((name, copy.deepcopy(arguments)))
        return copy.deepcopy(self.result)


class EvidenceRowsTests(unittest.TestCase):
    def retrieve(self, result: dict, *, schema: dict = LIVE_SCHEMA, **options) -> tuple[dict, list]:
        calls: list = []
        options = {"corpus_ids": ["cinema"], "rights_basis": "owner corpus, read-only directing research",
                   "endpoint": "https://polymath.example.test/mcp", "token": "test-token",
                   "retrieved_at": "2026-10-05T09:00:00Z", "mode": "HYBRID", "top_k": 6, **options}
        factory = lambda endpoint, token: FakeClient(endpoint, token, schema=schema, result=result, calls=calls)
        return polymath.retrieve("Film directing guidance for this scene: a shove", client_factory=factory, **options), calls

    def test_the_connected_contract_sends_one_corpus_and_maps_evidence_rows(self) -> None:
        package, calls = self.retrieve(live_result([row(1), row(2)]))
        self.assertEqual(calls, [("polymath_search", {"query": "Film directing guidance for this scene: a shove",
                                                      "corpus_id": "cinema", "mode": "HYBRID", "max_evidence": 6})])
        first = package["retrieved_passages"]["passages"][0]
        text = row(1)["text"]
        self.assertEqual(first, {"source_id": f"polymath://cinema/document/doc_{1:064x}", "title": "Book 1.md",
                                 "locator": f"chunk=chunk_{1:064x}", "text": text,
                                 "content_hash": "sha256:" + hashlib.sha256(text.encode()).hexdigest()})
        parameters = package["retrieved_passages"]["retrieval"]["parameters"]
        self.assertEqual((parameters["contract"], parameters["mode"], parameters["max_evidence"], parameters["dropped_rows"]),
                         ("retrieve-evidence-rows-v1", "HYBRID", 6, {"not_a_passage": 0, "too_short": 0}))
        self.assertEqual(package["context_evidence"][1]["metadata"]["rank"], 2)
        self.assertEqual(package["context_evidence"][0]["trust_class"], "untrusted_external_evidence")

    def test_the_connected_contract_takes_exactly_one_corpus(self) -> None:
        for scope in (None, [], ["cinema", "mythos"]):
            with self.assertRaises(polymath.PolymathMCPError) as caught:
                self.retrieve(live_result([row(1)]), corpus_ids=scope)
            self.assertEqual(caught.exception.code, "corpus_scope_invalid")

    def test_rows_that_are_not_passages_or_too_short_are_counted_not_used(self) -> None:
        rows = [row(1), row(2, text="1. Punching Square in the Face"), row(3, kind="graph_fact"), row(4)]
        package, _ = self.retrieve(live_result(rows))
        self.assertEqual([p["title"] for p in package["retrieved_passages"]["passages"]], ["Book 1.md", "Book 4.md"])
        self.assertEqual(package["retrieved_passages"]["retrieval"]["parameters"]["dropped_rows"], {"not_a_passage": 1, "too_short": 1})
        with self.assertRaises(polymath.PolymathMCPError) as caught:
            self.retrieve(live_result([row(2, text="1. Punching Square in the Face")]))
        self.assertEqual(caught.exception.code, "retrieval_empty")

    def test_rows_outside_the_requested_corpus_fail_closed(self) -> None:
        with self.assertRaises(polymath.PolymathMCPError) as caught:
            self.retrieve(live_result([row(1, corpus_id="mythos")]))
        self.assertEqual(caught.exception.code, "retrieval_scope_violation")

    def test_a_legacy_tool_schema_keeps_the_legacy_request(self) -> None:
        legacy = {"chunks": [{"corpus_id": "cinema", "doc_id": "doc_1", "chunk_id": "chunk_1", "text": row(1)["text"]}]}
        package, calls = self.retrieve(legacy, schema=LEGACY_SCHEMA, mode="HYBRID", top_k=6)
        self.assertEqual(calls[0][1], {"query": "Film directing guidance for this scene: a shove", "corpus_ids": ["cinema"],
                                       "retrieval_tier": "qdrant_mongo", "final_top_k": 6, "rerank_enabled": True,
                                       "search_mode": "local"})
        self.assertNotIn("contract", package["retrieved_passages"]["retrieval"]["parameters"])


if __name__ == "__main__":
    unittest.main()
