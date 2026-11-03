#!/usr/bin/env python3
"""Compare original converted chassis spring/damper and contact-load stage."""
import argparse
import ctypes as C
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

class Axle(C.Structure):_fields_=[(n,C.c_float) for n in ['spring','progression','shock','extension','valving','digression','travel','ride','blowout']]
class Input(C.Structure):_fields_=[(n,C.c_float) for n in ['plane_w','normal_dot','previous','dt','ride_extra','antiroll','mass']]
class Output(C.Structure):_fields_=[(n,C.c_float) for n in ['compression','compression_velocity','spring_force','damper_force','normal_force','penetration_excess']]+[('has_contact',C.c_bool),('bottomed_out',C.c_bool)]
POWER=C.CFUNCTYPE(C.c_float,C.c_float,C.c_float,C.c_void_p)
class Math(C.Structure):_fields_=[('power',POWER),('context',C.c_void_p)]

def verify(dol,attributes):
    raw=attributes.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ATTR_SHA:raise ValueError('Unexpected source')
    db=VehicleAttributes(raw);ref=OriginalPpcReference(dol.read_bytes());root=Path(__file__).resolve().parents[1];rng=random.Random(200516);cases=0;rows=0;power_failures=[];default_differences=0;max_error=0;contact_differences=0;antiroll_cases=0
    def bits(v):return struct.pack('>f',v)
    with tempfile.TemporaryDirectory(prefix='mw-suspension-') as temporary:
        lib=Path(temporary)/'suspension.so'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_physics_suspension.c'),'-lm','-o',str(lib)],check=True)
        impl=C.CDLL(str(lib));f=impl.mw_physics_suspension_load;f.argtypes=[C.POINTER(Axle),C.POINTER(Input),C.POINTER(Output),C.POINTER(Math)];f.restype=None
        antiroll=impl.mw_physics_suspension_antiroll;antiroll.argtypes=[C.POINTER(C.c_float)]*3;antiroll.restype=None
        def power(a,b,_):
            try:return ref.scalar_math('pow',a,second=b)
            except Exception as e:power_failures.append(str(e));return float('nan')
        callback=POWER(power);provider=Math(callback,None)
        for row in db.collections.values():
            if row['class_key']!=h('chassis'):continue
            fields=db.fields(row);layout=bytes(db.bin[row['layout']:row['layout']+116]);rows+=1
            for axle in [0,1]:
                a=Axle(*[fields[k]['value'][axle] for k in ['SPRING_STIFFNESS','SPRING_PROGRESSION','SHOCK_STIFFNESS','SHOCK_EXT_STIFFNESS','SHOCK_VALVING','SHOCK_DIGRESSION','TRAVEL','RIDE_HEIGHT']],fields['SHOCK_BLOWOUT']['value'])
                for scenario in range(24):
                    in_=Input(rng.uniform(-.4,.1),rng.choice([0,.1,.2,.201,.5,.9999,1]),rng.choice([0,.02,.1,.2]),rng.choice([1/120,1/60]),rng.choice([-1,0,1]),rng.uniform(-5000,5000),rng.choice([900,1300,3000]))
                    source=ref.suspension_load(layout,axle,*[getattr(in_,n) for n in ['plane_w','normal_dot','previous','dt','ride_extra','antiroll','mass']]);out=Output();f(C.byref(a),C.byref(in_),C.byref(out),C.byref(provider));assert not power_failures,power_failures
                    for key,_ in Output._fields_:
                        actual=getattr(out,key);expected=source[key]
                        if (actual!=expected if isinstance(actual,bool) else bits(actual)!=bits(expected)):raise AssertionError((db.label(row['key']),axle,scenario,key,actual,expected))
                    native=Output();f(C.byref(a),C.byref(in_),C.byref(native),None)
                    if native.has_contact!=out.has_contact or native.bottomed_out!=out.bottomed_out:contact_differences+=1
                    if bits(native.normal_force)!=bits(out.normal_force):default_differences+=1
                    max_error=max(max_error,abs(native.normal_force-out.normal_force));cases+=1
            sway=(C.c_float*2)(*fields['SWAYBAR_STIFFNESS']['value'])
            for scenario in range(16):
                previous=(C.c_float*4)(*([0,0,0,0] if scenario==0 else [rng.uniform(0,.25) for _ in range(4)]));source=ref.suspension_antiroll(layout,list(previous));out=(C.c_float*4)();antiroll(previous,sway,out)
                assert b''.join(bits(v) for v in source)==b''.join(bits(v) for v in out),('antiroll',db.label(row['key']),list(previous),source,list(out))
                antiroll_cases+=1
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,original_conversion_range=['0x8024A730','0x8024A7B4'],original_force_range=['0x8024AAC4','0x8024AC8C'],chassis_collections=rows,full_output_float_bit_cases=cases,antiroll_float_bit_cases=antiroll_cases,runtime_default_force_differences=default_differences,runtime_default_contact_differences=contact_differences,runtime_default_max_force_error=max_error,limitations=['exact force comparisons use original powf callback; defaulttargetpowf differences reported separately','normal/body-up dot is supplied after original0..1 clamp','wheelquery/basis/bodyhalfextents andvehicleupdatescheduler are separate'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.dol,a.attributes),indent=2))
