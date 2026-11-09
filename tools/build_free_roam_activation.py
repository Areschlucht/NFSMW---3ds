#!/usr/bin/env python3
"""Materialize an original cold-start free-roam scenery flag plan privately.

The cold loader initializes the active-group array to zero. Reset only visits
active groups; it does NOT mark every imported member inactive. Preserve source
member flags, then apply the original reset default (DOOR) and the selected bin.
No collision ownership, unlocked career, or matrix mutation is invented.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
from career_region_gates import collect
from gameplay_activation_recovery import bhash
from vehicle_dol import DolImage


def sha(raw):return hashlib.sha256(raw).hexdigest()


def build(catalog,activation,dol,stream,scene,bin_index):
    plans=collect(catalog,activation,dol,stream)
    matches=[p for p in plans['plans'] if p['bin_index']==bin_index]
    if len(matches)!=1:raise ValueError('Missing/duplicate source bin')
    plan=matches[0];groups={g['hash']:g for g in activation['groups']}
    members=activation['member_records'];initial=[m['initial_flags'] for m in members];flags=list(initial)
    ownership={}
    for group in groups.values():
        for index in group['member_indices']:
            if index in ownership:raise ValueError('Member belongs to multiple source groups')
            ownership[index]=group
    if len(ownership)!=len(members):raise ValueError('Not every source member has group ownership')
    operations=[{'group_hash':f'{bhash("SCENERY_GROUP_DOOR"):08x}',
                 'group_name':'SCENERY_GROUP_DOOR','original_state_argument':0},*plan['operations']]
    applied=[]
    for operation in operations:
        key=operation['group_hash'];argument=operation['original_state_argument']
        if argument not in (0,1) or key not in groups:raise ValueError('Invalid/unresolved source operation')
        group=groups[key]
        for index in group['member_indices']:flags[index]=(flags[index]&0xfbef)|(0x400 if argument else 0)
        applied.append({'group_hash':key,'group_id':group['id'],'group_name':operation['group_name'],
                        'original_state_argument':argument,'member_count':len(group['member_indices'])})
    manifest=json.loads((scene/'manifest.json').read_text())
    barrier_keys={r['hash'] for r in manifest['models'].values() if r['name'].startswith('XO_TRACKBARRIER')}
    scene_instances={}
    for section in manifest['sections']:
        raw=(scene/section['path']).read_bytes()
        if sha(raw)!=section['sha256']:raise ValueError('Scene section differs from manifest')
        count,offset=struct.unpack_from('<I',raw,24)[0],struct.unpack_from('<I',raw,36)[0]
        for i in range(count):
            record=raw[offset+i*144:offset+(i+1)*144]
            source=struct.unpack_from('<I',record)[0]
            slots=[f'{k:08x}' for k in struct.unpack_from('<4I',record,8+64+24)]
            info={'section':section['id'],'slots':slots,'barrier_model':any(k in barrier_keys for k in slots)}
            scene_instances.setdefault(source,[]).append(info)
    records=[];counts=Counter();transforms=[]
    with stream.open('rb') as f:
        for member in members:
            index=member['index'];group=ownership[index]
            for candidate in member['stream_instance_candidates']:
                offset=candidate['source_instance_offset'];f.seek(offset);raw=f.read(64)
                if len(raw)!=64 or sha(raw)!=candidate['instance_bytes_sha256']:raise ValueError('Original source instance mismatch')
                old=struct.unpack_from('<I',raw,24)[0]
                if old&65535!=initial[index]:raise ValueError('Cold source/member flag mismatch')
                new=(old&0xffff0000)|flags[index]
                required=bool(old&0x00800000 and (old^new)&0x400)
                if required:transforms.append(offset)
                if offset not in scene_instances:raise ValueError('Mapped source instance absent from scene')
                info=scene_instances[offset]
                barrier=any(x['barrier_model'] for x in info)
                original_rejected=bool(((old&255)^0x60)&0x10)
                rejected=bool(((new&255)^0x60)&0x10)
                record={'source_instance_offset':offset,'member_index':index,'group_id':group['id'],
                    'group_hash':group['hash'],'group_names':group['candidate_names'],
                    'original_flags':old,'effective_flags':new,'source_instance_sha256':sha(raw),
                    'source_translation':list(struct.unpack_from('<3f',raw,32)),
                    'barrier_model':barrier,'normal_draw_suppressed':rejected,
                    'transform_required':required,'scene_occurrences':info}
                records.append(record);counts['source_occurrences']+=1
                counts['barrier_occurrences']+=barrier
                counts['barriers_suppressed']+=barrier and rejected
                counts['barriers_retained']+=barrier and not rejected
                counts['flags_changed']+=old!=new
                counts['newly_visible']+=original_rejected and not rejected
                counts['nonbarrier_flags_changed']+=(old!=new and not barrier)
    records.sort(key=lambda r:r['source_instance_offset'])
    if len({r['source_instance_offset'] for r in records})!=len(records):raise ValueError('Duplicate source offset')
    overrides=[{'source_instance_offset':r['source_instance_offset'],'expected_source_flags':r['original_flags'],
                'effective_flags':r['effective_flags']} for r in records if r['original_flags']!=r['effective_flags']]
    if transforms:raise ValueError(f'Plan needs unported transform mutations: {transforms[:8]}')
    summary={'schema':1,'bin_index':bin_index,'source_sha256':plans['source_sha256'],
        'normal_draw_context_flags':0x10,'cold_active_groups':[],
        'active_group_ids':sorted({operation['group_id'] for operation in applied}),
        'group_zero_always_admitted':True,
        'operations':applied,'counts':dict(counts),'transform_mutation_count':len(transforms),
        'override_count':len(overrides),'overrides_sha256':sha(json.dumps(overrides,sort_keys=True,separators=(',',':')).encode()),
        'limits':['Cold source group-state plan, not a recovered career progression scheduler',
            'Initial source/member low flags match for every mapped occurrence',
            'Cold reset visits no active groups; a warm replacement must reset the prior active-group set',
            'No 0x400 transform transitions occur in this selected source plan',
            'Normal render mask0x10 is distinct from CI group ownership; collision group admission uses active_group_ids',
            f'Selected bin{bin_index} is explicit source state; this does not fabricate saved career progression',
            'Per-instance original geometry/flags are not removed by model-name matching']}
    return {'summary':summary,'overrides':overrides,'instances':records}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('catalog','groups','dol','stream','scene','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--bin',type=int,default=15);p.add_argument('--summary',type=Path)
    p.add_argument('--verify-original',action='store_true')
    a=p.parse_args();r=build(json.loads(a.catalog.read_text()),json.loads(a.groups.read_text()),a.dol.read_bytes(),a.stream,a.scene,a.bin)
    if a.verify_original:
        from scenery_flag_reference import Reference
        original=Reference(a.dol.read_bytes());pairs=sorted({(i['original_flags'],i['effective_flags']) for i in r['instances']})
        for old,new in pairs:
            outcome,actual=original.apply(old,new&65535)
            if outcome!='copied' or actual!=new:raise AssertionError('Original instance flag copy differs')
            if original.render(new,16)!=bool(((new&255)^0x60)&16):raise AssertionError('Original render gate differs')
        r['summary']['original_unique_flag_cases_verified']=len(pairs)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    if a.summary:a.summary.write_text(json.dumps(r['summary'],indent=2)+'\n')
    print(json.dumps(r['summary']))
