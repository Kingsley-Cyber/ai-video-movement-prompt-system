"""Named deterministic rule evaluators shared by querying and compilation."""

from __future__ import annotations

from typing import Any, Callable

Evaluator = Callable[[dict[str, Any], set[str], set[str]], tuple[bool, str]]


def _require_controls(
    rule: dict[str, Any], selected: set[str], controls: set[str]
) -> tuple[bool, str]:
    trigger = rule["trigger"].get("concept_id")
    if trigger not in selected:
        return True, "trigger not selected"
    required = set(rule["arguments"].get("control_ids", []))
    missing = sorted(required - controls)
    return (
        not missing,
        "missing controls: " + ", ".join(missing) if missing else "required controls present",
    )


def _forbid_combination(
    rule: dict[str, Any], selected: set[str], _controls: set[str]
) -> tuple[bool, str]:
    forbidden = set(rule["arguments"].get("concept_ids", []))
    present = sorted(forbidden & selected)
    return len(present) < 2, "forbidden combination: " + ", ".join(present)


def _require_concept(
    rule: dict[str, Any], selected: set[str], _controls: set[str]
) -> tuple[bool, str]:
    trigger = rule["trigger"].get("concept_id")
    if trigger not in selected:
        return True, "trigger not selected"
    required = rule["arguments"].get("concept_id")
    return required in selected, f"required concept {required}"


EVALUATORS: dict[str, Evaluator] = {
    "require_controls": _require_controls,
    "forbid_combination": _forbid_combination,
    "require_concept": _require_concept,
}


def controls_from_mapping(mapping: dict[str, Any]) -> set[str]:
    controls = {mapping["target_id"]}
    for action_unit in mapping["mapping"].get("required_action_units", []):
        controls.add(f"facs.{action_unit}")
    return controls


def controls_for_selection(
    mappings: list[dict[str, Any]],
    selected: set[str],
    provider: str | None = None,
    model_version: str | None = None,
) -> set[str]:
    controls: set[str] = set()
    for mapping in mappings:
        if mapping["concept_id"] not in selected:
            continue
        if mapping.get("provider") and mapping["provider"] != provider:
            continue
        if mapping.get("model_version") and mapping["model_version"] != model_version:
            continue
        controls.update(controls_from_mapping(mapping))
    return controls


def evaluate_rules(
    rules: list[dict[str, Any]], selected: set[str], controls: set[str]
) -> list[dict[str, Any]]:
    results = []
    for rule in sorted(rules, key=lambda item: item["id"]):
        evaluator = EVALUATORS.get(rule["evaluator"])
        if evaluator is None:
            results.append(
                {
                    "rule_id": rule["id"],
                    "passed": False,
                    "severity": "error",
                    "message": f"unknown named evaluator {rule['evaluator']}",
                    "explanation": rule["explanation"],
                }
            )
            continue
        passed, message = evaluator(rule, selected, controls)
        results.append(
            {
                "rule_id": rule["id"],
                "passed": passed,
                "severity": rule["severity"],
                "message": message,
                "explanation": rule["explanation"],
            }
        )
    return results


def referenced_concept_ids(rule: dict[str, Any]) -> set[str]:
    references: set[str] = set()
    trigger = rule.get("trigger", {}).get("concept_id")
    if isinstance(trigger, str):
        references.add(trigger)
    required = rule.get("arguments", {}).get("concept_id")
    if isinstance(required, str):
        references.add(required)
    references.update(
        item
        for item in rule.get("arguments", {}).get("concept_ids", [])
        if isinstance(item, str)
    )
    return references
