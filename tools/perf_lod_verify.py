#!/usr/bin/env python3
"""Compare portable originalLOD decision with bounded unmodified USA PPC."""
import argparse
import ctypes as c
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import tempfile
from perf_lod_reference import LodReference

class Input(c.Structure):
    _fields_=[('score',c.c_int32),('flags',c.c_uint32),('context',c.c_uint32),
              ('state',c.c_int32),('mask',c.c_uint32),('mesh',c.c_bool),
              ('tri',c.c_int16),('metric',c.c_float)]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,default=Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parent.parent
 raw=a.dol.read_bytes();ref=LodReference(raw);vectors=[]
 scores=[-2147483648,-1,0,1,2,7,8,12,13,16,17,18,21,22,23,31,32,33,52,53,86,87,88,100,2147483640,2147483647]
 for score in scores:
  for flags in (0,0x80,0x100,0x01000000,0x02000000,0x02000080,0x02000100):
   for ctx in (0,0x20,0x800,0x1000,0x1800,0x1820):
    for state in (0,2,3):vectors.append((score,flags,ctx,state,15,True,40,10.0))
 rng=random.Random(0x802bec38)
 for _ in range(6000):
  vectors.append((rng.choice(scores+[rng.randrange(0,10000)]),rng.getrandbits(32),rng.getrandbits(14),rng.randrange(-1,5),rng.randrange(16),rng.choice((True,False)),rng.choice((-32768,-1,0,39,40,32767)),rng.choice((-1.,0.,5.99,6.,6.01,10.,1000.,float('nan')))))
 with tempfile.TemporaryDirectory(prefix='nfsmw-lod-') as tmp:
  so=Path(tmp)/'lod.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_lod_select.c'),'-o',str(so)],check=True)
  dll=c.CDLL(str(so));dll.mw_lod_select.argtypes=[c.POINTER(Input)];dll.mw_lod_select.restype=c.c_int
  for n,vector in enumerate(vectors):
   data=Input(*vector);actual=dll.mw_lod_select(c.byref(data));original=ref.select(*vector)
   if actual!=original:raise ValueError(f'LOD mismatch at{n}: {vector}:C{actual},PPC{original}')
  assert dll.mw_lod_select(None)==-1
 report=dict(original_dol_sha256=hashlib.sha256(raw).hexdigest(),vectors=len(vectors),exact_slot_matches=True,scope='Decision802BEC38..802BED60 only; projected-score producer/visibility/activation not validated here.',sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'include/mw_lod_select.h',root/'source_bmw/mw_lod_select.c',root/'tools/perf_lod_reference.py')})
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
