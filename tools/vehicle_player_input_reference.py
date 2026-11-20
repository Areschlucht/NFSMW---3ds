#!/usr/bin/env python3
"""Source steering/input arithmetic versus unchanged bounded USA PowerPC calls."""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from vehicle_dol import DolImage
from vehicle_ppc_reference import DOL_SHA256
from vehicle_contact_frame_reference import OriginalWheelFrameReference
from unicorn.ppc_const import *

ROOT=Path(__file__).resolve().parents[1]
class Average(C.Structure):
    _fields_=[('values',C.c_float*33),('times',C.c_float*33),('sum',C.c_float),('average',C.c_float),('seconds',C.c_float),('capacity',C.c_uint32),('count',C.c_uint32),('cursor',C.c_uint32),('oldest',C.c_uint32)]
class SteeringState(C.Structure):
    _fields_=[('angle_degrees',C.c_float),('previous_input',C.c_float),('gain_history',C.c_float),('input_average',Average),('rate_average',Average)]
class SteeringInput(C.Structure):
    _fields_=[(n,C.c_float) for n in ('raw_steering','forward_speed','throttle','brake','handbrake','seconds','time','tire_steering')]+[('rear_slip_angle_turns',C.c_float*2)]+[(n,C.c_float) for n in ('blend_100','fade_1ac')]+[('interface_mode',C.c_uint32),('effect_present',C.c_bool),('effect_0',C.c_float)]
class BrakeState(C.Structure):
    _fields_=[(n,C.c_float) for n in ('radius','normal_input','handbrake_input','angular_speed','drive_torque','brake_torque','angular_acceleration')]+[(n,C.c_uint32) for n in ('axle','locked','direction')]
class ContactWheel(C.Structure):
    _fields_=[('brake',BrakeState),('wheel_index',C.c_uint32)]+[(n,C.c_float) for n in ('normal_load','lateral_force','longitudinal_force','lateral_grip_factor','grip_factor','residual_torque','previous_longitudinal_velocity','longitudinal_slip','traction_factor','slip_angle_turns','last_lateral_velocity','lateral_scale','longitudinal_scale','slip_budget','curve_scale','combined_factor','coupling_13c')]
class GroundWheel(C.Structure):
    _fields_=[('tire',ContactWheel),('compression',C.c_float),('air_seconds',C.c_float)]
class RouteState(C.Structure):
    _fields_=[('history',C.c_float)]
class RouteInput(C.Structure):
    _fields_=[(n,C.c_float) for n in ('forward_speed','slip_angle_9c','handbrake','brake','throttle','seconds','blend_100','disable_110','steering','body_24','source_speed_bc','grip_d0','grip_d4','source_e4_70','yaw_control')]+[(n,C.c_uint32) for n in ('wheel_disable_mask','flags_c4','mode_c8','mode_cc')]+[(n,C.c_bool) for n in ('effect_present','controller_present','controller_byte_2a','settings_present')]+[(n,C.c_float) for n in ('effect_4','effect_8')]
class RouteResult(C.Structure):
    _fields_=[('slip',C.c_float),('wheel',C.c_uint)]
class TractionState(C.Structure):
    _fields_=[('stage',C.c_uint32),('timer',C.c_float),('scale',C.c_float),('quiet_time',C.c_float)]
class YawState(C.Structure):
    _fields_=[('stage',C.c_uint32),('ramp',C.c_float)]
class AssistState(C.Structure):
    _fields_=[('route',RouteState),('traction',TractionState),('yaw',YawState)]
class AssistInput(C.Structure):
    _fields_=[('routing',RouteInput),('yaw_samples',C.POINTER(C.c_float)),('yaw_count',C.c_uint32),('engine_interface_present',C.c_bool)]+[(n,C.c_float) for n in ('engine_max_speed','averaged_steering','local_angular_y')]+[('body_up',C.c_float*3),('source_a4',C.c_float),('contact_count',C.c_uint32)]
class AssistOutput(C.Structure):
    _fields_=[('route',RouteResult),('torque_present',C.c_bool),('controller_a4_present',C.c_bool),('torque_world',C.c_float*3),('controller_a4_argument',C.c_float)]

class CollisionState(C.Structure):
    _fields_=[(n,C.c_float) for n in ('collision_timer','wall_nose_turn','wall_side_turn','last_ground_time')]
class CollisionInput(C.Structure):
    _fields_=[('flags',C.c_uint32),('owner_is_object_b',C.c_bool),('collision_body_present',C.c_bool)]+[(n,C.c_float*3) for n in ('position','normal','closing_velocity','object_a_velocity')]+[(n,C.c_float) for n in ('impulse_a','impulse_b')]+[(n,C.c_float*3) for n in ('body_position','body_forward','body_right','body_dimension')]+[(n,C.c_float) for n in ('signed_speed','source_time')]
class WallInput(C.Structure):
    _fields_=[('body_matrix',C.c_float*16),('angular_velocity_world',C.c_float*3),('steering',C.c_float),('throttle',C.c_float),('gear',C.c_uint32),('contact_count',C.c_uint32)]
class WallOutput(C.Structure):
    _fields_=[('count',C.c_uint32),('angular_velocity_world',(C.c_float*3)*2)]

def f32(x):return C.c_float(x).value
def bits(x):return struct.pack('>f',x)

