#!/usr/bin/env python3
"""Execute whole original EngineRacer8025762C against the supported EngineStep.

Uses canonical disabled induction/empty RPM limiter; external input, tuningNULL,
entity recharge gate, event-dispatch gate and optional boost scalar are explicit.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from vehicle_transmission_engine_verify import Reference,Params as MechanicalParams,Input as MechanicalInput,State as MechanicalState,Clutch,Curve,Tables,Wheel,EXTRA_ABI
from vehicle_transmission_nos_verify import Params as NosParams,Input as NosInput,State as NosState
from vehicle_transmission_auto_verify import Event
from vehicle_attributes import VehicleAttributes
from vehicle_verify_original import ATTR_SHA
from vehicle_ppc_reference import DOL_SHA256
for first,base,restore,offset in [(18,0x80257634,0x80258468,0x30),(29,0x80256c40,0x80256d88,0x10),(28,0x80257204,0x80257474,0x20)]:
    for r in range(first,32):
        off=offset+(r-first)*8;EXTRA_ABI[base+(r-first)*4]=0xf0000000|(r<<21)|(1<<16)|off;EXTRA_ABI[restore+(r-first)*4]=0xe0000000|(r<<21)|(1<<16)|off
class Induction(C.Structure):_fields_=[(n,C.c_float) for n in ['low','high','vacuum','spool']]
class Params(C.Structure):_fields_=[('mechanical',MechanicalParams),('nos',NosParams),('induction',Induction),('shift_speed',C.c_float),('limiter_count',C.c_size_t)]
class Input(C.Structure):_fields_=[('external',MechanicalInput),('nos',NosInput),('raw_throttle',C.c_float),('present',C.c_uint),('automatic',C.c_uint),('rev',C.c_uint)]
class State(C.Structure):_fields_=[('mechanical',MechanicalState),('nos',NosState)]+[(n,C.c_float) for n in ['cooldown','induction_amount','induction_display','induction_boost','scale']]+[('committed',C.c_uint)]
class StepReference(Reference):
    def full(self,el,tl,il,nl,p,inp,state,wheels):
        from unicorn import UC_HOOK_CODE
        from unicorn.ppc_const import UC_PPC_REG_3,UC_PPC_REG_FPR0
        self.mechanical(el,tl,p.mechanical,inp.external,state.mechanical,wheels,prepare_only=True)
        u=self.uc;obj=bytearray(u.mem_read(self.OBJECT,0x1b0))
        for off,v in [(0x5c,0x803fe188),(0x80,0x803fe0a0),(0x128,0x81606000),(0x13c,0x81605000),(0x38,0x81609000),(0x114,0x81609100 if inp.present else 0),(0x1a8,inp.rev),(0x188,state.committed)]:struct.pack_into('>I',obj,off,v)
        for off,v in [(0xfc,state.nos.charge),(0x104,state.nos.activity),(0x110,state.cooldown),(0x94,state.induction_amount),(0x98,state.induction_display),(0x9c,state.induction_boost),(0x100,state.scale)]:struct.pack_into('>f',obj,off,v)
        u.mem_write(self.OBJECT,bytes(obj));u.mem_write(0x81606000,nl);u.mem_write(0x81605000,il)
        for a in [0x81609000,0x81609100]:u.mem_write(a,bytes(4)+struct.pack('>I',0x81609400))
        table=bytearray(0x98)
        for off,callback in [(0x4c,0x10),(0x54,0x30),(0x1c,0x38),(0x8c,0x34)]:struct.pack_into('>I',table,off,self.CALLBACK+callback)
        u.mem_write(0x81609400,bytes(table));raw=bytearray(0x30);struct.pack_into('>f',raw,0x14,inp.raw_throttle);struct.pack_into('>I',raw,0x24,inp.nos.requested);u.mem_write(0x81609800,bytes(raw))
        u.mem_write(0x81609200,bytes(4)+struct.pack('>I',0x81609600));table=bytearray(0x98);struct.pack_into('>I',table,0x94,self.CALLBACK+0x20);u.mem_write(0x81609600,bytes(table))
        # Original Vehicle table retained except external tuning-pointer getter.
        vehicle_table=bytearray(self.dol.read(0x803f8728,0x1b0));struct.pack_into('>I',vehicle_table,0x1a4,self.CALLBACK+0x40);u.mem_write(0x8160f000,bytes(vehicle_table));u.mem_write(0x8160e0b8,struct.pack('>I',0x8160f000))
        for off in [0x10,0x20,0x30,0x34,0x38,0x40]:u.mem_write(self.CALLBACK+off,struct.pack('>I',0x4e800020))
        def callback(uc,a,size,unused):
            if a==self.CALLBACK:uc.reg_write(UC_PPC_REG_FPR0+1,struct.unpack('>Q',struct.pack('>d',inp.external.boost_scalar))[0])
            else:
                result=0
                if a==self.CALLBACK+0x10:result=0x81609200 if inp.nos.inhibited else 0
                if a==self.CALLBACK+0x34:result=inp.automatic
                if a==self.CALLBACK+0x38:result=0x81609800
                uc.reg_write(UC_PPC_REG_3,result)
        hook=u.hook_add(UC_HOOK_CODE,callback,begin=self.CALLBACK,end=self.CALLBACK+0x40)
        u.mem_write(0x8041f654,struct.pack('>I',inp.nos.unlimited))
        self.allowed=((0x8025762c,0x802584a8),(0x8025625c,0x802568a0),(0x80256a08,0x8025762c),(0x80269cdc,0x80269f38),(0x802479a0,0x80247a0c),(0x80268da8,0x80268e14),(0x80268e7c,0x80268ea4),(0x80268ecc,0x80268ed4),(0x8022e0dc,0x8022e0e4),(0x8022e114,0x8022e11c),(0x8022e1d0,0x8022e1d8),(0x802102a8,0x8021031c),(0x80223afc,0x80223c14),(0x80223cd0,0x80223d30),(0x8025546c,0x802554f4),(0x802557e8,0x80255a0c),(0x80255ad4,0x80255fa4),(0x8025607c,0x8025625c),(0x802240ac,0x80224268),(0x80058124,0x8005812c),(0x8005e0c8,0x8005e180),(0x80209080,0x802090a4),(0x801e9c48,0x801e9c54),(self.CALLBACK,self.CALLBACK+0x44))
        before=[bytes(u.mem_read(0x81610000+i*0x1000,0x140)) for i in range(4)];self.write_ranges=((self.OBJECT,self.OBJECT+len(obj)),*[(0x81610000+i*0x1000,0x81610000+i*0x1000+0x140) for i in range(4)])
        try:self._call(0x8025762c,self.OBJECT,inp.external.seconds)
        finally:self.write_ranges=();u.hook_del(hook)
        raw=bytes(u.mem_read(self.OBJECT,len(obj)));actual=State.from_buffer_copy(state)
        for name,off in [('output',0x84),('throttle',0x90),('omega',0xf0),('acceleration',0xf4),('shaft',0xf8),('slip',0x108),('reported',0x184),('delay',0x8c)]:setattr(actual.mechanical,name,struct.unpack_from('>f',raw,off)[0])
        for name,off in [('gear',0x88),('negative',0x10c),('request',0x18c)]:setattr(actual.mechanical,name,struct.unpack_from('>I',raw,off)[0])
        actual.mechanical.clutch=Clutch(*struct.unpack_from('>Iff',raw,0x19c))
        actual.nos=NosState(struct.unpack_from('>f',raw,0xfc)[0],struct.unpack_from('>f',raw,0x104)[0])
        for name,off in [('cooldown',0x110),('induction_amount',0x94),('induction_display',0x98),('induction_boost',0x9c),('scale',0x100)]:setattr(actual,name,struct.unpack_from('>f',raw,off)[0])
        actual.committed=struct.unpack_from('>I',raw,0x188)[0]
        changes=set(range(0x84,0xa0))|set(range(0x100,0x114))|set(range(0xf0,0x100))|set(range(0x184,0x190))|set(range(0x19c,0x1a8))
        assert all(a==b for i,(a,b) in enumerate(zip(obj,raw)) if i not in changes)
        output=(Wheel*4).from_buffer_copy(wheels)
        for i,b in enumerate(before):
            after=bytes(u.mem_read(0x81610000+i*0x1000,0x140));assert all(x==y for j,(x,y) in enumerate(zip(b,after)) if j not in range(0xd0,0xd4));output[i].omega=struct.unpack_from('>f',after,0xd0)[0]
        return actual,output

def verify(dol,attributes):
    from vehicle_vlt_hash import vlt_hash as h
    raw=attributes.read_bytes();assert hashlib.sha256(raw).hexdigest()==ATTR_SHA
    db=VehicleAttributes(raw);ref=StepReference(dol.read_bytes());ref.initialize_launch();root=Path(__file__).resolve().parents[1];rng=random.Random(802576);cases=0
    def layout(row):return bytes(db.bin[row['layout']:row['layout']+db.classes[row['class_key']]['base_size']])
    def bits(v):return struct.pack('>f',v)
    def flatten(value,prefix=''):
        out={}
        for name,typ in type(value)._fields_:
            v=getattr(value,name);key=prefix+name
            if issubclass(typ,C.Structure):out.update(flatten(v,key+'.'))
            else:out[key]=bits(v) if typ is C.c_float else v
        return out
    with tempfile.TemporaryDirectory(prefix='mw-fullstep-') as tmp:
        so=Path(tmp)/'step.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),*[str(root/f'source_bmw/{m}.c') for m in ['mw_physics_transmission_engine','mw_physics_transmission','mw_physics_transmission_policy','mw_physics_transmission_auto','mw_physics_transmission_nos','mw_physics_engine']],'-lm','-o',str(so)],check=True)
        lib=C.CDLL(str(so));step=lib.mw_physics_transmission_engine_step;step.argtypes=[C.POINTER(Params),C.POINTER(Input),C.POINTER(State),C.POINTER(Wheel),C.POINTER(Event)];step.restype=C.c_bool
        for name in ['bmwm3gtre46','m3gtre46careerstart']:
            er=db.find('engine',name);tr=db.find('transmission',name);ir=db.find('induction','default');nr=db.find('nos',0x1efbd807);ef=db.fields(er);tf=db.fields(tr);nf=db.fields(nr);el,tl,il,nl=map(layout,[er,tr,ir,nr]);torque=ef['TORQUE']['value']['values'];braking=ef['ENGINE_BRAKING']['value']['values'];ta=(C.c_float*len(torque))(*torque);ba=(C.c_float*len(braking))(*braking);rpm=[ef[k]['value'] for k in ['IDLE','MAX_RPM','RED_LINE']];ratios=tf['GEAR_RATIO']['value']['values'];eff=tf['GEAR_EFFICIENCY']['value']['values'];ra=(C.c_float*len(ratios))(*ratios);ea=(C.c_float*len(eff))(*eff);peak,peakrpm=ref.peak(el,il);_,up,down,_=ref.shift_tables(el,il,tl);tables=Tables((C.c_float*10)(*up),(C.c_float*10)(*down),len(ratios));mp=MechanicalParams(Curve(ta,len(torque),*rpm),Curve(ba,len(braking),*rpm),ra,ea,len(ratios),ef['FLYWHEEL_MASS']['value'],*(tf[k]['value'] for k in ['FINAL_GEAR','TORQUE_SPLIT','TORQUE_CONVERTER','CLUTCH_SLIP']),peak,peakrpm,C.pointer(tables));np=NosParams(*(nf[k]['value'] for k in ['NOS_DISENGAGE','TORQUE_BOOST','NOS_CAPACITY','RECHARGE_MIN','RECHARGE_MAX','RECHARGE_MIN_SPEED','RECHARGE_MAX_SPEED']));p=Params(mp,np,Induction(),tf['SHIFT_SPEED']['value'],0)
            for i in range(768):
                w=(Wheel*4)(*(Wheel(rng.uniform(-100,100),rng.choice([0,.1]),rng.choice([0,1]),rng.uniform(-20,20),.3433,0) for _ in range(4)));ms=MechanicalState(rng.randrange(len(ratios)),Clutch(rng.randrange(3),rng.choice([0,.05,.25]),rng.choice([.05,.25])),rng.choice([0,.1]),rng.uniform(0,1000),0,rng.uniform(-200,1500),0,rng.uniform(0,10000),0,0,0,0,rng.choice([0,1,2]));s=State(ms,NosState(rng.choice([0,.1,1]),rng.choice([0,.5,1])),rng.choice([0,.1]),.5,.5,.5,1,0)
                ext=MechanicalInput(rng.choice([1/120,1/60,.1]),0,0,1,rng.choice([0,6]),rng.randrange(2),rng.choice([0,1]),rng.choice([0,30]),rng.randrange(5),rng.randrange(2),rng.choice([0,.5]),(C.c_float*4)(*[rng.uniform(-5,5) for _ in range(4)]));ni=NosInput();ni.requested=rng.randrange(2);ni.inhibited=rng.randrange(2);ni.unlimited=rng.randrange(2);inp=Input(ext,ni,rng.choice([0,.1,1]),1,rng.randrange(2),rng.randrange(2))
                if i>=512 and i%32:s=State.from_buffer_copy(previous);w=(Wheel*4).from_buffer_copy(previous_wheels)
                expected,expectedw=ref.full(el,tl,il,nl,p,inp,s,w);actual=State.from_buffer_copy(s);outw=(Wheel*4).from_buffer_copy(w);event=Event();assert step(C.byref(p),C.byref(inp),C.byref(actual),outw,C.byref(event));a,b=flatten(actual),flatten(expected)
                if a!=b:raise AssertionError((name,i,{k:(a[k],b[k]) for k in a if a[k]!=b[k]}))
                assert list(map(bits,[v.omega for v in outw]))==list(map(bits,[v.omega for v in expectedw])),(name,i,'wheels')
                previous=actual;previous_wheels=outw;cases+=1
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,original_whole_function='8025762C..802584A8',whole_engine_state_cases=cases,stateful_continuation_steps=512,physical_collections=['bmwm3gtre46','m3gtre46careerstart'],nos_collection='1efbd807 (explicit selected test input; upgrade choice not claimed)',limitations=['Only disabled induction and empty RPM limiter supported; positive induction/nonempty limiter rejected','Active rev modulation deadline rejected; raw rev-block boolean supported','External raw input/automatic-enabled/tuningNULL/recharge-inhibit/event-dispatch callbacks supplied explicitly','Optional event allocation disabled; source-derived physical upgrade and scheduler remain gates'])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.dol,a.attributes);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
