#!/usr/bin/env python3
"""Verify portable components against bounded original PPC executions.

Original files are supplied locally and are not included in the repository.
Output contains hashes, counts and one BMW trace, not complete game data.
"""
import argparse
import ctypes
import hashlib
import json
import math
import random
import struct
import subprocess
import tempfile
from pathlib import Path
from vehicle_attributes import VehicleAttributes
from vehicle_ppc_reference import OriginalPpcReference, DOL_SHA256, PSQ_ABI
from vehicle_vlt_hash import vlt_hash

ATTR_SHA='5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c'


def verify(dol_path,attributes_path):
    raw=attributes_path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ATTR_SHA:raise ValueError('Unexpected attribute source SHA256')
    db=VehicleAttributes(raw);ref=OriginalPpcReference(dol_path.read_bytes())
    rng=random.Random(2005)
    names=['','engine','chassis','EngineRacer','SuspensionRacer']+[bytes(rng.randint(1,127) for _ in range(n)) for n in range(257)]
    for name in names:
        assert ref.hash(name)==vlt_hash(name),repr(name)
    class Curve(ctypes.Structure):
        _fields_=[('torque',ctypes.POINTER(ctypes.c_float)),('count',ctypes.c_size_t),('idle',ctypes.c_float),('maximum',ctypes.c_float),('redline',ctypes.c_float)]
    class TireDimensions(ctypes.Structure):
        _fields_=[('width',ctypes.c_float*2),('aspect',ctypes.c_float*2),('rim',ctypes.c_float*2)]
    root=Path(__file__).resolve().parents[1];rows=0;cases=0;trace=[];tire_rows=0;tire_cases=0;tire_trace=[]
    def bits(value):return struct.pack('>f',value).hex()
    with tempfile.TemporaryDirectory(prefix='mw-engine-reference-') as temporary:
        lib=Path(temporary)/'engine.so'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_physics_engine.c'),str(root/'source_bmw/mw_physics_tires.c'),'-lm','-o',str(lib)],check=True)
        implementation=ctypes.CDLL(str(lib));implementation.mw_physics_engine_curve_raw.argtypes=[ctypes.POINTER(Curve),ctypes.c_float];implementation.mw_physics_engine_curve_raw.restype=ctypes.c_float
        implementation.mw_physics_tire_diameter_m.argtypes=[ctypes.POINTER(TireDimensions),ctypes.c_int];implementation.mw_physics_tire_diameter_m.restype=ctypes.c_float
        for row in db.collections.values():
            if row['class_key']==vlt_hash('tires'):
                fields=db.fields(row);dimensions=TireDimensions(*((ctypes.c_float*2)(*fields[key]['value']) for key in ['SECTION_WIDTH','ASPECT_RATIO','RIM_SIZE']))
                layout=bytes(db.bin[row['layout']:row['layout']+80]);tire_rows+=1
                for front in [0,1,2,-1]:
                    original=ref.tire_diameter(layout,front);portable=implementation.mw_physics_tire_diameter_m(ctypes.byref(dimensions),front);tire_cases+=1
                    if bits(original)!=bits(portable):raise AssertionError(('tire',db.label(row['key']),front,original,portable))
                    if db.label(row['key'])=='bmwm3gtre46':tire_trace.append(dict(front_selector=front,diameter_m=original,float32_be=bits(original)))
            if row['class_key']!=vlt_hash('engine'):continue
            fields=db.fields(row);t=fields['TORQUE']['value']['values'];idle=fields['IDLE']['value'];maximum=fields['MAX_RPM']['value'];redline=fields['RED_LINE']['value']
            if not (maximum>idle and idle<=redline<=maximum):continue
            array=(ctypes.c_float*len(t))(*t);curve=Curve(array,len(t),idle,maximum,redline)
            layout=bytes(db.bin[row['layout']:row['layout']+96]);rows+=1
            samples=[0,idle-1,idle,idle+1,redline-1,redline,redline+1,maximum,maximum+1000]+[rng.uniform(-1000,maximum+1000) for _ in range(24)]
            for rpm in samples:
                rpm=ctypes.c_float(rpm).value
                original=ref.torque(layout,rpm);portable=implementation.mw_physics_engine_curve_raw(ctypes.byref(curve),rpm);cases+=1
                if bits(original)!=bits(portable):raise AssertionError((db.label(row['key']),rpm,original,portable,bits(original),bits(portable)))
                if db.label(row['key'])=='bmwm3gtre46' and len(trace)<9:trace.append(dict(rpm=rpm,raw_torque=original,float32_be=bits(original)))
        invalid=Curve(None,2,800,800,800)
        assert math.isnan(implementation.mw_physics_engine_curve_raw(ctypes.byref(invalid),1000))
        empty=Curve(None,1,0,0,0)
        assert implementation.mw_physics_engine_curve_raw(ctypes.byref(empty),1000)==0
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,original_curve_va='0x802240AC',original_hash_va='0x801956E8',original_tire_diameter_va='0x80224268',emulator_abi_nops={hex(k):hex(v) for k,v in PSQ_ABI.items()},hash_cases=len(names),engine_collections=rows,curve_float_bit_cases=cases,bmw_trace=trace,tire_collections=tire_rows,tire_float_bit_cases=tire_cases,bmw_tire_trace=tire_trace,comparison='exact IEEE754 float32 bits',limitations=['scalar torque curve only; no force or handling model claim','paired-single callee-save spills/reloads omitted only in reference emulator','invalid metadata is rejected rather than emulating original invalid memory accesses'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',required=True,type=Path);p.add_argument('--attributes',required=True,type=Path);a=p.parse_args()
    print(json.dumps(verify(a.dol,a.attributes),indent=2))
