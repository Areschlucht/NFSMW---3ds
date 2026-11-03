#!/usr/bin/env python3
"""Compare portable full contacted-wheel solver with original instruction traces.

Exact solver comparisons use original executable math callbacks. A separate
runtime-default comparison reports libm precision differences explicitly.
"""
import argparse
import ctypes as C
import hashlib
import json
import math
import random
import struct
import subprocess
import tempfile
from pathlib import Path
from vehicle_attributes import VehicleAttributes
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference,COMMIT
from vehicle_ppc_reference import OriginalPpcReference,DOL_SHA256
from vehicle_verify_original import ATTR_SHA
from vehicle_vlt_hash import vlt_hash as h

class BrakeState(C.Structure):
    _fields_=[(n,C.c_float) for n in ['radius','normal','hand','omega','drive','brake','accel']]+[(n,C.c_uint) for n in ['axle','locked','direction']]
CONTACT_FLOATS=['load','lateral','longitudinal','lat_grip','grip','residual','previous','slip','traction','angle','last_lateral','lat_scale','long_scale','budget','curve','combined','coupling']
class Wheel(C.Structure):_fields_=[('brake',BrakeState),('index',C.c_uint)]+[(n,C.c_float) for n in CONTACT_FLOATS]
class Input(C.Structure):_fields_=[(n,C.c_float) for n in ['lateral','longitudinal','vehicle_f3','load','dt']]
class BrakeAttrs(C.Structure):_fields_=[('normal',C.c_float*2),('hand',C.c_float),('lock',C.c_float*2)]
class Calibration(C.Structure):_fields_=[(n,C.c_float) for n in ['normal','hand','lock','resistance','inertia']]
class Parameters(C.Structure):_fields_=[('static',C.c_float*2),('dynamic',C.c_float*2),('scale',C.c_float*2),('brakes',BrakeAttrs),('calibration',Calibration),('curves',C.c_void_p),('surface_lateral',C.c_float),('surface_drive',C.c_float),('surface_rolling',C.c_float)]
UNARY=C.CFUNCTYPE(C.c_float,C.c_float,C.c_void_p)
BINARY=C.CFUNCTYPE(C.c_float,C.c_float,C.c_float,C.c_void_p)
class Math(C.Structure):_fields_=[('sqrt',UNARY),('angle',BINARY),('sin',UNARY),('context',C.c_void_p)]
BRAKE_MAP={'radius':0xc4,'normal':0xc8,'hand':0xcc,'omega':0xd0,'drive':0xe0,'brake':0xe4,'accel':0x108,'axle':0x10c,'locked':0x134,'direction':0x138}
FLOAT_MAP=dict(zip(CONTACT_FLOATS,[0xd4,0xd8,0xdc,0xe8,0xec,0xf4,0xfc,0xf0,0x110,0x118,0x130,0x11c,0x120,0x124,0x128,0x12c,0x13c]))

def raw_state(wheel):
    raw=bytearray(0x140)
    for n,off in BRAKE_MAP.items():struct.pack_into('>I' if n in ['axle','locked','direction'] else '>f',raw,off,getattr(wheel.brake,n))
    for n,off in FLOAT_MAP.items():struct.pack_into('>f',raw,off,getattr(wheel,n))
    struct.pack_into('>I',raw,0xf8,wheel.index);return raw

