"""Existing public directing operations with opt-in synthetic closed-set menus."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from lab.application.tests import test_directing_pipeline as pipeline
stacks=pipeline.stacks
from lab.second_brain.tests.test_directing_session import fixture_root,fixture
from lab.second_brain.tests.fixed_set_fixture import install
from lab.second_brain.src.fixed_sets import read_catalog
from lab.compiler.build import compile_build,make_build_request

class ClosedDirectingTests(unittest.TestCase):
    call=pipeline.DirectingPipelineTests.call
    result=pipeline.DirectingPipelineTests.result
    packet=pipeline.DirectingPipelineTests.packet
    submit=pipeline.DirectingPipelineTests.submit
    scene=pipeline.DirectingPipelineTests.scene
    rejected=pipeline.DirectingPipelineTests.rejected
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[3]/'work');self.addCleanup(self.temp.cleanup)
        self.root=fixture_root(Path(self.temp.name));install(self.root);self.data=fixture()
        self.catalog=read_catalog(self.root)
        self.sid=self.result('direct.start',dict(text=self.data['ask'],mode='complete',model='seedance-2.0',movement_sets=True))['session_id']
    def select(self,set_id,term):
        return copy.deepcopy(next(m['selection'] for m in self.catalog[set_id]['members'] if m['term']==term))
    def chosen(self):
        ds=stacks()['performance']
        for d in ds:
            field=next(iter(d['values']))
            if field in {'effort_weight','effort_time','effort_space','effort_flow'}:
                factor=field.split('_')[1];term={'weight':'strong','time':'sudden','space':'direct','flow':'bound'}[factor]
                d['values'][field]=self.select('laban.effort.'+factor,term)
            elif field=='shape':d['values'][field]=self.select('laban.shape.quality','advancing')
            elif field=='connectivity':d['values'][field]=self.select('bartenieff.connectivity','upper-lower')
        return ds
    def test_menus_are_pass_scoped_hash_bound_and_untested(self):
        p=self.packet('scene_action')
        self.assertNotIn('laban.effort.weight',p['fixed_sets'])
        self.scene();p=self.packet('performance')
        self.assertEqual(len(p['fixed_sets']),9);self.assertEqual(p['registry_gaps'],[])
        member=p['fixed_sets']['laban.effort.weight']['members'][0]
        self.assertEqual(member['selection'],self.select('laban.effort.weight','light'))
        self.assertEqual(member['model_support'],'untested');self.assertIn('definition',member)
        self.assertEqual(p,self.packet('performance'))
    def test_outside_set_rejects_atomically_with_registry_gap(self):
        self.scene();before=self.result('direct.state.read',dict(session_id=self.sid))
        ds=self.chosen();ds[1]['values']['effort_weight']='invented effort'
        self.rejected(self.submit('performance',ds),'REGISTRY_GAP')
        self.assertEqual(before,self.result('direct.state.read',dict(session_id=self.sid)))
    def test_public_finish_and_both_carriers_use_one_accepted_selection(self):
        self.scene();self.assertEqual(self.submit('performance',self.chosen())['disposition'],'accepted')
        for p,ds in stacks().items():
            if p!='performance':self.assertEqual(self.submit(p,ds)['disposition'],'accepted')
        finished=self.result('direct.finish',dict(session_id=self.sid));score=finished['score']
        request=make_build_request(score,project_id='closed-test',duration_seconds=15,model='seedance-2.0',prompt_format='prose')
        prose=compile_build(request,root=self.root)
        self.assertIn(b'firm body effort',prose['prompt.txt']);self.assertNotIn(b'member_hash',prose['prompt.txt'])
        request['settings']['prompt_format']='json';structured=compile_build(request,root=self.root)
        self.assertIn(b'laban.effort.weight.strong',structured['prompt.txt'])
        self.assertEqual(prose['canonical_score.json'],structured['canonical_score.json'])


    def test_small_accepted_scene_builds_labelled_wording_and_records_closed_bytes(self):
        from lab.application.tests.test_directing_pipeline import decision
        sid=self.result('direct.start',dict(text='An educational video showing a grounded reach, 15 seconds',model='seedance-2.0'))['session_id']
        self.sid=sid
        ds=[decision('scene','scene_action','scene','scenes','small',dict(duration_s=15,location='room',direction={'GOAL':[dict(text='Show one grounded reach.')]})),
            decision('actor','scene_action','entities','entities','a',dict(name='A',kind='person')),
            decision('beat','scene_action','beats','beats','b',dict(order=1,min_s=15,duration_s=15,role='reach',direction={'EFFORT':[dict(ref='actions.act.effort_weight',form='plain')]})),
            decision('act','scene_action','actions','actions','act',dict(actor='a',beat='b',order=1,verb='reaches',effort_weight=self.select('laban.effort.weight','light')))]
        self.assertEqual(self.submit('scene_action',ds)['disposition'],'accepted')
        finished=self.result('direct.finish',dict(session_id=sid,build_settings=dict(project_id='closed-small',prompt_format='prose',prompt_layout='labelled_skeleton_v1')))
        folder=Path(finished['build']['output_dir'])
        self.assertEqual((folder/'prompt.txt').read_bytes(),b'GOAL      Show one grounded reach.\n\nBEAT 1 (15s) reach\n  EFFORT   light body effort\n\n')
        audit=json.loads((folder/'capability_report.json').read_text())['projection_audit']
        self.assertEqual(audit['closed_code']['bytes'],17)
        self.assertFalse(audit['closed_code']['model_efficacy_claim'])
    def test_missing_live_inventory_is_reported_without_generated_members(self):
        fresh=fixture_root(Path(self.temp.name)/'absent')
        from lab.second_brain.src import directing_session as direct
        sid=direct.start_session('A reach, 15 seconds',mode='complete',preferences={'movement_sets':True},root=fresh)['session_id']
        packet=direct.read_packet(sid,'performance',root=fresh)
        self.assertEqual(packet['fixed_sets'],{})
        self.assertIn('laban.effort.weight',[g['set_id'] for g in packet['registry_gaps']])
    def test_opt_in_requires_complete_mode(self):
        response=self.call('direct.start',dict(text='A reach',movement_sets=True))
        self.assertEqual(response['status'],'error')
        self.assertIn('complete',response['error']['message'])

    def test_chain_failure_rejects_public_stack_without_ledger_change(self):
        self.scene();before=self.result('direct.state.read',dict(session_id=self.sid))
        ds=self.chosen();ds[0]['values']['body']={'initiation_chain':dict(kind=self.select('motion.initiation_chain.kind','successive'),root='left_foot',path=['left_foot','left_hand'],pattern=self.select('bartenieff.connectivity','upper-lower'),departure_reason='Intentional new upper-lower tactic.')}
        self.rejected(self.submit('performance',ds),'CHAIN_NOT_ADJACENT')
        self.assertEqual(before,self.result('direct.state.read',dict(session_id=self.sid)))
    def test_uniform_spacing_is_preserved_in_build_report(self):
        self.scene();ds=self.chosen()
        ds[0]['values']['body']={'phases':[dict(phase=p,spacing=self.select('motion.spacing','even')) for p in ['preparation','execution']]}
        self.assertEqual(self.submit('performance',ds)['disposition'],'accepted')
        for p,ds in stacks().items():
            if p!='performance':self.assertEqual(self.submit(p,ds)['disposition'],'accepted')
        score=self.result('direct.finish',dict(session_id=self.sid))['score']
        built=compile_build(make_build_request(score,project_id='uniform-test',duration_seconds=15,model='seedance-2.0',prompt_format='json'),root=self.root)
        report=json.loads(built['capability_report.json'])
        self.assertEqual([r['code'] for r in report['movement_reports']],['SPACING_UNIFORM'])

    def test_definition_citation_preserves_creative_application(self):
        self.scene();ds=self.chosen()
        member=next(m for m in self.catalog['laban.effort.weight']['members'] if m['term']=='strong')
        ds[1]['evidence_uses']=[dict(kind='concept',id=member['concept_id'],content_hash=member['selection']['member_hash'])]
        self.assertEqual(self.submit('performance',ds)['disposition'],'accepted')
        state=self.result('direct.state.read',dict(session_id=self.sid))
        choice=next(d for d in state['decisions'] if d['decision_id']=='p_effort_weight')
        self.assertEqual(choice['source_status'],'creative_application')
        self.assertEqual(choice['evidence_uses'],ds[1]['evidence_uses'])
    def test_build_snapshot_lists_each_selected_definition_hash(self):
        self.scene();self.assertEqual(self.submit('performance',self.chosen())['disposition'],'accepted')
        for p,ds in stacks().items():
            if p!='performance':self.assertEqual(self.submit(p,ds)['disposition'],'accepted')
        score=self.result('direct.finish',dict(session_id=self.sid))['score']
        built=compile_build(make_build_request(score,project_id='snapshot-test',duration_seconds=15,model='seedance-2.0',prompt_format='prose'),root=self.root)
        manifest=json.loads(built['build_manifest.json'])
        expected={'c_fixture_laban_effort_weight_strong','c_fixture_laban_effort_time_sudden','c_fixture_laban_effort_space_direct','c_fixture_laban_effort_flow_bound','c_fixture_laban_shape_quality_advancing','c_fixture_bartenieff_connectivity_upper_lower'}
        self.assertTrue(expected <= set(manifest['concept_ids']))
        self.assertEqual(set(manifest['concept_ids']),set(manifest['concept_hashes']))
