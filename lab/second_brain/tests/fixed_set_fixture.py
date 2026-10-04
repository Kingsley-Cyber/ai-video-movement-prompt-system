"""Synthetic, source-admitted vocabulary for software tests only."""
from pathlib import Path
from lab.second_brain.tests.helpers import concept, write_rows
from lab.second_brain.tests.test_source_registry import _complete_no_candidate_session
from lab.second_brain.src.source_registry import load_source_units
from lab.second_brain.src.validate import read_jsonl

# Membership and recipes are the owner's Round 2 table, not a production registry.
SETS = {
 'laban.effort.weight': ['light','strong'],
 'laban.effort.time': ['sustained','sudden'],
 'laban.effort.space': ['indirect','direct'],
 'laban.effort.flow': ['free','bound'],
 'laban.effort.action': ['punch','slash','dab','flick','press','wring','glide','float'],
 'laban.shape.quality': ['rising','sinking','spreading','enclosing','advancing','retreating'],
 'bartenieff.connectivity': ['breath','core-distal','head-tail','upper-lower','body-half','cross-lateral'],
 'motion.spacing': ['even','ease_in','ease_out','ease_in_out'],
 'motion.initiation_chain.kind': ['simultaneous','successive','sequential'],
}
RECIPES = {
 'punch':('strong','sudden','direct'),'slash':('strong','sudden','indirect'),
 'dab':('light','sudden','direct'),'flick':('light','sudden','indirect'),
 'press':('strong','sustained','direct'),'wring':('strong','sustained','indirect'),
 'glide':('light','sustained','direct'),'float':('light','sustained','indirect'),
}

def empty_inventory(root):
    """Keep synthetic/absent-catalog tests independent of real admitted members."""
    path = root / 'lab/concepts.jsonl'
    original = read_jsonl(path)
    removed = {c['id'] for c in original if 'fixed_set_member' in c.get('params', {})}
    rows = [c for c in original if c['id'] not in removed]
    write_rows(path, rows)
    for name in ('edges', 'mappings'):
        store = root / 'lab/second_brain/curated' / (name + '.jsonl')
        if store.exists():
            write_rows(store, [r for r in read_jsonl(store)
                               if not removed.intersection({r.get('u'), r.get('v'), r.get('concept_id')})])
    coverage = root / 'lab/second_brain/curated/domain_coverage_manifests.jsonl'
    write_rows(coverage, [m for m in read_jsonl(coverage) if 'fixed_set' not in m])

def install(root):
    empty_inventory(root)
    source=root/'work'/'fixed-fixture-source';source.mkdir(parents=True,exist_ok=True)
    text='Synthetic movement glossary, not render evidence. '+ ' '.join(
        f'{set_id}.{term} means fixture {term} movement.' for set_id,terms in SETS.items() for term in terms)
    (source/'members.md').write_text(text)
    _complete_no_candidate_session(root,source)
    unit=next(u for u in load_source_units(root) if 'Synthetic movement glossary' in u['storage'].get('passage',''))
    rows=read_jsonl(root/'lab/concepts.jsonl');manifests=read_jsonl(root/'lab/second_brain/curated/domain_coverage_manifests.jsonl')
    for set_id,terms in SETS.items():
        authority='project_convention' if set_id.startswith('motion.') else 'external_standard'
        members=[]
        for term in terms:
            code=set_id+'.'+term;cid='c_fixture_'+code.replace('.','_').replace('-','_')
            word={'light':'light body effort','strong':'firm body effort'}.get(term,term.replace('_',' ').replace('-',' ')+' movement')
            member=dict(set_id=set_id,version='1.0',code=code,term=term,definition='Fixture '+term+' movement.',visible_wording=word,
                conflicts=[],authority=authority,frame_of_reference='body',model_support='untested',evidence_status='unexplored',
                definition_source='research_summary',visible_wording_status='source_supplied',source_batch_sha256=unit['source_byte_hash'])
            if set_id=='laban.effort.action':member['recipe']={f:'laban.effort.'+f+'.'+v for f,v in zip(('weight','time','space'),RECIPES[term])}
            row=concept(cid,code,layer='whole-body movement',status='ingested')
            row.update(params={'fixed_set_member':member},source=[unit['source_ref']],provenance={'source_evidence':[dict(source_id=unit['source_ref'],locator=unit['locator'],claim=term+' movement definition',content_sha256=unit['content_sha256'])]})
            rows.append(row);members.append(dict(concept_id=cid,code=code))
        manifests.append(dict(schema='cpcs.domain_coverage_manifest/1.0',id='domain_inventory_fixture_'+set_id.replace('.','_'),domain='motion',
            inventory_name='Synthetic '+set_id,inventory_scope='complete_source_inventory',expected_ids=[m['concept_id'] for m in members],
            source_refs=[unit['source_ref']],completeness_claim='source_complete',fixed_set=dict(set_id=set_id,version='1.0',authority=authority,members=members)))
    write_rows(root/'lab/concepts.jsonl',rows)
    write_rows(root/'lab/second_brain/curated/domain_coverage_manifests.jsonl',manifests)
