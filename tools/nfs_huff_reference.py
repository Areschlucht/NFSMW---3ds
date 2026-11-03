"""Offline EA HUFF reference decoder, run in bounded x86 emulation only.

Optional dependencies: Unicorn 2.1.4 and the SHA-256 pinned QuickBMS reference
file. No downloaded instructions run natively; calls are limited to a Python
memset implementation and ignored stack-cookie checks inside the emulator.
This is a conversion aid, not a portable HUFF implementation for the 3DS.
Reference: https://github.com/LittleBigBug/QuickBMS/blob/master/src/included/ea_huff.c
"""
from pathlib import Path
import re,struct,sys,hashlib
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_PROT_READ,UC_PROT_WRITE,UC_PROT_EXEC,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
reference_bytes=Path('/workspace/toolchains/references/ea_huff.c').read_bytes()
if hashlib.sha256(reference_bytes).hexdigest()!='ea1529ff9db11d982868252256e8d848ea878b92210992338b66f8dd40d16f6d':
 raise ValueError('EA HUFF reference source checksum mismatch')
reference=reference_bytes.decode()
body=reference.split('ea_huff_dump[] = {',1)[1].split('};',1)[0]
code=bytes(int(x,16) for x in re.findall(r'0x([0-9a-fA-F]{2})',body))
CODE,SOURCE,OUTPUT,STACK=0x100000,0x200000,0x400000,0x800000

def decode(raw,expected,*,instruction_limit=5000000,timeout_us=3000000):
 if not 1<=instruction_limit<=100000000 or not 1<=timeout_us<=30000000:raise ValueError("HUFF emulation budget")
 if len(raw)<21 or raw[:8]!=b'HUFF\x01\x10\0\0' or struct.unpack_from('<I',raw,8)[0]!=expected or not 184<=expected<=32*1024*1024:raise ValueError('HUFF header')
 if struct.unpack_from('<I',raw,12)[0]+16!=len(raw):raise ValueError('HUFF compressed-size mismatch')
 uc=Uc(UC_ARCH_X86,UC_MODE_32)
 uc.mem_map(CODE,0x2000,UC_PROT_READ|UC_PROT_EXEC);uc.mem_write(CODE,code)
 uc.mem_map(SOURCE,(len(raw)+4095)&~4095,UC_PROT_READ);uc.mem_write(SOURCE,raw[16:])
 uc.mem_map(OUTPUT,(expected+4095)&~4095,UC_PROT_READ|UC_PROT_WRITE)
 uc.mem_map(STACK,0x10000,UC_PROT_READ|UC_PROT_WRITE)
 for address in(0xc89000,0xca9000):uc.mem_map(address,0x1000,UC_PROT_READ|UC_PROT_WRITE)
 def hook(uc,address,size,user):
  if address in (CODE+0x92d,CODE+0x947):
   sp=uc.reg_read(UC_X86_REG_ESP);dst,value,n=struct.unpack('<III',uc.mem_read(sp,12))
   if not STACK<=dst<=dst+n<=STACK+0x10000:raise ValueError('Unexpected memset destination')
   uc.mem_write(dst,bytes([value&255])*n);uc.reg_write(UC_X86_REG_EAX,dst);uc.reg_write(UC_X86_REG_EIP,address+5)
  elif address in(CODE+0xef6,CODE+0xf28,CODE+0xf3f):uc.reg_write(UC_X86_REG_EIP,address+5)
 def write(uc,access,address,size,value,user):
  if OUTPUT<=address<OUTPUT+((expected+4095)&~4095) and address+size>OUTPUT+expected:raise ValueError('Output overflow')
 uc.hook_add(UC_HOOK_CODE,hook,begin=CODE+0x92d,end=CODE+0x947)
 uc.hook_add(UC_HOOK_CODE,hook,begin=CODE+0xef6,end=CODE+0xf3f)
 uc.hook_add(UC_HOOK_MEM_WRITE,write)
 sp=STACK+0xf000;stop=CODE+0x1ff0
 uc.mem_write(sp,struct.pack('<II',stop,OUTPUT));uc.reg_write(UC_X86_REG_ESP,sp)
 uc.reg_write(UC_X86_REG_ECX,0);uc.reg_write(UC_X86_REG_EDX,SOURCE)
 uc.emu_start(CODE,stop,timeout=timeout_us,count=instruction_limit)
 if uc.reg_read(UC_X86_REG_EIP)!=stop:raise ValueError('HUFF emulation instruction/time limit')
 return bytes(uc.mem_read(OUTPUT,expected))