class PlayerReference(OriginalWheelFrameReference):
    def __init__(self,raw):
        if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected USA executable')
        super().__init__(raw,None);self.image=DolImage(raw)
        self.extra_allowed+=((0x802484f8,0x80248a34),(0x80208ec4,0x80208fa4),
            (0x802090b4,0x80209190),(0x8020982c,0x802099cc),(0x802782fc,0x80278308),
            (0x80249910,0x80249d80),(0x80249004,0x802490b0))
        self.inputs=None;self.kind='steering';self.engine_max_speed=0
        # Exact constructor-derived uniform descriptors. Original source
        # read-only sample arrays remain in place; BSS pointers/state supplied.
        for at,count,lo,hi,data in ((0x80489f78,21,-1,1,0x8041f488),
            (0x80489fc8,10,0,160,0x8041f374),(0x80489fdc,10,0,160,0x8041f3dc),
            (0x80489ff0,6,0,1,0x8041f39c),(0x8048a004,10,0,160,0x8041f3b4),
            (0x8048a018,6,0,10,0x8041f404),(0x8048a02c,6,0,1,0x8041f41c)):
            self.u.mem_write(at,struct.pack('>I3fI',count,lo,hi,f32((count-1)/f32(hi-lo)),data))
        self.u.mem_write(0x80489f4c,struct.pack('>8f',0,.2,.2,.5,.5,.7,.7,1))
        self.u.mem_write(0x80489f6c,struct.pack('>2I',0x80489f4c,4))
        self.u.mem_write(0x60005004,struct.pack('>I',0x60005100));self.u.mem_write(0x60005148,struct.pack('>II',0,0x6000f000))
        self.u.mem_write(0x60005204,struct.pack('>I',0x60005300));self.u.mem_write(0x60005380,struct.pack('>II',0,0x6000f010))
        self.u.mem_write(0x60005404,struct.pack('>I',0x60005500));self.u.mem_write(0x60005520,struct.pack('>IIII',0,0x6000f020,0,0x6000f030))
        self.u.mem_write(0x60005604,struct.pack('>I',0x60005700));self.u.mem_write(0x600058a0,struct.pack('>II',0,0x6000f040))
        self.u.mem_write(0x60005330,struct.pack('>II',0,0x6000f050))
        self.u.mem_write(0x60005b04,struct.pack('>I',0x60005c00));self.u.mem_write(0x60005c40,struct.pack('>II',0,0x6000f060))
        self.extra_allowed+=((0x802490b0,0x802492a0),(0x80058124,0x8005812c))
        self.extra_allowed+=((0x802498b4,0x80249ea4),(0x80248b5c,0x80248e48),(0x802492a0,0x802498b4),
            (0x80209080,0x802090a4),(0x8005e0c8,0x8005e168))
        self.u.mem_write(0x8048a040,struct.pack('>II',0x8041f584,6))
        degrees=f32(.01745329424738884)
        points=[0,0,f32(15*degrees),.1,f32(30*degrees),.45,f32(45*degrees),.85,f32(60*degrees),.95,f32(89*degrees),1.15,f32(90*degrees),0]
        self.u.mem_write(0x8048a048,struct.pack('>14f',*points));self.u.mem_write(0x8048a080,struct.pack('>II',0x8048a048,7))
        self.u.mem_write(0x8048a088,struct.pack('>I3fI',10,0,1,9,0x8041f608))
        self.u.mem_write(0x60005d04,struct.pack('>I',0x60005e00));self.u.mem_write(0x60005e00+0x120,struct.pack('>II',0,0x6000f070))
        self.u.mem_write(0x600053a0,struct.pack('>II',0,0x6000f080));self.commands=[]
        self.curve_evidence=[{'start':f'{a:08x}','end_exclusive':f'{b:08x}','sha256':hashlib.sha256(self.image.read(a,b-a)).hexdigest()} for a,b in ((0x80265a24,0x80265bc0),(0x802473fc,0x8024744c),(0x802486ec,0x80248984),(0x802498b4,0x80249ea4),(0x80248b5c,0x80248e48),(0x802492a0,0x802498b4),(0x80244c2c,0x80244e18),(0x8031dad0,0x8031dbac),(0x8031dcbc,0x8031dd98),(0x8031e4bc,0x8031e654),(0x8031e868,0x8031f4c0),(0x8024812c,0x802484f8),(0x80248e48,0x80249004))]
    def _hook(self,u,pc,size,data):
        if pc in (0x6000f090,0x6000f0a0,0x6000f0b0,0x6000f0c0,0x6000f0d0,0x6000f0e0):
            if pc==0x6000f090:u.reg_write(UC_PPC_REG_3,0x60007000)
            elif pc==0x6000f0a0:u.mem_write(u.reg_read(UC_PPC_REG_3),bytes(u.mem_read(0x60007100,12)))
            elif pc==0x6000f0b0:u.reg_write(UC_PPC_REG_3,0x60007200)
            elif pc==0x6000f0c0:u.reg_write(UC_PPC_REG_3,0x60007300)
            elif pc==0x6000f0d0:self.putfloating(1,self.collision_input.signed_speed)
            else:self.wall_commands.append(bytes(u.mem_read(u.reg_read(UC_PPC_REG_4),12)))
            u.reg_write(UC_PPC_REG_PC,u.reg_read(UC_PPC_REG_LR));return

        if pc in (0x6000f070,0x6000f080):
            self.commands.append(('torque',struct.unpack('>3f',bytes(u.mem_read(u.reg_read(UC_PPC_REG_4),12)))) if pc==0x6000f070 else ('controller',self.floating(1)))
            u.reg_write(UC_PPC_REG_PC,u.reg_read(UC_PPC_REG_LR));return
        if pc==0x6000f060:
            self.putfloating(1,self.engine_max_speed);u.reg_write(UC_PPC_REG_PC,u.reg_read(UC_PPC_REG_LR));return
        if pc==0x802490b0 and self.kind=='routing':
            self.putfloating(1,self.inputs.yaw_control);u.reg_write(UC_PPC_REG_PC,u.reg_read(UC_PPC_REG_LR));return
        if self.kind in ('routing','full_routing') and pc in (0x6000f000,0x6000f040,0x6000f050):
            i=self.inputs.routing if self.kind=='full_routing' else self.inputs
            answer={0x6000f000:0x60005200 if i.controller_present else 0,0x6000f040:0x60005800 if i.effect_present else 0,0x6000f050:0x60005900 if i.settings_present else 0}[pc]
            u.reg_write(UC_PPC_REG_3,answer);u.reg_write(UC_PPC_REG_PC,u.reg_read(UC_PPC_REG_LR));return
        if pc in (0x6000f000,0x6000f010,0x6000f020,0x6000f030,0x6000f040):
            i=self.inputs
            answer={0x6000f000:0x60005200,0x6000f010:0x60005400,0x6000f020:1,
                0x6000f030:i.interface_mode,0x6000f040:0x60005800 if i.effect_present else 0}[pc]
            u.reg_write(UC_PPC_REG_3,answer);u.reg_write(UC_PPC_REG_PC,u.reg_read(UC_PPC_REG_LR));return
        return super()._hook(u,pc,size,data)
    def put_average(self,at,a,buffer):
        raw=bytearray(0x38);raw[1:4]=bytes((a.capacity,a.count,a.cursor))
        struct.pack_into('>2fI',raw,8,a.sum,a.average,buffer)
        struct.pack_into('>fIII',raw,0x28,a.seconds,a.oldest,buffer+0x100,a.capacity*4)
        self.u.mem_write(at,bytes(raw));self.u.mem_write(buffer,struct.pack('>'+str(a.capacity)+'f',*a.values[:a.capacity]));self.u.mem_write(buffer+0x100,struct.pack('>'+str(a.capacity)+'f',*a.times[:a.capacity]))
    def get_average(self,at,capacity,buffer):
        raw=bytes(self.u.mem_read(at,0x38));a=Average();a.capacity=capacity;a.count=raw[2];a.cursor=raw[3]
        a.sum,a.average=struct.unpack_from('>2f',raw,8);a.seconds,a.oldest=struct.unpack_from('>fI',raw,0x28)
        for n,v in enumerate(struct.unpack('>'+str(capacity)+'f',bytes(self.u.mem_read(buffer,capacity*4)))):a.values[n]=v
        for n,v in enumerate(struct.unpack('>'+str(capacity)+'f',bytes(self.u.mem_read(buffer+0x100,capacity*4)))):a.times[n]=v
        return a
    def steering(self,state,i):
        self.kind='steering';self.inputs=i;u=self.u;car=0x60001000;common=0x60003000
        u.mem_write(car,bytes(0x220));u.mem_write(common,bytes(0xe0))
        for off,v in ((0x124,state.angle_degrees),(0x138,state.previous_input),(0x134,state.gain_history),(0x100,i.blend_100),(0x1ac,i.fade_1ac)):u.mem_write(car+off,bits(v))
        for off,v in ((0x38,0x60005000),(0x4c,0x60005600),(0xa8,0x60004000),(0x1c4,0x60007000),(0x1c8,0x60007200)):u.mem_write(car+off,struct.pack('>I',v))
        for off,v in ((0x48,i.forward_speed),(0x8c,i.raw_steering),(0x4c,i.throttle),(0x5c,i.brake),(0x7c,i.handbrake),(0xc0,i.seconds)):u.mem_write(common+off,bits(v))
        u.mem_write(0x60004048,bits(i.tire_steering));u.mem_write(0x60005800,bits(i.effect_0))
        u.mem_write(0x60007118,bits(i.rear_slip_angle_turns[0]));u.mem_write(0x60007318,bits(i.rear_slip_angle_turns[1]))
        u.mem_write(0x8049896c,bits(i.time))
        self.put_average(car+0x13c,state.input_average,0x60006000);self.put_average(car+0x174,state.rate_average,0x60006400)
        self.run(0x802484f8,0x6000fff0,[(UC_PPC_REG_3,car),(UC_PPC_REG_4,common)])
        out=SteeringState();out.angle_degrees=struct.unpack('>f',bytes(u.mem_read(car+0x124,4)))[0];out.previous_input=struct.unpack('>f',bytes(u.mem_read(car+0x138,4)))[0];out.gain_history=struct.unpack('>f',bytes(u.mem_read(car+0x134,4)))[0]
        out.input_average=self.get_average(car+0x13c,33,0x60006000);out.rate_average=self.get_average(car+0x174,9,0x60006400)
        return out,self.floating(1)
    def routing(self,state,i,wheels,full=None):
        self.kind='routing';self.inputs=i;u=self.u;car=0x60001000;common=0x60003000
        u.mem_write(car,bytes(0x220));u.mem_write(common,bytes(0xe0))
        for off,v in ((0x1b8,state.history),(0x100,i.blend_100),(0x110,i.disable_110)):u.mem_write(car+off,bits(v))
        for off,v in ((0x38,0x60005000),(0x4c,0x60005600),(0xe4,0x60005a00)):u.mem_write(car+off,struct.pack('>I',v))
        u.mem_write(0x60005a70,bits(i.source_e4_70));u.mem_write(0x6000592a,bytes([i.controller_byte_2a]))
        u.mem_write(0x60005804,struct.pack('>2f',i.effect_4,i.effect_8))
        for off,v in ((0x24,i.body_24),(0x48,i.forward_speed),(0x4c,i.throttle),(0x5c,i.brake),(0x7c,i.handbrake),(0x8c,i.steering),(0x9c,i.slip_angle_9c),(0xbc,i.source_speed_bc),(0xc0,i.seconds),(0xd0,i.grip_d0),(0xd4,i.grip_d4)):u.mem_write(common+off,bits(v))
        u.mem_write(common+0xc4,struct.pack('>I4H',i.flags_c4,i.mode_c8,0,i.mode_cc,i.wheel_disable_mask))
        fields={'normal_input':0xc8,'handbrake_input':0xcc,'grip_factor':0xec,'lateral_grip_factor':0xe8,'lateral_scale':0x11c,'longitudinal_scale':0x120,'longitudinal_slip':0xf0,'combined_factor':0x12c}
        for n,w in enumerate(wheels):
            at=0x60008000+n*0x180;u.mem_write(at,bytes(0x140));u.mem_write(car+0x1bc+n*4,struct.pack('>I',at))
            for name,off in fields.items():u.mem_write(at+off,bits(getattr(w.tire.brake if name.endswith('input') else w.tire,name)))
        if full:
            s,a=full;self.kind='full_routing';self.inputs=a;self.commands=[];self.engine_max_speed=a.engine_max_speed
            u.mem_write(car+0xf0,struct.pack('>I',0x60005d00));u.mem_write(car+0xf8,struct.pack('>I',0x60005b00 if a.engine_interface_present else 0));u.mem_write(car+0xa8,struct.pack('>I',0x60004000))
            samples=[a.yaw_samples[k] for k in range(a.yaw_count)];u.mem_write(0x60004000,struct.pack('>HHI',len(samples),len(samples),0)+struct.pack('>'+str(len(samples))+'f',*samples))
            u.mem_write(car+0x104,struct.pack('>I',a.contact_count));u.mem_write(car+0x10c,struct.pack('>If',s.yaw.stage,s.yaw.ramp));u.mem_write(car+0x114,struct.pack('>I3f',s.traction.stage,s.traction.timer,s.traction.scale,s.traction.quiet_time))
            for off,value in ((0x148,a.averaged_steering),):u.mem_write(car+off,bits(value))
            for off,value in ((0x94,a.local_angular_y),(0xa4,a.source_a4)):u.mem_write(common+off,bits(value))
            u.mem_write(common+0x10,struct.pack('>3f',*a.body_up))
            self.run(0x802498b4,0x6000fff0,[(UC_PPC_REG_3,car),(UC_PPC_REG_4,common)])
        else:self.run(0x80249910,0x80249d80,[(UC_PPC_REG_3,car),(UC_PPC_REG_4,common)])
        result=(GroundWheel*4).from_buffer_copy(bytes(wheels))
        for n,w in enumerate(result):
            at=0x60008000+n*0x180
            for name,off in fields.items():setattr(w.tire.brake if name.endswith('input') else w.tire,name,struct.unpack('>f',bytes(u.mem_read(at+off,4)))[0])
        route_state=RouteState(struct.unpack('>f',bytes(u.mem_read(car+0x1b8,4)))[0])
        if not full:return route_state,result,RouteResult(self.floating(26),u.reg_read(UC_PPC_REG_24))
        answer=AssistState();answer.route=route_state;answer.traction=TractionState(*struct.unpack('>I3f',bytes(u.mem_read(car+0x114,16))));answer.yaw=YawState(*struct.unpack('>If',bytes(u.mem_read(car+0x10c,8))))
        for j,w in enumerate(result):w.tire.combined_factor=struct.unpack('>f',bytes(u.mem_read(0x60008000+j*0x180+0x12c,4)))[0]
        return answer,result,self.commands
    def yaw_control(self,samples,speed,present,max_speed):
        self.kind='yaw_control';self.engine_max_speed=max_speed;u=self.u;car=0x60001000;layout=0x60004000
        u.mem_write(car,bytes(0x200));u.mem_write(car+0xf8,struct.pack('>I',0x60005b00 if present else 0));u.mem_write(car+0xa8,struct.pack('>I',layout))
        u.mem_write(layout,struct.pack('>HHI',len(samples),len(samples),0)+struct.pack('>'+str(len(samples))+'f',*samples));self.putfloating(1,speed)
        self.run(0x802490b0,0x6000fff0,[(UC_PPC_REG_3,car)]);return self.floating(1)

