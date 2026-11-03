#!/usr/bin/env python3
"""Clone a car scene using original source normals verified per expanded corner.
Geometry/UVs, materials, batch ordering and wheel payload stay unchanged.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import zlib
from wheel_rig import inspect_rig


def apply(source,reference,normal_dir,destination):
    if destination.exists():raise ValueError('Destination exists; sources are never overwritten')
    report=json.loads((normal_dir/'manifest.json').read_text())
    ref=reference.read_bytes();raw=bytearray((source/'body.nfm').read_bytes())
    if hashlib.sha256(ref).hexdigest()!=report['reference_nfm_sha256']:raise ValueError('Reference source differs')
    magic,version,nv,nb,nt,size,old_crc,reserved=struct.unpack_from('<4s7I',raw)
    if magic!=b'NFM1' or version!=1 or reserved or len(raw)!=size+32 or size!=nt*16+nb*16+nv*32 or zlib.crc32(raw[32:])!=old_crc:raise ValueError('Invalid NFM1 car')
    if struct.unpack_from('<3I',ref,8)!=(nv,nb,nt) or nv!=report['vertex_count']:raise ValueError('Corner counts differ')
    start=32+nt*16+nb*16
    if raw[32+nt*16:start]!=ref[32+nt*16:start]:raise ValueError('Batch order differs')
    normals=(normal_dir/'normals-f32le.bin').read_bytes()
    if len(normals)!=nv*12 or hashlib.sha256(normals).hexdigest()!=report['normals_sha256']:raise ValueError('Normals source differs')
    for i in range(nv):
        at=start+i*32
        if raw[at:at+12]!=ref[at:at+12] or raw[at+24:at+32]!=ref[at+24:at+32]:raise ValueError('Original position/UV correspondence differs')
        normal=struct.unpack_from('<3f',normals,i*12)
        if not all(math.isfinite(v) for v in normal) or not .9<sum(v*v for v in normal)<1.1:raise ValueError('Invalid original normal')
        raw[at+12:at+24]=normals[i*12:(i+1)*12]
    rig=bytearray((source/'wheels.nwa').read_bytes());inspect_rig(rig,nb,old_crc)
    crc=zlib.crc32(raw[32:]);struct.pack_into('<I',raw,24,crc);struct.pack_into('<I',rig,24,crc);inspect_rig(rig,nb,crc)
    shutil.copytree(source,destination)
    (destination/'body.nfm').write_bytes(raw);(destination/'wheels.nwa').write_bytes(rig)
    manifest=json.loads((source/'scene.json').read_text());manifest['original_normals']={'normals_sha256':report['normals_sha256'],'source_geometry_sha256':report['source_geometry_sha256'],'verified_corners':nv,'source_format':report['source_format'],'lighting':'Source normals supplied to existing provisional inspection shader; original lighting not claimed'}
    (destination/'scene.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (destination/'normal-source-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(destination);print(f'{nv} source normals applied; positions/UVs and draw order unchanged; CRC binding valid.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['source','reference','normal_dir','destination']:parser.add_argument(name,type=Path)
    args=parser.parse_args();apply(args.source,args.reference,args.normal_dir,args.destination)
