#!/usr/bin/env python3
"""Bounded original trigger extents and box/box narrowphase reference.

Synthetic actor OBB inputs are not the recovered vehicle shape provider. Shared
Gekko hooks model paired arithmetic with binary64 intermediates rounded to f32;
exact fused ties/FPSCR/subnormals are outside scope. No original bytes patched.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import struct
from race_trigger_reference import Reference as ScalarReference
from vehicle_ppc_reference import DOL_SHA256


def f32(x):return struct.unpack('>f',struct.pack('>f',x))[0]

def source_half_extents(dimensions):
    if len(dimensions)!=3 or not all(math.isfinite(x) for x in dimensions):
        raise ValueError('Finite source Dimensions required')
    dx,dy,dz=map(f32,dimensions)
    return [f32(dy*.5),f32(f32(dz+dz)*.5),f32(dx*.5)]


class ExtentsReference(ScalarReference):
    def half_extents(self,dimensions):
        from unicorn.ppc_const import UC_PPC_REG_FPR0
        dx,dy,dz=map(f32,dimensions);u=self.u;stack=0x81600000
        self.reg(1,stack);self.reg(9,stack+0x178)
        for n in (0,11,29,30):self.reg(n,0)
        u.mem_write(stack,bytes(512))
        for n,value in ((0,.5),(6,1),(10,dx),(11,0),(12,dy),(13,f32(dz+dz))):
            u.reg_write(UC_PPC_REG_FPR0+n,struct.unpack('>Q',struct.pack('>d',value))[0])
        self.writes=((stack+0x154,stack+0x194),)
        self.run(0x80306884,0x803068cc)
        return list(struct.unpack('>3f',bytes(u.mem_read(stack+0x188,12))))


class BoxReference:
    def __init__(self,raw):
        from map_recovery_contact_reference import OriginalContactReference
        from unicorn import UC_HOOK_MEM_WRITE
        from unicorn import ppc_const as r
        if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected USA DOL')
        self.ref=OriginalContactReference(raw,None);self.u=self.ref.u;self.r=r
        self.ref.extra_allowed=((0x80089320,0x80089d50),(0x8008a630,0x8008a6ac),
                                (0x801930c8,0x80193420))
        def guard(u,access,address,size,value,_):
            if not ((0x60002000<=address and address+size<=0x60002500) or
                    (0x7000f000<=address and address+size<=0x70010000)):
                raise ValueError('Original write escaped output/stack')
        self.u.hook_add(UC_HOOK_MEM_WRITE,guard)
        self.u.mem_write(0x60001300,bytes(16))

    def call(self,address,args):
        u=self.u;r=self.r
        for i,value in enumerate(args,3):u.reg_write(r.UC_PPC_REG_0+i,value)
        u.reg_write(r.UC_PPC_REG_1,0x7000ff00);u.reg_write(r.UC_PPC_REG_LR,0x6000fff0)
        self.ref.instructions=0
        u.emu_start(address,0x6000fff0,count=100000,timeout=200000)
        if u.reg_read(r.UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Original query budget exhausted')
        return u.reg_read(r.UC_PPC_REG_3)

    def query(self,first,second):
        for target,(center,half,yaw) in zip((0x60002000,0x60002200),(first,second)):
            if len(center)!=3 or len(half)!=3 or not all(math.isfinite(x) for x in (*center,*half,yaw)) or any(x<=0 for x in half):
                raise ValueError('Finite center, positive synthetic halfextents, yaw required')
            c=f32(math.cos(yaw));s=f32(math.sin(yaw))
            matrix=(c,0,-s,0,0,1,0,0,s,0,c,0,0,0,0,1)
            self.u.mem_write(0x60001000,struct.pack('>16f',*matrix))
            self.u.mem_write(0x60001100,struct.pack('>3f',*center))
            self.u.mem_write(0x60001200,struct.pack('>3f',*half))
            self.call(0x80089320,[target,0x60001000,0x60001100,0x60001200,1,0x60001300])
        return bool(self.call(0x8008a630,[0x60002000,0x60002200,0x60002400]))


def verify(raw,catalog):
    scalar=ExtentsReference(raw);dimensions=set()
    for row in catalog['race_definition_candidates']:
        for field in ('ordered_checkpoint_refs','startgrid_ref','finishline_ref'):
            for node in row.get(field,{}).get('nodes',[]):
                values=node.get('spatial_fields',{});value=values.get('Dimensions',values.get('0x6d9e21ad'))
                if value:dimensions.add(tuple(value['value']))
    source_dimensions=len(dimensions)
    dimensions.update(((2,60,40),(1,2,3),(0,0,0),(-2,-4,-8)))
    for d in sorted(dimensions):
        actual=scalar.half_extents(d);expected=source_half_extents(d)
        if struct.pack('>3f',*actual)!=struct.pack('>3f',*expected):raise AssertionError((d,actual,expected))
    box=BoxReference(raw);cases=[];mismatches=[]
    # Independent AABB oracle: exact dyadic values avoid boundary/FMA ambiguity.
    randomizer=random.Random(0x19a8d8)
    for _ in range(160):
        a=tuple(randomizer.randrange(-16,17)*.5 for _ in range(3))
        b=tuple(randomizer.randrange(-16,17)*.5 for _ in range(3))
        ah=tuple(randomizer.randrange(1,9)*.5 for _ in range(3))
        bh=tuple(randomizer.randrange(1,9)*.5 for _ in range(3))
        expected=all(abs(x-y)<=h+k for x,y,h,k in zip(a,b,ah,bh))
        actual=box.query((a,ah,0),(b,bh,0))
        if actual!=expected:mismatches.append({'first_center':a,'second_center':b,'first_half':ah,'second_half':bh,'modeled_original':actual,'geometric_aabb_oracle':expected})
        cases.append(actual)
    boundary=[]
    for axis in range(3):
        for delta in (-.125,0,.125):
            center=[0,0,0];center[axis]=2+delta
            actual=box.query(((0,0,0),(1,1,1),0),(center,(1,1,1),0))
            if actual!=(delta<=0):raise AssertionError('Unexpected original touching rule')
            boundary.append({'axis':axis,'center_axis':2+delta,'overlap':actual})
    # Generic rotated calls: symmetry is useful evidence, not a complete SAT port.
    rotated=0;asymmetric=[]
    for i in range(24):
        a=((0,0,0),(2,.5,1),i*math.pi/12)
        b=((3,0,0),(1,1,1),-i*math.pi/16)
        forward=box.query(a,b);reverse=box.query(b,a)
        if forward!=reverse:asymmetric.append({'case':i,'forward':forward,'reverse':reverse})
        rotated+=1
    image=scalar.image
    ranges=((0x80306884,0x803068cc),(0x8030654c,0x80306914),
            (0x80089320,0x80089658),(0x80089658,0x80089d50),
            (0x8008a630,0x8008a6ac),(0x801d93d0,0x801d94a8))
    return {'schema':1,'dol_sha256':DOL_SHA256,'distinct_source_dimensions':source_dimensions,
            'extents_cases':len(dimensions),'axis_aligned_oracle_cases':len(cases),
            'axis_aligned_hits':sum(cases),'geometric_aabb_mismatches':mismatches,'touching_boundary_cases':boundary,
            'rotated_symmetry_pairs':rotated,'rotated_asymmetries':asymmetric,
            'source_dimensions_to_internal_halfextents':'(sourceDy/2, sourceDz, sourceDx/2)',
            'box_dispatch':{'table':'803d3f50','kind1_kind1_entry':'803d3f60','function':'80089658'},
            'code_windows':[{'start':f'{a:08x}','end_exclusive':f'{b:08x}',
                 'sha256':hashlib.sha256(image.read(a,b-a)).hexdigest()} for a,b in ranges],
            'limits':['Synthetic actor boxes are not recovered concrete vehicle providers',
                'Paired hooks have documented binary64/f32 rather than exact Gekko fused-tie/FPSCR semantics',
                'Radius/type2 and slab/type3 are distinct branches, not replaced by boxes',
                'Notification entry/exit scheduling, swept motion and race checkpoint rules remain separate',
                'Observed AABB-oracle differences/asymmetries remain failures, not a validated general overlap predicate',
                'No general portable rotated OBB predicate, SDK build or runtime changes made']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for field in ('dol','catalog','output'):p.add_argument('--'+field,type=Path,required=True)
    a=p.parse_args();result=verify(a.dol.read_bytes(),json.loads(a.catalog.read_text()))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
