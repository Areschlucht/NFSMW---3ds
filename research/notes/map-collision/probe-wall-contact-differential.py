import ctypes as C,hashlib,json,math,random,struct,sys
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools')
from world_collision import packages
from map_recovery_ps_reference import f32
from map_recovery_contact_reference import OriginalContactReference
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
class Hit(C.Structure):_fields_=[('point',C.c_float*3),('wall_index',C.c_uint16),('material_index',C.c_uint8),('flags',C.c_uint8)]
lib=C.CDLL('/tmp/lib-world-collision.so');f=lib.world_collision_wall_bank_segment;f.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(C.c_float),C.POINTER(C.c_float),C.c_uint32,C.POINTER(Hit)]
normal_fn=lib.world_collision_wall_contact_normal;normal_fn.argtypes=[C.POINTER(C.c_float)]*4+[C.c_float,C.POINTER(C.c_float)]
stream=Path('/workspace/port-research/rockport/samples/STREAML2RA-full.BUN').read_bytes();ref=OriginalContactReference(Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes(),DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin'));rng=random.Random(2005)
cases=0;hits=0;errors=[];maxpoint=0;maxnormal=0;maxinst=0;flags={}
for pack in packages(stream):
 for inst in pack['instances']:
  asset=pack['assets'][inst['asset_index']]
  if not asset['walls']:continue
  rare=[w for w in asset['walls'] if w['flags']==6]
  if not rare and rng.randrange(7):continue
  wall=rng.choice(rare or asset['walls']);a=wall['endpoint_a'];b=wall['endpoint_b'];t=inst['world_to_local_translation'];mid=[(a[i]+b[i])/2-t[i] for i in range(3)]
  normal=[b[2]-a[2],0,a[0]-b[0]];length=math.hypot(normal[0],normal[2]);normal=[v/length for v in normal]
  raw=stream[asset['source_offset']:asset['source_offset']+asset['source_bytes']];arr=C.create_string_buffer(raw)
  for sign,dy,mask in ((1,0,0),(-1,0,0),(1,0,2),(1,0,16),(1,200,0),(1,-200,0)):
   start=[mid[i]-sign*normal[i]+(dy if i==1 else 0) for i in range(3)];end=[mid[i]+sign*normal[i]+(dy if i==1 else 0) for i in range(3)]
   original=ref.query_wall_contact(start,end,stream[inst['source_offset']:inst['source_offset']+64],raw,mask)
   local_a=[f32(f32(start[i])+t[i]) for i in range(3)];local_b=[f32(f32(end[i])+t[i]) for i in range(3)]
   out=Hit();result=f(arr,len(raw),(C.c_float*3)(*local_a),(C.c_float*3)(*local_b),mask,C.byref(out));cases+=1;maxinst=max(maxinst,original['instructions']);flags[str(wall['flags'])]=flags.get(str(wall['flags']),0)+1
   if bool(result)!=original['hit']:errors.append(dict(kind='hit',id=pack['id'],ci=inst['source_offset'],mask=mask,expected=original['hit'],got=result));continue
   if result:
    hits+=1;selected=asset['walls'][out.wall_index]
    worldpoint=[f32(out.point[i]-t[i]) for i in range(3)]
    worlda=[f32(selected['endpoint_a'][i]-t[i]) for i in range(3)];worldb=[f32(selected['endpoint_b'][i]-t[i]) for i in range(3)]
    n=(C.c_float*3)();status=normal_fn((C.c_float*3)(*start),(C.c_float*3)(*worldpoint),(C.c_float*3)(*worlda),(C.c_float*3)(*worldb),selected['inverse_horizontal_length'],n);assert status==0
    pe=max(abs(worldpoint[i]-original['point'][i]) for i in range(3));ne=max(abs(n[i]-original['normal'][i]) for i in range(3));maxpoint=max(maxpoint,pe);maxnormal=max(maxnormal,ne)
    token=asset['materials'][out.material_index]
    if pe or ne or token!=original['material_token']:errors.append(dict(kind='point_normal_material',id=pack['id'],ci=inst['source_offset'],point_error=pe,normal_error=ne,material_token=hex(token),original_token=hex(original['material_token'])))
report=dict(dol_sha256=ref.dol.sha256,full_wall_contact_address='0x802f3e6c',routine_sha256=hashlib.sha256(ref.dol.read(0x802f3e6c,0x423c-0x3e6c)).hexdigest(),cases=cases,hits=hits,source_wall_flags=flags,failure_count=len(errors),failures=errors[:20],maximum_world_point_error=maxpoint,maximum_world_normal_error=maxnormal,maximum_reference_instructions=maxinst,limitations='Original segment-wall contact output, no rigid-body response/impulses. Source identity CI and on-disc material tokens (original materialfixup consumers traced separately); scene activation/load-time flag mutations remain caller responsibilities.')
Path('/workspace/port-research/map-collision/wall-contact-differential.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
