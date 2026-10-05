from __future__ import annotations
import copy
import json
import tempfile
import unittest
from pathlib import Path
from lab.application.service import REQUEST_SCHEMA, invoke
from lab.compiler.build import compile_build, make_build_request
from lab.second_brain.tests.test_directing_session import fixture, fixture_root
from lab.second_brain.src.validate import REPO_ROOT


def decision(name, layer, sublayer, path, item, values, inputs=(), anchor=None):
    return dict(decision_id=name, layer=layer, sublayer=sublayer,
                target=dict(path=path, item_id=item), values=values, inputs=list(inputs),
                relative_anchor=anchor, justification='Keep the selected action readable.',
                source_status='creative_application', evidence_uses=[], lock=False, revision_of=None)


def stacks():
    performance = {
        'body': {'body': 'The planted rear foot starts the shove; the hips and shoulder carry it into the palms.'},
        'effort_weight': {'effort_weight': 'Weight travels through the front foot into both palms.'},
        'effort_time': {'effort_time': 'The shove releases after the preparatory elbow bend.'},
        'effort_space': {'effort_space': 'Both palms travel directly toward the chest.'},
        'effort_flow': {'effort_flow': 'The extension stops at contact and returns to guard.'},
        'shape': {'shape': 'Rome narrows his silhouette before opening his arms toward Dex.'},
        'space': {'space': 'The hands stay within the reach established chest to chest.'},
        'bartenieff': {'connectivity': 'Support foot to hips, shoulder, elbow, then palms.'},
        'face': {'face': 'Rome keeps his eyes on Dex; the jaw tightens at release.'},
        'affect': {'affect_visible': 'His still approach becomes a held stare, then a forceful release.'},
    }
    camera = {
        'framing': {'framing': 'medium-wide, both fighters visible from feet to head'},
        'angle': {'angle': 'eye-level three-quarter view'},
        'position': {'position': 'on the table side of the established action axis'},
        'movement': {'movement': 'locked off'},
        'movement_quality': {'movement_quality': 'steady throughout the exchange'},
        'relation': {'relation': 'observes both fighters without following the punch'},
        'lens': {'lens': 'wide field of view with separated silhouettes'},
        'focus': {'focus': 'both fighters and the bars remain legible'},
        'composition': {'composition': 'clear space between the palms and the chest'},
        'time': {'time': 'the same playback pace as the established approach'},
        'blur': {'blur': 'preserve readable hands during the cross'},
        'connection': {'connection': 'one continuous shot ending with both fighters apart'},
    }
    result = {
        'performance': [decision('p_'+k, 'performance', k, 'actions', 'act_2', v, ['d_action_2']) for k,v in performance.items()],
        'staging': [decision('stage', 'staging', 'blocking', 'scenes', 'scene_1',
                    {'blocking': 'Rome stays left, Dex stays right; the bars remain behind Dex.'}, ['d_entity_rome','d_entity_dex']),
                    # Kinematics is always on (owner SD-18): the staging stack carries a validated plan.
                    decision('stage_kinematics', 'staging', 'kinematics', 'scenes', 'scene_1',
                             {'kinematic_plan': json.loads((REPO_ROOT / 'lab/compiler/tests/fixtures/jail_fight_plan.json').read_text())},
                             ['d_entity_rome', 'd_entity_dex', 'd_scene_duration'])],
        'camera': [decision('cam_'+k, 'camera', k, 'shots', 'shot_1', v, ['d_action_2','p_body']) for k,v in camera.items()],
        'light_color': [decision('light', 'light_color', 'light', 'scenes', 'scene_1', {'lighting': 'Overhead jail fluorescents keep faces and contact readable.'}, ['cam_framing'])],
        'style': [decision('style', 'style', 'visual_style', 'scenes', 'scene_1', {'visual_style': 'Restrained live-action realism.'}, ['light'])],
        'audio': [decision('sound', 'audio', 'sound', 'scenes', 'scene_1', {'sound': 'The bars rattle on impact; the buzzer triggers separation; nobody speaks.'}, ['d_interaction_2','d_action_6'])],
        'synthesis': [decision('end', 'synthesis', 'end_state', 'scenes', 'scene_1', {'end_state': 'Both fighters upright, apart, looking at each other.'}, ['sound','cam_connection'])],
    }
    result['camera'][0]['values'].update(order=1, beat='beat_1', end_beat='beat_5', shows_initiation=True)
    return result


class DirectingPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = fixture_root(Path(self.temp.name)); self.data=fixture()
        self.sid=self.result('direct.start',dict(text=self.data['ask'],mode='complete',model='seedance-2.0'))['session_id']

    def call(self, op, args):
        return invoke(dict(schema=REQUEST_SCHEMA,operation='cpcs.'+op,arguments=args),role='operator',root=self.root)

    def result(self, op, args):
        r=self.call(op,args); self.assertEqual(r['status'],'success',r.get('error'));return r['result']

    def packet(self, p):
        return self.result('direct.packet.read',dict(session_id=self.sid,pass_id=p))

    def submit(self,p,ds,packet=None):
        packet=packet or self.packet(p)
        slots={d['sublayer'] for d in ds}
        proposal=dict(schema='cpcs.directing_proposal/1.0',pass_id=p,decisions=copy.deepcopy(ds),
            not_applicable=[dict(sublayer_id=s['sublayer_id'],reason='Not needed for this scene.') for s in packet['sublayers'] if not s['required'] and s['sublayer_id'] not in slots])
        return self.result('direct.proposal.submit',dict(session_id=self.sid,pass_id=p,packet_hash=packet['packet_hash'],proposal=proposal))

    def scene(self):
        r=self.submit('scene_action',self.data['proposal']['decisions']);self.assertEqual(r['disposition'],'accepted',r)

    def complete(self):
        self.scene()
        for p,ds in stacks().items():
            r=self.submit(p,ds);self.assertEqual(r['disposition'],'accepted',r)

    def rejected(self,r,code):
        self.assertEqual(r['disposition'],'rejected',r);self.assertIn(code,[e['code'] for e in r['rejections']])

    def test_complete_mode_has_connected_creative_passes(self):
        state=self.result('direct.state.read',dict(session_id=self.sid))
        self.assertEqual([p['pass_id'] for p in state['passes']],['scene_action','performance','staging','camera','light_color','style','audio','synthesis'])
        self.scene(); packet=self.packet('performance')
        self.assertIn('d_action_2',[d['decision_id'] for d in packet['upstream']])
        self.assertIn('d_scene_duration',packet['locks'])
        self.assertEqual(packet['constraints']['requested_duration_s'],15)
        self.assertIn('invent',packet['steering'].lower())

    def test_pass_cannot_run_before_its_inputs(self):
        self.rejected(self.submit('camera',stacks()['camera']),'upstream_not_accepted')

    def test_camera_stack_is_atomic(self):
        self.scene();self.submit('performance',stacks()['performance']);self.submit('staging',stacks()['staging'])
        self.rejected(self.submit('camera',stacks()['camera'][:-1]),'missing_required_sublayer')
        self.assertFalse(any(d['decision_id'].startswith('cam_') for d in self.result('direct.state.read',dict(session_id=self.sid))['decisions']))

    def test_sublayer_cannot_steal_another_sublayers_fields(self):
        self.scene(); changed=stacks()['performance'];changed[0]['values']={'effort_weight':'invented override'}
        self.rejected(self.submit('performance',changed),'field_not_allowed')

    def test_camera_needs_action_based_readability_or_explicit_reason(self):
        self.scene();self.submit('performance',stacks()['performance']);self.submit('staging',stacks()['staging'])
        ds=stacks()['camera'];ds[0]['values']['shows_initiation']=False
        self.rejected(self.submit('camera',ds),'camera_hides_initiation')
        ds[0]['values']['occlusion_reason']='Withhold the first push for a deliberate reveal.'
        self.assertEqual(self.submit('camera',ds)['disposition'],'accepted')

    def test_contacts_need_reaction_and_settle(self):
        ds=copy.deepcopy(self.data['proposal']['decisions']);ds[-1]['values'].pop('settle')
        self.rejected(self.submit('scene_action',ds),'contact_missing_response')

    def test_relative_anchor_quality_must_be_established(self):
        ds=copy.deepcopy(self.data['proposal']['decisions']);ds[11]['relative_anchor']['baseline']['quality']='brightness'
        self.rejected(self.submit('scene_action',ds),'anchor_quality_missing')

    def test_research_packet_has_exact_source_dispositions(self):
        self.scene();p=self.packet('performance')
        self.assertTrue(p['research']['concepts'])
        self.assertTrue(all('source_resolution' in c for c in p['research']['concepts']))
        self.assertTrue(all(c['layer'] in ['whole-body movement','Laban Shape','face','affect','performance','breath and performance'] for c in p['research']['concepts']))

    def test_research_cannot_be_claimed_from_unresolved_sources(self):
        self.scene();packet=self.packet('performance');ds=stacks()['performance']
        ds[0]['source_status']='sourced_research';ds[0]['evidence_uses']=[dict(kind='concept',id='c_absent',content_hash='sha256:'+'0'*64)]
        self.rejected(self.submit('performance',ds,packet),'evidence_outside_packet')

    def test_revision_preserves_history_and_invalidates_dependents(self):
        self.complete(); old=self.packet('camera'); ds=stacks()['performance']
        ds[0]['decision_id']='p_body_revised';ds[0]['revision_of']='p_body';ds[0]['values']['body']='The planted support foot leads into both shoulders, then the palms.'
        r=self.submit('performance',ds);self.assertEqual(r['disposition'],'accepted',r)
        s=self.result('direct.state.read',dict(session_id=self.sid))
        self.assertIn('p_body',[d['decision_id'] for d in s['decisions']]);self.assertIn('p_body_revised',[d['decision_id'] for d in s['decisions']])
        self.assertEqual(next(p for p in s['passes'] if p['pass_id']=='camera')['status'],'needs_recheck')
        self.rejected(self.submit('camera',stacks()['camera'],old),'stale_packet')
        self.assertEqual(self.call('direct.finish',dict(session_id=self.sid))['status'],'error')

    def test_locked_user_duration_cannot_be_revised(self):
        self.scene();ds=copy.deepcopy(self.data['proposal']['decisions']);ds[0]['decision_id']='changed_duration';ds[0]['revision_of']='d_scene_duration';ds[0]['values']['duration_s']=8
        self.rejected(self.submit('scene_action',ds),'locked_decision')

    def test_finish_emits_replayable_seedance_prompt_and_reference_still(self):
        self.complete();args=dict(session_id=self.sid,build_settings=dict(project_id='cpcs-local-export',duration_seconds=15,prompt_format='prose'))
        first=self.result('direct.finish',args);self.assertEqual(first,self.result('direct.finish',args))
        self.assertEqual(first['score']['project']['duration_seconds'],15)
        self.assertEqual(first['provider_fit']['status'],'supported')
        build=first['build'];self.assertIsNotNone(build)
        prompt=build['artifacts']['prompt.txt']['content'];self.assertIn('Rome',prompt);self.assertIn('rear foot',prompt);self.assertIn('three-quarter',prompt)
        self.assertIn('Shot 1',prompt);self.assertIn('much faster than',prompt)
        self.assertNotIn('p_body',prompt)
        carrier=json.loads(build['artifacts']['provider_request.json']['content'])
        self.assertEqual(carrier['method'],'MANUAL');self.assertEqual(carrier['settings']['duration_seconds'],15)
        self.assertIn('county jail',build['artifacts']['reference_still_prompt.txt']['content'])
        self.assertFalse(json.loads(build['artifacts']['capability_report.json']['content'])['prompt_budget_chars'])

    def test_structured_projection_uses_the_same_score(self):
        self.complete();a=dict(session_id=self.sid,build_settings=dict(project_id='cpcs-local-export',duration_seconds=15,prompt_format='json'))
        r=self.result('direct.finish',a);value=json.loads(r['build']['artifacts']['prompt.txt']['content'])
        self.assertEqual(value['score_id'],r['score']['score_id']);self.assertEqual(value['actions'],r['score']['actions'])

    def test_model_mismatch_does_not_shorten_the_score(self):
        self.complete();r=self.result('direct.finish',dict(session_id=self.sid,model='veo-3.1-generate-001',build_settings=dict(project_id='cpcs-local-export',duration_seconds=15)))
        self.assertEqual(r['provider_fit']['status'],'unsupported');self.assertEqual(r['score']['project']['duration_seconds'],15);self.assertIsNone(r['build'])

    def test_build_cannot_override_scene_duration(self):
        self.complete();r=self.call('direct.finish',dict(session_id=self.sid,build_settings=dict(project_id='cpcs-local-export',duration_seconds=8)))
        self.assertEqual(r['status'],'error');self.assertIn('duration',r['error']['message'])

    def test_variant_keeps_user_constraints_and_changes_session_identity(self):
        other=self.result('direct.start',dict(text=self.data['ask'],mode='complete',model='seedance-2.0',variant='more restrained'))
        self.assertNotEqual(other['session_id'],self.sid)
        p=self.result('direct.packet.read',dict(session_id=other['session_id'],pass_id='scene_action'))
        self.assertEqual(p['constraints']['requested_duration_s'],15);self.assertEqual(p['preferences']['variant'],'more restrained')

if __name__=='__main__':unittest.main()
