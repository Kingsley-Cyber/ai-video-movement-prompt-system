from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from lab.second_brain.src import pegasus
from lab.second_brain.src.providers import twelvelabs
from lab.second_brain.src.validate import ValidationFailure, read_jsonl
from lab.second_brain.tests.helpers import concept, make_root


class FakeAssets:
    def __init__(self) -> None:
        self.create_calls: list[dict] = []

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        return SimpleNamespace(id="asset_fixture", status="processing")

    def retrieve(self, asset_id, **kwargs):
        return SimpleNamespace(id=asset_id, status="ready")


class FakeKnowledgeStoreItems:
    def __init__(self, asset_id: str = "asset_fixture") -> None:
        self.asset_id = asset_id
        self.create_calls: list[tuple[str, dict]] = []

    def create(self, knowledge_store_id, **kwargs):
        self.create_calls.append((knowledge_store_id, kwargs))
        return SimpleNamespace(
            id="ksi_fixture", asset_id=kwargs["asset_id"], status="processing"
        )

    def retrieve(self, knowledge_store_id, item_id, **kwargs):
        return SimpleNamespace(
            id=item_id, asset_id=self.asset_id, status="ready"
        )


class FakeKnowledgeStores:
    def __init__(self, pages: list[dict] | None = None) -> None:
        self.pages = list(pages or [])
        self.search_calls: list[tuple[str, dict]] = []
        self.create_calls: list[dict] = []

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        return SimpleNamespace(id="ks_fixture", name=kwargs["name"])

    def search(self, knowledge_store_id, **kwargs):
        self.search_calls.append((knowledge_store_id, kwargs))
        return self.pages.pop(0)


class FakeResponses:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeAnalyzeTasks:
    def __init__(self, segment_data: dict) -> None:
        self.segment_data = segment_data
        self.create_calls: list[dict] = []

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        return {"task_id": "task_fixture", "status": "queued"}

    def retrieve(self, task_id, **kwargs):
        return {
            "task_id": task_id,
            "status": "ready",
            "result": {
                "generation_id": "generation_fixture",
                "finish_reason": "stop",
                "data": json.dumps(self.segment_data),
            },
        }


class FakeAnalyzeBatches:
    def __init__(self, semantic: dict) -> None:
        self.semantic = semantic
        self.create_calls: list[dict] = []

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        return {"batch_id": "batch_fixture", "status": "pending"}

    def retrieve(self, batch_id, **kwargs):
        return {"batch_id": batch_id, "status": "completed", "ready_items": 1}

    def results(self, batch_id, **kwargs):
        yield {
            "task_id": "task_batch_fixture",
            "custom_id": "source_1",
            "status": "ready",
            "data": {
                "finish_reason": "stop",
                "data": json.dumps(self.semantic),
            },
        }


class FakeEmbeddings:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}


class FakeClient:
    def __init__(
        self,
        *,
        response: dict | None = None,
        analyze_response: dict | None = None,
        pages: list[dict] | None = None,
        item_asset_id: str = "asset_fixture",
    ) -> None:
        self.assets = FakeAssets()
        self.knowledge_store_items = FakeKnowledgeStoreItems(item_asset_id)
        self.knowledge_stores = FakeKnowledgeStores(pages)
        self.responses = FakeResponses(response or {})
        self.analyze_response = analyze_response or {
            "finish_reason": "stop",
            "data": json.dumps(semantic_payload()),
        }
        self.analyze_calls: list[dict] = []
        tasks = FakeAnalyzeTasks(
            {
                "shots": [
                    {
                        "start_time": 0.0,
                        "end_time": 4.0,
                        "metadata": {
                            "shot_scale": "medium",
                            "camera_movement": "handheld",
                        },
                    }
                ]
            }
        )
        batches = FakeAnalyzeBatches(semantic_payload())
        self.analyze_async = SimpleNamespace(tasks=tasks, batches=batches)
        self.task_create_calls = tasks.create_calls
        self.batch_create_calls = batches.create_calls
        embeddings = FakeEmbeddings()
        self.embed = SimpleNamespace(v_2=embeddings)
        self.embedding_calls = embeddings.calls

    def analyze(self, **kwargs):
        self.analyze_calls.append(kwargs)
        return self.analyze_response


