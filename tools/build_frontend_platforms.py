#!/usr/bin/env python3
"""Decode original frontend platform scenes with every source model accounted for.

The static candidate explicitly selects BACKDROP_CRIB and BACKDROP_CURRGEN.
Shadow/reflection render passes, emitter proxies and source camera/script
consumers are retained as separate source exports, not silently discarded.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import zlib
from PIL import Image
from car_geometry_diagnostics import chunks
from decode_world import decode_model
from nfs_tpk import parse
from build_menu_icons import FRONT_SHA
from perf_tiling import IMAGE, tiled_rgba8

ARCHIVE_SHA='470b7586d4fe53634c0078acfba716ecd1d1841cef4957a118a18f46f72c83b1'
ENTRIES={
 'CAREER_SAFEHOUSE':(88975360,1528256,'8ed476e87012acb5c3c8b2cd37c76014440c16672b84fb0163afe20a9778aa62'),
 'CAR_LOT':(87947264,1027040,'2ce0ca20ada5c7fb15f2fd2b7591e4edc86f2e54a5b60153afe610f892dd3fe7'),
 'CUSTOMIZATION_SHOP':(90505216,1376320,'975e62e816982a9d2bb873f5dd1e6c199eb315981e2606d138985a6fa0b58799'),
 'CUSTOMIZATION_SHOP_BACKROOM':(91883520,1346928,'87284e600bd0c34b743b26fdeaa334e2c8ab03d215b250c2157203822f1143c8'),
 'PLATFORMCRIB':(93235200,1902880,'9d4ad4fdaea18482ff221d270a92fa406d34bfd254aae912ffbc1324426a34c2'),
}
STATIC_NAMES={'BACKDROP_CRIB','BACKDROP_CURRGEN'}

def digest(raw):return hashlib.sha256(raw).hexdigest()
def source_to_viewer(p):return p[0],p[2],-p[1]

def empty_record(raw,start,end):
    parts={k:(s,e) for k,s,e in chunks(raw,start+8,end)}
    hs,he=parts[0x134011];h=(hs+23)&~15
    name=raw[h+160:he].split(b'\0',1)[0].decode('ascii')
    gs,ge=parts[0x80134100];leaves={k:(s,e) for k,s,e in chunks(raw,gs+8,ge)}
    ms,me=leaves[0x134800];meta=(ms+23)&~15
    fmt,count=struct.unpack_from('>H2xH',raw,meta);size=struct.unpack_from('>I',raw,meta+8)[0]
    if fmt!=22 or count or size or any(raw[meta+8:me]):raise ValueError('Unresolved nonempty model: '+name)
    return {'name':name,'kind':'explicitly empty geometry record','source_offset':start,
            'source_bytes':end-start,'source_sha256':digest(raw[start:end]),'declared_descriptors':count}

def native_scene(models,textures,output):
    keys=sorted({f['texture'] for m in models for f in m['faces']});missing=set(keys)-textures.keys()
    if missing:raise ValueError('Missing original textures: '+','.join(sorted(missing)))
    lookup={k:i for i,k in enumerate(keys)};tex_records=[];tex_manifest=[]
    texdir=output/'textures';texdir.mkdir()
    for k in keys:
        t=textures[k];im=Image.frombytes('RGBA',(t['width'],t['height']),t['rgba']);hist=im.getchannel('A').histogram()
        flags=bool(sum(hist[1:255]))|(bool(sum(hist[:255]))<<1)
        if t['blend_mode'] in (1,2):flags|=1
        if t['blend_mode']==2:flags|=4
        im.save(texdir/(k+'.png'));tex_records.append((int(k,16),im.width,im.height,flags))
        tex_manifest.append({'hash':k,'name':t['name'],'width':im.width,'height':im.height,
            'flags':flags,'missing':False,'rgba_sha256':digest(t['rgba']),
            'alpha_test_mode':t['alpha_test_mode'],'blend_mode':t['blend_mode'],'source_bundle':t['source_bundle']})
    vertices=[];batches=[];degenerate=0
    for m in models:
        for f in m['faces']:
            pts=[source_to_viewer(m['positions'][c[0]]) for c in f['corners']]
            a=[pts[1][i]-pts[0][i] for i in range(3)];b=[pts[2][i]-pts[0][i] for i in range(3)]
            normal=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];length=math.sqrt(sum(v*v for v in normal))
            # Coincident coordinates may survive distinct source position indices.
            # Preserve their submitted triangles with a benign unused normal.
            if length<1e-10:normal=[0,1,0];degenerate+=1
            else:normal=[v/length for v in normal]
            texture=lookup[f['texture']]
            if batches and batches[-1][2]==texture:batches[-1][1]+=3
            else:batches.append([len(vertices),3,texture,0])
            for p,c in zip(pts,f['corners']):vertices.append([*p,*normal,*m['texcoords'][c[2]],*m['colors'][c[1]]])
    if not vertices or len(vertices)>200000 or len(batches)>2048 or len(keys)>128:raise ValueError('Scene exceeds native decoder budgets')
    source_bounds=[[min(v[a] for v in vertices) for a in range(3)],[max(v[a] for v in vertices) for a in range(3)]]
    scale=max(abs(v[a]) for v in vertices for a in range(3))
    if not math.isfinite(scale) or scale<=0:raise ValueError('Invalid normalization scale')
    for v in vertices:v[:3]=[x/scale for x in v[:3]]
    payload=b''.join(struct.pack('<4I',*t) for t in tex_records)+b''.join(struct.pack('<4I',*b) for b in batches)+b''.join(struct.pack('<12f',*v) for v in vertices)
    packed=struct.pack('<4s7I',b'NFM1',2,len(vertices),len(batches),len(keys),len(payload),zlib.crc32(payload),0)+payload
    (output/'platform.nfm').write_bytes(packed)
    return {'vertices':len(vertices),'triangles':len(vertices)//3,'batches':len(batches),'textures':tex_manifest,
        'source_to_viewer':'(sourceX,sourceZ,-sourceY)','normalization_origin_viewer':[0,0,0],
        'source_bounds_viewer':source_bounds,
        'normalization_scale_world':scale,'restore_viewer_position':'NFM.position * normalization_scale_world',
        'source_header_matrices_applied':False,'source_vertex_colors_preserved':True,
        'normals':'new flat geometric normals; original world geometry has no normal stream',
        'coordinate_degenerate_triangles_preserved':degenerate,'nfm_sha256':digest(packed)}

def build(archive,front,output,selected):
    with archive.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=ARCHIVE_SHA:raise ValueError('Unexpected ZZDATA1 source')
    art=front.read_bytes()
    if digest(art)!=FRONT_SHA:raise ValueError('Unexpected frontend source')
    shared={t['hash']:dict(t,source_bundle='FRONTEND-FRONTB.BUN') for t in parse(art)}
    if output.exists():raise ValueError('Use a new output directory')
    output.mkdir(parents=True);summaries=[]
    with archive.open('rb') as f:
        for name in selected:
            offset,size,expected=ENTRIES[name];f.seek(offset);raw=f.read(size)
            if len(raw)!=size or digest(raw)!=expected:raise ValueError('Platform source differs: '+name)
            dest=output/name;dest.mkdir();models=[];empty=[]
            for kind,start,end in chunks(raw,0,len(raw)):
                if kind!=0x80134000:continue
                for k,a,b in chunks(raw,start+8,end):
                    if k!=0x80134010:continue
                    try:m=decode_model(raw,a+8,b,allow_triangle_statistic_mismatch=True)
                    except ValueError:empty.append(empty_record(raw,a,b))
                    else:m.update(source_offset=a,source_bytes=b-a,source_sha256=digest(raw[a:b]));models.append(m)
            if not models:raise ValueError('No source geometry')
            static=[m for m in models if m['name'] in STATIC_NAMES]
            if {m['name'] for m in static}!=STATIC_NAMES:raise ValueError('Static candidate models missing')
            textures=dict(shared);textures.update({t['hash']:dict(t,source_bundle=name+'.BIN') for t in parse(raw)})
            native=native_scene(static,textures,dest)
            with gzip.GzipFile(filename=str(dest/'all-source-models.json.gz'),mode='wb',mtime=0) as g:g.write(json.dumps({'models':models,'empty_models':empty},separators=(',',':')).encode())
            summary={'platform':name,'source_archive':'ZZDATA1.BIN','source_offset':offset,'source_bytes':size,'source_sha256':expected,
                'source_models':len(models)+len(empty),'decoded_models':len(models),'source_triangles':sum(len(m['faces']) for m in models),
                'static_candidate_names':[m['name'] for m in static],'nonstatic_models_preserved':[m['name'] for m in models if m not in static],
                'empty_models':empty,'model_header_statistics':[{'name':m['name'],'declared':m['declared_triangles'],'emitted':len(m['faces'])} for m in models],
                'limits':['Static-model selection is an explicit 3DS candidate, not recovered original pass admission',
                    'All decoded source meshes are retained in all-source-models.json.gz; no unsupported nonempty mesh is silently omitted',
                    'Shadow-map/reflection passes, particle emitters, fans and scene scripts are not implemented by NFM export',
                    'Positions retain source geometry; header transforms await original frontend consumer validation',
                    'No replacement textures, guessed car placement, native menu camera constants or SDK build introduced'],**native}
            (dest/'scene.json').write_text(json.dumps(summary,indent=2)+'\n');summaries.append(summary)
    compact={'source_archive_sha256':ARCHIVE_SHA,'source_frontend_sha256':FRONT_SHA,'platforms':[{'name':s['platform'],'source_models':s['source_models'],'decoded_models':s['decoded_models'],'source_triangles':s['source_triangles'],'static_triangles':s['triangles'],'textures':len(s['textures']),'normalization_scale_world':s['normalization_scale_world'],'nfm_sha256':s['nfm_sha256']} for s in summaries]}
    (output/'summary.json').write_text(json.dumps(compact,indent=2)+'\n');return compact

def convert_native(output):
    summary=json.loads((output/'summary.json').read_text());env=os.environ.copy()
    for k in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'):env.pop(k,None)
    command=['docker','--host=unix:///var/run/docker.sock']
    subprocess.run(command+['info','--format','{{.ServerVersion}}'],env=env,check=True,stdout=subprocess.DEVNULL)
    # Inputs have only generated uppercase platform and hexadecimal texture names.
    script='set -e; for p in /platforms/*/textures/*.png; do tex3ds -f rgba8 -z none -r -o "${p%.png}.raw" "$p"; tex3ds -f rgba8 -z none -o "${p%.png}.t3x" "$p"; done'
    subprocess.run(command+['run','--rm','--network','none','--user',f'{os.getuid()}:{os.getgid()}',
        '--mount',f'type=bind,src={output.resolve()},dst=/platforms',IMAGE,'bash','-lc',script],env=env,check=True,stdout=subprocess.DEVNULL)
    results=[]
    for platform in summary['platforms']:
        name=platform['name'];scene=json.loads((output/name/'scene.json').read_text());rows=[]
        for t in scene['textures']:
            key=t['hash'];folder=output/name/'textures';im=Image.open(folder/(key+'.png')).convert('RGBA')
            if digest(im.tobytes())!=t['rgba_sha256']:raise ValueError('Original PNG pixels changed')
            expected=tiled_rgba8(im.tobytes(),im.width,im.height);raw=(folder/(key+'.raw')).read_bytes();native=(folder/(key+'.t3x')).read_bytes()
            if len(raw)!=len(expected)+4 or raw[0] or int.from_bytes(raw[1:4],'little')!=len(expected) or raw[4:]!=expected or not native.endswith(raw):raise ValueError('Native texture mismatch: '+name+'/'+key)
            rows.append({'hash':key,'gpu_bytes':len(expected),'gpu_sha256':digest(expected),'t3x_sha256':digest(native),'source_rgba_sha256':t['rgba_sha256']})
        gpu_bytes=sum(r['gpu_bytes'] for r in rows)
        scene['native_texture_gpu_bytes']=gpu_bytes;scene['native_vertex_gpu_bytes']=scene['vertices']*48
        scene['native_total_gpu_bytes']=gpu_bytes+scene['vertices']*48
        (output/name/'scene.json').write_text(json.dumps(scene,indent=2)+'\n')
        results.append({'platform':name,'textures':len(rows),'gpu_bytes':gpu_bytes,'rows':rows})
    report={'sdk_image':IMAGE,'texture_pixels_compared':True,'alpha_zero_rgb_policy':'Pinned tex3ds canonicalizes RGB to zero when alpha is zero; original PNGs remain unchanged','platforms':results}
    (output/'native-texture-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return {'platforms':len(results),'textures':sum(r['textures'] for r in results),'gpu_bytes_compared':sum(r['gpu_bytes'] for r in results)}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('archive','front','output'):p.add_argument('--'+n,type=Path)
    p.add_argument('--platform',choices=ENTRIES,action='append')
    p.add_argument('--convert-existing',type=Path,help='Convert/verify PNG assets in an already exported private directory using the pinned SDK tex3ds; no application build')
    a=p.parse_args()
    if a.convert_existing:result=convert_native(a.convert_existing)
    else:
        if not all((a.archive,a.front,a.output)):p.error('--archive, --front and --output are required for source export')
        result=build(a.archive,a.front,a.output,a.platform or list(ENTRIES))
    print(json.dumps(result,indent=2))
