from __future__ import annotations
import copy
import unittest
# Import the module, not the class: a TestCase class in this namespace would be discovered and run twice.
from lab.application.tests import test_directing_pipeline as pipeline
from lab.application.tests.test_directing_pipeline import stacks, decision

class DirectingInvariantTests(unittest.TestCase):
    def setUp(self):
        self.client=pipeline.DirectingPipelineTests();self.client.setUp();self.addCleanup(self.client.doCleanups)

    def test_lighting_packet_receives_transitive_action_and_body_context(self):
        c=self.client;c.scene()
        for p in ('performance','staging','camera'):self.assertEqual(c.submit(p,stacks()[p])['disposition'],'accepted')
        ids={d['decision_id'] for d in c.packet('light_color')['upstream']}
        self.assertIn('d_action_2',ids);self.assertIn('p_body',ids);self.assertIn('cam_framing',ids)

    def test_independent_relative_qualities_survive_on_the_same_action(self):
        c=self.client;ds=copy.deepcopy(c.data['proposal']['decisions'])
        ds[9]['values']['intensity']='The approach establishes the baseline pressure.'
        ds.append(decision('second_quality','scene_action','actions','actions','act_3',{'pressure':'The counter carries more pressure than the approach.'},['d_action_1'],
              {'baseline':{'item':'act_1','quality':'intensity'},'change':{'direction':'more','step':'slightly'}}))
        self.assertEqual(c.submit('scene_action',ds)['disposition'],'accepted')
        state=c.result('direct.state.read',dict(session_id=c.sid))
        relative=next(a for a in state['scene']['actions'] if a['id']=='act_3')['relative']
        self.assertIsInstance(relative,list)
        self.assertEqual({r['quality'] for r in relative},{'speed','intensity'})

    def test_a_shot_cannot_reference_an_unknown_beat(self):
        c=self.client;c.scene();c.submit('performance',stacks()['performance']);c.submit('staging',stacks()['staging'])
        ds=stacks()['camera'];ds[0]['values']['beat']='unknown_beat'
        c.rejected(c.submit('camera',ds),'unknown_reference')

if __name__=='__main__':unittest.main()
