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
        pages: list[dict] | None = None,
        item_asset_id: str = "asset_fixture",
    ) -> None:
        self.assets = FakeAssets()
        self.knowledge_store_items = FakeKnowledgeStoreItems(item_asset_id)
        self.knowledge_stores = FakeKnowledgeStores(pages)
        self.responses = FakeResponses(response or {})
        embeddings = FakeEmbeddings()
        self.embed = SimpleNamespace(v_2=embeddings)
        self.embedding_calls = embeddings.calls


def semantic_response() -> dict:
    semantic = {
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


def analysis_job() -> dict:
    return {
        "job_id": "tl_job_fixture_001",
        "knowledge_store_id": "ks_fixture",
        "item_id": "ksi_fixture",
        "source_video": {
            "asset_ref": "asset_fixture",
            "sha256": "a" * 64,
            "rights_scope": "original",
        },
        "interval": {"source_start_s": 0.0, "source_end_s": 4.0},
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
    def test_structured_response_is_traced_and_ingested_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(
                Path(directory),
                [concept("c_communication_graph", "communication graph")],
            )
            client = FakeClient(response=semantic_response())
            result = pegasus.extract_with_twelvelabs(
                analysis_job(), root, client=client
            )
            observation = result["observation"]
            self.assertEqual(observation["extractor"]["provider"], "twelvelabs")
            self.assertEqual(observation["candidate_concepts"], ["c_communication_graph"])
            self.assertIsNone(result["distillation_run"])
            self.assertEqual(
                len(
                    read_jsonl(
                        root
                        / "lab/second_brain/immutable/pegasus_observations.jsonl"
                    )
                ),
                1,
            )
            response_path = Path(result["artifacts"]["response"])
            digest = "sha256:" + hashlib.sha256(response_path.read_bytes()).hexdigest()
            self.assertEqual(observation["raw_response_hash"], digest)
            response_call = client.responses.calls[0]
            self.assertEqual(
                response_call["selections"],
                [{"kind": "item", "id": "ksi_fixture"}],
            )
            self.assertEqual(
                response_call["text"]["format"]["type"], "json_schema"
            )
            retry = pegasus.extract_with_twelvelabs(
                analysis_job(), root, client=client
            )
            self.assertEqual(
                retry["observation"]["record_hash"], observation["record_hash"]
            )
            self.assertEqual(
                len(
                    read_jsonl(
                        root
                        / "lab/second_brain/immutable/pegasus_observations.jsonl"
                    )
                ),
                1,
            )

    def test_provider_failures_do_not_append_immutable_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory))
            wrong_asset = FakeClient(
                response=semantic_response(), item_asset_id="asset_wrong"
            )
            with self.assertRaises(ValidationFailure):
                pegasus.extract_with_twelvelabs(
                    analysis_job(), root, client=wrong_asset
                )
            self.assertEqual(
                read_jsonl(
                    root / "lab/second_brain/immutable/pegasus_observations.jsonl"
                ),
                [],
            )
            incomplete = semantic_response()
            incomplete["status"] = "incomplete"
            with self.assertRaises(ValidationFailure):
                pegasus.extract_with_twelvelabs(
                    analysis_job(), root, client=FakeClient(response=incomplete)
                )
            self.assertEqual(
                read_jsonl(
                    root / "lab/second_brain/immutable/pegasus_observations.jsonl"
                ),
                [],
            )
            response_artifact = (
                root
                / "work/twelvelabs/tl_job_fixture_001/response.sdk.json"
            )
            self.assertTrue(response_artifact.is_file())


if __name__ == "__main__":
    unittest.main()
