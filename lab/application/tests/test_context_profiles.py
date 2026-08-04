from __future__ import annotations

import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lab.application.context_store import ContextProfileStore
from lab.application.service import (
    REQUEST_SCHEMA,
    authorization_request_hash,
    invoke,
    list_operations,
)
from lab.second_brain.src.intent import build_intent_context
from lab.second_brain.src.validate import REPO_ROOT

from lab.application.tests.test_facade import authority_snapshot


def request(operation: str, arguments: dict) -> dict:
    return {
        "schema": REQUEST_SCHEMA,
        "operation": operation,
        "arguments": arguments,
    }


def profile_arguments(
    context_id: str,
    value: str,
    *,
    project_id: str | None = None,
    kind: str = "user_defaults",
) -> dict:
    return {
        "context_id": context_id,
        "context_kind": kind,
        "project_id": project_id,
        "priority": 20,
        "values": {"camera": {"stabilization": value}},
        "locks": [],
        "valid_from": "2026-08-04T00:00:00Z",
        "valid_until": "2026-09-03T00:00:00Z",
    }


class ContextProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        (REPO_ROOT / "work").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(
            dir=REPO_ROOT / "work", prefix="context-profile-test."
        )
        self.path = Path(self.temporary.name) / "profiles.sqlite3"
        self.store = ContextProfileStore(REPO_ROOT, database_path=self.path)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_store_is_versioned_idempotent_bounded_and_retention_pruned(self) -> None:
        arguments = profile_arguments("context_personal_camera", "handheld_natural")
        first = self.store.put(**arguments)
        replay = self.store.put(**copy.deepcopy(arguments))
        self.assertEqual(first["disposition"], "created")
        self.assertEqual(replay["disposition"], "already_present")
        self.assertEqual(first["profile"], replay["profile"])
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

        revised_arguments = copy.deepcopy(arguments)
        revised_arguments["values"]["camera"]["stabilization"] = "tripod_static"
        revised = self.store.put(**revised_arguments)
        self.assertEqual(revised["disposition"], "updated")
        self.assertEqual(revised["profile"]["revision"], 2)
        self.assertEqual(
            revised["profile"]["previous_profile_hash"],
            first["profile"]["profile_hash"],
        )
        self.assertEqual(
            revised["profile"]["overlay"]["source_refs"],
            ["context-profile://context_personal_camera/2"],
        )
        active = self.store.get(
            "context_personal_camera", as_of="2026-08-05T00:00:00Z"
        )
        self.assertEqual(active, revised["profile"])

        too_long = copy.deepcopy(arguments)
        too_long["context_id"] = "context_retention_excess"
        too_long["valid_until"] = "2026-09-04T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "30-day retention"):
            self.store.put(**too_long)
        listing = self.store.list(as_of="2026-09-03T00:00:00Z")
        self.assertEqual(listing["profiles"], [])
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM context_profiles").fetchone()[0],
                0,
            )
        renewal = copy.deepcopy(revised_arguments)
        renewal["valid_from"] = "2026-09-03T00:00:00Z"
        renewal["valid_until"] = "2026-10-03T00:00:00Z"
        renewed = self.store.put(**renewal)
        self.assertEqual(renewed["profile"]["revision"], 3)
        self.assertEqual(
            renewed["profile"]["previous_profile_hash"],
            revised["profile"]["profile_hash"],
        )

    def test_public_profiles_change_scores_without_changing_knowledge_authority(self) -> None:
        project_a = "project-context-a"
        project_b = "project-context-b"
        put_a = profile_arguments(
            "context_project_camera_a",
            "handheld_context_a",
            project_id=project_a,
            kind="project_profile",
        )
        put_a["values"]["project"] = {
            "platform": "youtube_shorts",
            "aspect_ratio": "9:16",
            "duration_seconds": 6,
            "budget_usd": 25.0,
            "brand_rules": ["Keep the recommendation conversational."],
            "approved_claims": ["Supports skin hydration."],
            "reference_roles": ["product_reference"],
        }
        put_b = profile_arguments(
            "context_project_camera_b",
            "gimbal_context_b",
            project_id=project_b,
            kind="project_profile",
        )
        before = authority_snapshot()
        with mock.patch(
            "lab.application.service._context_store", return_value=self.store
        ):
            first_put = invoke(
                request("cpcs.context.profile.put", put_a), role="operator"
            )
            replay_put = invoke(
                request("cpcs.context.profile.put", copy.deepcopy(put_a)),
                role="operator",
            )
            second_put = invoke(
                request("cpcs.context.profile.put", put_b), role="operator"
            )
            self.assertEqual(first_put["status"], "success")
            self.assertEqual(replay_put["result"]["disposition"], "already_present")
            self.assertEqual(second_put["status"], "success")

            common = {
                "text": "Make a casual phone video recommending this skincare product",
                "context_as_of": "2026-08-05T00:00:00Z",
            }
            score_a = invoke(
                request(
                    "cpcs.score.build",
                    {
                        **common,
                        "context_profile_ids": ["context_project_camera_a"],
                        "context_project_id": project_a,
                    },
                )
            )
            score_b = invoke(
                request(
                    "cpcs.score.build",
                    {
                        **common,
                        "context_profile_ids": ["context_project_camera_b"],
                        "context_project_id": project_b,
                    },
                )
            )
            self.assertEqual(score_a["status"], "success")
            self.assertEqual(score_b["status"], "success")
            self.assertEqual(
                score_a["result"]["score"]["camera"]["stabilization"],
                "handheld_context_a",
            )
            self.assertEqual(
                score_a["result"]["score"]["project"]["platform"],
                "youtube_shorts",
            )
            self.assertEqual(
                score_a["result"]["score"]["project"]["approved_claims"],
                ["Supports skin hydration."],
            )
            self.assertEqual(
                score_b["result"]["score"]["camera"]["stabilization"],
                "gimbal_context_b",
            )
            self.assertNotEqual(
                score_a["result"]["score"]["score_id"],
                score_b["result"]["score"]["score_id"],
            )
            field = score_a["result"]["score"]["provenance"]["fields"][
                "camera.stabilization"
            ]
            self.assertIn(
                "context-profile://context_project_camera_a/1",
                field["source_refs"],
            )
            self.assertEqual(
                score_a["result"]["context_profiles"][0]["profile_hash"],
                first_put["result"]["profile"]["profile_hash"],
            )

            text = common["text"]
            routed = build_intent_context(text)
            assets = [
                {
                    "asset_id": f"asset_context_{index}",
                    "role": role,
                    "content_hash": "sha256:" + "a" * 64,
                    "rights_basis": "owner_authorized_test_fixture",
                }
                for index, role in enumerate(
                    routed["normalized_intent"]["requirements"]["missing_inputs"]
                )
            ]
            prepared = invoke(
                request(
                    "cpcs.production.prepare",
                    {
                        "text": text,
                        "project_id": project_a,
                        "assets": assets,
                        "context_profile_ids": ["context_project_camera_a"],
                        "context_as_of": common["context_as_of"],
                    },
                )
            )
            self.assertEqual(prepared["status"], "success")
            self.assertEqual(
                prepared["result"]["score"]["camera"]["stabilization"],
                "handheld_context_a",
            )
            self.assertEqual(
                prepared["result"]["build_request"]["settings"]["aspect_ratio"],
                "9:16",
            )
            self.assertEqual(
                prepared["result"]["build_request"]["settings"]["duration_seconds"],
                6,
            )
            self.assertRegex(
                prepared["result"]["build"]["build_id"], r"^build_[0-9a-f]{32}$"
            )
            corrected = invoke(
                request(
                    "cpcs.production.prepare",
                    {
                        "text": text,
                        "project_id": project_a,
                        "assets": assets,
                        "context_profile_ids": ["context_project_camera_a"],
                        "context_as_of": common["context_as_of"],
                        "aspect_ratio": "16:9",
                        "duration_seconds": 8,
                    },
                )
            )
            self.assertEqual(corrected["status"], "success")
            self.assertEqual(
                corrected["result"]["score"]["project"]["aspect_ratio"], "16:9"
            )
            self.assertEqual(
                corrected["result"]["build_request"]["settings"]["aspect_ratio"],
                "16:9",
            )

            mismatch = invoke(
                request(
                    "cpcs.score.build",
                    {
                        **common,
                        "context_profile_ids": ["context_project_camera_a"],
                        "context_project_id": project_b,
                    },
                )
            )
            self.assertEqual(mismatch["error"]["code"], "invalid_request")
            self.assertIn("another project", mismatch["error"]["message"])
        self.assertEqual(before, authority_snapshot())

    def test_invalid_fields_tamper_and_symlink_storage_fail_closed(self) -> None:
        invalid = profile_arguments("context_invalid_field", "ignored")
        invalid["values"] = {"provider_request": {"model": "forbidden"}}
        with self.assertRaisesRegex(ValueError, "undeclared canonical field"):
            self.store.put(**invalid)
        invalid_type = profile_arguments("context_invalid_type", "ignored")
        invalid_type["values"] = {"project": {"duration_seconds": "six"}}
        with self.assertRaisesRegex(ValueError, "duration_seconds"):
            self.store.put(**invalid_type)

        created = self.store.put(
            **profile_arguments("context_tamper_target", "handheld_natural")
        )
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "UPDATE context_profiles SET profile_json=profile_json || ? WHERE profile_hash=?",
                (b" ", created["profile"]["profile_hash"]),
            )
        with self.assertRaisesRegex(ValueError, "canonical JSON"):
            self.store.get(
                "context_tamper_target", as_of="2026-08-05T00:00:00Z"
            )

        target = Path(self.temporary.name) / "target.sqlite3"
        target.touch()
        symlink = Path(self.temporary.name) / "redirect.sqlite3"
        symlink.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlink"):
            ContextProfileStore(REPO_ROOT, database_path=symlink)

        future = Path(self.temporary.name) / "future.sqlite3"
        with sqlite3.connect(future) as connection:
            connection.execute("PRAGMA user_version=2")
        with self.assertRaisesRegex(ValueError, "version 2 is unsupported"):
            ContextProfileStore(REPO_ROOT, database_path=future)

    def test_destructive_delete_requires_exact_authorization(self) -> None:
        self.store.put(
            **profile_arguments("context_delete_target", "handheld_natural")
        )
        arguments = {"context_id": "context_delete_target"}
        with mock.patch(
            "lab.application.service._context_store", return_value=self.store
        ):
            denied = invoke(
                request("cpcs.context.profile.delete", arguments), role="operator"
            )
            self.assertEqual(denied["error"]["code"], "permission_denied")
            authorized = request("cpcs.context.profile.delete", arguments)
            authorized["authorization"] = {
                "schema": "cpcs.explicit_authorization/1.0",
                "authorization_id": "auth_context_delete",
                "authorized_by": "owner-test",
                "operation": "cpcs.context.profile.delete",
                "request_hash": authorization_request_hash(
                    "cpcs.context.profile.delete", arguments
                ),
                "reason": "Delete this exact local preference profile.",
            }
            deleted = invoke(authorized, role="operator")
            self.assertEqual(deleted["status"], "success")
            self.assertEqual(deleted["result"]["disposition"], "deleted")
        self.assertNotIn(
            "cpcs.context.profile.put",
            {row["name"] for row in list_operations("chat")},
        )
        self.assertIn(
            "cpcs.context.profile.put",
            {row["name"] for row in list_operations("operator")},
        )


if __name__ == "__main__":
    unittest.main()
