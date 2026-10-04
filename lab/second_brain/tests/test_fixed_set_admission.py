"""Closed-set admission through source, placement and reviewed bundle owners."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from lab.application.service import REQUEST_SCHEMA, authorization_request_hash, invoke
from lab.second_brain.src.curate import promote_distillation_bundle
from lab.second_brain.src.fixed_sets import read_catalog
from lab.second_brain.src.ingest import ingest_distillation_batch
from lab.second_brain.src.placement import plan_graph_growth
from lab.second_brain.src.validate import REPO_ROOT, ValidationFailure, read_jsonl, validate_curated, validate_instance
from lab.second_brain.tests.fixed_set_fixture import install
from lab.second_brain.tests.helpers import concept, make_root, representation_strategy, write_rows
from lab.second_brain.tests.test_source_registry import _review


class FixedSetAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        anchor = concept('c_anchor', 'Gesture taxonomy', 'whole-body movement')
        anchor.update(what='A taxonomy groups qualitative movement facets.', use_when='Organize vocabulary.', nl_triggers=['taxonomy', 'classification', 'inventory'])
        self.root = make_root(Path(self.temp.name), [anchor])
        shutil.copytree(REPO_ROOT / 'lab/application/schemas', self.root / 'lab/application/schemas')
        shutil.copytree(REPO_ROOT / 'lab/release', self.root / 'lab/release')
        self.coverage = self.root / 'lab/second_brain/curated/domain_coverage_manifests.jsonl'
        write_rows(self.coverage, [])
        install(self.root)
        all_cards = read_jsonl(self.root / 'lab/concepts.jsonl')
        self.cards = [c for c in all_cards if c.get('params', {}).get('fixed_set_member', {}).get('set_id') == 'laban.effort.weight']
        self.manifest = next(m for m in read_jsonl(self.coverage) if m['fixed_set']['set_id'] == 'laban.effort.weight')
        write_rows(self.root / 'lab/concepts.jsonl', [c for c in all_cards if 'fixed_set_member' not in c.get('params', {})])
        write_rows(self.coverage, [])
        (self.root / 'lab/registry.yaml').write_text('scripts:\n  second_brain_source_units: second_brain/immutable/source_units.jsonl\n  second_brain_graph_growth_plans: second_brain/staging/graph_growth_plans.jsonl\n')
        write_rows(self.root / 'lab/second_brain/staging/graph_growth_plans.jsonl', [])

    def stage(self, *, stale_hash=False):
        candidates = []
        for index, card in enumerate(self.cards, start=1):
            cid = card['id']
            record = copy.deepcopy(card)
            evidence = record.pop('provenance')['source_evidence']
            record.pop('id')
            record['kind'] = 'technique'
            if stale_hash:
                record['params']['fixed_set_member']['source_batch_sha256'] = 'sha256:' + '0' * 64
            common = dict(source_evidence=evidence, created_by='local_source', created_at='2026-10-04T00:00:00Z')
            candidates.append(dict(candidate_id='candidate_' + cid, proposal_type='concept', suggested_id=cid, proposed_record=record, **common))
            edge_id = f'edge_{index:06d}'
            candidates.append(dict(candidate_id='candidate_' + edge_id, proposal_type='edge', suggested_id=edge_id, proposed_record=dict(u=cid, v='c_anchor', type='refines', context='movement', authored_by='local_source', note='Synthetic effort facet refines the movement anchor.', sources=[dict(ref=evidence[0]['source_id'], locator=evidence[0]['locator'])]), **common))
            mapping_id = 'mapping_' + cid[2:]
            target = 'motion.fixed_sets.' + record['params']['fixed_set_member']['code']
            candidates.append(dict(candidate_id='candidate_' + mapping_id, proposal_type='mapping', suggested_id=mapping_id, proposed_record=dict(concept_id=cid, target_type='control', target_id=target, encoding='json', mapping=dict(field='effort_weight', value=record['params']['fixed_set_member']['code']), representation_strategy=representation_strategy(target), loss='low', provider=None, model_version=None, sources=record['source']), **common))
        batch = dict(batch_id='batch_fixed_set_admission', retrieval=dict(adapter='local_fixture', corpus_id='synthetic-glossary', query='weight selection', tool='local_extract', parameters={}, retrieved_at='2026-10-04T00:00:00Z'), extractor=dict(agent='fixture-worker', model='fixture-model', prompt_hash='sha256:' + 'e' * 64), candidates=candidates)
        run = ingest_distillation_batch(batch, self.root)
        assignments = {d['proposal_id']: d['suggested_id'] for d in run['candidate_decisions'] if d['proposal_id']}
        self.assertEqual(len(assignments), 6, [(d['candidate_id'], d['disposition'], d['reasons']) for d in run['candidate_decisions']])
        plan = plan_graph_growth(run['id'], assignments, self.root)
        self.assertTrue(plan['promotion_ready'], plan)
        return run, assignments

    def snapshot(self):
        return {p: p.read_bytes() for p in [self.root / 'lab/concepts.jsonl', *sorted((self.root / 'lab/second_brain/curated').glob('*'))] if p.is_file()}

    def review(self, manifest=None):
        return {**_review(), 'fixed_set_manifests': [copy.deepcopy(manifest or self.manifest)]}

    def test_public_promotion_commits_cards_and_inventory_in_one_transaction(self):
        run, ids = self.stage()
        args = dict(run_id=run['id'], durable_ids=ids, promoted_by='fixture-curator', review=self.review())
        auth = dict(schema='cpcs.explicit_authorization/1.0', authorization_id='auth_fixed_fixture', operation='cpcs.curate.promote', request_hash=authorization_request_hash('cpcs.curate.promote', args), authorized_by='fixture-owner', reason='Approve the complete synthetic weight set for this test.')
        response = invoke(dict(schema=REQUEST_SCHEMA, operation='cpcs.curate.promote', arguments=args, authorization=auth), role='curator', root=self.root)
        self.assertEqual(response['status'], 'success', response.get('error'))
        result = response['result']
        self.assertEqual(set(result['promoted_ids']), set(ids.values()))
        catalog = read_catalog(self.root)
        self.assertEqual(set(catalog), {'laban.effort.weight'})
        self.assertEqual({m['term'] for m in catalog['laban.effort.weight']['members']}, {'light', 'strong'})
        self.assertEqual(read_jsonl(self.coverage), [self.manifest])
        for card in read_jsonl(self.root / 'lab/concepts.jsonl')[1:]:
            self.assertTrue(card['provenance']['source_evidence'][0]['source_unit_id'])
            self.assertIn('ontology_placement', card['provenance']['validation'])
        validate_curated(self.root)
        receipt = result['transaction']
        self.assertEqual(receipt['state'], 'committed')
        self.assertIn('lab/second_brain/curated/domain_coverage_manifests.jsonl', [r['path'] for r in json.loads((self.root / receipt['receipt'] / 'manifest.json').read_text())['targets']])


    def test_world_reference_frame_preserves_supported_grounding_context(self):
        card = copy.deepcopy(self.cards[0])
        member = card['params']['fixed_set_member']
        member.update(set_id='bartenieff.connectivity', code='bartenieff.connectivity.upper-lower',
                      term='upper-lower', frame_of_reference='world',
                      definition='Lower-body support from the floor powers upper-body movement.')
        validate_instance('concept', card, self.root)

    def test_missing_companion_cannot_leave_orphan_cards(self):
        run, ids = self.stage()
        before = self.snapshot()
        with self.assertRaisesRegex(ValidationFailure, 'REGISTRY_GAP'):
            promote_distillation_bundle(run['id'], ids, 'fixture-curator', _review(), self.root)
        self.assertEqual(self.snapshot(), before)

    def test_invalid_companion_is_refused_without_authority_changes(self):
        run, ids = self.stage()
        before = self.snapshot()
        for change in ('outside_bundle', 'missing_member', 'non_fixed_inventory', 'duplicate_inventory'):
            with self.subTest(change=change):
                review = self.review()
                manifest = review['fixed_set_manifests'][0]
                if change == 'outside_bundle':
                    manifest['expected_ids'][0] = 'c_anchor'
                    manifest['fixed_set']['members'][0]['concept_id'] = 'c_anchor'
                elif change == 'missing_member':
                    manifest['expected_ids'].pop()
                    manifest['fixed_set']['members'].pop()
                elif change == 'non_fixed_inventory':
                    manifest.pop('fixed_set')
                else:
                    review['fixed_set_manifests'].append(copy.deepcopy(manifest))
                with self.assertRaises(ValidationFailure):
                    promote_distillation_bundle(run['id'], ids, 'fixture-curator', review, self.root)
                self.assertEqual(self.snapshot(), before)

    def test_stale_member_source_hash_rolls_back_both_stores(self):
        run, ids = self.stage(stale_hash=True)
        before = self.snapshot()
        with self.assertRaisesRegex(ValidationFailure, 'source hash'):
            promote_distillation_bundle(run['id'], ids, 'fixture-curator', self.review(), self.root)
        self.assertEqual(self.snapshot(), before)

    def test_public_authorization_binds_companion_bytes(self):
        run, ids = self.stage()
        args = dict(run_id=run['id'], durable_ids=ids, promoted_by='fixture-curator', review=self.review())
        auth = dict(schema='cpcs.explicit_authorization/1.0', authorization_id='auth_fixed_fixture', operation='cpcs.curate.promote', request_hash=authorization_request_hash('cpcs.curate.promote', args), authorized_by='fixture-owner', reason='Approve the synthetic weight set.')
        args['review']['fixed_set_manifests'][0]['inventory_name'] = 'Changed after authorization'
        before = self.snapshot()
        response = invoke(dict(schema=REQUEST_SCHEMA, operation='cpcs.curate.promote', arguments=args, authorization=auth), role='curator', root=self.root)
        self.assertEqual(response['status'], 'error')
        self.assertIn('bound to this exact request', response['error']['message'])
        self.assertEqual(self.snapshot(), before)
