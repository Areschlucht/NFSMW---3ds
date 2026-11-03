#!/usr/bin/env python3
"""Build a static BMW body scene from decoded assets; not vehicle/game logic.

Wheel/driver attachment placement and the generated paint skin are unresolved.
Missing texture references receive explicitly recorded solid-gray placeholders.
"""
import argparse
import json
import math
import struct
import zlib
from pathlib import Path
from PIL import Image
from decode_brakes import decode


def build(geometry,texture_dirs,output,fit_wheel_placement=False):
    models=decode(geometry.read_bytes(),lod='B')
    selected=[m for m in models if not any(s in m['name'] for s in ('DAMAGE0','DRIVER','TIRE','BRAKE_B'))]
    wheel_placement=None
    if fit_wheel_placement:
        from fit_bmw_wheels import fit_wheels
        body=next(m for m in models if m['name']=='BMWM3GTRE46_KIT00_BODY_B')
        tire=next(m for m in models if m['name']=='BMWM3GTRE46_KIT00_FRONT_TIRE_B')
        wheels,wheel_placement=fit_wheels(body,tire)
        selected.extend(wheels)
    for m in selected:
        matrix=m['transform']
        if not all(math.isfinite(x) for x in matrix) or any(abs(matrix[i])>1e-5 for i in (3,7,11)) or abs(matrix[15]-1)>1e-5:
            raise ValueError('Unsupported non-affine object transform')
        low,high=m['stored_bounds']
        if any(min(p[a] for p in m['positions'])<low[a]-0.001 or max(p[a] for p in m['positions'])>high[a]+0.001 for a in range(3)):
            raise ValueError('Decoded positions exceed stored part bounds')
    textures={}
    for directory in texture_dirs:
        for t in json.loads((directory/'manifest.json').read_text()):
            textures[t['hash']]=(t,directory/t['png'])
    used={m['strips'][s]['texture_hash'] for m in selected for s in m['face_strip_indices']}
    output.mkdir(parents=True,exist_ok=True)
    texout=output/'textures';texout.mkdir(exist_ok=True)
    texture_records=[];texture_manifest=[]
    for key in sorted(used):
        missing=key not in textures
        if missing:
            image=Image.new('RGBA',(8,8),(178,182,188,255));name='UNRESOLVED_'+key
        else:
            metadata,path=textures[key];image=Image.open(path).convert('RGBA');name=metadata['name']
        alpha=image.getchannel('A');histogram=alpha.histogram()
        flags=(1 if any(histogram[1:255]) else 0)|(2 if sum(histogram[:255]) else 0)
        image.save(texout/(key+'.png'))
        texture_records.append((int(key,16),image.width,image.height,flags))
        texture_manifest.append(dict(hash=key,name=name,missing=missing,width=image.width,height=image.height,flags=flags))
    lookup={t['hash']:i for i,t in enumerate(texture_manifest)}
    groups={};part_manifest=[];wheel_models=[]
    for m in selected:
        group_id=0
        if 'wheel_pivot' in m:
            wheel_models.append(m);group_id=len(wheel_models)
        part_manifest.append(dict(name=m['name'],triangles=len(m['faces'])))
        for face,uvs,s in zip(m['faces'],m['face_uv_indices'],m['face_strip_indices']):
            # Positions are already baked into the car frame and match its
            # stored bounds. Header matrices are not applied a second time.
            pts=[m['positions'][index] for index in face]
            u=[pts[1][i]-pts[0][i] for i in range(3)];v=[pts[2][i]-pts[0][i] for i in range(3)]
            normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            length=sum(n*n for n in normal)**0.5
            if not length:continue
            normal=[n/length for n in normal]
            # Source car axes are X=length, Y=width, Z=up. Viewer uses Y=up.
            normal=(normal[0],normal[2],-normal[1])
            key=(m['strips'][s]['texture_hash'],group_id);vertices=groups.setdefault(key,[])
            for p,uv in zip(pts,uvs):
                vertices.append([p[0],p[2],-p[1],*normal,*m['texcoords'][uv]])
    all_vertices=[v for vertices in groups.values() for v in vertices]
    low=[min(v[i] for v in all_vertices) for i in range(3)];high=[max(v[i] for v in all_vertices) for i in range(3)]
    extent=max(high[i]-low[i] for i in range(3))
    batches=[];vertices=[];batch_groups=[]
    for key,group in groups.items():
        batches.append((len(vertices),len(group),lookup[key[0]],0));batch_groups.append(key[1])
        for v in group:
            v[:3]=[(v[i]-(low[i]+high[i])*0.5)*2/extent for i in range(3)]
            vertices.append(v)
    payload=b''.join(struct.pack('<4I',*t) for t in texture_records)
    payload+=b''.join(struct.pack('<4I',*b) for b in batches)
    payload+=b''.join(struct.pack('<8f',*v) for v in vertices)
    header=struct.pack('<4s7I',b'NFM1',1,len(vertices),len(batches),len(texture_records),len(payload),zlib.crc32(payload),0)
    (output/'body.nfm').write_bytes(header+payload)
    rig=None
    if wheel_models:
        from wheel_rig import encode_rig
        wheel_records=[dict(pivot=[(m['wheel_pivot'][a]-(low[a]+high[a])/2)*2/extent for a in range(3)],
                            radius=m['wheel_radius'],front=m['wheel_front']) for m in wheel_models]
        rig=encode_rig(wheel_records,batch_groups,zlib.crc32(payload))
        (output/'wheels.nwa').write_bytes(rig)
    manifest=dict(parts=part_manifest,textures=texture_manifest,vertices=len(vertices),triangles=len(vertices)//3,
                  source_bounds=[low,high],unresolved='Generated BMWM3GTRE46_SKIN1, some lights, wheel/driver placement and game materials',
                  scene='Body/interior/windows/lights; provisional wheel groups' if wheel_placement else 'Static body/interior/windows/lights, no wheel or brake instances',
                  wheel_placement=wheel_placement,wheel_animation='wheels.nwa' if rig else None)
    (output/'scene.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Static scene:',len(selected),'parts,',len(vertices)//3,'triangles,',len(used),'texture references,',sum(t['missing'] for t in texture_manifest),'placeholders')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('geometry',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--textures',type=Path,action='append',required=True)
    parser.add_argument('--fit-wheels',action='store_true',help='Add provisional static tire instances fitted to BMW body arches')
    args=parser.parse_args();build(args.geometry,args.textures,args.output,args.fit_wheels)
