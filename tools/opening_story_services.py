#!/usr/bin/env python3
"""Verify original opening phone selectors and engine sabotage scheduling.
Runs unchanged PPC windows. No speech filename or playback duration is inferred.
"""
import argparse,ctypes,hashlib,json,struct,subprocess,tempfile
from pathlib import Path
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
from mw_debug_info import DebugInfo

def recover_phone(a,u,r):
 from audit_whole_game import directory_records,name_hash,ZDIR_SHA
 from vehicle_attributes import VehicleAttributes
 from vehicle_vlt_hash import vlt_hash
 from vehicle_dol import DolImage
 import wave
 zraw=a.zdir.read_bytes()
 if hashlib.sha256(zraw).hexdigest()!=ZDIR_SHA:raise ValueError('pinned ZDIR differs')
 rows={int(x['hash'],16):x for x in directory_records(zraw)}
 araw=a.attributes.read_bytes()
 if hashlib.sha256(araw).hexdigest()!='5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c':raise ValueError('pinned ATTRIBUTES differs')
 schema=VehicleAttributes(araw)
 collection=schema.find('audiosystem',0xdcf256e2)
 fields={f['field_key']:f for f in schema.fields(collection).values()}
 selected={}; source={}
 for suffix,key in [('evt',0x292001fb),('idx',0x9e8fd078),('csi',0xfb1533a6),('big',0xa2f24773)]:
  field=fields[key];name=field['value']['text'];rec=rows[name_hash(name)]
  if not name.lower().endswith('copspeech_en.'+suffix):raise ValueError('English speech path differs')
  archive=a.archives/('ZZDATA%d.BIN'%rec['archive'])
  with archive.open('rb') as f:f.seek(rec['offset_bytes']);data=f.read(rec['bytes'])
  if len(data)!=rec['bytes']:raise ValueError('truncated speech source')
  selected[suffix]=data;source[suffix]=dict(name=name,record=rec,sha256=hashlib.sha256(data).hexdigest(),field=field)
 evt=selected['evt'];idx=selected['idx'];u.mem_map(0x61000000,0x100000);u.mem_write(0x61000000,evt);u.reg_write(r.UC_PPC_REG_3,0x61000000);u.reg_write(r.UC_PPC_REG_4,204);u.reg_write(r.UC_PPC_REG_LR,0x70000000)
 u.emu_start(0x8037d9a4,0x70000000,count=2000);event=u.reg_read(r.UC_PPC_REG_3)-0x61000000
 if event<0 or evt[event+6]!=1:raise ValueError('expected original single-sentence CellCall event')
 sentence=event+4*struct.unpack_from('>H',evt,event+12)[0]
 if evt[sentence+2]>>2!=1:raise ValueError('expected original single-phrase CellCall sentence')
 phrase=sentence+4*evt[sentence+8];bank_id=struct.unpack_from('>H',evt,phrase)[0]
 if evt[phrase+3]!=0:raise ValueError('expected direct original speech bank')
 count=struct.unpack_from('>I',idx,84)[0];banks=[]
 for i in range(count):
  key,size,offset,audio=struct.unpack_from('>4I',idx,88+i*16)
  if offset+size>len(idx):raise ValueError('bank header range')
  if struct.unpack_from('>H',idx,offset)[0]==bank_id:banks.append((i,key,size,offset,audio))
 if len(banks)!=1:raise ValueError('ambiguous phone bank')
 i,key,size,bankoff,audio=banks[0];bank=idx[bankoff:bankoff+size];num=bank[5];stride=(bank[4]&0x7f)+2
 u.mem_write(0x60002000,struct.pack('>III',204,0x10000,1));u.mem_write(0x60003000,bank)
 matches=[]
 for sample in range(num):
  u.reg_write(r.UC_PPC_REG_1,0x70008000);u.reg_write(r.UC_PPC_REG_3,0x61000000+sentence);u.reg_write(r.UC_PPC_REG_4,0x61000000+phrase);u.reg_write(r.UC_PPC_REG_5,0x60002000);u.reg_write(r.UC_PPC_REG_6,0x60003000+14+sample*stride);u.reg_write(r.UC_PPC_REG_LR,0x70000000)
  u.emu_start(0x8037ebb0,0x70000000,count=1000)
  if u.reg_read(r.UC_PPC_REG_3):matches.append(sample)
 if len(matches)!=1:raise ValueError('CellCall10 does not resolve to unique original sample')
 sample=matches[0];u.reg_write(r.UC_PPC_REG_3,0x60003000);u.reg_write(r.UC_PPC_REG_4,sample);u.reg_write(r.UC_PPC_REG_5,0x60004000);u.reg_write(r.UC_PPC_REG_6,0x60004004);u.reg_write(r.UC_PPC_REG_LR,0x70000000)
 u.emu_start(0x80381420,0x70000000,count=1000)
 if u.reg_read(r.UC_PPC_REG_3)!=1:raise ValueError('original sample bounds rejected')
 offset,n=struct.unpack('>II',bytes(u.mem_read(0x60004000,8)));offset+=audio;clip=selected['big'][offset:offset+n]
 if len(clip)!=n or clip[:4]!=b'SCHl':raise ValueError('source speech sample range')
 out=a.output.parent;clipfile=out/'cellcall10.asf';clipfile.write_bytes(clip)
 result=dict(source=source,event_id=204,event_offset=event,sentence_offset=sentence,phrase_offset=phrase,bank_id=bank_id,bank_entry=i,bank_key=key,sample=sample,original_filter_cases=num,stream_offset=offset,stream_bytes=n,stream_sha256=hashlib.sha256(clip).hexdigest())
 if a.decoder:
  wav=out/'cellcall10.wav';subprocess.run([str(a.decoder),'-o',str(wav),str(clipfile)],check=True,capture_output=True)
  with wave.open(str(wav),'rb') as w:
   if w.getnchannels()!=1 or w.getsampwidth()!=2:raise ValueError('unexpected native phone PCM format')
   result['pcm']=dict(rate=w.getframerate(),channels=1,samples=w.getnframes(),duration=w.getnframes()/w.getframerate());pcm=w.readframes(w.getnframes())
  (out/'cellcall10.pcm').write_bytes(pcm);result['pcm']['sha256']=hashlib.sha256(pcm).hexdigest();result['pcm']['bytes']=len(pcm)
 return result

