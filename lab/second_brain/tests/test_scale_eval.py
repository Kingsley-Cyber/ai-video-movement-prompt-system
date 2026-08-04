from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

import yaml

from lab.second_brain.src.graph import build_live_graph, graph_stats
from lab.second_brain.src.indexes import build_index_catalog
from lab.second_brain.src.scale_eval import (
    DEFAULT_BENCHMARK,
    _load_benchmark,
    _prepare_fixture,
)
from lab.second_brain.src.validate import REPO_ROOT, ValidationFailure, read_jsonl


class ScaleBenchmarkTests(unittest.TestCase):
    def test_fixture_uses_unique_concepts_and_typed_reachability(self) -> None:
        work = REPO_ROOT / "work" / "scale"
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as temporary:
            root = Path(temporary) / "repo"
            fixture = _prepare_fixture(root, 2)
            source_concepts = read_jsonl(REPO_ROOT / "lab" / "concepts.jsonl")
            fixture_concepts = read_jsonl(root / "lab" / "concepts.jsonl")
            self.assertEqual(len(fixture_concepts), 2 * len(source_concepts))
            self.assertEqual(len({row["id"] for row in fixture_concepts}), len(fixture_concepts))
            self.assertEqual(fixture["counts"]["concepts"], len(fixture_concepts))
            graph = build_live_graph(root)
            catalog = build_index_catalog(root)
            self.assertEqual(
                graph_stats(graph)["nodes_by_tier"]["curated"],
                len(fixture_concepts),
            )
            self.assertEqual(
                catalog["dense_semantic_concepts"]["corpus_size"],
                len(fixture_concepts),
            )
            clone_edges = [
                row
                for row in read_jsonl(
                    root / "lab" / "second_brain" / "curated" / "edges.jsonl"
                )
                if row["context"] == "scale_fixture"
            ]
            self.assertEqual(len(clone_edges), len(source_concepts))
            self.assertEqual({row["type"] for row in clone_edges}, {"refines"})

    def test_configuration_rejects_unknown_and_overlapping_labels(self) -> None:
        source = yaml.safe_load((REPO_ROOT / DEFAULT_BENCHMARK).read_text())
        work = REPO_ROOT / "work" / "scale"
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as temporary:
            path = Path(temporary) / "benchmark.yaml"
            unknown = copy.deepcopy(source)
            unknown["query_cases"][0]["expected_concepts"][0] = "c_missing"
            path.write_text(yaml.safe_dump(unknown, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValidationFailure, "unknown concepts"):
                _load_benchmark(path, REPO_ROOT)

            overlap = copy.deepcopy(source)
            concept_id = overlap["query_cases"][0]["expected_concepts"][0]
            overlap["query_cases"][0]["forbidden_concepts"][0] = concept_id
            path.write_text(yaml.safe_dump(overlap, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValidationFailure, "expects and forbids"):
                _load_benchmark(path, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
