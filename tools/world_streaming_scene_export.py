"""Bounded original world model/texture/instance asset export.

One original section is read at a time. Models retain original local coordinates,
ordered triangles, matrix metadata, descriptor/material bytes and raw night alpha.
No LOD selection or model-header transform is baked in. Texture quality is explicit.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import mmap
from pathlib import Path
import struct
import zlib

from decode_world import decode_model
from nfs_rockport import chunks
from nfs_tpk import parse as parse_textures
from world_instances import read_instances


def align(value,unit=4):
    return (value+unit-1)&-unit


def asset_crc(data,field):
    value=zlib.crc32(data[:field])
    value=zlib.crc32(bytes(4),value)
    return zlib.crc32(data[field+4:],value)


def model_asset(data,start,end,source,guard):
    model=decode_model(data,start,end,allow_triangle_statistic_mismatch=True)
    leaves={kind:(start+a,start+b) for kind,a,b in chunks(data[start:end])}
    hs,he=leaves[0x134011];header=align(hs,16)
    ts,te=leaves[0x134012]
    a,b=leaves[0x80134100]
    geometry={kind:(a+c,a+d) for kind,c,d in chunks(data[a:b])}
    meta=align(geometry[0x134800][0],16)
    table=align(geometry[0x134801][0],16)
    blob=align(geometry[0x134802][0],32)
    count=struct.unpack_from('>H',data,meta+4)[0]
    _,_,_,colors,uvs=struct.unpack_from('>5I',data,meta+8)
    vertices=bytearray();night=bytearray();indices=[];unique={};batches=[];face_cursor=0
    position_format=None
    for index in range(count):
        at=table+index*16
        descriptor=data[at:at+16]
        offset=struct.unpack_from('>I',descriptor)[0]
        n,tex,flags,fmt=descriptor[8],descriptor[10],descriptor[12],descriptor[13]
        position_format=fmt
        widths=[2 if flags&bit else 1 for bit in (16,4,2)]
        cursor=blob+offset+(3 if flags&128 else 0)
        corners=[]
        for _ in range(n):
            corner=[]
            for width in widths:
                corner.append(int.from_bytes(data[cursor:cursor+width],'big'));cursor+=width
            corners.append(corner)
        triangles=sum(len({corners[j][0],corners[j+1][0],corners[j+2][0]})==3 for j in range(n-2))
        first=len(indices)
        for face in model['faces'][face_cursor:face_cursor+triangles]:
            for corner in face['corners']:
                key=tuple(corner)
                if key not in unique:
                    if len(unique)>=65535:
                        raise ValueError('Composite vertex count exceeds the explicit uint16 model budget')
                    unique[key]=len(unique)
                    position=model['positions'][corner[0]]
                    raw_uv=struct.unpack_from('>2h',data,blob+uvs+corner[2]*4)
                    rgba=data[blob+colors+corner[1]*4:blob+colors+(corner[1]+1)*4]
                    vertices.extend(struct.pack('<3f2h4B',*position,*raw_uv,*rgba[:3],255))
                    night.append(rgba[3])
                indices.append(unique[key])
        face_cursor+=triangles
        material=data[ts+tex*8:ts+(tex+1)*8]
        batches.append(struct.pack('<III',first,len(indices)-first,struct.unpack_from('<I',material)[0])+descriptor+material)
    if face_cursor!=len(model['faces']) or not indices:
        raise ValueError('No consumed triangle geometry or descriptor-face mismatch')
    output=bytearray(256)
    vo=len(output);output.extend(vertices)
    io=len(output);output.extend(struct.pack(f'<{len(indices)}H',*indices))
    output.extend(bytes(align(len(output))-len(output)))
    bo=len(output);output.extend(b''.join(batches))
    no=len(output);output.extend(night)
    output.extend(bytes(align(len(output))-len(output)))
    ho=len(output);output.extend(data[header:header+160])
    output[:4]=b'WSM1'
    struct.pack_into('<15I',output,4,1,len(output),int(model['hash'],16),len(unique),len(indices),count,
                     model['declared_triangles'],model['emitted_position_index_triangles'],vo,io,bo,no,
                     position_format,0,0)
    struct.pack_into('<6f',output,64,*model['bounds'][0],*model['bounds'][1])
    struct.pack_into('<16f',output,88,*model['matrix'])
    output[152:184]=bytes.fromhex(source['raw_sha256'])
    output[184:216]=bytes.fromhex(guard.split(':')[-1])
    struct.pack_into('<8I',output,216,source['section'],source['offset'],source['bytes'],
                     len(unique)*36+len(indices)*2,len(output),0,ho,160)
    struct.pack_into('<I',output,56,asset_crc(output,56))
    return bytes(output),dict(hash=model['hash'],name=model['name'],vertices=len(unique),
                              indices=len(indices),batches=count,linear_bytes=len(unique)*36+len(indices)*2,
                              source_declared_triangles=model['declared_triangles'],
                              emitted_triangles=model['emitted_position_index_triangles'],
                              texture_hashes=sorted({f['texture'] for f in model['faces']}))


def texture_asset(texture,tier):
    source_rgba=texture['rgba']
    width,height=texture['width'],texture['height'];rgba=source_rgba
    if tier and max(width,height)>tier:
        from PIL import Image
        image=Image.frombytes('RGBA',(width,height),rgba)
        image.thumbnail((tier,tier),Image.Resampling.LANCZOS)
        width,height=image.size;rgba=image.tobytes()
    identity=hashlib.sha256(struct.pack('<6I',int(texture['hash'],16),texture['width'],texture['height'],
                                        int(texture['native_format'],16),texture['alpha_test_mode'],texture['blend_mode'])+source_rgba+
                            struct.pack('<3I',width,height,tier)+rgba).hexdigest()
    output=bytearray(128)+rgba
    output[:4]=b'WTX1'
    struct.pack_into('<15I',output,4,1,len(output),int(texture['hash'],16),width,height,128,len(rgba),tier,
                     texture['alpha_test_mode'],texture['blend_mode'],int(texture['native_format'],16),
                     texture['width'],texture['height'],0,0)
    output[64:96]=hashlib.sha256(source_rgba).digest();output[96:128]=bytes.fromhex(identity)
    struct.pack_into('<I',output,56,asset_crc(output,56))
    return bytes(output),identity,dict(hash=texture['hash'],name=texture['name'],width=width,height=height,
                                      source_width=texture['width'],source_height=texture['height'],
                                      rgba_bytes=len(rgba),alpha_test=texture['alpha_test_mode'],blend=texture['blend_mode'],quality=tier)


def instance_records(data,section_offset):
    # The strict source reader validates every instance/object range and bounds.
    read_instances(data)
    records=[]
    for kind,a,b in chunks(data):
        if kind!=0x80034100:
            continue
        parts={k:(a+c,a+d) for k,c,d in chunks(data[a:b])}
        if 0x34102 not in parts:
            continue
        oa,ob=parts[0x34102];ia,ib=parts[0x34103];ia=align(ia,16)
        for at in range(ia,ib,64):
            object_at=oa+struct.unpack_from('<H',data,at+62)[0]*72
            records.append(struct.pack('<II',section_offset+at,section_offset+object_at)+
                           data[at:at+64]+data[object_at:object_at+72])
    return records


def section_asset(section,records,models,textures):
    output=bytearray(64)
    mo=len(output)
    for key,guard in models:
        output.extend(struct.pack('<I',int(key,16))+bytes.fromhex(guard.split(':')[-1])+bytes(4))
    to=len(output)
    for key,identity in textures:
        output.extend(struct.pack('<I',int(key,16))+bytes.fromhex(identity)+bytes(4))
    io=len(output);output.extend(b''.join(records))
    output[:4]=b'WSI1'
    struct.pack_into('<13I',output,4,1,len(output),section['id'],len(models),len(textures),len(records),
                     mo,to,io,section['offset'],section['bytes'],0,0)
    struct.pack_into('<I',output,48,asset_crc(output,48))
    return bytes(output)


def export(args):
    inventory=json.loads(args.inventory.read_text())
    catalog=json.loads(args.equivalence.read_text())
    if catalog['schema']<2:
        raise ValueError('Consumed equivalence must include the original LOD statistic')
    if catalog['source_sha256']!=inventory['source_sha256']:
        raise ValueError('Equivalence catalog refers to a different stream')
    grouped=defaultdict(list)
    for model in inventory['models']:
        grouped[model['section']].append(model)
    out=args.output
    for folder in ('models','textures','sections'):
        (out/folder).mkdir(parents=True,exist_ok=True)
    exported_models={};exported_textures={};sections=[];rejects=[];aliases=[]
    with args.stream.open('rb') as file:
        with mmap.mmap(file.fileno(),0,access=mmap.ACCESS_READ) as full:
            if hashlib.sha256(full).hexdigest()!=inventory['source_sha256']:
                raise ValueError('Stream differs from verified inventory')
            for section in inventory['sections']:
                data=full[section['offset']:section['offset']+section['bytes']]
                model_bindings=[];texture_bindings=[]
                for source in grouped[section['id']]:
                    proof=catalog['raw_variants'].get(source['raw_sha256'])
                    guard=proof['catalog_key'] if proof else source['hash']+':'+source['raw_sha256']
                    if guard is None:
                        rejects.append(dict(kind='model',hash=source['hash'],section=source['section'],offset=source['offset'],reason='Unresolved consumed-equivalence group'))
                        continue
                    key=source['hash']
                    if key in exported_models:
                        if exported_models[key]['catalog_key']!=guard:
                            raise ValueError('Unproved same-hash model variant; refusing global canonicalization')
                    else:
                        start=source['offset']-section['offset']
                        try:
                            payload,record=model_asset(data,start,start+source['bytes'],source,guard)
                        except ValueError as error:
                            rejects.append(dict(kind='model',hash=key,section=source['section'],offset=source['offset'],reason=str(error)))
                            continue
                        path=out/'models'/(key+'.wsm');path.write_bytes(payload)
                        exported_models[key]=dict(record,catalog_key=guard,path=str(path.relative_to(out)),bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
                    model_bindings.append((key,guard))
                    aliases.append(dict(hash=key,catalog_key=guard,section=source['section'],offset=source['offset'],raw_sha256=source['raw_sha256']))
                for kind,a,b in chunks(data):
                    if kind!=0xB3300000:
                        continue
                    # Source packages are independently aligned; parse within the
                    # complete section so original native alignment is preserved.
                    try:
                        # Prefix must be real top-level chunks, not padding bytes.
                        packet=(struct.pack('<II',0,a-16)+bytes(a-16)+data[a-8:b]) if a>=16 else data[a-8:b]
                        textures=parse_textures(packet)
                    except (ValueError,KeyError) as error:
                        rejects.append(dict(kind='texture_packet',section=section['id'],offset=section['offset']+a-8,reason=str(error)))
                        continue
                    for texture in textures:
                        payload,identity,record=texture_asset(texture,args.texture_tier)
                        if identity not in exported_textures:
                            path=out/'textures'/(texture['hash']+'-'+identity+'.wtx');path.write_bytes(payload)
                            exported_textures[identity]=dict(record,identity=identity,path=str(path.relative_to(out)),bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
                        texture_bindings.append((texture['hash'],identity))
                records=instance_records(data,section['offset'])
                payload=section_asset(section,records,model_bindings,texture_bindings)
                path=out/'sections'/(str(section['id'])+'.wsi');path.write_bytes(payload)
                sections.append(dict(id=section['id'],path=str(path.relative_to(out)),bytes=len(payload),instances=len(records),
                                     model_bindings=len(model_bindings),texture_bindings=len(texture_bindings),sha256=hashlib.sha256(payload).hexdigest()))
                if len(sections)%50==0:
                    print(json.dumps(dict(progress_sections=len(sections),models=len(exported_models),textures=len(exported_textures),rejected=len(rejects))),flush=True)
    manifest=dict(schema=1,source_sha256=inventory['source_sha256'],equivalence_catalog_sha256=hashlib.sha256(args.equivalence.read_bytes()).hexdigest(),
                  texture_quality='native' if not args.texture_tier else args.texture_tier,
                  sections=sections,models=exported_models,textures=exported_textures,model_aliases=aliases,rejected=rejects,
                  limitations='Original LOD selection/instance placement/material consumer readiness remain runtime gates. '
                              'WSM disk20 is not GPU20; expand to floatRGB WorldVertex36. Original night alpha is separate.')
    (out/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n')
    summary=dict(sections=len(sections),instances=sum(s['instances'] for s in sections),models=len(exported_models),
                 texture_payloads=len(exported_textures),rejected=len(rejects),
                 model_bytes=sum(m['bytes'] for m in exported_models.values()),texture_bytes=sum(t['bytes'] for t in exported_textures.values()))
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))


def retry_texture_rejects(args):
    """Re-export only packets rejected by a previously unsupported pixel format."""
    manifest=json.loads((args.output/'manifest.json').read_text())
    inventory=json.loads(args.inventory.read_text());sections={s['id']:s for s in inventory['sections']}
    if manifest['source_sha256']!=inventory['source_sha256']:
        raise ValueError('Existing export and source inventory differ')
    pending=defaultdict(list);kept=[]
    for reject in manifest['rejected']:
        if reject['kind']=='texture_packet':pending[reject['section']].append(reject)
        else:kept.append(reject)
    with args.stream.open('rb') as file:
        with mmap.mmap(file.fileno(),0,access=mmap.ACCESS_READ) as full:
            if hashlib.sha256(full).hexdigest()!=manifest['source_sha256']:
                raise ValueError('Stream differs from existing export')
            for sid,rejects in pending.items():
                section=sections[sid];data=full[section['offset']:section['offset']+section['bytes']]
                destination=args.output/'sections'/(str(sid)+'.wsi');old=destination.read_bytes()
                nm,nt,ni,mo,to,io=struct.unpack_from('<6I',old,16)
                models=[(f'{struct.unpack_from("<I",old,mo+i*40)[0]:08x}',old[mo+i*40+4:mo+i*40+36].hex()) for i in range(nm)]
                textures=[(f'{struct.unpack_from("<I",old,to+i*40)[0]:08x}',old[to+i*40+4:to+i*40+36].hex()) for i in range(nt)]
                for reject in rejects:
                    at=reject['offset']-section['offset'];size=struct.unpack_from('<I',data,at+4)[0]
                    packet=(struct.pack('<II',0,at-8)+bytes(at-8)+data[at:at+8+size]) if at>=8 else data[at:at+8+size]
                    try:decoded=parse_textures(packet)
                    except (ValueError,KeyError) as error:
                        kept.append(dict(reject,reason=str(error)));continue
                    for texture in decoded:
                        payload,identity,record=texture_asset(texture,args.texture_tier)
                        path=args.output/'textures'/(texture['hash']+'-'+identity+'.wtx')
                        if identity not in manifest['textures']:
                            path.write_bytes(payload)
                            manifest['textures'][identity]=dict(record,identity=identity,path=str(path.relative_to(args.output)),bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
                        textures.append((texture['hash'],identity))
                records=[old[io+i*144:io+(i+1)*144] for i in range(ni)]
                payload=section_asset(section,records,models,textures);destination.write_bytes(payload)
                record=next(s for s in manifest['sections'] if s['id']==sid)
                record.update(bytes=len(payload),texture_bindings=len(textures),sha256=hashlib.sha256(payload).hexdigest())
    manifest['rejected']=kept
    (args.output/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n')
    summary=json.loads((args.output/'summary.json').read_text())
    summary.update(texture_payloads=len(manifest['textures']),texture_bytes=sum(t['bytes'] for t in manifest['textures'].values()),rejected=len(kept))
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))


def refresh_equivalence(args):
    """Refresh proved identity guards without re-decoding/reordering geometry."""
    manifest=json.loads((args.output/'manifest.json').read_text())
    catalog=json.loads(args.equivalence.read_text())
    if catalog['schema']<2 or catalog['source_sha256']!=manifest['source_sha256']:
        raise ValueError('Expected original-statistic-preserving catalog for the same stream')
    for key,record in manifest['models'].items():
        path=args.output/record['path'];payload=bytearray(path.read_bytes())
        raw_sha=payload[152:184].hex();proof=catalog['raw_variants'].get(raw_sha)
        guard=proof['catalog_key'] if proof else key+':'+raw_sha
        if guard is None:
            raise ValueError('Updated audit rejects an already exported model')
        payload[184:216]=bytes.fromhex(guard.split(':')[-1])
        struct.pack_into('<I',payload,56,asset_crc(payload,56));path.write_bytes(payload)
        record.update(catalog_key=guard,sha256=hashlib.sha256(payload).hexdigest())
    for alias in manifest['model_aliases']:
        proof=catalog['raw_variants'].get(alias['raw_sha256'])
        if proof:alias['catalog_key']=proof['catalog_key']
    for section in manifest['sections']:
        path=args.output/section['path'];payload=bytearray(path.read_bytes())
        count,offset=struct.unpack_from('<I',payload,16)[0],struct.unpack_from('<I',payload,28)[0]
        for i in range(count):
            at=offset+i*40;key=f'{struct.unpack_from("<I",payload,at)[0]:08x}'
            payload[at+4:at+36]=bytes.fromhex(manifest['models'][key]['catalog_key'].split(':')[-1])
        struct.pack_into('<I',payload,48,asset_crc(payload,48));path.write_bytes(payload)
        section['sha256']=hashlib.sha256(payload).hexdigest()
    for record in manifest['textures'].values():
        path=args.output/record['path'];payload=bytearray(path.read_bytes())
        struct.pack_into('<I',payload,56,asset_crc(payload,56));path.write_bytes(payload)
        record['sha256']=hashlib.sha256(payload).hexdigest()
    manifest['equivalence_catalog_sha256']=hashlib.sha256(args.equivalence.read_bytes()).hexdigest()
    manifest['checksum']='CRC32 of the complete asset with its CRC field replaced by four zero bytes'
    (args.output/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n')
    print(json.dumps(dict(refreshed_models=len(manifest['models']),refreshed_textures=len(manifest['textures']),refreshed_sections=len(manifest['sections']))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inventory','stream','equivalence','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--texture-tier',type=int,choices=(0,256,512),default=0,help='0 preserves source-native dimensions')
    parser.add_argument('--retry-texture-rejects',action='store_true',help='Only revisit prior rejected texture packets; preserve existing models/instances')
    parser.add_argument('--refresh-equivalence',action='store_true',help='Refresh proved catalog identities and asset checksums without decoding geometry')
    args=parser.parse_args()
    (refresh_equivalence if args.refresh_equivalence else retry_texture_rejects if args.retry_texture_rejects else export)(args)
