"""RQ-1: release qualification artifacts (repo state, manifest, acceptance, report)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    return r.stdout.strip()


def main() -> int:
    branch = git("branch", "--show-current")
    head = git("rev-parse", "HEAD")
    base = git("merge-base", "HEAD", "origin/main")
    remote = git("remote", "get-url", "origin")

    repo_state = {
        "artifact": "CPCS_RQ1_REPO_STATE", "version": "v0.1",
        "branch": branch, "head": head, "base_commit": base,
        "merge_base_with_origin_main": base,
        "remote_url": remote,
        "worktree_path": str(REPO),
        "main_worktree": "untouched tracked state (see report note)",
        "note": ("main worktree at /Users/king/ai-video-movement-prompt-system "
                 "has no tracked modifications; it carries one pre-existing "
                 "untracked file (lab/application/reasoning_treatment.py) from "
                 "the initial integration seeding"),
    }
    (OUT / "CPCS_RQ1_REPO_STATE_v0.1.json").write_text(json.dumps(repo_state, indent=1))

    # ---- diff classification ----
    changed = git("status", "--short").splitlines()
    files = sorted({line.split(None, 1)[1].strip() for line in changed
                    if line.strip() and len(line.split(None, 1)) > 1})
    classification = {
        "PRODUCTION_CODE": ["lab/application/service.py",
                            "lab/application/reasoning_treatment.py",
                            "lab/application/cpcs_deliberation.py",
                            "lab/application/cpcs_guided.py",
                            "lab/application/cpcs_guided_handlers.py",
                            "lab/compiler/cpcs_typed.py"],
        "TEST": ["lab/application/tests/test_reasoning_treatment_surface.py",
                 "lab/application/tests/test_cpcs_typed_knowledge_coverage.py",
                 "lab/application/tests/test_tc2_residual_closure.py",
                 "lab/application/tests/test_deliberation_surface.py",
                 "lab/application/tests/test_guided_product_surface.py",
                 "lab/application/tests/test_product_mcp_golden.py"],
        "CONTRACT_SCHEMA": ["lab/application/cpcs_reasoning_path_registry.yaml",
                            "lab/application/cpcs_reasoning_path_registry.schema.json"],
        "ACCEPTANCE_ARTIFACT": [f for f in files
                                if f.startswith("lab/application/CPCS_")],
        "REPORT": ["lab/application/CPCS_REASONING_INTEGRATION_FINAL_REPORT.md",
                   "lab/application/TC1_TYPED_KNOWLEDGE_EXPANSION_REPORT.md",
                   "lab/application/TC2_RESIDUAL_SEMANTIC_CLOSURE_REPORT.md",
                   "lab/application/DR1_KNOWLEDGE_GROUNDED_DELIBERATION_REPORT.md",
                   "lab/application/PC1_GUIDED_PRODUCT_CLOSURE_REPORT.md"],
        "DOCUMENTATION": ["README.md"],
        "DIAGNOSTIC_TOOL": ["lab/application/real_runtime_integration.py",
                            "lab/application/materialize_fixtures.py",
                            "lab/application/tc1_artifacts.py",
                            "lab/application/tc1_coverage.py",
                            "lab/application/tc2_classify.py",
                            "lab/application/tc2_finalize.py",
                            "lab/application/tc2_residuals.py",
                            "lab/application/dr1_artifacts.py",
                            "lab/application/dr1_product_test.py",
                            "lab/application/dr1_acceptance.py",
                            "lab/application/compute_acceptance.py",
                            "lab/application/pc1_artifacts.py",
                            "lab/application/pc1_acceptance.py"],
        "DIAGNOSTIC_TOOL2": ["lab/application/rq1_artifacts.py"],
        "ACCIDENTAL": [],
    }
    classified = set()
    for v in classification.values():
        classified |= set(v)
    unclassified = sorted(set(files) - classified)
    manifest = {
        "artifact": "CPCS_V1_GUIDED_RELEASE_MANIFEST", "version": "v0.1",
        "release_name": "CPCS Guided Prompting v1",
        "branch": branch, "base_commit": base, "head_before_release_commit": head,
        "included_stages": ["RL-1", "TC-1", "TC-2", "DR-1", "PC-1", "RQ-1"],
        "key_capability_statuses": {
            "guided_prompting": "READY", "fast_completion": "READY",
            "auto_mode": "READY", "ideation": "READY",
            "hypothesis_reasoning": "READY", "query_steering": "READY",
            "graph_expansion": "READY", "reasoning_hops": "READY",
            "query_hops": "READY", "session_revision": "READY",
            "MCP": "READY", "prompt_compilation": "READY",
            "provider_generation": "OPTIONAL / NOT_CONFIGURED",
        },
        "acceptance_artifact_references": [
            "CPCS_REASONING_TREATMENT_ACCEPTANCE_v0.1.json",
            "CPCS_TYPED_EXPANSION_ACCEPTANCE_v0.1.json",
            "CPCS_TC2_ACCEPTANCE_v0.1.json",
            "CPCS_DR1_ACCEPTANCE_v0.1.json",
            "CPCS_PRODUCT_CLOSURE_ACCEPTANCE_v0.1.json",
            "CPCS_MCP_TRANSPORT_SMOKE_v0.1.json",
        ],
        "diff_classification": classification,
        "unclassified_files": unclassified,
        "known_limitations": [
            "provider generation unconfigured (optional, does not gate readiness)",
            "frozen-runtime activation breadth on trivial intents (upstream property)",
            "D4 admission policy keeps prose-only semantics as unsupported mappings "
            "by design",
            "session store is per-process (in-memory)",
        ],
        "release_qualification_status": "PENDING",
    }
    (OUT / "CPCS_V1_GUIDED_RELEASE_MANIFEST_v0.1.json").write_text(
        json.dumps(manifest, indent=1))
    print("unclassified files:", unclassified)
    return 0


if __name__ == "__main__":
    sys.exit(main())
