import ctypes as C,hashlib,json,random,struct,sys
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools')
from world_collision import packages
from map_recovery_ps_reference import f32
from world_collision_response_reference import OriginalGroundPlaneReference
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
stream=Path('/workspace/port-research/rockport/samples/STREAML2RA-full.BUN').read_bytes();ref=OriginalGroundPlaneReference(Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes(),DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin'))
lib=C.CDLL('/tmp/lib-world-collision.so');fn=lib.world_collision_ground_contact_plane;fn.argtypes=[C.POINTER(C.c_float),C.POINTER(C.c_float),C.POINTER(C.c_float)]
rng=random.Random(2005);cases=0;errors=[];maxnormal=0;maxscalar=0
for pack in packages(stream):
 for ci in pack['instances']:
  asset=pack['assets'][ci['asset_index']]
  for part in asset['parts']:
   if rng.randrange(24):continue
   triangle=rng.choice(part['triangles']);world=[[f32(part['vertices'][v][a]-ci['world_to_local_translation'][a]) for a in range(3)] for v in triangle['corners']]
   query=[f32(sum(v[a] for v in world)/3+(1 if a==1 else 0)) for a in range(3)];expected=ref.ground_plane(world,query)
   out=(C.c_float*4)();assert fn((C.c_float*9)(*(x for p in world for x in p)),(C.c_float*3)(*query),out)==0;cases+=1
   maxnormal=max(maxnormal,max(abs(out[a]-expected[a]) for a in range(3)));maxscalar=max(maxscalar,abs(out[3]-expected[3]))
   if struct.pack('>4f',*out)!=struct.pack('>4f',*expected):errors.append(dict(id=pack['id'],ci=ci['source_offset'],expected=expected,actual=list(out),world=world,query=query))
report=dict(dol_sha256=ref.dol.sha256,source_sha256=hashlib.sha256(stream).hexdigest(),original_slice_start='0x80308c18',original_slice_end='0x80308d8c',slice_sha256=hashlib.sha256(ref.dol.read(0x80308c18,0x174)).hexdigest(),cases=cases,float_bit_mismatches=len(errors),examples=errors[:10],maximum_normal_error=maxnormal,maximum_relative_plane_scalar_error=maxscalar,limitations='Actual world-triangle plane output producer only, using independentGekko newton2. Query cache/selector and physicalwheel point/upstream producer are separate; no suspension/response integration claim.')
Path('/workspace/port-research/map-collision/body-response/ground-plane-differential.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='examples'}))
