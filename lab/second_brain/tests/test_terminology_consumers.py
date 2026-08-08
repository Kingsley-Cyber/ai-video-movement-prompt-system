from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from lab.compiler.score import make_score_request, resolve_score
from lab.second_brain.src.context import build_context_bundle
from lab.second_brain.src.intent import build_intent_context
from lab.second_brain.src.source_extract import (
    _validate_bundle_invariants,
    extract_folder,
)
from lab.second_brain.src.terminology import (
    propose_terminology_resolution,
    resolve_terminology,
)
from lab.second_brain.src.validate import (
    REPO_ROOT,
    ValidationFailure,
    content_hash,
)
from lab.second_brain.tests.helpers import make_root, write_rows


def _concepts() -> list[dict]:
    wanted = {
        "c_action_atoms",
        "c_facs_events",
        "c_phase_landmarks",
        "c_secondary_motion",
    }
    return [
        row
        for row in (
            json.loads(line)
            for line in (REPO_ROOT / "lab/concepts.jsonl").read_text().splitlines()
            if line.strip()
        )
        if row["id"] in wanted
    ]


def _source_unit(
    root: Path,
    passage: str = (
        "FACS Action Units encode visible facial actions; physical action atoms "
        "are a separate motion vocabulary."
    ),
) -> dict:
    digest = hashlib.sha256(passage.encode()).hexdigest()
    row = {
        "schema": "cpcs.source_unit/1.0",
        "id": "source_unit_" + digest[:24],
        "source_id": "src_sha256_" + digest,
        "source_ref": "fixture://terminology-consumers",
        "locator": "paragraph:1",
        "source_byte_hash": "sha256:" + digest,
        "content_sha256": "sha256:" + digest,
        "rights_basis": "owner_authorized_fixture",
        "media_type": "text/plain",
        "evidence_class": "authored",
        "storage": {"kind": "embedded_passage", "passage": passage},
        "aliases": ["fixture://terminology-consumers#paragraph:1"],
        "prior_record_hash": None,
        "record_hash": "sha256:" + "0" * 64,
    }
    row["record_hash"] = content_hash(row)
    write_rows(
        root / "lab/second_brain/immutable/source_units.jsonl", [row]
    )
    return row


def _facial_proposal(root: Path, text: str) -> dict:
    resolution = resolve_terminology(text, None, root)
    source = _source_unit(root)
    return propose_terminology_resolution(
        resolution,
        resolution["agent_task"]["match_ids"][0],
        "facs.action_unit",
        [
            {
                "source_unit_id": source["id"],
                "content_sha256": source["content_sha256"],
            }
        ],
        {
            "client": "fixture-agent",
            "model": "fixture-model",
            "prompt_sha256": "sha256:" + "a" * 64,
        },
        "The cited source distinguishes facial Action Units from motion atoms.",
        root,
    )


class TerminologyConsumerTests(unittest.TestCase):
    def test_source_extraction_covers_each_candidate_with_recomputed_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = make_root(base, _concepts())
            source = base / "source"
            source.mkdir()
            (source / "action-units.md").write_text(
                "# Action Units\n\n"
                "Action units coding can mean visible facial actions or physical motion atoms.\n",
                encoding="utf-8",
            )
            bundle = extract_folder(
                source,
                research_goal="action units coding",
                rights_basis="owner_authorized_fixture",
                root=root,
            )
            self.assertEqual(
                {row["candidate_id"] for row in bundle["terminology_controls"]},
                {
                    row["candidate_id"]
                    for row in bundle["distillation_batch"]["candidates"]
                },
            )
            self.assertEqual(
                bundle["terminology_controls"][0]["resolution"]["state"],
                "agent_resolution_required",
            )
            tampered = copy.deepcopy(bundle)
            tampered["terminology_controls"][0]["domain"] = "performance"
            with self.assertRaisesRegex(
                ValidationFailure, "terminology control is stale"
            ):
                _validate_bundle_invariants(tampered, root)

    def test_context_hands_off_one_current_source_backed_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_root(Path(temporary), _concepts())
            proposal = _facial_proposal(root, "Use action units coding")
            bundle = build_context_bundle(
                "Use action units coding",
                token_budget=12_000,
                terminology_proposal_ids=[proposal["id"]],
                root=root,
            )
            self.assertEqual(bundle["terminology"]["proposal_ids"], [proposal["id"]])
            self.assertEqual(
                bundle["terminology"]["trust_class"],
                "interpreted_agent_resolution",
            )
            selected = {row["id"] for row in bundle["selected_concepts"]}
            self.assertIn("c_facs_events", selected)
            self.assertNotIn("c_action_atoms", selected)

    def test_compiler_rejects_an_unresolved_context_handoff(self) -> None:
        intent_context = build_intent_context(
            "Make a video with follow through", token_budget=12_000
        )
        self.assertEqual(
            intent_context["context_bundle"]["terminology"]["state"],
            "agent_resolution_required",
        )
        with self.assertRaisesRegex(
            ValidationFailure, "compiler admission requires resolved terminology"
        ):
            resolve_score(make_score_request(intent_context))

    def test_intent_context_carries_resolution_into_compiler_admission(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_root(Path(temporary), _concepts())
            write_rows(
                root / "lab/second_brain/curated/mappings.jsonl",
                [
                    json.loads(line)
                    for line in (
                        REPO_ROOT / "lab/second_brain/curated/mappings.jsonl"
                    ).read_text().splitlines()
                    if line.strip()
                ],
            )
            text = "Make a video with follow through"
            unresolved = build_intent_context(text, token_budget=12_000, root=root)
            request = unresolved["context_bundle"]["request"]
            resolution = resolve_terminology(
                request["query"], request["domain"], root
            )
            source = _source_unit(
                root,
                "Follow-through is the action phase after impact; secondary overlap "
                "is a separate continuing response in cloth or attached forms.",
            )
            proposal = propose_terminology_resolution(
                resolution,
                resolution["agent_task"]["match_ids"][0],
                "motion.action_phase",
                [
                    {
                        "source_unit_id": source["id"],
                        "content_sha256": source["content_sha256"],
                    }
                ],
                {
                    "client": "fixture-agent",
                    "model": "fixture-model",
                    "prompt_sha256": "sha256:" + "b" * 64,
                },
                "The passage separates the requested action phase from secondary overlap.",
                root,
            )
            resolved = build_intent_context(
                text,
                token_budget=12_000,
                terminology_proposal_ids=[proposal["id"]],
                root=root,
            )
            self.assertEqual(
                resolved["context_bundle"]["terminology"]["proposal_ids"],
                [proposal["id"]],
            )
            score = resolve_score(make_score_request(resolved), root)
            self.assertIn(score["score_status"], {"ready", "needs_input"})


if __name__ == "__main__":
    unittest.main()
