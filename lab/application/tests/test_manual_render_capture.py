from __future__ import annotations

import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from lab.application.service import REQUEST_SCHEMA, authorization_request_hash, invoke
from lab.compiler.provenance import sha256_bytes
from lab.second_brain.src.graph import build_live_graph
from lab.second_brain.src.reflect import project_run_edges
from lab.second_brain.src.validate import REPO_ROOT, read_jsonl, validate_immutable
from lab.second_brain.tests.helpers import make_root


class ManualRenderCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = make_root(self.base)
        shutil.copytree(REPO_ROOT / "lab/application/schemas", self.root / "lab/application/schemas")
        shutil.copytree(REPO_ROOT / "lab/release", self.root / "lab/release")
        self.media = self.base / "metadata-fixture.mp4"
        # Local synthetic file fixture for ffprobe, never a provider render.
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                        "color=size=16x16:rate=24", "-frames:v", "2",
                        "-c:v", "mpeg4", str(self.media)], check=True)
        self.prompt = self.base / "prompt.txt"
        self.prompt.write_bytes(b"A bottle opens.\n")
        self.receipt = {
            "capture_kind": "manual_render",
            "media": self.identity(self.media),
            "prompt_source": self.identity(self.prompt),
            "feedback": [
                {"speaker": "owner", "representation": "verbatim", "text": "CHAMPION"},
                {"speaker": "owner", "representation": "paraphrase", "text": "The kick struggled."},
                {"speaker": "Claude", "representation": "paraphrase", "text": "The knee stayed bent."},
            ],
        }

    @staticmethod
    def identity(path):
        data = path.read_bytes()
        return {"path": str(path), "sha256": sha256_bytes(data), "size_bytes": len(data)}

    def capture(self, receipt=None, authorize=True):
        args = {"receipt": receipt or self.receipt}
        request = {"schema": REQUEST_SCHEMA, "operation": "cpcs.record.render", "arguments": args}
        if authorize:
            request["authorization"] = {
                "schema": "cpcs.explicit_authorization/1.0", "authorization_id": "auth_manual",
                "authorized_by": "owner-test", "operation": "cpcs.record.render",
                "request_hash": authorization_request_hash("cpcs.record.render", args),
                "reason": "Record this exact local manual evidence only.",
            }
        return invoke(request, role="curator", root=self.root)

    def test_public_capture_preserves_unknowns_exact_source_and_attribution(self):
        response = self.capture()
        self.assertEqual(response["status"], "success", response)
        row = response["result"]
        self.assertEqual(row["media"], self.receipt["media"])
        self.assertEqual(row["prompt_source"]["sha256"], self.identity(self.prompt)["sha256"])
        self.assertEqual(row["prompt_source"]["text_utf8"], "A bottle opens.\n")
        self.assertEqual(row["prompt_source"]["binding"], "owner_attributed")
        self.assertEqual(row["feedback"], self.receipt["feedback"])
        self.assertEqual(row["submission"], dict.fromkeys([
            "route", "model", "seed", "settings", "submitted_at", "exact_submitted_text", "frame_rate"]))
        self.assertEqual(row["container"]["frame_rate"], "24/1")
        self.assertEqual(row["container"]["resolution"], [16, 16])
        self.assertEqual(row["container"]["codec"], "mpeg4")
        self.assertEqual(row["frame_rate_check"]["status"], "unobservable")
        self.assertEqual(row["causal_eligibility"], "ineligible_manual")
        self.assertNotIn("flight_id", row)
        self.assertNotIn("metrics", row)
        self.assertEqual(read_jsonl(self.root / "lab/second_brain/immutable/flights.jsonl"), [])
        self.assertEqual(list(self.root.rglob("*.mp4")), [])
        validate_immutable(self.root)

    def test_exact_replay_appends_once_and_never_learns(self):
        first = self.capture()
        self.assertEqual(first["status"], "success", first)
        second = self.capture()
        self.assertEqual(second, first)
        rows = read_jsonl(self.root / "lab/second_brain/immutable/runs.jsonl")
        self.assertEqual(len(rows), 1)
        self.assertEqual(project_run_edges(rows, self.root), [])
        graph = build_live_graph(self.root, include_derived=False)
        self.assertIn(rows[0]["id"], graph)
        self.assertEqual(list(graph.out_edges(rows[0]["id"])), [])

    def test_changed_media_bytes_reject_before_append(self):
        self.media.write_bytes(self.media.read_bytes() + b"changed")
        self.assertEqual(self.capture()["status"], "error")
        self.assertEqual(read_jsonl(self.root / "lab/second_brain/immutable/runs.jsonl"), [])

    def test_changed_prompt_bytes_reject_before_append(self):
        self.prompt.write_text("Different prompt.")
        self.assertEqual(self.capture()["status"], "error")
        self.assertEqual(read_jsonl(self.root / "lab/second_brain/immutable/runs.jsonl"), [])

    def test_manual_capture_cannot_invent_settings_or_scores(self):
        for key, value in (("seed", 4), ("metrics", {"quality": 5}), ("model", "guess")):
            with self.subTest(key=key):
                receipt = copy.deepcopy(self.receipt)
                receipt[key] = value
                self.assertEqual(self.capture(receipt)["status"], "error")

    def test_exact_authorization_is_required(self):
        self.assertEqual(self.capture(authorize=False)["status"], "error")


    def test_legacy_graph_rebuild_keeps_manual_node_without_flight(self):
        from lab.scripts.build_graph import build
        response = self.capture()
        self.assertEqual(response["status"], "success", response)
        (self.root / "lab/blocks.yaml").write_text("{}\n")
        (self.root / "lab/registry.yaml").write_text("{}\n")
        (self.root / "lab/runs").mkdir()
        (self.root / "lab/runs/results.csv").write_text("run_id,variant_id\n")
        graph = build(self.root)
        node_id = "run:" + response["result"]["id"]
        self.assertIn(node_id, {node["id"] for node in graph["nodes"]})
        self.assertEqual([edge for edge in graph["edges"] if edge["s"] == node_id], [])
