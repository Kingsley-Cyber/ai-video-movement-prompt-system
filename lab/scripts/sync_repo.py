#!/usr/bin/env python3
"""CONTROL PLANE: deterministic E2E sync across the repo's coupled artifacts.

The repo grows and shrinks TOGETHER. This script enforces the sync contract (root AGENTS.md):
when a research package is added or removed, the graph, concept cards, CONCEPT_INDEX, and agent
directions must move with it — drift fails the gate.

    python3 lab/scripts/sync_repo.py           # check (gate mode; exit != 0 on drift)
    python3 lab/scripts/sync_repo.py --fix     # regenerate derived artifacts (graph), then re-check;
                                               # content edits it cannot make are printed as REQUIRED ACTIONS

Checks:
  S1 graph freshness      graph.json == exact rebuild from sources (derived-view law)
  S2 research coverage    every research/ package: alias registered (build_graph.PAPER_ALIASES),
                          >=1 concept card sources it, CONCEPT_INDEX mentions it — catches ADDS
  S3 no dangling refs     no card/alias/index entry points at a research package that is gone — catches REMOVALS
  S4 routing sync         lab/AGENTS.md trigger table <-> RUNBOOK_*.md files, both directions
  S5 second-brain routing root/lab agent routes + registry + required control-plane entrypoints
  S6 universal-score routing one compiler owner + schemas + profiles + public resolver
  S7 render-runtime routing one journaled provider execution owner and transport boundary
  S8 render-verification routing one evidence and bounded-repair owner
  S9 application routing one service + stable CLI/MCP/HTTP adapters + request/response contracts
  S10 release routing package locks + CI + recovery + migration + security + qualification
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_graph  # noqa: E402  (shared root-finder + PAPER_ALIASES + build)

ACTIONS: list[str] = []
FAILS: list[str] = []


def fail(msg: str, action: str | None = None):
    FAILS.append(msg)
    print(f"  FAIL  {msg}")
    if action:
        ACTIONS.append(action)


def ok(msg: str):
    print(f"  ok    {msg}")


def main() -> None:
    fix = "--fix" in sys.argv
    root = build_graph.find_root()
    lab = root / "lab"

    # S1 — graph freshness (derived-view law)
    print("[S1] graph freshness")
    rebuilt = json.dumps(build_graph.build(root), indent=1, sort_keys=True) + "\n"
    gpath = lab / "graph.json"
    current = gpath.read_text() if gpath.exists() else ""
    if current != rebuilt:
        if fix:
            gpath.write_text(rebuilt)
            ok("graph.json regenerated (--fix)")
        else:
            fail("graph.json is stale or missing vs its sources",
                 "run: python3 lab/scripts/sync_repo.py --fix  (regenerates graph.json)")
    else:
        ok("graph.json matches exact rebuild")

    # S2/S3 — research packages <-> aliases <-> cards <-> CONCEPT_INDEX
    print("[S2] research coverage (adds)")
    research = root / "research"
    packages = sorted(p.name for p in research.iterdir()) if research.exists() else []
    cards_text = (lab / "concepts.jsonl").read_text()
    index_text = (lab / "CONCEPT_INDEX.md").read_text()
    for pkg in packages:
        aliases = build_graph.PAPER_ALIASES.get(pkg)
        if not aliases:
            fail(f"research/{pkg}: no alias registered",
                 f"INGEST INCOMPLETE for {pkg}: add alias to build_graph.PAPER_ALIASES, add concept "
                 f"cards (>=3 nl_triggers) sourcing it, add a CONCEPT_INDEX part, rebuild graph")
            continue
        if not any(a in cards_text for a in aliases + [pkg]):
            fail(f"research/{pkg}: zero concept cards source it",
                 f"add cards for {pkg} (growth protocol: retrievable + placed + adjustable)")
        else:
            ok(f"{pkg}: cards present")
        stem = pkg.split("_Research_Package")[0].split(".md")[0]
        if stem[:28] not in index_text and pkg not in index_text:
            fail(f"research/{pkg}: not mentioned in CONCEPT_INDEX.md",
                 f"add a CONCEPT_INDEX part/row for {pkg}")

    print("[S3] dangling refs (removals)")
    dangling = [pkg for pkg in build_graph.PAPER_ALIASES if pkg not in packages]
    for pkg in dangling:
        fail(f"alias registered for research/{pkg} but the package is GONE",
             f"REMOVAL INCOMPLETE for {pkg}: delete its alias from build_graph.PAPER_ALIASES, "
             f"retire/retag its concept cards, remove its CONCEPT_INDEX part, rebuild graph")
    if not dangling:
        ok("no aliases point at removed packages")

    # S4 — routing table <-> runbooks on disk
    print("[S4] routing sync")
    agents = (lab / "AGENTS.md").read_text()
    routed = set(re.findall(r"`(RUNBOOK_[A-Za-z0-9_]+\.md)`", agents))
    on_disk = {p.name for p in lab.glob("RUNBOOK_*.md")}
    for missing in sorted(routed - on_disk):
        fail(f"AGENTS.md routes to {missing} which does not exist", f"restore {missing} or remove its routing row")
    for orphan in sorted(on_disk - routed):
        fail(f"{orphan} exists but has no routing row in lab/AGENTS.md", f"add a trigger row for {orphan}")
    if routed == on_disk:
        ok(f"{len(on_disk)} runbooks all routed, no orphans")

    # S5 — second-brain directory cannot become an orphan
    print("[S5] second-brain routing")
    root_agents = (root / "AGENTS.md").read_text()
    registry = (lab / "registry.yaml").read_text()
    required = [
        lab / "second_brain" / "AGENTS.md",
        lab / "second_brain" / "IMPLEMENTATION_PLAN.md",
        lab / "second_brain" / "requirements.txt",
        lab / "second_brain" / "src" / "graph.py",
        lab / "second_brain" / "src" / "temporal.py",
        lab / "second_brain" / "src" / "indexes.py",
        lab / "second_brain" / "src" / "validate.py",
        lab / "second_brain" / "src" / "query.py",
        lab / "second_brain" / "src" / "context.py",
        lab / "second_brain" / "src" / "intent.py",
        lab / "second_brain" / "src" / "compile.py",
        lab / "second_brain" / "src" / "curate.py",
        lab / "second_brain" / "src" / "record.py",
        lab / "second_brain" / "src" / "ingest.py",
        lab / "second_brain" / "src" / "source_extract.py",
        lab / "second_brain" / "src" / "distill.py",
        lab / "second_brain" / "src" / "pegasus.py",
        lab / "second_brain" / "src" / "video_observation.py",
        lab / "second_brain" / "analysis_profiles.yaml",
        lab / "second_brain" / "src" / "providers" / "twelvelabs" / "__init__.py",
        lab / "second_brain" / "src" / "providers" / "twelvelabs" / "assets.py",
        lab / "second_brain" / "src" / "providers" / "twelvelabs" / "pegasus_analyze.py",
        lab / "second_brain" / "src" / "providers" / "twelvelabs" / "pegasus_segment.py",
        lab / "second_brain" / "src" / "providers" / "twelvelabs" / "pegasus_batch.py",
        lab / "second_brain" / "src" / "providers" / "twelvelabs" / "knowledge_store_search.py",
        lab / "second_brain" / "src" / "providers" / "twelvelabs" / "jockey.py",
        lab / "second_brain" / "src" / "providers" / "twelvelabs" / "marengo.py",
        lab / "second_brain" / "src" / "reflect.py",
        lab / "second_brain" / "src" / "migrate.py",
        lab / "second_brain" / "schemas" / "normalized_intent.schema.json",
        lab / "second_brain" / "schemas" / "derived_indexes.schema.json",
        lab / "second_brain" / "schemas" / "retrieved_passages.schema.json",
        lab / "second_brain" / "schemas" / "semantic_extraction_response.schema.json",
        lab / "second_brain" / "schemas" / "source_extraction_bundle.schema.json",
        lab / "second_brain" / "schemas" / "normalized_video_observation.schema.json",
        lab / "second_brain" / "schemas" / "video_observation_graph.schema.json",
        lab / "second_brain" / "schemas" / "video_analysis_cascade.schema.json",
        lab / "second_brain" / "schemas" / "twelvelabs_corpus_response.schema.json",
        lab / "profiles" / "intent_routing.yaml",
    ]
    required_registry_entries = {
        "second_brain_graph",
        "second_brain_temporal",
        "second_brain_indexes",
        "second_brain_validate",
        "second_brain_query",
        "second_brain_context",
        "second_brain_intent",
        "second_brain_compile",
        "second_brain_curate",
        "second_brain_record",
        "second_brain_ingest",
        "second_brain_source_extract",
        "second_brain_distill",
        "second_brain_pegasus",
        "second_brain_analysis_profiles",
        "second_brain_video_observation",
        "second_brain_twelvelabs",
        "second_brain_twelvelabs_assets",
        "second_brain_twelvelabs_analyze",
        "second_brain_twelvelabs_segment",
        "second_brain_twelvelabs_batch",
        "second_brain_twelvelabs_search",
        "second_brain_twelvelabs_jockey",
        "second_brain_twelvelabs_marengo",
        "second_brain_reflect",
        "second_brain_migrate",
    }
    if "lab/second_brain/AGENTS.md" not in root_agents:
        fail("root AGENTS.md does not route the second brain",
             "add a root routing row for lab/second_brain/AGENTS.md")
    if "second_brain/AGENTS.md" not in agents:
        fail("lab/AGENTS.md does not route the second brain",
             "add a lab workflow row for second_brain/AGENTS.md")
    if "second_brain: second_brain/" not in registry:
        fail("registry.yaml does not register second_brain/",
             "add second_brain: second_brain/ to lab/registry.yaml")
    missing_registry_entries = sorted(
        name for name in required_registry_entries if f"{name}:" not in registry
    )
    for name in missing_registry_entries:
        fail(
            f"registry.yaml does not register {name}",
            f"add scripts.{name} to lab/registry.yaml",
        )
    for path in required:
        if not path.exists():
            fail(f"required second-brain artifact missing: {path.relative_to(root)}")
    if (
        "lab/second_brain/AGENTS.md" in root_agents
        and "second_brain/AGENTS.md" in agents
        and "second_brain: second_brain/" in registry
        and not missing_registry_entries
        and all(path.exists() for path in required)
    ):
        ok("second brain is routed in root, lab, and registry with live entrypoints")

    # S6: the universal score cannot fork across profiles or clients
    print("[S6] universal-score routing")
    compiler_required = [
        lab / "compiler" / "AGENTS.md",
        lab / "compiler" / "score.py",
        lab / "compiler" / "reverse.py",
        lab / "compiler" / "build.py",
        lab / "compiler" / "profiles.py",
        lab / "compiler" / "merge.py",
        lab / "compiler" / "constraints.py",
        lab / "compiler" / "provenance.py",
        lab / "compiler" / "translations.py",
        lab / "compiler" / "control_translations.yaml",
        lab / "compiler" / "schemas" / "control_translation.schema.json",
        lab / "compiler" / "schemas" / "profile.schema.json",
        lab / "compiler" / "schemas" / "score_request.schema.json",
        lab / "compiler" / "schemas" / "universal_score.schema.json",
        lab / "compiler" / "schemas" / "build_request.schema.json",
        lab / "compiler" / "schemas" / "provider_capability.schema.json",
        lab / "compiler" / "schemas" / "veo_provider_request.schema.json",
        lab / "compiler" / "schemas" / "capability_report.schema.json",
        lab / "compiler" / "schemas" / "loss_report.schema.json",
        lab / "compiler" / "schemas" / "verification_plan.schema.json",
        lab / "compiler" / "schemas" / "build_manifest.schema.json",
        lab / "compiler" / "providers" / "veo_3_1.yaml",
        lab / "profiles" / "universal" / "video_v1.yaml",
        lab / "profiles" / "domain",
    ]
    compiler_checks = {
        "root route": "lab/compiler/AGENTS.md" in root_agents,
        "lab route": "compiler/AGENTS.md" in agents,
        "registry owner": "compiler: compiler/" in registry,
        "registry entrypoint": "universal_score:" in registry,
        "registry reverse entrypoint": "universal_reverse_score:" in registry,
        "registry build entrypoint": "provider_build:" in registry,
        "provider capabilities": "provider_capabilities_dir:" in registry,
        "translation registry": "control_translations:" in registry,
        "universal profile": "universal_profile:" in registry,
        "domain profiles": "domain_profiles_dir:" in registry,
    }
    for label, passed in compiler_checks.items():
        if not passed:
            fail(
                f"universal compiler missing {label}",
                "route lab/compiler and its profile owners in both agent files and registry.yaml",
            )
    for path in compiler_required:
        if not path.exists():
            fail(f"required universal-score artifact missing: {path.relative_to(root)}")
    if all(compiler_checks.values()) and all(path.exists() for path in compiler_required):
        ok("one routed compiler owner has profiles, translations, score resolution, and provider builds")

    # S7: provider execution has one routed, authority-free runtime owner
    print("[S7] render-runtime routing")
    runtime_required = [
        lab / "runtime" / "AGENTS.md",
        lab / "runtime" / "README.md",
        lab / "runtime" / "requirements.txt",
        lab / "runtime" / "contracts.py",
        lab / "runtime" / "journal.py",
        lab / "runtime" / "runner.py",
        lab / "runtime" / "adapters" / "base.py",
        lab / "runtime" / "adapters" / "veo.py",
        lab / "runtime" / "schemas" / "render_job.schema.json",
        lab / "runtime" / "schemas" / "render_result.schema.json",
    ]
    runtime_checks = {
        "root route": "lab/runtime/AGENTS.md" in root_agents,
        "lab route": "runtime/AGENTS.md" in agents,
        "registry owner": "runtime: runtime/" in registry,
        "registry runner": "render_job_runner:" in registry,
        "registry journal": "render_job_journal:" in registry,
        "registry adapter": "generation_adapter_veo:" in registry,
        "runtime requirements": "runtime_requirements:" in registry,
    }
    for label, passed in runtime_checks.items():
        if not passed:
            fail(
                f"render runtime missing {label}",
                "route lab/runtime in both agent files and registry.yaml",
            )
    for path in runtime_required:
        if not path.exists():
            fail(f"required render-runtime artifact missing: {path.relative_to(root)}")
    if all(runtime_checks.values()) and all(path.exists() for path in runtime_required):
        ok("one routed runtime owns journaled provider execution without authority writes")

    # S8: verification is a separate read-only boundary over builds and render evidence
    print("[S8] render-verification routing")
    verification_required = [
        lab / "verification" / "AGENTS.md",
        lab / "verification" / "README.md",
        lab / "verification" / "verify.py",
        lab / "verification" / "schemas" / "verification_evidence_bundle.schema.json",
        lab / "verification" / "schemas" / "compliance_report.schema.json",
    ]
    verification_checks = {
        "root route": "lab/verification/AGENTS.md" in root_agents,
        "lab route": "verification/AGENTS.md" in agents,
        "registry owner": "verification: verification/" in registry,
        "registry entrypoint": "render_verification:" in registry,
    }
    for label, passed in verification_checks.items():
        if not passed:
            fail(
                f"render verification missing {label}",
                "route lab/verification in both agent files and registry.yaml",
            )
    for path in verification_required:
        if not path.exists():
            fail(f"required render-verification artifact missing: {path.relative_to(root)}")
    if all(verification_checks.values()) and all(
        path.exists() for path in verification_required
    ):
        ok("one routed verifier owns read-only compliance and bounded repair planning")

    # S9: every client transport routes through one application service
    print("[S9] application-facade routing")
    application_required = [
        root / "bin" / "cpcs",
        lab / "application" / "AGENTS.md",
        lab / "application" / "README.md",
        lab / "application" / "contracts.py",
        lab / "application" / "service.py",
        lab / "application" / "cli.py",
        lab / "application" / "mcp.py",
        lab / "application" / "http.py",
        lab / "application" / "clients.py",
        lab / "application" / "schemas" / "application_request.schema.json",
        lab / "application" / "schemas" / "application_response.schema.json",
    ]
    application_checks = {
        "root route": "lab/application/AGENTS.md" in root_agents,
        "lab route": "application/AGENTS.md" in agents,
        "registry owner": "application: application/" in registry,
        "registry service": "application_service:" in registry,
        "registry CLI": "application_cli:" in registry,
        "registry MCP": "application_mcp:" in registry,
        "registry HTTP": "application_http:" in registry,
        "guided production operation": '"cpcs.production.prepare"' in (lab / "application" / "service.py").read_text(encoding="utf-8"),
        "analysis operation": '"cpcs.analyze.run"' in (lab / "application" / "service.py").read_text(encoding="utf-8"),
        "render operation": '"cpcs.render.run"' in (lab / "application" / "service.py").read_text(encoding="utf-8"),
        "verification operation": '"cpcs.verify.run"' in (lab / "application" / "service.py").read_text(encoding="utf-8"),
        "external authorization gate": "authorization_required" in (lab / "application" / "service.py").read_text(encoding="utf-8"),
    }
    for label, passed in application_checks.items():
        if not passed:
            fail(
                f"application facade missing {label}",
                "route lab/application in both agent files and registry.yaml",
            )
    for path in application_required:
        if not path.exists():
            fail(f"required application artifact missing: {path.relative_to(root)}")
    command = root / "bin" / "cpcs"
    if command.exists() and command.stat().st_mode & 0o111 == 0:
        fail("bin/cpcs is not executable", "restore the stable command executable bit")
    if all(application_checks.values()) and all(
        path.exists() for path in application_required
    ) and command.stat().st_mode & 0o111:
        ok("one routed application service owns stable CLI, MCP, HTTP, guided production, analysis, render, verification, and client contracts")

    # S10: the bounded release has one routed policy and executable qualification system
    print("[S10] local-release routing")
    release_required = [
        root / "pyproject.toml",
        root / "setup.cfg",
        root / "MANIFEST.in",
        root / "requirements.lock",
        root / "requirements-providers.lock",
        root / ".github" / "workflows" / "validate.yml",
        lab / "release" / "AGENTS.md",
        lab / "release" / "README.md",
        lab / "release" / "policy.yaml",
        lab / "release" / "contracts.py",
        lab / "release" / "backup.py",
        lab / "release" / "migrations.py",
        lab / "release" / "security.py",
        lab / "release" / "qualification.py",
        lab / "application" / "telemetry.py",
    ]
    release_checks = {
        "root route": "lab/release/AGENTS.md" in root_agents,
        "lab route": "release/AGENTS.md" in agents,
        "registry owner": "release: release/" in registry,
        "registry backup": "release_backup:" in registry,
        "registry migrations": "release_migrations:" in registry,
        "registry security": "release_security:" in registry,
        "registry qualification": "release_qualification:" in registry,
    }
    for label, passed in release_checks.items():
        if not passed:
            fail(
                f"local release missing {label}",
                "route lab/release in both agent files and registry.yaml",
            )
    for path in release_required:
        if not path.exists():
            fail(f"required local-release artifact missing: {path.relative_to(root)}")
    if all(release_checks.values()) and all(path.exists() for path in release_required):
        ok("one routed local-release owner has locks, CI, recovery, migrations, security, and qualification")

    print()
    if FAILS:
        print(f"SYNC RED: {len(FAILS)} drift issue(s).")
        if ACTIONS:
            print("REQUIRED ACTIONS (deterministic, in order):")
            for i, a in enumerate(dict.fromkeys(ACTIONS), 1):
                print(f"  {i}. {a}")
        sys.exit(1)
    print("SYNC GREEN: repo artifacts are in sync (graph, research, cards, index, routing).")


if __name__ == "__main__":
    main()
