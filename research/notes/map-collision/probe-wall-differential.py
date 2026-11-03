import ctypes as C,hashlib,importlib.util,json,math,random,struct,sys
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools')
from world_collision import packages
from map_recovery_contact_reference import OriginalContactReference
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
from map_recovery_ps_reference import f32
spec=importlib.util.spec_from_file_location('wall','/workspace/port-research/map-collision/probe-wall-query.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Hit(C.Structure):_fields_=[('point',C.c_float*3),('wall_index',C.c_uint16),('material_index',C.c_uint8),('flags',C.c_uint8)]
lib=C.CDLL('/tmp/lib-world-collision.so');f=lib.world_collision_wall_bank_segment;f.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(C.c_float),C.POINTER(C.c_float),C.c_uint32,C.POINTER(Hit)]
stream=Path('/workspace/port-research/rockport/samples/STREAML2RA-full.BUN').read_bytes();ref=OriginalContactReference(Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes(),DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin'));rng=random.Random(2005)
cases=0;hits=0;errors=[];maxpoint=0;maxinst=0;flags={}
for pack in packages(stream):
 for inst in pack['instances']:
  asset=pack['assets'][inst['asset_index']]
  if not asset['walls']:continue
  rare=[w for w in asset['walls'] if w['flags']==6]
  if not rare and rng.randrange(7):continue
  wall=rng.choice(rare or asset['walls']);a=wall['endpoint_a'];b=wall['endpoint_b'];t=inst['world_to_local_translation'];mid=[(a[i]+b[i])/2-t[i] for i in range(3)]
  normal=[b[2]-a[2],0,a[0]-b[0]];length=math.hypot(normal[0],normal[2]);normal=[v/length for v in normal]
  raw=stream[asset['source_offset']:asset['source_offset']+asset['source_bytes']];arr=C.create_string_buffer(raw)
  for dy,mask in ((0,0),(0,2),(0,16),(200,0),(-200,0)):
   start=[mid[i]-normal[i]+(dy if i==1 else 0) for i in range(3)];end=[mid[i]+normal[i]+(dy if i==1 else 0) for i in range(3)]
   original=ref.query_wall_bank(start,end,stream[inst['source_offset']:inst['source_offset']+64],raw,mask)
   local_a=[f32(f32(start[i])+t[i]) for i in range(3)];local_b=[f32(f32(end[i])+t[i]) for i in range(3)]
   out=Hit();result=f(arr,len(raw),(C.c_float*3)(*local_a),(C.c_float*3)(*local_b),mask,C.byref(out));cases+=1;maxinst=max(maxinst,original['instructions']);flags[str(wall['flags'])]=flags.get(str(wall['flags']),0)+1
   if bool(result)!=original['hit']:errors.append(dict(kind='hit',id=pack['id'],ci=inst['source_offset'],mask=mask,expected=original['hit'],got=result));continue
   if result:
    hits+=1;offset=16+struct.unpack_from('>H',raw,2)[0]+out.wall_index*32
    pe=max(abs(out.point[i]-original['point'][i]) for i in range(3));maxpoint=max(maxpoint,pe)
    if offset!=original['asset_relative_wall_offset'] or pe or out.material_index!=raw[offset+12] or out.flags!=raw[offset+13]:errors.append(dict(kind='selected_wall_or_point',id=pack['id'],ci=inst['source_offset'],point_error=pe,offset=offset,original_offset=original['asset_relative_wall_offset']))
report=dict(dol_sha256=ref.dol.sha256,wall_selection_address='0x802f3e6c',stop_before_response_address='0x802f4000',selection_sha256=hashlib.sha256(ref.dol.read(0x802f3e6c,0x4000-0x3e6c)).hexdigest(),intersection_address='0x803078e4',intersection_sha256=hashlib.sha256(ref.dol.read(0x803078e4,0x11c)).hexdigest(),cases=cases,hits=hits,source_wall_flags=flags,failure_count=len(errors),failures=errors[:20],maximum_point_error=maxpoint,maximum_reference_instructions=maxinst,limitations='Original wall-bank selection only, stopped before contact/response output assembly. Source identity transforms; runtime activation/load-time wallflag mutation and body response are not implemented.')
Path('/workspace/port-research/map-collision/wall-query-differential.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
