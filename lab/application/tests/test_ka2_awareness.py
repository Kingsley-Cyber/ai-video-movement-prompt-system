"""KA-2.1 — PASS 1 awareness profile + workflow tag model (hermetic)."""
from __future__ import annotations

import unittest

from lab.application.cpcs_knowledge_awareness import (
    EXPERTISE_TAGS,
    UNIVERSAL_CONSIDERATIONS,
    WORKFLOW_TO_EXPERTISE,
    build_awareness_profile,
    detect_intent_signals,
    detect_workflow_tags,
)

SERUM_INTENT = (
    "A woman records a casual handheld creator video trying a premium facial "
    "serum. She picks the bottle up from the bathroom counter, turns it so "
    "the label is visible, unscrews the dropper, dispenses two drops on the "
    "back of her other hand, rubs the serum between her fingers, applies it "
    "to her cheek, notices the texture, reacts positively, talks naturally "
    "to the viewer, then brings the bottle near the phone camera for the "
    "final product shot."
)
FIGHT_INTENT = (
    "A fighter catches an opponent's leg, swings him in a wide arc, releases "
    "him onto the water, then immediately pressures him while he tries to "
    "recover."
)
PRODUCT_ONLY_INTENT = (
    "Macro product-only serum bottle rotating slowly on a pedestal. No "
    "person is visible."
)
DESERT_INTENT = "A drone shot over an empty desert at golden hour."


class Ka2Awareness(unittest.TestCase):

    def test_serum_activates_multiple_workflow_tags(self):
        tags = {t.tag for t in detect_workflow_tags(SERUM_INTENT)}
        self.assertTrue({"UGC", "ECOMMERCE", "OBJECT_MANIPULATION",
                         "PERFORMANCE"} <= tags,
                        f"missing workflow tags: {tags}")

    def test_fight_activates_fight_and_action(self):
        tags = {t.tag for t in detect_workflow_tags(FIGHT_INTENT)}
        self.assertIn("FIGHT", tags)
        self.assertIn("ACTION", tags)

    def test_product_only_has_no_person_tags(self):
        tags = {t.tag for t in detect_workflow_tags(PRODUCT_ONLY_INTENT)}
        self.assertIn("ECOMMERCE", tags)
        self.assertNotIn("PERFORMANCE", tags)
        self.assertNotIn("UGC", tags)
        self.assertNotIn("DIALOGUE", tags)

    def test_word_boundary_no_surface_face_false_positive(self):
        tags = {t.tag for t in detect_workflow_tags(
            "A smooth surface reflects light.")}
        self.assertNotIn("PERFORMANCE", tags)

    def test_serum_candidates_include_facs_and_gaze(self):
        profile = build_awareness_profile(SERUM_INTENT)
        candidates = {t["tag"] for t in profile.candidate_expertise_tags}
        self.assertTrue({"FACS", "GAZE_ATTENTION", "CAPTURE_REALISM",
                         "PRODUCT_IDENTITY", "HAND_OBJECT_CONTACT",
                         "OBJECT_STATE_TRANSITION", "MATERIAL_RESPONSE"}
                        <= candidates, f"candidates: {candidates}")

    def test_product_only_candidates_exclude_facs(self):
        profile = build_awareness_profile(PRODUCT_ONLY_INTENT)
        candidates = {t["tag"] for t in profile.candidate_expertise_tags}
        self.assertNotIn("FACS", candidates)
        self.assertNotIn("LIVING_PERFORMANCE", candidates)
        self.assertTrue({"PRODUCT_IDENTITY", "VISIBILITY_PERSISTENCE"}
                        <= candidates)

    def test_desert_no_workflow_tags_yields_uncertainty(self):
        profile = build_awareness_profile("A calm empty frame.")
        self.assertFalse(profile.active_workflow_tags)
        self.assertTrue(any(u["kind"] == "AWARENESS_FAILURE_CANDIDATE"
                            for u in profile.uncertainties))

    def test_desert_activates_environment_and_camera_but_not_performance(self):
        tags = {t.tag for t in detect_workflow_tags(DESERT_INTENT)}
        self.assertIn("ENVIRONMENT", tags)
        self.assertIn("CAMERA_CENTRIC", tags)
        self.assertNotIn("PERFORMANCE", tags)
        self.assertNotIn("OBJECT_MANIPULATION", tags)
        self.assertNotIn("VEHICLE", tags)

    def test_universal_considerations_always_present(self):
        profile = build_awareness_profile(DESERT_INTENT)
        ids = {u["consideration_id"] for u in profile.universal_considerations}
        self.assertEqual(ids, {u["consideration_id"]
                               for u in UNIVERSAL_CONSIDERATIONS})
        self.assertTrue(ids)

    def test_tag_provenance_fields(self):
        profile = build_awareness_profile(SERUM_INTENT)
        all_expertise = {t for tags in WORKFLOW_TO_EXPERTISE.values()
                         for t in tags}
        for tag in profile.active_workflow_tags:
            self.assertEqual(tag["tag_level"], 1)
            self.assertEqual(tag["source"], "INTENT_ACTIVATED")
            self.assertTrue(tag["evidence_tokens"])
        for tag in profile.candidate_expertise_tags:
            self.assertEqual(tag["tag_level"], 2)
            self.assertEqual(tag["source"], "WORKFLOW_DERIVED")
            self.assertTrue(tag["corpus_doc_ids"])
            self.assertIn(tag["tag"], EXPERTISE_TAGS)
            self.assertIn(tag["tag"], all_expertise)

    def test_intent_signals_detected(self):
        signals = detect_intent_signals(SERUM_INTENT)
        self.assertTrue(signals["interactions"])
        self.assertTrue(signals["state_changes"])
        self.assertTrue(signals["performance"])
        self.assertTrue(signals["perception"])
        self.assertTrue(signals["environment_material"])

    def test_predicted_failure_families_from_signals(self):
        profile = build_awareness_profile(SERUM_INTENT)
        self.assertIn("FF-CONTACT", profile.predicted_failure_families)
        profile2 = build_awareness_profile(
            FIGHT_INTENT, activation={"packet_id": "x",
                                      "candidate_failure_families": ["FF-CONTACT"]})
        self.assertIn("FF-CONTACT", profile2.predicted_failure_families)

    def test_determinism_profile_hash_stable(self):
        a = build_awareness_profile(SERUM_INTENT)
        b = build_awareness_profile(SERUM_INTENT)
        self.assertEqual(a.profile_hash, b.profile_hash)
        self.assertEqual(a.to_dict(), b.to_dict())


if __name__ == "__main__":
    unittest.main()

    def test_negated_performance_token_not_a_signal(self):
        signals = detect_intent_signals(
            "A drone camera orbits a coastal cliff with no performer "
            "visible.")
        self.assertEqual(signals["performance"], [])
        signals2 = detect_intent_signals(
            "A performer reacts to the camera.")
        self.assertTrue(signals2["performance"])
