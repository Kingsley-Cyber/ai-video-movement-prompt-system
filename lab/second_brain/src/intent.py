"""Normalize ordinary video requests and route them into read-only CPCS context."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

import yaml

from .context import build_context_bundle
from .query import QUERY_POLICY
from .validate import REPO_ROOT, canonical_json_bytes, validate_instance
from .video_reasoning import validate_knowledge_comparison_lens

NormalizedIntent = dict[str, Any]
IntentContext = dict[str, Any]

POLICY_PATH = Path("lab/profiles/intent_routing.yaml")
POLICY_SCHEMA = "cpcs.intent_profile_policy/1.0"
NORMALIZED_SCHEMA = "cpcs.normalized_intent/1.0"


def _non_empty_strings(name: str, values: Iterable[str] | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{name} must be an iterable of strings, not one string")
    normalized: set[str] = set()
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name}[{index}] must be a non-empty string")
        normalized.add(value.strip())
    return sorted(normalized)


def _ordered_non_empty_strings(
    name: str, values: Iterable[str] | None
) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{name} must be an iterable of strings, not one string")
    normalized: list[str] = []
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name}[{index}] must be a non-empty string")
        item = value.strip()
        if item not in normalized:
            normalized.append(item)
    return normalized


def _phrase_present(text: str, phrase: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(phrase.lower()).replace(r"\ ", r"\s+")
    pattern += r"(?![a-z0-9])"
    return re.search(pattern, text.lower()) is not None


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _validate_policy(policy: Any) -> dict[str, Any]:
    if not isinstance(policy, dict):
        raise ValueError("intent profile policy must be an object")
    allowed_policy_fields = {
        "schema",
        "configuration_kind",
        "kernel_contract",
        "policy_version",
        "selection",
        "profiles",
        "task_rules",
        "preference_signals",
        "conflicts",
    }
    unexpected = set(policy) - allowed_policy_fields
    if unexpected:
        raise ValueError(
            "intent profile policy has unsupported fields: "
            + ", ".join(sorted(unexpected))
        )
    if policy.get("schema") != POLICY_SCHEMA:
        raise ValueError(f"intent profile policy schema must be {POLICY_SCHEMA}")
    if policy.get("configuration_kind") != "intent_routing_only":
        raise ValueError("intent profile policy may only configure intent routing")
    if policy.get("kernel_contract") != "cpcs.video_kernel/1.0":
        raise ValueError("intent profile policy must target the universal video kernel")
    _require_string(policy.get("policy_version"), "policy_version")

    selection = policy.get("selection")
    if not isinstance(selection, dict):
        raise ValueError("selection must be an object")
    unexpected = set(selection) - {
        "minimum_score",
        "maximum_secondary",
        "maximum_alternatives",
    }
    if unexpected:
        raise ValueError(
            "selection has unsupported fields: " + ", ".join(sorted(unexpected))
        )
    for key in ("minimum_score", "maximum_secondary", "maximum_alternatives"):
        value = selection.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"selection.{key} must be a non-negative integer")

    profiles = policy.get("profiles")
    if not isinstance(profiles, dict) or "general_video" not in profiles:
        raise ValueError("profiles must contain general_video")
    for profile_id, profile in profiles.items():
        _require_string(profile_id, "profile id")
        if not isinstance(profile, dict):
            raise ValueError(f"profiles.{profile_id} must be an object")
        unexpected = set(profile) - {
            "priority",
            "domain",
            "task",
            "audience_effect",
            "signals",
            "required_layers",
            "excluded_layers",
            "knowledge_terms",
            "missing_inputs",
        }
        if unexpected:
            raise ValueError(
                f"profiles.{profile_id} has unsupported fields: "
                + ", ".join(sorted(unexpected))
            )
        priority = profile.get("priority")
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise ValueError(f"profiles.{profile_id}.priority must be an integer")
        for key in ("domain", "task", "audience_effect"):
            _require_string(profile.get(key), f"profiles.{profile_id}.{key}")
        signals = profile.get("signals")
        if not isinstance(signals, dict):
            raise ValueError(f"profiles.{profile_id}.signals must be an object")
        for phrase, weight in signals.items():
            _require_string(phrase, f"profiles.{profile_id}.signals key")
            if isinstance(weight, bool) or not isinstance(weight, int) or weight <= 0:
                raise ValueError(
                    f"profiles.{profile_id}.signals.{phrase} must be a positive integer"
                )
        for key in (
            "required_layers",
            "excluded_layers",
            "knowledge_terms",
            "missing_inputs",
        ):
            _non_empty_strings(f"profiles.{profile_id}.{key}", profile.get(key))

    for index, rule in enumerate(policy.get("task_rules", [])):
        if not isinstance(rule, dict):
            raise ValueError(f"task_rules[{index}] must be an object")
        unexpected = set(rule) - {
            "id",
            "requires_profiles",
            "requires_any_signal",
            "task",
            "audience_effect",
        }
        if unexpected:
            raise ValueError(
                f"task_rules[{index}] has unsupported fields: "
                + ", ".join(sorted(unexpected))
            )
        _require_string(rule.get("id"), f"task_rules[{index}].id")
        _require_string(rule.get("task"), f"task_rules[{index}].task")
        _require_string(
            rule.get("audience_effect"), f"task_rules[{index}].audience_effect"
        )
        required = _non_empty_strings(
            f"task_rules[{index}].requires_profiles",
            rule.get("requires_profiles"),
        )
        unknown = set(required) - set(profiles)
        if unknown:
            raise ValueError(
                f"task_rules[{index}] references unknown profiles: {sorted(unknown)}"
            )
        _non_empty_strings(
            f"task_rules[{index}].requires_any_signal",
            rule.get("requires_any_signal"),
        )

    preferences = policy.get("preference_signals", {})
    if not isinstance(preferences, dict):
        raise ValueError("preference_signals must be an object")
    for signal, preference in preferences.items():
        _require_string(signal, "preference signal")
        _require_string(preference, f"preference_signals.{signal}")

    for index, conflict in enumerate(policy.get("conflicts", [])):
        if not isinstance(conflict, dict):
            raise ValueError(f"conflicts[{index}] must be an object")
        unexpected = set(conflict) - {
            "id",
            "profiles",
            "field",
            "options",
            "disposition",
            "selected",
            "reason",
        }
        if unexpected:
            raise ValueError(
                f"conflicts[{index}] has unsupported fields: "
                + ", ".join(sorted(unexpected))
            )
        for key in ("id", "field", "disposition", "reason"):
            _require_string(conflict.get(key), f"conflicts[{index}].{key}")
        conflict_profiles = _non_empty_strings(
            f"conflicts[{index}].profiles", conflict.get("profiles")
        )
        if len(conflict_profiles) < 2:
            raise ValueError(f"conflicts[{index}].profiles must contain two profiles")
        unknown = set(conflict_profiles) - set(profiles)
        if unknown:
            raise ValueError(
                f"conflicts[{index}] references unknown profiles: {sorted(unknown)}"
            )
        if len(_non_empty_strings(f"conflicts[{index}].options", conflict.get("options"))) < 2:
            raise ValueError(f"conflicts[{index}].options must contain two options")
        selected = conflict.get("selected")
        if selected is not None:
            _require_string(selected, f"conflicts[{index}].selected")
    return policy


def load_profile_policy(root: Path = REPO_ROOT) -> dict[str, Any]:
    """Load and semantically validate the router-only profile configuration."""
    path = root / POLICY_PATH
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot load intent profile policy: {exc}") from exc
    return _validate_policy(value)


def _score_profiles(text: str, policy: dict[str, Any]) -> dict[str, int]:
    scores: dict[str, int] = {}
    for profile_id, profile in policy["profiles"].items():
        score = sum(
            weight
            for phrase, weight in profile["signals"].items()
            if _phrase_present(text, phrase)
        )
        if score:
            scores[profile_id] = score
    return scores


def _ranked_profiles(
    scores: dict[str, int], policy: dict[str, Any]
) -> list[str]:
    return sorted(
        scores,
        key=lambda profile_id: (
            -scores[profile_id],
            policy["profiles"][profile_id]["priority"],
            profile_id,
        ),
    )


def _select_profiles(
    scores: dict[str, int],
    overrides: list[str],
    policy: dict[str, Any],
) -> tuple[str, list[str], list[str], str]:
    known = set(policy["profiles"])
    unknown = set(overrides) - known
    if unknown:
        raise ValueError("unknown profile override(s): " + ", ".join(sorted(unknown)))

    ranked = _ranked_profiles(scores, policy)
    minimum_score = policy["selection"]["minimum_score"]
    admitted = [profile_id for profile_id in ranked if scores[profile_id] >= minimum_score]
    max_secondary = policy["selection"]["maximum_secondary"]
    max_alternatives = policy["selection"]["maximum_alternatives"]

    if overrides:
        primary = overrides[0]
        secondary_pool = [*overrides[1:], *admitted]
        source = "user_override"
    elif admitted:
        primary = admitted[0]
        secondary_pool = admitted[1:]
        source = "automatic"
    else:
        primary = "general_video"
        secondary_pool = []
        source = "automatic"

    secondary: list[str] = []
    if max_secondary:
        for profile_id in secondary_pool:
            if profile_id != primary and profile_id not in secondary:
                secondary.append(profile_id)
            if len(secondary) == max_secondary:
                break

    selected = {primary, *secondary}
    alternatives = [profile_id for profile_id in ranked if profile_id not in selected]
    if primary == "general_video":
        alternatives.extend(
            profile_id
            for profile_id in sorted(
                known - {"general_video"},
                key=lambda item: (policy["profiles"][item]["priority"], item),
            )
            if profile_id not in alternatives
        )
    return primary, secondary, alternatives[:max_alternatives], source


def _selection_confidence(
    primary: str,
    scores: dict[str, int],
    source: str,
    policy: dict[str, Any],
) -> float:
    if source == "user_override":
        return 1.0
    if primary == "general_video" or primary not in scores:
        return 0.0
    ranked = _ranked_profiles(scores, policy)
    runner_up = next((scores[item] for item in ranked if item != primary), 0)
    denominator = scores[primary] + runner_up
    return round(scores[primary] / denominator, 6) if denominator else 0.0


def _task_and_effect(
    text: str,
    selected: list[str],
    primary: str,
    policy: dict[str, Any],
) -> tuple[str, str]:
    selected_set = set(selected)
    for rule in policy.get("task_rules", []):
        if not set(rule["requires_profiles"]) <= selected_set:
            continue
        if not any(
            _phrase_present(text, signal)
            for signal in rule["requires_any_signal"]
        ):
            continue
        return rule["task"], rule["audience_effect"]
    profile = policy["profiles"][primary]
    return profile["task"], profile["audience_effect"]


def _workflow_hint(text: str, constraints: list[str]) -> str | None:
    combined = " ".join([text, *constraints])
    if any(_phrase_present(combined, phrase) for phrase in ("reference video", "video to video")):
        return "video_to_video"
    if any(_phrase_present(combined, phrase) for phrase in ("reference image", "image to video")):
        return "image_to_video"
    if _phrase_present(combined, "text to video"):
        return "text_to_video"
    return None


def _requirements(
    text: str,
    constraints: list[str],
    selected: list[str],
    policy: dict[str, Any],
) -> dict[str, list[str]]:
    hard: set[str] = set()
    locks: set[str] = set()
    provided_inputs: set[str] = set()
    for constraint in constraints:
        prefix, separator, remainder = constraint.partition(":")
        normalized_prefix = prefix.strip().lower()
        if separator and normalized_prefix == "lock":
            locks.add(_require_string(remainder, "lock constraint"))
        elif separator and normalized_prefix == "input":
            provided_inputs.add(_require_string(remainder, "input constraint"))
        elif separator and normalized_prefix == "must":
            hard.add(_require_string(remainder, "must constraint"))
        else:
            hard.add(constraint)

    preferences = {
        normalized
        for signal, normalized in policy.get("preference_signals", {}).items()
        if _phrase_present(text, signal)
    }
    missing = {
        item
        for profile_id in selected
        for item in policy["profiles"][profile_id]["missing_inputs"]
        if item not in provided_inputs
    }
    return {
        "hard_constraints": sorted(hard),
        "soft_preferences": sorted(preferences),
        "continuity_locks": sorted(locks),
        "missing_inputs": sorted(missing),
    }


def _routing(
    text: str,
    selected: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    knowledge_terms: list[str] = []
    for profile_id in selected:
        for term in policy["profiles"][profile_id]["knowledge_terms"]:
            if term not in knowledge_terms:
                knowledge_terms.append(term)
    suffix = " ".join(knowledge_terms)
    query = re.sub(r"\s+", " ", f"{text} {suffix}").strip()
    required = sorted(
        {
            layer
            for profile_id in selected
            for layer in policy["profiles"][profile_id]["required_layers"]
        }
    )
    excluded = sorted(
        {
            layer
            for profile_id in selected
            for layer in policy["profiles"][profile_id]["excluded_layers"]
        }
    )
    return {
        "knowledge_query": query,
        "required_layers": required,
        "excluded_layers": excluded,
    }


def _conflicts(selected: list[str], policy: dict[str, Any]) -> list[dict[str, Any]]:
    selected_set = set(selected)
    rows = []
    for conflict in policy.get("conflicts", []):
        if set(conflict["profiles"]) <= selected_set:
            rows.append(
                {
                    "id": conflict["id"],
                    "profiles": list(conflict["profiles"]),
                    "field": conflict["field"],
                    "options": list(conflict["options"]),
                    "disposition": conflict["disposition"],
                    "selected": conflict.get("selected"),
                    "reason": conflict["reason"],
                }
            )
    return sorted(rows, key=lambda row: row["id"])


def _uncertainties(
    primary: str,
    scores: dict[str, int],
    alternatives: list[str],
    conflicts: list[dict[str, Any]],
    requirements: dict[str, list[str]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if primary == "general_video":
        rows.append(
            {
                "code": "domain_ambiguous",
                "message": "The request does not identify a supported video domain.",
                "alternatives": alternatives,
            }
        )
    elif scores:
        ranked = _ranked_profiles(scores, policy)
        if len(ranked) > 1 and scores[ranked[0]] == scores[ranked[1]]:
            tied = [item for item in ranked if scores[item] == scores[ranked[0]]]
            rows.append(
                {
                    "code": "profile_tie",
                    "message": "Multiple profiles have the same routing score.",
                    "alternatives": tied,
                }
            )
    if conflicts:
        rows.append(
            {
                "code": "profile_conflict",
                "message": "The selected profile blend requires an explicit conflict decision.",
                "alternatives": sorted(
                    {option for conflict in conflicts for option in conflict["options"]}
                ),
            }
        )
    if requirements["missing_inputs"]:
        rows.append(
            {
                "code": "missing_inputs",
                "message": "The request needs additional inputs before score resolution.",
                "alternatives": requirements["missing_inputs"],
            }
        )
    return rows


def normalize_intent(
    original_text: str,
    *,
    user_constraints: Iterable[str] | None = None,
    profile_overrides: Iterable[str] | None = None,
    root: Path = REPO_ROOT,
) -> NormalizedIntent:
    """Return a deterministic, provider-neutral normalized intent proposal."""
    text = _require_string(original_text, "original_text")
    constraints = _non_empty_strings("user_constraints", user_constraints)
    overrides = _ordered_non_empty_strings("profile_overrides", profile_overrides)
    policy = load_profile_policy(root)
    scores = _score_profiles(text, policy)
    primary, secondary, alternatives, source = _select_profiles(
        scores, overrides, policy
    )
    selected = [primary, *secondary]
    task, audience_effect = _task_and_effect(
        text, selected, primary, policy
    )
    requirements = _requirements(text, constraints, selected, policy)
    conflicts = _conflicts(selected, policy)
    routing = _routing(text, selected, policy)
    result: NormalizedIntent = {
        "schema": NORMALIZED_SCHEMA,
        "request": {
            "original_text": text,
            "user_constraints": constraints,
            "profile_overrides": overrides,
        },
        "intent": {
            "primary_domain": policy["profiles"][primary]["domain"],
            "task": task,
            "audience_effect": audience_effect,
            "workflow_hint": _workflow_hint(text, constraints),
        },
        "profiles": {
            "primary": primary,
            "secondary": secondary,
            "confidence": _selection_confidence(
                primary, scores, source, policy
            ),
            "alternatives": alternatives,
            "selection_source": source,
        },
        "requirements": requirements,
        "routing": routing,
        "conflicts": conflicts,
        "uncertainties": _uncertainties(
            primary,
            scores,
            alternatives,
            conflicts,
            requirements,
            policy,
        ),
        "policy_versions": {
            "intent_router": policy["policy_version"],
            "profile_policy": policy["schema"],
            "kernel_contract": policy["kernel_contract"],
        },
    }
    validate_instance("normalized_intent", result, root)
    return result


def canonical_intent_bytes(intent: NormalizedIntent) -> bytes:
    """Return canonical bytes for deterministic replay verification."""
    return canonical_json_bytes(intent)


def _intent_reference(intent: NormalizedIntent) -> str:
    digest = hashlib.sha256(canonical_intent_bytes(intent)).hexdigest()[:16]
    return f"normalized-intent:{digest}"


def build_intent_context(
    original_text: str,
    *,
    token_budget: int = 12_000,
    user_constraints: Iterable[str] | None = None,
    profile_overrides: Iterable[str] | None = None,
    minimum_status: str = "ingested",
    target_format: str = "hybrid",
    terminology_proposal_ids: Iterable[str] = (),
    knowledge_lens: dict[str, Any] | None = None,
    root: Path = REPO_ROOT,
) -> IntentContext:
    """Normalize a request, then call the existing safe context broker."""
    normalized = normalize_intent(
        original_text,
        user_constraints=user_constraints,
        profile_overrides=profile_overrides,
        root=root,
    )
    if knowledge_lens is not None:
        lens = validate_knowledge_comparison_lens(
            knowledge_lens, root, require_compilable=True
        )
        bundle = copy.deepcopy(lens["context_bundle"])
        lens_request = bundle["request"]
        expected = {
            "token_budget": token_budget,
            "minimum_status": minimum_status,
            "target_format": target_format,
        }
        mismatches = [
            key for key, value in expected.items() if lens_request[key] != value
        ]
        if mismatches:
            raise ValueError(
                "knowledge lens context options differ: " + ", ".join(mismatches)
            )
        lens_domain = lens_request["domain"]
        if lens_domain is not None and lens_domain != normalized["intent"]["primary_domain"]:
            raise ValueError("knowledge lens domain does not match normalized intent")
        bundle["request"]["intent"] = _intent_reference(normalized)
        validate_instance("context_bundle", bundle, root)
        return {"normalized_intent": normalized, "context_bundle": bundle}
    routing = normalized["routing"]
    retrieval_frame = {
        "schema": "cpcs.retrieval_frame/1.0",
        "domain_masks": [normalized["intent"]["primary_domain"]],
        "hard_constraints": normalized["requirements"]["hard_constraints"],
        "required_coverage_slots": routing["required_layers"],
        "excluded_layers": routing["excluded_layers"],
        "requested_outputs": ["concept", "mapping", "rule", "claim", "equation", "method", "mechanism", "source_passage"],
        "root_budget": QUERY_POLICY["maximum_roots"],
        "hop_budget": 5,
        "prerequisite_budget": 25 - QUERY_POLICY["maximum_roots"],
        "token_budget": token_budget,
    }
    bundle = build_context_bundle(
        routing["knowledge_query"],
        token_budget=token_budget,
        minimum_status=minimum_status,
        include_external_evidence=False,
        domain=normalized["intent"]["primary_domain"],
        target_format=target_format,
        required_layers=routing["required_layers"],
        excluded_layers=routing["excluded_layers"],
        intent=_intent_reference(normalized),
        terminology_proposal_ids=terminology_proposal_ids,
        retrieval_frame=retrieval_frame,
        root=root,
    )
    return {"normalized_intent": normalized, "context_bundle": bundle}


def _common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("request")
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--profile", action="append", default=[])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    normalize = sub.add_parser("normalize")
    _common_arguments(normalize)
    context = sub.add_parser("context")
    _common_arguments(context)
    context.add_argument("--token-budget", type=int, default=12_000)
    context.add_argument(
        "--minimum-status",
        choices=("ingested", "partial", "proven"),
        default="ingested",
    )
    context.add_argument(
        "--target-format",
        choices=("prose", "natural_language", "yaml", "json", "xml", "hybrid"),
        default="hybrid",
    )
    context.add_argument("--terminology-proposal-id", action="append", default=[])
    args = parser.parse_args(argv)
    if args.command == "normalize":
        result = normalize_intent(
            args.request,
            user_constraints=args.constraint,
            profile_overrides=args.profile,
        )
    else:
        result = build_intent_context(
            args.request,
            token_budget=args.token_budget,
            user_constraints=args.constraint,
            profile_overrides=args.profile,
            minimum_status=args.minimum_status,
            target_format=args.target_format,
            terminology_proposal_ids=args.terminology_proposal_id,
        )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
