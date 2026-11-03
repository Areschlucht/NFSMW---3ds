"""Bounded actual USA DOL tangent-response reference, not runtime game emulation.

Uses shared explicit Gekko PS hooks and caller-supplied pinned external frsqrte
model. No original code/tables bundled. Only original80083680 plus its explicit
vector/sqrt leaves execute; exact FPSCR/FMA ties/subnormals are outside scope.
"""
import hashlib
import struct
from map_recovery_contact_reference import OriginalContactReference
from map_recovery_ps_reference import f32
from unicorn.ppc_const import (UC_PPC_REG_1,UC_PPC_REG_3,UC_PPC_REG_4,UC_PPC_REG_5,
    UC_PPC_REG_6,UC_PPC_REG_LR,UC_PPC_REG_PC)


class OriginalBodyFrictionReference(OriginalContactReference):
    BODY_START=0x80083680
    BODY_END=0x800837d0
    def __init__(self,raw,frsqrte_reference):
        super().__init__(raw,frsqrte_reference)
        self.extra_allowed=((self.BODY_START,self.BODY_END),(0x801930e8,0x8019310c),
            (0x801931c0,0x801931dc),(0x801933d8,0x801933f0),(0x80193420,0x80193458))
        self.friction_sha256=hashlib.sha256(self.dol.read(self.BODY_START,self.BODY_END-self.BODY_START)).hexdigest()

    def tangent(self,coefficients,velocity,normal,normal_component):
        u=self.u;self.pair1={};self.instructions=0
        u.mem_write(0x60000100,struct.pack('>2f',*coefficients))
        u.mem_write(0x60000200,struct.pack('>3f',*velocity))
        u.mem_write(0x60000300,struct.pack('>3f',*normal))
        u.mem_write(0x60000400,bytes(12))
        self.putfloating(1,f32(normal_component))
        for register,value in ((UC_PPC_REG_1,0x7000ff00),(UC_PPC_REG_3,0x60000100),
            (UC_PPC_REG_4,0x60000200),(UC_PPC_REG_5,0x60000300),(UC_PPC_REG_6,0x60000400),
            (UC_PPC_REG_LR,0x6000fff0)):u.reg_write(register,value)
        u.emu_start(self.BODY_START,0x6000fff0,timeout=100000,count=10000)
        if u.reg_read(UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Original body-friction reference exceeded budget')
        return dict(branch=u.reg_read(UC_PPC_REG_3),correction=list(struct.unpack('>3f',bytes(u.mem_read(0x60000400,12)))),instructions=self.instructions)

    def sqrt_raw(self,value):
        self.pair1={};self.instructions=0;u=self.u
        self.putfloating(1,f32(value));u.reg_write(UC_PPC_REG_1,0x7000ff00);u.reg_write(UC_PPC_REG_LR,0x6000fff0)
        u.emu_start(0x80193420,0x6000fff0,timeout=100000,count=1000)
        if u.reg_read(UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Original sqrt exceeded budget')
        return self.floating(1)

class OriginalGroundPlaneReference(OriginalContactReference):
    """Original world-triangle normal and query-relative scalar producer."""
    def __init__(self,raw,frsqrte_reference):
        super().__init__(raw,frsqrte_reference)
        self.extra_allowed=((0x80308c18,0x80308d8c),)
    def ground_plane(self,triangle,query):
        from unicorn.ppc_const import UC_PPC_REG_27,UC_PPC_REG_30,UC_PPC_REG_31
        self.pair1={};self.instructions=0;u=self.u
        u.mem_write(0x60000100,b''.join(struct.pack('>4f',*p,0) for p in triangle))
        u.mem_write(0x60000200,struct.pack('>3f',*query));u.mem_write(0x60000300,bytes(16))
        for register,value in ((UC_PPC_REG_1,0x7000ff00),(UC_PPC_REG_27,0x60000200),
            (UC_PPC_REG_30,0x60000100),(UC_PPC_REG_31,0x60000300)):u.reg_write(register,value)
        u.emu_start(0x80308c18,0x80308d8c,timeout=100000,count=10000)
        if u.reg_read(UC_PPC_REG_PC)!=0x80308d8c:raise ValueError('Original ground-plane slice exceeded budget')
        return struct.unpack('>4f',bytes(u.mem_read(0x60000300,16)))

class OriginalBodyBoundReference(OriginalContactReference):
    """Actual body-bound endian fixup and packed-vector decoder slices."""
    BASE=0x60010000
    def __init__(self,raw,frsqrte_reference):
        super().__init__(raw,frsqrte_reference)
        self.extra_allowed=((0x8021e0e0,0x8021e360),(0x8005cb10,0x8005cb48),(0x8021e440,0x8021e60c))
    def fixup(self,raw_package):
        if not 32<=len(raw_package)<=0x20000:raise ValueError('Bound reference size exceeds mapping')
        u=self.u;self.pair1={};self.instructions=0;u.mem_write(self.BASE,raw_package)
        for register,value in ((UC_PPC_REG_1,0x7000f000),(UC_PPC_REG_3,self.BASE),(UC_PPC_REG_LR,0x6000fff0)):u.reg_write(register,value)
        u.emu_start(0x8021e0e0,0x6000fff0,timeout=100000,count=100000)
        if u.reg_read(UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Bound fixup exceeded budget')
        return bytes(u.mem_read(self.BASE,len(raw_package)))
    def decode_vectors(self,fixed_record):
        if len(fixed_record)!=48:raise ValueError('Expected one original48-byte bound')
        u=self.u;self.pair1={};self.instructions=0;u.mem_write(0x60000400,fixed_record)
        for register,value in ((UC_PPC_REG_1,0x7000f000),(UC_PPC_REG_5,0x60000400)):u.reg_write(register,value)
        u.emu_start(0x8021e440,0x8021e60c,timeout=100000,count=10000)
        if u.reg_read(UC_PPC_REG_PC)!=0x8021e60c:raise ValueError('Bound vector decoder exceeded budget')
        return dict(center=struct.unpack('>3f',bytes(u.mem_read(0x7000f008,12))),half_extents=struct.unpack('>3f',bytes(u.mem_read(0x7000f018,12))),quaternion=struct.unpack('>4f',bytes(u.mem_read(0x7000f028,16))))

class OriginalBodyPrimitiveReference(OriginalContactReference):
    """Original flag dispatch/box padding/sphere arguments; allocation observed.

    Only80231D6C's allocation/list insertion is intercepted after all primitive
    arguments have been produced. This verifies the shape producer, not the
    original allocator, linked-list bookkeeping or collision solver.
    """
    def __init__(self,raw,frsqrte_reference):
        super().__init__(raw,frsqrte_reference)
        self.extra_allowed=((0x8023446c,0x80234524),(0x80238ef8,0x80239018),(0x801930e8,0x8019310c))
        self.produced=None
    def _hook(self,u,address,size,data):
        if address==0x80231d6c:
            from unicorn.ppc_const import UC_PPC_REG_7,UC_PPC_REG_8,UC_PPC_REG_9,UC_PPC_REG_10
            self.produced=dict(kind=u.reg_read(UC_PPC_REG_7),runtime_flags=u.reg_read(UC_PPC_REG_9),
                half_extents=struct.unpack('>3f',bytes(u.mem_read(u.reg_read(UC_PPC_REG_4),12))),
                center=struct.unpack('>3f',bytes(u.mem_read(u.reg_read(UC_PPC_REG_5),12))),
                quaternion=struct.unpack('>4f',bytes(u.mem_read(u.reg_read(UC_PPC_REG_8),16))),
                token=struct.unpack('>I',bytes(u.mem_read(u.reg_read(UC_PPC_REG_10),4)))[0])
            u.reg_write(UC_PPC_REG_3,1);u.reg_write(UC_PPC_REG_PC,u.reg_read(UC_PPC_REG_LR));return
        super()._hook(u,address,size,data)
    def primitive(self,bound,padding=(0,0,0)):
        from unicorn.ppc_const import UC_PPC_REG_7,UC_PPC_REG_8,UC_PPC_REG_9
        u=self.u;self.pair1={};self.instructions=0;self.produced=None
        body=0x60001000;layout=0x60002000
        u.mem_write(body,bytes(256));u.mem_write(body+0x94,struct.pack('>I',layout));u.mem_write(layout,struct.pack('>3f',*padding))
        for at,values in ((0x60003000,bound['half_extents']),(0x60003100,bound['center']),(0x60003200,bound['quaternion'])):
            u.mem_write(at,struct.pack('>'+str(len(values))+'f',*values))
        u.mem_write(0x60003400,struct.pack('>I',bound['unknown_28']));self.putfloating(1,bound['source_radius'])
        for register,value in ((UC_PPC_REG_1,0x7000f000),(UC_PPC_REG_3,body),(UC_PPC_REG_4,0x60003400),
            (UC_PPC_REG_5,0x60003000),(UC_PPC_REG_6,0x60003100),(UC_PPC_REG_7,0x60003300),
            (UC_PPC_REG_8,0x60003200),(UC_PPC_REG_9,bound['flags']),(UC_PPC_REG_LR,0x6000fff0)):u.reg_write(register,value)
        u.emu_start(0x8023446c,0x6000fff0,timeout=100000,count=10000)
        if u.reg_read(UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Original primitive producer exceeded budget')
        return dict(created=bool(u.reg_read(UC_PPC_REG_3)),arguments=self.produced)

class OriginalBodyCoreReference(OriginalContactReference):
    """Execute original state constructor and16-pass static-contact core.

    The supplied state fields/parameters are explicit original producer inputs;
    this does not invent the BMW VehicleParams tensor/half-extent producers.
    """
    STATE=0x60010000
    def __init__(self,raw,frsqrte_reference):
        super().__init__(raw,frsqrte_reference)
        self.extra_allowed=((0x800837d0,0x80083988),(0x80083c74,0x80084690),
            (0x80083680,0x800837d0),(0x80193088,0x8019310c),(0x801931c0,0x80193200),
            (0x801933d8,0x80193458),(0x801935a4,0x801935e8))
        self.trace=[]
    def _hook(self,u,address,size,data):
        if address==0x8008420c:
            from unicorn.ppc_const import UC_PPC_REG_25
            stack=u.reg_read(UC_PPC_REG_1)
            self.trace.append(dict(iteration=u.reg_read(UC_PPC_REG_25),normal=struct.unpack('>3f',bytes(u.mem_read(stack+0x78,12))),lever=struct.unpack('>3f',bytes(u.mem_read(stack+8,12))),velocity=struct.unpack('>3f',bytes(u.mem_read(stack+0x98,12))),angular=struct.unpack('>3f',bytes(u.mem_read(stack+0x88,12))),effective_matrix=struct.unpack('>16f',bytes(u.mem_read(stack+0x38,64)))))
        super()._hook(u,address,size,data)
    def contact(self,*,mass,inertia,cg,velocity,angular,position,orientation,point,normal,friction,moment_scale=(1,1,1),mode=0,passes=16,extra_normal_accumulation=0):
        from unicorn.ppc_const import UC_PPC_REG_7,UC_PPC_REG_8,UC_PPC_REG_9
        if len(orientation)!=16 or not 1<=passes<=64:raise ValueError('Invalid body-core input')
        u=self.u;self.pair1={};self.instructions=0;self.trace=[]
        inputs=((0x60001000,orientation),(0x60001100,inertia),(0x60001200,cg),
            (0x60001300,velocity),(0x60001400,angular),(0x60001500,position))
        for at,values in inputs:u.mem_write(at,struct.pack('>'+str(len(values))+'f',*values))
        u.mem_write(self.STATE,bytes(0x118));self.putfloating(1,f32(mass))
        for register,value in ((UC_PPC_REG_1,0x7000f000),(UC_PPC_REG_3,self.STATE),
            (UC_PPC_REG_4,0x60001000),(UC_PPC_REG_5,0x60001100),(UC_PPC_REG_6,0x60001200),
            (UC_PPC_REG_7,0x60001300),(UC_PPC_REG_8,0x60001400),(UC_PPC_REG_9,0x60001500),
            (UC_PPC_REG_LR,0x6000fff0)):u.reg_write(register,value)
        u.emu_start(0x800837d0,0x6000fff0,timeout=100000,count=10000)
        if u.reg_read(UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Original body state constructor exceeded budget')
        u.mem_write(self.STATE+0xbc,struct.pack('>3f',*moment_scale));u.mem_write(self.STATE+0xc8,struct.pack('>I',mode))
        u.mem_write(self.STATE+0x10c,struct.pack('>f',extra_normal_accumulation))
        before=bytes(u.mem_read(self.STATE,0x118));u.mem_write(0x60003000,struct.pack('>3f3f2f',*point,*normal,*friction))
        self.pair1={};self.instructions=0
        for register,value in ((UC_PPC_REG_1,0x7000f000),(UC_PPC_REG_3,self.STATE),(UC_PPC_REG_4,0x60003000),(UC_PPC_REG_5,passes),(UC_PPC_REG_LR,0x6000fff0)):u.reg_write(register,value)
        u.emu_start(0x80083c74,0x6000fff0,timeout=1000000,count=200000)
        if u.reg_read(UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Original body contact core exceeded budget')
        after=bytes(u.mem_read(self.STATE,0x118))
        return dict(hit=bool(u.reg_read(UC_PPC_REG_3)),before=before.hex(),after=after.hex(),velocity=struct.unpack_from('>3f',after,0x98),angular=struct.unpack_from('>3f',after,0xa4),initial_normal_velocity=struct.unpack_from('>3f',after,0xd8),initial_tangent_velocity=struct.unpack_from('>3f',after,0xe4),normal_momentum=struct.unpack_from('>3f',after,0xd8),tangent_momentum=struct.unpack_from('>3f',after,0xe4),normal_correction=struct.unpack_from('>3f',after,0xf0),friction_correction=struct.unpack_from('>3f',after,0xfc),friction_branch=struct.unpack_from('>I',after,0x108)[0],trace=list(self.trace),instructions=self.instructions)
