#!/usr/bin/env python3
"""Bounded offline reference calls into one SHA-pinned original Speed.dol.

Requires Unicorn 2.1.4. Never used by the 3DS executable. Whitelisted original
Gekko paired-single callee-save spills/reloads are replaced only in emulator memory;
none contributes to returned torque. Everything else executes unmodified.
"""
import hashlib
import struct
from vehicle_dol import DolImage

DOL_SHA256 = '33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166'
PSQ_ABI = {
    0x802240b4: 0xf3a10028, 0x802240b8: 0xf3c10030, 0x802240bc: 0xf3e10038,
    0x80224254: 0xe3a10028, 0x80224258: 0xe3c10030, 0x8022425c: 0xe3e10038,
    0x802555d4: 0xf3810018, 0x802555d8: 0xf3a10020,
    0x802555dc: 0xf3c10028, 0x802555e0: 0xf3e10030,
    0x80255710: 0xe3810018, 0x80255714: 0xe3a10020,
    0x80255718: 0xe3c10028, 0x8025571c: 0xe3e10030,
    0x80246454: 0xf3c10010, 0x80246458: 0xf3e10018,
    0x80246570: 0xe3c10010, 0x80246574: 0xe3e10018,
}

# Further checked Gekko ABI spills/reloads in the contacted-wheel and lateral
# curve stages; their arithmetic instructions remain unchanged.
for _reg in range(18,32):
    _offset=0x10+(_reg-18)*8
    PSQ_ABI[0x80246588+(_reg-18)*4]=0xf0000000|(_reg<<21)|(1<<16)|_offset
    PSQ_ABI[0x80246cc0+(_reg-18)*4]=0xe0000000|(_reg<<21)|(1<<16)|_offset
for _reg in range(29,32):
    _offset=0x28+(_reg-29)*8
    PSQ_ABI[0x802460b8+(_reg-29)*4]=0xf0000000|(_reg<<21)|(1<<16)|_offset
    PSQ_ABI[0x80246214+(_reg-29)*4]=0xe0000000|(_reg<<21)|(1<<16)|_offset


