#!/usr/bin/env python3
"""Validate and package the native v0.18 prototype with private converted assets."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zipfile
import zlib
from package_rockport import scene_files
from wheel_rig import inspect_rig

ROOT=Path(__file__).resolve().parents[1]
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def validate_pack(path):
    with path.open('rb') as f:
        h=bytearray(f.read(128));stored=struct.unpack_from('<I',h,96)[0];struct.pack_into('<I',h,96,0)
        if h[:4]!=b'MWP1' or zlib.crc32(h)!=stored:raise ValueError('World archive header/CRC')
        version,header,stride,count,index_crc,data,total=struct.unpack_from('<7I',h,4)
        if (version,header,stride)!=(1,128,64) or not 0<count<=32768 or total!=path.stat().st_size:raise ValueError('World archive shape')
        index=f.read(count*64)
        if zlib.crc32(index)!=index_crc:raise ValueError('World archive index CRC')
        previous=None;end=data;counts={1:0,2:0,3:0};boot=False
        for at in range(0,len(index),64):
            kind,key,identity,offset,size,crc=struct.unpack_from('<II32sIII',index,at)
            order=(kind,key,identity)
            if kind not in counts or previous is not None and order<=previous:raise ValueError('World archive key order')
            if not size or offset%128 or offset<end or offset+size>total:raise ValueError('World archive range')
            if kind!=3 and any(identity):raise ValueError('Nontexture archive identity')
            f.seek(offset);payload=f.read(size)
            if len(payload)!=size or zlib.crc32(payload)!=crc:raise ValueError(f'World payload CRC {kind}/{key:08x}')
            previous=order;end=offset+size;counts[kind]+=1;boot|=kind==2 and key==0
        if end!=total or not boot:raise ValueError('World archive tail/boot providers')
        return dict(source_sha256=bytes(h[32:64]).hex(),scene_manifest_sha256=bytes(h[64:96]).hex(),entries=count,kind_counts=counts)

def package(args):
    pack_info=validate_pack(args.world_pack)
    wst=args.metadata.read_bytes();collision=args.collision.read_bytes();road=args.road.read_bytes()
    if wst[:4]!=b'WST1' or collision[:4]!=b'NWC1' or road[:4]!=b'NRD1':raise ValueError('Metadata/collision/road signature')
    source=bytes.fromhex(pack_info['source_sha256'])
    if source!=wst[64:96] or source!=collision[32:64]:raise ValueError('World/collision source mismatch')
    _,version,count,crc=struct.unpack_from('<4sIII',road)
    if version!=1 or len(road)!=64+count*36 or zlib.crc32(road[64:])!=crc:raise ValueError('Road spawn CRC')
    body=(args.bmw/'body.nfm').read_bytes()
    inspect_rig((args.bmw/'wheels.nwa').read_bytes(),struct.unpack_from('<I',body,12)[0],struct.unpack_from('<I',body,24)[0])
    ui=args.ui.read_bytes()
    if ui[:4]!=b'NUI2' or len(ui)<48 or zlib.crc32(ui[48:])!=struct.unpack_from('<I',ui,12)[0]:raise ValueError('UI artwork CRC')
    files=scene_files(args.bmw,'body.nfm','car-textures')
    files += [(args.bmw/'wheels.nwa','wheels.nwa'),(args.road,'road.nrd'),(args.world_pack,'world.mwp'),
        (args.metadata,'world-streaming.bin'),(args.collision,'world.nwc'),(args.ui,'ui.nui'),
        (ROOT/'ROCKPORT-PROTOTYPE.md','README.md')]
    for suffix,signature in [('3dsx',b'3DSX'),('smdh',b'SMDH')]:
        path=ROOT/(args.binary+'.'+suffix)
        with path.open('rb') as f:
            if f.read(4)!=signature:raise ValueError('Application signature')
        files.append((path,'nfsmw-rockport.'+suffix))
    names=[n for _,n in files]
    if len(names)!=len(set(names)):raise ValueError('Duplicate package path')
    manifest={'version':'0.18','type':'native asset-based prototype','full_original_physics':False,
        'whole_city_validated':False,'world':pack_info,
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'files':[{'path':n,'bytes':p.stat().st_size,'sha256':sha(p)} for p,n in files]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.exists():raise FileExistsError(args.output)
    with zipfile.ZipFile(args.output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path,name in files:z.write(path,'3ds/nfsmw-rockport/'+name)
        z.writestr('3ds/nfsmw-rockport/manifest.json',json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(args.output) as z:
        if z.testzip():raise ValueError('ZIP CRC failed')
        for row in manifest['files']:
            with z.open('3ds/nfsmw-rockport/'+row['path']) as f:
                if hashlib.file_digest(f,'sha256').hexdigest()!=row['sha256']:raise ValueError('ZIP SHA mismatch')
    digest=sha(args.output)
    args.output.with_suffix('.zip.sha256').write_text(digest+'  '+args.output.name+'\n')
    print(json.dumps({'zip':str(args.output),'bytes':args.output.stat().st_size,'sha256':digest,'files':len(files)+1},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['world-pack','metadata','collision','road','bmw','ui','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--binary',default='nfsmw-rockport-v0.18')
    package(p.parse_args())
