#!/usr/bin/env python3
"""Original event-type lookup with only attribute access supplied synthetically."""
import hashlib
import struct
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256


def original_table(raw):
    if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected USA DOL')
    im=DolImage(raw);rows=[]
    for i in range(11):
        address,kind=struct.unpack('>II',im.read(0x8041d31c+i*8,8));rows.append((im.c_string(address),kind))
    if len({n for n,k in rows})!=11 or len({k for n,k in rows})!=11:raise ValueError('Unexpected original table')
    return rows


class Original:
    def __init__(self,raw):
        from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
        from unicorn import ppc_const as r
        original_table(raw);self.im=DolImage(raw);self.r=r;self.u=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        self.u.mem_map(0x80000000,0x1800000)
        for s in self.im.sections:self.u.mem_write(s.address,raw[s.offset:s.offset+s.size])
        self.done=False
        def code(u,pc,size,data):
            if pc==0x80057250:
                if u.reg_read(r.UC_PPC_REG_4)!=0x0f6bcde1 or u.reg_read(r.UC_PPC_REG_LR)!=0x801a73ac:raise ValueError('Unexpected synthetic attribute request')
                u.reg_write(r.UC_PPC_REG_3,0x81601000);u.reg_write(r.UC_PPC_REG_PC,0x801a73ac)
            elif pc==0x801a73f4:self.done=True;u.emu_stop()
            elif not any(a<=pc<b for a,b in ((0x801a7398,0x801a73f4),(0x801a734c,0x801a7358),(0x80063034,0x80063098))):raise ValueError(f'Original lookup escaped: {pc:08x}')
        def write(u,access,address,size,value,data):raise ValueError('Unexpected lookup write')
        self.u.hook_add(UC_HOOK_CODE,code);self.u.hook_add(UC_HOOK_MEM_WRITE,write)
    def lookup(self,name):
        data=name.encode('ascii')
        if len(data)>255 or b'\0' in data:raise ValueError('Unexpected lookup string')
        u=self.u;r=self.r;self.done=False
        u.reg_write(r.UC_PPC_REG_31,0x81600000);u.mem_write(0x81600004,struct.pack('>I',0x81603000))
        u.mem_write(0x81601000,struct.pack('>I',0x81602000));u.mem_write(0x81602000,data+b'\0')
        u.emu_start(0x801a7398,0x817ffffc,count=20000,timeout=100000)
        if not self.done:raise ValueError('Original lookup budget exhausted')
        value=u.reg_read(r.UC_PPC_REG_3);return value-(1<<32) if value&(1<<31) else value
