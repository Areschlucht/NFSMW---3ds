#!/usr/bin/env python3
"""Bounded unchanged DoWheelForces late-command comparison (no source bytes output)."""
import argparse,ctypes as C,json,random,struct,subprocess,tempfile
from pathlib import Path
from map_recovery_contact_reference import OriginalContactReference
from build_vehicle_dynamics import MODULES,ROOT
f32=lambda x:C.c_float(x).value
class Input(C.Structure):_fields_=[('matrix',C.c_float*16),('angular',C.c_float*3),('yaw',C.c_float),('style',C.c_uint32),('previous',C.c_uint32)]
class Output(C.Structure):_fields_=[('wrench',C.c_bool),('raise_',C.c_bool),('angular_',C.c_bool),('force',C.c_float*3),('torque',C.c_float*3),('raise_y',C.c_float),('angular',C.c_float*3),('contacts',C.c_uint32)]
class Reference(OriginalContactReference):
 def __init__(self,raw):
  super().__init__(raw,None);self.extra_allowed=((0x8024b014,0x8024b168),(0x80193088,0x801930a8),(0x801932e0,0x8019330c),(0x801935a4,0x801935e8));self.calls=[]
 def _hook(self,u,pc,size,data):
  r=self.reg
  if pc in (0x6000f000,0x6000f010,0x6000f020,0x6000f030):
   if pc==0x6000f000:u.reg_write(r.UC_PPC_REG_3,4)
   elif pc==0x6000f010:self.calls.append(('wrench',bytes(u.mem_read(u.reg_read(r.UC_PPC_REG_4),12)),bytes(u.mem_read(u.reg_read(r.UC_PPC_REG_5),12))))
   elif pc==0x6000f020:self.calls.append(('raise',struct.pack('>f',self.floating(1))))
   else:self.calls.append(('angular',bytes(u.mem_read(u.reg_read(r.UC_PPC_REG_4),12))))
   u.reg_write(r.UC_PPC_REG_PC,u.reg_read(r.UC_PPC_REG_LR));return
  super()._hook(u,pc,size,data)
 def apply(self,x,forces,moments,contacts,raise_y):
  r=self.reg;u=self.u;self.calls=[];self.pair1={};self.instructions=0;sp=0x7000fc00;owner=0x60001000;common=0x60003000;body=0x60004000;table=0x60005000
  u.mem_write(sp,bytes(0x300));u.mem_write(owner,bytes(0x300));u.mem_write(common,bytes(0xe0));u.mem_write(body,struct.pack('>II',0,table));u.mem_write(table,bytes(0x200));u.mem_write(owner+0xf0,struct.pack('>I',body));u.mem_write(owner+0xa8,struct.pack('>I',0x60006000));u.mem_write(0x6000604c,struct.pack('>f',x.yaw));u.mem_write(owner+0x104,struct.pack('>I',x.previous));u.mem_write(owner+0x54,struct.pack('>I',table));
  for off,pc in ((0x18,0x6000f000),(0x110,0x6000f010),(0x100,0x6000f020),(0xd0,0x6000f030)):u.mem_write(table+off,struct.pack('>h2xI',0,pc))
  u.mem_write(common,struct.pack('>16f',*x.matrix));u.mem_write(common+0x90,struct.pack('>3f',*x.angular));u.mem_write(common+0xc8,struct.pack('>h',x.style))
  summed=lambda a:[f32(f32(f32(f32(0+a[0][j])+a[1][j])+a[2][j])+a[3][j]) for j in range(3)]
  u.mem_write(sp+0x88,struct.pack('>3f',*summed(forces)));u.mem_write(sp+0x78,struct.pack('>3f',*summed(moments)));u.mem_write(sp+0x160,struct.pack('>I',contacts));u.mem_write(sp+0x17c,struct.pack('>I',common+0x60));u.mem_write(sp+0x174,struct.pack('>I',0x60007000));u.mem_write(0x60007000,struct.pack('>4I',*[0x60008000+i*0x200 for i in range(4)]))
  for i in range(4):u.mem_write(0x60008000+i*0x200,bytes(0x120))
  for reg,val in ((1,sp),(20,sp+0x88),(25,sp+0x78),(24,common+0x10),(26,owner),(28,common),(23,0x20000000 if not contacts else 0x40000000)):
   u.reg_write(r.UC_PPC_REG_0+reg,val)
  self.putfloating(26,raise_y);u.emu_start(0x8024b014,0x8024b168,count=5000,timeout=1000000)
  return self.calls

