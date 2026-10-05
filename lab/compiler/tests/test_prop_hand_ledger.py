from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from lab.application.service import REQUEST_SCHEMA, invoke
from lab.compiler.build import compile_build, make_build_request
from lab.compiler.decisions import scene_from_decisions, validate_decisions
from lab.compiler.tests.test_build import ready_score
from lab.second_brain.src.directing_session import load_pass_registry
from lab.second_brain.src.validate import REPO_ROOT
from lab.second_brain.tests.test_directing_session import fixture_root


def choice(path, item, values, *, layer="scene_action", sublayer=None, inputs=()):
    return dict(decision_id=f"d_{layer}_{item}_{sublayer or path}", layer=layer,
                sublayer=sublayer or path, target=dict(path=path, item_id=item),
                values=values, inputs=list(inputs), relative_anchor=None,
                justification="Authored continuity for this scene.",
                source_status="creative_application", evidence_uses=[], lock=False,
                revision_of=None)


def rail_choices():
    def state(label, location, holder=None, hands=()):
        return dict(state=label, location=location, held_by=holder, hands=list(hands))
    ds = [choice("scenes", "scene", dict(duration_s=15, location="Hotel corridor"), sublayer="scene")]
    for item, name, kind in (("jun", "Jun", "person"), ("mara", "Mara", "person"),
                             ("rail", "Handrail", "object"),
                             ("long", "Long rail half", "object"),
                             ("stub", "Short rail stub", "object")):
        values = dict(name=name, kind=kind)
        if item == "rail":
            values["prop_state"] = state("whole", "between Jun's hands", "jun", ("left", "right"))
        ds.append(choice("entities", item, values))
    ds.extend(choice("beats", f"beat_{i}", dict(order=i, min_s=5)) for i in (1, 2, 3))
    ds.extend([
        choice("actions", "aim", dict(actor="jun", beat="beat_1", order=1,
            verb="levels the rail", needs=[dict(object="rail", state="whole", hands=["left", "right"])])),
        choice("actions", "break", dict(actor="mara", beat="beat_2", order=2,
            verb="chops the rail into two pieces", needs=[dict(object="rail", state="whole")],
            changes=[dict(object="rail", state="broken", pieces=[
                dict(object="long", **state("broken_piece", "stuck in the door")),
                dict(object="stub", **state("broken_piece", "Jun's right hand", "jun", ("right",)))])])),
        choice("actions", "drop", dict(actor="jun", beat="beat_3", order=3,
            verb="drops the stub", needs=[dict(object="stub", hands=["right"])],
            changes=[dict(object="stub", held_by=None, hands=[], location="on the carpet")])),
        choice("actions", "guard", dict(actor="jun", beat="beat_3", order=4,
            verb="raises both empty hands", needs=[dict(hands=["left", "right"])])),
    ])
    return ds


