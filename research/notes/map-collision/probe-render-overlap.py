import sys,struct,json,math,statistics
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools')
from world_collision import packages
stream=Path('/workspace/port-research/rockport/samples/STREAML2RA-full.BUN').read_bytes()
selected=set(range(101,131));all_tris=[]
for pack in packages(stream):
 if pack['id'] not in selected:continue
 for instance in pack['instances']:
  assert instance['basis_x']==[1,0,0] and instance['basis_z']==[0,0,1]
  asset=pack['assets'][instance['asset_index']];t=instance['world_to_local_translation']
  for part in asset['parts']:
   for triangle in part['triangles']:
    vertices=[part['vertices'][i] for i in triangle['corners']]
    all_tris.append((vertices,t,pack['id'],asset['materials'][triangle['material_index']],triangle['attributes']))
raw=Path('/workspace/port-research/rockport/scene-v0.15/road.nrd').read_bytes();origin=struct.unpack_from('<3f',raw,24)
queries=[]
for v in struct.iter_unpack('<9f',raw[64:]):queries.append([sum(v[a+3*i] for i in range(3))/3+origin[a] for a in range(3)])
reports={}
for variant in ('inverse_translation','reflected_local'):
 rows=[];grid={};step=32
 for vertices,t,pack,material,flags in all_tris:
  if variant=='inverse_translation':points=[[p[2]-t[2],p[1]-t[1],p[0]-t[0]]for p in vertices]
  else:points=[[-p[2]-t[2],-p[1]-t[1],-p[0]-t[0]]for p in vertices]
  a,b,c=points;ax,az=b[0]-a[0],b[2]-a[2];bx,bz=c[0]-a[0],c[2]-a[2];den=ax*bz-az*bx
  if abs(den)<1e-6:continue
  lowx=min(p[0]for p in points);highx=max(p[0]for p in points);lowz=min(p[2]for p in points);highz=max(p[2]for p in points)
  index=len(rows);rows.append((a,ax,az,b[1]-a[1],bx,bz,c[1]-a[1],den,pack,material,flags))
  for x in range(math.floor(lowx/step),math.floor(highx/step)+1):
   for z in range(math.floor(lowz/step),math.floor(highz/step)+1):grid.setdefault((x,z),[]).append(index)
 residual=[];miss=0;over2=0;matched=[]
 for qi,p in enumerate(queries):
  candidates=[]
  for i in grid.get((math.floor(p[0]/step),math.floor(p[2]/step)),[]):
   a,ax,az,ay,bx,bz,by,den,pack,mat,flags=rows[i];dx,dz=p[0]-a[0],p[2]-a[2];u=(dx*bz-dz*bx)/den;v=(ax*dz-az*dx)/den
   if u<-.00001 or v<-.00001 or u+v>1.00001:continue
   height=a[1]+u*ay+v*by;candidates.append((abs(height-p[1]),height,pack,mat,flags))
  if not candidates:miss+=1;continue
  best=min(candidates);residual.append(best[0]);over2+=best[0]>2;matched.append(dict(query=qi,source_view=p,collision_height=best[1],error=best[0],pack=best[2],material=f'{best[3]:08x}',flags=best[4]))
 sorted_r=sorted(residual)
 reports[variant]=dict(query_count=len(queries),projected_collision_matches=len(residual),no_collision_triangle=miss,within_2cm=sum(x<.02 for x in residual),within_5cm=sum(x<.05 for x in residual),within_10cm=sum(x<.1 for x in residual),within_2m=sum(x<2 for x in residual),median_error=statistics.median(residual),p95_error=sorted_r[int(len(sorted_r)*.95)],max_error=max(residual),mean_error=statistics.mean(residual),examples=matched[:10])
 print(variant,{k:v for k,v in reports[variant].items() if k!='examples'})
Path('/workspace/port-research/map-collision/render-collision-overlap.json').write_text(json.dumps(reports,indent=2)+'\n')
