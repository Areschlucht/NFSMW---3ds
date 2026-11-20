#!/usr/bin/env python3
"""Differential original Ginsu mapping, decoder and packet synthesis recovery.
Private original banks/executable are inputs; no original code/data is exported.
"""
import argparse,ctypes as C,hashlib,json,math,random,struct,subprocess,tempfile
from pathlib import Path
from map_recovery_contact_reference import OriginalContactReference
from mw_debug_info import DebugInfo
from unicorn import ppc_const as r
ROOT=Path(__file__).resolve().parents[1]
class Bank(C.Structure):
 _fields_=[(n,C.c_void_p) for n in ('data','frequency_positions','cycle_positions','samples')]+[('bytes',C.c_size_t)]+[(n,C.c_uint32) for n in ('segments','cycles','sample_count','rate')]+[(n,C.c_float) for n in ('min_frequency','max_frequency','min_period')]
class State(C.Structure):
 _fields_=[(n,C.c_int32) for n in ('playback','current','target','countdown','no_jump_remaining')]+[(n,C.c_uint32) for n in ('packet_size','overlap_size','no_jump_size')]+[('cached_block',C.c_int32),('decoded',C.c_float*32),('current_cycle',C.c_float),('packet',C.c_int16*1024),('cursor',C.c_uint32),('available',C.c_uint32),('ready',C.c_bool)]
