#!/usr/bin/env python3
"""Export actual GC S8/64 car normals in verified existing NFMv1 corner order.

Original VAT2 normalformat8010E458..46C; normalarray pointer80116D74..90;
GX stride4 binding801170AC..BC. Header object transforms are not applied a
second time. Fitted wheel positions use an existing provisional rig, so their
source normals receive the same180degree source-Z rotation on left wheels.
No smoothing, normalization, invented lighting or shared scene edits occur.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
import struct
import zlib
from pathlib import Path
from decode_brakes import decode
from nfs_rockport import chunks
from material_recovery_vehicle import texture_hash
from fit_bmw_wheels import fit_wheels
from material_recovery_vehicle import DOL_SHA256
from vehicle_dol import DolImage


def material_catalog(bundle):
    """Read observed original material records without inventing field names.

    The generic loader800F8CE4 byte-swaps fields; GC material initialization
    uses80109B70 and cached coefficient preparation80109BB8. Float fields are
    retained by exact record offsets until final GX consumers prove semantics.
    """
    result={}
    for kind,start,end in chunks(bundle):
        if kind!=0x00135200:continue
        if end-start!=168:raise ValueError('Unsupported original material record size')
        record=bundle[start:end]
        version,platform,kindword,key,variant=struct.unpack_from('<5I',record)
        if (version,platform,kindword,variant)!=(1,3,3,3):
            raise ValueError('Unknown original material record variant')
        rawname=record[20:48];nul=rawname.find(b'\0')
        if nul<0:raise ValueError('Unterminated original material name')
        name=rawname[:nul].decode('ascii')
        if texture_hash(name)!=key:raise ValueError('Original material name/hash mismatch')
        if key in result:raise ValueError('Duplicate original material hash')
        fields=[]
        for off in range(48,168,4):
            value=struct.unpack_from('<f',record,off)[0]
            if not math.isfinite(value):raise ValueError('Nonfinite original material field')
            fields.append(dict(offset=f'{off:02x}',value=value,original_bytes=record[off:off+4].hex()))
        result[key]=dict(key=f'{key:08x}',name=name,file_offset=start,raw_record=record.hex(),record_sha256=hashlib.sha256(record).hexdigest(),fields=fields)
    return result


def source_records(data):
    """Retain original descriptor and reference words that legacydecode omits."""
    def absolute(start,end):
        return [(k,start+s,start+e) for k,s,e in chunks(data[start:end])]
    roots=absolute(0,len(data))
    if roots[0][0]!=0x80134000:raise ValueError('Not original geometry root')
    result={}
    for kind,start,end in absolute(roots[0][1],roots[0][2]):
        if kind!=0x80134010:continue
        fields={k:(s,e) for k,s,e in absolute(start,end)}
        h,he=fields[0x134011];name=data[h+160:he].split(b'\0')[0].decode('ascii')
        references={}
        for tag in (0x134012,0x134013):
            a,b=fields[tag]
            if (b-a)%8:raise ValueError('Incomplete original geometry reference')
            references[tag]=list(struct.iter_unpack('<2I',data[a:b]))
        gs,ge=fields[0x80134100];leaves={k:(s,e) for k,s,e in absolute(gs,ge)}
        meta=(leaves[0x134800][0]+15)&~15;table=(leaves[0x134801][0]+15)&~15
        count=struct.unpack_from('>H',data,meta+4)[0]
        rows=[]
        for i in range(count):
            at=table+16*i
            if at+16>leaves[0x134801][1]:raise ValueError('Original descriptor exceeds table')
            raw=data[at:at+16];ti,si=raw[10:12]
            if ti>=len(references[0x134012]) or si>=len(references[0x134013]):raise ValueError('Original descriptor reference exceeds table')
            tex,tw=references[0x134012][ti];shader,sw=references[0x134013][si]
            rows.append(dict(descriptor_file_offset=at,descriptor_raw=raw.hex(),descriptor_flags=raw[12],descriptor_format=raw[13],
                texture_hash=f'{tex:08x}',texture_reference_word1=f'{tw:08x}',shader_hash=f'{shader:08x}',shader_reference_word1=f'{sw:08x}'))
        result[name]=rows
    return result


def viewer_normal(normal,side=None):
    x,y,z=normal
    if side is not None:
        if side not in (-1,1):raise ValueError('Fitted wheel side must be+1or-1')
        x,y=-side*x,-side*y
    return x,z,-y


def reference_scene(raw):
    if len(raw)<32:raise ValueError('Short reference NFM')
    magic,version,nv,nb,nt,size,crc,flags=struct.unpack_from('<4s7I',raw)
    if magic!=b'NFM1' or version!=1 or flags or size!=len(raw)-32 or zlib.crc32(raw[32:])!=crc:
        raise ValueError('Expected validated original NFMv1 reference')
    if size!=nt*16+nb*16+nv*32:raise ValueError('NFM schema length mismatch')
    textures=[struct.unpack_from('<4I',raw,32+i*16)[0] for i in range(nt)]
    batches=[struct.unpack_from('<4I',raw,32+nt*16+i*16) for i in range(nb)]
    at=32+nt*16+nb*16
    return dict(vertex_count=nv,batches=batches,textures=textures,vertices=raw[at:],crc=crc)


def export(geometry,reference,output,dol=None):
    ref=reference_scene(reference);models=decode(geometry,lod='B');records=source_records(geometry)
    selected=[dict(m) for m in models if not any(s in m['name'] for s in ('DAMAGE0','DRIVER','TIRE','BRAKE_B'))]
    body=next(m for m in models if m['name']=='BMWM3GTRE46_KIT00_BODY_B')
    tire=next(m for m in models if m['name']=='BMWM3GTRE46_KIT00_FRONT_TIRE_B')
    wheels,placement=fit_wheels(body,tire)
    for m,fit in zip(wheels,placement['arch_fits']):m['normal_wheel_side']=fit['side']
    selected.extend(wheels)
    groups={};partmeta=[];wheel_group=0;lengths=[]
    for part_id,m in enumerate(selected):
        group=0
        if 'wheel_pivot' in m:wheel_group+=1;group=wheel_group
        partmeta.append(dict(index=part_id,name=m['name'],wheel_group=group,source_normals=len(m['normal_candidates']),
                             wheel_side=m.get('normal_wheel_side'),source_transform=m['transform']))
        for face_id,(face,uv_ids,normal_ids,strip_id) in enumerate(zip(m['faces'],m['face_uv_indices'],m['face_normal_indices'],m['face_strip_indices'])):
            pts=[m['positions'][i] for i in face]
            a=[pts[1][i]-pts[0][i] for i in range(3)];b=[pts[2][i]-pts[0][i] for i in range(3)]
            cross=(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
            if not sum(x*x for x in cross):continue
            strip=m['strips'][strip_id];render_source=records[tire['name'] if 'normal_wheel_side' in m else m['name']][strip_id]
            if render_source['shader_hash']!=strip['shader_hash']:raise ValueError('Raw shader reference disagrees with decoded strip')
            key=(int(strip['texture_hash'],16),group)
            target=groups.setdefault(key,[])
            for corner,(p,uv,nidx) in enumerate(zip(pts,uv_ids,normal_ids)):
                source=m['normal_candidates'][nidx]
                if any(not -128<=round(x*64)<=127 or x!=round(x*64)/64 for x in source):
                    raise ValueError('Source normal is not exactly representable S8/64')
                normal=viewer_normal(source,m.get('normal_wheel_side'))
                lengths.append(math.sqrt(sum(x*x for x in normal)))
                target.append(dict(p=(p[0],p[2],-p[1]),uv=m['texcoords'][uv],normal=normal,
                    provenance=(part_id,face_id,corner,nidx,int(strip['shader_hash'],16)),render_source=render_source,strip_id=strip_id))
    expanded=[v for g in groups.values() for v in g]
    if len(expanded)!=ref['vertex_count'] or len(groups)!=len(ref['batches']):raise ValueError('Source/reference vertex or batch order mismatch')
    low=[min(v['p'][i] for v in expanded) for i in range(3)];high=[max(v['p'][i] for v in expanded) for i in range(3)]
    extent=max(high[i]-low[i] for i in range(3))
    cursor=0;normals=bytearray();mapping=bytearray();batchmeta=[];position_uv_matches=0;material_runs=[]
    for (texture,group),vertices in groups.items():
        batch=ref['batches'][len(batchmeta)]
        if batch[:2]!=(cursor,len(vertices)) or ref['textures'][batch[2]]!=texture or batch[3]!=0:
            raise ValueError('Reference batch does not preserve original expansion order')
        shaders=Counter()
        for vertex in vertices:
            p=[(vertex['p'][i]-(low[i]+high[i])*.5)*2/extent for i in range(3)]
            offset=cursor*32
            if struct.pack('<3f',*p)!=ref['vertices'][offset:offset+12] or struct.pack('<2f',*vertex['uv'])!=ref['vertices'][offset+24:offset+32]:
                raise ValueError(f'Bitwise source/reference position or UV mismatch at vertex{cursor}')
            position_uv_matches+=1
            normals.extend(struct.pack('<3f',*vertex['normal']));mapping.extend(struct.pack('<5I',*vertex['provenance']))
            shaders[f'{vertex["provenance"][4]:08x}']+=1;cursor+=1
        # Keep original strip/face-continuity boundaries even when adjacent
        # shader keys match. Never merge separated original draw records.
        run=None;previous_face=None
        for triangle in range(0,len(vertices),3):
            tri=vertices[triangle:triangle+3]
            if len(tri)!=3 or len({v['provenance'][4] for v in tri})!=1:
                raise ValueError('Material run triangle has inconsistent shader keys')
            v=tri[0];part_id,face_id,corner,normal_id,shader=v['provenance'];raw=v['render_source']
            identity=(part_id,v['strip_id'],shader,raw['shader_reference_word1'],raw['descriptor_flags'])
            if run is None or identity!=run['_identity'] or face_id!=previous_face+1:
                run=dict(raw,_identity=identity,first=batch[0]+triangle,count=0,nfm_batch=len(batchmeta),texture_hash=f'{texture:08x}',
                    wheel_group=group,source_part_index=part_id,source_part_name=partmeta[part_id]['name'],source_strip_index=v['strip_id'],
                    source_face_first=face_id,source_face_last=face_id,selected_material_hash='93c0eaf6' if shader==0xd6d6080a else f'{shader:08x}',
                    canonical_override='CARSKIN→canonicalMETPAINTSILVER' if shader==0xd6d6080a else None)
                material_runs.append(run)
            run['count']+=3;run['source_face_last']=face_id;previous_face=face_id
        batchmeta.append(dict(first=batch[0],count=batch[1],texture=f'{texture:08x}',wheel_group=group,original_shader_corner_counts=dict(shaders)))
    for run in material_runs:run.pop('_identity')
    if sum(r['count'] for r in material_runs)!=cursor:raise ValueError('Material run coverage mismatch')
    if min(lengths)<=0:raise ValueError('Zero original normal requires runtime shader handling')
    output.mkdir(parents=True,exist_ok=True)
    (output/'normals-f32le.bin').write_bytes(normals);(output/'normal-provenance-u32le.bin').write_bytes(mapping)
    result=dict(source_geometry_sha256=hashlib.sha256(geometry).hexdigest(),reference_nfm_sha256=hashlib.sha256(reference).hexdigest(),
        reference_nfm_payload_crc32=f'{ref["crc"]:08x}',vertex_count=cursor,bitwise_position_uv_matches=position_uv_matches,
        normals_sha256=hashlib.sha256(normals).hexdigest(),provenance_sha256=hashlib.sha256(mapping).hexdigest(),
        normal_layout='per expanded NFMvertex3float32LE xyz,12bytes; no normalization or smoothing',
        provenance_layout='pervertex5uint32LE(partindex,sourcefaceindex,cornerindex,normalindex,originalshaderhash)',
        source_format=dict(gx_vat=2,gx_attr=10,component_count='XYZ',component_type='S8',fractional_bits=6,array_stride=4),
        viewer_basis='source(nx,ny,nz)→viewer(nx,nz,-ny); fittedwheel pretransform=(-side*nx,-side*ny,nz), side+1left/-1right',
        source_normal_length=[min(lengths),max(lengths)],parts=partmeta,batches=batchmeta,material_runs=material_runs,
        material_run_scope='Exact intersections with current NFMbatches; original strip/facecontinuity kept; rawreferenceword1 and descriptorflags retained without speculative meanings',
        carskin_override_proof='Canonicalbasepaint attribute6BA02C05=93C0EAF6 selected802C8968..899C→CarRenderInfo+CC; draw802CD2DC..2F0 substitutesCARSKIN D6D6080A',
        limitations=['Wheel attachment positions remain the existing fitted rig, not original axle metadata',
                     'Current scene batches merge original shader hashes; source normals alone do not establish original material/lighting',
                     'Header transforms are not reapplied; current source positions are baked and bitwise match the reference'],
        patch_contract='Root may replace only bytes12..23 of each NFMv1vertex with normals.bin then update payloadCRC and wheelrigbinding; firstvalidate fullreferenceSHA/count/order')
    if dol is not None:
        if hashlib.sha256(dol.data).hexdigest()!=DOL_SHA256:raise ValueError('Normal proof requires pinned original DOL')
        result['dol_sha256']=DOL_SHA256
        result['original_code']=[dict(name=n,start=f'{a:08x}',end_exclusive=f'{b:08x}',file_offset=dol.file_offset(a,b-a),sha256=hashlib.sha256(dol.read(a,b-a)).hexdigest())
            for n,a,b in [('VAT2_normal_format',0x8010e458,0x8010e470),('normal_pointer',0x80116d4c,0x80116da4),('normal_array_bind',0x801170a8,0x801170c0)]]
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('geometry',type=Path);p.add_argument('reference_nfm',type=Path);p.add_argument('output',type=Path);p.add_argument('--dol',type=Path);p.add_argument('--materials',type=Path,help='Optional original GLOBALB material records')
    a=p.parse_args();r=export(a.geometry.read_bytes(),a.reference_nfm.read_bytes(),a.output,DolImage(a.dol.read_bytes()) if a.dol else None)
    if a.materials:
        raw=a.materials.read_bytes();catalog=material_catalog(raw)
        (a.output/'material-catalog.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(raw).hexdigest(),records=list(catalog.values())),indent=2)+'\n')
    print(r['vertex_count'],r['bitwise_position_uv_matches'],r['normals_sha256'])
