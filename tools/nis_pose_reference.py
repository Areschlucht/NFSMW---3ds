#!/usr/bin/env python3
"""Bounded original ROOT/SQT/world matrix comparison; private inputs only."""
import argparse
import ctypes as C
import json
import math
import struct
from pathlib import Path
from nis_actor_bindings import AnimationBank
from map_recovery_contact_reference import OriginalContactReference
from unicorn.ppc_const import *

class PoseReference(OriginalContactReference):
    def __init__(self,dol):
        super().__init__(dol,None)
        self.extra_allowed=((0x800a37dc,0x800a3ca4),(0x80090448,0x80090550),(0x800a3d78,0x800a3db4),(0x8005e024,0x8005e050),(0x8010ab28,0x8010ab58),(0x80329ea0,0x80329fa4),(0x80329e5c,0x80329ea0),(0x8005d4b0,0x8005d548),(0x8004ceb0,0x8004d014))
        self.terrain_enabled=False
    def _hook(self,u,address,size,data):
        if self.terrain_enabled:
            if address==0x802f0fdc:
                self.query=dict(mask_type=list(struct.unpack('>2I',bytes(u.mem_read(u.reg_read(UC_PPC_REG_3),8)))),point=list(struct.unpack('>3f',bytes(u.mem_read(u.reg_read(UC_PPC_REG_4),12)))),normal_pointer=u.reg_read(UC_PPC_REG_6))
                if self.terrain_hit:u.mem_write(u.reg_read(UC_PPC_REG_5),struct.pack('>f',self.terrain_height))
                u.reg_write(UC_PPC_REG_3,self.terrain_hit);u.reg_write(UC_PPC_REG_PC,u.reg_read(UC_PPC_REG_LR));return
            if address==0x8019480c:
                u.reg_write(UC_PPC_REG_3,0x60005100);u.reg_write(UC_PPC_REG_PC,u.reg_read(UC_PPC_REG_LR));return
            if address==0x6000ffe0:
                self.vehicle_matrix=bytes(u.mem_read(u.reg_read(UC_PPC_REG_4),64));u.reg_write(UC_PPC_REG_3,1);u.reg_write(UC_PPC_REG_PC,u.reg_read(UC_PPC_REG_LR));return
        return super()._hook(u,address,size,data)
    def call(self,address,args):
        u=self.u;u.reg_write(UC_PPC_REG_1,0x7000ff00);u.reg_write(UC_PPC_REG_LR,0x6000fff0)
        for i,value in enumerate(args):u.reg_write(UC_PPC_REG_3+i,value)
        u.emu_start(address,0x6000fff0,timeout=200000,count=200000)
        if u.reg_read(UC_PPC_REG_PC)!=0x6000fff0:raise ValueError('Original pose reference budget exceeded')


