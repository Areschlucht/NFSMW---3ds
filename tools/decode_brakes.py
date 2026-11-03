#!/usr/bin/env python3
"""Decode the four supplied brake meshes using the executable's aligned layout.

Supports format 0x16 with raw four-index or compiled five-index strips only.
UVs, candidate normals and reference hashes are exported; image textures,
material behavior and other vertex formats remain unsupported.
"""
import argparse
import json
import struct
from pathlib import Path


def decode(data, lod=None):
    def u16(p): return struct.unpack_from('>H', data, p)[0]
    def u32(p): return struct.unpack_from('>I', data, p)[0]
    def children(start, end):
        while start < end:
            if start+8 > end: raise ValueError('Short chunk header')
            kind, size = struct.unpack_from('<II', data, start)
            stop = start+8+size
            if stop > end: raise ValueError('Chunk outside parent')
            yield kind, start, stop
            start = stop
    root = list(children(0, len(data)))
    if root[0][0] != 0x80134000: raise ValueError('Not a geometry package')
    models = []
    for kind, start, end in children(root[0][1]+8, root[0][2]):
        if kind != 0x80134010: continue
        parts = {k:(s,e) for k,s,e in children(start+8, end)}
        header = parts[0x134011][0]+8
        name = data[header+160:parts[0x134011][1]].split(b'\0')[0].decode('ascii')
        if lod is not None and not name.endswith('_'+lod):continue
        geom, stop = parts[0x80134100]
        leaves = {k:(s,e) for k,s,e in children(geom+8,stop)}
        def references(kind):
            s,e=parts[kind]
            if (e-s-8)%8: raise ValueError('Unexpected reference table size')
            return [struct.unpack_from('<I',data,p)[0] for p in range(s+8,e,8)]
        texture_hashes=references(0x134012)
        shader_hashes=references(0x134013)
        meta = (leaves[0x134800][0]+0x17)&~15
        table = (leaves[0x134801][0]+0x17)&~15
        blob = (leaves[0x134802][0]+0x27)&~31
        if u16(meta)!=22: raise ValueError('Unsupported vertex format')
        count=u16(meta+4)
        if table+count*16 > leaves[0x134801][1]: raise ValueError('Short descriptor table')
        data_size=u32(meta+8)
        if blob+data_size > leaves[0x134802][1]: raise ValueError('Short geometry data')
        faces=[]; max_index=-1; strips=[]; degenerate=0
        for i in range(count):
            record=table+i*16; off=u32(record); length=u16(record+14)
            n=data[record+8]; flags=data[record+12]; fmt=data[record+13]
            if fmt!=22 or flags&~0x9e or n<3: raise ValueError('Unsupported draw record')
            if off+length>data_size: raise ValueError('Draw record outside geometry blob')
            p=blob+off
            widths=[2 if flags&bit else 1 for bit in (16,8,4,2)]
            stream_widths=widths[:3]+([widths[2]] if flags&128 else [])+widths[3:]
            stride=sum(stream_widths)
            prefix=3 if flags&128 else 0
            if prefix+n*stride>length: raise ValueError('Short strip')
            if prefix and (data[p]!=0x9a or u16(p+1)!=n): raise ValueError('Unexpected display list')
            corners=[]
            for j in range(n):
                at=p+prefix+j*stride;values=[]
                for width in stream_widths:
                    values.append(int.from_bytes(data[at:at+width],'big'));at+=width
                corners.append(values)
            ids=[c[0] for c in corners]
            uv_ids=[c[-1] for c in corners]
            normal_ids=[c[1] for c in corners]
            texture_index=data[record+10]; shader_index=data[record+11]
            if texture_index>=len(texture_hashes) or shader_index>=len(shader_hashes):
                raise ValueError('Reference table index out of bounds')
            max_index=max(max_index,*ids)
            strips.append(dict(offset=off, compiled=bool(prefix), indices=ids,
                               uv_indices=uv_ids, group=data[record+9],
                               normal_indices=normal_ids,
                               texture_hash=f'{texture_hashes[texture_index]:08x}',
                               shader_hash=f'{shader_hashes[shader_index]:08x}'))
            for j in range(n-2):
                a,b,c=ids[j:j+3]
                if j%2:a,b=b,a
                corners=[j,j+1,j+2]
                if j%2: corners[0],corners[1]=corners[1],corners[0]
                faces.append(((a,b,c),tuple(uv_ids[q] for q in corners),
                              tuple(normal_ids[q] for q in corners),len(strips)-1))
        position_offset=u32(meta+12)
        if position_offset+(max_index+1)*6>u32(meta+20): raise ValueError('Position array overlaps next array')
        positions=[tuple(x/2048 for x in struct.unpack_from('>3h',data,blob+position_offset+i*6)) for i in range(max_index+1)]
        uv_offset=u32(meta+24)
        uv_count=max(i for strip in strips for i in strip['uv_indices'])+1
        if uv_offset+uv_count*4>data_size: raise ValueError('UV array exceeds geometry blob')
        texcoords=[tuple(x/4096 for x in struct.unpack_from('>2h',data,blob+uv_offset+i*4)) for i in range(uv_count)]
        normal_offset=u32(meta+16)
        normal_count=max(i for strip in strips for i in strip['normal_indices'])+1
        if normal_offset+normal_count*4>data_size: raise ValueError('Normal array exceeds geometry blob')
        normals=[tuple(x/64 for x in struct.unpack_from('>3b',data,blob+normal_offset+i*4)) for i in range(normal_count)]
        good=[]; face_uvs=[]; face_normals=[]; face_strips=[]
        for (a,b,c),uv_ids,normal_ids,strip_index in faces:
            u=[positions[b][i]-positions[a][i] for i in range(3)];v=[positions[c][i]-positions[a][i] for i in range(3)]
            if len({a,b,c})<3:
                degenerate+=1;continue
            good.append((a,b,c))
            face_uvs.append(uv_ids); face_strips.append(strip_index)
            face_normals.append(normal_ids)
        expected=struct.unpack_from('<H',data,header+20)[0]
        if len(good)!=expected: raise ValueError(f'{name}: decoded {len(good)} triangles, header {expected}')
        models.append(dict(name=name,positions=positions,faces=good,strips=strips,
                           transform=struct.unpack_from('<16f',data,header+64),
                           texcoords=texcoords,face_uv_indices=face_uvs,face_strip_indices=face_strips,
                           normal_candidates=normals,face_normal_indices=face_normals,
                           texture_hashes=[f'{h:08x}' for h in texture_hashes],
                           shader_hashes=[f'{h:08x}' for h in shader_hashes],
                           skipped_degenerate=degenerate,header_triangles=expected,
                           stored_bounds=[struct.unpack_from('<3f',data,header+x) for x in (32,48)]))
    return models


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('asset',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--lod',choices=['A','B','C','D','E'],help='Explicitly select one detail level')
    args=parser.parse_args(); models=decode(args.asset.read_bytes(),args.lod);args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'models.json').write_text(json.dumps(models,indent=2)+'\n')
    for model in models:
        lines=['# Decoded brake geometry; positions use GX signed-16 fractional scale 11', 'o '+model['name']]
        lines+=['v %.9g %.9g %.9g'%tuple(p) for p in model['positions']]
        lines+=['vt %.9g %.9g'%tuple(uv) for uv in model['texcoords']]
        lines+=['vn %.9g %.9g %.9g'%tuple(n) for n in model['normal_candidates']]
        previous=None
        for face,uvs,normals,strip in zip(model['faces'],model['face_uv_indices'],model['face_normal_indices'],model['face_strip_indices']):
            if strip!=previous:
                descriptor=model['strips'][strip]
                lines.append('g strip_%d_tex_%s_shader_%s'%(strip,descriptor['texture_hash'],descriptor['shader_hash']))
                previous=strip
            lines.append('f '+' '.join(f'{v+1}/{uv+1}/{n+1}' for v,uv,n in zip(face,uvs,normals)))
        (args.output/(model['name']+'.obj')).write_text('\n'.join(lines)+'\n')
        print(model['name'],len(model['positions']),'positions',len(model['faces']),'triangles')
