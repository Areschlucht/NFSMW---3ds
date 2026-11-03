#!/usr/bin/env python3
"""Compare actual shaft update8025817C..80258298 with pinned original code.

Supplies caller live-ins explicitly, preserving whole-engine integration gates.
Checks all object bytes, returned reaction and both updated scalar float bits.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from vehicle_ppc_reference import OriginalPpcReference,DOL_SHA256

class Input(C.Structure):
    _fields_=[('gear',C.c_uint),('clutch',C.c_uint)]+[(n,C.c_float) for n in ['seconds','omega','rpm','torque','reaction','inertia','throttle','slip','idle','optimal','minimum','maximum']]
class Output(C.Structure):
    _fields_=[(n,C.c_float) for n in ['omega','acceleration','reaction']]

def original(ref,p):
    from unicorn.ppc_const import UC_PPC_REG_31,UC_PPC_REG_FPR0,UC_PPC_REG_MSR,UC_PPC_REG_PC
    u=ref.uc;obj=0x81608000;engine=ref.ENGINE;trans=0x81603000
    raw=bytearray(0x1b0)
    for off,value in [(0x88,p.gear),(0x19c,p.clutch),(0x150,engine),(0x164,trans)]:struct.pack_into('>I',raw,off,value)
    for off,value in [(0x90,p.throttle),(0xf0,p.omega),(0x194,p.optimal)]:struct.pack_into('>f',raw,off,value)
    u.mem_write(obj,bytes(raw));u.mem_write(engine+0x5c,struct.pack('>f',p.idle));u.mem_write(trans+0x74,struct.pack('>f',p.slip))
    u.reg_write(UC_PPC_REG_31,obj);u.reg_write(UC_PPC_REG_MSR,0x2000)
    for reg,value in [(19,p.inertia),(21,p.minimum),(23,p.rpm),(25,p.seconds),(26,p.maximum),(29,p.torque),(30,p.reaction)]:u.reg_write(UC_PPC_REG_FPR0+reg,struct.unpack('>Q',struct.pack('>d',value))[0])
    ref.allowed=((0x8025817c,0x80258298),);ref.write_ranges=((obj,obj+len(raw)),);ref.count=0
    try:u.emu_start(0x8025817c,0x80258298,count=100,timeout=200000)
    finally:ref.write_ranges=()
    if u.reg_read(UC_PPC_REG_PC)!=0x80258298:raise ValueError('Shaft reference exceeded bounds')
    actual=bytes(u.mem_read(obj,len(raw)))
    if any(a!=b for i,(a,b) in enumerate(zip(raw,actual)) if i not in range(0xf0,0xf8)):raise ValueError('Unexpected original state write')
    reaction=struct.unpack('>d',struct.pack('>Q',u.reg_read(UC_PPC_REG_FPR0+30)))[0]
    return (*struct.unpack_from('>2f',actual,0xf0),reaction)

def verify(dol):
    root=Path(__file__).resolve().parents[1];ref=OriginalPpcReference(dol.read_bytes());rng=random.Random(20058250);cases=0;branches={}
    def bits(v):return struct.pack('>f',v)
    with tempfile.TemporaryDirectory(prefix='mw-shaft-') as tmp:
        so=Path(tmp)/'shaft.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_physics_transmission.c'),str(root/'source_bmw/mw_physics_engine.c'),'-lm','-o',str(so)],check=True)
        lib=C.CDLL(str(so));step=lib.mw_physics_transmission_shaft_step;step.argtypes=[C.POINTER(Input),C.POINTER(Output)];step.restype=C.c_bool
        def check(p):
            nonlocal cases
            expected=original(ref,p);out=Output();assert step(C.byref(p),C.byref(out));actual=(out.omega,out.acceleration,out.reaction)
            if list(map(bits,expected))!=list(map(bits,actual)):raise AssertionError(([getattr(p,n) for n,t in p._fields_],expected,actual))
            cases+=1
            key='launch_reaction_attenuated' if bits(expected[2])!=bits(p.reaction) else 'reaction_unchanged';branches[key]=branches.get(key,0)+1
        # Exercise gate boundaries, degenerate optimal range, low/high speed clamp.
        for gear in (0,1,2,3,7):
            for clutch in (0,1,2):
                for throttle in (-.1,0,.1,1):
                    for torque,reaction in [(100,-100),(-100,100),(0,-100),(100,100)]:
                        for rpm in (0,800,4000,8500):
                            for optimal in (800,800.0000001,7500):
                                check(Input(gear,clutch,1/60,rpm*.10471976548433304,rpm,torque,reaction,.5,throttle,.8,800,optimal,800*.10471976548433304,9000*.10471976548433304))
        for _ in range(1024):
            rpm=rng.uniform(0,12000);check(Input(rng.randrange(8),rng.randrange(3),rng.choice([0,1/120,1/60,.1]),rpm*.10471976548433304,rpm,rng.uniform(-1000,1000),rng.uniform(-1000,1000),rng.uniform(.01,3),rng.random(),rng.uniform(0,2),800,rng.choice([800,7500]),800*.10471976548433304,9000*.10471976548433304))
    return dict(dol_sha256=DOL_SHA256,original_range='8025817C..80258298',float_bit_cases=cases,branches=branches,limitations=['Caller supplies explicit original live-ins including pre-integration engine RPM, peak-torque RPM and upper-limit selector','Whole-engine torque/shaft synchronization, event policy and cadence are separate'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();report=verify(a.dol);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
