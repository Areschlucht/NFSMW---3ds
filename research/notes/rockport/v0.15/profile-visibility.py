import ctypes as C,struct,json,math,statistics
from pathlib import Path
F3=C.c_float*3
class Bounds(C.Structure):_fields_=[('center',F3),('extent',F3)]
class Frustum(C.Structure):_fields_=[('plane',(C.c_float*4)*6)]
class Car(C.Structure):_fields_=[(n,C.c_float) for n in ['x','z','heading','speed','steering','lateral_speed','yaw_rate']]
class Camera(C.Structure):_fields_=[('eye',F3),('target',F3),('velocity',F3),('target_velocity',F3),('heading',C.c_float),('fov',C.c_float),('initialized',C.c_bool)]
lib=C.CDLL('/tmp/nfsmw-visibility-camera.so');lib.world_frustum.argtypes=[C.POINTER(Frustum),F3,F3,C.c_float,C.c_float,C.c_float,C.c_float];lib.world_frustum.restype=C.c_bool;lib.world_visible.argtypes=[C.POINTER(Frustum),C.POINTER(Bounds)];lib.world_visible.restype=C.c_bool;lib.chase_reset.argtypes=[C.POINTER(Camera),C.POINTER(Car),C.c_float];lib.chase_reset.restype=C.c_bool
scene=Path('/workspace/port-research/rockport/scene-v0.15');data=(scene/'world.nfm').read_bytes();nv,nb,nt=struct.unpack_from('<3I',data,8);start=32+nt*16+nb*16;vertices=list(struct.iter_unpack('<12f',data[start:]));batches=list(struct.iter_unpack('<4I',data[32+nt*16:start]));bounds=[]
for first,count,tex,_ in batches:
 points=vertices[first:first+count];lo=[min(p[a] for p in points) for a in range(3)];hi=[max(p[a] for p in points) for a in range(3)];bounds.append(Bounds(F3(*[(a+b)/2 for a,b in zip(lo,hi)]),F3(*[(b-a)/2 for a,b in zip(lo,hi)])))
road=(scene/'road.nrd').read_bytes();scale=struct.unpack_from('<f',road,16)[0];spawn=struct.unpack_from('<4f',road,36);records=[]
for label,path in [('start',scene/'road.nrd'),('northwest',Path('/workspace/port-research/rockport/v0.14/inspection-northwest-road.nrd'))]:
 s=struct.unpack_from('<4f',path.read_bytes(),36)
 for angle in range(0,360,30):
  car=Car(x=s[0],z=s[2],heading=s[3]+math.radians(angle));camera=Camera();assert lib.chase_reset(C.byref(camera),C.byref(car),s[1]);view=Frustum();eye=F3(*[p*scale for p in camera.eye]);at=F3(*[p*scale for p in camera.target]);assert lib.world_frustum(C.byref(view),eye,at,math.radians(camera.fov),400/240,.15*scale,700*scale)
  visible=[i for i,b in enumerate(bounds) if lib.world_visible(C.byref(view),C.byref(b))];triangles=sum(batches[i][1]//3 for i in visible);calls=0;last=None
  for i in visible:
   first,count,tex,_=batches[i]
   if last is None or last[0]!=first or last[1]!=tex:calls+=1
   last=(first+count,tex)
  records.append(dict(location=label,heading_offset_deg=angle,drawn_triangles=triangles,drawn_batches=len(visible),merged_draw_calls=calls,culled_percent=round(100*(1-triangles/(nv/3)),1)))
report=dict(total_triangles=nv//3,total_batches=nb,cell_size_m=64,samples=records,min_drawn=min(r['drawn_triangles'] for r in records),max_drawn=max(r['drawn_triangles'] for r in records),mean_drawn=round(statistics.mean(r['drawn_triangles'] for r in records)),geometry_and_contact_lossless=True)
Path('/workspace/port-research/rockport/v0.15/visibility-profile.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='samples'}));print('Start view:',records[0])
