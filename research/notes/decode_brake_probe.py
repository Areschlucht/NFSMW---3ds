#!/usr/bin/env python3
"""Experimental, sample-specific partial geometry probe, not a general decoder.

Exports only two candidate GX triangle strips in raw integer coordinate units.
Other primitives, materials, vertex attributes, and coordinate scale are unresolved.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def decode(data):
    if len(data) != 6080 or not data[0x230:].startswith(b'BRAKE_KIT00_B\0'):
        raise ValueError('Expected the inspected brake geometry sample')
    if struct.unpack_from('<II', data, 0x310) != (0x134802, 700):
        raise ValueError('Unexpected geometry data chunk')
    vertices = [struct.unpack_from('>3h', data, 0x428+i*6) for i in range(22)]
    faces = []
    strips = []
    degenerate = 0
    for offset, expected_count in ((0x340, 22), (0x3c0, 7)):
        # 0x9a is consistent with a GX triangle strip using vertex format 2.
        opcode, count = struct.unpack_from('>BH', data, offset)
        if opcode != 0x9a or count != expected_count:
            raise ValueError('Unexpected candidate primitive header')
        attributes = [tuple(data[offset+3+i*5:offset+8+i*5]) for i in range(count)]
        indices = [a[0] for a in attributes]
        if any(index >= len(vertices) for index in indices):
            raise ValueError('Position index out of bounds')
        strips.append(dict(offset=offset, vertices=count, attribute_indices=attributes))
        for i in range(count-2):
            a,b,c = indices[i:i+3]
            if i % 2:
                a,b = b,a
            if len({a,b,c}) != 3:
                degenerate += 1
                continue
            u = tuple(vertices[b][j]-vertices[a][j] for j in range(3))
            v = tuple(vertices[c][j]-vertices[a][j] for j in range(3))
            cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
            if cross == (0,0,0):
                degenerate += 1
                continue
            faces.append((a,b,c))
    return vertices, faces, dict(sha256=hashlib.sha256(data).hexdigest(),
        status='experimental partial mesh; raw coordinate units; not hardware validated',
        position_count=len(vertices), triangle_count=len(faces),
        degenerate_triangle_count=degenerate, strips=strips,
        bounds_raw=[(min(v[i] for v in vertices), max(v[i] for v in vertices)) for i in range(3)])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('asset', type=Path)
    parser.add_argument('output_directory', type=Path)
    args = parser.parse_args()
    vertices, faces, report = decode(args.asset.read_bytes())
    args.output_directory.mkdir(parents=True, exist_ok=True)
    obj = ['# Experimental PARTIAL mesh; raw integer coordinates; scale unknown',
           'o EBRAKE_KIT00_B_partial']
    obj += ['v %d %d %d' % v for v in vertices]
    obj += ['f %d %d %d' % tuple(i+1 for i in face) for face in faces]
    (args.output_directory/'brake-partial.obj').write_text('\n'.join(obj)+'\n')
    (args.output_directory/'brake-probe.json').write_text(json.dumps(report, indent=2)+'\n')
    # Three orthographic projections make coordinate and topology mistakes visible.
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="380" viewBox="0 0 960 380">',
           '<rect width="960" height="380" fill="#151923"/>',
           '<text x="20" y="25" fill="white" font-family="sans-serif" font-size="16">Experimental partial brake mesh — raw units; two candidate strips only</text>']
    for panel,(axis1,axis2,label) in enumerate(((0,2,'XZ'),(0,1,'XY'),(2,1,'ZY'))):
        for face in faces:
            points = ' '.join(f'{panel*320+160+vertices[i][axis1]*0.38:.2f},{205-vertices[i][axis2]*0.38:.2f}' for i in face)
            svg.append(f'<polygon points="{points}" fill="#4ac9b8" fill-opacity="0.15" stroke="#4ac9b8" stroke-width="1"/>')
        svg.append(f'<text x="{panel*320+145}" y="365" fill="white" font-family="sans-serif">{label}</text>')
    svg.append('</svg>')
    (args.output_directory/'brake-partial.svg').write_text('\n'.join(svg))
    print(json.dumps({k:v for k,v in report.items() if k!='strips'}, indent=2))
