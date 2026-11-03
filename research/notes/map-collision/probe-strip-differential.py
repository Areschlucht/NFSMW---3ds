import ctypes as C,json,random,struct,sys
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools')
from world_collision import packages
from map_recovery_strip_reference import OriginalStripReference
class Hit(C.Structure):
 _fields_=[('vertices',(C.c_float*3)*3),('material_index',C.c_uint8),('attributes',C.c_uint8),('triangle_index',C.c_uint16)]
lib=C.CDLL('/tmp/lib-world-collision.so');f=lib.world_collision_strip_candidate
f.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(C.c_float),C.POINTER(C.c_float),C.c_uint32,C.POINTER(Hit)]
ref=OriginalStripReference(Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes())
stream=Path('/workspace/port-research/rockport/samples/STREAML2RA-full.BUN').read_bytes()
rng=random.Random(2005);count=0;hits=0;max_error=0;flags={};fail=[]
for package in packages(stream):
 for asset in package['assets'].values():
  for part in asset['parts']:
   if rng.randrange(24):continue
   strip_at=asset['source_offset']+16+part['strip_offset'];strip=stream[strip_at:strip_at+len(part['vertices'])*8]
   tri=rng.choice(part['triangles']);points=[part['vertices'][i] for i in tri['corners']]
   midpoint=[sum(p[a] for p in points)/3 for a in range(3)]
   for point,mask in [(midpoint,0),([midpoint[0],midpoint[1]-2,midpoint[2]],0),(midpoint,8),(midpoint,3),(midpoint,16)]:
    out=Hit();arr=C.create_string_buffer(strip);center=(C.c_float*3)(*part['center']);p=(C.c_float*3)(*point)
    result=f(arr,len(strip),center,p,mask,C.byref(out));original=ref.query(point,part['center'],strip,mask)
    count+=1;flags[str(part['flags'])]=flags.get(str(part['flags']),0)+1
    if bool(result)!=original['hit']:
     fail.append(dict(package=package['id'],part_offset=strip_at,point=point,mask=mask,native=result,original=original['hit']))
    elif result:
     hits+=1
     error=max(abs(out.vertices[i][a]-original['vertices'][i][a]) for i in range(3) for a in range(3));max_error=max(max_error,error)
     if error or out.material_index!=original['material_index'] or out.attributes!=original['attributes']:fail.append(dict(metadata_or_vertex_mismatch=True,offset=strip_at,error=error))
report=dict(dol_sha256=ref.dol.sha256,routine_sha256=ref.routine_sha256,routine_address=hex(ref.ADDRESS),cases=count,hits=hits,strip_flags=flags,maximum_output_vertex_error=max_error,failures=fail[:20],failure_count=len(fail),limitations='Local candidate primitive only; sample centroid/masks/height differential, not exact boundary/NaN/FPSCR validation or full scene collision query/response.')
Path('/workspace/port-research/map-collision/strip-query-differential.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