def verify(dol,output):
 ref=Reference(dol.read_bytes());rng=random.Random(4984);count=0
 shim='''#include "mw_vehicle_runtime.h"
 bool chassis_test(const MwVehicleRuntimeChassisInput *in,const float f[12],const float t[12],unsigned contacts,float raise_y,MwVehicleRuntimeChassisOutput *out){MwVehicleDynamicsOutput w={0};for(unsigned i=0;i<4;i++){w.ground[i].world_force=(MwPhysicsContactVector){f[i*3],f[i*3+1],f[i*3+2]};w.world_moment[i]=(MwPhysicsContactVector){t[i*3],t[i*3+1],t[i*3+2]};w.ground[i].suspension.has_contact=i<contacts;}w.ground[1].suspension.penetration_excess=raise_y;return mw_vehicle_runtime_chassis_commands(in,&w,out);}
 '''
 with tempfile.TemporaryDirectory() as tmp:
  tmp=Path(tmp);(tmp/'shim.c').write_text(shim);mods=list(dict.fromkeys(MODULES+['mw_vehicle_runtime','mw_original_vehicle_mechanical','mw_original_power','mw_original_player_input','mw_original_rigid_body','mw_physics_grip','mw_physics_transmission_engine','mw_physics_transmission_auto','mw_physics_transmission_policy','mw_physics_transmission_nos']))
  subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(ROOT/'include'),str(tmp/'shim.c'),*[str(ROOT/'source_bmw'/(m+'.c')) for m in mods],'-lm','-o',str(tmp/'test.so')],check=True)
  fn=C.CDLL(str(tmp/'test.so')).chassis_test;fn.argtypes=[C.POINTER(Input),C.POINTER(C.c_float),C.POINTER(C.c_float),C.c_uint,C.c_float,C.POINTER(Output)];fn.restype=C.c_bool
  for i in range(2048):
   x=Input();x.matrix[:]=rng.choice([(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1),(1,0,0,0,0,.6,.8,0,0,-.8,.6,0,0,0,0,1),(0,0,-1,0,0,1,0,0,1,0,0,0,0,0,0,1)]);x.angular[:]=[rng.uniform(-10,10) for _ in range(3)];x.yaw=rng.choice([.26,.5,1,2]);x.style=i%2;x.previous=(i//5)%5;contacts=i%5;raise_y=f32(rng.choice([0,.03,.2]))
   forces=[[f32(rng.uniform(-20000,20000)) for _ in range(3)] for _ in range(4)];moments=[[f32(rng.uniform(-30000,30000)) for _ in range(3)] for _ in range(4)]
   # This source entry is only reached when at least one contact was accepted.
   if not contacts:continue
   want=ref.apply(x,forces,moments,contacts,raise_y);o=Output();assert fn(C.byref(x),(C.c_float*12)(*sum(forces,[])),(C.c_float*12)(*sum(moments,[])),contacts,raise_y,C.byref(o));got=[('wrench',struct.pack('>3f',*o.force),struct.pack('>3f',*o.torque))]
   if o.raise_:got.append(('raise',struct.pack('>f',o.raise_y)))
   if o.angular_:got.append(('angular',struct.pack('>3f',*o.angular)))
   if got!=want:raise AssertionError((i,got,want))
   count+=1
 report={'original_late_command_cases':count,'float_bit_mismatches':0,'range':'8024B014..8024B168','limits':['Precomputed wheel sums supplied at original late-function boundary; the original earlier contact/moment stage is separately compared','External body virtual commands captured without modifying original code','No full vehicle/world collision equivalence implied']};output.write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.dol,a.output),indent=2))
