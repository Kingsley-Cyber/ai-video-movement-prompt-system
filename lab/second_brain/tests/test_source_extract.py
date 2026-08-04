from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lab.second_brain.src.distill import run_distillation
from lab.second_brain.src.context import build_context_bundle
from lab.second_brain.src.curate import promote_distillation_bundle
from lab.second_brain.src.query import default_request, reason
from lab.second_brain.src.source_extract import (
    DEFAULT_CONFIGURATION,
    _validate_bundle_invariants,
    extract_folder,
    extract_retrieved_passages,
    write_bundle,
)
from lab.second_brain.src.validate import REPO_ROOT, ValidationFailure, canonical_json_bytes
from lab.second_brain.tests.helpers import concept, make_root


def authority_snapshot(root: Path) -> dict[str, bytes]:
    paths = [root / "lab/concepts.jsonl"]
    second_brain = root / "lab/second_brain"
    for tier in ("curated", "immutable", "derived", "staging"):
        tier_path = second_brain / tier
        if tier_path.exists():
            paths.extend(path for path in tier_path.rglob("*") if path.is_file())
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(paths)
    }


def write_multiformat_fixture(folder: Path) -> None:
    folder.mkdir(parents=True)
    (folder / "direction.md").write_text(
        """---
title: Decimal Motion Notes
author: Fixture
---
# Decimal Spatial Movement

Decimal waypoint values preserve small spatial changes in a directed hand path for repeatable motion studies.

$$
p(t) = (x(t), y(t))
$$

- Keep the coordinate basis explicit.
- Preserve the subject-relative frame.

| field | meaning |
|---|---|
| x | horizontal position |

> Smith 2026, section 2.

```json
{"x": 0.125, "y": 0.875}
```
""",
        encoding="utf-8",
    )
    (folder / "notes.txt").write_text(
        "Bound flow: A contained movement quality that limits free continuation and supports restrained direction.\n\n"
        "A second paragraph keeps source line ranges independently addressable for later review.",
        encoding="utf-8",
    )
    (folder / "controls.json").write_text(
        json.dumps({"motion": {"precision": "decimal spatial waypoints", "scale": 0.25}}),
        encoding="utf-8",
    )
    (folder / "records.jsonl").write_text(
        '{"term":"contact timing","definition":"Record the intended contact beat before provider compilation."}\n'
        '{"term":"recovery","definition":"Preserve the recovery phase after the visible contact event."}\n',
        encoding="utf-8",
    )
    (folder / "rules.yaml").write_text(
        "movement:\n  rule: preserve causal phase order\n  exception: diagnostic replay\n",
        encoding="utf-8",
    )
    (folder / "sequence.xml").write_text(
        '<sequence xmlns="urn:cpcs"><beat id="b1">anticipation</beat><beat id="b2">contact</beat></sequence>',
        encoding="utf-8",
    )
    (folder / "ignored.bin").write_bytes(b"not a supported research source")


def passage_envelope(text: str) -> dict:
    import hashlib

    return {
        "schema": "cpcs.retrieved_passages/1.0",
        "retrieval": {
            "adapter": "polymath_mcp",
            "corpus_id": "fixture-corpus",
            "query": "decimal spatial movement",
            "tool": "polymath_search",
            "parameters": {"top_k": 4},
            "retrieved_at": "2026-08-03T00:00:00Z",
        },
        "rights_basis": "authorized_research_fixture",
        "passages": [
            {
                "source_id": "polymath://book/one",
                "title": "Movement Precision",
                "locator": "chapter_2.section_4",
                "content_hash": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "text": text,
            }
        ],
    }


