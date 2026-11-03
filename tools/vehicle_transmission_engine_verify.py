#!/usr/bin/env python3
"""Whole original mechanical continuation after explicitly supplied timed inputs.

Runs802577A8..8025845C with actual original Engine/Vehicle/WheelControl vtables,
complete curve, torque, clutch, wheel sync/cap and shift-classifier call graph.
The earlier input/timed virtual stages and rev modulation are separate gates.
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
from vehicle_transmission_sync_verify import SyncReference,Wheel
from vehicle_transmission_peak_verify import PeakReference
from vehicle_transmission_policy_verify import EXTRA_ABI
from vehicle_attributes import VehicleAttributes
from vehicle_verify_original import ATTR_SHA
from vehicle_ppc_reference import DOL_SHA256

for first,base,restore,offset in [(30,0x8025648c,0x802565b0,0x28)]:
    for r in range(first,32):
        off=offset+(r-first)*8;EXTRA_ABI[base+(r-first)*4]=0xf0000000|(r<<21)|(1<<16)|off;EXTRA_ABI[restore+(r-first)*4]=0xe0000000|(r<<21)|(1<<16)|off

class Curve(C.Structure):_fields_=[('values',C.POINTER(C.c_float)),('count',C.c_size_t),('idle',C.c_float),('maximum',C.c_float),('redline',C.c_float)]
class Tables(C.Structure):_fields_=[('up',C.c_float*10),('down',C.c_float*10),('count',C.c_size_t)]
class Clutch(C.Structure):_fields_=[('mode',C.c_uint),('remaining',C.c_float),('duration',C.c_float)]
class State(C.Structure):
    _fields_=[('gear',C.c_uint),('clutch',Clutch)]+[(n,C.c_float) for n in ['delay','omega','acceleration','shaft','slip','reported','output','throttle','rev_deadline']]+[('negative',C.c_uint),('request',C.c_uint)]
class Params(C.Structure):
    _fields_=[('torque',Curve),('braking',Curve),('ratios',C.POINTER(C.c_float)),('efficiency',C.POINTER(C.c_float)),('count',C.c_size_t)]+[(n,C.c_float) for n in ['mass','final','split','converter','clutch_slip','peak','peakrpm']]+[('tables',C.POINTER(Tables))]
class Input(C.Structure):
    _fields_=[(n,C.c_float) for n in ['seconds','throttle','boost','scale']]+[('mode',C.c_uint),('gate',C.c_uint)]+[(n,C.c_float) for n in ['scalar58','speed128']]+[('contacts',C.c_uint),('boost_present',C.c_uint),('boost_scalar',C.c_float),('slips',C.c_float*4)]
class Reference(SyncReference,PeakReference):
    def initialize_launch(self):
        from unicorn.ppc_const import UC_PPC_REG_27,UC_PPC_REG_3,UC_PPC_REG_PC
        self.uc.reg_write(UC_PPC_REG_27,0x80410000);self.uc.reg_write(UC_PPC_REG_3,0)
        self.allowed=((0x80265eb0,0x80265ee4),);self.write_ranges=((0x8048a0e0,0x8048a0f4),)
        try:self.uc.emu_start(0x80265eb0,0x80265ee4,count=20,timeout=200000)
        finally:self.write_ranges=()
        assert self.uc.reg_read(UC_PPC_REG_PC)==0x80265ee4
        assert bytes(self.uc.mem_read(0x8048a0ec,8))==struct.pack('>II',0x8041f65c,5)
    def mechanical(self,el,tl,p,inp,s,wheels,prepare_only=False):
        from unicorn.ppc_const import UC_PPC_REG_26,UC_PPC_REG_31,UC_PPC_REG_FPR0,UC_PPC_REG_MSR,UC_PPC_REG_PC
        actor=self.speed_wheels(wheels);struct.pack_into('>I',actor,0x54,0x803fe938);struct.pack_into('>I',actor,0x104,inp.contacts);self.uc.mem_write(0x8160d000,bytes(actor))
        for i,v in enumerate(inp.slips):self.uc.mem_write(0x81610000+i*0x1000+0xf0,struct.pack('>f',v))
        vehicle=bytearray(0x200)
        for off,v in [(0xb8,0x803f8728),(0x148,inp.mode),(0x168,inp.gate)]:struct.pack_into('>I',vehicle,off,v)
        for off,v in [(0x128,inp.speed128),(0x16c,1),(0x170,inp.scalar58)]:struct.pack_into('>f',vehicle,off,v)
        self.uc.mem_write(0x8160e000,bytes(vehicle));self.uc.mem_write(self.ENGINE,el);self.uc.mem_write(0x81603000,tl)
        obj=bytearray(0x1b0)
        for off,v in [(0x14,0x803fdfc8),(0x54,0x803fe118),(0x118,0x8160d050),(0x4c,0x8160e0b4),(0x150,self.ENGINE),(0x164,0x81603000),(0x88,s.gear),(0x19c,s.clutch.mode),(0x18c,s.request),(0x10c,s.negative)]:struct.pack_into('>I',obj,off,v)
        for off,v in [(0x84,s.output),(0x8c,s.delay),(0x90,inp.throttle),(0x9c,inp.boost),(0x100,inp.scale),(0xf0,s.omega),(0xf4,s.acceleration),(0xf8,s.shaft),(0x108,s.slip),(0x184,s.reported),(0x190,C.c_float(p.peak*1.3558000326156616).value),(0x194,p.peakrpm),(0x19c+4,s.clutch.remaining),(0x19c+8,s.clutch.duration)]:struct.pack_into('>f',obj,off,v)
        struct.pack_into('>10f',obj,0xa0,*p.tables.contents.up);struct.pack_into('>10f',obj,0xc8,*p.tables.contents.down)
        self.uc.mem_write(self.OBJECT,bytes(obj))
        # Optional boost interface explicitly supplied; scalar-only callback.
        if inp.boost_present:
            struct.pack_into('>I',obj,0x11c,0x8160a000);self.uc.mem_write(self.OBJECT,bytes(obj))
            self.uc.mem_write(0x8160a000,bytes(4)+struct.pack('>I',0x8160a100));table=bytearray(0x18);struct.pack_into('>I',table,0x14,self.CALLBACK);self.uc.mem_write(0x8160a100,bytes(table))
        if prepare_only:return
        from unicorn import UC_HOOK_CODE
        def boost(uc,address,size,unused):uc.reg_write(UC_PPC_REG_FPR0+1,struct.unpack('>Q',struct.pack('>d',inp.boost_scalar))[0])
        hook=self.uc.hook_add(UC_HOOK_CODE,boost,begin=self.CALLBACK,end=self.CALLBACK)
        self.uc.reg_write(UC_PPC_REG_31,self.OBJECT);self.uc.reg_write(UC_PPC_REG_26,inp.gate);self.uc.reg_write(UC_PPC_REG_FPR0+25,struct.unpack('>Q',struct.pack('>d',inp.seconds))[0]);self.uc.reg_write(UC_PPC_REG_MSR,0x2000)
        self.allowed=((0x802577a8,0x8025845c),(0x8025625c,0x802568a0),(0x80256a08,0x80256c38),(0x80269dd8,0x80269f38),(0x802479a0,0x80247a0c),(0x80268da8,0x80268e14),(0x80268e7c,0x80268ea4),(0x80268ecc,0x80268ed4),(0x8022e0dc,0x8022e0e4),(0x8022e114,0x8022e11c),(0x8022e1d0,0x8022e1d8),(0x802102a8,0x8021031c),(0x80223afc,0x80223b3c),(0x8025546c,0x802554f4),(0x802557e8,0x80255a0c),(0x80255de0,0x80255fa4),(0x802240ac,0x80224268),(0x80058124,0x8005812c),(0x8005e0c8,0x8005e180),(0x80209080,0x802090a4),(self.CALLBACK,self.CALLBACK+4))
        before=[bytes(self.uc.mem_read(0x81610000+i*0x1000,0x140)) for i in range(4)]
        self.write_ranges=((self.OBJECT,self.OBJECT+len(obj)),*[(0x81610000+i*0x1000,0x81610000+i*0x1000+0x140) for i in range(4)]);self.count=0
        try:self.uc.emu_start(0x802577a8,0x8025845c,count=20000,timeout=1000000)
        finally:self.write_ranges=();self.uc.hook_del(hook)
        assert self.uc.reg_read(UC_PPC_REG_PC)==0x8025845c
        result=bytes(self.uc.mem_read(self.OBJECT,len(obj)));changes=set(range(0x19c,0x1a8))|set(range(0xf0,0xfc))|set(range(0x108,0x110))|set(range(0x84,0x88))|set(range(0x90,0x94))|set(range(0x184,0x188))|set(range(0x18c,0x190))
        assert all(a==b for i,(a,b) in enumerate(zip(obj,result)) if i not in changes)
        actual=State.from_buffer_copy(s)
        for name,off in [('output',0x84),('throttle',0x90),('omega',0xf0),('acceleration',0xf4),('shaft',0xf8),('slip',0x108),('reported',0x184)]:setattr(actual,name,struct.unpack_from('>f',result,off)[0])
        actual.clutch=Clutch(*struct.unpack_from('>Iff',result,0x19c));actual.negative=struct.unpack_from('>I',result,0x10c)[0];actual.request=struct.unpack_from('>I',result,0x18c)[0]
        outw=(Wheel*4).from_buffer_copy(wheels)
        for i,raw in enumerate(before):
            after=bytes(self.uc.mem_read(0x81610000+i*0x1000,0x140));assert all(a==b for j,(a,b) in enumerate(zip(raw,after)) if j not in range(0xd0,0xd4));outw[i].omega=struct.unpack_from('>f',after,0xd0)[0]
        return actual,outw

def verify(dol,attributes):
    from vehicle_vlt_hash import vlt_hash as h
    data=attributes.read_bytes();assert hashlib.sha256(data).hexdigest()==ATTR_SHA
    db=VehicleAttributes(data);ref=Reference(dol.read_bytes());ref.initialize_launch();root=Path(__file__).resolve().parents[1];rng=random.Random(8025762);cases=0
    def layout(row):return bytes(db.bin[row['layout']:row['layout']+db.classes[row['class_key']]['base_size']])
    def bits(v):return struct.pack('>f',v)
    with tempfile.TemporaryDirectory(prefix='mw-enginestep-') as tmp:
        so=Path(tmp)/'engine.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),*[str(root/f'source_bmw/{m}.c') for m in ['mw_physics_transmission_engine','mw_physics_transmission','mw_physics_transmission_policy','mw_physics_engine']],'-lm','-o',str(so)],check=True)
        lib=C.CDLL(str(so));step=lib.mw_physics_transmission_engine_mechanical_step;step.argtypes=[C.POINTER(Params),C.POINTER(Input),C.POINTER(State),C.POINTER(Wheel)];step.restype=C.c_bool
        profiles=[]
        for name in ['bmwm3gtre46','m3gtre46careerstart']:
            er=db.find('engine',name);tr=db.find('transmission',name);ir=db.find('induction','default');ef=db.fields(er);tf=db.fields(tr)
            torque=ef['TORQUE']['value']['values'];brake=ef['ENGINE_BRAKING']['value']['values'];ta=(C.c_float*len(torque))(*torque);ba=(C.c_float*len(brake))(*brake);args=[ef[k]['value'] for k in ['IDLE','MAX_RPM','RED_LINE']]
            ratios=tf['GEAR_RATIO']['value']['values'];eff=tf['GEAR_EFFICIENCY']['value']['values'];ra=(C.c_float*len(ratios))(*ratios);ea=(C.c_float*len(eff))(*eff)
            peak,peakrpm=ref.peak(layout(er),layout(ir));_,up,down,_=ref.shift_tables(layout(er),layout(ir),layout(tr));tables=Tables((C.c_float*10)(*up),(C.c_float*10)(*down),len(ratios))
            p=Params(Curve(ta,len(torque),*args),Curve(ba,len(brake),*args),ra,ea,len(ratios),ef['FLYWHEEL_MASS']['value'],*(tf[k]['value'] for k in ['FINAL_GEAR','TORQUE_SPLIT','TORQUE_CONVERTER','CLUTCH_SLIP']),peak,peakrpm,C.pointer(tables))
            profiles.append(dict(name=name,peak=peak,peak_rpm=peakrpm))
            for i in range(1280):
                wheels=(Wheel*4)(*(Wheel(rng.uniform(-200,200),rng.choice([0,.1]),rng.choice([0,.5,1,1.1]),rng.uniform(-50,50),.3433,rng.randrange(2)) for _ in range(4)))
                s=State(rng.randrange(len(ratios)),Clutch(rng.randrange(3),rng.choice([0,.05,.25]),rng.choice([.05,.25])),rng.choice([0,.1]),rng.uniform(0,1000),0,rng.uniform(-500,1500),rng.choice([-3000,0,3000]),rng.uniform(0,10000),0,0,0,0,0)
                inp=Input(rng.choice([1/120,1/60,.1]),rng.choice([0,.1,1]),rng.choice([0,.3]),rng.choice([0,.8,1]),rng.choice([0,6]),rng.randrange(2),rng.choice([0,1]),rng.choice([0,30]),rng.randrange(5),rng.randrange(2),rng.choice([0,.5,1]),(C.c_float*4)(*[rng.uniform(-5,5) for _ in range(4)]))
                if i>=1024:
                    if i%32:
                        s=State.from_buffer_copy(previous_state);wheels=(Wheel*4).from_buffer_copy(previous_wheels)
                        for wheel in wheels:
                            wheel.compression=rng.choice([0,.1]);wheel.previous=rng.uniform(-50,50)
                    else:s.gear=((i-1024)//32)%len(ratios)
                expected,expectedw=ref.mechanical(layout(er),layout(tr),p,inp,s,wheels);actual=State.from_buffer_copy(s);outw=(Wheel*4).from_buffer_copy(wheels)
                assert step(C.byref(p),C.byref(inp),C.byref(actual),outw)
                for field,typ in State._fields_:
                    a,b=getattr(actual,field),getattr(expected,field)
                    if typ is Clutch:
                        assert a.mode==b.mode and bits(a.remaining)==bits(b.remaining) and bits(a.duration)==bits(b.duration),(name,i,field,a.mode,b.mode,a.remaining,b.remaining)
                    elif typ is C.c_float:
                        if bits(a)!=bits(b):raise AssertionError((name,i,field,a,b,'input',[(n,getattr(inp,n)) for n,t in Input._fields_[:-1]],'gear',s.gear,'clutch',s.clutch.mode,'state',[(n,getattr(s,n)) for n,t in State._fields_ if t is C.c_float]))
                    else:assert a==b,(name,i,field,a,b)
                assert [bits(w.omega) for w in expectedw]==[bits(w.omega) for w in outw],(name,i,'wheels',[w.omega for w in expectedw],[w.omega for w in outw])
                previous_state=actual;previous_wheels=outw;cases+=1
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,original_range='802577A8..8025845C',full_mechanical_state_cases=cases,stateful_continuation_steps=512,profiles=profiles,launch_curve=dict(initializer='80265EB0..80265EE4',object='8048A0EC',samples='8041F65C',count=5),limitations=['Earlier raw-input/throttle/timed virtual phases57708..577A4 are explicit supplied producers','Active rev-modulation deadline is rejected pending original timer/sine/event port','Actual scheduler, event/manual/automatic gear commit wrapper, profile upgrade selection are separate'])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.dol,a.attributes);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
