from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.query import default_request, reason
from lab.second_brain.src.terminology import (
    inspect_terminology_proposal,
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
        "c_facs_events",
        "c_action_atoms",
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


def _source_unit(root: Path) -> dict:
    passage = "FACS Action Units encode visible facial actions; physical action atoms are a separate motion vocabulary."
    digest = hashlib.sha256(passage.encode()).hexdigest()
    row = {
        "schema": "cpcs.source_unit/1.0",
        "id": "source_unit_" + digest[:24],
        "source_id": "src_sha256_" + digest,
        "source_ref": "fixture://terminology",
        "locator": "paragraph:1",
        "source_byte_hash": "sha256:" + digest,
        "content_sha256": "sha256:" + digest,
        "rights_basis": "owner_authorized_fixture",
        "media_type": "text/plain",
        "evidence_class": "authored",
        "storage": {"kind": "embedded_passage", "passage": passage},
        "aliases": ["fixture://terminology#paragraph:1"],
        "prior_record_hash": None,
        "record_hash": "sha256:" + "0" * 64,
    }
    row["record_hash"] = content_hash(row)
    write_rows(
        root / "lab/second_brain/immutable/source_units.jsonl", [row]
    )
    return row


class TerminologyResolutionTests(unittest.TestCase):
    def test_identifier_and_context_resolution_are_replay_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory), _concepts())
            first = resolve_terminology(
                "Compare AU1, AU01, and au-1 for a facial expression",
                "performance",
                root,
            )
            second = resolve_terminology(
                "Compare AU1, AU01, and au-1 for a facial expression",
                "performance",
                root,
            )
            self.assertEqual(first, second)
            identifiers = [
                row for row in first["matches"] if row["match_type"] == "identifier"
            ]
            self.assertEqual(len(identifiers), 1)
            self.assertEqual(identifiers[0]["canonical_identifier"], "AU1")
            self.assertEqual(identifiers[0]["inventory_status"], "not_registered")
            self.assertEqual(identifiers[0]["selected_concept_ids"], ["c_facs_events"])

            facial = resolve_terminology("facial action units for the brow", None, root)
            fight = resolve_terminology("physical action units for fight choreography", None, root)
            self.assertEqual(
                facial["matches"][0]["selected_sense_id"], "facs.action_unit"
            )
            self.assertEqual(
                fight["matches"][0]["selected_sense_id"], "motion.action_atom"
            )

            phase = resolve_terminology("impact follow-through into recovery", None, root)
            overlap = resolve_terminology("cape follow through with cloth lag", None, root)
            self.assertEqual(
                phase["matches"][0]["selected_sense_id"], "motion.action_phase"
            )
            self.assertEqual(
                overlap["matches"][0]["selected_sense_id"], "motion.secondary_overlap"
            )

    def test_unresolved_homonym_pauses_query_until_agent_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory), _concepts())
            unresolved = resolve_terminology("Use action units coding", None, root)
            self.assertEqual(unresolved["state"], "agent_resolution_required")
            blocked = reason(
                default_request(
                    "Use action units coding", minimum_status="ingested"
                ),
                root,
            )
            self.assertTrue(blocked["root_selection"]["terminology_blocked"])
            self.assertEqual(blocked["selected_concepts"], [])
            self.assertEqual(
                blocked["root_selection"]["terminology_gated_root_ids"],
                ["c_action_atoms", "c_facs_events"],
            )

            source = _source_unit(root)
            ontology_before = (
                root / "lab/second_brain/curated/ontology_registry.json"
            ).read_bytes()
            proposal = propose_terminology_resolution(
                unresolved,
                unresolved["agent_task"]["match_ids"][0],
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
                "The cited passage distinguishes facial Action Units from motion atoms.",
                root,
            )
            replay = propose_terminology_resolution(
                unresolved,
                unresolved["agent_task"]["match_ids"][0],
                "facs.action_unit",
                proposal["source_evidence"],
                proposal["agent"],
                proposal["rationale"],
                root,
            )
            self.assertEqual(proposal, replay)
            self.assertTrue(inspect_terminology_proposal(proposal["id"], root)["current"])

            resolved = reason(
                default_request(
                    "Use action units coding",
                    minimum_status="ingested",
                    terminology_proposal_ids=[proposal["id"]],
                ),
                root,
            )
            selected = [row["id"] for row in resolved["selected_concepts"]]
            self.assertIn("c_facs_events", selected)
            self.assertNotIn("c_action_atoms", selected)
            self.assertFalse(resolved["root_selection"]["terminology_blocked"])
            self.assertEqual(
                resolved["terminology_control"]["trust_class"],
                "interpreted_agent_resolution",
            )
            self.assertEqual(
                ontology_before,
                (root / "lab/second_brain/curated/ontology_registry.json").read_bytes(),
            )

            tampered = copy.deepcopy(unresolved)
            tampered["input"]["text"] = "changed"
            with self.assertRaisesRegex(ValidationFailure, "stale or tampered"):
                propose_terminology_resolution(
                    tampered,
                    unresolved["agent_task"]["match_ids"][0],
                    "facs.action_unit",
                    proposal["source_evidence"],
                    proposal["agent"],
                    proposal["rationale"],
                    root,
                )


if __name__ == "__main__":
    unittest.main()
