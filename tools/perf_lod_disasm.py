#!/usr/bin/env python3
"""Read-only bounded original USA DOL LOD investigation disassembly."""
import argparse
from pathlib import Path
from capstone import Cs,CS_ARCH_PPC,CS_MODE_32,CS_MODE_BIG_ENDIAN
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
import hashlib

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('start',type=lambda x:int(x,0));p.add_argument('end',type=lambda x:int(x,0));p.add_argument('--dol',type=Path,default=Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol'));a=p.parse_args();raw=a.dol.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected executable')
 image=DolImage(raw);cs=Cs(CS_ARCH_PPC,CS_MODE_32|CS_MODE_BIG_ENDIAN);cs.skipdata=True
 for i in cs.disasm(image.read(a.start,a.end-a.start),a.start):print(f'{i.address:08x} {i.mnemonic:10} {i.op_str}')
if __name__=='__main__':main()
