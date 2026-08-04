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
from lab.second_brain.src.indexes import build_index_catalog
from lab.second_brain.src.query import (
    default_request,
    reason,
    search_knowledge_objects,
)
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
                [
                    concept("c_inverse_kinematics", "inverse kinematics motion control", "motion"),
                    concept("c_provider_behavior", "provider control compliance", "provider"),
                ],
            )
            source = base / "sources"
            source.mkdir()
            (source / "ik.md").write_text(
                """---
title: Bounded IK Direction
source_id: fixture-ik-2026
---
# Inverse kinematics motion control

Inverse kinematics solves joint parameters against visible target and constraint terms. A directing workflow can use its terms as controls or evaluation criteria without claiming that a video provider executes the solver.

The target-constraint claim is repeated here using equivalent wording: inverse kinematics solves joint parameters from target and constraint terms.

$$
E_{IK}(q) = w_p E_p(q) + w_c E_c(q)
$$

## Bounded solve method

Specify the target, declare constraints, solve candidate parameters, and inspect residual error.

| term | directorial meaning |
|---|---|
| E_p | visible target-position error |
| E_c | declared constraint error |

### Structured control examples

```yaml
motion:
  target_precision: 0.125
```

```json
{"motion": {"constraint_weight": 0.875}}
```

```xml
<motion><target precision="0.125" /></motion>
```

```python
residual = position_error + constraint_error
```

## Creative mechanism

Explicit targets plus constraints narrow motion ambiguity, which can improve readable staged near-contact while preserving an evaluation-only fallback.

One source disagrees: a provider may ignore target and constraint terms, so the technique does not necessarily improve readable motion.

An unverified statement says that a low residual always guarantees cinematic realism.

## Irrelevant catering note

The crew lunch menu contains soup and bread. [Fixture source, section 9]
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
            }
            self.assertIn("equation", evidence_chunks)
            equation_chunk = evidence_chunks["equation"]
            packet_by_chunk = {
                passage["chunk_id"]: semantic_packet["packet_id"]
                for semantic_packet in prepared["semantic_packets"]
                for passage in semantic_packet["passages"]
            }
            def located_chunk(fragment: str) -> str:
                return next(
                    row["chunk_id"]
                    for row in prepared["chunks"]
                    if fragment in row["text"] and row["chunk_id"] in packet_by_chunk
                )

            main_chunk = located_chunk("solves joint parameters against visible target")
            duplicate_chunk = located_chunk("claim is repeated here using equivalent wording")
            method_chunk = located_chunk("Specify the target, declare constraints")
            mechanism_chunk = located_chunk("Explicit targets plus constraints narrow motion ambiguity")
            contradiction_chunk = located_chunk("One source disagrees")
            unverified_chunk = located_chunk("An unverified statement")
            source_link = [
                {
                    "ref": "placeholder://replaced-by-adapter",
                    "locator": "placeholder",
                    "content_sha256": "sha256:" + "0" * 64,
                }
            ]
            records = [
                (
                    "claim",
                    "claim_a_main",
                    "claim_ik_target_constraints",
                    {
                        "concept_ids": ["c_inverse_kinematics"],
                        "statement": "Inverse kinematics solves parameters against target and constraint terms.",
                        "claim_kind": "definition",
                        "method_ids": ["method_bounded_ik"],
                        "supports_claim_ids": [],
                        "contradicts_claim_ids": ["claim_ik_provider_may_ignore_controls"],
                        "epistemic_class": "interpreted",
                        "evidence_status": "supported",
                        "confidence": 0.8,
                        "confidence_basis": "One source-located definition with no render qualification.",
                        "limitations": ["Provider execution of the solver is not established."],
                        "status": "ingested",
                        "sources": source_link,
                    },
                    main_chunk,
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
                        "solved_quantity": "weighted inverse-kinematics objective E_{IK}(q)",
                        "terms": [
                            {"symbol": "w_p E_p(q)", "meaning": "weighted target-position error"},
                            {"symbol": "w_c E_c(q)", "meaning": "weighted constraint error"},
                        ],
                        "variables": [
                            {"symbol": "q", "meaning": "candidate joint parameters", "role": "input", "unit": None},
                            {"symbol": "E_p", "meaning": "target-position error", "role": "preference", "unit": None},
                            {"symbol": "E_c", "meaning": "constraint error", "role": "constraint", "unit": None},
                        ],
                        "assumptions": ["The coordinate basis and target are declared."],
                        "constraints": ["Do not infer hidden three-dimensional motion from a rendered frame."],
                        "method_ids": ["method_bounded_ik"],
                        "mechanism_ids": ["mechanism_target_constraint_readability"],
                        "operational_mappings": [
                            {
                                "control_id": "motion.target_precision",
                                "effect": "Express the reviewed target tolerance.",
                                "method_id": "method_bounded_ik",
                            }
                        ],
                        "operational_effect": "Separates target preference from constraint penalties for score and verification planning.",
                        "execution_scope": "mixed",
                        "epistemic_class": "interpreted",
                        "evidence_status": "supported",
                        "confidence": 0.75,
                        "confidence_basis": "Exact source expression with interpreted directorial mappings.",
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
                        "purpose": "Translate a visible motion target into explicit constraints and evaluable residuals.",
                        "steps": ["Declare target and coordinate basis.", "Declare constraints.", "Evaluate residual error."],
                        "inputs": ["target", "coordinate basis", "constraints"],
                        "outputs": ["candidate motion controls", "residual metrics"],
                        "assumptions": ["The intended target is visible and source-relative."],
                        "applicability": ["Staged motion with an explicit visible target."],
                        "constraints": ["Keep provider capability separate from mathematical specification."],
                        "limitations": ["Fine numeric controls may not survive provider translation."],
                        "failure_conditions": ["Undeclared coordinate basis", "Unsupported provider precision"],
                        "equation_ids": ["equation_ik_objective"],
                        "mechanism_ids": ["mechanism_target_constraint_readability"],
                        "epistemic_class": "interpreted",
                        "evidence_status": "supported",
                        "confidence": 0.7,
                        "confidence_basis": "Source-located procedure; provider effect remains unqualified.",
                        "status": "ingested",
                        "sources": source_link,
                    },
                    method_chunk,
                ),
                (
                    "mechanism",
                    "ik_mechanism",
                    "mechanism_target_constraint_readability",
                    {
                        "concept_ids": ["c_inverse_kinematics"],
                        "name": "Target-constraint readability",
                        "purpose": "Reduce ambiguity in directed near-contact motion.",
                        "intent_effect": "Make staged near-contact motion more readable and controllable.",
                        "causal_hypothesis": "Explicit targets and bounded constraints reduce the motion solutions a provider may choose.",
                        "causal_chain": ["Declare visible target", "Constrain the path", "Reduce motion ambiguity"],
                        "claim_ids": ["claim_ik_target_constraints"],
                        "method_ids": ["method_bounded_ik"],
                        "equation_ids": ["equation_ik_objective"],
                        "controls": ["motion.target", "motion.constraints", "verification.residual"],
                        "prerequisites": ["Visible target", "Declared coordinate basis"],
                        "conflicts": ["Provider rejects or ignores numeric path controls."],
                        "verification_metrics": [
                            {
                                "metric_id": "metric_target_residual",
                                "observable": "visible target-position residual",
                                "success_condition": "Residual is below the reviewed shot threshold.",
                            }
                        ],
                        "failure_conditions": ["Provider ignores fine spatial controls"],
                        "limitations": ["Mechanism is a directing hypothesis until render evidence qualifies it."],
                        "epistemic_class": "interpreted",
                        "evidence_status": "unverified",
                        "confidence": 0.55,
                        "confidence_basis": "Mechanistic interpretation only; no isolated render evidence.",
                        "status": "ingested",
                        "sources": source_link,
                    },
                    mechanism_chunk,
                ),
                (
                    "claim",
                    "claim_z_duplicate",
                    "claim_ik_target_constraints_duplicate",
                    {
                        "concept_ids": ["c_inverse_kinematics"],
                        "statement": "Inverse kinematics solves joint parameters from target and constraint terms.",
                        "claim_kind": "definition",
                        "method_ids": ["method_bounded_ik"],
                        "supports_claim_ids": [],
                        "contradicts_claim_ids": ["claim_ik_provider_may_ignore_controls"],
                        "epistemic_class": "interpreted",
                        "evidence_status": "supported",
                        "confidence": 0.78,
                        "confidence_basis": "Repeated wording in the same source.",
                        "limitations": ["Provider execution of the solver is not established."],
                        "status": "ingested",
                        "sources": source_link,
                    },
                    duplicate_chunk,
                ),
                (
                    "claim",
                    "claim_contradiction",
                    "claim_ik_provider_may_ignore_controls",
                    {
                        "concept_ids": ["c_provider_behavior"],
                        "statement": "A provider may discard fine-grained numeric controls, so readable motion is not guaranteed.",
                        "claim_kind": "contradiction",
                        "method_ids": [],
                        "supports_claim_ids": [],
                        "contradicts_claim_ids": ["claim_ik_target_constraints"],
                        "epistemic_class": "authored",
                        "evidence_status": "contradicted",
                        "confidence": 0.45,
                        "confidence_basis": "A separately stated source disagreement without provider testing.",
                        "limitations": ["No provider or model version is identified."],
                        "status": "ingested",
                        "sources": source_link,
                    },
                    contradiction_chunk,
                ),
                (
                    "claim",
                    "claim_unverified",
                    "claim_low_residual_guarantees_realism",
                    {
                        "concept_ids": ["c_inverse_kinematics"],
                        "statement": "A low inverse-kinematics residual always guarantees cinematic realism.",
                        "claim_kind": "empirical",
                        "method_ids": [],
                        "supports_claim_ids": [],
                        "contradicts_claim_ids": [],
                        "epistemic_class": "authored",
                        "evidence_status": "unverified",
                        "confidence": 0.1,
                        "confidence_basis": "The source labels no experiment or provider evidence.",
                        "limitations": ["Universal guarantee is unsupported."],
                        "status": "ingested",
                        "sources": source_link,
                    },
                    unverified_chunk,
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
                        "packet_id": packet_id,
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
                            if packet_by_chunk[chunk_id] == packet_id
                        ],
                    }
                    for packet_id in sorted(set(packet_by_chunk.values()))
                    if any(packet_by_chunk[row[4]] == packet_id for row in records)
                ],
            }
            bundle = extract_folder(
                source,
                research_goal="inverse kinematics motion control target constraints",
                rights_basis="owner_authorized_fixture",
                semantic_response=response,
                root=root,
            )
            self.assertEqual(
                canonical_json_bytes(bundle),
                canonical_json_bytes(
                    extract_folder(
                        source,
                        research_goal="inverse kinematics motion control target constraints",
                        rights_basis="owner_authorized_fixture",
                        semantic_response=copy.deepcopy(response),
                        root=root,
                    )
                ),
            )
            kinds = {row["kind"] for row in bundle["chunks"]}
            self.assertTrue({"front_matter", "heading", "table", "equation", "code"} <= kinds)
            self.assertTrue(
                any(
                    row["heading_path"] == [
                        "Inverse kinematics motion control",
                        "Bounded solve method",
                        "Structured control examples",
                    ]
                    for row in bundle["chunks"]
                )
            )
            texts = [row["text"] for row in bundle["chunks"]]
            self.assertIn(
                "$$\nE_{IK}(q) = w_p E_p(q) + w_c E_c(q)\n$$",
                texts,
            )
            for exact in (
                "```yaml\nmotion:\n  target_precision: 0.125\n```",
                '```json\n{"motion": {"constraint_weight": 0.875}}\n```',
                '```xml\n<motion><target precision="0.125" /></motion>\n```',
                "```python\nresidual = position_error + constraint_error\n```",
            ):
                self.assertIn(exact, texts)
            self.assertTrue(
                any("| E_p | visible target-position error |" in text for text in texts)
            )
            self.assertEqual(
                bundle["coverage"]["sections_total"],
                bundle["coverage"]["sections_with_disposition"],
            )
            candidate_by_id = {
                row["suggested_id"]: row
                for row in bundle["distillation_batch"]["candidates"]
                if row["proposal_type"] in {"claim", "equation", "method", "mechanism"}
            }
            for candidate in candidate_by_id.values():
                self.assertEqual(
                    {
                        (row["ref"], row["locator"], row["content_sha256"])
                        for row in candidate["proposed_record"]["sources"]
                    },
                    {
                        (row["source_id"], row["locator"], row["content_sha256"])
                        for row in candidate["source_evidence"]
                    },
                )
            malformed = copy.deepcopy(bundle["distillation_batch"])
            next(
                row for row in malformed["candidates"]
                if row["proposal_type"] == "equation"
            )["proposed_record"].pop("expression")
            with self.assertRaisesRegex(ValidationFailure, "equation:.*expression"):
                run_distillation(malformed, root)
            truth_paths = [root / "lab/concepts.jsonl"] + list(
                (root / "lab/second_brain/curated").glob("*.jsonl")
            ) + list((root / "lab/second_brain/immutable").glob("*.jsonl"))
            truth_before = {str(path): path.read_bytes() for path in truth_paths}
            run = run_distillation(bundle["distillation_batch"], root)
            self.assertEqual(truth_before, {str(path): path.read_bytes() for path in truth_paths})
            self.assertEqual(
                canonical_json_bytes(run),
                canonical_json_bytes(run_distillation(bundle["distillation_batch"], root)),
            )
            typed_decisions = [
                row for row in run["candidate_decisions"]
                if row["proposal_type"] in {"claim", "equation", "method", "mechanism"}
            ]
            decisions_by_id = {row["suggested_id"]: row for row in typed_decisions}
            self.assertEqual(
                decisions_by_id["claim_ik_target_constraints_duplicate"]["disposition"],
                "review_possible_duplicate",
            )
            self.assertEqual(
                decisions_by_id["claim_ik_target_constraints_duplicate"]["dedup_candidates"][0]["id"],
                next(
                    row["candidate_id"]
                    for row in bundle["distillation_batch"]["candidates"]
                    if row["suggested_id"] == "claim_ik_target_constraints"
                ),
            )
            self.assertEqual(
                decisions_by_id["claim_ik_provider_may_ignore_controls"]["disposition"],
                "stage_claim",
            )
            self.assertIn(
                "claim_ik_target_constraints",
                decisions_by_id["claim_ik_provider_may_ignore_controls"]["proposed_record"]["contradicts_claim_ids"],
            )
            staged = [
                row for row in typed_decisions if row["proposal_id"] is not None
            ]
            durable_ids = {
                row["proposal_id"]: row["suggested_id"]
                for row in staged
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
            self.assertNotIn(
                "claim_ik_target_constraints_duplicate", promoted["promoted_ids"]
            )
            promoted_by_id = {row["id"]: row for row in promoted["records"]}
            equation = promoted_by_id["equation_ik_objective"]
            self.assertEqual(
                equation["expression"],
                "E_{IK}(q) = w_p E_p(q) + w_c E_c(q)",
            )
            for record in promoted["records"]:
                provenance = record["provenance"]
                self.assertTrue(provenance["source_evidence"])
                self.assertTrue(provenance["distillation"])
                self.assertEqual(provenance["validation"]["status"], "passed")
                self.assertTrue(provenance["deduplication"]["reviewed"])
                self.assertTrue(provenance["review"]["source_verified"])
            source_ref = promoted_by_id["claim_ik_target_constraints"]["sources"][0]["ref"]
            searches = [
                search_knowledge_objects("solves parameters against target constraints", root=root),
                search_knowledge_objects(object_ids=["claim_ik_target_constraints"], root=root),
                search_knowledge_objects(source_refs=[source_ref], object_types=["claim"], root=root),
                search_knowledge_objects(evidence_classes=["interpreted"], object_types=["claim"], root=root),
                search_knowledge_objects(concept_ids=["c_inverse_kinematics"], object_types=["claim"], root=root),
            ]
            self.assertTrue(
                all(
                    "claim_ik_target_constraints"
                    in {row["object_id"] for row in result["results"]}
                    for result in searches
                )
            )
            equation_search = search_knowledge_objects(
                object_ids=["equation_ik_objective"], root=root
            )
            equation_result = equation_search["results"][0]["record"]
            self.assertEqual(equation_result["solved_quantity"], equation["solved_quantity"])
            self.assertEqual(equation_result["terms"], equation["terms"])
            self.assertEqual(equation_result["variables"], equation["variables"])
            self.assertEqual(equation_result["assumptions"], equation["assumptions"])
            self.assertEqual(equation_result["method_ids"], ["method_bounded_ik"])
            method_result = search_knowledge_objects(
                object_ids=["method_bounded_ik"], root=root
            )["results"][0]["record"]
            for field in (
                "purpose", "inputs", "outputs", "assumptions", "applicability",
                "limitations", "sources",
            ):
                self.assertTrue(method_result[field])
            mechanism_result = search_knowledge_objects(
                object_ids=["mechanism_target_constraint_readability"], root=root
            )["results"][0]["record"]
            for field in (
                "purpose", "causal_hypothesis", "prerequisites", "conflicts",
                "controls", "verification_metrics", "confidence_basis", "sources",
            ):
                self.assertTrue(mechanism_result[field])
            cross = search_knowledge_objects(
                "solves parameters target constraint",
                object_ids=["claim_ik_target_constraints"],
                maximum_hops=5,
                root=root,
            )
            self.assertTrue(
                any(
                    path["nodes"] == [
                        "claim_ik_target_constraints",
                        "method_bounded_ik",
                        "equation_ik_objective",
                        "mechanism_target_constraint_readability",
                        "control:motion.target",
                    ]
                    for path in cross["selected_paths"]
                )
            )
            self.assertNotIn(
                "catering",
                canonical_json_bytes(cross).decode("utf-8").lower(),
            )
            self.assertTrue(
                all(row["trust_class"] == "curated_repository_authority" for row in cross["results"])
            )
            self.assertTrue(
                any(
                    row["to"] == "claim_ik_provider_may_ignore_controls"
                    and row["reason"] == "no_shared_concept_or_query_support"
                    for row in cross["rejected_paths"]
                )
            )
            catalog = build_index_catalog(root)
            self.assertIn("claim_ik_target_constraints", catalog["knowledge_object_links"])
            self.assertIn(
                "claim_ik_target_constraints",
                catalog["knowledge_object_lexical"]["parameters"],
            )
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
