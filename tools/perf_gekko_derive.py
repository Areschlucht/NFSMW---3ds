#!/usr/bin/env python3
"""Identify numeric estimate segments from bounded black-box oracle queries.

The external implementation is compiled solely through the existing pinned
host-only adapter. This script never reads/parses/copies its implementation.
"""
import ctypes as c
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference,COMMIT,SOURCES

def bits(value):return struct.unpack('>Q',struct.pack('>d',value))[0]
def number(raw):return struct.unpack('>d',struct.pack('>Q',raw))[0]

def main():
 root=Path(__file__).resolve().parent.parent;rng=random.Random(0x80193420)
 oracle=DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin')
 table=[];cells=0;errors=[]
 for parity in (0,1):
  row=[]
  for segment in range(16):
   x=(1+segment/16)*(2**parity)
   base=(bits(oracle.estimate(x))&((1<<52)-1))>>26
   next_tick=(bits(oracle.estimate(x+2**(parity-15)))&((1<<52)-1))>>26
   row.append([base,base-next_tick])
  table.append(row)
  for tick in range(32768):
   x=(1+tick/32768)*(2**parity);base,dec=row[tick>>11]
   predicted=(1022<<52)|((base-dec*(tick&2047))<<26)
   if bits(oracle.estimate(x))!=predicted:errors.append(['normalized_cell',parity,tick])
   cells+=1
 vectors=[0,1<<63,0x7ff0000000000000,0xfff0000000000000,0xbff0000000000000]
 vectors += [e<<52|m for e in range(1,2047) for m in (0,(1<<52)-1,rng.getrandbits(52))]
 vectors += [1<<b for b in range(52)]
 vectors += [rng.getrandbits(64) for _ in range(100000)]
 with tempfile.TemporaryDirectory(prefix='gekko-identify-') as tmp:
  lib=Path(tmp)/'math.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_gekko_math.c'),'-lm','-o',str(lib)],check=True)
  dll=c.CDLL(str(lib));function=dll.mw_gekko_frsqrte;function.argtypes=[c.c_double];function.restype=c.c_double
  for raw in vectors:
   x=number(raw);actual=bits(function(x));expected=bits(oracle.estimate(x))
   if actual!=expected:errors.append([f'{raw:016x}',f'{actual:016x}',f'{expected:016x}'])
 report=dict(method='64 segment-start/next-tick functional queries,65536 cellchecks,independent IEEE exponent reconstruction and randomized bit comparisons; no external implementation parsed.',
             oracle_commit=COMMIT,oracle_source_sha256=SOURCES,segments=table,
             normalized_cells=cells,raw_ieee_vectors=len(vectors),bit_mismatches=len(errors),examples=errors[:20],
             runtime_source_sha256=hashlib.sha256((root/'source_bmw/mw_gekko_math.c').read_bytes()).hexdigest())
 output=Path('/workspace/port-research/hardware-optimization/gekko-math');output.mkdir(parents=True,exist_ok=True);(output/'estimate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('segments','oracle_source_sha256')},indent=2));oracle.close()
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
