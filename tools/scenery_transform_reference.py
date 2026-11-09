#!/usr/bin/env python3
"""Bounded original 0x0400 scenery transform transition, not an event scheduler.

Source records are little endian; the executable's loaded instances are big
endian. The reference runs unchanged original bytes, with existing explicit
Gekko paired-single hooks. No game inputs or runtime files are modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256


def source_to_native(raw):
    if len(raw)!=64:raise ValueError('Expected one complete source instance')
    return b''.join(raw[i:i+4][::-1] for i in range(0,44,4))+b''.join(raw[i:i+2][::-1] for i in range(44,64,2))


def apply_source(raw, new_low_flags):
    """Portable equivalent on a complete source-format 64-byte record."""
    if len(raw)!=64 or not isinstance(new_low_flags,int) or not 0<=new_low_flags<=65535:
        raise ValueError('Complete source instance and uint16 flags required')
    out=bytearray(raw);old=struct.unpack_from('<I',raw,24)[0]
    if old&0x00800000 and (old^new_low_flags)&0x400:
        for at in (44,46,48):
            value=struct.unpack_from('<H',raw,at)[0]
            struct.pack_into('<H',out,at,(-value)&0xffff)
    struct.pack_into('<I',out,24,(old&0xffff0000)|new_low_flags)
    return bytes(out)


class Reference:
    def __init__(self, raw):
        from map_recovery_contact_reference import OriginalContactReference
        from unicorn import UC_HOOK_MEM_WRITE
        from unicorn import ppc_const as r
        if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected USA executable')
        self.image=DolImage(raw);self.ref=OriginalContactReference(raw,None);self.u=self.ref.u;self.r=r
        # Startup801? is not guessed: the entry bytes directly establish r13.
        if self.image.read(0x80003110,8)!=bytes.fromhex('3da0805061ad6dc0'):
            raise ValueError('Unexpected original SDA-base initialization')
        self.ref.extra_allowed=((0x802bccec,0x802bd028),(0x80329e28,0x80329e5c),
            (0x80329ea0,0x80329fa4),(0x8005e024,0x8005e050),(0x8010ab28,0x8010ab58))
        def write(u,access,address,size,value,data):
            if not ((0x7000f000<=address and address+size<=0x70010000) or
                    (0x60002000<=address and address+size<=0x60002040)):
                raise ValueError(f'Original write escaped stack/instance: {address:08x}')
        self.u.hook_add(UC_HOOK_MEM_WRITE,write)
    def apply(self, source, flags):
        if not 0<=flags<=65535:raise ValueError('Expected uint16 group-member flags')
        u=self.u;r=self.r
        u.mem_write(0x60002000,source_to_native(source))
        u.mem_write(0x60000000,struct.pack('>3H',0,0,flags))
        u.mem_write(0x60001020,struct.pack('>I',0x60002000))
        u.mem_write(0x7000f000,bytes(4096))
        for n,v in ((1,0x7000ff00),(3,0x60000000),(4,0x60001000),(13,0x80506dc0)):
            u.reg_write(r.UC_PPC_REG_0+n,v)
        self.ref.pair1={};self.ref.instructions=0
        u.emu_start(0x802bccec,0x802bd028,count=5000,timeout=100000)
        if u.reg_read(r.UC_PPC_REG_PC)!=0x802bd028:raise ValueError('Original execution budget exhausted')
        return source_to_native(bytes(u.mem_read(0x60002000,64)))


def verify(dol, plan, stream, max_source_cases=1024):
    ref=Reference(dol);unique={};occurrences=0
    with stream.open('rb') as f:
        for row in plan['instances']:
            f.seek(row['source_instance_offset']);source=f.read(64)
            if hashlib.sha256(source).hexdigest()!=row['source_instance_sha256']:
                raise ValueError('Source instance differs from verified plan')
            old=struct.unpack_from('<I',source,24)[0]
            if old!=row['original_flags']:raise ValueError('Source flag differs from plan')
            if old&0x00800000:
                occurrences+=1;unique.setdefault(struct.unpack_from('<9h',source,44),source)
    keys=sorted(unique)
    if not keys or max_source_cases<1:raise ValueError('No supported source cases requested')
    take=min(max_source_cases,len(keys))
    chosen=[keys[i*(len(keys)-1)//max(take-1,1)] for i in range(take)]
    source_cases=0;synthetic_cases=0
    def check(source, low):
        expected=apply_source(source,low);actual=ref.apply(source,low)
        if actual!=expected:raise AssertionError({'flags':low,'source':source.hex(),'actual':actual.hex(),'expected':expected.hex()})
        return actual
    for key in chosen:
        source=unique[key];flags=struct.unpack_from('<I',source,24)[0]
        target=(flags&65535)^0x400
        changed=check(source,target);source_cases+=1
        if check(changed,flags&65535)!=source:raise AssertionError('Original toggle does not roundtrip')
        source_cases+=1
    # Full int16 boundaries and distinct lanes, including wrapping -32768.
    edges=(-32768,-32767,-8192,-1,0,1,8192,32767)
    for value in edges:
        for lane in range(3):
            for eligible in (False,True):
                for initially_set in (False,True):
                    source=bytearray(64);old=(0x00800000 if eligible else 0)|0x8070|(0x400 if initially_set else 0)
                    struct.pack_into('<I',source,24,old);struct.pack_into('<3f',source,32,1.25,-2.5,3.75)
                    matrix=[1,2,3,4,5,6,7,8,9];matrix[lane]=value;struct.pack_into('<9h',source,44,*matrix)
                    check(bytes(source),(old&65535)^0x400);synthetic_cases+=1
    for source,low in ((bytes(63),0),(bytes(64),65536)):
        try:apply_source(source,low)
        except ValueError:pass
        else:raise AssertionError('Malformed portable input accepted')
    windows=((0x802bccec,0x802bd028),(0x80329e28,0x80329e5c),(0x80329ea0,0x80329fa4),
             (0x8005e024,0x8005e050),(0x8010ab28,0x8010ab58))
    return {'schema':1,'dol_sha256':DOL_SHA256,'eligible_source_occurrences':occurrences,
        'unique_eligible_source_matrices':len(unique),'source_matrices_sampled':take,
        'source_original_queries':source_cases,'synthetic_original_queries':synthetic_cases,
        'total_original_queries':source_cases+synthetic_cases,
        'transform_condition':'old_flags & 0x00800000 and (old_flags ^ new_low_flags) & 0x400',
        'matrix_operation':'Negate only int16 source entries at offsets44,46,48, preserving low16 wrapping',
        'unmodified_ranges_excluding_flag_word':['0..23','28..43','50..63'],
        'code_windows':[{'start':f'{a:08x}','end_exclusive':f'{b:08x}','sha256':hashlib.sha256(ref.image.read(a,b-a)).hexdigest()} for a,b in windows],
        'limits':['This is the exact bounded transform/flag consumer, not an event activation scheduler',
            'Existing paired hooks have documented general floating limitations; this verified diagonal reflection uses dyadic operations',
            'No collision state, group ordering, renderer or shared runtime file is changed by this tool',
            'Source matrices are sampled deterministically across sorted unique source matrices; count is explicit']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dol','plan','stream','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--max-source-cases',type=int,default=1024)
    a=p.parse_args();result=verify(a.dol.read_bytes(),json.loads(a.plan.read_text()),a.stream,a.max_source_cases)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
