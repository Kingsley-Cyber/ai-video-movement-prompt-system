"""Read closed selections from existing concept and coverage authorities."""
from __future__ import annotations
import copy
from pathlib import Path
from .authority import authority_reader
from .source_registry import load_source_units, _units_for_alias
from .validate import REPO_ROOT, ValidationFailure, read_jsonl, validate_instance, sha256_value

PERFORMANCE_SETS = {
    'effort_weight':'laban.effort.weight', 'effort_time':'laban.effort.time',
    'effort_space':'laban.effort.space', 'effort_flow':'laban.effort.flow',
    'shape':'laban.shape.quality', 'connectivity':'bartenieff.connectivity',
}
BODY_SETS = {'kind':'motion.initiation_chain.kind', 'pattern':'bartenieff.connectivity',
             'spacing':'motion.spacing', 'effort_action':'laban.effort.action'}
SELECTION_KEYS = {'fixed_set','version','code','member_hash'}

class RegistryGap(ValidationFailure):
    """A missing, incompatible or stale admitted member, never an invented value."""
    def __init__(self, reason, *, set_id='', code=''):
        self.gap={'set_id':set_id,'code':code,'reason':reason}
        super().__init__('REGISTRY_GAP: '+str(self.gap))

def is_selection(value):
    return isinstance(value,dict) and 'fixed_set' in value

@authority_reader('fixed_set_catalog')
def read_catalog(root: Path = REPO_ROOT):
    path=root/'lab/second_brain/curated/domain_coverage_manifests.jsonl'
    manifests=[m for m in read_jsonl(path) if 'fixed_set' in m] if path.exists() else []
    cards=read_jsonl(root/'lab/concepts.jsonl')
    fixed=[c for c in cards if 'fixed_set_member' in c.get('params',{})]
    if not manifests and not fixed:return {}
    units=load_source_units(root)
    unit_index={(u['source_ref'],u['locator'],u['content_sha256']):u for u in units}
    by_id={c['id']:c for c in cards};used=set();catalog={}
    for manifest in manifests:
        validate_instance('domain_coverage_manifest',manifest,root)
        spec=manifest['fixed_set'];set_id=spec['set_id']
        if set_id in catalog:raise RegistryGap('duplicate declared set',set_id=set_id)
        entries=spec['members'];ids=[e['concept_id'] for e in entries];codes=[e['code'] for e in entries]
        if len(ids)!=len(set(ids)) or len(codes)!=len(set(codes)) or set(ids)!=set(manifest['expected_ids']):
            raise RegistryGap('duplicate or mismatched membership',set_id=set_id)
        if manifest['inventory_scope']!='complete_source_inventory' or manifest['completeness_claim']!='source_complete':
            raise RegistryGap('membership is not a complete declared inventory',set_id=set_id)
        members=[]
        for entry in entries:
            card=by_id.get(entry['concept_id'])
            if card is None:raise RegistryGap('missing member',set_id=set_id,code=entry['code'])
            validate_instance('concept',card,root)
            member=card.get('params',{}).get('fixed_set_member')
            if member is None or any(member[k]!=spec[k] for k in ('set_id','version','authority')) or member['code']!=entry['code']:
                raise RegistryGap('member/manifest identity or version mismatch',set_id=set_id,code=entry['code'])
            if not member['code'].startswith(set_id+'.'):
                raise RegistryGap('member code lies outside its namespace',set_id=set_id,code=entry['code'])
            evidence=card.get('provenance',{}).get('source_evidence',[])
            if not evidence or any(not _units_for_alias(ref,units) for ref in card['source']):
                raise RegistryGap('missing exact source evidence',set_id=set_id,code=entry['code'])
            evidence_units=[]
            for item in evidence:
                unit=unit_index.get(tuple(item.get(k) for k in ('source_id','locator','content_sha256')))
                if unit is None or not item.get('claim') or unit['source_byte_hash']!=member['source_batch_sha256']:
                    raise RegistryGap('source hash or exact passage does not close',set_id=set_id,code=entry['code'])
                evidence_units.append(unit['id'])
            selection=dict(fixed_set=set_id,version=spec['version'],code=member['code'],member_hash=sha256_value(card))
            members.append({**copy.deepcopy(member),'concept_id':card['id'],'selection':selection,'source_unit_ids':sorted(set(evidence_units))})
            used.add(card['id'])
        catalog[set_id]={**copy.deepcopy(spec),'members':sorted(members,key=lambda m:m['code'])}
    if {c['id'] for c in fixed}-used:raise RegistryGap('member has no declared inventory')
    for spec in catalog.values():
        for member in spec['members']:
            for factor,code in member.get('recipe',{}).items():
                target=catalog.get('laban.effort.'+factor)
                if target is None or code not in {m['code'] for m in target['members']}:
                    raise RegistryGap('recipe references a missing factor member',set_id=member['set_id'],code=member['code'])
    return catalog

def _resolve(selection,catalog):
    if not is_selection(selection) or set(selection)!=SELECTION_KEYS or any(not isinstance(v,str) or not v for v in selection.values()):
        raise RegistryGap('closed selection requires exact code, version and member hash')
    spec=catalog.get(selection['fixed_set'])
    if spec is None or spec['version']!=selection['version']:
        raise RegistryGap('set or version is not admitted',set_id=selection['fixed_set'],code=selection['code'])
    member=next((m for m in spec['members'] if m['code']==selection['code']),None)
    if member is None:raise RegistryGap('code is not admitted',set_id=selection['fixed_set'],code=selection['code'])
    if member['selection']['member_hash']!=selection['member_hash']:
        raise RegistryGap('stale member hash',set_id=selection['fixed_set'],code=selection['code'])
    return member

def resolve_selection(selection,root: Path = REPO_ROOT):
    return _resolve(selection,read_catalog(root))

def selected_members(value,root: Path = REPO_ROOT):
    """Resolve one operation's selections from one read snapshot, not per token."""
    selections=[]
    def walk(v):
        if is_selection(v):selections.append(v)
        elif isinstance(v,dict):
            for x in v.values():walk(x)
        elif isinstance(v,list):
            for x in v:walk(x)
    walk(value)
    if not selections:return {}
    catalog=read_catalog(root)
    return {sha256_value(s):_resolve(s,catalog) for s in selections}

def slot_menus(root: Path = REPO_ROOT, *, actor_only=False):
    catalog=read_catalog(root)
    names=set(BODY_SETS.values()) if actor_only else set(PERFORMANCE_SETS.values())|set(BODY_SETS.values())
    menus={name:catalog[name] for name in sorted(names) if name in catalog}
    gaps=[dict(set_id=name,code='',reason='not_admitted') for name in sorted(names-set(catalog))]
    return menus,gaps
