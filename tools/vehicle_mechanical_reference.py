#!/usr/bin/env python3
"""Compare original802455E0 ordered body forces with the native mechanical stage.

Executes unchanged original scalar instructions and the existing explicit Gekko
paired-single model. Only external body-interface getter/force submission are
supplied; power executes the pinned original library in a separate reference.
Original archives and executable are read-only and never embedded in outputs.
"""
import argparse
import ctypes as C
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import zlib

from map_recovery_contact_reference import OriginalContactReference
from vehicle_attributes import VehicleAttributes
from vehicle_dol import DolImage
from vehicle_export_contact import component_reference
from vehicle_ppc_reference import OriginalPpcReference,DOL_SHA256
from vehicle_verify_original import ATTR_SHA

ROOT=Path(__file__).resolve().parents[1]
class Vector(C.Structure):_fields_=[('x',C.c_float),('y',C.c_float),('z',C.c_float)]
class Params(C.Structure):_fields_=[(n,C.c_float) for n in ('drag','aero','cg','drag_multiplier','drag_height','exponent','minimum')]
class Input(C.Structure):
    _fields_=[('matrix',C.c_float*16),('velocity',Vector),('cg',Vector)]+[(n,C.c_float) for n in ('speed','throttle','contacts','drag_scale','aero_scale','front','rear')]+[('effect_present',C.c_bool),('effect',C.c_float)]
class Force(C.Structure):_fields_=[('force',Vector),('point',Vector),('kind',C.c_uint32)]
class Output(C.Structure):_fields_=[('count',C.c_uint32),('forces',Force*2)]
POWER=C.CFUNCTYPE(C.c_double,C.c_double,C.c_double,C.c_void_p)
class Math(C.Structure):_fields_=[('power',POWER),('context',C.c_void_p)]


