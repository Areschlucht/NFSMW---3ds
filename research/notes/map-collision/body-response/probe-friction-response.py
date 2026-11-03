import ctypes as C,hashlib,json,math,random,struct,sys
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools')
from vehicle_attributes import VehicleAttributes
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
from world_collision_response_reference import OriginalBodyFrictionReference
from map_recovery_ps_reference import f32
attributes=VehicleAttributes(Path('/workspace/attachments/857a1856-1b3b-4be1-8a91-42f437324e6f/ATTRIBUTES.BIN').read_bytes());surfaces=json.loads(Path('/workspace/port-research/driving-engine/surface-values.json').read_text())['rows']
lib=C.CDLL('/tmp/lib-mw-body-collision.so');fn=lib.mw_body_collision_tangent_response;fn.argtypes=[C.POINTER(C.c_float)]*3+[C.c_float,C.POINTER(C.c_float)]
ref=OriginalBodyFrictionReference(Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes(),DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin'));rng=random.Random(2005)
rows=[];pairs=[]
for name in ('default','cars','racers'):
 row=attributes.find('rigidbodyspecs',name);fields=attributes.fields(row);rows.append(dict(name=name,collection_key=row['key'],fields={k:fields[k] for k in ('WALL_FRICTION','WORLD_MOMENT_SCALE','WALL_ELASTICITY')}))
 values=fields['WALL_FRICTION']['value']['values'];static=values[0];dynamic=min(values)
 for surface in surfaces:
  world=surface['fields']['WORLD_FRICTION']['value'];pairs.append((f32(dynamic*world),f32(static*world)))
cases=[]
for pair in pairs:
 for _ in range(8):
  n=[rng.uniform(-1,1) for _ in range(3)];length=math.sqrt(sum(v*v for v in n));n=[f32(v/length) for v in n];v=[f32(rng.uniform(-100,100)) for _ in range(3)];component=f32(n[2]*v[2]+f32(f32(n[0]*v[0])+f32(n[1]*v[1])));cases.append((pair,v,n,component,'varied'))
 for speed in (0,1,10,50):
  threshold=f32(speed*pair[1]);values=[0,threshold,threshold*2]
  if threshold>0:
   bits=struct.unpack('>I',struct.pack('>f',threshold))[0];values.extend(struct.unpack('>f',struct.pack('>I',bits+d))[0] for d in (-1,1))
  for tangent in values:cases.append((pair,[f32(tangent),f32(-speed),0],[0,1,0],f32(-speed),'threshold'))
SqrtCallback=C.CFUNCTYPE(C.c_float,C.c_float,C.c_void_p)
class Math(C.Structure):_fields_=[('sqrt_raw',SqrtCallback),('context',C.c_void_p)]
sqrt_callback=SqrtCallback(lambda value,context:ref.sqrt_raw(value));model_math=Math(sqrt_callback,None)
exact_fn=lib.mw_body_collision_tangent_response_with_math;exact_fn.argtypes=[C.POINTER(C.c_float)]*3+[C.c_float,C.POINTER(C.c_float),C.POINTER(Math)]
branches={};maxerror=0;errors=[];boundary_modes=[];exact_errors=[];exact_max=0
for pair,v,n,c,kind in cases:
 expected=ref.tangent(pair,v,n,c);out=(C.c_float*3)();branch=fn((C.c_float*2)(*pair),(C.c_float*3)(*v),(C.c_float*3)(*n),c,out);branches[str(branch)]=branches.get(str(branch),0)+1
 error=max(abs(out[i]-expected['correction'][i]) for i in range(3));maxerror=max(maxerror,error)
 exact_out=(C.c_float*3)();exact_branch=exact_fn((C.c_float*2)(*pair),(C.c_float*3)(*v),(C.c_float*3)(*n),c,exact_out,C.byref(model_math));exact_max=max(exact_max,max(abs(exact_out[i]-expected['correction'][i]) for i in range(3)))
 if exact_branch!=expected['branch'] or struct.pack('>3f',*exact_out)!=struct.pack('>3f',*expected['correction']):exact_errors.append(dict(expected=expected,got_branch=exact_branch,got=list(exact_out),coefficients=pair,velocity=v,normal=n,component=c,kind=kind))
 if branch!=expected['branch']:
  record=dict(coefficients=pair,velocity=v,normal=n,component=c,expected=expected['branch'],got=branch,error=error,case_kind=kind)
  if kind=='threshold':boundary_modes.append(record)
  else:errors.append(record)
 elif error>0.0001:errors.append(dict(kind='magnitude',error=error,coefficients=pair,velocity=v,normal=n))
report=dict(dol_sha256=ref.dol.sha256,original_address='0x80083680',routine_sha256=ref.friction_sha256,attribute_sha256=attributes.sha256,source_rows=rows,source_surface_rows=len(surfaces),cases=len(cases),branches=branches,nonboundary_failures=len(errors),failures=errors[:20],threshold_branch_differences=len(boundary_modes),threshold_examples=boundary_modes[:10],maximum_component_error=maxerror,original_math_failures=len(exact_errors),original_math_maximum_error=exact_max,original_math_examples=exact_errors[:10],limitations='Bounded tangent-correction producer only. Portable sqrtf versus pinned Gekko reciprocal-estimate/Newton model; near-threshold branch differences reported explicitly. No body effective-mass/inertia solver, shape selection or integration claim.')
Path('/workspace/port-research/map-collision/body-response/friction-response-differential.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('source_rows','threshold_examples','failures','original_math_examples')}))
