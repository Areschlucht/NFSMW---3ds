#!/usr/bin/env python3
"""Recover original CARPX NIS actor event timelines and source clock evidence.

Outputs exact hashes/names/raw command arguments; names are source DOL strings,
not inferred semantics. Does not claim full generic CARPX engine emulation.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from vehicle_dol import DolImage
from vehicle_vlt_hash import vlt_hash

DOL_SHA='33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166'

def decode(raw,dol):
    start=raw.find(b'CARPX')
    if start<0: raise ValueError('CARPX header missing')
    count=struct.unpack_from('>I',raw,start+8)[0]
    if count<2 or count>2048 or start+16*(count+1)>len(raw):raise ValueError('Invalid descriptor count')
    records={}
    for i in range(1,count+1):
        at=start+i*16;tag,packed,key,relative=struct.unpack_from('>4I',raw,at)
        size=packed&0xffffff;off=at+relative
        if packed>>24 not in (0x40,0xc0) or off>len(raw) or size>len(raw)-off:raise ValueError('CARPX record bounds')
        records[tag]=dict(tag=tag,key=key,offset=off,size=size,data=raw[off:off+size])
    sr=next(r for t,r in records.items() if t==0x53747273)
    strings=[x.decode('ascii') for x in sr['data'].split(b'\0') if x]
    names={vlt_hash(n):n for n in strings}
    # Event identifiers use the same Jenkins lookup2 hash as original801956E8.
    for row in dol.strings(minimum=2):
        if row['text'].startswith(('ENIS','ECamera','EDD','EAnim')):names[vlt_hash(row['text'])]=row['text']
    links={}
    for tag,r in records.items():
        if tag>>16!=0x656c:continue
        p=r['data'];n=struct.unpack_from('>I',p)[0]
        if n>128 or len(p)<16+n*16:raise ValueError('Event link count')
        commands=[]
        for i in range(n):
            at=16+i*16;key,size,rel,unknown=struct.unpack_from('>4I',p,at);off=at+rel
            if off+size>len(p) or size<4:raise ValueError('Event argument bounds')
            args=p[off:off+size]
            if struct.unpack_from('>I',args)[0]!=key:raise ValueError('Event key mismatch')
            words=list(struct.unpack('>'+str((len(args)-4)//4)+'I',args[4:])) if (len(args)-4)%4==0 else []
            commands.append(dict(command_hash=f'{key:08x}',command_name=names.get(key),argument_hex=args[4:].hex(),argument_words=[f'{x:08x}' for x in words]))
        links[tag]=commands
    actions=[]
    for tag,r in records.items():
        if tag>>16!=0x6541:continue
        p=r['data']
        if len(p)<16:raise ValueError('Short action')
        key,unknown,n,duration=struct.unpack_from('>IIIf',p)
        if n>2000 or unknown>128 or len(p)!=16+8*(n+unknown) or key!=r['key']:raise ValueError('Action timeline bounds/key')
        triggers=struct.unpack_from('>'+str(unknown)+'I',p,16)
        times=struct.unpack_from('>'+str(n)+'f',p,16+4*unknown);refs=struct.unpack_from('>'+str(n+unknown)+'I',p,16+4*(n+unknown))
        events=[]
        for t,ref in zip(times,refs[unknown:]):
            if ref not in links:raise ValueError('Missing event link')
            events.append(dict(time_seconds=t,link_tag=f'{ref:08x}',commands=links[ref]))
        actions.append(dict(name=names.get(key),name_hash=f'{key:08x}',duration_seconds=duration,trigger_events=[dict(trigger_hash=f'{h:08x}',trigger_name=names.get(h),commands=links[refs[i]]) for i,h in enumerate(triggers)],events=events))
    entities=[]
    for tag,r in records.items():
        if tag>>16!=0x6553:continue
        p=r['data'];initial,default,n=struct.unpack_from('>3I',p)
        if n>256 or len(p)!=12+8*n:raise ValueError('System states bounds')
        keys=struct.unpack_from('>'+str(n)+'I',p,12);refs=struct.unpack_from('>'+str(n)+'I',p,12+4*n)
        states=[]
        for key,ref in zip(keys,refs):
            state=records[ref];sp=state['data'];sn,filter_key=struct.unpack_from('>2I',sp)
            if sn>256 or len(sp)!=8+12*sn or key!=state['key']:raise ValueError('State stimuli bounds/key')
            stimuli=struct.unpack_from('>'+str(sn)+'I',sp,8)
            transitions=[]
            for i,stimulus in enumerate(stimuli):
                nxt,action=struct.unpack_from('>2I',sp,8+4*sn+8*i)
                transitions.append(dict(stimulus_hash=f'{stimulus:08x}',stimulus_name=names.get(stimulus),next_state_hash=f'{nxt:08x}',next_state_name=names.get(nxt),action_hash=f"{records[action]['key']:08x}" if action else None))
            states.append(dict(name=names.get(key),name_hash=f'{key:08x}',filter_hash=f'{filter_key:08x}',transitions=transitions))
        entities.append(dict(name=names.get(r['key']),name_hash=f"{r['key']:08x}",tag=f'{tag:08x}',initial_state_hash=f'{initial:08x}',default_state_hash=f'{default:08x}',states=states))
    scene_name=next((r['data'].split(b'\0',1)[0].decode('ascii') for tag,r in records.items() if tag>>16==0x694e),None)
    return dict(scene_name=scene_name,source_sha256=hashlib.sha256(raw).hexdigest(),carpx_offset=start,actions=actions,entities=entities)


def clock_evidence(dol):
    def value(address):return struct.unpack('>f',dol.read(address,4))[0]
    speed=value(0x803cfe0c);rate=value(0x803cfae0)
    if speed!=.5 or rate!=30:raise ValueError('Unverified source actor clock constants')
    return dict(controller='CAnimCtrl',setup_function='8004CC04 CreateCarAnimationControllers__10CAnimScene',speed_store='8004CD54 -> CAnimCtrl+60',speed=speed,advance_function='80047450 AdvanceAnimTime__9CAnimCtrlf',frame_rate_constant=rate,default_frames_per_input_second=speed*rate,sample_function='800476E4 UpdateAnimPose__9CAnimCtrlb',curve_sampler_input='CAnimCtrl+68 accumulated source frame',curve_conversion_context=False,source_slot_names=[f'ZPM_Car{i}' for i in range(1,9)]+[f'ZPM_Cop{i}' for i in range(1,9)],slot_registry='80457610: 16 entries,16bytes each; controller+0,actual vehicleinterface+4,lastpose+8,stateindex+C',registry_car_producer='801DFD04 EPlayRaceNIS constructor:801E02B8..0378 binds car1..8 in VEHICLE_RACERS(6) iteration order',registry_cop_producer='80284564 NISActivity::PrepareVehicles;cop1 registration8028469C..D0',remaining=['Racer intrusive-list order is not itself proof car1 is always local player','CARPX command argument words retained raw until original event constructors interpreted','Animation root placement belongs to CAnimScene source matrices; no arbitrary player-relative anchoring'])


def export_native(report,path):
    scenes=[];actions=[];systems=[];states=[];transitions=[];events=[];commands=[];args=bytearray()
    def name(v,n):
        raw=(v or '').encode('ascii')
        if len(raw)>=n:raise ValueError('Name too long')
        return raw+bytes(n-len(raw))
    source_by_name={s['scene_name']:s for s in report['scenes'].values()}
    for scene_name,metadata in report['scene_metadata'].items():
        src=source_by_name.get(scene_name,dict(scene_name=scene_name,actions=[],entities=[]))
        af=len(actions);sf=len(systems)
        action_map={a['name_hash']:af+i for i,a in enumerate(src['actions'])}
        for action in src['actions']:
            ef=len(events)
            for tagged,event_list in [(1,action['trigger_events']),(0,action['events'])]:
                for e in event_list:
                    cf=len(commands)
                    for command in e['commands']:
                        payload=bytes.fromhex(command['argument_hex']);commands.append((int(command['command_hash'],16),len(args),len(payload)));args.extend(payload)
                    key=int(e['trigger_hash'],16) if tagged else struct.unpack('<I',struct.pack('<f',e['time_seconds']))[0]
                    events.append((tagged,key,cf,len(commands)-cf))
            actions.append((name(action['name'],48),int(action['name_hash'],16),action['duration_seconds'],ef,len(events)-ef))
        for entity in src['entities']:
            stf=len(states)
            for state in entity['states']:
                tf=len(transitions)
                for t in state['transitions']:
                    transitions.append((int(t['stimulus_hash'],16),int(t['next_state_hash'],16),action_map[t['action_hash']] if t['action_hash'] else 0xffffffff))
                states.append((int(state['name_hash'],16),int(state['filter_hash'],16),tf,len(transitions)-tf))
            systems.append((name(entity['name'],32),int(entity['name_hash'],16),int(entity['initial_state_hash'],16),int(entity['default_state_hash'],16),stf,len(states)-stf,0,0,0))
        scenes.append((name(src['scene_name'],48),af,len(actions)-af,sf,len(systems)-sf,metadata['scene_type'],metadata['start_frame'],metadata['end_frame'],metadata['start_seconds'],metadata['total_seconds'],0,0,0))
    counts=[len(x) for x in (scenes,actions,systems,states,transitions,events,commands)]
    formats=['<48s5I2i2f3I','<48sIfII','<32s8I','<4I','<3I','<4I','<3I']
    tables=[b''.join(struct.pack(fmt,*r) for r in rows) for fmt,rows in zip(formats,(scenes,actions,systems,states,transitions,events,commands))]
    offsets=[];cursor=80
    for table in tables:offsets.append(cursor);cursor+=len(table)
    offsets.append(cursor)
    # Command payload offsets were relative to the arguments region.
    tables[-1]=b''.join(struct.pack('<3I',event,off+cursor,size) for event,off,size in commands)
    total=cursor+len(args)
    if total>2*1024*1024:raise ValueError('Native action asset budget exceeded')
    header=struct.pack('<4s18I',b'NAC1',1,*counts,*offsets,total,0)
    if len(header)!=76:raise ValueError('Header layout error')
    out=header+bytes(4)+b''.join(tables)+args;path.write_bytes(out)
    return dict(bytes=len(out),counts=counts,sha256=hashlib.sha256(out).hexdigest())


def verify_source_boundaries(dol_raw,report):
    from map_recovery_contact_reference import OriginalContactReference
    from unicorn.ppc_const import UC_PPC_REG_1,UC_PPC_REG_3,UC_PPC_REG_5,UC_PPC_REG_LR,UC_PPC_REG_PC
    class Ref(OriginalContactReference):
        def _hook(self,u,address,size,data):
            if address==0x801ecf6c:
                self.sent.append(u.reg_read(UC_PPC_REG_5))
                u.reg_write(UC_PPC_REG_PC,u.reg_read(UC_PPC_REG_LR));return
            super()._hook(u,address,size,data)
    ref=Ref(dol_raw,None);ref.extra_allowed=((0x801ed084,0x801ed1a0),(0x8003aa8c,0x8003aad8));u=ref.u;cases=0
    for src in report['scenes'].values():
        for action in src['actions']:
            times=[e['time_seconds'] for e in action['events']]
            n=len(times);tags=len(action['trigger_events'])
            raw=struct.pack('>3If',int(action['name_hash'],16),tags,n,action['duration_seconds'])+bytes(tags*4)+struct.pack('>'+str(n)+'f',*times)+bytes((tags+n)*4)
            u.mem_write(0x60001000,raw);u.mem_write(0x60000000,bytes(128));u.mem_write(0x6000000c,struct.pack('>I',0x60001000))
            intervals=[(-1.,0.),(0.,0.),(-1.,100.)]
            for t in times:intervals.extend([(-1.,t),(t,t),(t,t+.00001)])
            for previous,current in intervals:
                previous=struct.unpack('>f',struct.pack('>f',previous))[0];current=struct.unpack('>f',struct.pack('>f',current))[0]
                ref.sent=[];ref.putfloating(1,previous);ref.putfloating(2,current)
                for reg,val in [(UC_PPC_REG_1,0x7000ff00),(UC_PPC_REG_3,0x60000000),(UC_PPC_REG_LR,0x6000fff0)]:u.reg_write(reg,val)
                u.emu_start(0x801ed084,0x6000fff0,timeout=100000,count=100000)
                if u.reg_read(UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Original timed-event reference budget exceeded')
                expected=[i for i,t in enumerate(times) if previous<t<=current]
                if ref.sent!=expected:raise ValueError((src['scene_name'],action['name'],previous,current,ref.sent,expected))
                cases+=1
    return dict(original_function='801ED084 FireTimedEvents',cases=cases,exact_dispatch_indices=True,interval='(previous,current]',scope='Original dispatcher executes unchanged; only final event-list callback intercepted to capture source indices')


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('input',type=Path);a.add_argument('--dol',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--native',type=Path);a.add_argument('--scene-metadata',type=Path);a.add_argument('--verify-source',action='store_true');args=a.parse_args()
    raw=args.dol.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=DOL_SHA:raise ValueError('Original USA DOL revision required')
    dol=DolImage(raw);paths=sorted(args.input.glob('*.bin')) if args.input.is_dir() else [args.input]
    scenes={}
    for p in paths:
        if b'CARPX' in p.read_bytes():scenes[p.name]=decode(p.read_bytes(),dol)
    report=dict(original_dol_sha256=DOL_SHA,actor_clock=clock_evidence(dol),scenes=scenes)
    if args.verify_source:report['source_timing_verification']=verify_source_boundaries(raw,report)
    if args.scene_metadata:report['scene_metadata']=json.loads(args.scene_metadata.read_text())
    if args.native and not args.scene_metadata:raise ValueError('--scene-metadata is required for native scene timing')
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    if args.native:print(json.dumps(export_native(report,args.native)))
    print(json.dumps(dict(scenes=len(scenes),actions=sum(len(s['actions']) for s in scenes.values()),output=str(args.output))))
if __name__=='__main__':main()