class Reference(OriginalContactReference):
    def __init__(self,raw):
        super().__init__(raw,None)
        from unicorn import UC_HOOK_MEM_WRITE
        self.math=OriginalPpcReference(raw);self.calls=[];self.pow_calls=0
        self.extra_allowed=((0x802455e0,0x80245960),(0x80223adc,0x80223afc),
            (0x801931c0,0x801931dc),(0x80193088,0x801930a8),(0x801935a4,0x801935e8))
        def write(u,access,address,size,value,_):
            if not 0x7000f000<=address<address+size<=0x70010000:
                raise ValueError(f'Mechanical write escaped stack:{address:08x}')
        self.u.hook_add(UC_HOOK_MEM_WRITE,write)
    def _hook(self,u,address,size,data):
        from unicorn import ppc_const as r
        if address==0x6000f000:
            if u.reg_read(r.UC_PPC_REG_3)!=0x60002000:raise ValueError('Unexpected body getter receiver')
            u.reg_write(r.UC_PPC_REG_3,0x60003000);u.reg_write(r.UC_PPC_REG_PC,u.reg_read(r.UC_PPC_REG_LR));return
        if address==0x6000f010:
            if u.reg_read(r.UC_PPC_REG_3)!=0x60003000:raise ValueError('Unexpected force receiver')
            kinds={0x8024574c:1,0x80245934:2};lr=u.reg_read(r.UC_PPC_REG_LR)
            if lr not in kinds or len(self.calls)>=2:raise ValueError('Unexpected body force invocation')
            f=bytes(u.mem_read(u.reg_read(r.UC_PPC_REG_4),12));p=bytes(u.mem_read(u.reg_read(r.UC_PPC_REG_5),12))
            self.calls.append((kinds[lr],f,p));u.reg_write(r.UC_PPC_REG_PC,lr);return
        if address==0x8031cec0:
            self.putfloating(1,self.math.scalar_math('pow',self.floating(1),second=self.floating(2)))
            self.pow_calls+=1;u.reg_write(r.UC_PPC_REG_PC,u.reg_read(r.UC_PPC_REG_LR));return
        return super()._hook(u,address,size,data)
    def apply(self,p,x):
        from unicorn import ppc_const as r
        self.calls=[];self.pair1={};self.instructions=0;u=self.u
        owner=bytearray(0x90);struct.pack_into('>I',owner,0x38,0x60002000);struct.pack_into('>I',owner,0x7c,0x60006000)
        u.mem_write(0x60001000,bytes(owner))
        u.mem_write(0x60002000,bytes(4)+struct.pack('>I',0x60004000));u.mem_write(0x60003000,bytes(4)+struct.pack('>I',0x60005000))
        u.mem_write(0x600040a8,struct.pack('>h2xI',0,0x6000f000));u.mem_write(0x60005130,struct.pack('>h2xI',0,0x6000f010))
        chassis=bytearray(0x80);struct.pack_into('>f',chassis,0x5c,p.cg);struct.pack_into('>f',chassis,0x68,p.aero);struct.pack_into('>f',chassis,0x70,p.drag);u.mem_write(0x60006000,bytes(chassis))
        common=bytearray(0xd0);struct.pack_into('>16f',common,0,*x.matrix);struct.pack_into('>f',common,0x4c,x.throttle)
        struct.pack_into('>3f',common,0x50,x.velocity.x,x.velocity.y,x.velocity.z);struct.pack_into('>f',common,0x6c,x.contacts)
        struct.pack_into('>3f',common,0x70,x.cg.x,x.cg.y,x.cg.z);struct.pack_into('>f',common,0xbc,x.speed);u.mem_write(0x60007000,bytes(common))
        u.mem_write(0x60008010,struct.pack('>f',x.effect))
        for at,value in ((0x8041f280,p.drag_multiplier),(0x8041f284,p.drag_height),(0x8041f278,p.exponent),(0x8041f27c,p.minimum)):u.mem_write(at,struct.pack('>f',value))
        for reg,val in ((1,0x7000ff00),(3,0x60001000),(4,0x60007000),(5,0x60008000 if x.effect_present else 0)):
            u.reg_write(r.UC_PPC_REG_0+reg,val)
        u.reg_write(r.UC_PPC_REG_LR,0x6000fff0)
        for reg,val in ((1,x.drag_scale),(2,x.aero_scale),(3,x.front),(4,x.rear)):self.putfloating(reg,val)
        u.emu_start(0x802455e0,0x6000fff0,count=10000,timeout=1000000)
        if u.reg_read(r.UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Mechanical reference budget exhausted')
        return self.calls


def verify(dol,attributes,output):
    raw=dol.read_bytes();attr=attributes.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=DOL_SHA256 or hashlib.sha256(attr).hexdigest()!=ATTR_SHA:raise ValueError('Unknown source revision')
    image=DolImage(raw);db=VehicleAttributes(attr);ref=Reference(raw);rng=random.Random(4550);rows=[];cases=0;host_cases=0;host_mismatches=0;host_differences=[]
    with tempfile.TemporaryDirectory() as t:
        so=Path(t)/'mechanical.so'
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(ROOT/'include'),str(ROOT/'source_bmw/mw_original_vehicle_mechanical.c'),str(ROOT/'source_bmw/mw_original_power.c'),'-lm','-o',str(so)],check=True)
        lib=C.CDLL(str(so));native=lib.mw_vehicle_mechanical;native.argtypes=[C.POINTER(Params),C.POINTER(Input),C.POINTER(Output),C.POINTER(Math)];native.restype=C.c_bool
        power=POWER(lambda a,b,_:ref.math.scalar_math('pow',a,second=b));source_math=Math(power,None)
        host_power=POWER(lambda a,b,_:math.pow(a,b));host_math=Math(host_power,None)
        for name in ('m3gtre46careerstart','bmwm3gtre46','cobaltss','gti','is300','punto'):
            physical=db.find('pvehicle',name);chassis,binding=component_reference(db,physical,'chassis',0)
            fields={n:db.field_value(chassis,n) for n in ('DRAG_COEFFICIENT','AERO_COEFFICIENT','AERO_CG')}
            p=Params(*(fields[n]['value'] for n in fields),*(image.f32(a) for a in (0x8041f280,0x8041f284,0x8041f278,0x8041f27c)))
            packed=bytearray(128)+struct.pack('<7f',*(getattr(p,name) for name,_ in Params._fields_))
            struct.pack_into('<4s7I',packed,0,b'MMP1',1,len(packed),0,physical['key'],chassis['key'],128,7)
            packed[64:96]=bytes.fromhex(ATTR_SHA);packed[96:128]=bytes.fromhex(DOL_SHA256);struct.pack_into('<I',packed,12,zlib.crc32(packed[16:]))
            output.parent.mkdir(parents=True,exist_ok=True);profile_path=output.parent/(name+'.mmp')
            if profile_path.exists() and profile_path.read_bytes()!=packed:raise ValueError('Existing mechanical profile differs')
            profile_path.write_bytes(packed)
            before=cases
            for i in range(512):
                # Signed orthogonal/permuted axes and tilted unit frames keep
                # both real basis transforms and exact dyadic arithmetic covered.
                matrices=[(1,0,0,0,0,1,0,0,0,0,1,0),(0,0,-1,0,0,1,0,0,1,0,0,0),
                          (1,0,0,0,0,0,-1,0,0,1,0,0),(1,0,0,0,0,-1,0,0,0,0,-1,0),
                          (.6,0,-.8,0,0,1,0,0,.8,0,.6,0),
                          (1,0,0,0,0,.6,.8,0,0,-.8,.6,0)]
                m=(*matrices[i%len(matrices)],rng.choice([-100,.25,40]),rng.choice([0,6,25]),rng.choice([-20,0,120]),1)
                v=Vector(*(rng.choice([-64,-12,-1,0,1,9,64]) for _ in range(3)))
                x=Input((C.c_float*16)(*m),v,Vector(.125,.375,-.25),rng.choice([0,.00005,.0001,1,16,64]),rng.choice([0,.25,.5,1]),rng.choice([0,.25,.5,.75,1]),rng.choice([-1,0,.25,1,2]),rng.choice([-1,0,.25,1,2]),1.5,-1.225,i%3==0,rng.choice([-.5,0,1,4]))
                if i%7==0:p.drag_multiplier=rng.choice([.5,1,2,3]);p.drag_height=rng.choice([-.1,0,.5]);p.minimum=rng.choice([0,.4,1]);p.exponent=rng.choice([.5,1,2])
                expected=ref.apply(p,x);actual=Output();assert native(C.byref(p),C.byref(x),C.byref(actual),C.byref(source_math))
                if actual.count!=len(expected):raise AssertionError((name,i,'force count',actual.count,expected))
                for n,(kind,f,point) in enumerate(expected):
                    a=actual.forces[n]
                    gotf=struct.pack('>3f',a.force.x,a.force.y,a.force.z);gotp=struct.pack('>3f',a.point.x,a.point.y,a.point.z)
                    if a.kind!=kind or f!=gotf or point!=gotp:raise AssertionError({'profile':name,'case':i,'kind':kind,'expected_force':f.hex(),'native_force':gotf.hex(),'expected_point':point.hex(),'native_point':gotp.hex()})
                direct=Output();assert native(C.byref(p),C.byref(x),C.byref(direct),None)
                if bytes(direct)!=bytes(actual):raise AssertionError('Native positive powf branch differs from original dependency')
                host=Output();assert native(C.byref(p),C.byref(x),C.byref(host),C.byref(host_math));host_cases+=1
                for n,(_,f,point) in enumerate(expected):
                    a=host.forces[n]
                    mismatch=f!=struct.pack('>3f',a.force.x,a.force.y,a.force.z) or point!=struct.pack('>3f',a.point.x,a.point.y,a.point.z)
                    host_mismatches+=mismatch
                    if mismatch:host_differences.append({'profile':name,'case':i,'exponent':p.exponent,'expected_force':list(struct.unpack('>3f',f)),'host_force':[a.force.x,a.force.y,a.force.z]})
                cases+=1
            rows.append({'profile':name,'physical_key':f'{physical["key"]:08x}','chassis_key':f'{chassis["key"]:08x}','binding':binding,'fields':fields,'native_profile_sha256':hashlib.sha256(packed).hexdigest(),'cases':cases-before})
    report={'source_sha256':{'dol':DOL_SHA256,'attributes':ATTR_SHA},'original_range':'802455e0..80245960','cases':cases,'pow_calls':ref.pow_calls,'force_and_point_float_bit_mismatches':0,'native_default_float_bit_mismatches':0,'old_binary64_libm_cases':host_cases,'old_binary64_libm_force_call_mismatches':host_mismatches,'old_binary64_libm_differences':host_differences,'profiles':rows,
        'limits':['External original body-provider getter and force receiver supplied, not original rigid-body integration','Shared explicit paired-single model excludes exactGekkoFMA ties/FPSCR/subnormals','Native power covers positivefloat sourceexponents0,.5,1,2; othersrequireexplicitoriginalcallback orreject','No playerinputassist, accumulation,bottomout orwhole-car trajectories proved']}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'cases':cases,'native_default_float_bit_mismatches':0,'old_binary64_libm_force_call_mismatches':host_mismatches,'profiles':len(rows)}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('dol','attributes','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();verify(a.dol,a.attributes,a.output)
