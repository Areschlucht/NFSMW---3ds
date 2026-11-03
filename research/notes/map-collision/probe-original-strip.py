import json,struct,sys
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools')
from map_recovery_dol import DolImage
from unicorn import *
from unicorn.ppc_const import *
dol=DolImage(Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes())
u=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
u.mem_map(0x80000000,0x600000)
for s in dol.sections:u.mem_write(s['address'],dol.read(s['address'],s['size']))
u.mem_map(0x60000000,0x10000);u.mem_map(0x70000000,0x10000)
u.reg_write(UC_PPC_REG_MSR,u.reg_read(UC_PPC_REG_MSR)|(1<<13))
def hook(uc,address,size,data):
 if address in (0x802ef294,0x802efb70):uc.reg_write(UC_PPC_REG_PC,address+4)
 elif not 0x802ef290<=address<=0x802efb78:raise RuntimeError(hex(address))
u.hook_add(UC_HOOK_CODE,hook)
def query(point,flags=1,attributes=0,mask=0,vertices=((0,0,0),(0,0,128),(128,0,0))):
 u.mem_write(0x60000000,struct.pack('>I',mask))
 u.mem_write(0x60000100,struct.pack('>3f',*point))
 u.mem_write(0x60000200,struct.pack('>3f',0,0,0))
 raw=b''.join(struct.pack('>3hH',*p,extra) for p,extra in zip(vertices,(3,flags,attributes)))
 u.mem_write(0x60000300,raw)
 u.mem_write(0x60000400,bytes(64))
 for reg,value in ((UC_PPC_REG_1,0x7000ff00),(UC_PPC_REG_3,0x60000000),(UC_PPC_REG_4,0x60000100),(UC_PPC_REG_5,0x60000200),(UC_PPC_REG_6,0x60000300),(UC_PPC_REG_7,0x60000400),(UC_PPC_REG_LR,0x6000fff0)):
  u.reg_write(reg,value)
 u.emu_start(0x802ef290,0x6000fff0,timeout=100000,count=10000)
 if u.reg_read(UC_PPC_REG_PC)!=0x6000fff0:raise RuntimeError('reference budget exceeded')
 return u.reg_read(UC_PPC_REG_3),bytes(u.mem_read(0x60000400,48)).hex()
if __name__=='__main__':
 for flags in range(4):
  print(flags,query((.2,1,.2),flags))
