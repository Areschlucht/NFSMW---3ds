#!/usr/bin/env python3
"""Verify initialized original lateral tire force curves and curve consumer."""
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
from vehicle_vlt_hash import vlt_hash as h


def verify(dol,attributes):
    raw=attributes.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ATTR_SHA:raise ValueError('Unexpected attributes source')
    db=VehicleAttributes(raw);ref=OriginalPpcReference(dol.read_bytes());ref.initialize_contact_curves();rng=random.Random(200512)
    root=Path(__file__).resolve().parents[1];cases=0;rows=0;trace=[]
    class Curves(ctypes.Structure):_fields_=[('samples',(ctypes.c_float*6)*7)]
    def bits(v):return struct.pack('>f',v).hex()
    with tempfile.TemporaryDirectory(prefix='mw-original-lateral-') as temporary:
        lib=Path(temporary)/'lateral.so'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_physics_lateral.c'),'-lm','-o',str(lib)],check=True)
        impl=ctypes.CDLL(str(lib));f=impl.mw_physics_lateral_curve_raw;f.argtypes=[ctypes.POINTER(Curves),*([ctypes.c_float]*4)];f.restype=ctypes.c_float
        curves=Curves.in_dll(impl,'mw_physics_original_lateral_curves')
        for row in range(7):
            original=ref.dol.read(0x8041f288+row*24,24)
            assert original==b''.join(struct.pack('>f',v) for v in curves.samples[row])
            object_bytes=bytes(ref.uc.mem_read(0x80489eb0+row*20,20))
            assert object_bytes==struct.pack('>IfffI',6,0,10,.5,0x8041f288+row*24)
        for tire in db.collections.values():
            if tire['class_key']!=h('tires'):continue
            t=db.fields(tire);layout=bytes(db.bin[tire['layout']:tire['layout']+80]);rows+=1
            for axle in [0,1]:
                grip=t['GRIP_SCALE']['value'][axle]
                for force in [-1,0,1000,4000,12500,20000]:
                    for degree in [0,.001,1,2,4,6,8,10,12,20,rng.uniform(0,100)]:
                        force=ctypes.c_float(force).value;turns=ctypes.c_float(degree/360).value;scale=ctypes.c_float(rng.choice([.5,1,1.5])).value
                        original=ref.lateral_curve(layout,axle,scale,force,turns);portable=f(ctypes.byref(curves),force,turns,grip,scale)
                        if bits(original)!=bits(portable):raise AssertionError((db.label(tire['key']),axle,force,degree,scale,original,portable,bits(original),bits(portable)))
                        cases+=1
                        if db.label(tire['key'])=='bmwm3gtre46' and axle==1 and force==4000:trace.append(dict(angle_degrees=degree,wheel_scale=scale,force_result=original,float32_be=bits(original)))
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,consumer_va='0x802460B0',initialization_range=['0x80265868','0x802659A0'],original_sample_range=['0x8041F288','0x8041F330'],tire_collections=rows,float_bit_cases=cases,comparison='exact IEEE754 float32 bits',bmw_rear_trace=trace,limitations=['original initialized curve data; later runtime tuning not modeled','upstream scalar force stage only; combined-slip saturation and contact dynamics remain separate'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.dol,a.attributes),indent=2))
