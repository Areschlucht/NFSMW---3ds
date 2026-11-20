#!/usr/bin/env python3
"""Unpatched original CameraAnchor/SetForward/MakeSpace numerical evidence.
Complete driving-camera composition is a separate stage; no springs substituted.
"""
import argparse,ctypes,json,math,random,struct,subprocess,tempfile
from pathlib import Path
from map_recovery_contact_reference import OriginalContactReference
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
from mw_debug_info import DebugInfo
from camera_recovery_cubic_verify import Cubic,packed
from unicorn import ppc_const as r
class Anchor(ctypes.Structure):
 _fields_=[('velocity',ctypes.c_float*4),('speed',ctypes.c_float),('top_speed',ctypes.c_float),('position',ctypes.c_float*4),('dimensions',ctypes.c_float*4),('acceleration',ctypes.c_float*4),('matrix',ctypes.c_float*16)]
class Cache(ctypes.Structure):
 _fields_=[('angle',ctypes.c_uint16),('lag',ctypes.c_float),('height',ctypes.c_float),('lateral',ctypes.c_float),('fov',ctypes.c_uint16),('stiffness',ctypes.c_float),('tilting',ctypes.c_uint16),('index',ctypes.c_uint)]
class Tuning(ctypes.Structure):_fields_=[('scalar',ctypes.c_float*4),('vector',(ctypes.c_float*4)*10)]
class SourceData(ctypes.Structure):_fields_=[('hug',(ctypes.c_float*2)*5),('nos',ctypes.c_uint16)]
class DesiredInput(ctypes.Structure):_fields_=[('pov',ctypes.c_int),('timer',ctypes.c_uint32),('ground',ctypes.c_bool),('under',ctypes.c_bool),('nos',ctypes.c_bool),('snap',ctypes.c_bool),('dutch',ctypes.c_float*3)]
class Placement(ctypes.Structure):
 _fields_=[(x,ctypes.c_float*3) for x in ('eye','look','up')]+[('lifted',ctypes.c_bool)]
class Camera(ctypes.Structure):
 _fields_=[('fov',Cubic),('eye',Cubic*3),('look',Cubic*3),('forward',Cubic*3),('up',Cubic*3),('last_grounded',ctypes.c_uint32),('last_under',ctypes.c_uint32),('last_gear',ctypes.c_uint32),('ignore',ctypes.c_float),('impact',ctypes.c_float*2),('impact_seconds',ctypes.c_float*2),('samples',(ctypes.c_float*4)*5),('sum',ctypes.c_float*3),('average',ctypes.c_float*3),('count',ctypes.c_uint),('cursor',ctypes.c_uint),('initialized',ctypes.c_bool),('accel_lag',ctypes.c_bool),('look_back',ctypes.c_bool),('snap_next',ctypes.c_bool),('first_time',ctypes.c_bool),('perfect_focus',ctypes.c_bool)]