def verify(dol,root_bundle,inputs,library):
    ref=PoseReference(dol);u=ref.u;root_data=root_bundle[80:368]
    if root_data[32:36]!=bytes.fromhex('14140014') or struct.unpack_from('>I',root_data,40)[0]!=2:raise ValueError('Expected original ROOT skeleton')
    u.mem_write(0x60010000,root_data);ref.call(0x800a39d8,[0x60010020,0x60001000,0]);still=bytes(u.mem_read(0x60001000,96));rest=list(struct.unpack('>24f',still))
    expected=[1.,1.,1.,1.,0.,0.,0.,1.,0.,0.,0.,1.]*2
    if rest!=expected:raise ValueError('Unexpected ROOT still pose')
    lib=C.CDLL(str(library));ptr=C.POINTER(C.c_float);lib.mw_nis_pose_vehicle.argtypes=[ptr]*7;lib.mw_nis_pose_ground_height.argtypes=[ptr,C.c_int,C.c_float]
    mathlib=C.CDLL('libm.so.6');mathlib.fmaf.argtypes=[C.c_float]*3;mathlib.fmaf.restype=C.c_float
    array=lambda values:(C.c_float*len(values))(*values)
    f32=lambda x:struct.unpack('>f',struct.pack('>f',x))[0]
    def sample(curve,time):
        time=min(max(time,0),curve['frames']-1);frame=int(time);fraction=f32(time-frame)
        if not fraction:return curve['values'][frame]
        return [mathlib.fmaf(fraction,d,v) for v,d in zip(curve['values'][frame],curve['deltas'][frame])]
    cases=0;last_source=None
    for path in sorted(inputs):
        bank=AnimationBank(path.read_bytes());actors={}
        for c in bank.curves:
            prefix,kind=c['name'].rsplit('_',1);actors.setdefault(prefix,{})[kind]=c['children'][0]
        for prefix,curves in actors.items():
            maximum=max(c['frames']-1 for c in curves.values())
            for time in sorted({0.,.5,maximum/2+.25,float(maximum)}):
                pose=rest.copy();sc=sample(curves['s'],time) if 's' in curves else [1.,1.,1.];q=sample(curves['q'],time);t=sample(curves['t'],time)
                pose[12:15]=sc;pose[16:20]=q;pose[20:23]=t
                for angle,origin in [(0.,(0.,0.,0.)),(.4375,(1450.25,-300.5,101.75)),(-1.2345,(-200.,750.,53.25))]:
                    cs,sn=f32(math.cos(angle)),f32(math.sin(angle));rotation=[cs,sn,0.,0.,-sn,cs,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.];translation=[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,*origin,1.]
                    u.mem_write(0x60001000,struct.pack('>24f',*pose));ref.call(0x800a37dc,[0x60010020,0x60001000,0x60002000,0]);u.mem_write(0x60003000,bytes(u.mem_read(0x60002040,64)))
                    u.mem_write(0x60004000,struct.pack('>16f',*rotation));u.mem_write(0x60004100,struct.pack('>16f',*translation));ref.call(0x8005e024,[0x60003000,0x60004000,0x60003000]);ref.call(0x8005e024,[0x60003000,0x60004100,0x60003000]);source=bytes(u.mem_read(0x60003000,64));ref.call(0x8005d4b0,[0x60003000,0x60003000]);bond=bytes(u.mem_read(0x60003000,64))
                    out_source=array([0.]*16);out_bond=array([0.]*16)
                    if not lib.mw_nis_pose_vehicle(array(sc),array(q),array(t),array(rotation),array(translation),out_source,out_bond):raise ValueError('Native pose rejected valid source')
                    for label,actual,want in [('world',out_source,source),('bond',out_bond,bond)]:
                        raw=struct.pack('>16f',*actual)
                        if raw!=want:raise ValueError((prefix,time,angle,label,list(actual),struct.unpack('>16f',want)))
                    cases+=1;last_source=source
    # Execute the original outer terrain/vehicle stage with only external query
    # and COM vehicle destination mocked. This proves query inputs and height op.
    identity=struct.pack('>16f',1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)
    scene=bytearray(272);scene[0x44:0x84]=identity;scene[0x84:0xc4]=identity;u.mem_write(0x60006000,bytes(scene));u.mem_write(0x60007000,bytes(128));u.mem_write(0x6000702c,struct.pack('>I',0x60002000));u.mem_write(0x60002040,last_source)
    u.mem_write(0x80457610,struct.pack('>4I',0,0x60005000,0,0));u.mem_write(0x60005000,struct.pack('>I',0x60005080));u.mem_write(0x60005100,struct.pack('>2I',0,0x60005200));u.mem_write(0x60005238,struct.pack('>2I',0,0x6000ffe0))
    terrain=[];ref.terrain_enabled=True
    for hit,height in [(0,0.),(1,123.5),(1,-25.25)]:
        ref.terrain_hit=hit;ref.terrain_height=height;ref.putfloating(1,.016)
        ref.call(0x8004ceb0,[0x60006000,0,0x60007000]);actual=list(struct.unpack('>16f',ref.vehicle_matrix));initial=list(struct.unpack('>16f',last_source))
        # initial is source world; source outer routine converts to Bond first.
        native_source=array(initial);native_bond=array([0.]*16)
        lib.mw_nis_pose_world.argtypes=[ptr]*5
        if not lib.mw_nis_pose_world(native_source,array(struct.unpack('>16f',identity)),array(struct.unpack('>16f',identity)),None,native_bond):raise ValueError('Native terrain setup failed')
        if not lib.mw_nis_pose_ground_height(native_bond,hit,height):raise ValueError('Native terrain helper failed')
        if struct.pack('>16f',*native_bond)!=ref.vehicle_matrix:raise ValueError('Original terrain matrix differs')
        if ref.query['mask_type']!=[0,3] or ref.query['normal_pointer']!=0:raise ValueError('Terrain query contract differs')
        terrain.append(dict(hit=bool(hit),returned_height=height,output_bond_y=actual[13],query=ref.query))
    return dict(matrix_cases=cases,bit_identical_world_and_bond=True,root_still_pose=rest,terrain_cases=terrain,reference='Original GetStillPose+PoseSQTToGlobal+ROOT parent+scene bMulMatrix+ConvertToBond; complete outer terrain stage with external query and vehicle destination intercepted')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--root-bundle',type=Path,required=True);p.add_argument('--actor-inputs',type=Path,required=True);p.add_argument('--library',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();report=verify(a.dol.read_bytes(),a.root_bundle.read_bytes(),a.actor_inputs.glob('*.bin'),a.library);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(matrix_cases=report['matrix_cases'],bit_identical=report['bit_identical_world_and_bond'],terrain_cases=len(report['terrain_cases']))))
if __name__=='__main__':main()
