#!/usr/bin/env python3
"""Read-only source collision wall and track-barrier correlation diagnostics."""
import argparse,json,math,struct,hashlib
from pathlib import Path
from collections import Counter

def walls(path):
 raw=path.read_bytes()
 if raw[:4]!=b'NWC1':raise ValueError('NWC1 required')
 total=struct.unpack_from('<I',raw,8)[0]
 for index in range(total):
  pid,offset,size,count,crc,source,sourcebytes,_=struct.unpack_from('<8I',raw,64+index*32)
  data=raw[offset:offset+size]
  for i in range(count):
   at=16+i*96;off,n,source_ci,source_ca=struct.unpack_from('<4I',data,at);ci=data[at+32:at+96];asset=data[off:off+n]
   translation=struct.unpack_from('>3f',ci,48);prop,assetindex=struct.unpack_from('>2H',ci,24)
   mesh,wcount=struct.unpack_from('>2H',asset,2)
   for j in range(wcount):
    w=asset[16+mesh+j*32:16+mesh+(j+1)*32];a=struct.unpack_from('>3f',w);b=struct.unpack_from('>3f',w,16)
    a=[a[k]-translation[k] for k in range(3)];b=[b[k]-translation[k] for k in range(3)]
    yield dict(package=pid,instance=i,wall=j,source_ci=source_ci,source_ca=source_ca,asset_index=assetindex,ci_prop=prop,
     flags=w[13]|(0xc0 if prop else 0),a_native=a,b_native=b,
     material_key=f'{struct.unpack_from(">I",asset,16+mesh+wcount*32+w[12]*4)[0]:08x}')

def barriers(scene):
 m=json.loads((scene/'manifest.json').read_text());models={x['hash']:x['name'] for x in m['models'].values() if x['name'].startswith('XO_TRACKBARRIER')}
 for section in m['sections']:
  data=(scene/section['path']).read_bytes();n,at=struct.unpack_from('<I',data,24)[0],struct.unpack_from('<I',data,36)[0]
  for i in range(n):
   p=at+i*144;keys=struct.unpack_from('<4I',data,p+72+24)
   matches=[models[f'{k:08x}'] for k in keys if f'{k:08x}' in models]
   if not matches:continue
   original=data[p+8:p+72];position=struct.unpack_from('<3f',original,32)
   yield dict(section=section['id'],source_instance=struct.unpack_from('<I',data,p)[0],models=matches,
    source_position=position,native_position=[-position[1],position[2],position[0]],
    source_bounds=list(struct.unpack_from('<6f',original)),flags=f'{struct.unpack_from("<I",original,24)[0]:08x}')

def distance(p,a,b):
 v=[b[0]-a[0],b[2]-a[2]];d=v[0]*v[0]+v[1]*v[1];t=max(0,min(1,((p[0]-a[0])*v[0]+(p[2]-a[2])*v[1])/d)) if d else 0
 return math.hypot(p[0]-a[0]-t*v[0],p[2]-a[2]-t*v[1])


class OriginalGroupGate:
 def __init__(self,raw):
  from vehicle_dol import DolImage
  from vehicle_ppc_reference import DOL_SHA256
  from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
  from unicorn import ppc_const as r
  if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected USA DOL')
  self.image=DolImage(raw);self.r=r;self.u=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
  self.u.mem_map(0x80000000,0x1800000)
  for section in self.image.sections:self.u.mem_write(section.address,raw[section.offset:section.offset+section.size])
  self.begin=0;self.end=0;self.skip=0;self.result=None
  def code(u,pc,size,user):
   if pc==self.end:self.result=True;u.emu_stop()
   elif pc==self.skip:self.result=False;u.emu_stop()
   elif not self.begin<=pc<self.end:raise ValueError('Collision group gate escaped original window')
  def write(u,access,address,size,value,user):raise ValueError('Unexpected original group gate write')
  self.u.hook_add(UC_HOOK_CODE,code);self.u.hook_add(UC_HOOK_MEM_WRITE,write)
 def enabled(self,group,state,second=False):
  if not 0<=group<=65535 or not 0<=state<=255:raise ValueError('Invalid synthetic group/state')
  self.begin,self.end,self.skip=(0x802f2700,0x802f2718,0x802f25cc) if second else (0x802f2000,0x802f2018,0x802f1ecc)
  r=self.r;u=self.u;self.result=None
  u.reg_write(r.UC_PPC_REG_11,0x81600000)
  u.reg_write(r.UC_PPC_REG_15 if second else r.UC_PPC_REG_19,0x8043604c)
  u.mem_write(0x81600018,struct.pack('>H',group));u.mem_write(0x8043604c+group,bytes([state]))
  u.emu_start(self.begin,0x817ffffc,count=16,timeout=100000)
  if self.result is None:raise ValueError('Original group gate execution budget exhausted')
  return self.result

