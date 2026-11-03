import importlib.util,struct,sys
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools')
from unicorn.ppc_const import *
spec=importlib.util.spec_from_file_location('top','/workspace/port-research/map-collision/probe-top-query.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class WallBankReference(m.TopReference):
 def query_bank(self,a,b,ci_raw,asset,mask=0):
  u=self.u;self.pair1={};self.instructions=0;ci=bytearray(ci_raw);struct.pack_into('>I',ci,28,0x60010000)
  u.mem_write(0x60000000,struct.pack('>I',mask));u.mem_write(0x60000200,bytes(ci));u.mem_write(0x60000300,bytes(128));u.mem_write(0x60000600,struct.pack('>II',0x60000700,0x60000704));u.mem_write(0x60000700,struct.pack('>I',0x60000200));u.mem_write(0x60000800,struct.pack('>4f4f',*a,1,*b,1));u.mem_write(0x60010000,asset)
  for reg,value in ((UC_PPC_REG_1,0x7000ff00),(UC_PPC_REG_3,0x60000000),(UC_PPC_REG_4,0x60000600),(UC_PPC_REG_5,0x60000800),(UC_PPC_REG_6,0x60000300),(UC_PPC_REG_LR,0x6000fff0)):u.reg_write(reg,value)
  u.emu_start(0x802f3e6c,0x802f4000,timeout=200000,count=200000)
  if u.reg_read(UC_PPC_REG_PC)!=0x802f4000:raise ValueError('wall query exceeded budget')
  selected=u.reg_read(UC_PPC_REG_22)
  point=struct.unpack('>3f',bytes(u.mem_read(u.reg_read(UC_PPC_REG_1)+8,12))) if selected else None
  return dict(hit=bool(selected),asset_relative_wall_offset=selected-0x60010000 if selected else None,point=point,instructions=self.instructions)
if __name__=='__main__':
 from world_collision import packages
 stream=Path('/workspace/port-research/rockport/samples/STREAML2RA-full.BUN').read_bytes();ref=WallBankReference(Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes())
 for pack in packages(stream):
  for ci in pack['instances']:
   asset=pack['assets'][ci['asset_index']]
   if not asset['walls']:continue
   wall=asset['walls'][0];a=wall['endpoint_a'];b=wall['endpoint_b'];t=ci['world_to_local_translation'];mid=[(a[i]+b[i])/2-t[i] for i in range(3)];normal=[b[2]-a[2],0,a[0]-b[0]];length=(normal[0]**2+normal[2]**2)**.5;normal=[v/length for v in normal];start=[mid[i]-normal[i] for i in range(3)];end=[mid[i]+normal[i] for i in range(3)]
   print(pack['id'],wall,ref.query_bank(start,end,stream[ci['source_offset']:ci['source_offset']+64],stream[asset['source_offset']:asset['source_offset']+asset['source_bytes']]))
   raise SystemExit
