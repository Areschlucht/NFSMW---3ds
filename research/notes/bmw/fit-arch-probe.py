import sys,numpy as np
from pathlib import Path
sys.path.insert(0,'/workspace/NFSMW---3ds/tools');from decode_brakes import decode
m=next(m for m in decode(Path('/workspace/attachments/561b3c3e-177e-4bdd-9a6d-d8c1b9f6e01f/BMWM3GTRE46-GEOMETRY.BIN').read_bytes(),lod='B') if m['name']=='BMWM3GTRE46_KIT00_BODY_B')
for side in (1,-1):
 for end in (1,-1):
  ps=np.unique(np.array([p for p in m['positions'] if p[1]*side>.75 and .28<p[2]<.7 and p[0]*end>.6]),axis=0)
  pts=ps[:,[0,2]];rng=np.random.default_rng(0);best=None
  for it in range(3000):
   s=pts[rng.choice(len(pts),3,replace=False)];A=np.column_stack((2*s,np.ones(3)))
   try:sol=np.linalg.solve(A,np.sum(s*s,axis=1))
   except np.linalg.LinAlgError:continue
   c=sol[:2];r2=sol[2]+sum(c*c)
   if r2<=0:continue
   r=r2**.5
   if not .34<r<.5 or not .0<c[1]<.35 or not .8<c[0]*end<1.85:continue
   error=np.abs(np.linalg.norm(pts-c,axis=1)-r);ids=error<.006
   score=(sum(ids),-float(np.mean(error[ids])))
   if best is None or score>best[0]:best=score,c,r,ids
  _,c,r,ids=best;q=pts[ids];sol=np.linalg.lstsq(np.column_stack((2*q,np.ones(len(q)))),np.sum(q*q,axis=1),rcond=None)[0];c=sol[:2];r=(sol[2]+sum(c*c))**.5
  print(side,end,'center',c,'radius',r,'count',sum(ids),'outerY',np.median(abs(ps[ids,1])),'err',np.sqrt(np.mean((np.linalg.norm(q-c,axis=1)-r)**2)))
