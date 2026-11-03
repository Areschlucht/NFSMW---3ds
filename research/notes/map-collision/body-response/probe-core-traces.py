import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools')
from world_collision_response_reference import OriginalBodyCoreReference
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
identity=(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)
with DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin') as model:
 r=OriginalBodyCoreReference(Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes(),model);rows=[]
 for mass,inertia,point,mode in ((1,(1,1,1),(0,0,0),0),(2,(2,2,2),(0,0,0),0),(2,(2,2,2),(0,0,1),0),(2,(2,2,2),(0,0,1),1),(1500,(400,2000,2200),(0,0,2),0)):
  output=r.contact(mass=mass,inertia=inertia,cg=(0,0,0),velocity=(-10,1,0),angular=(0,0,0),position=(0,0,0),orientation=identity,point=point,normal=(1,0,0),friction=(.3,.55),mode=mode)
  rows.append(dict(mass=mass,inertia=inertia,point=point,mode=mode,output=output));print(mass,point,mode,'v',output['velocity'],'w',output['angular'],'J',output['normal_correction'],'mat',output['trace'][0]['effective_matrix'])
 report=dict(dol_sha256=r.dol.sha256,core_sha256=hashlib.sha256(r.dol.read(0x80083c74,0xa1c)).hexdigest(),cases=rows,limitations='Original core executable model with explicit synthetic physical-state producer inputs. BMW parameter/tensor/shape binding and original swept shape contact remain open.')
 Path('/workspace/port-research/map-collision/body-response/original-core-traces.json').write_text(json.dumps(report,indent=2)+'\n')
