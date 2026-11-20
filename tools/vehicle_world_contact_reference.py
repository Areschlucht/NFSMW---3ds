#!/usr/bin/env python3
"""Bounded original static-wall contact and RBVehicle modifier comparisons.

Original game executable and Dolphin estimate oracle stay private. Provider
getter values are explicit inputs; this does not claim original world broadphase,
source material lookup, callback event dispatch or full ground collision.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from build_vehicle_world import PrimitiveOriginal,Geometry,Shape
from vehicle_rigid_body_reference import make_state
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
from map_recovery_contact_reference import OriginalContactReference
from vehicle_ppc_reference import DOL_SHA256
ROOT=Path(__file__).resolve().parents[1]
class Barrier(C.Structure):
 _fields_=[('points',(C.c_float*3)*2),('inverse',C.c_float),('material',C.c_uint32),('ci',C.c_uint32),('asset',C.c_uint32),('section',C.c_uint16),('collision',C.c_uint16),('asset_index',C.c_uint16),('wall_index',C.c_uint16),('instance_flags',C.c_uint16),('group',C.c_uint16),('material_index',C.c_uint8),('flags',C.c_uint8)]
class Contact(C.Structure):
 _fields_=[('point',C.c_float*3),('normal',C.c_float*3),('penetration',C.c_float),('translation',C.c_float*3),('material',C.c_uint32),('ci',C.c_uint32),('asset',C.c_uint32),('wall',C.c_uint16),('section',C.c_uint16)]
class WallOriginal(PrimitiveOriginal):
 def __init__(self,*a):
  super().__init__(*a);self.extra_allowed+=((0x802f338c,0x802f390c),(0x80089320,0x80089398),(0x80193088,0x801930a8));self.packet=None
 def _hook(self,u,pc,size,data):
  if pc==0x6000a000:
   self.packet=bytes(u.mem_read(u.reg_read(self.reg.UC_PPC_REG_4),88));self.callback_point=bytes(u.mem_read(u.reg_read(self.reg.UC_PPC_REG_5),12))
   u.reg_write(self.reg.UC_PPC_REG_3,0);u.reg_write(self.reg.UC_PPC_REG_PC,u.reg_read(self.reg.UC_PPC_REG_LR));return
  if pc==0x802f365c:
   self.orientation_inputs=[struct.unpack('>3f',u.mem_read(u.reg_read(self.reg.UC_PPC_REG_3),12)),struct.unpack('>3f',u.mem_read(u.reg_read(self.reg.UC_PPC_REG_4),12))]
  super()._hook(u,pc,size,data)
 def wall(self,g,b,mask,force):
  u=self.u;r=self.reg;self.pair1={};self.instructions=0;self.packet=None;self.orientation_inputs=None
  def pack(g):return struct.pack('>39f2H4f',*g.floats,g.shape,g.penetrates_other,*g.delta,g.overlap)
  u.mem_write(0x7000f000,bytes(4096));u.mem_write(self.OWNER,pack(g));u.mem_write(0x60010000,struct.pack('>2I',mask,0));u.mem_write(0x60010100,struct.pack('>2I',0x60010200,0x60010228))
  raw=bytearray(40);struct.pack_into('>3f',raw,0,*b.points[0]);struct.pack_into('>3f',raw,16,*b.points[1]);raw[13]=b.flags;struct.pack_into('>fIf',raw,28,b.inverse,0xabcdef01,0);u.mem_write(0x60010200,bytes(raw))
  u.mem_write(0x60010300,struct.pack('>I',0x60010400));u.mem_write(0x60010400,bytes(16));u.mem_write(0x60010408,struct.pack('>II',0,0x6000a000))
  for i,v in [(1,0x7000ff00),(3,0x60010000),(4,self.OWNER),(5,0x60010100),(6,0x60010300),(7,0),(8,int(force))]:u.reg_write(r.UC_PPC_REG_0+i,v)
  u.reg_write(r.UC_PPC_REG_LR,0x6000fff0);u.emu_start(0x802f338c,0x6000fff0,count=60000,timeout=200000)
  if u.reg_read(r.UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('budget')
  raw=bytes(u.mem_read(self.OWNER,176));eg=Geometry();eg.floats[:]=struct.unpack_from('>39f',raw);eg.shape,eg.penetrates_other=struct.unpack_from('>2H',raw,156);eg.delta[:]=struct.unpack_from('>3f',raw,160);eg.overlap=struct.unpack_from('>f',raw,172)[0]
  c=Contact()
  if self.packet:
   c.point[:]=struct.unpack('>3f',self.callback_point);c.normal[:]=struct.unpack_from('>3f',self.packet,16);c.penetration=struct.unpack_from('>f',self.packet,28)[0]
   for i in range(3):c.translation[i]=C.c_float(c.normal[i]*c.penetration).value
  return u.reg_read(r.UC_PPC_REG_3),eg,c
class Body(C.Structure):
 _fields_=[('mass',C.c_float),('inertia',C.c_float*3),('cg',C.c_float*3),('position',C.c_float*3),('matrix',C.c_float*16),('velocity',C.c_float*3),('angular',C.c_float*3),('scale',C.c_float*3),('elasticity',C.c_float)]
class ModifyOriginal(OriginalContactReference):
 OWNER=0x60001000
 def __init__(self,*a):
  super().__init__(*a);self.extra_allowed+=((0x8023c33c,0x8023c558),(0x80236954,0x80236974),(0x80083c24,0x80083c74),(0x80193088,0x801930a8))
 def _hook(self,u,pc,size,data):
  r=self.reg
  # Exact actual getter return values, provider semantics are caller inputs.
  if pc in (0x8023c364,0x8023c380,0x8023c3a0,0x8023c3e4):
   target,value={0x8023c364:(0x8023c380,0x60011000),0x8023c380:(0x8023c398,self.player),0x8023c3a0:(0x8023c3c4,0x60011100),0x8023c3e4:(0x8023c3fc,0x60011200)}[pc]
   if pc==0x8023c3a0:
    u.reg_write(r.UC_PPC_REG_28,0x6001130c);u.reg_write(r.UC_PPC_REG_31,u.reg_read(r.UC_PPC_REG_1)+8)
   u.reg_write(r.UC_PPC_REG_3,value);u.reg_write(r.UC_PPC_REG_PC,target);return
  super()._hook(u,pc,size,data)
 def modify(self,s,player,f,v,n,scale):
  self.pair1={};self.instructions=0;self.player=int(player);u=self.u;r=self.reg
  owner=bytearray(0x140);struct.pack_into('>I',owner,0x94,0x60011400);u.mem_write(self.OWNER,bytes(owner));spec=bytearray(0x100);struct.pack_into('>3f',spec,0x20,*scale);u.mem_write(0x60011400,bytes(spec))
  u.mem_write(0x60011100,struct.pack('>3f',*f));u.mem_write(0x60011200,struct.pack('>3f',*v));u.mem_write(0x60011300,struct.pack('>6f',0,0,0,*n))
  raw=bytearray(0x118);struct.pack_into('>3f3f',raw,0x80,*s.inertia,*s.cg);struct.pack_into('>f',raw,0x10c,s.elasticity);u.mem_write(0x60011500,bytes(raw));u.mem_write(0x7000f000,bytes(4096))
  for i,val in [(1,0x7000ff00),(3,self.OWNER),(4,0),(5,0x60011300),(6,0x60011500)]:u.reg_write(r.UC_PPC_REG_0+i,val)
  u.reg_write(r.UC_PPC_REG_LR,0x6000fff0);u.emu_start(0x8023c33c,0x6000fff0,count=4000,timeout=200000)
  raw=bytes(u.mem_read(0x60011500,0x118));return struct.unpack_from('>6f',raw,0x80)+struct.unpack_from('>3f',raw,0xbc)+struct.unpack_from('>f',raw,0x10c)

def verify_wall(lib,dol,dolphin,cases):
    lib.mw_vehicle_world_wall_contact.argtypes=[C.POINTER(Geometry),C.POINTER(Barrier),C.c_uint32,C.c_bool,C.POINTER(Contact)]
    rng=random.Random(0x2f338c);errors=[];hits=0
    with DolphinFrsqrteReference(dolphin) as est:
     ref=WallOriginal(dol.read_bytes(),est)
     for i in range(cases):
      b=Barrier();b.points[0][:]=(-4,3,rng.uniform(-1,1));b.points[1][:]=(4,-1,rng.uniform(-1,1));x=b.points[0][0]-b.points[1][0];z=b.points[0][2]-b.points[1][2];b.inverse=1/(x*x+z*z)**.5;b.flags=rng.choice([0,16,2,18]);mask=rng.choice([0,0,2]);force=bool(i%2)
      if i%4==0:
       # Source-sized world coordinates, rotated/reversed barriers, nonunit
       # transformed normals and either top/bottom order exercise rounding.
       center=[rng.uniform(-3000,3000),rng.uniform(-200,200),rng.uniform(-3000,3000)]
       dx,dz=rng.uniform(-12,12),rng.uniform(-12,12)
       if abs(dx)+abs(dz)<.01:dx=1
       b.points[0][:]=(center[0]-dx,center[1]+rng.uniform(-4,4),center[2]-dz)
       b.points[1][:]=(center[0]+dx,center[1]+rng.uniform(-4,4),center[2]+dz)
       x=b.points[0][0]-b.points[1][0];z=b.points[0][2]-b.points[1][2]
       b.inverse=rng.choice([.5,1,2])/(x*x+z*z)**.5
      s=Shape();s.kind=1+i%2;s.quaternion[:]=(0,0,0,1);s.half_extents[:]=(.8,.5,2)
      a=make_state(rng,i);a.position[:]=(rng.uniform(-5,5),rng.uniform(-2,4),rng.uniform(-3,3));bb=type(a).from_buffer_copy(bytes(a))
      for axis in range(3):
       center=(b.points[0][axis]+b.points[1][axis])*.5
       a.position[axis]+=center;bb.position[axis]=a.position[axis]+rng.uniform(-1,1)
      g,_=ref.geometry(s,a,bb);actual=Geometry.from_buffer_copy(bytes(g));c=Contact();h=lib.mw_vehicle_world_wall_contact(C.byref(actual),C.byref(b),mask,force,C.byref(c));eh,eg,ec=ref.wall(g,b,mask,force);hits+=eh
      if h!=eh or bytes(actual)!=bytes(eg) or (h and bytes(c)[:40]!=bytes(ec)[:40]):
       errors.append({'orientation_inputs':ref.orientation_inputs,'barrier':list(b.points[0])+list(b.points[1])+[b.inverse,b.flags,mask,int(force)],'case':i,'hit':[h,eh],'geometry_words':[k for k in range(44) if bytes(actual)[k*4:k*4+4]!=bytes(eg)[k*4:k*4+4]],'contact_words':[k for k in range(10) if bytes(c)[k*4:k*4+4]!=bytes(ec)[k*4:k*4+4]],'actual':list(c.point)+list(c.normal)+[c.penetration]+list(c.translation),'expected':list(ec.point)+list(ec.normal)+[ec.penetration]+list(ec.translation)})
    report={'cases':cases,'hits':hits,'mismatches':len(errors),'errors':errors[:8]}
    return report

def verify_modifier(lib,dol,dolphin,cases):
    lib.mw_vehicle_world_modify_collision.argtypes=[C.POINTER(Body),C.c_bool]+[C.POINTER(C.c_float)]*4
    lib.mw_vehicle_world_modify_collision.restype=C.c_bool
    rng=random.Random(0x23c33c);errors=[]
    with DolphinFrsqrteReference(dolphin) as est:
     ref=ModifyOriginal(dol.read_bytes(),est)
     for i in range(cases):
      s=Body();s.inertia[:]=[rng.uniform(.01,3000) for k in range(3)];s.cg[:]=[rng.uniform(-2,2) for k in range(3)];s.elasticity=rng.uniform(-.1,1)
      f=(C.c_float*3)(*[rng.uniform(-1.1,1.1) for k in range(3)]);n=(C.c_float*3)(*[rng.uniform(-2,2) for k in range(3)]);v=(C.c_float*3)(*[rng.uniform(-20,20) for k in range(3)]);scale=(C.c_float*3)(*[rng.uniform(0,2) for k in range(3)])
      expected=ref.modify(s,bool(i%2),f,v,n,scale)
      if not lib.mw_vehicle_world_modify_collision(C.byref(s),bool(i%2),f,v,n,scale):raise ValueError('native rejected')
      actual=tuple(s.inertia)+tuple(s.cg)+tuple(s.scale)+(s.elasticity,)
      if struct.pack('=10f',*expected)!=struct.pack('=10f',*actual):errors.append({'case':i,'actual':actual,'expected':expected})
    return {'cases':cases,'mismatches':len(errors),'errors':errors[:8]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dol',type=Path,required=True)
    p.add_argument('--dolphin-reference',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cases',type=int,default=1024)
    a=p.parse_args()
    if not 1<=a.cases<=10000:p.error('Bounded case count required')
    if hashlib.sha256(a.dol.read_bytes()).hexdigest()!=DOL_SHA256:raise ValueError('Unknown original executable')
    with tempfile.TemporaryDirectory(prefix='mw-world-contact-') as temp:
        so=Path(temp)/'world.so'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(ROOT/'include'),
          *[str(ROOT/'source_bmw'/f) for f in ['mw_vehicle_world.c','mw_vehicle_world_intersection.c','mw_body_collision_shapes.c','mw_gekko_math.c']],'-lm','-o',str(so)],check=True)
        lib=C.CDLL(str(so))
        report={'wall':verify_wall(lib,a.dol,a.dolphin_reference,a.cases),'modifier':verify_modifier(lib,a.dol,a.dolphin_reference,a.cases),
          'dol_sha256':DOL_SHA256,'limits':['Original pure contact/modifier calls with explicit provider state','Not original world broadphase, source material lookup or collision event dispatch','Bounded Gekko model excludes FPSCR/subnormal and rare binary64 FMA ties']}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:{kk:vv for kk,vv in v.items() if kk!='errors'} for k,v in report.items() if isinstance(v,dict)}))
    if report['wall']['mismatches'] or report['modifier']['mismatches']:raise SystemExit(1)
if __name__=='__main__':main()
