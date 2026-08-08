"""Select and execute bounded reasoning policies over one CPCS context bundle.

The execution trace records deterministic operations and evidence IDs. It never asks for,
stores, or exposes a model's private chain-of-thought.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .authority import authority_reader
from .intent import build_intent_context
from .temporal import is_visible
from .terminology import validate_terminology_handoff
from .validate import REPO_ROOT, read_jsonl, sha256_value, validate_instance
from .video_reasoning import validate_knowledge_comparison_lens


REASONING_POLICY_VERSION = "cpcs-reasoning-policy/1.0"
EXECUTOR_REGISTRY_VERSION = "cpcs-reasoning-executors/1.0"
STRATEGY_SCHEMA = "cpcs.compiled_directing_strategy/1.0"
STATUS_RANK = {"ingested": 0, "partial": 1, "proven": 2, "deprecated": -1}


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _selected_concepts(context: dict[str, Any]) -> list[dict[str, Any]]:
    return list(context.get("selected_concepts", []))


def _available_inputs(
    normalized: dict[str, Any], context: dict[str, Any]
) -> dict[str, bool]:
    text = normalized["request"]["original_text"].lower()
    profiles = [
        normalized["profiles"]["primary"],
        *normalized["profiles"].get("secondary", []),
    ]
    numeric_tokens = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    numeric_control = bool(
        re.search(r"\b(?:fps|frames?|seconds?|duration|budget|ratio|calculate)\b", text)
        or re.search(r"\b\d+\s*:\s*\d+\b", text)
    )
    ambiguity = bool(
        normalized.get("uncertainties")
        or normalized["requirements"].get("missing_inputs")
        or normalized.get("conflicts")
    )
    return {
        "normalized_intent": True,
        "retrieved_evidence": bool(
            _selected_concepts(context)
            or context.get("knowledge_objects")
            or context.get("external_evidence")
        ),
        "numeric_constraints": bool(numeric_tokens and numeric_control),
        "multiple_domains": len(_unique(profiles)) > 1,
        "unresolved_ambiguity": ambiguity,
    }


def classify_task(
    normalized: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    """Classify the execution need without creating directing knowledge."""
    validate_instance("normalized_intent", normalized)
    validate_instance("context_bundle", context)
    text = normalized["request"]["original_text"].lower()
    available = _available_inputs(normalized, context)
    matches = {
        "research_distillation": sorted(
            set(re.findall(r"\b(?:distill|extract|ingest|paper|research source)\b", text))
        ),
        "deterministic_calculation": sorted(
            set(
                re.findall(
                    r"\b(?:aspect ratio|budget|calculate|duration|fps|frames?|seconds?)\b|\b\d+\s*:\s*\d+\b",
                    text,
                )
            )
        ),
        "creative_alternatives": sorted(
            set(re.findall(r"\b(?:alternatives?|angles?|options?|styles?|variants?)\b", text))
        ),
        "cross_domain_synthesis": sorted(
            set(re.findall(r"\b(?:combine|cross-domain|merge|synthesize|synergy)\b", text))
        ),
        "ambiguous_discovery": sorted(
            set(re.findall(r"\b(?:ambiguous|discover|explore|search|backtrack|not sure)\b", text))
        ),
    }
    if matches["research_distillation"]:
        task_class = "research_distillation"
    elif available["numeric_constraints"] and len(matches["deterministic_calculation"]) >= 2:
        task_class = "deterministic_calculation"
    elif matches["creative_alternatives"]:
        task_class = "creative_alternatives"
    elif matches["cross_domain_synthesis"] or available["multiple_domains"]:
        task_class = "cross_domain_synthesis"
    elif matches["ambiguous_discovery"] or not available["retrieved_evidence"]:
        task_class = "ambiguous_discovery"
    else:
        task_class = "direct"
    return {
        "policy_version": REASONING_POLICY_VERSION,
        "primary_task_class": task_class,
        "matched_signals": matches,
        "available_inputs": available,
    }


@authority_reader("reasoning_policy_snapshot")
def load_reasoning_policies(
    root: Path = REPO_ROOT,
    *,
    minimum_status: str = "partial",
) -> list[dict[str, Any]]:
    if minimum_status not in {"ingested", "partial", "proven"}:
        raise ValueError("minimum_status must be ingested, partial, or proven")
    path = root / "lab" / "second_brain" / "curated" / "reasoning_policies.jsonl"
    records = read_jsonl(path)
    policy_ids: set[str] = set()
    visible: list[dict[str, Any]] = []
    for record in records:
        validate_instance("reasoning_policy", record, root)
        if record["id"] != record["policy_id"]:
            raise ValueError(f"reasoning policy id mismatch: {record['id']}")
        if record["id"] in policy_ids:
            raise ValueError(f"duplicate reasoning policy: {record['id']}")
        policy_ids.add(record["id"])
        if record["executor"] not in EXECUTOR_REGISTRY:
            raise ValueError(f"reasoning policy uses unknown executor: {record['id']}")
        if (
            is_visible(record, "current", None)
            and record["status"] != "deprecated"
            and STATUS_RANK[record["status"]] >= STATUS_RANK[minimum_status]
        ):
            visible.append(record)
    return sorted(visible, key=lambda row: (-row["priority"], row["id"]))


def select_policy(
    normalized: dict[str, Any],
    context: dict[str, Any],
    *,
    requested_policy_id: str | None = None,
    root: Path = REPO_ROOT,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    classification = classify_task(normalized, context)
    policies = load_reasoning_policies(root)
    if not policies and root.resolve() != REPO_ROOT.resolve():
        policies = [
            row
            for row in load_reasoning_policies(REPO_ROOT)
            if row["id"] == "rp_direct"
        ]
    if not policies:
        raise ValueError("no governed reasoning policy is available")
    by_id = {row["id"]: row for row in policies}
    if requested_policy_id is not None:
        if requested_policy_id not in by_id:
            raise ValueError(
                f"requested reasoning policy is unavailable at partial status: {requested_policy_id}"
            )
        selected = by_id[requested_policy_id]
    else:
        task_class = classification["primary_task_class"]
        eligible = [
            row
            for row in policies
            if task_class in row["task_classes"]
            and all(
                classification["available_inputs"].get(requirement, False)
                for requirement in row["requires"]
            )
        ]
        selected = eligible[0] if eligible else by_id["rp_direct"]
    alternatives = [
        row["id"]
        for row in policies
        if row["id"] != selected["id"]
        and classification["primary_task_class"] in row["task_classes"]
    ]
    return selected, classification, alternatives


def _base_candidate(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "concept_ids": [row["id"] for row in _selected_concepts(context)],
        "knowledge_object_ids": [
            row["object_id"] for row in context.get("knowledge_objects", [])
        ],
        "mapping_ids": [row["id"] for row in context.get("mappings", [])],
        "uncovered_terms": context["knowledge_gap"].get("uncovered_terms", []),
    }


def _trace(
    step: int,
    operation: str,
    *,
    input_ids: Iterable[str] = (),
    output_ids: Iterable[str] = (),
    disposition: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "step": step,
        "operation": operation,
        "input_ids": _unique(input_ids),
        "output_ids": _unique(output_ids),
        "disposition": disposition,
        "details": details or {},
    }


class DirectExecutor:
    name = "direct"

    def execute(
        self, policy: dict[str, Any], normalized: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        candidate = _base_candidate(context)
        concept_ids = candidate["concept_ids"]
        return {
            "executor": self.name,
            "operations": ["select_retrieved_controls"],
            "reasoning_trace": [
                _trace(
                    1,
                    "select_retrieved_controls",
                    input_ids=concept_ids,
                    output_ids=concept_ids,
                    disposition="selected",
                    details={"selection_order": "cpcs.reason relevance order"},
                )
            ],
            "candidate_strategy": candidate,
            "strategy_alternatives": [],
            "calculations": [],
        }


class AoTExecutor:
    name = "algorithm_of_thoughts"

    def execute(
        self, policy: dict[str, Any], normalized: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        paths_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for path in context.get("typed_paths", []):
            paths_by_family[str(path.get("family") or "root")].append(path)
        branches = []
        trace = []
        for index, (family, paths) in enumerate(
            sorted(paths_by_family.items())[: policy["max_branches"]], 1
        ):
            outputs = _unique(path["to"] for path in paths)
            branches.append({"branch": family, "concept_ids": outputs})
            trace.append(
                _trace(
                    index,
                    "inspect_branch",
                    input_ids=_unique(path["from"] for path in paths),
                    output_ids=outputs,
                    disposition="retained",
                    details={"family": family, "path_count": len(paths)},
                )
            )
        if not trace:
            concept_ids = [row["id"] for row in _selected_concepts(context)]
            trace.append(
                _trace(
                    1,
                    "inspect_roots",
                    input_ids=concept_ids,
                    output_ids=concept_ids,
                    disposition="retained",
                    details={"reason": "no traversed branch was admitted"},
                )
            )
        candidate = _base_candidate(context)
        candidate["branches"] = branches
        return {
            "executor": self.name,
            "operations": ["inspect_branch", "prune_unrelated", "select_retrieved_controls"],
            "reasoning_trace": trace[: policy["max_steps"]],
            "candidate_strategy": candidate,
            "strategy_alternatives": branches,
            "calculations": [],
        }


class AtomExecutor:
    name = "atom_of_thoughts"

    def execute(
        self, policy: dict[str, Any], normalized: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        atoms: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        records = [
            (row["id"], "concept", row.get("covered_terms", []))
            for row in _selected_concepts(context)
        ] + [
            (row["object_id"], row["object_type"], row.get("concept_ids", []))
            for row in context.get("knowledge_objects", [])
        ]
        for index, (record_id, kind, dependencies) in enumerate(
            records[: policy["max_steps"]], 1
        ):
            atom = {
                "atom_id": f"atom_{index:03d}",
                "source_id": record_id,
                "kind": kind,
                "dependencies": _unique(dependencies),
            }
            atoms.append(atom)
            trace.append(
                _trace(
                    index,
                    "contract_evidence_atom",
                    input_ids=[record_id],
                    output_ids=[atom["atom_id"]],
                    disposition="contracted",
                    details={"source_kind": kind, "lineage_preserved": True},
                )
            )
        candidate = _base_candidate(context)
        candidate["atoms"] = atoms
        return {
            "executor": self.name,
            "operations": ["contract_evidence_atom", "assemble_atomic_state"],
            "reasoning_trace": trace,
            "candidate_strategy": candidate,
            "strategy_alternatives": [],
            "calculations": [],
        }


class CodeExecutor:
    name = "chain_of_code"

    @staticmethod
    def _calculations(text: str) -> list[dict[str, Any]]:
        calculations: list[dict[str, Any]] = []
        ratio = re.search(r"\b(\d+)\s*:\s*(\d+)\b", text)
        if ratio:
            width, height = int(ratio.group(1)), int(ratio.group(2))
            if height:
                calculations.append(
                    {
                        "operation": "aspect_ratio_decimal",
                        "inputs": {"width": width, "height": height},
                        "result": round(width / height, 8),
                    }
                )
        seconds = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)\b", text)
        fps = re.search(r"\b(\d+(?:\.\d+)?)\s*fps\b", text)
        if seconds and fps:
            duration = float(seconds.group(1))
            frame_rate = float(fps.group(1))
            calculations.append(
                {
                    "operation": "frame_count",
                    "inputs": {"duration_seconds": duration, "fps": frame_rate},
                    "result": round(duration * frame_rate, 8),
                }
            )
        return calculations

    def execute(
        self, policy: dict[str, Any], normalized: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        calculations = self._calculations(normalized["request"]["original_text"].lower())
        trace = [
            _trace(
                index,
                row["operation"],
                output_ids=[f"calculation_{index:03d}"],
                disposition="calculated",
                details={"inputs": row["inputs"], "result": row["result"]},
            )
            for index, row in enumerate(calculations[: policy["max_steps"]], 1)
        ]
        if not trace:
            trace = [
                _trace(
                    1,
                    "calculation_preflight",
                    disposition="retained",
                    details={"missing_operands": True, "arbitrary_code_execution": False},
                )
            ]
        candidate = _base_candidate(context)
        candidate["calculation_ids"] = [
            f"calculation_{index:03d}" for index in range(1, len(calculations) + 1)
        ]
        return {
            "executor": self.name,
            "operations": ["calculation_preflight", "fixed_numeric_calculation"],
            "reasoning_trace": trace,
            "candidate_strategy": candidate,
            "strategy_alternatives": [],
            "calculations": calculations,
        }


class ToTExecutor:
    name = "tree_of_thoughts"

    def execute(
        self, policy: dict[str, Any], normalized: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        by_layer: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in _selected_concepts(context):
            by_layer[str(row.get("layer") or "unclassified")].append(row)
        alternatives = []
        trace = []
        for index, (layer, records) in enumerate(
            sorted(by_layer.items())[: policy["max_branches"]], 1
        ):
            ids = [row["id"] for row in records]
            score = round(
                sum(len(row.get("covered_terms", [])) + 1 / (1 + row.get("depth", 0)) for row in records),
                8,
            )
            alternative = {
                "alternative_id": f"alternative_{index:03d}",
                "layer": layer,
                "concept_ids": ids,
                "retrieval_score": score,
            }
            alternatives.append(alternative)
            trace.append(
                _trace(
                    index,
                    "rank_retrieved_branch",
                    input_ids=ids,
                    output_ids=[alternative["alternative_id"]],
                    disposition="ranked",
                    details={"layer": layer, "retrieval_score": score},
                )
            )
        alternatives.sort(key=lambda row: (-row["retrieval_score"], row["alternative_id"]))
        candidate = _base_candidate(context)
        candidate["preferred_alternative"] = (
            alternatives[0]["alternative_id"] if alternatives else None
        )
        return {
            "executor": self.name,
            "operations": ["group_retrieved_branches", "rank_retrieved_branch"],
            "reasoning_trace": trace[: policy["max_steps"]],
            "candidate_strategy": candidate,
            "strategy_alternatives": alternatives,
            "calculations": [],
        }


class GoTExecutor:
    name = "graph_of_thoughts"

    def execute(
        self, policy: dict[str, Any], normalized: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        incoming: dict[str, set[str]] = defaultdict(set)
        for path in context.get("typed_paths", []):
            incoming[path["to"]].add(path["from"])
        by_layer: dict[str, list[str]] = defaultdict(list)
        for row in _selected_concepts(context):
            by_layer[str(row.get("layer") or "unclassified")].append(row["id"])
        clusters = []
        trace = []
        for index, (layer, concept_ids) in enumerate(
            sorted(by_layer.items())[: policy["max_branches"]], 1
        ):
            cluster_id = f"aggregate_{index:03d}"
            source_ids = _unique(
                source
                for concept_id in concept_ids
                for source in sorted(incoming.get(concept_id, set()))
            )
            cluster = {
                "aggregate_id": cluster_id,
                "layer": layer,
                "concept_ids": concept_ids,
                "incoming_concept_ids": source_ids,
            }
            clusters.append(cluster)
            trace.append(
                _trace(
                    index,
                    "aggregate_retrieved_concepts",
                    input_ids=_unique([*source_ids, *concept_ids]),
                    output_ids=[cluster_id],
                    disposition="aggregated",
                    details={"layer": layer, "source_count": len(source_ids)},
                )
            )
        candidate = _base_candidate(context)
        candidate["aggregates"] = clusters
        return {
            "executor": self.name,
            "operations": ["group_by_control_layer", "aggregate_retrieved_concepts"],
            "reasoning_trace": trace[: policy["max_steps"]],
            "candidate_strategy": candidate,
            "strategy_alternatives": clusters,
            "calculations": [],
        }


EXECUTOR_REGISTRY = {
    "direct": DirectExecutor,
    "algorithm_of_thoughts": AoTExecutor,
    "atom_of_thoughts": AtomExecutor,
    "chain_of_code": CodeExecutor,
    "tree_of_thoughts": ToTExecutor,
    "graph_of_thoughts": GoTExecutor,
}


def _knowledge_summary(
    context: dict[str, Any], policy: dict[str, Any]
) -> dict[str, Any]:
    curated = context.get("curated_evidence", [])
    external = context.get("external_evidence", [])
    source_refs = [row["reference"] for row in curated]
    source_refs.extend(
        f"{row['source_id']}#{row['locator']}" for row in external
    )
    source_refs.extend(policy["source_refs"])
    return {
        "concept_ids": _unique(row["id"] for row in _selected_concepts(context)),
        "knowledge_object_ids": _unique(
            row["object_id"] for row in context.get("knowledge_objects", [])
        ),
        "mapping_ids": _unique(row["id"] for row in context.get("mappings", [])),
        "evidence_ids": _unique(
            [row["id"] for row in curated]
            + [row["content_hash"] for row in external]
        ),
        "source_refs": _unique(source_refs),
        "knowledge_gap": context["knowledge_gap"],
        "conflicts": context.get("conflicts", []),
    }


def _directing_strategy(
    normalized: dict[str, Any], context: dict[str, Any], execution: dict[str, Any]
) -> dict[str, Any]:
    profiles = _unique(
        [normalized["profiles"]["primary"], *normalized["profiles"].get("secondary", [])]
    )
    concepts = _selected_concepts(context)
    priorities = _unique(
        [row["id"] for row in concepts]
        or [normalized["intent"]["task"]]
    )
    control_candidates = [
        {
            "mapping_id": row["id"],
            "concept_id": row["concept_id"],
            "target_type": row["target_type"],
            "target_id": row["target_id"],
            "encoding": row["encoding"],
            "mapping": row["mapping"],
            "loss": row["loss"],
        }
        for row in context.get("mappings", [])
    ]
    verification_focus = _unique(
        [row["target_id"] for row in control_candidates]
        + context["knowledge_gap"].get("uncovered_terms", [])
    )
    return {
        "task": normalized["intent"]["task"],
        "audience_effect": normalized["intent"]["audience_effect"],
        "profiles": profiles,
        "priorities": priorities,
        "control_candidates": control_candidates,
        "hard_constraints": normalized["requirements"]["hard_constraints"],
        "soft_preferences": normalized["requirements"]["soft_preferences"],
        "continuity_locks": normalized["requirements"]["continuity_locks"],
        "conflicts": [*normalized.get("conflicts", []), *context.get("conflicts", [])],
        "uncertainties": normalized.get("uncertainties", []),
        "verification_focus": verification_focus,
    }


def _knowledge_lens_trace(
    lens: dict[str, Any], context: dict[str, Any], knowledge: dict[str, Any]
) -> dict[str, Any]:
    return {
        "lens_hash": lens["lens_hash"],
        "authority_snapshot_hash": lens["authority_snapshot_hash"],
        "context_bundle_hash": lens["context_bundle_hash"],
        "query": lens["query"],
        "reference_vog": copy.deepcopy(lens["reference"]["vog"]),
        "candidate_vog": copy.deepcopy(lens["candidate"]["vog"]),
        "reviewed_bridge_ids": _unique(
            [
                *lens["reference"]["reviewed_bridge_ids"],
                *lens["candidate"]["reviewed_bridge_ids"],
            ]
        ),
        "concept_ids": _unique(row["id"] for row in _selected_concepts(context)),
        "mapping_ids": _unique(row["id"] for row in context.get("mappings", [])),
        "knowledge_object_ids": _unique(
            row["object_id"] for row in context.get("knowledge_objects", [])
        ),
        "source_refs": list(knowledge["source_refs"]),
    }


@authority_reader("compiled_directing_strategy")
def compile_directing_strategy(
    intent_context: dict[str, Any],
    *,
    requested_policy_id: str | None = None,
    knowledge_lens: dict[str, Any] | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    if set(intent_context) != {"normalized_intent", "context_bundle"}:
        raise ValueError(
            "intent_context must contain exactly normalized_intent and context_bundle"
        )
    normalized = intent_context["normalized_intent"]
    context = intent_context["context_bundle"]
    validate_instance("normalized_intent", normalized, root)
    validate_instance("context_bundle", context, root)
    validate_terminology_handoff(
        context["request"]["query"],
        context["request"]["domain"],
        context["terminology"],
        root,
        require_resolved=True,
    )
    lens = None
    if knowledge_lens is not None:
        lens = validate_knowledge_comparison_lens(
            knowledge_lens, root, require_compilable=True
        )
        unbound_context = copy.deepcopy(context)
        unbound_context["request"]["intent"] = None
        if sha256_value(unbound_context) != lens["context_bundle_hash"]:
            raise ValueError(
                "directing strategy context does not match the knowledge lens snapshot"
            )
    policy, classification, alternatives = select_policy(
        normalized,
        context,
        requested_policy_id=requested_policy_id,
        root=root,
    )
    executor = EXECUTOR_REGISTRY[policy["executor"]]()
    execution = executor.execute(policy, normalized, context)
    intent_hash = sha256_value(normalized)
    context_hash = sha256_value(context)
    policy_hash = sha256_value(policy)
    graph_backend = "cpcs.reason/configured_backend"
    knowledge = _knowledge_summary(context, policy)
    value = {
        "schema": STRATEGY_SCHEMA,
        "request": {
            "original_text": normalized["request"]["original_text"],
            "normalized_intent_hash": intent_hash,
            "context_hash": context_hash,
        },
        "policy_selection": {
            "policy_id": policy["id"],
            "policy_hash": policy_hash,
            "policy_version": REASONING_POLICY_VERSION,
            "task_class": classification["primary_task_class"],
            "executor": policy["executor"],
            "classification": classification,
            "alternatives": alternatives,
        },
        "knowledge": knowledge,
        "execution": execution,
        "directing_strategy": _directing_strategy(normalized, context, execution),
        "provenance": {
            "intent_hash": intent_hash,
            "context_hash": context_hash,
            "query_policy": context["policy_versions"]["query"],
            "graph_backend": graph_backend,
            "policy_hash": policy_hash,
            "executor_registry": EXECUTOR_REGISTRY_VERSION,
        },
        "trust_boundary": {
            "curated": "repository_authority",
            "immutable": "append_only_evidence",
            "derived": "rebuildable_non_authoritative",
            "execution": "ephemeral_deterministic_proposal",
        },
    }
    if lens is not None:
        value["knowledge_lens"] = _knowledge_lens_trace(lens, context, knowledge)
        value["provenance"]["knowledge_lens_hash"] = lens["lens_hash"]
    value["strategy_id"] = "strategy_" + sha256_value(value).removeprefix("sha256:")[:32]
    validate_instance("compiled_directing_strategy", value, root)
    return value


def compile_from_text(
    text: str,
    *,
    user_constraints: Iterable[str] | None = None,
    profile_overrides: Iterable[str] | None = None,
    token_budget: int = 12_000,
    minimum_status: str = "partial",
    target_format: str = "hybrid",
    requested_policy_id: str | None = None,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    intent_context = build_intent_context(
        text,
        user_constraints=user_constraints,
        profile_overrides=profile_overrides,
        token_budget=token_budget,
        minimum_status=minimum_status,
        target_format=target_format,
        root=root,
    )
    return compile_directing_strategy(
        intent_context,
        requested_policy_id=requested_policy_id,
        root=root,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text")
    parser.add_argument("--policy-id")
    parser.add_argument(
        "--minimum-status",
        choices=("ingested", "partial", "proven"),
        default="partial",
    )
    parser.add_argument(
        "--target-format",
        choices=("prose", "natural_language", "yaml", "json", "xml", "hybrid"),
        default="hybrid",
    )
    args = parser.parse_args(argv)
    result = compile_from_text(
        args.text,
        requested_policy_id=args.policy_id,
        minimum_status=args.minimum_status,
        target_format=args.target_format,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
