import hashlib,json,random,sys
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools')
from map_recovery_dol import DolImage
from map_recovery_ps_reference import point_transform_reference
from world_collision import instance_matrix,transform_point,inverse_affine,packages
raw=Path('/workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol').read_bytes()
dol=DolImage(raw)
code=dol.read(0x80193498,0x54)
rng=random.Random(2005)
maximum=0;count=0
for package in packages(Path('/workspace/port-research/rockport/samples/STREAML2RA-full.BUN').read_bytes()):
 for instance in package['instances']:
  matrix=instance_matrix(instance)
  # Source mesh centers transformed local→world→local exercise realistic
  # large translations, plus a non-central point. Keep float arithmetic error.
  asset=package['assets'][instance['asset_index']]
  local=asset['parts'][0]['center'] if asset['parts'] else asset['walls'][0]['endpoint_a'] if asset['walls'] else [0,0,0]
  point=transform_point(local,inverse_affine(matrix))
  reference=point_transform_reference(code,point,matrix)
  scalar=transform_point(point,matrix)
  maximum=max(maximum,max(abs(a-b) for a,b in zip(reference,scalar)))
  count+=1
# Exactly representable dyadic corpus, affine scale/reflection/shear/translation.
for _ in range(10000):
 matrix=[rng.randint(-20,20)/8 if i%4!=3 else 0 for i in range(16)];matrix[15]=1
 point=[rng.randint(-100,100)/8 for _ in range(3)]
 assert point_transform_reference(code,point,matrix)==transform_point(point,matrix)
report=dict(dol_sha256=dol.sha256,address='0x80193498',bytes=len(code),routine_sha256=hashlib.sha256(code).hexdigest(),original_instance_cases=count,synthetic_exact_dyadic_affine_cases=10000,max_original_instance_vs_binary64_affine_difference=maximum,limitations='Bounded instruction interpretation with binary64 intermediates rounded binary32 per paired op; not exact Gekko FMA/FPSCR emulation. Source CI orientations all identity; nonzero orientation flags rejected.')
Path('/workspace/port-research/map-collision/point-transform-reference.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