class PropHandLedgerTests(unittest.TestCase):
    def setUp(self):
        self.ds = rail_choices()
        self.spec = load_pass_registry(REPO_ROOT)["passes"][0]
        self.packet = {"constraints": {"requested_duration_s": 15}, "steering": "Direct."}

    def codes(self):
        return [e["code"] for e in validate_decisions(self.ds, self.spec, self.packet)]

    def action(self, item):
        return next(d["values"] for d in self.ds if d["target"]["item_id"] == item)

    def test_valid_break_drop_and_empty_hand_guard(self):
        before = copy.deepcopy(self.ds)
        self.assertEqual(self.codes(), [])
        self.assertEqual(self.ds, before)

    def test_retired_whole_prop_cannot_be_used_again(self):
        self.action("guard")["needs"] = [dict(object="rail", state="whole")]
        self.assertIn("PROP_STATE_CONFLICT", self.codes())

    def test_two_empty_hands_require_dropping_the_stub(self):
        self.action("drop").pop("changes")
        self.assertIn("HAND_OCCUPIED", self.codes())

    def test_explicit_grasp_cannot_overwrite_an_occupied_hand(self):
        self.action("guard")["changes"] = [dict(object="long", held_by="jun", hands=["right"], location="Jun's right hand")]
        self.action("drop").pop("changes")
        self.action("guard")["needs"] = []
        self.assertIn("HAND_OCCUPIED", self.codes())

    def test_break_requires_new_declared_piece_identities(self):
        self.action("break")["changes"][0]["pieces"][0]["object"] = "rail"
        self.assertIn("PIECE_IDENTITY", self.codes())

    def test_break_without_pieces_is_rejected(self):
        self.action("break")["changes"][0].pop("pieces")
        self.assertIn("PIECE_IDENTITY", self.codes())

    def test_fragment_cannot_lose_its_location(self):
        self.action("break")["changes"][0]["pieces"][0]["location"] = ""
        self.assertIn("PROP_VANISHED", self.codes())

    def test_prop_holder_must_be_a_declared_entity(self):
        self.action("drop")["changes"][0].update(held_by="unknown", hands=["left"])
        self.assertIn("unknown_reference", self.codes())

    def test_malformed_action_actor_is_a_typed_rejection(self):
        self.action("guard")["actor"] = {}
        self.assertIn("unknown_reference", self.codes())

    def test_actions_on_one_beat_need_an_explicit_unambiguous_order(self):
        self.action("guard")["order"] = self.action("drop")["order"]
        self.assertIn("PROP_SEQUENCE_UNRESOLVED", self.codes())

    def test_build_rejects_invalid_state_even_without_a_directing_session(self):
        self.action("guard")["needs"] = [dict(object="rail", state="whole")]
        scene = scene_from_decisions(self.ds)
        score = ready_score("A fight in a corridor", overlays=[dict(overlay_id="overlay_props",
            scope="scene_override", priority=0, values=scene, locks=[], source_refs=["authored://prop-test"])])
        request = make_build_request(score, project_id="prop-test", model="seedance-2.0", duration_seconds=15)
        with self.assertRaisesRegex(ValueError, "PROP_STATE_CONFLICT"):
            compile_build(request)

    def test_existing_entity_id_collection_still_builds_without_ledger_declarations(self):
        score = ready_score("A product demonstration", overlays=[dict(overlay_id="overlay_legacy_entity",
            scope="scene_override", priority=0, values=dict(entities=[dict(entity_id="bottle", name="Bottle")]),
            locks=[], source_refs=["authored://existing-identity-form"])])
        self.assertIn("prompt.txt", compile_build(make_build_request(score, project_id="identity-form")))

    def bottle(self, put_phone_down):
        def state(label, place, holder=None, hands=()):
            return dict(state=label, location=place, held_by=holder, hands=list(hands))
        ds = [choice("scenes", "scene", dict(duration_s=15, location="Kitchen counter"), sublayer="scene")]
        for obj, value in (
            ("phone", state("intact", "creator's left hand", "creator", ["left"])),
            ("bottle", state("closed", "creator's right hand", "creator", ["right"])),
            ("cap", state("attached", "on the bottle"))):
            ds.append(choice("entities", obj, dict(name=obj.title(), kind="object", prop_state=value)))
        ds.append(choice("entities", "creator", dict(name="Creator", kind="person")))
        ds.extend(choice("beats", f"beat_{i}", dict(order=i, min_s=5)) for i in (1, 2, 3))
        ds.append(choice("actions", "set_phone", dict(actor="creator", beat="beat_1", order=1,
            verb="sets down the phone" if put_phone_down else "keeps holding the phone",
            changes=[dict(object="phone", held_by=None, hands=[], location="on the counter")] if put_phone_down else [])))
        ds.append(choice("actions", "open", dict(actor="creator", beat="beat_2", order=2,
            verb="transfers the bottle to the left hand, grips and twists the cap with the right, then lifts it clear",
            needs=[dict(object="bottle", state="closed", hands=["right"]), dict(hands=["left"])],
            changes=[dict(object="bottle", state="open", held_by="creator", hands=["left"], location="creator's left hand"),
                     dict(object="cap", state="detached", held_by="creator", hands=["right"], location="above the open bottle")])))
        ds.append(choice("actions", "drink", dict(actor="creator", beat="beat_3", order=3,
            verb="raises the open bottle to drink", needs=[dict(object="bottle", state="open", hands=["left"])])))
        return ds

    def test_ugc_phone_hand_must_be_released_before_two_hand_opening(self):
        self.ds = self.bottle(False)
        self.assertIn("HAND_OCCUPIED", self.codes())
        self.ds = self.bottle(True)
        self.assertEqual(self.codes(), [])

    def test_drinking_requires_the_declared_open_result(self):
        self.ds = self.bottle(True)
        self.action("open")["changes"][0]["state"] = "closed"
        self.assertIn("PROP_STATE_CONFLICT", self.codes())


