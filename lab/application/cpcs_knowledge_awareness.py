"""KA-2.1 — PASS 1 broad knowledge awareness + workflow tag model.

Answers: "What expertise families could consequentially matter for this
creative request?" — BEFORE recruitment decides what actually matters.

Tags are activation hints, recruitment evidence, prioritization signals,
and evaluation descriptors. They NEVER gate frozen retrieval, exclude
recall upstream, directly become canonical controls, override structured
evidence, or replace canonical_concept_ids / triggers / objectives /
failures / requirements.

Levels:
  L0 UNIVERSAL — evaluated for every request (ALWAYS_CONSIDER: evaluate
                 whether it matters; never force into prompts).
  L1 WORKFLOW  — video class hints (not mutually exclusive).
  L2 EXPERTISE — corpus-supported knowledge families; provenance maps to
                 frozen-corpus document IDs.
  L3 MECHANISM — derived from existing structured IDs (canonical_concept_ids,
                 trigger_ids, objective_ids, failure_family_ids,
                 requirement_ids); no new taxonomy.

Deterministic structured-token inference only. No LLM, no prose mining.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

AWARENESS_SCHEMA = "cpcs.knowledge_awareness_profile/0.1"
TAG_SCHEMA = "cpcs.knowledge_tag/0.1"

TAG_ORIGINS = frozenset(
    {"CORPUS_DECLARED", "STRUCTURED_DERIVED", "WORKFLOW_DERIVED",
     "INTENT_ACTIVATED"})

# ---------------------------------------------------------------------------
# L0 — universal considerations (ALWAYS_CONSIDER: evaluate, never force)
# ---------------------------------------------------------------------------
UNIVERSAL_CONSIDERATIONS: list[dict[str, Any]] = [
    {"consideration_id": "UC_IDENTITY_PERSISTENCE",
     "description": "entities keep identity and defining features across the video",
     "corpus_doc_ids": ["more_control_03_camera",
                        "cpcs_reference_living_performance_realism"]},
    {"consideration_id": "UC_CAUSAL_ORDER",
     "description": "reactions follow their causes; contact precedes effect",
     "corpus_doc_ids": ["continuous_combat_state_contact_coarticulation_anime_time_volumetric_cinematography",
                        "03_mx_hierarchical_motion_grammar_gap_closure_research"]},
    {"consideration_id": "UC_TEMPORAL_COHERENCE",
     "description": "event order and timing stay coherent and beat-scoped",
     "corpus_doc_ids": ["granular_motion_control_for_ai_video_generation",
                        "03_mx_hierarchical_motion_grammar_gap_closure_research"]},
    {"consideration_id": "UC_CONTINUITY",
     "description": "state, wardrobe, props, and screen direction persist across cuts",
     "corpus_doc_ids": ["more_control_03_camera",
                        "cpcs_reference_living_performance_realism"]},
    {"consideration_id": "UC_STATE_CONSISTENCY",
     "description": "no unsupported state transition; state changes only through events",
     "corpus_doc_ids": ["continuous_combat_state_contact_coarticulation_anime_time_volumetric_cinematography",
                        "ug008_articulated_deformable_hand_object_state_transitions"]},
    {"consideration_id": "UC_CAMERA_READABILITY",
     "description": "the camera keeps the critical event perceivable",
     "corpus_doc_ids": ["more_control_03_camera",
                        "01_ai_video_motion_direction_kb_gap_closure_research"]},
    {"consideration_id": "UC_PHYSICAL_PLAUSIBILITY",
     "description": "weight, momentum, support, and contact read plausibly",
     "corpus_doc_ids": ["continuous_combat_state_contact_coarticulation_anime_time_volumetric_cinematography",
                        "granular_motion_control_for_ai_video_generation"]},
    {"consideration_id": "UC_VERIFICATION_CRITICAL_OUTCOMES",
     "description": "critical outcomes carry observable verification criteria",
     "corpus_doc_ids": ["kinetic_motion_direction_prompting_manual",
                        "director_motion_reasoning_runtime_gap_closure"]},
]

# ---------------------------------------------------------------------------
# L1 — workflow / video class tags (deterministic token vocabularies)
# ---------------------------------------------------------------------------
WORKFLOW_TOKEN_TAGS: dict[str, tuple[str, ...]] = {
    "ACTION": ("action", "fight", "fighter", "combat", "opponent", "punch",
               "kick", "throw", "swing", "chase", "attack", "battle", "duel",
               "catch", "strike", "slam"),
    "FIGHT": ("fight", "fighter", "combat", "opponent", "punch", "kick",
              "throw", "swing", "attack", "battle", "duel", "catch",
              "strike", "slam", "leg", "arc"),
    "UGC": ("creator", "handheld", "casual", "selfie", "phone camera",
            "records", "talks to the viewer", "vlog", "self-framing"),
    "ECOMMERCE": ("product", "unbox", "unboxes", "bottle", "serum", "label",
                  "luxury", "premium", "for sale", "ad"),
    "UGC_ECOMMERCE": ("creator", "handheld", "unbox", "unboxes",
                      "vlog", "selfie"),
    "PRODUCT_DEMO": ("demonstr", "showcase", "unbox", "tutorial", "how to",
                     "review", "demo"),
    "DIALOGUE": ("talk", "says", "dialogue", "line", "voice", "speaks",
                 "whisper", "conversation"),
    "PERFORMANCE": ("performer", "actor", "reacts", "react", "expression",
                    "emotional", "dance", "dancers", "performance", "face",
                    "smile", "concern", "looks at"),
    "OBJECT_MANIPULATION": ("hands", "hand", "picks", "grab", "grasp",
                            "unscrews", "dispenses", "rubs", "applies",
                            "assembles", "opens", "turns", "holds", "slices",
                            "pours", "carries"),
    "COOKING": ("chef", "slice", "slices", "kitchen", "recipe", "cook",
                "tomato", "cutting", "chop"),
    "VEHICLE": ("car", "vehicle", "drive", "drives"),
    "ENVIRONMENT": ("water", "rain", "desert", "street", "room", "stage",
                    "pedestal", "landscape", "mountain", "ocean", "floor"),
    "CINEMATIC_NARRATIVE": ("cinematic", "story", "narrat", "dramatic",
                            "film", "scene"),
    "CAMERA_CENTRIC": ("camera", "shot", "close-up", "closeup", "macro",
                       "drone", "pedestal", "orbit", "circles", "pan"),
}

# ---------------------------------------------------------------------------
# L2 — expertise tags with frozen-corpus provenance (doc IDs are real)
# ---------------------------------------------------------------------------
EXPERTISE_TAGS: dict[str, dict[str, Any]] = {
    "FACS": {"corpus_doc_ids": [
        "02_facs_laban_bartenieff_gap_closure_completed",
        "cpcs_facs_laban_ai_video_directorial_control_research_paper",
        "behavior_layer"]},
    "LABAN": {"corpus_doc_ids": [
        "02_facs_laban_bartenieff_gap_closure_completed",
        "cpcs_facs_laban_ai_video_directorial_control_research_paper"]},
    "BARTENIEFF": {"corpus_doc_ids": [
        "02_facs_laban_bartenieff_gap_closure_completed"]},
    "GAZE_ATTENTION": {"corpus_doc_ids": ["behavior_layer",
        "cpcs_reference_living_performance_realism"]},
    "LIVING_PERFORMANCE": {"corpus_doc_ids": [
        "cpcs_reference_living_performance_realism", "behavior_layer"]},
    "CAPTURE_REALISM": {"corpus_doc_ids": [
        "cpcs_reference_capture_surface_realism",
        "cpcs_reference_living_performance_realism"]},
    "HAND_OBJECT_CONTACT": {"corpus_doc_ids": [
        "ug008_articulated_deformable_hand_object_state_transitions",
        "gap_answer_01_articulated_deformable_hand_object"]},
    "PRODUCT_IDENTITY": {"corpus_doc_ids": [
        "kinetic_motion_direction_prompting_manual",
        "cpcs_reference_living_performance_realism"]},
    "MATERIAL_RESPONSE": {"corpus_doc_ids": [
        "03_mx_hierarchical_motion_grammar_gap_closure_research",
        "granular_motion_control_for_ai_video_generation"]},
    "SUPPORT_CONTACT": {"corpus_doc_ids": [
        "02_facs_laban_bartenieff_gap_closure_completed",
        "continuous_combat_state_contact_coarticulation_anime_time_volumetric_cinematography"]},
    "BIOMECHANICS": {"corpus_doc_ids": [
        "01_ai_video_motion_direction_kb_gap_closure_research"]},
    "FORCE_TRANSFER": {"corpus_doc_ids": [
        "continuous_combat_state_contact_coarticulation_anime_time_volumetric_cinematography",
        "granular_motion_control_for_ai_video_generation"]},
    "MOMENTUM": {"corpus_doc_ids": [
        "more_control_03_camera",
        "granular_motion_control_for_ai_video_generation"]},
    "RECOVERY": {"corpus_doc_ids": [
        "continuous_combat_state_contact_coarticulation_anime_time_volumetric_cinematography"]},
    "CONTACT_TOPOLOGY": {"corpus_doc_ids": [
        "continuous_combat_state_contact_coarticulation_anime_time_volumetric_cinematography",
        "gap_answer_04_directing_contact_causality"]},
    "OBJECT_STATE_TRANSITION": {"corpus_doc_ids": [
        "ug008_articulated_deformable_hand_object_state_transitions"]},
    "DIALOGUE_TIMING": {"corpus_doc_ids": [
        "cpcs_reference_natural_dialogue_mode"]},
    "CAMERA_CONTINUITY": {"corpus_doc_ids": [
        "more_control_03_camera",
        "continuous_combat_state_contact_coarticulation_anime_time_volumetric_cinematography"]},
    "VISIBILITY_PERSISTENCE": {"corpus_doc_ids": [
        "more_control_03_camera",
        "ug008_articulated_deformable_hand_object_state_transitions"]},
    "COMBAT_STATE": {"corpus_doc_ids": [
        "continuous_combat_state_contact_coarticulation_anime_time_volumetric_cinematography",
        "kinetic_motion_direction_prompting_manual"]},
}

# Workflow tag -> candidate expertise tags (HINTS ONLY: workflow tags add
# candidate evidence; they are never the sole recruitment reason).
WORKFLOW_TO_EXPERTISE: dict[str, tuple[str, ...]] = {
    "FIGHT": ("COMBAT_STATE", "SUPPORT_CONTACT", "FORCE_TRANSFER", "MOMENTUM",
              "RECOVERY", "CONTACT_TOPOLOGY", "BIOMECHANICS",
              "CAMERA_CONTINUITY"),
    "UGC": ("CAPTURE_REALISM", "LIVING_PERFORMANCE", "DIALOGUE_TIMING"),
    "ECOMMERCE": ("PRODUCT_IDENTITY", "HAND_OBJECT_CONTACT",
                  "OBJECT_STATE_TRANSITION", "VISIBILITY_PERSISTENCE",
                  "MATERIAL_RESPONSE"),
    "UGC_ECOMMERCE": ("CAPTURE_REALISM", "LIVING_PERFORMANCE", "FACS",
                      "GAZE_ATTENTION", "PRODUCT_IDENTITY",
                      "HAND_OBJECT_CONTACT", "OBJECT_STATE_TRANSITION",
                      "DIALOGUE_TIMING", "MATERIAL_RESPONSE",
                      "VISIBILITY_PERSISTENCE"),
    "PRODUCT_DEMO": ("PRODUCT_IDENTITY", "HAND_OBJECT_CONTACT",
                     "OBJECT_STATE_TRANSITION", "VISIBILITY_PERSISTENCE",
                     "MATERIAL_RESPONSE"),
    "DIALOGUE": ("DIALOGUE_TIMING", "FACS", "GAZE_ATTENTION",
                 "LIVING_PERFORMANCE"),
    "PERFORMANCE": ("FACS", "GAZE_ATTENTION", "LABAN", "BARTENIEFF",
                    "LIVING_PERFORMANCE", "DIALOGUE_TIMING"),
    "OBJECT_MANIPULATION": ("HAND_OBJECT_CONTACT", "OBJECT_STATE_TRANSITION",
                            "SUPPORT_CONTACT"),
    "COOKING": ("HAND_OBJECT_CONTACT", "MATERIAL_RESPONSE",
                "OBJECT_STATE_TRANSITION"),
    "VEHICLE": ("BIOMECHANICS", "MATERIAL_RESPONSE"),
    "ENVIRONMENT": ("MATERIAL_RESPONSE", "CAMERA_CONTINUITY"),
    "CAMERA_CENTRIC": ("CAMERA_CONTINUITY", "VISIBILITY_PERSISTENCE"),
    "CINEMATIC_NARRATIVE": ("CAMERA_CONTINUITY", "LIVING_PERFORMANCE"),
}

# Intent-signal vocabularies (deterministic token vocab; corpus-aligned)
INTENT_SIGNAL_VOCAB: dict[str, dict[str, tuple[str, ...]]] = {
    "interaction_tokens": {
        "tokens": ("grab", "grips", "hold", "holds", "touch", "touches",
                   "unbox", "unboxes", "slice", "slices", "throw", "throws",
                   "catch", "catches", "swing", "swings", "lift", "lifts",
                   "rub", "rubs", "apply", "applies", "dispense", "dispenses",
                   "unscrew", "unscrews", "pick", "picks", "carry", "carries",
                   "press", "presses", "release", "releases"),
        "failure_families": ("FF-CONTACT",),
    },
    "state_change_tokens": {
        "tokens": ("open", "opens", "close", "closes", "fall", "falls",
                   "drop", "drops", "release", "releases", "spill", "spills",
                   "crack", "cracks", "unscrew", "unscrews", "turn", "turns",
                   "slide", "slides", "land", "lands", "rotate", "rotates"),
        "failure_families": ("FF-CONTACT", "FF-CAUSALITY"),
    },
    "performance_tokens": {
        "tokens": ("smile", "smiles", "react", "reacts", "expression",
                   "looks", "gaze", "face", "talk", "talks", "concern",
                   "laugh", "emotion", "speaks", "whisper"),
        "failure_families": ("FF-CONTINUITY",),
    },
    "perception_tokens": {
        "tokens": ("visible", "label", "close-up", "closeup", "macro",
                   "readable", "camera", "orbit", "circles", "framing"),
        "failure_families": ("FF-CAMERA", "FF-VISIBILITY"),
    },
    "environment_tokens": {
        "tokens": ("water", "rain", "desk", "floor", "counter", "stage",
                   "street", "desert", "pedestal", "bathroom", "surface"),
        "failure_families": ("FF-DEFORMATION",),
    },
}


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass
class KnowledgeTag:
    tag: str
    tag_level: int
    source: str
    corpus_doc_ids: list[str]
    evidence_tokens: list[str]
    status: str
    lineage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TAG_SCHEMA,
            "tag": self.tag,
            "tag_level": self.tag_level,
            "source": self.source,
            "corpus_doc_ids": self.corpus_doc_ids,
            "evidence_tokens": self.evidence_tokens,
            "status": self.status,
            "lineage": self.lineage,
        }


def _token_matches(tokens: tuple[str, ...], text: str) -> list[str]:
    """Word-boundary matching; hyphens and multi-word tokens supported."""
    return sorted({t for t in tokens
                   if re.search(rf"\b{re.escape(t)}\b", text)})


def detect_workflow_tags(intent_text: str) -> list[KnowledgeTag]:
    """Deterministic L1 workflow tags from structured token vocabularies."""
    low = intent_text.lower()
    tags: list[KnowledgeTag] = []
    for tag, tokens in sorted(WORKFLOW_TOKEN_TAGS.items()):
        matched = _token_matches(tokens, low)
        if not matched:
            continue
        tags.append(KnowledgeTag(
            tag=tag, tag_level=1, source="INTENT_ACTIVATED",
            corpus_doc_ids=[], evidence_tokens=matched, status="ACTIVE",
            lineage={"detection": "structured_token_vocabulary"}))
    return tags


def detect_intent_signals(intent_text: str) -> dict[str, list[str]]:
    low = intent_text.lower()
    signals: dict[str, list[str]] = {
        "interactions": [], "state_changes": [], "performance": [],
        "perception": [], "environment_material": [],
    }
    key_map = {
        "interaction_tokens": "interactions",
        "state_change_tokens": "state_changes",
        "performance_tokens": "performance",
        "perception_tokens": "perception",
        "environment_tokens": "environment_material",
    }
    for vocab_key, target in key_map.items():
        vocab = INTENT_SIGNAL_VOCAB[vocab_key]
        matched = _token_matches(vocab["tokens"], low)
        if matched:
            signals[target] = matched
    return signals


def candidate_expertise_tags(workflow_tags: list[KnowledgeTag]
                             ) -> list[KnowledgeTag]:
    """L2 candidate expertise tags implied by L1 workflow hints."""
    out: dict[str, list[str]] = {}
    for wt in workflow_tags:
        for expertise in WORKFLOW_TO_EXPERTISE.get(wt.tag, ()):
            out.setdefault(expertise, []).append(wt.tag)
    tags: list[KnowledgeTag] = []
    for tag, implied_by in sorted(out.items()):
        meta = EXPERTISE_TAGS[tag]
        tags.append(KnowledgeTag(
            tag=tag, tag_level=2, source="WORKFLOW_DERIVED",
            corpus_doc_ids=sorted(meta["corpus_doc_ids"]),
            evidence_tokens=sorted(implied_by), status="CANDIDATE",
            lineage={"implied_by_workflow_tags": sorted(implied_by)}))
    return tags


@dataclass
class KnowledgeAwarenessProfile:
    profile_id: str
    profile_hash: str
    active_workflow_tags: list[dict[str, Any]]
    candidate_expertise_tags: list[dict[str, Any]]
    universal_considerations: list[dict[str, Any]]
    intent_signals: dict[str, list[str]]
    predicted_failure_families: list[str]
    activation_failure_families: list[str]
    uncertainties: list[dict[str, str]]
    lineage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": AWARENESS_SCHEMA,
            "profile_id": self.profile_id,
            "profile_hash": self.profile_hash,
            "active_workflow_tags": self.active_workflow_tags,
            "candidate_expertise_tags": self.candidate_expertise_tags,
            "universal_considerations": self.universal_considerations,
            "intent_signals": self.intent_signals,
            "predicted_failure_families": self.predicted_failure_families,
            "activation_failure_families": self.activation_failure_families,
            "uncertainties": self.uncertainties,
            "lineage": self.lineage,
        }


def build_awareness_profile(intent_text: str,
                            activation: dict[str, Any] | None = None
                            ) -> KnowledgeAwarenessProfile:
    """PASS 1: broad, recall-oriented. Does NOT gate retrieval and does
    NOT decide final recruitment."""
    workflow_tags = detect_workflow_tags(intent_text)
    expertise_tags = candidate_expertise_tags(workflow_tags)
    signals = detect_intent_signals(intent_text)
    token_failures: set[str] = set()
    activation_failures: set[str] = set(
        activation.get("candidate_failure_families", []) or []) \
        if activation else set()
    signal_to_vocab = {
        "interactions": "interaction_tokens",
        "state_changes": "state_change_tokens",
        "performance": "performance_tokens",
        "perception": "perception_tokens",
        "environment_material": "environment_tokens",
    }
    for signal_key, vocab_key in signal_to_vocab.items():
        if signals.get(signal_key):
            token_failures.update(
                INTENT_SIGNAL_VOCAB[vocab_key]["failure_families"])
    uncertainties: list[dict[str, str]] = []
    if not workflow_tags:
        uncertainties.append({
            "kind": "AWARENESS_FAILURE_CANDIDATE",
            "message": "no workflow tag matched; PASS 1 runs universal "
                       "considerations only",
        })
    # KA-2.4: predicted_failure_families is TOKEN-DERIVED ONLY (the honest
    # intent signal). Activation-derived failures are retrieval-adjacent
    # (query attribution) and are reported separately so recruitment
    # never conflates them with intent prediction.
    body = {
        "workflow_tags": [t.to_dict() for t in workflow_tags],
        "expertise_tags": [t.to_dict() for t in expertise_tags],
        "universal_consideration_ids": sorted(
            u["consideration_id"] for u in UNIVERSAL_CONSIDERATIONS),
        "intent_signals": signals,
        "predicted_failure_families": sorted(token_failures),
        "activation_failure_families": sorted(activation_failures),
        "uncertainties": uncertainties,
    }
    profile_id = "aware_" + _sha(body)[:16]
    profile_hash = _sha(body)
    return KnowledgeAwarenessProfile(
        profile_id=profile_id,
        profile_hash=profile_hash,
        active_workflow_tags=body["workflow_tags"],
        candidate_expertise_tags=body["expertise_tags"],
        universal_considerations=list(UNIVERSAL_CONSIDERATIONS),
        intent_signals=signals,
        predicted_failure_families=sorted(token_failures),
        activation_failure_families=sorted(activation_failures),
        uncertainties=uncertainties,
        lineage={
            "activation_packet_id": (activation or {}).get("packet_id", "unknown"),
            "source": "PASS1_structured_token_awareness",
        },
    )
