#!/usr/bin/env python3
"""Mutation checks on real source geometry for the layered alias audit."""
import json
from pathlib import Path
import struct
from perf_model_equivalence import signatures
from decode_world import decode_model
from nfs_rockport import chunks


def main():
    root=Path('/workspace/port-research')
    inv=json.loads((root/'world-streaming/initial-render-inventory.json').read_text())
    model=next(m for m in inv['models'] if m['validated'] and m['expected_triangles']>0)
    section=next(s for s in inv['sections'] if s['id']==model['section'])
    with (root/'rockport/samples/STREAML2RA-full.BUN').open('rb') as f:
        f.seek(section['offset']);source=f.read(section['bytes'])
    start=model['offset']-section['offset'];end=start+model['bytes']
    base=signatures(source,start,end);decoded=decode_model(source,start,end)
    leaves={k:(start+a,start+b) for k,a,b in chunks(source[start:end])}
    hs,he=leaves[0x134011];header=(hs+15)&~15
    gs,ge=leaves[0x80134100];geo={k:(gs+a,gs+b) for k,a,b in chunks(source[gs:ge])}
    meta=(geo[0x134800][0]+15)&~15;blob=(geo[0x134802][0]+31)&~31
    _,_,_,color,uv=struct.unpack_from('>5I',source,meta+8)
    p,c,t=decoded['faces'][0]['corners'][0]
    for label,offset in [('rgb',blob+color+c*4),('fourth_source_byte',blob+color+c*4+3),('uv',blob+uv+t*4+1)]:
        changed=bytearray(source);changed[offset]^=1;signature=signatures(changed,start,end)
        assert signature['geometry_sha256']!=base['geometry_sha256'],label
        assert signature['catalog_sha256']!=base['catalog_sha256'],label
    changed=bytearray(source);changed[header+64]^=1;signature=signatures(changed,start,end)
    assert signature['geometry_sha256']==base['geometry_sha256']
    assert signature['matrix_sha256']!=base['matrix_sha256']
    assert signature['catalog_sha256']!=base['catalog_sha256']
    changed=bytearray(source);changed[leaves[0x134012][0]+4]^=1;signature=signatures(changed,start,end)
    assert signature['geometry_sha256']==base['geometry_sha256']
    assert signature['catalog_sha256']!=base['catalog_sha256']
    changed=bytearray(source);changed[header+20]^=1;signature=signatures(changed,start,end)
    assert signature['geometry_sha256']==base['geometry_sha256']
    assert signature['catalog_sha256']!=base['catalog_sha256']
    assert signature['header_statistic_mismatch']
    print('Real-source mutations pass: RGB, fourthmetadata byte, UV, matrix, materialref and LOD-consumed original statistic break guarded key.')


if __name__=='__main__':main()
