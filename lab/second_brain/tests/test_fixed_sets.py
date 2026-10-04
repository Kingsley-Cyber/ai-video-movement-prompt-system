import copy
import tempfile
import unittest
from pathlib import Path
from lab.second_brain.src.fixed_sets import read_catalog, resolve_selection, RegistryGap
from lab.second_brain.src.validate import validate_curated, read_jsonl
from lab.second_brain.tests.test_directing_session import fixture_root
from lab.second_brain.tests.fixed_set_fixture import install
from lab.second_brain.tests.helpers import write_rows

class FixedSetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=fixture_root(Path(self.temp.name));install(self.root)

    def test_complete_owner_membership_and_flow_independent_recipes(self):
        catalog=read_catalog(self.root)
        self.assertEqual(len(catalog),9)
        self.assertEqual(sum(len(v['members']) for v in catalog.values()),35)
        for member in catalog['laban.effort.action']['members']:
            self.assertEqual(set(member['recipe']),{'weight','time','space'})
        self.assertEqual(catalog['motion.spacing']['authority'],'project_convention')
        self.assertEqual(catalog['laban.effort.weight']['authority'],'external_standard')
        self.assertTrue(all(m['model_support']=='untested' for v in catalog.values() for m in v['members']))

    def test_selection_binds_code_definition_and_version(self):
        m=read_catalog(self.root)['laban.effort.weight']['members'][0]
        resolved=resolve_selection(m['selection'],self.root)
        self.assertEqual(resolved['visible_wording'],'light body effort')
        bad=copy.deepcopy(m['selection']);bad['code']='laban.effort.weight.unsourced'
        with self.assertRaises(RegistryGap):resolve_selection(bad,self.root)
        bad=copy.deepcopy(m['selection']);bad['member_hash']='sha256:'+'a'*64
        with self.assertRaisesRegex(RegistryGap,'stale'):resolve_selection(bad,self.root)

    def test_missing_member_is_a_gap_not_partial_success(self):
        path=self.root/'lab/concepts.jsonl';rows=read_jsonl(path)
        write_rows(path,[r for r in rows if r['id']!='c_fixture_laban_effort_weight_light'])
        with self.assertRaisesRegex(RegistryGap,'missing'):read_catalog(self.root)

    def test_duplicate_code_rejected(self):
        path=self.root/'lab/second_brain/curated/domain_coverage_manifests.jsonl';rows=read_jsonl(path)
        m=next(r for r in rows if r.get('fixed_set',{}).get('set_id')=='laban.effort.weight')
        m['fixed_set']['members'][1]['code']=m['fixed_set']['members'][0]['code'];write_rows(path,rows)
        with self.assertRaises(RegistryGap):read_catalog(self.root)

    def test_manifest_and_card_version_must_agree(self):
        path=self.root/'lab/concepts.jsonl';rows=read_jsonl(path)
        next(r for r in rows if r['id']=='c_fixture_laban_effort_weight_light')['params']['fixed_set_member']['version']='other'
        write_rows(path,rows)
        with self.assertRaises(RegistryGap):read_catalog(self.root)

    def test_source_hash_must_close(self):
        path=self.root/'lab/concepts.jsonl';rows=read_jsonl(path)
        next(r for r in rows if r['id']=='c_fixture_laban_effort_weight_light')['params']['fixed_set_member']['source_batch_sha256']='sha256:'+'a'*64
        write_rows(path,rows)
        with self.assertRaises(RegistryGap):read_catalog(self.root)

    def test_flow_is_not_a_recipe_field(self):
        path=self.root/'lab/concepts.jsonl';rows=read_jsonl(path)
        next(r for r in rows if r['id']=='c_fixture_laban_effort_action_punch')['params']['fixed_set_member']['recipe']['flow']='bound'
        write_rows(path,rows)
        with self.assertRaises(ValueError):validate_curated(self.root)

    def test_absent_catalog_does_not_invent_members(self):
        fresh=fixture_root(Path(self.temp.name)/'empty')
        from lab.second_brain.tests.fixed_set_fixture import empty_inventory
        empty_inventory(fresh)
        self.assertEqual(read_catalog(fresh),{})

    def test_legacy_metadata_validation_does_not_enable_unclosed_selection(self):
        # A legacy repository may carry inventory metadata without declaring
        # source units as authority. Selection must still fail closed there.
        (self.root / 'lab/registry.yaml').unlink()
        write_rows(self.root / 'lab/second_brain/immutable/source_units.jsonl', [])
        validate_curated(self.root)
        with self.assertRaisesRegex(RegistryGap, 'missing exact source evidence'):
            read_catalog(self.root)

    def test_curated_validator_checks_declared_membership(self):
        path=self.root/'lab/second_brain/curated/domain_coverage_manifests.jsonl';rows=read_jsonl(path)
        rows[-1]['fixed_set']['members'][0]['code']='motion.initiation_chain.kind.other'
        write_rows(path,rows)
        with self.assertRaisesRegex(ValueError,'REGISTRY_GAP'):validate_curated(self.root)
