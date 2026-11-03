#!/usr/bin/env python3
"""Capture original GC material-cache coefficient preparation in bounded PPC.

Original800F8E24..30 initializes material then800FB4D8→80109BB8.
This captures coefficients/state words, not their final TEV interpretation.
Entry skips paired-single ABI saves only; no arithmetic instruction is patched.
Exit precedes ABI restores. The code makes no external calls in this region.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from material_recovery_car_render import material_catalog
from material_recovery_vehicle import DOL_SHA256
from vehicle_dol import DolImage


class MaterialCacheReference:
    def __init__(self,image):
        if hashlib.sha256(image.data).hexdigest()!=DOL_SHA256:raise ValueError('Original GC material cache needs pinned USA DOL')
        from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ
        self.uc=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN);u=self.uc
        for va,size in ((0x80109000,0x2000),(0x803c8000,0xa0000),(0x90000000,0x3000),(0x91000000,0x2000)):u.mem_map(va,size)
        image.file_offset(0x80109c04,0x760,executable=True)
        u.mem_write(0x80109c04,image.read(0x80109c04,0x760))
        for s in image.sections:
            if s.name in ('data0','data1','data2'):u.mem_write(s.address,image.read(s.address,s.size))
        def instruction(uc,address,size,unused):
            if not 0x80109c04<=address<0x8010a364:raise ValueError('Original material cache escaped scalar region')
        def write(uc,access,address,size,value,unused):
            if not (0x90001000<=address<address+size<=0x90001058 or 0x91000000<=address<address+size<=0x91002000):
                raise ValueError('Original material cache wrote outside output/stack')
        u.hook_add(UC_HOOK_CODE,instruction);u.hook_add(UC_HOOK_MEM_WRITE,write)
        self.context_reads=set()
        def read(uc,access,address,size,value,unused):
            if 0x80415180<=address<0x80456560:self.context_reads.add((address,size))
        u.hook_add(UC_HOOK_MEM_READ,read)
        self.image=image

    def capture(self,record):
        from unicorn.ppc_const import UC_PPC_REG_1,UC_PPC_REG_3,UC_PPC_REG_MSR,UC_PPC_REG_PC
        if len(record)!=168:raise ValueError('Expected original168-byte material record')
        raw=bytearray(record)
        for offset in (12,16,*range(48,168,4)):raw[offset:offset+4]=raw[offset:offset+4][::-1]
        struct.pack_into('>I',raw,0,0x90001000)
        self.context_reads.clear()
        u=self.uc;u.mem_write(0x90000000,bytes(raw));u.mem_write(0x90001000,bytes(0x58));u.mem_write(0x91000000,bytes(0x2000))
        u.reg_write(UC_PPC_REG_1,0x91001000);u.reg_write(UC_PPC_REG_3,0x90000000);u.reg_write(UC_PPC_REG_MSR,0x2000)
        u.emu_start(0x80109c04,0x8010a364,timeout=100000,count=8192)
        if u.reg_read(UC_PPC_REG_PC)!=0x8010a364:raise ValueError('Original material cache exceeded bounds')
        return bytes(u.mem_read(0x90001000,0x58))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dol',type=Path);p.add_argument('materials',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();d=DolImage(a.dol.read_bytes());b=a.materials.read_bytes();ref=MaterialCacheReference(d);rows=[]
    for material in material_catalog(b).values():
        raw=ref.capture(bytes.fromhex(material['raw_record']))
        rows.append(dict(name=material['name'],key=material['key'],context_reads=[dict(address=f'{va:08x}',size=size,file_offset=d.file_offset(va,size),original_bytes=d.read(va,size).hex()) for va,size in sorted(ref.context_reads)],record_sha256=material['record_sha256'],cache_be_hex=raw.hex(),
            coefficient_words=[dict(offset=f'{o:02x}',float32=struct.unpack_from('>f',raw,o)[0],raw_hex=raw[o:o+4].hex()) for o in range(0,72,4)],
            state_words={f'{o:02x}':f'{struct.unpack_from(">I",raw,o)[0]:08x}' for o in (72,76,80,84)}))
    a.output.write_text(json.dumps(dict(dol_sha256=DOL_SHA256,source_sha256=hashlib.sha256(b).hexdigest(),
        routine='80109bb8',executed_start='80109c04',executed_end_exclusive='8010a364',
        code_sha256=hashlib.sha256(d.read(0x80109c04,0x760)).hexdigest(),records=rows,
        limitation='Captured original GC cache arithmetic using original executable data0/data1/data2 static defaults; final TEV field interpretation and dynamic state consumers are separate. No original instructions were replaced.'),indent=2)+'\n')
    print(f'Captured{len(rows)} original material caches')