class SourceExtractionTests(unittest.TestCase):
    def test_typed_research_objects_distill_promote_and_retrieve_through_one_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_root(
                base / "root",
                [concept("c_inverse_kinematics", "inverse kinematics motion control", "motion")],
            )
            source = base / "sources"
            source.mkdir()
            (source / "ik.md").write_text(
                """# Inverse kinematics motion control

Inverse kinematics solves joint parameters against visible target and constraint terms. A directing workflow can use its terms as controls or evaluation criteria without claiming that a video provider executes the solver.

$$
E_{IK}(q) = w_p E_p(q) + w_c E_c(q)
$$

## Bounded solve method

Specify the target, declare constraints, solve candidate parameters, and inspect residual error.

## Creative mechanism

Explicit targets plus constraints narrow motion ambiguity, which can improve readable staged near-contact while preserving an evaluation-only fallback.
""",
                encoding="utf-8",
            )
            prepared = extract_folder(
                source,
                research_goal="inverse kinematics motion control target constraints",
                rights_basis="owner_authorized_fixture",
                root=root,
            )
            self.assertTrue(
                any(row["kind"] == "equation" for row in prepared["chunks"])
            )
            packet = prepared["semantic_packets"][0]
            evidence_chunks = {
                row["kind"]: row["chunk_id"]
                for row in prepared["chunks"]
                if row["chunk_id"] in {passage["chunk_id"] for passage in packet["passages"]}
            }
            default_chunk = packet["passages"][0]["chunk_id"]
            self.assertIn("equation", evidence_chunks)
            equation_chunk = evidence_chunks["equation"]
            source_link = [{"ref": "file:ik.md", "locator": "source section"}]
            records = [
                (
                    "claim",
                    "ik_claim",
                    "claim_ik_target_constraints",
                    {
                        "concept_ids": ["c_inverse_kinematics"],
                        "statement": "Inverse kinematics solves parameters against target and constraint terms.",
                        "claim_kind": "definition",
                        "epistemic_class": "interpreted",
                        "confidence": 0.8,
                        "limitations": ["Provider execution of the solver is not established."],
                        "status": "ingested",
                        "sources": source_link,
                    },
                    default_chunk,
                ),
                (
                    "equation",
                    "ik_equation",
                    "equation_ik_objective",
                    {
                        "concept_ids": ["c_inverse_kinematics"],
                        "name": "Weighted inverse kinematics objective",
                        "expression": "E_{IK}(q) = w_p E_p(q) + w_c E_c(q)",
                        "notation": "latex",
                        "variables": [
                            {"symbol": "q", "meaning": "candidate joint parameters", "role": "input", "unit": None},
                            {"symbol": "E_p", "meaning": "target-position error", "role": "preference", "unit": None},
                            {"symbol": "E_c", "meaning": "constraint error", "role": "constraint", "unit": None},
                        ],
                        "assumptions": ["The coordinate basis and target are declared."],
                        "constraints": ["Do not infer hidden three-dimensional motion from a rendered frame."],
                        "operational_effect": "Separates target preference from constraint penalties for score and verification planning.",
                        "execution_scope": "mixed",
                        "epistemic_class": "interpreted",
                        "confidence": 0.75,
                        "status": "ingested",
                        "sources": source_link,
                    },
                    equation_chunk,
                ),
                (
                    "method",
                    "ik_method",
                    "method_bounded_ik",
                    {
                        "concept_ids": ["c_inverse_kinematics"],
                        "name": "Bounded inverse kinematics direction",
                        "objective": "Translate a visible motion target into explicit constraints and evaluable residuals.",
                        "steps": ["Declare target and coordinate basis.", "Declare constraints.", "Evaluate residual error."],
                        "inputs": ["target", "coordinate basis", "constraints"],
                        "outputs": ["candidate motion controls", "residual metrics"],
                        "constraints": ["Keep provider capability separate from mathematical specification."],
                        "failure_conditions": ["Undeclared coordinate basis", "Unsupported provider precision"],
                        "epistemic_class": "interpreted",
                        "confidence": 0.7,
                        "status": "ingested",
                        "sources": source_link,
                    },
                    default_chunk,
                ),
                (
                    "mechanism",
                    "ik_mechanism",
                    "mechanism_target_constraint_readability",
                    {
                        "concept_ids": ["c_inverse_kinematics"],
                        "name": "Target-constraint readability",
                        "intent_effect": "Make staged near-contact motion more readable and controllable.",
                        "causal_chain": ["Declare visible target", "Constrain the path", "Reduce motion ambiguity"],
                        "controls": ["motion.target", "motion.constraints", "verification.residual"],
                        "prerequisites": ["Visible target", "Declared coordinate basis"],
                        "failure_conditions": ["Provider ignores fine spatial controls"],
                        "limitations": ["Mechanism is a directing hypothesis until render evidence qualifies it."],
                        "epistemic_class": "interpreted",
                        "confidence": 0.55,
                        "status": "ingested",
                        "sources": source_link,
                    },
                    default_chunk,
                ),
            ]
            response = {
                "schema": "cpcs.semantic_extraction_response/1.0",
                "extractor": {
                    "agent": "fixture-semantic-worker",
                    "model": "fixture-model-1",
                    "prompt_hash": "sha256:" + "c" * 64,
                },
                "packet_results": [
                    {
                        "packet_id": packet["packet_id"],
                        "candidates": [
                            {
                                "candidate_key": key,
                                "proposal_type": object_type,
                                "suggested_id": suggested_id,
                                "proposed_record": record,
                                "evidence_refs": [
                                    {"chunk_id": chunk_id, "claim": f"The passage supports {object_type} {key}."}
                                ],
                            }
                            for object_type, key, suggested_id, record, chunk_id in records
                        ],
                    }
                ],
            }
            bundle = extract_folder(
                source,
                research_goal="inverse kinematics motion control target constraints",
                rights_basis="owner_authorized_fixture",
                semantic_response=response,
                root=root,
            )
            malformed = copy.deepcopy(bundle["distillation_batch"])
            next(
                row for row in malformed["candidates"]
                if row["proposal_type"] == "equation"
            )["proposed_record"].pop("expression")
            with self.assertRaisesRegex(ValidationFailure, "equation:.*expression"):
                run_distillation(malformed, root)
            run = run_distillation(bundle["distillation_batch"], root)
            typed_decisions = [
                row for row in run["candidate_decisions"]
                if row["proposal_type"] in {"claim", "equation", "method", "mechanism"}
            ]
            self.assertEqual(
                {row["disposition"] for row in typed_decisions},
                {"stage_claim", "stage_equation", "stage_method", "stage_mechanism"},
            )
            durable_ids = {
                row["proposal_id"]: records_by_type[row["proposal_type"]]
                for row in typed_decisions
                for records_by_type in [{
                    "claim": "claim_ik_target_constraints",
                    "equation": "equation_ik_objective",
                    "method": "method_bounded_ik",
                    "mechanism": "mechanism_target_constraint_readability",
                }]
            }
            review = {
                "source_verified": True,
                "source_locator_resolved": True,
                "duplicate_checked": True,
                "operationally_useful": True,
                "relationships_validated": True,
                "numeric_precision_supported": True,
                "reviewed_at": "2026-08-04T00:00:00Z",
                "notes": "fixture review",
            }
            promoted = promote_distillation_bundle(
                run["id"], durable_ids, "fixture_curator", review, root
            )
            self.assertEqual(set(promoted["promoted_ids"]), set(durable_ids.values()))
            reasoning = reason(
                default_request(
                    "inverse kinematics motion control",
                    minimum_status="ingested",
                ),
                root,
            )
            self.assertEqual(
                {row["object_type"] for row in reasoning["knowledge_objects"]},
                {"claim", "equation", "method", "mechanism"},
            )
            context = build_context_bundle(
                "inverse kinematics motion control",
                token_budget=40_000,
                minimum_status="ingested",
                include_external_evidence=False,
                root=root,
            )
            self.assertEqual(
                {row["object_type"] for row in context["knowledge_objects"]},
                {"claim", "equation", "method", "mechanism"},
            )
            self.assertEqual(
                canonical_json_bytes(context),
                canonical_json_bytes(
                    build_context_bundle(
                        "inverse kinematics motion control",
                        token_budget=40_000,
                        minimum_status="ingested",
                        include_external_evidence=False,
                        root=root,
                    )
                ),
            )

    def test_all_formats_replay_with_locators_hashes_orientation_and_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_root(base / "root", [concept("c_anchor", "directed movement", "motion")])
            source = base / "sources"
            write_multiformat_fixture(source)
            before = authority_snapshot(root)
            first = extract_folder(
                source,
                research_goal="decimal spatial movement and restrained performance",
                rights_basis="owner_authorized_fixture",
                root=root,
            )
            second = extract_folder(
                source,
                research_goal="decimal spatial movement and restrained performance",
                rights_basis="owner_authorized_fixture",
                root=root,
            )
            self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
            _validate_bundle_invariants(first, root)
            self.assertEqual(before, authority_snapshot(root))
            parsed = {
                row["extension"]
                for row in first["inventory"]
                if row["status"] == "parsed"
            }
            self.assertEqual(parsed, {".md", ".txt", ".json", ".jsonl", ".yaml", ".xml"})
            self.assertEqual(
                next(row for row in first["inventory"] if row["extension"] == ".bin")["status"],
                "unsupported",
            )
            locators = {row["locator"].split(":", 1)[0] for row in first["chunks"]}
            self.assertTrue({"md", "text", "json", "jsonl", "yaml", "xml"} <= locators)
            self.assertTrue(
                any(row["kind"] == "equation" for row in first["chunks"])
            )
            for chunk in first["chunks"]:
                self.assertLessEqual(len(chunk["text"]), first["configuration"]["max_chunk_chars"])
                self.assertTrue(chunk["content_sha256"].startswith("sha256:"))
            coverage = first["coverage"]
            self.assertEqual(coverage["sections_total"], coverage["sections_with_disposition"])
            self.assertEqual(
                coverage["sections_total"], len(coverage["section_dispositions"])
            )
            self.assertEqual(
                {row["batch_id"] for row in first["source_ledger"]},
                {first["distillation_batch"]["batch_id"]},
            )
            self.assertTrue(first["orientation"])
            self.assertEqual(
                first["semantic_packets"][0]["allowed_outputs"],
                ["concept", "edge", "intent", "mapping", "rule", "claim", "equation", "method", "mechanism"],
            )
            self.assertTrue(first["semantic_packets"][0]["existing_concepts"])
            self.assertTrue(first["distillation_batch"]["candidates"])
            tampered = copy.deepcopy(first)
            tampered["distillation_batch"]["candidates"][0]["source_evidence"][0][
                "content_sha256"
            ] = "sha256:" + "0" * 64
            with self.assertRaisesRegex(ValidationFailure, "evidence does not resolve"):
                _validate_bundle_invariants(tampered, root)

    def test_large_source_is_chunked_into_bounded_semantic_packets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_root(base / "root", [concept("c_anchor", "spatial movement", "motion")])
            source = base / "sources"
            source.mkdir()
            paragraphs = [
                f"# Spatial Section {index}\n\nDecimal spatial movement paragraph {index} "
                + ("describes controlled motion evidence. " * 80)
                for index in range(18)
            ]
            (source / "large.md").write_text("\n\n".join(paragraphs), encoding="utf-8")
            config = copy.deepcopy(DEFAULT_CONFIGURATION)
            config.update(
                {
                    "max_chunk_chars": 900,
                    "max_packet_chars": 2_700,
                    "max_passages_per_packet": 4,
                    "max_semantic_chunks": 30,
                }
            )
            bundle = extract_folder(
                source,
                research_goal="decimal spatial movement",
                rights_basis="owner_authorized_fixture",
                configuration=config,
                root=root,
            )
            self.assertGreater(len(bundle["chunks"]), 18)
            self.assertGreater(len(bundle["semantic_packets"]), 1)
            source_chars = sum(row["byte_size"] for row in bundle["inventory"])
            for packet in bundle["semantic_packets"]:
                self.assertLessEqual(len(packet["passages"]), 4)
                self.assertLessEqual(packet["passage_chars"], 2_700)
                self.assertLess(packet["passage_chars"], source_chars)

    def test_semantic_response_is_packet_bound_and_existing_distiller_stages_connected_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_root(
                base / "root",
                [concept("c_anchor", "Laban direction framework", "motion")],
            )
            source = base / "sources"
            source.mkdir()
            (source / "decimal.md").write_text(
                "# Decimal waypoint precision\n\nUsing decimal waypoint values can preserve subtle hand-path changes in a spatial movement prompt.",
                encoding="utf-8",
            )
            prepared = extract_folder(
                source,
                research_goal="decimal waypoint spatial movement",
                rights_basis="owner_authorized_fixture",
                root=root,
            )
            packet = prepared["semantic_packets"][0]
            chunk_id = packet["passages"][0]["chunk_id"]
            concept_record = {
                "kind": "technique",
                "name": "Decimal waypoint precision",
                "what": "Use decimal waypoint values to preserve subtle changes in a directed spatial hand path.",
                "use_when": "precise spatial movement must remain explicit",
                "nl_triggers": [
                    "decimal waypoint movement",
                    "precise spatial hand path",
                    "decimal motion coordinates",
                ],
                "status": "ingested",
                "evidence": [],
                "source": ["file:decimal.md"],
                "layer": "motion",
            }
            response = {
                "schema": "cpcs.semantic_extraction_response/1.0",
                "extractor": {
                    "agent": "fixture-semantic-worker",
                    "model": "fixture-model-1",
                    "prompt_hash": "sha256:" + "b" * 64,
                },
                "packet_results": [
                    {
                        "packet_id": packet["packet_id"],
                        "candidates": [
                            {
                                "candidate_key": "decimal_concept",
                                "proposal_type": "concept",
                                "suggested_id": "c_decimal_waypoint_precision",
                                "proposed_record": concept_record,
                                "evidence_refs": [
                                    {"chunk_id": chunk_id, "claim": "The passage defines decimal waypoint precision."}
                                ],
                            },
                            {
                                "candidate_key": "decimal_placement",
                                "proposal_type": "edge",
                                "suggested_id": None,
                                "proposed_record": {
                                    "u": "c_decimal_waypoint_precision",
                                    "v": "c_anchor",
                                    "type": "refines",
                                    "context": "spatial movement precision",
                                    "authored_by": "local_source_proposal",
                                    "note": "The proposed concept specializes the existing direction framework.",
                                    "sources": [{"ref": "file:decimal.md", "locator": "heading"}],
                                },
                                "evidence_refs": [
                                    {"chunk_id": chunk_id, "claim": "The technique refines spatial movement direction."}
                                ],
                            },
                            {
                                "candidate_key": "decimal_mapping",
                                "proposal_type": "mapping",
                                "suggested_id": None,
                                "proposed_record": {
                                    "concept_id": "c_decimal_waypoint_precision",
                                    "target_type": "control",
                                    "target_id": "motion.decimal_waypoints",
                                    "encoding": "json",
                                    "mapping": {"value_type": "decimal_coordinate_sequence"},
                                    "loss": "low",
                                    "provider": None,
                                    "model_version": None,
                                    "sources": ["file:decimal.md"],
                                },
                                "evidence_refs": [
                                    {"chunk_id": chunk_id, "claim": "The passage supports a decimal coordinate control mapping."}
                                ],
                            },
                        ],
                    }
                ],
            }
            bundle = extract_folder(
                source,
                research_goal="decimal waypoint spatial movement",
                rights_basis="owner_authorized_fixture",
                semantic_response=response,
                root=root,
            )
            before = authority_snapshot(root)
            result = run_distillation(bundle["distillation_batch"], root)
            semantic = {
                row["candidate_id"]: row
                for row in result["candidate_decisions"]
                if row["candidate_id"].startswith("candidate_semantic_")
            }
            self.assertEqual(len(semantic), 3)
            self.assertEqual(
                {row["disposition"] for row in semantic.values()},
                {"stage_new", "stage_relationship", "stage_mapping"},
            )
            after = authority_snapshot(root)
            for path, body in before.items():
                if "/staging/" not in f"/{path}":
                    self.assertEqual(body, after[path])
            replay = extract_folder(
                source,
                research_goal="decimal waypoint spatial movement",
                rights_basis="owner_authorized_fixture",
                semantic_response=copy.deepcopy(response),
                root=root,
            )
            self.assertEqual(bundle["bundle_id"], replay["bundle_id"])

            bad = copy.deepcopy(response)
            bad["packet_results"][0]["candidates"][0]["evidence_refs"][0]["chunk_id"] = (
                "chunk_" + "0" * 24
            )
            with self.assertRaisesRegex(ValidationFailure, "outside packet"):
                extract_folder(
                    source,
                    research_goal="decimal waypoint spatial movement",
                    rights_basis="owner_authorized_fixture",
                    semantic_response=bad,
                    root=root,
                )

    def test_polymath_passages_preserve_retrieval_lineage_and_reject_hash_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_root(Path(directory), [concept("c_anchor", "movement", "motion")])
            text = "Decimal spatial movement can encode small hand-path changes while preserving a named coordinate basis."
            envelope = passage_envelope(text)
            first = extract_retrieved_passages(envelope, root=root)
            second = extract_retrieved_passages(copy.deepcopy(envelope), root=root)
            self.assertEqual(first, second)
            self.assertEqual(first["source_kind"], "polymath_passages")
            self.assertEqual(
                {row["created_by"] for row in first["distillation_batch"]["candidates"]},
                {"polymath_mcp"},
            )
            self.assertEqual(
                first["distillation_batch"]["retrieval"]["tool"], "polymath_search"
            )
            self.assertEqual(first["source_ledger"][0]["source_ref"], "polymath://book/one")
            tampered = copy.deepcopy(envelope)
            tampered["passages"][0]["text"] += " changed"
            with self.assertRaisesRegex(ValidationFailure, "hash mismatch"):
                extract_retrieved_passages(tampered, root=root)
            duplicate = copy.deepcopy(envelope)
            duplicate["passages"].append(copy.deepcopy(duplicate["passages"][0]))
            with self.assertRaisesRegex(ValidationFailure, "locator repeats"):
                extract_retrieved_passages(duplicate, root=root)
            config = copy.deepcopy(DEFAULT_CONFIGURATION)
            config["max_file_bytes"] = len(text.encode("utf-8")) - 1
            with self.assertRaisesRegex(ValidationFailure, "max_file_bytes"):
                extract_retrieved_passages(envelope, configuration=config, root=root)

    def test_symlink_yaml_alias_custom_tag_and_xml_entities_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_root(base / "root", [concept("c_anchor", "movement", "motion")])
            outside = base / "outside.md"
            outside.write_text("# Outside\n\nThis content must not enter the authorized folder.", encoding="utf-8")
            source = base / "symlink-source"
            source.mkdir()
            (source / "escape.md").symlink_to(outside)
            with self.assertRaisesRegex(ValidationFailure, "symlink file"):
                extract_folder(
                    source,
                    research_goal="movement",
                    rights_basis="owner_authorized_fixture",
                    root=root,
                )

            fifo_source = base / "fifo-source"
            fifo_source.mkdir()
            os.mkfifo(fifo_source / "pipe.md")
            with self.assertRaisesRegex(ValidationFailure, "non-regular source"):
                extract_folder(
                    fifo_source,
                    research_goal="movement",
                    rights_basis="owner_authorized_fixture",
                    root=root,
                )

            yaml_source = base / "yaml-source"
            yaml_source.mkdir()
            (yaml_source / "unsafe.yaml").write_text("value: !!python/object/apply:os.system ['id']", encoding="utf-8")
            with self.assertRaisesRegex(ValidationFailure, "unsafe or invalid YAML"):
                extract_folder(
                    yaml_source,
                    research_goal="movement",
                    rights_basis="owner_authorized_fixture",
                    root=root,
                )
            (yaml_source / "unsafe.yaml").write_text("loop: &loop [*loop]", encoding="utf-8")
            with self.assertRaisesRegex(ValidationFailure, "aliases or cyclic"):
                extract_folder(
                    yaml_source,
                    research_goal="movement",
                    rights_basis="owner_authorized_fixture",
                    root=root,
                )

            xml_source = base / "xml-source"
            xml_source.mkdir()
            (xml_source / "unsafe.xml").write_text(
                '<!DOCTYPE x [<!ENTITY leak SYSTEM "file:///etc/passwd">]><x>&leak;</x>',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValidationFailure, "DTD and entity"):
                extract_folder(
                    xml_source,
                    research_goal="movement",
                    rights_basis="owner_authorized_fixture",
                    root=root,
                )

    def test_tree_depth_file_size_output_scope_and_overwrite_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_root(base / "root", [concept("c_anchor", "movement", "motion")])
            (root / "work").mkdir()
            source = base / "sources"
            source.mkdir()
            (source / "deep.json").write_text('{"a":{"b":{"c":"deep value for movement direction"}}}', encoding="utf-8")
            config = copy.deepcopy(DEFAULT_CONFIGURATION)
            config["max_tree_depth"] = 1
            with self.assertRaisesRegex(ValidationFailure, "depth limit"):
                extract_folder(
                    source,
                    research_goal="movement",
                    rights_basis="owner_authorized_fixture",
                    configuration=config,
                    root=root,
                )
            config = copy.deepcopy(DEFAULT_CONFIGURATION)
            config["max_file_bytes"] = 8
            with self.assertRaisesRegex(ValidationFailure, "max_file_bytes"):
                extract_folder(
                    source,
                    research_goal="movement",
                    rights_basis="owner_authorized_fixture",
                    configuration=config,
                    root=root,
                )
            bundle = extract_folder(
                source,
                research_goal="movement",
                rights_basis="owner_authorized_fixture",
                root=root,
            )
            output = root / "work/source-bundle.json"
            write_bundle(bundle, output, root)
            self.assertEqual(output.read_bytes(), canonical_json_bytes(bundle))
            with self.assertRaises(FileExistsError):
                write_bundle(bundle, output, root)
            with self.assertRaises(PermissionError):
                write_bundle(bundle, root / "lab/second_brain/curated/escape.json", root)

    def test_public_folder_cli_replays_without_authority_mutation(self) -> None:
        before = authority_snapshot(REPO_ROOT)
        work = REPO_ROOT / "work"
        work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as directory:
            base = Path(directory)
            source = base / "sources"
            source.mkdir()
            (source / "note.md").write_text(
                "# Restrained motion\n\nBound flow contains continuation and can support restrained performance direction.",
                encoding="utf-8",
            )
            outputs = []
            for name in ("first.json", "second.json"):
                output = base / name
                process = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "lab.second_brain.src.source_extract",
                        "folder",
                        str(source),
                        "--research-goal",
                        "restrained movement",
                        "--rights-basis",
                        "owner_authorized_fixture",
                        "--output",
                        str(output),
                    ],
                    cwd=REPO_ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                result = json.loads(process.stdout)
                self.assertEqual(result["output"], str(output))
                outputs.append(output.read_bytes())
            self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(before, authority_snapshot(REPO_ROOT))


if __name__ == "__main__":
    unittest.main()