def bits(x):return struct.pack('>f',x)
class Reference(OriginalContactReference):
 def __init__(self,raw):
  super().__init__(raw,None);self.extra_allowed=((0x800eac84,0x800ec180),(0x800be830,0x800be87c),(0x800dbab0,0x800dbae8));self.u.mem_map(0x61000000,0x1000000)
 def install(self,raw):
  lo,hi,n,c,s,hz=struct.unpack_from('<2f4I',raw,8);fp=struct.unpack_from('<'+str(n+1)+'I',raw,32);cp=struct.unpack_from('<'+str(c+1)+'I',raw,32+(n+1)*4);start=32+(n+c+2)*4
  self.u.mem_write(0x61000000,raw[start:]);self.u.mem_write(0x61100000,struct.pack('>'+str(n+1)+'I',*fp));self.u.mem_write(0x61200000,struct.pack('>'+str(c+1)+'I',*cp));b=bytearray(176);struct.pack_into('>2f4I3If',b,4,lo,hi,n,c,s,hz,0x61100000,0x61200000,0x61000000,float(min(b-a for a,b in zip(cp,cp[1:]))));struct.pack_into('>i',b,172,-1);self.u.mem_write(0x60000000,bytes(b));self.raw=raw
 def call(self,start,fp=None,integer=0,result='int'):
  u=self.u;u.reg_write(r.UC_PPC_REG_1,0x7000ff00);u.reg_write(r.UC_PPC_REG_LR,0x6000fff0);u.reg_write(r.UC_PPC_REG_3,0x60000000);u.reg_write(r.UC_PPC_REG_4,integer)
  if fp is not None:self.putfloating(1,fp)
  u.emu_start(start,0x6000fff0,count=100000)
  if u.reg_read(r.UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('sourcebudget')
  return self.floating(1) if result=='float' else C.c_int32(u.reg_read(r.UC_PPC_REG_3)).value
 def calibrate(self,rpm,minimum,maximum,bank_min):
  u=self.u;u.mem_write(0x60004000,bytes(224));u.mem_write(0x60005000,bytes(224));u.mem_write(0x60006000,bytes(192));u.mem_write(0x60004018,struct.pack('>I',0x60005000));u.mem_write(0x600050cc,struct.pack('>I',0x60006000));u.mem_write(0x60006098,struct.pack('>2f',minimum,maximum));u.reg_write(r.UC_PPC_REG_31,0x60004000);self.putfloating(1,rpm);u.emu_start(0x800be830,0x800be87c,count=1000)
  desired=struct.unpack('>f',bytes(u.mem_read(0x600040bc,4)))[0];u.mem_write(0x60007000,bytes(144));u.mem_write(0x60007040,struct.pack('>I',0x60004000));u.mem_write(0x60007084,struct.pack('>f',desired));u.mem_write(0x60007064,struct.pack('>f',bank_min));u.reg_write(r.UC_PPC_REG_31,0x60007000);u.reg_write(r.UC_PPC_REG_3,0);u.emu_start(0x800dbab0,0x800dbae8,count=1000)
  return self.floating(31),self.floating(30)
 def samples(self,at,count):
  self.u.reg_write(r.UC_PPC_REG_5,count);self.u.reg_write(r.UC_PPC_REG_6,0x60001000);assert self.call(0x800eb8d0,integer=at)==1
  return struct.unpack('>'+str(count)+'h',bytes(self.u.mem_read(0x60001000,count*2)))
 def packet(self,s):
  q=bytearray(68);struct.pack_into('>I',q,12,1024);struct.pack_into('>3I',q,16,s.no_jump_size,s.packet_size,s.overlap_size);struct.pack_into('>I',q,40,0x60000000);struct.pack_into('>5if',q,44,s.playback,s.current,s.target,s.countdown,s.no_jump_remaining,s.current_cycle)
  self.u.mem_write(0x60002000,bytes(q));self.u.reg_write(r.UC_PPC_REG_1,0x7000ff00);self.u.reg_write(r.UC_PPC_REG_3,0x60002000);self.u.reg_write(r.UC_PPC_REG_4,0x60003000);self.u.reg_write(r.UC_PPC_REG_LR,0x6000fff0)
  self.u.emu_start(0x800eb9f0,0x800ec134,count=250000)
  if self.u.reg_read(r.UC_PPC_REG_PC)!=0x800ec134:raise ValueError('packetbudget')
  return (struct.unpack('>'+str(s.packet_size)+'h',bytes(self.u.mem_read(0x60003000,s.packet_size*2))),struct.unpack('>5if',bytes(self.u.mem_read(0x6000202c,24))))
def verify(args):
 raw=args.dol.read_bytes();ref=Reference(raw);rng=random.Random(0x474e7375);counts=dict(calibration=0,banks=0,frequency=0,cycle=0,period=0,inverse=0,decoded_samples=0,packets=0,packet_samples=0);inventory=[]
 with tempfile.TemporaryDirectory() as td:
  so=Path(td)/'ginsu.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(ROOT/'include'),str(ROOT/'source_bmw/mw_ginsu.c'),'-lm','-o',str(so)],check=True);lib=C.CDLL(str(so))
  lib.mw_ginsu_engine_frequency.argtypes=[C.POINTER(Bank),C.c_float,C.c_float,C.c_float,C.POINTER(C.c_float),C.POINTER(C.c_float)];lib.mw_ginsu_engine_frequency.restype=C.c_bool
  lib.mw_ginsu_bank_open.argtypes=[C.POINTER(Bank),C.c_void_p,C.c_size_t];lib.mw_ginsu_start.argtypes=[C.POINTER(State),C.POINTER(Bank),C.c_float];lib.mw_ginsu_frequency.argtypes=[C.POINTER(State),C.POINTER(Bank),C.c_float,C.c_float];lib.mw_ginsu_packet.argtypes=[C.POINTER(State),C.POINTER(Bank),C.POINTER(C.c_int16),C.c_size_t];lib.mw_ginsu_samples.argtypes=[C.POINTER(State),C.POINTER(Bank),C.c_int32,C.POINTER(C.c_int16),C.c_uint32]
  for name in ['frequency_sample','cycle_sample','cycle_period','sample_cycle']:
   fn=getattr(lib,'mw_ginsu_'+name);fn.argtypes=[C.POINTER(Bank),C.c_int32 if name=='sample_cycle' else C.c_float,C.POINTER(C.c_float if name in ['cycle_period','sample_cycle'] else C.c_int32)]
  for n in ['bank_open','start','frequency','packet','samples','frequency_sample','cycle_sample','cycle_period','sample_cycle']:getattr(lib,'mw_ginsu_'+n).restype=C.c_bool
  for path in sorted(args.banks.glob('*.gin')):
   data=path.read_bytes();buffer=C.create_string_buffer(data);b=Bank();assert lib.mw_ginsu_bank_open(C.byref(b),buffer,len(data)),path;ref.install(data);s=State();assert lib.mw_ginsu_start(C.byref(s),C.byref(b),b.min_frequency)
   for i in range(80):
    rpm=C.c_float(rng.uniform(-1000,20000)).value;minimum=C.c_float(rng.uniform(100,3000)).value;maximum=C.c_float(rng.uniform(4000,14000)).value;grain=C.c_float();pitch=C.c_float();assert lib.mw_ginsu_engine_frequency(C.byref(b),rpm,minimum,maximum,C.byref(grain),C.byref(pitch));expected=ref.calibrate(rpm,minimum,maximum,b.min_frequency)
    if bits(expected[0])!=bits(grain.value) or bits(expected[1])!=bits(pitch.value):raise AssertionError((path.name,'calibration',expected,grain.value,pitch.value))
    counts['calibration']+=1
    f=C.c_float(rng.uniform(b.min_frequency-500,b.max_frequency+500)).value;c=C.c_float(rng.uniform(-10,b.cycles+10)).value;sample=rng.randrange(-100,b.sample_count+100)
    for name,address,x,kind in [('frequency_sample',0x800eafc8,f,'frequency'),('cycle_sample',0x800eb178,c,'cycle'),('cycle_period',0x800eb308,c,'period'),('sample_cycle',0x800eb564,sample,'inverse')]:
     out=C.c_float() if kind in ['period','inverse'] else C.c_int32();assert getattr(lib,'mw_ginsu_'+name)(C.byref(b),x,C.byref(out));expected=ref.call(address,fp=x if kind!='inverse' else None,integer=x if kind=='inverse' else 0,result='float' if kind in ['period','inverse'] else 'int')
     if (bits(expected)!=bits(out.value)) if kind in ['period','inverse'] else (expected!=out.value):raise AssertionError((path.name,name,x,expected,out.value))
     counts[kind]+=1
   for at in [0,31,32,b.sample_count//2,b.sample_count-65]:
    out=(C.c_int16*64)();assert lib.mw_ginsu_samples(C.byref(s),C.byref(b),at,out,64);expected=ref.samples(at,64)
    if list(out)!=list(expected):raise AssertionError((path.name,'decode',at,next((i,a,e) for i,(a,e) in enumerate(zip(out,expected)) if a!=e)))
    counts['decoded_samples']+=64
   # Source transition timings in milliseconds; vary actual targets while
   # preserving the previous source packet state (not isolated fake loops).
   assert lib.mw_ginsu_start(C.byref(s),C.byref(b),b.min_frequency)
   for i in range(args.packets):
    target=b.min_frequency+(b.max_frequency-b.min_frequency)*(.5+.49*math.sin(i*.13));assert lib.mw_ginsu_frequency(C.byref(s),C.byref(b),target,16.666666)
    expected,state=ref.packet(s);out=(C.c_int16*1024)();assert lib.mw_ginsu_packet(C.byref(s),C.byref(b),out,1024),(path.name,i,'native refused')
    if list(out)[:s.packet_size]!=list(expected):raise AssertionError((path.name,i,'pcm',next((j,a,e) for j,(a,e) in enumerate(zip(out,expected)) if a!=e)))
    actual=(s.playback,s.current,s.target,s.countdown,s.no_jump_remaining,s.current_cycle)
    if actual[:5]!=state[:5] or bits(actual[5])!=bits(state[5]):raise AssertionError((path.name,i,'state',actual,state))
    counts['packets']+=1;counts['packet_samples']+=s.packet_size
   counts['banks']+=1;inventory.append(dict(file=path.name,sha256=hashlib.sha256(data).hexdigest(),rate=b.rate,samples=b.sample_count,segments=b.segments,cycles=b.cycles,minimum_frequency=b.min_frequency,maximum_frequency=b.max_frequency,packet=s.packet_size,overlap=s.overlap_size));print(path.name,counts,flush=True)
 report=dict(source_dol_sha256=hashlib.sha256(raw).hexdigest(),counts=counts,mismatches=0,banks=inventory,limits=['Reference packet numeric body stops before platform sound-packet submission; original maps, original XASdecode and all PCMmix instructions execute','Gekko paired-single ABI spills modeled by existing reference hooks; no audio arithmetic substituted','Standalone controlled source frequencies do not establish live vehicleRPM providers or final original gain/mix/pitch attenuation'])
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(counts))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--banks',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--packets',type=int,default=32);a=p.parse_args();verify(a)
