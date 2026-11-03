#!/usr/bin/env python3
"""Strict original0x3B901 compound body-bound recovery; unknown fields retained.

Source layout is established by original8021E0E0 endian/pointer fixup and
8021DFCC/E004 child/mesh accessors. Packed quaternion uses1/32767; center and
half-extents use original float0.001, without invented quaternion normalization.
This decodes original compound geometry, not car-body impulse integration.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from nfs_rockport import chunks
from map_recovery_ps_reference import f32
from vehicle_vlt_hash import vlt_hash


def decode_bound_package(data,start,end):
    q=(start+15)&~15
    if q+32>end or any(v!=0x11 for v in data[start:q]):raise ValueError('Invalid bound alignment/padding')
    key,count,fixed,reserved=struct.unpack_from('<4I',data,q)
    table=q+16;mesh_at=table+count*48
    if fixed or reserved or not 1<=count<=4096 or mesh_at+16>end:raise ValueError('Unsupported body bound header/count')
    mesh_count,mr0,mr1,mr2=struct.unpack_from('<4I',data,mesh_at)
    if mesh_count>128 or any((mr0,mr1,mr2)):raise ValueError('Unsupported body mesh header')
    meshes=[];at=mesh_at+16
    for index in range(mesh_count):
        if at+16>end:raise ValueError('Short body mesh descriptor')
        vertices,r0,r1,pointer=struct.unpack_from('<4I',data,at)
        if not 1<=vertices<=65535 or any((r0,r1,pointer)) or vertices>(end-at-16)//16:raise ValueError('Invalid body mesh vertex count/pointer')
        points=[list(struct.unpack_from('<4f',data,at+16+i*16)) for i in range(vertices)]
        if not all(math.isfinite(x) for p in points for x in p):raise ValueError('Nonfinite body mesh vertex')
        meshes.append(dict(index=index,source_offset=at,vertices=points))
        at+=16+vertices*16
    if at!=end:raise ValueError('Unconsumed body bound bytes')
    bounds=[]
    for index in range(count):
        b=table+index*48;raw=data[b:b+48]
        quat=struct.unpack_from('<4h',raw);center=struct.unpack_from('<3h',raw,8);flags=struct.unpack_from('<H',raw,14)[0]
        extents=struct.unpack_from('<3h',raw,16);children=raw[22];mesh=struct.unpack_from('b',raw,23)[0]
        extra=struct.unpack_from('<3h',raw,24);first_child=struct.unpack_from('<h',raw,30)[0]
        radius,material,unknown,pointer=struct.unpack_from('<f3I',raw,32)
        if any(v<0 for v in extents) or not math.isfinite(radius) or radius<0 or pointer:raise ValueError('Invalid body bound extent/radius/backpointer')
        if children and (first_child<0 or first_child+children>count or first_child<=index):raise ValueError('Invalid original bound children')
        if not children and first_child!=-1:raise ValueError('Unexpected leaf child offset')
        if mesh< -1 or mesh>=mesh_count or flags&16 and mesh<0:raise ValueError('Invalid bound mesh reference')
        bounds.append(dict(index=index,source_offset=b,raw_hex=raw.hex(),quaternion_raw=list(quat),quaternion=[f32(v*f32(1/32767)) for v in quat],center_raw=list(center),center=[f32(v*f32(.001)) for v in center],half_extents_raw=list(extents),half_extents=[f32(v*f32(.001)) for v in extents],flags=flags,child_count=children,first_child=first_child,mesh_index=mesh,raw_extra_position=list(extra),source_radius=radius,material_key=material,unknown_28=unknown))
    return dict(key=key,source_offset=q,source_bytes=end-q,source_sha256=hashlib.sha256(data[q:end]).hexdigest(),bounds=bounds,meshes=meshes)


def body_packages(data):
    for kind,start,end in chunks(data):
        if kind!=0x8003b900:continue
        for child,a,b in chunks(data[start:end]):
            if child!=0x3b901:raise ValueError('Unexpected body-bound child chunk')
            yield decode_bound_package(data,start+a,start+b)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bundle',type=Path);p.add_argument('output',type=Path);p.add_argument('--name',default='BMWM3GTRE46');args=p.parse_args();raw=args.bundle.read_bytes()
    packages=list(body_packages(raw));selected=[v for v in packages if v['key']==vlt_hash(args.name)]
    if len(selected)!=1:raise ValueError('Requested original model bound hash is missing/ambiguous')
    report=dict(source_sha256=hashlib.sha256(raw).hexdigest(),model_name=args.name,model_key=vlt_hash(args.name),package_count=len(packages),selected=selected[0],limitations='Original compound body geometry; original child flags/material semantics and actual rigid-body response must be preserved. No guessed box replacement.')
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(packages=len(packages),model=args.name,bounds=len(selected[0]['bounds']),meshes=len(selected[0]['meshes']))))


def fixed_reference_image(data,package,base_address=0x60010000):
    """Independent expected original endian/pointer-fixup image for host checks.

    Never used by native runtime; source raw bound/mesh fields stay preserved.
    """
    q=package['source_offset'];out=bytearray(data[q:q+package['source_bytes']])
    for at in (0,4):out[at:at+4]=out[at:at+4][::-1]
    struct.pack_into('>I',out,8,1)
    for bound in package['bounds']:
        at=bound['source_offset']-q
        for offset in (0,2,4,6,8,10,12,14,16,18,20,24,26,28,30):out[at+offset:at+offset+2]=out[at+offset:at+offset+2][::-1]
        for offset in (32,36,40):out[at+offset:at+offset+4]=out[at+offset:at+offset+4][::-1]
        struct.pack_into('>I',out,at+44,base_address)
    mesh_header=16+len(package['bounds'])*48;out[mesh_header:mesh_header+4]=out[mesh_header:mesh_header+4][::-1]
    for mesh in package['meshes']:
        at=mesh['source_offset']-q;out[at:at+4]=out[at:at+4][::-1];struct.pack_into('>I',out,at+12,base_address+at+16)
        for i in range(len(mesh['vertices'])*4):
            p=at+16+i*4;out[p:p+4]=out[p:p+4][::-1]
    return bytes(out)
