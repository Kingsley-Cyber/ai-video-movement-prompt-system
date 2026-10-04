"""Closed-selection checks and printed-byte proof with synthetic source fixtures."""
import copy
import tempfile
import unittest
from pathlib import Path
from lab.compiler import decisions, skeleton
from lab.second_brain.src.fixed_sets import read_catalog
from lab.second_brain.tests.test_directing_session import fixture_root
from lab.second_brain.tests.fixed_set_fixture import install

class ClosedMovementTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=fixture_root(Path(self.temp.name));install(self.root)
        self.catalog=read_catalog(self.root)
    def select(self,set_id,term):
        return copy.deepcopy(next(m['selection'] for m in self.catalog[set_id]['members'] if m['term']==term))
    def scene(self):
        s=dict(scenes=[dict(id='small',duration_s=1,direction={'GOAL':[dict(text='Show one grounded reach.')]})],
            entities=[dict(id='a',kinetic_signature={'patterns':[self.select('bartenieff.connectivity','upper-lower')]})],
            beats=[dict(id='b',order=1,duration_s=1,role='reach',direction={'EFFORT':[dict(ref='actions.act.effort_weight',form='plain')]})],
            actions=[dict(id='act',actor='a',beat='b',effort_weight=self.select('laban.effort.weight','light'))],interactions=[],shots=[])
        return s
    def check(self,scene):return decisions.movement_checks(scene,root=self.root)
    def chain(self,kind='successive',path=None,pattern='upper-lower'):
        return dict(kind=self.select('motion.initiation_chain.kind',kind),root='left_foot',
                    path=path or ['left_foot','left_ankle','left_knee','left_hip','pelvis','spine'],
                    pattern=self.select('bartenieff.connectivity',pattern))
    def codes(self,scene):return [r['code'] for r in self.check(scene)[0]]
    def test_default_recipe_prints_closed_wording_and_counts_retained_bytes(self):
        s=self.scene();text,audit,loss=skeleton.project(s,root=self.root)
        self.assertEqual(text,'GOAL      Show one grounded reach.\n\nBEAT 1 (1s) reach\n  EFFORT   light body effort\n\n')
        self.assertEqual(audit['closed_code']['bytes'],17)
        self.assertGreaterEqual(audit['byte_counts']['typed_bound'],17)
        self.assertEqual(loss,[])
        s['actions'][0]['effort_weight']=self.select('laban.effort.weight','strong')
        changed,_,_=skeleton.project(s,root=self.root)
        self.assertIn('firm body effort',changed);self.assertNotIn('light body effort',changed)
    def test_wrap_inside_member_wording_excludes_consumed_space(self):
        # Mutate fixture wording and re-read its hash; no production knowledge change.
        from lab.second_brain.tests.helpers import write_rows
        from lab.second_brain.src.validate import read_jsonl
        p=self.root/'lab/concepts.jsonl';rows=read_jsonl(p)
        next(r for r in rows if r['id']=='c_fixture_laban_effort_weight_light')['params']['fixed_set_member']['visible_wording']='One. Two.'
        write_rows(p,rows);self.catalog=read_catalog(self.root)
        text,audit,_=skeleton.project(self.scene(),root=self.root)
        self.assertIn('One.\n           Two.',text)
        self.assertEqual(audit['closed_code']['bytes'],8)
    def test_unknown_code_and_stale_hash_cannot_compile(self):
        s=self.scene();s['actions'][0]['effort_weight']['code']='laban.effort.weight.invented'
        with self.assertRaisesRegex(ValueError,'REGISTRY_GAP'):skeleton.project(s,root=self.root)
        s=self.scene();s['actions'][0]['effort_weight']['member_hash']='sha256:'+'a'*64
        with self.assertRaisesRegex(ValueError,'REGISTRY_GAP'):skeleton.project(s,root=self.root)
    def test_wrong_set_cannot_fill_bound_slot(self):
        s=self.scene();s['actions'][0]['effort_weight']=self.select('laban.effort.time','sudden')
        self.assertIn('REGISTRY_GAP',self.codes(s))
    def test_successive_path_checks_every_edge(self):
        s=self.scene();s['actions'][0]['body']={'initiation_chain':self.chain()}
        self.assertEqual(self.check(s)[0],[])
        s['actions'][0]['body']['initiation_chain']['path']=['left_foot','left_hand']
        self.assertIn('CHAIN_NOT_ADJACENT',self.codes(s))
    def test_sequential_requires_nonadjacent_step(self):
        s=self.scene();s['actions'][0]['body']={'initiation_chain':self.chain('sequential')}
        self.assertIn('CHAIN_NOT_ADJACENT',self.codes(s))
        s['actions'][0]['body']['initiation_chain']['path']=['left_foot','left_hand']
        self.assertEqual(self.check(s)[0],[])
    def test_sides_meet_only_at_pelvis_and_chest(self):
        s=self.scene();s['actions'][0]['body']={'initiation_chain':self.chain(path=['left_hip','pelvis','right_hip'])}
        s['actions'][0]['body']['initiation_chain']['root']='left_hip'
        self.assertEqual(self.check(s)[0],[])
        s['actions'][0]['body']['initiation_chain']['path']=['left_shoulder','right_shoulder']
        s['actions'][0]['body']['initiation_chain']['root']='left_shoulder'
        self.assertIn('CHAIN_NOT_ADJACENT',self.codes(s))
    def test_chain_root_and_body_parts_are_explicit(self):
        s=self.scene();s['actions'][0]['body']={'initiation_chain':self.chain(path=['unknown','spine'])}
        self.assertIn('CHAIN_NOT_ADJACENT',self.codes(s))
    def test_signature_departure_requires_reason(self):
        s=self.scene();s['actions'][0]['body']={'initiation_chain':self.chain(pattern='cross-lateral')}
        self.assertIn('INITIATION_CHAIN_MISMATCH',self.codes(s))
        s['actions'][0]['body']['initiation_chain']['departure_reason']='A deliberate cross-body recovery interrupts the habitual chain.'
        self.assertNotIn('INITIATION_CHAIN_MISMATCH',self.codes(s))
    def test_explicit_phase_crosswalk_and_order(self):
        s=self.scene();s['actions'][0]['body']={'phases':[{'phase':p} for p in ['preparation','initiation','stroke','endstroke','follow-through','recuperation']]}
        self.assertEqual(self.check(s)[0],[])
        s['actions'][0]['body']['phases']=[{'phase':p} for p in ['recovery','execution']]
        self.assertIn('PHASE_ORDER',self.codes(s))
        s['actions'][0]['body']['phases']=[{'phase':'unknown'}]
        self.assertIn('PHASE_ORDER',self.codes(s))
    def test_uniform_spacing_reports_without_rejecting(self):
        s=self.scene();s['actions'][0]['body']={'phases':[dict(phase=p,spacing=self.select('motion.spacing','even')) for p in ['preparation','execution']]}
        errors,reports=self.check(s);self.assertEqual(errors,[])
        self.assertIn('SPACING_UNIFORM',[r['code'] for r in reports])
        s['actions'][0]['body']['spacing_reason']='Deliberately mechanical reach.'
        self.assertEqual(self.check(s)[1],[])
    def test_action_recipe_checks_only_selected_factors_not_flow(self):
        s=self.scene();a=s['actions'][0];a['body']={'effort_action':self.select('laban.effort.action','punch')}
        self.assertIn('EFFORT_RECIPE_MISMATCH',self.codes(s))
        a['effort_weight']=self.select('laban.effort.weight','strong');a['effort_flow']=self.select('laban.effort.flow','free')
        self.assertEqual(self.check(s)[0],[])
        a['effort_weight']=self.select('laban.effort.weight','light');a['body']['recipe_departure_reason']='Light preparation borrows the directional recipe without its weight.'
        self.assertEqual(self.check(s)[0],[])
    def test_legacy_free_wording_is_unchanged_without_opt_in(self):
        s=self.scene();s['actions'][0]['effort_weight']='authored reach';s['entities'][0].pop('kinetic_signature')
        self.assertEqual(self.check(s),([],[]))
        text,audit,_=skeleton.project(s,root=self.root)
        self.assertIn('authored reach',text);self.assertNotIn('closed_code',audit)

    def test_null_departure_is_not_a_reason(self):
        s=self.scene();s['actions'][0]['body']={'initiation_chain':self.chain(pattern='cross-lateral')}
        s['actions'][0]['body']['initiation_chain']['departure_reason']=None
        self.assertIn('INITIATION_CHAIN_MISMATCH',self.codes(s))
        s=self.scene();s['actions'][0]['body']={'effort_action':self.select('laban.effort.action','punch'),'recipe_departure_reason':None}
        self.assertIn('EFFORT_RECIPE_MISMATCH',self.codes(s))
    def test_initiation_precedes_stroke_within_execution_crosswalk(self):
        s=self.scene();s['actions'][0]['body']={'phases':[{'phase':'stroke'},{'phase':'initiation'}]}
        self.assertIn('PHASE_ORDER',self.codes(s))
