#!/usr/bin/env python3
"""Pack one cold source plan for both scenery flags and collision group admission."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('plan','stream','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();plan=json.loads(a.plan.read_text());summary=plan['summary']
    if summary['transform_mutation_count'] or summary['normal_draw_context_flags']!=16:raise ValueError('Unsupported source transform/context')
    groups=bytearray(512)
    for op in summary['operations']:
        group=op['group_id']
        if op['original_state_argument']!=0 or not 0<group<4096:raise ValueError('Unsupported cold activation')
        groups[group//8]|=1<<(group%8)
    h=hashlib.sha256()
    with a.stream.open('rb') as f:
        while b:=f.read(1048576):h.update(b)
    rows=sorted(plan['overrides'],key=lambda r:r['source_instance_offset']);previous=-1;records=[]
    for r in rows:
        offset=r['source_instance_offset'];old=r['expected_source_flags'];new=r['effective_flags']
        if offset<=previous or old^new!=0x10 or not old&16:raise ValueError('Unsupported source flags')
        previous=offset;records.append(struct.pack('<3I',offset,old,new))
    data=bytearray(128)+groups+b''.join(records)
    struct.pack_into('<4s8I',data,0,b'NWS1',1,len(data),0,summary['bin_index'],16,len(rows),128,640)
    data[64:96]=h.digest();data[96:128]=bytes.fromhex(summary['source_sha256']['gameplay'])
    struct.pack_into('<I',data,12,zlib.crc32(data[16:]))
    if a.output.exists() and a.output.read_bytes()!=data:raise ValueError('Existing output differs')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if not a.output.exists():a.output.write_bytes(data)
    print(json.dumps({'bin':summary['bin_index'],'overrides':len(rows),'active_groups':summary['active_group_ids'],'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}))
