from __future__ import annotations
import copy, json, tempfile, unittest
from pathlib import Path
from lab.application.service import REQUEST_SCHEMA, invoke
from lab.compiler.tests.test_build import ready_score
from lab.compiler.build import compile_build, make_build_request
from lab.second_brain.tests.test_directing_session import fixture_root
from lab.second_brain.src.validate import REPO_ROOT

FIXTURES=Path(__file__).parent/'fixtures'
def champion(): return json.loads((FIXTURES/'corridor_scene.json').read_text())
def build(scene,layout='labelled_skeleton_v1',format='prose'):
    score=ready_score('A corridor fight, 15 seconds',overlays=[dict(overlay_id='overlay_skeleton',scope='scene_override',priority=0,values=scene,locks=[],source_refs=['authored://accepted-scene'])])
    return compile_build(make_build_request(score,project_id='skeleton-test',model='seedance-2.0',duration_seconds=15,prompt_format=format,prompt_layout=layout))
class LabelledSkeletonTests(unittest.TestCase):
    def test_champion_bytes_exact(self):
        self.assertEqual(build(champion())['prompt.txt'],(FIXTURES/'corridor_champion.txt').read_bytes())
    def test_recipe_rejects_text_tokens(self):
        scene=champion();scene['scenes'][0]['skeleton_recipe']['rows'][0]['text']='a hidden fallback'
        with self.assertRaisesRegex(ValueError,'RECIPE_TEXT|recipe'):build(scene)
    def test_beat_lengths_mutate_and_are_audited_as_carrier_choice(self):
        scene=champion();scene['beats'][0]['duration_s']=2;scene['beats'][1]['duration_s']=1.5
        scene['beats'][0]['min_s']=2
        artifacts=build(scene);self.assertIn(b'BEAT 1 (2s)',artifacts['prompt.txt'])
        audit=json.loads(artifacts['capability_report.json'])['projection_audit']
        self.assertEqual(audit['beat_timing']['kind'],'carrier_choice')
        self.assertFalse(audit['beat_timing']['provider_adherence_claim'])
    def test_invalid_duration_rejected(self):
        scene=champion();scene['beats'][0]['duration_s']=-1
        with self.assertRaisesRegex(ValueError,'DURATION'):build(scene)
    def test_range_mutation_changes_wording(self):
        scene=champion();scene['beats'][0]['range_relations'][0]['amount']=2
        self.assertIn(b'two arm-lengths apart',build(scene)['prompt.txt'])
        scene['beats'][0]['range_relations'][0]['amount']=-1
        with self.assertRaisesRegex(ValueError,'RANGE'):build(scene)
    def test_prop_state_mutation_changes_its_field(self):
        scene=champion();scene['actions'][3]['changes'][0]['state']='secured'
        scene['actions'][4]['needs'][0]['state']='secured'
        self.assertIn(b'rail secured',build(scene)['prompt.txt'])
    def test_retired_rail_reuse_rejected(self):
        scene=champion();scene['actions'][9]['needs']=[dict(object='rail',state='whole')]
        with self.assertRaisesRegex(ValueError,'PROP_STATE_CONFLICT'):build(scene)
    def test_occupied_catch_rejected(self):
        scene=champion();scene['actions'][8]['changes']=[]
        with self.assertRaisesRegex(ValueError,'HAND_OCCUPIED'):build(scene)
    def test_unnamed_piece_rejected(self):
        scene=champion();scene['actions'][6]['changes'][0]['pieces'][0]['object']='missing'
        with self.assertRaisesRegex(ValueError,'PIECE_IDENTITY'):build(scene)
    def test_missing_piece_location_rejected(self):
        scene=champion();scene['actions'][6]['changes'][0]['pieces'][0]['location']=''
        with self.assertRaisesRegex(ValueError,'PROP_VANISHED'):build(scene)
    def test_omission_removes_field_and_records_loss(self):
        scene=champion();del scene['beats'][1]['direction']['FACE']
        scene['scenes'][0]['direction_omissions']=[dict(ref='beats.b02.direction.FACE',decision_id='face_b02',reason='Optional face choice withdrawn.')]
        artifacts=build(scene)
        self.assertNotIn(b'eyes wide, flicking past her',artifacts['prompt.txt'])
        self.assertTrue(any('face_b02' in l['reason'] for l in json.loads(artifacts['loss_report.json'])['losses']))
    def test_prose_and_json_same_scene(self):
        scene=champion();self.assertIn(b'Action',build(scene,layout='default')['prompt.txt'])
        payload=json.loads(build(scene,format='json')['prompt.txt'])
        self.assertEqual(payload['beats'][0]['duration_s'],2.5)
    def test_structure_share_and_authored_hand_disclosed(self):
        artifacts=build(champion());audit=json.loads(artifacts['capability_report.json'])['projection_audit']
        self.assertEqual(sum(audit['byte_counts'].values()),len(artifacts['prompt.txt']))
        self.assertGreater(audit['byte_counts']['typed_bound'],0)
        self.assertGreater(audit['byte_counts']['authored_clause'],0)
        self.assertFalse(audit['authored_bindings'][0]['source_explicit'])
    def test_small_scene_uses_default_recipe(self):
        scene=dict(scenes=[dict(id='small',duration_s=15,location='counter',direction={'GOAL':[dict(text='Open a bottle.')],'END':[dict(text='Cap on counter.') ]})],entities=[dict(id='creator',name='Creator',kind='person')],beats=[dict(id='b1',order=1,min_s=15,duration_s=15,role='SETUP',direction={'DO':[dict(text='Creator twists the cap.') ]})],actions=[dict(id='a1',actor='creator',beat='b1',order=1,verb='twists')],interactions=[],shots=[])
        self.assertEqual(build(scene)['prompt.txt'],b'GOAL      Open a bottle.\n\nBEAT 1 (15s) SETUP\n  DO       Creator twists the cap.\n\nEND       Cap on counter.\n')
    def test_existing_default_callers_unchanged(self):
        scene=champion();score=ready_score('A corridor fight, 15 seconds',overlays=[dict(overlay_id='overlay_default',scope='scene_override',priority=0,values=scene,locks=[],source_refs=['authored://default'])])
        base=make_build_request(score,project_id='default-test',model='seedance-2.0',duration_seconds=15,prompt_format='prose')
        explicit=copy.deepcopy(base);explicit['settings']['prompt_layout']='default'
        self.assertEqual(compile_build(base),compile_build(explicit))
class SkeletonPublicTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=REPO_ROOT/'work');self.addCleanup(self.temp.cleanup)
        self.root=fixture_root(Path(self.temp.name))
    def call(self,op,args):
        response=invoke(dict(schema=REQUEST_SCHEMA,operation='cpcs.'+op,arguments=args),role='operator',root=self.root)
        self.assertEqual(response['status'],'success',response.get('error'));return response['result']
    def test_public_accept_finish_build_and_withdrawal(self):
        sid=self.call('direct.start',dict(text='A corridor fight, 15 seconds',model='seedance-2.0'))['session_id']
        packet=self.call('direct.packet.read',dict(session_id=sid,pass_id='scene_action'))
        decisions=[]
        for path,items in champion().items():
            for item in items:
                values={k:v for k,v in item.items() if k!='id'}
                decisions.append(dict(decision_id='d_'+item['id'],layer='scene_action',sublayer={'scenes':'scene','shots':'shots'}.get(path,path),target=dict(path=path,item_id=item['id']),values=values,inputs=[],relative_anchor=None,justification='Accepted owner-authored scene; protected interpretations §5.',source_status='creative_application',evidence_uses=([dict(kind='owner_source',content_hash='sha256:'+item['wording_source']['sha256'],locator='scenes.corridor.direction.GOAL')] if path=='scenes' else []),lock=False,revision_of=None))
        # Shots are owned by the camera pass, so this legacy one-pass import uses the existing scene collections through its scene/action contract extension.
        result=self.call('direct.proposal.submit',dict(session_id=sid,pass_id='scene_action',packet_hash=packet['packet_hash'],proposal=dict(schema='cpcs.directing_proposal/1.0',pass_id='scene_action',decisions=decisions,not_applicable=[])))
        self.assertEqual(result['disposition'],'accepted')
        result=self.call('direct.finish',dict(session_id=sid,build_settings=dict(project_id='public-champion',prompt_format='prose',prompt_layout='labelled_skeleton_v1')))
        self.assertEqual(result['score']['project']['duration_seconds'],15)
        build_dir=Path(result['build']['output_dir'])
        self.assertEqual((build_dir/'prompt.txt').read_bytes(),(FIXTURES/'corridor_champion.txt').read_bytes())
        self.call('direct.withdraw',dict(session_id=sid,decision_id='d_b02',field='direction.FACE',reason='Optional field withdrawn.'))
        result=self.call('direct.finish',dict(session_id=sid,build_settings=dict(project_id='withdraw-champion',prompt_format='prose',prompt_layout='labelled_skeleton_v1')))
        self.assertNotIn(b'eyes wide, flicking past her',(Path(result['build']['output_dir'])/'prompt.txt').read_bytes())
    def test_small_scene_public_acceptance_without_recipe(self):
        sid=self.call('direct.start',dict(text='A casual phone video: open a bottle, 15 seconds',model='seedance-2.0'))['session_id']
        packet=self.call('direct.packet.read',dict(session_id=sid,pass_id='scene_action'))
        scene=dict(scenes=[dict(id='small',duration_s=15,location='counter',direction={'GOAL':[dict(text='Open a bottle.')],'END':[dict(text='Cap on counter.') ]})],entities=[dict(id='creator',name='Creator',kind='person')],beats=[dict(id='b1',order=1,min_s=15,duration_s=15,role='SETUP',direction={'DO':[dict(text='Creator twists the cap.') ]})],actions=[dict(id='a1',actor='creator',beat='b1',order=1,verb='twists')])
        decisions=[dict(decision_id='d_'+item['id'],layer='scene_action',sublayer='scene' if path=='scenes' else path,target=dict(path=path,item_id=item['id']),values={k:v for k,v in item.items() if k!='id'},inputs=[],relative_anchor=None,justification='Authored example',source_status='creative_application',evidence_uses=[],lock=False,revision_of=None) for path,items in scene.items() for item in items]
        result=self.call('direct.proposal.submit',dict(session_id=sid,pass_id='scene_action',packet_hash=packet['packet_hash'],proposal=dict(schema='cpcs.directing_proposal/1.0',pass_id='scene_action',decisions=decisions,not_applicable=[])))
        self.assertEqual(result['disposition'],'accepted')
        result=self.call('direct.finish',dict(session_id=sid,build_settings=dict(project_id='public-small',prompt_format='prose',prompt_layout='labelled_skeleton_v1')))
        self.assertEqual((Path(result['build']['output_dir'])/'prompt.txt').read_bytes(),b'GOAL      Open a bottle.\n\nBEAT 1 (15s) SETUP\n  DO       Creator twists the cap.\n\nEND       Cap on counter.\n')
