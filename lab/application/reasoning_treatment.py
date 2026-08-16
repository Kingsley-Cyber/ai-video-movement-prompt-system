"""CPCS reasoning-layer treatment integration (RL-1/AB-1/RG-1/RC-1).

Overlay semantics:

  - Control A (existing application) remains the default and is unchanged.
  - Treatment B (CPCS reasoning v1) is an OPTIONAL layer: frozen CPCS
    reasoning/retrieval -> CPCSReasoningTreatmentPacket -> repo-native
    translation (score overlays + typed controls + verification) -> the
    SAME existing compiler/build/provider/runtime.

Design decisions (frozen for this integration):

  D1  The same normalized intent must be able to run through A or B and
      reach the same downstream compiler/evaluation surface.
  D2  One isolated upstream treatment factor (reasoning_policy) for the
      A/B experiment; downstream control differences are measured
      treatment effects.
  D3  RETRY != REPAIR: generation_v1 -> repair_v1 -> generation_v2.
  D4  Existing flat TEXT evidence admission = REJECTED.
      Retrieved evidence is never flattened into carrier text. Evidence
      stays structured in the treatment packet (atomic_record_id,
      provenance, why_retrieved) and is referenced BY ID via overlay
      source_refs / control provenance_ref. Any treatment control that
      can only be expressed as free prose is surfaced as an
      unsupported_mapping (rejected), never silently converted to text.
  D5  LLM authority boundary: the LLM may submit intent/complaints and
      request planning/inspection; it may not write curated knowledge,
      invent evidence, mutate arms, or reinterpret observations.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Protocol

from lab.compiler.profiles import REPO_ROOT, load_profile_catalog
from lab.compiler.score import validate_overlay

TREATMENT_VERSION = "cpcs-reasoning-v1"
TREATMENT_ARTIFACT = "CPCSReasoningTreatmentPacket"
PACKET_SCHEMA_ID = "cpcs.reasoning_treatment_packet/1.0"

OVERLAY_SCOPE_BY_HARDNESS = {
    "HARD": "event_lock",
    "SOFT": "scene_override",
    "PREFERENCE": "shot_override",
}
OVERLAY_PRIORITY_BY_SCOPE = {
    "event_lock": 700,
    "explicit_user_correction": 800,
    "scene_override": 500,
    "shot_override": 600,
}

_CONTROL_ID_RE = re.compile(r"^control_[0-9a-f]{16}$")
_METRIC_ID_RE = re.compile(r"^metric_[A-Za-z0-9._-]+$")
_OVERLAY_ID_RE = re.compile(r"^overlay_[A-Za-z0-9._-]+$")
_TOKEN_RE = re.compile(r"[a-z0-9_]{4,}")


def _sha(value: Any) -> str:
    if isinstance(value, bytes):
        return hashlib.sha256(value).hexdigest()
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TreatmentBackend(Protocol):
    """Produces a CPCSReasoningTreatmentPacket for one normalized intent."""

    def plan(
        self,
        intent_text: str,
        normalized_intent: dict[str, Any],
        *,
        query_mode: str = "INITIAL_GENERATION",
        discrepancy: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


@dataclass
class Translation:
    """Repo-native projection of one treatment packet (D4-aware)."""

    overlays: list[dict[str, Any]] = field(default_factory=list)
    structured_objects: list[dict[str, Any]] = field(default_factory=list)
    duplicate_semantics: list[dict[str, Any]] = field(default_factory=list)
    verification_requirements: list[dict[str, Any]] = field(default_factory=list)
    provider_neutral_controls: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)
    lineage: dict[str, Any] = field(default_factory=dict)
    unsupported_mappings: list[dict[str, Any]] = field(default_factory=list)
    # KA-1 WP-5 (additive): bridge-routed non-control knowledge. PLANNING and
    # NON_EXECUTABLE decisions never enter the resolved score.
    planning_guidance: list[dict[str, Any]] = field(default_factory=list)
    reasoning_material: list[dict[str, Any]] = field(default_factory=list)
    application_set: dict[str, Any] | None = None


def build_treatment_packet(
    *,
    treatment_id: str,
    source_intent_hash: str,
    query_mode: str,
    activated_requirements: list[str],
    mandatory_requirements: list[str],
    conditional_requirements: list[str],
    required_pathways: dict[str, str],
    objectives_at_risk: list[str],
    predicted_failure_families: list[str],
    retrieved_evidence: list[dict[str, Any]],
    proposed_obligations: list[dict[str, Any]],
    proposed_controls: list[dict[str, Any]],
    verification_obligations: list[dict[str, Any]],
    unknowns: list[dict[str, Any]],
    uncovered_mandatory_requirements: list[str],
    architecture_freeze_identity: str,
    retrieval_runtime_freeze_identity: str,
) -> dict[str, Any]:
    """Assemble the deterministic CPCSReasoningTreatmentPacket."""
    packet = {
        "schema": PACKET_SCHEMA_ID,
        "treatment_id": treatment_id,
        "treatment_version": TREATMENT_VERSION,
        "source_intent_hash": source_intent_hash,
        "query_mode": query_mode,
        "activated_requirements": sorted(set(activated_requirements)),
        "mandatory_requirements": sorted(set(mandatory_requirements)),
        "conditional_requirements": sorted(set(conditional_requirements)),
        "required_pathways": dict(sorted(required_pathways.items())),
        "objectives_at_risk": sorted(set(objectives_at_risk)),
        "predicted_failure_families": sorted(set(predicted_failure_families)),
        "retrieved_evidence": retrieved_evidence,
        "proposed_execution_obligations": proposed_obligations,
        "proposed_controls": proposed_controls,
        "verification_obligations": verification_obligations,
        "unknowns": unknowns,
        "uncovered_mandatory_requirements": sorted(set(uncovered_mandatory_requirements)),
        "architecture_freeze_identity": architecture_freeze_identity,
        "retrieval_runtime_freeze_identity": retrieval_runtime_freeze_identity,
    }
    packet["packet_hash"] = _sha(
        {k: v for k, v in packet.items() if k not in ("packet_hash",)}
    )
    return packet


class TreatmentAdapter:
    """Translates a treatment packet into repo-native compiler inputs.

    D4: evidence is never admitted as flat text. Every overlay/control
    references evidence by id (source_refs / provenance_ref). Prose-only
    controls are surfaced in unsupported_mappings, not flattened."""

    def __init__(self, root: Path = REPO_ROOT):
        self.root = root
        self.field_policies: dict[str, str] = load_profile_catalog(root).field_policies

    # -- typed path mapping (D4: no free prose in values) ------------------
    def _candidate_paths(self, control: dict[str, Any]) -> list[str]:
        section = {
            "camera": "camera",
            "actor": "performance",
            "object": "interactions",
            "scene": "continuity",
        }.get(control.get("target", "scene"), "continuity")
        statement = (control.get("control_semantics") or {}).get("statement") or ""
        tokens = sorted(set(_TOKEN_RE.findall(statement.lower())))
        paths = []
        for token in tokens:
            candidate = f"{section}.{token}"
            if candidate in self.field_policies:
                paths.append(candidate)
        if control.get("control_type"):
            for ct in control["control_type"]:
                token = ct.lower().removeprefix("ct-")
                candidate = f"{section}.{token}"
                if candidate in self.field_policies:
                    paths.append(candidate)
        return sorted(set(paths))

    def _typed_value(self, path: str) -> Any:
        policy = self.field_policies[path]
        if policy == "boolean":
            return True
        if policy in ("integer", "number"):
            return 1
        if policy == "array":
            return []
        if policy == "string":
            # D4: a bare string value here would admit flat text. Only
            # enum-controlled paths are safe for string values; otherwise
            # the mapping is rejected.
            return None
        return None

    def translate(self, packet: dict[str, Any],
                  *, snapshot: Any = None,
                  activation: dict[str, Any] | None = None) -> Translation:
        from lab.compiler import cpcs_typed

        out = Translation()
        evidence_by_id = {e.get("atomic_record_id"): e for e in
                          packet.get("retrieved_evidence", [])}
        emitted_semantics: dict[tuple[str, frozenset], str] = {}
        for control in packet.get("proposed_controls", []):
            control_id = control.get("control_id", "")
            hardness = control.get("hardness", "SOFT")
            source = control.get("source", "EVIDENCE_DERIVED")
            evidence_ids = control.get("supporting_evidence_ids", []) or []
            requirement_ids = control.get("source_requirement_ids", []) or []
            # duplicate-semantic suppression: same family + same requirement
            # lineage already represented by a mapped object (TC-2)
            dup_key = (str(control.get("control_type", [])),
                       frozenset(requirement_ids))
            if dup_key in emitted_semantics:
                out.duplicate_semantics.append({
                    "control_id": control_id,
                    "duplicate_of": emitted_semantics[dup_key],
                    "semantic_key": dup_key,
                    "requirement_ids": sorted(set(requirement_ids)),
                    "evidence_ids": sorted(set(evidence_ids)),
                })
                continue
            # TC-1 deterministic structured admission (D4-compliant, prose-free)
            path_id, entry = cpcs_typed.map_control(control)
            if path_id and entry:
                constructor = cpcs_typed.CONSTRUCTORS.get(path_id)
                if constructor:
                    enriched = dict(control)
                    enriched["_family"] = entry["semantic_family"]
                    obj = constructor(enriched)
                    out.structured_objects.append({
                        "target": obj.target,
                        "schema": obj.schema,
                        "value": obj.value,
                    })
                    emitted_semantics[dup_key] = (
                        obj.value.get("interaction_id")
                        or obj.value.get("invariant_id")
                        or obj.value.get("event_id")
                        or obj.value.get("constraint_id")
                        or obj.value.get("object_id")
                        or obj.value.get("relation_id")
                        or obj.value.get("edge_id")
                        or obj.value.get("continuity_id")
                        or obj.value.get("event_id")
                        or obj.value.get("invariant_id")
                        or path_id)
                    out.lineage[f"structured:{obj.value.get(next(iter(obj.value)), path_id)}"] = {
                        "path_id": path_id,
                        "semantic_family": entry["semantic_family"],
                        "control_ids": [control_id],
                        "requirement_ids": sorted(set(requirement_ids)),
                        "evidence_ids": sorted(set(evidence_ids)),
                        "source_control_types": list(control.get("control_type", [])),
                    }
                    continue
            paths = self._candidate_paths(control)
            typed = {p: self._typed_value(p) for p in paths if self._typed_value(p) is not None}
            if typed:
                scope = "explicit_user_correction" if source == "USER_EXPLICIT" \
                    else OVERLAY_SCOPE_BY_HARDNESS.get(hardness, "scene_override")
                overlay_id = f"overlay_{hardness.lower()}_{_sha(control_id)[:12]}"
                out.overlays.append({
                    "overlay_id": overlay_id,
                    "scope": scope,
                    "priority": OVERLAY_PRIORITY_BY_SCOPE[scope],
                    "values": typed,
                    "locks": sorted(typed),
                    "source_refs": sorted(set(evidence_ids)),
                })
                validate_overlay(out.overlays[-1], self.root)
                out.lineage[overlay_id] = {
                    "control_ids": [control_id],
                    "requirement_ids": sorted(set(requirement_ids)),
                    "evidence_ids": sorted(set(evidence_ids)),
                }
            elif paths and not typed:
                out.unsupported_mappings.append({
                    "control_id": control_id,
                    "reason": "string-valued path rejected under D4 "
                              "(no flat-text evidence admission)",
                    "candidate_paths": paths,
                    "requirement_ids": sorted(set(requirement_ids)),
                    "evidence_ids": sorted(set(evidence_ids)),
                    "proposed_semantic_meaning": (
                        control.get("control_semantics") or {}).get("statement"),
                    "effect_on_score": "none",
                })
            else:
                out.unsupported_mappings.append({
                    "control_id": control_id,
                    "reason": "no typed repo-native field mapping",
                    "requirement_ids": sorted(set(requirement_ids)),
                    "evidence_ids": sorted(set(evidence_ids)),
                    "proposed_semantic_meaning": (
                        control.get("control_semantics") or {}).get("statement"),
                    "effect_on_score": "none",
                })
            # typed provider-neutral control (D4: value is the typed value
            # of the FIRST mapped path; evidence referenced by id only)
            if typed:
                path0 = sorted(typed)[0]
                cid = "control_" + _sha(control_id)[:16]
                if not _CONTROL_ID_RE.match(cid):
                    cid = "control_" + hashlib.sha256(control_id.encode()).hexdigest()[:16]
                out.provider_neutral_controls.append({
                    "control_id": cid,
                    "path": path0,
                    "value": typed[path0],
                    "authority": "canonical_score",
                    "provenance_ref": "provenance.fields." + path0,
                })
        # verification obligations -> typed verification requirements
        for v in packet.get("verification_obligations", []):
            obs = v.get("observability", "semantic")
            observability = {"direct": "direct", "semantic": "semantic",
                             "measured": "measured", "human": "human_review"}.get(obs, "semantic")
            metric_id = "metric_" + _sha(v.get("obligation_id", "obligation"))[:24]
            out.verification_requirements.append({
                "metric_id": metric_id,
                "target_paths": sorted(v.get("target_paths", []) or []),
                "method": v.get("method", "cpcs-reasoning-v1 obligation"),
                "observability": observability,
                "source_profile": "profile://cpcs-reasoning-treatment",
            })
        # coverage statuses + unknowns surface as warnings (typed, no text dumps)
        if packet.get("uncovered_mandatory_requirements"):
            out.warnings.append({
                "code": "treatment_uncovered_mandatory",
                "message": "uncovered mandatory requirements: "
                           + ",".join(sorted(packet["uncovered_mandatory_requirements"])),
            })
        if packet.get("unknowns"):
            out.warnings.append({
                "code": "treatment_unknowns",
                "message": f"{len(packet['unknowns'])} unresolved unknowns surfaced "
                           "(structured in packet, not flattened)",
            })
        # KA-1 WP-5 knowledge application bridge pass (opt-in: snapshot +
        # activation provided). CONTROL/COMPOSITE decisions reuse the existing
        # structured-object and obligation paths above; VERIFICATION /
        # PLANNING / NON_EXECUTABLE route here. Non-control knowledge never
        # enters the resolved score (score_id integrity).
        if snapshot is not None and activation is not None:
            from .cpcs_knowledge_application import apply_knowledge

            application_set = apply_knowledge(packet, snapshot, activation)
            out.application_set = application_set.to_dict()
            seen_metrics = {v.get("metric_id")
                            for v in out.verification_requirements}
            for entry in application_set.applications:
                decision = entry["decision"]
                pack = entry["pack"]
                req_ids = sorted(pack["lineage"].get("requirement_ids", []))
                universal_types = sorted(
                    {r["universal_type"] for r in pack["source_records"]})
                if decision["decision"] == "VERIFICATION":
                    metric_id = "metric_ka1_" + _sha(pack["pack_id"])[:24]
                    if metric_id not in seen_metrics:
                        out.verification_requirements.append({
                            "metric_id": metric_id,
                            "target_paths": req_ids,
                            "method": "cpcs-reasoning-v1 ka1 bridge obligation",
                            "observability": "semantic",
                            "source_profile":
                                "profile://cpcs-reasoning-treatment",
                        })
                        seen_metrics.add(metric_id)
                elif decision["decision"] == "PLANNING":
                    out.planning_guidance.append({
                        "guidance_id": "guidance_" + _sha(pack["pack_id"])[:16],
                        "pack_id": pack["pack_id"],
                        "requirement_ids": req_ids,
                        "evidence_ids": pack["evidence_ids"],
                        "authority": decision["authority"],
                        "universal_types": universal_types,
                    })
                elif decision["decision"] == "NON_EXECUTABLE":
                    out.reasoning_material.append({
                        "material_id":
                            "material_" + _sha(pack["pack_id"])[:16],
                        "pack_id": pack["pack_id"],
                        "requirement_ids": req_ids,
                        "evidence_ids": pack["evidence_ids"],
                        "disposition": "NON_EXECUTABLE_KNOWLEDGE",
                        "universal_types": universal_types,
                    })
        return out


class DiscrepancyBuilder:
    """RG-1: expected vs observed -> DiscrepancyPacket (epistemically separated)."""

    def build(
        self,
        expected_states: list[dict[str, Any]],
        observations: list[dict[str, Any]],
        user_complaint: str | None = None,
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        discrepancies = []
        obs_by_req = {}
        for o in observations:
            obs_by_req.setdefault(o.get("requirement_id"), []).append(o)
        for exp in expected_states:
            rid = exp.get("requirement_id")
            obs = obs_by_req.get(rid, [])
            status = "OBSERVED_ONLY" if not obs else (
                "CONTRADICTED" if any(o.get("observed_value") != exp.get("expected_value")
                                      for o in obs)
                else "CORROBORATED")
            if user_complaint:
                status = "CORROBORATED" if status == "OBSERVED_ONLY" else status
            discrepancies.append({
                "discrepancy_id": "disc_" + _sha(f"{rid}{exp.get('expected_value')}")[:16],
                "expected": exp,
                "observed": obs,
                "user_report": user_complaint,
                "status": status,
                "affected_requirement_ids": [rid],
                "affected_objectives": exp.get("objectives", []) or [],
                "failure_families": exp.get("failure_family_if_violated", []) or [],
                "severity": exp.get("criticality", "important"),
                "time_phase_scope": exp.get("time_scope"),
                "evidence": {"observation_ids": [o.get("observation_id") for o in obs],
                             "user_report_epistemic_status": (
                                 "USER_REPORTED_ONLY — not measured video truth"
                                 if user_complaint else None)},
            })
        return {
            "schema": "cpcs.discrepancy_packet/1.0",
            "discrepancy_packet_id": "discpkt_" + _sha(
                [d["discrepancy_id"] for d in discrepancies])[:16],
            "source": source or {},
            "discrepancies": discrepancies,
            "user_complaint_epistemic_note":
                "user complaint alone is never treated as measured video truth",
        }


class RepairPlanner:
    """RG-1/RC-1: DiscrepancyPacket -> REPAIR_GAP retrieval -> RepairControlPlan."""

    def plan(
        self,
        discrepancy_packet: dict[str, Any],
        backend: TreatmentBackend,
        original_intent_text: str,
        normalized_intent: dict[str, Any],
        original_packet: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        repair_packet = backend.plan(
            original_intent_text,
            normalized_intent,
            query_mode="REPAIR_GAP",
            discrepancy=discrepancy_packet,
        )
        controls = repair_packet.get("proposed_controls", [])
        covered = {r: c for c in controls for r in c.get("source_requirement_ids", [])}
        plan = {
            "schema": "cpcs.repair_control_plan/1.0",
            "repair_plan_id": "repair_" + _sha(repair_packet["packet_hash"])[:16],
            "controls_to_add": [c for c in controls if c.get("action") == "add"],
            "controls_to_strengthen": [c for c in controls if c.get("action") == "strengthen"],
            "controls_to_weaken": [c for c in controls if c.get("action") == "weaken"],
            "controls_to_remove": [c.get("control_id") for c in controls
                                   if c.get("action") == "remove"],
            "controls_to_rescope": [c for c in controls if c.get("action") == "rescope"],
            "invariants_to_add_or_strengthen": [
                c for c in controls if c.get("hardness") == "HARD"],
            "verification_changes": repair_packet.get("verification_obligations", []),
            "supported_requirement_ids": sorted(set(covered)),
            "supporting_evidence_ids": sorted({e.get("atomic_record_id")
                                               for e in repair_packet.get("retrieved_evidence", [])}),
            "expected_repair_effect": {
                d["discrepancy_id"]: {"target": "RESOLVED" if d["status"] != "CONTRADICTED"
                                      else "INVESTIGATE"}
                for d in discrepancy_packet.get("discrepancies", [])},
            "remaining_uncertainty": repair_packet.get("unknowns", []),
            "lineage": {
                "generation": "v1",
                "repair": "v1",
                "revised_generation": "v2",
                "source_packet_hash": repair_packet["packet_hash"],
            },
        }
        return plan


class BackendUnavailableError(RuntimeError):
    """Typed fail-closed signal when the frozen CPCS runtime is unavailable."""

    def __init__(self, reason: str, details: dict[str, Any] | None = None):
        self.reason = reason
        self.details = details or {}
        super().__init__(reason)


_REQUIRED_ARTIFACTS = (
    "ARCHITECTURE_FREEZE_MANIFEST_v0.2.json",
    "RUNTIME_RETRIEVAL_FREEZE_MANIFEST_v0.1.json",
    "CPCS_PRODUCTION_RETRIEVAL_CONTRACT_v0.1.json",
    "CPCS_RETRIEVAL_GOLD_v0.2.json",
)
_REQUIRED_MODULES = ("cpcs_loader.py", "cpcs_production.py", "ec1_compiler.py")


def _record_field(loader: Any, atomic_record_id: str, field: str) -> Any:
    """Read one structured field from a loaded frozen record (KA-1 WP-5).

    Evidence remains ID-referenced; typed metadata travels in the treatment
    packet so the bridge can decide representation without prose mining."""
    records = getattr(loader, "records_by_arid", None) or {}
    record = records.get(atomic_record_id, {})
    return record.get(field)


class FrozenRuntimeBackend(TreatmentBackend):
    """Bridges the external frozen CPCS runtime into treatment packets.

    - lazy import: no import-time dependency on the external runtime
    - explicit freeze identity check (sha256 of the two manifests)
    - fails closed when the runtime dir or any frozen artifact is missing
    - never writes into the frozen runtime directory
    - never falls back to FakeBackend
    """

    def __init__(self, runtime_path: str | None = None):
        if runtime_path:
            self.runtime_path = runtime_path
        else:
            env = __import__("os").environ.get("CPCS_FROZEN_RUNTIME_PATH")
            if env:
                self.runtime_path = env
            else:
                from .bootstrap import resolved_runtime_path
                self.runtime_path = resolved_runtime_path()
        self._loaded = None

    def _check(self) -> dict[str, str]:
        import os

        if not self.runtime_path:
            raise BackendUnavailableError(
                "CPCS_FROZEN_RUNTIME_PATH is not configured",
                {"configure": "export CPCS_FROZEN_RUNTIME_PATH=/path/to/frozen/Runtime"},
            )
        rt = Path(self.runtime_path)
        if not rt.is_dir():
            raise BackendUnavailableError(
                f"frozen runtime directory missing: {rt}", {}
            )
        output_dir = rt.parent / "Output"
        missing = [
            name for name in _REQUIRED_ARTIFACTS
            if not (output_dir / name).is_file()
        ] + [
            name for name in _REQUIRED_MODULES if not (rt / name).is_file()
        ]
        if missing:
            raise BackendUnavailableError(
                "frozen runtime artifacts missing", {"missing": missing}
            )
        return {
            "architecture_freeze_identity": _sha(
                (output_dir / "ARCHITECTURE_FREEZE_MANIFEST_v0.2.json").read_bytes()
            )[:16],
            "retrieval_runtime_freeze_identity": _sha(
                (output_dir / "RUNTIME_RETRIEVAL_FREEZE_MANIFEST_v0.1.json").read_bytes()
            )[:16],
            "runtime_path": str(rt),
        }

    def _runtime(self):
        if self._loaded is None:
            identities = self._check()
            import sys as _sys

            _sys.path.insert(0, self.runtime_path)
            try:
                from cpcs_loader import CPCSLoader
                from cpcs_production import ProductionRetrieval, DEFAULT_CONFIG
                from ec1_compiler import ExecutionCompiler
            except ImportError as exc:  # pragma: no cover - environment dependent
                raise BackendUnavailableError(
                    f"frozen runtime import failed: {exc}", {}
                ) from exc
            from sentence_transformers import SentenceTransformer

            loader = CPCSLoader(version="v0.2")
            loader.validate()
            model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            self._loaded = (identities, loader, model, ProductionRetrieval,
                            DEFAULT_CONFIG, ExecutionCompiler)
        return self._loaded

    def plan(
        self,
        intent_text: str,
        normalized_intent: dict[str, Any],
        *,
        query_mode: str = "INITIAL_GENERATION",
        discrepancy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        identities, loader, model, ProductionRetrieval, DEFAULT_CONFIG, ExecutionCompiler = (
            self._runtime()
        )
        source_intent_hash = _sha(normalized_intent) or _sha(intent_text)
        if query_mode == "REPAIR_GAP":
            return self._repair_plan(
                intent_text, normalized_intent, source_intent_hash, discrepancy,
                identities, loader, model, ProductionRetrieval, DEFAULT_CONFIG,
                ExecutionCompiler,
            )
        pr = ProductionRetrieval(loader, model, dict(DEFAULT_CONFIG))
        pkt = pr.retrieve(intent_text)
        compiler = ExecutionCompiler(loader, model)
        execution = compiler.compile(intent_text, activation_packet=None)
        coverage = pkt["packet_summary"]
        mand = [r["requirement_id"] for r in pkt["requirements"]
                if r["importance"] == "mandatory"]
        cond = [r["requirement_id"] for r in pkt["requirements"]
                if r["importance"] != "mandatory"]
        uncovered = coverage.get("uncovered_requirements", [])
        return build_treatment_packet(
            treatment_id="treatment_" + source_intent_hash[:16],
            source_intent_hash=source_intent_hash,
            query_mode=query_mode,
            activated_requirements=mand + cond,
            mandatory_requirements=mand,
            conditional_requirements=cond,
            required_pathways={
                r["requirement_id"]: r["coverage_status"]
                for r in pkt["requirements"]},
            objectives_at_risk=sorted({o for i in pkt["evidence_items"]
                                       for o in i.get("objective_ids", [])}),
            predicted_failure_families=sorted({f for i in pkt["evidence_items"]
                                               for f in i.get("failure_family_ids", [])}),
            retrieved_evidence=[
                {
                    "atomic_record_id": i["atomic_record_id"],
                    "document_id": i.get("document_id"),
                    "supported_requirement_ids": i.get("supported_requirement_ids", []),
                    "trigger_ids": i.get("trigger_ids", []),
                    "objective_ids": i.get("objective_ids", []),
                    "failure_family_ids": i.get("failure_family_ids", []),
                    "control_ids": i.get("control_ids", []),
                    "universal_type": _record_field(
                        loader, i["atomic_record_id"], "universal_type"),
                    "provenance": i.get("provenance", {}),
                    "epistemic_status": i.get("epistemic_status")
                    or _record_field(
                        loader, i["atomic_record_id"], "epistemic_state"),
                    "coverage_selection_reason": i.get("coverage_selection_reason"),
                }
                for i in pkt["evidence_items"]],
            proposed_obligations=[
                {"obligation_id": o["obligation_id"],
                 "requirement_id": o["requirement_id"],
                 "kinds": o["kinds"], "status": o["status"]}
                for o in execution["execution_obligations"]],
            proposed_controls=[
                {"control_id": c["control_id"],
                 "control_type": c["control_type"],
                 "target": c["target"], "scope": c["scope"],
                 "hardness": c["hardness"], "source": c["source"],
                 "source_requirement_ids": c["source_requirement_ids"],
                 "supporting_evidence_ids": c["supporting_evidence_ids"],
                 "protected_objectives": c["protected_objectives"],
                 "prevented_failure_families": c["prevented_failure_families"],
                 "control_semantics": c["control_semantics"],
                 "action": "add"}
                for c in execution["director_control_ir"]["controls"]],
            verification_obligations=[
                {"obligation_id": e["expected_state_id"],
                 "requirement_id": e["requirement_id"],
                 "method": e["expected_condition"],
                 "observability": {
                     "DIRECTLY_OBSERVABLE": "direct",
                     "PARTIALLY_OBSERVABLE": "semantic",
                     "INFERRED": "semantic",
                     "NOT_DIRECTLY_OBSERVABLE": "human",
                 }.get(e["observability"], "semantic"),
                 "target_paths": [e["target"]],
                 "failure_family_ids": e["failure_family_if_violated"],
                 "criticality": e["criticality"]}
                for e in execution["expected_state_contract"]],
            unknowns=execution["scene_intent"].get("unknowns", []),
            uncovered_mandatory_requirements=uncovered,
            architecture_freeze_identity=identities["architecture_freeze_identity"],
            retrieval_runtime_freeze_identity=identities["retrieval_runtime_freeze_identity"],
        )

    def _repair_plan(
        self, intent_text, normalized_intent, source_intent_hash, discrepancy,
        identities, loader, model, ProductionRetrieval, DEFAULT_CONFIG,
        ExecutionCompiler,
    ) -> dict[str, Any]:
        # REPAIR_GAP query = discrepancy-driven terms + frozen vocabularies
        terms = [intent_text]
        for d in (discrepancy or {}).get("discrepancies", []):
            terms.append(str(d.get("expected", {}).get("expected_condition", "")))
            for f in d.get("failure_families", []) or []:
                terms.append(f)
        repair_query = " ; ".join(t for t in terms if t)
        pr = ProductionRetrieval(loader, model, dict(DEFAULT_CONFIG))
        pkt = pr.retrieve(repair_query)
        mand = [r["requirement_id"] for r in pkt["requirements"]
                if r["importance"] == "mandatory"]
        cond = [r["requirement_id"] for r in pkt["requirements"]
                if r["importance"] != "mandatory"]
        uncovered = pkt["packet_summary"].get("uncovered_requirements", [])
        affected = sorted({rid for d in (discrepancy or {}).get("discrepancies", [])
                           for rid in d.get("affected_requirement_ids", [])})
        controls = []
        for i in pkt["evidence_items"]:
            hardness = "HARD" if i.get("coverage_selection_reason") in (
                "uncovered_mandatory", "strongest_mandatory") else "SOFT"
            controls.append({
                "control_id": "repair_ctl_" + _sha(i["atomic_record_id"])[:16],
                "control_type": i.get("control_ids") or ["REPAIR_EVIDENCE"],
                "target": "scene", "scope": "scene", "hardness": hardness,
                "source": "EVIDENCE_DERIVED",
                "source_requirement_ids": [r for r in i.get("supported_requirement_ids", [])
                                           if r in set(affected + mand)],
                "supporting_evidence_ids": [i["atomic_record_id"]],
                "protected_objectives": i.get("objective_ids", []),
                "prevented_failure_families": i.get("failure_family_ids", []),
                "control_semantics": {
                    "statement": "repair evidence: " + i["atomic_record_id"],
                    "universal_type": "REPAIR_EVIDENCE"},
                "action": "strengthen" if hardness == "HARD" else "add",
            })
        return build_treatment_packet(
            treatment_id="repair_treatment_" + source_intent_hash[:16],
            source_intent_hash=source_intent_hash,
            query_mode="REPAIR_GAP",
            activated_requirements=affected + mand,
            mandatory_requirements=sorted(set(affected + mand)),
            conditional_requirements=cond,
            required_pathways={r["requirement_id"]: r["coverage_status"]
                               for r in pkt["requirements"]},
            objectives_at_risk=sorted({o for i in pkt["evidence_items"]
                                       for o in i.get("objective_ids", [])}),
            predicted_failure_families=sorted({f for d in
                (discrepancy or {}).get("discrepancies", []) for f in
                d.get("failure_families", [])}),
            retrieved_evidence=[
                {"atomic_record_id": i["atomic_record_id"],
                 "document_id": i.get("document_id"),
                 "supported_requirement_ids": i.get("supported_requirement_ids", []),
                 "universal_type": _record_field(
                     loader, i["atomic_record_id"], "universal_type"),
                 "provenance": i.get("provenance", {}),
                 "epistemic_status": i.get("epistemic_status")
                 or _record_field(
                     loader, i["atomic_record_id"], "epistemic_state"),
                 "coverage_selection_reason": i.get("coverage_selection_reason")}
                for i in pkt["evidence_items"]],
            proposed_obligations=[
                {"obligation_id": "obl_repair_" + rid, "requirement_id": rid,
                 "kinds": ["CONTROL", "VERIFICATION"],
                 "status": "REPRESENTED" if rid not in uncovered
                 else "REPRESENTED_WITHOUT_EVIDENCE"}
                for rid in sorted(set(affected + mand))],
            proposed_controls=controls,
            verification_obligations=[
                {"obligation_id": "verify_" + _sha(d["discrepancy_id"])[:16],
                 "requirement_id": d.get("affected_requirement_ids", [None])[0],
                 "method": "re-verify " + str(d.get("expected", {}).get("expected_condition", "")),
                 "observability": "semantic",
                 "target_paths": [],
                 "failure_family_ids": d.get("failure_families", []),
                 "criticality": d.get("severity", "important")}
                for d in (discrepancy or {}).get("discrepancies", [])],
            unknowns=[],
            uncovered_mandatory_requirements=uncovered,
            architecture_freeze_identity=identities["architecture_freeze_identity"],
            retrieval_runtime_freeze_identity=identities["retrieval_runtime_freeze_identity"],
        )


FAKE_FIXTURES: dict[str, dict[str, Any]] = {
    "simple_motion": {
        "mandatory": ["REQ-CONTACT-1"], "conditional": ["REQ-CAUSAL-1"],
        "evidence": [{"atomic_record_id": "ev_contact_001",
                      "supported_requirement_ids": ["REQ-CONTACT-1"],
                      "failure_family_ids": ["FF-CONTACT"],
                      "objective_ids": ["OBJ-CONTACT"],
                      "universal_type": "Constraint"},
                     {"atomic_record_id": "ev_contact_002",
                      "supported_requirement_ids": ["REQ-CONTACT-1", "REQ-CAUSAL-1"],
                      "failure_family_ids": ["FF-CAUSALITY"],
                      "objective_ids": ["OBJ-CAUSALITY"],
                      "universal_type": "Concept"}],
        "controls": [{"control_id": "ctl_contact_001", "control_type": ["CT-CONTACT-CONTRACT"],
                      "target": "scene", "scope": "scene", "hardness": "HARD",
                      "source": "EVIDENCE_DERIVED",
                      "source_requirement_ids": ["REQ-CONTACT-1"],
                      "supporting_evidence_ids": ["ev_contact_001"],
                      "protected_objectives": ["OBJ-CONTACT"],
                      "prevented_failure_families": ["FF-CONTACT"],
                      "control_semantics": {"statement": "contact contract",
                                            "universal_type": "Constraint"},
                      "action": "add"}],
        "verification": [{"obligation_id": "verify_contact_1",
                          "requirement_id": "REQ-CONTACT-1",
                          "method": "contact persistence", "observability": "direct",
                          "target_paths": ["interactions"], "failure_family_ids": ["FF-CONTACT"],
                          "criticality": "critical"}],
        "unknowns": [], "uncovered": [],
    },
    "trivial": {
        "mandatory": [], "conditional": [],
        "evidence": [], "controls": [], "verification": [], "unknowns": [], "uncovered": [],
    },
    # --- KA-1 WP-2 cross-domain fixture payloads (additive; hermetic only) ---
    "a_fighter_performs_a_hip_toss": {
        "mandatory": ["REQ-CONTACT-1", "REQ-SUP-1"],
        "conditional": ["REQ-CAUSAL-1"],
        "evidence": [
            {"atomic_record_id": "ev_combat_ff_rotation",
             "supported_requirement_ids": ["REQ-CONTACT-1"],
             "failure_family_ids": ["FF-CONTACT"],
             "objective_ids": ["OBJ-THROW"],
             "universal_type": "FailureMode",
             "epistemic_status": "known",
             "risk_tokens": ["mirrored_rotation"]},
            {"atomic_record_id": "ev_combat_mech_chain",
             "supported_requirement_ids": ["REQ-CONTACT-1", "REQ-SUP-1"],
             "failure_family_ids": [],
             "objective_ids": ["OBJ-THROW"],
             "universal_type": "Mechanism",
             "epistemic_status": "known",
             "mechanism_tokens": ["force_transfer_chain", "phase_model"]},
            {"atomic_record_id": "ev_combat_con_support",
             "supported_requirement_ids": ["REQ-SUP-1"],
             "failure_family_ids": ["FF-PHYSICS"],
             "objective_ids": ["OBJ-PHYSICAL-PLAUSIBILITY"],
             "universal_type": "Constraint",
             "epistemic_status": "known"},
        ],
        "controls": [
            {"control_id": "ctl_hip_toss_001",
             "control_type": ["CT-CONTACT-CONTRACT"],
             "target": "actor", "scope": "beat", "hardness": "HARD",
             "source": "EVIDENCE_DERIVED",
             "source_requirement_ids": ["REQ-CONTACT-1", "REQ-SUP-1"],
             "supporting_evidence_ids": ["ev_combat_ff_rotation",
                                         "ev_combat_mech_chain",
                                         "ev_combat_con_support"],
             "protected_objectives": ["OBJ-THROW"],
             "prevented_failure_families": ["FF-CONTACT", "FF-PHYSICS"],
             "control_semantics": {"statement": "hip toss throw contract",
                                   "universal_type": "Constraint"},
             "_roles": {"attacker": "fighter_a", "defender": "fighter_b",
                        "initiative": "fighter_a"},
             "_state_before": {"attacker_support": "stable",
                               "defender_support": "stable",
                               "grip": "hip_grip", "balance": "stable"},
             "_contact_interval": {"interval_s": [1.5, 2.5],
                                   "mode_sequence": ["impact", "pivot", "support"]},
             "_phases": [
                 {"action": "underhook_hip_placement", "support_shift": "lateral",
                  "com_displacement": "none", "grip_persists": True,
                  "support_lost": False},
                 {"action": "forward_pull", "support_shift": "forward",
                  "com_displacement": "displaced", "grip_persists": True,
                  "support_lost": False},
                 {"action": "load_bearing", "support_shift": "none",
                  "com_displacement": "lowered", "grip_persists": True,
                  "support_lost": True},
                 {"action": "projection", "support_shift": "none",
                  "com_displacement": "displaced", "grip_persists": False,
                  "support_lost": True},
             ],
             "_projection": {"rotation_axis": "single_axis",
                             "rotating_actor": "defender_only",
                             "force_vector": {"direction": "forward_down",
                                              "magnitude": "body_weight"}},
             "_state_after": {
                 "defender": {"momentum": "reduced", "orientation": "changed",
                              "balance": "unstable"},
                 "attacker": {"balance": "stable"},
             },
             "_recovery": {"allowed": ["plant_hand", "spin_out"],
                           "forbidden": ["mirrored_rotation"]},
             "_world_response": {"water": {"deformation": "splash",
                                           "drag": "velocity_reduction"}},
             "action": "add"},
        ],
        "verification": [
            {"obligation_id": "verify_hip_toss_contact",
             "requirement_id": "REQ-CONTACT-1",
             "method": "contact persistence", "observability": "direct",
             "target_paths": ["interactions"], "failure_family_ids": ["FF-CONTACT"],
             "criticality": "critical"},
        ],
        "unknowns": [], "uncovered": [],
    },
    "a_person_unboxes_a_luxury_watch": {
        "mandatory": ["REQ-OWN-1"],
        "conditional": ["REQ-VIS-1"],
        "evidence": [
            {"atomic_record_id": "ev_ecom_principle_identity",
             "supported_requirement_ids": ["REQ-OWN-1", "REQ-VIS-1"],
             "failure_family_ids": [],
             "objective_ids": ["OBJ-IDENTITY"],
             "universal_type": "Principle",
             "epistemic_status": "known",
             "mechanism_tokens": ["identity_visibility"]},
            {"atomic_record_id": "ev_ecom_ff_logo",
             "supported_requirement_ids": ["REQ-OWN-1"],
             "failure_family_ids": ["FF-IDENTITY"],
             "objective_ids": ["OBJ-IDENTITY"],
             "universal_type": "FailureMode",
             "epistemic_status": "known",
             "risk_tokens": ["logo_visibility_loss"]},
            {"atomic_record_id": "ev_ecom_def_handling",
             "supported_requirement_ids": ["REQ-OWN-1"],
             "failure_family_ids": [],
             "objective_ids": ["OBJ-IDENTITY"],
             "universal_type": "Definition",
             "epistemic_status": "known"},
        ],
        "controls": [
            {"control_id": "ctl_unbox_identity",
             "control_type": ["CT-POSITIVE-INVARIANTS"],
             "target": "object", "scope": "shot", "hardness": "HARD",
             "source": "EVIDENCE_DERIVED",
             "source_requirement_ids": ["REQ-OWN-1"],
             "supporting_evidence_ids": ["ev_ecom_principle_identity",
                                         "ev_ecom_ff_logo"],
             "protected_objectives": ["OBJ-IDENTITY"],
             "prevented_failure_families": ["FF-IDENTITY"],
             "control_semantics": {"statement": "identity continuity invariant",
                                   "universal_type": "Invariant"},
             "action": "add"},
            {"control_id": "ctl_unbox_interaction",
             "control_type": ["CT-CONTACT-CONTRACT"],
             "target": "object", "scope": "beat", "hardness": "HARD",
             "source": "EVIDENCE_DERIVED",
             "source_requirement_ids": ["REQ-OWN-1"],
             "supporting_evidence_ids": ["ev_ecom_principle_identity"],
             "protected_objectives": ["OBJ-IDENTITY"],
             "prevented_failure_families": ["FF-IDENTITY"],
             "control_semantics": {"statement": "hand-object handling contract",
                                   "universal_type": "Constraint"},
             "_roles": {"attacker": "hand", "defender": "watch",
                        "initiative": "hand"},
             "_state_before": {"attacker_support": "stable",
                               "defender_support": "stable",
                               "grip": "case_grip", "balance": "stable"},
             "_contact_interval": {"interval_s": [0.5, 6.0],
                                   "mode_sequence": ["grip", "slide", "support"]},
             "_phases": [
                 {"action": "grasp_case", "support_shift": "none",
                  "com_displacement": "none", "grip_persists": True,
                  "support_lost": False},
                 {"action": "lift_watch", "support_shift": "none",
                  "com_displacement": "displaced", "grip_persists": True,
                  "support_lost": False},
             ],
             "_projection": {"rotation_axis": "single_axis",
                             "rotating_actor": "defender_only",
                             "force_vector": {"direction": "upward",
                                              "magnitude": "hand_supported"}},
             "_state_after": {
                 "defender": {"momentum": "none", "orientation": "changed",
                              "balance": "stable"},
                 "attacker": {"balance": "stable"},
             },
             "_recovery": {"allowed": ["plant_hand"], "forbidden": []},
             "action": "add"},
            {"control_id": "ctl_unbox_visibility",
             "control_type": ["Visibility"],
             "target": "object", "scope": "shot", "hardness": "HARD",
             "source": "EVIDENCE_DERIVED",
             "source_requirement_ids": ["REQ-VIS-1"],
             "supporting_evidence_ids": ["ev_ecom_principle_identity"],
             "protected_objectives": ["OBJ-IDENTITY"],
             "prevented_failure_families": ["FF-CONTINUITY"],
             "control_semantics": {"statement": "defining features stay visible",
                                   "universal_type": "Constraint"},
             "action": "add"},
            {"control_id": "ctl_unbox_camera",
             "control_type": ["CT-CAMERA-CONTRACT"],
             "target": "camera", "scope": "shot", "hardness": "SOFT",
             "source": "EVIDENCE_DERIVED",
             "source_requirement_ids": ["REQ-VIS-1"],
             "supporting_evidence_ids": ["ev_ecom_principle_identity"],
             "protected_objectives": ["OBJ-READABILITY"],
             "prevented_failure_families": ["FF-CAMERA"],
             "control_semantics": {"statement": "camera keeps product readable",
                                   "universal_type": "Recommendation"},
             "action": "add"},
        ],
        "verification": [
            {"obligation_id": "verify_watch_identity",
             "requirement_id": "REQ-OWN-1",
             "method": "logo visibility maintained", "observability": "direct",
             "target_paths": ["entities"], "failure_family_ids": ["FF-IDENTITY"],
             "criticality": "critical"},
        ],
        "unknowns": [], "uncovered": [],
    },
    "a_chef_slices_a_tomato": {
        "mandatory": ["REQ-CONTACT-1"],
        "conditional": ["REQ-SUP-1"],
        "evidence": [
            {"atomic_record_id": "ev_cook_mech_cut",
             "supported_requirement_ids": ["REQ-CONTACT-1"],
             "failure_family_ids": [],
             "objective_ids": ["OBJ-CONTACT"],
             "universal_type": "Mechanism",
             "epistemic_status": "known",
             "mechanism_tokens": ["cut_deformation"]},
            {"atomic_record_id": "ev_cook_ff_hand",
             "supported_requirement_ids": ["REQ-CONTACT-1"],
             "failure_family_ids": ["FF-SAFETY"],
             "objective_ids": ["OBJ-CONTACT"],
             "universal_type": "FailureMode",
             "epistemic_status": "known",
             "risk_tokens": ["hand_safety"]},
            {"atomic_record_id": "ev_cook_con_guard",
             "supported_requirement_ids": ["REQ-CONTACT-1"],
             "failure_family_ids": ["FF-SAFETY"],
             "objective_ids": ["OBJ-CONTACT"],
             "universal_type": "Constraint",
             "epistemic_status": "known",
             "contradiction_ids": ["claim_cut_without_deformation"]},
        ],
        "controls": [
            {"control_id": "ctl_slice_interaction",
             "control_type": ["CT-CONTACT-CONTRACT"],
             "target": "object", "scope": "beat", "hardness": "HARD",
             "source": "EVIDENCE_DERIVED",
             "source_requirement_ids": ["REQ-CONTACT-1"],
             "supporting_evidence_ids": ["ev_cook_mech_cut", "ev_cook_ff_hand"],
             "protected_objectives": ["OBJ-CONTACT"],
             "prevented_failure_families": ["FF-SAFETY"],
             "control_semantics": {"statement": "knife-object cutting interaction",
                                   "universal_type": "Constraint"},
             "_roles": {"attacker": "chef", "defender": "tomato",
                        "initiative": "chef"},
             "_state_before": {"attacker_support": "stable",
                               "defender_support": "stable",
                               "grip": "handle_grip", "balance": "stable"},
             "_contact_interval": {"interval_s": [0.5, 2.0],
                                   "mode_sequence": ["press", "slide"]},
             "_phases": [
                 {"action": "blade_contact", "support_shift": "none",
                  "com_displacement": "none", "grip_persists": True,
                  "support_lost": False},
                 {"action": "cut_through", "support_shift": "none",
                  "com_displacement": "lowered", "grip_persists": False,
                  "support_lost": False},
             ],
             "_projection": {"rotation_axis": "unknown",
                             "rotating_actor": "unknown",
                             "force_vector": {"direction": "downward",
                                              "magnitude": "guided"}},
             "_state_after": {
                 "defender": {"momentum": "none", "orientation": "changed",
                              "balance": "stable"},
                 "attacker": {"balance": "stable"},
             },
             "_recovery": {"allowed": ["plant_hand"], "forbidden": []},
             "_world_response": {"surface": {
                 "deformation": "local_displacement", "drag": "none"}},
             "action": "add"},
        ],
        "verification": [
            {"obligation_id": "verify_slice_safety",
             "requirement_id": "REQ-CONTACT-1",
             "method": "hand safety maintained", "observability": "direct",
             "target_paths": ["interactions"], "failure_family_ids": ["FF-SAFETY"],
             "criticality": "critical"},
        ],
        "unknowns": [], "uncovered": [],
    },
}


class FakeBackend(TreatmentBackend):
    """Hermetic deterministic backend for structural tests ONLY.

    Production integration must never silently fall back to this."""

    def __init__(self, fixtures: dict[str, dict[str, Any]] | None = None):
        self.fixtures = fixtures or FAKE_FIXTURES

    def plan(
        self,
        intent_text: str,
        normalized_intent: dict[str, Any],
        *,
        query_mode: str = "INITIAL_GENERATION",
        discrepancy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source_intent_hash = _sha(normalized_intent)
        if query_mode == "REPAIR_GAP":
            fx = dict(FAKE_FIXTURES["simple_motion"])
            fx["query_mode_note"] = "repair"
            for d in (discrepancy or {}).get("discrepancies", []):
                fx["mandatory"] = sorted(set(fx["mandatory"]) | set(
                    d.get("affected_requirement_ids", [])))
                fx["controls"] = fx["controls"] + [
                    {"control_id": "ctl_repair_" + d["discrepancy_id"][-8:],
                     "control_type": ["CT-POSITIVE-INVARIANTS"],
                     "target": "scene", "scope": "scene", "hardness": "HARD",
                     "source": "EVIDENCE_DERIVED",
                     "source_requirement_ids": d.get("affected_requirement_ids", []),
                     "supporting_evidence_ids": ["ev_repair_" + d["discrepancy_id"][-8:]],
                     "protected_objectives": d.get("affected_objectives", []),
                     "prevented_failure_families": d.get("failure_families", []),
                     "control_semantics": {"statement": "repair invariant",
                                           "universal_type": "Invariant"},
                     "action": "strengthen"}]
                fx["evidence"] = fx["evidence"] + [
                    {"atomic_record_id": "ev_repair_" + d["discrepancy_id"][-8:],
                     "supported_requirement_ids": d.get("affected_requirement_ids", []),
                     "failure_family_ids": d.get("failure_families", []),
                     "objective_ids": d.get("affected_objectives", [])}]
            fx["uncovered"] = []
        else:
            norm = intent_text.strip().lower().replace(" ", "_")
            fx = self.fixtures.get(norm, None)
            if fx is None:
                # deterministic fallback: keyed by a fixture token in the intent
                for key, value in self.fixtures.items():
                    if key in norm or key.replace("_", " ") in intent_text.strip().lower():
                        fx = value
                        break
            if fx is None:
                fx = dict(FAKE_FIXTURES["trivial"])
                # per-domain deliberation fixtures (structured, deterministic)
                if "occlusion" in norm or "pillar" in norm:
                    fx = dict(FAKE_FIXTURES["simple_motion"])
                    fx["mandatory"] = ["REQ-VIS-1", "REQ-CONTACT-1"]
                    fx["evidence"] = fx["evidence"] + [{
                        "atomic_record_id": "ev_vis_001",
                        "supported_requirement_ids": ["REQ-VIS-1"],
                        "failure_family_ids": ["FF-CONTINUITY"],
                        "objective_ids": ["OBJ-CONTINUITY"],
                        "universal_type": "Concept"}]
                    fx["uncovered"] = []
                elif "camera" in norm:
                    fx = dict(FAKE_FIXTURES["simple_motion"])
                    fx["mandatory"] = ["REQ-CAM-1", "REQ-CONTACT-1"]
                    fx["evidence"] = fx["evidence"] + [{
                        "atomic_record_id": "ev_cam_001",
                        "supported_requirement_ids": ["REQ-CAM-1"],
                        "failure_family_ids": ["FF-CAMERA"],
                        "objective_ids": ["OBJ-READABILITY"],
                        "universal_type": "Constraint"}]
                elif "possession" in norm or "transfer" in norm or "takes" in norm:
                    fx = dict(FAKE_FIXTURES["simple_motion"])
                    fx["mandatory"] = ["REQ-OWN-1"]
                elif "support" in norm or "fall" in norm or "catches" in norm:
                    fx = dict(FAKE_FIXTURES["simple_motion"])
                    fx["mandatory"] = ["REQ-SUP-1"]
                elif "causal" in norm or "knocks" in norm:
                    fx = dict(FAKE_FIXTURES["simple_motion"])
                    fx["mandatory"] = ["REQ-CAUSAL-1", "REQ-CONTACT-1"]
        return build_treatment_packet(
            treatment_id="treatment_" + source_intent_hash[:16],
            source_intent_hash=source_intent_hash,
            query_mode=query_mode,
            activated_requirements=fx["mandatory"] + fx["conditional"],
            mandatory_requirements=fx["mandatory"],
            conditional_requirements=fx["conditional"],
            required_pathways={r: "COVERED_STRONG" for r in fx["mandatory"]},
            objectives_at_risk=sorted({o for c in fx["controls"]
                                       for o in c["protected_objectives"]}),
            predicted_failure_families=sorted({f for c in fx["controls"]
                                               for f in c["prevented_failure_families"]}),
            retrieved_evidence=fx["evidence"],
            proposed_obligations=[
                {"obligation_id": "obl_" + r, "requirement_id": r,
                 "kinds": ["CONTROL", "VERIFICATION"], "status": "REPRESENTED"}
                for r in fx["mandatory"]],
            proposed_controls=fx["controls"],
            verification_obligations=fx["verification"],
            unknowns=fx["unknowns"],
            uncovered_mandatory_requirements=fx["uncovered"],
            architecture_freeze_identity="fake-arch-v2",
            retrieval_runtime_freeze_identity="fake-runtime-v1",
        )


def get_backend() -> TreatmentBackend:
    """Frozen runtime when CPCS_FROZEN_RUNTIME_PATH is set; otherwise raises
    BackendUnavailableError (never FakeBackend)."""
    return FrozenRuntimeBackend()


# ---------------------------------------------------------------------------
# Application operation handlers (registered additively in service.py)
# ---------------------------------------------------------------------------

def _normalized_intent_context(text: str, root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    from lab.second_brain.src.intent import build_intent_context

    ic = build_intent_context(text, root=root)
    return ic["normalized_intent"], ic


def apply_structured_objects(score: dict[str, Any], structured_objects: list[dict[str, Any]]) -> None:
    """Append typed structured objects into the existing canonical families."""
    for obj in structured_objects:
        target = obj["target"]
        if target == "entities[]":
            score["entities"].append(obj["value"])
        elif target == "interactions[]":
            score["interactions"].append(obj["value"])
        elif target == "beats[]":
            score["beats"].append(obj["value"])
        elif target.startswith("continuity."):
            key = target.split("continuity.", 1)[1].replace("[]", "")
            score["continuity"].setdefault(key, []).append(obj["value"])
        elif target.startswith("camera."):
            key = target.split("camera.", 1)[1].replace("[]", "")
            score["camera"].setdefault(key, []).append(obj["value"])
        elif target.startswith("performance."):
            key = target.split("performance.", 1)[1].replace("[]", "")
            score["performance"].setdefault(key, []).append(obj["value"])
        elif target.startswith("style."):
            key = target.split("style.", 1)[1].replace("[]", "")
            score["style"].setdefault(key, []).append(obj["value"])
        elif target.startswith("editing."):
            key = target.split("editing.", 1)[1].replace("[]", "")
            score["editing"].setdefault(key, []).append(obj["value"])
        else:
            score["warnings"].append({
                "code": "cpcs_structured_target_unknown",
                "message": f"structured target not applicable: {target}",
            })


def handler_reasoning_experimental_plan(arguments: dict[str, Any], root: Path):
    intent, ic = _normalized_intent_context(arguments["intent_text"], root)
    backend = FrozenRuntimeBackend()
    packet = backend.plan(arguments["intent_text"], intent, query_mode="INITIAL_GENERATION")
    translation = TreatmentAdapter(root).translate(packet)
    return {
        "treatment_packet": packet,
        "treatment_packet_hash": packet["packet_hash"],
        "translation": {
            "overlay_ids": [o["overlay_id"] for o in translation.overlays],
            "unsupported_mappings": translation.unsupported_mappings,
            "verification_requirement_count": len(translation.verification_requirements),
            "provider_neutral_control_count": len(translation.provider_neutral_controls),
            "warnings": translation.warnings,
            "lineage": translation.lineage,
        },
        "status": "COMPLETE" if not packet["uncovered_mandatory_requirements"] else "INCOMPLETE",
    }


def handler_reasoning_experiment_prepare(arguments: dict[str, Any], root: Path):
    """A/B preparation: one isolated upstream factor (reasoning_policy)."""
    from lab.compiler.build import make_build_request
    from lab.compiler.score import make_score_request, resolve_score

    intent, ic = _normalized_intent_context(arguments["intent_text"], root)
    backend = FrozenRuntimeBackend()
    packet = backend.plan(arguments["intent_text"], intent, query_mode="INITIAL_GENERATION")
    translation = TreatmentAdapter(root).translate(packet)
    shared = {
        "provider": arguments.get("provider", "google_vertex_ai"),
        "model": arguments.get("model_version", "veo-3.1-generate-001"),
        "duration_seconds": arguments.get("duration_seconds", 8),
        "aspect_ratio": arguments.get("aspect_ratio", "16:9"),
        "seed": arguments.get("seed", 7),
        "sample_count": arguments.get("generation_count", 1),
        "resolution": arguments.get("resolution", "720p"),
    }
    score_a = resolve_score(make_score_request(ic, overlays=[]), root)
    build_a = make_build_request(
        score_a, project_id=arguments.get("project_id", "cpcs-ab-project"),
        duration_seconds=shared["duration_seconds"], aspect_ratio=shared["aspect_ratio"],
        seed=shared["seed"], sample_count=shared["sample_count"],
        resolution=shared["resolution"],
    )
    score_b = resolve_score(make_score_request(ic, overlays=translation.overlays), root)
    # The resolved score is NEVER mutated post-resolution (canonical score_id
    # integrity): treatment verification obligations, typed controls,
    # structured objects, and warnings travel alongside the build request in
    # the experiment package, not inside the score.
    build_b = make_build_request(
        score_b, project_id=arguments.get("project_id", "cpcs-ab-project"),
        duration_seconds=shared["duration_seconds"], aspect_ratio=shared["aspect_ratio"],
        seed=shared["seed"], sample_count=shared["sample_count"],
        resolution=shared["resolution"],
    )
    if packet["uncovered_mandatory_requirements"]:
        raise ValueError(
            "treatment B has uncovered mandatory requirements and cannot be "
            "represented as a valid compiled arm: "
            + ",".join(sorted(packet["uncovered_mandatory_requirements"]))
        )
    return {
        "experiment_id": arguments["flight_id"],
        "experiment_kind": "reasoning_layer_ab",
        "shared_input_hash": _sha(
            {"intent": intent, "shared": shared}
        ),
        "arm_a": {
            "reasoning_policy": "CURRENT_BASELINE",
            "normalized_intent_hash": _sha(intent),
            "build_request": build_a,
            "treatment_packet_id": None,
            "treatment_packet_hash": None,
            "overlay_ids": [],
            "unsupported_mappings": [],
            "verification_obligations": [],
            "typed_controls": [],
            "structured_objects": [],
            "warnings": [],
        },
        "arm_b": {
            "reasoning_policy": "CPCS_REASONING_V1",
            "normalized_intent_hash": _sha(intent),
            "build_request": build_b,
            "treatment_packet_id": packet["treatment_id"],
            "treatment_packet_hash": packet["packet_hash"],
            "overlay_ids": [o["overlay_id"] for o in translation.overlays],
            "unsupported_mappings": translation.unsupported_mappings,
            "verification_obligations": translation.verification_requirements,
            "typed_controls": translation.provider_neutral_controls,
            "structured_objects": translation.structured_objects,
            "warnings": translation.warnings,
        },
        "confounder_check": {"same_intent": True, "same_provider_parameters": True},
        "shared_downstream_compiler": True,
        "shared_evaluation_path": True,
        "differences_before_treatment": [],
    }


def handler_reasoning_experiment_inspect(arguments: dict[str, Any], root: Path):
    plan = handler_reasoning_experiment_prepare(arguments, root)
    return {
        "experiment_id": plan["experiment_id"],
        "experiment_kind": plan["experiment_kind"],
        "arm_a": {k: v for k, v in plan["arm_a"].items() if k != "build_request"},
        "arm_b": {k: v for k, v in plan["arm_b"].items() if k != "build_request"},
        "shared_downstream_compiler": plan["shared_downstream_compiler"],
        "shared_evaluation_path": plan["shared_evaluation_path"],
        "differences_before_treatment": plan["differences_before_treatment"],
    }


def handler_repair_gap_prepare(arguments: dict[str, Any], root: Path):
    return DiscrepancyBuilder().build(
        arguments["expected_states"],
        arguments.get("observations", []),
        user_complaint=arguments.get("user_complaint"),
        source=arguments.get("source", {}),
    )


def handler_repair_plan(arguments: dict[str, Any], root: Path):
    """REPAIR_GAP -> RepairControlPlan -> existing compiler overlays (RC-1)."""
    from lab.compiler.build import make_build_request
    from lab.compiler.score import make_score_request, resolve_score

    intent, ic = _normalized_intent_context(arguments["intent_text"], root)
    backend = FrozenRuntimeBackend()
    discrepancy = arguments["discrepancy_packet"]
    repair_packet = backend.plan(
        arguments["intent_text"], intent, query_mode="REPAIR_GAP", discrepancy=discrepancy
    )
    plan = RepairPlanner().plan(discrepancy, backend, arguments["intent_text"],
                                intent, original_packet=repair_packet)
    translation = TreatmentAdapter(root).translate(repair_packet)
    # The resolved score is NEVER mutated post-resolution (canonical score_id
    # integrity): repair treatment objects travel alongside the build request.
    score = resolve_score(make_score_request(ic, overlays=translation.overlays), root)
    build = make_build_request(
        score, project_id=arguments.get("project_id", "cpcs-repair-project"),
    )
    return {
        "repair_control_plan": plan,
        "translation": {
            "overlay_ids": [o["overlay_id"] for o in translation.overlays],
            "unsupported_mappings": translation.unsupported_mappings,
            "verification_obligations": translation.verification_requirements,
            "typed_controls": translation.provider_neutral_controls,
            "structured_objects": translation.structured_objects,
        },
        "revised_build_request": build,
        "lineage": plan["lineage"],
    }


def handler_repair_inspect(arguments: dict[str, Any], root: Path):
    return handler_repair_plan(arguments, root)
