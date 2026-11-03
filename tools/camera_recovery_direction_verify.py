#!/usr/bin/env python3
"""Original camera velocity/body-direction target comparisons, not full chase."""
import argparse,ctypes,hashlib,json,math,random,struct,subprocess,tempfile
from pathlib import Path
from camera_recovery_verify import Reference,DOL_SHA
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference,COMMIT,SOURCES
class DirectionReference(Reference):
    def __init__(self,raw,estimate):
        super().__init__(raw)
        from unicorn import UC_HOOK_CODE
        from unicorn.ppc_const import UC_PPC_REG_FPR0,UC_PPC_REG_PC
        self.estimate=estimate
        def instruction(u,a,size,user):
            if a==0x80060afc:
                value=struct.unpack('>d',struct.pack('>Q',u.reg_read(UC_PPC_REG_FPR0+10)))[0]
                result=self.estimate(value);u.reg_write(UC_PPC_REG_FPR0+13,struct.unpack('>Q',struct.pack('>d',result))[0]);u.reg_write(UC_PPC_REG_PC,a+4)
        self.uc.hook_add(UC_HOOK_CODE,instruction)
        self.allowed=((0x80080f8c,0x80081008),(0x802090a4,0x802090b4))
        self.extra_write_ranges=((0x80416000,0x80417000),(0x8045ac90,0x8045acc0))
        self.run(0x80080f8c,0x80081008)
        self.curve_raw=bytes(self.uc.mem_read(0x8045aca0,16))
        assert struct.unpack('>4f',self.curve_raw)==(8,0,13,1)
        assert bytes(self.uc.mem_read(0x8045acb0,8))==struct.pack('>2I',0x8045aca0,2)
    def direction(self,velocity,forward,speed):
        from unicorn.ppc_const import UC_PPC_REG_30
        mover=bytearray(0x124);struct.pack_into('>I',mover,0x80,self.LAYOUT);self.uc.mem_write(self.INSTANCE,bytes(mover))
        controller=bytearray(0x80);struct.pack_into('>3f',controller,0,*velocity);struct.pack_into('>f',controller,0x10,speed);struct.pack_into('>3f',controller,0x48,*forward);self.uc.mem_write(self.LAYOUT,bytes(controller))
        self.uc.reg_write(UC_PPC_REG_30,self.INSTANCE)
        self.allowed=((0x80073028,0x80073100),(0x80060d50,0x80060d88),(0x80060ac0,0x80060b8c),(0x802090b4,0x80209190))
        self.extra_write_ranges=()
        self.run(0x80073028,0x80073100)
        return bytes(self.uc.mem_read(self.STACK+8,12))
def verify(dol):
    raw=dol.read_bytes();oracle=DolphinFrsqrteReference('/workspace/port-research/driving-engine/references/dolphin');reference=DirectionReference(raw,oracle.estimate)
    rng=random.Random(0x80073028);root=Path(__file__).resolve().parents[1];vectors=[]
    for forward in [(1,0,0),(0,1,0),(0,0,1),(.6,.8,0),(-.6,0,.8)]:
        for velocity in [(0,0,0),(1,0,0),(-1,0,0),(0,10,0),(0,-10,0),(0,0,30),(8,-9,13),(-20,4,-2)]:
            for speed in [0,7.9999995,8,8.000001,10.5,12.999999,13,13.000001,80]:vectors.append((velocity,forward,speed))
    for _ in range(600):
        yaw=rng.uniform(-math.pi,math.pi);pitch=rng.uniform(-.5,.5)
        vectors.append(([rng.uniform(-100,100) for _ in range(3)],[math.cos(pitch)*math.cos(yaw),math.cos(pitch)*math.sin(yaw),math.sin(pitch)],rng.uniform(0,80)))
    count=0
    with tempfile.TemporaryDirectory(prefix='camera-direction-') as temporary:
        so=Path(temporary)/'direction.so';subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_original_camera_direction.c'),str(root/'source_bmw/mw_gekko_math.c'),'-lm','-o',str(so)],check=True)
        lib=ctypes.CDLL(str(so));arr=ctypes.c_float*3;function=lib.mw_original_camera_direction_target;function.argtypes=[arr,arr,ctypes.c_float,arr,ctypes.POINTER(ctypes.c_float)];function.restype=ctypes.c_bool
        for velocity,forward,speed in vectors:
            v=arr(*velocity);f=arr(*forward);speed=ctypes.c_float(speed).value;expected=reference.direction(v,f,speed);out=arr();weight=ctypes.c_float();assert function(v,f,speed,out,ctypes.byref(weight))
            actual=struct.pack('>3f',*out)
            if actual!=expected:raise AssertionError((list(v),list(f),speed,list(out),struct.unpack('>3f',expected)))
            count+=1
    oracle.close()
    return dict(dol_sha256=DOL_SHA,original_direction_range='80073028..80073100',original_curve_startup='80080F8C..80081004',original_curve_raw=reference.curve_raw.hex(),source_points=[[8,0],[13,1]],direction_float_bit_cases=count,patched_instructions=0,hardware_semantic_adapter='Onlyfrsqrte usesexistingexternalpinnedDolphinoracle;allremainingPPCunchanged',oracle_commit=COMMIT,oracle_source_hashes=SOURCES,limitations=['Direction target only; later timer/vertical attenuation and persistent interpolation not included','Actual original body-basis/controller frame must be supplied; no viewer-axis guess','Full camera collision,preset transitions,noise and finalmatrix output remain unported'])
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dol',type=Path,required=True);args=parser.parse_args();print(json.dumps(verify(args.dol),indent=2))
