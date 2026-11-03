#!/usr/bin/env python3
"""Pack strictly decoded original collision banks for bounded section activation.

NWC1 stores source-native BE CA banks unchanged and compact LE directory plus original CI
records. No geometry reconstruction, material substitution or guessed impulses.
Associations require exact source containment with original offsets and hashes.
"""
import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path
from world_collision import packages


def pack(stream, containment):
    source_sha = hashlib.sha256(stream).hexdigest()
    if containment['source_sha256'] != source_sha:
        raise ValueError('Containment source SHA differs from stream')
    by_offset = {r['collision_offset']: r for r in containment['relations']}
    if len(by_offset) != len(containment['relations']):
        raise ValueError('Duplicate physical collision containment record')
    contents = {}
    associations = []
    for package in packages(stream):
        offset, size = package['source_offset'], package['source_bytes']
        sha = hashlib.sha256(stream[offset:offset+size]).hexdigest()
        relation = by_offset.pop(offset, None)
        if relation is None or relation['bytes'] != size or relation['sha256'] != sha or relation['collision_id'] != package['id']:
            raise ValueError('Missing or mismatched exact collision containment')
        if not 0 <= relation['section_id'] <= 65535:
            raise ValueError('Section ID exceeds runtime representation')
        if sha not in contents:
            count = len(package['instances'])
            payload = bytearray(struct.pack('<4sIII', b'NWP1', count, 16, 16+count*96))
            payload.extend(bytes(count*96))
            asset_offsets = {}
            for index, asset in package['assets'].items():
                asset_offsets[index] = len(payload)
                payload.extend(stream[asset['source_offset']:asset['source_offset']+asset['source_bytes']])
            for index, ci in enumerate(package['instances']):
                if ci['basis_x'] != [1,0,0] or ci['basis_z'] != [0,0,1] or ci['raw_10'] & 3:
                    raise ValueError('Unsupported collision instance orientation')
                asset = package['assets'][ci['asset_index']]
                at = 16+index*96
                struct.pack_into('<IIIIHHIII', payload, at,
                    asset_offsets[ci['asset_index']], asset['source_bytes'],
                    ci['source_offset'], asset['source_offset'], 0, ci['asset_index'],
                    asset['raw_token'], 0, 0)
                payload[at+32:at+96] = stream[ci['source_offset']:ci['source_offset']+64]
            contents[sha] = dict(id=package['id'], payload=bytes(payload), instances=count,source_offset=offset,source_bytes=size)
        associations.append((relation['section_id'], sha, offset))
    if by_offset:
        raise ValueError('Containment refers to absent original collision package')
    ordered = sorted(contents, key=lambda sha: contents[sha]['id'])
    if len({contents[s]['id'] for s in ordered}) != len(ordered):
        raise ValueError('Same original collision ID has different content')
    if len(ordered) > 512 or len(associations) > 1024:
        raise ValueError('Collision directory exceeds bounded runtime limits')
    associations.sort()
    if len({a[0] for a in associations}) != len(associations):
        raise ValueError('Multiple original collision packages in one stream section')
    table_offset = 64
    associations_offset = table_offset+len(ordered)*32
    data_offset = (associations_offset+len(associations)*12+15)&~15
    out = bytearray(data_offset)
    directory = []
    package_index = {sha:i for i,sha in enumerate(ordered)}
    for i, sha in enumerate(ordered):
        package = contents[sha];payload = package['payload'];at=len(out)
        struct.pack_into('<8I', out, table_offset+i*32, package['id'],at,len(payload),
                         package['instances'],zlib.crc32(payload),package['source_offset'],package['source_bytes'],0)
        out.extend(payload)
        directory.append(dict(index=i,id=package['id'],offset=at,bytes=len(payload),instances=package['instances'],sha256=hashlib.sha256(payload).hexdigest(),original_sha256=sha))
    for i,(section,sha,original_offset) in enumerate(associations):
        struct.pack_into('<III',out,associations_offset+i*12,section,package_index[sha],original_offset)
    struct.pack_into('<4s7I32s',out,0,b'NWC1',1,len(ordered),len(associations),table_offset,associations_offset,data_offset,len(out),bytes.fromhex(source_sha))
    return bytes(out),dict(source_sha256=source_sha,format='NWC1',version=1,bytes=len(out),packages=directory,
                           associations=[dict(section_id=s,package_index=package_index[h],original_collision_offset=o) for s,h,o in associations],
                           limitations='Identity original CI only. Runtime applies original load-time0xC0 flags. Section activation/order supplied by original streaming selector; no body response or material substitution.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stream',type=Path);p.add_argument('containment',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
    raw,report=pack(args.stream.read_bytes(),json.loads(args.containment.read_text()));args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(raw)
    report['sha256']=hashlib.sha256(raw).hexdigest();args.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('bytes','sha256')}))