class OriginalPpcReference:
    STOP=0x81700000
    STACK=0x817ff000
    STRING=0x81600000
    INSTANCE=0x81601000
    ENGINE=0x81602000

    def __init__(self, raw):
        from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
        from unicorn.ppc_const import UC_PPC_REG_PC
        if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:
            raise ValueError('Unrecognized original executable SHA256')
        self.dol=DolImage(raw);self.uc=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        self.uc.mem_map(0x80000000,0x1800000)
        for s in self.dol.sections: self.uc.mem_write(s.address,raw[s.offset:s.offset+s.size])
        for address, word in PSQ_ABI.items():
            if self.dol.u32(address)!=word: raise ValueError('Unexpected paired-single ABI instruction')
            self.uc.mem_write(address,struct.pack('>I',0x60000000))
        self.allowed=();self.write_ranges=();self.count=0;self.frsqrte_reference=None;self.frsqrte_calls=0;self.emulate_abi=False
        def instruction(uc,address,size,unused):
            self.count+=1
            if not any(start<=address<end for start,end in self.allowed):
                raise ValueError(f'Original execution escaped allowed function ranges: {address:08x}')
            word=struct.unpack('>I',bytes(uc.mem_read(address,4)))[0]
            if self.emulate_abi and word>>26==4:
                raise ValueError('Unmodeled paired arithmetic in scalar contact call graph')
            if self.emulate_abi and address in PSQ_ABI:
                from unicorn.ppc_const import UC_PPC_REG_FPR0,UC_PPC_REG_1
                original=PSQ_ABI[address];register=(original>>21)&31
                effective=uc.reg_read(UC_PPC_REG_1)+(original&0xfff)
                if not 0x817fe000<=effective<effective+8<=0x81800000:raise ValueError('ABI spill escaped stack')
                if original>>26==60:
                    value=struct.unpack('>d',struct.pack('>Q',uc.reg_read(UC_PPC_REG_FPR0+register)))[0]
                    uc.mem_write(effective,struct.pack('>f',value)+bytes(4))
                else:
                    value=struct.unpack('>f',bytes(uc.mem_read(effective,4)))[0]
                    uc.reg_write(UC_PPC_REG_FPR0+register,struct.unpack('>Q',struct.pack('>d',value))[0])
            if self.frsqrte_reference is not None and word>>26==63 and ((word>>1)&1023)==26:
                from unicorn.ppc_const import UC_PPC_REG_FPR0,UC_PPC_REG_PC
                source=(word>>11)&31;destination=(word>>21)&31
                value=struct.unpack('>d',struct.pack('>Q',uc.reg_read(UC_PPC_REG_FPR0+source)))[0]
                result=self.frsqrte_reference.estimate(value)
                uc.reg_write(UC_PPC_REG_FPR0+destination,struct.unpack('>Q',struct.pack('>d',result))[0]);uc.reg_write(UC_PPC_REG_PC,address+4);self.frsqrte_calls+=1
        def write(uc,access,address,size,value,unused):
            if not any(start<=address<address+size<=end for start,end in ((0x817fe000,0x81800000),*self.write_ranges)):
                raise ValueError(f'Original execution wrote outside stack: {address:08x}')
        self.uc.hook_add(UC_HOOK_CODE,instruction)
        self.uc.hook_add(UC_HOOK_MEM_WRITE,write)

    def _call(self,start,r3,rpm=None,r4=0,float_result=False):
        from unicorn.ppc_const import UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_LR, UC_PPC_REG_FPR1, UC_PPC_REG_MSR, UC_PPC_REG_PC
        u=self.uc;self.count=0
        u.reg_write(UC_PPC_REG_1,self.STACK);u.reg_write(UC_PPC_REG_3,r3);u.reg_write(UC_PPC_REG_4,r4&0xffffffff)
        u.reg_write(UC_PPC_REG_LR,self.STOP);u.reg_write(UC_PPC_REG_MSR,0x2000)
        if rpm is not None: u.reg_write(UC_PPC_REG_FPR1,struct.unpack('>Q',struct.pack('>d',float(rpm)))[0])
        u.emu_start(start,self.STOP,count=100000,timeout=1000000)
        if u.reg_read(UC_PPC_REG_PC)!=self.STOP: raise RuntimeError('Original function exceeded bounded execution budget')
        return struct.unpack('>d',struct.pack('>Q',u.reg_read(UC_PPC_REG_FPR1)))[0] if rpm is not None or float_result else u.reg_read(UC_PPC_REG_3)

    def hash(self,text):
        value=text.encode('ascii') if isinstance(text,str) else bytes(text)
        if b'\0' in value or len(value)>4095: raise ValueError('Expected bounded NUL-free string')
        self.uc.mem_write(self.STRING,value+b'\0')
        self.allowed=((0x80195400,0x80195744),(0x80314d48,0x80314db4))
        return self._call(0x801956e8,self.STRING)

    def torque(self,layout,rpm):
        if len(layout)!=96: raise ValueError('Expected original 96-byte engine required layout')
        self.uc.mem_write(self.ENGINE,bytes(layout))
        self.uc.mem_write(self.INSTANCE,bytes(8)+struct.pack('>I',self.ENGINE)+bytes(8))
        self.allowed=((0x802240ac,0x80224268),(0x80058124,0x8005812c))
        return self._call(0x802240ac,self.INSTANCE,rpm)

    def tire_diameter(self,layout,front_axle):
        if len(layout)!=80: raise ValueError('Expected original 80-byte tires required layout')
        self.uc.mem_write(self.ENGINE,bytes(layout))
        self.uc.mem_write(self.INSTANCE,bytes(8)+struct.pack('>I',self.ENGINE)+bytes(8))
        self.allowed=((0x80224268,0x802242c0),)
        return self._call(0x80224268,self.INSTANCE,r4=front_axle,float_result=True)

    def wheel_brake(self,brakes_layout,state,argument=0.0,step=False):
        if len(brakes_layout)!=20 or len(state)!=0x140:raise ValueError('Unexpected brake/state layout')
        wheel=0x81604000
        self.uc.mem_write(self.ENGINE,bytes(brakes_layout))
        self.uc.mem_write(self.INSTANCE,bytes(8)+struct.pack('>I',self.ENGINE)+bytes(8))
        state=bytearray(state);struct.pack_into('>I',state,0x104,self.INSTANCE)
        self.uc.mem_write(wheel,bytes(state));self.write_ranges=((wheel,wheel+len(state)),)
        self.allowed=((0x802462d0,0x802463b0),) if not step else ((0x802462d0,0x80246580),)
        try:self._call(0x8024644c if step else 0x802462d0,wheel,argument)
        finally:self.write_ranges=()
        return bytes(self.uc.mem_read(wheel,len(state)))

    def requested_rpm(self,engine_layout,tires_layout,transmission_layout,gear,speed):
        if (len(engine_layout),len(tires_layout),len(transmission_layout))!=(96,80,132):raise ValueError('Unexpected drivetrain attribute layout')
        self.uc.mem_write(self.ENGINE,bytes(engine_layout));self.uc.mem_write(0x81603000,bytes(tires_layout));self.uc.mem_write(0x81605000,bytes(transmission_layout))
        obj=bytearray(0x1b0)
        for offset,pointer in [(0x150,self.ENGINE),(0x178,0x81603000),(0x164,0x81605000)]:struct.pack_into('>I',obj,offset,pointer)
        self.uc.mem_write(0x81608000,bytes(obj))
        self.allowed=((0x802555cc,0x80255728),(0x80224268,0x802242c0),(0x80058124,0x8005812c))
        return self._call(0x802555cc,0x81608000,speed,r4=gear)

    def rear_grip_assist(self,values):
        from unicorn.ppc_const import UC_PPC_REG_FPR1
        if len(values)!=5:raise ValueError('Expected original f1..f5 arguments')
        for i,value in enumerate(values):self.uc.reg_write(UC_PPC_REG_FPR1+i,struct.unpack('>Q',struct.pack('>d',float(value)))[0])
        self.allowed=((0x80249004,0x802490b0),)
        return self._call(0x80249004,0,float_result=True)

    def initialize_contact_curves(self):
        """Execute proven original startup subsection with its two live-ins.

        Original802653C0 sets r25=6;8026578C loads f30=0. The chosen subsection
        initializes seven curve objects and contains no other incoming values.
        """
        from unicorn.ppc_const import UC_PPC_REG_1,UC_PPC_REG_25,UC_PPC_REG_FPR30,UC_PPC_REG_MSR,UC_PPC_REG_PC
        from unicorn.ppc_const import UC_PPC_REG_FPR2
        # Source802653B8 sets count10; constructor calls802657E0/65808
        # use min0,max1 and source data8041F228/8041F250.
        for object_address,data_address in [(0x80489e68,0x8041f228),(0x80489e7c,0x8041f250)]:
            self.uc.mem_write(object_address,struct.pack('>I',10)+bytes(12)+struct.pack('>I',data_address))
            self.uc.reg_write(UC_PPC_REG_FPR2,struct.unpack('>Q',struct.pack('>d',1.0))[0])
            self.allowed=((0x80042614,0x80042640),(0x80045c90,0x80045cdc));self.write_ranges=((object_address,object_address+20),)
            try:self._call(0x80042614,object_address,0.0)
            finally:self.write_ranges=()
        self.uc.reg_write(UC_PPC_REG_1,self.STACK);self.uc.reg_write(UC_PPC_REG_25,6);self.uc.reg_write(UC_PPC_REG_FPR30,0);self.uc.reg_write(UC_PPC_REG_MSR,0x2000)
        self.allowed=((0x80265868,0x802659a0),(0x80042614,0x80042640),(0x80045c90,0x80045cdc))
        self.write_ranges=((0x80489eb0,0x80489f40),)
        try:
            self.uc.emu_start(0x80265868,0x802659a0,count=10000,timeout=1000000)
            if self.uc.reg_read(UC_PPC_REG_PC)!=0x802659a0:raise RuntimeError('Curve initialization exceeded budget')
        finally:self.write_ranges=()

    def lateral_curve(self,tires_layout,axle,wheel_scale,normal_force_argument,slip_angle_turns):
        from unicorn.ppc_const import UC_PPC_REG_FPR2
        if len(tires_layout)!=80 or axle not in (0,1):raise ValueError('Unexpected tire/axle layout')
        wheel=bytearray(0x140);struct.pack_into('>I',wheel,0x100,self.INSTANCE);struct.pack_into('>I',wheel,0x10c,axle);struct.pack_into('>f',wheel,0x128,wheel_scale)
        self.uc.mem_write(self.ENGINE,bytes(tires_layout));self.uc.mem_write(self.INSTANCE,bytes(8)+struct.pack('>I',self.ENGINE)+bytes(8));self.uc.mem_write(0x81604000,bytes(wheel))
        self.uc.reg_write(UC_PPC_REG_FPR2,struct.unpack('>Q',struct.pack('>d',float(slip_angle_turns)))[0])
        self.allowed=((0x802460b0,0x80246228),(0x80208ec4,0x80208fa4))
        return self._call(0x802460b0,0x81604000,normal_force_argument)

    def contacted_wheel(self,tires_layout,brakes_layout,surface_layout,state,arguments,frsqrte_reference):
        from unicorn.ppc_const import UC_PPC_REG_2,UC_PPC_REG_13,UC_PPC_REG_FPR1
        if len(tires_layout)!=80 or len(brakes_layout)!=20 or len(surface_layout) not in (251,252) or len(state)!=0x140 or len(arguments)!=5:raise ValueError('Unexpected contact input layout')
        for address,layout in [(0x81602000,tires_layout),(0x81603000,brakes_layout),(0x81605000,surface_layout)]:self.uc.mem_write(address,bytes(layout))
        for address,pointer in [(0x81601000,0x81602000),(0x81601100,0x81603000)]:self.uc.mem_write(address,bytes(8)+struct.pack('>I',pointer)+bytes(8))
        state=bytearray(state)
        for offset,pointer in [(0xa4,0x81605000),(0x100,0x81601000),(0x104,0x81601100)]:struct.pack_into('>I',state,offset,pointer)
        self.uc.mem_write(0x81604000,bytes(state))
        # Original entry80003108..14 establishes these small-data bases.
        self.uc.reg_write(UC_PPC_REG_2,0x80516dc0);self.uc.reg_write(UC_PPC_REG_13,0x80506dc0)
        for i,value in enumerate(arguments):self.uc.reg_write(UC_PPC_REG_FPR1+i,struct.unpack('>Q',struct.pack('>d',float(value)))[0])
        self.allowed=((0x802460b0,0x80246d00),(0x80208ec4,0x80208fa4),(0x80193420,0x80193458),(0x80193bb4,0x80193c74),(0x8005d1f0,0x8005d338),(0x8031dcbc,0x8031dd98),(0x8031e4bc,0x8031f500))
        self.write_ranges=((0x81604000,0x81604140),);self.frsqrte_reference=frsqrte_reference;self.frsqrte_calls=0;self.emulate_abi=True
        try:result=self._call(0x80246580,0x81604000,float_result=True)
        finally:self.write_ranges=();self.frsqrte_reference=None;self.emulate_abi=False
        return result,bytes(self.uc.mem_read(0x81604000,0x140))

    def friction_limit(self,state,magnitude,static_grip,speed_factor,slip_speed,undo_boost):
        from unicorn.ppc_const import UC_PPC_REG_30,UC_PPC_REG_31,UC_PPC_REG_FPR1,UC_PPC_REG_PC,UC_PPC_REG_MSR
        if len(state)!=0x140:raise ValueError('Unexpected wheel state')
        self.uc.reg_write(UC_PPC_REG_MSR,0x2000);self.uc.mem_write(0x81604000,bytes(state));self.uc.reg_write(UC_PPC_REG_31,0x81604000);self.uc.reg_write(UC_PPC_REG_30,int(undo_boost))
        for register,value in [(1,magnitude),(18,static_grip),(21,speed_factor),(27,slip_speed)]:self.uc.reg_write(UC_PPC_REG_FPR1+register-1,struct.unpack('>Q',struct.pack('>d',float(value)))[0])
        self.allowed=((0x80246a38,0x80246b14),);self.write_ranges=((0x81604000,0x81604140),)
        try:
            self.uc.emu_start(0x80246a38,0x80246b14,count=1000,timeout=1000000)
            if self.uc.reg_read(UC_PPC_REG_PC)!=0x80246b14:raise RuntimeError('Friction stage exceeded budget')
        finally:self.write_ranges=()
        return bytes(self.uc.mem_read(0x81604000,0x140))

    def scalar_math(self,kind,value,estimate=None,second=0):
        from unicorn.ppc_const import UC_PPC_REG_2,UC_PPC_REG_13,UC_PPC_REG_FPR2
        self.uc.reg_write(UC_PPC_REG_2,0x80516dc0);self.uc.reg_write(UC_PPC_REG_13,0x80506dc0)
        self.uc.reg_write(UC_PPC_REG_FPR2,struct.unpack('>Q',struct.pack('>d',float(second)))[0])
        if kind=='sqrt':start=0x80193420;self.allowed=((start,0x80193458),)
        elif kind=='angle':start=0x80193bb4;self.allowed=((start,0x80193c74),(0x8005d1f0,0x8005d338))
        elif kind=='pow':start=0x8031cec0;self.allowed=((start,0x8031dcbc),)
        elif kind=='sin':start=0x8031dcbc;self.allowed=((start,0x8031dd98),(0x8031e4bc,0x8031f500))
        else:raise ValueError('Unknown math reference')
        self.frsqrte_reference=estimate
        try:return self._call(start,0,value)
        finally:self.frsqrte_reference=None

    def contact_scale_producers(self,speed,mode_c8,gear):
        state=bytearray(0xd0);struct.pack_into('>f',state,0xbc,speed);struct.pack_into('>h',state,0xc8,mode_c8);struct.pack_into('>h',state,0xcc,gear)
        self.uc.mem_write(0x81608000,bytes(state));result=[]
        for start,end in [(0x802442b8,0x80244330),(0x80244590,0x80244630),(0x80244630,0x802446f0)]:
            self.allowed=((start,end),(0x80208ec4,0x80208fa4))
            result.append(self._call(start,0,float_result=True,r4=0x81608000))
        return result

    def contact_mounts(self,tires_layout,chassis_layout,half_extent_y):
        from unicorn.ppc_const import UC_PPC_REG_1,UC_PPC_REG_28,UC_PPC_REG_MSR,UC_PPC_REG_PC
        if len(tires_layout)!=80 or len(chassis_layout)!=116:raise ValueError('Unexpected contact geometry layout')
        self.uc.mem_write(0x81602000,bytes(tires_layout));self.uc.mem_write(0x81603000,bytes(chassis_layout));actor=bytearray(0x1cc)
        for offset,pointer in [(0xa8,0x81602000),(0xd0,0x81603000)]:struct.pack_into('>I',actor,offset,pointer)
        for i in range(4):struct.pack_into('>I',actor,0x1bc+i*4,0x81609000+i*0x200)
        self.uc.mem_write(0x81608000,bytes(actor));self.uc.mem_write(self.STACK+0xc,struct.pack('>f',half_extent_y));self.uc.reg_write(UC_PPC_REG_1,self.STACK);self.uc.reg_write(UC_PPC_REG_28,0x81608000);self.uc.reg_write(UC_PPC_REG_MSR,0x2000)
        self.allowed=((0x80247724,0x80247838),);self.write_ranges=((0x81609000,0x81609800),)
        try:
            self.uc.emu_start(0x80247724,0x80247838,count=1000,timeout=1000000)
            if self.uc.reg_read(UC_PPC_REG_PC)!=0x80247838:raise RuntimeError('Mount geometry exceeded bounded slice')
        finally:self.write_ranges=()
        return [struct.unpack('>3f',bytes(self.uc.mem_read(0x81609000+i*0x200+0x6c,12))) for i in range(4)]

    def suspension_load(self,chassis_layout,axle,query_w,normal_dot,previous,dt,ride_extra,antiroll,mass):
        from unicorn import UC_HOOK_CODE
        from unicorn.ppc_const import UC_PPC_REG_0,UC_PPC_REG_1,UC_PPC_REG_3,UC_PPC_REG_4,UC_PPC_REG_5,UC_PPC_REG_6,UC_PPC_REG_7,UC_PPC_REG_8,UC_PPC_REG_10,UC_PPC_REG_11,UC_PPC_REG_14,UC_PPC_REG_15,UC_PPC_REG_16,UC_PPC_REG_17,UC_PPC_REG_21,UC_PPC_REG_23,UC_PPC_REG_24,UC_PPC_REG_26,UC_PPC_REG_27,UC_PPC_REG_29,UC_PPC_REG_30,UC_PPC_REG_LR,UC_PPC_REG_MSR,UC_PPC_REG_FPR0,UC_PPC_REG_PC,UC_PPC_REG_2,UC_PPC_REG_13
        if len(chassis_layout)!=116 or axle not in (0,1):raise ValueError('Unexpected chassis/axle')
        u=self.uc;stack=self.STACK;chassis=0x81603000;wheel=0x81604000;actor=0x81608000
        u.mem_write(chassis,bytes(chassis_layout));u.mem_write(wheel,bytes(0x140));u.mem_write(wheel+0x48,struct.pack('>f',query_w));u.mem_write(wheel+0x78,struct.pack('>f',previous));u.mem_write(actor,bytes(0x1cc));u.mem_write(actor+0xd0,struct.pack('>I',chassis))
        u.reg_write(UC_PPC_REG_1,stack);u.reg_write(UC_PPC_REG_MSR,0x2000);u.reg_write(UC_PPC_REG_2,0x80516dc0);u.reg_write(UC_PPC_REG_13,0x80506dc0)
        for register,value in [(UC_PPC_REG_0,stack+0x118),(UC_PPC_REG_10,chassis),(UC_PPC_REG_11,0),(UC_PPC_REG_27,chassis+0x30),(UC_PPC_REG_30,chassis+0x28),(UC_PPC_REG_3,chassis+0x40),(UC_PPC_REG_4,chassis+0x38),(UC_PPC_REG_5,chassis+0x48),(UC_PPC_REG_6,chassis+0x10),(UC_PPC_REG_7,chassis+0x18),(UC_PPC_REG_8,chassis+8),(UC_PPC_REG_14,stack+0x120),(UC_PPC_REG_15,stack+0x128),(UC_PPC_REG_16,stack+0x130),(UC_PPC_REG_17,stack+0x148),(UC_PPC_REG_21,stack+0x150),(UC_PPC_REG_24,stack+0x158),(UC_PPC_REG_LR,stack+0x140)]:u.reg_write(register,value)
        for register,value in [(10,1),(11,self.dol.f32(0x803fb678)),(12,self.dol.f32(0x803fb674)),(31,ride_extra)]:u.reg_write(UC_PPC_REG_FPR0+register,struct.unpack('>Q',struct.pack('>d',float(value)))[0])
        self.allowed=((0x8024a730,0x8024a7b4),);self.write_ranges=()
        u.emu_start(0x8024a730,0x8024a7b4,count=1000,timeout=1000000)
        if u.reg_read(UC_PPC_REG_PC)!=0x8024a7b4:raise ValueError('Suspension conversion budget exceeded')
        for pointer_offset,target in [(0x188,0x118),(0x18c,0x120),(0x190,0x128),(0x194,0x130),(0x198,0x138),(0x168,0x148),(0x16c,0x150),(0x170,0x158),(0x164,0x28)]:u.mem_write(stack+pointer_offset,struct.pack('>I',stack+target))
        u.mem_write(stack+0x28+axle*8,struct.pack('>f',antiroll))
        for register,value in [(UC_PPC_REG_26,actor),(UC_PPC_REG_29,wheel),(UC_PPC_REG_30,axle),(UC_PPC_REG_21,axle*2),(UC_PPC_REG_23,axle*8)]:u.reg_write(register,value)
        for register,value in [(11,normal_dot),(16,self.dol.f32(0x803fb684)),(17,self.dol.f32(0x803fb680)),(21,1),(24,mass),(25,dt),(26,0),(27,0),(31,query_w)]:u.reg_write(UC_PPC_REG_FPR0+register,struct.unpack('>Q',struct.pack('>d',float(value)))[0])
        result={}
        def floating(register):return struct.unpack('>d',struct.pack('>Q',u.reg_read(UC_PPC_REG_FPR0+register)))[0]
        def capture(uc,address,size,unused):
            if address==0x8024ae68:uc.emu_stop()
            elif address==0x8024ac18:result['compression_velocity']=floating(31)
            elif address==0x8024ac60:result['spring_force']=floating(28);result['damper_force']=floating(11)
        hook=u.hook_add(UC_HOOK_CODE,capture);self.allowed=((0x8024aac4,0x8024ac8c),(0x8024ae68,0x8024ae6c),(0x8031cec0,0x8031dcbc));self.write_ranges=((wheel,wheel+0x140),)
        try:u.emu_start(0x8024aac4,0x8024ac8c,count=100000,timeout=1000000)
        finally:u.hook_del(hook);self.write_ranges=()
        pc=u.reg_read(UC_PPC_REG_PC)
        if pc not in (0x8024ac8c,0x8024ae68):raise ValueError('Suspension force budget exceeded')
        result.update(compression=floating(29),penetration_excess=floating(26),normal_force=floating(31) if pc==0x8024ac8c else 0,has_contact=pc==0x8024ac8c,bottomed_out=bool(struct.unpack('>I',bytes(u.mem_read(wheel+0x114,4)))[0]))
        for key in ['compression_velocity','spring_force','damper_force']:result.setdefault(key,0)
        return result

    def suspension_antiroll(self,chassis_layout,previous):
        from unicorn.ppc_const import UC_PPC_REG_26,UC_PPC_REG_CTR,UC_PPC_REG_PC
        if len(previous)!=4:raise ValueError('Four prior compressions required')
        self.suspension_load(chassis_layout,0,-1,0,0,1/120,0,0,1300)
        actor=0x81608000;stack=self.STACK
        for i,value in enumerate(previous):
            pointer=0x81609000+i*0x200;self.uc.mem_write(actor+0x1bc+i*4,struct.pack('>I',pointer));self.uc.mem_write(pointer+0x78,struct.pack('>f',value))
        self.uc.reg_write(UC_PPC_REG_26,actor);self.uc.reg_write(UC_PPC_REG_CTR,stack+0x140);self.allowed=((0x8024a7b4,0x8024a858),)
        self.uc.emu_start(0x8024a7b4,0x8024a858,count=1000,timeout=1000000)
        if self.uc.reg_read(UC_PPC_REG_PC)!=0x8024a858:raise RuntimeError('Antiroll reference budget exceeded')
        return struct.unpack('>4f',bytes(self.uc.mem_read(stack+0x28,16)))
