"""Owner-approved research inventory through the public accepted-scene path."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from lab.application.tests import test_directing_pipeline as pipeline
from lab.second_brain.src.fixed_sets import read_catalog
from lab.second_brain.src.validate import REPO_ROOT
from lab.second_brain.tests.test_directing_session import fixture_root


APPROVED = {
    'laban.effort.weight': {'light', 'strong'},
    'laban.effort.time': {'sustained', 'sudden'},
    'laban.effort.space': {'indirect', 'direct'},
    'laban.effort.flow': {'free', 'bound'},
    'laban.effort.action': {'punch', 'slash', 'dab', 'flick', 'press', 'wring', 'glide', 'float'},
    'laban.shape.quality': {'rising', 'sinking', 'spreading', 'enclosing', 'advancing', 'retreating'},
    'bartenieff.connectivity': {'breath', 'core-distal', 'head-tail', 'upper-lower', 'body-half', 'cross-lateral'},
    'motion.spacing': {'even', 'ease_in', 'ease_out', 'ease_in_out'},
    'motion.initiation_chain.kind': {'simultaneous', 'successive', 'sequential'},
}


class LiveClosedMovementTests(unittest.TestCase):
    call = pipeline.DirectingPipelineTests.call
    result = pipeline.DirectingPipelineTests.result
    packet = pipeline.DirectingPipelineTests.packet
    submit = pipeline.DirectingPipelineTests.submit

    def test_live_members_close_exact_owner_inventory_with_untested_support(self):
        catalog = read_catalog(REPO_ROOT)
        self.assertEqual(set(catalog), set(APPROVED))
        for name, terms in APPROVED.items():
            members = catalog[name]['members']
            self.assertEqual({m['term'] for m in members}, terms)
            for m in members:
                self.assertFalse(m['concept_id'].startswith('c_fixture_'))
                self.assertTrue(m['source_unit_ids'])
                self.assertEqual(m['model_support'], 'untested')
                self.assertEqual(m['evidence_status'], 'unexplored')
                self.assertEqual(m['authority'], 'project_convention' if name.startswith('motion.') else 'external_standard')
                if 'recipe' in m:
                    self.assertEqual(set(m['recipe']), {'weight', 'time', 'space'})

    def test_real_accepted_breath_scene_pins_visible_output_and_byte_share(self):
        temporary = tempfile.TemporaryDirectory(dir=REPO_ROOT / 'work')
        self.addCleanup(temporary.cleanup)
        self.root = fixture_root(Path(temporary.name))
        catalog = read_catalog(self.root)
        member = next(m for m in catalog['bartenieff.connectivity']['members'] if m['term'] == 'breath')
        self.sid = self.result('direct.start', dict(text='An educational video showing a grounded breath, 15 seconds', model='seedance-2.0'))['session_id']
        decision = pipeline.decision
        ds = [
            decision('scene', 'scene_action', 'scene', 'scenes', 'small', dict(duration_s=15, location='room', direction={'GOAL': [dict(text='Show one grounded breath.')]})),
            decision('actor', 'scene_action', 'entities', 'entities', 'a', dict(name='A', kind='person')),
            decision('beat', 'scene_action', 'beats', 'beats', 'b', dict(order=1, min_s=15, duration_s=15, role='breath', direction={'BODY': [dict(ref='actions.act.connectivity', form='plain')]})),
            decision('act', 'scene_action', 'actions', 'actions', 'act', dict(actor='a', beat='b', order=1, verb='breathes', connectivity=copy.deepcopy(member['selection']))),
        ]
        self.assertEqual(self.submit('scene_action', ds)['disposition'], 'accepted')
        finished = self.result('direct.finish', dict(session_id=self.sid, build_settings=dict(project_id='live-breath', prompt_format='prose', prompt_layout='labelled_skeleton_v1')))
        folder = Path(finished['build']['output_dir'])
        expected = b'GOAL      Show one grounded breath.\n\nBEAT 1 (15s) breath\n  BODY     the whole body swells and shrinks with the breath\n\n'
        self.assertEqual((folder / 'prompt.txt').read_bytes(), expected)
        audit = json.loads((folder / 'capability_report.json').read_text())['projection_audit']
        self.assertEqual(audit['closed_code']['bytes'], 49)
        self.assertFalse(audit['closed_code']['model_efficacy_claim'])
