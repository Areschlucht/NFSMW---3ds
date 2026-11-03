#!/usr/bin/env python3
"""Bounded original GC model texture-fixup/lookup miss-policy reference.

Executes unmodified original fixup, cache lookup,17render-target scan and empty
streaming-alias scan. Registry state is explicit test input, not a claim about
all possible live gameplay-generated resources. No fallback image is invented.
"""
import hashlib
import struct
from material_recovery_vehicle import DOL_SHA256,uint32


class OriginalTextureLookup:
    FALLBACK=0x90001000
    MODEL=0x90003000
    REFS=0x90004000
    STOP=0x81600000
    STACK=0x817ff000

    def __init__(self,image,known=()):
        if hashlib.sha256(image.data).hexdigest()!=DOL_SHA256:raise ValueError('Texture lookup reference requires pinned USA DOL')
        from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
        from unicorn.ppc_const import UC_PPC_REG_PC
        u=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN);self.uc=u;self.image=image
        u.mem_map(0x80000000,0x600000);u.mem_map(0x90000000,0x10000);u.mem_map(self.STOP,0x1000);u.mem_map(0x817fe000,0x2000)
        for s in image.sections:u.mem_write(s.address,image.read(s.address,s.size))
        self.allowed=((0x800f6e10,0x800f6e98),(0x800fd4a0,0x800fd624),(0x800ffc04,0x800ffc70),(0x800ffeac,0x800ffec0),(0x800f4ccc,0x800f4d20))
        def code(uc,address,size,unused):
            if not any(a<=address<b for a,b in self.allowed):raise ValueError(f'Lookup escaped original boundedfunctions at{address:08x}')
        def write(uc,access,address,size,value,unused):
            if not (0x817fe000<=address<address+size<=0x81800000 or self.REFS<=address<address+size<=self.REFS+2048):
                raise ValueError(f'Unexpected originallookup write at{address:08x}')
        u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
        # Empty regular-bank list, cache and streaming-alias registry are
        # explicit absence inputs. Registered default is the observed resource.
        head=0x8046284c;u.mem_write(head,struct.pack('>2I',head,head))
        u.mem_write(0x8046b20c,bytes(1024));u.mem_write(0x8041a5e0,bytes(4));u.mem_write(0x8041e650,bytes(4))
        u.mem_write(0x8041ab74,struct.pack('>I',self.FALLBACK));u.mem_write(self.FALLBACK+0x24,struct.pack('>I',0x66994f4a))
        # Index17standard render-target descriptors, with no matching target
        # hash registered. Actual original scanner is used without stubs.
        u.mem_write(0x80465988,bytes(17*124))
        for i in range(17):u.mem_write(0x8046bac4+i*64,struct.pack('>I',i))
        self.known={};buckets={}
        for i,key in enumerate(known):
            uint32(key);bucket=key&255
            if bucket in buckets:raise ValueError('Reference fixture cache bucket collision requires a real source-bank fixture')
            pointer=0x90006000+i*128
            if pointer+128>0x90010000:raise ValueError('Known resource fixture exceeds bound')
            u.mem_write(pointer+0x24,struct.pack('>I',key));u.mem_write(0x8046b20c+4*bucket,struct.pack('>I',pointer))
            self.known[key]=pointer;buckets[bucket]=key

    def _call(self,start,key,r4=0,r5=0):
        from unicorn.ppc_const import UC_PPC_REG_1,UC_PPC_REG_3,UC_PPC_REG_4,UC_PPC_REG_5,UC_PPC_REG_LR,UC_PPC_REG_PC
        u=self.uc;u.reg_write(UC_PPC_REG_1,self.STACK);u.reg_write(UC_PPC_REG_3,key);u.reg_write(UC_PPC_REG_4,r4);u.reg_write(UC_PPC_REG_5,r5);u.reg_write(UC_PPC_REG_LR,self.STOP)
        u.emu_start(start,self.STOP,timeout=200000,count=100000)
        if u.reg_read(UC_PPC_REG_PC)!=self.STOP:raise ValueError('Original lookup exceeded executionbound')
        return u.reg_read(UC_PPC_REG_3)

    def lookup(self,key,fallback):
        uint32(key)
        return self._call(0x800fd4a0,key,int(bool(fallback)))

    def bind_model(self,keys):
        if not 0<len(keys)<128:raise ValueError('Model texture reference count exceeds signedbyte')
        for key in keys:uint32(key)
        u=self.uc;u.mem_write(self.MODEL,bytes(128));u.mem_write(self.MODEL+0x19,bytes([len(keys)]));u.mem_write(self.MODEL+0x2c,struct.pack('>I',self.REFS))
        u.mem_write(self.REFS,b''.join(struct.pack('>2I',key,0) for key in keys))
        self._call(0x800f6e10,self.MODEL)
        return [struct.unpack('>I',u.mem_read(self.REFS+i*8+4,4))[0] for i in range(len(keys))]


def verify(image,requested,known=(),model_keys=()):
    """Return exact original pointer comparisons for explicit registry inputs."""
    reference=OriginalTextureLookup(image,known)
    cases=[]
    for key in requested:
        for enabled in (False,True):
            actual=reference.lookup(key,enabled)
            expected=reference.known.get(key,reference.FALLBACK if enabled else 0)
            if actual!=expected:raise ValueError(f'Original lookup result mismatch for {key:08x}')
            cases.append(dict(requested_hash=f'{key:08x}',fallback_enabled=enabled,
                returned_pointer=f'{actual:08x}',matched=True))
    bound=[]
    if model_keys:
        actual=reference.bind_model(model_keys)
        for key,pointer in zip(model_keys,actual):
            if pointer!=reference.known.get(key,reference.FALLBACK):
                raise ValueError(f'Original model fixup mismatch for {key:08x}')
            bound.append(dict(requested_hash=f'{key:08x}',returned_pointer=f'{pointer:08x}',matched=True))
    return dict(dol_sha256=hashlib.sha256(image.data).hexdigest(),
        original_lookup='800fd4a0',original_model_fixup='800f6e10',
        effective_fallback_hash='66994f4a',fallback_registration='800fc670..800fc688',
        original_fallback_global='8041ab74',known_cache_hashes=[f'{k:08x}' for k in known],
        registry_assumptions=dict(ordinary_bank_list='empty',render_target_matching_keys=0,
            streaming_alias_count=0,model_fixup_guard=0,registered_default='66994f4a'),
        limitation='Final-miss policy under these explicit registry inputs; live runtime aliases and regular providers take precedence.',
        direct_lookup_cases=cases,model_fixup_cases=bound)


if __name__=='__main__':
    import argparse
    import json
    from pathlib import Path
    from vehicle_dol import DolImage
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dol',type=Path,required=True)
    parser.add_argument('--requested',nargs='+',required=True,type=lambda s:int(s,16))
    parser.add_argument('--known',nargs='*',default=[],type=lambda s:int(s,16))
    parser.add_argument('--model-keys',nargs='*',default=[],type=lambda s:int(s,16))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=verify(DolImage(args.dol.read_bytes()),args.requested,args.known,args.model_keys)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(f"Matched {len(report['direct_lookup_cases'])} direct lookups and {len(report['model_fixup_cases'])} model references")
