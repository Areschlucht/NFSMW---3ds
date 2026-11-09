#!/usr/bin/env python3
"""Bounded USA GameCube tutorial selector and story-flow consumer evidence.

This does not treat source IntroMovie/OutroMovie fields as proven playback
instructions. Explicit synthetic dependencies are stopped/stubbed, not emulated
as a complete movie system or career state machine.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256

TUTORIALS={2:(0x40,0x803eeb9c,'drag_tutorial'),
           5:(0x80,0x803eebac,'speedtrap_tutorial'),
           4:(0x100,0x803eebc0,'tollbooth_tutorial')}


def selector(event_type, profile_flags):
    row=TUTORIALS.get(event_type)
    if row is None or profile_flags&row[0]:
        return 0,profile_flags
    return row[1],profile_flags|row[0]


def direct_calls(image,target):
    result=[]
    for section in image.sections:
        if not section.name.startswith('text'):
            continue
        for offset in range(section.offset,section.offset+section.size-3,4):
            word=struct.unpack_from('>I',image.data,offset)[0]
            if word>>26!=18 or word&2 or not word&1:
                continue
            displacement=word&0x03fffffc
            if displacement&0x02000000:
                displacement-=0x04000000
            address=section.address+offset-section.offset
            if (address+displacement)&0xffffffff==target:
                result.append(f'{address:08x}')
    return result


class Original:
    def __init__(self,raw):
        from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
        from unicorn import ppc_const as reg
        if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:
            raise ValueError('Unexpected USA DOL')
        self.image=DolImage(raw);self.reg=reg
        self.uc=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        self.uc.mem_map(0x80000000,0x1800000)
        for section in self.image.sections:
            self.uc.mem_write(section.address,raw[section.offset:section.offset+section.size])
        self.done=False;self.event_type=0
        def instruction(uc,address,size,user):
            if address==0x801a7320:
                if uc.reg_read(reg.UC_PPC_REG_LR)!=0x801c6690:
                    raise ValueError('Unexpected synthetic event-type call origin')
                uc.reg_write(reg.UC_PPC_REG_3,self.event_type&0xffffffff)
                uc.reg_write(reg.UC_PPC_REG_PC,0x801c6690)
            elif address==0x801c6710:
                self.done=True;uc.emu_stop()
            elif not 0x801c6688<=address<0x801c6710:
                raise ValueError(f'Execution escaped tutorial selector: {address:08x}')
        def write(uc,access,address,size,value,user):
            if address!=0x816000e8 or size!=4:
                raise ValueError('Unexpected original tutorial selector write')
        self.uc.hook_add(UC_HOOK_CODE,instruction)
        self.uc.hook_add(UC_HOOK_MEM_WRITE,write)

    def tutorial(self,event_type,profile_flags):
        u=self.uc;r=self.reg;self.event_type=event_type;self.done=False
        u.reg_write(r.UC_PPC_REG_0,0x81601000)
        u.reg_write(r.UC_PPC_REG_30,0x81600000)
        u.reg_write(r.UC_PPC_REG_31,0)
        u.mem_write(0x816000e8,struct.pack('>I',profile_flags))
        u.emu_start(0x801c6688,0x801c6710,count=100,timeout=100000)
        if not self.done:
            # Unicorn can finish naturally on end address without executing hook.
            if u.reg_read(r.UC_PPC_REG_PC)!=0x801c6710:
                raise ValueError('Original selector execution budget exhausted')
        return (u.reg_read(r.UC_PPC_REG_31),
                struct.unpack('>I',bytes(u.mem_read(0x816000e8,4)))[0])


def recover(raw):
    original=Original(raw);image=original.image
    for _,address,text in TUTORIALS.values():
        if image.c_string(address)!=text:
            raise ValueError('Original tutorial string mismatch')
    cases=0
    for event in range(-2,13):
        for bits in range(8):
            low=((bits&1)*0x40)|((bits&2)*0x40)|((bits&4)*0x40)
            for unrelated in (0,0x1,0xfffffe3f,0x80000000):
                flags=low|unrelated
                actual=original.tutorial(event,flags)
                expected=selector(event,flags)
                if actual!=expected:
                    raise AssertionError((event,flags,actual,expected))
                # Marking the once bit suppresses the same selection next time.
                if actual[0] and original.tutorial(event,actual[1])[0]!=0:
                    raise AssertionError('Tutorial repeats after source once bit')
                cases+=1
    fields=[0xf572ede8,0xb70268c0,0x64273c71]
    xrefs=image.constant_xrefs(fields)
    ranges=[(0x801c65e8,0x801c6784),(0x8017f9a8,0x8017fa0c),
            (0x8019f3a8,0x8019f460),(0x8015bbc0,0x8015bc4c),
            (0x8015c13c,0x8015c1e4)]
    return {'schema':1,'dol_sha256':DOL_SHA256,'original_tutorial_selector_cases':cases,
        'tutorials':[{'event_type':event,'profile_once_mask':f'{mask:08x}',
                      'stem_address':f'{address:08x}','stem':text}
                     for event,(mask,address,text) in sorted(TUTORIALS.items())],
        'original_code_ranges':[{'begin':f'{a:08x}','end_exclusive':f'{b:08x}',
             'sha256':hashlib.sha256(image.read(a,b-a)).hexdigest()} for a,b in ranges],
        'field_constant_xrefs':[{k:f'{v:08x}' if k!='register' else v for k,v in row.items()} for row in xrefs],
        'movie_finished_constructor':'8017f9a8',
        'movie_finished_constructor_call_sites':direct_calls(image,0x8017f9a8),
        'linked_field_nonzero_test':{'field_hash':'64273c71','lookup':'8019f400..8019f40c',
            'zero_branch':'8019f42c','nonzero_branch':'8019f438',
            'limitation':'This test is in cleanup and does not assign the target key as a next active event'},
        'tutorial_preconditions':[
            'global manager at8041d30c must be non-null',
            'global word8041ed94 must be zero',
            'manager+1aa8 must equal2',
            'local-player interface lookup8003cb4c(1) must be non-null',
            'current event manager+1aac must be non-null'],
        'no_selected_tutorial_path':'801c6734..801c676c constructs and dispatches MNotifyMovieFinished immediately',
        'limits':['Only the tutorial selector window was executed; event-type getter is explicitly stubbed',
            'No direct IntroMovie/OutroMovie hash references found by conservative scan; this is not proof of absence or dead fields',
            'MNotifyMovieFinished construction/dispatch does not establish completed, skipped or failed playback distinctions',
            'Career intro/outro ordering, playback skip policy and linked-event success conditions remain unrecovered',
            'No runtime input, SDK build, source asset or game logic was changed']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dol',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();result=recover(a.dol.read_bytes())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'original_tutorial_selector_cases':result['original_tutorial_selector_cases'],
                      'movie_finished_constructor_call_sites':result['movie_finished_constructor_call_sites']}))
