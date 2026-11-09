#!/usr/bin/env python3
"""Bounded original trigger constructor parameter windows, not a gate detector.

Preserves original geometry permutations/scales without guessing containment,
full/half extents, crossing direction, vehicle shape or progression semantics.
"""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import struct
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256


def f32(x):return struct.unpack('>f',struct.pack('>f',x))[0]
def bits(x):return struct.pack('>f',x)
_libm=ctypes.CDLL('libm.so.6');_fma=_libm.fmaf
_fma.argtypes=[ctypes.c_float]*3;_fma.restype=ctypes.c_float


def constructor_parameters(position,dimensions,rotation):
    if len(position)!=3 or len(dimensions)!=3 or not all(math.isfinite(x) for x in (*position,*dimensions,rotation)):
        raise ValueError('Expected finite source spatial fields')
    p=tuple(f32(x) for x in position);d=tuple(f32(x) for x in dimensions)
    x=f32(d[0]*.25);xx=f32(d[0]*x);y=f32(d[1]*.25)
    return {'shape_position':[-p[1],p[2],p[0]],'shape_dimension_parameters':[d[1],d[2],d[0]],
            'negative_rotation_turns':f32(-f32(rotation)*f32(1/360)),
            'box_sqrt_operand':_fma(d[1],y,xx)}


class Reference:
    def __init__(self,raw):
        from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
        from unicorn import ppc_const as r
        if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected USA DOL')
        self.image=DolImage(raw);self.r=r;self.u=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        self.u.mem_map(0x80000000,0x1800000)
        for s in self.image.sections:self.u.mem_write(s.address,raw[s.offset:s.offset+s.size])
        self.allowed=(0,0);self.writes=();self.stop=0;self.stopped=False
        def code(u,address,size,_):
            if address==self.stop:self.stopped=True;u.emu_stop()
            elif not self.allowed[0]<=address<self.allowed[1]:raise ValueError('Original execution escaped window')
        def write(u,access,address,size,value,_):
            if not any(a<=address and address+size<=b for a,b in self.writes):raise ValueError('Original write escaped allowed stack')
        self.u.hook_add(UC_HOOK_CODE,code);self.u.hook_add(UC_HOOK_MEM_WRITE,write)
    def reg(self,n,value):self.u.reg_write(getattr(self.r,f'UC_PPC_REG_{n}'),value)
    def run(self,a,b):
        self.allowed=(a,b);self.stop=b;self.stopped=False
        self.u.reg_write(self.r.UC_PPC_REG_MSR,0x2000)
        self.u.emu_start(a,0x817ffffc,count=300,timeout=100000)
        if not self.stopped:raise ValueError('Original window exhausted budget')
    def fp(self,n):return struct.unpack('>d',struct.pack('>Q',self.u.reg_read(self.r.UC_PPC_REG_FPR0+n)))[0]
    def notification_mode(self,mode):
        self.reg(5,mode&0xffffffff);self.reg(27,0x81604000);self.writes=()
        self.run(0x8019b980,0x8019b99c)
        return bool(self.u.reg_read(self.r.UC_PPC_REG_28)),bool(self.u.reg_read(self.r.UC_PPC_REG_30))
    def constructor(self,position,dimensions,rotation):
        u=self.u;stack=0x81600000;source=0x81601000;obj=0x81602000
        self.reg(1,stack);self.reg(28,source);self.reg(31,obj);self.reg(27,0x81603000)
        u.mem_write(stack,bytes(256));u.mem_write(source,struct.pack('>3f',*position));u.mem_write(stack+0x10,struct.pack('>3f',*dimensions))
        self.writes=((stack,stack+256),(obj+0x38,obj+0x3c))
        self.run(0x8019ab18,0x8019aba0)
        pos=struct.unpack('>3f',bytes(u.mem_read(stack+0x20,12)))
        dim=struct.unpack('>3f',bytes(u.mem_read(stack+0x30,12)))
        self.run(0x8019ac68,0x8019ac98)
        radius_operand=self.fp(1)
        self.reg(3,source);u.mem_write(source,struct.pack('>f',rotation))
        self.run(0x8019ad7c,0x8019ad94)
        return {'shape_position':list(pos),'shape_dimension_parameters':list(dim),
                'negative_rotation_turns':self.fp(1),'box_sqrt_operand':radius_operand}


def verify(raw,catalog):
    ref=Reference(raw);cases=[];seen=set()
    for row in catalog['race_definition_candidates']:
        for field in ('ordered_checkpoint_refs','startgrid_ref','finishline_ref'):
            for node in row.get(field,{}).get('nodes',[]):
                spatial=node.get('spatial_fields',{});d=spatial.get('Dimensions',spatial.get('0x6d9e21ad'))
                if 'Position' not in spatial or 'Rotation' not in spatial or d is None:continue
                args=tuple(spatial['Position']['value']),tuple(d['value']),spatial['Rotation']['value']
                if args in seen:continue
                seen.add(args);cases.append((node['key'],args))
    for i,(p,d,a) in enumerate([((1,2,3),(2,40,40),0),((-100,50,25),(1,2,3),90),((0,0,0),(80,20,10),-180),((1,-0.,-3),(0,0,0),360)]):
        cases.append((f'synthetic{i}',(p,d,a)))
    for _,args in cases:
        expected=constructor_parameters(*args);actual=ref.constructor(*args)
        for k in expected:
            a=actual[k] if isinstance(actual[k],list) else [actual[k]];b=expected[k] if isinstance(expected[k],list) else [expected[k]]
            if [bits(x) for x in a]!=[bits(x) for x in b]:raise AssertionError((k,args,actual,expected))
    modes=(*range(256),0xffffffff,0x80000000,0x10001,0x10002)
    for mode in modes:
        assert ref.notification_mode(mode)==(mode==1,mode==2)
    ranges=((0x8019b980,0x8019b99c),(0x8019ab18,0x8019aba0),(0x8019ac68,0x8019ac98),(0x8019ad7c,0x8019ad94))
    return {'schema':1,'dol_sha256':DOL_SHA256,'constructor_cases_matched':len(cases),
        'source_spatial_cases':len(seen),'notification_mode_cases':len(modes),'windows':[{'start':f'{a:08x}','end_exclusive':f'{b:08x}','sha256':hashlib.sha256(ref.image.read(a,b-a)).hexdigest()} for a,b in ranges],
        'formulas':constructor_parameters((1,2,3),(2,40,40),90),
        'limits':['Source Dimensions are retained as parameters, not assigned guessed full/half extent semantics',
            'Radius field wins before Dimensions branch; this reference only verifies the Dimensions branch',
            'Point/segment containment, direction, vehicle shape and activation/event ordering remain unrecovered',
            'No runtime code, original input, SDK build or game release changed']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dol','catalog','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=verify(a.dol.read_bytes(),json.loads(a.catalog.read_text()))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
