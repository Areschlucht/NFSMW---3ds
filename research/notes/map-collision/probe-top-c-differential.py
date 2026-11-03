import ctypes as C,importlib.util,json,math,random,struct,sys
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools')
from world_collision import packages
from map_recovery_contact_reference import OriginalContactReference
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
from map_recovery_ps_reference import f32
spec=importlib.util.spec_from_file_location('top','/workspace/port-research/map-collision/probe-top-query.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Hit(C.Structure):_fields_=[('vertices',(C.c_float*3)*3),('material_index',C.c_uint8),('attributes',C.c_uint8),('triangle_index',C.c_uint16)]
lib=C.CDLL('/tmp/lib-world-collision.so');f=lib.world_collision_strip_candidate;f.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(C.c_float),C.POINTER(C.c_float),C.c_uint32,C.POINTER(Hit)]
stream=Path('/workspace/port-research/rockport/samples/STREAML2RA-full.BUN').read_bytes();ref=OriginalContactReference(Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes(),DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin'))
class MeshHit(C.Structure):_fields_=[('triangle',Hit),('height_gap',C.c_float),('node_index',C.c_uint16)]
mesh_query=lib.world_collision_mesh_point_below
mesh_query.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(C.c_float),C.POINTER(C.c_float),C.c_uint32,C.POINTER(MeshHit)]
def reconstructed(point,inst,asset,mask):
 point=[f32(f32(point[a])+inst['world_to_local_translation'][a]) for a in range(3)]
 raw=stream[asset['source_offset']:asset['source_offset']+asset['source_bytes']]
 out=MeshHit();result=mesh_query(C.create_string_buffer(raw),len(raw),(C.c_float*3)(*point),(C.c_float*3)(*inst['extents']),mask,C.byref(out))
 if result<0:raise ValueError('portable C rejected original asset')
 if not result:return None
 return dict(vertices=[[f32(p[a]-inst['world_to_local_translation'][a]) for a in range(3)] for p in out.triangle.vertices],material_index=out.triangle.material_index,attributes=out.triangle.attributes,gap=out.height_gap)

rng=random.Random(2005);cases=0;hits=0;errors=[];maxgap=0;maxvertex=0;maxinst=0
for pack in packages(stream):
 for inst in pack['instances']:
  asset=pack['assets'][inst['asset_index']]
  if not asset['parts'] or rng.randrange(15):continue
  part=rng.choice(asset['parts']);tri=rng.choice(part['triangles']);v=[part['vertices'][i] for i in tri['corners']]
  for dy,mask in ((1,0),(-1,0),(1,8),(1,3)):
   point=[sum(p[a] for p in v)/3-inst['world_to_local_translation'][a]+(dy if a==1 else 0) for a in range(3)]
   src=ref.query_mesh(point,stream[inst['source_offset']:inst['source_offset']+64],stream[asset['source_offset']:asset['source_offset']+asset['source_bytes']],mask)
   got=reconstructed(point,inst,asset,mask);cases+=1;maxinst=max(maxinst,src['instructions'])
   if bool(got)!=src['hit']:errors.append(dict(kind='hit',id=pack['id'],ci=inst['source_offset'],point=point,mask=mask,expected=src['hit'],got=bool(got)));continue
   if got:
    hits+=1;raw=bytes.fromhex(src['triangle']);expected=[list(struct.unpack_from('>3f',raw,i*16)) for i in range(3)]
    ve=max(abs(got['vertices'][i][a]-expected[i][a]) for i in range(3) for a in range(3));ge=abs(got['gap']-src['height_delta']);maxgap=max(maxgap,ge);maxvertex=max(maxvertex,ve)
    if ve or got['material_index']!=raw[44] or got['attributes']!=raw[45]:errors.append(dict(kind='triangle',id=pack['id'],ci=inst['source_offset'],ve=ve,ge=ge))
report=dict(cases=cases,hits=hits,failure_count=len(errors),failures=errors[:20],maximum_gap_error=maxgap,maximum_triangle_vertex_error=maxvertex,maximum_reference_instructions=maxinst,limitations='Original frsqrte is hooked to checksum-pinned Dolphin Gekko estimate model at commit86d554802d7560acf12b5c5a2b3acb344069b5ce; reconstruction uses ordinary sqrt. Paired-single interpreter uses binary64 intermediate then binary32, not exact Gekko FMA ties. Emulator reference, not console trace. No collision response or original wheel-contact consumer linkage.')
Path('/workspace/port-research/map-collision/top-query-c-differential.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
