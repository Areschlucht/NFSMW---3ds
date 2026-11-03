#!/usr/bin/env python3
"""Read-only strip/count diagnostics for original car candidates.

Preserves declared statistics and counts emitted topology independently. Does not
weaken the production decoder or claim full vehicle/format/material support.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct


def chunks(data,start,end):
    while start<end:
        if start+8>end:raise ValueError('Truncated chunk')
        kind,size=struct.unpack_from('<II',data,start);stop=start+8+size
        if stop>end:raise ValueError('Chunk outside parent')
        yield kind,start,stop
        start=stop


def models(raw):
    roots=list(chunks(raw,0,len(raw)))
    if not roots or roots[0][0]!=0x80134000:raise ValueError('Not geometry package')
    for kind,start,end in chunks(raw,roots[0][1]+8,roots[0][2]):
        if kind!=0x80134010:continue
        parts={k:(a,b) for k,a,b in chunks(raw,start+8,end)}
        a,b=parts[0x134011];header=a+8
        name=raw[header+160:b].split(b'\0')[0].decode('ascii')
        result={'name':name,'declared_statistic':struct.unpack_from('<H',raw,header+20)[0]}
        g,ge=parts[0x80134100];leaves={k:(a,b) for k,a,b in chunks(raw,g+8,ge)}
        meta=(leaves[0x134800][0]+0x17)&~15
        table=(leaves[0x134801][0]+0x17)&~15
        blob=(leaves[0x134802][0]+0x27)&~31
        fmt,count=struct.unpack_from('>H2xH',raw,meta)
        data_size=struct.unpack_from('>I',raw,meta+8)[0]
        if blob+data_size>leaves[0x134802][1] or table+count*16>leaves[0x134801][1]:raise ValueError('Descriptor/data bounds')
        result['format']=fmt;raw_count=nondegenerate=0;descriptors=[]
        for i in range(count):
            at=table+i*16;off=struct.unpack_from('>I',raw,at)[0]
            n,flags,dfmt=raw[at+8],raw[at+12],raw[at+13]
            length=struct.unpack_from('>H',raw,at+14)[0]
            if off+length>data_size:raise ValueError('Descriptor exceeds blob')
            if fmt!=22 or dfmt!=22 or flags&~0x9e or n<3:
                result['unsupported_descriptor']={'index':i,'format':dfmt,'flags':flags,'n':n};break
            widths=[2 if flags&bit else 1 for bit in (16,8,4,2)]
            widths=widths[:3]+([widths[2]] if flags&128 else [])+widths[3:]
            stride=sum(widths);prefix=3 if flags&128 else 0
            if prefix+n*stride>length:raise ValueError('Truncated strip')
            p=blob+off
            if prefix and (raw[p]!=0x9a or struct.unpack_from('>H',raw,p+1)[0]!=n):raise ValueError('Display list mismatch')
            ids=[int.from_bytes(raw[p+prefix+j*stride:p+prefix+j*stride+widths[0]],'big') for j in range(n)]
            emitted=n-2;good=sum(len(set(ids[j:j+3]))==3 for j in range(n-2))
            raw_count+=emitted;nondegenerate+=good
            descriptors.append({'index':i,'n':n,'flags':flags,'bytes':length,'raw_triangles':emitted,'index_nondegenerate':good})
        result.update(raw_strip_triangles=raw_count,index_nondegenerate_triangles=nondegenerate,
            repeated_index_triangles=raw_count-nondegenerate,descriptor_count=count,
            descriptor_count_checked=len(descriptors),descriptors_sha256=hashlib.sha256(json.dumps(descriptors,sort_keys=True).encode()).hexdigest())
        if 'unsupported_descriptor' not in result:
            expected=result['declared_statistic']
            result['statistic_match']='both' if expected==raw_count==nondegenerate else 'raw_only' if expected==raw_count else 'nondegenerate_only' if expected==nondegenerate else 'neither'
        yield result


def inspect(directory):
    entries=json.loads((directory/'manifest.json').read_text())['entries'];records=[]
    for entry in entries:
        if not entry['candidate_name'].endswith('\\GEOMETRY.BIN'):continue
        raw=(directory/entry['file']).read_bytes()
        if len(raw)!=entry['bytes'] or hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Source differs')
        row={'candidate_name':entry['candidate_name'],'source_sha256':entry['sha256']}
        try:parts=list(models(raw))
        except (ValueError,KeyError,IndexError,struct.error) as e:row['error']=str(e)
        else:
            row['parts']=parts;row['suffix_counts']=dict(Counter(m['name'].rsplit('_',1)[-1] for m in parts))
        records.append(row)
    b=[m for r in records for m in r.get('parts',[]) if m['name'].endswith('_B')]
    allparts=[m for r in records for m in r.get('parts',[])]
    return {'schema':1,'geometry_records':len(records),'all_model_parts':len(allparts),
        'B_parts':len(b),'B_count_matches':dict(Counter(m.get('statistic_match','unsupported') for m in b)),
        'all_count_matches':dict(Counter(m.get('statistic_match','unsupported') for m in allparts)),
        'records_without_B':[{'candidate_name':r['candidate_name'],'suffix_counts':r['suffix_counts'],
            'first_model_names':[m['name'] for m in r['parts'][:3]]} for r in records if 'parts'in r and not any(m['name'].endswith('_B') for m in r['parts'])],
        'records':records,'limits':['Counts are topology diagnostics, not proof of declared statistic semantics',
            'Source statistic must remain unchanged for original LOD consumers','No runtime or shared decoder modified']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=inspect(a.directory);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ('records','records_without_B','limits')}))


def verify_car_emitter(dol, descriptor, packet):
    """Execute same original descriptor loop for car format22, with GX hooks."""
    from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
    from unicorn import ppc_const as reg
    from vehicle_dol import DolImage
    from vehicle_ppc_reference import DOL_SHA256
    if hashlib.sha256(dol).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected DOL')
    if len(descriptor)!=16 or descriptor[13]!=22:raise ValueError('Not car format22')
    flags=descriptor[12];n=descriptor[8]
    widths=[2 if flags&bit else 1 for bit in (16,8,4,2)]
    if flags&128:widths=widths[:3]+[widths[2]]+widths[3:]
    required=struct.unpack_from('>H',descriptor,14)[0] if flags&128 else n*sum(widths)
    if flags&~0x9e or n<3 or not 0<required<=len(packet)<=65535:raise ValueError('Invalid descriptor/packet')
    entry,stop,gx_begin,gx_list=0x8011773c,0x801181c0,0x8033d2a8,0x803408cc
    im=DolImage(dol);u=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
    u.mem_map(0x80117000,0x2000);u.mem_write(entry,im.read(entry,stop-entry+4))
    for address in (gx_begin,gx_list):u.mem_map(address&~4095,4096)
    u.mem_map(0x10000000,0x20000);u.mem_map(0xcc008000,4096)
    data_address=0x10002000;desc_address=0x10001000;stack=0x10018000
    u.mem_write(desc_address,struct.pack('>I',data_address)+descriptor[4:]);u.mem_write(data_address,packet)
    u.mem_write(stack+0x80,struct.pack('>I',0))
    for number,value in ((1,stack),(26,0x10019000),(27,0),(28,desc_address)):
        u.reg_write(getattr(reg,f'UC_PPC_REG_{number}'),value)
    result={'fifo':bytearray(),'begin':[],'display_lists':[],'stopped':False}
    def code(uc,address,size,_):
        if address==stop:result['stopped']=True;uc.emu_stop()
        elif address in (gx_begin,gx_list):
            args=[uc.reg_read(getattr(reg,f'UC_PPC_REG_{i}')) for i in (3,4,5)]
            if address==gx_begin:result['begin'].append(args)
            else:
                if args[0]!=data_address or args[1]!=required:raise ValueError('Display list outside packet')
                result['display_lists'].append(bytes(uc.mem_read(args[0],args[1])))
            uc.reg_write(reg.UC_PPC_REG_PC,uc.reg_read(reg.UC_PPC_REG_LR))
        elif not entry<=address<stop:raise ValueError('Execution escaped emitter')
    def write(uc,access,address,size,value,_):
        if address==0xcc008000:
            if size not in (1,2):raise ValueError('Unexpected FIFO width')
            result['fifo'].extend(value.to_bytes(size,'big'))
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    u.emu_start(entry,stop+4,count=10000)
    if not result['stopped']:raise ValueError('Emitter instruction budget exhausted')
    if flags&128:
        if result['fifo'] or result['display_lists']!=[packet[:required]]:raise ValueError('Compiled packet parity failed')
    else:
        if bytes(result['fifo'])!=packet[:required] or result['display_lists']:raise ValueError(f'Raw packet parity failed flags={flags:x}, n={n}, actual={len(result["fifo"])}, expected={required}, begin={result["begin"]}, actualfirst={bytes(result["fifo"])[:16].hex()}, expectedfirst={packet[:16].hex()}')
        if not result['begin'] or result['begin'][0][2]!=n:raise ValueError('Original GX vertex count differs')
    return {'flags':flags,'vertices':n,'compiled':bool(flags&128),'packet_bytes':required,
            'packet_sha256':hashlib.sha256(packet[:required]).hexdigest(),'original_parity':True}