def verify_collision(ref,dll):
    rng=random.Random(20051115);u=ref.u;car=0x60001000;common=0x60003000;info=0x6000c000
    event=dll.mw_player_collision_event;event.argtypes=[C.POINTER(CollisionState),C.POINTER(CollisionInput)];event.restype=C.c_bool
    wall=dll.mw_player_wall_steering;wall.argtypes=[C.POINTER(CollisionState),C.POINTER(WallInput),C.POINTER(WallOutput)];wall.restype=C.c_bool
    ref.extra_allowed+=((0x8024812c,0x802484f8),(0x80248e48,0x80249004),(0x80314950,0x80314a50))
    changed=[0,0,0];commands_seen=[0,0,0]
    for n in range(2048):
        u.mem_write(car,bytes(0x220));u.mem_write(info,bytes(128))
        def vector(scale=1):return (C.c_float*3)(*[rng.uniform(-scale,scale) for _ in range(3)])
        i=CollisionInput(flags=((n%4)<<29)|((n%16)<<25),owner_is_object_b=n%2==0,collision_body_present=n%3!=0,
            position=vector(4),normal=vector(),closing_velocity=vector(5),object_a_velocity=vector(2),impulse_a=rng.uniform(0,60),impulse_b=rng.uniform(0,60),
            body_position=vector(),body_forward=vector(),body_right=vector(),body_dimension=vector(2),signed_speed=rng.uniform(-20,20),source_time=rng.uniform(100,200))
        if n%3==0:i.normal[1]=0
        if n%5==0:i.object_a_velocity=(C.c_float*3)(0,0,0)
        state=CollisionState(rng.uniform(0,1),rng.choice((0,rng.uniform(-1,1))),rng.choice((0,rng.uniform(-1,1))),0)
        if n%16==0:
            i.flags=0x40000000;i.collision_body_present=True;i.impulse_a=25;i.owner_is_object_b=False
            i.position=(C.c_float*3)(0,0,3);i.normal=(C.c_float*3)(.6 if n%32 else -.6,0,-.8)
            i.closing_velocity=(C.c_float*3)(0,0,-.1);i.object_a_velocity=(C.c_float*3)(0,0,0)
            i.body_position=(C.c_float*3)(0,0,0);i.body_forward=(C.c_float*3)(0,0,1);i.body_right=(C.c_float*3)(1,0,0);i.body_dimension=(C.c_float*3)(1,1,2)
            i.signed_speed=-1 if n%32 else 1;state.collision_timer=0;state.wall_nose_turn=0;state.wall_side_turn=0
        ref.collision_input=i
        for off,value in ((0x1ac,state.collision_timer),(0x1b0,state.wall_nose_turn),(0x1b4,state.wall_side_turn),(0x108,state.last_ground_time)):u.mem_write(car+off,bits(value))
        for off,address in ((0x38,0x60005000),(0xf0,0x60005d00),(0xf4,0x6000b000 if i.collision_body_present else 0),(0x4c,0x60005600)):u.mem_write(car+off,struct.pack('>I',address))
        u.mem_write(0x60005008,struct.pack('>I',0x12345678));u.mem_write(info+0x4c,struct.pack('>I',0x12345678 if i.owner_is_object_b else 0x87654321))
        for off,value in ((0x1c,i.flags),):u.mem_write(info+off,struct.pack('>I',value))
        for off,value in ((0x5c,i.impulse_a),(0x6c,i.impulse_b)):u.mem_write(info+off,bits(value))
        for off,values in ((0,i.position),(0x10,i.normal),(0x20,i.closing_velocity),(0x50,i.object_a_velocity)):u.mem_write(info+off,struct.pack('>3f',*values))
        for address,values in ((0x60007000,i.body_position),(0x60007100,i.body_dimension),(0x60007200,i.body_forward),(0x60007300,i.body_right)):u.mem_write(address,struct.pack('>3f',*values))
        u.mem_write(0x60005e48,struct.pack('>II',0,0x6000f090));u.mem_write(0x60005ea0,struct.pack('>II',0,0x6000f0a0));u.mem_write(0x6000b004,struct.pack('>I',0x6000b100));u.mem_write(0x6000b238,struct.pack('>II',0,0x6000f0b0));u.mem_write(0x6000b240,struct.pack('>II',0,0x6000f0c0));u.mem_write(0x60005828,struct.pack('>II',0,0x6000f0d0));u.mem_write(0x8049896c,bits(i.source_time))
        ref.run(0x8024812c,0x6000fff0,[(UC_PPC_REG_3,car),(UC_PPC_REG_4,info)])
        want=CollisionState(*[struct.unpack('>f',bytes(u.mem_read(car+off,4)))[0] for off in (0x1ac,0x1b0,0x1b4,0x108)])
        old=CollisionState.from_buffer_copy(bytes(state));assert event(C.byref(state),C.byref(i))
        for j,name in enumerate(('collision_timer','wall_nose_turn','wall_side_turn')):changed[j]+=bits(getattr(old,name))!=bits(getattr(state,name))
        if bytes(state)!=bytes(want):raise AssertionError(('collision-event',n,list(bytes(state)),list(bytes(want))))
        w=WallInput(body_matrix=(C.c_float*16)(*[rng.uniform(-1,1) for _ in range(16)]),angular_velocity_world=vector(3),steering=rng.uniform(-1,1),throttle=rng.choice((0,.5,1)),gear=n%4,contact_count=n%5)
        for off,value in ((0x1ac,state.collision_timer),(0x1b0,state.wall_nose_turn),(0x1b4,state.wall_side_turn),(0x104,w.contact_count)):u.mem_write(car+off,struct.pack('>I',value) if off==0x104 else bits(value))
        u.mem_write(common,struct.pack('>16f',*w.body_matrix));u.mem_write(common+0x60,struct.pack('>3f',*w.angular_velocity_world));u.mem_write(common+0x4c,bits(w.throttle));u.mem_write(common+0x8c,bits(w.steering));u.mem_write(common+0xcc,struct.pack('>h',w.gear));u.mem_write(0x60005ed0,struct.pack('>II',0,0x6000f0e0));ref.wall_commands=[]
        ref.run(0x80248e48,0x6000fff0,[(UC_PPC_REG_3,car),(UC_PPC_REG_4,common)]);out=WallOutput();assert wall(C.byref(state),C.byref(w),C.byref(out))
        commands=[b''.join(bits(v) for v in out.angular_velocity_world[j]) for j in range(out.count)]
        commands_seen[out.count]+=1
        if commands!=ref.wall_commands:raise AssertionError(('wall-steering',n,[x.hex() for x in commands],[x.hex() for x in ref.wall_commands]))
    begin=dll.mw_player_collision_begin;begin.argtypes=[C.POINTER(CollisionState),C.c_float];begin.restype=C.c_bool
    end=dll.mw_player_collision_end;end.argtypes=[C.POINTER(CollisionState)]
    ref.extra_allowed+=((0x80247ac4,0x80247aec),(0x80247d40,0x80247d54))
    for n in range(256):
        state=CollisionState(rng.uniform(0,1),rng.uniform(-1,1),rng.uniform(-1,1),123);dt=f32(rng.choice((1/120,1/60,1/30)))
        u.mem_write(car+0x1ac,bits(state.collision_timer));u.mem_write(0x7000fcc8,bits(dt))
        ref.run(0x80247ac4,0x80247aec,[(UC_PPC_REG_30,car),(UC_PPC_REG_31,0x80400000)])
        assert begin(C.byref(state),dt)
        if bits(state.collision_timer)!=bytes(u.mem_read(car+0x1ac,4)):raise AssertionError(('collision-timer',n))
        u.mem_write(car+0x1b0,bits(state.wall_nose_turn));u.mem_write(car+0x1b4,bits(state.wall_side_turn))
        ref.run(0x80247d40,0x80247d54,[(UC_PPC_REG_30,car)])
        end(C.byref(state))
        if bits(state.wall_nose_turn)+bits(state.wall_side_turn)!=bytes(u.mem_read(car+0x1b0,8)):raise AssertionError(('collision-end',n))
    return {'collision_event_cases':2048,'wall_steering_cases':2048,'collision_tick_boundary_cases':256,
        'collision_changed_timer_nose_side':changed,'wall_command_counts_0_1_2':commands_seen}

