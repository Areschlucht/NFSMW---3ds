#!/usr/bin/env python3
"""Exhaust all original uint16 FOV producer inputs against unmodified PPC."""
import ctypes as c
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE
from unicorn import ppc_const as r
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256

def main():
 root=Path(__file__).resolve().parent.parent;raw=Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes();assert hashlib.sha256(raw).hexdigest()==DOL_SHA256;im=DolImage(raw)
 uc=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
 for low,size in ((0x10000000,0x10000),(0x800ff000,0x1000),(0x8005c000,0x1000),(0x803d0000,0x1000),(0x803de000,0x1000)):uc.mem_map(low,size)
 for a,n in ((0x800fff14,0x70),(0x8005ce20,0x130),(0x803d0000,0x1000),(0x803de000,0x1000)):uc.mem_write(a,im.read(a,n))
 # Only noncontributing Gekko paired-single f31 ABI spill/reload are skipped;
 # the original scalar stfd/lfd ABI pair still saves/restores f31 normally.
 abi={0x800fff1c:0xf3e10010,0x800fff78:0xe3e10010}
 for a,w in abi.items():assert im.u32(a)==w
 uc.reg_write(r.UC_PPC_REG_MSR,0x2000)
 state={'done':False}
 def hook(uc,a,size,unused):
  if a==0x1000fff0:state['done']=True;uc.emu_stop()
  elif a in abi:uc.reg_write(r.UC_PPC_REG_PC,a+4)
  elif not (0x800fff14<=a<0x800fff84 or 0x8005ce20<=a<0x8005ceeC or 0x8005cf28<=a<0x8005cf50):raise ValueError(f'Original FOV producer escaped:{a:08x}')
 uc.hook_add(UC_HOOK_CODE,hook);mismatch=[]
 with tempfile.TemporaryDirectory(prefix='lod-fov-') as temp:
  lib=Path(temp)/'lod.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_lod_select.c'),'-lm','-o',str(lib)],check=True)
  dll=c.CDLL(str(lib));dll.mw_lod_projection_raw.argtypes=[c.c_uint16];dll.mw_lod_projection_raw.restype=c.c_float
  for fov in range(65536):
   uc.reg_write(r.UC_PPC_REG_1,0x1000e000);uc.reg_write(r.UC_PPC_REG_3,fov);uc.reg_write(r.UC_PPC_REG_LR,0x1000fff0);state['done']=False
   uc.emu_start(0x800fff14,0x1000fff4,count=1000);assert state['done']
   original=struct.unpack('>d',struct.pack('>Q',uc.reg_read(r.UC_PPC_REG_FPR0+1)))[0];actual=dll.mw_lod_projection_raw(fov)
   if struct.pack('>f',actual)!=struct.pack('>f',original):mismatch.append([fov,actual,original])
 report={'vectors':65536,'bit_exact_mismatches':len(mismatch),'examples':mismatch[:10],'original_dol_sha256':DOL_SHA256,'abi_only_skipped':{hex(a):hex(w) for a,w in abi.items()}}
 output=Path('/workspace/port-research/hardware-optimization/lod/projection-validation.json');output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
