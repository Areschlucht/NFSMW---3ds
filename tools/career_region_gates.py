#!/usr/bin/env python3
"""Export exact source career-bin scenery-group plans, not invented district rules.

No source game data or runtime is modified. A bin plan is a sequence of original
name/state arguments; group names do not turn bit0x400 into a visibility Boolean.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from gameplay_activation_recovery import bhash
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
from vehicle_vlt_hash import vlt_hash

GAMEPLAY_SHA='7ac98113d931cd90c68dbdb8e6ba94c643eef85a9af076a5f2e71ac4072d9ab6'
GROUP_FIELD='0xe244f26b'
BIN_FIELD='0x6ce23062'


def digest(raw):return hashlib.sha256(raw).hexdigest()


def collect(catalog,activation,dol,stream=None):
    if digest(dol)!=DOL_SHA256:raise ValueError('Unexpected USA executable')
    if catalog['summary']['source_sha256']['gameplay']!=GAMEPLAY_SHA:
        raise ValueError('Unexpected source gameplay catalog')
    if activation['summary']['source_sha256']['gameplay']!=GAMEPLAY_SHA:
        raise ValueError('Activation catalog source differs')
    if vlt_hash('BinIndex')!=int(BIN_FIELD[2:],16):raise ValueError('Unexpected BinIndex hash')
    image=DolImage(dol)
    if struct.unpack('>2I',image.read(0x803ede7c,8))!=(0xffff,0x8019ddfc):
        raise ValueError('EnableBinBarriers callback registration differs')
    if image.c_string(0x803ede84)!='EnableBinBarriers':
        raise ValueError('Unexpected original callback name')
    if image.c_string(0x803f57c0)!='SCENERY_GROUP_DOOR':
        raise ValueError('Unexpected reset default group')
    by_hash={g['hash']:g for g in activation['groups']}
    if len(by_hash)!=len(activation['groups']):raise ValueError('Duplicate group hash')
    members=activation['member_records'];plans=[];bins=set();used={}
    for row in catalog['bin_definitions']:
        field=row['fields'][BIN_FIELD];index=field['value']
        if not isinstance(index,int) or index not in range(1,17) or index in bins:
            raise ValueError('Invalid/duplicate original BinIndex')
        if bytes.fromhex(field['original_bytes'])!=struct.pack('>I',index):
            raise ValueError('BinIndex differs from original typed bytes')
        bins.add(index);source=row['fields'].get(GROUP_FIELD)
        values=[]
        if source is not None:
            array=source['value']
            if source['type']!='EA::Reflection::Text' or array['count']!=len(array['values']) or array['count']>array['capacity']:
                raise ValueError('Malformed source group text array')
            values=array['values']
        operations=[]
        for literal in values:
            if not isinstance(literal,str) or not literal:raise ValueError('Empty/nontext group')
            name=literal[1:] if literal.startswith('*') else literal
            key=f'{bhash(name):08x}'
            if key not in by_hash:raise ValueError('Unresolved source group')
            group=by_hash[key]
            operations.append({'literal':literal,'group_name':name,'group_hash':key,
                'original_state_argument':int(literal.startswith('*')),
                'group_id':group['id'],'member_count':len(group['member_indices'])})
            used[key]=group
        plans.append({'bin_index':index,'collection_key':row['key'],'collection_name':row['name'],
            'bin_index_source':field,'group_field_present':source is not None,
            'group_field_source':source,'operations':operations})
    if bins!=set(range(1,17)):raise ValueError('Incomplete source bin set')
    plans.sort(key=lambda r:r['bin_index'],reverse=True)
    regions=[]
    with stream.open('rb') if stream else _NullFile() as f:
        for key,group in sorted(used.items()):
            records=[];positions=[]
            for member_id in group['member_indices']:
                if not 0<=member_id<len(members):raise ValueError('Out-of-range group member')
                member=members[member_id]
                if member['index']!=member_id:raise ValueError('Member table ordering differs')
                instances=[]
                for candidate in member.get('stream_instance_candidates',[]):
                    instance=dict(candidate)
                    if stream:
                        f.seek(candidate['source_instance_offset']);raw=f.read(64)
                        if len(raw)!=64 or digest(raw)!=candidate['instance_bytes_sha256']:
                            raise ValueError('Mapped source instance differs')
                        position=list(struct.unpack_from('<3f',raw,32))
                        if not all(math.isfinite(x) for x in position):raise ValueError('Nonfinite source placement')
                        instance['source_translation']=position;positions.append(position)
                    instances.append(instance)
                records.append({'member_index':member_id,'scenery_section':member['scenery_section'],
                    'instance_index':member['instance_index'],'initial_flags':member['initial_flags'],
                    'source_instances':instances})
            region={'group_hash':key,'group_id':group['id'],'candidate_names':group['candidate_names'],
                    'source_record_offset':group['source_record_offset'],'members':records}
            if positions:region['source_translation_envelope']={
                'minimum':[min(p[i] for p in positions) for i in range(3)],
                'maximum':[max(p[i] for p in positions) for i in range(3)]}
            regions.append(region)
    transitions=[]
    for previous,current in zip(plans,plans[1:]):
        old={o['group_hash']:o for o in previous['operations']};new={o['group_hash']:o for o in current['operations']}
        if {(k,o['original_state_argument']) for k,o in old.items()}=={(k,o['original_state_argument']) for k,o in new.items()}:continue
        transitions.append({'from_bin':previous['bin_index'],'to_bin':current['bin_index'],
            'removed_names':sorted(old[k]['group_name'] for k in old.keys()-new.keys()),
            'added_names':sorted(new[k]['group_name'] for k in new.keys()-old.keys()),
            'retained_names':sorted(new[k]['group_name'] for k in old.keys()&new.keys())})
    windows=[(0x8019ddfc,0x8019de28),(0x8019de34,0x8019de84),
             (0x8019e1ec,0x8019e220),(0x801a43ec,0x801a445c),
             (0x801a9558,0x801a9598),(0x801a9960,0x801a9a20),
             (0x801feb00,0x801feb54),(0x801feabc,0x801feb00),(0x801fea44,0x801fea94)]
    return {'schema':1,'source_sha256':catalog['summary']['source_sha256'],
        'plans':plans,'referenced_groups':regions,'plan_change_boundaries':transitions,
        'consumer_evidence':{
            'EnableBinBarriers_registered_callback':'8019ddfc','current_bin_object':'manager+1ab0',
            'bin_setter':'8019de34','global_reset':'801a99e4 -> 801feb00',
            'reset_group_flags':'801feabc -> 802bd50c','reset_default_group':'SCENERY_GROUP_DOOR (argument0)',
            'bin_lookup':'801a43ec','bin_index_getter':'801a9558','bin_index_field':'6ce23062',
            'group_apply_loop':'801a9960','profile_bin_source':'profile+ec (update path8019e204..8019e218)',
            'update_preconditions':'manager+1aa4 == 0 and manager+1ae4 != 0',
            'code_windows':[{'start':f'{a:08x}','end_exclusive':f'{b:08x}','sha256':digest(image.read(a,b-a))} for a,b in windows]},
        'limits':['Exact per-bin group plans, not a new career interpreter or playable lock implementation',
            'Global reset precedes replacement application; empty new plans do not mean retaining old active groups',
            'EnableBinBarriers alone reapplies the current plan; it is distinct from replacing the bin',
            'Bit0x400 can mutate transforms and is not labelled visibility; original state arguments are preserved',
            'Geographic district names are not proved from these coordinates/group names',
            'Profile byte producers, win progression, collision ownership and event reset ordering remain further integration gates',
            'Original arrays and source instances remain private; no SDK build or runtime edits']}


class _NullFile:
    def __enter__(self):return None
    def __exit__(self,*args):return False


class BinSetterReference:
    """Original prefix, with only its three external callees supplied as stubs."""
    def __init__(self,raw):
        from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
        from unicorn import ppc_const as r
        if digest(raw)!=DOL_SHA256:raise ValueError('Unexpected USA executable')
        self.image=DolImage(raw);self.r=r;self.u=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        self.u.mem_map(0x80000000,0x1800000)
        for s in self.image.sections:self.u.mem_write(s.address,raw[s.offset:s.offset+s.size])
        self.operations=[];self.done=False;self.new=0
        def code(u,pc,size,_):
            if pc in (0x8019de7c,0x8019dea4):self.done=True;u.emu_stop()
            elif pc in (0x801a99e4,0x801a43ec,0x801a9960):
                a=u.reg_read(r.UC_PPC_REG_3)
                if pc==0x801a99e4:self.operations.append(['reset',a])
                elif pc==0x801a43ec:
                    if a!=0x81602000:raise ValueError('Unexpected bin database receiver')
                    self.operations.append(['lookup',u.reg_read(r.UC_PPC_REG_4)])
                    u.reg_write(r.UC_PPC_REG_3,self.new)
                else:self.operations.append(['apply',a])
                u.reg_write(r.UC_PPC_REG_PC,u.reg_read(r.UC_PPC_REG_LR))
            elif not 0x8019de34<=pc<0x8019de7c:raise ValueError(f'Execution escaped prefix: {pc:08x}')
        def write(u,access,address,size,value,_):
            if not ((0x81600000+0x1ab0==address and size==4) or (0x816fffc0<=address and address+size<=0x81700010)):
                raise ValueError('Unexpected original prefix write')
        self.u.hook_add(UC_HOOK_CODE,code);self.u.hook_add(UC_HOOK_MEM_WRITE,write)
    def replace(self,old,target,new):
        u=self.u;r=self.r;self.done=False;self.operations=[];self.new=new
        u.reg_write(r.UC_PPC_REG_1,0x81700000);u.reg_write(r.UC_PPC_REG_3,0x81600000);u.reg_write(r.UC_PPC_REG_4,target)
        u.mem_write(0x81601ab0,struct.pack('>I',old));u.mem_write(0x8041d318,struct.pack('>I',0x81602000))
        u.emu_start(0x8019de34,0x817ffffc,count=1000,timeout=100000)
        if not self.done:raise ValueError('Original prefix budget exhausted')
        actual=struct.unpack('>I',bytes(u.mem_read(0x81601ab0,4)))[0]
        return self.operations,actual


def verify_setter(raw):
    original=BinSetterReference(raw);cases=0
    for old in (0,0x81601000):
        for target in (0,*range(1,17),17,255):
            new=0x81603000+target*32 if 1<=target<=16 else 0
            expected=([['reset',old]] if old else [])+[['lookup',target]]+([['apply',new]] if new else [])
            actual,stored=original.replace(old,target,new)
            if actual!=expected or stored!=new:raise AssertionError((old,target,actual,expected,stored,new))
            cases+=1
    return {'original_bin_setter_prefix_cases':cases,
        'limits':['Original prefix only; reset/lookup/apply callees stubbed explicitly',
                  'No full manager scheduler, profile win progression or collision execution claimed']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('catalog','groups','dol','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--stream',type=Path);p.add_argument('--verify-original',action='store_true')
    a=p.parse_args();dol=a.dol.read_bytes();r=collect(json.loads(a.catalog.read_text()),json.loads(a.groups.read_text()),dol,a.stream)
    if a.verify_original:r['verification']=verify_setter(dol)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'plans':len(r['plans']),'groups':len(r['referenced_groups']),
        'member_records':sum(len(g['members']) for g in r['referenced_groups']),
        'plan_change_boundaries':r['plan_change_boundaries'],'verification':r.get('verification')}))