def anchor_be(a):return b''.join(struct.pack('>f',x) for x in struct.unpack('=34f',bytes(a)))
class DriveReference(OriginalContactReference):
 def __init__(self,raw,oracle,elf):
  self.under=False;self.dutch=(0.,0.,0.);self.provider_calls=[]
  super().__init__(raw,oracle)
  self.u.reg_write(r.UC_PPC_REG_13,0x80506dc0);self.u.reg_write(r.UC_PPC_REG_2,0x80516dc0)
  self.extra_allowed=((0x8005e0c8,0x8005e168),(0x803147c0,0x80314864),(0x8010ab28,0x8010abcc),(0x8007381c,0x80074b38),(0x802083fc,0x80208478),(0x80207eb8,0x8020826c),(0x800733d0,0x800736c4),(0x8020905c,0x802090a4),(0x8010b5fc,0x8010b704),(0x8005e050,0x8005e070),(0x800736c4,0x8007381c),(0x8005ce20,0x8005cf50),(0x8005d1f0,0x8005d338),(0x80071ec4,0x80071f2c),(0x80041b14,0x80041b34),(0x80208fa4,0x802090a4),(0x80045c90,0x80045cdc),(0x80042614,0x80042658),(0x800832bc,0x800832c4),(0x80082344,0x80082348),(0x80195400,0x801956e8),(0x80314d48,0x80314db4),(0x801956e8,0x80195744),(0x80060d28,0x80060d88),(0x8010abcc,0x8010ac40),(0x8010af38,0x8010b0fc),(0x800685d8,0x80068750),(0x8006098c,0x80060b8c),(0x8005e070,0x8005e090),(0x80329e5c,0x80329fa4),(0x8008095c,0x80081770),(0x802090a4,0x80209190),(0x80072fcc,0x800733d0),(0x80071f2c,0x80071f58),(0x8007293c,0x80072960),(0x80072988,0x80072990),(0x8020836c,0x802083c4),(0x80060e14,0x80060e84),(0x80329e28,0x80329e5c))
  with DebugInfo(elf) as d:self.vtable=d.symbols('_vt.16CubicCameraMover')[0]['address']
  # Unchanged numeric initializer fragment; f31's value is established by
  # original80080B18 load and r28 is an unrelated container scratch base.
  self.putfloating(31,struct.unpack('>f',self.dol.read(0x803d3a0c,4))[0]);self.u.reg_write(r.UC_PPC_REG_28,0x60005000)
  self.u.reg_write(r.UC_PPC_REG_1,0x7000ff00);self.u.emu_start(0x80080f8c,0x80081228,count=50000)
 def _hook(self,u,address,size,data):
  if address==0x80072b80:
   self.provider_calls.append('under_vehicle');u.reg_write(r.UC_PPC_REG_3,int(self.under));u.reg_write(r.UC_PPC_REG_PC,u.reg_read(r.UC_PPC_REG_LR));return
  if address==0x80067258:
   self.provider_calls.append('dutch');u.mem_write(0x60007000,struct.pack('>3f',*self.dutch));u.reg_write(r.UC_PPC_REG_3,0x60007000);u.reg_write(r.UC_PPC_REG_PC,u.reg_read(r.UC_PPC_REG_LR));return
  if address==0x802c2270:
   self.provider_calls.append('flush_accumulation');u.reg_write(r.UC_PPC_REG_PC,u.reg_read(r.UC_PPC_REG_LR));return
  return super()._hook(u,address,size,data)
 def call(self,address):
  u=self.u;u.reg_write(r.UC_PPC_REG_1,0x7000ff00);u.reg_write(r.UC_PPC_REG_LR,0x6000fff0);
  try:u.emu_start(address,0x6000fff0,count=50000)
  except Exception as error:raise RuntimeError(hex(u.reg_read(r.UC_PPC_REG_PC))) from error
  if u.reg_read(r.UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('camera source budget')
 def anchor(self,a,m,v,dt):
  u=self.u;u.mem_write(0x60000000,anchor_be(a)+bytes(292-136));u.mem_write(0x60001000,struct.pack('>16f',*m));u.mem_write(0x60002000,struct.pack('>3f',*v))
  for reg,x in [(3,0x60000000),(4,0x60001000),(5,0x60002000)]:u.reg_write(r.UC_PPC_REG_0+reg,x)
  self.putfloating(1,dt);self.call(0x800685d8);return bytes(u.mem_read(0x60000000,136))
 def setup(self,a,s,pov):
  m=bytearray(232);struct.pack_into('>I',m,8,self.vtable);struct.pack_into('>I',m,128,0x60001000);struct.pack_into('>I',m,144,0x60002000);struct.pack_into('>i',m,156,pov);struct.pack_into('>I',m,180,s.last_grounded)
  self.u.mem_write(0x60000000,bytes(m));self.u.mem_write(0x60001000,anchor_be(a)+bytes(292-136));self.u.mem_write(0x60002000,b''.join(packed(c) for c in s.forward));self.u.mem_write(0x60003000,struct.pack('>h',pov)+bytes(34))
 def forward(self,a,s,pov,timer,snap):
  self.setup(a,s,pov);u=self.u;u.mem_write(0x804800c0,struct.pack('>I',timer));u.reg_write(r.UC_PPC_REG_3,0x60000000);u.reg_write(r.UC_PPC_REG_4,0x60003000);u.reg_write(r.UC_PPC_REG_5,int(snap));self.call(0x80072fcc);return bytes(u.mem_read(0x60002000,132))
 def space(self,a,s,pov):
  self.setup(a,s,pov);u=self.u;u.reg_write(r.UC_PPC_REG_3,0x60000000);u.reg_write(r.UC_PPC_REG_4,0x60004000);self.call(0x80073218);return bytes(u.mem_read(0x60004000,64))
 def stage_setup(self,a,s,pov):
  self.setup(a,s,pov);u=self.u
  for at,items in [(0x60002400,[s.fov]),(0x60002500,s.eye),(0x60002600,s.look),(0x60002700,s.up)]:u.mem_write(at,b''.join(packed(c) for c in items))
  for off,at in [(132,0x60002400),(136,0x60002500),(140,0x60002600),(148,0x60002700),(228,0x60002800)]:u.mem_write(0x60000000+off,struct.pack('>I',at))
  for off,value in [(164,s.look_back),(184,s.last_under),(188,s.last_gear)]:u.mem_write(0x60000000+off,struct.pack('>I',value))
  u.mem_write(0x600000c0,struct.pack('>f',s.ignore));u.mem_write(0x600000d4,struct.pack('>4f',*s.impact,*s.impact_seconds))
  u.reg_write(r.UC_PPC_REG_1,0x7000f000);u.reg_write(r.UC_PPC_REG_31,0x60000000)
 def channels(self,a,s,t,pov,damping,drift,dt):
  self.stage_setup(a,s,pov);u=self.u;u.mem_write(0x600010a4,struct.pack('>2f',damping,drift))
  u.mem_write(0x7000f008,struct.pack('>44f',*struct.unpack('=44f',bytes(t))))
  avg=bytearray(40);avg[1:4]=bytes([5,s.count,s.cursor]);struct.pack_into('>I',avg,8,0x60009000);struct.pack_into('>3f',avg,12,*s.sum);struct.pack_into('>3f',avg,28,*s.average);u.mem_write(0x60002800,bytes(avg));u.mem_write(0x60009000,struct.pack('>20f',*[x for sample in s.samples for x in sample]))
  ignore=s.ignore-dt if s.ignore>0 else s.ignore;u.mem_write(0x600000c0,struct.pack('>f',ignore));u.mem_write(0x804a5fdc,bytes(4));u.mem_write(0x804a5fe0,bytes(4));u.mem_write(0x8043728c,bytes(4));u.mem_write(0x80437288,bytes(4))
  self.putfloating(28,dt);self.putfloating(30,damping);self.putfloating(29,drift)
  u.emu_start(0x80073fe8,0x8007437c,count=30000)
  if u.reg_read(r.UC_PPC_REG_PC)!=0x8007437c:raise ValueError('channels budget')
  return (b''.join(bytes(u.mem_read(at,n)) for at,n in [(0x60002400,44),(0x60002500,132),(0x60002600,132),(0x60002000,132),(0x60002700,132)]),bytes(u.mem_read(0x60002800,40)),bytes(u.mem_read(0x60009000,80)),bytes(u.mem_read(0x600000d4,16)))
 def placement(self,a,s,pov,timer,changing,dt,space):
  self.stage_setup(a,s,pov);u=self.u;u.mem_write(0x60004000,struct.pack('>16f',*space));u.mem_write(0x804800c0,struct.pack('>I',timer));u.mem_write(0x600010cc,struct.pack('>I',changing))
  u.reg_write(r.UC_PPC_REG_25,0x60004000);u.reg_write(r.UC_PPC_REG_30,int(2<=pov<=6));self.putfloating(28,dt)
  u.emu_start(0x80074444,0x80074b38,count=50000)
  if u.reg_read(r.UC_PPC_REG_PC)!=0x80074b38:raise ValueError('placement budget')
  stack=0x7000f000
  return (b''.join(bytes(u.mem_read(at,12)) for at in (stack+0xd8,stack+0x128,stack+0xc8))+bytes([bool(u.reg_read(r.UC_PPC_REG_26))]),bytes(u.mem_read(0x600000d4,16)),bytes(u.mem_read(0x600000bc,4)))
 def desired(self,a,s,p,t,i):
  self.setup(a,s,i.pov);u=self.u;self.under=i.under;self.dutch=list(i.dutch);self.provider_calls=[]
  for at,items in [(0x60002400,[s.fov]),(0x60002500,s.eye),(0x60002600,s.look),(0x60002700,s.up)]:u.mem_write(at,b''.join(packed(c) for c in items))
  for off,at in [(132,0x60002400),(136,0x60002500),(140,0x60002600),(148,0x60002700),(228,0x60002800)]:u.mem_write(0x60000000+off,struct.pack('>I',at))
  for off,value in [(160,s.accel_lag),(168,i.snap)]:u.mem_write(0x60000000+off,struct.pack('>I',value))
  u.mem_write(0x6000281c,struct.pack('>3f',*s.average));u.mem_write(0x600010c4,struct.pack('>I',i.ground));u.mem_write(0x600010b4,struct.pack('>I',i.nos));u.mem_write(0x804800c0,struct.pack('>I',i.timer))
  pov=bytearray(36);struct.pack_into('>hHfffH',pov,0,i.pov,p.angle,p.lag,p.height,p.lateral,p.fov);struct.pack_into('>h',pov,24,p.tilting);u.mem_write(0x60003000,bytes(pov));u.mem_write(0x60006000,struct.pack('>44f',*struct.unpack('=44f',bytes(t))))
  for reg,value in [(3,0x60000000),(4,0x60004000),(5,0x60003000),(6,0x60006000),(7,i.snap)]:u.reg_write(r.UC_PPC_REG_0+reg,value)
  self.call(0x8007381c)
  state=b''.join(bytes(u.mem_read(at,n)) for at,n in [(0x60002400,44),(0x60002500,132),(0x60002600,132),(0x60002000,132),(0x60002700,132)])
  return state,bytes(u.mem_read(0x60004000,64))
def verify(a):
 root=Path(__file__).resolve().parents[1];oracle=DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin');ref=DriveReference(a.dol.read_bytes(),oracle,a.elf);rng=random.Random(0x80073e50);counts=dict(anchor=0,forward=0,space=0,desired=0,sine=0,channels=0,placement=0,lens=0,atan_table=0,look_at=0)
 with tempfile.TemporaryDirectory() as td:
  so=Path(td)/'drive.so';sources=['mw_drive_camera','mw_original_camera_cubic','mw_original_camera_direction','mw_gekko_math'];subprocess.run(['cc','-std=c11','-O2','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),*[str(root/'source_bmw'/(x+'.c')) for x in sources],'-lm','-o',str(so)],check=True);lib=ctypes.CDLL(str(so));arr=ctypes.c_float*3;mat=ctypes.c_float*16
  lib.mw_drive_camera_anchor_update.argtypes=[ctypes.POINTER(Anchor),mat,arr,ctypes.c_float];lib.mw_drive_camera_anchor_update.restype=ctypes.c_bool
  lib.mw_drive_camera_forward.argtypes=[ctypes.POINTER(Camera),ctypes.POINTER(Anchor),ctypes.c_int,ctypes.c_uint32,ctypes.c_bool];lib.mw_drive_camera_forward.restype=ctypes.c_bool
  lib.mw_drive_camera_desired.argtypes=[ctypes.POINTER(Camera),ctypes.POINTER(Anchor),ctypes.POINTER(Cache),ctypes.POINTER(Tuning),ctypes.POINTER(SourceData),ctypes.POINTER(DesiredInput),mat];lib.mw_drive_camera_desired.restype=ctypes.c_bool
  lib.mw_drive_camera_sine_turns.argtypes=[ctypes.c_uint16];lib.mw_drive_camera_sine_turns.restype=ctypes.c_float
  lib.mw_drive_camera_space.argtypes=[ctypes.POINTER(Camera),ctypes.POINTER(Anchor),ctypes.c_bool,mat];lib.mw_drive_camera_space.restype=ctypes.c_bool
  source=SourceData();source.hug=type(source.hug).from_buffer_copy(struct.pack('=10f',*struct.unpack('>10f',bytes(ref.u.mem_read(0x8045ad44,40)))));source.nos=struct.unpack('>H',bytes(ref.u.mem_read(0x8045adb2,2)))[0]
  defaults=SourceData();lib.mw_drive_camera_source_data.argtypes=[ctypes.POINTER(SourceData)];lib.mw_drive_camera_source_data(ctypes.byref(defaults));assert bytes(defaults)==bytes(source)
  for angle in range(0,65536,17):
   ref.u.reg_write(r.UC_PPC_REG_3,angle);ref.call(0x8005ce20);expected=ref.floating(1);actual=lib.mw_drive_camera_sine_turns(angle)
   assert struct.pack('>f',actual)==struct.pack('>f',expected);counts['sine']+=1
  table=(ctypes.c_uint16*257)();lib.mw_drive_camera_lens_table.argtypes=[ctypes.POINTER(ctypes.c_uint16)];lib.mw_drive_camera_lens_table(table)
  assert struct.pack('>257H',*table)==bytes(ref.u.mem_read(0x80415fe4,514));counts['atan_table']=257
  lib.mw_drive_camera_fov_turns.argtypes=[ctypes.c_float,ctypes.POINTER(ctypes.c_uint16),ctypes.POINTER(ctypes.c_uint16)];lib.mw_drive_camera_fov_turns.restype=ctypes.c_bool
  for value in range(1,32768,7):
   half=value>>1;ref.u.reg_write(r.UC_PPC_REG_3,half);ref.call(0x8005ce20);sine=ctypes.c_float(ref.floating(1)).value;ref.u.reg_write(r.UC_PPC_REG_3,half);ref.call(0x8005cf28);cosine=ctypes.c_float(ref.floating(1)).value
   ref.putfloating(1,1.0);ref.putfloating(2,ctypes.c_float(sine/cosine).value);ref.call(0x8005d1f0);expected=(ref.u.reg_read(r.UC_PPC_REG_3)*2)&65535
   output=ctypes.c_uint16();assert lib.mw_drive_camera_fov_turns(float(value),table,ctypes.byref(output))
   assert output.value==expected,(value,output.value,expected);counts['lens']+=1
  for case in range(160):
   angle=rng.uniform(-math.pi,math.pi);m=mat(math.cos(angle),math.sin(angle),0,0,-math.sin(angle),math.cos(angle),0,0,0,0,1,0,*[rng.uniform(-100,100) for _ in range(3)],1);v=arr(*[rng.uniform(-100,100) for _ in range(3)]);old=Anchor();old.speed=rng.uniform(0,100)
   for i in range(3):old.position[i]=m[12+i]+rng.uniform(-1,1)
   dt=ctypes.c_float(rng.choice([0,.001,1/60,.1])).value;expected=ref.anchor(old,m,v,dt);actual=Anchor.from_buffer_copy(bytes(old));assert lib.mw_drive_camera_anchor_update(ctypes.byref(actual),m,v,dt)
   if anchor_be(actual)!=expected:raise AssertionError(('anchor',case,struct.unpack('>34f',expected),struct.unpack('>34f',anchor_be(actual))))
   counts['anchor']+=1
   for pov in (0,2,3,6):
    s=Camera();s.last_grounded=1000
    for i in range(3):s.forward[i]=Cubic(0,0,0,0,(ctypes.c_float*4)(0,0,0,0),0,.3,0,1)
    # Include full vertical-basis attenuation, reverse and snapped channels.
    old.matrix=m;old.speed=math.sqrt(sum(x*x for x in v));old.velocity[:3]=v[:];old.matrix[2]=rng.uniform(-.8,.8)
    for timer in (1000,2000,9000,0xfffffff0):
     snap=case%2==0;expected=ref.forward(old,s,pov,timer,snap);actual=Camera.from_buffer_copy(bytes(s));assert lib.mw_drive_camera_forward(ctypes.byref(actual),ctypes.byref(old),pov,timer,snap)
     if b''.join(packed(c) for c in actual.forward)!=expected:raise AssertionError(('forward',case,pov,timer,list(actual.forward[2].__dict__),expected.hex(),b''.join(packed(c) for c in actual.forward).hex()))
     counts['forward']+=1
    for i in range(3):s.forward[i].value=v[i]
    expected=ref.space(old,s,pov);out=mat();assert lib.mw_drive_camera_space(ctypes.byref(s),ctypes.byref(old),pov>=2,out)
    if struct.pack('>16f',*out)!=expected:raise AssertionError(('space',case,pov,struct.unpack('>16f',expected),list(out)))
    counts['space']+=1
  for case in range(400):
   car=Anchor();angle=rng.uniform(-math.pi,math.pi);car.matrix=mat(math.cos(angle),math.sin(angle),0,0,-math.sin(angle),math.cos(angle),0,0,0,0,1,0,0,0,0,1);car.position[:3]=[10,20,30];car.velocity[:3]=[rng.uniform(-30,30) for _ in range(3)];car.speed=rng.uniform(0,100);car.top_speed=rng.choice([0,70,100]);state=Camera();state.last_grounded=1000;state.last_under=500;state.accel_lag=case%2==0;state.average[:]=[rng.uniform(-20,20) for _ in range(3)]
   for field in ['fov','eye','look','forward','up']:
    cs=[state.fov] if field=='fov' else getattr(state,field)
    for c in cs:c.mode=1;c.duration=.3;c.value=rng.uniform(-1,1);c.target=c.value
   profile=Cache(rng.randrange(4000),-6,1.5,.2,16000,1,case%2,0);t=Tuning()
   for vector in range(10):
    for axis in range(3):t.vector[vector][axis]=rng.uniform(-.2,.2) if vector in (0,3,6) else (-5 if vector in (1,4,7) else 5)
   inp=DesiredInput(rng.choice([0,1,2,3,4,5,6]),rng.choice([1000,2000,9000]),case%3==0,case%4==0,case%5==0,case%6==0,(ctypes.c_float*3)(.01,.02,-.03))
   expected,space=ref.desired(car,state,profile,t,inp);actual=Camera.from_buffer_copy(bytes(state));out=mat();assert lib.mw_drive_camera_desired(ctypes.byref(actual),ctypes.byref(car),ctypes.byref(profile),ctypes.byref(t),ctypes.byref(source),ctypes.byref(inp),out)
   native=b''.join(packed(c) for field in [[actual.fov],actual.eye,actual.look,actual.forward,actual.up] for c in field)
   if native!=expected:raise AssertionError(('desired',case,[(i,struct.unpack_from('>f',native,i)[0],struct.unpack_from('>f',expected,i)[0]) for i in range(0,len(native),4) if native[i:i+4]!=expected[i:i+4]][:12]))
   assert struct.pack('>16f',*out)==space;counts['desired']+=1
  lib.mw_drive_camera_channels.argtypes=[ctypes.POINTER(Camera),ctypes.POINTER(Anchor),ctypes.POINTER(Tuning),ctypes.c_int,ctypes.c_float,ctypes.c_float,ctypes.c_float];lib.mw_drive_camera_channels.restype=ctypes.c_bool
  lib.mw_drive_camera_placement.argtypes=[ctypes.POINTER(Camera),ctypes.POINTER(Anchor),ctypes.c_int,ctypes.c_uint32,ctypes.c_bool,ctypes.c_float,mat,ctypes.POINTER(Placement)];lib.mw_drive_camera_placement.restype=ctypes.c_bool
  lib.mw_drive_camera_look_at.argtypes=[arr,arr,arr,mat];lib.mw_drive_camera_look_at.restype=ctypes.c_bool
  for case in range(1024):
   eye=arr(*[rng.uniform(-3000,3000) for _ in range(3)]);look=arr(*[eye[i]+rng.uniform(-10,10) for i in range(3)]);up=arr(*[rng.uniform(-1,1) for _ in range(3)])
   if case%17==0:look=arr(*eye)
   if case%19==0:up=arr(0,0,0)
   ref.u.mem_write(0x60008000,struct.pack('>9f',*eye,*look,*up))
   for reg,value in [(3,0x60008100),(4,0x60008000),(5,0x6000800c),(6,0x60008018)]:ref.u.reg_write(r.UC_PPC_REG_0+reg,value)
   ref.call(0x8010af38);expected=bytes(ref.u.mem_read(0x60008100,64));out=mat();assert lib.mw_drive_camera_look_at(eye,look,up,out)
   if struct.pack('>16f',*out)!=expected:raise AssertionError(('look_at',case,list(out),struct.unpack('>16f',expected)))
   counts['look_at']+=1
  for case in range(512):
   car=Anchor();car.matrix=mat(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1);car.acceleration[:3]=[rng.uniform(-80,80) for _ in range(3)];car.speed=rng.uniform(0,100)
   state=Camera();state.ignore=rng.choice([-1,0,.01,1]);state.count=rng.randrange(6);state.cursor=rng.randrange(5);state.look_back=case%2==0;state.last_under=rng.choice([0,600,1000]);state.last_gear=rng.choice([0,500,1000])
   for axis in range(3):
    for sample in range(5):state.samples[sample][axis]=rng.uniform(-30,30)
    state.sum[axis]=sum(x[axis] for x in state.samples)
    state.average[axis]=rng.uniform(-10,10)
   for field in ['fov','eye','look','forward','up']:
    for c in ([state.fov] if field=='fov' else getattr(state,field)):
     c.mode=1;c.duration=.3;c.value=rng.uniform(-5,5);c.target=rng.uniform(-5,5);c.state=rng.randrange(3);c.derivative=rng.uniform(-1,1)
   for index in range(2):state.impact[index]=rng.choice([0,.2,.8]);state.impact_seconds[index]=rng.choice([-.1,0,.01,.3,1])
   tuning=Tuning();tuning.scalar[:]=[.3,.4,.2,.5];tuning.vector[9][:3]=[.2,.3,.4];pov=rng.choice([0,1,2,3,6]);damping=ctypes.c_float(rng.uniform(0,1)).value;drift=ctypes.c_float(rng.uniform(0,1)).value;dt=ctypes.c_float(rng.choice([0,1/60,.1,.5])).value
   expected,avg,samples,impact=ref.channels(car,state,tuning,pov,damping,drift,dt);actual=Camera.from_buffer_copy(bytes(state));assert lib.mw_drive_camera_channels(ctypes.byref(actual),ctypes.byref(car),ctypes.byref(tuning),pov,damping,drift,dt)
   native=b''.join(packed(c) for field in [[actual.fov],actual.eye,actual.look,actual.forward,actual.up] for c in field)
   if native!=expected:raise AssertionError(('channels',case,[(i,struct.unpack_from('>f',native,i)[0],struct.unpack_from('>f',expected,i)[0]) for i in range(0,len(native),4) if native[i:i+4]!=expected[i:i+4]][:12]))
   assert bytes([5,actual.count,actual.cursor])==avg[1:4]
   if struct.pack('>3f',*actual.sum)!=avg[12:24] or struct.pack('>3f',*actual.average)!=avg[28:40]:raise AssertionError(('avg',case,list(actual.sum),struct.unpack('>3f',avg[12:24]),list(actual.average),struct.unpack('>3f',avg[28:40])))
   assert struct.pack('>20f',*[x for sample in actual.samples for x in sample])==samples
   assert struct.pack('>4f',*actual.impact,*actual.impact_seconds)==impact,('impact',case,list(actual.impact),list(actual.impact_seconds),struct.unpack('>4f',impact))
   counts['channels']+=1
   yaw=rng.uniform(-math.pi,math.pi);pitch=rng.uniform(-.4,.4);cy,sy,cp,sp=math.cos(yaw),math.sin(yaw),math.cos(pitch),math.sin(pitch);space=mat(cy*cp,sy*cp,sp,0,-sy,cy,0,0,-cy*sp,-sy*sp,cp,0,*[rng.uniform(-5000,5000) for _ in range(3)],1);timer=rng.choice([1000,2000,9000,0xfffffff0]);changing=case%3==0
   expected,impact,last_gear=ref.placement(car,state,pov,timer,changing,dt,space);actual=Camera.from_buffer_copy(bytes(state));placement=Placement();assert lib.mw_drive_camera_placement(ctypes.byref(actual),ctypes.byref(car),pov,timer,changing,dt,space,ctypes.byref(placement))
   native=struct.pack('>9f',*placement.eye,*placement.look,*placement.up)+bytes([placement.lifted])
   if native!=expected:raise AssertionError(('placement',case,pov,timer,list(state.impact),list(state.impact_seconds),state.last_gear,car.speed,tuple(state.eye[i].value for i in range(3)),tuple(state.look[i].value for i in range(3)),struct.unpack('>5f',bytes(ref.u.mem_read(0x80416fc0,20))),[(i,struct.unpack_from('>f',native,i)[0],struct.unpack_from('>f',expected,i)[0]) for i in range(0,36,4) if native[i:i+4]!=expected[i:i+4]],native[36:],expected[36:]))
   assert struct.pack('>4f',*actual.impact,*actual.impact_seconds)==impact,('impact',case,list(actual.impact),list(actual.impact_seconds),struct.unpack('>4f',impact))
   assert struct.pack('>I',actual.last_gear)==last_gear
   counts['placement']+=1
 oracle.close();report=dict(patched_instructions=0,exact_float_bit_cases=counts,limits=['Whole Anchor/Forward/MakeSpace/ordinarySetDesired routines and bounded Update numeric stages verified; full Update noise/world-query providers still separate','Explicit offline paired-single/reciprocal-estimate model; no runtime emulator']);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['dol','elf','output']:p.add_argument('--'+n,type=Path,required=True)
 verify(p.parse_args())
