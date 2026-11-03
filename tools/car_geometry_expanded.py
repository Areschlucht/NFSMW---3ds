#!/usr/bin/env python3
"""Export bounded original GC car meshes, retaining advisory header statistics.

No runtime/shared decoder changes or SDK builds. Each accepted descriptor is
compared with the actual original format22 emitter. Raw input has four indices;
the original FIFO adds a second copy of its third index. Compiled input already
contains five indices. Source counts, material hashes, UVs, normals and unresolved channels remain
separate; this is not a complete vehicle assembly/material implementation.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
from car_geometry_diagnostics import chunks
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256


def sha(b): return hashlib.sha256(b).hexdigest()


class EmitterReference:
    def __init__(self, dol):
        from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
        from unicorn import ppc_const as reg
        if sha(dol)!=DOL_SHA256: raise ValueError('Unexpected original DOL')
        self.reg=reg;self.u=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        self.entry,self.stop=0x8011773c,0x801181c0
        self.begin,self.list=0x8033d2a8,0x803408cc
        image=DolImage(dol);self.u.mem_map(0x80117000,0x2000)
        self.u.mem_write(self.entry,image.read(self.entry,self.stop-self.entry+4))
        for at in (self.begin,self.list): self.u.mem_map(at&~4095,4096)
        self.u.mem_map(0x10000000,0x20000);self.u.mem_map(0xcc008000,4096)
        self.cache={};self.counts=Counter()
        def code(u,address,size,_):
            if address==self.stop: self.stopped=True;u.emu_stop()
            elif address in (self.begin,self.list):
                args=[u.reg_read(getattr(reg,f'UC_PPC_REG_{i}')) for i in (3,4,5)]
                if address==self.begin:self.begins.append(args)
                else:
                    if args[0]!=0x10002000 or args[1]!=len(self.packet): raise ValueError('GX list escaped bounded packet')
                    self.lists.append(bytes(u.mem_read(args[0],args[1])))
                u.reg_write(reg.UC_PPC_REG_PC,u.reg_read(reg.UC_PPC_REG_LR))
            elif not self.entry<=address<self.stop: raise ValueError('Emitter escaped original window')
        def write(u,access,address,size,value,_):
            if address==0xcc008000:
                if size not in (1,2):raise ValueError('Unexpected GX index width')
                self.fifo.extend(value.to_bytes(size,'big'))
            elif not 0x10000000<=address<0x10020000:raise ValueError('Emitter write outside scratch/FIFO')
        self.u.hook_add(UC_HOOK_CODE,code);self.u.hook_add(UC_HOOK_MEM_WRITE,write)

    def verify(self, descriptor, packet, widths):
        flags,n=descriptor[12],descriptor[8];compiled=bool(flags&128)
        key=sha(descriptor[4:]+packet)
        if key in self.cache:return self.cache[key]
        self.packet=packet;self.fifo=bytearray();self.begins=[];self.lists=[];self.stopped=False
        u=self.u;r=self.reg
        u.mem_write(0x10001000,struct.pack('>I',0x10002000)+descriptor[4:]);u.mem_write(0x10002000,packet)
        u.mem_write(0x10018080,struct.pack('>I',0))
        for number,value in ((1,0x10018000),(26,0x10019000),(27,0),(28,0x10001000)):
            u.reg_write(getattr(r,f'UC_PPC_REG_{number}'),value)
        u.emu_start(self.entry,self.stop+4,count=10000)
        if not self.stopped:raise ValueError('Original emitter budget exhausted')
        if compiled:
            if self.fifo or self.begins or self.lists!=[packet]:raise ValueError('Compiled original emitter differs')
        else:
            expected=bytearray();stride=sum(widths)
            for j in range(n):
                at=j*stride;corner=[]
                for width in widths:corner.append(packet[at:at+width]);at+=width
                expected.extend(b''.join(corner[:3]+corner[2:]))
            if self.fifo!=expected or self.lists or self.begins!=[[0x98,0,n]]:
                raise ValueError('Raw original emitter differs from four-to-five index expansion')
        kind='compiled' if compiled else 'raw'
        self.counts[kind]+=1
        result={'kind':kind,'source_bytes':len(packet),'fifo_bytes':len(self.fifo),'source_sha256':sha(packet)}
        self.cache[key]=result
        return result


def unique_children(data,start,end):
    result={}
    for key,a,b in chunks(data,start,end):
        if key in result:raise ValueError('Duplicate model/geometry chunk')
        result[key]=(a,b)
    return result


def decode_part(raw,start,end,reference):
    p=unique_children(raw,start+8,end)
    h,he=p[0x134011];h+=8
    if h+161>he:raise ValueError('Short model header')
    name=raw[h+160:he].split(b'\0',1)[0].decode('ascii')
    bounds=[struct.unpack_from('<3f',raw,h+i) for i in (32,48)]
    transform=struct.unpack_from('<16f',raw,h+64)
    if not all(math.isfinite(x) for x in (*bounds[0],*bounds[1],*transform)):raise ValueError('Nonfinite source header')
    if any(a>b for a,b in zip(*bounds)):raise ValueError('Inverted model bounds')
    refs={}
    for key,label in ((0x134012,'textures'),(0x134013,'shaders')):
        a,b=p[key]
        if (b-a-8)%8:raise ValueError('Malformed material references')
        refs[label]=[struct.unpack_from('<I',raw,i)[0] for i in range(a+8,b,8)]
    g,ge=p[0x80134100];leaves=unique_children(raw,g+8,ge)
    meta=(leaves[0x134800][0]+23)&~15;table=(leaves[0x134801][0]+23)&~15;blob=(leaves[0x134802][0]+39)&~31
    if meta+28>leaves[0x134800][1]:raise ValueError('Short geometry metadata')
    fmt,count=struct.unpack_from('>H2xH',raw,meta)
    size,po,no,co,uvo=struct.unpack_from('>5I',raw,meta+8)
    if fmt!=22 or count==0 or table+count*16>leaves[0x134801][1] or blob+size>leaves[0x134802][1]:raise ValueError('Unsupported/bounded metadata')
    strips=[];triangles=[];checks=[];maximum=[-1]*4
    for i in range(count):
        d=raw[table+i*16:table+(i+1)*16];off=struct.unpack_from('>I',d)[0];n,texture,shader,flags,dfmt=d[8],d[10],d[11],d[12],d[13];length=struct.unpack_from('>H',d,14)[0]
        if dfmt!=22 or flags&~0x9e or n<3 or off+length>size:raise ValueError('Unsupported/bounded descriptor')
        if texture>=len(refs['textures']) or shader>=len(refs['shaders']):raise ValueError('Material reference outside table')
        widths=[2 if flags&bit else 1 for bit in (16,8,4,2)]
        compiled=bool(flags&128);streamwidths=widths[:3]+([widths[2]] if compiled else [])+widths[3:]
        prefix=3 if compiled else 0;needed=prefix+n*sum(streamwidths)
        if needed>length:raise ValueError('Short index packet')
        packet=raw[blob+off:blob+off+length]
        if compiled and (packet[0]!=0x9a or struct.unpack_from('>H',packet,1)[0]!=n):raise ValueError('Unverified GX primitive/layout')
        checks.append(reference.verify(d,packet if compiled else packet[:needed],widths))
        corners=[];at=prefix
        for j in range(n):
            values=[]
            for width in streamwidths:values.append(int.from_bytes(packet[at:at+width],'big'));at+=width
            if compiled:
                # Preserve both independently indexed middle channels; their binding is unresolved.
                corner=(values[0],values[1],values[2],values[3],values[4])
            else:corner=(values[0],values[1],values[2],values[2],values[3])
            corners.append(corner)
            maximum=[max(maximum[0],corner[0]),max(maximum[1],corner[1]),max(maximum[2],corner[2],corner[3]),max(maximum[3],corner[4])]
        strips.append({'texture_hash':f"{refs['textures'][texture]:08x}",'shader_hash':f"{refs['shaders'][shader]:08x}",'group':d[9],'flags':flags,'corners':corners})
        for j in range(n-2):
            a,b,c=corners[j:j+3]
            if j%2:a,b=b,a
            if len({a[0],b[0],c[0]})==3:triangles.append({'corners':[a,b,c],'strip':i})
    ranges=[]
    for offset,stride,num in ((po,6,maximum[0]+1),(no,4,maximum[1]+1),(uvo,4,maximum[3]+1)):
        array_end=offset+stride*num
        if offset<0 or array_end>size:raise ValueError('Attribute array exceeds source blob')
        ranges.append((offset,array_end))
    for i,(a,b) in enumerate(ranges):
        for c,d in ranges[i+1:]:
            if max(a,c)<min(b,d):raise ValueError('Consumed attribute arrays overlap')
    positions=[tuple(v/2048 for v in struct.unpack_from('>3h',raw,blob+po+i*6)) for i in range(maximum[0]+1)]
    if any(not bounds[0][axis]-.001<=v[axis]<=bounds[1][axis]+.001 for v in positions for axis in range(3)):raise ValueError('Source positions exceed stored bounds')
    normals=[tuple(v/64 for v in struct.unpack_from('>3b',raw,blob+no+i*4)) for i in range(maximum[1]+1)]
    if not 0<=co<=uvo<=size:raise ValueError('Auxiliary source region outside blob')
    auxiliary=raw[blob+co:blob+uvo].hex()
    uv=[tuple(v/4096 for v in struct.unpack_from('>2h',raw,blob+uvo+i*4)) for i in range(maximum[3]+1)]
    declared=struct.unpack_from('<H',raw,h+20)[0]
    return {'name':name,'positions':positions,'normals_s8_64':normals,'source_auxiliary_region_hex':auxiliary,'unresolved_corner_channels':[2,3],'uv':uv,'strips':strips,'triangles':triangles,'transform':transform,'stored_bounds':bounds,
            'header_statistic':declared,'emitted_index_nondegenerate_triangles':len(triangles),'statistic_differs':declared!=len(triangles),
            'source_model_offset':start,'source_model_bytes':end-start,'descriptor_parity_checks':checks}


def run(directory,dol,output):
    if output.exists():raise ValueError('Use a new output directory')
    output.mkdir(parents=True);reference=EmitterReference(dol);entries=json.loads((directory/'manifest.json').read_text())['entries'];records=[]
    for entry in entries:
        if not entry['candidate_name'].endswith('\\GEOMETRY.BIN'):continue
        raw=(directory/entry['file']).read_bytes()
        if sha(raw)!=entry['sha256'] or len(raw)!=entry['bytes']:raise ValueError('Source payload differs')
        row={'candidate_name':entry['candidate_name'],'source_sha256':entry['sha256'],'models_exported':0,'rejected':[]}
        roots=list(chunks(raw,0,len(raw)))
        if not roots or roots[0][0]!=0x80134000:row['error']='Not geometry package';records.append(row);continue
        candidates=[]
        for key,start,end in chunks(raw,roots[0][1]+8,roots[0][2]):
            if key!=0x80134010:continue
            p=unique_children(raw,start+8,end);h,he=p[0x134011];name=raw[h+168:he].split(b'\0',1)[0].decode('ascii');candidates.append((name,start,end))
        lods={n.rsplit('_',1)[-1] for n,_,_ in candidates};lod=next((x for x in ('B','C','A','D','E') if x in lods),None);row['selected_offline_lod']=lod;row['available_suffixes']=sorted(lods)
        carout=output/(entry['hash']+'-'+str(entry['directory_record_offset']));carout.mkdir()
        for index,(name,start,end) in enumerate(candidates):
            if lod is not None and not name.endswith('_'+lod):continue
            try:model=decode_part(raw,start,end,reference)
            except (ValueError,KeyError,IndexError,struct.error) as e:row['rejected'].append({'name':name,'reason':str(e)});continue
            destination=carout/f'{index:04d}.mesh.json.gz'
            with gzip.open(destination,'wt',encoding='utf-8') as f:json.dump(model,f,separators=(',',':'))
            if '_KIT00_BODY_' in name and 'body_obj' not in row:
                obj=carout/'body.obj'
                lines=['# Source-derived geometry; original material hashes preserved, material semantics unresolved','o '+name]
                lines += ['v '+' '.join(map(str,v)) for v in model['positions']]
                lines += ['vt '+' '.join(map(str,v)) for v in model['uv']]
                lines += ['vn '+' '.join(map(str,v)) for v in model['normals_s8_64']]
                previous=None
                for face in model['triangles']:
                    index=face['strip']
                    if index!=previous:
                        strip=model['strips'][index];lines.append('g strip_'+str(index)+'_tex_'+strip['texture_hash']+'_shader_'+strip['shader_hash']);previous=index
                    lines.append('f '+' '.join(str(c[0]+1)+'/'+str(c[4]+1)+'/'+str(c[1]+1) for c in face['corners']))
                obj.write_text('\n'.join(lines)+'\n');row['body_obj']=str(obj.relative_to(output))
            row['models_exported']+=1;row.setdefault('triangles_exported',0);row['triangles_exported']+=len(model['triangles']);row.setdefault('source_statistic_discrepancies',0);row['source_statistic_discrepancies']+=model['statistic_differs']
        records.append(row)
    result={'schema':1,'original_dol_sha256':DOL_SHA256,'geometry_records':len(records),'records_with_exported_models':sum(r['models_exported']>0 for r in records),'exported_models':sum(r['models_exported'] for r in records),'triangles_exported':sum(r.get('triangles_exported',0) for r in records),'unique_original_emitter_cases':dict(reference.counts),'records':records,
            'limits':['OfflineLOD priority B,C,A,D,E is explicit export selection, not recovered original attachment or LOD binding','Unresolved corner channels2/3 and auxiliary source bytes retained; no invented colour-array indexing','Per-part rejection is explicit; an exported package may be incomplete','No runtime integration or SDKbuilds; this is not a verified playable roster']}
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');return result

def verify_exports(directory,dol,output):
    """Check legacy equality and malformed source cases against supplied data."""
    from decode_brakes import decode
    report=json.loads((output/'manifest.json').read_text())
    entries=json.loads((directory/'manifest.json').read_text())['entries']
    lookup={e['candidate_name']:e for e in entries};packages=parts=0
    for row in report['records']:
        if row['selected_offline_lod']!='B':continue
        entry=lookup[row['candidate_name']];raw=(directory/entry['file']).read_bytes()
        try:legacy=decode(raw,lod='B')
        except (ValueError,KeyError,IndexError,struct.error):continue
        folder=output/(entry['hash']+'-'+str(entry['directory_record_offset']))
        current={}
        for path in folder.glob('*.mesh.json.gz'):
            with gzip.open(path,'rt') as file:model=json.load(file)
            if model['source_model_bytes']<=0:raise ValueError('Invalid exported provenance')
            current[model['name']]=model
        for old in legacy:
            new=current[old['name']]
            if old['positions']!=[tuple(v) for v in new['positions']] or old['texcoords']!=[tuple(v) for v in new['uv']] or old['normal_candidates']!=[tuple(v) for v in new['normals_s8_64']]:raise ValueError('Legacy attribute mismatch')
            if old['faces']!=[tuple(c[0] for c in t['corners']) for t in new['triangles']] or old['face_uv_indices']!=[tuple(c[4] for c in t['corners']) for t in new['triangles']]:raise ValueError('Legacy topology mismatch')
            parts+=1
        packages+=1
    entry=lookup['CARS\\911GT2\\GEOMETRY.BIN'];raw=(directory/entry['file']).read_bytes()
    root=list(chunks(raw,0,len(raw)))[0]
    _,start,end=next(v for v in chunks(raw,root[1]+8,root[2]) if v[0]==0x80134010)
    reference=EmitterReference(dol);base=decode_part(raw,start,end,reference)
    fields=unique_children(raw,start+8,end);h=fields[0x134011][0]+8
    g,ge=fields[0x80134100];leaves=unique_children(raw,g+8,ge)
    meta=(leaves[0x134800][0]+23)&~15;table=(leaves[0x134801][0]+23)&~15
    cases=[(meta,'>H',17,'bad_format'),(meta+8,'>I',0,'bad_blob_size'),(table,'>I',0xffffffff,'draw_outside_blob'),(table+10,'B',255,'material_outside_table'),(meta+24,'>I',0xffffffff,'uv_outside_blob'),(h+32,'<I',0x7fc00000,'nonfinite_bounds'),(meta+16,'>I',struct.unpack_from('>I',raw,meta+12)[0],'attribute_overlap')]
    rejected=[]
    for offset,fmt,value,label in cases:
        changed=bytearray(raw);struct.pack_into(fmt,changed,offset,value)
        try:decode_part(changed,start,end,reference)
        except (ValueError,KeyError,IndexError,struct.error):rejected.append(label)
        else:raise AssertionError('Corruption accepted: '+label)
    changed=bytearray(raw);struct.pack_into('<H',changed,h+20,base['header_statistic']+1)
    result=decode_part(changed,start,end,reference)
    if result['triangles']!=base['triangles'] or result['header_statistic']!=base['header_statistic']+1:raise ValueError('Header statistic not independent')
    verification={'legacy_packages_exact':packages,'legacy_parts_exact':parts,'rejected_mutations':rejected,'header_statistic_preserved_independently':True,'body_obj_exports':sum('body_obj'in r for r in report['records'])}
    report['verification']=verification;(output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return verification


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('directory','dol','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--verify-exports',action='store_true')
    a=p.parse_args()
    if a.verify_exports:print(json.dumps(verify_exports(a.directory,a.dol.read_bytes(),a.output)))
    else:
        r=run(a.directory,a.dol.read_bytes(),a.output);print(json.dumps({k:v for k,v in r.items() if k not in ('records','limits')}))
