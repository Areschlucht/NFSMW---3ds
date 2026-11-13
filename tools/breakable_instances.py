#!/usr/bin/env python3
"""Bind source SmackableParams to exact original scenery instances; no name filter."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib
from nfs_rockport import chunks
from vehicle_attributes import VehicleAttributes
from vehicle_vlt_hash import vlt_hash
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
from gameplay_activation_recovery import source_groups,instance_mapping

ATTR_SHA='5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c'
def sha(raw):return hashlib.sha256(raw).hexdigest()

def build(a):
    stream=a.stream.read_bytes();l2ra=a.l2ra.read_bytes();attr=a.attributes.read_bytes();dol=a.dol.read_bytes()
    if sha(attr)!=ATTR_SHA or sha(dol)!=DOL_SHA256:raise ValueError('Wrong original ATTR/DOL')
    manifest=json.loads((a.scene/'manifest.json').read_text())
    if manifest['source_sha256']!=sha(stream):raise ValueError('Scene source differs')
    _,members=source_groups(l2ra);mapping=instance_mapping(l2ra,a.stream);db=VehicleAttributes(attr)
    objects={}
    for path in (a.scene/'sections').glob('*.wsi'):
        b=path.read_bytes();count,at=struct.unpack_from('<I',b,24)[0],struct.unpack_from('<I',b,36)[0]
        if b[:4]!=b'WSI1' or at+count*144!=len(b):raise ValueError('Malformed original scene')
        for i in range(count):
            p=at+i*144;offset,object_offset=struct.unpack_from('<II',b,p)
            if b[p+8:p+72]!=stream[offset:offset+64] or b[p+72:p+144]!=stream[object_offset:object_offset+72]:raise ValueError('Scene original bytes differ')
            objects[offset]=(b[p+8:p+72],b[p+72:p+144],object_offset,struct.unpack_from('<I',b,12)[0])
    blueprints={}
    for k,start,stop in chunks(l2ra):
        if k!=0x8003410b:continue
        for kind,x,y in chunks(l2ra[start:stop]):
            if kind!=0x3410c:raise ValueError('Unknown source blueprint child')
            raw=l2ra[start+x:start+y];key=struct.unpack_from('<I',raw)[0];count=raw[4]
            if len(raw)!=8+count*16:raise ValueError('Invalid source blueprint')
            blueprints[key]={'offset':start+x,'records':[{'state_key':f'{t:08x}','model_hash':f'{m:08x}','runtime_pointer':r,'flags':f}for t,m,r,f in struct.iter_unpack('<4I',raw[8:])]}
    props={};occurrences=0
    for k,start,stop in chunks(stream):
        if k!=0x34027:continue
        h=(start+15)&~15
        if any(x!=0x11 for x in stream[start:h]) or h+16>stop:raise ValueError('Invalid source smackable padding')
        section=struct.unpack_from('<H',stream,h+8)[0];count=struct.unpack_from('<H',stream,h+12)[0];fixed=stream[h+14]
        if fixed or h+16+count*64!=stop:raise ValueError('Invalid source smackable array')
        for i in range(count):
            off=h+16+i*64;raw=stream[off:off+64];quat=struct.unpack_from('<4f',raw);position=struct.unpack_from('<4f',raw,16)
            unknown,collision,key,member,local,flags=struct.unpack_from('<6I',raw,32);occurrences+=1
            if member>=len(members) or not all(math.isfinite(v)for v in quat+position):raise ValueError('Bad source smackable identity/pose')
            if member in props:
                if props[member]['raw']!=raw:raise ValueError('Conflicting physical smackable copies')
                props[member]['source_parameter_offsets'].append(off);continue
            row=db.collections.get((vlt_hash('smackable'),key))
            if row is None:raise ValueError('Source smackable reference does not resolve')
            fields=db.fields(row);mass=fields['MASS']['value'];scalar=fields['0xbe71dbad']['value']
            if not math.isfinite(mass)or mass<=0 or not math.isfinite(scalar):raise ValueError('Invalid source property scalar')
            m=members[member];targets=mapping.get((m['scenery_section'],m['instance_index']),[])
            if not targets:raise ValueError('Source scenery member is unmapped')
            bindings=[]
            for target in targets:
                source=target['source_instance_offset']
                if source not in objects:raise ValueError('Mapped source scenery absent in archive')
                inst,obj,objoff,directory=objects[source];translation=struct.unpack_from('<3f',inst,32)
                expected=(position[2],-position[0],position[1]);error=max(abs(x-y)for x,y in zip(translation,expected))
                if error>.0001:raise ValueError(f'Smackable/scenery placement differs: {member}/{error}')
                bounds=struct.unpack_from('<6f',inst);view_bounds=(bounds[0],bounds[2],-bounds[4],bounds[3],bounds[5],-bounds[1])
                blueprint=struct.unpack_from('<I',obj,64)[0]
                if blueprint and blueprint not in blueprints:raise ValueError('Source blueprint missing')
                bindings.append({'source_instance_offset':source,'source_object_offset':objoff,'stream_directory':directory,'original_flags':struct.unpack_from('<I',inst,24)[0],
                    'bounds_viewer':view_bounds,'translation_viewer':(translation[0],translation[2],-translation[1]),'blueprint_key':blueprint,'slots':[f'{x:08x}'for x in struct.unpack_from('<4I',obj,24)],'name':obj[:24].split(b'\0')[0].decode('ascii')})
            props[member]={'raw':raw,'member':member,'logical_section':section,'source_parameter_offsets':[off],'attribute_key':key,'attribute_name':db.label(key),'mass':mass,'source_scalar_be71dbad':scalar,
                'source_bool_1f989f01':int(fields['0x1f989f01']['value']),'source_bool_6f002423':int(fields['0x6f002423']['value']),'event_sequencer':fields['EventSequencer']['value'],
                'dynamic_collision_key':collision,'unknown_word20':unknown,'local_index':local,'flags':flags,'quaternion_internal':quat,'bindings':bindings}
    rows=[];seen=set()
    for member,p in props.items():
        for b in p['bindings']:
            offset=b['source_instance_offset']
            if offset in seen:raise ValueError('Two source props reference one scenery instance')
            seen.add(offset);rows.append((offset,p,b))
    rows.sort();record_data=bytearray();grid=defaultdict(list);step=128.
    lowx=math.floor(min(b['bounds_viewer'][0]for _,p,b in rows)/step)*step
    lowz=math.floor(min(b['bounds_viewer'][2]for _,p,b in rows)/step)*step
    nx=math.floor((max(b['bounds_viewer'][3]for _,p,b in rows)-lowx)/step)+1
    nz=math.floor((max(b['bounds_viewer'][5]for _,p,b in rows)-lowz)/step)+1
    if nx*nz>65536:raise ValueError('Source breakable grid exceeds native budget')
    for index,(offset,p,b)in enumerate(rows):
        record=bytearray(128)
        struct.pack_into('<8I2f2I6f3f4f7I',record,0,offset,p['source_parameter_offsets'][0],p['member'],p['attribute_key'],p['logical_section'],b['original_flags'],b['blueprint_key'],p['dynamic_collision_key'],
            p['mass'],p['source_scalar_be71dbad'],p['source_bool_1f989f01'],p['source_bool_6f002423'],*b['bounds_viewer'],*b['translation_viewer'],*p['quaternion_internal'],p['unknown_word20'],p['local_index'],p['flags'],p['event_sequencer']['hash32'],0,0,0)
        record_data.extend(record);bound=b['bounds_viewer']
        for z in range(math.floor((bound[2]-lowz)/step),math.floor((bound[5]-lowz)/step)+1):
            for x in range(math.floor((bound[0]-lowx)/step),math.floor((bound[3]-lowx)/step)+1):grid[z*nx+x].append(index)
    cells=nx*nz;offsets=[0];refs=[]
    for cell in range(cells):refs.extend(grid[cell]);offsets.append(len(refs))
    data=bytearray(160)+record_data;go=len(data);data.extend(struct.pack('<'+str(len(offsets))+'I',*offsets));ro=len(data);data.extend(struct.pack('<'+str(len(refs))+'I',*refs))
    struct.pack_into('<4s8I3f4I',data,0,b'NBP1',1,len(data),0,len(rows),128,160,go,ro,lowx,lowz,step,nx,nz,len(refs),max(props)+1)
    data[64:96]=bytes.fromhex(sha(stream));data[96:128]=bytes.fromhex(sha(l2ra));data[128:160]=bytes.fromhex(sha(attr));struct.pack_into('<I',data,12,zlib.crc32(data[16:]))
    windows=[(0x802212cc,0x8022139c),(0x802213f8,0x80221470),(0x80221470,0x80221514),(0x802bd878,0x802bd898),(0x802bdd20,0x802bdec8)]
    im=DolImage(dol);report={'schema':1,'source_sha256':{'stream':sha(stream),'l2ra':sha(l2ra),'attributes':sha(attr),'dol':sha(dol)},'source_parameter_occurrences':occurrences,'unique_scenery_members':len(props),'render_instance_bindings':len(rows),
        'bytes':len(data),'sha256':sha(data),'grid':[nx,nz],'grid_references':len(refs),'original_consumer_windows':[{'start':hex(x),'end':hex(y),'sha256':sha(im.read(x,y-x))}for x,y in windows],
        'limits':['Exact original typed property/scenery binding and placement; native hit detector is conservative source-bounds adaptation','Unknown source scalar0xBE71DBAD is retained, not falsely labeled a verified damage threshold','Blueprint entry order/keys retained; no guessed fragment spawn/selection or original debris physics','Original dynamic collider resources are distinct from static CI group ownership']}
    a.output.mkdir(parents=True,exist_ok=True)
    for name,payload in [('breakables.nbp',bytes(data)),('manifest.json',(json.dumps(report,indent=2)+'\n').encode()),('catalog.json',(json.dumps({'summary':report,'properties':[{k:v for k,v in p.items()if k!='raw'}for p in props.values()],'blueprints':{f'{k:08x}':v for k,v in blueprints.items()}},indent=2)+'\n').encode())]:
        path=a.output/name
        if path.exists()and path.read_bytes()!=payload:raise ValueError('Existing output differs')
        if not path.exists():path.write_bytes(payload)
    print(json.dumps({k:report[k]for k in('source_parameter_occurrences','unique_scenery_members','render_instance_bindings','bytes','sha256')}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in('l2ra','stream','attributes','scene','dol','output'):p.add_argument('--'+n,type=Path,required=True)
    build(p.parse_args())
