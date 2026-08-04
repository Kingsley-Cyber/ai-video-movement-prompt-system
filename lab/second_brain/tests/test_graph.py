from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import networkx as nx

from lab.second_brain.src.graph import build_live_graph
from lab.second_brain.tests.helpers import concept, make_root, write_rows


class GraphTests(unittest.TestCase):
    def test_multidigraph_accepts_unknown_layer_and_marks_curated_edges(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [
                    concept("c_alpha", "alpha", "future_cinematography_layer"),
                    concept("c_beta", "beta"),
                ],
            )
            write_rows(
                root / "lab/second_brain/curated/edges.jsonl",
                [
                    {
                        "id": "edge_000001",
                        "u": "c_alpha",
                        "v": "c_beta",
                        "type": "pairs_with",
                        "context": "all",
                        "authored_by": "test",
                        "note": None,
                        "sources": [],
                    }
                ],
            )
            graph = build_live_graph(root)
            self.assertIsInstance(graph, nx.MultiDiGraph)
            self.assertEqual(graph.nodes["c_alpha"]["layer"], "future_cinematography_layer")
            edge = graph.edges["c_alpha", "c_beta", "edge_000001"]
            self.assertEqual(edge["tier"], "curated")
            self.assertFalse(edge["rebuildable"])


if __name__ == "__main__":
    unittest.main()