def verify_original_gate(dol):
 ref=OriginalGroupGate(dol);count=0
 for second in (False,True):
  for group in (0,1,3,71,146,500,753,754,1023):
   for state in range(256):
    if ref.enabled(group,state,second)!=(group==0 or state!=0):raise AssertionError('Original group gate differs')
    count+=1
 return {'original_group_gate_cases':count,'group_state_table':'8043604c',
  'query_windows':[{'start':f'{a:08x}','end_exclusive':f'{b:08x}','sha256':hashlib.sha256(ref.image.read(a,b-a)).hexdigest()} for a,b in ((0x802f2000,0x802f2018),(0x802f2700,0x802f2718))],
  'exact_rule':'Collision CI admitted iff CI.group_id==0 or original_group_state[CI.group_id]!=0',
  'group_field_offset':24,'limits':['Bounded original scalar gates; geometry/actor query outside windows not executed','Synthetic state-byte inputs, not a recovered complete career state machine']}

NATIVE_PROBE_SOURCE = r'''#include "world_collision_runtime.h"
#include "world_streaming.h"
#include "streamed_drive.h"
#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
static WorldCollisionRuntime world;
static unsigned char arena[2*1024*1024];
static void *load(const char *path,size_t *n){FILE*f=fopen(path,"rb");assert(f);fseek(f,0,SEEK_END);long k=ftell(f);rewind(f);void *p=malloc(k);assert(fread(p,1,k,f)==(size_t)k);fclose(f);*n=k;return p;}
int main(int argc,char**argv){assert(argc==4);size_t n;void*p=load(argv[1],&n);RoadWorld road;assert(road_decode(p,n,&road));free(p);p=load(argv[2],&n);WorldStreamingDatabase db;assert(!world_streaming_open(p,n,&db));WorldStreamingSelector sel;world_streaming_selector_init(&db,&sel);assert(!world_collision_runtime_open(&world,argv[3],arena,sizeof(arena)));DriveState car;drive_reset(&car,road.spawn[0],road.spawn[2],road.heading);float y=road.spawn[1];StreamedDriveSurface surface={&world,&road};
 for(unsigned frame=0;frame<1200;frame++){
  uint16_t dep,ids[147];size_t count;assert(!world_streaming_select(&db,&sel,car.x+road.origin[0],-(car.z+road.origin[2]),&dep));assert(!world_streaming_plan(&db,&dep,1,ids,147,&count));assert(!world_collision_runtime_activate(&world,ids,count,NULL));
  for(unsigned step=0;step<2;step++){
   DriveState next=car;assert(drive_step(&next,(DriveInput){.throttle=1,.steering=0},1.f/120));
   float a[3]={car.x,y+.65f,car.z},b[3]={next.x,y+.65f,next.z},na[3],nb[3];world_collision_viewer_to_native(a,road.origin,na);world_collision_viewer_to_native(b,road.origin,nb);WorldCollisionContact hit;int status=world_collision_runtime_wall(&world,na,nb,0,&hit);assert(status>=0);
   if(status){printf("{\"frame\":%u,\"start\":[%.9g,%.9g,%.9g],\"end\":[%.9g,%.9g,%.9g],\"hit\":[%.9g,%.9g,%.9g],\"section\":%u,\"package\":%u,\"source_ci\":%u,\"source_ca\":%u,\"asset\":%u,\"wall\":%u,\"flags\":%u,\"instance_flags\":%u,\"material\":\"%08x\"}\n",frame,na[0],na[1],na[2],nb[0],nb[1],nb[2],hit.point_native[0],hit.point_native[1],hit.point_native[2],hit.section_id,hit.collision_id,hit.source_ci_offset,hit.source_asset_offset,hit.asset_index,hit.primitive_index,hit.primitive_flags,hit.instance_flags,hit.material_key);return 0;}
   float next_y;if(!streamed_drive_surface(&surface,next.x,next.z,y,&next_y,NULL)){printf("groundmiss frame%u pos%.9g,%.9g,%.9g\n",frame,nb[0],nb[1],nb[2]);return 0;}car=next;y=next_y;
  }
 }
}
'''

