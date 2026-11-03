#!/usr/bin/env python3
"""Compare powered-wheel synchronization/capping against original whole functions."""
import argparse
import ctypes as C
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from vehicle_transmission_verify import TransmissionReference,EXTRA_ABI
from vehicle_ppc_reference import DOL_SHA256

for base,restore,first,off in [(0x802565c8,0x80256888,28,0x10),(0x80256a10,0x80256b78,29,0x18)]:
    for r in range(first,32):
        offset=off+(r-first)*8;EXTRA_ABI[base+(r-first)*4]=0xf0000000|(r<<21)|(1<<16)|offset;EXTRA_ABI[restore+(r-first)*4]=0xe0000000|(r<<21)|(1<<16)|offset
class Wheel(C.Structure):_fields_=[(n,C.c_float) for n in ['omega','compression','traction','previous','radius']]+[('locked',C.c_uint)]
class SyncReference(TransmissionReference):
    def sync(self,wheels,split,gear,target,speed,cap=False):
        actor=self.speed_wheels(wheels);struct.pack_into('>I',actor,0x54,0x803fe938);self.uc.mem_write(0x8160d000,bytes(actor))
        vehicle=bytearray(0x200);struct.pack_into('>I',vehicle,0xb8,0x803f8728);struct.pack_into('>f',vehicle,0x128,speed);self.uc.mem_write(0x8160e000,bytes(vehicle))
        obj=bytearray(0x1b0)
        for off,value in [(0x118,0x8160d050),(0x4c,0x8160e0b4),(0x88,gear),(0x164,self.ENGINE),(0x54,0x8160b200)]:struct.pack_into('>I',obj,off,value)
        self.uc.mem_write(self.OBJECT,bytes(obj));layout=bytearray(132);struct.pack_into('>f',layout,0x70,split);self.uc.mem_write(self.ENGINE,bytes(layout))
        gear_table=bytearray(0x18);struct.pack_into('>hHI',gear_table,0x10,-0x50,0,0x80269eb4);self.uc.mem_write(0x8160b200,bytes(gear_table))
        self.allowed=((0x8025625c,0x80256484),(0x802565c0,0x802568a0),(0x80256a08,0x80256b8c),(0x80269eb4,0x80269ebc),(0x802479a0,0x80247a0c),(0x80268da8,0x80268e0c),(0x80268e0c,0x80268e14),(0x80268e7c,0x80268ea4),(0x8022e1d0,0x8022e1d8))
        before=[bytes(self.uc.mem_read(0x81610000+i*0x1000,0x140)) for i in range(4)];self.write_ranges=tuple((0x81610000+i*0x1000,0x81610000+i*0x1000+0x140) for i in range(4))
        try:self._call(0x80256a08 if cap else 0x802565c0,self.OBJECT,target)
        finally:self.write_ranges=()
        values=[]
        for i,raw in enumerate(before):
            after=bytes(self.uc.mem_read(0x81610000+i*0x1000,0x140))
            assert all(a==b for j,(a,b) in enumerate(zip(raw,after)) if j not in range(0xd0,0xd4));values.append(struct.unpack_from('>f',after,0xd0)[0])
        return values

def verify(dol):
    ref=SyncReference(dol.read_bytes());root=Path(__file__).resolve().parents[1];rng=random.Random(802565);counts={'sync':0,'cap':0}
    def bits(v):return struct.pack('>f',v)
    with tempfile.TemporaryDirectory(prefix='mw-sync-') as tmp:
        so=Path(tmp)/'sync.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_physics_transmission.c'),str(root/'source_bmw/mw_physics_engine.c'),'-lm','-o',str(so)],check=True)
        lib=C.CDLL(str(so));sync=lib.mw_physics_transmission_sync_wheels;sync.argtypes=[C.POINTER(Wheel),C.c_float,C.c_uint,C.c_float,C.c_float];sync.restype=C.c_bool
        cap=lib.mw_physics_transmission_cap_airborne_wheels;cap.argtypes=[C.POINTER(Wheel),C.c_float,C.c_float];cap.restype=C.c_bool
        for index in range(4096):
            wheels=(Wheel*4)(*(Wheel(rng.uniform(-200,200),rng.choice([-.1,0,.1]),rng.choice([0,.5,1,1.1]),rng.uniform(-60,60),rng.choice([.25,.3433,.5]),rng.randrange(2)) for _ in range(4)))
            split=C.c_float(rng.choice([0,.25,.5,.75,1])).value;gear=rng.choice([0,1,2,7]);target=C.c_float(rng.choice([0,-100,100,rng.uniform(-300,300)])).value;speed=C.c_float(rng.choice([-30,0,10,40/2.236989974975586,30])).value
            for mode,fun in [(False,sync),(True,cap)]:
                expected=ref.sync(wheels,split,gear,target,speed,mode);output=(Wheel*4).from_buffer_copy(wheels)
                assert fun(output,split,target) if mode else fun(output,split,gear,target,speed)
                actual=[w.omega for w in output]
                if list(map(bits,expected))!=list(map(bits,actual)):raise AssertionError((mode,index,split,gear,target,speed,expected,actual))
                counts['cap' if mode else 'sync']+=1
    return dict(dol_sha256=DOL_SHA256,float_bit_cases=counts,original_ranges=['802565C0..802568A0','80256A08..80256B8C'],wheel_interface='Actual original Racer vtable803FE938 and its signed this adjustments',vehicle_speed_getter='Actual Vehicle vtable803F8728.slot138→8022E1D0 readsVehicle+128',limitations=['Vehicle+128 producer remains separate; explicit supplied source scalar','Call ordering relative to original engine torque update remains a higher-level integration gate'])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.dol);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
