#!/usr/bin/env python3
"""Compare independently written caller sqrt stages with original scalar PPC."""
import ctypes as c
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE
from unicorn import ppc_const as r
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
from perf_lod_reference import ProjectedScoreReference

def f32bits(v):return struct.unpack('>I',struct.pack('>f',v))[0]
def f32(raw):return struct.unpack('>f',struct.pack('>I',raw))[0]

class ContactRootReference:
 def __init__(self,raw,estimate):
  assert hashlib.sha256(raw).hexdigest()==DOL_SHA256;im=DolImage(raw)
  self.uc=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN);uc=self.uc
  for a,n in ((0x10000000,0x1000),(0x80193000,0x1000),(0x803eb000,0x1000)):uc.mem_map(a,n)
  for a,n in ((0x80193420,0x38),(0x803eb000,0x1000)):uc.mem_write(a,im.read(a,n))
  uc.reg_write(r.UC_PPC_REG_MSR,0x2000);self.done=False
  def hook(uc,a,size,unused):
   if a==0x10000ff0:self.done=True;uc.emu_stop()
   elif a==0x80193434:
    x=struct.unpack('>d',struct.pack('>Q',uc.reg_read(r.UC_PPC_REG_FPR0+12)))[0]
    uc.reg_write(r.UC_PPC_REG_FPR0+1,struct.unpack('>Q',struct.pack('>d',estimate(x)))[0]);uc.reg_write(r.UC_PPC_REG_PC,a+4)
   elif not 0x80193420<=a<0x80193458:raise ValueError(f'Contactrootescaped:{a:08x}')
  uc.hook_add(UC_HOOK_CODE,hook)
 def root(self,value):
  uc=self.uc;uc.reg_write(r.UC_PPC_REG_FPR0+1,struct.unpack('>Q',struct.pack('>d',value))[0]);uc.reg_write(r.UC_PPC_REG_LR,0x10000ff0)
  self.done=False;uc.emu_start(0x80193420,0x10000ff4,count=1000);assert self.done
  return struct.unpack('>d',struct.pack('>Q',uc.reg_read(r.UC_PPC_REG_FPR0+1)))[0]

def main():
 root=Path(__file__).resolve().parent.parent;raw=Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes()
 oracle=DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin');one=ContactRootReference(raw,oracle.estimate);two=ProjectedScoreReference(raw,oracle.estimate)
 rng=random.Random(0x801916dc);vectors=[0,0x80000000,1,0x007fffff,0x00800000,0x7f7fffff]
 vectors += [(127<<23)|(tick<<8) for tick in range(32768)]
 vectors += [(128<<23)|(tick<<8) for tick in range(32768)]
 vectors += [rng.randrange(1,0x7f800000) for _ in range(20000)]
 mismatch1=[];mismatch2=[]
 with tempfile.TemporaryDirectory(prefix='gekko-newton-') as tmp:
  lib=Path(tmp)/'math.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_gekko_math.c'),'-lm','-o',str(lib)],check=True)
  dll=c.CDLL(str(lib));functions=[dll.mw_gekko_sqrt_newton1,dll.mw_gekko_sqrt_newton2]
  for function in functions:function.argtypes=[c.c_float];function.restype=c.c_float
  for bits in vectors:
   x=f32(bits)
   for function,reference,failures in ((functions[0],one.root,mismatch1),(functions[1],two.distance,mismatch2)):
    actual=f32bits(function(x));expected=f32bits(reference(x))
    if actual!=expected:failures.append([f'{bits:08x}',f'{actual:08x}',f'{expected:08x}'])
 report={'vectors_per_stage':len(vectors),'newton1_bit_mismatches':len(mismatch1),'newton2_bit_mismatches':len(mismatch2),'examples1':mismatch1[:15],'examples2':mismatch2[:15],'original_dol_sha256':DOL_SHA256,'oracle':'Original scalarPPC, onlyfrsqrte estimate externalpinnedDolphin. Validfinitepositivefloatdomain plus signedzero. NoFPUflags emulation.'}
 out=Path('/workspace/port-research/hardware-optimization/gekko-math');out.mkdir(parents=True,exist_ok=True);(out/'newton-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));oracle.close()
 if mismatch1 or mismatch2:raise SystemExit(1)
if __name__=='__main__':main()
