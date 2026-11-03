import ctypes as C,hashlib,json,math,random,struct,sys,time
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools')
from world_collision import packages
from map_recovery_contact_reference import OriginalContactReference
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
class Contact(C.Structure):
 _fields_=[('point',C.c_float*3),('normal',C.c_float*3),('triangle',(C.c_float*3)*3),('height_gap',C.c_float),('distance_squared',C.c_float),('material_key',C.c_uint32),('source_ci_offset',C.c_uint32),('source_asset_offset',C.c_uint32),('section_id',C.c_uint16),('collision_id',C.c_uint16),('asset_index',C.c_uint16),('primitive_index',C.c_uint16),('node_index',C.c_uint16),('instance_flags',C.c_uint16),('material_index',C.c_uint8),('primitive_flags',C.c_uint8),('strip_flags',C.c_uint8),('kind',C.c_uint8)]
class Admission(C.Structure):_fields_=[('bytes',C.c_size_t),('read_bytes',C.c_size_t),('packages',C.c_uint32),('no_collision',C.c_uint32),('retained',C.c_uint32)]
lib=C.CDLL('/tmp/lib-world-collision-runtime-test.so');lib.open_test_world.argtypes=[C.c_char_p,C.c_size_t];lib.open_test_world.restype=C.c_void_p;lib.close_test_world.argtypes=[C.c_void_p]
lib.world_collision_runtime_activate.argtypes=[C.c_void_p,C.POINTER(C.c_uint16),C.c_size_t,C.POINTER(Admission)]
lib.world_collision_runtime_ground.argtypes=[C.c_void_p,C.POINTER(C.c_float),C.c_uint32,C.POINTER(Contact)]
lib.world_collision_runtime_wall.argtypes=[C.c_void_p,C.POINTER(C.c_float),C.POINTER(C.c_float),C.c_uint32,C.POINTER(Contact)]
stream=Path('/workspace/port-research/rockport/samples/STREAML2RA-full.BUN').read_bytes();containment=json.loads(Path('/workspace/port-research/world-streaming/original-render-collision-containment.json').read_text());sections={r['collision_offset']:r['section_id'] for r in containment['relations']}
ref=OriginalContactReference(Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes(),DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin'))
w=lib.open_test_world(b'/workspace/port-research/map-collision/runtime/rockport-collision.nwc',1024*1024);assert w
rng=random.Random(2005);ground_cases=0;wall_cases=0;ground_hits=0;wall_hits=0;errors=[];maxgap=0;maxgnormal=0;maxwnormal=0;maxwpoint=0;largest=0
started=time.perf_counter()
for pack in packages(stream):
 if rng.randrange(8):continue
 section=sections[pack['source_offset']];admission=Admission();assert lib.world_collision_runtime_activate(w,(C.c_uint16*1)(section),1,C.byref(admission))==0;largest=max(largest,admission.bytes)
 mesh_instances=[i for i in pack['instances'] if pack['assets'][i['asset_index']]['parts']]
 wall_instances=[i for i in pack['instances'] if pack['assets'][i['asset_index']]['walls']]
 if mesh_instances:
  seed=rng.choice(mesh_instances);asset=pack['assets'][seed['asset_index']];part=rng.choice(asset['parts']);tri=rng.choice(part['triangles']);corners=[part['vertices'][v] for v in tri['corners']]
  point=[sum(v[a] for v in corners)/3-seed['world_to_local_translation'][a]+(1 if a==1 else 0) for a in range(3)]
  for mask in (0,8,3):
   best=None
   for ci in mesh_instances:
    asset=pack['assets'][ci['asset_index']];src=ref.query_mesh(point,stream[ci['source_offset']:ci['source_offset']+64],stream[asset['source_offset']:asset['source_offset']+asset['source_bytes']],mask)
    if src['hit'] and (best is None or src['height_delta']<best[0]['height_delta']):best=(src,ci,asset)
   out=Contact();got=lib.world_collision_runtime_ground(w,(C.c_float*3)(*point),mask,C.byref(out));ground_cases+=1
   if bool(got)!=bool(best):errors.append(dict(kind='ground_hit',section=section,mask=mask));continue
   if got:
    ground_hits+=1;src,ci,asset=best;raw=bytes.fromhex(src['triangle']);expected=[list(struct.unpack_from('>3f',raw,i*16)) for i in range(3)]
    ve=max(abs(out.triangle[i][a]-expected[i][a]) for i in range(3) for a in range(3));ge=abs(out.height_gap-src['height_delta']);ne=max(abs(out.normal[a]-src['query_normal'][a]) for a in range(3));maxgap=max(maxgap,ge);maxgnormal=max(maxgnormal,ne)
    if ve or out.source_ci_offset!=ci['source_offset'] or out.material_key!=asset['materials'][raw[44]] or out.primitive_flags!=raw[45]:errors.append(dict(kind='ground_geometry_material_source',section=section,ve=ve))
 if wall_instances:
  seed=rng.choice(wall_instances);asset=pack['assets'][seed['asset_index']];wall=rng.choice(asset['walls']);a=wall['endpoint_a'];b=wall['endpoint_b'];t=seed['world_to_local_translation'];mid=[(a[i]+b[i])/2-t[i] for i in range(3)];n=[b[2]-a[2],0,a[0]-b[0]];length=math.hypot(n[0],n[2]);n=[v/length for v in n];start=[mid[i]-n[i] for i in range(3)];end=[mid[i]+n[i] for i in range(3)]
  for mask in (0,64,2):
   best=None
   for ci in wall_instances:
    asset=pack['assets'][ci['asset_index']];rawasset=bytearray(stream[asset['source_offset']:asset['source_offset']+asset['source_bytes']])
    if ci['raw_18']:
     for j in range(len(asset['walls'])):rawasset[16+struct.unpack_from('>H',rawasset,2)[0]+j*32+13]|=0xc0
    src=ref.query_wall_contact(start,end,stream[ci['source_offset']:ci['source_offset']+64],bytes(rawasset),mask)
    if src['hit'] and (best is None or src['distance_squared']<best[0]['distance_squared']):best=(src,ci)
   out=Contact();got=lib.world_collision_runtime_wall(w,(C.c_float*3)(*start),(C.c_float*3)(*end),mask,C.byref(out));wall_cases+=1
   if bool(got)!=bool(best):errors.append(dict(kind='wall_hit',section=section,mask=mask));continue
   if got:
    wall_hits+=1;src,ci=best;pe=max(abs(out.point[a]-src['point'][a]) for a in range(3));ne=max(abs(out.normal[a]-src['normal'][a]) for a in range(3));maxwpoint=max(maxwpoint,pe);maxwnormal=max(maxwnormal,ne)
    if pe or ne or out.material_key!=src['material_token'] or out.source_ci_offset!=ci['source_offset']:errors.append(dict(kind='wall_point_normal_material_source',section=section,pe=pe,ne=ne))
lib.close_test_world(w)
report=dict(source_sha256=hashlib.sha256(stream).hexdigest(),ground_cases=ground_cases,ground_hits=ground_hits,wall_cases=wall_cases,wall_hits=wall_hits,failure_count=len(errors),failures=errors[:20],maximum_ground_gap_error=maxgap,maximum_ground_query_normal_error=maxgnormal,maximum_wall_world_point_error=maxwpoint,maximum_wall_world_normal_error=maxwnormal,largest_single_package_cache_bytes=largest,host_research_seconds=time.perf_counter()-started,limitations='Exact containing section activated, original per-instance results aggregated in source CI order; outer original collision spatial-list tie order and body response are not proven. Ground sqrtf differs from original pinned Gekko estimate model. Includes original load-time wallflags mutation and exact source-alias provenance.')
Path('/workspace/port-research/map-collision/runtime/runtime-original-differential.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
