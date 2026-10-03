from __future__ import annotations
import copy
import unittest
from lab.compiler.decisions import validate_decisions, scene_from_decisions
from lab.compiler.build import _direction_line
from lab.second_brain.tests.test_directing_session import fixture
from lab.second_brain.src.directing_session import load_pass_registry

class DirectingQuantityTests(unittest.TestCase):
    def setUp(self):
        self.ds=copy.deepcopy(fixture()['proposal']['decisions'])
        self.spec=load_pass_registry()['passes'][0]
        self.packet={'constraints':{'requested_duration_s':15},'steering':'visible quantities'}

    def quantity(self,value,visible):
        return dict(value=value,scale=dict(min=0,max=1),visible=visible)

    def test_declared_scale_preserves_numeric_truth_and_emits_visible_words(self):
        self.ds[10]['values']['effort_weight']=self.quantity(0.6,'Weight travels from the support foot into both palms.')
        self.assertEqual(validate_decisions(self.ds,self.spec,self.packet),[])
        s=scene_from_decisions(self.ds);a=next(a for a in s['actions'] if a['id']=='act_2')
        self.assertEqual(a['effort_weight']['value'],0.6)
        text=_direction_line({'path':'actions','value':[a]},s,{})
        self.assertIn('Weight travels',text);self.assertNotIn('0.6',text)

    def test_quantity_outside_its_declared_scale_is_rejected(self):
        self.ds[10]['values']['effort_weight']=self.quantity(2,'A visible weight shift.')
        self.assertIn('quantity_out_of_scale',[e['code'] for e in validate_decisions(self.ds,self.spec,self.packet)])

    def test_numeric_comparison_cannot_contradict_its_relative_direction(self):
        self.ds[9]['values']['speed']=self.quantity(0.8,'The walk establishes the pace.')
        self.ds[11]['values']['speed']=self.quantity(0.3,'The cross is faster than the walk.')
        self.assertIn('relative_direction_mismatch',[e['code'] for e in validate_decisions(self.ds,self.spec,self.packet)])

if __name__=='__main__':unittest.main()
