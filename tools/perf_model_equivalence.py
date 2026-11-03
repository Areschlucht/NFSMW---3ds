#!/usr/bin/env python3
"""Bounded exact ordered-attribute audit of same-hash original model variants.

Geometry equivalence is distinct from conservative full catalog equivalence.
Unknown header/leaf fields remain guards, never assumed unused material data.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import mmap
from pathlib import Path
import struct
from decode_world import decode_model
from nfs_rockport import chunks


def sha(value):
    return hashlib.sha256(value).hexdigest()


def signatures(data, start, end):
    decoded = decode_model(data,start,end,allow_triangle_statistic_mismatch=True)
    leaves={k:(start+a,start+b) for k,a,b in chunks(data[start:end])}
    hs,he=leaves[0x134011];h=(hs+15)&~15
    gs,ge=leaves[0x80134100]
    geometry={k:(gs+a,gs+b) for k,a,b in chunks(data[gs:ge])}
    meta=(geometry[0x134800][0]+15)&~15
    table=(geometry[0x134801][0]+15)&~15
    blob=(geometry[0x134802][0]+31)&~31
    count=struct.unpack_from('>H',data,meta+4)[0]
    size,po,unused,co,uv=struct.unpack_from('>5I',data,meta+8)
    ts,te=leaves[0x134012]
    consumed=hashlib.sha256()
    strip_attributes=hashlib.sha256()

    def corner_bytes(p,c,t):
        return (struct.pack('>3f',*decoded['positions'][p]) +
                bytes(data[blob+uv+t*4:blob+uv+(t+1)*4]) +
                bytes(data[blob+co+c*4:blob+co+(c+1)*4]))
    # Descriptor order/corner counts/primitive boundaries are a separate guard,
    # because invisible degenerate strips can still affect future material code.
    material=hashlib.sha256()
    for i in range(count):
        d=bytes(data[table+i*16:table+(i+1)*16])
        material.update(d[4:])  # exclude only relocatable geometry blob offset
        slot=d[10];material.update(bytes(data[ts+slot*8:ts+(slot+1)*8]))
        flags=d[12];widths=[2 if flags&bit else 1 for bit in (16,4,2)]
        at=blob+struct.unpack_from('>I',d)[0]+(3 if flags&128 else 0)
        strip_attributes.update(struct.pack('>I',d[8]))
        for _ in range(d[8]):
            indices=[]
            for width in widths:
                indices.append(int.from_bytes(data[at:at+width],'big'));at+=width
            strip_attributes.update(corner_bytes(*indices))
    for face in decoded['faces']:
        consumed.update(bytes.fromhex(face['texture']))
        for p,c,t in face['corners']:
            consumed.update(corner_bytes(p,c,t))
    header=bytearray(data[h:h+160])
    guard=hashlib.sha256(header)
    # Header statistic is not consumed by draw emission, but the later recovered
    # LOD consumer DOES use its signed>39 gate. Keep every original header bit.
    # Unknown leaves and metadata stay
    # conservative guards; no inference that identical geometry means full GX
    # material semantics are interchangeable.
    for k,(a,b) in sorted(leaves.items()):
        if k not in (0x134011,0x80134100,0x134012):
            guard.update(struct.pack('>I',k));guard.update(bytes(data[a:b]))
    guard.update(bytes(data[ts:te]))
    guard.update(bytes(data[meta:meta+28]))
    for k,(a,b) in sorted(geometry.items()):
        if k not in (0x134800,0x134801,0x134802):
            guard.update(struct.pack('>I',k));guard.update(bytes(data[a:b]))
    geom=consumed.hexdigest();matrix=sha(bytes(data[h+64:h+128]));mat=material.hexdigest();unknown=guard.hexdigest()
    strip=strip_attributes.hexdigest()
    strict=sha(bytes.fromhex(geom+strip+matrix+mat+unknown))
    return dict(geometry_sha256=geom,matrix_sha256=matrix,descriptor_material_sha256=mat,
                ordered_strip_attributes_sha256=strip,
                conservative_unknown_guard_sha256=unknown,catalog_sha256=strict,
                triangles=len(decoded['faces']),header_statistic_mismatch=decoded['triangle_statistic_mismatch'])


def audit(inventory, stream, output):
    inv=json.loads(inventory.read_text());groups=defaultdict(dict);aliases=defaultdict(list)
    with stream.open('rb') as source:
        if hashlib.file_digest(source,'sha256').hexdigest()!=inv['source_sha256']:
            raise ValueError('Source stream provenance mismatch')
    for model in inv['models']:
        groups[model['hash']][model['raw_sha256']]=model
        aliases[model['raw_sha256']].append(dict(section=model['section'],offset=model['offset'],bytes=model['bytes']))
    result=dict(schema=1,kind='layered-consumed-geometry-audit',source_sha256=inv['source_sha256'],
                inventory_sha256=sha(inventory.read_bytes()),groups={},summary={},
                limitations=['Exact consumed geometry signature includes original fourth colour byte, not generated alpha.',
                    'Geometry-only equivalence does not establish identical materials, shader programs or original LOD selection.',
                    'Conservative catalog guard retains unknown fields/leaf bytes and descriptor widths; false nonmerges are allowed.',
                    'Every raw alias is retained; no global one-model-per-hash choice is made.'])
    counts=Counter()
    with stream.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as full:
        for key,variants in sorted(groups.items()):
            if len(variants)<2:continue
            rows=[]
            for raw,model in variants.items():
                start=model['offset'];end=start+model['bytes']
                if sha(full[start:end])!=raw:raise ValueError('Original model provenance mismatch')
                row=dict(raw_sha256=raw,name=model['name'],aliases=aliases[raw])
                try:
                    row.update(signatures(full,start,end));counts['decoded_variants']+=1
                except (ValueError,struct.error,UnicodeDecodeError) as err:
                    row['error']=str(err);counts['rejected_variants']+=1
                rows.append(row)
            valid=[r for r in rows if 'error' not in r]
            geom=len({r['geometry_sha256'] for r in valid});catalog=len({r['catalog_sha256'] for r in valid})
            category=('unresolved_decode' if len(valid)!=len(rows) else
                      'different_consumed_geometry' if geom>1 else
                      'same_geometry_guarded_differences' if catalog>1 else 'full_guard_equivalent')
            counts[category]+=1
            result['groups'][key]=dict(classification=category,geometry_classes=geom,catalog_classes=catalog,variants=rows)
            if len(result['groups'])%200==0:print('Audited',len(result['groups']),'ambiguous hash groups',flush=True)
    counts['ambiguous_hash_groups']=len(result['groups']);result['summary']=dict(counts)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
    rows={}
    for key,group in result['groups'].items():
        for variant in group['variants']:
            rows[variant['raw_sha256']]=dict(original_hash=key,
                catalog_key=key+':'+variant['catalog_sha256'] if 'catalog_sha256' in variant else None,
                geometry_sha256=variant.get('geometry_sha256'),aliases=variant['aliases'],decode_error=variant.get('error'))
    catalog=dict(schema=2,scope='Only ambiguous groups; fullheaderstatistic retained becauseLOD consumes it.',
        source_sha256=result['source_sha256'],audit_sha256=sha(output.read_bytes()),raw_variants=rows,
        unresolved_groups={k:g for k,g in result['groups'].items() if g['classification']=='unresolved_decode'})
    output.with_name('catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory',type=Path,default=Path('/workspace/port-research/world-streaming/initial-render-inventory.json'))
    p.add_argument('--stream',type=Path,default=Path('/workspace/port-research/rockport/samples/STREAML2RA-full.BUN'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();audit(a.inventory,a.stream,a.output)
