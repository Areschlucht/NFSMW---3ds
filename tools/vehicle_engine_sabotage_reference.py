#!/usr/bin/env python3
"""Unchanged original sabotage deadline/ripple stage and real Blow transition."""
import argparse,ctypes as C,json,random,struct,subprocess,tempfile
from pathlib import Path
from vehicle_player_input_reference import PlayerReference,ROOT,bits,f32
from unicorn.ppc_const import *
class Story(C.Structure):_fields_=[('deadline',C.c_float),('blown',C.c_uint8)]
class Reference(PlayerReference):
 def __init__(self,raw):
  super().__init__(raw);self.extra_allowed+=((0x802580f8,0x8025817c),(0x80255360,0x802553c8),(0x8031dad0,0x8031dbd0),(0x8031dcbc,0x8031dd98),(0x8031e4bc,0x8031e654),(0x8031e868,0x8031f4c0),(0x8031dbd0,0x8031dc98),(0x8031e07c,0x8031e1cc));self.blown_event=False
 def _hook(self,u,pc,size,data):
  if pc in (0x801eb8d0,0x801d79c8):
   if pc==0x801eb8d0:u.reg_write(UC_PPC_REG_3,0x6000b000)
   else:self.blown_event=True
   u.reg_write(UC_PPC_REG_PC,u.reg_read(UC_PPC_REG_LR));return
  super()._hook(u,pc,size,data)
 def stage(self,omega,deadline,blown,clock):
  u=self.u;self.blown_event=False;self.pair1={};self.instructions=0;owner=0x60001000
  u.mem_write(owner,bytes(0x200));u.mem_write(owner+0xf0,bits(omega));u.mem_write(owner+0x1a8,struct.pack('>I',blown)+bits(deadline));u.mem_write(owner+0x38,struct.pack('>I',0x60002000));u.mem_write(0x60002000,bytes(16));u.mem_write(owner+0x80,struct.pack('>I',0x60003000));u.mem_write(0x60003018,struct.pack('>h2xI',-0x7c,0x80255360));u.mem_write(0x8049896c,bits(clock));u.reg_write(UC_PPC_REG_1,0x7000ff00);u.reg_write(UC_PPC_REG_31,owner);u.reg_write(UC_PPC_REG_13,0x80506dc0);u.reg_write(UC_PPC_REG_2,0x80516dc0)
  u.emu_start(0x802580f8,0x8025817c,count=20000,timeout=1000000)
  return bytes(u.mem_read(owner+0xf0,4)),bytes(u.mem_read(owner+0x1ac,4)),struct.unpack('>I',u.mem_read(owner+0x1a8,4))[0],self.blown_event

def verify(dol,output):
 ref=Reference(dol.read_bytes());rng=random.Random(58148);cases=0
 with tempfile.TemporaryDirectory() as tmp:
  so=Path(tmp)/'stage.so';mods=['mw_physics_transmission_engine','mw_physics_transmission','mw_physics_transmission_policy','mw_physics_transmission_auto','mw_physics_transmission_nos','mw_physics_engine','mw_original_player_input','mw_physics_grip','mw_physics_brakes','mw_physics_tires','mw_vehicle_dynamics','mw_physics_ground','mw_physics_suspension','mw_physics_contact_frame','mw_physics_contact_geometry','mw_physics_contact_scale','mw_physics_contact','mw_physics_lateral','mw_physics_friction','mw_physics_transmission_distribution','mw_gekko_math']
  subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(ROOT/'include'),*[str(ROOT/'source_bmw'/(m+'.c')) for m in mods],'-lm','-o',str(so)],check=True)
  dll=C.CDLL(str(so));sine=C.CFUNCTYPE(C.c_float,C.c_float)(('mw_player_source_sine',dll));fn=dll.mw_physics_transmission_sabotage_stage;fn.argtypes=[C.POINTER(C.c_float),C.POINTER(Story),C.c_float,type(sine),C.POINTER(C.c_bool)];fn.restype=C.c_bool
  for i in range(2048):
   clock=f32(rng.uniform(0,500));deadline=f32(clock+rng.choice([-1,-.01,0,.01,.1,1,5]));deadline=0 if i%17==0 else deadline;blown=int(i%19==0);omega=f32(rng.uniform(0,1100));want=ref.stage(omega,deadline,blown,clock);value=C.c_float(omega);story=Story(deadline,blown);event=C.c_bool(True);assert fn(C.byref(value),C.byref(story),clock,sine,C.byref(event));got=bits(value.value),bits(story.deadline),story.blown,event.value
   if got!=want:raise AssertionError((i,got,want,omega,deadline,clock))
   cases+=1
 report={'original_sabotage_stage_cases':cases,'float_bit_mismatches':0,'range':'802580F8..8025817C','real_blow_function':'80255360..802553C8','limits':['Actual source clock BSS and original sinf execute unchanged; event allocator/dispatch captured','Whole engine legacy1536-case regression separately passes; story extension full-engine frame comparison still pending']};output.write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.dol,a.output),indent=2))
