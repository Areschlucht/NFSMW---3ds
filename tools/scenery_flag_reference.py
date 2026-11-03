#!/usr/bin/env python3
"""Bounded original scalar scenery flag gates; no runtime policy is guessed.

The transform-changing path is detected and stopped before arithmetic. The
render-mask window is executed with explicit caller-supplied context flags.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256


def render_rejected(flags, context):
    return bool(((flags & 255) ^ 0x60) & context)


def transform_required(old, low):
    return bool(old & 0x00800000 and (old ^ low) & 0x400)


def draw_context_mask(flags, view_kind, game_state, profile_mode_one):
    result=flags|0x10
    if view_kind in (1,2):result|=2
    if game_state in (3,4):result|=1
    if 16<=view_kind<=21:result|=0x100
    if profile_mode_one:result|=4
    if result&0x1800:result|=0x40
    if result&0x1000:result|=2
    if view_kind==3:result|=0x20
    return result


class Reference:
    def __init__(self, raw):
        from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
        from unicorn import ppc_const as reg
        if hashlib.sha256(raw).hexdigest() != DOL_SHA256:
            raise ValueError('Unexpected USA executable')
        self.image = DolImage(raw)
        self.reg = reg
        self.uc = Uc(UC_ARCH_PPC, UC_MODE_32 | UC_MODE_BIG_ENDIAN)
        self.uc.mem_map(0x80000000, 0x1800000)
        for s in self.image.sections:
            self.uc.mem_write(s.address, raw[s.offset:s.offset+s.size])
        self.allowed = ()
        self.writes = ()
        self.stop = {}
        self.result = None
        def instruction(uc, address, size, _):
            if address in self.stop:
                self.result = self.stop[address]
                uc.emu_stop()
            elif not any(a <= address < b for a,b in self.allowed):
                raise ValueError(f'Execution escaped scalar window: {address:08x}')
        def write(uc, access, address, size, value, _):
            if not any(a <= address and address+size <= b for a,b in self.writes):
                raise ValueError(f'Write escaped instance: {address:08x}')
        self.uc.hook_add(UC_HOOK_CODE, instruction)
        self.uc.hook_add(UC_HOOK_MEM_WRITE, write)

    def run(self, start):
        self.result = None
        self.uc.emu_start(start, 0x817ffffc, count=1000, timeout=100000)
        if self.result is None:
            raise ValueError('Original execution budget exhausted')
        return self.result

    def render(self, flags, context):
        r=self.reg;u=self.uc
        # Exact original prefix window before geometry/model selection.
        for n,v in ((3,0x81600000),(28,0x81601000),(29,0x81602000)):
            u.reg_write(getattr(r,f'UC_PPC_REG_{n}'),v)
        u.mem_write(0x81600018,struct.pack('>I',0x81603000))
        u.mem_write(0x81601084,struct.pack('>I',context))
        u.mem_write(0x81602018,struct.pack('>I',flags))
        u.mem_write(0x8160203e,struct.pack('>h',0))
        self.allowed=((0x802beaa8,0x802beac8),)
        self.writes=()
        self.stop={0x802beac8:False,0x802bf250:True}
        return self.run(0x802beaa8)

    def apply(self, old, low):
        r=self.reg;u=self.uc
        for n,v in ((3,0x81600000),(4,0x81601000)):
            u.reg_write(getattr(r,f'UC_PPC_REG_{n}'),v)
        u.mem_write(0x81600000,struct.pack('>3H',0,0,low))
        u.mem_write(0x81601020,struct.pack('>I',0x81602000))
        u.mem_write(0x81602000,bytes(64))
        u.mem_write(0x81602018,struct.pack('>I',old))
        self.allowed=((0x802bccec,0x802bd028),)
        self.writes=((0x81602000,0x81602040),)
        self.stop={0x802bcd1c:'transform_branch',0x802bd028:'copied'}
        outcome=self.run(0x802bccec)
        flags=struct.unpack('>I',bytes(u.mem_read(0x81602018,4)))[0]
        return outcome,flags

    def context(self, flags, view_kind, game_state, profile_mode_one):
        r=self.reg;u=self.uc
        for n,v in ((3,0x81600000),(4,0x81601000),(5,flags)):
            u.reg_write(getattr(r,f'UC_PPC_REG_{n}'),v)
        u.mem_write(0x81600004,struct.pack('>I',view_kind))
        u.mem_write(0x8041aca0,struct.pack('>I',game_state))
        u.mem_write(0x8041d30c,struct.pack('>I',0x81604000 if profile_mode_one else 0))
        u.mem_write(0x81605aa4,struct.pack('>I',1 if profile_mode_one else 0))
        self.allowed=((0x800f4c08,0x800f4ca4),(0x800fe3e8,0x800fe3f4))
        self.writes=()
        self.stop={0x800f4ca4:'context_ready'}
        self.run(0x800f4c08)
        return u.reg_read(r.UC_PPC_REG_31)


def verify(raw):
    ref=Reference(raw);renders=0;copies=0;transforms=0;contexts=0
    # All low bytes against every low-byte draw context, plus actual LOD context
    # bits above the low byte. This does not identify the original mask producer.
    for flags in range(256):
        for context in (*range(256),0x800,0x1000,0x1800,0x1820):
            assert ref.render(flags,context)==render_rejected(flags,context)
            renders+=1
    for upper in (0,0x00800000,0x12340000,0xffff0000):
        for oldlow in (0,0x10,0x400,0x410,0xffff):
            for low in (0,1,0x10,0x400,0x410,0xffff):
                old=upper|oldlow
                outcome,new=ref.apply(old,low)
                if transform_required(old,low):
                    assert outcome=='transform_branch' and new==old
                    transforms+=1
                else:
                    assert outcome=='copied' and new==(old&0xffff0000)|low
                    copies+=1
    for flags in (0,0x10,0x20,0x800,0x1000,0x1800):
        for view in range(23):
            for state in range(5):
                for profile in (False,True):
                    expected=draw_context_mask(flags,view,state,profile)
                    assert ref.context(flags,view,state,profile)==expected
                    assert expected&0x10
                    contexts+=1
    ranges=[(0x802beaa8,0x802beac8),(0x802bccec,0x802bcd1c),(0x802bd014,0x802bd028),
            (0x800f4c08,0x800f4cb4)]
    return {'schema':1,'dol_sha256':DOL_SHA256,'render_mask_cases':renders,
            'unchanged_transform_copy_cases':copies,'transform_branch_cases':transforms,
            'original_context_builder_cases':contexts,
            'original_window_sha256':[{'start':f'{a:08x}','end_exclusive':f'{b:08x}',
                'sha256':hashlib.sha256(ref.image.read(a,b-a)).hexdigest()} for a,b in ranges],
            'render_formula':'reject iff (((instance_flags & 0xff) ^ 0x60) & draw_context_flags) != 0',
            'transform_gate':'old_flags & 0x00800000 and (old_flags ^ new_member_flags) & 0x400',
            'copy_formula':'(old_flags & 0xffff0000) | new_member_flags',
            'limits':['Context-builder inputs are explicit synthetic view/game/profile states; their live producers remain separate',
                'Transform-changing branch detected; arithmetic not executed or replaced',
                'Collision flag consumer/provider/event-state ordering remains unrecovered',
                'No runtime files or game input bytes changed']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dol',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=verify(a.dol.read_bytes())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('render_mask_cases','unchanged_transform_copy_cases','transform_branch_cases','original_context_builder_cases')}))
