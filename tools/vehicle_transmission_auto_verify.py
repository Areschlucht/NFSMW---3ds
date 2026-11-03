#!/usr/bin/env python3
"""Original automatic policy, accepted commit wrapper and post-input timers."""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from vehicle_transmission_engine_verify import Reference,Params as EngineParams,Input as EngineInput,State as EngineState,Clutch,Curve,Tables,Wheel,EXTRA_ABI
from vehicle_attributes import VehicleAttributes
from vehicle_verify_original import ATTR_SHA
from vehicle_ppc_reference import DOL_SHA256
for first,base,restore,offset in [(28,0x80255adc,0x80255dc8,0x20),(30,0x80257514,0x8025761c,0x10)]:
    for r in range(first,32):
        off=offset+(r-first)*8;EXTRA_ABI[base+(r-first)*4]=0xf0000000|(r<<21)|(1<<16)|off;EXTRA_ABI[restore+(r-first)*4]=0xe0000000|(r<<21)|(1<<16)|off
class Shift(C.Structure):_fields_=[('gear',C.c_uint),('clutch',C.c_uint),('delay',C.c_float)]
class State(C.Structure):_fields_=[('shift',Shift),('cooldown',C.c_float),('request',C.c_uint),('committed',C.c_uint)]
class Params(C.Structure):_fields_=[('tables',C.POINTER(Tables)),('ratios',C.POINTER(C.c_float)),('count',C.c_size_t),('speed',C.c_float),('idle',C.c_float)]
class Input(C.Structure):_fields_=[(n,C.c_float) for n in ['seconds','raw','throttle','shaft']]+[(n,C.c_uint) for n in ['present','enabled','gate']]+[('contacted',C.c_uint*4),('slips',C.c_float*4)]
class Event(C.Structure):_fields_=[(n,C.c_uint) for n in ['accepted','previous','new','automatic']]
class AutoReference(Reference):
    def automatic(self,el,tl,enginep,p,inp,state):
        from unicorn import UC_HOOK_CODE
        from unicorn.ppc_const import UC_PPC_REG_3
        s=EngineState();s.gear=state.shift.gear;s.clutch=Clutch(state.shift.clutch,0,0);s.delay=state.shift.delay;s.shaft=inp.shaft;s.request=state.request
        ei=EngineInput();ei.throttle=inp.throttle;ei.gate=inp.gate;wheels=(Wheel*4)(*(Wheel(0,float(bool(inp.contacted[i])),0,0,.3433,0) for i in range(4)))
        self.mechanical(el,tl,enginep,ei,s,wheels,prepare_only=True)
        u=self.uc;obj=bytearray(u.mem_read(self.OBJECT,0x1b0));struct.pack_into('>I',obj,0x38,0x81609000);struct.pack_into('>I',obj,0x114,0x81609100 if inp.present else 0);struct.pack_into('>f',obj,0x110,state.cooldown);struct.pack_into('>I',obj,0x188,state.committed);u.mem_write(self.OBJECT,bytes(obj))
        for i,slip in enumerate(inp.slips):u.mem_write(0x81610000+i*0x1000+0xf0,struct.pack('>f',slip))
        for a in [0x81609000,0x81609100]:u.mem_write(a,bytes(4)+struct.pack('>I',0x81609400))
        table=bytearray(0x90);struct.pack_into('>I',table,0x54,self.CALLBACK+0x30);struct.pack_into('>I',table,0x1c,self.CALLBACK+0x38);struct.pack_into('>I',table,0x8c,self.CALLBACK+0x34);u.mem_write(0x81609400,bytes(table));raw=bytearray(0x30);struct.pack_into('>f',raw,0x14,inp.raw);u.mem_write(0x81609800,bytes(raw))
        for a in [self.CALLBACK+0x30,self.CALLBACK+0x34,self.CALLBACK+0x38]:u.mem_write(a,struct.pack('>I',0x4e800020))
        def callback(uc,a,size,unused):uc.reg_write(UC_PPC_REG_3,0 if a==self.CALLBACK+0x30 else inp.enabled if a==self.CALLBACK+0x34 else 0x81609800)
        hook=u.hook_add(UC_HOOK_CODE,callback,begin=self.CALLBACK+0x30,end=self.CALLBACK+0x38)
        self.allowed=((0x8025750c,0x8025762c),(0x80255ad4,0x80255fa4),(0x8025607c,0x8025625c),(0x80269e90,0x80269f38),(0x8022e114,0x8022e11c),(0x80268da8,0x80268dc4),(0x80268e7c,0x80268ea4),(0x80058124,0x8005812c),(self.CALLBACK+0x30,self.CALLBACK+0x3c));self.write_ranges=((self.OBJECT,self.OBJECT+len(obj)),)
        try:self._call(0x8025750c,self.OBJECT,inp.seconds)
        finally:self.write_ranges=();u.hook_del(hook)
        after=bytes(u.mem_read(self.OBJECT,len(obj)));allowed=set(range(0x88,0x90))|set(range(0x110,0x114))|set(range(0x188,0x190))|set(range(0x19c,0x1a0));assert all(a==b for i,(a,b) in enumerate(zip(obj,after)) if i not in allowed)
        gear,delay=struct.unpack_from('>If',after,0x88);clutch=struct.unpack_from('>I',after,0x19c)[0];cooldown=struct.unpack_from('>f',after,0x110)[0];committed,request=struct.unpack_from('>2I',after,0x188)
        expected=State(Shift(gear,clutch,delay),cooldown,request,committed);accepted=gear!=state.shift.gear and state.shift.gear!=1
        return expected,Event(int(accepted),state.shift.gear if accepted else 0,gear if accepted else 0,int(accepted))

