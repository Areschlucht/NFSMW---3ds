#!/usr/bin/env python3
"""Verify original combined-force saturation given its explicit magnitude input."""
import argparse
import ctypes
import json
import math
import random
import struct
import subprocess
import tempfile
from pathlib import Path
from vehicle_ppc_reference import OriginalPpcReference,DOL_SHA256


def verify(dol):
    ref=OriginalPpcReference(dol.read_bytes());rng=random.Random(200513)
    class State(ctypes.Structure):_fields_=[(name,ctypes.c_float) for name in ['longitudinal','lateral','load','static','grip','combined','speed','budget','slip','traction']]+[('undo',ctypes.c_int)]
    root=Path(__file__).resolve().parents[1];cases=0
    with tempfile.TemporaryDirectory(prefix='mw-original-friction-') as temporary:
        lib=Path(temporary)/'friction.so'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_physics_friction.c'),'-lm','-o',str(lib)],check=True)
        impl=ctypes.CDLL(str(lib));f=impl.mw_physics_friction_limit_given_magnitude;f.argtypes=[ctypes.POINTER(State),ctypes.c_float];f.restype=None
        for case in range(8192):
            s=State(rng.uniform(-50000,50000),rng.uniform(-50000,50000),rng.choice([0,100,4000,10000]),rng.uniform(.2,3),rng.uniform(.2,2),rng.uniform(.2,2),rng.uniform(.2,2),rng.choice([0,.1,100,10000]),rng.uniform(-1000,1000),rng.random(),rng.randrange(2))
            magnitude=ctypes.c_float(math.hypot(s.longitudinal,s.lateral)).value
            if case<8:
                magnitudes=[0,ctypes.c_float(.001).value,struct.unpack('>f',bytes.fromhex('3a831270'))[0],40,40,.1,100,100]
                loads=[0,0,0,40,40,0,40,40];slips=[0,1,0,0,1,struct.unpack('>f',bytes.fromhex('3f800001'))[0],2,-2]
                magnitude=ctypes.c_float(magnitudes[case]).value
                s=State(magnitude*.8,magnitude*.6,loads[case],1,1,1,1,1,slips[case],.5,case%2)
            # Magnitude is an explicit stage input. This does not compare a
            # host hypot against original Gekko reciprocal estimate arithmetic.
            state=bytearray(0x140)
            for offset,value in [(0xdc,s.longitudinal),(0xd8,s.lateral),(0xd4,s.load),(0xec,s.grip),(0x12c,s.combined),(0x124,s.budget),(0x110,s.traction)]:struct.pack_into('>f',state,offset,value)
            original=ref.friction_limit(state,magnitude,s.static,s.speed,s.slip,s.undo);f(ctypes.byref(s),magnitude)
            for offset,value in [(0xdc,s.longitudinal),(0xd8,s.lateral),(0x110,s.traction)]:
                if original[offset:offset+4]!=struct.pack('>f',value):raise AssertionError((case,hex(offset),original[offset:offset+4].hex(),struct.pack('>f',value).hex()))
            cases+=1
    return dict(dol_sha256=DOL_SHA256,range=['0x80246A38','0x80246B14'],float_bit_cases=cases,comparison='exact IEEE754 float32 bits',limitations=['magnitude supplied identically to both implementations; no host-vs-Gekko sqrt claim','combined-force limit stage only; upstream force and downstream contact integration remain separate'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.dol),indent=2))
