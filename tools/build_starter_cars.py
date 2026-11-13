#!/usr/bin/env python3
"""Convert actual starter-candidate KIT00 meshes to native NFM/NWA/Tex3DS.

The source car models, source corner normals/UVs and source texture pixels are
preserved. The wheel mounting and flat stock-paint preview are documented native
adapters, not a recovered complete original preset/material renderer.
"""
import argparse
from collections import OrderedDict
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
from car_geometry_expanded import decode_part
from material_recovery_carparts import CarParts
from material_recovery_vehicle import light_targets, texture_hash
from nfs_huff_reference import decode as huff_decode
from nfs_tpk import parse as texture_parse
from perf_tiling import IMAGE, tiled_rgba8
from vehicle_attributes import VehicleAttributes
from wheel_rig import encode_rig, inspect_rig

ATTR_SHA='5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c'
PAINT_SOURCE_SHA='da02353de70dea3a8a51d6231e4efde15ab8c5c72eed6119a49bc9dad20b770b'
CARS=('COBALTSS','GTI','IS300','PUNTO')
DISPLAY={'COBALTSS':'Chevrolet Cobalt SS','GTI':'Volkswagen Golf GTI','IS300':'Lexus IS 300','PUNTO':'Fiat Punto'}
FE_KEYS={'COBALTSS':0x5a784095,'GTI':0x79054b53,'IS300':0x5bff2fb0,'PUNTO':0xa6ee7a11}


def sha(data):return hashlib.sha256(data).hexdigest()


def existing_pixels(directories):
    result={}
    for directory in directories:
        for record in json.loads((directory/'manifest.json').read_text()):
            image=Image.open(directory/record['png']).convert('RGBA')
            if image.size!=(record['width'],record['height']) or sha(image.tobytes())!=record['rgba_sha256']:
                raise ValueError('Decoded source texture changed')
            key=record['hash']
            if key in result and result[key][1].tobytes()!=image.tobytes():
                raise ValueError('Ambiguous source texture '+key)
            result[key]=(dict(record,manifest_sha256=sha((directory/'manifest.json').read_bytes())),image)
    return result


def geometry_parts(exports,candidates,car):
    manifest=json.loads((exports/'manifest.json').read_text())
    matches=[r for r in manifest['records'] if r['candidate_name']==f'CARS\\{car}\\GEOMETRY.BIN']
    if len(matches)!=1 or matches[0]['rejected']:raise ValueError('Missing or incomplete geometry package')
    record=matches[0];directory=exports/record['body_obj'].split('/')[0]
    entries=json.loads((candidates/'manifest.json').read_text())['entries']
    sources=[e for e in entries if e['candidate_name']==record['candidate_name']]
    if len(sources)!=1:raise ValueError('Ambiguous original geometry source')
    raw=(candidates/sources[0]['file']).read_bytes()
    if sha(raw)!=record['source_sha256'] or sha(raw)!=sources[0]['sha256']:raise ValueError('Geometry source differs')
    models=[]
    for path in sorted(directory.glob('*.mesh.json.gz')):
        row=json.loads(gzip.decompress(path.read_bytes()))
        if row['name']==f"{car}_BASE_{record['selected_offline_lod']}" or '_KIT00_' in row['name'] and 'DAMAGE' not in row['name']:
            class PacketCache:
                def __init__(self):self.index=0
                def verify(self,descriptor,packet,widths):
                    cached=row['descriptor_parity_checks'][self.index];self.index+=1
                    if sha(packet)!=cached['source_sha256']:raise ValueError('Original verified descriptor packet changed')
                    return cached
            cache=PacketCache();decoded=decode_part(raw,row['source_model_offset'],row['source_model_offset']+row['source_model_bytes'],cache)
            if cache.index!=len(row['descriptor_parity_checks']) or any(json.dumps(decoded[k],sort_keys=True)!=json.dumps(row[k],sort_keys=True) for k in decoded):raise ValueError('Expanded mesh differs from independently reloaded original source')
            row['mesh_export_sha256']=sha(path.read_bytes());models.append(row)
    if not models or not any('_BODY_' in m['name'] for m in models):raise ValueError('No intact stock body')
    return record,models


