#!/usr/bin/env python3
"""Resolve original preset -> physical pvehicle profile, preserving key evidence.

GC preset loader802DB494 reverses each serialized64-bit key. Consumers then read
native+54 (the low32bits of original field+50), not the visual model name.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from material_recovery_presets import report as preset_report,STRIDE,KIND
from vehicle_attributes import VehicleAttributes
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
from vehicle_vlt_hash import vlt_hash
from vehicle_verify_original import ATTR_SHA


def profile_keys(record):
    raw=bytes.fromhex(record['unknown_48'])
    if len(raw)!=24:raise ValueError('Expected exact original preset48..5F bytes')
    frontend,pvehicle=struct.unpack_from('<2Q',raw)
    return dict(frontend_key64=f'{frontend:016x}',frontend_collection_key=f'{frontend&0xffffffff:08x}',
                pvehicle_key64=f'{pvehicle:016x}',pvehicle_collection_key=f'{pvehicle&0xffffffff:08x}',
                raw_48_5f=raw.hex(),uninterpreted_58_5f=raw[16:].hex())


def verify_consumer(image,record_bytes):
    if hashlib.sha256(image.data).hexdigest()!=DOL_SHA256:raise ValueError('DOL checksum')
    if len(record_bytes)!=STRIDE:raise ValueError('Expected one original preset record')
    expected_key=struct.unpack_from('<I',record_bytes,0x50)[0]
    if not expected_key:raise ValueError('Zero physical profile uses a separate fallback path')
    from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
    from unicorn.ppc_const import UC_PPC_REG_1,UC_PPC_REG_3,UC_PPC_REG_4,UC_PPC_REG_30,UC_PPC_REG_31,UC_PPC_REG_LR,UC_PPC_REG_PC
    u=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN)
    obj,stack,stop,head=0x90000000,0x91000000,0xa0000000,0x804a6f80
    for address,size in [(0x802db000,0x1000),(0x8005c000,0x1000),(0x800f2000,0x1000),(0x80165000,0x1000),(0x801a2000,0x1000),(obj,0x1000),(stack,0x2000),(stop,0x1000),(0x804a6000,0x1000)]:u.mem_map(address,size)
    ranges=[(0x802db494,0x802db580),(0x8005caa0,0x8005cb34),(0x800f2ef0,0x800f2efc),(0x801651e0,0x801651ec),(0x801a2004,0x801a2010),(0x801a2054,0x801a205c)]
    for a,b in ranges:u.mem_write(a,image.read(a,b-a))
    u.mem_write(obj,struct.pack('>II',KIND,STRIDE)+record_bytes);u.mem_write(head,struct.pack('>II',head,head))
    def instruction(uc,address,size,unused):
        if not any(a<=address<b for a,b in ranges):raise ValueError(f'Preset consumer escaped:{address:08x}')
    def write(uc,access,address,size,value,unused):
        if not any(a<=address<address+size<=b for a,b in [(obj,obj+0x1000),(stack,stack+0x2000),(head,head+8)]):raise ValueError('Preset consumer wrote outside owned data')
    u.hook_add(UC_HOOK_CODE,instruction);u.hook_add(UC_HOOK_MEM_WRITE,write)
    u.reg_write(UC_PPC_REG_1,stack+0x1000);u.reg_write(UC_PPC_REG_3,obj);u.reg_write(UC_PPC_REG_LR,stop)
    u.emu_start(0x802db494,stop,count=200000,timeout=200000)
    if u.reg_read(UC_PPC_REG_PC)!=stop or u.reg_read(UC_PPC_REG_3)!=1:raise ValueError('Original preset loader failed')
    runtime=bytes(u.mem_read(obj+8,STRIDE))
    if runtime[0x50:0x58]!=record_bytes[0x50:0x58][::-1]:raise ValueError('Original key swap differs')
    results=[]
    for start,end,register in [(0x801651e0,0x801651ec,UC_PPC_REG_31),(0x801a2004,0x801a205c,UC_PPC_REG_30)]:
        u.reg_write(register,obj+8);u.emu_start(start,end,count=100,timeout=200000)
        result=dict(consumer_start=f'{start:08x}',collection_lookup_call=f'{end:08x}',class_key=f'{u.reg_read(UC_PPC_REG_3):08x}',collection_key=f'{u.reg_read(UC_PPC_REG_4):08x}')
        if u.reg_read(UC_PPC_REG_PC)!=end or u.reg_read(UC_PPC_REG_3)!=vlt_hash('pvehicle') or u.reg_read(UC_PPC_REG_4)!=expected_key:raise ValueError(('Original profile consumer mismatch',result))
        results.append(result)
    return dict(loader='802DB494',serialized_key_offset='50',runtime_key_read_offset='54',consumers=results)


def resolve(source,attributes,dol,preset_name):
    original=source.read_bytes();attr=attributes.read_bytes();image=DolImage(dol.read_bytes())
    if hashlib.sha256(attr).hexdigest()!=ATTR_SHA:raise ValueError('Attributes checksum')
    parsed=preset_report(original,image);matches=[r for r in parsed['records'] if r['preset_name']==preset_name]
    if len(matches)!=1:raise ValueError('Expected exactly one original preset')
    record=matches[0];keys=profile_keys(record);key=int(keys['pvehicle_collection_key'],16)
    db=VehicleAttributes(attr);physical=db.find('pvehicle',key);fields=db.fields(physical)
    raw=original[record['file_offset']:record['file_offset']+STRIDE]
    reference=verify_consumer(image,raw)
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,preset_source_sha256=hashlib.sha256(original).hexdigest(),
        preset=preset_name,preset_file_offset=record['file_offset'],preset_record_sha256=hashlib.sha256(raw).hexdigest(),visual_model=record['model_name'],
        **keys,physical_class='pvehicle',physical_collection=db.label(physical['key']),physical_model=fields['MODEL']['value'],original_reference=reference,
        physics_references={k:v for k,v in fields.items() if k in ['engine','transmission','tires','brakes','chassis','induction','frontend']},
        limitations=['Proves this original preset chooses the named pvehicle profile; it does not select arbitrary profiles by visualmodel','RefSpec upgrade indices still require their own original consumer rules','Source presets with zero profile keys take fallback behavior not covered here'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);p.add_argument('--dol',type=Path,required=True);p.add_argument('--preset',default='M3GTRCAREERSTART');p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=resolve(a.source,a.attributes,a.dol,a.preset);a.output.write_text(json.dumps(result,indent=2)+'\n');print(result['preset'],'->',result['physical_collection'],result['pvehicle_collection_key'])