def semantic_payload() -> dict:
    return {
        "entities": [
            {
                "label": "product",
                "description": "A product is visible.",
                "start_s": 1.0,
                "end_s": 2.0,
                "evidence_class": "interpreted",
                "confidence": 0.9,
            }
        ],
        "beats": [],
        "actions": [],
        "camera": [],
        "performance": [],
        "face_affect": [],
        "audio": [],
        "marketing_functions": [],
        "confidence": 0.85,
    }


def semantic_response() -> dict:
    semantic = semantic_payload()
    return {
        "id": "resp_fixture",
        "type": "response",
        "status": "completed",
        "session_id": "sess_fixture",
        "knowledge_store_id": "ks_fixture",
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": json.dumps(semantic)}
                ],
            }
        ],
    }


def corpus_response() -> dict:
    structured = {
        "schema": "cpcs.twelvelabs_corpus_response/1.0",
        "summary": "The selected item contains a product reveal.",
        "observations": [
            {
                "item_id": "ksi_fixture",
                "interval": {"start_s": 1.0, "end_s": 2.0},
                "layer": "marketing",
                "claim": {"label": "product_reveal"},
                "evidence_class": "interpreted",
                "confidence": 0.85,
                "alternatives": [],
            }
        ],
        "confidence": 0.85,
    }
    return {
        "id": "resp_corpus_fixture",
        "type": "response",
        "status": "completed",
        "session_id": "sess_fixture",
        "knowledge_store_id": "ks_fixture",
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": json.dumps(structured)}
                ],
            }
        ],
    }


def analysis_job() -> dict:
    return {
        "schema": "cpcs.twelvelabs_analyze_job/1.0",
        "job_id": "tl_analyze_fixture_001",
        "source_video": {
            "asset_ref": "asset_fixture",
            "sha256": "a" * 64,
            "rights_scope": "original",
        },
        "analysis_scope": "exact_video",
        "media_bounds": {"source_start_s": 0.0, "source_end_s": 4.0},
        "interval": {"source_start_s": 0.0, "source_end_s": 4.0},
        "profile_id": "pegasus.source_map/1.0",
        "prompt": "Identify the visual entities and story beats.",
        "candidate_concepts": ["c_communication_graph"],
        "created_at": "2026-07-30T00:00:00Z",
    }


class TwelveLabsTransportTests(unittest.TestCase):
    def test_doctor_never_returns_secret_values(self) -> None:
        report = twelvelabs.doctor(
            {
                twelvelabs.API_KEY_ENV: "secret-value",
                twelvelabs.STORE_ID_ENV: "ks_fixture",
            },
            sdk_version=twelvelabs.SDK_VERSION,
        )
        self.assertTrue(report["ready_for_analysis"])
        self.assertNotIn("secret-value", json.dumps(report))
        self.assertEqual(
            twelvelabs.to_plain(
                datetime(2026, 7, 30, tzinfo=timezone.utc)
            ),
            "2026-07-30T00:00:00Z",
        )

    def test_setup_search_and_embedding_contracts(self) -> None:
        pages = [
            {"data": [{"item_id": "ksi_1"}], "next_page_token": "next"},
            {"data": [{"item_id": "ksi_2"}], "next_page_token": None},
        ]
        client = FakeClient(pages=pages)
        store = twelvelabs.create_knowledge_store(
            "fixture store", client=client
        )
        indexed = twelvelabs.add_media(
            store["id"],
            media_type="video",
            url="https://example.test/video.mp4",
            client=client,
        )
        self.assertEqual(indexed["item"]["status"], "ready")
        search = twelvelabs.search_all(
            store["id"],
            "product reveal",
            filter_={"metadata.category": "ad"},
            client=client,
        )
        self.assertEqual([row["item_id"] for row in search["data"]], ["ksi_1", "ksi_2"])
        first = client.knowledge_stores.search_calls[0][1]
        second = client.knowledge_stores.search_calls[1][1]
        self.assertNotIn("page_token", first)
        self.assertEqual(second["page_token"], "next")
        for key in (
            "query",
            "filter",
            "search_options",
            "group_by",
            "page_size",
            "include_metadata",
        ):
            self.assertEqual(first[key], second[key])
        embedded = twelvelabs.create_embedding(
            "multi_input",
            text="compare these products",
            image_asset_ids=["asset_1", "asset_2"],
            client=client,
        )
        self.assertEqual(len(embedded["data"][0]["embedding"]), 3)
        call = client.embedding_calls[0]
        self.assertEqual(call["model_name"], "marengo3.0")
        self.assertEqual(call["input_type"], "multi_input")
        self.assertEqual(
            [item["asset_id"] for item in call["multi_input"]["media_sources"]],
            ["asset_1", "asset_2"],
        )

    def test_bounded_polling_handles_ready_failed_and_timeout(self) -> None:
        statuses = iter(
            [
                SimpleNamespace(id="asset_1", status="processing"),
                SimpleNamespace(id="asset_1", status="ready"),
            ]
        )
        clock = [0.0]

        def sleep(seconds: float) -> None:
            clock[0] += seconds

        ready = twelvelabs.wait_until_ready(
            lambda: next(statuses),
            resource_name="asset",
            timeout_s=5,
            poll_interval_s=1,
            sleep=sleep,
            monotonic=lambda: clock[0],
        )
        self.assertEqual(ready.status, "ready")
        with self.assertRaises(twelvelabs.TwelveLabsProviderError):
            twelvelabs.wait_until_ready(
                lambda: SimpleNamespace(id="asset_2", status="failed"),
                resource_name="asset",
                timeout_s=5,
                poll_interval_s=1,
                sleep=sleep,
                monotonic=lambda: clock[0],
            )
        timeout_clock = [0.0]

        def timeout_sleep(seconds: float) -> None:
            timeout_clock[0] += seconds

        with self.assertRaises(twelvelabs.TwelveLabsProviderError):
            twelvelabs.wait_until_ready(
                lambda: SimpleNamespace(id="asset_3", status="processing"),
                resource_name="asset",
                timeout_s=2,
                poll_interval_s=1,
                sleep=timeout_sleep,
                monotonic=lambda: timeout_clock[0],
            )


