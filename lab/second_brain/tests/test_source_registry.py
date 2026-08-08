from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from lab.application.agent_brief import build_agent_brief
from lab.application.service import APPLICATION_POLICY, OPERATIONS, list_operations
from lab.second_brain.src.context import build_context_bundle
from lab.second_brain.src.curate import promote_proposal
from lab.second_brain.src.reflect import rebuild
from lab.second_brain.src.research_session import (
    list_packets,
    read_packet,
    register_source,
    submit_extraction,
)
from lab.second_brain.src.source_registry import (
    build_source_closure_report,
    load_source_units,
)
from lab.second_brain.src.validate import REPO_ROOT, ValidationFailure
from lab.second_brain.tests.helpers import concept, make_root, write_rows


def _registration(source: Path) -> dict:
    return {
        "source_kind": "authorized_folder",
        "folder": str(source),
        "research_goal": "bound flow and exact facial source answers",
        "rights_basis": "owner_authorized_fixture",
        "extractor": {
            "agent": "fixture-worker",
            "model": "fixture-model",
            "prompt_hash": "sha256:" + "a" * 64,
        },
        "registered_at": "2026-08-07T00:00:00Z",
    }


def _complete_no_candidate_session(root: Path, source: Path) -> tuple[str, dict]:
    registered = register_source(_registration(source), root)
    session_id = registered["session_id"]
    for packet_state in list_packets(session_id, root)["packets"]:
        packet = read_packet(
            session_id, packet_state["packet_id"], root
        )["packet"]
        chunk_ids = [row["chunk_id"] for row in packet["passages"]]
        submit_extraction(
            session_id,
            {
                "packet_id": packet["packet_id"],
                "candidates": [],
                "no_candidate": {
                    "reason_code": "insufficient_evidence",
                    "reason": "The fixture exercises source preservation without proposing repository truth.",
                    "evidence_refs": [
                        {
                            "chunk_id": chunk_id,
                            "claim": "The passage was assessed but is not promoted by this fixture.",
                        }
                        for chunk_id in chunk_ids
                    ],
                    "coverage": {
                        "disposition": "no_semantic_candidate",
                        "assessed_chunk_ids": chunk_ids,
                        "unresolved_questions": [
                            "Which reviewed proposal should operationalize this passage?"
                        ],
                        "limitations": [
                            "The source unit is evidence, not curated knowledge."
                        ],
                    },
                },
            },
            "2026-08-07T00:01:00Z",
            root,
        )
    result = OPERATIONS["cpcs.research.source.units.admit"].handler(
        {"session_id": session_id}, root
    )
    return session_id, result


def _review() -> dict:
    return {
        "source_verified": True,
        "source_locator_resolved": True,
        "duplicate_checked": True,
        "operationally_useful": True,
        "relationships_validated": True,
        "numeric_precision_supported": True,
        "reviewed_at": "2026-08-07T00:02:00Z",
        "notes": "fixture source review",
    }


