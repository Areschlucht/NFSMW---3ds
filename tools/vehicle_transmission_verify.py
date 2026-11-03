#!/usr/bin/env python3
"""Bounded original EngineRacer torque/engine-braking comparisons.

This supplies an explicit external Vehicle callback response; that callback's
producer is not recovered by this tool. Every scalar wrapper instruction and
original curve lookup executes from the SHA-pinned DOL. Checked PSQ ABI spills
are emulated through the shared reference's scalar PS0 preservation.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from vehicle_attributes import VehicleAttributes
from vehicle_ppc_reference import OriginalPpcReference, PSQ_ABI, DOL_SHA256
from vehicle_verify_original import ATTR_SHA
from vehicle_vlt_hash import vlt_hash as h

EXTRA_ABI={0x80256264:0xf3c10018,0x80256268:0xf3e10020,0x80256474:0xe3c10018,0x80256478:0xe3e10020,0x80255474:0xf3e10010,0x802554e8:0xe3e10010,
           0x802557f0:0xf3c10028,0x802557f4:0xf3e10030,
           0x802559fc:0xe3c10028,0x80255a00:0xe3e10030}

class TransmissionReference(OriginalPpcReference):
    OBJECT=0x81608000
    CALLBACK=0x8160c000
    def __init__(self,raw):
        PSQ_ABI.update(EXTRA_ABI)
        super().__init__(raw)
        from unicorn import UC_HOOK_CODE
        from unicorn.ppc_const import UC_PPC_REG_3
        self.mode=0
        self.uc.mem_write(self.CALLBACK,struct.pack('>I',0x4e800020))
        def callback(uc,address,size,unused):
            if address==self.CALLBACK:uc.reg_write(UC_PPC_REG_3,self.mode)
        self.uc.hook_add(UC_HOOK_CODE,callback,begin=self.CALLBACK,end=self.CALLBACK)
        self.emulate_abi=True
    def output_torque(self,layout,rpm,boost,scale,mode):
        u=self.uc;u.mem_write(self.ENGINE,layout);obj=bytearray(0x1b0)
        struct.pack_into('>I',obj,0x150,self.ENGINE)
        struct.pack_into('>I',obj,0x4c,0x8160a000)
        struct.pack_into('>f',obj,0x9c,boost);struct.pack_into('>f',obj,0x100,scale)
        u.mem_write(self.OBJECT,bytes(obj));u.mem_write(0x8160a000,bytes(4)+struct.pack('>I',0x8160a100))
        table=bytearray(0xc0);struct.pack_into('>I',table,0xbc,self.CALLBACK);u.mem_write(0x8160a100,bytes(table))
        self.mode=mode
        self.allowed=((0x8025546c,0x802554f4),(0x802240ac,0x80224268),(0x80058124,0x8005812c),(self.CALLBACK,self.CALLBACK+4))
        return self._call(0x8025546c,self.OBJECT,rpm)
    def engine_braking(self,layout,argument,rpm):
        from unicorn.ppc_const import UC_PPC_REG_FPR2
        self.uc.mem_write(self.ENGINE,layout);obj=bytearray(0x1b0);struct.pack_into('>I',obj,0x150,self.ENGINE)
        self.uc.mem_write(self.OBJECT,bytes(obj))
        self.uc.reg_write(UC_PPC_REG_FPR2,struct.unpack('>Q',struct.pack('>d',rpm))[0])
        self.allowed=((0x802557e8,0x80255a0c),(0x80058124,0x8005812c))
        return self._call(0x802557e8,self.OBJECT,argument)

    def reported_rpm(self,mode,gear,seconds,previous,target,inertia):
        from unicorn.ppc_const import UC_PPC_REG_FPR2,UC_PPC_REG_FPR3,UC_PPC_REG_FPR4
        for reg,value in [(UC_PPC_REG_FPR2,previous),(UC_PPC_REG_FPR3,target),(UC_PPC_REG_FPR4,inertia)]:
            self.uc.reg_write(reg,struct.unpack('>Q',struct.pack('>d',value))[0])
        self.allowed=((0x80256b8c,0x80256c38),)
        return self._call(0x80256b8c,mode,seconds,r4=gear)

    def commit_gear(self,layout,gear,clutch,delay,requested):
        obj=bytearray(0x1b0);struct.pack_into('>I',obj,0x164,self.ENGINE)
        struct.pack_into('>If',obj,0x88,gear,delay);struct.pack_into('>I',obj,0x19c,clutch)
        self.uc.mem_write(self.ENGINE,layout);self.uc.mem_write(self.OBJECT,bytes(obj))
        self.allowed=((0x8025607c,0x8025617c),(0x80058124,0x8005812c))
        self.write_ranges=((self.OBJECT,self.OBJECT+len(obj)),)
        try:result=self._call(0x8025607c,self.OBJECT,r4=requested)
        finally:self.write_ranges=()
        actual=bytes(self.uc.mem_read(self.OBJECT,len(obj)))
        changed=set(range(0x88,0x90))|set(range(0x19c,0x1a0))
        assert all(a==b for i,(a,b) in enumerate(zip(obj,actual)) if i not in changed)
        return bool(result),struct.unpack_from('>I',actual,0x88)[0],struct.unpack_from('>I',actual,0x19c)[0],struct.unpack_from('>f',actual,0x8c)[0]

    def inertia(self,layout,gear):
        self.uc.mem_write(self.ENGINE,layout)
        self.uc.mem_write(self.INSTANCE,bytes(8)+struct.pack('>I',self.ENGINE)+bytes(8))
        self.allowed=((0x80223afc,0x80223b3c),)
        return self._call(0x80223afc,self.INSTANCE,r4=gear!=1,float_result=True)
    def clutch_core(self,values,max_difference,coupling):
        from unicorn import UC_HOOK_CODE
        from unicorn.ppc_const import UC_PPC_REG_0,UC_PPC_REG_1,UC_PPC_REG_CR,UC_PPC_REG_31,UC_PPC_REG_FPR0,UC_PPC_REG_MSR,UC_PPC_REG_PC
        mode,clutch,omega,shaft,shaft_accel,inertia,torque,ratio,split,fraction,blend,previous=values
        u=self.uc;obj=bytearray(0x1b0);struct.pack_into('>I',obj,0x88,mode);struct.pack_into('>I',obj,0x19c,clutch)
        for offset,v in [(0xf0,omega),(0xf8,shaft),(0x108,previous)]:struct.pack_into('>f',obj,offset,v)
        struct.pack_into('>I',obj,0x164,self.ENGINE);layout=bytearray(132);struct.pack_into('>f',layout,0x70,split)
        u.mem_write(self.ENGINE,bytes(layout));u.mem_write(self.OBJECT,bytes(obj))
        u.mem_write(0x8041f684,struct.pack('>f',max_difference));u.mem_write(0x8041f658,struct.pack('>f',coupling))
        u.reg_write(UC_PPC_REG_1,self.STACK);u.reg_write(UC_PPC_REG_31,self.OBJECT);u.reg_write(UC_PPC_REG_0,mode)
        u.reg_write(UC_PPC_REG_MSR,0x2000)
        assert self.dol.u32(0x80257cbc)==0x2c000001
        u.reg_write(UC_PPC_REG_CR,(2 if mode==1 else 4 if mode>1 else 8)<<28)
        for reg,value in [(6,0),(12,shaft_accel),(19,inertia),(22,fraction),(24,blend),(27,0),(28,ratio),(29,torque),(30,0)]:
            u.reg_write(UC_PPC_REG_FPR0+reg,struct.unpack('>Q',struct.pack('>d',value))[0])
        self.allowed=((0x80257cc8,0x80257ef8),(0x802580f8,0x802580fc));self.write_ranges=((self.OBJECT,self.OBJECT+len(obj)),)
        def stop(uc,address,size,unused):uc.emu_stop()
        handle=u.hook_add(UC_HOOK_CODE,stop,begin=0x802580f8,end=0x802580f8)
        try:self.count=0;u.emu_start(0x80257cc8,0x80257ef8,count=10000,timeout=1000000)
        finally:u.hook_del(handle);self.write_ranges=()
        assert u.reg_read(UC_PPC_REG_PC) in(0x80257ef8,0x802580f8)
        floats=[struct.unpack('>d',struct.pack('>Q',u.reg_read(UC_PPC_REG_FPR0+r)))[0] for r in (27,30)]
        floats.append(struct.unpack('>f',bytes(u.mem_read(self.OBJECT+0x108,4)))[0])
        actual=bytes(u.mem_read(self.OBJECT,len(obj)))
        assert all(a==b for i,(a,b) in enumerate(zip(obj,actual)) if i not in range(0x108,0x110))
        return floats,struct.unpack_from('>I',actual,0x10c)[0]

    def clutch_update(self,mode,remaining,duration,gear,seconds,engine,shaft,throttle,idle):
        from unicorn.ppc_const import UC_PPC_REG_1,UC_PPC_REG_7,UC_PPC_REG_28,UC_PPC_REG_30,UC_PPC_REG_31,UC_PPC_REG_FPR0,UC_PPC_REG_MSR,UC_PPC_REG_PC
        u=self.uc;obj=bytearray(0x1b0)
        struct.pack_into('>I',obj,0x88,gear);struct.pack_into('>f',obj,0x90,throttle)
        struct.pack_into('>f',obj,0xf0,engine);struct.pack_into('>f',obj,0xf8,shaft)
        struct.pack_into('>Iff',obj,0x19c,mode,remaining,duration);u.mem_write(self.OBJECT,bytes(obj))
        for reg,value in [(UC_PPC_REG_1,self.STACK),(UC_PPC_REG_7,0x80400000),(UC_PPC_REG_28,self.OBJECT+0x19c),(UC_PPC_REG_30,self.OBJECT+0x19c),(UC_PPC_REG_31,self.OBJECT)]:u.reg_write(reg,value)
        u.reg_write(UC_PPC_REG_MSR,0x2000)
        idle_w=struct.unpack('>f',struct.pack('>f',idle*self.dol.f32(0x803fbb0c)))[0]
        for reg,value in [(10,remaining),(11,0),(21,idle_w),(25,seconds)]:u.reg_write(UC_PPC_REG_FPR0+reg,struct.unpack('>Q',struct.pack('>d',value))[0])
        self.write_ranges=((self.OBJECT,self.OBJECT+len(obj)),)
        try:
            for start,end in [(0x802578a8,0x80257988),(0x80257af0,0x80257ba8)]:
                self.allowed=((start,end),);self.count=0;u.emu_start(start,end,count=10000,timeout=1000000)
                assert u.reg_read(UC_PPC_REG_PC)==end
        finally:self.write_ranges=()
        actual=bytes(u.mem_read(self.OBJECT,len(obj)))
        assert all(a==b for i,(a,b) in enumerate(zip(obj,actual)) if i not in range(0x19c,0x1a8))
        mode,remaining,duration=struct.unpack_from('>Iff',actual,0x19c)
        blend=struct.unpack('>d',struct.pack('>Q',u.reg_read(UC_PPC_REG_FPR0+24)))[0]
        return mode,remaining,duration,blend

    def differential(self,speeds,contacts,base,locking,override):
        obj=struct.pack('>2f2I2f2I',*speeds,*contacts,base,locking,0xa5a5a5a5,0xa5a5a5a5)
        self.uc.mem_write(self.INSTANCE,obj);self.allowed=((0x80249ea4,0x8024a00c),)
        self.write_ranges=((self.INSTANCE,self.INSTANCE+32),)
        try:self._call(0x80249ea4,self.INSTANCE,r4=override)
        finally:self.write_ranges=()
        actual=bytes(self.uc.mem_read(self.INSTANCE,32));assert actual[:24]==obj[:24]
        return struct.unpack_from('>2f',actual,24)

    def speed_wheels(self,wheels):
        actor=bytearray(0x1cc)
        for i,w in enumerate(wheels):
            raw=bytearray(0x140)
            for off,value in [(0xd0,w.omega),(0x78,w.compression),(0x110,w.traction),(0xfc,w.previous),(0xc4,w.radius)]:struct.pack_into('>f',raw,off,value)
            struct.pack_into('>I',raw,0x134,w.locked);address=0x81610000+i*0x1000
            self.uc.mem_write(address,bytes(raw));struct.pack_into('>I',actor,0x1bc+i*4,address)
        return actor
    def wheel_omega(self,wheels,index):
        self.uc.mem_write(0x8160d000,bytes(self.speed_wheels(wheels)))
        self.allowed=((0x802479a0,0x80247a0c),)
        return self._call(0x802479a0,0x8160d000,r4=index,float_result=True)
    def driven_omega(self,wheels,split,gear,directional):
        actor=self.speed_wheels(wheels);struct.pack_into('>I',actor,4,0x8160a100)
        wheel_table=bytearray(0xb0);struct.pack_into('>I',wheel_table,0xac,0x802479a0)
        self.uc.mem_write(0x8160a100,bytes(wheel_table));self.uc.mem_write(0x8160d000,bytes(actor))
        obj=bytearray(0x1b0);struct.pack_into('>I',obj,0x118,0x8160d000)
        struct.pack_into('>I',obj,0x88,gear);struct.pack_into('>I',obj,0x164,self.ENGINE)
        struct.pack_into('>I',obj,0x54,0x8160b200);gear_table=bytearray(0x18)
        struct.pack_into('>hHI',gear_table,0x10,-0x50,0,0x80269eb4)
        self.uc.mem_write(0x8160b200,bytes(gear_table));self.uc.mem_write(self.OBJECT,bytes(obj))
        layout=bytearray(132);struct.pack_into('>f',layout,0x70,split);self.uc.mem_write(self.ENGINE,bytes(layout))
        self.allowed=((0x8025625c,0x80256484),(0x802479a0,0x80247a0c),(0x80269eb4,0x80269ebc))
        return self._call(0x8025625c,self.OBJECT,r4=directional,float_result=True)

def verify(dol,attributes):
    raw=attributes.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ATTR_SHA:raise ValueError('Unexpected attributes checksum')
    db=VehicleAttributes(raw);ref=TransmissionReference(dol.read_bytes());rng=random.Random(20051123)
    root=Path(__file__).resolve().parents[1]
    class Curve(ctypes.Structure):
        _fields_=[('values',ctypes.POINTER(ctypes.c_float)),('count',ctypes.c_size_t),('idle',ctypes.c_float),('maximum',ctypes.c_float),('redline',ctypes.c_float)]
    counts={'torque':0,'engine_braking':0,'reported_rpm':0,'gear_commit':0,'inertia':0,'clutch_core':0,'clutch_update':0,'differential':0,'wheel_omega':0,'driven_omega':0};rows=0;trace=[]
    def f32(v):return ctypes.c_float(v).value
    def bits(v):return struct.pack('>f',v)
    with tempfile.TemporaryDirectory(prefix='mw-transmission-') as temporary:
        so=Path(temporary)/'transmission.so'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_physics_transmission.c'),str(root/'source_bmw/mw_physics_engine.c'),'-lm','-o',str(so)],check=True)
        lib=ctypes.CDLL(str(so));torque=lib.mw_physics_transmission_output_torque_nm
        torque.argtypes=[ctypes.POINTER(Curve),ctypes.c_float,ctypes.c_float,ctypes.c_float,ctypes.c_uint];torque.restype=ctypes.c_float
        brake=lib.mw_physics_transmission_engine_braking;brake.argtypes=[ctypes.POINTER(Curve),ctypes.c_float,ctypes.c_float];brake.restype=ctypes.c_float
        reported=lib.mw_physics_transmission_reported_rpm;reported.argtypes=[ctypes.c_uint,ctypes.c_uint,*([ctypes.c_float]*4)];reported.restype=ctypes.c_float
        class Shift(ctypes.Structure):_fields_=[('gear',ctypes.c_uint),('clutch',ctypes.c_uint),('delay',ctypes.c_float)]
        commit=lib.mw_physics_transmission_commit_gear;commit.argtypes=[ctypes.POINTER(Shift),ctypes.c_int,ctypes.POINTER(ctypes.c_float),ctypes.c_size_t,ctypes.c_float];commit.restype=ctypes.c_bool
        effective_inertia=lib.mw_physics_transmission_inertia;effective_inertia.argtypes=[ctypes.c_float,ctypes.c_uint];effective_inertia.restype=ctypes.c_float
        class ClutchInput(ctypes.Structure):_fields_=[('gear',ctypes.c_uint),('clutch',ctypes.c_uint)]+[(name,ctypes.c_float) for name in ['omega','shaft','shaft_accel','inertia','torque','ratio','split','fraction','blend','previous']]
        class ClutchOutput(ctypes.Structure):_fields_=[('wheel',ctypes.c_float),('reaction',ctypes.c_float),('slip',ctypes.c_float),('negative',ctypes.c_uint)]
        core=lib.mw_physics_transmission_clutch_core;core.argtypes=[ctypes.POINTER(ClutchInput),ctypes.c_float,ctypes.c_float,ctypes.POINTER(ClutchOutput)];core.restype=ctypes.c_bool
        class ClutchState(ctypes.Structure):_fields_=[('mode',ctypes.c_uint),('remaining',ctypes.c_float),('duration',ctypes.c_float)]
        update=lib.mw_physics_transmission_clutch_update;update.argtypes=[ctypes.POINTER(ClutchState),ctypes.c_uint,*([ctypes.c_float]*5),ctypes.POINTER(ctypes.c_float)];update.restype=ctypes.c_bool
        class Differential(ctypes.Structure):_fields_=[('speeds',ctypes.c_float*2),('contacts',ctypes.c_uint*2),('base',ctypes.c_float),('locking',ctypes.c_float)]
        differential=lib.mw_physics_transmission_differential;differential.argtypes=[ctypes.POINTER(Differential),ctypes.c_bool,ctypes.POINTER(ctypes.c_float)];differential.restype=ctypes.c_bool
        class SpeedWheel(ctypes.Structure):_fields_=[(n,ctypes.c_float) for n in ['omega','compression','traction','previous','radius']]+[('locked',ctypes.c_uint)]
        wheel_omega=lib.mw_physics_transmission_engine_wheel_omega;wheel_omega.argtypes=[ctypes.POINTER(SpeedWheel)];wheel_omega.restype=ctypes.c_float
        driven_omega=lib.mw_physics_transmission_driven_omega;driven_omega.argtypes=[ctypes.POINTER(SpeedWheel),ctypes.c_float,ctypes.c_uint,ctypes.c_bool];driven_omega.restype=ctypes.c_float
        for engine in db.collections.values():
            if engine['class_key']!=h('engine'):continue
            e=db.fields(engine);values=e['TORQUE']['value']['values'];braking=e['ENGINE_BRAKING']['value']['values']
            if len(values)<2 or e['MAX_RPM']['value']<=e['IDLE']['value']:continue
            rows+=1
            layout=bytes(db.bin[engine['layout']:engine['layout']+96]);idle=e['IDLE']['value'];maximum=e['MAX_RPM']['value'];redline=e['RED_LINE']['value']
            for gear in (0,1,2,7):
                expected=ref.inertia(layout,gear);actual=effective_inertia(e['FLYWHEEL_MASS']['value'],gear)
                if bits(expected)!=bits(actual):raise AssertionError(('inertia',db.label(engine['key']),gear,expected,actual))
                counts['inertia']+=1
            array=(ctypes.c_float*len(values))(*values);curve=Curve(array,len(values),idle,maximum,redline)
            rpms=[idle-1000,idle,f32((idle+redline)/2),redline,maximum+1000,f32(rng.uniform(idle,maximum))]
            for rpm in rpms:
                for mode in (0,6,7):
                    for boost,scale in [(0,1),(.5,.75),(-1,0),(f32(rng.uniform(0,2)),f32(rng.uniform(0,1)))]:
                        expected=ref.output_torque(layout,rpm,boost,scale,mode);actual=torque(ctypes.byref(curve),rpm,boost,scale,mode)
                        if bits(expected)!=bits(actual):raise AssertionError(('torque',db.label(engine['key']),rpm,mode,boost,scale,expected,actual,bits(expected).hex(),bits(actual).hex()))
                        counts['torque']+=1
            if braking:
                array=(ctypes.c_float*len(braking))(*braking);curve=Curve(array,len(braking),idle,maximum,redline)
                for rpm in rpms:
                    for argument in (-500,0,500,f32(rng.uniform(-1000,1000))):
                        expected=ref.engine_braking(layout,argument,rpm);actual=brake(ctypes.byref(curve),argument,rpm)
                        if bits(expected)!=bits(actual):raise AssertionError(('braking',db.label(engine['key']),rpm,argument,expected,actual,bits(expected).hex(),bits(actual).hex()))
                        counts['engine_braking']+=1
                        if db.label(engine['key'])=='bmwm3gtre46' and argument==500:trace.append(dict(rpm=rpm,torque_argument=argument,braking_result=expected))
        for mode in (0,1):
            for gear in range(8):
                for seconds in (0,1e-7,.001,1/120,1/60,.1):
                    for previous,target,inertia in [(800,8500,10),(8500,800,10),(3000,0,2),(0,0,40),(rng.uniform(0,10000),rng.uniform(0,10000),rng.uniform(1,100))]:
                        seconds,previous,target,inertia=map(f32,(seconds,previous,target,inertia))
                        expected=ref.reported_rpm(mode,gear,seconds,previous,target,inertia)
                        actual=reported(mode,gear,seconds,previous,target,inertia)
                        if bits(expected)!=bits(actual):raise AssertionError(('reported_rpm',mode,gear,seconds,previous,target,inertia,expected,actual))
                        counts['reported_rpm']+=1
        for row in db.collections.values():
            if row['class_key']!=h('transmission'):continue
            fields=db.fields(row);ratios=fields['GEAR_RATIO']['value']['values']
            if not ratios:continue
            array=(ctypes.c_float*len(ratios))(*ratios);layout=bytes(db.bin[row['layout']:row['layout']+132]);speed=fields['SHIFT_SPEED']['value']
            for gear in range(len(ratios)):
                for requested in (-1,0,1,2,len(ratios)-1,len(ratios)):
                    for clutch in (0,1,2):
                        state=Shift(gear,clutch,.375)
                        expected=ref.commit_gear(layout,gear,clutch,.375,requested)
                        result=commit(ctypes.byref(state),requested,array,len(ratios),speed)
                        if (expected[0],expected[1],expected[2],bits(expected[3]))!=(result,state.gear,state.clutch,bits(state.delay)):
                            raise AssertionError(('commit',db.label(row['key']),gear,requested,clutch,expected,result,state.gear,state.clutch,state.delay))
                        counts['gear_commit']+=1
        for mode in (0,1,2,5):
            for clutch in (0,1,2):
                for index in range(128):
                    values=[mode,clutch,*map(f32,[rng.uniform(-1000,1000),rng.uniform(-1000,1000),rng.uniform(-10000,10000),rng.uniform(.1,5),rng.uniform(-1000,2000),rng.uniform(-15,15),rng.choice([0,.3,1]),rng.choice([.25,.5,.75,1]),rng.uniform(0,1),rng.uniform(-10000,10000)])]
                    inp=ClutchInput(*values);out=ClutchOutput()
                    expected,negative=ref.clutch_core(values,300,20)
                    assert core(ctypes.byref(inp),300,20,ctypes.byref(out))
                    actual=[out.wheel,out.reaction,out.slip]
                    if negative!=out.negative or [bits(v) for v in expected]!=[bits(v) for v in actual]:raise AssertionError(('clutch',values,expected,actual,[bits(v).hex() for v in expected],[bits(v).hex() for v in actual]))
                    counts['clutch_core']+=1
        # Exact sign-reversal/2000RPM thresholds and omega-clamp boundaries.
        threshold=ctypes.c_float(2000).value
        above=struct.unpack('>f',struct.pack('>I',struct.unpack('>I',struct.pack('>f',threshold))[0]+1))[0]
        below=struct.unpack('>f',struct.pack('>I',struct.unpack('>I',struct.pack('>f',threshold))[0]-1))[0]
        for omega in (-300.0000305175781,-300,-299.9999694824219,0,299.9999694824219,300,300.0000305175781):
            for previous in (-above,-threshold,-below,-0.0,0.0,below,threshold,above):
                values=[2,1,*map(f32,[omega,0,0,.5,100,3,.3,1,1,previous])]
                inp=ClutchInput(*values);out=ClutchOutput();expected,negative=ref.clutch_core(values,300,20)
                assert core(ctypes.byref(inp),300,20,ctypes.byref(out));actual=[out.wheel,out.reaction,out.slip]
                if negative!=out.negative or [bits(v) for v in expected]!=[bits(v) for v in actual]:raise AssertionError(('clutch_boundary',values,expected,actual))
                counts['clutch_core']+=1
        for gear in (0,1,2,4):
            for mode in (0,1,2):
                for seconds in (0,1/60,.1):
                    for remaining in (0,.05,.25):
                        for duration in (0,.05,.25):
                            for engine,shaft in [(0,0),(200,50),(1000,1000)]:
                                for throttle in (0,.1,1):
                                    seconds,remaining,duration,engine,shaft,throttle=map(f32,(seconds,remaining,duration,engine,shaft,throttle))
                                    state=ClutchState(mode,remaining,duration);blend=ctypes.c_float()
                                    expected=ref.clutch_update(mode,remaining,duration,gear,seconds,engine,shaft,throttle,800)
                                    assert update(ctypes.byref(state),gear,seconds,engine,shaft,throttle,800,ctypes.byref(blend))
                                    actual=(state.mode,state.remaining,state.duration,blend.value)
                                    if expected[0]!=actual[0] or [bits(v) for v in expected[1:]]!=[bits(v) for v in actual[1:]]:raise AssertionError(('clutch_update',gear,mode,seconds,remaining,duration,engine,shaft,throttle,expected,actual))
                                    counts['clutch_update']+=1
        for row in db.collections.values():
            if row['class_key']!=h('transmission'):continue
            fields=db.fields(row)
            for locking in fields['DIFFERENTIAL']['value']['values']:
                for base in (0,.5,1,fields['TORQUE_SPLIT']['value']):
                    for speeds in [(0,0),(10,10),(10,30),(-10,30),(-10,-30),(100,-100)]:
                        for contacted,override in [((1,1),False),((1,1),True),((0,1),False),((1,0),False)]:
                            base,locking=map(f32,(base,locking));inp=Differential((ctypes.c_float*2)(*speeds),(ctypes.c_uint*2)(*contacted),base,locking);output=(ctypes.c_float*2)()
                            expected=ref.differential(speeds,contacted,base,locking,override)
                            assert differential(ctypes.byref(inp),override,output)
                            if [bits(v) for v in expected]!=[bits(v) for v in output]:raise AssertionError(('differential',db.label(row['key']),speeds,contacted,base,locking,override,expected,list(output)))
                            counts['differential']+=1
        for index in range(1024):
            wheels=(SpeedWheel*4)(*(SpeedWheel(rng.uniform(-100,100),rng.choice([0,.1]),rng.choice([0,.5,1,1.1]),rng.uniform(-40,40),rng.choice([.25,.3433,.5]),rng.randrange(2)) for _ in range(4)))
            for i in range(4):
                expected=ref.wheel_omega(wheels,i);actual=wheel_omega(ctypes.byref(wheels[i]))
                if bits(expected)!=bits(actual):raise AssertionError(('wheel_omega',index,i,expected,actual))
                counts['wheel_omega']+=1
            split=f32(rng.choice([0,.25,.5,.75,1]));gear=rng.choice([0,1,2,7]);mode=bool(index&1)
            expected=ref.driven_omega(wheels,split,gear,mode);actual=driven_omega(wheels,split,gear,mode)
            if bits(expected)!=bits(actual):raise AssertionError(('driven_omega',index,split,gear,mode,expected,actual))
            counts['driven_omega']+=1
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,engine_collections=rows,float_bit_cases=counts,additional_psq_abi={f'{a:08x}':f'{w:08x}' for a,w in EXTRA_ABI.items()},external_callback='Vehicle mode is explicitly supplied; body is not emulated',bmw_braking_trace=trace,limitations=['isolated numerical/state stages and clutch core, not the complete engine update or whole-car integration','boost/state scale producers, Vehicle mode labels and broader clutch-mode transitions remain separate','automatic/manual request policy, generated shift tables, final wheel distribution and engine angular update remain unported','engine braking argument keeps caller units; original invalid-array fallback is rejected safely'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.dol,a.attributes),indent=2))
