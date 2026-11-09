#!/usr/bin/env python3
"""Materialize exact per-event group overlays over an explicit source base plan.

No runtime/game input is changed. Event source fields supply array order and star
arguments. Ordinary race entry overlays its current state; only original special
source ID e3demo resets at the recovered entry window. Full exit-script scheduling
is not guessed. Original Q13 reflection is reused, not replaced with a rotation.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from gameplay_activation_recovery import bhash
from scenery_transform_reference import apply_source
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256

FIELD='0xe244f26b'
GAMEPLAY_SHA='7ac98113d931cd90c68dbdb8e6ba94c643eef85a9af076a5f2e71ac4072d9ab6'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def supported(event):
    fields=event['fields']
    if fields.get('0x0f6bcde1',{}).get('value') not in ('p2p','circuit') or fields['NumLaps']['value']<=0:return False
    checkpoints=event.get('ordered_checkpoint_refs',{}).get('nodes',[])
    start=event.get('startgrid_ref',{}).get('nodes',[]);finish=event.get('finishline_ref',{}).get('nodes',[])
    return bool(checkpoints and len(start)==len(finish)==1 and all(n['status']=='resolved' for n in (*checkpoints,*start,*finish))
        and {'Position','Rotation'}<=start[0].get('spatial_fields',{}).keys())


def event_operations(event,groups):
    field=event['fields'].get(FIELD)
    if not field:return [],None
    value=field['value']
    if field['type']!='EA::Reflection::Text' or value['count']!=len(value['values']) or value['count']>value['capacity']:
        raise ValueError('Malformed original event group array')
    result=[]
    for literal in value['values']:
        if not isinstance(literal,str) or not literal:raise ValueError('Invalid original group literal')
        star=literal.startswith('*');name=literal[1:] if star else literal;key=f'{bhash(name):08x}'
        if not name or key not in groups:raise ValueError('Unresolved source group')
        group=groups[key]
        result.append({'literal':literal,'group_name':name,'group_hash':key,'group_id':group['id'],
            'original_state_argument':int(star),'member_count':len(group['member_indices'])})
    return result,field


def load_sources(base,activation,stream):
    if base['summary']['source_sha256']['gameplay']!=GAMEPLAY_SHA or activation['summary']['source_sha256']['gameplay']!=GAMEPLAY_SHA:
        raise ValueError('Unexpected base/group gameplay source')
    groups={g['hash']:g for g in activation['groups']};members=activation['member_records'];records={}
    with stream.open('rb') as f:
        for row in base['instances']:
            at=row['source_instance_offset'];f.seek(at);raw=f.read(64)
            if len(raw)!=64 or sha(raw)!=row['source_instance_sha256']:raise ValueError('Original instance source differs')
            old=struct.unpack_from('<I',raw,24)[0]
            if old!=row['original_flags'] or old&65535!=members[row['member_index']]['initial_flags']:
                raise ValueError('Source/member initial flags differ')
            if at in records:raise ValueError('Duplicate source occurrence')
            records[at]=(row,raw)
    if len(records)!=sum(len(m['stream_instance_candidates']) for m in members):raise ValueError('Incomplete source coverage')
    return groups,members,records


def materialize(event,base,groups,members,records):
    flags=[m['initial_flags'] for m in members];active=set();states={}
    def apply(operation):
        group=groups[operation['group_hash']];argument=operation['original_state_argument']
        if argument not in (0,1):raise ValueError('Unexpected state argument')
        for index in group['member_indices']:flags[index]=(flags[index]&0xfbef)|(0x400 if argument else 0)
        active.add(group['id'])
        # Original setter overwrites the state byte with1, then adds bits2/4.
        extra=(group['unknown_tail_word']>>8)&255  # Unswapped byte at record+17.
        states[group['id']]=1|(2 if argument else 0)|(4 if extra else 0)
    for operation in base['summary']['operations']:apply(operation)
    # Validate explicit base against the materialized source fields before overlay.
    for row,raw in records.values():
        if flags[row['member_index']]!=(row['effective_flags']&65535):raise ValueError('Base plan does not match original operations')
    operations,provenance=event_operations(event,groups)
    special_reset=event['fields'].get('0xa78403ec',{}).get('value')=='e3demo'
    if special_reset:
        for group in groups.values():
            if group['id'] in active:
                for index in group['member_indices']:flags[index]|=0x10
        active.clear();states.clear();apply({'group_hash':f'{bhash("SCENERY_GROUP_DOOR"):08x}','original_state_argument':0})
    for operation in operations:apply(operation)
    overrides=[];reflections=[];counts=Counter()
    for offset,(row,raw) in sorted(records.items()):
        low=flags[row['member_index']];new=apply_source(raw,low);effective=struct.unpack_from('<I',new,24)[0]
        if raw!=new:
            overrides.append({'source_instance_offset':offset,'expected_source_flags':row['original_flags'],'effective_flags':effective})
        reflected=bool(row['original_flags']&0x00800000 and (row['original_flags']^effective)&0x400)
        if reflected:
            reflections.append({'source_instance_offset':offset,'q13_first_row':list(struct.unpack_from('<3h',new,44)),
                'effective_instance_sha256':sha(new)})
        if row['barrier_model']:
            counts['barriers_active' if not effective&16 else 'barriers_suppressed']+=1
        counts['source_occurrences']+=1
    return {'schema':1,'event_key':event['key'],'event_name':event['name'],
        'source_id':event['fields'].get('0xa78403ec',{}).get('value',''),
        'base_bin_index':base['summary']['bin_index'],'base_operations':base['summary']['operations'],
        'race_entry_special_reset':special_reset,'event_operations':operations,
        'event_group_field_provenance':provenance,'active_group_ids':sorted(active),
        'active_group_states':[{'group_id':i,'state_byte':states[i]} for i in sorted(active)],
        'group_zero_always_admitted':True,'normal_draw_context_flags':16,
        'overrides':overrides,'transform_mutation_count':len(reflections),'reflections':reflections,
        'counts':dict(counts),'overrides_sha256':sha(json.dumps(overrides,sort_keys=True,separators=(',',':')).encode())}


class EventLoopReference:
    """Original event apply loop; only its attribute getters/external refresh supplied."""
    def __init__(self,raw):
        from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
        from unicorn import ppc_const as r
        if sha(raw)!=DOL_SHA256:raise ValueError('Unexpected USA DOL')
        self.im=DolImage(raw);self.r=r;self.u=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        self.u.mem_map(0x80000000,0x1800000)
        for s in self.im.sections:self.u.mem_write(s.address,raw[s.offset:s.offset+s.size])
        self.ops=[];self.calls=[];self.done=False
        def code(u,pc,size,_):
            if pc==0x817ffffc:self.done=True;u.emu_stop();return
            if pc in (0x801a61c0,0x801a87b8,0x801a8864,0x801fe9ac,0x802ee62c,0x802f97e8):
                a=u.reg_read(r.UC_PPC_REG_3);index=u.reg_read(r.UC_PPC_REG_4)
                if pc in (0x801a61c0,0x801a87b8,0x801a8864):
                    if a!=0x81602000:raise ValueError('Wrong event receiver')
                    if pc==0x801a61c0:u.reg_write(r.UC_PPC_REG_3,len(self.ops))
                    else:
                        if index>=len(self.ops):raise ValueError('Original array index out of range')
                        value=0x81610000+index*128 if pc==0x801a87b8 else self.ops[index]['original_state_argument']
                        u.reg_write(r.UC_PPC_REG_3,value)
                elif pc==0x801fe9ac:
                    text=self.read_string(a)
                    self.calls.append(['apply',text,index])
                else:self.calls.append(['refresh',f'{pc:08x}'])
                u.reg_write(r.UC_PPC_REG_PC,u.reg_read(r.UC_PPC_REG_LR));return
            if not 0x8019f2dc<=pc<0x8019f36c:raise ValueError(f'Execution escaped event loop {pc:08x}')
        def write(u,access,address,size,value,_):
            if not (0x816fffc0<=address and address+size<=0x81700010):raise ValueError('Unexpected original write')
        self.u.hook_add(UC_HOOK_CODE,code);self.u.hook_add(UC_HOOK_MEM_WRITE,write)
    def read_string(self,at):
        raw=bytes(self.u.mem_read(at,128));return raw[:raw.index(0)].decode('ascii')
    def apply(self,operations,present=True):
        self.ops=operations;self.calls=[];self.done=False;u=self.u;r=self.r
        for i,o in enumerate(operations):
            text=o['group_name'].encode('ascii')+b'\0'
            if len(text)>128:raise ValueError('Test source name too long')
            u.mem_write(0x81610000+i*128,text)
        u.mem_write(0x81601aac,struct.pack('>I',0x81602000 if present else 0))
        u.reg_write(r.UC_PPC_REG_1,0x81700000);u.reg_write(r.UC_PPC_REG_3,0x81600000);u.reg_write(r.UC_PPC_REG_LR,0x817ffffc)
        u.emu_start(0x8019f2dc,0x817ffffc,count=100000,timeout=1000000)
        # Unicorn may stop at its end address without invoking the hook.
        if u.reg_read(r.UC_PPC_REG_PC)!=0x817ffffc:raise ValueError('Original event loop budget exhausted')
        expected=[['apply',o['group_name'],o['original_state_argument']] for o in operations]+[['refresh','802ee62c'],['refresh','802f97e8']] if present else []
        if self.calls!=expected:raise AssertionError((self.calls,expected))
        return self.calls


class EntryPrefixReference:
    """Original local reset condition; event getter/reset/apply supplied explicitly."""
    def __init__(self,raw):
        from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
        from unicorn import ppc_const as r
        self.im=DolImage(raw);self.r=r;self.u=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        self.u.mem_map(0x80000000,0x1800000)
        for s in self.im.sections:self.u.mem_write(s.address,raw[s.offset:s.offset+s.size])
        self.calls=[];self.done=False
        def code(u,pc,size,_):
            if pc==0x801c4a48:self.done=True;u.emu_stop();return
            if pc in (0x801a5158,0x801feb00,0x8019f2dc):
                if pc==0x801a5158:
                    if u.reg_read(r.UC_PPC_REG_3)!=0x81602000:raise ValueError('Unexpected event receiver')
                    u.reg_write(r.UC_PPC_REG_3,0x81604000)
                elif pc==0x801feb00:self.calls.append('reset')
                else:
                    if u.reg_read(r.UC_PPC_REG_3)!=0x81600000:raise ValueError('Unexpected apply manager')
                    self.calls.append('apply_event')
                u.reg_write(r.UC_PPC_REG_PC,u.reg_read(r.UC_PPC_REG_LR));return
            if not any(a<=pc<b for a,b in ((0x801c4a04,0x801c4a48),(0x80063034,0x80063098))):
                raise ValueError('Original race entry escaped bounded window')
        def write(*args):raise ValueError('Unexpected original entry-prefix write')
        self.u.hook_add(UC_HOOK_CODE,code);self.u.hook_add(UC_HOOK_MEM_WRITE,write)
    def enter(self,source_id):
        u=self.u;r=self.r;self.calls=[];self.done=False
        text=source_id.encode('ascii')+b'\0'
        if len(text)>256:raise ValueError('Source ID too long')
        u.mem_write(0x8041d30c,struct.pack('>I',0x81600000));u.mem_write(0x81601aac,struct.pack('>I',0x81602000));u.mem_write(0x81604000,text)
        u.reg_write(r.UC_PPC_REG_28,0x80420000)
        u.emu_start(0x801c4a04,0x817ffffc,count=2000,timeout=100000)
        if not self.done:raise ValueError('Original entry-prefix budget exhausted')
        expected=(['reset'] if source_id=='e3demo' else [])+['apply_event']
        if self.calls!=expected:raise AssertionError((source_id,self.calls,expected))
        return self.calls


def export(catalog,activation,dol,stream,base,output,selected=None,verify=False):
    if sha(dol)!=DOL_SHA256:raise ValueError('Unexpected USA DOL')
    if catalog['summary']['source_sha256']['gameplay']!=GAMEPLAY_SHA:raise ValueError('Unexpected source catalog')
    groups,members,records=load_sources(base,activation,stream)
    reference=EventLoopReference(dol) if verify else None
    entry_reference=EntryPrefixReference(dol) if verify else None
    events=[e for e in catalog['race_definition_candidates'] if supported(e)]
    if selected:events=[e for e in events if selected in (e['key'],e['name'])]
    if not events:raise ValueError('No supported event matched')
    output.mkdir(parents=True,exist_ok=True);rows=[];cases=0;entry_cases=0
    for event in events:
        result=materialize(event,base,groups,members,records)
        if reference:reference.apply(result['event_operations']);cases+=1
        if entry_reference:entry_reference.enter(result['source_id']);entry_cases+=1
        path=output/(event['key']+'.json')
        path.write_text(json.dumps(result,indent=2)+'\n')
        rows.append({'event_key':event['key'],'event_name':event['name'],'path':path.name,
            'event_group_operations':len(result['event_operations']),
            'star_operations':sum(o['original_state_argument'] for o in result['event_operations']),
            'active_groups':len(result['active_group_ids']),'overrides':len(result['overrides']),
            'transform_mutations':result['transform_mutation_count'],'counts':result['counts'],
            'plan_sha256':sha(path.read_bytes())})
    if reference:
        reference.apply([],False);reference.apply([],True);cases+=2
        for value in ('e3demo','E3DEMO','','e3demo '):entry_reference.enter(value);entry_cases+=1
    im=DolImage(dol)
    if im.c_string(0x803eeae8)!='e3demo' or im.c_string(0x803ede6c)!='DisableBarriers':raise ValueError('Original lifecycle literals differ')
    summary={'schema':1,'source_sha256':catalog['summary']['source_sha256'],
        'base_bin_index':base['summary']['bin_index'],'plans':len(rows),
        'original_event_loop_cases':cases,'original_entry_prefix_cases':entry_cases,'event_plans':rows,
        'consumer_evidence':{'current_event':'manager+1aac','event_apply_loop':'8019f2dc',
            'source_group_field':'e244f26b','count_getter':'801a61c0','name_getter':'801a87b8','star_getter':'801a8864',
            'race_entry_apply_call':'801c4a44','special_reset_source_id':'e3demo',
            'special_reset_window':'801c4a04..801c4a48','DisableBarriers_registration':'803ede68 ->8019f36c',
            'DisableBarriers_reset':'801feb00 ->802bd50c +SCENERY_GROUP_DOOR0',
            'code_windows':[{'start':f'{a:08x}','end_exclusive':f'{b:08x}','sha256':sha(im.read(a,b-a))} for a,b in
                [(0x8019f2dc,0x8019f36c),(0x801a61c0,0x801a621c),(0x801a87b8,0x801a8918),(0x801c4a04,0x801c4a48),(0x8019f36c,0x8019f3a8)]]},
        'limits':['Exact source-array overlays on an explicitly selected cold base state',
            'Ordinary source race entry does not unconditionally reset all groups; special e3demo does',
            'External attribute getters and collision refresh are explicitly supplied in the bounded event-loop reference',
            'Exit script ordering and replaying the career base after DisableBarriers remain lifecycle integration work',
            'Reflection uses separately original-execution-verified Q13 consumer; no geometry deletion or invented180degree rotation',
            'No native racing, countdown/opponents, trigger detection, frame publication, SDK build or runtime changes are claimed']}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('catalog','groups','dol','stream','base-plan','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--event');p.add_argument('--verify-original',action='store_true')
    a=p.parse_args();r=export(json.loads(a.catalog.read_text()),json.loads(a.groups.read_text()),a.dol.read_bytes(),a.stream,
        json.loads(a.base_plan.read_text()),a.output,a.event,a.verify_original)
    print(json.dumps({'plans':r['plans'],'base_bin':r['base_bin_index'],'original_event_loop_cases':r['original_event_loop_cases'],
        'star_operations':sum(e['star_operations'] for e in r['event_plans']),
        'transform_mutations':sum(e['transform_mutations'] for e in r['event_plans'])}))
