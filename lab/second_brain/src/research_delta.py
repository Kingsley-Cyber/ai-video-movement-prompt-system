"""Deterministic research-to-implementation impact planning without authority writes."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from .authority import authority_reader
from .research_session import list_proposals, session_status
from .validate import (
    REPO_ROOT,
    ValidationFailure,
    assert_write_target,
    canonical_json_bytes,
    read_jsonl,
    sha256_value,
    validate_instance,
)


DELTA_POLICY = "cpcs-research-delta/1.0"
DELTA_ID_PATTERN = re.compile(r"research_delta_[0-9a-f]{24}")
MAX_PLAN_BYTES = 8 * 1024 * 1024

_RECORD_OWNERS = {
    "claim": "lab/second_brain/curated/claims.jsonl",
    "equation": "lab/second_brain/curated/equations.jsonl",
    "method": "lab/second_brain/curated/methods.jsonl",
    "mechanism": "lab/second_brain/curated/mechanisms.jsonl",
}

_TARGETS: dict[str, dict[str, Any]] = {
    "knowledge_record": {
        "owner": "lab/second_brain/src/validate.py",
        "contracts": (
            "lab/second_brain/schemas/{record_type}.schema.json",
            "lab/second_brain/schemas/proposal.schema.json",
            "lab/second_brain/schemas/distillation_batch.schema.json",
        ),
        "allowed_paths": (
            "lab/second_brain/schemas/",
            "lab/second_brain/src/validate.py",
            "lab/second_brain/src/distill.py",
            "lab/second_brain/tests/",
        ),
        "proposal_kinds": ("schema", "test", "patch"),
        "tests": (
            "python3 -m unittest lab.second_brain.tests.test_validate lab.second_brain.tests.test_distill",
        ),
    },
    "typed_relationship": {
        "owner": "lab/second_brain/src/graph.py",
        "contracts": (
            "lab/second_brain/schemas/edge.schema.json",
            "lab/second_brain/src/graph.py",
            "lab/second_brain/src/query.py",
        ),
        "allowed_paths": (
            "lab/second_brain/schemas/edge.schema.json",
            "lab/second_brain/src/graph.py",
            "lab/second_brain/src/query.py",
            "lab/second_brain/tests/",
        ),
        "proposal_kinds": ("schema", "mapping", "code", "test", "patch"),
        "tests": (
            "python3 -m unittest lab.second_brain.tests.test_graph lab.second_brain.tests.test_query",
            "python3 -m lab.second_brain.src.retrieval_eval --output work/retrieval/research-delta.json",
        ),
    },
    "control_mapping": {
        "owner": "lab/compiler/control_translations.yaml",
        "contracts": (
            "lab/second_brain/schemas/mapping.schema.json",
            "lab/compiler/schemas/control_translation.schema.json",
            "lab/compiler/control_translations.yaml",
        ),
        "allowed_paths": (
            "lab/second_brain/curated/mappings.jsonl",
            "lab/compiler/control_translations.yaml",
            "lab/compiler/schemas/control_translation.schema.json",
            "lab/compiler/tests/",
        ),
        "proposal_kinds": ("mapping", "test", "patch"),
        "tests": ("python3 -m unittest discover -s lab/compiler/tests -p 'test_*.py'",),
    },
    "canonical_score": {
        "owner": "lab/compiler/score.py",
        "contracts": (
            "lab/compiler/schemas/universal_score.schema.json",
            "lab/compiler/schemas/score_request.schema.json",
            "lab/profiles/universal/video_v1.yaml",
        ),
        "allowed_paths": (
            "lab/compiler/score.py",
            "lab/compiler/schemas/",
            "lab/profiles/universal/video_v1.yaml",
            "lab/profiles/domain/",
            "lab/compiler/tests/",
        ),
        "proposal_kinds": ("schema", "code", "test", "patch"),
        "tests": ("python3 -m unittest discover -s lab/compiler/tests -p 'test_*.py'",),
    },
    "provider_capability": {
        "owner": "lab/compiler/providers/veo_3_1.yaml",
        "contracts": (
            "lab/compiler/schemas/provider_capability.schema.json",
            "lab/compiler/providers/veo_3_1.yaml",
            "lab/runtime/schemas/render_job.schema.json",
        ),
        "allowed_paths": (
            "lab/compiler/providers/",
            "lab/compiler/schemas/provider_capability.schema.json",
            "lab/runtime/adapters/",
            "lab/runtime/tests/",
        ),
        "proposal_kinds": ("provider_profile", "code", "test", "patch"),
        "tests": (
            "python3 -m unittest lab.compiler.tests.test_build",
            "python3 -m unittest discover -s lab/runtime/tests -p 'test_*.py'",
        ),
    },
    "prompt_projection": {
        "owner": "lab/compiler/build.py",
        "contracts": (
            "lab/compiler/schemas/build_manifest.schema.json",
            "lab/compiler/schemas/loss_report.schema.json",
            "lab/compiler/build.py",
        ),
        "allowed_paths": (
            "lab/compiler/build.py",
            "lab/compiler/schemas/",
            "lab/compiler/tests/",
        ),
        "proposal_kinds": ("code", "test", "documentation", "patch"),
        "tests": ("python3 -m unittest lab.compiler.tests.test_build",),
    },
    "verification_rule": {
        "owner": "lab/verification/verify.py",
        "contracts": (
            "lab/verification/schemas/verification_evidence_bundle.schema.json",
            "lab/verification/schemas/compliance_report.schema.json",
            "lab/verification/verify.py",
        ),
        "allowed_paths": (
            "lab/verification/",
            "lab/second_brain/schemas/pegasus_observation.schema.json",
            "lab/second_brain/schemas/measurement_observation.schema.json",
        ),
        "proposal_kinds": ("schema", "verification_rule", "code", "test", "patch"),
        "tests": (
            "python3 -m unittest discover -s lab/verification/tests -p 'test_*.py'",
        ),
    },
    "experiment_policy": {
        "owner": "lab/second_brain/src/reflect.py",
        "contracts": (
            "lab/second_brain/schemas/run.schema.json",
            "lab/second_brain/schemas/learned_weight.schema.json",
            "lab/second_brain/src/reflect.py",
        ),
        "allowed_paths": (
            "lab/second_brain/src/record.py",
            "lab/second_brain/src/reflect.py",
            "lab/second_brain/schemas/",
            "lab/second_brain/tests/",
        ),
        "proposal_kinds": ("policy", "code", "test", "patch"),
        "tests": (
            "python3 -m unittest lab.second_brain.tests.test_record lab.second_brain.tests.test_reflect",
        ),
    },
    "application_contract": {
        "owner": "lab/application/service.py",
        "contracts": (
            "lab/application/schemas/application_request.schema.json",
            "lab/application/schemas/application_response.schema.json",
            "lab/application/service.py",
        ),
        "allowed_paths": (
            "lab/application/service.py",
            "lab/application/schemas/",
            "lab/application/tests/",
        ),
        "proposal_kinds": ("schema", "code", "test", "patch"),
        "tests": (
            "python3 -m unittest discover -s lab/application/tests -p 'test_*.py'",
        ),
    },
}

_TARGET_COMPATIBILITY = {
    "knowledge_only": {"knowledge_record", "typed_relationship"},
    "contract_affecting": set(_TARGETS),
    "implementation_affecting": set(_TARGETS),
    "provider_version_affecting": {
        "provider_capability",
        "prompt_projection",
        "verification_rule",
    },
    "verification_affecting": {"verification_rule", "experiment_policy"},
    "policy_affecting": {
        "knowledge_record",
        "control_mapping",
        "experiment_policy",
        "application_contract",
    },
    "contradictory_or_unverified": set(),
}


def _file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _git_state(root: Path) -> tuple[str | None, list[str]]:
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--short", "--untracked-files=all"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        return None, []
    if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        return None, []
    dirty = sorted({row[3:] for row in status if len(row) > 3})
    return revision, dirty


def _delta_root(root: Path, *, create: bool) -> Path:
    repository = root.resolve()
    current = repository
    for part in ("work", "application", "research_deltas"):
        current = current / part
        if current.is_symlink():
            raise ValidationFailure(f"research delta path cannot be a symlink: {current}")
        if create:
            current.mkdir(mode=0o700, exist_ok=True)
            os.chmod(current, 0o700)
    if not current.is_dir():
        raise ValidationFailure("research delta operational root does not exist")
    resolved = current.resolve()
    if repository not in resolved.parents:
        raise ValidationFailure("research delta operational root escaped the repository")
    return resolved


def _plan_path(delta_id: str, root: Path, *, create: bool) -> Path:
    if DELTA_ID_PATTERN.fullmatch(delta_id) is None:
        raise ValidationFailure("research delta ID is invalid")
    base = _delta_root(root, create=create)
    directory = base / delta_id
    if directory.is_symlink():
        raise ValidationFailure("research delta directory cannot be a symlink")
    if create:
        directory.mkdir(mode=0o700, exist_ok=True)
        os.chmod(directory, 0o700)
    if base not in directory.resolve().parents:
        raise ValidationFailure("research delta directory escaped its operational root")
    return directory / "plan.json"


def _write_new(path: Path, value: dict[str, Any]) -> None:
    payload = canonical_json_bytes(value)
    if len(payload) > MAX_PLAN_BYTES:
        raise ValidationFailure("research delta plan exceeds the operational size limit")
    if path.exists():
        if path.is_symlink() or path.read_bytes() != payload:
            raise ValidationFailure("research delta plan identity collision")
        return
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)


def _read_plan(delta_id: str, root: Path) -> dict[str, Any]:
    path = _plan_path(delta_id, root, create=False)
    if path.is_symlink():
        raise ValidationFailure("research delta plan cannot be a symlink")
    try:
        if path.stat().st_size > MAX_PLAN_BYTES:
            raise ValidationFailure("research delta plan exceeds the operational size limit")
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationFailure(f"cannot read research delta plan: {error}") from error
    if not isinstance(value, dict):
        raise ValidationFailure("research delta plan must be an object")
    validate_instance("research_delta_plan", value, root)
    unsigned = copy.deepcopy(value)
    actual_hash = unsigned.pop("plan_hash")
    if sha256_value(unsigned) != actual_hash:
        raise ValidationFailure("research delta plan hash does not match its content")
    return value


def _existing_ids(proposal_type: str, root: Path) -> set[str]:
    relative = _RECORD_OWNERS[proposal_type]
    path = root / relative
    return {row["id"] for row in read_jsonl(path)} if path.is_file() else set()


def _normalize_source_refs(candidate: dict[str, Any]) -> list[dict[str, str]]:
    refs = []
    for source in candidate["source_evidence"]:
        content_hash = source.get("content_sha256")
        if not isinstance(content_hash, str):
            raise ValidationFailure(
                f"{candidate['candidate_id']} lacks a source content hash"
            )
        if not content_hash.startswith("sha256:"):
            content_hash = "sha256:" + content_hash
        refs.append(
            {
                "source_id": source["source_id"],
                "locator": source["locator"],
                "content_hash": content_hash,
                "evidence_claim": source["claim"],
            }
        )
    refs.sort(
        key=lambda row: (
            row["source_id"], row["locator"], row["content_hash"], row["evidence_claim"]
        )
    )
    return refs


def _target_spec(target: str, record_type: str) -> dict[str, Any]:
    spec = copy.deepcopy(_TARGETS[target])
    spec["contracts"] = tuple(
        value.format(record_type=record_type) for value in spec["contracts"]
    )
    return spec


def _contract_snapshots(paths: set[str], root: Path) -> list[dict[str, Any]]:
    rows = []
    for relative in sorted(paths):
        path = root / relative
        exists = path.is_file() and not path.is_symlink()
        rows.append(
            {
                "path": relative,
                "exists": exists,
                "content_hash": _file_hash(path) if exists else None,
            }
        )
    return rows


def _validate_selection(selection: dict[str, Any]) -> None:
    change_class = selection["change_class"]
    targets = set(selection["implementation_targets"])
    incompatible = sorted(targets - _TARGET_COMPATIBILITY[change_class])
    if incompatible:
        raise ValidationFailure(
            f"{change_class} cannot target: {', '.join(incompatible)}"
        )
    if selection["knowledge_class"] == "unverified" and targets:
        raise ValidationFailure(
            "unverified research cannot create an implementation proposal"
        )


@authority_reader("research_delta_prepare")
def prepare_research_delta(
    request: dict[str, Any], root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Create one content-addressed operational plan from completed research claims."""
    validate_instance("research_delta_request", request, root)
    selections = copy.deepcopy(request["claims"])
    for selection in selections:
        _validate_selection(selection)
    candidate_ids = [selection["candidate_id"] for selection in selections]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValidationFailure("research delta candidate IDs must be unique")

    status = session_status(request["session_id"], root)
    if status["state"] not in {"proposals_ready", "distilled"}:
        raise ValidationFailure("research delta requires completed extraction proposals")
    proposal_list = list_proposals(request["session_id"], root)
    candidates = {row["candidate_id"]: row for row in proposal_list["proposals"]}
    missing = sorted(set(candidate_ids) - set(candidates))
    if missing:
        raise ValidationFailure(
            "research delta references unknown candidates: " + ", ".join(missing)
        )

    concepts = (
        {row["id"] for row in read_jsonl(root / "lab" / "concepts.jsonl")}
        if (root / "lab" / "concepts.jsonl").is_file()
        else set()
    )
    operational_claims: list[dict[str, Any]] = []
    target_claims: dict[str, list[str]] = {}
    contract_paths: set[str] = set()
    selected_targets: dict[str, dict[str, Any]] = {}

    for selection in sorted(selections, key=lambda row: row["candidate_id"]):
        candidate = candidates[selection["candidate_id"]]
        if candidate["proposal_type"] != "claim":
            raise ValidationFailure(
                f"{candidate['candidate_id']} is not a claim proposal"
            )
        record = candidate["proposed_record"]
        statement = record.get("statement")
        concept_ids = sorted(set(record.get("concept_ids", [])))
        if not isinstance(statement, str) or not statement:
            raise ValidationFailure(
                f"{candidate['candidate_id']} claim has no statement"
            )
        if not concept_ids or not set(concept_ids) <= concepts:
            raise ValidationFailure(
                f"{candidate['candidate_id']} has unresolved concept placement"
            )
        source_refs = _normalize_source_refs(candidate)
        candidate_hash = sha256_value(candidate)
        suggested_id = candidate.get("suggested_id")
        existing = (
            suggested_id
            if isinstance(suggested_id, str)
            and suggested_id in _existing_ids("claim", root)
            else None
        )
        targets = sorted(selection["implementation_targets"])
        specs = {target: _target_spec(target, "claim") for target in targets}
        selected_targets.update(specs)
        affected_owners = sorted(
            {_RECORD_OWNERS["claim"]} | {spec["owner"] for spec in specs.values()}
        )
        affected_contracts = sorted(
            {"lab/second_brain/schemas/claim.schema.json"}
            | {
                contract
                for spec in specs.values()
                for contract in spec["contracts"]
            }
        )
        required_tests = sorted(
            {
                "python3 -m unittest lab.second_brain.tests.test_source_extract"
            }
            | {test for spec in specs.values() for test in spec["tests"]}
            | {"python3 lab/scripts/validate_repo.py"}
        )
        limitations = sorted(
            set(record.get("limitations", [])) | set(selection["limitations"])
        )
        identity = {
            "session_id": request["session_id"],
            "completed_bundle_hash": status["completed_bundle_hash"],
            "candidate_hash": candidate_hash,
            "knowledge_class": selection["knowledge_class"],
            "change_class": selection["change_class"],
            "scope": selection["scope"],
            "targets": targets,
        }
        claim_id = "operational_claim_" + sha256_value(identity)[7:31]
        claim = {
            "claim_id": claim_id,
            "proposal_ref": {
                "candidate_id": candidate["candidate_id"],
                "candidate_hash": candidate_hash,
                "proposal_type": "claim",
            },
            "source_refs": source_refs,
            "content_hashes": sorted({row["content_hash"] for row in source_refs}),
            "knowledge_class": selection["knowledge_class"],
            "change_class": selection["change_class"],
            "scope": selection["scope"],
            "claim": statement,
            "limitations": limitations,
            "current_owner": _RECORD_OWNERS["claim"],
            "affected_owners": affected_owners,
            "affected_contracts": affected_contracts,
            "required_tests": required_tests,
            "placement": {
                "status": "exact_id_overlap" if existing else "concept_anchored_new",
                "suggested_id": suggested_id,
                "existing_record_id": existing,
                "concept_ids": concept_ids,
            },
            "status": "staged",
        }
        operational_claims.append(claim)
        contract_paths.update(affected_contracts)
        for target in targets:
            target_claims.setdefault(target, []).append(claim_id)

    revision, dirty_paths = _git_state(root)
    snapshots = _contract_snapshots(contract_paths, root)
    baseline = {
        "repository_revision": revision,
        "dirty_paths": dirty_paths,
        "contract_snapshots": snapshots,
    }
    impact_paths = []
    for claim in operational_claims:
        concepts_for_claim = claim["placement"]["concept_ids"]
        targets = sorted(
            target
            for target, claim_ids in target_claims.items()
            if claim["claim_id"] in claim_ids
        )
        if not targets:
            nodes = [
                {"kind": "claim", "ref": claim["claim_id"]},
                {"kind": "concept", "ref": concepts_for_claim[0]},
                {"kind": "target", "ref": "review_only"},
                {"kind": "owner", "ref": claim["current_owner"]},
                {"kind": "contract", "ref": claim["affected_contracts"][0]},
                {"kind": "test", "ref": claim["required_tests"][0]},
            ]
            impact_paths.append(
                {
                    "claim_id": claim["claim_id"],
                    "target": "review_only",
                    "nodes": nodes,
                    "path_hash": sha256_value(nodes),
                }
            )
            continue
        for target in targets:
            spec = selected_targets[target]
            nodes = [{"kind": "claim", "ref": claim["claim_id"]}]
            nodes.extend({"kind": "concept", "ref": value} for value in concepts_for_claim)
            nodes.extend(
                [
                    {"kind": "target", "ref": target},
                    {"kind": "owner", "ref": spec["owner"]},
                    {"kind": "contract", "ref": spec["contracts"][0]},
                    {"kind": "test", "ref": spec["tests"][0]},
                ]
            )
            impact_paths.append(
                {
                    "claim_id": claim["claim_id"],
                    "target": target,
                    "nodes": nodes,
                    "path_hash": sha256_value(nodes),
                }
            )

    implementation_proposals = []
    for target in sorted(target_claims):
        spec = selected_targets[target]
        proposal_identity = {
            "target": target,
            "claim_ids": sorted(target_claims[target]),
            "owner": spec["owner"],
            "contracts": sorted(spec["contracts"]),
            "baseline": baseline,
            "policy": DELTA_POLICY,
        }
        implementation_proposals.append(
            {
                "proposal_id": "implementation_proposal_"
                + sha256_value(proposal_identity)[7:31],
                "claim_ids": sorted(target_claims[target]),
                "target": target,
                "proposal_kinds": sorted(spec["proposal_kinds"]),
                "current_owner": spec["owner"],
                "allowed_paths": sorted(spec["allowed_paths"]),
                "affected_contracts": sorted(spec["contracts"]),
                "required_tests": sorted(
                    set(spec["tests"]) | {"python3 lab/scripts/validate_repo.py"}
                ),
                "acceptance_checks": [
                    "exact source and content hashes remain bound",
                    "current owner is extended without a parallel authority",
                    "public contract and semantic regression tests pass",
                    "curated and immutable authority remain unchanged",
                    "owner reviews the isolated patch before integration",
                ],
                "patch_boundary": {
                    "status": "proposal_only_requires_explicit_owner_authorization",
                    "isolation_required": True,
                    "forbidden_actions": [
                        "assign durable curated IDs",
                        "edit frozen research",
                        "merge or push",
                        "promote knowledge or code",
                        "replace qualified behavior without comparison",
                    ],
                },
                "status": "staged",
            }
        )

    request_hash = sha256_value(request)
    identity = {
        "policy": DELTA_POLICY,
        "request_hash": request_hash,
        "session": {
            "completed_bundle_hash": status["completed_bundle_hash"],
            "captured_response_hash": status["captured_response_hash"],
            "batch_hash": proposal_list["batch_hash"],
        },
        "baseline": baseline,
        "operational_claims": operational_claims,
        "implementation_proposals": implementation_proposals,
    }
    delta_id = "research_delta_" + sha256_value(identity)[7:31]
    plan = {
        "schema": "cpcs.research_delta_plan/1.0",
        "delta_id": delta_id,
        "created_at": request["planned_at"],
        "objective": request["objective"],
        "request_hash": request_hash,
        "policy_versions": {"research_delta": DELTA_POLICY},
        "session": {
            "session_id": status["session_id"],
            "session_hash": status["session_hash"],
            "source_bundle_id": status["source_bundle_id"],
            "source_bundle_hash": status["source_bundle_hash"],
            "completed_bundle_id": status["completed_bundle_id"],
            "completed_bundle_hash": status["completed_bundle_hash"],
            "captured_response_hash": status["captured_response_hash"],
            "batch_id": proposal_list["batch_id"],
            "batch_hash": proposal_list["batch_hash"],
        },
        "baseline": baseline,
        "operational_claims": operational_claims,
        "impact_paths": sorted(
            impact_paths, key=lambda row: (row["claim_id"], row["target"])
        ),
        "implementation_proposals": implementation_proposals,
        "authority": {
            "research": "captured_untrusted_evidence",
            "plan": "operational_proposal_only",
            "code": "unchanged",
            "curated": "unchanged",
            "patch_execution": "requires_separate_explicit_owner_authorization",
        },
    }
    plan["plan_hash"] = sha256_value(plan)
    validate_instance("research_delta_plan", plan, root)
    output_path = _plan_path(delta_id, root, create=True)
    assert_write_target("research_delta", output_path, root)
    _write_new(output_path, plan)
    return plan


@authority_reader("research_delta_inspect")
def inspect_research_delta(
    delta_id: str, root: Path = REPO_ROOT
) -> dict[str, Any]:
    """Read and rehash one immutable operational research-delta plan."""
    return _read_plan(delta_id, root)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("request", type=Path)
    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("delta_id")
    args = parser.parse_args(argv)
    if args.command == "prepare":
        request = json.loads(args.request.read_text(encoding="utf-8"))
        value = prepare_research_delta(request)
    else:
        value = inspect_research_delta(args.delta_id)
    print(json.dumps(value, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
