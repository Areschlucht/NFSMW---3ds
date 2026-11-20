#!/usr/bin/env python3
"""Observe original common-menu AEMS sample selection offline.

Executes original PPC graph embedded in the original ABK and unchanged DOL AEMS
kernels. Applies only the exact original import/static relocations performed by
SNDAEMSI_resolvemodulebank. Stops at SNDplaybank: this verifies sample selection,
not DSP playback or a complete AEMS interpreter. No code is emitted to the3DS.
"""
import argparse,hashlib,json,struct
from pathlib import Path
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
BANK_SHA='59ea46087a01a688dcb2f0bedb71795b0931ac1537ea284afe44e7c08a54e234'
BANK=0x81000000;STATE=0x82000000;STOP=0x84000000

def sha(b):return hashlib.sha256(b).hexdigest()
def observed(dol,bank,selector,volume):
 from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
 from unicorn import ppc_const as r
 if sha(dol)!=DOL_SHA256 or sha(bank)!=BANK_SHA:raise ValueError('Unexpected original executable/common bank')
 image=DolImage(dol);raw=bytearray(bank)
 def word(at):return struct.unpack_from('>I',raw,at)[0]
 funcs=struct.unpack('>40I',image.read(0x80450224,160));fix=word(48)
 imports=[]
 for i in range(word(fix)):
  off=word(fix+4+i*4);index=struct.unpack_from('>H',raw,off)[0]<<16|struct.unpack_from('>H',raw,off+4)[0]
  if index>=40:raise ValueError('Unrecognized original AEMS import')
  address=funcs[index];struct.pack_into('>H',raw,off,address>>16);struct.pack_into('>H',raw,off+4,address&65535);imports.append(index)
 static=word(52)
 for i in range(word(static)):
  off=word(static+4+i*4);struct.pack_into('>I',raw,off,word(off)+BANK)
 module=word(28);code=word(module+40);data=word(module+44);size=word(module+48)
 if (struct.unpack_from('>H',raw,module+32)[0],raw[module+37],raw[module+38])!=(0,1,1):raise ValueError('Different original common module layout')
 for j in range(raw[module+36]):struct.pack_into('>I',raw,data+word(module+60+j*4),BANK)
 uc=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
 for address,size_map in [(0x80000000,0x600000),(BANK,0x100000),(STATE,0x100000),(0x83000000,0x100000),(STOP,0x1000)]:uc.mem_map(address,size_map)
 for s in image.sections:uc.mem_write(s.address,image.read(s.address,s.size))
 uc.mem_write(BANK,bytes(raw));uc.mem_write(STATE,bytes(raw[data:data+size]));uc.mem_write(STATE+0x40,struct.pack('>4I',selector,volume,4096,0))
 uc.reg_write(r.UC_PPC_REG_1,0x830ff000);uc.reg_write(r.UC_PPC_REG_3,STATE+24);uc.reg_write(r.UC_PPC_REG_LR,STOP);uc.reg_write(r.UC_PPC_REG_MSR,0x2000)
 result=[];count=0;called=set()
 def instruction(u,address,n,unused):
  nonlocal count
  count+=1
  if address==STOP:u.emu_stop();return
  if address==0x8035f974:
   result.append({'bank_sample':u.reg_read(r.UC_PPC_REG_4),'bank_handle':u.reg_read(r.UC_PPC_REG_3)});u.emu_stop();return
  if not (BANK+code<=address<BANK+data or 0x8035aa7c<=address<0x8035cbe8 or 0x80361480<=address<0x803614d8 or 0x80361544<=address<0x8036164c):raise ValueError(f'Original sound graph escaped allowed code {address:08x}')
  if address in funcs:called.add(address)
 def write(u,access,address,n,value,unused):
  if not (STATE<=address<address+n<=STATE+0x100000 or 0x83000000<=address<address+n<=0x83100000 or 0x804bec78<=address<address+n<=0x804bec90):raise ValueError('Original graph wrote outside admitted state/stack')
 uc.hook_add(UC_HOOK_CODE,instruction);uc.hook_add(UC_HOOK_MEM_WRITE,write)
 uc.emu_start(BANK+code,STOP,count=100000)
 if len(result)!=1:raise ValueError('Original source did not reach one sample boundary')
 return {'selector':selector,'volume':volume,**result[0],'instructions':count,'original_kernels':sorted(f'{x:08x}' for x in called)}

def sample_map(bank):
 # Original common ABK has one shared23-entry SAMPLEGROUP; vgmstream enumerates
 # non-dummy entries in this exact module/player traversal order.
 mod=struct.unpack_from('>I',bank,28)[0];data=struct.unpack_from('>I',bank,mod+44)[0];player=struct.unpack_from('>I',bank,mod+60)[0];table=struct.unpack_from('>I',bank,data+player+4)[0];count=struct.unpack_from('>I',bank,table)[0]
 if count!=23:raise ValueError('Different common sample group')
 ordinal=0;result={}
 for i in range(count):
  at=table+4+i*12;kind=bank[at];sample=struct.unpack_from('>I',bank,at+4)[0]
  if kind!=0:raise ValueError('Unexpected nonresident common sample')
  if not sample:continue
  ordinal+=1
  if sample in result:raise ValueError('Ambiguous common bank sample')
  result[sample]=ordinal
 return result

def build(args):
 dol=args.dol.read_bytes();bank=args.bank.read_bytes();mapping=sample_map(bank)
 cases=[observed(dol,bank,s,v) for s in range(23) for v in (0,16384,32767)]
 for s in range(23):
  if len({x['bank_sample'] for x in cases if x['selector']==s})!=1:raise ValueError('Volume affects selector; preserve richer graph')
 selections=[{'selector':s,'bank_sample':cases[s*3]['bank_sample'],'decoder_subsong':mapping.get(cases[s*3]['bank_sample'])} for s in range(23)]
 report={'schema':1,'dol_sha256':DOL_SHA256,'source_bank_sha256':BANK_SHA,'source_bank_name':'SOUND\\Global\\FE_COMMON_MB.abk','source_bank_archive_hash':'5b8b970e','evidence':'Original bank PPC graph plus original DOL AEMS kernels; exact original relocation only; execution stops at original SNDplaybank boundary8035f974','original_import_table':'80450224','cases':cases,'selections':selections,'count':len(cases),'limits':['This verifies common-menu selection only, not DSP playback or the full audio graph','BNKsample0 has no vgmstream-admitted sample and is retained as unmapped, never guessed as another clip']}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['dol','bank','output']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();r=build(a);print(json.dumps({'original_cases':r['count'],'selections':r['selections']},indent=2))
