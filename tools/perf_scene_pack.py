#!/usr/bin/env python3
"""Deterministic optional archive of immutable WSM/WSI/WTX payload bytes.

Manifest-selected assets only; one source file streamed at a time. The archive
retains disk payloads exactly and makes no GPU allocation/readiness claim.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import zlib

HEADER=128
ENTRY=64
MAX_ENTRIES=32768
MAX_BYTES=0x7fffffff

def sha(data):return hashlib.sha256(data).hexdigest()
def align(value):return (value+127)&~127

def pack(scene,output,report=None):
    scene=Path(scene).resolve();output=Path(output);report=Path(report) if report else output.with_suffix(output.suffix+'.json')
    if output.exists() or report.exists():raise FileExistsError('Archive/report already exists; choose a new output')
    manifest_path=scene/'manifest.json';manifest_raw=manifest_path.read_bytes();manifest=json.loads(manifest_raw)
    source=bytes.fromhex(manifest['source_sha256'])
    if len(source)!=32:raise ValueError('Expected original source SHA256')
    assets=[]
    patterns={1:r'models/([0-9a-f]{8})\.wsm',2:r'sections/([0-9]+)\.wsi',3:r'textures/([0-9a-f]{8})-([0-9a-f]{64})\.wtx'}
    for kind,collection in ((1,manifest['models'].values()),(2,manifest['sections']),(3,manifest['textures'].values())):
        for row in collection:
            path=row['path'];match=re.fullmatch(patterns[kind],path)
            if not match:raise ValueError('Unexpected asset path:'+path)
            identifier=int(match[1],10 if kind==2 else 16)
            identity=bytes.fromhex(match[2]) if kind==3 else bytes(32)
            if not 0<=identifier<=0xffffffff:raise ValueError('Identifier exceeds uint32')
            file=(scene/path).resolve()
            if not file.is_relative_to(scene):raise ValueError('Asset escapes selected scene')
            size=file.stat().st_size
            if size!=row['bytes'] or size<=0:raise ValueError('Manifest asset length mismatch:'+path)
            assets.append(dict(kind=kind,id=identifier,identity=identity,path=path,file=file,bytes=size,sha256=row['sha256']))
    assets.sort(key=lambda r:(r['kind'],r['id'],r['identity']))
    if not 0<len(assets)<=MAX_ENTRIES:raise ValueError('Index count exceeds bounded reader')
    previous=None;position=align(HEADER+ENTRY*len(assets))
    for asset in assets:
        key=(asset['kind'],asset['id'],asset['identity'])
        if key==previous:raise ValueError('Duplicate archive key')
        previous=key;position=align(position);asset['offset']=position;position+=asset['bytes']
    if position>MAX_BYTES:raise ValueError('Archive exceeds signed32 fseek limit')
    output.parent.mkdir(parents=True,exist_ok=True);created=False
    try:
        with output.open('xb') as target:
            created=True;target.write(bytes(align(HEADER+ENTRY*len(assets))))
            for asset in assets:
                target.write(bytes(asset['offset']-target.tell()));crc=0;digest=hashlib.sha256();copied=0
                with asset['file'].open('rb') as source_file:
                    while block:=source_file.read(1024*1024):
                        copied+=len(block)
                        if copied>asset['bytes']:raise ValueError('Source grew during packing')
                        target.write(block);crc=zlib.crc32(block,crc);digest.update(block)
                if copied!=asset['bytes'] or digest.hexdigest()!=asset['sha256']:raise ValueError('Source SHA/size differs from manifest:'+asset['path'])
                asset['crc32']=crc
            assert target.tell()==position
            index=b''.join(struct.pack('<II32sIII12x',a['kind'],a['id'],a['identity'],a['offset'],a['bytes'],a['crc32']) for a in assets)
            header=bytearray(HEADER);header[:4]=b'MWP1'
            struct.pack_into('<7I',header,4,1,HEADER,ENTRY,len(assets),zlib.crc32(index),align(HEADER+len(index)),position)
            header[32:64]=source;header[64:96]=hashlib.sha256(manifest_raw).digest();struct.pack_into('<I',header,96,zlib.crc32(header))
            target.seek(0);target.write(header);target.write(index)
            if manifest_path.read_bytes()!=manifest_raw:raise ValueError('Scene manifest changed during packing; retry a stable export')
        with output.open('rb') as archive_file:archive_sha=hashlib.file_digest(archive_file,'sha256').hexdigest()
        result=dict(schema=1,archive=str(output.resolve()),archive_bytes=position,archive_sha256=archive_sha,
                    source_sha256=manifest['source_sha256'],scene_manifest_sha256=sha(manifest_raw),
                    entries=len(assets),index_normal_heap_bytes=len(index),payload_bytes=sum(a['bytes'] for a in assets),
                    alignment_padding_bytes=position-HEADER-len(index)-sum(a['bytes'] for a in assets),
                    kind_counts=dict(Counter(str(a['kind']) for a in assets)),max_asset_bytes=max(a['bytes'] for a in assets),
                    gpu_allocation_claim=False,
                    assets=[{k:v for k,v in a.items() if k!='file' and k!='identity'}|{'identity':a['identity'].hex()} for a in assets])
        with report.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    except BaseException:
        if created:output.unlink(missing_ok=True)
        raise
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scene',type=Path);p.add_argument('output',type=Path);p.add_argument('--report',type=Path);a=p.parse_args();r=pack(a.scene,a.output,a.report);print(json.dumps({k:v for k,v in r.items() if k!='assets'},indent=2))