def verify_geometry(ref,dll):
    rng=random.Random(20051114)
    ref.u.reg_write(UC_PPC_REG_13,0x80506dc0);ref.u.reg_write(UC_PPC_REG_2,0x80516dc0)
    trig=dll.mw_player_source_sincos;trig.argtypes=[C.c_float,C.POINTER(C.c_float),C.POINTER(C.c_float)];trig.restype=C.c_bool
    directions=dll.mw_player_steer_directions;directions.argtypes=[C.POINTER(C.c_float),C.c_float,C.c_float,C.c_float,C.POINTER(C.c_float)];directions.restype=C.c_bool
    ref.extra_allowed+=((0x8031dad0,0x8031dbd0),(0x8031dcbc,0x8031dd98),(0x8031e4bc,0x8031e654),(0x8031e868,0x8031f4c0),(0x8031dbd0,0x8031dc98),(0x8031e07c,0x8031e1cc),(0x80244c2c,0x80244e18))
    samples=[0.,-0.,1e-20,-1e-20]+[f32(v) for v in (.785398,1.5707963,2.3561945,3.1415927,6.2831855,50,200)]+[f32(rng.uniform(-201,201)) for _ in range(4096)]
    samples.extend(f32(rng.uniform(-400,400)) for _ in range(2048))
    for _ in range(256):
        word=rng.getrandbits(32)
        if word&0x7f800000!=0x7f800000:
            value=struct.unpack('>f',struct.pack('>I',word))[0]
            if abs(value)<=400:samples.append(value)
    for multiple in range(1,256):
        center=struct.unpack('>I',bits(f32(multiple*1.5707963267948966)))[0]
        for delta in range(-8,9):
            value=struct.unpack('>f',struct.pack('>I',center+delta))[0]
            if value<=400:samples.extend((value,-value))
    for n,x in enumerate(samples):
        answer=[]
        for address in (0x8031dcbc,0x8031dad0):
            ref.putfloating(1,x);ref.run(address,0x6000fff0,[]);answer.append(ref.floating(1))
        sine=C.c_float();cosine=C.c_float();assert trig(x,C.byref(sine),C.byref(cosine))
        if [bits(sine.value),bits(cosine.value)]!=[bits(v) for v in answer]:raise AssertionError(('source-trig',n,x,[sine.value,cosine.value],answer))
    for n in range(1024):
        turns=f32(rng.uniform(-.49,.99));track=f32(rng.uniform(1,2));base=f32(rng.uniform(2,4));matrix=(C.c_float*16)(*[rng.uniform(-1,1) for _ in range(16)]);result=(C.c_float*12)()
        ref.u.mem_write(0x6000107c,struct.pack('>I',0x60002000));ref.u.mem_write(0x60002020,bits(track));ref.u.mem_write(0x60002054,bits(base));ref.u.mem_write(0x60003000,struct.pack('>16f',*matrix));ref.putfloating(1,turns)
        ref.run(0x80244c2c,0x6000fff0,[(UC_PPC_REG_3,0x60001000),(UC_PPC_REG_4,0x60003000),(UC_PPC_REG_5,0x6000a000),(UC_PPC_REG_6,0x6000a020)])
        expected=[struct.unpack('>3f',bytes(ref.u.mem_read(at,12))) for at in (0x6000a000,0x6000a020)]
        assert directions(matrix,turns,track,base,result)
        if [bits(v) for v in result[:6]]!=[bits(v) for vector in expected for v in vector]:raise AssertionError(('world-directions',n,turns,list(result[:6]),expected))
    return {'source_sincos_cases':len(samples),'ackermann_world_direction_cases':1024}

