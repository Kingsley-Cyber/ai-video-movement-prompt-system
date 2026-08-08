"""Build a deterministic, authority-aware operating brief for a CPCS agent."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lab.second_brain.src.validate import sha256_value


AGENT_BRIEF_POLICY = "cpcs-agent-brief/1.17"
ROLE_LEVEL = {"chat": 0, "operator": 1, "curator": 2}
SECRET_PATTERNS = (
    re.compile(r"\btlk_[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bTWELVE_LABS_API_KEY\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\bPOLYMATH_(?:API_KEY|TOKEN)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\bCPCS_NEO4J_PASSWORD\s*[:=]\s*\S+", re.IGNORECASE),
)


@dataclass(frozen=True)
class Workflow:
    workflow_id: str
    label: str
    triggers: tuple[str, ...]
    routes: tuple[tuple[str, str], ...]
    operations: tuple[str, ...]
    phases: tuple[tuple[str, str, tuple[str, ...], bool], ...]


WORKFLOWS = (
    Workflow(
        "repository_orientation",
        "repository orientation and tool discovery",
        (),
        (
            ("AGENTS.md", "Root governance and task routing"),
            ("README.md", "Human product orientation and supported entry points"),
            ("ARCHITECTURE.md", "Normative architecture, current state, and verified gaps"),
            ("lab/application/AGENTS.md", "Public application and MCP boundary"),
            ("lab/registry.yaml", "Active implementation and artifact pointers"),
        ),
        ("cpcs.agent.brief", "cpcs.status"),
        (
            (
                "orient",
                "Read only the selected owners, inspect the role-filtered tool catalog, and confirm current authority status.",
                ("cpcs.status",),
                False,
            ),
        ),
    ),
    Workflow(
        "terminology_resolution",
        "canonical identifier and homonym resolution",
        (
            "terminology",
            "homonym",
            "identifier resolution",
            "sense resolution",
            "au1",
            "au01",
            "action unit",
            "follow through",
        ),
        (
            ("lab/second_brain/AGENTS.md", "Terminology, source, graph, and authority boundaries"),
            ("lab/second_brain/curated/ontology_registry.json", "Closed identifier rules and candidate senses"),
            ("ARCHITECTURE.md", "Current terminology implementation and remaining coverage"),
        ),
        (
            "cpcs.terminology.resolve",
            "cpcs.source.resolve",
            "cpcs.terminology.propose",
            "cpcs.terminology.inspect",
            "cpcs.reason",
        ),
        (
            (
                "detect_terminology",
                "Normalize registered identifiers and detect homonyms before graph traversal. Deterministic context may resolve one sense; a tie must remain closed.",
                ("cpcs.terminology.resolve",),
                False,
            ),
            (
                "resolve_source_backed_sense",
                "For an unresolved match, inspect exact source units, select only one returned candidate sense, preserve uncertainty, and stage the choice for this exact query. Do not edit or promote the ontology registry.",
                ("cpcs.source.resolve", "cpcs.terminology.propose", "cpcs.terminology.inspect"),
                False,
            ),
            (
                "reason_with_bounded_sense",
                "Pass the current proposal ID to cpcs.reason. The reasoner admits the selected sense, rejects competing homonym roots, and labels the choice interpreted rather than curated.",
                ("cpcs.reason",),
                False,
            ),
        ),
    ),
    Workflow(
        "twelvelabs_analysis",
        "Pegasus and TwelveLabs analysis",
        (
            "pegasus",
            "twelvelabs",
            "12labs",
            "api key",
            "video analysis",
            "analyze video",
            "analyze asset",
            "atomic extraction",
            "atomic video",
            "rerun atomic",
            "jockey",
            "marengo",
            "segment sdk",
        ),
        (
            ("lab/RUNBOOK_pegasus_extraction.md", "Authorized video-analysis procedure"),
            ("lab/second_brain/AGENTS.md", "Evidence, provider, VOG, and authority boundaries"),
            ("lab/application/README.md", "Public analysis and verification operations"),
        ),
        (
            "cpcs.analyze.atomic.prepare",
            "cpcs.analyze.run",
            "cpcs.analyze.cascade",
            "cpcs.verify.asset.prepare",
            "cpcs.verify.analysis.prepare",
            "cpcs.verify.run",
            "cpcs.measure.pose.prepare",
            "cpcs.measure.pose.run",
            "cpcs.measure.normalize",
        ),
        (
            (
                "provider_readiness",
                "Confirm authorized source bytes, local media bounds, SDK readiness, and environment-only credentials.",
                (),
                False,
            ),
            (
                "plan_atomic_analysis",
                "Select a fixed fast, standard, or research profile set and inspect its exact provider-call count before execution.",
                ("cpcs.analyze.atomic.prepare",),
                False,
            ),
            (
                "semantic_analysis",
                "Run one source-bounded TwelveLabs job when diagnosing or qualifying an individual surface; the atomic cascade normally owns multi-profile execution.",
                ("cpcs.analyze.run",),
                True,
            ),
            (
                "evidence_fusion",
                "Fuse reviewed semantic and optional local measurement lanes, then append immutable evidence only with curator authorization.",
                ("cpcs.analyze.cascade",),
                True,
            ),
        ),
    ),
    Workflow(
        "research_distillation",
        "bounded research distillation",
        (
            "research",
            "rag",
            "knowledge base",
            "knowledge graph",
            "knowledge maintenance",
            "brain health",
            "core memory",
            "stale knowledge",
            "knowledge decay",
            "concept",
            "distill",
            "ingest",
            "research delta",
            "impact plan",
            "operational claim",
            "markdown file",
            "md file",
            "polymath",
            "source closure",
            "source context",
            "exact research",
            "unanswered question",
            "ontology placement",
            "graph growth",
        ),
        (
            ("lab/second_brain/AGENTS.md", "Research evidence and promotion control plane"),
            ("AGENT_PROMPT.md", "Semantic-worker workflow guidance"),
            ("lab/CONCEPT_INDEX.md", "Current research coverage"),
        ),
        (
            "cpcs.research.source.register",
            "cpcs.research.source.inspect",
            "cpcs.source.status",
            "cpcs.source.resolve",
            "cpcs.terminology.resolve",
            "cpcs.terminology.propose",
            "cpcs.terminology.inspect",
            "cpcs.research.packet.list",
            "cpcs.research.packet.read",
            "cpcs.research.extraction.submit",
            "cpcs.research.extraction.status",
            "cpcs.research.coverage.inspect",
            "cpcs.research.proposals.list",
            "cpcs.research.proposals.validate",
            "cpcs.research.distillation.run",
            "cpcs.research.placement.plan",
            "cpcs.research.placement.inspect",
            "cpcs.research.promotion.prepare",
            "cpcs.research.source.units.admit",
            "cpcs.research.delta.prepare",
            "cpcs.research.delta.inspect",
            "cpcs.research.delta.patch.prepare",
            "cpcs.research.delta.patch.execute",
            "cpcs.research.delta.patch.inspect",
            "cpcs.research.delta.patch.discard",
            "cpcs.curate.promote",
            "cpcs.brain.health",
            "cpcs.maintenance.prepare",
            "cpcs.maintenance.status",
            "cpcs.maintenance.advance",
        ),
        (
            (
                "inspect_source_closure",
                "Inspect which concepts already resolve to preserved local research and dereference exact passages before requesting external retrieval.",
                ("cpcs.source.status", "cpcs.source.resolve"),
                False,
            ),
            (
                "register_research",
                "Register exact authorized bytes and open one content-bound extraction session.",
                ("cpcs.research.source.register", "cpcs.research.source.inspect"),
                False,
            ),
            (
                "extract_bounded_packets",
                "Read bounded packets and submit either typed source-closed proposals or one evidence-linked no-candidate disposition that accounts for every packet passage.",
                (
                    "cpcs.research.packet.list",
                    "cpcs.research.packet.read",
                    "cpcs.research.extraction.submit",
                    "cpcs.research.coverage.inspect",
                    "cpcs.research.proposals.validate",
                ),
                False,
            ),
            (
                "admit_source_units",
                "After complete packet coverage, explicitly authorize one immutable append of every verified source passage so future agents can work without the retrieval provider.",
                ("cpcs.research.source.units.admit",),
                False,
            ),
            (
                "stage_research",
                "Inspect each extraction terminology control, resolve an open sense only from exact source units and the returned closed candidates, then pass that proposal ID to placement. Run deterministic edge-family and placement admission and prepare the review packet without changing curated authority.",
                (
                    "cpcs.terminology.resolve",
                    "cpcs.source.resolve",
                    "cpcs.terminology.propose",
                    "cpcs.terminology.inspect",
                    "cpcs.research.distillation.run",
                    "cpcs.research.placement.plan",
                    "cpcs.research.placement.inspect",
                    "cpcs.research.promotion.prepare",
                ),
                False,
            ),
            (
                "plan_research_delta",
                "Select source-bound claim candidates, classify their evidence and change scope, then resolve existing owners, contracts, tests, and patch boundaries into an operational proposal only.",
                (
                    "cpcs.research.delta.prepare",
                    "cpcs.research.delta.inspect",
                ),
                False,
            ),
            (
                "qualify_research_delta_patch",
                "Capture a proposal-scoped unified diff, require exact owner authorization for isolated execution, inspect the gate receipt, and explicitly discard the detached worktree after review. This phase never merges, pushes, or promotes.",
                (
                    "cpcs.research.delta.patch.prepare",
                    "cpcs.research.delta.patch.execute",
                    "cpcs.research.delta.patch.inspect",
                    "cpcs.research.delta.patch.discard",
                ),
                True,
            ),
            (
                "promote_research",
                "Promote only the explicitly reviewed proposal set with request-bound curator authorization.",
                ("cpcs.curate.promote",),
                True,
            ),
            (
                "maintain_brain",
                "Build the revision-bound health report, seal a selective rebuild plan, advance its hash-chained transitions, and submit the validated Neo4j snapshot only when that exact external effect is authorized.",
                (
                    "cpcs.brain.health",
                    "cpcs.maintenance.prepare",
                    "cpcs.maintenance.status",
                    "cpcs.maintenance.advance",
                ),
                True,
            ),
        ),
    ),
    Workflow(
        "directing_compilation",
        "natural-language and structured directing compilation",
        (
            "prompt",
            "natural language",
            "yaml",
            "json",
            "xml",
            "coding language",
            "directing strategy",
            "video generation",
        ),
        (
            ("lab/AGENTS.md", "Prompt composition and experiment routing"),
            ("lab/FORMAT_CONTROL_MAP.md", "Format ownership and projection guidance"),
            ("lab/compiler/AGENTS.md", "Canonical score and provider-build ownership"),
            ("lab/blocks.yaml", "Current modular prompt ingredients"),
        ),
        (
            "cpcs.intent.normalize",
            "cpcs.intent.context",
            "cpcs.context.get",
            "cpcs.source.resolve",
            "cpcs.terminology.resolve",
            "cpcs.terminology.propose",
            "cpcs.terminology.inspect",
            "cpcs.knowledge.search",
            "cpcs.reason",
            "cpcs.strategy.compile",
            "cpcs.score.build",
            "cpcs.build.compile",
        ),
        (
            (
                "normalize_and_retrieve",
                "Normalize ordinary language and inspect the context terminology handoff. If a registered homonym remains open, cite exact source units, stage one returned sense, and rebuild the context with that proposal ID before strategy or score admission. Retrieve only relevant source-traceable controls.",
                (
                    "cpcs.intent.context",
                    "cpcs.terminology.resolve",
                    "cpcs.source.resolve",
                    "cpcs.terminology.propose",
                    "cpcs.terminology.inspect",
                    "cpcs.context.get",
                    "cpcs.knowledge.search",
                    "cpcs.reason",
                    "cpcs.strategy.compile",
                ),
                False,
            ),
            (
                "compile_strategy",
                "Select one evidence-bounded reasoning policy, emit a provider-neutral directing strategy, resolve the canonical JSON score, then compile labelled build projections.",
                ("cpcs.strategy.compile", "cpcs.score.build", "cpcs.build.compile"),
                False,
            ),
        ),
    ),
    Workflow(
        "provider_execution",
        "journaled provider execution",
        ("render", "provider execution", "generate the video", "veo", "production job"),
        (
            ("lab/runtime/AGENTS.md", "Provider execution, replay, and cancellation"),
            ("lab/compiler/AGENTS.md", "Provider build preparation"),
        ),
        (
            "cpcs.production.prepare",
            "cpcs.render.create",
            "cpcs.render.run",
            "cpcs.render.show",
            "cpcs.render.events",
        ),
        (
            (
                "prepare_generation",
                "Create one canonical score and materialized provider build without submitting it.",
                ("cpcs.production.prepare", "cpcs.render.create"),
                False,
            ),
            (
                "execute_generation",
                "Submit through the journaled provider boundary and inspect the saved result and event chain.",
                ("cpcs.render.run", "cpcs.render.show", "cpcs.render.events"),
                False,
            ),
        ),
    ),
    Workflow(
        "render_evidence_workflow",
        "journaled render-to-evidence workflow",
        (
            "end-to-end render",
            "render to evidence",
            "render-to-evidence",
            "render evidence workflow",
            "journaled workflow",
            "no manual bridge",
            "resume workflow",
            "recover workflow",
        ),
        (
            ("lab/application/AGENTS.md", "Cross-system workflow and public-operation boundary"),
            ("lab/runtime/AGENTS.md", "Journaled provider execution and cancellation"),
            ("lab/verification/AGENTS.md", "Evidence comparison and bounded repair"),
            ("lab/second_brain/AGENTS.md", "Immutable evidence and testimonial authority"),
            ("REPO_CONTINUITY_IMPLEMENTATION_PLAN.md", "Workflow qualification order and remaining live gates"),
        ),
        (
            "cpcs.workflow.render.prepare",
            "cpcs.workflow.render.status",
            "cpcs.workflow.render.advance",
            "cpcs.workflow.render.review",
            "cpcs.workflow.render.cancel",
        ),
        (
            (
                "prepare_render_evidence_workflow",
                "Bind one sealed experiment arm, materialized provider build, exact artifact destination, analysis settings, optional measurement lane, and verification metrics without submitting or admitting evidence.",
                ("cpcs.workflow.render.prepare", "cpcs.workflow.render.status"),
                False,
            ),
            (
                "advance_render_evidence_workflow",
                "Authorize the exact persisted state and next-step hash, advance one fixed step, then inspect status before authorizing another effect.",
                ("cpcs.workflow.render.advance", "cpcs.workflow.render.status"),
                False,
            ),
            (
                "review_render_evidence_workflow",
                "At the human stop, preserve the exact statement and submit its quote-spanned reviewed normalization against the current workflow state. Follow status.metric_requirements: every sealed scalar not exactly owned by a conclusive compliance status needs one matching normalization.metric_findings entry bound to a sealed concept or canonical control.",
                ("cpcs.workflow.render.review", "cpcs.workflow.render.status"),
                True,
            ),
            (
                "cancel_render_evidence_workflow",
                "Cancel only the exact current workflow state through the existing provider cancellation boundary, then retain the terminal recovery trail.",
                ("cpcs.workflow.render.cancel", "cpcs.workflow.render.status"),
                True,
            ),
        ),
    ),
    Workflow(
        "graph_projection",
        "CPCS Neo4j projection and parity",
        (
            "neo4j",
            "graph projection",
            "graph sync",
            "graph parity",
            "hot load",
            "rebuild graph",
        ),
        (
            ("lab/second_brain/AGENTS.md", "Graph authority, synchronization, and query boundaries"),
            ("REPO_CONTINUITY_IMPLEMENTATION_PLAN.md", "Neo4j projection target and qualification order"),
            ("ARCHITECTURE.md", "Current projection status and residual limits"),
            ("lab/second_brain/neo4j.compose.yaml", "Pinned local CPCS-owned deployment"),
        ),
        (
            "cpcs.graph.projection.plan",
            "cpcs.graph.projection.status",
            "cpcs.graph.projection.sync",
            "cpcs.graph.projection.parity",
            "cpcs.reason",
        ),
        (
            (
                "inspect_projection",
                "Build the no-write Git projection plan and inspect the configured active generation before any synchronization.",
                ("cpcs.graph.projection.plan", "cpcs.graph.projection.status"),
                False,
            ),
            (
                "sync_exact_snapshot",
                "Authorize only the inspected snapshot hash, then run the idempotent namespace-bounded synchronization operation.",
                ("cpcs.graph.projection.sync",),
                True,
            ),
            (
                "verify_shadow_parity",
                "Compare bounded reasoning responses against NetworkX before selecting Neo4j or shadow mode for an application process.",
                ("cpcs.graph.projection.parity", "cpcs.reason"),
                False,
            ),
        ),
    ),
    Workflow(
        "evaluator_stability",
        "evaluator drift and held-out optimization stability",
        (
            "evaluator drift",
            "held-out",
            "held out",
            "metric gaming",
            "recursive degradation",
            "recursive optimization",
            "calibration stability",
        ),
        (
            ("lab/release/AGENTS.md", "Qualification evidence and release authority boundary"),
            ("lab/release/stability.py", "Deterministic evaluator-stability owner"),
            ("REPO_CONTINUITY_IMPLEMENTATION_PLAN.md", "Qualification order and remaining external gates"),
        ),
        (
            "cpcs.qualification.stability.evaluate",
            "cpcs.qualification.stability.inspect",
        ),
        (
            (
                "evaluate_evaluator_stability",
                "Compare versioned evaluator identities against source-bound human calibration and disjoint held-out optimization cases.",
                ("cpcs.qualification.stability.evaluate",),
                False,
            ),
            (
                "inspect_evaluator_stability",
                "Replay the stored report, inspect every failed check, and pass its complete request-named artifact closure to a separately trusted qualification evaluator.",
                ("cpcs.qualification.stability.inspect",),
                False,
            ),
        ),
    ),
    Workflow(
        "reference_candidate_comparison",
        "exact-media reference and candidate comparison",
        (
            "side by side",
            "side-by-side",
            "left right comparison",
            "compare reference",
            "compare candidate",
            "reference fidelity",
            "recreation fidelity",
        ),
        (
            ("lab/RUNBOOK_reference_to_kinematic_truth.md", "Reference reconstruction and comparison procedure"),
            ("lab/verification/AGENTS.md", "Exact-media comparison and evidence boundaries"),
            ("lab/compiler/AGENTS.md", "Canonical score and rebuilt prompt ownership"),
            ("lab/AGENTS.md", "Unrendered variant and experiment discipline"),
        ),
        (
            "cpcs.video.compare.prepare",
            "cpcs.video.compare.status",
            "cpcs.video.compare.advance",
            "cpcs.video.compare.inspect",
            "cpcs.video.compare.cancel",
            "cpcs.verify.reference.compare",
            "cpcs.video.research_gaps",
            "cpcs.video.comparison.lens",
            "cpcs.video.bridge.promote",
        ),
        (
            (
                "prepare_video_comparison",
                "Bind both authorized video hashes and intervals, build identical atomic Pegasus plans, freeze the provider-call maximum, and inspect the next-step hash without provider contact.",
                ("cpcs.video.compare.prepare", "cpcs.video.compare.status"),
                False,
            ),
            (
                "advance_video_comparison",
                "Authorize one returned step hash at a time so reference and candidate cascades remain operational-only, VOG-separated, receipt-backed, and replayable without another provider call.",
                ("cpcs.video.compare.advance", "cpcs.video.compare.cancel"),
                True,
            ),
            (
                "inspect_video_comparison",
                "Inspect the final paired VOG lineage, optional same-tool local measurements, deterministic differences, and left-reference/right-candidate visual record.",
                ("cpcs.video.compare.inspect",),
                False,
            ),
            (
                "apply_knowledge_lens",
                "Before or after the paired workflow, freeze a graph-grounded comparison lens, inspect Pegasus research gaps, and promote an observation-to-concept bridge only after exact source-bound review.",
                (
                    "cpcs.video.comparison.lens",
                    "cpcs.video.research_gaps",
                    "cpcs.video.bridge.promote",
                ),
                True,
            ),
            (
                "compare_existing_evidence",
                "Use the lower-level verifier directly only when both analyses and optional local artifacts already exist and are hash bound.",
                ("cpcs.verify.reference.compare",),
                False,
            ),
            (
                "rebuild_through_canonical_authority",
                "Carry reviewed comparison targets into the existing canonical score and compiler owners; do not treat the report or a hand-written projection as authority or qualification.",
                (),
                False,
            ),
        ),
    ),
    Workflow(
        "verification_and_learning",
        "render verification and controlled learning",
        (
            "verify",
            "verification",
            "compare render",
            "experiment",
            "reflection",
            "learn from",
            "testimonial",
            "human feedback",
            "director feedback",
            "good outcome",
            "bad outcome",
            "mixed outcome",
            "outcome memory",
            "failure card",
            "no go",
            "run remarks",
        ),
        (
            ("lab/verification/AGENTS.md", "Evidence comparison and bounded repair"),
            ("lab/runtime/AGENTS.md", "Exact render artifact ownership"),
        ),
        (
            "cpcs.verify.asset.prepare",
            "cpcs.verify.analysis.prepare",
            "cpcs.verify.run",
            "cpcs.experiment.prepare",
            "cpcs.experiment.seal",
            "cpcs.record.testimonial.capture",
            "cpcs.record.testimonial.review",
            "cpcs.testimonial.inspect",
            "cpcs.experiment.accept",
        ),
        (
            (
                "verify_output",
                "Bind analysis to the exact artifact and compare semantic, measured, and human evidence without flattening conflicts.",
                (
                    "cpcs.verify.asset.prepare",
                    "cpcs.verify.analysis.prepare",
                    "cpcs.verify.run",
                ),
                False,
            ),
            (
                "capture_human_feedback",
                "Capture the exact statement against verified artifact bytes, append a quote-spanned reviewed normalization with one exact metric finding for each human-owned sealed metric, and inspect correction lineage before selecting that review for an experiment receipt.",
                (
                    "cpcs.record.testimonial.capture",
                    "cpcs.record.testimonial.review",
                    "cpcs.testimonial.inspect",
                ),
                True,
            ),
            (
                "record_learning",
                "Seal the flight, then submit every conclusive arm and its current testimonial review through the accepted-experiment gate. That gate preflights completeness, records runs, invokes the existing reflector, stages typed candidates, and proves replay without promoting knowledge.",
                (
                    "cpcs.experiment.prepare",
                    "cpcs.experiment.seal",
                    "cpcs.experiment.accept",
                ),
                True,
            ),
        ),
    ),
)


OPERATION_PURPOSES = {
    operation: phase[1]
    for workflow in WORKFLOWS
    for phase in workflow.phases
    for operation in phase[2]
}
OPERATION_PURPOSES.update(
    {
        "cpcs.agent.brief": "Regenerate this task-scoped operating contract.",
        "cpcs.status": "Inspect runtime, authority, integration, and role boundaries.",
        "cpcs.intent.normalize": "Inspect provider-neutral intent without retrieving or compiling.",
        "cpcs.terminology.resolve": "Normalize registered identifiers and return closed homonym candidates before traversal.",
        "cpcs.terminology.propose": "Stage one exact-query source-backed agent sense choice without changing canonical authority.",
        "cpcs.terminology.inspect": "Recompute the proposal's registry, source, and closed-sense checks before query use.",
        "cpcs.research.extraction.status": "Inspect packet progress and captured-response hashes.",
        "cpcs.research.extraction.submit": "Capture one complete packet result: candidates with source evidence, or an explicit no-candidate reason with exact passage coverage.",
        "cpcs.research.proposals.list": "Review untrusted proposals before validation or staging.",
        "cpcs.measure.pose.prepare": "Bind exact media and detector bytes for local measurement.",
        "cpcs.measure.pose.run": "Produce reviewable detected 2D measurement candidates.",
        "cpcs.measure.normalize": "Project selected immutable measurements into VOG observations.",
        "cpcs.analyze.atomic.prepare": "Create a replay-stable fast, standard, or research extraction plan without spending provider calls.",
        "cpcs.experiment.accept": "Accept all complete reviewed arms once, invoke the existing reflector, and record evidence, derived diffs, and unreviewed improvement candidates.",
        "cpcs.graph.projection.plan": "Hash the validated all-version Git reasoning graph without contacting Neo4j.",
        "cpcs.graph.projection.status": "Inspect the isolated projection generation without returning credentials or Cypher.",
        "cpcs.graph.projection.sync": "Synchronize only the exact authorized snapshot into the CPCS namespace.",
        "cpcs.graph.projection.parity": "Compare bounded reasoning outputs from Neo4j and NetworkX before backend adoption.",
        "cpcs.workflow.render.prepare": "Create one content-bound workflow without submitting a render or admitting evidence.",
        "cpcs.workflow.render.status": "Inspect the redacted workflow state, exact next-step hash, recovery action, and immutable outcome reference.",
        "cpcs.workflow.render.advance": "Advance exactly one fixed render, analysis, measurement, verification, or recording step under request-bound authorization.",
        "cpcs.workflow.render.review": "Supply exact human testimony and its reviewed normalization only at the workflow human-review stop.",
        "cpcs.workflow.render.cancel": "Cancel the exact current workflow through the existing journaled provider boundary.",
        "cpcs.video.compare.prepare": "Create identical source-bound atomic plans and a fixed paired provider-call schedule without provider contact.",
        "cpcs.video.compare.status": "Inspect paired step, VOG, measurement, provider-call, and recovery state without exposing local paths.",
        "cpcs.video.compare.advance": "Advance one fixed operational-only analysis, same-tool measurement, or verifier step under exact authorization.",
        "cpcs.video.compare.inspect": "Read the completed operational comparison report and separate VOG lineage.",
        "cpcs.video.compare.cancel": "Cancel the paired workflow between synchronous child steps while retaining receipts.",
        "cpcs.qualification.stability.evaluate": "Detect evaluator drift, held-out score disagreement, and recursive optimization collapse without granting qualification.",
        "cpcs.qualification.stability.inspect": "Replay and inspect one source-bound supporting-evidence report.",
    }
)


def _normalize_task(task: str) -> str:
    return re.sub(r"\s+", " ", task.strip().lower())


def _reject_secret_text(task: str) -> None:
    if any(pattern.search(task) for pattern in SECRET_PATTERNS):
        raise ValueError(
            "task contains a credential-shaped value; keep secrets in the process environment"
        )


def _select_workflows(task: str) -> list[Workflow]:
    normalized = _normalize_task(task)
    selected = [WORKFLOWS[0]]
    selected.extend(
        workflow
        for workflow in WORKFLOWS[1:]
        if any(trigger in normalized for trigger in workflow.triggers)
    )
    return selected


def _route_record(root: Path, workflow_id: str, path_text: str, reason: str) -> dict[str, Any]:
    path = root / path_text
    exists = path.is_file()
    content_hash = None
    if exists:
        content_hash = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "workflow_id": workflow_id,
        "path": path_text,
        "reason": reason,
        "exists": exists,
        "content_hash": content_hash,
    }


def _deduplicated_routes(root: Path, workflows: list[Workflow]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for workflow in workflows:
        for path_text, reason in workflow.routes:
            if path_text in seen:
                continue
            seen.add(path_text)
            rows.append(_route_record(root, workflow.workflow_id, path_text, reason))
    return rows


def _operation_rows(
    workflows: list[Workflow],
    requested_role: str,
    operation_catalog: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    catalog = {row["name"]: row for row in operation_catalog}
    selected_names: list[str] = []
    for workflow in workflows:
        for name in workflow.operations:
            if name not in selected_names:
                selected_names.append(name)
    missing = [name for name in selected_names if name not in catalog]
    if missing:
        raise ValueError("agent brief references unknown operations: " + ", ".join(missing))
    rows = []
    for name in selected_names:
        operation = catalog[name]
        required_role = operation["required_role"]
        rows.append(
            {
                "name": name,
                "purpose": OPERATION_PURPOSES[name],
                "required_role": required_role,
                "available_to_requested_role": (
                    ROLE_LEVEL[requested_role] >= ROLE_LEVEL[required_role]
                ),
                "mutation_scope": operation["mutation_scope"],
                "authorization_required": operation["authorization_required"],
                "mcp_exposed": operation["mcp_exposed"],
            }
        )
    return rows


def _phase_rows(
    workflows: list[Workflow], operation_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    operations = {row["name"]: row for row in operation_rows}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for workflow in workflows:
        for phase_id, objective, operation_names, optional in workflow.phases:
            if phase_id in seen:
                continue
            seen.add(phase_id)
            phase_operations = [operations[name] for name in operation_names]
            rows.append(
                {
                    "index": len(rows) + 1,
                    "phase_id": phase_id,
                    "workflow_id": workflow.workflow_id,
                    "objective": objective,
                    "operations": list(operation_names),
                    "optional": optional,
                    "minimum_role": max(
                        (row["required_role"] for row in phase_operations),
                        key=lambda role: ROLE_LEVEL[role],
                        default="chat",
                    ),
                    "authorization_required": any(
                        row["authorization_required"] for row in phase_operations
                    ),
                    "stop_condition": (
                        "Stop for exact human authorization before this phase."
                        if any(row["authorization_required"] for row in phase_operations)
                        else "Stop on a schema error, missing evidence, unresolved authority conflict, or failed replay check."
                    ),
                }
            )
    return rows


def _natural_brief(
    task: str,
    requested_role: str,
    workflows: list[Workflow],
    phases: list[dict[str, Any]],
) -> str:
    workflow_labels = ", ".join(workflow.label for workflow in workflows)
    blocked = [
        phase["phase_id"]
        for phase in phases
        if ROLE_LEVEL[requested_role] < ROLE_LEVEL[phase["minimum_role"]]
    ]
    blocked_text = (
        " The requested role cannot run these phases: " + ", ".join(blocked) + "."
        if blocked
        else " The requested role can discover every listed phase, but controlled side effects still need exact authorization."
    )
    return (
        "CPCS is one provider-neutral creative-reasoning system. For this task, load only the "
        f"routed owners and use these workflows: {workflow_labels}. Start with status and tool "
        "discovery, keep source evidence separate from repository authority, and use the canonical "
        "JSON score as semantic truth. Inspect cpcs.source.status and use cpcs.source.resolve before "
        "requesting Polymath. cpcs.context.get dereferences selected concepts into hash-verified local "
        "passages and reports an exact local source-answer disposition for graph gaps. A quarantined "
        "reference is not evidence. Admit completed-session source units before reviewed promotion so "
        "future agents can reproduce the lineage without the retrieval provider. Natural language is a readable summary. YAML and XML are "
        "labelled projections for configuration and ordered control; they cannot add unsupported "
        "meaning. For atomic video extraction, prepare a fixed mode first: fast is orientation, "
        "standard is directing coverage, and research adds quality and contradiction review. "
        "Inspect the declared provider-call count and start with one worker until account-specific "
        "concurrency is qualified. Pegasus output is interpreted semantic evidence unless a separate local "
        "measurement supplies the claimed value. Supply API credentials only through the process "
        "environment at the provider boundary. Never place them in prompts, tool arguments, files, "
        "logs, telemetry, or commits. Preserve human feedback verbatim before normalization, ground every "
        "finding in exact source spans, bind every human-scored metric to the same scalar value and a sealed "
        "concept or canonical control, and treat attribution as an unverified candidate until an isolated "
        "experiment supports it. Never reflect automatically from one render, a partial arm set, raw measurement, "
        "an LLM diagnosis, or an unreviewed testimonial. Use cpcs.experiment.accept only after every sealed arm is "
        "complete and explicitly accepted. For a render-to-evidence workflow, prepare once, inspect status, "
        "authorize only the returned state and next-step hashes, advance one step, and stop at awaiting_review "
        "for exact human testimony. Resume the same workflow after interruption; never create an alternate child "
        "operation, prompt, or evidence store. "
        "For direct video comparison, prepare one paired workflow, authorize only its returned step hash, keep "
        "both VOGs separate, and inspect the operational report after completion. The workflow may use one shared "
        "local measurement configuration, but it cannot record observations or promote research. "
        "Treat second-brain maintenance as a first-class task: inspect current status, coverage, temporal scope, retrieval gaps, "
        "and projection state before relying on knowledge; keep core memory concise and source-linked; and return "
        "an exact source answer or explicit gap instead of inventing a missing graph fact. Use cpcs.brain.health and the "
        "resumable cpcs.maintenance.* transitions for selective rebuilds; Neo4j submission still requires exact authorization. Preserve good, bad, "
        "The unified health and maintenance-state contracts remain planned for promotion-spanning repair and cancellation; "
        "the implemented inspect, rebuild, projection, and qualification path must not be generalized beyond its closed states. "
        "mixed, inconclusive, and reviewed no-go outcomes with exact remarks, dimensions, limitations, tested "
        "deltas, and evidence scope. Derived positives and negatives may change rank only inside scope; a hard "
        "no-go requires a reviewed failure card or curated rule. For evaluator changes, "
        "bind both evaluator identities, keep "
        "optimization cases disjoint from held-out cases, and require human calibration evidence before a "
        "stability report can support qualification. External qualification must verify every request-named "
        f"artifact byte, not only the report. Task: {task}.{blocked_text}"
    )


def build_agent_brief(
    arguments: dict[str, Any],
    *,
    operation_catalog: list[dict[str, Any]],
    application_policy: str,
    root: Path,
) -> dict[str, Any]:
    """Return one replay-stable operating contract with no authority mutation."""
    task = arguments["task"].strip()
    _reject_secret_text(task)
    requested_role = arguments.get("role", "chat")
    workflows = _select_workflows(task)
    routes = _deduplicated_routes(root, workflows)
    operations = _operation_rows(workflows, requested_role, operation_catalog)
    phases = _phase_rows(workflows, operations)
    brief: dict[str, Any] = {
        "schema": "cpcs.agent_brief/1.0",
        "brief_id": "pending",
        "request": {"task": task, "requested_role": requested_role},
        "repository": {
            "project": "CPCS",
            "product": "Creative Reasoning Operating System for AI Video Generation",
            "governance_entrypoint": "AGENTS.md",
            "architecture_owner": "ARCHITECTURE.md",
            "canonical_semantic_authority": "fully resolved CPCS Universal Score in canonical JSON",
            "production_authority": "disabled_until_all_categorical_release_gates_pass",
        },
        "task_routing": {
            "selected_workflows": [workflow.workflow_id for workflow in workflows],
            "routes": routes,
            "unresolved_inputs": [
                "Exact source rights, media path or asset ID, provider/model target, and desired authority effect must be supplied when the selected operation requires them."
            ],
        },
        "agent_method": [
            {
                "method": "self_orientation",
                "instruction": "Read routed owners and discover the live role-filtered catalog before planning calls.",
            },
            {
                "method": "task_conditioned_routing",
                "instruction": "Load only task-relevant owners and operations; do not invent a parallel workflow or ontology.",
            },
            {
                "method": "bounded_context",
                "instruction": "Give a semantic worker source-located packets, not an entire large document or unrestricted store.",
            },
            {
                "method": "typed_plan_act_observe_verify",
                "instruction": "Validate each request, inspect each typed response, preserve errors, and verify replay before the next authority effect.",
            },
            {
                "method": "epistemic_separation",
                "instruction": "Keep authored, measured, detected, inferred, interpreted, simulated, and derived evidence classes distinct.",
            },
            {
                "method": "knowledge_maintenance",
                "instruction": "Use cpcs.brain.health and cpcs.maintenance.* to inspect freshness, semantic coverage, provenance, retrieval gaps, outcome direction, and projection readiness; trace missing answers to exact source evidence, keep FACS as one canary rather than the ontology boundary, preserve every hash-chained transition receipt, and never claim planned maintenance contracts for promotion-spanning repair or cancellation.",
            },
            {
                "method": "authority_aware_stop",
                "instruction": "Stop before external spending, curated promotion, or immutable admission until exact human authorization is present.",
            },
        ],
        "operations": operations,
        "execution_plan": phases,
        "credential_policy": {
            "environment_variables": [
                "TWELVE_LABS_API_KEY",
                "TWELVE_LABS_KNOWLEDGE_STORE_ID",
                "CPCS_NEO4J_URI",
                "CPCS_NEO4J_USER",
                "CPCS_NEO4J_PASSWORD",
                "CPCS_NEO4J_DATABASE",
                "CPCS_NEO4J_NAMESPACE",
                "CPCS_NEO4J_OWNERSHIP",
                "CPCS_GRAPH_BACKEND",
                "CPCS_GRAPH_FALLBACK",
            ],
            "allowed_channel": "process environment populated from an OS keychain or secret manager outside the repository",
            "forbidden_channels": [
                "agent prompt or context",
                "MCP or CLI arguments",
                "job JSON, YAML, or XML",
                "source, work artifacts, logs, telemetry, tests, commits, or chat output",
            ],
            "readiness_output": "configuration booleans and SDK/API versions only",
        },
        "serialization_policy": {
            "semantic_authority": "canonical_json",
            "natural_language": "Human-facing intent, evidence-qualified summary, and limitations.",
            "json": "Typed canonical fields, numeric controls, arrays, hashes, and provenance.",
            "yaml": "Readable intent, configuration, profile choices, and sparse control projection.",
            "xml": "Ordered hierarchy, beats, triggers, dialogue, and sequencing projection.",
            "projection_rule": "Every non-canonical format names its canonical source, capability disposition, loss, and verification need. No projection may add meaning.",
            "provider_scope_rule": "Format performance is provider, model, task, version, duration, budget, and evidence scoped.",
        },
        "command_templates": [
            {
                "purpose": "Inspect chat-safe runtime status",
                "command": "./bin/cpcs status",
                "writes": "none",
            },
            {
                "purpose": "Generate a task-specific brief",
                "command": "./bin/cpcs agent.brief <<'JSON'\n{\"task\":\"<task>\",\"role\":\"<chat|operator|curator>\"}\nJSON",
                "writes": "none",
            },
            {
                "purpose": "Prepare a deterministic atomic extraction plan",
                "command": "./bin/cpcs analyze.atomic.prepare --role operator --input work/twelvelabs/atomic-request.json",
                "writes": "none",
            },
            {
                "purpose": "Inspect secret-safe TwelveLabs readiness",
                "command": "python3 -m lab.second_brain.src.pegasus doctor",
                "writes": "none",
            },
            {
                "purpose": "Inspect the deterministic Neo4j projection plan",
                "command": "./bin/cpcs graph.projection.plan --role operator",
                "writes": "none",
            },
            {
                "purpose": "Inspect a journaled render-to-evidence workflow",
                "command": "./bin/cpcs workflow.render.status --role operator --input work/workflows/status-request.json",
                "writes": "none",
            },
            {
                "purpose": "Run the repository validation gate",
                "command": "python3 lab/scripts/validate_repo.py",
                "writes": "derived files only when a routed owner explicitly requests regeneration",
            },
        ],
        "verification": {
            "required_checks": [
                "same task, role, repository bytes, and policy produce the same brief ID",
                "read-only bootstrap leaves curated, immutable, staging, and derived authority unchanged",
                "every recommended operation exists in the live catalog",
                "unknown request fields fail closed",
                "secret values never appear in the brief or application telemetry",
                "external evidence and derived associations never claim curated authority",
            ],
            "final_gate": "python3 lab/scripts/validate_repo.py",
        },
        "natural_language_brief": _natural_brief(task, requested_role, workflows, phases),
        "policy_versions": {
            "agent_brief": AGENT_BRIEF_POLICY,
            "application": application_policy,
        },
    }
    identity = {**brief, "brief_id": None}
    brief["brief_id"] = "agent_brief_" + sha256_value(identity).removeprefix("sha256:")[:24]
    return brief
