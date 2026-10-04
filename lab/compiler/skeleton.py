"""Typed, field-bound labelled direction. No source-file or oracle dependency."""
from __future__ import annotations
import math,re
from decimal import Decimal
from typing import Any
from lab.second_brain.src.validate import REPO_ROOT, sha256_value
from lab.second_brain.src.fixed_sets import is_selection, selected_members

LABELS=('GOAL','MOTION PRIORITY','STYLE','LOOK','PACE','CAST','WORLD','PHYSICS','ANCHORS','RULES','PHRASES','BEAT','TACTIC','RANGE','CAM','DO','WHY','ANSWER','READ','REACT','BODY','EFFORT','SHAPE','SPACE','CONTACT','PROP','FACE','END','SOUND','AVOID')
COLLECTIONS=('scenes','entities','beats','actions','interactions','shots')
FORMS={'plain','title','upper','seconds','word','distance','gripped','held','lodged','placed','held_singular'}
ROW_KEYS={'ref','label','indent','gap','breaks','continuation_indents','blank_after'}

def _number(value):
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('INVALID_BOUND_NUMBER')
    return format(Decimal(str(value)).normalize(),'f')
def _word(value):
    # English integer spelling is lexical serialization, not a scientific vocabulary.
    names=('zero','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen')
    if type(value) is not int or value<0:raise ValueError('INVALID_COUNT')
    return names[value] if value<len(names) else str(value)
def _distance(value):
    if not isinstance(value,dict) or type(value.get('amount')) not in (int,float) or not math.isfinite(value['amount']) or value['amount']<=0:raise ValueError('RANGE_INVALID')
    n=value['amount'];unit=value.get('unit');form=value.get('form')
    units={'arm_length':("arm's length",'arm-lengths','an'),'leg_length':('leg-length','leg-lengths','a'),'rail_length':('rail-length','rail-lengths','a'),'stride':('stride','strides','a'),'finger_width':('finger-width','finger-widths','a')}
    if unit not in units:raise ValueError('RANGE_UNIT_UNKNOWN')
    singular,plural,article=units[unit]
    if n!=1:return (_word(n) if type(n) is int else _number(n))+' '+plural
    return ('a full ' if form=='full' else article+' ' if form=='article' else 'one ' if form=='count' else '')+singular

def validate_scene(scene, *, root=REPO_ROOT):
    from .decisions import movement_checks
    movement_errors, _ = movement_checks(scene, root=root)
    if movement_errors:raise ValueError("; ".join(e["code"]+": "+e["message"] for e in movement_errors))
    if not any('direction' in s for s in scene.get('scenes',[])):return
    beats=sorted(scene['beats'],key=lambda b:b['order'])
    if [b['order'] for b in beats]!=list(range(1,len(beats)+1)):raise ValueError('BEAT_ORDER')
    lengths=[]
    for b in beats:
        v=b.get('duration_s')
        if type(v) not in (int,float) or not math.isfinite(v) or v<=0 or v<b.get('min_s',v):raise ValueError('DURATION_INVALID')
        lengths.append(Decimal(str(v)))
        for relation in b.get('range_relations',[]):_distance(relation)
    if sum(lengths)!=Decimal(str(scene['scenes'][0]['duration_s'])):raise ValueError('DURATION_TOTAL')
    for shot in scene.get('shots',[]):
        for field,disposition in shot.get('source_dispositions',{}).items():
            if field not in {'framing','angle','movement','lens','focus'} or disposition!='source_unspecified' or shot.get(field) is not None:
                raise ValueError('SOURCE_UNSPECIFIED_CAMERA_CONFLICT')
    for collection in COLLECTIONS:
        for item in scene.get(collection,[]):
            for label,segments in item.get('direction',{}).items():
                if label not in LABELS or not isinstance(segments,list):raise ValueError('DIRECTION_FIELD')
                for node in segments:
                    if set(node)=={'text'} and isinstance(node['text'],str):continue
                    if set(node)=={'ref','form'} and isinstance(node['ref'],str) and node['form'] in FORMS:continue
                    raise ValueError('DIRECTION_BINDING')
    from .decisions import prop_hand_ledger
    errors,ledger=prop_hand_ledger(scene)
    if errors:raise ValueError('; '.join(e['code'] for e in errors))
    groups={c:{i['id']:i for i in scene.get(c,[])} for c in COLLECTIONS}
    for collection in COLLECTIONS:
        for item in scene.get(collection,[]):
            for nodes in item.get('direction',{}).values():
                for node in nodes:
                    if 'ref' not in node:continue
                    bits=node['ref'].split('.')
                    try:
                        value=ledger[bits[1]][bits[2]] if bits[0]=='ledger' else groups[bits[0]][bits[1]]
                        for bit in bits[3:] if bits[0]=='ledger' else bits[2:]:
                            value=value[int(bit)] if isinstance(value,list) else value[bit]
                    except (KeyError,IndexError,ValueError,TypeError) as exc:raise ValueError('BOUND_REFERENCE: '+node['ref']) from exc
    recipe=scene['scenes'][0].get('skeleton_recipe')
    if recipe is not None:
        if not isinstance(recipe,dict) or set(recipe)!={'version','rows'} or recipe['version']!='labelled_skeleton_v1' or not isinstance(recipe['rows'],list):raise ValueError('RECIPE_TEXT_OR_SHAPE')
        for row in recipe['rows']:
            if set(row)!=ROW_KEYS or row['label'] not in LABELS or not re.fullmatch(r'(scenes|entities|beats|actions|interactions|shots)\.[A-Za-z0-9_]+\.direction\.[A-Z ]+',row['ref']):raise ValueError('RECIPE_TEXT_OR_REFERENCE')
            if any(type(row[k]) is not int or row[k]<0 for k in ('indent','gap','blank_after')):raise ValueError('RECIPE_SPACING')
            for key in ('breaks','continuation_indents'):
                if not isinstance(row[key],list) or any(type(v) is not int or v<0 for v in row[key]):raise ValueError('RECIPE_WRAPS')
            if row['breaks']!=sorted(set(row['breaks'])) or len(row['breaks'])!=len(row['continuation_indents']):raise ValueError('RECIPE_WRAPS')

