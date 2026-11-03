#!/usr/bin/env python3
"""Identify exact original zero-packet model records without relaxing decoder."""
from collections import defaultdict
import hashlib
import json
import mmap
from pathlib import Path
import struct
from nfs_rockport import chunks

def digest(b):return hashlib.sha256(b).hexdigest()
def audit():
 root=Path('/workspace/port-research');invpath=root/'world-streaming/initial-render-inventory.json';inv=json.loads(invpath.read_text());rows=[];groups=defaultdict(list)
 with (root/'rockport/samples/STREAML2RA-full.BUN').open('rb') as source,mmap.mmap(source.fileno(),0,access=mmap.ACCESS_READ) as data:
  for model in inv['models']:
   if model.get('reason')!='Invalid geometry metadata/bounds':continue
   start=model['offset'];end=start+model['bytes'];assert digest(data[start:end])==model['raw_sha256']
   leaves={k:(start+a,start+b) for k,a,b in chunks(data[start:end])};assert set(leaves)=={0x134011,0x134012,0x80134100}
   hs,he=leaves[0x134011];h=(hs+15)&~15;assert data[hs:h]==bytes([0x11])*(h-hs)
   header=bytes(data[h:h+160]);tail=bytes(data[h+160:he]);name=tail.split(b'\0')[0];assert b'\0' in tail
   ts,te=leaves[0x134012];material=bytes(data[ts:te]);assert len(material)%8==0
   gs,ge=leaves[0x80134100];geo={k:(gs+a,gs+b) for k,a,b in chunks(data[gs:ge])};assert set(geo)=={0x134800,0x134801,0x134802}
   semantic=[]
   for kind,alignment in ((0x134800,16),(0x134801,16),(0x134802,32)):
    a,b=geo[kind];aligned=(a+alignment-1)&-alignment;assert aligned<=b and data[a:aligned]==bytes([0x11])*(aligned-a)
    semantic.append(bytes(data[aligned:b]))
   meta,descriptors,blob=semantic
   assert len(meta)>=28 and struct.unpack_from('>3H',meta)==(22,0,0)
   assert meta[:2]==b'\0\x16' and not any(meta[2:]) and not descriptors and not blob
   # Header name tail padding is retained verbatim as well, so unexplained bytes
   # cannot accidentally make two no-draw records share a full payload.
   guard=digest(header+tail+struct.pack('>I',len(material))+material+struct.pack('>I',len(meta))+meta)
   row=dict(hash=model['hash'],name=model['name'],raw_sha256=model['raw_sha256'],section=model['section'],offset=start,bytes=model['bytes'],guard_sha256=guard,
            classification='EXACT_SOURCE_EMPTY_NO_DRAW',catalog_key=model['hash']+':EMPTY:'+guard,
            header_sha256=digest(header),material_refs_sha256=digest(material),metadata_sha256=digest(meta),header_signed_statistic=struct.unpack_from('<h',header,20)[0],
            matrix_sha256=digest(header[64:128]),metric9c_bits=header[156:160].hex(),name_tail_sha256=digest(tail),metadata_bytes=len(meta))
   rows.append(row);groups[model['hash']].append(row)
 report=dict(schema=1,source_sha256=inv['source_sha256'],inventory_sha256=digest(invpath.read_bytes()),summary=dict(occurrences=len(rows),hashes=len(groups),equivalent_groups=sum(len({r['guard_sha256'] for r in g})==1 for g in groups.values())),
             groups={k:dict(empty=True,full_guard_equivalent=len({r['guard_sha256'] for r in g})==1,aliases=g) for k,g in groups.items()},
             limitations='Static original zero-draw records only. Preserve raw160 header and all provenance; animation/runtime population remains a separate unresolved gate. No nonempty decoder relaxed; no fabricated render faces.')
 assert len(rows)==21 and len(groups)==18
 out=root/'hardware-optimization/model-equivalence/empty-catalog.json';out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['summary'],indent=2));print('Guard mismatches:',[k for k,g in report['groups'].items() if not g['full_guard_equivalent']])
if __name__=='__main__':audit()
