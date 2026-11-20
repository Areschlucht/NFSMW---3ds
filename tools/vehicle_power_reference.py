#!/usr/bin/env python3
"""Compare source positive powf positive branches against unchanged PowerPC code."""
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
from vehicle_ppc_reference import OriginalPpcReference,DOL_SHA256

ROOT=Path(__file__).resolve().parents[1]
def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def value(x):return struct.unpack('<f',struct.pack('<I',x))[0]
def verify(dol,output):
    raw=dol.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected USA DOL')
    class PowerReference(OriginalPpcReference):
        def _call(self,*args,**kwargs):
            self.allowed+=((0x8031e07c,0x8031e1cc),)
            return super()._call(*args,**kwargs)
    reference=PowerReference(raw);rng=random.Random(31704)
    edges=[0,0x80000000,1,2,3,0x3fffff,0x7fffff,0x800000,0x800001,
        0x00800002,0x3eaaaaab,0x3f000000,0x3f7fffff,0x3f800000,0x3f800001,
        0x40000000,0x40400000,0x40800000,0x7e7fffff,0x7f7ffffe,0x7f7fffff]
    edges += [center+delta for center in (0x3f9cc471,0x3fddb3d6) for delta in range(-16,17)]
    examples=edges+[rng.randrange(0x7f800000) for _ in range(2048)]
    cases=0;finite=0;overflow=0
    with tempfile.TemporaryDirectory() as directory:
        library=Path(directory)/'power.so'
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(ROOT/'include'),str(ROOT/'source_bmw/mw_original_power.c'),'-lm','-o',str(library)],check=True)
        native=C.CDLL(str(library)).mw_original_power_positive
        native.argtypes=[C.c_float,C.c_float,C.POINTER(C.c_float)];native.restype=C.c_bool
        for exponent in (0,.5,1,2,*[C.c_float(x).value for x in (.7,.8,C.c_float(1-C.c_float(.8).value).value,.75,.01,1.3,1.99)]):
            for encoded in examples:
                base=value(encoded);expected=reference.scalar_math('pow',base,second=exponent);out=C.c_float(123)
                valid=native(base,exponent,C.byref(out))
                if math.isfinite(expected):
                    if not valid or bits(expected)!=bits(out.value):raise AssertionError({'base_bits':hex(encoded),'exponent':exponent,'expected':expected,'native':out.value,'expected_bits':hex(bits(expected)),'native_bits':hex(bits(out.value))})
                    finite+=1
                else:
                    if valid or out.value!=123:raise AssertionError('Finite-result guard differs')
                    overflow+=1
                cases+=1
        for base,exponent in ((-1,.5),(1,3),(float('inf'),.5),(float('nan'),1),(1,float('nan'))):
            out=C.c_float(123)
            if native(base,exponent,C.byref(out)) or out.value!=123:raise AssertionError('Unsupported domain was accepted')
    report={'dol_sha256':DOL_SHA256,'original_powf_range':'8031CEC0..8031D5B8','sqrtf_range':'8031D704..8031D7FC',
        'original_powf_code_sha256':hashlib.sha256(reference.dol.read(0x8031cec0,0x6f8)).hexdigest(),
        'original_sqrtf_code_sha256':hashlib.sha256(reference.dol.read(0x8031d704,0xf8)).hexdigest(),
        'cases':cases,'finite_float_bit_matches':finite,'nonfinite_result_rejections':overflow,'float_bit_mismatches':0,
        'supported_exponents':'finite0..2','random_seed':31704,
        'limits':['Finite positive/signed-zero float inputs only, not full original powf general domain',
            'Exponents outside0..2 and nonfinite results reject without writes; no libm fallback',
            'Original float-return behavior preserved; not binary64 pow',
            'Reference default floating-state results, not hardware FPSCR/exceptions or complete-game denormal policy']}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('cases','finite_float_bit_matches','nonfinite_result_rejections','float_bit_mismatches')}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.dol,a.output)