def run(a):
 raw=a.dol.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=DOL_SHA256: raise ValueError('pinned USA DOL differs')
 im=DolImage(raw)
 from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE
 from unicorn import ppc_const as r
 u=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN);u.mem_map(0x80000000,0x1800000);u.mem_map(0x60000000,0x10000);u.mem_map(0x70000000,0x10000)
 for s in im.sections:u.mem_write(s.address,raw[s.offset:s.offset+s.size])
 u.reg_write(r.UC_PPC_REG_MSR,0x2000)
 root=Path(__file__).resolve().parents[1]
 with tempfile.TemporaryDirectory() as td:
  so=Path(td)/'services.so';subprocess.run(['cc','-shared','-fPIC','-std=c99','-I'+str(root/'include'),str(root/'source_bmw/mw_story_services.c'),'-lm','-o',str(so)],check=True)
  lib=ctypes.CDLL(str(so));lib.mw_story_cell_selector.argtypes=[ctypes.c_int,ctypes.POINTER(ctypes.c_uint32),ctypes.POINTER(ctypes.c_uint32)]
  selectors=[]
  for sms in range(-2,110):
   u.mem_write(0x60000000,bytes.fromhex('123456789abcdef0'));u.reg_write(r.UC_PPC_REG_3,sms&0xffffffff);u.reg_write(r.UC_PPC_REG_4,0x60000000);u.reg_write(r.UC_PPC_REG_LR,0x70000000)
   u.emu_start(0x802ad828,0x70000000,count=256)
   b=ctypes.c_uint32(0x12345678);n=ctypes.c_uint32(0x9abcdef0);ok=lib.mw_story_cell_selector(sms,ctypes.byref(b),ctypes.byref(n))
   assert ok==u.reg_read(r.UC_PPC_REG_3)
   assert struct.pack('>II',b.value,n.value)==bytes(u.mem_read(0x60000000,8))
   selectors.append(sms)
  class Engine(ctypes.Structure):_fields_=[('deadline',ctypes.c_float),('blown',ctypes.c_uint8)]
  lib.mw_story_engine_sabotage.argtypes=[ctypes.POINTER(Engine),ctypes.c_float,ctypes.c_float]
  lib.mw_story_engine_tick.argtypes=[ctypes.POINTER(Engine),ctypes.c_float]
  cases=[]
  for clock,delay,deadline,blown in [(0,5,0,0),(20,5,0,0),(20,5,25,0),(20,0,0,0),(20,1e-6,0,0),(20,5,0,1),(20,0.125,0,0)]:
   addr=0x60000000;u.mem_write(addr,bytes(1024));u.mem_write(addr+0x80,struct.pack('>I',0x803fe0a0));u.mem_write(addr+0x1a8,struct.pack('>If',blown,deadline));u.mem_write(0x8049896c,struct.pack('>f',clock))
   u.reg_write(r.UC_PPC_REG_31,addr);u.reg_write(r.UC_PPC_REG_1,0x70008000);u.reg_write(r.UC_PPC_REG_FPR31,struct.unpack('>Q',struct.pack('>d',ctypes.c_float(delay).value))[0]);u.reg_write(r.UC_PPC_REG_FPR13,0)
   u.emu_start(0x802552f8,0x80255348,count=256)
   e=Engine(deadline,blown);lib.mw_story_engine_sabotage(ctypes.byref(e),clock,delay)
   assert struct.pack('>f',e.deadline)==bytes(u.mem_read(addr+0x1ac,4)), (clock,delay,deadline,blown,e.deadline,bytes(u.mem_read(addr+0x1ac,4)).hex());cases.append([clock,delay,deadline,blown,e.deadline])
  # Execute original tick deadline branch, hooking only actual virtual Blow call.
  emitted=[]
  def hook(cpu,address,size,data):
   if address==0x80255360:
    emitted.append(1);cpu.emu_stop()
  h=u.hook_add(UC_HOOK_CODE,hook)
  for clock in (24.,24.999,25.,25.001,100.):
   u.mem_write(0x600001ac,struct.pack('>f',25.));u.mem_write(0x8049896c,struct.pack('>f',clock));u.reg_write(r.UC_PPC_REG_31,0x60000000);u.reg_write(r.UC_PPC_REG_1,0x70008000)
   emitted.clear();u.emu_start(0x802580f8,0x80258148,count=256)
   e=Engine(25.,0);actual=lib.mw_story_engine_tick(ctypes.byref(e),clock);assert actual==bool(emitted)
  u.hook_del(h)
 with DebugInfo(a.elf) as db:
  selected={}
  for name in ['CellCallStruct','EngineRacer']:
   e=db.find(name,tags={2,19})[0];selected[name]=dict(die_offset=e.offset,size=e.size,members=[dict(name=m['name'],offset=m['offset']) for m in db.members(e) if name=='CellCallStruct' or m['offset'] in (424,428)])
  # Cross-check the debug ELF initialized sections against this exact DOL.
  sections=0
  for name in ('.init','.text','.over','.ctors','.dtors','.rodata','.data','.sdata','.sdata2'):
   h=db.sections[name];assert db.data[h['offset']:h['offset']+h['size']]==im.read(h['address'],h['size']);sections+=1
 report=dict(schema=1,dol_sha256=DOL_SHA256,elf_sha256=hashlib.sha256(a.elf.read_bytes()).hexdigest(),identical_initialized_sections=sections,selector_cases=len(selectors),schedule_cases=cases,tick_cases=5,selected_types=selected,
  source_windows=[dict(address=hex(x),size=y,sha256=hashlib.sha256(im.read(x,y)).hexdigest()) for x,y in [(0x802ad828,444),(0x802552d4,240),(0x802580f8,132)]],
  limits=['Original selector identity is not an identified speech audio clip','Original engine scheduling/blown transition covered; RPM ripple and complete damage response separate'])
 a.output.parent.mkdir(parents=True,exist_ok=True)
 if a.archives:
  if not a.zdir or not a.attributes:raise ValueError('audio recovery requires zdir and attributes')
  report['phone_audio']=recover_phone(a,u,r)
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['dol','elf','output']:p.add_argument('--'+n,type=Path,required=True)
 for n in ['archives','zdir','attributes','decoder']:p.add_argument('--'+n,type=Path)
 run(p.parse_args())
