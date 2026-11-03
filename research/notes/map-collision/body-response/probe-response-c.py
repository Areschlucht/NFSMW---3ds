import ctypes,hashlib,json,math,random,struct,sys
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools')
from world_collision_response_reference import OriginalBodyCoreReference
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
F=ctypes.c_float
class State(ctypes.Structure):_fields_=[('mass',F),('inertia',F*3),('cg',F*3),('position',F*3),('orientation',F*16),('velocity',F*3),('angular',F*3),('moment_scale',F*3),('extra',F)]
class Contact(ctypes.Structure):_fields_=[('point',F*3),('normal',F*3),('friction',F*2),('passes',ctypes.c_uint)]
class Result(ctypes.Structure):_fields_=[('velocity',F*3),('angular',F*3),('normal_velocity',F*3),('tangent_velocity',F*3),('normal_correction',F*3),('friction_correction',F*3),('branch',ctypes.c_uint),('iterations',ctypes.c_uint)]
lib=ctypes.CDLL('/tmp/mw-body-response.so');lib.mw_body_collision_response.argtypes=[ctypes.POINTER(State),ctypes.POINTER(Contact),ctypes.POINTER(Result)];lib.mw_body_collision_response.restype=ctypes.c_int
identity=(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)
rng=random.Random(130044);cases=[]
for mass,inertia,point in [(1,(1,1,1),(0,0,0)),(2,(2,2,2),(0,0,1)),(1500,(400,2000,2200),(0,0,2))]:
 cases.append(dict(mass=mass,inertia=inertia,cg=(0,0,0),velocity=(-10,1,0),angular=(0,0,0),position=(0,0,0),orientation=identity,point=point,normal=(1,0,0),friction=(.3,.55),passes=16))
for i in range(297):
 t=rng.uniform(-math.pi,math.pi);cs,sn=math.cos(t),math.sin(t)
 orientation=identity if i%3==0 else (cs,0,sn,0,0,1,0,0,-sn,0,cs,0,0,0,0,1)
 cases.append(dict(mass=rng.choice([1,2,500,1500]),inertia=[rng.choice([.5,1,2,400,2000]) for _ in range(3)],cg=[rng.uniform(-.5,.5) for _ in range(3)],velocity=[rng.uniform(-20,20) for _ in range(3)],angular=[rng.uniform(-2,2) for _ in range(3)],position=[rng.uniform(-100,100) for _ in range(3)],orientation=orientation,point=[rng.uniform(-100,100) for _ in range(3)],normal=[rng.uniform(-1,1) for _ in range(3)],friction=rng.choice([(0,0),(.3,.55),(.8,1)]),moment_scale=rng.choice([(1,1,1),(3,1.5,3)]),passes=rng.choice([1,2,4,16,32])))
for i in range(700):
 t=rng.uniform(-math.pi,math.pi);cs,sn=math.cos(t),math.sin(t)
 orientation=identity if i%4==0 else (cs,0,sn,0,0,1,0,0,-sn,0,cs,0,0,0,0,1)
 pos=[rng.uniform(-2000,2000) for _ in range(3)]
 cases.append(dict(mass=rng.choice([1,2,500,1500]),inertia=[rng.choice([0,1e-7,1e-6,2e-6,.5,1,2,400,2000]) for _ in range(3)],cg=[rng.uniform(-.5,.5) for _ in range(3)],velocity=[rng.uniform(-20,20) for _ in range(3)],angular=[rng.uniform(-2,2) for _ in range(3)],position=pos,orientation=orientation,point=[p+rng.uniform(-2,2) for p in pos],normal=(0,0,0) if i%40==0 else [rng.uniform(-3,3) for _ in range(3)],friction=rng.choice([(0,0),(.3,.55),(.8,1)]),moment_scale=rng.choice([(1,1,1),(3,1.5,3)]),passes=rng.choice([1,2,4,16,32,64]),extra_normal_accumulation=rng.choice([0,0,0,.1,1])))
errors=[];comparisons=0;hit_count=0;branches={};iteration_histogram={}
with DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin') as model:
 ref=OriginalBodyCoreReference(Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes(),model)
 for i,k in enumerate(cases):
  expected=ref.contact(**k);s=State(k['mass'],(F*3)(*k['inertia']),(F*3)(*k['cg']),(F*3)(*k['position']),(F*16)(*k['orientation']),(F*3)(*k['velocity']),(F*3)(*k['angular']),(F*3)(*k.get('moment_scale',(1,1,1))),k.get('extra_normal_accumulation',0))
  c=Contact((F*3)(*k['point']),(F*3)(*k['normal']),(F*2)(*k['friction']),k['passes']);r=Result();hit=lib.mw_body_collision_response(ctypes.byref(s),ctypes.byref(c),ctypes.byref(r))
  hit_count+=int(expected['hit']);branches[str(expected['friction_branch'])]=branches.get(str(expected['friction_branch']),0)+1
  iteration_histogram[str(r.iterations)]=iteration_histogram.get(str(r.iterations),0)+1
  mismatches=[]
  for field,ex in [('velocity','velocity'),('angular','angular'),('normal_velocity','normal_momentum'),('tangent_velocity','tangent_momentum'),('normal_correction','normal_correction'),('friction_correction','friction_correction')]:
   actual=list(getattr(r,field));wanted=list(expected[ex]);comparisons+=3
   if struct.pack('>3f',*actual)!=struct.pack('>3f',*wanted):mismatches.append(dict(field=field,actual=actual,expected=wanted))
  if hit!=int(expected['hit']) or r.branch!=expected['friction_branch']:mismatches.append(dict(hit=hit,expectedhit=expected['hit'],branch=r.branch,expectedbranch=expected['friction_branch']))
  if mismatches:errors.append(dict(case=i,input=k,mismatches=mismatches,trace=expected['trace']))
  if i<5:print(i,'hit',hit,'errors',mismatches)
 report=dict(dol_sha256=ref.dol.sha256,original_core_address='0x80083C74',original_core_sha256=hashlib.sha256(ref.dol.read(0x80083c74,0xa1c)).hexdigest(),original_state_constructor_sha256=hashlib.sha256(ref.dol.read(0x800837d0,0x1b8)).hexdigest(),portable_source_sha256=hashlib.sha256(Path('/workspace/NFSMW---3ds/source_bmw/mw_body_collision_response.c').read_bytes()).hexdigest(),cases=len(cases),hit_cases=hit_count,branch_counts=branches,iteration_histogram=iteration_histogram,float_comparisons=comparisons,error_cases=len(errors),errors=errors,limitations='Bounded original PPC/PS functional reference with pinned external Gekko estimate model. Explicit synthetic producer inputs, not BMW parameter binding or swept original body-contact generation. FPSCR/PS subnormal modes and hardware console trace excluded.')
 Path('/workspace/port-research/map-collision/body-response/response-c-differential.json').write_text(json.dumps(report,indent=2)+'\n')
print('cases',len(cases),'error_cases',len(errors))