def project(scene, *, root=REPO_ROOT):
    from .decisions import prop_hand_ledger
    validate_scene(scene, root=root)
    members=selected_members(scene,root)
    errors,ledger=prop_hand_ledger(scene)
    if errors:raise ValueError('; '.join(e['code'] for e in errors))
    groups={c:{next(i[k] for k in ('id','entity_id','scene_id','beat_id','action_id','interaction_id','shot_id') if k in i):i for i in scene.get(c,[])} for c in COLLECTIONS}
    root_scene=scene['scenes'][0]
    def resolve(path):
        bits=path.split('.')
        if bits[0]=='ledger':v=ledger[bits[1]][bits[2]];bits=bits[3:]
        else:v=groups[bits[0]][bits[1]];bits=bits[2:]
        for bit in bits:v=v[int(bit)] if isinstance(v,list) else v[bit]
        return v
    def render(node):
        if 'layout' in node:return node['layout'],'layout'
        if 'text' in node:return node['text'],'authored_clause'
        try:v=resolve(node['ref'])
        except (KeyError,IndexError,ValueError) as exc:raise ValueError('BOUND_REFERENCE: '+node['ref']) from exc
        form=node['form']
        if is_selection(v):
            if form not in ('plain','title','upper'):raise ValueError('CLOSED_CODE_FORM')
            text=members[sha256_value(v)]['visible_wording']
            if form=='upper':text=text.upper()
            elif form=='title':text=text[:1].upper()+text[1:]
            return text,'closed_code'
        if form=='seconds':return _number(v)+'s','typed_bound'
        if form=='word':return _word(v),'typed_bound'
        if form=='distance':return _distance(v),'typed_bound'
        if form in ('gripped','held','lodged','placed','held_singular'):
            obj=node['ref'].split('.')[2];name=groups['entities'][obj]['name']
            if form=='gripped':text=name+' '+v['state']
            elif form=='held':text=name+((' '+v['state']) if v['state']!='whole' else '')+' in '+groups['entities'][v['held_by']]['name']+"'s hands"
            elif form=='lodged':text=name+' tip stuck '+v['location']+', '+groups['entities'][v['held_by']]['name']+' still holding the other end'
            elif form=='held_singular':text=name+' in '+groups['entities'][v['held_by']]['name']+"'s hand"
            else:text=name+' '+v['location']
            return text,'typed_bound'
        if not isinstance(v,(str,int,float)):raise ValueError('BOUND_VALUE_NOT_SCALAR')
        text=_number(v) if type(v) in (int,float) else v
        if form=='upper':return text.upper(),'typed_bound'
        return (text[:1].upper()+text[1:] if form=='title' else text),'typed_bound'
    rows=root_scene.get('skeleton_recipe',{}).get('rows')
    if rows is None:
        rows=[]
        def add(path,label,indent=0,blank=0):rows.append(dict(ref=path,label=label,indent=indent,gap=max(1,(11 if indent else 10)-indent-len(label)),breaks=[],continuation_indents=[],blank_after=blank))
        for label in LABELS:
            if label in root_scene.get('direction',{}) and label not in ('END','SOUND','AVOID'):add(f"scenes.{root_scene['id']}.direction.{label}",label,blank=1)
        for beat in sorted(scene['beats'],key=lambda b:b['order']):
            # Default heading uses typed values; no hand-made presentation recipe.
            heading=[dict(ref=f"beats.{beat['id']}.order",form='plain'),dict(layout=' ('),dict(ref=f"beats.{beat['id']}.duration_s",form='seconds'),dict(layout=') '),dict(ref=f"beats.{beat['id']}.role",form='plain')]
            groups['beats'][beat['id']]={**beat,'direction':{**beat.get('direction',{}),'BEAT':heading}}
            add(f"beats.{beat['id']}.direction.BEAT",'BEAT');rows[-1]['gap']=1
            fields=[label for label in LABELS if label in beat.get('direction',{}) and label!='BEAT']
            for index,label in enumerate(fields):add(f"beats.{beat['id']}.direction.{label}",label,2,1 if index==len(fields)-1 else 0)
        for label in ('END','SOUND','AVOID'):
            if label in root_scene.get('direction',{}):add(f"scenes.{root_scene['id']}.direction.{label}",label)
    closed_bytes=0
    output=[];counts=dict(typed_bound=0,authored_clause=0,layout=0);field_audit=[];omissions=[]
    explicit_omissions={o['ref']:o for c in COLLECTIONS for item in scene.get(c,[]) for o in item.get('direction_omissions',[])}
    protected={'GOAL','CAST','WORLD','BEAT','DO','CONTACT','PROP','END','RANGE'}
    if any(o['ref'].split('.')[-1] in protected for o in explicit_omissions.values()):raise ValueError('PROTECTED_DIRECTION_FIELD')
    omissions=list(explicit_omissions.values())
    for omission in omissions:
        try:resolve(omission['ref'])
        except (KeyError,IndexError):continue
        raise ValueError('OMITTED_FIELD_STILL_PRESENT')
    for row in rows:
        try:nodes=resolve(row['ref'])
        except (KeyError,IndexError):
            if row['ref'] not in explicit_omissions:raise ValueError('MISSING_DIRECTION_DECISION: '+row['ref'])
            continue
        rendered=[render(node) for node in nodes];text=''.join(v for v,_ in rendered)
        origins=[kind for value,kind in rendered for _ in value]
        content_kinds={'typed_bound' if kind=='closed_code' else kind for _,kind in rendered if kind!='layout'}
        field_audit.append(dict(ref=row['ref'],kind='fully_bound' if content_kinds=={'typed_bound'} else 'authored_only' if content_kinds=={'authored_clause'} else 'partly_bound'))
        words=list(re.finditer(r'\S+',text));cuts=[words[n].start() for n in row['breaks'] if n<len(words)]
        if not row['breaks'] and 'skeleton_recipe' not in root_scene:
            # Default wraps at sentence boundaries, with no invented width budget.
            cuts=[m.end() for m in re.finditer(r'(?<=\.) ',text)]
        lines=[];start=0
        for cut in [*cuts,len(text)]:
            line=text[start:cut].rstrip() if cut!=len(text) else text[start:cut]
            lines.append(line)
            for ix,char in enumerate(line,start):
                kind=origins[ix]
                size=len(char.encode('utf-8'))
                if kind=='closed_code':
                    closed_bytes+=size;counts['typed_bound']+=size
                elif kind!='layout':counts[kind]+=size
            start=cut
        prefix=' '*row['indent']+row['label']+' '*row['gap']
        printed=prefix+lines[0]
        for ix,line in enumerate(lines[1:]):printed+='\n'+' '*(row['continuation_indents'][ix] if ix<len(row['continuation_indents']) else len(prefix))+line
        printed+='\n'+'\n'*row['blank_after'];output.append(printed)
    result=''.join(output)
    # Only retained text contributes to content counts. Consumed spaces have no
    # emitted byte; replacement whitespace and builder punctuation are layout.
    substantive=counts['typed_bound']+counts['authored_clause'];counts['layout']=len(result.encode())-substantive
    if counts['layout']<0:raise ValueError('LAYOUT_BYTE_ACCOUNTING')
    clock=Decimal(0);timing=[]
    for beat in sorted(scene['beats'],key=lambda b:b['order']):
        end=clock+Decimal(str(beat['duration_s']))
        timing.append(dict(beat=beat['id'],duration_s=beat['duration_s'],start_s=float(clock),end_s=float(end)));clock=end
    camera_dispositions=[dict(shot=shot['id'],field=field,disposition=disposition) for shot in scene.get('shots',[]) for field,disposition in shot.get('source_dispositions',{}).items()]
    audit=dict(layout='labelled_skeleton_v1',byte_counts=counts,fields=field_audit,authored_bindings=root_scene.get('authored_bindings',[]),camera_dispositions=camera_dispositions,beat_timing=dict(kind='carrier_choice',provider_adherence_claim=False,beats=timing),source=root_scene.get('wording_source'))
    if members:audit['closed_code']=dict(bytes=closed_bytes,kind='subset_of_typed_bound',members=sorted(m['code'] for m in members.values()),model_efficacy_claim=False)
    return result,audit,omissions
