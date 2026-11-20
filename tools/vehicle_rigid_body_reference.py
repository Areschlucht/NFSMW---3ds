#!/usr/bin/env python3
"""Bounded unpatched original rigid-body integration/force comparisons.

No original bytes/tables bundled. Explicit caller state and Gekko PS helper model
are not a complete original game execution or physical parameter producer.
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
from map_recovery_contact_reference import OriginalContactReference
from vehicle_ppc_reference import DOL_SHA256


FIELDS=[('quaternion',4),('position',3),('velocity',3),('angular_velocity',3),
        ('orientation',16),('world_inverse_inertia',16),('force',3),('torque',3),('local_cg',3),('inertia',3)]
class State(ctypes.Structure):
    _fields_=[(name,ctypes.c_float*count) for name,count in FIELDS]+[('inverse_mass',ctypes.c_float),('status',ctypes.c_uint32),('flags',ctypes.c_uint32)]


class Parameters(ctypes.Structure):
    _fields_=[('mass',ctypes.c_float),('inverse_mass',ctypes.c_float),
              ('halfextent',ctypes.c_float*3),('inertia',ctypes.c_float*3)]


class Original(OriginalContactReference):
    OWNER=0x60001000
    STATE=0x60002000
    def __init__(self,raw,estimate=None):
        if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected original USA executable')
        self.wake=False;super().__init__(raw,estimate)
        self.extra_allowed=((0x80235030,0x80235aa8),(0x8026724c,0x80267264),(0x80234320,0x802343dc),
            (0x80193010,0x8019304c),(0x801930e8,0x8019310c),(0x80193154,0x80193178),
            (0x801931c0,0x801931dc),(0x80193200,0x8019321c),(0x801932e0,0x8019330c),
            (0x80193338,0x80193364),(0x801933d8,0x80193408),(0x801935a4,0x801935e8),
            (0x8031d704,0x8031d7fc),(0x80278bc0,0x80278c98),
            (0x801931dc,0x80193200),(0x802337f0,0x80233c2c),(0x80193814,0x80193a60),(0x80193420,0x80193458),(0x80212e50,0x80212ee4))
        from unicorn import UC_HOOK_MEM_WRITE
        def write(u,access,address,size,value,_):
            if not any(a<=address and address+size<=b for a,b in
                ((0x7000f000,0x70010000),(self.OWNER,self.OWNER+0x140),(self.STATE,self.STATE+0xb0))):
                raise ValueError(f'Original write outside state/stack: {address:08x}')
        self.u.hook_add(UC_HOOK_MEM_WRITE,write)
    def _hook(self,u,pc,size,data):
        if pc==0x80234360:
            # Arithmetic flag clear has executed. The registry/event side effect
            # is explicitly observed, not fabricated or made part of the solver.
            self.wake=True;u.reg_write(self.reg.UC_PPC_REG_PC,0x802343c8);return
        super()._hook(u,pc,size,data)
    def call(self,state,dt=None,force=None,point=None,torque=None,matrix=None,raise_y=None):
        self.pair1={};self.instructions=0;self.wake=False;u=self.u;r=self.reg
        owner=bytearray(0x140);body=bytearray(0xb0)
        struct.pack_into('>I',owner,0x88,self.OWNER+0xf0);struct.pack_into('>I',owner,0xf0,self.STATE)
        struct.pack_into('>16f',owner,0xa0,*state.world_inverse_inertia);struct.pack_into('>3f',owner,0x100,*state.local_cg)
        for name,at in [('quaternion',0),('position',0x10),('velocity',0x20),('angular_velocity',0x30),
                        ('inertia',0x40),('force',0x50),('torque',0x60),('orientation',0x70)]:
            values=getattr(state,name);struct.pack_into('>'+str(len(values))+'f',body,at,*values)
        struct.pack_into('>f',body,0x3c,state.inverse_mass);struct.pack_into('>H',body,0x1c,state.flags);body[0x5d]=state.status
        u.mem_write(self.OWNER,bytes(owner));u.mem_write(self.STATE,bytes(body));u.mem_write(0x7000f000,bytes(4096))
        u.reg_write(r.UC_PPC_REG_1,0x7000ff00);u.reg_write(r.UC_PPC_REG_3,self.OWNER);u.reg_write(r.UC_PPC_REG_LR,0x6000fff0)
        if matrix is not None:
            u.mem_write(0x60010000,struct.pack('>16f',*matrix))
            u.reg_write(r.UC_PPC_REG_4,0x60010000);entry=0x802337f0
        elif raise_y is not None:self.putfloating(1,raise_y);entry=0x8026724c
        elif force is not None and torque is not None:
            u.mem_write(self.OWNER+0x120,struct.pack('>3f',*force));u.mem_write(self.OWNER+0x130,struct.pack('>3f',*torque))
            u.reg_write(r.UC_PPC_REG_4,self.OWNER+0x120);u.reg_write(r.UC_PPC_REG_5,self.OWNER+0x130);entry=0x80235030
        elif dt is not None:self.putfloating(1,dt);entry=0x802352e4
        elif torque is not None:
            u.mem_write(self.OWNER+0x120,struct.pack('>3f',*torque))
            u.reg_write(r.UC_PPC_REG_4,self.OWNER+0x120);entry=0x802350a8
        else:
            u.mem_write(self.OWNER+0x120,struct.pack('>3f',*force));u.mem_write(self.OWNER+0x130,struct.pack('>3f',*point))
            u.reg_write(r.UC_PPC_REG_4,self.OWNER+0x120);u.reg_write(r.UC_PPC_REG_5,self.OWNER+0x130);entry=0x80235220
        u.emu_start(entry,0x6000fff0,count=30000,timeout=200000)
        if u.reg_read(r.UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Original integration exceeded budget')
        result=State.from_buffer_copy(bytes(state));body=bytes(u.mem_read(self.STATE,0xb0));owner=bytes(u.mem_read(self.OWNER,0x140))
        for name,at in [('quaternion',0),('position',0x10),('velocity',0x20),('angular_velocity',0x30),
                        ('inertia',0x40),('force',0x50),('torque',0x60),('orientation',0x70)]:
            values=getattr(result,name);values[:]=struct.unpack_from('>'+str(len(values))+'f',body,at)
        result.world_inverse_inertia[:]=struct.unpack_from('>16f',owner,0xa0)
        result.status=body[0x5d];result.flags=struct.unpack_from('>H',body,0x1c)[0]
        return result,self.wake

    def parameters(self,mass,extent,tensor):
        self.pair1={};self.instructions=0;u=self.u;r=self.reg
        u.mem_write(self.OWNER,bytes(0x200));u.mem_write(self.STATE,bytes(0xb0))
        u.mem_write(self.OWNER+0x188,struct.pack('>I',self.STATE))
        u.mem_write(self.STATE+0x10,struct.pack('>3h',*extent))
        u.mem_write(0x7000f000,bytes(4096));u.reg_write(r.UC_PPC_REG_1,0x7000fe00)
        u.reg_write(r.UC_PPC_REG_31,self.OWNER)
        u.emu_start(0x80212e50,0x80212ee4,count=1000,timeout=200000)
        half=struct.unpack('>3f',u.mem_read(0x7000fe18,12))
        u.mem_write(self.OWNER,struct.pack('>3f',*tensor))
        u.reg_write(r.UC_PPC_REG_3,self.STATE+0x80);u.reg_write(r.UC_PPC_REG_4,self.OWNER)
        u.reg_write(r.UC_PPC_REG_LR,0x6000fff0)
        self.putfloating(1,mass)
        for i,x in enumerate(half):self.putfloating(i+2,x)
        u.emu_start(0x80278bc0,0x6000fff0,count=3000,timeout=200000)
        if u.reg_read(r.UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Original inertia producer exceeded budget')
        return half,struct.unpack('>3f',u.mem_read(self.STATE+0x80,12))


def make_state(rng,index):
    s=State();s.quaternion[:]=(0,0,0,1)
    for a in (s.orientation,s.world_inverse_inertia):
        for i in range(4):a[i*5]=1
    s.inverse_mass=rng.choice([1,1/1500,1/1300,0]);s.inertia[:]=[rng.choice([0,1e-7,1e-6,2e-6,1,400,2000]) for _ in range(3)]
    for name,span in [('position',2000),('velocity',350),('angular_velocity',40),('force',20000),('torque',100),('local_cg',.5)]:
        getattr(s,name)[:]=[rng.uniform(-span,span) for _ in range(3)]
    s.status=index%17 if index%17<3 else 0;s.flags=rng.choice([0,0x40,2,0x42,0x100])
    if index%8==0:s.angular_velocity[:]=(0,0,0);s.torque[:]=(0,0,0)
    if index%4:
        # Already normalized caller orientation; the original producer is not
        # inferred here. Nontrivial exact dyadic unit quaternions cover axes.
        s.quaternion[:]=rng.choice([(0,0,.6,.8),(0,.6,0,.8),(.6,0,0,.8),(.5,.5,.5,.5),(1,0,0,0),(0,1,0,0),(0,0,1,0),(.8,0,0,.6),(0,.8,0,.6),(0,0,.8,.6)])
        x,y,z,w=s.quaternion;s.orientation[:]=(1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w),0,
            2*(x*y-z*w),1-2*(x*x+z*z),2*(y*z+x*w),0,2*(x*z+y*w),2*(y*z-x*w),1-2*(x*x+y*y),0,0,0,0,1)
    return s


def export_parameters(attributes,bundle,output):
    from vehicle_attributes import VehicleAttributes
    from vehicle_verify_original import ATTR_SHA
    from vehicle_vlt_hash import vlt_hash
    from world_collision_response_shapes import body_packages
    raw=bundle.read_bytes();source=attributes.read_bytes()
    if hashlib.sha256(source).hexdigest()!=ATTR_SHA:raise ValueError('Unknown source attributes')
    if hashlib.sha256(raw).hexdigest()!='da02353de70dea3a8a51d6231e4efde15ab8c5c72eed6119a49bc9dad20b770b':raise ValueError('Unknown source physical body bundle')
    db=VehicleAttributes(source);packages={p['key']:p for p in body_packages(raw)}
    result={'bundle':str(bundle),'bundle_sha256':hashlib.sha256(raw).hexdigest(),'profiles':{}}
    for name,model in [('m3gtre46careerstart','BMWM3GTRE46'),('bmwm3gtre46','BMWM3GTRE46'),('cobaltss','COBALTSS'),('gti','GTI'),('is300','IS300'),('punto','PUNTO')]:
        row=db.find('pvehicle',name);package=packages[vlt_hash(model)];bound=package['bounds'][0]
        entry={'model_name':model,'model_key':f'{package["key"]:08x}','physical_halfextent_mm':bound['half_extents_raw'],
               'bound_package_offset':package['source_offset'],'bound_package_sha256':package['source_sha256'],'root_offset':bound['source_offset'],
               'mass':db.field_value(row,'MASS'),'tensor_scale':db.field_value(row,'TENSOR_SCALE')}
        binding=db.field_value(row,'rigidbodyspecs');ref=binding['value'];spec=db.collections[(ref['class_key'],ref['collection_key'])]
        entry.update(rigidbodyspecs=binding,local_cg=db.field_value(spec,'CG'),gravity=db.field_value(spec,'GRAVITY'),collision_box_pad=db.field_value(spec,'COLLISION_BOX_PAD'))
        for key in ('DRAG','DRAG_ANGULAR','NATURAL_ANGULAR_DAMPING','SLEEP_VELOCITY'):entry[key.lower()]=db.field_value(spec,key)
        result['profiles'][name]=entry
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')


def verify(dol,output,cases,dolphin=None):
    root=Path(__file__).resolve().parents[1]
    from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
    estimate=DolphinFrsqrteReference(dolphin) if dolphin else None
    ref=Original(dol.read_bytes(),estimate);rng=random.Random(0x352e4);errors=[];count=0
    with tempfile.TemporaryDirectory(prefix='nfsmw-rigid-body-') as tmp:
        libpath=Path(tmp)/'body.so'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_original_rigid_body.c'),str(root/'source_bmw/mw_gekko_math.c'),'-lm','-o',str(libpath)],check=True)
        lib=ctypes.CDLL(str(libpath));lib.mw_original_rigid_body_integrate.argtypes=[ctypes.POINTER(State),ctypes.c_float];lib.mw_original_rigid_body_integrate.restype=ctypes.c_bool
        lib.mw_original_rigid_body_add_force.argtypes=[ctypes.POINTER(State),ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_bool)];lib.mw_original_rigid_body_add_force.restype=ctypes.c_bool
        lib.mw_original_rigid_body_add_wrench.argtypes=[ctypes.POINTER(State),ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_bool)]
        lib.mw_original_rigid_body_add_wrench.restype=ctypes.c_bool
        lib.mw_original_rigid_body_raise_position.argtypes=[ctypes.POINTER(State),ctypes.c_float];lib.mw_original_rigid_body_raise_position.restype=ctypes.c_bool
        lib.mw_original_rigid_body_set_orientation.argtypes=[ctypes.POINTER(State),ctypes.POINTER(ctypes.c_float)]
        lib.mw_original_rigid_body_set_orientation.restype=ctypes.c_bool
        lib.mw_original_rigid_body_add_torque.argtypes=[ctypes.POINTER(State),ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_bool)]
        lib.mw_original_rigid_body_add_torque.restype=ctypes.c_bool
        lib.mw_original_rigid_body_parameters.argtypes=[ctypes.c_float,ctypes.POINTER(ctypes.c_int16),ctypes.POINTER(ctypes.c_float),ctypes.POINTER(Parameters)]
        lib.mw_original_rigid_body_parameters.restype=ctypes.c_bool
        for index in range(cases):
            original=make_state(rng,index);dt=ctypes.c_float(rng.choice([0,1/120,1/60,1/30,.1])).value
            expected,_=ref.call(original,dt=dt);actual=State.from_buffer_copy(bytes(original))
            if not lib.mw_original_rigid_body_integrate(ctypes.byref(actual),dt):raise AssertionError('Native rejected supported reference input')
            for name,_ in FIELDS:
                a=bytes(getattr(actual,name));b=bytes(getattr(expected,name))
                if a!=b:errors.append({'case':index,'kind':'integrate','field':name,'actual':list(getattr(actual,name)),'expected':list(getattr(expected,name))})
            if (actual.status,actual.flags)!=(expected.status,expected.flags):errors.append({'case':index,'field':'flags/status'})
            force=[rng.uniform(-10000,10000) for _ in range(3)];point=[rng.uniform(-5,5)+original.position[i] for i in range(3)]
            expected,wake=ref.call(original,force=force,point=point);actual=State.from_buffer_copy(bytes(original));aw=ctypes.c_bool()
            lib.mw_original_rigid_body_add_force(ctypes.byref(actual),(ctypes.c_float*3)(*force),(ctypes.c_float*3)(*point),ctypes.byref(aw))
            for name,_ in FIELDS:
                if bytes(getattr(actual,name))!=bytes(getattr(expected,name)):errors.append({'case':index,'kind':'force','field':name,'actual':list(getattr(actual,name)),'expected':list(getattr(expected,name))})
            if (actual.status,actual.flags,aw.value)!=(expected.status,expected.flags,wake):errors.append({'case':index,'kind':'force','field':'flags/status/wake'})
            expected,wake=ref.call(original,torque=force);actual=State.from_buffer_copy(bytes(original));aw=ctypes.c_bool()
            if not lib.mw_original_rigid_body_add_torque(ctypes.byref(actual),(ctypes.c_float*3)(*force),ctypes.byref(aw)):raise AssertionError('Native torque rejection')
            for name,_ in FIELDS:
                if bytes(getattr(actual,name))!=bytes(getattr(expected,name)):errors.append({'case':index,'kind':'torque','field':name})
            if (actual.status,actual.flags,aw.value)!=(expected.status,expected.flags,wake):errors.append({'case':index,'kind':'torque','field':'flags/status/wake'})
            expected,wake=ref.call(original,force=force,torque=point);actual=State.from_buffer_copy(bytes(original));aw=ctypes.c_bool()
            if not lib.mw_original_rigid_body_add_wrench(ctypes.byref(actual),(ctypes.c_float*3)(*force),(ctypes.c_float*3)(*point),ctypes.byref(aw)):raise AssertionError('Native wrench rejection')
            if bytes(actual)!=bytes(expected) or aw.value!=wake:errors.append({'case':index,'kind':'wrench'})
            amount=ctypes.c_float(rng.uniform(-1,1)).value;expected,_=ref.call(original,raise_y=amount);actual=State.from_buffer_copy(bytes(original))
            if not lib.mw_original_rigid_body_raise_position(ctypes.byref(actual),amount) or bytes(actual)!=bytes(expected):errors.append({'case':index,'kind':'raise_y'})
            mass=ctypes.c_float(rng.uniform(200,10000)).value
            extent=[rng.randint(1,32767) for _ in range(3)];tensor=[rng.uniform(.1,4) for _ in range(3)]
            half,inertia=ref.parameters(mass,extent,tensor);p=Parameters()
            if not lib.mw_original_rigid_body_parameters(mass,(ctypes.c_int16*3)(*extent),(ctypes.c_float*3)(*tensor),ctypes.byref(p)):raise AssertionError('Native parameter rejection')
            for name,expected in [('halfextent',half),('inertia',inertia)]:
                if bytes(getattr(p,name))!=struct.pack('=3f',*expected):errors.append({'case':index,'kind':'parameters','field':name,'actual':list(getattr(p,name)),'expected':list(expected)})
            if estimate:
                expected,_=ref.call(original,matrix=original.orientation);actual=State.from_buffer_copy(bytes(original))
                if not lib.mw_original_rigid_body_set_orientation(ctypes.byref(actual),original.orientation):raise AssertionError('Native matrix rejection')
                for name,_ in FIELDS:
                    if bytes(getattr(actual,name))!=bytes(getattr(expected,name)):errors.append({'case':index,'kind':'orientation','field':name,'actual':list(getattr(actual,name)),'expected':list(getattr(expected,name))})
                count+=1
            count+=6
    report={'dol_sha256':DOL_SHA256,'calls':count,'integration_cases':cases,'force_cases':cases,'parameter_cases':cases,'torque_cases':cases,'wrench_cases':cases,'vertical_correction_cases':cases,'orientation_cases':cases if estimate else 0,'float_bit_mismatches':len(errors),
        'errors':errors[:24],'original_windows':[{'start':f'{a:08x}','end':f'{b:08x}','sha256':hashlib.sha256(ref.dol.read(a,b-a)).hexdigest()} for a,b in ((0x802352e4,0x80235aa8),(0x80235220,0x802352e0),(0x802350a8,0x8023510c),(0x80235030,0x802350a8),(0x8026724c,0x80267264),(0x8031d704,0x8031d7fc),(0x80278bc0,0x80278c98),
            (0x801931dc,0x80193200),(0x802337f0,0x80233c2c),(0x80193814,0x80193a60),(0x80193420,0x80193458),(0x80212e50,0x80212ee4))],
        'dolphin_reference':{'commit':'86d554802d7560acf12b5c5a2b3acb344069b5ce','enabled':estimate is not None},
        'limits':['Explicit synthetic body/provider state, not full game telemetry or original scheduler',
                  'Original force wake registry/event side effect observed after exact flag clear; external dispatch not executed',
                  'Gekko paired-single functional model excludes FPSCR/subnormal/exception modes and rare binary64 FMA ties']}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('calls','float_bit_mismatches')}))
    if errors:raise SystemExit(1)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--attributes',type=Path);p.add_argument('--body-bundle',type=Path);p.add_argument('--parameter-output',type=Path);p.add_argument('--dolphin-reference',type=Path);p.add_argument('--cases',type=int,default=1024);a=p.parse_args()
    if not 1<=a.cases<=10000:raise ValueError('Invalid bounded case count')
    if any((a.attributes,a.body_bundle,a.parameter_output)):
        if not all((a.attributes,a.body_bundle,a.parameter_output)):p.error('Parameter export needs attributes, body-bundle and parameter-output')
        export_parameters(a.attributes,a.body_bundle,a.parameter_output)
    verify(a.dol,a.output,a.cases,a.dolphin_reference)
