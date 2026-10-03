from __future__ import annotations
import copy
import json
import tempfile
import unittest
from pathlib import Path
from lab.compiler.build import compile_build, make_build_request, load_validated_build_directory, write_build_directory
from lab.compiler.tests.test_build import ready_score


class DirectingBuildTests(unittest.TestCase):
    def setUp(self):
        self.score=ready_score('Create a multi-actor action scene with readable screen direction')

    def test_same_score_projects_to_two_models_with_explicit_route_differences(self):
        veo=compile_build(make_build_request(self.score,project_id='cpcs-export-test',prompt_format='prose'))
        seedance=compile_build(make_build_request(self.score,project_id='cpcs-export-test',model='seedance-2.0',prompt_format='prose'))
        self.assertEqual(veo['canonical_score.json'],seedance['canonical_score.json'])
        self.assertEqual(json.loads(veo['provider_request.json'])['method'],'POST')
        self.assertEqual(json.loads(seedance['provider_request.json'])['method'],'MANUAL')
        self.assertNotEqual(veo['build_manifest.json'],seedance['build_manifest.json'])
        self.assertTrue(json.loads(seedance['loss_report.json'])['provider_limitations'])

    def test_manual_build_uses_same_hash_validated_eight_artifact_loader(self):
        a=compile_build(make_build_request(self.score,project_id='cpcs-export-test',model='seedance-2.0',prompt_format='json'))
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'build';write_build_directory(a,p)
            loaded=load_validated_build_directory(p)
            self.assertEqual(loaded['artifact_bytes'],a)
            (p/'prompt.txt').write_text('Changed prompt')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                load_validated_build_directory(p)

    def test_unknown_model_is_rejected_without_guessing_capability(self):
        request=make_build_request(self.score,project_id='cpcs-export-test')
        request['target']['model']='unknown-model'
        with self.assertRaises(ValueError):compile_build(request)

    def test_unsupported_length_never_silently_trims_the_model_request(self):
        request=make_build_request(self.score,project_id='cpcs-export-test',duration_seconds=15)
        original=copy.deepcopy(request)
        with self.assertRaisesRegex(ValueError,'duration_seconds'):compile_build(request)
        self.assertEqual(original,request)

    def test_unknown_budget_preserves_long_control_and_reports_unknown(self):
        s=ready_score('Create a multi-actor action scene with readable screen direction',overlays=[dict(overlay_id='overlay_long_scene',scope='scene_override',priority=0,values={'scenes':[{'id':'scene_long','description':'visible texture '*1500}]},locks=[],source_refs=['test-authored://long-scene'])])
        a=compile_build(make_build_request(s,project_id='cpcs-export-test',model='seedance-2.0'))
        self.assertIn('visible texture '*1500,a['prompt.txt'].decode())
        report=json.loads(a['capability_report.json']);self.assertIsNone(report['prompt_budget_chars'])
        self.assertIn('unknown', ' '.join(report['limitations']))

if __name__=='__main__':unittest.main()
