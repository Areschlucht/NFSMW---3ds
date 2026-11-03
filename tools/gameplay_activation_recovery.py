#!/usr/bin/env python3
"""Read-only original scenery-group and gameplay-reference evidence export.

No runtime activation policy is inferred from names. Full original member tables
belong in private research output; use --summary for a compact authored checkpoint.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from gameplay_packages import GameplayPackages, dol_labels
from nfs_rockport import chunks, decode as decode_index
from vehicle_attributes import VehicleAttributes
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256

PREFIXES=('BARRIER_','BARRIERS_','PLAYER_BARRIERS_','SCENERY_GROUP_','FREE_ROAM')

def bhash(text):
    value=0xffffffff
    for c in text.encode('ascii'):value=(value*33+c)&0xffffffff
    return value

def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for v in value.values():yield from strings(v)
    elif isinstance(value,list):
        for v in value:yield from strings(v)

def source_groups(raw):
    leaves={k:(a,b) for k,a,b in chunks(raw)}
    a,b=leaves[0x34108]
    count=(b-a)//6
    if any(raw[a+count*6:b]):raise ValueError('Nonzero member-table padding')
    members=[{'index':i,'scenery_section':s,'instance_index':n,'initial_flags':f}
             for i,(s,n,f) in enumerate(struct.iter_unpack('<3H',raw[a:a+count*6]))]
    a,b=leaves[0x34109];groups=[];ids=set();keys=set()
    while a<b:
        if b-a<20:raise ValueError('Truncated group record')
        link0,link1,key,identifier,n,tail=struct.unpack_from('<IIIhhI',raw,a)
        end=a+((20+2*n+3)&~3)
        if n<0 or identifier<=0 or identifier>=4096 or identifier in ids or key in keys or end>b:
            raise ValueError('Invalid original group bounds/identity')
        indices=list(struct.unpack_from('<'+str(n)+'H',raw,a+20))
        if any(i>=count for i in indices):raise ValueError('Invalid group member index')
        ids.add(identifier);keys.add(key)
        groups.append({'hash':f'{key:08x}','id':identifier,'source_record_offset':a,
                       'unknown_link_words':[link0,link1],'unknown_tail_word':tail,
                       'member_indices':indices})
        a=end
    return groups,members

def instance_mapping(index,stream):
    """Map logical scenery numbers to exact original instance offsets.

    A stream directory entry can contain MULTIPLE scenery sections. Its directory
    ID is not interchangeable with each 34101 section number.
    """
    mapping={}
    with stream.open('rb') as f:
        for section in decode_index(index)['sections']:
            f.seek(section['offset']);raw=f.read(section['bytes'])
            if len(raw)!=section['bytes']:raise ValueError('Truncated stream section')
            for kind,a,b in chunks(raw):
                if kind!=0x80034100:continue
                parts={k:(a+x,a+y) for k,x,y in chunks(raw[a:b])}
                if 0x34103 not in parts:continue
                h,he=parts[0x34101]
                if he-h<16:raise ValueError('Truncated scenery header')
                logical=struct.unpack_from('<I',raw,h+12)[0]
                ia,ib=parts[0x34103];ia=(ia+15)&~15
                if (ib-ia)%64:raise ValueError('Malformed instance array')
                for i,at in enumerate(range(ia,ib,64)):
                    key=(logical,i)
                    mapping.setdefault(key,[]).append({'stream_directory_id':section['id'],
                                  'source_instance_offset':section['offset']+at,
                                  'instance_bytes_sha256':hashlib.sha256(raw[at:at+64]).hexdigest()})
    return mapping

def recover(gameplay,schema,index,dol,stream=None):
    if hashlib.sha256(dol).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected original DOL')
    image=DolImage(dol)
    expected=[(name,1 if name!='FREE_ROAM' else 0) for name in PREFIXES]
    actual=[]
    for i in range(5):
        address,flag=struct.unpack('>2I',image.read(0x8043707c+i*8,8))
        actual.append((image.c_string(address),flag))
    if actual!=expected:raise ValueError('Unexpected original classification table')
    groups,members=source_groups(index);byhash={g['hash']:g for g in groups}
    gp=GameplayPackages(gameplay,VehicleAttributes(schema),labels=dol_labels(dol))
    names={};refs=[]
    # StrE supplies literal candidates; original bHash is case-sensitive.
    for db in gp.databases.values():
        for labels in db.names.values():
            for name in labels:
                candidate=name.removeprefix('*');key=f'{bhash(candidate):08x}'
                if key in byhash:names.setdefault(key,set()).add(candidate)
    for package,db in gp.databases.items():
        for (_,key),row in db.collections.items():
            for field,value in db.fields(row).items():
                matching=sorted(set(s for s in strings(value['value']) if s.removeprefix('*').startswith(PREFIXES)))
                for text in matching:
                    name=text.removeprefix('*');hashed=f'{bhash(name):08x}'
                    refs.append({'package':package,'collection':db.label(key),'field':field,
                        'text':text,'leading_star_state':text.startswith('*'),'original_bhash':hashed,'matched_group':hashed in byhash,
                        'source_file_offset':value['file_offset'],'source_sha256':value['source_sha256']})
    mapping=instance_mapping(index,stream) if stream else {}
    for member in members:
        target=mapping.get((member['scenery_section'],member['instance_index']))
        if target:member['stream_instance_candidates']=target
    for group in groups:group['candidate_names']=sorted(names.get(group['hash'],set()))
    evidence={'classification_table_address':'8043707c','classifier':'802c117c',
        'classifier_caller':'801fe9ac','case_sensitive_hash_function':'80062ecc',
        'member_table_loader':'802bd5d4','member_index_resolver':'802bccc4',
        'group_table_loader':'802bd234','group_lookup':'802bd374',
        'gameplay_group_field_hash':'e244f26b','gameplay_apply_loop':'801a9960',
        'gameplay_group_name_accessor':'801a98a8','gameplay_leading_star_accessor':'801a9900',
        'group_state_setter':'802bd3a8','group_state_remover':'802bd48c',
        'instance_flag_application':'802bccd8',
        'set_formula':'member.flags = (member.flags & 0xfbef) | (arg != 0 ? 0x400 : 0)',
        'remove_formula':'member.flags |= 0x10',
        'application_formula':'instance.flags = (instance.flags & 0xffff0000) + member.flags',
        'limits':['Bit0x400 can trigger transform mutation; it is not merely a visibility bit.',
                  'Multiple loaded provider occurrences can share logical scenery/instance IDs; preserve all source candidates.',
                  'Bit0x10 downstream draw/collision semantics and complete event/career producers remain integration gates.',
                  'Hash/name matches identify source groups but do not justify enabling all BARRIER-named objects.',
                  'GameCube loading mutates linked-list words; preserved source values are not host pointers.']}
    summary={'schema':1,'source_sha256':{'gameplay':hashlib.sha256(gameplay).hexdigest(),
        'attributes':hashlib.sha256(schema).hexdigest(),'l2ra':hashlib.sha256(index).hexdigest(),'dol':DOL_SHA256},
        'groups':len(groups),'member_records':len(members),
        'group_memberships':sum(len(g['member_indices']) for g in groups),
        'groups_with_literal_name_candidates':len(names),
        'field_reference_count':len(refs),'field_reference_counts':dict(Counter(r['field'] for r in refs)),
        'logical_instances_mapped_to_stream':sum('stream_instance_candidates' in m for m in members),
        'members_with_multiple_stream_candidates':sum(len(m.get('stream_instance_candidates',[]))>1 for m in members),
        'classification_table':actual,'consumer_evidence':evidence,
        'group_examples':[{k:v for k,v in g.items() if k!='member_indices'}|
                          {'member_count':len(g['member_indices'])} for g in groups[:6]],
        'field_reference_examples':refs[:6]}
    return summary,{'summary':summary,'groups':groups,'member_records':members,'gameplay_references':refs}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('gameplay','attributes','index','dol','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--stream',type=Path);p.add_argument('--summary',type=Path)
    a=p.parse_args();s,r=recover(a.gameplay.read_bytes(),a.attributes.read_bytes(),a.index.read_bytes(),a.dol.read_bytes(),a.stream)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    if a.summary:a.summary.write_text(json.dumps(s,indent=2)+'\n')
    print(json.dumps({k:s[k] for k in ('groups','member_records','groups_with_literal_name_candidates','field_reference_count','logical_instances_mapped_to_stream')}))
