import hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools')
from world_collision_response_shapes import body_packages,fixed_reference_image
from world_collision_response_reference import OriginalBodyBoundReference
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
D=Path('/workspace/port-research/v018-decoded/GLOBAL-GLOBALB_VM_NGC.BUN').read_bytes();r=OriginalBodyBoundReference(Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes(),DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin'))
packages=0;bounds=0;meshes=0;vertices=0;fixup_errors=[];decode_errors=[]
for p in body_packages(D):
 packages+=1;expected=fixed_reference_image(D,p);q=p['source_offset'];actual=r.fixup(D[q:q+p['source_bytes']]);meshes+=len(p['meshes']);vertices+=sum(len(m['vertices']) for m in p['meshes'])
 if expected!=actual:fixup_errors.append(dict(key=hex(p['key']),differences=[i for i,(a,b) in enumerate(zip(expected,actual)) if a!=b][:30]))
 for b in p['bounds']:
  off=b['source_offset']-q;v=r.decode_vectors(actual[off:off+48]);bounds+=1
  for key in ('center','half_extents','quaternion'):
   if struct.pack('>'+str(len(v[key]))+'f',*v[key])!=struct.pack('>'+str(len(b[key]))+'f',*b[key]):decode_errors.append(dict(key=hex(p['key']),bound=b['index'],field=key,expected=b[key],actual=v[key]))
report=dict(dol_sha256=r.dol.sha256,source_sha256=hashlib.sha256(D).hexdigest(),packages=packages,bounds=bounds,meshes=meshes,vertices=vertices,fixup_failures=len(fixup_errors),fixup_examples=fixup_errors[:10],vector_float_bit_failures=len(decode_errors),vector_examples=decode_errors[:10],original_fixup='0x8021e0e0',original_vector_slice='0x8021e440..0x8021e60c',limitations='Original compound bound/mesh decoder, not collision impulse integration. Raw quaternions not renormalized; all unknown source fields retained.')
Path('/workspace/port-research/map-collision/body-response/bound-decoder-differential.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
