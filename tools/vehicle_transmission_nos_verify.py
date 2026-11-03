#!/usr/bin/env python3
"""Complete original timed NOS function with explicit external callback outcomes."""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from vehicle_transmission_engine_verify import Reference,EXTRA_ABI
from vehicle_attributes import VehicleAttributes
from vehicle_vlt_hash import vlt_hash as h
from vehicle_verify_original import ATTR_SHA
from vehicle_ppc_reference import DOL_SHA256
for r in range(26,32):
    off=0x18+(r-26)*8;EXTRA_ABI[0x80256da4+(r-26)*4]=0xf0000000|(r<<21)|(1<<16)|off;EXTRA_ABI[0x802571dc+(r-26)*4]=0xe0000000|(r<<21)|(1<<16)|off
class Params(C.Structure):_fields_=[(n,C.c_float) for n in ['disengage','boost','capacity','rmin','rmax','smin','smax']]
class Input(C.Structure):
    _fields_=[(n,C.c_float) for n in ['seconds','throttle','speed']]+[(n,C.c_uint) for n in ['gear','requested','rev','inhibited','mode','unlimited','boost_present']]+[('boost',C.c_float),('tuning_present',C.c_uint),('tuning',C.c_float)]
class State(C.Structure):_fields_=[('charge',C.c_float),('activity',C.c_float)]
class NosReference(Reference):
    def nos(self,layout,inp,s):
        from unicorn import UC_HOOK_CODE
        from unicorn.ppc_const import UC_PPC_REG_3,UC_PPC_REG_5,UC_PPC_REG_FPR0
        obj=bytearray(0x1b0)
        for off,v in [(0x5c,0x803fe188),(0x80,0x803fe0a0),(0x128,self.ENGINE),(0x38,0x81609000),(0x4c,0x8160e0b4),(0x88,inp.gear),(0x1a8,inp.rev)]:struct.pack_into('>I',obj,off,v)
        for off,v in [(0x90,inp.throttle),(0xfc,s.charge),(0x104,s.activity)]:struct.pack_into('>f',obj,off,v)
        if inp.boost_present:struct.pack_into('>I',obj,0x11c,0x8160a000)
        self.uc.mem_write(self.OBJECT,bytes(obj));self.uc.mem_write(self.ENGINE,layout)
        behavior=bytearray(0x100);struct.pack_into('>I',behavior,4,0x81609400);self.uc.mem_write(0x81609000,bytes(behavior))
        table=bytearray(0x98);struct.pack_into('>I',table,0x4c,self.CALLBACK+0x10);self.uc.mem_write(0x81609400,bytes(table))
        self.uc.mem_write(0x81609200,bytes(4)+struct.pack('>I',0x81609600));table=bytearray(0x98);struct.pack_into('>I',table,0x94,self.CALLBACK+0x20);self.uc.mem_write(0x81609600,bytes(table))
        self.uc.mem_write(0x8160a000,bytes(4)+struct.pack('>I',0x8160a100));table=bytearray(0x18);struct.pack_into('>I',table,0x14,self.CALLBACK);self.uc.mem_write(0x8160a100,bytes(table))
        vehicle=bytearray(0x200);struct.pack_into('>I',vehicle,0xb8,0x803f8728);struct.pack_into('>I',vehicle,0x148,inp.mode);struct.pack_into('>f',vehicle,0x128,inp.speed);self.uc.mem_write(0x8160e000,bytes(vehicle))
        for a in [self.CALLBACK+0x10,self.CALLBACK+0x20]:self.uc.mem_write(a,struct.pack('>I',0x4e800020))
        def callback(uc,address,size,unused):
            if address==self.CALLBACK:uc.reg_write(UC_PPC_REG_FPR0+1,struct.unpack('>Q',struct.pack('>d',inp.boost))[0])
            elif address==self.CALLBACK+0x10:uc.reg_write(UC_PPC_REG_3,0x81609200 if inp.inhibited else 0)
            else:uc.reg_write(UC_PPC_REG_3,0)
        hook=self.uc.hook_add(UC_HOOK_CODE,callback,begin=self.CALLBACK,end=self.CALLBACK+0x20)
        self.uc.mem_write(0x8041f654,struct.pack('>I',inp.unlimited));self.uc.reg_write(UC_PPC_REG_5,inp.requested)
        tuning=bytearray(0x20);struct.pack_into('>f',tuning,0x14,inp.tuning);self.uc.mem_write(0x8160c100,bytes(tuning))
        self.allowed=((0x80256d9c,0x802571fc),(0x80269cdc,0x80269d30),(0x80269e4c,0x80269e54),(0x8022e1d0,0x8022e1d8),(0x8022e0dc,0x8022e0e4),(0x80223cd0,0x80223d30),(self.CALLBACK,self.CALLBACK+0x24))
        self.write_ranges=((self.OBJECT,self.OBJECT+len(obj)),)
        try:scale=self._call(0x80256d9c,self.OBJECT,inp.seconds,r4=0x8160c100 if inp.tuning_present else 0)
        finally:self.write_ranges=();self.uc.hook_del(hook)
        result=bytes(self.uc.mem_read(self.OBJECT,len(obj)));assert all(a==b for i,(a,b) in enumerate(zip(obj,result)) if i not in set(range(0xfc,0x100))|set(range(0x104,0x108)))
        return struct.unpack_from('>f',result,0xfc)[0],struct.unpack_from('>f',result,0x104)[0],scale

