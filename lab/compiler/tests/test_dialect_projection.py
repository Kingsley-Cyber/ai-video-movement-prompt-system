import json
import unittest
from lab.compiler.build import compile_build,make_build_request
from lab.compiler.tests.test_build import ready_score

class DialectProjectionTests(unittest.TestCase):
    def setUp(self):
        self.score=ready_score('Create an original shonen counterattack with readable screen direction',overlays=[dict(overlay_id='overlay_timing',scope='scene_override',priority=0,values={'beats':[{'id':'beat_probe','order':1,'label':'probe','start_s':0,'duration_s':8,'min_s':8}]},locks=[],source_refs=['test-authored://timing'])])

    def test_seedance_prose_does_not_claim_timestamp_conditioning(self):
        seedance=compile_build(make_build_request(self.score,project_id='cpcs-export-test',model='seedance-2.0',prompt_format='prose'))
        veo=compile_build(make_build_request(self.score,project_id='cpcs-export-test',prompt_format='prose'))
        self.assertNotIn('start s:',seedance['prompt.txt'].decode())
        self.assertIn('start s:',veo['prompt.txt'].decode())
        self.assertEqual(seedance['canonical_score.json'],veo['canonical_score.json'])
        self.assertIn('timing',' '.join(r['reason'].lower() for r in json.loads(seedance['loss_report.json'])['losses']))

    def test_seedance_json_keeps_numeric_truth_with_an_explicit_timing_loss(self):
        a=compile_build(make_build_request(self.score,project_id='cpcs-export-test',model='seedance-2.0',prompt_format='json'))
        self.assertEqual(json.loads(a['prompt.txt'])['beats'][0]['start_s'],0)
        self.assertIn('timestamp',' '.join(r['reason'].lower() for r in json.loads(a['loss_report.json'])['losses']))

if __name__=='__main__':unittest.main()
