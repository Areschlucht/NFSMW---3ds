#!/usr/bin/env python3
"""Original projected-score comparison, including deliberate integer boundaries."""
import ctypes as c
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from perf_lod_reference import ProjectedScoreReference
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference

def main():
 root=Path(__file__).resolve().parent.parent
 oracle=DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin')
 raw=Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes();ref=ProjectedScoreReference(raw,oracle.estimate)
 rng=random.Random(802);vectors=[]
 for _ in range(6000):
  radius=rng.uniform(0,3000);projection=rng.uniform(128,1000);p=tuple(rng.uniform(-10000,10000) for _ in range(3));cam=tuple(rng.uniform(-5000,5000) for _ in range(3))
  vectors.append((p,cam,(0.,1.,0.),radius,projection))
 for radius in (0.,1.,10.,100.,1000.,3000.):
  for projection in (128.,256.,365.,512.,1000.):
   for target in (1,2,17,18,22,23,31,32,52,53,87,88,100):
    distance=(radius+6)*projection/target+(radius+6);bits=struct.unpack('<I',struct.pack('<f',distance))[0]
    for delta in range(-4,5):
     distance=struct.unpack('<f',struct.pack('<I',bits+delta))[0]
     vectors.append(((0.,distance,0.),(0.,0.,0.),(0.,1.,0.),radius,projection))
 mismatches=[];callback_mismatches=[];native_mismatches=[]
 with tempfile.TemporaryDirectory(prefix='lod-score-') as temp:
  lib=Path(temp)/'lod.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_lod_select.c'),str(root/'source_bmw/mw_gekko_math.c'),'-lm','-o',str(lib)],check=True)
  dll=c.CDLL(str(lib));function=dll.mw_lod_projected_score;function.argtypes=[c.POINTER(c.c_float)]*3+[c.c_float,c.c_float,c.c_void_p,c.c_void_p,c.POINTER(c.c_int32)];function.restype=c.c_bool
  callback_type=c.CFUNCTYPE(c.c_float,c.c_float,c.c_void_p)
  callback=callback_type(lambda squared,unused:ref.distance(squared))
  dll.mw_gekko_sqrt_newton2.argtypes=[c.c_float];dll.mw_gekko_sqrt_newton2.restype=c.c_float
  native_callback=callback_type(lambda squared,unused:dll.mw_gekko_sqrt_newton2(squared))
  for p,cam,forward,radius,projection in vectors:
   original=ref.score(p,cam,forward,radius,projection)
   arrays=[(c.c_float*3)(*a) for a in (p,cam,forward)]
   for sqrt_stage,failures in ((None,mismatches),(callback,callback_mismatches),(native_callback,native_mismatches)):
    actual=c.c_int32();assert function(*arrays,radius,projection,sqrt_stage,None,c.byref(actual))
    if actual.value!=original:failures.append([p,cam,forward,radius,projection,actual.value,original])
 report={'vectors':len(vectors),'sqrtf_score_mismatches':len(mismatches),'original_sqrt_callback_score_mismatches':len(callback_mismatches),'native_gekko_callback_score_mismatches':len(native_mismatches),'native_examples':native_mismatches[:10],'sqrtf_examples':mismatches[:15],
         'scope':'Original PPC producer uses external pinned Dolphin estimate only. Independent portable mw_gekko_sqrt_newton2 callback also compared; sqrtf remains a separate approximate control.'}
 output=Path('/workspace/port-research/hardware-optimization/lod/score-validation.json');output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='sqrtf_examples'},indent=2));oracle.close()
if __name__=='__main__':main()
