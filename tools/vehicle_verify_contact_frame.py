#!/usr/bin/env python3
"""Verify original wheel-local projection/basis against a bounded paired model."""
import argparse
import ctypes as C
import json
import math
import random
import struct
import subprocess
import tempfile
from pathlib import Path
from vehicle_contact_frame_reference import OriginalWheelFrameReference
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference,COMMIT
from vehicle_ppc_reference import OriginalPpcReference,DOL_SHA256
from vehicle_verify_contact import Math,UNARY,BINARY

class Vector(C.Structure):_fields_=[(n,C.c_float) for n in ['x','y','z']]
class Frame(C.Structure):_fields_=[('lateral_axis',Vector),('longitudinal_force_axis',Vector),('lateral_velocity',C.c_float),('longitudinal_velocity',C.c_float),('normal_load_factor',C.c_float)]

def verify(dol,dolphin):
    raw=dol.read_bytes();root=Path(__file__).resolve().parents[1];rng=random.Random(200515);cases=0;default_max_error=0;force_cases=0
    def bits(value):return struct.pack('>f',value)
    with tempfile.TemporaryDirectory(prefix='mw-contact-frame-') as temporary,DolphinFrsqrteReference(dolphin) as estimate:
        reference=OriginalWheelFrameReference(raw,estimate);scalar=OriginalPpcReference(raw)
        lib=Path(temporary)/'frame.so'
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_physics_contact_frame.c'),str(root/'source_bmw/mw_gekko_math.c'),'-lm','-o',str(lib)],check=True)
        impl=C.CDLL(str(lib));f=impl.mw_physics_contact_frame;f.argtypes=[C.POINTER(Vector),C.POINTER(Vector),C.POINTER(Vector),C.POINTER(Frame),C.POINTER(Math)];f.restype=None
        world=impl.mw_physics_contact_world_force;world.argtypes=[C.POINTER(Frame),C.POINTER(Vector),*([C.c_float]*5),C.POINTER(Vector)];world.restype=None
        point=impl.mw_physics_contact_point_velocity;point.argtypes=[C.POINTER(C.c_float),*([C.POINTER(Vector)]*6)];point.restype=None
        moment=impl.mw_physics_contact_force_moment;moment.argtypes=[C.POINTER(C.c_float),C.POINTER(Vector),C.c_float,C.c_float,*([C.POINTER(Vector)]*4)];moment.restype=None
        moment_cases=0
        failures=[]
        def original_sqrt(value,_):
            try:return scalar.scalar_math('sqrt',value,estimate)
            except Exception as e:failures.append(str(e));return float('nan')
        sqrt=UNARY(original_sqrt);empty_angle=BINARY();empty_sin=UNARY();provider=Math(sqrt,empty_angle,empty_sin,None)
        point_cases=0
        for index in range(2048):
            # Actual source rotation supports nonorthonormal float matrices too.
            matrix=(C.c_float*16)(*[rng.uniform(-1,1) for _ in range(12)],*[rng.uniform(-15000,15000) for _ in range(3)],1)
            mount,cg,linear,angular=[Vector(*[rng.uniform(-scale,scale) for _ in range(3)]) for scale in [3,1,100,15]]
            expected=reference.point_velocity(list(matrix),*[list(getattr(v,k) for k in ["x","y","z"]) for v in [mount,cg,linear,angular]])
            query,velocity=Vector(),Vector();point(matrix,C.byref(mount),C.byref(cg),C.byref(linear),C.byref(angular),C.byref(query),C.byref(velocity))
            for name,result in [("query_point",query),("velocity",velocity)]:
                for component,want in zip(["x","y","z"],expected[name]):
                    if bits(getattr(result,component))!=bits(want):raise AssertionError(("point-kinematics",index,name,component,getattr(result,component),want))
            force=Vector(*[rng.uniform(-40000,40000) for _ in range(3)]);compression=C.c_float(rng.uniform(0,.3)).value;ride=C.c_float(rng.uniform(0,.5)).value
            expected_moment=reference.force_moment(list(matrix),[getattr(mount,k) for k in ['x','y','z']],compression,ride,[getattr(cg,k) for k in ['x','y','z']],[getattr(force,k) for k in ['x','y','z']])
            application,torque=Vector(),Vector();moment(matrix,C.byref(mount),compression,ride,C.byref(cg),C.byref(force),C.byref(application),C.byref(torque))
            for name,result in [('application_point',application),('world_moment',torque)]:
                for component,want in zip(['x','y','z'],expected_moment[name]):
                    if bits(getattr(result,component))!=bits(want):raise AssertionError(('force-moment',index,name,component,getattr(result,component),want))
            moment_cases+=1
            point_cases+=1
        vectors=[([0,1,0],[0,0,1],[1,0,20]),([0,1,0],[0,1,0],[1,2,3]),([0,0,0],[1,0,0],[1,2,3])]
        def unit():
            v=[rng.uniform(-1,1) for _ in range(3)];length=math.sqrt(sum(x*x for x in v));return [x/length for x in v]
        vectors += [(unit(),unit(),[rng.uniform(-100,100) for _ in range(3)]) for _ in range(2048)]
        for normal,direction,velocity in vectors:
            n,d,v=Vector(*normal),Vector(*direction),Vector(*velocity);original=reference.frame(*[[getattr(item,key) for key in ['x','y','z']] for item in [n,d,v]]);out=Frame()
            f(C.byref(n),C.byref(d),C.byref(v),C.byref(out),C.byref(provider));assert not failures,failures
            for name in ['lateral_axis','longitudinal_force_axis']:
                for component,expected in zip(['x','y','z'],original[name]):
                    actual=getattr(getattr(out,name),component)
                    if bits(actual)!=bits(expected):raise AssertionError((cases,name,component,actual,expected))
            for name in ['lateral_velocity','longitudinal_velocity','normal_load_factor']:
                if bits(getattr(out,name))!=bits(original[name]):raise AssertionError((cases,name,getattr(out,name),original[name]))
            up=Vector(*(unit() if cases>2 else [0,1,0]));spring=C.c_float(rng.uniform(0,20000)).value;mass=C.c_float(rng.uniform(900,3000)).value;dt=C.c_float(rng.choice([1/120,1/60])).value;lf=C.c_float(rng.uniform(-30000,30000)).value;longf=C.c_float(rng.uniform(-30000,30000)).value
            source_force=reference.world_force([getattr(n,k) for k in ['x','y','z']],original['lateral_axis'],[getattr(up,k) for k in ['x','y','z']],spring,mass,dt,original['lateral_velocity'],lf,longf)
            world_out=Vector();world(C.byref(out),C.byref(up),spring,mass,dt,lf,longf,C.byref(world_out))
            for name,expected in zip(['x','y','z'],source_force):
                if bits(getattr(world_out,name))!=bits(expected):raise AssertionError(('world-force',cases,name,getattr(world_out,name),expected))
            force_cases+=1
            native=Frame();f(C.byref(n),C.byref(d),C.byref(v),C.byref(native),None)
            for name in ['lateral_velocity','longitudinal_velocity','normal_load_factor']:default_max_error=max(default_max_error,abs(getattr(native,name)-getattr(out,name)))
            cases+=1
    return dict(dol_sha256=DOL_SHA256,dolphin_commit=COMMIT,reference_ranges=['0x8021C750..0x8021C7D8','0x8024AA28..0x8024AA8C','0x8024ACFC..0x8024AD3C','0x8024AF4C..0x8024AFD4'],paired_model_float_bit_cases=cases,world_force_float_bit_cases=force_cases,point_velocity_float_bit_cases=point_cases,force_moment_float_bit_cases=moment_cases,runtime_default_max_projection_error=default_max_error,limitations=['paired reference uses shared bounded binary64-to-float model; no console FMA-tie/subnormal/FPSCR claim','original sqrt callbacks cross-check independent runtime Gekko stage','steered direction producer remains separate; point velocity producer now executes actual original slice'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--dolphin-reference',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.dol,a.dolphin_reference),indent=2))