class PropHandPublicTests(unittest.TestCase):
    def setUp(self):
        # This follows the documented repository-local work workspace, without
        # modifying the existing tests or inventing Git provenance for a data root.
        self.temp = tempfile.TemporaryDirectory(dir=REPO_ROOT / "work")
        self.addCleanup(self.temp.cleanup)
        self.root = fixture_root(Path(self.temp.name))
        self.sid = self.call("direct.start", dict(text="A corridor fight, 15 seconds", mode="complete",
                                                model="seedance-2.0"))["session_id"]

    def call(self, op, args):
        response = invoke(dict(schema=REQUEST_SCHEMA, operation="cpcs." + op, arguments=args),
                          role="operator", root=self.root)
        self.assertEqual(response["status"], "success", response.get("error"))
        return response["result"]

    def submit(self, pass_id, ds):
        packet = self.call("direct.packet.read", dict(session_id=self.sid, pass_id=pass_id))
        selected = {d["sublayer"] for d in ds}
        proposal = dict(schema="cpcs.directing_proposal/1.0", pass_id=pass_id, decisions=ds,
            not_applicable=[dict(sublayer_id=s["sublayer_id"], reason="No additional choice for this authored case.")
                            for s in packet["sublayers"] if not s["required"] and s["sublayer_id"] not in selected])
        return self.call("direct.proposal.submit", dict(session_id=self.sid, pass_id=pass_id,
                        packet_hash=packet["packet_hash"], proposal=proposal))

    def test_invalid_proposal_leaves_accepted_state_unchanged(self):
        before = self.call("direct.state.read", dict(session_id=self.sid))
        ds = rail_choices()
        ds[-1]["values"]["needs"] = [dict(object="rail", state="whole")]
        result = self.submit("scene_action", ds)
        self.assertEqual(result["disposition"], "rejected")
        self.assertIn("PROP_STATE_CONFLICT", [r["code"] for r in result["rejections"]])
        self.assertEqual(before, self.call("direct.state.read", dict(session_id=self.sid)))

    def test_accepted_state_reaches_prose_and_json_with_carried_fragment_locations(self):
        ds = rail_choices()
        self.assertEqual(self.submit("scene_action", ds)["disposition"], "accepted")
        for spec in load_pass_registry(self.root)["passes"][1:]:
            packet = self.call("direct.packet.read", dict(session_id=self.sid, pass_id=spec["pass_id"]))
            choices = []
            for slot in spec["sublayers"]:
                if not slot["required"]:
                    continue
                values = {f: "Observe the continuing corridor action." for f in slot["fields"]}
                if slot["sublayer_id"] == "kinematics":  # always on (owner SD-18): a validated plan
                    values = {"kinematic_plan": json.loads((REPO_ROOT / "lab/compiler/tests/fixtures/corridor_rail_plan.json").read_text())}
                values.update({k: v for k, v in dict(order=1, beat="beat_1", end_beat="beat_3",
                              shows_initiation=True).items() if k in values})
                item = "shot" if slot["target_path"] == "shots" else "scene"
                choices.append(choice(slot["target_path"], item, values, layer=spec["pass_id"],
                                      sublayer=slot["sublayer_id"], inputs=[packet["upstream"][0]["decision_id"]]))
            result = self.submit(spec["pass_id"], choices)
            self.assertEqual(result["disposition"], "accepted", result)
        settings = dict(project_id="prop-ledger", duration_seconds=15, prompt_format="prose")
        result = self.call("direct.finish", dict(session_id=self.sid, build_settings=settings))
        self.assertEqual(result["provider_fit"]["status"], "supported")
        prompt = result["build"]["artifacts"]["prompt.txt"]["content"]
        self.assertIn("PROP", prompt)
        last = prompt.split("Beat 3:")[1]
        self.assertIn("Long rail half", last)
        self.assertIn("stuck in the door", last)
        self.assertIn("Short rail stub", last)
        self.assertIn("on the carpet", last)
        self.assertNotIn("whole", last)
        again = self.call("direct.finish", dict(session_id=self.sid, build_settings=settings))
        self.assertEqual(result, again)
        settings["prompt_format"] = "json"
        structured = self.call("direct.finish", dict(session_id=self.sid, build_settings=settings))
        self.assertEqual(result["score"], structured["score"])
        self.assertIn('"pieces"', structured["build"]["artifacts"]["prompt.txt"]["content"])


if __name__ == "__main__":
    unittest.main()
