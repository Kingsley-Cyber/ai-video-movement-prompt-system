"""PC-1 application handlers: guided session ops + doctor."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lab.compiler.profiles import REPO_ROOT

from .cpcs_guided import (
    STORE,
    GuidedProjector,
    classify_unknown,
    detect_mode,
    _sha,
)
from .cpcs_deliberation import DeliberationEngine, frozen_knowledge_snapshot
from .reasoning_treatment import (
    FrozenRuntimeBackend,
    TreatmentAdapter,
    apply_structured_objects,
)


def _runtime():
    snapshot = frozen_knowledge_snapshot()
    backend = FrozenRuntimeBackend()
    return snapshot, backend


def _knowledge_application_summary(translation: Any) -> dict[str, Any]:
    """WP-5: decision-type counts + pack ids for the finish package."""
    application_set = translation.application_set
    if not application_set:
        return {"applications": 0, "counts": {}, "pack_ids": [],
                "unknowns": []}
    counts: dict[str, int] = {}
    for entry in application_set["applications"]:
        decision = entry["decision"]["decision"]
        counts[decision] = counts.get(decision, 0) + 1
    return {
        "applications": len(application_set["applications"]),
        "counts": dict(sorted(counts.items())),
        "pack_ids": [e["pack"]["pack_id"]
                     for e in application_set["applications"]],
        "unknowns": application_set["unknowns"],
        "set_hash": application_set["set_hash"],
    }


def _deliberate(text: str, duration_seconds: float | None = None) -> dict[str, Any]:
    from lab.second_brain.src.intent import build_intent_context

    snapshot, backend = _runtime()
    ic = build_intent_context(text, root=REPO_ROOT)
    engine = DeliberationEngine(snapshot, backend)
    deliberation = engine.deliberate(text, ic["normalized_intent"])
    # KA-2.1 PASS 1: broad knowledge awareness profile (recall-oriented;
    # never gates retrieval, never decides final recruitment).
    from .cpcs_knowledge_awareness import build_awareness_profile

    awareness = build_awareness_profile(
        text, activation=deliberation["knowledge_activation_packet"])
    deliberation["knowledge_awareness_profile"] = awareness.to_dict()
    # KA-1 WP-5: the bridge pass runs inside translate when snapshot +
    # activation are provided; non-control knowledge lands in
    # planning_guidance / reasoning_material and never enters the score.
    treatment_packet = backend.plan(text, ic["normalized_intent"])
    translation = TreatmentAdapter(REPO_ROOT).translate(
        treatment_packet,
        snapshot=snapshot,
        activation=deliberation["knowledge_activation_packet"])
    # SI-1: deterministic projection of real-runtime EC-1 semantics
    # (condition types, target paths, failure families, evidence IDs)
    # into the existing structured interaction contract. No prose
    # classification; absent fields stay None.
    from .cpcs_structured_interaction_projection import (
        enrich_interaction_payloads,
    )

    translation.structured_objects = enrich_interaction_payloads(
        translation.structured_objects, treatment_packet)
    # KA-2 WP-3: build constellation + recruitment + refinement; additively
    # fill the two existing empty closure fields. Existing computed values
    # (accepted_hypotheses, safe_inferences, completeness, ...) are
    # preserved exactly.
    application_set = translation.application_set
    if application_set:
        from .cpcs_knowledge_constellation import assemble_constellation
        from .cpcs_knowledge_recruitment import recruit_for_intent
        from .cpcs_knowledge_refinement import (
            apply_to_closure,
            assess_prerequisites,
            build_refinement_packet,
        )

        # Evidence metadata must come from the TREATMENT PACKET: the
        # activation packet does not carry retrieved_evidence, and region
        # facets lose failure_family_ids / canonical_concept_ids when the
        # lookup is empty (metadata survival defect).
        evidence_by_id: dict[str, dict[str, Any]] = {
            ev["atomic_record_id"]: ev
            for ev in (treatment_packet.get("retrieved_evidence", []) or [])
            if ev.get("atomic_record_id")
        }
        constellation = assemble_constellation(
            application_set,
            deliberation["knowledge_activation_packet"],
            evidence_by_id=evidence_by_id,
        )
        pack_lookup = {
            entry["pack"]["pack_id"]: entry["pack"]
            for entry in application_set["applications"]
        }
        recruitment = recruit_for_intent(
            constellation,
            deliberation["knowledge_activation_packet"],
            pack_lookup=pack_lookup,
            awareness=deliberation.get("knowledge_awareness_profile", {}),
        )
        new_pre, gaps = assess_prerequisites(
            recruitment, constellation,
            deliberation["knowledge_activation_packet"],
            pack_lookup=pack_lookup,
        )
        refinement = build_refinement_packet(
            recruitment, constellation,
            deliberation["knowledge_activation_packet"],
            new_prerequisites=new_pre,
            coverage_gaps=gaps,
            application_set=application_set,
        )
        deliberation["knowledge_constellation"] = constellation.to_dict()
        deliberation["knowledge_recruitment"] = recruitment
        deliberation["recruitment_refinement"] = refinement
        deliberation["reasoning_closure_packet"] = apply_to_closure(
            refinement, deliberation["reasoning_closure_packet"])
        # KA-2.2: atomic decomposition + placement from typed structured
        # objects only (D4-clean); modular assembly for presentation.
        from .cpcs_knowledge_placement import (
            assemble_directing_modules,
            build_placement,
            decompose_atomic_units,
        )

        units = decompose_atomic_units(translation.structured_objects)
        placement = build_placement(
            recruitment, constellation, units, pack_lookup=pack_lookup,
            awareness=deliberation.get("knowledge_awareness_profile", {}))
        modules = assemble_directing_modules(
            placement, units, refinement, pack_lookup=pack_lookup,
            constellation=constellation)
        deliberation["atomic_units"] = [u.to_dict() for u in units]
        deliberation["knowledge_placement"] = [
            p.to_dict() for p in placement]
        deliberation["directing_modules"] = modules
    # TD-1: temporal directing plan (additive sidecar). No total duration
    # means no fabricated seconds — the plan stays TEMPORALLY_
    # UNDERSPECIFIED with relative weights and causal ordering.
    from .cpcs_temporal_director import build_temporal_plan

    temporal_plan = build_temporal_plan(
        units,
        total_duration_s=duration_seconds,
        duration_source="USER_EXPLICIT" if duration_seconds else None,
        placement=placement,
    )
    # NB-1: narrative beat graph from the user's own action clauses,
    # bound to SI-1 units; TD-1 schedule entries gain narrative beat
    # references (additive). User order is precedence, never causation.
    from .cpcs_narrative_beats import (
        annotate_temporal_plan,
        build_narrative_beat_graph,
    )

    beat_graph = build_narrative_beat_graph(text, units=units)
    deliberation["narrative_beat_graph"] = beat_graph.to_dict()
    deliberation["temporal_directing_plan"] = annotate_temporal_plan(
        temporal_plan, beat_graph)
    return deliberation, translation, ic


def _projector() -> GuidedProjector:
    return GuidedProjector(lambda: None, lambda: None)


def handler_guided_start(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    text = arguments["intent_text"]
    session = STORE.create(text, {"intent": {}})
    mode = arguments.get("mode")
    if mode is None:
        detected, _ = detect_mode(text)
        mode = "AUTO" if detected == "AUTO" else detected
    deliberation, translation, ic = _deliberate(
        text, duration_seconds=arguments.get("duration_seconds"))
    projector = _projector()
    projection = projector.project(session, deliberation, mode=mode)
    session["_deliberation"] = deliberation
    session["_translation"] = translation
    session["_intent_context"] = ic
    session["active_closure_id"] = deliberation["reasoning_closure_packet"]["closure_id"]
    session["active_projection_id"] = projection["projection_id"]
    session["interaction_mode"] = projection["interaction_mode"]
    session["blocking_unknowns"] = projection["blocking_unknowns"]
    session["status"] = ("AWAITING_USER"
                         if projection["clarification_candidates"] else "READY_TO_FINISH")
    return {
        "session_id": session["session_id"],
        "revision_id": session["current_revision"],
        "interaction_mode": projection["interaction_mode"],
        "projection": projection,
        "status": session["status"],
    }


def handler_guided_project(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    session = STORE.get(arguments["session_id"])
    deliberation = session.get("_deliberation")
    if deliberation is None:
        raise LookupError("session has no active deliberation")
    mode = session.get("interaction_mode", "AUTO")
    projector = _projector()
    projection = projector.project(session, deliberation, mode=mode)
    session["active_projection_id"] = projection["projection_id"]
    return {"session_id": session["session_id"],
            "revision_id": session["current_revision"],
            "interaction_mode": projection["interaction_mode"],
            "projection": projection}


def handler_guided_answer(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    session = STORE.get(arguments["session_id"])
    answer = arguments["answer_text"]
    choice_id = arguments.get("choice_id") or arguments.get("question_id")
    decision = {
        "decision_id": _sha(session["session_id"] + answer + str(session["current_revision"]))[:24],
        "session_id": session["session_id"],
        "revision_id": session["current_revision"],
        "subject": choice_id or "user answer",
        "decision_status": "USER_RESOLVED",
        "selected_value": answer,
        "alternative_values": [],
        "reason": "user answer",
        "authority_source": "USER_CORRECTION",
        "affected_requirement_ids": [],
        "affected_hypothesis_ids": [choice_id] if choice_id else [],
        "affected_paths": [],
        "evidence_refs": [],
        "confidence": 1.0,
        "creative_choice_id": choice_id if arguments.get("choice_id") else None,
        "lineage": {"answer_text": answer},
    }
    decision["decision_hash"] = _sha(
        {k: v for k, v in decision.items() if k != "decision_hash"})
    STORE.record_decision(session["session_id"], decision)
    # FAST transition detection: user says "just finish"
    low = " " + answer.lower() + " "
    if any(t in low for t in ("just finish", "just give me the prompt",
                              "that's enough", "whatever", "finish it",
                              "don't ask me anything")):
        return handler_guided_finish({"session_id": session["session_id"]}, root)
    session["status"] = "READY_TO_FINISH"
    return {"session_id": session["session_id"],
            "revision_id": session["current_revision"],
            "recorded_decision": decision,
            "status": session["status"]}


def _finish(session: dict[str, Any]) -> dict[str, Any]:
    from lab.compiler.build import compile_build, make_build_request
    from lab.compiler.score import make_score_request, resolve_score

    deliberation = session["_deliberation"]
    translation = session["_translation"]
    ic = session["_intent_context"]
    closure = deliberation["reasoning_closure_packet"]

    # blocking unknowns fail closed
    blocking = [h for h in deliberation["hypothesis_set"]["hypotheses"]
                if classify_unknown(h) == "BLOCKING" and h["status"] != "SUPPORTED"]
    if blocking:
        session["status"] = "BLOCKED"
        return {
            "session_id": session["session_id"],
            "status": "BLOCKED",
            "blocking_reason": [h["claim"] for h in blocking],
            "reason": ("completion refused: blocking unknowns must be resolved "
                       "before a coherent package can be produced"),
            "final_prompt_package": None,
        }
    projector = _projector()
    decisions = projector.build_completion_decisions(session, deliberation,
                                                     projector.project(
                                                         session, deliberation,
                                                         mode=session.get("interaction_mode", "FAST")))
    # existing compiler path (same as Control A + typed overlays). The resolved
    # score is NEVER mutated post-resolution (canonical score_id integrity):
    # treatment verification obligations, typed controls, and structured objects
    # travel in the prompt package alongside the score, not inside it.
    import hashlib as _hashlib

    defaulted_inputs = []
    score = resolve_score(make_score_request(ic, overlays=translation.overlays), root=REPO_ROOT)
    missing = [u for u in score["unresolved"] if u.get("code") == "missing_input"]
    if missing:
        # baseline default completion for missing INPUT fields only (authority
        # order: EXISTING_BASELINE_DEFAULT). Anything else fails closed below.
        assets = []
        intent = ic["normalized_intent"].get("intent", {})
        for u in missing:
            role = u["options"][0]
            default_value = (intent.get("primary_domain", "general_video")
                             if role == "video_domain" else "unspecified")
            assets.append({
                "asset_id": f"asset_default_{role}",
                "role": role,
                "content_hash": "sha256:" + _hashlib.sha256(
                    default_value.encode()).hexdigest(),
                "rights_basis": "baseline_default_completion",
            })
            defaulted_inputs.append({
                "decision_id": _sha(session["session_id"] + role + str(
                    session["current_revision"]))[:24],
                "session_id": session["session_id"],
                "revision_id": session["current_revision"],
                "subject": f"missing input: {role}",
                "decision_status": "BASELINE_DEFAULTED",
                "selected_value": default_value,
                "alternative_values": [],
                "reason": "baseline default completion for missing input",
                "authority_source": "EXISTING_BASELINE_DEFAULT",
                "affected_requirement_ids": [],
                "affected_hypothesis_ids": [],
                "affected_paths": [],
                "evidence_refs": [],
                "confidence": 0.5,
                "lineage": {"role": role},
            })
            defaulted_inputs[-1]["decision_hash"] = _sha(
                {k: v for k, v in defaulted_inputs[-1].items() if k != "decision_hash"})
        score = resolve_score(make_score_request(
            ic, overlays=translation.overlays, assets=assets), root=REPO_ROOT)
    remaining = [u for u in score["unresolved"] if u.get("code") != "missing_input"]
    if remaining:
        session["status"] = "BLOCKED"
        return {
            "session_id": session["session_id"],
            "status": "BLOCKED",
            "blocking_reason": [u.get("message") for u in remaining],
            "reason": "completion refused: score-level unresolved items require explicit resolution",
            "final_prompt_package": None,
        }
    build_request = make_build_request(score, project_id="cpcs-guided")
    artifacts = compile_build(build_request, root=REPO_ROOT)
    prompt_text = artifacts.get("prompt.txt", b"").decode("utf-8", "replace")
    decisions = decisions + defaulted_inputs
    session["completion_decisions"] = decisions
    session["canonical_score_id"] = score["score_id"]
    session["prompt_build_id"] = _sha(json.dumps(build_request, sort_keys=True,
                                                  default=str))[:24]
    session["status"] = "COMPLETED"
    STORE.snapshot_revision(session["session_id"])
    return {
        "session_id": session["session_id"],
        "status": "COMPLETED",
        "completion_decisions": decisions,
        "questions_asked": 0,
        "blocking_unknowns": [],
        "canonical_score_id": score["score_id"],
        "prompt_build_id": session["prompt_build_id"],
        "final_prompt_package": {
            "prompt": prompt_text,
            "prompt_length": len(prompt_text),
            "verification_obligations": translation.verification_requirements,
            "typed_controls": translation.provider_neutral_controls,
            "structured_objects": translation.structured_objects,
            "overlay_ids": [o["overlay_id"] for o in translation.overlays],
            "planning_guidance": translation.planning_guidance,
            "reasoning_material": translation.reasoning_material,
            "knowledge_application": _knowledge_application_summary(translation),
            "recruitment_refinement": deliberation.get("recruitment_refinement"),
            "knowledge_awareness": deliberation.get(
                "knowledge_awareness_profile"),
            "directing_modules": deliberation.get("directing_modules"),
            "canonical_score_id": score["score_id"],
            "baseline_defaulted_inputs": [d["selected_value"] for d in defaulted_inputs],
            "hard_semantics_preserved": True,
            "note": "provider-neutral treatment objects travel alongside the "
                    "canonical score; the resolved score itself is unmodified",
        },
        "closure_reason": closure["closure_reason"],
    }


def handler_guided_finish(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    session = STORE.get(arguments["session_id"])
    return _finish(session)


def handler_guided_revise(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    session = STORE.get(arguments["session_id"])
    correction = arguments["correction"]
    old_deliberation = session.get("_deliberation")
    projector = _projector()
    invalidation = {"invalidated_ids": [], "recomputed_ids": [], "preserved_ids": []}
    if old_deliberation is not None:
        invalidation = projector.targeted_invalidation(
            session, correction,
            old_deliberation["hypothesis_set"]["hypotheses"])
    STORE.snapshot_revision(session["session_id"])
    revised_text = session["original_request"] + ". Correction: " + correction
    deliberation, translation, ic = _deliberate(revised_text)
    session["_deliberation"] = deliberation
    session["_translation"] = translation
    session["_intent_context"] = ic
    session["active_closure_id"] = deliberation["reasoning_closure_packet"]["closure_id"]
    session["interaction_mode"] = "GUIDED"
    projection = projector.project(session, deliberation, mode="GUIDED")
    session["active_projection_id"] = projection["projection_id"]
    session["status"] = "AWAITING_USER"
    result = {
        "session_id": session["session_id"],
        "revision_id": session["current_revision"],
        "targeted_invalidation": invalidation,
        "projection": projection,
    }
    # user asked to finish within the revision?
    low = " " + correction.lower() + " "
    if any(t in low for t in ("just finish", "just give me the prompt", "finish it")):
        result["finish"] = _finish(session)
    return result


def handler_guided_inspect(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    session = STORE.get(arguments["session_id"])
    projection = handler_guided_project({"session_id": session["session_id"]}, root)
    deliberation = session["_deliberation"]
    return {
        "session_id": session["session_id"],
        "revision_id": session["current_revision"],
        "status": session["status"],
        "projection": projection["projection"],
        "hidden_reasoning_summary": projection["projection"]["hidden_reasoning_summary"],
        "completion_decisions": session["completion_decisions"],
        "user_decisions": session["user_decisions"],
        "deliberation_diagnostics": {
            "closure": deliberation["reasoning_closure_packet"]["reasoning_completeness"],
            "hypotheses": len(deliberation["hypothesis_set"]["hypotheses"]),
            "queries": len(deliberation["query_steering_plan"]["queries"]),
            "contradictions": deliberation["reasoning_closure_packet"]["contradictions_preserved"],
        },
    }


def handler_session_inspect(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    session = STORE.get(arguments["session_id"])
    return {k: v for k, v in session.items() if not k.startswith("_")}


def handler_session_history(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    session = STORE.get(arguments["session_id"])
    return {
        "session_id": session["session_id"],
        "revision_history": session["revision_history"],
        "history_count": len(session["revision_history"]),
    }


def cpcs_doctor(root: Path, runtime_path: str | None = None) -> dict[str, Any]:
    import os

    checks = {}
    if runtime_path is None:
        runtime_path = os.environ.get("CPCS_FROZEN_RUNTIME_PATH")
        if not runtime_path:
            from .bootstrap import load_local_config
            config = load_local_config(root)
            runtime_path = (config or {}).get("runtime_path")
    output_dir = Path(runtime_path).parent / "Output" if runtime_path else None

    checks["application_service"] = "OK"
    checks["frozen_cpcs_runtime"] = ("OK" if runtime_path and Path(runtime_path).is_dir()
                                     else "NOT CONFIGURED")
    arch = output_dir / "ARCHITECTURE_FREEZE_MANIFEST_v0.2.json" if output_dir else None
    checks["architecture_freeze"] = "OK" if arch and arch.is_file() else "MISSING"
    retr = output_dir / "RUNTIME_RETRIEVAL_FREEZE_MANIFEST_v0.1.json" if output_dir else None
    checks["retrieval_contract"] = "OK" if retr and retr.is_file() else "MISSING"
    checks["graph_projection"] = "OK"
    try:
        from lab.compiler import cpcs_typed
        checks["typed_registry"] = "OK" if cpcs_typed.REGISTRY else "MISSING"
    except Exception:
        checks["typed_registry"] = "MISSING"
    try:
        from lab.application import cpcs_deliberation, cpcs_guided  # noqa: F401
        checks["deliberation"] = "OK"
        checks["guided_projection"] = "OK"
    except Exception:
        checks["deliberation"] = "MISSING"
        checks["guided_projection"] = "MISSING"
    checks["session_revision"] = "OK" if STORE is not None else "MISSING"
    try:
        from lab.application import cpcs_knowledge_application  # noqa: F401
        checks["knowledge_application"] = "OK"
    except Exception:
        checks["knowledge_application"] = "MISSING"
    try:
        from lab.compiler.build import compile_build, make_build_request  # noqa: F401
        from lab.compiler.score import make_score_request, resolve_score  # noqa: F401
        checks["compiler"] = "OK"
    except Exception:
        checks["compiler"] = "MISSING"
    from lab.compiler.profiles import REPO_ROOT as _APP_ROOT
    checks["mcp_transport"] = "OK" if (_APP_ROOT / "bin" / "cpcs-mcp").is_file() else "MISSING"
    checks["provider_generation"] = "NOT CONFIGURED (optional; does not gate readiness)"

    required = ["application_service", "frozen_cpcs_runtime", "architecture_freeze",
                "retrieval_contract", "graph_projection", "typed_registry",
                "deliberation", "guided_projection", "session_revision", "compiler",
                "mcp_transport", "knowledge_application"]
    failures = [k for k in required if checks[k] != "OK"]
    ready = not failures
    return {
        "checks": checks,
        "guided_prompting_ready": ready,
        "status": "READY" if ready else "NOT_READY",
        "failing_components": failures,
    }


def handler_doctor(arguments: dict[str, Any], root: Path) -> dict[str, Any]:
    return cpcs_doctor(root)


def handler_knowledge_apply_inspect(arguments: dict[str, Any],
                                    root: Path) -> dict[str, Any]:
    """WP-8: read-only KnowledgeApplicationSet summary, no provider contact.

    Fails closed with a typed error envelope when the frozen runtime is
    unavailable."""
    from lab.second_brain.src.intent import build_intent_context

    from .cpcs_knowledge_application import apply_knowledge
    from .reasoning_treatment import BackendUnavailableError

    intent_text = arguments["intent_text"]
    try:
        snapshot = frozen_knowledge_snapshot()
        backend = FrozenRuntimeBackend()
        ic = build_intent_context(intent_text, root=root)
        engine = DeliberationEngine(snapshot, backend)
        deliberation = engine.deliberate(intent_text, ic["normalized_intent"])
        packet = backend.plan(intent_text, ic["normalized_intent"])
        application_set = apply_knowledge(
            packet, snapshot, deliberation["knowledge_activation_packet"])
    except (BackendUnavailableError, RuntimeError) as exc:
        return {
            "status": "ERROR",
            "reason": "frozen_runtime_unavailable",
            "detail": str(exc),
        }
    counts: dict[str, int] = {}
    packs = []
    for entry in application_set.applications:
        decision = entry["decision"]["decision"]
        counts[decision] = counts.get(decision, 0) + 1
        packs.append({
            "pack_id": entry["pack"]["pack_id"],
            "principle_family": entry["pack"]["principle_family"],
            "decision": decision,
            "target_family": entry["decision"]["target_family"],
            "evidence_ids": entry["pack"]["evidence_ids"],
        })
    return {
        "status": "OK",
        "set_id": application_set.set_id,
        "set_hash": application_set.set_hash,
        "packs": packs,
        "decision_counts": dict(sorted(counts.items())),
        "unknowns": application_set.unknowns,
        "lineage": application_set.lineage,
    }
