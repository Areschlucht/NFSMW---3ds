"""Full-stream bounded render inventory, preserving every original occurrence."""
from pathlib import Path
from collections import Counter,defaultdict
import sys,struct,json,hashlib,mmap,time
from nfs_rockport import decode as decode_index,chunks
from decode_world import decode_model
from world_instances import read_instances
import argparse
parser=argparse.ArgumentParser(description='Inventory original models one indexed section at a time; no global mesh arrays')
parser.add_argument('--samples',type=Path,required=True)
parser.add_argument('--output-directory',type=Path,required=True)
args=parser.parse_args()
root=args.samples;ix=decode_index((root/'L2RA.BUN').read_bytes())['sections'];out=args.output_directory;out.mkdir(parents=True,exist_ok=True);models=[];bad=[];sections=[];fmtcounts=Counter();top=Counter();texsources=defaultdict(list);occ=Counter();time0=time.time()
with (root/'STREAML2RA-full.BUN').open('rb') as f:
 with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as full:
  for sn,section in enumerate(ix):
   off=section['offset'];data=full[off:off+section['bytes']];record=dict(section,top_chunks={},model_hashes=[],texture_hashes=[],instance_model_keys=[]);kinds=Counter()
   for kind,a,b in chunks(data):
    kinds[f'{kind:08x}']+=1;top[f'{kind:08x}']+=1
    if kind==0x80134000:
     for k,s,e in chunks(data[a:b]):
      s+=a;e+=a
      if k!=0x80134010:continue
      leaves={k:(s+q,s+r) for k,q,r in chunks(data[s:e])}
      if 0x134011 not in leaves:continue
      h,he=leaves[0x134011];h=(h+15)&~15
      name=data[h+160:he].split(b'\0')[0].decode('ascii');key=f'{struct.unpack_from("<I",data,h+16)[0]:08x}';expected=struct.unpack_from('<H',data,h+20)[0]
      m=dict(name=name,hash=key,section=section['id'],offset=off+s,bytes=e-s,expected_triangles=expected,raw_sha256=hashlib.sha256(data[s:e]).hexdigest(),bounds=[list(struct.unpack_from('<3f',data,h+x)) for x in (32,48)],matrix=list(struct.unpack_from('<16f',data,h+64)))
      record['model_hashes'].append(key);occ[key]+=1
      ts,te=leaves[0x134012];m['textures']=[f'{struct.unpack_from("<I",data,q)[0]:08x}' for q in range(ts,te,8)]
      g,ge=leaves[0x80134100];gg={k:(g+q,g+r) for k,q,r in chunks(data[g:ge])};meta=(gg[0x134800][0]+15)&~15;table=(gg[0x134801][0]+15)&~15;blob=(gg[0x134802][0]+31)&~31;cnt=struct.unpack_from('>H',data,meta+4)[0]
      desc=[]
      for d in range(cnt):
       q=table+d*16;de=dict(offset=struct.unpack_from('>I',data,q)[0],raw=data[q:q+16].hex(),n=data[q+8],n9=data[q+9],tex=data[q+10],byte11=data[q+11],flags=data[q+12],fmt=data[q+13],bytes=struct.unpack_from('>H',data,q+14)[0]);desc.append(de);fmtcounts[str(de['fmt'])]+=1
      m['consumed_textures']=sorted({m['textures'][de['tex']] for de in desc if de['tex']<len(m['textures'])})
      try:
       decoded=decode_model(data,s,e);m['validated_triangles']=len(decoded['faces']);m['positions']=len(decoded['positions']);m['validated']=True
      except (ValueError,struct.error) as error:
       m['validated']=False;m['reason']=str(error);m['draws']=desc;bad.append(m.copy())
      models.append(m)
    elif kind==0xb3300000:
     parts={k:(a+s,a+e) for k,s,e in chunks(data[a:b])};h,he=parts[0xb3310000];hdr={k:(h+s,h+e) for k,s,e in chunks(data[h:he])};ks,ke=hdr[0x33310002]
     for p in range(ks,ke,8):
      key=f'{struct.unpack_from("<I",data,p)[0]:08x}';texsources[key].append(dict(section=section['id'],offset=off+a-8,bytes=b-a+8));record['texture_hashes'].append(key)
   try:
    instances=read_instances(data);record['instances']=len(instances);record['instance_model_keys']=sorted({k for i in instances for k in i['keys']});record['instance_bounds']=[min(i['bounds'][a] for i in instances) for a in range(3)]+[max(i['bounds'][a+3] for i in instances) for a in range(3)] if instances else None
   except ValueError as err:record['instance_error']=str(err)
   record['top_chunks']=dict(kinds);sections.append(record)
   if sn%100==0:print(sn,'sections,',len(models),'models,',len(bad),'rejects',round(time.time()-time0,1),'s',flush=True)
with (root/'STREAML2RA-full.BUN').open('rb') as source:
 source_sha=hashlib.file_digest(source,'sha256').hexdigest()
report=dict(source_sha256=source_sha,sections=sections,models=models,rejected=bad,texture_sources=dict(texsources),top_chunks=dict(top),formats=dict(fmtcounts),model_occurrences=dict(occ));(out/'initial-render-inventory.json').write_text(json.dumps(report,indent=2)+'\n');print('Done',len(models),'models',len(bad),'rejected',len(texsources),'texture keys',sum(s.get('instances',0) for s in sections),'instances',time.time()-time0)