def trace_forward(road,metadata,collision):
 import subprocess,tempfile
 project=Path(__file__).resolve().parents[1]
 with tempfile.TemporaryDirectory(prefix='mw-collision-forward-') as temporary:
  source=Path(temporary)/'probe.c';source.write_text(NATIVE_PROBE_SOURCE);binary=Path(temporary)/'probe'
  files=['world_collision_runtime.c','world_collision_query.c','world_streaming.c','mw_gekko_math.c','streamed_drive.c','driving_controller.c','road_contact.c']
  subprocess.run(['cc','-O2','-std=c11','-I'+str(project/'include'),str(source),*[str(project/'source_bmw'/f) for f in files],'-lm','-o',str(binary)],check=True)
  result=subprocess.run([str(binary),str(road),str(metadata),str(collision)],check=True,text=True,capture_output=True)
  return json.loads(result.stdout) if result.stdout.startswith('{') else {'status':'no wall JSON','output':result.stdout}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--trace-forward',action='store_true');p.add_argument('--metadata',type=Path);p.add_argument('--dol',type=Path);p.add_argument('--verify-original',action='store_true')
 for field in ('collision','scene','road','output'):p.add_argument('--'+field,type=Path,required=True)
 a=p.parse_args();road=a.road.read_bytes();v=struct.unpack_from('<9f',road,16);origin=v[2:5];spawn=v[5:8];viewer=[origin[i]+spawn[i] for i in range(3)];native=[viewer[2],viewer[1],viewer[0]]
 ws=list(walls(a.collision));bs=list(barriers(a.scene));near=[]
 for w in ws:
  d=distance(native,w['a_native'],w['b_native'])
  if d<180 and min(w['a_native'][1],w['b_native'][1])<native[1]+1<max(w['a_native'][1],w['b_native'][1]):near.append(dict(w,distance_from_spawn=d))
 near.sort(key=lambda w:w['distance_from_spawn'])
 bn=[dict(b,distance_from_spawn=math.hypot(b['native_position'][0]-native[0],b['native_position'][2]-native[2])) for b in bs]
 bn.sort(key=lambda b:b['distance_from_spawn'])
 report={'spawn_native':native,'spawn_viewer':viewer,'heading':v[-1],'walls_total':len(ws),'wall_flag_counts':dict(Counter(w['flags'] for w in ws)),
  'nearby_walls':near,'nearest_barriers':bn[:60],
  'limits':['Distance correlation is diagnostic, not a source ownership proof','No collision exclusions or game inputs changed']}
 if a.trace_forward:
  report['forward_probe']=trace_forward(a.road,a.metadata or a.road.parent/'world-streaming.bin',a.collision)
 if a.verify_original:
  if not a.dol:raise ValueError('--dol is required for original gate verification')
  report['original_group_gate']=verify_original_gate(a.dol.read_bytes())
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'spawn':native,'walls_total':len(ws),'wall_flags':report['wall_flag_counts'],'forward_probe':report.get('forward_probe'),'original_group_gate':report.get('original_group_gate'),'near_walls':len(near),'nearest_walls':near[:5],'nearest_barriers':bn[:5]},indent=2))
