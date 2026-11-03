from pathlib import Path
import json,struct
from vehicle_dol import DolImage
from material_recovery_carparts import CarParts
from material_recovery_vehicle import DOL_SHA256,texture_hash
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN
from unicorn.ppc_const import UC_PPC_REG_3,UC_PPC_REG_4,UC_PPC_REG_5,UC_PPC_REG_LR,UC_PPC_REG_PC
D=DolImage(Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes())
C=CarParts(Path('/workspace/port-research/v018-decoded/GLOBAL-GLOBALB_VM_NGC.BUN').read_bytes())
u=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN)
for va,size in ((0x802d9000,0x1000),(0x80437000,0x1000),(0x90000000,0x10000),(0xa0000000,0x1000)):u.mem_map(va,size)
u.mem_write(0x802d9b14,D.read(0x802d9b14,0xc8))
u.mem_write(0x80437750,struct.pack('>I',0x90000000))
u.mem_write(0x90000014,struct.pack('>I',0x90001000));u.mem_write(0x9000001c,struct.pack('>I',0x90006000))
a,b=C.tables[0x3460c];groups=C.data[a:b]
u.mem_write(0x90001000,b''.join(groups[i:i+2][::-1] for i in range(0,len(groups),2)))
a,b=C.tables[0x34605];attrs=C.data[a:b]
u.mem_write(0x90006000,b''.join(attrs[i:i+4][::-1] for i in range(0,len(attrs),4)))
n=0
for key in (0xc7f288d1,0xe9886d54,0xd0561e8c,0xd0561e8e):
 p=C.part(key);r=bytearray.fromhex(p['raw_record'])
 for off in (0,2,8,10,12):r[off:off+2]=r[off:off+2][::-1]
 u.mem_write(0x90000100,bytes(r))
 for name in ('TEXTURE','RED','GREEN','BLUE','GLOSS','NUMCOLOURS','REMAP'):
  u.reg_write(UC_PPC_REG_3,0x90000100);u.reg_write(UC_PPC_REG_4,texture_hash(name));u.reg_write(UC_PPC_REG_5,0);u.reg_write(UC_PPC_REG_LR,0xa0000000)
  u.emu_start(0x802d9b14,0xa0000000,timeout=100000,count=8192)
  if u.reg_read(UC_PPC_REG_PC)!=0xa0000000:raise ValueError('Original lookup escaped bound')
  at=u.reg_read(UC_PPC_REG_3);value=struct.unpack('>I',u.mem_read(at+4,4))[0] if at else None
  if value!=C.value(p,name):raise ValueError((p['name'],name,value,C.value(p,name)))
  n+=1
report={'dol_sha256':DOL_SHA256,'source_sha256':C.sha256,'lookup_function':'802d9b14','cases':n,'matched':n,'scope':'Original selectedattribute lookup over loader-endian-transformed original carpart/group/attribute bytes; does not execute the whole carparts loader'}
Path('/workspace/port-research/materials-fidelity/carparts-lookup-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
