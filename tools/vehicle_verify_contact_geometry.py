#!/usr/bin/env python3
"""Verify original physical wheel mounts; no visual TireOffsets substitution."""
import argparse
import ctypes as C
import hashlib
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from vehicle_attributes import VehicleAttributes
from vehicle_ppc_reference import OriginalPpcReference,DOL_SHA256
from vehicle_verify_original import ATTR_SHA
from vehicle_verify_contact_frame import Vector
from vehicle_vlt_hash import vlt_hash as h


def verify(dol,attributes):
    raw=attributes.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ATTR_SHA:raise ValueError('Unexpected attributes')
    db=VehicleAttributes(raw);ref=OriginalPpcReference(dol.read_bytes());root=Path(__file__).resolve().parents[1];cases=0;rows=0;bmw=[]
    class Tires(C.Structure):_fields_=[(name,C.c_float*2) for name in ['width','aspect','rim']]
    def layout(row):return bytes(db.bin[row['layout']:row['layout']+db.classes[row['class_key']]['base_size']])
    with tempfile.TemporaryDirectory(prefix='mw-mount-geometry-') as temporary:
        lib=Path(temporary)/'geometry.so'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_physics_contact_geometry.c'),'-o',str(lib)],check=True)
        impl=C.CDLL(str(lib));f=impl.mw_physics_contact_mounts;f.argtypes=[C.POINTER(Tires),C.POINTER(C.c_float),*([C.c_float]*3),C.POINTER(Vector)];f.restype=None
        for tire in db.collections.values():
            if tire['class_key']!=h('tires'):continue
            try:chassis=db.find('chassis',tire['key'])
            except KeyError:continue
            t=db.fields(tire);c=db.fields(chassis);dimensions=Tires(*[(C.c_float*2)(*t[key]['value']) for key in ['SECTION_WIDTH','ASPECT_RATIO','RIM_SIZE']]);track=(C.c_float*2)(*c['TRACK_WIDTH']['value']);rows+=1
            for half_extent_y in [-1,0,.3,1]:
                source=ref.contact_mounts(layout(tire),layout(chassis),C.c_float(half_extent_y).value);out=(Vector*4)()
                f(C.byref(dimensions),track,c['FRONT_AXLE']['value'],c['WHEEL_BASE']['value'],half_extent_y,out)
                for i in range(4):
                    for key,value in zip(['x','y','z'],source[i]):assert struct.pack('>f',value)==struct.pack('>f',getattr(out[i],key)),(db.label(tire['key']),i,key,value,getattr(out[i],key))
                cases+=1
                if db.label(tire['key'])=='bmwm3gtre46' and half_extent_y==0:bmw=source
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,original_range=['0x80247724','0x80247838'],vehicle_collections=rows,float_bit_cases=cases,bmw_mounts_at_half_extent_y_zero=bmw,limitations=['body half-extentY is an explicit argument; its bodyshape/parameter producer remains separate','original initialized physical wheel geometry; visualTireOffsets remain distinct'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.dol,a.attributes),indent=2))
