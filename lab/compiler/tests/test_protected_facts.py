"""Contact and prop facts in labelled direction come from validated state (plan slice 1).

Three different claims, each tested on its own: what is refused (a structural use the state contradicts),
what is only disclosed (authored words Python cannot read), and what still builds unchanged (the champion).
"""
from __future__ import annotations

import json
import unittest

from lab.compiler.tests.test_labelled_skeleton import FIXTURES, build, champion


def beat(scene, beat_id):
    return next(b for b in scene["beats"] if b["id"] == beat_id)


def audit_of(artifacts):
    return json.loads(artifacts["capability_report.json"])["projection_audit"]


class ProtectedFactTests(unittest.TestCase):
    def test_the_champion_builds_unchanged_and_its_prop_changes_are_disclosed(self):
        artifacts = build(champion())
        self.assertEqual(artifacts["prompt.txt"], (FIXTURES / "corridor_champion.txt").read_bytes())
        audit = audit_of(artifacts)
        self.assertEqual(audit["retired_mentions"], [])
        changes = audit["prop_changes"]
        self.assertIn(dict(beat="b04", object="rail", change="state", printed="bound"), changes)
        self.assertIn(dict(beat="b05", object="rail", change="state", printed="bound"), changes)
        # the wall rail's gap is printed only as authored words: disclosed, not checked
        self.assertIn(dict(beat="b05", object="wall_rail", change="state", printed="not_bound"), changes)
        self.assertIn(dict(beat="b07", object="rail", change="retired", printed="not_applicable"), changes)
        self.assertIn(dict(beat="b07", object="rail_stub", change="new", printed="bound"), changes)
        # the stub drops at beat 9, where the champion has no PROP row
        self.assertIn(dict(beat="b09", object="rail_stub", change="state", printed="not_bound"), changes)

    def test_a_rail_restored_through_another_beats_state_is_refused(self):
        scene = champion()       # beat 8 printing the rail as it was at beat 6, after it broke at beat 7
        beat(scene, "b08").setdefault("direction", {})["PROP"] = [dict(ref="ledger.b06.rail", form="lodged")]
        with self.assertRaisesRegex(ValueError, "LEDGER_BEAT_MISMATCH: beats.b08 prints ledger.b06.rail"):
            build(scene)

    def test_a_rail_restored_in_authored_words_is_disclosed_not_refused(self):
        scene = champion()
        beat(scene, "b07")["direction"]["PROP"].append(dict(text="; the intact whole rail is back in JUN's hands"))
        artifacts = build(scene)
        self.assertIn(b"the intact whole rail is back in JUN's hands", artifacts["prompt.txt"])
        audit = audit_of(artifacts)
        self.assertEqual(audit["retired_mentions"],
                         [dict(ref="beats.b07.direction.PROP", object="rail", retired_at="b07", level="advisory")])
        self.assertIn(dict(ref="beats.b07.direction.PROP", kind="partly_bound"), audit["fields"])

    def test_naming_a_live_piece_or_fixture_is_not_a_retired_mention(self):
        scene = champion()
        beat(scene, "b07")["direction"]["PROP"].append(
            dict(text="; half the rail stays in the door; the gap in the wall rail stays empty"))
        artifacts = build(scene)
        self.assertIn(b"the gap in the wall rail stays empty", artifacts["prompt.txt"])
        self.assertEqual(audit_of(artifacts)["retired_mentions"], [])

    def test_a_contact_timing_claim_in_authored_words_is_reported_as_unverified(self):
        # This layout has no typed clock for a reaction; the claim builds and its row is reported as authored.
        scene = champion()
        beat(scene, "b03")["direction"]["DO"].append(dict(text=" JUN slides before MARA's heel touches his guard."))
        artifacts = build(scene)
        self.assertIn(b"JUN slides before MARA's heel touches his guard.", artifacts["prompt.txt"])
        self.assertIn(dict(ref="beats.b03.direction.DO", kind="partly_bound"), audit_of(artifacts)["fields"])

    def test_a_contact_row_prints_its_own_contacts_part_and_surface_from_the_contact(self):
        scene = champion()
        beat(scene, "b03")["direction"]["CONTACT"][1] = dict(text="heel")      # same words, no longer bound
        with self.assertRaisesRegex(ValueError, "CONTACT_BINDING: beats.b03 CONTACT does not print contact_b03.body_part"):
            build(scene)
        scene = champion()
        beat(scene, "b03")["direction"]["CONTACT"][1] = dict(ref="interactions.contact_b10.body_part", form="plain")
        with self.assertRaisesRegex(ValueError, "CONTACT_BINDING: beats.b03 CONTACT prints contact_b10, a contact of another beat"):
            build(scene)

    def test_a_holder_form_needs_a_holder_and_a_ledger_state(self):
        scene = champion()       # the half left in the door has no holder
        beat(scene, "b07")["direction"]["PROP"][0] = dict(ref="ledger.b07.rail_half_door", form="held")
        with self.assertRaisesRegex(ValueError, "FORM_PRECONDITION: ledger.b07.rail_half_door as held needs a holder"):
            build(scene)
        scene = champion()
        beat(scene, "b03")["direction"]["DO"][0] = dict(ref="entities.mara.name", form="held")
        with self.assertRaisesRegex(ValueError, "FORM_PRECONDITION: entities.mara.name as held needs a ledger state"):
            build(scene)


if __name__ == "__main__":
    unittest.main()
