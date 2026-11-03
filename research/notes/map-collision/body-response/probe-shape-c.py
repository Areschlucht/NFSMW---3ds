import ctypes as C,hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools')
from world_collision_response_shapes import body_packages
from world_collision_response_reference import OriginalBodyPrimitiveReference
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
class Compound(C.Structure):_fields_=[('data',C.c_void_p),('bytes',C.c_size_t),('model_key',C.c_uint32),('bound_count',C.c_uint32),('mesh_count',C.c_uint32),('mesh_offsets',C.c_uint32*128)]
class Bound(C.Structure):_fields_=[('quaternion',C.c_float*4),('center',C.c_float*3),('half_extents',C.c_float*3),('radius',C.c_float),('material_key',C.c_uint32),('token',C.c_uint32),('source_flags',C.c_uint16),('first_child',C.c_int16),('mesh_index',C.c_int8),('child_count',C.c_uint8)]
class Shape(C.Structure):_fields_=[('quaternion',C.c_float*4),('center',C.c_float*3),('half_extents',C.c_float*3),('radius',C.c_float),('material_key',C.c_uint32),('token',C.c_uint32),('source_flags',C.c_uint16),('runtime_flags',C.c_uint16),('bound_index',C.c_uint16),('kind',C.c_uint8)]
lib=C.CDLL('/tmp/lib-mw-body-shapes.so');lib.mw_body_collision_compound_open.argtypes=[C.c_void_p,C.c_size_t,C.c_uint32,C.POINTER(Compound)];lib.mw_body_collision_bound.argtypes=[C.POINTER(Compound),C.c_uint,C.POINTER(Bound)];lib.mw_body_collision_primitive.argtypes=[C.POINTER(Bound),C.POINTER(C.c_float),C.POINTER(Shape)];lib.mw_body_collision_static_children.argtypes=[C.POINTER(Compound),C.c_uint,C.POINTER(C.c_float),C.POINTER(Shape),C.c_size_t,C.POINTER(C.c_size_t)]
D=Path('/workspace/port-research/v018-decoded/GLOBAL-GLOBALB_VM_NGC.BUN').read_bytes();ref=OriginalBodyPrimitiveReference(Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes(),DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin'));cases=0;decoded=0;created=0;errors=[];bmw=None
for package in body_packages(D):
 q=package['source_offset'];raw=D[q:q+package['source_bytes']];storage=C.create_string_buffer(raw);compound=Compound();assert lib.mw_body_collision_compound_open(storage,len(raw),package['key'],C.byref(compound))==0
 for source in package['bounds']:
  b=Bound();assert lib.mw_body_collision_bound(C.byref(compound),source['index'],C.byref(b))==0;decoded+=1
  for field in ('quaternion','center','half_extents'):
   if struct.pack('>'+str(len(getattr(b,field)))+'f',*getattr(b,field))!=struct.pack('>'+str(len(source[field]))+'f',*source[field]):errors.append(dict(kind='decode',key=hex(package['key']),index=source['index'],field=field))
  for pad in ((0,0,0),(.01,.02,.03)):
   expected=ref.primitive(source,pad);out=Shape();got=lib.mw_body_collision_primitive(C.byref(b),(C.c_float*3)(*pad),C.byref(out));cases+=1
   if bool(got)!=expected['created']:errors.append(dict(kind='created',key=hex(package['key']),index=source['index']));continue
   if got:
    created+=1;args=expected['arguments']
    if out.kind!=args['kind'] or out.runtime_flags!=args['runtime_flags'] or out.token!=args['token']:errors.append(dict(kind='flags/type',key=hex(package['key']),index=source['index']))
    for field in ('quaternion','center','half_extents'):
     if struct.pack('>'+str(len(getattr(out,field)))+'f',*getattr(out,field))!=struct.pack('>'+str(len(args[field]))+'f',*args[field]):errors.append(dict(kind='producer',key=hex(package['key']),index=source['index'],field=field,actual=list(getattr(out,field)),expected=args[field]))
 if package['key']==0xcae3e635:
  shapes=(Shape*16)();count=C.c_size_t();status=lib.mw_body_collision_static_children(C.byref(compound),0,(C.c_float*3)(0,0,0),shapes,16,C.byref(count));assert status==0
  bmw=[dict(bound_index=s.bound_index,kind=s.kind,runtime_flags=s.runtime_flags,source_flags=s.source_flags,center=list(s.center),half_extents=list(s.half_extents),quaternion=list(s.quaternion),radius=s.radius,material_key=hex(s.material_key)) for s in shapes[:count.value]]
  Path('/workspace/port-research/map-collision/body-response/bmwm3gtre46-collision.bnd').write_bytes(raw)
report=dict(source_sha256=hashlib.sha256(D).hexdigest(),dol_sha256=ref.dol.sha256,decoded_bounds=decoded,primitive_cases=cases,produced=created,float_bit_or_flag_failures=len(errors),examples=errors[:10],bmw_static_children=bmw,limitations='Original primitive arguments verified with allocator/list insertion intercepted. Static children preserve original detailed-child and world-loop flag filtering. No body pose/swept SAT/effective-mass response integration claim.')
Path('/workspace/port-research/map-collision/body-response/shape-c-differential.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('bmw_static_children','examples')}));print('BMW',[(s['bound_index'],s['kind']) for s in bmw])
