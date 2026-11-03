#!/usr/bin/env python3
"""Compare original speed/gear -> requested RPM stage with portable C."""
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
    db=VehicleAttributes(raw);ref=OriginalPpcReference(dol.read_bytes());rng=random.Random(200511)
    class Tires(ctypes.Structure):_fields_=[('width',ctypes.c_float*2),('aspect',ctypes.c_float*2),('rim',ctypes.c_float*2)]
    root=Path(__file__).resolve().parents[1];cases=0;rows=0;trace=[]
    def bits(v):return struct.pack('>f',v).hex()
    def layout(row):return bytes(db.bin[row['layout']:row['layout']+db.classes[row['class_key']]['base_size']])
    with tempfile.TemporaryDirectory(prefix='mw-original-rpm-') as temporary:
        lib=Path(temporary)/'rpm.so'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_physics_drivetrain.c'),str(root/'source_bmw/mw_physics_tires.c'),'-lm','-o',str(lib)],check=True)
        impl=ctypes.CDLL(str(lib));f=impl.mw_physics_requested_rpm;f.argtypes=[ctypes.POINTER(Tires),ctypes.POINTER(ctypes.c_float),ctypes.c_size_t,ctypes.c_uint,*([ctypes.c_float]*4)];f.restype=ctypes.c_float
        for engine in db.collections.values():
            if engine['class_key']!=h('engine'):continue
            try:tires=db.find('tires',engine['key']);trans=db.find('transmission',engine['key'])
            except KeyError:continue
            e=db.fields(engine);t=db.fields(tires);tr=db.fields(trans);ratios=tr['GEAR_RATIO']['value']['values']
            if e['RED_LINE']['value']<=0:continue
            dimensions=Tires(*((ctypes.c_float*2)(*t[key]['value']) for key in ['SECTION_WIDTH','ASPECT_RATIO','RIM_SIZE']))
            array=(ctypes.c_float*len(ratios))(*ratios);rows+=1
            for gear in range(len(ratios)):
                for speed in [-100,-20,-.001,0,.001,20,100,rng.uniform(-200,200)]:
                    speed=ctypes.c_float(speed).value
                    original=ref.requested_rpm(layout(engine),layout(tires),layout(trans),gear,speed)
                    portable=f(ctypes.byref(dimensions),array,len(ratios),gear,tr['FINAL_GEAR']['value'],e['IDLE']['value'],e['RED_LINE']['value'],speed)
                    if bits(original)!=bits(portable):raise AssertionError((db.label(engine['key']),gear,speed,original,portable,bits(original),bits(portable)))
                    cases+=1
                    if db.label(engine['key'])=='bmwm3gtre46' and speed==20:trace.append(dict(gear_slot=gear,speed_mps=speed,rpm=original,float32_be=bits(original)))
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,function_va='0x802555CC',vehicle_collections=rows,float_bit_cases=cases,comparison='exact IEEE754 float32 bits',bmw_trace=trace,limitations=['requested RPM scalar stage only; actual engine RPM integration and clutch are separate','original invalid-array-index fallback is not reproduced','input speed unit follows proven metre tire dimensions and angular conversions'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.dol,a.attributes),indent=2))