def verify(dol,attributes,dolphin):
    raw=attributes.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ATTR_SHA:raise ValueError('Unexpected attributes')
    db=VehicleAttributes(raw);ref=OriginalPpcReference(dol.read_bytes());ref.initialize_contact_curves();rng=random.Random(200514)
    def layout(row):return bytes(db.bin[row['layout']:row['layout']+db.classes[row['class_key']]['base_size']])
    def bits(v):return struct.pack('>f',v)
    root=Path(__file__).resolve().parents[1];cases=0;rows=0;angle_cases=0;default_max_error=0;default_differences=0;default_max_relative=0;failures=[];scale_cases=0;default_discrete_mismatches=0;default_max_spin_error=0;default_field_differences=0;free_cases=0
    with tempfile.TemporaryDirectory(prefix='mw-full-contact-') as temporary,DolphinFrsqrteReference(dolphin) as estimate:
        library=Path(temporary)/'contact.so';sources=['contact','brakes','lateral','friction','contact_scale']
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),*[str(root/('source_bmw/mw_physics_'+s+'.c')) for s in sources],str(root/'source_bmw/mw_gekko_math.c'),'-lm','-o',str(library)],check=True)
        impl=C.CDLL(str(library));step=impl.mw_physics_contact_step;step.argtypes=[C.POINTER(Wheel),C.POINTER(Input),C.POINTER(Parameters),C.POINTER(Math)];step.restype=C.c_bool
        free=impl.mw_physics_contact_free_step;free.argtypes=[C.POINTER(Wheel),C.POINTER(Parameters),C.c_float];free.restype=C.c_bool
        angle=impl.mw_physics_contact_angle_turns;angle.argtypes=[C.c_float,C.c_float];angle.restype=C.c_float
        class ScaleInput(C.Structure):_fields_=[('speed',C.c_float),('gear',C.c_uint),('mode',C.c_int),('effect',C.c_float),('extra',C.c_float),('include_extra',C.c_int)]
        class Scales(C.Structure):_fields_=[(n,C.c_float) for n in ['budget','curve','grip','coupling']]
        prepare=impl.mw_physics_contact_scales;prepare.argtypes=[C.POINTER(ScaleInput),C.POINTER(Scales)];prepare.restype=None
        for speed in [0,.1,10,20,38,71,100]+[rng.uniform(0,200) for _ in range(100)]:
            for mode in [0,1,2]:
                for gear in [0,1,2,7]:
                    scale_input=ScaleInput(speed,gear,mode,0,0,0);scales=Scales();prepare(C.byref(scale_input),C.byref(scales))
                    original=ref.contact_scale_producers(scale_input.speed,mode,gear)
                    for name,value in zip(['budget','curve','grip'],original):
                        assert bits(value)==bits(getattr(scales,name)),('scale',speed,mode,gear,name,value,getattr(scales,name))
                    scale_cases+=1
        for i in range(2048):
            a=C.c_float(rng.uniform(-200,200)).value;b=C.c_float(rng.uniform(-200,200)).value
            original=ref.scalar_math('angle',a,second=b)
            assert bits(original)==bits(angle(a,b)),('angle',a,b,original,angle(a,b));angle_cases+=1
        def callback(kind,value,second=0):
            try:return ref.scalar_math(kind,value,estimate,second)
            except Exception as e:failures.append(str(e));return float('nan')
        sqrt_cb=UNARY(lambda value,_:callback('sqrt',value));angle_cb=BINARY(lambda a,b,_:callback('angle',a,b));sin_cb=UNARY(lambda value,_:callback('sin',value));original_math=Math(sqrt_cb,angle_cb,sin_cb,None)
        surfaces=['asphalt','grass','gravel','concrete']
        for tire in db.collections.values():
            if tire['class_key']!=h('tires'):continue
            try:brake=db.find('brakes',tire['key'])
            except KeyError:continue
            t=db.fields(tire);b=db.fields(brake);rows+=1
            for index in range(4):
                for scenario in range(24):
                    surface=db.find('simsurface',surfaces[scenario%4]);sf=db.fields(surface)
                    params=Parameters(*[(C.c_float*2)(*t[k]['value']) for k in ['STATIC_GRIP','DYNAMIC_GRIP','GRIP_SCALE']],BrakeAttrs((C.c_float*2)(*b['BRAKES']['value']),b['EBRAKE']['value'],(C.c_float*2)(*b['BRAKE_LOCK']['value'])),Calibration(4,10,1.2,100,10),None,sf['LATERAL_GRIP']['value'],sf['DRIVE_GRIP']['value'],sf['ROLLING_RESISTANCE']['value'])
                    speed=rng.choice([-30,-.5,0,.5,1.001,2,5,20,50]);lat=rng.choice([-100,-10,-1,0,1,10,100]);load=rng.choice([0,1000,4000,10000]);radius=.3433
                    state=Wheel();state.index=index;state.brake=BrakeState(radius,rng.choice([0,.3,1]),rng.choice([0,.5,1]) if index>1 else 0,rng.choice([0,speed/radius,rng.uniform(-200,200)]),rng.uniform(-3000,3000),rng.uniform(-100,100),rng.uniform(-20,20),index>>1,rng.randrange(2),rng.randrange(3))
                    for n,v in dict(load=rng.choice([0,load]),lat_grip=rng.choice([.85,1,1.1]),grip=rng.choice([.7,1,1.3]),residual=rng.uniform(-20,20),previous=speed+rng.choice([-.2,0,.2]),traction=rng.choice([.2,.8,1]),lat_scale=rng.choice([.8,1,1.2]),long_scale=rng.choice([.8,1,1.2]),budget=rng.choice([.5,10000]),curve=rng.choice([.8,1,1.2]),combined=rng.choice([.8,1,1.2]),coupling=rng.choice([0,.15,.2,1])).items():setattr(state,n,v)
                    original_input=bytes(state);arguments=Input(lat,speed,abs(speed),load,rng.choice([1/120,1/60]))
                    returned,out=ref.contacted_wheel(layout(tire),layout(brake),layout(surface),raw_state(state),[getattr(arguments,n) for n in ['lateral','longitudinal','vehicle_f3','load','dt']],estimate)
                    assert step(C.byref(state),C.byref(arguments),C.byref(params),C.byref(original_math));assert not failures,failures
                    for n,offset in BRAKE_MAP.items():
                        actual=struct.pack('>I' if n in ['axle','locked','direction'] else '>f',getattr(state.brake,n))
                        if actual!=out[offset:offset+4]:raise AssertionError((db.label(tire['key']),index,scenario,'brake.'+n,actual.hex(),out[offset:offset+4].hex()))
                    for n,offset in FLOAT_MAP.items():
                        if bits(getattr(state,n))!=out[offset:offset+4]:raise AssertionError((db.label(tire['key']),index,scenario,n,bits(getattr(state,n)).hex(),out[offset:offset+4].hex(),dict(speed=speed,lat=lat,load=load)))
                    portable=Wheel.from_buffer_copy(original_input);assert step(C.byref(portable),C.byref(arguments),C.byref(params),None)
                    for name,_ in BrakeState._fields_:
                        if name in ['axle','locked','direction']:default_field_differences+=int(getattr(portable.brake,name)!=getattr(state.brake,name))
                        else:default_field_differences+=int(bits(getattr(portable.brake,name))!=bits(getattr(state.brake,name)))
                    for name in CONTACT_FLOATS:default_field_differences+=int(bits(getattr(portable,name))!=bits(getattr(state,name)))
                    default_discrete_mismatches+=int(portable.brake.locked!=state.brake.locked or portable.brake.direction!=state.brake.direction)
                    default_max_spin_error=max(default_max_spin_error,abs(portable.brake.omega-state.brake.omega))
                    for n in ['lateral','longitudinal']:
                        expected=getattr(state,n);actual=getattr(portable,n);error=abs(actual-expected)
                        default_max_error=max(default_max_error,error);default_max_relative=max(default_max_relative,error/max(1,abs(expected)))
                        if bits(actual)!=bits(expected):default_differences+=1
                    if scenario%4==0:
                        airborne=Wheel.from_buffer_copy(original_input);source_free=ref.wheel_brake(layout(brake),raw_state(airborne),arguments.dt,True);assert free(C.byref(airborne),C.byref(params),arguments.dt)
                        for name,offset in BRAKE_MAP.items():
                            actual=struct.pack('>I' if name in ['axle','locked','direction'] else '>f',getattr(airborne.brake,name))
                            if actual!=source_free[offset:offset+4]:raise AssertionError(('free',db.label(tire['key']),name,actual.hex(),source_free[offset:offset+4].hex()))
                        for name,offset in FLOAT_MAP.items():
                            if bits(getattr(airborne,name))!=source_free[offset:offset+4]:raise AssertionError(('free',db.label(tire['key']),name,bits(getattr(airborne,name)).hex(),source_free[offset:offset+4].hex()))
                        free_cases+=1
                    cases+=1
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,dolphin_commit=COMMIT,original_contact_va='0x80246580',tire_brake_collections=rows,full_state_float_bit_cases=cases,free_wheel_full_state_float_bit_cases=free_cases,angle_float_bit_cases=angle_cases,scale_producer_float_bit_cases=scale_cases,runtime_default_force_differences=default_differences,runtime_default_field_bit_differences=default_field_differences,runtime_default_discrete_state_mismatches=default_discrete_mismatches,runtime_default_max_spin_error=default_max_spin_error,runtime_default_max_force_error=default_max_error,runtime_default_max_relative_force_error=default_max_relative,limitations=['original math callbacks are an independent check; runtime-default parity is reported separately','runtime default uses original angle quantization and independently implemented Gekko sqrt; target sine checked separately','synthetic wheel-state producers, not whole-vehicle handling traces'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);p.add_argument('--dolphin-reference',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.dol,a.attributes,a.dolphin_reference),indent=2))