class SourceRegistryTests(unittest.TestCase):
    def test_public_session_admission_is_idempotent_and_hash_verified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_root(base, [concept("c_bound_flow", "Bound Flow")])
            source = base / "source"
            source.mkdir()
            (source / "movement.md").write_text(
                "# Movement\n\nBound Flow contains movement.\n",
                encoding="utf-8",
            )
            session_id, first = _complete_no_candidate_session(root, source)
            second = OPERATIONS["cpcs.research.source.units.admit"].handler(
                {"session_id": session_id}, root
            )
            self.assertTrue(first["admission"]["admitted_ids"])
            self.assertEqual(second["admission"]["admitted_ids"], [])
            self.assertEqual(
                first["admission"]["registry_hash"],
                second["admission"]["registry_hash"],
            )
            units = load_source_units(root)
            self.assertTrue(units)
            registry = root / "lab/second_brain/immutable/source_units.jsonl"
            original = registry.read_text(encoding="utf-8")
            registry.write_text(original.replace("Bound Flow", "Bound Drift", 1), encoding="utf-8")
            with self.assertRaisesRegex(ValidationFailure, "hash"):
                load_source_units(root)

    def test_production_promotion_requires_one_registered_evidence_unit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_root(base, [concept("c_anchor", "Anchor")])
            source = base / "source"
            source.mkdir()
            (source / "movement.md").write_text(
                "# Movement\n\nBound Flow contains movement.\n",
                encoding="utf-8",
            )
            _, admission = _complete_no_candidate_session(root, source)
            unit = load_source_units(root)[0]
            (root / "lab/registry.yaml").write_text(
                "scripts:\n  second_brain_source_units: second_brain/immutable/source_units.jsonl\n",
                encoding="utf-8",
            )
            proposed = concept("ignored", "Registered source concept", status="ingested")
            proposed.pop("id")
            proposed["source"] = [f"{unit['source_ref']}#{unit['locator']}"]

            def proposal(proposal_id: str, content_sha256: str, name: str) -> dict:
                record = copy.deepcopy(proposed)
                record["name"] = name
                record["what"] = f"{name} operational definition"
                record["use_when"] = f"use {name}"
                record["nl_triggers"] = [name, f"{name} control", f"{name} technique"]
                return {
                    "proposal_id": proposal_id,
                    "proposal_type": "concept",
                    "proposed_record": record,
                    "source_evidence": [
                        {
                            "source_id": unit["source_ref"],
                            "locator": unit["locator"],
                            "claim": "The preserved passage supports this fixture concept.",
                            "content_sha256": content_sha256,
                        }
                    ],
                    "created_by": "manual",
                    "created_at": "2026-08-07T00:01:00Z",
                    "status": "pending",
                    "dedup_candidates": [],
                    "rejection_reason": None,
                    "promotion": None,
                }

            valid = proposal(
                "proposal_registered_source", unit["content_sha256"], "Registered source concept"
            )
            invalid = proposal(
                "proposal_unregistered_source", "sha256:" + "f" * 64, "Unregistered source concept"
            )
            write_rows(
                root / "lab/second_brain/staging/proposals.jsonl",
                [valid, invalid],
            )
            promoted = promote_proposal(
                valid["proposal_id"], "c_registered_source", "fixture_curator", _review(), root
            )
            self.assertEqual(
                promoted["provenance"]["source_evidence"][0]["source_unit_id"],
                unit["id"],
            )
            with self.assertRaisesRegex(ValidationFailure, "does not resolve"):
                promote_proposal(
                    invalid["proposal_id"],
                    "c_unregistered_source",
                    "fixture_curator",
                    _review(),
                    root,
                )

    def test_context_dereferences_passages_and_answers_only_exact_graph_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            row = concept("c_bound_flow", "Bound Flow")
            root = make_root(base, [row])
            source = base / "source"
            source.mkdir()
            (source / "movement.md").write_text(
                "# Movement\n\nBound Flow contains movement. The orbital marker zygomatic signal is documented.\n",
                encoding="utf-8",
            )
            _, admission = _complete_no_candidate_session(root, source)
            unit = load_source_units(root)[0]
            row["source"] = [f"{unit['source_ref']}#{unit['locator']}"]
            write_rows(root / "lab/concepts.jsonl", [row])
            rebuild(root)
            authority_before = {
                "concepts": (root / "lab/concepts.jsonl").read_bytes(),
                "source_units": (
                    root / "lab/second_brain/immutable/source_units.jsonl"
                ).read_bytes(),
            }
            context = build_context_bundle(
                "bound flow movement", token_budget=8_000, root=root
            )
            passages = [
                evidence
                for evidence in context["curated_evidence"]
                if evidence["evidence_kind"] == "source_unit"
            ]
            self.assertTrue(passages)
            for passage in passages:
                self.assertEqual(
                    passage["content_hash"],
                    "sha256:"
                    + hashlib.sha256(passage["passage"].encode("utf-8")).hexdigest(),
                )
            fallback = build_context_bundle(
                "orbital marker zygomatic", token_budget=8_000, root=root
            )["source_answer"]
            self.assertEqual(fallback["disposition"], "answered_local")
            self.assertEqual(
                fallback["answer_span"]["quote_hash"],
                "sha256:"
                + hashlib.sha256(
                    fallback["answer_span"]["quote"].encode("utf-8")
                ).hexdigest(),
            )
            self.assertEqual(
                authority_before,
                {
                    "concepts": (root / "lab/concepts.jsonl").read_bytes(),
                    "source_units": (
                        root / "lab/second_brain/immutable/source_units.jsonl"
                    ).read_bytes(),
                },
            )

    def test_live_polymath_dependencies_are_explicitly_quarantined_and_briefed(self) -> None:
        report = build_source_closure_report()
        self.assertEqual(report["counts"]["polymath_dependent_concepts"], 37)
        self.assertEqual(report["counts"]["polymath_quarantined_concepts"], 37)
        catalogs = {
            role: {row["name"] for row in list_operations(role)}
            for role in ("chat", "operator", "curator")
        }
        self.assertTrue(
            {"cpcs.source.status", "cpcs.source.resolve"} <= catalogs["chat"]
        )
        self.assertNotIn(
            "cpcs.research.source.units.admit", catalogs["operator"]
        )
        self.assertIn(
            "cpcs.research.source.units.admit", catalogs["curator"]
        )
        brief = build_agent_brief(
            {"task": "Inspect exact research source context and close source lineage", "role": "operator"},
            operation_catalog=list_operations("curator"),
            application_policy=APPLICATION_POLICY,
            root=REPO_ROOT,
        )
        operations = {row["name"]: row for row in brief["operations"]}
        self.assertIn("cpcs.source.resolve", operations)
        self.assertFalse(
            operations["cpcs.research.source.units.admit"]["available_to_requested_role"]
        )


if __name__ == "__main__":
    unittest.main()