def verify(dol,output=None,attributes=None):
    raw=dol.read_bytes();ref=PlayerReference(raw);rng=random.Random(20051113);cases=0;route_cases=0;yaw_cases=0;full_cases=0;charge_cases=0;profiles=[]
    if attributes:
        from vehicle_attributes import VehicleAttributes
        from vehicle_export_contact import component_reference
        from vehicle_verify_original import ATTR_SHA
        attr=attributes.read_bytes()
        if hashlib.sha256(attr).hexdigest()!=ATTR_SHA:raise ValueError('Unexpected attributes revision')
        db=VehicleAttributes(attr)
        for name in ('m3gtre46careerstart','bmwm3gtre46','cobaltss','gti','is300','punto'):
            p=db.find('pvehicle',name);t,_=component_reference(db,p,'tires',0)
            profiles.append({'name':name,'physical_key':f'{p["key"]:08x}','tires_key':f'{t["key"]:08x}',
                'steering':db.field_value(t,'STEERING')['value'],'yaw_control':db.field_value(t,'YAW_CONTROL')['value']['values']})
    with tempfile.TemporaryDirectory(prefix='mw-player-input-') as tmp:
        lib=Path(tmp)/'input.so'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(ROOT/'include'),str(ROOT/'source_bmw/mw_original_player_input.c'),str(ROOT/'source_bmw/mw_physics_grip.c'),'-lm','-o',str(lib)],check=True)
        dll=C.CDLL(str(lib));init=dll.mw_player_steering_init;init.argtypes=[C.POINTER(SteeringState)];init.restype=C.c_bool
        step=dll.mw_player_steering_step;step.argtypes=[C.POINTER(SteeringState),C.POINTER(SteeringInput),C.POINTER(C.c_float)];step.restype=C.c_bool
        route=dll.mw_player_route_wheels;route.argtypes=[C.POINTER(RouteState),C.POINTER(RouteInput),C.POINTER(GroundWheel),C.POINTER(RouteResult)];route.restype=C.c_bool
        yaw=dll.mw_player_yaw_control;yaw.argtypes=[C.POINTER(C.c_float),C.c_uint32,C.c_float,C.c_bool,C.c_float,C.POINTER(C.c_float)];yaw.restype=C.c_bool
        fullroute=dll.mw_player_input_route;fullroute.argtypes=[C.POINTER(AssistState),C.POINTER(AssistInput),C.POINTER(GroundWheel),C.POINTER(AssistOutput)];fullroute.restype=C.c_bool
        charge=dll.mw_player_charge_gamebreaker;charge.argtypes=[C.POINTER(C.c_float),C.c_float];charge.restype=C.c_bool
        ref.extra_allowed+=((0x80289384,0x802893cc),)
        for n in range(256):
            before=f32((n-128)/64);amount=f32((n%31-15)/7);actual=C.c_float(before)
            ref.u.mem_write(0x6000108c,bits(before));ref.putfloating(1,amount)
            ref.run(0x80289384,0x6000fff0,[(UC_PPC_REG_3,0x60001000)])
            expected=bytes(ref.u.mem_read(0x6000108c,4));assert charge(C.byref(actual),amount)
            if bits(actual.value)!=expected:raise AssertionError(('gamebreaker-charge',n,actual.value,expected.hex()))
            charge_cases+=1
        for mode in range(3):
            for scale in [.5,1,1.5,2]+[p['steering'] for p in profiles]:
                state=SteeringState();assert init(C.byref(state));time=100.0
                for frame in range(192):
                    dt=f32(rng.choice((1/120,1/60,1/30)));time=f32(time+dt)
                    i=SteeringInput(raw_steering=rng.uniform(-1,1),forward_speed=rng.uniform(-35,190),throttle=rng.choice((0,.5,1)),brake=rng.choice((0,.5,1)),handbrake=rng.choice((0,1)),seconds=dt,time=time,tire_steering=scale,rear_slip_angle_turns=(C.c_float*2)(rng.uniform(-.2,.2),rng.uniform(-.2,.2)),blend_100=rng.choice((0,.25,1)),fade_1ac=rng.choice((0,.2,.9,1)),interface_mode=mode,effect_present=frame%2==0,effect_0=rng.uniform(-1,1))
                    want,value=ref.steering(state,i);actual=C.c_float();assert step(C.byref(state),C.byref(i),C.byref(actual))
                    if bytes(state)!=bytes(want) or bits(actual.value)!=bits(value):
                        differences=[]
                        for name,_ in SteeringState._fields_:
                            a,b=getattr(state,name),getattr(want,name)
                            if name.endswith('average'):
                                if bytes(a)!=bytes(b):differences.append((name,{n:(getattr(a,n),getattr(b,n)) for n in ('sum','average','count','cursor','oldest') if getattr(a,n)!=getattr(b,n)}))
                            elif bits(a)!=bits(b):differences.append((name,a,b))
                        raise AssertionError({'mode':mode,'scale':scale,'frame':frame,'output':[actual.value,value],'state':differences,'input':{n:getattr(i,n) for n,_ in SteeringInput._fields_ if n!='rear_slip_angle_turns'}})
                    cases+=1
        for n in range(2048):
            i=RouteInput(forward_speed=rng.uniform(-20,70),slip_angle_9c=rng.uniform(-20,100),handbrake=rng.choice((0,.1,.5,1)),brake=rng.choice((0,.5,1)),throttle=rng.choice((0,.8,1)),seconds=rng.choice((1/120,1/60,1/30)),blend_100=rng.choice((0,.25,1)),disable_110=rng.uniform(0,1),steering=rng.uniform(-1,1),body_24=rng.uniform(-1,1),source_speed_bc=rng.uniform(0,80),grip_d0=rng.uniform(.3,2),grip_d4=rng.uniform(.3,2),source_e4_70=rng.choice((-1,0,1,2)),yaw_control=rng.uniform(.1,2),wheel_disable_mask=n%16,flags_c4=n%2,mode_c8=n%3,mode_cc=2,effect_present=n%2==0,controller_present=n%3!=0,controller_byte_2a=n%5==0,settings_present=n%4!=0,effect_4=rng.uniform(-1,1),effect_8=rng.uniform(-1,1))
            state=RouteState(rng.uniform(0,1));wheels=(GroundWheel*4)()
            for j,w in enumerate(wheels):
                w.tire.grip_factor=rng.uniform(.1,2);w.tire.lateral_grip_factor=rng.uniform(.1,2);w.tire.longitudinal_slip=rng.uniform(-1,2);w.tire.lateral_scale=rng.uniform(.1,2);w.tire.longitudinal_scale=rng.uniform(.1,2)
            want,expected,result=ref.routing(state,i,wheels);actual=RouteResult();assert route(C.byref(state),C.byref(i),wheels,C.byref(actual))
            if bytes(state)!=bytes(want) or bytes(wheels)!=bytes(expected) or bytes(actual)!=bytes(result):
                raise AssertionError({'route_case':n,'history':[state.history,want.history],'slip':[actual.slip,result.slip],'wheel':[actual.wheel,result.wheel],
                    'wheels':[{name:[getattr(wheels[j].tire.brake if name.endswith('input') else wheels[j].tire,name),getattr(expected[j].tire.brake if name.endswith('input') else expected[j].tire,name)] for name in ('normal_input','handbrake_input','grip_factor','lateral_grip_factor','lateral_scale','longitudinal_scale')} for j in range(4)]})
            route_cases+=1
        for p in profiles:
            samples=(C.c_float*len(p['yaw_control']))(*p['yaw_control'])
            for n in range(128):
                speed=f32(rng.uniform(-200,200));present=n%2==0;max_speed=f32((0,30,80,180)[n%4]);out=C.c_float()
                expected=ref.yaw_control(p['yaw_control'],speed,present,max_speed)
                assert yaw(samples,len(samples),speed,present,max_speed,C.byref(out))
                if bits(out.value)!=bits(expected):raise AssertionError(('yaw-control',p['name'],speed,present,max_speed,out.value,expected))
                yaw_cases+=1
        for n in range(2048):
            r=RouteInput(forward_speed=rng.uniform(-20,70),slip_angle_9c=rng.uniform(-.3,.3),handbrake=rng.choice((0,.5,1)),brake=rng.choice((0,.5,1)),throttle=rng.choice((0,.8,1)),seconds=rng.choice((1/120,1/60,1/30)),blend_100=rng.choice((0,.25,1)),disable_110=0,steering=rng.uniform(-1,1),body_24=rng.uniform(-1,1),source_speed_bc=rng.uniform(0,80),grip_d0=1,grip_d4=1,source_e4_70=rng.choice((-1,0,1,2)),yaw_control=0,wheel_disable_mask=n%16,flags_c4=n%2,mode_c8=n%3,mode_cc=n%3,effect_present=n%2==0,controller_present=n%3!=0,controller_byte_2a=n%5==0,settings_present=n%4!=0,effect_4=rng.uniform(-1,1),effect_8=rng.uniform(-1,1))
            samples=(C.c_float*4)(.1,.35,.4,.6)
            a=AssistInput(routing=r,yaw_samples=samples,yaw_count=4,engine_interface_present=n%2==0,engine_max_speed=rng.choice((0,30,80)),averaged_steering=rng.uniform(-1,1),local_angular_y=rng.uniform(-3,3),body_up=(C.c_float*3)(rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(-1,1)),source_a4=rng.uniform(.1,2),contact_count=n%5)
            s=AssistState(route=RouteState(rng.uniform(0,1)),traction=TractionState(n%7,rng.uniform(-.1,30),rng.uniform(0,1),rng.uniform(0,2)),yaw=YawState(n%4,rng.uniform(0,1)))
            a.routing.disable_110=s.yaw.ramp
            wheels=(GroundWheel*4)()
            for j,w in enumerate(wheels):w.tire.grip_factor=rng.uniform(.1,2);w.tire.lateral_grip_factor=1;w.tire.longitudinal_slip=rng.uniform(-1,30);w.tire.combined_factor=rng.uniform(.3,2)
            # Original prefix returns no peak-slip registers after fullcallee;
            # preserve the independent maximum from actual initial wheel data.
            max_slip=max(0,*[w.tire.longitudinal_slip for w in wheels]);max_wheel=next((j for j,w in enumerate(wheels) if w.tire.longitudinal_slip==max_slip),0)
            want,expected,commands=ref.routing(s.route,a.routing,wheels,(s,a));out=AssistOutput();assert fullroute(C.byref(s),C.byref(a),wheels,C.byref(out))
            expected_commands=[]
            if out.controller_a4_present:expected_commands.append(('controller',out.controller_a4_argument))
            if out.torque_present:expected_commands.append(('torque',tuple(out.torque_world)))
            different=[]
            if bytes(s)!=bytes(want):different.append(('state',bytes(s).hex(),bytes(want).hex()))
            if bytes(wheels)!=bytes(expected):different.append(('wheels',[w.tire.combined_factor for w in wheels],[w.tire.combined_factor for w in expected]))
            def command_bits(entries):
                return [(kind,b''.join(bits(x) for x in value) if isinstance(value,tuple) else bits(value)) for kind,value in entries]
            if command_bits(commands)!=command_bits(expected_commands):different.append(('commands',commands,expected_commands))
            if out.route.slip!=max_slip or out.route.wheel!=max_wheel:different.append(('max',out.route.slip,max_slip,out.route.wheel,max_wheel))
            if different:raise AssertionError({'full_case':n,'differences':different})
            full_cases+=1
        collision_report=verify_collision(ref,dll)
        geometry_report=verify_geometry(ref,dll)
    report={'schema':1,**geometry_report,**collision_report,'dol_sha256':DOL_SHA256,'steering_stateful_cases':cases,'wheel_route_prefix_cases':route_cases,'yaw_control_getter_cases':yaw_cases,'complete_route_cases':full_cases,'gamebreaker_charge_cases':charge_cases,'physical_profiles':profiles,'float_bit_mismatches':0,'source_windows':ref.curve_evidence,
        'limits':['External mode/effect/time providers explicitly supplied; original call instructions and numerical routines unchanged',
            'Source initial uniform curves and writable calibration1.45 are initialized values, not arbitrary post-startup tuning',
            'Source game input/common-state producers and whole-body integration remain separate',
            'Shared Gekko paired ABI float model excludes FPSCR/subnormal/arbitrary exception claims']}
    if output:output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();print(json.dumps(verify(a.dol,a.output,a.attributes),indent=2))