class TwelveLabsExtractionTests(unittest.TestCase):
    def test_exact_analyze_and_clipped_analyze_are_isolated_and_replayable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory))
            client = FakeClient()
            result = pegasus.execute_analyze_job(
                analysis_job(), root, client=client, source_id="source_fixture"
            )
            self.assertEqual(result["observations"][0]["source_id"], "source_fixture")
            self.assertEqual(client.analyze_calls[0]["video"]["asset_id"], "asset_fixture")
            self.assertNotIn("start_time", client.analyze_calls[0])
            self.assertNotIn("knowledge_store_id", client.analyze_calls[0])
            replay = pegasus.renormalize_analyze_artifacts(
                analysis_job(),
                root / "work/twelvelabs/tl_analyze_fixture_001",
                root,
                source_id="source_fixture",
            )
            self.assertEqual(
                json.dumps(replay, sort_keys=True),
                json.dumps(result["observations"], sort_keys=True),
            )
            clipped = analysis_job()
            clipped["job_id"] = "tl_analyze_fixture_002"
            clipped["analysis_scope"] = "clipped_interval"
            pegasus.execute_analyze_job(clipped, root, client=client)
            self.assertEqual(client.analyze_calls[1]["start_time"], 0.0)
            self.assertEqual(client.analyze_calls[1]["end_time"], 4.0)
            self.assertEqual(
                read_jsonl(root / "lab/second_brain/immutable/pegasus_observations.jsonl"),
                [],
            )

    def test_exact_analyze_rejects_partial_media_authority_before_provider_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory))
            client = FakeClient()
            job = analysis_job()
            job["media_bounds"] = {"source_start_s": 0.0, "source_end_s": 8.0}
            with self.assertRaisesRegex(ValidationFailure, "complete media bounds"):
                pegasus.execute_analyze_job(job, root, client=client)
            self.assertEqual(client.analyze_calls, [])
            self.assertFalse(
                (root / "work/twelvelabs/tl_analyze_fixture_001").exists()
            )

    def test_segment_batch_search_jockey_and_marengo_use_distinct_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory))
            client = FakeClient(
                response=corpus_response(),
                pages=[{"data": [{"item_id": "ksi_fixture"}], "next_page_token": None}],
            )
            source = analysis_job()["source_video"]
            segment = pegasus.execute_segment_job(
                {
                    "schema": "cpcs.twelvelabs_segment_job/1.0",
                    "job_id": "tl_segment_fixture_001",
                    "source_video": source,
                    "media_bounds": {"source_start_s": 0.0, "source_end_s": 4.0},
                    "interval": {"source_start_s": 0.0, "source_end_s": 4.0},
                    "profile_id": "pegasus.shot_scene/1.0",
                    "min_segment_duration": 2.0,
                    "max_segment_duration": None,
                    "created_at": "2026-07-30T00:00:00Z",
                },
                root,
                client=client,
            )
            self.assertEqual(segment["observations"][0]["layer"], "segment")
            batch = pegasus.execute_batch_job(
                {
                    "schema": "cpcs.twelvelabs_batch_job/1.0",
                    "job_id": "tl_batch_fixture_001",
                    "analysis_mode": "general",
                    "profile_id": "pegasus.source_map/1.0",
                    "items": [
                        {
                            "custom_id": "source_1",
                            "asset_ref": "asset_fixture",
                            "sha256": "a" * 64,
                            "rights_scope": "original",
                            "interval": {"source_start_s": 0.0, "source_end_s": 4.0},
                        }
                    ],
                    "created_at": "2026-07-30T00:00:00Z",
                },
                root,
                client=client,
            )
            self.assertEqual(batch["observations"][0]["provenance"]["surface"], "pegasus_batch")
            search = pegasus.execute_search_job(
                {
                    "schema": "cpcs.twelvelabs_search_job/1.0",
                    "job_id": "tl_search_fixture_001",
                    "knowledge_store_id": "ks_fixture",
                    "query": "product reveal",
                    "modalities": ["visual"],
                    "authorized_item_ids": ["ksi_fixture"],
                    "created_at": "2026-07-30T00:00:00Z",
                },
                root,
                client=client,
            )
            self.assertEqual(search["hits"][0]["item_id"], "ksi_fixture")
            self.assertEqual(
                client.knowledge_stores.search_calls[-1][1]["filter"],
                {"item_id": {"in_": ["ksi_fixture"]}},
            )
            jockey = pegasus.execute_jockey_job(
                {
                    "schema": "cpcs.twelvelabs_jockey_job/1.0",
                    "job_id": "tl_jockey_fixture_001",
                    "knowledge_store_id": "ks_fixture",
                    "selections": [{"kind": "item", "id": "ksi_fixture"}],
                    "profile_id": "jockey.corpus_pattern_analysis/1.0",
                    "prompt": "Compare structure.",
                    "instructions": None,
                    "created_at": "2026-07-30T00:00:00Z",
                },
                root,
                client=client,
            )
            self.assertEqual(
                jockey["corpus_observations"]["observations"][0]["item_id"],
                "ksi_fixture",
            )
            wrong_citation = corpus_response()
            structured = json.loads(
                wrong_citation["output"][0]["content"][0]["text"]
            )
            structured["observations"][0]["item_id"] = "ksi_unselected"
            wrong_citation["output"][0]["content"][0]["text"] = json.dumps(
                structured
            )
            unsafe_job = {
                "schema": "cpcs.twelvelabs_jockey_job/1.0",
                "job_id": "tl_jockey_fixture_unsafe",
                "knowledge_store_id": "ks_fixture",
                "selections": [{"kind": "item", "id": "ksi_fixture"}],
                "profile_id": "jockey.corpus_pattern_analysis/1.0",
                "prompt": "Compare structure.",
                "instructions": None,
                "created_at": "2026-07-30T00:00:00Z",
            }
            with self.assertRaises(ValidationFailure):
                pegasus.execute_jockey_job(
                    unsafe_job,
                    root,
                    client=FakeClient(response=wrong_citation),
                )
            embedding = pegasus.execute_marengo_job(
                {
                    "schema": "cpcs.twelvelabs_marengo_job/1.0",
                    "job_id": "tl_marengo_fixture_001",
                    "input_type": "text",
                    "text": "product reveal",
                    "asset_id": None,
                    "image_asset_ids": [],
                    "created_at": "2026-07-30T00:00:00Z",
                },
                root,
                client=client,
            )
            self.assertEqual(len(embedding["embedding_response"]["data"][0]["embedding"]), 3)

    def test_invalid_provider_output_saves_request_but_not_immutable_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory))
            semantic = semantic_payload()
            semantic["entities"][0]["end_s"] = 5.0
            client = FakeClient(
                analyze_response={"finish_reason": "stop", "data": json.dumps(semantic)}
            )
            with self.assertRaises(ValidationFailure):
                pegasus.execute_analyze_job(analysis_job(), root, client=client)
            self.assertTrue(
                (root / "work/twelvelabs/tl_analyze_fixture_001/request.json").is_file()
            )
            self.assertTrue(
                (root / "work/twelvelabs/tl_analyze_fixture_001/response.sdk.json").is_file()
            )
            self.assertEqual(
                read_jsonl(root / "lab/second_brain/immutable/pegasus_observations.jsonl"),
                [],
            )


if __name__ == "__main__":
    unittest.main()