def verify(dol,attributes):
    raw=attributes.read_bytes();assert hashlib.sha256(raw).hexdigest()==ATTR_SHA
    db=VehicleAttributes(raw);ref=AutoReference(dol.read_bytes());root=Path(__file__).resolve().parents[1];rng=random.Random(80255);cases=0
    def layout(row):return bytes(db.bin[row['layout']:row['layout']+db.classes[row['class_key']]['base_size']])
    def bits(v):return struct.pack('>f',v)
    with tempfile.TemporaryDirectory(prefix='mw-auto-') as tmp:
        so=Path(tmp)/'auto.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),*[str(root/f'source_bmw/{m}.c') for m in ['mw_physics_transmission_auto','mw_physics_transmission','mw_physics_transmission_policy','mw_physics_engine']],'-lm','-o',str(so)],check=True)
        lib=C.CDLL(str(so));step=lib.mw_physics_transmission_automatic_step;step.argtypes=[C.POINTER(Params),C.POINTER(Input),C.POINTER(State),C.POINTER(Event)];step.restype=C.c_bool
        accepted=0
        for name in ['bmwm3gtre46','m3gtre46careerstart']:
            er=db.find('engine',name);tr=db.find('transmission',name);ir=db.find('induction','default');ef=db.fields(er);tf=db.fields(tr);el,tl=layout(er),layout(tr)
            _,up,down,_=ref.shift_tables(el,layout(ir),tl);ratios=tf['GEAR_RATIO']['value']['values'];ra=(C.c_float*len(ratios))(*ratios);tables=Tables((C.c_float*10)(*up),(C.c_float*10)(*down),len(ratios));enginep=EngineParams();enginep.tables=C.pointer(tables);p=Params(C.pointer(tables),ra,len(ratios),tf['SHIFT_SPEED']['value'],ef['IDLE']['value'])
            for i in range(2048):
                inp=Input(rng.choice([0,1/60,.1]),rng.choice([0,.5,1,1.1]),rng.choice([0,.5,1]),rng.uniform(0,1000),rng.randrange(2),rng.randrange(2),rng.randrange(2),(C.c_uint*4)(*[rng.choice([1,1,0]) for _ in range(4)]),(C.c_float*4)(*[rng.choice([-10,0,3.99,4,4.01]) for _ in range(4)]))
                state=State(Shift(rng.randrange(len(ratios)),rng.randrange(3),rng.choice([-.1,0,.1])),rng.choice([0,.1]),rng.choice([0,1,2,3,4,5]),rng.randrange(2));expected,event=ref.automatic(el,tl,enginep,p,inp,state);actual=State.from_buffer_copy(state);out=Event();assert step(C.byref(p),C.byref(inp),C.byref(actual),C.byref(out))
                got=(actual.shift.gear,actual.shift.clutch,bits(actual.shift.delay),bits(actual.cooldown),actual.request,actual.committed);want=(expected.shift.gear,expected.shift.clutch,bits(expected.shift.delay),bits(expected.cooldown),expected.request,expected.committed)
                if got!=want:raise AssertionError((name,i,got,want,[(n,getattr(inp,n)) for n,t in Input._fields_[:7]],state.shift.gear,state.request))
                assert bytes(out)==bytes(event),(name,i,'event',list(bytes(out)),list(bytes(event)))
                accepted+=out.accepted;cases+=1
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,whole_automatic_post_update_cases=cases,accepted_shifts=accepted,original_ranges=['80255AD4..80255DE0','8025617C..8025625C','8025750C..8025762C'],limitations=['Optional game event allocation/dispatch callback is disabled in original reference; accepted gear-event data is returned to caller','Actual automatic-enabled/raw input providers and scheduler remain explicit'])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.dol,a.attributes);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
