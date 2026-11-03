"""Offline bounded original mesh/wall selection reference, not runtime emulation.

Runs only SHA-pinned uploaded executable ranges. Explicit paired-single hooks
use binary64 intermediates rounded binary32, excluding exact Gekko FMA ties,
FPSCR, subnormal/NaN behavior. Caller supplies a pinned external reciprocal-
square-root estimate model (see vehicle_dolphin_frsqrte); no lookup table or
original game code is bundled. Evidence is an emulator model, not console trace.
Wall-bank query stops before contact assembly; wall-contact query includes
original point/normal/material output, without rigid-body impulses or response.
"""
import struct
from map_recovery_strip_reference import OriginalStripReference
from map_recovery_ps_reference import f32
from unicorn.ppc_const import *
class OriginalContactReference(OriginalStripReference):
 def __init__(self,raw,frsqrte_reference):
  self.pair1={};self.instructions=0;super().__init__(raw)
  self.sqrt_reference=frsqrte_reference
  self.extra_allowed=()
  self.u.mem_map(0x60010000,0x20000)
 def floating(self,i):return struct.unpack('>d',struct.pack('>Q',self.u.reg_read(UC_PPC_REG_FPR0+i)))[0]
 def putfloating(self,i,v):self.u.reg_write(UC_PPC_REG_FPR0+i,struct.unpack('>Q',struct.pack('>d',v))[0])
 def pair(self,i):
  x=self.floating(i);return (x,self.pair1.get(i,x))
 def putpair(self,i,p):self.putfloating(i,p[0]);self.pair1[i]=p[1]
 def _hook(self,u,address,size,data):
  self.instructions+=1
  if address==0x802f06b4:self.last_ground_normal=struct.unpack('>3f',bytes(u.mem_read(u.reg_read(UC_PPC_REG_1)+0xc8,12)))
  allowed=((0x802f0364,0x802f0818),(0x802ef290,0x802efb7c),(0x802edf84,0x802ee098),(0x80193498,0x801934ec),(0x80193154,0x80193178),(0x80193010,0x8019304c),(0x80191810,0x801918a0),(0x801916dc,0x80191774),(0x801928bc,0x80192950),(0x80307cc8,0x80307d1c),(0x802f3e6c,0x802f423c),(0x803078e4,0x80307a00),(0x80193364,0x8019338c))
  allowed+=self.extra_allowed
  if not any(lo<=address<hi for lo,hi in allowed):raise ValueError(f'top reference escaped at{address:08x}')
  w=struct.unpack('>I',bytes(u.mem_read(address,4)))[0];op=w>>26
  d,a,b,c=((w>>bit)&31 for bit in (21,16,11,6))
  if op==63 and ((w>>1)&1023)==26: # original frsqrte, pinned external Gekko model
   self.putfloating(d,self.sqrt_reference.estimate(self.floating(b)))
  elif op==48: # lfs broadcasts to paired lanes on Gekko
   disp=w&65535;disp=disp-65536 if disp&32768 else disp
   at=(u.reg_read(UC_PPC_REG_0+a) if a else 0)+disp
   value=struct.unpack('>f',bytes(u.mem_read(at,4)))[0];self.putpair(d,(value,value))
  elif op in (56,60):
   if (w>>12)&7:raise ValueError('unsupported quantization')
   disp=w&4095;disp=disp-4096 if disp&2048 else disp
   at=(u.reg_read(UC_PPC_REG_0+a) if a else 0)+disp;single=(w>>15)&1
   if op==56:
    p=struct.unpack('>f' if single else '>2f',bytes(u.mem_read(at,4 if single else 8)))
    self.putpair(d,(p[0],1.0 if single else p[1]))
   else:u.mem_write(at,struct.pack('>f' if single else '>2f',*self.pair(d)[:1 if single else 2]))
  elif op==4:
   xo=(w>>1)&1023;short=(w>>1)&31
   pa,pb,pc=self.pair(a),self.pair(b),self.pair(c)
   if xo in (528,560,592,624):
    first=0 if xo in (528,560) else 1;second=0 if xo in (528,592) else 1
    result=(pa[first],pb[second])
   elif xo==40:result=[-v for v in pb]
   elif short in (12,13):result=[pa[i]*pc[short-12] for i in range(2)]
   elif short in (14,15):result=[pa[i]*pc[short-14]+pb[i] for i in range(2)]
   elif short==10:result=[pa[0]+pb[1],pc[1]]
   elif short==20:result=[pa[i]-pb[i] for i in range(2)]
   elif short==21:result=[pa[i]+pb[i] for i in range(2)]
   elif short==25:result=[pa[i]*pc[i] for i in range(2)]
   elif short==28:result=[pa[i]*pc[i]-pb[i] for i in range(2)]
   elif short==29:result=[pa[i]*pc[i]+pb[i] for i in range(2)]
   else:raise ValueError(f'unsupported PS {w:08x} at{address:08x}')
   self.putpair(d,[f32(v) for v in result])
  else:return
  u.reg_write(UC_PPC_REG_PC,address+4)
 def query_mesh(self,point,instance_raw,asset,mask=0):
  if len(instance_raw)!=64 or len(asset)<16 or len(asset)>0x20000:raise ValueError("Invalid reference input size")
  u=self.u;self.pair1={};self.instructions=0;self.last_ground_normal=None
  ci=bytearray(instance_raw);struct.pack_into('>I',ci,28,0x60010000)
  u.mem_write(0x60000000,struct.pack('>I',mask));u.mem_write(0x60000100,struct.pack('>3f',*point));u.mem_write(0x60000200,bytes(ci));u.mem_write(0x60000300,bytes(64));u.mem_write(0x60000400,struct.pack('>f',123456));u.mem_write(0x60010000,asset)
  for reg,value in ((UC_PPC_REG_1,0x7000ff00),(UC_PPC_REG_3,0x60000000),(UC_PPC_REG_4,0x60000100),(UC_PPC_REG_5,0x60000200),(UC_PPC_REG_6,0x60000300),(UC_PPC_REG_7,0x60000400),(UC_PPC_REG_LR,0x6000fff0)):u.reg_write(reg,value)
  u.emu_start(0x802f0364,0x6000fff0,timeout=200000,count=200000)
  if u.reg_read(UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('top reference budget exceeded')
  return dict(hit=bool(u.reg_read(UC_PPC_REG_3)),triangle=bytes(u.mem_read(0x60000300,48)).hex(),height_delta=struct.unpack('>f',bytes(u.mem_read(0x60000400,4)))[0],query_normal=self.last_ground_normal,instructions=self.instructions)

 def query_wall_bank(self,a,b,ci_raw,asset,mask=0):
  if len(ci_raw)!=64 or len(asset)<16 or len(asset)>0x20000:raise ValueError("Invalid reference input size")
  u=self.u;self.pair1={};self.instructions=0;ci=bytearray(ci_raw);struct.pack_into('>I',ci,28,0x60010000)
  u.mem_write(0x60000000,struct.pack('>I',mask));u.mem_write(0x60000200,bytes(ci));u.mem_write(0x60000300,bytes(128));u.mem_write(0x60000600,struct.pack('>II',0x60000700,0x60000704));u.mem_write(0x60000700,struct.pack('>I',0x60000200));u.mem_write(0x60000800,struct.pack('>4f4f',*a,1,*b,1));u.mem_write(0x60010000,asset)
  for reg,value in ((UC_PPC_REG_1,0x7000ff00),(UC_PPC_REG_3,0x60000000),(UC_PPC_REG_4,0x60000600),(UC_PPC_REG_5,0x60000800),(UC_PPC_REG_6,0x60000300),(UC_PPC_REG_LR,0x6000fff0)):u.reg_write(reg,value)
  u.emu_start(0x802f3e6c,0x802f4000,timeout=200000,count=200000)
  if u.reg_read(UC_PPC_REG_PC)!=0x802f4000:raise ValueError('wall query exceeded budget')
  selected=u.reg_read(UC_PPC_REG_22)
  point=struct.unpack('>3f',bytes(u.mem_read(u.reg_read(UC_PPC_REG_1)+8,12))) if selected else None
  return dict(hit=bool(selected),asset_relative_wall_offset=selected-0x60010000 if selected else None,point=point,instructions=self.instructions)

 def query_wall_contact(self,a,b,ci_raw,asset,mask=0):
  if len(ci_raw)!=64 or len(asset)<16 or len(asset)>0x20000:raise ValueError("Invalid reference input size")
  u=self.u;self.pair1={};self.instructions=0;ci=bytearray(ci_raw);struct.pack_into('>I',ci,28,0x60010000)
  u.mem_write(0x60000000,struct.pack('>I',mask));u.mem_write(0x60000200,bytes(ci));u.mem_write(0x60000300,bytes(128));u.mem_write(0x60000600,struct.pack('>II',0x60000700,0x60000704));u.mem_write(0x60000700,struct.pack('>I',0x60000200));u.mem_write(0x60000800,struct.pack('>4f4f',*a,1,*b,1));u.mem_write(0x60010000,asset)
  for reg,value in ((UC_PPC_REG_1,0x7000ff00),(UC_PPC_REG_3,0x60000000),(UC_PPC_REG_4,0x60000600),(UC_PPC_REG_5,0x60000800),(UC_PPC_REG_6,0x60000300),(UC_PPC_REG_LR,0x6000fff0)):u.reg_write(reg,value)
  u.emu_start(0x802f3e6c,0x6000fff0,timeout=200000,count=200000)
  if u.reg_read(UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('wall query exceeded budget')
  raw=bytes(u.mem_read(0x60000300,88))
  return dict(hit=bool(u.reg_read(UC_PPC_REG_3)),point=struct.unpack_from('>3f',raw,0),normal=struct.unpack_from('>3f',raw,16),material_token=struct.unpack_from('>I',raw,64)[0],distance_squared=struct.unpack_from('>f',raw,68)[0],raw_result=raw.hex(),instructions=self.instructions)
