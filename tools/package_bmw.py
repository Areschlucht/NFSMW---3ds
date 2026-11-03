#!/usr/bin/env python3
"""Package the static BMW body viewer and already converted scene sidecars."""
import argparse
import hashlib
import json
import struct
import zipfile
import zlib
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('scene',type=Path)
args=parser.parse_args();project=Path(__file__).resolve().parent.parent
raw=(args.scene/'body.nfm').read_bytes()
magic,version,nv,nb,nt,size,crc,reserved=struct.unpack_from('<4s7I',raw)
if magic!=b'NFM1' or version!=1 or len(raw)!=size+32 or zlib.crc32(raw[32:])!=crc:
    raise SystemExit('Invalid scene header/CRC')
manifest=json.loads((args.scene/'scene.json').read_text())
if nt!=len(manifest['textures']) or nv!=manifest['vertices']:
    raise SystemExit('Scene manifest mismatch')
texture_paths=[]
for i in range(nt):
    key=struct.unpack_from('<I',raw,32+i*16)[0]
    if f'{key:08x}'!=manifest['textures'][i]['hash']:raise SystemExit('Texture order mismatch')
    path=args.scene/'textures'/f'{key:08x}.t3x'
    if not path.is_file() or path.stat().st_size<16:raise SystemExit(f'Missing texture: {path}')
    texture_paths.append(path)
binary=project/'nfsmw-bmw-viewer.3dsx';icon=project/'nfsmw-bmw-viewer.smdh'
if binary.read_bytes()[:4]!=b'3DSX' or icon.read_bytes()[:4]!=b'SMDH':raise SystemExit('Invalid executable/icon build')
out=project/'dist';out.mkdir(exist_ok=True);destination=out/'nfsmw-menu-prototype-v0.5.zip'
prefix='3ds/nfsmw-bmw-viewer/'
with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for path in (binary,icon,args.scene/'body.nfm'):z.write(path,prefix+path.name)
    for path in texture_paths:z.write(path,prefix+'textures/'+path.name)
    z.write(project/'BMW-VIEWER.md',prefix+'README.md')
    z.write(args.scene/'scene.json',prefix+'scene.json')
with zipfile.ZipFile(destination) as z:
    if z.testzip() is not None:raise SystemExit('ZIP CRC check failed')
print(destination)
print('SHA-256:',hashlib.sha256(destination.read_bytes()).hexdigest())