def verify(dol,attributes):
    raw=attributes.read_bytes();assert hashlib.sha256(raw).hexdigest()==ATTR_SHA
    db=VehicleAttributes(raw);ref=NosReference(dol.read_bytes());root=Path(__file__).resolve().parents[1];rng=random.Random(80256);cases=0;rows=0
    def bits(v):return struct.pack('>f',v)
    with tempfile.TemporaryDirectory(prefix='mw-nos-') as tmp:
        so=Path(tmp)/'nos.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_physics_transmission_nos.c'),'-lm','-o',str(so)],check=True)
        lib=C.CDLL(str(so));step=lib.mw_physics_transmission_nos_step;step.argtypes=[C.POINTER(Params),C.POINTER(Input),C.POINTER(State),C.POINTER(C.c_float)];step.restype=C.c_bool
        for row in db.collections.values():
            if row['class_key']!=h('nos'):continue
            fields=db.fields(row);layout=bytes(db.bin[row['layout']:row['layout']+32]);p=Params(*(fields[k]['value'] for k in ['NOS_DISENGAGE','TORQUE_BOOST','NOS_CAPACITY','RECHARGE_MIN','RECHARGE_MAX','RECHARGE_MIN_SPEED','RECHARGE_MAX_SPEED']));rows+=1
            for i in range(384):
                inp=Input(rng.choice([0,1/120,1/60,.1,1]),rng.choice([0,.1,1]),rng.choice([0,5/2.236989974975586,10/2.236989974975586,30,100]),rng.choice([0,1,2,7]),rng.randrange(2),rng.randrange(2),rng.randrange(2),rng.choice([0,6]),rng.randrange(2),rng.randrange(2),rng.choice([0,.5,1]),rng.randrange(2),rng.choice([-1,0,1,5]))
                state=State(rng.choice([0,.001,.5,1]),rng.choice([0,.1,.5,1]));
                if i>=256 and i%32:state=State.from_buffer_copy(previous)
                expected=ref.nos(layout,inp,state);actual=State.from_buffer_copy(state);scale=C.c_float();assert step(C.byref(p),C.byref(inp),C.byref(actual),C.byref(scale));got=(actual.charge,actual.activity,scale.value)
                if list(map(bits,expected))!=list(map(bits,got)):raise AssertionError((db.label(row['key']),i,expected,got,[(n,getattr(inp,n)) for n,t in Input._fields_],state.charge,state.activity))
                previous=actual;cases+=1
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,nos_collections=rows,whole_function_float_state_cases=cases,stateful_continuation_steps=rows*128,original_range='80256D9C..802571FC',limitations=['Optional vehicle-object recharge-inhibit callback is explicitly supplied','Physical profile NOS upgrade selection and broader request input producer remain separate'])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.dol,a.attributes);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
