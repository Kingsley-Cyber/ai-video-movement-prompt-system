"""Bound wording and attribution proof, separate from the immutable oracle."""
import copy
import json
import unittest
from lab.compiler.tests.test_labelled_skeleton import champion, build
from lab.compiler.skeleton import project
from lab.compiler.decisions import validate_decisions
from lab.second_brain.src.validate import REPO_ROOT

class BindingContracts(unittest.TestCase):
    def test_wrap_accounting_counts_emitted_bytes(self):
        scene = dict(scenes=[dict(id='small',duration_s=1,direction={'GOAL':[dict(text='One. Two.')]})], entities=[], beats=[dict(id='b',order=1,duration_s=1,role='HOLD')], actions=[], interactions=[], shots=[])
        text,audit,_=project(scene)
        self.assertIn('One.\n          Two.',text)
        self.assertEqual(audit['byte_counts'],dict(typed_bound=7,authored_clause=8,layout=33))
        self.assertEqual(len(text.encode()),48)
    def test_wrap_inside_bound_value_counts_printed_bytes(self):
        scene = dict(scenes=[dict(id='small',duration_s=1,title='One. Two.',direction={'GOAL':[dict(ref='scenes.small.title',form='plain')]})], entities=[], beats=[dict(id='b',order=1,duration_s=1,role='HOLD')], actions=[], interactions=[], shots=[])
        text,audit,_=project(scene)
        self.assertIn('One.\n          Two.',text)
        self.assertEqual(audit['byte_counts'],dict(typed_bound=15,authored_clause=0,layout=33))
        self.assertEqual(len(text.encode()),48)
    def test_layout_node_forbidden_in_scene_data(self):
        scene=champion();scene['beats'][0]['direction']['DO']=[dict(layout='hidden prose')]
        with self.assertRaisesRegex(ValueError,'DIRECTION_BINDING'):build(scene)
    def test_layout_node_forbidden_in_recipe(self):
        scene=champion();scene['scenes'][0]['skeleton_recipe']['rows'][0]['layout']='hidden prose'
        with self.assertRaisesRegex(ValueError,'RECIPE'):build(scene)
    def test_camera_binding_mutation_changes_camera_field(self):
        scene=champion();scene['shots'][0]['framing']='wide two-shot'
        self.assertIn(b'wide two-shot',build(scene)['prompt.txt'])
    def test_appearance_binding_mutation_changes_cast(self):
        scene=champion();scene['entities'][0]['appearance']['hair']='cropped silver hair'
        self.assertIn(b'cropped silver hair',build(scene)['prompt.txt'])
    def test_contact_binding_mutation_changes_contact(self):
        scene=champion();scene['interactions'][0]['surface']='raised forearms'
        self.assertIn(b'raised forearms',build(scene)['prompt.txt'])
    def test_owner_source_hash_bound_to_accepted_wording(self):
        scene=champion()
        decisions=[]
        for path,items in scene.items():
            for item in items:
                decisions.append(dict(decision_id='d_'+item['id'],layer='scene_action',sublayer={'scenes':'scene','shots':'shots'}.get(path,path),target=dict(path=path,item_id=item['id']),values={k:v for k,v in item.items() if k!='id'},inputs=[],relative_anchor=None,justification='Accepted authoring',source_status='creative_application',evidence_uses=[],lock=False,revision_of=None))
        decisions[0]['evidence_uses']=[dict(kind='owner_source',content_hash='sha256:'+scene['scenes'][0]['wording_source']['sha256'],locator='scenes.corridor.direction.GOAL')]
        spec=dict(pass_id='scene_action',reads=[],sublayers=[dict(sublayer_id={'scenes':'scene','shots':'shots'}.get(p,p),target_path=p) for p in scene])
        packet=dict(constraints=dict(requested_duration_s=15))
        self.assertEqual(validate_decisions(decisions,spec,packet,root=REPO_ROOT),[])
        decisions[0]['evidence_uses'][0]['content_hash']='sha256:'+'0'*64
        self.assertIn('owner_source_mismatch',[e['code'] for e in validate_decisions(decisions,spec,packet,root=REPO_ROOT)])

    def test_unspecified_camera_slots_have_dispositions(self):
        artifacts=build(champion())
        audit=json.loads(artifacts['capability_report.json'])['projection_audit']
        rows=audit['camera_dispositions']
        self.assertEqual(len(rows),28)
        self.assertTrue(all(r['disposition']=='source_unspecified' for r in rows))
        self.assertEqual({r['field'] for r in rows},{'lens','focus','angle','movement'})
        for shot in champion()['shots']:
            if shot['id'] in {'s02','s04','s07','s08'}:
                self.assertIsNone(shot['angle']);self.assertIsNone(shot['movement'])

    def test_unspecified_camera_disposition_cannot_hide_value(self):
        scene=champion();scene['shots'][1]['movement']='static'
        with self.assertRaisesRegex(ValueError,'SOURCE_UNSPECIFIED'):build(scene)

    def test_angle_binding_does_not_change_beside_word(self):
        scene=champion();scene['shots'][8]['angle']='front'
        prompt=build(scene)['prompt.txt']
        self.assertIn(b'from beside the windows, both fighters seen from the front',prompt)
        self.assertNotIn(b'befront',prompt)
    def test_final_heading_uses_camera_and_cast_bindings(self):
        scene=champion();scene['shots'][9]['angle']='high three-quarter';scene['entities'][0]['name']='RIN'
        prompt=build(scene)['prompt.txt']
        self.assertIn(b'BEAT 10 (1s) TIGHT HIGH THREE-QUARTER against the window light, RIN on the left',prompt)
