#!/usr/bin/env python3
"""Exact WTX RGBA→PICA RGBA8 upload contract against pinned tex3ds output."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import zlib
from PIL import Image
from world_materials import world_rgba

IMAGE='devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5'

def tiled_rgba8(rgba,width,height,*,flip=False,zero_transparent_rgb=True):
    if not (8<=width<=1024 and 8<=height<=1024) or width&(width-1) or height&(height-1) or len(rgba)!=width*height*4:
        raise ValueError('Expected native power-of-two8..1024 RGBA dimensions')
    output=bytearray(len(rgba))
    for y in range(height):
        target_y=height-1-y if flip else y
        for x in range(width):
            # Tile-local target coordinates, preserving row orientation.
            morton=(x&1)|((target_y&1)<<1)|((x&2)<<1)|((target_y&2)<<2)|((x&4)<<2)|((target_y&4)<<3)
            at=(((target_y>>3)*(width>>3)+(x>>3))*64+morton)*4
            source=(y*width+x)*4
            texel=rgba[source:source+4]
            output[at:at+4]=bytes(4) if zero_transparent_rgb and not texel[3] else texel[::-1]
    return bytes(output)

def wtx(path):
    data=path.read_bytes()
    if len(data)<128 or data[:4]!=b'WTX1':raise ValueError('Invalid WTX header')
    version,total,key,width,height,offset,size,tier,alpha,blend=struct.unpack_from('<10I',data,4)
    crc=zlib.crc32(data[:56]);crc=zlib.crc32(bytes(4),crc);crc=zlib.crc32(data[60:],crc)
    if version!=1 or total!=len(data) or offset!=128 or size!=width*height*4 or total!=128+size or struct.unpack_from('<I',data,56)[0]!=crc:
        raise ValueError('Invalid WTX bounds/CRC')
    rgba,policy=world_rgba(dict(rgba=data[128:],alpha_test_mode=alpha,blend_mode=blend))
    return dict(width=width,height=height,rgba=rgba,alpha=alpha,blend=blend,policy=policy,source_sha256=hashlib.sha256(data).hexdigest(),source_name=path.name)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--textures',type=Path,default=Path('/workspace/port-research/world-streaming/scene-native/textures'));parser.add_argument('--output',type=Path,default=Path('/workspace/port-research/hardware-optimization/tiling'));parser.add_argument('--reuse-reference',action='store_true');args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    samples={};sizes=set();policies=Counter();total=0
    for path in sorted(args.textures.glob('*.wtx')):
        with path.open('rb') as stream:header=stream.read(128)
        width,height=struct.unpack_from('<2I',header,16);alpha,blend=struct.unpack_from('<2I',header,36);sizes.add((width,height));policies[alpha,blend]+=1;total+=1
        samples.setdefault((alpha,blend,width!=height),path)
    cases=[]
    for width,height in sorted(sizes|{(8,8),(16,16),(32,32),(128,128),(8,16),(16,8)}):
        rgba=bytes(component for y in range(height) for x in range(width) for component in
                   ((x*37+y*5)&255,(x*11+y*71)&255,(x*19+y*23+17)&255,(x*29+y*31)&255))
        cases.append(dict(name=f'synthetic-{width}x{height}',width=width,height=height,rgba=rgba,policy='Synthetic varied source alpha, including zero with nonzero RGB'))
    for path in samples.values():
        info=wtx(path);info['name']='original-'+path.stem;cases.append(info)
    for case in cases:
        Image.frombytes('RGBA',(case['width'],case['height']),case['rgba']).save(args.output/(case['name']+'.png'))
    manifest=args.output/'cases.json';manifest.write_text(json.dumps([dict(name=c['name']) for c in cases]))
    env=os.environ.copy()
    for key in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'):env.pop(key,None)
    # File names are generated locally and source hash/name only; Docker receives
    # a task-owned directory and cannot mutate shared renderer source/state.
    command='for png in /audit/synthetic-*.png /audit/original-*.png; do tex3ds -f rgba8 -z none -r -o "${png%.png}.raw" "$png" || exit; tex3ds -f rgba8 -z none -o "${png%.png}.t3x" "$png" || exit; done'
    if not args.reuse_reference:
        subprocess.run(['docker','--host=unix:///var/run/docker.sock','run','--rm','--network','none','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,src={args.output.resolve()},dst=/audit',IMAGE,'bash','-lc',command],env=env,check=True)
    report=dict(sdk_image=IMAGE,texture_inventory_count=total,native_dimensions=sorted(sizes),opacity_counts={f'{a}:{b}':n for (a,b),n in policies.items()},cases=[],contract='Source top row stays first; ABGR bytes;8x8 Mortontiles row-major; zeroRGB when effective alpha0 for tex3ds parity; no upload flip; fake compression header stripped; existing UV1-v retained.')
    for case in cases:
        raw=(args.output/(case['name']+'.raw')).read_bytes();t3x=(args.output/(case['name']+'.t3x')).read_bytes()
        if raw[0]!=0 or int.from_bytes(raw[1:4],'little')!=len(raw)-4:raise ValueError('Unexpected raw uncompressed header')
        gpu=raw[4:];expected=tiled_rgba8(case['rgba'],case['width'],case['height'])
        flipped=tiled_rgba8(case['rgba'],case['width'],case['height'],flip=True)
        direct=tiled_rgba8(case['rgba'],case['width'],case['height'],zero_transparent_rgb=False)
        row={k:v for k,v in case.items() if k!='rgba'};row.update(gpu_bytes=len(gpu),gpu_sha256=hashlib.sha256(gpu).hexdigest(),manual_exact=expected==gpu,vertical_flip_exact=flipped==gpu,t3x_payload_exact=t3x.endswith(raw),t3x_metadata_bytes=len(t3x)-len(raw),changed_bytes=sum(a!=b for a,b in zip(expected,gpu)),unmodified_transparent_rgb_changed_bytes=sum(a!=b for a,b in zip(direct,gpu)))
        if len(gpu)!=len(expected) or expected!=gpu or not t3x.endswith(raw):raise ValueError('Byteidentityfailure:'+case['name']+':'+str(row))
        report['cases'].append(row)
    report['all_exact']=all(c['manual_exact'] and c['t3x_payload_exact'] for c in report['cases']);report['source_file_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (args.output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(cases),native_sizes=len(sizes),original_samples=len(samples),all_exact=report['all_exact'],gpu_bytes_compared=sum(c['gpu_bytes'] for c in report['cases']),metadata_sizes=sorted({c['t3x_metadata_bytes'] for c in report['cases']})),indent=2))

if __name__=='__main__':main()
