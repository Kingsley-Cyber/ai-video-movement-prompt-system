from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lab.application import service
from lab.application.service import REQUEST_SCHEMA, invoke
from lab.second_brain.src.validate import REPO_ROOT, sha256_value
from lab.second_brain.src.video_reasoning import build_knowledge_comparison_lens
from lab.second_brain.tests.test_video_reasoning import _vog


def _request(operation: str, arguments: dict) -> dict:
    return {
        "schema": REQUEST_SCHEMA,
        "operation": operation,
        "arguments": arguments,
    }


def _authority_bytes() -> dict[Path, bytes]:
    second_brain = REPO_ROOT / "lab" / "second_brain"
    paths = [
        REPO_ROOT / "lab" / "concepts.jsonl",
        *sorted((second_brain / "curated").glob("*")),
        *sorted((second_brain / "immutable").glob("*")),
        *sorted((second_brain / "staging").glob("*")),
        *sorted((second_brain / "derived").glob("*")),
    ]
    return {path: path.read_bytes() for path in paths if path.is_file()}


class KnowledgeConditionedVideoStrategyTests(unittest.TestCase):
    def test_lens_changes_score_and_prompt_with_closed_lineage(self) -> None:
        lens = build_knowledge_comparison_lens(
            _vog(REPO_ROOT, "strategy_reference"),
            _vog(REPO_ROOT, "strategy_candidate"),
            query=(
                "genuine smile cheeks raise with mouth AU06 AU12 "
                "facial expression control"
            ),
            domain=None,
        )
        text = "Create a restrained scene where she realizes he is lying"
        asset = {
            "asset_id": "asset_character_reference",
            "role": "character_references",
            "content_hash": "sha256:" + hashlib.sha256(b"character").hexdigest(),
            "rights_basis": "owner_authorized_test_fixture",
        }
        common = {
            "text": text,
            "project_id": "lens-strategy-test",
            "assets": [asset],
        }
        before = _authority_bytes()
        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "lab.application.service._application_work_root",
            return_value=Path(directory),
        ):
            direct = invoke(_request("cpcs.production.prepare", common))
            conditioned_arguments = {**common, "knowledge_lens": lens}
            conditioned = invoke(
                _request("cpcs.production.prepare", conditioned_arguments)
            )
            replay = invoke(
                _request("cpcs.production.prepare", conditioned_arguments)
            )
            self.assertEqual(direct["status"], "success", direct)
            self.assertEqual(conditioned["status"], "success", conditioned)
            self.assertEqual(replay["status"], "success", replay)

            direct_result = direct["result"]
            result = conditioned["result"]
            self.assertNotEqual(
                direct_result["score"]["score_id"], result["score"]["score_id"]
            )
            self.assertNotIn(
                "mapping_000001",
                {
                    row["mapping_id"]
                    for row in direct_result["score"]["research_translation"]["applied"]
                },
            )
            self.assertIn(
                "mapping_000001",
                {
                    row["mapping_id"]
                    for row in result["score"]["research_translation"]["applied"]
                },
            )
            self.assertEqual(
                result["score"]["performance"]["facs_action_units"],
                ["AU06", "AU12"],
            )
            trace = result["directing_strategy"]["knowledge_lens"]
            self.assertEqual(trace["lens_hash"], lens["lens_hash"])
            self.assertIn("c_duchenne", trace["concept_ids"])
            self.assertIn("mapping_000001", trace["mapping_ids"])
            self.assertTrue(trace["knowledge_object_ids"])
            self.assertTrue(trace["source_refs"])
            prompt = (
                Path(result["build"]["output_dir"]) / "prompt.txt"
            ).read_text(encoding="utf-8")
            self.assertIn(
                'performance.facs_action_units = ["AU06","AU12"]', prompt
            )
            self.assertEqual(
                result["score"]["score_id"], replay["result"]["score"]["score_id"]
            )
            self.assertEqual(
                result["build"]["build_hash"],
                replay["result"]["build"]["build_hash"],
            )

            normalized_intent = result["normalized_intent"]
            direct_score_request = {
                "schema": "cpcs.score_request/1.0",
                "normalized_intent": copy.deepcopy(normalized_intent),
                "context_bundle": copy.deepcopy(result["context_bundle"]),
                "directing_strategy": copy.deepcopy(result["directing_strategy"]),
                "knowledge_lens": copy.deepcopy(lens),
                "profile_selection": [
                    normalized_intent["profiles"]["primary"],
                    *normalized_intent["profiles"]["secondary"],
                ],
                "overlays": [],
                "conflict_resolutions": {},
                "assets": [copy.deepcopy(asset)],
            }
            direct_score = invoke(
                _request("cpcs.score.build", {"score_request": direct_score_request})
            )
            self.assertEqual(direct_score["status"], "success", direct_score)
            self.assertEqual(
                direct_score["result"]["score"]["score_id"],
                result["score"]["score_id"],
            )

            stripped_score_request = copy.deepcopy(direct_score_request)
            stripped_score_request.pop("knowledge_lens")
            stripped_score = invoke(
                _request(
                    "cpcs.score.build",
                    {"score_request": stripped_score_request},
                )
            )
            self.assertEqual(stripped_score["status"], "error")
            self.assertIn(
                "requires the exact knowledge lens",
                stripped_score["error"]["message"],
            )

            tampered = copy.deepcopy(lens)
            tampered["query"] += " altered"
            rejected = invoke(
                _request(
                    "cpcs.strategy.compile",
                    {"text": text, "knowledge_lens": tampered},
                )
            )
            self.assertEqual(rejected["status"], "error")
            self.assertIn("lens hash is invalid", rejected["error"]["message"])

            stale = copy.deepcopy(lens)
            stale["concepts"][0]["name"] += " stale"
            stale["context_bundle"]["selected_concepts"][0]["name"] += " stale"
            stale["context_bundle_hash"] = sha256_value(stale["context_bundle"])
            stale["authority_snapshot_hash"] = sha256_value(
                {
                    "context_bundle_hash": stale["context_bundle_hash"],
                    "policy_versions": stale["context_bundle"]["policy_versions"],
                }
            )
            stale["lens_hash"] = sha256_value(
                {key: value for key, value in stale.items() if key != "lens_hash"}
            )
            stale_rejected = invoke(
                _request(
                    "cpcs.strategy.compile",
                    {"text": text, "knowledge_lens": stale},
                )
            )
            self.assertEqual(stale_rejected["status"], "error")
            self.assertIn("snapshot is stale", stale_rejected["error"]["message"])

        self.assertEqual(before, _authority_bytes())


if __name__ == "__main__":
    unittest.main()
