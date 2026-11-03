#!/usr/bin/env python3
"""Export original race routes and typed story links without inventing game rules.

The catalog is source data, not playable races or a complete career interpreter.
Only original typed arrays establish route ordering; collection-name numbering
and folder-child order are not substituted for those arrays.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct

from gameplay_packages import GameplayPackages, dol_labels
from vehicle_attributes import VehicleAttributes
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
from vehicle_vlt_hash import vlt_hash

# Associations observed by resolving source GCollectionKey values to named nodes.
# Human-readable original field names and full consumers remain unrecovered.
ROUTE_FIELDS={'0x34aae3fc':'ordered_checkpoint_refs',
              '0xe43b2ccc':'startgrid_ref','0xb0a24adc':'finishline_ref'}
LINK_FIELD='0x64273c71'
SPATIAL_FIELDS=('Position','Rotation','Radius','0x6d9e21ad')
LABEL_CANDIDATES={'Checkpoint':'34aae3fc','Children':'916e0e78',
                  'IntroMovie':'f572ede8','OutroMovie':'b70268c0','BossRaces':'d5a174aa',
                  'Dimensions':'6d9e21ad','RequiredBounty':'d3657d92',
                  'RequiredRacesWon':'d617fedc','RequiredChallenges':'6dd4b98b'}


def compact(field):
    return {k:field[k] for k in ('field_key','field_name','type','value',
        'source_collection','source_sha256','file_offset','original_bytes')}


def keys(field):
    if field['type']!='GCollectionKey':
        raise ValueError('Expected original GCollectionKey field')
    value=field['value']
    items=value['values'] if 'values' in value else [value]
    if 'count' in value and value['count']!=len(items):
        raise ValueError('Typed collection array count mismatch')
    raw=bytes.fromhex(field['original_bytes'])
    if 'values' in value:
        if len(raw)<8:raise ValueError('Short original key array')
        capacity,count,size,flags=struct.unpack_from('>4H',raw)
        if size!=4 or count!=len(items) or count>capacity or len(raw)!=8+capacity*4:
            raise ValueError('Original key-array source differs from typed decoder')
        original=list(struct.unpack_from('>'+str(count)+'I',raw,8))
    else:
        if len(raw)!=4:raise ValueError('Short original collection key')
        original=[struct.unpack('>I',raw)[0]]
    for item,source_key in zip(items,original):
        if item.get('type')!='GCollectionKey' or not re.fullmatch('[0-9a-f]{8}',item.get('raw_hex','')):
            raise ValueError('Unsupported collection-key representation')
        key=int(item['raw_hex'],16)
        if key!=source_key:raise ValueError('Typed key differs from original big-endian source bytes')
        yield key


def export(gameplay,attributes,dol):
    if hashlib.sha256(dol).hexdigest()!=DOL_SHA256:
        raise ValueError('Unexpected USA executable')
    labels=dol_labels(dol)
    base=VehicleAttributes(attributes,labels=labels)
    gp=GameplayPackages(gameplay,base,labels)
    rows={}
    for package,db in gp.databases.items():
        for (_,key),row in db.collections.items():
            if key in rows:raise ValueError('Ambiguous cross-class collection key')
            rows[key]={'key':f'{key:08x}','name':db.label(key),'package':package,
                       'parent_key':f'{row["parent"]:08x}','fields':db.fields(row)}
    unresolved=set();resolved=0;nulls=0
    def reference(key,spatial=False):
        nonlocal resolved,nulls
        if key==0:
            nulls+=1
            return {'key':'00000000','status':'null'}
        if key not in rows:
            unresolved.add(key)
            return {'key':f'{key:08x}','status':'unresolved'}
        resolved+=1;target=rows[key]
        ref={k:target[k] for k in ('key','name','package')}
        ref['status']='resolved'
        if spatial:
            ref['spatial_fields']={n:compact(target['fields'][n]) for n in SPATIAL_FIELDS if n in target['fields']}
        return ref
    candidates=[];story=[];graph=[];bin_nodes=[];checkpoint_count=0
    for key,row in rows.items():
        fields=row['fields'];refs={}
        for name,field in fields.items():
            if field['type']=='GCollectionKey':
                refs[name]={'field_provenance':compact(field),
                            'targets':[reference(k) for k in keys(field)]}
        graph.append({k:row[k] for k in ('key','name','package','parent_key')}|{'reference_fields':refs})
        if re.fullmatch('race_bin_[0-9]{2}',row['name']):
            bin_nodes.append({k:row[k] for k in ('key','name','package','parent_key')}|
                {'fields':{n:compact(f) for n,f in fields.items()},'reference_fields':refs})
        movies=[{'field':n,'source':compact(f),'movie_stem':f['value']} for n,f in fields.items()
                if f['type']=='EA::Reflection::Text' and isinstance(f['value'],str)
                and f['value'].lower().startswith('storyfmv_')]
        if movies:story.append({k:row[k] for k in ('key','name','package')}|{'movie_fields':movies,'reference_fields':refs})
        if 'NumLaps' not in fields:continue
        candidate={k:row[k] for k in ('key','name','package','parent_key')}
        candidate['fields']={n:compact(f) for n,f in fields.items()}
        candidate['reference_fields']=refs
        for field,association in ROUTE_FIELDS.items():
            if field not in fields:continue
            candidate[association]={'field_hash':field,'source':compact(fields[field]),
                'nodes':[reference(k,spatial=True) for k in keys(fields[field])]}
            if field=='0x34aae3fc':checkpoint_count+=len(candidate[association]['nodes'])
        if LINK_FIELD in fields:
            candidate['linked_event_field']={'field_hash':LINK_FIELD,'source':compact(fields[LINK_FIELD]),
                'targets':[reference(k) for k in keys(fields[LINK_FIELD])]}
        candidates.append(candidate)
    image=DolImage(dol)
    if any(f'{vlt_hash(label):08x}'!=key for label,key in LABEL_CANDIDATES.items()):
        raise ValueError('Candidate field-label hash mismatch')
    xrefs=image.constant_xrefs([int(k,16) for k in set((*ROUTE_FIELDS,LINK_FIELD,
        '0xf572ede8','0xb70268c0',*LABEL_CANDIDATES.values()))])
    xrefs=[{k:f'{v:08x}' if k!='register' else v for k,v in r.items()} for r in xrefs]
    summary={'schema':1,'source_sha256':{'gameplay':gp.sha256,'attributes':base.sha256,'dol':DOL_SHA256},
        'definitions_with_numlaps':len(candidates),
        'definitions_with_checkpoint_array':sum('ordered_checkpoint_refs' in r for r in candidates),
        'ordered_checkpoint_references':checkpoint_count,'story_bearing_definitions':len(story),
        'race_bin_definitions':len(bin_nodes),'typed_key_reference_observations_resolved':resolved,
        'candidate_field_labels':LABEL_CANDIDATES,
        'null_key_observations':nulls,'unresolved_nonzero_keys':sorted(f'{k:08x}' for k in unresolved),
        'field_constant_xrefs':xrefs,
        'limits':['Definitions include templates and challenges; counts are not playable race counts',
            'Route associations resolve source names; full field consumer semantics remain a separate gate',
            'Race types, checkpoint trigger dimensions/direction/units and progression thresholds are not guessed',
            'Linked-event field is preserved without assigning success/failure/unlock transition meaning',
            'Original positions/rotations are unchanged, not converted to a guessed physics coordinate frame',
            'Story movie strings are references, not proof of decoder/runtime playback or trigger order']}
    return {'summary':summary,'race_definition_candidates':candidates,'story_definitions':story,
            'bin_definitions':bin_nodes,'typed_reference_graph':graph}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('gameplay','attributes','dol','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--summary',type=Path)
    a=p.parse_args();r=export(a.gameplay.read_bytes(),a.attributes.read_bytes(),a.dol.read_bytes())
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    if a.summary:a.summary.write_text(json.dumps(r['summary'],indent=2)+'\n')
    print(json.dumps({k:v for k,v in r['summary'].items() if k not in ('field_constant_xrefs','limits','source_sha256')}))
