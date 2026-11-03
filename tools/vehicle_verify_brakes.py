#!/usr/bin/env python3
"""Compare recovered wheel brake/lock transitions against original PPC."""
import argparse
import ctypes
import hashlib
import json
import random
import struct
import subprocess
import tempfile
from pathlib import Path
from vehicle_attributes import VehicleAttributes
from vehicle_ppc_reference import OriginalPpcReference,DOL_SHA256
from vehicle_verify_original import ATTR_SHA
from vehicle_vlt_hash import vlt_hash


def verify(dol,attributes):
    raw=attributes.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ATTR_SHA:raise ValueError('Unexpected attributes checksum')
    db=VehicleAttributes(raw);ref=OriginalPpcReference(dol.read_bytes());rng=random.Random(200510)
    class Attributes(ctypes.Structure):
        _fields_=[('normal',ctypes.c_float*2),('hand',ctypes.c_float),('lock',ctypes.c_float*2)]
    class Calibration(ctypes.Structure):
        _fields_=[('normal_scale',ctypes.c_float),('hand_scale',ctypes.c_float),('lock_scale',ctypes.c_float),('resistance',ctypes.c_float),('inertia',ctypes.c_float)]
    class State(ctypes.Structure):
        _fields_=[('radius',ctypes.c_float),('normal',ctypes.c_float),('hand',ctypes.c_float),('omega',ctypes.c_float),('drive',ctypes.c_float),('brake',ctypes.c_float),('acceleration',ctypes.c_float),('axle',ctypes.c_uint32),('locked',ctypes.c_uint32),('direction',ctypes.c_uint32)]
    mapping={'radius':0xc4,'normal':0xc8,'hand':0xcc,'omega':0xd0,'drive':0xe0,'brake':0xe4,'acceleration':0x108,'axle':0x10c,'locked':0x134,'direction':0x138}
    root=Path(__file__).resolve().parents[1];cases=0;rows=0;trace=[];grip_cases=0
    calibration=Calibration(4,10,1.2,100,10)
    def bits(v):return struct.pack('>f',v).hex()
    with tempfile.TemporaryDirectory(prefix='mw-original-brakes-') as temporary:
        lib=Path(temporary)/'brakes.so'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_physics_brakes.c'),str(root/'source_bmw/mw_physics_grip.c'),'-lm','-o',str(lib)],check=True)
        impl=ctypes.CDLL(str(lib))
        for function in ['mw_physics_brake_lock_raw','mw_physics_free_wheel_brake_step']:
            f=getattr(impl,function);f.argtypes=[ctypes.POINTER(Attributes),ctypes.POINTER(Calibration),ctypes.POINTER(State),ctypes.c_float];f.restype=None
        grip=impl.mw_physics_rear_grip_assist_raw;grip.argtypes=[ctypes.c_float]*5;grip.restype=ctypes.c_float
        values=[[0,.5,0,1,0],[.3490659,1,30,1,0],[.1,1,30,1,0],[.1,0,30,1,0]]+[[rng.uniform(-2,2),rng.choice([0,.5,1]),rng.uniform(-30,100),rng.uniform(0,3),rng.uniform(-1,1)] for _ in range(1024)]
        for value in values:
            value=[ctypes.c_float(v).value for v in value];original=ref.rear_grip_assist(value);portable=grip(*value)
            if bits(original)!=bits(portable):raise AssertionError(('rear-grip',value,original,portable))
            grip_cases+=1
        for row in db.collections.values():
            if row['class_key']!=vlt_hash('brakes'):continue
            f=db.fields(row);a=Attributes((ctypes.c_float*2)(*f['BRAKES']['value']),f['EBRAKE']['value'],(ctypes.c_float*2)(*f['BRAKE_LOCK']['value']));layout=bytes(db.bin[row['layout']:row['layout']+20]);rows+=1
            for axle in [0,1]:
                for normal,hand in [(0,0),(1,0),(0,1),(.5,.5),(1,1)]:
                    for omega in [-1000,-20,-.001,0,.001,20,1000]:
                        for step in [False,True]:
                            state=State(.3433,normal,hand,omega,rng.uniform(-2000,2000),rng.uniform(-100,100),rng.uniform(-10,10),axle,rng.randrange(2),rng.randrange(3))
                            original_state=bytearray(0x140)
                            for key,offset in mapping.items():struct.pack_into('>I' if key in ['axle','locked','direction'] else '>f',original_state,offset,getattr(state,key))
                            argument=ctypes.c_float(rng.choice([0,1/120,1/60]) if step else rng.choice([0,1000,10000,100000])).value
                            original=ref.wheel_brake(layout,original_state,argument,step)
                            getattr(impl,'mw_physics_free_wheel_brake_step' if step else 'mw_physics_brake_lock_raw')(ctypes.byref(a),ctypes.byref(calibration),ctypes.byref(state),argument)
                            for key,offset in mapping.items():
                                actual=struct.pack('>I' if key in ['axle','locked','direction'] else '>f',getattr(state,key))
                                if actual!=original[offset:offset+4]:raise AssertionError((db.label(row['key']),axle,normal,hand,omega,step,key,actual.hex(),original[offset:offset+4].hex()))
                            cases+=1
                            if db.label(row['key'])=='bmwm3gtre46' and not step and axle==1 and normal==0 and hand==1:trace.append(dict(initial_omega=omega,contact_force_argument=argument,locked=state.locked,result_omega=state.omega))
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,brake_collections=rows,lock_and_free_spin_cases=cases,rear_grip_assist_cases=grip_cases,comparison='exact float32 bits and integer state',lock_va='0x802462D0',spin_transition_va='0x802463B0',free_spin_va='0x8024644C',bmw_rear_handbrake_trace=trace,limitations=['contact tire solver and input routing are not emulated here','initialized calibration globals, not arbitrary game-time tuning states','no whole-vehicle handling fidelity claim'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.dol,a.attributes),indent=2))
