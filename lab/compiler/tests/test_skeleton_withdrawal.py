import unittest
from lab.compiler.tests.test_labelled_skeleton import champion,build
class SkeletonWithdrawalContracts(unittest.TestCase):
    def test_protected_omission_rejected(self):
        s=champion();del s['beats'][6]['direction']['PROP']
        s['scenes'][0]['direction_omissions']=[dict(ref='beats.b07.direction.PROP',decision_id='rail_break',reason='drop')]
        with self.assertRaisesRegex(ValueError,'PROTECTED'):build(s)
    def test_unresolved_typed_binding_rejected(self):
        s=champion();s['beats'][0]['direction']['RANGE'][0]={'ref':'entities.missing.name','form':'plain'}
        with self.assertRaisesRegex(ValueError,'REFERENCE'):build(s)
        from lab.compiler.skeleton import validate_scene
        with self.assertRaisesRegex(ValueError,'REFERENCE'):validate_scene(s)
    def test_default_layout_records_withdrawn_field_loss(self):
        s=champion();del s['scenes'][0]['skeleton_recipe'];del s['beats'][1]['direction']['FACE']
        s['scenes'][0]['direction_omissions']=[dict(ref='beats.b02.direction.FACE',decision_id='face_b02',reason='Optional face withdrawn.')]
        import json
        losses=json.loads(build(s)['loss_report.json'])['losses']
        self.assertTrue(any(l['loss_type']=='omitted_decision' and l['path']=='beats.b02.direction.FACE' and 'face_b02' in l['reason'] for l in losses))