def original_texture_bank(candidates,car,shared):
    manifest=json.loads((candidates/'manifest.json').read_text())
    matches=[r for r in manifest['entries'] if r['candidate_name']==f'CARS\\{car}\\TEXTURES.BIN']
    if len(matches)!=1:raise ValueError('Missing or ambiguous car textures')
    record=matches[0];raw=(candidates/record['file']).read_bytes()
    if sha(raw)!=record['sha256']:raise ValueError('Car texture source differs')
    result=dict(shared)
    for t in texture_parse(raw,huff_decode):
        image=Image.frombytes('RGBA',(t['width'],t['height']),t.pop('rgba'))
        if t['hash'] in result and result[t['hash']][1].tobytes()!=image.tobytes():raise ValueError('Ambiguous local/source texture')
        result[t['hash']]=(dict(t,source_sha256=record['sha256'],rgba_sha256=sha(image.tobytes())),image)
    return record,result


def texture_binding(car,key,bank,paint):
    if key in bank:return bank[key],None
    lights={f'{texture_hash(n):08x}':f'{k:08x}' for n,k in light_targets(car,window_front_target=texture_hash('WINDOW_FRONT')).items()}
    windows={f'{texture_hash(n):08x}' for n in ('WINDOW_LEFT_FRONT','WINDOW_RIGHT_FRONT','WINDOW_LEFT_REAR','WINDOW_RIGHT_REAR','WINDOW_REAR','WINDOW_BACK')}
    if key in lights:
        target=lights[key]
        if target not in bank:raise ValueError('Original lamp target absent '+target)
        return bank[target],{'adapter':'original intact default-prefix light selector; flags1608/160C=0','target_hash':target}
    if key in windows:
        target=f'{texture_hash("WINDOW_FRONT"):08x}'
        return bank[target],{'adapter':'native common untinted window binding; per-window tint consumer not recovered','target_hash':target}
    if key in {f'{texture_hash(car+"_SKIN1"):08x}',f'{texture_hash(car+"_SKIN2"):08x}'}:
        image=Image.new('RGBA',(8,8),tuple(paint['rgba']))
        return ({'name':paint['name']+'_DIFFUSE_ADAPTER','hash':key,'rgba_sha256':sha(image.tobytes())},image),{'adapter':'native constant original-palette diffuse; no generated paint/reflection material','paint':paint}
    raise ValueError('Unresolved texture; no placeholder emitted '+car+'/'+key)


