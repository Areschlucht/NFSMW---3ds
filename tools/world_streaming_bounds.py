"""Cross-check model positions, header bounds and original instance transforms."""
import sys,json,mmap,collections,itertools
from pathlib import Path
from world_instances import read_instances,transform_points
from world_render_recovery_geometry import diagnose_model
import argparse
parser=argparse.ArgumentParser(description='Validate all original sibling LODs against stored instance bounds without relaxing tolerance')
parser.add_argument('--inventory',type=Path,required=True)
parser.add_argument('--stream',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
inv=json.loads(args.inventory.read_text());target={m['hash'] for m in inv['rejected'] if 'Triangle count mismatch' in m['reason']};byhash=collections.defaultdict(list)
for m in inv['models']:byhash[m['hash']].append(m)
records=[];cache={}
def bounds(points):return [min(p[a] for p in points) for a in range(3)]+[max(p[a] for p in points) for a in range(3)]
with args.stream.open('rb') as f:
 with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as full:
  for section in inv['sections']:
   data=full[section['offset']:section['offset']+section['bytes']]
   for inst in read_instances(data):
    if not target.intersection(inst['keys']):continue
    candidates=[]
    for key in inst['keys']:
     for source in byhash.get(key,[]):
      sha=source['raw_sha256']
      if sha not in cache:
       start=source['offset'];prefix=start%32;raw=bytes(prefix)+full[start:start+source['bytes']]
       try:cache[sha]=diagnose_model(raw,prefix,len(raw))[0]
       except ValueError:cache[sha]=None
      model=cache[sha]
      if model is None:continue
      tight=bounds(transform_points(model['positions'],inst['matrix'],inst['translation']))
      corners=list(itertools.product(*zip(*model['bounds'])));transformed_header=bounds(transform_points(corners,inst['matrix'],inst['translation']))
      error=lambda bb:max(abs(a-b) for a,b in zip(bb,inst['bounds']))
      violation=max([inst['bounds'][a]-tight[a] for a in range(3)]+[tight[a+3]-inst['bounds'][a+3] for a in range(3)]+[0])
      candidates.append(dict(hash=key,model=model['name'],source_section=source['section'],source_offset=source['offset'],tight_error=error(tight),transformed_header_error=error(transformed_header),containment_violation=violation,tight_bounds=tight,transformed_header_bounds=transformed_header))
    records.append(dict(name=inst['name'],section=section['id'],offset=section['offset']+inst['offset'],stored_bounds=inst['bounds'],best_tight=min(candidates,key=lambda c:c['tight_error']),best_header=min(candidates,key=lambda c:c['transformed_header_error']),best_contained=min(candidates,key=lambda c:c['containment_violation'])))
sumry=dict(instances=len(records),tight_matches=sum(r['best_tight']['tight_error']<=.15 for r in records),transformed_header_matches=sum(r['best_header']['transformed_header_error']<=.15 for r in records),contained=sum(r['best_contained']['containment_violation']<=.05 for r in records),decoded_raw_variants=len(cache));args.output.write_text(json.dumps(dict(summary=sumry,instances=records),indent=2)+'\n');print(sumry);print([(r['name'],r['best_tight']['tight_error'],r['best_header']['transformed_header_error'],r['best_contained']['containment_violation']) for r in records if r['best_tight']['tight_error']>.15][:15])
