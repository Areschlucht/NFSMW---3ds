#!/usr/bin/env python3
"""Package the original-sector driving prototype and its converted sidecars."""
import argparse
import hashlib
import json
import struct
import zipfile
import zlib
from pathlib import Path
from wheel_rig import inspect_rig


def scene_files(folder,name,texture_dir):
    raw=(folder/name).read_bytes()
    magic,version,nv,nb,nt,size,crc,reserved=struct.unpack_from('<4s7I',raw)
    stride=32 if version==1 else 48
    if magic!=b'NFM1' or version not in (1,2) or reserved or len(raw)!=size+32 or size!=nt*16+nb*16+nv*stride or zlib.crc32(raw[32:])!=crc:
        raise ValueError('Invalid scene header/CRC')
    files=[(folder/name,name)]
    manifest=json.loads((folder/'scene.json').read_text())
    if manifest['vertices']!=nv or len(manifest['textures'])!=nt:raise ValueError('Scene manifest mismatch')
    for i in range(nt):
        key=struct.unpack_from('<I',raw,32+i*16)[0]
        if manifest['textures'][i]['hash']!=f'{key:08x}':raise ValueError('Texture manifest order mismatch')
        path=folder/'textures'/f'{key:08x}.t3x'
        if path.stat().st_size<16:raise ValueError('Invalid texture sidecar')
        files.append((path,f'{texture_dir}/{path.name}'))
    return files


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('world',type=Path);p.add_argument('bmw',type=Path)
    a=p.parse_args();project=Path(__file__).resolve().parent.parent
    raw=(a.world/'road.nrd').read_bytes()
    magic,version,count,crc=struct.unpack_from('<4sIII',raw)
    if magic!=b'NRD1' or version!=1 or len(raw)!=64+count*36 or zlib.crc32(raw[64:])!=crc:raise ValueError('Invalid contact asset')
    files=scene_files(a.world,'world.nfm','world-textures')+scene_files(a.bmw,'body.nfm','car-textures')
    body=(a.bmw/'body.nfm').read_bytes()
    inspect_rig((a.bmw/'wheels.nwa').read_bytes(),struct.unpack_from('<I',body,12)[0],struct.unpack_from('<I',body,24)[0])
    files.append((a.bmw/'wheels.nwa','wheels.nwa'))
    for suffix,signature in (('3dsx',b'3DSX'),('smdh',b'SMDH')):
        binary=project/f'nfsmw-rockport.{suffix}'
        if binary.read_bytes()[:4]!=signature:raise ValueError('Invalid application build')
        files.append((binary,binary.name))
    files.extend(((a.world/'road.nrd','road.nrd'),(project/'ROCKPORT-PROTOTYPE.md','README.md'),
                  (a.world/'scene.json','world-scene.json'),(a.bmw/'scene.json','car-scene.json')))
    destination=project/'dist/nfsmw-rockport-prototype-v0.17.zip';destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path,name in files:archive.write(path,'3ds/nfsmw-rockport/'+name)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:raise ValueError('ZIP integrity check failed')
    print(destination)
    print('SHA-256:',hashlib.sha256(destination.read_bytes()).hexdigest())