def build_car(args,car,db,shared,paint):
    source,models=geometry_parts(args.meshes,args.candidates,car);texsource,bank=original_texture_bank(args.candidates,car,shared)
    ecar=db.find('ecar',car.lower());offsets=db.field_value(ecar,'TireOffsets');mounts=offsets['value']['values']
    if len(mounts)!=4:raise ValueError('Four original art mounts required')
    static=[m for m in models if not any(s in m['name'] for s in ('_TIRE_','_BRAKE_'))]
    tire=[m for m in models if '_FRONT_TIRE_' in m['name']]
    if len(tire)!=1:raise ValueError('One source front tire mesh required')
    groups=OrderedDict();parts=[]
    def append(model,wheel=0,mount=None):
        side=1 if mount and mount[1]>0 else -1
        parts.append({'name':model['name'],'wheel_group':wheel,'source_model_offset':model['source_model_offset'],'mesh_export_sha256':model['mesh_export_sha256']})
        for triangle in model['triangles']:
            corners=triangle['corners'];strip=model['strips'][triangle['strip']]
            positions=[model['positions'][c[0]] for c in corners]
            a=[positions[1][i]-positions[0][i] for i in range(3)];b=[positions[2][i]-positions[0][i] for i in range(3)]
            if not sum(v*v for v in (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])):continue
            vertices=groups.setdefault((strip['texture_hash'],wheel),[])
            for p,c in zip(positions,corners):
                n=model['normals_s8_64'][c[1]];uv=model['uv'][c[4]]
                if mount:p=(mount[0]-side*p[0],mount[1]-side*p[1],mount[2]+p[2]);n=(-side*n[0],-side*n[1],n[2])
                vertices.append([p[0],p[2],-p[1],n[0],n[2],-n[1],*uv,1.,1.,1.,1.])
    for m in static:append(m)
    for i,mount in enumerate(mounts):
        append(tire[0],i+1,mount)
        brakes=[m for m in models if ('_FRONT_BRAKE_' if i<2 else '_REAR_BRAKE_') in m['name']]
        if len(brakes)>1:raise ValueError('Ambiguous brake mesh')
        if brakes:append(brakes[0],i+1,mount)
    vertices=[v for g in groups.values() for v in g]
    low=[min(v[a] for v in vertices) for a in range(3)];high=[max(v[a] for v in vertices) for a in range(3)]
    half=max(high[a]-low[a] for a in range(3))/2;center=[(low[a]+high[a])/2 for a in range(3)]
    if not 1<half<4:raise ValueError('Unsupported native car extent')
    out=args.output/car;textures=out/'textures';textures.mkdir(parents=True)
    keys=sorted({k[0] for k in groups});texture_records=[];texmanifest=[]
    for key in keys:
        (record,image),binding=texture_binding(car,key,bank,paint)
        if image.width<8 or image.height<8:raise ValueError('Source texture smaller than native minimum')
        hist=image.getchannel('A').histogram();flags=(1 if any(hist[1:255]) else 0)|(2 if sum(hist[:255]) else 0)
        image.save(textures/(key+'.png'));texture_records.append((int(key,16),image.width,image.height,flags))
        texmanifest.append({'hash':key,'name':record['name'],'missing':False,'width':image.width,'height':image.height,'flags':flags,'rgba_sha256':sha(image.tobytes()),'source':record,'binding':binding})
    lookup={k:i for i,k in enumerate(keys)};batches=[];batch_groups=[];flat=[]
    for (key,group),rows in groups.items():
        batches.append((len(flat),len(rows),lookup[key],0));batch_groups.append(group)
        for row in rows:row[:3]=[(row[a]-center[a])/half for a in range(3)];flat.append(row)
    payload=b''.join(struct.pack('<4I',*r) for r in texture_records+batches)+b''.join(struct.pack('<12f',*v) for v in flat)
    body=struct.pack('<4s7I',b'NFM1',2,len(flat),len(batches),len(keys),len(payload),zlib.crc32(payload),0)+payload
    (out/'body.nfm').write_bytes(body)
    rig=encode_rig([{'pivot':[(m[0]-center[0])/half,(m[2]-center[1])/half,(-m[1]-center[2])/half],'radius':m[3],'front':i<2} for i,m in enumerate(mounts)],batch_groups,zlib.crc32(payload))
    (out/'wheels.nwa').write_bytes(rig);inspect_rig(rig,len(batches),zlib.crc32(payload))
    result={'id':car,'display_name':DISPLAY.get(car,car),'frontend_collection_key':f'{FE_KEYS.get(car,0):08x}','ecar_collection_key':f'{ecar["key"]:08x}','half_extent':half,'source_bounds_viewer':[low,high],'center_viewer':center,'vertices':len(flat),'triangles':len(flat)//3,'parts':parts,'textures':texmanifest,'body_sha256':sha(body),'wheel_rig_sha256':sha(rig),'source_geometry':source,'source_textures':texsource,'wheel_mounts':offsets,'scene':'native intact KIT00 source mesh adapter','limitations':['Stock part choice follows concrete KIT00 geometry names, not a recovered saved/purchase preset','Exact source TireOffsets are used; complete original hub/body-height/FE compression transform is not established','Original front tire geometry is instanced four times; original rim/kit/tire scaling producer remains separate','Constant original white palette paint is an explicit native preview selection, not original default purchase color','Original source normals/UVs preserved; full paint, tint, reflection, transparency and lamp state producers remain incomplete']}
    (out/'scene.json').write_text(json.dumps(result,indent=2)+'\n');return result


def native_textures(output):
    env=os.environ.copy()
    for k in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'):env.pop(k,None)
    docker=['docker','--host=unix:///var/run/docker.sock']
    subprocess.run(docker+['info','--format','{{.ServerVersion}}'],check=True,env=env,stdout=subprocess.DEVNULL)
    subprocess.run(docker+['run','--rm','--network','none','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,src={output.resolve()},dst=/cars',IMAGE,'bash','-lc','set -e; for p in /cars/*/textures/*.png; do tex3ds -f rgba8 -z none -r -o "${p%.png}.raw" "$p"; tex3ds -f rgba8 -z none -o "${p%.png}.t3x" "$p"; done'],check=True,env=env)
    total=0
    for png in output.glob('*/textures/*.png'):
        image=Image.open(png).convert('RGBA');expected=tiled_rgba8(image.tobytes(),image.width,image.height)
        raw=png.with_suffix('.raw').read_bytes();t3x=png.with_suffix('.t3x').read_bytes()
        if len(raw)!=len(expected)+4 or raw[0] or int.from_bytes(raw[1:4],'little')!=len(expected) or raw[4:]!=expected or not t3x.endswith(raw):raise ValueError('Tex3DS source-pixel comparison failed '+str(png))
        total+=1
    return total


def pack_catalog(directory,catalog,carparts_sha):
    records=[]
    for car in sorted(catalog['cars'],key=lambda r:r['id']):
        scene=json.loads((directory/car['id']/'scene.json').read_text())
        body=(directory/car['id']/'body.nfm').read_bytes();rig=(directory/car['id']/'wheels.nwa').read_bytes()
        if sha(body)!=car['body_sha256'] or sha(rig)!=car['wheel_rig_sha256']:raise ValueError('Catalog asset changed')
        name=car['id'].encode('ascii');display=car['display_name'].encode('ascii')
        if len(name)>31 or len(display)>63:raise ValueError('Catalog text exceeds native bound')
        records.append(struct.pack('<4IfI32s64s32s8x',int(car['frontend_collection_key'],16),int(car['ecar_collection_key'],16),struct.unpack_from('<I',body,24)[0],struct.unpack_from('<I',rig,20)[0],car['half_extent'],0,name,display,bytes.fromhex(scene['source_geometry']['source_sha256'])))
    data=bytearray(96)+b''.join(records)
    struct.pack_into('<4s7I',data,0,b'NVC1',1,len(data),0,len(records),96,160,0)
    data[32:64]=bytes.fromhex(ATTR_SHA);data[64:96]=bytes.fromhex(carparts_sha);struct.pack_into('<I',data,12,zlib.crc32(data[16:]))
    path=directory/'catalog.nvc'
    if path.exists() and path.read_bytes()!=data:raise ValueError('Existing native catalog differs')
    if not path.exists():path.write_bytes(data)
    return {'bytes':len(data),'sha256':sha(data)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('meshes','candidates','attributes','carparts','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--shared-textures',type=Path,action='append',required=True);p.add_argument('--native-textures',action='store_true');p.add_argument('--car',choices=(*CARS,'TRAFHA'),action='append')
    a=p.parse_args()
    if a.output.exists():raise ValueError('Use a new output directory; no originals overwritten')
    raw=a.attributes.read_bytes()
    if sha(raw)!=ATTR_SHA:raise ValueError('Expected pinned original attributes')
    db=VehicleAttributes(raw);cp=CarParts(a.carparts.read_bytes())
    if cp.sha256!=PAINT_SOURCE_SHA:raise ValueError('Expected pinned original carpart source')
    part=cp.part(texture_hash('GLOSS_L1_COLOR01'))
    paint={'name':part['name'],'key':part['key'],'source_sha256':cp.sha256,'rgba':[cp.value(part,k) for k in ('RED','GREEN','BLUE')]+[255],'gloss':cp.value(part,'GLOSS')}
    shared=existing_pixels(a.shared_textures);records=[build_car(a,c,db,shared,paint) for c in (a.car or CARS)]
    count=native_textures(a.output) if a.native_textures else 0
    summary={'schema':1,'attributes_sha256':ATTR_SHA,'cars':[{k:r[k] for k in ('id','display_name','frontend_collection_key','ecar_collection_key','half_extent','vertices','triangles','body_sha256','wheel_rig_sha256','limitations')} for r in records],'source_rgba_to_native_textures_compared':count,'textures_native':bool(count)}
    summary['native_catalog']=pack_catalog(a.output,summary,cp.sha256)
    (a.output/'catalog.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
