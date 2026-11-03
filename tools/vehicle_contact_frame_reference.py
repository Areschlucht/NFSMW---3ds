"""Bounded original contact-frame leaf/slice reference using shared PS model."""
import struct
from map_recovery_contact_reference import OriginalContactReference
from unicorn.ppc_const import *

class OriginalWheelFrameReference(OriginalContactReference):
    def __init__(self,raw,estimate):
        super().__init__(raw,estimate)
        self.extra_allowed=((0x8024af4c,0x8024afd4),(0x80193498,0x801934ec),(0x8024aa8c,0x8024aac4),(0x8024ae98,0x8024aed0),(0x8021c750,0x8021c7d8),(0x801935a4,0x801935e8),(0x80193154,0x80193178),(0x8024aa28,0x8024aa8c),(0x8024acfc,0x8024ad3c),(0x8024ad74,0x8024ae48),(0x801930e8,0x80193110),(0x80193088,0x801930a8),(0x801931c0,0x801931f0),(0x801933d8,0x80193498),(0x80041a80,0x80041ac0))

    def _hook(self,u,address,size,unused):
        if address==getattr(self,"slice_end",None):
            u.emu_stop();return
        return super()._hook(u,address,size,unused)

    def run(self,start,end,registers):
        self.pair1={};self.instructions=0;self.slice_end=end
        for register,value in [(UC_PPC_REG_1,0x7000fc00),(UC_PPC_REG_LR,0x6000fff0),*registers]:self.u.reg_write(register,value)
        self.u.emu_start(start,end,timeout=200000,count=10000)
        if self.u.reg_read(UC_PPC_REG_PC)!=end:raise ValueError('Frame reference exceeded bounded slice')

    def frame(self,normal,direction,velocity):
        u=self.u;stack=0x7000fc00
        u.mem_write(0x60001000,bytes(0x140));u.mem_write(0x6000103c,struct.pack('>3f',*normal));u.mem_write(stack+0x38,struct.pack('>3f',*direction));u.mem_write(0x60000300,struct.pack('>3f',*velocity))
        self.run(0x8024aa28,0x8024aa8c,[(UC_PPC_REG_29,0x60001000),(UC_PPC_REG_21,0),(UC_PPC_REG_16,0x60000400)])
        lateral=struct.unpack('>3f',bytes(u.mem_read(0x60000400,12)))
        self.putfloating(20,4);self.putfloating(19,3);self.putfloating(23,.30000001192092896)
        self.run(0x8024acfc,0x8024ad3c,[(UC_PPC_REG_3,stack+0x98),(UC_PPC_REG_4,stack+0x88),(UC_PPC_REG_5,0x60000500),(UC_PPC_REG_24,0x60000500)])
        factor=self.floating(30)
        self.run(0x80193088,0x6000fff0,[(UC_PPC_REG_3,0x60000300),(UC_PPC_REG_4,0x60000400)]);lat_velocity=self.floating(1)
        self.run(0x80193088,0x6000fff0,[(UC_PPC_REG_3,0x60000300),(UC_PPC_REG_4,stack+0x98)]);long_velocity=self.floating(1)
        self.run(0x80193010,0x6000fff0,[(UC_PPC_REG_3,0x60000400),(UC_PPC_REG_4,stack+0x88),(UC_PPC_REG_5,0x60000600)])
        self.run(0x80041a80,0x6000fff0,[(UC_PPC_REG_3,0x60000600),(UC_PPC_REG_4,0x60000600)])
        longitudinal=struct.unpack('>3f',bytes(u.mem_read(0x60000600,12)))
        return dict(lateral_axis=lateral,longitudinal_force_axis=longitudinal,lateral_velocity=lat_velocity,longitudinal_velocity=long_velocity,normal_load_factor=factor)

    def world_force(self,normal,lateral_axis,body_up,raw_spring,mass,dt,lateral_velocity,lateral_force,longitudinal_force):
        u=self.u;stack=0x7000fc00
        for address,vector in [(stack+0x88,normal),(stack+0xa8,lateral_axis),(0x60000300,body_up)]:u.mem_write(address,struct.pack('>3f',*vector))
        self.putfloating(1,raw_spring)
        self.run(0x801931c0,0x6000fff0,[(UC_PPC_REG_3,0x60000300),(UC_PPC_REG_4,stack+0xb8)])
        u.mem_write(0x600010dc,struct.pack('>f',longitudinal_force))
        for reg,value in [(1,lateral_force),(31,lateral_velocity),(25,dt),(18,.25),(24,mass),(28,0)]:self.putfloating(reg,value)
        self.run(0x8024ad74,0x8024ae48,[(UC_PPC_REG_17,stack+0xd8),(UC_PPC_REG_31,stack+0xf8),(UC_PPC_REG_29,0x60001000)])
        return struct.unpack('>3f',bytes(u.mem_read(stack+0xf8,12)))

    def point_velocity(self,matrix,mount,cg_offset,linear,angular):
        u=self.u;wheel=0x60001000;pose=0x60002000
        u.mem_write(wheel,bytes(0x140));u.mem_write(wheel+0x6c,struct.pack('>3f',*mount));u.mem_write(pose,struct.pack('>16f',*matrix))
        for address,vector in [(0x60000300,angular),(0x60000400,linear),(0x60000500,cg_offset)]:u.mem_write(address,struct.pack('>3f',*vector))
        self.run(0x8021c750,0x8021c7d8,[(UC_PPC_REG_31,wheel),(UC_PPC_REG_29,wheel+0x7c),(UC_PPC_REG_30,pose),(UC_PPC_REG_27,0x60000300),(UC_PPC_REG_26,0x60000400),(UC_PPC_REG_28,0x60000500)])
        return dict(query_point=struct.unpack('>3f',bytes(u.mem_read(wheel+0x4c,12))),velocity=struct.unpack('>3f',bytes(u.mem_read(wheel+0x8c,12))))

    def normal_dot_up(self,normal,up):
        self.u.mem_write(0x6000103c,struct.pack('>3f',*normal));self.u.mem_write(0x60000300,struct.pack('>3f',*up))
        self.u.mem_write(0x7000fc88,struct.pack('>3f',*normal))
        self.putfloating(22,1);self.putfloating(27,0)
        self.run(0x8024aa8c,0x8024aac4,[(UC_PPC_REG_29,0x60001000),(UC_PPC_REG_22,0x60000300)])
        return self.floating(11)

    def compression_tail(self,compression,previous_air,dt):
        self.u.mem_write(0x60001068,struct.pack('>f',previous_air))
        self.putfloating(29,compression);self.putfloating(25,dt);self.putfloating(27,0)
        self.run(0x8024ae98,0x8024aed0,[(UC_PPC_REG_29,0x60001000),(UC_PPC_REG_21,0)])
        return struct.unpack('>f',bytes(self.u.mem_read(0x60001068,4)))[0],struct.unpack('>f',bytes(self.u.mem_read(0x60001078,4)))[0]

    def force_moment(self,matrix,mount,compression,ride_height,cg_offset,force):
        u=self.u;wheel=0x60001000;pose=0x60002000;stack=0x7000fc00
        u.mem_write(wheel,bytes(0x140));u.mem_write(wheel+0x6c,struct.pack('>3f',*mount));u.mem_write(wheel+0x78,struct.pack('>f',compression));u.mem_write(wheel+0x5c,struct.pack('>3f',*force));u.mem_write(pose,struct.pack('>16f',*matrix))
        u.mem_write(0x60000300,struct.pack('>f',ride_height));u.mem_write(0x60000400,struct.pack('>3f',*cg_offset));u.mem_write(stack+0x184,struct.pack('>I',0x60000400))
        self.run(0x8024af4c,0x8024afd4,[(UC_PPC_REG_30,wheel),(UC_PPC_REG_28,pose),(UC_PPC_REG_9,0),(UC_PPC_REG_11,0x60000300),(UC_PPC_REG_27,0),(UC_PPC_REG_3,stack+0x98),(UC_PPC_REG_4,pose),(UC_PPC_REG_5,stack+0x98)])
        return dict(application_point=struct.unpack('>3f',bytes(u.mem_read(wheel+0x4c,12))),world_moment=struct.unpack('>3f',bytes(u.mem_read(stack+0xa8,12))))
